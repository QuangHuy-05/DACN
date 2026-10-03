"""Run/score a new text-only five-field experiment, excluding 100 test rows."""

import argparse
import json
from pathlib import Path

from src.evaluation.benchmark_runner import run_fivefield_inference, score_fivefield_run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="stage", required=True)
    infer = sub.add_parser("infer")
    infer.add_argument("--config", type=Path, required=True)
    infer.add_argument("--output-dir", type=Path, required=True)
    infer.add_argument("--hold-manifest", type=Path, default=Path("data/interim/annotation/sprint03/test_hold_manifest_v1.json"))
    score = sub.add_parser("score")
    score.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.stage == "infer":
        report = run_fivefield_inference(json.loads(args.config.read_text(encoding="utf-8")), args.output_dir, args.hold_manifest)
        print(json.dumps({k: report[k] for k in ("run_id", "sample_count", "status_counts")}))
    else:
        report = score_fivefield_run(args.run_dir)
        print(json.dumps(report["overall"]))


if __name__ == "__main__":
    main()
