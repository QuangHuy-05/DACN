"""Offset-safe component rendering and matching for locked address text."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Component:
    field: str
    surface: str
    source_value: str
    construction_system: str
    transformation: str = "identity"


def render_components(components: list[Component], separator: str = ", ") -> tuple[str, list[dict]]:
    """Return text and half-open offsets from the same concatenation pass."""
    text = ""
    offsets = []
    for component in components:
        if not component.surface:
            continue
        if text:
            text += separator
        start = len(text)
        text += component.surface
        offsets.append({"component": component, "start": start, "end": len(text)})
    return text, offsets


def align_unique(text: str, components: list[Component]) -> tuple[list[dict], str | None]:
    """Accept one ordered, non-overlapping placement, or abstain entirely."""
    placements: list[list[dict]] = []

    def visit(index: int, cursor: int, selected: list[dict]) -> None:
        if len(placements) > 1:
            return
        if index == len(components):
            placements.append(selected)
            return
        component = components[index]
        start = text.find(component.surface, cursor)
        while start >= 0:
            end = start + len(component.surface)
            visit(index + 1, end, selected + [{"component": component, "start": start, "end": end}])
            start = text.find(component.surface, start + 1)

    visit(0, 0, [])
    if len(placements) != 1:
        return [], "ambiguous_or_missing_ordered_surface"
    return placements[0], None
