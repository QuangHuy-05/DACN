import contextlib
import importlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

ms = importlib.import_module("scripts.70_run_multiseed_local")
ROOT = ms.ROOT


class SeedAndConfigTests(unittest.TestCase):
    def test_seed_outside_locked_set_is_rejected(self):
        for seed in (0, 7, 43, 2026):
            with self.assertRaises(ValueError):
                ms.validate_seed(seed)
        for seed in (42, 1337, 2025):
            self.assertEqual(ms.validate_seed(seed), seed)
        with self.assertRaises(ValueError):
            ms.run_name("pcrf", 99)
        with self.assertRaises(ValueError):
            ms.run_name("nope", 42)

    def test_run_order_is_sequential_pcrf_then_dyn_per_seed(self):
        self.assertEqual(ms.RUN_ORDER, [("pcrf", 42), ("dyn", 42), ("pcrf", 1337), ("dyn", 1337),
                                        ("pcrf", 2025), ("dyn", 2025)])

    def test_locked_files_unchanged_by_building_a_seed_config(self):
        paths = [ROOT / v["config"] for v in ms.MODELS.values()] + [ms.PROTOCOL_LOCK]
        if not all(p.exists() for p in paths):
            self.skipTest("locked configs not available")
        before = [ms.fr.sha256_file(p) for p in paths]
        try:
            config = ms.build_seed_config("dyn", 1337)
        except ImportError:
            self.skipTest("modeling package not importable in this runtime")
        self.assertEqual(config["seed"], 1337)
        self.assertEqual(config["candidate"]["id"], "c02")
        self.assertEqual(config["device"], "cpu")
        self.assertEqual(before, [ms.fr.sha256_file(p) for p in paths])
        original = json.loads((ROOT / ms.MODELS["dyn"]["config"]).read_text(encoding="utf-8"))
        self.assertEqual(original["seed"], 42)  # only the in-memory copy changed
        manifest = ms.PROCESSED / "run_manifest.json"
        if manifest.exists():
            recorded = json.loads(manifest.read_text(encoding="utf-8"))["inputs"]
            self.assertEqual(recorded["protocol_lock_sha256"], ms.fr.sha256_file(ms.PROTOCOL_LOCK))
            for model, digest in recorded["config_sha256"].items():
                self.assertEqual(digest, ms.fr.sha256_file(ROOT / ms.MODELS[model]["config"]))


class CleanupTests(unittest.TestCase):
    def _make_run(self, base: Path) -> Path:
        run = base / "pcrf_seed42"
        (run / "checkpoints").mkdir(parents=True)
        for name in ("epoch_001.pt", "epoch_002.pt", "resume_epoch_002.pt", "last.pt", "best.pt"):
            (run / "checkpoints" / name).write_bytes(name.encode() * 10)
        (run / "checkpoints" / "best.pt.json").write_text("{}", encoding="utf-8")
        (run / "training_log.jsonl").write_text("{}\n", encoding="utf-8")
        return run

    def test_cleanup_removes_heavy_files_but_keeps_best(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            run = self._make_run(base)
            result = ms.safe_cleanup(run, base)
            self.assertEqual(sorted(r["file"] for r in result["removed"]),
                             ["epoch_001.pt", "epoch_002.pt", "last.pt", "resume_epoch_002.pt"])
            self.assertTrue(all(r["sha256"] and r["bytes"] > 0 for r in result["removed"]))
            self.assertTrue((run / "checkpoints/best.pt").exists())
            self.assertTrue((run / "checkpoints/best.pt.json").exists())
            self.assertTrue((run / "training_log.jsonl").exists())

    def test_cleanup_refuses_directories_outside_the_package(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as other:
            base = Path(tmp)
            outside = self._make_run(Path(other))
            with self.assertRaises(ValueError):
                ms.safe_cleanup(outside, base)
            with self.assertRaises(ValueError):
                ms.safe_cleanup(base, base)
            self.assertTrue((outside / "checkpoints/epoch_001.pt").exists())


class StatisticsTests(unittest.TestCase):
    def test_mean_std_hand_example(self):
        result = ms.mean_std([1.0, 2.0, 3.0])
        self.assertEqual((result["n"], result["mean"]), (3, 2.0))
        self.assertAlmostEqual(result["std"], 1.0)  # ddof=1
        one = ms.mean_std([0.5])
        self.assertEqual((one["n"], one["mean"], one["std"]), (1, 0.5, None))
        self.assertEqual(ms.mean_std([None, 1.0, 3.0])["n"], 2)
        self.assertEqual(ms.mean_std([])["mean"], None)

    def test_sprint3_gpu_row_is_not_in_the_average(self):
        with tempfile.TemporaryDirectory() as tmp:
            processed, interim = Path(tmp) / "p", Path(tmp) / "i"
            (processed / "runs").mkdir(parents=True)
            interim.mkdir()
            for seed, f1 in ((42, 0.97), (1337, 0.95)):
                row = {"run": f"pcrf_seed{seed}", "variant": "pcrf", "seed": seed, "model": "pcrf", "t0_precision": f1,
                       "t0_recall": f1, "t0_f1": f1, "exact_match": 90, "t1": "NOT_IMPLEMENTED"}
                (processed / "runs" / f"pcrf_seed{seed}_pcrf_metrics.json").write_text(json.dumps({"row": row}), encoding="utf-8")
            original = (ms.PROCESSED, ms.INTERIM)
            ms.PROCESSED, ms.INTERIM = processed, interim
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    ms.cmd_aggregate(None)
            finally:
                ms.PROCESSED, ms.INTERIM = original
            summary = json.loads((processed / "metrics.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["pcrf"]["t0_f1"]["n"], 2)
        self.assertAlmostEqual(summary["pcrf"]["t0_f1"]["mean"], 0.96)
        self.assertEqual(summary["pcrf"]["partial_seeds"], "PARTIAL_SEEDS")
        self.assertIn("PHOBERT-CRF", summary["sprint3_gpu_t4_seed42_not_in_mean"])
        self.assertEqual(summary["dyn"]["t0_f1"]["n"], 0)


class DiagnosticTests(unittest.TestCase):
    def test_argmax_ignores_threshold_and_respects_mask(self):
        from src.evaluation.schema import SpanModelOutput
        def pred(sid, posterior, system="khong_ro"):
            return SpanModelOutput(sid, "x", predicted_system=system, trace={"structure": {"posterior": posterior}})
        preds = [pred("a", {"cu": 0.5, "moi": 0.3, "Lai": 0.2}), pred("b", {"cu": 0.2, "moi": 0.3, "Lai": 0.5}),
                 pred("c", {"cu": 0.9, "moi": 0.05, "Lai": 0.05})]
        golds = [{"sample_id": "a", "address_system": "cu"}, {"sample_id": "b", "address_system": "Lai"},
                 {"sample_id": "c", "address_system": "moi"}]
        units = ms.argmax_t1_units(preds, golds, excluded={"c"})
        self.assertEqual(units.tolist(), [[0, 0], [2, 2]])


if __name__ == "__main__":
    unittest.main()
