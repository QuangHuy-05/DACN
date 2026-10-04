"""Kaggle preflight and real pretrained smoke; full training requires separate evidence."""

import gc
import json
from pathlib import Path
import subprocess

from src.evaluation.dev_runner import ROOT, file_hash, write_json, write_jsonl
from src.modeling.alignment import encode_gold, decode_tags
from src.modeling.checkpoints import save_checkpoint, load_checkpoint
from src.modeling.datasets import load_corpus
from src.modeling.hardware_profile import apply_hardware_profile
from src.modeling.labels import t1_target
from src.modeling.protocol import load_config, candidate_config
from src.modeling.resources import preflight, validate_resource_lock, load_phobert_processor

CORPUS = ROOT / "data/processed/annotation/sprint03/corpus_train_dev_v2"
LOCK = ROOT / "data/interim/modeling/sprint03/task_01_06_20261003_v1/resource_lock_local_v1.json"
PROFILE = ROOT / "configs/kaggle/sprint03/cuda128_profile_v1.json"
CONFIGS = {"PHOBERT-CRF": "phobert_crf_v1.json", "PROPOSED-DYN": "proposed_dyn_v1.json"}


def checked_config(model_id, candidate="c01"):
    if model_id not in CONFIGS:
        raise ValueError("MODEL_NOT_CLEARED_FOR_KAGGLE_PIPELINE")
    config = candidate_config(load_config(ROOT / "configs/modeling/sprint03" / CONFIGS[model_id]), candidate)
    return apply_hardware_profile(config, PROFILE)


def evidence_identity():
    return {"corpus_manifest_sha256": file_hash(CORPUS / "manifest.json"),
            "resource_lock_sha256": file_hash(LOCK), "hardware_profile_sha256": file_hash(PROFILE),
            "protocol_lock_sha256": file_hash(ROOT / "configs/modeling/sprint03/protocol_lock_v1.json"),
            "source_sha256": file_hash(Path(__file__))}


def validate_smoke_evidence(path):
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    if report.get("status") != "SMOKE_PASS" or report.get("full_training_performed") is not False:
        raise ValueError("FULL_TRAINING_REQUIRES_REAL_SMOKE_PASS")
    if report.get("identity") != evidence_identity():
        raise ValueError("SMOKE_IDENTITY_MISMATCH")
    if set(report.get("models", {})) != set(CONFIGS) or any(
            row.get("status") != "PRETRAINED_OPTIMIZER_CHECKPOINT_PASS" for row in report["models"].values()):
        raise ValueError("INCOMPLETE_SMOKE_MODEL_COVERAGE")
    if report.get("alignment", {}).get("train") != 240 or report["alignment"].get("dev") != 60:
        raise ValueError("SMOKE_ALIGNMENT_NOT_COMPLETE")
    for row in report["models"].values():
        if row.get("pretrained") is not True or row.get("device") != "cuda:0" or row.get("optimizer_steps") != 1 or row.get("checkpoint_reload") != "PASS":
            raise ValueError("SMOKE_NOT_REAL_PRETRAINED_GPU_INTEGRATION")
    return report


def audit_alignment(processor, manifest, splits, output):
    diagnostics, aligned = [], {}
    for split, rows in splits.items():
        aligned[split] = []
        for row in rows:
            # Alignment consumes text first. Gold is attached only afterwards for QA/train.
            alignment = processor.align_text(row["text"])
            before = alignment.to_dict()
            tags = encode_gold(alignment, row["spans"])
            restored, repairs = decode_tags(alignment, tags)
            if repairs or before != alignment.to_dict() or {
                    (s.start, s.end, s.label) for s in restored} != {
                    (s["start"], s["end"], s["label"]) for s in row["spans"]}:
                raise ValueError("RAW_OFFSET_ALIGNMENT_ROUND_TRIP_FAILED:" + row["sample_id"])
            target, mask = t1_target(row, manifest)
            aligned[split].append((alignment, tags, target, mask))
            diagnostics.append({"sample_id": row["sample_id"], "split": split,
                                "status": "EXACT", "t1_mask": mask, "gold_span_count": len(restored)})
    write_jsonl(output / "alignment.jsonl", diagnostics)
    result = {"train": len(aligned["train"]), "dev": len(aligned["dev"]),
              "t1_eligible": {name: sum(int(row[-1]) for row in rows) for name, rows in aligned.items()},
              "test100": "NOT_INCLUDED_NOT_READ", "status": "EXACT_ALL_RELEASED_SAMPLES"}
    write_json(output / "alignment_report.json", result)
    return aligned, result


def one_model_smoke(config, lock, processor, examples, manifest, output):
    import torch
    from src.modeling.training import create_phobert_model, collate, checkpoint_metadata, set_seed
    set_seed(config["seed"], config["deterministic"])
    model = create_phobert_model(config, lock).to(config["device"])
    encoder_params = list(model.encoder.parameters())
    encoder_ids = {id(p) for p in encoder_params}
    optimizer = torch.optim.AdamW([
        {"params": encoder_params, "lr": config["candidate"]["encoder_lr"]},
        {"params": [p for p in model.parameters() if id(p) not in encoder_ids], "lr": config["candidate"]["head_lr"]},
    ], weight_decay=config["weight_decay"])
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda _: 1.0)
    group = examples[:config["micro_batch_size"]]
    batch = collate(group, processor, config["device"])
    if not config["t1_implemented"]:
        batch.pop("t1_targets")
        batch.pop("t1_mask")
    model.train()
    optimizer.zero_grad(set_to_none=True)
    result = model(**batch)
    loss = result["loss"]
    if not bool(torch.isfinite(loss)):
        raise RuntimeError("NONFINITE_SMOKE_LOSS")
    previous = model.emission.weight.detach().clone()
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), config["gradient_clip"])
    optimizer.step()
    scheduler.step()
    if torch.equal(previous, model.emission.weight.detach()):
        raise RuntimeError("SMOKE_OPTIMIZER_DID_NOT_UPDATE_WEIGHTS")
    optimizer.zero_grad(set_to_none=True)
    model.eval()
    inference_batch = {k: v for k, v in batch.items() if k not in {"tags", "t1_targets", "t1_mask"}}
    with torch.no_grad():
        expected = model(**inference_batch)["emissions"].detach().cpu()
    checkpoint = output / "smoke.pt"
    metadata = checkpoint_metadata(config, manifest, LOCK, epoch=0, global_step=1, resume_supported=True)
    metadata.update(purpose="integration_smoke_only", not_for_model_selection=True,
                    full_training_performed=False, pretrained=True)
    saved = save_checkpoint(checkpoint, model, metadata, optimizer, scheduler, {"smoke_only": True})
    with torch.no_grad():
        model.emission.weight.add_(1.0)
    load_checkpoint(checkpoint, config, config["corpus_manifest_sha256"], file_hash(LOCK),
                    model, optimizer, scheduler, resume=True)
    with torch.no_grad():
        restored = model(**inference_batch)["emissions"].detach().cpu()
    if not torch.allclose(expected, restored, atol=1e-6, rtol=1e-5):
        raise RuntimeError("PRETRAINED_CHECKPOINT_RELOAD_MISMATCH")
    value = {"status": "PRETRAINED_OPTIMIZER_CHECKPOINT_PASS", "model_id": config["model_id"],
             "optimizer_steps": 1, "smoke_batch_size": len(group), "loss": float(loss.detach()),
             "checkpoint_sha256": saved["checkpoint_sha256"], "checkpoint_bytes": checkpoint.stat().st_size,
             "device": config["device"], "pretrained": True, "purpose": "integration_smoke_only",
             "checkpoint_reload": "PASS", "t1_mask_used": config["t1_implemented"],
             "full_training_performed": False, "benchmark_metrics": "NOT_COMPUTED"}
    write_json(output / "smoke_model_report.json", value)
    del model, optimizer, scheduler, loss, result, batch, inference_batch, expected, restored, previous
    gc.collect()
    torch.cuda.empty_cache()
    return value


def run_smoke(output, mode="smoke"):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    report = {"status": "PREFLIGHT_PENDING", "mode": mode, "identity": evidence_identity(),
              "test100": "NOT_INCLUDED_NOT_READ", "full_training_performed": False, "models": {}}
    report_path = output / "smoke_report.json"
    try:
        configs = {name: checked_config(name) for name in CONFIGS}
        checks = {name: preflight(config, LOCK) for name, config in configs.items()}
        write_json(output / "preflight.json", checks)
        blockers = {name: result["blockers"] for name, result in checks.items() if result["blockers"]}
        if blockers:
            report.update(status="BLOCKED_PREFLIGHT", blockers=blockers)
            return report
        manifest, splits = load_corpus(CORPUS)
        lock = validate_resource_lock(LOCK, "PHOBERT-CRF")
        processor = load_phobert_processor(configs["PHOBERT-CRF"], lock)
        examples, alignment = audit_alignment(processor, manifest, splits, output)
        report["alignment"] = alignment
        if mode == "preflight":
            report["status"] = "PREFLIGHT_ALIGNMENT_PASS_SMOKE_NOT_RUN"
            return report
        for name, config in configs.items():
            directory = output / name.lower().replace("-", "_")
            directory.mkdir()
            report["models"][name] = one_model_smoke(config, lock, processor, examples["train"], manifest, directory)
            write_json(report_path, report)
        report["status"] = "SMOKE_PASS"
        return report
    except Exception as error:
        report.update(status="SMOKE_FAILED", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        write_json(report_path, report)


def run_full(output, smoke_evidence, enable_full=False, model_id="PHOBERT-CRF", candidate_id="c01"):
    if not enable_full:
        raise ValueError("FULL_TRAINING_DISABLED_BY_DEFAULT")
    validate_smoke_evidence(smoke_evidence)
    checked_config(model_id, candidate_id)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    for name in (model_id,):
        module = "scripts.32_train_phobert_crf" if name == "PHOBERT-CRF" else "scripts.33_train_proposed_dynamic"
        for candidate in (candidate_id,):
            import sys
            run_id = output.name + "_" + name.lower().replace("-", "_") + "_" + candidate
            run = ROOT / "data/processed/evaluation/sprint03" / run_id
            common = ["--resources", str(LOCK), "--hardware-profile", str(PROFILE), "--candidate", candidate]
            subprocess.run([sys.executable, "-m", module, "train", "--output-dir", str(run),
                            "--run-id", run_id] + common, cwd=ROOT, check=True)
            dev = run.with_name(run.name + "_dev")
            subprocess.run([sys.executable, "-m", module, "infer", "--checkpoint", str(run / "checkpoints/best.pt"),
                            "--output-dir", str(dev), "--inference-only"] + common, cwd=ROOT, check=True)
            subprocess.run([sys.executable, "-m", module, "score", "--source-run", str(dev)] + common, cwd=ROOT, check=True)
            if name == "PROPOSED-DYN":
                calibration = output / (candidate + "_calibration")
                subprocess.run([sys.executable, "-m", module, "calibrate", "--source-run", str(dev),
                                "--output-dir", str(calibration)] + common, cwd=ROOT, check=True)
                for variant in ("proposed_dyn_v1.json", "proposed_no_constraint_v1.json"):
                    ablation = dev.with_name(dev.name + "_" + variant.removesuffix(".json"))
                    config = ROOT / "configs/modeling/sprint03" / variant
                    subprocess.run([sys.executable, "-m", module, "infer", "--config", str(config),
                        "--checkpoint", str(run / "checkpoints/best.pt"), "--decoder-policy", str(calibration / "decoder_policy.json"),
                        "--output-dir", str(ablation), "--inference-only"] + common, cwd=ROOT, check=True)
                    subprocess.run([sys.executable, "-m", module, "score", "--config", str(config),
                                    "--source-run", str(ablation)] + common, cwd=ROOT, check=True)
    report = {"status": "FULL_TRAINING_DEV_ONLY_COMPLETE", "identity": evidence_identity(), "test100": "NOT_INCLUDED_NOT_READ"}
    write_json(output / "full_training_report.json", report)
    return report
