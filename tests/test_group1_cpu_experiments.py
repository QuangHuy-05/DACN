"""WP4 tests: perturbation offsets, determinism, leak-free augmentation sets, GT_* isolation, CRF reproduction."""

from __future__ import annotations

import importlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from src.evaluation import perturbations as pert

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data/processed/annotation/sprint03/corpus_v1_release2"
TRAIN = ROOT / "data/processed/annotation/sprint03/corpus_train_dev_v2/train.jsonl"
SCRIPT = importlib.import_module("scripts.71_run_cpu_hypothesis_experiments")

TEXT = "8, Ngõ 28 Ông Ích Khiêm, Phường Ba Đình, Thành phố Hà Nội"
SPANS = [{"start": 0, "end": 1, "label": "SoNha"}, {"start": 3, "end": 9, "label": "Ngo/Hem"},
         {"start": 10, "end": 23, "label": "TenDuong"}, {"start": 25, "end": 39, "label": "PhuongXa"},
         {"start": 41, "end": 57, "label": "TinhThanh"}]


def read_all(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def gold_rows() -> list[dict]:
    rows = read_all(TRAIN) + read_all(CORPUS / "dev.jsonl") + read_all(CORPUS / "test_benchmark_t0.jsonl")
    return rows


class PerturbationTests(unittest.TestCase):
    def test_recompose_keeps_surfaces_and_offsets(self):
        for order in ("original", "reverse"):
            text, spans, perm = pert.recompose_with_order(TEXT, SPANS, order)
            self.assertTrue(pert.verify_surfaces(TEXT, SPANS, text, spans))
            self.assertEqual(sorted(perm), list(range(len(SPANS))))
        text, _, perm = pert.recompose_with_order(TEXT, SPANS, "original")
        self.assertEqual(perm, list(range(5)))
        self.assertEqual(text, "8, Ngõ 28, Ông Ích Khiêm, Phường Ba Đình, Thành phố Hà Nội")
        reverse_text, spans, _ = pert.recompose_with_order(TEXT, SPANS, "reverse")
        self.assertTrue(reverse_text.startswith("Thành phố Hà Nội, Phường Ba Đình"))
        self.assertEqual(reverse_text[spans[0]["start"]:spans[0]["end"]], "Thành phố Hà Nội")

    def test_shuffle_is_deterministic_per_seed_and_key(self):
        a = pert.recompose_with_order(TEXT, SPANS, "shuffle", 42, "id1")
        b = pert.recompose_with_order(TEXT, SPANS, "shuffle", 42, "id1")
        c = pert.recompose_with_order(TEXT, SPANS, "shuffle", 1337, "id1")
        self.assertEqual(a, b)
        self.assertTrue(pert.verify_surfaces(TEXT, SPANS, a[0], a[1]))
        self.assertTrue(pert.verify_surfaces(TEXT, SPANS, c[0], c[1]))
        with self.assertRaises(ValueError):
            pert.recompose_with_order(TEXT, SPANS, "shuffle")

    def test_overlapping_spans_are_rejected(self):
        with self.assertRaises(ValueError):
            pert.recompose_with_order("abcdef", [{"start": 0, "end": 4, "label": "A"}, {"start": 2, "end": 6, "label": "B"}])

    def test_drop_commas_maps_offsets_reversibly(self):
        new_text, old_to_new, new_to_old = pert.drop_commas("A,  B, C ,")
        self.assertEqual(new_text, "A B C")
        self.assertEqual(old_to_new[0], 0)
        self.assertEqual(old_to_new[1], 1)      # the comma became the single separating space
        self.assertIsNone(old_to_new[2])        # the following space was collapsed
        self.assertEqual(new_to_old, [0, 1, 4, 5, 7])
        text, spans = pert.transform_sample(TEXT, SPANS, no_commas=True, lowercase=True)
        self.assertEqual(text, "8 ngõ 28 ông ích khiêm phường ba đình thành phố hà nội")
        self.assertEqual(text[spans[2]["start"]:spans[2]["end"]], "ông ích khiêm")

    def test_transforms_are_exact_on_all_400_gold_samples(self):
        rows = gold_rows()
        self.assertEqual(len(rows), 400)
        for flags in ({"no_commas": True}, {"lowercase": True}, {"no_commas": True, "lowercase": True}):
            for row in rows:
                text, spans = pert.transform_sample(row["text"], row["spans"], **flags)
                olds = sorted(row["spans"], key=lambda s: (s["start"], s["end"]))
                news = sorted(spans, key=lambda s: (s["start"], s["end"]))
                for old, new in zip(olds, news):
                    self.assertEqual(text[new["start"]:new["end"]],
                                     pert.expected_surface(row["text"][old["start"]:old["end"]], **flags))

    def test_recompose_is_exact_on_all_400_gold_samples(self):
        for row in gold_rows():
            for order, seed in (("original", None), ("reverse", None), ("shuffle", 42), ("shuffle", 1337), ("shuffle", 2025)):
                text, spans, _ = pert.recompose_with_order(row["text"], row["spans"], order, seed, row["sample_id"])
                self.assertTrue(pert.verify_surfaces(row["text"], row["spans"], text, spans))
                for span in spans:
                    self.assertTrue(text[span["start"]:span["end"]])


class HelperTests(unittest.TestCase):
    def test_lane_prefix(self):
        for value in ("Ngõ 5 Lê Lợi", "hẻm 12", "Ngách 1/88 Phạm Tuấn Tài", "Kiệt 3"):
            self.assertTrue(SCRIPT.starts_with_lane(value), value)
        self.assertFalse(SCRIPT.starts_with_lane("Đường Hoàng Quốc Việt"))

    def test_stratified_sample_is_deterministic_and_proportional(self):
        rows = [{"sample_id": f"r{i:03d}", "k": "a" if i < 60 else "b"} for i in range(100)]
        one = SCRIPT.stratified_sample(rows, lambda r: r["k"], 20, "seed")
        two = SCRIPT.stratified_sample(rows, lambda r: r["k"], 20, "seed")
        self.assertEqual(one, two)
        self.assertEqual(sum(r["k"] == "a" for r in one), 12)
        self.assertEqual(len(SCRIPT.stratified_sample(rows, lambda r: r["k"], 500, "seed")), 100)

    def test_model_side_files_never_carry_gt_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = [{"sample_id": "x", "text": "9, Hà Nội", "GT_SoNha": "SECRET", "row": {"GT_SoNha": "SECRET"},
                     "spans": [{"start": 0, "end": 1, "label": "SoNha", "system": "khong_xac_dinh", "extra": 1}]}]
            SCRIPT.write_train(Path(tmp) / "t.jsonl", rows)
            SCRIPT.write_inputs(Path(tmp) / "i.jsonl", rows)
            for name in ("t.jsonl", "i.jsonl"):
                self.assertNotIn("SECRET", (Path(tmp) / name).read_text(encoding="utf-8"))
                self.assertNotIn("GT_", (Path(tmp) / name).read_text(encoding="utf-8"))
        self.assertNotIn("GT_", inspect.getsource(SCRIPT.worker_main))

    def test_failed_alignment_is_reported_not_guessed(self):
        row = {"SoNha": "9", "TenDuong": "Lê Lợi", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "Hà Nội",
               "ChuoiDiaChi": "9, Lê Lợi, Hà Nội"}
        aligned, reason = SCRIPT.align_surface_row(row, "t")
        self.assertIsNone(reason)
        self.assertEqual([s["label"] for s in aligned["spans"]], ["SoNha", "TenDuong", "TinhThanh"])
        row["SoNha"] = "99"
        aligned, reason = SCRIPT.align_surface_row(row, "t")
        self.assertIsNone(aligned)
        self.assertIsNotNone(reason)


@unittest.skipUnless(SCRIPT.CRF_PYTHON.exists() and TRAIN.exists(), "CRF runtime or corpus missing")
class CrfReproductionTests(unittest.TestCase):
    def test_locked_crf_reproduces_hash_and_test_f1(self):
        from src.evaluation import frozen_reliability as fr
        from src.evaluation.dev_runner import load_predictions
        test_gold, excluded = fr.load_gold("test")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            SCRIPT.write_inputs(out / "in.jsonl", test_gold)
            job = {"models": [{"name": "BASE", "train_jsonl": str(TRAIN), "model_path": str(out / "m.crfsuite"),
                               "metadata_path": str(out / "m.json"),
                               "predict": [{"inputs": str(out / "in.jsonl"), "out": str(out / "pred.jsonl")}]}]}
            result = SCRIPT.run_crf_job(job, out / "job.json")[0]
            self.assertEqual(result["checkpoint_sha256"], SCRIPT.REFERENCE_CHECKPOINT_SHA256)
            micro = fr.scorer_metrics(load_predictions(out / "pred.jsonl"), test_gold, excluded)["t0_exact_span"]["micro"]
            self.assertEqual((micro["precision"], micro["recall"], micro["f1"]), (0.9234, 0.8924, 0.9076))

    def test_worker_refuses_to_overwrite_a_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "m.crfsuite").write_bytes(b"x")
            job = {"models": [{"name": "BASE", "train_jsonl": str(TRAIN), "model_path": str(out / "m.crfsuite"),
                               "metadata_path": str(out / "m.json"), "predict": []}]}
            with self.assertRaises(RuntimeError):
                SCRIPT.run_crf_job(job, out / "job.json")


@unittest.skipUnless(TRAIN.exists() and (ROOT / "data/processed/benchmark/04_missing_fields_800.csv").exists(),
                     "corpus or benchmark missing")
class AugmentationLeakTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from src.evaluation import leak_guard as lg
        cls.lg = lg
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        cls.ctx = SCRIPT.build_context(base / "i", base / "p")
        cls.design = SCRIPT.build_h2_design(cls.ctx)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_design_counts_match_the_measured_values(self):
        d = self.design
        self.assertEqual((d["data04"]["after_leak_guard"], d["data04"]["after_lane_prefix_filter"],
                          d["data04"]["after_dev_test_address_overlap"]), (779, 664, 653))
        self.assertEqual(d["all_aligned"]["groups"], 142)
        self.assertEqual(d["pool"]["01_full_address_new_verified.csv"]["after_dev_test_address_overlap"], 880)
        self.assertEqual(d["pool"]["03_real_address_old_1500.csv"]["after_dev_test_address_overlap"], 1199)

    def test_no_sprint3_text_and_no_dev_test_address_in_any_augmentation_pool(self):
        h2 = self.ctx["h2"]
        index = self.lg.build_exclusion_index()
        pairs = SCRIPT.dev_test_pairs(self.ctx)
        for part in ("aug_train", "heldout", "eval_full", "train_pool"):
            for row in h2[part]:
                self.assertFalse(index.lookup(row["text"]), row["text"])
                by = {s["label"]: row["text"][s["start"]:s["end"]] for s in row["spans"]}
                self.assertFalse(SCRIPT.starts_with_lane(by.get("TenDuong", "")))
                source = row["row"]
                # Data 04 is filtered on its GT house number/street; Data 01/03 have no GT columns.
                keys = ("GT_SoNha", "GT_TenDuong") if "GT_SoNha" in source else ("SoNha", "TenDuong")
                self.assertNotIn((self.lg.normalize_for_overlap(source[keys[0]]),
                                  self.lg.normalize_for_overlap(source[keys[1]])), pairs)

    def test_aug_train_and_heldout_are_group_disjoint(self):
        h2 = self.ctx["h2"]
        self.assertFalse({r["group_key"] for r in h2["aug_train"]} & {r["group_key"] for r in h2["heldout"]})
        self.assertTrue(all(r["group_key"].startswith("ADM|") for r in h2["aug_train"]))
        self.assertTrue(all(r["group_key"].startswith("UNRESOLVED|") for r in h2["heldout"]
                            if not r["group_key"].startswith("ADM|")))
        self.assertEqual(len(h2["aug_train"]) + len(h2["heldout"]), 653)

    def test_eval_full_is_excluded_from_the_full_training_pool(self):
        h2 = self.ctx["h2"]
        self.assertFalse({r["sample_id"] for r in h2["eval_full"]} & {r["sample_id"] for r in h2["train_pool"]})


if __name__ == "__main__":
    unittest.main()
