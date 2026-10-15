"""Fictional final-test fixtures: no real test100 inputs or model experiments."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.evaluation.dev_runner import file_hash, write_json, write_jsonl, run_dev_inference
from src.evaluation.schema import CharacterSpan, SpanModelOutput
from src.evaluation import test_runner as runner
from src.data.test_corpus_release import APPROVED_STATUS


class FixtureAdapter:
    def parse_spans(self, text):
        if text.startswith("99"):
            raise RuntimeError("fictional failure")
        return SpanModelOutput("", text, [CharacterSpan(0, 2, "SoNha", text[:2])], predicted_system="khong_ro")


class FinalTestPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.input = self.root / "test_input.jsonl"
        self.gold = self.root / "test_benchmark_t0.jsonl"
        self.manifest = self.root / "manifest.json"
        self.config = self.root / "config.json"
        self.lock = self.root / "selection.json"
        self.samples = [{"sample_id": "fixture-a", "text": "12, gần Cầu A"},
                        {"sample_id": "fixture-b", "text": "99, Đường B"}]
        self.golds = [{**row, "source_group": "group" + str(i), "address_system": "moi",
            "spans": [{"start": 0, "end": 2, "label": "SoNha", "system": "khong_xac_dinh"}]} for i, row in enumerate(self.samples)]
        self.golds[0]["spans"].append({"start": 4, "end": 13, "label": "MocDinhVi", "system": "khong_xac_dinh"})
        write_jsonl(self.input, self.samples)
        write_jsonl(self.gold, self.golds)
        self.release = {"status": APPROVED_STATUS, "sample_counts": {"test": 2},
            "source_train_dev_manifest_sha256": "fixture-source-sha", "evaluation_exclusions": {"t1": ["fixture-a"]},
            "output_sha256": {"test_input.jsonl": file_hash(self.input), "test_benchmark_t0.jsonl": file_hash(self.gold)}}
        self.model = {"model_id": "CRF-INDEP", "run_id": "fixture_final_test", "seed": 42,
                      "supported_labels": ["SoNha"], "t1_implemented": False, "adapter_kwargs": {}, "resources": {}}
        (self.root / "dev-evidence.txt").write_text("fictional dev evidence", encoding="utf-8")
        self.selection = {"status": "DEV_SELECTION_FROZEN", "model_id": "CRF-INDEP", "selection_split": "dev",
            "experiment_kind": "fixture", "config_identity_sha256": runner.config_identity(self.model),
            "resources": {}, "code_sha256": {}, "dev_corpus_manifest_sha256": "fixture-source-sha",
            "dev_evidence": {"dev-evidence.txt": file_hash(self.root / "dev-evidence.txt")}}
        self.save()
        for target, value in (("src.evaluation.test_runner.ROOT", self.root),
                              ("src.evaluation.dev_runner.runtime_manifest", {"hardware": "fixture"})):
            mocker = patch(target, value) if target.endswith(".ROOT") else patch(target, return_value=value)
            mocker.start()
            self.addCleanup(mocker.stop)

    def save(self):
        write_json(self.manifest, self.release)
        write_json(self.config, self.model)
        write_json(self.lock, self.selection)

    def infer(self):
        output = self.root / "run"
        runner.run_test_inference(self.input, self.manifest, self.config, self.lock, output,
                                  adapter=FixtureAdapter(), fixture=True)
        self.assertFalse((output / "metrics.json").exists())
        return output

    def test_separate_freeze_score_full11_fn_mask_t0_and_runtime_error(self):
        output = self.infer()
        metrics = runner.score_test_predictions(output, self.gold, self.manifest, self.input, fixture=True)
        self.assertEqual(metrics["t0_exact_span"]["micro"]["total_tp"], 1)
        self.assertEqual(metrics["t0_exact_span"]["micro"]["total_fn"], 2)
        self.assertEqual(metrics["t1_address_system"]["declared_exception_excluded_ids"], ["fixture-a"])
        self.assertIsNone(metrics["t1_address_system"]["overall_accuracy"])
        self.assertEqual(metrics["t1_address_system"]["model_task_status"], "NOT_IMPLEMENTED")
        self.assertEqual(metrics["experiment_kind"], "fixture")
        with self.assertRaises(FileExistsError):
            runner.score_test_predictions(output, self.gold, self.manifest, self.input, fixture=True)

    def test_zero_denominator_is_null(self):
        self.release["evaluation_exclusions"]["t1"] = [row["sample_id"] for row in self.samples]
        self.save()
        metrics = runner.score_test_predictions(self.infer(), self.gold, self.manifest, self.input, fixture=True)
        self.assertIsNone(metrics["structural_consistency"]["quan_huyen_false_positive_rate_on_new"])

    def test_fixture_lock_does_not_open_real_test(self):
        with self.assertRaisesRegex(ValueError, "FIXTURE_LOCK"):
            runner.check_selection_lock(self.lock, self.model)

    def test_selection_pending_and_modified_config_are_rejected(self):
        self.selection["status"] = "PENDING_DEV_SELECTION"
        self.save()
        with self.assertRaisesRegex(ValueError, "SELECTION_LOCK"):
            self.infer()
        self.selection["status"] = "DEV_SELECTION_FROZEN"
        self.model["seed"] = 1337
        self.save()
        with self.assertRaisesRegex(ValueError, "SELECTION_LOCK"):
            self.infer()

    def test_no_gold_read_during_inference(self):
        self.gold.unlink()
        self.infer()

    def test_hidden_metadata_and_duplicate_input_are_rejected(self):
        for rows in ([{**self.samples[0], "GT_SoNha": "12"}], [self.samples[0], self.samples[0]]):
            write_jsonl(self.input, rows)
            self.release["output_sha256"]["test_input.jsonl"] = file_hash(self.input)
            self.save()
            with self.assertRaises(ValueError):
                self.infer()

    def test_prediction_and_gold_tamper_rejected(self):
        output = self.infer()
        with (output / "predictions.jsonl").open("a", encoding="utf-8") as stream:
            stream.write("{}\n")
        with self.assertRaisesRegex(ValueError, "FROZEN_PREDICTION"):
            runner.score_test_predictions(output, self.gold, self.manifest, self.input, fixture=True)

    def test_dev_api_still_rejects_test_run(self):
        with self.assertRaisesRegex(ValueError, "dev run"):
            run_dev_inference(FixtureAdapter(), self.samples, self.model, self.root / "dev")

    def test_dev_evidence_tamper_rejected(self):
        (self.root / "dev-evidence.txt").write_text("changed")
        with self.assertRaisesRegex(ValueError, "EVIDENCE_CHANGED"):
            self.infer()

    def test_dev_selection_fixture_is_frozen_and_higher_threshold_breaks_tie(self):
        source = self.root / "train_dev_manifest.json"
        write_json(source, {"status": "TRAIN_DEV_APPROVED_TEST_PENDING"})
        folders = []
        final = None
        for threshold in (0.82, 0.86):
            folder = self.root / str(threshold)
            folder.mkdir()
            config = {**self.model, "model_id": "HEUR-JW", "run_id": "fixture_dev",
                      "adapter_kwargs": {"similarity_threshold": threshold}}
            metric = {"t0_exact_span": {"micro": {"total_tp": 1, "total_fp": 0, "total_fn": 1},
                                      "per_label": {"SoNha": {"tp": 1, "fp": 0, "fn": 1, "support": 2}}}}
            write_json(folder / "model_config.json", config)
            write_json(folder / "metrics.json", metric)
            write_jsonl(folder / "predictions.jsonl", [])
            write_json(folder / "run_manifest.json", {"split": "dev", "track": "T0_T1_DEV", "model_id": "HEUR-JW",
                "inputs": {"corpus_manifest_sha256": file_hash(source)}, "output_sha256": {
                    name: file_hash(folder / name) for name in ("model_config.json", "predictions.jsonl")}})
            write_json(folder / "scoring_manifest.json", {"split": "dev", "corpus_manifest_sha256": file_hash(source),
                "prediction_sha256": file_hash(folder / "predictions.jsonl"), "output_sha256": {"metrics.json": file_hash(folder / "metrics.json")}})
            folders.append(folder)
            final = {**config, "run_id": "fixture_test_selected"}
        config_path = self.root / "final.json"
        write_json(config_path, final)
        lock_path = self.root / "chosen.json"
        selected = runner.freeze_dev_selection(config_path, folders, source, lock_path, fixture=True)
        self.assertEqual(selected["selected_dev_run"], "0.86")
        self.assertEqual(selected["experiment_kind"], "fixture")
        with self.assertRaisesRegex(ValueError, "FIXTURE_LOCK"):
            runner.check_selection_lock(lock_path, final)
        with self.assertRaises(FileExistsError):
            runner.freeze_dev_selection(config_path, folders, source, lock_path, fixture=True)

    def test_ablation_requires_same_checkpoint_and_disabled_constraint(self):
        base = {**self.model, "model_id": "PROPOSED-DYN", "adapter_kwargs": {"config": {
            "model_id": "PROPOSED-DYN", "structural_policy": {"enabled": True}}},
            "resources": {"checkpoint": {"path": "fixture.pt", "sha256": "a" * 64}}}
        ablation = copy.deepcopy(base)
        ablation["model_id"] = ablation["adapter_kwargs"]["config"]["model_id"] = "PROPOSED-NO-CONSTRAINT"
        base_path, ablation_path = self.root / "base.json", self.root / "ablation.json"
        write_json(base_path, base)
        write_json(ablation_path, ablation)
        with patch("src.evaluation.test_runner.check_selection_lock"):
            with self.assertRaisesRegex(ValueError, "MUST_BE_DISABLED"):
                runner.derive_ablation_lock(self.lock, base_path, ablation_path, self.root / "ablation_lock.json")
            ablation["adapter_kwargs"]["config"]["structural_policy"]["enabled"] = False
            ablation["resources"]["checkpoint"]["sha256"] = "b" * 64
            write_json(ablation_path, ablation)
            with self.assertRaisesRegex(ValueError, "SAME_CHECKPOINT"):
                runner.derive_ablation_lock(self.lock, base_path, ablation_path, self.root / "ablation_lock.json")


if __name__ == "__main__":
    unittest.main()
