"""Hash-gated train/dev data and immutable, versioned model-data derivatives."""

from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

from src.evaluation.dev_runner import ROOT, check_release_file, file_hash, load_dev_input, read_jsonl, write_json, write_jsonl
from src.modeling.alignment import align_text, encode_gold, DeepparseProcessor
from src.modeling.labels import label_metadata, t1_target
from src.evaluation.schema import SPAN11_LABELS

CORPUS_MANIFEST_SHA256 = "9c91b77fa220e41b1b1067e5e99b216b7b4b2176181674b340f16dec134947bf"


def load_corpus(corpus_dir: Path, enforce_release_pin: bool = True) -> tuple[dict, dict]:
    manifest_path = corpus_dir / "manifest.json"
    if enforce_release_pin and file_hash(manifest_path) != CORPUS_MANIFEST_SHA256:
        raise ValueError("BLOCKED_INPUT_HASH: corpus manifest changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name, digest in manifest["output_sha256"].items():
        if not (corpus_dir / name).is_file() or file_hash(corpus_dir / name) != digest:
            raise ValueError("BLOCKED_INPUT_HASH:" + name)
    rows = {}
    for split in ("train", "dev"):
        check_release_file(corpus_dir / f"{split}.jsonl", manifest_path, f"{split}.jsonl")
        rows[split] = read_jsonl(corpus_dir / f"{split}.jsonl")
        if len(rows[split]) != manifest["sample_counts"][split]:
            raise ValueError("Corpus count mismatch")
    inputs = load_dev_input(corpus_dir / "dev_input.jsonl", manifest_path)
    if inputs != [{"sample_id": row["sample_id"], "text": row["text"]} for row in rows["dev"]]:
        raise ValueError("Dev inference text/identity mismatch")
    ids = [row["sample_id"] for split in rows.values() for row in split]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate ID or split overlap")
    return manifest, rows


def prepare_data(corpus_dir: Path, output_dir: Path, phobert_processor=None) -> dict:
    if output_dir.exists():
        raise FileExistsError(output_dir)
    manifest, splits = load_corpus(corpus_dir)
    trace_path = ROOT / "data/interim/annotation/sprint03/reannotation_v2_release1/trace.jsonl"
    generation = json.loads(trace_path.with_name("generation_manifest.json").read_text(encoding="utf-8"))
    if file_hash(trace_path) != generation["output_sha256"]["trace.jsonl"]:
        raise ValueError("PROVENANCE_TRACE_CHANGED")
    trace = {row["sample_id"]: row for row in read_jsonl(trace_path)}
    queue_relative = "data/interim/annotation/sprint03/annotation_queue_batch02_train_dev.csv"
    queue_path = ROOT / queue_relative
    if file_hash(queue_path) != manifest["input_sha256"][queue_relative]:
        raise ValueError("PROVENANCE_QUEUE_CHANGED")
    with queue_path.open(encoding="utf-8-sig", newline="") as stream:
        queue = {row["sample_id"]: row for row in csv.DictReader(stream)}
    provenance = []
    for split, rows in splits.items():
        for row in rows:
            item = trace[row["sample_id"]]
            evidence = item["evidence"]
            derivation = evidence.get("derivation", "not_recorded")
            kind = "observed" if derivation.startswith("observed") else "derived" if derivation.startswith("derived") else "synthetic" if derivation.startswith(("synthetic", "controlled_synthetic")) else "unverified_provenance"
            if item["group_id"] != row["source_group"]:
                raise ValueError("PROVENANCE_GROUP_MISMATCH")
            provenance.append({"sample_id": row["sample_id"], "split": split, "source_group": row["source_group"],
                "text_sha256": hashlib.sha256(row["text"].encode("utf-8")).hexdigest(),
                "source_kind": kind, "derivation": derivation, "stratum": item["stratum"],
                "source_dataset": queue.get(row["sample_id"], {}).get("source_dataset", item["stratum"]),
                "source_ref": evidence.get("source_ref"), "source_row": evidence.get("source_row"),
                "source_file_sha256": evidence.get("source_file_sha256"), "noise_type": "not_recorded",
                "feature_permission": "sidecar_only_never_inference_or_training_features"})
    output_dir.mkdir(parents=True)
    processors = {"raw": align_text, "deepparse_surface": DeepparseProcessor().align_text}
    if phobert_processor is not None:
        processors["phobert"] = phobert_processor.align_text
    report, diagnostics = {}, []
    for name, processor in processors.items():
        report[name] = {}
        for split, rows in splits.items():
            converted, statuses, gold_counts, represented = [], Counter(), Counter(), Counter()
            eligible = 0
            for row in rows:
                for span in row["spans"]:
                    gold_counts[span["label"]] += 1
                target, mask = t1_target(row, manifest)
                eligible += int(mask)
                try:
                    alignment = processor(row["text"])
                    tags = encode_gold(alignment, row["spans"])
                    value = {"sample_id": row["sample_id"], "split": split,
                             "alignment": alignment.to_dict(), "tags": tags, "t1_target": target,
                             "t1_mask": mask, "status": "EXACT"}
                    for span in row["spans"]:
                        represented[span["label"]] += 1
                except ValueError as exc:
                    value = {"sample_id": row["sample_id"], "split": split,
                             "status": "UNREPRESENTABLE", "reason": str(exc)}
                statuses[value["status"]] += 1
                diagnostics.append({"processor": name, **value})
                converted.append(value)
            write_jsonl(output_dir / f"{name}_{split}.jsonl", converted)
            report[name][split] = {"sample_count": len(rows), "statuses": dict(statuses),
                                  "gold_spans": {label: gold_counts[label] for label in SPAN11_LABELS},
                                  "represented_spans": {label: represented[label] for label in SPAN11_LABELS},
                                  "unrepresentable_spans": {label: gold_counts[label] - represented[label] for label in SPAN11_LABELS},
                                  "t1_eligible": eligible}
    report["phobert_integration"] = "INTEGRATION_PENDING_RESOURCE"
    if phobert_processor is not None:
        if not getattr(phobert_processor, "resource_evidence", None):
            report["phobert_integration"] = "FIXTURE_PROCESSOR_ONLY_NOT_PRETRAINED_INTEGRATION"
        else:
            report["phobert_integration"] = "INTEGRATION_VERIFIED" if all(row["statuses"] == {"EXACT": row["sample_count"]} for row in report["phobert"].values()) else "INTEGRATION_PENDING_ALIGNMENT"
            report["phobert_resource_evidence"] = phobert_processor.resource_evidence
    report["deepparse_integration"] = "PREPARATION_ONLY_NATIVE_LIBRARY_PENDING"
    write_json(output_dir / "alignment_report.json", report)
    write_jsonl(output_dir / "alignment_diagnostics.jsonl", diagnostics)
    write_json(output_dir / "label_map.json", label_metadata())
    label_hash = file_hash(output_dir / "label_map.json")
    for item in provenance:
        item["label_map_sha256"] = label_hash
        item["processor_code_sha256"] = file_hash(Path(__file__).with_name("alignment.py"))
    write_jsonl(output_dir / "provenance_sidecar.jsonl", provenance)
    outputs = {p.name: file_hash(p) for p in output_dir.iterdir() if p.is_file()}
    write_json(output_dir / "input_manifest.json", {
        "status": "PREPARED" if all(v["statuses"] == {"EXACT": v["sample_count"]}
            for n in processors for v in report[n].values()) else "BLOCKED_ALIGNMENT",
        "purpose": "model_data_preparation_not_model_predictions", "test": "NOT_READ_NOT_USED",
        "corpus_manifest_sha256": file_hash(corpus_dir / "manifest.json"),
        "input_sha256": {name: file_hash(corpus_dir / name) for name in ("train.jsonl", "dev.jsonl", "dev_input.jsonl")},
        "evaluation_exclusions": manifest.get("evaluation_exclusions", {}), "outputs": outputs,
        "provenance_input_sha256": {trace_path.relative_to(ROOT).as_posix(): file_hash(trace_path), queue_relative: file_hash(queue_path)},
        "code_sha256": {Path(__file__).relative_to(ROOT).as_posix(): file_hash(Path(__file__)),
            "src/modeling/alignment.py": file_hash(Path(__file__).with_name("alignment.py")),
            "src/modeling/labels.py": file_hash(Path(__file__).with_name("labels.py")),
            "src/evaluation/span_features.py": file_hash(ROOT / "src/evaluation/span_features.py")},
        "processor_code_sha256": file_hash(Path(__file__).with_name("alignment.py"))})
    return report
