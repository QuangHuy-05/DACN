"""Text-only alignment; gold is attached only after the token stream is fixed."""

from dataclasses import asdict, dataclass, field
import hashlib
import unicodedata

from src.evaluation.schema import CharacterSpan
from src.evaluation.span_features import Token, tokenize, BIO_LABELS, decode_bio

RAW_PROCESSOR_VERSION = "word_punct_raw_v1"
DP_PROCESSOR_VERSION = "dp_surface_bio_v1"
PHOBERT_PROCESSOR_VERSION = "phobert_raw_unit_pool_v2_tone_relocation"

_VIETNAMESE_TONE_MARKS = frozenset("\u0300\u0301\u0303\u0309\u0323")
_TONE_MARK_NAMES = {"\u0300": "grave", "\u0301": "acute", "\u0303": "tilde",
                    "\u0309": "hook_above", "\u0323": "dot_below"}
_VIETNAMESE_VOWELS = frozenset("aăâeêioôơuưy")


@dataclass
class Alignment:
    raw_text: str
    processor_version: str
    units: list[Token]
    model_tokens: list[str] = field(default_factory=list)
    model_offsets: list[tuple[int, int]] = field(default_factory=list)
    input_ids: list[int] = field(default_factory=list)
    special_mask: list[bool] = field(default_factory=list)
    unit_to_model: list[list[int]] = field(default_factory=list)
    prepared_text: str = ""
    diagnostics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        value = asdict(self)
        value["text_sha256"] = hashlib.sha256(self.raw_text.encode("utf-8")).hexdigest()
        value["prediction_unit_mask"] = [True] * len(self.units)
        return value


def align_text(text: str) -> Alignment:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("EMPTY_TEXT: nonempty original text required")
    units = tokenize(text)
    if not units:
        raise ValueError("EMPTY_UNITS")
    return Alignment(text, RAW_PROCESSOR_VERSION, units)


def encode_gold(alignment: Alignment, spans: list[dict]) -> list[str]:
    text, units = alignment.raw_text, alignment.units
    tags, previous_end = ["O"] * len(units), -1
    for span in sorted(spans, key=lambda item: (item["start"], item["end"])):
        start, end, label = span["start"], span["end"], span["label"]
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
            raise ValueError("INVALID_GOLD_OFFSET")
        if "B-" + label not in BIO_LABELS or start < previous_end:
            raise ValueError("INVALID_GOLD_LABEL_OR_OVERLAP")
        if span.get("text", text[start:end]) != text[start:end]:
            raise ValueError("GOLD_SUBSTRING_MISMATCH")
        indices = [i for i, unit in enumerate(units) if unit.start < end and unit.end > start]
        if not indices or units[indices[0]].start != start or units[indices[-1]].end != end:
            raise ValueError("UNREPRESENTABLE_GOLD_BOUNDARY")
        for offset, index in enumerate(indices):
            tags[index] = ("B-" if offset == 0 else "I-") + label
        previous_end = end
    decoded, repairs = decode_bio(text, units, tags)
    if repairs or {(s.start, s.end, s.label) for s in decoded} != {
            (s["start"], s["end"], s["label"]) for s in spans}:
        raise ValueError("GOLD_ROUND_TRIP_FAILED")
    return tags


def decode_tags(alignment: Alignment, tags: list[str], allow_repairs: bool = False
                ) -> tuple[list[CharacterSpan], list[dict]]:
    spans, repairs = decode_bio(alignment.raw_text, alignment.units, tags)
    if repairs and not allow_repairs:
        raise ValueError("ILLEGAL_BIO_PATH")
    return spans, repairs


def identity_preprocessor(address: str) -> str:
    """Override Deepparse comma-removal; its mandatory lowercase remains enabled."""
    return address


class DeepparseProcessor:
    version = DP_PROCESSOR_VERSION

    def align_text(self, text: str) -> Alignment:
        alignment = align_text(text)
        words = [unit.text.lower() for unit in alignment.units]
        if any(len(word) != len(unit.text) for word, unit in zip(words, alignment.units)):
            raise ValueError("LOWERCASE_LENGTH_CHANGED")
        alignment.processor_version = self.version
        alignment.model_tokens = words
        alignment.model_offsets = [(unit.start, unit.end) for unit in alignment.units]
        alignment.prepared_text = " ".join(words)
        alignment.unit_to_model = [[i] for i in range(len(words))]
        return alignment

    def decode(self, alignment: Alignment, native: list) -> tuple[list[CharacterSpan], list[dict]]:
        if len(native) != len(alignment.units):
            raise ValueError("NATIVE_COUNT_OR_EARLY_EOS")
        tags = []
        for expected, pair in zip(alignment.model_tokens, native):
            if len(pair) != 2 or pair[0] != expected:
                raise ValueError("NATIVE_TOKEN_MISMATCH")
            tag = pair[1][0] if isinstance(pair[1], (tuple, list)) else pair[1]
            if tag not in BIO_LABELS:
                raise ValueError("UNKNOWN_NATIVE_TAG_OR_EOS")
            tags.append(tag)
        return decode_tags(alignment, tags, allow_repairs=True)


def _normalized_stream(text: str) -> tuple[str, list[tuple[int, int]]]:
    chars, offsets, index = [], [], 0
    while index < len(text):
        end = index + 1
        while end < len(text) and unicodedata.combining(text[end]):
            end += 1
        cluster = unicodedata.normalize("NFC", text[index:end])
        for char in cluster:
            if not char.isspace():
                chars.append(char)
                offsets.append((index, end))
        index = end
    return "".join(chars), offsets


def _alignment_char_key(char: str) -> tuple[str, tuple[str, ...]]:
    """Compare a letter's base/quality marks while treating tone separately."""
    decomposed = unicodedata.normalize("NFD", char)
    bases = [value for value in decomposed if not unicodedata.combining(value)]
    if len(bases) != 1:
        return decomposed, ()
    quality_marks = tuple(sorted(value for value in decomposed
                                 if unicodedata.combining(value) and value not in _VIETNAMESE_TONE_MARKS))
    return bases[0], quality_marks


def _tone_marks(char: str) -> tuple[str, ...]:
    return tuple(sorted(value for value in unicodedata.normalize("NFD", char)
                        if value in _VIETNAMESE_TONE_MARKS))


def _tone_relocation_is_safe(word: str, source_indices: tuple[int | None, ...],
                             stream: str, positions: list[tuple[int, int]], raw_text: str) -> bool:
    """Allow tone placement changes only within one contiguous vowel nucleus."""
    source_group, target_group = [], []
    previous_source = None

    def group_matches() -> bool:
        return sorted(source_group) == sorted(target_group)

    for char, source_index in zip(word, source_indices):
        if char == "_" or source_index is None:
            if not group_matches():
                return False
            source_group.clear()
            target_group.clear()
            previous_source = None
            continue

        if previous_source is not None:
            previous_end = positions[previous_source][1]
            next_start = positions[source_index][0]
            if raw_text[previous_end:next_start].isspace():
                if not group_matches():
                    return False
                source_group.clear()
                target_group.clear()

        source_char = stream[source_index]
        source_base = _alignment_char_key(source_char)[0]
        target_base = _alignment_char_key(char)[0]
        source_tones, target_tones = _tone_marks(source_char), _tone_marks(char)
        if source_tones and source_base.casefold() not in _VIETNAMESE_VOWELS:
            return False
        if target_tones and target_base.casefold() not in _VIETNAMESE_VOWELS:
            return False
        if (not source_base.isalpha() or not target_base.isalpha() or
                source_base.casefold() not in _VIETNAMESE_VOWELS or
                target_base.casefold() not in _VIETNAMESE_VOWELS):
            if not group_matches():
                return False
            source_group.clear()
            target_group.clear()
            previous_source = source_index
            continue
        source_group.extend(source_tones)
        target_group.extend(target_tones)
        previous_source = source_index
    return group_matches()


def _segmented_word_maps(text: str, words: list[str]) -> tuple[list[list[tuple[int, int]]], list[dict]]:
    stream, positions = _normalized_stream(text)
    cursor, mappings, tone_relocations = 0, [], []
    for word_index, word in enumerate(words):
        if unicodedata.normalize("NFC", word) != word:
            raise ValueError("SEGMENTER_OUTPUT_NOT_NFC")
        # Literal underscores are distinct from the segmenter's inserted separators.
        states = {(cursor, (), ())}
        for char in word:
            following = set()
            for point, mapping, source_indices in states:
                if point < len(stream) and _alignment_char_key(stream[point]) == _alignment_char_key(char):
                    following.add((point + 1, mapping + (positions[point],), source_indices + (point,)))
                if char == "_" and cursor < point < len(stream):
                    previous_end, next_start = positions[point - 1][1], positions[point][0]
                    # Inserted separators must correspond to original whitespace.
                    if text[previous_end:next_start] and text[previous_end:next_start].isspace():
                        following.add((point, mapping + ((previous_end, previous_end),), source_indices + (None,)))
            states = following
        before_tone_validation = states
        states = {state for state in states
                  if _tone_relocation_is_safe(word, state[2], stream, positions, text)}
        if before_tone_validation and not states:
            raise ValueError("SEGMENTER_CHANGED_TONE_OR_MOVED_TONE_ACROSS_SYLLABLE")
        unique = {(point - cursor, mapping, source_indices)
                  for point, mapping, source_indices in states}
        if len(unique) != 1:
            raise ValueError("SEGMENTER_TEXT_CHANGED_OR_AMBIGUOUS_UNDERSCORE")
        count, mapping, source_indices = unique.pop()
        mappings.append(list(mapping))
        for char_index, (char, source_index) in enumerate(zip(word, source_indices)):
            if source_index is None:
                continue
            source_tones, target_tones = _tone_marks(stream[source_index]), _tone_marks(char)
            if source_tones != target_tones:
                tone_relocations.append({"word_index": word_index, "char_index": char_index,
                                         "raw_offset": list(positions[source_index]),
                                         "source_tone_marks": [_TONE_MARK_NAMES[value] for value in source_tones],
                                         "segmenter_tone_marks": [_TONE_MARK_NAMES[value] for value in target_tones]})
        cursor += count
    if cursor != len(stream):
        raise ValueError("SEGMENTER_DROPPED_TEXT")
    return mappings, tone_relocations


class PhoBERTProcessor:
    version = PHOBERT_PROCESSOR_VERSION

    def __init__(self, tokenizer, segmenter, max_encoder_tokens: int):
        self.tokenizer, self.segmenter = tokenizer, segmenter
        self.max_encoder_tokens = max_encoder_tokens

    def align_text(self, text: str) -> Alignment:
        alignment = align_text(text)
        # NFC is reversible through _normalized_stream's original cluster offsets.
        segmented = self.segmenter.word_segment(unicodedata.normalize("NFC", text))
        if not isinstance(segmented, list) or any(not isinstance(item, str) for item in segmented):
            raise ValueError("SEGMENTER_API_MISMATCH")
        words = " ".join(segmented).split()
        word_maps, tone_relocations = _segmented_word_maps(text, words)
        pieces, spans = [], []
        for word, mapping in zip(words, word_maps):
            subwords = self.tokenizer.tokenize(word)
            if subwords == [getattr(self.tokenizer, "unk_token", "<unk>")]:
                subwords_raw = [word]
            else:
                subwords_raw = [piece[:-2] if piece.endswith("@@") else piece for piece in subwords]
            if not subwords or "".join(subwords_raw) != word:
                raise ValueError("SUBWORD_RECONSTRUCTION_FAILED")
            offset = 0
            for piece, literal in zip(subwords, subwords_raw):
                refs = [interval for interval in mapping[offset:offset + len(literal)] if interval[0] < interval[1]]
                point = mapping[offset][0] if offset < len(mapping) else len(text)
                spans.append((min(s for s, _ in refs), max(e for _, e in refs)) if refs else (point, point))
                pieces.append(piece)
                offset += len(literal)
        ids = self.tokenizer.convert_tokens_to_ids(pieces)
        built = self.tokenizer.build_inputs_with_special_tokens(ids)
        special = self.tokenizer.get_special_tokens_mask(ids, already_has_special_tokens=False)
        if len(built) != len(special) or sum(not value for value in special) != len(pieces):
            raise ValueError("SPECIAL_TOKEN_MAPPING_FAILED")
        if len(built) > self.max_encoder_tokens:
            raise ValueError("ENCODER_TOO_LONG: truncation is disabled")
        iterator = iter(zip(pieces, spans))
        model_tokens, model_offsets = [], []
        for flag, token_id in zip(special, built):
            piece, interval = (f"special:{token_id}", (-1, -1)) if flag else next(iterator)
            model_tokens.append(piece)
            model_offsets.append(interval)
        unit_to_model = [[i for i, (start, end) in enumerate(model_offsets)
                          if not special[i] and start < unit.end and end > unit.start]
                         for unit in alignment.units]
        if any(not indices for indices in unit_to_model):
            raise ValueError("RAW_UNIT_WITHOUT_ENCODER_EMBEDDING")
        alignment.processor_version = self.version
        alignment.model_tokens, alignment.model_offsets = model_tokens, model_offsets
        alignment.input_ids, alignment.special_mask = built, [bool(v) for v in special]
        alignment.unit_to_model, alignment.prepared_text = unit_to_model, " ".join(words)
        alignment.diagnostics = {"pooling": "mean_over_overlapping_subwords",
                                 "prediction_units": "raw_surface_tokens",
                                 "segmenter_input": "NFC; original text is retained",
                                 "unicode_compare": "NFC; original offsets retained",
                                 "tone_relocation_policy": "same_base_and_quality_marks; same_tone_multiset_per_vowel_nucleus_v1",
                                 "tone_relocation_count": len(tone_relocations),
                                 "tone_relocations": tone_relocations}
        return alignment
