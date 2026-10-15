"""Generate and verify data freeze run_manifest.json for baseline evaluations."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import pandas as pd

from src.evaluation.protocol import (
    FUZZY_EMPTY_POLICY,
    FUZZY_NORMALIZATION,
    FUZZY_SIMILARITY_METHOD,
    SCORING_PROTOCOL_VERSION,
)


BENCHMARK_FILES = (
    "01_full_address_new_verified.csv",
    "02_raw_noisy_synthetic_1000.csv",
    "03_real_address_old_1500.csv",
    "04_missing_fields_800.csv",
    "06_hybrid_addresses_600.csv",
    "07_bidirectional_pairs_verified.csv",
)


def compute_sha256(path: Path) -> str:
    """Calculate the hexadecimal SHA-256 digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(
    benchmark_dir: Path,
    mapping_path: Path,
    run_id: str | None = None,
    run_kind: str = "full",
) -> dict:
    """Build immutable input metadata without writing an artifact to disk."""
    now_iso = datetime.now(timezone.utc).isoformat()
    files_info = {}

    for fname in BENCHMARK_FILES:
        fpath = benchmark_dir / fname
        if not fpath.exists():
            raise FileNotFoundError(fpath)
        df = pd.read_csv(fpath, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        sha = compute_sha256(fpath)
        files_info[fname] = {
            "row_count": len(df),
            "columns": list(df.columns),
            "sha256": sha,
            "size_bytes": fpath.stat().st_size,
        }

    if not mapping_path.exists():
        raise FileNotFoundError(mapping_path)
    mapping_info = {
        "file_name": mapping_path.name,
        "sha256": compute_sha256(mapping_path),
        "size_bytes": mapping_path.stat().st_size,
    }

    try:
        postal_version = metadata.version("postal")
    except metadata.PackageNotFoundError:
        postal_version = None
    source_dir = Path(os.environ.get("LIBPOSTAL_SOURCE_DIR", Path.home() / "libpostal-src"))
    source_commit = None
    if source_dir.is_dir():
        check = subprocess.run(["git", "-C", str(source_dir), "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
        if check.returncode == 0:
            source_commit = check.stdout.strip()
    code_root = Path(__file__).resolve().parents[2]
    code_files = (
        "src/evaluation/adapters/libpostal_adapter.py",
        "src/evaluation/adapters/vnadmin_adapter.py",
        "src/evaluation/scorer.py",
        "src/evaluation/data_contract.py",
        "src/evaluation/manifest.py",
        "src/evaluation/protocol.py",
        "src/evaluation/run_artifacts.py",
        "scripts/05_run_baseline_pilot.py",
        "scripts/06_run_baseline_full.py",
        "scripts/07_generate_baseline_report.py",
        "scripts/08_generate_report_materials.py",
        "scripts/build_baseline_dashboard.py",
        "src/evaluation/reporter.py",
    )

    manifest = {
        "manifest_version": "4.0",
        "freeze_timestamp": now_iso,
        "run_id": run_id,
        "run_kind": run_kind,
        "artifact_layout": "data/processed/evaluation/runs/<run_id>",
        "seed": 42,
        "mapping_source": mapping_info,
        "python_version": platform.python_version(),
        "runtime_packages": {name: metadata.version(name) for name in ("pandas", "pyarrow", "osmium", "tqdm")},
        "baseline_tools": {
            "vietnamadminunits": metadata.version("vietnamadminunits"),
            "libpostal": postal_version,
            "libpostal_model": "openvenues default",
            "libpostal_c_commit": source_commit,
        },
        "protocol": (
            "oracle mode for 01/02/03/04; both modes for 06; old-to-new conversion for 07; "
            "strict exact metrics plus normalized Levenshtein similarity; Data 07 targets "
            "resolved from MaPhuongXaMoi in the authoritative mapping"
        ),
        "scoring": {
            "protocol_version": SCORING_PROTOCOL_VERSION,
            "fuzzy_similarity_method": FUZZY_SIMILARITY_METHOD,
            "fuzzy_similarity_normalization": FUZZY_NORMALIZATION,
            "fuzzy_empty_policy": FUZZY_EMPTY_POLICY,
            "administrative_target_rule": (
                "fuzzy similarity is descriptive only; target identity remains strict after "
                "normalization, with Data 07 gold ward/province resolved by official target code"
            ),
        },
        "code_hashes": {name: compute_sha256(code_root / name) for name in code_files},
        "datasets": files_info,
    }
    return manifest


def generate_manifest(
    benchmark_dir: Path,
    mapping_path: Path,
    output_manifest_path: Path,
    run_id: str | None = None,
    run_kind: str = "full",
) -> dict:
    """Compatibility wrapper that builds and writes an input manifest."""
    manifest = build_manifest(benchmark_dir, mapping_path, run_id=run_id, run_kind=run_kind)

    output_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    return manifest
