"""Build evidence-backed old/new address pairs for the 2025 reform."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data.administrative_alias import normalize_diff_record
from src.data.administrative_mapping import clean_value, load_administrative_mapping


COLUMNS = (
    "ID_Node",
    "DiaChi_Cu",
    "DiaChi_Moi",
    "LoaiAnhXa",
    "QuanHe",
    "HinhThucSapNhap",
    "MaPhuongXaMoi",
    "Nguon",
)
OLD_COLUMNS = ("OSM_Type", "OSM_ID", "SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh")
DIFF_COLUMNS = (
    "OSM_Type", "OSM_ID", "SoNha", "TenDuong", "PhuongXa_Cu",
    "QuanHuyen_Cu", "TinhThanh_Cu", "PhuongXa_Moi", "QuanHuyen_Moi",
    "TinhThanh_Moi", "DiaChi_Cu",
)


def _read_required(path: Path, columns: tuple[str, ...]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError(f"{path}: missing columns {sorted(missing)}")
    return frame


def _address(*parts: object) -> str:
    return ", ".join(part for part in map(clean_value, parts) if part)


def _new_target_from_diff(mapping, record: dict):
    """Find the current ward whichever OSM administrative field carries it."""
    norm = normalize_diff_record(record)
    province = norm.get("TinhThanh_Moi", "")
    for value in (norm.get("PhuongXa_Moi", ""), norm.get("QuanHuyen_Moi", "")):
        target = mapping.target_for_new_unit(province, value)
        if target is not None:
            return target
    return None


def _sample_stratified(frame: pd.DataFrame, size: int, seed: int) -> pd.DataFrame:
    """Cap direct observations without silently discarding a rare relation."""
    if size <= 0 or frame.empty:
        return frame.iloc[0:0].copy()
    if len(frame) <= size:
        return frame
    groups = [(name, group) for name, group in frame.groupby("QuanHe", sort=True)]
    selected: list[pd.DataFrame] = []
    remaining = size
    # Reserve one record per supported relation first.
    for index, (_, group) in enumerate(groups):
        reserve = 1 if remaining >= len(groups) - index else 0
        if reserve:
            selected.append(group.sample(n=1, random_state=seed + index))
            remaining -= 1
    if remaining == 0:
        return pd.concat(selected, ignore_index=True)

    already = set(pd.concat(selected).index) if selected else set()
    candidates = frame.loc[~frame.index.isin(already)]
    selected.append(candidates.sample(n=remaining, random_state=seed))
    return pd.concat(selected, ignore_index=True)


def generate_bidirectional_pairs(
    real_pairs_path: Path,
    mapping_path: Path,
    old_snapshot_path: Path,
    target_size: int = 600,
    seed: int = 42,
    full_snapshot_path: Path | None = None,
) -> pd.DataFrame:
    """Return observed pairs, then safe snapshot-derived pairs.

    Direct OSM observations may represent every relationship type (1-1, 1-N,
    N-1, M-N), because the changed OSM object identifies the real destination.
    Snapshot-only records are generated only when the old unit has exactly one
    authoritative target. This prohibits guessing the target for a split or a
    many-to-many territorial redistribution.
    """
    if target_size < 0:
        raise ValueError("target_size must be non-negative")

    mapping = load_administrative_mapping(mapping_path)
    real = _read_required(real_pairs_path, DIFF_COLUMNS)
    old = _read_required(old_snapshot_path, OLD_COLUMNS)

    # Use full old snapshot for matching real diff IDs if available; otherwise fallback to old
    if full_snapshot_path is None:
        default_full = old_snapshot_path.parent / "osm_old_snapshot_full.csv"
        if default_full.exists():
            full_snapshot_path = default_full

    full_old = _read_required(full_snapshot_path, OLD_COLUMNS) if (full_snapshot_path and full_snapshot_path.exists()) else old
    snapshot_by_id = {
        (record["OSM_Type"], record["OSM_ID"]): record
        for record in full_old.to_dict("records")
    }
    observed: list[dict] = []
    derived: list[dict] = []
    seen_pairs: set[tuple[str, str]] = set()
    seen_nodes: set[str] = set()

    def add(
        record: dict,
        old_fields: tuple[object, object, object],
        target,
        source: str,
        output: list[dict],
        old_address: str,
    ) -> None:
        province, district, ward = old_fields
        if target is None or not clean_value(record.get("TenDuong")):
            return
        # Match the stable new-unit identity. Metadata such as merger form can
        # legitimately vary between source wards entering the same target.
        target = mapping.edge_for_old_target(province, district, ward, target)
        if target is None:
            return

        relation_type, relation = mapping.relation_for(province, district, ward, target)
        new_address = _address(record.get("SoNha"), record.get("TenDuong"), target.ward, target.province)
        node_id = f"{record['OSM_Type']}:{record['OSM_ID']}"
        pair_key = (old_address, new_address)
        if not old_address or old_address == new_address or pair_key in seen_pairs or node_id in seen_nodes:
            return
        seen_pairs.add(pair_key)
        seen_nodes.add(node_id)
        output.append({
            "ID_Node": node_id,
            "DiaChi_Cu": old_address,
            "DiaChi_Moi": new_address,
            "LoaiAnhXa": relation_type,
            "QuanHe": relation,
            "HinhThucSapNhap": target.merger_form,
            "MaPhuongXaMoi": target.code,
            "Nguon": source,
        })

    for record in real.to_dict("records"):
        snapshot = snapshot_by_id.get((record["OSM_Type"], record["OSM_ID"]))
        if snapshot is None:
            continue
        # Do not treat a changed house number/street as administrative evidence.
        if (
            clean_value(record["SoNha"]).casefold() != clean_value(snapshot["SoNha"]).casefold()
            or clean_value(record["TenDuong"]).casefold() != clean_value(snapshot["TenDuong"]).casefold()
        ):
            continue
        norm = normalize_diff_record(record)
        add(
            record,
            (norm["TinhThanh_Cu"], norm["QuanHuyen_Cu"], norm["PhuongXa_Cu"]),
            _new_target_from_diff(mapping, norm),
            "OSM_Diff+vietnam-sap-nhap-phuong-xa.csv",
            observed,
            clean_value(record.get("DiaChi_Cu")),
        )

    # The old snapshot has no geometry showing where a split fragment went.
    for record in old.to_dict("records"):
        old_fields = (record["TinhThanh"], record["QuanHuyen"], record["PhuongXa"])
        targets = mapping.targets_for_old(*old_fields)
        if len(targets) != 1:
            continue
        add(
            record,
            old_fields,
            targets[0],
            "OSM_Snapshot+vietnam-sap-nhap-phuong-xa.csv",
            derived,
            _address(
                record.get("SoNha"), record.get("TenDuong"), record["PhuongXa"],
                record["QuanHuyen"], record["TinhThanh"],
            ),
        )

    observed_frame = _sample_stratified(pd.DataFrame(observed, columns=COLUMNS), target_size, seed)
    remaining = max(0, target_size - len(observed_frame))
    derived_frame = pd.DataFrame(derived, columns=COLUMNS)
    if len(derived_frame) > remaining:
        derived_frame = _sample_stratified(derived_frame, remaining, seed)
    return pd.concat([observed_frame, derived_frame], ignore_index=True)
