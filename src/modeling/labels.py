"""Versioned BIO schema and the manifest-driven T1 supervision policy."""

from src.evaluation.schema import ADDRESS_SYSTEMS, SPAN11_LABELS
from src.evaluation.span_features import BIO_LABELS

LABEL_VERSION = "s3-span-bio23-v1"
TAG_TO_ID = {tag: index for index, tag in enumerate(BIO_LABELS)}
DP_TAG_TO_ID = {**TAG_TO_ID, "EOS": len(BIO_LABELS)}


def label_metadata() -> dict:
    return {"version": LABEL_VERSION, "schema": "s3-span-v1.1",
            "span_labels": list(SPAN11_LABELS), "bio_labels": list(BIO_LABELS),
            "t1_labels": list(ADDRESS_SYSTEMS), "t1_reject": "khong_ro"}


def t1_target(row: dict, manifest: dict) -> tuple[int, bool]:
    system = row.get("address_system")
    excluded = manifest.get("evaluation_exclusions", {}).get("t1", [])
    eligible = system in ADDRESS_SYSTEMS and row["sample_id"] not in excluded
    return (ADDRESS_SYSTEMS.index(system) if eligible else 0), eligible


def bio_constraints() -> tuple[list[bool], list[list[bool]]]:
    start = [not tag.startswith("I-") for tag in BIO_LABELS]
    transitions = []
    for previous in BIO_LABELS:
        transitions.append([not tag.startswith("I-") or previous in
                            ("B-" + tag[2:], "I-" + tag[2:]) for tag in BIO_LABELS])
    return start, transitions
