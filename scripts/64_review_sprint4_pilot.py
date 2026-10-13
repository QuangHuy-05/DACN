"""Review a pilot timing log and optional exports; produce interim JSON/CSV only."""
import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
from math import isfinite
import json

from src.data.sprint4_pilot import file_hash, write_new_json
from src.data.sprint4_pilot_review import (REPEAT_FIELDS, TIMING_FIELDS, annotation_summary, read_csv,
                                         read_package, repeat_summary, timing_summary, workload_projection)

ROOT = Path(__file__).resolve().parents[1]


def review(package, output, timing_path=None, export_path=None, repeat_path=None, annotation_days=6, adjudication_minutes=0):
    if output.exists() or not output.resolve().is_relative_to((ROOT / "data/interim/annotation/sprint04").resolve()):
        raise ValueError("OUTPUT_EXISTS_OR_OUTSIDE_S4_INTERIM")
    if type(annotation_days) is not int or annotation_days <= 0 or not isfinite(adjudication_minutes) or adjudication_minutes < 0:
        raise ValueError("INVALID_PLANNING_INPUT")
    manifest, queue = read_package(package)
    sample_ids = set(queue)
    timing_path = timing_path or package / "timing_log.csv"
    timing = timing_summary(read_csv(timing_path, TIMING_FIELDS), sample_ids)
    annotation = annotation_summary(json.loads(export_path.read_text(encoding="utf-8-sig")), queue) if export_path else {
        "status": "NOT_PROVIDED", "structurally_valid_annotations": 0, "gold_release": "NOT_APPROVED"}
    repeated = repeat_summary(read_csv(repeat_path, set(REPEAT_FIELDS)), sample_ids) if repeat_path else {
        "status": "NOT_PROVIDED", "timing_eligible_samples": 0, "agreement_metrics": "NOT_MEASURED"}
    forecasts = None
    if timing["complete_timing_required_for_projection"]:
        forecasts = [workload_projection(timing["minutes_per_usable_sample_including_reject_cost"],
                                        daily, annotation_days, adjudication_minutes) for daily in (60, 90)]
    inputs = {"pilot_manifest": file_hash(package / "manifest.json"), "timing_csv": file_hash(timing_path)}
    if export_path:
        inputs["annotation_export"] = file_hash(export_path)
    if repeat_path:
        inputs["repeat_csv"] = file_hash(repeat_path)
    report = {"version": "s4-pilot-review-v1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "status": "REVIEW_ONLY_NOT_CORPUS_APPROVAL", "input_sha256": inputs,
              "candidate_samples": len(queue), "source_ready_samples_in_bound_package": manifest["annotation_ready_samples"],
              "timing": timing, "annotation": annotation, "repeat": repeated, "workload_estimates": forecasts,
              "sample_target_committed": None, "source_rights_approved_by_this_tool": False,
              "training_allowed_by_this_tool": False, "gold_samples_released": 0,
              "planning_assumptions": {"daily_minutes_user_confirmed": [60, 90], "active_annotation_days_assumed": annotation_days,
                                       "adjudication_minutes_assumed": adjudication_minutes,
                                       "calendar_washout_feasibility_verified": False},
              "limitations": ["timing_and_blinding_are_user_recorded", "structural_QA_does_not_verify_label_semantics",
                              "workload_does_not_establish_source_inventory_or_group_split_feasibility",
                              "no_agreement_metrics_without_two_round_annotation_exports"]}
    output.mkdir(parents=True)
    write_new_json(output / "pilot_review.json", report)
    with (output / "repeat_timing_template.csv").open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=REPEAT_FIELDS)
        writer.writeheader()
        writer.writerows({"sample_id": sample_id} for sample_id in sorted(sample_ids))
    write_new_json(output / "manifest.json", {"version": "s4-pilot-review-output-v1", "input_sha256": inputs,
                   "output_sha256": {path.name: file_hash(path) for path in output.iterdir() if path.is_file()},
                   "code_sha256": {name: file_hash(ROOT / name) for name in (
                       "src/data/sprint4_pilot_review.py", "scripts/64_review_sprint4_pilot.py",
                       "scripts/17_convert_span_annotation_batch.py", "src/data/sprint4_pilot.py")}})
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timing", type=Path)
    parser.add_argument("--annotation-export", type=Path)
    parser.add_argument("--repeat-log", type=Path)
    parser.add_argument("--annotation-days", type=int, default=6)
    parser.add_argument("--adjudication-minutes", type=float, default=0)
    args = parser.parse_args()
    report = review(args.package, args.output, args.timing, args.annotation_export, args.repeat_log,
                    args.annotation_days, args.adjudication_minutes)
    print(json.dumps({key: report[key] for key in ("status", "candidate_samples", "source_ready_samples_in_bound_package",
                     "workload_estimates", "sample_target_committed", "gold_samples_released")}, ensure_ascii=False, indent=2))
