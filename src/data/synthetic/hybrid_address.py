"""Generate verified old/new hybrid addresses without guessing territory."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.data.administrative_mapping import (
    clean_value,
    default_mapping_path,
    load_administrative_mapping,
    normalise_text,
)


# Kept as small compatibility helpers for scripts that imported the old names.
_norm = normalise_text
_value = clean_value


def select_unique_hybrids(candidates: dict[str, list[dict]], quotas: dict[str, int], seed: int) -> list[dict]:
    """Select reproducibly while keeping one temporal label per surface string."""
    selected: list[dict] = []
    selected_addresses: set[str] = set()
    for kind, count in quotas.items():
        ordered = pd.DataFrame(candidates[kind]).sample(frac=1, random_state=seed).to_dict("records")
        chosen = [row for row in ordered if row["ChuoiDiaChi"] not in selected_addresses][:count]
        if len(chosen) != count:
            raise ValueError(f"Only {len(chosen)}/{count} uniquely labelled {kind} hybrid addresses")
        selected.extend(chosen)
        selected_addresses.update(row["ChuoiDiaChi"] for row in chosen)
    return selected


def get_new_province(old_province_str: str, mapping_path: Path | None = None) -> str:
    """Resolve a province through the authoritative 2025 CSV, not a hard-code."""
    mapping = load_administrative_mapping(mapping_path or default_mapping_path())
    return mapping.resolve_new_province(old_province_str)


def generate_hybrid_addresses(
    df_old_snapshot: pd.DataFrame,
    mapping_path: Path,
    target_size: int = 600,
    seed: int = 42,
) -> pd.DataFrame:
    """Build hybrid addresses only for old units with one verified target.

    A row in a 1-N or M-N territorial relation has no deterministic target at
    address level without geometry. It is deliberately excluded here. An N-1
    merge remains usable because every old unit has one confirmed target.
    """
    mapping = load_administrative_mapping(mapping_path)
    candidates = {"C1": [], "C2": [], "C3": []}
    seen = {key: set() for key in candidates}

    for row in df_old_snapshot.to_dict("records"):
        so_nha = _value(row.get("SoNha"))
        ten_duong = _value(row.get("TenDuong"))
        px_cu = _value(row.get("PhuongXa"))
        qh_cu = _value(row.get("QuanHuyen"))
        tt_cu = _value(row.get("TinhThanh"))
        if not all((ten_duong, px_cu, qh_cu, tt_cu)):
            continue

        targets = mapping.targets_for_old(tt_cu, qh_cu, px_cu)
        if len(targets) != 1:
            continue
        target = targets[0]
        relation_type, relation = mapping.relation_for(tt_cu, qh_cu, px_cu, target)
        tt_moi, px_moi = target.province, target.ward
        if _norm(px_moi) == _norm(px_cu) and _norm(tt_moi) == _norm(tt_cu):
            continue

        for kind in candidates:
            if kind in ("C2", "C3") and _norm(tt_moi) == _norm(tt_cu):
                continue
            if kind == "C1":
                kieu_lai = "C1_PhuongMoi_QuanCu_TinhCu"
                px, qh, tt = px_moi, qh_cu, tt_cu
                spans = {"PhuongXa": "moi", "QuanHuyen": "cu", "TinhThanh": "cu"}
            elif kind == "C2":
                kieu_lai = "C2_PhuongMoi_QuanCu_TinhMoi"
                px, qh, tt = px_moi, qh_cu, tt_moi
                spans = {"PhuongXa": "moi", "QuanHuyen": "cu", "TinhThanh": "moi"}
            else:
                kieu_lai = "C3_PhuongCu_QuanCu_TinhMoi"
                px, qh, tt = px_cu, qh_cu, tt_moi
                spans = {"PhuongXa": "cu", "QuanHuyen": "cu", "TinhThanh": "moi"}

            address = ", ".join(part for part in (so_nha, ten_duong, px, qh, tt) if part)
            if address in seen[kind]:
                continue
            seen[kind].add(address)
            candidates[kind].append({
                "ChuoiDiaChi": address,
                "SoNha": so_nha,
                "TenDuong": ten_duong,
                "PhuongXa": px,
                "QuanHuyen": qh,
                "TinhThanh": tt,
                "KieuLai": kieu_lai,
                "HeQuyChieu": "Lai",
                "Span_He_Detail": json.dumps(spans, ensure_ascii=False),
                "LoaiAnhXa": relation_type,
                "QuanHe": relation,
                "HinhThucSapNhap": target.merger_form,
                "Nguon": "OSM snapshot + vietnam-sap-nhap-phuong-xa.csv",
            })

    quotas = {"C1": round(target_size * 0.7), "C2": round(target_size * 0.2)}
    quotas["C3"] = target_size - quotas["C1"] - quotas["C2"]
    # The same surface can represent C2 and C3 when old/new ward names coincide.
    selected = select_unique_hybrids(candidates, quotas, seed)
    return pd.DataFrame(selected).sample(frac=1, random_state=seed).reset_index(drop=True)
