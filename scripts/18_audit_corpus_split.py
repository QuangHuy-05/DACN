"""Audit corpus splits for leakage, group overlap, and near-duplicates.

Follows Protocol v1.0 and Sprint 3 Execution Plan (C2.6):
- Verifies sample_id uniqueness across splits.
- Verifies zero group_id overlap across train, dev, and test.
- Checks exact text hash collisions.
- Scans cross-split near duplicates (SequenceMatcher >= 0.85) to produce review queue.
- Verifies zero overlap with benchmark 01-07 reserved groups.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import json
import random
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = ROOT / "data/processed/benchmark"


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_text(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.casefold()).replace("đ", "d")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join(s.split())


def audit_splits(
    train_records: list[dict],
    dev_records: list[dict],
    test_records: list[dict],
    reserved_benchmark_groups: set[str],
    near_dup_threshold: float = 0.85,
) -> dict:
    splits = {
        "train": train_records,
        "dev": dev_records,
        "test": test_records,
    }

    # 1. Sample ID uniqueness
    all_ids = []
    for sp_name, recs in splits.items():
        for r in recs:
            sid = r["sample_id"]
            all_ids.append(sid)

    id_counts = Counter(all_ids)
    duplicate_ids = [sid for sid, c in id_counts.items() if c > 1]
    missing_groups = [r["sample_id"] for recs in splits.values() for r in recs if not r.get("source_group")]

    # 2. Group overlap
    groups_by_split = {
        sp_name: {r["source_group"] for r in recs if r.get("source_group")}
        for sp_name, recs in splits.items()
    }

    group_collisions = {}
    split_names = list(splits.keys())
    for i in range(len(split_names)):
        for j in range(i + 1, len(split_names)):
            s1, s2 = split_names[i], split_names[j]
            overlap = groups_by_split[s1] & groups_by_split[s2]
            if overlap:
                group_collisions[f"{s1}_vs_{s2}"] = sorted(overlap)

    # 3. Benchmark group leakage into train/dev
    train_dev_groups = groups_by_split["train"] | groups_by_split["dev"]
    benchmark_leakage = train_dev_groups & reserved_benchmark_groups

    # 4. Exact text collision
    text_to_splits = defaultdict(set)
    normalized_to_splits = defaultdict(set)
    for sp_name, recs in splits.items():
        for r in recs:
            text_to_splits[r["text"]].add(sp_name)
            normalized_to_splits[normalize_text(r["text"])].add(sp_name)
    exact_text_collisions = {
        t: sorted(sps) for t, sps in text_to_splits.items() if len(sps) > 1
    }
    normalized_text_collisions = {
        t: sorted(sps) for t, sps in normalized_to_splits.items() if len(sps) > 1
    }

    # 5. Near duplicate scan across all split pairs. Similarity only nominates
    # a pair for human review; it is not proof of a shared address.
    near_duplicates = []
    for first, second in (("train", "dev"), ("train", "test"), ("dev", "test")):
        for a in splits[first]:
            a_n = normalize_text(a["text"])
            for b in splits[second]:
                b_n = normalize_text(b["text"])
                # A large length gap cannot meet the similarity threshold.
                if abs(len(a_n) - len(b_n)) > max(len(a_n), len(b_n)) * (1.0 - near_dup_threshold):
                    continue
                ratio = SequenceMatcher(None, a_n, b_n).ratio()
                if ratio >= near_dup_threshold:
                    near_duplicates.append({
                        "first_split": first,
                        "first_sample_id": a["sample_id"],
                        "first_text": a["text"],
                        "second_split": second,
                        "second_sample_id": b["sample_id"],
                        "second_text": b["text"],
                        "similarity": round(ratio, 4),
                    })

    status = "AUDIT_PASS"
    if duplicate_ids or missing_groups or group_collisions or benchmark_leakage or exact_text_collisions or normalized_text_collisions:
        status = "BLOCKED_LEAKAGE"
    elif near_duplicates:
        status = "NEEDS_NEAR_DUP_REVIEW"

    return {
        "status": status,
        "sample_counts": {sp: len(recs) for sp, recs in splits.items()},
        "group_counts": {sp: len(grps) for sp, grps in groups_by_split.items()},
        "duplicate_sample_ids": duplicate_ids,
        "missing_source_group_ids": missing_groups,
        "group_collisions": group_collisions,
        "benchmark_leakage_groups": sorted(benchmark_leakage),
        "exact_text_collisions_count": len(exact_text_collisions),
        "exact_text_collisions": exact_text_collisions,
        "normalized_text_collisions": normalized_text_collisions,
        "near_duplicates_count": len(near_duplicates),
        "near_duplicates_review_queue": near_duplicates,
    }


def read_queue(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"sample_id", "text", "group_id", "planned_role"}
        if required - set(reader.fieldnames or ()):
            raise ValueError(f"{path}: missing {sorted(required - set(reader.fieldnames or ()))}")
        return list(reader)


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_audit(output_dir: Path, report: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    near = report["near_duplicates_review_queue"]
    with (output_dir / "near_duplicate_review_queue.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        fields = ("first_split", "first_sample_id", "first_text", "second_split",
                  "second_sample_id", "second_text", "similarity", "decision", "reason", "reviewer")
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(near)
    (output_dir / "split_audit_report.json").write_text(
        json.dumps({k: v for k, v in report.items() if k != "near_duplicates_review_queue"},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def apply_decisions(report: dict, decisions_path: Path | None) -> dict:
    if decisions_path is None:
        return report
    decisions = read_queue_for_decisions(decisions_path)
    expected = {(row["first_sample_id"], row["second_sample_id"])
                for row in report["near_duplicates_review_queue"]}
    actual = {(row["first_sample_id"], row["second_sample_id"]) for row in decisions}
    if expected != actual or len(decisions) != len(actual):
        raise ValueError("Decision CSV pairs differ from current near-duplicate queue")
    pending = []
    same_site = []
    for row in decisions:
        pair = (row["first_sample_id"], row["second_sample_id"])
        if row["decision"] == "same_site":
            same_site.append(pair)
        elif row["decision"] != "distinct" or not row["reason"].strip() or not row["reviewer"].strip():
            pending.append(pair)
    report["near_duplicate_decisions_sha256"] = file_hash(decisions_path)
    report["near_duplicate_pending_pairs"] = pending
    report["near_duplicate_same_site_pairs"] = same_site
    if same_site or pending:
        report["status"] = "BLOCKED_NEAR_DUP_DECISIONS"
    elif report["status"] == "NEEDS_NEAR_DUP_REVIEW":
        report["status"] = "AUDIT_PASS_WITH_HUMAN_NEAR_DUP_REVIEW"
    return report


def read_queue_for_decisions(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"first_sample_id", "second_sample_id", "decision", "reason", "reviewer"}
        if required - set(reader.fieldnames or ()):
            raise ValueError(f"Decision CSV missing {sorted(required - set(reader.fieldnames or ()))}")
        return list(reader)


def preflight(output_dir: Path, decisions_path: Path | None = None) -> dict:
    annotation_dir = ROOT / "data/interim/annotation/sprint03"
    snapshot = json.loads((ROOT / "docs/sprints/sprint_03/s3_04_input_snapshot_v1.json").read_text(encoding="utf-8"))
    drift = [relative for relative, entry in snapshot["inputs"].items()
             if not (ROOT / relative).is_file() or file_hash(ROOT / relative) != entry["sha256"]]
    if drift:
        raise ValueError(f"BLOCKED_INPUT_DRIFT: {drift}")
    queue01_path = annotation_dir / "annotation_queue_batch01.csv"
    queue02_path = annotation_dir / "annotation_queue_batch02_train_dev.csv"
    queue01, queue02 = read_queue(queue01_path), read_queue(queue02_path)
    batch_manifest = json.loads((annotation_dir / "annotation_batch02_manifest.json").read_text(encoding="utf-8"))
    if file_hash(queue02_path) != batch_manifest["output_hashes"]["queue_csv"]:
        raise ValueError("BLOCKED_INPUT_DRIFT: batch02 queue hash")
    batch_import_path = annotation_dir / "label_studio_batch02_import.json"
    if file_hash(batch_import_path) != batch_manifest["output_hashes"]["label_studio_import_json"]:
        raise ValueError("BLOCKED_INPUT_DRIFT: batch02 import hash")
    hold = json.loads((annotation_dir / "test_hold_manifest_v1.json").read_text(encoding="utf-8"))
    frozen = {row["sample_id"]: row for row in hold["samples"]}
    pilot = [row for row in queue01 if row["planned_role"] == "pilot_train_pool"]
    test = [row for row in queue01 if row["planned_role"] == "frozen_benchmark_test_hold"]
    if len(pilot) != 68 or len(test) != 100 or {row["sample_id"] for row in test} != set(frozen):
        raise ValueError("Pilot or frozen test ID list changed")
    for row in test:
        expected = frozen[row["sample_id"]]
        text_hash = hashlib.sha256(row["text"].encode("utf-8")).hexdigest()
        if (text_hash != expected["text_sha256"] or row["group_id"] != expected["group_id"] or
                row["source_dataset"] != expected["source_dataset"]):
            raise ValueError(f"Frozen test text/group changed: {row['sample_id']}")
    if Counter(row["source_dataset"] for row in test) != Counter(hold["strata_counts"]):
        raise ValueError("Frozen test source quotas changed")

    for import_path, expected_rows in ((batch_import_path, queue02),
                                       (annotation_dir / "label_studio_test_benchmark_t0_import.json", test)):
        imported = json.loads(import_path.read_text(encoding="utf-8"))
        if not isinstance(imported, list) or len(imported) != len(expected_rows):
            raise ValueError(f"Import task count changed: {import_path}")
        expected_by_id = {row["sample_id"]: row["text"] for row in expected_rows}
        seen_import_ids = set()
        for task in imported:
            data = task.get("data") if isinstance(task, dict) else None
            if (not isinstance(data, dict) or set(data) != {"sample_id", "text"} or
                    data["sample_id"] in seen_import_ids or
                    expected_by_id.get(data["sample_id"]) != data["text"]):
                raise ValueError(f"Import task changed or exposes metadata: {import_path}")
            seen_import_ids.add(data["sample_id"])

    pilot_groups = sorted({row["group_id"] for row in pilot})
    random.Random(1042).shuffle(pilot_groups)
    pilot_splits = {group: "dev" if index % 5 == 0 else "train"
                    for index, group in enumerate(pilot_groups)}
    assignments = [(row, pilot_splits[row["group_id"]], "pilot_gold_v1") for row in pilot]
    for row in queue02:
        if row.get("planned_split") not in {"train", "dev"}:
            raise ValueError(f"Invalid batch02 split: {row['sample_id']}")
        assignments.append((row, row["planned_split"], "batch02_candidate"))
    output_dir.mkdir(parents=True, exist_ok=True)
    assignment_path = output_dir / "train_dev_split_assignments.csv"
    with assignment_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("sample_id", "split", "source_group", "origin"))
        writer.writeheader()
        for row, split, origin in assignments:
            writer.writerow({"sample_id": row["sample_id"], "split": split,
                             "source_group": row["group_id"], "origin": origin})

    def canonical(row: dict[str, str]) -> dict:
        return {"sample_id": row["sample_id"], "text": row["text"], "source_group": row["group_id"]}

    batch_builder = importlib.import_module("scripts.16_prepare_t0_corpus_batch")
    reserved = batch_builder.get_reserved_benchmark_groups()
    report = audit_splits(
        [canonical(row) for row, split, _ in assignments if split == "train"],
        [canonical(row) for row, split, _ in assignments if split == "dev"],
        [canonical(row) for row in test], reserved,
    )
    # Synthetic children can point to a source parent that is intentionally not
    # another annotation task. Register that source parent with the same split.
    osm_rows = batch_builder.read_csv(batch_builder.OSM_OLD_PATH, ("ChuoiDiaChi", "SoNha", "TenDuong"))
    osm_by_line = {row["_source_line"]: row for row in osm_rows}
    osm_hash = file_hash(batch_builder.OSM_OLD_PATH)
    source_parents = {}
    orphan_parents = []
    for row in queue02:
        parent_id = row.get("parent_sample_id")
        if not parent_id:
            continue
        expected_id = f"osm_row_{row['source_row']}"
        source_row = osm_by_line.get(row["source_row"])
        if (parent_id != expected_id or source_row is None or
                batch_builder.row_group(source_row) != row["group_id"] or
                row["source_file_sha256"] != osm_hash):
            orphan_parents.append(row["sample_id"])
            continue
        parent = {
            "parent_sample_id": parent_id,
            "source_ref": row["source_ref"],
            "source_row": row["source_row"],
            "source_group": row["group_id"],
            "split": row["planned_split"],
            "source_text_sha256": hashlib.sha256(source_row["ChuoiDiaChi"].encode("utf-8")).hexdigest(),
            "annotation_status": "SOURCE_PARENT_NOT_ANNOTATED",
        }
        if parent_id in source_parents and source_parents[parent_id] != parent:
            orphan_parents.append(row["sample_id"])
        source_parents[parent_id] = parent
    parent_path = output_dir / "source_parent_manifest.csv"
    with parent_path.open("w", encoding="utf-8-sig", newline="") as stream:
        fields = ("parent_sample_id", "source_ref", "source_row", "source_group", "split",
                  "source_text_sha256", "annotation_status")
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(source_parents[key] for key in sorted(source_parents))
    report["unresolved_parent_sample_ids"] = orphan_parents
    report["source_parent_count"] = len(source_parents)
    report["source_parent_manifest_sha256"] = file_hash(parent_path)
    report["assignment_sha256"] = file_hash(assignment_path)
    report["input_sha256"] = {str(queue01_path.relative_to(ROOT)): file_hash(queue01_path),
                              str(queue02_path.relative_to(ROOT)): file_hash(queue02_path)}
    if orphan_parents:
        report["status"] = "BLOCKED_PARENT_REFERENCES"
    if decisions_path is not None and decisions_path.resolve() == (output_dir / "near_duplicate_review_queue.csv").resolve():
        raise ValueError("Copy the generated review queue to a separate decision CSV before editing")
    report = apply_decisions(report, decisions_path)
    write_audit(output_dir, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    pre = commands.add_parser("preflight", help="Audit frozen queues before annotation")
    pre.add_argument("--output-dir", type=Path, default=ROOT / "data/interim/annotation/sprint03/split_preflight_v1")
    pre.add_argument("--decisions", type=Path, help="Separate human decision CSV for near-duplicate pairs")
    final = commands.add_parser("audit", help="Audit three already approved canonical JSONL splits")
    for name in ("train", "dev", "test"):
        final.add_argument(f"--{name}", type=Path, required=True)
    final.add_argument("--output-dir", type=Path, required=True)
    final.add_argument("--decisions", type=Path)
    args = parser.parse_args()
    if args.command == "preflight":
        report = preflight(args.output_dir, decisions_path=args.decisions)
    else:
        reserved = importlib.import_module("scripts.16_prepare_t0_corpus_batch").get_reserved_benchmark_groups()
        report = audit_splits(read_jsonl(args.train), read_jsonl(args.dev),
                              read_jsonl(args.test), reserved)
        if args.decisions is not None and args.decisions.resolve() == (args.output_dir / "near_duplicate_review_queue.csv").resolve():
            raise ValueError("Use a separate decision CSV, not the generated review queue")
        report = apply_decisions(report, args.decisions)
        write_audit(args.output_dir, report)
    print(json.dumps({"status": report["status"], "sample_counts": report["sample_counts"],
                      "near_duplicates_count": report["near_duplicates_count"],
                      "unresolved_parent_count": len(report.get("unresolved_parent_sample_ids", []))},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
