"""Tests of WP2b (scripts/68c_run_t1_tier2_local.py): hashes, frozen-output guard, text-only input, probe, stats."""

from __future__ import annotations

import importlib
import inspect
import json
from pathlib import Path
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
M = importlib.import_module("scripts.68c_run_t1_tier2_local")
P = importlib.import_module("src.evaluation.t1_pipeline")


class HashChecks(unittest.TestCase):
    def test_six_checkpoints_match_reviewed_hashes(self):
        for model, seed in M.RUN_ORDER:
            path = REPO / M.MULTISEED / M.run_name(model, seed) / "checkpoints" / "best.pt"
            if not path.exists():
                self.skipTest(f"{path} missing (data/interim is not tracked)")
        for model, seed in M.RUN_ORDER:
            info = M.verify_checkpoint(model, seed)
            self.assertTrue(info["sha256"].startswith(M.CHECKPOINT_PREFIX[(model, seed)]))

    def test_tier2_inputs_hash_checked(self):
        inputs = REPO / M.TIER1_RUN / "tier2_inputs"
        if not (inputs / "tier2_inputs.json").exists():
            self.skipTest("tier2_inputs missing")
        self.assertEqual(set(M.verify_inputs()), set(M.INPUT_SETS))
        with self.assertRaises(ValueError):
            M.load_text_inputs(inputs, "s3_test", "0" * 64)

    def test_wrong_checkpoint_hash_stops(self):
        original = dict(M.CHECKPOINT_PREFIX)
        path = REPO / M.MULTISEED / "dyn_seed42" / "checkpoints" / "best.pt"
        if not path.exists():
            self.skipTest("checkpoint missing")
        try:
            M.CHECKPOINT_PREFIX[("dyn", 42)] = "deadbeef"
            with self.assertRaises(ValueError):
                M.verify_checkpoint("dyn", 42)
        finally:
            M.CHECKPOINT_PREFIX.update(original)


class FrozenGuard(unittest.TestCase):
    def test_scoring_refuses_changed_prediction(self):
        old_interim, old_processed = M.INTERIM, M.PROCESSED
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            try:
                M.INTERIM, M.PROCESSED = tmp / "interim", tmp / "processed"
                (M.INTERIM / "dyn_seed42").mkdir(parents=True)
                M.PROCESSED.mkdir()
                file = M.INTERIM / "dyn_seed42" / "predictions.jsonl"
                file.write_text('{"a": 1}\n', encoding="utf-8")
                (M.PROCESSED / "frozen_hashes.json").write_text(json.dumps(
                    {"files": {"dyn_seed42/predictions.jsonl": M.sha256_file(file)}}), encoding="utf-8")
                self.assertEqual(len(M.verify_frozen()), 1)
                file.write_text('{"a": 2}\n', encoding="utf-8")
                with self.assertRaises(ValueError):
                    M.verify_frozen()
            finally:
                M.INTERIM, M.PROCESSED = old_interim, old_processed


class TextOnlyContract(unittest.TestCase):
    def test_inference_input_rejects_extra_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.jsonl"
            path.write_text(json.dumps({"key": "k", "text": "t", "gold_system": "Lai"}) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                M.load_text_inputs(Path(tmp), "x", M.sha256_file(path))
            path.write_text(json.dumps({"key": "k", "text": "t"}) + "\n", encoding="utf-8")
            self.assertEqual(M.load_text_inputs(Path(tmp), "x", M.sha256_file(path)), [{"key": "k", "text": "t"}])

    def test_probe_takes_only_matrices_and_integer_labels(self):
        params = list(inspect.signature(M.fit_probe).parameters)
        self.assertEqual(params, ["P", "x_fit", "y_fit", "x_dev", "y_dev"])  # no frame, no gold column argument


class StatsAndSelection(unittest.TestCase):
    def test_mean_std_by_hand(self):
        got = M.mean_std([0.5, 0.7, 0.9])
        self.assertEqual(got["n"], 3)
        self.assertAlmostEqual(got["mean"], 0.7)
        self.assertAlmostEqual(got["std"], 0.2)  # ddof = 1
        self.assertIsNone(M.mean_std([0.4])["std"])
        mixed = M.mean_std([0.5, "NOT_EVALUABLE_SINGLE_CLASS", None])
        self.assertEqual((mixed["n"], mixed["n_not_numeric"]), (1, 2))

    def test_l2_tie_takes_larger_l2(self):
        import numpy as np
        x = np.array([[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0]] * 4)
        y = [0, 1, 2] * 4
        model, l2, trials = M.fit_probe(P, x, y, x, y)
        self.assertTrue(M.l2_is_tie(trials))
        self.assertEqual(l2, max(P.L2_GRID))  # tier-1 rule: macro-F1, accuracy, then the larger L2
        self.assertEqual(model.l2, l2)

    def test_labels(self):
        self.assertEqual(M.final_label({"predicted_system": "Lai", "abstain": False}), "Lai")
        self.assertEqual(M.final_label({"predicted_system": "khong_ro", "abstain": False}), "khong_ro")
        self.assertEqual(M.final_label({"predicted_system": "cu", "abstain": False, "rejected": True}), "khong_ro")
        row = {"posterior": {"cu": 0.4, "moi": 0.2, "Lai": 0.4}}
        self.assertEqual(M.argmax_label(row), "cu")  # tie -> lower class index
        self.assertEqual(M.argmax_label({"rejected": True, "posterior": None}), "khong_ro")


class OutputGuard(unittest.TestCase):
    def test_refuses_existing_and_protected_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileExistsError):
                M.guard_output_dir(Path(tmp))
            self.assertTrue(str(M.guard_output_dir(Path(tmp) / "new")).endswith("new"))
        with self.assertRaises(ValueError):
            M.guard_output_dir(M.TIER1_RUN)
        with self.assertRaises(ValueError):
            M.guard_output_dir(M.TIER1_RUN / "tier2_local_new")
        with self.assertRaises(ValueError):
            M.guard_output_dir(M.MULTISEED / "anything")


if __name__ == "__main__":
    unittest.main()
