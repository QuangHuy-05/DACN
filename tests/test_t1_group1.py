"""Regression tests for WP2: T1 sets, T1-PIPE rule, situation tags, DYN diagnostics."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

from src.evaluation import t1_pipeline as P
from src.evaluation import t1_situations as S
from src.evaluation import t2_lookup as L
from src.evaluation.leak_guard import load_corpus_records, normalize_for_overlap

ROOT = Path(__file__).resolve().parents[1]
SETS_DIR = ROOT / "data/interim/modeling/sprint04/t1_sets_20261015_v1"
CORPUS_DIR = ROOT / "data/processed/annotation/sprint03/corpus_v1_release2"
DATA06 = ROOT / "data/processed/benchmark/06_hybrid_addresses_600.csv"
HEUR_CONFIG = ROOT / P.LOCKED_HEUR_CONFIG
DYN_TEST_PREDICTIONS = ROOT / ("data/interim/modeling/sprint03/final_completion_20261005_v1/kaggle_final_output_v4/"
                               "dacn_artifacts/dacn-s3-final-infer-20261005-v4/workspace/data/interim/modeling/"
                               "sprint03/dacn-s3-final-infer-20261005-v4/dyn_test/predictions.jsonl")
HAS_SETS = (SETS_DIR / "run_manifest.json").exists() and CORPUS_DIR.exists() and DATA06.exists()


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name.replace(".py", "").replace("/", "_"), ROOT / "scripts" / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILD = load_script("67_build_t1_sets.py")
EVAL = load_script("68_run_t1_evaluation.py")


def read_set(name: str) -> pd.DataFrame:
    return pd.read_csv(SETS_DIR / f"{name}.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")


class FakeEntity:
    def __init__(self, level, system, name):
        self.level, self.system, self.canonical_name = level, system, name


class FakeResolver:
    """Stands in for HEUR-JW: surface -> candidate entities (level, system)."""

    def __init__(self, table):
        self.table = table
        self.seen_context = []

    @staticmethod
    def _core(value):
        return value.casefold()

    def _resolve(self, value, context):
        self.seen_context.append((value, {k: sorted(v) for k, v in context.items()}))
        candidates = [FakeEntity(level, system, value) for level, system in self.table.get(value, [])]
        return candidates, {"decision": "ACCEPT" if candidates else "REJECT"}


def spans_for(text: str, parts: dict[str, str]) -> list[dict]:
    return [{"start": text.index(surface), "end": text.index(surface) + len(surface), "label": label}
            for label, surface in parts.items()]


class PipeRuleTests(unittest.TestCase):
    TEXT = "12, Đường A, Phường X, Quận Y, Tỉnh Z"
    PARTS = {"TenDuong": "Đường A", "PhuongXa": "Phường X", "QuanHuyen": "Quận Y", "TinhThanh": "Tỉnh Z"}

    def predict(self, table):
        resolver = FakeResolver(table)
        system, detail = P.pipe_predict(resolver, self.TEXT, spans_for(self.TEXT, self.PARTS))
        return system, detail, resolver

    def test_old_and_new_spans_give_lai(self):
        system, _, _ = self.predict({"Phường X": [("ward", "moi")], "Quận Y": [("district", "cu")]})
        self.assertEqual(system, "Lai")

    def test_single_system_branches(self):
        self.assertEqual(self.predict({"Phường X": [("ward", "cu")], "Quận Y": [("district", "cu")]})[0], "cu")
        self.assertEqual(self.predict({"Phường X": [("ward", "moi")]})[0], "moi")

    def test_undetermined_gives_khong_ro(self):
        # A name valid in both systems does not determine the system; nothing else resolves.
        table = {"Tỉnh Z": [("province", "cu"), ("province", "moi")]}
        system, detail, _ = self.predict(table)
        self.assertEqual(system, P.ABSTAIN)
        self.assertEqual({d["system"] for d in detail}, {P.UNKNOWN_SPAN_SYSTEM})
        self.assertEqual(self.predict({})[0], P.ABSTAIN)

    def test_only_admin_spans_are_resolved_right_to_left_with_context(self):
        _, detail, resolver = self.predict({"Tỉnh Z": [("province", "cu")], "Quận Y": [("district", "cu")]})
        self.assertEqual([value for value, _ in resolver.seen_context], ["Tỉnh Z", "Quận Y", "Phường X"])
        self.assertEqual(resolver.seen_context[2][1], {"province": ["tỉnh z"], "district": ["quận y"]})
        self.assertEqual(len(detail), 3)  # the street span is never looked up

    def test_combine_systems_four_branches(self):
        self.assertEqual(P.combine_systems(["cu", "moi", "khong_xac_dinh"]), "Lai")
        self.assertEqual(P.combine_systems(["cu", "cu"]), "cu")
        self.assertEqual(P.combine_systems(["moi", "khong_xac_dinh"]), "moi")
        self.assertEqual(P.combine_systems(["khong_xac_dinh"]), P.ABSTAIN)
        self.assertEqual(P.combine_systems([]), P.ABSTAIN)


class InferenceContractTests(unittest.TestCase):
    def test_inference_refuses_gold_and_metadata_columns(self):
        frame = pd.DataFrame({"key": ["a"], "text": ["1, Đường A, Phường X"]})
        self.assertEqual(P.inference_texts(frame), ["1, Đường A, Phường X"])
        self.assertEqual(P.inference_texts(frame[["text"]]), ["1, Đường A, Phường X"])
        for column in ("gold_system", "KieuLai", "source", "admin_group_key"):
            with self.assertRaises(ValueError):
                P.inference_texts(frame.assign(**{column: "x"}))

    def test_prediction_functions_take_text_only(self):
        resolver = FakeResolver({"Phường X": [("ward", "moi")]})
        text = P.inference_texts(pd.DataFrame({"text": ["Phường X"]}))[0]
        self.assertEqual(P.pipe_predict(resolver, text, [{"start": 0, "end": 8, "label": "PhuongXa"}])[0], "moi")

    @unittest.skipUnless(HEUR_CONFIG.exists(), "locked HEUR-JW config missing")
    def test_every_cpu_system_runs_on_a_text_only_frame(self):
        frame = pd.DataFrame({"text": ["12, Đường Lý Thường Kiệt, Phường Phù Khê, Tỉnh Bắc Ninh",
                                       "5, Phố Huế, Phường Phố Huế, Quận Hai Bà Trưng, Hà Nội"]})
        heur = P.load_locked_heur(ROOT)
        extractor = P.FeatureExtractor(heur)
        for text in P.inference_texts(frame):
            self.assertIn(P.heur_predict(heur, text), (*P.CLASSES, P.ABSTAIN))
            spans = [{"start": s.start, "end": s.end, "label": s.label} for s in heur.parse_spans(text).spans]
            # The reused rule on HEUR-JW's own spans gives HEUR-JW's own T1.
            self.assertEqual(P.pipe_predict(heur, text, spans)[0], P.heur_predict(heur, text))
            features = extractor.features(text)
            self.assertTrue(any(name.startswith(P.GAZETTEER_PREFIX) for name in features))
            self.assertFalse(any(name.startswith(P.GAZETTEER_PREFIX) for name in extractor.features(text, False)))
            self.assertIsInstance(extractor.has_district_sign(text), bool)
        self.assertFalse(extractor.has_district_sign(frame["text"][0]))
        self.assertTrue(extractor.has_district_sign(frame["text"][1]))


class ClassifierAndMetricTests(unittest.TestCase):
    def test_softmax_is_deterministic_and_separates_simple_data(self):
        x = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]] * 20, dtype=float)
        y = [0, 1, 2] * 20
        first = P.SoftmaxClassifier(0.1).fit(x, y)
        second = P.SoftmaxClassifier(0.1).fit(x, y)
        np.testing.assert_array_equal(first.weights, second.weights)
        self.assertEqual(first.predict(np.eye(3)).tolist(), [0, 1, 2])
        model, l2, trials = P.select_l2(x, y, x, y)
        self.assertEqual(l2, max(P.L2_GRID))  # ties are broken towards the larger L2
        self.assertEqual(len(trials), len(P.L2_GRID))

    def test_metrics_count_abstention_as_wrong(self):
        gold = ["cu", "cu", "moi", "Lai", "Lai"]
        predicted = ["cu", P.ABSTAIN, "moi", "cu", "Lai"]
        metrics = P.t1_metrics(gold, predicted)
        self.assertEqual((metrics["n"], metrics["correct"], metrics["abstain_count"]), (5, 3, 1))
        self.assertAlmostEqual(metrics["accuracy"], 0.6)
        self.assertEqual(metrics["per_class"]["Lai"], {"support": 2, "predicted": 1, "tp": 1, "precision": 1.0,
                                                       "recall": 0.5, "f1": 2 / 3})
        # cu: tp 1, fp 1, fn 1 -> 0.5; moi: 1.0; Lai: 2/3
        self.assertAlmostEqual(metrics["macro_f1"], (0.5 + 1.0 + 2 / 3) / 3)
        units = P.to_units(gold, predicted)
        grouped = P.aggregate_by_cluster(units, ["a", "a", "b", "b", "c"])
        self.assertEqual(grouped.shape, (3, 3, 4))
        self.assertAlmostEqual(P.macro_f1_stat(grouped), metrics["macro_f1"])
        self.assertAlmostEqual(P.accuracy_stat(grouped), 0.6)
        self.assertAlmostEqual(P.class_recall_stat("Lai")(units), 0.5)

    def test_single_class_set_has_no_macro_f1(self):
        metrics = P.t1_metrics(["Lai", "Lai"], ["Lai", "cu"])
        self.assertEqual(metrics["macro_f1"], P.NOT_EVALUABLE_SINGLE_CLASS)
        self.assertEqual(metrics["per_class"]["cu"]["recall"], None)
        self.assertTrue(np.isnan(P.class_f1_stat("cu")(P.to_units(["Lai"], ["Lai"]))))


def tagger_fixture() -> S.SituationTagger:
    def edge(old_id, new_id, old_ward, new_ward, row):
        return L.make_edge(old_id, new_id, "Tỉnh Cũ", "Quận X", old_ward, "Tỉnh Mới", new_ward, new_id, "?",
                           "Hợp nhất toàn bộ", row)

    table = L.T2Table([
        edge("o1", "n1", "Phường 1", "Phường N1", 1),      # 1-1
        edge("o2", "n2", "Phường 2", "Phường N2", 2),      # N-1 into N2
        edge("o3", "n2", "Phường 3", "Phường N2", 3),
        edge("o4", "n3", "Phường 4", "Phường N3", 4),      # 1-N from Phường 4
        edge("o4", "n4", "Phường 4", "Phường N4", 5),
        edge("o5", "n5", "Phường A", "Phường B", 6),       # old "Phường A" -> new "Phường B"
        edge("o6", "n6", "Phường C", "Phường A", 7),       # a different new "Phường A"
    ])
    entities = [
        {"entity_id": "P_old", "level": "province", "system": "cu", "canonical_name": "Tỉnh Cũ", "parent_id": ""},
        {"entity_id": "D_old", "level": "district", "system": "cu", "canonical_name": "Quận X", "parent_id": "P_old"},
        {"entity_id": "P_new", "level": "province", "system": "moi", "canonical_name": "Tỉnh Mới", "parent_id": ""},
    ]
    for old_id, name in (("o1", "Phường 1"), ("o2", "Phường 2"), ("o3", "Phường 3"), ("o4", "Phường 4"),
                         ("o5", "Phường A"), ("o6", "Phường C")):
        entities.append({"entity_id": old_id, "level": "ward", "system": "cu", "canonical_name": name,
                         "parent_id": "D_old"})
    for new_id, name in (("n1", "Phường N1"), ("n2", "Phường N2"), ("n3", "Phường N3"), ("n4", "Phường N4"),
                         ("n5", "Phường B"), ("n6", "Phường A")):
        entities.append({"entity_id": new_id, "level": "ward", "system": "moi", "canonical_name": name,
                         "parent_id": "P_new"})
    return S.SituationTagger(table, L.SingleVersionIndex(entities, table))


class SituationTagTests(unittest.TestCase):
    def test_tags_are_deterministic_and_follow_the_definition(self):
        tagger = tagger_fixture()
        cases = [
            (("cu", "Tỉnh Cũ", "Quận X", "Phường 4"), ("A",)),          # old unit with two targets
            (("cu", "Tỉnh Cũ", "Quận X", "Phường 1"), ("NONE",)),       # one target
            (("moi", "Tỉnh Mới", "", "Phường N2"), ("B",)),             # merged from two old units
            (("moi", "Tỉnh Mới", "", "Phường N1"), ("NONE",)),
            (("Lai", "Tỉnh Cũ", "Quận X", "Phường N1"), ("C",)),
            (("cu", "Tỉnh Cũ", "Quận X", "Phường A"), ("D",)),          # name exists in both systems
            (("Lai", "Tỉnh Mới", "Quận X", "Phường A"), ("C", "D")),
            ((None, "Tỉnh Cũ", "", ""), ("NONE",)),
        ]
        for arguments, expected in cases:
            self.assertEqual(tagger.tags(*arguments), expected, arguments)
            self.assertEqual(tagger.tags(*arguments), tagger.tags(*arguments))
        self.assertEqual(S.format_tags(("C", "D")), "C|D")

    def test_a_and_b_need_the_matching_system(self):
        tagger = tagger_fixture()
        self.assertNotIn("A", tagger.tags("moi", "Tỉnh Cũ", "Quận X", "Phường 4"))
        self.assertNotIn("B", tagger.tags("cu", "Tỉnh Mới", "", "Phường N2"))


class DynDiagnosisTests(unittest.TestCase):
    @staticmethod
    def prediction(sample_id, posterior, predicted, abstain):
        confidence = max(posterior.values())
        runner_up = sorted(posterior.values())[-2]
        return {"sample_id": sample_id, "predicted_system": predicted, "trace": {"structure": {
            "posterior": posterior, "confidence": confidence, "margin_observed": confidence - runner_up,
            "threshold": 0.7, "margin_required": 0.2, "predicted_system": predicted, "t1_abstain": abstain}}}

    def test_reads_posterior_and_threshold_from_a_prediction_row(self):
        row = self.prediction("s1", {"cu": 0.55, "moi": 0.05, "Lai": 0.40}, "khong_ro", True)
        info = P.read_structure(row)
        self.assertEqual(info["argmax"], "cu")
        self.assertAlmostEqual(info["posterior"]["Lai"], 0.40)
        self.assertEqual((info["threshold"], info["margin_required"]), (0.7, 0.2))
        self.assertFalse(info["passes_threshold"])
        self.assertFalse(info["passes_margin"])
        with self.assertRaises(ValueError):
            P.read_structure({"sample_id": "s2", "trace": {}})

    def test_separates_head_failure_from_threshold_rejection(self):
        gold = [{"sample_id": "a", "address_system": "Lai"}, {"sample_id": "b", "address_system": "Lai"},
                {"sample_id": "c", "address_system": "cu"}, {"sample_id": "d", "address_system": None},
                {"sample_id": "e", "address_system": "moi"}]
        predictions = [
            self.prediction("a", {"cu": 0.80, "moi": 0.05, "Lai": 0.15}, "cu", False),       # head ranks cu first
            self.prediction("b", {"cu": 0.35, "moi": 0.05, "Lai": 0.60}, "khong_ro", True),  # rejected by threshold
            self.prediction("c", {"cu": 0.90, "moi": 0.05, "Lai": 0.05}, "cu", False),
            self.prediction("d", {"cu": 0.90, "moi": 0.05, "Lai": 0.05}, "cu", False),
            self.prediction("e", {"cu": 0.05, "moi": 0.90, "Lai": 0.05}, "moi", False),
        ]
        result = P.diagnose_dyn(gold, predictions, ["e"])
        self.assertEqual(result["mask"], {"eligible": 3, "null": 1, "excluded": 1})
        self.assertEqual(result["lai"]["support"], 2)
        self.assertEqual(result["lai"]["argmax_is_lai"], 1)
        self.assertEqual(result["lai"]["argmax_is_lai_but_rejected"], 1)
        self.assertEqual(result["lai"]["argmax_other_class"], {"cu": 1})
        self.assertEqual(result["with_threshold"]["per_class"]["Lai"]["tp"], 0)
        self.assertEqual(result["argmax_only"]["per_class"]["Lai"]["tp"], 1)
        self.assertEqual(result["observed_threshold_margin"], {"0.7/0.2": 5})


class SplitLogicTests(unittest.TestCase):
    def pool(self) -> pd.DataFrame:
        rows = []
        for province in ("Tỉnh A", "Tỉnh B"):
            for group in range(30):
                for member in range(2):
                    rows.append({"key": f"{province}-{group}-{member}", "province_new": province,
                                 "admin_group_key": f"ADM|{province}|{group}", "unresolved_group": False})
        rows.append({"key": "u", "province_new": "Tỉnh A", "admin_group_key": "UNRESOLVED|x", "unresolved_group": True})
        return pd.DataFrame(rows)

    def test_group_split_is_deterministic_and_stratified(self):
        pool = self.pool()
        first, second = BUILD.assign_groups(pool, 7), BUILD.assign_groups(pool, 7)
        self.assertEqual(first, second)
        self.assertNotEqual(first, BUILD.assign_groups(pool, 8))
        self.assertNotIn("UNRESOLVED|x", first)  # unresolved groups are never split
        self.assertEqual(set(first.values()), {"train", "dev", "eval"})
        for province in ("Tỉnh A", "Tỉnh B"):
            parts = [part for group, part in first.items() if f"|{province}|" in group]
            self.assertEqual(len(parts), 30)
            self.assertIn(parts.count("train"), (17, 18, 19))  # about 60% of the groups of each province
            self.assertIn(parts.count("dev"), (5, 6, 7))

    def test_bare_ward_and_province_pair(self):
        self.assertEqual(BUILD.bare_ward("Phường Ba Đình"), "ba đình")
        self.assertEqual(BUILD.bare_ward("P. Ba Đình"), "ba đình")
        self.assertEqual(BUILD.bare_ward("Thị trấn Chờ"), "chờ")
        self.assertEqual(BUILD.bare_ward("Ba Đình"), "ba đình")


@unittest.skipUnless(HAS_SETS, "t1_sets_20261015_v1 or Sprint 3 corpus missing")
class BuiltSetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts = {name: read_set(f"t1_synth_{name}") for name in ("train", "dev", "eval")}
        cls.heldout = read_set("t1_data06_heldout")
        cls.records, _ = load_corpus_records(CORPUS_DIR)
        cls.manifest = json.loads((SETS_DIR / "run_manifest.json").read_text(encoding="utf-8"))

    def test_parts_are_group_disjoint_and_train_dev_are_resolved(self):
        groups = {name: set(frame["admin_group_key"]) for name, frame in self.parts.items()}
        self.assertFalse(groups["train"] & groups["dev"])
        self.assertFalse(groups["train"] & groups["eval"])
        self.assertFalse(groups["dev"] & groups["eval"])
        for name in ("train", "dev"):
            self.assertFalse(self.parts[name]["admin_group_key"].str.startswith("UNRESOLVED|").any())
            self.assertTrue((self.parts[name]["unresolved_group"] == "False").all())

    def test_no_sprint3_or_data06_string_in_train_or_dev(self):
        blocked = {normalize_for_overlap(row["text"]) for rows in self.records.values() for row in rows}
        data06 = pd.read_csv(DATA06, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        blocked |= {normalize_for_overlap(text) for text in data06["ChuoiDiaChi"]}
        for name in ("train", "dev", "eval"):  # eval must be clean of the corpus and Data 06 as well
            normalized = set(self.parts[name]["text"].map(normalize_for_overlap))
            self.assertFalse(normalized & blocked, name)

    def test_no_dev_test_province_ward_pair_in_train_or_dev(self):
        mapping = BUILD.load_administrative_mapping(BUILD.default_mapping_path())
        holdout = BUILD.sprint3_holdout(self.records, mapping)
        self.assertTrue(holdout["pairs"])
        for name in ("train", "dev"):
            frame = self.parts[name]
            pairs = {(BUILD.province_pair_key(mapping, p), BUILD.bare_ward(w))
                     for p, w in zip(frame["gold_province"], frame["gold_ward"])}
            self.assertFalse(pairs & holdout["pairs"], name)
            self.assertFalse(set(frame["admin_group_key"]) & holdout["groups"], name)

    def test_train_is_balanced_without_duplication(self):
        counts = self.parts["train"]["gold_system"].value_counts()
        self.assertEqual(set(counts.index), set(P.CLASSES))
        self.assertEqual(counts.nunique(), 1)
        for frame in (*self.parts.values(), self.heldout):
            self.assertFalse(frame["text"].duplicated().any())
            self.assertFalse(frame["key"].duplicated().any())

    def test_data06_heldout_facts(self):
        self.assertEqual(len(self.heldout), 580)
        self.assertEqual(set(self.heldout["gold_system"]), {"Lai"})
        self.assertEqual(self.heldout["KieuLai"].str[:2].value_counts().to_dict(), {"C1": 410, "C2": 115, "C3": 55})
        train_groups = set(self.parts["train"]["admin_group_key"])
        seen = self.heldout["admin_group_key"].isin(train_groups)
        self.assertEqual((self.heldout["group_seen_in_synth_train"] == "True").tolist(), seen.tolist())
        self.assertEqual(self.manifest["reproduction"]["mismatches"], {})

    def test_sprint3_test_mask_is_64_20_16(self):
        manifest = json.loads((CORPUS_DIR / "manifest.json").read_text(encoding="utf-8"))
        mask = P.t1_mask(self.records["test"], manifest["test_evaluation_exclusions"]["t1"])
        self.assertEqual({name: len(ids) for name, ids in mask.items()}, {"eligible": 64, "null": 20, "excluded": 16})

    @unittest.skipUnless(DYN_TEST_PREDICTIONS.exists(), "frozen DYN test predictions missing")
    def test_frozen_dyn_diagnosis_reproduces_sprint3_t1(self):
        manifest = json.loads((CORPUS_DIR / "manifest.json").read_text(encoding="utf-8"))
        result = P.diagnose_dyn(self.records["test"], P.read_jsonl(DYN_TEST_PREDICTIONS),
                                manifest["test_evaluation_exclusions"]["t1"])
        self.assertEqual(round(result["with_threshold"]["accuracy"], 4), 0.7188)
        self.assertEqual(round(result["with_threshold"]["macro_f1"], 4), 0.5626)
        self.assertEqual(result["lai"]["support"], 5)
        self.assertEqual(result["observed_threshold_margin"], {"0.7/0.2": 100})


class RunScriptContractTests(unittest.TestCase):
    def test_h5_rows_and_columns_are_declared(self):
        for system in ("HEUR-JW", "PROPOSED-DYN", "T1-PIPE-CRF", "T1-PIPE-PCRF", "T1-PIPE-DYN", "T1-FEAT",
                       "T1-FEAT-NOGAZ", "T1-HEAD-PROBE", "DYN-T1-AUG", "BASELINE-MAJORITY", "BASELINE-ONE-FEATURE"):
            self.assertIn(system, EVAL.SYSTEM_ORDER)
            self.assertIn("uses_gazetteer", EVAL.SYSTEM_DEFINITIONS[system])
        self.assertFalse(EVAL.SYSTEM_DEFINITIONS[EVAL.DYN]["uses_gazetteer"])
        self.assertFalse(EVAL.SYSTEM_DEFINITIONS[EVAL.PROBE]["uses_gazetteer"])
        self.assertEqual(EVAL.COLUMN_LABELS["s3_test_eligible"], "POST_HOC_SECONDARY")
        self.assertEqual(EVAL.CI_SEED, 20261015)
        self.assertEqual(EVAL.DEFAULT_RESAMPLES, 10000)


if __name__ == "__main__":
    unittest.main()
