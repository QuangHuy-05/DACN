"""Verified administrative-unit mappings for the 1 July 2025 reform.

The source CSV represents *atomic territorial relationships*: one row links an
old ward, district and province to one new ward.  It must not be collapsed to
``old ward -> new ward`` because an old unit can contribute territory to more
than one new unit and a new unit can receive territory from more than one old
unit.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import re
import unicodedata

import pandas as pd


REQUIRED_COLUMNS = (
    "Phường/Xã cũ",
    "Quận/Huyện cũ",
    "Tỉnh/TP cũ (trước sáp nhập)",
    "Tỉnh/TP mới",
    "Phường/Xã mới (từ 1/7/2025)",
    "Loại đơn vị mới",
    "Mã phường/xã mới",
    "Hình thức sáp nhập",
    "Diện tích mới (km²)",
)


def clean_value(value: object) -> str:
    """Return a display value without CSV nulls or trailing separators."""
    return "" if pd.isna(value) else str(value).strip().rstrip(", ")


def normalise_text(value: object) -> str:
    """Normalise spacing/case but retain Vietnamese accents and unit types.

    Keeping accents and prefixes prevents unsafe collisions such as similarly
    named ``Xã`` and ``Phường``.  A non-exact OSM spelling is left unresolved
    for review instead of being guessed.
    """
    return re.sub(
        r"\s+", " ", unicodedata.normalize("NFC", clean_value(value)).casefold()
    ).strip()


def province_key(value: object) -> str:
    """Create a comparable province key while accepting common level prefixes."""
    key = normalise_text(value)
    return re.sub(r"^(?:tỉnh|thành phố|tp\.?)\s+", "", key).strip()


def unit_key(value: object) -> str:
    """Create an exact comparable key for a ward or district name."""
    return normalise_text(value)


@dataclass(frozen=True)
class NewUnit:
    """Canonical target data retained for one atomic old-to-new edge."""

    province: str
    ward: str
    unit_type: str
    code: str
    merger_form: str
    area_km2: str


class AdministrativeMapping:
    """Index the official atomic mapping graph in both directions."""

    def __init__(self, edges: pd.DataFrame) -> None:
        self.edges = edges
        self.old_to_new: dict[tuple[str, str, str], tuple[NewUnit, ...]] = {}
        self.new_to_old: dict[tuple[str, str], tuple[tuple[str, str, str], ...]] = {}
        self._new_units: dict[tuple[str, str], NewUnit] = {}
        self._old_province_to_new: dict[str, str] = {}
        self._new_province_by_key: dict[str, str] = {}

        outgoing: dict[tuple[str, str, str], dict[tuple[str, str], NewUnit]] = defaultdict(dict)
        incoming: dict[tuple[str, str], set[tuple[str, str, str]]] = defaultdict(set)

        for row in edges.to_dict("records"):
            old = self.old_key(
                row["Tỉnh/TP cũ (trước sáp nhập)"],
                row["Quận/Huyện cũ"],
                row["Phường/Xã cũ"],
            )
            target = NewUnit(
                province=clean_value(row["Tỉnh/TP mới"]),
                ward=clean_value(row["Phường/Xã mới (từ 1/7/2025)"]),
                unit_type=clean_value(row["Loại đơn vị mới"]),
                code=clean_value(row["Mã phường/xã mới"]),
                merger_form=clean_value(row["Hình thức sáp nhập"]),
                area_km2=clean_value(row["Diện tích mới (km²)"]),
            )
            new = self.new_key(target.province, target.ward)
            outgoing[old][new] = target
            incoming[new].add(old)
            self._new_units.setdefault(new, target)
            self._old_province_to_new[province_key(old[0])] = target.province
            self._new_province_by_key[province_key(target.province)] = target.province

        self.old_to_new = {
            old: tuple(targets[key] for key in sorted(targets))
            for old, targets in outgoing.items()
        }
        self.new_to_old = {
            new: tuple(sorted(origins)) for new, origins in incoming.items()
        }

    @staticmethod
    def old_key(province: object, district: object, ward: object) -> tuple[str, str, str]:
        return (province_key(province), unit_key(district), unit_key(ward))

    @staticmethod
    def new_key(province: object, ward: object) -> tuple[str, str]:
        return (province_key(province), unit_key(ward))

    def resolve_new_province(self, province: object) -> str:
        """Return the official post-reform province for an old or new name."""
        key = province_key(province)
        return self._new_province_by_key.get(key, self._old_province_to_new.get(key, ""))

    def targets_for_old(
        self, province: object, district: object, ward: object
    ) -> tuple[NewUnit, ...]:
        return self.old_to_new.get(self.old_key(province, district, ward), ())

    def edge_for_old_target(
        self,
        province: object,
        district: object,
        ward: object,
        target: NewUnit,
    ) -> NewUnit | None:
        """Return the exact edge metadata for an old unit and target identity.

        ``Hình thức sáp nhập`` may differ for two source wards entering the
        same new ward. Therefore edge membership is compared by the stable
        `(new province, new ward)` identity, not by the complete dataclass.
        """
        target_key = self.new_key(target.province, target.ward)
        return next(
            (
                edge
                for edge in self.targets_for_old(province, district, ward)
                if self.new_key(edge.province, edge.ward) == target_key
            ),
            None,
        )

    def has_new_unit(self, province: object, ward: object) -> bool:
        canonical_province = self.resolve_new_province(province)
        if not canonical_province:
            return False
        return self.new_key(canonical_province, ward) in self._new_units

    def target_for_new_unit(self, province: object, ward: object) -> NewUnit | None:
        canonical_province = self.resolve_new_province(province)
        if not canonical_province:
            return None
        return self._new_units.get(self.new_key(canonical_province, ward))

    def relation_for(self, province: object, district: object, ward: object, target: NewUnit) -> tuple[str, str]:
        """Classify one atomic edge from degrees in the complete mapping graph.

        ``A`` and ``B`` are reserved for pure 1-N and N-1 relations.  If both
        sides have several neighbours, the relation is ``M`` / M-N and cannot
        safely be treated as either a split or a merge.
        """
        old = self.old_key(province, district, ward)
        new = self.new_key(target.province, target.ward)
        old_degree = len(self.old_to_new.get(old, ()))
        new_degree = len(self.new_to_old.get(new, ()))
        if old_degree == 1 and new_degree == 1:
            return "C", "1-1"
        if old_degree > 1 and new_degree == 1:
            return "A", "1-N"
        if old_degree == 1 and new_degree > 1:
            return "B", "N-1"
        return "M", "M-N"

    def summary(self) -> dict[str, int]:
        relationship_counts: dict[tuple[str, str], int] = defaultdict(int)
        for old, targets in self.old_to_new.items():
            for target in targets:
                relationship_counts[self.relation_for(*old, target)] += 1
        return {
            "atomic_edges": len(self.edges),
            "old_units": len(self.old_to_new),
            "new_units": len(self.new_to_old),
            "one_to_one_edges": relationship_counts[("C", "1-1")],
            "one_to_many_edges": relationship_counts[("A", "1-N")],
            "many_to_one_edges": relationship_counts[("B", "N-1")],
            "many_to_many_edges": relationship_counts[("M", "M-N")],
        }


def load_administrative_mapping(path: Path) -> AdministrativeMapping:
    """Load and validate the authoritative 2025 administrative mapping CSV."""
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"{path}: missing required columns {missing}")

    frame = frame.loc[:, REQUIRED_COLUMNS].copy()
    # Five special districts are represented directly at district level, so
    # their historical ward is intentionally blank.  Retain them in the
    # graph, but do not reject the authoritative file for that valid shape.
    required_identity = (
        "Quận/Huyện cũ",
        "Tỉnh/TP cũ (trước sáp nhập)",
        "Tỉnh/TP mới",
        "Phường/Xã mới (từ 1/7/2025)",
    )
    empty_rows = frame.loc[
        frame.loc[:, required_identity].apply(lambda column: column.map(clean_value).eq("")).any(axis=1)
    ]
    if not empty_rows.empty:
        raise ValueError(
            f"{path}: {len(empty_rows)} mapping rows lack an old or new unit identity"
        )

    # Repeated source rows convey no additional mapping information.
    frame = frame.drop_duplicates().reset_index(drop=True)

    # A formal new-unit code must never point to two differently named targets.
    coded = frame[frame["Mã phường/xã mới"].map(clean_value).ne("")]
    code_conflicts = coded.groupby("Mã phường/xã mới")[[
        "Tỉnh/TP mới", "Phường/Xã mới (từ 1/7/2025)"
    ]].nunique()
    if (code_conflicts > 1).any(axis=1).any():
        bad_codes = code_conflicts[(code_conflicts > 1).any(axis=1)].index.tolist()[:5]
        raise ValueError(f"{path}: conflicting target identities for codes {bad_codes}")

    # A pre-reform province has exactly one post-reform province in this source.
    province_targets = frame.assign(
        _old=frame["Tỉnh/TP cũ (trước sáp nhập)"].map(province_key),
        _new=frame["Tỉnh/TP mới"].map(clean_value),
    ).groupby("_old")["_new"].nunique()
    if (province_targets > 1).any():
        bad = province_targets[province_targets > 1].index.tolist()[:5]
        raise ValueError(f"{path}: an old province has multiple new provinces: {bad}")

    return AdministrativeMapping(frame)


def default_mapping_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "reference"
        / "administrative_units"
        / "vietnam-sap-nhap-phuong-xa.csv"
    )
