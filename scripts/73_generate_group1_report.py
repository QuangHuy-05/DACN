"""WP6: cross-check the Group 1 runs and generate the tables/text of docs/sprints/sprint_04/14_group1_summary.md.

No experiment is run here. The script
  1. verifies every output hash declared in each run_manifest.json against the file on disk (a mismatch stops it
     with exit code 2 before anything is written);
  2. reads every number it quotes from a committed result file (CSV/JSON) -- each value carries its source path;
  3. compares ~5 headline numbers per report with those files (cross_check.csv; a difference is reported, the
     original report is never edited);
  4. writes tables (long form, one source per cell), a markdown draft of report 14 and a run_manifest.json.

Run in the main runtime (~/.venv_dacn), from the repository root:
  python -m scripts.73_generate_group1_report
An existing output directory is never overwritten (use --out-dir <name>_v2).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BASE = ROOT / "data/processed/evaluation/sprint04"
INTERIM_BASE = ROOT / "data/interim/modeling/sprint04"
DEFAULT_OUT = "group1_summary_20261015_v2"
RULE_VERSION = "group1-summary-v1"

# key -> (run directory name, manifest kind)
RUNS = {
    "WP1": ("t2_baseline_20261014_v1", "wp1"),
    "WP2": ("t1_h5_20261015_v1", "wp2"),
    "WP2b": ("t1_h5_tier2_local_20261016_v1", "wp2b"),
    "WP3a": ("reliability_20261014_v1", "wp3a"),
    "WP3b": ("multiseed_20261015_v1", "wp3b"),
    "WP4": ("cpu_hypotheses_20261016_v1", "wp4"),
    "WP4v2": ("cpu_hypotheses_20261016_v2", "wp4v2"),
    "WP5": ("constraint_ablation_20261017_v1", "wp5"),
}
SYSTEMS5 = ["HEUR-JW", "CRF-INDEP", "PHOBERT-CRF", "PROPOSED-DYN", "PROPOSED-NO-CONSTRAINT"]
SEEDS = [42, 1337, 2025]


class HashMismatch(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def rel(path: Path) -> str:
    """Repository-relative path; an absolute path when the file lives outside the repository (e.g. --base-dir copies)."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


# ------------------------------------------------------------------ step 1: hashes
def expected_hashes(kind: str, run_dir: Path, manifest: dict) -> list[dict]:
    """Return [{path, sha256, optional}] declared by the run manifest. Layouts differ between work packages."""
    items: list[dict] = []

    def add(path: Path, sha: str, optional: bool = False):
        items.append({"path": path, "sha256": sha, "optional": optional})

    def add_map(mapping: dict, key_sha=None):
        for name, value in mapping.items():
            sha = value if isinstance(value, str) else value["sha256"]
            # prediction dumps are not committed; they are checked when on disk
            add(run_dir / name, sha, optional="predictions" in name)

    if kind in ("wp1", "wp3a"):
        add_map(manifest["output_sha256"])
    elif kind == "wp2":
        add_map(manifest["outputs"])
        add_map(manifest["tier2"]["outputs"])
        add(run_dir / "tier2/status.json", manifest["tier2"]["status_file_sha256"])
    elif kind == "wp2b":
        add_map(manifest["outputs"])
        add(run_dir / "frozen_hashes.json", manifest["frozen_hashes_sha256"])
    elif kind == "wp3b":
        # WP3b's manifest declares no output hashes (a finding, see report 14): check the frozen prediction hashes.
        frozen = json.loads((run_dir / "frozen_hashes.json").read_text(encoding="utf-8"))
        for key, value in frozen.items():
            folder, variant = key.split("/")
            path = INTERIM_BASE / run_dir.name / folder / f"test_{variant}" / "predictions.jsonl"
            add(path, value["predictions_sha256"], optional=True)
    elif kind == "wp4":
        add_map(manifest["outputs_sha256"])
        interim = INTERIM_BASE / run_dir.name
        for name, sha in manifest["interim_prediction_sha256"].items():
            add(interim / name, sha, optional=True)
    elif kind == "wp4v2":
        add_map(manifest["outputs_sha256"])
        add(run_dir / "rescore_drop_gt.py", manifest["script_sha256"])
    elif kind == "wp5":
        add_map(manifest["outputs"])
    elif kind == "flat":  # used by the unit tests
        add_map(manifest["output_sha256"])
    else:
        raise ValueError(f"unknown manifest kind {kind}")
    return items


def check_hashes(run_key: str, items: list[dict]) -> list[dict]:
    rows = []
    for item in items:
        path: Path = item["path"]
        if not path.exists():
            status = "MISSING_OPTIONAL" if item["optional"] else "MISSING_REQUIRED"
            actual = ""
        else:
            actual = sha256_file(path)
            status = "OK" if actual == item["sha256"] else "MISMATCH"
        try:
            shown = rel(path)
        except ValueError:
            shown = path.as_posix()
        rows.append({"run": run_key, "file": shown, "expected_sha256": item["sha256"], "actual_sha256": actual,
                     "status": status})
    bad = [r for r in rows if r["status"] in ("MISMATCH", "MISSING_REQUIRED")]
    if bad:
        detail = "; ".join(f"{r['run']}:{r['file']}:{r['status']}" for r in bad[:5])
        raise HashMismatch(f"{len(bad)} hash problem(s): {detail}")
    return rows


def verify_all(base: Path, runs: dict) -> tuple[list[dict], dict]:
    rows, manifests = [], {}
    for key, (name, kind) in runs.items():
        run_dir = base / name
        manifest_path = run_dir / "run_manifest.json"
        if not manifest_path.exists():
            raise HashMismatch(f"{key}: missing {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifests[key] = manifest
        rows.extend(check_hashes(key, expected_hashes(kind, run_dir, manifest)))
    return rows, manifests


def cross_run_links(base: Path, manifests: dict) -> list[dict]:
    """Hashes that one run stores about another run's files; a difference is recorded, not fatal."""
    def link(name, left, right):
        return {"link": name, "declared": left, "actual": right, "status": "OK" if left == right else "DIFFERENT"}

    wp1_dir = base / RUNS["WP2"][0]
    out = [
        link("WP2b.tier1_run_manifest_sha256 == sha256(WP2/run_manifest.json)",
             manifests["WP2b"]["tier1_run_manifest_sha256"], sha256_file(wp1_dir / "run_manifest.json")),
        link("WP2b.tier1_predictions_sha256 == sha256(WP2/predictions.jsonl)",
             manifests["WP2b"]["tier1_predictions_sha256"], sha256_file(wp1_dir / "predictions.jsonl")),
        link("WP4v2.source_v1_manifest_sha256 == sha256(WP4/run_manifest.json)",
             manifests["WP4v2"]["source_v1_manifest_sha256"], sha256_file(base / RUNS["WP4"][0] / "run_manifest.json")),
    ]
    frozen = json.loads((base / RUNS["WP3b"][0] / "frozen_hashes.json").read_text(encoding="utf-8"))
    wp5 = manifests["WP5"]["frozen_input_hashes"]
    for seed in SEEDS:
        for kind, key in (("dyn_on", "dyn"), ("dyn_off", "dyn_off"), ("pcrf", "pcrf")):
            model = "pcrf" if kind == "pcrf" else "dyn"
            out.append(link(f"WP5.test_seed{seed}.{kind} == WP3b.frozen[{model}_seed{seed}/{key}]",
                            wp5[f"test_seed{seed}"][kind]["sha256"], frozen[f"{model}_seed{seed}/{key}"]["predictions_sha256"]))
    return out


# ------------------------------------------------------------------ step 2: cells with sources
class Cells:
    """Registry of quoted numbers. Every value is read from a result file and keeps its source."""

    def __init__(self, base: Path):
        self.base = base
        self.rows: dict[str, dict] = {}
        self._csv: dict[Path, list[dict]] = {}
        self._json: dict[Path, object] = {}
        self.files: dict[str, str] = {}

    def _path(self, run: str, rel_path: str) -> Path:
        return self.base / RUNS[run][0] / rel_path

    def _register(self, cid: str, path: Path, selector: str, value):
        if cid in self.rows:
            raise KeyError(f"duplicate cell id {cid}")
        file_rel = rel(path)
        self.files[file_rel] = sha256_file(path)
        self.rows[cid] = {"cell": cid, "value": value, "file": file_rel, "selector": selector}

    def csv(self, cid: str, run: str, rel_path: str, where: dict, col: str):
        path = self._path(run, rel_path)
        rows = self._csv.setdefault(path, read_csv(path))
        match = [r for r in rows if all(r.get(k) == v for k, v in where.items())]
        if len(match) != 1:
            raise LookupError(f"{cid}: {len(match)} rows match {where} in {rel_path}")
        raw = match[0][col]
        if raw == "":
            raise LookupError(f"{cid}: empty {col} in {rel_path} {where}")
        try:
            value = float(raw)
        except ValueError:
            value = raw
        self._register(cid, path, ",".join(f"{k}={v}" for k, v in where.items()) + f" -> {col}", value)

    def csv3(self, prefix: str, run: str, rel_path: str, where: dict, cols: dict[str, str]):
        for tag, col in cols.items():
            self.csv(f"{prefix}.{tag}", run, rel_path, where, col)

    def json(self, cid: str, run: str, rel_path: str, keys: list[str]):
        path = self._path(run, rel_path)
        data = self._json.setdefault(path, json.loads(path.read_text(encoding="utf-8")))
        node = data
        for key in keys:
            node = node[key]
        self._register(cid, path, "/".join(keys), float(node) if isinstance(node, (int, float)) else node)

    def get(self, cid: str):
        return self.rows[cid]["value"]

    def source(self, cid: str) -> str:
        r = self.rows[cid]
        return f"{r['file']} [{r['selector']}]"


def fmt(value, spec: str) -> str:
    if spec == "s":
        return str(value)
    if spec == "i":
        return str(int(round(float(value))))
    sign_fix = lambda s: s.replace("-", "−")
    if spec.startswith("p"):
        return sign_fix(f"{float(value) * 100:.{int(spec[1:] or 1)}f}".replace(".", ",") + "%")
    if spec.startswith("+"):
        text = f"{float(value):+.{int(spec[1:])}f}"
        return sign_fix(text.replace(".", ","))
    return sign_fix(f"{float(value):.{int(spec)}f}".replace(".", ","))


TOKEN = re.compile(r"\{([A-Za-z0-9_.|\-]+)(?::([A-Za-z0-9+]+))?\}")


class Doc:
    """Template renderer: `{cell.id:3}` -> 3 decimals with decimal comma; records which cells each rendered text used."""

    def __init__(self, cells: Cells):
        self.cells = cells
        self.used: list[tuple[str, str]] = []  # (label, cell id)

    def render(self, template: str, label: str = "") -> tuple[str, list[str]]:
        ids: list[str] = []

        def sub(match):
            cid, spec = match.group(1), match.group(2) or "3"
            ids.append(cid)
            self.used.append((label, cid))
            return fmt(self.cells.get(cid), spec)

        return TOKEN.sub(sub, template), ids


# Report-value cross check: (report, location, text as printed, reported number, decimals, cell id)
def build_cells(base: Path) -> Cells:
    c = Cells(base)
    W3A, W3B, W1, W2, W2B, W4, W4V2, W5 = "WP3a", "WP3b", "WP1", "WP2", "WP2b", "WP4", "WP4v2", "WP5"

    # ---- WP3a: T0 CI, exact match, T1 CI, paired
    for s in SYSTEMS5:
        c.csv3(f"r.f1.{s}", W3A, "tables/test_t0_micro_ci.csv", {"system": s, "metric": "f1"},
               {"v": "estimate", "lo": "ci_low", "hi": "ci_high"})
        c.csv3(f"r.em.{s}", W3A, "tables/test_t0_exact_match_ci.csv", {"system": s},
               {"n": "n_exact", "v": "estimate", "lo": "ci_low", "hi": "ci_high"})
    for s in ("HEUR-JW", "PROPOSED-DYN"):
        for metric in ("accuracy", "macro_f1"):
            c.csv3(f"r.t1.{s}.{metric}", W3A, "tables/test_t1_ci.csv", {"system": s, "metric": metric},
                   {"v": "estimate", "lo": "ci_low", "hi": "ci_high"})
    pairs = {"pcrf_dyn": ("T0_micro_F1", "PHOBERT-CRF", "PROPOSED-DYN"),
             "dyn_off": ("T0_micro_F1", "PROPOSED-DYN", "PROPOSED-NO-CONSTRAINT"),
             "pcrf_crf": ("T0_micro_F1", "PHOBERT-CRF", "CRF-INDEP"),
             "pcrf_heur": ("T0_micro_F1", "PHOBERT-CRF", "HEUR-JW"),
             "t1_heur_dyn": ("T1_accuracy", "HEUR-JW", "PROPOSED-DYN")}
    for tag, (metric, a, b) in pairs.items():
        c.csv3(f"r.pair.{tag}", W3A, "tables/test_paired_comparisons.csv",
               {"metric": metric, "system_a": a, "system_b": b},
               {"d": "delta", "lo": "ci_low", "hi": "ci_high", "b": "mcnemar_b_a_right_b_wrong",
                "c": "mcnemar_c_a_wrong_b_right"})

    # ---- WP3b: three local seeds
    for model in ("pcrf", "dyn"):
        for metric in ("t0_f1", "exact_match"):
            c.json(f"m.{model}.{metric}.mean", W3B, "metrics.json", [model, metric, "mean"])
            c.json(f"m.{model}.{metric}.std", W3B, "metrics.json", [model, metric, "std"])
    for metric in ("t1_accuracy", "t1_macro_f1", "t1_lai_f1"):
        c.json(f"m.dyn.{metric}.mean", W3B, "metrics.json", ["dyn", metric, "mean"])
        c.json(f"m.dyn.{metric}.std", W3B, "metrics.json", ["dyn", metric, "std"])
    c.json("m.delta.mean", W3B, "metrics.json", ["delta_mean_std", "pcrf_minus_dyn_t0_f1", "mean"])
    c.json("m.delta.std", W3B, "metrics.json", ["delta_mean_std", "pcrf_minus_dyn_t0_f1", "std"])
    c.json("m.kaggle.pcrf.f1", W3B, "metrics.json", ["sprint3_gpu_t4_seed42_not_in_mean", "PHOBERT-CRF", "t0_f1"])
    c.json("m.kaggle.dyn.f1", W3B, "metrics.json", ["sprint3_gpu_t4_seed42_not_in_mean", "PROPOSED-DYN", "t0_f1"])
    c.json("m.kaggle.dyn.t1acc", W3B, "metrics.json", ["sprint3_gpu_t4_seed42_not_in_mean", "PROPOSED-DYN", "t1_accuracy"])
    c.json("m.kaggle.dyn.t1f1", W3B, "metrics.json", ["sprint3_gpu_t4_seed42_not_in_mean", "PROPOSED-DYN", "t1_macro_f1"])
    for seed in SEEDS:
        for model in ("pcrf", "dyn"):
            c.csv(f"m.{model}.{seed}.f1", W3B, "tables/per_seed.csv", {"run": f"{model}_seed{seed}", "variant": model}, "t0_f1")
        c.csv(f"m.dyn.{seed}.t1acc", W3B, "tables/per_seed.csv", {"run": f"dyn_seed{seed}", "variant": "dyn"}, "t1_accuracy")
        c.csv(f"m.dyn.{seed}.argmax", W3B, "tables/per_seed.csv", {"run": f"dyn_seed{seed}", "variant": "dyn"}, "argmax_t1_accuracy")

    # ---- WP2 (tier 1) and WP2b (tier 2 local): T1
    for s in ("HEUR-JW", "PROPOSED-DYN", "T1-PIPE-CRF", "T1-PIPE-PCRF", "T1-PIPE-DYN", "T1-FEAT"):
        c.csv3(f"t1.{s}.test", W2, "tables/h5_main.csv", {"system": s, "column": "s3_test_eligible"},
               {"acc": "accuracy", "lo": "accuracy_ci_low", "hi": "accuracy_ci_high", "mf1": "macro_f1",
                "lai_r": "lai_recall", "lai_f1": "lai_f1"})
    for s in ("HEUR-JW", "T1-FEAT"):
        c.csv(f"t1.{s}.synth.acc", W2, "tables/h5_main.csv", {"system": s, "column": "t1_synth_eval"}, "accuracy")
        c.csv(f"t1.{s}.d06.rec", W2, "tables/h5_main.csv", {"system": s, "column": "t1_data06_heldout"}, "lai_recall")
    c.csv3("t1.dyn.d_heur", W2, "tables/h5_main.csv", {"system": "PROPOSED-DYN", "column": "s3_test_eligible"},
           {"d": "delta_acc_vs_heur", "lo": "delta_acc_ci_low", "hi": "delta_acc_ci_high", "p": "mcnemar_p"})
    for s in ("PROPOSED-DYN", "T1-PIPE-PCRF", "T1-PIPE-DYN", "T1-HEAD-PROBE", "DYN-ARGMAX-DIAGNOSTIC"):
        for col, tag in (("s3_test_eligible", "test"), ("t1_synth_eval", "synth"), ("t1_data06_heldout", "d06")):
            where = {"system": s, "column": col}
            c.csv3(f"t2l.{s}.{tag}", W2B, "tables/h5_tier2_local_mean_std.csv", where,
                   {"acc": "accuracy_mean", "acc_sd": "accuracy_std", "lai_r": "lai_recall_mean"})
            if tag != "d06":
                c.csv3(f"t2l.{s}.{tag}.mf1", W2B, "tables/h5_tier2_local_mean_std.csv", where,
                       {"m": "macro_f1_mean", "sd": "macro_f1_std"})

    # ---- WP1: T2
    main = "tables/t2_main_oracle_n2.csv"
    for s, d in (("T2-LOOKUP-STRICT", "cu_to_moi"), ("T2-LOOKUP-DEFAULT-MAIN", "cu_to_moi"),
                 ("T2-LOOKUP-DEFAULT-MAIN", "moi_to_cu"), ("T2-LOOKUP-DEFAULT-FIRST", "cu_to_moi"),
                 ("T2-LOOKUP-DEFAULT-FIRST", "moi_to_cu"), ("T2-VNADMIN", "cu_to_moi"),
                 ("T2-SINGLE-VERSION", "cu_to_moi"), ("T2-SINGLE-VERSION", "moi_to_cu"),
                 ("T2-LOOKUP-STRICT", "moi_to_cu")):
        where = {"system": s, "direction": d, "slice_type": "ALL", "slice": "ALL"}
        c.csv3(f"t2.{s}.{d}", W1, main, where, {"acc": "accuracy", "k": "n_clusters", "sil": "silent_errors",
                                                "silr": "silent_error_rate", "cov": "coverage"})
    for s, d in (("T2-LOOKUP-STRICT", "cu_to_moi"), ("T2-LOOKUP-DEFAULT-MAIN", "cu_to_moi"),
                 ("T2-LOOKUP-DEFAULT-MAIN", "moi_to_cu"), ("T2-LOOKUP-DEFAULT-FIRST", "cu_to_moi"),
                 ("T2-LOOKUP-DEFAULT-FIRST", "moi_to_cu"), ("T2-VNADMIN", "cu_to_moi"),
                 ("T2-SINGLE-VERSION", "cu_to_moi"), ("T2-SINGLE-VERSION", "moi_to_cu")):
        where = {"system": s, "direction": d, "slice_type": "ALL", "slice": "ALL"}
        c.csv3(f"t2.{s}.{d}.ci", W1, main, where, {"lo": "accuracy_ci_low", "hi": "accuracy_ci_high"})
    for form, tag in (("Tách — nhập chủ yếu", "main"), ("Tách — một phần", "part")):
        for d in ("cu_to_moi", "moi_to_cu"):
            c.csv(f"t2.form.{tag}.{d}", W1, main, {"system": "T2-LOOKUP-DEFAULT-MAIN", "direction": d,
                                                    "slice_type": "HinhThucSapNhap", "slice": form}, "accuracy")
        c.csv(f"t2.form.{tag}.n", W1, main, {"system": "T2-LOOKUP-DEFAULT-MAIN", "direction": "cu_to_moi",
                                               "slice_type": "HinhThucSapNhap", "slice": form}, "n")
    for lvl in ("N0", "N1", "N2"):
        c.csv(f"t2.norm.{lvl}", W1, "tables/t2_sensitivity_normalisation.csv",
              {"system": "T2-LOOKUP-DEFAULT-MAIN", "direction": "cu_to_moi", "level": lvl}, "accuracy")
    c.csv3("t2.pipe.heur", W1, "tables/t2_pipeline.csv",
           {"system": "T2-LOOKUP-DEFAULT-MAIN", "direction": "cu_to_moi", "condition": "pipeline:HEUR-JW",
            "slice_type": "ALL", "slice": "ALL"}, {"acc": "accuracy", "cov": "coverage"})
    c.csv3("t2.pipe.crf", W1, "tables/t2_pipeline.csv",
           {"system": "T2-LOOKUP-DEFAULT-MAIN", "direction": "cu_to_moi", "condition": "pipeline:CRF-INDEP",
            "slice_type": "ALL", "slice": "ALL"}, {"acc": "accuracy", "cov": "coverage"})
    for s in ("T2-LOOKUP-DEFAULT-MAIN",):
        c.csv3(f"t2.e3.{s}", W1, "tables/t2_e3_asymmetry.csv",
               {"condition": "oracle", "level": "N2", "slice": "ALL=ALL", "system": s},
               {"d": "delta", "lo": "delta_ci_low_new_ward", "hi": "delta_ci_high_new_ward", "p": "mcnemar_p",
                "b": "fwd_right_back_wrong", "c": "fwd_wrong_back_right", "k": "n_clusters_new_ward"})
    for g in ("share_old_keys_deterministic", "share_new_keys_deterministic", "atomic_edges", "mean_fan_in",
              "ceiling_deterministic_pick_old_to_new", "ceiling_deterministic_pick_new_to_old"):
        c.json(f"t2.graph.{g}", W1, "graph_analysis.json", [g])
    c.csv("t2.ceiling.moi_to_cu", W1, "tables/t2_unit_constant_ceiling.csv",
          {"direction": "moi_to_cu", "slice_type": "ALL", "slice": "ALL"}, "unit_constant_ceiling")
    c.csv("t2.ceiling.cu_to_moi", W1, "tables/t2_unit_constant_ceiling.csv",
          {"direction": "cu_to_moi", "slice_type": "ALL", "slice": "ALL"}, "unit_constant_ceiling")
    sit = "tables/t2_h5_situation_c.csv"
    for col in ("MATCH_WRONG_SILENT", "MATCH_CORRECT", "NO_MATCH", "n_evaluated"):
        c.csv(f"t2.c.old.{col}", W1, sit, {"assumption": "assume_old", "kieulai": "ALL",
                                            "system": "T2-LOOKUP-DEFAULT-MAIN"}, col)
    d7 = "tables/t2_h5_situation_d_data07.csv"
    for d in ("cu_to_moi", "moi_to_cu"):
        c.csv3(f"t2.d.{d}", W1, d7, {"system": "T2-SINGLE-VERSION", "direction": d, "group": "D_GROUP_ALL"},
               {"n": "n", "sil": "silent_errors", "rate": "silent_error_rate_in_group", "share": "share_of_600"})
    c.csv("t2.d.census", W1, "tables/t2_h5_situation_d_census.csv", {"metric": "share_d"}, "value")
    for fb, lf in (("MAIN", "L1"), ("MAIN", "L2")):
        c.csv3(f"t2.e2.{lf}", W1, "tables/t2_e2_street.csv", {"fallback": fb, "leak_filter": lf, "slice": "ALL"},
               {"street": "acc_street", "dflt": "acc_default", "d": "delta", "lo": "delta_ci_low",
                "hi": "delta_ci_high", "n": "n", "k": "n_clusters"})
    c.csv("t2.e2.L2.decisive", W1, "tables/t2_e2_street_index.csv", {"leak_filter": "L2"},
          "evidence_evidence_rate_decisive")
    c.csv("t2.e2.L1.decisive", W1, "tables/t2_e2_street_index.csv", {"leak_filter": "L1"},
          "evidence_evidence_rate_decisive")

    # ---- WP4: H3, E1, H2, H4
    h3 = "h3_field_order.csv"
    for sysname, tag in (("CRF-INDEP", "crf"), ("HEUR-JW", "heur")):
        for cond in ("original_text", "recomposed_original_order", "reverse", "shuffle_seed42"):
            c.csv(f"h3.{tag}.{cond}.f1", W4, h3, {"system": sysname, "condition": cond, "subset": "all"}, "f1")
            c.csv3(f"h3.{tag}.{cond}.d", W4, h3, {"system": sysname, "condition": cond, "subset": "all"},
                   {"v": "delta_f1", "lo": "delta_ci_low", "hi": "delta_ci_high"})
    for cond in ("commas_drop|case_keep", "commas_keep|case_lower"):
        for sysname, tag in (("CRF-INDEP", "crf"), ("HEUR-JW", "heur")):
            c.csv3(f"e1a.{tag}.{cond}", W4, "e1_preprocessing.csv",
                   {"experiment": "E1a_test_time_only", "system": sysname, "condition": cond},
                   {"f1": "f1", "d": "delta_f1", "lo": "delta_ci_low", "hi": "delta_ci_high"})
        c.csv3(f"e1b.crf.{cond}", W4, "e1_preprocessing.csv",
               {"experiment": "E1b_train_and_test", "system": "CRF-INDEP", "condition": cond},
               {"f1": "f1", "d": "delta_f1", "lo": "delta_ci_low", "hi": "delta_ci_high"})
    c.csv("h2.base.gt", W4, "h2_heldout_missing.csv", {"truth": "gt", "subset": "all", "model": "BASE"}, "f1")
    c.csv("h2.base.surface", W4, "h2_heldout_missing.csv", {"truth": "surface", "subset": "all", "model": "BASE"}, "f1")
    c.csv("h2.rows.heldout", W4, "h2_heldout_missing.csv", {"truth": "gt", "subset": "all", "model": "BASE"}, "n_rows")
    for cmp_, tag in (("AUG-MISSING - BASE", "miss_base"), ("AUG-FULL - BASE", "full_base"),
                      ("AUG-MISSING - AUG-FULL", "miss_full")):
        c.csv3(f"h2.p.{tag}", W4, "h2_paired_deltas.csv",
               {"truth": "gt", "subset": "all", "N": "240", "subset_seed": "20261016", "comparison": cmp_},
               {"d": "delta_f1", "lo": "ci_low", "hi": "ci_high"})
    for truth in ("gt", "surface"):
        c.csv3(f"h2.drop.{truth}", W4V2, "h2_drop_vs_full_gt.csv", {"model": "BASE", "truth": truth},
               {"held": "heldout_f1", "full": "full_f1", "d": "delta", "rel": "relative_drop",
                "nh": "n_heldout", "nf": "n_full"})
    c.csv3("h2.td.test20.miss", W4, "h2_test_dev.csv", {"split": "test", "subset": "04_missing_20", "model": "AUG-MISSING",
                                                          "N": "240", "subset_seed": "20261016"},
           {"f1": "f1", "d": "delta_vs_base"})
    c.csv("h2.td.test20.base", W4, "h2_test_dev.csv", {"split": "test", "subset": "04_missing_20", "model": "BASE"}, "f1")
    for sysname in SYSTEMS5:
        c.csv3(f"h4.{sysname}", W4, "h4_admin_vs_road.csv", {"system": sysname},
               {"admin": "admin_f1", "road": "road_f1", "d": "delta", "lo": "ci_low", "hi": "ci_high"})

    # ---- WP5: constraint ablation
    c.csv("w5.hr.test.n", W5, "tables/headroom.csv", {"dataset": "test_kaggle", "emission_model": "PROPOSED-DYN checkpoint"}, "n_headroom")
    c.csv("w5.hr.test.gold", W5, "tables/headroom.csv", {"dataset": "test_kaggle", "emission_model": "PROPOSED-DYN checkpoint"}, "n_gold_moi_without_quan_huyen")
    c.csv("w5.hr.5f.n", W5, "tables/headroom.csv", {"dataset": "fivefield_kaggle", "emission_model": "PROPOSED-DYN checkpoint"}, "n_headroom")
    c.csv("w5.hr.5f.gold", W5, "tables/headroom.csv", {"dataset": "fivefield_kaggle", "emission_model": "PROPOSED-DYN checkpoint"}, "n_gold_moi")
    c.csv("w5.hr.5f.dynmoi", W5, "tables/headroom.csv", {"dataset": "fivefield_kaggle", "emission_model": "PROPOSED-DYN checkpoint"}, "headroom_dyn_moi")
    for ds in ("test_kaggle", "test_seed42", "test_seed1337", "test_seed2025", "fivefield_kaggle", "dev_kaggle"):
        c.csv3(f"w5.onoff.{ds}", W5, "tables/onoff_dyn_source.csv", {"dataset": ds, "t1_source": "DYN"},
               {"ban": "n_ban_rows", "chg": "n_changed_rows", "d": "delta", "lo": "ci_low", "hi": "ci_high"})
    c.csv("w5.hr.s1337", W5, "tables/headroom.csv", {"dataset": "test_seed1337", "emission_model": "PROPOSED-DYN checkpoint"}, "n_headroom")
    for ds in ("test_kaggle", "test_seed1337", "fivefield_kaggle"):
        c.csv3(f"w5.oracle.{ds}", W5, "tables/oracle_upper_bound.csv",
               {"dataset": ds, "emission_model": "PROPOSED-DYN checkpoint"},
               {"d": "delta", "lo": "ci_low", "hi": "ci_high", "fix": "correct_fix", "harm": "harm", "neutral": "neutral"})
    for seed in SEEDS:
        c.csv(f"w5.seed.{seed}.pcrf", W5, "tables/seed_summary.csv", {"seed": str(seed)}, "PHOBERT-CRF")
        c.csv(f"w5.seed.{seed}.dyn", W5, "tables/seed_summary.csv", {"seed": str(seed)}, "PROPOSED-DYN")
    for cell in ("PHOBERT-CRF", "PROPOSED-NO-CONSTRAINT", "PROPOSED-DYN", "PHOBERT-CRF emissions + external T1"):
        c.csv(f"w5.x22.{cell}", W5, "tables/model_comparison_2x2.csv", {"dataset": "test_kaggle", "cell": cell}, "f1")
    return c


# ------------------------------------------------------------------ step 3: headline cross-check
# (report, where in report, quoted text, reported number, decimals, cell id). Decimals = digits printed in the report.
CHECKS = [
    ("09", "§3.1 DEFAULT-MAIN cũ→mới accuracy", "0,965", 0.965, 3, "t2.T2-LOOKUP-DEFAULT-MAIN.cu_to_moi.acc"),
    ("09", "§3.1 DEFAULT-MAIN mới→cũ accuracy", "0,077", 0.077, 3, "t2.T2-LOOKUP-DEFAULT-MAIN.moi_to_cu.acc"),
    ("09", "§3.1 DEFAULT-MAIN mới→cũ lỗi im lặng", "554", 554, 0, "t2.T2-LOOKUP-DEFAULT-MAIN.moi_to_cu.sil"),
    ("09", "§3.1 STRICT cũ→mới accuracy", "0,407", 0.407, 3, "t2.T2-LOOKUP-STRICT.cu_to_moi.acc"),
    ("09", "§3.4 N0 accuracy", "0,008", 0.008, 3, "t2.norm.N0"),
    ("09", "§3.4 N1 accuracy", "0,860", 0.860, 3, "t2.norm.N1"),
    ("09", "§8 khóa cũ tất định", "95,3%", 0.953, 3, "t2.graph.share_old_keys_deterministic"),
    ("09", "§8 khóa mới tất định", "4,1%", 0.041, 3, "t2.graph.share_new_keys_deterministic"),
    ("09", "§9 trần luật hằng mới→cũ", "0,742", 0.742, 3, "t2.ceiling.moi_to_cu"),
    ("09", "§6 E2 L2 STREET accuracy", "0,993", 0.993, 3, "t2.e2.L2.street"),
    ("10", "§6.1 HEUR-JW test accuracy", "0,9219", 0.9219, 4, "t1.HEUR-JW.test.acc"),
    ("10", "§6.1 DYN gốc test accuracy", "0,7188", 0.7188, 4, "t1.PROPOSED-DYN.test.acc"),
    ("10", "§6.1 T1-PIPE-PCRF test accuracy", "0,9688", 0.9688, 4, "t1.T1-PIPE-PCRF.test.acc"),
    ("10", "§6.2 T1-FEAT synth_eval accuracy", "0,8925", 0.8925, 4, "t1.T1-FEAT.synth.acc"),
    ("10", "§6.3 HEUR-JW Lai recall data06", "0,2948", 0.2948, 4, "t1.HEUR-JW.d06.rec"),
    ("10", "§11.2 DYN thr. test accuracy mean", "0,740", 0.740, 3, "t2l.PROPOSED-DYN.test.acc"),
    ("10", "§11.2 DYN thr. test accuracy std", "0,092", 0.092, 3, "t2l.PROPOSED-DYN.test.acc_sd"),
    ("10", "§11.2 probe test accuracy mean", "0,849", 0.849, 3, "t2l.T1-HEAD-PROBE.test.acc"),
    ("10", "§11.2 probe synth_eval accuracy mean", "0,752", 0.752, 3, "t2l.T1-HEAD-PROBE.synth.acc"),
    ("11a", "§2 PHOBERT-CRF F1", "0,9843", 0.9843, 4, "r.f1.PHOBERT-CRF.v"),
    ("11a", "§2 PROPOSED-DYN F1", "0,9821", 0.9821, 4, "r.f1.PROPOSED-DYN.v"),
    ("11a", "§2 CRF-INDEP F1", "0,9076", 0.9076, 4, "r.f1.CRF-INDEP.v"),
    ("11a", "§3 PCRF−DYN ΔF1", "+0,0022", 0.0022, 4, "r.pair.pcrf_dyn.d"),
    ("11a", "§3 PCRF−CRF ΔF1", "+0,0767", 0.0767, 4, "r.pair.pcrf_crf.d"),
    ("11a", "§3 T1 HEUR−DYN Δ accuracy", "+0,2031", 0.2031, 4, "r.pair.t1_heur_dyn.d"),
    ("11b", "b2 PHOBERT-CRF F1 mean", "0,9787", 0.9787, 4, "m.pcrf.t0_f1.mean"),
    ("11b", "b2 PHOBERT-CRF F1 std", "0,0030", 0.0030, 4, "m.pcrf.t0_f1.std"),
    ("11b", "b2 PROPOSED-DYN F1 mean", "0,9783", 0.9783, 4, "m.dyn.t0_f1.mean"),
    ("11b", "b2 PROPOSED-DYN F1 std", "0,0111", 0.0111, 4, "m.dyn.t0_f1.std"),
    ("11b", "b2 DYN T1 accuracy mean", "0,7396", 0.7396, 4, "m.dyn.t1_accuracy.mean"),
    ("11b", "b2 DYN T1 accuracy std", "0,0916", 0.0916, 4, "m.dyn.t1_accuracy.std"),
    ("11b", "b3 PCRF−DYN mean", "+0,0004", 0.0004, 4, "m.delta.mean"),
    ("12", "§1 CRF đảo ngược F1", "0,2171", 0.2171, 4, "h3.crf.reverse.f1"),
    ("12", "§1 CRF đảo ngược Δ", "−0,716", -0.716, 3, "h3.crf.reverse.d.v"),
    ("12", "§2 E1a CRF bỏ phẩy Δ", "−0,317", -0.317, 3, "e1a.crf.commas_drop|case_keep.d"),
    ("12", "§2 E1b CRF bỏ phẩy Δ", "−0,058", -0.058, 3, "e1b.crf.commas_drop|case_keep.d"),
    ("12", "§3 H2 AUG-MISSING−AUG-FULL Δ", "−0,001", -0.001, 3, "h2.p.miss_full.d"),
    ("12", "§3 H2 BASE gt giảm tương đối", "32,4%", 0.324, 3, "h2.drop.gt.rel"),
    ("12", "§3 H2 BASE surface giảm tương đối", "6,8%", 0.068, 3, "h2.drop.surface.rel"),
    ("12", "§4 H4 HEUR-JW Δ", "−0,038", -0.038, 3, "h4.HEUR-JW.d"),
    ("13", "§2 dư địa test (gold-new)", "0", 0, 0, "w5.hr.test.n"),
    ("13", "§2 dư địa 5 trường", "168", 168, 0, "w5.hr.5f.n"),
    ("13", "§5 test Kaggle ban Δ F1", "−0,0022", -0.0022, 4, "w5.onoff.test_kaggle.d"),
    ("13", "§7b ORACLE 5 trường Δ F1", "+0,0019", 0.0019, 4, "w5.oracle.fivefield_kaggle.d"),
    ("13", "§7b ORACLE seed 1337 Δ F1", "+0,0022", 0.0022, 4, "w5.oracle.test_seed1337.d"),
    ("13", "§8 2×2 PHOBERT-CRF F1", "0,9843", 0.9843, 4, "w5.x22.PHOBERT-CRF"),
    ("13", "§8 2×2 PROPOSED-DYN F1", "0,9821", 0.9821, 4, "w5.x22.PROPOSED-DYN"),
]


def interim_crf_checks(base: Path) -> list[dict]:
    """CRF transition bounds quoted from review WP5 / WP6 (interim files, not committed); re-measured when on disk."""
    folder = INTERIM_BASE / RUNS["WP5"][0] / "crf_params"
    claims = [("kaggle_dyn", "min", -0.068), ("kaggle_dyn", "max", 0.045), ("kaggle_pcrf", "min", -0.077),
              ("kaggle_pcrf", "max", 0.050), ("seed1337_dyn", "min", -0.092), ("seed1337_dyn", "max", 0.055),
              ("all_8_checkpoints", "max_abs", 0.092)]
    names = ["kaggle_dyn", "kaggle_pcrf"] + [f"seed{sd}_{m}" for sd in SEEDS for m in ("dyn", "pcrf")]
    measured = {}
    if base == BASE and all((folder / f"{n}.json").exists() for n in names):
        for n in names:
            data = json.loads((folder / f"{n}.json").read_text(encoding="utf-8"))
            values = [v for line in data["transitions"] for v in line if v is not None and abs(v) < 1e9]
            measured[n] = (min(values), max(values))
    rows = []
    for name, tag, reported in claims:
        row = {"report": "13 §2 / review WP6 Q1", "location": f"transitions CRF {name} {tag}",
               "reported_text": f"{reported:+.3f}".replace(".", ","), "reported_value": reported, "decimals": 3,
               "source": f"{rel(folder)}/{name}.json [transitions {tag}] (interim, không commit)"}
        if not measured:
            rows.append({**row, "file_value": "", "status": "NOT_ON_DISK"})
            continue
        if name == "all_8_checkpoints":
            value = max(max(abs(lo), abs(hi)) for lo, hi in measured.values())
        else:
            value = measured[name][0 if tag == "min" else 1]
        rows.append({**row, "file_value": value, "status": "MATCH" if abs(value - reported) <= 0.0005 + 1e-9 else "DIFFERENT"})
    return rows


def run_checks(cells: Cells) -> list[dict]:
    rows = []
    for report, where, text, reported, nd, cid in CHECKS:
        value = cells.get(cid)
        tol = 0.5 * 10 ** (-nd) + 1e-9
        ok = abs(float(value) - reported) <= tol
        rows.append({"report": report, "location": where, "reported_text": text, "reported_value": reported,
                     "file_value": value, "decimals": nd, "status": "MATCH" if ok else "DIFFERENT",
                     "source": cells.source(cid)})
    return rows


# ------------------------------------------------------------------ step 4: tables and report text
def hypothesis_rows(d: Doc) -> list[dict]:
    """Status is taken from the reports after review (original label kept); evidence numbers come from files."""
    R = d.render
    H = []

    def add(code, group, status, original, template, n, refs):
        text, ids = R(template, code)
        n_text, n_ids = R(n, code + "/n")
        H.append({"Ma": code, "PhanCong": group, "TrangThai": status, "NhanGoc": original, "BangChung": text,
                  "CoMau": n_text, "DuongDan": refs, "cells": ids + n_ids})

    add("H1", "ĐATN", "NOT_TESTABLE", "NOT_TESTABLE (13 §9.1)",
        "Không có type/gazetteer adapter nào được hiện thực; thứ đã kiểm là mask T1 + giải mã ràng buộc, dư địa "
        "{w5.hr.test.n:i}/{w5.hr.test.gold:i} mẫu gold-new trên test, ORACLE ΔF1 {w5.oracle.test_kaggle.d:4}. "
        "Không ủng hộ cũng không bác bỏ H1.",
        "test 100 mẫu (25 gold-new); 5 trường 4.800 dòng", "13_constraint_ablation_and_h1.md §9")
    add("H2", "ĐACN", "PARTLY_SUPPORTED", "phần tụt: ủng hộ; phần phục hồi đặc thù: không ủng hộ (12 §3)",
        "Tụt: BASE F1 `gt` {h2.drop.gt.held:3} so với {h2.drop.gt.full:3} khi đủ trường (giảm {h2.drop.gt.rel:p1}; "
        "`surface`: {h2.drop.surface.rel:p1}). Phục hồi: AUG-MISSING − AUG-FULL = {h2.p.miss_full.d:3} "
        "[{h2.p.miss_full.lo:3}; {h2.p.miss_full.hi:3}] (N = 240), thêm dữ liệu nói chung giúp "
        "{h2.p.miss_base.d:+3} so với BASE: không đặc thù cho địa chỉ thiếu trường.",
        "held-out {h2.rows.heldout:i} dòng, 300 dòng đầy đủ; 3 seed lấy mẫu; test 04_missing 20 mẫu",
        "12_cpu_hypothesis_results.md §3")
    add("H3", "ĐACN", "SUPPORTED", "ủng hộ (12 §1)",
        "CRF-INDEP F1 {h3.crf.recomposed_original_order.f1:3} (thứ tự gốc dựng lại) → {h3.crf.reverse.f1:3} khi đảo "
        "(Δ {h3.crf.reverse.d.v:3} [{h3.crf.reverse.d.lo:3}; {h3.crf.reverse.d.hi:3}]); HEUR-JW Δ {h3.heur.reverse.d.v:3}. "
        "Chỉ kiểm trên CRF-INDEP và HEUR-JW; Tầng 2 neural NOT_RUN (12 §5). Chuỗi dựng lại không còn nguyên văn.",
        "test 100 mẫu / 446 span", "12_cpu_hypothesis_results.md §1")
    add("H4", "ĐATN", "INCONCLUSIVE", "không kết luận được ở mức tổng quát (12 §4)",
        "ΔF1 hành chính − đường sá: HEUR-JW {h4.HEUR-JW.d:3} [{h4.HEUR-JW.lo:3}; {h4.HEUR-JW.hi:3}], PHOBERT-CRF "
        "{h4.PHOBERT-CRF.d:3} [{h4.PHOBERT-CRF.lo:3}; {h4.PHOBERT-CRF.hi:3}], PROPOSED-DYN {h4.PROPOSED-DYN.d:3}; "
        "2/5 hệ có CI loại 0; nhóm mốc support 0 (`NOT_EVALUABLE_NO_GOLD_SUPPORT`).",
        "test 100 mẫu (244 span hành chính, 200 đường sá, 0 mốc)", "12_cpu_hypothesis_results.md §4")
    add("H5", "ĐACN", "NOT_SUPPORTED", "mô hình đề xuất: NEGATIVE_RESULT; \"Lai khó nhất\": không kết luận được (10 §8, §11.4)",
        "Test Sprint 3: T1 PROPOSED-DYN {t1.PROPOSED-DYN.test.acc:3} so với HEUR-JW {t1.HEUR-JW.test.acc:3} "
        "(Δ {t1.dyn.d_heur.d:3} [{t1.dyn.d_heur.lo:3}; {t1.dyn.d_heur.hi:3}]); ba seed cục bộ: accuracy "
        "{t2l.PROPOSED-DYN.test.acc:3} ± {t2l.PROPOSED-DYN.test.acc_sd:3}, `Lai` recall data06 "
        "{t2l.PROPOSED-DYN.d06.lai_r:3}. T2: tra bảng không thất bại hoàn toàn trên chuỗi lai (lỗi im lặng "
        "{t2.c.old.MATCH_WRONG_SILENT:i}/{t2.c.old.n_evaluated:i}); tình huống D, mới→cũ: "
        "{t2.d.moi_to_cu.sil:i} lỗi im lặng ({t2.d.moi_to_cu.rate:p1} trong nhóm D).",
        "test 64 eligible (`Lai` 5); synth_eval 2.195; data06 580; Data 06 599 cho T2",
        "10_t1_h5_results.md §6, §11; 09_t2_baseline_results.md §7")
    add("E1", "ĐACN", "PARTLY_SUPPORTED",
        "ba ý: ủng hộ / ủng hộ một phần / không ủng hộ-không kết luận được; báo cáo không có phán quyết chung (12 §2)",
        "Bỏ phẩy lúc test: CRF Δ {e1a.crf.commas_drop|case_keep.d:3}, HEUR-JW Δ {e1a.heur.commas_drop|case_keep.d:3}; "
        "huấn luyện cùng điều kiện còn Δ {e1b.crf.commas_drop|case_keep.d:3}; hạ chữ CRF Δ "
        "{e1a.crf.commas_keep|case_lower.d:3} (chế độ a), {e1b.crf.commas_keep|case_lower.d:3} (chế độ b). "
        "Tầng 2 (neural) NOT_RUN.",
        "test 100 mẫu", "12_cpu_hypothesis_results.md §2")
    add("E2", "ĐATN", "INCONCLUSIVE", "INCONCLUSIVE (09 §6)",
        "T2-STREET L2 {t2.e2.L2.street:3} so với mặc định {t2.e2.L2.dflt:3} (Δ {t2.e2.L2.d:3} "
        "[{t2.e2.L2.lo:3}; {t2.e2.L2.hi:3}], {t2.e2.L2.k:i} cụm), nhưng mỗi đơn vị cũ của Data 07 chỉ có một đích "
        "(trần luật hằng-theo-đơn-vị {t2.ceiling.cu_to_moi:3}), nên không tách được tên đường khỏi việc nhớ đích.",
        "Data 07: 600 cặp, 49 cụm đơn vị cũ", "09_t2_baseline_results.md §6")
    add("E3", "ĐACN", "SUPPORTED", "được ủng hộ mạnh (09 §9)",
        "DEFAULT-MAIN cũ→mới {t2.T2-LOOKUP-DEFAULT-MAIN.cu_to_moi.acc:3} so với mới→cũ "
        "{t2.T2-LOOKUP-DEFAULT-MAIN.moi_to_cu.acc:3} (Δ {t2.e3.T2-LOOKUP-DEFAULT-MAIN.d:3} "
        "[{t2.e3.T2-LOOKUP-DEFAULT-MAIN.lo:3}; {t2.e3.T2-LOOKUP-DEFAULT-MAIN.hi:3}], {t2.e3.T2-LOOKUP-DEFAULT-MAIN.k:i} "
        "cụm); khóa giải tất định {t2.graph.share_old_keys_deterministic:p1} (cũ) so với "
        "{t2.graph.share_new_keys_deterministic:p1} (mới). Nguyên nhân cấu trúc, chỉ có B và M.",
        "Data 07: 600 cặp (B 244, M 356); đồ thị 10.597 cạnh", "09_t2_baseline_results.md §5, §8, §9")
    H.append({"Ma": "E4", "PhanCong": "mục 6 không phân công", "TrangThai": "NOT_RUN",
              "NhanGoc": "VQA đang HOLD (docs/data_quality.md)",
              "BangChung": "Không chạy: Viet-Receipt-VQA đang HOLD, không có ground truth đầy đủ cho 130 chuỗi hóa đơn.",
              "CoMau": "—", "DuongDan": "docs/data_quality.md", "cells": []})
    return H


def t0_t1_rows(d: Doc) -> dict[str, list[dict]]:
    """Long-form cells for the unified T0 / T1 / T2 tables. One row per displayed cell, with its sources."""
    R = d.render
    tables: dict[str, list[dict]] = {"T0": [], "T1": [], "T2": []}

    def put(table, group, row, col, template):
        text, ids = R(template, f"{table}/{group}/{row}/{col}")
        tables[table].append({"Bang": table, "Nhom": group, "Hang": row, "Cot": col, "HienThi": text,
                              "Nguon": " ; ".join(d.cells.source(i) for i in ids), "CellIds": ",".join(ids)})

    g = "Sprint 3 (Kaggle T4, seed 42) với CI bootstrap theo mẫu — WP3a"
    for s in SYSTEMS5:
        put("T0", g, s, "F1 [CI 95%]", f"{{r.f1.{s}.v:4}} [{{r.f1.{s}.lo:4}}; {{r.f1.{s}.hi:4}}]")
        put("T0", g, s, "exact-match toàn địa chỉ [CI] (tỷ lệ)", f"{{r.em.{s}.v:2}} [{{r.em.{s}.lo:2}}; {{r.em.{s}.hi:2}}]")
    g = "`LOCAL_CPU_RETRAINED`, ba seed 42 / 1337 / 2025 trên CPU cục bộ — WP3b (không trộn với hàng Kaggle ở trên)"
    for model, name in (("pcrf", "PHOBERT-CRF"), ("dyn", "PROPOSED-DYN")):
        put("T0", g, name, "F1 mean ± std (n = 3)", f"{{m.{model}.t0_f1.mean:4}} ± {{m.{model}.t0_f1.std:4}}")
        put("T0", g, name, "F1 theo seed", f"{{m.{model}.42.f1:4}} / {{m.{model}.1337.f1:4}} / {{m.{model}.2025.f1:4}}")
        put("T0", g, name, "exact-match mean ± std", f"{{m.{model}.exact_match.mean:1}} ± {{m.{model}.exact_match.std:1}}")
    g = "Hiệu PHOBERT-CRF − PROPOSED-DYN"
    put("T0", g, "Sprint 3, Kaggle seed 42 (WP3a)", "ΔF1", "{r.pair.pcrf_dyn.d:+4} [CI ghép cặp {r.pair.pcrf_dyn.lo:+4}; {r.pair.pcrf_dyn.hi:+4}]")
    put("T0", g, "ba seed cục bộ (WP3b)", "ΔF1", "{m.delta.mean:+4} ± {m.delta.std:4} (mean ± std của hiệu)")

    g = "Test Sprint 3, 64 mẫu eligible, `Lai` support 5 (`POST_HOC_SECONDARY`) — checkpoint Sprint 3 và pipeline T1-PIPE (WP2)"
    t1_sys = [("HEUR-JW", "HEUR-JW"), ("PROPOSED-DYN", "DYN gốc (Kaggle seed 42)"), ("T1-PIPE-CRF", "T1-PIPE-CRF"),
              ("T1-PIPE-PCRF", "T1-PIPE-PCRF"), ("T1-PIPE-DYN", "T1-PIPE-DYN"), ("T1-FEAT", "T1-FEAT")]
    for s, name in t1_sys:
        put("T1", g, name, "accuracy [CI cụm]", f"{{t1.{s}.test.acc:3}} [{{t1.{s}.test.lo:3}}; {{t1.{s}.test.hi:3}}]")
        put("T1", g, name, "macro-F1", f"{{t1.{s}.test.mf1:3}}")
        put("T1", g, name, "`Lai` recall", f"{{t1.{s}.test.lai_r:3}}")
    g = "Tập stress (tổng hợp, cùng generator) — WP2"
    for s in ("HEUR-JW", "T1-FEAT"):
        put("T1", g, s, "synth_eval (2.195): accuracy", f"{{t1.{s}.synth.acc:3}}")
        put("T1", g, s, "data06 (580, chỉ `Lai`): `Lai` recall", f"{{t1.{s}.d06.rec:3}}")
    g = "`LOCAL_CPU_RETRAINED`, ba seed — WP2b (checkpoint huấn luyện lại, không phải checkpoint Sprint 3)"
    for s, name in (("PROPOSED-DYN", "DYN ngưỡng 0,7 / 0,2"), ("DYN-ARGMAX-DIAGNOSTIC", "DYN argmax (chẩn đoán)"),
                    ("T1-PIPE-PCRF", "T1-PIPE-PCRF"), ("T1-PIPE-DYN", "T1-PIPE-DYN"), ("T1-HEAD-PROBE", "T1-HEAD-PROBE")):
        put("T1", g, name, "test: accuracy mean ± std", f"{{t2l.{s}.test.acc:3}} ± {{t2l.{s}.test.acc_sd:3}}")
        put("T1", g, name, "test: macro-F1 mean", f"{{t2l.{s}.test.mf1.m:3}}")
        put("T1", g, name, "synth_eval: accuracy mean", f"{{t2l.{s}.synth.acc:3}}")
        put("T1", g, name, "data06: `Lai` recall mean", f"{{t2l.{s}.d06.lai_r:3}}")
    g = "Để so: DYN Sprint 3 trên Kaggle"
    put("T1", g, "DYN (Kaggle seed 42, WP3b)", "test: accuracy / macro-F1", "{m.kaggle.dyn.t1acc:3} / {m.kaggle.dyn.t1f1:3}")

    g = "Oracle-segmentation, N2, 600 cặp — WP1"
    for s, name in (("T2-LOOKUP-STRICT", "STRICT"), ("T2-LOOKUP-DEFAULT-MAIN", "DEFAULT-MAIN"),
                    ("T2-LOOKUP-DEFAULT-FIRST", "DEFAULT-FIRST"), ("T2-SINGLE-VERSION", "SINGLE-VERSION")):
        put("T2", g, name, "cũ→mới: accuracy [CI cụm]",
            f"{{t2.{s}.cu_to_moi.acc:3}} [{{t2.{s}.cu_to_moi.ci.lo:3}}; {{t2.{s}.cu_to_moi.ci.hi:3}}]")
        put("T2", g, name, "cũ→mới: lỗi im lặng (/600)", f"{{t2.{s}.cu_to_moi.sil:i}}")
        if s == "T2-LOOKUP-STRICT":
            put("T2", g, name, "mới→cũ: accuracy [CI cụm]", "{t2.T2-LOOKUP-STRICT.moi_to_cu.acc:3} (DEGENERATE: luôn abstain)")
        else:
            put("T2", g, name, "mới→cũ: accuracy [CI cụm]",
                f"{{t2.{s}.moi_to_cu.acc:3}} [{{t2.{s}.moi_to_cu.ci.lo:3}}; {{t2.{s}.moi_to_cu.ci.hi:3}}]")
        put("T2", g, name, "mới→cũ: lỗi im lặng (/600)", f"{{t2.{s}.moi_to_cu.sil:i}}")
    put("T2", g, "T2-VNADMIN (geocoder tắt)", "cũ→mới: accuracy [CI cụm]",
        "{t2.T2-VNADMIN.cu_to_moi.acc:3} [{t2.T2-VNADMIN.cu_to_moi.ci.lo:3}; {t2.T2-VNADMIN.cu_to_moi.ci.hi:3}]")
    put("T2", g, "T2-VNADMIN (geocoder tắt)", "cũ→mới: lỗi im lặng (/600)", "{t2.T2-VNADMIN.cu_to_moi.sil:i}")
    g = "Điều kiện pipeline (span từ mô hình rồi DEFAULT-MAIN; cũ→mới; N2) — WP1"
    put("T2", g, "HEUR-JW → DEFAULT-MAIN", "accuracy", "{t2.pipe.heur.acc:3}")
    put("T2", g, "HEUR-JW → DEFAULT-MAIN", "coverage", "{t2.pipe.heur.cov:3}")
    put("T2", g, "CRF-INDEP → DEFAULT-MAIN", "accuracy", "{t2.pipe.crf.acc:3}")
    put("T2", g, "CRF-INDEP → DEFAULT-MAIN", "coverage", "{t2.pipe.crf.cov:3}")
    return tables


def findings_text(d: Doc) -> dict[str, str]:
    R = lambda t, label: R_(d, t, label)
    out = {}
    out["t2_asym"] = R(
        "Bất đối xứng hai chiều là cấu trúc của cải cách, không phải độ khó của mô hình: {t2.graph.share_old_keys_deterministic:p1} khóa cũ "
        "giải tất định so với {t2.graph.share_new_keys_deterministic:p1} khóa mới (trung bình {t2.graph.mean_fan_in:2} phường cũ/phường mới); "
        "DEFAULT-MAIN đạt {t2.T2-LOOKUP-DEFAULT-MAIN.cu_to_moi.acc:3} cũ→mới và {t2.T2-LOOKUP-DEFAULT-MAIN.moi_to_cu.acc:3} "
        "mới→cũ với {t2.T2-LOOKUP-DEFAULT-MAIN.moi_to_cu.sil:i}/600 lỗi im lặng (CI Δ cụm phường mới "
        "[{t2.e3.T2-LOOKUP-DEFAULT-MAIN.lo:3}; {t2.e3.T2-LOOKUP-DEFAULT-MAIN.hi:3}]). Chuẩn hóa tên quan trọng hơn mọi luật chọn: "
        "accuracy cũ→mới {t2.norm.N0:3} (N0) / {t2.norm.N1:3} (N1) / {t2.norm.N2:3} (N2). Mức {t2.T2-LOOKUP-DEFAULT-MAIN.cu_to_moi.acc:p1} của "
        "luật mặc định là do cách lấy mẫu Data 07: đúng {t2.form.main.cu_to_moi:3} trên cặp \"nhập chủ yếu\" ({t2.form.main.n:i}) và "
        "{t2.form.part.cu_to_moi:3} trên cặp \"một phần\" ({t2.form.part.n:i}). Nguồn: `09_t2_baseline_results.md` §3, §8, §9.", "f.t2")
    out["model"] = R(
        "Mô hình đề xuất không hơn PhoBERT-CRF ở T0: ba seed cục bộ cho PHOBERT-CRF {m.pcrf.t0_f1.mean:4} ± {m.pcrf.t0_f1.std:4} và "
        "PROPOSED-DYN {m.dyn.t0_f1.mean:4} ± {m.dyn.t0_f1.std:4}; hiệu {m.delta.mean:+4} ± {m.delta.std:4} đổi dấu theo seed, "
        "hiệu Kaggle seed 42 ({r.pair.pcrf_dyn.d:+4}, CI ghép cặp [{r.pair.pcrf_dyn.lo:+4}; {r.pair.pcrf_dyn.hi:+4}]) nằm trong biến thiên seed: "
        "không phân biệt được (không phải \"tương đương\"). Ở T1 mô hình kém baseline luật: accuracy {t1.PROPOSED-DYN.test.acc:3} so với "
        "{t1.HEUR-JW.test.acc:3} của HEUR-JW (Δ {t1.dyn.d_heur.d:3} [{t1.dyn.d_heur.lo:3}; {t1.dyn.d_heur.hi:3}]), ba seed cục bộ "
        "{t2l.PROPOSED-DYN.test.acc:3} ± {t2l.PROPOSED-DYN.test.acc_sd:3}. T1 tốt nhất đến từ ghép span với gazetteer: T1-PIPE-PCRF/-DYN "
        "{t1.T1-PIPE-PCRF.test.acc:3} ở cả ba seed, `Lai` recall {t1.T1-PIPE-PCRF.test.lai_r:3} trên test nhưng chỉ "
        "{t2l.T1-PIPE-PCRF.d06.lai_r:3} trên data06 (trùng danh pháp). Biến thiên T1 của DYN giữa seed nằm ở tỷ lệ từ chối dưới ngưỡng cố định: "
        "accuracy argmax {m.dyn.42.argmax:3} / {m.dyn.1337.argmax:3} / {m.dyn.2025.argmax:3} (ổn định), accuracy có ngưỡng "
        "{m.dyn.42.t1acc:3} / {m.dyn.1337.t1acc:3} / {m.dyn.2025.t1acc:3}. Nguồn: `11_reliability_results.md` phần a, b5; `10_t1_h5_results.md` §11.", "f.model")
    out["crf"] = (
        "**Suy luận, không có thí nghiệm cô lập** (13 §9.2, §11): đường giải mã không ràng buộc của PhoBERT-CRF và DYN gần như là argmax của emission "
        "(encoder + lớp tuyến tính) dưới mặt nạ BIO, nên lớp CRF gần như không được dùng. Cơ sở đo: độ lớn tham số transitions tối đa chỉ 0,092 ở cả 8 checkpoint "
        "(DYN Kaggle [−0,068; +0,045], PHOBERT-CRF Kaggle [−0,077; +0,050], DYN seed 1337 [−0,092; +0,055]; đo lại từ `crf_params/*.json`, `tables/cross_check.csv`), "
        "trong khi khoảng cách emission top-1/top-2 của **DYN Kaggle trên test** có trung vị 3,29 (số đo của review WP5, Q2, báo cáo 13 §2 trích lại; "
        "không đo lại ở gói này và không đo cho PhoBERT-CRF). Hệ quả đã đo: dư địa của ràng buộc bằng 0 trên dữ liệu sạch (ý 4).")
    out["constraint"] = R(
        "Ràng buộc giải mã không có tác dụng trên dữ liệu sạch vì dư địa bằng {w5.hr.test.n:i}: đường giải mã không ràng buộc không sinh `QuanHuyen` cho "
        "địa chỉ mới ({w5.hr.test.n:i}/{w5.hr.test.gold:i} mẫu gold-new trên test; một mẫu ngoại lệ ở seed 1337). Ràng buộc kích hoạt "
        "{w5.onoff.test_kaggle.ban:i} mẫu nhưng chỉ đổi {w5.onoff.test_kaggle.chg:i} mẫu và làm hại (ΔF1 {w5.onoff.test_kaggle.d:4}, CI chạm 0); ba seed cục bộ "
        "đổi 0 mẫu. Dư địa chỉ có trên track 5 trường (`DEVELOPMENT_TRACK`, nhiễu/thiếu trường): {w5.hr.5f.n:i}/{w5.hr.5f.gold:i} mẫu, DYN chỉ khai thác "
        "{w5.hr.5f.dynmoi:i}; cận trên ORACLE ΔF1 {w5.oracle.fivefield_kaggle.d:+4} [{w5.oracle.fivefield_kaggle.lo:+4}; {w5.oracle.fivefield_kaggle.hi:+4}] "
        "(đánh giá thấp vì scorer 5 trường so bề mặt chưa chuẩn hóa; không so với std giữa seed). Nguồn: `13_constraint_ablation_and_h1.md` §2, §6, §7.", "f.constraint")
    out["h2"] = R(
        "H2 phụ thuộc thước đo: BASE tụt {h2.drop.gt.rel:p1} theo `gt` (F1 {h2.drop.gt.held:3} so với {h2.drop.gt.full:3}; "
        "{h2.drop.gt.nh:i} dòng thiếu trường so với {h2.drop.gt.nf:i} dòng đầy đủ) nhưng chỉ {h2.drop.surface.rel:p1} theo `surface` "
        "(Δ {h2.drop.surface.d:3}); chênh chủ yếu do 25,3% trường GT vắng khỏi chuỗi (báo cáo 12 §3). Thêm dữ liệu thiếu trường không hơn thêm dữ liệu đầy đủ "
        "(Δ {h2.p.miss_full.d:3} [{h2.p.miss_full.lo:3}; {h2.p.miss_full.hi:3}]). Nguồn: `12_cpu_hypothesis_results.md` §3.", "f.h2")
    return out


def R_(d: Doc, template: str, label: str) -> str:
    return d.render(template, label)[0]


def md_table(header: list[str], rows: list[list[str]]) -> str:
    esc = lambda s: str(s).replace("|", "\\|")
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(esc(x) for x in row) + " |" for row in rows]
    return "\n".join(lines)


def pivot(rows: list[dict]) -> str:
    """One markdown table per group; the source of every cell is in tables/unified_cells.csv."""
    out = []
    for group in dict.fromkeys(r["Nhom"] for r in rows):
        sub = [r for r in rows if r["Nhom"] == group]
        cols = list(dict.fromkeys(r["Cot"] for r in sub))
        order = list(dict.fromkeys(r["Hang"] for r in sub))
        grid: dict[str, dict[str, str]] = {}
        for r in sub:
            grid.setdefault(r["Hang"], {})[r["Cot"]] = r["HienThi"]
        out.append(f"*{group}*\n\n" + md_table(["Hệ"] + cols, [[h] + [grid[h].get(col, "") for col in cols] for h in order]))
    return "\n\n".join(out)


def write_csv(path: Path, header: list[str], rows: list[dict]):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def report_markdown(hyp: list[dict], tables: dict, findings: dict, checks: list[dict], links: list[dict],
                    hash_rows: list[dict], extra: dict) -> str:
    diff = [r for r in checks if r["status"] == "DIFFERENT"]
    diff_lines = ("\n".join(f"- Báo cáo {r['report']} {r['location']}: báo cáo ghi {r['reported_text']}, file kết quả cho {r['file_value']} ({r['source']})."
                            for r in diff) if diff else "")
    link_diff = [r for r in links if r["status"] != "OK"]
    parts = [
        "# 14. Tổng hợp kết quả Nhóm 1 (WP0–WP5)",
        "",
        extra["header"],
        "",
        "## a. Giả thuyết H1–H5 và thí nghiệm E1–E4",
        "",
        "Trạng thái lấy từ **báo cáo đã sửa theo review** (nhãn gốc ghi cạnh bên); không nâng hạng, không làm mềm kết quả âm. "
        "Nhãn \"quy đổi\" của H2 và E1 là của WP6 (báo cáo 12 chỉ có nhãn từng ý). Phân công ĐACN/ĐATN theo đề cương mục 6.",
        "",
        md_table(["Mã", "Phân công", "Trạng thái", "Nhãn gốc", "Bằng chứng", "Cỡ mẫu", "Đường dẫn"],
                 [[h["Ma"], h["PhanCong"], f"**{h['TrangThai']}**", h["NhanGoc"], h["BangChung"], h["CoMau"], h["DuongDan"]] for h in hyp]),
        "",
        "## b. Bảng T0 / T1 / T2 hợp nhất",
        "",
        "Mọi số trong bảng đọc từ file kết quả; nguồn từng ô ở `tables/unified_cells.csv`. "
        "Hàng `LOCAL_CPU_RETRAINED` là checkpoint huấn luyện lại trên CPU, **không trộn** với hàng Kaggle seed 42 của Sprint 3. "
        "Test Sprint 3 đã bị quan sát: mọi số trên test là hậu nghiệm.",
        "",
        "### b1. T0 (test Sprint 3, 100 mẫu / 446 span)",
        "",
        pivot(tables["T0"]),
        "",
        "### b2. T1 (test 64 eligible, `Lai` support 5; synth_eval 2.195; data06 580 — stress track)",
        "",
        pivot(tables["T1"]),
        "",
        "### b3. T2 (Data 07, 600 cặp: B 244, M 356; A/C `NOT_EVALUABLE_NO_SUPPORT`; oracle-segmentation, N2)",
        "",
        pivot(tables["T2"]),
        "",
        "## c. Phát hiện xuyên gói",
        "",
        f"**1. T2: bất đối xứng do cấu trúc.** {findings['t2_asym']}",
        "",
        f"**2. Mô hình đề xuất không hơn PhoBERT-CRF (T0) và kém baseline luật (T1).** {findings['model']}",
        "",
        f"**3. Lớp CRF gần như không được dùng.** {findings['crf']}",
        "",
        f"**4. Ràng buộc không có dư địa trên dữ liệu sạch.** {findings['constraint']}",
        "",
        f"**5. H2 phụ thuộc thước đo.** {findings['h2']}",
        "",
        "## d. Giới hạn và đe dọa tính hợp lệ",
        "",
        extra["limits"],
        "",
        "## e. Phần còn thiếu, theo nguyên nhân",
        "",
        extra["missing"],
        "",
        "## f. Sai lệch phát hiện ở bước kiểm chéo",
        "",
        extra["deviations_intro"],
        "",
        diff_lines,
        "" if not link_diff else "\n".join(f"- Liên kết hash giữa các run khác nhau: {r['link']} (khai báo {r['declared'][:12]}…, thực tế {r['actual'][:12]}…)" for r in link_diff),
        extra["deviations"],
        "",
        "## Kiểm thử và tái lập",
        "",
        extra["repro"],
    ]
    return "\n".join(parts) + "\n"


# Same quantity reported by two different work packages: (description, cell a, cell b, tolerance)
CONSISTENCY = [
    ("T1 accuracy HEUR-JW, test: WP2 so với WP3a", "t1.HEUR-JW.test.acc", "r.t1.HEUR-JW.accuracy.v", 1e-6),
    ("T1 accuracy DYN Kaggle, test: WP2 so với WP3a", "t1.PROPOSED-DYN.test.acc", "r.t1.PROPOSED-DYN.accuracy.v", 1e-6),
    ("T1 macro-F1 DYN Kaggle, test: WP2 so với WP3a", "t1.PROPOSED-DYN.test.mf1", "r.t1.PROPOSED-DYN.macro_f1.v", 1e-6),
    ("T1 accuracy DYN Kaggle, test: WP3b (hàng riêng) so với WP3a", "m.kaggle.dyn.t1acc", "r.t1.PROPOSED-DYN.accuracy.v", 5e-5),
    ("T0 F1 PROPOSED-DYN Kaggle: WP3a so với WP5", "r.f1.PROPOSED-DYN.v", "w5.x22.PROPOSED-DYN", 1e-6),
    ("T0 F1 PHOBERT-CRF Kaggle: WP3a so với WP5", "r.f1.PHOBERT-CRF.v", "w5.x22.PHOBERT-CRF", 1e-6),
    ("T0 F1 CRF-INDEP: WP3a so với WP4 (điều kiện gốc)", "r.f1.CRF-INDEP.v", "h3.crf.original_text.f1", 5e-5),
    ("T0 F1 HEUR-JW: WP3a so với WP4 (điều kiện gốc)", "r.f1.HEUR-JW.v", "h3.heur.original_text.f1", 5e-5),
    ("T1 accuracy DYN ba seed, mean: WP3b so với WP2b", "m.dyn.t1_accuracy.mean", "t2l.PROPOSED-DYN.test.acc", 5e-5),
    ("T1-PIPE-PCRF test accuracy: WP2 (span Kaggle) so với WP2b (mean ba seed)", "t1.T1-PIPE-PCRF.test.acc", "t2l.T1-PIPE-PCRF.test.acc", 1e-6),
] + [(f"T0 F1 {name} seed {seed}: WP3b so với WP5", f"m.{model}.{seed}.f1", f"w5.seed.{seed}.{model}", 5e-5)
     for seed in SEEDS for model, name in (("pcrf", "PHOBERT-CRF"), ("dyn", "PROPOSED-DYN"))]


def run_consistency(cells: Cells) -> list[dict]:
    rows = []
    for desc, a, b, tol in CONSISTENCY:
        va, vb = float(cells.get(a)), float(cells.get(b))
        rows.append({"quantity": desc, "value_a": va, "source_a": cells.source(a), "value_b": vb,
                     "source_b": cells.source(b), "tolerance": tol, "status": "AGREE" if abs(va - vb) <= tol else "DISAGREE"})
    return rows


def build_extra(doc: Doc, checks: list[dict], consistency: list[dict], links: list[dict], hash_rows: list[dict],
                test_summary: str) -> dict[str, str]:
    """Hand-written sections of report 14. Numbers inside {..} are cell references; the rest cites a report section."""
    R = lambda template, label: doc.render(template, label)[0]
    n_hash = len(hash_rows)
    n_pred = sum("predictions" in r["file"] for r in hash_rows)
    bad_checks = [r for r in checks if r["status"] == "DIFFERENT"]
    bad_cons = [r for r in consistency if r["status"] != "AGREE"]
    bad_links = [r for r in links if r["status"] != "OK"]
    out = {}
    out["header"] = R(
        "**Ngày:** 15/10/2026. **Phạm vi:** tổng hợp WP0–WP5 của Nhóm 1 (kế hoạch `06_group1_science_gap_plan.md`, Amendment A2 `08_amendment_a2_group1_scope.md`). "
        "Không chạy thí nghiệm mới: mọi số đọc từ file kết quả đã commit bằng `scripts/73_generate_group1_report.py` "
        "(bảng sinh tự động; manifest, bảng kiểm chéo và nguồn từng ô ở `data/processed/evaluation/sprint04/group1_summary_20261015_v2/`; bản v1 là bản trước review WP6, giữ nguyên). "
        "Nguồn: báo cáo `09`–`13` đã sửa theo review và các bản review trong `reviews/` (WP1: `review_wp1_20261013.md`, review trong phiên điều phối 13/10 được ghi lại thành file ngày 15/10, không phải review mới).\n\n"
        "**Cách đọc.** Test Sprint 3 (100 mẫu / 446 span) đã bị quan sát, nên mọi số trên test là hậu nghiệm; tập tổng hợp thuộc stress track; "
        "hàng `LOCAL_CPU_RETRAINED` là checkpoint huấn luyện lại trên CPU, không trộn với hàng Kaggle seed 42; kết quả âm giữ nguyên.\n\n"
        "**Tóm tắt.**\n"
        "- T0: PHOBERT-CRF {r.f1.PHOBERT-CRF.v:4} và PROPOSED-DYN {r.f1.PROPOSED-DYN.v:4} (Kaggle) không phân biệt được; ba seed cục bộ "
        "{m.pcrf.t0_f1.mean:4} ± {m.pcrf.t0_f1.std:4} và {m.dyn.t0_f1.mean:4} ± {m.dyn.t0_f1.std:4}. PHOBERT-CRF hơn CRF-INDEP ({r.f1.CRF-INDEP.v:4}) và HEUR-JW ({r.f1.HEUR-JW.v:4}) với CI ghép cặp loại 0 (WP3a).\n"
        "- T1: mô hình đề xuất kém baseline luật (accuracy {t1.PROPOSED-DYN.test.acc:3} so với {t1.HEUR-JW.test.acc:3}); T1 tốt nhất đến từ ghép span với gazetteer ({t1.T1-PIPE-PCRF.test.acc:3}).\n"
        "- T2 (lần đầu có số): cũ→mới {t2.T2-LOOKUP-DEFAULT-MAIN.cu_to_moi.acc:3}, mới→cũ {t2.T2-LOOKUP-DEFAULT-MAIN.moi_to_cu.acc:3} với luật mặc định; chênh là cấu trúc của cải cách.\n"
        "- Giả thuyết: SUPPORTED H3, E3; PARTLY_SUPPORTED H2, E1; NOT_SUPPORTED H5; INCONCLUSIVE H4, E2; NOT_TESTABLE H1; NOT_RUN E4.", "header")
    out["limits"] = (
        "1. **Test 100 mẫu / 446 span đã bị quan sát ở Sprint 3**; CI chỉ phản ánh lấy mẫu; hiệu nhỏ hơn khoảng ±0,011 F1 không phân biệt được (11a §4, §8).\n"
        "2. **Gold do một người gán có AI hỗ trợ; IAA chưa đo** (`NOT_MEASURED`): CI không phản ánh nhiễu nhãn (11a §8).\n"
        "3. **Data 07** chỉ có B (244) và M (356); A và C `NOT_EVALUABLE_NO_SUPPORT`; 23 mã phường mới, 49 đơn vị cũ chuẩn hóa, 441/600 dòng ở Hà Nội, một đơn vị cũ chiếm 299 cặp; "
        "được xác minh bằng chính CSV nguồn của gazetteer nên candidate-recall 100% là do cấu trúc (tính vòng lặp) và mỗi đơn vị cũ chỉ có một đích quan sát, "
        "nên không đo được việc chọn đích khác nhau trong cùng một đơn vị (09 §10).\n"
        "4. **Dữ liệu lai cùng một generator**: `Lai` của test, Data 06 và tập tổng hợp đều sinh bằng `generate_hybrid_addresses` từ cùng nguồn OSM; kết quả tốt trên chúng "
        "không chứng minh tổng quát sang địa chỉ lai do người thật viết; tập huấn luyện T1 tổng hợp chỉ 105 dòng (10 §3, §8, §9).\n"
        "5. **Nhãn hiếm và nhãn mốc không có support**: `ToaNha/CanHo`, `MocDinhVi`, `HuongDi`, `GhiChu` support 0 (`NOT_EVALUABLE_NO_GOLD_SUPPORT`); `Khac` support 2; `Lai` support 5 (test) và 8 (dev) — mọi số `Lai` là `LOW_SUPPORT` (11a §2, §8).\n"
        "6. **Checkpoint Kaggle (GPU T4) so với cục bộ (CPU)**: hai nhóm riêng, seed danh nghĩa 42 không cùng lần huấn luyện; **ba seed là ước lượng thô** (n = 3, ddof = 1, cùng một test nên không độc lập về mẫu); "
        "tính tất định mới kiểm trên PHOBERT-CRF seed 42 (11b b4, b6).\n"
        "7. **Silver và track phát triển**: nhãn Data 04 là silver từ generator; thước đo `gt` của H2 bị chặn trên vì 25,3% trường GT vắng khỏi chuỗi (12 §3); track 5 trường là `DEVELOPMENT_TRACK`, hàng không độc lập nên CI theo dòng quá hẹp (13 §10).\n"
        "8. **Gazetteer** mã cũ còn partial (2.187 mã chưa xác minh), hai snapshot 30/06 và 01/07/2025 không phải lịch sử hiệu lực pháp lý; T2 tra bằng tên (09 §10).\n"
        "9. **Dev** đã dùng để chọn (`SELECTION_SET`), chỉ 8 mẫu `cu` và 8 `Lai` nên hiệu chỉnh ngưỡng T1 là `CALIBRATION_NOT_EVALUABLE` (11a §6; protocol mục 7).\n"
        "10. **Ngoài phạm vi đo**: VQA đang HOLD (E4), Data 05 hoãn, Deepparse chưa chạy vì chưa xác minh điều kiện sử dụng checkpoint (AGENTS.md mục 9).")
    out["missing"] = (
        "**(i) Thiếu do dữ liệu — chuyển Nhóm 2 / ĐATN.** Loại A và C ở T2 (Data 07 chỉ có B/M; gazetteer chỉ có 3 cạnh A và 132 cạnh C, 09 §8); E2 (cần dữ liệu mà một đơn vị cũ đi về ít nhất hai đích quan sát); "
        "nhãn mốc/hướng (support 0) và H4 theo nhóm mốc; `Lai` do người thật viết; Accuracy@161km (cần tọa độ); E4 (`NOT_RUN`, VQA đang HOLD: thiếu 130 chuỗi hóa đơn có ground truth đầy đủ).\n\n"
        "**(ii) Thiếu do môi trường.** Tầng 2 của WP4 (H3 và E1 trên PHOBERT-CRF/PROPOSED-DYN) là `NOT_RUN`: adapter khóa đòi ≥ 20 GiB ổ D: trống, đo được khoảng 18 GiB lúc chạy (12 §5). "
        "WP2b chạy được cùng loại adapter khi ổ còn trống khoảng 28 GB (`free_bytes_at_prepare` trong manifest WP2b); suy luận (chưa chạy lại): giải phóng đĩa là đủ, lệnh nằm ở 12 §5. Ngoài ra \"DYN gốc\" (checkpoint Kaggle `7a4a3d01…`) trên hai tập stress vẫn `BLOCKED_LOCAL_NEURAL` vì checkpoint này không nạp được trên CPU (10 §7).\n\n"
        "**(iii) Hoãn có chủ đích.** `DYN-T1-AUG` (`DEFERRED_NEEDS_TRAINING_PROTOCOL_CHANGE`: `load_corpus`/`load_config` ghim hash, cần protocol huấn luyện mới); H1 (không có adapter; điều kiện cần ở 13 §9.3); "
        "ablation ràng buộc trên `t1_stress_v1` (cần suy luận neural, 13 §1).\n\n"
        "**(iv) Tùy chọn.** CI cho track 5 trường (WP3a §7, `NOT_RUN`); ô PHOBERT-CRF trên track 5 trường của WP5 (`NOT_RUN`); pipeline T2 với span neural (chỉ HEUR-JW và CRF-INDEP đã chạy, 09 §10); gán lặp intra-annotator; dev của DYN có ràng buộc `NOT_FOUND` (11a §6; WP5 đã dựng lại bằng giải mã lại).")
    intro = (f"Kiểm chéo bằng `scripts/73`: **{n_hash} hash đầu ra** khai báo trong `run_manifest.json` của tám run đều khớp file hiện tại (không MISMATCH, không thiếu file bắt buộc; "
             f"trong đó {n_pred} file prediction không commit nhưng có trên đĩa và khớp); **{len(checks)} số tiêu đề** của báo cáo 09–13 được đối chiếu với `metrics.json`/CSV: "
             f"{sum(r['status'] == 'MATCH' for r in checks)} khớp, {len(bad_checks)} lệch; **{len(consistency)} đại lượng** do hai gói cùng báo: "
             f"{len(consistency) - len(bad_cons)} khớp, {len(bad_cons)} lệch; **{len(links)} liên kết hash** giữa các run: {len(links) - len(bad_links)} khớp, {len(bad_links)} khác. "
             "Chi tiết ở `tables/hash_verification.csv`, `cross_check.csv`, `cross_report_consistency.csv`, `cross_run_links.csv`. Báo cáo gốc không bị sửa.")
    items = []
    for r in bad_checks:
        items.append(f"- Số lệch: báo cáo {r['report']} {r['location']} ghi {r['reported_text']}, file kết quả cho {r['file_value']} ({r['source']}).")
    for r in bad_cons:
        items.append(f"- Hai gói báo khác nhau: {r['quantity']} ({r['value_a']} so với {r['value_b']}).")
    for r in bad_links:
        items.append(f"- Hash liên kết khác: {r['link']}.")
    if not items:
        items.append("- **Số liệu: không có số nào lệch** ở ba phép kiểm trên.")
    items += [
        "- **Quản trị WP3b (đã biết, 11b b1):** `run_manifest.json` của WP3b không khai báo hash đầu ra, nên `metrics.json` và `tables/per_seed.csv` không có hash để đối chiếu; chỉ kiểm được hash prediction đóng băng "
        "(`frozen_hashes.json`, khớp, và khớp với hash WP5 ghi lại). Hash mã trong manifest (bản B `87fd49e4…`) không khớp script đã commit (bản D); logic không đổi. Số WP3b vẫn khớp WP5 và WP2b (bảng nhất quán).",
        "- **Review WP1 do phiên điều phối thực hiện** (`reviews/review_wp1_20261013.md`, review trong phiên 13/10 được ghi lại thành file ngày 15/10): không phải review của một phiên độc lập riêng như WP2–WP5.",
        "- **Hai định nghĩa \"tình huống D\":** 09 §7.2 (tên phường trùng giữa hai hệ trong cùng tỉnh, phân nhóm theo cạnh gazetteer, trên Data 07) và 10 §4 (thẻ D của `SingleVersionIndex.homonyms` trên mẫu T1, nhạy với tiền tố loại đơn vị). Số hai báo cáo không so được; bảng a chỉ trích số D của báo cáo 09 cho T2.",
        "- **Phán quyết chung của H2 và E1 là quy đổi của WP6:** báo cáo 12 cho nhãn từng ý (H2: tụt ủng hộ / phục hồi đặc thù không ủng hộ; E1: ba ý) và không có nhãn chung cho E1 (review WP4 N2). Hai ô này không phải \"nhãn gốc\" của báo cáo.",
        "- **Cận \"< 0,07\" của báo cáo 13 §2 chỉ đúng với 4/8 checkpoint** (đo lại từ `crf_params/*.json`: PHOBERT-CRF Kaggle [−0,077; +0,050], DYN seed 1337 [−0,092; +0,055], PHOBERT-CRF seed 1337 và 2025 cũng vượt 0,07); độ lớn tối đa là 0,092. Báo cáo 13 là bản sau review và không bị sửa ở gói này; ý c3 dùng cận 0,092 (review WP6 Q1).",
        "- **Làm tròn:** ba CI ở báo cáo 14 khác chữ số cuối so với báo cáo gốc; giá trị trong file là nguồn. H5 Δ T1 DYN − HEUR-JW [−0,389; −0,058] so với 10 §6.1 [−0,388; −0,057] (file −0,388889 / −0,057687; báo cáo 10 cắt bớt); H2 AUG-MISSING − AUG-FULL [−0,013; 0,011] so với 12 [−0,014; +0,011] (file −0,0135); H4 PHOBERT-CRF −0,015 so với 12 −0,016 (file −0,0155).",
        "- **Con số tham số CRF < 0,07 và khoảng cách emission trung vị 3,29** (13 §2) là số đo của review WP5 (Q2) từ `crf_params/` (interim, không commit): không có trong file kết quả đã commit. Khoảng của transitions được đo lại từ file interim và khớp; trung vị 3,29 không đo lại.",
        "- **Tên thư mục là mã phiên bản kế hoạch, không phải ngày chạy** (09 đầu báo cáo; 13 đầu báo cáo): ví dụ `t2_baseline_20261014_v1` chạy 13/10, `constraint_ablation_20261017_v1` chạy 14–15/10.",
        "- Mốc số test trong các báo cáo (349 → 374 → 396 → 406 → 422 → 438) là lịch sử tăng dần theo gói, không phải lệch; mốc hiện tại ở mục dưới.",
    ]
    out["deviations_intro"] = intro
    out["deviations"] = "\n".join(items)
    out["repro"] = (
        f"Bộ test đầy đủ (`python -m unittest discover -s tests -v`, `~/.venv_dacn`): {test_summary}.\n\n"
        "```bash\ncd /mnt/d/DACN && source ~/.venv_dacn/bin/activate\n"
        "python -m scripts.73_generate_group1_report            # từ chối ghi đè; dùng --out-dir group1_summary_20261015_v3 để chạy lại\n"
        "python -m unittest tests.test_group1_summary -v\npython -m unittest discover -s tests\n```\n\n"
        "Mã thoát: 2 (không ghi gì) nếu một hash trong `run_manifest.json` của tám run không khớp, hoặc thiếu manifest/file bắt buộc; 3 nếu thư mục đầu ra đã tồn tại (không ghi đè); 0 nếu xong. "
        "Bản nháp báo cáo do script sinh nằm ở `report_draft.md` trong thư mục đầu ra; báo cáo này chỉ khác bản nháp ở dòng kết quả bộ test (chạy sau khi sinh).")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out-dir", default=DEFAULT_OUT, help="directory name under data/processed/evaluation/sprint04")
    ap.add_argument("--base-dir", default=str(BASE), help="directory holding the eight run directories")
    ap.add_argument("--out-root", help="where --out-dir is created (default: --base-dir)")
    ap.add_argument("--test-summary", default="[[TEST_SUMMARY: điền kết quả bộ test sau khi chạy]]",
                    help="text for the test-suite line of the report (the suite is run after this script)")
    args = ap.parse_args(argv)

    base = Path(args.base_dir)
    out_dir = Path(args.out_root or base) / args.out_dir
    if out_dir.exists():
        print(f"REFUSING to overwrite existing {out_dir}; use --out-dir <name>_v2", file=sys.stderr)
        return 3
    try:
        hash_rows, manifests = verify_all(base, RUNS)
    except HashMismatch as exc:
        print(f"HASH CHECK FAILED, nothing written: {exc}", file=sys.stderr)
        return 2
    links = cross_run_links(base, manifests)

    cells = build_cells(base)
    checks = run_checks(cells) + interim_crf_checks(base)
    doc = Doc(cells)
    hyp = hypothesis_rows(doc)
    tables = t0_t1_rows(doc)
    findings = findings_text(doc)

    consistency = run_consistency(cells)
    extra = build_extra(doc, checks, consistency, links, hash_rows, args.test_summary)

    tables_dir = out_dir / "tables"
    tables_dir.mkdir(parents=True)
    write_csv(tables_dir / "hash_verification.csv", ["run", "file", "expected_sha256", "actual_sha256", "status"], hash_rows)
    write_csv(tables_dir / "cross_run_links.csv", ["link", "declared", "actual", "status"], links)
    write_csv(tables_dir / "cross_check.csv", ["report", "location", "reported_text", "reported_value", "file_value",
                                                "decimals", "status", "source"], checks)
    write_csv(tables_dir / "cross_report_consistency.csv", ["quantity", "value_a", "source_a", "value_b", "source_b",
                                                              "tolerance", "status"], consistency)
    write_csv(tables_dir / "cells.csv", ["cell", "value", "file", "selector"], list(cells.rows.values()))
    unified = [r for name in ("T0", "T1", "T2") for r in tables[name]]
    write_csv(tables_dir / "unified_cells.csv", ["Bang", "Nhom", "Hang", "Cot", "HienThi", "Nguon", "CellIds"], unified)
    hyp_rows = [{**{k: v for k, v in h.items() if k != "cells"}, "CellIds": ",".join(h["cells"]),
                 "Nguon": " ; ".join(cells.source(i) for i in h["cells"]) or h["DuongDan"]} for h in hyp]
    write_csv(tables_dir / "hypotheses.csv", ["Ma", "PhanCong", "TrangThai", "NhanGoc", "BangChung", "CoMau", "DuongDan",
                                               "CellIds", "Nguon"], hyp_rows)

    (out_dir / "report_draft.md").write_text(report_markdown(hyp, tables, findings, checks, links, hash_rows, extra),
                                             encoding="utf-8")
    outputs = {p.relative_to(out_dir).as_posix(): sha256_file(p) for p in sorted(out_dir.rglob("*")) if p.is_file()}
    manifest = {
        "rule_version": RULE_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "purpose": "WP6 cross-check and summary of Group 1; no experiment run",
        "runs": {k: RUNS[k][0] for k in RUNS},
        "run_manifest_sha256": {k: sha256_file(base / RUNS[k][0] / "run_manifest.json") for k in RUNS},
        "hash_checks": {"files": len(hash_rows), "by_status": {s: sum(r["status"] == s for r in hash_rows) for s in sorted({r["status"] for r in hash_rows})}},
        "cross_run_links": {"checked": len(links), "different": sum(r["status"] != "OK" for r in links)},
        "cross_check": {"checked": len(checks), "different": sum(r["status"] == "DIFFERENT" for r in checks),
                        "not_on_disk": sum(r["status"] == "NOT_ON_DISK" for r in checks)},
        "cross_report_consistency": {"checked": len(consistency), "different": sum(r["status"] != "AGREE" for r in consistency)},
        "input_sha256": dict(sorted(cells.files.items())),
        "code_sha256": {"scripts/73_generate_group1_report.py": sha256_file(Path(__file__))},
        "rows_out": {"cells": len(cells.rows), "unified_cells": len(unified), "hypotheses": len(hyp_rows)},
        "output_sha256": outputs,
    }
    (out_dir / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: {len(hash_rows)} hashes verified, {len(checks)} headline numbers checked "
          f"({manifest['cross_check']['different']} different), wrote {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
