"""Read-only audit of final development runs and protected frozen artifacts."""

import argparse
from collections import Counter
import json
from pathlib import Path

from src.evaluation.benchmark_runner import BENCHMARKS, reserved_rows
from src.evaluation.dev_runner import ROOT, file_hash, load_predictions, read_jsonl, resource_manifest, write_json


def audit(output_dir: Path, run_names: list[str] | None = None) -> dict:
    if output_dir.exists():
        raise FileExistsError(output_dir)
    corpus_dir = ROOT / "data/processed/annotation/sprint03/corpus_train_dev_v2"
    corpus = json.loads((corpus_dir/"manifest.json").read_text(encoding="utf-8"))
    protected = {}
    for name, digest in corpus["output_sha256"].items():
        if file_hash(corpus_dir/name) != digest:
            raise ValueError(f"Approved corpus changed: {name}")
        protected[str((corpus_dir/name).relative_to(ROOT))] = digest
    prior = json.loads((ROOT/"docs/sprints/sprint_03/baseline_run_audit.json").read_text(encoding="utf-8"))
    for name, digest in prior["frozen_hashes_before"].items():
        if file_hash(ROOT/name) != digest:
            raise ValueError(f"Frozen baseline changed: {name}")
        protected[name] = digest
    prior_manifest = json.loads((ROOT/"data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json").read_text(encoding="utf-8"))
    for name, info in prior_manifest["datasets"].items():
        path = ROOT/"data/processed/benchmark"/name
        if file_hash(path) != info["sha256"]:
            raise ValueError(f"Frozen benchmark changed: {name}")
        protected[str(path.relative_to(ROOT))] = info["sha256"]
    hold_path = ROOT/"data/interim/annotation/sprint03/test_hold_manifest_v1.json"
    excluded = reserved_rows(hold_path)
    dev_ids = {r["sample_id"] for r in read_jsonl(corpus_dir/"dev_input.jsonl")}
    run_names = run_names or ["heur_jw_dev_20261002_v2/threshold_0.86", "crf_indep_dev_20261002_v1/ctx2_c10.05_c20.1/dev_run",
                 "heur_jw_5field_20261002_v1", "crf_indep_5field_20261002_v1"]
    reports = []
    for name in run_names:
        run_dir = ROOT/"data/processed/evaluation/sprint03"/name
        run = json.loads((run_dir/"run_manifest.json").read_text(encoding="utf-8"))
        score = json.loads((run_dir/"scoring_manifest.json").read_text(encoding="utf-8"))
        config = json.loads((run_dir/"model_config.json").read_text(encoding="utf-8"))
        resource_manifest(config)
        for manifest in (run, score):
            for filename, digest in manifest.get("output_sha256", {}).items():
                if file_hash(run_dir/filename) != digest:
                    raise ValueError(f"Run output drift: {name}/{filename}")
        if score.get("run_manifest_sha256") and file_hash(run_dir/"run_manifest.json") != score["run_manifest_sha256"]:
            raise ValueError("Scoring manifest no longer matches inference")
        records = read_jsonl(run_dir/"predictions.jsonl")
        if run["track"] == "T0_T1_DEV":
            predictions = load_predictions(run_dir/"predictions.jsonl")
            if {r.sample_id for r in predictions} != dev_ids or len(predictions) != 60:
                raise ValueError("Dev identity/count mismatch")
            metrics = json.loads((run_dir/"metrics.json").read_text())
            if metrics["t1_address_system"]["declared_exception_excluded_ids"] != corpus["evaluation_exclusions"]["t1"]:
                raise ValueError("Declared T1 exception was not masked")
        else:
            for record in records:
                if record["source_row"] in excluded[record["dataset"]]:
                    raise ValueError("Test hold row reached inference")
            for key in BENCHMARKS:
                if set(run["datasets"][key]["excluded_test_rows"]) != excluded[key]:
                    raise ValueError("Test row exclusion mismatch")
            if len(records) != 4800:
                raise ValueError("Expected 4,800 permitted benchmark rows")
        reports.append({"run_dir": str(run_dir.relative_to(ROOT)), "model_id": config["model_id"],
            "count": len(records), "status_counts": dict(Counter(r["status"] for r in records)),
            "run_manifest_sha256": file_hash(run_dir/"run_manifest.json"), "predictions_sha256": file_hash(run_dir/"predictions.jsonl"),
            "metrics_sha256": file_hash(run_dir/"metrics.json"), "scoring_manifest_sha256": file_hash(run_dir/"scoring_manifest.json"),
            "model_config_sha256": file_hash(run_dir/"model_config.json")})
    report = {"status": "AUDIT_PASS_DP_ENVIRONMENT_BLOCKED", "tasks": {
        "1_environment": "COMPLETE", "2_heur_jw": "IMPLEMENTED_AND_RUN", "3_dp_zs_ft": "ADAPTER_IMPLEMENTED_REAL_RUN_BLOCKED",
        "4_crf_indep": "TRAINED_AND_RUN"}, "runs": reports, "protected_sha256": protected,
        "corpus_manifest_sha256": file_hash(corpus_dir/"manifest.json"), "hold_identity_sha256": file_hash(hold_path),
        "test_gold": "NOT_READ_NOT_USED", "test_hold_rows_excluded": sum(len(v) for v in excluded.values()),
        "dp_blockers": ["WSL RAM 3.64 GiB + 1 GiB swap below full FastText 8-10 GB", "Pretrained card does not declare resource license"],
        "historical_runs": {"heur_jw_dev_20261002_v1": "Superseded by v2 after fixing explicit unit-type filtering; retained unchanged"},
        "code_sha256": {str(path.relative_to(ROOT)): file_hash(path) for path in (
            ROOT/"src/evaluation/benchmark_runner.py", ROOT/"src/evaluation/experiment_config.py",
            ROOT/"src/evaluation/span_features.py", ROOT/"src/evaluation/adapters/heur_jw_adapter.py",
            ROOT/"src/evaluation/adapters/crf_adapter.py", ROOT/"src/evaluation/adapters/deepparse_adapter.py",
            ROOT/"scripts/26_train_independent_crf.py", ROOT/"scripts/27_sweep_heur_jw_dev.py",
            ROOT/"scripts/28_run_fivefield_experiment.py", Path(__file__).resolve())}}
    output_dir.mkdir(parents=True)
    write_json(output_dir/"completion_audit.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--runs", nargs="+", help="Run directories relative to data/processed/evaluation/sprint03")
    args = parser.parse_args()
    report = audit(args.output_dir, args.runs)
    print(json.dumps({"status": report["status"], "tasks": report["tasks"], "runs": len(report["runs"])}))


if __name__ == "__main__":
    main()
