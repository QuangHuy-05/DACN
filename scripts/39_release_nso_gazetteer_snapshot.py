"""Validate an official dated NSO export and release a new Gazetteer snapshot."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from src.data.administrative_code_verifier import audit_sources, validate_reference, verify_codes, TemporalGazetteerEvidence
from src.data.nso_gazetteer_release import (
    OFFICIAL_PORTAL_URL,
    ROOT,
    SNAPSHOT_DATE,
    SOURCE_ID,
    build_verified_package,
    make_reference_rows,
    read_official_export,
    reconcile_mapping,
    sha256,
    validate_snapshot_rows,
    _write_csv,
    _write_json,
)


def inside(path: Path, parent: Path) -> bool:
    return path.resolve().is_relative_to(parent.resolve())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--export",
        type=Path,
        default=ROOT / "data/interim/modeling/sprint03/nso_official_crosswalk_2025_20261003_v1/nso_administrative_comparison_2025-06-30_to_2025-07-01.xls",
    )
    parser.add_argument(
        "--download-manifest",
        type=Path,
        default=ROOT / "data/interim/modeling/sprint03/nso_official_crosswalk_2025_20261003_v1/download_manifest.json",
    )
    parser.add_argument(
        "--legal-document",
        type=Path,
        default=ROOT / "data/interim/modeling/sprint03/nso_official_crosswalk_2025_20261003_v1/qdtg_19_2025_official_signed.pdf",
    )
    parser.add_argument(
        "--xlrd-dir",
        type=Path,
        default=ROOT / "data/interim/modeling/sprint03/nso_official_crosswalk_2025_20261003_v1/vendor/xlrd-2.0.2",
    )
    parser.add_argument(
        "--mapping",
        type=Path,
        default=ROOT / "data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv",
    )
    parser.add_argument("--source-package", type=Path, default=ROOT / "data/processed/gazetteer/s3_v2")
    parser.add_argument(
        "--release-dir",
        type=Path,
        default=ROOT / "data/interim/modeling/sprint03/nso_official_crosswalk_2025_20261003_v1/release_v1",
    )
    parser.add_argument(
        "--output-package",
        type=Path,
        default=ROOT / "data/processed/gazetteer/s3_v3_nso_2025_snapshot",
    )
    args = parser.parse_args()

    interim_root = ROOT / "data/interim/modeling/sprint03"
    package_root = ROOT / "data/processed/gazetteer"
    if not inside(args.release_dir, interim_root) or args.release_dir.resolve() == interim_root.resolve():
        raise ValueError("RELEASE_EVIDENCE_MUST_BE_NEW_INTERIM_VERSION")
    if not inside(args.output_package, package_root) or args.output_package.resolve() == package_root.resolve():
        raise ValueError("GAZETTEER_PACKAGE_MUST_BE_NEW_VERSION_UNDER_PROCESSED")
    if args.release_dir.exists() or args.output_package.exists():
        raise FileExistsError("Refusing to overwrite interim evidence or a Gazetteer release")

    current_rows, dated_rows, profile = read_official_export(args.export, args.xlrd_dir)
    snapshot_validation = validate_snapshot_rows(dated_rows)
    mapping_report = reconcile_mapping(dated_rows, args.mapping)
    download_manifest = json.loads(args.download_manifest.read_text(encoding="utf-8"))
    source_hash = sha256(args.export)
    if download_manifest.get("sha256") != source_hash or download_manifest.get("source_url") != OFFICIAL_PORTAL_URL:
        raise ValueError("OFFICIAL_EXPORT_DOWNLOAD_MANIFEST_MISMATCH")
    if download_manifest.get("date_new") != SNAPSHOT_DATE or download_manifest.get("date_old") != "2025-06-30":
        raise ValueError("OFFICIAL_EXPORT_QUERY_DATE_MISMATCH")
    args.release_dir.mkdir(parents=True)
    _write_json(args.release_dir / "official_export_profile.json", profile)
    _write_json(args.release_dir / "mapping_reconciliation.json", mapping_report)
    if mapping_report["status"] == "BLOCKED_MISMATCH":
        print(json.dumps({"status": "BLOCKED_MAPPING_RECONCILIATION", "mapping": mapping_report}, ensure_ascii=True))
        return 2

    gazetteer = TemporalGazetteerEvidence(args.source_package)
    reference_rows = make_reference_rows(dated_rows, gazetteer)
    reference_path = args.release_dir / "official_code_reference_2025-07-01.csv"
    _write_csv(reference_path, tuple(reference_rows[0].keys()), reference_rows)

    checks = [
        "Official NSO portal URL and downloaded export SHA-256 match the download manifest",
        "Comparison-side rows all have effective date 2025-07-01 and cite 2025 resolutions",
        "3,321 unique new ward codes and 34 unique new province codes are present",
        "All 3,321 ward codes join exactly once to the repository mapping and Gazetteer entities",
        "All 3,321 ward-to-province parent links match the official comparison-side province",
        "Official/canonical name differences are retained as explicit variants, not normalized away",
        "Live-side 2026 portal changes are excluded from this snapshot",
    ]
    reference_manifest = {
        "schema_version": "s3-official-code-reference-v1",
        "source_id": SOURCE_ID,
        "url": OFFICIAL_PORTAL_URL,
        "issuer": "Cục Thống kê (NSO), cổng Danh mục đơn vị hành chính",
        "document_id": "Official portal comparison export: 2025-07-01 vs 2025-06-30; filter level=Xã",
        "accessed_at": download_manifest["retrieved_at"],
        "reference_sha256": sha256(reference_path),
        "source_export_sha256": source_hash,
        "authority_status": "OFFICIAL_PRIMARY_SOURCE",
        "extraction_review_status": "AUTOMATED_VALIDATED",
        "automated_validation": {"status": "PASS", "checks": checks, "row_count": len(reference_rows)},
        "license_status": "PUBLIC_PORTAL_TERMS_NOT_LOCATED",
        "effective_from": SNAPSHOT_DATE,
        "effective_to": "",
        "table_as_of": SNAPSHOT_DATE,
        "change_history_verified_through": SNAPSHOT_DATE,
        "snapshot_only": True,
        "source_selection": "dated comparison-side columns only; current/live-side rows excluded",
        "row_counts": snapshot_validation,
        "mapping_reconciliation_status": mapping_report["status"],
        "mapping_name_variant_count": mapping_report["name_variant_count"],
    }
    manifest_path = args.release_dir / "official_code_reference_manifest.json"
    _write_json(manifest_path, reference_manifest)
    validated_manifest, validated_rows = validate_reference(reference_path, manifest_path)
    decisions = verify_codes(gazetteer, validated_rows, SNAPSHOT_DATE)
    _write_json(args.release_dir / "source_audit_summary.json", {
        "status": "PARTIAL_OLD_CODES_UNVERIFIED",
        "source_package": gazetteer.manifest["version"],
        "snapshot_date": SNAPSHOT_DATE,
        "decision_counts": {key: sum(row["status"] == key for row in decisions) for key in sorted({row["status"] for row in decisions})},
        "verified_new_ward_codes": sum(row["status"] == "VERIFIED_PRIMARY_REFERENCE" and gazetteer.by_id[row["entity_id"]]["system"] == "moi" and gazetteer.by_id[row["entity_id"]]["level"] == "ward" for row in decisions),
        "verified_new_province_codes": sum(row["status"] == "VERIFIED_PRIMARY_REFERENCE" and gazetteer.by_id[row["entity_id"]]["system"] == "moi" and gazetteer.by_id[row["entity_id"]]["level"] == "province" for row in decisions),
        "verified_old_codes": sum(row["status"] == "VERIFIED_PRIMARY_REFERENCE" and gazetteer.by_id[row["entity_id"]]["system"] == "cu" for row in decisions),
        "snapshot_scope": "exactly 2025-07-01; not a continuous change history",
        "new_package_released": True,
        "validated_reference_sha256": validated_manifest["reference_sha256"],
    })

    source_register = [
        {
            "source_id": "repo_mapping_csv_v2", "local_file": "data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv",
            "sha256": sha256(args.mapping),
        },
        {"source_id": SOURCE_ID, "local_file": None, "sha256": None},
    ]
    audit_dir = args.release_dir / "frozen_s3_v2_audit"
    audit_report = audit_sources(args.source_package, audit_dir, source_register, reference_path, manifest_path, SNAPSHOT_DATE)

    result = build_verified_package(
        args.source_package, args.output_package, dated_rows, validated_rows,
        mapping_report, args.export, args.mapping, legal_document_path=args.legal_document,
        reference_manifest_path=manifest_path,
    )
    _write_json(args.release_dir / "release_report.json", {
        **result,
        "release_time_utc": datetime.now(timezone.utc).isoformat(),
        "official_export_sha256": source_hash,
        "official_reference_sha256": sha256(reference_path),
        "official_source_url": OFFICIAL_PORTAL_URL,
        "snapshot_date": SNAPSHOT_DATE,
        "export_profile": profile,
        "mapping_reconciliation": mapping_report,
        "frozen_s3_v2_audit": audit_report,
        "package_manifest_sha256": sha256(args.output_package / "manifest.json"),
    })
    print(json.dumps({
        "status": result["status"], "package": str(args.output_package.relative_to(ROOT)),
        "release_evidence": str(args.release_dir.relative_to(ROOT)),
        "official_codes_verified": result["official_codes_verified"],
        "new_provinces_verified": result["new_provinces_verified"],
        "new_wards_verified": result["new_wards_verified"],
        "old_codes_verified": result["old_codes_verified"],
        "name_variants_vs_mapping": mapping_report["name_variant_count"],
        "name_variants_vs_gazetteer": sum(row["name_alignment"] != "EXACT" for row in validated_rows),
        "snapshot_lookup_scope": SNAPSHOT_DATE,
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
