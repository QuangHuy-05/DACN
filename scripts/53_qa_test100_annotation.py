"""QA a raw Label Studio test export without training, tuning or scoring models."""

import argparse
import json
from pathlib import Path

from src.data.test_annotation_qa import review_test_export


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--queue", type=Path, default=Path("data/interim/annotation/sprint03/annotation_queue_batch01.csv"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--assisted-manifest", type=Path,
                        help="Explicitly opt into the authorized AI-assisted test annotation protocol")
    parser.add_argument("--adjudication-map", type=Path)
    args = parser.parse_args()
    result = review_test_export(args.export, args.queue, args.output_dir,
                               args.assisted_manifest, args.adjudication_map)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] in {"STRUCTURE_FAILED", "SOURCE_EXPORT_CHANGED_DURING_QA"}:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
