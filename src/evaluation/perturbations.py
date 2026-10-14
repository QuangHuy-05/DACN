"""Text perturbations with exact offset bookkeeping (WP4: H3 field order, E1 comma/case).

Standard library only, so the CRF runtime (no numpy/pandas) can import it.  Every function returns the
new text together with spans whose offsets were recomputed; callers must still check ``verify_surfaces``.
"""

from __future__ import annotations

import random
import re

SEPARATOR = ", "
_WHITESPACE = re.compile(r"\s")


def sorted_spans(spans: list[dict]) -> list[dict]:
    ordered = sorted(spans, key=lambda s: (s["start"], s["end"]))
    for previous, current in zip(ordered, ordered[1:]):
        if current["start"] < previous["end"]:
            raise ValueError("Overlapping gold spans cannot be recomposed")
    return ordered


def shuffle_permutation(n: int, seed: int, key: str) -> list[int]:
    """Deterministic permutation of range(n); the key (sample_id) keeps samples independent."""
    order = list(range(n))
    random.Random(f"{seed}|{key}").shuffle(order)
    return order


def recompose_with_order(text: str, spans: list[dict], order: str | list[int] = "original",
                         seed: int | None = None, key: str = "") -> tuple[str, list[dict], list[int]]:
    """Join the gold span surfaces with ', ' in a chosen order and recompute offsets.

    ``order``: "original" (control: only separators/outside text change), "reverse", "shuffle"
    (needs ``seed``; permutation depends on seed and ``key``), or an explicit permutation list.
    Returns (new_text, new_spans, permutation); the surface of every span is unchanged.
    """
    ordered = sorted_spans(spans)
    n = len(ordered)
    if order == "original":
        permutation = list(range(n))
    elif order == "reverse":
        permutation = list(range(n - 1, -1, -1))
    elif order == "shuffle":
        if seed is None:
            raise ValueError("shuffle needs a seed")
        permutation = shuffle_permutation(n, seed, key)
    elif isinstance(order, list) and sorted(order) == list(range(n)):
        permutation = list(order)
    else:
        raise ValueError(f"Unknown order {order!r}")
    new_text, new_spans = "", []
    for index in permutation:
        span = ordered[index]
        surface = text[span["start"]:span["end"]]
        if new_text:
            new_text += SEPARATOR
        start = len(new_text)
        new_text += surface
        new_spans.append({**span, "start": start, "end": len(new_text)})
    return new_text, new_spans, permutation


def verify_surfaces(old_text: str, old_spans: list[dict], new_text: str, new_spans: list[dict],
                    transform=lambda s: s) -> bool:
    """True when each new span's text equals ``transform`` of the matching old span's text (same label)."""
    if len(old_spans) != len(new_spans):
        return False
    by_label_old = sorted((s["label"], old_text[s["start"]:s["end"]]) for s in old_spans)
    by_label_new = sorted((s["label"], new_text[s["start"]:s["end"]]) for s in new_spans)
    return by_label_new == sorted((label, transform(surface)) for label, surface in by_label_old)


def drop_commas(text: str) -> tuple[str, list[int | None], list[int]]:
    """Replace every comma by a space, collapse whitespace runs, strip the ends.

    Returns (new_text, old_to_new, new_to_old).  ``old_to_new[i]`` is None for an old character that no
    longer exists (a comma/space merged into a neighbouring space or stripped away).
    """
    chars, origin = [], []
    for index, char in enumerate(text):
        chars.append(" " if char == "," else char)
        origin.append(index)
    kept_chars, kept_origin = [], []
    for char, index in zip(chars, origin):
        if _WHITESPACE.match(char):
            if not kept_chars or _WHITESPACE.match(kept_chars[-1]):
                continue
            kept_chars.append(" ")
        else:
            kept_chars.append(char)
        kept_origin.append(index)
    while kept_chars and kept_chars[-1] == " ":
        kept_chars.pop()
        kept_origin.pop()
    old_to_new: list[int | None] = [None] * len(text)
    for new_index, old_index in enumerate(kept_origin):
        old_to_new[old_index] = new_index
    return "".join(kept_chars), old_to_new, kept_origin


def _surface_without_commas(surface: str) -> str:
    return " ".join(surface.replace(",", " ").split())


def expected_surface(surface: str, *, no_commas: bool = False, lowercase: bool = False) -> str:
    """What a span surface must read after ``transform_sample`` with the same flags."""
    value = _surface_without_commas(surface) if no_commas else surface
    return value.lower() if lowercase else value


def transform_sample(text: str, spans: list[dict], *, no_commas: bool = False,
                     lowercase: bool = False) -> tuple[str, list[dict]]:
    """Apply the E1 preprocessing with reversible offset mapping; raises if a span boundary is lost."""
    if not no_commas and not lowercase:
        return text, [dict(s) for s in spans]
    new_text, new_spans = text, [dict(s) for s in spans]
    if no_commas:
        new_text, old_to_new, new_to_old = drop_commas(text)
        mapped = []
        for span in spans:
            first, last = old_to_new[span["start"]], old_to_new[span["end"] - 1]
            if first is None or last is None:
                raise ValueError("Span boundary character vanished while dropping commas")
            start, end = first, last + 1
            # Reversibility: mapping back must give the original boundaries.
            if new_to_old[start] != span["start"] or new_to_old[end - 1] != span["end"] - 1:
                raise ValueError("Offset mapping is not reversible")
            expected = _surface_without_commas(text[span["start"]:span["end"]])
            if new_text[start:end] != expected:
                raise ValueError("Span surface changed beyond comma removal")
            mapped.append({**span, "start": start, "end": end})
        new_spans = mapped
    if lowercase:
        lowered = new_text.lower()
        if len(lowered) != len(new_text):
            raise ValueError("str.lower changed the text length")
        new_text = lowered  # equal length, so offsets are unchanged
    return new_text, new_spans


def has_text_outside_spans(text: str, spans: list[dict]) -> bool:
    """True when the text is not exactly the span surfaces joined by ', ' in their original order."""
    return text != SEPARATOR.join(text[s["start"]:s["end"]] for s in sorted_spans(spans))
