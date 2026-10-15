"""Read-only integrity snapshots and modeling artifact audit."""

from collections import Counter
import json
from pathlib import Path
import subprocess

from src.evaluation.dev_runner import ROOT, STATUSES, file_hash, read_jsonl, write_json
from src.evaluation.schema import SpanModelOutput, CharacterSpan
from src.evaluation.span_scorer import validate_span_integrity
from src.modeling.datasets import load_corpus
from src.modeling.alignment import Alignment, decode_tags
from src.evaluation.span_features import Token
from src.modeling.labels import label_metadata, t1_target


def code_hashes() -> dict:
    names = set()
    for directory in ("src/modeling", "src/evaluation", "src/data"):
        names.update(p for p in (ROOT / directory).rglob("*.py"))
    names.update(p for p in (ROOT / "scripts").glob("*.py"))
    return {p.relative_to(ROOT).as_posix(): file_hash(p) for p in sorted(names)}


def git_state() -> dict:
    def run(args):
        result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else None
    return {"revision": run(["rev-parse", "HEAD"]), "dirty_status": run(["status", "--porcelain"]),
            "code_identity_policy": "actual file hashes include uncommitted source; HEAD alone is insufficient"}


def frozen_snapshot() -> dict:
    roots = [ROOT / "data/processed/annotation/sprint03/corpus_train_dev_v2",
             ROOT / "data/processed/gazetteer/s3_v1", ROOT / "data/processed/gazetteer/s3_v2"]
    roots.extend(p for p in (ROOT / "data/processed").rglob("baseline_v*") if p.is_dir())
    evaluation = ROOT / "data/processed/evaluation/sprint03"
    if evaluation.exists():
        roots.extend(p for p in evaluation.iterdir() if p.is_dir())
    files = set(p for root in roots if root.exists() for p in root.rglob("*") if p.is_file())
    # Never enumerate/read the external test-only or raw annotation project data.
    return {"policy": "approved train/dev and existing baseline/gazetteer/run bytes; test100 excluded",
            "files": {p.relative_to(ROOT).as_posix(): file_hash(p) for p in sorted(files)}}


def compare_snapshot(snapshot: dict) -> dict:
    changed = [name for name, digest in snapshot["files"].items() if not (ROOT / name).is_file() or file_hash(ROOT / name) != digest]
    return {"status": "FROZEN_HASH_PASS" if not changed else "BLOCKED_FROZEN_HASH", "checked_files": len(snapshot["files"]), "changed": changed}


def audit_run(run_dir: Path, corpus_dir: Path, enforce_release_pin: bool = True) -> dict:
    manifest, splits = load_corpus(corpus_dir, enforce_release_pin)
    issues = []
    result = {"purpose": "read_only_modeling_audit", "test100": "NOT_READ_NOT_USED"}
    config_path = run_dir / "model_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    if not any((run_dir / name).exists() for name in ("training_manifest.json", "run_manifest.json")):
        issues.append("NO_TRAINING_OR_INFERENCE_MANIFEST")
    if config.get("purpose") == "unit_or_integration_test" and config.get("pretrained") is not False:
        issues.append("FIXTURE_MISLABELED_PRETRAINED")
    for manifest_name, hashes_key in (("training_manifest.json", "output_sha256"), ("run_manifest.json", "output_sha256"), ("scoring_manifest.json", "output_sha256")):
        path = run_dir / manifest_name
        if not path.exists():
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        for name, digest in record.get(hashes_key, {}).items():
            target = run_dir / name
            if not target.is_file() or file_hash(target) != digest:
                issues.append("OUTPUT_HASH_MISMATCH:" + name)
        for name, digest in record.get("code_sha256", {}).items():
            if not (ROOT / name).is_file() or file_hash(ROOT / name) != digest:
                issues.append("CODE_HASH_MISMATCH:" + name)
        for name, digest in record.get("resource_sha256", {}).items():
            if not (ROOT / name).is_file() or file_hash(ROOT / name) != digest:
                issues.append("RESOURCE_HASH_MISMATCH:" + name)
        for name, entry in record.get("resources", {}).items():
            target = ROOT / entry["path"]
            if not target.is_file() or file_hash(target) != entry["sha256"]:
                issues.append("RESOURCE_HASH_MISMATCH:" + name)
        for name, digest in record.get("runtime", {}).get("code_sha256", {}).items():
            if not (ROOT / name).is_file() or file_hash(ROOT / name) != digest:
                issues.append("CODE_HASH_MISMATCH:" + name)
    prediction_path = run_dir / "predictions.jsonl"
    if prediction_path.exists():
        rows = read_jsonl(prediction_path)
        gold_by_id = {row["sample_id"]: row for row in splits["dev"]}
        if Counter(row["sample_id"] for row in rows) != Counter(gold_by_id.keys()):
            issues.append("DEV_ID_COUNT_MISMATCH")
        for row in rows:
            sid = row["sample_id"]
            if sid not in gold_by_id:
                continue
            output = SpanModelOutput(**{**row, "spans": [CharacterSpan(**s) for s in row["spans"]]})
            if output.status not in STATUSES:
                issues.append("INVALID_PREDICTION_STATUS:" + sid)
            if output.raw_text != gold_by_id[sid]["text"] or validate_span_integrity(output.spans, output.raw_text) or any(s.text != output.raw_text[s.start:s.end] for s in output.spans):
                issues.append("INVALID_RAW_OFFSETS:" + sid)
        result["predictions"] = {"count": len(rows), "status_counts": dict(Counter(row["status"] for row in rows))}
        score_path = run_dir / "scoring_manifest.json"
        if score_path.exists():
            score = json.loads(score_path.read_text(encoding="utf-8"))
            if score["prediction_sha256"] != file_hash(prediction_path):
                issues.append("PREDICTION_TAMPERED")
            if set(score["t1_declared_exception_excluded_ids"]) != set(manifest["evaluation_exclusions"]["t1"]) & set(gold_by_id):
                issues.append("T1_EXCEPTION_MASK_MISMATCH")
    for path in (run_dir / "checkpoints").glob("*.pt.json") if (run_dir / "checkpoints").exists() else []:
        meta = json.loads(path.read_text(encoding="utf-8"))
        checkpoint = path.with_suffix("")
        if not checkpoint.exists() or file_hash(checkpoint) != meta["checkpoint_sha256"]:
            issues.append("CHECKPOINT_TAMPERED:" + checkpoint.name)
    result.update(status="AUDIT_PASS" if not issues else "AUDIT_FAIL", issues=issues,
                  corpus_manifest_sha256=file_hash(corpus_dir / "manifest.json"))
    return result


def audit_prepared(prepared_dir: Path, corpus_dir: Path) -> dict:
    manifest, splits = load_corpus(corpus_dir)
    prepared = json.loads((prepared_dir / "input_manifest.json").read_text(encoding="utf-8"))
    issues = []
    if prepared["corpus_manifest_sha256"] != file_hash(corpus_dir / "manifest.json"):
        issues.append("CORPUS_VERSION_CHANGED")
    for name, digest in prepared["outputs"].items():
        if not (prepared_dir / name).is_file() or file_hash(prepared_dir / name) != digest:
            issues.append("DERIVATIVE_HASH_MISMATCH:" + name)
    for name, digest in prepared.get("code_sha256", {}).items():
        if not (ROOT / name).is_file() or file_hash(ROOT / name) != digest:
            issues.append("PREPARATION_CODE_CHANGED:" + name)
    if prepared["processor_code_sha256"] != file_hash(ROOT / "src/modeling/alignment.py"):
        issues.append("PROCESSOR_CODE_CHANGED")
    if json.loads((prepared_dir / "label_map.json").read_text(encoding="utf-8")) != label_metadata():
        issues.append("LABEL_MAP_MISMATCH")
    counts = {}
    for name in ("raw", "deepparse_surface", "phobert"):
        for split, golds in splits.items():
            path = prepared_dir / f"{name}_{split}.jsonl"
            if not path.exists():
                continue
            rows = read_jsonl(path)
            if [row["sample_id"] for row in rows] != [row["sample_id"] for row in golds]:
                issues.append("DERIVATIVE_ID_OR_ORDER_MISMATCH:" + path.name)
                continue
            exact = eligible = 0
            for row, gold in zip(rows, golds):
                if row["status"] != "EXACT":
                    issues.append("UNREPRESENTABLE:" + row["sample_id"])
                    continue
                value = row["alignment"]
                alignment = Alignment(**{key: val for key, val in value.items() if key not in ("text_sha256", "prediction_unit_mask", "units")},
                                      units=[Token(**unit) for unit in value["units"]])
                spans, _ = decode_tags(alignment, row["tags"])
                if alignment.raw_text != gold["text"] or {(s.start, s.end, s.label) for s in spans} != {(s["start"], s["end"], s["label"]) for s in gold["spans"]}:
                    issues.append("RAW_SPAN_ROUND_TRIP_MISMATCH:" + row["sample_id"])
                target, mask = t1_target(gold, manifest)
                if (row["t1_target"], row["t1_mask"]) != (target, mask):
                    issues.append("T1_SUPERVISION_MASK_MISMATCH:" + row["sample_id"])
                exact += 1
                eligible += int(mask)
            counts[path.name] = {"samples": len(rows), "exact": exact, "t1_eligible": eligible}
    provenance = read_jsonl(prepared_dir / "provenance_sidecar.jsonl")
    expected_coverage = json.loads((corpus_dir / "coverage.json").read_text(encoding="utf-8"))
    for split in splits:
        kinds = dict(Counter(row["source_kind"] for row in provenance if row["split"] == split))
        if kinds != expected_coverage[split]["source_kind"]:
            issues.append("PROVENANCE_COVERAGE_MISMATCH:" + split)
    return {"status": "ALIGNMENT_AUDIT_PASS" if not issues else "ALIGNMENT_AUDIT_FAIL", "counts": counts,
            "issues": issues, "test100": "NOT_READ_NOT_USED", "purpose": "preparation_not_model_experiment"}
