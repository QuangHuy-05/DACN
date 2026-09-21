"""Explicit task protocol labels shared by runner, reports, and tests."""

from __future__ import annotations


DATASET07_DIRECTION = "old_to_new"
DATASET07_SCORED_FIELDS = ("PhuongXa", "TinhThanh")


def scenario_for_dataset07(relation: str) -> str:
    """Data 07 always evaluates old-to-new conversion; relation is separate metadata."""
    del relation
    return "A"


METRIC_DEFINITIONS = {
    "exact_match_rate": "Tỷ lệ bản ghi có mọi trường được chấm đều khớp sau chuẩn hóa.",
    "micro_f1_scored_fields": "F1 gộp mọi quyết định trên các trường được chấm; mismatch tính một FP và một FN.",
    "macro_mean_field_f1": "Trung bình không trọng số của F1 từng trường được chấm.",
}
