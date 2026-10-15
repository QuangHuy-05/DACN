"""Read-only test annotation QA, separate from model inference and scoring."""

from collections import Counter
import csv
import importlib
import json
from pathlib import Path

from src.data.annotation_release import TEMPORAL_CUE, content_findings, file_hash, write_json


def t1_review_findings(record):
    """Request evidence, without deriving whole-address gold from span systems."""
    system = record.get("address_system")
    if not system or TEMPORAL_CUE.search(record["text"]):
        return []
    known = {span.get("system") for span in record.get("spans", [])
             if span.get("label") in {"PhuongXa", "QuanHuyen", "TinhThanh"}
             and span.get("system") in {"cu", "moi"}}
    if not known or (system == "Lai" and known != {"cu", "moi"}):
        return [{"code": "t1_evidence_needs_review",
                 "reason": "Whole-address system needs a recorded temporal basis; unknown span systems do not establish it.",
                 "address_system": system, "known_administrative_span_systems": sorted(known)}]
    return []


def review_test_export(export_path, queue_path, output_dir, assisted_manifest=None,
                       adjudication_map=None):
    export_path, queue_path, output_dir = map(Path, (export_path, queue_path, output_dir))
    if output_dir.exists():
        raise FileExistsError("Use a new test QA directory; previous evidence stays immutable")
    original_export_path = export_path
    raw_bytes = original_export_path.read_bytes()
    snapshot = output_dir / "inputs" / "label_studio_export.json"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_bytes(raw_bytes)
    export_path = snapshot
    converter = importlib.import_module("scripts.17_convert_span_annotation_batch")
    mode = "ai_assisted_human_review" if assisted_manifest is not None else "blind"
    report = converter.convert_export(export_path, queue_path, output_dir / "structure",
        role=converter.TEST_ROLE, adjudication_map_path=adjudication_map,
        test_annotation_mode=mode, assisted_manifest_path=assisted_manifest)
    queue = converter.read_queue(queue_path, converter.TEST_ROLE)
    tasks = json.loads(export_path.read_text(encoding="utf-8"))
    by_id = {task["data"]["sample_id"]: task for task in tasks
             if isinstance(task, dict) and isinstance(task.get("data"), dict)
             and task["data"].get("sample_id") in queue}
    items = []
    finding_counts = Counter()
    notes_pending = 0
    unchanged = 0
    reviewer_ids = set()
    for sid, expected in queue.items():
        task = by_id.get(sid, {})
        item = {"sample_id": sid, "task_id": task.get("id"),
                "project_id": task.get("project"), "text": expected["text"],
                "source_group": expected["group_id"],
                "structural_status": report["task_statuses"][sid], "annotations": []}
        for annotation in task.get("annotations", []):
            if annotation.get("was_cancelled"):
                continue
            entry = {"annotation_id": annotation.get("id"),
                     "completed_by": annotation.get("completed_by"),
                     "created_at": annotation.get("created_at"),
                     "updated_at": annotation.get("updated_at"),
                     "findings": []}
            try:
                converted = converter.convert_annotation(annotation, expected["text"], sid)
                entry.update(converted)
                record = {"sample_id": sid, "text": expected["text"],
                          "spans": converted["spans"], "address_system": converted["address_system"]}
                entry["findings"] = content_findings(record) + t1_review_findings(record)
                finding_counts.update(finding["code"] for finding in entry["findings"])
                pending = "GỢI Ý AI CHƯA DUYỆT" in converted["review_note"]
                entry["retained_candidate_note"] = pending
                notes_pending += int(pending)
                prediction = annotation.get("prediction")
                entry["unchanged_span_and_t1_suggestion"] = None
                if isinstance(prediction, dict):
                    proposed = converter.convert_annotation(prediction, expected["text"], sid)
                    same = (converted["spans"] == proposed["spans"] and
                            converted["address_system"] == proposed["address_system"])
                    entry["unchanged_span_and_t1_suggestion"] = same
                    unchanged += int(same)
                reviewer = annotation.get("completed_by")
                if isinstance(reviewer, (int, str)):
                    reviewer_ids.add(str(reviewer))
            except (ValueError, KeyError, TypeError) as exc:
                entry["conversion_error"] = str(exc)
            item["annotations"].append(entry)
        items.append(item)
    write_json(output_dir / "annotation_review.json", items)
    with (output_dir / "all_tasks_review.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        fields = ("sample_id", "task_id", "project_id", "structural_status", "text", "annotation_ids",
                  "finding_codes", "decision", "reason", "reviewer")
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for item in items:
            writer.writerow({key: item[key] for key in fields[:5]} | {
                "annotation_ids": "|".join(str(ann["annotation_id"]) for ann in item["annotations"]),
                "finding_codes": "|".join(sorted({finding["code"] for ann in item["annotations"]
                                                 for finding in ann["findings"]})),
                "decision": "", "reason": "", "reviewer": ""})
    summary = {
        "status": "STRUCTURE_FAILED" if report["status"] != "READY_FOR_HUMAN_REVIEW" else "CONTENT_REVIEW_PENDING",
        "annotation_protocol": report["annotation_protocol"],
        "export_sha256": file_hash(export_path),
        "export_snapshot": "inputs/label_studio_export.json",
        "source_export_unchanged": file_hash(original_export_path) == file_hash(export_path),
        "expected_tasks": len(queue), "exported_tasks": len(tasks),
        "status_counts": report["status_counts"], "structure_issues": report["issues"],
        "missing_sample_ids": [sid for sid, status in report["task_statuses"].items() if status == "missing_from_export"],
        "multiple_annotation_task_ids": [item["task_id"] for item in items
            if item["structural_status"] == "multiple_annotations_pending_adjudication"],
        "content_finding_counts": dict(finding_counts),
        "converted_label_distribution": report["label_distribution"],
        "reviewer_ids": sorted(reviewer_ids),
        "retained_candidate_note_annotation_count": notes_pending,
        "unchanged_span_and_t1_suggestion_annotation_count": unchanged,
        "human_review": "Owner reports labeling complete; final all-100 attestation/adjudication pending",
        "agreement": "NOT_MEASURED", "gold_status": "NOT_RELEASED",
        "model_training_tuning_scoring": "NOT_EXECUTED",
        "note": "Content findings and unchanged suggestions are review signals, not proof of labeling errors or lack of human review.",
    }
    if not summary["source_export_unchanged"]:
        summary["status"] = "SOURCE_EXPORT_CHANGED_DURING_QA"
    write_json(output_dir / "review_summary.json", summary)
    return summary
