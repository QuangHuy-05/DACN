"""WP3a: bootstrap CIs and paired tests on frozen Sprint 3 predictions (no model is run).

    python -m scripts.69_bootstrap_frozen_results [--repro-only]

Output directory is versioned; an existing directory is never overwritten.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from src.evaluation import frozen_reliability as fr
from src.evaluation.dev_runner import load_predictions
from src.evaluation.schema import SPAN11_LABELS

OUT_DIR = fr.ROOT / "data/processed/evaluation/sprint04/reliability_20261014_v1"
T0_PAIRS = (
    ("PHOBERT-CRF", "PROPOSED-DYN"),
    ("PROPOSED-DYN", "PROPOSED-NO-CONSTRAINT"),
    ("PHOBERT-CRF", "CRF-INDEP"),
    ("PHOBERT-CRF", "HEUR-JW"),
    ("CRF-INDEP", "HEUR-JW"),
)
T1_PAIR = ("HEUR-JW", "PROPOSED-DYN")
SOURCE_FILES = ("src/evaluation/frozen_reliability.py", "src/evaluation/stats.py",
                "src/evaluation/span_scorer.py", "scripts/69_bootstrap_frozen_results.py")


def fmt_ci(result: dict) -> dict:
    return {"estimate": result.get("estimate"), "ci_low": result.get("ci_low"), "ci_high": result.get("ci_high"),
            "status": result.get("status"), "reason": result.get("reason"),
            "n_nonfinite_resamples": result.get("n_nonfinite_resamples")}


def load_system(name: str, path: Path, golds, excluded) -> dict:
    predictions = load_predictions(path)
    units = fr.build_units(predictions, golds, excluded)
    metrics = fr.scorer_metrics(predictions, golds, excluded)
    units["scorer_agrees"] = fr.check_units_against_scorer(units, metrics)
    if not all(units["scorer_agrees"].values()):
        raise ValueError(f"{name}: per-sample sums differ from the scorer: {units['scorer_agrees']}")
    units["metrics"] = metrics
    return units


def reproduction_rows(systems: dict[str, dict]) -> tuple[list[dict], bool]:
    rows, all_ok = [], True
    for name, data in systems.items():
        micro = data["metrics"]["t0_exact_span"]["micro"]
        got = (micro["precision"], micro["recall"], micro["f1"])
        want = fr.PUBLISHED_T0[name]
        ok = tuple(got) == tuple(want)
        t1 = data["metrics"]["t1_address_system"]
        row = {"system": name, "t0_P": got[0], "t0_R": got[1], "t0_F1": got[2],
               "published_P": want[0], "published_R": want[1], "published_F1": want[2], "t0_match": ok,
               "t1_eligible": t1["total_evaluated"], "t1_null_excluded": t1["gold_null_excluded"],
               "t1_declared_excluded": t1["declared_exception_excluded"]}
        if name in fr.T1_NOT_IMPLEMENTED:
            if not data["all_predicted_khong_ro"]:
                raise ValueError(f"{name}: expected no T1 head but found a predicted system")
            row.update(t1_accuracy="NOT_IMPLEMENTED", t1_macro_f1="NOT_IMPLEMENTED", published_t1="NOT_IMPLEMENTED",
                       t1_match=True,
                       t1_note=f"scorer returns {t1['overall_accuracy']}/{t1['macro_f1_all_3_classes']} because every sample is khong_ro; not a result")
        else:
            got1 = (t1["overall_accuracy"], t1["macro_f1_all_3_classes"])
            want1 = fr.PUBLISHED_T1[name]
            row.update(t1_accuracy=got1[0], t1_macro_f1=got1[1], published_t1=list(want1), t1_match=got1 == want1,
                       t1_note="")
        ok &= row["t1_match"]
        all_ok &= ok
        rows.append(row)
    mask = next(iter(systems.values()))["metrics"]["t1_address_system"]
    mask_ok = (mask["total_evaluated"], mask["gold_null_excluded"], mask["declared_exception_excluded"]) == (64, 20, 16)
    return rows, all_ok and mask_ok


def ci_tables(systems: dict[str, dict], cluster_ids: list[str] | None, source_ids: list[str] | None) -> dict:
    out = {"t0_micro": [], "t0_labels": [], "t0_exact": [], "t1": [], "t1_missing_class": {}}
    for name, data in systems.items():
        for metric, stat in (("precision", fr.precision_stat), ("recall", fr.recall_stat), ("f1", fr.f1_stat)):
            out["t0_micro"].append({"system": name, "metric": metric, "n_samples": len(data["totals"]),
                                    **fmt_ci(fr.bootstrap(stat, data["totals"]))})
        for i, label in enumerate(SPAN11_LABELS):
            counts = data["by_label"][:, i, :]
            support = int(counts[:, 0].sum() + counts[:, 2].sum())
            flag = fr.support_flag(support)
            if support == 0:
                row = {"estimate": None, "ci_low": None, "ci_high": None, "status": flag, "reason": None,
                       "n_nonfinite_resamples": None}
            else:
                row = fmt_ci(fr.bootstrap(fr.f1_stat, counts))
            out["t0_labels"].append({"system": name, "label": label, "gold_support": support, "support_flag": flag, **row})
        out["t0_exact"].append({"system": name, "n_samples": len(data["exact"]), "n_exact": int(data["exact"].sum()),
                                **fmt_ci(fr.bootstrap(lambda u: float(np.mean(u)), data["exact"].astype(float)))})
        t1 = data["t1"]
        if name in fr.T1_NOT_IMPLEMENTED:
            for metric in ("accuracy", "macro_f1", "lai_f1", "coverage"):
                out["t1"].append({"system": name, "metric": metric, "n_eligible": len(t1), "lai_support": None,
                                  "estimate": None, "ci_low": None, "ci_high": None, "status": "NOT_IMPLEMENTED",
                                  "reason": None, "n_nonfinite_resamples": None})
            continue
        lai_support = int((t1[:, 0] == 2).sum())
        macro = fr.MacroF1()
        specs = (("accuracy", fr.t1_accuracy_stat), ("macro_f1", macro), ("lai_f1", fr.lai_f1_stat),
                 ("coverage", fr.t1_coverage_stat))
        for metric, stat in specs:
            row = fmt_ci(fr.bootstrap(stat, t1))
            if metric == "lai_f1":
                row["status"] = row["status"] if fr.support_flag(lai_support) == "OK" else f"{row['status']}|{fr.support_flag(lai_support)}"
            out["t1"].append({"system": name, "metric": metric, "n_eligible": len(t1), "lai_support": lai_support, **row})
        out["t1_missing_class"][name] = {"share_of_calls": macro.missing_share, "calls": macro.calls}
    return out


def comparison_rows(systems: dict[str, dict]) -> list[dict]:
    rows = []
    for a, b in T0_PAIRS:
        da, db = systems[a], systems[b]
        result = fr.paired_comparison(fr.f1_stat, da["totals"], db["totals"], da["exact"], db["exact"])
        sa, sb = da["totals"].sum(axis=0), db["totals"].sum(axis=0)
        rows.append(_comparison_row("T0_micro_F1", a, b, len(da["totals"]), result,
                                    {"tp_fp_fn_a": sa.tolist(), "tp_fp_fn_b": sb.tolist(),
                                     "samples_differing_totals": int((da["totals"] != db["totals"]).any(axis=1).sum()),
                                     "samples_differing_exact": int((da["exact"] != db["exact"]).sum())}))
    a, b = T1_PAIR
    ta, tb = systems[a]["t1"], systems[b]["t1"]
    if not np.array_equal(ta[:, 0], tb[:, 0]):
        raise ValueError("T1 gold differs between systems")
    result = fr.paired_comparison(fr.t1_accuracy_stat, ta, tb, ta[:, 0] == ta[:, 1], tb[:, 0] == tb[:, 1])
    rows.append(_comparison_row("T1_accuracy", a, b, len(ta), result,
                                {"samples_differing_correct": int(((ta[:, 0] == ta[:, 1]) != (tb[:, 0] == tb[:, 1])).sum())}))
    secondary = fr.paired_comparison(fr.MacroF1(), ta, tb, ta[:, 0] == ta[:, 1], tb[:, 0] == tb[:, 1])
    rows.append(_comparison_row("T1_macro_F1_secondary", a, b, len(ta), secondary, {}))
    # Holm family = the six primary comparisons (five T0 pairs, one T1 pair); the T1 macro-F1 row is secondary.
    primary = [r for r in rows if not r["metric"].endswith("secondary")]
    for key in ("p_randomization", "p_mcnemar"):
        for row, adj in zip(primary, fr.holm_adjust([r[key] for r in primary])):
            row[key.replace("p_", "p_holm_")] = adj
    for row in rows:
        row["holm_family_size"] = len(primary) if row in primary else None
    return rows


def _comparison_row(metric, a, b, n, result, extra) -> dict:
    d, r, m = result["delta"], result["randomization"], result["mcnemar"]
    return {"metric": metric, "system_a": a, "system_b": b, "n_samples": n,
            "delta": d.get("estimate"), "ci_low": d.get("ci_low"), "ci_high": d.get("ci_high"),
            "ci_width": result["ci_width"], "prop_delta_le_0": d.get("prop_delta_le_0"),
            "delta_status": d.get("status"), "delta_reason": d.get("reason"),
            "p_randomization": r.get("p_value"), "randomization_status": r.get("status"),
            "mcnemar_b_a_right_b_wrong": m["b"], "mcnemar_c_a_wrong_b_right": m["c"],
            "p_mcnemar": m["p_value"], "mcnemar_status": m["status"], "mcnemar_reason": m["reason"],
            "p_holm_randomization": None, "p_holm_mcnemar": None, **extra}


def source_tables(systems: dict[str, dict], golds: list[dict]) -> dict:
    source_of = fr.load_source_datasets()
    sources = np.array([source_of[g["sample_id"]] for g in golds])
    groups = [g["source_group"] for g in golds]
    slices = []
    for name, data in systems.items():
        for source in sorted(set(sources)):
            mask = sources == source
            counts = data["totals"][mask]
            slices.append({"system": name, "source_dataset": source, "n_samples": int(mask.sum()),
                           "gold_spans": int(counts[:, 0].sum() + counts[:, 2].sum()),
                           **fmt_ci(fr.bootstrap(fr.f1_stat, counts))})
    clusters = []
    for name, data in systems.items():
        by_source = fr.stats.cluster_bootstrap_ci(fr.f1_stat, data["totals"], list(sources), fr.N_RESAMPLES, seed=fr.SEED)
        by_group = fr.stats.cluster_bootstrap_ci(fr.f1_stat, data["totals"], groups, fr.N_RESAMPLES, seed=fr.SEED)
        plain = fr.bootstrap(fr.f1_stat, data["totals"])
        clusters.append({"system": name, "cluster": "source_dataset", "n_clusters": by_source.get("n_clusters"),
                         **fmt_ci(by_source)})
        clusters.append({"system": name, "cluster": "source_group", "n_clusters": by_group.get("n_clusters"),
                         **fmt_ci(by_group)})
        clusters.append({"system": name, "cluster": "sample", "n_clusters": len(data["totals"]), **fmt_ci(plain)})
    return {"slices": slices, "clusters": clusters, "groups_unique": len(set(groups)) == len(groups)}


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    names = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)


def run_split(split: str, paths: dict[str, Path]) -> tuple[dict, list[dict], list[dict], dict]:
    golds, excluded = fr.load_gold(split)
    systems = {name: load_system(name, path, golds, excluded) for name, path in paths.items()}
    return systems, golds, excluded


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repro-only", action="store_true", help="only print the reproduction table")
    args = parser.parse_args()

    paths = fr.test_prediction_paths()
    hashes = fr.verify_frozen_hashes(paths)  # stops before any statistic if a hash differs
    systems, golds, excluded = run_split("test", paths)
    repro, repro_ok = reproduction_rows(systems)
    print(json.dumps(repro, ensure_ascii=False, indent=1))
    print("REPRODUCTION_OK" if repro_ok else "REPRODUCTION_MISMATCH")
    if args.repro_only:
        return 0 if repro_ok else 2
    if not repro_ok:
        print("Published scores not reproduced; stopping before any CI.", file=sys.stderr)
        return 2
    if OUT_DIR.exists():
        raise FileExistsError(f"{OUT_DIR} exists; refusing to overwrite (create a _v2 directory)")
    OUT_DIR.mkdir(parents=True)
    (OUT_DIR / "tables").mkdir()

    # Single manifest: the plan is declared before any statistic is computed, outputs are filled in at the end.
    manifest = {
        "version": "s4-wp3a-reliability-v1", "created_at": datetime.now(timezone.utc).isoformat(),
        "seed": fr.SEED, "n_resamples": fr.N_RESAMPLES, "alpha": 0.05, "systems": list(fr.SYSTEMS),
        "t0_pairs": [list(p) for p in T0_PAIRS], "t1_pair": list(T1_PAIR),
        "holm_family": "5 T0 pairs + 1 T1 pair (6); missing p counts as 1 in the ranking",
        "inputs": {"test_predictions": hashes,
                   "gold_test_sha256": fr.sha256_file(fr.CORPUS_DIR / "test_benchmark_t0.jsonl"),
                   "corpus_manifest_sha256": fr.sha256_file(fr.CORPUS_DIR / "manifest.json"),
                   "identity_registry_sha256": fr.sha256_file(fr.CORPUS_DIR / "identity_registry.jsonl")},
        "code_sha256": {f: fr.sha256_file(fr.ROOT / f) for f in SOURCE_FILES},
        "rows_in": {"test_samples": len(golds), "t1_eligible": 64},
        "label": "POST_HOC_UNCERTAINTY_ON_OBSERVED_TEST",
    }
    (OUT_DIR / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    result = {"reproduction": repro}
    result["ci"] = ci_tables(systems, None, None)
    result["comparisons"] = comparison_rows(systems)
    result["by_source"] = source_tables(systems, golds)
    gold_t1_ids = next(iter(systems.values()))["t1_ids"]
    result["t1_eligible_ids"] = gold_t1_ids

    # Tier 2: dev (selection set), only systems whose selected dev run is found by hash.
    dev_locations = fr.locate_dev_predictions()
    dev_paths = {n: i["path"] for n, i in dev_locations.items() if i["path"] is not None}
    dev = {"label": "SELECTION_SET", "locations": {
        n: {"status": i["status"], "selected_dev_run": i["selected_dev_run"], "expected_sha256": i["expected_sha256"],
            "path": str(i["path"].relative_to(fr.ROOT)) if i["path"] else None} for n, i in dev_locations.items()}}
    dev_systems, dev_golds, dev_excluded = run_split("dev", dev_paths)
    dev["n_samples"] = len(dev_golds)
    dev["t1_eligible"] = next(iter(dev_systems.values()))["metrics"]["t1_address_system"]["total_evaluated"]
    dev["scorer"] = {n: {"t0_micro": d["metrics"]["t0_exact_span"]["micro"],
                         "t1": {k: d["metrics"]["t1_address_system"][k] for k in ("overall_accuracy", "macro_f1_all_3_classes", "total_evaluated")}}
                     for n, d in dev_systems.items()}
    dev["ci"] = ci_tables(dev_systems, None, None)
    # Constrained DYN has no dev run: PHOBERT-CRF is compared with the unconstrained decoder instead, and the
    # DYN on/off pair is NOT_EVALUABLE on dev.
    dev_pairs = [p for p in T0_PAIRS if p[0] in dev_systems and p[1] in dev_systems]
    dev_pairs.insert(0, ("PHOBERT-CRF", "PROPOSED-NO-CONSTRAINT"))
    dev["comparisons"] = comparison_rows_dev(dev_systems, dev_pairs)
    dev["not_evaluable"] = {"PROPOSED-DYN dev (constrained)": "NOT_FOUND_ONLY_NO_CONSTRAINT_DEV_RUN_EXISTS",
                            "DYN on vs off (dev)": "NOT_EVALUABLE_NO_CONSTRAINED_DEV_RUN"}
    result["dev"] = dev
    result["track_5_fields"] = {"status": "NOT_RUN", "label": "DEVELOPMENT_TRACK"}

    (OUT_DIR / "metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
    write_csv(OUT_DIR / "tables/reproduction.csv", repro)
    write_csv(OUT_DIR / "tables/test_t0_micro_ci.csv", result["ci"]["t0_micro"])
    write_csv(OUT_DIR / "tables/test_t0_label_ci.csv", result["ci"]["t0_labels"])
    write_csv(OUT_DIR / "tables/test_t0_exact_match_ci.csv", result["ci"]["t0_exact"])
    write_csv(OUT_DIR / "tables/test_t1_ci.csv", result["ci"]["t1"])
    write_csv(OUT_DIR / "tables/test_paired_comparisons.csv", result["comparisons"])
    write_csv(OUT_DIR / "tables/test_by_source_dataset.csv", result["by_source"]["slices"])
    write_csv(OUT_DIR / "tables/test_cluster_sensitivity.csv", result["by_source"]["clusters"])
    write_csv(OUT_DIR / "tables/dev_t0_micro_ci.csv", dev["ci"]["t0_micro"])
    write_csv(OUT_DIR / "tables/dev_t0_label_ci.csv", dev["ci"]["t0_labels"])
    write_csv(OUT_DIR / "tables/dev_t0_exact_match_ci.csv", dev["ci"]["t0_exact"])
    write_csv(OUT_DIR / "tables/dev_t1_ci.csv", dev["ci"]["t1"])
    write_csv(OUT_DIR / "tables/dev_paired_comparisons.csv", dev["comparisons"])

    manifest["output_sha256"] = {str(p.relative_to(OUT_DIR)): fr.sha256_file(p)
                                 for p in sorted(OUT_DIR.rglob("*")) if p.is_file() and p.name != "run_manifest.json"}
    manifest["rows_out"] = {"test_ci_rows": len(result["ci"]["t0_micro"]) + len(result["ci"]["t0_labels"]) + len(result["ci"]["t1"]),
                            "comparisons": len(result["comparisons"])}
    (OUT_DIR / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"written {OUT_DIR}")
    return 0


def comparison_rows_dev(systems: dict[str, dict], pairs) -> list[dict]:
    """Same paired tests on dev; family size is the number of dev pairs available (no T1 pair unless both found)."""
    rows = []
    for a, b in pairs:
        da, db = systems[a], systems[b]
        rows.append(_comparison_row("T0_micro_F1", a, b, len(da["totals"]),
                                    fr.paired_comparison(fr.f1_stat, da["totals"], db["totals"], da["exact"], db["exact"]),
                                    {"samples_differing_exact": int((da["exact"] != db["exact"]).sum())}))
    t1_pair = (T1_PAIR[0], "PROPOSED-NO-CONSTRAINT")  # unconstrained dev run stands in for DYN's T1 head
    if all(s in systems for s in t1_pair):
        ta, tb = systems[t1_pair[0]]["t1"], systems[t1_pair[1]]["t1"]
        rows.append(_comparison_row("T1_accuracy", *t1_pair, len(ta),
                                    fr.paired_comparison(fr.t1_accuracy_stat, ta, tb, ta[:, 0] == ta[:, 1], tb[:, 0] == tb[:, 1]), {}))
    for key in ("p_randomization", "p_mcnemar"):
        for row, adj in zip(rows, fr.holm_adjust([r[key] for r in rows])):
            row[key.replace("p_", "p_holm_")] = adj
    for row in rows:
        row["holm_family_size"] = len(rows)
    return rows


def _json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(type(value))


if __name__ == "__main__":
    raise SystemExit(main())
