"""Create benchmark sets from OSM and the authoritative 2025 mapping graph."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

# Allow ``python scripts/03_generate_benchmarks.py`` from the repository root.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.administrative_mapping import clean_value, load_administrative_mapping
from src.data.administrative_alias import normalize_diff_record
from src.data.coverage_reporter import generate_and_save_coverage_report
from src.data.synthetic.bidirectional import generate_bidirectional_pairs
from src.data.synthetic.hybrid_address import generate_hybrid_addresses
from src.data.synthetic.missing_fields import generate_missing_fields
from src.data.synthetic.raw_noisy import generate_raw_noisy_addresses


BENCHMARK_DIR = ROOT / "data" / "processed" / "benchmark"
FIELDS = ["SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh"]


def require_csv(path: Path, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    data = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    missing = set(columns) - set(data.columns)
    if missing:
        raise ValueError(f"{path}: missing columns {sorted(missing)}")
    return data


def _address_record(so_nha: object, ten_duong: object, target) -> dict[str, str]:
    return {
        "SoNha": clean_value(so_nha),
        "TenDuong": clean_value(ten_duong),
        "PhuongXa": target.ward,
        # The post-2025 benchmark is two-tier. A legacy district is never
        # erased merely to make a source row look current; it is omitted only
        # after a current ward is verified from the authoritative table.
        "QuanHuyen": "",
        "TinhThanh": target.province,
    }


def build_new_addresses(
    latest: pd.DataFrame, pairs: pd.DataFrame, mapping_path: Path
) -> pd.DataFrame:
    """Build confirmed post-2025 addresses without an XOR ward/district hack.

    A current row is accepted if its province and ward are a known current unit.
    A row still carrying old tags is converted only when its full old
    province/district/ward key has one target. The direct OSM-diff new side is
    accepted only after its stated target is found in the same mapping graph.
    """
    mapping = load_administrative_mapping(mapping_path)
    verified: list[dict[str, str]] = []

    for row in latest.to_dict("records"):
        if not clean_value(row.get("TenDuong")):
            continue
        target = mapping.target_for_new_unit(row.get("TinhThanh"), row.get("PhuongXa"))
        if target is None:
            targets = mapping.targets_for_old(
                row.get("TinhThanh"), row.get("QuanHuyen"), row.get("PhuongXa")
            )
            target = targets[0] if len(targets) == 1 else None
        if target is not None:
            verified.append(_address_record(row.get("SoNha"), row.get("TenDuong"), target))

    for raw_row in pairs.to_dict("records"):
        # Match current OSM tags through the same controlled alias layer used
        # by Set 07 and its audit; raw values remain available in the diff CSV.
        row = normalize_diff_record(raw_row)
        if not clean_value(row.get("TenDuong")):
            continue
        target = None
        for candidate in (row.get("PhuongXa_Moi"), row.get("QuanHuyen_Moi")):
            target = mapping.target_for_new_unit(row.get("TinhThanh_Moi"), candidate)
            if target is not None:
                break
        if target is not None:
            verified.append(_address_record(row.get("SoNha"), row.get("TenDuong"), target))

    pool = pd.DataFrame(verified, columns=FIELDS)
    if pool.empty:
        return pool.assign(ChuoiDiaChi=pd.Series(dtype=str))
    pool["ChuoiDiaChi"] = pool[FIELDS].apply(
        lambda row: ", ".join(value for value in row if value), axis=1
    )
    return pool.drop_duplicates(subset="ChuoiDiaChi").reset_index(drop=True)


def build_outputs() -> dict[str, pd.DataFrame]:
    old = require_csv(ROOT / "data/interim/osm/osm_old_snapshot_20250630.csv", FIELDS)
    latest = require_csv(ROOT / "data/interim/osm/osm_latest_clean.csv", FIELDS)
    pairs_path = ROOT / "data/processed/osm/osm_real_bidirectional_pairs.csv"
    pairs = require_csv(
        pairs_path,
        ["SoNha", "TenDuong", "PhuongXa_Moi", "QuanHuyen_Moi", "TinhThanh_Moi"],
    )
    mapping_path = ROOT / "data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv"
    load_administrative_mapping(mapping_path)  # Fail before writing partial benchmark files.
    noise = ROOT / "configs/noise_params.json"

    new = build_new_addresses(latest, pairs, mapping_path)
    if new.empty:
        raise ValueError("No verified post-2025 addresses")
    new_complete = new[
        new[["SoNha", "TenDuong", "PhuongXa", "TinhThanh"]]
        .apply(lambda col: col.astype(str).str.strip().ne(""))
        .all(axis=1)
    ].copy().drop_duplicates(subset="ChuoiDiaChi").reset_index(drop=True)
    if len(new_complete) < 1000:
        raise ValueError(f"Not enough complete new addresses for Data 01: {len(new_complete)}/1000")

    old_complete = old[
        old[["SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh"]]
        .apply(lambda col: col.astype(str).str.strip().ne(""))
        .all(axis=1)
    ].copy()
    old_complete["ChuoiDiaChi"] = old_complete[FIELDS].apply(
        lambda row: ", ".join(clean_value(value) for value in row if clean_value(value)), axis=1
    )
    old_complete = old_complete.drop_duplicates(subset="ChuoiDiaChi").reset_index(drop=True)
    if len(old_complete) < 1500:
        raise ValueError(f"Not enough complete legacy addresses for Data 03: {len(old_complete)}/1500")

    new_sample = new_complete.sample(n=1000, random_state=42).copy()
    new_sample["HeQuyChieu"] = "moi"
    old_sample = old_complete.sample(n=1500, random_state=42).copy()
    old_sample["HeQuyChieu"] = "cu"
    missing = generate_missing_fields(old_complete, new_complete, noise_params_path=noise, target_size=800, seed=42)
    raw_noisy = generate_raw_noisy_addresses(
        old_complete,
        new_complete,
        noise_params_path=noise,
        target_size=1000,
        ratio_old=0.5,
        seed=42,
    )
    hybrid = generate_hybrid_addresses(old_complete, mapping_path, target_size=600, seed=42)
    verified_pairs = generate_bidirectional_pairs(
        pairs_path,
        mapping_path,
        ROOT / "data/interim/osm/osm_old_snapshot_20250630.csv",
        target_size=600,
        full_snapshot_path=ROOT / "data/interim/osm/osm_old_snapshot_full.csv",
    )
    return {
        "01_full_address_new_verified.csv": new_sample,
        "02_raw_noisy_synthetic_1000.csv": raw_noisy,
        "03_real_address_old_1500.csv": old_sample,
        "04_missing_fields_800.csv": missing,
        "06_hybrid_addresses_600.csv": hybrid,
        "07_bidirectional_pairs_verified.csv": verified_pairs,
    }


def main() -> None:
    outputs = build_outputs()
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    for name, frame in outputs.items():
        path = BENCHMARK_DIR / name
        frame.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"{name}: {len(frame)} rows")
    pairs = outputs["07_bidirectional_pairs_verified.csv"]
    report_path = ROOT / "docs" / "benchmark_coverage_report.md"
    stats = generate_and_save_coverage_report(pairs, report_path)
    print(f"\nSaved coverage report to {report_path}")
    print(f"Set 07 Relationship counts: {stats['relationship_counts']}")
    print(f"Set 07 Source counts: {stats['source_counts']}")
    print(f"Set 07 Region counts: {stats['region_counts']}")
    print(f"Set 07 Geometry counts: {stats['geometry_counts']}")
    if stats["warnings"]:
        print("\n[Quality Warnings]:")
        for w in stats["warnings"]:
            print(f" - {w}")
    print("\nLandmark subset 05 is not generated: no verified landmark source is present.")


if __name__ == "__main__":
    main()
