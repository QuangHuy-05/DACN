"""Unified schema definitions for baseline predictions and evaluation outputs.

The unified contract requires 9 columns:
ID, DiaChiGoc, CongCu, TruongDuDoan, TruongDung, DungSai, LoaiLoi, TinhHuongMoHo, GhiChu
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from typing import Any


STANDARD_FIELDS = ("SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh")

SPAN11_LABELS = (
    "SoNha",
    "TenDuong",
    "Ngo/Hem",
    "ToaNha/CanHo",
    "PhuongXa",
    "QuanHuyen",
    "TinhThanh",
    "MocDinhVi",
    "HuongDi",
    "GhiChu",
    "Khac",
)

ADDRESS_SYSTEMS = ("cu", "moi", "Lai")

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


@dataclass
class CharacterSpan:
    """A character span with half-open offset [start, end) and schema label."""

    start: int
    end: int
    label: str
    text: str = ""
    system: str = "khong_xac_dinh"  # "cu" | "moi" | "khong_xac_dinh"

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "label": self.label,
            "text": self.text,
            "system": self.system,
        }


@dataclass
class SpanModelOutput:
    """Model output containing 11-label spans, predicted system, and trace metadata."""

    sample_id: str
    raw_text: str
    spans: list[CharacterSpan] = field(default_factory=list)
    predicted_system: str = "khong_ro"  # "cu" | "moi" | "Lai" | "khong_ro"
    abstain: bool = False
    latency_ms: float = 0.0
    trace: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "raw_text": self.raw_text,
            "spans": [s.to_dict() for s in self.spans],
            "predicted_system": self.predicted_system,
            "abstain": self.abstain,
            "latency_ms": self.latency_ms,
            "trace": self.trace,
        }

    def to_standard_5_fields(self) -> StandardPrediction:
        """Extract standard 5 fields from 11 spans for backwards compatibility."""
        fields: dict[str, list[str]] = {
            "SoNha": [],
            "TenDuong": [],
            "PhuongXa": [],
            "QuanHuyen": [],
            "TinhThanh": [],
        }
        for s in self.spans:
            if s.label in fields:
                fields[s.label].append(s.text.strip())
        return StandardPrediction(
            so_nha=", ".join(fields["SoNha"]),
            ten_duong=", ".join(fields["TenDuong"]),
            phuong_xa=", ".join(fields["PhuongXa"]),
            quan_huyen=", ".join(fields["QuanHuyen"]),
            tinh_thanh=", ".join(fields["TinhThanh"]),
        )
