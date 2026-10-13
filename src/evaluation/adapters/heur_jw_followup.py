"""Versioned compact-prefix rules; original v3 behavior remains available."""

from datetime import date
import re

from src.data.nso_dual_snapshot import DualSnapshotGazetteer
from src.evaluation.adapters.heur_jw_adapter import HeuristicJaroWinklerAdapter, normalize_surface


class HeuristicJaroWinklerFollowup(HeuristicJaroWinklerAdapter):
    RULE_VERSION = "heur_jw_compact_prefix_dual_snapshot_v4"
    PREFIX = re.compile(r"^(?:thành\s+phố|thị\s+trấn|thị\s+xã|đặc\s+khu|phường|huyện|quận|tỉnh|xã)\s+|^(?:tp|tt|tx|p|q|h|x)(?:\.\s*|\s+)", re.I)
    MARKER = re.compile(r"(?<!\w)(?:thành\s+phố|thị\s+trấn|thị\s+xã|đặc\s+khu|phường|huyện|quận|tỉnh|xã|đường|phố|ngõ|hẻm|ngách|kiệt)\b|(?<!\w)(?:tp|tt|tx|p|q|h|x)(?:\.\s*|\s+)", re.I)

    @staticmethod
    def _expand(value):
        return re.sub(r"^(tp|tt|tx|p|q|h|x)\s+", r"\1. ", normalize_surface(value))

    @staticmethod
    def _levels(value):
        return HeuristicJaroWinklerAdapter._levels(HeuristicJaroWinklerFollowup._expand(value))

    @staticmethod
    def _unit_kind(value):
        return HeuristicJaroWinklerAdapter._unit_kind(HeuristicJaroWinklerFollowup._expand(value))

    def _load_gazetteer(self):
        super()._load_gazetteer()
        self.dated_evidence = DualSnapshotGazetteer(self.gazetteer_dir)

    def _valid(self, entity):
        point = self.as_of_date if self.temporal_policy == "fixed_as_of" else date.fromisoformat(self.dated_evidence.snapshots[entity.system])
        return point.isoformat() == self.dated_evidence.snapshots[entity.system] and super()._valid(entity)

    def _resolve(self, value, context):
        candidates, info = super()._resolve(value, context)
        for candidate in info["candidates"]:
            candidate["source_evidence"] = self.dated_evidence.evidence.get(candidate["entity_id"])
            candidate["verified_as_of"] = self.dated_evidence.snapshots[candidate["system"]] if candidate["source_evidence"] else None
        return candidates, info
