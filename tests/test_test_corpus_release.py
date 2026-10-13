"""Publisher approval/immutability tests on synthetic annotations, not test100."""
import copy
import csv
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

_fixture_spec = importlib.util.spec_from_file_location("annotation_fixture_support", Path(__file__).with_name("test_test_annotation_qa.py"))
qa_fixture = importlib.util.module_from_spec(_fixture_spec)
_fixture_spec.loader.exec_module(qa_fixture)
from src.data.test_annotation_qa import review_test_export
from src.data import test_corpus_release as release
from src.evaluation.dev_runner import file_hash, write_json


class TestCorpusReleaseTests(unittest.TestCase):
    def test_ambiguous_benchmark_provenance_is_not_observed(self):
        self.assertEqual(release.provenance_kind({"derivation": "observed_or_existing_benchmark"}),
                         "unverified_provenance")
        for derivation, kind in (("observed_osm", "observed"), ("derived_verified_unique_admin_mapping", "derived"),
                                 ("controlled_synthetic_fixture", "synthetic")):
            self.assertEqual(release.provenance_kind({"derivation": derivation}), kind)

    def test_source_metadata_uses_pinned_queues_and_rejects_changed_hash(self):
        source = self.root / "data/processed/annotation/sprint03/source"
        source.mkdir(parents=True)
        queue = self.root / "annotation_queue_fixture.csv"
        queue.write_text("sample_id,text,group_id,derivation\nx,text,g,observed_osm\n")
        manifest = {"input_sha256": {queue.name: file_hash(queue)}}
        self.assertEqual(release.locked_source_metadata(source, manifest)["x"]["group_id"], "g")
        queue.write_text(queue.read_text() + "y,other,h,observed_osm\n")
        with self.assertRaisesRegex(ValueError, "PROVENANCE_QUEUE_CHANGED"):
            release.locked_source_metadata(source, manifest)

    def setUp(self):
        self.fixture = qa_fixture.TestAnnotationQATests(methodName="runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        with self.fixture.queue.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        for row in rows:
            row["source_dataset"] = "fictional_source"
            row["derivation"] = "controlled_synthetic_fixture"
        with self.fixture.queue.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        self.hold = self.root / "hold.json"
        write_json(self.hold, {"status": "FROZEN_BENCHMARK_TEST_HOLD", "samples": [
            {"sample_id": row["sample_id"], "group_id": row["group_id"],
             "source_dataset": row["source_dataset"], "text_sha256": release.text_hash(row["text"])} for row in rows]})
        self.qa = self.root / "review"
        review_test_export(self.fixture.export, self.fixture.queue, self.qa, self.fixture.manifest)
        self.args = (self.qa, self.fixture.queue, self.hold, self.fixture.manifest)
        self.records, _, self.selected, self.findings, self.bindings = release.candidate_inputs(*self.args)
        self.approval = {"bindings": self.bindings, "reviewed_sample_count": 100, "reviewer": "fixture reviewer",
            "label_studio_user_id": 1, "reviewed_at": "2026-10-04", "human_authorization_quote": "fixture approval",
            "decision": "approve", "evaluation_exclusions": {"t1": []}}
        self.decisions = {"bindings": self.bindings, "reviewer": "fixture reviewer", "decisions": []}

    def test_candidate_is_never_gold_and_refuses_overwrite(self):
        output = self.root / "candidate"
        result = release.prepare_test_release(*self.args, output)
        self.assertEqual(result["status"], "CANDIDATE_NOT_GOLD")
        with self.assertRaises(FileExistsError):
            release.prepare_test_release(*self.args, output)

    def test_hash_current_identity_approval(self):
        self.assertEqual(release.validate_approval(self.approval, self.decisions, self.selected, self.findings, self.bindings), [])
        self.approval["label_studio_user_id"] = 2
        with self.assertRaisesRegex(ValueError, "IDENTITY_MISMATCH"):
            release.validate_approval(self.approval, self.decisions, self.selected, self.findings, self.bindings)

    def test_no_approval_or_partial_scope(self):
        for value in ({}, {**self.approval, "reviewed_sample_count": 99}):
            with self.assertRaisesRegex(ValueError, "APPROVAL"):
                release.validate_approval(value, self.decisions, self.selected, self.findings, self.bindings)

    def test_raw_canonical_label_tamper_is_rejected(self):
        path = self.qa / "structure/canonical_candidate.jsonl"
        rows = release.read_jsonl(path)
        rows[0]["spans"][0]["label"] = "Khac"
        release.write_jsonl(path, rows)
        with self.assertRaises(ValueError):
            release.candidate_inputs(*self.args)

    def test_hidden_canonical_metadata_is_rejected(self):
        path = self.qa / "structure/canonical_candidate.jsonl"
        rows = release.read_jsonl(path)
        rows[0]["GT_System"] = "moi"
        release.write_jsonl(path, rows)
        with self.assertRaisesRegex(ValueError, "SCHEMA_CHANGED"):
            release.candidate_inputs(*self.args)

    def test_stale_raw_report_is_rejected(self):
        path = self.qa / "inputs/label_studio_export.json"
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "STALE_QA_BINDING"):
            release.candidate_inputs(*self.args)

    def test_frozen_hold_identity_is_rejected(self):
        hold = release.load_json(self.hold)
        hold["samples"][0]["text_sha256"] = "bad"
        write_json(self.hold, hold)
        with self.assertRaisesRegex(ValueError, "TEST_TEXT_GROUP_CHANGED"):
            release.candidate_inputs(*self.args)

    def test_t1_findings_require_human_evidence_or_declared_mask(self):
        sid = next(iter(self.selected))
        findings = [{"sample_id": sid, "code": "t1_evidence_needs_review"}]
        with self.assertRaisesRegex(ValueError, "UNRESOLVED"):
            release.validate_approval(self.approval, self.decisions, self.selected, findings, self.bindings)
        selected = self.selected[sid]
        decision = {"sample_id": sid, "annotation_id": selected["annotation_id"],
            "annotation_sha256": selected["annotation_sha256"], "decision": "keep", "reason": "fixture reason",
            "reviewed_at": "2026-10-04", "exclude_from_t1": False, "accepted_finding_codes": [findings[0]["code"]]}
        self.decisions["decisions"] = [decision]
        with self.assertRaisesRegex(ValueError, "EVIDENCE_OR_EXCLUSION"):
            release.validate_approval(self.approval, self.decisions, self.selected, findings, self.bindings)
        decision.update(exclude_from_t1=True, decision="keep_as_exception")
        self.approval["evaluation_exclusions"]["t1"] = [sid]
        self.assertEqual(release.validate_approval(self.approval, self.decisions, self.selected, findings, self.bindings), [sid])

    def test_unknown_or_old_decision_is_rejected(self):
        self.decisions["decisions"] = [{"sample_id": "not_in_export"}]
        with self.assertRaisesRegex(ValueError, "INVALID_REVIEW_DECISION"):
            release.validate_approval(self.approval, self.decisions, self.selected, self.findings, self.bindings)

    def test_flags_require_explicit_disposition(self):
        self.selected[next(iter(self.selected))]["review_flags"] = ["privacy_review"]
        with self.assertRaisesRegex(ValueError, "UNRESOLVED"):
            release.validate_approval(self.approval, self.decisions, self.selected, self.findings, self.bindings)

    def test_multiple_different_flags_requires_selection(self):
        annotation = copy.deepcopy(self.fixture.tasks[0]["annotations"][0])
        annotation["id"] = 9900
        annotation["result"].append({"from_name": "review_flags", "to_name": "address_text", "type": "choices",
                                   "value": {"choices": ["temporal_ambiguity"]}})
        self.fixture.tasks[0]["annotations"].append(annotation)
        self.fixture.save_export()
        other = self.root / "multiple"
        review_test_export(self.fixture.export, self.fixture.queue, other, self.fixture.manifest)
        with self.assertRaisesRegex(ValueError, "QA_NOT_COMPLETE"):
            release.candidate_inputs(other, *self.args[1:])

    def test_publish_full_fixture_preserves_train_dev_and_t1_exception(self):
        source = self.root / "data/processed/annotation/sprint03/train_dev"
        source.mkdir(parents=True)
        splits = {name: [{"sample_id": f"{name}-{i}", "text": "fixture", "source_group": f"{name}-g{i}"}
                         for i in range(count)] for name, count in (("train", 240), ("dev", 60))}
        for name in ("train.jsonl", "dev.jsonl", "dev_input.jsonl"):
            (source / name).write_bytes(b"immutable fixture source\n")
        write_json(source / "coverage.json", {"purpose": "fixture"})
        source_manifest = {"evaluation_exclusions": {"t1": ["s3_60931c369cbd85ef"]}}
        write_json(source / "manifest.json", source_manifest)
        approval, decisions = self.root / "approval.json", self.root / "decisions.json"
        write_json(approval, self.approval)
        write_json(decisions, self.decisions)
        assignment, near = self.root / "assignment.csv", self.root / "near.csv"
        assignment.write_text("fixture assignment")
        near.write_text("fixture decisions")
        output = source.with_name("corpus_fixture")
        test_output = source.with_name("test_fixture")
        before = file_hash(self.fixture.export)
        with patch("src.data.test_corpus_release.audit_release_split", return_value=(source_manifest, splits, {"status": "AUDIT_PASS_FIXTURE"})):
            result = release.publish_test_corpus(*self.args, source, assignment, near, approval, decisions,
                                                 output, test_output_dir=test_output)
            with self.assertRaises(FileExistsError):
                release.publish_test_corpus(*self.args, source, assignment, near, approval, decisions, output)
        self.assertEqual(result["sample_counts"], {"train": 240, "dev": 60, "test": 100})
        self.assertEqual(result["evaluation_exclusions"]["t1"], ["s3_60931c369cbd85ef"])
        self.assertEqual((source / "train.jsonl").read_bytes(), (output / "train.jsonl").read_bytes())
        self.assertEqual(len(release.read_jsonl(test_output / "test_benchmark_t0.jsonl")), 100)
        self.assertEqual(file_hash(self.fixture.export), before)
        for name, digest in result["output_sha256"].items():
            self.assertEqual(file_hash(output / name), digest)


if __name__ == "__main__":
    unittest.main()
