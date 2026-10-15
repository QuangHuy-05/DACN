"""G2-6: feasibility audit of the data behind four Group 1 gaps (E2, T2 type A/C, landmark labels, real `Lai`).

Run from the repository root in the main runtime (``~/.venv_dacn``):

    python -m scripts.74_audit_data_feasibility --out-dir data/processed/evaluation/sprint04/data_feasibility_20261016_v1

Read-only over existing data: nothing is collected, no model is run, no gold is created and no pair is added to a
corpus.  The output directory must not exist (exit code 3).  A missing input or a gazetteer hash mismatch exits 2.

Administrative rules kept explicit (AGENTS.md section 6):

* an old unit is the full key province + district + ward, normalised through ``administrative_mapping`` and the
  verified aliases of ``administrative_alias``; no alias is invented here;
* an OSM diff row is evidence only when its house number and street are unchanged against the full old snapshot, its
  old key resolves to a source edge and its observed new target is an edge of that old unit;
* a pair derived from the snapshot is allowed only when the old key has exactly one target (B or C), never A or M.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import pandas as pd  # noqa: E402  (after sys.path so the script also runs directly)

from src.data.administrative_alias import normalize_diff_record  # noqa: E402
from src.data.administrative_mapping import (  # noqa: E402
    clean_value, load_administrative_mapping, province_key, unit_key,
)
from src.data.synthetic.bidirectional import _new_target_from_diff, generate_bidirectional_pairs  # noqa: E402
from src.evaluation.leak_guard import admin_group_key, normalize_for_overlap  # noqa: E402
from src.evaluation.t2_lookup import T2Table  # noqa: E402

SCRIPT_VERSION = "data-feasibility-g2-6-v1"
DEFAULT_OUT = Path("data/processed/evaluation/sprint04/data_feasibility_20261016_v3")

MAPPING_CSV = Path("data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv")
PAIRS = Path("data/processed/osm/osm_real_bidirectional_pairs.csv")
DATA07 = Path("data/processed/benchmark/07_bidirectional_pairs_verified.csv")
GAZETTEER_DIR = Path("data/processed/gazetteer/s3_v2")
GAZETTEER_ACTIVE_EDGES = Path("data/processed/gazetteer/s3_v4_nso_dual_snapshot_release2/edges.csv")
SNAPSHOT_FULL = Path("data/interim/osm/osm_old_snapshot_full.csv")
SNAPSHOT_BALANCED = Path("data/interim/osm/osm_old_snapshot_20250630.csv")
SOURCE_REGISTER = Path("configs/annotation/sprint04/source_register_v1.csv")
DECISION_LOG = Path("data/interim/annotation/sprint04/decision_log_20261013_v2/source_use_decisions.csv")
TB243_MANIFEST = Path("data/interim/annotation/sprint04/source_tb243_20261013_v1/source_manifest.json")
CORPUS_DIR = Path("data/processed/annotation/sprint03/corpus_v1_release2")
CORPUS_FILES = {"train": "train.jsonl", "dev": "dev.jsonl", "test": "test_benchmark_t0.jsonl"}

SOURCE_FILES = (
    "scripts/74_audit_data_feasibility.py", "src/evaluation/t2_lookup.py", "src/evaluation/leak_guard.py",
    "src/data/administrative_mapping.py", "src/data/administrative_alias.py",
    "src/data/synthetic/bidirectional.py",
)

PAIRS_COLUMNS = (
    "OSM_Type", "OSM_ID", "SoNha", "TenDuong", "PhuongXa_Cu", "QuanHuyen_Cu", "TinhThanh_Cu", "DiaChi_Cu",
    "PhuongXa_Moi", "QuanHuyen_Moi", "TinhThanh_Moi", "DiaChi_Moi", "HinhHocCoDuLieu", "HinhHocThayDoi", "Nguon",
)
DATA07_COLUMNS = ("ID_Node", "DiaChi_Cu", "DiaChi_Moi", "LoaiAnhXa", "QuanHe", "HinhThucSapNhap",
                  "MaPhuongXaMoi", "Nguon")
SNAPSHOT_COLUMNS = ("OSM_Type", "OSM_ID", "SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh")
REGISTER_COLUMNS = (
    "source_id", "publisher", "candidate_t0_labels", "candidate_t1_review", "annotation_clearance",
    "collected_sample_count", "annotation_ready_sample_count",
)
DECISION_COLUMNS = ("source_key", "local_research", "annotation", "cloud_upload", "redistribution", "pilot_samples")

# Register source_id -> decision-log source_key (the log renames some sources).
REGISTER_TO_DECISION_KEY = {
    "S4_SRC_UEH_CAMPUS": "ueh_campus",
    "S4_SRC_HANOI_TB729": "hanoi_tb729",
    "S4_SRC_QHKT_CURRENT": "qhkt_current",
    "S4_SRC_QHKT_2024": "qhkt_notice_2024",
    "S4_SRC_UEH_EVENT": "ueh_event",
    "S4_SRC_TUDU_GUIDE": "tudu_home",
    "S4_SRC_OSM_FALLBACK": "osm_copyright",
}
# Label status: rights exist but no sample has been labelled, so it is NOT the threshold-based RUNNABLE_NOW.
RIGHTS_OK = "RIGHTS_OK_SUPPORT_UNMEASURED"
LANDMARK_LABELS = ("MocDinhVi", "HuongDi", "GhiChu", "ToaNha/CanHo")

# Row statuses, in the order the Data 07 generator applies its filters.
ST_NO_SNAPSHOT = "NO_SNAPSHOT_RECORD"
ST_STREET_CHANGED = "STREET_OR_HOUSENUMBER_CHANGED"
ST_NEW_UNRESOLVED = "NEW_TARGET_UNRESOLVED"
ST_OLD_UNRESOLVED = "OLD_KEY_NOT_IN_SOURCE"
ST_NOT_EDGE = "OBSERVED_TARGET_NOT_AN_EDGE"
ST_ELIGIBLE = "ELIGIBLE"

# Declared before any verdict is computed (written to run_manifest.json first).
THRESHOLDS = {
    "min_rows": 30,
    "min_units": 10,
    "rationale": (
        "min_units = 10 old units/clusters: report 09 section 6 treated k = 10 as barely enough (M slice CI "
        "[0,000; 0,567]); min_rows = 30 rows so that an average unit contributes at least a few rows. "
        "CAVEAT: written after a preliminary look that already showed 0 units with two valid targets, so the "
        "thresholds are not blind; the E2 verdict is the same for every positive threshold."
    ),
    "status_rule": (
        "RUNNABLE_NOW if observed rows >= min_rows and observed units >= min_units; else NEEDS_NEW_SOURCE if the "
        "whole gazetteer population of such units >= min_units; else NOT_FEASIBLE"
    ),
}


# ---------------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_required(path: Path, columns: tuple[str, ...]) -> pd.DataFrame:
    """Read a CSV as strings after checking the file and its required columns exist."""
    if not Path(path).exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    missing = [name for name in columns if name not in frame.columns]
    if missing:
        raise ValueError(f"{path}: missing required columns {missing}")
    return frame


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> int:
    with Path(path).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in columns})
    return len(rows)


def dump_json(path: Path, payload) -> None:
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


# ---------------------------------------------------------------------------
# Pure logic (unit tested)
# ---------------------------------------------------------------------------

def street_key(text: object) -> str:
    """Street comparison key; same convention as the T2-STREET index (leading 'đường'/'phố' dropped)."""
    value = normalize_for_overlap(text)
    for prefix in ("đường ", "phố "):
        if value.startswith(prefix):
            return value[len(prefix):]
    return value


def classify_support(observed_rows: int, observed_units: int, population_units: int,
                     min_rows: int = THRESHOLDS["min_rows"], min_units: int = THRESHOLDS["min_units"]) -> str:
    """Three-state feasibility verdict; see ``THRESHOLDS['status_rule']``."""
    if observed_rows >= min_rows and observed_units >= min_units:
        return "RUNNABLE_NOW"
    if population_units >= min_units:
        return "NEEDS_NEW_SOURCE"
    return "NOT_FEASIBLE"


def street_dependence(rows: list[dict]) -> str:
    """Can the street alone explain the target among the rows of ONE old unit?

    rows: dicts with ``Target`` (new key) and ``Street``.  Needs two valid targets to be meaningful.
    """
    by_target: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        by_target[row["Target"]].add(street_key(row["Street"]))
    if len(by_target) < 2:
        return "NOT_APPLICABLE_SINGLE_TARGET"
    street_targets: dict[str, set[str]] = defaultdict(set)
    for target, streets in by_target.items():
        for street in streets:
            street_targets[street].add(target)
    if any(len(targets) > 1 for targets in street_targets.values()):
        return "STREET_SHARED_ACROSS_TARGETS"
    if len(street_targets) < 2:
        return "INSUFFICIENT_STREETS"
    return "STREET_SEPARATES_TARGETS"


def unit_key_text(key: tuple) -> str:
    return "|".join(key)


def audit_osm_rows(pairs: pd.DataFrame, snapshot: pd.DataFrame, mapping, gazetteer: T2Table,
                   data07_ids: set[str]) -> list[dict]:
    """One audit row per OSM diff row, following the Data 07 generator's filter order."""
    snapshot_by_id = {(r["OSM_Type"], r["OSM_ID"]): r for r in snapshot.to_dict("records")}
    edge_by_pair = {(e.old_key, e.new_key): e for e in gazetteer.edges}
    rows = []
    for record in pairs.to_dict("records"):
        node_id = f"{record['OSM_Type']}:{record['OSM_ID']}"
        norm = normalize_diff_record(record)
        old_fields = (norm["TinhThanh_Cu"], norm["QuanHuyen_Cu"], norm["PhuongXa_Cu"])
        out = {
            "ID_Node": node_id, "SoNha": record["SoNha"], "TenDuong": record["TenDuong"],
            "OldKeyNormalized": "", "NewTarget": "", "AdminGroup": "", "Status": "", "SubReason": "",
            "Relation": "", "InData07": node_id in data07_ids, "HinhHocThayDoi": record["HinhHocThayDoi"],
            "GazetteerEdgeFound": "", "GazetteerFanOut": "",
        }
        old_key = mapping.old_key(*old_fields)
        old_targets = mapping.targets_for_old(*old_fields)
        out["OldKeyNormalized"] = unit_key_text(old_key) if any(old_key) else ""
        out["AdminGroup"] = admin_group_key(*old_fields, mapping)
        snap = snapshot_by_id.get((record["OSM_Type"], record["OSM_ID"]))
        target = _new_target_from_diff(mapping, norm)
        if snap is None:
            out["Status"] = ST_NO_SNAPSHOT
        elif (clean_value(record["SoNha"]).casefold() != clean_value(snap["SoNha"]).casefold()
              or clean_value(record["TenDuong"]).casefold() != clean_value(snap["TenDuong"]).casefold()):
            out["Status"] = ST_STREET_CHANGED
        elif target is None:
            out["Status"] = ST_NEW_UNRESOLVED
            if not clean_value(record["PhuongXa_Moi"]) and not clean_value(record["QuanHuyen_Moi"]):
                out["SubReason"] = "NEW_WARD_BLANK"
            elif not mapping.resolve_new_province(norm["TinhThanh_Moi"]):
                out["SubReason"] = "NEW_PROVINCE_UNRESOLVED"
            else:
                out["SubReason"] = "NEW_WARD_NOT_A_KNOWN_UNIT"
        elif not old_targets:
            out["Status"] = ST_OLD_UNRESOLVED
            out["SubReason"] = "OLD_KEY_INCOMPLETE" if not all(old_key) else "OLD_NAME_NOT_FOUND"
        else:
            new_key = mapping.new_key(target.province, target.ward)
            out["NewTarget"] = unit_key_text(new_key)
            out["GazetteerFanOut"] = len(old_targets)
            edge = edge_by_pair.get((old_key, new_key))
            if mapping.edge_for_old_target(*old_fields, target) is None:
                out["Status"] = ST_NOT_EDGE
                out["GazetteerEdgeFound"] = False
            else:
                out["Status"] = ST_ELIGIBLE
                out["GazetteerEdgeFound"] = edge is not None
                out["Relation"] = mapping.relation_for(*old_fields, target)[0]
        rows.append(out)
    return rows


def unit_table(audit_rows: list[dict]) -> list[dict]:
    """Per normalised old unit: valid observed targets, gazetteer fan-out and street dependence (E2)."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in audit_rows:
        if row["Status"] == ST_ELIGIBLE:
            grouped[row["OldKeyNormalized"]].append(row)
    table = []
    for old_key, members in sorted(grouped.items()):
        targets = {m["NewTarget"] for m in members}
        evidence = [{"Target": m["NewTarget"], "Street": m["TenDuong"]} for m in members]
        fan_out = int(members[0]["GazetteerFanOut"])
        table.append({
            "OldKeyNormalized": old_key,
            "AdminGroup": members[0]["AdminGroup"],
            "Rows": len(members),
            "RowsInData07": sum(1 for m in members if m["InData07"]),
            "DistinctValidTargets": len(targets),
            "GazetteerFanOut": fan_out,
            "FanOutObservedShare": round(len(targets) / fan_out, 4) if fan_out else "",
            "Relations": "|".join(sorted({m["Relation"] for m in members})),
            "DistinctStreets": len({street_key(m["TenDuong"]) for m in members}),
            "StreetDependence": street_dependence(evidence),
        })
    return table


def raw_multi_target_trace(pairs: pd.DataFrame, audit_rows: list[dict]) -> list[dict]:
    """Explain each old unit that has >= 2 targets under the RAW string key (province|district|ward cũ).

    Raw target key = province|PhuongXa_Moi exactly as stored.  Cause priority is fixed in code: a real second
    valid target, then an observed target that is not an edge, then rows all excluded, then raw-key artefacts.
    """
    raw_old = (pairs["TinhThanh_Cu"] + "|" + pairs["QuanHuyen_Cu"] + "|" + pairs["PhuongXa_Cu"]).tolist()
    raw_new = (pairs["TinhThanh_Moi"] + "|" + pairs["PhuongXa_Moi"]).tolist()
    groups: dict[str, list[int]] = defaultdict(list)
    for index, key in enumerate(raw_old):
        groups[key].append(index)
    result = []
    for key, indexes in sorted(groups.items()):
        if len({raw_new[i] for i in indexes}) < 2:
            continue
        rows = [audit_rows[i] for i in indexes]
        statuses = Counter(r["Status"] for r in rows)
        eligible = [r for r in rows if r["Status"] == ST_ELIGIBLE]
        per_unit: dict[str, set[str]] = defaultdict(set)
        for r in eligible:
            per_unit[r["OldKeyNormalized"]].add(r["NewTarget"])
        max_targets = max((len(v) for v in per_unit.values()), default=0)
        parts = key.split("|")
        incomplete = (not all(parts)) or any(not pairs.iloc[i]["PhuongXa_Moi"] for i in indexes)
        if max_targets >= 2:
            cause = "REAL_MULTI_VALID_TARGET"
        elif statuses[ST_NOT_EDGE] and eligible:
            cause = "OBSERVED_TARGET_NOT_AN_EDGE_PLUS_VALID_TARGET"
        elif not eligible:
            cause = "NO_ELIGIBLE_ROW"
        elif incomplete:
            cause = "RAW_KEY_ARTEFACT_EMPTY_FIELD"
        else:
            cause = "RAW_KEY_ARTEFACT_SPELLING_VARIANTS"
        result.append({
            "RawOldKey": key, "Rows": len(indexes), "RawDistinctTargets": len({raw_new[i] for i in indexes}),
            "EligibleRows": len(eligible), "NormalizedOldUnits": len(per_unit),
            "MaxValidTargetsPerNormalizedUnit": max_targets,
            "StatusCounts": json.dumps(dict(statuses), ensure_ascii=False, sort_keys=True),
            "Cause": cause,
        })
    return result


def gazetteer_multi_target_units(gazetteer: T2Table) -> int:
    fan_out: dict[tuple, set[str]] = defaultdict(set)
    for edge in gazetteer.edges:
        fan_out[edge.old_key].add(edge.new_entity_id)
    return sum(1 for targets in fan_out.values() if len(targets) >= 2)


def edge_support_rows(gazetteer: T2Table, audit_rows: list[dict], snapshot_full: pd.DataFrame,
                      snapshot_balanced: pd.DataFrame, mapping) -> list[dict]:
    """Every A and C edge with the evidence that exists for it today (no pair is created)."""
    observed = Counter((r["OldKeyNormalized"], r["NewTarget"]) for r in audit_rows if r["Status"] == ST_ELIGIBLE)
    any_status = Counter(r["OldKeyNormalized"] for r in audit_rows if r["OldKeyNormalized"])
    snap_full = Counter(unit_key_text(mapping.old_key(r["TinhThanh"], r["QuanHuyen"], r["PhuongXa"]))
                        for r in snapshot_full.to_dict("records"))
    snap_bal = Counter(unit_key_text(mapping.old_key(r["TinhThanh"], r["QuanHuyen"], r["PhuongXa"]))
                       for r in snapshot_balanced.to_dict("records"))
    rows = []
    for edge in gazetteer.edges:
        relation = gazetteer.relations[edge.source_row]
        if relation not in ("A", "C"):
            continue
        old = unit_key_text(edge.old_key)
        new = unit_key_text(edge.new_key)
        rows.append({
            "SourceRow": edge.source_row, "Relation": relation,
            "OldProvince": edge.old_province, "OldDistrict": edge.old_district, "OldWard": edge.old_ward,
            "NewProvince": edge.new_province, "NewWard": edge.new_ward,
            "NameUnchanged": edge.old_key[2] == edge.new_key[1],
            "ObservedEligibleRows": observed.get((old, new), 0),
            "OsmDiffRowsWithOldKeyAnyStatus": any_status.get(old, 0),
            "SnapshotFullRowsWithOldKey": snap_full.get(old, 0),
            "SnapshotBalancedRowsWithOldKey": snap_bal.get(old, 0),
        })
    return rows


def label_source_rows(register: pd.DataFrame, decisions: pd.DataFrame, tb243: dict) -> list[dict]:
    """One row per source: labels named by its register description (not by a sample) and its use rights."""
    by_key = {r["source_key"]: r for r in decisions.to_dict("records")}
    rows = []
    for record in register.to_dict("records"):
        key = REGISTER_TO_DECISION_KEY.get(record["source_id"], "")
        decision = by_key.get(key, {})
        listed = [x for x in record["candidate_t0_labels"].split("|") if x]
        rows.append({
            "SourceId": record["source_id"], "DecisionKey": key, "Publisher": record["publisher"],
            "InRegisterV1": True,
            "RegisterLabelsListed": "|".join(listed),
            "LandmarkLabelsListed": "|".join(x for x in listed if x in LANDMARK_LABELS),
            "LaiMentionInRegister": record["candidate_t1_review"],
            "LocalResearch": decision.get("local_research", "NO_DECISION"),
            "Annotation": decision.get("annotation", "NO_DECISION"),
            "CloudUpload": decision.get("cloud_upload", "NO_DECISION"),
            "Redistribution": decision.get("redistribution", "NO_DECISION"),
            "CollectedSamplesRegister": record["collected_sample_count"],
            "AnnotationReadyRegister": record["annotation_ready_sample_count"],
            "PilotSamplesDecisionLog": decision.get("pilot_samples", ""),
        })
    decisions_tb = tb243.get("decisions", {})
    rows.append({
        "SourceId": "TB243_PHU_LUC_II", "DecisionKey": "", "Publisher": "UBND TP Ho Chi Minh (Thong bao 243/TB-UBND)",
        "InRegisterV1": False, "RegisterLabelsListed": "", "LandmarkLabelsListed": "",
        "LaiMentionInRegister": "NOT_APPLICABLE_NEW_SYSTEM_ONLY",
        "LocalResearch": decisions_tb.get("local_research", "NO_DECISION"),
        "Annotation": decisions_tb.get("annotation", "NO_DECISION"),
        "CloudUpload": decisions_tb.get("cloud_upload", "NO_DECISION"),
        "Redistribution": decisions_tb.get("redistribution", "NO_DECISION"),
        "CollectedSamplesRegister": "", "AnnotationReadyRegister": "", "PilotSamplesDecisionLog": "",
    })
    return rows


def label_verdicts(source_rows: list[dict]) -> list[dict]:
    """Per label: sources that name it and whether any is approved for annotation (rights, not support)."""
    out = []
    for label in LANDMARK_LABELS:
        naming = [r for r in source_rows if label in r["LandmarkLabelsListed"].split("|")]
        approved = [r for r in naming if r["Annotation"] == "APPROVED"]
        out.append({"Label": label, "SourcesNaming": "|".join(r["SourceId"] for r in naming),
                    "ApprovedForAnnotation": "|".join(r["SourceId"] for r in approved),
                    "Status": RIGHTS_OK if approved else "NEEDS_NEW_SOURCE", "Support": "NOT_MEASURED"})
    # The register names `Lai` only as "old_new_parallel_mentions_require_review" (a review need, not a sample).
    lai_sources = [r for r in source_rows if "old_new" in r["LaiMentionInRegister"]]
    lai_approved = [r for r in lai_sources if r["Annotation"] == "APPROVED"]
    out.append({"Label": "Lai_human_written", "SourcesNaming": "|".join(r["SourceId"] for r in lai_sources),
                "ApprovedForAnnotation": "|".join(r["SourceId"] for r in lai_approved),
                "Status": RIGHTS_OK if lai_approved else "NEEDS_NEW_SOURCE", "Support": "NOT_MEASURED"})
    return out


def corpus_label_support(corpus_dir: Path) -> list[dict]:
    """Sprint 3 gold support per label/system (measured, context only)."""
    rows = []
    for split, name in CORPUS_FILES.items():
        path = corpus_dir / name
        if not path.exists():
            raise FileNotFoundError(path)
        samples = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        labels = Counter(span["label"] for sample in samples for span in sample["spans"])
        systems = Counter(str(sample.get("address_system")) for sample in samples)
        for label in sorted(labels):
            rows.append({"Split": split, "Kind": "span_label", "Name": label, "Count": labels[label],
                         "Denominator": len(samples)})
        for system in sorted(systems):
            rows.append({"Split": split, "Kind": "address_system", "Name": system, "Count": systems[system],
                         "Denominator": len(samples)})
    return rows


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def compute(root: Path) -> dict:
    """Load inputs and compute every table and metric (no file is written)."""
    paths = {name: root / rel for name, rel in (
        ("pairs", PAIRS), ("data07", DATA07), ("snapshot_full", SNAPSHOT_FULL), ("snapshot_balanced", SNAPSHOT_BALANCED),
        ("register", SOURCE_REGISTER), ("decisions", DECISION_LOG), ("tb243", TB243_MANIFEST))}
    pairs = read_required(paths["pairs"], PAIRS_COLUMNS)
    data07 = read_required(paths["data07"], DATA07_COLUMNS)
    snapshot_full = read_required(paths["snapshot_full"], SNAPSHOT_COLUMNS)
    snapshot_balanced = read_required(paths["snapshot_balanced"], SNAPSHOT_COLUMNS)
    register = read_required(paths["register"], REGISTER_COLUMNS)
    decisions = read_required(paths["decisions"], DECISION_COLUMNS)
    if not paths["tb243"].exists():
        raise FileNotFoundError(paths["tb243"])
    tb243 = json.loads(paths["tb243"].read_text(encoding="utf-8"))

    mapping_path = root / MAPPING_CSV
    mapping = load_administrative_mapping(mapping_path)
    gazetteer = T2Table.load(root / GAZETTEER_DIR)  # verifies the four hashed tables against manifest.json
    audit_rows = audit_osm_rows(pairs, snapshot_full, mapping, gazetteer, set(data07["ID_Node"]))
    units = unit_table(audit_rows)

    # Cross-check against the generator itself (in memory only; nothing is written or added to a corpus).
    generated = generate_bidirectional_pairs(
        root / PAIRS, mapping_path, root / SNAPSHOT_BALANCED, target_size=10**6, seed=42,
        full_snapshot_path=root / SNAPSHOT_FULL)
    observed_generator = generated[generated["Nguon"].str.startswith("OSM_Diff")]
    derived_generator = generated[~generated["Nguon"].str.startswith("OSM_Diff")]
    eligible_ids = {r["ID_Node"] for r in audit_rows if r["Status"] == ST_ELIGIBLE}

    trace = raw_multi_target_trace(pairs, audit_rows)
    edge_rows = edge_support_rows(gazetteer, audit_rows, snapshot_full, snapshot_balanced, mapping)
    sources = label_source_rows(register, decisions, tb243)
    verdicts = label_verdicts(sources)
    support = corpus_label_support(root / CORPUS_DIR)
    return {
        "paths": paths, "pairs": pairs, "data07": data07, "gazetteer": gazetteer, "mapping": mapping,
        "audit_rows": audit_rows, "units": units, "trace": trace, "edge_rows": edge_rows, "sources": sources,
        "verdicts": verdicts, "support": support, "observed_generator": observed_generator,
        "derived_generator": derived_generator, "eligible_ids": eligible_ids, "tb243": tb243,
    }


def reproduction_rows(data: dict) -> list[dict]:
    """Facts the coordinator measured on 15/10/2026 versus this run (mismatch is reported, never hidden)."""
    pairs, data07, gazetteer = data["pairs"], data["data07"], data["gazetteer"]
    raw_old = pairs["TinhThanh_Cu"] + "|" + pairs["QuanHuyen_Cu"] + "|" + pairs["PhuongXa_Cu"]
    raw_new = pairs["TinhThanh_Moi"] + "|" + pairs["PhuongXa_Moi"]
    per_unit = raw_new.groupby(raw_old).nunique()
    distribution = {str(k): int(v) for k, v in sorted(per_unit.value_counts().items())}
    gaz_codes: dict[str, set[str]] = defaultdict(set)
    for edge in gazetteer.edges:
        gaz_codes["|".join((edge.old_province, edge.old_district, edge.old_ward))].add(edge.new_ward_code)
    multi_raw = list(per_unit[per_unit >= 2].index)
    both = [key for key in multi_raw if len(gaz_codes.get(key, ())) >= 2]
    rows_in_both = int(raw_old.isin(both).sum())
    relation_counts = Counter(gazetteer.relations.values())
    # Variant for the diagnostic only: blank old fields act as wildcards against the gazetteer.
    wildcard_hits = []
    for key in multi_raw:
        province, district, ward = (unit_key(x) for x in key.split("|"))
        if not (province or district or ward):
            continue
        codes = {e.new_ward_code for e in gazetteer.edges
                 if (not province or e.old_key[0] == province_key(key.split("|")[0]))
                 and (not district or e.old_key[1] == district) and (not ward or e.old_key[2] == ward)}
        if len(codes) >= 2:
            wildcard_hits.append(key)

    def check(item, claimed, observed, note=""):
        status = "MATCH" if claimed == observed else "MISMATCH"
        return {"Item": item, "Claimed_1510": json.dumps(claimed, ensure_ascii=False),
                "Observed": json.dumps(observed, ensure_ascii=False), "Status": status, "Note": note}

    rows = [
        check("pairs_rows", 1631, len(pairs)),
        check("pairs_columns", 18, len(pairs.columns)),
        check("pairs_Nguon_values", ["OSM Diff History (Real User Update)"], sorted(pairs["Nguon"].unique())),
        check("data07_rows", 600, len(data07)),
        check("data07_LoaiAnhXa", {"B": 244, "M": 356}, dict(sorted(Counter(data07["LoaiAnhXa"]).items()))),
        check("raw_old_units", 361, int(per_unit.shape[0]), "raw key = province|district|ward cũ as stored"),
        check("raw_units_by_distinct_targets", {"1": 340, "2": 19, "3": 1, "4": 1}, distribution,
              "raw target key = province|PhuongXa_Moi as stored"),
        check("raw_units_with_ge2_targets", 21, len(multi_raw)),
        check("gazetteer_old_keys", 10035, len(gaz_codes)),
        check("gazetteer_old_keys_ge2_new_codes", 471, sum(1 for v in gaz_codes.values() if len(v) >= 2)),
        check("raw_multi_units_also_ge2_in_gazetteer_units", 5, len(both),
              "claimed 5 units / 7 rows; exact raw key reproduces fewer"),
        check("raw_multi_units_also_ge2_in_gazetteer_rows", 7, rows_in_both),
        {"Item": "variant_blank_fields_as_wildcard_units", "Claimed_1510": "", "Observed": json.dumps(len(wildcard_hits)),
         "Status": "INFO", "Note": "diagnostic variant tried to explain the 5/7 claim; also does not give 5"},
        check("gazetteer_edges", 10597, len(gazetteer.edges)),
        check("gazetteer_relations", {"A": 3, "B": 9432, "C": 132, "M": 1030}, dict(sorted(relation_counts.items()))),
        check("non_atomic_transitions", 5, len(gazetteer.non_atomic)),
        check("pairs_HinhHocCoDuLieu_all_True", True, bool((pairs["HinhHocCoDuLieu"] == "True").all())),
        check("pairs_HinhHocThayDoi_True", 287, int((pairs["HinhHocThayDoi"] == "True").sum())),
    ]
    return rows


def build_metrics(data: dict) -> dict:
    audit_rows, units, edge_rows = data["audit_rows"], data["units"], data["edge_rows"]
    status = Counter(r["Status"] for r in audit_rows)
    sub = Counter((r["Status"], r["SubReason"]) for r in audit_rows if r["SubReason"])
    gazetteer = data["gazetteer"]
    eligible = [r for r in audit_rows if r["Status"] == ST_ELIGIBLE]
    multi_units = [u for u in units if u["DistinctValidTargets"] >= 2]
    fan_out_units = [u for u in units if u["GazetteerFanOut"] >= 2]
    population_multi = gazetteer_multi_target_units(gazetteer)
    not_edge = [r for r in audit_rows if r["Status"] == ST_NOT_EDGE]
    cause_counts = Counter(t["Cause"] for t in data["trace"])
    relation_rows = Counter(r["Relation"] for r in eligible)
    relation_units: dict[str, set[str]] = defaultdict(set)
    for r in eligible:
        relation_units[r["Relation"]].add(r["OldKeyNormalized"])
    derived = data["derived_generator"]
    by_relation = {rel: [e for e in edge_rows if e["Relation"] == rel] for rel in ("A", "C")}

    def edge_summary(relation: str, only_changed: bool = False) -> dict:
        subset = [e for e in by_relation[relation] if (not only_changed or not e["NameUnchanged"])]
        return {
            "edges": len(subset),
            "old_units": len({(e["OldProvince"], e["OldDistrict"], e["OldWard"]) for e in subset}),
            "name_unchanged": sum(1 for e in subset if e["NameUnchanged"]),
            "with_observed_eligible_row": sum(1 for e in subset if e["ObservedEligibleRows"] > 0),
            "observed_eligible_rows": sum(e["ObservedEligibleRows"] for e in subset),
            "with_osm_diff_row_any_status": sum(1 for e in subset if e["OsmDiffRowsWithOldKeyAnyStatus"] > 0),
            "with_snapshot_full_row": sum(1 for e in subset if e["SnapshotFullRowsWithOldKey"] > 0),
            "snapshot_full_rows": sum(e["SnapshotFullRowsWithOldKey"] for e in subset),
        }

    a_all, c_all, c_changed = edge_summary("A"), edge_summary("C"), edge_summary("C", only_changed=True)
    derived_c = derived[derived["LoaiAnhXa"] == "C"]
    verdict = {
        "E2": classify_support(sum(u["Rows"] for u in multi_units), len(multi_units), population_multi),
        "T2_A": classify_support(a_all["observed_eligible_rows"], a_all["with_observed_eligible_row"], a_all["old_units"]),
        "T2_C": classify_support(c_all["observed_eligible_rows"], c_all["with_observed_eligible_row"], c_all["old_units"]),
        "T2_C_NAME_CHANGED": classify_support(c_changed["observed_eligible_rows"], c_changed["with_observed_eligible_row"],
                                              c_changed["old_units"]),
    }
    return {
        "script_version": SCRIPT_VERSION, "thresholds": THRESHOLDS,
        "osm_rows": {
            "total": len(audit_rows), "status": dict(sorted(status.items())),
            "sub_reason": {f"{k[0]}/{k[1]}": v for k, v in sorted(sub.items())},
            "eligible": len(eligible), "eligible_in_data07": sum(1 for r in eligible if r["InData07"]),
            "eligible_not_in_data07": sum(1 for r in eligible if not r["InData07"]),
            "eligible_hinhhoc_changed": sum(1 for r in eligible if r["HinhHocThayDoi"] == "True"),
            "eligible_relation_rows": dict(sorted(relation_rows.items())),
            "eligible_relation_old_units": {k: len(v) for k, v in sorted(relation_units.items())},
            "eligible_edge_found_in_gazetteer_table": sum(1 for r in eligible if r["GazetteerEdgeFound"] is True),
            "generator_observed_rows": int(len(data["observed_generator"])),
            "generator_observed_equals_eligible": set(data["observed_generator"]["ID_Node"]) == data["eligible_ids"],
            "data07_subset_of_eligible": set(data["data07"]["ID_Node"]) <= data["eligible_ids"],
        },
        "e2": {
            "eligible_old_units": len(units),
            "units_with_ge2_valid_targets": len(multi_units),
            "rows_in_units_with_ge2_valid_targets": sum(u["Rows"] for u in multi_units),
            "admin_groups_of_those_units": len({u["AdminGroup"] for u in multi_units}),
            "eligible_units_with_gazetteer_fan_out_ge2": len(fan_out_units),
            "rows_in_those_units": sum(u["Rows"] for u in fan_out_units),
            "targets_observed_per_fan_out_unit": dict(sorted(Counter(u["DistinctValidTargets"] for u in fan_out_units).items())),
            "gazetteer_old_units_with_fan_out_ge2": population_multi,
            "observed_not_edge_rows": len(not_edge),
            "observed_not_edge_units": len({r["OldKeyNormalized"] for r in not_edge}),
            "raw_multi_target_causes": dict(sorted(cause_counts.items())),
            "raw_multi_target_units": len(data["trace"]),
        },
        "t2_a": a_all, "t2_c": c_all, "t2_c_name_changed": c_changed,
        "derivable_pairs_in_memory": {
            "observed_rows": int(len(data["observed_generator"])), "derived_rows": int(len(derived)),
            "derived_by_relation": dict(sorted(Counter(derived["LoaiAnhXa"]).items())),
            # 1-1 edges: one new ward code per old unit, so distinct codes = distinct old units
            "derived_c_old_units": int(derived_c["MaPhuongXaMoi"].nunique()) if len(derived_c) else 0,
            "note": "computed in memory by generate_bidirectional_pairs(target_size=1e6); nothing written",
        },
        "verdict": verdict,
        "labels": data["verdicts"],
    }


def conclusion_rows(metrics: dict) -> list[dict]:
    e2, a, c, cc = metrics["e2"], metrics["t2_a"], metrics["t2_c"], metrics["t2_c_name_changed"]
    verdict = metrics["verdict"]
    rows = [
        {"Item": "E2", "Status": verdict["E2"],
         "Numbers": (f"units with >=2 valid targets: {e2['units_with_ge2_valid_targets']} (rows "
                     f"{e2['rows_in_units_with_ge2_valid_targets']}, clusters {e2['admin_groups_of_those_units']}); "
                     f"eligible units {e2['eligible_old_units']}, of which fan-out>=2: "
                     f"{e2['eligible_units_with_gazetteer_fan_out_ge2']} each observed with "
                     f"{e2['targets_observed_per_fan_out_unit']} target(s); gazetteer units with fan-out>=2: "
                     f"{e2['gazetteer_old_units_with_fan_out_ge2']}; raw 21 -> causes {e2['raw_multi_target_causes']}"),
         "Blocker": ("E2 negative after the current filter: 0 units with >= 2 valid targets matching gazetteer edges; "
                     "15/21 raw multi-target units NOT EVALUABLE (all rows excluded, unknown whether truly multi-target); "
                     "only 5/21 shown to be key artefacts (4 spelling variants + 1 empty field); check first the "
                     "298 rows whose new ward name is not recognised before asking for a new source"),
         "Decider": "project owner (G2-7: new OSM extraction or other observed source)"},
        {"Item": "T2_A", "Status": verdict["T2_A"],
         "Numbers": (f"A edges {a['edges']} over {a['old_units']} old units; observed eligible rows "
                     f"{a['observed_eligible_rows']}; OSM diff rows with that old key {a['with_osm_diff_row_any_status']} units; "
                     f"snapshot rows {a['snapshot_full_rows']}"),
         "Blocker": "population below min_units even with perfect data; snapshot-derived A is forbidden (AGENTS 6)",
         "Decider": "group 1 owner: report A as qualitative cases only"},
        {"Item": "T2_C", "Status": verdict["T2_C"],
         "Numbers": (f"C edges {c['edges']} over {c['old_units']} old units, {c['name_unchanged']} with unchanged name; "
                     f"observed eligible rows {c['observed_eligible_rows']}; derived C rows (in memory) "
                     f"{metrics['derivable_pairs_in_memory']['derived_by_relation'].get('C', 0)} over "
                     f"{metrics['derivable_pairs_in_memory']['derived_c_old_units']} units"),
         "Blocker": "no directly observed C row; derived C is circular (target from the same table) and tiny",
         "Decider": "project owner (new observed source) or accept C as sanity check only"},
        {"Item": "T2_C_NAME_CHANGED", "Status": verdict["T2_C_NAME_CHANGED"],
         "Numbers": f"C edges whose ward name changes: {cc['edges']} over {cc['old_units']} old units; observed rows {cc['observed_eligible_rows']}",
         "Blocker": "name-unchanged C is trivial for a name lookup; the informative subset is below min_units",
         "Decider": "group 1 owner"},
    ]
    for entry in metrics["labels"]:
        rows.append({
            "Item": entry["Label"], "Status": entry["Status"],
            "Numbers": f"support: {entry['Support']}; sources naming it (register description): {entry['SourcesNaming'] or 'none'}; "
                       f"approved for annotation: {entry['ApprovedForAnnotation'] or 'none'}",
            "Blocker": ("annotation by the owner on an approved source (support unmeasured)" if entry["Status"] == RIGHTS_OK
                        else "no source with annotation APPROVED names this label"),
            "Decider": "project owner (annotation, G2-3/G2-4)" if entry["Status"] == RIGHTS_OK
            else "project owner (G2-7: approve a new source)",
        })
    return rows


def declared_manifest(root: Path, out: Path, started: str) -> dict:
    return {
        "script_version": SCRIPT_VERSION, "declared_at_utc": started, "seed": "NOT_USED_NO_SAMPLING",
        "thresholds": THRESHOLDS,
        "rules": {
            "row_eligibility": "same filter order as generate_bidirectional_pairs: snapshot id (full) -> house number and street "
                               "unchanged -> new target resolved -> old key in source -> observed target is an edge",
            "normalisation": "administrative_alias.normalize_diff_record then administrative_mapping keys (N2)",
            "raw_key": "province|district|ward cũ and province|PhuongXa_Moi exactly as stored (coordinator's 15/10 key)",
            "relation": "degrees of the atomic graph (s3_v2 edges.csv via T2Table.relations)",
            "derived_pairs": "B or C only when the old key has exactly one target; never A or M",
            "label_status": "RIGHTS_OK_SUPPORT_UNMEASURED = an annotation-APPROVED source names the label in its register "
                            "description; support is NOT_MEASURED (owner annotation needed); distinct from the "
                            "threshold-based RUNNABLE_NOW",
        },
        "out_dir": out.as_posix(),
    }


def execute(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    out = Path(args.out_dir)
    out = out if out.is_absolute() else root / out
    if out.exists():
        print(f"refuse to overwrite existing output directory: {out}", file=sys.stderr)
        return 3
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        data = compute(root)  # loading and row audit only; no verdict yet
    except (FileNotFoundError, ValueError) as error:
        print(f"input error: {error}", file=sys.stderr)
        return 2
    # Declared rules and thresholds are written before any verdict is computed.
    out.mkdir(parents=True)
    manifest = declared_manifest(root, out, started)
    dump_json(out / "run_manifest.json", manifest)

    metrics = build_metrics(data)
    reproduction = reproduction_rows(data)
    conclusions = conclusion_rows(metrics)
    outputs = {}
    outputs["osm_row_audit.csv"] = write_csv(out / "osm_row_audit.csv", data["audit_rows"], [
        "ID_Node", "SoNha", "TenDuong", "Status", "SubReason", "OldKeyNormalized", "NewTarget", "AdminGroup",
        "Relation", "GazetteerFanOut", "GazetteerEdgeFound", "InData07", "HinhHocThayDoi"])
    outputs["e2_unit_audit.csv"] = write_csv(out / "e2_unit_audit.csv", data["units"], [
        "OldKeyNormalized", "AdminGroup", "Rows", "RowsInData07", "DistinctValidTargets", "GazetteerFanOut",
        "FanOutObservedShare", "Relations", "DistinctStreets", "StreetDependence"])
    outputs["e2_raw_multi_target_trace.csv"] = write_csv(out / "e2_raw_multi_target_trace.csv", data["trace"], [
        "RawOldKey", "Rows", "RawDistinctTargets", "EligibleRows", "NormalizedOldUnits",
        "MaxValidTargetsPerNormalizedUnit", "StatusCounts", "Cause"])
    outputs["t2_ac_edges.csv"] = write_csv(out / "t2_ac_edges.csv", data["edge_rows"], [
        "SourceRow", "Relation", "OldProvince", "OldDistrict", "OldWard", "NewProvince", "NewWard", "NameUnchanged",
        "ObservedEligibleRows", "OsmDiffRowsWithOldKeyAnyStatus", "SnapshotFullRowsWithOldKey",
        "SnapshotBalancedRowsWithOldKey"])
    outputs["label_source_assessment.csv"] = write_csv(out / "label_source_assessment.csv", data["sources"], [
        "SourceId", "DecisionKey", "Publisher", "InRegisterV1", "RegisterLabelsListed", "LandmarkLabelsListed",
        "LaiMentionInRegister", "LocalResearch", "Annotation", "CloudUpload", "Redistribution",
        "CollectedSamplesRegister", "AnnotationReadyRegister", "PilotSamplesDecisionLog"])
    outputs["label_verdicts.csv"] = write_csv(out / "label_verdicts.csv", data["verdicts"], [
        "Label", "SourcesNaming", "ApprovedForAnnotation", "Status", "Support"])
    outputs["sprint3_gold_support.csv"] = write_csv(out / "sprint3_gold_support.csv", data["support"], [
        "Split", "Kind", "Name", "Count", "Denominator"])
    outputs["reproduction_check.csv"] = write_csv(out / "reproduction_check.csv", reproduction, [
        "Item", "Claimed_1510", "Observed", "Status", "Note"])
    outputs["conclusions.csv"] = write_csv(out / "conclusions.csv", conclusions, [
        "Item", "Status", "Numbers", "Blocker", "Decider"])
    metrics["reproduction"] = {"match": sum(1 for r in reproduction if r["Status"] == "MATCH"),
                               "mismatch": [r["Item"] for r in reproduction if r["Status"] == "MISMATCH"]}
    dump_json(out / "metrics.json", metrics)

    inputs = {name: {"path": path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path),
                     "sha256": sha256_file(path)} for name, path in data["paths"].items()}
    for name in ("edges.csv", "non_atomic_transitions.csv", "manifest.json"):
        inputs[f"gazetteer_{name}"] = {"path": (GAZETTEER_DIR / name).as_posix(), "sha256": sha256_file(root / GAZETTEER_DIR / name)}
    inputs["gazetteer_active_edges_s3_v4_release2"] = {
        "path": GAZETTEER_ACTIVE_EDGES.as_posix(), "sha256": sha256_file(root / GAZETTEER_ACTIVE_EDGES)}
    inputs["administrative_mapping_csv"] = {
        "path": "data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv",
        "sha256": sha256_file(root / "data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv")}
    for split, name in CORPUS_FILES.items():
        inputs[f"corpus_{split}"] = {"path": (CORPUS_DIR / name).as_posix(), "sha256": sha256_file(root / CORPUS_DIR / name)}
    manifest.update({
        "finished_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "inputs": inputs,
        "source_sha256": {rel: sha256_file(root / rel) for rel in SOURCE_FILES},
        "rows_in": {"osm_pairs": len(data["pairs"]), "data07": len(data["data07"]),
                    "gazetteer_edges": len(data["gazetteer"].edges)},
        "rows_out": outputs,
        "outputs_sha256": {p.name: sha256_file(p) for p in sorted(out.iterdir()) if p.is_file() and p.name != "run_manifest.json"},
        "gazetteer_s3_v2_edges_equal_active_release2": inputs["gazetteer_edges.csv"]["sha256"] == inputs["gazetteer_active_edges_s3_v4_release2"]["sha256"],
    })
    dump_json(out / "run_manifest.json", manifest)
    print(f"done -> {out}")
    print(json.dumps(metrics["verdict"], ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--root", type=Path, default=REPO)
    return execute(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
