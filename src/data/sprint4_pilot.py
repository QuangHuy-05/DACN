"""Prepare source-review candidates, with gates before manual annotation.

This module never assigns gold labels, changes a released split, or trains models.
"""
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from hashlib import sha256
from pathlib import Path
import json
import re
import unicodedata


def file_hash(path):
    digest = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def confined_path(root, relative):
    path = (Path(root) / relative).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError("PATH_OUTSIDE_PROJECT")
    return path


def verify_bound_file(root, relative, expected_hash):
    path = confined_path(root, relative)
    if not path.is_file() or file_hash(path) != expected_hash:
        raise ValueError(f"SOURCE_HASH_MISMATCH: {relative}")
    return path


def validate_candidate(root, sample, sources):
    required = {"sample_id", "text", "source_key", "document_group", "site_group",
                "source_block", "start", "end", "extraction_method", "locator"}
    if required - sample.keys():
        raise ValueError("MISSING_CANDIDATE_FIELDS")
    if not sample["text"].strip() or not sample["site_group"] or not sample["document_group"]:
        raise ValueError("EMPTY_TEXT_OR_GROUP")
    start, end = sample["start"], sample["end"]
    block = sample["source_block"]
    if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= len(block):
        raise ValueError("INVALID_SOURCE_OFFSETS")
    if block[start:end] != sample["text"]:
        raise ValueError("SOURCE_SUBSTRING_MISMATCH")
    source = sources[sample["source_key"]]
    verify_bound_file(root, source["path"], source["sha256"])
    method = sample["extraction_method"]
    if method == "HTML_LITERAL_SUBSTRING":
        text_path = verify_bound_file(root, source["text_path"], source["text_sha256"])
        if block not in text_path.read_text(encoding="utf-8-sig"):
            raise ValueError("HTML_LITERAL_NOT_FOUND")
    elif method == "AI_VISUAL_TRANSCRIPTION":
        locator = sample["locator"]
        verify_bound_file(root, locator["image_path"], locator["image_sha256"])
        if not isinstance(locator.get("page"), int) or locator["page"] < 1:
            raise ValueError("INVALID_PDF_PAGE")
        bounds = locator.get("bbox_normalized", [])
        if len(bounds) != 4 or not 0 <= bounds[0] < bounds[2] <= 1 or not 0 <= bounds[1] < bounds[3] <= 1:
            raise ValueError("INVALID_IMAGE_BOUNDS")
        if sample.get("transcription_transform") != "VISUAL_LINES_JOINED_WITH_SINGLE_SPACE":
            raise ValueError("TRANSCRIPTION_TRANSFORM_UNDECLARED")
    else:
        raise ValueError("UNSUPPORTED_EXTRACTION_METHOD")


def connected_groups(samples):
    """Link both document and physical site; old/new variants cannot cross splits."""
    parents = list(range(len(samples)))
    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index
    seen = {}
    for index, sample in enumerate(samples):
        for field in ("document_group", "site_group"):
            key = (field, sample[field])
            if key in seen:
                parents[find(index)] = find(seen[key])
            else:
                seen[key] = index
    members = {}
    for index, sample in enumerate(samples):
        members.setdefault(find(index), []).append(sample["sample_id"])
    groups = {}
    for ids in members.values():
        group = "s4_component_" + sha256("|".join(sorted(ids)).encode()).hexdigest()[:16]
        for sample_id in ids:
            groups[sample_id] = group
    return groups


def annotation_ready(sample, source):
    # Neither public availability nor an AI transcription is a release approval.
    return (source.get("annotation_clearance") == "APPROVED"
            and source.get("local_research_clearance") == "APPROVED"
            and sample.get("source_text_review") == "HUMAN_VERIFIED"
            and sample.get("privacy_review") == "INSTITUTIONAL_NO_PERSONAL_ADDRESS"
            and sample.get("overlap_review") == "PASS")


def manual_tasks(samples, sources):
    return [{"data": {"sample_id": row["sample_id"], "text": row["text"]}}
            for row in samples if annotation_ready(row, sources[row["source_key"]])]


def normalize_text(text):
    text = unicodedata.normalize("NFKD", text.casefold().replace("đ", "d"))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text)).strip()


def duplicate_pairs(samples, previous=(), threshold=0.85):
    findings = []
    current = [(row["sample_id"], normalize_text(row["text"]), row["text"], "pilot_review") for row in samples]
    old = [(row["sample_id"], normalize_text(row["text"]), row["text"], row["split"]) for row in previous]
    for index, left in enumerate(current):
        for right in current[index + 1:] + old:
            if left[2] == right[2]:
                kind, score = "EXACT", 1.0
            elif left[1] == right[1]:
                kind, score = "NORMALIZED", 1.0
            else:
                lengths = len(left[1]), len(right[1])
                if sum(lengths) == 0 or 2 * min(lengths) / sum(lengths) < threshold:
                    continue
                score = SequenceMatcher(None, left[1], right[1], autojunk=False).ratio()
                if score < threshold:
                    continue
                kind = "NEAR"
            findings.append({"sample_id": left[0], "other_id": right[0], "other_split": right[3],
                             "kind": kind, "similarity": round(score, 6)})
    return findings


def resolved_overlap_samples(findings, decisions):
    """Accept only documented distinct-location decisions for development pilots.

    Exact/normalized matches need a different review, so this gate cannot waive them.
    """
    by_pair = {(item["sample_id"], item["other_id"]): item for item in findings}
    reviewed = set()
    for decision in decisions:
        pair = (decision["sample_id"], decision["other_id"])
        finding = by_pair.get(pair)
        if (not finding or finding["kind"] != "NEAR" or finding["other_split"] not in {"train", "dev"}
                or decision.get("decision") != "DISTINCT_LOCATION_DEVELOPMENT_ONLY"
                or not decision.get("basis", "").strip()
                or decision.get("similarity") != finding["similarity"] or pair in reviewed):
            raise ValueError("INVALID_OVERLAP_DECISION")
        reviewed.add(pair)
    external = {}
    for pair, finding in by_pair.items():
        if finding["other_split"] != "pilot_review":
            external.setdefault(pair[0], set()).add(pair)
    return {sample_id for sample_id, pairs in external.items() if pairs <= reviewed}


def previous_texts(root, corpus_relative):
    """Read only ID/text for leakage detection; never export released gold fields."""
    corpus = confined_path(root, corpus_relative)
    manifest = json.loads((corpus / "manifest.json").read_text(encoding="utf-8-sig"))
    hashes = manifest["output_sha256"]
    registry_path = verify_bound_file(root, f"{corpus_relative}/identity_registry.jsonl", hashes["identity_registry.jsonl"])
    registry = {row["sample_id"]: row for row in
                (json.loads(line) for line in registry_path.read_text(encoding="utf-8-sig").splitlines())}
    result = []
    for split, name in (("train", "train.jsonl"), ("dev", "dev_input.jsonl"), ("test", "test_input.jsonl")):
        path = verify_bound_file(root, f"{corpus_relative}/{name}", hashes[name])
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            record = json.loads(line)
            item = registry[record["sample_id"]]
            if item["split"] != split or item["text_sha256"] != sha256(record["text"].encode()).hexdigest():
                raise ValueError("RELEASE_REGISTRY_TEXT_MISMATCH")
            result.append({"sample_id": record["sample_id"], "text": record["text"], "split": split})
    if len(result) != len(registry):
        raise ValueError("RELEASE_REGISTRY_COUNT_MISMATCH")
    return result


def frozen_integrity(root, snapshot_relative):
    snapshot = json.loads(confined_path(root, snapshot_relative).read_text(encoding="utf-8-sig"))
    changed = []
    for entry in snapshot["files"]:
        path = confined_path(root, entry["path"])
        if not path.is_file() or path.stat().st_size != entry["bytes"] or file_hash(path) != entry["sha256"]:
            changed.append(entry["path"])
    checkpoint_changed = []
    for entry in snapshot["selected_checkpoints"]:
        path = confined_path(root, entry["path"])
        if not path.is_file() or file_hash(path) != entry["expected_sha256"]:
            checkpoint_changed.append(entry["path"])
    raw_changed = []
    for entry in snapshot["raw_files"]:
        path = confined_path(root, entry["path"])
        expected = datetime.fromisoformat(entry["mtime_utc"].replace("Z", "+00:00")).timestamp()
        if not path.is_file() or path.stat().st_size != entry["bytes"] or abs(path.stat().st_mtime - expected) > 0.00001:
            raw_changed.append(entry["path"])
    expected_paths = {entry["path"] for entry in snapshot["files"]}
    added = []
    for scope in snapshot["required_scopes"]:
        path = confined_path(root, scope)
        if path.is_dir():
            added.extend(p.relative_to(Path(root).resolve()).as_posix() for p in path.rglob("*")
                         if p.is_file() and "__pycache__" not in p.parts
                         and p.relative_to(Path(root).resolve()).as_posix() not in expected_paths)
    return {"status": "PASS" if not (changed or checkpoint_changed or raw_changed or added) else "MISMATCH",
            "checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "hashed_files_checked": len(snapshot["files"]), "checkpoints_checked": len(snapshot["selected_checkpoints"]),
            "raw_metadata_checked": len(snapshot["raw_files"]), "raw_verification": "SIZE_AND_MTIME_ONLY",
            "changed": changed, "checkpoint_changed": checkpoint_changed, "raw_changed": raw_changed,
            "added_in_scopes": sorted(set(added))}


def write_new_json(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def capacity_projection(daily_minutes, days, measured_minutes_per_sample, repeat_count, adjudication_minutes=0):
    if min(daily_minutes, days, measured_minutes_per_sample) <= 0 or repeat_count < 0 or adjudication_minutes < 0:
        raise ValueError("INVALID_CAPACITY_INPUT")
    usable = daily_minutes * days / 1.2 - adjudication_minutes
    return max(0, int(usable / measured_minutes_per_sample) - repeat_count)


def repeat_earliest_at(round1_completed_at):
    completed = datetime.fromisoformat(round1_completed_at)
    if completed.utcoffset() is None:
        raise ValueError("REPEAT_TIMESTAMP_NEEDS_TIMEZONE")
    return (completed + timedelta(hours=168)).isoformat()
