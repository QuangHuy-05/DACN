"""Versioned artifact paths and integrity checks for baseline runs."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from src.evaluation.manifest import compute_sha256


RUN_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,63}$")


def validate_run_id(run_id: str) -> str:
    """Validate a filesystem-safe, human-readable baseline run identifier."""
    if not RUN_ID_PATTERN.fullmatch(str(run_id)):
        raise ValueError("run_id must match ^[a-z][a-z0-9_]{2,63}$")
    return str(run_id)


@dataclass(frozen=True)
class RunArtifacts:
    """All mutable outputs for one baseline execution live under its run ID."""

    project_root: Path
    run_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_root", Path(self.project_root).resolve())
        object.__setattr__(self, "run_id", validate_run_id(self.run_id))

    @property
    def evaluation_dir(self) -> Path:
        return self.project_root / "data" / "processed" / "evaluation"

    @property
    def run_dir(self) -> Path:
        return self.evaluation_dir / "runs" / self.run_id

    @property
    def manifest_path(self) -> Path:
        return self.run_dir / "run_manifest.json"

    @property
    def predictions_path(self) -> Path:
        return self.run_dir / "baseline_predictions_unified.csv"

    @property
    def raw_log_path(self) -> Path:
        return self.run_dir / "baseline_raw_responses.jsonl"

    @property
    def tables_dir(self) -> Path:
        return self.run_dir / "comparative_analysis_tables"

    @property
    def docs_dir(self) -> Path:
        return self.project_root / "docs" / "runs" / self.run_id

    @property
    def report_path(self) -> Path:
        return self.docs_dir / "baseline_evaluation_report.md"

    @property
    def dashboard_path(self) -> Path:
        return self.docs_dir / "baseline_dashboard.html"


def prepare_run_directory(artifacts: RunArtifacts, overwrite: bool = False) -> None:
    """Create a new run directory or reject accidental overwrite by default."""
    if artifacts.run_dir.exists() and not overwrite:
        raise FileExistsError(
            f"Run '{artifacts.run_id}' already exists at {artifacts.run_dir}. "
            "Choose a new --run-id or pass --overwrite-run explicitly."
        )
    artifacts.run_dir.mkdir(parents=True, exist_ok=True)


def write_manifest(manifest_path: Path, manifest: dict[str, Any]) -> None:
    """Write the final manifest only after output hashes have been populated."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def append_artifact_hashes(manifest_path: Path, artifacts: dict[str, Path]) -> dict[str, Any]:
    """Record hashes for generated artifacts without changing frozen input metadata."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    generated = manifest.setdefault("generated_artifacts", {})
    for name, path in artifacts.items():
        if not path.exists():
            raise FileNotFoundError(path)
        generated[name] = {
            "relative_path": str(path),
            "sha256": compute_sha256(path),
            "size_bytes": path.stat().st_size,
        }
    write_manifest(manifest_path, manifest)
    return manifest


def verify_run_outputs(artifacts: RunArtifacts) -> dict[str, Any]:
    """Verify the prediction and raw-log hashes recorded by a completed run."""
    manifest = json.loads(artifacts.manifest_path.read_text(encoding="utf-8"))
    expected = manifest.get("output_hashes", {})
    required = {
        artifacts.predictions_path.name: artifacts.predictions_path,
        artifacts.raw_log_path.name: artifacts.raw_log_path,
    }
    for name, path in required.items():
        if expected.get(name) != compute_sha256(path):
            raise ValueError(f"Output hash mismatch for {path}")
    return manifest
