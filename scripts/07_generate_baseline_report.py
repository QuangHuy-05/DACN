"""Generate a versioned Markdown report from one completed baseline run."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evaluation.manifest import compute_sha256
from src.evaluation.reporter import generate_baseline_report_markdown
from src.evaluation.run_artifacts import RunArtifacts, verify_run_outputs


def generate_report(run_id: str) -> Path:
    """Verify a completed run then write its report beneath `docs/runs/<run_id>`."""
    artifacts = RunArtifacts(ROOT, run_id)
    manifest = verify_run_outputs(artifacts)
    if manifest.get("run_id") != run_id:
        raise ValueError(f"Manifest run ID mismatch: expected {run_id}, got {manifest.get('run_id')}")

    df_eval = pd.read_csv(artifacts.predictions_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    if manifest.get("output_hashes", {}).get(artifacts.raw_log_path.name) != compute_sha256(artifacts.raw_log_path):
        raise ValueError(f"Output changed after run: {artifacts.raw_log_path}")

    report_manifest = dict(manifest)
    report_manifest["reporter_sha256"] = compute_sha256(ROOT / "src/evaluation/reporter.py")
    md = generate_baseline_report_markdown(
        df_eval,
        manifest_data=report_manifest,
        benchmark_dir=ROOT / "data/processed/benchmark",
        raw_log_path=artifacts.raw_log_path,
    )
    artifacts.docs_dir.mkdir(parents=True, exist_ok=True)
    artifacts.report_path.write_text(md, encoding="utf-8")
    print(f"[DONE] Baseline evaluation report saved to {artifacts.report_path}")
    return artifacts.report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a report for one versioned baseline run.")
    parser.add_argument("--run-id", required=True, help="Run identifier created by script 05 or 06")
    args = parser.parse_args()
    generate_report(args.run_id)


if __name__ == "__main__":
    main()
