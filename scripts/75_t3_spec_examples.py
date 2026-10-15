"""Read-only measurements quoted by docs/sprints/sprint_04/20_t3_specification.md.

This script is NOT a T3 system.  It re-measures, from existing files only, the numbers
and the raw evidence (candidate sets, fan-out/fan-in, element keys, edge existence) that
the specification uses as examples.  Verdicts such as SAME_PLACE / UNDETERMINED are
applied by hand in the document; nothing here decides a pair.

Run from the repository root in the main runtime (``~/.venv_dacn``):

    python -m scripts.75_t3_spec_examples                    # JSON on stdout
    python -m scripts.75_t3_spec_examples --out <new.json>   # also write it (never overwrites)

Nothing is trained, downloaded or written into the data directories.  Gold columns of
Data 07 are read only to define the measurements (positives, groups, gold units).
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
GAZETTEER_DIR = Path("data/processed/gazetteer/s3_v4_nso_dual_snapshot_release2")
DATA07 = Path("data/processed/benchmark/07_bidirectional_pairs_verified.csv")
DATA07_COLUMNS = ("ID_Node", "DiaChi_Cu", "DiaChi_Moi", "LoaiAnhXa", "QuanHe", "HinhThucSapNhap",
                  "MaPhuongXaMoi", "Nguon")
SCRIPT_VERSION = "t3-spec-examples-v1"

# Facts quoted in the specification; a mismatch stops the run (reproduction gate).
EXPECTED = {
    "rows": 600,
    "loai": {"M": 356, "B": 244},
    "old_units_normalized": 49,
    "new_codes": 23,
    "admin_groups": 21,
    "head_equal_old_new": 600,
    "t2_cu_to_moi_main_correct": 579,
    "t2_cu_to_moi_main_silent": 21,
    "t2_moi_to_cu_main_correct": 46,
    "t2_moi_to_cu_main_silent": 554,
    "atomic_edges": 10597,
    "relations": {"B": 9432, "C": 132, "M": 1030, "A": 3},
}

# Rows quoted as examples in the document (CSV line = index + 2, header is line 1).
EXAMPLE_IDS = {
    "E1_n_to_1": "node:11675985421",
    "E2_m_to_n": "way:1301699235",
    "E3_silent_t2": "way:1370501880",
    "E4_hard_negative_a": "way:565803559",
    "E4_hard_negative_b": "node:11290270603",
}


def _setup():
    sys.path.insert(0, str(REPO))
    from src.evaluation import t2_lookup, t2_scorer
    from src.evaluation.leak_guard import normalize_for_overlap
    from src.data.administrative_mapping import province_key, unit_key

    return t2_lookup, t2_scorer, normalize_for_overlap, province_key, unit_key


class Context:
    """Gazetteer table, Data 07 rows and their parsed (oracle) address parts."""

    def __init__(self, repo: Path = REPO) -> None:
        self.L, self.S, self.normalize, self.province_key, self.unit_key = _setup()
        L, S = self.L, self.S
        for path in (repo / GAZETTEER_DIR, repo / DATA07):
            if not path.exists():
                raise FileNotFoundError(path)
        self.table = L.T2Table.load(repo / GAZETTEER_DIR)
        self.index = L.load_single_version_index(repo / GAZETTEER_DIR, self.table)
        self.rows = L.read_csv_rows(repo / DATA07, DATA07_COLUMNS)
        ids = [r["ID_Node"] for r in self.rows]
        if len(set(ids)) != len(ids):
            raise ValueError("ID_Node is not unique in Data 07")
        self.by_id = {r["ID_Node"]: i for i, r in enumerate(self.rows)}
        self.old = [S.split_address(r["DiaChi_Cu"], "old") for r in self.rows]
        self.new = [S.split_address(r["DiaChi_Moi"], "new") for r in self.rows]
        self.head_old = [S.house_and_street(p["head"]) for p in self.old]
        self.head_new = [S.house_and_street(p["head"]) for p in self.new]
        self.gold = [S.build_pair_gold(self.table, r) for r in self.rows]
        self.groups = [S.admin_cluster(r) for r in self.rows]
        self.edge_pairs = {(e.old_entity_id, e.new_entity_id) for e in self.table.edges}

    def element(self, head: tuple[str, str]) -> tuple[str, str]:
        """Normalised (house number, street key); the street drops a generic Đường/Phố prefix."""
        return self.normalize(head[0]), self.L.street_key(head[1])

    @staticmethod
    def elements_differ(a: tuple[str, str], b: tuple[str, str]) -> bool:
        """Safe 'different element' test: other street, or the same street with two present, unequal numbers.

        Same street with a missing house number on either side is NOT a negative (it may be one element).
        """
        if a[1] != b[1]:
            return True
        return bool(a[0] and b[0] and a[0] != b[0])


def default_main_outcomes(ctx: Context) -> dict:
    """T2 DEFAULT-MAIN / STRICT at N2 on the oracle fields, both directions (re-measure of report 09 section 3)."""
    L = ctx.L
    out = {}
    for system in (L.DEFAULT_MAIN, L.STRICT):
        for direction, parsed, gold_side in ((L.OLD_TO_NEW, ctx.old, "new"), (L.NEW_TO_OLD, ctx.new, "old")):
            correct = silent = abstain = 0
            for i in range(len(ctx.rows)):
                res = L.resolve_lookup(ctx.table, system, direction, "N2", ctx.S.lookup_fields(parsed[i]))
                gold = getattr(ctx.gold[i], gold_side)
                if res.status == "ABSTAIN":
                    abstain += 1
                elif res.answer is not None and gold is not None and res.answer.key == gold.key:
                    correct += 1
                else:
                    silent += 1
            out[f"{system}|{direction}"] = {"correct": correct, "silent_error": silent, "abstain": abstain,
                                           "n": len(ctx.rows)}
    return out


def reproduce_facts(ctx: Context) -> dict:
    L = ctx.L
    rows = ctx.rows
    house_present = sum(1 for h, _ in ctx.head_new if h)
    group_sizes = Counter(ctx.groups)
    ordered = group_sizes.most_common()
    outcomes = default_main_outcomes(ctx)
    main = L.DEFAULT_MAIN
    facts = {
        "rows": len(rows),
        "loai": dict(Counter(r["LoaiAnhXa"] for r in rows)),
        "old_units_normalized": len({g.old.cid for g in ctx.gold}),
        "new_codes": len({r["MaPhuongXaMoi"] for r in rows}),
        "admin_groups": len(group_sizes),
        "head_equal_old_new": sum(a == b for a, b in zip(ctx.head_old, ctx.head_new)),
        "house_number_present": house_present,
        "street_only_rows": len(rows) - house_present,
        "street_missing_rows": sum(1 for _, s in ctx.head_new if not s),
        "gold_edge_exists": sum(g.edge_exists for g in ctx.gold),
        "t2_cu_to_moi_main_correct": outcomes[f"{main}|{L.OLD_TO_NEW}"]["correct"],
        "t2_cu_to_moi_main_silent": outcomes[f"{main}|{L.OLD_TO_NEW}"]["silent_error"],
        "t2_moi_to_cu_main_correct": outcomes[f"{main}|{L.NEW_TO_OLD}"]["correct"],
        "t2_moi_to_cu_main_silent": outcomes[f"{main}|{L.NEW_TO_OLD}"]["silent_error"],
        "atomic_edges": len(ctx.table.edges),
        "relations": dict(Counter(ctx.table.relations.values())),
        "non_atomic_transitions": len(ctx.table.non_atomic),
        "t2_outcomes": outcomes,
        "group_sizes_top5": [[k, v] for k, v in ordered[:5]],
        "largest_group_share": ordered[0][1] / len(rows),
        "top3_group_share": sum(v for _, v in ordered[:3]) / len(rows),
        "rows_per_new_code_top3": Counter(r["MaPhuongXaMoi"] for r in rows).most_common(3),
    }
    mismatches = {k: {"expected": want, "observed": facts.get(k)} for k, want in EXPECTED.items()
                  if facts.get(k) != want}
    facts["reproduction_mismatches"] = mismatches
    return facts


def fan_counts(ctx: Context) -> dict:
    """Per-row fan-out (old unit -> new targets) and fan-in (new unit -> old sources) at N2."""
    fan_out, fan_in = Counter(), Counter()
    for i in range(len(ctx.rows)):
        old_c, _, _ = ctx.table.old_to_new_candidates("N2", ctx.old[i]["province"], ctx.old[i]["district"],
                                                      ctx.old[i]["ward"])
        new_c, _, _ = ctx.table.new_to_old_candidates("N2", ctx.new[i]["province"], ctx.new[i]["ward"])
        fan_out[len(old_c)] += 1
        fan_in[len(new_c)] += 1
    return {"fan_out_per_row": dict(sorted(fan_out.items())), "fan_in_per_row": dict(sorted(fan_in.items()))}


def positive_gold_counts(ctx: Context) -> dict:
    """Counts of the Data 07 positives by the gold-decision features of the specification (section 3).

    SAME: point-level and the old unit has one target (exclusive overlap).  SAME_CONDITIONAL: point-level and the
    old unit has >= 2 targets (shared overlap).  UNDETERMINED: no house number (street-only, not point-level).
    This counts rows by features; it does not run any decision rule on text.
    """
    counts = Counter()
    for i in range(len(ctx.rows)):
        old_c, _, _ = ctx.table.old_to_new_candidates("N2", ctx.old[i]["province"], ctx.old[i]["district"],
                                                      ctx.old[i]["ward"])
        if not ctx.head_new[i][0]:
            counts["UNDETERMINED"] += 1
        elif len(old_c) == 1:
            counts["SAME"] += 1
        else:
            counts["SAME_CONDITIONAL"] += 1
    by_loai = Counter((ctx.rows[i]["LoaiAnhXa"], bool(ctx.head_new[i][0])) for i in range(len(ctx.rows)))
    return {"counts": dict(sorted(counts.items())),
            "by_loai_and_house_present": {f"{k[0]}|house={k[1]}": v for k, v in sorted(by_loai.items())}}


def sha256_file(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def negative_estimates(ctx: Context) -> dict:
    """Constructible-negative capacities measured on Data 07 anchors and on the gazetteer."""
    rows = ctx.rows
    n = len(rows)
    codes = [r["MaPhuongXaMoi"] for r in rows]
    elems = [ctx.element(h) for h in ctx.head_new]
    by_code: dict[str, list[int]] = defaultdict(list)
    for i, code in enumerate(codes):
        by_code[code].append(i)

    # N-A: same new ward, a different element (a = old text of row i, b = new text of row j, i != j).
    pair_total = street_differs = same_street_numbers_differ = same_old_unit = excluded_unsafe_same_street = 0
    anchors, per_group = set(), Counter()
    for members in by_code.values():
        for i in members:
            for j in members:
                if i == j:
                    continue
                if ctx.elements_differ(elems[i], elems[j]):
                    pair_total += 1
                    anchors.add(i)
                    per_group[ctx.groups[i]] += 1
                    if elems[i][1] != elems[j][1]:
                        street_differs += 1
                    else:
                        same_street_numbers_differ += 1
                    if ctx.gold[i].old.cid == ctx.gold[j].old.cid:
                        same_old_unit += 1
                elif elems[i][1] == elems[j][1]:
                    excluded_unsafe_same_street += 1
    top_group = per_group.most_common(1)[0] if per_group else ("", 0)
    cap_k2 = 0
    for i in range(n):
        candidates = sum(1 for j in by_code[codes[i]] if j != i and ctx.elements_differ(elems[i], elems[j]))
        cap_k2 += min(2, candidates)

    # N-B: territory swap.  b keeps the element text of row i but takes a new ward that no edge of a's old unit reaches.
    n_new_units = ctx.table.unique_new_units()
    swap_candidates = []
    for i in range(n):
        reachable = {e.new_entity_id for e in ctx.gold[i].old.edges}
        swap_candidates.append(n_new_units - len(reachable))

    # Excluded type: another valid target of the same old unit (text-identical to a valid positive).
    other_target = []
    for i in range(n):
        reachable = {e.new_entity_id for e in ctx.gold[i].old.edges}
        other_target.append(len(reachable) - 1)

    # N-B2: homonym swap across old provinces (same old ward name, another old province).
    ward_to_units: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for (_, ward_key), cands in ctx.index.old_wards.items():
        for cand in cands:
            ward_to_units[ward_key].add((cand.key[0], cand.key[1]))
    homonym_rows, homonym_units, homonym_swaps = 0, set(), 0
    for i in range(n):
        province_k = ctx.province_key(ctx.old[i]["province"])
        ward_k = ctx.unit_key(ctx.old[i]["ward"])
        others = {u for u in ward_to_units.get(ward_k, set()) if u[0] != province_k}
        if others:
            homonym_rows += 1
            homonym_units.add((province_k, ctx.unit_key(ctx.old[i]["district"]), ward_k))
            homonym_swaps += len(others)
    new_name_provinces: dict[str, set[str]] = defaultdict(set)
    for (province_k, ward_k) in ctx.index.new_wards:
        new_name_provinces[ward_k].add(province_k)
    new_homonym_rows = sum(
        1 for i in range(n)
        if new_name_provinces.get(ctx.gold[i].new.key[1], set()) - {ctx.gold[i].new.key[0]}
    )

    # N-C: same ward name inside one new province, old unit vs new unit (situation D, region level).
    d_pairs = d_linked = 0
    for key, olds in ctx.index.old_wards.items():
        for cand_old in olds:
            for cand_new in ctx.index.new_wards.get(key, []):
                d_pairs += 1
                d_linked += (cand_old.cid, cand_new.cid) in ctx.edge_pairs
    old_name_provinces = Counter()
    for ward_k, units in ward_to_units.items():
        old_name_provinces[len({u[0] for u in units}) >= 2] += 1

    group_sizes = Counter(ctx.groups)
    return {
        "N_A_same_new_ward_other_element": {
            "ordered_pairs": pair_total,
            "street_differs": street_differs,
            "same_street_numbers_differ": same_street_numbers_differ,
            "same_old_unit": same_old_unit,
            "different_old_unit": pair_total - same_old_unit,
            "excluded_same_street_missing_number": excluded_unsafe_same_street,
            "anchor_rows_with_a_negative": len(anchors),
            "groups_with_pairs": len(per_group),
            "largest_group": {"key": top_group[0], "pairs": top_group[1],
                              "share": (top_group[1] / pair_total) if pair_total else None},
            "capacity_at_most_2_per_anchor": cap_k2,
        },
        "N_B_territory_swap": {
            "new_units_in_gazetteer": n_new_units,
            "candidates_per_anchor_min": min(swap_candidates),
            "candidates_per_anchor_max": max(swap_candidates),
            "capacity_at_most_2_per_anchor": 2 * n,
        },
        "N_B2_homonym_old_ward_other_province": {
            "anchor_rows": homonym_rows,
            "anchor_old_units": len(homonym_units),
            "swap_candidates": homonym_swaps,
            "rows_with_new_ward_name_in_other_province": new_homonym_rows,
        },
        "N_C_same_province_homonym_region_level": {
            "old_new_same_name_pairs": d_pairs,
            "linked_by_edge": d_linked,
            "no_edge": d_pairs - d_linked,
            "data07_anchor_rows_with_no_edge_homonym": None,  # filled by run()
        },
        "excluded_other_valid_target": {
            "text_identical_swaps": sum(other_target),
            "rows_with_fan_out_ge_2": sum(1 for v in other_target if v >= 1),
        },
        "gazetteer_ward_names": {
            "old_names_in_ge2_old_provinces": old_name_provinces[True],
            "old_names_total": sum(old_name_provinces.values()),
            "new_names_in_ge2_new_provinces": sum(1 for v in new_name_provinces.values() if len(v) >= 2),
            "new_names_total": len(new_name_provinces),
        },
        "undetermined_capacity": {
            "natural_street_only_rows": sum(1 for h, _ in ctx.head_new if not h),
            "drop_house_number_twins": sum(1 for h, _ in ctx.head_new if h),
            "ward_level_twins": n,
        },
        "groups": {"count": len(group_sizes), "sizes_desc": sorted(group_sizes.values(), reverse=True)},
    }


def data07_homonym_anchor_without_edge(ctx: Context) -> int:
    """Data 07 rows whose old ward name has a same-province new homonym that is NOT a target of the old unit."""
    count = 0
    for i in range(len(ctx.rows)):
        old_key = ctx.gold[i].old.key
        new_province = ctx.table.old_to_new_province.get(old_key[0])
        targets = {e.new_entity_id for e in ctx.gold[i].old.edges}
        homonyms = ctx.index.new_wards.get((new_province, old_key[2]), [])
        if any(h.cid not in targets for h in homonyms):
            count += 1
    return count


def example_evidence(ctx: Context, row_id: str) -> dict:
    """Raw evidence for one Data 07 row (no verdict)."""
    L = ctx.L
    i = ctx.by_id[row_id]
    row = ctx.rows[i]
    f_old, f_new = ctx.S.lookup_fields(ctx.old[i]), ctx.S.lookup_fields(ctx.new[i])
    to_new = L.resolve_lookup(ctx.table, L.DEFAULT_MAIN, L.OLD_TO_NEW, "N2", f_old)
    to_old = L.resolve_lookup(ctx.table, L.DEFAULT_MAIN, L.NEW_TO_OLD, "N2", f_new)
    strict_new = L.resolve_lookup(ctx.table, L.STRICT, L.OLD_TO_NEW, "N2", f_old)
    gold = ctx.gold[i]
    return {
        "id": row_id,
        "csv_line": i + 2,
        "DiaChi_Cu": row["DiaChi_Cu"],
        "DiaChi_Moi": row["DiaChi_Moi"],
        "LoaiAnhXa": row["LoaiAnhXa"],
        "QuanHe": row["QuanHe"],
        "HinhThucSapNhap": row["HinhThucSapNhap"],
        "MaPhuongXaMoi": row["MaPhuongXaMoi"],
        "element_old": list(ctx.element(ctx.head_old[i])),
        "element_new": list(ctx.element(ctx.head_new[i])),
        "gold_old_unit": gold.old.display(),
        "gold_new_unit": gold.new.display(),
        "edge_exists": gold.edge_exists,
        "admin_group": ctx.groups[i],
        "cu_to_moi_candidates": [c.display() for c in to_new.candidates],
        "cu_to_moi_default_main_pick": to_new.answer.display() if to_new.answer else None,
        "cu_to_moi_default_main_correct": bool(to_new.answer and to_new.answer.key == gold.new.key),
        "cu_to_moi_strict": strict_new.reason if strict_new.status == "ABSTAIN" else "ANSWER",
        "moi_to_cu_candidate_count": len(to_old.candidates),
        "moi_to_cu_default_main_pick": to_old.answer.display() if to_old.answer else None,
        "moi_to_cu_default_main_correct": bool(to_old.answer and to_old.answer.key == gold.old.key),
    }


def homonym_example(ctx: Context) -> dict | None:
    """The one Data 07 row whose new ward name also exists as a new ward in another province."""
    for i in range(len(ctx.rows)):
        key = ctx.gold[i].new.key
        others = [(pk, wk) for (pk, wk) in ctx.index.new_wards if wk == key[1] and pk != key[0]]
        if others:
            evidence = example_evidence(ctx, ctx.rows[i]["ID_Node"])
            evidence["homonym_new_wards"] = [
                c.display() for pk, wk in others for c in ctx.index.new_wards[(pk, wk)]]
            old_edges = {e.new_entity_id for e in ctx.gold[i].old.edges}
            evidence["homonym_is_edge_target_of_old_unit"] = any(
                c.cid in old_edges for pk, wk in others for c in ctx.index.new_wards[(pk, wk)])
            return evidence
    return None


def run(repo: Path = REPO) -> dict:
    ctx = Context(repo)
    facts = reproduce_facts(ctx)
    estimates = negative_estimates(ctx)
    estimates["N_C_same_province_homonym_region_level"]["data07_anchor_rows_with_no_edge_homonym"] = (
        data07_homonym_anchor_without_edge(ctx))
    return {
        "script_version": SCRIPT_VERSION,
        "inputs": {"gazetteer": str(GAZETTEER_DIR), "data07": str(DATA07),
                   "gazetteer_manifest_sha256": sha256_file(repo / GAZETTEER_DIR / "manifest.json"),
                   "data07_sha256": sha256_file(repo / DATA07)},
        "facts": facts,
        "fan_counts": fan_counts(ctx),
        "positive_gold_decision_counts": positive_gold_counts(ctx),
        "negative_estimates": estimates,
        "examples": {name: example_evidence(ctx, rid) for name, rid in EXAMPLE_IDS.items()},
        "homonym_example": homonym_example(ctx),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=None, help="optional JSON path; refused if it already exists")
    args = parser.parse_args(argv)
    out = None
    if args.out is not None:
        out = args.out if args.out.is_absolute() else REPO / args.out
        if out.exists():
            print(f"refusing to overwrite {out}", file=sys.stderr)
            return 3
    result = run()
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to a legacy code page
        sys.stdout.reconfigure(encoding="utf-8")
    print(text)
    return 2 if result["facts"]["reproduction_mismatches"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
