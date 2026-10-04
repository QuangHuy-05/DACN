"""Fixtures verify cloud handoff guards; these are not pretrained GPU experiments."""

import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.evaluation.dev_runner import ROOT, file_hash
from src.modeling.kaggle_handoff import assert_training_file, safe_name, verify_download, validate_package
from src.modeling.kaggle_remote import checked_config, validate_smoke_evidence, evidence_identity, audit_alignment, run_full
from src.modeling.alignment import align_text


class KaggleGuardsTests(unittest.TestCase):
    def test_relaunch_is_not_a_new_data_upload(self):
        from src.modeling.kaggle_handoff import build_relaunch
        with tempfile.TemporaryDirectory(dir=ROOT / "data/interim/modeling/sprint03") as folder:
            root = Path(folder)
            source = root / "source"
            (source / "kernel").mkdir(parents=True)
            (source / "kernel/kernel-metadata.json").write_text(json.dumps({
                "is_private": True, "enable_gpu": True, "dataset_sources": ["owner/train"]}))
            item = {"version": "fixture", "mode": "smoke", "identity": evidence_identity(), "archives": {},
                    "model": "PHOBERT-CRF", "candidate": "c01", "allow_full_training": False,
                    "train_count": 240, "dev_count": 60, "test100": "NOT_INCLUDED_NOT_READ",
                    "kernel_id": "owner/old", "dataset_id": "owner/train"}
            with patch("src.modeling.kaggle_handoff.validate_package", return_value=item):
                result = build_relaunch(root / "new", source, "dacn-new-notebook001")
            self.assertEqual(result["upload_bytes"], 0)
            self.assertEqual(result["dataset_id"], "owner/train")
            self.assertFalse((root / "new/dataset").exists())
            notebook = json.loads((root / "new/kernel/kaggle_entry.ipynb").read_text())
            self.assertEqual(notebook["cells"][0]["outputs"], [])

    def test_private_policy_cannot_be_bypassed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "kernel").mkdir()
            path = root / "kernel/kernel-metadata.json"
            path.write_text(json.dumps({"is_private": False, "dataset_sources": ["owner/train"]}))
            (root / "handoff_manifest.json").write_text(json.dumps({
                "package_files": {"kernel/kernel-metadata.json": file_hash(path)},
                "dataset_id": "owner/train", "test100": "NOT_INCLUDED_NOT_READ", "mode": "smoke"}))
            with self.assertRaisesRegex(ValueError, "PRIVATE_INPUT_POLICY"):
                validate_package(root)

    def test_only_released_train_dev_data_can_be_uploaded(self):
        assert_training_file("data/processed/annotation/sprint03/corpus_train_dev_v2/train.jsonl")
        for name in ("data/interim/annotation/sprint03/test100_import.json", "data/raw/foo",
                     "data/processed/benchmark/a.csv", "data/interim/annotation/a.json", "x/kaggle.json"):
            with self.assertRaises(ValueError):
                assert_training_file(name)

    def test_no_path_escape_in_job_name(self):
        self.assertEqual(safe_name("dacn-kaggle-run001"), "dacn-kaggle-run001")
        for name in ("../escape", "/tmp/x", "a", "x/y/z"):
            with self.assertRaises(ValueError):
                safe_name(name)

    def test_gpu_overlay_preserves_locked_training(self):
        config = checked_config("PHOBERT-CRF")
        self.assertEqual(config["device"], "cuda:0")
        self.assertEqual(config["hardware_profile"]["version"], "s3-kaggle-cuda128-v1")
        self.assertEqual(config["max_epochs"], 20)
        self.assertEqual(config["micro_batch_size"], 4)
        self.assertEqual(config["effective_batch_size"], 16)
        self.assertFalse(config["hardware_profile"]["amp"])

    def test_full_training_is_off_and_fixture_is_not_smoke_pass(self):
        with self.assertRaisesRegex(ValueError, "DISABLED"):
            run_full(Path("never_created"), None)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fixture.json"
            path.write_text(json.dumps({"status": "FIXTURE_PASS", "identity": evidence_identity()}))
            with self.assertRaisesRegex(ValueError, "REAL_SMOKE_PASS"):
                validate_smoke_evidence(path)

    def test_changed_identity_blocks_full_training(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fixture.json"
            path.write_text(json.dumps({"status": "SMOKE_PASS", "full_training_performed": False, "identity": {}}))
            with self.assertRaisesRegex(ValueError, "IDENTITY_MISMATCH"):
                validate_smoke_evidence(path)

    def test_alignment_uses_raw_text_and_masks_t1_only(self):
        rows = [{"sample_id": "excluded", "text": "12 phố A", "spans": [
            {"start": 0, "end": 2, "label": "SoNha"}], "address_system": "moi"}]
        processor = type("FixtureProcessor", (), {"align_text": staticmethod(align_text)})()
        with tempfile.TemporaryDirectory() as folder:
            examples, report = audit_alignment(processor, {"evaluation_exclusions": {"t1": ["excluded"]}},
                                               {"train": rows, "dev": rows}, Path(folder))
            self.assertFalse(examples["train"][0][-1])
            self.assertEqual(report["t1_eligible"]["dev"], 0)
            self.assertEqual(examples["train"][0][1][0], "B-SoNha")

    def test_download_requires_hash_and_run_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            report = root / "job_report.json"
            report.write_text("fixture")
            (root / "artifact_manifest.json").write_text(json.dumps({"run_id": "r", "identity": {},
                "status": "REMOTE_BLOCKED_OR_FAILED", "files": {report.name: file_hash(report)}}))
            result = verify_download(root, {"run_id": "r", "identity": {}})
            self.assertEqual(result["remote_status"], "REMOTE_BLOCKED_OR_FAILED")
            report.write_text("changed")
            with self.assertRaisesRegex(ValueError, "OUTPUT_HASH_MISMATCH"):
                verify_download(root, {"run_id": "r", "identity": {}})

    def test_existing_api_report_prevents_repeating_mutation(self):
        module = importlib.import_module("scripts.50_kaggle_pipeline")
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / "existing.json"
            report.write_text("{}")
            with patch.object(module.subprocess, "run") as call:
                with self.assertRaises(FileExistsError):
                    module.kaggle_call(["datasets", "create"], report=report)
                call.assert_not_called()

    def test_template_is_parseable_after_configuration_injection(self):
        import ast
        template = (ROOT / "notebooks/sprint03/kaggle_entry.py").read_text()
        ast.parse(template.replace("__JOB_CONFIG_JSON__", repr("{}")))
        self.assertNotIn("kaggle.json", template)

    def test_api_rejection_is_not_success_even_if_cli_exits_zero(self):
        from types import SimpleNamespace
        module = importlib.import_module("scripts.50_kaggle_pipeline")
        fake = SimpleNamespace(stdout="Kernel push error: GPU quota exceeded", stderr="", returncode=0)
        with patch.object(module, "credential_environment", return_value=({}, [])), \
                patch.object(module.subprocess, "run", return_value=fake), \
                patch.object(module.Path, "is_file", return_value=True):
            result = module.kaggle_call(["kernels", "push"])
        self.assertEqual(result["returncode"], 2)
        self.assertEqual(result["status"], "API_COMMAND_FAILED")


if __name__ == "__main__":
    unittest.main()
