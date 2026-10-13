"""Atomic, hash-bound checkpoints and explicit optimizer/RNG resume contracts."""

import os
from pathlib import Path
import random
import tempfile

from src.evaluation.dev_runner import file_hash, write_json
from src.modeling.labels import label_metadata
from src.modeling.protocol import canonical_hash


def training_signature(config: dict) -> str:
    # Run names and inference-only constraint mode do not change learned weights.
    value = {key: val for key, val in config.items() if key not in ("run_id", "structural_policy", "purpose")}
    if value.get("model_id") == "PROPOSED-NO-CONSTRAINT":
        value["model_id"] = "PROPOSED-DYN"
    return canonical_hash(value)


def validate_checkpoint_metadata(meta: dict, config: dict, corpus_hash: str,
                                 resource_lock_sha256: str, resume: bool = False) -> None:
    if meta.get("label_map") != label_metadata():
        raise ValueError("CHECKPOINT_LABEL_MAP_MISMATCH")
    if meta.get("processor_version") != config["processor_version"]:
        raise ValueError("CHECKPOINT_PROCESSOR_MISMATCH")
    if meta.get("corpus_manifest_sha256") != corpus_hash or meta.get("resource_lock_sha256") != resource_lock_sha256:
        raise ValueError("CHECKPOINT_DATA_OR_RESOURCE_MISMATCH")
    if meta.get("training_signature") != training_signature(config):
        raise ValueError("RESUME_CONFIG_MISMATCH")
    if resume and meta.get("resume_supported") is not True:
        raise ValueError("OPTIMIZER_RESUME_UNSUPPORTED: use --weights-from with a new run")


def capture_rng():
    import torch
    states = {"python": random.getstate(), "torch": torch.get_rng_state()}
    if torch.cuda.is_available():
        states["cuda"] = torch.cuda.get_rng_state_all()
    try:
        import numpy as np
        states["numpy"] = np.random.get_state()
    except ImportError:
        pass
    return states


def restore_rng(states):
    import torch
    random.setstate(states["python"])
    torch.set_rng_state(states["torch"])
    if "cuda" in states and torch.cuda.is_available():
        torch.cuda.set_rng_state_all(states["cuda"])
    if "numpy" in states:
        import numpy as np
        np.random.set_state(states["numpy"])


def save_checkpoint(path: Path, model, metadata: dict, optimizer=None, scheduler=None,
                    selection_state=None, native_payload=None) -> dict:
    import torch
    if path.exists() or path.with_suffix(path.suffix + ".json").exists():
        raise FileExistsError("Checkpoint path is immutable: " + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = native_payload or {"model": model.state_dict(), "optimizer": optimizer.state_dict() if optimizer else None,
        "scheduler": scheduler.state_dict() if scheduler else None, "scaler": None,
        "rng": capture_rng(), "selection_state": selection_state or {}}
    # PyTorch's zip writer rejects leading-dot basenames on some filesystems.
    handle, temporary = tempfile.mkstemp(prefix="checkpoint-", suffix=".pt.tmp", dir=path.parent)
    os.close(handle)
    temp_path = Path(temporary)
    try:
        torch.save(payload, temp_path)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    value = {**metadata, "checkpoint_sha256": file_hash(path), "checkpoint_file": path.name,
             "atomic_write": True, "complete": True}
    write_json(path.with_suffix(path.suffix + ".json"), value)
    return value


def load_checkpoint(path: Path, config: dict, corpus_hash: str, resource_hash: str,
                    model=None, optimizer=None, scheduler=None, resume=False):
    import json
    import torch
    meta = json.loads(path.with_suffix(path.suffix + ".json").read_text(encoding="utf-8"))
    if not meta.get("complete") or file_hash(path) != meta["checkpoint_sha256"]:
        raise ValueError("CHECKPOINT_CHANGED_OR_INCOMPLETE")
    validate_checkpoint_metadata(meta, config, corpus_hash, resource_hash, resume)
    # Only local, explicitly hashed project checkpoints are accepted. RNG includes Python/NumPy objects.
    payload = torch.load(path, map_location="cpu", weights_only=False)
    if model is not None:
        model.load_state_dict(payload.get("model", payload.get("address_tagger_model")), strict=True)
    if resume:
        if optimizer is None or payload.get("optimizer") is None or payload.get("scheduler") is None or scheduler is None:
            raise ValueError("MISSING_OPTIMIZER_SCHEDULER_FOR_RESUME")
        optimizer.load_state_dict(payload["optimizer"])
        scheduler.load_state_dict(payload["scheduler"])
        restore_rng(payload["rng"])
    return payload, meta
