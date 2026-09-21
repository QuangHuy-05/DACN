"""Generate reproducible, labelled raw-noise address examples for Data 2.

The generator starts from verified clean OSM addresses.  It creates a noisy
surface string for baseline input while retaining one immutable ``GT_*`` copy
of every field for scoring.  Observed receipt noise rates only guide relative
choices; they never become labels for the real receipt corpus.
"""

from __future__ import annotations

import json
import random
import re
import unicodedata
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from src.data.administrative_mapping import clean_value
from src.utils.text_normalize import apply_prefix_abbreviations


FIELDS = ("SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh")
LEVELS = ("nhe", "vua", "nang")
LEVEL_WEIGHTS = (0.40, 0.40, 0.20)
OUTPUT_COLUMNS = (
    "ID",
    "ChuoiDiaChi",
    "ChuoiDiaChiGoc",
    *FIELDS,
    *(f"GT_{field}" for field in FIELDS),
    "HeQuyChieu",
    "MucDoNhieu",
    "LoaiNhieu",
    "SoPhepBienDoi",
    "Seed",
    "Nguon",
)


def _field_value(row: dict, field: str) -> str:
    return clean_value(row.get(field, ""))


def _clean_address(values: dict[str, str]) -> str:
    return ", ".join(values[field] for field in FIELDS if values[field])


def _remove_diacritics(value: str) -> str:
    """Remove Vietnamese diacritics while retaining letters and whitespace."""
    normalized = unicodedata.normalize("NFD", value)
    without_marks = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return without_marks.replace("đ", "d").replace("Đ", "D")


def _introduce_ocr_typo(value: str, rng: random.Random) -> str:
    """Introduce one common invoice/OCR confusion without changing all text."""
    replacements = {
        "o": "0", "O": "0", "i": "1", "I": "1", "l": "1", "s": "5", "S": "5",
    }
    positions = [index for index, char in enumerate(value) if char in replacements]
    if not positions:
        return value
    index = rng.choice(positions)
    return value[:index] + replacements[value[index]] + value[index + 1:]


def _abbreviate_fields(
    values: dict[str, str], abbreviation_probs: dict, rng: random.Random
) -> bool:
    """Apply observed prefix abbreviations and report whether a field changed."""
    changed = False
    for field, prefix_type in (
        ("PhuongXa", "ward"),
        ("QuanHuyen", "district"),
        ("TinhThanh", "city"),
    ):
        abbreviated = apply_prefix_abbreviations(
            values[field], prefix_type, abbreviation_probs, rng=rng
        )
        if abbreviated != values[field]:
            values[field] = abbreviated
            changed = True
    return changed


def _choose_text_field(values: dict[str, str], rng: random.Random) -> str | None:
    candidates = [
        field for field in ("TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh")
        if values[field] and any(char.isalpha() for char in values[field])
    ]
    return rng.choice(candidates) if candidates else None


def _drop_fields(
    values: dict[str, str], system: str, missing_rates: dict, rng: random.Random
) -> str | None:
    """Remove one eligible component using receipt-derived relative weights."""
    candidates: list[tuple[str, float]] = []
    if values["SoNha"]:
        candidates.append(("SoNha", float(missing_rates.get("drop_housenumber", 0))))
    if values["PhuongXa"]:
        candidates.append(("PhuongXa", float(missing_rates.get("drop_ward", 0))))
    if system == "cu" and values["QuanHuyen"]:
        candidates.append(("QuanHuyen", float(missing_rates.get("drop_district", 0))))
    if not candidates:
        return None
    fields, weights = zip(*candidates)
    if not any(weights):
        weights = tuple(1.0 for _ in fields)
    chosen = rng.choices(fields, weights=weights, k=1)[0]
    values[chosen] = ""
    return chosen


def _render_noisy(values: dict[str, str], level: str, rng: random.Random) -> tuple[str, bool]:
    """Render deliberately inconsistent receipt-like separators and order."""
    parts = [(field, values[field]) for field in FIELDS if values[field]]
    reordered = False
    if level == "nang" and len(parts) >= 3 and rng.random() < 0.45:
        # Preserve house number with street, but move the administrative tail.
        tail = parts[2:]
        rng.shuffle(tail)
        parts = parts[:2] + tail
        reordered = True

    separator = rng.choice((",", " - ", "; "))
    return separator.join(value for _, value in parts), reordered


def _apply_noise(
    original: dict[str, str],
    system: str,
    level: str,
    abbreviation_probs: dict,
    missing_rates: dict,
    rng: random.Random,
) -> tuple[dict[str, str], str, list[str]]:
    """Create one noisy surface and an auditable list of transformations."""
    surface = dict(original)
    operations: list[str] = []

    if _abbreviate_fields(surface, abbreviation_probs, rng):
        operations.append("viet_tat")

    if level in {"vua", "nang"} and rng.random() < 0.75:
        field = _choose_text_field(surface, rng)
        if field:
            deaccented = _remove_diacritics(surface[field])
            if deaccented != surface[field]:
                surface[field] = deaccented
                operations.append("bo_dau")

    if level == "nang" and rng.random() < 0.70:
        dropped = _drop_fields(surface, system, missing_rates, rng)
        if dropped:
            operations.append(f"thieu_{dropped}")

    if level == "nang" and rng.random() < 0.60:
        field = _choose_text_field(surface, rng)
        if field:
            typo = _introduce_ocr_typo(surface[field], rng)
            if typo != surface[field]:
                surface[field] = typo
                operations.append("loi_ocr_ky_tu")

    address, reordered = _render_noisy(surface, level, rng)
    if reordered:
        operations.append("dao_thu_tu_hanh_chinh")
    operations.append("dinh_dang_phan_cach")

    # A generated sample must be observably different from its clean source.
    if address == _clean_address(original):
        address = re.sub(r",\s*", ",", address)
    return surface, address, operations


def _eligible_records(frame: pd.DataFrame, system: str) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    required = ("SoNha", "TenDuong", "PhuongXa", "TinhThanh")
    if system == "cu":
        required = (*required, "QuanHuyen")
    for row in frame.to_dict("records"):
        values = {field: _field_value(row, field) for field in FIELDS}
        if all(values[field] for field in required):
            records.append(values)
    return records


def generate_raw_noisy_addresses(
    old_addresses: pd.DataFrame,
    new_addresses: pd.DataFrame,
    noise_params_path: Path,
    target_size: int = 1000,
    ratio_old: float = 0.5,
    seed: int = 42,
) -> pd.DataFrame:
    """Build Data 2 from clean labelled addresses and controlled noise.

    ``ChuoiDiaChi`` is the only intended baseline input.  ``GT_*`` fields and
    ``ChuoiDiaChiGoc`` are evaluation metadata and must not be exposed to a
    baseline parser.
    """
    if target_size < 1 or not 0 <= ratio_old <= 1:
        raise ValueError("target_size must be positive and ratio_old must be in [0, 1]")
    if not noise_params_path.exists():
        raise FileNotFoundError(noise_params_path)

    config = json.loads(noise_params_path.read_text(encoding="utf-8"))
    probabilities = config.get("noise_probabilities", {})
    abbreviation_probs = probabilities.get("abbreviations", {})
    missing_rates = probabilities.get("missing_rates", {})
    rng = random.Random(seed)
    quotas = {"cu": round(target_size * ratio_old)}
    quotas["moi"] = target_size - quotas["cu"]
    sources = {
        "cu": _eligible_records(old_addresses, "cu"),
        "moi": _eligible_records(new_addresses, "moi"),
    }
    if any(quotas[system] and not sources[system] for system in quotas):
        raise ValueError("No eligible clean addresses for one requested reference system")

    rows: list[dict[str, str]] = []
    seen_surfaces: set[str] = set()
    for system in ("cu", "moi"):
        attempts = 0
        while sum(row["HeQuyChieu"] == system for row in rows) < quotas[system]:
            attempts += 1
            if attempts > quotas[system] * 80:
                raise ValueError(f"Could not create {quotas[system]} unique noisy {system} addresses")
            original = dict(rng.choice(sources[system]))
            level = rng.choices(LEVELS, weights=LEVEL_WEIGHTS, k=1)[0]
            surface, noisy_address, operations = _apply_noise(
                original, system, level, abbreviation_probs, missing_rates, rng
            )
            if not noisy_address or noisy_address in seen_surfaces:
                continue
            seen_surfaces.add(noisy_address)
            rows.append({
                "ID": "",
                "ChuoiDiaChi": noisy_address,
                "ChuoiDiaChiGoc": _clean_address(original),
                **surface,
                **{f"GT_{field}": original[field] for field in FIELDS},
                "HeQuyChieu": system,
                "MucDoNhieu": level,
                "LoaiNhieu": "|".join(operations),
                "SoPhepBienDoi": str(len(operations)),
                "Seed": str(seed),
                "Nguon": "synthetic_from_verified_osm",
            })

    rng.shuffle(rows)
    for index, row in enumerate(rows, start=1):
        row["ID"] = f"N{index:05d}"
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
