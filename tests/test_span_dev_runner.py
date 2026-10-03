"""Contract tests use local fixtures, never frozen benchmark test samples."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from src.evaluation.dev_runner import (
    file_hash, load_dev_input, resource_manifest, run_dev_inference,
    score_dev_predictions, write_json, write_jsonl,
)
from src.evaluation.schema import CharacterSpan, SpanModelOutput
from src.evaluation.span_scorer import compute_exact_span_metrics, validate_span_integrity


class FixtureAdapter:
    def __init__(self):
        self.received = []

    def parse_spans(self, text):
        self.received.append(text)
        if text == "99":
            raise RuntimeError("fixture failure")
        if text == "bad":
            return SpanModelOutput("", text, [CharacterSpan(0, 3, "NativeTag", text)])
        if text == "bad_text":
            return SpanModelOutput("", text, [CharacterSpan(0, 2, "SoNha")])
        return SpanModelOutput("", text, [CharacterSpan(0, 2, "SoNha", text[:2])], predicted_system="cu")


def config():
    return {"run_id": "local_fixture_dev", "model_id": "FIXTURE_ONLY", "seed": 42,
            "supported_labels": ["SoNha"], "resources": {}}


class SpanDevRunnerTests(unittest.TestCase):
    def test_declared_time_exception_masks_t1_only_without_editing_gold(self):
        gold = [{"sample_id": "fixture", "text": "12", "spans": [
            {"start": 0, "end": 2, "label": "SoNha", "system": "khong_xac_dinh"}], "address_system": "moi"}]
        predictions = [SpanModelOutput("fixture", "12", [CharacterSpan(0, 2, "SoNha", "12")], predicted_system="cu")]
        metrics = compute_exact_span_metrics(predictions, gold, excluded_t1_sample_ids=["fixture"])
        self.assertEqual(metrics["t0_exact_span"]["micro"]["total_tp"], 1)
        self.assertEqual(metrics["t1_address_system"]["total_evaluated"], 0)
        self.assertEqual(metrics["t1_address_system"]["gold_null_excluded"], 0)
        self.assertEqual(metrics["t1_address_system"]["declared_exception_excluded"], 1)
        self.assertEqual(metrics["structural_consistency"]["new_system_sample_count"], 0)
        self.assertEqual(gold[0]["address_system"], "moi")
        with self.assertRaisesRegex(ValueError, "exclusion IDs"):
            compute_exact_span_metrics(predictions, gold, excluded_t1_sample_ids=["missing"])

    def test_separate_scoring_reads_declared_t1_exclusion_from_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            gold = root / "dev.jsonl"
            write_jsonl(gold, [{"sample_id": "fixture", "text": "12", "spans": [
                {"start": 0, "end": 2, "label": "SoNha", "system": "khong_xac_dinh"}], "address_system": "moi"}])
            manifest = root / "manifest.json"
            write_json(manifest, {"status": "TRAIN_DEV_APPROVED_TEST_PENDING", "sample_counts": {"dev": 1},
                                 "evaluation_exclusions": {"t1": ["fixture"]}, "output_sha256": {"dev.jsonl": file_hash(gold)}})
            run = root / "run"
            run_dev_inference(FixtureAdapter(), [{"sample_id": "fixture", "text": "12"}], config(), run,
                              {"corpus_manifest_sha256": file_hash(manifest)})
            metrics = score_dev_predictions(run / "predictions.jsonl", gold, run, manifest)
            self.assertEqual(metrics["t0_exact_span"]["micro"]["f1"], 1.0)
            self.assertEqual(metrics["t1_address_system"]["declared_exception_excluded_ids"], ["fixture"])
            self.assertEqual(json.loads((run / "scoring_manifest.json").read_text(encoding="utf-8"))["t1_declared_exception_excluded_ids"], ["fixture"])

    def test_cli_inference_then_scoring_with_frozen_local_fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inputs = [{"sample_id": "fixture_a", "text": "12"}, {"sample_id": "fixture_b", "text": "99"}]
            source, gold = root / "dev_input.jsonl", root / "dev.jsonl"
            write_jsonl(source, inputs)
            write_jsonl(gold, [{**row, "spans": [{"start": 0, "end": 2, "label": "SoNha", "system": "khong_xac_dinh"}], "address_system": "cu"} for row in inputs])
            manifest = root / "manifest.json"
            write_json(manifest, {"status": "TRAIN_DEV_APPROVED_TEST_PENDING", "scope": "LOCAL_FIXTURE_ONLY",
                                 "sample_counts": {"dev": 2}, "output_sha256": {"dev_input.jsonl": file_hash(source), "dev.jsonl": file_hash(gold)}})
            model_config = root / "model_config.json"
            write_json(model_config, {**config(), "adapter_factory": "tests.test_span_dev_runner:FixtureAdapter"})
            run = root / "run"
            working_dir = Path(__file__).resolve().parents[1]
            inference = subprocess.run([sys.executable, "-m", "scripts.23_run_span_dev", "--input", str(source),
                "--corpus-manifest", str(manifest), "--model-config", str(model_config), "--output-dir", str(run)],
                cwd=working_dir, capture_output=True, text=True, check=False)
            self.assertEqual(inference.returncode, 0, inference.stderr)
            self.assertEqual(json.loads(inference.stdout)["sample_count"], 2)
            scoring_command = [sys.executable, "-m", "scripts.24_score_span_dev", "--predictions", str(run / "predictions.jsonl"),
                "--gold", str(gold), "--corpus-manifest", str(manifest), "--run-dir", str(run)]
            scoring = subprocess.run(scoring_command, cwd=working_dir, capture_output=True, text=True, check=False)
            self.assertEqual(scoring.returncode, 0, scoring.stderr)
            self.assertEqual(json.loads(scoring.stdout)["t0_micro"]["total_fn"], 1)
            with (run / "predictions.jsonl").open("a", encoding="utf-8") as stream:
                stream.write("\n")
            tampered = subprocess.run(scoring_command, cwd=working_dir, capture_output=True, text=True, check=False)
            self.assertNotEqual(tampered.returncode, 0)
            self.assertIn("Predictions changed", tampered.stderr)

    def test_runner_passes_only_text_and_keeps_failures_and_raw_output(self):
        with tempfile.TemporaryDirectory() as temp:
            adapter = FixtureAdapter()
            inputs = [{"sample_id": str(i), "text": text} for i, text in enumerate(("12", "99", "bad", "bad_text"))]
            output = Path(temp) / "run"
            report = run_dev_inference(adapter, inputs, config(), output)
            records = [json.loads(line) for line in (output / "predictions.jsonl").read_text().splitlines()]
            self.assertEqual(adapter.received, ["12", "99", "bad", "bad_text"])
            self.assertEqual([row["sample_id"] for row in records], ["0", "1", "2", "3"])
            self.assertEqual(report["status_counts"], {"ok": 1, "runtime_error": 1, "invalid_output": 2})
            self.assertEqual(records[2]["spans"], [])
            self.assertEqual(records[2]["raw_output"]["spans"][0]["label"], "NativeTag")
            with self.assertRaises(FileExistsError):
                run_dev_inference(adapter, inputs, config(), output)

    def test_missing_prediction_is_false_negative_not_dropped(self):
        gold = [{"sample_id": sid, "text": "12", "spans": [{"start": 0, "end": 2, "label": "SoNha"}], "address_system": "cu"} for sid in ("a", "b")]
        pred = [SpanModelOutput("a", "12", [CharacterSpan(0, 2, "SoNha", "12")], predicted_system="cu")]
        metrics = compute_exact_span_metrics(pred, gold)
        self.assertEqual(metrics["t0_exact_span"]["micro"]["total_fn"], 1)
        self.assertEqual(metrics["sample_coverage"]["missing_prediction_ids"], ["b"])
        self.assertEqual(metrics["t1_address_system"]["overall_accuracy"], 0.5)
        with self.assertRaises(ValueError):
            compute_exact_span_metrics(pred + [SpanModelOutput("extra", "")], gold)
        with self.assertRaises(ValueError):
            compute_exact_span_metrics(pred * 2, gold)

    def test_t1_null_and_district_denominator_are_explicit(self):
        gold = [
            {"sample_id": "null", "text": "12", "spans": [], "address_system": None},
            {"sample_id": "new", "text": "Xã A", "spans": [], "address_system": "moi"},
            {"sample_id": "conflict", "text": "Quận 1", "spans": [{"start": 0, "end": 6, "label": "QuanHuyen"}], "address_system": "moi"},
        ]
        pred = [SpanModelOutput(row["sample_id"], row["text"], predicted_system="khong_ro", abstain=True) for row in gold]
        metrics = compute_exact_span_metrics(pred, gold)
        self.assertEqual(metrics["t1_address_system"]["total_evaluated"], 2)
        self.assertEqual(metrics["t1_address_system"]["gold_null_excluded"], 1)
        self.assertEqual(metrics["structural_consistency"]["new_system_sample_count"], 1)
        self.assertEqual(metrics["structural_consistency"]["excluded_inconsistent_new_gold_count"], 1)

    def test_unicode_offset_is_not_normalized_and_booleans_are_rejected(self):
        text = "12, Xã A\u0300"
        start = text.index("Xã")
        span = CharacterSpan(start, len(text), "PhuongXa", text[start:])
        self.assertEqual(validate_span_integrity([span], text), [])
        self.assertTrue(validate_span_integrity([CharacterSpan(True, 2, "SoNha")], text))
        self.assertTrue(validate_span_integrity([CharacterSpan(0, 1, "SoNha")], ""))

    def test_release_gate_and_metadata_rejection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "dev_input.jsonl"
            write_jsonl(source, [{"sample_id": "a", "text": "12", "GT_SoNha": "12"}])
            manifest = root / "manifest.json"
            write_json(manifest, {"status": "BLOCKED_CONTENT_REVIEW"})
            with self.assertRaises(ValueError):
                load_dev_input(source, manifest)
            write_json(manifest, {"status": "TRAIN_DEV_APPROVED_TEST_PENDING", "sample_counts": {"dev": 1}, "output_sha256": {"dev_input.jsonl": file_hash(source)}})
            with self.assertRaises(ValueError):
                load_dev_input(source, manifest)

    def test_annotation_cannot_be_disguised_as_model_resource(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file = root / "data/interim/annotation/gold.jsonl"
            file.parent.mkdir(parents=True)
            file.write_text("private gold")
            cfg = {"resources": {"fake": {"role": "checkpoint", "path": str(file), "sha256": file_hash(file)}}}
            with self.assertRaises(ValueError):
                resource_manifest(cfg, root)

    def test_separate_scoring_freeze_and_error_penalty(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            gold = root / "dev.jsonl"
            write_jsonl(gold, [{"sample_id": sid, "text": text, "spans": [{"start": 0, "end": 2, "label": "SoNha", "system": "khong_xac_dinh"}], "address_system": "cu"} for sid, text in (("a", "12"), ("b", "99"))])
            manifest = root / "manifest.json"
            write_json(manifest, {"status": "TRAIN_DEV_APPROVED_TEST_PENDING", "sample_counts": {"dev": 2}, "output_sha256": {"dev.jsonl": file_hash(gold)}})
            run = root / "run"
            run_dev_inference(FixtureAdapter(), [{"sample_id": "a", "text": "12"}, {"sample_id": "b", "text": "99"}], config(), run, {"corpus_manifest_sha256": file_hash(manifest)})
            metrics = score_dev_predictions(run / "predictions.jsonl", gold, run, manifest)
            self.assertEqual(metrics["t0_exact_span"]["micro"]["total_fn"], 1)
            self.assertEqual(metrics["sample_coverage"]["status_counts"]["runtime_error"], 1)
            with self.assertRaises(FileExistsError):
                score_dev_predictions(run / "predictions.jsonl", gold, run, manifest)


if __name__ == "__main__":
    unittest.main()
