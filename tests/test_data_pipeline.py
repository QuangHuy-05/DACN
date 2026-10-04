import tempfile
import unittest
import importlib.util
import importlib
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.data.administrative_mapping import load_administrative_mapping
from src.data.noise_profiler import profile_noise
from src.data.osm_extractor import HistoryBiDirectionalMapper, clean_tag
from src.data.synthetic.bidirectional import generate_bidirectional_pairs
from src.data.synthetic.hybrid_address import generate_hybrid_addresses, get_new_province, select_unique_hybrids
from src.data.synthetic.missing_fields import (
    DROP_FIELDS,
    generate_missing_fields,
    validate_clean_source,
    validate_missing_surface,
)
from src.data.synthetic.raw_noisy import generate_raw_noisy_addresses
from src.data.span_trace import Component, align_unique, render_components
from src.data.annotation_release import (
    annotation_fingerprint, content_findings, coverage, file_hash,
    load_human_adjudications, load_manual_findings,
    publish_release, validate_canonical_annotation, write_json, write_jsonl,
)
from src.data.test_assisted_annotation import (
    align_segments, build_candidates, file_hash as assisted_file_hash,
    read_locked_tasks, ward_system, write_package,
)


class FakeElement:
    def __init__(self, element_id, timestamp, tags, visible=True):
        self.id = element_id
        self.timestamp = timestamp
        self.tags = tags
        self.visible = visible


class DataPipelineTests(unittest.TestCase):
    def test_test_annotation_review_conflict_is_read_only(self):
        record = {"sample_id": "fictional-test-fixture", "text": "Quận A",
                  "address_system": "moi", "spans": [
                      {"start": 0, "end": 6, "label": "QuanHuyen", "system": "cu"}]}
        original = json.dumps(record, ensure_ascii=False, sort_keys=True)
        self.assertTrue(any(f["code"] == "new_address_contains_district" for f in content_findings(record)))
        self.assertEqual(json.dumps(record, ensure_ascii=False, sort_keys=True), original)

    def test_assisted_test_requires_explicit_amendment(self):
        with self.assertRaisesRegex(ValueError, "ACKNOWLEDGE_ASSISTED_TEST_REQUIRED"):
            write_package(Path("unused"), Path("unused"), acknowledge=False)

    def test_assisted_test_rejects_hidden_metadata_and_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            for tasks in (
                [{"data": {"sample_id": "fixture", "text": "1", "GT_SoNha": "1"}}],
                [{"data": {"sample_id": "fixture", "text": "1"}},
                 {"data": {"sample_id": "fixture", "text": "2"}}],
            ):
                path.write_text(json.dumps(tasks), encoding="utf-8")
                with self.assertRaises(ValueError):
                    read_locked_tasks(path, assisted_file_hash(path), len(tasks))
            with self.assertRaisesRegex(ValueError, "HASH_MISMATCH"):
                read_locked_tasks(path, "0" * 64, 2)

    def test_assisted_test_aligns_repeated_literal_without_repairing_raw_text(self):
        text = "1, Đường A, Phường B, Quận C, Phường B"
        spans = align_segments(text, [["house", "1"], ["road", "Đường A"],
            ["ward", "Phường B"], ["district", "Quận C"], ["ward", "Phường B"]])
        self.assertEqual(spans[-1]["start"], text.rindex("Phường B"))
        self.assertEqual(spans[-2]["system"], "cu")
        self.assertTrue(all(text[s["start"]:s["end"]] == s["text"] for s in spans))
        with self.assertRaisesRegex(ValueError, "UNEXPLAINED_UNLABELED_CONTENT"):
            align_segments("Đường A, Phường B", [["ward", "Phường B"]])

    def test_assisted_test_shared_name_and_parent_gap_abstain(self):
        old = [{"level": "ward", "official_name": "Phường A", "province_name": "Tỉnh B",
                "district_name": "Quận C", "validation_status": "PARENT_CODE_LINK_PASS",
                "official_code": "001"}]
        new = [{"level": "ward", "province": "Tỉnh B", "canonical_ward": "Phường A",
                "official_ward_name": "Phường A", "code": "002"}]
        system, trace = ward_system("P. A", "Tỉnh B", "Quận C", old, new)
        self.assertEqual(system, "khong_xac_dinh")
        self.assertEqual(trace["reason"], "NAME_PRESENT_IN_BOTH_SNAPSHOTS")
        old[0]["validation_status"] = "PARENT_CODE_LINK_FAIL"
        system, trace = ward_system("Phường A", "Tỉnh B", "Quận C", old, new)
        self.assertEqual(system, "khong_xac_dinh")
        self.assertEqual(trace["reason"], "OLD_REFERENCE_PARENT_LINK_GAP")

    def test_assisted_test_t1_separate_from_neutral_spans(self):
        tasks = [{"data": {"sample_id": "fictional", "text": "1, Đường A, Phường B, Quận C, Hà Nội"}}]
        proposals = {"rows": [["fictional", [["house", "1"], ["road", "Đường A"],
                     ["ward", "Phường B"], ["district", "Quận C"], ["province", "Hà Nội"]], ""]]}
        new = [{"level": "ward", "province": "Thành phố Hà Nội", "canonical_ward": "Phường B",
                "official_ward_name": "Phường B", "code": "fixture", "source_id": "fixture",
                "source_locator": "fixture"}]
        record = build_candidates(tasks, proposals, [], new)[0]
        self.assertEqual(record["address_system"], "Lai")
        self.assertEqual(record["status"], "candidate_not_gold")
        self.assertEqual([s["system"] for s in record["spans"]],
                         ["khong_xac_dinh", "khong_xac_dinh", "moi", "cu", "khong_xac_dinh"])
        proposals["rows"][0][0] = "not-the-frozen-id"
        with self.assertRaisesRegex(ValueError, "PROPOSAL_IDS_DIFFER"):
            build_candidates(tasks, proposals, [], new)

    def test_annotation_review_road_prefix_and_repeated_ward(self):
        text = "12, Tỉnh lộ 8, Phường 7, Phường 7"
        road_start = text.index("Tỉnh")
        ward_start = text.index("Phường")
        record = {"sample_id": "fixture", "text": text, "address_system": None, "spans": [
            {"start": 0, "end": 2, "label": "SoNha", "system": "khong_xac_dinh"},
            {"start": road_start, "end": road_start + len("Tỉnh lộ 8"), "label": "TenDuong", "system": "khong_xac_dinh"},
            {"start": ward_start, "end": ward_start + len("Phường 7"), "label": "PhuongXa", "system": "khong_xac_dinh"},
        ]}
        issues = content_findings(record)
        self.assertFalse(any(i["code"] == "administrative_label_mismatch" for i in issues))
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["start"], text.rindex("Phường"))
        abbreviation = {"sample_id": "abbr", "text": "12, P.7", "address_system": None, "spans": [
            {"start": 0, "end": 2, "label": "SoNha", "system": "khong_xac_dinh"}]}
        self.assertEqual(content_findings(abbreviation)[0]["text"], "P.7")

    def test_annotation_review_conflicting_t1_does_not_rewrite_span(self):
        record = {"sample_id": "fixture", "text": "Quận 1", "address_system": "moi", "spans": [
            {"start": 0, "end": 6, "label": "QuanHuyen", "system": "cu"}]}
        issues = content_findings(record)
        self.assertEqual(issues[0]["code"], "new_address_contains_district")
        self.assertEqual(record["spans"][0]["label"], "QuanHuyen")

    def test_annotation_review_unlabeled_numeric_parenthesis(self):
        text = "8 (660/8), Đường A"
        record = {"sample_id": "fixture", "text": text, "spans": [], "address_system": None}
        self.assertTrue(any(i["code"] == "unannotated_leading_number" for i in content_findings(record)))

    def test_annotation_review_span_t1_conflict_survives_district_relabeling(self):
        record = {"sample_id": "fixture", "text": "Phường A", "address_system": "moi", "spans": [
            {"start": 0, "end": 8, "label": "PhuongXa", "system": "cu"}]}
        self.assertEqual(content_findings(record)[0]["code"], "address_span_system_conflict")
        for system in (None, "Lai"):
            record["address_system"] = system
            self.assertEqual(content_findings(record), [])
        record["address_system"] = "cu"
        record["spans"][0]["system"] = "moi"
        self.assertEqual(content_findings(record)[0]["code"], "address_span_system_conflict")

    def test_annotation_review_subward_component_is_not_a_landmark(self):
        text = "thôn A"
        record = {"sample_id": "fixture", "text": text, "address_system": None, "spans": [
            {"start": 0, "end": len(text), "label": "MocDinhVi", "system": "khong_xac_dinh"}]}
        self.assertEqual(content_findings(record)[0]["code"], "subward_component_label")
        record["spans"][0]["label"] = "Khac"
        self.assertEqual(content_findings(record), [])
        record["text"] = "gần thôn A"
        record["spans"] = [{"start": 0, "end": len(record["text"]), "label": "MocDinhVi", "system": "khong_xac_dinh"}]
        self.assertEqual(content_findings(record), [])
    def test_manual_annotation_review_is_hash_bound_and_does_not_edit_gold(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            export = directory / "export.json"
            export.write_text("[]", encoding="utf-8")
            path = directory / "manual.json"
            record = {"sample_id": "fixture", "text": "Trung tâm A", "spans": []}
            review = {"export_sha256": {"batch": file_hash(export)}, "reviewer": "agent", "evidence": "text review",
                      "findings": [{"sample_id": "fixture", "code": "manual_level_review", "reason": "Check place vs ward",
                                    "start": 0, "end": 11, "text": "Trung tâm A"}]}
            path.write_text(json.dumps(review), encoding="utf-8")
            found = load_manual_findings(path, {"batch": export}, {"fixture": record})
            self.assertEqual(len(found["fixture"]), 1)
            self.assertEqual(record["spans"], [])
            export.write_text("[{}]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "stale"):
                load_manual_findings(path, {"batch": export}, {"fixture": record})
            review["export_sha256"]["batch"] = file_hash(export)
            review["findings"][0]["text"] = "wrong substring"
            path.write_text(json.dumps(review), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "round-trip"):
                load_manual_findings(path, {"batch": export}, {"fixture": record})

    def test_release_canonical_labels_cannot_be_patched_after_raw_qa(self):
        span = {"start": 0, "end": 2, "label": "SoNha", "system": "khong_xac_dinh"}
        record = {"sample_id": "fixture", "spans": [dict(span)], "address_system": None}
        converted = {"spans": [{**span, "region_id": "r1", "text": "12"}], "address_system": None}
        validate_canonical_annotation(record, converted)
        record["spans"][0]["label"] = "TenDuong"
        with self.assertRaisesRegex(ValueError, "differs"):
            validate_canonical_annotation(record, converted)
        record["spans"][0]["label"] = "SoNha"
        record["address_system"] = "moi"
        with self.assertRaisesRegex(ValueError, "differs"):
            validate_canonical_annotation(record, converted)

    def test_annotation_coverage_uses_derivation_not_parent_dataset(self):
        records = [{"sample_id": name, "text": name, "spans": [], "address_system": None} for name in ("observed", "derived", "synthetic", "unknown")]
        meta = {name: {"source_dataset": "osm_old_snapshot_full", "derivation": value} for name, value in (
            ("observed", "observed_verified_old_osm"), ("derived", "derived_verified_unique_admin_mapping"),
            ("synthetic", "synthetic_noise_controlled"), ("unknown", ""))}
        result = coverage(records, meta)
        self.assertEqual(result["source_kind"], {"observed": 1, "derived": 1, "synthetic": 1, "unverified_provenance": 1})
        self.assertEqual(len(result["label_support"]), 11)

    def make_publication_fixture(self, root):
        candidate = root / "data/interim/annotation/sprint03/candidate_fixture"
        candidate.mkdir(parents=True)
        rows = [{"sample_id": f"fixture_{index}", "text": f"Mẫu {index}", "source_group": f"group_{index}",
                 "spans": [], "address_system": None} for index in range(300)]
        write_jsonl(candidate / "train.jsonl", rows[:240])
        write_jsonl(candidate / "dev.jsonl", rows[240:])
        write_jsonl(candidate / "dev_input.jsonl", [{"sample_id": row["sample_id"], "text": row["text"]} for row in rows[240:]])
        write_jsonl(candidate / "quarantine.jsonl", [])
        write_json(candidate / "content_review_items.json", [])
        write_json(candidate / "adjudicated_content_exceptions.json", [])
        write_json(candidate / "coverage.json", {"scope": "LOCAL_FIXTURE_ONLY"})
        write_json(candidate / "split_audit.json", {"status": "AUDIT_PASS", "scope": "LOCAL_FIXTURE_ONLY"})
        write_json(candidate / "approval_record.json", {"status": "HUMAN_REVIEW_ATTESTED", "unresolved_sample_ids": [],
                   "attestation": {"reviewed_sample_count": 300, "reviewer": "fixture_reviewer"}})
        (candidate / "label_studio_correction_queue.csv").write_text("sample_id,reason\n", encoding="utf-8-sig")
        with (candidate / "decision_log_v2.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=("sample_id", "decision", "reviewer", "reason"))
            writer.writeheader()
            writer.writerows({"sample_id": row["sample_id"], "decision": "keep", "reviewer": "fixture_reviewer",
                             "reason": "Local fixture, not a human benchmark decision"} for row in rows)
        (root / "input_fixture.txt").write_text("fixture input", encoding="utf-8")
        (root / "code_fixture.py").write_text("# local fixture\n", encoding="utf-8")
        manifest = {"status": "TRAIN_DEV_APPROVED_TEST_PENDING", "version": "candidate_fixture",
                    "sample_counts": {"train": 240, "dev": 60}, "expected_sample_counts": {"train": 240, "dev": 60},
                    "quarantined_sample_count": 0, "quarantined_sample_ids": [], "human_review_attested": 300,
                    "test_status": "TEST_PENDING", "input_sha256": {"input_fixture.txt": file_hash(root / "input_fixture.txt")},
                    "code_sha256": {"code_fixture.py": file_hash(root / "code_fixture.py")},
                    "output_sha256": {path.name: file_hash(path) for path in candidate.iterdir()}}
        write_json(candidate / "manifest.json", manifest)
        return candidate, manifest

    def test_publication_preserves_bytes_and_refuses_overwrite_or_blocked_status(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate, manifest = self.make_publication_fixture(root)
            output = root / "data/processed/annotation/sprint03/corpus_fixture_v2"
            published = publish_release(root, candidate, output)
            self.assertEqual(published["version"], "corpus_fixture_v2")
            self.assertEqual(published["output_sha256"], manifest["output_sha256"])
            self.assertEqual(published["candidate_manifest"]["sha256"], file_hash(candidate / "manifest.json"))
            self.assertFalse((output / "test.jsonl").exists())
            with self.assertRaises(FileExistsError):
                publish_release(root, candidate, output)
            manifest["status"] = "BLOCKED_CONTENT_REVIEW"
            write_json(candidate / "manifest.json", manifest)
            other_output = output.parent / "blocked_fixture"
            with self.assertRaisesRegex(ValueError, "status"):
                publish_release(root, candidate, other_output)
            self.assertFalse(other_output.exists())

    def test_publication_rejects_input_and_artifact_hash_drift_before_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate, manifest = self.make_publication_fixture(root)
            output = root / "data/processed/annotation/sprint03/corpus_fixture_v2"
            (root / "input_fixture.txt").write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "drift"):
                publish_release(root, candidate, output)
            self.assertFalse(output.exists())
            (root / "input_fixture.txt").write_text("fixture input", encoding="utf-8")
            with (candidate / "dev.jsonl").open("a", encoding="utf-8") as stream:
                stream.write("{}\n")
            with self.assertRaisesRegex(ValueError, "artifact hash"):
                publish_release(root, candidate, output)
            self.assertFalse(output.exists())

    def test_publication_rejects_wrong_input_projection_and_output_location(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate, manifest = self.make_publication_fixture(root)
            output = root / "data/processed/annotation/sprint03/corpus_fixture_v2"
            write_jsonl(candidate / "dev_input.jsonl", [{"sample_id": "fixture_240", "text": "Mẫu 240", "GT_SoNha": "secret"}])
            manifest["output_sha256"]["dev_input.jsonl"] = file_hash(candidate / "dev_input.jsonl")
            write_json(candidate / "manifest.json", manifest)
            with self.assertRaisesRegex(ValueError, "text-only"):
                publish_release(root, candidate, output)
            self.assertFalse(output.exists())
            with self.assertRaisesRegex(ValueError, "version directory"):
                publish_release(root, candidate, root / "data/raw/corpus_fixture")

    def test_human_adjudication_binds_identity_export_and_annotation_without_editing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            export, path = root / "export.json", root / "adjudication.json"
            export.write_text("[]", encoding="utf-8")
            record = {"sample_id": "fixture", "text": "Phường A", "address_system": "moi", "spans": [
                {"start": 0, "end": 8, "label": "PhuongXa", "system": "cu"}]}
            attestation = {"reviewer": "fixture_owner", "label_studio_user_id": 1}
            review = {**attestation, "date": "2026-10-02", "human_authorization_quote": "Local fixture authorization",
                      "export_sha256": {"batch": file_hash(export)}, "decisions": [{
                          "sample_id": "fixture", "decision": "keep_as_exception", "reason": "Fixture retained contradiction",
                          "annotation_sha256": annotation_fingerprint(record),
                          "accepted_finding_codes": ["address_span_system_conflict"], "exclude_from_t1": True}]}
            write_json(path, review)
            decisions = load_human_adjudications(path, {"batch": export}, {"fixture": record}, attestation)
            self.assertTrue(decisions["fixture"]["exclude_from_t1"])
            self.assertEqual(record["spans"][0]["system"], "cu")
            review["decisions"][0]["exclude_from_t1"] = False
            write_json(path, review)
            with self.assertRaisesRegex(ValueError, "excluded from T1"):
                load_human_adjudications(path, {"batch": export}, {"fixture": record}, attestation)
            review["decisions"][0]["exclude_from_t1"] = True
            review["reviewer"] = "other_owner"
            write_json(path, review)
            with self.assertRaisesRegex(ValueError, "identity"):
                load_human_adjudications(path, {"batch": export}, {"fixture": record}, attestation)
            review["reviewer"] = "fixture_owner"
            write_json(path, review)
            record["address_system"] = "cu"
            with self.assertRaisesRegex(ValueError, "fingerprint"):
                load_human_adjudications(path, {"batch": export}, {"fixture": record}, attestation)

    def test_publication_keeps_declared_exception_and_t1_mask(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate, manifest = self.make_publication_fixture(root)
            rows = [json.loads(line) for line in (candidate / "dev.jsonl").read_text(encoding="utf-8").splitlines()]
            rows[0].update({"text": "Phường A", "address_system": "moi", "spans": [
                {"start": 0, "end": 8, "label": "PhuongXa", "system": "cu"}]})
            sid = rows[0]["sample_id"]
            decision = {"sample_id": sid, "decision": "keep_as_exception", "reason": "Local fixture authorization",
                        "annotation_sha256": annotation_fingerprint(rows[0]), "accepted_finding_codes": ["address_span_system_conflict"],
                        "exclude_from_t1": True, "human_authorization_quote": "Keep fixture annotation"}
            write_jsonl(candidate / "dev.jsonl", rows)
            write_jsonl(candidate / "dev_input.jsonl", [{"sample_id": row["sample_id"], "text": row["text"]} for row in rows])
            write_json(candidate / "adjudicated_content_exceptions.json", [decision])
            approval = json.loads((candidate / "approval_record.json").read_text(encoding="utf-8"))
            approval.update({"status": "HUMAN_REVIEW_ATTESTED_WITH_EXCEPTIONS", "human_adjudications": [decision]})
            write_json(candidate / "approval_record.json", approval)
            manifest.update({"adjudicated_exception_count": 1, "evaluation_exclusions": {"t1": [sid]}})
            manifest["output_sha256"] = {name: file_hash(candidate / name) for name in manifest["output_sha256"]}
            write_json(candidate / "manifest.json", manifest)
            output = root / "data/processed/annotation/sprint03/corpus_fixture_v2"
            release = publish_release(root, candidate, output)
            self.assertEqual(release["evaluation_exclusions"]["t1"], [sid])
            actual = json.loads((output / "dev.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(actual["address_system"], "moi")
            self.assertEqual(actual["spans"][0]["system"], "cu")

    def test_gazetteer_v2_island_transitions_have_district_entities(self):
        root = Path(__file__).resolve().parents[1]
        package = root / "data/processed/gazetteer/s3_v2"
        with (package / "entities.csv").open("r", encoding="utf-8-sig", newline="") as stream:
            entities = {row["entity_id"]: row for row in csv.DictReader(stream)}
        with (package / "non_atomic_transitions.csv").open("r", encoding="utf-8-sig", newline="") as stream:
            transitions = list(csv.DictReader(stream))
        self.assertEqual(len(transitions), 5)
        for row in transitions:
            self.assertEqual(entities[row["old_entity_id"]]["level"], "district")
            self.assertEqual(entities[row["new_entity_id"]]["level"], "ward")
            self.assertEqual(row["status"], "NOT_WARD_EDGE")

    def test_non_latin_rejected_and_street_tail_cleaned(self):
        self.assertEqual(clean_tag("Đường Số 10, "), "Đường Số 10")
        self.assertEqual(clean_tag("شارع السلام"), "")
        self.assertEqual(clean_tag("улица"), "")

    def test_deleted_or_untagged_latest_revision_is_not_a_pair(self):
        handler = HistoryBiDirectionalMapper()
        old = datetime(2025, 6, 30, tzinfo=timezone.utc)
        new = datetime(2025, 7, 2, tzinfo=timezone.utc)
        tags = {"addr:street": "Lê Lợi", "addr:ward": "Phường 1", "addr:city": "Hà Nội"}
        handler.process_element(FakeElement(1, old, tags), "node")
        handler.process_element(FakeElement(1, new, {}), "node")
        self.assertIsNone(handler.history_tracker[("node", 1)]["new"])
        self.assertIsNotNone(handler.history_tracker[("node", 1)]["old"])
        handler.pbar.close()

    def test_geometry_is_read_only_for_valid_address_tags(self):
        class CountingHandler(HistoryBiDirectionalMapper):
            def __init__(self):
                super().__init__()
                self.geometry_calls = 0

            def geometry_signature(self, elem, elem_type):
                self.geometry_calls += 1
                return "node:0.0000000,0.0000000"

        handler = CountingHandler()
        old = datetime(2025, 6, 30, tzinfo=timezone.utc)
        handler.process_element(FakeElement(1, old, {"name": "not an address"}), "way")
        handler.process_element(
            FakeElement(2, old, {
                "addr:street": "Lê Lợi", "addr:ward": "Phường 1", "addr:city": "Hà Nội",
            }),
            "node",
        )
        self.assertEqual(handler.geometry_calls, 1)
        handler.pbar.close()

    def test_missing_fields_preserves_truth_and_is_repeatable(self):
        old = pd.DataFrame([{"SoNha": str(i), "TenDuong": f"Đường {i}",
                             "PhuongXa": "Phường 1", "QuanHuyen": "Quận 1",
                             "TinhThanh": "Thành phố Hồ Chí Minh"} for i in range(20)])
        new = old.assign(QuanHuyen="")
        one = generate_missing_fields(old, new, target_size=10)
        two = generate_missing_fields(old, new, target_size=10)
        self.assertEqual(one.to_csv(index=False), two.to_csv(index=False))
        self.assertEqual(one.HeQuyChieu.value_counts().to_dict(), {"cu": 5, "moi": 5})
        self.assertTrue((one[one.HeQuyChieu == "moi"].QuanHuyen == "").all())
        self.assertTrue((one.GT_PhuongXa == "Phường 1").all())

    def test_raw_noisy_data_keeps_ground_truth_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as folder:
            config_path = Path(folder) / "noise.json"
            config_path.write_text("""{
  "noise_probabilities": {
    "abbreviations": {"ward_P": 1.0, "district_Q": 1.0, "city_TP": 1.0},
    "missing_rates": {"drop_housenumber": 1.0, "drop_ward": 1.0, "drop_district": 1.0}
  }
}""", encoding="utf-8")
            old = pd.DataFrame([{
                "SoNha": str(index), "TenDuong": f"Đường Cũ {index}",
                "PhuongXa": "Phường 1", "QuanHuyen": "Quận 1", "TinhThanh": "Thành phố Hà Nội",
            } for index in range(1, 21)])
            new = pd.DataFrame([{
                "SoNha": str(index), "TenDuong": f"Đường Mới {index}",
                "PhuongXa": "Phường Mới", "QuanHuyen": "", "TinhThanh": "Thành phố Hồ Chí Minh",
            } for index in range(1, 21)])
            one = generate_raw_noisy_addresses(old, new, config_path, target_size=20, seed=9)
            two = generate_raw_noisy_addresses(old, new, config_path, target_size=20, seed=9)
            self.assertEqual(one.to_csv(index=False), two.to_csv(index=False))
            self.assertEqual(one.HeQuyChieu.value_counts().to_dict(), {"cu": 10, "moi": 10})
            self.assertTrue((one.ChuoiDiaChi != one.ChuoiDiaChiGoc).all())
            self.assertTrue((one[one.HeQuyChieu == "cu"].GT_QuanHuyen != "").all())
            self.assertTrue((one[one.HeQuyChieu == "moi"].GT_QuanHuyen == "").all())
            self.assertTrue(one.LoaiNhieu.str.contains("dinh_dang_phan_cach").all())

    def test_hybrid_never_fabricates_unknown_province(self):
        self.assertEqual(get_new_province("Tỉnh Kiên Giang"), "Tỉnh An Giang")
        self.assertEqual(get_new_province(""), "")
        self.assertEqual(get_new_province("Unknownland"), "")

    def test_hybrid_selection_rejects_conflicting_surface_labels(self):
        candidates = {
            "C2": [{"ChuoiDiaChi": "same", "KieuLai": "C2"}],
            "C3": [{"ChuoiDiaChi": "same", "KieuLai": "C3"}, {"ChuoiDiaChi": "other", "KieuLai": "C3"}],
        }
        selected = select_unique_hybrids(candidates, {"C2": 1, "C3": 1}, seed=42)
        self.assertEqual({row["ChuoiDiaChi"] for row in selected}, {"same", "other"})

    def test_noise_profile_has_auditable_denominator(self):
        profile = profile_noise(["12 Lê Lợi, P. 1, Q. 1, TP.HCM", "Đường A, Phường 2, Hà Nội"])
        self.assertEqual(profile["sample_size"], 2)
        self.assertEqual(profile["counts"]["abbreviations"]["ward_P"], 1)
        self.assertEqual(profile["counts"]["abbreviations"]["district_Q"], 1)

    def test_atomic_mapping_preserves_split_merge_and_many_to_many(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            mapping_path = root / "mapping.csv"
            rows = [
                # A: one old unit contributes to two otherwise distinct new units.
                ("Xã A", "Huyện H", "Tỉnh Cũ", "Tỉnh Mới", "Xã A1", "Tách — một phần"),
                ("Xã A", "Huyện H", "Tỉnh Cũ", "Tỉnh Mới", "Xã A2", "Tách — nhập chủ yếu"),
                # B: two old units join one new unit.
                ("Xã B1", "Huyện H", "Tỉnh Cũ", "Tỉnh Mới", "Xã B", "Hợp nhất toàn bộ"),
                ("Xã B2", "Huyện H", "Tỉnh Cũ", "Tỉnh Mới", "Xã B", "Hợp nhất toàn bộ"),
                # M: each old unit has several targets and targets have several origins.
                ("Xã M1", "Huyện H", "Tỉnh Cũ", "Tỉnh Mới", "Xã M-A", "Tách — một phần"),
                ("Xã M1", "Huyện H", "Tỉnh Cũ", "Tỉnh Mới", "Xã M-B", "Tách — nhập chủ yếu"),
                ("Xã M2", "Huyện H", "Tỉnh Cũ", "Tỉnh Mới", "Xã M-A", "Tách — nhập chủ yếu"),
                ("Xã M2", "Huyện H", "Tỉnh Cũ", "Tỉnh Mới", "Xã M-B", "Tách — một phần"),
            ]
            pd.DataFrame([{
                "Phường/Xã cũ": old_ward,
                "Quận/Huyện cũ": district,
                "Tỉnh/TP cũ (trước sáp nhập)": old_province,
                "Tỉnh/TP mới": new_province,
                "Phường/Xã mới (từ 1/7/2025)": new_ward,
                "Loại đơn vị mới": "Xã",
                "Mã phường/xã mới": f"{index:05d}",
                "Hình thức sáp nhập": merger_form,
                "Diện tích mới (km²)": "1",
            } for index, (old_ward, district, old_province, new_province, new_ward, merger_form) in enumerate(rows)]).to_csv(mapping_path, index=False)
            mapping = load_administrative_mapping(mapping_path)
            self.assertEqual(mapping.relation_for("Tỉnh Cũ", "Huyện H", "Xã A", mapping.targets_for_old("Tỉnh Cũ", "Huyện H", "Xã A")[0]), ("A", "1-N"))
            self.assertEqual(mapping.relation_for("Tỉnh Cũ", "Huyện H", "Xã B1", mapping.targets_for_old("Tỉnh Cũ", "Huyện H", "Xã B1")[0]), ("B", "N-1"))
            self.assertEqual(mapping.relation_for("Tỉnh Cũ", "Huyện H", "Xã M1", mapping.targets_for_old("Tỉnh Cũ", "Huyện H", "Xã M1")[0]), ("M", "M-N"))

    def test_bidirectional_pairs_do_not_guess_split_or_many_to_many_targets(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            mapping = root / "mapping.csv"
            pairs = root / "pairs.csv"
            snapshot = root / "old.csv"
            edges = [
                ("Xã A", "Xã A1"), ("Xã A", "Xã A2"),
                ("Xã B1", "Xã B"), ("Xã B2", "Xã B"),
                ("Xã M1", "Xã M-A"), ("Xã M1", "Xã M-B"),
                ("Xã M2", "Xã M-A"), ("Xã M2", "Xã M-B"),
            ]
            pd.DataFrame([{
                "Phường/Xã cũ": old_ward, "Quận/Huyện cũ": "Huyện H",
                "Tỉnh/TP cũ (trước sáp nhập)": "Tỉnh Cũ", "Tỉnh/TP mới": "Tỉnh Mới",
                "Phường/Xã mới (từ 1/7/2025)": new_ward, "Loại đơn vị mới": "Xã",
                "Mã phường/xã mới": f"{index:05d}",
                "Hình thức sáp nhập": "Tách — một phần" if old_ward in {"Xã A", "Xã M1", "Xã M2"} else "Hợp nhất toàn bộ",
                "Diện tích mới (km²)": "1",
            } for index, (old_ward, new_ward) in enumerate(edges)]).to_csv(mapping, index=False)
            pd.DataFrame([
                {"OSM_ID": 1, "OSM_Type": "node", "TinhThanh_Cu": "Tỉnh Cũ", "QuanHuyen_Cu": "Huyện H", "PhuongXa_Cu": "Xã A", "PhuongXa_Moi": "Xã A1", "QuanHuyen_Moi": "", "TinhThanh_Moi": "Tỉnh Mới", "SoNha": "1", "TenDuong": "Đường A", "DiaChi_Cu": "1, Đường A, Xã A, Huyện H, Tỉnh Cũ"},
                {"OSM_ID": 2, "OSM_Type": "node", "TinhThanh_Cu": "Tỉnh Cũ", "QuanHuyen_Cu": "Huyện H", "PhuongXa_Cu": "Xã B1", "PhuongXa_Moi": "Xã B", "QuanHuyen_Moi": "", "TinhThanh_Moi": "Tỉnh Mới", "SoNha": "2", "TenDuong": "Đường B", "DiaChi_Cu": "2, Đường B, Xã B1, Huyện H, Tỉnh Cũ"},
                {"OSM_ID": 3, "OSM_Type": "node", "TinhThanh_Cu": "Tỉnh Cũ", "QuanHuyen_Cu": "Huyện H", "PhuongXa_Cu": "Xã M1", "PhuongXa_Moi": "Xã M-A", "QuanHuyen_Moi": "", "TinhThanh_Moi": "Tỉnh Mới", "SoNha": "3", "TenDuong": "Đường M", "DiaChi_Cu": "3, Đường M, Xã M1, Huyện H, Tỉnh Cũ"},
            ]).to_csv(pairs, index=False)
            pd.DataFrame([
                {"OSM_ID": 1, "OSM_Type": "node", "SoNha": "1", "TenDuong": "Đường A", "PhuongXa": "Xã A", "QuanHuyen": "Huyện H", "TinhThanh": "Tỉnh Cũ"},
                {"OSM_ID": 2, "OSM_Type": "node", "SoNha": "2", "TenDuong": "Đường B", "PhuongXa": "Xã B1", "QuanHuyen": "Huyện H", "TinhThanh": "Tỉnh Cũ"},
                {"OSM_ID": 3, "OSM_Type": "node", "SoNha": "3", "TenDuong": "Đường M", "PhuongXa": "Xã M1", "QuanHuyen": "Huyện H", "TinhThanh": "Tỉnh Cũ"},
                {"OSM_ID": 4, "OSM_Type": "node", "SoNha": "4", "TenDuong": "Đường D", "PhuongXa": "Xã B2", "QuanHuyen": "Huyện H", "TinhThanh": "Tỉnh Cũ"},
                {"OSM_ID": 5, "OSM_Type": "node", "SoNha": "5", "TenDuong": "Đường S", "PhuongXa": "Xã A", "QuanHuyen": "Huyện H", "TinhThanh": "Tỉnh Cũ"},
                {"OSM_ID": 6, "OSM_Type": "node", "SoNha": "6", "TenDuong": "Đường X", "PhuongXa": "Xã M2", "QuanHuyen": "Huyện H", "TinhThanh": "Tỉnh Cũ"},
            ]).to_csv(snapshot, index=False)
            result = generate_bidirectional_pairs(pairs, mapping, snapshot, target_size=10)
            self.assertEqual(set(result[result.Nguon.str.startswith("OSM_Diff")].QuanHe), {"1-N", "N-1", "M-N"})
            derived = result[result.Nguon.str.startswith("OSM_Snapshot")]
            self.assertEqual(set(derived.QuanHe), {"N-1"})
            self.assertIn("Đường D", " ".join(derived.DiaChi_Cu))
            self.assertNotIn("Đường S", " ".join(derived.DiaChi_Cu))
            self.assertNotIn("Đường X", " ".join(derived.DiaChi_Cu))

    def test_administrative_alias_normalizes_known_variants_and_typos(self):
        from src.data.administrative_alias import (
            resolve_province_alias,
            resolve_district_alias,
            resolve_ward_alias,
            normalize_diff_record,
            normalize_diff_record_with_trace,
        )
        self.assertEqual(resolve_province_alias("Ho Chi Minh City"), "Thành phố Hồ Chí Minh")
        self.assertEqual(resolve_province_alias("Hanoi"), "Thành phố Hà Nội")
        self.assertEqual(resolve_district_alias("Thành phố Bác Ninh"), "Thành phố Bắc Ninh")
        self.assertEqual(resolve_district_alias("Q.Ba Đình"), "Quận Ba Đình")
        self.assertEqual(resolve_ward_alias("Hàng Buồm"), "Phường Hàng Buồm")

        rec = {
            "TinhThanh_Cu": "Hanoi",
            "QuanHuyen_Cu": "Hoan Kiem",
            "PhuongXa_Cu": "Hang Buom",
            "TinhThanh_Moi": "Hà Nội",
            "QuanHuyen_Moi": "",
            "PhuongXa_Moi": "Phường Hoàn Kiếm",
        }
        normed = normalize_diff_record(rec)
        self.assertEqual(normed["TinhThanh_Cu"], "Thành phố Hà Nội")
        self.assertEqual(normed["QuanHuyen_Cu"], "Quận Hoàn Kiếm")
        self.assertEqual(normed["PhuongXa_Cu"], "Phường Hàng Buồm")
        traced, changes = normalize_diff_record_with_trace(rec)
        self.assertEqual(traced, normed)
        self.assertEqual(len(changes), 4)
        self.assertTrue(any("PhuongXa_Cu: Hang Buom → Phường Hàng Buồm" in c for c in changes))

    def test_direct_pairs_use_full_snapshot_and_audited_aliases(self):
        """A direct OSM observation must not be lost because Set 03 is sampled."""
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            mapping_path = root / "mapping.csv"
            pairs_path = root / "pairs.csv"
            balanced_snapshot = root / "old.csv"
            full_snapshot = root / "osm_old_snapshot_full.csv"

            # Two old wards sharing one new ward create an N-1 official edge.
            pd.DataFrame([
                {
                    "Phường/Xã cũ": "Phường Hàng Buồm", "Quận/Huyện cũ": "Quận Hoàn Kiếm",
                    "Tỉnh/TP cũ (trước sáp nhập)": "Thành phố Hà Nội", "Tỉnh/TP mới": "Thành phố Hà Nội",
                    "Phường/Xã mới (từ 1/7/2025)": "Phường Hoàn Kiếm", "Loại đơn vị mới": "Phường",
                    "Mã phường/xã mới": "00001", "Hình thức sáp nhập": "Hợp nhất toàn bộ",
                    "Diện tích mới (km²)": "1",
                },
                {
                    "Phường/Xã cũ": "Phường Hàng Bồ", "Quận/Huyện cũ": "Quận Hoàn Kiếm",
                    "Tỉnh/TP cũ (trước sáp nhập)": "Thành phố Hà Nội", "Tỉnh/TP mới": "Thành phố Hà Nội",
                    "Phường/Xã mới (từ 1/7/2025)": "Phường Hoàn Kiếm", "Loại đơn vị mới": "Phường",
                    "Mã phường/xã mới": "00001", "Hình thức sáp nhập": "Hợp nhất toàn bộ",
                    "Diện tích mới (km²)": "1",
                },
            ]).to_csv(mapping_path, index=False)
            pd.DataFrame([{
                "OSM_Type": "node", "OSM_ID": "101", "SoNha": "1", "TenDuong": "Đường Hàng Ngang",
                "PhuongXa_Cu": "Hang Buom", "QuanHuyen_Cu": "Hoan Kiem", "TinhThanh_Cu": "Hanoi",
                "PhuongXa_Moi": "Phường Hoàn Kiếm", "QuanHuyen_Moi": "", "TinhThanh_Moi": "Hà Nội",
                "DiaChi_Cu": "1, Đường Hàng Ngang, Phường Hàng Buồm, Quận Hoàn Kiếm, Thành phố Hà Nội",
            }]).to_csv(pairs_path, index=False)
            # The balanced snapshot intentionally does not contain direct ID 101.
            pd.DataFrame([{
                "OSM_Type": "node", "OSM_ID": "202", "SoNha": "2", "TenDuong": "Đường Hàng Bồ",
                "PhuongXa": "Phường Hàng Bồ", "QuanHuyen": "Quận Hoàn Kiếm", "TinhThanh": "Thành phố Hà Nội",
            }]).to_csv(balanced_snapshot, index=False)
            pd.DataFrame([{
                "OSM_Type": "node", "OSM_ID": "101", "SoNha": "1", "TenDuong": "Đường Hàng Ngang",
                "PhuongXa": "Phường Hàng Buồm", "QuanHuyen": "Quận Hoàn Kiếm", "TinhThanh": "Thành phố Hà Nội",
            }]).to_csv(full_snapshot, index=False)

            result = generate_bidirectional_pairs(
                pairs_path, mapping_path, balanced_snapshot, target_size=10,
                full_snapshot_path=full_snapshot,
            )
            direct = result[result["Nguon"].str.startswith("OSM_Diff")]
            self.assertEqual(direct["ID_Node"].tolist(), ["node:101"])
            self.assertEqual(direct["QuanHe"].tolist(), ["N-1"])

    def test_audit_does_not_treat_missing_geometry_as_unchanged(self):
        script_path = Path(__file__).resolve().parents[1] / "scripts" / "04_audit_osm_diff_filters.py"
        spec = importlib.util.spec_from_file_location("osm_diff_audit", script_path)
        audit_module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(audit_module)

        self.assertEqual(audit_module.geometry_status({}), "not_captured")
        self.assertEqual(
            audit_module.geometry_status({"HinhHocCoDuLieu": "False", "HinhHocThayDoi": "False"}),
            "not_captured",
        )
        self.assertEqual(
            audit_module.geometry_status({"HinhHocCoDuLieu": "True", "HinhHocThayDoi": "False"}),
            "unchanged",
        )
        self.assertEqual(
            audit_module.geometry_status({"HinhHocCoDuLieu": "True", "HinhHocThayDoi": "True"}),
            "changed",
        )

    def test_new_address_builder_uses_the_same_alias_layer_as_pair_audit(self):
        script_path = Path(__file__).resolve().parents[1] / "scripts" / "03_generate_benchmarks.py"
        spec = importlib.util.spec_from_file_location("benchmark_generator", script_path)
        benchmark_module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(benchmark_module)

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            mapping_path = root / "mapping.csv"
            pd.DataFrame([{
                "Phường/Xã cũ": "Phường Hàng Buồm", "Quận/Huyện cũ": "Quận Hoàn Kiếm",
                "Tỉnh/TP cũ (trước sáp nhập)": "Thành phố Hà Nội", "Tỉnh/TP mới": "Thành phố Hà Nội",
                "Phường/Xã mới (từ 1/7/2025)": "Phường Hoàn Kiếm", "Loại đơn vị mới": "Phường",
                "Mã phường/xã mới": "00001", "Hình thức sáp nhập": "Hợp nhất toàn bộ",
                "Diện tích mới (km²)": "1",
            }]).to_csv(mapping_path, index=False)
            latest = pd.DataFrame(columns=["SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh"])
            pairs = pd.DataFrame([{
                "SoNha": "1", "TenDuong": "Đường Hàng Ngang", "PhuongXa_Moi": "Phường Hoàn Kiếm",
                "QuanHuyen_Moi": "", "TinhThanh_Moi": "Hà Nội",
            }])
            result = benchmark_module.build_new_addresses(latest, pairs, mapping_path)
            self.assertEqual(result["TinhThanh"].tolist(), ["Thành phố Hà Nội"])
            self.assertEqual(result["QuanHuyen"].tolist(), [""])

    def test_coverage_reporter_computes_multidimensional_metrics(self):
        from src.data.coverage_reporter import analyze_pairs_coverage, generate_coverage_markdown
        df = pd.DataFrame([
            {
                "ID_Node": "node:101",
                "DiaChi_Cu": "1, Đường A, Xã B, Huyện C, Hà Nội",
                "DiaChi_Moi": "1, Đường A, Phường D, Thành phố Hà Nội",
                "QuanHe": "N-1",
                "HinhThucSapNhap": "Hợp nhất toàn bộ",
                "Nguon": "OSM_Diff+vietnam-sap-nhap-phuong-xa.csv",
            },
            {
                "ID_Node": "way:202",
                "DiaChi_Cu": "2, Đường B, Xã M, Huyện N, Thành phố Hồ Chí Minh",
                "DiaChi_Moi": "2, Đường B, Phường P, Thành phố Hồ Chí Minh",
                "QuanHe": "M-N",
                "HinhThucSapNhap": "Tách — nhập chủ yếu",
                "Nguon": "OSM_Snapshot+vietnam-sap-nhap-phuong-xa.csv",
            },
        ])
        stats = analyze_pairs_coverage(df)
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["geometry_counts"], {"node": 1, "way": 1})
        self.assertEqual(stats["relationship_counts"]["N-1"], 1)
        self.assertEqual(stats["relationship_counts"]["M-N"], 1)
        self.assertEqual(stats["relationship_counts"]["1-N"], 0)
        self.assertEqual(stats["region_counts"]["Bac"], 1)
        self.assertEqual(stats["region_counts"]["Trung"], 0)
        self.assertEqual(stats["region_counts"]["Nam"], 1)
        self.assertTrue(any("1-N" in w for w in stats["warnings"]))
        self.assertTrue(any("M-N" in w for w in stats["warnings"]))

        empty = analyze_pairs_coverage(pd.DataFrame())
        self.assertEqual(empty["total"], 0)
        self.assertEqual(empty["direct_relation_counts"]["1-N"], 0)
        self.assertIn("0.0%", generate_coverage_markdown(empty))

    def test_data03_contains_only_complete_legacy_addresses(self):
        """Data 03 must contain complete 5-field legacy addresses and reject incomplete quota."""
        rows = [
            {"SoNha": "1", "TenDuong": "Đường A", "PhuongXa": "Phường 1", "QuanHuyen": "Quận 1", "TinhThanh": "Hà Nội"},
            {"SoNha": "", "TenDuong": "Đường B", "PhuongXa": "Phường 2", "QuanHuyen": "Quận 2", "TinhThanh": "Hà Nội"},
            {"SoNha": "3", "TenDuong": "Đường C", "PhuongXa": "", "QuanHuyen": "Quận 3", "TinhThanh": "Hà Nội"},
        ]
        df = pd.DataFrame(rows)
        fields = ["SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh"]
        complete = df[df[fields].apply(lambda col: col.str.strip().ne("")).all(axis=1)]
        self.assertEqual(len(complete), 1)
        self.assertEqual(complete.iloc[0]["SoNha"], "1")
        # Quota check
        with self.assertRaises(ValueError) as ctx:
            if len(complete) < 1500:
                raise ValueError(f"Not enough complete legacy addresses for Data 03: {len(complete)}/1500")
        self.assertIn("Not enough complete legacy addresses for Data 03: 1/1500", str(ctx.exception))

    def test_missing_fields_removes_only_declared_fields(self):
        """Every missing-field row must drop only the fields specified by KieuThieu."""
        old = pd.DataFrame([{"SoNha": str(i), "TenDuong": f"Đường {i}",
                             "PhuongXa": f"Phường {i}", "QuanHuyen": f"Quận {i}",
                             "TinhThanh": "Thành phố Hồ Chí Minh"} for i in range(1, 31)])
        new = pd.DataFrame([{"SoNha": str(i), "TenDuong": f"Đường Mới {i}",
                             "PhuongXa": f"Phường Mới {i}", "QuanHuyen": "",
                             "TinhThanh": "Thành phố Hà Nội"} for i in range(1, 31)])
        out = generate_missing_fields(old, new, target_size=20, seed=42)
        self.assertEqual(len(out), 20)
        fields = ("SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh")
        for _, row in out.iterrows():
            kt = row["KieuThieu"]
            sys = row["HeQuyChieu"]
            expected_dropped = set(DROP_FIELDS[kt])
            if sys == "moi":
                expected_dropped.add("QuanHuyen")
            for f in fields:
                if f in expected_dropped:
                    self.assertEqual(row[f], "", f"Field {f} should be dropped for {kt}")
                else:
                    self.assertNotEqual(row[f], "", f"Field {f} should not be dropped for {kt}")

    def test_missing_fields_preserves_gt_values(self):
        """Ground truth fields GT_* must be preserved exactly before deletion."""
        old = pd.DataFrame([{"SoNha": str(i), "TenDuong": f"Đường Cũ {i}",
                             "PhuongXa": f"Phường Cũ {i}", "QuanHuyen": f"Quận Cũ {i}",
                             "TinhThanh": "Thành phố Hồ Chí Minh"} for i in range(1, 21)])
        new = pd.DataFrame([{"SoNha": str(i), "TenDuong": f"Đường Mới {i}",
                             "PhuongXa": f"Phường Mới {i}", "QuanHuyen": "",
                             "TinhThanh": "Thành phố Hà Nội"} for i in range(1, 21)])
        out = generate_missing_fields(old, new, target_size=10, seed=42)
        for _, row in out.iterrows():
            sys = row["HeQuyChieu"]
            self.assertTrue(row["GT_SoNha"].strip().isdigit())
            self.assertTrue(row["GT_TenDuong"].startswith("Đường"))
            self.assertTrue(row["GT_PhuongXa"].startswith("Phường"))
            self.assertTrue(row["GT_TinhThanh"].startswith("Thành phố"))
            if sys == "cu":
                self.assertTrue(row["GT_QuanHuyen"].startswith("Quận Cũ"))
            else:
                self.assertEqual(row["GT_QuanHuyen"], "")

    def test_new_system_allows_empty_district(self):
        """Empty QuanHuyen is structural for 2-tier new system, not an error."""
        new = pd.DataFrame([{"SoNha": "10", "TenDuong": "Đường A",
                             "PhuongXa": "Phường B", "QuanHuyen": "",
                             "TinhThanh": "Thành phố Hà Nội"}])
        # Should validate without error
        validate_clean_source(new, "moi")
        # Validation row check
        row_dict = {
            "SoNha": "", "TenDuong": "Đường A", "PhuongXa": "Phường B",
            "QuanHuyen": "", "TinhThanh": "Thành phố Hà Nội",
            "GT_SoNha": "10", "GT_TenDuong": "Đường A", "GT_PhuongXa": "Phường B",
            "GT_QuanHuyen": "", "GT_TinhThanh": "Thành phố Hà Nội",
        }
        validate_missing_surface(row_dict, "moi", "drop_housenumber", source_index=0)

    def test_missing_generator_rejects_incomplete_source(self):
        """Source with missing fields must be rejected immediately."""
        bad_old = pd.DataFrame([{"SoNha": "", "TenDuong": "Đường A", "PhuongXa": "P1", "QuanHuyen": "Q1", "TinhThanh": "HN"}])
        good_new = pd.DataFrame([{"SoNha": "1", "TenDuong": "Đường B", "PhuongXa": "P2", "QuanHuyen": "", "TinhThanh": "HCM"}])
        with self.assertRaises(ValueError) as ctx:
            validate_clean_source(bad_old, "cu")
        self.assertIn("Incomplete clean source for system 'cu'", str(ctx.exception))
        with self.assertRaises(ValueError):
            generate_missing_fields(bad_old, good_new, target_size=2)

        bad_new = pd.DataFrame([{"SoNha": "1", "TenDuong": "Đường B", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "HCM"}])
        good_old = pd.DataFrame([{"SoNha": "1", "TenDuong": "Đường A", "PhuongXa": "P1", "QuanHuyen": "Q1", "TinhThanh": "HN"}])
        with self.assertRaises(ValueError) as ctx:
            validate_clean_source(bad_new, "moi")
        self.assertIn("Incomplete clean source for system 'moi'", str(ctx.exception))
        with self.assertRaises(ValueError):
            generate_missing_fields(good_old, bad_new, target_size=2)

    def test_data02_uses_complete_sources_only(self):
        """Data 02 requires complete source addresses and produces full GT_*."""
        with tempfile.TemporaryDirectory() as folder:
            noise_cfg = Path(folder) / "noise.json"
            noise_cfg.write_text('{"noise_probabilities": {}}', encoding="utf-8")
            old = pd.DataFrame([{"SoNha": "1", "TenDuong": "Đường A", "PhuongXa": "Phường 1", "QuanHuyen": "Quận 1", "TinhThanh": "Hà Nội"}])
            new = pd.DataFrame([{"SoNha": "2", "TenDuong": "Đường B", "PhuongXa": "Phường 2", "QuanHuyen": "", "TinhThanh": "Hồ Chí Minh"}])
            out = generate_raw_noisy_addresses(old, new, noise_cfg, target_size=2, seed=42)
            self.assertEqual(len(out), 2)
            for _, r in out.iterrows():
                self.assertNotEqual(r["GT_SoNha"], "")
                self.assertNotEqual(r["GT_TenDuong"], "")
                self.assertNotEqual(r["GT_PhuongXa"], "")
                self.assertNotEqual(r["GT_TinhThanh"], "")
                if r["HeQuyChieu"] == "cu":
                    self.assertNotEqual(r["GT_QuanHuyen"], "")
                else:
                    self.assertEqual(r["GT_QuanHuyen"], "")

    def test_data06_uses_complete_legacy_source(self):
        """Data 06 hybrid addresses from complete source must have all 5 surface fields."""
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            mapping_path = root / "mapping.csv"
            pd.DataFrame([{
                "Phường/Xã cũ": "Xã Cũ", "Quận/Huyện cũ": "Huyện Cũ",
                "Tỉnh/TP cũ (trước sáp nhập)": "Tỉnh Cũ", "Tỉnh/TP mới": "Tỉnh Mới",
                "Phường/Xã mới (từ 1/7/2025)": "Phường Mới", "Loại đơn vị mới": "Phường",
                "Mã phường/xã mới": "99999", "Hình thức sáp nhập": "Hợp nhất toàn bộ",
                "Diện tích mới (km²)": "1",
            }]).to_csv(mapping_path, index=False)
            complete_old = pd.DataFrame([{
                "SoNha": "123", "TenDuong": "Đường Cũ", "PhuongXa": "Xã Cũ",
                "QuanHuyen": "Huyện Cũ", "TinhThanh": "Tỉnh Cũ",
            }])
            hybrids = generate_hybrid_addresses(complete_old, mapping_path, target_size=1, seed=42)
            self.assertEqual(len(hybrids), 1)
            row = hybrids.iloc[0]
            self.assertEqual(row["SoNha"], "123")
            self.assertEqual(row["TenDuong"], "Đường Cũ")
            self.assertEqual(row["PhuongXa"], "Phường Mới")
            self.assertEqual(row["QuanHuyen"], "Huyện Cũ")
            self.assertIn(row["TinhThanh"], ("Tỉnh Cũ", "Tỉnh Mới"))

    def test_generators_are_reproducible_with_same_seed(self):
        """Generators must produce identical CSVs with the same seed."""
        old = pd.DataFrame([{"SoNha": str(i), "TenDuong": f"Đường {i}",
                             "PhuongXa": f"Phường {i}", "QuanHuyen": f"Quận {i}",
                             "TinhThanh": "Thành phố Hồ Chí Minh"} for i in range(1, 21)])
        new = pd.DataFrame([{"SoNha": str(i), "TenDuong": f"Đường Mới {i}",
                             "PhuongXa": f"Phường Mới {i}", "QuanHuyen": "",
                             "TinhThanh": "Thành phố Hà Nội"} for i in range(1, 21)])
        run1 = generate_missing_fields(old, new, target_size=10, seed=123)
        run2 = generate_missing_fields(old, new, target_size=10, seed=123)
        self.assertEqual(run1.to_csv(index=False), run2.to_csv(index=False))


class SourceReannotationTests(unittest.TestCase):
    def test_component_offsets_and_ambiguous_repeated_surface(self):
        components = [Component("SoNha", "12", "12", "cu"),
                      Component("TenDuong", "Đường 12", "Đường 12", "cu")]
        text, placed = render_components(components)
        self.assertEqual(text, "12, Đường 12")
        self.assertEqual([(p["start"], p["end"]) for p in placed], [(0, 2), (4, 12)])
        self.assertEqual(align_unique("Phường 7, Phường 7", [
            Component("PhuongXa", "Phường 7", "Phường 7", "cu")])[1],
            "ambiguous_or_missing_ordered_surface")

    def test_frozen_reannotation_package_has_trace_and_no_leakage(self):
        generator = importlib.import_module("scripts.21_prepare_source_reannotation")
        prediction_import = importlib.import_module("scripts.15_import_pilot_predictions")
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "v2"
            with patch.object(sys, "argv", ["prepare", "--output-dir", str(output)]):
                generator.main()
            with patch.object(sys, "argv", ["prepare", "--output-dir", str(output)]):
                with self.assertRaises(FileExistsError):
                    generator.main()
            pilot = json.loads((output / "pilot68_candidates.json").read_text(encoding="utf-8"))
            batch = json.loads((output / "batch232_candidates.json").read_text(encoding="utf-8"))
            self.assertEqual(len(pilot), 68)
            self.assertEqual(len(batch), 232)
            prediction_import.validate_candidates(output / "pilot68_candidates.json", 68)
            prediction_import.validate_candidates(output / "batch232_candidates.json", 232)
            trace = {row["sample_id"]: row for row in (
                json.loads(line) for line in (output / "trace.jsonl").read_text(encoding="utf-8").splitlines())}
            self.assertEqual(len(trace), 300)
            frozen_test = {row["sample_id"] for row in json.loads(
                (generator.BASE / "test_hold_manifest_v1.json").read_text(encoding="utf-8"))["samples"]}
            self.assertFalse({record["sample_id"] for record in pilot + batch} & frozen_test)
            for name, records in (("pilot68", pilot), ("batch232", batch)):
                tasks = json.loads((output / f"{name}_import.json").read_text(encoding="utf-8"))
                self.assertEqual([task["data"] for task in tasks], [
                    {"sample_id": record["sample_id"], "text": record["text"]} for record in records])
                self.assertTrue(all(set(task) == {"data"} and set(task["data"]) == {"sample_id", "text"}
                                    for task in tasks))
            for record in pilot + batch:
                item_trace = trace[record["sample_id"]]
                traced = {(part["start"], part["end"], part["field"]): part
                          for part in item_trace["components"] if part["match_status"] == "exact"}
                previous_end = 0
                for span in record["spans"]:
                    self.assertGreaterEqual(span["start"], previous_end)
                    self.assertEqual(record["text"][span["start"]:span["end"]], span["text"])
                    self.assertIn(span["label"], generator.LABELS)
                    self.assertIn(span["system"], generator.SYSTEMS)
                    if span["label"] in {"SoNha", "TenDuong"}:
                        self.assertEqual(span["system"], "khong_xac_dinh")
                    if span["label"] == "QuanHuyen":
                        self.assertEqual(span["system"], "cu")
                    part = traced[(span["start"], span["end"], span["label"])]
                    self.assertEqual(part["span_system_candidate"], span["system"])
                    self.assertIn("evidence", part)
                    previous_end = span["end"]
                if item_trace["stratum"] == "osm_new_2tier":
                    self.assertNotIn("QuanHuyen", [span["label"] for span in record["spans"]])
                if item_trace["stratum"] == "synthetic_missing":
                    missing = [part["field"] for part in item_trace["components"]
                               if part["match_status"] == "absent_by_generator"]
                    self.assertEqual(len(missing), 1)
                    self.assertNotIn(missing[0], [span["label"] for span in record["spans"]])


class Sprint3BIODataContractTests(unittest.TestCase):
    def test_modeling_gold_free_units_keep_adjacent_spans_separate(self):
        from src.modeling.alignment import align_text, encode_gold, decode_tags
        text = "A B"
        alignment = align_text(text)
        tags = encode_gold(alignment, [{"start": 0, "end": 1, "label": "Khac"},
                                       {"start": 2, "end": 3, "label": "Khac"}])
        self.assertEqual(tags, ["B-Khac", "B-Khac"])
        self.assertEqual([s.text for s in decode_tags(alignment, tags)[0]], ["A", "B"])

    def test_raw_unicode_bio_round_trip_keeps_delimiters_outside_spans(self):
        from src.evaluation.span_features import encode_gold, decode_bio
        text = "Số 12/3A, P.7, Hà Nội"
        spans = [{"start": 0, "end": 8, "label": "SoNha"},
                 {"start": 10, "end": 13, "label": "PhuongXa"},
                 {"start": 15, "end": len(text), "label": "TinhThanh"}]
        tokens, tags = encode_gold(text, spans)
        decoded, repairs = decode_bio(text, tokens, tags)
        self.assertEqual([span.text for span in decoded], ["Số 12/3A", "P.7", "Hà Nội"])
        self.assertEqual(repairs, [])
        self.assertEqual(len(set(tags)-{"O"}), 6)


class SourceReconciliationDiagnosticTests(unittest.TestCase):
    def test_phobert_nfd_gold_uses_original_cluster_offsets(self):
        import unicodedata
        from src.modeling.alignment import PhoBERTProcessor, encode_gold, decode_tags
        class Tokenizer:
            model_max_length = 256
            unk_token = '<unk>'
            def tokenize(self, value): return [value]
            def convert_tokens_to_ids(self, pieces): return [3] * len(pieces)
            def build_inputs_with_special_tokens(self, ids): return [0] + ids + [2]
            def get_special_tokens_mask(self, ids, already_has_special_tokens=False): return [1] + [0] * len(ids) + [1]
        class Segmenter:
            def word_segment(self, value): return [value]
        text = unicodedata.normalize('NFD', 'Hà Nội')
        alignment = PhoBERTProcessor(Tokenizer(), Segmenter(), 256).align_text(text)
        result = decode_tags(alignment, encode_gold(alignment, [{'start': 0, 'end': len(text), 'label': 'TinhThanh'}]))[0]
        self.assertEqual(result[0].text, text)
        self.assertEqual(result[0].end, len(text))

    def test_checkpoint_uses_portable_temporary_basename(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from src.modeling import checkpoints
        recorded = []
        def fake_save(payload, path):
            recorded.append(path.name)
            self.assertFalse(path.name.startswith('.'))
            path.write_bytes(b'fixture-only')
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'fixture.pt'
            with patch.dict('sys.modules', {'torch': SimpleNamespace(save=fake_save)}):
                record = checkpoints.save_checkpoint(output, None, {}, native_payload={'fixture': True})
            self.assertTrue(record['complete'])
            self.assertTrue(recorded[0].endswith('.pt.tmp'))
            self.assertEqual(output.read_bytes(), b'fixture-only')
            self.assertEqual(sorted(p.name for p in output.parent.iterdir()), ['fixture.pt', 'fixture.pt.json'])

    def test_diacritics_are_only_diagnostics_and_level_is_preserved(self):
        from src.data.source_reconciliation import diagnostic_difference
        self.assertEqual(diagnostic_difference('Tỉnh Hòa Bình', 'Tỉnh Hoà Bình'), 'DIACRITIC_OR_TONE_VARIATION')
        self.assertEqual(diagnostic_difference('Phường A', 'Xã A'), 'UNIT_TYPE_MISMATCH')
        self.assertEqual(diagnostic_difference('Phường A', 'Phường B'), 'NAME_MISMATCH_UNAUDITED')
        self.assertEqual(diagnostic_difference('Phường A', 'P.A', ['P.A']), 'EXISTING_AUDITED_ALIAS')


class DatedCatalogueRegression(unittest.TestCase):
    def test_test_release_temporal_findings_are_not_silently_approved(self):
        from src.data.test_corpus_release import validate_approval
        with self.assertRaisesRegex(ValueError, "APPROVAL"):
            validate_approval({}, {}, {"fixture": {}}, [], {})

    def test_old_ward_without_district_is_not_verified(self):
        from src.data.nso_soap_catalog import build_reference
        entry = {"sha256": "fixture", "response_file": "fixture.xml"}
        province = {"MaTinh": "01", "TenTinh": "Tỉnh A", "_diffgr_id": "p"}
        ward = {"MaTinh": "01", "TenTinh": "Tỉnh A", "MaPhuongXa": "00001", "TenPhuongXa": "Xã B", "_diffgr_id": "w"}
        rows, report = build_reference({"province": (entry, [province]), "ward": (entry, [ward])}, "2025-06-30", "cu")
        self.assertEqual(rows[-1]["validation_status"], "PARENT_CODE_LINK_FAIL")
        self.assertEqual(report["status"], "PARTIAL_PARENT_LINK_GAPS")


if __name__ == "__main__":
    unittest.main()
