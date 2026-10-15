"""Score a frozen dev inference run separately from model execution."""

import argparse
import json
from pathlib import Path

from src.evaluation.dev_runner import score_dev_predictions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True, help="Frozen dev.jsonl")
    parser.add_argument("--corpus-manifest", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    metrics = score_dev_predictions(args.predictions, args.gold, args.run_dir, args.corpus_manifest)
    print(json.dumps({"metric_version": metrics["metric_version"], "t0_micro": metrics["t0_exact_span"]["micro"], "t1_total": metrics["t1_address_system"]["total_evaluated"]}))


if __name__ == "__main__":
    main()
