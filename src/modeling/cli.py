"""Prepare/preflight/train/infer entry points; help does not import neural packages."""

import argparse
import json
from pathlib import Path

from src.evaluation.dev_runner import ROOT, build_adapter, file_hash, load_dev_input, run_dev_inference, score_dev_predictions, write_json
from src.evaluation.experiment_config import modeling_config
from src.modeling.artifacts import audit_run
from src.modeling.datasets import load_corpus, prepare_data
from src.modeling.protocol import load_config, candidate_config
from src.modeling.resources import preflight, validate_resource_lock, load_phobert_processor

CORPUS = ROOT / "data/processed/annotation/sprint03/corpus_train_dev_v2"


def validate_output_directory(path: Path, action: str) -> None:
    allowed = [ROOT / "data/interim/modeling/sprint03"]
    if action in ("train", "infer"):
        allowed.append(ROOT / "data/processed/evaluation/sprint03")
    if not any(path.resolve().is_relative_to(folder.resolve()) and path.resolve() != folder.resolve() for folder in allowed):
        raise ValueError("OUTPUT_MUST_BE_NEW_MODELING_OR_EVALUATION_RUN; frozen/raw/annotation/gazetteer writes forbidden")


def main(default_config: str):
    parser = argparse.ArgumentParser(description="Sprint 3 local-only modeling pipeline; no test100/auto downloads")
    parser.add_argument("action", choices=("prepare", "preflight", "train", "infer", "calibrate", "score"))
    parser.add_argument("--config", type=Path, default=ROOT / "configs/modeling/sprint03" / default_config)
    parser.add_argument("--corpus-dir", type=Path, default=CORPUS)
    parser.add_argument("--resources", type=Path)
    parser.add_argument("--hardware-profile", type=Path, help="Explicit versioned GPU overlay; preserves the locked training budget")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--candidate", choices=("c01", "c02"), default="c01")
    parser.add_argument("--run-id")
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--resume-from", type=Path)
    parser.add_argument("--weights-from", type=Path)
    parser.add_argument("--source-run", type=Path)
    parser.add_argument("--decoder-policy", type=Path)
    parser.add_argument("--inference-only", action="store_true", help="Freeze predictions; score in a separate invocation")
    args = parser.parse_args()
    for name in ("config", "corpus_dir", "resources", "hardware_profile", "output_dir", "checkpoint", "resume_from", "weights_from", "source_run", "decoder_policy"):
        value = getattr(args, name)
        if value is not None:
            setattr(args, name, value.resolve())
    if args.output_dir:
        validate_output_directory(args.output_dir, args.action)
    config = candidate_config(load_config(args.config), args.candidate)
    if args.hardware_profile:
        from src.modeling.hardware_profile import apply_hardware_profile
        config = apply_hardware_profile(config, args.hardware_profile)
    if args.action == "score":
        if args.source_run is None:
            parser.error("--source-run required for separate scoring")
        load_corpus(args.corpus_dir)
        validate_output_directory(args.source_run, "infer")
        metrics = score_dev_predictions(args.source_run / "predictions.jsonl", args.corpus_dir / "dev.jsonl", args.source_run, args.corpus_dir / "manifest.json")
        write_json(args.source_run / "completion_audit.json", audit_run(args.source_run, args.corpus_dir))
        print(json.dumps({"status": "DEV_SCORED", "t0": metrics["t0_exact_span"]["micro"]}))
        return 0
    if args.action == "preflight":
        result = preflight(config, args.resources)
        try:
            load_corpus(args.corpus_dir)
            result["corpus"] = "HASH_COUNT_PASS_240_60"
        except (OSError, ValueError, KeyError) as exc:
            result["status"] = "BLOCKED_INPUT_HASH"
            result["blockers"].append(str(exc))
        if args.output_dir:
            args.output_dir.mkdir(parents=True, exist_ok=False)
            write_json(args.output_dir / "preflight.json", result)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if not result["blockers"] else 2
    if args.output_dir is None:
        parser.error("--output-dir required for prepare/train/infer")
    if args.action == "calibrate":
        if args.source_run is None:
            parser.error("--source-run required for frozen dev calibration")
        from src.modeling.calibration import calibrate_frozen_dev
        print(json.dumps(calibrate_frozen_dev(args.source_run, args.corpus_dir, args.output_dir), ensure_ascii=False))
        return 0
    if args.action == "prepare":
        processor = None
        if args.resources and config["model_id"] != "DP-FT-FT":
            readiness = preflight(config, args.resources)
            if readiness["blockers"]:
                raise RuntimeError(str(readiness["blockers"]))
            processor = load_phobert_processor(config, validate_resource_lock(args.resources, config["model_id"]))
        print(json.dumps(prepare_data(args.corpus_dir, args.output_dir, processor), ensure_ascii=False))
        return 0
    if args.resources is None:
        parser.error("--resources required for train/infer; see inventory, no automatic installation")
    config["run_id"] = args.run_id or args.output_dir.name
    if args.action == "train":
        from src.modeling.training import train_model
        result = train_model(config, args.resources, args.corpus_dir, args.output_dir, args.resume_from, args.weights_from)
        print(json.dumps({"status": result["status"], "run": str(args.output_dir)}))
        return 0
    if args.checkpoint is None:
        parser.error("--checkpoint required for infer")
    load_corpus(args.corpus_dir)
    run_id = args.run_id or args.output_dir.name
    inferred = modeling_config(run_id, config, args.checkpoint, args.resources, args.decoder_policy)
    samples = load_dev_input(args.corpus_dir / "dev_input.jsonl", args.corpus_dir / "manifest.json")
    adapter = build_adapter(inferred)
    run_dev_inference(adapter, samples, inferred, args.output_dir,
        {"corpus_manifest_sha256": file_hash(args.corpus_dir / "manifest.json"),
         "dev_input_sha256": file_hash(args.corpus_dir / "dev_input.jsonl")})
    if args.inference_only:
        print(json.dumps({"status": "DEV_PREDICTIONS_FROZEN_NOT_SCORED", "run": str(args.output_dir)}))
        return 0
    # Prediction is now frozen. Only this stage reads dev gold.
    score_dev_predictions(args.output_dir / "predictions.jsonl", args.corpus_dir / "dev.jsonl", args.output_dir, args.corpus_dir / "manifest.json")
    write_json(args.output_dir / "completion_audit.json", audit_run(args.output_dir, args.corpus_dir))
    print(json.dumps({"status": "DEV_INFERENCE_SCORED", "run": str(args.output_dir)}))
    return 0
