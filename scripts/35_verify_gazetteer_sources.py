"""Gazetteer source audit, exact dated reference verification and lookup."""

import argparse
import json
from pathlib import Path

from src.evaluation.dev_runner import ROOT
from src.data.administrative_code_verifier import audit_sources, TemporalGazetteerEvidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("audit", "lookup"))
    parser.add_argument("--gazetteer-dir", type=Path, default=ROOT / "data/processed/gazetteer/s3_v2")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--source-register", type=Path, default=ROOT / "configs/modeling/sprint03/gazetteer_source_register_v1.json")
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--reference-manifest", type=Path)
    parser.add_argument("--date", default="2025-06-30")
    parser.add_argument("--name")
    parser.add_argument("--level", choices=("province", "district", "ward"))
    parser.add_argument("--province")
    parser.add_argument("--district")
    args = parser.parse_args()
    if args.action == "lookup":
        if not args.name or not args.level:
            parser.error("--name and --level required")
        result = TemporalGazetteerEvidence(args.gazetteer_dir).lookup(args.name, args.level, args.date,
            {key: value for key, value in (("province", args.province), ("district", args.district)) if value})
    else:
        if args.output_dir is None:
            parser.error("--output-dir required")
        allowed = (ROOT / "data/interim/modeling/sprint03", ROOT / "data/interim/gazetteer")
        if not any(args.output_dir.resolve().is_relative_to(folder.resolve()) and args.output_dir.resolve() != folder.resolve() for folder in allowed):
            raise ValueError("AUDIT_OUTPUT_MUST_BE_NEW_INTERIM_VERSION; frozen package writes forbidden")
        result = audit_sources(args.gazetteer_dir, args.output_dir,
            json.loads(args.source_register.read_text(encoding="utf-8")), args.reference, args.reference_manifest, args.date)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
