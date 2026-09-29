"""Scorer and metric calculator for baseline evaluations across 6 benchmark datasets."""

from __future__ import annotations

from typing import Any

from src.data.administrative_mapping import clean_value, normalise_text
from src.evaluation.schema import (
    STANDARD_FIELDS,
    StandardPrediction,
    UnifiedEvaluationRecord,
)


def _norm(val: Any) -> str:
    """Normalize Unicode, case and whitespace while retaining accents and unit types."""
    s = clean_value(val)
    if not s:
        return ""
    # Keep unit-type prefixes so different administrative entities cannot
    # become exact matches solely because their names share a suffix.
    return normalise_text(s)


def normalized_edit_similarity(prediction: Any, truth: Any) -> float | None:
    """Return normalized Levenshtein similarity; empty-empty pairs are unscored."""
    pred_value = _norm(prediction)
    truth_value = _norm(truth)
    if not pred_value and not truth_value:
        return None
    if not pred_value or not truth_value:
        return 0.0
    if pred_value == truth_value:
        return 1.0

    # Address fields are short, so the two-row dynamic-programming algorithm
    # keeps this dependency-free and deterministic.
    previous = list(range(len(truth_value) + 1))
    for pred_index, pred_char in enumerate(pred_value, start=1):
        current = [pred_index]
        for truth_index, truth_char in enumerate(truth_value, start=1):
            substitution_cost = 0 if pred_char == truth_char else 1
            current.append(
                min(
                    current[-1] + 1,
                    previous[truth_index] + 1,
                    previous[truth_index - 1] + substitution_cost,
                )
            )
        previous = current
    distance = previous[-1]
    return 1.0 - distance / max(len(pred_value), len(truth_value))


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


def score_prediction_pair(
    prediction: dict[str, str],
    truth: dict[str, str],
    scored_fields: tuple[str, ...] = STANDARD_FIELDS,
) -> dict[str, Any]:
    """Return strict and fuzzy scores for one prediction, comparing like fields."""
    unknown_fields = set(scored_fields) - set(STANDARD_FIELDS)
    if unknown_fields:
        raise ValueError(f"Unknown scored fields: {sorted(unknown_fields)}")

    comparisons = compare_fields(prediction, truth)
    field_metrics: dict[str, dict[str, Any]] = {}
    similarities: list[float] = []
    tp = fp = fn = 0
    for field in scored_fields:
        comparison = comparisons[field]
        pred_value = _norm(prediction.get(field, ""))
        truth_value = _norm(truth.get(field, ""))
        similarity = normalized_edit_similarity(pred_value, truth_value)
        if similarity is not None:
            similarities.append(similarity)

        if comparison == "TP":
            field_tp, field_fp, field_fn = 1, 0, 0
        elif comparison == "TN":
            field_tp, field_fp, field_fn = 0, 0, 0
        elif comparison == "FP":
            field_tp, field_fp, field_fn = 0, 1, 0
        elif comparison == "FN":
            field_tp, field_fp, field_fn = 0, 0, 1
        else:
            field_tp, field_fp, field_fn = 0, 1, 1
        tp += field_tp
        fp += field_fp
        fn += field_fn
        field_metrics[field] = {
            "exact_correct": comparison in {"TP", "TN"},
            "exact_comparison": comparison,
            "fuzzy_similarity": similarity,
            "fuzzy_scored": similarity is not None,
        }

    fuzzy_mean = sum(similarities) / len(similarities) if similarities else None
    exact_match = all(comparisons[field] in {"TP", "TN"} for field in scored_fields)
    return {
        "exact_match": exact_match,
        "micro_mean_fuzzy_similarity": fuzzy_mean,
        "fuzzy_scored_fields": len(similarities),
        "field_metrics": field_metrics,
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


def aggregate_prediction_pairs(
    pairs: list[tuple[dict[str, str], dict[str, str]]],
    scored_fields: tuple[str, ...] = STANDARD_FIELDS,
) -> dict[str, Any]:
    """Aggregate strict, exact field and fuzzy similarity metrics consistently."""
    pair_scores = [
        score_prediction_pair(prediction, truth, scored_fields)
        for prediction, truth in pairs
    ]
    record_count = len(pair_scores)
    field_metrics: dict[str, dict[str, Any]] = {}
    for field in scored_fields:
        scored_pairs = [
            score["field_metrics"][field]
            for score in pair_scores
        ]
        exact_correct = sum(bool(item["exact_correct"]) for item in scored_pairs)
        fuzzy_values = [
            float(item["fuzzy_similarity"])
            for item in scored_pairs
            if item["fuzzy_scored"]
        ]
        field_tp = sum(item["exact_comparison"] == "TP" for item in scored_pairs)
        field_fp = sum(item["exact_comparison"] in {"FP", "MISMATCH"} for item in scored_pairs)
        field_fn = sum(item["exact_comparison"] in {"FN", "MISMATCH"} for item in scored_pairs)
        f1_denominator = 2 * field_tp + field_fp + field_fn
        field_metrics[field] = {
            "exact_correct": exact_correct,
            "exact_n": record_count,
            "exact_match_rate": exact_correct / record_count if record_count else None,
            "fuzzy_similarity_sum": sum(fuzzy_values),
            "fuzzy_similarity_n": len(fuzzy_values),
            "mean_fuzzy_similarity": sum(fuzzy_values) / len(fuzzy_values) if fuzzy_values else None,
            "tp": field_tp,
            "fp": field_fp,
            "fn": field_fn,
            "f1": (2 * field_tp / f1_denominator) if f1_denominator else 0.0,
        }

    fuzzy_values = [
        float(field_score["fuzzy_similarity"])
        for score in pair_scores
        for field_score in score["field_metrics"].values()
        if field_score["fuzzy_scored"]
    ]
    field_means = [
        float(item["mean_fuzzy_similarity"])
        for item in field_metrics.values()
        if item["mean_fuzzy_similarity"] is not None
    ]
    total_tp = sum(score["tp"] for score in pair_scores)
    total_fp = sum(score["fp"] for score in pair_scores)
    total_fn = sum(score["fn"] for score in pair_scores)
    micro_f1_denominator = 2 * total_tp + total_fp + total_fn
    return {
        "record_count": record_count,
        "exact_record_correct": sum(bool(score["exact_match"]) for score in pair_scores),
        "exact_record_match_rate": (
            sum(bool(score["exact_match"]) for score in pair_scores) / record_count
            if record_count else None
        ),
        "micro_mean_fuzzy_similarity": (
            sum(fuzzy_values) / len(fuzzy_values) if fuzzy_values else None
        ),
        "fuzzy_scored_records": sum(
            score["fuzzy_scored_fields"] > 0 for score in pair_scores
        ),
        "fuzzy_scored_field_values": len(fuzzy_values),
        "macro_mean_field_fuzzy_similarity": (
            sum(field_means) / len(field_means) if field_means else None
        ),
        "micro_f1_scored_fields": (
            2 * total_tp / micro_f1_denominator if micro_f1_denominator else 0.0
        ),
        "macro_mean_field_f1": (
            sum(item["f1"] for item in field_metrics.values()) / len(field_metrics)
            if field_metrics else 0.0
        ),
        "field_metrics": field_metrics,
    }


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

    pair_metrics = aggregate_prediction_pairs(
        [
            (
                json.loads(record.truong_du_doan),
                json.loads(record.truong_dung),
            )
            for record in eval_records
        ],
        STANDARD_FIELDS,
    )

    return {
        "total": total,
        "exact_accuracy": correct_cnt / total,
        "partial_rate": partial_cnt / total,
        "error_rate": error_cnt / total,
        "unsupported_rate": unsupported_cnt / total,
        "field_metrics": {
            field: {
                **field_metrics[field],
                "exact_match_rate": pair_metrics["field_metrics"][field]["exact_match_rate"],
                "mean_fuzzy_similarity": pair_metrics["field_metrics"][field]["mean_fuzzy_similarity"],
                "fuzzy_similarity_n": pair_metrics["field_metrics"][field]["fuzzy_similarity_n"],
            }
            for field in STANDARD_FIELDS
        },
        "micro_mean_fuzzy_similarity": pair_metrics["micro_mean_fuzzy_similarity"],
        "macro_mean_field_fuzzy_similarity": pair_metrics["macro_mean_field_fuzzy_similarity"],
        "fuzzy_scored_field_values": pair_metrics["fuzzy_scored_field_values"],
    }
