"""Dated official references, exact reconciliation and immutable dual-snapshot release."""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import csv
import json
from pathlib import Path
import shutil
import urllib.request

from src.data.administrative_code_verifier import TemporalGazetteerEvidence, canonical_name
from src.data.nso_soap_catalog import (
    SERVICE_URL, OPERATIONS, build_reference, parse_table_rows, post_soap,
    province_counts, save_response, sha256_bytes, validate_rows,
)
from src.evaluation.dev_runner import ROOT, file_hash, read_jsonl, write_json, write_jsonl

OLD_DATE = "2025-06-30"
NEW_DATE = "2025-07-01"
COMMUNITY_URL = "https://raw.githubusercontent.com/thanglequoc/vietnamese-provinces-database/v2.4.1/json/vn_only_simplified_json_generated_data_vn_units_minified.json"
COMMUNITY_LICENSE = "https://raw.githubusercontent.com/thanglequoc/vietnamese-provinces-database/v2.4.1/LICENSE"


def reference_key(row):
    return (row["system"], row["level"],
            canonical_name(row["official_name"] if row["level"] == "province" else row["province_name"]),
            canonical_name(row["official_name"] if row["level"] == "district" else row["district_name"]),
            canonical_name(row["official_name"] if row["level"] == "ward" else ""))


def reconcile(gazetteer, reference):
    index = defaultdict(list)
    for row in reference:
        if row["validation_status"] == "PARENT_CODE_LINK_PASS":
            index[reference_key(row)].append(row)
    decisions = []
    for entity in gazetteer.entities:
        if entity["system"] != "cu":
            continue
        matches = index[gazetteer.full_key(entity)]
        code = entity["candidate_code"] or entity["official_code"]
        unique = len(matches) == 1
        verified = unique and (not code or code == matches[0]["official_code"])
        status = "VERIFIED_EXACT_PRIMARY_SNAPSHOT" if verified else (
            "CODE_CONFLICT" if unique else "AMBIGUOUS_REFERENCE_KEY" if matches else "NO_REFERENCE_AS_OF")
        decisions.append({"entity_id": entity["entity_id"], "level": entity["level"], "system": "cu",
                          "full_key": list(gazetteer.full_key(entity)), "candidate_code": code or None,
                          "status": status, "verified_code": matches[0]["official_code"] if verified else None,
                          "as_of_date": OLD_DATE, "reason": status,
                          "evidence": matches,
                          "policy": "exact NFC/whitespace/case key and parent; no fuzzy promotion"})
    return decisions


def fetch_catalog(output_dir: Path, parent: Path, cached_dir: Path | None = None):
    if output_dir.exists():
        raise FileExistsError(output_dir)
    output_dir.mkdir(parents=True)
    # Inventory is written before any network transfer; no dependency install.
    write_json(output_dir / "download_inventory.json", {
        "created_at": datetime.now(timezone.utc).isoformat(), "package_install": [],
        "sources": [SERVICE_URL, COMMUNITY_URL, COMMUNITY_LICENSE],
        "estimated_bytes": 16000000, "license": "NSO public terms not located; community repository MIT",
        "target": output_dir.relative_to(ROOT).as_posix(), "purpose": "U1 exact dated code verification"})
    raw = output_dir / "responses"
    entries, responses = [], {}
    for operation, spec in OPERATIONS.items():
        params = {"DenNgay": "30/06/2025"}
        cached_manifest = json.loads((cached_dir / "download_manifest.json").read_text()) if cached_dir else {}
        cached = next((item for item in cached_manifest.get("responses", []) if item["operation"] == operation and item["query"] == params), None)
        if cached:
            raw.mkdir(parents=True, exist_ok=True)
            for field, digest_field in (("response_file", "sha256"), ("request_file", "request_sha256")):
                source = cached_dir / "responses" / cached[field]
                if file_hash(source) != cached[digest_field]:
                    raise ValueError("CACHED_RESPONSE_HASH_MISMATCH")
                shutil.copy2(source, raw / cached[field])
            entry = dict(cached, reused_from=cached_dir.relative_to(ROOT).as_posix())
            payload = (raw / entry["response_file"]).read_bytes()
        else:
            fetched = post_soap(operation, params)
            entry = save_response(raw, "old_" + spec["level"], operation, params, fetched, "national")
            payload = fetched["response"]
        entries.append(entry)
        write_json(output_dir / "download_manifest.json", {"responses": entries})
        rows = parse_table_rows(payload, operation)
        validation = validate_rows(rows, operation)
        write_json(output_dir / ("old_" + spec["level"] + "_validation.json"), validation)
        if validation["status"] != "PASS":
            raise ValueError("INVALID_OFFICIAL_RESPONSE:" + json.dumps(validation))
        responses[spec["level"]] = (entry, rows)
        print(json.dumps({"download": spec["level"], "rows": len(rows)}), flush=True)
    reference, validation = build_reference(responses, OLD_DATE, "cu")
    write_json(output_dir / "reference_validation.json", validation)
    if validation["status"] == "FAIL":
        raise ValueError("REFERENCE_PARENT_VALIDATION_FAILED")
    write_jsonl(output_dir / "reference_old.jsonl", reference)
    with (output_dir / "reference_old.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(reference[0]))
        writer.writeheader()
        writer.writerows(reference)
    # A date control uses a named province outside the corpus, not test samples.
    params = {"DenNgay": "01/07/2025", "Tinh": "01"}
    fetched = post_soap("DanhMucPhuongXa", params)
    entry = save_response(raw, "new_hanoi_ward_control", "DanhMucPhuongXa", params, fetched, "province_code_01")
    entries.append(entry)
    write_json(output_dir / "download_manifest.json", {"responses": entries})
    new_rows = parse_table_rows(fetched["response"], "DanhMucPhuongXa")
    # New catalogue repeats the province in legacy district columns. This
    # control checks province/ward codes only; it creates no district entity.
    control_rows = [{key: value for key, value in row.items() if key not in ("MaQuanHuyen", "TenQuanHuyen")} for row in new_rows]
    if validate_rows(control_rows, "DanhMucPhuongXa")["status"] != "PASS":
        raise ValueError("DATE_CONTROL_INVALID")
    old_hanoi = [row for row in reference if row["level"] == "ward" and row["province_code"] == "01"]
    control = {"old_count": len(old_hanoi), "new_count": len(new_rows),
               "new_legacy_district_columns": "retained in XML, excluded from two-level date-control validation",
               "old_codes": sorted(row["official_code"] for row in old_hanoi),
               "new_codes": sorted(row["MaPhuongXa"] for row in new_rows)}
    control["status"] = "PASS_DATE_CHANGES_CATALOGUE" if control["old_codes"] != control["new_codes"] else "BLOCKED_IDENTICAL_DATE_CONTROL"
    write_json(output_dir / "date_control.json", control)
    if control["status"].startswith("BLOCKED"):
        raise ValueError(control["status"])
    community_files = {}
    for name, url in (("community_v2.4.1.json", COMMUNITY_URL), ("community_LICENSE", COMMUNITY_LICENSE)):
        with urllib.request.urlopen(url, timeout=30) as response:
            payload = response.read(16000001)
            if len(payload) > 16000000:
                raise ValueError("COMMUNITY_RESPONSE_TOO_LARGE")
        (output_dir / name).write_bytes(payload)
        community_files[name] = {"url": url, "sha256": sha256_bytes(payload), "bytes": len(payload), "tag": "v2.4.1"}
    community = json.loads((output_dir / "community_v2.4.1.json").read_text(encoding="utf-8"))
    community_reference = []
    for province in community:
        pn = province["FullName"]
        community_reference.append(("cu", "province", canonical_name(pn), "", "", province["Code"]))
        for district in province.get("District") or []:
            dn = district["FullName"]
            community_reference.append(("cu", "district", canonical_name(pn), canonical_name(dn), "", district["Code"]))
            for ward in district.get("Ward") or []:
                community_reference.append(("cu", "ward", canonical_name(pn), canonical_name(dn), canonical_name(ward["FullName"]), ward["Code"]))
    official_set = {reference_key(row) + (row["official_code"],) for row in reference}
    community_set = set(community_reference)
    write_json(output_dir / "nso_community_diff.json", {
        "nso_counts": dict(Counter(row["level"] for row in reference)),
        "community_counts": dict(Counter(row[1] for row in community_reference)),
        "exact_full_key_code_intersection": len(official_set & community_set),
        "official_only": sorted(official_set - community_set), "community_only": sorted(community_set - official_set),
        "policy": "differences are evidence gaps; no inferred retirement, alias or extra source row"})
    gazetteer = TemporalGazetteerEvidence(parent)
    decisions = reconcile(gazetteer, reference)
    write_jsonl(output_dir / "code_decisions.jsonl", decisions)
    write_jsonl(output_dir / "unresolved.jsonl", [row for row in decisions if not row["verified_code"]])
    report = {"source": SERVICE_URL, "as_of": OLD_DATE, "reference_counts": validation["counts"],
              "date_control": {key: control[key] for key in ("old_count", "new_count", "status")},
              "decision_counts": dict(Counter(row["status"] for row in decisions)),
              "verified_by_level": dict(Counter(row["level"] for row in decisions if row["verified_code"])),
              "unresolved_by_level": dict(Counter(row["level"] for row in decisions if not row["verified_code"])),
              "province_ward_counts": province_counts(reference, "ward"),
              "parent_link_gap_rows": len(validation["parent_link_issues"]),
              "parent_manifest_sha256": file_hash(parent / "manifest.json"),
              "status": "PARTIAL_EXACT_OFFICIAL_REFERENCE", "test100": "NOT_READ_NOT_USED"}
    write_json(output_dir / "reconciliation_report.json", report)
    write_json(output_dir / "download_manifest.json", {"responses": entries, "community": community_files})
    write_json(output_dir / "reference_manifest.json", {
        "source_url": SERVICE_URL, "authority_status": "OFFICIAL_PRIMARY_SOURCE",
        "as_of_date": OLD_DATE, "snapshot_only": True, "legal_interval": "UNKNOWN",
        "license_status": "PUBLIC_PORTAL_TERMS_NOT_LOCATED", "validation": validation,
        "reference_sha256": file_hash(output_dir / "reference_old.jsonl"),
        "download_manifest_sha256": file_hash(output_dir / "download_manifest.json")})
    return report


def publish_dual(parent: Path, evidence_dir: Path, output_dir: Path):
    if output_dir.exists() or output_dir.with_name(output_dir.name + ".staging").exists():
        raise FileExistsError(output_dir)
    gaz = TemporalGazetteerEvidence(parent)
    report = json.loads((evidence_dir / "reconciliation_report.json").read_text())
    if report["parent_manifest_sha256"] != file_hash(parent / "manifest.json"):
        raise ValueError("PARENT_MANIFEST_MISMATCH")
    reference_manifest = json.loads((evidence_dir / "reference_manifest.json").read_text())
    if reference_manifest["reference_sha256"] != file_hash(evidence_dir / "reference_old.jsonl"):
        raise ValueError("REFERENCE_HASH_MISMATCH")
    downloads = json.loads((evidence_dir / "download_manifest.json").read_text())
    rebuilt_responses = {}
    for entry in downloads["responses"]:
        if entry["sha256"] != file_hash(evidence_dir / "responses" / entry["response_file"]):
            raise ValueError("RAW_REFERENCE_HASH_MISMATCH")
        if entry["query"] == {"DenNgay": "30/06/2025"}:
            operation = entry["operation"]
            if entry["source_url"] != SERVICE_URL or operation not in OPERATIONS:
                raise ValueError("REFERENCE_SOURCE_SCOPE_MISMATCH")
            rows = parse_table_rows((evidence_dir / "responses" / entry["response_file"]).read_bytes(), operation)
            if validate_rows(rows, operation)["status"] != "PASS":
                raise ValueError("INVALID_RAW_REFERENCE")
            rebuilt_responses[OPERATIONS[operation]["level"]] = (entry, rows)
    if set(rebuilt_responses) != {"province", "district", "ward"}:
        raise ValueError("REFERENCE_RESPONSE_SET_INCOMPLETE")
    rebuilt_reference, rebuilt_validation = build_reference(rebuilt_responses, OLD_DATE, "cu")
    if rebuilt_validation["status"] == "FAIL" or rebuilt_reference != read_jsonl(evidence_dir / "reference_old.jsonl"):
        raise ValueError("REFERENCE_NOT_REPRODUCIBLE_FROM_RAW_XML")
    # Recompute decisions; never trust an editable CSV as promotion authority.
    decisions = reconcile(gaz, rebuilt_reference)
    confirmed = {row["entity_id"]: row for row in decisions if row["verified_code"]}
    staging = output_dir.with_name(output_dir.name + ".staging")
    shutil.copytree(parent, staging)
    entities = [dict(row) for row in gaz.entities]
    old_evidence = []
    for entity in entities:
        decision = confirmed.get(entity["entity_id"])
        if not decision:
            continue
        source = decision["evidence"][0]
        entity.update(official_code=decision["verified_code"], code_status="verified_primary_source_snapshot",
                      status="verified_official_source_snapshot", source_id=source["source_id"], source_hash=source["source_hash"])
        old_evidence.append({"entity_id": entity["entity_id"], "system": "cu", "level": entity["level"],
                            "province": decision["full_key"][2], "district": decision["full_key"][3], "ward": decision["full_key"][4],
                            "code": decision["verified_code"], "official_province_name": source["province_name"],
                            "official_ward_name": source["official_name"] if entity["level"] == "ward" else "",
                            "name_alignment": "EXACT_FULL_KEY_PARENT_CODE", "source_id": source["source_id"],
                            "source_sha256": source["source_hash"], "source_locator": source["source_locator"],
                            "source_as_of": OLD_DATE, "source_url": SERVICE_URL})
    with (staging / "entities.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(entities[0]))
        writer.writeheader()
        writer.writerows(entities)
    with (parent / "code_evidence.csv").open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, evidence = reader.fieldnames, list(reader)
    with (staging / "code_evidence.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(evidence + old_evidence)
    coverage = {"verified_by_system_level": dict(Counter(row["system"] + ":" + row["level"] for row in evidence + old_evidence)),
                "old_unresolved": report["unresolved_by_level"], "graph_counts": gaz.manifest["counts"],
                "snapshot_dates_by_system": {"cu": OLD_DATE, "moi": NEW_DATE}, "license_status": "PUBLIC_PORTAL_TERMS_NOT_LOCATED"}
    write_json(staging / "coverage_report.json", coverage)
    write_json(staging / "old_code_reference_manifest.json", reference_manifest)
    write_json(staging / "release_diff.json", {"newly_verified_old": len(old_evidence), "counts_by_level": report["verified_by_level"],
                                               "entities_ids_names_parents_unchanged": True,
                                               "graph_alias_files_unchanged": ["edges.csv", "non_atomic_transitions.csv", "aliases.csv"],
                                               "source_evidence_dir": evidence_dir.relative_to(ROOT).as_posix()})
    # Remove inherited examples: they describe the parent's single-day policy.
    write_json(staging / "lookup_examples.json", {"policy": "see script 41 lookup; exact dates only", "examples": []})
    manifest = dict(gaz.manifest)
    manifest.update(version="s3-gazetteer-v4-nso-dual-snapshot-partial", parent_version=gaz.manifest["version"],
                    parent_manifest_sha256=file_hash(parent / "manifest.json"), snapshot_date=None,
                    snapshot_dates_by_system={"cu": OLD_DATE, "moi": NEW_DATE},
                    release_status="PARTIAL_OLD_CODES_UNVERIFIED",
                    old_code_reference={"verified": len(old_evidence), "counts": report["verified_by_level"],
                                        "reference_manifest_sha256": file_hash(evidence_dir / "reference_manifest.json")},
                    release_module_sha256=file_hash(Path(__file__)))
    manifest["counts"] = dict(manifest["counts"], official_code_evidence_rows=len(evidence) + len(old_evidence))
    manifest["limitations"] = [item for item in manifest["limitations"] if "0 verified official old" not in item and "Old province/district/ward codes remain" not in item and "rejects dates outside that exact" not in item]
    manifest["limitations"] += ["Old codes verified only on exact official full key/code/parent at 2025-06-30; unresolved codes remain unverified.",
                                 "Two proven snapshots only: cu 2025-06-30 and moi 2025-07-01; no legal start date inferred."]
    manifest["output_sha256"] = {path.name: file_hash(path) for path in staging.iterdir() if path.is_file() and path.name != "manifest.json"}
    write_json(staging / "manifest.json", manifest)
    DualSnapshotGazetteer(staging)
    staging.rename(output_dir)
    return {"package": output_dir.relative_to(ROOT).as_posix(), "verified_old": len(old_evidence), "coverage": coverage}


class DualSnapshotGazetteer(TemporalGazetteerEvidence):
    def __init__(self, package_dir):
        super().__init__(package_dir)
        self.snapshots = self.manifest.get("snapshot_dates_by_system")
        if self.snapshots != {"cu": OLD_DATE, "moi": NEW_DATE}:
            raise ValueError("DUAL_SNAPSHOT_MANIFEST_REQUIRED")
        with (package_dir / "code_evidence.csv").open(encoding="utf-8-sig", newline="") as stream:
            self.evidence = {row["entity_id"]: row for row in csv.DictReader(stream)}
        for entity in self.entities:
            if entity["code_status"] == "verified_primary_source_snapshot":
                evidence = self.evidence.get(entity["entity_id"])
                if not evidence or evidence["code"] != entity["official_code"] or evidence["source_as_of"] != self.snapshots[entity["system"]]:
                    raise ValueError("CODE_EVIDENCE_SCOPE_MISMATCH")

    def lookup(self, name, level, reference_date, parent_context=None, system=None):
        from datetime import date
        date.fromisoformat(reference_date)
        if system is not None and system not in self.snapshots:
            raise ValueError("INVALID_SYSTEM")
        if level not in ("province", "district", "ward"):
            raise ValueError("INVALID_ADMIN_LEVEL")
        allowed = {key for key, point in self.snapshots.items() if point == reference_date and (not system or key == system)}
        if not allowed:
            return {"status": "OUT_OF_SNAPSHOT_SCOPE", "candidates": [], "reject_reason": "no evidence at requested system/date", "snapshot_dates_by_system": self.snapshots}
        context = {key: canonical_name(value) for key, value in (parent_context or {}).items()}
        if set(context) - {"province", "district"}:
            raise ValueError("INVALID_PARENT_CONTEXT")
        candidates = []
        for entity in self.entities:
            if entity["system"] not in allowed or entity["level"] != level or canonical_name(entity["canonical_name"]) != canonical_name(name):
                continue
            key = self.full_key(entity)
            if any(context.get(field) and context[field] != key[index] for field, index in (("province", 2), ("district", 3))):
                continue
            source = self.evidence.get(entity["entity_id"])
            verified = entity["code_status"] == "verified_primary_source_snapshot"
            candidates.append(dict(entity, official_code=entity["official_code"] if verified else None,
                                   evidence=source if verified else None, verified_as_of=reference_date if verified else None,
                                   legal_valid_from="UNKNOWN", full_key=list(key)))
        status = "NO_MATCH" if not candidates else "AMBIGUOUS" if len(candidates) > 1 else "VERIFIED" if candidates[0]["evidence"] else "CANDIDATE"
        return {"status": status, "candidates": candidates, "reject_reason": None if status == "VERIFIED" else status,
                "policy": "exact canonical/level/parent/system/date; all candidates retained"}
