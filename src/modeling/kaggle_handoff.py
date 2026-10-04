"""Hash-bound, private Kaggle packages from the frozen train/dev handoff only."""

import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import zipfile

from src.evaluation.dev_runner import ROOT, file_hash, write_json
from src.modeling.datasets import load_corpus
from src.modeling.kaggle_remote import evidence_identity, validate_smoke_evidence

OLD = ROOT / "data/interim/modeling/sprint03/pre_colab_20261003_resume_v1/handoff_v1"
OVERLAY = ("src/modeling/hardware_profile.py", "src/modeling/kaggle_remote.py",
           "scripts/51_run_kaggle_remote.py", "configs/kaggle/sprint03/cuda128_profile_v1.json")


def safe_name(value):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{4,69}", value):
        raise ValueError("INVALID_KAGGLE_SLUG")
    return value


def assert_training_file(name):
    allowed_data = ("data/processed/annotation/sprint03/corpus_train_dev_v2/",
                    "data/interim/modeling/sprint03/task_01_06_20261003_v1/resource_lock_local_v1.json")
    if name.startswith("data/") and not any(name.startswith(prefix) for prefix in allowed_data):
        raise ValueError("DATA_OUTSIDE_APPROVED_TRAIN_DEV_PACKAGE:" + name)
    if any(part in name.lower() for part in ("kaggle.json", ".venv", "__pycache__", "test100_import", "test_benchmark_t0.jsonl")):
        raise ValueError("FORBIDDEN_UPLOAD_MEMBER:" + name)


def build_kaggle_package(output, username, run_id, mode="smoke", enable_full=False,
                         smoke_evidence=None, model="PHOBERT-CRF", candidate="c01"):
    safe_name(run_id)
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", username):
        raise ValueError("INVALID_KAGGLE_USERNAME")
    if mode not in {"smoke", "preflight", "full"}:
        raise ValueError("INVALID_MODE")
    if mode == "full":
        if not enable_full or not smoke_evidence:
            raise ValueError("FULL_TRAINING_REQUIRES_EXPLICIT_FLAG_AND_SMOKE_EVIDENCE")
        validate_smoke_evidence(smoke_evidence)
    if model not in {"PHOBERT-CRF", "PROPOSED-DYN"} or candidate not in {"c01", "c02"}:
        raise ValueError("MODEL_OR_CANDIDATE_NOT_LOCKED")
    if output.exists():
        raise FileExistsError(output)
    output.resolve().relative_to((ROOT / "data/interim/modeling/sprint03").resolve())
    manifest, _ = load_corpus(ROOT / "data/processed/annotation/sprint03/corpus_train_dev_v2")
    old = json.loads((OLD / "handoff_manifest.json").read_text())
    for key in ("code_archive", "resource_archive"):
        if file_hash(ROOT / old[key]["path"]) != old[key]["sha256"]:
            raise ValueError("FROZEN_HANDOFF_ARCHIVE_CHANGED")
    dataset, kernel = output / "dataset", output / "kernel"
    dataset.mkdir(parents=True)
    kernel.mkdir()
    code = dataset / "dacn_code.bundle"
    with zipfile.ZipFile(ROOT / old["code_archive"]["path"]) as source:
        previous = json.loads(source.read("code_bundle_manifest.json"))
        contents = {}
        for name, digest in previous["files"].items():
            assert_training_file(name)
            data = source.read(name)
            if hashlib.sha256(data).hexdigest() != digest:
                raise ValueError("FROZEN_CODE_MEMBER_CHANGED:" + name)
            contents[name] = data
    for name in OVERLAY:
        assert_training_file(name)
        contents[name] = (ROOT / name).read_bytes()
    if mode == "full":
        contents["configs/kaggle/sprint03/approved_smoke.json"] = Path(smoke_evidence).read_bytes()
    code_manifest = {"version": "s3-kaggle-code-v1", "scope": "train240/dev60 only; no test/raw export/credentials",
                     "files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(contents.items())}}
    code_manifest_bytes = json.dumps(code_manifest, ensure_ascii=False, indent=2).encode("utf-8")
    with zipfile.ZipFile(code, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as stream:
        for name, data in contents.items():
            stream.writestr(name, data)
        stream.writestr("code_bundle_manifest.json", code_manifest_bytes)
    resource = dataset / "dacn_resources.bundle"
    try:
        os.link(ROOT / old["resource_archive"]["path"], resource)
        storage = "hardlink_existing_resource_archive"
    except OSError:
        shutil.copyfile(ROOT / old["resource_archive"]["path"], resource)
        storage = "copy_existing_resource_archive"
    with zipfile.ZipFile(resource) as stream:
        resource_manifest_bytes = stream.read("resource_bundle_manifest.json")
    configuration = {"version": "s3-kaggle-job-v1", "run_id": run_id, "mode": mode,
        "allow_full_training": mode == "full" and enable_full, "model": model, "candidate": candidate,
        "identity": evidence_identity(), "train_count": 240, "dev_count": 60, "test100": "NOT_INCLUDED_NOT_READ",
        "archives": {"dacn_code.bundle": {"sha256": file_hash(code), "manifest": "code_bundle_manifest.json",
                    "manifest_sha256": hashlib.sha256(code_manifest_bytes).hexdigest()},
                     "dacn_resources.bundle": {"sha256": file_hash(resource), "manifest": "resource_bundle_manifest.json",
                    "manifest_sha256": hashlib.sha256(resource_manifest_bytes).hexdigest()}}}
    write_json(dataset / "runtime_config.json", configuration)
    dataset_id, kernel_id = username + "/" + run_id + "-resources", username + "/" + run_id
    write_json(dataset / "dataset-metadata.json", {"id": dataset_id, "title": run_id + " resources",
        "licenses": [{"name": "other"}], "description": "Private DACN train/dev only. OSM-derived address corpus with source provenance; project annotations/code; PhoBERT MIT; VnCoreNLP GPL; Temurin OpenJDK notices. Source/license evidence preserved in bundle. No test100, personal customer addresses, raw annotation exports or credentials."})
    template = (ROOT / "notebooks/sprint03/kaggle_entry.py").read_text(encoding="utf-8")
    entry = template.replace("__JOB_CONFIG_JSON__", repr(json.dumps(configuration)))
    ast.parse(entry)
    (kernel / "kaggle_entry.py").write_text(entry, encoding="utf-8")
    write_json(kernel / "kernel-metadata.json", {"id": kernel_id, "title": run_id.replace("-", " "),
        "code_file": "kaggle_entry.py", "language": "python", "kernel_type": "script", "is_private": True,
        "enable_gpu": True, "enable_internet": True, "machine_shape": "NvidiaTeslaT4",
        "dataset_sources": [dataset_id], "competition_sources": [], "kernel_sources": []})
    result = {**configuration, "dataset_id": dataset_id, "kernel_id": kernel_id,
        "resource_storage": storage, "frozen_handoff": old,
        "package_files": {p.relative_to(output).as_posix(): file_hash(p) for p in output.rglob("*") if p.is_file()},
        "upload_bytes": sum(p.stat().st_size for p in dataset.iterdir() if p.is_file()),
        "test100": "NOT_INCLUDED_NOT_READ", "full_training": "ENABLED" if mode == "full" else "DISABLED"}
    write_json(output / "handoff_manifest.json", result)
    validate_package(output)
    return result


def validate_package(directory):
    manifest = json.loads((directory / "handoff_manifest.json").read_text(encoding="utf-8"))
    for name, digest in manifest["package_files"].items():
        file = (directory / name).resolve()
        if not file.is_relative_to(directory.resolve()) or file_hash(file) != digest:
            raise ValueError("KAGGLE_PACKAGE_CHANGED:" + name)
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()}
    if actual != set(manifest["package_files"]) | {"handoff_manifest.json"}:
        raise ValueError("UNDECLARED_KAGGLE_UPLOAD_FILE")
    metadata = json.loads((directory / "kernel/kernel-metadata.json").read_text())
    if metadata.get("is_private") is not True or metadata.get("dataset_sources") != [manifest["dataset_id"]]:
        raise ValueError("PRIVATE_INPUT_POLICY_VIOLATION")
    if manifest["test100"] != "NOT_INCLUDED_NOT_READ":
        raise ValueError("TEST_INPUT_FORBIDDEN")
    if manifest["mode"] == "full":
        with zipfile.ZipFile(directory / "dataset/dacn_code.bundle") as stream:
            report = json.loads(stream.read("configs/kaggle/sprint03/approved_smoke.json"))
        if report.get("status") != "SMOKE_PASS" or report.get("identity") != evidence_identity():
            raise ValueError("FULL_TRAINING_SMOKE_GATE_FAILED")
    return manifest


def verify_download(directory, package):
    indexes = list(directory.rglob("artifact_manifest.json"))
    if len(indexes) != 1:
        raise ValueError("REMOTE_ARTIFACT_MANIFEST_MISSING_OR_AMBIGUOUS")
    index = json.loads(indexes[0].read_text())
    if index.get("run_id") != package["run_id"] or index.get("identity") != package["identity"]:
        raise ValueError("REMOTE_RUN_IDENTITY_MISMATCH")
    for name, digest in index["files"].items():
        file = (indexes[0].parent / name).resolve()
        if not file.is_relative_to(indexes[0].parent.resolve()) or file_hash(file) != digest:
            raise ValueError("REMOTE_OUTPUT_HASH_MISMATCH:" + name)
    result = {"status": "DOWNLOADED_HASH_VERIFIED", "remote_status": index["status"],
              "files": len(index["files"]), "identity": index["identity"]}
    write_json(directory / "download_verification.json", result)
    return result


def build_relaunch(output, source, run_id):
    """New notebook job reuses immutable uploaded inputs; never reuploads or alters them."""
    safe_name(run_id)
    existing = validate_package(source)
    if existing["mode"] != "smoke" or existing["identity"] != evidence_identity():
        raise ValueError("RELAUNCH_REQUIRES_CURRENT_SMOKE_INPUTS")
    if output.exists():
        raise FileExistsError(output)
    output.resolve().relative_to((ROOT / "data/interim/modeling/sprint03").resolve())
    kernel = output / "kernel"
    kernel.mkdir(parents=True)
    job = {key: existing[key] for key in ("version", "mode", "identity", "archives", "model", "candidate",
                                        "allow_full_training", "train_count", "dev_count", "test100")}
    job["run_id"] = run_id
    template = (ROOT / "notebooks/sprint03/kaggle_entry.py").read_text(encoding="utf-8")
    code = template.replace("__JOB_CONFIG_JSON__", repr(json.dumps(job)))
    ast.parse(code)
    notebook = {"nbformat": 4, "nbformat_minor": 5, "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
        "cells": [{"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
                   "source": code.splitlines(keepends=True)}]}
    write_json(kernel / "kaggle_entry.ipynb", notebook)
    metadata = json.loads((source / "kernel/kernel-metadata.json").read_text())
    username = existing["kernel_id"].split("/")[0]
    metadata.update(id=username + "/" + run_id, title=run_id.replace("-", " "),
                    code_file="kaggle_entry.ipynb", kernel_type="notebook")
    write_json(kernel / "kernel-metadata.json", metadata)
    result = {**job, "kernel_id": metadata["id"], "dataset_id": existing["dataset_id"],
              "reuses_uploaded_package": str(source.relative_to(ROOT)), "upload_bytes": 0,
              "full_training": "DISABLED", "package_files": {
                  p.relative_to(output).as_posix(): file_hash(p) for p in kernel.iterdir() if p.is_file()}}
    write_json(output / "handoff_manifest.json", result)
    validate_package(output)
    return result
