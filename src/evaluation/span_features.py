"""Deterministic word/punctuation tokens and literal BIO alignment for CRF."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from src.evaluation.schema import CharacterSpan, SPAN11_LABELS

TOKENIZER_VERSION = "word_punct_raw_v1"
FEATURE_VERSION = "surface_context_v1"
FOLLOWUP_FEATURE_VERSION = "surface_admin_segment_cue_v2"
TOKEN_PATTERN = re.compile(r"\w+(?:[-/]\w+)*|[^\w\s]", re.UNICODE)
BIO_LABELS = ("O", *(f"{prefix}-{label}" for label in SPAN11_LABELS for prefix in ("B", "I")))


@dataclass(frozen=True)
class Token:
    text: str
    start: int
    end: int


def tokenize(text: str) -> list[Token]:
    return [Token(m.group(), m.start(), m.end()) for m in TOKEN_PATTERN.finditer(text)]


def encode_gold(text: str, spans: list[dict]) -> tuple[list[Token], list[str]]:
    tokens = tokenize(text)
    tags = ["O"] * len(tokens)
    previous_end = -1
    for span in sorted(spans, key=lambda item: (item["start"], item["end"])):
        start, end, label = span["start"], span["end"], span["label"]
        if label not in SPAN11_LABELS or not 0 <= start < end <= len(text) or start < previous_end:
            raise ValueError("Invalid or overlapping gold span")
        indices = [i for i, token in enumerate(tokens) if token.start < end and token.end > start]
        if not indices or tokens[indices[0]].start != start or tokens[indices[-1]].end != end:
            raise ValueError(f"Gold boundary crosses a tokenizer token: {start}:{end}")
        for offset, i in enumerate(indices):
            tags[i] = ("B-" if offset == 0 else "I-") + label
        previous_end = end
    decoded, repairs = decode_bio(text, tokens, tags)
    expected = {(s["start"], s["end"], s["label"]) for s in spans}
    if repairs or {(s.start, s.end, s.label) for s in decoded} != expected:
        raise ValueError("Gold BIO round-trip failed")
    return tokens, tags


def decode_bio(text: str, tokens: list[Token], tags: list[str]) -> tuple[list[CharacterSpan], list[dict]]:
    if len(tokens) != len(tags) or any(tag not in BIO_LABELS for tag in tags):
        raise ValueError("Invalid BIO sequence")
    spans, repairs = [], []
    active = None

    def close() -> None:
        nonlocal active
        if active is not None:
            start, end, label = active
            spans.append(CharacterSpan(start, end, label, text[start:end],
                                       "cu" if label == "QuanHuyen" else "khong_xac_dinh"))
        active = None

    for i, (token, tag) in enumerate(zip(tokens, tags)):
        if text[token.start:token.end] != token.text:
            raise ValueError("Token offsets do not refer to the original text")
        if tag == "O":
            close()
            continue
        prefix, label = tag.split("-", 1)
        # A learned CRFsuite transition can produce an illegal I. The fixed
        # decoder starts a B at that position and records every repair.
        if prefix == "I" and (active is None or active[2] != label):
            repairs.append({"token_index": i, "from": tag, "to": "B-" + label})
            prefix = "B"
        if prefix == "B":
            close()
            active = (token.start, token.end, label)
        else:
            active = (active[0], token.end, label)
    close()
    return spans, repairs


def _shape(value: str) -> str:
    return "".join("d" if c.isdigit() else "X" if c.isupper() else "x" if c.islower() else c for c in value)


def token_features(text: str, tokens: list[Token], context: int = 2, feature_version: str = FEATURE_VERSION) -> list[dict]:
    if context not in (1, 2):
        raise ValueError("Feature context must be 1 or 2")
    features = []
    if feature_version not in (FEATURE_VERSION, FOLLOWUP_FEATURE_VERSION):
        raise ValueError("UNKNOWN_CRF_FEATURE_VERSION")
    cue = "none"
    distance = 0
    for i, token in enumerate(tokens):
        word = unicodedata.normalize("NFC", token.text).casefold()
        if token.text in (",", ";", "(", ")") or (i and "\n" in text[tokens[i-1].end:token.start]):
            cue, distance = "none", 0
        if word in {"phường", "xã", "quận", "huyện", "tỉnh", "tp", "p", "q", "h", "x", "đường", "ngõ", "hẻm", "ngách"}:
            cue, distance = word, 0
        else:
            distance += 1
        item = {"bias": 1.0, "lower": word, "shape": _shape(token.text),
                "digit": token.text.isdigit(), "title": token.text.istitle(), "upper": token.text.isupper(),
                "has_digit": any(c.isdigit() for c in token.text), "has_slash": "/" in token.text,
                "has_dash": "-" in token.text, "punct": not any(c.isalnum() for c in token.text),
                "length": min(len(token.text), 20), "position_bucket": min(i, 8),
                "admin_prefix": word in {"phường", "xã", "quận", "huyện", "tỉnh", "tp", "p", "q", "h", "x"},
                "road_prefix": word in {"đường", "phố", "đ", "d"},
                "lane_prefix": word in {"ngõ", "ngách", "hẻm", "kiệt"}}
        for size in (1, 2, 3):
            item[f"prefix{size}"] = word[:size]
            item[f"suffix{size}"] = word[-size:]
        for delta in range(-context, context + 1):
            if delta == 0:
                continue
            j = i + delta
            if 0 <= j < len(tokens):
                neighbor = tokens[j].text
                item[f"{delta}:lower"] = unicodedata.normalize("NFC", neighbor).casefold()
                item[f"{delta}:shape"] = _shape(neighbor)
                item[f"{delta}:digit"] = neighbor.isdigit()
            else:
                item[f"{delta}:boundary"] = True
        if i:
            item["gap_before"] = text[tokens[i-1].end:token.start]
        if feature_version == FOLLOWUP_FEATURE_VERSION:
            item["segment_prefix_cue"] = cue
            item["tokens_since_cue"] = min(distance, 8)
            item["title_after_cue"] = token.text.istitle() and cue != "none"
            item["compound_unit_prefix"] = word in {"phố", "trấn", "khu"} and i > 0 and tokens[i-1].text.casefold() in {"thành", "thị", "đặc"}
        features.append(item)
    return features
