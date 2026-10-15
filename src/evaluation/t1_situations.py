"""Situation tags A-D for T1 samples (scoring side only).

The proposal (section 1.2) names four situations but gives no machine-readable
definition.  The operational definition used by Group 1 is derived from
``edges.csv`` only:

* ``A`` - a ``cu`` sample whose old unit has more than one new target;
* ``B`` - a ``moi`` sample whose new ward receives more than one old unit;
* ``C`` - a ``Lai`` sample;
* ``D`` - the ward name exists in both systems inside the same new province
  (``SingleVersionIndex.homonyms`` of the T2 module, both directions).

A sample may carry several tags; none -> ``NONE``.  The tagger reads gold
fields (system, province, district, ward) and must never feed an inference path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from src.data.administrative_mapping import unit_key
from src.evaluation import t2_lookup as L

RULE_VERSION = "t1-situations-v1"
TAGS = ("A", "B", "C", "D")
NONE_TAG = "NONE"
MATCH_LEVEL = "N2"  # same normalisation level as the main T2 table


class SituationTagger:
    """Assign A-D tags from the edge table and the single-version name index."""

    def __init__(self, table: L.T2Table, index: L.SingleVersionIndex) -> None:
        self.table = table
        self.index = index

    @classmethod
    def load(cls, gazetteer_dir: Path) -> "SituationTagger":
        table = L.T2Table.load(Path(gazetteer_dir))
        return cls(table, L.load_single_version_index(Path(gazetteer_dir), table))

    def fan_out(self, province: str, district: str, ward: str) -> int:
        """Number of distinct new targets of the matched old unit(s); 0 = no match."""
        edges, _ = self.table.match_old(MATCH_LEVEL, province.strip(), district.strip(), ward.strip())
        return len({edge.new_key for edge in edges})

    def fan_in(self, province: str, ward: str) -> int:
        """Number of distinct old units merged into the matched new ward; 0 = no match."""
        edges, _ = self.table.match_new(MATCH_LEVEL, province.strip(), ward.strip())
        return len({edge.old_key for edge in edges})

    def is_cross_system_homonym(self, province: str, ward: str) -> bool:
        """Same ward key in the old and the new name pool of one new province."""
        if not province.strip() or not ward.strip():
            return False
        pkey = self.index._target_province_key(MATCH_LEVEL, province.strip())
        if pkey is None:
            return False
        wkey = unit_key(ward)
        return bool(self.index.homonyms(L.OLD_TO_NEW, pkey, wkey)) and bool(
            self.index.homonyms(L.NEW_TO_OLD, pkey, wkey)
        )

    def tags(self, gold_system: str | None, province: str, district: str, ward: str) -> tuple[str, ...]:
        found = []
        # A and B need the full key of the sample's own system; a hybrid string
        # has no single-system key, so it is never tagged A or B.
        if gold_system == "cu" and ward.strip() and self.fan_out(province, district, ward) > 1:
            found.append("A")
        if gold_system == "moi" and ward.strip() and self.fan_in(province, ward) > 1:
            found.append("B")
        if gold_system == "Lai":
            found.append("C")
        if self.is_cross_system_homonym(province, ward):
            found.append("D")
        return tuple(found) if found else (NONE_TAG,)


def format_tags(tags: Sequence[str]) -> str:
    return "|".join(tags)


def fields_from_gold_spans(text: str, spans: Sequence[dict]) -> dict[str, str]:
    """Rightmost gold PhuongXa/QuanHuyen/TinhThanh surface (scoring side)."""
    labels = {"PhuongXa": "ward", "QuanHuyen": "district", "TinhThanh": "province"}
    fields = {"province": "", "district": "", "ward": ""}
    for span in sorted(spans, key=lambda s: (s["start"], s["end"])):
        name = labels.get(span["label"])
        if name:
            fields[name] = text[span["start"]:span["end"]].strip()
    return fields
