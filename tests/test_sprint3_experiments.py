"""Critical alignment, ambiguity, test exclusion and CRF execution checks."""

import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.evaluation.adapters.deepparse_adapter import align_native_tokens, map_native_output
from src.evaluation.adapters.heur_jw_adapter import HeuristicJaroWinklerAdapter
from src.evaluation.benchmark_runner import run_fivefield_inference, reserved_rows
from src.evaluation.dev_runner import file_hash
from src.evaluation.schema import CharacterSpan, SpanModelOutput
from src.evaluation.span_features import FEATURE_VERSION, TOKENIZER_VERSION, decode_bio, encode_gold, tokenize, token_features


def make_gazetteer(path):
    columns = ["entity_id", "level", "system", "canonical_name", "parent_id", "valid_from", "valid_to", "code_status"]
    rows = [
        ["p_old", "province", "cu", "Tỉnh Đông", "", "", "2025-06-30", "unverified"],
        ["p_new", "province", "moi", "Tỉnh Đông", "", "2025-07-01", "", "verified_from_mapping"],
        ["p_other", "province", "cu", "Tỉnh Tây", "", "", "2025-06-30", "unverified"],
        ["d", "district", "cu", "Quận Một", "p_old", "", "2025-06-30", "unverified"],
        ["w_old", "ward", "cu", "Phường An Phú", "d", "", "2025-06-30", "unverified"],
        ["w_new", "ward", "moi", "Phường An Phú", "p_new", "2025-07-01", "", "verified_from_mapping"],
        ["w_other", "ward", "cu", "Phường An Phú", "p_other", "", "2025-06-30", "unverified"],
    ]
    with (path/"entities.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerows(rows)
    (path/"aliases.csv").write_text("entity_id,alias,system,level,source_id,source_hash\n", encoding="utf-8-sig")
    for name in ("edges.csv", "non_atomic_transitions.csv"):
        (path/name).write_text("fixture\n", encoding="utf-8")
    hashes = {name: file_hash(path/name) for name in ("entities.csv", "aliases.csv", "edges.csv", "non_atomic_transitions.csv")}
    (path/"manifest.json").write_text(json.dumps({"version": "s3_v2_fixture", "output_sha256": hashes}), encoding="utf-8")


class ExperimentAlignmentTests(unittest.TestCase):
    def test_gold_word_boundary_crossing_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "boundary"):
            encode_gold("ABC123", [{"start": 0, "end": 3, "label": "TenDuong"}])

    def test_bio_decoding_logs_illegal_i_without_changing_offsets(self):
        text = "Đường Lê Lợi"
        spans, repairs = decode_bio(text, tokenize(text), ["I-TenDuong"]*3)
        self.assertEqual([(s.start, s.end, s.text) for s in spans], [(0, len(text), text)])
        self.assertEqual(len(repairs), 1)

    def test_deepparse_repeated_tokens_align_in_order(self):
        text = "12, Đường A, Phường A"
        components = [("12", "StreetNumber"), ("đường", "StreetName"), ("a", "StreetName"),
                      ("phường", "Municipality"), ("a", "Municipality")]
        spans, log = map_native_output(text, components)
        self.assertEqual([s.text for s in spans], ["12", "Đường A", "Phường A"])
        self.assertTrue(all(text[s.start:s.end] == s.text for s in spans))

    def test_deepparse_ambiguous_city_not_forced_to_province(self):
        spans, _ = map_native_output("Thành phố Phú Quốc", [("thành", "Municipality"),
            ("phố", "Municipality"), ("phú", "Municipality"), ("quốc", "Municipality")])
        self.assertEqual(spans, [])

    def test_deepparse_composite_admin_group_is_rejected(self):
        spans, log = map_native_output("Phường An Quận Một", [(x.lower(), "Municipality") for x in "Phường An Quận Một".split()])
        self.assertEqual(spans, [])
        self.assertIn("REJECT_MULTIPLE", log[0]["reason"])

    def test_deepparse_does_not_find_later_occurrence_on_mismatch(self):
        with self.assertRaises(ValueError):
            align_native_tokens("A B A", [("a", "StreetName"), ("a", "StreetName")])
        with self.assertRaises(ValueError):
            align_native_tokens("İ", [("i̇", "StreetName")])


class HeuristicRejectionTests(unittest.TestCase):
    def test_unit_type_is_not_erased_when_ranking_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            make_gazetteer(path)
            content = (path/"entities.csv").read_text(encoding="utf-8-sig")
            content = content.replace("w_new,ward,moi,Phường An Phú", "w_new,ward,moi,Xã An Phú")
            (path/"entities.csv").write_text(content, encoding="utf-8-sig")
            manifest = json.loads((path/"manifest.json").read_text())
            manifest["output_sha256"]["entities.csv"] = file_hash(path/"entities.csv")
            (path/"manifest.json").write_text(json.dumps(manifest))
            output = HeuristicJaroWinklerAdapter(path, 1.0).parse_spans("Phường An Phú, Tỉnh Đông")
            ward = next(s for s in output.spans if s.label == "PhuongXa")
            self.assertEqual(ward.system, "cu")
            trace = next(x for x in output.trace["admin_matches"] if x["surface"] == "Phường An Phú")
            self.assertEqual(trace["entity_id"], "w_old")

    def test_same_name_two_periods_supports_span_but_not_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            make_gazetteer(path)
            adapter = HeuristicJaroWinklerAdapter(path, 1.0)
            output = adapter.parse_spans("Phường An Phú, Tỉnh Đông")
            ward = next(s for s in output.spans if s.label == "PhuongXa")
            self.assertEqual(ward.system, "khong_xac_dinh")
            trace = next(x for x in output.trace["admin_matches"] if x["surface"] == "Phường An Phú")
            self.assertIsNone(trace["entity_id"])
            self.assertEqual(trace["contender_count"], 2)
            self.assertEqual(output.predicted_system, "khong_ro")

    def test_fixed_date_filters_old_and_hash_tampering_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            make_gazetteer(path)
            adapter = HeuristicJaroWinklerAdapter(path, 1.0, temporal_policy="fixed_as_of", as_of_date="2025-07-01")
            output = adapter.parse_spans("Quận Một, Tỉnh Đông")
            self.assertNotIn("QuanHuyen", [s.label for s in output.spans])
            with (path/"entities.csv").open("a", encoding="utf-8") as stream:
                stream.write("tampered\n")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                HeuristicJaroWinklerAdapter(path)

    def test_admin_context_rejects_wrong_province_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            make_gazetteer(path)
            output = HeuristicJaroWinklerAdapter(path, 1.0).parse_spans("Quận Một, Tỉnh Tây")
            self.assertNotIn("QuanHuyen", [s.label for s in output.spans])


class FivefieldIsolationTests(unittest.TestCase):
    def test_hold_manifest_uses_csv_physical_lines_not_record_indices(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"hold.json"
            samples = [{"sample_id": str(i), "text_sha256": "x", "source_dataset": "01_new", "group_id": str(i),
                        "stratum": "fixture", "source_row": str(i+2)} for i in range(100)]
            path.write_text(json.dumps({"total_samples": 100, "samples": samples}))
            with patch("src.evaluation.benchmark_runner.HOLD_MANIFEST_HASH", file_hash(path)):
                rows = reserved_rows(path)
            self.assertEqual(rows["01_new"], set(range(100)))

    def test_hold_row_never_reaches_adapter(self):
        class Spy:
            def __init__(self):
                self.seen = []
            def parse_spans(self, text):
                self.seen.append(text)
                return SpanModelOutput("", text, [CharacterSpan(0, len(text), "SoNha", text)])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/"bench.csv").write_text("ChuoiDiaChi,GT_SoNha\n12,secret-label\n99,held-label\n", encoding="utf-8-sig")
            hold = root/"hold.json"
            hold.write_text(json.dumps({"samples": [{"source_dataset": "01_new", "source_row": "3",
                "text_sha256": hashlib.sha256(b"99").hexdigest()}]}))
            spy = Spy()
            config = {"model_id": "FIXTURE", "run_id": "fixture_dev", "seed": 42, "supported_labels": ["SoNha"]}
            with patch("src.evaluation.benchmark_runner.BENCHMARKS", {"01_new": "bench.csv"}), \
                 patch("src.evaluation.benchmark_runner.reserved_rows", return_value={"01_new": {1}}), \
                 patch("src.evaluation.benchmark_runner.build_adapter", return_value=spy):
                report = run_fivefield_inference(config, root/"run", hold, root)
            self.assertEqual(spy.seen, ["12"])
            self.assertEqual(report["sample_count"], 1)
            self.assertNotIn("secret-label", (root/"run/predictions.jsonl").read_text())
            with self.assertRaises(FileExistsError):
                run_fivefield_inference(config, root/"run", hold, root)

    @unittest.skipUnless(importlib.util.find_spec("pycrfsuite"), "Run in the inventoried CRF runtime")
    def test_real_crf_training_and_literal_decode(self):
        import pycrfsuite
        from src.evaluation.adapters.crf_adapter import IndependentCRFAdapter
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            trainer = pycrfsuite.Trainer(verbose=False)
            text = "12 Đường Lê Lợi"
            tokens, tags = encode_gold(text, [{"start": 0, "end": 2, "label": "SoNha"},
                                              {"start": 3, "end": len(text), "label": "TenDuong"}])
            trainer.append(token_features(text, tokens, 1), tags)
            trainer.set_params({"c1": 0, "c2": 0.01, "max_iterations": 30})
            trainer.train(str(path/"model.crfsuite"))
            (path/"metadata.json").write_text(json.dumps({"context": 1, "feature_version": FEATURE_VERSION,
                "tokenizer_version": TOKENIZER_VERSION}), encoding="utf-8")
            output = IndependentCRFAdapter(str(path/"model.crfsuite"), str(path/"metadata.json")).parse_spans(text)
            self.assertEqual([(s.start, s.end, s.label) for s in output.spans], [(0,2,"SoNha"),(3,len(text),"TenDuong")])
            self.assertEqual(output.predicted_system, "khong_ro")


if __name__ == "__main__":
    unittest.main()
