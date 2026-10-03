"""Explicit device overlay; locked data, optimizer, search and precision stay unchanged."""

import copy
import json
from pathlib import Path

from src.evaluation.dev_runner import file_hash
from src.modeling.protocol import PROTOCOL_LOCK_PATH, validate_training_config


def apply_hardware_profile(config, path: Path):
    profile = json.loads(path.read_text(encoding="utf-8"))
    expected_keys = {"version", "device", "precision", "amp", "torch_version", "cuda_wheel_index", "min_vram_bytes", "protocol_lock_sha256"}
    if set(profile) != expected_keys or profile["version"] != "s3-colab-cuda128-v1":
        raise ValueError("UNKNOWN_HARDWARE_PROFILE")
    if profile["device"] != "cuda:0" or profile["precision"] != "float32" or profile["amp"] is not False or profile["torch_version"] != "2.8.0" or profile["cuda_wheel_index"] != "https://download.pytorch.org/whl/cu128" or profile["min_vram_bytes"] != 8 * 1024**3:
        raise ValueError("HARDWARE_PROFILE_CHANGES_LOCKED_POLICY")
    if profile["protocol_lock_sha256"] != file_hash(PROTOCOL_LOCK_PATH):
        raise ValueError("HARDWARE_PROFILE_PROTOCOL_MISMATCH")
    result = copy.deepcopy(config)
    result.update(device=profile["device"], hardware_profile=profile, hardware_profile_sha256=file_hash(path))
    validate_training_config(result)
    return result
