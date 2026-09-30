"""Regression unit tests for Sprint 3 S3-04 (Corpus Gold/Split) and S3-03 (Gazetteer v2)."""

import csv
import importlib
import json
import unittest
from datetime import date
from pathlib import Path

gaz_mod = importlib.import_module("scripts.19_build_temporal_gazetteer_v2")
lookup = gaz_mod.lookup

ROOT = Path(__file__).resolve().parents[1]


class Sprint03PipelineTests(unittest.TestCase):
    def test_converter_rejects_export_text_or_system_region_drift(self):
        converter = importlib.import_module("scripts.17_convert_span_annotation_batch")
        text = "12, Đường A"
        annotation = {"result": [
            {"id": "one", "from_name": "span_label",
             "value": {"start": 0, "end": 2, "text": "99", "labels": ["SoNha"]}},
            {"id": "one", "from_name": "span_system",
             "value": {"start": 0, "end": 2, "text": "12", "choices": ["khong_xac_dinh"]}},
        ]}
        with self.assertRaisesRegex(ValueError, "exported span text differs"):
            converter.convert_annotation(annotation, text, "sample")
        annotation["result"][0]["value"]["text"] = "12"
        annotation["result"][1]["value"]["end"] = 3
        annotation["result"][1]["value"]["text"] = "12,"
        with self.assertRaisesRegex(ValueError, "span_system region differs"):
            converter.convert_annotation(annotation, text, "sample")

    def test_batch02_candidate_predictions_round_trip_without_test_data(self):
        importer = importlib.import_module("scripts.15_import_pilot_predictions")
        converter = importlib.import_module("scripts.17_convert_span_annotation_batch")
        candidate_path = ROOT / "data/interim/annotation/sprint03/batch02_span11_candidate_predictions.json"
        candidates = importer.validate_candidates(candidate_path, expected_count=232)
        self.assertEqual(len(candidates), 232)
        for sample_id, record in candidates.items():
            converted = converter.convert_annotation(
                {"result": importer.prediction_results(record)}, record["text"], sample_id
            )
            self.assertEqual(len(converted["spans"]), len(record["spans"]))

    def test_test_hold_manifest_integrity(self):
        manifest_p = ROOT / "data/interim/annotation/sprint03/test_hold_manifest_v1.json"
        self.assertTrue(manifest_p.is_file())
        with manifest_p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["total_samples"], 100)
        self.assertEqual(
            data["strata_counts"],
            {"01_new": 20, "02_noisy": 20, "03_old": 20, "04_missing": 20, "06_hybrid": 20},
        )
        self.assertEqual(len(data["samples"]), 100)

    def test_batch02_queue_and_zero_leakage(self):
        queue_p = ROOT / "data/interim/annotation/sprint03/annotation_queue_batch02_train_dev.csv"
        manifest_p = ROOT / "data/interim/annotation/sprint03/annotation_batch02_manifest.json"
        self.assertTrue(queue_p.is_file())
        self.assertTrue(manifest_p.is_file())

        with queue_p.open("r", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 232)

        # Check group separation between train and dev
        train_groups = {r["group_id"] for r in rows if r["planned_split"] == "train"}
        dev_groups = {r["group_id"] for r in rows if r["planned_split"] == "dev"}
        self.assertEqual(len(train_groups & dev_groups), 0)

        # Check zero overlap with test hold
        test_manifest_p = ROOT / "data/interim/annotation/sprint03/test_hold_manifest_v1.json"
        with test_manifest_p.open("r", encoding="utf-8") as f:
            test_data = json.load(f)
        test_groups = {s["group_id"] for s in test_data["samples"]}
        batch02_groups = train_groups | dev_groups
        self.assertEqual(len(batch02_groups & test_groups), 0)

    def test_label_studio_import_formats_have_zero_leakage(self):
        for fname in [
            "data/interim/annotation/sprint03/label_studio_batch02_import.json",
            "data/interim/annotation/sprint03/label_studio_test_benchmark_t0_import.json",
        ]:
            p = ROOT / fname
            self.assertTrue(p.is_file())
            with p.open("r", encoding="utf-8") as f:
                tasks = json.load(f)
            self.assertGreater(len(tasks), 0)
            for t in tasks:
                self.assertIn("data", t)
                self.assertEqual(set(t["data"].keys()), {"sample_id", "text"})

    def test_gazetteer_v2_manifest_and_counts(self):
        manifest_p = ROOT / "data/processed/gazetteer/s3_v2/manifest.json"
        self.assertTrue(manifest_p.is_file())
        with manifest_p.open("r", encoding="utf-8") as f:
            m = json.load(f)
        self.assertEqual(m["version"], "s3-gazetteer-v2-partial")
        self.assertEqual(m["release_status"], "PARTIAL_OLD_CODES_UNVERIFIED")
        self.assertEqual(m["counts"]["atomic_edges"], 10597)
        self.assertEqual(m["counts"]["non_atomic_transitions"], 5)
        self.assertEqual(m["counts"]["entities"], 14149)
        self.assertEqual(m["counts"]["aliases"], 187)
        self.assertEqual(len(m["output_sha256"]), 7)

    def test_gazetteer_v2_temporal_lookup_behavior(self):
        # 1. Old ward lookup prior to reform (2025-06-30)
        res_old = lookup(
            name="Phường Bến Nghé",
            level="ward",
            as_of=date(2025, 6, 30),
            province="Thành phố Hồ Chí Minh",
        )
        self.assertEqual(res_old["entity_status"], "UNIQUE_ENTITY")
        self.assertEqual(res_old["candidates"][0]["system"], "cu")
        self.assertEqual(res_old["candidates"][0]["code_status"], "candidate_third_party_unverified")
        self.assertEqual(res_old["candidates"][0]["transitions"][0]["new_ward"], "Phường Sài Gòn")

        # 2. New ward lookup after reform (2025-07-01)
        res_new = lookup(
            name="Phường Sài Gòn",
            level="ward",
            as_of=date(2025, 7, 1),
            province="Thành phố Hồ Chí Minh",
        )
        self.assertEqual(res_new["entity_status"], "UNIQUE_ENTITY")
        self.assertEqual(res_new["candidates"][0]["system"], "moi")
        self.assertEqual(res_new["candidates"][0]["code_status"], "verified_source")
        self.assertEqual(res_new["candidates"][0]["district"], "")

        # District-level island transitions stay separate from ward edges.
        island = lookup(
            name="Huyện Côn Đảo",
            level="district",
            as_of=date(2025, 6, 30),
            province="Tỉnh Bà Rịa - Vũng Tàu",
        )
        self.assertEqual(island["target_status"], "UNIQUE_TARGET")
        self.assertEqual(island["candidates"][0]["transitions"][0]["transition_kind"],
                         "DISTRICT_TO_SPECIAL_ZONE")
        self.assertEqual(island["candidates"][0]["transitions"][0]["new_ward"], "Đặc khu Côn Đảo")

        # A district from the old system cannot be used as the parent of a new ward.
        wrong_parent = lookup(
            name="Phường Sài Gòn", level="ward", as_of=date(2025, 7, 1),
            province="Thành phố Hồ Chí Minh", district="Quận 1",
        )
        self.assertEqual(wrong_parent["entity_status"], "NO_MATCH")

    def test_preflight_registers_source_parents_and_requires_near_duplicate_review(self):
        audit_mod = importlib.import_module("scripts.18_audit_corpus_split")
        report_p = ROOT / "data/interim/annotation/sprint03/split_preflight_v1/split_audit_report.json"
        parent_p = ROOT / "data/interim/annotation/sprint03/split_preflight_v1/source_parent_manifest.csv"
        self.assertTrue(report_p.is_file())
        self.assertTrue(parent_p.is_file())
        report = json.loads(report_p.read_text(encoding="utf-8"))
        self.assertEqual(report["source_parent_count"], 172)
        self.assertEqual(report["unresolved_parent_sample_ids"], [])
        self.assertEqual(report["sample_counts"], {"train": 240, "dev": 60, "test": 100})
        self.assertEqual(report["status"], "NEEDS_NEAR_DUP_REVIEW")
        self.assertGreater(report["near_duplicates_count"], 0)
        self.assertEqual(audit_mod.file_hash(parent_p), report["source_parent_manifest_sha256"])


if __name__ == "__main__":
    unittest.main()
