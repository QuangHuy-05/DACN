"""Adapter for vietnamadminunits baseline library."""

from __future__ import annotations

import re
from typing import Any

from vietnamadminunits import convert_address, parse_address
from src.evaluation.adapters.base import BaseAddressParser
from src.evaluation.schema import StandardPrediction


def _split_street_house_number(street_text: str | None, house_no: str | None) -> tuple[str, str]:
    """Separate house number and street name if combined in AdminUnit.street."""
    h = str(house_no or "").strip()
    s = str(street_text or "").strip()
    if h and s:
        return h, s
    if not s:
        return h, ""

    # Common Vietnamese patterns: "123 Đường A" or "12/3A, Phố B"
    match = re.match(r"^(\d+[\w\/\-]*)(?:[,\s]+)(.*)$", s)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return "", s


def _call_geocoder_with_trace(geocoder: Any, address: str, trace: dict[str, Any], max_attempts: int = 2):
    """Call an external geocoder with bounded retries and an auditable fallback.

    Returning ``None`` after a service failure deliberately invokes the
    third-party converter's documented default-ward branch. The raw trace
    retains that distinction; callers must not treat it as spatial evidence.
    """
    trace["geocoder_attempted"] = True
    trace["geocoder_attempts"] = 0
    errors: list[str] = []
    for attempt in range(1, max_attempts + 1):
        trace["geocoder_attempts"] = attempt
        try:
            result = geocoder(address)
        except Exception as exc:
            errors.append(type(exc).__name__)
            continue
        trace["geocoder_status"] = "resolved" if result else "empty"
        if errors:
            trace["geocoder_error_types"] = errors
        return result
    trace["geocoder_status"] = "unavailable_after_retries"
    trace["geocoder_error_types"] = errors
    return None


class VietnamAdminUnitsAdapter(BaseAddressParser):
    """Adapter wrapping parse_address and convert_address of vietnamadminunits."""

    @property
    def tool_name(self) -> str:
        return "vietnamadminunits"

    def parse(self, raw_address: str, mode: str = "FROM_2025", **kwargs: Any) -> tuple[StandardPrediction, Any]:
        """Parse raw address using specified mode ('FROM_2025' or 'LEGACY')."""
        try:
            unit = parse_address(raw_address, mode=mode, keep_street=True)
            if unit is None:
                return StandardPrediction(), {"error": "Returned None", "mode": mode}

            h_no, st = _split_street_house_number(
                getattr(unit, "street", None), getattr(unit, "house_number", None)
            )
            pred = StandardPrediction(
                so_nha=h_no,
                ten_duong=st,
                phuong_xa=str(getattr(unit, "ward", "") or ""),
                quan_huyen=str(getattr(unit, "district", "") or ""),
                tinh_thanh=str(getattr(unit, "province", "") or ""),
            )
            raw_data = {
                "address": unit.get_address(),
                "province": getattr(unit, "province", None),
                "district": getattr(unit, "district", None),
                "ward": getattr(unit, "ward", None),
                "street": getattr(unit, "street", None),
                "mode": mode,
            }
            return pred, raw_data
        except Exception as e:
            return StandardPrediction(), {"error": str(e), "mode": mode}

    def convert_to_2025(self, raw_address: str) -> tuple[StandardPrediction, Any]:
        """Convert legacy address to 2025 administrative unit with branch tracing."""
        trace: dict[str, Any] = {
            "direction": "old_to_new",
            "geocoder_attempted": False,
            "geocoder_status": "not_applicable",
            "fallback_used": "unknown",
            "selection_path": "unknown",
        }
        converter_module = None
        original_geocoder = None
        try:
            # The third-party converter imports this symbol into its module.
            # Temporarily wrap it so the audit log records the actual branch
            # rather than inferring fallback behavior from an error outcome.
            from vietnamadminunits.converter import converter_2025 as converter_module

            original_geocoder = converter_module.get_geo_location

            def traced_geocoder(address: str):
                return _call_geocoder_with_trace(original_geocoder, address, trace)

            converter_module.get_geo_location = traced_geocoder
            unit = convert_address(raw_address, mode="CONVERT_2025")
            if unit is None:
                return StandardPrediction(), {"error": "Convert returned None", "conversion_trace": trace}

            old_unit = getattr(unit, "OldAdminUnit", None)
            old_key = ""
            if old_unit is not None:
                old_key = "_".join(
                    str(getattr(old_unit, name, "") or "")
                    for name in ("province_key", "district_key", "ward_key")
                )
            trace["old_admin_key"] = old_key
            trace["old_street_present"] = bool(getattr(old_unit, "street", ""))
            trace["selected_ward"] = str(getattr(unit, "ward", "") or "")

            if old_unit is not None:
                province_key = next(
                    (key for key, values in converter_module.DICT_PROVINCE.items()
                     if getattr(old_unit, "province_key", "") in values),
                    None,
                )
                divided = converter_module.DICT_PROVINCE_WARD_DIVIDED.get(province_key, {}).get(old_key, [])
                trace["candidate_count"] = len(divided)
                if not divided:
                    trace["selection_path"] = "unique_dictionary_or_unresolved"
                    trace["fallback_used"] = False
                elif not trace["old_street_present"]:
                    trace["selection_path"] = "divided_default_without_street"
                    trace["fallback_used"] = True
                elif trace["geocoder_status"] in {"empty", "unavailable_after_retries"}:
                    trace["selection_path"] = "divided_default_after_geocoder_unavailable"
                    trace["fallback_used"] = True
                elif trace["geocoder_status"] == "resolved":
                    trace["selection_path"] = "divided_geospatial_selection"
                    trace["fallback_used"] = False
                else:
                    trace["selection_path"] = "divided_unobserved_branch"

            h_no, st = _split_street_house_number(
                getattr(unit, "street", None), getattr(unit, "house_number", None)
            )
            pred = StandardPrediction(
                so_nha=h_no,
                ten_duong=st,
                phuong_xa=str(getattr(unit, "ward", "") or ""),
                quan_huyen="",  # Post-2025 has no district
                tinh_thanh=str(getattr(unit, "province", "") or ""),
            )
            raw_data = {
                "address": unit.get_address(),
                "province": getattr(unit, "province", None),
                "ward": getattr(unit, "ward", None),
                "street": getattr(unit, "street", None),
                "conversion_trace": trace,
            }
            return pred, raw_data
        except Exception as e:
            return StandardPrediction(), {"error": str(e), "conversion_trace": trace}
        finally:
            if converter_module is not None and original_geocoder is not None:
                converter_module.get_geo_location = original_geocoder
