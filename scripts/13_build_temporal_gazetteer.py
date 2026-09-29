"""Build a provenance-aware, partial 2025 temporal administrative gazetteer.

Only the repository mapping CSV defines old-to-new edges. Third-party legacy
codes are candidate attributes and never become verified official IDs here.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAPPING = ROOT / "data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv"
LEGACY = ROOT / "third_party/vietnamadminunits/data/interim/legacy_63-province-10040-ward_with_location_and_key.csv"
ALIAS_SOURCE = ROOT / "src/data/administrative_alias.py"
OUTPUT = ROOT / "data/processed/gazetteer/s3_v1"
VERSION = "s3-gazetteer-v1-partial"
BOUNDARY = "2025-07-01"
ENTITY_FIELDS = (
    "entity_id", "level", "system", "canonical_name", "parent_id",
    "official_code", "candidate_code", "candidate_code_source_id",
    "candidate_code_source_hash", "code_status", "valid_from",
    "valid_to", "source_id", "source_hash", "status",
)
EDGE_FIELDS = (
    "old_entity_id", "new_entity_id", "old_province", "old_district",
    "old_ward", "new_province", "new_ward", "new_ward_code",
    "relation", "merge_form", "source_row", "source_id", "source_hash",
)
ALIAS_FIELDS = ("entity_id", "alias", "system", "level", "source_id", "source_hash")
MAPPING_COLUMNS = (
    "Phường/Xã cũ", "Quận/Huyện cũ", "Tỉnh/TP cũ (trước sáp nhập)",
    "Tỉnh/TP mới", "Phường/Xã mới (từ 1/7/2025)",
    "Mã phường/xã mới", "Hình thức sáp nhập",
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
    # Parse literal tables without importing the data pipeline or dependencies.
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
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build() -> dict:
    mapping_rows = read_csv(MAPPING, MAPPING_COLUMNS)
    legacy_rows = read_csv(LEGACY, ("province", "district", "ward", "provinceCode", "districtCode", "wardCode"))
    hashes = {"mapping": sha256(MAPPING), "legacy_candidate": sha256(LEGACY),
              "audited_aliases": sha256(ALIAS_SOURCE), "build_script": sha256(Path(__file__))}
    legacy_index = defaultdict(list)
    for row in legacy_rows:
        key = tuple(norm(row[column]) for column in ("province", "district", "ward"))
        legacy_index[key].append(row)

    entities = {}
    edges = []
    old_targets = defaultdict(set)
    new_sources = defaultdict(set)
    legacy_match = Counter()
    skipped_rows = []
    source_id = "mapping"

    def add_entity(system: str, level: str, province: str, district: str,
                   name: str, parent_id: str, official_code: str = "") -> str:
        entity_id = stable_id(system, level, province, district, name)
        row = {
            "entity_id": entity_id, "level": level, "system": system,
            "canonical_name": name, "parent_id": parent_id,
            "official_code": official_code, "candidate_code": "",
            "candidate_code_source_id": "", "candidate_code_source_hash": "",
            "code_status": "verified_source" if official_code else "unverified_missing",
            "valid_from": BOUNDARY if system == "moi" else "",
            "valid_to": "" if system == "moi" else "2025-06-30",
            "source_id": source_id, "source_hash": hashes["mapping"],
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
        if not all((old_district, old_province, new_ward, new_province, new_code)):
            skipped_rows.append({"source_row": source_row, "reason": "missing_required_unit_or_new_code"})
            continue
        if not old_ward:
            # District-only island conversion has no old ward key; retain its
            # new unit, but never fabricate an atomic old-ward edge.
            np = add_entity("moi", "province", new_province, "", new_province, "")
            add_entity("moi", "ward", new_province, "", new_ward, np, new_code)
            skipped_rows.append({"source_row": source_row, "reason": "no_old_ward_district_level_transition"})
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
            "old_entity_id": ow, "new_entity_id": nw,
            "old_province": old_province, "old_district": old_district,
            "old_ward": old_ward, "new_province": new_province,
            "new_ward": new_ward, "new_ward_code": new_code,
            "relation": "", "merge_form": row["Hình thức sáp nhập"].strip(),
            "source_row": source_row, "source_id": source_id,
            "source_hash": hashes["mapping"],
        }
        edges.append(edge)
        old_targets[ow].add(nw)
        new_sources[nw].add(ow)

    # A relation is a property of both graph degrees, never a name heuristic.
    for edge in edges:
        out_degree = len(old_targets[edge["old_entity_id"]])
        in_degree = len(new_sources[edge["new_entity_id"]])
        edge["relation"] = ("C/1-1" if out_degree == in_degree == 1 else
                            "A/1-N" if out_degree > 1 and in_degree == 1 else
                            "B/N-1" if out_degree == 1 and in_degree > 1 else "M/M-N")

    aliases = []
    names = defaultdict(list)
    for entity in entities.values():
        names[(entity["level"], norm(entity["canonical_name"]))].append(entity)
    for table, level in (("PROVINCE_ALIASES", "province"),
                         ("DISTRICT_ALIASES", "district"), ("WARD_ALIASES", "ward")):
        for alias, canonical in audited_aliases()[table].items():
            for entity in names.get((level, norm(canonical)), []):
                if norm(alias) == norm(canonical):
                    continue
                aliases.append({
                    "entity_id": entity["entity_id"], "alias": alias,
                    "system": entity["system"], "level": level,
                    "source_id": "audited_aliases", "source_hash": hashes["audited_aliases"],
                })
    aliases = list({(row["entity_id"], norm(row["alias"])): row for row in aliases}.values())

    OUTPUT.mkdir(parents=True, exist_ok=True)
    entity_rows = sorted(entities.values(), key=lambda row: row["entity_id"])
    edge_rows = sorted(edges, key=lambda row: (row["old_entity_id"], row["new_entity_id"], row["source_row"]))
    alias_rows = sorted(aliases, key=lambda row: (row["entity_id"], norm(row["alias"])))
    write_csv(OUTPUT / "entities.csv", ENTITY_FIELDS, entity_rows)
    write_csv(OUTPUT / "edges.csv", EDGE_FIELDS, edge_rows)
    write_csv(OUTPUT / "aliases.csv", ALIAS_FIELDS, alias_rows)
    unique_old_wards = {e["entity_id"] for e in entity_rows if e["system"] == "cu" and e["level"] == "ward"}
    new_code_index = defaultdict(set)
    for entity in entity_rows:
        if entity["system"] == "moi" and entity["level"] == "ward":
            new_code_index[entity["official_code"]].add(entity["entity_id"])
    if any(len(ids) > 1 for ids in new_code_index.values()):
        raise ValueError("One new ward code points to multiple named entities")
    manifest = {
        "version": VERSION, "effective_boundary": BOUNDARY,
        "build_script_sha256": hashes["build_script"],
        "source_files": {
            "mapping": {"path": MAPPING.relative_to(ROOT).as_posix(), "sha256": hashes["mapping"], "role": "only_authority_for_edges_and_new_ward_codes"},
            "legacy_candidate": {"path": LEGACY.relative_to(ROOT).as_posix(), "sha256": hashes["legacy_candidate"], "role": "unverified_candidate_old_codes_only"},
            "audited_aliases": {"path": ALIAS_SOURCE.relative_to(ROOT).as_posix(), "sha256": hashes["audited_aliases"], "role": "audited_spelling_aliases_only"},
        },
        "counts": {
            "source_rows": len(mapping_rows), "usable_atomic_edges": len(edge_rows),
            "skipped_rows": len(skipped_rows), "entities": len(entity_rows),
            "old_wards": len(unique_old_wards), "new_wards": len(new_code_index),
            "aliases": len(alias_rows), "relations": dict(Counter(e["relation"] for e in edge_rows)),
            "old_ward_candidate_codes": sum(bool(e["candidate_code"]) for e in entity_rows if e["system"] == "cu" and e["level"] == "ward"),
            "old_ward_missing_verified_codes": len(unique_old_wards),
            "legacy_join_rows": dict(legacy_match),
        },
        "limitations": [
            "All entity_id values are internal stable IDs, not government codes.",
            "Old codes from third_party are candidate attributes until cross-checked with an authoritative source.",
            "No coordinates or geometry are included; ambiguous names and multiple targets require context.",
            "The old valid_from date is unknown; the old version ends on 2025-06-30.",
        ],
        "skipped_mapping_rows": skipped_rows,
        "output_sha256": {name: sha256(OUTPUT / name) for name in ("entities.csv", "edges.csv", "aliases.csv")},
    }
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def lookup(name: str, level: str, as_of: date, system: str | None, province: str | None) -> dict:
    entity_rows = read_csv(OUTPUT / "entities.csv", ENTITY_FIELDS)
    alias_rows = read_csv(OUTPUT / "aliases.csv", ALIAS_FIELDS)
    edge_rows = read_csv(OUTPUT / "edges.csv", EDGE_FIELDS)
    matched_ids = {row["entity_id"] for row in entity_rows if row["level"] == level and norm(row["canonical_name"]) == norm(name)}
    matched_ids.update(row["entity_id"] for row in alias_rows if row["level"] == level and norm(row["alias"]) == norm(name))
    by_id = {row["entity_id"]: row for row in entity_rows}
    parent_map = by_id
    candidates = []
    for entity_id in sorted(matched_ids):
        entity = by_id[entity_id]
        if system and entity["system"] != system:
            continue
        if entity["valid_from"] and as_of < date.fromisoformat(entity["valid_from"]):
            continue
        if entity["valid_to"] and as_of > date.fromisoformat(entity["valid_to"]):
            continue
        parent = parent_map.get(entity["parent_id"])
        ancestor = parent_map.get(parent["parent_id"]) if parent else None
        province_name = (ancestor or parent or entity)["canonical_name"] if level != "province" else entity["canonical_name"]
        if province and norm(province) != norm(province_name):
            continue
        transitions = [
            {"new_entity_id": edge["new_entity_id"], "relation": edge["relation"],
             "source_row": edge["source_row"], "source_hash": edge["source_hash"]}
            for edge in edge_rows if level == "ward" and entity["system"] == "cu"
            and edge["old_entity_id"] == entity_id
        ]
        candidates.append({**entity, "province": province_name,
                           "transition_candidates": transitions})
    return {
        "query": {"name": name, "level": level, "as_of": as_of.isoformat(), "system": system, "province": province},
        "status": "NO_MATCH" if not candidates else "UNIQUE" if len(candidates) == 1 else "AMBIGUOUS",
        "candidates": candidates,
        "note": "UNIQUE means one indexed candidate, not that an unverified candidate_code is official.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("build")
    query = subparsers.add_parser("lookup")
    query.add_argument("--name", required=True)
    query.add_argument("--level", choices=("province", "district", "ward"), required=True)
    query.add_argument("--as-of", required=True, type=date.fromisoformat)
    query.add_argument("--system", choices=("cu", "moi"))
    query.add_argument("--province")
    args = parser.parse_args()
    result = build() if args.command == "build" else lookup(args.name, args.level, args.as_of, args.system, args.province)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
