"""Standalone Kaggle bootstrap. Job configuration is injected by the package builder."""

import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import threading
import time
import traceback
import zipfile

JOB = json.loads(__JOB_CONFIG_JSON__)
WORKSPACE = Path("/tmp") / JOB["run_id"]
SAVED = Path("/kaggle/working/dacn_artifacts") / JOB["run_id"]
SAVED.mkdir(parents=True, exist_ok=False)
STATUS = {"status": "BOOTSTRAP_PENDING", "run_id": JOB["run_id"], "identity": JOB["identity"],
          "mode": JOB["mode"], "test100": "NOT_INCLUDED_NOT_READ", "full_training_performed": False}


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def extract_bundle(name, definition):
    found = list(Path("/kaggle/input").rglob(name))
    if len(found) == 1:
        archive = found[0]
        if digest(archive) != definition["sha256"]:
            raise ValueError("INPUT_ARCHIVE_HASH_MISMATCH:" + name)
        with zipfile.ZipFile(archive) as stream:
            raw = stream.read(definition["manifest"])
            if hashlib.sha256(raw).hexdigest() != definition["manifest_sha256"]:
                raise ValueError("INNER_MANIFEST_HASH_MISMATCH")
            manifest = json.loads(raw)
            expected = set(manifest["files"]) | {definition["manifest"]}
            if set(stream.namelist()) != expected:
                raise ValueError("UNDECLARED_ARCHIVE_MEMBER")
            for entry in stream.infolist():
                target = (WORKSPACE / entry.filename).resolve()
                if "\\" in entry.filename or not target.is_relative_to(WORKSPACE.resolve()):
                    raise ValueError("UNSAFE_ZIP_PATH")
                if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError("ZIP_SYMLINK_FORBIDDEN")
                if target.exists():
                    raise FileExistsError(target)
            stream.extractall(WORKSPACE)
            for entry in stream.infolist():
                mode = (entry.external_attr >> 16) & 0o777
                if mode:
                    (WORKSPACE / entry.filename).chmod(mode)
    else:
        # Kaggle may expand archives during dataset ingestion: trust only a pinned manifest.
        manifests = [p for p in Path("/kaggle/input").rglob(definition["manifest"])
                     if digest(p) == definition["manifest_sha256"]]
        if len(manifests) != 1:
            raise ValueError("INPUT_BUNDLE_NOT_FOUND:" + name)
        manifest = json.loads(manifests[0].read_text())
        base = manifests[0].parent.resolve()
        for relative, checksum in manifest["files"].items():
            source = (base / relative).resolve()
            target = (WORKSPACE / relative).resolve()
            if not source.is_relative_to(base) or not target.is_relative_to(WORKSPACE.resolve()):
                raise ValueError("UNSAFE_EXPANDED_PATH")
            if digest(source) != checksum or target.exists():
                raise ValueError("EXPANDED_FILE_HASH_OR_COLLISION")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        shutil.copyfile(manifests[0], WORKSPACE / definition["manifest"])
    for relative, checksum in manifest["files"].items():
        if digest(WORKSPACE / relative) != checksum:
            raise ValueError("EXTRACTED_FILE_HASH_MISMATCH:" + relative)


def run(command, log):
    print("Running:", command[:4], flush=True)
    with log.open("a", encoding="utf-8") as output:
        subprocess.run(command, cwd=WORKSPACE, stdout=output, stderr=subprocess.STDOUT, check=True)


def backup(final=False):
    total = 0
    for relative in ("data/interim/modeling/sprint03/" + JOB["run_id"], "data/processed/evaluation/sprint03"):
        source_dir = WORKSPACE / relative
        if not source_dir.exists():
            continue
        for source in source_dir.rglob("*"):
            if not source.is_file() or source.suffix == ".tmp":
                continue
            # An immutable checkpoint is complete only after its hash sidecar was published.
            if source.suffix == ".pt":
                sidecar = source.with_suffix(".pt.json")
                if not sidecar.exists():
                    continue
                if digest(source) != json.loads(sidecar.read_text())["checkpoint_sha256"]:
                    raise ValueError("BACKUP_CHECKPOINT_HASH_MISMATCH")
            total += source.stat().st_size
            if total > 19 * 1024**3:
                raise RuntimeError("PERSISTED_OUTPUT_EXCEEDS_19_GIB_BUDGET")
            target = SAVED / "workspace" / source.relative_to(WORKSPACE)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists() or digest(target) != digest(source):
                temporary = target.with_suffix(target.suffix + ".tmp")
                shutil.copyfile(source, temporary)
                if digest(temporary) != digest(source):
                    temporary.unlink()
                    if final:
                        raise RuntimeError("FINAL_BACKUP_SOURCE_CHANGED")
                    continue
                temporary.replace(target)
    return total


def main():
    WORKSPACE.mkdir(parents=True, exist_ok=False)
    free = shutil.disk_usage(WORKSPACE).free
    inventory = {"platform": platform.platform(), "kernel_python": platform.python_version(),
                 "cpu_count": os.cpu_count(), "disk_free_bytes": free,
                 "meminfo": Path("/proc/meminfo").read_text().splitlines()[:6]}
    executable = shutil.which("nvidia-smi") or next((str(p) for p in (
        Path("/usr/bin/nvidia-smi"), Path("/usr/local/nvidia/bin/nvidia-smi")) if p.is_file()), None)
    gpu = subprocess.run([executable, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
                         capture_output=True, text=True) if executable else None
    inventory["gpu"] = gpu.stdout.strip() if gpu else None
    inventory["gpu_command_returncode"] = gpu.returncode if gpu else 127
    inventory["device_nodes"] = [str(p) for p in Path("/dev").glob("nvidia*")]
    write(SAVED / "environment_initial.json", inventory)
    if gpu is None or gpu.returncode or not gpu.stdout.strip():
        raise RuntimeError("KAGGLE_GPU_NOT_AVAILABLE: request accepted but hardware not verified; check account GPU access, accelerator and image")
    if free < 25 * 1024**3:
        raise RuntimeError("KAGGLE_SCRATCH_DISK_BELOW_25_GIB_BOOTSTRAP_BUDGET")
    for name, definition in JOB["archives"].items():
        extract_bundle(name, definition)
    cache = WORKSPACE / "runtime_cache"
    for name in ("TMPDIR", "TEMP", "TMP", "PIP_CACHE_DIR", "UV_CACHE_DIR", "XDG_CACHE_HOME", "HF_HOME", "TORCH_HOME", "UV_PYTHON_INSTALL_DIR"):
        directory = cache / name.lower()
        directory.mkdir(parents=True, exist_ok=True)
        os.environ[name] = str(directory)
    os.environ.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1", CUBLAS_WORKSPACE_CONFIG=":4096:8",
                      TOKENIZERS_PARALLELISM="false", OMP_NUM_THREADS="2", MKL_NUM_THREADS="2")
    write(SAVED / "cloud_install_inventory.json", {"recorded_before_install": True,
        "bootstrap": "uv==0.8.22 from PyPI", "python": "isolated CPython 3.11 via uv",
        "torch": "2.8.0 CUDA12.8 https://download.pytorch.org/whl/cu128",
        "requirements": (WORKSPACE / "configs/colab/sprint03/requirements_transitive_v1.txt").read_text(),
        "resource_downloads": "NONE: verified attached bundle only", "scope": "Kaggle scratch only"})
    log = SAVED / "bootstrap.log"
    uv_folder = WORKSPACE / "bootstrap_uv"
    run([sys.executable, "-m", "pip", "install", "--target", str(uv_folder), "uv==0.8.22"], log)
    env = WORKSPACE / "runtime_py311"
    run([str(uv_folder / "bin/uv"), "venv", "--python", "3.11", str(env), "--seed"], log)
    python = str(env / "bin/python")
    run([python, "-m", "pip", "install", "torch==2.8.0", "--index-url", "https://download.pytorch.org/whl/cu128"], log)
    run([python, "-m", "pip", "install", "-r", "configs/colab/sprint03/requirements_transitive_v1.txt"], log)
    installed = subprocess.check_output([python, "-m", "pip", "freeze"], cwd=WORKSPACE, text=True)
    (SAVED / "cloud_packages.txt").write_text(installed)
    runtime_bytes = sum(p.stat().st_size for folder in (env, uv_folder, cache) for p in folder.rglob("*") if p.is_file())
    write(SAVED / "cloud_install_sizes.json", {"logical_bytes": runtime_bytes, "GB": runtime_bytes / 10**9,
                                             "GiB": runtime_bytes / 1024**3, "location": "Kaggle scratch, not local D"})
    lock = json.loads((WORKSPACE / "data/interim/modeling/sprint03/task_01_06_20261003_v1/resource_lock_local_v1.json").read_text())
    java = WORKSPACE / lock["java"]["path"]
    (java / "bin/java").chmod(0o755)
    os.environ.update(JAVA_HOME=str(java), JAVA_TOOL_OPTIONS="-Djava.io.tmpdir=" + str(cache / "tmpdir") + " -XX:-UsePerfData",
                      HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    os.environ["PATH"] = str(java / "bin") + os.pathsep + os.environ["PATH"]
    output = WORKSPACE / "data/interim/modeling/sprint03" / JOB["run_id"]
    command = [python, "-m", "scripts.51_run_kaggle_remote", JOB["mode"], "--output-dir", str(output),
               "--model", JOB["model"], "--candidate", JOB["candidate"]]
    if JOB["mode"] == "full":
        if JOB["allow_full_training"] is not True:
            raise ValueError("FULL_TRAINING_DISABLED")
        command += ["--allow-full-training", "--smoke-evidence", "configs/kaggle/sprint03/approved_smoke.json"]
    stop, failures = threading.Event(), []
    def periodic_backup():
        while not stop.wait(120):
            try:
                backup()
            except Exception as error:
                failures.append(str(error))
    worker = threading.Thread(target=periodic_backup, daemon=True)
    worker.start()
    try:
        run(command, SAVED / "remote_run.log")
    finally:
        stop.set()
        worker.join(timeout=10)
        STATUS["backup_bytes"] = backup(final=True)
        STATUS["periodic_backup_warnings"] = failures
    report_name = "full_training_report.json" if JOB["mode"] == "full" else "smoke_report.json"
    report = json.loads((output / report_name).read_text())
    if report["identity"] != JOB["identity"]:
        raise ValueError("REMOTE_IDENTITY_MISMATCH")
    STATUS.update(status=report["status"], full_training_performed=JOB["mode"] == "full")


try:
    main()
except Exception as error:
    STATUS.update(status="REMOTE_BLOCKED_OR_FAILED", error_type=type(error).__name__, error=str(error),
                  traceback=traceback.format_exc())
    print(STATUS["traceback"], flush=True)
    if WORKSPACE.exists():
        try:
            backup(final=True)
        except Exception as backup_error:
            STATUS["backup_error"] = str(backup_error)
finally:
    write(SAVED / "job_report.json", STATUS)
    index = {"run_id": JOB["run_id"], "identity": JOB["identity"], "status": STATUS["status"],
             "files": {p.relative_to(SAVED).as_posix(): digest(p) for p in SAVED.rglob("*") if p.is_file() and not p.name.endswith(".tmp")}}
    write(SAVED / "artifact_manifest.json", index)
    print(json.dumps(STATUS), flush=True)
