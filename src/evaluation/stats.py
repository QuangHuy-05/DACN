"""Uncertainty and paired-comparison statistics for frozen predictions.

Only ``numpy`` and the standard library are used.  Every stochastic function
requires an explicit keyword ``seed``.

``units`` is an array whose first axis indexes samples (or clusters' members).
For span tasks each row should hold per-sample counts such as ``(tp, fp, fn)``
so that ``statistic_fn`` recomputes micro-F1 from the *summed* counts of every
resample; averaging per-sample F1 would answer a different question.

Degenerate inputs never raise silently and never fabricate an interval: the
result has ``None`` for the missing numbers, a ``status`` and a ``reason``.
"""

from __future__ import annotations

from math import comb, isfinite
from typing import Callable, Sequence

import numpy as np

DEFAULT_RESAMPLES = 10_000
STATUS_OK = "OK"
STATUS_NO_SUPPORT = "NOT_EVALUABLE_NO_SUPPORT"
STATUS_DEGENERATE = "DEGENERATE"

StatisticFn = Callable[[np.ndarray], float]


def micro_f1_from_counts(counts: np.ndarray) -> float:
    """Micro-F1 from rows ``(tp, fp, fn)``; NaN when nothing is predicted or gold."""
    summed = np.asarray(counts, dtype=float).sum(axis=0)
    tp, fp, fn = summed[0], summed[1], summed[2]
    denominator = 2 * tp + fp + fn
    return float("nan") if denominator == 0 else float(2 * tp / denominator)


def exact_match_rate(units: np.ndarray) -> float:
    """Mean of a 0/1 column (or vector); NaN for an empty input."""
    values = np.asarray(units, dtype=float)
    return float("nan") if values.size == 0 else float(values.mean())


def _as_units(units: Sequence | np.ndarray) -> np.ndarray:
    array = np.asarray(units)
    if array.ndim == 0:
        raise ValueError("units must have at least one axis")
    return array


def _check_n(n_resamples: int, alpha: float) -> None:
    if n_resamples < 1:
        raise ValueError("n_resamples must be >= 1")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be in (0, 1)")


def _all_rows_identical(units: np.ndarray) -> bool:
    flat = units.reshape(len(units), -1)
    return bool((flat == flat[0]).all())


def _null_result(method: str, status: str, reason: str, n_units: int, seed: int, **extra) -> dict:
    result = {
        "method": method,
        "status": status,
        "reason": reason,
        "estimate": None,
        "ci_low": None,
        "ci_high": None,
        "n_units": n_units,
        "seed": seed,
    }
    result.update(extra)
    return result


def _percentile_ci(values: np.ndarray, alpha: float) -> tuple[float, float]:
    low, high = np.percentile(values, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(low), float(high)


def _finite(values: list[float]) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    return array[np.isfinite(array)]


def _summarise(
    method: str, estimate: float, draws: list[float], alpha: float, n_units: int,
    seed: int, n_resamples: int, **extra,
) -> dict:
    finite = _finite(draws)
    base = {
        "method": method,
        "alpha": alpha,
        "n_resamples": n_resamples,
        "n_units": n_units,
        "seed": seed,
        "n_nonfinite_resamples": int(len(draws) - len(finite)),
    }
    base.update(extra)
    if not isfinite(estimate) or len(finite) == 0:
        return {**base, "status": STATUS_NO_SUPPORT, "reason": "STATISTIC_NOT_FINITE",
                "estimate": None, "ci_low": None, "ci_high": None}
    low, high = _percentile_ci(finite, alpha)
    return {**base, "status": STATUS_OK, "reason": None,
            "estimate": float(estimate), "ci_low": low, "ci_high": high}


def bootstrap_ci(
    statistic_fn: StatisticFn,
    units: Sequence | np.ndarray,
    n_resamples: int = DEFAULT_RESAMPLES,
    alpha: float = 0.05,
    *,
    seed: int,
) -> dict:
    """Percentile bootstrap over samples (rows of ``units``)."""
    _check_n(n_resamples, alpha)
    data = _as_units(units)
    n = len(data)
    method = "bootstrap_percentile"
    if n == 0:
        return _null_result(method, STATUS_NO_SUPPORT, "NO_UNITS", 0, seed)
    if _all_rows_identical(data):
        return _null_result(method, STATUS_DEGENERATE, "ALL_UNITS_IDENTICAL", n, seed,
                            estimate=_to_float(statistic_fn(data)))
    rng = np.random.default_rng(seed)
    draws = [float(statistic_fn(data[rng.integers(0, n, size=n)])) for _ in range(n_resamples)]
    return _summarise(method, float(statistic_fn(data)), draws, alpha, n, seed, n_resamples)


def _to_float(value: float) -> float | None:
    value = float(value)
    return value if isfinite(value) else None


def _cluster_members(cluster_ids: Sequence, n: int) -> list[np.ndarray]:
    ids = np.asarray(cluster_ids)
    if len(ids) != n:
        raise ValueError(f"cluster_ids has {len(ids)} entries but there are {n} units")
    _, inverse = np.unique(ids, return_inverse=True)
    order = np.argsort(inverse, kind="stable")
    boundaries = np.flatnonzero(np.diff(inverse[order])) + 1
    return np.split(order, boundaries)


def cluster_bootstrap_ci(
    statistic_fn: StatisticFn,
    units: Sequence | np.ndarray,
    cluster_ids: Sequence,
    n_resamples: int = DEFAULT_RESAMPLES,
    alpha: float = 0.05,
    *,
    seed: int,
) -> dict:
    """Percentile bootstrap that resamples whole clusters with replacement."""
    _check_n(n_resamples, alpha)
    data = _as_units(units)
    n = len(data)
    method = "cluster_bootstrap_percentile"
    if n == 0:
        return _null_result(method, STATUS_NO_SUPPORT, "NO_UNITS", 0, seed, n_clusters=0)
    members = _cluster_members(cluster_ids, n)
    k = len(members)
    if k == 1:
        return _null_result(method, STATUS_DEGENERATE, "SINGLE_CLUSTER", n, seed, n_clusters=1,
                            estimate=_to_float(statistic_fn(data)))
    if _all_rows_identical(data):
        return _null_result(method, STATUS_DEGENERATE, "ALL_UNITS_IDENTICAL", n, seed, n_clusters=k,
                            estimate=_to_float(statistic_fn(data)))
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(n_resamples):
        chosen = rng.integers(0, k, size=k)
        draws.append(float(statistic_fn(data[np.concatenate([members[c] for c in chosen])])))
    return _summarise(method, float(statistic_fn(data)), draws, alpha, n, seed, n_resamples,
                      n_clusters=k)


def _paired_inputs(units_a, units_b) -> tuple[np.ndarray, np.ndarray]:
    a, b = _as_units(units_a), _as_units(units_b)
    if len(a) != len(b):
        raise ValueError(f"paired inputs differ in length: {len(a)} vs {len(b)}")
    return a, b


def paired_bootstrap_delta(
    statistic_fn: StatisticFn,
    units_a: Sequence | np.ndarray,
    units_b: Sequence | np.ndarray,
    n_resamples: int = DEFAULT_RESAMPLES,
    alpha: float = 0.05,
    cluster_ids: Sequence | None = None,
    *,
    seed: int,
) -> dict:
    """Bootstrap ``statistic(A) - statistic(B)`` using the same indices for both systems.

    ``cluster_ids`` switches to resampling whole clusters (same clusters for A and B).
    ``prop_delta_le_0`` is the share of finite resamples with delta <= 0.
    """
    _check_n(n_resamples, alpha)
    a, b = _paired_inputs(units_a, units_b)
    n = len(a)
    method = "paired_bootstrap_delta" + ("_cluster" if cluster_ids is not None else "")
    if n == 0:
        return _null_result(method, STATUS_NO_SUPPORT, "NO_UNITS", 0, seed, prop_delta_le_0=None)
    members = None
    if cluster_ids is not None:
        members = _cluster_members(cluster_ids, n)
        if len(members) == 1:
            return _null_result(method, STATUS_DEGENERATE, "SINGLE_CLUSTER", n, seed, n_clusters=1,
                                prop_delta_le_0=None)
    if _all_rows_identical(a) and _all_rows_identical(b):
        return _null_result(method, STATUS_DEGENERATE, "ALL_UNITS_IDENTICAL", n, seed,
                            prop_delta_le_0=None)
    observed = float(statistic_fn(a)) - float(statistic_fn(b))
    rng = np.random.default_rng(seed)
    deltas = []
    for _ in range(n_resamples):
        if members is None:
            idx = rng.integers(0, n, size=n)
        else:
            chosen = rng.integers(0, len(members), size=len(members))
            idx = np.concatenate([members[c] for c in chosen])
        deltas.append(float(statistic_fn(a[idx])) - float(statistic_fn(b[idx])))
    result = _summarise(method, observed, deltas, alpha, n, seed, n_resamples,
                        **({"n_clusters": len(members)} if members is not None else {}))
    finite = _finite(deltas)
    result["prop_delta_le_0"] = float((finite <= 0).mean()) if len(finite) else None
    return result


def approximate_randomization(
    statistic_fn: StatisticFn,
    units_a: Sequence | np.ndarray,
    units_b: Sequence | np.ndarray,
    n_permutations: int = DEFAULT_RESAMPLES,
    *,
    seed: int,
) -> dict:
    """Two-sided paired approximate randomization test on ``statistic(A) - statistic(B)``.

    Each permutation swaps the two systems' rows independently with probability
    1/2.  ``p = (1 + #{|delta*| >= |delta|}) / (n_permutations + 1)``.
    """
    if n_permutations < 1:
        raise ValueError("n_permutations must be >= 1")
    a, b = _paired_inputs(units_a, units_b)
    n = len(a)
    method = "approximate_randomization_two_sided"
    if n == 0:
        return _null_result(method, STATUS_NO_SUPPORT, "NO_UNITS", 0, seed, p_value=None,
                            observed_delta=None, n_permutations=n_permutations)
    flat_a, flat_b = a.reshape(n, -1), b.reshape(n, -1)
    if (flat_a == flat_b).all():
        return _null_result(method, STATUS_DEGENERATE, "ALL_PAIRS_IDENTICAL", n, seed, p_value=None,
                            observed_delta=0.0, n_permutations=n_permutations)
    observed = float(statistic_fn(a)) - float(statistic_fn(b))
    if not isfinite(observed):
        return _null_result(method, STATUS_NO_SUPPORT, "STATISTIC_NOT_FINITE", n, seed,
                            p_value=None, observed_delta=None, n_permutations=n_permutations)
    rng = np.random.default_rng(seed)
    extreme = 0
    for _ in range(n_permutations):
        swap = rng.random(n) < 0.5
        swap_shape = swap.reshape((n,) + (1,) * (a.ndim - 1))
        delta = float(statistic_fn(np.where(swap_shape, b, a))) - float(statistic_fn(np.where(swap_shape, a, b)))
        if abs(delta) >= abs(observed) - 1e-12:
            extreme += 1
    return {
        "method": method, "status": STATUS_OK, "reason": None, "observed_delta": observed,
        "p_value": (1 + extreme) / (n_permutations + 1), "n_permutations": n_permutations,
        "n_units": n, "seed": seed,
    }


def mcnemar_exact(b: int, c: int) -> dict:
    """Exact two-sided McNemar test (binomial, p=0.5) on discordant counts.

    ``b``: A right / B wrong; ``c``: A wrong / B right.  ``p = min(1, 2*P(X <= min(b,c)))``
    with integer arithmetic so large counts do not underflow.  No discordant
    pair means the test carries no information: ``p_value`` is ``None``.
    """
    if int(b) != b or int(c) != c or b < 0 or c < 0:
        raise ValueError("b and c must be non-negative integers")
    b, c = int(b), int(c)
    n = b + c
    base = {"method": "mcnemar_exact_two_sided", "b": b, "c": c, "n_discordant": n}
    if n == 0:
        return {**base, "status": STATUS_DEGENERATE, "reason": "NO_DISCORDANT_PAIRS", "p_value": None}
    tail = sum(comb(n, i) for i in range(min(b, c) + 1))
    p_value = min(1.0, 2 * tail / 2 ** n)
    return {**base, "status": STATUS_OK, "reason": None, "p_value": p_value}
