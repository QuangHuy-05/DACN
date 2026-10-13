"""Audit PhoBERT character alignment with the pinned VnCoreNLP word segmenter.

This is an alignment-only check. It reads approved train/dev, never reads test100,
and emits neither model predictions nor metrics.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

from src.evaluation.dev_runner import ROOT, file_hash, read_jsonl, write_json, write_jsonl
from src.evaluation.span_features import tokenize
from src.modeling.alignment import _segmented_word_maps, align_text, encode_gold, decode_tags
from src.modeling.cli import validate_output_directory
from src.modeling.datasets import CORPUS_MANIFEST_SHA256, load_corpus


CORPUS = ROOT / "data/processed/annotation/sprint03/corpus_train_dev_v2"
RESOURCE_LOCK = ROOT / "data/interim/modeling/sprint03/task_01_06_20261003_v1/resource_lock_local_v1.json"
PREVIOUS_AUDIT = ROOT / "data/interim/modeling/sprint03/task_01_06_20261003_v1/alignment_coverage_and_review.json"
PREVIOUS_SEGMENTATION = ROOT / "data/interim/modeling/sprint03/task_01_06_20261003_v1/neural_integration_v2/text_only_alignments.jsonl"
EXPECTED_COUNTS = {"train": 240, "dev": 60}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def verify_segmenter_assets(lock: dict) -> tuple[Path, Path]:
    component = lock["components"]["segmenter"]
    directory = ROOT / component["path"]
    for relative, expected in component["files"].items():
        path = directory / relative
        if not path.is_file() or file_hash(path) != expected:
            raise ValueError(f"SEGMENTER_ASSET_HASH_MISMATCH:{relative}")
    return directory, directory / "VnCoreNLP-1.2.jar"


def run_segmenter(java: str, jar: Path, working_directory: Path,
                  texts: list[str], output: Path, split: str) -> list[str]:
    if any(any(char in text for char in "\r\n\t") for text in texts):
        raise ValueError(f"UNSUPPORTED_CONTROL_CHARACTER_IN_{split.upper()}_TEXT")
    input_path = output / f"{split}_segmenter_input.txt"
    output_path = output / f"{split}_segmenter_output.tsv"
    with input_path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(texts))
        stream.write("\n")
    command = [java, "-Xmx1g", "-jar", str(jar), "-fin", str(input_path.resolve()),
               "-fout", str(output_path.resolve()), "-annotators", "wseg"]
    started = time.perf_counter()
    result = subprocess.run(command, cwd=working_directory, capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=900)
    (output / f"{split}_segmenter_process.log").write_text(
        result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"VNCORenlp_WSEG_FAILED_{split.upper()}:{result.returncode}")
    if not output_path.is_file():
        raise RuntimeError(f"VNCORenlp_OUTPUT_MISSING_{split.upper()}")
    groups, current = [], []
    for line_index, line in enumerate(output_path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            if current:
                groups.append(current)
                current = []
            continue
        columns = line.split("\t")
        if len(columns) < 2 or not columns[0].strip().isdigit() or not columns[1].strip():
            raise ValueError(f"VNCORenlp_OUTPUT_ROW_INVALID_{split.upper()}:{line_index}")
        current.append(columns[1].strip())
    if current:
        groups.append(current)

    # The CLI emits one group per sentence, so a source address with punctuation
    # may span multiple groups. Greedily join groups until they map exactly to
    # the current text; no marker or synthetic character is added to model input.
    segmented, group_index = [], 0
    for sample_index, text in enumerate(texts):
        words = []
        for candidate_group_index in range(group_index, len(groups)):
            words.extend(groups[candidate_group_index])
            try:
                _segmented_word_maps(text, words)
            except ValueError as error:
                if "SEGMENTER_DROPPED_TEXT" in str(error):
                    continue
                raise ValueError(f"VNCORenlp_GROUP_MAPPING_FAILED_{split.upper()}:{sample_index}:{error}") from error
            segmented.append(" ".join(words))
            group_index = candidate_group_index + 1
            break
        else:
            raise ValueError(f"VNCORenlp_CANNOT_ASSIGN_SENTENCE_GROUPS_{split.upper()}:{sample_index}")
    if group_index != len(groups):
        raise ValueError(f"VNCORenlp_UNASSIGNED_SENTENCE_GROUPS_{split.upper()}:{len(groups) - group_index}")
    (output / f"{split}_segmenter_timing.json").write_text(json.dumps(
        {"sample_count": len(texts), "elapsed_seconds": time.perf_counter() - started,
         "command": command, "return_code": result.returncode}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    return segmented


def audit_text_alignment(rows: list[dict], split: str, segmented_texts: list[str]) -> list[dict]:
    aligned = []
    for row, segmented in zip(rows, segmented_texts):
        try:
            words = segmented.split()
            maps, relocations = _segmented_word_maps(row["text"], words)
            mapped_ranges = [interval for word_map in maps for interval in word_map
                             if interval[0] < interval[1]]
            missing_units = [index for index, unit in enumerate(tokenize(row["text"]))
                             if not any(start < unit.end and end > unit.start
                                        for start, end in mapped_ranges)]
            if missing_units:
                raise ValueError(f"RAW_UNITS_WITHOUT_SEGMENTER_MAPPING:{missing_units}")
            aligned.append({"sample_id": row["sample_id"], "split": split,
                            "text_sha256": sha256_text(row["text"]), "status": "EXACT",
                            "segmenter_text": segmented, "segmenter_text_sha256": sha256_text(segmented),
                            "segmenter_word_count": len(words), "character_map": maps,
                            "tone_relocation_character_changes": relocations})
        except ValueError as error:
            aligned.append({"sample_id": row["sample_id"], "split": split,
                            "text_sha256": sha256_text(row["text"]), "status": "UNREPRESENTABLE",
                            "reason": str(error), "segmenter_text": segmented,
                            "segmenter_text_sha256": sha256_text(segmented)})
    return aligned


def audit_gold_round_trip(splits: dict, alignment_status: dict[str, str]) -> list[dict]:
    """Attach gold only after the text-only segmentation/map artifacts are frozen."""
    result = []
    for split, rows in splits.items():
        for row in rows:
            try:
                if alignment_status.get(row["sample_id"]) != "EXACT":
                    raise ValueError("TEXT_ALIGNMENT_UNREPRESENTABLE")
                raw_alignment = align_text(row["text"])
                tags = encode_gold(raw_alignment, row["spans"])
                decoded, repairs = decode_tags(raw_alignment, tags)
                expected = {(span["start"], span["end"], span["label"]) for span in row["spans"]}
                actual = {(span.start, span.end, span.label) for span in decoded}
                if repairs or actual != expected or any(
                        span.text != row["text"][span.start:span.end] for span in decoded):
                    raise ValueError("GOLD_RAW_OFFSET_ROUND_TRIP_FAILED")
                status, reason = "EXACT", None
            except ValueError as error:
                status, reason = "UNREPRESENTABLE", str(error)
                decoded = []
            result.append({"sample_id": row["sample_id"], "split": split, "status": status,
                           "reason": reason, "gold_span_count": len(decoded)})
    return result


def run(output_directory: Path, java: str | None = None) -> dict:
    validate_output_directory(output_directory, "prepare")
    if output_directory.exists():
        raise FileExistsError(output_directory)
    if file_hash(CORPUS / "manifest.json") != CORPUS_MANIFEST_SHA256:
        raise ValueError("CORPUS_MANIFEST_PIN_MISMATCH")
    manifest, splits = load_corpus(CORPUS)
    for name, expected in EXPECTED_COUNTS.items():
        if len(splits[name]) != expected:
            raise ValueError(f"CORPUS_COUNT_MISMATCH:{name}")
    lock = json.loads(RESOURCE_LOCK.read_text(encoding="utf-8"))
    segmenter_directory, jar = verify_segmenter_assets(lock)
    java = java or shutil.which("java")
    if not java:
        raise RuntimeError("JAVA_NOT_FOUND; activate the declared D runtime or specify --java")

    output_directory.mkdir(parents=True)
    text_only = {name: [{"sample_id": row["sample_id"], "text": row["text"]} for row in rows]
                 for name, rows in splits.items()}
    segmenter_outputs = {}
    alignment_rows = []
    for split in ("train", "dev"):
        texts = [row["text"] for row in text_only[split]]
        segmenter_outputs[split] = run_segmenter(java, jar, segmenter_directory, texts,
                                                 output_directory, split)
        alignment_rows.extend(audit_text_alignment(splits[split], split, segmenter_outputs[split]))

    # Persist and hash text-only maps before this function reads gold spans for QA.
    text_alignment_path = output_directory / "text_only_character_alignment.jsonl"
    write_jsonl(text_alignment_path, alignment_rows)
    text_alignment_sha256 = file_hash(text_alignment_path)
    alignment_status = {row["sample_id"]: row["status"] for row in alignment_rows}
    gold_qa = audit_gold_round_trip(splits, alignment_status)
    write_jsonl(output_directory / "supervised_raw_span_round_trip_qa.jsonl", gold_qa)

    old_rejected_ids = set()
    if PREVIOUS_AUDIT.is_file():
        previous = json.loads(PREVIOUS_AUDIT.read_text(encoding="utf-8"))
        old_rejected_ids = {row["sample_id"] for row in previous.get("rejected", [])}
    current_exact_ids = {row["sample_id"] for row in alignment_rows if row["status"] == "EXACT"}
    current_rejected = [row for row in alignment_rows if row["status"] != "EXACT"]
    gold_counts = Counter(row["status"] for row in gold_qa)
    tone_changes = [change for row in alignment_rows
                    for change in row.get("tone_relocation_character_changes", [])]
    previous_unresolved = sorted(old_rejected_ids - current_exact_ids)
    previous_rows = {row["sample_id"]: row for row in read_jsonl(PREVIOUS_SEGMENTATION)} if PREVIOUS_SEGMENTATION.is_file() else {}
    current_by_id = {row["sample_id"]: row for row in alignment_rows}
    previous_segmentation_mismatches = []
    for sample_id, previous_row in previous_rows.items():
        if previous_row["status"] == "EXACT":
            previous_text = previous_row["alignment"]["prepared_text"]
        else:
            diagnostic = previous_row.get("segmentation_diagnostic", {})
            sentences = diagnostic.get("segmented_sentences", [])
            previous_text = " ".join(sentences)
        previous_text = " ".join(previous_text.split())
        current_text = current_by_id.get(sample_id, {}).get("segmenter_text", "")
        if previous_text != current_text:
            previous_segmentation_mismatches.append(sample_id)
    previous_segmentation_comparison_available = len(previous_rows) == sum(EXPECTED_COUNTS.values())
    result = {"purpose": "actual_vncorenlp_character_offset_audit_only",
              "corpus_manifest_sha256": file_hash(CORPUS / "manifest.json"),
              "resource_lock_sha256": file_hash(RESOURCE_LOCK),
              "segmenter_jar_sha256": file_hash(jar),
              "segmenter_asset_hashes_verified": True,
              "java_executable": java,
              "java_version": subprocess.run([java, "-version"], capture_output=True, text=True,
                                               encoding="utf-8", errors="replace").stderr.strip(),
              "split_counts": {name: len(splits[name]) for name in splits},
              "text_alignment": {name: dict(Counter(row["status"] for row in alignment_rows if row["split"] == name))
                                 for name in splits},
              "gold_raw_span_round_trip": dict(gold_counts),
              "previously_rejected_count": len(old_rejected_ids),
              "previously_rejected_recovered": len(old_rejected_ids & current_exact_ids),
              "previously_rejected_unresolved": previous_unresolved,
              "previous_processor_segmentation_rows": len(previous_rows),
              "previous_processor_segmentation_match_count": (len(previous_rows) - len(previous_segmentation_mismatches)
                                                              if previous_segmentation_comparison_available else None),
              "previous_processor_segmentation_mismatches": (previous_segmentation_mismatches
                                                              if previous_segmentation_comparison_available else None),
              "tone_relocation_character_change_count": len(tone_changes),
              "samples_with_tone_relocation": sum(bool(row.get("tone_relocation_character_changes"))
                                                   for row in alignment_rows),
              "unrepresentable_sample_ids": [row["sample_id"] for row in current_rejected],
              "text_only_alignment_sha256": text_alignment_sha256,
              "gold_qa_started_after_alignment_hash": True,
              "training_performed": False, "prediction_produced": False,
              "test100_read_or_used": False, "colab_used": False,
              "code_sha256": {"scripts/38_audit_phobert_tone_alignment.py": file_hash(Path(__file__).resolve()),
                              "src/modeling/alignment.py": file_hash(ROOT / "src/modeling/alignment.py")}}
    result["status"] = ("ALIGNMENT_AND_GOLD_OFFSET_AUDIT_PASS" if not current_rejected and
                        gold_counts == {"EXACT": sum(EXPECTED_COUNTS.values())} and
                        not previous_unresolved and
                        (not previous_segmentation_comparison_available or not previous_segmentation_mismatches)
                        else "ALIGNMENT_AUDIT_INCOMPLETE")
    write_json(output_directory / "alignment_audit_manifest.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--java", help="Java executable; defaults to the active environment's java")
    args = parser.parse_args()
    result = run(args.output_dir.resolve(), args.java)
    print(json.dumps({key: result[key] for key in (
        "status", "text_alignment", "gold_raw_span_round_trip", "previously_rejected_count",
        "previously_rejected_recovered", "previously_rejected_unresolved",
        "previous_processor_segmentation_rows", "previous_processor_segmentation_match_count",
        "previous_processor_segmentation_mismatches",
        "tone_relocation_character_change_count", "samples_with_tone_relocation")}, ensure_ascii=False))
    if result["status"] != "ALIGNMENT_AND_GOLD_OFFSET_AUDIT_PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
