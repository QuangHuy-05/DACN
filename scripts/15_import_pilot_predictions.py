"""Attach reviewed-by-human candidate spans as Label Studio predictions.

This script never creates tasks or annotations. Its default mode is a dry run.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATES = ROOT / "data/interim/annotation/sprint03/pilot_span11_candidate_answers.json"
EXPECTED_PROJECT_TITLE = "DACN_S3_T0_PILOT_v1"
MODEL_VERSION = "s3_span11_manual_candidates_v1_not_gold"
LABELS = {
    "SoNha", "TenDuong", "Ngo/Hem", "ToaNha/CanHo", "PhuongXa",
    "QuanHuyen", "TinhThanh", "MocDinhVi", "HuongDi", "GhiChu", "Khac",
}
SPAN_SYSTEMS = {"cu", "moi", "khong_xac_dinh"}
ADDRESS_SYSTEMS = {"cu", "moi", "Lai"}
REVIEW_FLAGS = {"unreadable_ocr", "ambiguous_label", "temporal_ambiguity", "privacy_review"}


def request_json(base_url: str, path: str, method: str = "GET", payload=None,
                 authorization: str | None = None):
    headers = {"Accept": "application/json"}
    if authorization:
        headers["Authorization"] = authorization
    body = None
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(base_url + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read(500).decode("utf-8", errors="replace")
        raise RuntimeError(f"Label Studio API returned HTTP {error.code} at {path}: {detail}") from error


def authorization_header(base_url: str, token_kind: str) -> str:
    token = os.environ.get("LABEL_STUDIO_API_TOKEN", "").strip()
    if not token:
        raise ValueError("Set LABEL_STUDIO_API_TOKEN in this terminal; do not paste it into a file or chat")
    if token_kind == "legacy":
        return f"Token {token}"
    response = request_json(base_url, "/api/token/refresh", "POST", {"refresh": token})
    access = response.get("access") if isinstance(response, dict) else None
    if not isinstance(access, str) or not access:
        raise RuntimeError("PAT refresh did not return an access token")
    return f"Bearer {access}"


def validate_candidates(path: Path, expected_count: int = 68) -> dict[str, dict]:
    if not path.is_file():
        raise FileNotFoundError(path)
    records = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(records, list) or len(records) != expected_count:
        raise ValueError(f"Expected exactly {expected_count} candidates")
    result = {}
    for record in records:
        sample_id, text = record.get("sample_id"), record.get("text")
        if not isinstance(sample_id, str) or not isinstance(text, str) or sample_id in result:
            raise ValueError(f"Missing or duplicate sample_id: {sample_id!r}")
        if record.get("status") != "candidate_not_gold":
            raise ValueError(f"{sample_id}: unexpected candidate status")
        if record.get("address_system") not in ADDRESS_SYSTEMS | {None}:
            raise ValueError(f"{sample_id}: invalid address system")
        flags = record.get("review_flags", [])
        if not isinstance(flags, list) or not set(flags) <= REVIEW_FLAGS:
            raise ValueError(f"{sample_id}: invalid review flags")
        if not isinstance(record.get("review_note", ""), str):
            raise ValueError(f"{sample_id}: invalid review note")
        spans = record.get("spans")
        if not isinstance(spans, list):
            raise ValueError(f"{sample_id}: spans must be a list")
        previous_end = 0
        for span in spans:
            start, end = span.get("start"), span.get("end")
            if (type(start) is not int or type(end) is not int or
                    not 0 <= previous_end <= start < end <= len(text) or
                    text[start:end] != span.get("text") or
                    span.get("label") not in LABELS or
                    span.get("system") not in SPAN_SYSTEMS):
                raise ValueError(f"{sample_id}: invalid span at [{start},{end})")
            if span["label"] == "QuanHuyen" and span["system"] != "cu":
                raise ValueError(f"{sample_id}: QuanHuyen must use system=cu")
            previous_end = end
        result[sample_id] = record
    return result


def prediction_results(record: dict) -> list[dict]:
    results = []
    for index, span in enumerate(record["spans"], start=1):
        region_id = f"span_{index:03d}"
        results.append({
            "id": region_id, "from_name": "span_label", "to_name": "address_text",
            "type": "labels", "value": {
                "start": span["start"], "end": span["end"], "text": span["text"],
                "labels": [span["label"]],
            },
        })
        # The shared region ID connects the required system choice to its span.
        results.append({
            "id": region_id, "from_name": "span_system", "to_name": "address_text",
            "type": "choices", "value": {
                "start": span["start"], "end": span["end"], "text": span["text"],
                "choices": [span["system"]],
            },
        })
    if record["address_system"] is not None:
        results.append({
            "id": "address_system", "from_name": "address_system", "to_name": "address_text",
            "type": "choices", "value": {"choices": [record["address_system"]]},
        })
    if record["review_flags"]:
        results.append({
            "id": "review_flag", "from_name": "review_flag", "to_name": "address_text",
            "type": "choices", "value": {"choices": record["review_flags"]},
        })
    if record["review_note"]:
        results.append({
            "id": "review_note", "from_name": "review_note", "to_name": "address_text",
            "type": "textarea", "value": {"text": [record["review_note"]]},
        })
    return results


def validate_project(project: dict, expected_title: str = EXPECTED_PROJECT_TITLE) -> None:
    if project.get("title") != expected_title:
        raise ValueError(f"Wrong project title: {project.get('title')!r}")
    config = project.get("label_config")
    if not isinstance(config, str):
        raise ValueError("Project label_config is unavailable")
    root = ET.fromstring(config)
    controls = {element.get("name"): element for element in root.iter()
                if element.tag in {"Labels", "Choices", "TextArea"}}
    if set(controls) != {"span_label", "span_system", "address_system", "review_flag", "review_note"}:
        raise ValueError("Project controls differ from the Sprint 3 pilot XML")
    if {label.get("value") for label in controls["span_label"]} != LABELS:
        raise ValueError("Project span labels differ from the 11-label schema")
    if {choice.get("value") for choice in controls["span_system"]} != SPAN_SYSTEMS:
        raise ValueError("Project span systems differ from the candidate schema")
    if controls["span_system"].get("perRegion") != "true":
        raise ValueError("Project span_system is not per-region")
    if controls["span_system"].get("required") != "true":
        raise ValueError("Project span_system must be required")
    if {choice.get("value") for choice in controls["address_system"]} != ADDRESS_SYSTEMS:
        raise ValueError("Project address systems differ from the locked XML")
    if {choice.get("value") for choice in controls["review_flag"]} != REVIEW_FLAGS:
        raise ValueError("Project review flags differ from the locked XML")


def fetch_tasks(base_url: str, project_id: int, authorization: str) -> list[dict]:
    tasks = []
    page = 1
    while True:
        query = urllib.parse.urlencode({
            "project": project_id, "fields": "all", "page_size": 100, "page": page,
        })
        response = request_json(base_url, f"/api/tasks/?{query}", authorization=authorization)
        batch = response.get("tasks") if isinstance(response, dict) else None
        if not isinstance(batch, list) or not isinstance(response.get("total"), int):
            raise ValueError("Unexpected paginated task response")
        tasks.extend(batch)
        if len(tasks) >= response["total"]:
            if len(tasks) != response["total"]:
                raise ValueError("Task pages contain repeated entries")
            break
        if not batch:
            raise ValueError("Task pagination stopped before total was reached")
        page += 1
    return tasks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--project-id", type=int, default=1)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--token-kind", choices=("legacy", "pat"), default="legacy")
    parser.add_argument("--sample-id", help="Import only one sample first for UI inspection")
    parser.add_argument("--apply", action="store_true", help="Write predictions to existing tasks")
    parser.add_argument("--expected-count", type=int, default=68)
    parser.add_argument("--project-title", default=EXPECTED_PROJECT_TITLE)
    parser.add_argument("--model-version", default=MODEL_VERSION)
    args = parser.parse_args()
    url = urllib.parse.urlparse(args.base_url)
    if url.scheme != "http" or url.hostname not in {"localhost", "127.0.0.1"} or url.path.strip("/"):
        raise ValueError("Only a local http://localhost:8080 Label Studio URL is accepted")
    base_url = args.base_url.rstrip("/")
    if args.expected_count < 1 or "TEST" in args.project_title.upper():
        raise ValueError("Predictions are restricted to train/dev projects")
    candidates = validate_candidates(args.candidates, expected_count=args.expected_count)
    hold_manifest = ROOT / "data/interim/annotation/sprint03/test_hold_manifest_v1.json"
    if hold_manifest.is_file():
        held_out_ids = {row["sample_id"] for row in json.loads(hold_manifest.read_text(encoding="utf-8"))["samples"]}
        if set(candidates) & held_out_ids:
            raise ValueError("Candidate IDs overlap the frozen benchmark test hold")
    if args.sample_id and args.sample_id not in candidates:
        raise ValueError(f"Unknown sample_id: {args.sample_id}")
    authorization = authorization_header(base_url, args.token_kind)
    project = request_json(base_url, f"/api/projects/{args.project_id}/", authorization=authorization)
    validate_project(project, expected_title=args.project_title)
    tasks = fetch_tasks(base_url, args.project_id, authorization)
    by_sample = {}
    for task in tasks:
        data = task.get("data") if isinstance(task, dict) else None
        sample_id = data.get("sample_id") if isinstance(data, dict) else None
        if sample_id in by_sample:
            raise ValueError(f"Duplicate task sample_id in project: {sample_id}")
        by_sample[sample_id] = task
    if len(tasks) != args.expected_count or set(by_sample) != set(candidates):
        raise ValueError("Project tasks differ from candidate sample IDs; no upload performed")
    for sample_id, task in by_sample.items():
        if task["data"].get("text") != candidates[sample_id]["text"]:
            raise ValueError(f"{sample_id}: task text differs from candidate; no upload performed")
        if type(task.get("id")) is not int:
            raise ValueError(f"{sample_id}: missing numeric task ID")

    pending, annotated, existing = [], [], []
    for sample_id, task in by_sample.items():
        if args.sample_id and sample_id != args.sample_id:
            continue
        annotation_count = task.get("total_annotations")
        predictions = task.get("predictions")
        if not isinstance(annotation_count, int) or not isinstance(predictions, list):
            raise ValueError(f"{sample_id}: full annotation/prediction fields unavailable")
        if annotation_count > 0 or task.get("annotations"):
            annotated.append(sample_id)
        elif any(prediction.get("model_version") == args.model_version for prediction in predictions):
            existing.append(sample_id)
        else:
            pending.append((task["id"], sample_id))

    print(json.dumps({
        "mode": "apply" if args.apply else "dry_run", "project_id": args.project_id,
        "project_tasks": len(tasks), "to_import": len(pending),
        "already_annotated_skipped": annotated, "already_imported_skipped": existing,
        "pending_sample_ids": [sample_id for _, sample_id in pending],
    }, ensure_ascii=False, indent=2))
    if not args.apply or not pending:
        return
    payload = [
        {"task": task_id, "model_version": args.model_version,
         "result": prediction_results(candidates[sample_id])}
        for task_id, sample_id in pending
    ]
    response = request_json(
        base_url, f"/api/projects/{args.project_id}/import/predictions",
        "POST", payload, authorization,
    )
    if not isinstance(response, dict) or response.get("created") != len(payload):
        raise RuntimeError(f"Import response did not confirm {len(payload)} predictions: {response!r}")
    print(f"Imported {len(payload)} candidate predictions. Open Label Studio and review before Submit.")


if __name__ == "__main__":
    main()
