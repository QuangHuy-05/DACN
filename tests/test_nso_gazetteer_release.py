import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.data.administrative_code_verifier import TemporalGazetteerEvidence, verify_codes
from src.data.nso_gazetteer_release import reconcile_mapping, validate_snapshot_rows


class NsoGazetteerReleaseTests(unittest.TestCase):
    def snapshot_rows(self):
        provinces = [(f"00{index:02d}", f"Tỉnh {index:02d}") for index in range(34)]
        rows = []
        for index in range(3321):
            province_code, province = provinces[index % len(provinces)]
            rows.append({
                "province_code": province_code,
                "province": province,
                "ward_code": f"{index:05d}",
                "ward": f"Xã {index:04d}",
                "resolution": "Nghị quyết 19/2025/NQ-UBTVQH15",
                "effective_date": "2025-07-01",
                "source_locator": f"Sheet1!G{index + 2}:M{index + 2}",
            })
        return rows

    def test_snapshot_requires_dated_unique_3321_codes_and_34_provinces(self):
        self.assertEqual(validate_snapshot_rows(self.snapshot_rows()), {"new_wards": 3321, "new_provinces": 34})
        invalid = self.snapshot_rows()
        invalid[0]["effective_date"] = "2026-01-01"
        with self.assertRaisesRegex(ValueError, "SNAPSHOT_EFFECTIVE_DATE_MISMATCH"):
            validate_snapshot_rows(invalid)

    def test_mapping_reconciliation_accepts_code_join_but_records_name_variant(self):
        with tempfile.TemporaryDirectory() as temp:
            mapping_path = Path(temp) / "mapping.csv"
            with mapping_path.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=["Mã phường/xã mới", "Phường/Xã mới (từ 1/7/2025)", "Tỉnh/TP mới"])
                writer.writeheader()
                writer.writerow({"Mã phường/xã mới": "00001", "Phường/Xã mới (từ 1/7/2025)": "Xã Hòa An", "Tỉnh/TP mới": "Tỉnh A"})
            result = reconcile_mapping([{
                "ward_code": "00001", "ward": "Xã Hoà An", "province": "Tỉnh A",
            }], mapping_path)
        self.assertEqual(result["status"], "EXACT_CODE_AND_PARENT_MATCH_WITH_NAME_VARIANTS")
        self.assertEqual(result["name_variant_count"], 1)
        self.assertEqual(result["code_or_parent_mismatches"], [])
        self.assertEqual(result["name_variants"][0]["code"], "00001")

    def test_mapping_reconciliation_blocks_parent_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            mapping_path = Path(temp) / "mapping.csv"
            with mapping_path.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=["Mã phường/xã mới", "Phường/Xã mới (từ 1/7/2025)", "Tỉnh/TP mới"])
                writer.writeheader()
                writer.writerow({"Mã phường/xã mới": "00001", "Phường/Xã mới (từ 1/7/2025)": "Xã A", "Tỉnh/TP mới": "Tỉnh A"})
            result = reconcile_mapping([{"ward_code": "00001", "ward": "Xã A", "province": "Tỉnh B"}], mapping_path)
        self.assertEqual(result["status"], "BLOCKED_MISMATCH")
        self.assertEqual(len(result["code_or_parent_mismatches"]), 1)

    def make_snapshot_package(self, root: Path) -> TemporalGazetteerEvidence:
        package = root / "gazetteer"
        package.mkdir()
        entity_fields = ["entity_id", "level", "system", "canonical_name", "parent_id", "official_code", "candidate_code", "candidate_code_source_id", "candidate_code_source_hash", "code_status", "valid_from", "valid_to", "source_id", "source_hash", "status"]
        entities = [
            {"entity_id": "moi:province:1", "level": "province", "system": "moi", "canonical_name": "Tỉnh A", "parent_id": "", "official_code": "01", "candidate_code": "", "candidate_code_source_id": "", "candidate_code_source_hash": "", "code_status": "verified_primary_source_snapshot", "valid_from": "2025-07-01", "valid_to": "", "source_id": "nso", "source_hash": "", "status": "verified_official_source_snapshot"},
            {"entity_id": "moi:ward:1", "level": "ward", "system": "moi", "canonical_name": "Xã Hòa An", "parent_id": "moi:province:1", "official_code": "00001", "candidate_code": "", "candidate_code_source_id": "", "candidate_code_source_hash": "", "code_status": "verified_primary_source_snapshot", "valid_from": "2025-07-01", "valid_to": "", "source_id": "nso", "source_hash": "", "status": "verified_official_source_snapshot"},
        ]
        with (package / "entities.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=entity_fields)
            writer.writeheader()
            writer.writerows(entities)
        for name, fields in (("edges.csv", ["old_entity_id", "new_entity_id", "relation"]), ("non_atomic_transitions.csv", ["old_entity_id", "new_entity_id", "relation"])):
            with (package / name).open("w", encoding="utf-8-sig", newline="") as stream:
                csv.DictWriter(stream, fieldnames=fields).writeheader()
        hashes = {}
        for path in package.iterdir():
            hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        (package / "manifest.json").write_text(json.dumps({"version": "test-snapshot", "snapshot_only": True, "snapshot_date": "2025-07-01", "output_sha256": hashes}), encoding="utf-8")
        return TemporalGazetteerEvidence(package)

    def test_snapshot_lookup_rejects_other_dates_and_keeps_code_name_variants(self):
        with tempfile.TemporaryDirectory() as temp:
            gazetteer = self.make_snapshot_package(Path(temp))
            result = gazetteer.lookup("Xã Hòa An", "ward", "2025-07-01", {"province": "Tỉnh A"})
            out_of_scope = gazetteer.lookup("Xã Hòa An", "ward", "2025-07-02", {"province": "Tỉnh A"})
            reference = [{
                "province": "Tỉnh A", "district": "", "ward": "Xã Hòa An", "level": "ward", "system": "moi", "code": "00001",
                "valid_from": "2025-07-01", "valid_to": "", "source_id": "nso", "source_locator": "Sheet1!G2:M2",
                "official_ward_name": "Xã Hoà An", "name_alignment": "CODE_MATCH_NAME_VARIANT",
            }]
            decisions = verify_codes(gazetteer, reference, "2025-07-01")
        self.assertEqual(result["status"], "VERIFIED")
        self.assertEqual(result["candidates"][0]["official_code"], "00001")
        self.assertEqual(result["candidates"][0]["evidence_scope"], "official_primary_source_snapshot")
        self.assertEqual(out_of_scope["status"], "OUT_OF_SNAPSHOT_SCOPE")
        self.assertEqual(decisions[1]["status"], "VERIFIED_PRIMARY_REFERENCE")
        self.assertEqual(decisions[1]["evidence"][0]["name_alignment"], "CODE_MATCH_NAME_VARIANT")


if __name__ == "__main__":
    unittest.main()
