"""Baseline HEUR-JW: Heuristic candidate lookup from temporal gazetteer + Jaro-Winkler ranking.

Follows the Sprint 3 Model Matrix contract:
- Extracts spans for administrative units (TinhThanh, QuanHuyen, PhuongXa) and surface cues (SoNha, TenDuong, Ngo/Hem).
- Uses Jaro-Winkler string similarity against audited gazetteer entities and aliases.
- Validates temporal validity against the 01/07/2025 boundary to classify address system (cu, moi, Lai).
- Abstains (abstain=True) when confidence is below threshold or ambiguity cannot be resolved.
"""

from __future__ import annotations

import csv
from datetime import date
from functools import lru_cache
import hashlib
import json
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
    code_status: str = "unverified"


class HeuristicJaroWinklerAdapter(BaseAddressParser, BaseSpanAddressParser):
    """HEUR-JW baseline adapter evaluating address strings using gazetteer and Jaro-Winkler."""

    RULE_VERSION = "heur_jw_temporal_reject_v3"
    SUPPORTED_LABELS = ["SoNha", "TenDuong", "Ngo/Hem", "PhuongXa", "QuanHuyen", "TinhThanh"]
    LEVEL_LABELS = {"province": "TinhThanh", "district": "QuanHuyen", "ward": "PhuongXa"}
    PREFIX = re.compile(
        r"^(?:thành\s+phố|thị\s+trấn|thị\s+xã|đặc\s+khu|phường|huyện|quận|tỉnh|xã)\s+|^(?:tp|tt|tx|p|q|h|x)\.\s*", re.I)
    MARKER = re.compile(
        r"(?<!\w)(?:thành\s+phố|thị\s+trấn|thị\s+xã|đặc\s+khu|phường|huyện|quận|tỉnh|xã|đường|phố|ngõ|hẻm|ngách|kiệt)\b|(?<!\w)(?:tp|tt|tx|p|q|h|x)\.", re.I)

    def __init__(self, gazetteer_dir: str | Path | None = None, similarity_threshold: float = 0.90,
                 ambiguity_margin: float = 0.02, temporal_policy: str = "dual_snapshot", as_of_date: str | None = None):
        self._tool_name = "HEUR-JW"
        if not 0 <= similarity_threshold <= 1 or not 0 <= ambiguity_margin < 1:
            raise ValueError("Invalid matching threshold/margin")
        if temporal_policy not in {"dual_snapshot", "fixed_as_of"}:
            raise ValueError("Explicit temporal policy required")
        if temporal_policy == "fixed_as_of" and not as_of_date:
            raise ValueError("fixed_as_of requires an explicit ISO date")
        self.threshold, self.margin = similarity_threshold, ambiguity_margin
        self.temporal_policy = temporal_policy
        self.as_of_date = date.fromisoformat(as_of_date) if as_of_date else None
        root = Path(__file__).resolve().parents[3]
        self.gazetteer_dir = Path(gazetteer_dir) if gazetteer_dir else root / "data/processed/gazetteer/s3_v2"
        self.entities = {}
        self.forms = {level: {} for level in self.LEVEL_LABELS}
        self._load_gazetteer()

    @property
    def tool_name(self) -> str:
        return self._tool_name

    def _load_gazetteer(self) -> None:
        manifest_path = self.gazetteer_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.gazetteer_version = manifest["version"]
        self.resource_hashes = {}
        for name in ("entities.csv", "aliases.csv", "edges.csv", "non_atomic_transitions.csv"):
            path = self.gazetteer_dir / name
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if manifest["output_sha256"].get(name) != digest:
                raise ValueError(f"Gazetteer hash mismatch: {name}")
            self.resource_hashes[name] = digest
        with (self.gazetteer_dir / "entities.csv").open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            required = {"entity_id", "level", "system", "canonical_name", "parent_id", "valid_from", "valid_to", "code_status"}
            if not required <= set(reader.fieldnames or []):
                raise ValueError("Incomplete gazetteer schema")
            for row in reader:
                candidate = GazetteerCandidate(**{k: row[k] for k in required})
                if candidate.level not in self.forms or candidate.entity_id in self.entities:
                    raise ValueError("Invalid/duplicate gazetteer identity")
                self.entities[candidate.entity_id] = candidate
                self._add_form(candidate.canonical_name, candidate.entity_id)
        if any(e.parent_id and e.parent_id not in self.entities for e in self.entities.values()):
            raise ValueError("Gazetteer contains missing parent IDs")
        with (self.gazetteer_dir / "aliases.csv").open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if row["entity_id"] not in self.entities or row["source_id"] != "audited_aliases":
                    raise ValueError("Only aliases from the audited layer are permitted")
                self._add_form(row["alias"], row["entity_id"])
        self.blocks = {level: {} for level in self.forms}
        for level, forms in self.forms.items():
            for form in forms:
                self.blocks[level].setdefault(form[0], []).append(form)

    def _add_form(self, value: str, entity_id: str) -> None:
        core = self._core(value)
        if core:
            level = self.entities[entity_id].level
            self.forms[level].setdefault(core, set()).add(entity_id)

    @classmethod
    def _core(cls, value: str) -> str:
        return cls.PREFIX.sub("", normalize_surface(value)).strip()

    @staticmethod
    def _levels(value: str) -> list[str]:
        norm = normalize_surface(value)
        if re.match(r"^(?:phường|xã|thị trấn|đặc khu)\b|^(?:p|x|tt)\.", norm):
            return ["ward"]
        if re.match(r"^(?:quận|huyện|thị xã)\b|^(?:q|h|tx)\.", norm):
            return ["district"]
        if re.match(r"^tỉnh\b", norm):
            return ["province"]
        if re.match(r"^thành phố\b|^tp\.", norm):
            return ["province", "district"]
        return ["province", "district", "ward"]

    def _valid(self, entity: GazetteerCandidate) -> bool:
        point = self.as_of_date if self.temporal_policy == "fixed_as_of" else date.fromisoformat(
            "2025-06-30" if entity.system == "cu" else "2025-07-01")
        return (not entity.valid_from or date.fromisoformat(entity.valid_from) <= point) and (
            not entity.valid_to or point <= date.fromisoformat(entity.valid_to))

    @staticmethod
    def _unit_kind(value: str) -> str | None:
        normalized = normalize_surface(value)
        for full, short in (("phường", "p"), ("xã", "x"), ("quận", "q"), ("huyện", "h"),
                            ("thị trấn", "tt"), ("thị xã", "tx"), ("thành phố", "tp"), ("tỉnh", "t"), ("đặc khu", "dk")):
            if normalized.startswith(full+" ") or normalized.startswith(short+"."):
                return full
        return None

    def _ancestor_core(self, entity: GazetteerCandidate, level: str) -> str | None:
        visited = set()
        while entity.parent_id:
            if entity.parent_id in visited:
                raise ValueError("Cyclic gazetteer parent chain")
            visited.add(entity.parent_id)
            entity = self.entities[entity.parent_id]
            if entity.level == level:
                return self._core(entity.canonical_name)
        return None

    @lru_cache(maxsize=20000)
    def _rank(self, value: str, level: str) -> tuple:
        core = self._core(value)
        if not core:
            return ()
        forms = [core] if core in self.forms[level] else self.blocks[level].get(core[0], [])
        scored = {}
        for form in forms:
            # This fixed candidate blocking rule is part of the model config.
            if min(len(form), len(core)) / max(len(form), len(core)) < 0.60:
                continue
            score = jaro_winkler_similarity(core, form)
            if score < 0.80:
                continue
            for entity_id in self.forms[level][form]:
                entity = self.entities[entity_id]
                kind = self._unit_kind(value)
                if self._valid(entity) and (kind is None or kind == self._unit_kind(entity.canonical_name)):
                    scored[entity_id] = max(score, scored.get(entity_id, 0))
        return tuple(sorted(scored.items(), key=lambda item: (-item[1], item[0])))

    def _resolve(self, value: str, context: dict) -> tuple[list[GazetteerCandidate], dict]:
        ranked = []
        allowed = self._levels(value)
        for level in allowed:
            for entity_id, score in self._rank(value, level):
                entity = self.entities[entity_id]
                if context.get("province") and level != "province":
                    if self._ancestor_core(entity, "province") not in context["province"]:
                        continue
                if context.get("district") and level == "ward" and entity.system == "cu":
                    if self._ancestor_core(entity, "district") not in context["district"]:
                        continue
                ranked.append((entity, score))
        ranked.sort(key=lambda item: (-item[1], item[0].entity_id))
        best = ranked[0][1] if ranked else 0
        contenders = [entity for entity, score in ranked if score >= self.threshold and best-score <= self.margin]
        info = {"surface": value, "allowed_levels": allowed, "score": best,
            "context": {k: sorted(v) for k, v in context.items()}, "candidate_count": len(ranked),
            "contender_count": len(contenders), "candidates": [
                {"entity_id": e.entity_id, "level": e.level, "system": e.system, "name": e.canonical_name,
                 "parent_id": e.parent_id, "score": score, "code_status": e.code_status,
                 "valid_from": e.valid_from, "valid_to": e.valid_to} for e, score in ranked[:10]]}
        if not contenders:
            info["decision"] = "REJECT_BELOW_THRESHOLD_OR_NO_CONTEXT_MATCH"
            return [], info
        if len({entity.level for entity in contenders}) != 1:
            info["decision"] = "REJECT_AMBIGUOUS_LEVEL"
            return [], info
        info["decision"] = "ACCEPT_SPAN_LEVEL" if len(contenders) == 1 else "ACCEPT_LEVEL_IDENTITY_UNRESOLVED"
        info["entity_id"] = contenders[0].entity_id if len(contenders) == 1 else None
        info["identity_abstain"] = len(contenders) != 1
        info["official_id_output"] = "NOT_IMPLEMENTED_UNVERIFIED_CODES_NOT_EXPORTED"
        return contenders, info

    @classmethod
    def _segments(cls, text: str) -> list[tuple[int, int]]:
        segments = []
        for match in re.finditer(r"[^,;\n()]+", text):
            start, end = match.start(), match.end()
            while start < end and text[start].isspace():
                start += 1
            while end > start and text[end-1].isspace():
                end -= 1
            if start == end:
                continue
            markers = list(cls.MARKER.finditer(text, start, end))
            if re.match(r"(?:ngõ|hẻm|ngách|kiệt)\b", text[start:end], re.I):
                markers = [m for m in markers if re.match(r"(?:ngõ|hẻm|ngách|kiệt|đường|phố)\b", m.group(), re.I)]
            boundaries = sorted({start, end, *(m.start() for m in markers)})
            for left, right in zip(boundaries, boundaries[1:]):
                while right > left and text[right-1].isspace():
                    right -= 1
                if right > left:
                    segments.append((left, right))
        return segments

    def parse_spans(
        self, raw_address: str, sample_id: str = "", **kwargs: Any
    ) -> SpanModelOutput:
        started = time.perf_counter()
        text = raw_address or ""
        spans = []
        trace = {"admin_matches": [], "rule_version": self.RULE_VERSION,
                 "gazetteer_version": self.gazetteer_version, "temporal_policy": self.temporal_policy,
                 "as_of_date": self.as_of_date.isoformat() if self.as_of_date else None}

        def add(start, end, label, system="khong_xac_dinh"):
            if start < end and not any(max(start, s.start) < min(end, s.end) for s in spans):
                spans.append(CharacterSpan(start, end, label, text[start:end], system))

        house = re.match(r"\s*((?:số\s+)?[A-Za-z]{0,4}\d+[A-Za-z]?(?:[-/][\w]+)*)", text, re.I)
        if house:
            add(*house.span(1), "SoNha")
        segments = self._segments(text)
        remaining = []
        for start, end in segments:
            if house and start < house.end(1):
                start = max(start, house.end(1))
                while start < end and text[start].isspace():
                    start += 1
            if start >= end:
                continue
            surface = text[start:end]
            if re.match(r"(?:ngõ|hẻm|ngách|kiệt)\b", surface, re.I):
                numeric = re.match(r"(?:ngõ|hẻm|ngách|kiệt)\s+\d+(?:/\d+)*", surface, re.I)
                lane_end = start+numeric.end() if numeric else end
                add(start, lane_end, "Ngo/Hem")
                if lane_end < end:
                    left = lane_end
                    while left < end and text[left].isspace():
                        left += 1
                    add(left, end, "TenDuong")
            elif re.match(r"(?:đường|phố)\b", surface, re.I):
                add(start, end, "TenDuong")
            else:
                remaining.append((start, end))
        context = {}
        rejected = []
        for start, end in reversed(remaining):
            candidates, info = self._resolve(text[start:end], context)
            info.update(start=start, end=end)
            trace["admin_matches"].append(info)
            if candidates:
                level = candidates[0].level
                systems = {entity.system for entity in candidates}
                system = next(iter(systems)) if len(systems) == 1 else "khong_xac_dinh"
                add(start, end, self.LEVEL_LABELS[level], system)
                if level in {"province", "district"}:
                    context[level] = {self._core(entity.canonical_name) for entity in candidates}
            else:
                rejected.append((start, end))
        # Unprefixed street after a literal house number is a fixed surface
        # rule; it never fills an absent district from the gazetteer.
        if house:
            for start, end in sorted(rejected):
                before = text[house.end(1):start]
                if re.fullmatch(r"[\s,;]*", before) and not self.PREFIX.match(text[start:end]):
                    add(start, end, "TenDuong")
                    break
        spans.sort(key=lambda span: (span.start, span.end))
        systems = {span.system for span in spans if span.label in self.LEVEL_LABELS.values()} - {"khong_xac_dinh"}
        predicted_system = "Lai" if systems == {"cu", "moi"} else next(iter(systems)) if len(systems) == 1 else "khong_ro"
        return SpanModelOutput(sample_id, text, spans, predicted_system=predicted_system,
            abstain=not bool(spans), latency_ms=(time.perf_counter()-started)*1000, trace=trace,
            raw_output={"literal_spans": [s.to_dict() for s in spans], "candidate_trace": trace["admin_matches"]})

    def parse(self, raw_address: str, **kwargs: Any) -> tuple[StandardPrediction, Any]:
        """Backwards-compatible parse returning 5 standard fields."""
        output = self.parse_spans(raw_address, **kwargs)
        return output.to_standard_5_fields(), output.trace
