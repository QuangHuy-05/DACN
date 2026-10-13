"""Fetch a completed Kaggle job without loading large checkpoints into RAM."""
import argparse
import importlib
import json
import os
from pathlib import Path

from src.evaluation.dev_runner import ROOT, write_json
from src.modeling.kaggle_handoff import validate_package, verify_download
from src.modeling.kaggle_artifacts import download_output, verify_selected_output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-dir", type=Path, required=True)
    parser.add_argument("--kernel-ref", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--credentials", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--profile", choices=("all", "selection"), default="all")
    parser.add_argument("--reuse-dir", type=Path)
    args = parser.parse_args()
    if args.report.exists():
        raise FileExistsError(args.report)
    args.output_dir.resolve().relative_to((ROOT / "data/interim/modeling/sprint03").resolve())
    if args.reuse_dir:
        args.reuse_dir.resolve().relative_to((ROOT / "data/interim/modeling/sprint03").resolve())
    package = validate_package(args.package_dir.resolve())
    if args.kernel_ref.rsplit("/", 1)[0] != package["kernel_id"]:
        raise ValueError("KERNEL_PACKAGE_ID_MISMATCH")
    environment, _ = importlib.import_module("scripts.50_kaggle_pipeline").credential_environment(args.credentials)
    os.environ.update(environment)
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.authenticate()
    transfer = download_output(api, args.kernel_ref, args.output_dir.resolve(), args.profile, args.reuse_dir)
    verified = (verify_download if args.profile == "all" else verify_selected_output)(args.output_dir.resolve(), package)
    result = {"status": verified["status"], "remote_status": verified["remote_status"],
              "verification": verified, "transfer": transfer}
    write_json(args.report, result)
    print(json.dumps({"status": result["status"], "remote_status": result["remote_status"],
                      "downloaded_bytes": transfer["downloaded_bytes"]}))


if __name__ == "__main__":
    main()
