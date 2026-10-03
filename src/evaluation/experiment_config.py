"""Declared, hashed resources shared by the three Sprint 3 configurations."""

from pathlib import Path

from src.evaluation.dev_runner import ROOT, file_hash


def resource(path: Path, role: str) -> dict:
    return {"path": path.resolve().relative_to(ROOT).as_posix(), "sha256": file_hash(path), "role": role}


def heur_config(run_id: str, threshold: float, seed: int = 42, gazetteer_dir=None, rule_version="v3") -> dict:
    from src.evaluation.adapters.heur_jw_adapter import HeuristicJaroWinklerAdapter
    gaz = (ROOT / gazetteer_dir).resolve() if gazetteer_dir else ROOT / "data/processed/gazetteer/s3_v2"
    adapter = HeuristicJaroWinklerAdapter
    if rule_version == "v4":
        from src.evaluation.adapters.heur_jw_followup import HeuristicJaroWinklerFollowup
        adapter = HeuristicJaroWinklerFollowup
    elif rule_version != "v3":
        raise ValueError("UNKNOWN_HEUR_RULE_VERSION")
    resources = {name: resource(gaz/name, "gazetteer") for name in (
        "entities.csv", "aliases.csv", "edges.csv", "non_atomic_transitions.csv", "manifest.json")}
    resources["rules"] = resource(ROOT / "src/evaluation/adapters/heur_jw_adapter.py", "rules")
    if rule_version == "v4":
        for relative in ("src/evaluation/adapters/heur_jw_followup.py", "src/data/nso_dual_snapshot.py", "src/data/administrative_code_verifier.py"):
            resources[relative] = resource(ROOT / relative, "rules")
        resources["code_evidence"] = resource(gaz / "code_evidence.csv", "gazetteer")
    return {"model_id": "HEUR-JW", "run_id": run_id, "seed": seed,
        "supported_labels": HeuristicJaroWinklerAdapter.SUPPORTED_LABELS, "t1_implemented": True,
        "adapter_factory": adapter.__module__ + ":" + adapter.__name__,
        "adapter_kwargs": {"gazetteer_dir": gaz.relative_to(ROOT).as_posix(), "similarity_threshold": threshold,
                           "ambiguity_margin": 0.02, "temporal_policy": "dual_snapshot"},
        "resources": resources, "candidate_blocking": "same first Unicode character; core-length ratio >=0.60; JW>=0.80",
        "device": "cpu", "rule_version": adapter.RULE_VERSION}


def crf_config(run_id: str, checkpoint: Path, metadata: Path, seed: int = 42) -> dict:
    from src.evaluation.schema import SPAN11_LABELS
    return {"model_id": "CRF-INDEP", "run_id": run_id, "seed": seed, "supported_labels": list(SPAN11_LABELS),
        "t1_implemented": False, "device": "cpu", "adapter_factory": "src.evaluation.adapters.crf_adapter:IndependentCRFAdapter",
        "adapter_kwargs": {"checkpoint_path": checkpoint.resolve().relative_to(ROOT).as_posix(),
                           "metadata_path": metadata.resolve().relative_to(ROOT).as_posix()},
        "resources": {"checkpoint": resource(checkpoint, "checkpoint"), "metadata": resource(metadata, "rules"),
                      "features": resource(ROOT / "src/evaluation/span_features.py", "tokenizer"),
                      "adapter": resource(ROOT / "src/evaluation/adapters/crf_adapter.py", "rules")}}


def modeling_config(run_id: str, training_config: dict, checkpoint: Path,
                    resource_lock_path: Path, decoder_policy_path: Path | None = None) -> dict:
    """Bind all actual local files for new neural adapters; no placeholder hashes."""
    import json
    from src.modeling.resources import validate_resource_lock
    from src.modeling.artifacts import code_hashes
    model_id = training_config["model_id"]
    lock = validate_resource_lock(resource_lock_path, model_id)
    adapters = {"DP-FT-FT": "deepparse_finetuned_adapter:DeepparseFinetunedAdapter",
                "PHOBERT-CRF": "phobert_crf_adapter:PhoBERTCRFAdapter",
                "PROPOSED-DYN": "proposed_dynamic_adapter:ProposedDynamicAdapter",
                "PROPOSED-NO-CONSTRAINT": "proposed_dynamic_adapter:ProposedDynamicAdapter"}
    resources = {"checkpoint": resource(checkpoint, "checkpoint"),
                 "checkpoint_metadata": resource(checkpoint.with_suffix(checkpoint.suffix + ".json"), "rules"),
                 "resource_lock": resource(resource_lock_path, "rules")}
    for name in code_hashes():
        resources["code:" + name] = resource(ROOT / name, "rules")
    for component, entry in lock["components"].items():
        role = "segmenter" if component == "segmenter" else "tokenizer" if component == "tokenizer" else "checkpoint"
        for relative in entry["files"]:
            resources[component + ":" + relative] = resource(ROOT / entry["path"] / relative, role)
    config = {"model_id": model_id, "run_id": run_id, "seed": training_config["seed"],
              "supported_labels": training_config["supported_labels"], "t1_implemented": training_config["t1_implemented"],
              "adapter_factory": "src.evaluation.adapters." + adapters[model_id],
              "adapter_kwargs": {"checkpoint_path": checkpoint.resolve().relative_to(ROOT).as_posix(),
                    "resource_lock_path": resource_lock_path.resolve().relative_to(ROOT).as_posix(), "config": training_config},
              "resources": resources, "device": training_config["device"], "purpose": training_config["purpose"],
              "pretrained": training_config["pretrained"], "processor_version": training_config["processor_version"],
              "label_map": training_config["label_map"]}
    # Checkpoint metadata contains only training contract; never attach gold rows to inference config.
    meta = json.loads(checkpoint.with_suffix(checkpoint.suffix + ".json").read_text(encoding="utf-8"))
    config["checkpoint_selection_epoch"] = meta["epoch"]
    if decoder_policy_path:
        from src.modeling.calibration import load_decoder_policy
        if not training_config["t1_implemented"]:
            raise ValueError("T1_POLICY_FOR_T0_ONLY_MODEL_FORBIDDEN")
        config["adapter_kwargs"]["decoder_policy"] = load_decoder_policy(decoder_policy_path, checkpoint, training_config)
        config["resources"]["decoder_policy"] = resource(decoder_policy_path, "rules")
        config["resources"]["calibration_manifest"] = resource(decoder_policy_path.with_name("calibration_manifest.json"), "rules")
    return config
