"""Text-only T0/T1 dev inference and a separate, frozen scoring stage."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib
from importlib import metadata
import inspect
import json
import os
from pathlib import Path
import platform
import random
import subprocess
from time import perf_counter

from src.evaluation.schema import ADDRESS_SYSTEMS, SPAN11_LABELS, CharacterSpan, SpanModelOutput
from src.evaluation.span_scorer import compute_exact_span_metrics, evaluate_single_sample_spans, validate_span_integrity

ROOT = Path(__file__).resolve().parents[2]
STATUSES = {"ok", "abstain", "runtime_error", "invalid_output", "missing_prediction"}


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(path)
    values = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if any(not isinstance(row, dict) for row in values):
        raise ValueError("JSONL records must be objects")
    return values


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, values: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in values), encoding="utf-8")


def validate_dev_samples(samples: list[dict]) -> None:
    if not samples or any(set(row) != {"sample_id", "text"} for row in samples):
        raise ValueError("Dev inference input must contain only sample_id and text")
    ids = [row["sample_id"] for row in samples]
    if any(not isinstance(sid, str) or not sid for sid in ids) or len(set(ids)) != len(ids):
        raise ValueError("Dev inference IDs must be nonempty and unique")
    if any(not isinstance(row["text"], str) for row in samples):
        raise ValueError("Dev inference text must be a string")


def check_release_file(path: Path, manifest_path: Path, artifact_name: str) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "TRAIN_DEV_APPROVED_TEST_PENDING":
        raise ValueError(f"Dev run blocked by corpus status: {manifest.get('status')}")
    expected = manifest.get("output_sha256", {}).get(artifact_name)
    if not expected or file_hash(path) != expected:
        raise ValueError(f"Frozen {artifact_name} hash differs from corpus manifest")
    return manifest


def load_dev_input(path: Path, manifest_path: Path) -> list[dict]:
    manifest = check_release_file(path, manifest_path, "dev_input.jsonl")
    samples = read_jsonl(path)
    validate_dev_samples(samples)
    if len(samples) != manifest["sample_counts"]["dev"]:
        raise ValueError("Dev input sample count differs from corpus manifest")
    return samples


def validate_config(config: dict) -> None:
    if not isinstance(config.get("model_id"), str) or not config["model_id"]:
        raise ValueError("model_id is required")
    if not isinstance(config.get("run_id"), str) or "dev" not in config["run_id"].casefold():
        raise ValueError("run_id must identify a dev run")
    if type(config.get("seed")) is not int:
        raise ValueError("An explicit integer seed is required")
    labels = config.get("supported_labels")
    if not isinstance(labels, list) or not labels or len(labels) != len(set(labels)) or set(labels) - set(SPAN11_LABELS):
        raise ValueError("supported_labels must be a nonempty schema subset")
    if not isinstance(config.get("adapter_kwargs", {}), dict):
        raise ValueError("adapter_kwargs must be an object")


def resource_manifest(config: dict, root: Path = ROOT) -> dict:
    entries = {}
    for name, value in config.get("resources", {}).items():
        if value.get("role") not in {"gazetteer", "checkpoint", "tokenizer", "segmenter", "rules"}:
            raise ValueError(f"Resource {name}: unsupported role")
        path = Path(value["path"])
        if not path.is_absolute():
            path = root / path
        path = path.resolve()
        # Annotation/benchmark files are never model resources, even if a
        # caller gives them a misleading checkpoint or gazetteer role.
        blocked = [root / "data/processed/annotation", root / "data/interim/annotation", root / "data/processed/benchmark"]
        if any(path.is_relative_to(item.resolve()) for item in blocked):
            raise ValueError(f"Resource {name}: gold/annotation/benchmark access is forbidden")
        if not path.is_file():
            raise FileNotFoundError(path)
        digest = file_hash(path)
        if not value.get("sha256") or value["sha256"] != digest:
            raise ValueError(f"Resource {name}: explicit SHA-256 does not match")
        entries[name] = {"path": value["path"], "role": value["role"], "sha256": digest}
    return entries


def runtime_manifest() -> dict:
    packages = {dist.metadata["Name"]: dist.version for dist in metadata.distributions() if dist.metadata.get("Name")}
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False)
    return {
        "python": platform.python_version(), "platform": platform.platform(),
        "machine": platform.machine(), "cpu_count": os.cpu_count(),
        "gpu": "NOT_INSPECTED", "packages": dict(sorted(packages.items())),
        "git_commit": revision.stdout.strip() if revision.returncode == 0 else None,
        "code_sha256": {name: file_hash(ROOT / name) for name in (
            "src/evaluation/dev_runner.py", "src/evaluation/schema.py", "src/evaluation/span_scorer.py",
            "src/evaluation/adapters/base.py", "scripts/23_run_span_dev.py", "scripts/24_score_span_dev.py")},
    }


def run_dev_inference(adapter: object, samples: list[dict], config: dict, output_dir: Path,
                      input_manifest: dict | None = None) -> dict:
    """Core also supports local fixtures. The CLI enforces corpus approval."""
    validate_dev_samples(samples)
    validate_config(config)
    resources = resource_manifest(config)
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite run: {output_dir}")
    random.seed(config["seed"])
    predictions = []
    for row in samples:
        started = perf_counter()
        raw = None
        adapter_returned = False
        try:
            # Neither sample ID, gold nor source metadata is passed to the
            # parser. The runner attaches the ID after parsing the text.
            output = adapter.parse_spans(row["text"])
            adapter_returned = True
            latency = (perf_counter() - started) * 1000
            if not isinstance(output, SpanModelOutput):
                raise TypeError("Adapter must return SpanModelOutput")
            raw = output.to_dict()
            issues = validate_span_integrity(output.spans, row["text"])
            if any(span.text != row["text"][span.start:span.end] for span in output.spans):
                issues.append("Span literal text does not round-trip to the original substring")
            if output.raw_text != row["text"]:
                issues.append("Adapter changed original text")
            if output.predicted_system not in (*ADDRESS_SYSTEMS, "khong_ro"):
                issues.append("Invalid predicted T1 system")
            if output.status not in STATUSES:
                issues.append("Invalid output status")
            if any(span.label not in config["supported_labels"] for span in output.spans):
                issues.append("Adapter produced a label outside its declared supported subset")
            json.dumps(raw, ensure_ascii=False, allow_nan=False)
            if issues:
                output = SpanModelOutput(row["sample_id"], row["text"], abstain=True,
                    status="invalid_output", raw_output=raw, error="; ".join(issues), trace={"validation_issues": issues})
            else:
                output.sample_id = row["sample_id"]
                if output.status == "ok" and output.abstain:
                    output.status = "abstain"
                if output.status in {"runtime_error", "invalid_output", "missing_prediction"}:
                    output = SpanModelOutput(row["sample_id"], row["text"], abstain=True,
                        status=output.status, raw_output=raw, error=output.error or "Adapter reported failure")
                elif output.raw_output is None:
                    output.raw_output = raw
            output.latency_ms = latency
        except Exception as exc:
            output = SpanModelOutput(row["sample_id"], row["text"], abstain=True,
                status="invalid_output" if adapter_returned else "runtime_error", latency_ms=(perf_counter() - started) * 1000,
                raw_output=repr(raw) if raw is not None else None,
                error=f"{type(exc).__name__}: {exc}")
        predictions.append(output.to_dict())
    output_dir.mkdir(parents=True)
    write_jsonl(output_dir / "predictions.jsonl", predictions)
    write_json(output_dir / "model_config.json", config)
    latencies = sorted(row["latency_ms"] for row in predictions)
    manifest = {
        "run_id": config["run_id"], "model_id": config["model_id"], "track": "T0_T1_DEV", "split": "dev",
        "stage": "inference", "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_count": len(samples), "supported_labels": config["supported_labels"],
        "status_counts": dict(Counter(row["status"] for row in predictions)),
        "seed": config["seed"], "seed_scope": "Python random; adapter determinism must be specified in adapter config",
        "resources": resources, "runtime": runtime_manifest(),
        "adapter_code": {"path": inspect.getsourcefile(type(adapter)),
                         "sha256": file_hash(Path(inspect.getsourcefile(type(adapter)))) if inspect.getsourcefile(type(adapter)) else None},
        "inputs": input_manifest or {"scope": "local fixture, not a benchmark model run"},
        "adapter_input_permission": "Original text only; runner attaches sample_id after parse_spans",
        "output_sha256": {name: file_hash(output_dir / name) for name in ("predictions.jsonl", "model_config.json")},
        "latency_ms": {"mean": sum(latencies) / len(latencies), "p50": latencies[len(latencies)//2], "p95": latencies[min(len(latencies)-1, int(len(latencies)*0.95))]},
    }
    write_json(output_dir / "run_manifest.json", manifest)
    return manifest


def load_predictions(path: Path) -> list[SpanModelOutput]:
    outputs = []
    for row in read_jsonl(path):
        spans = [CharacterSpan(**span) for span in row["spans"]]
        issues = validate_span_integrity(spans, row["raw_text"])
        if any(span.text != row["raw_text"][span.start:span.end] for span in spans):
            issues.append("Stored span text does not match the original substring")
        if issues:
            raise ValueError(f"{row['sample_id']}: invalid stored prediction: {issues}")
        if row.get("status", "ok") not in STATUSES:
            raise ValueError("Invalid stored prediction status")
        if row.get("status") in {"runtime_error", "invalid_output", "missing_prediction"} and (spans or not row.get("abstain")):
            raise ValueError("Failure predictions must explicitly abstain with empty scored spans")
        outputs.append(SpanModelOutput(**{**row, "spans": spans}))
    return outputs


def score_dev_predictions(prediction_path: Path, gold_path: Path, run_dir: Path,
                          corpus_manifest_path: Path) -> dict:
    corpus_manifest = check_release_file(gold_path, corpus_manifest_path, "dev.jsonl")
    run_manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    if run_manifest.get("split") != "dev" or run_manifest.get("track") != "T0_T1_DEV":
        raise ValueError("Only dev runs may be scored here")
    if file_hash(prediction_path) != run_manifest["output_sha256"]["predictions.jsonl"]:
        raise ValueError("Predictions changed after inference was frozen")
    if file_hash(run_dir / "model_config.json") != run_manifest["output_sha256"]["model_config.json"]:
        raise ValueError("Model config changed after inference was frozen")
    if run_manifest["inputs"].get("corpus_manifest_sha256") != file_hash(corpus_manifest_path):
        raise ValueError("Inference and scoring corpus versions differ")
    if file_hash(ROOT / "src/evaluation/span_scorer.py") != run_manifest["runtime"]["code_sha256"]["src/evaluation/span_scorer.py"]:
        raise ValueError("Scoring protocol code changed after inference was frozen")
    for name in ("metrics.json", "error_analysis.jsonl", "scoring_manifest.json"):
        if (run_dir / name).exists():
            raise FileExistsError("Refusing to overwrite scoring artifacts")
    golds = read_jsonl(gold_path)
    if len(golds) != corpus_manifest["sample_counts"]["dev"]:
        raise ValueError("Dev gold count differs from manifest")
    for row in golds:
        spans = [CharacterSpan(s["start"], s["end"], s["label"], row["text"][s["start"]:s["end"]], s["system"]) for s in row["spans"]]
        issues = validate_span_integrity(spans, row["text"])
        if issues:
            raise ValueError(f"{row['sample_id']}: invalid gold: {issues}")
    predictions = load_predictions(prediction_path)
    excluded_t1 = set(corpus_manifest.get("evaluation_exclusions", {}).get("t1", []))
    dev_excluded_t1 = sorted(excluded_t1 & {row["sample_id"] for row in golds})
    metrics = compute_exact_span_metrics(predictions, golds, excluded_t1_sample_ids=dev_excluded_t1)
    config = json.loads((run_dir / "model_config.json").read_text(encoding="utf-8"))
    metrics["t1_address_system"]["model_task_status"] = "IMPLEMENTED" if config.get("t1_implemented", True) else "NOT_IMPLEMENTED"
    supported = set(run_manifest["supported_labels"])
    all_gold_spans = sum(len(row["spans"]) for row in golds)
    supported_gold = sum(s["label"] in supported for row in golds for s in row["spans"])
    metrics["supported_label_coverage"] = {"labels": sorted(supported), "gold_spans_in_supported_labels": supported_gold,
        "all_gold_spans": all_gold_spans, "fraction": supported_gold/all_gold_spans if all_gold_spans else None,
        "scoring_policy": "Full T0 metrics retain all 11 labels; unsupported gold spans count as missed"}
    subset_golds = [{**row, "spans": [s for s in row["spans"] if s["label"] in supported]} for row in golds]
    metrics["t0_supported_subset"] = compute_exact_span_metrics(predictions, subset_golds,
        excluded_t1_sample_ids=dev_excluded_t1)["t0_exact_span"]
    by_id = {pred.sample_id: pred for pred in predictions}
    errors = []
    for gold in golds:
        pred = by_id.get(gold["sample_id"], SpanModelOutput(gold["sample_id"], gold["text"], abstain=True, status="missing_prediction"))
        spans = [CharacterSpan(s["start"], s["end"], s["label"], gold["text"][s["start"]:s["end"]], s["system"]) for s in gold["spans"]]
        diag = evaluate_single_sample_spans(pred.spans, spans, gold["text"])
        t1_excluded = gold["sample_id"] in excluded_t1
        t1_error = not t1_excluded and gold.get("address_system") is not None and (pred.abstain or pred.predicted_system != gold["address_system"])
        if diag["fp_count"] or diag["fn_count"] or t1_error or pred.status != "ok":
            errors.append({"sample_id": pred.sample_id, "status": pred.status, "error": pred.error,
                "t0": diag, "gold_t1": gold.get("address_system"), "predicted_t1": pred.predicted_system, "t1_error": t1_error, "t1_excluded_by_adjudication": t1_excluded})
    write_json(run_dir / "metrics.json", metrics)
    write_jsonl(run_dir / "error_analysis.jsonl", errors)
    write_json(run_dir / "scoring_manifest.json", {"metric_version": metrics["metric_version"], "split": "dev",
        "gold_sha256": file_hash(gold_path), "prediction_sha256": file_hash(prediction_path),
        "corpus_manifest_sha256": file_hash(corpus_manifest_path), "scorer_sha256": file_hash(ROOT / "src/evaluation/span_scorer.py"),
        "t1_declared_exception_excluded_ids": dev_excluded_t1,
        "output_sha256": {name: file_hash(run_dir / name) for name in ("metrics.json", "error_analysis.jsonl")}})
    return metrics


def build_adapter(config: dict) -> object:
    validate_config(config)
    resource_manifest(config)
    random.seed(config["seed"])
    factory = config["adapter_factory"]
    if not isinstance(factory, str) or factory.count(":") != 1:
        raise ValueError("adapter_factory must be module:class")
    module_name, class_name = factory.split(":")
    return getattr(importlib.import_module(module_name), class_name)(**config.get("adapter_kwargs", {}))
