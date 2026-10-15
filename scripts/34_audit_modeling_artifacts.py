"""Read-only audit: never rescoring or altering a frozen artifact."""

import argparse
import json
from pathlib import Path

from src.modeling.artifacts import audit_run, audit_prepared, frozen_snapshot, compare_snapshot
from src.modeling.cli import CORPUS, validate_output_directory
from src.evaluation.dev_runner import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("snapshot", "compare", "run", "prepared"))
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--corpus-dir", type=Path, default=CORPUS)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    validate_output_directory(args.output, "preflight")
    if args.output.exists():
        raise FileExistsError(args.output)
    if args.action == "snapshot":
        result = frozen_snapshot()
    elif args.action == "compare":
        if args.snapshot is None:
            parser.error("--snapshot required")
        result = compare_snapshot(json.loads(args.snapshot.read_text(encoding="utf-8")))
    else:
        if args.run_dir is None:
            parser.error("--run-dir required")
        result = audit_prepared(args.run_dir, args.corpus_dir) if args.action == "prepared" else audit_run(args.run_dir, args.corpus_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, result)
    print(json.dumps({key: val for key, val in result.items() if key != "files"}, ensure_ascii=False))
    return int(result.get("status") in ("AUDIT_FAIL", "ALIGNMENT_AUDIT_FAIL", "BLOCKED_FROZEN_HASH"))


if __name__ == "__main__":
    raise SystemExit(main())
