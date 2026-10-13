"""Bounded-memory Kaggle output downloads using the official SDK and pinned version."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil


def parse_kernel_ref(kernel_ref):
    match = re.fullmatch(r"([A-Za-z0-9_-]+)/([a-z0-9-]+)/(\d+)", kernel_ref)
    if not match or int(match.group(3)) < 1:
        raise ValueError("EXACT_KERNEL_VERSION_REQUIRED")
    owner, slug, version = match.groups()
    # Kaggle's SDK expects v1/v2, whereas users and push output use 1/2.
    return owner, slug, "v" + str(int(version))


def output_path(root, name):
    relative = PurePosixPath(name)
    if not name or "\\" in name or ":" in name or relative.is_absolute() or ".." in relative.parts:
        raise ValueError("UNSAFE_REMOTE_ARTIFACT_PATH")
    target = (Path(root) / relative).resolve()
    target.relative_to(Path(root).resolve())
    return target


def stream_response(response, target, max_bytes=19 * 1024**3):
    """Never access Response.content: a checkpoint can exceed the local RAM budget."""
    target = Path(target)
    partial = target.with_name(target.name + ".download.part")
    if target.exists() or partial.exists():
        response.close()
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    digest, total, created = hashlib.sha256(), 0, False
    try:
        response.raise_for_status()
        length = response.headers.get("Content-Length")
        if length and int(length) > max_bytes:
            raise ValueError("REMOTE_ARTIFACT_EXCEEDS_DISK_BUDGET")
        with partial.open("xb") as output:
            created = True
            for block in response.iter_content(chunk_size=1024 * 1024):
                if not block:
                    continue
                total += len(block)
                if total > max_bytes:
                    raise ValueError("REMOTE_ARTIFACT_EXCEEDS_DISK_BUDGET")
                output.write(block)
                digest.update(block)
        if length and response.headers.get("Content-Encoding", "identity") == "identity" and total != int(length):
            raise ValueError("REMOTE_ARTIFACT_TRUNCATED")
        partial.replace(target)
        return {"bytes": total, "sha256": digest.hexdigest()}
    finally:
        response.close()
        if created and partial.exists():
            partial.unlink()


def selected_output(name, profile):
    if profile not in {"all", "selection"}:
        raise ValueError("UNKNOWN_ARTIFACT_PROFILE")
    # Keep every report/sidecar and the best + resumable last weights. Other
    # epoch weights remain in the immutable remote output, with declared hashes.
    return profile == "all" or not name.endswith(".pt") or name.endswith(("/best.pt", "/last.pt"))


def verify_selected_output(directory, package):
    from src.evaluation.dev_runner import file_hash, write_json
    directory = Path(directory)
    indexes = list(directory.rglob("artifact_manifest.json"))
    if len(indexes) != 1:
        raise ValueError("REMOTE_ARTIFACT_MANIFEST_MISSING_OR_AMBIGUOUS")
    index = json.loads(indexes[0].read_text(encoding="utf-8"))
    if index.get("run_id") != package["run_id"] or index.get("identity") != package["identity"]:
        raise ValueError("REMOTE_RUN_IDENTITY_MISMATCH")
    verified, deferred = {}, {}
    for name, digest in index["files"].items():
        path = output_path(indexes[0].parent, name)
        if selected_output(name, "selection"):
            if not path.is_file() or file_hash(path) != digest:
                raise ValueError("REMOTE_OUTPUT_HASH_MISMATCH:" + name)
            verified[name] = digest
        else:
            deferred[name] = digest
    if index.get("status") == "FULL_TRAINING_DEV_ONLY_COMPLETE" and not any(
            name.endswith("/best.pt") for name in verified):
        raise ValueError("SELECTED_CHECKPOINT_MISSING")
    result = {"status": "SELECTED_ARTIFACTS_HASH_VERIFIED", "remote_status": index["status"],
              "identity": index["identity"], "verified_files": verified,
              "remote_only_epoch_checkpoints": deferred,
              "scope": "all reports/sidecars + best/last weights; other epoch weights not downloaded or locally verified"}
    write_json(directory / "download_verification.json", result)
    return result


def reuse_verified_file(source, target, expected_hash):
    from src.evaluation.dev_runner import file_hash
    source, target = Path(source), Path(target)
    if not source.is_file() or file_hash(source) != expected_hash:
        return None
    if target.exists():
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    os.link(source, target)
    return {"bytes": target.stat().st_size, "sha256": expected_hash,
            "transfer_bytes": 0, "method": "hardlink_existing_artifact_verified_against_fresh_remote_index"}


def transfer_with_retry(url, open_response, refresh_url, target, budget, request_error):
    warnings = []
    for attempt in range(3):
        try:
            result = stream_response(open_response(url), target, budget)
            result["transfer_retries"] = warnings
            return result
        except request_error as error:
            status = getattr(getattr(error, "response", None), "status_code", None)
            warnings.append({"attempt": attempt + 1, "error_type": type(error).__name__, "http_status": status})
            if attempt == 2:
                raise RuntimeError("KAGGLE_ARTIFACT_TRANSFER_FAILED:" + type(error).__name__ +
                                   ":HTTP" + str(status)) from None
            # Refresh the URL from the same pinned SDK page. Signed URLs and
            # raw exception messages are never written to reports.
            url = refresh_url()


def download_output(api, kernel_ref, output_dir, profile="all", reuse_dir=None):
    """Use version_label for every page; do not fall back to latest output."""
    import requests
    from kagglesdk.kernels.types.kernels_api_service import ApiListKernelSessionOutputRequest
    owner, slug, version = parse_kernel_ref(kernel_ref)
    selected_output("artifact_manifest.json", profile)
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(output_dir)
    output_dir.mkdir(parents=True)
    token, seen_tokens, seen_paths, records = None, set(), set(), []
    total, transferred, index, index_root = 0, 0, None, None
    while True:
        with api.build_kaggle_client() as client:
            request = ApiListKernelSessionOutputRequest()
            request.user_name, request.kernel_slug, request.version_label = owner, slug, version
            request.page_size, request.page_token = 20, token
            page = client.kernels.kernels_api_client.list_kernel_session_output(request)
        for item in page.files or []:
            target = output_path(output_dir, item.file_name)
            if target in seen_paths:
                raise ValueError("DUPLICATE_REMOTE_ARTIFACT_PATH")
            seen_paths.add(target)
            if not selected_output(item.file_name, profile):
                continue
            result = None
            # The manifest is always fetched fresh. Cache files are accepted
            # only against that exact remote version's declared content hash.
            if reuse_dir is not None and index is not None and target.is_relative_to(index_root):
                relative = target.relative_to(index_root).as_posix()
                expected = index["files"].get(relative)
                if expected:
                    result = reuse_verified_file(output_path(reuse_dir, item.file_name), target, expected)
            if result is not None:
                if total + result["bytes"] > 19 * 1024**3:
                    raise ValueError("REMOTE_ARTIFACT_EXCEEDS_DISK_BUDGET")
                total += result["bytes"]
                records.append({"path": item.file_name, **result})
                continue
            def refresh_current_url():
                with api.build_kaggle_client() as client:
                    retry = ApiListKernelSessionOutputRequest()
                    retry.user_name, retry.kernel_slug, retry.version_label = owner, slug, version
                    retry.page_size, retry.page_token = 20, token
                    updated = client.kernels.kernels_api_client.list_kernel_session_output(retry)
                matches = [entry.url for entry in updated.files or [] if entry.file_name == item.file_name]
                if len(matches) != 1:
                    raise ValueError("PINNED_REMOTE_FILE_DISAPPEARED")
                return matches[0]
            budget = min(19 * 1024**3 - total, shutil.disk_usage(output_dir).free - 256 * 1024**2)
            result = transfer_with_retry(item.url, lambda url: requests.get(url, stream=True, timeout=(30, 90)),
                                         refresh_current_url, target, budget, requests.RequestException)
            total += result["bytes"]
            transferred += result["bytes"]
            records.append({"path": item.file_name, **result})
            if target.name == "artifact_manifest.json":
                index = json.loads(target.read_text(encoding="utf-8"))
                index_root = target.parent
        next_token = page.next_page_token
        if not next_token:
            break
        if next_token in seen_tokens:
            raise ValueError("REPEATED_REMOTE_PAGE_TOKEN")
        seen_tokens.add(next_token)
        token = next_token
    return {"kernel_ref": kernel_ref, "profile": profile, "files": records, "downloaded_bytes": transferred,
            "resident_logical_bytes": total, "reused_bytes": total - transferred,
            "GB": transferred / 1e9, "GiB": transferred / 2**30,
            "method": "1MiB chunks, exact SDK version_label, atomic files; optional fresh-index-verified hardlinks"}
