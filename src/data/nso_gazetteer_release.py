"""Import and release a dated official NSO snapshot into a new Gazetteer version.

The official portal is live and includes later administrative changes. This module
uses only the comparison-side columns whose legal effective date is 2025-07-01,
then requires exact agreement with the project mapping table before releasing.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

from src.data.administrative_code_verifier import TemporalGazetteerEvidence

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DATE = "2025-07-01"
EXPECTED_NEW_WARDS = 3321
EXPECTED_NEW_PROVINCES = 34
OFFICIAL_PORTAL_URL = "https://danhmuchanhchinh.nso.gov.vn/Doi_Chieu_Moi.aspx"
REFERENCE_FIELDS = (
    "province", "district", "ward", "level", "system", "code",
    "valid_from", "valid_to", "source_id", "source_locator",
    "canonical_province", "canonical_district", "canonical_ward",
    "official_province_name", "official_ward_name", "name_alignment",
)
CODE_EVIDENCE_FIELDS = (
    "entity_id", "system", "level", "province", "district", "ward", "code",
    "official_province_name", "official_ward_name", "name_alignment",
    "source_id", "source_sha256", "source_locator", "source_as_of", "source_url",
)
SOURCE_ID = "nso_portal_snapshot_2025_07_01"
GAZETTEER_VERSION = "s3-gazetteer-v3-nso-2025-snapshot-partial"
EXPECTED_HEADERS = (
    "Tỉnh", "Tên Tỉnh", "Xã", "Tên Xã", "Nghị định", "Ngày hiệu lực",
    "Tên Xã DC", "Xã DC", "Nghị định", "Ngày hiệu lực", "Tên Tỉnh DC",
    "Tỉnh DC", "Ghi Chú",
)


def normalize(value: str) -> str:
    """Normalize Unicode composition and whitespace without dropping accents."""
    return " ".join(unicodedata.normalize("NFC", value or "").split()).casefold()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _text(value: Any, field: str, row_number: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"SOURCE_CODE_OR_TEXT_NOT_STORED_AS_TEXT:{field}:row={row_number}")
    result = " ".join(unicodedata.normalize("NFC", value).split())
    if not result:
        raise ValueError(f"SOURCE_REQUIRED_CELL_EMPTY:{field}:row={row_number}")
    return result


def read_official_export(path: Path, xlrd_dir: Path) -> tuple[list[dict], list[dict], dict]:
    """Read the official Excel export without executing workbook macros or formulas."""
    if not path.is_file():
        raise FileNotFoundError(path)
    if not xlrd_dir.is_dir():
        raise FileNotFoundError(f"xlrd runtime not found: {xlrd_dir}")
    sys.path.insert(0, str(xlrd_dir))
    try:
        import xlrd  # type: ignore[import-not-found]
    except ImportError as error:
        raise RuntimeError("xlrd 2.0.2 is required to read the official .xls export") from error

    book = xlrd.open_workbook(str(path), on_demand=True)
    if book.sheet_names() != ["Sheet1"]:
        raise ValueError(f"UNEXPECTED_OFFICIAL_EXPORT_SHEETS:{book.sheet_names()}")
    sheet = book.sheet_by_index(0)
    headers = tuple(sheet.cell_value(0, column) for column in range(sheet.ncols))
    if headers != EXPECTED_HEADERS:
        raise ValueError(f"UNEXPECTED_OFFICIAL_EXPORT_SCHEMA:{headers!r}")

    current_rows: list[dict] = []
    comparison_rows: list[dict] = []
    for row_index in range(1, sheet.nrows):
        excel_row = row_index + 1
        cells = [sheet.cell_value(row_index, column) for column in range(sheet.ncols)]
        # Main side is the live current list; comparison side is the dated 2025 snapshot.
        current_date = xlrd.xldate_as_datetime(cells[5], book.datemode).date().isoformat()
        comparison_date = xlrd.xldate_as_datetime(cells[9], book.datemode).date().isoformat()
        current_rows.append({
            "province_code": _text(cells[0], "province_code", excel_row),
            "province": _text(cells[1], "province", excel_row),
            "ward_code": _text(cells[2], "ward_code", excel_row),
            "ward": _text(cells[3], "ward", excel_row),
            "resolution": _text(cells[4], "resolution", excel_row),
            "effective_date": current_date,
            "source_locator": f"Sheet1!A{excel_row}:F{excel_row}",
        })
        comparison_rows.append({
            "province_code": _text(cells[11], "province_code_dc", excel_row),
            "province": _text(cells[10], "province_dc", excel_row),
            "ward_code": _text(cells[7], "ward_code_dc", excel_row),
            "ward": _text(cells[6], "ward_dc", excel_row),
            "resolution": _text(cells[8], "resolution_dc", excel_row),
            "effective_date": comparison_date,
            "note": " ".join(unicodedata.normalize("NFC", str(cells[12] or "")).split()),
            "source_locator": f"Sheet1!G{excel_row}:M{excel_row}",
        })

    profile = {
        "sheet": sheet.name,
        "headers": list(headers),
        "data_rows": sheet.nrows - 1,
        "current_effective_date_counts": dict(Counter(row["effective_date"] for row in current_rows)),
        "comparison_effective_date_counts": dict(Counter(row["effective_date"] for row in comparison_rows)),
        "current_rows_changed_after_2025_snapshot": sum(row["effective_date"] > SNAPSHOT_DATE for row in current_rows),
        "current_ward_names_differ_from_2025_side": sum(
            normalize(current_rows[index]["ward"]) != normalize(comparison_rows[index]["ward"])
            for index in range(len(current_rows))
        ),
        "current_province_names_differ_from_2025_side": sum(
            normalize(current_rows[index]["province"]) != normalize(comparison_rows[index]["province"])
            for index in range(len(current_rows))
        ),
    }
    return current_rows, comparison_rows, profile


def validate_snapshot_rows(rows: list[dict]) -> dict:
    if len(rows) != EXPECTED_NEW_WARDS:
        raise ValueError(f"SNAPSHOT_ROW_COUNT_MISMATCH:{len(rows)}:{EXPECTED_NEW_WARDS}")
    if any(row["effective_date"] != SNAPSHOT_DATE for row in rows):
        bad_dates = sorted({row["effective_date"] for row in rows if row["effective_date"] != SNAPSHOT_DATE})
        raise ValueError(f"SNAPSHOT_EFFECTIVE_DATE_MISMATCH:{bad_dates}")
    if any("2025" not in row["resolution"] for row in rows):
        raise ValueError("SNAPSHOT_CONTAINS_NON_2025_RESOLUTION")
    ward_codes = [row["ward_code"] for row in rows]
    if len(set(ward_codes)) != len(ward_codes):
        raise ValueError("DUPLICATE_NEW_WARD_CODE_IN_OFFICIAL_EXPORT")
    province_pairs = {(row["province_code"], normalize(row["province"])) for row in rows}
    if len(province_pairs) != EXPECTED_NEW_PROVINCES:
        raise ValueError(f"SNAPSHOT_PROVINCE_COUNT_MISMATCH:{len(province_pairs)}:{EXPECTED_NEW_PROVINCES}")
    by_province_code: dict[str, set[str]] = defaultdict(set)
    for code, name in province_pairs:
        by_province_code[code].add(name)
    if any(len(names) != 1 for names in by_province_code.values()):
        raise ValueError("CONFLICTING_PROVINCE_NAME_FOR_CODE")
    return {"new_wards": len(ward_codes), "new_provinces": len(province_pairs)}


def make_reference_rows(rows: list[dict]) -> list[dict[str, str]]:
    """Create exact reference keys for the 2025 snapshot; do not pad or infer codes."""
    validate_snapshot_rows(rows)
    result: list[dict[str, str]] = []
    source_provinces: dict[str, dict] = {}
    for row in rows:
        existing = source_provinces.get(row["province_code"])
        if existing and normalize(existing["province"]) != normalize(row["province"]):
            raise ValueError("CONFLICTING_PROVINCE_NAME_FOR_CODE")
        source_provinces.setdefault(row["province_code"], row)
    for row in sorted(source_provinces.values(), key=lambda item: item["province_code"]):
        result.append({
            "province": row["province"], "district": "", "ward": "", "level": "province", "system": "moi",
            "code": row["province_code"], "valid_from": SNAPSHOT_DATE, "valid_to": "",
            "source_id": SOURCE_ID, "source_locator": row["source_locator"],
        })
    for row in rows:
        result.append({
            "province": row["province"], "district": "", "ward": row["ward"], "level": "ward", "system": "moi",
            "code": row["ward_code"], "valid_from": SNAPSHOT_DATE, "valid_to": "",
            "source_id": SOURCE_ID, "source_locator": row["source_locator"],
        })
    return result


def reconcile_mapping(rows: list[dict], mapping_path: Path) -> dict:
    """Reconcile by official ward code; retain every name difference explicitly.

    A matching code is the join key. Names are compared exactly after NFC and
    whitespace normalization; differences are reported and never auto-corrected.
    Province context must still match so a code cannot be attached under a wrong
    parent just because its numeric code matches.
    """
    with mapping_path.open(encoding="utf-8-sig", newline="") as stream:
        mapping = list(csv.DictReader(stream))
    expected: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for row in mapping:
        code = (row.get("Mã phường/xã mới") or "").strip()
        if code:
            expected[code].add((normalize(row["Phường/Xã mới (từ 1/7/2025)"]), normalize(row["Tỉnh/TP mới"])))
    conflicts = {code: sorted(values) for code, values in expected.items() if len(values) != 1}
    observed = {row["ward_code"]: (normalize(row["ward"]), normalize(row["province"])) for row in rows}
    code_mismatches = []
    name_variants = []
    for code, value in sorted(observed.items()):
        candidate = expected.get(code)
        if candidate is None or len(candidate) != 1:
            code_mismatches.append({"code": code, "official": value, "mapping_candidates": sorted(candidate or set())})
            continue
        mapping_ward, mapping_province = next(iter(candidate))
        official_ward, official_province = value
        if official_province != mapping_province:
            code_mismatches.append({"code": code, "official": value, "mapping_candidates": sorted(candidate)})
        elif official_ward != mapping_ward:
            name_variants.append({"code": code, "official_ward": official_ward,
                "mapping_ward": mapping_ward, "official_province": official_province,
                "mapping_province": mapping_province,
                "policy": "retain both spellings; code and province context match"})
    missing_from_official = sorted(set(expected) - set(observed))
    return {
        "mapping_rows": len(mapping),
        "mapping_unique_new_codes": len(expected),
        "mapping_internal_code_conflicts": conflicts,
        "official_rows": len(rows),
        "exact_code_and_province_matches": len(rows) - len(code_mismatches),
        "name_variant_count": len(name_variants),
        "name_variants": name_variants,
        "code_or_parent_mismatches": code_mismatches,
        "mapping_codes_missing_from_official_export": missing_from_official,
        "status": "EXACT_CODE_AND_PARENT_MATCH_WITH_NAME_VARIANTS" if not conflicts and not code_mismatches and not missing_from_official and len(expected) == len(rows) and name_variants else
                  "EXACT_MATCH" if not conflicts and not code_mismatches and not missing_from_official and len(expected) == len(rows) else "BLOCKED_MISMATCH",
    }


def make_reference_rows(rows: list[dict], gazetteer: TemporalGazetteerEvidence) -> list[dict[str, str]]:
    """Align an official snapshot to existing entities by code and parent.

    Raw official names are stored alongside canonical Gazetteer names. The
    Gazetteer spelling is not changed, and source spelling variants are not
    silently promoted to aliases.
    """
    validate_snapshot_rows(rows)
    province_entities = {
        normalize(entity["canonical_name"]): entity
        for entity in gazetteer.entities
        if entity["system"] == "moi" and entity["level"] == "province"
    }
    if len(province_entities) != EXPECTED_NEW_PROVINCES:
        raise ValueError("GAZETTEER_NEW_PROVINCE_COUNT_MISMATCH")
    wards_by_code: dict[str, dict] = {}
    for entity in gazetteer.entities:
        if entity["system"] == "moi" and entity["level"] == "ward":
            code = entity["official_code"] or entity["candidate_code"]
            if code in wards_by_code:
                raise ValueError(f"DUPLICATE_GAZETTEER_NEW_WARD_CODE:{code}")
            wards_by_code[code] = entity
    if len(wards_by_code) != EXPECTED_NEW_WARDS:
        raise ValueError("GAZETTEER_NEW_WARD_CODE_COUNT_MISMATCH")

    province_source: dict[str, dict] = {}
    for row in rows:
        key = normalize(row["province"])
        previous = province_source.get(key)
        if previous and previous["province_code"] != row["province_code"]:
            raise ValueError("OFFICIAL_PROVINCE_CODE_CONFLICT")
        province_source.setdefault(key, row)
    if set(province_source) != set(province_entities):
        raise ValueError("OFFICIAL_PROVINCE_NAMES_DO_NOT_MATCH_GAZETTEER")

    result = []
    province_code_by_name = {}
    for key, source in sorted(province_source.items()):
        entity = province_entities[key]
        province_code_by_name[key] = source["province_code"]
        result.append({
            "province": entity["canonical_name"], "district": "", "ward": "",
            "level": "province", "system": "moi", "code": source["province_code"],
            "valid_from": SNAPSHOT_DATE, "valid_to": "", "source_id": SOURCE_ID,
            "source_locator": source["source_locator"], "canonical_province": entity["canonical_name"],
            "canonical_district": "", "canonical_ward": "",
            "official_province_name": source["province"], "official_ward_name": "",
            "name_alignment": "EXACT" if normalize(entity["canonical_name"]) == normalize(source["province"]) else "VARIANT",
        })

    seen_codes = set()
    for source in rows:
        code = source["ward_code"]
        entity = wards_by_code.get(code)
        if entity is None:
            raise ValueError(f"OFFICIAL_WARD_CODE_NOT_IN_GAZETTEER:{code}")
        parent = gazetteer.by_id.get(entity["parent_id"])
        if not parent or parent["level"] != "province" or normalize(parent["canonical_name"]) != normalize(source["province"]):
            raise ValueError(f"OFFICIAL_WARD_PROVINCE_PARENT_MISMATCH:{code}")
        if code in seen_codes:
            raise ValueError(f"DUPLICATE_OFFICIAL_WARD_CODE:{code}")
        seen_codes.add(code)
        result.append({
            "province": parent["canonical_name"], "district": "", "ward": entity["canonical_name"],
            "level": "ward", "system": "moi", "code": code,
            "valid_from": SNAPSHOT_DATE, "valid_to": "", "source_id": SOURCE_ID,
            "source_locator": source["source_locator"], "canonical_province": parent["canonical_name"],
            "canonical_district": "", "canonical_ward": entity["canonical_name"],
            "official_province_name": source["province"], "official_ward_name": source["ward"],
            "name_alignment": "EXACT" if normalize(entity["canonical_name"]) == normalize(source["ward"]) else "CODE_MATCH_NAME_VARIANT",
        })
    if len(result) != EXPECTED_NEW_WARDS + EXPECTED_NEW_PROVINCES:
        raise ValueError("OFFICIAL_REFERENCE_EXPECTED_3355_KEYS")
    return result


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _full_key_index(gazetteer: TemporalGazetteerEvidence) -> dict[tuple, dict]:
    index = {}
    for entity in gazetteer.entities:
        key = gazetteer.full_key(entity)
        if key in index:
            raise ValueError(f"DUPLICATE_GAZETTEER_FULL_KEY:{key}")
        index[key] = entity
    return index


def build_verified_package(
    source_package: Path,
    output_package: Path,
    official_rows: list[dict],
    reference_rows: list[dict[str, str]],
    mapping_report: dict,
    export_path: Path,
    mapping_path: Path,
    owner_confirmed_mapping_origin: bool = True,
    legal_document_path: Path | None = None,
    reference_manifest_path: Path | None = None,
) -> dict:
    """Create s3_v3 as a new immutable derivative; never edit s3_v2 in place."""
    if output_package.exists():
        raise FileExistsError(output_package)
    if mapping_report["status"] not in ("EXACT_MATCH", "EXACT_CODE_AND_PARENT_MATCH_WITH_NAME_VARIANTS"):
        raise ValueError("MAPPING_RECONCILIATION_NOT_EXACT")
    validate_snapshot_rows(official_rows)
    package = TemporalGazetteerEvidence(source_package)
    base_manifest = package.manifest
    for name, expected_hash in base_manifest["output_sha256"].items():
        if sha256(source_package / name) != expected_hash:
            raise ValueError(f"FROZEN_SOURCE_PACKAGE_HASH_MISMATCH:{name}")
    by_key = _full_key_index(package)
    code_by_key = {}
    locator_by_key = {}
    reference_by_level_code = {}
    for row in reference_rows:
        key = (row["system"], row["level"], normalize(row["province"]), normalize(row["district"]), normalize(row["ward"]))
        if key in code_by_key:
            raise ValueError(f"DUPLICATE_REFERENCE_FULL_KEY:{key}")
        code_by_key[key] = row["code"]
        locator_by_key[key] = row["source_locator"]
        level_code_key = (row["level"], row["code"])
        if level_code_key in reference_by_level_code:
            raise ValueError(f"DUPLICATE_REFERENCE_LEVEL_CODE:{level_code_key}")
        reference_by_level_code[level_code_key] = row
    if len(code_by_key) != EXPECTED_NEW_WARDS + EXPECTED_NEW_PROVINCES:
        raise ValueError("OFFICIAL_REFERENCE_EXPECTED_3355_KEYS")
    entity_by_key = {(key[0], key[1], normalize(key[2]), normalize(key[3]), normalize(key[4])): entity for key, entity in by_key.items()}
    missing = sorted(key for key in code_by_key if key not in entity_by_key)
    conflicts = []
    evidence = []
    for key, code in code_by_key.items():
        entity = entity_by_key.get(key)
        if entity is None:
            continue
        existing_code = entity["official_code"] or entity["candidate_code"]
        if existing_code and existing_code != code:
            conflicts.append({"entity_id": entity["entity_id"], "existing_code": existing_code, "official_code": code})
        official_name_row = reference_by_level_code[(key[1], code)]
        evidence.append({
            "entity_id": entity["entity_id"], "system": key[0], "level": key[1],
            "province": entity["canonical_name"] if key[1] == "province" else _province_name(package, entity),
            "district": _parent_name(package, entity, "district"),
            "ward": entity["canonical_name"] if key[1] == "ward" else "", "code": code,
            "official_province_name": official_name_row["official_province_name"],
            "official_ward_name": official_name_row["official_ward_name"],
            "name_alignment": official_name_row["name_alignment"],
            "source_id": SOURCE_ID, "source_sha256": sha256(export_path),
            "source_locator": locator_by_key[key], "source_as_of": SNAPSHOT_DATE, "source_url": OFFICIAL_PORTAL_URL,
        })
    if missing or conflicts or len(evidence) != EXPECTED_NEW_WARDS + EXPECTED_NEW_PROVINCES:
        raise ValueError(json.dumps({"missing_gazetteer_keys": missing[:20], "code_conflicts": conflicts[:20], "evidence_count": len(evidence)}, ensure_ascii=False))

    staging = output_package.with_name(output_package.name + ".staging")
    if staging.exists():
        raise FileExistsError(staging)
    shutil.copytree(source_package, staging)
    try:
        input_entities = package.entities
        verified_by_id = {row["entity_id"]: row for row in evidence}
        output_entities = []
        for original in input_entities:
            row = dict(original)
            official = verified_by_id.get(row["entity_id"])
            if official:
                row["official_code"] = official["code"]
                row["candidate_code"] = ""
                row["candidate_code_source_id"] = ""
                row["candidate_code_source_hash"] = ""
                row["code_status"] = "verified_primary_source_snapshot"
                row["status"] = "verified_official_source_snapshot"
            output_entities.append(row)
        entity_fields = tuple(output_entities[0].keys())
        _write_csv(staging / "entities.csv", entity_fields, output_entities)
        _write_csv(staging / "official_code_reference.csv", REFERENCE_FIELDS, reference_rows)
        _write_csv(staging / "code_evidence.csv", CODE_EVIDENCE_FIELDS, evidence)
        if reference_manifest_path is None or not reference_manifest_path.is_file():
            raise FileNotFoundError("Official code reference manifest is required for a reproducible release")
        shutil.copyfile(reference_manifest_path, staging / "official_code_reference_manifest.json")

        with (source_package / "source_register.csv").open(encoding="utf-8-sig", newline="") as stream:
            source_register = list(csv.DictReader(stream))
        source_register = [{**row, "source_export_sha256": ""} for row in source_register]
        source_register.append({
            "source_id": SOURCE_ID,
            "name": "Cục Thống kê — đối chiếu đơn vị hành chính, snapshot 01/07/2025",
            "path_or_url": OFFICIAL_PORTAL_URL,
            "level_scope": "province,ward",
            "system": "moi",
            "valid_range": "as_of_2025-07-01",
            "access_date": datetime.now().date().isoformat(),
            "license": "Public official portal; explicit dataset reuse terms not located",
            "sha256": "",
            "source_export_sha256": sha256(export_path),
            "role": "primary_source_new_province_and_ward_codes_snapshot",
        })
        _write_csv(staging / "source_register.csv", tuple(source_register[0].keys()), source_register)

        coverage = _read_json(staging / "coverage_report.json")
        coverage["version"] = GAZETTEER_VERSION
        coverage["new_provinces_with_official_verified_code"] = EXPECTED_NEW_PROVINCES
        coverage["new_wards_with_official_verified_code"] = EXPECTED_NEW_WARDS
        coverage["old_wards_with_official_verified_code"] = 0
        coverage["official_code_source_snapshot"] = {
            "source_id": SOURCE_ID, "as_of": SNAPSHOT_DATE, "verified_entities": len(evidence),
            "new_provinces": EXPECTED_NEW_PROVINCES, "new_wards": EXPECTED_NEW_WARDS,
            "name_variants_retained": sum(row["name_alignment"] != "EXACT" for row in evidence),
        }
        coverage["release_status"] = "PARTIAL_OLD_CODES_UNVERIFIED"
        _write_json(staging / "coverage_report.json", coverage)

        manifest = dict(base_manifest)
        manifest["version"] = GAZETTEER_VERSION
        manifest["parent_version"] = base_manifest["version"]
        manifest["parent_manifest_sha256"] = sha256(source_package / "manifest.json")
        manifest["release_status"] = "PARTIAL_OLD_CODES_UNVERIFIED"
        manifest["snapshot_only"] = True
        manifest["snapshot_date"] = SNAPSHOT_DATE
        manifest["official_code_snapshot"] = {
            "source_id": SOURCE_ID, "as_of": SNAPSHOT_DATE, "url": OFFICIAL_PORTAL_URL,
            "source_export_path": str(export_path.relative_to(ROOT)), "source_export_sha256": sha256(export_path),
            "reference_manifest_sha256": sha256(reference_manifest_path),
            "source_mapping_sha256": sha256(mapping_path), "verified_new_provinces": EXPECTED_NEW_PROVINCES,
            "verified_new_wards": EXPECTED_NEW_WARDS, "old_codes_verified": 0,
            "owner_confirmed_mapping_origin": owner_confirmed_mapping_origin,
            "license_status": "PUBLIC_PORTAL_TERMS_NOT_LOCATED",
            "selection_policy": "comparison-side rows with effective date 2025-07-01; live-side 2026 updates excluded",
            "mapping_name_variants": mapping_report["name_variant_count"],
            "entity_name_variants": sum(row["name_alignment"] != "EXACT" for row in evidence),
        }
        if legal_document_path and legal_document_path.is_file():
            manifest["official_code_snapshot"]["companion_legal_document"] = {
                "url": "https://datafiles.chinhphu.vn/cpp/files/vbpq/2025/7/19ttg.signed.pdf",
                "path": str(legal_document_path.relative_to(ROOT)),
                "sha256": sha256(legal_document_path),
                "role": "legal provenance; not transcribed to create reference rows",
            }
        manifest["counts"] = dict(manifest["counts"])
        manifest["counts"]["official_code_evidence_rows"] = len(evidence)
        manifest["limitations"] = list(manifest.get("limitations", []))
        manifest["limitations"].extend([
            "New province and ward codes are verified against an official NSO export as of 2025-07-01.",
            "Old province/district/ward codes remain candidates or missing; package release is partial.",
            "The official portal is live and also includes later changes; only the 2025 comparison side was imported.",
            "This package is a 2025-07-01 snapshot and lookup rejects dates outside that exact as-of date.",
            "Official source spellings that differ from canonical project names are recorded by code; canonical names and aliases were not rewritten.",
            "Public access was confirmed; explicit data reuse license terms were not located.",
        ])
        release_script = ROOT / "scripts/39_release_nso_gazetteer_snapshot.py"
        manifest["parent_build_script_sha256"] = base_manifest.get("build_script_sha256")
        manifest["build_script_sha256"] = sha256(release_script) if release_script.is_file() else None
        manifest["release_script_sha256"] = manifest["build_script_sha256"]
        manifest["release_module_sha256"] = sha256(Path(__file__))
        manifest["code_verifier_sha256"] = sha256(ROOT / "src/data/administrative_code_verifier.py")
        manifest["output_sha256"] = {
            path.name: sha256(path)
            for path in staging.iterdir()
            if path.is_file() and path.name != "manifest.json"
        }
        _write_json(staging / "manifest.json", manifest)
        # Re-open the finished package to verify all listed hashes and parent links.
        TemporalGazetteerEvidence(staging)
        staging.rename(output_package)
    except Exception:
        # Leave the staging directory as evidence for recovery; never touch the frozen source.
        raise
    return {
        "status": "PARTIAL_OLD_CODES_UNVERIFIED",
        "package": str(output_package),
        "official_codes_verified": len(evidence),
        "new_provinces_verified": EXPECTED_NEW_PROVINCES,
        "new_wards_verified": EXPECTED_NEW_WARDS,
        "old_codes_verified": 0,
    }


def _parent_name(gazetteer: TemporalGazetteerEvidence, entity: dict, level: str) -> str:
    current = gazetteer.by_id.get(entity["parent_id"])
    while current:
        if current["level"] == level:
            return current["canonical_name"]
        current = gazetteer.by_id.get(current["parent_id"])
    return ""


def _province_name(gazetteer: TemporalGazetteerEvidence, entity: dict) -> str:
    if entity["level"] == "province":
        return entity["canonical_name"]
    current = entity
    while current:
        if current["level"] == "province":
            return current["canonical_name"]
        current = gazetteer.by_id.get(current["parent_id"])
    return ""
