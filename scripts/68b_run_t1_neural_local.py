"""Tier 2 of WP2: local CPU inference of the frozen DYN / PHOBERT-CRF checkpoints.

Run with the neural runtime as its own process (numpy + torch, no pandas):
    OMP_NUM_THREADS=6 MKL_NUM_THREADS=6 PYTHONDONTWRITEBYTECODE=1 \
        data/interim/modeling/sprint03/runtime_neural_d_v1/bin/python scripts/68b_run_t1_neural_local.py

It reads the text-only inputs saved by tier 1 (``<run>/tier2_inputs``) and
writes ``<run>/tier2/`` (never overwritten):
    status.json                 SMOKE_PASS or BLOCKED_LOCAL_NEURAL with the verbatim error
    dyn_predictions.jsonl       spans, predicted_system, posterior (locked threshold/margin)
    pcrf_predictions.jsonl      spans of PHOBERT-CRF (when it loads)
    cls_<set>.npy / .keys.json  frozen-encoder CLS vectors for T1-HEAD-PROBE

No locked code, hash or check is modified, patched or bypassed.  The adapter is
built only through ``modeling_config`` + ``build_adapter``; if the locked
preflight or checkpoint checks refuse, the run stops with BLOCKED_LOCAL_NEURAL
and the verbatim error.  The smoke step compares five test samples with the
frozen Sprint 3 predictions before anything else is run; any span difference
stops tier 2.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
import traceback

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

DEFAULT_OUT = Path("data/processed/evaluation/sprint04/t1_h5_20261015_v1")
THREADS = 6
SMOKE_SAMPLES = 5
POSTERIOR_TOLERANCE = 1e-4
RELEASE = Path("data/interim/modeling/sprint03/release_and_kaggle_20261005_v1")
NEURAL_RUNS = Path("data/interim/modeling/sprint03/final_completion_20261005_v1/kaggle_final_output_v4/dacn_artifacts/"
                   "dacn-s3-final-infer-20261005-v4/workspace/data/interim/modeling/sprint03/"
                   "dacn-s3-final-infer-20261005-v4")
MODELS = {
    "dyn": {
        "frozen_run": NEURAL_RUNS / "dyn_test",
        "workspace": RELEASE / "dyn_c02_selection_artifacts_v1/dacn_artifacts/dacn-s3-dyn-c02-20261005-v1/workspace",
    },
    "pcrf": {
        "frozen_run": NEURAL_RUNS / "pcrf_test",
        "workspace": RELEASE / "pcrf_c02_selection_artifacts_v2/dacn_artifacts/dacn-s3-pcrf-c02-20261005-v1/workspace",
    },
}
LOCAL_JAVA_DIR = Path("data/interim/modeling/sprint03/resources_d_v1/java17")
DYN_SETS = ("synth_eval", "data06")  # sets on which DYN / PCRF predictions are scored
CLS_SETS = ("t1_synth_train", "t1_synth_dev", "synth_eval", "data06", "s3_train", "s3_dev", "s3_test")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def dump_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def locked_pieces(name: str) -> dict:
    """Frozen model config of the Sprint 3 test run and the local files it names."""
    spec = MODELS[name]
    frozen = json.loads((REPO / spec["frozen_run"] / "model_config.json").read_text(encoding="utf-8"))
    resources = frozen["resources"]
    checkpoint = REPO / spec["workspace"] / resources["checkpoint"]["path"]
    if sha256_file(checkpoint) != resources["checkpoint"]["sha256"]:
        raise ValueError(f"HASH_MISMATCH checkpoint of {name}")
    policy_path = None
    if "decoder_policy" in resources:
        policy_path = REPO / spec["workspace"] / resources["decoder_policy"]["path"]
        if sha256_file(policy_path) != resources["decoder_policy"]["sha256"]:
            raise ValueError(f"HASH_MISMATCH decoder policy of {name}")
    return {
        "frozen": frozen,
        "training_config": frozen["adapter_kwargs"]["config"],
        "checkpoint": checkpoint,
        "resource_lock": REPO / frozen["adapter_kwargs"]["resource_lock_path"],
        "decoder_policy_path": policy_path,
        "decoder_policy": frozen["adapter_kwargs"].get("decoder_policy"),
    }


def build_prescribed(pieces: dict, device: str | None = None):
    """Path named by the work package: modeling_config + build_adapter.

    ``device=None`` keeps the frozen training config untouched.  ``device="cpu"``
    only changes that one field in a copy; the locked checkpoint signature
    check then decides whether such a config may load the weights.  Nothing is
    patched, injected or skipped in either case.
    """
    from src.evaluation.dev_runner import build_adapter
    from src.evaluation.experiment_config import modeling_config

    training = copy.deepcopy(pieces["training_config"])
    if device is not None:
        training["device"] = device
    config = modeling_config("wp2_local_dev_smoke", training, pieces["checkpoint"],
                             pieces["resource_lock"], pieces["decoder_policy_path"])
    return build_adapter(config)


def use_project_java() -> str | None:
    """Put the project-local JRE (already on disk since Sprint 3) on PATH when no java is visible."""
    import os
    import shutil

    if shutil.which("java"):
        return shutil.which("java")
    for candidate in sorted((REPO / LOCAL_JAVA_DIR).glob("*/bin/java")):
        os.environ["PATH"] = str(candidate.parent) + os.pathsep + os.environ.get("PATH", "")
        return str(candidate)
    return None


def load_adapter(name: str) -> tuple[object | None, dict]:
    report = {"model": name, "attempts": []}
    try:
        pieces = locked_pieces(name)
    except Exception:  # noqa: BLE001 - the verbatim error is the deliverable
        report["attempts"].append({"path": "locked_pieces", "ok": False, "error": traceback.format_exc()})
        return None, report
    for label, device in (("modeling_config+build_adapter, frozen training config", None),
                          ("modeling_config+build_adapter, device=cpu in a config copy", "cpu")):
        started = time.perf_counter()
        try:
            adapter = build_prescribed(pieces, device)
            report["attempts"].append({"path": label, "ok": True, "seconds": round(time.perf_counter() - started, 1)})
            report["loaded_via"] = label
            return adapter, report
        except Exception:  # noqa: BLE001
            report["attempts"].append({"path": label, "ok": False, "error": traceback.format_exc()})
    return None, report


class ClsCapture:
    """Forward hook that keeps the encoder CLS vector of the last model call."""

    def __init__(self, model) -> None:
        self.last = None
        self.handle = model.register_forward_hook(self._hook)

    def _hook(self, module, inputs, output):
        self.last = output["cls"][0].detach().cpu().numpy().copy()

    def take(self):
        value, self.last = self.last, None
        return value


def span_keys(spans) -> list[tuple[int, int, str]]:
    return sorted((s["start"], s["end"], s["label"]) for s in spans)


def smoke(adapter, inputs: list[dict], frozen: dict[str, dict], with_t1: bool) -> dict:
    rows, ok = [], True
    for item in inputs[:SMOKE_SAMPLES]:
        output = adapter.parse_spans(item["text"], sample_id=item["key"])
        reference = frozen[item["key"]]
        local_spans = span_keys([s.to_dict() for s in output.spans])
        row = {"key": item["key"], "spans_equal": local_spans == span_keys(reference["spans"])}
        if with_t1:
            local = output.trace["structure"]["posterior"]
            ref = reference["trace"]["structure"]["posterior"]
            row["posterior_max_abs_diff"] = max(abs(local[k] - ref[k]) for k in ref)
            row["system_equal"] = output.predicted_system == reference["predicted_system"]
            row["posterior_within_tolerance"] = row["posterior_max_abs_diff"] <= POSTERIOR_TOLERANCE
            ok &= row["system_equal"] and row["posterior_within_tolerance"]
        ok &= row["spans_equal"]
        rows.append(row)
    return {"passed": bool(ok), "samples": rows, "posterior_tolerance": POSTERIOR_TOLERANCE}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--smoke-only", action="store_true")
    args = parser.parse_args(argv)
    run_dir = args.output if args.output.is_absolute() else REPO / args.output
    inputs_dir, out = run_dir / "tier2_inputs", run_dir / "tier2"
    if not (inputs_dir / "tier2_inputs.json").exists():
        raise SystemExit(f"{inputs_dir} is missing; run tier 1 first")
    if out.exists():
        raise SystemExit(f"{out} already exists; refusing to overwrite")
    listing = json.loads((inputs_dir / "tier2_inputs.json").read_text(encoding="utf-8"))
    inputs = {}
    for name, info in listing["files"].items():
        path = inputs_dir / f"{name}.jsonl"
        if sha256_file(path) != info["sha256"]:
            raise SystemExit(f"HASH_MISMATCH {path}")
        inputs[name] = read_jsonl(path)  # rows are {"key", "text"} only

    import numpy as np
    import torch

    torch.set_num_threads(THREADS)
    out.mkdir()
    status = {"status": "BLOCKED_LOCAL_NEURAL", "python": platform.python_version(), "torch": torch.__version__,
              "java": use_project_java(), "cuda_available": bool(torch.cuda.is_available()),
              "threads": torch.get_num_threads(), "inputs": {n: len(rows) for n, rows in inputs.items()},
              "models": {}}

    def finish(code: int) -> int:
        dump_json(out / "status.json", status)
        print(json.dumps({k: v for k, v in status.items() if k != "models"}, ensure_ascii=False, indent=1))
        return code

    dyn, report = load_adapter("dyn")
    status["models"]["dyn"] = report
    if dyn is None:
        status["reason"] = "DYN checkpoint could not be loaded locally; see models.dyn.attempts"
        return finish(3)
    frozen_dyn = {r["sample_id"]: r for r in read_jsonl(REPO / MODELS["dyn"]["frozen_run"] / "predictions.jsonl")}
    try:
        status["smoke"] = smoke(dyn, inputs["s3_test"], frozen_dyn, with_t1=True)
    except Exception:  # noqa: BLE001
        status["smoke"] = {"passed": False, "error": traceback.format_exc()}
    if not status["smoke"]["passed"]:
        status["reason"] = "smoke comparison with the frozen Sprint 3 predictions failed"
        return finish(3)
    status["status"] = "SMOKE_PASS"
    if args.smoke_only:
        status["note"] = "smoke only; no inference written"
        return finish(0)

    capture = ClsCapture(dyn.model)
    outputs = {}
    started = time.perf_counter()
    with (out / "dyn_predictions.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
        for name in CLS_SETS:
            vectors, valid = [], []
            for item in inputs[name]:
                output = dyn.parse_spans(item["text"], sample_id=item["key"])
                vector = capture.take()
                valid.append(vector is not None)  # None: the processor rejected the text, no model call
                vectors.append(vector if vector is not None else np.zeros(dyn.model.t1_head.in_features, dtype=np.float32))
                if name in DYN_SETS:
                    structure = output.trace.get("structure") or {}
                    stream.write(json.dumps({
                        "dataset": name, "key": item["key"],
                        "spans": [{"start": s.start, "end": s.end, "label": s.label} for s in output.spans],
                        "predicted_system": "khong_ro" if output.abstain else output.predicted_system,
                        "posterior": structure.get("posterior"), "threshold": structure.get("threshold"),
                        "margin_required": structure.get("margin_required"), "status": output.status,
                    }, ensure_ascii=False) + "\n")
            np.save(out / f"cls_{name}.npy", np.asarray(vectors, dtype=np.float32))
            dump_json(out / f"cls_{name}.keys.json", {"keys": [item["key"] for item in inputs[name]], "valid": valid})
            outputs[f"cls_{name}.npy"] = {"rows": len(vectors), "invalid_rows": valid.count(False),
                                          "sha256": sha256_file(out / f"cls_{name}.npy")}
            print(f"[dyn] {name}: {len(vectors)} rows, {time.perf_counter() - started:.0f}s", flush=True)
    outputs["dyn_predictions.jsonl"] = {"sha256": sha256_file(out / "dyn_predictions.jsonl")}
    status["dyn_seconds"] = round(time.perf_counter() - started, 1)
    capture.handle.remove()
    del dyn

    pcrf, report = load_adapter("pcrf")
    status["models"]["pcrf"] = report
    if pcrf is not None:
        frozen_pcrf = {r["sample_id"]: r for r in read_jsonl(REPO / MODELS["pcrf"]["frozen_run"] / "predictions.jsonl")}
        try:
            status["smoke_pcrf"] = smoke(pcrf, inputs["s3_test"], frozen_pcrf, with_t1=False)
        except Exception:  # noqa: BLE001
            status["smoke_pcrf"] = {"passed": False, "error": traceback.format_exc()}
        if status["smoke_pcrf"]["passed"]:
            started = time.perf_counter()
            with (out / "pcrf_predictions.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
                for name in DYN_SETS:
                    for item in inputs[name]:
                        output = pcrf.parse_spans(item["text"], sample_id=item["key"])
                        stream.write(json.dumps({
                            "dataset": name, "key": item["key"],
                            "spans": [{"start": s.start, "end": s.end, "label": s.label} for s in output.spans],
                            "status": output.status}, ensure_ascii=False) + "\n")
                    print(f"[pcrf] {name}: {time.perf_counter() - started:.0f}s", flush=True)
            outputs["pcrf_predictions.jsonl"] = {"sha256": sha256_file(out / "pcrf_predictions.jsonl")}
            status["pcrf_seconds"] = round(time.perf_counter() - started, 1)
    status["outputs"] = outputs
    return finish(0)


if __name__ == "__main__":
    sys.exit(main())
