"""Finite T1 confidence sweep on frozen dev outputs and eligible gold only."""

from collections import Counter
import json
from pathlib import Path

from src.evaluation.dev_runner import file_hash, read_jsonl, write_json
from src.evaluation.schema import ADDRESS_SYSTEMS
from src.modeling.datasets import load_corpus
from src.modeling.labels import t1_target
from src.modeling.structural_decoder import structure_decision, RULE_VERSION

CONFIDENCE_GRID = [(threshold, margin) for threshold in (0.7, 0.8, 0.9) for margin in (0.1, 0.2)]


def confidence_sweep(predictions: list[dict], golds: list[dict], corpus_manifest: dict) -> dict:
    by_id = {row["sample_id"]: row for row in predictions}
    if len(by_id) != len(predictions) or set(by_id) != {row["sample_id"] for row in golds}:
        raise ValueError("CALIBRATION_REQUIRES_ALL_DEV_IDS")
    eligible = [row for row in golds if t1_target(row, corpus_manifest)[1]]
    if not eligible:
        raise ValueError("NO_ELIGIBLE_T1_DEV_GOLD")
    support = Counter(row["address_system"] for row in eligible)
    results = []
    for threshold, margin in CONFIDENCE_GRID:
        tp, fp, fn = Counter(), Counter(), Counter()
        accepted = correct = 0
        for gold in eligible:
            prediction = by_id[gold["sample_id"]]
            posterior = prediction.get("trace", {}).get("structure", {})
            posterior = posterior.get("posterior") if isinstance(posterior, dict) else None
            system = "khong_ro"
            if posterior and prediction.get("status") == "ok" and not prediction.get("abstain"):
                system = structure_decision([posterior[label] for label in ADDRESS_SYSTEMS], threshold, margin)["predicted_system"]
            actual = gold["address_system"]
            if system in ADDRESS_SYSTEMS:
                accepted += 1
            if system == actual:
                tp[actual] += 1
                correct += 1
            else:
                fn[actual] += 1
                if system in ADDRESS_SYSTEMS:
                    fp[system] += 1
        macro = sum(2*tp[label]/(2*tp[label]+fp[label]+fn[label]) if 2*tp[label]+fp[label]+fn[label] else 0 for label in support) / len(support)
        results.append({"threshold": threshold, "margin": margin, "eligible": len(eligible), "accepted": accepted,
            "correct": correct, "macro_f1_gold_supported": macro, "accuracy_all_eligible": correct/len(eligible),
            "coverage": accepted/len(eligible), "accuracy_when_accepted": correct/accepted if accepted else None})
    best = max(results, key=lambda row: (row["macro_f1_gold_supported"], row["accuracy_all_eligible"], row["coverage"], row["threshold"], row["margin"]))
    return {"grid": results, "selected": best, "eligible_gold_support": dict(support),
            "selection": "T1 macro gold-supported F1, accuracy, coverage, higher threshold, higher margin",
            "excluded_ids": sorted(row["sample_id"] for row in golds if not t1_target(row, corpus_manifest)[1])}


def calibrate_frozen_dev(run_dir: Path, corpus_dir: Path, output_dir: Path) -> dict:
    if output_dir.exists():
        raise FileExistsError(output_dir)
    manifest, splits = load_corpus(corpus_dir)
    run = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    prediction_path = run_dir / "predictions.jsonl"
    if run.get("split") != "dev" or not run["model_id"].startswith("PROPOSED"):
        raise ValueError("T1_CALIBRATION_ONLY_PROPOSED_DEV")
    if file_hash(prediction_path) != run["output_sha256"]["predictions.jsonl"] or file_hash(run_dir / "model_config.json") != run["output_sha256"]["model_config.json"]:
        raise ValueError("FROZEN_CALIBRATION_INPUT_TAMPERED")
    if run["inputs"]["corpus_manifest_sha256"] != file_hash(corpus_dir / "manifest.json"):
        raise ValueError("CALIBRATION_CORPUS_VERSION_MISMATCH")
    result = confidence_sweep(read_jsonl(prediction_path), splits["dev"], manifest)
    output_dir.mkdir(parents=True)
    selected = result["selected"]
    policy = {"version": RULE_VERSION, "threshold": selected["threshold"], "margin": selected["margin"],
              "checkpoint_sha256": run["resources"]["checkpoint"]["sha256"],
              "corpus_manifest_sha256": file_hash(corpus_dir / "manifest.json"),
              "prediction_sha256": file_hash(prediction_path), "source_run": run["run_id"], "selection_split": "dev",
              "calibration_code_sha256": file_hash(Path(__file__)), "t1_eligible": selected["eligible"],
              "excluded_t1_ids": manifest["evaluation_exclusions"]["t1"]}
    write_json(output_dir / "confidence_sweep.json", result)
    write_json(output_dir / "decoder_policy.json", policy)
    write_json(output_dir / "calibration_manifest.json", {"purpose": "dev_T1_calibration", "test100": "NOT_READ_NOT_USED",
        "outputs": {name: file_hash(output_dir / name) for name in ("decoder_policy.json", "confidence_sweep.json")}})
    return policy


def load_decoder_policy(path: Path, checkpoint: Path, config: dict) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    manifest = json.loads(path.with_name("calibration_manifest.json").read_text(encoding="utf-8"))
    if file_hash(path) != manifest["outputs"]["decoder_policy.json"]:
        raise ValueError("CALIBRATION_POLICY_TAMPERED")
    if value["checkpoint_sha256"] != file_hash(checkpoint) or value["corpus_manifest_sha256"] != config["corpus_manifest_sha256"] or value["selection_split"] != "dev":
        raise ValueError("CALIBRATION_CHECKPOINT_OR_DATA_MISMATCH")
    if (value["threshold"], value["margin"]) not in CONFIDENCE_GRID:
        raise ValueError("CALIBRATION_OUTSIDE_LOCKED_GRID")
    return {"version": RULE_VERSION, "threshold": value["threshold"], "margin": value["margin"],
            "enabled": config["model_id"] == "PROPOSED-DYN"}
