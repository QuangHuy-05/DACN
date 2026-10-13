"""Locked development budgets and deterministic checkpoint selection."""

import copy
import hashlib
import json
from pathlib import Path

from src.evaluation.schema import SPAN11_LABELS
from src.modeling.alignment import DP_PROCESSOR_VERSION, PHOBERT_PROCESSOR_VERSION
from src.modeling.datasets import CORPUS_MANIFEST_SHA256
from src.modeling.labels import label_metadata

PROTOCOL_VERSION = "s3-training-v1"
PROTOCOL_LOCK_PATH = Path(__file__).resolve().parents[2] / "configs/modeling/sprint03/protocol_lock_v1.json"
MODEL_PROCESSORS = {"DP-FT-FT": DP_PROCESSOR_VERSION, "PHOBERT-CRF": PHOBERT_PROCESSOR_VERSION,
                    "PROPOSED-DYN": PHOBERT_PROCESSOR_VERSION, "PROPOSED-NO-CONSTRAINT": PHOBERT_PROCESSOR_VERSION}


def canonical_hash(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def validate_training_config(config: dict) -> None:
    model = config.get("model_id")
    if model not in MODEL_PROCESSORS or config.get("protocol_version") != PROTOCOL_VERSION:
        raise ValueError("UNKNOWN_MODEL_OR_PROTOCOL")
    if config.get("processor_version") != MODEL_PROCESSORS[model]:
        raise ValueError("PROCESSOR_MISMATCH")
    if config.get("label_map") != label_metadata():
        raise ValueError("LABEL_MAP_MISMATCH")
    if config.get("corpus_manifest_sha256") != CORPUS_MANIFEST_SHA256:
        raise ValueError("BLOCKED_INPUT_HASH")
    if config.get("selection_split") != "dev" or config.get("training_split") != "train":
        raise ValueError("ONLY_FIXED_TRAIN_DEV_ALLOWED")
    if config.get("supported_labels") != list(SPAN11_LABELS):
        raise ValueError("ALL_SCHEMA_LABELS_REQUIRED")
    if config.get("seed") not in (42, 1337, 2025):
        raise ValueError("SEED_OUTSIDE_LOCKED_PROTOCOL")
    if config.get("long_sequence_policy") != "reject_no_truncation":
        raise ValueError("UNSUPPORTED_LONG_SEQUENCE_POLICY")
    candidates = config.get("candidates", [])
    if len(candidates) != 2 or [row.get("id") for row in candidates] != ["c01", "c02"]:
        raise ValueError("CANDIDATE_BUDGET_MISMATCH")
    if "candidate" in config and config["candidate"] not in candidates:
        raise ValueError("CANDIDATE_OUTSIDE_LOCKED_SEARCH")
    if config.get("max_epochs") != 20 or config.get("patience") != 5:
        raise ValueError("EPOCH_BUDGET_MISMATCH")
    if config.get("effective_batch_size") != 16:
        raise ValueError("BATCH_BUDGET_MISMATCH")
    if model == "DP-FT-FT":
        if config.get("seq2seq_params") is not None or config.get("embedding") != "fasttext-full":
            raise ValueError("PRETRAINED_FASTTEXT_ARCHITECTURE_REQUIRED")
        if [row.get("learning_rate") for row in candidates] != [0.01, 0.005]:
            raise ValueError("DP_SEARCH_MISMATCH")
    else:
        if [row.get("encoder_lr") for row in candidates] != [2e-5, 5e-5]:
            raise ValueError("ENCODER_SEARCH_MISMATCH")
        if any(row.get("head_lr") != 0.001 for row in candidates):
            raise ValueError("HEAD_SEARCH_MISMATCH")
        if config.get("max_encoder_tokens") != 256 or config.get("micro_batch_size") != 4:
            raise ValueError("ENCODER_OR_BATCH_POLICY_MISMATCH")
        if config.get("amp") is not False or config.get("consistency_weight") != 0:
            raise ValueError("UNIMPLEMENTED_LOSS_OR_AMP_POLICY")
        expected = {"optimizer": "AdamW", "weight_decay": 0.01, "gradient_clip": 1.0,
                    "warmup_fraction": 0.1, "scheduler": "linear_warmup_linear_decay", "dropout": 0.1,
                    "gradient_accumulation_steps": 4, "deterministic": True}
        if any(config.get(key) != value for key, value in expected.items()):
            raise ValueError("OPTIMIZER_OR_TRAINING_POLICY_MISMATCH")
        expected_t1 = model.startswith("PROPOSED")
        if config.get("t1_implemented") is not expected_t1:
            raise ValueError("TASK_HEAD_MISMATCH")
        if config.get("t1_loss_weight") != (0.5 if expected_t1 else 0.0):
            raise ValueError("LOSS_WEIGHT_MISMATCH")
        policy = config.get("structural_policy", {})
        if policy != {"version": "confidence_bio_constraint_v1", "threshold": 0.8,
                      "margin": 0.2, "enabled": model == "PROPOSED-DYN"}:
            raise ValueError("STRUCTURAL_POLICY_MISMATCH")


def candidate_config(config: dict, candidate_id: str) -> dict:
    validate_training_config(config)
    candidate = next((row for row in config["candidates"] if row["id"] == candidate_id), None)
    if candidate is None:
        raise ValueError("Unknown candidate")
    return {**copy.deepcopy(config), "candidate": copy.deepcopy(candidate)}


def selection_key(metrics: dict, epoch: int, candidate_index: int = 0) -> tuple:
    t0 = metrics["t0_exact_span"]
    # Derive full-precision F1 from counts, rather than rounded presentation fields.
    def f1(row):
        return 2 * row["tp"] / (2 * row["tp"] + row["fp"] + row["fn"]) if (2 * row["tp"] + row["fp"] + row["fn"]) else 0.0
    micro = f1({key: t0["micro"]["total_" + key] for key in ("tp", "fp", "fn")})
    supported = [f1(value) for value in t0["per_label"].values() if value.get("support", value["tp"] + value["fn"]) > 0]
    return micro, sum(supported) / len(supported) if supported else 0.0, -epoch, -candidate_index


def load_config(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    validate_training_config(config)
    if not PROTOCOL_LOCK_PATH.is_file():
        raise ValueError("PROTOCOL_LOCK_MISSING: restore the approved lock before running")
    lock = json.loads(PROTOCOL_LOCK_PATH.read_text(encoding="utf-8"))
    if lock.get("version") != PROTOCOL_VERSION:
        raise ValueError("PROTOCOL_LOCK_VERSION_MISMATCH")
    known = lock["config_canonical_sha256"]
    if canonical_hash(config) not in known.values():
        raise ValueError("CONFIG_CHANGED_AFTER_PROTOCOL_LOCK: publish a reviewed new protocol before changing config")
    return config
