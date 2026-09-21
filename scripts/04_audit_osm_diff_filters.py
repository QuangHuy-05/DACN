"""Explain every OSM diff record accepted or rejected by the pair builder."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.administrative_alias import normalize_diff_record_with_trace
from src.data.administrative_mapping import clean_value, load_administrative_mapping
from src.data.synthetic.bidirectional import DIFF_COLUMNS, _new_target_from_diff


REAL_PATH = ROOT / "data/processed/osm/osm_real_bidirectional_pairs.csv"
OLD_FULL_PATH = ROOT / "data/interim/osm/osm_old_snapshot_full.csv"
OLD_BALANCED_PATH = ROOT / "data/interim/osm/osm_old_snapshot_20250630.csv"
OLD_PATH = OLD_FULL_PATH if OLD_FULL_PATH.exists() else OLD_BALANCED_PATH
MAPPING_PATH = ROOT / "data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv"
OUT_PATH = ROOT / "data/processed/evaluation/osm_diff_filter_audit.csv"


def geometry_status(record: dict) -> str:
    """Return movement evidence state, including legacy diffs without geometry."""
    available = clean_value(record.get("HinhHocCoDuLieu", "")).casefold()
    if available not in {"true", "1", "yes"}:
        return "not_captured"

    value = clean_value(record.get("HinhHocThayDoi", "")).casefold()
    if value in {"true", "1", "yes"}:
        return "changed"
    if value in {"false", "0", "no"}:
        return "unchanged"
    return "not_captured"


def audit() -> pd.DataFrame:
    mapping = load_administrative_mapping(MAPPING_PATH)
    real = pd.read_csv(REAL_PATH, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    old = pd.read_csv(OLD_PATH, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    missing = set(DIFF_COLUMNS) - set(real.columns)
    if missing:
        raise ValueError(f"{REAL_PATH}: missing columns {sorted(missing)}")
    old_by_id = {
        (row["OSM_Type"], row["OSM_ID"]): row
        for row in old.to_dict("records")
    }
    seen_pairs: set[tuple[str, str]] = set()
    seen_nodes: set[str] = set()
    rows: list[dict[str, str]] = []

    for record in real.to_dict("records"):
        node_id = f"{record['OSM_Type']}:{record['OSM_ID']}"
        snapshot = old_by_id.get((record["OSM_Type"], record["OSM_ID"]))
        reason = "accepted_observed"
        detail = "matched official edge and passed all evidence checks"
        target = None
        old_address = clean_value(record.get("DiaChi_Cu"))
        norm, alias_changes = normalize_diff_record_with_trace(record)
        geometry = geometry_status(record)

        if snapshot is None:
            reason = "not_in_old_snapshot"
            detail = "the old snapshot has no row for this OSM object"
        elif (
            clean_value(record["SoNha"]).casefold() != clean_value(snapshot["SoNha"]).casefold()
            or clean_value(record["TenDuong"]).casefold() != clean_value(snapshot["TenDuong"]).casefold()
        ):
            reason = "house_or_street_changed"
            detail = "administrative and physical/address text changes cannot be separated"
        elif not clean_value(record["TenDuong"]):
            reason = "missing_street"
            detail = "the pair builder requires a street to create a reliable address"
        else:
            target = _new_target_from_diff(mapping, norm)
            if target is None:
                if not clean_value(norm.get("PhuongXa_Moi")) and not clean_value(norm.get("QuanHuyen_Moi")):
                    reason = "missing_new_ward"
                    detail = "new address lacks ward information in OSM tags"
                else:
                    reason = "new_unit_not_found"
                    detail = "new ward/district field does not match a known unit in the official CSV"
            else:
                target = mapping.edge_for_old_target(
                    norm["TinhThanh_Cu"], norm["QuanHuyen_Cu"], norm["PhuongXa_Cu"], target
                )
                if target is None:
                    if not clean_value(norm.get("PhuongXa_Cu")):
                        reason = "missing_old_ward"
                        detail = "old snapshot lacks ward name to verify territorial edge"
                    elif not clean_value(norm.get("QuanHuyen_Cu")):
                        reason = "missing_old_district"
                        detail = "old snapshot lacks district name to resolve ambiguity"
                    elif geometry == "changed":
                        reason = "possible_geometry_move"
                        detail = (
                            "the OSM object geometry changed alongside an unverified administrative edge; "
                            "review the move before treating the CSV as incomplete"
                        )
                    elif geometry == "unchanged":
                        reason = "stationary_unverified_edge"
                        detail = (
                            "geometry did not change, but the old-to-new edge is absent; "
                            "review OSM tags and the administrative CSV"
                        )
                    else:
                        reason = "unverified_historical_edge"
                        detail = (
                            "the old-to-new edge is absent and this legacy diff has no geometry evidence; "
                            "re-extract OSM to distinguish a move from a mapping/source issue"
                        )
                else:
                    new_address = ", ".join(
                        part for part in map(
                            clean_value,
                            (record.get("SoNha"), record.get("TenDuong"), target.ward, target.province),
                        ) if part
                    )
                    pair_key = (old_address, new_address)
                    if not old_address:
                        reason = "missing_old_address"
                        detail = "the source did not provide a usable old address string"
                    elif old_address == new_address:
                        reason = "no_address_change"
                        detail = "old and new canonical address strings are identical"
                    elif pair_key in seen_pairs or node_id in seen_nodes:
                        reason = "duplicate_observed_pair"
                        detail = "the same text pair or OSM object was already accepted"
                    else:
                        seen_pairs.add(pair_key)
                        seen_nodes.add(node_id)

        rows.append({
            "OSM_Type": record["OSM_Type"],
            "OSM_ID": record["OSM_ID"],
            "ID_Node": node_id,
            "DiaChi_Cu": old_address,
            "TinhThanh_Cu": record["TinhThanh_Cu"],
            "QuanHuyen_Cu": record["QuanHuyen_Cu"],
            "PhuongXa_Cu": record["PhuongXa_Cu"],
            "TinhThanh_Moi": record["TinhThanh_Moi"],
            "QuanHuyen_Moi": record["QuanHuyen_Moi"],
            "PhuongXa_Moi": record["PhuongXa_Moi"],
            "TinhThanh_Cu_Chuan": norm["TinhThanh_Cu"],
            "QuanHuyen_Cu_Chuan": norm["QuanHuyen_Cu"],
            "PhuongXa_Cu_Chuan": norm["PhuongXa_Cu"],
            "TinhThanh_Moi_Chuan": norm["TinhThanh_Moi"],
            "QuanHuyen_Moi_Chuan": norm["QuanHuyen_Moi"],
            "PhuongXa_Moi_Chuan": norm["PhuongXa_Moi"],
            "AliasDaApDung": " | ".join(alias_changes),
            "SoAliasDaApDung": str(len(alias_changes)),
            "TrangThaiHinhHoc": geometry,
            "KetQua": reason,
            "ChiTiet": detail,
            "QuanHe": mapping.relation_for(
                norm["TinhThanh_Cu"], norm["QuanHuyen_Cu"], norm["PhuongXa_Cu"], target
            )[1] if reason in {"accepted_observed", "duplicate_observed_pair"} and target is not None else "",
        })
    return pd.DataFrame(rows)


def main() -> None:
    result = audit()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    print(f"Saved {len(result)} audit rows to {OUT_PATH}")
    print(result.KetQua.value_counts().to_dict())


if __name__ == "__main__":
    main()
