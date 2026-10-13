"""Publish an approved train/dev candidate into a new processed version."""

import argparse
import json
from pathlib import Path

from src.data.annotation_release import publish_release

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = publish_release(ROOT, args.candidate_dir, args.output_dir)
    print(json.dumps({key: manifest[key] for key in ("version", "status", "sample_counts", "test_status")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
