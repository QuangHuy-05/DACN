"""Read-only frozen/artifact audit and measured local artifact storage."""
import argparse
import ast
import json
import os
from pathlib import Path
import zipfile
from src.evaluation.dev_runner import ROOT, file_hash, write_json
from src.data.test_corpus_release import APPROVED_STATUS


def audit_frozen(ledger):
    changes = []
    for relative, digest in ledger["files"].items():
        path = ROOT / relative
        if not path.is_file() or file_hash(path) != digest:
            changes.append(relative)
    for relative, expected in ledger.get("size_only", {}).items():
        path = ROOT / relative
        if not path.is_file():
            changes.append(relative)
        else:
            stat = path.stat()
            if {"bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns} != expected:
                changes.append(relative)
    return {"status": "PASS" if not changes else "FAIL", "hashes_checked": len(ledger["files"]),
            "raw_size_mtime_checked": len(ledger.get("size_only", {})), "changed": changes}


def measure(roots):
    identities, total, logical, files = set(), 0, 0, 0
    for root in roots:
        for directory, subdirs, names in os.walk(root, followlinks=False):
            subdirs[:] = [name for name in subdirs if not (Path(directory) / name).is_symlink()]
            for name in names:
                path = Path(directory) / name
                if path.is_symlink():
                    continue
                stat = path.stat()
                logical += stat.st_size
                key = (stat.st_dev, stat.st_ino) if stat.st_ino else str(path.resolve())
                if key not in identities:
                    identities.add(key)
                    total += stat.st_size
                    files += 1
    return {"bytes": total, "GB": total / 1e9, "GiB": total / 2**30, "files": files,
            "logical_bytes_before_hardlink_deduplication": logical,
            "method": "file sizes, symlinks excluded, overlapping paths/hardlink inode deduplicated; not filesystem allocated bytes"}


def audit_handoff(path):
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("code_archive", "resource_archive"):
        record = manifest[key]
        archive = ROOT / record["path"]
        if file_hash(archive) != record["sha256"]:
            raise ValueError("HANDOFF_ARCHIVE_CHANGED")
        with zipfile.ZipFile(archive) as stream:
            names = stream.namelist()
            if len(names) != len(set(names)):
                raise ValueError("DUPLICATE_ZIP_MEMBER")
            if any("__pycache__" in name or "exports/" in name or "test_benchmark_t0.jsonl" in name
                   or "annotation_queue_batch01" in name or ".venv" in name for name in names):
                raise ValueError("TRAINING_BUNDLE_CONTAINS_FORBIDDEN_ARTIFACT")
    notebook = ROOT / manifest["notebook"]
    if file_hash(notebook) != manifest["notebook_sha256"]:
        raise ValueError("HANDOFF_NOTEBOOK_CHANGED")
    for cell in json.loads(notebook.read_text())["cells"]:
        if cell["cell_type"] == "code":
            ast.parse("".join(cell["source"]))
            if cell["execution_count"] is not None or cell["outputs"]:
                raise ValueError("NOTEBOOK_ALREADY_EXECUTED")
    return {"status": "PASS", "archive_hashes": "PASS", "allowlist_scope": "PASS",
            "notebook_ast": "PASS", "cloud_training": "NOT_EXECUTED"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--handoff-manifest", type=Path)
    parser.add_argument("--corpus-manifest", type=Path)
    parser.add_argument("--measure-root", type=Path, nargs="*", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = {"frozen": audit_frozen(json.loads(args.ledger.read_text())),
        "installs_downloads": {"bytes": 0, "GB": 0, "GiB": 0, "packages": [], "models": [],
                              "basis": "inventory44 reuse-only; no install/download command executed"},
        "artifacts": measure(args.measure_root), "test_inference_scoring": "NOT_EXECUTED", "neural_training": "NOT_EXECUTED"}
    if args.handoff_manifest:
        result["handoff"] = audit_handoff(args.handoff_manifest)
    if args.corpus_manifest:
        corpus = json.loads(args.corpus_manifest.read_text())
        if corpus.get("status") != APPROVED_STATUS or corpus["sample_counts"] != {"train": 240, "dev": 60, "test": 100}:
            raise ValueError("CORPUS_NOT_APPROVED_240_60_100")
        for name, digest in corpus["output_sha256"].items():
            if file_hash(args.corpus_manifest.parent / name) != digest:
                raise ValueError("CORPUS_OUTPUT_CHANGED")
        result["corpus"] = {"status": "PASS", "counts": corpus["sample_counts"], "evaluation_exclusions": corpus["evaluation_exclusions"]}
    else:
        result["corpus"] = {"status": "BLOCKED_HUMAN_ADJUDICATION", "approved_release_created": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, result)
    print(json.dumps({"frozen": result["frozen"], "artifacts": result["artifacts"], "corpus": result["corpus"]}))
    return 0 if result["frozen"]["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
