"""WP2b: tier 2 of WP2 on the six CPU-retrained WP3b checkpoints (LOCAL_CPU_RETRAINED).

Steps (neural workers use the neural runtime, one process per checkpoint; the rest uses the main venv):

    python -m scripts.68c_run_t1_tier2_local prepare                       # dirs, hash checks, declared manifest
    NEURAL=data/interim/modeling/sprint03/runtime_neural_d_v1/bin/python
    $NEURAL -m scripts.68c_run_t1_tier2_local smoke-all                    # 6 x smoke vs WP3b test predictions
    $NEURAL -m scripts.68c_run_t1_tier2_local infer-all                    # 6 x full inference (resumable)
    python -m scripts.68c_run_t1_tier2_local freeze                        # SHA-256 of every output, BEFORE scoring
    python -m scripts.68c_run_t1_tier2_local score                         # tables, CIs, paired tests

Nothing is trained.  The probe is a numpy softmax on CLS vectors.  No file of scripts 68/68b/70, src/modeling,
configs or the earlier run directories is modified; their functions are imported.  Every number carries the
label LOCAL_CPU_RETRAINED: these are not the locked Sprint 3 checkpoint (7a4a3d01...).
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

LABEL = "LOCAL_CPU_RETRAINED"
SCRIPT_VERSION = "t1-h5-tier2-local-v1"
SEEDS = (42, 1337, 2025)
THREADS = 6
CI_SEED = 20261016
RESAMPLES = 10_000
MAX_PROJECTED_SECONDS = 5 * 3600
MIN_FREE_BYTES = 20 * 1024**3  # locked adapter preflight (DISK_BELOW_TRAINING_ARTIFACT_BUDGET)

INTERIM = Path("data/interim/modeling/sprint04/t1_tier2_local_20261016_v1")
PROCESSED = Path("data/processed/evaluation/sprint04/t1_h5_tier2_local_20261016_v1")
TIER1_RUN = Path("data/processed/evaluation/sprint04/t1_h5_20261015_v1")
MULTISEED = Path("data/interim/modeling/sprint04/multiseed_20261015_v1")
SETS_DIR = Path("data/interim/modeling/sprint04/t1_sets_20261015_v1")
# Directories this package must never write into.
PROTECTED = (TIER1_RUN, MULTISEED, SETS_DIR)

# SHA-256 prefixes from docs/sprints/sprint_04/reviews/review_wp3b_20261014.md (seed 42 / 1337 / 2025).
CHECKPOINT_PREFIX = {
    ("pcrf", 42): "5306980e", ("pcrf", 1337): "54f1136b", ("pcrf", 2025): "bb4ee1b5",
    ("dyn", 42): "62105473", ("dyn", 1337): "b70d0f7d", ("dyn", 2025): "fc41f407",
}
RUN_ORDER = [(model, seed) for seed in SEEDS for model in ("dyn", "pcrf")]
INPUT_SETS = ("t1_synth_train", "t1_synth_dev", "synth_eval", "data06", "s3_train", "s3_dev", "s3_test")
CLS_SETS = INPUT_SETS  # DYN: CLS of all seven sets
PRED_SETS = {"dyn": ("synth_eval", "data06", "s3_dev", "s3_test"), "pcrf": ("synth_eval", "data06", "s3_test")}
SMOKE_SAMPLES = 100
POSTERIOR_TOLERANCE = 1e-6
SCORED_DATASETS = ("s3_test", "synth_eval", "data06")

# Scoring-side system identifiers (HEUR-JW / T1-PIPE-CRF / T1-FEAT are tier-1 predictions read back unchanged).
DYN_SYS, DYN_ARGMAX, PIPE_PCRF, PIPE_DYN = "PROPOSED-DYN", "DYN-ARGMAX-DIAGNOSTIC", "T1-PIPE-PCRF", "T1-PIPE-DYN"
PROBE, PROBE_SYNTH = "T1-HEAD-PROBE", "T1-HEAD-PROBE-SYNTH-ONLY"
HEUR, FEAT, PIPE_CRF = "HEUR-JW", "T1-FEAT", "T1-PIPE-CRF"
NEURAL_SYSTEMS = (DYN_SYS, DYN_ARGMAX, PIPE_PCRF, PIPE_DYN, PROBE, PROBE_SYNTH)
REFERENCE_SYSTEMS = (HEUR, PIPE_CRF, FEAT)
EXTRA_DEFINITIONS = {
    DYN_ARGMAX: {"uses_gazetteer": False, "definition": "DIAGNOSTIC: raw posterior argmax of the DYN T1 head, no "
                 "threshold/margin; not a configuration"},
    PROBE_SYNTH: {"uses_gazetteer": False, "definition": "T1-HEAD-PROBE trained on t1_synth_train only (shows the "
                  "contribution of the Sprint 3 train T1 labels)"},
}
DECLARED_RULES = {
    "dyn": "locked decoder policy threshold 0.7 / margin 0.2 with constraint on (scripts/70 inference_config); "
           "processor-rejected texts stay in the denominator as khong_ro",
    "dyn_argmax": "posterior argmax, tie -> lower class index (t1_pipeline.read_structure convention); diagnostic only",
    "t1_pipe": "same rule as tier 1: administrative spans of the model + HEUR-JW _resolve + system rule",
    "probe": "numpy softmax, standardised features (statistics from the training rows only); training rows = "
             "t1_synth_train + Sprint 3 train rows with a T1 label and a valid CLS; L2 in {0.01, 0.1, 1} by "
             "t1_synth_dev macro-F1, accuracy, then larger L2; synth-only variant uses t1_synth_train rows only",
    "ci": "cluster bootstrap over admin_group_key, B = 10000, seed 20261016, per seed",
    "mean_std": "over the three seeds, sample std (ddof = 1), n reported; no seed is selected",
    "paired": "vs HEUR-JW (scripts/68 score_cell) and vs T1-FEAT of tier 1, same samples",
}


# ---------------------------------------------------------------------------------------------- helpers
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def dump_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) + "\n",
                    encoding="utf-8", newline="\n")


def _json_default(value):
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(type(value))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_name(model: str, seed: int) -> str:
    if model not in ("dyn", "pcrf") or seed not in SEEDS:
        raise ValueError(f"unknown run {model} seed {seed}")
    return f"{model}_seed{seed}"


def guard_output_dir(path: Path) -> Path:
    """Refuse an existing directory and every protected earlier run directory."""
    path = Path(path)
    resolved = (path if path.is_absolute() else REPO / path).resolve()
    for protected in PROTECTED:
        root = (REPO / protected).resolve()
        if resolved == root or root in resolved.parents:
            raise ValueError(f"OUTPUT_IN_PROTECTED_DIRECTORY: {path}")
    if resolved.exists():
        raise FileExistsError(f"{path} already exists; refusing to overwrite (use a _v2 directory)")
    return resolved


def mean_std(values) -> dict:
    """Mean and sample std (ddof = 1) over the numeric entries; std None for n < 2; non-numeric entries counted."""
    import numpy as np
    numeric = [float(v) for v in values if isinstance(v, (int, float)) and not isinstance(v, bool) and v == v]
    n = len(numeric)
    return {"n": n, "n_not_numeric": len(list(values)) - n, "mean": float(np.mean(numeric)) if n else None,
            "std": float(np.std(numeric, ddof=1)) if n > 1 else None}


def load_text_inputs(inputs_dir: Path, name: str, expected_sha: str) -> list[dict]:
    """Read one tier-2 input file; hash-checked, and only {key, text} rows are accepted."""
    path = Path(inputs_dir) / f"{name}.jsonl"
    if sha256_file(path) != expected_sha:
        raise ValueError(f"HASH_MISMATCH {path}")
    rows = read_jsonl(path)
    for row in rows:
        if set(row) != {"key", "text"}:
            raise ValueError(f"inference input must only carry key/text; got {sorted(row)}")
    return rows


def verify_inputs() -> dict:
    """SHA-256 of the seven tier-2 input files against tier2_inputs.json; wrong hash stops the run."""
    inputs_dir = REPO / TIER1_RUN / "tier2_inputs"
    listing = json.loads((inputs_dir / "tier2_inputs.json").read_text(encoding="utf-8"))["files"]
    out = {}
    for name in INPUT_SETS:
        load_text_inputs(inputs_dir, name, listing[name]["sha256"])
        out[name] = listing[name]
    return out


def verify_checkpoint(model: str, seed: int) -> dict:
    """Full SHA-256 of best.pt: file hash == training summary hash and starts with the reviewed prefix."""
    run_dir = REPO / MULTISEED / run_name(model, seed)
    path = run_dir / "checkpoints" / "best.pt"
    actual = sha256_file(path)
    summary = json.loads((run_dir / "multiseed_train_summary.json").read_text(encoding="utf-8"))
    if actual != summary["best_checkpoint_sha256"] or not actual.startswith(CHECKPOINT_PREFIX[(model, seed)]):
        raise ValueError(f"HASH_MISMATCH checkpoint {path}")
    return {"path": f"{MULTISEED.as_posix()}/{run_name(model, seed)}/checkpoints/best.pt", "sha256": actual,
            "best_epoch": summary["best_epoch"], "train_seconds": summary["train_seconds"]}


def load70():
    return importlib.import_module("scripts.70_run_multiseed_local")


def final_label(row: dict) -> str:
    """T1 label of one DYN prediction row; rejected / abstained / non-class stays in the denominator as khong_ro."""
    if row.get("rejected") or row.get("abstain") or row.get("predicted_system") not in ("cu", "moi", "Lai"):
        return "khong_ro"
    return row["predicted_system"]


def argmax_label(row: dict) -> str:
    posterior = row.get("posterior")
    if row.get("rejected") or not posterior:
        return "khong_ro"
    classes = ("cu", "moi", "Lai")
    return max(classes, key=lambda c: (posterior[c], -classes.index(c)))


def fit_probe(P, x_fit, y_fit, x_dev, y_dev):
    """L2 selection and fit; takes only feature matrices and integer labels (no frames, no gold columns)."""
    return P.select_l2(x_fit, y_fit, x_dev, y_dev, seed=P.CLASSIFIER_SEED, standardize=True)


def l2_is_tie(trials: list[dict]) -> bool:
    return len({(round(t["dev_macro_f1"], 12), round(t["dev_accuracy"], 12)) for t in trials}) == 1


# ---------------------------------------------------------------------------------------------- orchestration
def worker_env() -> dict:
    env = load70().worker_env()
    env["PYTHONPATH"] = str(REPO)
    return env


def cmd_prepare(args) -> int:
    import numpy as np  # noqa: F401  (main runtime check)
    interim, processed = guard_output_dir(INTERIM), guard_output_dir(PROCESSED)
    inputs = verify_inputs()
    checkpoints = {run_name(m, s): verify_checkpoint(m, s) for m, s in RUN_ORDER}
    interim.mkdir(parents=True)
    processed.mkdir(parents=True)
    (interim / "smoke").mkdir()
    manifest = {
        "script_version": SCRIPT_VERSION, "status": "DECLARED_BEFORE_SCORING", "declared_at": now_iso(), "label": LABEL,
        "note": "checkpoints retrained locally on CPU (WP3b), NOT the locked Sprint 3 checkpoint 7a4a3d01...; "
                "the BLOCKED_LOCAL_NEURAL cells of 'DYN gốc' in the tier-1 H5 table are unchanged",
        "seeds": list(SEEDS), "ci_seed": CI_SEED, "n_resamples": RESAMPLES, "threads": THREADS,
        "systems_neural": list(NEURAL_SYSTEMS), "systems_reference_tier1": list(REFERENCE_SYSTEMS),
        "rules": DECLARED_RULES, "l2_grid": [0.01, 0.1, 1.0],
        "checkpoints_sha256": checkpoints, "tier2_inputs_sha256": inputs,
        "tier1_run_manifest_sha256": sha256_file(REPO / TIER1_RUN / "run_manifest.json"),
        "tier1_predictions_sha256": sha256_file(REPO / TIER1_RUN / "predictions.jsonl"),
        "code_sha256": {name: sha256_file(REPO / name) for name in (
            "scripts/68c_run_t1_tier2_local.py", "scripts/68_run_t1_evaluation.py", "scripts/68b_run_t1_neural_local.py",
            "scripts/70_run_multiseed_local.py", "src/evaluation/t1_pipeline.py", "src/evaluation/t1_situations.py",
            "src/evaluation/stats.py", "src/evaluation/experiment_config.py")},
        "free_bytes_at_prepare": shutil.disk_usage(REPO).free,
    }
    dump_json(processed / "run_manifest.json", manifest)
    print(json.dumps({"prepared": True, "free_gib": round(manifest["free_bytes_at_prepare"] / 1024**3, 1)}))
    return 0


def _spawn(step: str, model: str, seed: int, log: Path) -> int:
    cmd = [sys.executable, "-m", "scripts.68c_run_t1_tier2_local", step, "--model", model, "--seed", str(seed)]
    with log.open("w", encoding="utf-8") as handle:
        return subprocess.run(cmd, cwd=REPO, env=worker_env(), stdout=handle, stderr=subprocess.STDOUT).returncode


def cmd_smoke_all(args) -> int:
    (REPO / INTERIM / "logs").mkdir(exist_ok=True)
    for model, seed in RUN_ORDER:
        name = run_name(model, seed)
        if (REPO / INTERIM / "smoke" / f"{name}.json").exists():
            continue
        code = _spawn("smoke", model, seed, REPO / INTERIM / "logs" / f"{name}_smoke.log")
        print(f"smoke {name}: exit {code}", flush=True)
    return cmd_smoke_summary(args)


def cmd_smoke_summary(args) -> int:
    rows, total, passed = [], 0.0, 0
    sizes = {"dyn": sum(len(read_jsonl(REPO / TIER1_RUN / "tier2_inputs" / f"{n}.jsonl")) for n in INPUT_SETS),
             "pcrf": sum(len(read_jsonl(REPO / TIER1_RUN / "tier2_inputs" / f"{n}.jsonl")) for n in PRED_SETS["pcrf"])}
    for model, seed in RUN_ORDER:
        path = REPO / INTERIM / "smoke" / f"{run_name(model, seed)}.json"
        if not path.exists():
            rows.append({"run": run_name(model, seed), "status": "SMOKE_NOT_RUN"})
            continue
        info = json.loads(path.read_text(encoding="utf-8"))
        per_sample = info["seconds_100"] / info["samples"]
        projected = info["load_seconds"] + per_sample * sizes[model]
        total += projected
        passed += info["status"] == "SMOKE_PASS"
        rows.append({**{k: info[k] for k in ("run", "status", "load_seconds", "seconds_100", "samples")},
                     "projected_seconds": projected})
    status = "BLOCKED_LOCAL_NEURAL" if passed == 0 else ("PROJECTION_OVER_5H" if total > MAX_PROJECTED_SECONDS else "OK")
    summary = {"runs": rows, "passed": passed, "projected_total_seconds": total, "status": status}
    dump_json(REPO / INTERIM / "smoke_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0 if status == "OK" else 3


def cmd_infer_all(args) -> int:
    smoke = json.loads((REPO / INTERIM / "smoke_summary.json").read_text(encoding="utf-8"))
    ok = {r["run"] for r in smoke["runs"] if r["status"] == "SMOKE_PASS"}
    for model, seed in RUN_ORDER:
        name = run_name(model, seed)
        if name not in ok or (REPO / INTERIM / name / "inference_done.json").exists():
            continue
        if shutil.disk_usage(REPO).free < MIN_FREE_BYTES:
            print("STOP: free disk below the locked 20 GiB preflight")
            return 3
        code = _spawn("infer", model, seed, REPO / INTERIM / "logs" / f"{name}_infer.log")
        print(f"infer {name}: exit {code}", flush=True)
        if code:
            return 2
    return 0


# ---------------------------------------------------------------------------------------------- neural workers
def build_local_adapter(model: str, seed: int):
    """Adapter exactly as WP3b's scripts/70 builds it (inference_config -> adapter_factory)."""
    pm = load70()
    run_dir = REPO / MULTISEED / run_name(model, seed)
    config = pm.inference_config(model, seed, model, run_dir)  # variant == model name: "dyn" (policy on) / "pcrf"
    module, name = config["adapter_factory"].split(":")
    return getattr(importlib.import_module(module), name)(**config["adapter_kwargs"]), config


class ClsCapture:
    """Forward hook that keeps the encoder CLS vector of the last model call (same as scripts/68b)."""

    def __init__(self, model) -> None:
        self.last = None
        self.handle = model.register_forward_hook(self._hook)

    def _hook(self, module, inputs, output):
        self.last = output["cls"][0].detach().cpu().numpy().copy()

    def take(self):
        value, self.last = self.last, None
        return value


def _prepare_runtime():
    import torch
    os.environ["OMP_NUM_THREADS"] = os.environ["MKL_NUM_THREADS"] = str(THREADS)
    torch.set_num_threads(THREADS)
    sys.path.insert(0, str(REPO))
    java = importlib.import_module("scripts.68b_run_t1_neural_local").use_project_java()
    return torch, java


def _row(dataset: str, item: dict, output, vector, model: str) -> dict:
    structure = (output.trace or {}).get("structure") or {}
    return {
        "dataset": dataset, "key": item["key"],
        "spans": [{"start": s.start, "end": s.end, "label": s.label} for s in output.spans],
        "predicted_system": output.predicted_system, "abstain": bool(output.abstain), "status": output.status,
        "rejected": "alignment_reject" in (output.trace or {}),  # processor refused the text: no model call
        "posterior": structure.get("posterior"), "confidence": structure.get("confidence"),
        "threshold": structure.get("threshold"), "margin_required": structure.get("margin_required"),
    }


def cmd_smoke(args) -> int:
    import numpy as np
    torch, java = _prepare_runtime()
    model, seed = args.model, args.seed
    name = run_name(model, seed)
    verify_checkpoint(model, seed)
    inputs_dir = REPO / TIER1_RUN / "tier2_inputs"
    listing = json.loads((inputs_dir / "tier2_inputs.json").read_text(encoding="utf-8"))["files"]
    items = load_text_inputs(inputs_dir, "s3_test", listing["s3_test"]["sha256"])[:SMOKE_SAMPLES]
    ref_dir = "test_dyn" if model == "dyn" else "test_pcrf"
    reference = {r["sample_id"]: r for r in read_jsonl(REPO / MULTISEED / name / ref_dir / "predictions.jsonl")}
    info = {"run": name, "label": LABEL, "java": java, "threads": torch.get_num_threads(), "samples": len(items)}
    started = time.perf_counter()
    try:
        adapter, _ = build_local_adapter(model, seed)
    except Exception as exc:  # noqa: BLE001 - verbatim error is the deliverable
        import traceback
        info.update(status="SMOKE_FAIL", reason="adapter could not be built", error=traceback.format_exc())
        dump_json(REPO / INTERIM / "smoke" / f"{name}.json", {**info, "load_seconds": 0.0, "seconds_100": 1.0})
        print("SMOKE_FAIL adapter", exc)
        return 3
    info["load_seconds"] = round(time.perf_counter() - started, 1)
    capture = ClsCapture(adapter.model) if model == "dyn" else None
    diffs, span_ok, system_ok, abstain_ok, cls_ok, post_max = [], 0, 0, 0, 0, 0.0
    started = time.perf_counter()
    for item in items:
        output = adapter.parse_spans(item["text"], sample_id=item["key"])
        ref = reference[item["key"]]
        got = sorted((s.start, s.end, s.label) for s in output.spans)
        want = sorted((s["start"], s["end"], s["label"]) for s in ref["spans"])
        ok_span = got == want
        ok_system = output.predicted_system == ref["predicted_system"]
        ok_abstain = bool(output.abstain) == bool(ref["abstain"])
        span_ok += ok_span
        system_ok += ok_system
        abstain_ok += ok_abstain
        if model == "dyn":
            vector = capture.take()
            cls_ok += vector is not None and vector.shape == (768,) and bool(np.isfinite(vector).all())
            local = (output.trace or {}).get("structure") or {}
            if local.get("posterior") and ref["trace"].get("structure"):
                post_max = max(post_max, max(abs(local["posterior"][k] - ref["trace"]["structure"]["posterior"][k])
                                             for k in local["posterior"]))
        if not (ok_span and ok_system and ok_abstain):
            diffs.append(item["key"])
    info["seconds_100"] = round(time.perf_counter() - started, 1)
    passed = len(diffs) == 0 and post_max <= POSTERIOR_TOLERANCE
    info.update(status="SMOKE_PASS" if passed else "SMOKE_FAIL", spans_equal=span_ok, predicted_system_equal=system_ok,
                abstain_equal=abstain_ok, cls_vectors_ok=cls_ok if model == "dyn" else "NOT_APPLICABLE",
                posterior_max_abs_diff=post_max if model == "dyn" else "NOT_APPLICABLE",
                posterior_tolerance=POSTERIOR_TOLERANCE, differing_keys=diffs[:10], differing_count=len(diffs))
    dump_json(REPO / INTERIM / "smoke" / f"{name}.json", info)
    print(json.dumps(info, ensure_ascii=False))
    return 0 if passed else 3


def cmd_infer(args) -> int:
    import numpy as np
    torch, java = _prepare_runtime()
    model, seed = args.model, args.seed
    name = run_name(model, seed)
    checkpoint = verify_checkpoint(model, seed)
    final = REPO / INTERIM / name
    work = REPO / INTERIM / f"{name}.tmp"
    if final.exists():
        raise SystemExit(f"{final} already exists; refusing to overwrite")
    if work.exists():  # leftover of an interrupted run of THIS package only
        shutil.rmtree(work)
    work.mkdir()
    inputs_dir = REPO / TIER1_RUN / "tier2_inputs"
    listing = json.loads((inputs_dir / "tier2_inputs.json").read_text(encoding="utf-8"))["files"]
    adapter, _ = build_local_adapter(model, seed)
    capture = ClsCapture(adapter.model) if model == "dyn" else None
    sets = INPUT_SETS if model == "dyn" else PRED_SETS["pcrf"]
    started = time.perf_counter()
    counts = {}
    with (work / "predictions.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
        for dataset in sets:
            items = load_text_inputs(inputs_dir, dataset, listing[dataset]["sha256"])  # {key, text} only
            vectors, valid = [], []
            rejected = 0
            for item in items:
                output = adapter.parse_spans(item["text"], sample_id=item["key"])
                vector = capture.take() if capture else None
                row = _row(dataset, item, output, vector, model)
                rejected += row["rejected"]
                if capture:
                    valid.append(vector is not None)
                    vectors.append(vector if vector is not None else np.zeros(768, dtype=np.float32))
                if dataset in PRED_SETS[model]:
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            if capture:
                np.save(work / f"cls_{dataset}.npy", np.asarray(vectors, dtype=np.float32))
                dump_json(work / f"cls_{dataset}.keys.json", {"keys": [i["key"] for i in items], "valid": valid})
            counts[dataset] = {"rows": len(items), "processor_rejected": rejected}
            print(f"[{name}] {dataset}: {len(items)} rows, {time.perf_counter() - started:.0f}s", flush=True)
    done = {"run": name, "label": LABEL, "checkpoint": checkpoint, "counts": counts, "java": java,
            "threads": torch.get_num_threads(), "seconds": round(time.perf_counter() - started, 1), "finished_at": now_iso(),
            "files": {p.name: sha256_file(p) for p in sorted(work.iterdir())}}
    dump_json(work / "inference_done.json", done)
    work.rename(final)
    print(json.dumps({"done": name, "seconds": done["seconds"]}))
    return 0


# ---------------------------------------------------------------------------------------------- freeze + score
def cmd_freeze(args) -> int:
    path = REPO / PROCESSED / "frozen_hashes.json"
    if path.exists():
        raise SystemExit(f"{path} exists; refusing to overwrite")
    frozen = {}
    for model, seed in RUN_ORDER:
        run_dir = REPO / INTERIM / run_name(model, seed)
        if not (run_dir / "inference_done.json").exists():
            continue
        for file in sorted(run_dir.iterdir()):
            frozen[f"{run_name(model, seed)}/{file.name}"] = sha256_file(file)
    dump_json(path, {"frozen_at": now_iso(), "label": LABEL, "files": frozen})
    print(json.dumps({"frozen_files": len(frozen)}))
    return 0


def verify_frozen() -> dict:
    """Scoring refuses to run when any output differs from frozen_hashes.json."""
    frozen = json.loads((REPO / PROCESSED / "frozen_hashes.json").read_text(encoding="utf-8"))["files"]
    for relative, expected in frozen.items():
        if sha256_file(REPO / INTERIM / relative) != expected:
            raise ValueError(f"FROZEN_HASH_MISMATCH {relative}")
    return frozen


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> dict:
    m68 = importlib.import_module("scripts.68_run_t1_evaluation")
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: m68._fmt(row.get(column)) for column in columns})
    keys = [tuple(m68._fmt(row.get(c)) for c in columns) for row in rows]
    return {"rows": len(rows), "columns": len(columns), "duplicate_rows": len(keys) - len(set(keys))}


def paired_vs(run, P, stats, np, system: str, ref: str, column: str) -> dict:
    """Paired accuracy comparison of ``system`` against ``ref`` on one column (scripts/68 recipe)."""
    dataset, gold = run.column_frame(column)
    a, b = run.predictions.get((system, dataset)), run.predictions.get((ref, dataset))
    if a is None or b is None:
        return {"system": system, "reference": ref, "column": column, "status": "NOT_RUN"}
    keys, golds, clusters = gold["key"], gold["gold_system"].tolist(), gold["cluster"].tolist()
    la, lb = [a[k] for k in keys], [b[k] for k in keys]
    ua, ub = P.to_units(golds, la), P.to_units(golds, lb)
    ga, gb = P.aggregate_by_cluster(ua, clusters), P.aggregate_by_cluster(ub, clusters)
    ids = np.arange(len(ga))
    delta = stats.paired_bootstrap_delta(P.accuracy_stat, ga, gb, cluster_ids=ids, n_resamples=RESAMPLES, seed=CI_SEED)
    b_only = sum(x == g and y != g for x, y, g in zip(la, lb, golds))
    c_only = sum(x != g and y == g for x, y, g in zip(la, lb, golds))
    mc = stats.mcnemar_exact(b_only, c_only)
    rnd = stats.approximate_randomization(P.accuracy_stat, ua, ub, n_permutations=RESAMPLES, seed=CI_SEED)
    return {"system": system, "reference": ref, "column": column, "status": "OK", "n": len(keys),
            "acc_system": P.accuracy_stat(ua), "acc_reference": P.accuracy_stat(ub),
            "delta_acc": P.accuracy_stat(ua) - P.accuracy_stat(ub), "delta_ci_low": delta.get("ci_low"),
            "delta_ci_high": delta.get("ci_high"), "mcnemar_b_system_only": b_only, "mcnemar_c_reference_only": c_only,
            "mcnemar_p": mc.get("p_value"), "randomization_p": rnd.get("p_value")}


PER_SEED_EXTRA = ["seed", "label"]
BREAKDOWN_EXTRA = ["seed", "label"]
MEAN_FIELDS = ("accuracy", "macro_f1", "lai_precision", "lai_recall", "lai_f1", "coverage", "abstain_rate")


def cmd_score(args) -> int:
    import numpy as np
    global PROCESSED
    if args.out:  # re-score the same frozen outputs into a new directory (reproducibility check)
        source = REPO / PROCESSED
        target = guard_output_dir(args.out)
        target.mkdir(parents=True)
        shutil.copy2(source / "frozen_hashes.json", target / "frozen_hashes.json")
        manifest = json.loads((source / "run_manifest.json").read_text(encoding="utf-8"))
        manifest["status"] = "DECLARED_BEFORE_SCORING"
        manifest.pop("outputs", None)
        dump_json(target / "run_manifest.json", manifest)
        PROCESSED = target.relative_to(REPO)
    verify_frozen()
    m68 = importlib.import_module("scripts.68_run_t1_evaluation")
    m68.CI_SEED = CI_SEED  # in-process override of the CI seed (the file is untouched)
    for name, definition in EXTRA_DEFINITIONS.items():
        m68.SYSTEM_DEFINITIONS.setdefault(name, definition)
    P = importlib.import_module("src.evaluation.t1_pipeline")
    stats = importlib.import_module("src.evaluation.stats")
    out = REPO / PROCESSED
    manifest = json.loads((out / "run_manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] != "DECLARED_BEFORE_SCORING":
        raise SystemExit("run_manifest.json is not in DECLARED_BEFORE_SCORING state; refusing to score twice")
    (out / "tables").mkdir()

    run = m68.Run(REPO / SETS_DIR, out, RESAMPLES)
    run.cell_status = {}
    run.load_sets()
    run.load_corpus()
    run.build_gold()
    tier1_manifest = json.loads((REPO / TIER1_RUN / "run_manifest.json").read_text(encoding="utf-8"))
    if sha256_file(REPO / TIER1_RUN / "predictions.jsonl") != tier1_manifest["outputs"]["predictions.jsonl"]["sha256"]:
        raise ValueError("tier-1 predictions.jsonl differs from its manifest")
    base: dict = {}
    for row in P.read_jsonl(REPO / TIER1_RUN / "predictions.jsonl"):
        if row["system"] in REFERENCE_SYSTEMS:
            base.setdefault((row["system"], row["dataset"]), {})[row["key"]] = row["predicted_system"]

    # Re-derive the tier-1 reference cells and compare with the published tier-1 table.
    run.predictions = dict(base)
    tier1_table = {(r["system"], r["column"]): r for r in csv.DictReader(
        (REPO / TIER1_RUN / "tables" / "h5_main.csv").open(encoding="utf-8-sig", newline=""))}
    columns = list(m68.COLUMNS) + list(m68.EXTRA_COLUMNS)
    check_rows = []
    for system in REFERENCE_SYSTEMS:
        for column in m68.COLUMNS:
            cell = run.score_cell(system, column, with_ci=False)
            published = tier1_table[(system, column)]
            check_rows.append({"system": system, "column": column, "n": cell["n"], "accuracy_here": cell["accuracy"],
                               "accuracy_tier1": published["accuracy"],
                               "match": abs(float(cell["accuracy"]) - float(published["accuracy"])) < 5e-7})
    write_csv(out / "tables" / "tier1_reference_check.csv", check_rows,
              ["system", "column", "n", "accuracy_here", "accuracy_tier1", "match"])
    if not all(r["match"] for r in check_rows):
        raise ValueError("tier-1 reference cells do not reproduce the published table")

    heur = P.load_locked_heur(REPO)
    texts = {d: dict(zip(run.texts[d]["key"], P.inference_texts(run.texts[d]))) for d in SCORED_DATASETS}
    per_seed_rows, breakdowns, paired_rows, probe_rows, reject_rows, pred_out = [], {"kieu_lai": [], "situation": [], "province": []}, [], [], [], []
    cell_details = {}
    for seed in SEEDS:
        dyn_dir, pcrf_dir = REPO / INTERIM / run_name("dyn", seed), REPO / INTERIM / run_name("pcrf", seed)
        neural = {}
        for model, directory in (("dyn", dyn_dir), ("pcrf", pcrf_dir)):
            if not (directory / "inference_done.json").exists():
                continue
            rows = {}
            for r in P.read_jsonl(directory / "predictions.jsonl"):
                rows.setdefault(r["dataset"], {})[r["key"]] = r
            neural[model] = rows
            done = json.loads((directory / "inference_done.json").read_text(encoding="utf-8"))
            for dataset, info in done["counts"].items():
                reject_rows.append({"seed": seed, "model": model, "dataset": dataset, **info})
        preds = dict(base)
        for dataset in SCORED_DATASETS:
            keys = run.texts[dataset]["key"].tolist()
            if "dyn" in neural:
                rows = neural["dyn"][dataset]
                preds[(DYN_SYS, dataset)] = {k: final_label(rows[k]) for k in keys}
                preds[(DYN_ARGMAX, dataset)] = {k: argmax_label(rows[k]) for k in keys}
                preds[(PIPE_DYN, dataset)] = {k: P.pipe_predict(heur, texts[dataset][k], rows[k]["spans"])[0] for k in keys}
            if "pcrf" in neural:
                rows = neural["pcrf"][dataset]
                preds[(PIPE_PCRF, dataset)] = {k: P.pipe_predict(heur, texts[dataset][k], rows[k]["spans"])[0] for k in keys}
        # Probe on the CLS vectors of the same-seed DYN encoder.
        if "dyn" in neural:
            def cls(name):
                meta = json.loads((dyn_dir / f"cls_{name}.keys.json").read_text(encoding="utf-8"))
                return meta["keys"], np.load(dyn_dir / f"cls_{name}.npy"), np.asarray(meta["valid"], dtype=bool)

            train, dev = run.sets["t1_synth_train"], run.sets["t1_synth_dev"]
            k_tr, x_tr, v_tr = cls("t1_synth_train")
            k_dv, x_dv, v_dv = cls("t1_synth_dev")
            k_s3, x_s3, v_s3 = cls("s3_train")
            if k_tr != train["key"].tolist() or k_dv != dev["key"].tolist():
                raise ValueError("CLS keys do not match the synthetic sets")
            s3_label = {r["sample_id"]: r.get("address_system") for r in run.records["train"]}
            s3_rows = [i for i, k in enumerate(k_s3) if s3_label[k] in P.CLASSES and v_s3[i]]
            tr_rows = [i for i in range(len(k_tr)) if v_tr[i]]
            dv_rows = [i for i in range(len(k_dv)) if v_dv[i]]
            y_tr = [P.CLASSES.index(train["gold_system"].iloc[i]) for i in tr_rows]
            y_dv = [P.CLASSES.index(dev["gold_system"].iloc[i]) for i in dv_rows]
            y_s3 = [P.CLASSES.index(s3_label[k_s3[i]]) for i in s3_rows]
            variants = {PROBE: (np.vstack([x_tr[tr_rows], x_s3[s3_rows]]), y_tr + y_s3),
                        PROBE_SYNTH: (x_tr[tr_rows], y_tr)}
            for system, (x_fit, y_fit) in variants.items():
                model, l2, trials = fit_probe(P, x_fit, y_fit, x_dv[dv_rows], y_dv)
                probe_rows.append({"seed": seed, "system": system, "selected_l2": l2, "tie_on_dev": l2_is_tie(trials),
                                   "dev_macro_f1_by_l2": {t["l2"]: t["dev_macro_f1"] for t in trials},
                                   "dev_accuracy_by_l2": {t["l2"]: t["dev_accuracy"] for t in trials},
                                   "train_rows": len(y_fit), "train_class_counts": dict(Counter(P.CLASSES[i] for i in y_fit)),
                                   "dev_rows": len(dv_rows), "feature_dim": int(x_fit.shape[1])})
                for dataset in SCORED_DATASETS:
                    keys, matrix, valid = cls(dataset)
                    if keys != run.texts[dataset]["key"].tolist():
                        raise ValueError(f"CLS keys do not match {dataset}")
                    predicted = model.predict(matrix)
                    preds[(system, dataset)] = {k: (P.CLASSES[i] if ok else P.ABSTAIN) for k, i, ok in zip(keys, predicted, valid)}
        run.predictions = preds
        for system in NEURAL_SYSTEMS:
            for column in columns:
                if (system, m68.COLUMNS.get(column, m68.EXTRA_COLUMNS.get(column))[0]) not in preds:
                    continue
                cell = run.score_cell(system, column)
                cell_details[f"seed{seed}|{system}|{column}"] = cell.pop("_detail", {})
                per_seed_rows.append({**cell, "seed": seed, "label": LABEL})
            for column in m68.COLUMNS:
                for ref in (HEUR, FEAT):
                    paired_rows.append({"seed": seed, **paired_vs(run, P, stats, np, system, ref, column)})
        for kind in breakdowns:
            for r in run.breakdown_rows([s for s in NEURAL_SYSTEMS if any(k[0] == s for k in preds)], kind):
                breakdowns[kind].append({**r, "seed": seed, "label": LABEL})
        for (system, dataset), labels in sorted(preds.items()):
            if system in NEURAL_SYSTEMS:
                pred_out.extend({"seed": seed, "dataset": dataset, "key": k, "system": system, "predicted_system": v}
                                for k, v in labels.items())

    outputs = {}
    outputs["tables/h5_tier2_local_per_seed.csv"] = write_csv(
        out / "tables" / "h5_tier2_local_per_seed.csv", per_seed_rows, PER_SEED_EXTRA + m68.H5_COLUMNS)
    # mean +- std over seeds
    ms_rows = []
    for system in NEURAL_SYSTEMS:
        for column in columns:
            cells = [r for r in per_seed_rows if r["system"] == system and r["column"] == column]
            if not cells:
                continue
            entry = {"system": system, "column": column, "label": LABEL, "seeds": len(cells),
                     "column_label": cells[0]["column_label"], "status": cells[0]["status"]}
            for field in MEAN_FIELDS:
                stat = mean_std([c.get(field) for c in cells])
                entry.update({f"{field}_mean": stat["mean"], f"{field}_std": stat["std"], f"{field}_n": stat["n"]})
            entry["per_seed_accuracy"] = "; ".join(f"{c['seed']}:{float(c['accuracy']):.4f}" for c in cells if c["status"] == "OK")
            ms_rows.append(entry)
    ms_cols = ["system", "column", "label", "column_label", "status", "seeds"] + [
        f"{f}_{s}" for f in MEAN_FIELDS for s in ("mean", "std", "n")] + ["per_seed_accuracy"]
    outputs["tables/h5_tier2_local_mean_std.csv"] = write_csv(out / "tables" / "h5_tier2_local_mean_std.csv", ms_rows, ms_cols)
    for kind, rows in breakdowns.items():
        name = f"tables/h5_tier2_local_by_{kind}.csv"
        outputs[name] = write_csv(out / name, rows, BREAKDOWN_EXTRA + m68.BREAKDOWN_COLUMNS)
    paired_cols = ["seed", "system", "reference", "column", "status", "n", "acc_system", "acc_reference", "delta_acc",
                   "delta_ci_low", "delta_ci_high", "mcnemar_b_system_only", "mcnemar_c_reference_only", "mcnemar_p",
                   "randomization_p"]
    outputs["tables/paired_vs_heur_and_feat.csv"] = write_csv(out / "tables" / "paired_vs_heur_and_feat.csv", paired_rows, paired_cols)
    outputs["tables/rejections.csv"] = write_csv(out / "tables" / "rejections.csv", reject_rows,
                                                 ["seed", "model", "dataset", "rows", "processor_rejected"])
    flat_probe = [{**r, "dev_macro_f1_by_l2": json.dumps(r["dev_macro_f1_by_l2"]),
                   "dev_accuracy_by_l2": json.dumps(r["dev_accuracy_by_l2"]),
                   "train_class_counts": json.dumps(r["train_class_counts"])} for r in probe_rows]
    outputs["tables/probe_selection.csv"] = write_csv(out / "tables" / "probe_selection.csv", flat_probe,
        ["seed", "system", "selected_l2", "tie_on_dev", "dev_macro_f1_by_l2", "dev_accuracy_by_l2", "train_rows",
         "train_class_counts", "dev_rows", "feature_dim"])
    with (out / "predictions_tier2_local.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
        for row in pred_out:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    outputs["predictions_tier2_local.jsonl"] = {"rows": len(pred_out)}
    dump_json(out / "metrics.json", {"label": LABEL, "cells": cell_details, "probe": probe_rows})
    for name in list(outputs) + ["metrics.json"]:
        outputs.setdefault(name, {})["sha256"] = sha256_file(out / name)
    manifest.update({"status": "SCORED", "scored_at": now_iso(), "outputs": outputs,
                     "frozen_hashes_sha256": sha256_file(out / "frozen_hashes.json"),
                     "rows_in": {d: len(run.texts[d]) for d in SCORED_DATASETS},
                     "code_sha256_at_scoring": {"scripts/68c_run_t1_tier2_local.py": sha256_file(Path(__file__))}})
    dump_json(out / "run_manifest.json", manifest)
    print(json.dumps({"scored": True, "cells": len(per_seed_rows)}))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "smoke-all", "smoke-summary", "infer-all", "freeze", "score", "smoke", "infer"))
    parser.add_argument("--model", choices=("dyn", "pcrf"))
    parser.add_argument("--seed", type=int)
    parser.add_argument("--out", type=Path, help="score: write into this new directory instead of the package one")
    args = parser.parse_args(argv)
    return {"prepare": cmd_prepare, "smoke-all": cmd_smoke_all, "smoke-summary": cmd_smoke_summary,
            "infer-all": cmd_infer_all, "freeze": cmd_freeze, "score": cmd_score,
            "smoke": cmd_smoke, "infer": cmd_infer}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
