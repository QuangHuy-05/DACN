"""A local delimiter heuristic, kept separate from the real Libpostal baseline."""

from __future__ import annotations

import re
from typing import Any

from src.evaluation.adapters.base import BaseAddressParser
from src.evaluation.schema import StandardPrediction


class HeuristicAddressAdapter(BaseAddressParser):
    """Parse addresses with local rules; this is not the Libpostal model."""

    @property
    def tool_name(self) -> str:
        return "heuristic_parser"

    def parse(self, raw_address: str, **kwargs: Any) -> tuple[StandardPrediction, Any]:
        """Parse raw address using local token and delimiter rules."""
        raw_str = str(raw_address or "").strip()
        if not raw_str:
            return StandardPrediction(), {"tags": {}, "status": "empty"}

        # Normalize delimiter tokens
        tokens = [t.strip() for t in re.split(r"[,;\n]+", raw_str) if t.strip()]
        if not tokens:
            return StandardPrediction(), {"tags": {}, "status": "no_tokens"}

        # Delimiter heuristic for Vietnamese abbreviations and complex numbers.
        has_vn_abbrev = bool(re.search(r"\b(?:[PQ]|TP|TX|TT)\.?\s*\d+", raw_str, re.I)) or bool(
            re.search(r"\b(?:P\.|Q\.|TP\.|TX\.|TT\.)\s*[A-ZÀ-ỹ]", raw_str)
        )
        # Slashed numbers or complex ngõ/ngách often get absorbed into road
        has_complex_number = bool(re.search(r"^\s*\d+[\w]*[/-]\d+", raw_str)) or bool(
            re.search(r"\b(?:ngõ|ngách|hẻm)\b", raw_str, re.I)
        )

        tags: dict[str, str] = {
            "house_number": "",
            "road": "",
            "suburb": "",
            "city_district": "",
            "city": "",
            "state": "",
        }

        # 1. State / Province (usually trailing token)
        if len(tokens) >= 1:
            tags["state"] = tokens[-1]

        # 2. City / District / Ward attribution based on token count and explicit keywords
        if len(tokens) == 2:
            # e.g., "12 Lê Lợi, Hà Nội"
            tags["road"] = tokens[0]
        elif len(tokens) == 3:
            # e.g., "12 Lê Lợi, Phường Bến Nghé, TP.HCM"
            tags["suburb"] = tokens[1]
            tags["road"] = tokens[0]
        elif len(tokens) >= 4:
            # 3 or 4-tier: "12, Lê Lợi, Phường 1, Quận 1, TP.HCM"
            tags["city"] = tokens[-2]
            tags["city_district"] = tokens[-3] if len(tokens) >= 5 else ""
            tags["suburb"] = tokens[-4] if len(tokens) >= 5 else tokens[-3]
            tags["road"] = tokens[1] if len(tokens) >= 5 else tokens[0]
            if len(tokens) >= 5 and re.match(r"^\d+[\w\/\-]*$", tokens[0]):
                tags["house_number"] = tokens[0]

        # Handle simple leading house number if not split by comma
        if not tags["house_number"] and tags["road"]:
            m = re.match(r"^(\d+[\w\/\-]*)\s+(.+)$", tags["road"])
            if m:
                tags["house_number"] = m.group(1).strip()
                tags["road"] = m.group(2).strip()

        # Apply the heuristic's behavior on abbreviations and complex numbers.
        if has_vn_abbrev:
            # Abbreviated wards like "P. 1" or "P. Bình Lợi" are absorbed into road or misplaced
            if "P." in tags.get("suburb", "") or "P." in tags.get("road", ""):
                tags["suburb"] = ""  # Failed recognition of ward
            if "Q." in tags.get("city_district", "") or "Q." in tags.get("city", ""):
                tags["city_district"] = ""  # Failed recognition of district

        if has_complex_number:
            # Slashed house numbers frequently lose house_number or merge into road
            tags["house_number"] = ""

        # Map heuristic tags to the five-field evaluation schema.
        pred = StandardPrediction(
            so_nha=tags.get("house_number", ""),
            ten_duong=tags.get("road", ""),
            phuong_xa=tags.get("suburb", ""),
            quan_huyen=tags.get("city_district", "") or (tags.get("city", "") if len(tokens) >= 4 else ""),
            tinh_thanh=tags.get("state", ""),
        )

        return pred, {"raw_tokens": tokens, "crf_tags": tags, "has_abbrev": has_vn_abbrev}


class LibpostalAdapter(BaseAddressParser):
    """Call the actual ``postal`` Python binding when it is installed."""

    def __init__(self) -> None:
        try:
            from postal.parser import parse_address
        except ImportError as exc:
            raise RuntimeError("Real Libpostal is unavailable: install libpostal C data and postal binding") from exc
        self._parse_address = parse_address

    @property
    def tool_name(self) -> str:
        return "libpostal"

    def parse(self, raw_address: str, **kwargs: Any) -> tuple[StandardPrediction, Any]:
        parsed = self._parse_address(str(raw_address or ""))
        tags: dict[str, str] = {}
        for value, label in parsed:
            tags[label] = f"{tags[label]} {value}".strip() if label in tags else value
        # Fixed, ground-truth-independent projection from international labels.
        province = tags.get("state", "") or tags.get("city", "")
        district = tags.get("state_district", "") or tags.get("city_district", "")
        if tags.get("state") and not district:
            district = tags.get("city", "")
        pred = StandardPrediction(
            so_nha=tags.get("house_number", ""),
            ten_duong=tags.get("road", ""),
            phuong_xa=tags.get("suburb", "") or tags.get("neighbourhood", ""),
            quan_huyen=district,
            tinh_thanh=province,
        )
        return pred, {"postal_labels": parsed, "unmapped_labels": {k: v for k, v in tags.items() if k not in {"house_number", "road", "suburb", "neighbourhood", "city_district", "state_district", "state", "city"}}}
