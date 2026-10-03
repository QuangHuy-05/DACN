"""Review canonical annotations and prepare a frozen train/dev candidate.

Raw exports stay immutable. Content findings quarantine samples; they never
rewrite spans or silently promote structural QA to approved gold.
"""

from __future__ import annotations

from collections import Counter
import csv
import hashlib
import importlib
import json
from pathlib import Path
import re
import shutil

from src.evaluation.schema import ADDRESS_SYSTEMS, SPAN11_LABELS


DEFAULT_SYSTEM_LABELS = {
    "SoNha", "TenDuong", "Ngo/Hem", "ToaNha/CanHo", "MocDinhVi",
    "HuongDi", "GhiChu", "Khac",
}
TEMPORAL_CUE = re.compile(r"nay là|trước|sau|\bcũ\b|\bmới\b|\b20\d{2}\b", re.I)
ADMIN_PREFIX = re.compile(
    r"(?:^|[,;]\s*|\bnay là\s+)(?P<name>Phường|Xã|Thị trấn|Quận|Huyện|Thị xã|Tỉnh|Thành phố|P\.|Q\.|TP\.)(?:\s+|(?<=\.)(?=\S))",
    re.I,
)
PREFIX_LABEL = {
    "phường": "PhuongXa", "xã": "PhuongXa", "thị trấn": "PhuongXa",
    "quận": "QuanHuyen", "huyện": "QuanHuyen", "thị xã": "QuanHuyen",
    "tỉnh": "TinhThanh", "thành phố": "TinhThanh",
    "p.": "PhuongXa", "q.": "QuanHuyen", "tp.": "TinhThanh",
}


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(path)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_csv(path: Path, required: set[str]) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if required - set(reader.fieldnames or ()):
            raise ValueError(f"{path}: missing columns {sorted(required - set(reader.fieldnames or ()))}")
        return list(reader)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, values: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in values), encoding="utf-8")


def content_findings(record: dict) -> list[dict]:
    """Conservative text-only checks. Findings require human correction/review."""
    text, spans = record["text"], record["spans"]
    findings = []

    def add(code: str, reason: str, start: int | None = None, end: int | None = None) -> None:
        item = {"sample_id": record["sample_id"], "code": code, "reason": reason,
                "start": start, "end": end, "text": text[start:end] if start is not None else text}
        if item not in findings:
            findings.append(item)

    for span in spans:
        start, end = span["start"], span["end"]
        literal = text[start:end]
        if span["label"] in DEFAULT_SYSTEM_LABELS and span["system"] != "khong_xac_dinh" and not TEMPORAL_CUE.search(text):
            add("nonadministrative_system_without_time", f"{span['label']} has system {span['system']} without a textual time cue; review against guideline default khong_xac_dinh.", start, end)
        if literal != literal.strip() or literal.startswith((",", ";")) or literal.endswith((",", ";")):
            add("separator_in_span", "External whitespace/separator is included in the span.", start, end)
        if re.match(r"^(?:thôn|ấp|khu phố)\b", literal, re.I) and span["label"] != "Khac":
            add("subward_component_label", "A bare thôn/ấp/khu phố component is Khac under the frozen schema; a relative landmark phrase is a separate case.", start, end)
        # Repeated mentions are separate spans, even if the surface name repeats.
        if span["label"] in {"PhuongXa", "QuanHuyen", "TinhThanh"} and len(literal) > 2:
            for match in re.finditer(re.escape(literal), text):
                left, right = match.span()
                if ((left and text[left - 1].isalnum()) or
                        (right < len(text) and text[right].isalnum())):
                    continue
                if not any(s["start"] < right and s["end"] > left for s in spans):
                    add("unannotated_repeated_entity", f"An unannotated occurrence repeats surface text from {span['label']}; human must determine its level from context, since identical names can denote different entities.", left, right)

    for match in ADMIN_PREFIX.finditer(text):
        start = match.start("name")
        prefix_end = match.end("name")
        covering = [s for s in spans if s["start"] <= start and s["end"] >= prefix_end]
        expected = PREFIX_LABEL[match.group("name").casefold()]
        if match.group("name").casefold() == "tỉnh" and re.match(r"lộ\b", text[match.end():], re.I):
            continue  # Tỉnh lộ is a road, not a province mention.
        if not covering:
            end = next((i for i in range(prefix_end, len(text)) if text[i] in ",;"), len(text))
            add("unannotated_administrative_prefix", f"Visible {match.group('name')} component is unannotated; expected label candidate {expected}.", start, end)
        elif covering[0]["label"] != expected:
            # Thành phố can also be a district in the old hierarchy. Review,
            # rather than automatically rewriting the administrative level.
            if match.group("name").casefold() in {"thành phố", "tp."} and covering[0]["label"] == "QuanHuyen":
                continue
            add("administrative_label_mismatch", f"Visible prefix suggests {expected}, but span is {covering[0]['label']}.", covering[0]["start"], covering[0]["end"])

    leading = re.match(r"(?:Số\s+)?\d[^,;]*", text, re.I)
    if leading:
        houses = [s for s in spans if s["label"] == "SoNha" and s["start"] < leading.end()]
        if not houses:
            add("unannotated_leading_number", "Leading numeric component has no SoNha span; human must confirm its meaning and boundary.", 0, leading.end())
        elif re.search(r"\(\s*\d", leading.group()) and not any(s["end"] >= leading.end() for s in houses):
            add("parenthetical_house_boundary", "A numeric parenthesis follows SoNha; the complete house-number boundary needs an explicit decision.", 0, leading.end())

    if record.get("address_system") == "moi" and any(s["label"] == "QuanHuyen" for s in spans):
        add("new_address_contains_district", "T1 moi conflicts with a visible QuanHuyen span; review T1 without deleting the entity.")
    administrative_spans = [span for span in spans if span["label"] in {"PhuongXa", "QuanHuyen", "TinhThanh"}]
    whole_system = record.get("address_system")
    conflicting_system = {"moi": "cu", "cu": "moi"}.get(whole_system)
    # Relabeling a district as a ward must not hide an old/new contradiction.
    # Lai and null are deliberately not treated as inconsistent here.
    if conflicting_system and any(span["system"] == conflicting_system for span in administrative_spans):
        if not (whole_system == "moi" and any(span["label"] == "QuanHuyen" for span in spans)):
            add("address_span_system_conflict", f"T1 {whole_system} conflicts with an administrative span explicitly marked {conflicting_system}; review both decisions using text evidence.")
    explicit_missing_ranges = {(item["start"], item["end"]) for item in findings if item["code"] == "unannotated_administrative_prefix"}
    return [item for item in findings if item["code"] != "unannotated_repeated_entity" or not any(start <= item["start"] and end >= item["end"] for start, end in explicit_missing_ranges)]


def load_manual_findings(path: Path | None, export_paths: dict[str, Path], records: dict[str, dict]) -> dict[str, list[dict]]:
    """Bind additional content-review findings to the exact export and text.

    This supplements text rules; it cannot override them or edit annotations.
    Reviewer identity describes who reported the issue, not who approved gold.
    """
    if path is None:
        return {}
    review = json.loads(path.read_text(encoding="utf-8"))
    expected_hashes = {name: file_hash(export_path) for name, export_path in export_paths.items()}
    if review.get("export_sha256") != expected_hashes:
        raise ValueError("Manual content review is stale for these exports")
    if not review.get("reviewer") or not review.get("evidence") or not isinstance(review.get("findings"), list):
        raise ValueError("Manual content review needs reviewer, evidence and findings")
    findings_by_id: dict[str, list[dict]] = {}
    for item in review["findings"]:
        sid = item.get("sample_id")
        if sid not in records or not item.get("code") or not item.get("reason"):
            raise ValueError("Invalid manual content finding identity/code/reason")
        start, end = item.get("start"), item.get("end")
        text = records[sid]["text"]
        if start is None and end is None:
            literal = text
        elif type(start) is int and type(end) is int and 0 <= start < end <= len(text):
            literal = text[start:end]
        else:
            raise ValueError(f"{sid}: invalid manual finding offset")
        if item.get("text") != literal:
            raise ValueError(f"{sid}: manual finding text does not round-trip")
        findings_by_id.setdefault(sid, []).append({
            "sample_id": sid, "code": item["code"], "reason": item["reason"],
            "start": start, "end": end, "text": literal,
        })
    return findings_by_id


def validate_canonical_annotation(record: dict, converted: dict) -> None:
    """Reject edited canonical labels even when the raw-export QA hash matches."""
    expected_spans = [{key: span[key] for key in ("start", "end", "label", "system")} for span in converted["spans"]]
    if record.get("spans") != expected_spans or record.get("address_system") != converted["address_system"]:
        raise ValueError(f"{record['sample_id']}: canonical annotation differs from the selected raw annotation")


def annotation_fingerprint(record: dict) -> str:
    value = {key: record.get(key) for key in ("sample_id", "text", "spans", "address_system")}
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def load_human_adjudications(path: Path | None, export_paths: dict[str, Path],
                            records: dict[str, dict], attestation: dict) -> dict[str, dict]:
    """Keep explicitly accepted annotations; time conflicts stay excluded from T1."""
    if path is None:
        return {}
    review = json.loads(path.read_text(encoding="utf-8"))
    if review.get("export_sha256") != {name: file_hash(file) for name, file in export_paths.items()}:
        raise ValueError("Human adjudication is stale for these exports")
    if (review.get("reviewer") != attestation["reviewer"] or
            review.get("label_studio_user_id") != attestation["label_studio_user_id"] or
            not review.get("human_authorization_quote") or not review.get("date") or
            not isinstance(review.get("decisions"), list)):
        raise ValueError("Human adjudication requires attested identity, direct authorization and date")
    decisions = {}
    for decision in review["decisions"]:
        sid = decision.get("sample_id")
        codes = decision.get("accepted_finding_codes")
        if (sid not in records or sid in decisions or not decision.get("reason") or
                decision.get("decision") not in {"keep", "keep_as_exception"} or
                decision.get("annotation_sha256") != annotation_fingerprint(records[sid]) or
                not isinstance(codes, list) or len(codes) != len(set(codes)) or
                set(codes) - {"address_span_system_conflict", "period_claim_requires_adjudication"} or
                type(decision.get("exclude_from_t1")) is not bool):
            raise ValueError("Invalid human adjudication identity/fingerprint/decision/reason/code")
        if codes and decision["decision"] != "keep_as_exception":
            raise ValueError("Accepted content findings must be recorded as an exception")
        if "address_span_system_conflict" in codes and not decision["exclude_from_t1"]:
            raise ValueError("A retained time-system conflict must be excluded from T1")
        decisions[sid] = {**decision, "reviewer": review["reviewer"], "date": review["date"],
                          "human_authorization_quote": review["human_authorization_quote"]}
    return decisions


def coverage(records: list[dict], metadata: dict[str, dict]) -> dict:
    labels = Counter(s["label"] for row in records for s in row["spans"])
    systems = Counter(s["system"] for row in records for s in row["spans"])
    source_kinds = Counter()
    for row in records:
        derivation = metadata[row["sample_id"]].get("derivation", "").casefold()
        if derivation.startswith("observed"):
            kind = "observed"
        elif derivation.startswith("derived"):
            kind = "derived"
        elif derivation.startswith(("synthetic", "controlled_synthetic")):
            kind = "synthetic"
        else:
            kind = "unverified_provenance"
        source_kinds[kind] += 1
    return {
        "samples": len(records), "spans": sum(labels.values()),
        "label_support": {label: labels[label] for label in SPAN11_LABELS},
        "span_system": {system: systems[system] for system in ("cu", "moi", "khong_xac_dinh")},
        "t1": {system: sum(row.get("address_system") == system for row in records) for system in (*ADDRESS_SYSTEMS, None)},
        "source_dataset": dict(Counter(metadata[row["sample_id"]].get("source_dataset", "unknown") for row in records)),
        "source_kind": dict(source_kinds),
        "derivation": dict(Counter(metadata[row["sample_id"]].get("derivation", "not_recorded") for row in records)),
        "stratum": dict(Counter(metadata[row["sample_id"]].get("stratum", "not_recorded") for row in records)),
        "noise_type": dict(Counter(metadata[row["sample_id"]].get("noise_type") or metadata[row["sample_id"]].get("LoaiNhieu") or "not_recorded" for row in records)),
        "note": "Source kind comes from the declared queue derivation; a source OSM dataset alone does not make a child observed. Missing noise metadata stays not_recorded.",
    }


def prepare_release(root: Path, review_dir: Path, assignment_path: Path, decisions_path: Path,
                    attestation_path: Path, output_dir: Path, manual_review_path: Path | None = None,
                    adjudications_path: Path | None = None) -> dict:
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite output: {output_dir}")
    converter = importlib.import_module("scripts.17_convert_span_annotation_batch")
    auditor = importlib.import_module("scripts.18_audit_corpus_split")
    annotation_dir = root / "data/interim/annotation/sprint03"
    input_snapshot_path = root / "docs/sprints/sprint_03/s3_04_input_snapshot_v1.json"
    input_snapshot = json.loads(input_snapshot_path.read_text(encoding="utf-8"))
    for relative, entry in input_snapshot["inputs"].items():
        if not (root / relative).is_file() or file_hash(root / relative) != entry["sha256"]:
            raise ValueError(f"Frozen source input drift: {relative}")
    queue01_path, queue02_path = annotation_dir / "annotation_queue_batch01.csv", annotation_dir / "annotation_queue_batch02_train_dev.csv"
    queue01 = converter.read_queue(queue01_path)
    queue02 = converter.read_queue(queue02_path, "train_dev_batch02")
    metadata = {**{sid: row for sid, row in queue01.items() if row["planned_role"] == "pilot_train_pool"}, **queue02}
    if len(metadata) != 300:
        raise ValueError("Expected 300 frozen train/dev queue samples")
    configs = [("pilot", "pilot_qa/pilot_canonical_candidate.jsonl", "pilot_qa/pilot_qa_report.json"),
               ("batch", "batch_qa/canonical_candidate.jsonl", "batch_qa/qa_report.json")]
    canonical, selected, references = [], {}, {}
    for name, canonical_file, report_file in configs:
        export_path = review_dir / f"inputs/{name}_export.json"
        report = json.loads((review_dir / report_file).read_text(encoding="utf-8"))
        if report["status"] != "READY_FOR_HUMAN_REVIEW" or report["issues"]:
            raise ValueError(f"{name}: structural QA has not passed")
        if report["export_sha256"] != file_hash(export_path):
            raise ValueError(f"{name}: QA report is stale for current export")
        canonical.extend(read_jsonl(review_dir / canonical_file))
        tasks = json.loads(export_path.read_text(encoding="utf-8"))
        for task in tasks:
            sid = task["data"]["sample_id"]
            anns = [a for a in task["annotations"] if not a.get("was_cancelled")]
            if len(anns) != 1:
                raise ValueError(f"{sid}: explicit adjudication selection required")
            selected[sid] = (task, anns[0], converter.convert_annotation(anns[0], task["data"]["text"], sid), name)
        for item in (export_path, review_dir / canonical_file, review_dir / report_file):
            references[str(item.relative_to(root))] = file_hash(item)
    by_id = {row["sample_id"]: row for row in canonical}
    if len(canonical) != 300 or len(by_id) != 300 or set(by_id) != set(metadata):
        raise ValueError("Canonical sample IDs differ from frozen 300-sample queue")
    assignments = read_csv(assignment_path, {"sample_id", "split", "source_group", "origin"})
    assignment_by_id = {row["sample_id"]: row for row in assignments}
    if len(assignments) != 300 or len(assignment_by_id) != 300 or set(assignment_by_id) != set(by_id):
        raise ValueError("Frozen assignment IDs differ from canonical records")
    frozen_audit_path = assignment_path.parent / "split_audit_report.json"
    frozen_audit = json.loads(frozen_audit_path.read_text(encoding="utf-8"))
    if file_hash(assignment_path) != frozen_audit["assignment_sha256"]:
        raise ValueError("Frozen split assignment hash changed")
    if file_hash(decisions_path) != frozen_audit["near_duplicate_decisions_sha256"]:
        raise ValueError("Reviewed near-duplicate decisions hash changed")
    for path in (queue01_path, queue02_path):
        if file_hash(path) != frozen_audit["input_sha256"][str(path.relative_to(root))]:
            raise ValueError("Frozen annotation queue hash changed")
    parents_path = assignment_path.parent / "source_parent_manifest.csv"
    if file_hash(parents_path) != frozen_audit["source_parent_manifest_sha256"]:
        raise ValueError("Source parent registry hash changed")
    split_records = {"train": [], "dev": []}
    for row in canonical:
        expected, assignment = metadata[row["sample_id"]], assignment_by_id[row["sample_id"]]
        validate_canonical_annotation(row, selected[row["sample_id"]][2])
        if row["text"] != expected["text"] or row["source_group"] != expected["group_id"] or assignment["source_group"] != row["source_group"]:
            raise ValueError(f"{row['sample_id']}: text/group mismatch")
        if assignment["split"] not in split_records:
            raise ValueError("Invalid frozen split")
        split_records[assignment["split"]].append(row)
    if {name: len(rows) for name, rows in split_records.items()} != {"train": 240, "dev": 60}:
        raise ValueError("Frozen allocation differs from 240 train / 60 dev")
    hold_path = annotation_dir / "test_hold_manifest_v1.json"
    hold = json.loads(hold_path.read_text(encoding="utf-8"))
    frozen_test = {row["sample_id"]: row for row in hold["samples"]}
    test_rows = []
    for sid, row in queue01.items():
        if row["planned_role"] != "frozen_benchmark_test_hold":
            continue
        if (sid not in frozen_test or frozen_test[sid]["group_id"] != row["group_id"] or
                frozen_test[sid]["text_sha256"] != hashlib.sha256(row["text"].encode()).hexdigest()):
            raise ValueError("Frozen test identity changed")
        test_rows.append({"sample_id": sid, "text": row["text"], "source_group": row["group_id"]})
    if len(test_rows) != 100 or set(frozen_test) != {row["sample_id"] for row in test_rows}:
        raise ValueError("Frozen test IDs changed")
    reserved = importlib.import_module("scripts.16_prepare_t0_corpus_batch").get_reserved_benchmark_groups()
    audit = auditor.apply_decisions(auditor.audit_splits(split_records["train"], split_records["dev"], test_rows, reserved), decisions_path)
    if audit["status"] not in {"AUDIT_PASS", "AUDIT_PASS_WITH_HUMAN_NEAR_DUP_REVIEW"}:
        raise ValueError(f"Split audit failed: {audit['status']}")
    # Test records above contain only frozen identity/text for leakage checks,
    # never annotations. They are not written as a gold test split.
    audit.pop("near_duplicates_review_queue")
    audit["scope"] = "train/dev candidate vs frozen test identity; test gold pending"
    attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
    if attestation.get("reviewed_sample_count") != 300 or not attestation.get("reviewer") or not attestation.get("evidence"):
        raise ValueError("Incomplete human review attestation")
    if any(ann.get("completed_by") != attestation.get("label_studio_user_id") for _, ann, _, _ in selected.values()):
        raise ValueError("Annotation author does not match attested Label Studio account ID")
    manual_findings = load_manual_findings(manual_review_path,
        {name: review_dir / f"inputs/{name}_export.json" for name in ("pilot", "batch")}, by_id)
    adjudications = load_human_adjudications(adjudications_path,
        {name: review_dir / f"inputs/{name}_export.json" for name in ("pilot", "batch")}, by_id, attestation)
    findings, log, exceptions = [], [], []
    for sid in sorted(by_id):
        row = by_id[sid]
        task, ann, converted, origin = selected[sid]
        issues = content_findings(row) + manual_findings.get(sid, [])
        if "privacy_review" in converted["review_flags"]:
            issues.append({"sample_id": sid, "code": "privacy_clearance_pending", "reason": "Retained privacy flag needs a specific human clearance decision.", "start": None, "end": None, "text": row["text"]})
        for issue in issues:
            issue.update({"label_studio_task_id": task["id"], "project_id": task.get("project"),
                          "annotation_id": ann["id"], "address_text": row["text"],
                          "split": assignment_by_id[sid]["split"]})
        decision = adjudications.get(sid)
        if decision:
            accepted_codes = set(decision["accepted_finding_codes"])
            if accepted_codes - {item["code"] for item in issues}:
                raise ValueError(f"{sid}: human decision accepts a finding absent from the current review")
            accepted_issues = [item for item in issues if item["code"] in accepted_codes]
            if accepted_issues or decision["exclude_from_t1"]:
                exceptions.append({**decision, "findings": accepted_issues, "split": assignment_by_id[sid]["split"]})
            issues = [item for item in issues if item["code"] not in accepted_codes]
        findings.extend(issues)
        log.append({
            "sample_id": sid, "annotation_id": ann["id"], "label_studio_task_id": task["id"],
            "origin": f"{origin}_v2", "decision": "pending_correction" if issues else decision["decision"] if decision else "keep",
            "reason": "; ".join(i["reason"] for i in issues) if issues else decision["reason"] if decision else "Owner attests review of all 300 samples; no blocking text-rule finding. Existing flags/notes are preserved.",
            "reviewer": attestation["reviewer"], "label_studio_completed_by": ann.get("completed_by"),
            "attestation_date": attestation.get("attestation_date", ""),
            "decision_author": "owner direct adjudication recorded by agent" if decision else "agent text-rule audit; owner review scope attested",
            "export_sha256": file_hash(review_dir / f"inputs/{origin}_export.json"),
            "guideline_version": "s3-span-v1.1", "review_flags": "|".join(converted["review_flags"]),
            "review_note": converted["review_note"], "annotation_modified": False,
            "additional_review_evidence": str(manual_review_path.relative_to(root)) if manual_review_path else "",
            "human_adjudication_evidence": str(adjudications_path.relative_to(root)) if decision else "",
            "excluded_from_t1": decision["exclude_from_t1"] if decision else False,
        })
    blocked_ids = {item["sample_id"] for item in findings}
    eligible = {name: [row for row in rows if row["sample_id"] not in blocked_ids] for name, rows in split_records.items()}
    audit["candidate_subset_sample_counts"] = {name: len(rows) for name, rows in eligible.items()}
    audit["quarantined_sample_ids"] = sorted(blocked_ids)
    audit["subset_audit_policy"] = "The candidate is a subset of the audited frozen 300 identities. Removing samples cannot introduce cross-split leakage; all nominated pairs in the superset are adjudicated. Labels do not affect this identity audit."
    output_dir.mkdir(parents=True)
    for name, rows in eligible.items():
        write_jsonl(output_dir / f"{name}.jsonl", sorted(rows, key=lambda r: r["sample_id"]))
    write_jsonl(output_dir / "dev_input.jsonl", [{"sample_id": row["sample_id"], "text": row["text"]} for row in sorted(eligible["dev"], key=lambda r: r["sample_id"])])
    write_jsonl(output_dir / "quarantine.jsonl", [by_id[sid] for sid in sorted(blocked_ids)])
    write_json(output_dir / "content_review_items.json", findings)
    write_json(output_dir / "adjudicated_content_exceptions.json", exceptions)
    with (output_dir / "label_studio_correction_queue.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("sample_id", "label_studio_task_id", "project_id", "annotation_id", "split", "code", "start", "end", "text", "reason", "address_text"))
        writer.writeheader()
        writer.writerows(findings)
    with (output_dir / "decision_log_v2.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(log[0]))
        writer.writeheader()
        writer.writerows(log)
    write_json(output_dir / "split_audit.json", audit)
    excluded_t1_ids = sorted(sid for sid, decision in adjudications.items() if decision["exclude_from_t1"])
    coverage_report = {name: coverage(rows, metadata) for name, rows in eligible.items()}
    for name, rows in eligible.items():
        coverage_report[name]["t1_declared_exception_excluded_ids"] = sorted(row["sample_id"] for row in rows if row["sample_id"] in excluded_t1_ids)
        coverage_report[name]["t1_eligible_samples"] = sum(row.get("address_system") is not None and row["sample_id"] not in excluded_t1_ids for row in rows)
    write_json(output_dir / "coverage.json", coverage_report)
    approval = {"status": "PENDING_CONTENT_CORRECTIONS" if blocked_ids else "HUMAN_REVIEW_ATTESTED_WITH_EXCEPTIONS" if exceptions else "HUMAN_REVIEW_ATTESTED",
                "attestation": attestation, "unresolved_sample_ids": sorted(blocked_ids),
                "specific_agent_findings_are_not_human_adjudications": True,
                "human_adjudications": list(adjudications.values()),
                "inter_annotator_agreement": "NOT_MEASURED", "schema_version": "s3-span-v1.1"}
    write_json(output_dir / "approval_record.json", approval)
    if manual_review_path:
        references[str(manual_review_path.relative_to(root))] = file_hash(manual_review_path)
    if adjudications_path:
        references[str(adjudications_path.relative_to(root))] = file_hash(adjudications_path)
    for path in (assignment_path, decisions_path, parents_path, frozen_audit_path, hold_path,
                 attestation_path, input_snapshot_path, root / "configs/label_studio_span11.xml", root / "docs/sprints/sprint_03/span_11_annotation_guideline.md", queue01_path, queue02_path):
        references[str(path.relative_to(root))] = file_hash(path)
    manifest = {
        "version": "corpus_train_dev_v2_candidate", "status": "BLOCKED_CONTENT_REVIEW" if blocked_ids else "TRAIN_DEV_APPROVED_TEST_PENDING",
        "split": "train_dev", "schema_version": "s3-span-v1.1", "test_status": "TEST_PENDING",
        "human_review_attested": 300, "expected_sample_counts": {"train": 240, "dev": 60},
        "sample_counts": {name: len(rows) for name, rows in eligible.items()},
        "quarantined_sample_count": len(blocked_ids), "quarantined_sample_ids": sorted(blocked_ids),
        "quality_status": "APPROVED_WITH_DECLARED_EXCEPTIONS" if exceptions and not blocked_ids else "CONTENT_REVIEW_PENDING" if blocked_ids else "APPROVED_WITHOUT_KNOWN_BLOCKING_FINDINGS",
        "adjudicated_exception_count": len(exceptions), "evaluation_exclusions": {"t1": excluded_t1_ids},
        "t1_training_policy": "Mask evaluation_exclusions.t1 IDs from T1 training and system-consistency loss; original annotations remain unchanged. T0 retains all approved spans.",
        "near_duplicate_decisions_count": len(auditor.read_queue_for_decisions(decisions_path)),
        "input_sha256": references, "output_sha256": {path.name: file_hash(path) for path in output_dir.iterdir() if path.is_file()},
        "annotation_versions": ["pilot_v2", "batch_v2"],
        "code_sha256": {name: file_hash(root / name) for name in (
            "src/data/annotation_release.py", "scripts/22_review_and_package_train_dev.py",
            "scripts/25_publish_train_dev.py",
            "scripts/11_convert_label_studio_pilot.py", "scripts/17_convert_span_annotation_batch.py",
            "scripts/18_audit_corpus_split.py")},
        "inter_annotator_agreement": "NOT_MEASURED",
        "inference_permission": "No real dev run until status TRAIN_DEV_APPROVED_TEST_PENDING; input must be sample_id/text only.",
    }
    write_json(output_dir / "manifest.json", manifest)
    return manifest


def publish_release(root: Path, candidate_dir: Path, output_dir: Path) -> dict:
    """Publish an approved, hash-verified package without changing annotations."""
    root, candidate_dir, output_dir = root.resolve(), candidate_dir.resolve(), output_dir.resolve()
    interim_root = root / "data/interim/annotation/sprint03"
    processed_root = root / "data/processed/annotation/sprint03"
    if not candidate_dir.is_relative_to(interim_root):
        raise ValueError("Candidate must be inside Sprint 3 annotation interim data")
    if not output_dir.is_relative_to(processed_root) or output_dir == processed_root:
        raise ValueError("Release must be a version directory inside Sprint 3 processed annotation data")
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite release: {output_dir}")
    manifest_path = candidate_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    approved_status = "TRAIN_DEV_APPROVED_TEST_PENDING"
    if manifest.get("status") != approved_status:
        raise ValueError(f"Publication blocked by candidate status: {manifest.get('status')}")
    expected_counts = {"train": 240, "dev": 60}
    if (manifest.get("sample_counts") != expected_counts or
            manifest.get("expected_sample_counts") != expected_counts or
            manifest.get("quarantined_sample_count") != 0 or manifest.get("quarantined_sample_ids") or
            manifest.get("human_review_attested") != 300 or manifest.get("test_status") != "TEST_PENDING"):
        raise ValueError("Publication requires all 300 reviewed train/dev samples and no quarantine")
    required_outputs = {"train.jsonl", "dev.jsonl", "dev_input.jsonl", "quarantine.jsonl",
                        "content_review_items.json", "label_studio_correction_queue.csv",
                        "decision_log_v2.csv", "split_audit.json", "coverage.json", "approval_record.json",
                        "adjudicated_content_exceptions.json"}
    output_hashes = manifest.get("output_sha256", {})
    if set(output_hashes) != required_outputs:
        raise ValueError("Candidate output inventory differs from the train/dev release contract")
    for name, expected_hash in output_hashes.items():
        path = candidate_dir / name
        if not path.is_file() or file_hash(path) != expected_hash:
            raise ValueError(f"Candidate artifact hash changed: {name}")
    for section in ("input_sha256", "code_sha256"):
        if not manifest.get(section):
            raise ValueError(f"Candidate manifest is missing {section}")
        for relative, expected_hash in manifest[section].items():
            path = (root / relative).resolve()
            if not path.is_relative_to(root) or not path.is_file() or file_hash(path) != expected_hash:
                raise ValueError(f"Candidate {section} drift: {relative}")
    approval = json.loads((candidate_dir / "approval_record.json").read_text(encoding="utf-8"))
    if (approval.get("status") not in {"HUMAN_REVIEW_ATTESTED", "HUMAN_REVIEW_ATTESTED_WITH_EXCEPTIONS"} or approval.get("unresolved_sample_ids") or
            approval.get("attestation", {}).get("reviewed_sample_count") != 300 or
            not approval.get("attestation", {}).get("reviewer")):
        raise ValueError("Human review approval is incomplete")
    audit = json.loads((candidate_dir / "split_audit.json").read_text(encoding="utf-8"))
    if audit.get("status") not in {"AUDIT_PASS", "AUDIT_PASS_WITH_HUMAN_NEAR_DUP_REVIEW"}:
        raise ValueError("Split audit has not passed")
    if (read_jsonl(candidate_dir / "quarantine.jsonl") or
            json.loads((candidate_dir / "content_review_items.json").read_text(encoding="utf-8"))):
        raise ValueError("Candidate still contains unresolved content findings")
    decisions = read_csv(candidate_dir / "decision_log_v2.csv", {"sample_id", "decision", "reviewer", "reason"})
    split_rows = {name: read_jsonl(candidate_dir / f"{name}.jsonl") for name in expected_counts}
    samples = split_rows["train"] + split_rows["dev"]
    ids = {row["sample_id"] for row in samples}
    if (len(samples) != 300 or len(ids) != 300 or
            any(len(split_rows[name]) != count for name, count in expected_counts.items()) or
            len(decisions) != 300 or {row["sample_id"] for row in decisions} != ids or
            any(row["decision"] not in {"keep", "keep_as_exception"} or not row["reviewer"] or not row["reason"] for row in decisions)):
        raise ValueError("Release sample identity/count/decision log mismatch")
    if ({row["source_group"] for row in split_rows["train"]} &
            {row["source_group"] for row in split_rows["dev"]}):
        raise ValueError("Train and dev contain a shared source group")
    expected_input = [{"sample_id": row["sample_id"], "text": row["text"]} for row in split_rows["dev"]]
    if read_jsonl(candidate_dir / "dev_input.jsonl") != expected_input:
        raise ValueError("Dev inference input differs from the approved text-only dev split")
    exceptions = json.loads((candidate_dir / "adjudicated_content_exceptions.json").read_text(encoding="utf-8"))
    exception_by_id = {item["sample_id"]: item for item in exceptions}
    if (len(exception_by_id) != len(exceptions) or set(exception_by_id) - ids or
            manifest.get("adjudicated_exception_count", 0) != len(exceptions)):
        raise ValueError("Adjudication exception identity/count mismatch")
    expected_exclusions = sorted(item["sample_id"] for item in exceptions if item["exclude_from_t1"])
    if manifest.get("evaluation_exclusions", {"t1": []}) != {"t1": expected_exclusions}:
        raise ValueError("T1 exclusion policy differs from the adjudicated exceptions")
    approval_decisions = {item["sample_id"]: item for item in approval.get("human_adjudications", [])}
    for row in samples:
        exception = exception_by_id.get(row["sample_id"])
        accepted_codes = set(exception["accepted_finding_codes"]) if exception else set()
        if exception:
            authorized = approval_decisions.get(row["sample_id"], {})
            if (exception["annotation_sha256"] != annotation_fingerprint(row) or
                    not exception.get("human_authorization_quote") or
                    authorized.get("accepted_finding_codes") != exception["accepted_finding_codes"] or
                    authorized.get("exclude_from_t1") != exception["exclude_from_t1"] or
                    ("address_span_system_conflict" in accepted_codes and not exception["exclude_from_t1"])):
                raise ValueError("Retained exception lacks matching human authorization/T1 exclusion")
        if any(item["code"] not in accepted_codes for item in content_findings(row)):
            raise ValueError("Unadjudicated text-rule content findings remain in the release")
    # Copy approved bytes only; publication never supplies or repairs labels.
    output_dir.mkdir(parents=True)
    for name in sorted(required_outputs):
        shutil.copyfile(candidate_dir / name, output_dir / name)
    published = {**manifest, "version": output_dir.name,
                 "release_kind": "approved_train_dev_only",
                 "candidate_manifest": {"path": str(manifest_path.relative_to(root)), "sha256": file_hash(manifest_path)},
                 "release_directory": str(output_dir.relative_to(root)),
                 "publication_policy": "Approved candidate bytes preserved; no test gold included; no output overwrite.",
                 "output_sha256": {name: file_hash(output_dir / name) for name in sorted(required_outputs)}}
    write_json(output_dir / "manifest.json", published)
    return published
