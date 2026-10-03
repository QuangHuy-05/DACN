"""Synthetic fixtures for official evidence gates; no benchmark/test100 input."""

import csv
import ast
import json
from pathlib import Path
import tempfile
import unittest

from src.data.nso_soap_catalog import NsoSoapError, build_envelope, parse_table_rows, validate_rows, build_reference
from src.data.nso_dual_snapshot import DualSnapshotGazetteer, reconcile
from src.evaluation.dev_runner import file_hash
from src.modeling.pre_colab import compare_ledger, git_snapshot
from unittest.mock import patch


def fixture_package(directory):
    entities = []
    for identity, level, system, name, parent, code in (
        ("p0", "province", "cu", "Tỉnh A", "", "01"),
        ("p1", "province", "moi", "Tỉnh A", "", "01"),
        ("d0", "district", "cu", "Huyện B", "p0", "001"),
        ("w0", "ward", "cu", "Xã C", "d0", "00001"),
        ("w1", "ward", "moi", "Xã C", "p1", "00001"),
        ("wu", "ward", "cu", "Xã U", "d0", ""),
    ):
        entities.append({"entity_id": identity, "level": level, "system": system,
                         "canonical_name": name, "parent_id": parent, "official_code": code,
                         "candidate_code": "", "code_status": "verified_primary_source_snapshot" if code else "missing",
                         "valid_from": "", "valid_to": "2025-06-30" if system == "cu" else "",
                         "source_id": "fixture", "source_hash": "fixture", "status": "fixture"})
    tables = {"entities.csv": entities,
              "aliases.csv": [{"entity_id": "w0", "alias": "X.C", "source_id": "audited_aliases"}],
              "edges.csv": [{"old_entity_id": "w0", "new_entity_id": "w1", "relation": "A/1-N"},
                            {"old_entity_id": "w0", "new_entity_id": "p1", "relation": "A/1-N"}],
              "non_atomic_transitions.csv": [{"old_entity_id": "d0", "new_entity_id": "w1", "relation": "non-atomic"}],
              "code_evidence.csv": [{"entity_id": row["entity_id"], "code": row["official_code"], "source_as_of": "2025-06-30" if row["system"] == "cu" else "2025-07-01"} for row in entities if row["official_code"]]}
    for name, rows in tables.items():
        with (directory / name).open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    (directory / "manifest.json").write_text(json.dumps({"version": "fixture-dual", "snapshot_dates_by_system": {"cu": "2025-06-30", "moi": "2025-07-01"},
         "output_sha256": {name: file_hash(directory / name) for name in tables}}))
    return entities


class OfficialReferenceTests(unittest.TestCase):
    def test_only_read_operations_and_date_parameters(self):
        with self.assertRaises(ValueError):
            build_envelope("Update", {"DenNgay": "30/06/2025"})
        with self.assertRaises(ValueError):
            build_envelope("DanhMucTinh", {"DenNgay": "invalid"})
        self.assertIn(b"30/06/2025", build_envelope("DanhMucTinh", {"DenNgay": "30/06/2025"}))

    def test_xml_fault_and_schema_are_not_rows(self):
        with self.assertRaises(NsoSoapError):
            parse_table_rows(b'<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Fault/></soap:Envelope>', "DanhMucTinh")
        xml = b'<r xmlns:n="http://tempuri.org/" xmlns:d="urn:schemas-microsoft-com:xml-diffgram-v1"><n:DanhMucTinhResult><schema><element name="TABLE"/></schema><d:diffgram><DataSet><TABLE><MaTinh>01</MaTinh><TenTinh>Tinh A</TenTinh></TABLE></DataSet></d:diffgram></n:DanhMucTinhResult></r>'
        rows = parse_table_rows(xml, "DanhMucTinh")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["MaTinh"], "01")

    def test_leading_zero_duplicate_empty_code_validation(self):
        row = {"MaTinh": "01", "TenTinh": "Tỉnh A", "_diffgr_id": "r1"}
        self.assertEqual(validate_rows([row], "DanhMucTinh")["status"], "PASS")
        self.assertEqual(validate_rows([dict(row, MaTinh="1")], "DanhMucTinh")["status"], "FAIL")
        self.assertEqual(validate_rows([row, row], "DanhMucTinh")["status"], "FAIL")
        self.assertEqual(validate_rows([], "DanhMucTinh")["status"], "FAIL")

    def test_parent_failure_is_not_promoted(self):
        p = {"MaTinh": "01", "TenTinh": "Tỉnh A", "_diffgr_id": "p"}
        d = {"MaTinh": "02", "TenTinh": "Tỉnh A", "MaQuanHuyen": "001", "TenQuanHuyen": "Huyện B", "_diffgr_id": "d"}
        w = dict(d, MaTinh="01", MaPhuongXa="00001", TenPhuongXa="Xã C", _diffgr_id="w")
        entry = {"sha256": "fixture", "response_file": "fixture.xml"}
        ref, validation = build_reference({"province": (entry, [p]), "district": (entry, [d]), "ward": (entry, [w])}, "2025-06-30", "cu")
        self.assertEqual(validation["status"], "PARTIAL_PARENT_LINK_GAPS")
        self.assertEqual([row["validation_status"] for row in ref][1:], ["PARENT_CODE_LINK_FAIL"] * 2)


class GazetteerFollowupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        fixture_package(self.directory)
        self.gaz = DualSnapshotGazetteer(self.directory)

    def tearDown(self):
        self.temp.cleanup()

    def test_dual_date_and_reused_code_identity(self):
        old = self.gaz.lookup("Xã C", "ward", "2025-06-30")
        new = self.gaz.lookup("Xã C", "ward", "2025-07-01")
        self.assertEqual(old["status"], "VERIFIED")
        self.assertEqual(new["status"], "VERIFIED")
        self.assertNotEqual(old["candidates"][0]["entity_id"], new["candidates"][0]["entity_id"])

    def test_outside_scope_and_parent_reject(self):
        self.assertEqual(self.gaz.lookup("Xã C", "ward", "2025-07-02")["status"], "OUT_OF_SNAPSHOT_SCOPE")
        self.assertEqual(self.gaz.lookup("Xã C", "ward", "2025-06-30", {"district": "Huyện D"})["status"], "NO_MATCH")
        self.assertEqual(self.gaz.lookup("Xã C", "ward", "2025-07-01", system="cu")["status"], "OUT_OF_SNAPSHOT_SCOPE")

    def test_unverified_and_all_targets(self):
        self.assertEqual(self.gaz.lookup("Xã U", "ward", "2025-06-30")["status"], "CANDIDATE")
        self.assertEqual(len(self.gaz.targets("w0")["targets"]), 2)
        self.assertEqual(len(self.gaz.targets("d0")["targets"]), 1)

    def test_conflict_and_unique_uncoded_assignment(self):
        row = {"system": "cu", "level": "ward", "official_name": "Xã C", "province_name": "Tỉnh A", "district_name": "Huyện B", "validation_status": "PARENT_CODE_LINK_PASS", "official_code": "99999"}
        decision = {item["entity_id"]: item for item in reconcile(self.gaz, [row])}
        self.assertEqual(decision["w0"]["status"], "CODE_CONFLICT")
        row.update(official_name="Xã U", official_code="00009")
        decision = {item["entity_id"]: item for item in reconcile(self.gaz, [row])}
        self.assertEqual(decision["wu"]["verified_code"], "00009")
        self.assertEqual(reconcile(self.gaz, [row, row])[-1]["verified_code"], None)

    def test_hash_gate(self):
        (self.directory / "entities.csv").write_text("corrupted")
        with self.assertRaises(ValueError):
            DualSnapshotGazetteer(self.directory)

    def test_source_register_completion_keeps_parent_and_derives_counts(self):
        from src.data.nso_release_metadata import complete_source_register
        parent_manifest = json.loads((self.directory / "manifest.json").read_text())
        parent_manifest.update(counts={"entities": 6}, official_code_snapshot={"old_codes_verified": 0})
        (self.directory / "manifest.json").write_text(json.dumps(parent_manifest))
        (self.directory / "coverage_report.json").write_text(json.dumps({"graph_counts": {}}))
        fields = ["source_id", "name", "path_or_url", "level_scope", "system", "valid_range", "access_date", "license", "sha256", "role", "source_export_sha256"]
        with (self.directory / "source_register.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            csv.DictWriter(stream, fieldnames=fields).writeheader()
        before = file_hash(self.directory / "entities.csv")
        evidence = self.directory / "evidence"
        (evidence / "responses").mkdir(parents=True)
        response = evidence / "responses/fixture.xml"
        response.write_text("synthetic source fixture")
        entries = [{"query": {"DenNgay": "30/06/2025"}, "response_file": "fixture.xml", "sha256": file_hash(response),
                    "operation": operation, "source_url": "https://fixture.invalid/", "retrieved_at": "fixture"}
                   for operation in ("DanhMucTinh", "DanhMucQuanHuyen", "DanhMucPhuongXa")]
        (evidence / "download_manifest.json").write_text(json.dumps({"responses": entries}))
        with tempfile.TemporaryDirectory() as release_root:
            output = Path(release_root) / "release"
            with patch("src.data.nso_release_metadata.ROOT", Path(release_root)):
                complete_source_register(self.directory, evidence, output)
                with self.assertRaises(FileExistsError):
                    complete_source_register(self.directory, evidence, output)
            self.assertEqual(file_hash(output / "entities.csv"), before)
            self.assertEqual(file_hash(self.directory / "entities.csv"), before)
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["verified_code_counts"], {"cu": 3, "moi": 2, "total": 5})

    def test_porcelain_preserves_first_filename(self):
        with patch("src.modeling.pre_colab._run", side_effect=lambda args, root: " M AGENTS.md\n?? file.py" if "status" in args else "fixture"):
            self.assertEqual(git_snapshot(self.directory)["modified"], ["AGENTS.md"])

    def test_compact_prefix_rules_preserve_offsets_and_scope(self):
        from src.evaluation.adapters.heur_jw_followup import HeuristicJaroWinklerFollowup
        adapter = HeuristicJaroWinklerFollowup(self.directory, similarity_threshold=1)
        text = "12, Đường A, X C, H B, Tỉnh A"
        output = adapter.parse_spans(text)
        self.assertIn("QuanHuyen", [span.label for span in output.spans])
        self.assertTrue(all(span.text == text[span.start:span.end] for span in output.spans))
        future = HeuristicJaroWinklerFollowup(self.directory, temporal_policy="fixed_as_of", as_of_date="2025-07-02")
        self.assertFalse(future._valid(future.entities["w1"]))

    def test_crf_new_features_keep_old_version_unchanged(self):
        from src.evaluation.span_features import tokenize, token_features, FOLLOWUP_FEATURE_VERSION
        text = "phường Tân Phú, đường A"
        tokens = tokenize(text)
        old = token_features(text, tokens)
        new = token_features(text, tokens, feature_version=FOLLOWUP_FEATURE_VERSION)
        self.assertNotIn("segment_prefix_cue", old[0])
        self.assertEqual(new[2]["segment_prefix_cue"], "phường")
        self.assertEqual(new[3]["segment_prefix_cue"], "none")


class HardwareAndHandoffTests(unittest.TestCase):
    def test_zero_shot_gate_never_loads_parser_when_blocked(self):
        from src.evaluation.adapters.deepparse_locked_adapter import LockedDeepparseFastTextAdapter
        with patch("src.evaluation.adapters.deepparse_locked_adapter.preflight", return_value={"blockers": ["RAM_BELOW_FULL_FASTTEXT_PREFLIGHT"]}), patch("src.modeling.deepparse_training.construct_parser") as constructor:
            with self.assertRaises(RuntimeError):
                LockedDeepparseFastTextAdapter("fixture_missing_lock.json")
            constructor.assert_not_called()

    def test_zero_shot_explicitly_uses_pretrained_cpu_not_retrained_checkpoint(self):
        from src.evaluation.adapters.deepparse_locked_adapter import LockedDeepparseFastTextAdapter
        with patch("src.evaluation.adapters.deepparse_locked_adapter.zero_shot_gate", return_value=(Path("fixture"), {"fixture": True})), patch("src.modeling.deepparse_training.construct_parser") as constructor:
            adapter = LockedDeepparseFastTextAdapter("fixture")
            constructor.assert_called_once_with({"fixture": True}, "cpu", checkpoint=None)
            self.assertEqual(adapter.tool_name, "DP-ZS-FT")

    def test_gpu_overlay_preserves_budget_and_rejects_amp_or_wrong_pin(self):
        from src.modeling.protocol import load_config
        from src.modeling.hardware_profile import apply_hardware_profile
        from src.evaluation.dev_runner import ROOT
        config = load_config(ROOT / "configs/modeling/sprint03/phobert_crf_v1.json")
        profile_path = ROOT / "configs/colab/sprint03/cuda128_profile_v1.json"
        overlaid = apply_hardware_profile(config, profile_path)
        expected = dict(overlaid)
        for key in ("hardware_profile", "hardware_profile_sha256"):
            expected.pop(key)
        expected["device"] = config["device"]
        self.assertEqual(expected, config)
        self.assertEqual(config["device"], "cpu")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            profile = json.loads(profile_path.read_text())
            profile["amp"] = True
            path.write_text(json.dumps(profile))
            with self.assertRaises(ValueError):
                apply_hardware_profile(config, path)
            profile["amp"] = False
            profile["protocol_lock_sha256"] = "wrong"
            path.write_text(json.dumps(profile))
            with self.assertRaises(ValueError):
                apply_hardware_profile(config, path)

    def test_bundles_merge_without_manifest_collision_and_refuse_drift(self):
        from src.modeling.colab_handoff import safe_extract, write_archive, check_bundle
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            one, two = root / "one.txt", root / "two.txt"
            one.write_text("code fixture")
            two.write_text("resource fixture")
            destination = root / "workspace"
            with patch("src.modeling.colab_handoff.ROOT", root):
                code = write_archive(root / "code.zip", {"src/fixture.txt": one}, {"scope": "fixture"})
                resource = write_archive(root / "resources.zip", {"resources/fixture.txt": two}, {"scope": "fixture"}, "resource_bundle_manifest.json")
            safe_extract(root / "code.zip", destination, code["sha256"])
            safe_extract(root / "resources.zip", destination, resource["sha256"], "resource_bundle_manifest.json")
            self.assertEqual(check_bundle(destination)["status"], "BUNDLE_HASH_PASS")
            self.assertEqual(check_bundle(destination, "resource_bundle_manifest.json")["files"], 1)
            (destination / "src/fixture.txt").write_text("drift")
            with self.assertRaises(FileExistsError):
                safe_extract(root / "code.zip", destination, code["sha256"])

    def test_zip_rejects_path_traversal_and_wrong_checksum(self):
        import zipfile
        from src.modeling.colab_handoff import safe_extract
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "bad.zip"
            with zipfile.ZipFile(archive, "w") as stream:
                stream.writestr("../outside.txt", "fixture")
            with self.assertRaises(ValueError):
                safe_extract(archive, root / "output", "wrong")
            with self.assertRaises(ValueError):
                safe_extract(archive, root / "output", file_hash(archive))
            self.assertFalse((root / "outside.txt").exists())

    def test_notebook_syntax_no_execution_and_training_off(self):
        from src.modeling.colab_handoff import notebook_content
        notebook = notebook_content({"sha256": "a" * 64}, {"sha256": "b" * 64})
        sources = []
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                source = "".join(cell["source"])
                ast.parse(source)
                sources.append(source)
                self.assertIsNone(cell["execution_count"])
                self.assertEqual(cell["outputs"], [])
        self.assertIn("ENABLE_NEURAL_TRAINING = False", sources[0])
        self.assertTrue(any('CHECKPOINT = RUN / "checkpoints/best.pt"' in source for source in sources))
        self.assertFalse(any("test_benchmark_t0" in source for source in sources))


if __name__ == "__main__":
    unittest.main()
