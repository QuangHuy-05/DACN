"""T1 (cu / moi / Lai) systems, features, metrics and DYN diagnostics for Group 1.

Only ``numpy`` and the standard library are imported at module level so the
file can be loaded from the main runtime and from the neural runtime.

Inference contract: every ``predict_*`` / ``*_features`` function receives raw
address strings (plus model spans for the pipeline variants).  Gold labels and
benchmark metadata are consumed only by the metric and diagnostic helpers.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from typing import Iterable, Sequence

import numpy as np

RULE_VERSION = "t1-pipeline-v1"
CLASSES = ("cu", "moi", "Lai")
ABSTAIN = "khong_ro"
ABSTAIN_INDEX = len(CLASSES)
UNKNOWN_SPAN_SYSTEM = "khong_xac_dinh"
ADMIN_LABELS = ("PhuongXa", "QuanHuyen", "TinhThanh")

NOT_EVALUABLE_SINGLE_CLASS = "NOT_EVALUABLE_SINGLE_CLASS"
NOT_EVALUABLE_NO_SUPPORT = "NOT_EVALUABLE_NO_SUPPORT"

LOCKED_HEUR_CONFIG = Path(
    "data/interim/modeling/sprint03/final_completion_20261005_v1/light_test_runs_v2/heur-jw/model_config.json"
)

L2_GRID = (0.01, 0.1, 1.0)
CLASSIFIER_SEED = 42
ALLOWED_INFERENCE_COLUMNS = frozenset({"key", "text"})


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Inference-side guard
# ---------------------------------------------------------------------------

def inference_texts(frame) -> list[str]:
    """Return the ``text`` column and refuse any frame that carries more than key/text.

    The guard is the anti-leak contract of this package: gold_system, KieuLai,
    source and every other metadata column must stay on the scoring side.
    """
    columns = set(getattr(frame, "columns", ()))
    extra = sorted(columns - ALLOWED_INFERENCE_COLUMNS)
    if extra:
        raise ValueError(f"inference input must only carry key/text; got extra columns {extra}")
    if "text" not in columns:
        raise ValueError("inference input needs a 'text' column")
    return [str(value) for value in frame["text"].tolist()]


# ---------------------------------------------------------------------------
# HEUR-JW (locked configuration) and the span -> system rule
# ---------------------------------------------------------------------------

def load_locked_heur(repo: Path):
    """Build HEUR-JW with the arguments frozen in the Sprint 3 light-test config."""
    from src.evaluation.adapters.heur_jw_followup import HeuristicJaroWinklerFollowup

    config_path = Path(repo) / LOCKED_HEUR_CONFIG
    if not config_path.exists():
        raise FileNotFoundError(config_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    kwargs = dict(config["adapter_kwargs"])
    kwargs["gazetteer_dir"] = str(Path(repo) / kwargs["gazetteer_dir"])
    return HeuristicJaroWinklerFollowup(**kwargs)


def combine_systems(span_systems: Iterable[str]) -> str:
    """Reference-system rule of HEUR-JW applied to administrative span systems.

    cu + moi -> Lai; exactly one system -> that system; nothing determined ->
    khong_ro.  Mirrors the last step of ``HeuristicJaroWinklerAdapter.parse_spans``.
    """
    systems = {s for s in span_systems if s in ("cu", "moi")}
    if systems == {"cu", "moi"}:
        return "Lai"
    if len(systems) == 1:
        return next(iter(systems))
    return ABSTAIN


def pipe_predict(resolver, text: str, spans: Sequence[dict]) -> tuple[str, list[dict]]:
    """T1-PIPE: administrative spans of a T0 model + HEUR-JW's own ``_resolve``.

    Spans are visited right to left so the province/district context is built
    exactly as in HEUR-JW.  The T0 label only selects which spans are looked
    up; the level and system come from the gazetteer resolution.
    """
    context: dict = {}
    detail = []
    admin = [s for s in spans if s.get("label") in ADMIN_LABELS]
    for span in sorted(admin, key=lambda s: (s["start"], s["end"]), reverse=True):
        surface = text[span["start"]:span["end"]]
        candidates, info = resolver._resolve(surface, context)
        system, level = UNKNOWN_SPAN_SYSTEM, None
        if candidates:
            level = candidates[0].level
            systems = {entity.system for entity in candidates}
            system = next(iter(systems)) if len(systems) == 1 else UNKNOWN_SPAN_SYSTEM
            if level in {"province", "district"}:
                context[level] = {resolver._core(entity.canonical_name) for entity in candidates}
        detail.append({"start": span["start"], "end": span["end"], "label": span["label"],
                       "resolved_level": level, "system": system, "decision": info.get("decision")})
    return combine_systems(item["system"] for item in detail), detail


def heur_predict(resolver, text: str) -> str:
    output = resolver.parse_spans(text)
    return ABSTAIN if output.abstain else output.predicted_system


# ---------------------------------------------------------------------------
# T1-FEAT features (text + gazetteer membership, no labels)
# ---------------------------------------------------------------------------

DISTRICT_KINDS = ("quận", "huyện", "thị xã")
TAIL_POSITIONS = (1, 2, 3)
GAZETTEER_LEVELS = ("province", "district", "ward")
SURFACE_PREFIX = "s:"
GAZETTEER_PREFIX = "g:"


def split_segments(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[,;\n]", text or "") if part.strip()]


def _membership(systems: set[str]) -> str:
    if systems == {"cu", "moi"}:
        return "both"
    if systems == {"cu"}:
        return "cu"
    if systems == {"moi"}:
        return "moi"
    return "none"


class FeatureExtractor:
    """Binary features from the text and from exact gazetteer membership.

    ``gazetteer`` is a loaded HEUR-JW adapter; only its name index, prefix
    rules and parent chain are used (exact core-name match, no fuzzy score).
    """

    def __init__(self, gazetteer) -> None:
        self.gaz = gazetteer

    def _entities(self, segment: str, level: str) -> list:
        core = self.gaz._core(segment)
        kind = self.gaz._unit_kind(segment)
        found = []
        if kind is None and core.isdigit():
            return found  # a bare number is a house number, not "Quận 12" / "Phường 3"
        for entity_id in sorted(self.gaz.forms[level].get(core, ())):
            entity = self.gaz.entities[entity_id]
            # A written unit type must agree with the gazetteer entry (Xã != Phường).
            if self.gaz._valid(entity) and (kind is None or kind == self.gaz._unit_kind(entity.canonical_name)):
                found.append(entity)
        return found

    def surface_features(self, text: str) -> dict[str, float]:
        segments = split_segments(text)
        features = {f"{SURFACE_PREFIX}bias_segments={min(len(segments), 6)}": 1.0}
        kinds = []
        for position in TAIL_POSITIONS:
            if len(segments) < position:
                features[f"{SURFACE_PREFIX}pos{position}_absent"] = 1.0
                kinds.append(None)
                continue
            kind = self.gaz._unit_kind(segments[-position])
            kinds.append(kind)
            features[f"{SURFACE_PREFIX}pos{position}_kind={kind or 'none'}"] = 1.0
        # District-level sign visible in the text itself.
        if any(self.gaz._unit_kind(segment) in DISTRICT_KINDS for segment in segments):
            features[f"{SURFACE_PREFIX}district_marker"] = 1.0
        if segments and segments[-1].isascii():
            features[f"{SURFACE_PREFIX}province_ascii"] = 1.0
        return features

    def gazetteer_features(self, text: str) -> dict[str, float]:
        segments = split_segments(text)
        features: dict[str, float] = {}
        tail = {p: segments[-p] for p in TAIL_POSITIONS if len(segments) >= p}
        for position, segment in tail.items():
            for level in GAZETTEER_LEVELS:
                systems = {entity.system for entity in self._entities(segment, level)}
                features[f"{GAZETTEER_PREFIX}pos{position}_{level}={_membership(systems)}"] = 1.0
        if 1 in tail:
            province_core = self.gaz._core(tail[1])
            for position in (2, 3):
                if position not in tail:
                    continue
                wards = [e for e in self._entities(tail[position], "ward")
                         if self.gaz._ancestor_core(e, "province") == province_core]
                features[f"{GAZETTEER_PREFIX}pos{position}_ward_in_province="
                         f"{_membership({e.system for e in wards})}"] = 1.0
                districts = [e for e in self._entities(tail[position], "district")
                             if self.gaz._ancestor_core(e, "province") == province_core]
                if self._entities(tail[position], "district"):
                    features[f"{GAZETTEER_PREFIX}pos{position}_district_in_province="
                             f"{'yes' if districts else 'no'}"] = 1.0
            if 2 in tail and 3 in tail:
                district_core = self.gaz._core(tail[2])
                old_wards = [e for e in self._entities(tail[3], "ward") if e.system == "cu"]
                if old_wards and self._entities(tail[2], "district"):
                    under = any(self.gaz._ancestor_core(e, "district") == district_core for e in old_wards)
                    features[f"{GAZETTEER_PREFIX}pos3_old_ward_under_pos2_district={'yes' if under else 'no'}"] = 1.0
        return features

    def features(self, text: str, use_gazetteer: bool = True) -> dict[str, float]:
        features = self.surface_features(text)
        if use_gazetteer:
            features.update(self.gazetteer_features(text))
        return features

    def has_district_sign(self, text: str) -> bool:
        """One-feature baseline: a district prefix, or a non-final segment that is an old district name."""
        segments = split_segments(text)
        if any(self.gaz._unit_kind(segment) in DISTRICT_KINDS for segment in segments):
            return True
        return any(self._entities(segment, "district") for segment in segments[:-1])


class Vectorizer:
    """Feature-name vocabulary fixed on the training set."""

    def __init__(self, feature_dicts: Sequence[dict[str, float]]) -> None:
        self.names = sorted({name for item in feature_dicts for name in item})
        self.index = {name: i for i, name in enumerate(self.names)}

    def transform(self, feature_dicts: Sequence[dict[str, float]]) -> np.ndarray:
        matrix = np.zeros((len(feature_dicts), len(self.names)), dtype=np.float64)
        for row, item in enumerate(feature_dicts):
            for name, value in item.items():
                column = self.index.get(name)
                if column is not None:  # unseen feature names are dropped
                    matrix[row, column] = value
        return matrix


# ---------------------------------------------------------------------------
# Linear softmax classifier (numpy)
# ---------------------------------------------------------------------------

class SoftmaxClassifier:
    """Multinomial logistic regression, full-batch gradient descent.

    Objective: mean cross-entropy + ``l2 / (2 n)`` * ||W||^2 (bias unpenalised).
    Weights start at zero, so the fit is deterministic; ``seed`` is recorded
    for the manifest only.
    """

    def __init__(self, l2: float, seed: int = CLASSIFIER_SEED, iterations: int = 3000,
                 learning_rate: float = 0.5, standardize: bool = False) -> None:
        self.l2, self.seed, self.iterations = float(l2), int(seed), int(iterations)
        self.learning_rate, self.standardize = float(learning_rate), bool(standardize)
        self.weights = None
        self.bias = None
        self.mean = None
        self.scale = None

    def _prepare(self, matrix: np.ndarray) -> np.ndarray:
        if not self.standardize:
            return matrix
        return (matrix - self.mean) / self.scale

    @staticmethod
    def _softmax(logits: np.ndarray) -> np.ndarray:
        shifted = logits - logits.max(axis=1, keepdims=True)
        exp = np.exp(shifted)
        return exp / exp.sum(axis=1, keepdims=True)

    def fit(self, matrix: np.ndarray, labels: Sequence[int]) -> "SoftmaxClassifier":
        x = np.asarray(matrix, dtype=np.float64)
        y = np.asarray(labels, dtype=np.int64)
        if len(x) == 0 or len(x) != len(y):
            raise ValueError("empty or misaligned training data")
        if self.standardize:
            self.mean = x.mean(axis=0)
            scale = x.std(axis=0)
            self.scale = np.where(scale > 0, scale, 1.0)
        x = self._prepare(x)
        n, d = x.shape
        onehot = np.zeros((n, len(CLASSES)))
        onehot[np.arange(n), y] = 1.0
        self.weights = np.zeros((d, len(CLASSES)))
        self.bias = np.zeros(len(CLASSES))
        for _ in range(self.iterations):
            error = (self._softmax(x @ self.weights + self.bias) - onehot) / n
            self.weights -= self.learning_rate * (x.T @ error + self.l2 / n * self.weights)
            self.bias -= self.learning_rate * error.sum(axis=0)
        return self

    def predict_proba(self, matrix: np.ndarray) -> np.ndarray:
        x = self._prepare(np.asarray(matrix, dtype=np.float64))
        return self._softmax(x @ self.weights + self.bias)

    def predict(self, matrix: np.ndarray) -> np.ndarray:
        return self.predict_proba(matrix).argmax(axis=1)


def select_l2(train_x, train_y, dev_x, dev_y, grid: Sequence[float] = L2_GRID, **kwargs):
    """Pick L2 on the synthetic dev split: macro-F1, then accuracy, then the larger L2."""
    trials = []
    best = None
    for l2 in grid:
        model = SoftmaxClassifier(l2, **kwargs).fit(train_x, train_y)
        units = to_units([CLASSES[i] for i in dev_y], [CLASSES[i] for i in model.predict(dev_x)])
        trial = {"l2": l2, "dev_macro_f1": macro_f1_stat(units), "dev_accuracy": accuracy_stat(units)}
        trials.append(trial)
        rank = (round(trial["dev_macro_f1"], 12), round(trial["dev_accuracy"], 12), l2)
        if best is None or rank > best[0]:
            best = (rank, model, l2)
    return best[1], best[2], trials


# ---------------------------------------------------------------------------
# Metrics: a unit is a 3 x 4 count matrix [gold class, predicted class or khong_ro]
# ---------------------------------------------------------------------------

def to_units(gold: Sequence[str], predicted: Sequence[str]) -> np.ndarray:
    """One one-hot confusion matrix per sample, shape ``(n, 3, 4)``.

    Count matrices are additive, so the same statistic functions work on
    samples and on per-cluster sums (cluster bootstrap resamples the sums).
    """
    if len(gold) != len(predicted):
        raise ValueError("gold and predictions differ in length")
    units = np.zeros((len(gold), len(CLASSES), len(CLASSES) + 1), dtype=np.int64)
    for row, (g, p) in enumerate(zip(gold, predicted)):
        if g not in CLASSES:
            raise ValueError(f"gold label {g!r} is not a T1 class")
        units[row, CLASSES.index(g), CLASSES.index(p) if p in CLASSES else ABSTAIN_INDEX] = 1
    return units


def aggregate_by_cluster(units: np.ndarray, cluster_ids: Sequence) -> np.ndarray:
    """Sum sample units inside each cluster -> ``(n_clusters, 3, 4)`` (sorted cluster order)."""
    units = np.asarray(units)
    if len(units) != len(cluster_ids):
        raise ValueError("cluster_ids and units differ in length")
    order = sorted(set(cluster_ids))
    position = {cluster: i for i, cluster in enumerate(order)}
    out = np.zeros((len(order),) + units.shape[1:], dtype=np.int64)
    for unit, cluster in zip(units, cluster_ids):
        out[position[cluster]] += unit
    return out


def _confusion(units: np.ndarray) -> np.ndarray:
    return np.asarray(units).reshape(-1, len(CLASSES), len(CLASSES) + 1).sum(axis=0)


def accuracy_stat(units: np.ndarray) -> float:
    """Overall accuracy; an abstention counts as wrong (Sprint 3 scorer convention)."""
    confusion = _confusion(units)
    total = confusion.sum()
    return float("nan") if total == 0 else float(np.trace(confusion[:, :len(CLASSES)]) / total)


def _class_counts(confusion: np.ndarray, index: int) -> tuple[int, int, int]:
    tp = int(confusion[index, index])
    return tp, int(confusion[:, index].sum() - tp), int(confusion[index].sum() - tp)


def _f1(tp: int, fp: int, fn: int) -> float:
    return 0.0 if 2 * tp + fp + fn == 0 else 2 * tp / (2 * tp + fp + fn)


def macro_f1_stat(units: np.ndarray) -> float:
    """Mean F1 over the three classes; a class without support or prediction scores 0."""
    confusion = _confusion(units)
    if confusion.sum() == 0:
        return float("nan")
    return float(np.mean([_f1(*_class_counts(confusion, i)) for i in range(len(CLASSES))]))


def class_f1_stat(label: str):
    index = CLASSES.index(label)

    def statistic(units: np.ndarray) -> float:
        tp, fp, fn = _class_counts(_confusion(units), index)
        # No gold support in a resample: undefined, not zero.
        return float("nan") if tp + fn == 0 else float(_f1(tp, fp, fn))

    return statistic


def class_recall_stat(label: str):
    index = CLASSES.index(label)

    def statistic(units: np.ndarray) -> float:
        tp, _, fn = _class_counts(_confusion(units), index)
        return float("nan") if tp + fn == 0 else float(tp / (tp + fn))

    return statistic


def t1_metrics(gold: Sequence[str], predicted: Sequence[str]) -> dict:
    """Accuracy, macro-F1, per-class P/R/F1 with support, coverage and abstention."""
    n = len(gold)
    if n == 0:
        return {"n": 0, "status": NOT_EVALUABLE_NO_SUPPORT}
    units = to_units(gold, predicted)
    confusion = _confusion(units)
    abstain = int(confusion[:, ABSTAIN_INDEX].sum())
    per_class = {}
    for index, label in enumerate(CLASSES):
        tp, fp, fn = _class_counts(confusion, index)
        support = tp + fn
        per_class[label] = {
            "support": support,
            "predicted": tp + fp,
            "tp": tp,
            "precision": (tp / (tp + fp)) if tp + fp else None,
            "recall": (tp / support) if support else None,
            "f1": _f1(tp, fp, fn) if support else None,
        }
    classes_with_support = sum(per_class[label]["support"] > 0 for label in CLASSES)
    columns = CLASSES + (ABSTAIN,)
    correct = int(np.trace(confusion[:, :len(CLASSES)]))
    return {
        "n": n,
        "status": "OK",
        "correct": correct,
        "accuracy": correct / n,
        "macro_f1": macro_f1_stat(units) if classes_with_support > 1 else NOT_EVALUABLE_SINGLE_CLASS,
        "classes_with_support": classes_with_support,
        "per_class": per_class,
        "coverage": (n - abstain) / n,
        "abstain_count": abstain,
        "abstain_rate": abstain / n,
        "accepted_accuracy": (correct / (n - abstain)) if n > abstain else None,
        "confusion": {f"{g}->{p}": int(confusion[i, j]) for i, g in enumerate(CLASSES)
                      for j, p in enumerate(columns) if confusion[i, j]},
    }


# ---------------------------------------------------------------------------
# Sprint 3 T1 mask and DYN diagnostics (frozen predictions, no model run)
# ---------------------------------------------------------------------------

def t1_mask(gold_rows: Sequence[dict], excluded_ids: Iterable[str]) -> dict[str, list[str]]:
    """Split sample ids into eligible / gold-null / declared-exclusion (scorer order)."""
    excluded = set(excluded_ids)
    out = {"eligible": [], "null": [], "excluded": []}
    for row in gold_rows:
        if row["sample_id"] in excluded:
            out["excluded"].append(row["sample_id"])
        elif row.get("address_system") in CLASSES:
            out["eligible"].append(row["sample_id"])
        else:
            out["null"].append(row["sample_id"])
    return out


def read_structure(prediction: dict) -> dict:
    """Posterior and decision fields of one frozen DYN prediction row."""
    structure = prediction.get("trace", {}).get("structure")
    if not structure or "posterior" not in structure:
        raise ValueError(f"{prediction.get('sample_id')}: prediction has no trace.structure.posterior")
    posterior = {label: float(structure["posterior"][label]) for label in CLASSES}
    argmax = max(CLASSES, key=lambda label: (posterior[label], -CLASSES.index(label)))
    return {
        "posterior": posterior,
        "argmax": argmax,
        "confidence": float(structure["confidence"]),
        "margin_observed": float(structure["margin_observed"]),
        "threshold": float(structure["threshold"]),
        "margin_required": float(structure["margin_required"]),
        "passes_threshold": float(structure["confidence"]) >= float(structure["threshold"]),
        "passes_margin": float(structure["margin_observed"]) >= float(structure["margin_required"]),
        "predicted_system": structure["predicted_system"],
        "t1_abstain": bool(structure["t1_abstain"]),
    }


def _quantiles(values: Sequence[float]) -> dict:
    if not values:
        return {"n": 0}
    array = np.asarray(values, dtype=float)
    q = np.percentile(array, [0, 25, 50, 75, 100])
    return {"n": int(len(array)), "min": float(q[0]), "p25": float(q[1]), "median": float(q[2]),
            "p75": float(q[3]), "max": float(q[4]), "mean": float(array.mean())}


def diagnose_dyn(gold_rows: Sequence[dict], predictions: Sequence[dict], excluded_ids: Iterable[str]) -> dict:
    """Separate "head cannot rank Lai first" from "threshold/margin rejects Lai"."""
    by_id = {row["sample_id"]: row for row in predictions}
    gold_by_id = {row["sample_id"]: row for row in gold_rows}
    mask = t1_mask(gold_rows, excluded_ids)
    rows = []
    for sample_id in mask["eligible"]:
        info = read_structure(by_id[sample_id])
        gold = gold_by_id[sample_id]["address_system"]
        rows.append({"sample_id": sample_id, "gold": gold, **info,
                     "posterior_gold": info["posterior"][gold]})
    golds = [r["gold"] for r in rows]
    thresholded = [r["predicted_system"] for r in rows]
    argmax = [r["argmax"] for r in rows]
    lai = [r for r in rows if r["gold"] == "Lai"]
    return {
        "mask": {key: len(value) for key, value in mask.items()},
        "observed_threshold_margin": {f"{t}/{m}": c for (t, m), c in sorted(Counter(
            (by_id[i]["trace"]["structure"]["threshold"], by_id[i]["trace"]["structure"]["margin_required"])
            for i in gold_by_id).items())},
        "with_threshold": t1_metrics(golds, thresholded),
        "argmax_only": t1_metrics(golds, argmax),
        "lai": {
            "support": len(lai),
            "argmax_is_lai": sum(r["argmax"] == "Lai" for r in lai),
            "argmax_is_lai_but_rejected": sum(r["argmax"] == "Lai" and r["t1_abstain"] for r in lai),
            "argmax_other_class": dict(Counter(r["argmax"] for r in lai if r["argmax"] != "Lai")),
            "rejected_by_threshold_or_margin": sum(r["t1_abstain"] for r in lai),
            "posterior_lai_on_lai": _quantiles([r["posterior"]["Lai"] for r in lai]),
        },
        "posterior_lai_by_gold": {label: _quantiles([r["posterior"]["Lai"] for r in rows if r["gold"] == label])
                                  for label in CLASSES},
        "posterior_gold_by_gold": {label: _quantiles([r["posterior_gold"] for r in rows if r["gold"] == label])
                                   for label in CLASSES},
        "rows": rows,
    }
