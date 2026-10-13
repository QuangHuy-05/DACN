"""Exact administrative-code evidence, date-aware lookup and honest v2 gaps."""

from collections import Counter, defaultdict
import csv
from datetime import date, timedelta
import json
from pathlib import Path
import unicodedata
from urllib.parse import urlparse

from src.evaluation.dev_runner import ROOT, file_hash, write_json, write_jsonl

REFERENCE_COLUMNS = {"province", "district", "ward", "level", "system", "code", "valid_from", "valid_to", "source_id", "source_locator"}


def canonical_name(value: str) -> str:
    # Preserve diacritics and unit types; no fuzzy match or invented alias.
    return " ".join(unicodedata.normalize("NFC", value).split())


def read_csv(path: Path, required: set[str]) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not required <= set(reader.fieldnames or []):
            raise ValueError("REFERENCE_COLUMNS_MISSING: " + str(sorted(required - set(reader.fieldnames or []))))
        return list(reader)


def interval_contains(start: str, end_exclusive: str, reference_date: str) -> bool:
    point = date.fromisoformat(reference_date)
    return (not start or date.fromisoformat(start) <= point) and (not end_exclusive or point < date.fromisoformat(end_exclusive))


class TemporalGazetteerEvidence:
    def __init__(self, package_dir: Path):
        self.directory = package_dir
        self.manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
        for name, digest in self.manifest["output_sha256"].items():
            if file_hash(package_dir / name) != digest:
                raise ValueError("FROZEN_GAZETTEER_HASH_MISMATCH:" + name)
        self.entities = read_csv(package_dir / "entities.csv", {"entity_id", "level", "system", "canonical_name", "parent_id", "code_status", "candidate_code", "official_code", "valid_from", "valid_to"})
        self.by_id = {row["entity_id"]: row for row in self.entities}
        if len(self.by_id) != len(self.entities):
            raise ValueError("DUPLICATE_ENTITY_ID")
        if any(row["parent_id"] and row["parent_id"] not in self.by_id for row in self.entities):
            raise ValueError("MISSING_PARENT_ID")
        self.edges = read_csv(package_dir / "edges.csv", {"old_entity_id", "new_entity_id", "relation"})
        self.non_atomic = read_csv(package_dir / "non_atomic_transitions.csv", {"old_entity_id", "new_entity_id", "relation"})

    def full_key(self, row: dict) -> tuple:
        names, current, visited = {}, row, set()
        while current:
            if current["entity_id"] in visited:
                raise ValueError("ADMIN_PARENT_CYCLE")
            visited.add(current["entity_id"])
            names[current["level"]] = canonical_name(current["canonical_name"])
            current = self.by_id.get(current["parent_id"])
        return row["system"], row["level"], names.get("province", ""), names.get("district", ""), names.get("ward", "")

    def half_open_interval(self, row: dict) -> tuple[str, str]:
        end = row["valid_to"]
        # Frozen s3_v2 uses inclusive valid_to. Translate in memory, preserve source bytes.
        if end:
            end = (date.fromisoformat(end) + timedelta(days=1)).isoformat()
        return row["valid_from"], end

    def lookup(self, name: str, level: str, reference_date: str, parent_context=None) -> dict:
        date.fromisoformat(reference_date)
        # A one-day official export proves a state of the world only for that
        # snapshot. Do not silently treat it as an open-ended historical table.
        if self.manifest.get("snapshot_only") and reference_date != self.manifest.get("snapshot_date"):
            return {"status": "OUT_OF_SNAPSHOT_SCOPE", "candidates": [],
                    "reject_reason": "official reference is a one-day snapshot; request its exact as-of date",
                    "snapshot_date": self.manifest.get("snapshot_date"), "requested_date": reference_date}
        if level not in ("province", "district", "ward"):
            raise ValueError("INVALID_ADMIN_LEVEL")
        context = {key: canonical_name(value) for key, value in (parent_context or {}).items()}
        if set(context) - {"province", "district"}:
            raise ValueError("INVALID_PARENT_CONTEXT")
        candidates = []
        for row in self.entities:
            if row["level"] != level or canonical_name(row["canonical_name"]) != canonical_name(name):
                continue
            system, _, province, district, _ = self.full_key(row)
            if any(context.get(key) and context[key] != value for key, value in (("province", province), ("district", district))):
                continue
            start, end = self.half_open_interval(row)
            if not interval_contains(start, end, reference_date):
                continue
            snapshot_verified = row["code_status"] == "verified_primary_source_snapshot"
            candidates.append({"entity_id": row["entity_id"], "level": level, "system": system,
                "canonical_name": row["canonical_name"], "parent_id": row["parent_id"], "full_key": [system, level, province, district, self.full_key(row)[-1]],
                "official_code": row["official_code"] or None, "candidate_code": row["candidate_code"] or None,
                "code_status": row["code_status"], "source_id": row["source_id"], "source_hash": row["source_hash"],
                "valid_from": start or None, "valid_to_exclusive": end or None,
                "evidence_scope": "official_primary_source_snapshot" if snapshot_verified else "repository_source_only_not_external_authority_verified",
                "validity_warning": "START_UNKNOWN" if not start else None})
        status = "NO_MATCH" if not candidates else "AMBIGUOUS" if len(candidates) > 1 else "VERIFIED" if candidates[0]["code_status"] == "verified_primary_source_snapshot" else "CANDIDATE"
        reject_reason = "no exact name/level/parent/date match" if not candidates else "multiple identities; do not choose first" if len(candidates) > 1 else None if status == "VERIFIED" else "external code authority still unverified"
        return {"status": status, "candidates": candidates,
                "reject_reason": reject_reason,
                "interval_policy": "half_open; s3_v2 inclusive end translated +1 day",
                "alias_policy": "exact canonical only; existing audited aliases remain frozen"}

    def targets(self, entity_id: str) -> dict:
        targets = [row for row in self.edges + self.non_atomic if row["old_entity_id"] == entity_id]
        return {"entity_id": entity_id, "targets": targets, "status": "MULTIPLE_TARGETS_REQUIRES_CONTEXT" if len(targets) > 1 else "SINGLE_TARGET_EVIDENCE" if targets else "NO_EDGE",
                "policy": "never collapse multiple targets; non-atomic edges retained"}


def validate_reference(reference_path: Path, manifest_path: Path) -> tuple[dict, list[dict]]:
    metadata = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = {"schema_version", "source_id", "url", "issuer", "document_id", "accessed_at", "reference_sha256", "authority_status", "extraction_review_status", "license_status", "effective_from", "effective_to", "table_as_of", "change_history_verified_through"}
    if not required <= set(metadata) or metadata["schema_version"] != "s3-official-code-reference-v1":
        raise ValueError("REFERENCE_MANIFEST_INCOMPLETE")
    host = urlparse(metadata["url"]).hostname or ""
    if not (host.endswith(".gov.vn") or host == "vbpl.vn" or host.endswith(".chinhphu.vn") or host == "chinhphu.vn"):
        raise ValueError("REFERENCE_NOT_OFFICIAL_PRIMARY_DOMAIN")
    accepted_review_statuses = {"APPROVED", "AUTOMATED_VALIDATED"}
    if metadata["authority_status"] != "OFFICIAL_PRIMARY_SOURCE" or metadata["extraction_review_status"] not in accepted_review_statuses:
        raise ValueError("REFERENCE_AUTHORITY_OR_EXTRACTION_NOT_REVIEWED")
    if metadata["extraction_review_status"] == "AUTOMATED_VALIDATED":
        validation = metadata.get("automated_validation", {})
        if validation.get("status") != "PASS" or not validation.get("checks"):
            raise ValueError("REFERENCE_AUTOMATED_VALIDATION_EVIDENCE_MISSING")
    if metadata["reference_sha256"] != file_hash(reference_path):
        raise ValueError("REFERENCE_HASH_MISMATCH")
    rows = read_csv(reference_path, REFERENCE_COLUMNS)
    for row in rows:
        if row["system"] not in ("cu", "moi") or row["level"] not in ("province", "district", "ward"):
            raise ValueError("REFERENCE_LEVEL_OR_SYSTEM_INVALID")
        if not row["code"].isascii() or not row["code"].isdigit() or not row["source_locator"] or row["source_id"] != metadata["source_id"]:
            raise ValueError("REFERENCE_CODE_OR_EVIDENCE_INVALID")
        if not row["province"] or row["level"] == "ward" and (not row["ward"] or row["system"] == "cu" and not row["district"]):
            raise ValueError("REFERENCE_FULL_PARENT_KEY_REQUIRED")
        if row["level"] == "district" and not row["district"]:
            raise ValueError("REFERENCE_DISTRICT_KEY_REQUIRED")
        for key in ("valid_from", "valid_to"):
            if row[key]:
                date.fromisoformat(row[key])
        if not row["valid_from"] or row["valid_to"] and row["valid_to"] <= row["valid_from"]:
            raise ValueError("REFERENCE_EFFECTIVE_INTERVAL_REQUIRED")
        if metadata["effective_from"] and row["valid_from"] < metadata["effective_from"] or metadata["effective_to"] and (not row["valid_to"] or row["valid_to"] > metadata["effective_to"]):
            raise ValueError("REFERENCE_ROW_OUTSIDE_DOCUMENT_INTERVAL")
    return metadata, rows


def verify_codes(gazetteer: TemporalGazetteerEvidence, reference_rows: list[dict], reference_date: str) -> list[dict]:
    index = defaultdict(list)
    for row in reference_rows:
        # Source spellings remain in official_* columns. Optional canonical_*
        # columns are a code-linked alignment to the existing entity label and
        # are never derived with fuzzy name matching.
        key = tuple([row["system"], row["level"]] + [
            canonical_name(row.get("canonical_" + name) or row[name])
            for name in ("province", "district", "ward")])
        if interval_contains(row["valid_from"], row["valid_to"], reference_date):
            index[key].append(row)
    decisions = []
    for entity in gazetteer.entities:
        start, end = gazetteer.half_open_interval(entity)
        matches = index.get(gazetteer.full_key(entity), []) if interval_contains(start, end, reference_date) else []
        codes = {row["code"] for row in matches}
        existing = entity["candidate_code"] or entity["official_code"]
        verified = len(codes) == 1 and bool(existing) and existing in codes
        status = "VERIFIED_PRIMARY_REFERENCE" if verified else "CODE_CONFLICT" if existing and codes and existing not in codes else "REFERENCE_CODE_AVAILABLE_ENTITY_UNCODED" if codes and not existing else "CODE_CONFLICT" if len(codes) > 1 else "NO_EXACT_DATED_REFERENCE"
        decisions.append({"entity_id": entity["entity_id"], "internal_id_stable": True,
            "reference_date": reference_date, "candidate_or_repo_code": existing or None,
            "verified_code": existing if verified else None,
            "status": status,
            "reference_candidates": sorted(codes), "evidence": [{"source_id": row["source_id"], "source_locator": row["source_locator"],
                "official_province_name": row.get("official_province_name"), "official_ward_name": row.get("official_ward_name"),
                "name_alignment": row.get("name_alignment")} for row in matches],
            "original_status": entity["code_status"], "promotion_policy": "derivative decisions only; frozen entity never modified"})
    return decisions


def audit_sources(package_dir: Path, output_dir: Path, source_register: list[dict],
                  reference_path=None, reference_manifest_path=None, reference_date="2025-06-30") -> dict:
    if output_dir.exists():
        raise FileExistsError(output_dir)
    gazetteer = TemporalGazetteerEvidence(package_dir)
    for entry in source_register:
        if entry.get("local_file"):
            source_file = ROOT / entry["local_file"]
            if not entry.get("sha256") or not source_file.is_file() or file_hash(source_file) != entry["sha256"]:
                raise ValueError("SOURCE_REGISTER_LOCAL_FILE_HASH_MISMATCH:" + entry["source_id"])
        elif entry.get("sha256") is not None:
            raise ValueError("WEB_ONLY_SOURCE_CANNOT_CLAIM_LOCAL_FILE_HASH")
    reference_metadata, reference_rows = None, []
    if bool(reference_path) != bool(reference_manifest_path):
        raise ValueError("REFERENCE_CSV_AND_MANIFEST_REQUIRED_TOGETHER")
    if reference_path:
        reference_metadata, reference_rows = validate_reference(reference_path, reference_manifest_path)
        snapshot = reference_metadata["table_as_of"]
        through = reference_metadata["change_history_verified_through"]
        if reference_metadata.get("snapshot_only") and snapshot != reference_date:
            raise ValueError("SNAPSHOT_ONLY_REFERENCE_DATE_MISMATCH")
        # A 2004 code catalogue is not a June 2025 snapshot without intervening changes.
        if snapshot != reference_date and (not through or date.fromisoformat(through) < date.fromisoformat(reference_date)):
            raise ValueError("REFERENCE_SNAPSHOT_OR_CHANGE_HISTORY_NOT_VALID_FOR_DATE")
    decisions = verify_codes(gazetteer, reference_rows, reference_date)
    coverage = Counter((row["system"], row["level"], row["code_status"]) for row in gazetteer.entities)
    verified = sum(row["status"] == "VERIFIED_PRIMARY_REFERENCE" for row in decisions)
    report = {"status": "PARTIAL_OLD_CODES_UNVERIFIED", "frozen_package": gazetteer.manifest["version"],
        "frozen_manifest_sha256": file_hash(package_dir / "manifest.json"), "entities": len(gazetteer.entities),
        "atomic_edges": len(gazetteer.edges), "non_atomic_edges": len(gazetteer.non_atomic),
        "audited_aliases": gazetteer.manifest["counts"]["aliases"],
        "relation_counts_preserved": dict(Counter(row["relation"] for row in gazetteer.edges)),
        "coverage": [{"system": system, "level": level, "code_status": status, "count": count} for (system, level, status), count in sorted(coverage.items())],
        "newly_verified_codes": verified, "verified_old_ward_codes": sum(row["status"] == "VERIFIED_PRIMARY_REFERENCE" and gazetteer.by_id[row["entity_id"]]["system"] == "cu" and gazetteer.by_id[row["entity_id"]]["level"] == "ward" for row in decisions),
        "decision_counts": dict(Counter(row["status"] for row in decisions)), "reference_metadata": reference_metadata,
        "gap": "Official publications identified; no reviewed dated reference transcription supplied. Internal CSV agreement is not external authority verification." if not reference_rows else "Partial decisions available; code/table licensing and complete release validation remain separate gates.",
        "new_package_released": False, "validity_policy": "half-open adapter; v2 bytes retained", "test100": "NOT_READ_NOT_USED"}
    output_dir.mkdir(parents=True)
    write_json(output_dir / "source_register.json", source_register)
    write_jsonl(output_dir / "code_verification_decisions.jsonl", decisions)
    write_json(output_dir / "coverage_gap_report.json", report)
    write_json(output_dir / "audit_manifest.json", {"purpose": "source_audit_not_gazetteer_release", "frozen_manifest_sha256": report["frozen_manifest_sha256"],
        "output_sha256": {p.name: file_hash(p) for p in output_dir.iterdir() if p.is_file()},
        "reference_sha256": file_hash(reference_path) if reference_path else None,
        "verifier_sha256": file_hash(Path(__file__))})
    return report
