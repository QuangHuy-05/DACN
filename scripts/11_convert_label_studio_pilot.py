"""Convert a Label Studio pilot export to validated canonical span candidates.

No model or benchmark metadata is read from the annotator UI. The queue is
used only after export to recover source groups and check text identity.
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
DEFAULT_QUEUE = ROOT / "data/interim/annotation/sprint03/annotation_queue_batch01.csv"
DEFAULT_OUTPUT = ROOT / "data/interim/annotation/sprint03/pilot_conversion"
LABEL_CONFIG = ROOT / "configs/label_studio_span11.xml"
GUIDELINE = ROOT / "docs/sprints/sprint_03/span_11_annotation_guideline.md"
LABELS = frozenset({
    "SoNha", "TenDuong", "Ngo/Hem", "ToaNha/CanHo", "PhuongXa",
    "QuanHuyen", "TinhThanh", "MocDinhVi", "HuongDi", "GhiChu", "Khac",
})
SPAN_SYSTEMS = frozenset({"cu", "moi", "khong_xac_dinh"})
ADDRESS_SYSTEMS = frozenset({"cu", "moi", "Lai"})
REVIEW_FLAGS = frozenset({"unreadable_ocr", "ambiguous_label", "temporal_ambiguity", "privacy_review"})
TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_queue(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"sample_id", "text", "group_id", "planned_role"}
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"Queue missing columns: {sorted(missing)}")
        rows = [row for row in reader if row["planned_role"] == "pilot_train_pool"]
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
            if text[start:end] != value.get("text"):
                raise ValueError(f"{sample_id}/{region_id}: text[start:end] does not match export")
            fragment = text[start:end]
            if fragment[0].isspace() or fragment[-1].isspace() or fragment[0] in ",;()" or fragment[-1] in ",;()":
                raise ValueError(f"{sample_id}/{region_id}: span includes outside whitespace or separator")
            label = single_choice(value, "labels", LABELS, f"{sample_id}/{region_id}")
            regions[region_id] = {"start": start, "end": end, "text": text[start:end], "label": label}
        elif name == "span_system":
            region_id = result.get("id")
            if not isinstance(region_id, str) or not region_id or region_id in systems:
                raise ValueError(f"{sample_id}: missing or duplicate span-system region ID")
            systems[region_id] = single_choice(value, "choices", SPAN_SYSTEMS, f"{sample_id}/{region_id}")
        elif name == "address_system":
            if whole_system is not None:
                raise ValueError(f"{sample_id}: duplicate whole-address system")
            whole_system = single_choice(value, "choices", ADDRESS_SYSTEMS, sample_id)
        elif name == "review_flag":
            choices = value.get("choices") if isinstance(value, dict) else None
            if not isinstance(choices, list) or any(choice not in REVIEW_FLAGS for choice in choices):
                raise ValueError(f"{sample_id}: invalid review flags")
            review_flags = sorted(set(review_flags) | set(choices))
        elif name == "review_note":
            notes = value.get("text") if isinstance(value, dict) else None
            if not isinstance(notes, list) or any(not isinstance(note, str) for note in notes):
                raise ValueError(f"{sample_id}: invalid review note")
            review_note = "\n".join(note.strip() for note in notes if note.strip())
        else:
            raise ValueError(f"{sample_id}: unknown result from_name={name!r}")
    if set(regions) != set(systems):
        missing = sorted(set(regions) - set(systems))
        orphan = sorted(set(systems) - set(regions))
        raise ValueError(f"{sample_id}: missing span systems={missing}; orphan systems={orphan}")
    spans = []
    for region_id, region in regions.items():
        system = systems[region_id]
        if region["label"] == "QuanHuyen" and system != "cu":
            raise ValueError(f"{sample_id}/{region_id}: QuanHuyen must have system=cu")
        spans.append({**region, "system": system})
    spans.sort(key=lambda item: (item["start"], item["end"]))
    for left, right in zip(spans, spans[1:]):
        if left["end"] > right["start"]:
            raise ValueError(f"{sample_id}: overlapping spans at {left['start']} and {right['start']}")
    lead_time = annotation.get("lead_time")
    return {
        "sample_id": sample_id,
        "text": text,
        "spans": spans,
        "address_system": whole_system,
        "review_flags": review_flags,
        "review_note": review_note,
        "annotation_id": annotation.get("id"),
        "annotator_id": str(annotation.get("completed_by", "")),
        "lead_time_seconds": lead_time if isinstance(lead_time, (int, float)) and lead_time >= 0 else None,
    }


def token_labels(record: dict) -> list[str]:
    tokens = list(TOKEN_PATTERN.finditer(record["text"]))
    result = []
    for token in tokens:
        matching = [span for span in record["spans"]
                    if span["start"] <= token.start() and token.end() <= span["end"]]
        crossed = [span for span in record["spans"]
                   if token.start() < span["end"] and span["start"] < token.end() and span not in matching]
        if crossed:
            raise ValueError(f"{record['sample_id']}: token crosses span boundary at {token.start()}")
        result.append(matching[0]["label"] if matching else "O")
    return result


def agreement(pairs: list[tuple[dict, dict]]) -> dict:
    if not pairs:
        return {"status": "NOT_MEASURED", "reason": "No two independent valid annotations on the same task"}
    joint = Counter()
    first = Counter()
    second = Counter()
    exact_common = exact_first = exact_second = 0
    tasks = []
    for a, b in pairs:
        a_tokens, b_tokens = token_labels(a), token_labels(b)
        if len(a_tokens) != len(b_tokens):
            raise ValueError(f"{a['sample_id']}: token count differs")
        for x, y in zip(a_tokens, b_tokens):
            joint[(x, y)] += 1
            first[x] += 1
            second[y] += 1
        a_spans = {(s["start"], s["end"], s["label"]) for s in a["spans"]}
        b_spans = {(s["start"], s["end"], s["label"]) for s in b["spans"]}
        exact_common += len(a_spans & b_spans)
        exact_first += len(a_spans)
        exact_second += len(b_spans)
        tasks.append(a["sample_id"])
    count = sum(joint.values())
    observed = sum(value for (a, b), value in joint.items() if a == b) / count if count else None
    expected = sum(first[label] * second[label] for label in first | second) / (count * count) if count else None
    kappa = (observed - expected) / (1 - expected) if observed is not None and expected is not None and expected < 1 else None
    precision = exact_common / exact_first if exact_first else None
    recall = exact_common / exact_second if exact_second else None
    f1 = (2 * exact_common / (exact_first + exact_second)) if exact_first + exact_second else None
    return {
        "status": "MEASURED", "double_annotated_tasks": len(tasks), "sample_ids": tasks,
        "token_count": count, "tokenizer": r"\w+|[^\w\s]",
        "cohens_kappa_token": kappa, "observed_agreement": observed,
        "expected_agreement": expected, "exact_span_precision": precision,
        "exact_span_recall": recall, "exact_span_f1": f1,
        "exact_span_common": exact_common, "exact_span_annotator_a": exact_first,
        "exact_span_annotator_b": exact_second,
        "note": "Pairing is by task; two different completed_by IDs are required. No adjudicated gold is inferred.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", type=Path, required=True, help="Raw Label Studio JSON export")
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--adjudication-map", type=Path,
                        help="Optional JSON object sample_id -> approved annotation ID")
    args = parser.parse_args()
    if not args.export.is_file():
        raise FileNotFoundError(args.export)
    queue = read_queue(args.queue)
    selection = {}
    if args.adjudication_map:
        selection = json.loads(args.adjudication_map.read_text(encoding="utf-8"))
        if not isinstance(selection, dict):
            raise ValueError("Adjudication map must be a JSON object")
    tasks = json.loads(args.export.read_text(encoding="utf-8-sig"))
    if not isinstance(tasks, list):
        raise ValueError("Label Studio export must be a JSON task array")
    issues = []
    seen = set()
    canonical = []
    pairs = []
    status = Counter()
    times = []
    flagged = 0
    task_statuses = {}
    review_items = []
    for task in tasks:
        data = task.get("data") if isinstance(task, dict) else None
        sample_id = data.get("sample_id") if isinstance(data, dict) else None
        if sample_id not in queue:
            issues.append({"sample_id": sample_id, "issue": "not_in_pilot_queue"})
            continue
        if sample_id in seen:
            issues.append({"sample_id": sample_id, "issue": "duplicate_export_task"})
            task_statuses[sample_id] = "duplicate_export_task"
            continue
        seen.add(sample_id)
        text = data.get("text")
        if text != queue[sample_id]["text"]:
            issues.append({"sample_id": sample_id, "issue": "task_text_differs_from_queue"})
            status["invalid"] += 1
            task_statuses[sample_id] = "invalid_text"
            continue
        annotations = [a for a in task.get("annotations", [])
                       if isinstance(a, dict) and not a.get("was_cancelled") and not a.get("skipped")]
        if not annotations:
            status["unannotated"] += 1
            task_statuses[sample_id] = "unannotated"
            continue
        converted = []
        for annotation in annotations:
            try:
                converted.append(convert_annotation(annotation, text, sample_id))
            except ValueError as error:
                issues.append({"sample_id": sample_id, "annotation_id": annotation.get("id"), "issue": str(error)})
        if len(converted) != len(annotations):
            status["invalid"] += 1
            task_statuses[sample_id] = "invalid_annotation"
            continue
        annotators = {record["annotator_id"] for record in converted}
        if len(converted) == 2 and len(annotators) == 2 and "" not in annotators:
            pairs.append((converted[0], converted[1]))
        if len(converted) > 1:
            selected_id = str(selection.get(sample_id, ""))
            matches = [record for record in converted if str(record["annotation_id"]) == selected_id]
            if not selected_id or len(matches) != 1:
                status["needs_adjudication"] += 1
                task_statuses[sample_id] = "needs_adjudication"
                continue
            record = matches[0]
            status["adjudicated"] += 1
        else:
            record = converted[0]
        if record["review_flags"] or record["review_note"]:
            flagged += 1
            review_items.append({
                "sample_id": sample_id, "annotation_id": record["annotation_id"],
                "review_flags": record["review_flags"], "review_note": record["review_note"],
                "status": "NEEDS_HUMAN_DECISION",
            })
        if record["lead_time_seconds"] is not None:
            times.append(record["lead_time_seconds"])
        canonical.append({
            "sample_id": sample_id, "text": text,
            "spans": [{key: span[key] for key in ("start", "end", "label", "system")}
                      for span in record["spans"]],
            "address_system": record["address_system"],
            "source_group": queue[sample_id]["group_id"],
        })
        status["valid_selected_annotation"] += 1
        task_statuses[sample_id] = "valid_pending_human_review"
    missing = sorted(set(queue) - seen)
    status["missing_from_export"] = len(missing)
    for sample_id in missing:
        issues.append({"sample_id": sample_id, "issue": "missing_from_export"})
        task_statuses[sample_id] = "missing_from_export"
    try:
        agreement_report = agreement(pairs)
    except ValueError as error:
        agreement_report = {"status": "INVALID", "reason": str(error)}
        issues.append({"sample_id": None, "issue": str(error)})
    complete = (not issues and len(canonical) == len(queue) and not status["needs_adjudication"]
                and not status["unannotated"])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "READY_FOR_HUMAN_REVIEW" if complete else "INCOMPLETE_OR_INVALID",
        "expected_pilot_tasks": len(queue), "exported_tasks": len(tasks),
        "counts": dict(status), "task_statuses": dict(sorted(task_statuses.items())),
        "review_flagged_tasks": flagged, "issues": issues,
        "agreement": agreement_report,
        "median_lead_time_seconds": median(times) if times else None,
        "export_sha256": file_hash(args.export), "queue_sha256": file_hash(args.queue),
        "label_config_sha256": file_hash(LABEL_CONFIG),
        "guideline_sha256": file_hash(GUIDELINE),
        "adjudication_map_sha256": file_hash(args.adjudication_map) if args.adjudication_map else None,
        "note": "Canonical output is a candidate, not adjudicated gold. Human review must approve it.",
    }
    report_path = args.output_dir / "pilot_qa_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "pilot_review_items.json").write_text(
        json.dumps(review_items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if complete:
        output_path = args.output_dir / "pilot_canonical_candidate.jsonl"
        with output_path.open("w", encoding="utf-8") as stream:
            for record in sorted(canonical, key=lambda item: item["sample_id"]):
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps({"status": report["status"], "counts": report["counts"],
                      "report": str(report_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
