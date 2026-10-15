"""Prepare reviewed train/dev v2 from immutable export/converter snapshots."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.data.annotation_release import prepare_release

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-dir", type=Path, required=True)
    parser.add_argument("--assignments", type=Path, default=ROOT / "data/interim/annotation/sprint03/split_preflight_review_20261001/train_dev_split_assignments.csv")
    parser.add_argument("--decisions", type=Path, default=ROOT / "data/interim/annotation/sprint03/split_preflight_v1/near_duplicate_decisions.csv")
    parser.add_argument("--attestation", type=Path, required=True)
    parser.add_argument("--manual-review", type=Path, help="Hash-bound additional content findings; does not override QA rules")
    parser.add_argument("--adjudications", type=Path, help="Direct human decisions bound to export and annotation hashes; retained time conflicts are excluded from T1")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = prepare_release(ROOT, args.review_dir.resolve(), args.assignments.resolve(),
                             args.decisions.resolve(), args.attestation.resolve(), args.output_dir.resolve(),
                             args.manual_review.resolve() if args.manual_review else None,
                             args.adjudications.resolve() if args.adjudications else None)
    print(json.dumps({key: report[key] for key in ("status", "sample_counts", "quarantined_sample_count", "near_duplicate_decisions_count")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
