"""Prepare manual privacy/provenance review for all filtered VQA addresses."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/interim/vqa/viet_receipt_raw_addresses.csv"
OUTPUT = ROOT / "data/interim/annotation/sprint03/vqa_review_queue.csv"
REPORT = ROOT / "docs/sprints/sprint_03/vqa_review_inventory.json"
LANDMARK = re.compile(r"\b(?:gần|đối diện|cạnh|bên cạnh|chợ|cầu|bệnh viện|ngã tư)\b", re.I)
DIRECTION = re.compile(r"\b(?:hướng|đi về|rẽ|quẹo|đi thẳng|bên trái|bên phải)\b", re.I)
CONTACT = re.compile(r"(?:\b0\d{9,10}\b|\S+@\S+|\b(?:khách hàng|người nhận|điện thoại)\b)", re.I)
FIELDS = (
    "candidate_id", "text", "source_row", "source_file_sha256", "text_sha256",
    "landmark_cue", "direction_cue", "contact_cue", "source_document_id",
    "source_group_id", "privacy_status", "reuse_rights_status", "reviewer",
    "reviewed_at", "decision_reason",
)


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def main() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    source_hash = digest(SOURCE.read_bytes())
    with SOURCE.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if "ChuoiDiaChi" not in (reader.fieldnames or []):
            raise ValueError("VQA interim CSV lacks ChuoiDiaChi")
        rows = list(reader)
    output = []
    for line_number, row in enumerate(rows, start=2):
        text = row["ChuoiDiaChi"].strip()
        if not text:
            continue
        text_hash = digest(text.encode("utf-8"))
        output.append({
            "candidate_id": f"vqa_{text_hash[:16]}",
            "text": text,
            "source_row": str(line_number),
            "source_file_sha256": source_hash,
            "text_sha256": text_hash,
            "landmark_cue": str(bool(LANDMARK.search(text))).lower(),
            "direction_cue": str(bool(DIRECTION.search(text))).lower(),
            "contact_cue": str(bool(CONTACT.search(text))).lower(),
            "source_document_id": "",
            "source_group_id": "",
            "privacy_status": "PENDING_MANUAL_REVIEW",
            "reuse_rights_status": "UNVERIFIED",
            "reviewer": "",
            "reviewed_at": "",
            "decision_reason": "",
        })
    ids = [row["candidate_id"] for row in output]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate VQA candidate IDs; inspect identical text")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(output)
    report = {
        "source": SOURCE.relative_to(ROOT).as_posix(), "source_sha256": source_hash,
        "row_count": len(output),
        "landmark_cue_count": sum(row["landmark_cue"] == "true" for row in output),
        "direction_cue_count": sum(row["direction_cue"] == "true" for row in output),
        "contact_cue_count": sum(row["contact_cue"] == "true" for row in output),
        "source_document_id_available_in_interim_csv": False,
        "privacy_reviewed_count": 0, "reuse_rights_verified_count": 0,
        "status": "HOLD",
        "limitations": [
            "Regex cues are only triage signals, not gold labels or full PII clearance.",
            "The interim CSV has one column and cannot recover receipt/document IDs.",
            "Do not place VQA in training or public exports until manual privacy and rights review is recorded.",
        ],
        "review_queue": OUTPUT.relative_to(ROOT).as_posix(),
        "review_queue_sha256": digest(OUTPUT.read_bytes()),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "rows": len(output),
                      "report": str(REPORT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
