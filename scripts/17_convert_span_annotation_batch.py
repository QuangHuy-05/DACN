"""Generalized Label Studio export converter and QA validator for T0/T1 annotation batches.

Works across pilot, batch 02 train/dev, and 100 test benchmark hold.
Validates:
1. sample_id and text exact identity with queue.
2. Character offset half-open intervals [start, end) and slice integrity.
3. Zero overlap between spans.
4. Schema conformity (11 labels).
5. Address system validity per span and per record.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
LABEL_CONFIG = ROOT / "configs/label_studio_span11.xml"
GUIDELINE = ROOT / "docs/sprints/sprint_03/span_11_annotation_guideline.md"

LABELS = frozenset({
    "SoNha", "TenDuong", "Ngo/Hem", "ToaNha/CanHo", "PhuongXa",
    "QuanHuyen", "TinhThanh", "MocDinhVi", "HuongDi", "GhiChu", "Khac",
})
SPAN_SYSTEMS = frozenset({"cu", "moi", "khong_xac_dinh"})
ADDRESS_SYSTEMS = frozenset({"cu", "moi", "Lai"})
REVIEW_FLAGS = frozenset({
    "unreadable_ocr", "ambiguous_label", "temporal_ambiguity", "privacy_review"
})
TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_queue(path: Path, role: str | None = None) -> dict[str, dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"sample_id", "text", "group_id"}
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"Queue missing columns: {sorted(missing)}")
        rows = [
            row for row in reader
            if role is None or row.get("planned_role") == role
        ]
    result = {}
    for row in rows:
        sample_id = row["sample_id"]
        if sample_id in result:
            raise ValueError(f"Duplicate sample_id in queue: {sample_id}")
        result[sample_id] = row
    return result


def single_choice(value: object, key: str, allowed: frozenset[str], context: str) -> str:
    choices = value.get(key) if isinstance(value, dict) else None
    if not isinstance(choices, list) or len(choices) != 1 or choices[0] not in allowed:
        raise ValueError(f"{context}: expected exactly one valid {key}")
    return choices[0]


def convert_annotation(annotation: dict, text: str, sample_id: str) -> dict:
    results = annotation.get("result")
    if not isinstance(results, list):
        raise ValueError("annotation.result is not a list")
    regions = {}
    systems = {}
    whole_system = None
    review_flags = []
    review_note = ""
    for result in results:
        if not isinstance(result, dict):
            raise ValueError("result item is not an object")
        name = result.get("from_name")
        value = result.get("value")
        if name == "span_label":
            region_id = result.get("id")
            if not isinstance(region_id, str) or not region_id or region_id in regions:
                raise ValueError(f"{sample_id}: missing or duplicate span region ID")
            if not isinstance(value, dict):
                raise ValueError(f"{sample_id}/{region_id}: missing span value")
            start, end = value.get("start"), value.get("end")
            if type(start) is not int or type(end) is not int or not (0 <= start < end <= len(text)):
                raise ValueError(f"{sample_id}/{region_id}: invalid offset [{start},{end})")
            if value.get("text") != text[start:end]:
                raise ValueError(f"{sample_id}/{region_id}: exported span text differs from text[start:end]")
            labels = value.get("labels")
            if not isinstance(labels, list) or len(labels) != 1 or labels[0] not in LABELS:
                raise ValueError(f"{sample_id}/{region_id}: expected one valid span label")
            regions[region_id] = {
                "start": start,
                "end": end,
                "label": labels[0],
                "text": text[start:end],
            }
        elif name == "span_system":
            region_id = result.get("id")
            if not isinstance(region_id, str) or not region_id or region_id in systems:
                raise ValueError(f"{sample_id}: missing or duplicate span_system region ID")
            if (not isinstance(value, dict) or type(value.get("start")) is not int or
                    type(value.get("end")) is not int or
                    value.get("text") != text[value["start"]:value["end"]]):
                raise ValueError(f"{sample_id}/{region_id}: invalid span_system text/offset")
            systems[region_id] = (
                single_choice(value, "choices", SPAN_SYSTEMS, f"{sample_id}/{region_id}"),
                value["start"], value["end"], value["text"],
            )
        elif name == "address_system":
            if whole_system is not None:
                raise ValueError(f"{sample_id}: duplicate address_system")
            whole_system = single_choice(
                value, "choices", ADDRESS_SYSTEMS, f"{sample_id}/address_system"
            )
        elif name == "review_flag":
            flags = value.get("choices") if isinstance(value, dict) else None
            if not isinstance(flags, list) or any(f not in REVIEW_FLAGS for f in flags):
                raise ValueError(f"{sample_id}: invalid review_flag choices")
            review_flags.extend(flags)
        elif name == "review_note":
            text_lines = value.get("text") if isinstance(value, dict) else None
            if text_lines is not None and not isinstance(text_lines, list):
                raise ValueError(f"{sample_id}: invalid review_note")
            review_note = " ".join(text_lines).strip() if text_lines else ""
        else:
            raise ValueError(f"{sample_id}: unknown annotation control {name!r}")

    missing_systems = set(regions) - set(systems)
    if missing_systems:
        raise ValueError(f"{sample_id}: spans missing system: {sorted(missing_systems)}")
    orphaned_systems = set(systems) - set(regions)
    if orphaned_systems:
        raise ValueError(f"{sample_id}: span systems without spans: {sorted(orphaned_systems)}")

    spans = []
    for region_id, span in regions.items():
        system, system_start, system_end, system_text = systems[region_id]
        if (system_start, system_end, system_text) != (span["start"], span["end"], span["text"]):
            raise ValueError(f"{sample_id}/{region_id}: span_system region differs from span_label")
        if span["label"] == "QuanHuyen" and system != "cu":
            raise ValueError(f"{sample_id}/{region_id}: QuanHuyen must have system 'cu'")
        spans.append({
            "region_id": region_id,
            "start": span["start"],
            "end": span["end"],
            "label": span["label"],
            "text": span["text"],
            "system": system,
        })
    spans.sort(key=lambda s: (s["start"], s["end"]))
    for previous, current in zip(spans, spans[1:]):
        if previous["end"] > current["start"]:
            raise ValueError(
                f"{sample_id}: overlapping spans [{previous['start']},{previous['end']}) "
                f"and [{current['start']},{current['end']})"
            )
    return {
        "spans": spans,
        "address_system": whole_system,
        "review_flags": sorted(set(review_flags)),
        "review_note": review_note,
        "lead_time": annotation.get("lead_time"),
    }


def convert_export(
    export_path: Path,
    queue_path: Path,
    output_dir: Path,
    role: str | None = None,
    adjudication_map_path: Path | None = None,
) -> dict:
    queue = read_queue(queue_path, role=role)
    if not export_path.is_file():
        raise FileNotFoundError(export_path)
    pilot_manifest = json.loads((ROOT / "data/processed/annotation/sprint03/pilot_gold_v1_manifest.json").read_text(encoding="utf-8"))
    if file_hash(LABEL_CONFIG) != pilot_manifest["sha256"]["label_config"] or file_hash(GUIDELINE) != pilot_manifest["sha256"]["guideline"]:
        raise ValueError("Locked Label Studio config or span guideline has changed")

    adjudication_map = {}
    if adjudication_map_path:
        with adjudication_map_path.open("r", encoding="utf-8") as stream:
            adjudication_map = json.load(stream)

    raw_text = export_path.read_text(encoding="utf-8")
    tasks = json.loads(raw_text)
    if not isinstance(tasks, list):
        raise ValueError("Export top level must be a list of tasks")

    output_dir.mkdir(parents=True, exist_ok=True)
    canonical_path = output_dir / "canonical_candidate.jsonl"
    report_path = output_dir / "qa_report.json"
    review_path = output_dir / "review_items.json"

    task_by_id = {}
    issues = []
    for task in tasks:
        data = task.get("data") if isinstance(task, dict) else None
        sample_id = data.get("sample_id") if isinstance(data, dict) else None
        if not sample_id:
            task_id = task.get("id") if isinstance(task, dict) else "non-object"
            issues.append(f"Task {task_id}: missing data.sample_id")
            continue
        if sample_id in task_by_id:
            issues.append(f"Duplicate task for sample_id: {sample_id}")
            continue
        if set(data) != {"sample_id", "text"}:
            issues.append(f"{sample_id}: task.data contains unexpected fields")
        task_by_id[sample_id] = task

    unknown_ids = sorted(set(task_by_id) - set(queue))
    if unknown_ids:
        issues.append(f"Export contains unknown sample IDs: {unknown_ids}")

    task_statuses = {}
    converted_records = []
    review_items = []
    label_counts = Counter()
    span_system_counts = Counter()
    address_system_counts = Counter()
    lead_times = []

    for sample_id, expected in queue.items():
        task = task_by_id.get(sample_id)
        if not task:
            task_statuses[sample_id] = "missing_from_export"
            continue
        actual_text = (task.get("data") or {}).get("text")
        if actual_text != expected["text"]:
            issues.append(f"{sample_id}: text differs between queue and export")
            task_statuses[sample_id] = "text_mismatch"
            continue
        if role == "frozen_benchmark_test_hold" and (task.get("predictions") or task.get("total_predictions")):
            issues.append(f"{sample_id}: test task contains predictions")
            task_statuses[sample_id] = "test_prediction_leakage"
            continue
        raw_annotations = task.get("annotations", [])
        if not isinstance(raw_annotations, list) or any(not isinstance(ann, dict) for ann in raw_annotations):
            issues.append(f"{sample_id}: invalid annotations list")
            task_statuses[sample_id] = "invalid_annotations"
            continue
        annotations = [ann for ann in raw_annotations if not ann.get("was_cancelled")]
        if not annotations:
            task_statuses[sample_id] = "unannotated"
            continue
        if len(annotations) > 1 and sample_id not in adjudication_map:
            task_statuses[sample_id] = "multiple_annotations_pending_adjudication"
            continue

        selected_ann = annotations[0]
        if sample_id in adjudication_map:
            ann_id = adjudication_map[sample_id]
            matched = [ann for ann in annotations if ann.get("id") == ann_id]
            if not matched:
                issues.append(f"{sample_id}: adjudication annotation ID {ann_id} not found")
                task_statuses[sample_id] = "adjudication_id_not_found"
                continue
            selected_ann = matched[0]
        if role == "frozen_benchmark_test_hold" and selected_ann.get("parent_prediction") is not None:
            issues.append(f"{sample_id}: test annotation derived from a prediction")
            task_statuses[sample_id] = "test_prediction_leakage"
            continue

        try:
            converted = convert_annotation(selected_ann, expected["text"], sample_id)
        except Exception as exc:
            issues.append(f"{sample_id}: conversion error: {exc}")
            task_statuses[sample_id] = "conversion_error"
            continue

        task_statuses[sample_id] = "converted"
        if converted["lead_time"] is not None:
            lead_times.append(converted["lead_time"])
        for span in converted["spans"]:
            label_counts[span["label"]] += 1
            span_system_counts[span["system"]] += 1
        if converted["address_system"]:
            address_system_counts[converted["address_system"]] += 1

        record = {
            "sample_id": sample_id,
            "text": expected["text"],
            "spans": [
                {
                    "start": s["start"],
                    "end": s["end"],
                    "label": s["label"],
                    "system": s["system"],
                }
                for s in converted["spans"]
            ],
            "address_system": converted["address_system"],
            "source_group": expected["group_id"],
        }
        converted_records.append(record)

        if converted["review_flags"] or converted["review_note"]:
            review_items.append({
                "sample_id": sample_id,
                "text": expected["text"],
                "review_flags": converted["review_flags"],
                "review_note": converted["review_note"],
                "spans": record["spans"],
                "address_system": record["address_system"],
            })

    with canonical_path.open("w", encoding="utf-8") as stream:
        for rec in converted_records:
            stream.write(json.dumps(rec, ensure_ascii=False) + "\n")

    with review_path.open("w", encoding="utf-8") as stream:
        json.dump(review_items, stream, ensure_ascii=False, indent=2)

    status_counts = Counter(task_statuses.values())
    overall_status = "READY_FOR_HUMAN_REVIEW" if (
        not issues and status_counts.get("converted") == len(queue)
    ) else "FAILED_QA"

    report = {
        "status": overall_status,
        "export_sha256": file_hash(export_path),
        "queue_sha256": file_hash(queue_path),
        "label_config_sha256": file_hash(LABEL_CONFIG),
        "guideline_sha256": file_hash(GUIDELINE),
        "expected_tasks": len(queue),
        "task_statuses": task_statuses,
        "status_counts": dict(status_counts),
        "issues": issues,
        "converted_tasks": len(converted_records),
        "flagged_tasks": len(review_items),
        "label_distribution": dict(label_counts),
        "span_system_distribution": dict(span_system_counts),
        "address_system_distribution": dict(address_system_counts),
        "lead_time_seconds": {
            "median": round(median(lead_times), 2) if lead_times else None,
            "min": round(min(lead_times), 2) if lead_times else None,
            "max": round(max(lead_times), 2) if lead_times else None,
        },
    }

    with report_path.open("w", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", type=Path, required=True, help="Raw JSON export from Label Studio")
    parser.add_argument("--queue", type=Path, required=True, help="Queue CSV file")
    parser.add_argument("--role", type=str, default=None, help="Planned role filter (optional)")
    parser.add_argument("--output-dir", type=Path, required=True, help="Output directory for QA and canonical candidate")
    parser.add_argument("--adjudication-map", type=Path, default=None, help="Optional adjudication map JSON")
    args = parser.parse_args()

    report = convert_export(
        args.export,
        args.queue,
        args.output_dir,
        role=args.role,
        adjudication_map_path=args.adjudication_map,
    )
    print(json.dumps({
        "status": report["status"],
        "converted": report["converted_tasks"],
        "expected": report["expected_tasks"],
        "issues_count": len(report["issues"]),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
