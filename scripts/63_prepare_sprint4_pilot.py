"""Package an immutable Sprint 4 source-review pilot, not a released corpus."""
import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
import json
import random

from src.data.sprint4_pilot import (connected_groups, duplicate_pairs, file_hash, frozen_integrity,
                                  manual_tasks, previous_texts, resolved_overlap_samples,
                                  validate_candidate, write_new_json)

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = "data/interim/annotation/sprint04/protocol_v1/baseline_snapshot.json"


def prepare(config_path, output):
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    samples, sources = config["samples"], config["sources"]
    if len({row["sample_id"] for row in samples}) != len(samples):
        raise ValueError("DUPLICATE_SAMPLE_ID")
    if output.resolve().exists() or not output.resolve().is_relative_to((ROOT / "data/interim/annotation/sprint04").resolve()):
        raise ValueError("OUTPUT_EXISTS_OR_OUTSIDE_S4_INTERIM")
    before = frozen_integrity(ROOT, SNAPSHOT)
    if before["status"] != "PASS":
        raise ValueError("FROZEN_BASELINE_MISMATCH: " + json.dumps(before))
    for row in samples:
        validate_candidate(ROOT, row, sources)
    previous = previous_texts(ROOT, "data/processed/annotation/sprint03/corpus_v1_release2")
    findings = duplicate_pairs(samples, previous)
    groups = connected_groups(samples)
    external_hits = {row["sample_id"] for row in findings if row["other_split"] != "pilot_review"}
    decisions = config.get("overlap_decisions", [])
    external_hits.difference_update(resolved_overlap_samples(findings, decisions))
    cross_group = [row for row in findings if row["other_split"] == "pilot_review"
                   and groups[row["sample_id"]] != groups[row["other_id"]]]
    # Near duplicates across components block annotation until a documented decision.
    external_hits.update(row["sample_id"] for row in cross_group)
    external_hits.update(row["other_id"] for row in cross_group)
    for row in samples:
        row["component_group"] = groups[row["sample_id"]]
        row["reserved_role"] = "DEVELOPMENT_ONLY_PILOT_NOT_HOLDOUT"
        row["overlap_review"] = "REVIEW_REQUIRED" if row["sample_id"] in external_hits else "PASS"
    random.Random(config["seed"]).shuffle(samples)
    tasks = manual_tasks(samples, sources)
    output.mkdir(parents=True)
    write_new_json(output / "source_review_queue.json", samples)
    write_new_json(output / "annotation_import.json", tasks)
    write_new_json(output / "source_use_assessment.json", sources)
    write_new_json(output / "operational_inputs.json", config["operational_inputs"])
    write_new_json(output / "overlap_decisions.json", decisions)
    write_new_json(output / "duplicate_audit.json", {"previous_samples": len(previous), "threshold": 0.85,
                   "method": "NFKD_CASEFOLD_DIACRITICS_PUNCTUATION_WHITESPACE_SEQUENCE_MATCHER",
                   "findings": findings, "cross_component_findings": cross_group,
                   "external_hits_require_review": sorted(external_hits), "gold_read_for_development": False})
    with (output / "timing_log.csv").open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("sample_id", "source_review_seconds", "annotation_started_at",
               "annotation_finished_at", "annotation_seconds", "review_seconds", "valid_sample", "difficulty_note"))
        writer.writeheader()
        writer.writerows({"sample_id": row["sample_id"]} for row in samples)
    with (output / "source_review.csv").open("x", encoding="utf-8-sig", newline="") as stream:
        fields = ("sample_id", "text", "source_key", "source_url", "source_page", "site_group", "component_group",
                  "extraction_method", "source_text_review", "overlap_review", "annotation_clearance")
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in samples:
            writer.writerow({**{key: row[key] for key in fields if key in row},
                             "source_url": sources[row["source_key"]]["source_url"],
                             "source_page": row["locator"].get("page", ""),
                             "annotation_clearance": sources[row["source_key"]]["annotation_clearance"]})
    xml = (ROOT / "configs/label_studio_span11.xml").read_text(encoding="utf-8-sig").replace("Sprint 3 -", "Sprint 4 -")
    (output / "label_config.xml").write_text(xml, encoding="utf-8")
    after = frozen_integrity(ROOT, SNAPSHOT)
    write_new_json(output / "frozen_integrity.json", {"before": before, "after": after})
    files = {path.name: file_hash(path) for path in output.iterdir() if path.is_file()}
    manifest = {"version": config["version"], "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "status": "SOURCE_REVIEW_PREPARED_ANNOTATION_GATES_PENDING", "seed": config["seed"],
                "input_sha256": file_hash(config_path), "candidate_samples": len(samples),
                "annotation_ready_samples": len(tasks), "site_groups": len({row["site_group"] for row in samples}),
                "document_groups": len({row["document_group"] for row in samples}),
                "connected_components": len(set(groups.values())), "holdout_eligible_samples_in_this_package": 0,
                "holdout_status": "HOLDOUT_NOT_COMMITTED", "gold_samples": 0,
                "annotation_mode": "HUMAN_MANUAL_NO_PREDICTIONS", "human_pilot_execution": "NOT_EXECUTED",
                "intra_annotator_execution": "NOT_EXECUTED", "inter_annotator_agreement": "NOT_MEASURED",
                "cloud_upload": "NOT_EXECUTED_CLEARANCE_PENDING", "training": "NOT_EXECUTED",
                "candidate_feature_gaps": ["HuongDi", "MocDinhVi", "GhiChu", "T1_Lai"],
                "candidate_features_are_gold_support": False, "output_sha256": files,
                "frozen_baseline_status": after["status"]}
    write_new_json(output / "manifest.json", manifest)
    if after["status"] != "PASS":
        raise ValueError("FROZEN_BASELINE_CHANGED_DURING_PREPARATION")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.config, args.output), ensure_ascii=False, indent=2))
