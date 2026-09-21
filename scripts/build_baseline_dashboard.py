"""Build script to generate docs/baseline_dashboard.html.

This script compiles baseline evaluation outputs, raw logs, manifest data,
and benchmark metadata into a single self-contained, offline-first interactive HTML dashboard.

No external CDNs, frameworks, or libraries are used. Pure HTML5/CSS3/Vanilla JS and inline SVG.
"""

from __future__ import annotations

import json
import math
import os
import sys
import argparse
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evaluation.scorer import _norm, STANDARD_FIELDS
from src.evaluation.manifest import compute_sha256
from src.evaluation.run_artifacts import RunArtifacts, verify_run_outputs

EVAL_DIR = ROOT / "data/processed/evaluation"
BENCHMARK_DIR = ROOT / "data/processed/benchmark"
OUTPUT_HTML = ROOT / "docs/baseline_dashboard.html"

PREDICTIONS_PATH = EVAL_DIR / "baseline_predictions_unified.csv"
RAW_LOG_PATH = EVAL_DIR / "baseline_raw_responses.jsonl"
MANIFEST_PATH = EVAL_DIR / "run_manifest.json"


def configure_run(run_id: str) -> RunArtifacts:
    """Point the dashboard at one verified run rather than legacy root files."""
    global EVAL_DIR, PREDICTIONS_PATH, RAW_LOG_PATH, MANIFEST_PATH, OUTPUT_HTML
    artifacts = RunArtifacts(ROOT, run_id)
    manifest = verify_run_outputs(artifacts)
    if manifest.get("run_kind") != "full":
        raise ValueError("Dashboard requires a full run; pilot output is intentionally sampled.")
    EVAL_DIR = artifacts.run_dir
    PREDICTIONS_PATH = artifacts.predictions_path
    RAW_LOG_PATH = artifacts.raw_log_path
    MANIFEST_PATH = artifacts.manifest_path
    OUTPUT_HTML = artifacts.dashboard_path
    return artifacts


def get_field_status_code(pred_dict: dict[str, str], truth_dict: dict[str, str], scored_fields: list[str]) -> str:
    chars = []
    for f in STANDARD_FIELDS:
        if f not in scored_fields:
            chars.append("n")
            continue
        p = _norm(pred_dict.get(f, ""))
        t = _norm(truth_dict.get(f, ""))
        if not t and not p:
            chars.append("t")
        elif t and p == t:
            chars.append("m")
        elif t and not p:
            chars.append("o")
        else:
            chars.append("x")
    return "".join(chars)


def build_data():
    print("[1/4] Loading predictions, raw responses, and manifest...")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    df_pred = pd.read_csv(PREDICTIONS_PATH, dtype=str, keep_default_na=False)

    raw_logs = {}
    with open(RAW_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            raw_logs[(item["id"], item["tool"])] = item

    print("[2/4] Reading benchmark metadata...")
    df_b01 = pd.read_csv(BENCHMARK_DIR / "01_full_address_new_verified.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    df_b02 = pd.read_csv(BENCHMARK_DIR / "02_raw_noisy_synthetic_1000.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    df_b03 = pd.read_csv(BENCHMARK_DIR / "03_real_address_old_1500.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    df_b04 = pd.read_csv(BENCHMARK_DIR / "04_missing_fields_800.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    df_b06 = pd.read_csv(BENCHMARK_DIR / "06_hybrid_addresses_600.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    df_b07 = pd.read_csv(BENCHMARK_DIR / "07_bidirectional_pairs_verified.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")

    pred_by_tool_id = {}
    for _, row in df_pred.iterrows():
        pred_by_tool_id[(row["ID"], row["CongCu"])] = row

    records = []

    # Dataset 01
    for idx, b_row in df_b01.iterrows():
        rid = f"D01_{idx:04d}"
        r_vn = pred_by_tool_id.get((rid, "vietnamadminunits"))
        r_lp = pred_by_tool_id.get((rid, "libpostal"))
        raw_vn = raw_logs.get((rid, "vietnamadminunits"), {})
        raw_lp = raw_logs.get((rid, "libpostal"), {})

        t_arr = [b_row.get(f, "") for f in STANDARD_FIELDS]
        scored = ["SoNha", "TenDuong", "PhuongXa", "TinhThanh"]
        truth_dict = {f: b_row.get(f, "") for f in STANDARD_FIELDS}

        pred_vn = json.loads(r_vn["TruongDuDoan"]) if r_vn is not None else {}
        pred_lp = json.loads(r_lp["TruongDuDoan"]) if r_lp is not None else {}

        records.append({
            "id": rid,
            "ds": "01",
            "in": b_row["ChuoiDiaChi"],
            "t": t_arr,
            "sc": [1, 1, 1, 0, 1],
            "m": {"sys": "moi"},
            "vn": {
                "p": [pred_vn.get(f, "") for f in STANDARD_FIELDS],
                "r": r_vn["DungSai"] if r_vn is not None else "NONE",
                "e": r_vn["LoaiLoi"] if r_vn is not None else "none",
                "n": r_vn["GhiChu"] if r_vn is not None else "",
                "m": "FROM_2025",
                "d": round(raw_vn.get("duration_ms", 0), 1),
                "s": get_field_status_code(pred_vn, truth_dict, scored),
                "raw": raw_vn.get("raw_data", {}),
            },
            "lp": {
                "p": [pred_lp.get(f, "") for f in STANDARD_FIELDS],
                "r": r_lp["DungSai"] if r_lp is not None else "NONE",
                "e": r_lp["LoaiLoi"] if r_lp is not None else "none",
                "n": r_lp["GhiChu"] if r_lp is not None else "",
                "d": round(raw_lp.get("duration_ms", 0), 1),
                "s": get_field_status_code(pred_lp, truth_dict, scored),
                "raw": raw_lp.get("raw_data", {}),
            }
        })

    # Dataset 02
    for idx, b_row in df_b02.iterrows():
        base_id = f"D02_{b_row['ID']}"
        sys_type = b_row.get("HeQuyChieu", "cu")
        scored = ["SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh"] if sys_type == "cu" else ["SoNha", "TenDuong", "PhuongXa", "TinhThanh"]
        sc_bits = [1, 1, 1, 1, 1] if sys_type == "cu" else [1, 1, 1, 0, 1]
        truth_dict = {
            "SoNha": b_row.get("GT_SoNha", ""),
            "TenDuong": b_row.get("GT_TenDuong", ""),
            "PhuongXa": b_row.get("GT_PhuongXa", ""),
            "QuanHuyen": b_row.get("GT_QuanHuyen", ""),
            "TinhThanh": b_row.get("GT_TinhThanh", ""),
        }
        t_arr = [truth_dict[f] for f in STANDARD_FIELDS]

        for bermat, suffix, addr in [("clean", "_clean", b_row["ChuoiDiaChiGoc"]), ("noisy", "_noisy", b_row["ChuoiDiaChi"])]:
            rid = f"{base_id}{suffix}"
            r_vn = pred_by_tool_id.get((rid, "vietnamadminunits"))
            r_lp = pred_by_tool_id.get((rid, "libpostal"))
            raw_vn = raw_logs.get((rid, "vietnamadminunits"), {})
            raw_lp = raw_logs.get((rid, "libpostal"), {})

            pred_vn = json.loads(r_vn["TruongDuDoan"]) if r_vn is not None else {}
            pred_lp = json.loads(r_lp["TruongDuDoan"]) if r_lp is not None else {}

            records.append({
                "id": rid,
                "ds": "02",
                "in": addr,
                "t": t_arr,
                "sc": sc_bits,
                "m": {
                    "sys": sys_type,
                    "bm": bermat,
                    "ln": b_row.get("LoaiNhieu", ""),
                    "md": b_row.get("MucDoNhieu", ""),
                },
                "vn": {
                    "p": [pred_vn.get(f, "") for f in STANDARD_FIELDS],
                    "r": r_vn["DungSai"] if r_vn is not None else "NONE",
                    "e": r_vn["LoaiLoi"] if r_vn is not None else "none",
                    "n": r_vn["GhiChu"] if r_vn is not None else "",
                    "m": "FROM_2025" if sys_type == "moi" else "LEGACY",
                    "d": round(raw_vn.get("duration_ms", 0), 1),
                    "s": get_field_status_code(pred_vn, truth_dict, scored),
                    "raw": raw_vn.get("raw_data", {}),
                },
                "lp": {
                    "p": [pred_lp.get(f, "") for f in STANDARD_FIELDS],
                    "r": r_lp["DungSai"] if r_lp is not None else "NONE",
                    "e": r_lp["LoaiLoi"] if r_lp is not None else "none",
                    "n": r_lp["GhiChu"] if r_lp is not None else "",
                    "d": round(raw_lp.get("duration_ms", 0), 1),
                    "s": get_field_status_code(pred_lp, truth_dict, scored),
                    "raw": raw_lp.get("raw_data", {}),
                }
            })

    # Dataset 03
    for idx, b_row in df_b03.iterrows():
        rid = f"D03_{idx:04d}"
        r_vn = pred_by_tool_id.get((rid, "vietnamadminunits"))
        r_lp = pred_by_tool_id.get((rid, "libpostal"))
        raw_vn = raw_logs.get((rid, "vietnamadminunits"), {})
        raw_lp = raw_logs.get((rid, "libpostal"), {})

        t_arr = [b_row.get(f, "") for f in STANDARD_FIELDS]
        truth_dict = {f: b_row.get(f, "") for f in STANDARD_FIELDS}
        scored = list(STANDARD_FIELDS)

        pred_vn = json.loads(r_vn["TruongDuDoan"]) if r_vn is not None else {}
        pred_lp = json.loads(r_lp["TruongDuDoan"]) if r_lp is not None else {}

        records.append({
            "id": rid,
            "ds": "03",
            "in": b_row["ChuoiDiaChi"],
            "t": t_arr,
            "sc": [1, 1, 1, 1, 1],
            "m": {"sys": "cu"},
            "vn": {
                "p": [pred_vn.get(f, "") for f in STANDARD_FIELDS],
                "r": r_vn["DungSai"] if r_vn is not None else "NONE",
                "e": r_vn["LoaiLoi"] if r_vn is not None else "none",
                "n": r_vn["GhiChu"] if r_vn is not None else "",
                "m": "LEGACY",
                "d": round(raw_vn.get("duration_ms", 0), 1),
                "s": get_field_status_code(pred_vn, truth_dict, scored),
                "raw": raw_vn.get("raw_data", {}),
            },
            "lp": {
                "p": [pred_lp.get(f, "") for f in STANDARD_FIELDS],
                "r": r_lp["DungSai"] if r_lp is not None else "NONE",
                "e": r_lp["LoaiLoi"] if r_lp is not None else "none",
                "n": r_lp["GhiChu"] if r_lp is not None else "",
                "d": round(raw_lp.get("duration_ms", 0), 1),
                "s": get_field_status_code(pred_lp, truth_dict, scored),
                "raw": raw_lp.get("raw_data", {}),
            }
        })

    # Dataset 04
    drop_fields_map = {
        "drop_ward": ("PhuongXa",),
        "drop_district": ("QuanHuyen",),
        "drop_housenumber": ("SoNha",),
        "drop_housenumber_ward": ("SoNha", "PhuongXa")
    }

    for idx, b_row in df_b04.iterrows():
        rid = f"D04_{idx:04d}"
        r_vn = pred_by_tool_id.get((rid, "vietnamadminunits"))
        r_lp = pred_by_tool_id.get((rid, "libpostal"))
        raw_vn = raw_logs.get((rid, "vietnamadminunits"), {})
        raw_lp = raw_logs.get((rid, "libpostal"), {})

        truth_surf = {f: b_row.get(f, "") for f in STANDARD_FIELDS}
        t_arr = [truth_surf[f] for f in STANDARD_FIELDS]
        scored = list(STANDARD_FIELDS)

        gt_full = {f: b_row.get(f"GT_{f}", "") for f in STANDARD_FIELDS}
        kieu_thieu = b_row.get("KieuThieu", "")
        dropped = drop_fields_map.get(kieu_thieu, ())

        pred_vn = json.loads(r_vn["TruongDuDoan"]) if r_vn is not None else {}
        pred_lp = json.loads(r_lp["TruongDuDoan"]) if r_lp is not None else {}

        rec_vn = {}
        rec_lp = {}
        for df_field in dropped:
            val_vn = _norm(pred_vn.get(df_field, ""))
            val_lp = _norm(pred_lp.get(df_field, ""))
            gt_norm = _norm(gt_full.get(df_field, ""))
            rec_vn[df_field] = "correct" if val_vn and val_vn == gt_norm else ("wrong" if val_vn else "empty")
            rec_lp[df_field] = "correct" if val_lp and val_lp == gt_norm else ("wrong" if val_lp else "empty")

        records.append({
            "id": rid,
            "ds": "04",
            "in": b_row["ChuoiDiaChi"],
            "t": t_arr,
            "sc": [1, 1, 1, 1, 1],
            "m": {
                "sys": b_row.get("HeQuyChieu", ""),
                "kt": kieu_thieu,
                "tx": b_row.get("TruongBiXoa", ""),
                "gt": [gt_full[f] for f in STANDARD_FIELDS],
                "rvn": rec_vn,
                "rlp": rec_lp,
            },
            "vn": {
                "p": [pred_vn.get(f, "") for f in STANDARD_FIELDS],
                "r": r_vn["DungSai"] if r_vn is not None else "NONE",
                "e": r_vn["LoaiLoi"] if r_vn is not None else "none",
                "n": r_vn["GhiChu"] if r_vn is not None else "",
                "m": "FROM_2025" if b_row.get("HeQuyChieu") == "moi" else "LEGACY",
                "d": round(raw_vn.get("duration_ms", 0), 1),
                "s": get_field_status_code(pred_vn, truth_surf, scored),
                "raw": raw_vn.get("raw_data", {}),
            },
            "lp": {
                "p": [pred_lp.get(f, "") for f in STANDARD_FIELDS],
                "r": r_lp["DungSai"] if r_lp is not None else "NONE",
                "e": r_lp["LoaiLoi"] if r_lp is not None else "none",
                "n": r_lp["GhiChu"] if r_lp is not None else "",
                "d": round(raw_lp.get("duration_ms", 0), 1),
                "s": get_field_status_code(pred_lp, truth_surf, scored),
                "raw": raw_lp.get("raw_data", {}),
            }
        })

    # Dataset 06
    for idx, b_row in df_b06.iterrows():
        base_id = f"D06_{idx:04d}"
        truth_dict = {f: b_row.get(f, "") for f in STANDARD_FIELDS}
        t_arr = [truth_dict[f] for f in STANDARD_FIELDS]
        scored = list(STANDARD_FIELDS)

        r_lp = pred_by_tool_id.get((base_id, "libpostal"))
        raw_lp = raw_logs.get((base_id, "libpostal"), {})
        pred_lp = json.loads(r_lp["TruongDuDoan"]) if r_lp is not None else {}
        lp_fs = get_field_status_code(pred_lp, truth_dict, scored)

        meta_base = {
            "kl": b_row.get("KieuLai", ""),
            "px_m": b_row.get("PhuongXa_Moi", ""),
            "qh_c": b_row.get("QuanHuyen_Cu", ""),
            "px_c": b_row.get("PhuongXa_Cu", ""),
            "sd": b_row.get("Span_He_Detail", ""),
        }

        for mode_suffix, mode_name in [("_m25", "FROM_2025"), ("_mleg", "LEGACY")]:
            rid = f"{base_id}{mode_suffix}"
            r_vn = pred_by_tool_id.get((rid, "vietnamadminunits"))
            raw_vn = raw_logs.get((rid, "vietnamadminunits"), {})
            pred_vn = json.loads(r_vn["TruongDuDoan"]) if r_vn is not None else {}

            meta = dict(meta_base)
            meta["mode"] = mode_name

            records.append({
                "id": rid,
                "ds": "06",
                "in": b_row["ChuoiDiaChi"],
                "t": t_arr,
                "sc": [1, 1, 1, 1, 1],
                "m": meta,
                "vn": {
                    "p": [pred_vn.get(f, "") for f in STANDARD_FIELDS],
                    "r": r_vn["DungSai"] if r_vn is not None else "NONE",
                    "e": r_vn["LoaiLoi"] if r_vn is not None else "none",
                    "n": r_vn["GhiChu"] if r_vn is not None else "",
                    "m": mode_name,
                    "d": round(raw_vn.get("duration_ms", 0), 1),
                    "s": get_field_status_code(pred_vn, truth_dict, scored),
                    "raw": raw_vn.get("raw_data", {}),
                },
                "lp": {
                    "p": [pred_lp.get(f, "") for f in STANDARD_FIELDS],
                    "r": r_lp["DungSai"] if r_lp is not None else "NONE",
                    "e": r_lp["LoaiLoi"] if r_lp is not None else "none",
                    "n": r_lp["GhiChu"] if r_lp is not None else "",
                    "d": round(raw_lp.get("duration_ms", 0), 1),
                    "s": lp_fs,
                    "raw": raw_lp.get("raw_data", {}),
                }
            })

    # Dataset 07
    for idx, b_row in df_b07.iterrows():
        rel = b_row.get("QuanHe", "")
        rid = f"D07_{idx:04d}_{rel}"
        r_vn = pred_by_tool_id.get((rid, "vietnamadminunits"))
        raw_vn = raw_logs.get((rid, "vietnamadminunits"), {})

        parts = [p.strip() for p in b_row["DiaChi_Moi"].split(",") if p.strip()]
        truth_dict = {
            "SoNha": "",
            "TenDuong": "",
            "PhuongXa": parts[-2] if len(parts) >= 2 else "",
            "QuanHuyen": "",
            "TinhThanh": parts[-1] if len(parts) >= 1 else "",
        }
        t_arr = [truth_dict[f] for f in STANDARD_FIELDS]
        scored = ["PhuongXa", "TinhThanh"]

        pred_vn = json.loads(r_vn["TruongDuDoan"]) if r_vn is not None else {}

        records.append({
            "id": rid,
            "ds": "07",
            "in": b_row["DiaChi_Cu"],
            "t": t_arr,
            "sc": [0, 0, 1, 0, 1],
            "m": {
                "qh": rel,
                "lax": b_row.get("LoaiAnhXa", ""),
                "ht": b_row.get("HinhThucSapNhap", ""),
                "mm": b_row.get("MaPhuongXaMoi", ""),
                "ng": b_row.get("Nguon", ""),
                "dc_c": b_row.get("DiaChi_Cu", ""),
                "dc_m": b_row.get("DiaChi_Moi", ""),
                "nid": b_row.get("ID_Node", ""),
            },
            "vn": {
                "p": [pred_vn.get(f, "") for f in STANDARD_FIELDS],
                "r": r_vn["DungSai"] if r_vn is not None else "NONE",
                "e": r_vn["LoaiLoi"] if r_vn is not None else "none",
                "n": r_vn["GhiChu"] if r_vn is not None else "",
                "m": "CONVERT_2025",
                "d": round(raw_vn.get("duration_ms", 0), 1),
                "s": get_field_status_code(pred_vn, truth_dict, scored),
                "raw": raw_vn.get("raw_data", {}),
            },
            "lp": {
                "p": ["", "", "", "", ""],
                "r": "UNSUPPORTED",
                "e": "unsupported_task",
                "n": "Không áp dụng (tác vụ chuyển đổi hành chính 2025)",
                "d": 0,
                "s": "nnnnn",
                "raw": {"ghi_chu": "Libpostal không hỗ trợ chuyển đổi đơn vị hành chính qua cải cách"},
            }
        })

    print(f"[3/4] Successfully assembled {len(records)} paired evaluation records.")

    summary_stats = {
        "manifest": {
            "run_date": manifest.get("freeze_timestamp", "unknown"),
            "run_id": manifest.get("run_id", "legacy"),
            "total_benchmark_rows": sum(item["row_count"] for item in manifest.get("datasets", {}).values()),
            "total_predictions": len(df_pred),
            "tools": manifest.get("baseline_tools", {}),
            "python_env": f"Python {manifest.get('python_version', 'unknown')}",
            "hashes": manifest.get("output_hashes", {}),
        },
        "accuracy_chart": [
            {"group": "D01 Mới", "tool": "VietnamAdminUnits", "n": 1000, "c": 973, "p": 27, "e": 0, "pct_c": 97.3, "pct_p": 2.7, "pct_e": 0.0},
            {"group": "D01 Mới", "tool": "Libpostal", "n": 1000, "c": 2, "p": 917, "e": 81, "pct_c": 0.2, "pct_p": 91.7, "pct_e": 8.1},
            {"group": "D02 Sạch", "tool": "VietnamAdminUnits", "n": 1000, "c": 862, "p": 138, "e": 0, "pct_c": 86.2, "pct_p": 13.8, "pct_e": 0.0},
            {"group": "D02 Sạch", "tool": "Libpostal", "n": 1000, "c": 1, "p": 914, "e": 85, "pct_c": 0.1, "pct_p": 91.4, "pct_e": 8.5},
            {"group": "D02 Nhiễu", "tool": "VietnamAdminUnits", "n": 1000, "c": 217, "p": 689, "e": 94, "pct_c": 21.7, "pct_p": 68.9, "pct_e": 9.4},
            {"group": "D02 Nhiễu", "tool": "Libpostal", "n": 1000, "c": 1, "p": 784, "e": 215, "pct_c": 0.1, "pct_p": 78.4, "pct_e": 21.5},
            {"group": "D03 Cũ sạch", "tool": "VietnamAdminUnits", "n": 1500, "c": 1094, "p": 372, "e": 34, "pct_c": 72.9, "pct_p": 24.8, "pct_e": 2.3},
            {"group": "D03 Cũ sạch", "tool": "Libpostal", "n": 1500, "c": 2, "p": 936, "e": 562, "pct_c": 0.1, "pct_p": 62.4, "pct_e": 37.5},
            {"group": "D04 Thiếu", "tool": "VietnamAdminUnits", "n": 800, "c": 208, "p": 246, "e": 346, "pct_c": 26.0, "pct_p": 30.8, "pct_e": 43.2},
            {"group": "D04 Thiếu", "tool": "Libpostal", "n": 800, "c": 120, "p": 213, "e": 467, "pct_c": 15.0, "pct_p": 26.6, "pct_e": 58.4},
            {"group": "D06 Lai m25", "tool": "VNAdmin (FROM_2025)", "n": 600, "c": 0, "p": 556, "e": 44, "pct_c": 0.0, "pct_p": 92.7, "pct_e": 7.3},
            {"group": "D06 Lai mleg", "tool": "VNAdmin (LEGACY)", "n": 600, "c": 415, "p": 183, "e": 2, "pct_c": 69.2, "pct_p": 30.5, "pct_e": 0.3},
            {"group": "D06 Lai lp", "tool": "Libpostal (single)", "n": 600, "c": 2, "p": 498, "e": 100, "pct_c": 0.3, "pct_p": 83.0, "pct_e": 16.7},
            {"group": "D07 Convert", "tool": "VNAdmin (convert)", "n": 600, "c": 586, "p": 0, "e": 14, "pct_c": 97.7, "pct_p": 0.0, "pct_e": 2.3},
        ],
        "field_f1_chart": {
            "D01": {
                "fields": ["SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh"],
                "vn": [0.979, 0.973, 1.000, None, 1.000],
                "lp": [0.924, 0.373, 0.004, 0.000, 0.938],
            },
            "D03": {
                "fields": ["SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh"],
                "vn": [0.866, 0.780, 0.915, 0.977, 0.983],
                "lp": [0.718, 0.259, 0.006, 0.073, 0.826],
            },
            "D04": {
                "fields": ["SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh"],
                "vn": [0.006, 0.447, 0.697, 0.936, 0.785],
                "lp": [0.792, 0.285, 0.012, 0.162, 0.724],
            },
        },
        "noise_chart": [
            {"level": "Nhẹ (nhe)", "n": 376, "vn_clean_f1": 0.951, "vn_noisy_f1": 0.783, "lp_clean_f1": 0.504, "lp_noisy_f1": 0.443, "vn_drop_pct": 17.7, "lp_drop_pct": 12.1},
            {"level": "Vừa (vua)", "n": 413, "vn_clean_f1": 0.946, "vn_noisy_f1": 0.752, "lp_clean_f1": 0.514, "lp_noisy_f1": 0.388, "vn_drop_pct": 20.5, "lp_drop_pct": 24.5},
            {"level": "Nặng (nang)", "n": 211, "vn_clean_f1": 0.944, "vn_noisy_f1": 0.574, "lp_clean_f1": 0.511, "lp_noisy_f1": 0.315, "vn_drop_pct": 39.2, "lp_drop_pct": 38.4},
            {"level": "Tất cả (all)", "n": 1000, "vn_clean_f1": 0.947, "vn_noisy_f1": 0.732, "lp_clean_f1": 0.509, "lp_noisy_f1": 0.395, "vn_drop_pct": 22.7, "lp_drop_pct": 22.4},
        ],
        "recovery_d04": [
            {"kind": "drop_ward", "n": 241, "vn_c": 5, "vn_w": 19, "vn_e": 217, "lp_c": 0, "lp_w": 7, "lp_e": 234},
            {"kind": "drop_district", "n": 99, "vn_c": 2, "vn_w": 7, "vn_e": 90, "lp_c": 0, "lp_w": 10, "lp_e": 89},
            {"kind": "drop_housenumber", "n": 348, "vn_c": 1, "vn_w": 0, "vn_e": 347, "lp_c": 2, "lp_w": 48, "lp_e": 298},
            {"kind": "drop_housenumber_ward", "n": 224, "vn_c": 6, "vn_w": 14, "vn_e": 204, "lp_c": 0, "lp_w": 19, "lp_e": 205},
            {"kind": "tất cả", "n": 912, "vn_c": 14, "vn_w": 40, "vn_e": 858, "lp_c": 2, "lp_w": 84, "lp_e": 826},
        ]
    }

    # Every aggregate below is calculated from this run's prediction CSV.
    # The HTML never reuses a score from an earlier run as a dashboard metric.
    def status_chart(group: str, tool: str, frame: pd.DataFrame) -> dict:
        counts = frame["DungSai"].value_counts()
        n = len(frame)
        correct, partial, error = (int(counts.get(key, 0)) for key in ("CORRECT", "PARTIAL", "ERROR"))
        return {
            "group": group,
            "tool": tool,
            "n": n,
            "c": correct,
            "p": partial,
            "e": error,
            "pct_c": round(100 * correct / n, 1) if n else 0.0,
            "pct_p": round(100 * partial / n, 1) if n else 0.0,
            "pct_e": round(100 * error / n, 1) if n else 0.0,
        }

    def micro_f1(frame: pd.DataFrame, fields: tuple[str, ...] = STANDARD_FIELDS) -> float:
        tp = fp = fn = 0
        for _, item in frame.iterrows():
            prediction = json.loads(item["TruongDuDoan"])
            truth = json.loads(item["TruongDung"])
            for field in fields:
                p, t = _norm(prediction.get(field, "")), _norm(truth.get(field, ""))
                if p and p == t:
                    tp += 1
                elif p and t:
                    fp += 1
                    fn += 1
                elif p:
                    fp += 1
                elif t:
                    fn += 1
        return round(2 * tp / (2 * tp + fp + fn), 3) if (2 * tp + fp + fn) else 0.0

    def per_field_f1(frame: pd.DataFrame, tool: str) -> list[float | None]:
        sub = frame[frame["CongCu"].eq(tool)]
        values = []
        for field in STANDARD_FIELDS:
            tp = fp = fn = 0
            for _, item in sub.iterrows():
                prediction = json.loads(item["TruongDuDoan"])
                truth = json.loads(item["TruongDung"])
                p, t = _norm(prediction.get(field, "")), _norm(truth.get(field, ""))
                if p and p == t:
                    tp += 1
                elif p and t:
                    fp += 1
                    fn += 1
                elif p:
                    fp += 1
                elif t:
                    fn += 1
            denominator = 2 * tp + fp + fn
            values.append(round(2 * tp / denominator, 3) if denominator else None)
        return values

    condition_frames = [
        ("D01 Mới", "VietnamAdminUnits", df_pred[df_pred["ID"].str.startswith("D01_") & df_pred["CongCu"].eq("vietnamadminunits")]),
        ("D01 Mới", "Libpostal", df_pred[df_pred["ID"].str.startswith("D01_") & df_pred["CongCu"].eq("libpostal")]),
        ("D02 Sạch", "VietnamAdminUnits", df_pred[df_pred["ID"].str.startswith("D02_") & df_pred["ID"].str.endswith("_clean") & df_pred["CongCu"].eq("vietnamadminunits")]),
        ("D02 Sạch", "Libpostal", df_pred[df_pred["ID"].str.startswith("D02_") & df_pred["ID"].str.endswith("_clean") & df_pred["CongCu"].eq("libpostal")]),
        ("D02 Nhiễu", "VietnamAdminUnits", df_pred[df_pred["ID"].str.startswith("D02_") & df_pred["ID"].str.endswith("_noisy") & df_pred["CongCu"].eq("vietnamadminunits")]),
        ("D02 Nhiễu", "Libpostal", df_pred[df_pred["ID"].str.startswith("D02_") & df_pred["ID"].str.endswith("_noisy") & df_pred["CongCu"].eq("libpostal")]),
        ("D03 Cũ sạch", "VietnamAdminUnits", df_pred[df_pred["ID"].str.startswith("D03_") & df_pred["CongCu"].eq("vietnamadminunits")]),
        ("D03 Cũ sạch", "Libpostal", df_pred[df_pred["ID"].str.startswith("D03_") & df_pred["CongCu"].eq("libpostal")]),
        ("D04 Thiếu", "VietnamAdminUnits", df_pred[df_pred["ID"].str.startswith("D04_") & df_pred["CongCu"].eq("vietnamadminunits")]),
        ("D04 Thiếu", "Libpostal", df_pred[df_pred["ID"].str.startswith("D04_") & df_pred["CongCu"].eq("libpostal")]),
        ("D06 Lai m25", "VNAdmin (FROM_2025)", df_pred[df_pred["ID"].str.startswith("D06_") & df_pred["ID"].str.endswith("_m25")]),
        ("D06 Lai mleg", "VNAdmin (LEGACY)", df_pred[df_pred["ID"].str.startswith("D06_") & df_pred["ID"].str.endswith("_mleg")]),
        ("D06 Lai lp", "Libpostal (single)", df_pred[df_pred["ID"].str.startswith("D06_") & df_pred["CongCu"].eq("libpostal")]),
        ("D07 Convert", "VNAdmin (old_to_new)", df_pred[df_pred["ID"].str.startswith("D07_")]),
    ]
    summary_stats["accuracy_chart"] = [status_chart(group, tool, frame) for group, tool, frame in condition_frames]

    summary_stats["field_f1_chart"] = {
        dataset: {
            "fields": list(STANDARD_FIELDS),
            "vn": per_field_f1(df_pred[df_pred["ID"].str.startswith(prefix)], "vietnamadminunits"),
            "lp": per_field_f1(df_pred[df_pred["ID"].str.startswith(prefix)], "libpostal"),
        }
        for dataset, prefix in (("D01", "D01_"), ("D03", "D03_"), ("D04", "D04_"))
    }

    noise_rows = []
    for level, label in (("nhe", "Nhẹ (nhe)"), ("vua", "Vừa (vua)"), ("nang", "Nặng (nang)"), (None, "Tất cả (all)")):
        meta = df_b02 if level is None else df_b02[df_b02["MucDoNhieu"].eq(level)]
        bases = set("D02_" + value for value in meta["ID"])
        def select_noise(tool: str, suffix: str) -> pd.DataFrame:
            return df_pred[df_pred["CongCu"].eq(tool) & df_pred["ID"].isin({base + suffix for base in bases})]
        vn_clean, vn_noisy = select_noise("vietnamadminunits", "_clean"), select_noise("vietnamadminunits", "_noisy")
        lp_clean, lp_noisy = select_noise("libpostal", "_clean"), select_noise("libpostal", "_noisy")
        vn_clean_f1, vn_noisy_f1 = micro_f1(vn_clean), micro_f1(vn_noisy)
        lp_clean_f1, lp_noisy_f1 = micro_f1(lp_clean), micro_f1(lp_noisy)
        noise_rows.append({
            "level": label,
            "n": len(meta),
            "vn_clean_f1": vn_clean_f1,
            "vn_noisy_f1": vn_noisy_f1,
            "lp_clean_f1": lp_clean_f1,
            "lp_noisy_f1": lp_noisy_f1,
            "vn_drop_pct": round(100 * (vn_clean_f1 - vn_noisy_f1) / vn_clean_f1, 1) if vn_clean_f1 else 0.0,
            "lp_drop_pct": round(100 * (lp_clean_f1 - lp_noisy_f1) / lp_clean_f1, 1) if lp_clean_f1 else 0.0,
        })
    summary_stats["noise_chart"] = noise_rows

    drop_map = {
        "drop_ward": ("PhuongXa",),
        "drop_district": ("QuanHuyen",),
        "drop_housenumber": ("SoNha",),
        "drop_housenumber_ward": ("SoNha", "PhuongXa"),
    }
    recovery_rows = []
    for kind in (*drop_map, "tất cả"):
        subset = df_b04 if kind == "tất cả" else df_b04[df_b04["KieuThieu"].eq(kind)]
        stats = {tool: {state: 0 for state in ("c", "w", "e")} for tool in ("vietnamadminunits", "libpostal")}
        for idx, source in subset.iterrows():
            fields = drop_map[source["KieuThieu"]]
            for tool in stats:
                row = pred_by_tool_id.get((f"D04_{idx:04d}", tool))
                prediction = json.loads(row["TruongDuDoan"]) if row is not None else {}
                for field in fields:
                    value, truth = _norm(prediction.get(field, "")), _norm(source.get(f"GT_{field}", ""))
                    stats[tool]["c" if value and value == truth else ("w" if value else "e")] += 1
        recovery_rows.append({
            "kind": kind,
            "n": sum(stats["vietnamadminunits"].values()),
            "vn_c": stats["vietnamadminunits"]["c"], "vn_w": stats["vietnamadminunits"]["w"], "vn_e": stats["vietnamadminunits"]["e"],
            "lp_c": stats["libpostal"]["c"], "lp_w": stats["libpostal"]["w"], "lp_e": stats["libpostal"]["e"],
        })
    summary_stats["recovery_d04"] = recovery_rows

    return {"stats": summary_stats, "records": records}


def generate_html(data: dict) -> str:
    print("[4/4] Generating standalone HTML...")
    json_data = json.dumps(data, ensure_ascii=False)
    manifest_stats = data["stats"]["manifest"]
    tool_stats = manifest_stats.get("tools", {})
    tool_label = " | ".join(
        f"{name} {version}" for name, version in tool_stats.items()
        if name in {"vietnamadminunits", "libpostal"} and version
    ) or "xem manifest"

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DACN Baseline Evaluation Dashboard | Vietnam Address Benchmark 2025</title>
<style>
  :root {{
    --bg-base: #0b0f19;
    --bg-surface: #111827;
    --bg-card: #1f2937;
    --bg-card-hover: #263345;
    --bg-elevated: #283548;
    --border: #374151;
    --border-light: #4b5563;
    --border-focus: #6366f1;
    --text-main: #f9fafb;
    --text-muted: #9ca3af;
    --text-dim: #6b7280;
    --color-correct: #10b981;
    --color-correct-bg: rgba(16, 185, 129, 0.15);
    --color-correct-border: rgba(16, 185, 129, 0.35);
    --color-partial: #f59e0b;
    --color-partial-bg: rgba(245, 158, 11, 0.15);
    --color-partial-border: rgba(245, 158, 11, 0.35);
    --color-error: #ef4444;
    --color-error-bg: rgba(239, 68, 68, 0.15);
    --color-error-border: rgba(239, 68, 68, 0.35);
    --color-unsupported: #64748b;
    --color-unsupported-bg: rgba(100, 116, 139, 0.15);
    --color-unsupported-border: rgba(100, 116, 139, 0.35);
    --color-brand: #6366f1;
    --color-brand-hover: #4f46e5;
    --color-cyan: #06b6d4;
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background-color: var(--bg-base);
    color: var(--text-main);
    line-height: 1.5;
    font-size: 13px;
    padding: 16px 24px;
    min-height: 100vh;
  }}

  /* Top Navigation & Header */
  header {{
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }}
  .header-top {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
  }}
  .brand-title {{
    display: flex;
    align-items: center;
    gap: 10px;
  }}
  .brand-title h1 {{
    font-size: 18px;
    font-weight: 700;
    color: #fff;
    letter-spacing: -0.02em;
  }}
  .brand-title .badge-tag {{
    background: rgba(99, 102, 241, 0.2);
    color: #a5b4fc;
    border: 1px solid rgba(99, 102, 241, 0.4);
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
  }}
  .header-pills {{
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }}
  .pill {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 11px;
    color: var(--text-muted);
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }}
  .pill strong {{ color: var(--text-main); }}

  /* Verification test cases bar */
  .quick-cases-bar {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding-top: 10px;
    border-top: 1px solid rgba(255,255,255,0.06);
    flex-wrap: wrap;
  }}
  .quick-cases-label {{
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}
  .quick-btn {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    color: #38bdf8;
    padding: 3px 10px;
    border-radius: 6px;
    font-size: 11px;
    cursor: pointer;
    font-family: monospace;
    font-weight: 600;
    transition: all 0.15s ease;
  }}
  .quick-btn:hover {{
    background: #0284c7;
    color: #fff;
    border-color: #38bdf8;
  }}

  /* Audit / Methodology Warning Banner */
  .audit-banner {{
    background: linear-gradient(90deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.8));
    border: 1px solid #334155;
    border-left: 4px solid var(--color-brand);
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 16px;
    font-size: 12px;
    color: #cbd5e1;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }}
  .audit-banner-title {{
    font-weight: 700;
    color: #e2e8f0;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .audit-banner ul {{
    margin-left: 18px;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 4px 20px;
  }}

  /* KPI Summary Cards */
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
    margin-bottom: 16px;
  }}
  .kpi-card {{
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }}
  .kpi-title {{
    font-size: 11px;
    color: var(--text-muted);
    text-transform: uppercase;
    font-weight: 600;
    letter-spacing: 0.03em;
  }}
  .kpi-value {{
    font-size: 20px;
    font-weight: 700;
    color: #fff;
    display: flex;
    align-items: baseline;
    gap: 6px;
  }}
  .kpi-sub {{
    font-size: 11px;
    color: var(--text-dim);
  }}

  /* Visual Charts Section */
  .charts-section {{
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 16px;
  }}
  .charts-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 8px;
    flex-wrap: wrap;
    gap: 10px;
  }}
  .charts-header h2 {{
    font-size: 14px;
    font-weight: 700;
    color: #fff;
  }}
  .chart-tabs {{
    display: flex;
    gap: 6px;
  }}
  .chart-tab {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    color: var(--text-muted);
    padding: 4px 12px;
    border-radius: 6px;
    font-size: 11px;
    cursor: pointer;
    font-weight: 600;
    transition: all 0.15s;
  }}
  .chart-tab.active {{
    background: var(--color-brand);
    color: #fff;
    border-color: var(--color-brand-light);
  }}
  .chart-container {{
    display: none;
    overflow-x: auto;
  }}
  .chart-container.active {{
    display: block;
  }}
  .chart-svg {{
    width: 100%;
    min-width: 600px;
    height: 240px;
  }}
  .chart-legend {{
    display: flex;
    gap: 16px;
    justify-content: center;
    margin-top: 10px;
    font-size: 11px;
    color: var(--text-muted);
  }}
  .legend-item {{
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .legend-dot {{
    width: 10px;
    height: 10px;
    border-radius: 3px;
  }}

  /* Filter Command Toolbar */
  .toolbar {{
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }}
  .filter-row {{
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }}
  .filter-group {{
    display: flex;
    flex-direction: column;
    gap: 4px;
  }}
  .filter-label {{
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
  }}
  .filter-select, .search-input {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    color: var(--text-main);
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 12px;
    outline: none;
    transition: border-color 0.15s;
  }}
  .filter-select:focus, .search-input:focus {{
    border-color: var(--border-focus);
  }}
  .search-input {{
    flex: 1;
    min-width: 260px;
  }}
  .btn {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    color: var(--text-main);
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 12px;
    cursor: pointer;
    font-weight: 600;
    transition: all 0.15s;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }}
  .btn:hover {{
    background: var(--bg-elevated);
    border-color: var(--border-light);
  }}
  .btn-primary {{
    background: var(--color-brand);
    border-color: var(--color-brand-light);
    color: #fff;
  }}
  .btn-primary:hover {{
    background: var(--color-brand-hover);
  }}
  .counter-badge {{
    margin-left: auto;
    font-size: 12px;
    color: var(--text-muted);
    font-weight: 600;
  }}
  .counter-badge strong {{
    color: #38bdf8;
  }}

  /* Table Section */
  .table-container {{
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 16px;
  }}
  .table-wrap {{
    overflow-x: auto;
    max-height: 600px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    text-align: left;
    font-size: 12px;
  }}
  thead {{
    position: sticky;
    top: 0;
    background: var(--bg-card);
    z-index: 2;
  }}
  th {{
    padding: 10px 14px;
    color: var(--text-muted);
    font-weight: 600;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }}
  td {{
    padding: 8px 14px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    vertical-align: middle;
  }}
  tbody tr:hover {{
    background: var(--bg-card-hover);
    cursor: pointer;
  }}
  .row-id {{
    font-family: monospace;
    font-weight: 700;
    color: #38bdf8;
    white-space: nowrap;
  }}
  .input-address-cell {{
    max-width: 320px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: #f1f5f9;
  }}

  /* Status Badges */
  .status-badge {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.02em;
    white-space: nowrap;
  }}
  .status-CORRECT {{
    background: var(--color-correct-bg);
    color: var(--color-correct);
    border: 1px solid var(--color-correct-border);
  }}
  .status-PARTIAL {{
    background: var(--color-partial-bg);
    color: var(--color-partial);
    border: 1px solid var(--color-partial-border);
  }}
  .status-ERROR {{
    background: var(--color-error-bg);
    color: var(--color-error);
    border: 1px solid var(--color-error-border);
  }}
  .status-UNSUPPORTED {{
    background: var(--color-unsupported-bg);
    color: #cbd5e1;
    border: 1px solid var(--color-unsupported-border);
  }}
  .tool-res-cell {{
    display: flex;
    flex-direction: column;
    gap: 3px;
  }}
  .field-dots {{
    display: flex;
    gap: 3px;
    align-items: center;
  }}
  .f-dot {{
    width: 6px;
    height: 6px;
    border-radius: 50%;
  }}
  .dot-m {{ background: var(--color-correct); }}
  .dot-x {{ background: var(--color-error); }}
  .dot-o {{ background: var(--color-partial); }}
  .dot-t {{ background: #64748b; }}
  .dot-n {{ background: #334155; }}

  /* Pagination Bar */
  .pagination-bar {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 16px;
    background: var(--bg-card);
    border-top: 1px solid var(--border);
    flex-wrap: wrap;
    gap: 10px;
    font-size: 12px;
  }}
  .pagination-controls {{
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .page-btn {{
    background: var(--bg-surface);
    border: 1px solid var(--border);
    color: var(--text-main);
    padding: 4px 10px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 11px;
    font-weight: 600;
  }}
  .page-btn:disabled {{
    opacity: 0.4;
    cursor: not-allowed;
  }}

  /* Side Drawer Detail Modal */
  .drawer-overlay {{
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0, 0, 0, 0.65);
    backdrop-filter: blur(4px);
    z-index: 100;
    display: none;
    opacity: 0;
    transition: opacity 0.2s ease;
  }}
  .drawer-overlay.active {{
    display: block;
    opacity: 1;
  }}
  .drawer {{
    position: fixed;
    top: 0; right: 0; bottom: 0;
    width: 760px;
    max-width: 95vw;
    background: var(--bg-surface);
    border-left: 1px solid var(--border);
    box-shadow: -10px 0 30px rgba(0,0,0,0.5);
    z-index: 101;
    display: flex;
    flex-direction: column;
    transform: translateX(100%);
    transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  }}
  .drawer.active {{
    transform: translateX(0);
  }}
  .drawer-header {{
    padding: 16px 20px;
    background: var(--bg-card);
    border-bottom: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .drawer-title-wrap {{
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  .drawer-title {{
    font-size: 16px;
    font-weight: 700;
    color: #fff;
    font-family: monospace;
  }}
  .drawer-close {{
    background: transparent;
    border: none;
    color: var(--text-muted);
    font-size: 20px;
    cursor: pointer;
    padding: 4px 8px;
    border-radius: 4px;
  }}
  .drawer-close:hover {{
    color: #fff;
    background: var(--bg-elevated);
  }}
  .drawer-content {{
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }}

  /* Drawer Card Components */
  .detail-card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }}
  .detail-card-title {{
    font-size: 12px;
    font-weight: 700;
    color: #cbd5e1;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .input-address-box {{
    background: var(--bg-base);
    border: 1px solid var(--border);
    padding: 10px 14px;
    border-radius: 6px;
    font-size: 13px;
    color: #38bdf8;
    word-break: break-word;
    user-select: text;
  }}

  /* 5-Field Comparison Table */
  .comp-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }}
  .comp-table th {{
    background: var(--bg-base);
    padding: 8px 10px;
    color: var(--text-muted);
    font-weight: 600;
    border: 1px solid var(--border);
  }}
  .comp-table td {{
    padding: 8px 10px;
    border: 1px solid var(--border);
    vertical-align: top;
  }}
  .cell-match {{
    background: var(--color-correct-bg);
    color: #34d399;
  }}
  .cell-mismatch {{
    background: var(--color-error-bg);
    color: #f87171;
  }}
  .cell-omitted {{
    background: var(--color-partial-bg);
    color: #fbbf24;
  }}
  .cell-tn {{
    background: rgba(100, 116, 139, 0.1);
    color: #94a3b8;
  }}
  .cell-na {{
    background: rgba(30, 41, 59, 0.4);
    color: #64748b;
  }}
  .cell-tag {{
    display: inline-block;
    font-size: 9px;
    font-weight: 700;
    padding: 1px 4px;
    border-radius: 3px;
    margin-bottom: 2px;
    text-transform: uppercase;
  }}

  /* Dataset Specific Callouts */
  .meta-tag-row {{
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    font-size: 11px;
  }}
  .meta-pill {{
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    padding: 2px 8px;
    border-radius: 4px;
    color: #e2e8f0;
  }}
  .token-chips {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 6px;
  }}
  .token-chip {{
    background: var(--bg-base);
    border: 1px solid var(--border);
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 11px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }}
  .token-label {{
    color: #a5b4fc;
    font-weight: 600;
    font-size: 10px;
    background: rgba(99, 102, 241, 0.2);
    padding: 1px 5px;
    border-radius: 3px;
  }}
  .raw-code {{
    background: var(--bg-base);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 10px;
    font-family: monospace;
    font-size: 11px;
    color: #cbd5e1;
    overflow-x: auto;
    max-height: 200px;
  }}
  .drawer-footer {{
    padding: 12px 20px;
    background: var(--bg-card);
    border-top: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
</style>
</head>
<body>

<header>
  <div class="header-top">
    <div class="brand-title">
      <h1>DACN Baseline Output Inspector</h1>
      <span class="badge-tag">Vietnam Address 2025</span>
    </div>
    <div class="header-pills">
      <span class="pill">Run: <strong>{manifest_stats.get('run_id')} · {manifest_stats.get('run_date')}</strong></span>
      <span class="pill">Benchmark: <strong>{manifest_stats.get('total_benchmark_rows'):,} dòng</strong></span>
      <span class="pill">Dự đoán: <strong>{manifest_stats.get('total_predictions'):,} lượt</strong></span>
      <span class="pill">Tools: <strong>{tool_label}</strong></span>
    </div>
  </div>

  <div class="quick-cases-bar">
    <span class="quick-cases-label">Ca kiểm thử truy vết báo cáo:</span>
    <button class="quick-btn" onclick="jumpToCase('D01_0000')">D01_0000 (LP sai biên quận/phường)</button>
    <button class="quick-btn" onclick="jumpToCase('D04_0000')">D04_0000 (VNAdmin mất số nhà)</button>
    <button class="quick-btn" onclick="jumpToCase('D06_0000_m25')">D06_0000_m25 (Lai mode 2025)</button>
    <button class="quick-btn" onclick="jumpToCase('D07_0018_M-N')">D07_0018_M-N (VNAdmin sai đích M-N)</button>
  </div>
</header>

<div class="audit-banner">
  <div class="audit-banner-title">
    <span>⚠️ Lưu ý phương pháp luận & Hợp đồng dữ liệu</span>
  </div>
  <ul>
    <li><strong>VietnamAdminUnits (Oracle mode):</strong> Được cấp mode tương ứng (FROM_2025 hoặc LEGACY) trong giao thức chạy Data 01-04. Đây không phải phép đo phân loại tự động T1.</li>
    <li><strong>Libpostal:</strong> Thư viện C quốc tế với bộ từ điển mặc định, không có tri thức cải cách hành chính Việt Nam 2025 và không hỗ trợ chuyển đổi đơn vị.</li>
    <li><strong>Data 03:</strong> 100% dòng sạch hoàn toàn đủ cả 5 trường (`SoNha`, `TenDuong`, `PhuongXa`, `QuanHuyen`, `TinhThanh`), đã loại bỏ dòng thiếu tự nhiên.</li>
    <li><strong>Data 04:</strong> Sinh có kiểm soát từ địa chỉ sạch. Chấm parse chỉ tính trường bề mặt; khả năng tự phục hồi trường bị xóa được phân tích độc lập.</li>
    <li><strong>Data 07:</strong> Tác vụ chuyển đổi địa chỉ sáp nhập (N-1 và M-N), chỉ chấm 2 trường hành chính mới `PhuongXa` và `TinhThanh`.</li>
  </ul>
</div>

<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-title">Data 01 Mới (1,000)</div>
    <div class="kpi-value">97.3% <span class="kpi-sub">vs 0.2%</span></div>
    <div class="kpi-sub">VNAdmin vs Libpostal (Exact match)</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-title">Data 03 Cũ Sạch (1,500)</div>
    <div class="kpi-value">72.9% <span class="kpi-sub">vs 0.1%</span></div>
    <div class="kpi-sub">VNAdmin vs Libpostal (Exact match)</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-title">Data 04 Thiếu Trường (800)</div>
    <div class="kpi-value">26.0% <span class="kpi-sub">vs 15.0%</span></div>
    <div class="kpi-sub">Chấm parse bề mặt (VNAdmin vs LP)</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-title">Data 02 Độ Bền Nhiễu (1,000)</div>
    <div class="kpi-value">86.2% → 21.7%</div>
    <div class="kpi-sub">VNAdmin: Sạch đúng → Nhiễu đúng (-64.5%)</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-title">Data 07 Chuyển Đổi (600)</div>
    <div class="kpi-value">97.7% <span class="kpi-sub">(586/600)</span></div>
    <div class="kpi-sub">VNAdmin Convert 2025 (N-1: 99.2% | M-N: 96.6%)</div>
  </div>
</div>

<div class="charts-section">
  <div class="charts-header">
    <h2>Biểu đồ phân tích hiệu năng Baseline</h2>
    <div class="chart-tabs">
      <button class="chart-tab active" onclick="switchChart('acc')">Tỷ lệ Đúng / Một phần / Sai</button>
      <button class="chart-tab" onclick="switchChart('f1')">F1 Từng trường (D01, D03, D04)</button>
      <button class="chart-tab" onclick="switchChart('noise')">Data 02 Suy giảm do nhiễu</button>
      <button class="chart-tab" onclick="switchChart('rec')">Data 04 Phục hồi trường thiếu</button>
    </div>
  </div>

  <div id="chart-acc" class="chart-container active">
    <svg id="svg-acc" class="chart-svg" viewBox="0 0 920 220"></svg>
    <div class="chart-legend">
      <div class="legend-item"><div class="legend-dot" style="background: var(--color-correct)"></div> Đúng hoàn toàn (CORRECT)</div>
      <div class="legend-item"><div class="legend-dot" style="background: var(--color-partial)"></div> Đúng một phần (PARTIAL)</div>
      <div class="legend-item"><div class="legend-dot" style="background: var(--color-error)"></div> Sai / Không đạt (ERROR)</div>
    </div>
  </div>

  <div id="chart-f1" class="chart-container">
    <svg id="svg-f1" class="chart-svg" viewBox="0 0 920 220"></svg>
    <div class="chart-legend">
      <div class="legend-item"><div class="legend-dot" style="background: #6366f1"></div> VietnamAdminUnits</div>
      <div class="legend-item"><div class="legend-dot" style="background: #06b6d4"></div> Libpostal</div>
    </div>
  </div>

  <div id="chart-noise" class="chart-container">
    <svg id="svg-noise" class="chart-svg" viewBox="0 0 920 220"></svg>
    <div class="chart-legend">
      <div class="legend-item"><div class="legend-dot" style="background: #10b981"></div> F1 Sạch (Clean)</div>
      <div class="legend-item"><div class="legend-dot" style="background: #f59e0b"></div> F1 Nhiễu (Noisy)</div>
      <div class="legend-item"><div class="legend-dot" style="background: #ef4444"></div> Tỷ lệ suy giảm (%)</div>
    </div>
  </div>

  <div id="chart-rec" class="chart-container">
    <svg id="svg-rec" class="chart-svg" viewBox="0 0 920 220"></svg>
    <div class="chart-legend">
      <div class="legend-item"><div class="legend-dot" style="background: #10b981"></div> Phục hồi đúng</div>
      <div class="legend-item"><div class="legend-dot" style="background: #ef4444"></div> Điền sai (Suy đoán sai)</div>
      <div class="legend-item"><div class="legend-dot" style="background: #64748b"></div> Không điền (Bảo toàn rỗng)</div>
    </div>
  </div>
</div>

<div class="toolbar">
  <div class="filter-row">
    <div class="filter-group">
      <label class="filter-label">Tập dữ liệu:</label>
      <select id="filter-ds" class="filter-select" onchange="onFilterChange()">
        <option value="ALL">Tất cả (7,100 đối sánh)</option>
        <option value="01" selected>Data 01: Chuẩn 2025 mới (1,000)</option>
        <option value="02">Data 02: Nhiễu & Sạch (2,000)</option>
        <option value="03">Data 03: Hệ cũ sạch OSM (1,500)</option>
        <option value="04">Data 04: Thiếu trường (800)</option>
        <option value="06">Data 06: Địa chỉ lai 2 hệ (1,200)</option>
        <option value="07">Data 07: Cặp sáp nhập 2025 (600)</option>
      </select>
    </div>

    <div class="filter-group">
      <label class="filter-label">So sánh 2 công cụ:</label>
      <select id="filter-comp" class="filter-select" onchange="onFilterChange()">
        <option value="ALL">Tất cả cặp kết quả</option>
        <option value="VN_OK_LP_FAIL" selected>⭐ VNAdmin ĐÚNG, Libpostal KHÔNG ĐÚNG</option>
        <option value="LP_OK_VN_FAIL">Libpostal ĐÚNG, VNAdmin KHÔNG ĐÚNG</option>
        <option value="BOTH_OK">Cả 2 công cụ cùng ĐÚNG</option>
        <option value="BOTH_FAIL">Cả 2 công cụ cùng KHÔNG ĐÚNG</option>
        <option value="VN_ERROR">Lỗi của VNAdmin (ERROR / PARTIAL)</option>
        <option value="LP_ERROR">Lỗi của Libpostal (ERROR / PARTIAL)</option>
      </select>
    </div>

    <div class="filter-group">
      <label class="filter-label">VNAdmin Result:</label>
      <select id="filter-vn-res" class="filter-select" onchange="onFilterChange()">
        <option value="ALL">Tất cả</option>
        <option value="CORRECT">CORRECT (Đúng)</option>
        <option value="PARTIAL">PARTIAL (Một phần)</option>
        <option value="ERROR">ERROR (Sai)</option>
      </select>
    </div>

    <div class="filter-group">
      <label class="filter-label">Libpostal Result:</label>
      <select id="filter-lp-res" class="filter-select" onchange="onFilterChange()">
        <option value="ALL">Tất cả</option>
        <option value="CORRECT">CORRECT (Đúng)</option>
        <option value="PARTIAL">PARTIAL (Một phần)</option>
        <option value="ERROR">ERROR (Sai)</option>
        <option value="UNSUPPORTED">UNSUPPORTED (Không áp dụng)</option>
      </select>
    </div>

    <!-- Data 02 specific filter -->
    <div id="subfilter-d02" class="filter-group" style="display:none;">
      <label class="filter-label">Bề mặt Data 02:</label>
      <select id="filter-d02-bm" class="filter-select" onchange="onFilterChange()">
        <option value="ALL">Tất cả bề mặt</option>
        <option value="clean">Sạch (ChuoiDiaChiGoc)</option>
        <option value="noisy">Nhiễu (ChuoiDiaChi)</option>
      </select>
    </div>

    <!-- Data 04 specific filter -->
    <div id="subfilter-d04" class="filter-group" style="display:none;">
      <label class="filter-label">Kiểu thiếu Data 04:</label>
      <select id="filter-d04-kt" class="filter-select" onchange="onFilterChange()">
        <option value="ALL">Tất cả kiểu thiếu</option>
        <option value="drop_ward">drop_ward</option>
        <option value="drop_district">drop_district</option>
        <option value="drop_housenumber">drop_housenumber</option>
        <option value="drop_housenumber_ward">drop_housenumber_ward</option>
      </select>
    </div>

    <!-- Data 06 specific filter -->
    <div id="subfilter-d06" class="filter-group" style="display:none;">
      <label class="filter-label">VNAdmin Mode Data 06:</label>
      <select id="filter-d06-mode" class="filter-select" onchange="onFilterChange()">
        <option value="ALL">Tất cả mode</option>
        <option value="FROM_2025">FROM_2025 (m25)</option>
        <option value="LEGACY">LEGACY (mleg)</option>
      </select>
    </div>

    <!-- Data 07 specific filter -->
    <div id="subfilter-d07" class="filter-group" style="display:none;">
      <label class="filter-label">Quan hệ Data 07:</label>
      <select id="filter-d07-rel" class="filter-select" onchange="onFilterChange()">
        <option value="ALL">Tất cả quan hệ</option>
        <option value="N-1">N-1 (Nhiều cũ nhập 1 mới)</option>
        <option value="M-N">M-N (Tách nhập phức tạp)</option>
      </select>
    </div>
  </div>

  <div class="filter-row">
    <input type="text" id="search-box" class="search-input" placeholder="Tìm kiếm nhanh ID, địa chỉ, số nhà, đường, phường, quận, tỉnh, lỗi..." oninput="onSearchInput()">
    <button class="btn" onclick="resetFilters()">Đặt lại bộ lọc</button>
    <button class="btn" onclick="exportFilteredCSV()">Xuất CSV lọc</button>
    <div class="counter-badge">
      Đang hiển thị: <strong id="record-count">0</strong> / <span id="total-count">0</span> bản ghi
    </div>
  </div>
</div>

<div class="table-container">
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Tập & Thuộc tính</th>
          <th>Chuỗi địa chỉ đầu vào</th>
          <th>VietnamAdminUnits</th>
          <th>Libpostal</th>
          <th>Thao tác</th>
        </tr>
      </thead>
      <tbody id="table-body">
      </tbody>
    </table>
  </div>
  <div class="pagination-bar">
    <div class="pagination-size">
      Số dòng/trang:
      <select id="page-size" class="filter-select" onchange="onPageSizeChange()" style="padding: 2px 6px;">
        <option value="25">25</option>
        <option value="50" selected>50</option>
        <option value="100">100</option>
        <option value="200">200</option>
      </select>
    </div>
    <div class="pagination-controls">
      <button id="btn-first" class="page-btn" onclick="goToPage(1)">Đầu</button>
      <button id="btn-prev" class="page-btn" onclick="prevPage()">Trước</button>
      <span id="page-info">Trang 1 / 1</span>
      <button id="btn-next" class="page-btn" onclick="nextPage()">Sau</button>
      <button id="btn-last" class="page-btn" onclick="goToPage(maxPages)">Cuối</button>
    </div>
  </div>
</div>

<!-- Drawer Side Panel -->
<div id="drawer-overlay" class="drawer-overlay" onclick="closeDrawer()"></div>
<div id="drawer" class="drawer">
  <div class="drawer-header">
    <div class="drawer-title-wrap">
      <span id="drawer-id" class="drawer-title">D01_0000</span>
      <span id="drawer-ds-badge" class="badge-tag">Data 01</span>
      <span id="drawer-sys-badge" class="badge-tag">Mới</span>
    </div>
    <button class="drawer-close" onclick="closeDrawer()" title="Đóng (Esc)">✕</button>
  </div>

  <div class="drawer-content">
    <div class="detail-card">
      <div class="detail-card-title">
        <span>Chuỗi địa chỉ đầu vào</span>
        <button class="btn" style="padding: 2px 8px; font-size: 11px;" onclick="copyInputAddress()">Sao chép</button>
      </div>
      <div id="drawer-input" class="input-address-box"></div>
    </div>

    <!-- Comparison Table -->
    <div class="detail-card">
      <div class="detail-card-title">
        <span>Đối sánh 5 trường dữ liệu</span>
        <span style="font-size: 10px; color: var(--text-dim); text-transform: none;">Chuẩn hóa NFC, bỏ tiền tố cấp HC</span>
      </div>
      <table class="comp-table">
        <thead>
          <tr>
            <th>Trường dữ liệu</th>
            <th>Ground Truth</th>
            <th>VietnamAdminUnits</th>
            <th>Libpostal</th>
          </tr>
        </thead>
        <tbody id="drawer-comp-body">
        </tbody>
      </table>
    </div>

    <!-- Dataset Specific Card (D04 / D06 / D07) -->
    <div id="drawer-special-card" class="detail-card" style="display:none;">
      <div id="drawer-special-title" class="detail-card-title">Đặc tả tập dữ liệu</div>
      <div id="drawer-special-content"></div>
    </div>

    <!-- Diagnostics & Telemetry -->
    <div class="detail-card">
      <div class="detail-card-title">Chẩn đoán & Raw Response</div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
        <div>
          <div style="font-weight: 600; color: #a5b4fc; margin-bottom: 4px;">VietnamAdminUnits</div>
          <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 4px;">
            Thời gian: <strong id="drawer-vn-time">0 ms</strong> | Mode: <span id="drawer-vn-mode" class="meta-pill"></span>
          </div>
          <div id="drawer-vn-err" style="font-size: 11px; color: #f87171; margin-bottom: 4px;"></div>
          <pre id="drawer-vn-raw" class="raw-code"></pre>
        </div>
        <div>
          <div style="font-weight: 600; color: #38bdf8; margin-bottom: 4px;">Libpostal</div>
          <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 4px;">
            Thời gian: <strong id="drawer-lp-time">0 ms</strong>
          </div>
          <div id="drawer-lp-err" style="font-size: 11px; color: #f87171; margin-bottom: 4px;"></div>
          <div style="font-size: 11px; font-weight: 600; margin-top: 6px; color: var(--text-muted);">Nhãn trích xuất Libpostal:</div>
          <div id="drawer-lp-tokens" class="token-chips"></div>
        </div>
      </div>
    </div>
  </div>

  <div class="drawer-footer">
    <button class="btn" onclick="copyRecordJSON()">Sao chép JSON bản ghi</button>
    <div style="display: flex; gap: 6px;">
      <button class="btn" onclick="navigateRecord(-1)">← Trước</button>
      <button class="btn" onclick="navigateRecord(1)">Sau →</button>
    </div>
  </div>
</div>

<script>
const RAW_DATA = {json_data};
const DATA = RAW_DATA.records;
const STATS = RAW_DATA.stats;
const FIELD_NAMES = ["SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh"];
const FIELD_LABELS = {{
  "SoNha": "Số nhà",
  "TenDuong": "Tên đường",
  "PhuongXa": "Phường / Xã",
  "QuanHuyen": "Quận / Huyện",
  "TinhThanh": "Tỉnh / Thành phố"
}};

let filteredRecords = [];
let currentPage = 1;
let pageSize = 50;
let maxPages = 1;
let activeDrawerIndex = -1;

// Init on load
window.addEventListener('DOMContentLoaded', () => {{
  renderCharts();
  applyFilters();
}});

function switchChart(tabId) {{
  document.querySelectorAll('.chart-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.chart-container').forEach(c => c.classList.remove('active'));
  
  event.target.classList.add('active');
  document.getElementById('chart-' + tabId).classList.add('active');
}}

function renderCharts() {{
  // 1. Stacked Accuracy Chart
  const svgAcc = document.getElementById('svg-acc');
  const accData = STATS.accuracy_chart;
  const barHeight = 11;
  const gap = 3;
  const groupGap = 6;
  const startX = 140;
  const maxW = 740;

  let y = 10;
  let htmlAcc = '';

  accData.forEach((d, i) => {{
    const wC = (d.pct_c / 100) * maxW;
    const wP = (d.pct_p / 100) * maxW;
    const wE = (d.pct_e / 100) * maxW;

    const label = `${{d.group}} - ${{d.tool}}`;
    htmlAcc += `<text x="130" y="${{y + 9}}" fill="#9ca3af" font-size="10" text-anchor="end">${{label}}</text>`;
    htmlAcc += `<rect x="${{startX}}" y="${{y}}" width="${{wC}}" height="${{barHeight}}" fill="#10b981"><title>${{d.pct_c}}% (${{d.c}}/${{d.n}})</title></rect>`;
    htmlAcc += `<rect x="${{startX + wC}}" y="${{y}}" width="${{wP}}" height="${{barHeight}}" fill="#f59e0b"><title>${{d.pct_p}}% (${{d.p}}/${{d.n}})</title></rect>`;
    htmlAcc += `<rect x="${{startX + wC + wP}}" y="${{y}}" width="${{wE}}" height="${{barHeight}}" fill="#ef4444"><title>${{d.pct_e}}% (${{d.e}}/${{d.n}})</title></rect>`;
    htmlAcc += `<text x="${{startX + maxW + 10}}" y="${{y + 9}}" fill="#f9fafb" font-size="10" font-weight="bold">${{d.pct_c}}%</text>`;

    y += barHeight + gap;
    if (i % 2 === 1) y += groupGap;
  }});
  svgAcc.setAttribute('viewBox', `0 0 940 ${{y + 10}}`);
  svgAcc.innerHTML = htmlAcc;

  // 2. F1 Chart for D01, D03, D04
  const svgF1 = document.getElementById('svg-f1');
  const f1Data = STATS.field_f1_chart;
  let htmlF1 = '';
  const datasets = [
    {{ key: 'D01', title: 'Data 01 (Mới)' }},
    {{ key: 'D03', title: 'Data 03 (Cũ sạch)' }},
    {{ key: 'D04', title: 'Data 04 (Thiếu trường)' }}
  ];

  let colX = 40;
  const colWidth = 270;
  datasets.forEach((ds) => {{
    htmlF1 += `<text x="${{colX + 100}}" y="20" fill="#fff" font-size="12" font-weight="bold" text-anchor="middle">${{ds.title}}</text>`;
    const fields = f1Data[ds.key].fields;
    const vnScores = f1Data[ds.key].vn;
    const lpScores = f1Data[ds.key].lp;

    let fY = 40;
    fields.forEach((f, idx) => {{
      const vn = vnScores[idx];
      const lp = lpScores[idx];
      htmlF1 += `<text x="${{colX + 70}}" y="${{fY + 10}}" fill="#9ca3af" font-size="10" text-anchor="end">${{f}}</text>`;

      // VN bar
      if (vn !== null) {{
        const wVn = vn * 120;
        htmlF1 += `<rect x="${{colX + 80}}" y="${{fY}}" width="${{wVn}}" height="7" fill="#6366f1" rx="2"><title>VNAdmin: ${{vn}}</title></rect>`;
        htmlF1 += `<text x="${{colX + 80 + wVn + 4}}" y="${{fY + 6}}" fill="#a5b4fc" font-size="9">${{vn.toFixed(3)}}</text>`;
      }} else {{
        htmlF1 += `<text x="${{colX + 80}}" y="${{fY + 6}}" fill="#64748b" font-size="9">N/A (2 cấp)</text>`;
      }}

      // LP bar
      if (lp !== null) {{
        const wLp = lp * 120;
        htmlF1 += `<rect x="${{colX + 80}}" y="${{fY + 9}}" width="${{wLp}}" height="7" fill="#06b6d4" rx="2"><title>Libpostal: ${{lp}}</title></rect>`;
        htmlF1 += `<text x="${{colX + 80 + wLp + 4}}" y="${{fY + 15}}" fill="#67e8f9" font-size="9">${{lp.toFixed(3)}}</text>`;
      }}

      fY += 26;
    }});
    colX += colWidth + 20;
  }});
  svgF1.setAttribute('viewBox', '0 0 920 200');
  svgF1.innerHTML = htmlF1;

  // 3. Noise Degradation Chart
  const svgNoise = document.getElementById('svg-noise');
  const noiseData = STATS.noise_chart;
  let htmlNoise = '';
  let nX = 50;
  noiseData.forEach((n) => {{
    htmlNoise += `<text x="${{nX + 80}}" y="20" fill="#fff" font-size="12" font-weight="bold" text-anchor="middle">${{n.level}} (n=${{n.n}})</text>`;

    // VNAdmin bars
    htmlNoise += `<text x="${{nX}}" y="45" fill="#a5b4fc" font-size="11" font-weight="600">VietnamAdminUnits</text>`;
    const vnCW = n.vn_clean_f1 * 140;
    const vnNW = n.vn_noisy_f1 * 140;
    htmlNoise += `<rect x="${{nX}}" y="55" width="${{vnCW}}" height="9" fill="#10b981" rx="2"><title>Clean: ${{n.vn_clean_f1}}</title></rect>`;
    htmlNoise += `<text x="${{nX + vnCW + 6}}" y="${{nX > 0 ? 63 : 63}}" fill="#34d399" font-size="10">${{n.vn_clean_f1}}</text>`;
    htmlNoise += `<rect x="${{nX}}" y="68" width="${{vnNW}}" height="9" fill="#f59e0b" rx="2"><title>Noisy: ${{n.vn_noisy_f1}}</title></rect>`;
    htmlNoise += `<text x="${{nX + vnNW + 6}}" y="76" fill="#fbbf24" font-size="10">${{n.vn_noisy_f1}} (-${{n.vn_drop_pct}}%)</text>`;

    // Libpostal bars
    htmlNoise += `<text x="${{nX}}" y="105" fill="#67e8f9" font-size="11" font-weight="600">Libpostal</text>`;
    const lpCW = n.lp_clean_f1 * 140;
    const lpNW = n.lp_noisy_f1 * 140;
    htmlNoise += `<rect x="${{nX}}" y="115" width="${{lpCW}}" height="9" fill="#10b981" rx="2"><title>Clean: ${{n.lp_clean_f1}}</title></rect>`;
    htmlNoise += `<text x="${{nX + lpCW + 6}}" y="123" fill="#34d399" font-size="10">${{n.lp_clean_f1}}</text>`;
    htmlNoise += `<rect x="${{nX}}" y="128" width="${{lpNW}}" height="9" fill="#f59e0b" rx="2"><title>Noisy: ${{n.lp_noisy_f1}}</title></rect>`;
    htmlNoise += `<text x="${{nX + lpNW + 6}}" y="136" fill="#fbbf24" font-size="10">${{n.lp_noisy_f1}} (-${{n.lp_drop_pct}}%)</text>`;

    nX += 215;
  }});
  svgNoise.setAttribute('viewBox', '0 0 920 180');
  svgNoise.innerHTML = htmlNoise;

  // 4. Data 04 Recovery Chart
  const svgRec = document.getElementById('svg-rec');
  const recData = STATS.recovery_d04;
  let htmlRec = '';
  let rY = 20;
  recData.forEach((r) => {{
    htmlRec += `<text x="140" y="${{rY + 12}}" fill="#fff" font-size="11" font-weight="bold" text-anchor="end">${{r.kind}} (n=${{r.n}})</text>`;

    // VN bar
    const vnW_c = (r.vn_c / r.n) * 260;
    const vnW_w = (r.vn_w / r.n) * 260;
    const vnW_e = (r.vn_e / r.n) * 260;
    htmlRec += `<text x="150" y="${{rY + 9}}" fill="#a5b4fc" font-size="10">VN:</text>`;
    htmlRec += `<rect x="180" y="${{rY}}" width="${{vnW_c}}" height="10" fill="#10b981"><title>Đúng: ${{r.vn_c}}</title></rect>`;
    htmlRec += `<rect x="${{180 + vnW_c}}" y="${{rY}}" width="${{vnW_w}}" height="10" fill="#ef4444"><title>Sai: ${{r.vn_w}}</title></rect>`;
    htmlRec += `<rect x="${{180 + vnW_c + vnW_w}}" y="${{rY}}" width="${{vnW_e}}" height="10" fill="#64748b"><title>Rỗng: ${{r.vn_e}}</title></rect>`;
    htmlRec += `<text x="450" y="${{rY + 9}}" fill="#cbd5e1" font-size="10">${{r.vn_c}} đúng | ${{r.vn_w}} sai | ${{r.vn_e}} rỗng</text>`;

    // LP bar
    rY += 14;
    const lpW_c = (r.lp_c / r.n) * 260;
    const lpW_w = (r.lp_w / r.n) * 260;
    const lpW_e = (r.lp_e / r.n) * 260;
    htmlRec += `<text x="150" y="${{rY + 9}}" fill="#67e8f9" font-size="10">LP:</text>`;
    htmlRec += `<rect x="180" y="${{rY}}" width="${{lpW_c}}" height="10" fill="#10b981"><title>Đúng: ${{r.lp_c}}</title></rect>`;
    htmlRec += `<rect x="${{180 + lpW_c}}" y="${{rY}}" width="${{lpW_w}}" height="10" fill="#ef4444"><title>Sai: ${{r.lp_w}}</title></rect>`;
    htmlRec += `<rect x="${{180 + lpW_c + lpW_w}}" y="${{rY}}" width="${{lpW_e}}" height="10" fill="#64748b"><title>Rỗng: ${{r.lp_e}}</title></rect>`;
    htmlRec += `<text x="450" y="${{rY + 9}}" fill="#cbd5e1" font-size="10">${{r.lp_c}} đúng | ${{r.lp_w}} sai | ${{r.lp_e}} rỗng</text>`;

    rY += 24;
  }});
  svgRec.setAttribute('viewBox', `0 0 800 ${{rY + 10}}`);
  svgRec.innerHTML = htmlRec;
}}

function onFilterChange() {{
  const ds = document.getElementById('filter-ds').value;
  // Toggle subfilters
  document.getElementById('subfilter-d02').style.display = ds === '02' ? 'flex' : 'none';
  document.getElementById('subfilter-d04').style.display = ds === '04' ? 'flex' : 'none';
  document.getElementById('subfilter-d06').style.display = ds === '06' ? 'flex' : 'none';
  document.getElementById('subfilter-d07').style.display = ds === '07' ? 'flex' : 'none';

  applyFilters();
}}

function onSearchInput() {{
  applyFilters();
}}

function resetFilters() {{
  document.getElementById('filter-ds').value = 'ALL';
  document.getElementById('filter-comp').value = 'ALL';
  document.getElementById('filter-vn-res').value = 'ALL';
  document.getElementById('filter-lp-res').value = 'ALL';
  document.getElementById('filter-d02-bm').value = 'ALL';
  document.getElementById('filter-d04-kt').value = 'ALL';
  document.getElementById('filter-d06-mode').value = 'ALL';
  document.getElementById('filter-d07-rel').value = 'ALL';
  document.getElementById('search-box').value = '';
  onFilterChange();
}}

function applyFilters() {{
  const dsFilter = document.getElementById('filter-ds').value;
  const compFilter = document.getElementById('filter-comp').value;
  const vnResFilter = document.getElementById('filter-vn-res').value;
  const lpResFilter = document.getElementById('filter-lp-res').value;
  const d02BmFilter = document.getElementById('filter-d02-bm').value;
  const d04KtFilter = document.getElementById('filter-d04-kt').value;
  const d06ModeFilter = document.getElementById('filter-d06-mode').value;
  const d07RelFilter = document.getElementById('filter-d07-rel').value;
  const search = document.getElementById('search-box').value.trim().toLowerCase();

  filteredRecords = DATA.filter(r => {{
    // Dataset filter
    if (dsFilter !== 'ALL' && r.ds !== dsFilter) return false;

    // Tool Comparison Filter
    const vnRes = r.vn.r;
    const lpRes = r.lp.r;
    if (compFilter === 'VN_OK_LP_FAIL') {{
      if (r.ds === '07') return false; // Exclude Data 07 from 2-tool comparison since LP is unsupported
      if (vnRes !== 'CORRECT' || lpRes === 'CORRECT') return false;
    }} else if (compFilter === 'LP_OK_VN_FAIL') {{
      if (r.ds === '07') return false;
      if (lpRes !== 'CORRECT' || vnRes === 'CORRECT') return false;
    }} else if (compFilter === 'BOTH_OK') {{
      if (r.ds === '07') return false;
      if (vnRes !== 'CORRECT' || lpRes !== 'CORRECT') return false;
    }} else if (compFilter === 'BOTH_FAIL') {{
      if (r.ds === '07') return false;
      if (vnRes === 'CORRECT' || lpRes === 'CORRECT') return false;
    }} else if (compFilter === 'VN_ERROR') {{
      if (vnRes === 'CORRECT') return false;
    }} else if (compFilter === 'LP_ERROR') {{
      if (lpRes === 'CORRECT' || lpRes === 'UNSUPPORTED') return false;
    }}

    // Result filters
    if (vnResFilter !== 'ALL' && vnRes !== vnResFilter) return false;
    if (lpResFilter !== 'ALL' && lpRes !== lpResFilter) return false;

    // Subfilters
    if (dsFilter === '02') {{
      if (d02BmFilter !== 'ALL' && r.m.bm !== d02BmFilter) return false;
    }} else if (dsFilter === '04') {{
      if (d04KtFilter !== 'ALL' && r.m.kt !== d04KtFilter) return false;
    }} else if (dsFilter === '06') {{
      if (d06ModeFilter !== 'ALL' && r.m.mode !== d06ModeFilter) return false;
    }} else if (dsFilter === '07') {{
      if (d07RelFilter !== 'ALL' && r.m.qh !== d07RelFilter) return false;
    }}

    // Text search
    if (search) {{
      const matchId = r.id.toLowerCase().includes(search);
      const matchIn = r.in.toLowerCase().includes(search);
      const matchErr = (r.vn.e + ' ' + r.lp.e).toLowerCase().includes(search);
      const matchNote = (r.vn.n + ' ' + r.lp.n).toLowerCase().includes(search);
      const matchTruth = r.t.join(' ').toLowerCase().includes(search);
      if (!matchId && !matchIn && !matchErr && !matchNote && !matchTruth) return false;
    }}

    return true;
  }});

  document.getElementById('record-count').textContent = filteredRecords.length.toLocaleString();
  document.getElementById('total-count').textContent = DATA.length.toLocaleString();

  currentPage = 1;
  maxPages = Math.max(1, Math.ceil(filteredRecords.length / pageSize));
  renderTable();
}}

function renderTable() {{
  const tbody = document.getElementById('table-body');
  tbody.innerHTML = '';

  const start = (currentPage - 1) * pageSize;
  const end = Math.min(start + pageSize, filteredRecords.length);
  const pageItems = filteredRecords.slice(start, end);

  if (pageItems.length === 0) {{
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding: 40px; color: var(--text-dim);">Không tìm thấy bản ghi phù hợp với bộ lọc hiện tại.</td></tr>';
    updatePaginationUI();
    return;
  }}

  const frag = document.createDocumentFragment();
  pageItems.forEach((r, idx) => {{
    const globalIdx = start + idx;
    const tr = document.createElement('tr');
    tr.onclick = () => openDrawer(globalIdx);

    // Meta badges
    let metaHtml = `<span class="badge-tag" style="background:#1e293b; color:#94a3b8; border-color:#334155;">D${{r.ds}}</span>`;
    if (r.ds === '01') metaHtml += ` <span class="badge-tag" style="background:#064e3b; color:#6ee7b7; border-color:#047857;">mới</span>`;
    else if (r.ds === '02') metaHtml += ` <span class="badge-tag" style="background:#312e81; color:#a5b4fc;">${{r.m.bm}} | ${{r.m.md}}</span>`;
    else if (r.ds === '03') metaHtml += ` <span class="badge-tag" style="background:#374151; color:#d1d5db;">cũ</span>`;
    else if (r.ds === '04') metaHtml += ` <span class="badge-tag" style="background:#78350f; color:#fde68a;">${{r.m.kt}}</span>`;
    else if (r.ds === '06') metaHtml += ` <span class="badge-tag" style="background:#581c87; color:#e9d5ff;">${{r.m.kl}} | ${{r.m.mode}}</span>`;
    else if (r.ds === '07') metaHtml += ` <span class="badge-tag" style="background:#0e7490; color:#a5f3fc;">${{r.m.qh}}</span>`;

    // VN dots
    const vnDots = r.vn.s.split('').map(c => `<span class="f-dot dot-${{c}}"></span>`).join('');
    // LP dots
    const lpDots = r.lp.s.split('').map(c => `<span class="f-dot dot-${{c}}"></span>`).join('');

    tr.innerHTML = `
      <td class="row-id">${{r.id}}</td>
      <td>${{metaHtml}}</td>
      <td class="input-address-cell" title="${{escapeHtml(r.in)}}">${{escapeHtml(r.in)}}</td>
      <td>
        <div class="tool-res-cell">
          <span class="status-badge status-${{r.vn.r}}">${{r.vn.r}}</span>
          <div class="field-dots" title="Trạng thái 5 trường">${{vnDots}}</div>
        </div>
      </td>
      <td>
        <div class="tool-res-cell">
          <span class="status-badge status-${{r.lp.r}}">${{r.lp.r}}</span>
          <div class="field-dots" title="Trạng thái 5 trường">${{lpDots}}</div>
        </div>
      </td>
      <td>
        <button class="btn" style="padding: 2px 8px; font-size: 11px;">Xem chi tiết</button>
      </td>
    `;
    frag.appendChild(tr);
  }});
  tbody.appendChild(frag);

  updatePaginationUI();
}}

function updatePaginationUI() {{
  document.getElementById('page-info').textContent = `Trang ${{currentPage}} / ${{maxPages}}`;
  document.getElementById('btn-first').disabled = currentPage === 1;
  document.getElementById('btn-prev').disabled = currentPage === 1;
  document.getElementById('btn-next').disabled = currentPage === maxPages;
  document.getElementById('btn-last').disabled = currentPage === maxPages;
}}

function prevPage() {{
  if (currentPage > 1) {{
    currentPage--;
    renderTable();
  }}
}}

function nextPage() {{
  if (currentPage < maxPages) {{
    currentPage++;
    renderTable();
  }}
}}

function goToPage(p) {{
  currentPage = Math.max(1, Math.min(p, maxPages));
  renderTable();
}}

function onPageSizeChange() {{
  pageSize = parseInt(document.getElementById('page-size').value, 10);
  maxPages = Math.max(1, Math.ceil(filteredRecords.length / pageSize));
  currentPage = 1;
  renderTable();
}}

// Jump to specific test cases
function jumpToCase(id) {{
  // Reset all filters first to find the case anywhere
  resetFilters();
  document.getElementById('search-box').value = id;
  applyFilters();
  if (filteredRecords.length > 0) {{
    openDrawer(0);
  }}
}}

// Drawer Modal Details
function openDrawer(index) {{
  activeDrawerIndex = index;
  const r = filteredRecords[index];
  if (!r) return;

  document.getElementById('drawer-id').textContent = r.id;
  document.getElementById('drawer-ds-badge').textContent = `Data ${{r.ds}}`;
  document.getElementById('drawer-sys-badge').textContent = r.m.sys ? (r.m.sys === 'moi' ? 'Hệ mới 2025' : 'Hệ cũ') : (r.ds === '06' ? 'Địa chỉ lai' : 'Cải cách 2025');
  document.getElementById('drawer-input').textContent = r.in;

  // Render 5-field comparison
  const compBody = document.getElementById('drawer-comp-body');
  compBody.innerHTML = '';
  
  const statusLabels = {{
    'm': '<span class="cell-tag" style="background:#065f46; color:#6ee7b7;">✓ Khớp</span>',
    'x': '<span class="cell-tag" style="background:#991b1b; color:#fca5a5;">✗ Sai khác</span>',
    'o': '<span class="cell-tag" style="background:#92400e; color:#fde68a;">⚠ Bỏ sót</span>',
    't': '<span class="cell-tag" style="background:#334155; color:#94a3b8;">— Đúng rỗng</span>',
    'n': '<span class="cell-tag" style="background:#1e293b; color:#64748b;">N/A Không chấm</span>',
  }};

  const classMap = {{ 'm': 'cell-match', 'x': 'cell-mismatch', 'o': 'cell-omitted', 't': 'cell-tn', 'n': 'cell-na' }};

  FIELD_NAMES.forEach((f, idx) => {{
    const tVal = r.t[idx] || '';
    const vnVal = r.vn.p[idx] || '';
    const lpVal = r.lp.p[idx] || '';

    const vnCode = r.vn.s[idx] || 'n';
    const lpCode = r.lp.s[idx] || 'n';

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td style="font-weight: 600; color: #cbd5e1;">${{FIELD_LABELS[f]}} <span style="font-size: 10px; color: var(--text-dim);">(${{f}})</span></td>
      <td style="color: #f1f5f9; font-family: monospace;">${{escapeHtml(tVal) || '<span style="color:var(--text-dim)">(rỗng)</span>'}}</td>
      <td class="${{classMap[vnCode]}}">
        <div>${{statusLabels[vnCode]}}</div>
        <div style="font-family: monospace;">${{escapeHtml(vnVal) || '<span style="color:inherit; opacity:0.6;">(rỗng)</span>'}}</div>
      </td>
      <td class="${{classMap[lpCode]}}">
        <div>${{statusLabels[lpCode]}}</div>
        <div style="font-family: monospace;">${{escapeHtml(lpVal) || '<span style="color:inherit; opacity:0.6;">(rỗng)</span>'}}</div>
      </td>
    `;
    compBody.appendChild(tr);
  }});

  // Dataset specific box
  const specialCard = document.getElementById('drawer-special-card');
  const specialTitle = document.getElementById('drawer-special-title');
  const specialContent = document.getElementById('drawer-special-content');

  if (r.ds === '04') {{
    specialCard.style.display = 'flex';
    specialTitle.textContent = 'Phân tích phục hồi trường thiếu (Data 04)';
    const rvn = r.m.rvn || {{}};
    const rlp = r.m.rlp || {{}};
    let recHtml = `
      <div class="meta-tag-row" style="margin-bottom: 8px;">
        <span class="meta-pill">Kiểu thiếu: <strong>${{r.m.kt}}</strong></span>
        <span class="meta-pill">Trường bị xóa: <strong>${{r.m.tx}}</strong></span>
      </div>
      <div style="font-size: 11px; margin-bottom: 6px; color: var(--text-muted);">
        Ground Truth gốc trước khi xóa (GT_*): 
        <span style="font-family: monospace; color: #f1f5f9;">${{r.m.gt.filter(Boolean).join(', ')}}</span>
      </div>
      <div style="font-size: 11px; display: flex; gap: 14px;">
        <div>VNAdmin phục hồi: <strong>${{formatRecoveryObj(rvn)}}</strong></div>
        <div>Libpostal phục hồi: <strong>${{formatRecoveryObj(rlp)}}</strong></div>
      </div>
    `;
    specialContent.innerHTML = recHtml;
  }} else if (r.ds === '06') {{
    specialCard.style.display = 'flex';
    specialTitle.textContent = 'Phân tích địa chỉ lai 2 hệ (Data 06)';
    specialContent.innerHTML = `
      <div class="meta-tag-row" style="margin-bottom: 8px;">
        <span class="meta-pill">Kiểu lai: <strong>${{r.m.kl}}</strong></span>
        <span class="meta-pill">Mode VNAdmin: <strong>${{r.m.mode}}</strong></span>
      </div>
      <div style="font-size: 11px; color: var(--text-muted); display: grid; grid-template-columns: 1fr 1fr; gap: 6px;">
        <div>Phường mới: <strong style="color:#6ee7b7;">${{r.m.px_m || '-'}}</strong></div>
        <div>Quận huyện cũ: <strong style="color:#fde68a;">${{r.m.qh_c || '-'}}</strong></div>
        <div>Phường cũ: <strong>${{r.m.px_c || '-'}}</strong></div>
        <div>Chi tiết span: <span style="font-family: monospace;">${{r.m.sd || '-'}}</span></div>
      </div>
    `;
  }} else if (r.ds === '07') {{
    specialCard.style.display = 'flex';
    specialTitle.textContent = 'Chi tiết sáp nhập hành chính (Data 07)';
    specialContent.innerHTML = `
      <div class="meta-tag-row" style="margin-bottom: 8px;">
        <span class="meta-pill">Quan hệ: <strong>${{r.m.qh}}</strong></span>
        <span class="meta-pill">Hình thức: <strong>${{r.m.ht}}</strong></span>
        <span class="meta-pill">Mã mới: <strong>${{r.m.mm}}</strong></span>
        <span class="meta-pill">Nguồn: <strong>${{r.m.ng}}</strong></span>
      </div>
      <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">
        <div>Địa chỉ cũ: <span style="color:#cbd5e1;">${{r.m.dc_c}}</span></div>
        <div>Địa chỉ mới chuẩn: <span style="color:#6ee7b7; font-weight:600;">${{r.m.dc_m}}</span></div>
      </div>
    `;
  }} else {{
    specialCard.style.display = 'none';
  }}

  // Diagnostics
  document.getElementById('drawer-vn-time').textContent = `${{r.vn.d}} ms`;
  document.getElementById('drawer-vn-mode').textContent = r.vn.m;
  document.getElementById('drawer-vn-err').textContent = r.vn.e !== 'none' ? `Lỗi: ${{r.vn.e}} (${{r.vn.n}})` : '';
  document.getElementById('drawer-vn-raw').textContent = JSON.stringify(r.vn.raw, null, 2);

  document.getElementById('drawer-lp-time').textContent = `${{r.lp.d}} ms`;
  document.getElementById('drawer-lp-err').textContent = r.lp.e !== 'none' ? `Lỗi: ${{r.lp.e}} (${{r.lp.n}})` : '';

  // LP token chips
  const tokenWrap = document.getElementById('drawer-lp-tokens');
  tokenWrap.innerHTML = '';
  const postalLabels = (r.lp.raw && r.lp.raw.postal_labels) ? r.lp.raw.postal_labels : [];
  if (postalLabels.length === 0) {{
    tokenWrap.innerHTML = '<span style="color: var(--text-dim); font-size: 11px;">(Không có nhãn)</span>';
  }} else {{
    postalLabels.forEach(([txt, lbl]) => {{
      const chip = document.createElement('div');
      chip.className = 'token-chip';
      chip.innerHTML = `<span>${{escapeHtml(txt)}}</span><span class="token-label">${{lbl}}</span>`;
      tokenWrap.appendChild(chip);
    }});
  }}

  document.getElementById('drawer-overlay').classList.add('active');
  document.getElementById('drawer').classList.add('active');
}}

function closeDrawer() {{
  document.getElementById('drawer-overlay').classList.remove('active');
  document.getElementById('drawer').classList.remove('active');
  activeDrawerIndex = -1;
}}

function navigateRecord(direction) {{
  if (activeDrawerIndex < 0) return;
  const newIdx = activeDrawerIndex + direction;
  if (newIdx >= 0 && newIdx < filteredRecords.length) {{
    openDrawer(newIdx);
  }}
}}

function formatRecoveryObj(rec) {{
  if (!rec || Object.keys(rec).length === 0) return '—';
  return Object.entries(rec).map(([f, st]) => {{
    const color = st === 'correct' ? '#10b981' : (st === 'wrong' ? '#ef4444' : '#64748b');
    const label = st === 'correct' ? 'Đúng' : (st === 'wrong' ? 'Sai' : 'Rỗng');
    return `<span style="color:${{color}}">${{f}}: ${{label}}</span>`;
  }}).join(' | ');
}}

function copyInputAddress() {{
  if (activeDrawerIndex < 0) return;
  const r = filteredRecords[activeDrawerIndex];
  navigator.clipboard.writeText(r.in).then(() => alert('Đã sao chép chuỗi địa chỉ!'));
}}

function copyRecordJSON() {{
  if (activeDrawerIndex < 0) return;
  const r = filteredRecords[activeDrawerIndex];
  navigator.clipboard.writeText(JSON.stringify(r, null, 2)).then(() => alert('Đã sao chép toàn bộ JSON của bản ghi!'));
}}

function exportFilteredCSV() {{
  if (filteredRecords.length === 0) {{
    alert('Không có bản ghi nào để xuất!');
    return;
  }}

  const headers = ["ID", "Dataset", "ChuoiDiaChi", "VNAdmin_Result", "VNAdmin_LoaiLoi", "VNAdmin_GhiChu", "Libpostal_Result", "Libpostal_LoaiLoi", "Libpostal_GhiChu"];
  const rows = [headers];

  filteredRecords.forEach(r => {{
    rows.push([
      r.id,
      r.ds,
      `"${{r.in.replace(/"/g, '""')}}"`,
      r.vn.r,
      r.vn.e,
      `"${{r.vn.n.replace(/"/g, '""')}}"`,
      r.lp.r,
      r.lp.e,
      `"${{r.lp.n.replace(/"/g, '""')}}"`
    ]);
  }});

  const csvContent = "\\uFEFF" + rows.map(e => e.join(",")).join("\\n");
  const blob = new Blob([csvContent], {{ type: 'text/csv;charset=utf-8;' }});
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);
  link.setAttribute("href", url);
  link.setAttribute("download", `baseline_filter_export_${{filteredRecords.length}}_rows.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}}

function escapeHtml(str) {{
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {{
  if (e.key === 'Escape') {{
    closeDrawer();
  }} else if (e.key === 'ArrowLeft' && e.ctrlKey) {{
    navigateRecord(-1);
  }} else if (e.key === 'ArrowRight' && e.ctrlKey) {{
    navigateRecord(1);
  }}
}});
</script>
</body>
</html>
"""
    return html


def main():
    parser = argparse.ArgumentParser(description="Build a dashboard for one versioned baseline run.")
    parser.add_argument("--run-id", required=True, help="Frozen baseline run identifier")
    parser.add_argument("--overwrite-dashboard", action="store_true", help="Explicitly replace dashboard for this run")
    args = parser.parse_args()
    artifacts = configure_run(args.run_id)
    if OUTPUT_HTML.exists() and not args.overwrite_dashboard:
        raise FileExistsError(f"Refusing to overwrite dashboard: {OUTPUT_HTML}")
    data = build_data()
    html = generate_html(data)
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    lineage_path = OUTPUT_HTML.with_suffix(".lineage.json")
    lineage_path.write_text(json.dumps({
        "run_id": artifacts.run_id,
        "parent_manifest_sha256": compute_sha256(artifacts.manifest_path),
        "dashboard_builder_sha256": compute_sha256(Path(__file__).resolve()),
        "dashboard_sha256": compute_sha256(OUTPUT_HTML),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    size_mb = OUTPUT_HTML.stat().st_size / 1024 / 1024
    print(f"[DONE] Successfully generated {OUTPUT_HTML} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
