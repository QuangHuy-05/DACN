"""Local bundle/security and future GPU execution gate fixtures."""
import ast
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from src.evaluation.dev_runner import file_hash
from src.modeling.colab_handoff import TRAIN_DEPENDENCIES, safe_extract, write_archive, build_handoff
from src.modeling.colab_local_handoff import training_notebook, final_notebook
from src.modeling.colab_runtime import validate_smoke_evidence, run_candidate


class LocalColabHandoffTests(unittest.TestCase):
    def test_training_bundle_dependency_list_has_no_test_queue(self):
        self.assertEqual(len(TRAIN_DEPENDENCIES), 3)
        self.assertTrue(any(path.endswith("trace.jsonl") for path in TRAIN_DEPENDENCIES))
        self.assertFalse(any("batch01" in path for path in TRAIN_DEPENDENCIES))

    def test_old_notebook_blocks_before_bundle_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            notebook = root / "notebooks/sprint03/old.ipynb"
            notebook.parent.mkdir(parents=True)
            notebook.write_text("immutable old notebook")
            with patch("src.modeling.colab_handoff.ROOT", root), self.assertRaises(FileExistsError):
                build_handoff(root / "output", notebook, "v2")
            self.assertFalse((root / "output").exists())

    def test_duplicate_members_and_unlisted_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for duplicate in (True, False):
                archive = root / ("duplicate.zip" if duplicate else "extra.zip")
                with zipfile.ZipFile(archive, "w") as stream:
                    stream.writestr("file.txt", "a")
                    if duplicate:
                        stream.writestr("file.txt", "b")
                    stream.writestr("code_bundle_manifest.json", json.dumps({"files": {}, "scope": "fixture"}))
                with self.assertRaises(ValueError):
                    safe_extract(archive, root / archive.stem, file_hash(archive))
                self.assertFalse((root / archive.stem / "file.txt").exists())

    def test_archive_builder_rejects_traversal_and_manifest_collision(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "a.txt"
            source.write_text("fixture")
            for key in ("../outside", "code_bundle_manifest.json", "C:/secret"):
                with self.assertRaises(ValueError):
                    write_archive(root / "bad.zip", {key: source}, {"scope": "fixture"})
            self.assertFalse((root / "bad.zip").exists())

    def test_notebook_ast_and_execution_gates(self):
        code = {"path": "dacn_train_dev_bundle_v2.zip", "sha256": "a" * 64}
        resources = {"path": "dacn_phobert_resources_v2.zip", "sha256": "b" * 64}
        notebook = training_notebook(code, resources)
        sources = []
        for item in notebook["cells"] + final_notebook()["cells"]:
            if item["cell_type"] == "code":
                source = "".join(item["source"])
                ast.parse(source)
                self.assertIsNone(item["execution_count"])
                self.assertEqual(item["outputs"], [])
        sources = ["".join(item["source"]) for item in notebook["cells"] if item["cell_type"] == "code"]
        self.assertIn("ENABLE_NEURAL_TRAINING = False", sources[0])
        self.assertTrue(any("validate_smoke_evidence" in source for source in sources))
        self.assertFalse(any("test_benchmark_t0" in source for source in sources))
        self.assertTrue(any('"c01", "c02"' in source for source in sources))

    def test_resource_legal_symlink_is_dereferenced_only_with_explicit_policy(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target, link = root / "LICENSE", root / "legal-link"
            target.write_text("fixture legal terms")
            try:
                link.symlink_to(target)
            except OSError:
                self.skipTest("Filesystem does not permit fixture symlinks")
            with patch("src.modeling.colab_handoff.ROOT", root):
                with self.assertRaises(ValueError):
                    write_archive(root / "default.zip", {"legal/LICENSE": link}, {"scope": "fixture"})
                info = write_archive(root / "resource.zip", {"legal/LICENSE": link}, {"scope": "fixture"},
                                     "resource_bundle_manifest.json", allow_source_symlinks=True)
            safe_extract(root / "resource.zip", root / "workspace", info["sha256"], "resource_bundle_manifest.json")
            self.assertFalse((root / "workspace/legal/LICENSE").is_symlink())
            self.assertEqual((root / "workspace/legal/LICENSE").read_text(), target.read_text())

    def test_training_default_rejects_without_loading_any_model(self):
        with patch("src.modeling.colab_runtime.validate_smoke_evidence") as validator:
            with self.assertRaisesRegex(ValueError, "DISABLED_BY_DEFAULT"):
                run_candidate(Path("fixture"), Path("smoke"), "PHOBERT-CRF")
            validator.assert_not_called()

    def test_cpu_fixture_or_partial_smoke_cannot_open_gpu_training(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "smoke.json"
            identity = {"fixture": "hash"}
            value = {"status": "SMOKE_PASS", "full_training_performed": False, "identity": identity,
                "alignment": {"train": 240, "dev": 60}, "models": {name: {
                    "status": "PRETRAINED_OPTIMIZER_CHECKPOINT_PASS", "pretrained": True, "device": "cpu",
                    "optimizer_steps": 1, "checkpoint_reload": "PASS"} for name in ("PHOBERT-CRF", "PROPOSED-DYN")}}
            path.write_text(json.dumps(value))
            with patch("src.modeling.colab_runtime.evidence_identity", return_value=identity):
                with self.assertRaisesRegex(ValueError, "CPU_OR_PARTIAL_SMOKE"):
                    validate_smoke_evidence(path)


if __name__ == "__main__":
    unittest.main()
