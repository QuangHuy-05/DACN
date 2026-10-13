"""Per-sample representation and uncertainty helpers for frozen Sprint 3 predictions.

Read-only analysis: nothing here runs a model.  Predictions are scored with the
Sprint 3 span scorer sample by sample so that the per-sample (tp, fp, fn) rows sum
exactly to the published totals, and statistics are recomputed from the *summed*
counts of every bootstrap resample (see ``src/evaluation/stats.py``).
"""

from __future__ import annotations

import hashlib
import json
import os
from math import isfinite
from pathlib import Path

import numpy as np

from src.evaluation.dev_runner import load_predictions, read_jsonl
from src.evaluation.schema import ADDRESS_SYSTEMS, SPAN11_LABELS, CharacterSpan
from src.evaluation.span_scorer import compute_exact_span_metrics, evaluate_single_sample_spans
from src.evaluation import stats

ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = ROOT / "data/processed/annotation/sprint03/corpus_v1_release2"
FINAL_DIR = ROOT / "data/interim/modeling/sprint03/final_completion_20261005_v1"
KAGGLE_DIR = (FINAL_DIR / "kaggle_final_output_v4/dacn_artifacts/dacn-s3-final-infer-20261005-v4"
              / "workspace/data/interim/modeling/sprint03/dacn-s3-final-infer-20261005-v4")
DEV_SEARCH_ROOTS = (
    ROOT / "data/interim/modeling/sprint03/release_and_kaggle_20261005_v1",
    ROOT / "data/processed/evaluation/sprint03",
)

SEED = 20261014
N_RESAMPLES = 10_000
LOW_SUPPORT_THRESHOLD = 10

SYSTEMS = ("HEUR-JW", "CRF-INDEP", "PHOBERT-CRF", "PROPOSED-DYN", "PROPOSED-NO-CONSTRAINT")
# CRF-INDEP and PHOBERT-CRF have no T1 head; the scorer's 0.0 there only means "every sample khong_ro".
T1_NOT_IMPLEMENTED = ("CRF-INDEP", "PHOBERT-CRF")
LIGHT_TEST_DIRS = {"HEUR-JW": "light_test_runs_v2/heur-jw", "CRF-INDEP": "light_test_runs_v2/crf-indep"}
NEURAL_TEST_DIRS = {"PHOBERT-CRF": "pcrf_test", "PROPOSED-DYN": "dyn_test", "PROPOSED-NO-CONSTRAINT": "dyn_off_test"}

# Published Sprint 3 test scores (docs/sprints/sprint_03/49_sprint3_final_results.md), P/R/F1 rounded to 4 dp.
PUBLISHED_T0 = {
    "HEUR-JW": (0.9512, 0.8744, 0.9112),
    "CRF-INDEP": (0.9234, 0.8924, 0.9076),
    "PHOBERT-CRF": (0.9843, 0.9843, 0.9843),
    "PROPOSED-DYN": (0.9821, 0.9821, 0.9821),
    "PROPOSED-NO-CONSTRAINT": (0.9843, 0.9843, 0.9843),
}
PUBLISHED_T1 = {  # accuracy, macro-F1 over 3 classes, 64 eligible
    "HEUR-JW": (0.9219, 0.9249),
    "PROPOSED-DYN": (0.7188, 0.5626),
    "PROPOSED-NO-CONSTRAINT": (0.7188, 0.5626),
}

N_CLASSES = len(ADDRESS_SYSTEMS)
ABSTAIN_INDEX = N_CLASSES  # predicted class index for khong_ro / abstain


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(path: Path) -> Path:
    if not Path(path).exists():
        raise FileNotFoundError(f"Required input missing: {path}")
    return Path(path)


# --------------------------------------------------------------------- inputs
def load_corpus_manifest() -> dict:
    return json.loads(_require(CORPUS_DIR / "manifest.json").read_text(encoding="utf-8"))


def load_gold(split: str) -> tuple[list[dict], list[str]]:
    """Gold rows plus the T1 exclusion IDs of the split; the file hash is checked against the manifest."""
    manifest = load_corpus_manifest()
    name = {"test": "test_benchmark_t0.jsonl", "dev": "dev.jsonl"}[split]
    path = _require(CORPUS_DIR / name)
    expected = manifest["output_sha256"][name]
    if sha256_file(path) != expected:
        raise ValueError(f"{name} does not match the corpus manifest hash")
    key = "test_evaluation_exclusions" if split == "test" else "evaluation_exclusions"
    rows = read_jsonl(path)
    # The manifest's dev list ("evaluation_exclusions") also carries the 16 test IDs; the scorer rejects IDs
    # absent from the split, so only the IDs present in this split's gold are passed on.
    present = {row["sample_id"] for row in rows}
    return rows, [sid for sid in manifest[key]["t1"] if sid in present]


def load_source_datasets() -> dict[str, str]:
    registry = read_jsonl(_require(CORPUS_DIR / "identity_registry.jsonl"))
    return {row["sample_id"]: row["source_dataset"] for row in registry}


def test_prediction_paths() -> dict[str, Path]:
    """Real prediction paths (the run_dir fields of the freeze file point to a moved workspace)."""
    paths = {name: FINAL_DIR / rel / "predictions.jsonl" for name, rel in LIGHT_TEST_DIRS.items()}
    paths.update({name: KAGGLE_DIR / rel / "predictions.jsonl" for name, rel in NEURAL_TEST_DIRS.items()})
    return {name: paths[name] for name in SYSTEMS}


def verify_frozen_hashes(paths: dict[str, Path]) -> dict[str, dict]:
    """Stop before any computation if a prediction file differs from the freeze record."""
    frozen = json.loads(_require(FINAL_DIR / "all_test_predictions_frozen.json").read_text(encoding="utf-8"))
    report = {}
    for name, path in paths.items():
        expected = frozen["models"][name]["predictions_sha256"]
        actual = sha256_file(_require(path))
        if actual != expected:
            raise ValueError(f"{name}: prediction hash {actual} != frozen {expected}")
        report[name] = {"path": str(path.relative_to(ROOT)), "sha256": actual, "frozen_sha256": expected}
    return report


def locate_dev_predictions() -> dict[str, dict]:
    """Find each system's selected dev predictions and verify them against the selection lock evidence.

    The lock paths of the neural systems no longer exist, so a copy is searched by hash only.
    A system whose selected dev run has no hash-matching copy is NOT_FOUND; no other file is substituted.
    """
    lock_paths = {name: _require(FINAL_DIR / rel / "selection_lock.json") for name, rel in LIGHT_TEST_DIRS.items()}
    lock_paths.update({name: _require(KAGGLE_DIR / rel / "selection_lock.json") for name, rel in NEURAL_TEST_DIRS.items()})
    index: dict[str, Path] | None = None
    result = {}
    for name in SYSTEMS:
        lock = json.loads(lock_paths[name].read_text(encoding="utf-8"))
        selected = lock["selected_dev_run"]
        expected = lock["dev_evidence"].get(f"{selected}/predictions.jsonl")
        info = {"selected_dev_run": selected, "expected_sha256": expected, "status": "NOT_FOUND", "path": None}
        direct = ROOT / selected / "predictions.jsonl"
        if expected and direct.exists() and sha256_file(direct) == expected:
            info.update(status="FOUND", path=direct)
        elif expected:
            if index is None:
                index = _hash_index()
            if expected in index:
                info.update(status="FOUND", path=index[expected])
        if name == "PROPOSED-DYN" and "no_constraint" in selected:
            # The selection evidence of the constrained model only holds the unconstrained dev run, so there is
            # no dev prediction of the constrained decoder; substituting it would mislabel the system.
            info.update(status="NOT_FOUND_ONLY_NO_CONSTRAINT_DEV_RUN_EXISTS", found_path=info["path"], path=None)
        result[name] = info
    return result


def _hash_index() -> dict[str, Path]:
    index: dict[str, Path] = {}
    for root in DEV_SEARCH_ROOTS:
        for dirpath, _, files in os.walk(root):
            if "predictions.jsonl" in files:
                path = Path(dirpath) / "predictions.jsonl"
                index.setdefault(sha256_file(path), path)
    return index


# ---------------------------------------------------------- per-sample units
def build_units(predictions, golds: list[dict], excluded_t1: list[str]) -> dict:
    """Per-sample rows for one system. All gold samples must have exactly one prediction."""
    pred_by_id = {p.sample_id: p for p in predictions}
    if len(pred_by_id) != len(predictions) or set(pred_by_id) != {g["sample_id"] for g in golds}:
        raise ValueError("Predictions must cover the gold samples exactly once")
    excluded = set(excluded_t1)
    label_index = {label: i for i, label in enumerate(SPAN11_LABELS)}
    n = len(golds)
    totals = np.zeros((n, 3), dtype=np.int64)
    by_label = np.zeros((n, len(SPAN11_LABELS), 3), dtype=np.int64)
    exact = np.zeros(n, dtype=np.int64)
    t1_rows, t1_ids = [], []
    for i, gold in enumerate(golds):
        pred = pred_by_id[gold["sample_id"]]
        text = gold["text"]
        gold_spans = [CharacterSpan(s["start"], s["end"], s["label"], text[s["start"]:s["end"]],
                                    s.get("system", "khong_xac_dinh")) for s in gold["spans"]]
        evaluation = evaluate_single_sample_spans(pred.spans, gold_spans, raw_text=text)
        for _, _, label in evaluation["tp_keys"]:
            by_label[i, label_index[label], 0] += 1
        for _, _, label in evaluation["fp_keys"]:
            by_label[i, label_index[label], 1] += 1
        for _, _, label in evaluation["fn_keys"]:
            by_label[i, label_index[label], 2] += 1
        totals[i] = (evaluation["tp_count"], evaluation["fp_count"], evaluation["fn_count"])
        exact[i] = int(evaluation["fp_count"] == 0 and evaluation["fn_count"] == 0)
        gold_system = None if gold["sample_id"] in excluded else gold.get("address_system")
        if gold_system in ADDRESS_SYSTEMS:
            abstained = pred.abstain or pred.predicted_system == "khong_ro"
            predicted = ABSTAIN_INDEX if abstained else ADDRESS_SYSTEMS.index(pred.predicted_system)
            t1_rows.append((ADDRESS_SYSTEMS.index(gold_system), predicted))
            t1_ids.append(gold["sample_id"])
    return {
        "sample_ids": [g["sample_id"] for g in golds],
        "totals": totals, "by_label": by_label, "exact": exact,
        "t1": np.asarray(t1_rows, dtype=np.int64).reshape(-1, 2), "t1_ids": t1_ids,
        "all_predicted_khong_ro": all(p.predicted_system == "khong_ro" for p in predictions),
    }


def scorer_metrics(predictions, golds, excluded_t1) -> dict:
    return compute_exact_span_metrics(predictions, golds, excluded_t1_sample_ids=excluded_t1)


def check_units_against_scorer(units: dict, metrics: dict) -> dict:
    """Per-sample sums must equal the scorer's totals (T0 overall, per label, T1 accuracy)."""
    micro = metrics["t0_exact_span"]["micro"]
    sums = units["totals"].sum(axis=0)
    ok = (int(sums[0]), int(sums[1]), int(sums[2])) == (micro["total_tp"], micro["total_fp"], micro["total_fn"])
    per_label_ok = True
    for i, label in enumerate(SPAN11_LABELS):
        s = units["by_label"][:, i, :].sum(axis=0)
        m = metrics["t0_exact_span"]["per_label"][label]
        per_label_ok &= (int(s[0]), int(s[1]), int(s[2])) == (m["tp"], m["fp"], m["fn"])
    t1 = units["t1"]
    t1_ok = len(t1) == metrics["t1_address_system"]["total_evaluated"]
    if len(t1):
        t1_ok &= round(float((t1[:, 0] == t1[:, 1]).mean()), 4) == metrics["t1_address_system"]["overall_accuracy"]
    return {"t0_total": bool(ok), "t0_per_label": bool(per_label_ok), "t1": bool(t1_ok)}


# ----------------------------------------------------------------- statistics
def f1_stat(counts: np.ndarray) -> float:
    return stats.micro_f1_from_counts(counts)


def precision_stat(counts: np.ndarray) -> float:
    s = np.asarray(counts, dtype=float).sum(axis=0)
    return float("nan") if s[0] + s[1] == 0 else float(s[0] / (s[0] + s[1]))


def recall_stat(counts: np.ndarray) -> float:
    s = np.asarray(counts, dtype=float).sum(axis=0)
    return float("nan") if s[0] + s[2] == 0 else float(s[0] / (s[0] + s[2]))


def t1_accuracy_stat(units: np.ndarray) -> float:
    return float("nan") if len(units) == 0 else float((units[:, 0] == units[:, 1]).mean())


def t1_coverage_stat(units: np.ndarray) -> float:
    return float("nan") if len(units) == 0 else float((units[:, 1] != ABSTAIN_INDEX).mean())


def _class_f1(units: np.ndarray, cls: int) -> float:
    gold, pred = units[:, 0], units[:, 1]
    tp = int(((gold == cls) & (pred == cls)).sum())
    fp = int(((gold != cls) & (pred == cls)).sum())
    fn = int(((gold == cls) & (pred != cls)).sum())
    return 0.0 if 2 * tp + fp + fn == 0 else 2 * tp / (2 * tp + fp + fn)


class MacroF1:
    """Macro-F1 over the classes present in the gold of the (re)sample.

    On the full sample all three classes are present, which equals the scorer's
    ``macro_f1_all_3_classes``.  Resamples missing a gold class average over the
    present classes and are counted (``missing_class_calls`` / ``calls``).
    """

    def __init__(self) -> None:
        self.calls = 0
        self.missing_class_calls = 0

    def __call__(self, units: np.ndarray) -> float:
        self.calls += 1
        present = [c for c in range(N_CLASSES) if (units[:, 0] == c).any()]
        if len(present) < N_CLASSES:
            self.missing_class_calls += 1
        if not present:
            return float("nan")
        return float(np.mean([_class_f1(units, c) for c in present]))

    @property
    def missing_share(self) -> float | None:
        return self.missing_class_calls / self.calls if self.calls else None


def lai_f1_stat(units: np.ndarray) -> float:
    """F1 of class Lai; undefined (NaN) when the resample has no gold Lai."""
    lai = ADDRESS_SYSTEMS.index("Lai")
    return float("nan") if not (units[:, 0] == lai).any() else _class_f1(units, lai)


def support_flag(support: int) -> str:
    if support == 0:
        return "NOT_EVALUABLE_NO_GOLD_SUPPORT"
    return "LOW_SUPPORT" if support < LOW_SUPPORT_THRESHOLD else "OK"


def bootstrap(stat, units, seed: int = SEED) -> dict:
    return stats.bootstrap_ci(stat, units, N_RESAMPLES, seed=seed)


def holm_adjust(p_values: list[float | None]) -> list[float | None]:
    """Holm step-down over the whole family; a missing p (DEGENERATE) counts as 1 in the ranking."""
    m = len(p_values)
    ranked = sorted(range(m), key=lambda i: (1.0 if p_values[i] is None else p_values[i]))
    adjusted: list[float | None] = [None] * m
    running = 0.0
    for rank, i in enumerate(ranked):
        if p_values[i] is None:
            continue
        running = max(running, min(1.0, (m - rank) * p_values[i]))
        adjusted[i] = running
    return adjusted


def paired_comparison(stat, units_a, units_b, correct_a, correct_b, seed: int = SEED) -> dict:
    """Delta of ``stat`` with paired bootstrap CI, approximate randomization p and exact McNemar."""
    delta = stats.paired_bootstrap_delta(stat, units_a, units_b, N_RESAMPLES, seed=seed)
    randomization = stats.approximate_randomization(stat, units_a, units_b, N_RESAMPLES, seed=seed)
    a, b = np.asarray(correct_a, dtype=bool), np.asarray(correct_b, dtype=bool)
    mcnemar = stats.mcnemar_exact(int((a & ~b).sum()), int((~a & b).sum()))
    width = None if delta["ci_low"] is None else delta["ci_high"] - delta["ci_low"]
    return {"delta": delta, "randomization": randomization, "mcnemar": mcnemar, "ci_width": width}


def finite_or_none(value) -> float | None:
    return float(value) if value is not None and isfinite(value) else None
