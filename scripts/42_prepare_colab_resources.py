"""Record source/license/resource evidence; no model downloads, imports or training."""

import argparse
from importlib import metadata
import json
from pathlib import Path
import urllib.request
import urllib.error

from src.evaluation.dev_runner import ROOT, file_hash, write_json
from src.modeling.resources import validate_resource_lock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir = args.output_dir.resolve()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    source_urls = {
        "deepparse_hub": "https://huggingface.co/api/models/deepparse/fasttext-base?blobs=true",
        "fasttext_terms": "https://fasttext.cc/docs/en/crawl-vectors.html",
        "pytorch_profile": "https://pytorch.org/get-started/previous-versions/",
        "colab_faq": "https://research.google.com/colaboratory/faq.html",
    }
    write_json(args.output_dir / "inventory_before.json", {"install": [], "estimated_metadata_bytes": 1000000,
              "downloads": source_urls, "purpose": "metadata/license only", "target": args.output_dir.relative_to(ROOT).as_posix()})
    downloads = {}
    for name, url in source_urls.items():
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (DACN source verification)"})
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = response.read(2000001)
        except (urllib.error.URLError, TimeoutError) as error:
            downloads[name] = {"url": url, "status": "DOWNLOAD_BLOCKED", "error": str(error), "bytes": 0}
            continue
        if len(payload) > 2000000:
            raise ValueError("METADATA_RESPONSE_TOO_LARGE")
        target = args.output_dir / (name + (".json" if name == "deepparse_hub" else ".html"))
        target.write_bytes(payload)
        downloads[name] = {"url": url, "sha256": file_hash(target), "bytes": len(payload)}
    hub = json.loads((args.output_dir / "deepparse_hub.json").read_text())
    lock_path = ROOT / "data/interim/modeling/sprint03/task_01_06_20261003_v1/resource_lock_local_v1.json"
    lock = validate_resource_lock(lock_path, "PHOBERT-CRF")
    write_json(args.output_dir / "phobert_resource_lock_local.json", lock)
    registry = [{"resource": name, "source_url": entry.get("source_url") or entry.get("license_source_url"),
                 "revision": entry["revision"], "license": entry.get("license"), "license_status": entry["license_status"],
                 "path": entry["path"], "files": entry["files"], "local_status": "HASH_VERIFIED"}
                for name, entry in lock["components"].items()]
    registry += [
        {"resource": "full_fasttext_native_deepparse", "file": "cc.fr.300.bin", "source_url": "https://dl.fbaipublicfiles.com/fasttext/vectors-crawl/cc.fr.300.bin.gz",
         "native_identity_evidence": "deepparse 0.11.0 download_tools.py download_fasttext_embeddings", "license": "CC-BY-SA-3.0", "license_source_url": source_urls["fasttext_terms"],
         "license_status": "CLEARED_WITH_ATTRIBUTION_SHARE_ALIKE", "local_status": "NOT_DOWNLOADED", "local_sha256": None,
         "estimated_compressed_bytes": 6800000000, "minimum_available_ram_bytes": 10 * 1024**3,
         "conditions": "Preserve attribution and share-alike terms for any redistributed/adapted embedding; do not substitute Vietnamese/light FastText."},
        {"resource": "deepparse_base_checkpoint", "source_url": "https://huggingface.co/deepparse/fasttext-base", "revision": hub["sha"],
         "license": hub.get("cardData", {}).get("license"), "license_status": "UNKNOWN" if not hub.get("cardData", {}).get("license") else "REQUIRES_SCOPE_REVIEW",
         "files_upstream": hub.get("siblings", []), "local_status": "NOT_DOWNLOADED", "local_sha256": None,
         "blocker": "checkpoint weight license not stated in model card; repository code license is a separate scope"},
    ]
    for path, role in ((ROOT / "data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv", "administrative_mapping"),
                       (ROOT / "third_party/vietnamadminunits/data/raw/danhmuchanhchinh.gso.gov.vn_ward_2025-07-18.csv", "third_party_ward"),
                       (ROOT / "third_party/vietnamadminunits/data/raw/danhmuchanhchinh.gso.gov.vn_district_2025-07-18.csv", "third_party_district")):
        registry.append({"resource": role, "path": path.relative_to(ROOT).as_posix(), "sha256": file_hash(path),
                         "source_url": "https://danhmuchanhchinh.nso.gov.vn/" if role == "administrative_mapping" else "https://github.com/tranngocminhhieu/vietnamadminunits",
                         "license_status": "PUBLIC_PORTAL_TERMS_NOT_LOCATED", "redistribution": "NOT_CLEARED_BY_THIS_AUDIT", "original_export_url": "UNVERIFIED"})
    packages = {dist.metadata["Name"]: dist.version for dist in metadata.distributions() if dist.metadata.get("Name")}
    write_json(args.output_dir / "source_resource_registry.json", {"resources": registry, "packages": packages, "metadata_downloads": downloads})
    write_json(args.output_dir / "deepparse_download_recipe_pending.json", {
        "model_family": "DP-FT-FT", "status": "PROSPECTIVE_NOT_AN_ACTIVE_LOCK", "repository": "deepparse/fasttext-base", "revision": hub["sha"],
        "embedding": "cc.fr.300.bin", "embedding_url": "https://dl.fbaipublicfiles.com/fasttext/vectors-crawl/cc.fr.300.bin.gz",
        "steps": ["resolve checkpoint license scope", "check 10 GiB host RAM plus compressed/extracted/cache/checkpoint disk", "download pinned upstream resources into one declared offline cache", "record actual SHA256 and licenses", "verify native offline loader with the full embedding", "publish active resource lock after these gates"],
        "native_integration": "PENDING_FULL_FASTTEXT", "local_download_executed": False,
        "blockers": ["CHECKPOINT_LICENSE_UNVERIFIED", "FULL_EMBEDDING_NOT_DOWNLOADED", "LOCAL_HOST_RAM_BELOW_10_GIB"]})
    # These files are new profiles, outside the previously frozen modeling configs.
    profile_dir = ROOT / "configs/colab/sprint03"
    profile_dir.mkdir(parents=True, exist_ok=True)
    profile_path = profile_dir / "cuda128_profile_v1.json"
    if profile_path.exists():
        raise FileExistsError(profile_path)
    write_json(profile_path, {"version": "s3-colab-cuda128-v1", "device": "cuda:0", "precision": "float32", "amp": False,
                            "torch_version": "2.8.0", "cuda_wheel_index": "https://download.pytorch.org/whl/cu128",
                            "min_vram_bytes": 8 * 1024**3, "protocol_lock_sha256": file_hash(ROOT / "configs/modeling/sprint03/protocol_lock_v1.json")})
    freeze = profile_dir / "requirements_transitive_v1.txt"
    if freeze.exists():
        raise FileExistsError(freeze)
    freeze.write_text("\n".join(f"{name}=={version}" for name, version in sorted(packages.items()) if name.casefold() not in {"torch", "pip", "setuptools", "wheel"}) + "\n")
    write_json(args.output_dir / "installation_accounting.json", {"new_packages_installed": [], "new_model_weights_downloaded": [], "new_install_bytes": 0,
              "new_install_gb": 0, "new_install_gib": 0, "metadata_download_bytes": sum(entry["bytes"] for entry in downloads.values()),
              "prior_install_total_bytes": 2453588804, "prior_total_scope": "historical 03/10 install inventory; not a remeasurement of current disk"})
    print(json.dumps({"status": "RESOURCE_DOSSIER_PREPARED_WITH_DECLARED_DP_BLOCKERS", "hub_revision": hub["sha"], "new_install_bytes": 0}))


if __name__ == "__main__":
    main()
