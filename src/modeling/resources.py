"""Local-only resources: preflight never downloads, imports models or trains."""

from importlib import metadata, util
from contextlib import contextmanager
import json
from pathlib import Path
import platform
import shutil
import os
from unittest.mock import patch

from src.evaluation.dev_runner import ROOT, file_hash
from src.modeling.protocol import validate_training_config


def validate_resource_lock(path: Path, model_id: str) -> dict:
    lock = json.loads(path.read_text(encoding="utf-8"))
    if lock.get("model_family") != ("DP-FT-FT" if model_id == "DP-FT-FT" else "PHOBERT"):
        raise ValueError("RESOURCE_FAMILY_MISMATCH")
    required = ("base_checkpoint", "embedding") if model_id == "DP-FT-FT" else ("encoder", "tokenizer", "segmenter")
    for name in required:
        entry = lock.get("components", {}).get(name, {})
        if not entry.get("revision") or entry.get("license_status") != "CLEARED":
            raise ValueError(f"RESOURCE_EVIDENCE_PENDING:{name}")
        directory = ROOT / entry.get("path", "")
        if not directory.is_dir() or not entry.get("files"):
            raise ValueError(f"RESOURCE_FILES_MISSING:{name}")
        forbidden = [ROOT / "data/raw", ROOT / "data/interim/annotation", ROOT / "data/processed/annotation", ROOT / "data/processed/benchmark"]
        if any(directory.resolve().is_relative_to(blocked.resolve()) for blocked in forbidden):
            raise ValueError("ANNOTATION_OR_ADDRESS_DATA_CANNOT_BE_MODEL_RESOURCE")
        for relative, digest in entry["files"].items():
            file = (directory / relative).resolve()
            if not file.is_relative_to(directory.resolve()) or not file.is_file() or file_hash(file) != digest:
                raise ValueError(f"RESOURCE_HASH_MISMATCH:{name}:{relative}")
        actual = {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
        if actual != set(entry["files"]):
            raise ValueError(f"RESOURCE_UNDECLARED_FILES:{name}")
    return lock


def preflight(config: dict, resource_lock_path: Path | None = None) -> dict:
    validate_training_config(config)
    names = {"torch": "torch", "deepparse": "deepparse", "poutyne": "poutyne"} if config["model_id"] == "DP-FT-FT" else {
        "torch": "torch", "transformers": "transformers", "py-vncorenlp": "py_vncorenlp"}
    packages, blockers = {}, []
    if platform.python_version_tuple()[:2] != ("3", "11"):
        blockers.append("PYTHON_TARGET_MISMATCH: pinned neural profile requires isolated WSL Python 3.11")
    for package, module in names.items():
        try:
            version = metadata.version(package)
            packages[package] = version
            if version.split("+", 1)[0] != config["package_versions"][package]:
                blockers.append(f"PACKAGE_VERSION_MISMATCH:{package}:{version}")
            if util.find_spec(module) is None:
                blockers.append(f"MODULE_MISSING:{module}")
        except metadata.PackageNotFoundError:
            packages[package] = None
            blockers.append(f"PACKAGE_MISSING:{package}")
    lock = None
    if resource_lock_path is None:
        blockers.append("RESOURCE_LOCK_MISSING:no local checkpoint/tokenizer/segmenter evidence")
    else:
        try:
            lock = validate_resource_lock(resource_lock_path, config["model_id"])
        except (OSError, ValueError, KeyError) as exc:
            blockers.append(str(exc))
    if config["model_id"] == "DP-FT-FT":
        try:
            info = Path("/proc/meminfo").read_text()
            available = int(next(line.split()[1] for line in info.splitlines() if line.startswith("MemAvailable:"))) * 1024
            if available < 10 * 1024**3:
                blockers.append("RAM_BELOW_FULL_FASTTEXT_PREFLIGHT:need 10 GiB available host RAM")
        except (OSError, StopIteration, ValueError):
            available = None
            blockers.append("HOST_RAM_NOT_VERIFIED")
    else:
        available = None
        if shutil.which("java") is None:
            blockers.append("JAVA_MISSING_FOR_VNCORENLP")
    required_disk = 3 * 1024**3 if config["model_id"] == "DP-FT-FT" else 20 * 1024**3
    if shutil.disk_usage(ROOT).free < required_disk:
        blockers.append(f"DISK_BELOW_TRAINING_ARTIFACT_BUDGET:need {required_disk} bytes free per new run")
    gpu = None
    if str(config.get("device", "cpu")).startswith("cuda"):
        try:
            import torch
            if not torch.cuda.is_available():
                blockers.append("CUDA_NOT_AVAILABLE:no automatic CPU fallback")
            else:
                gpu = torch.cuda.get_device_properties(0).total_memory
                if gpu < config.get("hardware_profile", {}).get("min_vram_bytes", 8 * 1024**3):
                    blockers.append("GPU_VRAM_BELOW_PROFILE_BUDGET")
        except (ImportError, RuntimeError, OSError) as error:
            blockers.append("CUDA_RUNTIME_NOT_VERIFIED:" + type(error).__name__)
    return {"model_id": config["model_id"], "status": "PREFLIGHT_PASS" if not blockers else "INTEGRATION_PENDING_RESOURCE",
            "python": platform.python_version(), "packages": packages, "resource_lock_verified": lock is not None,
            "disk_free_bytes": shutil.disk_usage(ROOT).free, "required_training_disk_free_bytes": required_disk, "available_ram_bytes": available,
            "gpu_vram_bytes": gpu, "hardware_profile_sha256": config.get("hardware_profile_sha256"),
            "blockers": blockers, "download_performed": False, "training_performed": False}


def load_phobert_processor(config: dict, lock: dict):
    from transformers import AutoTokenizer
    from py_vncorenlp import VnCoreNLP
    from src.modeling.alignment import PhoBERTProcessor
    components = lock["components"]
    tokenizer = AutoTokenizer.from_pretrained(str(ROOT / components["tokenizer"]["path"]),
                                             local_files_only=True, use_fast=False)
    original_directory = Path.cwd()
    try:
        segmenter = VnCoreNLP(annotators=["wseg"], save_dir=str(ROOT / components["segmenter"]["path"]))
    finally:
        os.chdir(original_directory)
    limit = min(config["max_encoder_tokens"], tokenizer.model_max_length)
    processor = PhoBERTProcessor(tokenizer, segmenter, limit)
    processor.resource_evidence = {"tokenizer": components["tokenizer"], "segmenter": components["segmenter"],
                                   "transformers": metadata.version("transformers"), "py-vncorenlp": metadata.version("py-vncorenlp")}
    return processor


@contextmanager
def offline_native_resources():
    """Native loaders may try downloading a missing cache file despite offline=True."""
    def denied(*args, **kwargs):
        raise RuntimeError("NETWORK_DISABLED_FOR_MODEL_LOADER: supply exact declared local cache")
    with patch("socket.socket.connect", denied), patch("socket.create_connection", denied):
        yield
