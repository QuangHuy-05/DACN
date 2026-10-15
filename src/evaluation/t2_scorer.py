"""Scoring for the T2 baseline: gold derivation, per-row outcomes, cell metrics and paired tests.

Everything that reads gold columns (``LoaiAnhXa``, ``MaPhuongXaMoi``, ``KieuLai`` ...)
lives here, never in the lookup systems.  Rates always carry their denominator;
an empty slice is ``NOT_EVALUABLE_NO_SUPPORT`` rather than 0.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from statistics import mean, median
from typing import Sequence

import numpy as np

from src.data.administrative_mapping import province_key, unit_key
from src.evaluation import stats
from src.evaluation.leak_guard import admin_group_key
from src.evaluation.t2_lookup import (
    NEW_TO_OLD, OLD_TO_NEW, Candidate, Resolution, SingleVersionIndex, T2Table,
)

NO_SUPPORT = "NOT_EVALUABLE_NO_SUPPORT"
NOT_SUPPORTED = "NOT_SUPPORTED"
NO_UNIQUE_GOLD = "NOT_EVALUABLE_NO_UNIQUE_GOLD"
LOW_EVIDENCE = "NOT_EVALUABLE_LOW_EVIDENCE"
CI_SEED = 20261014
CI_RESAMPLES = 10_000
RELATION_LETTERS = ("A", "B", "C", "M")
MERGE_FORMS = ("Hợp nhất toàn bộ", "Tách — nhập chủ yếu", "Tách — một phần")


# ---------------------------------------------------------------------------
# Address text helpers (oracle segmentation)
# ---------------------------------------------------------------------------

def split_address(text: str, kind: str) -> dict:
    """Split on commas from the right: old = ward, district, province; new = ward, province.

    Extra commas inside the leading part (house number / street) do not shift
    the right-aligned administrative parts.  Missing parts become ''.
    """
    parts = [p.strip() for p in str(text).split(",")]
    take = 3 if kind == "old" else 2
    admin = parts[-take:] if len(parts) >= take else [""] * (take - len(parts)) + parts
    head = parts[:-take] if len(parts) > take else []
    if kind == "old":
        out = {"ward": admin[0], "district": admin[1], "province": admin[2]}
    else:
        out = {"ward": admin[0], "district": "", "province": admin[1]}
    out["head"] = head
    return out


_HOUSE_NUMBER = re.compile(r"^(?:số\s*)?\d+[a-zA-Z]?(?:[/\-]\d+[a-zA-Z]?)*$", re.I)


def house_and_street(head: Sequence[str]) -> tuple[str, str]:
    """(house number, street) from the non-administrative head parts.

    The first part is a house number only when it looks like one (digits with
    optional letter/slash groups); otherwise all parts belong to the street.
    """
    if not head:
        return "", ""
    if _HOUSE_NUMBER.match(head[0].strip()):
        return head[0].strip(), ", ".join(head[1:])
    return "", ", ".join(head)


def lookup_fields(parsed: dict) -> dict:
    return {"province": parsed["province"], "district": parsed["district"], "ward": parsed["ward"]}


# ---------------------------------------------------------------------------
# Gold
# ---------------------------------------------------------------------------

@dataclass
class PairGold:
    old: Candidate | None  # gold old unit resolved at N2 (identity independent of the query level)
    new: Candidate | None
    edge_exists: bool
    old_cluster: str
    new_cluster: str
    code_expected: str


def build_pair_gold(table: T2Table, row: dict) -> PairGold:
    """Resolve the observed pair on both sides with the strongest allowed normalisation (N2).

    The observed pair is the gold; the query level only changes how the *input*
    is matched, never how the gold is identified.
    """
    old, new = split_address(row["DiaChi_Cu"], "old"), split_address(row["DiaChi_Moi"], "new")
    old_edges, _ = table.match_old("N2", old["province"], old["district"], old["ward"])
    new_edges, _ = table.match_new("N2", new["province"], new["ward"])
    old_units = {e.old_entity_id for e in old_edges}
    new_units = {e.new_entity_id for e in new_edges}
    gold_old = _single(old_edges, "old") if len(old_units) == 1 else None
    gold_new = _single(new_edges, "new") if len(new_units) == 1 else None
    exists = bool(gold_old and gold_new and any(e.new_entity_id == gold_new.cid for e in gold_old.edges))
    old_cluster = "|".join(gold_old.key) if gold_old else "UNRESOLVED|" + "|".join(
        (province_key(old["province"]), unit_key(old["district"]), unit_key(old["ward"])))
    return PairGold(gold_old, gold_new, exists, old_cluster, row.get("MaPhuongXaMoi", ""),
                    row.get("MaPhuongXaMoi", ""))


def _single(edges, side: str) -> Candidate:
    from src.evaluation.t2_lookup import group_candidates

    return group_candidates(edges, side)[0]


def admin_cluster(row: dict) -> str:
    """Connected-component key used only for the sensitivity table (``leak_guard.admin_group_key``)."""
    old = split_address(row["DiaChi_Cu"], "old")
    return admin_group_key(old["province"], old["district"], old["ward"])


# ---------------------------------------------------------------------------
# Per-row outcome
# ---------------------------------------------------------------------------

def score_resolution(res: Resolution, gold_key: tuple | None, gold_code: str = "") -> dict:
    """Outcome flags of one resolution against the gold identity key.

    ``silent`` = answered, wrong, and no warning/abstain was produced.
    A missing gold identity can never be matched and counts as wrong.
    """
    answered = res.status == "ANSWER"
    correct = bool(answered and gold_key is not None and res.answer.key == gold_key)
    candidate_keys = {c.key for c in res.candidates}
    code_agrees = None
    if answered and correct and gold_code and res.answer.code:
        code_agrees = res.answer.code == gold_code
    return {
        "answered": answered,
        "abstain": not answered,
        "reason": res.reason,
        "no_match": res.reason == "NO_MATCH",
        "correct": correct,
        "silent": bool(answered and not correct and not res.warning),
        "n_candidates": len(res.candidates),
        "gold_in_candidates": bool(gold_key is not None and gold_key in candidate_keys),
        "code_agrees": code_agrees,
    }


# ---------------------------------------------------------------------------
# Cell metrics
# ---------------------------------------------------------------------------

def _ci(values: np.ndarray, clusters: Sequence[str], seed: int, n_resamples: int) -> dict:
    return stats.cluster_bootstrap_ci(stats.exact_match_rate, values, clusters, n_resamples, seed=seed)


def summarize_cell(records: Sequence[dict], with_ci: bool = True, seed: int = CI_SEED,
                   n_resamples: int = CI_RESAMPLES) -> dict:
    """Metrics of one (system, direction, condition, level, slice) cell.

    ``records`` need: correct, answered, abstain, no_match, silent, n_candidates,
    gold_in_candidates, cluster.  Accuracy counts abstention as wrong.
    """
    n = len(records)
    if n == 0:
        return {"n": 0, "status": NO_SUPPORT}
    correct = np.array([r["correct"] for r in records], dtype=float)
    silent = np.array([r["silent"] for r in records], dtype=float)
    answered = sum(1 for r in records if r["answered"])
    matched = [r["n_candidates"] for r in records if r["n_candidates"] > 0]
    clusters = [r["cluster"] for r in records]
    by_unit: dict[str, list[float]] = {}
    for r, c in zip(records, correct):
        by_unit.setdefault(r["cluster"], []).append(c)
    unit_sizes = {k: len(v) for k, v in by_unit.items()}
    largest_unit = max(unit_sizes, key=lambda k: unit_sizes[k])
    out = {
        "n": n,
        "status": "OK",
        "answered": answered,
        "correct": int(correct.sum()),
        "abstain": n - answered,
        "no_match": sum(1 for r in records if r["no_match"]),
        "ambiguous_abstain": sum(1 for r in records if r["reason"] == "AMBIGUOUS"),
        "accuracy": float(correct.mean()),
        "accepted_accuracy": (float(correct.sum() / answered) if answered else None),
        "coverage": answered / n,
        "abstain_rate": (n - answered) / n,
        "no_match_rate": sum(1 for r in records if r["no_match"]) / n,
        "candidate_recall": sum(1 for r in records if r["gold_in_candidates"]) / n,
        "n_matched": len(matched),
        "candidates_mean_matched": (mean(matched) if matched else None),
        "candidates_median_matched": (median(matched) if matched else None),
        "share_multi_candidate": sum(1 for r in records if r["n_candidates"] > 1) / n,
        "silent_errors": int(silent.sum()),
        "silent_error_rate": float(silent.mean()),
        "macro_accuracy": float(np.mean([np.mean(v) for v in by_unit.values()])),
        "n_units": len(by_unit),
        "largest_unit": largest_unit,
        "largest_unit_pairs": unit_sizes[largest_unit],
    }
    if with_ci:
        acc_ci = _ci(correct, clusters, seed, n_resamples)
        se_ci = _ci(silent, clusters, seed, n_resamples)
        out.update({
            "accuracy_ci_low": acc_ci["ci_low"], "accuracy_ci_high": acc_ci["ci_high"],
            "accuracy_ci_status": acc_ci["status"] if acc_ci["status"] != "OK" else "OK",
            "silent_ci_low": se_ci["ci_low"], "silent_ci_high": se_ci["ci_high"],
            "silent_ci_status": se_ci["status"] if se_ci["status"] != "OK" else "OK",
            "n_clusters": acc_ci.get("n_clusters", len(by_unit)),
            "ci_cluster_definition": "source unit of the evaluated direction",
            "ci_method": f"cluster bootstrap percentile B={n_resamples} seed={seed}",
        })
    return out


def unit_constant_ceiling(records: Sequence[dict], gold_keys: Sequence[tuple | None]) -> float | None:
    """Best accuracy of any rule that returns one fixed target per source unit.

    Per source unit take the most frequent gold target; this ceiling shows how
    much of an accuracy figure is decided by how Data 07 was sampled.
    """
    if not records:
        return None
    per_unit: dict[str, dict] = {}
    for r, g in zip(records, gold_keys):
        per_unit.setdefault(r["cluster"], {}).setdefault(g, 0)
        per_unit[r["cluster"]][g] += 1
    return sum(max(v.values()) for v in per_unit.values()) / len(records)


def slice_defs(records: Sequence[dict]):
    """(slice_type, slice_value, subset); A and C are present with zero support on Data 07."""
    yield "ALL", "ALL", list(records)
    for letter in RELATION_LETTERS:
        yield "LoaiAnhXa", letter, [r for r in records if r["loai"] == letter]
    values = list(MERGE_FORMS) + sorted({r["hinhthuc"] for r in records} - set(MERGE_FORMS))
    for value in values:
        yield "HinhThucSapNhap", value, [r for r in records if r["hinhthuc"] == value]


# ---------------------------------------------------------------------------
# Paired comparisons (E3 across directions, E2 across systems)
# ---------------------------------------------------------------------------

def paired_comparison(a: Sequence[bool], b: Sequence[bool], cluster_options: dict[str, Sequence[str]],
                      seed: int = CI_SEED, n_resamples: int = CI_RESAMPLES) -> dict:
    """McNemar exact and paired cluster bootstrap on ``accuracy(a) - accuracy(b)`` over the same pairs."""
    arr_a, arr_b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if len(arr_a) != len(arr_b):
        raise ValueError("paired inputs differ in length")
    n = len(arr_a)
    if n == 0:
        return {"n": 0, "status": NO_SUPPORT}
    only_a = int(((arr_a == 1) & (arr_b == 0)).sum())
    only_b = int(((arr_a == 0) & (arr_b == 1)).sum())
    out = {
        "n": n, "status": "OK",
        "accuracy_a": float(arr_a.mean()), "accuracy_b": float(arr_b.mean()),
        "delta": float(arr_a.mean() - arr_b.mean()),
        "a_right_b_wrong": only_a, "a_wrong_b_right": only_b,
        "both_right": int(((arr_a == 1) & (arr_b == 1)).sum()),
        "both_wrong": int(((arr_a == 0) & (arr_b == 0)).sum()),
        "mcnemar": stats.mcnemar_exact(only_a, only_b),
    }
    for name, ids in cluster_options.items():
        res = stats.paired_bootstrap_delta(stats.exact_match_rate, arr_a, arr_b, n_resamples,
                                           cluster_ids=list(ids), seed=seed)
        out[f"delta_ci_{name}"] = {k: res.get(k) for k in ("ci_low", "ci_high", "n_clusters", "status", "reason")}
    return out


# ---------------------------------------------------------------------------
# Situation D: the same ward name in both systems, different territory
# ---------------------------------------------------------------------------

class GraphView:
    """Adjacency by entity id for scope comparisons."""

    def __init__(self, table: T2Table) -> None:
        self.targets: dict[str, set[str]] = {}
        self.sources: dict[str, set[str]] = {}
        for edge in table.edges:
            self.targets.setdefault(edge.old_entity_id, set()).add(edge.new_entity_id)
            self.sources.setdefault(edge.new_entity_id, set()).add(edge.old_entity_id)

    def same_scope(self, old_id: str, new_id: str) -> bool:
        return self.targets.get(old_id) == {new_id} and self.sources.get(new_id) == {old_id}

    def edge(self, old_id: str, new_id: str) -> bool:
        return new_id in self.targets.get(old_id, ())


def homonym_label(graph: GraphView, index: SingleVersionIndex, direction: str,
                  gold_old: Candidate | None, gold_new: Candidate | None) -> str:
    """Situation-D label of an observed pair for one direction.

    The query ward name is looked up as a name in the target system (what a
    version-blind system does).  Labels: NO_HOMONYM; SAME_SCOPE; D_SCOPE_DIFFERS
    (homonym is the gold target but one unit has other neighbours);
    D_OTHER_TARGET_EDGE_EXISTS (homonym is a different unit still linked by an
    edge); D_DISJOINT (homonym shares no edge with the source: other territory).
    """
    if gold_old is None or gold_new is None:
        return "GOLD_UNRESOLVED"
    if direction == OLD_TO_NEW:
        found = index.homonyms(OLD_TO_NEW, gold_new.key[0], gold_old.key[2])
        gold_id = gold_new.cid
        linked = lambda h: graph.edge(gold_old.cid, h.cid)
        scope = lambda h: graph.same_scope(gold_old.cid, h.cid)
    else:
        found = index.homonyms(NEW_TO_OLD, gold_new.key[0], gold_new.key[1])
        gold_id = gold_old.cid
        linked = lambda h: graph.edge(h.cid, gold_new.cid)
        scope = lambda h: graph.same_scope(h.cid, gold_new.cid)
    if not found:
        return "NO_HOMONYM"
    if any(h.cid == gold_id for h in found):
        return "SAME_SCOPE" if scope(next(h for h in found if h.cid == gold_id)) else "D_SCOPE_DIFFERS"
    return "D_OTHER_TARGET_EDGE_EXISTS" if any(linked(h) for h in found) else "D_DISJOINT"


def homonym_census(table: T2Table, graph: GraphView, index: SingleVersionIndex) -> dict:
    """Over the whole gazetteer: old wards that share a name with a new ward of the same province."""
    counts = {"old_wards": 0, "old_wards_with_homonym": 0, "pairs": 0, "SAME_SCOPE": 0,
              "D_SCOPE_DIFFERS": 0, "D_EDGE_ABSENT": 0}
    for (npk, wkey), olds in index.old_wards.items():
        for old in olds:
            counts["old_wards"] += 1
            news = index.new_wards.get((npk, wkey), [])
            if not news:
                continue
            counts["old_wards_with_homonym"] += 1
            for new in news:
                counts["pairs"] += 1
                if not graph.edge(old.cid, new.cid):
                    counts["D_EDGE_ABSENT"] += 1
                elif graph.same_scope(old.cid, new.cid):
                    counts["SAME_SCOPE"] += 1
                else:
                    counts["D_SCOPE_DIFFERS"] += 1
    pairs = counts["pairs"]
    counts["share_d"] = ((counts["D_SCOPE_DIFFERS"] + counts["D_EDGE_ABSENT"]) / pairs) if pairs else None
    counts["label"] = "gazetteer-level census of name collisions (structural), not observed error"
    return counts


# ---------------------------------------------------------------------------
# Situation C gold (hybrid strings, Data 06)
# ---------------------------------------------------------------------------

def situation_c_gold(table: T2Table, row: dict) -> tuple[tuple | None, str]:
    """Gold new unit of a hybrid string, or ``None`` with an exclusion reason.

    ``KieuLai`` is read here (scoring side only): C1/C2 have a new ward, so the
    gold is that ward in the canonical new province; C3 has an old ward whose
    gold exists only if its full old key feeds exactly one new unit.
    """
    kind = row["KieuLai"].split("_")[0]
    province, district, ward = row["TinhThanh"], row["QuanHuyen"], row["PhuongXa"]
    if kind in ("C1", "C2"):
        edges, _ = table.match_new("N2", province, ward)
        units = {e.new_entity_id for e in edges}
        if len(units) != 1:
            return None, "NEW_WARD_NOT_FOUND"
        return edges[0].new_key, ""
    if kind == "C3":
        # Full old key as stated (province, district, ward) at N2, exactly as a lookup system would use it.
        # A row whose stated province is not the old province of the ward has no gold here (counted apart).
        edges, _ = table.match_old("N2", province, district, ward)
        units = {e.new_entity_id for e in edges}
        if len(units) == 0:
            return None, "NO_TARGET_FULL_KEY"
        if len(units) > 1:
            return None, "SEVERAL_TARGETS"
        return edges[0].new_key, ""
    return None, "UNKNOWN_KIEULAI"
