"""WP3b: multi-seed local CPU training of PHOBERT-CRF and PROPOSED-DYN (candidate c02), then frozen scoring.

Run everything with the neural runtime (Python 3.11, torch CPU); every worker is its own process because
py-vncorenlp can create one JVM per interpreter:

    data/interim/modeling/sprint03/runtime_neural_d_v1/bin/python -m scripts.70_run_multiseed_local run-all
    ... preflight | train --model M --seed S | infer --model M --seed S --variant V | score --model M --seed S | aggregate

No file in src/modeling/, configs/ or src/evaluation/adapters/ is changed: the seed is set on an in-memory copy
of the locked config. Test predictions are frozen (SHA-256 recorded) before the test gold is read.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation import frozen_reliability as fr  # noqa: E402  (stdlib + numpy only)

SEEDS = (42, 1337, 2025)
THREADS = 6
MIN_FREE_BYTES = 15 * 1024**3
MAX_PROJECTED_SECONDS = 6 * 3600
MODELS = {
    "pcrf": {"model_id": "PHOBERT-CRF", "config": "configs/modeling/sprint03/phobert_crf_v1.json"},
    "dyn": {"model_id": "PROPOSED-DYN", "config": "configs/modeling/sprint03/proposed_dyn_v1.json"},
}
RUN_ORDER = [(model, seed) for seed in SEEDS for model in ("pcrf", "dyn")]
VARIANTS = {"pcrf": ("pcrf",), "dyn": ("dyn", "dyn_off")}
# Locked decoder policy (threshold/margin) reused for every seed; dev has 8 Lai (< 10), so no recalibration.
DECODER_THRESHOLD, DECODER_MARGIN = 0.7, 0.2

TRAIN_CORPUS = ROOT / "data/processed/annotation/sprint03/corpus_train_dev_v2"
EVAL_CORPUS = ROOT / "data/processed/annotation/sprint03/corpus_v1_release2"
RESOURCE_LOCK = ROOT / "data/interim/modeling/sprint03/task_01_06_20261003_v1/resource_lock_local_v1.json"
JAVA_BIN = ROOT / "data/interim/modeling/sprint03/resources_d_v1/java17/jdk-17.0.20.1+1-jre/bin"
PROTOCOL_LOCK = ROOT / "configs/modeling/sprint03/protocol_lock_v1.json"
INTERIM = ROOT / "data/interim/modeling/sprint04/multiseed_20261015_v1"
PROCESSED = ROOT / "data/processed/evaluation/sprint04/multiseed_20261015_v1"

# Sprint 3 Kaggle T4 (seed 42) — reported as its own row, never part of the mean.
SPRINT3_GPU = {
    "PHOBERT-CRF": {"t0_f1": 0.9843, "t1": "NOT_IMPLEMENTED"},
    "PROPOSED-DYN": {"t0_f1": 0.9821, "t1_accuracy": 0.7188, "t1_macro_f1": 0.5626},
    "PROPOSED-NO-CONSTRAINT": {"t0_f1": 0.9843, "t1_accuracy": 0.7188, "t1_macro_f1": 0.5626},
}


# ------------------------------------------------------------------ pure helpers (unit-tested)
def validate_seed(seed: int) -> int:
    if seed not in SEEDS:
        raise ValueError(f"SEED_OUTSIDE_LOCKED_PROTOCOL: {seed}")
    return seed


def run_name(model: str, seed: int) -> str:
    if model not in MODELS:
        raise ValueError(f"unknown model {model}")
    # DACN_RUN_TAG is only set by the determinism check so the rerun lives in its own directory.
    return f"{model}_seed{validate_seed(seed)}{os.environ.get('DACN_RUN_TAG', '')}"


def mean_std(values: list[float]) -> dict:
    """Mean and sample std (ddof=1); std is None for n < 2 (never a fake 0)."""
    clean = [float(v) for v in values if v is not None]
    n = len(clean)
    if n == 0:
        return {"n": 0, "mean": None, "std": None}
    return {"n": n, "mean": float(np.mean(clean)), "std": float(np.std(clean, ddof=1)) if n > 1 else None}


def safe_cleanup(run_dir: Path, base: Path = INTERIM) -> dict:
    """Delete heavy per-epoch/resume checkpoints of ONE run; best.pt (+ .json) and every .json are kept.

    Refuses any directory outside ``base``. Records size and SHA-256 of each deleted file.
    """
    run_dir, base = Path(run_dir).resolve(), Path(base).resolve()
    if not run_dir.is_relative_to(base) or run_dir == base:
        raise ValueError("CLEANUP_OUTSIDE_PACKAGE_DIRECTORY")
    checkpoints = run_dir / "checkpoints"
    removed = []
    if checkpoints.is_dir():
        for path in sorted(checkpoints.glob("*.pt")):
            if path.name == "best.pt":
                continue
            removed.append({"file": path.name, "bytes": path.stat().st_size, "sha256": fr.sha256_file(path)})
            path.unlink()
    return {"removed": removed, "kept": sorted(p.name for p in checkpoints.glob("*")) if checkpoints.is_dir() else []}


def build_seed_config(model: str, seed: int) -> dict:
    """Locked c02 config with the seed set on an in-memory copy (the config file is never written)."""
    from src.modeling.protocol import candidate_config, load_config
    validate_seed(seed)
    config = candidate_config(load_config(ROOT / MODELS[model]["config"]), "c02")
    config = copy.deepcopy(config)
    config["seed"] = seed
    if config["device"] != "cpu":
        raise ValueError("LOCAL_RUN_REQUIRES_CPU_DEVICE_IN_LOCKED_CONFIG")
    return config


def worker_env() -> dict:
    env = dict(os.environ)
    env.update(OMP_NUM_THREADS=str(THREADS), MKL_NUM_THREADS=str(THREADS), PYTHONDONTWRITEBYTECODE="1",
               JAVA_HOME=str(JAVA_BIN.parent), PATH=str(JAVA_BIN) + os.pathsep + env.get("PATH", ""))
    return env


def free_bytes() -> int:
    return shutil.disk_usage(ROOT).free


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=_default) + "\n", encoding="utf-8")


def _default(value):
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(type(value))


def argmax_t1_units(predictions, golds, excluded) -> np.ndarray:
    """(gold, predicted) rows using the raw posterior argmax (no threshold/margin); diagnostic only."""
    by_id = {p.sample_id: p for p in predictions}
    rows = []
    for gold in golds:
        system = None if gold["sample_id"] in excluded else gold.get("address_system")
        if system not in fr.ADDRESS_SYSTEMS:
            continue
        structure = (by_id[gold["sample_id"]].trace or {}).get("structure") or {}
        posterior = structure.get("posterior")
        if not posterior:
            return np.zeros((0, 2), dtype=np.int64)
        best = max(range(3), key=lambda i: (posterior[fr.ADDRESS_SYSTEMS[i]], -i))
        rows.append((fr.ADDRESS_SYSTEMS.index(system), best))
    return np.asarray(rows, dtype=np.int64).reshape(-1, 2)


# ------------------------------------------------------------------ workers
def _set_threads() -> None:
    import torch
    torch.set_num_threads(THREADS)


def cmd_preflight(args) -> int:
    from src.modeling.resources import preflight
    from src.modeling.datasets import load_corpus
    os.environ.update(worker_env())
    result = {"created_at": now(), "models": {}}
    for model in MODELS:
        config = build_seed_config(model, 42)
        report = preflight(config, RESOURCE_LOCK)
        try:
            load_corpus(TRAIN_CORPUS)
            report["corpus"] = "HASH_COUNT_PASS_240_60"
        except (OSError, ValueError, KeyError) as exc:
            report["blockers"].append(str(exc))
        result["models"][model] = report
    result["corpus_identity"] = {name: fr.sha256_file(TRAIN_CORPUS / name) == fr.sha256_file(EVAL_CORPUS / name)
                                 for name in ("train.jsonl", "dev.jsonl")}
    write_json(PROCESSED / "preflight.json", result)
    print(json.dumps({m: r["blockers"] for m, r in result["models"].items()}, ensure_ascii=False),
          json.dumps(result["corpus_identity"]))
    return 0 if not any(r["blockers"] for r in result["models"].values()) else 2


def cmd_train(args) -> int:
    from src.modeling.training import train_model
    _set_threads()
    run_dir = INTERIM / run_name(args.model, args.seed)
    config = build_seed_config(args.model, args.seed)
    config["run_id"] = run_dir.name
    started = time.monotonic()
    result = train_model(config, RESOURCE_LOCK, TRAIN_CORPUS, run_dir)
    elapsed = time.monotonic() - started
    logs = [json.loads(line) for line in (run_dir / "training_log.jsonl").read_text(encoding="utf-8").splitlines() if line]
    best = json.loads((run_dir / "checkpoints/best.pt.json").read_text(encoding="utf-8"))
    summary = {"run": run_dir.name, "status": result["status"], "seed": args.seed, "train_seconds": elapsed,
               "epochs_run": len(logs), "best_epoch": best["epoch"], "best_dev_key": next(
                   row["dev_selection_key"] for row in logs if row["epoch"] == best["epoch"]),
               "best_checkpoint_sha256": best["checkpoint_sha256"], "finished_at": now()}
    write_json(run_dir / "multiseed_train_summary.json", summary)
    print(json.dumps(summary))
    return 0


def inference_config(model: str, seed: int, variant: str, run_dir: Path) -> dict:
    from src.evaluation.experiment_config import modeling_config
    from src.modeling.structural_decoder import RULE_VERSION
    training = build_seed_config(model, seed)
    training["run_id"] = run_dir.name
    if variant == "dyn_off":
        training["model_id"] = "PROPOSED-NO-CONSTRAINT"
        training["structural_policy"] = {**training["structural_policy"], "enabled": False}
    config = modeling_config(f"{run_dir.name}_{variant}_test", training, run_dir / "checkpoints/best.pt", RESOURCE_LOCK)
    if model == "dyn":
        config["adapter_kwargs"]["decoder_policy"] = {"version": RULE_VERSION, "threshold": DECODER_THRESHOLD,
                                                      "margin": DECODER_MARGIN, "enabled": variant == "dyn"}
    return config


def cmd_infer(args) -> int:
    import importlib
    from src.evaluation.dev_runner import run_text_inference
    from src.evaluation.test_runner import load_test_input
    _set_threads()
    run_dir = INTERIM / run_name(args.model, args.seed)
    if args.variant not in VARIANTS[args.model]:
        raise ValueError("variant not valid for this model")
    config = inference_config(args.model, args.seed, args.variant, run_dir)
    input_path, manifest_path = EVAL_CORPUS / "test_input.jsonl", EVAL_CORPUS / "manifest.json"
    _, samples = load_test_input(input_path, manifest_path)  # hash-checked, text only; gold is not opened
    module, name = config["adapter_factory"].split(":")
    adapter = getattr(importlib.import_module(module), name)(**config["adapter_kwargs"])
    out = run_dir / f"test_{args.variant}"
    manifest = run_text_inference(adapter, samples, config, out,
        {"corpus_manifest_sha256": fr.sha256_file(manifest_path), "test_input_sha256": fr.sha256_file(input_path)},
        split="test", track="T0_T1_FINAL_TEST")
    print(json.dumps({"variant": args.variant, "status_counts": manifest["status_counts"],
                      "predictions_sha256": manifest["output_sha256"]["predictions.jsonl"]}))
    return 0


def _score_variant(model: str, seed: int, variant: str) -> dict:
    """Score one frozen test prediction file; the recorded hash must match before gold is read."""
    from src.evaluation.dev_runner import load_predictions
    name = run_name(model, seed)
    path = INTERIM / name / f"test_{variant}" / "predictions.jsonl"
    frozen = json.loads((PROCESSED / "frozen_hashes.json").read_text(encoding="utf-8"))
    key = f"{name}/{variant}"
    if frozen[key]["predictions_sha256"] != fr.sha256_file(path):
        raise ValueError(f"{key}: prediction changed after freezing")
    golds, excluded = fr.load_gold("test")  # gold is read only now
    predictions = load_predictions(path)
    units = fr.build_units(predictions, golds, excluded)
    metrics = fr.scorer_metrics(predictions, golds, excluded)
    if not all(fr.check_units_against_scorer(units, metrics).values()):
        raise ValueError(f"{key}: per-sample units differ from scorer")
    micro = metrics["t0_exact_span"]["micro"]
    t1 = metrics["t1_address_system"]
    row = {"run": name, "variant": variant, "seed": seed, "model": model,
           "t0_precision": micro["precision"], "t0_recall": micro["recall"], "t0_f1": micro["f1"],
           "t0_tp_fp_fn": [micro["total_tp"], micro["total_fp"], micro["total_fn"]],
           "exact_match": int(units["exact"].sum()), "n_samples": len(golds)}
    if model == "pcrf":
        row.update(t1="NOT_IMPLEMENTED")
    else:
        lai = fr.ADDRESS_SYSTEMS.index("Lai")
        u = units["t1"]
        row.update(t1="IMPLEMENTED", t1_eligible=t1["total_evaluated"], t1_accuracy=t1["overall_accuracy"],
                   t1_macro_f1=t1["macro_f1_all_3_classes"], t1_lai_f1=t1["per_class"]["Lai"]["f1"],
                   t1_lai_support=t1["per_class"]["Lai"]["support"], t1_coverage=1 - t1["abstain_rate"],
                   t1_abstain=t1["abstain_count"], t1_confusion=t1["confusion_matrix"])
        diag = argmax_t1_units(predictions, golds, excluded)
        if len(diag):
            macro = fr.MacroF1()
            row["t1_argmax_diagnostic"] = {"accuracy": fr.t1_accuracy_stat(diag), "macro_f1": macro(diag),
                                           "lai_f1": fr._class_f1(diag, lai), "label": "DIAGNOSTIC_NOT_A_CONFIGURATION"}
        del u
    return {"row": row, "units": units, "metrics": metrics}


def cmd_score(args) -> int:
    name = run_name(args.model, args.seed)
    out = {}
    for variant in VARIANTS[args.model]:
        scored = _score_variant(args.model, args.seed, variant)
        write_json(PROCESSED / "runs" / f"{name}_{variant}_metrics.json", {"row": scored["row"], "scorer": scored["metrics"]})
        np.savez(PROCESSED / "runs" / f"{name}_{variant}_units.npz", totals=scored["units"]["totals"],
                 exact=scored["units"]["exact"], t1=scored["units"]["t1"])
        out[variant] = scored["row"]["t0_f1"]
    print(json.dumps(out))
    return 0


# ------------------------------------------------------------------ orchestration
def run_worker(step: str, model: str, seed: int, extra: list[str] | None = None) -> tuple[int, Path]:
    log = INTERIM / "logs" / f"{run_name(model, seed)}_{step}{'_' + extra[-1] if extra else ''}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "scripts.70_run_multiseed_local", step, "--model", model, "--seed", str(seed), *(extra or [])]
    with log.open("w", encoding="utf-8") as handle:
        code = subprocess.run(cmd, cwd=ROOT, env=worker_env(), stdout=handle, stderr=subprocess.STDOUT).returncode
    return code, log


def _blocked(stage: str, name: str, log: Path) -> int:
    tail = "\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-40:])
    write_json(PROCESSED / "BLOCKED_LOCAL_TRAINING.json", {"status": "BLOCKED_LOCAL_TRAINING", "stage": stage, "run": name,
                                                            "log": str(log.relative_to(ROOT)), "error_tail": tail, "at": now()})
    print(f"BLOCKED_LOCAL_TRAINING at {stage} {name}; see {log}")
    return 2


def write_manifest(extra: dict | None = None) -> None:
    files = {"train.jsonl": None, "dev.jsonl": None}
    manifest = {
        "version": "s4-wp3b-multiseed-v1", "created_at": now(), "seeds": list(SEEDS), "run_order": [list(r) for r in RUN_ORDER],
        "candidate": "c02", "threads": THREADS, "device": "cpu",
        "decoder_policy": {"threshold": DECODER_THRESHOLD, "margin": DECODER_MARGIN, "recalibrated_per_seed": False},
        "inputs": {
            "config_sha256": {m: fr.sha256_file(ROOT / v["config"]) for m, v in MODELS.items()},
            "protocol_lock_sha256": fr.sha256_file(PROTOCOL_LOCK),
            "resource_lock_sha256": fr.sha256_file(RESOURCE_LOCK),
            "train_corpus_manifest_sha256": fr.sha256_file(TRAIN_CORPUS / "manifest.json"),
            "eval_corpus_manifest_sha256": fr.sha256_file(EVAL_CORPUS / "manifest.json"),
            "train_dev_identical_in_both_corpora": {n: fr.sha256_file(TRAIN_CORPUS / n) == fr.sha256_file(EVAL_CORPUS / n) for n in files},
            "test_input_sha256": fr.sha256_file(EVAL_CORPUS / "test_input.jsonl"),
        },
        "code_sha256": {f: fr.sha256_file(ROOT / f) for f in (
            "scripts/70_run_multiseed_local.py", "src/evaluation/frozen_reliability.py", "src/evaluation/stats.py",
            "src/modeling/training.py", "src/modeling/protocol.py", "src/modeling/structural_decoder.py")},
        "sprint3_gpu_rows_in_mean": False,
    }
    manifest.update(extra or {})
    write_json(PROCESSED / "run_manifest.json", manifest)


def cmd_run_all(args) -> int:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    INTERIM.mkdir(parents=True, exist_ok=True)
    (PROCESSED / "runs").mkdir(exist_ok=True)
    write_manifest()
    frozen_path = PROCESSED / "frozen_hashes.json"
    frozen = json.loads(frozen_path.read_text(encoding="utf-8")) if frozen_path.exists() else {}
    timings = {}
    for model, seed in RUN_ORDER:
        if args.only and run_name(model, seed) not in args.only:
            continue
        name = run_name(model, seed)
        done = INTERIM / name / "multiseed_run_done.json"
        if done.exists():
            continue
        if free_bytes() < MIN_FREE_BYTES:
            print(f"STOP: free disk below {MIN_FREE_BYTES} bytes")
            return 3
        run_dir = INTERIM / name
        if not run_dir.exists():
            code, log = run_worker("train", model, seed)
            if code:
                return _blocked("train", name, log)
        summary = json.loads((run_dir / "multiseed_train_summary.json").read_text(encoding="utf-8"))
        timings[name] = summary["train_seconds"]
        # Clean right after training: the locked adapter preflight demands 20 GiB free before inference, and a
        # 16-epoch run leaves ~9 GB of per-epoch checkpoints. best.pt (hash in training_manifest) is kept.
        early = run_dir / "cleanup_after_training.json"
        if not early.exists() and not (run_dir / "early_cleanup_before_inference.json").exists():
            write_json(early, safe_cleanup(run_dir))
        for variant in VARIANTS[model]:
            if not (run_dir / f"test_{variant}").exists():
                code, log = run_worker("infer", model, seed, ["--variant", variant])
                if code:
                    return _blocked("infer", name, log)
            frozen[f"{name}/{variant}"] = {
                "predictions_sha256": fr.sha256_file(run_dir / f"test_{variant}" / "predictions.jsonl"), "frozen_at": now()}
        write_json(frozen_path, frozen)  # frozen before any gold access
        code, log = run_worker("score", model, seed)
        if code:
            return _blocked("score", name, log)
        cleanup = safe_cleanup(run_dir)
        write_json(done, {"summary": summary, "cleanup": cleanup, "disk_free_after_bytes": free_bytes(), "at": now()})
        if name == "pcrf_seed42" and not args.only:
            projected = summary["train_seconds"] * len(RUN_ORDER)
            if projected > MAX_PROJECTED_SECONDS:
                write_json(PROCESSED / "STOPPED_PROJECTION_OVER_6H.json", {"projected_seconds": projected, "first_run": summary})
                print("STOP: projected total over 6 hours; the project owner decides (cut seeds or Kaggle)")
                return 3
    return 0


def cmd_determinism(args) -> int:
    """Retrain PCRF seed 42 once more in its own directory and compare frozen test predictions (step 5)."""
    original = INTERIM / "pcrf_seed42" / "test_pcrf" / "predictions.jsonl"
    os.environ["DACN_RUN_TAG"] = "_rerun"
    rerun_dir = INTERIM / run_name("pcrf", 42)
    if not rerun_dir.exists() and free_bytes() < MIN_FREE_BYTES + 5 * 1024**3:
        print("STOP: not enough free disk for a rerun")
        return 3
    if not rerun_dir.exists():
        code, log = run_worker("train", "pcrf", 42)
        if code:
            return _blocked("train-determinism", run_name("pcrf", 42), log)
    early = safe_cleanup(rerun_dir)  # frees the 20 GiB the locked adapter preflight needs
    if not (rerun_dir / "test_pcrf").exists():
        code, log = run_worker("infer", "pcrf", 42, ["--variant", "pcrf"])
        if code:
            return _blocked("infer-determinism", run_name("pcrf", 42), log)
    from src.evaluation.dev_runner import load_predictions
    a, b = load_predictions(original), load_predictions(rerun_dir / "test_pcrf" / "predictions.jsonl")
    spans = lambda p: [(s.start, s.end, s.label) for s in p.spans]
    differing = [x.sample_id for x, y in zip(a, b) if x.sample_id != y.sample_id or spans(x) != spans(y)]
    emission_gap = 0.0
    for x, y in zip(a, b):
        ex, ey = (x.raw_output or {}).get("emissions"), (y.raw_output or {}).get("emissions")
        if ex and ey and len(ex) == len(ey):
            emission_gap = max(emission_gap, float(np.max(np.abs(np.asarray(ex) - np.asarray(ey)))))
    result = {"status": "DETERMINISTIC_ON_CPU" if not differing and emission_gap == 0.0 else "NONDETERMINISTIC_ON_CPU",
              "samples_with_different_spans": len(differing), "differing_sample_count_of": len(a),
              "max_abs_emission_difference": emission_gap, "best_epoch_original": json.loads(
                  (INTERIM / "pcrf_seed42" / "multiseed_train_summary.json").read_text(encoding="utf-8"))["best_epoch"],
              "best_epoch_rerun": json.loads((rerun_dir / "multiseed_train_summary.json").read_text(encoding="utf-8"))["best_epoch"],
              "best_checkpoint_sha256_equal": json.loads((INTERIM / "pcrf_seed42" / "multiseed_train_summary.json").read_text(
                  encoding="utf-8"))["best_checkpoint_sha256"] == json.loads((rerun_dir / "multiseed_train_summary.json").read_text(
                  encoding="utf-8"))["best_checkpoint_sha256"], "cleanup": early, "at": now()}
    write_json(PROCESSED / "determinism_check.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "cleanup"}))
    return 0


# ------------------------------------------------------------------ aggregation
def _load_runs() -> list[dict]:
    rows = []
    for path in sorted((PROCESSED / "runs").glob("*_metrics.json")):
        rows.append(json.loads(path.read_text(encoding="utf-8"))["row"])
    return rows


def _train_info(name: str) -> dict:
    done = INTERIM / name / "multiseed_run_done.json"
    if not done.exists():
        return {}
    summary = json.loads(done.read_text(encoding="utf-8"))["summary"]
    dev_dir = INTERIM / name / "validation" / f"{name}_epoch{summary['best_epoch']:03d}_dev"
    dev_f1 = None
    if (dev_dir / "metrics.json").exists():
        dev_f1 = json.loads((dev_dir / "metrics.json").read_text(encoding="utf-8"))["t0_exact_span"]["micro"]["f1"]
    return {"dev_t0_f1": dev_f1, "best_epoch": summary["best_epoch"], "epochs_run": summary["epochs_run"],
            "train_seconds": summary["train_seconds"]}


def cmd_aggregate(args) -> int:
    rows = _load_runs()
    by = {(r["model"], r["variant"], r["seed"]): r for r in rows}
    seeds_done = {m: sorted({r["seed"] for r in rows if r["variant"] == m}) for m in ("pcrf", "dyn")}
    table = []
    for r in sorted(rows, key=lambda r: (r["seed"], r["variant"])):
        info = _train_info(r["run"]) if r["variant"] in ("pcrf", "dyn") else {}
        table.append({**{k: r.get(k) for k in ("run", "variant", "seed", "t0_precision", "t0_recall", "t0_f1", "exact_match",
                                             "t1", "t1_accuracy", "t1_macro_f1", "t1_lai_f1", "t1_lai_support", "t1_coverage")},
                      "argmax_t1_accuracy": (r.get("t1_argmax_diagnostic") or {}).get("accuracy"),
                      "argmax_t1_macro_f1": (r.get("t1_argmax_diagnostic") or {}).get("macro_f1"),
                      "argmax_t1_lai_f1": (r.get("t1_argmax_diagnostic") or {}).get("lai_f1"), **info})
    summary = {}
    for variant in ("pcrf", "dyn", "dyn_off"):
        sel = [r for r in rows if r["variant"] == variant]
        entry = {"seeds": sorted(r["seed"] for r in sel),
                 "partial_seeds": len(sel) < len(SEEDS) and "PARTIAL_SEEDS" or None,
                 "t0_f1": mean_std([r["t0_f1"] for r in sel]), "t0_precision": mean_std([r["t0_precision"] for r in sel]),
                 "t0_recall": mean_std([r["t0_recall"] for r in sel]), "exact_match": mean_std([r["exact_match"] for r in sel])}
        if variant != "pcrf":
            for key in ("t1_accuracy", "t1_macro_f1", "t1_lai_f1", "t1_coverage"):
                entry[key] = mean_std([r[key] for r in sel])
        summary[variant] = entry
    deltas = []
    for seed in SEEDS:
        a, b, off = by.get(("pcrf", "pcrf", seed)), by.get(("dyn", "dyn", seed)), by.get(("dyn", "dyn_off", seed))
        row = {"seed": seed}
        if a and b:
            row["pcrf_minus_dyn_t0_f1"] = a["t0_f1"] - b["t0_f1"]
            ua = np.load(PROCESSED / "runs" / f"{a['run']}_pcrf_units.npz")
            ub = np.load(PROCESSED / "runs" / f"{b['run']}_dyn_units.npz")
            pair = fr.paired_comparison(fr.f1_stat, ua["totals"], ub["totals"], ua["exact"], ub["exact"])
            row["paired_ci"] = [pair["delta"].get("ci_low"), pair["delta"].get("ci_high")]
            row["paired_p_randomization"] = pair["randomization"].get("p_value")
            row["mcnemar"] = [pair["mcnemar"]["b"], pair["mcnemar"]["c"]]
        if b and off:
            row["dyn_on_minus_off_t0_f1"] = b["t0_f1"] - off["t0_f1"]
        deltas.append(row)
    summary["deltas_by_seed"] = deltas
    summary["delta_mean_std"] = {
        "pcrf_minus_dyn_t0_f1": mean_std([d.get("pcrf_minus_dyn_t0_f1") for d in deltas]),
        "dyn_on_minus_off_t0_f1": mean_std([d.get("dyn_on_minus_off_t0_f1") for d in deltas])}
    summary["sprint3_gpu_t4_seed42_not_in_mean"] = SPRINT3_GPU
    summary["crf_indep"] = "DETERMINISTIC_SEED_INVARIANT (L-BFGS; one frozen row: test T0 F1 0.9076)"
    summary["heur_jw"] = "FIXED_CONFIGURATION (one frozen row: test T0 F1 0.9112)"
    write_json(PROCESSED / "metrics.json", summary)
    (PROCESSED / "tables").mkdir(exist_ok=True)
    names = list(dict.fromkeys(k for row in table for k in row))
    with (PROCESSED / "tables/per_seed.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=names)
        writer.writeheader()
        writer.writerows(table)
    print(json.dumps({k: summary[k] for k in ("pcrf", "dyn", "dyn_off", "delta_mean_std")}, ensure_ascii=False, indent=1))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("preflight", "train", "infer", "score", "run-all", "aggregate", "determinism"))
    parser.add_argument("--model", choices=tuple(MODELS))
    parser.add_argument("--seed", type=int)
    parser.add_argument("--variant")
    parser.add_argument("--only", nargs="*", help="restrict run-all to these run names (smoke / retries)")
    args = parser.parse_args()
    if args.command in ("train", "infer", "score"):
        validate_seed(args.seed)
    return {"preflight": cmd_preflight, "train": cmd_train, "infer": cmd_infer, "score": cmd_score,
            "run-all": cmd_run_all, "aggregate": cmd_aggregate, "determinism": cmd_determinism}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
