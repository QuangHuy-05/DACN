"""Explicit task protocol labels shared by runner, reports, and tests."""

from __future__ import annotations


DATASET07_DIRECTION = "old_to_new"
DATASET07_SCORED_FIELDS = ("PhuongXa", "TinhThanh")
SCORING_PROTOCOL_VERSION = "2.0"
FUZZY_SIMILARITY_METHOD = "normalized_levenshtein"
FUZZY_NORMALIZATION = (
    "NFC Unicode, casefold, collapse whitespace, strip surrounding whitespace and "
    "trailing comma separators, "
    "retain Vietnamese diacritics and administrative unit-type prefixes, and "
    "compare only corresponding fields."
)
FUZZY_EMPTY_POLICY = (
    "Ignore pairs where both values are empty; score a one-sided empty pair as 0. "
    "Report the number of non-empty field pairs used as the denominator."
)


def scenario_for_dataset07(relation: str) -> str:
    """Data 07 always evaluates old-to-new conversion; relation is separate metadata."""
    del relation
    return "A"


METRIC_DEFINITIONS = {
    "exact_match_rate": "Tỷ lệ bản ghi có mọi trường được chấm đều khớp sau chuẩn hóa.",
    "micro_f1_scored_fields": "F1 gộp mọi quyết định trên các trường được chấm; mismatch tính một FP và một FN.",
    "macro_mean_field_f1": "Trung bình không trọng số của F1 từng trường được chấm.",
    "micro_mean_fuzzy_similarity": (
        "Trung bình normalized Levenshtein similarity trên các cặp giá trị trường "
        "có ít nhất một vế không rỗng; rỗng-rỗng bị loại khỏi mẫu số."
    ),
    "macro_mean_field_fuzzy_similarity": (
        "Trung bình không trọng số của micro_mean_fuzzy_similarity theo từng trường "
        "có ít nhất một cặp giá trị không rỗng."
    ),
    "field_fuzzy_similarity": (
        "1 - Levenshtein_distance / max(length(pred), length(truth)); cặp có một vế "
        "rỗng nhận 0, cặp rỗng-rỗng không được chấm. Đây là độ gần chuỗi, không "
        "xác nhận hai đơn vị hành chính là cùng một thực thể."
    ),
}
