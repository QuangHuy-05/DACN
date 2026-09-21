"""Run the baseline protocol on a stratified pilot in its own artifact directory."""

import argparse
from importlib import import_module


def run_pilot(run_id: str, overwrite: bool = False) -> None:
    import_module("scripts.06_run_baseline_full").run_full_evaluation(
        run_id=run_id,
        sample_per_dataset=20,
        overwrite=overwrite,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a versioned stratified baseline pilot.")
    parser.add_argument("--run-id", required=True, help="Unique lowercase run identifier, e.g. baseline_v2_pilot")
    parser.add_argument("--overwrite-run", action="store_true", help="Explicitly allow replacing files in an existing run directory")
    args = parser.parse_args()
    run_pilot(args.run_id, overwrite=args.overwrite_run)
