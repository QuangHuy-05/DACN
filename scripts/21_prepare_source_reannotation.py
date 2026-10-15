"""Build source-traced, non-gold T0 reannotation packages for frozen tasks."""

from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path

from src.data.span_trace import Component, align_unique, render_components


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/interim/annotation/sprint03"
DEFAULT_OUTPUT = BASE / "reannotation_v2"
FIELDS = ("SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh")
LABELS = set(FIELDS) | {"Ngo/Hem", "ToaNha/CanHo", "MocDinhVi", "HuongDi", "GhiChu", "Khac"}
SYSTEMS = {"cu", "moi", "khong_xac_dinh"}
STRATA = {
    "osm_old_pilot": 24, "osm_new_pilot": 24, "pilot_rare_candidate": 20,
    "osm_old_3tier": 60, "osm_new_2tier": 60, "synthetic_noise": 40,
    "synthetic_missing": 40, "synthetic_hybrid": 32,
}
MAPPING = ROOT / "data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv"
GUIDELINE = ROOT / "docs/sprints/sprint_03/span_11_annotation_guideline.md"
XML = ROOT / "configs/label_studio_span11.xml"
REPLACEMENTS = (
    ("Phường ", "P. "), ("Quận ", "Q. "), ("Thành phố ", "TP. "),
    ("Đường ", "Đ. "), ("Hồ Chí Minh", "HCM"), ("Hà Nội", "HN"),
    ("Xã ", "X. "),
)
RARE_TEMPLATES = {
    "gần cầu Sài Gòn": [("MocDinhVi", "gần cầu Sài Gòn")],
    "cách cầu Sài Gòn 200 m": [("MocDinhVi", "cách cầu Sài Gòn 200 m")],
    "phía trước cầu Sài Gòn": [("MocDinhVi", "phía trước cầu Sài Gòn")],
    "đối diện chợ Bà Chiểu": [("MocDinhVi", "đối diện chợ Bà Chiểu")],
    "bên cạnh chợ Bà Chiểu": [("MocDinhVi", "bên cạnh chợ Bà Chiểu")],
    "gần ngã tư Hàng Xanh": [("MocDinhVi", "gần ngã tư Hàng Xanh")],
    "hướng Bình Thạnh": [("HuongDi", "hướng Bình Thạnh")],
    "đi về hướng Bình Thạnh": [("HuongDi", "đi về hướng Bình Thạnh")],
    "theo hướng Bình Thạnh": [("HuongDi", "theo hướng Bình Thạnh")],
    "rẽ trái": [("HuongDi", "rẽ trái")],
    "rẽ phải": [("HuongDi", "rẽ phải")],
    "đi thẳng": [("HuongDi", "đi thẳng")],
    "Căn A305, tầng 3, Tòa A": [
        ("ToaNha/CanHo", "Căn A305"), ("GhiChu", "tầng 3"), ("ToaNha/CanHo", "Tòa A")],
    "Tòa B, căn 1204": [("ToaNha/CanHo", "Tòa B"), ("ToaNha/CanHo", "căn 1204")],
    "tầng 3, cổng sau": [("GhiChu", "tầng 3"), ("GhiChu", "cổng sau")],
    "lầu 2, lối giao hàng": [("GhiChu", "lầu 2"), ("GhiChu", "lối giao hàng")],
    "Khu phố 4, Phường 7": [("Khac", "Khu phố 4"), ("PhuongXa", "Phường 7")],
    "Ấp 2, Xã Bình Hưng": [("Khac", "Ấp 2"), ("PhuongXa", "Xã Bình Hưng")],
    "Ngõ 42 Phố Trần Bình Trọng": [("Ngo/Hem", "Ngõ 42"), ("TenDuong", "Phố Trần Bình Trọng")],
    "Hẻm 12/3 Đường Nguyễn Xí": [("Ngo/Hem", "Hẻm 12/3"), ("TenDuong", "Đường Nguyễn Xí")],
}


def digest(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(path)
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    digest(path)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        return list(reader)


def read_json(path: Path):
    digest(path)
    return json.loads(path.read_text(encoding="utf-8-sig"))


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def admin_key(value: str) -> str:
    return " ".join(value.strip().split())


def load_mapping() -> tuple[dict, set, set, set, set]:
    rows = read_csv(MAPPING, {
        "Phường/Xã cũ", "Quận/Huyện cũ", "Tỉnh/TP cũ (trước sáp nhập)",
        "Tỉnh/TP mới", "Phường/Xã mới (từ 1/7/2025)",
    })
    edges: dict[tuple[str, str, str], dict[tuple[str, str], list[int]]] = defaultdict(lambda: defaultdict(list))
    old_wards, new_wards, old_provinces, new_provinces = set(), set(), set(), set()
    for line, row in enumerate(rows, start=2):
        old = tuple(admin_key(row[key]) for key in (
            "Tỉnh/TP cũ (trước sáp nhập)", "Quận/Huyện cũ", "Phường/Xã cũ"))
        new = tuple(admin_key(row[key]) for key in (
            "Tỉnh/TP mới", "Phường/Xã mới (từ 1/7/2025)"))
        if all(old) and all(new):
            edges[old][new].append(line)
            old_wards.add(old[2])
            new_wards.add(new[1])
            old_provinces.add(old[0])
            new_provinces.add(new[0])
    return edges, old_wards, new_wards, old_provinces, new_provinces


def source_row(item: dict, cache: dict[Path, list[dict]], hashes: dict[str, str]) -> dict:
    path = ROOT / item["source_ref"]
    if path not in cache:
        cache[path] = read_csv(path, set(FIELDS)) if item["stratum"] != "pilot_rare_candidate" else []
        hashes[relative(path)] = digest(path)
    if hashes[relative(path)] != item["source_file_sha256"]:
        raise ValueError(f"{item['sample_id']}: source hash changed: {path}")
    number = int(item["source_row"])
    if item["stratum"] == "pilot_rare_candidate":
        seeds = read_json(path)
        return seeds[number - 1]
    if number < 2 or number - 2 >= len(cache[path]):
        raise ValueError(f"{item['sample_id']}: missing source row {number}")
    return cache[path][number - 2]


def unique_target(edges: dict, old_key: tuple[str, str, str]):
    targets = edges.get(old_key, {})
    if len(targets) != 1:
        return None
    target, lines = next(iter(targets.items()))
    return target, lines


def replay_noise(source: dict, locked: str) -> tuple[list[Component], str | None]:
    """Infer only operations the frozen batch-02 generator could have applied."""
    original = [Component(field, source[field], source[field], "cu") for field in FIELDS if source[field]]
    if render_components(original)[0] != source["ChuoiDiaChi"]:
        return [], "source_clean_render_mismatch"
    matches = {}
    for mask in range(1 << len(REPLACEMENTS)):
        transformed = list(original)
        operations = []
        for index, (before, after) in enumerate(REPLACEMENTS):
            if not (mask & (1 << index)):
                continue
            rendered = render_components(transformed)[0]
            if before not in rendered:
                continue
            first = rendered.index(before)
            offsets = render_components(transformed)[1]
            owner = next((i for i, entry in enumerate(offsets)
                          if entry["start"] <= first and first + len(before) <= entry["end"]), None)
            if owner is None:
                continue
            part = transformed[owner]
            transformed[owner] = replace(part, surface=part.surface.replace(before, after, 1),
                                         transformation=part.transformation + f"|{before}->{after}")
            operations.append((before, after))
        rendered, offsets = render_components(transformed)
        if rendered == locked:
            key = tuple(part.surface for part in transformed)
            matches[key] = transformed
            continue
        if len(rendered) != len(locked):
            continue
        differences = [i for i, (left, right) in enumerate(zip(rendered, locked)) if left != right]
        if len(differences) != 1:
            continue
        position = differences[0]
        if rendered[position].lower() != locked[position]:
            continue
        owner = next((i for i, entry in enumerate(offsets)
                      if entry["start"] <= position < entry["end"]), None)
        if owner is None:
            continue
        part = transformed[owner]
        local = position - offsets[owner]["start"]
        surface = part.surface[:local] + locked[position] + part.surface[local + 1:]
        transformed[owner] = replace(part, surface=surface,
                                     transformation=part.transformation + "|lowercase_one_character")
        if render_components(transformed)[0] == locked:
            key = tuple(part.surface for part in transformed)
            matches[key] = transformed
    if len(matches) != 1:
        return [], "noise_replay_ambiguous_or_unmatched"
    return next(iter(matches.values())), None


def build_components(item: dict, source: dict, edges: dict) -> tuple[list[Component], dict, str | None]:
    stratum = item["stratum"]
    evidence = {"source_ref": item["source_ref"], "source_row": item["source_row"],
                "source_file_sha256": item["source_file_sha256"], "derivation": item["derivation"]}
    if "OSM_ID" in source:
        evidence["osm_object"] = {"type": source.get("OSM_Type"), "id": source.get("OSM_ID")}
    if stratum == "pilot_rare_candidate":
        if source.get("text") != item["text"] or item["text"] not in RARE_TEMPLATES:
            return [], evidence, "rare_seed_has_no_verified_template"
        return [Component(field, surface, surface, "synthetic_seed", "explicit_seed_template")
                for field, surface in RARE_TEMPLATES[item["text"]]], evidence, None
    old_key = tuple(admin_key(source.get(key, "")) for key in ("TinhThanh", "QuanHuyen", "PhuongXa"))
    evidence["old_admin_key"] = list(old_key)
    if stratum == "synthetic_noise":
        components, reason = replay_noise(source, item["text"])
        return components, evidence, reason
    if stratum == "synthetic_missing":
        choices = []
        for dropped in ("QuanHuyen", "SoNha", "PhuongXa"):
            parts = [Component(field, source[field], source[field], "cu", "identity")
                     for field in FIELDS if field != dropped and source[field]]
            if render_components(parts)[0] == item["text"]:
                choices.append((dropped, parts))
        if len(choices) != 1:
            return [], evidence, "missing_field_replay_ambiguous_or_unmatched"
        evidence["dropped_field"] = choices[0][0]
        return choices[0][1], evidence, None
    if stratum in {"osm_new_2tier", "synthetic_hybrid", "osm_new_pilot"}:
        observed_new = (stratum == "osm_new_pilot" and not source.get("QuanHuyen", "").strip()
                        and (admin_key(source["TinhThanh"]), admin_key(source["PhuongXa"]))
                        in {(target) for targets in edges.values() for target in targets})
        if observed_new:
            values = {field: source[field] for field in ("SoNha", "TenDuong", "PhuongXa", "TinhThanh")}
            systems = {field: "moi" for field in values}
            evidence["mapping_evidence"] = "observed_current_unit_in_source"
        else:
            resolved = unique_target(edges, old_key)
            if resolved is None:
                return [], evidence, "old_admin_key_has_no_unique_verified_target"
            (new_province, new_ward), lines = resolved
            evidence["mapping_evidence"] = {"source_ref": relative(MAPPING), "rows": lines,
                                            "new_admin_key": [new_province, new_ward],
                                            "relation": "unique_target_for_full_old_key"}
            values = {"SoNha": source["SoNha"], "TenDuong": source["TenDuong"],
                      "PhuongXa": new_ward, "TinhThanh": new_province}
            systems = {"SoNha": "cu", "TenDuong": "cu", "PhuongXa": "moi", "TinhThanh": "moi"}
            if stratum == "synthetic_hybrid":
                values["QuanHuyen"] = source["QuanHuyen"]
                values["TinhThanh"] = source["TinhThanh"]
                systems["QuanHuyen"] = systems["TinhThanh"] = "cu"
        return [Component(field, values[field],
                          source[field] if field in {"PhuongXa", "TinhThanh"} and not observed_new else values[field],
                          systems[field],
                          "derived_unique_mapping" if systems[field] == "moi" and not observed_new else "identity")
                for field in FIELDS if field in values and values[field]], evidence, None
    return [Component(field, source[field], source[field], "cu")
            for field in FIELDS if source[field]], evidence, None


def span_system(component: Component, name_sets: tuple[set, set, set, set]) -> tuple[str, str | None]:
    if component.field in {"SoNha", "TenDuong"}:
        return "khong_xac_dinh", None
    if component.field == "QuanHuyen":
        return "cu", None
    if component.field not in {"PhuongXa", "TinhThanh"}:
        return "khong_xac_dinh", None
    old_wards, new_wards, old_provinces, new_provinces = name_sets
    old_names, new_names = (old_wards, new_wards) if component.field == "PhuongXa" else (old_provinces, new_provinces)
    # Source provenance cannot resolve an identical visible name across periods.
    if component.surface != component.source_value and component.transformation != "derived_unique_mapping":
        return "khong_xac_dinh", "transformed_admin_surface"
    if component.construction_system == "synthetic_seed":
        return "khong_xac_dinh", "seed_has_no_admin_identity"
    value = admin_key(component.surface)
    if value in old_names and value in new_names:
        return "khong_xac_dinh", "name_used_in_both_periods"
    if component.construction_system == "cu" and value in old_names and value not in new_names:
        return "cu", None
    if component.construction_system == "moi" and value in new_names and value not in old_names:
        return "moi", None
    return "khong_xac_dinh", "admin_period_not_visible_or_unverified"


def load_inputs() -> tuple[list[dict], list[dict], dict[str, str], dict[str, str]]:
    pilot_queue = [row for row in read_csv(BASE / "annotation_queue_batch01.csv", {
        "sample_id", "text", "source_ref", "source_row", "source_file_sha256", "group_id", "planned_role", "stratum"})
        if row["planned_role"] == "pilot_train_pool"]
    batch_queue = read_csv(BASE / "annotation_queue_batch02_train_dev.csv", {
        "sample_id", "text", "source_ref", "source_row", "source_file_sha256", "group_id", "planned_split", "stratum"})
    if len(pilot_queue) != 68 or len(batch_queue) != 232:
        raise ValueError(f"Frozen queue size changed: {len(pilot_queue)} pilot, {len(batch_queue)} batch")
    test_ids = {row["sample_id"] for row in read_json(BASE / "test_hold_manifest_v1.json")["samples"]}
    vqa_ids = {row["sample_id"] for row in read_csv(BASE / "annotation_queue_batch01.csv", {"sample_id", "planned_role"})
               if row["planned_role"] == "external_test_hold"}
    all_rows = pilot_queue + batch_queue
    ids = [row["sample_id"] for row in all_rows]
    if len(ids) != len(set(ids)) or set(ids) & (test_ids | vqa_ids):
        raise ValueError("Duplicate, test, or VQA ID in frozen task queues")
    if dict(Counter(row["stratum"] for row in all_rows)) != STRATA:
        raise ValueError("Frozen stratum counts changed")
    splits = {row["sample_id"]: row for row in read_csv(
        BASE / "split_preflight_v1/train_dev_split_assignments.csv", {"sample_id", "split", "source_group"})}
    for row in all_rows:
        assignment = splits.get(row["sample_id"])
        if (assignment is None or assignment["source_group"] != row["group_id"] or
                assignment["split"] not in {"train", "dev"} or
                (row.get("planned_split") and row["planned_split"] != assignment["split"])):
            raise ValueError(f"Split/group mismatch: {row['sample_id']}")
    for rows, path in ((pilot_queue, BASE / "label_studio_pilot_import.json"),
                       (batch_queue, BASE / "label_studio_batch02_import.json")):
        tasks = read_json(path)
        expected = [{"data": {"sample_id": row["sample_id"], "text": row["text"]}} for row in rows]
        if tasks != expected:
            raise ValueError(f"Import differs from frozen queue or exposes extra data: {path}")
    return pilot_queue, batch_queue, {key: row["split"] for key, row in splits.items()}, {
        "test": len(test_ids), "vqa_hold": len(vqa_ids)}


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Version directory is not empty: {output}")
    pilot, batch, splits, hold_counts = load_inputs()
    preflight = read_json(BASE / "split_preflight_v1/split_audit_report.json")
    pending_pairs = preflight["near_duplicates_count"]
    edges, *sets = load_mapping()
    source_cache: dict[Path, list[dict]] = {}
    hashes = {}
    candidates = {"pilot": [], "batch": []}
    trace, review = [], []
    coverage = {name: Counter() for name in STRATA}
    for package, rows in (("pilot", pilot), ("batch", batch)):
        for item in rows:
            stratum, text, sample_id = item["stratum"], item["text"], item["sample_id"]
            stats = coverage[stratum]
            stats["samples"] += 1
            source = source_row(item, source_cache, hashes)
            components, evidence, reason = build_components(item, source, edges)
            placements = []
            offset_method = "render_join"
            if reason is None:
                if stratum == "pilot_rare_candidate":
                    placements, reason = align_unique(text, components)
                    offset_method = "ordered_unique_seed_template"
                else:
                    rendered, placements = render_components(components)
                    if rendered != text:
                        # Only observed OSM rows may use ordered matching when the
                        # historical render differs; derived text needs exact replay.
                        if stratum in {"osm_old_pilot", "osm_old_3tier"}:
                            placements, reason = align_unique(text, components)
                            offset_method = "ordered_unique_source_alignment"
                        else:
                            placements, reason = [], "locked_text_replay_mismatch"
            spans, flags = [], set()
            boundary_abstentions = 0
            if reason:
                stats["abstained_components"] += max(1, len(components))
                review.append({"sample_id": sample_id, "stratum": stratum, "start": "", "end": "",
                               "field": "", "reason": reason, "source_ref": item["source_ref"],
                               "source_row": item["source_row"], "priority": "high"})
                trace.append({"sample_id": sample_id, "group_id": item["group_id"],
                              "planned_split": splits[sample_id], "stratum": stratum,
                              "match_status": "abstain", "abstain_reason": reason,
                              "evidence": evidence, "components": [
                                  {"field": part.field, "surface": part.surface,
                                   "source_value": part.source_value, "construction_system": part.construction_system,
                                   "transformation": part.transformation, "start": None, "end": None,
                                   "match_status": "abstain", "abstain_reason": reason}
                                  for part in components]})
            else:
                traced = []
                for placed in placements:
                    component = placed["component"]
                    start, end = placed["start"], placed["end"]
                    if text[start:end] != component.surface or component.field not in LABELS:
                        raise AssertionError(f"{sample_id}: invalid component offset/label")
                    # Match the export QA boundary rule; a source field can contain
                    # brackets that require a human to choose separate literal spans.
                    surface = component.surface
                    if (surface[0].isspace() or surface[-1].isspace()
                            or surface[0] in ",;()" or surface[-1] in ",;()"):
                        boundary_abstentions += 1
                        stats["abstained_components"] += 1
                        flags.add("ambiguous_label")
                        review.append({"sample_id": sample_id, "stratum": stratum,
                                       "start": start, "end": end, "field": component.field,
                                       "reason": "source_component_requires_boundary_review",
                                       "source_ref": item["source_ref"], "source_row": item["source_row"],
                                       "priority": "high"})
                        traced.append({"field": component.field, "surface": surface,
                                       "source_value": component.source_value,
                                       "construction_system": component.construction_system,
                                       "transformation": component.transformation,
                                       "start": start, "end": end, "match_status": "abstain",
                                       "offset_method": offset_method, "evidence": evidence,
                                       "abstain_reason": "source_component_requires_boundary_review"})
                        continue
                    system, ambiguity = span_system(component, tuple(sets))
                    span = {"start": start, "end": end, "text": component.surface,
                            "label": component.field, "system": system}
                    spans.append(span)
                    traced.append({"field": component.field, "surface": component.surface,
                                   "source_value": component.source_value,
                                   "source_key": evidence.get("old_admin_key"),
                                   "entity_id_if_verified": None,
                                   "construction_system": component.construction_system,
                                   "span_system_candidate": system,
                                   "transformation": component.transformation,
                                   "character_alignment": [
                                       {"operation": tag, "source_start": left_start,
                                        "source_end": left_end, "surface_start": right_start,
                                        "surface_end": right_end}
                                       for tag, left_start, left_end, right_start, right_end in
                                       difflib.SequenceMatcher(None, component.source_value,
                                                               component.surface, autojunk=False).get_opcodes()
                                   ] if stratum == "synthetic_noise" else None,
                                   "offset_method": offset_method,
                                   "start": start, "end": end, "match_status": "exact",
                                   "evidence": evidence, "abstain_reason": None})
                    if ambiguity:
                        stats["temporally_undetermined_spans"] += 1
                        flags.add("temporal_ambiguity")
                        review.append({"sample_id": sample_id, "stratum": stratum,
                                       "start": start, "end": end, "field": component.field,
                                       "reason": ambiguity, "source_ref": item["source_ref"],
                                       "source_row": item["source_row"], "priority": "medium"})
                if evidence.get("dropped_field"):
                    traced.append({"field": evidence["dropped_field"], "surface": "", "start": None,
                                   "end": None, "match_status": "absent_by_generator",
                                   "transformation": "drop_field", "evidence": evidence,
                                   "abstain_reason": None})
                    stats["dropped_fields"] += 1
                trace.append({"sample_id": sample_id, "group_id": item["group_id"],
                              "planned_split": splits[sample_id], "stratum": stratum,
                              "match_status": ("partially_abstained" if boundary_abstentions else
                                               "replayed" if stratum != "pilot_rare_candidate" else "seed_template"),
                              "abstain_reason": None, "evidence": evidence, "components": traced})
                stats["candidate_spans"] += len(spans)
                stats["tasks_with_spans"] += bool(spans)
            systems = {span["system"] for span in spans}
            address_system = None
            if "cu" in systems and "moi" in systems:
                address_system = "Lai"
            elif "cu" in systems and any(span["label"] == "QuanHuyen" for span in spans):
                address_system = "cu"
            elif "moi" in systems and "cu" not in systems:
                address_system = "moi"
            # A hybrid T1 claim requires both a visibly new ward and an old district.
            if stratum == "synthetic_hybrid" and not (
                any(span["label"] == "PhuongXa" and span["system"] == "moi" for span in spans)
                and any(span["label"] == "QuanHuyen" and span["system"] == "cu" for span in spans)
            ):
                address_system = None
                flags.add("temporal_ambiguity")
                review.append({"sample_id": sample_id, "stratum": stratum, "start": "", "end": "",
                               "field": "address_system", "reason": "hybrid_T1_not_visible",
                               "source_ref": item["source_ref"], "source_row": item["source_row"], "priority": "medium"})
            stats["t1_proposed"] += address_system is not None
            stats["abstained_tasks"] += bool(reason)
            stats["partially_abstained_tasks"] += bool(boundary_abstentions)
            notes = []
            if "temporal_ambiguity" in flags:
                notes.append("Check visible administrative period.")
            if boundary_abstentions:
                notes.append("Add the skipped source component after reviewing its span boundaries.")
            candidates[package].append({"sample_id": sample_id, "text": text,
                "status": "candidate_not_gold", "spans": spans,
                "address_system": address_system, "review_flags": sorted(flags),
                "review_note": " ".join(notes)})
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "pilot68_import.json", [{"data": {"sample_id": r["sample_id"], "text": r["text"]}} for r in pilot])
    write_json(output / "batch232_import.json", [{"data": {"sample_id": r["sample_id"], "text": r["text"]}} for r in batch])
    write_json(output / "pilot68_candidates.json", candidates["pilot"])
    write_json(output / "batch232_candidates.json", candidates["batch"])
    with (output / "trace.jsonl").open("w", encoding="utf-8") as handle:
        for row in trace:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (output / "manual_review_queue.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("sample_id", "stratum", "start", "end", "field",
                                                      "reason", "source_ref", "source_row", "priority"))
        writer.writeheader()
        writer.writerows(review)
    for row in review:
        coverage[row["stratum"]]["manual_review_items"] += 1
    write_json(output / "coverage_report.json", {
        "status": "candidate_not_gold", "strata": {
            key: {metric: value[metric] for metric in (
                "samples", "tasks_with_spans", "candidate_spans", "abstained_tasks",
                "abstained_components", "partially_abstained_tasks", "dropped_fields", "temporally_undetermined_spans",
                "t1_proposed", "manual_review_items")}
            for key, value in coverage.items()},
        "manual_review_items": len(review),
        "review_reasons": dict(Counter(row["reason"] for row in review)),
        "hold_counts": hold_counts, "near_duplicate_pairs_pending": pending_pairs})
    input_paths = [BASE / name for name in (
        "annotation_queue_batch01.csv", "annotation_queue_batch02_train_dev.csv",
        "label_studio_pilot_import.json", "label_studio_batch02_import.json",
        "test_hold_manifest_v1.json", "annotation_batch02_manifest.json",
        "split_preflight_v1/train_dev_split_assignments.csv",
        "split_preflight_v1/split_audit_report.json")]
    input_paths += [MAPPING, GUIDELINE, XML, ROOT / "configs/span11_rare_seed_examples.json",
                    ROOT / "docs/sprints/sprint_03/annotation_batch01_manifest.json",
                    ROOT / "docs/sprints/sprint_03/t0_corpus_split_protocol_v1.md",
                    BASE / "split_preflight_v1/source_parent_manifest.csv",
                    ROOT / "src/data/span_trace.py", Path(__file__)]
    input_hashes = {relative(path): digest(path) for path in input_paths}
    input_hashes.update(hashes)
    outputs = {path.name: digest(path) for path in output.iterdir() if path.is_file()}
    write_json(output / "generation_manifest.json", {
        "version": "s3_span11_source_trace_v2_not_gold", "seed": 42,
        "guideline_version": "s3-span-v1.1", "status": "candidate_not_gold",
        "input_sha256": input_hashes, "output_sha256": outputs,
        "sample_counts": {"pilot": len(pilot), "batch02": len(batch)},
        "strata_counts": dict(Counter(row["stratum"] for row in pilot + batch)),
        "limitations": ["Noise operations are inferred from the locked surface; original RNG decisions were not stored.",
                        "Temporal labels require visible period evidence and may remain undetermined.",
                        f"Near-duplicate split review remains pending ({pending_pairs} pairs)."]})
    print(json.dumps({"output_dir": str(output), "coverage": {k: dict(v) for k, v in coverage.items()},
                      "manual_review_items": len(review)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
