import importlib
import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.evaluation import frozen_reliability as fr
from src.evaluation.dev_runner import load_predictions

SCRIPT = "scripts.69_bootstrap_frozen_results"


def _data_available() -> bool:
    try:
        return all(p.exists() for p in fr.test_prediction_paths().values()) and (fr.CORPUS_DIR / "manifest.json").exists()
    except Exception:
        return False


class SyntheticStatisticsTests(unittest.TestCase):
    def test_holm_adjust_matches_hand_calculation(self):
        adjusted = fr.holm_adjust([0.01, 0.04, 0.03, None])
        # sorted p: 0.01 (x4), 0.03 (x3), 0.04 (x2); None is skipped
        self.assertAlmostEqual(adjusted[0], 0.04)
        self.assertAlmostEqual(adjusted[2], 0.09)
        self.assertAlmostEqual(adjusted[1], 0.09)  # monotone: max(0.09, 0.08)
        self.assertIsNone(adjusted[3])

    def test_macro_f1_counts_resamples_missing_a_class(self):
        macro = fr.MacroF1()
        full = np.array([[0, 0], [1, 1], [2, 2]])
        self.assertEqual(macro(full), 1.0)
        self.assertEqual(macro.missing_class_calls, 0)
        macro(np.array([[0, 0], [1, 3]]))
        self.assertEqual(macro.missing_class_calls, 1)
        self.assertAlmostEqual(macro.missing_share, 0.5)

    def test_lai_f1_undefined_without_gold_lai(self):
        self.assertTrue(np.isnan(fr.lai_f1_stat(np.array([[0, 0], [1, 1]]))))
        self.assertEqual(fr.lai_f1_stat(np.array([[2, 2], [0, 2]])), 2 / 3)

    def test_support_flags(self):
        self.assertEqual(fr.support_flag(0), "NOT_EVALUABLE_NO_GOLD_SUPPORT")
        self.assertEqual(fr.support_flag(5), "LOW_SUPPORT")
        self.assertEqual(fr.support_flag(10), "OK")

    def test_bootstrap_is_deterministic_by_seed(self):
        counts = np.array([[3, 1, 0], [2, 0, 1], [4, 1, 1], [1, 0, 0]] * 5)
        first = fr.stats.bootstrap_ci(fr.f1_stat, counts, 500, seed=7)
        second = fr.stats.bootstrap_ci(fr.f1_stat, counts, 500, seed=7)
        other = fr.stats.bootstrap_ci(fr.f1_stat, counts, 500, seed=8)
        self.assertEqual((first["ci_low"], first["ci_high"]), (second["ci_low"], second["ci_high"]))
        self.assertNotEqual((first["ci_low"], first["ci_high"]), (other["ci_low"], other["ci_high"]))

    def test_identical_systems_are_degenerate_not_a_made_up_p(self):
        counts = np.array([[3, 1, 0], [2, 0, 1], [4, 1, 1]])
        result = fr.paired_comparison(fr.f1_stat, counts, counts, [1, 0, 1], [1, 0, 1])
        self.assertEqual(result["randomization"]["status"], "DEGENERATE")
        self.assertIsNone(result["randomization"]["p_value"])
        self.assertEqual(result["mcnemar"]["status"], "DEGENERATE")


@unittest.skipUnless(_data_available(), "frozen Sprint 3 predictions are not available")
class FrozenDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.golds, cls.excluded = fr.load_gold("test")
        cls.paths = fr.test_prediction_paths()
        cls.script = importlib.import_module(SCRIPT)
        cls.systems = {n: cls.script.load_system(n, p, cls.golds, cls.excluded) for n, p in cls.paths.items()}

    def test_per_sample_sums_equal_scorer_totals(self):
        for name, data in self.systems.items():
            self.assertTrue(all(data["scorer_agrees"].values()), (name, data["scorer_agrees"]))

    def test_published_scores_reproduce(self):
        rows, ok = self.script.reproduction_rows(self.systems)
        self.assertTrue(ok, rows)

    def test_t1_mask_is_64_20_16(self):
        t1 = self.systems["HEUR-JW"]["metrics"]["t1_address_system"]
        self.assertEqual((t1["total_evaluated"], t1["gold_null_excluded"], t1["declared_exception_excluded"]), (64, 20, 16))
        self.assertEqual(len(self.systems["HEUR-JW"]["t1"]), 64)

    def test_systems_without_t1_head_are_not_implemented_not_zero(self):
        tables = self.script.ci_tables(
            {n: self.systems[n] for n in fr.T1_NOT_IMPLEMENTED}, None, None)
        self.assertTrue(tables["t1"])
        for row in tables["t1"]:
            self.assertEqual(row["status"], "NOT_IMPLEMENTED")
            self.assertIsNone(row["estimate"])

    def test_every_test_sample_is_its_own_source_group(self):
        self.assertEqual(len({g["source_group"] for g in self.golds}), len(self.golds))

    def test_hash_mismatch_stops_before_any_computation(self):
        with tempfile.TemporaryDirectory() as tmp:
            tampered = Path(tmp) / "predictions.jsonl"
            tampered.write_bytes(self.paths["HEUR-JW"].read_bytes() + b"\n")
            with self.assertRaises(ValueError):
                fr.verify_frozen_hashes({"HEUR-JW": tampered})

    def test_frozen_hashes_verify(self):
        report = fr.verify_frozen_hashes(self.paths)
        self.assertEqual(set(report), set(fr.SYSTEMS))

    def test_gold_hash_checked_against_manifest(self):
        self.assertEqual(len(self.golds), 100)
        self.assertEqual(len(load_predictions(self.paths["HEUR-JW"])), 100)


if __name__ == "__main__":
    unittest.main()
