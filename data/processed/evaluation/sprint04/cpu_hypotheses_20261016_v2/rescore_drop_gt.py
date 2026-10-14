"""Re-score stored WP4 H2 predictions (no training, no inference): `gt` drop vs full, absent GT fields, AUG-FULL overlap.

Run from the repo root in ~/.venv_dacn:  python data/processed/evaluation/sprint04/cpu_hypotheses_20261016_v2/rescore_drop_gt.py
Reads data/interim/modeling/sprint04/cpu_hypotheses_20261016_v1/h2 (predictions and training files); writes next to this script.
"""
import csv
import hashlib
import importlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
S = importlib.import_module("scripts.71_run_cpu_hypothesis_experiments")
from src.evaluation import frozen_reliability as fr  # noqa: E402
from src.evaluation import leak_guard as lg  # noqa: E402

OUT = Path(__file__).resolve().parent
H2 = ROOT / "data/interim/modeling/sprint04/cpu_hypotheses_20261016_v1/h2"
norm = lg.normalize_for_overlap


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ctx = S.build_context(Path(tmp) / "i", Path(tmp) / "p")
        design = S.build_h2_design(ctx)
    held, full = ctx["h2"]["heldout"], ctx["h2"]["eval_full"]
    held_clusters = [r["group_key"] for r in held]
    gt_fields = [(r["sample_id"], f) for r in held for f in S.SURFACE_FIELDS if r["gt"][f].strip()]
    absent = [(i, f) for i, f in gt_fields if not next(r for r in held if r["sample_id"] == i)["surface"][f].strip()]
    summary = {"gt_fields_total": len(gt_fields), "gt_fields_absent_from_text": len(absent),
               "absent_share": len(absent) / len(gt_fields), "max_recall_under_gt": 1 - len(absent) / len(gt_fields)}
    rows = []
    names = ["BASE"] + [f"{m}_N{n}_s{s}" for s in S.SUBSET_SEEDS for n in S.AUG_SIZES for m in ("AUG-MISSING", "AUG-FULL")]
    held_gt_f1 = {}
    for name in names:
        pred = H2 / "predictions" / name
        gt_units = S.five_field_units(pred / "heldout.jsonl", held, "gt")
        surf_units = S.five_field_units(pred / "heldout.jsonl", held, "surface")
        full_units = S.five_field_units(pred / "eval_full.jsonl", full, "surface")
        full_f1 = fr.f1_stat(full_units)
        for truth, units in (("gt", gt_units), ("surface", surf_units)):
            d = S.unpaired_delta(fr.f1_stat, units, full_units, held_clusters)
            rows.append({"model": name, "truth": truth, "heldout_f1": S.fnum(fr.f1_stat(units)), "full_f1": S.fnum(full_f1),
                         "delta": S.fnum(d["estimate"]), "ci_low": S.fnum(d["ci_low"]), "ci_high": S.fnum(d["ci_high"]),
                         "relative_drop": S.fnum(-d["estimate"] / full_f1), "n_heldout": len(held), "n_full": len(full)})
        held_gt_f1[name] = (gt_units, surf_units)
    S.csv_write(OUT / "h2_drop_vs_full_gt.csv", rows)
    # Surface per KieuThieu for BASE (same numbers as v1) plus the full-address reference.
    import numpy as np
    kieu = np.array([r["KieuThieu"] for r in held])
    base_surface = held_gt_f1["BASE"][1]
    per_kieu = {k: S.fnum(fr.f1_stat(base_surface[kieu == k])) for k in sorted(set(kieu))}
    # Address-level overlap between each AUG-FULL training set and the heldout rows (GT 4-tuple without district).
    def key4(d):
        return tuple(norm(d[f]) for f in ("SoNha", "TenDuong", "PhuongXa", "TinhThanh"))
    held_keys = {key4(r["gt"]) for r in held}
    pool_by_id = {r["sample_id"]: r for r in ctx["h2"]["train_pool"] + ctx["h2"]["eval_full"]}
    overlap_rows, shifts = [], []
    for seed in S.SUBSET_SEEDS:
        for n in S.AUG_SIZES:
            tag = f"N{n}_s{seed}"
            full_ids = [r["sample_id"] for r in S.read_jsonl(H2 / "train" / f"AUG-FULL_{tag}.jsonl") if r["sample_id"].startswith("d0")]
            miss_ids = [r["sample_id"] for r in S.read_jsonl(H2 / "train" / f"AUG-MISSING_{tag}.jsonl") if r["sample_id"].startswith("d04")]
            full_keys = {key4(pool_by_id[i]["surface"]) for i in full_ids}
            miss_keys = {key4(next(r for r in ctx["h2"]["d04"] if r["sample_id"] == i)["gt"]) for i in miss_ids}
            overlap_full = sum(key4(r["gt"]) in full_keys for r in held)
            overlap_miss = sum(key4(r["gt"]) in miss_keys for r in held)
            keep = np.array([key4(r["gt"]) not in full_keys for r in held])
            for truth_i, truth in enumerate(("gt", "surface")):
                a = held_gt_f1[f"AUG-MISSING_{tag}"][truth_i]
                b = held_gt_f1[f"AUG-FULL_{tag}"][truth_i]
                clusters = [c for c, k in zip(held_clusters, keep) if k]
                before = S.paired_delta(fr.f1_stat, a, b, cluster_ids=held_clusters)
                after = S.paired_delta(fr.f1_stat, a[keep], b[keep], cluster_ids=clusters)
                shifts.append(abs(after["estimate"] - before["estimate"]))
                overlap_rows.append({"N": n, "subset_seed": seed, "truth": truth, "heldout_rows_in_aug_full": overlap_full,
                                     "heldout_rows_in_aug_missing": overlap_miss, "rows_kept_after_removal": int(keep.sum()),
                                     "delta_before": S.fnum(before["estimate"]), "delta_after": S.fnum(after["estimate"]),
                                     "ci_after_low": S.fnum(after["ci_low"]), "ci_after_high": S.fnum(after["ci_high"]),
                                     "ci_after_contains_0": bool(after["ci_low"] <= 0 <= after["ci_high"])})
    S.csv_write(OUT / "h2_aug_full_overlap_check.csv", overlap_rows)
    summary.update(base_surface_by_kieu=per_kieu, max_abs_delta_shift=max(shifts), all_12_ci_contain_0=all(r["ci_after_contains_0"] for r in overlap_rows),
                   eval_full_rows_in_heldout=sum(key4(r["surface"]) in held_keys for r in full))
    (OUT / "rescore_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    manifest = {"status": "COMPLETE", "note": "re-scoring of stored v1 predictions; no training or inference",
                "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "source_v1_manifest_sha256": hashlib.sha256((ROOT / "data/processed/evaluation/sprint04/cpu_hypotheses_20261016_v1/run_manifest.json").read_bytes()).hexdigest(),
                "outputs_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.glob("*")) if p.suffix in (".csv", ".json") and p.name != "run_manifest.json"}}
    (OUT / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
