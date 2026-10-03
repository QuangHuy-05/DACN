"""Fixed-split training and frozen dev validation, shared by three model families."""

import copy
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil

from src.evaluation.dev_runner import ROOT, file_hash, write_json, write_jsonl, run_dev_inference, score_dev_predictions, load_dev_input
from src.evaluation.experiment_config import modeling_config
from src.modeling.alignment import encode_gold
from src.modeling.artifacts import code_hashes, git_state, audit_run
from src.modeling.checkpoints import save_checkpoint, load_checkpoint, training_signature, capture_rng, restore_rng
from src.modeling.datasets import load_corpus
from src.modeling.labels import TAG_TO_ID, DP_TAG_TO_ID, t1_target
from src.modeling.protocol import selection_key
from src.modeling.resources import load_phobert_processor, preflight, validate_resource_lock


def create_phobert_model(config, lock):
    from transformers import AutoModel
    from src.modeling.phobert_crf import PhoBERTCRF
    from src.modeling.proposed_dynamic import ProposedDynamic
    encoder = AutoModel.from_pretrained(str(ROOT / lock["components"]["encoder"]["path"]), local_files_only=True)
    if encoder.config.max_position_embeddings < config["max_encoder_tokens"]:
        raise ValueError("ENCODER_POSITION_LIMIT_BELOW_LOCKED_LIMIT")
    cls = ProposedDynamic if config["t1_implemented"] else PhoBERTCRF
    kwargs = {"dropout": config["dropout"]}
    if config["t1_implemented"]:
        kwargs["t1_loss_weight"] = config["t1_loss_weight"]
    return cls(encoder, **kwargs)


def set_seed(seed, deterministic=True):
    import torch
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except ImportError:
        pass
    torch.use_deterministic_algorithms(deterministic)
    if hasattr(torch.backends, "cudnn"):
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = deterministic


def collate(examples, processor, device):
    import torch
    from torch.nn.utils.rnn import pad_sequence
    ids = pad_sequence([torch.tensor(a.input_ids) for a, _, _, _ in examples], batch_first=True,
                       padding_value=processor.tokenizer.pad_token_id).to(device)
    attention = torch.arange(ids.shape[1], device=device)[None] < torch.tensor([len(a.input_ids) for a, _, _, _ in examples], device=device)[:, None]
    tags = pad_sequence([torch.tensor([TAG_TO_ID[tag] for tag in tags]) for _, tags, _, _ in examples],
                        batch_first=True, padding_value=0).to(device)
    return {"input_ids": ids, "attention_mask": attention.long(), "unit_to_model": [a.unit_to_model for a, _, _, _ in examples],
            "tags": tags, "t1_targets": torch.tensor([target for _, _, target, _ in examples], device=device),
            "t1_mask": torch.tensor([mask for _, _, _, mask in examples], dtype=torch.bool, device=device)}


def checkpoint_metadata(config, manifest, resource_path, epoch, global_step, resume_supported):
    return {"model_id": config["model_id"], "tasks": ["T0", "T1"] if config["t1_implemented"] else ["T0"],
            "label_map": config["label_map"], "processor_version": config["processor_version"], "config": config,
            "training_signature": training_signature(config), "corpus_manifest_sha256": config["corpus_manifest_sha256"],
            "train_dev_sha256": {name: manifest["output_sha256"][name] for name in ("train.jsonl", "dev.jsonl")},
            "resource_lock_sha256": file_hash(resource_path), "epoch": epoch, "global_step": global_step,
            "resume_supported": resume_supported, "evaluation_exclusions": manifest["evaluation_exclusions"],
            "purpose": config["purpose"], "pretrained": config["pretrained"], "code_sha256": code_hashes()}


def freeze_validation(adapter, config, checkpoint, resource_path, corpus_dir, run_dir, epoch):
    run_id = f"{run_dir.name}_epoch{epoch:03d}_dev"
    inference_config = modeling_config(run_id, config, checkpoint, resource_path)
    samples = load_dev_input(corpus_dir / "dev_input.jsonl", corpus_dir / "manifest.json")
    epoch_dir = run_dir / "validation" / run_id
    rng = capture_rng()
    try:
        run_dev_inference(adapter, samples, inference_config, epoch_dir,
            {"corpus_manifest_sha256": file_hash(corpus_dir / "manifest.json"),
             "dev_input_sha256": file_hash(corpus_dir / "dev_input.jsonl")})
        metrics = score_dev_predictions(epoch_dir / "predictions.jsonl", corpus_dir / "dev.jsonl", epoch_dir, corpus_dir / "manifest.json")
    finally:
        restore_rng(rng)
    # Audit receives only released dev; T1 masks apply in the shared scorer.
    write_json(epoch_dir / "completion_audit.json", audit_run(epoch_dir, corpus_dir))
    return metrics


def _publish_checkpoint_alias(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    try:
        os.link(source, temporary)
    except OSError:
        shutil.copyfile(source, temporary)
    temporary.replace(target)
    meta = json.loads(source.with_suffix(source.suffix + ".json").read_text(encoding="utf-8"))
    meta["checkpoint_file"] = target.name
    write_json(target.with_suffix(target.suffix + ".json"), meta)


def _resource_hashes(resource_path, lock):
    hashes = {resource_path.resolve().relative_to(ROOT).as_posix(): file_hash(resource_path)}
    for entry in lock["components"].values():
        hashes.update({(Path(entry["path"]) / name).as_posix(): digest for name, digest in entry["files"].items()})
    return hashes


def train_model(config, resource_path, corpus_dir, run_dir, resume_from=None, weights_from=None):
    if config["model_id"] == "PROPOSED-NO-CONSTRAINT":
        raise ValueError("ABLATION_USES_SAME_PROPOSED_CHECKPOINT; run infer with no-constraint config")
    if run_dir.exists():
        raise FileExistsError("Refusing to overwrite training run")
    if resume_from and weights_from:
        raise ValueError("Choose optimizer resume OR weights restart")
    readiness = preflight(config, resource_path)
    if readiness["blockers"]:
        raise RuntimeError("RESOURCE_PREFLIGHT_BLOCKED: " + str(readiness["blockers"]))
    lock = validate_resource_lock(resource_path, config["model_id"])
    manifest, splits = load_corpus(corpus_dir)
    if config["model_id"] == "DP-FT-FT":
        if resume_from:
            raise ValueError("DP_OPTIMIZER_RESUME_UNSUPPORTED: --weights-from in a new run")
        return _train_deepparse(config, resource_path, lock, corpus_dir, run_dir, manifest, splits, weights_from)
    import torch
    from src.evaluation.adapters.phobert_crf_adapter import PhoBERTCRFAdapter
    set_seed(config["seed"], config["deterministic"])
    processor = load_phobert_processor(config, lock)
    # Validate every sample first; dev units depend only on text, labels attached afterwards.
    examples = {}
    for split, rows in splits.items():
        examples[split] = []
        for row in rows:
            alignment = processor.align_text(row["text"])
            examples[split].append((alignment, encode_gold(alignment, row["spans"]), *t1_target(row, manifest)))
    model = create_phobert_model(config, lock).to(config["device"])
    encoder_params = list(model.encoder.parameters())
    encoder_ids = {id(p) for p in encoder_params}
    head_params = [p for p in model.parameters() if id(p) not in encoder_ids]
    optimizer = torch.optim.AdamW([{"params": encoder_params, "lr": config["candidate"]["encoder_lr"]},
        {"params": head_params, "lr": config["candidate"]["head_lr"]}], weight_decay=config["weight_decay"])
    steps_per_epoch = math.ceil(len(examples["train"]) / config["effective_batch_size"])
    total_steps = steps_per_epoch * config["max_epochs"]
    warmup = int(total_steps * config["warmup_fraction"])
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda step:
        step / max(1, warmup) if step < warmup else max(0, (total_steps - step) / max(1, total_steps - warmup)))
    start_epoch, global_step, best_key, stale = 1, 0, None, 0
    initialization = None
    if resume_from or weights_from:
        source = resume_from or weights_from
        payload, meta = load_checkpoint(source, config, config["corpus_manifest_sha256"], file_hash(resource_path),
            model, optimizer if resume_from else None, scheduler if resume_from else None, bool(resume_from))
        initialization = {"path": str(source.relative_to(ROOT)), "sha256": file_hash(source),
                          "kind": "optimizer_scheduler_rng_resume" if resume_from else "weights_new_optimizer_new_run"}
        if resume_from:
            start_epoch, global_step = meta["epoch"] + 1, meta["global_step"]
            state = payload["selection_state"]
            best_key = tuple(state["best_key"]) if state.get("best_key") is not None else None
            stale = state.get("stale", 0)
            if start_epoch > config["max_epochs"] or stale >= config["patience"]:
                raise ValueError("RESUME_EXCEEDS_OR_HAS_FINISHED_LOCKED_BUDGET")
    run_dir.mkdir(parents=True)
    write_json(run_dir / "model_config.json", config)
    if resume_from:
        best_source = resume_from.parent / "best.pt"
        if not best_source.exists():
            raise ValueError("RESUME_REQUIRES_HASH_VERIFIED_BEST_CHECKPOINT_IN_SOURCE_RUN")
        load_checkpoint(best_source, config, config["corpus_manifest_sha256"], file_hash(resource_path))
        _publish_checkpoint_alias(best_source, run_dir / "checkpoints/best.pt")
    logs = []
    previous_resume = None
    for epoch in range(start_epoch, config["max_epochs"] + 1):
        model.train()
        order = list(range(len(examples["train"])))
        random.shuffle(order)
        losses = []
        for base in range(0, len(order), config["effective_batch_size"]):
            optimizer.zero_grad(set_to_none=True)
            block = order[base:base + config["effective_batch_size"]]
            for offset in range(0, len(block), config["micro_batch_size"]):
                group = block[offset:offset + config["micro_batch_size"]]
                batch = collate([examples["train"][i] for i in group], processor, config["device"])
                if not config["t1_implemented"]:
                    batch.pop("t1_targets")
                    batch.pop("t1_mask")
                result = model(**batch)
                loss = result["loss"]
                if not bool(torch.isfinite(loss)):
                    raise RuntimeError("NONFINITE_TRAINING_LOSS")
                (loss * len(group) / len(block)).backward()
                losses.append(float(loss.detach()))
            torch.nn.utils.clip_grad_norm_(model.parameters(), config["gradient_clip"])
            optimizer.step()
            scheduler.step()
            global_step += 1
        checkpoint = run_dir / "checkpoints" / f"epoch_{epoch:03d}.pt"
        meta = checkpoint_metadata(config, manifest, resource_path, epoch, global_step, False)
        # Save before inference/scoring; completion state is recorded separately after scoring.
        save_checkpoint(checkpoint, model, meta, native_payload={"model": model.state_dict()})
        model.eval()
        evaluation_config = copy.deepcopy(config)
        if evaluation_config["t1_implemented"]:
            evaluation_config["model_id"] = "PROPOSED-NO-CONSTRAINT"
            evaluation_config["structural_policy"]["enabled"] = False
        adapter = PhoBERTCRFAdapter(config=evaluation_config, model=model, processor=processor)
        metrics = freeze_validation(adapter, evaluation_config, checkpoint, resource_path, corpus_dir, run_dir, epoch)
        key = selection_key(metrics, epoch, int(config["candidate"]["id"][-2:]) - 1)
        improved = best_key is None or key > best_key
        if improved:
            best_key, stale = key, 0
            _publish_checkpoint_alias(checkpoint, run_dir / "checkpoints/best.pt")
        else:
            stale += 1
        # Resume uses post-validation selection counters; do not mutate the frozen epoch checkpoint.
        resume_checkpoint = run_dir / "checkpoints" / f"resume_epoch_{epoch:03d}.pt"
        resume_meta = {**meta, "resume_supported": True}
        save_checkpoint(resume_checkpoint, model, resume_meta, optimizer, scheduler,
                        {"best_key": best_key, "stale": stale})
        _publish_checkpoint_alias(resume_checkpoint, run_dir / "checkpoints/last.pt")
        # Only full resume state rolls during this active run; inference epoch weights remain immutable.
        if previous_resume is not None:
            previous_resume.unlink()
            previous_resume.with_suffix(previous_resume.suffix + ".json").unlink()
        previous_resume = resume_checkpoint
        logs.append({"epoch": epoch, "global_step": global_step, "mean_train_loss": sum(losses)/len(losses),
            "dev_selection_key": key, "selection_decoder": "unconstrained", "improved": improved, "stale": stale})
        write_jsonl(run_dir / "training_log.jsonl", logs)
        if stale >= config["patience"]:
            break
    return finalize_training(run_dir, config, resource_path, lock, initialization, logs)


def finalize_training(run_dir, config, resource_path, lock, initialization, logs):
    files = {p.relative_to(run_dir).as_posix(): file_hash(p) for p in run_dir.rglob("*") if p.is_file()}
    value = {"status": "TRAINED_DEV_ONLY", "model_id": config["model_id"], "purpose": config["purpose"],
        "pretrained": config["pretrained"], "config": config, "initialization": initialization, "epochs_in_this_run": len(logs),
        "code_sha256": code_hashes(), "git": git_state(), "resource_sha256": _resource_hashes(resource_path, lock),
        "corpus_manifest_sha256": config["corpus_manifest_sha256"], "output_sha256": files,
        "checkpoint_retention": "immutable model-only epochs and best; last full optimizer/scheduler/RNG; rolling resume states during active run",
        "test100": "NOT_READ_NOT_USED", "selection": "full_schema_exact_span_f1_then_gold_supported_macro_then_epoch"}
    write_json(run_dir / "training_manifest.json", value)
    return value


def _train_deepparse(config, resource_path, lock, corpus_dir, run_dir, manifest, splits, weights_from):
    import torch
    from poutyne import Callback
    from src.modeling.deepparse_training import construct_parser, train_native
    from src.evaluation.adapters.deepparse_finetuned_adapter import DeepparseFinetunedAdapter
    set_seed(config["seed"])
    if weights_from:
        load_checkpoint(weights_from, config, config["corpus_manifest_sha256"], file_hash(resource_path))
    parser = construct_parser(lock, config["device"], weights_from)
    run_dir.mkdir(parents=True)
    write_json(run_dir / "model_config.json", config)
    training_logs = []
    def fingerprints():
        return {name: {"shape": list(value.shape), "sha256": hashlib.sha256(value.detach().cpu().contiguous().numpy().tobytes()).hexdigest()}
                for name, value in parser.model.state_dict().items()}
    pretrained_state = fingerprints()

    class ExactSpanCallback(Callback):
        def __init__(self):
            super().__init__()
            self.best_key, self.stale = None, 0

        def on_train_begin(self, logs=None):
            initial = fingerprints()
            transferred = sorted(name for name in pretrained_state if initial.get(name) == pretrained_state[name])
            changed = sorted(name for name in initial if initial[name] != pretrained_state.get(name))
            encoder = [name for name in pretrained_state if name.startswith("encoder.")]
            decoder = [name for name in pretrained_state if name.startswith("decoder.") and not name.startswith("decoder.linear.")]
            if not encoder or not decoder or any(name not in transferred for name in encoder + decoder):
                raise RuntimeError("PRETRAINED_ENCODER_DECODER_BACKBONE_TRANSFER_NOT_VERIFIED")
            write_json(run_dir / "transfer_report.json", {"transferred_unchanged": transferred,
                "initialized_or_changed": changed, "removed": sorted(set(pretrained_state) - set(initial)),
                "state_before": pretrained_state, "state_after_custom_head": initial,
                "seq2seq_params": None, "embedding_update": "native FastText vectorizer fixed",
                "verification_time": "after native head replacement, before first training batch"})

        def on_epoch_end(self, epoch, logs=None):
            checkpoint = run_dir / "checkpoints" / f"epoch_{epoch:03d}.pt"
            metadata = checkpoint_metadata(config, manifest, resource_path, epoch, epoch * 15, False)
            native = {"address_tagger_model": parser.model.state_dict(), "model_type": "fasttext",
                      "version": "Finetuned_" + parser.version, "prediction_tags": DP_TAG_TO_ID,
                      "named_parser": config["model_id"]}
            save_checkpoint(checkpoint, parser.model, metadata, native_payload=native)
            adapter = DeepparseFinetunedAdapter(config=config, parser=parser)
            metrics = freeze_validation(adapter, config, checkpoint, resource_path, corpus_dir, run_dir, epoch)
            key = selection_key(metrics, epoch, int(config["candidate"]["id"][-2:]) - 1)
            improved = self.best_key is None or key > self.best_key
            if improved:
                self.best_key, self.stale = key, 0
                _publish_checkpoint_alias(checkpoint, run_dir / "checkpoints/best.pt")
            else:
                self.stale += 1
            _publish_checkpoint_alias(checkpoint, run_dir / "checkpoints/last.pt")
            training_logs.append({"epoch": epoch, "selection_key": key, "improved": improved,
                                  "native_log": logs, "stale": self.stale})
            write_jsonl(run_dir / "training_log.jsonl", training_logs)
            if self.stale >= config["patience"]:
                self.model.stop_training = True

    api = train_native(parser, splits, config, run_dir / "native_logs", ExactSpanCallback())
    write_json(run_dir / "native_api.json", api)
    initialization = {"kind": "weights_new_optimizer_new_run", "path": str(weights_from.relative_to(ROOT)),
                      "sha256": file_hash(weights_from)} if weights_from else None
    return finalize_training(run_dir, config, resource_path, lock, initialization, training_logs)
