"""GPU entry point inside a verified private Kaggle train/dev workspace."""

import argparse
import json
from pathlib import Path

from src.modeling.kaggle_remote import run_smoke, run_full


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("preflight", "smoke", "full"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--allow-full-training", action="store_true")
    parser.add_argument("--smoke-evidence", type=Path)
    parser.add_argument("--model", choices=("PHOBERT-CRF", "PROPOSED-DYN"), default="PHOBERT-CRF")
    parser.add_argument("--candidate", choices=("c01", "c02"), default="c01")
    args = parser.parse_args()
    if args.mode == "full":
        result = run_full(args.output_dir, args.smoke_evidence, args.allow_full_training, args.model, args.candidate)
    else:
        result = run_smoke(args.output_dir, args.mode)
    print(json.dumps(result, ensure_ascii=False))
    if result["status"].startswith("BLOCKED"):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
