"""WP5 constraint ablation: re-decoding gate, change classification, ORACLE isolation, no-inference import path."""

import csv
import json
import subprocess
import sys
import unittest
from pathlib import Path

from src.evaluation import constraint_ablation as ca
from src.evaluation.span_features import BIO_LABELS, tokenize
from src.modeling.structural_decoder import viterbi_reference

ROOT = Path(__file__).resolve().parents[1]
RUN_NAME = "constraint_ablation_20261017_v1"
PARAMS_DIR = ROOT / "data/interim/modeling/sprint04" / RUN_NAME / "crf_params"
PROCESSED = ROOT / "data/processed/evaluation/sprint04" / RUN_NAME
ID = {tag: i for i, tag in enumerate(BIO_LABELS)}


def zero_params():
    n = len(BIO_LABELS)
    return {"start": [0.0] * n, "end": [0.0] * n, "transitions": [[0.0] * n for _ in range(n)]}


def toy_emissions():
    """Token 0 is a house number; token 1 prefers QuanHuyen (5) over PhuongXa (4); token 2 is the street."""
    n = len(BIO_LABELS)
    rows = [[0.0] * n for _ in range(3)]
    rows[0][ID["B-SoNha"]] = 10.0
    rows[1][ID["B-QuanHuyen"]], rows[1][ID["B-PhuongXa"]] = 5.0, 4.0
    rows[2][ID["B-TenDuong"]] = 3.0
    return rows


def toy_row(structure_ban=True):
    params, emissions = zero_params(), toy_emissions()
    text = "12 Lê Lợi"
    free, _ = ca.viterbi_with_ties(emissions, params)
    banned, _ = ca.viterbi_with_ties(emissions, params, ca.QUAN_HUYEN_IDS)
    row = {"sample_id": "toy", "raw_text": text, "status": "ok", "abstain": False, "predicted_system": "moi",
           "has_emissions": True, "units": [{"text": t.text, "start": t.start, "end": t.end} for t in tokenize(text)],
           "emissions": emissions, "path_before": free, "path_after": banned if structure_ban else free,
           "structure": {"predicted_system": "moi" if structure_ban else "cu", "ban_district": structure_ban}}
    row["stored_spans"] = [s.to_dict() for s in ca.spans_from_path(row, row["path_after"])]
    return row, params


class ToyDecodeTest(unittest.TestCase):
    def test_ban_moves_quan_huyen_to_phuong_xa(self):
        free, _ = ca.viterbi_with_ties(toy_emissions(), zero_params())
        banned, _ = ca.viterbi_with_ties(toy_emissions(), zero_params(), ca.QUAN_HUYEN_IDS)
        self.assertEqual([BIO_LABELS[i] for i in free], ["B-SoNha", "B-QuanHuyen", "B-TenDuong"])
        self.assertEqual([BIO_LABELS[i] for i in banned], ["B-SoNha", "B-PhuongXa", "B-TenDuong"])

    def test_empty_forbidden_set_equals_no_ban_and_matches_reference(self):
        p, e = zero_params(), toy_emissions()
        ours, _ = ca.viterbi_with_ties(e, p, [])
        none, _ = ca.viterbi_with_ties(e, p, None)
        ref, _ = viterbi_reference(e, p["transitions"], p["start"], p["end"], [])
        ref_none, _ = viterbi_reference(e, p["transitions"], p["start"], p["end"], None)
        self.assertEqual(ours, none)
        self.assertEqual(ours, ref)
        self.assertEqual(ref, ref_none)
        ban_ours, _ = ca.viterbi_with_ties(e, p, ca.QUAN_HUYEN_IDS)
        ban_ref, _ = viterbi_reference(e, p["transitions"], p["start"], p["end"], ca.QUAN_HUYEN_IDS)
        self.assertEqual(ban_ours, ban_ref)

    def test_exact_tie_is_counted_and_lowest_index_wins(self):
        e = toy_emissions()
        e[1][ID["B-PhuongXa"]] = e[1][ID["B-QuanHuyen"]]
        path, ties = ca.viterbi_with_ties(e, zero_params())
        ref, _ = viterbi_reference(e, zero_params()["transitions"], zero_params()["start"], zero_params()["end"], [])
        self.assertGreater(ties, 0)
        self.assertEqual(path, ref)
        self.assertEqual(BIO_LABELS[path[1]], "B-PhuongXa")  # lower tag index than B-QuanHuyen

    def test_gate_passes_on_consistent_row_and_fails_on_tampered_row(self):
        row, params = toy_row(structure_ban=True)
        ca.redecode_rows([row], params)
        self.assertEqual(ca.gate_rows([row], "toy", constrained_reference=True)["status"], "PASS")
        row["path_after"] = list(row["path_before"])  # claims the ban did nothing although it fired
        ca.redecode_rows([row], params)
        gate = ca.gate_rows([row], "toy", constrained_reference=True)
        self.assertEqual(gate["status"], "FAIL")
        self.assertEqual(gate["ban_vs_after_mismatch"], 1)

    def test_off_file_without_constraint_passes(self):
        row, params = toy_row(structure_ban=False)
        ca.redecode_rows([row], params)
        self.assertEqual(ca.gate_rows([row], "toy-off", constrained_reference=False)["status"], "PASS")

    def test_spans_for_ban_changes_span_label(self):
        row, params = toy_row()
        ca.redecode_rows([row], params)
        labels_free = [s.label for s in ca.spans_for(row, False)]
        labels_ban = [s.label for s in ca.spans_for(row, True)]
        self.assertIn("QuanHuyen", labels_free)
        self.assertNotIn("QuanHuyen", labels_ban)
        self.assertTrue(ca.row_changed(row, True))
        self.assertFalse(ca.row_changed(row, False))


class ClassificationTest(unittest.TestCase):
    def test_correct_fix_harm_neutral(self):
        self.assertEqual(ca.classify_change((4, 1, 0), (5, 0, 0)), "correct_fix")   # spurious QuanHuyen removed
        self.assertEqual(ca.classify_change((5, 0, 0), (3, 1, 2)), "harm")          # gold QuanHuyen lost
        self.assertEqual(ca.classify_change((4, 1, 1), (4, 1, 1)), "neutral")
        self.assertEqual(ca.classify_change((4, 1, 1), (3, 2, 2)), "harm")
        self.assertEqual(ca.tally(["harm", "neutral", "harm"]), {"correct_fix": 0, "harm": 2, "neutral": 1})

    def test_micro_f1_and_sample_std(self):
        self.assertAlmostEqual(ca.micro_f1([(3, 1, 1), (1, 0, 1)]), 2 * 4 / (2 * 4 + 1 + 2))
        self.assertIsNone(ca.sample_std([0.5]))
        self.assertAlmostEqual(ca.sample_std([1.0, 3.0]), 2 ** 0.5)


class OracleIsolationTest(unittest.TestCase):
    def test_model_comparison_row_refuses_oracle(self):
        counts, exact = [(1, 0, 0), (1, 1, 0)], [True, False]
        self.assertEqual(ca.model_comparison_row("PHOBERT-CRF", False, False, "none", counts, exact)["n_rows"], 2)
        with self.assertRaises(ValueError):
            ca.model_comparison_row("X", False, True, "ORACLE_UPPER_BOUND", counts, exact)
        with self.assertRaises(ValueError):
            ca.model_comparison_row("DYN + ORACLE", True, True, "gold", counts, exact)

    def test_oracle_flags_follow_gold_only(self):
        import numpy as np
        arrays = {"gold_moi": np.array([True, False, True])}
        self.assertEqual(ca.oracle_flags(arrays).tolist(), [True, False, True])

    def test_published_comparison_table_has_no_oracle(self):
        path = PROCESSED / "tables/model_comparison_2x2.csv"
        if not path.exists():
            self.skipTest("constraint ablation output not produced")
        self.assertNotIn("ORACLE", path.read_text(encoding="utf-8-sig").upper())
        oracle = PROCESSED / "tables/oracle_upper_bound.csv"
        with oracle.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertTrue(rows)
        self.assertTrue(all(r["label"] == "ORACLE_UPPER_BOUND" for r in rows))
        ablation = (PROCESSED / "tables/t1_source_ablation.csv").read_text(encoding="utf-8-sig").upper()
        self.assertNotIn("ORACLE", ablation)


class NoInferencePathTest(unittest.TestCase):
    def test_module_imports_neither_torch_nor_adapter(self):
        code = ("import sys; sys.path.insert(0, %r); import src.evaluation.constraint_ablation as m; "
                "bad = [k for k in sys.modules if k == 'torch' or 'adapters' in k or k.startswith('transformers')]; "
                "print(bad); sys.exit(1 if bad else 0)") % str(ROOT)
        done = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_sources_never_build_adapter_or_run_model(self):
        for name in ("src/evaluation/constraint_ablation.py", "scripts/72_run_constraint_ablation.py"):
            text = (ROOT / name).read_text(encoding="utf-8")
            for forbidden in ("build_adapter", "PhoBERTCRFAdapter", "parse_spans(", "from_pretrained", "load_checkpoint(", ".forward("):
                self.assertNotIn(forbidden, text, f"{name} must not contain {forbidden}")

    def test_constants_match_frozen_reliability(self):
        from src.evaluation import frozen_reliability as fr
        self.assertEqual((ca.SEED, ca.N_RESAMPLES), (fr.SEED, fr.N_RESAMPLES))


def _real_inputs_available():
    needed = [PARAMS_DIR / "kaggle_dyn.json", ROOT / ca.KAGGLE_REL / "dyn_test/predictions.jsonl",
              ROOT / ca.KAGGLE_REL / "dyn_off_test/predictions.jsonl", ROOT / ca.KAGGLE_REL / "pcrf_test/predictions.jsonl"]
    return all(p.exists() for p in needed)


@unittest.skipUnless(_real_inputs_available(), "interim CRF parameters / frozen predictions not available")
class RealKaggleTestSetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.params = json.loads((PARAMS_DIR / "kaggle_dyn.json").read_text(encoding="utf-8"))
        cls.on = ca.load_rows(ROOT / ca.KAGGLE_REL / "dyn_test/predictions.jsonl")
        cls.off = ca.load_rows(ROOT / ca.KAGGLE_REL / "dyn_off_test/predictions.jsonl")
        ca.redecode_rows(cls.on, cls.params)
        ca.redecode_rows(cls.off, cls.params)

    def test_gate_reproduces_before_and_after_paths_on_all_rows(self):
        on = ca.gate_rows(self.on, "on", constrained_reference=True)
        off = ca.gate_rows(self.off, "off", constrained_reference=False)
        self.assertEqual((on["status"], on["n_decodable"], on["free_vs_before_mismatch"], on["ban_vs_after_mismatch"]), ("PASS", 100, 0, 0))
        self.assertEqual(on["ban_rows"], 20)
        self.assertEqual((off["status"], off["free_vs_before_mismatch"]), ("PASS", 0))
        self.assertEqual(on["reference_disagree"] + off["reference_disagree"], 0)

    def test_headroom_is_zero_of_twelve(self):
        from src.evaluation import frozen_reliability as fr
        golds, excluded = fr.load_gold("test")
        arrays = ca.span_arrays(self.off, golds, excluded)
        flags = ca.dyn_flags_from_rows(self.off, arrays["sample_ids"])
        headroom = ca.analyze_headroom(arrays, flags)
        self.assertEqual((headroom["n_gold_moi_without_quan_huyen"], headroom["n_headroom"]), (25, 0))
        self.assertEqual((headroom["n_gold_moi_t1_eligible"], headroom["n_headroom_t1_eligible"]), (12, 0))
        # the single changed row is the known QuanHuyen -> PhuongXa harm
        source = ca.analyze_source(arrays, flags, "DYN", with_ci=False)
        self.assertEqual((source["n_changed_rows"], source["n_span_changes"], source["harm"]), (1, 2, 1))
        self.assertEqual(source["changed_sample_ids"], ["s3_224ae519b196f730"])
        self.assertEqual(round(source["f1_no_constraint"], 4), 0.9843)
        self.assertEqual(round(source["f1_with_ban"], 4), 0.9821)


if __name__ == "__main__":
    unittest.main()
