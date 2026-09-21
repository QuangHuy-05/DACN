"""Unified schema definitions for baseline predictions and evaluation outputs.

The unified contract requires 9 columns:
ID, DiaChiGoc, CongCu, TruongDuDoan, TruongDung, DungSai, LoaiLoi, TinhHuongMoHo, GhiChu
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any


STANDARD_FIELDS = ("SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh")

UNIFIED_SCHEMA_COLUMNS = (
    "ID",
    "DiaChiGoc",
    "CongCu",
    "TruongDuDoan",
    "TruongDung",
    "DungSai",
    "LoaiLoi",
    "TinhHuongMoHo",
    "GhiChu",
)


@dataclass
class StandardPrediction:
    """Standardized 5-field address output from any baseline tool."""

    so_nha: str = ""
    ten_duong: str = ""
    phuong_xa: str = ""
    quan_huyen: str = ""
    tinh_thanh: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "SoNha": self.so_nha.strip(),
            "TenDuong": self.ten_duong.strip(),
            "PhuongXa": self.phuong_xa.strip(),
            "QuanHuyen": self.quan_huyen.strip(),
            "TinhThanh": self.tinh_thanh.strip(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class UnifiedEvaluationRecord:
    """One evaluation record strictly adhering to the 9-column contract."""

    record_id: str
    dia_chi_goc: str
    cong_cu: str
    truong_du_doan: str
    truong_dung: str
    dung_sai: str  # "CORRECT" | "PARTIAL" | "ERROR" | "UNSUPPORTED"
    loai_loi: str  # e.g. "none", "missing_field", "hallucination", "silent_error", "boundary_error"
    tinh_huong_mo_ho: str  # "A" | "B" | "C" | "D" | "NONE"
    ghi_chu: str

    def to_dict(self) -> dict[str, str]:
        return {
            "ID": str(self.record_id),
            "DiaChiGoc": str(self.dia_chi_goc),
            "CongCu": str(self.cong_cu),
            "TruongDuDoan": str(self.truong_du_doan),
            "TruongDung": str(self.truong_dung),
            "DungSai": str(self.dung_sai),
            "LoaiLoi": str(self.loai_loi),
            "TinhHuongMoHo": str(self.tinh_huong_mo_ho),
            "GhiChu": str(self.ghi_chu),
        }
