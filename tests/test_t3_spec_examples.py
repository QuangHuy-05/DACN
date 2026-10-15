"""Regression tests for the read-only T3 specification measurements (scripts/75_t3_spec_examples.py)."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/75_t3_spec_examples.py"
GAZETTEER = ROOT / "data/processed/gazetteer/s3_v4_nso_dual_snapshot_release2"
DATA07 = ROOT / "data/processed/benchmark/07_bidirectional_pairs_verified.csv"
HAS_REAL_DATA = GAZETTEER.exists() and DATA07.exists()


def load_script():
    spec = importlib.util.spec_from_file_location("t3_spec_examples", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ElementRuleTests(unittest.TestCase):
    """The safe 'different element' rule used to build negatives (pure function, no data)."""

    @classmethod
    def setUpClass(cls):
        cls.differ = staticmethod(load_script().Context.elements_differ)

    def test_other_street_differs(self):
        self.assertTrue(self.differ(("8", "khúc hạo"), ("8", "hàng cót")))

    def test_same_street_two_present_unequal_numbers_differ(self):
        self.assertTrue(self.differ(("8", "khúc hạo"), ("10", "khúc hạo")))

    def test_same_street_missing_number_is_not_a_negative(self):
        self.assertFalse(self.differ(("", "quốc lộ 18"), ("12", "quốc lộ 18")))
        self.assertFalse(self.differ(("", "quốc lộ 18"), ("", "quốc lộ 18")))

    def test_identical_element_does_not_differ(self):
        self.assertFalse(self.differ(("12c", "hàng cót"), ("12c", "hàng cót")))


@unittest.skipUnless(HAS_REAL_DATA, "Data 07 or the gazetteer is not available")
class RealDataReproductionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_script()
        cls.result = cls.module.run(ROOT)
        cls.facts = cls.result["facts"]
        cls.estimates = cls.result["negative_estimates"]

    def test_expected_facts_reproduce(self):
        self.assertEqual(self.facts["reproduction_mismatches"], {})
        self.assertEqual(self.facts["rows"], 600)
        self.assertEqual(self.facts["loai"], {"M": 356, "B": 244})
        self.assertEqual((self.facts["old_units_normalized"], self.facts["new_codes"]), (49, 23))
        self.assertEqual(self.facts["admin_groups"], 21)

    def test_data07_has_no_negative_or_a_c_pairs(self):
        self.assertEqual(set(self.facts["loai"]), {"B", "M"})
        self.assertEqual(self.facts["gold_edge_exists"], 600)       # every pair is an existing edge
        self.assertEqual(self.facts["head_equal_old_new"], 600)     # element text never changes

    def test_t2_default_main_numbers(self):
        self.assertEqual((self.facts["t2_cu_to_moi_main_correct"], self.facts["t2_cu_to_moi_main_silent"]), (579, 21))
        self.assertEqual((self.facts["t2_moi_to_cu_main_correct"], self.facts["t2_moi_to_cu_main_silent"]), (46, 554))
        strict = self.facts["t2_outcomes"]
        self.assertEqual(strict["T2-LOOKUP-STRICT|cu_to_moi"]["correct"], 244)
        self.assertEqual(strict["T2-LOOKUP-STRICT|moi_to_cu"]["abstain"], 600)

    def test_groups_are_concentrated(self):
        self.assertAlmostEqual(self.facts["largest_group_share"], 441 / 600)
        self.assertEqual(self.estimates["groups"]["sizes_desc"][0], 441)

    def test_negative_capacity_is_internally_consistent(self):
        n_a = self.estimates["N_A_same_new_ward_other_element"]
        self.assertEqual(n_a["ordered_pairs"], n_a["street_differs"] + n_a["same_street_numbers_differ"])
        self.assertEqual(n_a["ordered_pairs"], n_a["same_old_unit"] + n_a["different_old_unit"])
        self.assertLessEqual(n_a["capacity_at_most_2_per_anchor"], 2 * 600)
        self.assertLessEqual(n_a["groups_with_pairs"], self.facts["admin_groups"])
        # Other valid targets of one old unit exist for exactly the M rows; they are never built as negatives.
        self.assertEqual(self.estimates["excluded_other_valid_target"]["rows_with_fan_out_ge_2"], 356)

    def test_positive_gold_decision_counts(self):
        gold = self.result["positive_gold_decision_counts"]
        self.assertEqual(gold["counts"], {"SAME": 182, "SAME_CONDITIONAL": 349, "UNDETERMINED": 69})
        self.assertEqual(sum(gold["counts"].values()), 600)
        self.assertEqual(gold["by_loai_and_house_present"]["B|house=True"], 182)   # B rows are exactly the fan-out-1 rows
        self.assertEqual(gold["by_loai_and_house_present"]["M|house=False"], 7)
        self.assertEqual(len(self.result["inputs"]["gazetteer_manifest_sha256"]), 64)

    def test_gazetteer_homonym_counts(self):
        d = self.estimates["N_C_same_province_homonym_region_level"]
        self.assertEqual((d["old_new_same_name_pairs"], d["linked_by_edge"], d["no_edge"]), (1989, 1832, 157))
        self.assertEqual(d["data07_anchor_rows_with_no_edge_homonym"], 0)  # Data 07 cannot anchor this type

    def test_example_rows(self):
        e1, e2 = self.result["examples"]["E1_n_to_1"], self.result["examples"]["E2_m_to_n"]
        e3 = self.result["examples"]["E3_silent_t2"]
        self.assertEqual((e1["csv_line"], e1["LoaiAnhXa"], e1["moi_to_cu_candidate_count"]), (3, "B", 14))
        self.assertTrue(e1["edge_exists"] and not e1["moi_to_cu_default_main_correct"])
        self.assertEqual((e2["csv_line"], e2["LoaiAnhXa"], len(e2["cu_to_moi_candidates"])), (58, "M", 2))
        self.assertFalse(e2["cu_to_moi_default_main_correct"])  # one of the 21 'một phần' silent errors
        self.assertEqual(e2["cu_to_moi_strict"], "AMBIGUOUS")
        self.assertEqual((e3["csv_line"], e3["moi_to_cu_candidate_count"]), (7, 6))
        self.assertFalse(e3["moi_to_cu_default_main_correct"])
        hard_a, hard_b = self.result["examples"]["E4_hard_negative_a"], self.result["examples"]["E4_hard_negative_b"]
        self.assertEqual(hard_a["MaPhuongXaMoi"], hard_b["MaPhuongXaMoi"])      # same new ward
        self.assertEqual(hard_a["element_old"][1], hard_b["element_old"][1])    # same street
        self.assertNotEqual(hard_a["element_old"][0], hard_b["element_old"][0])  # different house number
        homonym = self.result["homonym_example"]
        self.assertEqual(homonym["homonym_new_wards"], ["Phường Diên Hồng, Tỉnh Gia Lai"])
        self.assertFalse(homonym["homonym_is_edge_target_of_old_unit"])

    def test_result_is_json_serialisable(self):
        json.dumps(self.result, ensure_ascii=False)


class CommandLineTests(unittest.TestCase):
    def test_refuses_to_overwrite_existing_output(self):
        module = load_script()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "existing.json"
            target.write_text("{}", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                code = module.main(["--out", str(target)])
            self.assertEqual(code, 3)
            self.assertEqual(target.read_text(encoding="utf-8"), "{}")


if __name__ == "__main__":
    unittest.main()
