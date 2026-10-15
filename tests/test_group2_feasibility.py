"""Tests for the G2-6 data feasibility audit (pure logic plus real-data facts)."""

from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/74_audit_data_feasibility.py"
RUN_V3 = ROOT / "data/processed/evaluation/sprint04/data_feasibility_20261016_v3"

spec = importlib.util.spec_from_file_location("audit74", SCRIPT)
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)

HAS_REAL_DATA = all((ROOT / p).exists() for p in (
    A.PAIRS, A.DATA07, A.GAZETTEER_DIR / "edges.csv", A.SNAPSHOT_FULL, A.SNAPSHOT_BALANCED,
    A.SOURCE_REGISTER, A.DECISION_LOG, A.TB243_MANIFEST, A.CORPUS_DIR / "train.jsonl"))


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


class ClassifySupportTests(unittest.TestCase):
    def test_three_states(self):
        self.assertEqual(A.classify_support(30, 10, 500), "RUNNABLE_NOW")
        self.assertEqual(A.classify_support(29, 10, 500), "NEEDS_NEW_SOURCE")
        self.assertEqual(A.classify_support(30, 9, 500), "NEEDS_NEW_SOURCE")
        self.assertEqual(A.classify_support(0, 0, 3), "NOT_FEASIBLE")
        self.assertEqual(A.classify_support(0, 0, 10), "NEEDS_NEW_SOURCE")


class StreetDependenceTests(unittest.TestCase):
    def test_single_target_not_applicable(self):
        rows = [{"Target": "t1", "Street": "Phố A"}, {"Target": "t1", "Street": "Phố B"}]
        self.assertEqual(A.street_dependence(rows), "NOT_APPLICABLE_SINGLE_TARGET")

    def test_streets_separate_targets(self):
        rows = [{"Target": "t1", "Street": "Phố A"}, {"Target": "t2", "Street": "Đường B"}]
        self.assertEqual(A.street_dependence(rows), "STREET_SEPARATES_TARGETS")

    def test_same_street_two_targets(self):
        # "Phố A" and "A" share a street key, so the street cannot decide the target.
        rows = [{"Target": "t1", "Street": "Phố A"}, {"Target": "t2", "Street": "A"}]
        self.assertEqual(A.street_dependence(rows), "STREET_SHARED_ACROSS_TARGETS")

    def test_blank_streets_are_shared(self):
        rows = [{"Target": "t1", "Street": ""}, {"Target": "t2", "Street": ""}]
        self.assertEqual(A.street_dependence(rows), "STREET_SHARED_ACROSS_TARGETS")


class UnitTableTests(unittest.TestCase):
    def test_two_valid_targets_are_counted(self):
        def row(target, street):
            return {"Status": A.ST_ELIGIBLE, "OldKeyNormalized": "u1", "NewTarget": target, "TenDuong": street,
                    "InData07": True, "AdminGroup": "ADM|x", "GazetteerFanOut": 2, "Relation": "M"}
        rows = [row("t1", "A"), row("t2", "B"), {**row("t1", "C"), "Status": A.ST_NOT_EDGE}]
        table = A.unit_table(rows)
        self.assertEqual(len(table), 1)
        self.assertEqual(table[0]["DistinctValidTargets"], 2)
        self.assertEqual(table[0]["Rows"], 2)
        self.assertEqual(table[0]["StreetDependence"], "STREET_SEPARATES_TARGETS")


class OutputGuardTests(unittest.TestCase):
    def test_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(A.main(["--out-dir", tmp]), 3)

    def test_missing_input_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(A.main(["--root", tmp, "--out-dir", str(Path(tmp) / "out")]), 2)
            self.assertFalse((Path(tmp) / "out").exists())


@unittest.skipUnless(HAS_REAL_DATA, "real data not available")
class RealDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "run"
        code = A.main(["--out-dir", str(cls.out)])
        assert code == 0
        cls.metrics = json.loads((cls.out / "metrics.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_row_audit_and_data07(self):
        rows = self.metrics["osm_rows"]
        self.assertEqual(rows["total"], 1631)
        self.assertEqual(sum(rows["status"].values()), 1631)
        self.assertEqual(rows["eligible"], 773)
        self.assertTrue(rows["data07_subset_of_eligible"])
        self.assertEqual(rows["eligible_edge_found_in_gazetteer_table"], 773)
        self.assertEqual(rows["eligible_relation_rows"], {"B": 312, "M": 461})

    def test_e2_has_no_multi_target_unit(self):
        e2 = self.metrics["e2"]
        self.assertEqual(e2["eligible_old_units"], 50)
        self.assertEqual(e2["units_with_ge2_valid_targets"], 0)
        self.assertEqual(e2["raw_multi_target_units"], 21)
        self.assertEqual(sum(e2["raw_multi_target_causes"].values()), 21)
        self.assertNotIn("REAL_MULTI_VALID_TARGET", e2["raw_multi_target_causes"])
        self.assertEqual(e2["gazetteer_old_units_with_fan_out_ge2"], 471)

    def test_t2_a_c_support(self):
        self.assertEqual((self.metrics["t2_a"]["edges"], self.metrics["t2_c"]["edges"]), (3, 132))
        self.assertEqual(self.metrics["t2_a"]["observed_eligible_rows"], 0)
        self.assertEqual(self.metrics["t2_c"]["observed_eligible_rows"], 0)
        self.assertEqual(self.metrics["verdict"], {
            "E2": "NEEDS_NEW_SOURCE", "T2_A": "NOT_FEASIBLE", "T2_C": "NEEDS_NEW_SOURCE",
            "T2_C_NAME_CHANGED": "NOT_FEASIBLE"})

    def test_reproduction_reports_known_mismatch(self):
        rows = {r["Item"]: r for r in read_rows(self.out / "reproduction_check.csv")}
        self.assertEqual(rows["raw_old_units"]["Status"], "MATCH")
        self.assertEqual(rows["raw_multi_units_also_ge2_in_gazetteer_units"]["Status"], "MISMATCH")
        self.assertEqual(rows["raw_multi_units_also_ge2_in_gazetteer_units"]["Observed"], "1")

    def test_label_verdicts_follow_rights(self):
        verdicts = {r["Label"]: r for r in read_rows(self.out / "label_verdicts.csv")}
        self.assertEqual(verdicts["GhiChu"]["Status"], "RIGHTS_OK_SUPPORT_UNMEASURED")
        self.assertEqual(verdicts["GhiChu"]["Support"], "NOT_MEASURED")
        for label in ("MocDinhVi", "HuongDi", "ToaNha/CanHo", "Lai_human_written"):
            self.assertEqual(verdicts[label]["Status"], "NEEDS_NEW_SOURCE", label)

    def test_csv_shape_and_no_duplicates(self):
        audit = read_rows(self.out / "osm_row_audit.csv")
        self.assertEqual(len(audit), 1631)
        self.assertEqual(len({r["ID_Node"] for r in audit}), 1631)
        with (self.out / "osm_row_audit.csv").open("rb") as stream:
            self.assertEqual(stream.read(3), b"\xef\xbb\xbf")  # utf-8-sig

    def test_e2_blocker_does_not_overclaim(self):
        row = next(r for r in read_rows(self.out / "conclusions.csv") if r["Item"] == "E2")
        self.assertNotIn("came from key artefacts", row["Blocker"])
        self.assertIn("15/21", row["Blocker"])
        self.assertIn("298", row["Blocker"])

    def test_manifest_declares_thresholds_and_hashes(self):
        manifest = json.loads((self.out / "run_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["thresholds"]["min_units"], 10)
        self.assertTrue(manifest["gazetteer_s3_v2_edges_equal_active_release2"])
        self.assertIn("scripts/74_audit_data_feasibility.py", manifest["source_sha256"])

    @unittest.skipUnless(RUN_V3.exists(), "v3 output not present")
    def test_reproduces_committed_v3_tables(self):
        for name in ("metrics.json", "conclusions.csv", "osm_row_audit.csv", "e2_unit_audit.csv", "t2_ac_edges.csv", "label_verdicts.csv"):
            self.assertEqual((self.out / name).read_bytes(), (RUN_V3 / name).read_bytes(), name)


if __name__ == "__main__":
    unittest.main()
