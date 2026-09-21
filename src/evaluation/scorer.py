"""Scorer and metric calculator for baseline evaluations across 6 benchmark datasets."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from src.data.administrative_mapping import clean_value, normalise_text
from src.evaluation.schema import (
    STANDARD_FIELDS,
    StandardPrediction,
    UnifiedEvaluationRecord,
)


def _norm(val: Any) -> str:
    """Normalize text for semantic field comparison (NFC, lowercase, collapse spaces)."""
    s = clean_value(val)
    if not s:
        return ""
    # Strip common administrative level prefixes for semantic matching
    s = re.sub(
        r"^(?:thành phố|tỉnh|quận|huyện|thị xã|phường|xã|thị trấn|tp\.?|q\.?|h\.?|tx\.?|p\.?|x\.?|tt\.?)\s+",
        "",
        normalise_text(s),
    )
    return s.strip()


def compare_fields(pred: dict[str, str], truth: dict[str, str]) -> dict[str, str]:
    """Compare predicted 5 fields with ground truth 5 fields.
    
    Returns TP/TN/FP/FN/MISMATCH. A mismatch contributes both FP and FN to F1.
    """
    result = {}
    for f in STANDARD_FIELDS:
        p_val = _norm(pred.get(f, ""))
        t_val = _norm(truth.get(f, ""))

        if not t_val and not p_val:
            result[f] = "TN"
        elif t_val and p_val == t_val:
            result[f] = "TP"
        elif not t_val and p_val:
            result[f] = "FP"  # Hallucinated or over-imputed
        elif t_val and not p_val:
            result[f] = "FN"  # Omitted
        else:
            result[f] = "MISMATCH"  # Wrong entity: one false positive and one false negative.
    return result


def evaluate_record(
    record_id: str,
    raw_address: str,
    tool_name: str,
    prediction: StandardPrediction,
    ground_truth: dict[str, str],
    scenario: str = "NONE",
    extra_notes: str = "",
    scored_fields: tuple[str, ...] = STANDARD_FIELDS,
) -> UnifiedEvaluationRecord:
    """Evaluate a single baseline prediction against ground truth and produce UnifiedEvaluationRecord."""
    pred_dict = prediction.to_dict()
    comp = compare_fields(pred_dict, ground_truth)

    comp = {field: comp[field] for field in scored_fields}
    num_tp = sum(1 for v in comp.values() if v == "TP")
    num_fp = sum(1 for v in comp.values() if v in {"FP", "MISMATCH"})
    num_fn = sum(1 for v in comp.values() if v in {"FN", "MISMATCH"})
    num_truth_fields = sum(1 for f in scored_fields if clean_value(ground_truth.get(f, "")))

    # Determine overall DungSai status
    if num_truth_fields == 0:
        dung_sai = "CORRECT" if num_fp == 0 else "ERROR"
    elif num_tp == num_truth_fields and num_fp == 0:
        dung_sai = "CORRECT"
    elif num_tp >= 2:
        dung_sai = "PARTIAL"
    else:
        dung_sai = "ERROR"

    # Determine LoaiLoi
    loai_loi = "none"
    ghi_chu = extra_notes

    if dung_sai != "CORRECT":
        # Check hallucination on dropped/empty fields
        hallucinated_fields = [f for f, v in comp.items() if v == "FP" and not clean_value(ground_truth.get(f, ""))]
        if hallucinated_fields:
            loai_loi = "hallucination_over_imputation"
            ghi_chu = f"{extra_notes}|Tự điền trường không có trong nguồn: {', '.join(hallucinated_fields)}"
        elif scenario in ("A", "D") and comp.get("PhuongXa") == "MISMATCH":
            loai_loi = "wrong_target"
            ghi_chu = f"{extra_notes}|Sai đích phường/xã"
        elif num_fn > 0 and num_tp > 0:
            loai_loi = "missing_field"
            ghi_chu = f"{extra_notes}|Bỏ sót thành phần địa chỉ có trong chuỗi"
        elif "P." in raw_address or "Q." in raw_address or "TP." in raw_address:
            loai_loi = "abbreviation_misunderstood"
            ghi_chu = f"{extra_notes}|Không nhận diện được từ viết tắt tiếng Việt"
        else:
            loai_loi = "parse_boundary_error"
            ghi_chu = f"{extra_notes}|Cắt sai biên hoặc gán sai vai trò thực thể"

    std_truth = StandardPrediction(
        so_nha=ground_truth.get("SoNha", ""),
        ten_duong=ground_truth.get("TenDuong", ""),
        phuong_xa=ground_truth.get("PhuongXa", ""),
        quan_huyen=ground_truth.get("QuanHuyen", ""),
        tinh_thanh=ground_truth.get("TinhThanh", ""),
    )

    return UnifiedEvaluationRecord(
        record_id=str(record_id),
        dia_chi_goc=str(raw_address),
        cong_cu=str(tool_name),
        truong_du_doan=prediction.to_json(),
        truong_dung=std_truth.to_json(),
        dung_sai=dung_sai,
        loai_loi=loai_loi,
        tinh_huong_mo_ho=scenario,
        ghi_chu=ghi_chu,
    )


def compute_aggregate_metrics(eval_records: list[UnifiedEvaluationRecord]) -> dict[str, Any]:
    """Calculate overall accuracy, precision, recall, and F1 by field and overall."""
    total = len(eval_records)
    if total == 0:
        return {"total": 0}

    correct_cnt = sum(1 for r in eval_records if r.dung_sai == "CORRECT")
    partial_cnt = sum(1 for r in eval_records if r.dung_sai == "PARTIAL")
    error_cnt = sum(1 for r in eval_records if r.dung_sai == "ERROR")
    unsupported_cnt = sum(1 for r in eval_records if r.dung_sai == "UNSUPPORTED")

    field_stats = {f: {"TP": 0, "FP": 0, "FN": 0, "TN": 0} for f in STANDARD_FIELDS}

    for r in eval_records:
        import json
        p_dict = json.loads(r.truong_du_doan)
        t_dict = json.loads(r.truong_dung)
        c = compare_fields(p_dict, t_dict)
        for f, res in c.items():
            if res == "MISMATCH":
                field_stats[f]["FP"] += 1
                field_stats[f]["FN"] += 1
            else:
                field_stats[f][res] += 1

    field_metrics = {}
    for f, counts in field_stats.items():
        tp = counts["TP"]
        fp = counts["FP"]
        fn = counts["FN"]
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        field_metrics[f] = {
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "accuracy": (tp + counts["TN"]) / total,
        }

    return {
        "total": total,
        "exact_accuracy": correct_cnt / total,
        "partial_rate": partial_cnt / total,
        "error_rate": error_cnt / total,
        "unsupported_rate": unsupported_cnt / total,
        "field_metrics": field_metrics,
    }
