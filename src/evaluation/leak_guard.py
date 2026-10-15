"""Leakage guard for experiments that draw on benchmark data (Data 01/03/04/06).

Two protections shared by Group 1 experiments:

* text overlap: a benchmark row whose normalised text equals any Sprint 3
  corpus text (train, dev or test) must not be used for training or evaluation;
* administrative grouping: rows are split by the connected component of the
  old/new mapping graph so one territory never appears on both sides.

Everything here reads the frozen corpus; nothing is written back to it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import unicodedata
import weakref

import pandas as pd

from src.data.administrative_alias import (
    resolve_district_alias,
    resolve_province_alias,
    resolve_ward_alias,
)
from src.data.administrative_mapping import (
    AdministrativeMapping,
    clean_value,
    default_mapping_path,
    load_administrative_mapping,
    province_key,
    unit_key,
)

RULE_VERSION = "leak-guard-v1"
SPLIT_FILES = {
    "train": "train.jsonl",
    "dev": "dev.jsonl",
    "test": "test_benchmark_t0.jsonl",
}
REGISTRY_FILE = "identity_registry.jsonl"
DEFAULT_CORPUS_DIR = Path("data/processed/annotation/sprint03/corpus_v1_release2")

REASON_EXACT = "TRUNG_CHUOI_CHINH_XAC"
REASON_NORMALIZED = "TRUNG_SAU_CHUAN_HOA"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_for_overlap(text: object) -> str:
    """NFC, casefold, punctuation/symbols removed, whitespace collapsed.

    Diacritics are kept on purpose: removing them would merge distinct
    Vietnamese names and report overlap that does not exist.
    """
    value = unicodedata.normalize("NFC", "" if text is None else str(text)).casefold()
    value = "".join(
        " " if unicodedata.category(char)[0] in "PS" else char for char in value
    )
    return " ".join(value.split())


@dataclass(frozen=True)
class CorpusEntry:
    split: str
    sample_id: str
    source_group: str
    raw_text: str


@dataclass
class ExclusionIndex:
    """Normalised text -> corpus entries, plus source groups per split."""

    by_text: dict[str, list[CorpusEntry]] = field(default_factory=dict)
    groups_by_split: dict[str, set[str]] = field(default_factory=dict)
    splits: tuple[str, ...] = ()
    corpus_sha256: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_records(
        cls, records_by_split: dict[str, list[dict]], splits: tuple[str, ...] | None = None
    ) -> "ExclusionIndex":
        """Build an index from in-memory records (``text``, ``sample_id``, ``source_group``)."""
        chosen = tuple(splits) if splits is not None else tuple(records_by_split)
        unknown = [name for name in chosen if name not in records_by_split]
        if unknown:
            raise ValueError(f"unknown splits {unknown}; available {sorted(records_by_split)}")
        index = cls(splits=chosen)
        for split in chosen:
            groups = index.groups_by_split.setdefault(split, set())
            for record in records_by_split[split]:
                entry = CorpusEntry(
                    split=split,
                    sample_id=str(record.get("sample_id", "")),
                    source_group=str(record.get("source_group", "")),
                    raw_text=str(record["text"]),
                )
                index.by_text.setdefault(normalize_for_overlap(entry.raw_text), []).append(entry)
                if entry.source_group:
                    groups.add(entry.source_group)
        return index

    def lookup(self, text: object) -> list[CorpusEntry]:
        return self.by_text.get(normalize_for_overlap(text), [])

    def exact_raw_texts(self) -> set[str]:
        return {entry.raw_text for entries in self.by_text.values() for entry in entries}


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_corpus_records(corpus_dir: Path | None = None) -> tuple[dict[str, list[dict]], dict[str, str]]:
    """Load train/dev/test and verify every file against ``manifest.json`` first."""
    base = Path(corpus_dir) if corpus_dir is not None else _repo_root() / DEFAULT_CORPUS_DIR
    manifest_path = base / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)
    expected = json.loads(manifest_path.read_text(encoding="utf-8"))["output_sha256"]
    needed = list(SPLIT_FILES.values()) + [REGISTRY_FILE]
    observed: dict[str, str] = {}
    for name in needed:
        path = base / name
        if not path.exists():
            raise FileNotFoundError(path)
        if name not in expected:
            raise ValueError(f"{name} is not listed in {manifest_path.name}")
        observed[name] = sha256_file(path)
        if observed[name] != expected[name]:
            raise ValueError(f"HASH_MISMATCH {name}: manifest {expected[name]} != file {observed[name]}")

    records = {split: _read_jsonl(base / name) for split, name in SPLIT_FILES.items()}
    registry = {row["sample_id"]: row for row in _read_jsonl(base / REGISTRY_FILE)}
    for split, rows in records.items():
        for row in rows:
            reg = registry.get(row["sample_id"])
            if reg is None or reg["split"] != split:
                raise ValueError(f"{row['sample_id']} missing from identity registry or wrong split")
            if reg["text_sha256"] != hashlib.sha256(row["text"].encode("utf-8")).hexdigest():
                raise ValueError(f"{row['sample_id']} text hash differs from identity registry")
            # The registry is the source of truth for group identity.
            row["source_group"] = reg["source_group"]
    return records, observed


def build_exclusion_index(
    splits: tuple[str, ...] = ("train", "dev", "test"), corpus_dir: Path | None = None
) -> ExclusionIndex:
    records, observed = load_corpus_records(corpus_dir)
    index = ExclusionIndex.from_records(records, splits)
    index.corpus_sha256 = observed
    return index


def filter_benchmark(
    frame: pd.DataFrame,
    text_column: str,
    splits: tuple[str, ...] = ("train", "dev", "test"),
    index: ExclusionIndex | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return ``(kept, dropped)``; ``dropped`` carries reason and offending split.

    A row is dropped when its normalised text equals a corpus text in any of
    ``splits``.  Added columns on ``dropped``: ``LyDoLoai`` (exact raw match or
    match only after normalisation), ``SplitGayTrung``, ``SampleIdGayTrung``
    and ``KhoaChuanHoa``.  Row order and index of ``frame`` are preserved.
    """
    if text_column not in frame.columns:
        raise ValueError(f"missing text column {text_column!r}")
    active = index if index is not None else build_exclusion_index(splits)
    wanted = tuple(splits)
    missing = [name for name in wanted if name not in active.splits]
    if missing:
        raise ValueError(f"index was built without splits {missing}")

    reasons, hit_splits, hit_ids, keys = [], [], [], []
    is_dropped = []
    for text in frame[text_column].tolist():
        key = normalize_for_overlap(text)
        entries = [e for e in active.by_text.get(key, []) if e.split in wanted]
        is_dropped.append(bool(entries))
        if entries:
            exact = any(e.raw_text == text for e in entries)
            reasons.append(REASON_EXACT if exact else REASON_NORMALIZED)
            hit_splits.append("|".join(sorted({e.split for e in entries})))
            hit_ids.append("|".join(sorted({e.sample_id for e in entries})))
            keys.append(key)
    mask = pd.Series(is_dropped, index=frame.index)
    kept = frame.loc[~mask].copy()
    dropped = frame.loc[mask].copy()
    dropped["LyDoLoai"] = reasons
    dropped["SplitGayTrung"] = hit_splits
    dropped["SampleIdGayTrung"] = hit_ids
    dropped["KhoaChuanHoa"] = keys
    return kept, dropped


# ---------------------------------------------------------------------------
# Administrative grouping
# ---------------------------------------------------------------------------

_COMPONENT_CACHE: "weakref.WeakKeyDictionary[AdministrativeMapping, dict[tuple, str]]" = weakref.WeakKeyDictionary()


def _components(mapping: AdministrativeMapping) -> dict[tuple, str]:
    """Map every old/new unit node to its connected-component label.

    One old ward may feed several new wards (and vice versa), so grouping by a
    single ward name would leave territory shared across groups.  Connected
    components of the full edge graph are the smallest unit that is disjoint
    on both sides of the reform.  Label = smallest node of the component.
    """
    cached = _COMPONENT_CACHE.get(mapping)
    if cached is not None:
        return cached
    parent: dict[tuple, tuple] = {}

    def find(node: tuple) -> tuple:
        parent.setdefault(node, node)
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for old, targets in mapping.old_to_new.items():
        for target in targets:
            a, b = find(("old",) + old), find(("new",) + mapping.new_key(target.province, target.ward))
            if a != b:
                parent[max(a, b)] = min(a, b)
    labels = {node: "|".join(find(node)[1:]) for node in list(parent)}
    _COMPONENT_CACHE[mapping] = labels
    return labels


_DEFAULT_MAPPING: AdministrativeMapping | None = None


def _default_mapping() -> AdministrativeMapping:
    global _DEFAULT_MAPPING
    if _DEFAULT_MAPPING is None:
        _DEFAULT_MAPPING = load_administrative_mapping(default_mapping_path())
    return _DEFAULT_MAPPING


def admin_group_key(
    province: object,
    district: object,
    ward: object,
    mapping: AdministrativeMapping | None = None,
) -> str:
    """Group key for disjoint splits; old and new forms of one territory agree.

    Lookup order: a full old key (province + district + ward) when a district
    is given, then a new key (province + ward).  A hybrid address (new ward,
    old district) therefore falls through to the new-ward lookup.  Names that
    resolve in neither system get a ``UNRESOLVED`` key built from the
    normalised text, so identical unresolved units still share a group.
    """
    active = mapping if mapping is not None else _default_mapping()
    labels = _components(active)
    district_text, ward_text = clean_value(district), clean_value(ward)
    raw = (province, district_text, ward_text)
    # Verified aliases (administrative_alias.py) are tried only after the exact
    # spelling fails; no alias is invented here.
    aliased = (
        resolve_province_alias(province),
        resolve_district_alias(district_text),
        resolve_ward_alias(ward_text),
    )
    for prov, dist, wrd in (raw, aliased):
        if dist:
            node = ("old",) + active.old_key(prov, dist, wrd)
            if node in labels:
                return "ADM|" + labels[node]
        canonical = active.resolve_new_province(prov)
        if canonical and wrd:
            node = ("new",) + active.new_key(canonical, wrd)
            if node in labels:
                return "ADM|" + labels[node]
    return "UNRESOLVED|" + "|".join(
        (province_key(province), unit_key(district_text), unit_key(ward_text))
    )
