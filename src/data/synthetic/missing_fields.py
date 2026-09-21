"""Generate missing-field examples without corrupting ground-truth fields."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.text_normalize import apply_prefix_abbreviations


FIELDS = ("SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh")
DROP_FIELDS = {
    "drop_ward": ("PhuongXa",),
    "drop_district": ("QuanHuyen",),
    "drop_housenumber_ward": ("SoNha", "PhuongXa"),
    "drop_housenumber": ("SoNha",),
}
DEFAULT_WEIGHTS = {
    "drop_ward": 0.4,
    "drop_district": 0.3,
    "drop_housenumber_ward": 0.2,
    "drop_housenumber": 0.1,
}


def _value(row: Any, field: str) -> str:
    value = row.get(field, "") if hasattr(row, "get") else getattr(row, field, "")
    return "" if pd.isna(value) else str(value).strip().rstrip(", ")


def validate_clean_source(frame: pd.DataFrame, system: str) -> None:
    """Ensure input source dataframe contains complete clean addresses."""
    if frame is None or frame.empty:
        raise ValueError(f"Source data for system '{system}' is empty or None")
    required = ["SoNha", "TenDuong", "PhuongXa", "TinhThanh"]
    if system == "cu":
        required.append("QuanHuyen")

    for idx, row in enumerate(frame.to_dict("records")):
        for field in required:
            val = _value(row, field)
            if not val:
                raise ValueError(
                    f"Incomplete clean source for system '{system}' at index {idx}: "
                    f"field '{field}' is empty"
                )


def validate_missing_surface(
    row: dict[str, str],
    system: str,
    missing_kind: str,
    source_index: int | str = "unknown",
) -> None:
    """Assert that only declared fields were dropped, remaining fields are intact, and GT is preserved."""
    if missing_kind not in DROP_FIELDS:
        raise ValueError(
            f"Unknown missing_kind '{missing_kind}' for system '{system}' (source index {source_index})"
        )
    if system == "moi" and missing_kind == "drop_district":
        raise ValueError(
            f"drop_district is not allowed for new system 'moi' (source index {source_index})"
        )

    expected_dropped = set(DROP_FIELDS[missing_kind])
    if system == "moi":
        expected_dropped.add("QuanHuyen")

    for field in FIELDS:
        val = row.get(field, "")
        if field in expected_dropped:
            if val != "":
                raise ValueError(
                    f"Validation failed for system '{system}', missing_kind '{missing_kind}' at source index {source_index}: "
                    f"field '{field}' should be empty but found '{val}'"
                )
        else:
            if val == "":
                raise ValueError(
                    f"Validation failed for system '{system}', missing_kind '{missing_kind}' at source index {source_index}: "
                    f"field '{field}' was unexpectedly empty"
                )

        # Ground truth validation
        gt_field = f"GT_{field}"
        gt_val = row.get(gt_field, "")
        if system == "moi" and field == "QuanHuyen":
            if gt_val != "":
                raise ValueError(
                    f"Validation failed for system '{system}', missing_kind '{missing_kind}' at source index {source_index}: "
                    f"GT_QuanHuyen must be empty for 2-tier new system, found '{gt_val}'"
                )
        else:
            if gt_val == "":
                raise ValueError(
                    f"Validation failed for system '{system}', missing_kind '{missing_kind}' at source index {source_index}: "
                    f"ground truth '{gt_field}' must not be empty"
                )


def generate_missing_fields(
    df_old: pd.DataFrame,
    df_new: pd.DataFrame,
    noise_params_path: Path | None = None,
    target_size: int = 800,
    ratio_old: float = 0.5,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate controlled missing-field examples from verified clean source addresses."""
    if not 0 <= ratio_old <= 1 or target_size < 1:
        raise ValueError("Invalid ratio_old or target_size")
    if df_new is None or df_new.empty or df_old is None or df_old.empty:
        raise ValueError("Both old and new source data are required")

    validate_clean_source(df_old, "cu")
    validate_clean_source(df_new, "moi")

    config: dict[str, Any] = {}
    if noise_params_path:
        if not noise_params_path.exists():
            raise FileNotFoundError(noise_params_path)
        config = json.loads(noise_params_path.read_text(encoding="utf-8")).get("noise_probabilities", {})

    abbrev = config.get("abbreviations", {})
    weights = config.get("missing_rates", DEFAULT_WEIGHTS)
    rng = random.Random(seed)
    quotas = {
        "cu": round(target_size * ratio_old),
        "moi": target_size - round(target_size * ratio_old),
    }

    output: list[dict[str, str]] = []
    for system, source in (("cu", df_old), ("moi", df_new)):
        candidates: list[tuple[int, dict[str, str], str]] = []
        for orig_idx, row in enumerate(source.to_dict("records")):
            original = {field: _value(row, field) for field in FIELDS}
            if system == "moi":
                original["QuanHuyen"] = ""  # Structural absence in two-tier system.
            for kind in DROP_FIELDS:
                if system == "moi" and kind == "drop_district":
                    continue
                candidates.append((orig_idx, original, kind))

        if not candidates and quotas[system]:
            raise ValueError(f"No eligible clean addresses for system '{system}'")

        weighted = [max(0.0, float(weights.get(kind, 0.0))) for _, _, kind in candidates]
        if not any(weighted):
            weighted = [1.0] * len(candidates)

        seen: set[str] = set()
        attempts = 0
        system_rows: list[dict[str, str]] = []
        max_attempts = max(1000, quotas[system] * 30)

        while len(system_rows) < quotas[system] and attempts < max_attempts:
            attempts += 1
            orig_idx, original, kind = rng.choices(candidates, weights=weighted, k=1)[0]
            surface = original.copy()
            for field in DROP_FIELDS[kind]:
                surface[field] = ""
            if system == "moi":
                surface["QuanHuyen"] = ""  # Two-tier new system.

            for field, prefix_type in (
                ("PhuongXa", "ward"),
                ("QuanHuyen", "district"),
                ("TinhThanh", "city"),
            ):
                if surface[field]:
                    surface[field] = apply_prefix_abbreviations(
                        surface[field], prefix_type, abbrev, rng=rng
                    )

            address = ", ".join(surface[field] for field in FIELDS if surface[field])
            if address in seen:
                continue
            seen.add(address)

            row_data = {
                "ChuoiDiaChi": address,
                **surface,
                **{f"GT_{field}": original[field] for field in FIELDS},
                "KieuThieu": kind,
                "HeQuyChieu": system,
            }
            validate_missing_surface(row_data, system, kind, source_index=orig_idx)
            system_rows.append(row_data)

        if len(system_rows) != quotas[system]:
            raise ValueError(
                f"Only {len(system_rows)}/{quotas[system]} unique {system} missing-field examples"
            )
        output.extend(system_rows)

    rng.shuffle(output)
    return pd.DataFrame(output)
