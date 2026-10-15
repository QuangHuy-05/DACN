"""Write an active zero-shot config only after license/hash/RAM/resource gates pass."""

import argparse
import json
from pathlib import Path

from src.evaluation.adapters.deepparse_locked_adapter import zero_shot_gate
from src.evaluation.adapters.deepparse_adapter import SUPPORTED_LABELS, MAPPING_VERSION
from src.evaluation.dev_runner import ROOT, file_hash, write_json

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resources", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    try:
        path, lock = zero_shot_gate(args.resources)
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(json.dumps({"status": "BLOCKED_NO_ACTIVE_CONFIG_WRITTEN", "blocker": str(error)}))
        raise SystemExit(2)
    resources = {"lock": {"path": path.resolve().relative_to(ROOT).as_posix(), "sha256": file_hash(path), "role": "resource_lock"}}
    for component, entry in lock["components"].items():
        for name, digest in entry["files"].items():
            resources[component + ":" + name] = {"path": (Path(entry["path"]) / name).as_posix(), "sha256": digest, "role": component}
    for name in ("configs/deepparse_native_mapping_v1.json", "src/evaluation/adapters/deepparse_locked_adapter.py",
                 "src/evaluation/adapters/deepparse_adapter.py", "src/modeling/deepparse_training.py", "src/modeling/resources.py"):
        resources[name] = {"path": name, "sha256": file_hash(ROOT / name), "role": "mapping_or_loader"}
    config = {"model_id": "DP-ZS-FT", "run_id": args.run_id, "seed": 42, "supported_labels": SUPPORTED_LABELS,
              "t1_implemented": False, "device": "cpu", "mapping_version": MAPPING_VERSION,
              "adapter_factory": "src.evaluation.adapters.deepparse_locked_adapter:LockedDeepparseFastTextAdapter",
              "adapter_kwargs": {"resource_lock_path": path.resolve().relative_to(ROOT).as_posix()},
              "resources": resources, "fine_tuned": False, "offline": True}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, config)
    print(json.dumps({"status": "ACTIVE_ZERO_SHOT_CONFIG_WRITTEN", "output_sha256": file_hash(args.output)}))
