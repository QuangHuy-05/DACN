"""Final-test inference gate and separate frozen scoring; fixtures are explicit.

No test annotation is available to adapter construction or parsing. Selection
locks are created from completed dev runs, not from test results.
"""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path

from src.data.test_corpus_release import APPROVED_STATUS
from src.evaluation.dev_runner import (ROOT, file_hash, load_predictions, read_jsonl,
    resource_manifest, run_text_inference, validate_dev_samples, write_json, write_jsonl)
from src.evaluation.schema import SPAN11_LABELS, CharacterSpan
from src.evaluation.span_scorer import compute_exact_span_metrics, evaluate_single_sample_spans, validate_span_integrity
from src.modeling.protocol import selection_key

MODEL_IDS = {"HEUR-JW", "DP-ZS-FT", "DP-FT-FT", "CRF-INDEP", "PHOBERT-CRF",
             "PROPOSED-DYN", "PROPOSED-NO-CONSTRAINT"}
NEURAL_IDS = {"DP-FT-FT", "PHOBERT-CRF", "PROPOSED-DYN"}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def config_identity(config):
    content = json.loads(json.dumps({k: v for k, v in config.items() if k != "run_id"}))
    content.get("adapter_kwargs", {}).get("config", {}).pop("run_id", None)
    return hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def code_identity():
    return {p.relative_to(ROOT).as_posix(): file_hash(p) for p in (ROOT / "src").rglob("*.py")
            if "__pycache__" not in p.parts}


def validate_test_config(config):
    if config.get("model_id") not in MODEL_IDS:
        raise ValueError("Unknown final-test model")
    run_id = config.get("run_id")
    if (not isinstance(run_id, str) or "test" not in run_id.casefold() or
            Path(run_id).name != run_id or any(c in run_id for c in ("/", "\\"))):
        raise ValueError("run_id must identify a new test run")
    labels = config.get("supported_labels")
    if (type(config.get("seed")) is not int or not isinstance(labels, list) or not labels or
            len(set(labels)) != len(labels) or set(labels) - set(SPAN11_LABELS) or
            not isinstance(config.get("adapter_kwargs", {}), dict)):
        raise ValueError("Invalid seed/supported_labels/adapter kwargs")


def load_test_input(input_path, corpus_manifest_path, *, fixture=False):
    manifest = read_json(corpus_manifest_path)
    if manifest.get("status") != APPROVED_STATUS:
        raise ValueError("TEST_RELEASE_NOT_APPROVED")
    if manifest.get("sample_counts", {}).get("test") != 100 and not fixture:
        raise ValueError("FINAL_TEST_MUST_HAVE_100")
    if manifest.get("output_sha256", {}).get("test_input.jsonl") != file_hash(Path(input_path)):
        raise ValueError("TEST_INPUT_HASH_CHANGED")
    samples = read_jsonl(Path(input_path))
    validate_dev_samples(samples)
    if len(samples) != manifest["sample_counts"]["test"]:
        raise ValueError("TEST_INPUT_COUNT_CHANGED")
    return manifest, samples


def check_selection_lock(lock_path, config, *, fixture=False):
    lock = read_json(lock_path)
    if (lock.get("status") != "DEV_SELECTION_FROZEN" or lock.get("selection_split") != "dev" or
            lock.get("model_id") != config["model_id"] or
            lock.get("config_identity_sha256") != config_identity(config)):
        raise ValueError("FINAL_SELECTION_LOCK_PENDING_OR_CHANGED")
    if lock.get("experiment_kind") == "fixture" and not fixture:
        raise ValueError("FIXTURE_LOCK_CANNOT_OPEN_REAL_TEST")
    resources = resource_manifest(config)
    if resources != lock.get("resources"):
        raise ValueError("SELECTED_RESOURCES_CHANGED")
    sources = lock.get("dev_evidence", {})
    if not sources or not lock.get("dev_corpus_manifest_sha256"):
        raise ValueError("DEV_SELECTION_EVIDENCE_MISSING")
    for name, digest in sources.items():
        path = ROOT / name
        if not path.is_file() or file_hash(path) != digest:
            raise ValueError("DEV_SELECTION_EVIDENCE_CHANGED:" + name)
    for name, digest in lock.get("code_sha256", {}).items():
        if file_hash(ROOT / name) != digest:
            raise ValueError("SELECTED_CODE_CHANGED:" + name)
    return lock


def _verified_dev_run(run_dir, source_manifest_sha256):
    run_dir = Path(run_dir)
    run, scoring = read_json(run_dir / "run_manifest.json"), read_json(run_dir / "scoring_manifest.json")
    if (run.get("split") != "dev" or run.get("track") != "T0_T1_DEV" or
            scoring.get("split") != "dev" or
            scoring.get("corpus_manifest_sha256") != source_manifest_sha256 or
            run.get("inputs", {}).get("corpus_manifest_sha256") != source_manifest_sha256):
        raise ValueError("SELECTION_REQUIRES_COMPLETED_DEV_RUN")
    for manifest in (run, scoring):
        for name, digest in manifest.get("output_sha256", {}).items():
            if file_hash(run_dir / name) != digest:
                raise ValueError("DEV_EVIDENCE_HASH_CHANGED")
    if scoring.get("prediction_sha256") != file_hash(run_dir / "predictions.jsonl"):
        raise ValueError("DEV_PREDICTIONS_CHANGED")
    config = read_json(run_dir / "model_config.json")
    if resource_manifest(config) != run.get("resources", {}):
        raise ValueError("DEV_SELECTED_RESOURCE_HASH_CHANGED")
    return run, config, read_json(run_dir / "metrics.json")


def freeze_dev_selection(config_path, dev_runs, source_manifest_path, output_lock, *, fixture=False):
    """Rank declared completed dev runs; never reads a test input or gold file."""
    output_lock = Path(output_lock)
    if output_lock.exists():
        raise FileExistsError(output_lock)
    config = read_json(config_path)
    validate_test_config(config)
    source_hash = file_hash(Path(source_manifest_path))
    if not fixture:
        from src.modeling.datasets import CORPUS_MANIFEST_SHA256
        if source_hash != CORPUS_MANIFEST_SHA256:
            raise ValueError("DEV_SOURCE_IS_NOT_PINNED_RELEASE")
    if read_json(source_manifest_path).get("status") != "TRAIN_DEV_APPROVED_TEST_PENDING":
        raise ValueError("APPROVED_DEV_SOURCE_REQUIRED")
    rows, evidence = [], {}
    for index, folder in enumerate(dev_runs):
        run, dev_config, metric = _verified_dev_run(folder, source_hash)
        accepted_model = ("PROPOSED-NO-CONSTRAINT" if config["model_id"] == "PROPOSED-DYN" else config["model_id"])
        if run["model_id"] != accepted_model:
            raise ValueError("DEV_MODEL_MISMATCH")
        candidate = dev_config.get("adapter_kwargs", {}).get("config", {}).get("candidate", {}).get("id")
        candidate_index = {"c01": 0, "c02": 1}.get(candidate, index)
        epoch = dev_config.get("checkpoint_selection_epoch", 10**9)
        key = selection_key(metric, epoch, candidate_index)
        rule = "full11 micro F1, gold-supported macro F1, earlier epoch, earlier c01/c02 candidate"
        if config["model_id"] == "HEUR-JW":
            key = (key[0], dev_config["adapter_kwargs"]["similarity_threshold"])
            rule = "frozen HEUR sweep: highest full11 dev micro F1, higher threshold"
        elif config["model_id"] == "CRF-INDEP":
            metadata = read_json(ROOT / dev_config["resources"]["metadata"]["path"])
            key = (key[0], -metadata["context"], metadata["parameters"]["c2"], metadata["parameters"]["c1"])
            rule = "frozen CRF grid: highest full11 dev micro F1, smaller context, higher c2, higher c1"
        rows.append((key, Path(folder), dev_config))
        for name in ("run_manifest.json", "scoring_manifest.json", "model_config.json", "metrics.json", "predictions.jsonl"):
            path = Path(folder) / name
            evidence[path.resolve().relative_to(ROOT.resolve()).as_posix()] = file_hash(path)
    if not rows:
        raise ValueError("DEV_CANDIDATE_RUNS_REQUIRED")
    if config["model_id"] in NEURAL_IDS:
        candidate_ids = {row[2].get("adapter_kwargs", {}).get("config", {}).get("candidate", {}).get("id") for row in rows}
        if len(rows) != 2 or candidate_ids != {"c01", "c02"}:
            raise ValueError("NEURAL_SELECTION_REQUIRES_BOTH_LOCKED_CANDIDATES")
    best = max(rows, key=lambda row: row[0])
    if config["model_id"] == "PROPOSED-DYN":
        selected_resources = resource_manifest(best[2])
        current_resources = resource_manifest(config)
        if {k: v for k, v in current_resources.items() if k not in {"decoder_policy", "calibration_manifest"}} != {
                k: v for k, v in selected_resources.items() if k not in {"decoder_policy", "calibration_manifest"}}:
            raise ValueError("PROPOSED_CHECKPOINT_NOT_SELECTED_ON_UNCONSTRAINED_DEV")
        if "decoder_policy" not in current_resources or "calibration_manifest" not in current_resources:
            raise ValueError("PROPOSED_CALIBRATION_LOCK_REQUIRED")
        policy = read_json(ROOT / current_resources["decoder_policy"]["path"])
        if policy.get("selection_split") != "dev" or policy.get("checkpoint_sha256") != current_resources["checkpoint"]["sha256"]:
            raise ValueError("CALIBRATION_NOT_BOUND_TO_SELECTED_DEV_CHECKPOINT")
        from src.modeling.calibration import load_decoder_policy
        decoder = load_decoder_policy(ROOT / current_resources["decoder_policy"]["path"],
            ROOT / current_resources["checkpoint"]["path"], config["adapter_kwargs"]["config"])
        if config["adapter_kwargs"].get("decoder_policy") != decoder:
            raise ValueError("EMBEDDED_DECODER_POLICY_CHANGED")
        def neutral_selected(value):
            value = json.loads(json.dumps(value))
            value.pop("run_id", None)
            value["model_id"] = "PROPOSED-DYN"
            inner = value["adapter_kwargs"]["config"]
            inner.pop("run_id", None)
            inner["model_id"] = "PROPOSED-DYN"
            inner["structural_policy"]["enabled"] = True
            value["adapter_kwargs"].pop("decoder_policy", None)
            value["resources"] = {k: v for k, v in value["resources"].items()
                                  if k not in {"decoder_policy", "calibration_manifest"}}
            return value
        if neutral_selected(config) != neutral_selected(best[2]):
            raise ValueError("PROPOSED_CONFIG_CHANGED_AFTER_DEV_SELECTION")
    elif config_identity(config) != config_identity(best[2]):
        raise ValueError("CONFIG_IS_NOT_DEV_SELECTED_CANDIDATE")
    lock = {"version": "s3-final-selection-v1", "status": "DEV_SELECTION_FROZEN", "selection_split": "dev",
        "model_id": config["model_id"], "config_identity_sha256": config_identity(config),
        "dev_corpus_manifest_sha256": source_hash, "dev_evidence": evidence,
        "selected_dev_run": best[1].resolve().relative_to(ROOT.resolve()).as_posix(),
        "selection_rule": rule, "experiment_kind": "fixture" if fixture else "development_selection",
        "resources": resource_manifest(config), "code_sha256": code_identity(),
        "created_at": datetime.now(timezone.utc).isoformat(), "test_used_for_selection": False}
    output_lock.parent.mkdir(parents=True, exist_ok=True)
    write_json(output_lock, lock)
    return lock


def derive_ablation_lock(base_lock_path, base_config_path, ablation_config_path, output_lock):
    """Same resources/checkpoint/config; only model identity and constraint differ."""
    base, ablation = read_json(base_config_path), read_json(ablation_config_path)
    check_selection_lock(base_lock_path, base)
    if base["model_id"] != "PROPOSED-DYN" or ablation.get("model_id") != "PROPOSED-NO-CONSTRAINT":
        raise ValueError("ABLATION_MODEL_PAIR_MISMATCH")
    inner = ablation.get("adapter_kwargs", {}).get("config", {})
    if inner.get("structural_policy", {}).get("enabled") is not False:
        raise ValueError("ABLATION_CONSTRAINT_MUST_BE_DISABLED")
    def neutral(value):
        value = json.loads(json.dumps(value))
        value.pop("run_id", None)
        value["model_id"] = "PROPOSED-DYN"
        inner = value.get("adapter_kwargs", {}).get("config", {})
        inner["model_id"] = "PROPOSED-DYN"
        if "structural_policy" in inner:
            inner["structural_policy"]["enabled"] = True
        if "decoder_policy" in value.get("adapter_kwargs", {}):
            value["adapter_kwargs"]["decoder_policy"]["enabled"] = True
        return value
    if neutral(base) != neutral(ablation):
        raise ValueError("ABLATION_MUST_REUSE_SAME_CHECKPOINT_AND_CALIBRATION")
    lock = read_json(base_lock_path)
    lock.update(model_id=ablation["model_id"], config_identity_sha256=config_identity(ablation),
                same_checkpoint_base_lock_sha256=file_hash(Path(base_lock_path)))
    output_lock = Path(output_lock)
    if output_lock.exists():
        raise FileExistsError(output_lock)
    write_json(output_lock, lock)
    return lock


def preflight_test(input_path, manifest_path, config_path, selection_lock_path, *, fixture=False):
    manifest, samples = load_test_input(input_path, manifest_path, fixture=fixture)
    config = read_json(config_path)
    validate_test_config(config)
    lock = check_selection_lock(selection_lock_path, config, fixture=fixture)
    if lock["dev_corpus_manifest_sha256"] != manifest.get("source_train_dev_manifest_sha256"):
        raise ValueError("TEST_AND_DEV_SOURCE_RELEASE_DIFFER")
    return manifest, samples, config, lock


def run_test_inference(input_path, manifest_path, config_path, selection_lock_path, output_dir,
                       *, adapter=None, fixture=False):
    manifest, samples, config, lock = preflight_test(
        input_path, manifest_path, config_path, selection_lock_path, fixture=fixture)
    if adapter is not None and not fixture:
        raise ValueError("ADAPTER_INJECTION_IS_FIXTURE_ONLY")
    if adapter is None:
        factory = config["adapter_factory"]
        if not isinstance(factory, str) or factory.count(":") != 1:
            raise ValueError("adapter_factory must be module:class")
        module, name = factory.split(":")
        adapter = getattr(importlib.import_module(module), name)(**config.get("adapter_kwargs", {}))
    output_dir = Path(output_dir)
    run = run_text_inference(adapter, samples, config, output_dir,
        {"corpus_manifest_sha256": file_hash(Path(manifest_path)),
         "test_input_sha256": file_hash(Path(input_path)), "selection_lock_sha256": file_hash(Path(selection_lock_path))},
        split="test", track="T0_T1_FINAL_TEST")
    run.update(experiment_kind="fixture" if fixture else "final_test", code_sha256=code_identity(),
               selection_lock=lock)
    write_json(output_dir / "selection_lock.json", lock)
    run["output_sha256"]["selection_lock.json"] = file_hash(output_dir / "selection_lock.json")
    write_json(output_dir / "run_manifest.json", run)
    return run


def score_test_predictions(run_dir, gold_path, manifest_path, input_path, *, fixture=False):
    run_dir = Path(run_dir)
    manifest, samples = load_test_input(input_path, manifest_path, fixture=fixture)
    run = read_json(run_dir / "run_manifest.json")
    if run.get("split") != "test" or run.get("track") != "T0_T1_FINAL_TEST":
        raise ValueError("FINAL_TEST_RUN_REQUIRED")
    if run.get("experiment_kind") == "fixture" and not fixture:
        raise ValueError("FIXTURE_RUN_CANNOT_BE_REPORTED_AS_TEST")
    for name, digest in run["output_sha256"].items():
        if file_hash(run_dir / name) != digest:
            raise ValueError("FROZEN_PREDICTION_OR_CONFIG_CHANGED")
    if run.get("code_sha256") != code_identity():
        raise ValueError("INFERENCE_SCORER_CODE_CHANGED")
    if (run["inputs"].get("corpus_manifest_sha256") != file_hash(Path(manifest_path)) or
            run["inputs"].get("test_input_sha256") != file_hash(Path(input_path)) or
            run["inputs"].get("selection_lock_sha256") != file_hash(run_dir / "selection_lock.json")):
        raise ValueError("INFERENCE_SCORING_VERSION_MISMATCH")
    config = read_json(run_dir / "model_config.json")
    check_selection_lock(run_dir / "selection_lock.json", config, fixture=fixture)
    if manifest["output_sha256"].get("test_benchmark_t0.jsonl") != file_hash(Path(gold_path)):
        raise ValueError("GOLD_RELEASE_HASH_CHANGED")
    for name in ("metrics.json", "error_analysis.jsonl", "scoring_manifest.json"):
        if (run_dir / name).exists():
            raise FileExistsError("Scoring artifacts are immutable")
    golds, predictions = read_jsonl(Path(gold_path)), load_predictions(run_dir / "predictions.jsonl")
    expected = {r["sample_id"]: r["text"] for r in samples}
    if (len(golds) != len(expected) or {g["sample_id"]: g["text"] for g in golds} != expected or
            len(predictions) != len(expected) or {p.sample_id: p.raw_text for p in predictions} != expected):
        raise ValueError("MISSING_DUPLICATE_UNKNOWN_OR_TEXT_MISMATCH")
    for gold in golds:
        spans = [CharacterSpan(s["start"], s["end"], s["label"], gold["text"][s["start"]:s["end"]], s["system"]) for s in gold["spans"]]
        if validate_span_integrity(spans, gold["text"]):
            raise ValueError("INVALID_GOLD_SPANS")
    excluded = sorted(set(manifest.get("evaluation_exclusions", {}).get("t1", [])) & set(expected))
    metric = compute_exact_span_metrics(predictions, golds, excluded_t1_sample_ids=excluded)
    supported = set(config["supported_labels"])
    support = sum(len(row["spans"]) for row in golds)
    covered = sum(s["label"] in supported for row in golds for s in row["spans"])
    metric["supported_label_coverage"] = {"labels": sorted(supported), "all_gold_spans": support,
        "gold_spans_in_supported_labels": covered, "fraction": covered/support if support else None,
        "policy": "Unsupported gold remains FN in full11; no samples dropped"}
    subset = [{**g, "spans": [s for s in g["spans"] if s["label"] in supported]} for g in golds]
    metric["t0_supported_subset"] = compute_exact_span_metrics(predictions, subset, excluded_t1_sample_ids=excluded)["t0_exact_span"]
    t1 = metric["t1_address_system"]
    t1["model_task_status"] = "IMPLEMENTED" if config.get("t1_implemented", False) else "NOT_IMPLEMENTED"
    if not config.get("t1_implemented", False):
        for key in ("overall_accuracy", "accepted_accuracy", "macro_f1_all_3_classes"):
            t1[key] = None
        for row in t1["per_class"].values():
            for key in ("precision", "recall", "f1"):
                row[key] = None
    elif not t1["total_evaluated"]:
        t1["overall_accuracy"] = t1["accepted_accuracy"] = None
    metric["latency_ms"] = run["latency_ms"]
    metric["latency_scope"] = {"runtime": run["runtime"], "warmup": "not excluded",
                              "operation": "per-address adapter.parse_spans including preprocessing", "batch_size": 1}
    metric["experiment_kind"] = run["experiment_kind"]
    for label, values in metric["t0_exact_span"]["per_label"].items():
        values["model_supported"] = label in supported
        values["support_status"] = "NO_GOLD_SUPPORT" if not values["support"] else "GOLD_SUPPORTED"
    registry_path = Path(manifest_path).parent / "identity_registry.jsonl"
    if registry_path.is_file():
        if manifest["output_sha256"].get("identity_registry.jsonl") != file_hash(registry_path):
            raise ValueError("SOURCE_REGISTRY_CHANGED")
        registry = {r["sample_id"]: r for r in read_jsonl(registry_path) if r["split"] == "test"}
        if set(registry) != set(expected):
            raise ValueError("SOURCE_REGISTRY_IDENTITY_MISMATCH")
        groups = defaultdict(list)
        for gold in golds:
            groups[registry[gold["sample_id"]].get("source_dataset", "not_recorded")].append(gold)
        metric["t0_by_source_dataset"] = {name: compute_exact_span_metrics(
            [p for p in predictions if p.sample_id in {g["sample_id"] for g in group}], group,
            excluded_t1_sample_ids=[sid for sid in excluded if sid in {g["sample_id"] for g in group}])["t0_exact_span"]
            for name, group in groups.items()}
    by_id = {p.sample_id: p for p in predictions}
    errors = []
    for gold in golds:
        pred = by_id[gold["sample_id"]]
        spans = [CharacterSpan(s["start"], s["end"], s["label"], gold["text"][s["start"]:s["end"]], s["system"]) for s in gold["spans"]]
        diagnostic = evaluate_single_sample_spans(pred.spans, spans, gold["text"])
        errors.append({"sample_id": pred.sample_id, "status": pred.status, "t0": diagnostic,
                       "t1_excluded": pred.sample_id in excluded, "error": pred.error})
    write_json(run_dir / "metrics.json", metric)
    write_jsonl(run_dir / "error_analysis.jsonl", errors)
    write_json(run_dir / "scoring_manifest.json", {"split": "test", "experiment_kind": run["experiment_kind"],
        "corpus_manifest_sha256": file_hash(Path(manifest_path)), "gold_sha256": file_hash(Path(gold_path)),
        "prediction_sha256": file_hash(run_dir / "predictions.jsonl"), "selection_lock_sha256": file_hash(run_dir / "selection_lock.json"),
        "output_sha256": {name: file_hash(run_dir / name) for name in ("metrics.json", "error_analysis.jsonl")}})
    return metric
