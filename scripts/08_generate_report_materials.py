"""Generate traceable v4 report materials from a frozen versioned baseline run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Iterable

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evaluation.manifest import compute_sha256
from src.evaluation.materials import parse_prediction_json, select_traceable_cases, validate_case_table
from src.evaluation.protocol import (
    DATASET07_DIRECTION,
    DATASET07_SCORED_FIELDS,
    FUZZY_EMPTY_POLICY,
    FUZZY_NORMALIZATION,
    FUZZY_SIMILARITY_METHOD,
    METRIC_DEFINITIONS,
    SCORING_PROTOCOL_VERSION,
)
from src.evaluation.run_artifacts import RunArtifacts, verify_run_outputs
from src.evaluation.schema import STANDARD_FIELDS, UNIFIED_SCHEMA_COLUMNS
from src.evaluation.scorer import (
    _norm,
    aggregate_prediction_pairs,
    score_prediction_pair,
)


HYBRID_CONTRACT = {
    "C1": {"PhuongXa": "moi", "QuanHuyen": "cu", "TinhThanh": "cu"},
    "C2": {"PhuongXa": "moi", "QuanHuyen": "cu", "TinhThanh": "moi"},
    "C3": {"PhuongXa": "cu", "QuanHuyen": "cu", "TinhThanh": "moi"},
}

REFERENCES = """## Tài liệu tham khảo

1. **[R1]** Quốc hội. *Nghị quyết số 202/2025/QH15 về sắp xếp đơn vị hành chính cấp tỉnh*. [Cổng Thông tin điện tử Chính phủ](https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-quyet-so-202-2025-qh15-ve-sap-xep-don-vi-hanh-chinh-cap-tinh-119250612174148722.htm).
2. **[R2]** Ủy ban Thường vụ Quốc hội. *Nghị quyết số 76/2025/UBTVQH15 về sắp xếp đơn vị hành chính năm 2025*. [Cổng Thông tin điện tử Chính phủ](https://xaydungchinhsach.chinhphu.vn/nghi-quyet-so-76-2025-ubtvqh15-sap-xep-don-vi-hanh-chinh-nam-2025-119250415130519882.htm).
3. **[R3]** Lafferty, J., McCallum, A., & Pereira, F. (2001). *Conditional Random Fields: Probabilistic Models for Segmenting and Labeling Sequence Data*. [PDF](https://www.cs.columbia.edu/~jebara/6772/papers/crf.pdf).
4. **[R4]** Nguyen, D. Q. & Nguyen, A. T. (2020). *PhoBERT: Pre-trained language models for Vietnamese*. Findings of EMNLP. [ACL Anthology](https://aclanthology.org/2020.findings-emnlp.92/).
5. **[R5]** OpenVenues. *libpostal: international street address NLP*. [Repository và tài liệu kỹ thuật](https://github.com/openvenues/libpostal).
6. **[R6]** OpenStreetMap Wiki. *Planet.osm/full and full-history data*. [Documentation](https://wiki.openstreetmap.org/wiki/Planet_History).
7. **[R7]** Dự án DACN. `data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv`, bảng ánh xạ hành chính được version/hash trong manifest của run.
"""


def _dataset_name(record_id: str) -> str:
    return str(record_id).split("_", maxsplit=1)[0]


def _metric_rows(
    predictions: pd.DataFrame,
    data04: pd.DataFrame | None = None,
    data06: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build dataset and per-field metrics through the shared scorer."""
    definitions: list[tuple[str, pd.DataFrame, tuple[str, ...]]] = [
        ("Data 01|all", predictions[predictions["ID"].str.startswith("D01_")], STANDARD_FIELDS),
        ("Data 02|clean", predictions[predictions["ID"].str.startswith("D02_") & predictions["ID"].str.endswith("_clean")], STANDARD_FIELDS),
        ("Data 02|noisy", predictions[predictions["ID"].str.startswith("D02_") & predictions["ID"].str.endswith("_noisy")], STANDARD_FIELDS),
        ("Data 03|all", predictions[predictions["ID"].str.startswith("D03_")], STANDARD_FIELDS),
        ("Data 04|surface_parse", predictions[predictions["ID"].str.startswith("D04_")], STANDARD_FIELDS),
        ("Data 06|libpostal", predictions[predictions["ID"].str.startswith("D06_") & predictions["CongCu"].eq("libpostal")], STANDARD_FIELDS),
        ("Data 06|vn_from_2025", predictions[predictions["ID"].str.startswith("D06_") & predictions["ID"].str.endswith("_m25")], STANDARD_FIELDS),
        ("Data 06|vn_legacy", predictions[predictions["ID"].str.startswith("D06_") & predictions["ID"].str.endswith("_mleg")], STANDARD_FIELDS),
        ("Data 07|old_to_new", predictions[predictions["ID"].str.startswith("D07_")], DATASET07_SCORED_FIELDS),
    ]

    if data04 is not None:
        for kind in sorted(data04["KieuThieu"].unique()):
            source_indices = data04.index[data04["KieuThieu"].eq(kind)]
            record_keys = {f"D04_{index:04d}" for index in source_indices}
            condition = predictions["ID"].str.extract(r"^(D04_\d{4})", expand=False).isin(record_keys)
            definitions.append((f"Data 04|KieuThieu={kind}", predictions[condition], STANDARD_FIELDS))

    if data06 is not None:
        kinds = data06["KieuLai"].str.extract(r"^(C[1-3])", expand=False)
        for kind in ("C1", "C2", "C3"):
            source_indices = data06.index[kinds.eq(kind)]
            record_keys = {f"D06_{index:04d}" for index in source_indices}
            base_mask = predictions["ID"].str.extract(r"^(D06_\d{4})", expand=False).isin(record_keys)
            mode_specs = (
                ("libpostal", "single_parse", predictions["CongCu"].eq("libpostal")),
                ("vietnamadminunits", "FROM_2025", predictions["ID"].str.endswith("_m25")),
                ("vietnamadminunits", "LEGACY", predictions["ID"].str.endswith("_mleg")),
            )
            for tool, mode, mode_mask in mode_specs:
                condition = base_mask & mode_mask & predictions["CongCu"].eq(tool)
                definitions.append((
                    f"Data 06|KieuLai={kind}|mode={mode}",
                    predictions[condition],
                    STANDARD_FIELDS,
                ))

    metric_rows: list[dict[str, object]] = []
    field_rows: list[dict[str, object]] = []
    for label, frame, fields in definitions:
        for tool, sub in frame.groupby("CongCu", sort=True):
            pairs = [
                (
                    parse_prediction_json(row["TruongDuDoan"]),
                    parse_prediction_json(row["TruongDung"]),
                )
                for _, row in sub.iterrows()
            ]
            metrics = aggregate_prediction_pairs(pairs, fields)
            metric_rows.append({
                "dataset_condition": label,
                "tool": tool,
                "scored_fields": ",".join(fields),
                "n": metrics["record_count"],
                "exact_correct": metrics["exact_record_correct"],
                "exact_match_rate": metrics["exact_record_match_rate"],
                "micro_mean_fuzzy_similarity": metrics["micro_mean_fuzzy_similarity"],
                "fuzzy_scored_field_values": metrics["fuzzy_scored_field_values"],
                "macro_mean_field_fuzzy_similarity": metrics["macro_mean_field_fuzzy_similarity"],
                "micro_f1_scored_fields": metrics["micro_f1_scored_fields"],
                "macro_mean_field_f1": metrics["macro_mean_field_f1"],
            })
            for field, field_metric in metrics["field_metrics"].items():
                field_rows.append({
                    "dataset_condition": label,
                    "tool": tool,
                    "field": field,
                    "exact_correct": field_metric["exact_correct"],
                    "exact_n": field_metric["exact_n"],
                    "exact_match_rate": field_metric["exact_match_rate"],
                    "fuzzy_similarity_sum": field_metric["fuzzy_similarity_sum"],
                    "fuzzy_similarity_n": field_metric["fuzzy_similarity_n"],
                    "mean_fuzzy_similarity": field_metric["mean_fuzzy_similarity"],
                })
    return pd.DataFrame(metric_rows), pd.DataFrame(field_rows)


def _validate_data06_contract(data06: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for key, expected in HYBRID_CONTRACT.items():
        part = data06[data06["KieuLai"].str.startswith(f"{key}_")]
        if part.empty:
            raise ValueError(f"Data 06 has no {key} rows")
        spans = part["Span_He_Detail"].map(json.loads)
        if not all(span == expected for span in spans):
            raise ValueError(f"Data 06 span contract mismatch for {key}")
        if part["QuanHuyen"].astype(str).str.strip().eq("").any():
            raise ValueError(f"Data 06 {key} unexpectedly omits QuanHuyen")
        rows.append({
            "KieuLai": key,
            "n": len(part),
            "PhuongXa_he": expected["PhuongXa"],
            "QuanHuyen_he": expected["QuanHuyen"],
            "TinhThanh_he": expected["TinhThanh"],
            "all_surface_district_present": True,
        })
    return pd.DataFrame(rows)


def _data07_scope(data07: pd.DataFrame) -> pd.DataFrame:
    counts = data07.groupby("QuanHe", sort=True).size().rename("n").reset_index()
    counts["direction_evaluated"] = DATASET07_DIRECTION
    counts["scored_fields"] = ",".join(DATASET07_SCORED_FIELDS)
    return counts


def _structure_scenario_rows(metrics: pd.DataFrame) -> pd.DataFrame:
    """Label existing Data 04/06 strata without calling them probabilities."""
    mask = metrics["dataset_condition"].str.startswith(
        ("Data 04|KieuThieu=", "Data 06|KieuLai=")
    )
    result = metrics.loc[mask].copy()
    result.insert(0, "diagnostic_axis", "structural_scenario")
    result["interpretation"] = "Existing benchmark stratum; not a calibrated uncertainty estimate."
    return result.reset_index(drop=True)


def _spatial_trace_rows(
    predictions: pd.DataFrame,
    raw_logs: list[dict[str, object]],
    data07: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Project Data 07 converter traces and summarize observed selection paths."""
    raw_index = {
        (str(item["id"]), str(item["tool"])): item
        for item in raw_logs
    }
    rows: list[dict[str, object]] = []
    data07 = data07.reset_index(drop=True)
    subset = predictions[predictions["ID"].str.startswith("D07_")]
    for _, prediction_row in subset.iterrows():
        record_id = str(prediction_row["ID"])
        try:
            source_index = int(record_id.split("_", maxsplit=2)[1])
        except (IndexError, ValueError) as exc:
            raise ValueError(f"Cannot resolve Data 07 source row for {record_id}") from exc
        if source_index >= len(data07):
            raise ValueError(f"Data 07 source row is out of range for {record_id}")
        source = data07.iloc[source_index]
        key = (record_id, str(prediction_row["CongCu"]))
        raw = raw_index.get(key)
        if raw is None:
            raise ValueError(f"Data 07 prediction has no raw trace: {key}")
        raw_data = raw.get("raw_data", {})
        trace = raw.get("trace", {})
        if not trace and isinstance(raw_data, dict):
            trace = raw_data.get("conversion_trace", {})
        if not isinstance(trace, dict):
            trace = {}
        prediction = parse_prediction_json(prediction_row["TruongDuDoan"])
        truth = parse_prediction_json(prediction_row["TruongDung"])
        pair_score = score_prediction_pair(prediction, truth, DATASET07_SCORED_FIELDS)
        candidate_count = trace.get("candidate_count")
        try:
            candidate_count = int(candidate_count) if candidate_count not in (None, "") else None
        except (TypeError, ValueError):
            candidate_count = None
        rows.append({
            "ID": record_id,
            "CongCu": str(prediction_row["CongCu"]),
            "QuanHe": str(source["QuanHe"]),
            "MaPhuongXaMoi": str(source["MaPhuongXaMoi"]),
            "exact_target_match": pair_score["exact_match"],
            "target_fuzzy_similarity": pair_score["micro_mean_fuzzy_similarity"],
            "candidate_count": candidate_count,
            "multiple_converter_candidates": (
                candidate_count > 1 if candidate_count is not None else None
            ),
            "selection_path": str(trace.get("selection_path", "not_recorded")),
            "geocoder_status": str(trace.get("geocoder_status", "not_recorded")),
            "fallback_used": str(trace.get("fallback_used", "not_recorded")),
            "raw_status": str(raw.get("status", "unknown")),
            "interpretation": (
                "Converter trace diagnostic only; candidate count is not a probability "
                "or boundary-distance estimate."
            ),
        })
    details = pd.DataFrame(rows)
    if details.empty:
        return details, pd.DataFrame(columns=[
            "diagnostic_axis", "CongCu", "QuanHe", "candidate_count",
            "selection_path", "geocoder_status", "fallback_used", "n",
            "exact_target_correct", "exact_target_match_rate", "interpretation",
        ])

    summary_source = details.copy()
    for column in (
        "candidate_count",
        "selection_path",
        "geocoder_status",
        "fallback_used",
    ):
        summary_source[column] = summary_source[column].map(
            lambda value: "not_recorded" if pd.isna(value) else str(value)
        )
    group_columns = [
        "CongCu", "QuanHe", "candidate_count", "selection_path",
        "geocoder_status", "fallback_used",
    ]
    summary = (
        summary_source.groupby(group_columns, dropna=False, sort=True)
        .agg(
            n=("ID", "size"),
            exact_target_correct=("exact_target_match", "sum"),
            exact_target_match_rate=("exact_target_match", "mean"),
        )
        .reset_index()
    )
    summary.insert(0, "diagnostic_axis", "spatial_converter_trace")
    summary["interpretation"] = (
        "Observed converter trace stratum; not calibrated model uncertainty or "
        "geometric boundary ambiguity."
    )
    return details, summary


def _md_table(frame: pd.DataFrame, columns: Iterable[str]) -> str:
    names = list(columns)
    lines = ["| " + " | ".join(names) + " |", "| " + " | ".join("---" for _ in names) + " |"]
    for _, row in frame.iterrows():
        cells = [str(row[name]).replace("|", "\\|").replace("\n", " ") for name in names]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _run_header(run_id: str, manifest: dict, predictions: pd.DataFrame) -> str:
    benchmark_rows = sum(item["row_count"] for item in manifest.get("datasets", {}).values())
    return "\n".join([
        f"- **Phiên bản tài liệu:** v4 fuzzy/uncertainty draft (sinh tự động)",
        f"- **Run nguồn:** `{run_id}`",
        f"- **Manifest SHA-256:** `{compute_sha256(RunArtifacts(ROOT, run_id).manifest_path)}`",
        f"- **Dòng benchmark:** {benchmark_rows}; **lượt dự đoán:** {len(predictions)}.",
        "- **Trạng thái:** draft có truy vết artifact; không thay thế báo cáo baseline v1 frozen.",
    ])


def _write_text_once(path: Path, text: str, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite generated material: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _generate_documents(
    artifacts: RunArtifacts,
    docs_dir: Path,
    tables_dir: Path,
    manifest: dict,
    predictions: pd.DataFrame,
    metrics: pd.DataFrame,
    field_metrics: pd.DataFrame,
    data06_contract: pd.DataFrame,
    data07_scope: pd.DataFrame,
    structural_metrics: pd.DataFrame,
    spatial_summary: pd.DataFrame,
    cases: pd.DataFrame,
    overwrite: bool,
) -> list[Path]:
    header = _run_header(artifacts.run_id, manifest, predictions)
    metric_rounding = {
        "exact_match_rate": 6,
        "micro_mean_fuzzy_similarity": 6,
        "macro_mean_field_fuzzy_similarity": 6,
        "micro_f1_scored_fields": 6,
        "macro_mean_field_f1": 6,
    }
    metrics_table = _md_table(metrics.round(metric_rounding), metrics.columns)
    structural_table = _md_table(
        structural_metrics.round(metric_rounding),
        structural_metrics.columns,
    )
    spatial_table = _md_table(
        spatial_summary.round({"exact_target_match_rate": 6}),
        spatial_summary.columns,
    )
    contract_table = _md_table(data06_contract, data06_contract.columns)
    scope_table = _md_table(data07_scope, data07_scope.columns)
    case_view = cases[["ID", "CongCu", "Dataset", "LoaiLoi", "DungSai", "DiaChiGoc", "TruongDuDoan", "TruongDung", "RawStatus"]]
    cases_table = _md_table(case_view, case_view.columns)

    evidence = f"""# Bằng chứng baseline và chẩn đoán có truy vết (v4)

{header}

## 1. Phương pháp và giới hạn diễn giải

Tài liệu này đọc trực tiếp prediction CSV, raw JSONL và bảng CSV ở `comparative_analysis_tables/` của cùng run. Case study được chọn bằng quy tắc xác định: sắp xếp theo `(dataset, tool, LoaiLoi, ID)`, sau đó lấy một dòng đầu tiên cho mỗi nhóm `(dataset, tool, LoaiLoi)`. Mỗi case được kiểm tra lại với khóa `(ID, CongCu)` ở cả prediction và raw log trước khi xuất.

`exact_match_rate`, `micro_f1_scored_fields` và `macro_mean_field_f1` là ba chỉ số khác nhau. Định nghĩa: {METRIC_DEFINITIONS['exact_match_rate']} {METRIC_DEFINITIONS['micro_f1_scored_fields']} {METRIC_DEFINITIONS['macro_mean_field_f1']}

Metric fuzzy dùng `{FUZZY_SIMILARITY_METHOD}` sau chuẩn hóa theo protocol: {FUZZY_NORMALIZATION} {FUZZY_EMPTY_POLICY} Định nghĩa: {METRIC_DEFINITIONS['micro_mean_fuzzy_similarity']} {METRIC_DEFINITIONS['macro_mean_field_fuzzy_similarity']} Fuzzy similarity đo độ gần chuỗi, không thay thế xác minh đúng thực thể hành chính.

Data 02 là nhiễu tổng hợp có kiểm soát, được hiệu chuẩn từ profile VQA; nó không thay thế đánh giá trên hóa đơn thật. Data 07 chỉ đo `{DATASET07_DIRECTION}` bằng VietnamAdminUnits và chỉ chấm `{', '.join(DATASET07_SCORED_FIELDS)}`; không có phép đo new-to-old hoặc Libpostal conversion.

## 2. Bảng định lượng nguồn

Nguồn: `comparative_analysis_tables/dataset_metrics.csv` của run `{artifacts.run_id}`. Bảng `dataset_field_metrics.csv` có {len(field_metrics)} hàng theo điều kiện/trường, gồm exact numerator/denominator và fuzzy similarity sum/denominator.

{metrics_table}

## 3. Hợp đồng Data 06 và phạm vi Data 07

Nguồn: `comparative_analysis_tables/data06_contract.csv` và `data07_scope.csv`.

### Data 06

{contract_table}

Mọi kiểu Data 06 hiện có đều giữ `QuanHuyen` trên chuỗi bề mặt. C1 là phường/xã mới + quận/huyện cũ + tỉnh/thành cũ; C2 là phường/xã mới + quận/huyện cũ + tỉnh/thành mới; C3 là phường/xã cũ + quận/huyện cũ + tỉnh/thành mới.

### Data 07

{scope_table}

## 4. Chẩn đoán uncertainty theo tình huống cấu trúc và trace chuyển đổi không gian

Data 04 (`KieuThieu`) và Data 06 (`KieuLai`/C1-C3) được dùng làm strata cấu trúc có sẵn. Đây là so sánh theo nhóm benchmark, không phải xác suất bất định đã hiệu chuẩn.

### Cấu trúc

Nguồn: `comparative_analysis_tables/structural_scenarios.csv`.

{structural_table}

### Không gian / trace converter

Nguồn: `comparative_analysis_tables/spatial_trace_summary.csv`; từng dòng có trace nằm trong `spatial_trace_cases.csv`.

{spatial_table}

`candidate_count`, `selection_path`, `geocoder_status` và `fallback_used` là dấu vết converter. Chúng không phải confidence, khoảng cách tới ranh giới hay nhãn nhập nhằng được kiểm chứng thủ công. Adapter không xuất xác suất; run này không báo calibration/ECE.

## 5. Case study được sinh từ output

Nguồn: `comparative_analysis_tables/case_studies.csv`. Các dòng sau là projection của output, không phải ví dụ minh họa viết thủ công.

{cases_table}

## 6. Diễn giải có điều kiện

Các output chỉ chứng minh hành vi quan sát được của adapter và tool ở run này. Khi raw log không có trace nhánh converter, không được kết luận một lỗi cụ thể do fallback/geocoder. Run mới ghi `conversion_trace` để phân biệt ánh xạ từ điển, geocoder và fallback. Bất kỳ kết luận nhân quả nào phải trỏ tới ID cùng trace hoặc được ghi là giả thuyết kỹ thuật.
"""

    prep = f"""# Tóm tắt chuẩn bị dữ liệu và hợp đồng benchmark (v4)

{header}

## 1. Nguồn và snapshot OSM

Pipeline đọc `data/raw/osm/vietnam-internal.osh.pbf` bằng `pyosmium`, tách snapshot bằng mốc thời gian `2025-06-30T23:59:59Z`. Đây là lượt quét full-history trong code, không phải artifact từ lệnh CLI `osmium time-filter`. OSM full-history lưu nhiều revision của cùng đối tượng, phù hợp để kiểm tra thay đổi theo thời điểm [R6]. Snapshot hiện lưu 26.961 đối tượng: 15.749 node và 11.212 way; 6.008/15.749 node có đủ năm trường địa chỉ.

## 2. Mục đích từng tập

| Tập | Số dòng | Vai trò kiểm chứng | Hợp đồng chính |
| --- | ---: | --- | --- |
| Data 01 | 1.000 | Parse địa chỉ mới sạch | Cấu trúc hai cấp, `QuanHuyen` rỗng theo schema. |
| Data 02 | 1.000 | Độ bền trước phép biến đổi tổng hợp | Giữ `ChuoiDiaChiGoc`, `GT_*`, loại/mức nhiễu, seed. |
| Data 03 | 1.500 | Mốc parse hệ cũ sạch | Đủ cả năm trường bề mặt; không có thiếu tự nhiên. |
| Data 04 | 800 | Tách extraction và recovery khi thiếu trường | Sinh từ địa chỉ sạch; chỉ xóa theo `KieuThieu`; giữ `GT_*`. |
| Data 06 | 600 | Xung đột hệ quy chiếu trong cùng chuỗi | Chỉ dùng cạnh có một đích xác minh. |
| Data 07 | 600 | Conversion hành chính cũ → mới | Cặp OSM diff quan sát trực tiếp, chấm phường/xã và tỉnh/thành. |

## 3. Hợp đồng Data 03 và Data 04

Data 03 là mốc sạch đầy đủ trường của hệ cũ. Data 04 bắt đầu từ địa chỉ sạch cùng schema, sau đó xóa đúng trường quy định; `GT_*` giữ đáp án trước xóa. Điểm parse chính dùng trường còn hiện diện trên surface; phân tích recovery phải tách riêng, không dùng `GT_*` để tính extraction score.

## 4. Địa chỉ lai và conversion

{contract_table}

{scope_table}

Các cạnh 1-N và M-N không được dựng từ snapshot khi thiếu bằng chứng hình học/toạ độ. Data 07 là quan sát trực tiếp nên có thể chứa M-N; phạm vi hiện tại không đại diện cho mọi vùng hoặc quan hệ hành chính.

{REFERENCES}
"""

    chapter1 = f"""# Chương 1. Động lực nghiên cứu và phát biểu bài toán (v4)

{header}

## 1.1. Bối cảnh

Việc sắp xếp đơn vị hành chính năm 2025 tạo ra hai hệ tham chiếu cho cùng một địa chỉ: hệ cũ có tỉnh/thành, quận/huyện, phường/xã; hệ mới trong benchmark dùng tỉnh/thành và phường/xã. Nghị quyết về sắp xếp cấp tỉnh năm 2025 được công bố theo Nghị quyết 202/2025/QH15 [R1]; khung sắp xếp đơn vị hành chính năm 2025 được nêu trong Nghị quyết 76/2025/UBTVQH15 [R2]. Bài toán kỹ thuật là bảo toàn nghĩa địa chỉ khi chuỗi có thể dùng hệ cũ, hệ mới hoặc trộn cả hai.

## 1.2. Vấn đề nghiên cứu

Đề tài tách bốn nhóm nhiệm vụ: T0 tách span theo schema 11 nhãn; T1 nhận diện hệ quy chiếu `cu/moi/Lai`; T2 ánh xạ đơn vị hành chính theo thời điểm; T3 đối sánh hai địa chỉ theo thời gian. Baseline hiện mới chấm năm trường chuẩn hóa và conversion old-to-new trên Data 07. Vì vậy, số baseline không được trình bày như kết quả hoàn tất T0, T1 hoặc T3.

## 1.3. Bằng chứng thực nghiệm hiện có

Run `{artifacts.run_id}` gồm {len(predictions)} lượt dự đoán từ {sum(item['row_count'] for item in manifest.get('datasets', {}).values())} dòng benchmark. Bảng sau chỉ ra các điều kiện đã thực thi; tên metric và mẫu số được giữ nguyên để tránh so sánh sai.

{metrics_table}

Data 02 cho phép so sánh cùng ground truth giữa chuỗi sạch và chuỗi nhiễu tổng hợp. Data 06 mô hình hóa địa chỉ lai theo ba hợp đồng dưới đây, thay vì giả định thiếu quận/huyện:

{contract_table}

Data 07 chỉ có quan hệ N-1/M-N trong sample hiện tại:

{scope_table}

## 1.4. Câu hỏi nghiên cứu

1. Một mô hình trích xuất theo ngữ cảnh có cải thiện span địa chỉ tiếng Việt trước nhiễu và viết tắt không?
2. Có thể phân loại hệ quy chiếu trước khi parsing để tránh ép địa chỉ lai vào một mode cố định không?
3. Khi ánh xạ có nhiều đích, cơ chế nào nên trả kết quả, yêu cầu thêm bằng chứng hoặc từ chối dự đoán?
4. Độ phủ theo quan hệ, vùng và nguồn có làm thay đổi cách diễn giải kết quả không?

## 1.5. Phạm vi và tiêu chí không suy rộng

Chưa có Data 05 dựa trên mốc, nhãn T0 đủ 11 span, T1 tự động, task B/new-to-old hoặc T3. Độ phủ Data 07 tập trung N-1/M-N và có thiên lệch vùng, nên không suy rộng sang 1-1/1-N hoặc toàn quốc. Các case thực nghiệm nằm trong `baseline_diagnostics_v4.md` cùng run và được truy vết bằng ID/raw log.

{REFERENCES}
"""

    chapter2 = rf"""# Chương 2. Cơ sở lý thuyết và phương pháp đánh giá (v4)

{header}

## 2.1. Trích xuất cấu trúc địa chỉ

T0 được phát biểu như gán nhãn chuỗi với 11 nhãn span: `SoNha`, `TenDuong`, `Ngo/Hem`, `ToaNha/CanHo`, `PhuongXa`, `QuanHuyen`, `TinhThanh`, `MocDinhVi`, `HuongDi`, `GhiChu`, `Khac`. Conditional Random Fields là khung phân biệt cho phân đoạn và gán nhãn chuỗi [R3]. Với tiếng Việt, PhoBERT là encoder đơn ngữ đã được đánh giá trên các tác vụ như POS, parsing và NER [R4]; đây là cơ sở để thử nghiệm encoder ngữ cảnh kết hợp đầu ra span, không phải bằng chứng rằng mô hình đã được huấn luyện trong repository này.

## 2.2. Đồ thị hành chính đa thời điểm

Biểu diễn mỗi đơn vị theo khóa `(tỉnh, quận/huyện, phường/xã, thời điểm)` và mỗi chuyển đổi là một cạnh đến đơn vị mới. Bậc vào/ra tạo các quan hệ 1-1, 1-N, N-1 và M-N. N-1 có một đích khi đi cũ → mới; 1-N và M-N cần bằng chứng không gian hoặc cơ chế abstention nếu địa chỉ không đủ định vị. Bảng nguồn [R7] là căn cứ duy nhất để tạo cạnh; tên đơn lẻ không đủ làm khóa ánh xạ.

## 2.3. Hai baseline trong phạm vi nghiên cứu

Libpostal là thư viện C dùng statistical NLP và dữ liệu địa lý mở để parse/normalize địa chỉ [R5]. VietnamAdminUnits là package được kiểm thử ở version đã ghi trong manifest. Phép so sánh trong repository là so sánh **adapter + phiên bản tool + protocol**, không suy rộng thành xếp hạng tuyệt đối của hai hệ thống ngoài điều kiện run.

## 2.4. Giao thức chấm điểm

Với mỗi trường được chấm, so sánh strict sau chuẩn hóa tạo TP, TN, FP, FN hoặc MISMATCH; MISMATCH đóng góp một FP và một FN. Exact match yêu cầu toàn bộ trường được chấm khớp. Báo cáo fuzzy dùng normalized Levenshtein similarity, bằng 1 trừ khoảng cách Levenshtein chia cho độ dài lớn hơn của hai chuỗi chuẩn hóa. Chuẩn hóa dùng NFC, casefold và gộp khoảng trắng; giữ dấu tiếng Việt và tiền tố loại đơn vị hành chính. So sánh chỉ trong cùng trường. Cặp rỗng-rỗng bị loại khỏi fuzzy denominator; một vế rỗng có điểm 0. Mọi bảng trường ghi numerator và denominator.

Điểm fuzzy là mức gần bề mặt chuỗi. Với đích hành chính, một tên gần giống không được tính là đúng đơn vị; exact target match vẫn là tiêu chí nhận diện thực thể.

$$F1_{{micro}} = \frac{{2TP}}{{2TP + FP + FN}}$$

$$F1_{{macro}} = \frac{{1}}{{|F|}} \sum_{{f \in F}} F1_f$$

Data 07 chỉ có `PhuongXa`, `TinhThanh` trong tập trường chấm và direction `{DATASET07_DIRECTION}`. Truth phường/xã và tỉnh/thành được tra từ `MaPhuongXaMoi` qua bảng mapping. Tỷ lệ exact, fuzzy và F1 của từng điều kiện được ghi riêng:

{metrics_table}

## 2.5. Thiết kế đề xuất

Giai đoạn 1 nhận chuỗi thô, chuẩn hóa có dấu vết và dự đoán span cùng hệ quy chiếu. Giai đoạn 2 tra đồ thị hành chính theo thời điểm. Nếu cạnh có một đích đã xác minh thì trả kết quả; nếu nhiều đích thì dùng toạ độ/bằng chứng biên giới hoặc trả trạng thái bất định. Cơ chế abstention giảm rủi ro gán một đích không có căn cứ, nhưng cần được đánh giá thực nghiệm bằng task riêng.

Phân tích hiện tại tách tình huống cấu trúc (nhóm `KieuThieu`, `KieuLai`) khỏi trace converter phục vụ lựa chọn đích. Đây là strata/chỉ báo chẩn đoán, không phải xác suất uncertainty. Chưa có nhãn bất định thủ công, xác suất dự đoán hoặc hình học biên giới đủ để tính calibration hay độ gần ranh giới.

## 2.6. Tái lập và giới hạn

OSM full-history giữ nhiều revision của đối tượng [R6], nhưng tag OSM là nhãn cộng đồng. Data 02 là tổng hợp; Data 03/04 có hợp đồng rõ; Data 06/07 không bao phủ toàn bộ quan hệ. Run mới ghi trace converter để phân biệt fallback/geocoder từ quan sát trực tiếp. Các giới hạn này là một phần của phương pháp, không được che bằng điểm aggregate.

{REFERENCES}
"""

    index = f"""# Chỉ mục artifact báo cáo và trạng thái kiểm toán (v4)

{header}

## Artifact nguồn

| Thành phần | Đường dẫn | Vai trò |
| --- | --- | --- |
| Manifest | `{artifacts.manifest_path.relative_to(ROOT)}` | Hash benchmark, mapping, package và code của run. |
| Prediction | `{artifacts.predictions_path.relative_to(ROOT)}` | Output 9 cột đã chấm. |
| Raw log | `{artifacts.raw_log_path.relative_to(ROOT)}` | Response/trace theo `(ID, tool)`. |
| Bảng định lượng | `{tables_dir.relative_to(ROOT)}` | Metric, scope, contract và case CSV. |

## Tài liệu sinh tự động

| Tệp | Nguồn máy đọc được | Trạng thái |
| --- | --- | --- |
| `baseline_diagnostics_v4.md` | prediction + raw + bảng exact/fuzzy/diagnostic | Draft có truy vết |
| `data_preparation_summary_v4.md` | benchmark + OSM snapshot + manifest | Draft có truy vết |
| `chapter_01_research_motivation_v4.md` | bảng metric + nguồn [R1], [R2] | Draft có truy vết |
| `chapter_02_theoretical_foundation_v4.md` | protocol + nguồn [R3]–[R7] | Draft có truy vết |

Không tài liệu nào trong nhóm này thay thế baseline v1 frozen. Mọi thay đổi protocol, adapter, benchmark hoặc mapping phải tạo run ID mới và sinh lại toàn bộ bảng/tài liệu từ run đó.

{REFERENCES}
"""

    targets = {
        "baseline_diagnostics_v4.md": evidence,
        "data_preparation_summary_v4.md": prep,
        "chapter_01_research_motivation_v4.md": chapter1,
        "chapter_02_theoretical_foundation_v4.md": chapter2,
        "report_materials_index_v4.md": index,
    }
    paths = []
    for name, content in targets.items():
        path = docs_dir / name
        _write_text_once(path, content, overwrite)
        paths.append(path)
    return paths


def generate_materials(run_id: str, materials_id: str = "v4_fuzzy", overwrite: bool = False) -> dict[str, Path]:
    """Create tables and v4 documents after verifying a frozen baseline run."""
    artifacts = RunArtifacts(ROOT, run_id)
    manifest = verify_run_outputs(artifacts)
    if manifest.get("run_id") not in (None, run_id):
        raise ValueError(f"Manifest run ID mismatch: {manifest.get('run_id')}")
    scoring_version = manifest.get("scoring", {}).get("protocol_version")
    if scoring_version != SCORING_PROTOCOL_VERSION:
        raise ValueError(
            f"Run {run_id} uses scoring protocol {scoring_version!r}; "
            f"report-material generation requires {SCORING_PROTOCOL_VERSION!r}. "
            "Create a new baseline run instead of reinterpreting existing outputs."
        )

    predictions = pd.read_csv(artifacts.predictions_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    raw_logs = [json.loads(line) for line in artifacts.raw_log_path.read_text(encoding="utf-8").splitlines()]
    if tuple(predictions.columns) != UNIFIED_SCHEMA_COLUMNS:
        raise ValueError(
            "Prediction CSV does not match the required 9-column contract: "
            f"{list(predictions.columns)}"
        )
    if len(predictions) != len(raw_logs):
        raise ValueError("Prediction/raw-log count mismatch")
    output_row_counts = manifest.get("output_row_counts", {})
    if len(predictions) != int(output_row_counts.get(artifacts.predictions_path.name, -1)):
        raise ValueError("Prediction row count does not match the frozen manifest")
    if len(raw_logs) != int(output_row_counts.get(artifacts.raw_log_path.name, -1)):
        raise ValueError("Raw-log row count does not match the frozen manifest")

    prediction_keys = set(zip(predictions["ID"], predictions["CongCu"]))
    raw_keys = {(str(item.get("id", "")), str(item.get("tool", ""))) for item in raw_logs}
    if len(prediction_keys) != len(predictions) or len(raw_keys) != len(raw_logs):
        raise ValueError("Duplicate (ID, CongCu) key in prediction or raw-log artifacts")
    if prediction_keys != raw_keys:
        raise ValueError("Prediction/raw-log (ID, CongCu) keys do not match")

    benchmark_dir = ROOT / "data" / "processed" / "benchmark"
    for name, frozen in manifest.get("datasets", {}).items():
        input_path = benchmark_dir / name
        if not input_path.exists() or compute_sha256(input_path) != frozen.get("sha256"):
            raise ValueError(f"Benchmark input differs from frozen run manifest: {input_path}")
    mapping_path = ROOT / "data" / "reference" / "administrative_units" / "vietnam-sap-nhap-phuong-xa.csv"
    frozen_mapping = manifest.get("mapping_source", {})
    if (
        not mapping_path.exists()
        or compute_sha256(mapping_path) != frozen_mapping.get("sha256")
    ):
        raise ValueError(f"Administrative mapping differs from frozen run manifest: {mapping_path}")
    data04 = pd.read_csv(benchmark_dir / "04_missing_fields_800.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    data06 = pd.read_csv(benchmark_dir / "06_hybrid_addresses_600.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    data07 = pd.read_csv(benchmark_dir / "07_bidirectional_pairs_verified.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    metrics, field_metrics = _metric_rows(predictions, data04=data04, data06=data06)
    structural_metrics = _structure_scenario_rows(metrics)
    spatial_cases, spatial_summary = _spatial_trace_rows(predictions, raw_logs, data07)
    data06_contract = _validate_data06_contract(data06)
    data07_scope = _data07_scope(data07)
    cases = select_traceable_cases(predictions, raw_logs)
    validate_case_table(cases, predictions, raw_logs)

    safe_materials_id = "".join(ch for ch in materials_id if ch.islower() or ch.isdigit() or ch == "_")
    if safe_materials_id != materials_id or not materials_id:
        raise ValueError("materials_id must contain only lowercase letters, digits, and underscores")
    derived_root = ROOT / "data" / "processed" / "evaluation" / "derived" / run_id / materials_id
    tables_dir = derived_root / "comparative_analysis_tables"
    docs_dir = ROOT / "docs" / "runs" / run_id / materials_id
    if derived_root.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite derived material set: {derived_root}")
    tables_dir.mkdir(parents=True, exist_ok=True)
    table_paths = {
        "dataset_metrics.csv": metrics,
        "dataset_field_metrics.csv": field_metrics,
        "structural_scenarios.csv": structural_metrics,
        "spatial_trace_cases.csv": spatial_cases,
        "spatial_trace_summary.csv": spatial_summary,
        "data06_contract.csv": data06_contract,
        "data07_scope.csv": data07_scope,
        "case_studies.csv": cases,
    }
    results: dict[str, Path] = {}
    for name, frame in table_paths.items():
        path = tables_dir / name
        if path.exists() and not overwrite:
            raise FileExistsError(f"Refusing to overwrite table: {path}")
        frame.to_csv(path, index=False, encoding="utf-8-sig")
        results[name] = path

    docs = _generate_documents(
        artifacts,
        docs_dir,
        tables_dir,
        manifest,
        predictions,
        metrics,
        field_metrics,
        data06_contract,
        data07_scope,
        structural_metrics,
        spatial_summary,
        cases,
        overwrite,
    )
    results.update({path.name: path for path in docs})
    lineage = {
        "run_id": run_id,
        "parent_manifest_sha256": compute_sha256(artifacts.manifest_path),
        "selection_rule": "first error after sort(dataset, tool, LoaiLoi, ID), one record per group",
        "output_hashes": {name: compute_sha256(path) for name, path in results.items()},
    }
    lineage["derived_root"] = str(derived_root.relative_to(ROOT))
    lineage_path = tables_dir / "report_materials_lineage.json"
    lineage_path.write_text(json.dumps(lineage, ensure_ascii=False, indent=2), encoding="utf-8")
    results[lineage_path.name] = lineage_path
    print(f"[DONE] Generated {len(results)} traceable report artifacts for run {run_id}")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate traceable v4 report materials from one baseline run.")
    parser.add_argument("--run-id", required=True, help="Frozen baseline run identifier")
    parser.add_argument("--materials-id", default="v4_fuzzy", help="Versioned derived-material identifier, default: v4_fuzzy")
    parser.add_argument("--overwrite-materials", action="store_true", help="Explicitly replace generated materials for this run")
    args = parser.parse_args()
    generate_materials(args.run_id, materials_id=args.materials_id, overwrite=args.overwrite_materials)


if __name__ == "__main__":
    main()
