"""Hash-bound test approval and immutable three-split release.

This publisher never edits an export or derives T1 from benchmark metadata.
Preparation is a candidate; publication additionally requires human decisions.
"""

from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path
import shutil

from src.data.annotation_release import (annotation_fingerprint, content_findings,
    coverage, file_hash, read_csv, read_jsonl, validate_canonical_annotation,
    write_json, write_jsonl)
from src.data.test_annotation_qa import t1_review_findings
from src.modeling.datasets import load_corpus

APPROVED_STATUS = "CORPUS_240_60_100_APPROVED"
DECISION_CODES_REQUIRING_T1_MASK = {
    "t1_evidence_needs_review", "dated_reference_system_conflict",
    "address_span_system_conflict", "new_address_contains_district",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def provenance_kind(metadata):
    derivation = metadata.get("derivation", "").casefold()
    # This queue value explicitly mixes observation and existing benchmark children.
    if derivation == "observed_or_existing_benchmark":
        return "unverified_provenance"
    if derivation.startswith("observed"):
        return "observed"
    if derivation.startswith("derived"):
        return "derived"
    if derivation.startswith(("synthetic", "controlled_synthetic")):
        return "synthetic"
    return "unverified_provenance"


def locked_source_metadata(train_dev_dir, source_manifest):
    """Read provenance only from source queues already pinned by the train/dev release."""
    root = Path(train_dev_dir).resolve().parents[4]
    result = {}
    for relative, expected in source_manifest.get("input_sha256", {}).items():
        if not Path(relative).name.startswith("annotation_queue_") or not relative.endswith(".csv"):
            continue
        path = (root / relative).resolve()
        path.relative_to(root)
        if file_hash(path) != expected:
            raise ValueError("TRAIN_DEV_PROVENANCE_QUEUE_CHANGED")
        for row in read_csv(path, {"sample_id", "text", "group_id"}):
            sid = row["sample_id"]
            if sid in result and result[sid] != row:
                raise ValueError("CONFLICTING_LOCKED_PROVENANCE_QUEUE")
            result[sid] = row
    return result


def selected_fingerprint(record, converted):
    value = {"canonical": annotation_fingerprint(record),
             "review_flags": converted["review_flags"], "review_note": converted["review_note"]}
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def candidate_inputs(qa_dir, queue_path, hold_path, assisted_manifest_path, selection_path=None,
                     manual_findings_path=None):
    """Recheck selected raw annotations, not just a prior green QA report."""
    qa_dir, queue_path, hold_path, assisted_manifest_path = map(
        Path, (qa_dir, queue_path, hold_path, assisted_manifest_path))
    converter = importlib.import_module("scripts.17_convert_span_annotation_batch")
    report = load_json(qa_dir / "structure/qa_report.json")
    export_path = qa_dir / "inputs/label_studio_export.json"
    checks = {"export_sha256": export_path, "queue_sha256": queue_path,
              "guideline_sha256": converter.GUIDELINE, "label_config_sha256": converter.LABEL_CONFIG}
    for key, path in checks.items():
        if report.get(key) != file_hash(path):
            raise ValueError("STALE_QA_BINDING:" + key)
    if (report.get("status") != "READY_FOR_HUMAN_REVIEW" or report.get("issues") or
            report.get("expected_tasks") != 100 or report.get("converted_tasks") != 100):
        raise ValueError("TEST_QA_NOT_COMPLETE_100")
    selection = load_json(selection_path) if selection_path else {}
    if report.get("adjudication_map_sha256") != (file_hash(Path(selection_path)) if selection_path else None):
        raise ValueError("STALE_ANNOTATION_SELECTION")
    queue = converter.read_queue(queue_path, converter.TEST_ROLE)
    suggestions, protocol = converter.load_test_assistance(assisted_manifest_path, queue)
    if report.get("annotation_protocol") != protocol:
        raise ValueError("ASSISTED_PROTOCOL_CHANGED")
    hold = load_json(hold_path)
    frozen = {item["sample_id"]: item for item in hold["samples"]}
    if (hold.get("status") != "FROZEN_BENCHMARK_TEST_HOLD" or len(frozen) != 100 or
            len(hold["samples"]) != 100 or set(queue) != set(frozen)):
        raise ValueError("FROZEN_TEST_IDENTITY_CHANGED")
    tasks = load_json(export_path)
    if not isinstance(tasks, list) or len(tasks) != 100:
        raise ValueError("EXPORT_TASK_COUNT_CHANGED")
    by_id = {}
    for task in tasks:
        data = task.get("data", {})
        sid = data.get("sample_id")
        if set(data) != {"sample_id", "text"} or sid in by_id or sid not in queue:
            raise ValueError("EXPORT_HIDDEN_OR_DUPLICATE_ID")
        by_id[sid] = task
    records = read_jsonl(qa_dir / "structure/canonical_candidate.jsonl")
    canonical = {record["sample_id"]: record for record in records}
    if len(records) != 100 or set(canonical) != set(frozen) or set(selection) - set(frozen):
        raise ValueError("CANONICAL_IDENTITY_CHANGED")
    selected, findings = {}, []
    for sid, expected in queue.items():
        frozen_row, task, record = frozen[sid], by_id[sid], canonical[sid]
        if set(record) != {"sample_id", "text", "spans", "address_system", "source_group"} or any(
                set(span) != {"start", "end", "label", "system"} for span in record["spans"]):
            raise ValueError("CANONICAL_SCHEMA_CHANGED:" + sid)
        if (task["data"]["text"] != expected["text"] or record["text"] != expected["text"] or
                text_hash(expected["text"]) != frozen_row["text_sha256"] or
                expected["group_id"] != frozen_row["group_id"] or
                expected["source_dataset"] != frozen_row["source_dataset"] or
                record["source_group"] != expected["group_id"]):
            raise ValueError("TEST_TEXT_GROUP_CHANGED:" + sid)
        annotations = [ann for ann in task["annotations"] if not ann.get("was_cancelled")]
        if sid in selection:
            annotations = [ann for ann in annotations if ann.get("id") == selection[sid]]
        if len(annotations) != 1:
            raise ValueError("ANNOTATION_SELECTION_REQUIRED:" + sid)
        annotation = annotations[0]
        converter.verify_assisted_prediction(task, annotation, suggestions[sid])
        converted = converter.convert_annotation(annotation, record["text"], sid)
        validate_canonical_annotation(record, converted)
        selected[sid] = {"task_id": task["id"], "annotation_id": annotation["id"],
                         "label_studio_user_id": annotation["completed_by"],
                         "annotation_sha256": selected_fingerprint(record, converted),
                         "review_flags": converted["review_flags"], "review_note": converted["review_note"]}
        findings.extend({**finding, "sample_id": sid} for finding in
                        content_findings(record) + t1_review_findings(record))
    if manual_findings_path:
        manual = load_json(manual_findings_path)
        if manual.get("export_sha256") != file_hash(export_path):
            raise ValueError("STALE_MANUAL_REVIEW")
        for finding in manual.get("findings", []):
            if finding.get("sample_id") not in canonical or not finding.get("code") or not finding.get("reason"):
                raise ValueError("INVALID_MANUAL_FINDING")
            findings.append(finding)
    bindings = {key: file_hash(path) for key, path in checks.items()}
    bindings.update(assisted_manifest_sha256=file_hash(assisted_manifest_path),
                    hold_manifest_sha256=file_hash(hold_path),
                    canonical_sha256=file_hash(qa_dir / "structure/canonical_candidate.jsonl"),
                    selection_sha256=file_hash(Path(selection_path)) if selection_path else None,
                    manual_findings_sha256=file_hash(Path(manual_findings_path)) if manual_findings_path else None)
    return records, queue, selected, findings, bindings


def validate_approval(approval, decisions, selected, findings, bindings):
    """Require current scope, identity, all flags, and explicit T1 exceptions."""
    if (approval.get("bindings") != bindings or approval.get("reviewed_sample_count") != len(selected) or
            not approval.get("reviewer") or not approval.get("reviewed_at") or
            not approval.get("human_authorization_quote") or approval.get("decision") != "approve"):
        raise ValueError("HUMAN_APPROVAL_MISSING_STALE_OR_WRONG_SCOPE")
    user_id = approval.get("label_studio_user_id")
    if user_id is None or any(item["label_studio_user_id"] != user_id for item in selected.values()):
        raise ValueError("REVIEWER_IDENTITY_MISMATCH")
    if decisions.get("bindings") != bindings or decisions.get("reviewer") != approval["reviewer"]:
        raise ValueError("STALE_DECISIONS_OR_REVIEWER")
    by_id = {}
    for decision in decisions.get("decisions", []):
        sid = decision.get("sample_id")
        if (sid not in selected or sid in by_id or
                decision.get("annotation_sha256") != selected[sid]["annotation_sha256"] or
                decision.get("annotation_id") != selected[sid]["annotation_id"] or
                decision.get("decision") not in {"keep", "keep_as_exception"} or
                not decision.get("reason") or not decision.get("reviewed_at") or
                type(decision.get("exclude_from_t1")) is not bool):
            raise ValueError("INVALID_REVIEW_DECISION")
        by_id[sid] = decision
    expected_codes = {}
    for finding in findings:
        expected_codes.setdefault(finding["sample_id"], set()).add(finding["code"])
    for sid, item in selected.items():
        required = expected_codes.get(sid, set()) | {"flag:" + flag for flag in item["review_flags"]}
        decision = by_id.get(sid)
        if required and (decision is None or set(decision.get("accepted_finding_codes", [])) != required):
            raise ValueError("UNRESOLVED_FINDING_OR_FLAG:" + sid)
        if decision:
            if set(decision.get("accepted_finding_codes", [])) != required:
                raise ValueError("UNKNOWN_OR_STALE_FINDING:" + sid)
            if required & DECISION_CODES_REQUIRING_T1_MASK and not decision["exclude_from_t1"]:
                if not decision.get("temporal_evidence"):
                    raise ValueError("TEMPORAL_EVIDENCE_OR_EXCLUSION_REQUIRED:" + sid)
            if decision["exclude_from_t1"] and decision["decision"] != "keep_as_exception":
                raise ValueError("MASK_REQUIRES_DECLARED_EXCEPTION")
    excluded = sorted(sid for sid, decision in by_id.items() if decision["exclude_from_t1"])
    if excluded != sorted(approval.get("evaluation_exclusions", {}).get("t1", [])):
        raise ValueError("APPROVAL_EXCEPTION_SCOPE_MISMATCH")
    return excluded


def audit_release_split(train_dev_dir, records, assignment_path, decisions_path, queue_path, hold_path):
    source_manifest, splits = load_corpus(Path(train_dev_dir))
    if {key: len(value) for key, value in splits.items()} != {"train": 240, "dev": 60}:
        raise ValueError("TRAIN_DEV_COUNTS_CHANGED")
    for path in (assignment_path, decisions_path, queue_path, hold_path):
        relative = Path(path).resolve().relative_to(Path(train_dev_dir).resolve().parents[4]).as_posix()
        # Paths are explicitly pinned in the approved train/dev source manifest.
        if source_manifest["input_sha256"].get(relative) != file_hash(Path(path)):
            raise ValueError("FROZEN_SPLIT_SOURCE_CHANGED:" + relative)
    assignments = read_csv(Path(assignment_path), {"sample_id", "split", "source_group"})
    by_id = {row["sample_id"]: row for row in assignments}
    if len(by_id) != 300 or len(assignments) != 300:
        raise ValueError("FROZEN_ASSIGNMENT_COUNTS_CHANGED")
    for split, rows in splits.items():
        for row in rows:
            assignment = by_id.get(row["sample_id"], {})
            if assignment.get("split") != split or assignment.get("source_group") != row["source_group"]:
                raise ValueError("FROZEN_ASSIGNMENT_CHANGED")
    auditor = importlib.import_module("scripts.18_audit_corpus_split")
    batch_builder = importlib.import_module("scripts.16_prepare_t0_corpus_batch")
    audit = auditor.audit_splits(splits["train"], splits["dev"], records,
                                batch_builder.get_reserved_benchmark_groups())
    old_decisions = auditor.read_queue_for_decisions(Path(decisions_path))
    current_pairs = {(r["first_sample_id"], r["second_sample_id"]): r for r in audit["near_duplicates_review_queue"]}
    for decision in old_decisions:
        pair = (decision["first_sample_id"], decision["second_sample_id"])
        current = current_pairs.get(pair)
        if not current or any(decision[key] != current[key] for key in
                              ("first_text", "second_text", "first_split", "second_split")):
            raise ValueError("NEAR_DUPLICATE_REVIEW_TEXT_CHANGED")
    audit = auditor.apply_decisions(audit, Path(decisions_path))
    if audit["status"] not in {"AUDIT_PASS", "AUDIT_PASS_WITH_HUMAN_NEAR_DUP_REVIEW"}:
        raise ValueError("SPLIT_AUDIT_BLOCKED:" + audit["status"])
    audit["reused_decisions_count"] = len(old_decisions)
    return source_manifest, splits, audit


def prepare_test_release(qa_dir, queue_path, hold_path, assisted_manifest_path,
                         output_dir, selection_path=None, manual_findings_path=None):
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(output_dir)
    records, queue, selected, findings, bindings = candidate_inputs(
        qa_dir, queue_path, hold_path, assisted_manifest_path, selection_path, manual_findings_path)
    output_dir.mkdir(parents=True)
    write_jsonl(output_dir / "canonical_candidate.jsonl", records)
    write_json(output_dir / "candidate_review.json", {"status": "CANDIDATE_NOT_GOLD", "bindings": bindings,
        "selected_annotations": selected, "findings": findings,
        "required_flag_decisions": {sid: item["review_flags"] for sid, item in selected.items() if item["review_flags"]},
        "sample_count": len(records), "human_approval": "REQUIRED", "agreement": "NOT_MEASURED"})
    return {"status": "CANDIDATE_NOT_GOLD", "sample_count": len(records), "findings": len(findings)}


def publish_test_corpus(qa_dir, queue_path, hold_path, assisted_manifest_path, train_dev_dir,
                        assignment_path, decisions_path, approval_path, review_decisions_path,
                        output_dir, selection_path=None, manual_findings_path=None, test_output_dir=None):
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(output_dir)
    test_output_dir = Path(test_output_dir) if test_output_dir else None
    if test_output_dir and (test_output_dir.exists() or test_output_dir.resolve() == output_dir.resolve()):
        raise FileExistsError(test_output_dir)
    records, queue, selected, findings, bindings = candidate_inputs(
        qa_dir, queue_path, hold_path, assisted_manifest_path, selection_path, manual_findings_path)
    approval, decisions = load_json(approval_path), load_json(review_decisions_path)
    excluded = validate_approval(approval, decisions, selected, findings, bindings)
    source, splits, audit = audit_release_split(train_dev_dir, records, assignment_path,
                                               decisions_path, queue_path, hold_path)
    output_dir.mkdir(parents=True)
    for name in ("train.jsonl", "dev.jsonl", "dev_input.jsonl"):
        shutil.copyfile(Path(train_dev_dir) / name, output_dir / name)
    write_jsonl(output_dir / "test_benchmark_t0.jsonl", records)
    write_jsonl(output_dir / "test_input.jsonl", [{"sample_id": r["sample_id"], "text": r["text"]} for r in records])
    write_json(output_dir / "approval_record.json", approval)
    write_json(output_dir / "review_decisions.json", decisions)
    write_json(output_dir / "selected_annotations.json", selected)
    write_json(output_dir / "test_findings.json", findings)
    write_json(output_dir / "split_audit_report.json", audit)
    write_json(output_dir / "train_dev_source_manifest.json", source)
    test_coverage = coverage(records, queue)
    test_coverage["source_kind"] = dict(Counter(provenance_kind(queue[r["sample_id"]]) for r in records))
    test_coverage["provenance_note"] = (
        "observed_or_existing_benchmark is ambiguous and remains unverified_provenance; "
        "source_dataset and stratum are retained, without claiming all test rows were observed.")
    test_coverage["t1_eligible"] = sum(r["address_system"] is not None and r["sample_id"] not in excluded for r in records)
    test_coverage["t1_excluded_ids"] = excluded
    write_json(output_dir / "coverage.json", {"train_dev": load_json(Path(train_dev_dir) / "coverage.json"),
                                             "test": test_coverage})
    registry = []
    source_metadata = locked_source_metadata(train_dev_dir, source)
    for split, rows in {**splits, "test": records}.items():
        for row in rows:
            metadata = (queue if split == "test" else source_metadata).get(row["sample_id"], {})
            if metadata and (metadata["text"] != row["text"] or metadata["group_id"] != row["source_group"]):
                raise ValueError("PROVENANCE_IDENTITY_MISMATCH")
            registry.append({"sample_id": row["sample_id"], "source_group": row["source_group"],
                "split": split, "text_sha256": text_hash(row["text"]),
                "source_dataset": metadata.get("source_dataset", "see_train_dev_source_manifest"),
                "stratum": metadata.get("stratum", "not_recorded"),
                "source_kind": provenance_kind(metadata),
                "derivation": metadata.get("derivation", "not_recorded"),
                "feature_permission": "scorer_sidecar_only_never_inference"})
    write_jsonl(output_dir / "identity_registry.jsonl", registry)
    (output_dir / "README.md").write_text(
        "# Corpus Sprint 3\n\n240 train / 60 dev / 100 test. "
        "Train/dev bytes match corpus_train_dev_v2; its source manifest remains immutable.\n\n"
        "Test annotation: AI-assisted human review; independent agreement NOT_MEASURED. "
        "Read evaluation_exclusions.t1 before T1 scoring/structure diagnostics; every T0 span remains.\n\n"
        "Training uses the original pinned train/dev release. Final inference uses test_input.jsonl only; "
        "gold is opened by a separate scorer after prediction freeze. Test is never for tuning.\n",
        encoding="utf-8")
    manifest = {"version": output_dir.name, "status": APPROVED_STATUS,
        "schema_version": "s3-span-v1.1", "created_at": datetime.now(timezone.utc).isoformat(),
        "sample_counts": {"train": 240, "dev": 60, "test": 100},
        "annotation_mode": "AI_ASSISTED_HUMAN_REVIEW", "agreement": "NOT_MEASURED",
        "quality_status": "APPROVED_WITH_DECLARED_EXCEPTIONS" if excluded or source["evaluation_exclusions"]["t1"] else "APPROVED",
        "evaluation_exclusions": {"t1": sorted(set(source["evaluation_exclusions"]["t1"]) | set(excluded))},
        "test_evaluation_exclusions": {"t1": excluded}, "test_approval_bindings": bindings,
        "source_train_dev_manifest_sha256": file_hash(Path(train_dev_dir) / "manifest.json"),
        "approval_sha256": file_hash(Path(approval_path)), "decisions_sha256": file_hash(Path(review_decisions_path)),
        "split_source_sha256": {Path(p).resolve().relative_to(Path(train_dev_dir).resolve().parents[4]).as_posix():
                                file_hash(Path(p)) for p in (assignment_path, decisions_path)},
        "output_sha256": {p.name: file_hash(p) for p in output_dir.iterdir() if p.is_file()},
        "code_sha256": {"publisher": file_hash(Path(__file__)),
                         "converter": file_hash(Path(importlib.import_module("scripts.17_convert_span_annotation_batch").__file__))},
        "model_test_inference_scoring": "NOT_EXECUTED"}
    if test_output_dir:
        test_output_dir.mkdir(parents=True)
        for name in ("test_benchmark_t0.jsonl", "test_input.jsonl", "approval_record.json", "review_decisions.json",
                     "selected_annotations.json", "test_findings.json", "split_audit_report.json", "README.md"):
            shutil.copyfile(output_dir / name, test_output_dir / name)
        write_json(test_output_dir / "coverage.json", test_coverage)
        write_jsonl(test_output_dir / "identity_registry.jsonl", [row for row in registry if row["split"] == "test"])
        test_manifest = {**manifest, "version": test_output_dir.name, "status": "TEST_GOLD_APPROVED",
            "sample_counts": {"test": 100}, "evaluation_exclusions": {"t1": excluded},
            "output_sha256": {p.name: file_hash(p) for p in test_output_dir.iterdir() if p.is_file()}}
        write_json(test_output_dir / "manifest.json", test_manifest)
        manifest["source_test_release"] = {"path": test_output_dir.resolve().relative_to(
            Path(train_dev_dir).resolve().parents[4]).as_posix(), "manifest_sha256": file_hash(test_output_dir / "manifest.json")}
    write_json(output_dir / "manifest.json", manifest)
    return manifest
