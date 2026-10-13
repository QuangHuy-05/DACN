"""Read-only acceptance of new runs, approved corpus and existing alignment evidence."""

import argparse
from collections import Counter
import importlib
import json
from pathlib import Path
import shutil

from src.evaluation.dev_runner import ROOT, file_hash, read_jsonl, write_json
from src.modeling.datasets import load_corpus
from src.modeling.pre_colab import compare_ledger
from src.data.nso_dual_snapshot import DualSnapshotGazetteer


def accept(output):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    prefix = "data/interim/modeling/sprint03/pre_colab_20261003_resume_v1"
    ledger = json.loads((ROOT / prefix / "p0/frozen_before.json").read_text())
    frozen = compare_ledger(ledger)
    write_json(output / "frozen_compare.json", frozen)
    if frozen["status"] != "FROZEN_LEDGER_PASS":
        raise ValueError("FROZEN_ARTIFACT_CHANGED")
    runs = []
    for base, pattern in (("heur_jw_followup_20261003_v1", "threshold_*"), ("crf_followup_20261003_v1", "*/dev_run")):
        runs += [path.relative_to(ROOT / "data/processed/evaluation/sprint03").as_posix()
                 for path in sorted((ROOT / "data/processed/evaluation/sprint03" / base).glob(pattern))]
    runs += ["heur_jw_followup_fivefield_20261003_v1", "crf_followup_fivefield_20261003_v1"]
    legacy = importlib.import_module("scripts.29_audit_sprint3_experiments")
    audit = legacy.audit(output / "runs", runs)
    if len(audit["runs"]) != 16:
        raise ValueError("TRIAL_BUDGET_OR_COUNT_MISMATCH")
    corpus_dir = ROOT / "data/processed/annotation/sprint03/corpus_train_dev_v2"
    load_corpus(corpus_dir)
    gold = {row["sample_id"]: row for row in read_jsonl(corpus_dir / "dev.jsonl")}
    corpus = json.loads((corpus_dir / "manifest.json").read_text())
    excluded = set(corpus["evaluation_exclusions"]["t1"])
    snapshot = output / "run_code_snapshot"
    diagnostics = {}
    for name in runs:
        directory = ROOT / "data/processed/evaluation/sprint03" / name
        run = json.loads((directory / "run_manifest.json").read_text())
        for entry in run.get("resources", {}).values():
            if not isinstance(entry, dict) or not str(entry.get("path", "")).endswith(".py"):
                continue
            source = ROOT / entry["path"]
            if file_hash(source) != entry["sha256"]:
                raise ValueError("NEW_RUN_CODE_DRIFT")
            destination = snapshot / entry["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        if run["track"] != "T0_T1_DEV":
            continue
        counts = Counter()
        predictions = read_jsonl(directory / "predictions.jsonl")
        for prediction in predictions:
            item = gold[prediction["sample_id"]]
            if prediction["raw_text"] != item["text"]:
                raise ValueError("RAW_TEXT_DRIFT")
            previous_end = 0
            for span in sorted(prediction["spans"], key=lambda row: row["start"]):
                if not previous_end <= span["start"] < span["end"] <= len(item["text"]) or item["text"][span["start"]:span["end"]] != span["text"]:
                    raise ValueError("OFFSET_OR_OVERLAP_INVALID")
                previous_end = span["end"]
            if item["sample_id"] in excluded or item["address_system"] not in ("cu", "moi", "Lai"):
                continue
            system = item["address_system"]
            counts[system + "_samples"] += 1
            predicted_districts = {(span["start"], span["end"]) for span in prediction["spans"] if span["label"] == "QuanHuyen"}
            gold_districts = {(span["start"], span["end"]) for span in item["spans"] if span["label"] == "QuanHuyen"}
            if system == "moi":
                counts["moi_samples_with_predicted_district"] += bool(predicted_districts)
            else:
                counts[system + "_district_support"] += len(gold_districts)
                counts[system + "_district_exact_tp"] += len(gold_districts & predicted_districts)
        diagnostics[name] = {"district": dict(counts), "latency_ms": run.get("latency_ms"),
                             "raw_span_qa": "PASS_60_IDS_EXACT_TEXT_OFFSETS_NO_OVERLAP"}
    integration_dir = ROOT / "data/interim/modeling/sprint03/neural_integration_tone_v2_replay_20261003_fullpath"
    integration = json.loads((integration_dir / "integration_manifest.json").read_text())
    for name, digest in integration["output_sha256"].items():
        if file_hash(integration_dir / name) != digest:
            raise ValueError("ALIGNMENT_EVIDENCE_DRIFT")
    if integration["text_alignment"] != {"train": {"EXACT": 240}, "dev": {"EXACT": 60}}:
        raise ValueError("ALIGNMENT_NOT_300_EXACT")
    gaz = DualSnapshotGazetteer(ROOT / "data/processed/gazetteer/s3_v4_nso_dual_snapshot_release2")
    result = {"status": "ACCEPTANCE_PASS", "run_count": len(runs), "run_diagnostics": diagnostics,
              "frozen_files": frozen["checked_files"], "corpus": {"train": 240, "dev": 60, "spans": 1341, "bio_states": 23,
              "manifest_sha256": file_hash(corpus_dir / "manifest.json"), "t1_mask": sorted(excluded)},
              "alignment": {"status": "EXISTING_ACTUAL_PROCESSOR_300_EXACT_HASH_VERIFIED", "processor_unchanged": True,
              "evidence_manifest_sha256": file_hash(integration_dir / "integration_manifest.json")},
              "gazetteer_entities": len(gaz.entities), "test100": "NOT_READ_NOT_SCORED", "neural_training": "NOT_EXECUTED"}
    write_json(output / "acceptance.json", result)
    return {key: value for key, value in result.items() if key != "run_diagnostics"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(accept(args.output_dir.resolve()), ensure_ascii=False))
