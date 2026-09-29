"""Baseline HEUR-JW: Heuristic candidate lookup from temporal gazetteer + Jaro-Winkler ranking.

Follows the Sprint 3 Model Matrix contract:
- Extracts spans for administrative units (TinhThanh, QuanHuyen, PhuongXa) and surface cues (SoNha, TenDuong, Ngo/Hem).
- Uses Jaro-Winkler string similarity against audited gazetteer entities and aliases.
- Validates temporal validity against the 01/07/2025 boundary to classify address system (cu, moi, Lai).
- Abstains (abstain=True) when confidence is below threshold or ambiguity cannot be resolved.
"""

from __future__ import annotations

import csv
import re
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from src.evaluation.adapters.base import BaseAddressParser, BaseSpanAddressParser
from src.evaluation.schema import (
    CharacterSpan,
    SpanModelOutput,
    StandardPrediction,
)


def jaro_similarity(s1: str, s2: str) -> float:
    """Calculate Jaro similarity between two strings."""
    if s1 == s2:
        return 1.0
    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0

    max_dist = max(len1, len2) // 2 - 1
    if max_dist < 0:
        max_dist = 0

    s1_matches = [False] * len1
    s2_matches = [False] * len2

    matches = 0
    for i in range(len1):
        start = max(0, i - max_dist)
        end = min(i + max_dist + 1, len2)
        for j in range(start, end):
            if s2_matches[j]:
                continue
            if s1[i] == s2[j]:
                s1_matches[i] = True
                s2_matches[j] = True
                matches += 1
                break

    if matches == 0:
        return 0.0

    transpositions = 0
    k = 0
    for i in range(len1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1

    t = transpositions / 2.0
    return (matches / len1 + matches / len2 + (matches - t) / matches) / 3.0


def jaro_winkler_similarity(s1: str, s2: str, prefix_scaling: float = 0.1) -> float:
    """Calculate Jaro-Winkler distance between two strings with prefix bonus."""
    j_sim = jaro_similarity(s1, s2)
    prefix_len = 0
    for c1, c2 in zip(s1[:4], s2[:4]):
        if c1 == c2:
            prefix_len += 1
        else:
            break
    return j_sim + prefix_len * prefix_scaling * (1.0 - j_sim)


def normalize_surface(text: str) -> str:
    """Normalize whitespace and lowercase while preserving Vietnamese accents."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text or "").casefold().strip())


@dataclass
class GazetteerCandidate:
    entity_id: str
    level: str
    system: str
    canonical_name: str
    parent_id: str
    valid_from: str
    valid_to: str


class HeuristicJaroWinklerAdapter(BaseAddressParser, BaseSpanAddressParser):
    """HEUR-JW baseline adapter evaluating address strings using gazetteer and Jaro-Winkler."""

    def __init__(
        self,
        gazetteer_dir: str | Path | None = None,
        similarity_threshold: float = 0.82,
    ) -> None:
        self._tool_name = "HEUR-JW"
        self.threshold = similarity_threshold

        root_path = Path(__file__).resolve().parents[3]
        if gazetteer_dir is None:
            self.gazetteer_dir = root_path / "data/processed/gazetteer/s3_v1"
        else:
            self.gazetteer_dir = Path(gazetteer_dir)

        self._entities_by_level: dict[str, list[GazetteerCandidate]] = {
            "province": [],
            "district": [],
            "ward": [],
        }
        self._alias_map: dict[str, list[tuple[str, str]]] = {
            "province": [],
            "district": [],
            "ward": [],
        }
        self._load_gazetteer()

    @property
    def tool_name(self) -> str:
        return self._tool_name

    def _load_gazetteer(self) -> None:
        entities_file = self.gazetteer_dir / "entities.csv"
        aliases_file = self.gazetteer_dir / "aliases.csv"

        if not entities_file.is_file():
            return

        with entities_file.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            for row in reader:
                lvl = row.get("level", "")
                if lvl in self._entities_by_level:
                    cand = GazetteerCandidate(
                        entity_id=row["entity_id"],
                        level=lvl,
                        system=row.get("system", ""),
                        canonical_name=row.get("canonical_name", ""),
                        parent_id=row.get("parent_id", ""),
                        valid_from=row.get("valid_from", ""),
                        valid_to=row.get("valid_to", ""),
                    )
                    self._entities_by_level[lvl].append(cand)

        if aliases_file.is_file():
            with aliases_file.open("r", encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream)
                for row in reader:
                    lvl = row.get("level", "")
                    alias = row.get("alias", "")
                    entity_id = row.get("entity_id", "")
                    if lvl in self._alias_map and alias:
                        self._alias_map[lvl].append((normalize_surface(alias), entity_id))

    def _find_best_admin_match(
        self, segment_text: str, level: str
    ) -> tuple[GazetteerCandidate | None, float, str]:
        """Find best matching entity at a level using Jaro-Winkler."""
        norm_seg = normalize_surface(segment_text)
        if not norm_seg:
            return None, 0.0, ""

        # First check direct alias matches
        for alias, entity_id in self._alias_map.get(level, []):
            if norm_seg == alias or (len(alias) > 3 and alias in norm_seg):
                for cand in self._entities_by_level[level]:
                    if cand.entity_id == entity_id:
                        return cand, 1.0, cand.canonical_name

        best_cand: GazetteerCandidate | None = None
        best_score = 0.0
        best_name = ""

        # Check candidate similarity
        for cand in self._entities_by_level.get(level, []):
            norm_cand = normalize_surface(cand.canonical_name)
            # Remove administrative prefix for lenient matching if present
            core_cand = re.sub(
                r"^(?:tỉnh|thành phố|tp\.?|quận|huyện|thị xã|tx\.?|phường|xã|thị trấn|tt\.?)\s+",
                "",
                norm_cand,
            ).strip()
            core_seg = re.sub(
                r"^(?:tỉnh|thành phố|tp\.?|quận|huyện|thị xã|tx\.?|phường|xã|thị trấn|tt\.?)\s+",
                "",
                norm_seg,
            ).strip()

            score_full = jaro_winkler_similarity(norm_seg, norm_cand)
            score_core = (
                jaro_winkler_similarity(core_seg, core_cand)
                if core_seg and core_cand
                else 0.0
            )
            score = max(score_full, score_core)

            if score > best_score:
                best_score = score
                best_cand = cand
                best_name = cand.canonical_name

        if best_score >= self.threshold:
            return best_cand, best_score, best_name
        return None, best_score, best_name

    def parse_spans(
        self, raw_address: str, sample_id: str = "", **kwargs: Any
    ) -> SpanModelOutput:
        start_time = time.perf_counter()
        raw_text = raw_address or ""

        spans: list[CharacterSpan] = []
        occupied_ranges: list[tuple[int, int]] = []
        trace: dict[str, Any] = {"admin_matches": []}

        def is_occupied(s: int, e: int) -> bool:
            return any(max(s, occ_s) < min(e, occ_e) for occ_s, occ_e in occupied_ranges)

        # 1. Surface cue extraction: SoNha & Ngo/Hem
        # Look for SoNha at start of address
        sonha_match = re.search(r"^\s*(?:Số\s+)?(\d+[A-Za-z]?(?:/\d+[A-Za-z]?)*)", raw_text, re.IGNORECASE)
        if sonha_match:
            s_start, s_end = sonha_match.span(1)
            spans.append(
                CharacterSpan(
                    start=s_start,
                    end=s_end,
                    label="SoNha",
                    text=raw_text[s_start:s_end],
                )
            )
            occupied_ranges.append((s_start, s_end))

        # Look for Ngo/Hem
        ngo_match = re.search(r"\b(?:ngõ|hẻm|ngách|kiệt)\s+([^\s,]+(?:/\d+)*)", raw_text, re.IGNORECASE)
        if ngo_match:
            n_start, n_end = ngo_match.span()
            if not is_occupied(n_start, n_end):
                spans.append(
                    CharacterSpan(
                        start=n_start,
                        end=n_end,
                        label="Ngo/Hem",
                        text=raw_text[n_start:n_end],
                    )
                )
                occupied_ranges.append((n_start, n_end))

        # Look for TenDuong prefix
        duong_match = re.search(r"\b(?:đường|phố)\s+([^,]+)", raw_text, re.IGNORECASE)
        if duong_match:
            d_start, d_end = duong_match.span()
            # Clean trailing spaces
            cleaned_end = d_start + len(raw_text[d_start:d_end].rstrip())
            if not is_occupied(d_start, cleaned_end):
                spans.append(
                    CharacterSpan(
                        start=d_start,
                        end=cleaned_end,
                        label="TenDuong",
                        text=raw_text[d_start:cleaned_end],
                    )
                )
                occupied_ranges.append((d_start, cleaned_end))

        # 2. Administrative Segment Parsing (split by comma or common delimiters)
        # We split text into non-overlapping token segments
        segments = []
        for m in re.finditer(r"[^,;\n]+", raw_text):
            seg_str = m.group(0).strip()
            if not seg_str:
                continue
            seg_start = m.start() + (len(m.group(0)) - len(m.group(0).lstrip()))
            seg_end = seg_start + len(seg_str)
            segments.append((seg_start, seg_end, seg_str))

        detected_levels: dict[str, tuple[GazetteerCandidate, float]] = {}

        # Reverse order scan (Province -> District -> Ward)
        for s_start, s_end, seg_str in reversed(segments):
            if is_occupied(s_start, s_end):
                continue

            # Check Province if not found
            if "province" not in detected_levels:
                cand, score, name = self._find_best_admin_match(seg_str, "province")
                if cand:
                    detected_levels["province"] = (cand, score)
                    spans.append(
                        CharacterSpan(
                            start=s_start,
                            end=s_end,
                            label="TinhThanh",
                            text=raw_text[s_start:s_end],
                            system=cand.system,
                        )
                    )
                    occupied_ranges.append((s_start, s_end))
                    trace["admin_matches"].append({"level": "province", "name": name, "score": score})
                    continue

            # Check District if not found
            if "district" not in detected_levels:
                cand, score, name = self._find_best_admin_match(seg_str, "district")
                if cand:
                    detected_levels["district"] = (cand, score)
                    spans.append(
                        CharacterSpan(
                            start=s_start,
                            end=s_end,
                            label="QuanHuyen",
                            text=raw_text[s_start:s_end],
                            system=cand.system,
                        )
                    )
                    occupied_ranges.append((s_start, s_end))
                    trace["admin_matches"].append({"level": "district", "name": name, "score": score})
                    continue

            # Check Ward if not found
            if "ward" not in detected_levels:
                cand, score, name = self._find_best_admin_match(seg_str, "ward")
                if cand:
                    detected_levels["ward"] = (cand, score)
                    spans.append(
                        CharacterSpan(
                            start=s_start,
                            end=s_end,
                            label="PhuongXa",
                            text=raw_text[s_start:s_end],
                            system=cand.system,
                        )
                    )
                    occupied_ranges.append((s_start, s_end))
                    trace["admin_matches"].append({"level": "ward", "name": name, "score": score})
                    continue

        # Sort spans by character start offset
        spans.sort(key=lambda s: (s.start, s.end))

        # 3. Temporal reasoning & Address System determination
        has_district = "district" in detected_levels
        ward_cand = detected_levels.get("ward", (None, 0.0))[0]

        predicted_system = "khong_ro"
        abstain = False

        if not detected_levels:
            abstain = True
            predicted_system = "khong_ro"
        elif has_district:
            # District is strictly legacy (3-tier system)
            if ward_cand and ward_cand.system == "moi":
                predicted_system = "Lai"
            else:
                predicted_system = "cu"
        else:
            # No district found
            if ward_cand and ward_cand.system == "moi":
                predicted_system = "moi"
            elif ward_cand and ward_cand.system == "cu":
                # Old ward without district - could be incomplete old or ambiguous
                predicted_system = "cu"
            elif "province" in detected_levels and len(detected_levels) == 1:
                # Only province, too ambiguous
                abstain = True
                predicted_system = "khong_ro"
            else:
                predicted_system = "khong_ro"
                abstain = True

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return SpanModelOutput(
            sample_id=sample_id,
            raw_text=raw_text,
            spans=spans,
            predicted_system=predicted_system,
            abstain=abstain,
            latency_ms=round(elapsed_ms, 3),
            trace=trace,
        )

    def parse(self, raw_address: str, **kwargs: Any) -> tuple[StandardPrediction, Any]:
        """Backwards-compatible parse returning 5 standard fields."""
        output = self.parse_spans(raw_address, **kwargs)
        return output.to_standard_5_fields(), output.trace
