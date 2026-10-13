"""Read-only pilot QA and workload estimates; no gold publication or training."""
from collections import Counter
from datetime import datetime
from importlib import import_module
from math import ceil, floor, isfinite
from statistics import mean, median
import csv
import json

from src.data.sprint4_pilot import file_hash, repeat_earliest_at

TIMING_FIELDS = {"sample_id", "source_review_seconds", "annotation_started_at", "annotation_finished_at",
                 "annotation_seconds", "review_seconds", "valid_sample", "difficulty_note"}
REPEAT_FIELDS = ("sample_id", "split", "round1_completed_at", "round2_started_at", "round1_mode", "round2_mode",
                 "predictions_visible", "prior_annotations_visible")


def read_csv(path, required):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not required <= set(reader.fieldnames or ()) or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("CSV_MISSING_OR_DUPLICATE_COLUMNS")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("CSV_ROW_WIDTH_MISMATCH")
    return rows


def timestamp(value):
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("TIMESTAMP_NEEDS_TIMEZONE")
    return parsed


def seconds(value, positive=False):
    result = float(value)
    if not isfinite(result) or result < 0 or (positive and result == 0):
        raise ValueError("INVALID_SECONDS")
    return result


def check_ids(rows, sample_ids):
    seen = set()
    for row in rows:
        sample_id = row.get("sample_id")
        if sample_id not in sample_ids or sample_id in seen:
            raise ValueError("UNKNOWN_OR_DUPLICATE_SAMPLE_ID")
        seen.add(sample_id)
    return seen


def timing_summary(rows, sample_ids):
    seen = check_ids(rows, sample_ids)
    completed, pending, issues = [], sorted(sample_ids - seen), []
    for row in rows:
        sample_id = row["sample_id"]
        if all(not row.get(field, "").strip() for field in TIMING_FIELDS - {"sample_id"}):
            pending.append(sample_id)
            continue
        try:
            start, finish = timestamp(row["annotation_started_at"]), timestamp(row["annotation_finished_at"])
            duration = (finish - start).total_seconds()
            annotation = seconds(row["annotation_seconds"], positive=True)
            if duration <= 0 or annotation > duration + 1:
                raise ValueError("ACTIVE_TIME_EXCEEDS_WALL_TIME_OR_REVERSED_TIMESTAMPS")
            total = annotation + seconds(row["review_seconds"]) + seconds(row["source_review_seconds"])
            valid = row["valid_sample"].strip().lower()
            if valid not in {"true", "false"}:
                raise ValueError("VALID_SAMPLE_MUST_BE_TRUE_OR_FALSE")
            if valid == "false" and not row["difficulty_note"].strip():
                raise ValueError("REJECTED_SAMPLE_NEEDS_REASON")
            completed.append({"sample_id": sample_id, "valid": valid == "true", "total_seconds": total})
        except (ValueError, KeyError, TypeError) as error:
            issues.append({"sample_id": sample_id, "reason": str(error)})
    valid_count = sum(row["valid"] for row in completed)
    durations = [row["total_seconds"] for row in completed]
    complete = len(completed) == len(sample_ids) and bool(sample_ids) and not issues
    return {"status": "COMPLETE" if complete else "PARTIAL" if completed else "INVALID" if issues else "NOT_MEASURED",
            "expected_samples": len(sample_ids), "timed_samples": len(completed), "valid_samples_declared": valid_count,
            "invalid_samples_declared": len(completed) - valid_count, "pending_sample_ids": sorted(pending), "issues": issues,
            "valid_rate_on_timed_samples": valid_count / len(completed) if completed else None,
            "mean_minutes_per_attempt": mean(durations) / 60 if durations else None,
            "median_minutes_per_attempt": median(durations) / 60 if durations else None,
            # Rejected attempts consume the owner's time too.
            "minutes_per_usable_sample_including_reject_cost": sum(durations) / valid_count / 60 if valid_count else None,
            "measurement_basis": "USER_RECORDED_ACTIVE_ANNOTATION_PLUS_SOURCE_REVIEW_PLUS_REVIEW",
            "validity_is_human_declared_not_gold_approval": True,
            "complete_timing_required_for_projection": complete and valid_count > 0}


def repeat_count(sample_count):
    if type(sample_count) is not int or sample_count < 0:
        raise ValueError("INVALID_SAMPLE_COUNT")
    return min(sample_count, 60, max(30, ceil(0.15 * sample_count)))


def workload_projection(minutes_per_sample, daily_minutes, annotation_days, adjudication_minutes=0):
    values = (minutes_per_sample, daily_minutes, annotation_days, adjudication_minutes)
    if (not all(isfinite(value) for value in values) or min(values[:3]) <= 0 or adjudication_minutes < 0
            or type(annotation_days) is not int):
        raise ValueError("INVALID_CAPACITY_INPUT")
    budget = daily_minutes * annotation_days
    lower, upper = 0, floor(budget / (1.2 * minutes_per_sample))
    while lower < upper:
        candidate = (lower + upper + 1) // 2
        needed = 1.2 * ((candidate + repeat_count(candidate)) * minutes_per_sample + adjudication_minutes)
        if needed <= budget:
            lower = candidate
        else:
            upper = candidate - 1
    feasible = 1.2 * adjudication_minutes <= budget
    return {"daily_minutes": daily_minutes, "active_annotation_days_assumed": annotation_days,
            "minutes_per_usable_sample_measured": minutes_per_sample, "train_dev_first_pass_samples_estimated": lower,
            "repeat_samples_estimated": repeat_count(lower), "buffer_percent": 20,
            "adjudication_minutes_assumed": adjudication_minutes, "budget_minutes": budget,
            "estimated_required_minutes": 1.2 * ((lower + repeat_count(lower)) * minutes_per_sample + adjudication_minutes),
            "fixed_cost_budget_feasible": feasible, "calendar_washout_feasibility_verified": False,
            "status": "WORKLOAD_ESTIMATE_NOT_CORPUS_COMMITMENT"}


def repeat_summary(rows, sample_ids):
    seen = check_ids(rows, sample_ids)
    pending, issues, eligible = sorted(sample_ids - seen), [], []
    for row in rows:
        sample_id = row["sample_id"]
        if all(not row.get(field, "").strip() for field in REPEAT_FIELDS[1:]):
            pending.append(sample_id)
            continue
        earliest = None
        try:
            if row["split"] not in {"train", "dev"}:
                raise ValueError("REPEAT_REQUIRES_TRAIN_OR_DEV")
            if row["round1_mode"] != "HUMAN_MANUAL" or row["round2_mode"] != "HUMAN_MANUAL":
                raise ValueError("REPEAT_REQUIRES_MANUAL_BOTH_ROUNDS")
            if row["predictions_visible"].strip().lower() != "false" or row["prior_annotations_visible"].strip().lower() != "false":
                raise ValueError("REPEAT_REQUIRES_DECLARED_BLINDING")
            earliest = repeat_earliest_at(row["round1_completed_at"])
            if timestamp(row["round2_started_at"]) < timestamp(earliest):
                raise ValueError("WASHOUT_LESS_THAN_168_HOURS")
            eligible.append({"sample_id": sample_id, "round2_earliest_at": earliest})
        except (ValueError, KeyError, TypeError) as error:
            issues.append({"sample_id": sample_id, "round2_earliest_at": earliest, "reason": str(error)})
    return {"status": "DECLARED_TIMING_CHECKED" if eligible and not issues and not pending else "PARTIAL" if eligible else "NOT_MEASURED",
            "timing_eligible_samples": len(eligible), "eligible": eligible, "pending_sample_ids": pending, "issues": issues,
            "blinding_basis": "USER_DECLARATION_NOT_INDEPENDENT_OBSERVATION",
            "agreement_metrics": "NOT_MEASURED", "inter_annotator_agreement": "NOT_MEASURED"}


def annotation_summary(tasks, queue):
    if not isinstance(tasks, list):
        raise ValueError("LABEL_STUDIO_EXPORT_MUST_BE_LIST")
    converter = import_module("scripts.17_convert_span_annotation_batch")
    seen, valid, issues = set(), [], []
    label_counts, system_counts = Counter(), Counter()
    for task in tasks:
        if not isinstance(task, dict) or not isinstance(task.get("data"), dict):
            raise ValueError("INVALID_LABEL_STUDIO_TASK")
        sample_id = task["data"].get("sample_id")
        if sample_id not in queue or sample_id in seen:
            raise ValueError("UNKNOWN_OR_DUPLICATE_SAMPLE_ID")
        seen.add(sample_id)
        try:
            if task["data"].get("text") != queue[sample_id]["text"]:
                raise ValueError("EXPORT_TEXT_DIFFERS_FROM_QUEUE")
            annotations = task.get("annotations", [])
            if not isinstance(annotations, list) or any(not isinstance(item, dict) for item in annotations):
                raise ValueError("INVALID_ANNOTATIONS_LIST")
            active = [item for item in annotations if not item.get("was_cancelled")]
            if len(active) != 1:
                raise ValueError("EXACTLY_ONE_COMPLETED_ANNOTATION_REQUIRED")
            selected = active[0]
            if (task.get("predictions") or task.get("total_predictions") or selected.get("prediction")
                    or selected.get("parent_prediction") is not None
                    or any(item.get("origin") == "prediction" for item in selected.get("result", []) if isinstance(item, dict))):
                raise ValueError("MANUAL_PILOT_PREDICTION_PROVENANCE_FOUND")
            if not selected.get("completed_by"):
                raise ValueError("HUMAN_ANNOTATOR_ID_MISSING")
            converted = converter.convert_annotation(selected, queue[sample_id]["text"], sample_id)
            if not converted["spans"] or converted["review_flags"]:
                raise ValueError("EMPTY_SPANS_OR_REVIEW_FLAGS_REQUIRE_ADJUDICATION")
            valid.append(sample_id)
            label_counts.update(span["label"] for span in converted["spans"])
            system_counts.update([converted["address_system"] or "NULL"])
        except (ValueError, KeyError, TypeError) as error:
            issues.append({"sample_id": sample_id, "reason": str(error)})
    return {"status": "STRUCTURAL_QA_COMPLETE" if len(valid) == len(queue) and bool(queue) else "PARTIAL" if valid else "NOT_MEASURED",
            "structurally_valid_annotations": len(valid), "valid_sample_ids": valid,
            "missing_sample_ids": sorted(set(queue) - seen), "issues": issues,
            "span_support_from_structurally_valid_exports": {label: label_counts[label] for label in sorted(converter.LABELS)},
            "t1_declared_counts": dict(system_counts), "counts_are_approved_gold_support": False,
            "semantic_correctness": "HUMAN_REVIEW_REQUIRED", "gold_release": "NOT_APPROVED"}


def read_package(package):
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8-sig"))
    for name, expected in manifest["output_sha256"].items():
        path = (package / name).resolve()
        if not path.is_relative_to(package.resolve()) or not path.is_file() or file_hash(path) != expected:
            raise ValueError("PILOT_PACKAGE_HASH_MISMATCH")
    rows = json.loads((package / "source_review_queue.json").read_text(encoding="utf-8-sig"))
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("INVALID_PILOT_QUEUE")
    queue = {row["sample_id"]: row for row in rows}
    if len(queue) != len(rows) or len(queue) != manifest["candidate_samples"]:
        raise ValueError("PILOT_QUEUE_COUNT_OR_ID_MISMATCH")
    return manifest, queue
