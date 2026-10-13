"""No pretrained downloads: contracts run everywhere; real Torch tests skip explicitly."""

import copy
import csv
import itertools
from importlib.util import find_spec
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import unicodedata

from src.evaluation.dev_runner import ROOT, file_hash, write_json, write_jsonl, run_dev_inference
from src.evaluation.schema import SPAN11_LABELS, CharacterSpan, SpanModelOutput
from src.evaluation.span_features import BIO_LABELS
from src.evaluation.span_scorer import compute_exact_span_metrics
from src.modeling.alignment import align_text, encode_gold, decode_tags, DeepparseProcessor, PhoBERTProcessor
from src.modeling.checkpoints import training_signature, validate_checkpoint_metadata
from src.modeling.datasets import load_corpus
from src.modeling.deepparse_training import training_pairs, decode_native_ids, validate_native_api
from src.modeling.labels import label_metadata, bio_constraints, TAG_TO_ID, t1_target
from src.modeling.protocol import load_config, candidate_config, selection_key, validate_training_config
from src.modeling.resources import preflight, validate_resource_lock
from src.modeling.artifacts import audit_run, audit_prepared
from src.modeling.calibration import confidence_sweep, CONFIDENCE_GRID
from src.modeling.structural_decoder import structure_decision, viterbi_reference
from src.data.administrative_code_verifier import TemporalGazetteerEvidence, verify_codes, validate_reference

CORPUS = ROOT / "data/processed/annotation/sprint03/corpus_train_dev_v2"
CONFIGS = ROOT / "configs/modeling/sprint03"


class FixtureTokenizer:
    """Alignment API fixture, not a real PhoBERT tokenizer or pretrained verification."""
    unk_token, pad_token_id = "<unk>", 1
    def tokenize(self, text):
        return [text[:2] + "@@", text[2:]] if len(text) > 2 else [text]
    def convert_tokens_to_ids(self, pieces):
        return list(range(3, len(pieces) + 3))
    def build_inputs_with_special_tokens(self, ids):
        return [0] + ids + [2]
    def get_special_tokens_mask(self, ids, already_has_special_tokens=False):
        return [1] + [0] * len(ids) + [1]


class FixtureSegmenter:
    def __init__(self, output=None):
        self.output = output
    def word_segment(self, text):
        return self.output if self.output is not None else [unicodedata.normalize("NFC", text)]


class AlignmentContractTests(unittest.TestCase):
    def test_diacritics_whitespace_punctuation_slash_hyphen(self):
        text = "12/3-5,\tPhố Hà Nội.\n(khu A)"
        a = align_text(text)
        spans = [{"start": 0, "end": 6, "label": "SoNha"}, {"start": 8, "end": 18, "label": "TenDuong"}, {"start": 21, "end": 26, "label": "Khac"}]
        tags = encode_gold(a, spans)
        decoded, _ = decode_tags(a, tags)
        self.assertEqual([(s.start, s.end, s.label) for s in decoded], [(s["start"], s["end"], s["label"]) for s in spans])
        self.assertEqual(tags[1], "O")

    def test_nfc_nfd_offsets_use_original_python_indices(self):
        for text in ("Hà Nội", unicodedata.normalize("NFD", "Hà Nội")):
            a = align_text(text)
            spans, _ = decode_tags(a, encode_gold(a, [{"start": 0, "end": len(text), "label": "TinhThanh"}]))
            self.assertEqual(spans[0].text, text)
            self.assertEqual(spans[0].end, len(text))

    def test_repeated_names_and_adjacent_entities(self):
        a = align_text("Hà Nội Hà Nội")
        tags = encode_gold(a, [{"start": 0, "end": 6, "label": "TinhThanh"}, {"start": 7, "end": 13, "label": "TinhThanh"}])
        self.assertEqual(tags, ["B-TinhThanh", "I-TinhThanh", "B-TinhThanh", "I-TinhThanh"])
        self.assertEqual(len(decode_tags(a, tags)[0]), 2)

    def test_gold_does_not_change_text_only_tokenization(self):
        text = "12 Hà Nội"
        before = align_text(text).to_dict()
        for label in SPAN11_LABELS:
            encode_gold(align_text(text), [{"start": 0, "end": 2, "label": label}])
            self.assertEqual(align_text(text).to_dict(), before)

    def test_offset_overlap_unknown_label_and_partial_token_reject(self):
        a = align_text("123 ABC")
        cases = [[{"start": -1, "end": 3, "label": "SoNha"}], [{"start": 0, "end": 3, "label": "Unknown"}],
                 [{"start": 0, "end": 2, "label": "SoNha"}], [{"start": 0, "end": 3, "label": "SoNha", "text": "12"}],
                 [{"start": 0, "end": 3, "label": "SoNha"}, {"start": 0, "end": 3, "label": "TenDuong"}]]
        for spans in cases:
            with self.subTest(spans=spans), self.assertRaises(ValueError):
                encode_gold(a, spans)

    def test_empty_input_rejects(self):
        for text in ("", " \t\n"):
            with self.assertRaises(ValueError):
                align_text(text)

    def test_illegal_bio_reject_or_logged_repair(self):
        a = align_text("ABC")
        with self.assertRaises(ValueError):
            decode_tags(a, ["I-TenDuong"])
        spans, repairs = decode_tags(a, ["I-TenDuong"], True)
        self.assertEqual(len(repairs), 1)
        self.assertEqual(spans[0].text, "ABC")

    def test_dp_punctuation_preserved_and_lowercase_alignment(self):
        a = DeepparseProcessor().align_text("12, Hà Nội")
        self.assertEqual(a.prepared_text, "12 , hà nội")
        spans, _ = decode_native_ids(a, [TAG_TO_ID["B-SoNha"], 0, TAG_TO_ID["B-TinhThanh"], TAG_TO_ID["I-TinhThanh"], 23])
        self.assertEqual(spans[1].text, "Hà Nội")
        with self.assertRaises(ValueError):
            DeepparseProcessor().align_text("İ")

    def test_dp_eos_missing_extra_unknown_and_illegal_bio(self):
        a = DeepparseProcessor().align_text("12 A")
        for ids in ([23], [0], [0, 0, 0], [99, 0]):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                decode_native_ids(a, ids)
        _, trace = decode_native_ids(a, [0, 0])
        self.assertTrue(trace["eos_missing_at_output_limit"])
        _, trace = decode_native_ids(a, [0, TAG_TO_ID["I-TenDuong"], 23])
        self.assertEqual(len(trace["illegal_bio_repairs"]), 1)

    def test_dp_converter_not_native_subset(self):
        rows = [{"text": "gần cầu", "spans": [{"start": 0, "end": 7, "label": "MocDinhVi"}]}]
        pairs = training_pairs(rows)
        self.assertEqual(pairs[0][1], ["B-MocDinhVi", "I-MocDinhVi"])

    def test_phobert_inserted_and_literal_underscore(self):
        p = PhoBERTProcessor(FixtureTokenizer(), FixtureSegmenter(["Hà_Nội , a_b"]), 256)
        a = p.align_text("Hà Nội, a_b")
        self.assertEqual(len(a.unit_to_model), 4)
        self.assertEqual(a.model_offsets[0], (-1, -1))
        self.assertTrue(a.special_mask[-1])
        encode_gold(a, [{"start": 0, "end": 6, "label": "TinhThanh"}, {"start": 8, "end": 11, "label": "Khac"}])

    def test_phobert_subword_crossing_multiple_raw_units(self):
        class WholeWord(FixtureTokenizer):
            def tokenize(self, text): return [text]
        a = PhoBERTProcessor(WholeWord(), FixtureSegmenter(["Hà_Nội"]), 256).align_text("Hà Nội")
        self.assertEqual(a.unit_to_model[0], a.unit_to_model[1])
        self.assertEqual(encode_gold(a, [{"start": 0, "end": 2, "label": "Khac"}]), ["B-Khac", "O"])

    def test_phobert_mixed_literal_inserted_underscores_in_one_word(self):
        a = PhoBERTProcessor(FixtureTokenizer(), FixtureSegmenter(["a_b_c"]), 256).align_text("a_b c")
        self.assertEqual(len(a.units), 2)
        self.assertTrue(all(a.unit_to_model))
        with self.assertRaises(ValueError):
            PhoBERTProcessor(FixtureTokenizer(), FixtureSegmenter(["Hà_Nội"]), 256).align_text("HàNội")

    def test_phobert_unknown_covers_known_original_interval(self):
        class Unknown(FixtureTokenizer):
            def tokenize(self, text): return ["<unk>"]
        a = PhoBERTProcessor(Unknown(), FixtureSegmenter(["Hà_Nội"]), 256).align_text("Hà Nội")
        self.assertEqual(a.model_offsets[1], (0, 6))

    def test_phobert_nfd_and_reject_unrecoverable_normalization(self):
        text = unicodedata.normalize("NFD", "Hà Nội")
        a = PhoBERTProcessor(FixtureTokenizer(), FixtureSegmenter(["Hà_Nội"]), 256).align_text(text)
        spans, _ = decode_tags(a, encode_gold(a, [{"start": 0, "end": len(text), "label": "TinhThanh"}]))
        self.assertEqual(spans[0].text, text)
        with self.assertRaises(ValueError):
            PhoBERTProcessor(FixtureTokenizer(), FixtureSegmenter(["Ha_Noi"]), 256).align_text("Hà Nội")

    def test_phobert_accepts_tone_relocation_and_keeps_raw_character_offsets(self):
        text = "Hòa"
        alignment = PhoBERTProcessor(FixtureTokenizer(), FixtureSegmenter(["Hoà"]), 256).align_text(text)
        self.assertEqual(alignment.raw_text, text)
        self.assertEqual(alignment.model_offsets[1:-1], [(0, 2), (2, 3)])
        self.assertEqual(alignment.diagnostics["tone_relocation_count"], 2)  # source and destination character slots
        decoded, repairs = decode_tags(alignment, encode_gold(alignment, [
            {"start": 0, "end": len(text), "label": "TinhThanh"}]))
        self.assertEqual(repairs, [])
        self.assertEqual(decoded[0].text, text)

    def test_phobert_rejects_tone_change_and_relocation_across_syllables(self):
        with self.assertRaisesRegex(ValueError, "SEGMENTER_CHANGED_TONE"):
            PhoBERTProcessor(FixtureTokenizer(), FixtureSegmenter(["Hoá"]), 256).align_text("Hòa")
        with self.assertRaisesRegex(ValueError, "SEGMENTER_CHANGED_TONE"):
            PhoBERTProcessor(FixtureTokenizer(), FixtureSegmenter(["Hoa_Bình"]), 256).align_text("Hòa Binh")
        with self.assertRaisesRegex(ValueError, "SEGMENTER_CHANGED_TONE"):
            PhoBERTProcessor(FixtureTokenizer(), FixtureSegmenter(["Hoa,Bình"]), 256).align_text("Hòa,Binh")
        with self.assertRaisesRegex(ValueError, "SEGMENTER_CHANGED_TONE"):
            PhoBERTProcessor(FixtureTokenizer(), FixtureSegmenter(["banà"]), 256).align_text("bàna")

    def test_phobert_normalizes_only_segmenter_input_and_preserves_nfd_offsets(self):
        text = unicodedata.normalize("NFD", "Hà Nội")
        class IdentitySegmenter:
            def word_segment(self, value):
                self.received = value
                return [value]
        segmenter = IdentitySegmenter()
        alignment = PhoBERTProcessor(FixtureTokenizer(), segmenter, 256).align_text(text)
        self.assertEqual(segmenter.received, "Hà Nội")
        self.assertEqual(alignment.raw_text, text)
        decoded, _ = decode_tags(alignment, encode_gold(alignment, [{"start": 0, "end": len(text), "label": "TinhThanh"}]))
        self.assertEqual(decoded[0].end, len(text))
        self.assertEqual(decoded[0].text, text)

    def test_phobert_length_special_mask_and_segmenter_drop_reject(self):
        with self.assertRaisesRegex(ValueError, "ENCODER_TOO_LONG"):
            PhoBERTProcessor(FixtureTokenizer(), FixtureSegmenter(), 3).align_text("Hà Nội")
        with self.assertRaises(ValueError):
            PhoBERTProcessor(FixtureTokenizer(), FixtureSegmenter(["Hà"]), 256).align_text("Hà Nội")
        class BadSpecial(FixtureTokenizer):
            def get_special_tokens_mask(self, ids, already_has_special_tokens=False): return [0] * len(ids)
        with self.assertRaises(ValueError):
            PhoBERTProcessor(BadSpecial(), FixtureSegmenter(), 256).align_text("Hà")


class ProtocolAndArtifactTests(unittest.TestCase):
    def test_all_configs_validate_and_ablation_shares_signature(self):
        for name in ("dp_ft_ft_v1", "phobert_crf_v1", "proposed_dyn_v1", "proposed_no_constraint_v1"):
            validate_training_config(load_config(CONFIGS / (name + ".json")))
        a = candidate_config(load_config(CONFIGS / "proposed_dyn_v1.json"), "c01")
        b = candidate_config(load_config(CONFIGS / "proposed_no_constraint_v1.json"), "c01")
        self.assertEqual(training_signature(a), training_signature(b))

    def test_protocol_rejects_labels_processor_test_and_candidate_mismatch(self):
        config = load_config(CONFIGS / "phobert_crf_v1.json")
        for key, value in (("processor_version", "different"), ("label_map", {}), ("selection_split", "test"), ("max_epochs", 99), ("candidate", {"id": "other"})):
            invalid = {**config, key: value}
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_training_config(invalid)

    def test_missing_protocol_lock_is_not_a_permissive_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("src.modeling.protocol.PROTOCOL_LOCK_PATH", Path(directory) / "missing_lock.json"):
                with self.assertRaisesRegex(ValueError, "PROTOCOL_LOCK_MISSING"):
                    load_config(CONFIGS / "phobert_crf_v1.json")

    def test_config_changes_after_protocol_lock_are_rejected(self):
        config = load_config(CONFIGS / "phobert_crf_v1.json")
        # A different allowed seed still requires a separately reviewed protocol/config.
        config["seed"] = 1337
        validate_training_config(config)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "changed.json"
            write_json(path, config)
            with self.assertRaisesRegex(ValueError, "CONFIG_CHANGED_AFTER_PROTOCOL_LOCK"):
                load_config(path)

    def test_corpus_hash_count_and_mask(self):
        manifest, splits = load_corpus(CORPUS)
        self.assertEqual([len(splits[s]) for s in ("train", "dev")], [240, 60])
        self.assertEqual([sum(t1_target(row, manifest)[1] for row in splits[s]) for s in ("train", "dev")], [206, 53])
        excluded = set(manifest["evaluation_exclusions"]["t1"])
        for row in splits["dev"]:
            if row["sample_id"] in excluded:
                self.assertFalse(t1_target(row, manifest)[1])
                self.assertTrue(encode_gold(align_text(row["text"]), row["spans"]))

    def test_null_is_masked_not_fourth_target(self):
        for system in (None, "khong_ro", "not_a_class"):
            self.assertEqual(t1_target({"sample_id": "a", "address_system": system}, {}), (0, False))

    def test_selection_micro_macro_then_epoch_then_candidate(self):
        gold = [{"sample_id": "a", "text": "12 X", "spans": [{"start": 0, "end": 2, "label": "SoNha"}, {"start": 3, "end": 4, "label": "Khac"}], "address_system": None}]
        metrics = compute_exact_span_metrics([SpanModelOutput("a", "12 X", [CharacterSpan(0, 2, "SoNha", "12")])], gold)
        self.assertAlmostEqual(selection_key(metrics, 1)[0], 2/3)
        self.assertGreater(selection_key(metrics, 1), selection_key(metrics, 2))
        self.assertGreater(selection_key(metrics, 1, 0), selection_key(metrics, 1, 1))

    def test_missing_resources_blocks_without_installation(self):
        result = preflight(load_config(CONFIGS / "phobert_crf_v1.json"))
        self.assertTrue(result["blockers"])
        self.assertFalse(result["download_performed"])
        self.assertFalse(result["training_performed"])
        with self.assertRaisesRegex(ValueError, "RESOURCE_EVIDENCE_PENDING"):
            validate_resource_lock(CONFIGS / "phobert_resource_lock_template.json", "PHOBERT-CRF")

    def test_checkpoint_mismatch_and_resume_policy(self):
        config = candidate_config(load_config(CONFIGS / "dp_ft_ft_v1.json"), "c01")
        meta = {"label_map": label_metadata(), "processor_version": config["processor_version"],
                "corpus_manifest_sha256": "data", "resource_lock_sha256": "resources", "training_signature": training_signature(config), "resume_supported": False}
        validate_checkpoint_metadata(meta, config, "data", "resources")
        with self.assertRaisesRegex(ValueError, "RESUME_UNSUPPORTED"):
            validate_checkpoint_metadata(meta, config, "data", "resources", True)
        for bad in ({**meta, "label_map": {}}, {**meta, "resource_lock_sha256": "changed"}, {**meta, "training_signature": "changed"}):
            with self.assertRaises(ValueError): validate_checkpoint_metadata(bad, config, "data", "resources")

    def test_neural_cli_help_never_imports_optional_models(self):
        for module in ("scripts.30_prepare_model_training_data", "scripts.31_train_deepparse_finetuned", "scripts.32_train_phobert_crf", "scripts.33_train_proposed_dynamic", "scripts.34_audit_modeling_artifacts", "scripts.35_verify_gazetteer_sources"):
            result = subprocess.run([sys.executable, "-m", module, "--help"], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("usage:", result.stdout)

    def test_native_api_guard_accepts_contract_rejects_wrong_version(self):
        class Parser:
            def __init__(self, cache_dir=None, offline=False, path_to_retrained_model=None): pass
            def retrain(self, val_dataset_container=None, prediction_tags=None, seq2seq_params=None, callbacks=None): pass
        class Container:
            def __init__(self, data, is_training_container=True, data_cleaning_pre_processing_fn=None): pass
        self.assertIn("val_dataset_container", validate_native_api(Parser, Container)["retrain"])
        with self.assertRaises(RuntimeError): validate_native_api(object, Container)

    def test_resource_hash_changed_or_extra_files_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            resource = folder / "model.bin"
            resource.write_bytes(b"fixture")
            entry = {"path": str(folder), "revision": "fixture-not-pretrained", "license_status": "CLEARED", "files": {"model.bin": file_hash(resource)}}
            lock_path = folder.parent / (folder.name + "_lock.json")
            try:
                write_json(lock_path, {"model_family": "PHOBERT", "components": {name: entry for name in ("encoder", "tokenizer", "segmenter")}})
                validate_resource_lock(lock_path, "PHOBERT-CRF")
                (folder / "undeclared.bin").write_bytes(b"extra")
                with self.assertRaisesRegex(ValueError, "UNDECLARED_FILES"): validate_resource_lock(lock_path, "PHOBERT-CRF")
                (folder / "undeclared.bin").unlink()
                resource.write_bytes(b"changed")
                with self.assertRaisesRegex(ValueError, "HASH_MISMATCH"): validate_resource_lock(lock_path, "PHOBERT-CRF")
            finally:
                lock_path.unlink(missing_ok=True)

    def test_frozen_prediction_audit_tampering_and_metadata_input_reject(self):
        class FixtureAdapter:
            def parse_spans(self, text):
                return SpanModelOutput("", text, [CharacterSpan(0, 1, "SoNha", text[:1])])
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            corpus = base / "corpus"
            corpus.mkdir()
            golds = [{"sample_id": "fixture_dev", "text": "2", "spans": [{"start": 0, "end": 1, "label": "SoNha", "system": "khong_xac_dinh"}], "address_system": None}]
            write_jsonl(corpus / "train.jsonl", [{**golds[0], "sample_id": "fixture_train", "text": "1"}])
            write_jsonl(corpus / "dev.jsonl", golds)
            inputs = [{"sample_id": "fixture_dev", "text": "2"}]
            write_jsonl(corpus / "dev_input.jsonl", inputs)
            write_json(corpus / "manifest.json", {"status": "TRAIN_DEV_APPROVED_TEST_PENDING", "sample_counts": {"train": 1, "dev": 1},
                "output_sha256": {name: file_hash(corpus / name) for name in ("train.jsonl", "dev.jsonl", "dev_input.jsonl")}, "evaluation_exclusions": {"t1": []}})
            config = {"model_id": "alignment-fixture", "run_id": "fixture_dev", "seed": 42, "supported_labels": list(SPAN11_LABELS),
                      "resources": {}, "purpose": "unit_or_integration_test", "pretrained": False}
            run = base / "verification_run"
            with self.assertRaises(ValueError):
                run_dev_inference(FixtureAdapter(), [{**inputs[0], "GT_SoNha": "2"}], config, run)
            run_dev_inference(FixtureAdapter(), inputs, config, run, {"corpus_manifest_sha256": file_hash(corpus / "manifest.json")})
            self.assertEqual(audit_run(run, corpus, False)["status"], "AUDIT_PASS")
            (run / "predictions.jsonl").write_text("\n", encoding="utf-8")
            audit = audit_run(run, corpus, False)
            self.assertEqual(audit["status"], "AUDIT_FAIL")
            self.assertIn("DEV_ID_COUNT_MISMATCH", audit["issues"])
            self.assertTrue(any("OUTPUT_HASH_MISMATCH" in issue for issue in audit["issues"]))

    def test_frozen_validation_calls_existing_scorer_with_correct_contract(self):
        from src.modeling.training import freeze_validation
        from src.modeling import artifacts
        class FixtureAdapter:
            def parse_spans(self, text): return SpanModelOutput("", text, [CharacterSpan(0, 1, "SoNha", text)])
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            corpus = base / "fixture_corpus"
            corpus.mkdir()
            gold = {"sample_id": "fixture", "text": "2", "spans": [{"start": 0, "end": 1, "label": "SoNha", "system": "khong_xac_dinh"}], "address_system": None}
            write_jsonl(corpus / "train.jsonl", [{**gold, "sample_id": "train_fixture"}])
            write_jsonl(corpus / "dev.jsonl", [gold])
            write_jsonl(corpus / "dev_input.jsonl", [{"sample_id": "fixture", "text": "2"}])
            write_json(corpus / "manifest.json", {"status": "TRAIN_DEV_APPROVED_TEST_PENDING", "sample_counts": {"train": 1, "dev": 1},
                "output_sha256": {name: file_hash(corpus / name) for name in ("train.jsonl", "dev.jsonl", "dev_input.jsonl")}, "evaluation_exclusions": {"t1": []}})
            config = {"model_id": "fixture", "run_id": "fixture_dev", "seed": 42, "supported_labels": list(SPAN11_LABELS),
                      "resources": {}, "purpose": "unit_or_integration_test", "pretrained": False, "t1_implemented": False}
            with patch("src.modeling.training.modeling_config", return_value=config), patch("src.modeling.training.capture_rng", return_value={}), patch("src.modeling.training.restore_rng") as restore, patch("src.modeling.training.audit_run", side_effect=lambda run, data: artifacts.audit_run(run, data, False)):
                metrics = freeze_validation(FixtureAdapter(), config, base / "fixture_only.pt", base / "fixture_lock.json", corpus, base / "fixture_training", 1)
                self.assertEqual(metrics["t0_exact_span"]["micro"]["f1"], 1.0)
                restore.assert_called_once_with({})

    def test_new_output_cannot_write_frozen_or_raw_roots(self):
        from src.modeling.cli import validate_output_directory
        for path in (CORPUS / "new_dir", ROOT / "data/raw/new_dir", ROOT / "data/processed/gazetteer/s3_v2/new_dir"):
            with self.assertRaises(ValueError): validate_output_directory(path, "prepare")
        validate_output_directory(ROOT / "data/interim/modeling/sprint03/new_fixture", "prepare")

    def test_alignment_all_300_without_gold_dependent_tokens(self):
        _, splits = load_corpus(CORPUS)
        for rows in splits.values():
            for row in rows:
                for processor in (align_text, DeepparseProcessor().align_text):
                    alignment = processor(row["text"])
                    before = alignment.to_dict()
                    spans, _ = decode_tags(alignment, encode_gold(alignment, row["spans"]))
                    self.assertEqual(alignment.to_dict(), before)
                    self.assertEqual({(s.start, s.end, s.label) for s in spans}, {(s["start"], s["end"], s["label"]) for s in row["spans"]})


class StructureTests(unittest.TestCase):
    def test_t1_sweep_masks_manifest_exceptions_and_null(self):
        golds = [{"sample_id": "eligible", "address_system": "moi"}, {"sample_id": "excluded", "address_system": "cu"}, {"sample_id": "null", "address_system": None}]
        predictions = [{"sample_id": row["sample_id"], "status": "ok", "abstain": False,
                       "trace": {"structure": {"posterior": {"cu": 0.01, "moi": 0.98, "Lai": 0.01}}}} for row in golds]
        result = confidence_sweep(predictions, golds, {"evaluation_exclusions": {"t1": ["excluded"]}})
        self.assertEqual(len(result["grid"]), 6)
        self.assertEqual(result["selected"]["eligible"], 1)
        self.assertEqual(result["selected"]["accuracy_all_eligible"], 1)
        self.assertEqual(result["excluded_ids"], ["excluded", "null"])
        predictions[1]["trace"]["structure"]["posterior"] = None
        self.assertEqual(confidence_sweep(predictions, golds, {"evaluation_exclusions": {"t1": ["excluded"]}})["selected"], result["selected"])
        with self.assertRaises(ValueError): confidence_sweep(predictions[:1], golds, {})

    def test_confident_new_only_bans_district(self):
        decision = structure_decision([0.01, 0.98, 0.01])
        self.assertEqual(decision["predicted_system"], "moi")
        self.assertTrue(decision["ban_district"])
        for posterior in ([0.98, 0.01, 0.01], [0.01, 0.01, 0.98], [0.2, 0.6, 0.2]):
            self.assertFalse(structure_decision(posterior)["ban_district"])
        self.assertFalse(structure_decision([0.01, 0.98, 0.01], enabled=False)["ban_district"])

    def test_invalid_posteriors_reject(self):
        for posterior in ([0.5, 0.5], [1, 1, 1], [math.nan, 0, 1], [-1, 1, 1]):
            with self.assertRaises(ValueError): structure_decision(posterior)

    def test_viterbi_bio_and_constraint_on_wrong_t1(self):
        n = len(BIO_LABELS)
        emissions = [[0.0] * n for _ in range(2)]
        emissions[0][TAG_TO_ID["I-QuanHuyen"]] = 100
        emissions[0][TAG_TO_ID["B-QuanHuyen"]] = 10
        emissions[1][TAG_TO_ID["I-QuanHuyen"]] = 10
        transitions, starts = [[0.0] * n for _ in range(n)], [0.0] * n
        original, _ = viterbi_reference(emissions, transitions, starts, starts)
        self.assertEqual(original, [TAG_TO_ID["B-QuanHuyen"], TAG_TO_ID["I-QuanHuyen"]])
        after, _ = viterbi_reference(emissions, transitions, starts, starts, structure_decision([0.01, 0.98, 0.01])["forbidden_tag_ids"])
        self.assertFalse(any(BIO_LABELS[i].endswith("-QuanHuyen") for i in after))
        # When T1 is wrong this loses district recall: policy cannot promise zero errors.
        self.assertEqual(len(after), len(original))
        with self.assertRaises(ValueError): viterbi_reference([], transitions, starts, starts)


class GazetteerEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gaz = TemporalGazetteerEvidence(ROOT / "data/processed/gazetteer/s3_v2")

    def test_date_boundary_old_end_inclusive_adapter(self):
        row = next(row for row in self.gaz.entities if row["system"] == "cu" and row["level"] == "district")
        old = self.gaz.lookup(row["canonical_name"], "district", "2025-06-30")
        new = self.gaz.lookup(row["canonical_name"], "district", "2025-07-01")
        self.assertIn(row["entity_id"], [r["entity_id"] for r in old["candidates"]])
        self.assertNotIn(row["entity_id"], [r["entity_id"] for r in new["candidates"]])

    def test_duplicate_name_not_first_row_and_parent_context(self):
        wards = [row for row in self.gaz.entities if row["system"] == "cu" and row["level"] == "ward"]
        counts = {}
        for row in wards: counts[row["canonical_name"]] = counts.get(row["canonical_name"], 0) + 1
        name = next(name for name, count in counts.items() if count > 1)
        result = self.gaz.lookup(name, "ward", "2025-06-30")
        self.assertEqual(result["status"], "AMBIGUOUS")
        selected = result["candidates"][0]
        context = {"province": selected["full_key"][2], "district": selected["full_key"][3]}
        narrowed = self.gaz.lookup(name, "ward", "2025-06-30", context)
        self.assertEqual(len(narrowed["candidates"]), 1)

    def test_multiple_targets_and_non_atomic_preserved(self):
        counts = {}
        for row in self.gaz.edges: counts[row["old_entity_id"]] = counts.get(row["old_entity_id"], 0) + 1
        old_id = next(sid for sid, count in counts.items() if count > 1)
        self.assertEqual(self.gaz.targets(old_id)["status"], "MULTIPLE_TARGETS_REQUIRES_CONTEXT")
        self.assertEqual(len(self.gaz.non_atomic), 5)

    def test_exact_full_key_and_leading_zero_no_padding(self):
        row = next(row for row in self.gaz.entities if row["system"] == "cu" and row["candidate_code"].startswith("0"))
        system, level, province, district, ward = self.gaz.full_key(row)
        ref = {"system": system, "level": level, "province": province, "district": district, "ward": ward,
               "code": row["candidate_code"], "valid_from": "2024-01-01", "valid_to": "2025-07-01", "source_id": "fixture", "source_locator": "fixture p1"}
        decisions = {d["entity_id"]: d for d in verify_codes(self.gaz, [ref], "2025-06-30")}
        self.assertEqual(decisions[row["entity_id"]]["verified_code"], row["candidate_code"])
        self.assertEqual(decisions[row["entity_id"]]["status"], "VERIFIED_PRIMARY_REFERENCE")
        for bad in ({**ref, "district": "Other"}, {**ref, "code": row["candidate_code"].lstrip("0")}, {**ref, "valid_to": "2024-07-01"}):
            d = next(d for d in verify_codes(self.gaz, [bad], "2025-06-30") if d["entity_id"] == row["entity_id"])
            self.assertIsNone(d["verified_code"])

    def test_no_reference_means_zero_verified(self):
        decisions = verify_codes(self.gaz, [], "2025-06-30")
        self.assertEqual(sum(d["verified_code"] is not None for d in decisions), 0)
        self.assertEqual(len(decisions), 14149)

    def test_reference_manifest_authority_hash_columns_and_interval(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            reference, meta_path = folder / "ref.csv", folder / "manifest.json"
            columns = ["province", "district", "ward", "level", "system", "code", "valid_from", "valid_to", "source_id", "source_locator"]
            row = dict(zip(columns, ["Tỉnh A", "Huyện B", "Xã C", "ward", "cu", "00123", "2025-06-30", "2025-07-01", "fixture", "fixture page1"]))
            with reference.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=columns)
                writer.writeheader()
                writer.writerow(row)
            metadata = {"schema_version": "s3-official-code-reference-v1", "source_id": "fixture", "url": "https://vbpl.vn/fixture-only",
                "issuer": "fixture-only", "document_id": "fixture-only", "accessed_at": "2026-10-02", "reference_sha256": file_hash(reference),
                "authority_status": "OFFICIAL_PRIMARY_SOURCE", "extraction_review_status": "APPROVED", "license_status": "UNKNOWN",
                "effective_from": "2025-06-30", "effective_to": "2025-07-01", "table_as_of": "2025-06-30", "change_history_verified_through": None}
            write_json(meta_path, metadata)
            _, values = validate_reference(reference, meta_path)
            self.assertEqual(values[0]["code"], "00123")
            for invalid in ({**metadata, "authority_status": "THIRD_PARTY"}, {**metadata, "url": "https://example.com/source"}, {**metadata, "reference_sha256": "changed"}, {**metadata, "effective_to": "2025-06-30"}):
                write_json(meta_path, invalid)
                with self.assertRaises(ValueError): validate_reference(reference, meta_path)


try:
    import torch
except ImportError:
    torch = None


@unittest.skipIf(find_spec("deepparse") is None, "deepparse absent: actual pinned parser/container API integration PENDING_RESOURCE")
class DeepparsePackageIntegrationTests(unittest.TestCase):
    def test_actual_package_api_and_bio24_dataset_container(self):
        from deepparse.parser import AddressParser
        from deepparse.dataset_container import ListDatasetContainer
        api = validate_native_api(AddressParser, ListDatasetContainer)
        data = training_pairs([{"text": "12, Hà Nội", "spans": [{"start": 0, "end": 2, "label": "SoNha"}, {"start": 4, "end": 10, "label": "TinhThanh"}]}])
        container = ListDatasetContainer(data, is_training_container=True, data_cleaning_pre_processing_fn=None)
        self.assertEqual(len(container), 1)
        self.assertIn("val_dataset_container", api["retrain"])


@unittest.skipIf(torch is None, "torch absent: real CRF/tiny model forward/backward/save/resume integration PENDING_RESOURCE")
class TorchIntegrationTests(unittest.TestCase):
    @staticmethod
    def encoder():
        class TinyEncoder(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.config = SimpleNamespace(hidden_size=8)
                self.embedding = torch.nn.Embedding(32, 8)
            def forward(self, input_ids, attention_mask):
                return SimpleNamespace(last_hidden_state=self.embedding(input_ids))
        return TinyEncoder()

    def test_crf_partition_viterbi_against_bruteforce(self):
        from src.modeling.crf import LinearChainCRF
        crf = LinearChainCRF().double()
        torch.manual_seed(42)
        emissions = torch.randn(1, 2, 23, dtype=torch.double, requires_grad=True)
        mask = torch.ones(1, 2, dtype=torch.bool)
        starts, allowed = bio_constraints()
        scores, paths = [], []
        for path in itertools.product(range(23), repeat=2):
            if starts[path[0]] and allowed[path[0]][path[1]]:
                scores.append(float(emissions[0, 0, path[0]].detach() + emissions[0, 1, path[1]].detach()))
                paths.append(list(path))
        expected = math.log(sum(math.exp(value) for value in scores))
        self.assertAlmostEqual(float(crf.log_partition(emissions, mask)[0]), expected, places=10)
        self.assertEqual(crf.decode(emissions, mask)[0], paths[max(range(len(scores)), key=scores.__getitem__)])
        loss = crf.nll(emissions, torch.tensor([[0, 0]]), mask)
        loss.backward()
        self.assertTrue(torch.isfinite(emissions.grad).all())
        self.assertTrue(torch.isfinite(crf.transitions.grad).all())

    def test_crf_mask_padding_and_illegal_tags(self):
        from src.modeling.crf import LinearChainCRF
        crf = LinearChainCRF()
        emissions = torch.randn(2, 3, 23)
        mask = torch.tensor([[1, 1, 1], [1, 1, 0]], dtype=torch.bool)
        self.assertEqual([len(p) for p in crf.decode(emissions, mask)], [3, 2])
        with self.assertRaises(ValueError): crf.decode(emissions, torch.tensor([[1, 0, 1], [1, 1, 0]], dtype=torch.bool))
        with self.assertRaises(ValueError): crf.nll(emissions, torch.full((2, 3), -100), mask)

    def test_phobert_forward_backward_and_no_special_padding_gold(self):
        from src.modeling.phobert_crf import PhoBERTCRF
        model = PhoBERTCRF(self.encoder(), dropout=0)
        result = model(torch.tensor([[0, 3, 4, 2], [0, 5, 2, 1]]), torch.tensor([[1, 1, 1, 1], [1, 1, 1, 0]]),
                       [[[1], [2]], [[1]]], torch.tensor([[0, 0], [0, 0]]))
        result["loss"].backward()
        self.assertTrue(torch.isfinite(result["loss"]))
        self.assertGreater(float(model.emission.weight.grad.abs().sum()), 0)
        self.assertGreater(float(model.crf.transitions.grad.abs().sum()), 0)
        self.assertEqual(result["mask"].tolist(), [[True, True], [True, False]])

    def test_t1_mask_all_null_finite_and_exception_t0_loss(self):
        from src.modeling.proposed_dynamic import ProposedDynamic
        model = ProposedDynamic(self.encoder(), dropout=0)
        args = [torch.tensor([[0, 3, 2]]), torch.ones(1, 3, dtype=torch.long), [[[1]]]]
        result = model(*args, tags=torch.tensor([[TAG_TO_ID["B-SoNha"]]]), t1_targets=torch.tensor([0]), t1_mask=torch.tensor([False]))
        result["loss"].backward()
        self.assertEqual(float(result["t1_loss"]), 0)
        self.assertTrue(torch.isfinite(result["loss"]))
        self.assertGreater(float(model.emission.weight.grad.abs().sum()), 0)
        self.assertEqual(float(model.t1_head.weight.grad.abs().sum()), 0)

    def test_tiny_checkpoint_save_reload_optimizer_resume(self):
        from src.modeling.phobert_crf import PhoBERTCRF
        from src.modeling.checkpoints import save_checkpoint, load_checkpoint
        model = PhoBERTCRF(self.encoder(), dropout=0)
        config = candidate_config(load_config(CONFIGS / "phobert_crf_v1.json"), "c01")
        optimizer = torch.optim.AdamW(model.parameters())
        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda step: 1)
        meta = {"label_map": label_metadata(), "processor_version": config["processor_version"], "corpus_manifest_sha256": "data",
                "resource_lock_sha256": "resources", "training_signature": training_signature(config), "resume_supported": True,
                "purpose": "unit_or_integration_test", "pretrained": False}
        model.eval()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.pt"
            save_checkpoint(path, model, meta, optimizer, scheduler, {"best_key": [0, 0, -1, 0]})
            other = PhoBERTCRF(self.encoder(), dropout=0)
            other_optimizer = torch.optim.AdamW(other.parameters())
            other_scheduler = torch.optim.lr_scheduler.LambdaLR(other_optimizer, lambda step: 1)
            load_checkpoint(path, config, "data", "resources", other, other_optimizer, other_scheduler, True)
            for a, b in zip(model.parameters(), other.parameters()): self.assertTrue(torch.equal(a, b))
            with self.assertRaises(FileExistsError): save_checkpoint(path, other, meta)
            path.write_bytes(path.read_bytes() + b"tampered")
            with self.assertRaises(ValueError): load_checkpoint(path, config, "data", "resources")

    def test_adapter_text_only_offsets_and_paired_decoder(self):
        from src.modeling.proposed_dynamic import ProposedDynamic
        from src.evaluation.adapters.proposed_dynamic_adapter import ProposedDynamicAdapter
        model = ProposedDynamic(self.encoder(), dropout=0)
        processor = PhoBERTProcessor(FixtureTokenizer(), FixtureSegmenter(), 256)
        config = candidate_config(load_config(CONFIGS / "proposed_dyn_v1.json"), "c01")
        adapter = ProposedDynamicAdapter(config=config, model=model, processor=processor)
        output = adapter.parse_spans("12 Hà Nội")
        self.assertEqual(output.raw_text, "12 Hà Nội")
        for span in output.spans: self.assertEqual(span.text, output.raw_text[span.start:span.end])
        self.assertIn("path_before_constraint", output.trace)
        self.assertIn("posterior", output.trace["structure"])
