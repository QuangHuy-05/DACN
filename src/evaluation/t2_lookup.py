"""T2 baselines: two-way administrative-unit lookup over the atomic mapping graph.

The authoritative table is ``edges.csv`` of the NSO dual-snapshot gazetteer
(one row = old province + district + ward -> new province + ward).  Systems are
pure functions of *text fields*; gold labels never enter this module.

Administrative caveats kept explicit here:

* An old key always carries province, district and ward; ward names repeat
  across the country, so a ward alone is never a key (it is only allowed as a
  wildcard lookup when a model failed to emit the other spans).
* ``A/1-N`` is almost absent (3 edges); one old unit feeding several new units
  is in practice ``M/M-N``.  Relations are classified from graph degrees and
  never coerced.
* The five district -> special-zone transitions are not ward edges; they are
  reported as ``NON_ATOMIC`` and never guessed.
* Aliases come only from ``administrative_alias.py`` (level N2); no fuzzy match.

Heavy optional libraries (``vietnamadminunits``) are imported lazily and
``pycrfsuite``/``torch`` are never imported here.
"""

from __future__ import annotations

import csv
from contextlib import contextmanager
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
from statistics import mean, median
from typing import Iterable, Iterator, Sequence

from src.data.administrative_alias import (
    resolve_district_alias,
    resolve_province_alias,
    resolve_ward_alias,
)
from src.data.administrative_mapping import province_key, unit_key
from src.evaluation.leak_guard import normalize_for_overlap

RULE_VERSION = "t2-lookup-v1"
LEVELS = ("N0", "N1", "N2")
OLD_TO_NEW = "cu_to_moi"
NEW_TO_OLD = "moi_to_cu"

STRICT = "T2-LOOKUP-STRICT"
DEFAULT_MAIN = "T2-LOOKUP-DEFAULT-MAIN"
DEFAULT_FIRST = "T2-LOOKUP-DEFAULT-FIRST"
VNADMIN = "T2-VNADMIN"
SINGLE_VERSION = "T2-SINGLE-VERSION"
STREET = "T2-STREET"
LOOKUP_SYSTEMS = (STRICT, DEFAULT_MAIN, DEFAULT_FIRST)

# Preference when a default rule must pick among several targets.
MERGE_FORM_PRIORITY = {
    "Hợp nhất toàn bộ": 0,
    "Tách — nhập chủ yếu": 1,
    "Tách — một phần": 2,
}
UNKNOWN_PRIORITY = 99

REQUIRED_EDGE_COLUMNS = (
    "old_entity_id", "new_entity_id", "old_province", "old_district", "old_ward",
    "new_province", "new_ward", "new_ward_code", "relation", "merge_form", "source_row",
)
REQUIRED_NON_ATOMIC_COLUMNS = (
    "source_row", "old_entity_id", "new_entity_id", "old_province", "old_district",
    "new_province", "new_ward", "new_ward_code",
)
REQUIRED_ENTITY_COLUMNS = ("entity_id", "level", "system", "canonical_name", "parent_id")
HASHED_TABLE_FILES = ("edges.csv", "entities.csv", "aliases.csv", "non_atomic_transitions.csv")

REASON_NO_MATCH = "NO_MATCH"
REASON_AMBIGUOUS = "AMBIGUOUS"
REASON_NON_ATOMIC = "NON_ATOMIC"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# Graph primitives
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Edge:
    old_entity_id: str
    new_entity_id: str
    old_province: str
    old_district: str
    old_ward: str
    new_province: str
    new_ward: str
    new_ward_code: str
    relation: str  # single letter A/B/C/M
    merge_form: str
    source_row: int
    old_key: tuple[str, str, str] = ("", "", "")
    new_key: tuple[str, str] = ("", "")


def make_edge(
    old_entity_id: str, new_entity_id: str, old_province: str, old_district: str,
    old_ward: str, new_province: str, new_ward: str, new_ward_code: str,
    relation: str, merge_form: str, source_row: int,
) -> Edge:
    """Build an edge with N1 keys (same functions as ``administrative_mapping``)."""
    return Edge(
        old_entity_id, new_entity_id, old_province.strip(), old_district.strip(),
        old_ward.strip(), new_province.strip(), new_ward.strip(), new_ward_code.strip(),
        relation.split("/")[0].strip(), merge_form.strip(), int(source_row),
        old_key=(province_key(old_province), unit_key(old_district), unit_key(old_ward)),
        new_key=(province_key(new_province), unit_key(new_ward)),
    )


def classify_relations(edges: Sequence[Edge]) -> dict[int, str]:
    """Relation per ``source_row`` from graph degrees: C 1-1, B N-1, A 1-N, M M-N.

    Degrees count *distinct* neighbours so a duplicated row cannot turn 1-1
    into N-1.  M-N is never folded into A or B.
    """
    targets: dict[str, set[str]] = {}
    sources: dict[str, set[str]] = {}
    for edge in edges:
        targets.setdefault(edge.old_entity_id, set()).add(edge.new_entity_id)
        sources.setdefault(edge.new_entity_id, set()).add(edge.old_entity_id)
    labels = {}
    for edge in edges:
        out_degree, in_degree = len(targets[edge.old_entity_id]), len(sources[edge.new_entity_id])
        if out_degree == 1 and in_degree == 1:
            labels[edge.source_row] = "C"
        elif out_degree > 1 and in_degree == 1:
            labels[edge.source_row] = "A"
        elif out_degree == 1 and in_degree > 1:
            labels[edge.source_row] = "B"
        else:
            labels[edge.source_row] = "M"
    return labels


@dataclass(frozen=True)
class Candidate:
    side: str  # "new" or "old"
    cid: str  # entity id (stable internal id, not an official code)
    key: tuple
    province: str
    district: str
    ward: str
    code: str
    edges: tuple[Edge, ...] = ()

    def display(self) -> str:
        parts = [self.ward, self.district, self.province] if self.side == "old" else [self.ward, self.province]
        return ", ".join(part for part in parts if part)

    def first_rank(self) -> tuple[int, str]:
        return (min((e.source_row for e in self.edges), default=10**9), self.cid)

    def main_rank(self) -> tuple[int, int, str]:
        best = min(
            ((MERGE_FORM_PRIORITY.get(e.merge_form, UNKNOWN_PRIORITY), e.source_row) for e in self.edges),
            default=(UNKNOWN_PRIORITY, 10**9),
        )
        return (best[0], best[1], self.cid)


def group_candidates(edges: Iterable[Edge], side: str) -> list[Candidate]:
    """Distinct targets (side='new') or distinct sources (side='old') of edges."""
    grouped: dict[str, list[Edge]] = {}
    for edge in edges:
        grouped.setdefault(edge.new_entity_id if side == "new" else edge.old_entity_id, []).append(edge)
    result = []
    for cid, members in grouped.items():
        head = members[0]
        if side == "new":
            result.append(Candidate("new", cid, head.new_key, head.new_province, "", head.new_ward,
                                    head.new_ward_code, tuple(members)))
        else:
            result.append(Candidate("old", cid, head.old_key, head.old_province, head.old_district,
                                    head.old_ward, "", tuple(members)))
    return sorted(result, key=lambda c: (c.first_rank(), c.cid))


# ---------------------------------------------------------------------------
# Table loading
# ---------------------------------------------------------------------------

def read_csv_rows(path: Path, required: Sequence[str]) -> list[dict[str, str]]:
    if not Path(path).exists():
        raise FileNotFoundError(path)
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = [name for name in required if name not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: missing required columns {missing}")
        return list(reader)


def _alias_old(fields: tuple[str, str, str]) -> tuple[str, str, str]:
    province, district, ward = fields
    return (
        resolve_province_alias(province) if province else "",
        resolve_district_alias(district) if district else "",
        resolve_ward_alias(ward) if ward else "",
    )


def _alias_new(fields: tuple[str, str]) -> tuple[str, str]:
    province, ward = fields
    return (resolve_province_alias(province) if province else "", resolve_ward_alias(ward) if ward else "")


class T2Table:
    """Edge table with N0/N1/N2 matching on both sides."""

    def __init__(self, edges: Sequence[Edge], non_atomic: Sequence[dict[str, str]] = (),
                 source_hashes: dict[str, str] | None = None) -> None:
        self.edges = tuple(sorted(edges, key=lambda e: e.source_row))
        self.non_atomic = tuple(non_atomic)
        self.source_hashes = dict(source_hashes or {})
        self.relations = classify_relations(self.edges)

        self.new_province_by_key: dict[str, str] = {}
        self.old_to_new_province: dict[str, str] = {}
        self._old_bucket: dict[str, dict[str, list[Edge]]] = {"N0": {}, "N1": {}}
        self._new_bucket: dict[str, dict[str, list[Edge]]] = {"N0": {}, "N1": {}}
        for edge in self.edges:
            self.new_province_by_key.setdefault(edge.new_key[0], edge.new_province)
            known = self.old_to_new_province.setdefault(edge.old_key[0], edge.new_key[0])
            if known != edge.new_key[0]:
                raise ValueError(f"old province {edge.old_province!r} maps to several new provinces")
            self._old_bucket["N0"].setdefault(edge.old_ward, []).append(edge)
            self._old_bucket["N1"].setdefault(edge.old_key[2], []).append(edge)
            self._new_bucket["N0"].setdefault(edge.new_ward, []).append(edge)
            self._new_bucket["N1"].setdefault(edge.new_key[1], []).append(edge)
        self._non_atomic_old = {
            (province_key(r["old_province"]), unit_key(r["old_district"])): r for r in self.non_atomic
        }
        self._non_atomic_new = {
            (province_key(r["new_province"]), unit_key(r["new_ward"])): r for r in self.non_atomic
        }

    @classmethod
    def load(cls, gazetteer_dir: Path) -> "T2Table":
        base = Path(gazetteer_dir)
        manifest_path = base / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(manifest_path)
        expected = json.loads(manifest_path.read_text(encoding="utf-8"))["output_sha256"]
        observed = {}
        for name in HASHED_TABLE_FILES:
            path = base / name
            if not path.exists():
                raise FileNotFoundError(path)
            observed[name] = sha256_file(path)
            if expected.get(name) != observed[name]:
                raise ValueError(f"HASH_MISMATCH {name}: manifest {expected.get(name)} != file {observed[name]}")
        observed["manifest.json"] = sha256_file(manifest_path)
        rows = read_csv_rows(base / "edges.csv", REQUIRED_EDGE_COLUMNS)
        edges = [
            make_edge(r["old_entity_id"], r["new_entity_id"], r["old_province"], r["old_district"],
                      r["old_ward"], r["new_province"], r["new_ward"], r["new_ward_code"],
                      r["relation"], r["merge_form"], int(r["source_row"]))
            for r in rows
        ]
        non_atomic = read_csv_rows(base / "non_atomic_transitions.csv", REQUIRED_NON_ATOMIC_COLUMNS)
        table = cls(edges, non_atomic, observed)
        table.file_relations = {int(r["source_row"]): r["relation"].split("/")[0] for r in rows}
        return table

    # -- province canonicalisation ------------------------------------------------

    def _canonical_new_province(self, level: str, province: str) -> str | None:
        """New-province comparison key; N0 keeps the raw string."""
        if level == "N0":
            return province.strip() or None
        key = province_key(province)
        if key in self.new_province_by_key:
            return key
        return self.old_to_new_province.get(key)

    # -- matching -----------------------------------------------------------------

    @staticmethod
    def _variants(level: str, fields: tuple, alias_fn) -> Iterator[tuple[str, tuple]]:
        raw = tuple(str(f).strip() for f in fields)
        yield "raw", raw
        if level == "N2":
            aliased = alias_fn(raw)
            if aliased != raw:
                yield "alias", aliased

    def _match_old_once(self, level: str, province: str, district: str, ward: str) -> list[Edge]:
        if not ward:
            return []
        bucket_level = "N0" if level == "N0" else "N1"
        bucket = self._old_bucket[bucket_level].get(ward if level == "N0" else unit_key(ward), [])
        out = []
        for edge in bucket:
            if level == "N0":
                if province and edge.old_province != province:
                    continue
                if district and edge.old_district != district:
                    continue
            else:
                if province and edge.old_key[0] != province_key(province):
                    continue
                if district and edge.old_key[1] != unit_key(district):
                    continue
            out.append(edge)
        return out

    def match_old(self, level: str, province: str, district: str, ward: str) -> tuple[list[Edge], str]:
        """Edges whose old unit matches; empty fields are wildcards (ward is required)."""
        for variant, (p, d, w) in self._variants(level, (province, district, ward), _alias_old):
            found = self._match_old_once(level, p, d, w)
            if found:
                return found, variant
        return [], "none"

    def _match_new_once(self, level: str, province: str, ward: str) -> list[Edge]:
        if not ward:
            return []
        bucket_level = "N0" if level == "N0" else "N1"
        bucket = self._new_bucket[bucket_level].get(ward if level == "N0" else unit_key(ward), [])
        if not province:
            return list(bucket)
        wanted = self._canonical_new_province(level, province)
        if wanted is None:
            return []
        if level == "N0":
            return [e for e in bucket if e.new_province == wanted]
        return [e for e in bucket if e.new_key[0] == wanted]

    def match_new(self, level: str, province: str, ward: str) -> tuple[list[Edge], str]:
        for variant, (p, w) in self._variants(level, (province, ward), _alias_new):
            found = self._match_new_once(level, p, w)
            if found:
                return found, variant
        return [], "none"

    # -- candidate generation -------------------------------------------------------

    def old_to_new_candidates(self, level: str, province: str, district: str, ward: str):
        """Return ``(candidates, reason, info)``; ``reason`` is '' when candidates exist."""
        province, district, ward = province.strip(), district.strip(), ward.strip()
        info = {"variant": "none", "missing": [n for n, v in (("province", province), ("district", district),
                                                              ("ward", ward)) if not v]}
        if not ward:
            special = self._non_atomic_old.get((province_key(province), unit_key(district)))
            if special is not None and province and district:
                return [self._special_candidate(special)], REASON_NON_ATOMIC, info
            return [], REASON_NO_MATCH, info
        edges, variant = self.match_old(level, province, district, ward)
        info["variant"] = variant
        if not edges:
            return [], REASON_NO_MATCH, info
        return group_candidates(edges, "new"), "", info

    def new_to_old_candidates(self, level: str, province: str, ward: str):
        province, ward = province.strip(), ward.strip()
        info = {"variant": "none", "missing": [n for n, v in (("province", province), ("ward", ward)) if not v]}
        if not ward:
            return [], REASON_NO_MATCH, info
        edges, variant = self.match_new(level, province, ward)
        info["variant"] = variant
        if edges:
            return group_candidates(edges, "old"), "", info
        special = self._non_atomic_new.get((province_key(province), unit_key(ward)))
        if special is None and level != "N0":
            special = self._non_atomic_new.get((province_key(resolve_province_alias(province)), unit_key(ward)))
        if special is not None:
            return [self._special_candidate(special, side="old")], REASON_NON_ATOMIC, info
        return [], REASON_NO_MATCH, info

    @staticmethod
    def _special_candidate(row: dict[str, str], side: str = "new") -> Candidate:
        if side == "new":
            key = (province_key(row["new_province"]), unit_key(row["new_ward"]))
            return Candidate("new", row["new_entity_id"], key, row["new_province"], "", row["new_ward"],
                             row["new_ward_code"])
        key = (province_key(row["old_province"]), unit_key(row["old_district"]), "")
        return Candidate("old", row["old_entity_id"], key, row["old_province"], row["old_district"], "", "")

    def unique_old_units(self) -> int:
        return len({e.old_entity_id for e in self.edges})

    def unique_new_units(self) -> int:
        return len({e.new_entity_id for e in self.edges})


# ---------------------------------------------------------------------------
# Resolution (what a system returns for one text query)
# ---------------------------------------------------------------------------

@dataclass
class Resolution:
    system: str
    status: str  # ANSWER | ABSTAIN
    reason: str  # '', AMBIGUOUS, NO_MATCH, NON_ATOMIC or a rule tag
    candidates: list[Candidate] = field(default_factory=list)
    answer: Candidate | None = None
    warning: bool = False  # abstain / no-match are warned failures; answers are not
    flags: dict = field(default_factory=dict)

    @property
    def abstained(self) -> bool:
        return self.status == "ABSTAIN"


def choose_default(candidates: Sequence[Candidate], rule: str) -> Candidate:
    """Deterministic pick: ``main`` = merge-form priority then source row; ``first`` = source row."""
    if not candidates:
        raise ValueError("no candidates to choose from")
    if rule == "main":
        return min(candidates, key=lambda c: c.main_rank())
    if rule == "first":
        return min(candidates, key=lambda c: c.first_rank())
    raise ValueError(f"unknown default rule {rule!r}")


def apply_selection_rule(system: str, candidates: list[Candidate], reason: str, info: dict) -> Resolution:
    """Turn candidates into an answer according to a lookup system's rule."""
    if reason:  # NO_MATCH / NON_ATOMIC: failure with a warning for every lookup system
        return Resolution(system, "ABSTAIN", reason, candidates, None, True, dict(info))
    if system == STRICT:
        if len(candidates) == 1:
            return Resolution(system, "ANSWER", "OK_UNIQUE", candidates, candidates[0], False, dict(info))
        return Resolution(system, "ABSTAIN", REASON_AMBIGUOUS, candidates, None, True, dict(info))
    rule = {DEFAULT_MAIN: "main", DEFAULT_FIRST: "first"}.get(system)
    if rule is None:
        raise ValueError(f"not a lookup system: {system}")
    picked = choose_default(candidates, rule)
    tag = "OK_UNIQUE" if len(candidates) == 1 else f"DEFAULT_PICK_{rule.upper()}"
    return Resolution(system, "ANSWER", tag, candidates, picked, False, dict(info))


def resolve_lookup(table: T2Table, system: str, direction: str, level: str, fields: dict) -> Resolution:
    """T2-LOOKUP-* on text fields: ``province``, ``district`` (old side only), ``ward``."""
    if direction == OLD_TO_NEW:
        cands, reason, info = table.old_to_new_candidates(
            level, fields.get("province", ""), fields.get("district", ""), fields.get("ward", ""))
    elif direction == NEW_TO_OLD:
        cands, reason, info = table.new_to_old_candidates(level, fields.get("province", ""), fields.get("ward", ""))
    else:
        raise ValueError(f"unknown direction {direction!r}")
    return apply_selection_rule(system, cands, reason, info)


def resolve_identity_new(table: T2Table, system: str, level: str, fields: dict) -> Resolution:
    """Treat the input as an already-new address: validate it as a new unit and return it."""
    edges, variant = table.match_new(level, fields.get("province", ""), fields.get("ward", ""))
    info = {"variant": variant, "assumption": "new"}
    if not edges:
        return Resolution(system, "ABSTAIN", REASON_NO_MATCH, [], None, True, info)
    return apply_selection_rule(system, group_candidates(edges, "new"), "", info)


# ---------------------------------------------------------------------------
# T2-SINGLE-VERSION: name lookup in one system, no notion of time
# ---------------------------------------------------------------------------

class SingleVersionIndex:
    """Ward names of the *target* system, indexed by (province, ward key)."""

    def __init__(self, entities: Sequence[dict[str, str]], table: T2Table) -> None:
        by_id = {e["entity_id"]: e for e in entities}
        self.table = table
        self.new_wards: dict[tuple[str, str], list[Candidate]] = {}
        self.old_wards: dict[tuple[str, str], list[Candidate]] = {}
        new_province_name = {pk: name for pk, name in table.new_province_by_key.items()}
        for entity in entities:
            if entity["level"] != "ward":
                continue
            if entity["system"] == "moi":
                province = by_id.get(entity["parent_id"])
                if province is None:
                    continue
                pkey = province_key(province["canonical_name"])
                cand = Candidate("new", entity["entity_id"], (pkey, unit_key(entity["canonical_name"])),
                                 province["canonical_name"], "", entity["canonical_name"], "")
                self.new_wards.setdefault((pkey, cand.key[1]), []).append(cand)
            elif entity["system"] == "cu":
                district = by_id.get(entity["parent_id"])
                province = by_id.get(district["parent_id"]) if district else None
                if district is None or province is None:
                    continue
                opk = province_key(province["canonical_name"])
                npk = table.old_to_new_province.get(opk)
                if npk is None:
                    continue
                cand = Candidate("old", entity["entity_id"],
                                 (opk, unit_key(district["canonical_name"]), unit_key(entity["canonical_name"])),
                                 province["canonical_name"], district["canonical_name"],
                                 entity["canonical_name"], "")
                self.old_wards.setdefault((npk, cand.key[2]), []).append(cand)
        self._new_province_names = new_province_name

    def _target_province_key(self, level: str, province: str) -> str | None:
        key = self.table._canonical_new_province("N1", province)
        if key is None and level == "N2":
            key = self.table._canonical_new_province("N1", resolve_province_alias(province))
        return key

    def resolve(self, direction: str, level: str, fields: dict) -> Resolution:
        province, ward = fields.get("province", "").strip(), fields.get("ward", "").strip()
        info = {"variant": "single_version"}
        pkey = self._target_province_key(level, province) if province else None
        if not ward or pkey is None:
            return Resolution(SINGLE_VERSION, "ABSTAIN", REASON_NO_MATCH, [], None, True, info)
        wards = [unit_key(ward)]
        if level == "N2":
            alias_key = unit_key(resolve_ward_alias(ward))
            if alias_key not in wards:
                wards.append(alias_key)
        pool = self.new_wards if direction == OLD_TO_NEW else self.old_wards
        found: list[Candidate] = []
        for wkey in wards:
            found = pool.get((pkey, wkey), [])
            if found:
                break
        if not found:
            return Resolution(SINGLE_VERSION, "ABSTAIN", REASON_NO_MATCH, [], None, True, info)
        if len(found) == 1:
            return Resolution(SINGLE_VERSION, "ANSWER", "NAME_EXISTS_IN_TARGET", list(found), found[0], False, info)
        return Resolution(SINGLE_VERSION, "ABSTAIN", REASON_AMBIGUOUS, list(found), None, True, info)

    def homonyms(self, direction: str, province_key_new: str, ward_key: str) -> list[Candidate]:
        pool = self.new_wards if direction == OLD_TO_NEW else self.old_wards
        return list(pool.get((province_key_new, ward_key), []))


def load_single_version_index(gazetteer_dir: Path, table: T2Table) -> SingleVersionIndex:
    return SingleVersionIndex(read_csv_rows(Path(gazetteer_dir) / "entities.csv", REQUIRED_ENTITY_COLUMNS), table)


# ---------------------------------------------------------------------------
# T2-STREET (E2): street evidence for choosing among several targets
# ---------------------------------------------------------------------------

_STREET_TYPE_PREFIX = re.compile(r"^(?:đường|phố)\s+")


def street_key(text: object) -> str:
    """Normalised street name; generic leading 'đường'/'phố' is dropped, lane markers are kept."""
    return _STREET_TYPE_PREFIX.sub("", normalize_for_overlap(text)).strip()


@dataclass
class StreetIndex:
    by_street: dict[str, set[tuple[str, str]]] = field(default_factory=dict)
    kept_texts: set[str] = field(default_factory=set)
    report: dict = field(default_factory=dict)

    def wards_for(self, street: object) -> set[tuple[str, str]]:
        return self.by_street.get(street_key(street), set())


def build_street_index(
    table: T2Table,
    data01_rows: Sequence[dict[str, str]],
    osm_rows: Sequence[dict[str, str]],
    exclude_texts: set[str],
    exclude_pairs: set[tuple[str, str]] | None,
    level: str = "N2",
) -> StreetIndex:
    """Street -> set of new-ward keys, with string-level leakage filters.

    No source has an OSM id, so leakage is controlled by text only:
    (i) rows whose normalised full address equals a Data 07 ``DiaChi_Moi`` are
    dropped; (ii) when ``exclude_pairs`` is given, rows sharing a (house number,
    ``street_key``) pair with any Data 07 address are dropped too.  Neighbours on the
    same street may still remain; that residual leakage cannot be removed here.
    """
    index = StreetIndex()
    counters = {
        "rows_in": 0, "no_street": 0, "no_unique_new_ward": 0,
        "dropped_text_overlap": 0, "dropped_pair_overlap": 0, "kept": 0,
    }
    per_source: dict[str, int] = {}

    def new_ward_of(row: dict[str, str], source: str) -> tuple[str, str] | None:
        province = (row.get("TinhThanh") or "").strip()
        if not province:
            return None
        values = [(row.get("PhuongXa") or "").strip()]
        if source == "osm":
            values.append((row.get("QuanHuyen") or "").strip())
        hits = []
        for value in values:
            if not value:
                continue
            edges, _ = table.match_new(level, province, value)
            if edges:
                hits.append(edges[0].new_key)
        # Accept only rows with exactly one value that is a known new ward.
        return hits[0] if len(hits) == 1 else None

    for source, rows in (("data01", data01_rows), ("osm", osm_rows)):
        for row in rows:
            counters["rows_in"] += 1
            street = street_key(row.get("TenDuong", ""))
            if not street:
                counters["no_street"] += 1
                continue
            ward_key = new_ward_of(row, source)
            if ward_key is None:
                counters["no_unique_new_ward"] += 1
                continue
            text = normalize_for_overlap(row.get("ChuoiDiaChi", ""))
            if text in exclude_texts:
                counters["dropped_text_overlap"] += 1
                continue
            if exclude_pairs is not None:
                # Same street normalisation as the index key, otherwise "Phố X" and "X" would evade the filter.
                pair = (normalize_for_overlap(row.get("SoNha", "")), street_key(row.get("TenDuong", "")))
                if pair in exclude_pairs:
                    counters["dropped_pair_overlap"] += 1
                    continue
            index.by_street.setdefault(street, set()).add(ward_key)
            index.kept_texts.add(text)
            counters["kept"] += 1
            per_source[source] = per_source.get(source, 0) + 1
    index.report = {
        **counters,
        "kept_by_source": per_source,
        "distinct_streets": len(index.by_street),
        "distinct_street_ward_pairs": sum(len(v) for v in index.by_street.values()),
        "strict_pair_filter": exclude_pairs is not None,
    }
    return index


def resolve_street(
    table: T2Table, street_index: StreetIndex, fallback: str, level: str, fields: dict, street: str,
) -> Resolution:
    """T2-STREET: use street evidence when several targets exist, else the default rule.

    ``fallback`` is ``main`` or ``first``.  Evidence is *decisive* only when the
    street index narrows the candidates to exactly one target.  Fallback rows
    carry ``fallback_used`` as an internal marker, not a user-facing warning.
    """
    system = STREET
    cands, reason, info = table.old_to_new_candidates(
        level, fields.get("province", ""), fields.get("district", ""), fields.get("ward", ""))
    if reason:
        return Resolution(system, "ABSTAIN", reason, cands, None, True, dict(info))
    flags = dict(info, fallback=fallback, multi_candidate=len(cands) > 1, evidence="not_needed",
                 fallback_used=False, street_present=bool(street_key(street)))
    if len(cands) == 1:
        return Resolution(system, "ANSWER", "OK_UNIQUE", cands, cands[0], False, flags)
    wanted = street_index.wards_for(street)
    narrowed = [c for c in cands if c.key in wanted]
    if len(narrowed) == 1:
        flags["evidence"] = "decisive"
        return Resolution(system, "ANSWER", "STREET_EVIDENCE", cands, narrowed[0], False, flags)
    pool = narrowed if 1 < len(narrowed) < len(cands) else cands
    flags["evidence"] = "narrowed_not_unique" if pool is narrowed else ("none" if not narrowed else "uninformative")
    flags["fallback_used"] = True
    return Resolution(system, "ANSWER", f"DEFAULT_PICK_{fallback.upper()}", cands,
                      choose_default(pool, fallback), False, flags)


# ---------------------------------------------------------------------------
# T2-VNADMIN with the network geocoder disabled
# ---------------------------------------------------------------------------

@contextmanager
def geocoder_disabled():
    """Replace the library's geocoder symbol by a stub returning ``None``.

    ``VietnamAdminUnitsAdapter`` wraps ``converter_2025.get_geo_location``;
    wrapping the stub keeps the trace (``geocoder_status == 'empty'``) while no
    request is ever made.  The original symbol is restored on exit.
    """
    from vietnamadminunits.converter import converter_2025 as module

    original = module.get_geo_location
    module.get_geo_location = lambda address: None
    try:
        yield module
    finally:
        module.get_geo_location = original


def run_vnadmin(addresses: Sequence[str]) -> list[dict]:
    """Convert old addresses with the library's default (geocoder-free) branch."""
    with geocoder_disabled():
        from src.evaluation.adapters.vnadmin_adapter import VietnamAdminUnitsAdapter

        adapter = VietnamAdminUnitsAdapter()
        outputs = []
        for address in addresses:
            prediction, raw = adapter.convert_to_2025(address)
            trace = raw.get("conversion_trace", {}) if isinstance(raw, dict) else {}
            outputs.append({
                "province": prediction.tinh_thanh,
                "ward": prediction.phuong_xa,
                "error": raw.get("error") if isinstance(raw, dict) else None,
                "selection_path": trace.get("selection_path", "unknown"),
                "geocoder_status": trace.get("geocoder_status", "unknown"),
                "candidate_count": trace.get("candidate_count"),
            })
    return outputs


def vnadmin_resolution(table: T2Table, output: dict) -> Resolution:
    """Map a library answer to a candidate in the edge table by (province, ward) key."""
    flags = {k: output.get(k) for k in ("selection_path", "geocoder_status", "candidate_count")}
    if output.get("error") or not output.get("ward"):
        return Resolution(VNADMIN, "ABSTAIN", "LIBRARY_EMPTY_OR_ERROR", [], None, True,
                          dict(flags, error=output.get("error")))
    key = (province_key(output.get("province", "")), unit_key(output["ward"]))
    edges = [e for e in table._new_bucket["N1"].get(key[1], []) if e.new_key == key]
    if not edges:
        # The library returned a name that is not a new ward of the table (kept as a silent wrong answer).
        cand = Candidate("new", f"unknown:{key[0]}|{key[1]}", key, output.get("province", ""), "",
                         output["ward"], "")
    else:
        cand = group_candidates(edges, "new")[0]
    return Resolution(VNADMIN, "ANSWER", "LIBRARY_ANSWER", [cand], cand, False, flags)


# ---------------------------------------------------------------------------
# Model spans -> lookup fields (pipeline condition)
# ---------------------------------------------------------------------------

def fields_from_spans(spans: Sequence[dict]) -> dict:
    """Rightmost PhuongXa / QuanHuyen / TinhThanh span text; absent level -> '' (wildcard).

    Administrative names sit at the right end of Vietnamese addresses, so with
    several spans of one label the rightmost is used (declared rule).
    """
    labels = {"PhuongXa": "ward", "QuanHuyen": "district", "TinhThanh": "province"}
    fields = {"province": "", "district": "", "ward": ""}
    for span in sorted(spans, key=lambda s: (s["start"], s["end"])):
        name = labels.get(span["label"])
        if name:
            fields[name] = str(span.get("text", "")).strip()
    return fields


# ---------------------------------------------------------------------------
# Graph analysis ("near-structural", not observed accuracy)
# ---------------------------------------------------------------------------

def _distribution(counts: Iterable[int]) -> dict[str, int]:
    tally: dict[int, int] = {}
    for value in counts:
        tally[value] = tally.get(value, 0) + 1
    return {str(k): tally[k] for k in sorted(tally)}


def graph_analysis(table: T2Table) -> dict:
    """Fan-out (old -> new), fan-in (new -> old) and deterministic share over all atomic edges."""
    targets: dict[str, set[str]] = {}
    sources: dict[str, set[str]] = {}
    relation_of_old: dict[str, set[str]] = {}
    for edge in table.edges:
        targets.setdefault(edge.old_entity_id, set()).add(edge.new_entity_id)
        sources.setdefault(edge.new_entity_id, set()).add(edge.old_entity_id)
    n_edges = len(table.edges)
    file_rel = getattr(table, "file_relations", None)
    mismatches = (
        sum(1 for row, rel in table.relations.items() if file_rel.get(row) != rel) if file_rel else None
    )
    by_relation = {}
    for letter in ("A", "B", "C", "M"):
        rows = [e for e in table.edges if table.relations[e.source_row] == letter]
        out_degrees = [len(targets[e.old_entity_id]) for e in rows]
        in_degrees = [len(sources[e.new_entity_id]) for e in rows]
        by_relation[letter] = {
            "edges": len(rows),
            "fan_out_per_edge": _distribution(out_degrees),
            "fan_in_per_edge": _distribution(in_degrees),
            "share_old_key_deterministic": (sum(1 for d in out_degrees if d == 1) / len(rows)) if rows else None,
            "share_new_key_deterministic": (sum(1 for d in in_degrees if d == 1) / len(rows)) if rows else None,
            "status": "OK" if rows else "NOT_EVALUABLE_NO_SUPPORT",
        }
    n_old, n_new = len(targets), len(sources)
    return {
        "label": "near-structural (counts over all atomic edges); not observed accuracy",
        "atomic_edges": n_edges,
        "old_units": n_old,
        "new_units": n_new,
        "relation_counts": {k: v["edges"] for k, v in by_relation.items()},
        "relation_label_mismatch_vs_file": mismatches,
        "fan_out_old_key": _distribution(len(v) for v in targets.values()),
        "fan_in_new_key": _distribution(len(v) for v in sources.values()),
        "old_keys_deterministic": sum(1 for v in targets.values() if len(v) == 1),
        "new_keys_deterministic": sum(1 for v in sources.values() if len(v) == 1),
        "share_old_keys_deterministic": sum(1 for v in targets.values() if len(v) == 1) / n_old,
        "share_new_keys_deterministic": sum(1 for v in sources.values() if len(v) == 1) / n_new,
        # Over a uniformly drawn edge, one fixed pick per key is right on at most one edge per key.
        "ceiling_deterministic_pick_old_to_new": n_old / n_edges,
        "ceiling_deterministic_pick_new_to_old": n_new / n_edges,
        "mean_fan_out": mean(len(v) for v in targets.values()),
        "median_fan_out": median(len(v) for v in targets.values()),
        "mean_fan_in": mean(len(v) for v in sources.values()),
        "median_fan_in": median(len(v) for v in sources.values()),
        "max_fan_in": max(len(v) for v in sources.values()),
        "by_relation": by_relation,
        "non_atomic_transitions": {
            "count": len(table.non_atomic),
            "rows": [
                {"old": f"{r['old_district']}, {r['old_province']}", "new": f"{r['new_ward']}, {r['new_province']}",
                 "status": "NON_ATOMIC_NOT_WARD_EDGE"}
                for r in table.non_atomic
            ],
        },
    }
