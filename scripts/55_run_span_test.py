"""Freeze dev selection, preflight, or explicitly execute final text-only inference."""

import argparse
import json
from pathlib import Path
from src.evaluation.test_runner import freeze_dev_selection, preflight_test, run_test_inference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("lock", "preflight", "infer"))
    parser.add_argument("--model-config", type=Path, required=True)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--corpus-manifest", type=Path)
    parser.add_argument("--selection-lock", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--output-lock", type=Path)
    parser.add_argument("--dev-runs", type=Path, nargs="+")
    parser.add_argument("--train-dev-manifest", type=Path, default=Path("data/processed/annotation/sprint03/corpus_train_dev_v2/manifest.json"))
    parser.add_argument("--execute-final-test", action="store_true")
    args = parser.parse_args()
    if args.action == "lock":
        if not args.dev_runs or not args.output_lock:
            parser.error("lock requires --dev-runs and --output-lock")
        result = freeze_dev_selection(args.model_config, args.dev_runs, args.train_dev_manifest, args.output_lock)
        print(json.dumps({"status": result["status"], "selected_dev_run": result["selected_dev_run"]}))
        return
    if not all((args.input, args.corpus_manifest, args.selection_lock)):
        parser.error("preflight/infer require --input, --corpus-manifest and --selection-lock")
    if args.action == "preflight":
        _, samples, config, _ = preflight_test(args.input, args.corpus_manifest, args.model_config, args.selection_lock)
        print(json.dumps({"status": "FINAL_TEST_PREFLIGHT_PASS", "model_id": config["model_id"], "count": len(samples), "inference": "NOT_EXECUTED"}))
    else:
        if not args.execute_final_test or not args.output_dir:
            parser.error("infer requires --execute-final-test and a new --output-dir; local preparation does not execute test")
        allowed = (Path("data/interim/modeling/sprint03"), Path("data/processed/evaluation/sprint03"))
        if not any(args.output_dir.resolve().is_relative_to(path.resolve()) and args.output_dir.resolve() != path.resolve() for path in allowed):
            parser.error("test run output must be a new modeling/evaluation directory")
        result = run_test_inference(args.input, args.corpus_manifest, args.model_config, args.selection_lock, args.output_dir)
        print(json.dumps({"status": "TEST_PREDICTIONS_FROZEN", "sample_count": result["sample_count"]}))


if __name__ == "__main__":
    main()
