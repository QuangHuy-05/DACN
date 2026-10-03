"""Separate text-only inference and frozen scoring for the five-field track."""

from __future__ import annotations

from collections import Counter
import csv
from datetime import datetime, timezone
import inspect
import json
from pathlib import Path
from time import perf_counter

from src.evaluation.dev_runner import ROOT, STATUSES, build_adapter, file_hash, read_jsonl, resource_manifest, runtime_manifest, write_json, write_jsonl
from src.evaluation.schema import STANDARD_FIELDS, SpanModelOutput
from src.evaluation.span_scorer import validate_span_integrity

BENCHMARKS = {
    "01_new": "01_full_address_new_verified.csv",
    "02_noisy": "02_raw_noisy_synthetic_1000.csv",
    "03_old": "03_real_address_old_1500.csv",
    "04_missing": "04_missing_fields_800.csv",
    "06_hybrid": "06_hybrid_addresses_600.csv",
}
HOLD_MANIFEST_HASH = "7e77d73bec74b44044661ae858a7959c6849ee38bfdd14fdfda50794d3bf14e1"
PROJECTION_VERSION = "literal_span_to_five_fields_v1"


def reserved_rows(hold_manifest_path: Path) -> dict[str, set[int]]:
    if file_hash(hold_manifest_path) != HOLD_MANIFEST_HASH:
        raise ValueError("Frozen test identity manifest changed")
    manifest = json.loads(hold_manifest_path.read_text(encoding="utf-8"))
    # This identity-only manifest has no annotation/GT. It is used solely
    # to exclude test rows, and is never supplied to an adapter.
    if manifest["total_samples"] != 100 or len(manifest["samples"]) != 100:
        raise ValueError("Expected 100 frozen test identities")
    excluded = {key: set() for key in BENCHMARKS}
    for sample in manifest["samples"]:
        if set(sample) != {"sample_id", "text_sha256", "source_dataset", "group_id", "stratum", "source_row"}:
            raise ValueError("Test identity manifest must not contain gold labels")
        # Annotation preparation records CSV physical lines: header=1,
        # first record=2. Inference uses zero-based record indices.
        index = int(sample["source_row"]) - 2
        if index < 0:
            raise ValueError("Invalid frozen CSV source line")
        excluded[sample["source_dataset"]].add(index)
    return excluded


def run_fivefield_inference(config: dict, output_dir: Path, hold_manifest_path: Path,
                            benchmark_dir: Path = ROOT / "data/processed/benchmark") -> dict:
    if output_dir.exists():
        raise FileExistsError(output_dir)
    resources = resource_manifest(config)
    excluded = reserved_rows(hold_manifest_path)
    identity = json.loads(hold_manifest_path.read_text(encoding="utf-8"))
    excluded_hashes = {(s["source_dataset"], int(s["source_row"])-2): s["text_sha256"] for s in identity["samples"]}
    adapter = build_adapter(config)
    output_dir.mkdir(parents=True)
    write_json(output_dir / "model_config.json", config)
    datasets, counts, latencies = {}, Counter(), []
    count = 0
    with (output_dir / "predictions.jsonl").open("w", encoding="utf-8") as sink:
        for dataset, filename in BENCHMARKS.items():
            path = benchmark_dir / filename
            digest = file_hash(path)
            kept, total = 0, 0
            with path.open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream)
                if "ChuoiDiaChi" not in (reader.fieldnames or []):
                    raise ValueError(f"Missing inference column: {filename}")
                for index, row in enumerate(reader):
                    total += 1
                    if index in excluded[dataset]:
                        if __import__("hashlib").sha256(row["ChuoiDiaChi"].encode("utf-8")).hexdigest() != excluded_hashes[(dataset,index)]:
                            raise ValueError("Frozen hold source line/text hash mismatch")
                        continue
                    text = row["ChuoiDiaChi"]
                    started = perf_counter()
                    try:
                        output = adapter.parse_spans(text)
                        if not isinstance(output, SpanModelOutput):
                            raise TypeError("Expected SpanModelOutput")
                        issues = validate_span_integrity(output.spans, text)
                        if output.raw_text != text or any(s.text != text[s.start:s.end] for s in output.spans):
                            issues.append("Literal span round-trip failure")
                        if any(s.label not in config["supported_labels"] for s in output.spans):
                            issues.append("Undeclared label")
                        if output.status not in STATUSES:
                            issues.append("Invalid status")
                        if issues:
                            raise ValueError("; ".join(issues))
                        if output.status in {"invalid_output", "runtime_error", "missing_prediction"}:
                            output = SpanModelOutput("", text, abstain=True, status=output.status,
                                raw_output=output.to_dict(), error=output.error)
                        if output.abstain and output.status == "ok":
                            output.status = "abstain"
                    except Exception as exc:
                        output = SpanModelOutput("", text, abstain=True, status="runtime_error", error=f"{type(exc).__name__}: {exc}")
                    output.sample_id = f"D{dataset[:2]}_{index}"
                    output.latency_ms = (perf_counter()-started)*1000
                    record = {**output.to_dict(), "dataset": dataset, "source_row": index,
                              "fields": output.to_standard_5_fields().to_dict()}
                    sink.write(json.dumps(record, ensure_ascii=False, allow_nan=False)+"\n")
                    counts[output.status] += 1
                    latencies.append(output.latency_ms)
                    kept += 1
                    count += 1
            if file_hash(path) != digest:
                raise ValueError("Benchmark changed during inference")
            datasets[dataset] = {"file": filename, "sha256": digest, "source_rows": total,
                                 "evaluated_rows": kept, "excluded_test_rows": sorted(excluded[dataset])}
    latencies.sort()
    manifest = {"run_id": config["run_id"]+"_5field", "model_id": config["model_id"],
        "track": "FIVE_FIELDS_DEVELOPMENT", "mode": "TEXT_ONLY", "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_count": count, "status_counts": dict(counts), "datasets": datasets,
        "test_policy": "100 identity-reserved benchmark rows excluded before inference/scoring; no test annotations read",
        "hold_identity_sha256": file_hash(hold_manifest_path), "projection_version": PROJECTION_VERSION,
        "input_permission": "Adapter.parse_spans(ChuoiDiaChi) only; no oracle mode",
        "resources": resources, "runtime": runtime_manifest(),
        "adapter_sha256": file_hash(Path(inspect.getsourcefile(type(adapter)))),
        "runner_sha256": file_hash(Path(__file__)), "seed": config["seed"],
        "output_sha256": {name: file_hash(output_dir / name) for name in ("predictions.jsonl", "model_config.json")},
        "latency_ms": {"mean": sum(latencies)/len(latencies), "p50": latencies[len(latencies)//2],
                       "p95": latencies[min(len(latencies)-1, int(len(latencies)*0.95))]}}
    write_json(output_dir / "run_manifest.json", manifest)
    return manifest


def score_fivefield_run(run_dir: Path, benchmark_dir: Path = ROOT / "data/processed/benchmark") -> dict:
    # Import the existing strict scorer only at scoring time. Its pandas
    # dependency lives in the main project runtime, not the CRF runtime.
    from src.evaluation.scorer import aggregate_prediction_pairs, compare_fields
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    config = json.loads((run_dir / "model_config.json").read_text(encoding="utf-8"))
    if manifest["track"] != "FIVE_FIELDS_DEVELOPMENT" or manifest["mode"] != "TEXT_ONLY":
        raise ValueError("Unsupported scoring permission")
    for name, digest in manifest["output_sha256"].items():
        if file_hash(run_dir / name) != digest:
            raise ValueError("Frozen prediction/config changed")
    for name in ("metrics.json", "error_analysis.jsonl", "scoring_manifest.json"):
        if (run_dir / name).exists():
            raise FileExistsError("Refusing to overwrite scoring artifacts")
    predictions = read_jsonl(run_dir / "predictions.jsonl")
    by_key = {(r["dataset"], r["source_row"]): r for r in predictions}
    if len(by_key) != len(predictions):
        raise ValueError("Duplicate prediction identities")
    all_pairs, errors, metrics, consumed = [], [], {}, set()
    support = Counter()
    new_count = district_fp = 0
    for dataset, entry in manifest["datasets"].items():
        path = benchmark_dir / entry["file"]
        if file_hash(path) != entry["sha256"]:
            raise ValueError("Benchmark hash changed between inference and scoring")
        pairs, statuses = [], Counter()
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            required = {("GT_"+f if dataset == "02_noisy" else f) for f in STANDARD_FIELDS}
            if not required <= set(reader.fieldnames or []):
                raise ValueError("Missing gold columns")
            for index, row in enumerate(reader):
                if index in entry["excluded_test_rows"]:
                    continue
                key = (dataset, index)
                pred = by_key[key]
                consumed.add(key)
                if pred["raw_text"] != row["ChuoiDiaChi"]:
                    raise ValueError("Prediction text changed")
                gold = {f: row["GT_"+f if dataset == "02_noisy" else f] for f in STANDARD_FIELDS}
                pair = (pred["fields"], gold)
                pairs.append(pair)
                statuses[pred["status"]] += 1
                support.update(f for f, value in gold.items() if value.strip())
                if row.get("HeQuyChieu") == "moi" and not gold["QuanHuyen"].strip():
                    new_count += 1
                    district_fp += bool(pred["fields"]["QuanHuyen"].strip())
                comparisons = compare_fields(*pair)
                if any(value not in {"TP", "TN"} for value in comparisons.values()):
                    errors.append({"sample_id": pred["sample_id"], "dataset": dataset, "text": pred["raw_text"],
                                   "prediction": pred["fields"], "gold": gold, "comparisons": comparisons,
                                   "status": pred["status"], "stratum": row.get("KieuThieu", row.get("KieuLai", row.get("MucDoNhieu")))})
        metrics[dataset] = {**aggregate_prediction_pairs(pairs), "status_counts": dict(statuses), "mode": "TEXT_ONLY"}
        all_pairs.extend(pairs)
    if consumed != set(by_key):
        raise ValueError("Extra prediction outside the allowed benchmark rows")
    result = {"track": "FIVE_FIELDS_DEVELOPMENT", "protocol_version": "2.0", "mode": "TEXT_ONLY",
              "projection": "Original span literals joined by comma for repeated fields; no canonical repair or field imputation",
              "datasets": metrics, "overall": aggregate_prediction_pairs(all_pairs),
              "supported_labels": config["supported_labels"], "gold_field_support": dict(support),
              "supported_field_coverage": sum(v for k,v in support.items() if k in config["supported_labels"])/sum(support.values()),
              "quan_huyen_diagnostic": {"gold_new_without_district": new_count, "false_positive_samples": district_fp,
                                         "rate": district_fp/new_count if new_count else None},
              "interpretation": "Existing benchmark development comparison, not final T0 test performance; all 100 hold rows excluded"}
    write_json(run_dir / "metrics.json", result)
    write_jsonl(run_dir / "error_analysis.jsonl", errors)
    write_json(run_dir / "scoring_manifest.json", {"run_manifest_sha256": file_hash(run_dir / "run_manifest.json"),
        "prediction_sha256": file_hash(run_dir / "predictions.jsonl"),
        "scorer_sha256": file_hash(ROOT / "src/evaluation/scorer.py"),
        "benchmark_runner_sha256": file_hash(Path(__file__)),
        "output_sha256": {name: file_hash(run_dir/name) for name in ("metrics.json", "error_analysis.jsonl")}})
    return result
