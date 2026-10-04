"""Network-free transfer fixtures; these are not pretrained experiments."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from src.modeling.kaggle_artifacts import output_path, stream_response, parse_kernel_ref, selected_output, verify_selected_output, reuse_verified_file


class ResponseFixture:
    def __init__(self, blocks, length):
        self.blocks = blocks
        self.headers = {"Content-Length": str(length)}
        self.closed = False
    @property
    def content(self):
        raise AssertionError("Whole-file buffering is forbidden")
    def raise_for_status(self):
        pass
    def iter_content(self, chunk_size):
        if chunk_size != 1024 * 1024:
            raise AssertionError("Unexpected chunk budget")
        yield from self.blocks
    def close(self):
        self.closed = True


class KaggleArtifactTests(unittest.TestCase):
    def test_cached_file_requires_fresh_index_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, target = root / "source.pt", root / "new/checkpoint.pt"
            source.write_bytes(b"cached")
            self.assertIsNone(reuse_verified_file(source, target, "different"))
            self.assertFalse(target.exists())
            result = reuse_verified_file(source, target, hashlib.sha256(b"cached").hexdigest())
            self.assertEqual(result["transfer_bytes"], 0)
            self.assertEqual(target.read_bytes(), b"cached")
            self.assertEqual(source.stat().st_ino, target.stat().st_ino)
            with self.assertRaises(FileExistsError):
                reuse_verified_file(source, target, result["sha256"])

    def test_selection_profile_is_explicit_and_preserves_reports_best_last(self):
        for name in ("reports/metrics.json", "weights/epoch_001.pt.json", "weights/best.pt", "weights/last.pt"):
            self.assertTrue(selected_output(name, "selection"))
        self.assertFalse(selected_output("weights/epoch_001.pt", "selection"))
        self.assertTrue(selected_output("weights/epoch_001.pt", "all"))
        with self.assertRaisesRegex(ValueError, "UNKNOWN_ARTIFACT_PROFILE"):
            selected_output("x", "unknown")

    def test_selection_verification_does_not_claim_remote_only_epochs_verified(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "weights/best.pt"
            path.parent.mkdir()
            path.write_bytes(b"weights")
            files = {"weights/best.pt": hashlib.sha256(b"weights").hexdigest(), "weights/epoch_001.pt": "remote-only"}
            (root / "artifact_manifest.json").write_text(json.dumps({"run_id": "r", "identity": {},
                "status": "FULL_TRAINING_DEV_ONLY_COMPLETE", "files": files}))
            result = verify_selected_output(root, {"run_id": "r", "identity": {}})
            self.assertEqual(result["status"], "SELECTED_ARTIFACTS_HASH_VERIFIED")
            self.assertEqual(set(result["remote_only_epoch_checkpoints"]), {"weights/epoch_001.pt"})
            path.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "OUTPUT_HASH_MISMATCH"):
                verify_selected_output(root, {"run_id": "r", "identity": {}})

    def test_selection_verification_requires_all_selected_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "artifact_manifest.json").write_text(json.dumps({"run_id": "r", "identity": {},
                "status": "FULL_TRAINING_DEV_ONLY_COMPLETE", "files": {"metrics.json": "missing"}}))
            with self.assertRaisesRegex(ValueError, "OUTPUT_HASH_MISMATCH"):
                verify_selected_output(root, {"run_id": "r", "identity": {}})
    def test_version_is_pinned_to_sdk_v_label(self):
        self.assertEqual(parse_kernel_ref("owner/kernel-slug/2"), ("owner", "kernel-slug", "v2"))
        for name in ("owner/kernel-slug", "owner/kernel-slug/0", "owner/kernel-slug/latest"):
            with self.assertRaisesRegex(ValueError, "EXACT_KERNEL_VERSION_REQUIRED"):
                parse_kernel_ref(name)

    def test_streaming_hash_and_atomic_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "checkpoint.pt"
            response = ResponseFixture([b"ab", b"", b"cd"], 4)
            result = stream_response(response, path)
            self.assertEqual(path.read_bytes(), b"abcd")
            self.assertEqual(result["sha256"], hashlib.sha256(b"abcd").hexdigest())
            self.assertTrue(response.closed)
            self.assertFalse(path.with_name(path.name + ".download.part").exists())
    def test_truncated_transfer_does_not_publish(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "checkpoint.pt"
            with self.assertRaisesRegex(ValueError, "TRUNCATED"):
                stream_response(ResponseFixture([b"ab"], 4), path)
            self.assertEqual(list(Path(folder).iterdir()), [])
    def test_disk_budget_and_existing_output(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "checkpoint.pt"
            with self.assertRaisesRegex(ValueError, "DISK_BUDGET"):
                stream_response(ResponseFixture([b"ab"], 2), path, max_bytes=1)
            path.write_bytes(b"original")
            with self.assertRaises(FileExistsError):
                stream_response(ResponseFixture([b"new"], 3), path)
            self.assertEqual(path.read_bytes(), b"original")
    def test_remote_paths_cannot_escape_workspace(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in ("../outside", "/outside", "C:/outside", "a\\b", ""):
                with self.assertRaises(ValueError):
                    output_path(folder, name)
            self.assertEqual(output_path(folder, "nested/checkpoint.pt"), Path(folder) / "nested/checkpoint.pt")
