"""Build/upload private train-dev jobs; smoke first, never test100 or implicit full training."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME = ROOT / "data/interim/modeling/sprint03/kaggle_runtime_d_v1"


def credential_environment(path=None):
    env = dict(os.environ)
    secret_values = []
    if path:
        value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        if not isinstance(value.get("username"), str) or not isinstance(value.get("key"), str):
            raise ValueError("Expected Kaggle legacy credentials; file content must not be pasted in chat")
        env.update(KAGGLE_USERNAME=value["username"], KAGGLE_KEY=value["key"])
        secret_values.append(value["key"])
    for key in ("KAGGLE_KEY", "KAGGLE_API_TOKEN"):
        if env.get(key):
            secret_values.append(env[key])
    if not secret_values:
        raise ValueError("KAGGLE_AUTH_REQUIRED: supply --credentials or KAGGLE_API_TOKEN")
    cache = ROOT / "data/interim/modeling/sprint03/kaggle_setup_20261004_v1/cache"
    for key, name in (("KAGGLE_CONFIG_DIR", "config"), ("XDG_CACHE_HOME", "xdg"),
                      ("XDG_CONFIG_HOME", "config"), ("TMPDIR", "tmp")):
        target = cache / name
        target.mkdir(parents=True, exist_ok=True)
        env[key] = str(target)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["TQDM_DISABLE"] = "1"
    return env, secret_values


def kaggle_call(arguments, runtime=DEFAULT_RUNTIME, credentials=None, report=None, timeout=900, entry_module=None):
    if report and Path(report).exists():
        raise FileExistsError(report)
    env, secrets = credential_environment(credentials)
    executable = Path(runtime) / ("bin/python" if entry_module else "bin/kaggle")
    if not executable.is_file():
        raise FileNotFoundError("Install the inventoried Kaggle CLI environment first")
    command = [str(executable), "-m", entry_module, *arguments] if entry_module else [str(executable), *arguments]
    result = subprocess.run(command, cwd=ROOT, env=env,
                            capture_output=True, text=True, timeout=timeout)
    output = result.stdout + result.stderr
    for secret in secrets:
        output = output.replace(secret, "[REDACTED]")
    # Kaggle CLI may return exit 0 after an API-level kernel push rejection.
    code = result.returncode
    if code == 0 and any(marker in output for marker in ("Kernel push error:", "not valid dataset sources")):
        code = 2
    record = {"timestamp": datetime.now(timezone.utc).isoformat(),
              "command": ["python", "-m", entry_module, *arguments] if entry_module else ["kaggle", *arguments],
              "returncode": code, "process_returncode": result.returncode, "output": output,
              "status": "API_COMMAND_SUCCEEDED" if code == 0 else "API_COMMAND_FAILED"}
    if report:
        report = Path(report)
        if report.exists():
            raise FileExistsError(report)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": record["status"], "returncode": code,
                      "message": "\n".join(line for line in output.splitlines() if "%|" not in line)[:4000]}, ensure_ascii=False))
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "relaunch", "authcheck", "quota", "upload", "submit", "status", "dataset-status", "inspect", "fetch"))
    parser.add_argument("--package-dir", type=Path)
    parser.add_argument("--source-package", type=Path)
    parser.add_argument("--username")
    parser.add_argument("--run-id", default="dacn-s3-kaggle-smoke-20261004-v1")
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--credentials", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--kernel-ref", help="owner/slug/version for an exact remote run")
    parser.add_argument("--artifact-profile", choices=("all", "selection"), default="all")
    parser.add_argument("--reuse-dir", type=Path)
    parser.add_argument("--mode", choices=("preflight", "smoke", "full"), default="smoke")
    parser.add_argument("--allow-full-training", action="store_true")
    parser.add_argument("--smoke-evidence", type=Path)
    parser.add_argument("--model", choices=("PHOBERT-CRF", "PROPOSED-DYN"), default="PHOBERT-CRF")
    parser.add_argument("--candidate", choices=("c01", "c02"), default="c01")
    args = parser.parse_args()
    if args.action == "relaunch":
        from src.modeling.kaggle_handoff import build_relaunch
        if not args.package_dir or not args.source_package:
            parser.error("relaunch requires --package-dir and --source-package")
        print(json.dumps(build_relaunch(args.package_dir.resolve(), args.source_package.resolve(), args.run_id)))
        return
    if args.action == "prepare":
        from src.modeling.kaggle_handoff import build_kaggle_package
        if not args.username or not args.package_dir:
            parser.error("prepare requires --username and --package-dir")
        print(json.dumps(build_kaggle_package(args.package_dir.resolve(), args.username, args.run_id,
              args.mode, args.allow_full_training, args.smoke_evidence, args.model, args.candidate), ensure_ascii=False))
        return
    if args.action in {"authcheck", "quota"}:
        command = ["datasets", "list", "--mine", "--page-size", "1"] if args.action == "authcheck" else ["quota", "--format", "json"]
        result = kaggle_call(command,
                             args.runtime, args.credentials, args.report)
        raise SystemExit(result["returncode"])
    if not args.package_dir:
        parser.error("--package-dir required")
    from src.modeling.kaggle_handoff import validate_package
    manifest = validate_package(args.package_dir.resolve())
    if args.action == "upload":
        if manifest.get("reuses_uploaded_package"):
            raise ValueError("RELAUNCH_REUSES_EXISTING_DATASET: no upload required")
        command = ["datasets", "create", "-p", str(args.package_dir.resolve() / "dataset"), "--keep-tabular", "--dir-mode", "skip"]
    elif args.action == "submit":
        if manifest["mode"] == "full" and not args.allow_full_training:
            raise ValueError("FULL_TRAINING_DISABLED_BY_DEFAULT")
        command = ["kernels", "push", "-p", str(args.package_dir.resolve() / "kernel"), "--timeout",
                   "43200" if manifest["mode"] == "full" else "1800"]
    elif args.action == "status":
        command = ["kernels", "status", args.kernel_ref or manifest["kernel_id"]]
    elif args.action == "dataset-status":
        command = ["datasets", "status", manifest["dataset_id"]]
    elif args.action == "inspect":
        if not args.output_dir:
            parser.error("inspect requires --output-dir")
        args.output_dir.resolve().relative_to((ROOT / "data/interim/modeling/sprint03").resolve())
        if args.output_dir.exists():
            raise FileExistsError(args.output_dir)
        command = ["kernels", "pull", manifest["kernel_id"], "--metadata", "-p", str(args.output_dir.resolve())]
    else:
        if not args.output_dir:
            parser.error("fetch requires --output-dir")
        args.output_dir.resolve().relative_to((ROOT / "data/interim/modeling/sprint03").resolve())
        if args.output_dir.exists():
            raise FileExistsError("Fetch into a new directory; never overwrite old artifacts")
        if not args.kernel_ref:
            parser.error("fetch requires --kernel-ref owner/slug/version")
        command = ["--package-dir", str(args.package_dir.resolve()), "--kernel-ref", args.kernel_ref,
                   "--output-dir", str(args.output_dir.resolve()), "--report",
                   str(args.output_dir.with_name(args.output_dir.name + "_transfer.json").resolve()),
                   "--profile", args.artifact_profile]
        if args.reuse_dir:
            command.extend(["--reuse-dir", str(args.reuse_dir.resolve())])
        result = kaggle_call(command, args.runtime, args.credentials, args.report, timeout=7200,
                             entry_module="scripts.60_download_kaggle_artifacts")
        raise SystemExit(result["returncode"])
    result = kaggle_call(command, args.runtime, args.credentials, args.report)
    raise SystemExit(result["returncode"])


if __name__ == "__main__":
    main()
