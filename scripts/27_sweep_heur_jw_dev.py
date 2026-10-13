"""Tune only HEUR-JW thresholds on frozen dev; save every frozen run."""

import argparse
import csv
import json
from pathlib import Path

from src.evaluation.adapters.heur_jw_adapter import HeuristicJaroWinklerAdapter
from src.evaluation.dev_runner import ROOT, file_hash, load_dev_input, read_jsonl, run_dev_inference, score_dev_predictions, write_json
from src.evaluation.experiment_config import heur_config


def sweep(corpus_dir: Path, output_dir: Path, experiment_id: str, seed: int = 42, gazetteer_dir=None, rule_version="v3") -> dict:
    if output_dir.exists():
        raise FileExistsError(output_dir)
    manifest_path = corpus_dir / "manifest.json"
    samples = load_dev_input(corpus_dir / "dev_input.jsonl", manifest_path)
    output_dir.mkdir(parents=True)
    results = []
    for threshold in (0.82, 0.86, 0.90, 0.94, 0.98, 1.0):
        config = heur_config(experiment_id+f"_dev_t{threshold:.2f}", threshold, seed, gazetteer_dir, rule_version)
        run_dir = output_dir / f"threshold_{threshold:.2f}"
        from src.evaluation.dev_runner import build_adapter
        adapter = build_adapter(config)
        run_dev_inference(adapter, samples, config, run_dir,
            {"dev_input_sha256": file_hash(corpus_dir / "dev_input.jsonl"), "corpus_manifest_sha256": file_hash(manifest_path)})
        metrics = score_dev_predictions(run_dir/"predictions.jsonl", corpus_dir/"dev.jsonl", run_dir, manifest_path)
        predictions = read_jsonl(run_dir / "predictions.jsonl")
        admin = [x for row in predictions for x in row["trace"]["admin_matches"]]
        micro = metrics["t0_exact_span"]["micro"]
        result = {"threshold": threshold, "precision": micro["precision"], "recall": micro["recall"], "f1": micro["f1"],
            "sample_span_coverage": sum(bool(row["spans"]) for row in predictions)/len(predictions),
            "gold_span_recall": micro["recall"],
            "admin_accepted_fraction": sum(x["decision"].startswith("ACCEPT") for x in admin)/len(admin) if admin else 0,
            "admin_identity_resolved_fraction": sum(x.get("entity_id") is not None for x in admin)/len(admin) if admin else 0,
            "admin_rejects": sum(x["decision"].startswith("REJECT") for x in admin),
            "config_path": (run_dir/"model_config.json").resolve().relative_to(ROOT).as_posix(),
            "run_dir": run_dir.resolve().relative_to(ROOT).as_posix()}
        results.append(result)
        print(json.dumps(result), flush=True)
    chosen = sorted(results, key=lambda row: (-row["f1"], -row["threshold"]))[0]
    write_json(output_dir / "chosen_model_config.json", json.loads((ROOT/chosen["config_path"]).read_text(encoding="utf-8")))
    with (output_dir / "precision_coverage.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    report = {"experiment_id": experiment_id, "model_id": "HEUR-JW", "status": "DEV_THRESHOLD_SELECTED_TEST_PENDING",
        "selection_rule": "highest all-schema exact-span dev F1; ties prefer higher threshold",
        "coverage_definition": "sample_span_coverage counts a sample with >=1 returned literal span; gold_span_recall is TP/all gold spans",
        "identity_definition": "Resolved internal entity ID; ambiguous same-level candidates can support T0 while identity/system abstains",
        "results": results, "chosen": chosen, "corpus_manifest_sha256": file_hash(manifest_path),
        "test": "NOT_READ_NOT_USED", "interpretation": "Dev threshold selection, not final test performance"}
    write_json(output_dir / "sweep_manifest.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", type=Path, default=Path("data/processed/annotation/sprint03/corpus_train_dev_v2"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--gazetteer-dir", type=Path)
    parser.add_argument("--rule-version", choices=("v3", "v4"), default="v3")
    args = parser.parse_args()
    report = sweep(args.corpus_dir, args.output_dir, args.experiment_id, args.seed, args.gazetteer_dir, args.rule_version)
    print(json.dumps({"status": report["status"], "chosen": report["chosen"]}))


if __name__ == "__main__":
    main()
