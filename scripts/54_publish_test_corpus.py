"""Prepare test candidate or publish approved corpus; never overwrite or edit raw labels."""

import argparse
import json
from pathlib import Path
from src.data.test_corpus_release import prepare_test_release, publish_test_corpus


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "publish"))
    parser.add_argument("--qa-dir", type=Path, required=True)
    parser.add_argument("--queue", type=Path, default=Path("data/interim/annotation/sprint03/annotation_queue_batch01.csv"))
    parser.add_argument("--hold-manifest", type=Path, default=Path("data/interim/annotation/sprint03/test_hold_manifest_v1.json"))
    parser.add_argument("--assisted-manifest", type=Path, default=Path("data/interim/annotation/sprint03/test100_assisted_v1/manifest.json"))
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--manual-findings", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--train-dev-dir", type=Path, default=Path("data/processed/annotation/sprint03/corpus_train_dev_v2"))
    parser.add_argument("--assignment", type=Path, default=Path("data/interim/annotation/sprint03/split_preflight_review_20261001/train_dev_split_assignments.csv"))
    parser.add_argument("--near-duplicate-decisions", type=Path, default=Path("data/interim/annotation/sprint03/split_preflight_v1/near_duplicate_decisions.csv"))
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--review-decisions", type=Path)
    parser.add_argument("--test-output-dir", type=Path)
    args = parser.parse_args()
    common = dict(qa_dir=args.qa_dir, queue_path=args.queue, hold_path=args.hold_manifest,
                  assisted_manifest_path=args.assisted_manifest, output_dir=args.output_dir,
                  selection_path=args.selection, manual_findings_path=args.manual_findings)
    if args.action == "prepare":
        result = prepare_test_release(**common)
    else:
        if not args.approval or not args.review_decisions:
            parser.error("publish requires --approval and --review-decisions")
        if not args.output_dir.resolve().is_relative_to(Path("data/processed/annotation/sprint03").resolve()):
            parser.error("release must be under processed/annotation/sprint03")
        if args.test_output_dir and not args.test_output_dir.resolve().is_relative_to(Path("data/processed/annotation/sprint03").resolve()):
            parser.error("test release must be under processed/annotation/sprint03")
        result = publish_test_corpus(**common, train_dev_dir=args.train_dev_dir,
            assignment_path=args.assignment, decisions_path=args.near_duplicate_decisions,
            approval_path=args.approval, review_decisions_path=args.review_decisions, test_output_dir=args.test_output_dir)
    print(json.dumps({key: result[key] for key in ("status", "sample_counts", "sample_count") if key in result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
