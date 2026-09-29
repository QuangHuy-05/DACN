"""Execute one versioned baseline run across all six benchmark datasets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
import pandas as pd
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evaluation.adapters.libpostal_adapter import LibpostalAdapter
from src.evaluation.adapters.vnadmin_adapter import VietnamAdminUnitsAdapter
from src.evaluation.data_contract import validate_benchmarks
from src.evaluation.manifest import build_manifest, compute_sha256
from src.evaluation.protocol import DATASET07_SCORED_FIELDS, scenario_for_dataset07
from src.evaluation.run_artifacts import RunArtifacts, prepare_run_directory, write_manifest
from src.evaluation.schema import UNIFIED_SCHEMA_COLUMNS
from src.evaluation.scorer import evaluate_record


BENCHMARK_DIR = ROOT / "data/processed/benchmark"
MAPPING_PATH = ROOT / "data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv"


def _load_new_targets_by_code(mapping_path: Path) -> dict[str, tuple[str, str]]:
    """Resolve official ward code to its canonical ward name and province."""
    if not mapping_path.exists():
        raise FileNotFoundError(mapping_path)
    mapping = pd.read_csv(
        mapping_path,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    )
    required = {
        "Mã phường/xã mới",
        "Phường/Xã mới (từ 1/7/2025)",
        "Tỉnh/TP mới",
    }
    missing = required - set(mapping.columns)
    if missing:
        raise ValueError(f"Administrative mapping missing columns: {sorted(missing)}")

    targets: dict[str, tuple[str, str]] = {}
    for row in mapping.to_dict("records"):
        code = str(row["Mã phường/xã mới"]).strip()
        ward = str(row["Phường/Xã mới (từ 1/7/2025)"]).strip()
        province = str(row["Tỉnh/TP mới"]).strip()
        if not code or not ward or not province:
            continue
        target = (ward, province)
        if code in targets and targets[code] != target:
            raise ValueError(f"Conflicting official target values for ward code {code}")
        targets[code] = target
    return targets


def run_full_evaluation(
    run_id: str,
    sample_per_dataset: int | None = None,
    overwrite: bool = False,
) -> RunArtifacts:
    """Run full or pilot evaluation in an isolated artifact directory."""
    artifacts = RunArtifacts(ROOT, run_id)
    prepare_run_directory(artifacts, overwrite=overwrite)
    print("Generating / verifying run manifest...")
    manifest = build_manifest(
        BENCHMARK_DIR,
        MAPPING_PATH,
        run_id=artifacts.run_id,
        run_kind="pilot" if sample_per_dataset is not None else "full",
    )
    validate_benchmarks(BENCHMARK_DIR, manifest)
    new_targets_by_code = _load_new_targets_by_code(MAPPING_PATH)

    vn_adapter = VietnamAdminUnitsAdapter()
    lp_adapter = LibpostalAdapter()

    def load_frame(name: str) -> pd.DataFrame:
        frame = pd.read_csv(BENCHMARK_DIR / name, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        if sample_per_dataset is None:
            return frame
        strata = {
            "02_raw_noisy_synthetic_1000.csv": ("HeQuyChieu", "MucDoNhieu"),
            "04_missing_fields_800.csv": ("HeQuyChieu", "KieuThieu"),
            "06_hybrid_addresses_600.csv": ("KieuLai",),
            "07_bidirectional_pairs_verified.csv": ("QuanHe",),
        }.get(name, ())
        if strata:
            representative = frame.groupby(list(strata), sort=True).sample(n=1, random_state=42)
        else:
            representative = frame.iloc[0:0]
        remaining = frame.drop(index=representative.index)
        extra = remaining.sample(n=max(0, sample_per_dataset - len(representative)), random_state=42)
        selected = pd.concat((representative, extra)).sort_index()
        print(f"Pilot {name}: {len(selected)} rows, strata={selected.groupby(list(strata)).ngroups if strata else 'random'}")
        return selected

    eval_records: list[dict] = []
    raw_logs: list[dict] = []

    def record_eval(eval_rec, raw_data, duration_ms):
        eval_records.append(eval_rec.to_dict())
        status = "exception" if isinstance(raw_data, dict) and "error" in raw_data else "success"
        raw_logs.append({
            "id": eval_rec.record_id,
            "tool": eval_rec.cong_cu,
            "input": eval_rec.dia_chi_goc,
            "dung_sai": eval_rec.dung_sai,
            "loai_loi": eval_rec.loai_loi,
            "scenario": eval_rec.tinh_huong_mo_ho,
            "raw_data": raw_data,
            "trace": raw_data.get("conversion_trace", {}) if isinstance(raw_data, dict) else {},
            "status": status,
            "duration_ms": round(duration_ms, 2),
        })

    # =========================================================================
    # 1. Dataset 01: 1,000 New Clean Addresses
    # =========================================================================
    print("\n--- Running Dataset 01: Full Address New Verified (1,000 rows) ---")
    df01 = load_frame("01_full_address_new_verified.csv")
    for idx, r in tqdm(df01.iterrows(), total=len(df01), desc="Data 01"):
        rid = f"D01_{idx:04d}"
        addr = r["ChuoiDiaChi"]
        truth = {f: r.get(f, "") for f in ("SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh")}

        # VNAdmin
        t0 = time.perf_counter()
        pred_vn, raw_vn = vn_adapter.parse(addr, mode="FROM_2025")
        t_vn = (time.perf_counter() - t0) * 1000
        eval_vn = evaluate_record(rid, addr, "vietnamadminunits", pred_vn, truth, scenario="NONE", extra_notes="mode=FROM_2025")
        record_eval(eval_vn, raw_vn, t_vn)

        # Libpostal
        t0 = time.perf_counter()
        pred_lp, raw_lp = lp_adapter.parse(addr)
        t_lp = (time.perf_counter() - t0) * 1000
        eval_lp = evaluate_record(rid, addr, lp_adapter.tool_name, pred_lp, truth, scenario="NONE")
        record_eval(eval_lp, raw_lp, t_lp)

    # =========================================================================
    # 2. Dataset 02: 1,000 Noisy vs Clean Paired Addresses
    # =========================================================================
    print("\n--- Running Dataset 02: Raw Noisy Synthetic (1,000 rows x 2 runs) ---")
    df02 = load_frame("02_raw_noisy_synthetic_1000.csv")
    for idx, r in tqdm(df02.iterrows(), total=len(df02), desc="Data 02"):
        rid = f"D02_{r.get('ID', f'{idx:04d}')}"
        truth = {
            "SoNha": r.get("GT_SoNha", ""),
            "TenDuong": r.get("GT_TenDuong", ""),
            "PhuongXa": r.get("GT_PhuongXa", ""),
            "QuanHuyen": r.get("GT_QuanHuyen", ""),
            "TinhThanh": r.get("GT_TinhThanh", ""),
        }
        addr_noisy = r["ChuoiDiaChi"]
        addr_clean = r["ChuoiDiaChiGoc"]
        mode = "FROM_2025" if r.get("HeQuyChieu") == "moi" else "LEGACY"
        noise_info = f"muc_do={r.get('MucDoNhieu')}|loai={r.get('LoaiNhieu')}"

        # VNAdmin Noisy
        t0 = time.perf_counter()
        pred_vn_n, raw_vn_n = vn_adapter.parse(addr_noisy, mode=mode)
        t_vn_n = (time.perf_counter() - t0) * 1000
        eval_vn_n = evaluate_record(f"{rid}_noisy", addr_noisy, "vietnamadminunits", pred_vn_n, truth, scenario="NONE", extra_notes=noise_info)
        record_eval(eval_vn_n, raw_vn_n, t_vn_n)

        # VNAdmin Clean
        t0 = time.perf_counter()
        pred_vn_c, raw_vn_c = vn_adapter.parse(addr_clean, mode=mode)
        t_vn_c = (time.perf_counter() - t0) * 1000
        eval_vn_c = evaluate_record(f"{rid}_clean", addr_clean, "vietnamadminunits", pred_vn_c, truth, scenario="NONE", extra_notes="clean_baseline")
        record_eval(eval_vn_c, raw_vn_c, t_vn_c)

        # Libpostal Noisy
        t0 = time.perf_counter()
        pred_lp_n, raw_lp_n = lp_adapter.parse(addr_noisy)
        t_lp_n = (time.perf_counter() - t0) * 1000
        eval_lp_n = evaluate_record(f"{rid}_noisy", addr_noisy, lp_adapter.tool_name, pred_lp_n, truth, scenario="NONE", extra_notes=noise_info)
        record_eval(eval_lp_n, raw_lp_n, t_lp_n)

        # Libpostal Clean
        t0 = time.perf_counter()
        pred_lp_c, raw_lp_c = lp_adapter.parse(addr_clean)
        t_lp_c = (time.perf_counter() - t0) * 1000
        eval_lp_c = evaluate_record(f"{rid}_clean", addr_clean, lp_adapter.tool_name, pred_lp_c, truth, scenario="NONE", extra_notes="clean_baseline")
        record_eval(eval_lp_c, raw_lp_c, t_lp_c)

    # =========================================================================
    # 3. Dataset 03: 1,500 Real OSM Old Addresses
    # =========================================================================
    print("\n--- Running Dataset 03: Real Address Old (1,500 rows) ---")
    df03 = load_frame("03_real_address_old_1500.csv")
    for idx, r in tqdm(df03.iterrows(), total=len(df03), desc="Data 03"):
        rid = f"D03_{idx:04d}"
        addr = r["ChuoiDiaChi"]
        truth = {f: r.get(f, "") for f in ("SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh")}

        # VNAdmin LEGACY
        t0 = time.perf_counter()
        pred_vn, raw_vn = vn_adapter.parse(addr, mode="LEGACY")
        t_vn = (time.perf_counter() - t0) * 1000
        eval_vn = evaluate_record(rid, addr, "vietnamadminunits", pred_vn, truth, scenario="NONE", extra_notes="mode=LEGACY")
        record_eval(eval_vn, raw_vn, t_vn)

        # Libpostal
        t0 = time.perf_counter()
        pred_lp, raw_lp = lp_adapter.parse(addr)
        t_lp = (time.perf_counter() - t0) * 1000
        eval_lp = evaluate_record(rid, addr, lp_adapter.tool_name, pred_lp, truth, scenario="NONE")
        record_eval(eval_lp, raw_lp, t_lp)

    # =========================================================================
    # 4. Dataset 04: 800 Missing Fields Addresses
    # =========================================================================
    print("\n--- Running Dataset 04: Missing Fields (800 rows) ---")
    df04 = load_frame("04_missing_fields_800.csv")
    for idx, r in tqdm(df04.iterrows(), total=len(df04), desc="Data 04"):
        rid = f"D04_{idx:04d}"
        addr = r["ChuoiDiaChi"]
        # Extraction is scored against fields still present on the surface.
        # GT_* is reserved for a separate recovery analysis in the report.
        truth = {f: r.get(f, "") for f in ("SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh")}
        mode = "FROM_2025" if r.get("HeQuyChieu") == "moi" else "LEGACY"
        kieu_thieu = r.get("KieuThieu", "")

        t0 = time.perf_counter()
        pred_vn, raw_vn = vn_adapter.parse(addr, mode=mode)
        t_vn = (time.perf_counter() - t0) * 1000
        eval_vn = evaluate_record(rid, addr, "vietnamadminunits", pred_vn, truth, scenario="NONE", extra_notes=f"kieu_thieu={kieu_thieu}")
        record_eval(eval_vn, raw_vn, t_vn)

        t0 = time.perf_counter()
        pred_lp, raw_lp = lp_adapter.parse(addr)
        t_lp = (time.perf_counter() - t0) * 1000
        eval_lp = evaluate_record(rid, addr, lp_adapter.tool_name, pred_lp, truth, scenario="NONE", extra_notes=f"kieu_thieu={kieu_thieu}")
        record_eval(eval_lp, raw_lp, t_lp)

    # =========================================================================
    # 5. Dataset 06: 600 Hybrid Addresses (Both Modes for VNAdmin)
    # =========================================================================
    print("\n--- Running Dataset 06: Hybrid Addresses (600 rows x 3 runs) ---")
    df06 = load_frame("06_hybrid_addresses_600.csv")
    for idx, r in tqdm(df06.iterrows(), total=len(df06), desc="Data 06"):
        rid = f"D06_{idx:04d}"
        addr = r["ChuoiDiaChi"]
        truth = {f: r.get(f, "") for f in ("SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh")}
        kieu_lai = r.get("KieuLai", "")

        # VNAdmin mode FROM_2025
        t0 = time.perf_counter()
        pred_vn_25, raw_vn_25 = vn_adapter.parse(addr, mode="FROM_2025")
        t_vn_25 = (time.perf_counter() - t0) * 1000
        eval_vn_25 = evaluate_record(f"{rid}_m25", addr, "vietnamadminunits", pred_vn_25, truth, scenario="C", extra_notes=f"kieu_lai={kieu_lai}_mode=FROM_2025")
        record_eval(eval_vn_25, raw_vn_25, t_vn_25)

        # VNAdmin mode LEGACY
        t0 = time.perf_counter()
        pred_vn_leg, raw_vn_leg = vn_adapter.parse(addr, mode="LEGACY")
        t_vn_leg = (time.perf_counter() - t0) * 1000
        eval_vn_leg = evaluate_record(f"{rid}_mleg", addr, "vietnamadminunits", pred_vn_leg, truth, scenario="C", extra_notes=f"kieu_lai={kieu_lai}_mode=LEGACY")
        record_eval(eval_vn_leg, raw_vn_leg, t_vn_leg)

        # Libpostal
        t0 = time.perf_counter()
        pred_lp, raw_lp = lp_adapter.parse(addr)
        t_lp = (time.perf_counter() - t0) * 1000
        eval_lp = evaluate_record(rid, addr, lp_adapter.tool_name, pred_lp, truth, scenario="C", extra_notes=f"kieu_lai={kieu_lai}")
        record_eval(eval_lp, raw_lp, t_lp)

    # =========================================================================
    # 6. Dataset 07: 600 Bidirectional Reform Pairs
    # =========================================================================
    print("\n--- Running Dataset 07: Bidirectional Reform Pairs (600 rows) ---")
    df07 = load_frame("07_bidirectional_pairs_verified.csv")
    for idx, r in tqdm(df07.iterrows(), total=len(df07), desc="Data 07"):
        rel = r.get("QuanHe", "")
        rid = f"D07_{idx:04d}_{rel}"
        addr_old = r["DiaChi_Cu"]
        addr_new = r["DiaChi_Moi"]

        # Ground truth comes from the authoritative target code, not CSV text splitting.
        target_code = str(r.get("MaPhuongXaMoi", "")).strip()
        if target_code not in new_targets_by_code:
            raise ValueError(
                f"Data 07 target code {target_code!r} is missing from the official mapping"
            )
        target_ward, target_province = new_targets_by_code[target_code]
        truth_new = {"PhuongXa": target_ward, "TinhThanh": target_province}

        scenario = scenario_for_dataset07(rel)

        # VNAdmin Convert Old -> 2025
        t0 = time.perf_counter()
        pred_vn_conv, raw_vn_conv = vn_adapter.convert_to_2025(addr_old)
        t_vn_conv = (time.perf_counter() - t0) * 1000
        eval_vn_conv = evaluate_record(
            rid,
            addr_old,
            "vietnamadminunits",
            pred_vn_conv,
            truth_new,
            scenario=scenario,
            extra_notes=f"relation={rel}|direction=old_to_new|convert_2025",
            scored_fields=DATASET07_SCORED_FIELDS,
        )
        record_eval(eval_vn_conv, raw_vn_conv, t_vn_conv)

    # Save Unified Predictions CSV
    df_eval = pd.DataFrame(eval_records, columns=UNIFIED_SCHEMA_COLUMNS)
    df_eval.to_csv(artifacts.predictions_path, index=False, encoding="utf-8-sig")
    print(f"\n[DONE] Saved {len(df_eval)} unified evaluation records to {artifacts.predictions_path}")

    # Save Raw Responses JSONL
    with open(artifacts.raw_log_path, "w", encoding="utf-8") as f:
        for item in raw_logs:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"[DONE] Saved {len(raw_logs)} raw responses to {artifacts.raw_log_path}")
    manifest["output_hashes"] = {
        artifacts.predictions_path.name: compute_sha256(artifacts.predictions_path),
        artifacts.raw_log_path.name: compute_sha256(artifacts.raw_log_path),
    }
    manifest["output_row_counts"] = {
        artifacts.predictions_path.name: len(df_eval),
        artifacts.raw_log_path.name: len(raw_logs),
    }
    write_manifest(artifacts.manifest_path, manifest)
    print(f"[DONE] Wrote manifest to {artifacts.manifest_path}")
    return artifacts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a versioned full baseline evaluation.")
    parser.add_argument("--run-id", required=True, help="Unique lowercase run identifier, e.g. baseline_v2")
    parser.add_argument("--overwrite-run", action="store_true", help="Explicitly allow replacing files in an existing run directory")
    args = parser.parse_args()
    run_full_evaluation(run_id=args.run_id, overwrite=args.overwrite_run)
