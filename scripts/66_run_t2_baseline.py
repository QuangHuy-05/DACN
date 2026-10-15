"""T2 baseline: two-way administrative-unit lookup on Data 07, asymmetry (E3), street evidence (E2), H5 situations C/D.

Run from the repository root in the main runtime (``~/.venv_dacn``):

    python -m scripts.66_run_t2_baseline --out-dir data/processed/evaluation/sprint04/t2_baseline_20261014_v1

CRF-INDEP inference needs ``pycrfsuite`` which only the CRF runtime has; this
file therefore doubles as a stdlib-only worker (``--crf-worker``) launched as a
separate process.  Module-level imports stay stdlib-only for that reason.

The output directory must not exist (no overwrite).  Gold columns are read only
by the scoring helpers; every system receives text fields.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[1]
CRF_RUNTIME = Path("data/interim/evaluation/sprint03/runtime_py311/bin/python")
LOCKED_CONFIG_DIR = Path("data/interim/modeling/sprint03/final_completion_20261005_v1/light_test_runs_v2")
GAZETTEER_DIR = Path("data/processed/gazetteer/s3_v4_nso_dual_snapshot_release2")
DATA07 = Path("data/processed/benchmark/07_bidirectional_pairs_verified.csv")
DATA06 = Path("data/processed/benchmark/06_hybrid_addresses_600.csv")
DATA01 = Path("data/processed/benchmark/01_full_address_new_verified.csv")
OSM_LATEST = Path("data/interim/osm/osm_latest_clean.csv")
DEFAULT_OUT = Path("data/processed/evaluation/sprint04/t2_baseline_20261014_v1")
CI_SEED = 20261014
SCRIPT_VERSION = "t2-baseline-run-v1"
MAIN_LEVEL = "N2"
LOW_EVIDENCE_THRESHOLD = 0.20

DATA07_COLUMNS = ("ID_Node", "DiaChi_Cu", "DiaChi_Moi", "LoaiAnhXa", "QuanHe", "HinhThucSapNhap",
                  "MaPhuongXaMoi", "Nguon")
DATA06_COLUMNS = ("ChuoiDiaChi", "SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh", "KieuLai")
DATA01_COLUMNS = ("SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh", "ChuoiDiaChi")
OSM_COLUMNS = ("SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh", "ChuoiDiaChi")

SOURCE_FILES = (
    "src/evaluation/t2_lookup.py", "src/evaluation/t2_scorer.py", "scripts/66_run_t2_baseline.py",
    "src/evaluation/stats.py", "src/evaluation/leak_guard.py", "src/data/administrative_mapping.py",
    "src/data/administrative_alias.py", "src/evaluation/adapters/vnadmin_adapter.py",
    "src/evaluation/adapters/heur_jw_adapter.py", "src/evaluation/adapters/heur_jw_followup.py",
    "src/data/nso_dual_snapshot.py", "src/evaluation/adapters/crf_adapter.py",
    "src/evaluation/span_features.py", "src/evaluation/schema.py",
)

# Facts measured on 13/10/2026 (plan section 1); a mismatch stops the run before anything is written.
EXPECTED = {
    "data07_rows": 600,
    "data07_loai": {"M": 356, "B": 244},
    "data07_codes": 23,
    "data07_old_units_raw": 69,
    "data07_ha_noi_rows": 441,
    "data07_old_parts": {"4": 66, "5": 532, "6": 1, "9": 1},
    "data07_m_main_form": 335,
    "old_match_N0": 5,
    "old_match_N1": 535,
    "new_match_N0": 600,
    "fanout_N1_M": {"0": 13, "2": 44, "4": 299},
    "fanout_N1_B": {"0": 52, "1": 192},
    "multi_candidate_rows_N1": 343,
    "atomic_edges": 10597,
    "relation_counts": {"A": 3, "B": 9432, "C": 132, "M": 1030},
    "merge_form_M": {"Tách — nhập chủ yếu": 468, "Tách — một phần": 562},
    "mapping_only_edges": 5,
    "relation_label_mismatch_vs_file": 0,
    "data06_rows": 600,
    "data06_kieulai": {"C1": 420, "C2": 120, "C3": 60},
    "data06_full_old_key_match_N1": 421,
}

SYSTEM_DEFINITIONS = {
    "T2-LOOKUP-STRICT": "full-key lookup in edges.csv; answer only when exactly one target; otherwise abstain with the "
                        "candidate list and reason AMBIGUOUS / NO_MATCH / NON_ATOMIC",
    "T2-LOOKUP-DEFAULT-MAIN": "always pick one target: merge_form priority 'Hợp nhất toàn bộ' > 'Tách — nhập chủ yếu' > "
                              "'Tách — một phần', ties by smallest source_row; no warning on ambiguity",
    "T2-LOOKUP-DEFAULT-FIRST": "always pick the target with smallest source_row; ignores merge_form; no warning",
    "T2-VNADMIN": "VietnamAdminUnitsAdapter.convert_to_2025 on the whole DiaChi_Cu string; geocoder replaced by a stub "
                  "returning None before the adapter is created; old->new only (new->old NOT_SUPPORTED); compared by "
                  "normalised (province, ward)",
    "T2-SINGLE-VERSION": "version-blind name lookup in the target system inside the target province; one hit = answer, "
                         "none = NO_MATCH (warned), homonyms = AMBIGUOUS abstain (warned)",
    "T2-STREET-L1-MAIN": "street evidence (street -> new wards) among several targets, leak filter (i); fallback DEFAULT-MAIN",
    "T2-STREET-L1-FIRST": "street evidence, leak filter (i); fallback DEFAULT-FIRST",
    "T2-STREET-L2-MAIN": "street evidence, leak filters (i)+(ii) strict; fallback DEFAULT-MAIN",
    "T2-STREET-L2-FIRST": "street evidence, leak filters (i)+(ii) strict; fallback DEFAULT-FIRST",
}
STREET_VARIANTS = {
    "T2-STREET-L1-MAIN": ("L1", "main"), "T2-STREET-L1-FIRST": ("L1", "first"),
    "T2-STREET-L2-MAIN": ("L2", "main"), "T2-STREET-L2-FIRST": ("L2", "first"),
}

DECLARED_RULES = {
    "normalisation_levels": {
        "N0": "raw string after strip only",
        "N1": "administrative_mapping keys (province_key / unit_key / resolve of old->new province)",
        "N2": "N1; if no key matches, retry once with verified aliases from administrative_alias.py; no fuzzy match",
    },
    "main_table": "oracle segmentation, N2",
    "oracle_segmentation": "comma split from the right: old = ward[-3], district[-2], province[-1]; new = ward[-2], province[-1]",
    "gold": {
        "cu_to_moi": "new unit (province key + ward key) of DiaChi_Moi resolved at N2; code compared with MaPhuongXaMoi",
        "moi_to_cu": "old unit (province, district, ward) of DiaChi_Cu resolved at N2 in edges.csv; unresolved gold counts as wrong",
        "abstain": "counts as not correct in accuracy; accepted accuracy reported separately",
        "silent_error": "answered AND wrong AND no warning/abstain, over all rows",
        "no_match": "failure WITH warning, never a silent error, always inside the denominator",
    },
    "clusters": {
        "primary": "source unit of the evaluated direction (old unit key for cu_to_moi; new ward code for moi_to_cu)",
        "sensitivity": "leak_guard.admin_group_key(DiaChi_Cu)",
        "e3_primary": "new ward code (23 clusters, the more conservative unit-based option)",
        "bootstrap": "percentile cluster bootstrap, B and seed in manifest",
    },
    "pipeline_span_rule": "rightmost PhuongXa / QuanHuyen / TinhThanh span; absent level = wildcard, ward absent = NO_MATCH",
    "street": {
        "street_key": "normalize_for_overlap with a leading 'đường'/'phố' removed",
        "index_rows": "Data 01 (PhuongXa new ward) + osm_latest_clean (exactly one of PhuongXa/QuanHuyen is a known new ward)",
        "L1": "drop rows whose normalised ChuoiDiaChi equals a Data 07 DiaChi_Moi",
        "L2": "L1 plus drop rows sharing (house number, street_key) with any Data 07 address (empty house number counts as a value)",
        "evidence": "decisive = index narrows the targets to exactly one; otherwise fall back to the default rule (flagged)",
        "low_evidence_rule": f"decisive/multi-candidate rows < {LOW_EVIDENCE_THRESHOLD} -> NOT_EVALUABLE_LOW_EVIDENCE",
        "fallback_flag": "internal marker; not a user-facing warning, so wrong fallback answers are silent errors",
    },
    "situation_c": "Data 06 oracle fields; gold = new unit only; assume_old = cu_to_moi lookup, assume_new = identity check "
                   "in the new table; moi_to_cu has no unique gold (NOT_EVALUABLE_NO_UNIQUE_GOLD)",
    "situation_d": "ward name shared by an old and a new ward in the same new province; classes SAME_SCOPE / "
                   "D_SCOPE_DIFFERS / D_OTHER_TARGET_EDGE_EXISTS / D_DISJOINT from edges",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# CRF worker (stdlib + pycrfsuite only; never imports numpy/pandas)
# ---------------------------------------------------------------------------

def crf_worker(repo: Path, input_path: Path, output_path: Path) -> None:
    sys.path.insert(0, str(repo))
    from src.evaluation.adapters.crf_adapter import IndependentCRFAdapter

    config = json.loads((repo / LOCKED_CONFIG_DIR / "crf-indep" / "model_config.json").read_text(encoding="utf-8"))
    adapter = IndependentCRFAdapter(**{k: str(repo / v) for k, v in config["adapter_kwargs"].items()})
    with input_path.open(encoding="utf-8") as src, output_path.open("w", encoding="utf-8", newline="\n") as dst:
        for line in src:
            item = json.loads(line)  # only {"key", "text"}: no metadata reaches the model
            out = adapter.parse_spans(item["text"], sample_id=item["key"])
            spans = [{"start": s.start, "end": s.end, "label": s.label, "text": s.text} for s in out.spans]
            dst.write(json.dumps({"key": item["key"], "spans": spans, "abstain": out.abstain,
                                  "python": platform.python_version()}, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _fmt(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float):
        return f"{value:.6f}"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: _fmt(row.get(c)) for c in columns})
    return len(rows)


def dump_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
                    encoding="utf-8", newline="\n")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Experiment
# ---------------------------------------------------------------------------

class T2Run:
    def __init__(self, args: argparse.Namespace) -> None:
        sys.path.insert(0, str(REPO))
        import numpy  # noqa: F401  (main runtime only)
        from src.evaluation import t2_lookup, t2_scorer

        self.L, self.S = t2_lookup, t2_scorer
        self.args = args
        out = Path(args.out_dir)
        self.out = out if out.is_absolute() else REPO / out
        self.preds: list[dict] = []
        self.cells: dict[tuple, list[dict]] = {}
        self.unsupported: list[dict] = []
        self.tables: dict[str, tuple[list[dict], list[str]]] = {}
        self.notes: dict = {}
        self.situation_c_exclusions: list[dict] = []

    # -- inputs ---------------------------------------------------------------------

    def load_inputs(self) -> None:
        L = self.L
        self.table = L.T2Table.load(REPO / GAZETTEER_DIR)
        self.sv_index = L.load_single_version_index(REPO / GAZETTEER_DIR, self.table)
        self.rows07 = L.read_csv_rows(REPO / DATA07, DATA07_COLUMNS)
        self.rows06 = L.read_csv_rows(REPO / DATA06, DATA06_COLUMNS)
        ids = [r["ID_Node"] for r in self.rows07]
        if len(set(ids)) != len(ids):
            raise ValueError("ID_Node is not unique in Data 07")
        S = self.S
        self.old07 = [S.split_address(r["DiaChi_Cu"], "old") for r in self.rows07]
        self.new07 = [S.split_address(r["DiaChi_Moi"], "new") for r in self.rows07]
        self.fields_old = [S.lookup_fields(p) for p in self.old07]
        self.fields_new = [S.lookup_fields(p) for p in self.new07]
        self.gold07 = [S.build_pair_gold(self.table, r) for r in self.rows07]
        self.admin07 = [S.admin_cluster(r) for r in self.rows07]

    # -- preflight ------------------------------------------------------------------

    def preflight(self) -> dict:
        from collections import Counter

        L, S, table = self.L, self.S, self.table
        from src.data.administrative_mapping import default_mapping_path, load_administrative_mapping

        mapping = load_administrative_mapping(default_mapping_path())
        edge_pairs = {(e.old_key, e.new_key) for e in table.edges}
        mapping_pairs = {(old, mapping.new_key(t.province, t.ward))
                         for old, targets in mapping.old_to_new.items() for t in targets}
        loai = Counter(r["LoaiAnhXa"] for r in self.rows07)
        observed = {
            "data07_rows": len(self.rows07),
            "data07_loai": dict(loai),
            "data07_codes": len({r["MaPhuongXaMoi"] for r in self.rows07}),
            "data07_old_units_raw": len({(p["province"], p["district"], p["ward"]) for p in self.old07}),
            "data07_ha_noi_rows": sum(1 for f in self.fields_new
                                      if table._canonical_new_province("N1", f["province"]) == "hà nội"),
            "data07_old_parts": {str(k): v for k, v in sorted(Counter(
                len(r["DiaChi_Cu"].split(",")) for r in self.rows07).items())},
            "data07_m_main_form": sum(1 for r in self.rows07
                                      if r["LoaiAnhXa"] == "M" and r["HinhThucSapNhap"] == "Tách — nhập chủ yếu"),
        }
        for level in ("N0", "N1", "N2"):
            observed[f"old_match_{level}"] = sum(
                1 for f in self.fields_old if table.old_to_new_candidates(level, f["province"], f["district"], f["ward"])[0])
            observed[f"new_match_{level}"] = sum(
                1 for f in self.fields_new if table.new_to_old_candidates(level, f["province"], f["ward"])[0])
        fan = {"M": Counter(), "B": Counter()}
        multi = 0
        for r, f in zip(self.rows07, self.fields_old):
            k = len(table.old_to_new_candidates("N1", f["province"], f["district"], f["ward"])[0])
            fan[r["LoaiAnhXa"]][str(k)] += 1
            multi += k > 1
        observed["fanout_N1_M"] = dict(sorted(fan["M"].items()))
        observed["fanout_N1_B"] = dict(sorted(fan["B"].items()))
        observed["multi_candidate_rows_N1"] = multi
        observed["atomic_edges"] = len(table.edges)
        observed["relation_counts"] = dict(sorted(Counter(table.relations.values()).items()))
        observed["merge_form_M"] = dict(sorted(Counter(
            e.merge_form for e in table.edges if table.relations[e.source_row] == "M").items()))
        observed["mapping_only_edges"] = len(mapping_pairs - edge_pairs)
        observed["edges_only_vs_mapping"] = len(edge_pairs - mapping_pairs)
        observed["relation_label_mismatch_vs_file"] = L.graph_analysis(table)["relation_label_mismatch_vs_file"]
        observed["data06_rows"] = len(self.rows06)
        observed["data06_kieulai"] = dict(sorted(Counter(r["KieuLai"].split("_")[0] for r in self.rows06).items()))
        observed["data06_full_old_key_match_N1"] = sum(
            1 for r in self.rows06
            if table.old_to_new_candidates("N1", r["TinhThanh"], r["QuanHuyen"], r["PhuongXa"])[0])
        checks = {name: {"expected": want, "observed": observed.get(name), "ok": observed.get(name) == want}
                  for name, want in EXPECTED.items()}
        extra = {
            "edges_only_vs_mapping": {"expected": 0, "observed": observed["edges_only_vs_mapping"],
                                      "ok": observed["edges_only_vs_mapping"] == 0},
            "old_match_N2": {"expected": "recorded, not asserted", "observed": observed["old_match_N2"], "ok": True},
            "new_match_N1_N2": {"expected": "recorded, not asserted",
                                "observed": [observed["new_match_N1"], observed["new_match_N2"]], "ok": True},
            "gold_pair_edge_exists": {"expected": "recorded", "observed": sum(g.edge_exists for g in self.gold07),
                                      "ok": True},
        }
        checks.update(extra)
        return checks

    # -- model resources --------------------------------------------------------------

    def verify_locked_config(self, model_dir: str) -> dict:
        """Hash every resource listed in a Sprint 3 locked model config against the file on disk."""
        config = json.loads((REPO / LOCKED_CONFIG_DIR / model_dir / "model_config.json").read_text(encoding="utf-8"))
        mismatches = []
        for name, resource in config["resources"].items():
            path = REPO / resource["path"]
            actual = sha256_file(path) if path.exists() else None
            if actual != resource["sha256"]:
                mismatches.append({"resource": name, "path": resource["path"], "locked": resource["sha256"],
                                   "actual": actual})
        return {"config": str(LOCKED_CONFIG_DIR / model_dir / "model_config.json"),
                "config_sha256": sha256_file(REPO / LOCKED_CONFIG_DIR / model_dir / "model_config.json"),
                "adapter_kwargs": config["adapter_kwargs"], "mismatches": mismatches, "ok": not mismatches}

    # -- manifest ---------------------------------------------------------------------

    def write_declared_manifest(self, preflight: dict, models: dict) -> dict:
        inputs = {str(p): sha256_file(REPO / p) for p in (DATA07, DATA06, DATA01, OSM_LATEST)}
        inputs.update({f"{GAZETTEER_DIR}/{name}": digest for name, digest in self.table.source_hashes.items()})
        manifest = {
            "stage": "declared_before_scoring",
            "script_version": SCRIPT_VERSION,
            "rule_versions": {"t2_lookup": self.L.RULE_VERSION},
            "created_at": now_iso(),
            "python": platform.python_version(),
            "seeds": {"bootstrap_seed": CI_SEED, "bootstrap_resamples": self.args.resamples,
                      "sampling": "none (full Data 07 / Data 06, no sampling)"},
            "systems": SYSTEM_DEFINITIONS,
            "conditions": ["oracle", "pipeline:HEUR-JW", "pipeline:CRF-INDEP"],
            "normalisation_levels": list(self.L.LEVELS),
            "rules": DECLARED_RULES,
            "tiers": {
                "tier1": "STRICT/MAIN/FIRST x oracle x N2 x both directions; E3; graph analysis",
                "tier2": "N0/N1 sensitivity; T2-VNADMIN; T2-SINGLE-VERSION; situations C and D",
                "tier3": {"pipeline": "NOT_RUN" if self.args.skip_pipeline else "RUN",
                          "street": "NOT_RUN" if self.args.skip_street else "RUN"},
            },
            "preflight_checks": preflight,
            "pipeline_models": models,
            "input_sha256": inputs,
            "source_sha256": {p: sha256_file(REPO / p) for p in SOURCE_FILES},
            "rows_in": {"data07": len(self.rows07), "data06": len(self.rows06)},
        }
        dump_json(self.out / "run_manifest.json", manifest)
        return manifest

    # -- recording --------------------------------------------------------------------

    def record(self, dataset: str, rid: str, direction: str, system: str, condition: str, level: str,
               fields: dict, res, outcome: dict, extra: dict | None = None) -> None:
        self.preds.append({
            "dataset": dataset, "ID_Node": rid, "direction": direction, "system": system, "condition": condition,
            "level": level, "input": fields, "n_candidates": len(res.candidates),
            "candidates": [c.cid for c in res.candidates], "answer": res.answer.cid if res.answer else None,
            "answer_name": res.answer.display() if res.answer else None,
            "answer_code": res.answer.code if res.answer else None,
            "abstain": outcome["abstain"], "warning": res.warning, "correct": outcome["correct"],
            "silent_error": outcome["silent"], "reason": res.reason, "flags": res.flags, **(extra or {}),
        })

    def add07(self, i: int, direction: str, system: str, condition: str, level: str, fields: dict, res,
              extra: dict | None = None, flags_record: dict | None = None) -> None:
        S, L = self.S, self.L
        gold, row = self.gold07[i], self.rows07[i]
        if direction == L.OLD_TO_NEW:
            gold_key = gold.new.key if gold.new else None
            outcome = S.score_resolution(res, gold_key, row["MaPhuongXaMoi"])
            cluster = gold.old_cluster
        else:
            gold_key = gold.old.key if gold.old else None
            outcome = S.score_resolution(res, gold_key, "")
            cluster = gold.new_cluster
        rec = {**outcome, "i": i, "cluster": cluster, "loai": row["LoaiAnhXa"], "hinhthuc": row["HinhThucSapNhap"],
               "gold_key": gold_key, **(flags_record or {})}
        self.cells.setdefault((system, direction, condition, level), []).append(rec)
        self.record("data07", row["ID_Node"], direction, system, condition, level, fields, res, outcome, extra)

    # -- run: oracle conditions -------------------------------------------------------

    def run_oracle(self) -> None:
        L = self.L
        n = len(self.rows07)
        for system in L.LOOKUP_SYSTEMS:
            for level in L.LEVELS:
                for i in range(n):
                    self.add07(i, L.OLD_TO_NEW, system, "oracle", level, self.fields_old[i],
                               L.resolve_lookup(self.table, system, L.OLD_TO_NEW, level, self.fields_old[i]))
                    self.add07(i, L.NEW_TO_OLD, system, "oracle", level, self.fields_new[i],
                               L.resolve_lookup(self.table, system, L.NEW_TO_OLD, level, self.fields_new[i]))
        for i in range(n):
            self.add07(i, L.OLD_TO_NEW, L.SINGLE_VERSION, "oracle", MAIN_LEVEL, self.fields_old[i],
                       self.sv_index.resolve(L.OLD_TO_NEW, MAIN_LEVEL, self.fields_old[i]))
            self.add07(i, L.NEW_TO_OLD, L.SINGLE_VERSION, "oracle", MAIN_LEVEL, self.fields_new[i],
                       self.sv_index.resolve(L.NEW_TO_OLD, MAIN_LEVEL, self.fields_new[i]))

    def run_vnadmin(self) -> None:
        L = self.L
        outputs = L.run_vnadmin([r["DiaChi_Cu"] for r in self.rows07])
        self.vnadmin_outputs = outputs
        for i, output in enumerate(outputs):
            res = L.vnadmin_resolution(self.table, output)
            self.add07(i, L.OLD_TO_NEW, L.VNADMIN, "oracle", "NA", {"address": self.rows07[i]["DiaChi_Cu"]}, res)
        self.unsupported.append({"system": L.VNADMIN, "direction": L.NEW_TO_OLD, "condition": "oracle",
                                 "level": "NA", "status": self.S.NOT_SUPPORTED,
                                 "reason": "library converts old -> 2025 only"})

    # -- run: street evidence (E2) ---------------------------------------------------

    def run_street(self) -> None:
        L, S = self.L, self.S
        data01 = L.read_csv_rows(REPO / DATA01, DATA01_COLUMNS)
        osm = L.read_csv_rows(REPO / OSM_LATEST, OSM_COLUMNS)
        exclude_texts = {L.normalize_for_overlap(r["DiaChi_Moi"]) for r in self.rows07}
        pairs = set()
        for parsed in self.old07 + self.new07:
            house, street = S.house_and_street(parsed["head"])
            pairs.add((L.normalize_for_overlap(house), L.street_key(street)))
        indexes = {
            "L1": L.build_street_index(self.table, data01, osm, exclude_texts, None),
            "L2": L.build_street_index(self.table, data01, osm, exclude_texts, pairs),
        }
        self.street_indexes = indexes
        self.data07_streets = {S.house_and_street(p["head"])[1] for p in self.old07}
        for system, (leak, fallback) in STREET_VARIANTS.items():
            for i in range(len(self.rows07)):
                street = S.house_and_street(self.old07[i]["head"])[1]
                res = L.resolve_street(self.table, indexes[leak], fallback, MAIN_LEVEL, self.fields_old[i], street)
                extra = {"street_query": L.street_key(street)}
                flag_rec = {"evidence": res.flags.get("evidence"), "multi": res.flags.get("multi_candidate", False),
                            "fallback_used": res.flags.get("fallback_used", False)}
                self.add07(i, L.OLD_TO_NEW, system, "oracle", MAIN_LEVEL, self.fields_old[i], res, extra, flag_rec)
            self.unsupported.append({"system": system, "direction": L.NEW_TO_OLD, "condition": "oracle",
                                     "level": MAIN_LEVEL, "status": S.NOT_SUPPORTED,
                                     "reason": "street evidence is defined for old -> new target selection"})

    # -- run: pipeline condition ------------------------------------------------------

    def run_pipeline(self, workdir: Path) -> dict:
        L = self.L
        workdir.mkdir(parents=True, exist_ok=True)
        texts = workdir / "pipeline_inputs.jsonl"
        with texts.open("w", encoding="utf-8", newline="\n") as stream:
            for r in self.rows07:  # only an opaque key and the text; no metadata
                stream.write(json.dumps({"key": f"{r['ID_Node']}|cu", "text": r["DiaChi_Cu"]}, ensure_ascii=False) + "\n")
                stream.write(json.dumps({"key": f"{r['ID_Node']}|moi", "text": r["DiaChi_Moi"]}, ensure_ascii=False) + "\n")

        spans: dict[str, dict] = {}
        # HEUR-JW in the main runtime with the locked arguments.
        config = json.loads((REPO / LOCKED_CONFIG_DIR / "heur-jw" / "model_config.json").read_text(encoding="utf-8"))
        from src.evaluation.adapters.heur_jw_followup import HeuristicJaroWinklerFollowup

        kwargs = dict(config["adapter_kwargs"])
        kwargs["gazetteer_dir"] = str(REPO / kwargs["gazetteer_dir"])
        heur = HeuristicJaroWinklerFollowup(**kwargs)
        heur_out = workdir / "heur_jw_spans.jsonl"
        heur_spans = {}
        with texts.open(encoding="utf-8") as src, heur_out.open("w", encoding="utf-8", newline="\n") as dst:
            for line in src:
                item = json.loads(line)
                out = heur.parse_spans(item["text"], sample_id=item["key"])
                sp = [{"start": s.start, "end": s.end, "label": s.label, "text": s.text} for s in out.spans]
                heur_spans[item["key"]] = sp
                dst.write(json.dumps({"key": item["key"], "spans": sp, "abstain": out.abstain}, ensure_ascii=False) + "\n")
        spans["HEUR-JW"] = heur_spans

        # CRF-INDEP in its own runtime (separate process, pycrfsuite only).
        crf_out = workdir / "crf_indep_spans.jsonl"
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        cmd = [str(REPO / CRF_RUNTIME), str(REPO / "scripts" / "66_run_t2_baseline.py"), "--crf-worker",
               "--worker-in", str(texts), "--worker-out", str(crf_out), "--repo", str(REPO)]
        subprocess.run(cmd, check=True, env=env, cwd=str(REPO))
        crf_spans = {}
        crf_python = ""
        for line in crf_out.read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            crf_spans[item["key"]] = item["spans"]
            crf_python = item["python"]
        spans["CRF-INDEP"] = crf_spans

        missing = {}
        for model, by_key in spans.items():
            counters = {"strings": 0, "no_ward": 0, "no_province": 0, "no_district_old": 0}
            for i, r in enumerate(self.rows07):
                old_f = L.fields_from_spans(by_key[f"{r['ID_Node']}|cu"])
                new_f = L.fields_from_spans(by_key[f"{r['ID_Node']}|moi"])
                counters["strings"] += 2
                counters["no_ward"] += (not old_f["ward"]) + (not new_f["ward"])
                counters["no_province"] += (not old_f["province"]) + (not new_f["province"])
                counters["no_district_old"] += not old_f["district"]
                for system in L.LOOKUP_SYSTEMS:
                    cond = f"pipeline:{model}"
                    self.add07(i, L.OLD_TO_NEW, system, cond, MAIN_LEVEL, old_f,
                               L.resolve_lookup(self.table, system, L.OLD_TO_NEW, MAIN_LEVEL, old_f))
                    self.add07(i, L.NEW_TO_OLD, system, cond, MAIN_LEVEL, {k: new_f[k] for k in ("province", "ward")},
                               L.resolve_lookup(self.table, system, L.NEW_TO_OLD, MAIN_LEVEL, new_f))
            missing[model] = counters
        return {"missing_spans": missing, "crf_python": crf_python,
                "span_files_sha256": {p.name: sha256_file(p) for p in (heur_out, crf_out, texts)}}

    # -- run: H5 situation C (Data 06) -------------------------------------------------

    def run_situation_c(self) -> list[dict]:
        L, S, table = self.L, self.S, self.table
        outcome_rows = []
        systems = list(L.LOOKUP_SYSTEMS) + [L.SINGLE_VERSION]
        for j, row in enumerate(self.rows06):
            fields = {"province": row["TinhThanh"], "district": row["QuanHuyen"], "ward": row["PhuongXa"]}
            gold_key, excluded = S.situation_c_gold(table, row)  # KieuLai is read on the scoring side only
            kind = row["KieuLai"].split("_")[0]
            if excluded and not any(d["row"] == f"d06:{j}" for d in self.situation_c_exclusions):
                wildcard = table.old_to_new_candidates("N2", "", row["QuanHuyen"], row["PhuongXa"])[0]
                self.situation_c_exclusions.append({
                    "row": f"d06:{j}", "kieulai": kind, "reason": excluded, "text": row["ChuoiDiaChi"],
                    "targets_if_province_ignored": [c.display() for c in wildcard]})
            for assumption in ("assume_old", "assume_new"):
                for system in systems:
                    if system == L.SINGLE_VERSION:
                        res = self.sv_index.resolve(L.OLD_TO_NEW, MAIN_LEVEL, fields)  # version-blind: same for both
                    elif assumption == "assume_old":
                        res = L.resolve_lookup(table, system, L.OLD_TO_NEW, MAIN_LEVEL, fields)
                    else:
                        res = L.resolve_identity_new(table, system, MAIN_LEVEL, fields)
                    outcome = S.score_resolution(res, gold_key)
                    if excluded:
                        category = "EXCLUDED_" + excluded
                    elif res.status == "ANSWER":
                        category = "MATCH_CORRECT" if outcome["correct"] else "MATCH_WRONG_SILENT"
                    else:
                        category = res.reason
                    self.record("data06", f"d06:{j}", "cu_to_moi_target_new", system, f"situation_c:{assumption}",
                                MAIN_LEVEL, fields, res, outcome, {"category": category})
                    outcome_rows.append({"system": system, "assumption": assumption, "kieulai": kind,
                                         "category": category})
        return outcome_rows

    # -- metrics ----------------------------------------------------------------------

    def summarise_cells(self) -> list[dict]:
        S = self.S
        rows = []
        for (system, direction, condition, level), records in sorted(self.cells.items()):
            for stype, svalue, subset in S.slice_defs(records):
                full_ci = condition == "oracle" and level == MAIN_LEVEL
                with_ci = bool(subset) and (stype == "ALL" or full_ci)
                summary = S.summarize_cell(subset, with_ci=with_ci, n_resamples=self.args.resamples)
                rows.append({"system": system, "direction": direction, "condition": condition, "level": level,
                             "slice_type": stype, "slice": svalue, **summary})
        for item in self.unsupported:
            for stype, svalue in self._slice_names():
                rows.append({**item, "slice_type": stype, "slice": svalue, "n": None})
        return rows

    def _slice_names(self):
        yield "ALL", "ALL"
        for letter in self.S.RELATION_LETTERS:
            yield "LoaiAnhXa", letter
        for form in self.S.MERGE_FORMS:
            yield "HinhThucSapNhap", form

    def cluster_sensitivity(self) -> list[dict]:
        S = self.S
        rows = []
        for (system, direction, condition, level), records in sorted(self.cells.items()):
            if condition != "oracle" or level not in (MAIN_LEVEL, "NA"):
                continue
            primary = S.summarize_cell(records, with_ci=True, n_resamples=self.args.resamples)
            relabelled = [{**r, "cluster": self.admin07[r["i"]]} for r in records]
            admin = S.summarize_cell(relabelled, with_ci=True, n_resamples=self.args.resamples)
            for name, summary in (("source_unit", primary), ("admin_group_key", admin)):
                rows.append({"system": system, "direction": direction, "cluster_definition": name, "n": summary["n"],
                             "n_clusters": summary.get("n_clusters"), "accuracy": summary["accuracy"],
                             "accuracy_ci_low": summary.get("accuracy_ci_low"),
                             "accuracy_ci_high": summary.get("accuracy_ci_high"),
                             "silent_error_rate": summary["silent_error_rate"],
                             "silent_ci_low": summary.get("silent_ci_low"),
                             "silent_ci_high": summary.get("silent_ci_high"),
                             "largest_cluster_share": (
                                 max(__import__("collections").Counter(
                                     r["cluster"] for r in (records if name == "source_unit" else relabelled)).values())
                                 / summary["n"])})
        return rows

    def asymmetry(self) -> list[dict]:
        S, L = self.S, self.L
        rows = []
        clusters = {"old_unit": [g.old_cluster for g in self.gold07], "new_ward": [g.new_cluster for g in self.gold07],
                    "admin_group_key": self.admin07}
        conditions = ["oracle", "pipeline:HEUR-JW", "pipeline:CRF-INDEP"]
        for condition in conditions:
            for system in list(L.LOOKUP_SYSTEMS) + [L.SINGLE_VERSION]:
                fwd = self.cells.get((system, L.OLD_TO_NEW, condition, MAIN_LEVEL))
                back = self.cells.get((system, L.NEW_TO_OLD, condition, MAIN_LEVEL))
                if not fwd or not back:
                    continue
                for stype, svalue, _ in S.slice_defs(fwd):
                    if stype not in ("ALL", "LoaiAnhXa") or (stype == "LoaiAnhXa" and svalue not in ("B", "M")):
                        continue
                    idx = [k for k, r in enumerate(fwd)
                           if stype == "ALL" or r["loai"] == svalue]
                    a = [fwd[k]["correct"] for k in idx]
                    b = [back[k]["correct"] for k in idx]
                    cmp_ = S.paired_comparison(a, b, {name: [ids[fwd[k]["i"]] for k in idx] for name, ids in clusters.items()},
                                               n_resamples=self.args.resamples)
                    row = {"system": system, "condition": condition, "level": MAIN_LEVEL, "slice": f"{stype}={svalue}",
                           "n": cmp_["n"], "status": cmp_["status"],
                           "acc_cu_to_moi": cmp_.get("accuracy_a"), "acc_moi_to_cu": cmp_.get("accuracy_b"),
                           "delta": cmp_.get("delta"), "fwd_right_back_wrong": cmp_.get("a_right_b_wrong"),
                           "fwd_wrong_back_right": cmp_.get("a_wrong_b_right"), "both_right": cmp_.get("both_right"),
                           "both_wrong": cmp_.get("both_wrong"),
                           "mcnemar_p": (cmp_.get("mcnemar") or {}).get("p_value"),
                           "mcnemar_status": (cmp_.get("mcnemar") or {}).get("status")}
                    for name in clusters:
                        ci = cmp_.get(f"delta_ci_{name}", {})
                        row[f"delta_ci_low_{name}"] = ci.get("ci_low")
                        row[f"delta_ci_high_{name}"] = ci.get("ci_high")
                        row[f"n_clusters_{name}"] = ci.get("n_clusters")
                        row[f"ci_status_{name}"] = ci.get("status")
                    rows.append(row)
        for system in ("T2-VNADMIN",) + tuple(STREET_VARIANTS):
            rows.append({"system": system, "condition": "oracle", "level": MAIN_LEVEL, "slice": "ALL",
                         "status": S.NOT_SUPPORTED})
        return rows

    def street_tables(self) -> tuple[list[dict], list[dict], dict]:
        L, S = self.L, self.S
        clusters = [g.old_cluster for g in self.gold07]
        rows, index_rows = [], []
        evidence_summary = {}
        for leak in ("L1", "L2"):
            rep = self.street_indexes[leak].report
            base = self.cells[(f"T2-STREET-{leak}-MAIN", L.OLD_TO_NEW, "oracle", MAIN_LEVEL)]
            multi = [r for r in base if r["multi"]]
            decisive = [r for r in multi if r["evidence"] == "decisive"]
            narrowed = [r for r in multi if r["evidence"] in ("decisive", "narrowed_not_unique")]
            rate = (len(decisive) / len(multi)) if multi else None
            status = ("NOT_EVALUABLE_NO_SUPPORT" if not multi
                      else (S.LOW_EVIDENCE if rate < LOW_EVIDENCE_THRESHOLD else "OK"))
            overlap = sum(1 for r in base if self._street_in_data07_index(leak, r["i"]))
            evidence_summary[leak] = {"status": status, "multi_candidate_rows": len(multi), "decisive_rows": len(decisive),
                                      "narrowed_rows": len(narrowed), "evidence_rate_decisive": rate,
                                      "evidence_rate_over_all_600": len(decisive) / len(base),
                                      "rows_with_street_in_index": overlap}
            index_rows.append({"leak_filter": leak, **rep, **{f"evidence_{k}": v for k, v in evidence_summary[leak].items()}})
            for fallback in ("main", "first"):
                default = self.cells[(L.DEFAULT_MAIN if fallback == "main" else L.DEFAULT_FIRST,
                                      L.OLD_TO_NEW, "oracle", MAIN_LEVEL)]
                street = self.cells[(f"T2-STREET-{leak}-{fallback.upper()}", L.OLD_TO_NEW, "oracle", MAIN_LEVEL)]
                for name, pick in (("ALL", lambda r: True), ("LoaiAnhXa=M", lambda r: r["loai"] == "M"),
                                   ("LoaiAnhXa=B", lambda r: r["loai"] == "B"),
                                   ("multi_candidate", lambda r: r["multi"]),
                                   ("decisive_evidence", lambda r: r["evidence"] == "decisive")):
                    idx = [k for k, r in enumerate(street) if pick(r)]
                    cmp_ = S.paired_comparison([street[k]["correct"] for k in idx], [default[k]["correct"] for k in idx],
                                               {"old_unit": [clusters[street[k]["i"]] for k in idx]},
                                               n_resamples=self.args.resamples) if idx else {"n": 0, "status": S.NO_SUPPORT}
                    ci = cmp_.get("delta_ci_old_unit", {})
                    rows.append({
                        "leak_filter": leak, "fallback": fallback.upper(), "slice": name,
                        "status": S.LOW_EVIDENCE if status == S.LOW_EVIDENCE else cmp_["status"],
                        "n": cmp_["n"], "acc_street": cmp_.get("accuracy_a"), "acc_default": cmp_.get("accuracy_b"),
                        "delta": cmp_.get("delta"), "street_right_default_wrong": cmp_.get("a_right_b_wrong"),
                        "street_wrong_default_right": cmp_.get("a_wrong_b_right"),
                        "mcnemar_p": (cmp_.get("mcnemar") or {}).get("p_value"),
                        "delta_ci_low": ci.get("ci_low"), "delta_ci_high": ci.get("ci_high"),
                        "n_clusters": ci.get("n_clusters"), "ci_status": ci.get("status"),
                        "street_silent_errors": sum(street[k]["silent"] for k in idx) if idx else None,
                        "default_silent_errors": sum(default[k]["silent"] for k in idx) if idx else None,
                        "fallback_rows_in_slice": sum(1 for k in idx if street[k]["fallback_used"]) if idx else None,
                    })
        return rows, index_rows, evidence_summary

    def _street_in_data07_index(self, leak: str, i: int) -> bool:
        street = self.S.house_and_street(self.old07[i]["head"])[1]
        return bool(self.street_indexes[leak].wards_for(street))

    def situation_d(self) -> tuple[list[dict], dict]:
        L, S = self.L, self.S
        graph = S.GraphView(self.table)
        census = S.homonym_census(self.table, graph, self.sv_index)
        labels = {}
        for direction in (L.OLD_TO_NEW, L.NEW_TO_OLD):
            labels[direction] = [S.homonym_label(graph, self.sv_index, direction, g.old, g.new) for g in self.gold07]
        rows = []
        for direction in (L.OLD_TO_NEW, L.NEW_TO_OLD):
            records = self.cells[(L.SINGLE_VERSION, direction, "oracle", MAIN_LEVEL)]
            groups = {}
            for rec, label in zip(records, labels[direction]):
                groups.setdefault(label, []).append(rec)
            order = ["NO_HOMONYM", "SAME_SCOPE", "D_SCOPE_DIFFERS", "D_OTHER_TARGET_EDGE_EXISTS", "D_DISJOINT",
                     "GOLD_UNRESOLVED"]
            d_group = [r for label in ("D_SCOPE_DIFFERS", "D_OTHER_TARGET_EDGE_EXISTS", "D_DISJOINT")
                       for r in groups.get(label, [])]
            for label, recs in [(label, groups.get(label, [])) for label in order] + [("D_GROUP_ALL", d_group)]:
                n = len(recs)
                rows.append({
                    "system": L.SINGLE_VERSION, "direction": direction, "group": label, "n": n,
                    "status": "OK" if n else S.NO_SUPPORT,
                    "correct": sum(r["correct"] for r in recs) if n else None,
                    "abstain_warned": sum(r["abstain"] for r in recs) if n else None,
                    "silent_errors": sum(r["silent"] for r in recs) if n else None,
                    "silent_error_rate_in_group": (sum(r["silent"] for r in recs) / n) if n else None,
                    "share_of_600": n / len(records),
                })
        return rows, census

    def situation_c_tables(self, outcome_rows: list[dict]) -> list[dict]:
        from collections import Counter

        L, S = self.L, self.S
        rows = []
        categories = ["NO_MATCH", "AMBIGUOUS", "NON_ATOMIC", "MATCH_CORRECT", "MATCH_WRONG_SILENT"]
        for assumption in ("assume_old", "assume_new"):
            for system in list(L.LOOKUP_SYSTEMS) + [L.SINGLE_VERSION]:
                subset = [x for x in outcome_rows if x["system"] == system and x["assumption"] == assumption]
                for kind in ("ALL", "C1", "C2", "C3"):
                    part = [x for x in subset if kind == "ALL" or x["kieulai"] == kind]
                    excluded = [x for x in part if x["category"].startswith("EXCLUDED_")]
                    evaluated = [x for x in part if not x["category"].startswith("EXCLUDED_")]
                    count = Counter(x["category"] for x in evaluated)
                    n_eval = len(evaluated)
                    row = {"assumption": assumption, "system": system, "direction": L.OLD_TO_NEW + "->target_new",
                           "kieulai": kind, "n_total": len(part), "n_excluded_no_gold": len(excluded),
                           "excluded_reasons": dict(Counter(x["category"] for x in excluded)), "n_evaluated": n_eval,
                           "status": "OK" if n_eval else S.NO_SUPPORT}
                    for cat in categories:
                        row[cat] = count.get(cat, 0)
                        row[f"{cat}_rate"] = (count.get(cat, 0) / n_eval) if n_eval else None
                    rows.append(row)
            rows.append({"assumption": assumption, "system": "ALL_SYSTEMS", "direction": L.NEW_TO_OLD,
                         "kieulai": "ALL", "status": S.NO_UNIQUE_GOLD,
                         "excluded_reasons": "N-1 target set has no unique old gold"})
        return rows

    # -- tables -----------------------------------------------------------------------

    def sensitivity_rows(self, metrics_rows: list[dict]) -> list[dict]:
        keep = ("system", "direction", "level", "n", "answered", "coverage", "accuracy", "accepted_accuracy",
                "no_match", "no_match_rate", "ambiguous_abstain", "candidate_recall", "silent_errors",
                "silent_error_rate", "share_multi_candidate", "status")
        return [{k: r.get(k) for k in keep} for r in metrics_rows
                if r["condition"] == "oracle" and r["slice"] == "ALL"
                and r["system"] in self.L.LOOKUP_SYSTEMS]

    def input_matching_rows(self) -> list[dict]:
        from collections import Counter

        L = self.L
        rows = []
        for side, fields in (("old", self.fields_old), ("new", self.fields_new)):
            for level in L.LEVELS:
                matched = Counter()
                for r, f in zip(self.rows07, fields):
                    if side == "old":
                        cands = self.table.old_to_new_candidates(level, f["province"], f["district"], f["ward"])[0]
                    else:
                        cands = self.table.new_to_old_candidates(level, f["province"], f["ward"])[0]
                    matched[("ALL", "ALL", bool(cands))] += 1
                    matched[("LoaiAnhXa", r["LoaiAnhXa"], bool(cands))] += 1
                for (stype, svalue), total in sorted({(k[0], k[1]): 0 for k in matched}.items()):
                    hit = matched.get((stype, svalue, True), 0)
                    miss = matched.get((stype, svalue, False), 0)
                    rows.append({"side": side, "level": level, "slice_type": stype, "slice": svalue, "n": hit + miss,
                                 "key_matched": hit, "no_key_match": miss,
                                 "key_match_rate": hit / (hit + miss) if hit + miss else None})
        return rows

    def fanout_rows(self) -> list[dict]:
        from collections import Counter

        L = self.L
        rows = []
        for level in (MAIN_LEVEL, "N1"):
            for direction, fields in ((L.OLD_TO_NEW, self.fields_old), (L.NEW_TO_OLD, self.fields_new)):
                dist: dict[tuple, Counter] = {}
                for r, f in zip(self.rows07, fields):
                    if direction == L.OLD_TO_NEW:
                        k = len(self.table.old_to_new_candidates(level, f["province"], f["district"], f["ward"])[0])
                    else:
                        k = len(self.table.new_to_old_candidates(level, f["province"], f["ward"])[0])
                    dist.setdefault(("ALL", "ALL"), Counter())[k] += 1
                    dist.setdefault(("LoaiAnhXa", r["LoaiAnhXa"]), Counter())[k] += 1
                for (stype, svalue), counter in sorted(dist.items()):
                    n = sum(counter.values())
                    for k, count in sorted(counter.items()):
                        rows.append({"level": level, "direction": direction, "slice_type": stype, "slice": svalue,
                                     "n_candidates": k, "rows": count, "share": count / n, "n": n})
        return rows

    def ceiling_rows(self) -> list[dict]:
        L, S = self.L, self.S
        rows = []
        for direction in (L.OLD_TO_NEW, L.NEW_TO_OLD):
            records = self.cells[(L.DEFAULT_MAIN, direction, "oracle", MAIN_LEVEL)]
            for stype, svalue, subset in S.slice_defs(records):
                ceiling = S.unit_constant_ceiling(subset, [r["gold_key"] for r in subset])
                rows.append({"direction": direction, "slice_type": stype, "slice": svalue, "n": len(subset),
                             "unit_constant_ceiling": ceiling,
                             "status": "OK" if subset else S.NO_SUPPORT,
                             "note": "best accuracy of any rule returning one fixed target per source unit on Data 07"})
        return rows

    def vnadmin_rows(self) -> list[dict]:
        from collections import Counter

        L = self.L
        rows = []
        records = self.cells[(L.VNADMIN, L.OLD_TO_NEW, "oracle", "NA")]
        for stype, svalue, subset in self.S.slice_defs(records):
            paths = Counter(self.vnadmin_outputs[r["i"]]["selection_path"] for r in subset)
            empty = sum(1 for r in subset if self.vnadmin_outputs[r["i"]]["error"] or not self.vnadmin_outputs[r["i"]]["ward"])
            geo = Counter(self.vnadmin_outputs[r["i"]]["geocoder_status"] for r in subset)
            if not subset:
                rows.append({"slice_type": stype, "slice": svalue, "n": 0, "status": self.S.NO_SUPPORT})
                continue
            for path, count in sorted(paths.items()):
                rows.append({"slice_type": stype, "slice": svalue, "selection_path": path, "n": len(subset), "rows": count,
                             "share": count / len(subset), "empty_or_error_rows": empty,
                             "geocoder_status": geo, "status": "OK"})
        return rows

    # -- orchestration ------------------------------------------------------------------

    def execute(self) -> int:
        started = time.time()
        out = self.out
        if out.exists():
            print(f"REFUSED: {out} already exists (no overwrite); choose a new _vN directory", file=sys.stderr)
            return 3
        self.load_inputs()
        checks = self.preflight()
        failed = {k: v for k, v in checks.items() if not v["ok"]}
        if failed:
            print("PREFLIGHT MISMATCH: stop before writing any system.", file=sys.stderr)
            print(json.dumps(failed, ensure_ascii=False, indent=2), file=sys.stderr)
            return 2
        models = {}
        if not self.args.skip_pipeline:
            models = {"HEUR-JW": self.verify_locked_config("heur-jw"), "CRF-INDEP": self.verify_locked_config("crf-indep")}
        out.mkdir(parents=True)
        manifest = self.write_declared_manifest(checks, models)  # systems/rules/seeds are fixed from here on
        L, S = self.L, self.S

        self.run_oracle()
        self.run_vnadmin()
        pipeline_info = {"status": "NOT_RUN"}
        if not self.args.skip_pipeline:
            blocked = [m for m, info in models.items() if not info["ok"]]
            if blocked:
                pipeline_info = {"status": "BLOCKED", "reason": "locked resource hash mismatch", "models": blocked}
            else:
                pipeline_info = {"status": "RUN", **self.run_pipeline(out / "pipeline")}
        street_evidence = {}
        if not self.args.skip_street:
            self.run_street()
        situation_c_rows = self.run_situation_c()

        metrics_rows = self.summarise_cells()
        metric_columns = [
            "system", "direction", "condition", "level", "slice_type", "slice", "status", "reason", "n", "answered",
            "correct", "abstain", "no_match", "ambiguous_abstain", "accuracy", "accuracy_ci_low", "accuracy_ci_high",
            "n_clusters", "accepted_accuracy", "coverage", "abstain_rate", "no_match_rate", "candidate_recall",
            "n_matched", "candidates_mean_matched", "candidates_median_matched", "share_multi_candidate",
            "silent_errors", "silent_error_rate", "silent_ci_low", "silent_ci_high", "macro_accuracy", "n_units",
            "largest_unit", "largest_unit_pairs", "accuracy_ci_status", "silent_ci_status", "ci_method",
        ]
        tables: dict[str, tuple[list[dict], list[str]]] = {"t2_metrics_all": (metrics_rows, metric_columns)}
        main_rows = [r for r in metrics_rows if r.get("condition") == "oracle" and r.get("level") in (MAIN_LEVEL, "NA")]
        tables["t2_main_oracle_n2"] = (main_rows, metric_columns)
        sens = self.sensitivity_rows(metrics_rows)
        tables["t2_sensitivity_normalisation"] = (sens, list(sens[0]))
        matching = self.input_matching_rows()
        tables["t2_input_matching"] = (matching, list(matching[0]))
        fan = self.fanout_rows()
        tables["t2_fanout_data07"] = (fan, list(fan[0]))
        e3 = self.asymmetry()
        e3_columns = sorted({k for r in e3 for k in r}, key=lambda k: (k not in ("system", "condition", "level", "slice"), k))
        tables["t2_e3_asymmetry"] = (e3, e3_columns)
        sensitivity = self.cluster_sensitivity()
        tables["t2_cluster_sensitivity"] = (sensitivity, list(sensitivity[0]))
        ceiling = self.ceiling_rows()
        tables["t2_unit_constant_ceiling"] = (ceiling, list(ceiling[0]))
        vn = self.vnadmin_rows()
        tables["t2_vnadmin_paths"] = (vn, sorted({k for r in vn for k in r}))
        pipe_rows = [r for r in metrics_rows if str(r.get("condition", "")).startswith("pipeline:")]
        if pipe_rows:
            tables["t2_pipeline"] = (pipe_rows, metric_columns)
        if not self.args.skip_street:
            e2, index_rows, street_evidence = self.street_tables()
            tables["t2_e2_street"] = (e2, sorted({k for r in e2 for k in r}, key=lambda k: (k not in ("leak_filter", "fallback", "slice"), k)))
            tables["t2_e2_street_index"] = (index_rows, sorted({k for r in index_rows for k in r}))
        c_rows = self.situation_c_tables(situation_c_rows)
        tables["t2_h5_situation_c"] = (c_rows, sorted({k for r in c_rows for k in r}, key=lambda k: (k not in ("assumption", "system", "direction", "kieulai"), k)))
        d_rows, census = self.situation_d()
        tables["t2_h5_situation_d_data07"] = (d_rows, list(d_rows[0]))
        census_rows = [{"metric": k, "value": v} for k, v in census.items()]
        tables["t2_h5_situation_d_census"] = (census_rows, ["metric", "value"])

        graph = L.graph_analysis(self.table)
        dump_json(out / "graph_analysis.json", graph)
        graph_fan = [{"direction": d, "fan": k, "keys": v} for d, dist in
                     (("old_to_new_fan_out", graph["fan_out_old_key"]), ("new_to_old_fan_in", graph["fan_in_new_key"]))
                     for k, v in dist.items()]
        tables["t2_graph_fanout"] = (graph_fan, ["direction", "fan", "keys"])
        graph_rel = [{"relation": rel, **{k: v for k, v in info.items() if k not in ("fan_out_per_edge", "fan_in_per_edge")},
                      "fan_out_per_edge": info["fan_out_per_edge"], "fan_in_per_edge": info["fan_in_per_edge"]}
                     for rel, info in graph["by_relation"].items()]
        tables["t2_graph_by_relation"] = (graph_rel, list(graph_rel[0]))

        table_counts = {}
        for name, (rows, columns) in tables.items():
            table_counts[name] = write_csv(out / "tables" / f"{name}.csv", rows, columns)

        with (out / "predictions.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
            for row in self.preds:
                stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        dump_json(out / "metrics.json", {
            "label": "T2 baseline; Data 07 accuracy is circular w.r.t. edges.csv (see report), graph rows are structural",
            "metrics": metrics_rows, "asymmetry_e3": e3, "cluster_sensitivity": sensitivity,
            "street": {"evidence": street_evidence, "status": "NOT_RUN" if self.args.skip_street else "RUN"},
            "situation_d_census": census, "pipeline": pipeline_info,
            "situation_c_exclusions": self.situation_c_exclusions,
            "unsupported": self.unsupported, "unit_constant_ceiling": ceiling,
        })

        manifest.update({
            "stage": "completed", "finished_at": now_iso(), "elapsed_seconds": round(time.time() - started, 1),
            "rows_out": {"predictions": len(self.preds), "metric_rows": len(metrics_rows), **{f"table:{k}": v for k, v in table_counts.items()}},
            "pipeline": pipeline_info,
            "output_sha256": {str(p.relative_to(out)): sha256_file(p) for p in sorted(out.rglob("*"))
                              if p.is_file() and p.name != "run_manifest.json"},
        })
        dump_json(out / "run_manifest.json", manifest)
        print(f"done: {len(self.preds)} predictions, {len(tables)} tables -> {out}")
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--resamples", type=int, default=10_000)
    parser.add_argument("--skip-pipeline", action="store_true", help="tier 3 pipeline condition -> NOT_RUN")
    parser.add_argument("--skip-street", action="store_true", help="tier 3 T2-STREET -> NOT_RUN")
    parser.add_argument("--crf-worker", action="store_true")
    parser.add_argument("--worker-in", type=Path)
    parser.add_argument("--worker-out", type=Path)
    parser.add_argument("--repo", type=Path, default=REPO)
    args = parser.parse_args(argv)
    if args.crf_worker:
        crf_worker(args.repo, args.worker_in, args.worker_out)
        return 0
    return T2Run(args).execute()


if __name__ == "__main__":
    raise SystemExit(main())
