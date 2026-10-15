"""Package explicitly authorized AI suggestions without publishing test gold.

Span proposals are authored from text alone. Administrative reference lookups
only supply conservative dated hints; this module never loads benchmark GT.
"""

from collections import Counter
import csv
import hashlib
import importlib
import json
from pathlib import Path
import re
import shutil
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
TEST_IMPORT = ROOT / "docs/sprints/sprint_03/annotation_handoff/test100_v1/test100_import.json"
TEST_HASH = "edabd2212dfbeb49bd3ce139b49d804c0815c5e41550160eea0319f652997247"
MODEL_VERSION = "s3_span11_test100_ai_assisted_v1_not_gold"
SHORT_LABELS = {
    "house": "SoNha", "road": "TenDuong", "alley": "Ngo/Hem",
    "building": "ToaNha/CanHo", "ward": "PhuongXa", "district": "QuanHuyen",
    "province": "TinhThanh", "landmark": "MocDinhVi", "direction": "HuongDi",
    "note": "GhiChu", "other": "Khac",
}
OLD_REFERENCE = ROOT / "data/interim/modeling/sprint03/pre_colab_20261003_resume_v1/u1_v4/reference_old.jsonl"
NEW_REFERENCE = ROOT / "data/processed/gazetteer/s3_v4_nso_dual_snapshot_release2/official_code_reference.csv"
RESOURCE_HASHES = {
    "old_reference": "a58ebd6019268321bd92cee5ded74b1af7162f6bb211cc0bf8500d2ba3c9ab00",
    "new_reference": "a01e4d813887dcdfaf9c1e11782059121acaf2ffe50b71fe7451bb554b7ac852",
}
PRIORITY_IDS = {
    "s3_b489935e347b0113", "s3_3dfc3828c9e52f8c", "s3_e192f19b0b238432",
    "s3_b4c966dd68e1fd73", "s3_878554ae9b7f8f0b", "s3_c3abeb01e2e73e91",
    "s3_3271d5524fc50164", "s3_39a5dfd0ab38f906", "s3_813d3b0d62e9319c",
    "s3_98d58db06330840b",
}


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized(value):
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


def read_locked_tasks(path=TEST_IMPORT, expected_hash=TEST_HASH, expected_count=100):
    if file_hash(path) != expected_hash:
        raise ValueError("FROZEN_TEST_IMPORT_HASH_MISMATCH")
    tasks = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(tasks, list) or len(tasks) != expected_count:
        raise ValueError("WRONG_FROZEN_TASK_COUNT")
    ids = set()
    for task in tasks:
        if not isinstance(task, dict) or set(task) != {"data"}:
            raise ValueError("INPUT_MUST_BE_TEXT_ONLY_TASKS")
        data = task["data"]
        if not isinstance(data, dict) or set(data) != {"sample_id", "text"}:
            raise ValueError("HIDDEN_METADATA_NOT_ALLOWED")
        if (not isinstance(data["sample_id"], str) or not data["sample_id"] or
                not isinstance(data["text"], str) or not data["text"] or
                data["sample_id"] in ids):
            raise ValueError("INVALID_OR_DUPLICATE_TASK")
        ids.add(data["sample_id"])
    return tasks


def align_segments(text, segments):
    """Explicit ordered literal proposals, never token normalization or fuzzy offsets."""
    spans, cursor = [], 0
    for part in segments:
        if not isinstance(part, list) or len(part) != 2:
            raise ValueError("INVALID_SEGMENT_SPECIFICATION")
        short_label, literal = part
        if short_label not in SHORT_LABELS or not isinstance(literal, str) or not literal:
            raise ValueError("INVALID_LABEL_OR_LITERAL")
        start = text.find(literal, cursor)
        if start < 0:
            raise ValueError(f"LITERAL_NOT_FOUND_AFTER_{cursor}:{literal}")
        # Skipped address content would silently select the wrong repeated mention.
        if text[cursor:start].strip(" \t\r\n,;.-()"):
            raise ValueError(f"UNEXPLAINED_UNLABELED_CONTENT:{text[cursor:start]!r}")
        end = start + len(literal)
        spans.append({"start": start, "end": end, "text": literal,
                      "label": SHORT_LABELS[short_label],
                      "system": "cu" if short_label == "district" else "khong_xac_dinh"})
        cursor = end
    if text[cursor:].strip(" \t\r\n,;.-()"):
        raise ValueError("UNEXPLAINED_TRAILING_CONTENT")
    return spans


def province_name(raw):
    key = normalized(raw)
    names = {
        "hà nội": "Thành phố Hà Nội", "tp.hn": "Thành phố Hà Nội",
        "tp. hà nội": "Thành phố Hà Nội", "thành phố hà nội": "Thành phố Hà Nội",
        "hồ chí minh": "Thành phố Hồ Chí Minh", "tphcm": "Thành phố Hồ Chí Minh",
        "thành phố hồ chí minh": "Thành phố Hồ Chí Minh",
        "bắc ninh": "Tỉnh Bắc Ninh", "t. bắc ninh": "Tỉnh Bắc Ninh",
        "tỉnh bắc ninh": "Tỉnh Bắc Ninh", "vĩnh long": "Tỉnh Vĩnh Long",
        "cần thơ": "Thành phố Cần Thơ",
    }
    return names.get(key)


def ward_name(raw):
    # Only grammatical prefixes expand; accented names are never fuzzily repaired.
    key = normalized(raw)
    if key.startswith(("phường ", "xã ", "đặc khu ")):
        return raw
    remainder = re.sub(r"^p(?:\.|\s)\s*", "", raw, flags=re.IGNORECASE)
    if normalized(remainder) in {"đ a tốn", "đa tốn", "cổ bi"}:
        return "Xã " + remainder
    return "Phường " + remainder


def district_name(raw):
    if normalized(raw).startswith(("quận ", "huyện ", "thành phố ", "thị xã ")):
        return raw
    remainder = re.sub(r"^q(?:\.|\s)\s*", "", raw, flags=re.IGNORECASE)
    if normalized(remainder) == "gia lâm":
        return "Huyện " + remainder
    return "Quận " + remainder


def load_references():
    for name, path in (("old_reference", OLD_REFERENCE), ("new_reference", NEW_REFERENCE)):
        if file_hash(path) != RESOURCE_HASHES[name]:
            raise ValueError("ADMINISTRATIVE_RESOURCE_HASH_MISMATCH:" + name)
    old = [json.loads(line) for line in OLD_REFERENCE.read_text(encoding="utf-8").splitlines() if line]
    with NEW_REFERENCE.open(encoding="utf-8-sig", newline="") as stream:
        new = list(csv.DictReader(stream))
    return old, new


def ward_system(raw, province, district, old, new):
    name = ward_name(raw)
    hits = [row for row in old if row["level"] == "ward" and
            normalized(row["official_name"]) == normalized(name)]
    trace = {"literal": raw, "reference_name": name, "province": province,
             "district": district, "scope": "cu:2025-06-30; moi:2025-07-01",
             "raw_offsets_unchanged": True}
    if not province:
        return "khong_xac_dinh", dict(trace, reason="NO_EXACT_PROVINCE_CONTEXT")
    # Failed source parent links cannot be used as proof of absence in the old system.
    if any(row["validation_status"] != "PARENT_CODE_LINK_PASS" for row in hits):
        return "khong_xac_dinh", dict(trace, reason="OLD_REFERENCE_PARENT_LINK_GAP")
    old_hits = [row for row in hits if normalized(row["province_name"]) == normalized(province)]
    new_hits = [row for row in new if row["level"] == "ward" and
                normalized(row["province"]) == normalized(province) and
                normalized(name) in {normalized(row["canonical_ward"]), normalized(row["official_ward_name"])}]
    trace.update(old_codes=sorted({row["official_code"] for row in old_hits}),
                 new_codes=sorted({row["code"] for row in new_hits}))
    if old_hits and new_hits:
        return "khong_xac_dinh", dict(trace, reason="NAME_PRESENT_IN_BOTH_SNAPSHOTS")
    if district:
        old_hits = [row for row in old_hits if normalized(row["district_name"]) == normalized(district)]
    if len(old_hits) == 1 and not new_hits:
        return "cu", dict(trace, reason="EXACT_OLD_WARD_PARENT_SNAPSHOT", evidence=[{
            key: old_hits[0][key] for key in ("official_code", "source_id", "source_hash", "source_locator")}])
    if len(new_hits) == 1 and not old_hits:
        # Test text without a date still needs human confirmation of the 2025 interpretation.
        return "moi", dict(trace, reason="EXACT_NEW_WARD_PROVINCE_SNAPSHOT", evidence=[{
            key: new_hits[0][key] for key in ("code", "source_id", "source_locator")}])
    return "khong_xac_dinh", dict(trace, reason="NO_UNIQUE_DATED_REFERENCE")


def build_candidates(tasks, proposals, old, new):
    rows = proposals.get("rows")
    if not isinstance(rows, list) or len(rows) != len(tasks):
        raise ValueError("PROPOSAL_COUNT_MISMATCH")
    definitions = {}
    for row in rows:
        if (not isinstance(row, list) or len(row) != 3 or not isinstance(row[0], str) or
                row[0] in definitions or not isinstance(row[2], str)):
            raise ValueError("INVALID_OR_DUPLICATE_PROPOSAL")
        definitions[row[0]] = row
    if set(definitions) != {task["data"]["sample_id"] for task in tasks}:
        raise ValueError("PROPOSAL_IDS_DIFFER_FROM_FROZEN_TEST")
    records = []
    for number, task in enumerate(tasks, 1):
        sample_id, text = task["data"]["sample_id"], task["data"]["text"]
        _, parts, note = definitions[sample_id]
        spans = align_segments(text, parts)
        province = next((province_name(s["text"]) for s in spans if s["label"] == "TinhThanh"), None)
        district = next((district_name(s["text"]) for s in spans if s["label"] == "QuanHuyen"), None)
        traces = []
        for span in spans:
            if span["label"] == "PhuongXa":
                span["system"], trace = ward_system(span["text"], province, district, old, new)
                traces.append(dict(trace, start=span["start"], end=span["end"]))
        ward_systems = {s["system"] for s in spans if s["label"] == "PhuongXa"}
        known = ward_systems - {"khong_xac_dinh"}
        whole = None
        if "khong_xac_dinh" not in ward_systems:
            if (district and "moi" in known) or known == {"cu", "moi"}:
                whole = "Lai"
            elif len(known) == 1:
                whole = next(iter(known))
            elif district:
                whole = "cu"
        flags = []
        if whole is None:
            flags.append("temporal_ambiguity")
        bare_district = any(s["label"] == "QuanHuyen" and not
                            re.match(r"^(quận|huyện|thành phố|thị xã|quan|q[.\s])", s["text"], re.I)
                            for s in spans)
        if sample_id in PRIORITY_IDS or bare_district:
            flags.append("ambiguous_label")
        explanation = "GỢI Ý AI CHƯA DUYỆT. " + note
        if traces:
            explanation += " Hệ phường/xã: " + "; ".join(
                f'{trace["literal"]}: {trace["reason"]}' for trace in traces) + "."
        if whole is None:
            explanation += " Chưa đủ bằng chứng chốt hệ toàn câu; đang để trống."
        else:
            explanation += f" Hệ toàn câu {whole} là đề xuất theo đơn vị đủ bằng chứng, cần người duyệt xác nhận."
        explanation += " Số nhà/đường và tên tỉnh trùng thời kỳ giữ khong_xac_dinh; không sao chép hệ toàn câu vào chúng."
        records.append({"sample_id": sample_id, "text": text, "spans": spans,
                        "status": "candidate_not_gold", "address_system": whole,
                        "review_flags": flags, "review_note": explanation.strip(),
                        "review_priority": "label_and_boundary" if "ambiguous_label" in flags else
                            "temporal" if "temporal_ambiguity" in flags else "routine",
                        "display_number": number, "reference_trace": traces})
    return records


def write_package(output_dir, proposal_path, acknowledge=False):
    if not acknowledge:
        raise ValueError("ACKNOWLEDGE_ASSISTED_TEST_REQUIRED")
    output_dir = Path(output_dir).resolve()
    output_dir.relative_to((ROOT / "data/interim/annotation/sprint03").resolve())
    if output_dir.exists():
        raise FileExistsError("USE_A_NEW_PACKAGE_VERSION:" + str(output_dir))
    tasks = read_locked_tasks()
    proposals = json.loads(Path(proposal_path).read_text(encoding="utf-8"))
    old, new = load_references()
    candidates = build_candidates(tasks, proposals, old, new)
    helper = importlib.import_module("scripts.15_import_pilot_predictions")
    converter = importlib.import_module("scripts.17_convert_span_annotation_batch")
    output_dir.mkdir(parents=True)
    def dump(name, value):
        (output_dir / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    dump("test100_candidate_spans.json", candidates)
    helper.validate_candidates(output_dir / "test100_candidate_spans.json", expected_count=100)
    imports = []
    for task, record in zip(tasks, candidates):
        result = helper.prediction_results(record)
        # Structural round trip only: no annotation is saved or claimed as human gold.
        canonical = converter.convert_annotation({"result": result}, record["text"], record["sample_id"])
        if [(s["start"], s["end"], s["label"], s["system"]) for s in canonical["spans"]] != [
                (s["start"], s["end"], s["label"], s["system"]) for s in record["spans"]]:
            raise ValueError("PREDICTION_ROUND_TRIP_MISMATCH")
        imports.append({"data": dict(task["data"]), "predictions": [{"model_version": MODEL_VERSION, "result": result}]})
    dump("test100_import_with_predictions.json", imports)
    dump("test100_text_only_import.json", tasks)
    dump("review_queue.json", [{k: row[k] for k in ("display_number", "sample_id", "review_priority", "review_flags", "review_note")}
                                for row in candidates])
    source_package = TEST_IMPORT.parent
    for name in ("label_studio_span11.xml", "span_11_annotation_guideline.md"):
        shutil.copyfile(source_package / name, output_dir / name)
    lines = ["# 100 mẫu test — gợi ý AI, chờ người duyệt", "", "Không phải gold. Số thứ tự dưới đây là thứ tự file import, không phải task ID Label Studio.", ""]
    for row in candidates:
        lines += [f'## {row["display_number"]}. {row["sample_id"]}', "", row["text"], "",
                  "| Đoạn nguyên văn | Nhãn | Hệ |", "| --- | --- | --- |"]
        lines += [f'| `{s["text"]}` | {s["label"]} | {s["system"]} |' for s in row["spans"]]
        lines += ["", f'Hệ toàn câu: **{row["address_system"] or "chưa xác định — để trống"}**.', "", row["review_note"], ""]
    (output_dir / "review_all_100.md").write_text("\n".join(lines), encoding="utf-8")
    counts = {"tasks": len(candidates), "spans": sum(len(row["spans"]) for row in candidates),
              "labels": dict(Counter(s["label"] for row in candidates for s in row["spans"])),
              "span_systems": dict(Counter(s["system"] for row in candidates for s in row["spans"])),
              "address_systems": dict(Counter(row["address_system"] or "UNDETERMINED" for row in candidates)),
              "review_priorities": dict(Counter(row["review_priority"] for row in candidates))}
    dump("prediction_structure_qa.json", {"status": "PASS_CANDIDATE_STRUCTURE_ONLY", "counts": counts,
         "checks": {"frozen_ids_text": "PASS", "substring_offset": "PASS", "overlap": "PASS",
                    "required_span_system": "PASS", "label_studio_result_round_trip": "PASS",
                    "human_review": "PENDING", "human_annotations_created": 0,
                    "model_evaluation": "NOT_RUN"}})
    dump("manifest.json", {"version": "test100-ai-assisted-v1-20261004", "created_on": "2026-10-04",
         "annotation_mode": "AI_ASSISTED_HUMAN_REVIEW_PENDING", "status": "CANDIDATES_NOT_GOLD",
         "authorization": "Owner requested AI annotation of test100 followed by owner review on 2026-10-04",
         "protocol_amendment": "docs/sprints/sprint_03/37_test100_ai_assisted_annotation.md",
         "guideline_version": "s3-span-v1.1", "model_version": MODEL_VERSION,
         "method": proposals["method"], "count": counts,
         "test_input_sha256": file_hash(TEST_IMPORT), "proposal_sha256": file_hash(proposal_path),
         "builder_sha256": file_hash(Path(__file__)),
         "serializer_sha256": file_hash(Path(helper.__file__)),
         "structure_validator_sha256": file_hash(Path(converter.__file__)),
         "administrative_resources": {name: {"path": path.relative_to(ROOT).as_posix(), "sha256": file_hash(path)}
            for name, path in (("old_reference", OLD_REFERENCE), ("new_reference", NEW_REFERENCE))},
         "source_url": "https://danhmuchanhchinh.nso.gov.vn/", "source_scope": "Two snapshots only; parent gaps cause abstention",
         "new_downloads": [], "packages_installed": [], "installed_bytes": 0,
         "human_review_count": 0, "agreement": "NOT_MEASURED", "benchmark_gold_read": False,
         "baseline_predictions_used": False, "training_tuning_scoring_on_test": False,
         "original_blind_handoff": "UNCHANGED_ARCHIVED_PROTOCOL",
         "files": {path.name: {"sha256": file_hash(path), "bytes": path.stat().st_size}
                   for path in sorted(output_dir.iterdir()) if path.is_file()}})
    if file_hash(TEST_IMPORT) != TEST_HASH:
        raise ValueError("FROZEN_INPUT_CHANGED")
    return counts
