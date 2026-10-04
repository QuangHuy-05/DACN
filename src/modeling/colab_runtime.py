"""Future Colab execution with a real GPU smoke gate; imports do not train."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import threading

from src.evaluation.dev_runner import ROOT, file_hash, write_json
from src.modeling.datasets import load_corpus
from src.modeling.hardware_profile import apply_hardware_profile
from src.modeling.protocol import load_config, candidate_config, selection_key
from src.modeling.resources import preflight, validate_resource_lock, load_phobert_processor
from src.modeling.kaggle_remote import audit_alignment, one_model_smoke

CORPUS = ROOT / "data/processed/annotation/sprint03/corpus_train_dev_v2"
LOCK = ROOT / "data/interim/modeling/sprint03/task_01_06_20261003_v1/resource_lock_local_v1.json"
PROFILE = ROOT / "configs/colab/sprint03/cuda128_profile_v1.json"
CONFIGS = {"PHOBERT-CRF": "phobert_crf_v1.json", "PROPOSED-DYN": "proposed_dyn_v1.json"}


def checked_config(model_id, candidate="c01"):
    if model_id not in CONFIGS:
        raise ValueError("MODEL_REQUIRES_SEPARATE_CLEARED_RESOURCE_GATE")
    return apply_hardware_profile(candidate_config(load_config(
        ROOT / "configs/modeling/sprint03" / CONFIGS[model_id]), candidate), PROFILE)


def evidence_identity():
    return {"corpus_manifest_sha256": file_hash(CORPUS / "manifest.json"),
        "resource_lock_sha256": file_hash(LOCK), "hardware_profile_sha256": file_hash(PROFILE),
        "protocol_lock_sha256": file_hash(ROOT / "configs/modeling/sprint03/protocol_lock_v1.json"),
        "source_sha256": file_hash(Path(__file__)),
        "smoke_implementation_sha256": file_hash(ROOT / "src/modeling/kaggle_remote.py")}


def validate_smoke_evidence(path):
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    if report.get("status") != "SMOKE_PASS" or report.get("full_training_performed") is not False:
        raise ValueError("FULL_TRAINING_REQUIRES_REAL_GPU_SMOKE")
    if report.get("identity") != evidence_identity() or set(report.get("models", {})) != set(CONFIGS):
        raise ValueError("SMOKE_IDENTITY_OR_MODEL_COVERAGE_MISMATCH")
    if report.get("alignment", {}).get("train") != 240 or report["alignment"].get("dev") != 60:
        raise ValueError("SMOKE_ALIGNMENT_INCOMPLETE")
    for row in report["models"].values():
        if (row.get("status") != "PRETRAINED_OPTIMIZER_CHECKPOINT_PASS" or row.get("pretrained") is not True
                or row.get("device") != "cuda:0" or row.get("optimizer_steps") != 1
                or row.get("checkpoint_reload") != "PASS"):
            raise ValueError("FIXTURE_CPU_OR_PARTIAL_SMOKE_CANNOT_OPEN_TRAINING")
    return report


def run_smoke(output_dir, mode="smoke"):
    if mode not in {"preflight", "smoke"}:
        raise ValueError("UNKNOWN_SMOKE_MODE")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    report = {"status": "PREFLIGHT_PENDING", "identity": evidence_identity(), "mode": mode,
              "full_training_performed": False, "test100": "NOT_INCLUDED_NOT_READ", "models": {}}
    try:
        configs = {name: checked_config(name) for name in CONFIGS}
        checks = {name: preflight(config, LOCK) for name, config in configs.items()}
        write_json(output / "preflight.json", checks)
        blockers = {name: row["blockers"] for name, row in checks.items() if row["blockers"]}
        if blockers:
            report.update(status="BLOCKED_PREFLIGHT", blockers=blockers)
            return report
        manifest, splits = load_corpus(CORPUS)
        lock = validate_resource_lock(LOCK, "PHOBERT-CRF")
        processor = load_phobert_processor(configs["PHOBERT-CRF"], lock)
        examples, report["alignment"] = audit_alignment(processor, manifest, splits, output)
        if mode == "preflight":
            report["status"] = "PREFLIGHT_PASS_GPU_SMOKE_NOT_EXECUTED"
            return report
        for name, config in configs.items():
            folder = output / name.lower().replace("-", "_")
            folder.mkdir()
            report["models"][name] = one_model_smoke(config, lock, processor, examples["train"], manifest, folder)
            write_json(output / "smoke_report.json", report)
        report["status"] = "SMOKE_PASS"
        return report
    except Exception as error:
        report.update(status="SMOKE_FAILED", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        write_json(output / "smoke_report.json", report)


def backup_run(run, backup_directory):
    """Copy immutable files and atomic checkpoints, verifying every copied file."""
    if backup_directory is None:
        raise ValueError("PERSISTENT_BACKUP_DIRECTORY_REQUIRED")
    destination = Path(backup_directory) / run.name
    destination.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for source in run.rglob("*"):
        if not source.is_file() or source.name.endswith(".tmp"):
            continue
        relative = source.relative_to(run)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        # A live last checkpoint can be replaced atomically. Retry a stable copy.
        for _ in range(3):
            before = file_hash(source)
            temporary = target.with_name(target.name + ".backup_tmp")
            shutil.copyfile(source, temporary)
            if before == file_hash(temporary) == file_hash(source):
                temporary.replace(target)
                hashes[relative.as_posix()] = before
                break
        else:
            raise RuntimeError("BACKUP_SOURCE_CHANGED_DURING_COPY:" + str(relative))
    write_json(destination / "backup_manifest.json", {"run_id": run.name, "files": hashes})
    return hashes


def run_candidate(output_dir, smoke_evidence, model_id, candidate="c01", *, enable_training=False,
                  backup_directory=None, resume_from=None):
    if not enable_training:
        raise ValueError("FULL_TRAINING_DISABLED_BY_DEFAULT")
    validate_smoke_evidence(smoke_evidence)
    checked_config(model_id, candidate)
    if backup_directory is None:
        raise ValueError("PERSISTENT_BACKUP_DIRECTORY_REQUIRED")
    backup_directory = Path(backup_directory).resolve()
    if backup_directory.is_relative_to(Path("/content").resolve()):
        drive_mount = Path("/content/drive")
        if not drive_mount.is_mount() or not backup_directory.is_relative_to(drive_mount.resolve()):
            raise ValueError("BACKUP_MUST_SURVIVE_EPHEMERAL_CONTENT_OR_USE_VERIFIED_DRIVE_MOUNT")
    backup_directory.mkdir(parents=True, exist_ok=True)
    output = Path(output_dir).resolve()
    allowed = ROOT / "data/processed/evaluation/sprint03"
    if not output.is_relative_to(allowed) or output == allowed or output.exists():
        raise ValueError("NEW_EVALUATION_RUN_DIRECTORY_REQUIRED")
    module = "scripts.32_train_phobert_crf" if model_id == "PHOBERT-CRF" else "scripts.33_train_proposed_dynamic"
    common = ["--resources", str(LOCK), "--hardware-profile", str(PROFILE), "--candidate", candidate]
    command = [sys.executable, "-m", module]
    train = command + ["train", "--output-dir", str(output), "--run-id", output.name] + common
    if resume_from:
        train += ["--resume-from", str(resume_from)]
    stop, backup_errors = threading.Event(), []
    def periodic_backup():
        while not stop.wait(300):
            try:
                backup_run(output, backup_directory)
            except Exception as error:
                backup_errors.append(str(error))
    worker = threading.Thread(target=periodic_backup, daemon=True)
    worker.start()
    try:
        subprocess.run(train, cwd=ROOT, check=True)
        dev = output.with_name(output.name + "_dev")
        infer = command + ["infer", "--checkpoint", str(output / "checkpoints/best.pt"),
                           "--output-dir", str(dev), "--inference-only"] + common
        if model_id == "PROPOSED-DYN":
            infer += ["--config", "configs/modeling/sprint03/proposed_no_constraint_v1.json"]
        subprocess.run(infer, cwd=ROOT, check=True)
        subprocess.run(command + ["score", "--source-run", str(dev)] + common, cwd=ROOT, check=True)
        backup_run(dev, backup_directory)
    finally:
        stop.set()
        worker.join(timeout=10)
        if output.exists():
            backup_run(output, backup_directory)
    if backup_errors:
        raise RuntimeError("PERIODIC_BACKUP_FAILED:" + ";".join(backup_errors))
    return {"status": "CANDIDATE_TRAIN_DEV_COMPLETE", "dev_run": str(dev), "test100": "NOT_READ_NOT_USED"}


def select_and_lock(model_id, dev_runs, output_dir):
    """Select c01/c02 on dev; calibrate/ablate only the chosen proposed checkpoint."""
    from src.evaluation.experiment_config import modeling_config
    from src.evaluation.test_runner import freeze_dev_selection, derive_ablation_lock, _verified_dev_run
    from src.modeling.calibration import calibrate_frozen_dev
    output = Path(output_dir)
    if output.exists():
        raise FileExistsError(output)
    if model_id not in CONFIGS or len(dev_runs) != 2:
        raise ValueError("BOTH_LOCKED_NEURAL_CANDIDATES_REQUIRED")
    candidates = []
    source_hash = file_hash(CORPUS / "manifest.json")
    for folder in map(Path, dev_runs):
        run, config, metrics = _verified_dev_run(folder, source_hash)
        expected = "PHOBERT-CRF" if model_id == "PHOBERT-CRF" else "PROPOSED-NO-CONSTRAINT"
        if run["model_id"] != expected:
            raise ValueError("DEV_SELECTION_REQUIRES_UNCONSTRAINED_PROPOSED")
        inner = config["adapter_kwargs"]["config"]
        index = {"c01": 0, "c02": 1}[inner["candidate"]["id"]]
        candidates.append((selection_key(metrics, config["checkpoint_selection_epoch"], index), folder, config))
    if {row[2]["adapter_kwargs"]["config"]["candidate"]["id"] for row in candidates} != {"c01", "c02"}:
        raise ValueError("CANDIDATE_COVERAGE_INCOMPLETE")
    _, selected, selected_config = max(candidates, key=lambda row: row[0])
    output.mkdir(parents=True)
    checkpoint = ROOT / selected_config["resources"]["checkpoint"]["path"]
    inner = checked_config(model_id, selected_config["adapter_kwargs"]["config"]["candidate"]["id"])
    policy_path = None
    if model_id == "PROPOSED-DYN":
        calibrate_frozen_dev(selected, CORPUS, output / "calibration")
        policy_path = output / "calibration/decoder_policy.json"
    final_config = modeling_config(output.name + "_final_test", inner, checkpoint, LOCK, policy_path)
    write_json(output / "final_model_config.json", final_config)
    freeze_dev_selection(output / "final_model_config.json", dev_runs, CORPUS / "manifest.json", output / "selection_lock.json")
    if model_id == "PROPOSED-DYN":
        ablation_inner = apply_hardware_profile(candidate_config(load_config(
            ROOT / "configs/modeling/sprint03/proposed_no_constraint_v1.json"), inner["candidate"]["id"]), PROFILE)
        ablation = modeling_config(output.name + "_ablation_test", ablation_inner, checkpoint, LOCK, policy_path)
        write_json(output / "ablation_model_config.json", ablation)
        derive_ablation_lock(output / "selection_lock.json", output / "final_model_config.json",
                             output / "ablation_model_config.json", output / "ablation_selection_lock.json")
        # Dev on/off comparison uses precisely this checkpoint and calibrated policy.
        module = [sys.executable, "-m", "scripts.33_train_proposed_dynamic"]
        for variant in ("proposed_dyn_v1.json", "proposed_no_constraint_v1.json"):
            target = ROOT / "data/processed/evaluation/sprint03" / (output.name + "_dev_" + variant[:-5])
            common = ["--resources", str(LOCK), "--hardware-profile", str(PROFILE), "--candidate", inner["candidate"]["id"],
                      "--config", "configs/modeling/sprint03/" + variant]
            subprocess.run(module + ["infer", "--checkpoint", str(checkpoint), "--decoder-policy", str(policy_path),
                "--output-dir", str(target), "--inference-only"] + common, cwd=ROOT, check=True)
            subprocess.run(module + ["score", "--source-run", str(target)] + common, cwd=ROOT, check=True)
    result = {"status": "DEV_SELECTION_FROZEN", "selected_dev_run": selected.relative_to(ROOT).as_posix(),
              "checkpoint_sha256": file_hash(checkpoint), "stability_seeds": "NOT_EXECUTED", "test100": "NOT_READ_NOT_USED"}
    write_json(output / "selection_report.json", result)
    return result
