"""Fetch/verify dated official NSO codes, publish a new package or look up an identity."""

import argparse
import json
from pathlib import Path

from src.data.nso_dual_snapshot import DualSnapshotGazetteer, fetch_catalog, publish_dual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    fetch = sub.add_parser("fetch")
    fetch.add_argument("--output-dir", type=Path, required=True)
    fetch.add_argument("--parent", type=Path, default=Path("data/processed/gazetteer/s3_v3_nso_2025_snapshot"))
    fetch.add_argument("--cached-dir", type=Path)
    release = sub.add_parser("publish")
    release.add_argument("--evidence-dir", type=Path, required=True)
    release.add_argument("--output-dir", type=Path, required=True)
    release.add_argument("--parent", type=Path, default=Path("data/processed/gazetteer/s3_v3_nso_2025_snapshot"))
    lookup = sub.add_parser("lookup")
    lookup.add_argument("--package", type=Path, required=True)
    lookup.add_argument("--name", required=True)
    lookup.add_argument("--level", choices=("province", "district", "ward"), required=True)
    lookup.add_argument("--date", required=True)
    lookup.add_argument("--province")
    lookup.add_argument("--district")
    lookup.add_argument("--system", choices=("cu", "moi"))
    args = parser.parse_args()
    if args.command == "fetch":
        result = fetch_catalog(args.output_dir.resolve(), args.parent.resolve(), args.cached_dir.resolve() if args.cached_dir else None)
    elif args.command == "publish":
        result = publish_dual(args.parent.resolve(), args.evidence_dir.resolve(), args.output_dir.resolve())
    else:
        context = {key: value for key, value in (("province", args.province), ("district", args.district)) if value}
        result = DualSnapshotGazetteer(args.package).lookup(args.name, args.level, args.date, context, args.system)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
