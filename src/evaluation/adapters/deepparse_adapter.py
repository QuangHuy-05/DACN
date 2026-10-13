"""Zero-shot FastText adapter with fixed mapping and conservative raw alignment.

The adapter is implemented even on machines that cannot load full FastText.
Only ordered token/tag output is aligned; aggregated field strings cannot
recover repeated mentions safely.
"""

from __future__ import annotations

import re
import time

from src.evaluation.adapters.base import BaseAddressParser, BaseSpanAddressParser
from src.evaluation.schema import CharacterSpan, SpanModelOutput

MAPPING_VERSION = "dp_native_literal_v1"
SUPPORTED_LABELS = ["SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh"]
NATIVE_DIRECT = {"StreetNumber": "SoNha", "StreetName": "TenDuong"}
ADMIN_PREFIXES = (
    (re.compile(r"^(?:phường|xã|thị\s+trấn|đặc\s+khu|p\.|x\.|tt\.)\s*", re.I), "PhuongXa"),
    (re.compile(r"^(?:quận|huyện|thị\s+xã|q\.|h\.|tx\.)\s*", re.I), "QuanHuyen"),
    (re.compile(r"^tỉnh\s+", re.I), "TinhThanh"),
)


def align_native_tokens(text: str, components: list) -> list[tuple[int, int, str]]:
    """Reverse the documented comma-removal/lowercase/whitespace pipeline.

    Every processed whitespace token must align in sequence to the complete
    raw non-comma token stream. We never search a later occurrence on failure.
    Length-changing lowercase or unsupported preprocessors cause rejection.
    """
    raw_tokens = list(re.finditer(r"[^\s,]+", text))
    if len(raw_tokens) != len(components):
        raise ValueError("Native token count differs from reversible raw token stream")
    aligned = []
    for raw, component in zip(raw_tokens, components):
        if len(component) != 2:
            raise ValueError("Native token/tag pair required")
        value, tag = component
        if isinstance(tag, (tuple, list)):
            tag = tag[0]
        if not isinstance(value, str) or raw.group().lower() != value or len(raw.group().lower()) != len(raw.group()):
            raise ValueError("Native preprocessing cannot be reversed exactly")
        aligned.append((raw.start(), raw.end(), tag))
    return aligned


def map_native_output(text: str, components: list) -> tuple[list[CharacterSpan], list[dict]]:
    aligned = align_native_tokens(text, components)
    groups = []
    for start, end, tag in aligned:
        if groups and groups[-1][2] == tag and text[groups[-1][1]:start].isspace():
            groups[-1] = (groups[-1][0], end, tag)
        else:
            groups.append((start, end, tag))
    spans, mapping_log = [], []
    for start, end, tag in groups:
        literal = text[start:end]
        label = NATIVE_DIRECT.get(tag)
        reason = "native_direct" if label else "unsupported_or_ambiguous_native_tag"
        if tag in {"Municipality", "Province"}:
            # Province/Municipality are broad native tags. Only unambiguous
            # administrative prefixes in the predicted group establish level.
            for pattern, target in ADMIN_PREFIXES:
                if pattern.match(literal):
                    label, reason = target, "explicit_surface_admin_prefix"
                    break
            interior = re.search(r"\s(?:phường|xã|quận|huyện|tỉnh)\s", literal, re.I)
            if label and interior:
                label, reason = None, "REJECT_MULTIPLE_ADMIN_UNITS_IN_NATIVE_GROUP"
        mapping_log.append({"start": start, "end": end, "native_tag": tag, "schema_label": label, "reason": reason})
        if label:
            spans.append(CharacterSpan(start, end, label, literal, "cu" if label == "QuanHuyen" else "khong_xac_dinh"))
    return spans, mapping_log


class DeepparseFastTextAdapter(BaseAddressParser, BaseSpanAddressParser):
    def __init__(self, cache_dir: str, device: str = "cpu", offline: bool = True):
        from deepparse.parser import AddressParser
        self.parser = AddressParser(model_type="fasttext", device=device, cache_dir=cache_dir,
                                    offline=offline, verbose=False)

    @property
    def tool_name(self) -> str:
        return "DP-ZS-FT"

    def parse_spans(self, raw_address: str, sample_id: str = "", **kwargs) -> SpanModelOutput:
        started = time.perf_counter()
        parsed = self.parser(raw_address, with_prob=False, num_workers=0, with_hyphen_split=False)
        components = list(parsed.address_parsed_components)
        raw_output = {"parser_raw_address": parsed.raw_address, "native_tokens": components,
                      "native_fields": parsed.to_dict()}
        try:
            spans, mapping_log = map_native_output(raw_address, components)
        except ValueError as exc:
            return SpanModelOutput(sample_id, raw_address, abstain=True, status="abstain", raw_output=raw_output,
                                   error=str(exc), trace={"alignment": "REJECTED", "mapping_version": MAPPING_VERSION})
        return SpanModelOutput(sample_id, raw_address, spans, abstain=not bool(spans),
            latency_ms=(time.perf_counter()-started)*1000, raw_output=raw_output,
            trace={"alignment": "ORDERED_EXACT_ROUND_TRIP", "mapping_version": MAPPING_VERSION,
                   "mapping_log": mapping_log, "t1": "NOT_IMPLEMENTED", "fine_tuned": False})

    def parse(self, raw_address: str, **kwargs):
        output = self.parse_spans(raw_address)
        return output.to_standard_5_fields(), output.to_dict()
