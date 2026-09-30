"""Create conservative text-only span suggestions for the 232 train/dev tasks.

Reads the Label Studio import only. It never reads benchmark GT, source columns,
planned splits, or the 100 held-out test tasks. All output remains candidate data
until the annotator corrects every task and approves the export.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANNOTATION_DIR = ROOT / "data/interim/annotation/sprint03"
IMPORT_PATH = ANNOTATION_DIR / "label_studio_batch02_import.json"
OUTPUT_PATH = ANNOTATION_DIR / "batch02_span11_candidate_predictions.json"
REPORT_PATH = ANNOTATION_DIR / "batch02_prediction_generation_report.json"

WARD_PREFIX = re.compile(r"^(?:(?:phường|xã|thị trấn|đặc khu)\b|(?:p|x)\.(?:\s|$))", re.IGNORECASE)
DISTRICT_PREFIX = re.compile(r"^(?:(?:quận|huyện|thị xã)\b|(?:q|h)\.(?:\s|$))", re.IGNORECASE)
PROVINCE_PREFIX = re.compile(r"^(?:(?:tỉnh|thành phố)\b|tp\.(?:\s|$))", re.IGNORECASE)
HOUSE_PATTERN = re.compile(r"^(?:số\s+)?(?:[A-Z]{0,3})?\d[\w/.-]*$", re.IGNORECASE)
ROAD_PREFIX = re.compile(r"^(?:(?:đường|phố|đại lộ|quốc lộ|tỉnh lộ|hương lộ)\b|đ\.(?:\s|$))", re.IGNORECASE)
ALLEY_PREFIX = re.compile(r"^(?:ngõ|ngách|hẻm)\b", re.IGNORECASE)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def components(text: str) -> list[tuple[int, int, str]]:
    parts = []
    for match in re.finditer(r"[^,]+", text):
        surface = match.group()
        trimmed = surface.strip()
        if trimmed:
            start = match.start() + len(surface) - len(surface.lstrip())
            parts.append((start, start + len(trimmed), trimmed))
    return parts


def suggest(text: str) -> tuple[list[dict], list[str]]:
    parts = components(text)
    warnings = []
    labels: dict[int, str] = {}
    n = len(parts)
    if n not in {4, 5}:
        warnings.append(f"{n} thành phần phân cách dấu phẩy; cần kiểm tra cấu trúc thủ công")
    else:
        first_is_house = bool(HOUSE_PATTERN.fullmatch(parts[0][2]))
        labels[0] = "SoNha" if first_is_house else "TenDuong"
        if first_is_house:
            labels[1] = "TenDuong"
        if n == 5 and first_is_house:
            labels[2], labels[3] = "PhuongXa", "QuanHuyen"
        elif n == 4 and not first_is_house:
            labels[1], labels[2] = "PhuongXa", "QuanHuyen"
        elif n == 4:
            third = parts[2][2]
            if WARD_PREFIX.match(third):
                labels[2] = "PhuongXa"
            elif DISTRICT_PREFIX.match(third):
                labels[2] = "QuanHuyen"
            else:
                warnings.append("Thành phần thứ ba không đủ bằng chứng phân biệt phường/xã với quận/huyện")
        labels[n - 1] = "TinhThanh"

    # Explicit unit words override positional guesses, including malformed OSM
    # hierarchies. Ambiguous pieces are left blank for the human annotator.
    for index, (_, _, part) in enumerate(parts):
        if WARD_PREFIX.match(part):
            if labels.get(index) not in {None, "PhuongXa"}:
                warnings.append(f"Thành phần {index + 1} trái cấu trúc dự kiến: {part}")
            labels[index] = "PhuongXa"
        elif DISTRICT_PREFIX.match(part):
            if labels.get(index) not in {None, "QuanHuyen"}:
                warnings.append(f"Thành phần {index + 1} trái cấu trúc dự kiến: {part}")
            labels[index] = "QuanHuyen"
        elif PROVINCE_PREFIX.match(part) and index == n - 1:
            labels[index] = "TinhThanh"
        elif ALLEY_PREFIX.match(part) and labels.get(index) == "TenDuong":
            labels.pop(index)
            warnings.append(f"Thành phần {index + 1} chứa ngõ/hẻm; tách Ngo/Hem và TenDuong thủ công")
        elif ROAD_PREFIX.match(part) and labels.get(index) in {"PhuongXa", "QuanHuyen"}:
            labels.pop(index)
            warnings.append(f"Thành phần {index + 1} có dạng tên đường trong vị trí hành chính")

    spans = []
    for index, (start, end, part) in enumerate(parts):
        label = labels.get(index)
        if not label:
            continue
        if text[start:end] != part:
            raise ValueError("Offset calculation failed")
        spans.append({
            "start": start, "end": end, "text": part, "label": label,
            "system": "cu" if label == "QuanHuyen" else "khong_xac_dinh",
        })
    return spans, warnings


def main() -> None:
    tasks = json.loads(IMPORT_PATH.read_text(encoding="utf-8"))
    if not isinstance(tasks, list) or len(tasks) != 232:
        raise ValueError("Batch 02 import must contain exactly 232 tasks")
    records = []
    seen = set()
    warnings_by_id = {}
    label_counts = Counter()
    for number, task in enumerate(tasks, start=1):
        data = task.get("data") if isinstance(task, dict) else None
        if not isinstance(data, dict) or set(data) != {"sample_id", "text"}:
            raise ValueError(f"Task {number} exposes unexpected data")
        sample_id, text = data["sample_id"], data["text"]
        if not isinstance(sample_id, str) or not isinstance(text, str) or sample_id in seen:
            raise ValueError(f"Invalid or duplicate sample ID at task {number}")
        seen.add(sample_id)
        spans, warnings = suggest(text)
        label_counts.update(span["label"] for span in spans)
        if warnings:
            warnings_by_id[sample_id] = warnings
        records.append({
            "number": number, "sample_id": sample_id, "text": text,
            "spans": spans, "address_system": None,
            "review_flags": ["ambiguous_label"] if warnings else [],
            "review_note": "; ".join(warnings),
            "status": "candidate_not_gold",
        })
    OUTPUT_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "status": "CANDIDATE_NOT_GOLD",
        "method": "surface_text_only_v1",
        "task_count": len(records),
        "tasks_with_warnings": len(warnings_by_id),
        "predicted_span_counts": dict(label_counts),
        "tasks_requiring_manual_structure_review": warnings_by_id,
        "input_sha256": file_hash(IMPORT_PATH),
        "candidate_sha256": file_hash(OUTPUT_PATH),
        "test_predictions_created": 0,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "tasks": len(records),
                      "warnings": len(warnings_by_id), "spans": sum(label_counts.values())}))


if __name__ == "__main__":
    main()
