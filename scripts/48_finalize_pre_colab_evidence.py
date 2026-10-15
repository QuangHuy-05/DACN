"""Verify shared bundles/portable CLI and record truthful readiness/accounting."""

import argparse
import ast
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

from src.evaluation.dev_runner import ROOT, file_hash, read_jsonl, write_json
from src.modeling.colab_handoff import safe_extract
from src.modeling.pre_colab import compare_ledger, machine_snapshot
from src.data.nso_dual_snapshot import reference_key

EVIDENCE = ROOT / "data/interim/modeling/sprint03/pre_colab_20261003_resume_v1"


def logical_size(paths):
    seen, total = set(), 0
    for path in paths:
        for file in ([path] if path.is_file() else path.rglob("*")):
            if not file.is_file():
                continue
            stat = file.stat()
            identity = (stat.st_dev, stat.st_ino)
            if identity not in seen:
                seen.add(identity)
                total += stat.st_size
    return {"bytes": total, "gb": total / 1e9, "gib": total / 2**30, "regular_files_distinct_inode": len(seen)}


def verify_archive(path, expected_hash, manifest_name):
    if file_hash(path) != expected_hash:
        raise ValueError("ZIP_CHECKSUM_MISMATCH")
    with zipfile.ZipFile(path) as archive:
        manifest = json.loads(archive.read(manifest_name))
        names = [entry.filename for entry in archive.infolist()]
        if len(names) != len(set(names)) or set(names) != set(manifest["files"]) | {manifest_name}:
            raise ValueError("UNDECLARED_OR_DUPLICATE_ZIP_FILE")
        for name, digest in manifest["files"].items():
            if name.startswith("/") or ".." in Path(name).parts or "\\" in name or any(part in name.lower() for part in ("test100", "test_benchmark", "exports/", ".venv", "/cache/")):
                raise ValueError("FORBIDDEN_BUNDLE_PATH:" + name)
            sha = hashlib.sha256()
            with archive.open(name) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    sha.update(chunk)
            if sha.hexdigest() != digest:
                raise ValueError("ZIP_MEMBER_HASH_MISMATCH:" + name)
    return {"status": "ALL_MEMBER_HASHES_PASS", "files": len(manifest["files"]), "scope": manifest["scope"]}


def finalize(output):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    reference = read_jsonl(EVIDENCE / "u1_v4/reference_old.jsonl")
    invalid = defaultdict(list)
    for row in reference:
        if row["validation_status"] != "PARENT_CODE_LINK_PASS":
            invalid[reference_key(row)].append(row)
    unresolved = read_jsonl(EVIDENCE / "u1_v4/unresolved.jsonl")
    for row in unresolved:
        evidence = invalid.get(tuple(row["full_key"]), [])
        row["invalid_parent_reference_candidates"] = evidence
        row["diagnostic_reason"] = "EXACT_NAME_REFERENCE_REJECTED_PARENT_LINK" if evidence else "NO_VALID_EXACT_FULL_KEY_IN_DATED_SOURCE"
    from src.evaluation.dev_runner import write_jsonl
    write_jsonl(output / "unresolved_diagnostics.jsonl", unresolved)
    registry = json.loads((EVIDENCE / "u3_v3/source_resource_registry.json").read_text())
    package_rows = []
    for distribution in metadata.distributions():
        name = distribution.metadata.get("Name")
        if name:
            package_rows.append({"name": name, "version": distribution.version,
                                 "source_url": f"https://pypi.org/project/{name}/{distribution.version}/",
                                 "author": distribution.metadata.get("Author") or distribution.metadata.get("Author-email"),
                                 "license_expression_or_metadata": distribution.metadata.get("License-Expression") or distribution.metadata.get("License") or "UNKNOWN",
                                 "role": "existing_local_runtime_not_installed_this_turn"})
    lock_path = ROOT / "data/interim/modeling/sprint03/task_01_06_20261003_v1/resource_lock_local_v1.json"
    lock = json.loads(lock_path.read_text())
    registry["runtime_package_registry"] = package_rows
    registry["java"] = lock["java"]
    registry["asset_source_urls"] = {
        "phobert_encoder_tokenizer": "https://huggingface.co/vinai/phobert-base/tree/01daacda68afe13d83023d16ec647239e344a1e6",
        "vncorenlp": "https://github.com/vncorenlp/VnCoreNLP/tree/62bbc58fe5d113c898eae112656be97dcf50b3a0",
        "java": "https://github.com/adoptium/temurin17-binaries/releases/tag/jdk-17.0.20.1%2B1",
        "nso_reference_manifest": (EVIDENCE / "u1_v4/reference_manifest.json").relative_to(ROOT).as_posix(),
        "uv_bootstrap_future_only": "https://pypi.org/project/uv/0.8.22/"}
    registry["created_at"] = datetime.now(timezone.utc).isoformat()
    registry["new_local_install_bytes"] = 0
    write_json(output / "resource_registry_complete.json", registry)
    handoff = EVIDENCE / "handoff_v1"
    manifest = json.loads((handoff / "handoff_manifest.json").read_text())
    bundle_checks = {}
    for key, name in (("code_archive", "code_bundle_manifest.json"), ("resource_archive", "resource_bundle_manifest.json")):
        entry = manifest[key]
        bundle_checks[key] = verify_archive(ROOT / entry["path"], entry["sha256"], name)
    workspace = output / "portable_code_smoke"
    safe_extract(ROOT / manifest["code_archive"]["path"], workspace, manifest["code_archive"]["sha256"])
    commands = []
    for module in ("scripts.30_prepare_model_training_data", "scripts.31_train_deepparse_finetuned", "scripts.32_train_phobert_crf",
                   "scripts.33_train_proposed_dynamic", "scripts.34_audit_modeling_artifacts", "scripts.47_prepare_dp_zero_shot_config"):
        result = subprocess.run([sys.executable, "-m", module, "--help"], cwd=workspace, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise RuntimeError("PORTABLE_HELP_FAILURE:" + module + ":" + result.stderr)
        commands.append({"module": module, "exit_code": result.returncode})
    notebook = json.loads((ROOT / manifest["notebook"]).read_text())
    if file_hash(ROOT / manifest["notebook"]) != manifest["notebook_sha256"]:
        raise ValueError("NOTEBOOK_HASH_DRIFT")
    codes = []
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            source = "".join(cell["source"])
            ast.parse(source)
            if cell["outputs"] or cell["execution_count"] is not None:
                raise ValueError("NOTEBOOK_MUST_BE_UNEXECUTED")
            codes.append(source)
    if not any("ENABLE_NEURAL_TRAINING = False" in source for source in codes):
        raise ValueError("TRAINING_NOT_DISABLED_BY_DEFAULT")
    test_summary = {}
    for name in ("full_suite_final.log", "neural_suite_final.log", "crf_suite_final.log"):
        path = EVIDENCE / "u5" / name
        log = path.read_text()
        count = re.search(r"Ran (\d+) tests", log)
        skip = re.search(r"OK \(skipped=(\d+)\)", log)
        if not count or "FAILED (" in log or not re.search(r"^OK(?: \(skipped=\d+\))?$", log, re.M):
            raise ValueError("TEST_SUITE_NOT_PASS:" + name)
        total, skipped = int(count[1]), int(skip[1]) if skip else 0
        test_summary[name] = {"total": total, "pass": total - skipped, "skip": skipped, "fail": 0, "sha256": file_hash(path)}
    frozen = compare_ledger(json.loads((EVIDENCE / "p0/frozen_before.json").read_text()))
    if frozen["status"] != "FROZEN_LEDGER_PASS":
        raise ValueError("FROZEN_HASH_CHANGED")
    write_json(output / "bundle_checks.json", {"bundle_checks": bundle_checks, "portable_cli_help": commands, "notebook_code_cells_ast_pass": len(codes), "execution": "NOT_EXECUTED"})
    write_json(output / "test_summary.json", test_summary)
    write_json(output / "frozen_compare.json", frozen)
    shared = {}
    for source in (output / "resource_registry_complete.json", EVIDENCE / "u3_v3/deepparse_download_recipe_pending.json"):
        destination = handoff / source.name
        if destination.exists():
            raise FileExistsError(destination)
        shutil.copy2(source, destination)
        shared[destination.name] = file_hash(destination)
    write_json(handoff / "handoff_metadata_manifest.json", {"files": shared, "scope": "resource dossier and pending recipe; not an active DP lock"})
    initial = json.loads((EVIDENCE / "p0/initial_state.json").read_text())
    machine = machine_snapshot()
    accounting = {"new_packages_installed": [], "new_weights_downloaded": [], "new_install": {"bytes": 0, "gb": 0, "gib": 0},
                  "historical_install_only": {"bytes": 2453588804, "gb": 2.453588804, "gib": 2453588804 / 2**30},
                  "artifact_categories": {}, "disk_before": initial.get("machine", initial.get("environment", {})), "disk_after": machine,
                  "policy": "logical regular-file bytes, distinct inode; artifact copies/ZIPs are separate files; no claim disk delta equals installs"}
    categories = {
        "new_evidence_and_handoff": [EVIDENCE],
        "new_gazetteer_packages": [ROOT / "data/processed/gazetteer/s3_v4_nso_dual_snapshot", ROOT / "data/processed/gazetteer/s3_v4_nso_dual_snapshot_release2"],
        "new_baseline_runs": [ROOT / "data/processed/evaluation/sprint03" / name for name in ("heur_jw_followup_20261003_v1", "crf_followup_20261003_v1", "heur_jw_followup_fivefield_20261003_v1", "crf_followup_fivefield_20261003_v1")]}
    for name, paths in categories.items():
        accounting["artifact_categories"][name] = logical_size(paths)
    accounting["artifact_total"] = logical_size([path for paths in categories.values() for path in paths])
    write_json(output / "storage_accounting.json", accounting)
    write_json(EVIDENCE / "storage_accounting.json", accounting)
    return {"status": "BUNDLE_PORTABLE_AST_TESTS_FROZEN_PASS", "tests": test_summary, "artifact_total": accounting["artifact_total"], "new_install_bytes": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(finalize(args.output_dir.resolve()), ensure_ascii=False))
