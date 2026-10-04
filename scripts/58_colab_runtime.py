"""Future Colab GPU preflight/smoke, explicit training, and dev-only selection."""
import argparse
import json
from pathlib import Path
from src.modeling.colab_runtime import run_smoke, run_candidate, select_and_lock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preflight", "smoke", "train", "select"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--smoke-evidence", type=Path)
    parser.add_argument("--enable-neural-training", action="store_true")
    parser.add_argument("--model", choices=("PHOBERT-CRF", "PROPOSED-DYN"))
    parser.add_argument("--candidate", choices=("c01", "c02"), default="c01")
    parser.add_argument("--backup-directory", type=Path)
    parser.add_argument("--resume-from", type=Path)
    parser.add_argument("--dev-runs", type=Path, nargs="+")
    args = parser.parse_args()
    if args.action in {"preflight", "smoke"}:
        result = run_smoke(args.output_dir, args.action)
    elif args.action == "train":
        if not args.model or not args.smoke_evidence or not args.backup_directory:
            parser.error("train needs --model, --smoke-evidence and --backup-directory")
        result = run_candidate(args.output_dir, args.smoke_evidence, args.model, args.candidate,
            enable_training=args.enable_neural_training, backup_directory=args.backup_directory, resume_from=args.resume_from)
    else:
        if not args.model or not args.dev_runs:
            parser.error("select needs --model and both --dev-runs")
        result = select_and_lock(args.model, args.dev_runs, args.output_dir)
    print(json.dumps(result, ensure_ascii=False))
    return 2 if result["status"].startswith("BLOCKED") else 0


if __name__ == "__main__":
    raise SystemExit(main())
