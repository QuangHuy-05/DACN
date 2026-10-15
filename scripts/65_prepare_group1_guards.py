"""Run the leakage guard on Data 01/03/04/06 and write ``exclusion_report.json``.

Usage (from the repository root, main venv):
    python -m scripts.65_prepare_group1_guards

The guard only reads the frozen Sprint 3 corpus and the benchmark CSVs.  The
output directory is versioned; an existing directory is never overwritten.
Exit code 2 means the exact-match overlap counts did not reproduce.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import pandas as pd

from src.data.administrative_mapping import default_mapping_path
from src.evaluation.leak_guard import (
    DEFAULT_CORPUS_DIR,
    REASON_EXACT,
    REASON_NORMALIZED,
    RULE_VERSION,
    admin_group_key,
    build_exclusion_index,
    filter_benchmark,
    sha256_file,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = Path("data/interim/modeling/sprint04/group1_guards_20261013_v1")
BENCHMARK_DIR = Path("data/processed/benchmark")

# dataset -> (file, columns for the administrative group key)
DATASETS = {
    "data01": ("01_full_address_new_verified.csv", ("TinhThanh", "QuanHuyen", "PhuongXa")),
    "data03": ("03_real_address_old_1500.csv", ("TinhThanh", "QuanHuyen", "PhuongXa")),
    # Data 04 drops fields in the visible columns; GT_* keep the full address.
    "data04": ("04_missing_fields_800.csv", ("GT_TinhThanh", "GT_QuanHuyen", "GT_PhuongXa")),
    "data06": ("06_hybrid_addresses_600.csv", ("TinhThanh", "QuanHuyen", "PhuongXa")),
}
TEXT_COLUMN = "ChuoiDiaChi"
# Exact (raw string) overlap with the whole 400-sample corpus, measured 13/10/2026.
EXPECTED_EXACT_OVERLAP = {"data01": 20, "data03": 21, "data04": 21, "data06": 20}


def load_csv(path: Path, extra_columns: tuple[str, ...]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    missing = [c for c in (TEXT_COLUMN, *extra_columns) if c not in frame.columns]
    if missing:
        raise ValueError(f"{path}: missing required columns {missing}")
    return frame


def group_summary(frame: pd.DataFrame, columns: tuple[str, ...]) -> dict:
    province, district, ward = columns
    keys = [
        admin_group_key(row[province], row[district], row[ward])
        for row in frame[list(columns)].to_dict("records")
    ]
    unresolved = sum(key.startswith("UNRESOLVED|") for key in keys)
    return {
        "rows": len(keys),
        "distinct_groups": len(set(keys)),
        "rows_with_unresolved_group": unresolved,
        "largest_group_rows": max(Counter(keys).values()) if keys else 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    if output.exists():
        raise SystemExit(f"{output} already exists; refusing to overwrite. Use a _v2 directory.")

    index = build_exclusion_index(("train", "dev", "test"), ROOT / DEFAULT_CORPUS_DIR)
    exact_texts = index.exact_raw_texts()
    inputs: dict[str, str] = {
        f"corpus/{name}": digest for name, digest in index.corpus_sha256.items()
    }
    inputs["corpus/manifest.json"] = sha256_file(ROOT / DEFAULT_CORPUS_DIR / "manifest.json")
    inputs["reference/vietnam-sap-nhap-phuong-xa.csv"] = sha256_file(default_mapping_path())

    datasets, rows_in, rows_out, reproduced = {}, 0, 0, True
    for name, (filename, group_columns) in DATASETS.items():
        path = ROOT / BENCHMARK_DIR / filename
        frame = load_csv(path, group_columns)
        inputs[f"benchmark/{filename}"] = sha256_file(path)
        kept, dropped = filter_benchmark(frame, TEXT_COLUMN, ("train", "dev", "test"), index)
        exact_count = int(frame[TEXT_COLUMN].isin(exact_texts).sum())
        match = exact_count == EXPECTED_EXACT_OVERLAP[name]
        reproduced &= match
        rows_in += len(frame)
        rows_out += len(kept)
        datasets[name] = {
            "file": filename,
            "rows_in": len(frame),
            "rows_kept": len(kept),
            "rows_dropped": len(dropped),
            "exact_match_overlap": exact_count,
            "exact_match_expected": EXPECTED_EXACT_OVERLAP[name],
            "exact_match_reproduced": match,
            "dropped_by_reason": dict(Counter(dropped["LyDoLoai"])),
            "dropped_by_split": dict(Counter(dropped["SplitGayTrung"])),
            "admin_group_all_rows": group_summary(frame, group_columns),
            "admin_group_kept_rows": group_summary(kept, group_columns),
            "dropped_rows": [
                {
                    "row_index": int(i),  # 0-based position in the CSV body
                    "text": row[TEXT_COLUMN],
                    "reason": row["LyDoLoai"],
                    "split": row["SplitGayTrung"],
                    "sample_id": row["SampleIdGayTrung"],
                    "normalized_key": row["KhoaChuanHoa"],
                }
                for i, row in dropped.iterrows()
            ],
        }

    report = {
        "rule_version": RULE_VERSION,
        "reasons": {REASON_EXACT: "raw string equals a corpus text",
                    REASON_NORMALIZED: "equal only after NFC/casefold/punctuation/whitespace normalisation"},
        "normalization": "NFC, casefold, punctuation and symbols removed, whitespace collapsed; diacritics kept",
        "splits_checked": ["train", "dev", "test"],
        "status": "PASS" if reproduced else "REPRODUCTION_MISMATCH",
        "datasets": datasets,
    }
    output.mkdir(parents=True)
    (output / "exclusion_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    code_files = ("src/evaluation/leak_guard.py", "src/data/administrative_mapping.py",
                  "scripts/65_prepare_group1_guards.py")
    manifest = {
        "run": "group1_guards_20261013_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "rule_version": RULE_VERSION,
        "seed": None,  # no sampling is performed
        "seed_note": "deterministic; no random operation",
        "input_sha256": inputs,
        "code_sha256": {name: sha256_file(ROOT / name) for name in code_files},
        "rows_in": rows_in,
        "rows_out": rows_out,
        "output_sha256": {"exclusion_report.json": sha256_file(output / "exclusion_report.json")},
    }
    (output / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for name, info in datasets.items():
        print(f"{name}: in={info['rows_in']} kept={info['rows_kept']} dropped={info['rows_dropped']} "
              f"exact={info['exact_match_overlap']} (expected {info['exact_match_expected']})")
    print(report["status"])
    return 0 if reproduced else 2


if __name__ == "__main__":
    sys.exit(main())
