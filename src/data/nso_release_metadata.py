"""Complete source-register metadata in a new package; graph/code bytes stay frozen."""

import csv
from collections import Counter
import json
from pathlib import Path
import shutil

from src.data.nso_dual_snapshot import DualSnapshotGazetteer
from src.evaluation.dev_runner import ROOT, file_hash, write_json


def complete_source_register(parent: Path, evidence: Path, output: Path):
    if output.exists() or output.with_name(output.name + ".staging").exists():
        raise FileExistsError(output)
    gaz = DualSnapshotGazetteer(parent)
    downloads = json.loads((evidence / "download_manifest.json").read_text())
    with (parent / "source_register.csv").open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, sources = reader.fieldnames, list(reader)
    for entry in downloads["responses"]:
        if entry["query"] != {"DenNgay": "30/06/2025"}:
            continue
        response = evidence / "responses" / entry["response_file"]
        if file_hash(response) != entry["sha256"]:
            raise ValueError("SOURCE_RESPONSE_HASH_MISMATCH")
        source_id = "nso_soap_" + entry["operation"] + "_2025-06-30"
        sources.append({"source_id": source_id, "name": "NSO dated SOAP " + entry["operation"],
                        "path_or_url": entry["source_url"], "level_scope": entry["operation"], "system": "cu",
                        "valid_range": "verified_as_of_2025-06-30_only_not_legal_interval",
                        "access_date": entry.get("retrieved_at_utc", entry.get("retrieved_at", "2026-10-03")),
                        "license": "PUBLIC_PORTAL_TERMS_NOT_LOCATED", "sha256": entry["sha256"],
                        "role": "primary_source_exact_old_code_parent_snapshot", "source_export_sha256": entry["sha256"]})
    staging = output.with_name(output.name + ".staging")
    shutil.copytree(parent, staging)
    with (staging / "source_register.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(sources)
    manifest = dict(gaz.manifest)
    manifest.update(version="s3-gazetteer-v4.2-nso-dual-snapshot-partial", parent_version=gaz.manifest["version"],
                    parent_manifest_sha256=file_hash(parent / "manifest.json"),
                    metadata_module_sha256=file_hash(Path(__file__)))
    # An inherited single-day summary must not masquerade as the aggregate total.
    manifest["parent_new_snapshot_summary"] = manifest.pop("official_code_snapshot", {})
    verified_counts = Counter(row["system"] for row in gaz.entities if row["code_status"] == "verified_primary_source_snapshot")
    manifest["verified_code_counts"] = {"cu": verified_counts["cu"], "moi": verified_counts["moi"], "total": sum(verified_counts.values())}
    coverage = json.loads((staging / "coverage_report.json").read_text())
    coverage["graph_counts"] = manifest["counts"]
    write_json(staging / "coverage_report.json", coverage)
    write_json(staging / "metadata_completion.json", {
        "changes": ["add three dated official SOAP responses to source register", "separate inherited new-only summary from dual-snapshot totals"],
        "unchanged": {name: file_hash(parent / name) for name in ("entities.csv", "aliases.csv", "edges.csv", "non_atomic_transitions.csv", "code_evidence.csv")},
        "source_download_manifest_sha256": file_hash(evidence / "download_manifest.json")})
    manifest["output_sha256"] = {path.name: file_hash(path) for path in staging.iterdir() if path.is_file() and path.name != "manifest.json"}
    write_json(staging / "manifest.json", manifest)
    DualSnapshotGazetteer(staging)
    staging.rename(output)
    return {"status": "METADATA_COMPLETION_RELEASED", "package": output.relative_to(ROOT).as_posix(), "source_register_rows": len(sources)}
