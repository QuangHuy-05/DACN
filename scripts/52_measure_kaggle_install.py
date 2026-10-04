"""Measure new D-only installation and package bytes without double-counting old resources."""

import json
import argparse
from pathlib import Path
import os
import subprocess

from src.evaluation.dev_runner import ROOT, file_hash, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    setup = ROOT / "data/interim/modeling/sprint03/kaggle_setup_20261004_v1"
    runtime = ROOT / "data/interim/modeling/sprint03/kaggle_runtime_d_v1"
    groups = {"installed_cli_environment": runtime, "download_cache_and_evidence": setup}
    groups.update({"handoff_" + path.name: path
                  for path in (ROOT / "data/interim/modeling/sprint03").glob("kaggle_*20261004_v*")
                  if path.is_dir() and path != setup})
    existing = ROOT / "data/interim/modeling/sprint03/pre_colab_20261003_resume_v1/handoff_v1/dacn_phobert_resources_v1.zip"
    stat = existing.stat()
    seen = {(stat.st_dev, stat.st_ino)}
    result = {}
    for name, folder in groups.items():
        logical, unique, files, reused = 0, 0, 0, 0
        for path in sorted(folder.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            info = path.stat()
            logical += info.st_size
            files += 1
            identity = (info.st_dev, info.st_ino)
            if identity in seen:
                reused += info.st_size
            else:
                seen.add(identity)
                unique += info.st_size
        result[name] = {"logical_bytes": logical, "additional_unique_file_bytes": unique,
                        "reused_hardlink_bytes": reused, "files": files,
                        "GB": unique / 10**9, "GiB": unique / 1024**3}
    installed = subprocess.check_output([str(runtime / "bin/python"), "-m", "pip", "freeze"], text=True)
    package_list = setup / "installed_packages.txt"
    if package_list.exists() and package_list.read_text() != installed:
        raise ValueError("CLI_PACKAGE_SET_CHANGED_SINCE_INSTALL")
    if not package_list.exists():
        package_list.write_text(installed)
    total = sum(row["additional_unique_file_bytes"] for row in result.values())
    value = {"method": "regular file stat sizes; no symlink targets; deduplicate st_dev/st_ino and exclude pre-existing resource archive inode; not a filesystem block-allocation measurement",
             "groups": result, "total_additional_unique_file_bytes": total,
             "GB": total / 10**9, "GiB": total / 1024**3,
             "installed_packages": installed.splitlines(), "new_local_models_downloaded": 0,
             "all_new_local_install_and_cache": "D:/DACN/data/interim/modeling/sprint03",
             "remote_checkpoint_download_bytes": "report separately after smoke; not a local package installation"}
    output = args.output or setup / "disk_install_report.json"
    if output.exists():
        raise FileExistsError(output)
    write_json(output, value)
    print(json.dumps({key: val for key, val in value.items() if key != "installed_packages"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
