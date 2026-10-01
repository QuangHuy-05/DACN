"""Standalone source-trace QA, runnable without optional OSM adapter packages."""

import importlib
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class SourceReannotationStandaloneTests(unittest.TestCase):
    def test_frozen_packages_and_span_trace(self):
        generator = importlib.import_module("scripts.21_prepare_source_reannotation")
        importer = importlib.import_module("scripts.15_import_pilot_predictions")
        converter = importlib.import_module("scripts.11_convert_label_studio_pilot")
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "v2"
            with patch.object(sys, "argv", ["prepare", "--output-dir", str(output)]):
                generator.main()
            records = []
            for package, expected in (("pilot68", 68), ("batch232", 232)):
                path = output / f"{package}_candidates.json"
                importer.validate_candidates(path, expected)
                candidates = json.loads(path.read_text(encoding="utf-8"))
                tasks = json.loads((output / f"{package}_import.json").read_text(encoding="utf-8"))
                self.assertEqual(len(candidates), expected)
                self.assertEqual([task["data"] for task in tasks], [
                    {"sample_id": row["sample_id"], "text": row["text"]} for row in candidates])
                self.assertTrue(all(set(task) == {"data"} and set(task["data"]) == {"sample_id", "text"}
                                    for task in tasks))
                records.extend(candidates)
            hold = {row["sample_id"] for row in json.loads(
                (generator.BASE / "test_hold_manifest_v1.json").read_text(encoding="utf-8"))["samples"]}
            self.assertEqual(len({row["sample_id"] for row in records}), 300)
            self.assertFalse({row["sample_id"] for row in records} & hold)
            vqa_hold = {row["sample_id"] for row in generator.read_csv(
                generator.BASE / "annotation_queue_batch01.csv", {"sample_id", "planned_role"})
                if row["planned_role"] == "external_test_hold"}
            self.assertFalse({row["sample_id"] for row in records} & vqa_hold)
            traces = {row["sample_id"]: row for row in map(
                json.loads, (output / "trace.jsonl").read_text(encoding="utf-8").splitlines())}
            self.assertEqual(len(traces), 300)
            for record in records:
                # Check the actual export consumer, including its boundary rules,
                # rather than only the looser API import validation.
                converted = converter.convert_annotation(
                    {"result": importer.prediction_results(record)}, record["text"], record["sample_id"])
                self.assertEqual(converted["spans"], record["spans"])
                trace = traces[record["sample_id"]]
                lookup = {(part["start"], part["end"], part["field"]): part
                          for part in trace["components"] if part["match_status"] == "exact"}
                for span in record["spans"]:
                    self.assertEqual(record["text"][span["start"]:span["end"]], span["text"])
                    part = lookup[(span["start"], span["end"], span["label"])]
                    self.assertEqual(part["span_system_candidate"], span["system"])
                    self.assertIn("offset_method", part)
                    self.assertIn("evidence", part)
                    if span["label"] in {"SoNha", "TenDuong"}:
                        self.assertEqual(span["system"], "khong_xac_dinh")
                    if span["label"] == "QuanHuyen":
                        self.assertEqual(span["system"], "cu")
                if trace["stratum"] == "osm_new_2tier":
                    self.assertNotIn("QuanHuyen", [span["label"] for span in record["spans"]])
                if trace["stratum"] == "synthetic_missing":
                    dropped = [part["field"] for part in trace["components"]
                               if part["match_status"] == "absent_by_generator"]
                    self.assertEqual(len(dropped), 1)
                    self.assertNotIn(dropped[0], [span["label"] for span in record["spans"]])
            boundary_record = next(row for row in records if row["sample_id"] == "s3_c1f7b490f4d7c9bc")
            self.assertNotIn("SoNha", [span["label"] for span in boundary_record["spans"]])
            self.assertIn("ambiguous_label", boundary_record["review_flags"])
            self.assertTrue(any(part.get("abstain_reason") == "source_component_requires_boundary_review"
                                for part in traces[boundary_record["sample_id"]]["components"]))
            review_path = output / "manual_review_queue.csv"
            self.assertTrue(review_path.read_bytes().startswith(b"\xef\xbb\xbf"))
            with review_path.open(encoding="utf-8-sig", newline="") as handle:
                review = list(csv.DictReader(handle))
            report = json.loads((output / "coverage_report.json").read_text(encoding="utf-8"))
            self.assertEqual(len(review), report["manual_review_items"])
            manifest = json.loads((output / "generation_manifest.json").read_text(encoding="utf-8"))
            for name, expected_hash in manifest["output_sha256"].items():
                self.assertEqual(generator.digest(output / name), expected_hash)
            with patch.object(sys, "argv", ["prepare", "--output-dir", str(output)]):
                with self.assertRaises(FileExistsError):
                    generator.main()


if __name__ == "__main__":
    unittest.main()
