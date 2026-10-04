"""Build the explicitly authorized test100 AI-assisted review package; never gold."""

import argparse
import json
from pathlib import Path

from src.data.test_assisted_annotation import ROOT, write_package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposals", type=Path, default=ROOT / "data/interim/annotation/sprint03/test100_assisted_inputs_v1/span_proposals.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/interim/annotation/sprint03/test100_assisted_v1")
    parser.add_argument("--acknowledge-assisted-test", action="store_true",
                        help="Explicitly acknowledge the owner-authorized assisted annotation amendment")
    args = parser.parse_args()
    counts = write_package(args.output_dir, args.proposals, args.acknowledge_assisted_test)
    print(json.dumps({"status": "CANDIDATES_PENDING_HUMAN_REVIEW", "counts": counts,
                      "output_dir": str(args.output_dir)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
