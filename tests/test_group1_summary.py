"""WP6: hash gate, overwrite refusal, per-cell sources, determinism of the Group 1 summary generator."""

import csv
import hashlib
import importlib
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = "scripts.73_generate_group1_report"


def load_module():
    return importlib.import_module(MODULE)


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def make_fake_run(base: Path, tamper: bool = False, drop_required: bool = False):
    """A run directory in the 'flat' manifest layout used only by the tests."""
    run = base / "fake_run"
    (run / "tables").mkdir(parents=True)
    (run / "tables/a.csv").write_text("x\n1\n", encoding="utf-8")
    (run / "predictions.jsonl").write_text('{"k": 1}\n', encoding="utf-8")
    manifest = {"output_sha256": {
        "tables/a.csv": hashlib.sha256(b"x\n1\n").hexdigest(),
        "predictions.jsonl": hashlib.sha256(b'{"k": 1}\n').hexdigest()}}
    (run / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    if tamper:
        (run / "tables/a.csv").write_text("x\n2\n", encoding="utf-8")
    if drop_required:
        (run / "tables/a.csv").unlink()
    return run


class HashGateTests(unittest.TestCase):
    def test_matching_hashes_pass(self):
        mod = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            make_fake_run(Path(tmp))
            rows, _ = mod.verify_all(Path(tmp), {"X": ("fake_run", "flat")})
            self.assertEqual({r["status"] for r in rows}, {"OK"})

    def test_tampered_output_stops_the_script(self):
        mod = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            make_fake_run(Path(tmp), tamper=True)
            with self.assertRaises(mod.HashMismatch):
                mod.verify_all(Path(tmp), {"X": ("fake_run", "flat")})

    def test_missing_required_file_stops_but_missing_prediction_dump_does_not(self):
        mod = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            run = make_fake_run(Path(tmp))
            (run / "predictions.jsonl").unlink()  # prediction dumps are not committed: allowed to be absent
            rows, _ = mod.verify_all(Path(tmp), {"X": ("fake_run", "flat")})
            self.assertIn("MISSING_OPTIONAL", {r["status"] for r in rows})
        with tempfile.TemporaryDirectory() as tmp:
            make_fake_run(Path(tmp), drop_required=True)
            with self.assertRaises(mod.HashMismatch):
                mod.verify_all(Path(tmp), {"X": ("fake_run", "flat")})

    def test_main_returns_2_and_writes_nothing_when_a_run_is_missing(self):
        mod = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            code = mod.main(["--base-dir", tmp, "--out-root", tmp, "--out-dir", "out_x"])
            self.assertEqual(code, 2)
            self.assertFalse((Path(tmp) / "out_x").exists())


class OverwriteTests(unittest.TestCase):
    def test_existing_output_directory_is_refused_and_untouched(self):
        mod = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            existing = Path(tmp) / "out_x"
            existing.mkdir()
            (existing / "keep.txt").write_text("keep", encoding="utf-8")
            code = mod.main(["--base-dir", tmp, "--out-root", tmp, "--out-dir", "out_x"])
            self.assertEqual(code, 3)
            self.assertEqual((existing / "keep.txt").read_text(encoding="utf-8"), "keep")
            self.assertEqual([p.name for p in existing.iterdir()], ["keep.txt"])


class RelPathTests(unittest.TestCase):
    def test_rel_is_absolute_outside_the_repository_and_relative_inside(self):
        mod = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.csv"
            path.write_text("a,b", encoding="utf-8")
            self.assertEqual(mod.rel(path), path.resolve().as_posix())
        self.assertEqual(mod.rel(ROOT / "scripts"), "scripts")

    def test_cells_can_be_read_from_a_base_dir_outside_the_repository(self):
        mod = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / mod.RUNS["WP1"][0]
            run.mkdir()
            (run / "t.csv").write_text("\n".join(["k,v", "a,1.5", ""]), encoding="utf-8")
            cells = mod.Cells(Path(tmp))
            cells.csv("x", "WP1", "t.csv", {"k": "a"}, "v")
            self.assertEqual(cells.get("x"), 1.5)
            self.assertTrue(cells.source("x").startswith(Path(tmp).resolve().as_posix()))


class FormatTests(unittest.TestCase):
    def test_decimal_comma_sign_and_percent(self):
        mod = load_module()
        self.assertEqual(mod.fmt(0.98431, "4"), "0,9843")
        self.assertEqual(mod.fmt(-0.0022, "4"), "−0,0022")
        self.assertEqual(mod.fmt(0.0022, "+4"), "+0,0022")
        self.assertEqual(mod.fmt(0.9531, "p1"), "95,3%")
        self.assertEqual(mod.fmt(554.0, "i"), "554")

    def test_unknown_cell_in_template_raises(self):
        mod = load_module()
        cells = mod.Cells(mod.BASE)
        with self.assertRaises(KeyError):
            mod.Doc(cells).render("{no.such.cell:3}")


def real_data_available() -> bool:
    mod = load_module()
    return all((mod.BASE / name / "run_manifest.json").exists() for name, _ in mod.RUNS.values())


@unittest.skipUnless(real_data_available(), "Group 1 run directories not present")
class GeneratedOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        mod = load_module()
        cls.mod = mod
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "summary"
        code = mod.main(["--out-root", cls.tmp.name, "--out-dir", "summary", "--test-summary", "TEST"])
        assert code == 0, code
        cls.second = Path(cls.tmp.name) / "summary_again"
        assert mod.main(["--out-root", cls.tmp.name, "--out-dir", "summary_again", "--test-summary", "TEST"]) == 0

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_every_displayed_cell_has_an_existing_source_file(self):
        rows = read_csv(self.out / "tables/unified_cells.csv")
        self.assertGreater(len(rows), 50)
        for row in rows:
            self.assertTrue(row["HienThi"].strip(), row)
            self.assertTrue(row["Nguon"].strip(), f"no source: {row['Hang']} / {row['Cot']}")
            self.assertTrue(row["CellIds"].strip(), f"cell without a cell id: {row['Hang']} / {row['Cot']}")
            for source in row["Nguon"].split(" ; "):
                path = ROOT / source.split(" [")[0]
                self.assertTrue(path.exists(), f"missing source file {path}")

    def test_every_registered_cell_and_hypothesis_has_a_source(self):
        for row in read_csv(self.out / "tables/cells.csv"):
            self.assertTrue((ROOT / row["file"]).exists(), row)
            self.assertTrue(row["selector"], row)
        hypotheses = read_csv(self.out / "tables/hypotheses.csv")
        self.assertEqual([h["Ma"] for h in hypotheses], ["H1", "H2", "H3", "H4", "H5", "E1", "E2", "E3", "E4"])
        for h in hypotheses:
            self.assertTrue(h["Nguon"].strip(), h["Ma"])
            self.assertIn(h["TrangThai"], {"SUPPORTED", "PARTLY_SUPPORTED", "NOT_SUPPORTED", "INCONCLUSIVE", "NOT_TESTABLE", "NOT_RUN"})

    def test_headline_numbers_match_the_result_files(self):
        checks = read_csv(self.out / "tables/cross_check.csv")
        self.assertGreaterEqual(len(checks), 40)
        self.assertEqual([r for r in checks if r["status"] == "DIFFERENT"], [])
        self.assertGreaterEqual(sum(r["status"] == "MATCH" for r in checks), 40)
        self.assertEqual([r for r in read_csv(self.out / "tables/cross_report_consistency.csv") if r["status"] != "AGREE"], [])

    def test_all_declared_hashes_verified_and_manifest_records_inputs(self):
        manifest = json.loads((self.out / "run_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(set(manifest["hash_checks"]["by_status"]) - {"OK", "MISSING_OPTIONAL"}, set())
        self.assertGreater(manifest["hash_checks"]["files"], 100)
        self.assertTrue(manifest["input_sha256"])
        for rel_path, sha in manifest["input_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / rel_path).read_bytes()).hexdigest(), sha)
        for rel_path, sha in manifest["output_sha256"].items():
            self.assertEqual(hashlib.sha256((self.out / rel_path).read_bytes()).hexdigest(), sha)

    def test_output_is_deterministic(self):
        first = json.loads((self.out / "run_manifest.json").read_text(encoding="utf-8"))["output_sha256"]
        second = json.loads((self.second / "run_manifest.json").read_text(encoding="utf-8"))["output_sha256"]
        self.assertEqual(first, second)

    def test_draft_report_has_sections_a_to_f(self):
        text = (self.out / "report_draft.md").read_text(encoding="utf-8")
        for heading in ("## a.", "## b.", "## c.", "## d.", "## e.", "## f."):
            self.assertIn(heading, text)
        self.assertNotIn("{", text.replace("{{", ""), "unrendered template token")


if __name__ == "__main__":
    unittest.main()
