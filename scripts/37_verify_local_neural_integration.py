"""Actual local neural integration only: no training or benchmark predictions."""
import argparse
from collections import Counter
from difflib import SequenceMatcher
from importlib import metadata
import inspect
import json
import os
from pathlib import Path
import platform
import time
import unicodedata

from src.evaluation.dev_runner import ROOT, file_hash, read_jsonl, write_json, write_jsonl
from src.modeling.alignment import encode_gold, decode_tags
from src.modeling.cli import validate_output_directory
from src.modeling.datasets import load_corpus
from src.modeling.labels import t1_target
from src.modeling.resources import validate_resource_lock, load_phobert_processor, offline_native_resources

CORPUS = ROOT / "data/processed/annotation/sprint03/corpus_train_dev_v2"


def audit_gold_alignment(alignment, row, manifest):
    """Gold is attached after the text-only alignment has been frozen."""
    before = alignment.to_dict()
    tags = encode_gold(alignment, row["spans"])
    spans, repairs = decode_tags(alignment, tags)
    if alignment.to_dict() != before or repairs:
        raise ValueError("ALIGNMENT_MUTATED_OR_BIO_REPAIRED")
    if {(s.start, s.end, s.label) for s in spans} != {(s["start"], s["end"], s["label"]) for s in row["spans"]}:
        raise ValueError("GOLD_ROUND_TRIP_FAILED")
    target, mask = t1_target(row, manifest)
    return {"status": "EXACT", "gold_span_count": len(spans), "t1_target": target, "t1_mask": mask}


def deepparse_api():
    from deepparse.parser import AddressParser
    from deepparse.dataset_container import ListDatasetContainer
    from src.modeling.deepparse_training import validate_native_api, training_pairs
    from deepparse.parser.address_parser import _pre_trained_tags_to_idx
    from deepparse.converter import DataProcessor, TagsConverter
    api = validate_native_api(AddressParser, ListDatasetContainer)
    fixture = [{"text": "12, Hà Nội", "spans": [{"start": 0, "end": 2, "label": "SoNha"},
                                               {"start": 4, "end": 10, "label": "TinhThanh"}]}]
    with offline_native_resources():
        container = ListDatasetContainer(training_pairs(fixture), is_training_container=True,
                                         data_cleaning_pre_processing_fn=None)
    mem = dict((line.split(":")[0], int(line.split()[1]) * 1024) for line in Path("/proc/meminfo").read_text().splitlines() if line.split()[1].isdigit())
    return {"status": "PACKAGE_API_PASS", "version": metadata.version("deepparse"), "signatures": api,
            "parser_source_sha256": file_hash(Path(inspect.getfile(AddressParser))),
            "fixture_container_rows": len(container), "native_constructor_executed": False,
            "native_pretrained_tags": _pre_trained_tags_to_idx,
            "native_eos_index": TagsConverter(_pre_trained_tags_to_idx)("EOS"),
            "native_inference_processor_signature": str(inspect.signature(DataProcessor.process_for_inference)),
            "native_output_contract_evidence": "installed FormattedParsedAddress.to_list; no native prediction emitted",
            "tag_mapping_sha256": file_hash(ROOT / "configs/deepparse_native_mapping_v1.json"),
            "pretrained_status": "PRETRAINED_INTEGRATION_BLOCKED_RESOURCE",
            "available_ram_bytes": mem["MemAvailable"], "required_fasttext_ram_bytes": 10 * 1024**3,
            "blockers": ["full FastText requires 10GiB available RAM", "embedding and pretrained weights license/resource lock pending"],
            "prediction_produced": False}


def rejected_segmentation_diagnostic(processor, text):
    segmented = processor.segmenter.word_segment(unicodedata.normalize("NFC", text))
    raw_stream = "".join(char for char in unicodedata.normalize("NFC", text) if not char.isspace())
    # The underscore removal is a diagnostic hypothesis only, never an offset fix.
    segmented_stream = "".join("".join(segmented).split()).replace("_", "")
    differences = [{"operation": op, "raw_nfc_range": [a, b], "segmented_range": [c, d],
                    "raw_fragment": raw_stream[a:b], "segmenter_fragment": segmented_stream[c:d]}
                   for op, a, b, c, d in SequenceMatcher(None, raw_stream, segmented_stream, autojunk=False).get_opcodes() if op != "equal"]
    return {"segmented_sentences": segmented, "stream_differences": differences,
            "usage": "review evidence only; no gold or offset repair performed"}


def run(lock_path, output, forward=True):
    validate_output_directory(output, "prepare")
    if output.exists():
        raise FileExistsError(output)
    lock = validate_resource_lock(lock_path, "PHOBERT-CRF")
    config = json.loads((ROOT / "configs/modeling/sprint03/phobert_crf_v1.json").read_text())
    output.mkdir(parents=True)
    write_json(output / "deepparse_api.json", deepparse_api())
    # This read-only hash gate establishes identity; no gold reaches the processor.
    manifest, splits = load_corpus(CORPUS)
    text_inputs = {name: [{"sample_id": r["sample_id"], "text": r["text"]} for r in rows] for name, rows in splits.items()}
    for split, inputs in text_inputs.items():
        write_jsonl(output / f"{split}_text_only.jsonl", inputs)
    with offline_native_resources():
        processor = load_phobert_processor(config, lock)
        smoke = []
        custom = ["12, đường Lê Lợi, phường Bến Nghé, TP. Hồ Chí Minh",
                  "Hà Nội, Hà Nội", "12/3-A, đường A_B; tầng 3", unicodedata.normalize("NFD", "12 Hà Nội"),
                  "đường " + "Hà Nội " * 300]
        for index, text in enumerate(custom):
            try:
                alignment = processor.align_text(text)
                smoke.append({"case": index, "status": "EXACT", "alignment": alignment.to_dict()})
            except ValueError as error:
                smoke.append({"case": index, "status": "REJECTED", "reason": str(error)})
        write_jsonl(output / "crafted_smoke.jsonl", smoke)
        alignments, alignment_rows = {}, []
        for split in ("train", "dev"):
            # Reload the text-only derivative; processor never sees source/gold/system.
            for item in read_jsonl(output / f"{split}_text_only.jsonl"):
                start = time.perf_counter()
                try:
                    alignment = processor.align_text(item["text"])
                    alignments[item["sample_id"]] = alignment
                    row = {"sample_id": item["sample_id"], "split": split, "status": "EXACT", "alignment": alignment.to_dict()}
                except ValueError as error:
                    row = {"sample_id": item["sample_id"], "split": split, "status": "UNREPRESENTABLE", "reason": str(error)}
                    row["segmentation_diagnostic"] = rejected_segmentation_diagnostic(processor, item["text"])
                row["latency_seconds"] = time.perf_counter() - start
                alignment_rows.append(row)
        write_jsonl(output / "text_only_alignments.jsonl", alignment_rows)
        frozen_alignment_hash = file_hash(output / "text_only_alignments.jsonl")
        # QA phase only, after the processor outputs are serialized and hashed.
        qa = []
        for split, rows in splits.items():
            for row in rows:
                alignment = alignments.get(row["sample_id"])
                try:
                    if alignment is None:
                        raise ValueError("TEXT_ALIGNMENT_UNREPRESENTABLE")
                    result = audit_gold_alignment(alignment, row, manifest)
                except ValueError as error:
                    result = {"status": "UNREPRESENTABLE", "reason": str(error)}
                qa.append({"sample_id": row["sample_id"], "split": split, **result})
        write_jsonl(output / "supervised_alignment_qa.jsonl", qa)
        if file_hash(output / "text_only_alignments.jsonl") != frozen_alignment_hash:
            raise ValueError("SERIALIZED_ALIGNMENT_CHANGED_AFTER_QA")
        encoder_smoke = {"status": "NOT_RUN", "reason": "forward disabled", "training_performed": False}
        if forward:
            import torch
            from transformers import AutoModel
            available = int(next(line.split()[1] for line in Path("/proc/meminfo").read_text().splitlines() if line.startswith("MemAvailable:"))) * 1024
            if available < 1400 * 1024**2:
                encoder_smoke = {"status": "BLOCKED", "reason": "short encoder smoke requires 1400MiB available RAM", "available_ram_bytes": available}
            else:
                crafted = processor.align_text("12 đường Lê Lợi, Hà Nội")
                model = AutoModel.from_pretrained(str(ROOT / lock["components"]["encoder"]["path"]), local_files_only=True)
                model.eval()
                with torch.no_grad():
                    result = model(input_ids=torch.tensor([crafted.input_ids]), attention_mask=torch.ones(1, len(crafted.input_ids), dtype=torch.long))
                encoder_smoke = {"status": "PRETRAINED_FORWARD_PASS", "input": "crafted_address_not_benchmark", "shape": list(result.last_hidden_state.shape),
                    "finite": bool(torch.isfinite(result.last_hidden_state).all()), "batch_size": 1, "device": "cpu", "model_eval": not model.training,
                    "gradient_enabled": False, "training_performed": False, "benchmark_prediction_produced": False}
                del model, result
        write_json(output / "encoder_smoke.json", encoder_smoke)
    result = {"purpose": "actual_package_and_processor_integration_no_training_no_metrics", "test100": "NOT_READ_NOT_USED", "colab": "NOT_USED",
              "resource_lock_sha256": file_hash(lock_path), "corpus_manifest_sha256": file_hash(CORPUS / "manifest.json"),
              "python": platform.python_version(), "runtime_prefix": os.path.relpath(os.sys.prefix, ROOT),
              "text_alignment": {split: dict(Counter(r["status"] for r in alignment_rows if r["split"] == split)) for split in splits},
              "gold_alignment_qa": {split: dict(Counter(r["status"] for r in qa if r["split"] == split)) for split in splits},
              "alignment_reject_reasons": dict(Counter(r["reason"] for r in alignment_rows if "reason" in r)),
              "t1_declared_exceptions": manifest["evaluation_exclusions"]["t1"], "encoder_smoke": encoder_smoke,
              "code_sha256": {p.relative_to(ROOT).as_posix(): file_hash(p) for p in (Path(__file__), ROOT / "src/modeling/alignment.py", ROOT / "src/modeling/resources.py")},
              "output_sha256": {p.name: file_hash(p) for p in output.iterdir() if p.is_file()}}
    write_json(output / "integration_manifest.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resource-lock", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--skip-forward", action="store_true")
    args = parser.parse_args()
    result = run(args.resource_lock.resolve(), args.output_dir.resolve(), not args.skip_forward)
    print(json.dumps({key: result[key] for key in ("text_alignment", "gold_alignment_qa", "encoder_smoke")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
