"""Read-only source reconciliation and frozen baseline taxonomy."""
import argparse
import json
from pathlib import Path

from src.evaluation.dev_runner import ROOT
from src.data.source_reconciliation import reconcile_existing
from src.evaluation.frozen_error_analysis import analyze_frozen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('source', 'baseline'))
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    allowed = ROOT / 'data/interim/modeling/sprint03'
    if not args.output_dir.resolve().is_relative_to(allowed.resolve()) or args.output_dir.resolve() == allowed.resolve():
        raise ValueError('NEW_INTERIM_VERSION_REQUIRED')
    result = (reconcile_existing if args.action == 'source' else analyze_frozen)(ROOT, args.output_dir)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
