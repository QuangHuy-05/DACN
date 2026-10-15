"""Score frozen final-test predictions; never recalibrate or modify predictions."""

import argparse
import json
from pathlib import Path
from src.evaluation.test_runner import score_test_predictions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--corpus-manifest", type=Path, required=True)
    parser.add_argument("--execute-final-test", action="store_true")
    args = parser.parse_args()
    if not args.execute_final_test:
        parser.error("scoring real test is a final-phase operation; pass --execute-final-test then")
    result = score_test_predictions(args.run_dir, args.gold, args.corpus_manifest, args.input)
    print(json.dumps({"status": "FINAL_TEST_SCORED", "t0": result["t0_exact_span"]["micro"]}))


if __name__ == "__main__":
    main()
