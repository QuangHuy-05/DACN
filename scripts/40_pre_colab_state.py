"""P0/U5 pre-Colab state: initial inventory, frozen ledger and ledger comparison.

Examples:
    python -m scripts.40_pre_colab_state snapshot --output-dir data/interim/modeling/sprint03/pre_colab_20261003_v1/p0
    python -m scripts.40_pre_colab_state compare --ledger .../p0/frozen_before.json --output .../frozen_after_compare.json
"""

import argparse
import json
from pathlib import Path

from src.evaluation.dev_runner import ROOT, write_json
from src.modeling.pre_colab import compare_ledger, frozen_ledger, load_json, write_p0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    snap = sub.add_parser("snapshot", help="write initial_state/frozen_before/input_availability")
    snap.add_argument("--output-dir", type=Path, required=True)
    cmp_ = sub.add_parser("compare", help="compare current bytes with a frozen ledger")
    cmp_.add_argument("--ledger", type=Path, required=True)
    cmp_.add_argument("--output", type=Path, required=True)
    cmp_.add_argument("--write-after-ledger", type=Path)
    args = parser.parse_args()
    if args.command == "snapshot":
        print(json.dumps(write_p0(ROOT / args.output_dir if not args.output_dir.is_absolute() else args.output_dir),
                         ensure_ascii=False, indent=2))
        return 0
    output = args.output if args.output.is_absolute() else ROOT / args.output
    if output.exists():
        raise FileExistsError(output)
    result = compare_ledger(load_json(args.ledger))
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, result)
    if args.write_after_ledger:
        after = args.write_after_ledger if args.write_after_ledger.is_absolute() else ROOT / args.write_after_ledger
        if after.exists():
            raise FileExistsError(after)
        write_json(after, frozen_ledger())
    print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in result.items()}, indent=2))
    return 0 if result["status"] == "FROZEN_LEDGER_PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
