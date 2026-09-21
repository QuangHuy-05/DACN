"""Estimate observable address-noise rates from deduplicated VQA strings.

These are weak-label estimates: absent tokens do not prove the original address
omitted an administrative field. Counts and denominators are kept for audit.
"""

import json
import re
from pathlib import Path

import pandas as pd


PATTERNS = {
    "ward_P": re.compile(r"(?<!\w)P(?:\.|\s+)(?=\s*[\wÀ-ỹ])", re.I),
    "ward_F": re.compile(r"(?<!\w)F(?:\.|\s+)(?=\s*[\wÀ-ỹ])", re.I),
    "district_Q": re.compile(r"(?<!\w)Q(?:\.|\s+)(?=\s*[\wÀ-ỹ])", re.I),
    "district_H": re.compile(r"(?<!\w)H(?:\.|\s+)(?=\s*[\wÀ-ỹ])", re.I),
    "district_TX": re.compile(r"(?<!\w)TX(?:\.|\s+)(?=\s*[\wÀ-ỹ])", re.I),
    "district_TP": re.compile(r"(?<!\w)TP(?:\.|\s+)(?=\s*[\wÀ-ỹ])", re.I),
    "city_TPHCM": re.compile(r"(?<!\w)(?:TP\s*\.?\s*HCM|TPHCM)(?!\w)", re.I),
    "city_TP": re.compile(r"(?<!\w)TP(?:\.|\s+)(?=\s*[\wÀ-ỹ])", re.I),
    "ward_full": re.compile(r"\b(?:phường|xã|thị trấn)\b", re.I),
    "district_full": re.compile(r"\b(?:quận|huyện|thị xã)\b", re.I),
    "housenumber": re.compile(r"^\s*(?:số\s*)?\d+[A-Za-z]?(?:[/-]\d+[A-Za-z]?)*\b", re.I),
}


def profile_noise(addresses):
    rows = [str(value).strip() for value in addresses if pd.notna(value) and str(value).strip()]
    total = len(rows)
    if not total:
        raise ValueError("No receipt addresses to profile")
    counts = {name: sum(bool(pattern.search(row)) for row in rows) for name, pattern in PATTERNS.items()}
    abbreviations = {name: round(counts[name] / total, 6) for name in (
        "ward_P", "ward_F", "district_Q", "district_H", "district_TX", "district_TP", "city_TPHCM", "city_TP"
    )}
    missing_counts = {
        "drop_ward": sum(not (PATTERNS["ward_P"].search(row) or PATTERNS["ward_F"].search(row) or PATTERNS["ward_full"].search(row)) for row in rows),
        "drop_district": sum(not any(PATTERNS[name].search(row) for name in ("district_Q", "district_H", "district_TX", "district_TP", "district_full")) for row in rows),
        "drop_housenumber": total - counts["housenumber"],
    }
    missing_counts["drop_housenumber_ward"] = sum(
        not PATTERNS["housenumber"].search(row) and
        not any(PATTERNS[name].search(row) for name in ("ward_P", "ward_F", "ward_full"))
        for row in rows
    )
    missing_rates = {name: round(count / total, 6) for name, count in missing_counts.items()}
    return {
        "sample_size": total,
        "method": "regex weak-label estimates; missing means no detectable marker, not verified field absence",
        "noise_probabilities": {"abbreviations": abbreviations, "missing_rates": missing_rates},
        "counts": {"abbreviations": counts, "missing_rates": missing_counts},
    }


def write_noise_profile(csv_path: Path, output_path: Path):
    frame = pd.read_csv(csv_path, encoding="utf-8-sig")
    if "ChuoiDiaChi" not in frame:
        raise ValueError(f"Missing ChuoiDiaChi in {csv_path}")
    profile = profile_noise(frame["ChuoiDiaChi"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return profile
