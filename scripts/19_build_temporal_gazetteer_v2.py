"""Build and query temporal gazetteer v2 (S3-03).

Features:
- Produces clean gazetteer package in data/processed/gazetteer/s3_v2/
- Fully preserves s3_v1 without overwriting.
- Separates official_code (verified) from candidate_code (unverified third-party).
- Stores the 5 non-atomic district-level island transitions in non_atomic_transitions.csv.
- Generates source_register.csv, coverage_report.json, and manifest.json.
- Provides context-aware temporal lookup query CLI.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MAPPING = ROOT / "data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv"
LEGACY = ROOT / "third_party/vietnamadminunits/data/interim/legacy_63-province-10040-ward_with_location_and_key.csv"
ALIAS_SOURCE = ROOT / "src/data/administrative_alias.py"
OUTPUT_V2 = ROOT / "data/processed/gazetteer/s3_v2"
VERSION = "s3-gazetteer-v2-partial"
BOUNDARY = "2025-07-01"

ENTITY_FIELDS = (
    "entity_id",
    "level",
    "system",
    "canonical_name",
    "parent_id",
    "official_code",
    "candidate_code",
    "candidate_code_source_id",
    "candidate_code_source_hash",
    "code_status",
    "valid_from",
    "valid_to",
    "source_id",
    "source_hash",
    "status",
)

EDGE_FIELDS = (
    "old_entity_id",
    "new_entity_id",
    "old_province",
    "old_district",
    "old_ward",
    "new_province",
    "new_ward",
    "new_ward_code",
    "relation",
    "merge_form",
    "source_row",
    "source_id",
    "source_hash",
)

NON_ATOMIC_FIELDS = (
    "source_row",
    "old_entity_id",
    "new_entity_id",
    "old_province",
    "old_district",
    "new_province",
    "new_ward",
    "new_ward_code",
    "new_unit_type",
    "merge_form",
    "relation",
    "status",
    "source_id",
    "source_hash",
)

ALIAS_FIELDS = ("entity_id", "alias", "system", "level", "source_id", "source_hash")
SOURCE_REGISTER_FIELDS = (
    "source_id", "name", "path_or_url", "level_scope", "system",
    "valid_range", "access_date", "license", "sha256", "role"
)

MAPPING_COLUMNS = (
    "Phường/Xã cũ",
    "Quận/Huyện cũ",
    "Tỉnh/TP cũ (trước sáp nhập)",
    "Tỉnh/TP mới",
    "Phường/Xã mới (từ 1/7/2025)",
    "Loại đơn vị mới",
    "Mã phường/xã mới",
    "Hình thức sáp nhập",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def norm(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value or "").casefold().split())


def read_csv(path: Path, required: tuple[str, ...]) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = set(required) - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"{path.name}: missing columns {sorted(missing)}")
        return list(reader)


def stable_id(system: str, level: str, province: str, district: str, name: str) -> str:
    key = "|".join(map(norm, (system, level, province, district, name)))
    return f"{system}:{level}:{hashlib.sha256(key.encode('utf-8')).hexdigest()[:20]}"


def audited_aliases() -> dict[str, dict[str, str]]:
    tree = ast.parse(ALIAS_SOURCE.read_text(encoding="utf-8"))
    names = {"PROVINCE_ALIASES", "DISTRICT_ALIASES", "WARD_ALIASES"}
    result = {}
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id in names:
                result[node.target.id] = ast.literal_eval(node.value)
    if set(result) != names:
        raise ValueError("Could not read all audited alias dictionaries")
    return result


def write_csv(path: Path, fields: tuple[str, ...], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build() -> dict[str, Any]:
    print(f"Building temporal gazetteer v2 in {OUTPUT_V2}...")
    OUTPUT_V2.mkdir(parents=True, exist_ok=True)

    # v1 is the frozen comparison point. Refuse to build on a changed copy.
    v1_dir = ROOT / "data/processed/gazetteer/s3_v1"
    v1_manifest = json.loads((v1_dir / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in v1_manifest["output_sha256"].items():
        if sha256(v1_dir / name) != expected:
            raise ValueError(f"Frozen gazetteer v1 input drift: {name}")

    mapping_rows = read_csv(MAPPING, MAPPING_COLUMNS)
    legacy_rows = read_csv(
        LEGACY,
        ("province", "district", "ward", "provinceCode", "districtCode", "wardCode"),
    )
    hashes = {
        "mapping": sha256(MAPPING),
        "legacy_candidate": sha256(LEGACY),
        "audited_aliases": sha256(ALIAS_SOURCE),
        "build_script": sha256(Path(__file__)),
    }

    legacy_index = defaultdict(list)
    for row in legacy_rows:
        key = tuple(norm(row[column]) for column in ("province", "district", "ward"))
        legacy_index[key].append(row)

    entities: dict[str, dict[str, str]] = {}
    edges: list[dict[str, str]] = []
    non_atomic_transitions: list[dict[str, str]] = []
    old_targets = defaultdict(set)
    new_sources = defaultdict(set)
    legacy_match = Counter()
    source_id = "official_mapping_2025"

    def add_entity(
        system: str,
        level: str,
        province: str,
        district: str,
        name: str,
        parent_id: str,
        official_code: str = "",
    ) -> str:
        entity_id = stable_id(system, level, province, district, name)
        row = {
            "entity_id": entity_id,
            "level": level,
            "system": system,
            "canonical_name": name,
            "parent_id": parent_id,
            "official_code": official_code,
            "candidate_code": "",
            "candidate_code_source_id": "",
            "candidate_code_source_hash": "",
            "code_status": "verified_source" if official_code else "unverified_missing",
            "valid_from": BOUNDARY if system == "moi" else "",
            "valid_to": "" if system == "moi" else "2025-06-30",
            "source_id": source_id,
            "source_hash": hashes["mapping"],
            "status": "mapped" if official_code else "mapped_without_verified_code",
        }
        existing = entities.get(entity_id)
        if existing:
            identity_fields = ("level", "system", "canonical_name", "parent_id", "official_code")
            if any(existing[field] != row[field] for field in identity_fields):
                raise ValueError(f"Conflicting entity definition: {entity_id}")
        else:
            entities[entity_id] = row
        return entity_id

    for source_row, row in enumerate(mapping_rows, start=2):
        old_ward = row["Phường/Xã cũ"].strip()
        old_district = row["Quận/Huyện cũ"].strip()
        old_province = row["Tỉnh/TP cũ (trước sáp nhập)"].strip()
        new_ward = row["Phường/Xã mới (từ 1/7/2025)"].strip()
        new_province = row["Tỉnh/TP mới"].strip()
        new_code = row["Mã phường/xã mới"].strip()
        new_unit_type = row.get("Loại đơn vị mới", "").strip()
        merge_form = row["Hình thức sáp nhập"].strip()

        if not all((old_district, old_province, new_ward, new_province, new_code)):
            continue

        if not old_ward:
            # 5 Island district conversions: Non-atomic transition
            op = add_entity("cu", "province", old_province, "", old_province, "")
            od = add_entity("cu", "district", old_province, "", old_district, op)
            np = add_entity("moi", "province", new_province, "", new_province, "")
            nw = add_entity("moi", "ward", new_province, "", new_ward, np, new_code)
            non_atomic_transitions.append({
                "source_row": str(source_row),
                "old_entity_id": od,
                "new_entity_id": nw,
                "old_province": old_province,
                "old_district": old_district,
                "new_province": new_province,
                "new_ward": new_ward,
                "new_ward_code": new_code,
                "new_unit_type": new_unit_type,
                "merge_form": merge_form,
                "relation": "DISTRICT_TO_SPECIAL_ZONE",
                "status": "NOT_WARD_EDGE",
                "source_id": source_id,
                "source_hash": hashes["mapping"],
            })
            continue

        op = add_entity("cu", "province", old_province, "", old_province, "")
        od = add_entity("cu", "district", old_province, "", old_district, op)
        ow = add_entity("cu", "ward", old_province, old_district, old_ward, od)
        np = add_entity("moi", "province", new_province, "", new_province, "")
        nw = add_entity("moi", "ward", new_province, "", new_ward, np, new_code)

        key = tuple(norm(value) for value in (old_province, old_district, old_ward))
        candidates = legacy_index.get(key, [])
        if len(candidates) == 1:
            legacy_match["unique_name_join"] += 1
            for eid, column in ((op, "provinceCode"), (od, "districtCode"), (ow, "wardCode")):
                code = candidates[0][column].strip()
                if code:
                    prior = entities[eid]["candidate_code"]
                    if prior and prior != code:
                        raise ValueError(f"Conflicting third-party code for {eid}")
                    entities[eid]["candidate_code"] = code
                    entities[eid]["candidate_code_source_id"] = "legacy_candidate"
                    entities[eid]["candidate_code_source_hash"] = hashes["legacy_candidate"]
                    entities[eid]["code_status"] = "candidate_third_party_unverified"
        else:
            legacy_match["missing_or_ambiguous_name_join"] += 1

        edge = {
            "old_entity_id": ow,
            "new_entity_id": nw,
            "old_province": old_province,
            "old_district": old_district,
            "old_ward": old_ward,
            "new_province": new_province,
            "new_ward": new_ward,
            "new_ward_code": new_code,
            "relation": "",
            "merge_form": merge_form,
            "source_row": str(source_row),
            "source_id": source_id,
            "source_hash": hashes["mapping"],
        }
        edges.append(edge)
        old_targets[ow].add(nw)
        new_sources[nw].add(ow)

    if len(edges) + len(non_atomic_transitions) != len(mapping_rows):
        raise ValueError("Mapping rows were skipped without an explicit audit record")
    if len(non_atomic_transitions) != 5:
        raise ValueError(f"Expected five non-atomic transitions, got {len(non_atomic_transitions)}")
    if any(entity["parent_id"] and entity["parent_id"] not in entities for entity in entities.values()):
        raise ValueError("Gazetteer contains an orphan parent ID")
    if any(edge["old_entity_id"] not in entities or edge["new_entity_id"] not in entities for edge in edges):
        raise ValueError("Gazetteer edge references a missing entity")
    new_codes = [entity["official_code"] for entity in entities.values()
                 if entity["system"] == "moi" and entity["level"] == "ward"]
    if len(new_codes) != len(set(new_codes)) or any(not code for code in new_codes):
        raise ValueError("New ward codes are missing or shared by different entities")

    # Classify edge graph degrees
    relation_counts = Counter()
    for edge in edges:
        old_id = edge["old_entity_id"]
        new_id = edge["new_entity_id"]
        fan_out = len(old_targets[old_id])
        fan_in = len(new_sources[new_id])
        if fan_out == 1 and fan_in == 1:
            rel = "C/1-1"
        elif fan_out > 1 and fan_in == 1:
            rel = "A/1-N"
        elif fan_out == 1 and fan_in > 1:
            rel = "B/N-1"
        else:
            rel = "M/M-N"
        edge["relation"] = rel
        relation_counts[rel] += 1

    # Aliases
    aliases_data = audited_aliases()
    alias_rows = []
    alias_seen = set()

    for entity_id, entity in entities.items():
        table_name = f"{entity['level'].upper()}_ALIASES"
        table = aliases_data.get(table_name, {})
        norm_name = norm(entity["canonical_name"])
        for variant, canonical in table.items():
            if norm(canonical) == norm_name:
                if norm(variant) == norm_name:
                    continue
                key = (entity_id, norm(variant))
                if key not in alias_seen:
                    alias_seen.add(key)
                    alias_rows.append({
                        "entity_id": entity_id,
                        "alias": variant,
                        "system": entity["system"],
                        "level": entity["level"],
                        "source_id": "audited_aliases",
                        "source_hash": hashes["audited_aliases"],
                    })

    # Source register
    source_register_rows = [
        {
            "source_id": "official_mapping_2025",
            "name": "Bảng đối chiếu sắp xếp đơn vị hành chính cấp xã 2025",
            "path_or_url": "data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv",
            "level_scope": "province,district,ward",
            "system": "cu_to_moi",
            "valid_range": "2025-07-01_onward",
            "access_date": "2026-09-16",
            "license": "NOT_DOCUMENTED_IN_REPOSITORY",
            "sha256": hashes["mapping"],
            "role": "edge_authority_and_new_ward_official_code",
        },
        {
            "source_id": "legacy_candidate",
            "name": "Bảng đơn vị hành chính 63 tỉnh 10.040 xã cũ (VietnamAdminUnits)",
            "path_or_url": "third_party/vietnamadminunits/data/interim/legacy_63-province-10040-ward_with_location_and_key.csv",
            "level_scope": "province,district,ward",
            "system": "cu",
            "valid_range": "up_to_2025-06-30",
            "access_date": "2026-09-16",
            "license": "NOT_DOCUMENTED_IN_REPOSITORY",
            "sha256": hashes["legacy_candidate"],
            "role": "candidate_old_codes_only_unverified",
        },
        {
            "source_id": "audited_aliases",
            "name": "Lớp định danh và viết tắt hành chính đã kiểm chứng",
            "path_or_url": "src/data/administrative_alias.py",
            "level_scope": "province,district,ward",
            "system": "cu,moi",
            "valid_range": "all",
            "access_date": "2026-09-25",
            "license": "Internal Project Audited Alias Layer",
            "sha256": hashes["audited_aliases"],
            "role": "audited_alias_authority",
        },
    ]

    # Write CSVs
    entity_list = sorted(entities.values(), key=lambda r: (r["system"], r["level"], r["canonical_name"], r["entity_id"]))
    edges.sort(key=lambda r: (r["old_province"], r["old_district"], r["old_ward"], r["new_ward"]))
    alias_rows.sort(key=lambda r: (r["level"], r["alias"], r["entity_id"]))

    write_csv(OUTPUT_V2 / "entities.csv", ENTITY_FIELDS, entity_list)
    write_csv(OUTPUT_V2 / "edges.csv", EDGE_FIELDS, edges)
    write_csv(OUTPUT_V2 / "aliases.csv", ALIAS_FIELDS, alias_rows)
    write_csv(OUTPUT_V2 / "non_atomic_transitions.csv", NON_ATOMIC_FIELDS, non_atomic_transitions)
    write_csv(OUTPUT_V2 / "source_register.csv", SOURCE_REGISTER_FIELDS, source_register_rows)

    # Coverage report
    coverage_report = {
        "version": VERSION,
        "total_entities": len(entity_list),
        "entities_by_level": dict(Counter(e["level"] for e in entity_list)),
        "entities_by_system": dict(Counter(e["system"] for e in entity_list)),
        "old_wards_total": sum(1 for e in entity_list if e["system"] == "cu" and e["level"] == "ward"),
        "old_wards_with_candidate_code": sum(
            1 for e in entity_list if e["system"] == "cu" and e["level"] == "ward" and e["candidate_code"]
        ),
        "old_wards_with_official_verified_code": sum(
            1 for e in entity_list if e["system"] == "cu" and e["level"] == "ward" and e["code_status"] == "verified_source"
        ),
        "new_wards_total": sum(1 for e in entity_list if e["system"] == "moi" and e["level"] == "ward"),
        "new_wards_with_official_verified_code": sum(
            1 for e in entity_list if e["system"] == "moi" and e["level"] == "ward" and e["code_status"] == "verified_source"
        ),
        "new_wards_with_source_table_code": len(new_codes),
        "atomic_edges_total": len(edges),
        "edge_relations": dict(relation_counts),
        "non_atomic_transitions_count": len(non_atomic_transitions),
        "aliases_count": len(alias_rows),
        "release_status": "PARTIAL_OLD_CODES_UNVERIFIED",
    }
    (OUTPUT_V2 / "coverage_report.json").write_text(
        json.dumps(coverage_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    old_ward_names = Counter(entity["canonical_name"] for entity in entity_list
                             if entity["system"] == "cu" and entity["level"] == "ward")
    ambiguous_name = next(name for name, count in sorted(old_ward_names.items()) if count > 1)
    example_queries = [
        ("unique_old_ward", {"name": "Phường Bến Nghé", "level": "ward", "as_of": "2025-06-30",
                             "province": "Thành phố Hồ Chí Minh"}),
        ("duplicate_name_without_parent", {"name": ambiguous_name, "level": "ward", "as_of": "2025-06-30"}),
        ("old_system_after_boundary", {"name": "Phường Bến Nghé", "level": "ward", "as_of": "2025-07-01"}),
        ("new_system_before_boundary", {"name": "Phường Sài Gòn", "level": "ward", "as_of": "2025-06-30"}),
        ("unknown_name", {"name": "Đơn vị không tồn tại DACN", "level": "ward", "as_of": "2025-07-01"}),
    ]
    for relation, case in (("A/1-N", "one_to_many"), ("M/M-N", "many_to_many")):
        edge = next(item for item in edges if item["relation"] == relation)
        example_queries.append((case, {
            "name": edge["old_ward"], "level": "ward", "as_of": "2025-06-30",
            "province": edge["old_province"], "district": edge["old_district"],
        }))
    island = non_atomic_transitions[0]
    example_queries.append(("district_to_special_zone", {
        "name": island["old_district"], "level": "district", "as_of": "2025-06-30",
        "province": island["old_province"],
    }))
    examples = []
    for case, query in example_queries:
        kwargs = dict(query)
        kwargs["as_of"] = date.fromisoformat(kwargs["as_of"])
        examples.append({"case": case, "result": lookup(**kwargs)})
    (OUTPUT_V2 / "lookup_examples.json").write_text(
        json.dumps(examples, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # Manifest
    manifest = {
        "version": VERSION,
        "effective_boundary": BOUNDARY,
        "release_status": "PARTIAL_OLD_CODES_UNVERIFIED",
        "build_script_sha256": hashes["build_script"],
        "source_files": {
            "mapping": {"path": str(MAPPING.relative_to(ROOT)), "sha256": hashes["mapping"], "role": "official_mapping_authority"},
            "legacy_candidate": {"path": str(LEGACY.relative_to(ROOT)), "sha256": hashes["legacy_candidate"], "role": "candidate_old_codes_only"},
            "audited_aliases": {"path": str(ALIAS_SOURCE.relative_to(ROOT)), "sha256": hashes["audited_aliases"], "role": "audited_aliases_authority"},
        },
        "counts": {
            "source_rows": len(mapping_rows),
            "atomic_edges": len(edges),
            "non_atomic_transitions": len(non_atomic_transitions),
            "entities": len(entity_list),
            "aliases": len(alias_rows),
            "relations": dict(relation_counts),
            "legacy_join_rows": dict(legacy_match),
        },
        "limitations": [
            "All entity_id values are internal stable IDs, not official government codes.",
            "Old ward codes from third_party are unverified candidate codes; 0 verified official old codes in repo.",
            "No coordinates or geometry polygons are included.",
            "Old valid_from date is unknown; old version valid_to ends on 2025-06-30.",
            "5 island district-to-special-zone transitions are non-atomic and preserved in non_atomic_transitions.csv.",
            "The repository does not document the external publication URL or reuse license of the mapping CSV; verified_source means verified against that CSV only.",
        ],
        "output_sha256": {
            "entities.csv": sha256(OUTPUT_V2 / "entities.csv"),
            "edges.csv": sha256(OUTPUT_V2 / "edges.csv"),
            "aliases.csv": sha256(OUTPUT_V2 / "aliases.csv"),
            "non_atomic_transitions.csv": sha256(OUTPUT_V2 / "non_atomic_transitions.csv"),
            "source_register.csv": sha256(OUTPUT_V2 / "source_register.csv"),
            "coverage_report.json": sha256(OUTPUT_V2 / "coverage_report.json"),
            "lookup_examples.json": sha256(OUTPUT_V2 / "lookup_examples.json"),
        },
    }
    (OUTPUT_V2 / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Build complete. Manifest written to {OUTPUT_V2 / 'manifest.json'}")
    return manifest


def lookup(
    name: str,
    level: str,
    as_of: date,
    system: str | None = None,
    province: str | None = None,
    district: str | None = None,
) -> dict[str, Any]:
    """Query temporal gazetteer v2 with full parent context."""
    entity_rows = read_csv(OUTPUT_V2 / "entities.csv", ENTITY_FIELDS)
    alias_rows = read_csv(OUTPUT_V2 / "aliases.csv", ALIAS_FIELDS)
    edge_rows = read_csv(OUTPUT_V2 / "edges.csv", EDGE_FIELDS)
    non_atomic_rows = read_csv(OUTPUT_V2 / "non_atomic_transitions.csv", NON_ATOMIC_FIELDS)

    target_norm = norm(name)
    matched_ids = {
        row["entity_id"]
        for row in entity_rows
        if row["level"] == level and norm(row["canonical_name"]) == target_norm
    }
    matched_ids.update(
        row["entity_id"]
        for row in alias_rows
        if row["level"] == level and norm(row["alias"]) == target_norm
    )

    by_id = {row["entity_id"]: row for row in entity_rows}
    candidates = []

    for entity_id in sorted(matched_ids):
        entity = by_id[entity_id]
        if system and entity["system"] != system:
            continue
        if entity["valid_from"] and as_of < date.fromisoformat(entity["valid_from"]):
            continue
        if entity["valid_to"] and as_of > date.fromisoformat(entity["valid_to"]):
            continue

        parent = by_id.get(entity["parent_id"])
        ancestor = by_id.get(parent["parent_id"]) if parent else None

        prov_name = ""
        dist_name = ""
        if level == "province":
            prov_name = entity["canonical_name"]
        elif level == "district":
            dist_name = entity["canonical_name"]
            prov_name = parent["canonical_name"] if parent else ""
        elif level == "ward":
            if entity["system"] == "cu":
                dist_name = parent["canonical_name"] if parent else ""
                prov_name = ancestor["canonical_name"] if ancestor else ""
            else:  # moi: 2-tier
                prov_name = parent["canonical_name"] if parent else ""

        if province and norm(province) != norm(prov_name):
            continue
        if district and norm(district) != norm(dist_name):
            continue

        transitions = [
            {
                "new_entity_id": edge["new_entity_id"],
                "new_province": edge["new_province"],
                "new_ward": edge["new_ward"],
                "new_ward_code": edge["new_ward_code"],
                "relation": edge["relation"],
                "merge_form": edge["merge_form"],
                "source_row": edge["source_row"],
                "source_id": edge["source_id"],
                "source_hash": edge["source_hash"],
                "transition_kind": "WARD_EDGE",
            }
            for edge in edge_rows
            if level == "ward" and entity["system"] == "cu" and edge["old_entity_id"] == entity_id
        ]
        transitions.extend({
            "new_entity_id": transition["new_entity_id"],
            "new_province": transition["new_province"],
            "new_ward": transition["new_ward"],
            "new_ward_code": transition["new_ward_code"],
            "relation": transition["relation"],
            "merge_form": transition["merge_form"],
            "source_row": transition["source_row"],
            "source_id": transition["source_id"],
            "source_hash": transition["source_hash"],
            "transition_kind": "DISTRICT_TO_SPECIAL_ZONE",
        } for transition in non_atomic_rows
            if level == "district" and entity["system"] == "cu" and transition["old_entity_id"] == entity_id)

        candidates.append({
            "entity_id": entity["entity_id"],
            "canonical_name": entity["canonical_name"],
            "level": entity["level"],
            "system": entity["system"],
            "province": prov_name,
            "district": dist_name,
            "official_code": entity["official_code"],
            "candidate_code": entity["candidate_code"],
            "code_status": entity["code_status"],
            "valid_from": entity["valid_from"] or "unknown_historical",
            "valid_to": entity["valid_to"] or "ongoing",
            "source_id": entity["source_id"],
            "source_hash": entity["source_hash"],
            "transitions": transitions,
        })

    entity_status = "NO_MATCH" if not candidates else "UNIQUE_ENTITY" if len(candidates) == 1 else "AMBIGUOUS_ENTITY"

    # Target transition status
    target_status = "NO_TRANSITION"
    if candidates and level in {"ward", "district"}:
        all_targets = [t for c in candidates for t in c.get("transitions", [])]
        if not all_targets:
            target_status = "NO_VERIFIED_TARGET"
        elif len(candidates) == 1 and len({t["new_entity_id"] for t in all_targets}) == 1:
            target_status = "UNIQUE_TARGET"
        else:
            target_status = "MULTIPLE_TARGETS"

    return {
        "query": {
            "name": name,
            "level": level,
            "as_of": as_of.isoformat(),
            "system": system,
            "province": province,
            "district": district,
        },
        "entity_status": entity_status,
        "target_status": target_status,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("build")

    query = subparsers.add_parser("lookup")
    query.add_argument("--name", required=True)
    query.add_argument("--level", choices=("province", "district", "ward"), required=True)
    query.add_argument("--as-of", required=True, type=date.fromisoformat)
    query.add_argument("--system", choices=("cu", "moi"))
    query.add_argument("--province")
    query.add_argument("--district")

    args = parser.parse_args()
    if args.command == "build":
        manifest = build()
        print(json.dumps({"status": manifest["release_status"], "counts": manifest["counts"]}, ensure_ascii=False, indent=2))
    elif args.command == "lookup":
        res = lookup(args.name, args.level, args.as_of, args.system, args.province, args.district)
        print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
