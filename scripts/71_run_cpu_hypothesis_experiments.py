"""WP4: cheap CPU hypothesis experiments H3 (field order), E1 (comma/case), H2 (missing-field augmentation), H4.

Main process (``~/.venv_dacn``) builds inputs, scores and runs statistics.  Every CRF training/inference is a separate
process in the CRF runtime (pycrfsuite, no numpy/pandas) started by this same script in ``worker`` mode:

    python -m scripts.71_run_cpu_hypothesis_experiments run [--interim-dir D --processed-dir D]
    runtime_py311/bin/python -m scripts.71_run_cpu_hypothesis_experiments worker JOB.json     (internal)

Output directories are versioned; an existing directory is never overwritten.  Test Sprint 3 was already observed,
so every number on it is a post-hoc robustness analysis, not a selection signal.  Model hyper-parameters are read
from the locked Sprint 3 metadata and never tuned per condition.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CRF_PYTHON = ROOT / "data/interim/evaluation/sprint03/runtime_py311/bin/python"
REFERENCE_DIR = ROOT / "data/processed/evaluation/sprint03/crf_followup_20261003_v1/ctx1_c10.1_c21"
REFERENCE_CHECKPOINT_SHA256 = "b4ff0d23427934cf10fbfe72764eb83d931bec05a8fb8b4a3056df8c682004f8"
TRAIN_DIR = ROOT / "data/processed/annotation/sprint03/corpus_train_dev_v2"
EVAL_DIR = ROOT / "data/processed/annotation/sprint03/corpus_v1_release2"
BENCHMARK_DIR = ROOT / "data/processed/benchmark"
HEUR_CONFIG = ROOT / "data/interim/modeling/sprint03/final_completion_20261005_v1/light_test_runs_v2/heur-jw/model_config.json"
DEFAULT_INTERIM = ROOT / "data/interim/modeling/sprint04/cpu_hypotheses_20261016_v1"
DEFAULT_PROCESSED = ROOT / "data/processed/evaluation/sprint04/cpu_hypotheses_20261016_v1"

SEED = 20261016                 # H2 group split, k-fold and bootstrap seed of this package
PERMUTATION_SEEDS = (42, 1337, 2025)
SUBSET_SEEDS = (20261016, 1337, 2025)   # H2 augmentation subsets; the first one is the primary run
AUG_SIZES = (120, 240)
HELDOUT_GROUP_SHARE = 0.30
EVAL_FULL_SIZE = 300
KFOLD_K = 5
KFOLD_SEED = 42
SOURCE_FILES = ("scripts/71_run_cpu_hypothesis_experiments.py", "src/evaluation/perturbations.py",
                "src/evaluation/frozen_reliability.py", "src/evaluation/stats.py", "src/evaluation/leak_guard.py",
                "src/evaluation/span_features.py", "src/evaluation/adapters/crf_adapter.py",
                "src/evaluation/span_scorer.py", "src/evaluation/scorer.py", "src/data/span_trace.py")
LANE_PREFIXES = ("ngõ", "hẻm", "ngách", "kiệt")


# ------------------------------------------------------------------ small io helpers (stdlib)
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def require(path: Path) -> Path:
    if not Path(path).exists():
        raise FileNotFoundError(f"Required input missing: {path}")
    return Path(path)


# ------------------------------------------------------------------ CRF worker (CRF runtime only)
def worker_main(job_path: Path) -> None:
    """Train CRF models and write predictions.  Text and spans only; no numpy/pandas, no ground-truth metadata columns."""
    import pycrfsuite
    from src.evaluation.adapters.crf_adapter import IndependentCRFAdapter
    from src.evaluation.span_features import encode_gold, token_features

    job = json.loads(job_path.read_text(encoding="utf-8"))
    reference = json.loads(require(Path(job["reference_metadata"])).read_text(encoding="utf-8"))
    results = []
    for item in job["models"]:
        model_path, meta_path = Path(item["model_path"]), Path(item["metadata_path"])
        if item.get("reuse"):          # predict-only item on a model trained earlier
            adapter = IndependentCRFAdapter(str(require(model_path)), str(require(meta_path)))
            for target in item["predict"]:
                rows = []
                for sample in read_jsonl(Path(target["inputs"])):
                    output = adapter.parse_spans(sample["text"])
                    output.sample_id, output.latency_ms = sample["sample_id"], 0.0
                    rows.append(output.to_dict())
                write_jsonl(Path(target["out"]), rows)
            results.append({"model": item["name"], "reuse": True})
            continue
        if model_path.exists() or meta_path.exists():
            raise FileExistsError(f"Refusing to overwrite {model_path}")
        model_path.parent.mkdir(parents=True, exist_ok=True)
        train = read_jsonl(Path(item["train_jsonl"]))
        aligned = [encode_gold(row["text"], row["spans"]) for row in train]   # raises on any boundary problem
        trainer = pycrfsuite.Trainer(verbose=False)
        trainer.select("lbfgs", "crf1d")
        for row, (tokens, tags) in zip(train, aligned):
            trainer.append(token_features(row["text"], tokens, reference["context"], reference["feature_version"]), tags)
        trainer.set_params(reference["parameters"])          # locked hyper-parameters, identical in every condition
        started = time.perf_counter()
        trainer.train(str(model_path))
        metadata = {key: reference[key] for key in ("model_id", "algorithm", "context", "parameters", "feature_version",
                                                    "tokenizer_version", "bio_schema")}
        metadata.update({"seed": reference["seed"], "train_samples": len(train),
                         "token_count": sum(len(t) for t, _ in aligned),
                         "train_jsonl_sha256": sha256_file(Path(item["train_jsonl"])),
                         "checkpoint_sha256": sha256_file(model_path),
                         "training_seconds": time.perf_counter() - started})
        write_json(meta_path, metadata)
        adapter = IndependentCRFAdapter(str(model_path), str(meta_path))
        outputs = {}
        for target in item["predict"]:
            rows = []
            for sample in read_jsonl(Path(target["inputs"])):
                output = adapter.parse_spans(sample["text"])    # text only
                output.sample_id = sample["sample_id"]
                output.latency_ms = 0.0                          # keeps prediction files byte-reproducible
                rows.append(output.to_dict())
            write_jsonl(Path(target["out"]), rows)
            outputs[target["out"]] = len(rows)
        results.append({"model": item["name"], "checkpoint_sha256": metadata["checkpoint_sha256"],
                        "train_samples": len(train), "predictions": outputs})
    Path(job["result_path"]).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")


def run_crf_job(job: dict, job_path: Path) -> list[dict]:
    """Start the CRF worker process for ``job`` and return its result list."""
    require(CRF_PYTHON)
    job = {**job, "reference_metadata": str(REFERENCE_DIR / "model_metadata.json"),
           "result_path": str(job_path.with_suffix(".result.json"))}
    write_json(job_path, job)
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(ROOT)}
    completed = subprocess.run([str(CRF_PYTHON), "-m", "scripts.71_run_cpu_hypothesis_experiments", "worker",
                                str(job_path)], cwd=ROOT, env=env, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"CRF worker failed:\n{completed.stderr[-3000:]}")
    return json.loads(Path(job["result_path"]).read_text(encoding="utf-8"))


# ------------------------------------------------------------------ analysis helpers (main venv: numpy, pandas)
def csv_write(path: Path, rows: list[dict]) -> None:
    import csv
    if not rows:
        return
    names = list(dict.fromkeys(key for row in rows for key in row))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)


def fnum(value, digits: int = 4):
    return None if value is None else round(float(value), digits)


def verdict_from_delta(delta: dict) -> str:
    """Reading of a paired delta CI: only an interval that excludes 0 separates the conditions."""
    if delta.get("ci_low") is None:
        return delta.get("status") or "NOT_EVALUABLE"
    if delta["ci_high"] < 0:
        return "DROP_CI_EXCLUDES_0"
    if delta["ci_low"] > 0:
        return "GAIN_CI_EXCLUDES_0"
    return "NOT_SEPARABLE_CI_INCLUDES_0"


def first_ci(stat, units, seed: int | None = None) -> dict:
    from src.evaluation import frozen_reliability as fr
    from src.evaluation import stats
    return stats.bootstrap_ci(stat, units, fr.N_RESAMPLES, seed=SEED if seed is None else seed)


def paired_delta(stat, units_a, units_b, cluster_ids=None) -> dict:
    from src.evaluation import frozen_reliability as fr
    from src.evaluation import stats
    return stats.paired_bootstrap_delta(stat, units_a, units_b, fr.N_RESAMPLES, cluster_ids=cluster_ids, seed=SEED)


def unpaired_delta(stat, units_a, units_b, clusters_a=None) -> dict:
    """Independent-sample bootstrap of stat(A) - stat(B); used when A and B are different rows.

    ``clusters_a`` resamples whole groups on side A (rows of one territory are not independent).
    """
    import numpy as np
    from src.evaluation import frozen_reliability as fr
    a, b = np.asarray(units_a), np.asarray(units_b)
    if len(a) == 0 or len(b) == 0:
        return {"status": "NOT_EVALUABLE_NO_SUPPORT", "estimate": None, "ci_low": None, "ci_high": None}
    rng = np.random.default_rng(SEED)
    observed = float(stat(a)) - float(stat(b))
    members = None
    if clusters_a is not None:
        keys = sorted(set(clusters_a))
        position = {k: i for i, k in enumerate(keys)}
        members = [[] for _ in keys]
        for row, key in enumerate(clusters_a):
            members[position[key]].append(row)
        members = [np.asarray(m) for m in members]

    def draw_a():
        if members is None:
            return a[rng.integers(0, len(a), len(a))]
        chosen = rng.integers(0, len(members), len(members))
        return a[np.concatenate([members[c] for c in chosen])]

    draws = [float(stat(draw_a())) - float(stat(b[rng.integers(0, len(b), len(b))])) for _ in range(fr.N_RESAMPLES)]
    draws = np.asarray(draws)[np.isfinite(draws)]
    low, high = np.percentile(draws, [2.5, 97.5])
    return {"status": "OK", "estimate": observed, "ci_low": float(low), "ci_high": float(high),
            "method": "unpaired_bootstrap_delta"}


def load_units(prediction_path: Path, golds: list[dict], excluded: list[str]) -> dict:
    from src.evaluation import frozen_reliability as fr
    from src.evaluation.dev_runner import load_predictions
    return fr.build_units(load_predictions(prediction_path), golds, excluded)


def micro_row(units: dict, label_names: tuple[str, ...] | None = None) -> dict:
    from src.evaluation import frozen_reliability as fr
    totals = units["totals"]
    out = {"n_samples": len(totals), "tp": int(totals[:, 0].sum()), "fp": int(totals[:, 1].sum()),
           "fn": int(totals[:, 2].sum())}
    for name, stat in (("precision", fr.precision_stat), ("recall", fr.recall_stat), ("f1", fr.f1_stat)):
        ci = first_ci(stat, totals)
        out[name] = fnum(ci.get("estimate"))
        out[f"{name}_ci_low"], out[f"{name}_ci_high"] = fnum(ci.get("ci_low")), fnum(ci.get("ci_high"))
        out[f"{name}_status"] = ci.get("status")
    return out


def label_rows(units: dict, extra: dict) -> list[dict]:
    from src.evaluation import frozen_reliability as fr
    from src.evaluation.schema import SPAN11_LABELS
    rows = []
    for i, label in enumerate(SPAN11_LABELS):
        counts = units["by_label"][:, i, :]
        support = int(counts[:, 0].sum() + counts[:, 2].sum())
        rows.append({**extra, "label": label, "gold_support": support, "support_flag": fr.support_flag(support),
                     "f1": fnum(fr.f1_stat(counts)) if support else None})
    return rows


def sorted_by_id(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda row: row["sample_id"])


def make_gold(base: dict, text: str, spans: list[dict]) -> dict:
    return {**base, "text": text, "spans": spans}


def write_inputs(path: Path, golds: list[dict]) -> None:
    write_jsonl(path, [{"sample_id": g["sample_id"], "text": g["text"]} for g in golds])


def write_train(path: Path, rows: list[dict]) -> None:
    write_jsonl(path, [{"sample_id": r["sample_id"], "text": r["text"],
                        "spans": [{k: s[k] for k in ("start", "end", "label", "system")} for s in r["spans"]]}
                       for r in rows])


# ------------------------------------------------------------------ HEUR-JW (main venv)
class HeuristicRunner:
    """Locked HEUR-JW adapter built through the same resource-hash check as the Sprint 3 test run."""

    def __init__(self) -> None:
        import importlib
        from src.evaluation.dev_runner import resource_manifest
        self.config = json.loads(require(HEUR_CONFIG).read_text(encoding="utf-8"))
        resource_manifest(self.config)          # raises when a locked gazetteer/rule file hash differs
        module_name, class_name = self.config["adapter_factory"].split(":")
        self.adapter = getattr(importlib.import_module(module_name), class_name)(**self.config["adapter_kwargs"])

    def predict(self, golds: list[dict], out_path: Path) -> None:
        rows = []
        for gold in golds:
            output = self.adapter.parse_spans(gold["text"])    # text only
            output.sample_id = gold["sample_id"]
            output.latency_ms = 0.0
            rows.append(output.to_dict())
        write_jsonl(out_path, rows)


# ------------------------------------------------------------------ context and step 0
def build_context(interim: Path, processed: Path) -> dict:
    """Load frozen gold/train inputs, verify hashes, create the versioned output directories."""
    from src.evaluation import frozen_reliability as fr
    for directory in (interim, processed):
        if directory.exists():
            raise FileExistsError(f"Refusing to overwrite {directory}; use a new version directory")
    manifest = fr.load_corpus_manifest()
    train_hash = sha256_file(require(TRAIN_DIR / "train.jsonl"))
    if train_hash != manifest["output_sha256"]["train.jsonl"]:
        raise ValueError("train.jsonl differs from the corpus manifest")
    train = read_jsonl(TRAIN_DIR / "train.jsonl")
    registry = {row["sample_id"]: row for row in read_jsonl(require(fr.CORPUS_DIR / "identity_registry.jsonl"))}
    test_gold, test_excluded = fr.load_gold("test")
    dev_gold, dev_excluded = fr.load_gold("dev")
    frozen = fr.verify_frozen_hashes(fr.test_prediction_paths())
    interim.mkdir(parents=True)
    processed.mkdir(parents=True)
    return {"interim": interim, "processed": processed, "train": train, "registry": registry,
            "test_gold": test_gold, "test_excluded": test_excluded, "dev_gold": dev_gold, "dev_excluded": dev_excluded,
            "frozen_hashes": frozen, "corpus_manifest": manifest, "heur": None}


def heur(ctx: dict) -> HeuristicRunner:
    if ctx["heur"] is None:
        ctx["heur"] = HeuristicRunner()
    return ctx["heur"]


def declared_manifest(ctx: dict) -> dict:
    """Written BEFORE any scoring: systems, conditions, seeds and rules are fixed here."""
    from src.evaluation import frozen_reliability as fr
    inputs = {"train.jsonl": sha256_file(TRAIN_DIR / "train.jsonl"),
              "identity_registry.jsonl": sha256_file(fr.CORPUS_DIR / "identity_registry.jsonl"),
              "test_benchmark_t0.jsonl": sha256_file(fr.CORPUS_DIR / "test_benchmark_t0.jsonl"),
              "dev.jsonl": sha256_file(fr.CORPUS_DIR / "dev.jsonl"),
              "reference_checkpoint": sha256_file(REFERENCE_DIR / "model.crfsuite"),
              "reference_metadata": sha256_file(REFERENCE_DIR / "model_metadata.json"),
              "heur_config": sha256_file(HEUR_CONFIG)}
    for name in ("01_full_address_new_verified.csv", "03_real_address_old_1500.csv", "04_missing_fields_800.csv"):
        inputs[name] = sha256_file(require(BENCHMARK_DIR / name))
    return {
        "run_id": ctx["processed"].name, "status": "DECLARED_BEFORE_SCORING", "rule_version": "wp4_cpu_hypotheses_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs_sha256": inputs, "frozen_test_predictions": ctx["frozen_hashes"],
        "code_sha256": {name: sha256_file(ROOT / name) for name in SOURCE_FILES},
        "seeds": {"bootstrap_and_h2_split": SEED, "h3_permutations": list(PERMUTATION_SEEDS),
                  "h2_subset_seeds_primary_first": list(SUBSET_SEEDS), "kfold": KFOLD_SEED},
        "declared_systems": ["CRF-INDEP (retrained, locked config)", "HEUR-JW (locked config; test-time perturbations only)"],
        "declared_conditions": {
            "H3": ["recomposed_original_order (control)", "reverse", *[f"shuffle_seed{s}" for s in PERMUTATION_SEEDS]],
            "E1": ["commas x case 2x2; mode a (test-time only) and mode b (train+test)"],
            "H2": {"models": ["BASE", "AUG-MISSING", "AUG-FULL"], "N": list(AUG_SIZES),
                   "heldout_group_share": HELDOUT_GROUP_SHARE, "eval_full_size": EVAL_FULL_SIZE},
            "H4": "groups admin/road/landmark/other from frozen test predictions"},
        "hyperparameters": "read from the locked Sprint 3 model_metadata.json; identical in every condition; no tuning",
        "gt_columns_policy": "GT_* used only to build group keys and to leak-filter; never features or labels",
        "test_status": "Sprint 3 test already observed: every number on it is post-hoc robustness analysis",
        "row_counts": {"train": len(ctx["train"]), "test": len(ctx["test_gold"]), "dev": len(ctx["dev_gold"])},
    }


def train_base(ctx: dict) -> dict:
    """Retrain the locked CRF in the CRF runtime; prediction files for test and dev originals."""
    out = ctx["interim"] / "models/base"
    write_inputs(out / "test_input.jsonl", ctx["test_gold"])
    write_inputs(out / "dev_input.jsonl", ctx["dev_gold"])
    job = {"models": [{"name": "BASE", "train_jsonl": str(TRAIN_DIR / "train.jsonl"), "model_path": str(out / "model.crfsuite"),
                       "metadata_path": str(out / "model_metadata.json"),
                       "predict": [{"inputs": str(out / "test_input.jsonl"), "out": str(out / "predictions_test.jsonl")},
                                   {"inputs": str(out / "dev_input.jsonl"), "out": str(out / "predictions_dev.jsonl")}]}]}
    result = run_crf_job(job, out / "job.json")[0]
    return {"model_path": out / "model.crfsuite", "metadata_path": out / "model_metadata.json",
            "pred_test": out / "predictions_test.jsonl", "pred_dev": out / "predictions_dev.jsonl", "result": result}


def span_keys(predictions) -> list:
    return [(p.sample_id, [(s.start, s.end, s.label) for s in p.spans]) for p in predictions]


def step0(ctx: dict) -> dict:
    """Reproduce CRF-INDEP and HEUR-JW at original conditions and measure the preconditions of H3/E1."""
    from src.evaluation import frozen_reliability as fr
    from src.evaluation.dev_runner import load_predictions
    from src.evaluation import perturbations as pert
    base = train_base(ctx)
    report = {"checkpoint_sha256": base["result"]["checkpoint_sha256"], "reference_sha256": REFERENCE_CHECKPOINT_SHA256}
    if report["checkpoint_sha256"] != REFERENCE_CHECKPOINT_SHA256:
        raise RuntimeError(f"STEP0_MISMATCH checkpoint hash {report['checkpoint_sha256']}")
    frozen_paths = fr.test_prediction_paths()
    predictions = load_predictions(base["pred_test"])
    micro = fr.scorer_metrics(predictions, ctx["test_gold"], ctx["test_excluded"])["t0_exact_span"]["micro"]
    report["crf_test_prf1"] = [micro["precision"], micro["recall"], micro["f1"]]
    if tuple(report["crf_test_prf1"]) != fr.PUBLISHED_T0["CRF-INDEP"]:
        raise RuntimeError(f"STEP0_MISMATCH CRF test P/R/F1 {report['crf_test_prf1']}")
    report["crf_spans_equal_frozen"] = span_keys(predictions) == span_keys(load_predictions(frozen_paths["CRF-INDEP"]))
    heur_out = ctx["interim"] / "models/heur_original_test.jsonl"
    heur(ctx).predict(ctx["test_gold"], heur_out)
    heur_preds = load_predictions(heur_out)
    hm = fr.scorer_metrics(heur_preds, ctx["test_gold"], ctx["test_excluded"])["t0_exact_span"]["micro"]
    report["heur_test_prf1"] = [hm["precision"], hm["recall"], hm["f1"]]
    report["heur_spans_equal_frozen"] = span_keys(heur_preds) == span_keys(load_predictions(frozen_paths["HEUR-JW"]))
    if tuple(report["heur_test_prf1"]) != fr.PUBLISHED_T0["HEUR-JW"] or not report["heur_spans_equal_frozen"]:
        raise RuntimeError(f"STEP0_MISMATCH HEUR-JW {report['heur_test_prf1']}")

    # Preconditions of the perturbations over all 400 gold samples (train + dev + test).
    samples = ([("train", r) for r in ctx["train"]] + [("dev", r) for r in ctx["dev_gold"]]
               + [("test", r) for r in ctx["test_gold"]])
    pre = {"samples": len(samples), "overlapping_spans": 0, "lower_changes_length": 0, "no_comma": 0,
           "outside_text": 0, "outside_text_test": 0, "no_comma_test": 0, "offset_failures": {}, "surface_failures": {}}
    for split, row in samples:
        text, spans = row["text"], row["spans"]
        try:
            pert.sorted_spans(spans)
        except ValueError:
            pre["overlapping_spans"] += 1
        pre["lower_changes_length"] += int(len(text.lower()) != len(text))
        pre["no_comma"] += int("," not in text)
        pre["no_comma_test"] += int("," not in text and split == "test")
        outside = pert.has_text_outside_spans(text, spans)
        pre["outside_text"] += int(outside)
        pre["outside_text_test"] += int(outside and split == "test")
    for name, flags in (("no_commas", {"no_commas": True}), ("lowercase", {"lowercase": True}),
                        ("no_commas+lowercase", {"no_commas": True, "lowercase": True})):
        fails = surface = 0
        for _, row in samples:
            try:
                new_text, new_spans = pert.transform_sample(row["text"], row["spans"], **flags)
            except ValueError:
                fails += 1
                continue
            ordered = pert.sorted_spans(row["spans"])
            ok = len(new_spans) == len(ordered) and all(
                new_text[n["start"]:n["end"]] == pert.expected_surface(row["text"][o["start"]:o["end"]], **flags)
                for o, n in zip(sorted(row["spans"], key=lambda s: (s["start"], s["end"])),
                                sorted(new_spans, key=lambda s: (s["start"], s["end"]))))
            surface += int(not ok)
        pre["offset_failures"][name], pre["surface_failures"][name] = fails, surface
    report["preconditions_400"] = pre
    if (pre["overlapping_spans"] or pre["lower_changes_length"] or any(pre["offset_failures"].values())
            or any(pre["surface_failures"].values())):
        raise RuntimeError(f"STEP0_MISMATCH preconditions {pre}")
    ctx["base"], ctx["step0"] = base, report
    return report


# ------------------------------------------------------------------ H3 / E1: test-time perturbation tables
def evaluate_conditions(ctx: dict, experiment: str, conditions: dict, control: str, crf_models: dict,
                        systems: tuple[str, ...], subsets: dict | None = None) -> tuple[list[dict], list[dict], dict]:
    """Run every system on every condition and build micro tables, per-label rows and units.

    ``conditions``: name -> list of gold dicts with the perturbed text/spans (same sample_ids).
    ``crf_models``: name -> (model_path, metadata_path); one model per condition (E1 mode b) or the same model.
    ``subsets``: name -> boolean mask over the samples (paired analysis is repeated on each).
    """
    import numpy as np
    from src.evaluation import frozen_reliability as fr
    pred_dir = ctx["interim"] / "predictions" / experiment
    golds_ref = ctx["test_gold"]
    paths: dict[str, dict[str, Path]] = {system: {} for system in systems}
    crf_items = []
    for name, golds in conditions.items():
        input_path = pred_dir / "inputs" / f"{name}.jsonl"
        write_inputs(input_path, golds)
        if "CRF-INDEP" in systems:
            model, meta = crf_models[name]
            out = pred_dir / "CRF-INDEP" / f"{name}.jsonl"
            crf_items.append({"name": name, "reuse": True, "model_path": str(model), "metadata_path": str(meta),
                              "predict": [{"inputs": str(input_path), "out": str(out)}]})
            paths["CRF-INDEP"][name] = out
        if "HEUR-JW" in systems:
            out = pred_dir / "HEUR-JW" / f"{name}.jsonl"
            heur(ctx).predict(golds, out)
            paths["HEUR-JW"][name] = out
    if crf_items:
        run_crf_job({"models": crf_items}, pred_dir / "crf_job.json")
    units = {system: {name: load_units(paths[system][name], conditions[name], ctx["test_excluded"])
                      for name in conditions} for system in systems}
    n = len(golds_ref)
    masks = {"all": np.ones(n, dtype=bool), **(subsets or {})}
    micro_rows, label_out = [], []
    for system in systems:
        for subset_name, mask in masks.items():
            if mask.sum() == 0:
                continue
            control_units = units[system][control]["totals"][mask]
            for name in conditions:
                current = units[system][name]
                row = {"experiment": experiment, "system": system, "condition": name, "subset": subset_name,
                       "control": control, **micro_row({"totals": current["totals"][mask]})}
                delta = paired_delta(fr.f1_stat, current["totals"][mask], control_units)
                row.update(delta_f1=fnum(delta.get("estimate")), delta_ci_low=fnum(delta.get("ci_low")),
                           delta_ci_high=fnum(delta.get("ci_high")), delta_status=delta.get("status"),
                           reading=verdict_from_delta(delta) if name != control else "CONTROL")
                micro_rows.append(row)
                if subset_name == "all":
                    label_out.extend(label_rows(current, {"experiment": experiment, "system": system, "condition": name}))
    return micro_rows, label_out, units


def h3_conditions(ctx: dict) -> tuple[dict, dict]:
    """Recompose the 100 test texts from their gold spans in five orders; verify every surface."""
    from src.evaluation import perturbations as pert
    orders = {"recomposed_original_order": ("original", None), "reverse": ("reverse", None),
              **{f"shuffle_seed{seed}": ("shuffle", seed) for seed in PERMUTATION_SEEDS}}
    conditions = {"original_text": [dict(g) for g in ctx["test_gold"]]}
    checks = {}
    for name, (order, seed) in orders.items():
        golds, surfaces_ok, changed, same_order = [], 0, 0, 0
        for gold in ctx["test_gold"]:
            text, spans, permutation = pert.recompose_with_order(gold["text"], gold["spans"], order, seed, gold["sample_id"])
            surfaces_ok += int(pert.verify_surfaces(gold["text"], gold["spans"], text, spans)
                               and all(text[s["start"]:s["end"]] for s in spans))
            changed += int(text != gold["text"])
            same_order += int(permutation == list(range(len(permutation))))
            golds.append(make_gold(gold, text, spans))
        checks[name] = {"samples": len(golds), "surface_preserved": surfaces_ok, "text_differs_from_original": changed,
                        "identity_permutation_samples": same_order}
        conditions[name] = golds
    outside = [pert.has_text_outside_spans(g["text"], g["spans"]) for g in ctx["test_gold"]]
    checks["_outside_text_test_samples"] = int(sum(outside))
    return conditions, checks


def run_h3(ctx: dict) -> dict:
    import numpy as np
    conditions, checks = h3_conditions(ctx)
    if any(v["surface_preserved"] != v["samples"] for k, v in checks.items() if not k.startswith("_")):
        raise RuntimeError(f"H3 surface check failed: {checks}")
    from src.evaluation import perturbations as pert
    outside = np.array([pert.has_text_outside_spans(g["text"], g["spans"]) for g in ctx["test_gold"]])
    subsets = {"outside_text_samples": outside, "no_outside_text_samples": ~outside}
    base = ctx["base"]
    models = {name: (base["model_path"], base["metadata_path"]) for name in conditions}
    micro, labels, units = evaluate_conditions(ctx, "H3", conditions, "recomposed_original_order", models,
                                               ("CRF-INDEP", "HEUR-JW"), subsets)
    csv_write(ctx["processed"] / "h3_field_order.csv", micro)
    csv_write(ctx["processed"] / "h3_field_order_per_label.csv", labels)
    return {"checks": checks, "rows": micro}


def e1_conditions(ctx: dict) -> dict:
    from src.evaluation import perturbations as pert
    grid = {"commas_keep|case_keep": {}, "commas_drop|case_keep": {"no_commas": True},
            "commas_keep|case_lower": {"lowercase": True}, "commas_drop|case_lower": {"no_commas": True, "lowercase": True}}
    return {name: {"flags": flags,
                   "test": [make_gold(g, *pert.transform_sample(g["text"], g["spans"], **flags)) for g in ctx["test_gold"]]}
            for name, flags in grid.items()}


def run_e1(ctx: dict) -> dict:
    """E1: mode a = test-time perturbation of the original model; mode b = train and test under the same condition."""
    from src.evaluation import perturbations as pert
    grid = e1_conditions(ctx)
    base = ctx["base"]
    control = "commas_keep|case_keep"
    # Mode (a): the locked model sees perturbed text only at test time.
    conditions_a = {name: item["test"] for name, item in grid.items()}
    models_a = {name: (base["model_path"], base["metadata_path"]) for name in grid}
    micro_a, labels_a, _ = evaluate_conditions(ctx, "E1a_test_time_only", conditions_a, control, models_a,
                                               ("CRF-INDEP", "HEUR-JW"))
    # Mode (b): retrain CRF with the same transformation applied to the 240 training samples.
    train_dir = ctx["interim"] / "e1b"
    items, train_report = [], {}
    for name, item in grid.items():
        rows = []
        for row in ctx["train"]:
            text, spans = pert.transform_sample(row["text"], row["spans"], **item["flags"])
            rows.append({"sample_id": row["sample_id"], "text": text, "spans": spans})
        write_train(train_dir / name / "train.jsonl", rows)
        items.append({"name": name, "train_jsonl": str(train_dir / name / "train.jsonl"),
                      "model_path": str(train_dir / name / "model.crfsuite"),
                      "metadata_path": str(train_dir / name / "model_metadata.json"), "predict": []})
    results = run_crf_job({"models": items}, train_dir / "train_job.json")
    train_report = {r["model"]: r["checkpoint_sha256"] for r in results}
    if train_report[control] != REFERENCE_CHECKPOINT_SHA256:
        raise RuntimeError("E1b control model differs from the reference checkpoint")
    models_b = {name: (train_dir / name / "model.crfsuite", train_dir / name / "model_metadata.json") for name in grid}
    micro_b, labels_b, _ = evaluate_conditions(ctx, "E1b_train_and_test", conditions_a, control, models_b, ("CRF-INDEP",))
    csv_write(ctx["processed"] / "e1_preprocessing.csv", micro_a + micro_b)
    csv_write(ctx["processed"] / "e1_preprocessing_per_label.csv", labels_a + labels_b)
    return {"rows_a": micro_a, "rows_b": micro_b, "train_checkpoints": train_report}


# ------------------------------------------------------------------ H2: missing-field augmentation
SURFACE_FIELDS = ("SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh")


def load_csv_rows(name: str) -> list[dict]:
    import csv
    with require(BENCHMARK_DIR / name).open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    needed = {"ChuoiDiaChi", *SURFACE_FIELDS}
    if rows and not needed <= set(rows[0]):
        raise ValueError(f"{name} lacks columns {sorted(needed - set(rows[0]))}")
    return rows


def starts_with_lane(value: str) -> bool:
    """Gold keeps Ngo/Hem as its own span, so rows with the lane inside TenDuong would teach a wrong convention."""
    return value.strip().casefold().startswith(LANE_PREFIXES)


def align_surface_row(row: dict, sample_id: str) -> tuple[dict | None, str | None]:
    """Spans from the surface columns aligned into ChuoiDiaChi; ambiguous/failed alignment returns a reason."""
    from src.data.span_trace import Component
    from src.data.span_trace import align_unique
    from src.evaluation.span_features import encode_gold
    components = [Component(field, row[field], row[field], "unknown") for field in SURFACE_FIELDS if row[field]]
    if not components:
        return None, "no_surface_components"
    placed, error = align_unique(row["ChuoiDiaChi"], components)
    if error:
        return None, error
    spans = [{"start": p["start"], "end": p["end"], "label": p["component"].field,
              "system": "cu" if p["component"].field == "QuanHuyen" else "khong_xac_dinh"} for p in placed]
    try:
        encode_gold(row["ChuoiDiaChi"], spans)
    except ValueError:
        return None, "token_boundary_or_roundtrip"
    return {"sample_id": sample_id, "text": row["ChuoiDiaChi"], "spans": spans}, None


def dev_test_pairs(ctx: dict) -> set:
    """Normalised (house number, street) of every dev and test gold sample, used for the address-level leak filter."""
    from src.evaluation import leak_guard as lg
    if "dev_test_surface_pairs" not in ctx:
        pairs = set()
        for gold in ctx["dev_gold"] + ctx["test_gold"]:
            by_label = {s["label"]: gold["text"][s["start"]:s["end"]] for s in gold["spans"]}
            pairs.add((lg.normalize_for_overlap(by_label.get("SoNha", "")), lg.normalize_for_overlap(by_label.get("TenDuong", ""))))
        ctx["dev_test_surface_pairs"] = pairs
    return ctx["dev_test_surface_pairs"]


def filter_chain(ctx: dict, name: str, prefix: str, with_gt: bool) -> tuple[list[dict], dict]:
    """leak_guard -> lane rows -> (SoNha, TenDuong) overlap with dev/test -> span alignment."""
    import pandas as pd
    from src.evaluation import leak_guard as lg
    rows = load_csv_rows(name)
    frame = pd.DataFrame(rows)
    counts = {"source_rows": len(frame)}
    if ctx.get("exclusion_index") is None:
        ctx["exclusion_index"] = lg.build_exclusion_index()
    kept, dropped = lg.filter_benchmark(frame, "ChuoiDiaChi", index=ctx["exclusion_index"])
    counts["after_leak_guard"] = len(kept)
    kept = kept[~kept["TenDuong"].map(starts_with_lane)]
    counts["after_lane_prefix_filter"] = len(kept)
    pairs = dev_test_pairs(ctx)
    column = ("GT_SoNha", "GT_TenDuong") if with_gt else ("SoNha", "TenDuong")
    overlap = [(lg.normalize_for_overlap(a), lg.normalize_for_overlap(b)) in pairs
               for a, b in zip(kept[column[0]], kept[column[1]])]
    kept = kept[[not flag for flag in overlap]]
    counts["after_dev_test_address_overlap"] = len(kept)
    records, reasons = [], {}
    for index, row in kept.iterrows():
        aligned, reason = align_surface_row(row.to_dict(), f"{prefix}_{index:04d}")
        if aligned is None:
            reasons[reason] = reasons.get(reason, 0) + 1
            continue
        aligned["row"] = row.to_dict()
        records.append(aligned)
    counts["alignment_dropped"] = reasons
    counts["aligned"] = len(records)
    return records, counts


def stratified_sample(rows: list[dict], key, n: int, seed_text: str) -> list[dict]:
    """Largest-remainder quota per stratum, deterministic from ``seed_text``."""
    import random
    n = min(n, len(rows))
    strata: dict[str, list[dict]] = {}
    for row in rows:
        strata.setdefault(key(row), []).append(row)
    quota = {k: n * len(v) / len(rows) for k, v in strata.items()}
    take = {k: min(int(q), len(strata[k])) for k, q in quota.items()}
    for k in sorted(quota, key=lambda k: (-(quota[k] - int(quota[k])), k))[: n - sum(take.values())]:
        take[k] = min(take[k] + 1, len(strata[k]))
    rng = random.Random(seed_text)
    chosen = []
    for k in sorted(strata):
        bucket = sorted(strata[k], key=lambda r: r["sample_id"])
        rng.shuffle(bucket)
        chosen.extend(bucket[: take[k]])
    return sorted(chosen, key=lambda r: r["sample_id"])


def build_h2_design(ctx: dict) -> dict:
    import random
    from collections import Counter
    from src.evaluation import leak_guard as lg
    d04, counts04 = filter_chain(ctx, "04_missing_fields_800.csv", "d04", with_gt=True)
    for record in d04:
        row = record["row"]
        record.update(KieuThieu=row["KieuThieu"], HeQuyChieu=row["HeQuyChieu"],
                      group_key=lg.admin_group_key(row["GT_TinhThanh"], row["GT_QuanHuyen"], row["GT_PhuongXa"]),
                      gt={f: row[f"GT_{f}"] for f in SURFACE_FIELDS}, surface={f: row[f] for f in SURFACE_FIELDS})
    adm_keys = sorted({r["group_key"] for r in d04 if r["group_key"].startswith("ADM|")})
    shuffled = list(adm_keys)
    random.Random(SEED).shuffle(shuffled)
    held_adm = set(shuffled[: round(HELDOUT_GROUP_SHARE * len(shuffled))])
    heldout = [r for r in d04 if not r["group_key"].startswith("ADM|") or r["group_key"] in held_adm]
    aug_train = [r for r in d04 if r["group_key"].startswith("ADM|") and r["group_key"] not in held_adm]
    assert not ({r["group_key"] for r in heldout} & {r["group_key"] for r in aug_train})

    pool, pool_counts = [], {}
    for name, prefix in (("01_full_address_new_verified.csv", "d01"), ("03_real_address_old_1500.csv", "d03")):
        records, counts = filter_chain(ctx, name, prefix, with_gt=False)
        for record in records:
            record.update(HeQuyChieu=record["row"]["HeQuyChieu"], surface={f: record["row"][f] for f in SURFACE_FIELDS},
                          group_key=None)
        pool.extend(records)
        pool_counts[name] = counts
    cu_share = sum(r["HeQuyChieu"] == "cu" for r in heldout) / len(heldout)
    eval_full = stratified_sample(pool, lambda r: r["HeQuyChieu"], EVAL_FULL_SIZE, f"{SEED}|eval_full")
    used = {r["sample_id"] for r in eval_full}
    train_pool = [r for r in pool if r["sample_id"] not in used]

    def describe(rows):
        return {"rows": len(rows), "groups": len({r["group_key"] for r in rows}),
                "KieuThieu": dict(Counter(r["KieuThieu"] for r in rows)), "HeQuyChieu": dict(Counter(r["HeQuyChieu"] for r in rows)),
                "unresolved_rows": sum(r["group_key"].startswith("UNRESOLVED|") for r in rows)}

    surface_pairs = ctx["dev_test_surface_pairs"]
    surface_overlap = sum((lg.normalize_for_overlap(r["surface"]["SoNha"]), lg.normalize_for_overlap(r["surface"]["TenDuong"]))
                          in surface_pairs for r in d04)
    design = {"data04": counts04, "surface_pair_overlap_rows_kept": surface_overlap, "pool": pool_counts, "adm_groups": len(adm_keys), "heldout_adm_groups": len(held_adm),
              "all_aligned": {**describe(d04), "largest_group_share": max(Counter(r["group_key"] for r in d04).values()) / len(d04)},
              "heldout_missing": describe(heldout), "aug_train": describe(aug_train),
              "groups_disjoint": True, "eval_full": {"rows": len(eval_full), "HeQuyChieu": dict(Counter(r["HeQuyChieu"] for r in eval_full)),
                                                      "requested_stratification": "proportional to the pool"},
              "train_pool_rows": len(train_pool), "heldout_cu_share": cu_share}
    ctx["h2"] = {"d04": d04, "heldout": heldout, "aug_train": aug_train, "eval_full": eval_full, "train_pool": train_pool}
    return design


def five_field_units(prediction_path: Path, rows: list[dict], truth_key: str):
    """Per-sample (tp, fp, fn) of the 5-field scorer; ``truth_key`` selects the GT silver or the surface truth."""
    import numpy as np
    from src.evaluation.dev_runner import load_predictions
    from src.evaluation.scorer import score_prediction_pair
    predictions = {p.sample_id: p for p in load_predictions(prediction_path)}
    if set(predictions) != {r["sample_id"] for r in rows}:
        raise ValueError("Prediction ids differ from the evaluation rows")
    out = []
    for row in rows:
        score = score_prediction_pair(predictions[row["sample_id"]].to_standard_5_fields().to_dict(), row[truth_key])
        out.append((score["tp"], score["fp"], score["fn"]))
    return np.asarray(out, dtype=np.int64)


def cluster_f1(units, clusters) -> dict:
    from src.evaluation import frozen_reliability as fr
    from src.evaluation import stats
    return stats.cluster_bootstrap_ci(fr.f1_stat, units, clusters, fr.N_RESAMPLES, seed=SEED)


def run_h2(ctx: dict) -> dict:
    from collections import Counter
    import numpy as np
    from src.evaluation import frozen_reliability as fr
    design = build_h2_design(ctx)
    h2 = ctx["h2"]
    base_rows = [{"sample_id": r["sample_id"], "text": r["text"], "spans": r["spans"]} for r in ctx["train"]]
    root = ctx["interim"] / "h2"
    write_inputs(root / "inputs/test.jsonl", ctx["test_gold"])
    write_inputs(root / "inputs/dev.jsonl", ctx["dev_gold"])
    write_inputs(root / "inputs/heldout.jsonl", h2["heldout"])
    write_inputs(root / "inputs/eval_full.jsonl", h2["eval_full"])
    # Training sets: BASE plus three augmentation families, N and subset seed declared in the manifest.
    models, composition = {}, {}
    models["BASE"] = base_rows
    for seed in SUBSET_SEEDS:
        for n in AUG_SIZES:
            aug = stratified_sample(h2["aug_train"], lambda r: r["KieuThieu"], n, f"{seed}|{n}|missing")
            n_cu = sum(r["HeQuyChieu"] == "cu" for r in aug)
            pool_cu = [r for r in h2["train_pool"] if r["HeQuyChieu"] == "cu"]
            pool_moi = [r for r in h2["train_pool"] if r["HeQuyChieu"] == "moi"]
            full = (stratified_sample(pool_cu, lambda r: "x", n_cu, f"{seed}|{n}|full_cu")
                    + stratified_sample(pool_moi, lambda r: "x", len(aug) - n_cu, f"{seed}|{n}|full_moi"))
            full = sorted(full, key=lambda r: r["sample_id"])
            tag = f"N{n}_s{seed}"
            models[f"AUG-MISSING_{tag}"] = base_rows + [{k: r[k] for k in ("sample_id", "text", "spans")} for r in aug]
            models[f"AUG-FULL_{tag}"] = base_rows + [{k: r[k] for k in ("sample_id", "text", "spans")} for r in full]
            heldout_keys = {r["group_key"] for r in h2["heldout"]}
            composition[tag] = {"requested_N": n, "actual_N_missing": len(aug), "actual_N_full": len(full),
                                "missing_KieuThieu": dict(sorted(Counter(r["KieuThieu"] for r in aug).items())),
                                "missing_HeQuyChieu": {"cu": n_cu, "moi": len(aug) - n_cu},
                                "aug_missing_groups": len({r["group_key"] for r in aug}),
                                "aug_missing_groups_in_heldout": len({r["group_key"] for r in aug} & heldout_keys)}
    items = []
    for name, rows in models.items():
        write_train(root / "train" / f"{name}.jsonl", rows)
        pred = root / "predictions" / name
        items.append({"name": name, "train_jsonl": str(root / "train" / f"{name}.jsonl"),
                      "model_path": str(root / "models" / name / "model.crfsuite"),
                      "metadata_path": str(root / "models" / name / "model_metadata.json"),
                      "predict": [{"inputs": str(root / f"inputs/{part}.jsonl"), "out": str(pred / f"{part}.jsonl")}
                                  for part in ("test", "dev", "heldout", "eval_full")]})
    results = {r["model"]: r["checkpoint_sha256"] for r in run_crf_job({"models": items}, root / "train_job.json")}
    if results["BASE"] != REFERENCE_CHECKPOINT_SHA256:
        raise RuntimeError("H2 BASE model differs from the reference checkpoint")

    held_clusters = [r["group_key"] for r in h2["heldout"]]
    kieu = np.array([r["KieuThieu"] for r in h2["heldout"]])
    sources = fr.load_source_datasets()
    is_04 = np.array([sources[g["sample_id"]] == "04_missing" for g in ctx["test_gold"]])
    design["test_04_missing_samples"] = int(is_04.sum())
    rows_out, delta_out, drop_out, td_out = [], [], [], []
    held_units, full_units, test_units, dev_units = {}, {}, {}, {}
    for name in models:
        pred = root / "predictions" / name
        held_units[name] = {t: five_field_units(pred / "heldout.jsonl", h2["heldout"], t) for t in ("gt", "surface")}
        full_units[name] = five_field_units(pred / "eval_full.jsonl", h2["eval_full"], "surface")
        test_units[name] = load_units(pred / "test.jsonl", ctx["test_gold"], ctx["test_excluded"])
        dev_units[name] = load_units(pred / "dev.jsonl", ctx["dev_gold"], ctx["dev_excluded"])
    subsets = {"all": np.ones(len(kieu), dtype=bool), **{k: kieu == k for k in sorted(set(kieu))}}

    def parse(name):
        if name == "BASE":
            return "BASE", None, None
        family, tag = name.split("_", 1)
        return family, int(tag.split("_")[0][1:]), int(tag.split("_s")[1])

    for name in models:
        family, n, seed = parse(name)
        for truth in ("gt", "surface"):
            for subset, mask in subsets.items():
                units = held_units[name][truth][mask]
                clusters = [c for c, keep in zip(held_clusters, mask) if keep]
                ci = cluster_f1(units, clusters)
                rows_out.append({"truth": truth, "subset": subset, "model": family, "N": n, "subset_seed": seed,
                                 "n_rows": int(mask.sum()), "n_groups": len(set(clusters)), "tp": int(units[:, 0].sum()),
                                 "fp": int(units[:, 1].sum()), "fn": int(units[:, 2].sum()), "f1": fnum(ci.get("estimate")),
                                 "ci_low": fnum(ci.get("ci_low")), "ci_high": fnum(ci.get("ci_high")), "ci_status": ci.get("status"),
                                 "flag": fr.support_flag(int(mask.sum()))})
        # Does the model drop on missing-field addresses relative to full ones of the same source family?
        drop = unpaired_delta(fr.f1_stat, held_units[name]["surface"], full_units[name], held_clusters)
        drop_out.append({"model": family, "N": n, "subset_seed": seed, "heldout_surface_f1": fnum(fr.f1_stat(held_units[name]["surface"])),
                         "full_surface_f1": fnum(fr.f1_stat(full_units[name])), "delta_missing_minus_full": fnum(drop.get("estimate")),
                         "ci_low": fnum(drop.get("ci_low")), "ci_high": fnum(drop.get("ci_high")), "n_missing": len(kieu),
                         "n_full": len(h2["eval_full"]), "reading": verdict_from_delta(drop)})
        t = test_units[name]
        for subset, mask in (("04_missing_20", is_04), ("other_80", ~is_04), ("all_100", np.ones(len(is_04), dtype=bool))):
            ci = first_ci(fr.f1_stat, t["totals"][mask])
            td_out.append({"split": "test", "subset": subset, "label": "POST_HOC_SECONDARY", "model": family, "N": n, "subset_seed": seed,
                           "n_samples": int(mask.sum()), "f1": fnum(ci.get("estimate")), "ci_low": fnum(ci.get("ci_low")),
                           "ci_high": fnum(ci.get("ci_high")), "ci_status": ci.get("status")})
        ci = first_ci(fr.f1_stat, dev_units[name]["totals"])
        td_out.append({"split": "dev", "subset": "all_60", "label": "NO_DEGRADATION_CHECK", "model": family, "N": n, "subset_seed": seed,
                       "n_samples": len(dev_units[name]["totals"]), "f1": fnum(ci.get("estimate")), "ci_low": fnum(ci.get("ci_low")),
                       "ci_high": fnum(ci.get("ci_high")), "ci_status": ci.get("status")})

    base_test, base_dev = test_units["BASE"]["totals"], dev_units["BASE"]["totals"]
    masks_test = {"04_missing_20": is_04, "other_80": ~is_04, "all_100": np.ones(len(is_04), dtype=bool)}
    for row in td_out:
        if row["model"] == "BASE":
            continue
        name = f"{row['model']}_N{row['N']}_s{row['subset_seed']}"
        if row["split"] == "test":
            mask = masks_test[row["subset"]]
            delta = paired_delta(fr.f1_stat, test_units[name]["totals"][mask], base_test[mask])
        else:
            delta = paired_delta(fr.f1_stat, dev_units[name]["totals"], base_dev)
        row.update(delta_vs_base=fnum(delta.get("estimate")), delta_ci_low=fnum(delta.get("ci_low")),
                   delta_ci_high=fnum(delta.get("ci_high")), delta_reading=verdict_from_delta(delta))
    comparisons = (("AUG-MISSING", "BASE"), ("AUG-FULL", "BASE"), ("AUG-MISSING", "AUG-FULL"))
    for seed in SUBSET_SEEDS:
        for n in AUG_SIZES:
            tag = f"N{n}_s{seed}"
            names = {"BASE": "BASE", "AUG-MISSING": f"AUG-MISSING_{tag}", "AUG-FULL": f"AUG-FULL_{tag}"}
            for left, right in comparisons:
                for truth in ("gt", "surface"):
                    for subset, mask in subsets.items():
                        clusters = [c for c, keep in zip(held_clusters, mask) if keep]
                        delta = paired_delta(fr.f1_stat, held_units[names[left]][truth][mask],
                                             held_units[names[right]][truth][mask], cluster_ids=clusters)
                        delta_out.append({"truth": truth, "subset": subset, "N": n, "subset_seed": seed,
                                          "comparison": f"{left} - {right}", "n_rows": int(mask.sum()),
                                          "delta_f1": fnum(delta.get("estimate")), "ci_low": fnum(delta.get("ci_low")),
                                          "ci_high": fnum(delta.get("ci_high")), "status": delta.get("status"),
                                          "reading": verdict_from_delta(delta)})
    csv_write(ctx["processed"] / "h2_heldout_missing.csv", rows_out)
    csv_write(ctx["processed"] / "h2_paired_deltas.csv", delta_out)
    csv_write(ctx["processed"] / "h2_drop_vs_full.csv", drop_out)
    csv_write(ctx["processed"] / "h2_test_dev.csv", td_out)
    summary = []
    for family in ("BASE", "AUG-MISSING", "AUG-FULL"):
        for n in ((None,) if family == "BASE" else AUG_SIZES):
            for truth in ("gt", "surface"):
                values = [r["f1"] for r in rows_out if r["model"] == family and r["N"] == n and r["truth"] == truth
                          and r["subset"] == "all"]
                mean = sum(values) / len(values)
                std = (sum((v - mean) ** 2 for v in values) / (len(values) - 1)) ** 0.5 if len(values) > 1 else None
                summary.append({"model": family, "N": n, "truth": truth, "n_subset_seeds": len(values), "mean_f1": fnum(mean),
                                "std_f1": fnum(std), "min_f1": fnum(min(values)), "max_f1": fnum(max(values))})
    csv_write(ctx["processed"] / "h2_summary_over_subset_seeds.csv", summary)
    write_jsonl(ctx["processed"] / "h2_training_data_ids.jsonl",
                [{"model": name, "sample_ids": [r["sample_id"] for r in rows if r["sample_id"].startswith("d0")]} for name, rows in models.items()])
    return {"design": design, "composition": composition, "checkpoints": results, "summary": summary, "drop": drop_out,
            "deltas": delta_out, "rows": rows_out, "test_dev": td_out}


# ------------------------------------------------------------------ H4: label groups
LABEL_GROUPS = {"administrative": ("PhuongXa", "QuanHuyen", "TinhThanh"),
                "road": ("SoNha", "TenDuong", "Ngo/Hem"),
                "landmark": ("MocDinhVi", "HuongDi"),
                "other": ("ToaNha/CanHo", "GhiChu", "Khac")}


def group_counts(units: dict, labels: tuple[str, ...]):
    """Per-sample (tp, fp, fn) summed over the labels of one group."""
    from src.evaluation.schema import SPAN11_LABELS
    index = [SPAN11_LABELS.index(label) for label in labels]
    return units["by_label"][:, index, :].sum(axis=1)


def group_table(units: dict, extra: dict) -> list[dict]:
    from src.evaluation import frozen_reliability as fr
    rows = []
    for group, labels in LABEL_GROUPS.items():
        counts = group_counts(units, labels)
        support = int(counts[:, 0].sum() + counts[:, 2].sum())
        flag = fr.support_flag(support)
        row = {**extra, "group": group, "labels": "|".join(labels), "gold_support": support, "support_flag": flag,
               "n_samples": len(counts), "tp": int(counts[:, 0].sum()), "fp": int(counts[:, 1].sum()), "fn": int(counts[:, 2].sum())}
        if support == 0:
            row.update(precision=None, recall=None, f1=None, status="NOT_EVALUABLE_NO_GOLD_SUPPORT" if extra.get("kind") == "test"
                       else "NOT_EVALUABLE_NO_SUPPORT")
        else:
            for name, stat in (("precision", fr.precision_stat), ("recall", fr.recall_stat), ("f1", fr.f1_stat)):
                ci = first_ci(stat, counts)
                row[name] = fnum(ci.get("estimate"))
                row[f"{name}_ci_low"], row[f"{name}_ci_high"] = fnum(ci.get("ci_low")), fnum(ci.get("ci_high"))
            row["status"] = flag if flag != "OK" else "OK"
        rows.append(row)
    return rows


def kfold_reference(ctx: dict) -> dict:
    """Group k-fold (source_group, seed 42) of the locked CRF on the 240 train samples: reference for the landmark group."""
    import random
    import numpy as np
    from src.evaluation import frozen_reliability as fr
    from src.evaluation.dev_runner import load_predictions
    groups = {}
    for row in ctx["train"]:
        groups.setdefault(ctx["registry"][row["sample_id"]]["source_group"], []).append(row)
    order = sorted(groups)
    random.Random(KFOLD_SEED).shuffle(order)
    folds = [[] for _ in range(KFOLD_K)]
    for position, key in enumerate(order):          # round-robin over shuffled groups
        folds[position % KFOLD_K].extend(groups[key])
    root = ctx["interim"] / "kfold"
    items = []
    for k, held in enumerate(folds):
        held_ids = {r["sample_id"] for r in held}
        write_train(root / f"fold{k}/train.jsonl", [r for r in ctx["train"] if r["sample_id"] not in held_ids])
        write_inputs(root / f"fold{k}/heldout.jsonl", held)
        items.append({"name": f"fold{k}", "train_jsonl": str(root / f"fold{k}/train.jsonl"),
                      "model_path": str(root / f"fold{k}/model.crfsuite"), "metadata_path": str(root / f"fold{k}/model_metadata.json"),
                      "predict": [{"inputs": str(root / f"fold{k}/heldout.jsonl"), "out": str(root / f"fold{k}/predictions.jsonl")}]})
    run_crf_job({"models": items}, root / "job.json")
    predictions = [p for k in range(KFOLD_K) for p in load_predictions(root / f"fold{k}/predictions.jsonl")]
    golds = [row for fold in folds for row in fold]
    units = fr.build_units(predictions, golds, [])
    table = group_table(units, {"system": "CRF-INDEP", "kind": "kfold_train240", "scope": f"group_{KFOLD_K}fold_seed{KFOLD_SEED}"})
    for row in table:   # declared reference only: landmark/other have a handful of gold spans, no conclusion is drawn
        if row["group"] in ("landmark", "other"):
            row["status"] = row["support_flag"] = "LOW_SUPPORT"
    return {"rows": table, "fold_sizes": [len(f) for f in folds], "n_groups": len(order),
            "micro_f1": fnum(fr.f1_stat(units["totals"]))}


def run_h4(ctx: dict) -> dict:
    import numpy as np
    from src.evaluation import frozen_reliability as fr
    from src.evaluation import stats
    from src.evaluation.dev_runner import load_predictions
    paths = fr.test_prediction_paths()
    rows, delta_rows, systems_units = [], [], {}
    for system in fr.SYSTEMS:
        units = fr.build_units(load_predictions(paths[system]), ctx["test_gold"], ctx["test_excluded"])
        systems_units[system] = units
        rows.extend(group_table(units, {"system": system, "kind": "test", "scope": "frozen_test_100"}))
        admin, road = group_counts(units, LABEL_GROUPS["administrative"]), group_counts(units, LABEL_GROUPS["road"])
        paired = np.concatenate([admin, road], axis=1)
        stat = lambda u: fr.f1_stat(u[:, :3]) - fr.f1_stat(u[:, 3:])
        ci = stats.bootstrap_ci(stat, paired, fr.N_RESAMPLES, seed=SEED)
        delta_rows.append({"system": system, "comparison": "administrative F1 - road F1", "n_samples": len(paired),
                           "admin_f1": fnum(fr.f1_stat(admin)), "road_f1": fnum(fr.f1_stat(road)),
                           "delta": fnum(ci.get("estimate")), "ci_low": fnum(ci.get("ci_low")), "ci_high": fnum(ci.get("ci_high")),
                           "status": ci.get("status"), "reading": verdict_from_delta(ci)})
    reference = kfold_reference(ctx)
    csv_write(ctx["processed"] / "h4_label_groups.csv", rows + reference["rows"])
    csv_write(ctx["processed"] / "h4_admin_vs_road.csv", delta_rows)
    return {"rows": rows, "delta": delta_rows, "kfold": reference}


# ------------------------------------------------------------------ orchestration
def json_clean(value):
    """NaN/inf become None so metrics.json stays strict JSON."""
    import math
    if isinstance(value, dict):
        return {str(k): json_clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_clean(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        return json_clean(value.item())
    return value


def run_all(args: argparse.Namespace) -> None:
    started = time.time()
    interim, processed = Path(args.interim_dir), Path(args.processed_dir)
    ctx = build_context(interim, processed)
    manifest = declared_manifest(ctx)
    write_json(processed / "run_manifest.json", manifest)      # declared before any scoring
    results = {"step0": step0(ctx)}
    results["H3"] = run_h3(ctx)
    results["E1"] = run_e1(ctx)
    results["H2"] = run_h2(ctx)
    results["H4"] = run_h4(ctx)
    write_json(processed / "metrics.json", json_clean(results))
    outputs = {p.name: sha256_file(p) for p in sorted(processed.iterdir()) if p.name != "run_manifest.json"}
    prediction_hashes = {str(p.relative_to(interim)): sha256_file(p) for p in sorted(interim.rglob("*.jsonl"))
                         if "predictions" in p.parts}
    manifest.update(status="COMPLETE", finished_at_utc=datetime.now(timezone.utc).isoformat(),
                    elapsed_seconds=round(time.time() - started, 1), outputs_sha256=outputs,
                    interim_prediction_sha256=prediction_hashes,
                    reproduction={"command": "python -m scripts.71_run_cpu_hypothesis_experiments run --interim-dir D --processed-dir D"})
    write_json(processed / "run_manifest.json", manifest)
    print(json.dumps({"status": "COMPLETE", "elapsed_seconds": manifest["elapsed_seconds"], "outputs": len(outputs)}))


# ------------------------------------------------------------------ Tier 2: neural inference only (local retrained checkpoints)
NEURAL_PYTHON = ROOT / "data/interim/modeling/sprint03/runtime_neural_d_v1/bin/python"
MULTISEED_INTERIM = ROOT / "data/interim/modeling/sprint04/multiseed_20261015_v1"
TIER2_SEEDS = (42, 1337, 2025)
TIER2_MODELS = {"pcrf": ("PHOBERT-CRF", "pcrf"), "dyn": ("PROPOSED-DYN", "dyn")}   # model key -> (system, variant)
TIER2_LABEL = "LOCAL_CPU_RETRAINED"       # not the locked Sprint 3 Kaggle checkpoints
TIER2_CONTROL_H3, TIER2_CONTROL_E1 = "recomposed_original_order", "commas_keep|case_keep"


def tier2_dirs(processed: Path, interim: Path) -> tuple[Path, Path]:
    return processed / "tier2_local_neural", interim / "tier2"


def tier2_conditions(light_ctx: dict) -> dict:
    """The nine text conditions: original, five H3 orders, three E1 test-time preprocessings."""
    h3, checks = h3_conditions(light_ctx)
    e1 = e1_conditions(light_ctx)
    conditions = {"original_text": h3["original_text"]}
    conditions.update({k: v for k, v in h3.items() if k != "original_text"})
    conditions.update({k: v["test"] for k, v in e1.items() if k != TIER2_CONTROL_E1})
    return conditions


def light_context() -> dict:
    from src.evaluation import frozen_reliability as fr
    gold, excluded = fr.load_gold("test")
    return {"test_gold": gold, "test_excluded": excluded}


def tier2_prepare(processed: Path, interim: Path) -> dict:
    out_processed, out_interim = tier2_dirs(processed, interim)
    for directory in (out_processed, out_interim):
        if directory.exists():
            raise FileExistsError(f"Refusing to overwrite {directory}")
    light = light_context()
    conditions = tier2_conditions(light)
    for name, golds in conditions.items():
        write_inputs(out_interim / "inputs" / f"{name}.jsonl", golds)
    out_processed.mkdir(parents=True)
    manifest = {
        "run_id": "tier2_local_neural", "status": "DECLARED_BEFORE_SCORING", "label": TIER2_LABEL,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "models": {k: {"system": s, "variant": v} for k, (s, v) in TIER2_MODELS.items()}, "seeds": list(TIER2_SEEDS),
        "conditions": list(conditions), "controls": {"H3": TIER2_CONTROL_H3, "E1": TIER2_CONTROL_E1},
        "decoder_policy": "locked WP3b inference_config (threshold 0.7, margin 0.2); no tuning",
        "checkpoint_sha256": {f"{m}_seed{s}": sha256_file(MULTISEED_INTERIM / f"{m}_seed{s}/checkpoints/best.pt")
                              for m in TIER2_MODELS for s in TIER2_SEEDS if (MULTISEED_INTERIM / f"{m}_seed{s}/checkpoints/best.pt").exists()},
        "input_sha256": {name: sha256_file(out_interim / "inputs" / f"{name}.jsonl") for name in conditions},
        "code_sha256": {name: sha256_file(ROOT / name) for name in SOURCE_FILES},
        "test_status": "Sprint 3 test already observed: post-hoc robustness analysis only",
        "smoke_rule": "original_text predictions must equal the WP3b test prediction of the same checkpoint (spans and T1)",
    }
    write_json(out_processed / "run_manifest.json", manifest)
    return manifest


def tier2_worker(model: str, seed: int, interim: Path, only: str | None) -> None:
    """Neural runtime, one checkpoint per process: load once, predict every condition (text only)."""
    import importlib
    sys.path.insert(0, str(ROOT))
    multiseed = importlib.import_module("scripts.70_run_multiseed_local")
    multiseed._set_threads()
    system, variant = TIER2_MODELS[model]
    run_dir = MULTISEED_INTERIM / multiseed.run_name(model, seed)
    config = multiseed.inference_config(model, seed, variant, run_dir)
    module, name = config["adapter_factory"].split(":")
    started = time.time()
    adapter = getattr(importlib.import_module(module), name)(**config["adapter_kwargs"])
    loaded = time.time() - started
    out_dir = tier2_dirs(Path("."), interim)[1] / f"{model}_seed{seed}"
    out_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted((tier2_dirs(Path("."), interim)[1] / "inputs").glob("*.jsonl")):
        if only and path.stem != only:
            continue
        target = out_dir / path.name
        if target.exists():
            raise FileExistsError(f"Refusing to overwrite {target}")
        rows = []
        for sample in read_jsonl(path):
            output = adapter.parse_spans(sample["text"])       # text only
            output.sample_id, output.latency_ms = sample["sample_id"], 0.0
            rows.append(output.to_dict())
        write_jsonl(target, rows)
    write_json(out_dir / f"worker_{only or 'all'}.json", {"model": model, "seed": seed, "load_seconds": round(loaded, 1),
                                                           "total_seconds": round(time.time() - started, 1)})


def tier2_run(args: argparse.Namespace) -> None:
    """Start one worker process per checkpoint, sequentially (each owns the 6 CPU threads)."""
    import importlib
    multiseed = importlib.import_module("scripts.70_run_multiseed_local")
    env = multiseed.worker_env()
    interim = Path(args.interim_dir)
    for seed in TIER2_SEEDS:
        for model in TIER2_MODELS:
            if (args.only_model and model != args.only_model) or (args.only_seed and seed != args.only_seed):
                continue
            log = interim / "tier2" / "logs" / f"{model}_seed{seed}_{args.only or 'all'}.log"
            log.parent.mkdir(parents=True, exist_ok=True)
            cmd = [str(NEURAL_PYTHON), "-m", "scripts.71_run_cpu_hypothesis_experiments", "tier2-worker",
                   "--model", model, "--seed", str(seed), "--interim-dir", str(interim)] + (["--only", args.only] if args.only else [])
            with log.open("w", encoding="utf-8") as handle:
                code = subprocess.run(cmd, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT).returncode
            print(json.dumps({"model": model, "seed": seed, "exit_code": code, "log": str(log)}), flush=True)
            if code != 0:
                raise RuntimeError(f"tier2 worker failed for {model} seed {seed}; see {log}")


def tier2_smoke(interim: Path) -> dict:
    """original_text predictions of every available checkpoint vs the WP3b test predictions."""
    from src.evaluation.dev_runner import load_predictions
    report = {}
    for model, (system, variant) in TIER2_MODELS.items():
        for seed in TIER2_SEEDS:
            new = tier2_dirs(Path("."), interim)[1] / f"{model}_seed{seed}" / "original_text.jsonl"
            old = MULTISEED_INTERIM / f"{model}_seed{seed}" / f"test_{variant}" / "predictions.jsonl"
            if not new.exists() or not old.exists():
                report[f"{model}_seed{seed}"] = "NOT_RUN"
                continue
            a, b = load_predictions(new), load_predictions(old)
            same_spans = span_keys(a) == span_keys(b)
            same_t1 = [(p.predicted_system, p.abstain) for p in a] == [(p.predicted_system, p.abstain) for p in b]
            report[f"{model}_seed{seed}"] = {"spans_equal": same_spans, "t1_equal": same_t1, "n": len(a)}
    return report


def tier2_score(processed: Path, interim: Path) -> dict:
    import numpy as np
    from src.evaluation import frozen_reliability as fr
    out_processed, out_interim = tier2_dirs(processed, interim)
    light = light_context()
    conditions = tier2_conditions(light)
    smoke = tier2_smoke(interim)
    rows, label_rows_out, available = [], [], {}
    for model, (system, _) in TIER2_MODELS.items():
        for seed in TIER2_SEEDS:
            run = out_interim / f"{model}_seed{seed}"
            if not all((run / f"{name}.jsonl").exists() for name in conditions):
                continue
            check = smoke[f"{model}_seed{seed}"]
            if check == "NOT_RUN" or not (check["spans_equal"] and check["t1_equal"]):
                raise RuntimeError(f"Smoke check failed for {model} seed {seed}: {check}")
            units = {name: load_units(run / f"{name}.jsonl", golds, light["test_excluded"]) for name, golds in conditions.items()}
            available[(model, seed)] = units
            for experiment, control, names in (
                    ("H3", TIER2_CONTROL_H3, [n for n in conditions if n == TIER2_CONTROL_H3 or n.startswith(("reverse", "shuffle"))]),
                    ("E1a", "original_text", ["original_text"] + [n for n in conditions if "|" in n])):
                for name in names:
                    cur = units[name]
                    delta = paired_delta(fr.f1_stat, cur["totals"], units[control]["totals"])
                    row = {"label": TIER2_LABEL, "experiment": experiment, "system": system, "seed": seed, "condition": name,
                           "control": control, **micro_row({"totals": cur["totals"]}), "delta_f1": fnum(delta.get("estimate")),
                           "delta_ci_low": fnum(delta.get("ci_low")), "delta_ci_high": fnum(delta.get("ci_high")),
                           "reading": "CONTROL" if name == control else verdict_from_delta(delta)}
                    rows.append(row)
                    label_rows_out.extend(label_rows(cur, {"label": TIER2_LABEL, "experiment": experiment, "system": system,
                                                          "seed": seed, "condition": name}))
    summary = []
    for model, (system, _) in TIER2_MODELS.items():
        for experiment in ("H3", "E1a"):
            for name in dict.fromkeys(r["condition"] for r in rows if r["experiment"] == experiment):
                mine = [r for r in rows if r["system"] == system and r["experiment"] == experiment and r["condition"] == name]
                if not mine:
                    continue
                f1 = [r["f1"] for r in mine]
                d = [r["delta_f1"] for r in mine]
                std = lambda v: float(np.std(v, ddof=1)) if len(v) > 1 else None
                summary.append({"label": TIER2_LABEL, "experiment": experiment, "system": system, "condition": name,
                                "n_seeds": len(mine), "f1_per_seed": json.dumps(f1), "f1_mean": fnum(np.mean(f1)),
                                "f1_std": fnum(std(f1)), "delta_mean": fnum(np.mean(d)), "delta_std": fnum(std(d)),
                                "seeds_with_delta_ci_excluding_0": sum(r["reading"].endswith("EXCLUDES_0") for r in mine)})
    status = "COMPLETE" if len(available) == len(TIER2_MODELS) * len(TIER2_SEEDS) else ("PARTIAL" if available else "NOT_RUN")
    blockers = sorted({line.strip() for log in (out_interim / "logs").glob("*.log") if log.exists()
                       for line in log.read_text(encoding="utf-8", errors="replace").splitlines()
                       if line.strip().startswith("RuntimeError:")})
    csv_write(out_processed / "tier2_per_checkpoint.csv", rows)
    csv_write(out_processed / "tier2_per_checkpoint_per_label.csv", label_rows_out)
    csv_write(out_processed / "tier2_mean_std.csv", summary)
    write_json(out_processed / "tier2_metrics.json", json_clean({"status": status, "blockers_seen_in_worker_logs": blockers, "smoke": smoke,
                                                                "checkpoints_scored": [f"{m}_seed{s}" for m, s in available]}))
    manifest = json.loads((out_processed / "run_manifest.json").read_text(encoding="utf-8"))
    manifest.update(status=status, finished_at_utc=datetime.now(timezone.utc).isoformat(),
                    outputs_sha256={p.name: sha256_file(p) for p in sorted(out_processed.iterdir()) if p.name != "run_manifest.json"},
                    prediction_sha256={str(p.relative_to(out_interim)): sha256_file(p) for p in sorted(out_interim.glob("*_seed*/*.jsonl"))})
    write_json(out_processed / "run_manifest.json", manifest)
    return {"status": status, "scored": len(available), "smoke": smoke}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("worker", help="internal: CRF train/predict job").add_argument("job", type=Path)
    run = sub.add_parser("run", help="Tier 1: H3, E1, H2, H4 on CPU")
    run.add_argument("--interim-dir", type=Path, default=DEFAULT_INTERIM)
    run.add_argument("--processed-dir", type=Path, default=DEFAULT_PROCESSED)
    for name, help_text in (("tier2-prepare", "write the nine conditions and the declared manifest"),
                            ("tier2-run", "launch one neural worker per checkpoint (sequential)"),
                            ("tier2-score", "score finished checkpoints; PARTIAL when some are missing")):
        item = sub.add_parser(name, help=help_text)
        item.add_argument("--interim-dir", type=Path, default=DEFAULT_INTERIM)
        item.add_argument("--processed-dir", type=Path, default=DEFAULT_PROCESSED)
        if name == "tier2-run":
            item.add_argument("--only", help="run a single condition (smoke: original_text)")
            item.add_argument("--only-model", choices=sorted(TIER2_MODELS))
            item.add_argument("--only-seed", type=int, choices=TIER2_SEEDS)
    worker2 = sub.add_parser("tier2-worker", help="internal: one neural checkpoint")
    worker2.add_argument("--model", required=True, choices=sorted(TIER2_MODELS))
    worker2.add_argument("--seed", type=int, required=True, choices=TIER2_SEEDS)
    worker2.add_argument("--interim-dir", type=Path, required=True)
    worker2.add_argument("--only")
    args = parser.parse_args()
    if args.command == "worker":
        worker_main(args.job)
    elif args.command == "run":
        run_all(args)
    elif args.command == "tier2-prepare":
        tier2_prepare(args.processed_dir, args.interim_dir)
    elif args.command == "tier2-run":
        tier2_run(args)
    elif args.command == "tier2-worker":
        tier2_worker(args.model, args.seed, args.interim_dir, args.only)
    elif args.command == "tier2-score":
        print(json.dumps(json_clean(tier2_score(args.processed_dir, args.interim_dir)), ensure_ascii=False))


if __name__ == "__main__":
    main()
