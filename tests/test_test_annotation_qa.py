"""Fixture tests of assisted QA gates; these are not benchmark experiments."""

import copy
import csv
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.data.test_annotation_qa import review_test_export, t1_review_findings

converter = importlib.import_module("scripts.17_convert_span_annotation_batch")


class TestAnnotationQATests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.package = self.root / "package"
        self.package.mkdir()
        text = "12, Đường A"
        result = [
            {"id": "s", "from_name": "span_label", "to_name": "address_text", "type": "labels",
             "value": {"start": 0, "end": 2, "text": "12", "labels": ["SoNha"]}},
            {"id": "s", "from_name": "span_system", "to_name": "address_text", "type": "choices",
             "value": {"start": 0, "end": 2, "text": "12", "choices": ["khong_xac_dinh"]}},
        ]
        self.model_version = "s3_span11_test100_ai_assisted_v1_not_gold"
        self.tasks = []
        locked, imports = [], []
        self.queue = self.root / "queue.csv"
        with self.queue.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=("sample_id", "text", "group_id", "planned_role"))
            writer.writeheader()
            for index in range(100):
                sid = f"fixture-{index:03}"
                data = {"sample_id": sid, "text": text}
                writer.writerow(data | {"group_id": f"g{index}", "planned_role": converter.TEST_ROLE})
                locked.append({"data": data})
                pred = {"model_version": self.model_version, "result": copy.deepcopy(result)}
                imports.append({"data": data, "predictions": [pred]})
                nested = pred | {"id": 1100 + index}
                self.tasks.append({"id": 100 + index, "project": 7, "data": data,
                    "predictions": [nested["id"]], "total_predictions": 1,
                    "annotations": [{"id": 2100 + index, "completed_by": 1,
                        "parent_prediction": nested["id"], "prediction": nested,
                        "result": copy.deepcopy(result), "was_cancelled": False}]})
        self.export = self.root / "export.json"
        self.save_export()
        files = {"test100_text_only_import.json": json.dumps(locked, ensure_ascii=False).encode(),
                 "test100_import_with_predictions.json": json.dumps(imports, ensure_ascii=False).encode(),
                 "label_studio_span11.xml": converter.LABEL_CONFIG.read_bytes(),
                 "span_11_annotation_guideline.md": converter.GUIDELINE.read_bytes()}
        for name, contents in files.items():
            (self.package / name).write_bytes(contents)
        test_hash = converter.file_hash(self.package / "test100_text_only_import.json")
        self.manifest = self.package / "manifest.json"
        self.manifest.write_text(json.dumps({
            "version": "fixture-v1", "annotation_mode": "AI_ASSISTED_HUMAN_REVIEW_PENDING",
            "status": "CANDIDATES_NOT_GOLD", "authorization": "fixture owner request",
            "model_version": self.model_version, "count": {"tasks": 100}, "test_input_sha256": test_hash,
            "benchmark_gold_read": False, "baseline_predictions_used": False,
            "training_tuning_scoring_on_test": False,
            "files": {name: {"sha256": converter.file_hash(self.package / name)} for name in files},
        }), encoding="utf-8")
        patcher = patch("src.data.test_assisted_annotation.TEST_HASH", test_hash)
        patcher.start()
        self.addCleanup(patcher.stop)

    def save_export(self):
        self.export.write_text(json.dumps(self.tasks, ensure_ascii=False), encoding="utf-8")

    def convert(self, **kwargs):
        return converter.convert_export(self.export, self.queue, self.root / "qa",
            role=converter.TEST_ROLE, test_annotation_mode="ai_assisted_human_review",
            assisted_manifest_path=self.manifest, **kwargs)

    def test_blind_default_still_rejects_predictions(self):
        result = converter.convert_export(self.export, self.queue, self.root / "blind", role=converter.TEST_ROLE)
        self.assertEqual(result["status_counts"], {"test_prediction_leakage": 100})

    def test_omitting_role_cannot_bypass_test_prediction_gate(self):
        with self.assertRaisesRegex(ValueError, "explicit frozen_benchmark_test_hold role"):
            converter.convert_export(self.export, self.queue, self.root / "without_role")

    def test_assisted_mode_requires_manifest_and_test_role(self):
        with self.assertRaisesRegex(ValueError, "test role and an assisted manifest"):
            converter.convert_export(self.export, self.queue, self.root / "invalid",
                                     role=converter.TEST_ROLE, test_annotation_mode="ai_assisted_human_review")
        with self.assertRaisesRegex(ValueError, "explicit"):
            converter.convert_export(self.export, self.queue, self.root / "invalid", role=converter.TEST_ROLE,
                                     assisted_manifest_path=self.manifest)

    def test_reviewed_annotation_can_edit_prediction_without_editing_source(self):
        self.tasks[0]["annotations"][0]["result"][0]["value"]["labels"] = ["Khac"]
        self.save_export()
        original_hash = converter.file_hash(self.export)
        result = self.convert()
        self.assertEqual(result["converted_tasks"], 100)
        self.assertEqual(result["annotation_protocol"]["mode"], "AI_ASSISTED_HUMAN_REVIEW")
        self.assertEqual(result["annotation_protocol"]["gold_approval"], "PENDING_HUMAN_ADJUDICATION")
        self.assertEqual(converter.file_hash(self.export), original_hash)

    def test_undeclared_or_mutated_prediction_is_rejected(self):
        self.tasks[0]["annotations"][0]["prediction"]["model_version"] = "evaluated-baseline"
        self.tasks[1]["annotations"][0]["prediction"]["result"][0]["value"]["labels"] = ["Khac"]
        self.save_export()
        result = self.convert()
        self.assertEqual(result["status_counts"]["conversion_error"], 2)
        self.assertEqual(result["converted_tasks"], 98)

    def test_prediction_only_does_not_become_a_human_annotation(self):
        self.tasks[0]["annotations"] = []
        self.save_export()
        result = self.convert()
        self.assertEqual(result["task_statuses"]["fixture-000"], "unannotated")

    def test_multiple_annotations_require_explicit_selection(self):
        extra = copy.deepcopy(self.tasks[0]["annotations"][0])
        extra["id"] = 9999
        self.tasks[0]["annotations"].append(extra)
        self.save_export()
        self.assertEqual(self.convert()["task_statuses"]["fixture-000"],
                         "multiple_annotations_pending_adjudication")
        mapping = self.root / "adjudication.json"
        mapping.write_text(json.dumps({"fixture-000": 9999}), encoding="utf-8")
        self.assertEqual(self.convert(adjudication_map_path=mapping)["converted_tasks"], 100)

    def test_assisted_files_and_queue_are_hash_bound(self):
        (self.package / "label_studio_span11.xml").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.convert()

    def test_export_missing_task_is_reported_and_qa_refuses_overwrite(self):
        self.tasks.pop()
        self.save_export()
        original_hash = converter.file_hash(self.export)
        out = self.root / "review"
        result = review_test_export(self.export, self.queue, out, self.manifest)
        self.assertEqual(result["missing_sample_ids"], ["fixture-099"])
        self.assertEqual(result["gold_status"], "NOT_RELEASED")
        self.assertEqual(converter.file_hash(self.export), original_hash)
        self.assertEqual((out / result["export_snapshot"]).read_bytes(), self.export.read_bytes())
        with self.assertRaises(FileExistsError):
            review_test_export(self.export, self.queue, out, self.manifest)

    def test_empty_role_selection_is_not_a_pass(self):
        with self.assertRaisesRegex(ValueError, "no tasks"):
            converter.convert_export(self.export, self.queue, self.root / "empty", role="wrong_role")

    def test_t1_unknown_admin_requests_evidence_without_rewriting_gold(self):
        record = {"text": "Phường A, Hà Nội", "address_system": "moi",
                  "spans": [{"label": "PhuongXa", "system": "khong_xac_dinh"}]}
        original = copy.deepcopy(record)
        self.assertEqual(t1_review_findings(record)[0]["code"], "t1_evidence_needs_review")
        self.assertEqual(record, original)
        record["address_system"] = None
        self.assertEqual(t1_review_findings(record), [])

    def test_t1_hybrid_needs_both_systems_or_a_recorded_temporal_basis(self):
        record = {"text": "Phường A, Quận B", "address_system": "Lai",
                  "spans": [{"label": "QuanHuyen", "system": "cu"}]}
        self.assertEqual(len(t1_review_findings(record)), 1)
        record["spans"].append({"label": "PhuongXa", "system": "moi"})
        self.assertEqual(t1_review_findings(record), [])
        record["spans"] = []
        record["text"] = "Phường A (nay là Phường B)"
        self.assertEqual(t1_review_findings(record), [])


if __name__ == "__main__":
    unittest.main()
