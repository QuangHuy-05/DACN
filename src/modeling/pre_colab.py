"""Pre-Colab state ledger, input availability and readiness helpers.

The older ``src.modeling.artifacts.frozen_snapshot`` only covered s3_v1/s3_v2
and existing runs.  This module keeps that function untouched and adds a
broader ledger that also pins s3_v3, the mapping/third-party code tables,
locked modeling configs, prepared derivatives and the test-only handoff bytes.
Test100 files are hashed as bytes only; their content is never parsed here.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path

from src.evaluation.dev_runner import ROOT, file_hash, write_json

LEDGER_SCHEMA = "s3-pre-colab-frozen-ledger-v1"

# Directories whose every regular file is frozen at the start of the turn.
FROZEN_DIRECTORIES = (
    "data/processed/annotation/sprint03",
    "data/processed/gazetteer/s3_v1",
    "data/processed/gazetteer/s3_v2",
    "data/processed/gazetteer/s3_v3_nso_2025_snapshot",
    "data/processed/evaluation/sprint03",
    "data/processed/benchmark",
    "data/reference/administrative_units",
    "configs/modeling/sprint03",
    "docs/sprints/sprint_03/annotation_handoff/test100_v1",
    "data/interim/annotation/sprint03",
    "data/interim/modeling/sprint03/seven_priorities_20261002_v1/prepared_v3",
    "data/interim/modeling/sprint03/alignment_tone_policy_v2_20261003/full_300_audit_r5",
    "data/interim/modeling/sprint03/neural_integration_tone_v2_replay_20261003_fullpath",
    "data/interim/modeling/sprint03/nso_official_crosswalk_2025_20261003_v1",
)
FROZEN_FILES = (
    "third_party/vietnamadminunits/data/raw/danhmuchanhchinh.gso.gov.vn_ward_2025-07-18.csv",
    "third_party/vietnamadminunits/data/raw/danhmuchanhchinh.gso.gov.vn_district_2025-07-18.csv",
    "third_party/vietnamadminunits/data/interim/legacy_63-province-10040-ward_with_location_and_key.csv",
    "data/interim/modeling/sprint03/task_01_06_20261003_v1/resource_lock_local_v1.json",
    "configs/deepparse_native_mapping_v1.json",
    "configs/requirements_sprint3_crf.txt",
)
# Raw sources are multi-GB; record size/mtime instead of rehashing every turn.
SIZE_ONLY_DIRECTORIES = ("data/raw",)
TEST_ONLY_PREFIX = "docs/sprints/sprint_03/annotation_handoff/test100_v1/"


def _iter_files(directory: Path):
    if not directory.exists():
        return []
    return sorted(path for path in directory.rglob("*") if path.is_file() and "__pycache__" not in path.parts)


def frozen_ledger(root: Path = ROOT) -> dict:
    files, missing = {}, []
    for relative in FROZEN_DIRECTORIES:
        directory = root / relative
        if not directory.exists():
            missing.append(relative)
            continue
        for path in _iter_files(directory):
            files[path.relative_to(root).as_posix()] = file_hash(path)
    for relative in FROZEN_FILES:
        path = root / relative
        if path.is_file():
            files[relative] = file_hash(path)
        else:
            missing.append(relative)
    size_only = {}
    for relative in SIZE_ONLY_DIRECTORIES:
        for path in _iter_files(root / relative):
            stat = path.stat()
            size_only[path.relative_to(root).as_posix()] = {"bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns}
    return {
        "schema_version": LEDGER_SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "policy": ("byte hashes of approved corpus, every frozen Gazetteer incl. s3_v3, runs, benchmark, mapping, "
                   "third-party code CSVs, locked configs, prepared derivatives and test100 handoff bytes; "
                   "test100 content not parsed"),
        "test100_files_hashed_bytes_only": sorted(name for name in files if name.startswith(TEST_ONLY_PREFIX)),
        "files": files,
        "size_only": size_only,
        "missing_inputs": missing,
    }


def compare_ledger(ledger: dict, root: Path = ROOT) -> dict:
    changed, removed = [], []
    for name, digest in ledger["files"].items():
        path = root / name
        if not path.is_file():
            removed.append(name)
        elif file_hash(path) != digest:
            changed.append(name)
    size_changed = []
    for name, meta in ledger.get("size_only", {}).items():
        path = root / name
        if not path.is_file():
            removed.append(name)
            continue
        stat = path.stat()
        if stat.st_size != meta["bytes"] or stat.st_mtime_ns != meta["mtime_ns"]:
            size_changed.append(name)
    added_in_frozen_dirs = []
    for relative in FROZEN_DIRECTORIES:
        for path in _iter_files(root / relative):
            name = path.relative_to(root).as_posix()
            if name not in ledger["files"]:
                added_in_frozen_dirs.append(name)
    status = "FROZEN_LEDGER_PASS" if not (changed or removed or size_changed) else "BLOCKED_FROZEN_CHANGE"
    return {"status": status, "checked_files": len(ledger["files"]), "checked_size_only": len(ledger.get("size_only", {})),
            "changed": changed, "removed": removed, "size_changed": size_changed,
            "added_files_in_frozen_directories": added_in_frozen_dirs,
            "note": "added files are new versioned outputs inside parent directories; existing bytes must be unchanged"}


def _run(args: list[str], root: Path = ROOT) -> str | None:
    try:
        result = subprocess.run(args, cwd=root, capture_output=True, text=True, check=False, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return None
    # Porcelain status starts with meaningful spaces; strip only the newline.
    return result.stdout.rstrip("\r\n") if result.returncode == 0 else None


def git_snapshot(root: Path = ROOT) -> dict:
    porcelain = _run(["git", "status", "--porcelain"], root) or ""
    lines = [line for line in porcelain.splitlines() if line]
    return {
        "branch": _run(["git", "branch", "--show-current"], root),
        "head": _run(["git", "rev-parse", "HEAD"], root),
        "remotes": _run(["git", "remote", "-v"], root),
        "recent_log": (_run(["git", "log", "--oneline", "-n", "10"], root) or "").splitlines(),
        "modified": sorted(line[3:] for line in lines if not line.startswith("??")),
        "untracked": sorted(line[3:] for line in lines if line.startswith("??")),
        "policy": "no reset/clean/stash/switch; dirty files preserved",
    }


def machine_snapshot(root: Path = ROOT) -> dict:
    meminfo = {}
    proc = Path("/proc/meminfo")
    if proc.is_file():
        for line in proc.read_text().splitlines():
            key, value = line.split(":", 1)
            if key in ("MemTotal", "MemAvailable", "SwapTotal", "SwapFree"):
                meminfo[key + "_bytes"] = int(value.split()[0]) * 1024
    usage = shutil.disk_usage(root)
    gpu = _run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], root)
    return {
        "platform": platform.platform(), "python": platform.python_version(), "cpu_count": os.cpu_count(),
        "memory": meminfo, "disk_root": str(root.as_posix()),
        "disk_total_bytes": usage.total, "disk_free_bytes": usage.free,
        "disk_free_gb": round(usage.free / 1e9, 9), "disk_free_gib": round(usage.free / 2**30, 9),
        "gpu": gpu or "NO_NVIDIA_GPU_VISIBLE",
        "measured_at": datetime.now(timezone.utc).isoformat(),
    }


def _git_tracked(paths: list[str], root: Path = ROOT) -> set[str]:
    output = _run(["git", "ls-files", "--", *paths], root) or ""
    return set(output.splitlines())


def _git_ignored(path: str, root: Path = ROOT) -> bool:
    result = subprocess.run(["git", "check-ignore", "-q", path], cwd=root, check=False)
    return result.returncode == 0


REQUIRED_INPUTS = {
    "corpus_manifest": "data/processed/annotation/sprint03/corpus_train_dev_v2/manifest.json",
    "corpus_train": "data/processed/annotation/sprint03/corpus_train_dev_v2/train.jsonl",
    "corpus_dev": "data/processed/annotation/sprint03/corpus_train_dev_v2/dev.jsonl",
    "corpus_dev_input": "data/processed/annotation/sprint03/corpus_train_dev_v2/dev_input.jsonl",
    "gazetteer_s3_v2": "data/processed/gazetteer/s3_v2/manifest.json",
    "gazetteer_s3_v3": "data/processed/gazetteer/s3_v3_nso_2025_snapshot/manifest.json",
    "mapping_csv": "data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv",
    "third_party_ward_csv": "third_party/vietnamadminunits/data/raw/danhmuchanhchinh.gso.gov.vn_ward_2025-07-18.csv",
    "protocol_lock": "configs/modeling/sprint03/protocol_lock_v1.json",
    "prepared_v3_manifest": "data/interim/modeling/sprint03/seven_priorities_20261002_v1/prepared_v3/input_manifest.json",
    "resource_lock_local": "data/interim/modeling/sprint03/task_01_06_20261003_v1/resource_lock_local_v1.json",
    "phobert_resources": "data/interim/modeling/sprint03/resources_d_v1/phobert_base",
    "vncorenlp_resources": "data/interim/modeling/sprint03/resources_d_v1/vncorenlp_wseg",
    "java_runtime": "data/interim/modeling/sprint03/resources_d_v1/java17",
    "neural_runtime": "data/interim/modeling/sprint03/runtime_neural_d_v1/bin/python",
    "crf_runtime": "data/interim/evaluation/sprint03/runtime_py311/bin/python",
    "nso_export_xls": "data/interim/modeling/sprint03/nso_official_crosswalk_2025_20261003_v1/nso_administrative_comparison_2025-06-30_to_2025-07-01.xls",
    "test100_handoff_manifest": "docs/sprints/sprint_03/annotation_handoff/test100_v1/manifest.json",
    "frozen_heur_dev_run": "data/processed/evaluation/sprint03/heur_jw_dev_20261002_v2",
    "frozen_crf_dev_run": "data/processed/evaluation/sprint03/crf_indep_dev_20261002_v1",
}


def input_availability(root: Path = ROOT) -> dict:
    tracked = _git_tracked(list(REQUIRED_INPUTS.values()), root)
    rows = {}
    for key, relative in REQUIRED_INPUTS.items():
        path = root / relative
        exists = path.exists()
        tracked_here = relative in tracked or any(name.startswith(relative.rstrip("/") + "/") for name in tracked)
        rows[key] = {
            "path": relative, "exists_local": exists,
            "git_tracked_at_head": tracked_here,
            "git_ignored": _git_ignored(relative, root),
            "fresh_clone_has_it": tracked_here,
            "kind": "directory" if path.is_dir() else "file" if path.is_file() else "missing",
        }
    return {"inputs": rows,
            "fresh_clone_missing": sorted(key for key, row in rows.items() if not row["fresh_clone_has_it"]),
            "local_missing": sorted(key for key, row in rows.items() if not row["exists_local"]),
            "note": "interim artifacts are git-ignored; partner/Colab need a separate bundle with manifest/hash"}


def initial_state(root: Path = ROOT) -> dict:
    return {"created_at": datetime.now(timezone.utc).isoformat(), "git": git_snapshot(root),
            "machine": machine_snapshot(root), "test100": "BYTES_HASHED_ONLY_NOT_READ"}


def write_p0(output_dir: Path, root: Path = ROOT) -> dict:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    state = initial_state(root)
    ledger = frozen_ledger(root)
    availability = input_availability(root)
    write_json(output_dir / "initial_state.json", state)
    write_json(output_dir / "frozen_before.json", ledger)
    write_json(output_dir / "input_availability.json", availability)
    return {"initial_state": "initial_state.json", "frozen_files": len(ledger["files"]),
            "size_only": len(ledger["size_only"]), "missing": ledger["missing_inputs"],
            "fresh_clone_missing": availability["fresh_clone_missing"]}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
