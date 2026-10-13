"""Tests for the shared Group 1 modules: leak_guard and stats."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

from src.data.administrative_mapping import default_mapping_path, load_administrative_mapping
from src.evaluation import leak_guard
from src.evaluation import stats
from src.evaluation.leak_guard import (
    ExclusionIndex,
    REASON_EXACT,
    REASON_NORMALIZED,
    admin_group_key,
    filter_benchmark,
    normalize_for_overlap,
)

ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = ROOT / leak_guard.DEFAULT_CORPUS_DIR


def _small_index() -> ExclusionIndex:
    return ExclusionIndex.from_records({
        "train": [{"sample_id": "t1", "source_group": "g1", "text": "12, Đường Láng, Phường Láng Hạ, Hà Nội"}],
        "dev": [{"sample_id": "d1", "source_group": "g2", "text": "5 Ngõ 3, Phố Huế"}],
        "test": [{"sample_id": "x1", "source_group": "g3", "text": "99 Trần Hưng Đạo"}],
    })


class NormalizeTests(unittest.TestCase):
    def test_case_punctuation_and_spacing(self):
        a = normalize_for_overlap("  12, Đường  Láng; Phường Láng Hạ - Hà Nội. ")
        b = normalize_for_overlap("12 đường láng phường láng hạ hà nội")
        self.assertEqual(a, b)

    def test_diacritics_are_kept(self):
        self.assertNotEqual(normalize_for_overlap("Phường Mai"), normalize_for_overlap("Phuong Mai"))

    def test_nfc_equivalence(self):
        import unicodedata
        word = "Đường Láng"
        self.assertEqual(normalize_for_overlap(unicodedata.normalize("NFD", word)),
                         normalize_for_overlap(word))


class FilterBenchmarkTests(unittest.TestCase):
    def test_drops_case_and_punctuation_variants_only(self):
        frame = pd.DataFrame({
            "ChuoiDiaChi": [
                "12, Đường Láng, Phường Láng Hạ, Hà Nội",      # exact
                "12 ĐƯỜNG LÁNG PHƯỜNG LÁNG HẠ HÀ NỘI",         # case + punctuation
                "5, Ngõ 3, Phố Huế",                            # punctuation only, dev
                "99 Trần Hưng Đạo, Hà Nội",                     # extra word: NOT a match
                "13, Đường Láng, Phường Láng Hạ, Hà Nội",      # different number: NOT a match
            ],
            "Ghi": list("abcde"),
        })
        kept, dropped = filter_benchmark(frame, "ChuoiDiaChi", index=_small_index())
        self.assertEqual(list(kept["Ghi"]), ["d", "e"])
        self.assertEqual(list(dropped["Ghi"]), ["a", "b", "c"])
        self.assertEqual(list(dropped["LyDoLoai"]), [REASON_EXACT, REASON_NORMALIZED, REASON_NORMALIZED])
        self.assertEqual(list(dropped["SplitGayTrung"]), ["train", "train", "dev"])
        self.assertEqual(list(dropped["SampleIdGayTrung"]), ["t1", "t1", "d1"])
        self.assertEqual(len(kept) + len(dropped), len(frame))

    def test_split_subset_and_missing_column(self):
        frame = pd.DataFrame({"ChuoiDiaChi": ["99 trần hưng đạo", "5 ngõ 3 phố huế"]})
        index = _small_index()
        kept, dropped = filter_benchmark(frame, "ChuoiDiaChi", splits=("test",), index=index)
        self.assertEqual(list(dropped["SplitGayTrung"]), ["test"])
        self.assertEqual(len(kept), 1)
        with self.assertRaises(ValueError):
            filter_benchmark(frame, "Khac", index=index)

    def test_split_not_in_index_is_an_error(self):
        index = ExclusionIndex.from_records({"train": [{"sample_id": "a", "text": "x"}]}, ("train",))
        with self.assertRaises(ValueError):
            filter_benchmark(pd.DataFrame({"t": ["x"]}), "t", splits=("train", "test"), index=index)

    def test_empty_frame(self):
        kept, dropped = filter_benchmark(pd.DataFrame({"t": []}), "t", index=_small_index())
        self.assertEqual((len(kept), len(dropped)), (0, 0))
        self.assertIn("LyDoLoai", dropped.columns)


class CorpusLoadingTests(unittest.TestCase):
    def test_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            files = {
                "train.jsonl": "a", "dev.jsonl": "b", "test_benchmark_t0.jsonl": "c",
                "identity_registry.jsonl": "d",
            }
            for name, content in files.items():
                (base / name).write_text(content, encoding="utf-8")
            expected = {n: hashlib.sha256(c.encode()).hexdigest() for n, c in files.items()}
            expected["dev.jsonl"] = "0" * 64
            (base / "manifest.json").write_text(json.dumps({"output_sha256": expected}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "HASH_MISMATCH dev.jsonl"):
                leak_guard.load_corpus_records(base)

    def test_missing_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                leak_guard.load_corpus_records(Path(tmp))

    @unittest.skipUnless((CORPUS_DIR / "manifest.json").exists(), "frozen corpus not available")
    def test_real_corpus_exact_overlap_counts(self):
        index = leak_guard.build_exclusion_index(corpus_dir=CORPUS_DIR)
        self.assertEqual(sum(len(e) for e in index.by_text.values()), 400)
        self.assertEqual({s: len(g) > 0 for s, g in index.groups_by_split.items()},
                         {"train": True, "dev": True, "test": True})
        exact = index.exact_raw_texts()
        expected = {
            "01_full_address_new_verified.csv": 20, "03_real_address_old_1500.csv": 21,
            "04_missing_fields_800.csv": 21, "06_hybrid_addresses_600.csv": 20,
        }
        for filename, count in expected.items():
            path = ROOT / "data/processed/benchmark" / filename
            if not path.exists():
                self.skipTest(f"{filename} not available")
            frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
            self.assertEqual(int(frame["ChuoiDiaChi"].isin(exact).sum()), count, filename)


@unittest.skipUnless(default_mapping_path().exists(), "administrative mapping CSV not available")
class AdminGroupKeyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mapping = load_administrative_mapping(default_mapping_path())

    def test_old_and_new_forms_share_a_group(self):
        checked = 0
        for old, targets in list(self.mapping.old_to_new.items())[:300]:
            for target in targets:
                old_key = admin_group_key(old[0], old[1], old[2], self.mapping)
                new_key = admin_group_key(target.province, "", target.ward, self.mapping)
                self.assertTrue(old_key.startswith("ADM|"))
                self.assertEqual(old_key, new_key)
                checked += 1
        self.assertGreater(checked, 0)

    def test_hybrid_address_falls_through_to_new_ward(self):
        old, targets = next(iter(self.mapping.old_to_new.items()))
        target = targets[0]
        hybrid = admin_group_key(old[0], "Quận Không Tồn Tại", target.ward, self.mapping)
        self.assertEqual(hybrid, admin_group_key(target.province, "", target.ward, self.mapping))

    def test_shared_territory_is_one_group(self):
        # A new ward fed by several old wards must give every source the same key.
        new_key, origins = next((k, v) for k, v in self.mapping.new_to_old.items() if len(v) > 1)
        keys = {admin_group_key(o[0], o[1], o[2], self.mapping) for o in origins}
        self.assertEqual(len(keys), 1)

    def test_unresolved_is_stable_and_normalised(self):
        a = admin_group_key("Hà Nội", "Quận X", "Phường  Không Có", self.mapping)
        b = admin_group_key("hà nội", "quận x", "phường không có", self.mapping)
        self.assertTrue(a.startswith("UNRESOLVED|"))
        self.assertEqual(a, b)


class StatsTests(unittest.TestCase):
    @staticmethod
    def _counts(n: int, seed: int, p_hit: float = 0.8) -> np.ndarray:
        rng = np.random.default_rng(seed)
        hit = rng.random(n) < p_hit
        return np.column_stack([hit * rng.integers(1, 5, n), (~hit) * 1, (~hit) * rng.integers(0, 3, n)])

    def test_micro_f1_uses_summed_counts_not_mean_of_f1(self):
        counts = np.array([[1, 0, 0], [0, 3, 1]])
        self.assertAlmostEqual(stats.micro_f1_from_counts(counts), 2 / (2 + 3 + 1))
        self.assertTrue(np.isnan(stats.micro_f1_from_counts(np.zeros((3, 3)))))

    def test_bootstrap_is_deterministic_by_seed(self):
        data = self._counts(60, 1)
        a = stats.bootstrap_ci(stats.micro_f1_from_counts, data, 500, seed=7)
        b = stats.bootstrap_ci(stats.micro_f1_from_counts, data, 500, seed=7)
        c = stats.bootstrap_ci(stats.micro_f1_from_counts, data, 500, seed=8)
        self.assertEqual(a, b)
        self.assertNotEqual((a["ci_low"], a["ci_high"]), (c["ci_low"], c["ci_high"]))
        self.assertLessEqual(a["ci_low"], a["estimate"])
        self.assertGreaterEqual(a["ci_high"], a["estimate"])

    def test_bootstrap_ci_covers_true_value_on_synthetic_data(self):
        # True mean of a Bernoulli(0.7) column is 0.7; ~95% of intervals should cover it.
        covered, trials = 0, 150
        for trial in range(trials):
            rng = np.random.default_rng(1000 + trial)
            data = (rng.random(200) < 0.7).astype(float)
            result = stats.bootstrap_ci(stats.exact_match_rate, data, 400, seed=trial)
            covered += result["ci_low"] <= 0.7 <= result["ci_high"]
        self.assertGreaterEqual(covered / trials, 0.88)
        self.assertLessEqual(covered / trials, 0.995)

    def test_cluster_bootstrap_is_wider_with_correlated_clusters(self):
        rng = np.random.default_rng(3)
        cluster = np.repeat(np.arange(20), 10)
        values = (rng.random(20)[cluster] < 0.5).astype(float)  # whole cluster hit or miss
        plain = stats.bootstrap_ci(stats.exact_match_rate, values, 1000, seed=1)
        grouped = stats.cluster_bootstrap_ci(stats.exact_match_rate, values, cluster, 1000, seed=1)
        self.assertGreater(grouped["ci_high"] - grouped["ci_low"], plain["ci_high"] - plain["ci_low"])
        self.assertEqual(grouped["n_clusters"], 20)

    def test_paired_bootstrap_delta_detects_clear_gap(self):
        a = self._counts(120, 5, 0.9)
        b = self._counts(120, 5, 0.9)
        b[:60] = [0, 1, 1]  # system B fails on the first half of the same samples
        result = stats.paired_bootstrap_delta(stats.micro_f1_from_counts, a, b, 800, seed=2)
        self.assertGreater(result["estimate"], 0)
        self.assertGreater(result["ci_low"], 0)
        self.assertEqual(result["prop_delta_le_0"], 0.0)
        again = stats.paired_bootstrap_delta(stats.micro_f1_from_counts, a, b, 800, seed=2)
        self.assertEqual(result, again)

    def test_paired_bootstrap_with_clusters_and_length_mismatch(self):
        a, b = self._counts(40, 1), self._counts(40, 2)
        clusters = np.repeat(np.arange(8), 5)
        result = stats.paired_bootstrap_delta(stats.micro_f1_from_counts, a, b, 300, cluster_ids=clusters, seed=1)
        self.assertEqual(result["n_clusters"], 8)
        with self.assertRaises(ValueError):
            stats.paired_bootstrap_delta(stats.micro_f1_from_counts, a, b[:10], 10, seed=1)

    def test_approximate_randomization(self):
        a = self._counts(100, 9, 0.95)
        b = a.copy()
        b[:40] = [0, 1, 1]
        diff = stats.approximate_randomization(stats.micro_f1_from_counts, a, b, 999, seed=4)
        self.assertLess(diff["p_value"], 0.01)
        c = self._counts(100, 10, 0.8)
        d = self._counts(100, 11, 0.8)
        same = stats.approximate_randomization(stats.micro_f1_from_counts, c, d, 999, seed=4)
        self.assertGreater(same["p_value"], 0.05)
        self.assertEqual(same, stats.approximate_randomization(stats.micro_f1_from_counts, c, d, 999, seed=4))

    def test_mcnemar_matches_hand_computation(self):
        # b=5, c=1: n=6, P(X<=1)=(1+6)/64 -> p = 14/64
        self.assertAlmostEqual(stats.mcnemar_exact(5, 1)["p_value"], 14 / 64)
        # b=10, c=0: p = 2/1024
        self.assertAlmostEqual(stats.mcnemar_exact(10, 0)["p_value"], 2 / 1024)
        # b=c=3: two-sided tail exceeds 1 -> capped at 1
        self.assertEqual(stats.mcnemar_exact(3, 3)["p_value"], 1.0)
        self.assertEqual(stats.mcnemar_exact(1, 5)["p_value"], stats.mcnemar_exact(5, 1)["p_value"])
        with self.assertRaises(ValueError):
            stats.mcnemar_exact(-1, 2)

    def test_mcnemar_large_counts_do_not_overflow(self):
        result = stats.mcnemar_exact(900, 100)
        self.assertEqual(result["status"], "OK")
        self.assertLess(result["p_value"], 1e-100)

    def test_edge_cases_return_null_with_reason(self):
        fn = stats.micro_f1_from_counts
        empty = np.zeros((0, 3))
        for result in (
            stats.bootstrap_ci(fn, empty, 10, seed=1),
            stats.cluster_bootstrap_ci(fn, empty, [], 10, seed=1),
            stats.paired_bootstrap_delta(fn, empty, empty, 10, seed=1),
        ):
            self.assertIsNone(result["ci_low"])
            self.assertEqual(result["status"], "NOT_EVALUABLE_NO_SUPPORT")
            self.assertEqual(result["reason"], "NO_UNITS")
        self.assertIsNone(stats.approximate_randomization(fn, empty, empty, 10, seed=1)["p_value"])

        same = np.tile([2, 1, 1], (10, 1))
        result = stats.bootstrap_ci(fn, same, 10, seed=1)
        self.assertEqual((result["status"], result["reason"]), ("DEGENERATE", "ALL_UNITS_IDENTICAL"))
        self.assertIsNone(result["ci_low"])
        self.assertAlmostEqual(result["estimate"], 4 / 6)

        data = self._counts(10, 1)
        single = stats.cluster_bootstrap_ci(fn, data, ["g"] * 10, 10, seed=1)
        self.assertEqual(single["reason"], "SINGLE_CLUSTER")
        self.assertIsNone(single["ci_low"])
        self.assertEqual(stats.mcnemar_exact(0, 0)["reason"], "NO_DISCORDANT_PAIRS")
        self.assertIsNone(stats.mcnemar_exact(0, 0)["p_value"])
        self.assertEqual(
            stats.approximate_randomization(fn, data, data.copy(), 10, seed=1)["reason"], "ALL_PAIRS_IDENTICAL")

    def test_statistic_without_support_is_not_evaluable(self):
        result = stats.bootstrap_ci(stats.micro_f1_from_counts, np.array([[0, 0, 0], [0, 0, 0]]), 10, seed=1)
        # Identical rows are caught first; the estimate itself is not finite.
        self.assertIsNone(result["ci_low"])
        mixed = np.array([[0, 0, 0], [0, 0, 0], [0, 0, 0], [1, 0, 0]])
        out = stats.bootstrap_ci(stats.micro_f1_from_counts, mixed, 50, seed=1)
        self.assertEqual(out["status"], "OK")
        self.assertGreater(out["n_nonfinite_resamples"], 0)


if __name__ == "__main__":
    unittest.main()
