"""WP5: ablation of the QuanHuyen decoding constraint by re-decoding saved emissions (CPU, no model inference).

Two stages, two runtimes (see AGENTS.md / Khối chung):
  extract-crf  neural runtime  : read CRF start/end/transitions tensors from checkpoints (no adapter, no inference)
  run          main runtime    : gate -> re-decode -> score (gold is read only after every gate passed)

  data/interim/modeling/sprint03/runtime_neural_d_v1/bin/python -m scripts.72_run_constraint_ablation extract-crf
  python -m scripts.72_run_constraint_ablation run
Output directories carry the run name; an existing directory is never overwritten (use --run-name ..._v2).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_RUN = "constraint_ablation_20261017_v1"
INTERIM_BASE = ROOT / "data/interim/modeling/sprint04"
PROCESSED_BASE = ROOT / "data/processed/evaluation/sprint04"
FINAL_DIR_REL = "data/interim/modeling/sprint03/final_completion_20261005_v1"
SEEDS = (42, 1337, 2025)
WP3B_STD = {"PHOBERT-CRF": 0.0030, "PROPOSED-DYN": 0.0111}  # quoted from docs/sprints/sprint_04/11 (b2), cross-checked below

LABEL_TEST = "SPRINT3_TEST_OBSERVED_POSTHOC"
LABEL_SEED = "LOCAL_CPU_RETRAINED__SPRINT3_TEST_OBSERVED_POSTHOC"
LABEL_5F = "DEVELOPMENT_TRACK"
LABEL_DEV = "SELECTION_SET"


def interim_dir(run_name: str) -> Path:
    return INTERIM_BASE / run_name


def extract_crf(run_name: str) -> None:
    from src.evaluation import constraint_ablation as ca

    target = interim_dir(run_name) / "crf_params"
    if target.exists():
        raise FileExistsError(f"{target} exists; use --run-name <name>_v2")
    target.mkdir(parents=True)
    summary = {}
    for name, (rel, expected_prefix) in ca.CHECKPOINTS.items():
        params = ca.extract_crf_params(ROOT / rel)
        if expected_prefix and not params["checkpoint_sha256"].startswith(expected_prefix):
            raise ValueError(f"{name}: checkpoint SHA-256 {params['checkpoint_sha256']} does not start with {expected_prefix}")
        params["checkpoint_path"] = rel
        (target / f"{name}.json").write_text(json.dumps(params, ensure_ascii=False), encoding="utf-8")
        summary[name] = {"checkpoint_path": rel, "checkpoint_sha256": params["checkpoint_sha256"],
                         "keys": params["state_dict_keys"], "bio_masks_match_labels_py": params["bio_masks_match_labels_py"],
                         "torch_load_mode": params["torch_load_mode"]}
        print(name, params["checkpoint_sha256"][:12], params["bio_masks_match_labels_py"], flush=True)
    (target / "extraction_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


# ----------------------------------------------------------------------- helpers
def sha256_file(path: Path) -> str:
    from src.evaluation.constraint_ablation import sha256_file as digest

    return digest(path)


def jsonable(value):
    import numpy as np

    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(type(value))


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=jsonable) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: ("" if row.get(c) is None else row.get(c)) for c in columns})


def rel(path: Path) -> str:
    return str(Path(path).resolve().relative_to(ROOT)).replace("\\", "/")


# ------------------------------------------------------------------ dataset specs
def build_specs(ca, fr) -> list[dict]:
    kaggle = ROOT / ca.KAGGLE_REL
    seed_root = ROOT / ca.SEED_REL
    dev = fr.locate_dev_predictions()
    dev_dyn_dir = Path(dev["PROPOSED-NO-CONSTRAINT"]["path"]).parent
    constrained_ref = dev_dyn_dir.parent / dev_dyn_dir.name.replace("proposed_no_constraint_v1", "proposed_dyn_v1")
    specs = [{"name": "test_kaggle", "label": LABEL_TEST, "kind": "span", "split": "test", "checkpoints": ("kaggle_dyn", "kaggle_pcrf"),
              "files": {"dyn_on": kaggle / "dyn_test/predictions.jsonl", "dyn_off": kaggle / "dyn_off_test/predictions.jsonl",
                        "pcrf": kaggle / "pcrf_test/predictions.jsonl"},
              "heur": ROOT / FINAL_DIR_REL / "light_test_runs_v2/heur-jw/predictions.jsonl"}]
    for seed in SEEDS:
        specs.append({"name": f"test_seed{seed}", "label": LABEL_SEED, "kind": "span", "split": "test",
                      "checkpoints": (f"seed{seed}_dyn", f"seed{seed}_pcrf"),
                      "files": {"dyn_on": seed_root / f"dyn_seed{seed}/test_dyn/predictions.jsonl",
                                "dyn_off": seed_root / f"dyn_seed{seed}/test_dyn_off/predictions.jsonl",
                                "pcrf": seed_root / f"pcrf_seed{seed}/test_pcrf/predictions.jsonl"},
                      "heur": ROOT / FINAL_DIR_REL / "light_test_runs_v2/heur-jw/predictions.jsonl"})
    specs.append({"name": "fivefield_kaggle", "label": LABEL_5F, "kind": "five", "checkpoints": ("kaggle_dyn", None),
                  "files": {"dyn_on": kaggle / "dyn_5field/predictions.jsonl", "dyn_off": kaggle / "dyn_off_5field/predictions.jsonl"},
                  "heur": ROOT / ca.HEUR_5FIELD_REL / "predictions.jsonl"})
    dev_files = {"dyn_off": Path(dev["PROPOSED-NO-CONSTRAINT"]["path"]), "pcrf": Path(dev["PHOBERT-CRF"]["path"])}
    spec_dev = {"name": "dev_kaggle", "label": LABEL_DEV, "kind": "span", "split": "dev", "checkpoints": ("kaggle_dyn", "kaggle_pcrf"),
                "files": dev_files, "heur": Path(dev["HEUR-JW"]["path"]),
                # Only the unconstrained dev run is in the selection lock; the constrained run is a gate reference only.
                "gate_only": {"dyn_on_reference": constrained_ref / "predictions.jsonl"}}
    specs.append(spec_dev)
    return specs


def verify_frozen(specs: list[dict], fr, ca) -> dict:
    """Prediction hashes must equal the freeze records before anything is analysed."""
    report = {}
    test_paths = fr.test_prediction_paths()
    report["test_kaggle"] = fr.verify_frozen_hashes(test_paths)
    frozen_seed = json.loads((ROOT / "data/processed/evaluation/sprint04/multiseed_20261015_v1/frozen_hashes.json").read_text(encoding="utf-8"))
    names = {"dyn_on": "dyn", "dyn_off": "dyn_off", "pcrf": "pcrf"}
    for seed in SEEDS:
        spec = next(s for s in specs if s["name"] == f"test_seed{seed}")
        entry = {}
        for system, path in spec["files"].items():
            expected = frozen_seed[f"{'pcrf' if system == 'pcrf' else 'dyn'}_seed{seed}/{names[system]}"]["predictions_sha256"]
            actual = sha256_file(path)
            if actual != expected:
                raise ValueError(f"seed {seed} {system}: hash {actual} != frozen {expected}")
            entry[system] = {"path": rel(path), "sha256": actual}
        report[spec["name"]] = entry
    final_report = json.loads((ROOT / ca.KAGGLE_REL / "final_inference_report.json").read_text(encoding="utf-8"))["files"]
    spec = next(s for s in specs if s["name"] == "fivefield_kaggle")
    entry = {}
    for system, dirname in (("dyn_on", "dyn_5field"), ("dyn_off", "dyn_off_5field")):
        actual = sha256_file(spec["files"][system])
        if actual != final_report[f"{dirname}/predictions.jsonl"]:
            raise ValueError(f"five-field {system}: hash mismatch with final_inference_report")
        entry[system] = {"path": rel(spec["files"][system]), "sha256": actual}
    entry["heur_followup_fivefield"] = {"path": rel(spec["heur"]), "sha256": sha256_file(spec["heur"]),
                                         "note": "no freeze record; selected because its config equals the locked test config"}
    report["fivefield_kaggle"] = entry
    spec = next(s for s in specs if s["name"] == "dev_kaggle")
    report["dev_kaggle"] = {system: {"path": rel(p), "sha256": sha256_file(p)} for system, p in {**spec["files"], "heur": spec["heur"],
                            **spec["gate_only"]}.items()}
    report["dev_kaggle"]["note"] = ("dyn_off, pcrf and heur are hash-verified by locate_dev_predictions against the selection locks; "
                                    "dyn_on_reference is the constrained dev run NOT in the selection evidence (gate reference only)")
    return report


# -------------------------------------------------------------------- main run
def run(run_name: str) -> int:
    import numpy as np
    from src.evaluation import constraint_ablation as ca
    from src.evaluation import frozen_reliability as fr

    interim = interim_dir(run_name)
    processed = PROCESSED_BASE / run_name
    params_dir = interim / "crf_params"
    if not params_dir.exists():
        raise FileNotFoundError(f"{params_dir} missing: run extract-crf first")
    redecode_dir = interim / "redecode"
    for target in (redecode_dir, processed):
        if target.exists():
            raise FileExistsError(f"{target} exists; refusing to overwrite (use --run-name <name>_v2)")
    params = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in params_dir.glob("*.json") if p.stem != "extraction_summary"}
    for name in ca.CHECKPOINTS:
        if name not in params:
            raise FileNotFoundError(f"CRF parameters for {name} missing")
        if params[name]["bio_masks_match_labels_py"] is not True:
            raise ValueError(f"{name}: checkpoint BIO masks differ from src/modeling/labels.py")
    specs = build_specs(ca, fr)
    frozen = verify_frozen(specs, fr, ca)

    # ---- stage 1: load, re-decode, gate (no gold) ----------------------------------------------------------
    redecode_dir.mkdir(parents=True)
    loaded, gates, started = {}, [], datetime.now(timezone.utc).isoformat()
    for spec in specs:
        dyn_ckpt, pcrf_ckpt = spec["checkpoints"]
        systems = dict(spec["files"])
        systems.update(spec.get("gate_only", {}))
        for system, path in systems.items():
            ckpt = pcrf_ckpt if system == "pcrf" else dyn_ckpt
            rows = ca.load_rows(path)
            ca.redecode_rows(rows, params[ckpt])
            label = f"{spec['name']}/{system}"
            gate = ca.gate_rows(rows, label, constrained_reference=system in ("dyn_on", "dyn_on_reference"))
            gate.update(checkpoint=ckpt, checkpoint_sha256=params[ckpt]["checkpoint_sha256"], prediction_file=rel(path))
            gates.append(gate)
            print(f"gate {label}: {gate['status']} decodable={gate['n_decodable']} ban_rows={gate['ban_rows']}", flush=True)
            if system in spec["files"]:
                loaded[(spec["name"], system)] = rows
            with (redecode_dir / f"{spec['name']}__{system}.jsonl").open("w", encoding="utf-8") as sink:
                for r in rows:
                    sink.write(json.dumps({"sample_id": r["sample_id"], "has_emissions": r["has_emissions"],
                                           "free_path": r.get("free"), "banned_path": r.get("banned"),
                                           "stored_before": r.get("path_before"), "stored_after": r.get("path_after"),
                                           "t1_predicted_system": (r.get("structure") or {}).get("predicted_system"),
                                           "ban_district_stored": (r.get("structure") or {}).get("ban_district"),
                                           "free_ties": r.get("free_ties"), "ban_ties": r.get("ban_ties")}) + "\n")
    gate_report = {"rule": ca.RULE_VERSION, "forbidden_tag_ids": ca.QUAN_HUYEN_IDS,
                   "forbidden_tags": [ca.BIO_LABELS[i] for i in ca.QUAN_HUYEN_IDS], "gates": gates}
    write_json(redecode_dir / "gate_report.json", gate_report)
    failed = [g["label"] for g in gates if g["status"] != "PASS"]
    if failed:
        print("GATE FAILED -> stop before any analysis:", failed)
        return 2

    # ---- stage 2: manifest before scoring (systems, rules, seed, input hashes) -------------------------------
    processed.mkdir(parents=True)
    code_files = [ROOT / "src/evaluation/constraint_ablation.py", Path(__file__), ROOT / "src/modeling/structural_decoder.py",
                  ROOT / "src/modeling/labels.py", ROOT / "src/evaluation/stats.py", ROOT / "src/evaluation/frozen_reliability.py"]
    manifest = {
        "run_name": run_name, "stage": "PRE_SCORING", "started_utc": started, "rule_version": ca.RULE_VERSION,
        "rule": "ban B-/I-QuanHuyen in the Viterbi decode when the T1 source predicts 'moi'; T1 sources compared: DYN (own head, "
                "threshold 0.7 / margin 0.2 as stored), HEUR-JW (frozen predicted_system), ORACLE_UPPER_BOUND (gold system)",
        "systems": ["PHOBERT-CRF", "PROPOSED-NO-CONSTRAINT", "PROPOSED-DYN", "DYN-emissions+HEUR-JW-T1", "PCRF-emissions+HEUR-JW-T1"],
        "oracle_systems": ["DYN-emissions+ORACLE_UPPER_BOUND", "PCRF-emissions+ORACLE_UPPER_BOUND"],
        "datasets": {s["name"]: {"label": s["label"], "kind": s["kind"], "files": {k: rel(v) for k, v in s["files"].items()}}
                     for s in specs},
        "bootstrap": {"seed": ca.SEED, "n_resamples": ca.N_RESAMPLES, "unit": "row (sample / five-field row)"},
        "frozen_input_hashes": frozen,
        "crf_checkpoints": {n: {"path": params[n]["checkpoint_path"], "sha256": params[n]["checkpoint_sha256"]} for n in ca.CHECKPOINTS},
        "gate_summary": {g["label"]: g["status"] for g in gates},
        "code_sha256": {rel(p): sha256_file(p) for p in code_files},
        "no_neural_inference": "CRF tensors read with torch.load only; no adapter, no model forward pass",
    }
    pre_digest = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    write_json(processed / "run_manifest.json", manifest)

    # ---- stage 3: scoring ------------------------------------------------------------------------------------
    results = {}
    heur_cache = {}

    def heur_map(path: Path) -> dict:
        if path not in heur_cache:
            heur_cache[path] = ca.load_system_map(path)
        return heur_cache[path]

    five_manifest = json.loads((ROOT / FINAL_DIR_REL / "fivefield_input.manifest.json").read_text(encoding="utf-8"))
    for spec in specs:
        name = spec["name"]
        off_rows = loaded[(name, "dyn_off")]
        on_rows = loaded.get((name, "dyn_on"))
        pcrf_rows = loaded.get((name, "pcrf"))
        if spec["kind"] == "span":
            golds, excluded = fr.load_gold(spec["split"])
            build = lambda rows: ca.span_arrays(rows, golds, excluded)  # noqa: E731
        else:
            keys = {(r["dataset"], r["source_row"]) for r in off_rows}
            gold = ca.load_fivefield_gold(keys, five_manifest)
            build = lambda rows: ca.fivefield_arrays(rows, gold)  # noqa: E731
        arr = build(off_rows)
        ids = arr["sample_ids"]
        heur = heur_map(spec["heur"])
        flags = {"DYN": ca.dyn_flags_from_rows(off_rows, ids), "HEUR-JW": ca.heur_flags(heur, ids), "ORACLE_UPPER_BOUND": ca.oracle_flags(arr)}
        entry = {"label": spec["label"], "kind": spec["kind"], "n_rows": len(ids), "sources": {}, "checks": {}}
        for source, f in flags.items():
            entry["sources"][source] = ca.analyze_source(arr, f, source)
            entry["sources"][source]["label"] = "ORACLE_UPPER_BOUND" if source.startswith("ORACLE") else spec["label"]
        entry["headroom"] = ca.analyze_headroom(arr, flags["DYN"], [heur[i] for i in ids])
        # the file that ran the constraint must be reproduced by re-decoding with the DYN source
        if on_rows is not None:
            on_by_id = {r["sample_id"]: r for r in on_rows}
            # rows without emissions (abstentions) have no path or structure: they are identical in both modes
            decodable = [(i, on_by_id[s]) for i, s in enumerate(ids) if on_by_id[s]["has_emissions"]]
            same_flags = all(bool(r["structure"]["ban_district"]) == bool(flags["DYN"][i]) for i, r in decodable)
            same_paths = all(r["path_after"] == ca.path_for(r, bool(flags["DYN"][i])) for i, r in decodable)
            entry["checks"] = {"stored_ban_district_equals_dyn_source_flags": same_flags,
                               "stored_path_after_equals_redecode_with_dyn_source": same_paths}
            if spec["kind"] == "span":
                stored_on = ca.stored_span_counts(on_rows, golds, excluded)
                stored_off = ca.stored_span_counts(off_rows, golds, excluded)
                entry["checks"]["stored_on_counts_equal_redecoded"] = bool(np.array_equal(stored_on, ca.pick(arr, flags["DYN"])))
                entry["checks"]["stored_off_counts_equal_redecoded"] = bool(np.array_equal(stored_off, arr["cf"]))
                entry["stored_on_vs_off"] = ca.pair_stats(stored_on, stored_off)
        if spec["kind"] == "span":
            micro = {"free": ca.micro_f1(arr["cf"]), "dyn": ca.micro_f1(ca.pick(arr, flags["DYN"]))}
            entry["dyn_t0_f1"] = micro
        if pcrf_rows is not None:
            arr_p = build(pcrf_rows)
            ids_p = arr_p["sample_ids"]
            flags_p = {"HEUR-JW": ca.heur_flags(heur, ids_p), "ORACLE_UPPER_BOUND": ca.oracle_flags(arr_p)}
            entry["pcrf_sources"] = {}
            for source, f in flags_p.items():
                entry["pcrf_sources"][source] = ca.analyze_source(arr_p, f, source)
                entry["pcrf_sources"][source]["label"] = "ORACLE_UPPER_BOUND" if source.startswith("ORACLE") else spec["label"]
            entry["pcrf_headroom"] = ca.analyze_headroom(arr_p, None, [heur[i] for i in ids_p])
            counts_dyn = ca.pick(arr, flags["DYN"])
            cells = [("PHOBERT-CRF", False, False, "none", arr_p["cf"], arr_p["ef"]),
                     ("PROPOSED-NO-CONSTRAINT", True, False, "none", arr["cf"], arr["ef"]),
                     ("PROPOSED-DYN", True, True, "DYN head", counts_dyn, np.where(flags["DYN"], arr["eb"], arr["ef"])),
                     ("PHOBERT-CRF emissions + external T1", False, True, "HEUR-JW (external, frozen)",
                      ca.pick(arr_p, flags_p["HEUR-JW"]), np.where(flags_p["HEUR-JW"], arr_p["eb"], arr_p["ef"]))]
            entry["comparison_2x2"] = [ca.model_comparison_row(*c) for c in cells]
            base = arr_p["cf"]
            entry["comparison_2x2_paired_vs_pcrf"] = {
                c[0]: ca.pair_stats(c[4], base) for c in cells[1:]}
            entry["comparison_2x2_paired_vs_pcrf"]["PROPOSED-DYN vs PROPOSED-NO-CONSTRAINT"] = ca.pair_stats(counts_dyn, arr["cf"])
            entry["oracle_cells"] = {  # ORACLE_UPPER_BOUND: kept apart from comparison_2x2
                "PHOBERT-CRF emissions + ORACLE_UPPER_BOUND": entry["pcrf_sources"]["ORACLE_UPPER_BOUND"],
                "DYN emissions + ORACLE_UPPER_BOUND": entry["sources"]["ORACLE_UPPER_BOUND"]}
        results[name] = entry
        print("scored", name, flush=True)

    # published-score cross-check on the Kaggle test (Sprint 3 values, 4 dp)
    kag = results["test_kaggle"]
    published = fr.PUBLISHED_T0
    kag["matches_published_t0_f1"] = {
        "PHOBERT-CRF": round(kag["comparison_2x2"][0]["f1"], 4) == published["PHOBERT-CRF"][2],
        "PROPOSED-NO-CONSTRAINT": round(kag["comparison_2x2"][1]["f1"], 4) == published["PROPOSED-NO-CONSTRAINT"][2],
        "PROPOSED-DYN": round(kag["comparison_2x2"][2]["f1"], 4) == published["PROPOSED-DYN"][2]}

    # seed summary (descriptive; n = 3, ddof = 1)
    seed_rows = []
    for seed in SEEDS:
        r = results[f"test_seed{seed}"]
        cells = {c["cell"]: c["f1"] for c in r["comparison_2x2"]}
        seed_rows.append({"seed": seed, **{k: cells[k] for k in cells},
                          "dyn_ban_delta": r["sources"]["DYN"]["f1_with_ban"] - r["sources"]["DYN"]["f1_no_constraint"],
                          "heur_ban_delta": r["sources"]["HEUR-JW"]["f1_with_ban"] - r["sources"]["HEUR-JW"]["f1_no_constraint"],
                          "oracle_ban_delta_ORACLE_UPPER_BOUND": r["sources"]["ORACLE_UPPER_BOUND"]["f1_with_ban"] - r["sources"]["ORACLE_UPPER_BOUND"]["f1_no_constraint"]})
    seed_summary = {"label": LABEL_SEED, "per_seed": seed_rows, "mean_std": {}}
    for key in ("PHOBERT-CRF", "PROPOSED-NO-CONSTRAINT", "PROPOSED-DYN", "PHOBERT-CRF emissions + external T1", "dyn_ban_delta", "heur_ban_delta"):
        values = [row[key] for row in seed_rows]
        seed_summary["mean_std"][key] = {"mean": sum(values) / len(values), "std_ddof1": ca.sample_std(values)}
    seed_summary["wp3b_reported_std_cross_check"] = {
        k: {"reported": WP3B_STD[k], "measured_here": round(seed_summary["mean_std"][k]["std_ddof1"], 4)} for k in WP3B_STD}

    # no run name or timestamp in metrics.json, so a re-run into a new directory is byte-identical
    metrics = {"rule_version": ca.RULE_VERSION, "results": results, "seed_summary": seed_summary,
               "gate": gate_report["gates"]}
    write_json(processed / "metrics.json", metrics)
    write_tables(processed, results, seed_summary, gates)

    final = dict(manifest, stage="COMPLETE", finished_utc=datetime.now(timezone.utc).isoformat(),
                 pre_scoring_manifest_sha256=pre_digest,
                 outputs={p.name if p.parent == processed else f"tables/{p.name}": sha256_file(p)
                          for p in sorted(list(processed.glob("*.json")) + list(processed.glob("tables/*.csv"))) if p.name != "run_manifest.json"},
                 row_counts={n: r["n_rows"] for n, r in results.items()})
    write_json(processed / "run_manifest.json", final)
    print("done", processed)
    return 0


# ----------------------------------------------------------------------- tables
def write_tables(processed: Path, results: dict, seed_summary: dict, gates: list[dict]) -> None:
    tables = processed / "tables"
    tables.mkdir()
    gate_cols = ["label", "status", "checkpoint", "n_rows", "n_decodable", "n_no_emissions", "free_vs_before_mismatch", "ban_rows",
                 "ban_vs_after_mismatch", "after_eq_before_on_nonban_mismatch", "stored_span_mismatch", "reference_disagree",
                 "rows_with_tie_free", "rows_with_tie_ban"]
    write_csv(tables / "gate.csv", gates, gate_cols)

    source_cols = ["dataset", "label", "emission_model", "t1_source", "n_rows", "n_ban_rows", "n_changed_rows", "n_span_changes",
                   "correct_fix", "harm", "neutral", "f1_no_constraint", "f1_with_ban", "delta", "ci_low", "ci_high", "ci_status",
                   "exact_no_constraint", "exact_with_ban"]

    def source_row(dataset, entry_label, emission, s):
        p = s.get("paired", {})
        return {"dataset": dataset, "label": s["label"], "emission_model": emission, "t1_source": s["source"], "n_rows": s["n_rows"],
                "n_ban_rows": s["n_ban_rows"], "n_changed_rows": s["n_changed_rows"], "n_span_changes": s["n_span_changes"],
                "correct_fix": s["correct_fix"], "harm": s["harm"], "neutral": s["neutral"],
                "f1_no_constraint": s["f1_no_constraint"], "f1_with_ban": s["f1_with_ban"], "delta": p.get("delta"),
                "ci_low": p.get("ci_low"), "ci_high": p.get("ci_high"), "ci_status": p.get("status"),
                "exact_no_constraint": s["exact_no_constraint"], "exact_with_ban": s["exact_with_ban"]}

    on_off, ablation, oracle = [], [], []
    for dataset, r in results.items():
        for emission, group in (("PROPOSED-DYN checkpoint", r["sources"]), ("PHOBERT-CRF checkpoint", r.get("pcrf_sources", {}))):
            for source, s in group.items():
                row = source_row(dataset, r["label"], emission, s)
                if source.startswith("ORACLE"):
                    oracle.append(row)
                else:
                    ablation.append(row)
                    if source == "DYN":
                        on_off.append(row)
    write_csv(tables / "onoff_dyn_source.csv", on_off, source_cols)
    write_csv(tables / "t1_source_ablation.csv", ablation, source_cols)
    write_csv(tables / "oracle_upper_bound.csv", oracle, source_cols)

    head_cols = ["dataset", "label", "emission_model", "n_rows", "n_gold_moi", "n_gold_moi_without_quan_huyen", "n_gold_moi_t1_eligible", "n_headroom", "n_headroom_t1_eligible",
                 "n_headroom_removed_by_unconditional_ban", "headroom_dyn_moi", "headroom_dyn_cu", "headroom_dyn_Lai",
                 "headroom_dyn_khong_ro", "headroom_heur_moi", "headroom_heur_cu", "headroom_heur_Lai", "headroom_heur_khong_ro",
                 "n_headroom_fixed_by_dyn_ban", "harm_exposure_dyn_ban", "harm_exposure_removed", "status"]
    head = []
    for dataset, r in results.items():
        for emission, h in (("PROPOSED-DYN checkpoint", r["headroom"]), ("PHOBERT-CRF checkpoint", r.get("pcrf_headroom"))):
            if h is None:
                continue
            by = h.get("headroom_by_dyn_t1", {})
            hh = h.get("headroom_by_heur_t1", {})
            head.append({"dataset": dataset, "label": r["label"], "emission_model": emission, **h,
                         "headroom_dyn_moi": by.get("moi"), "headroom_dyn_cu": by.get("cu"), "headroom_dyn_Lai": by.get("Lai"),
                         "headroom_dyn_khong_ro": by.get("khong_ro"),
                         "headroom_heur_moi": hh.get("moi"), "headroom_heur_cu": hh.get("cu"), "headroom_heur_Lai": hh.get("Lai"),
                         "headroom_heur_khong_ro": hh.get("khong_ro"),
                         "harm_exposure_dyn_ban": h.get("n_harm_exposure_gold_quan_huyen_with_dyn_ban"),
                         "harm_exposure_removed": h.get("n_harm_exposure_qh_removed_by_ban")})
    write_csv(tables / "headroom.csv", head, head_cols)

    comp_cols = ["dataset", "label", "cell", "train_with_t1_head", "decode_with_constraint", "t1_source", "n_rows", "f1", "ci_low",
                 "ci_high", "exact_rows", "tp", "fp", "fn", "delta_vs_phobert_crf", "delta_ci_low", "delta_ci_high"]
    comp = []
    for dataset, r in results.items():
        for cell in r.get("comparison_2x2", []):
            paired = r["comparison_2x2_paired_vs_pcrf"].get(cell["cell"], {})
            comp.append({"dataset": dataset, "label": r["label"], **cell, "delta_vs_phobert_crf": paired.get("delta"),
                         "delta_ci_low": paired.get("ci_low"), "delta_ci_high": paired.get("ci_high")})
    write_csv(tables / "model_comparison_2x2.csv", comp, comp_cols)

    seed_cols = ["seed", "PHOBERT-CRF", "PROPOSED-NO-CONSTRAINT", "PROPOSED-DYN", "PHOBERT-CRF emissions + external T1",
                 "dyn_ban_delta", "heur_ban_delta"]
    write_csv(tables / "seed_summary.csv", seed_summary["per_seed"], seed_cols)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("stage", choices=["extract-crf", "run"])
    parser.add_argument("--run-name", default=DEFAULT_RUN)
    args = parser.parse_args()
    if args.stage == "extract-crf":
        extract_crf(args.run_name)
        return 0
    return run(args.run_name)


if __name__ == "__main__":
    raise SystemExit(main())
