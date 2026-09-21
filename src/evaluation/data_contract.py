"""Validate frozen benchmark inputs before any baseline call."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.evaluation.manifest import BENCHMARK_FILES, compute_sha256


REQUIRED_COLUMNS = {
    BENCHMARK_FILES[0]: {"ChuoiDiaChi", "SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh", "HeQuyChieu"},
    BENCHMARK_FILES[1]: {"ID", "ChuoiDiaChi", "ChuoiDiaChiGoc", "HeQuyChieu", "MucDoNhieu", "LoaiNhieu", *(f"GT_{name}" for name in ("SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh"))},
    BENCHMARK_FILES[2]: {"ChuoiDiaChi", "SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh", "HeQuyChieu"},
    BENCHMARK_FILES[3]: {"ChuoiDiaChi", "KieuThieu", "HeQuyChieu", *(f"GT_{name}" for name in ("SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh")), *(name for name in ("SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh"))},
    BENCHMARK_FILES[4]: {"ChuoiDiaChi", "KieuLai", "HeQuyChieu", "Span_He_Detail", "SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh"},
    BENCHMARK_FILES[5]: {"ID_Node", "DiaChi_Cu", "DiaChi_Moi", "QuanHe", "Nguon", "MaPhuongXaMoi"},
}

EXPECTED_ROWS = dict(zip(BENCHMARK_FILES, (1000, 1000, 1500, 800, 600, 600)))
FIVE_FIELDS = ("SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh")


def validate_benchmarks(benchmark_dir: Path, manifest: dict | None = None) -> dict[str, dict]:
    """Return diagnostics; reject schema, label and identity errors."""
    summary: dict[str, dict] = {}
    mapping_path = Path(__file__).resolve().parents[2] / "data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv"
    if not mapping_path.exists():
        raise FileNotFoundError(mapping_path)
    if manifest is not None and compute_sha256(mapping_path) != manifest["mapping_source"]["sha256"]:
        raise ValueError("Administrative mapping changed after manifest freeze")
    mapping = pd.read_csv(mapping_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    valid_targets = set(zip(mapping["Mã phường/xã mới"], mapping["Phường/Xã mới (từ 1/7/2025)"], mapping["Tỉnh/TP mới"]))

    for name in BENCHMARK_FILES:
        path = benchmark_dir / name
        if not path.exists():
            raise FileNotFoundError(path)
        if path.read_bytes()[:3] != b"\xef\xbb\xbf":
            raise ValueError(f"{name}: expected UTF-8 BOM")
        frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        missing = REQUIRED_COLUMNS[name] - set(frame.columns)
        if missing:
            raise ValueError(f"{name}: missing columns {sorted(missing)}")
        if len(frame) != EXPECTED_ROWS[name]:
            raise ValueError(f"{name}: expected {EXPECTED_ROWS[name]} rows, found {len(frame)}")
        if manifest is not None:
            saved = manifest["datasets"][name]
            if list(frame.columns) != saved["columns"] or compute_sha256(path) != saved["sha256"]:
                raise ValueError(f"{name}: changed after manifest freeze")

        address_col = "DiaChi_Cu" if name == BENCHMARK_FILES[5] else "ChuoiDiaChi"
        if frame[address_col].str.strip().eq("").any():
            raise ValueError(f"{name}: empty input address")
        if name != BENCHMARK_FILES[5] and frame[address_col].duplicated().any():
            raise ValueError(f"{name}: duplicate input with potentially conflicting labels")

        # Dataset 01 validation
        if name == BENCHMARK_FILES[0]:
            if set(frame["HeQuyChieu"]) != {"moi"}:
                raise ValueError(f"{name}: invalid reference-system labels")
            if frame["QuanHuyen"].str.strip().ne("").any():
                raise ValueError(f"{name}: QuanHuyen must be empty for 2-tier new system")
            for field in ("SoNha", "TenDuong", "PhuongXa", "TinhThanh"):
                if frame[field].str.strip().eq("").any():
                    raise ValueError(f"{name}: field '{field}' must not be empty")

        # Dataset 02 validation
        if name == BENCHMARK_FILES[1]:
            if frame["ID"].duplicated().any() or frame["ChuoiDiaChi"].eq(frame["ChuoiDiaChiGoc"]).any():
                raise ValueError(f"{name}: duplicate ID or unchanged noisy input")
            if set(frame["HeQuyChieu"]) != {"cu", "moi"}:
                raise ValueError(f"{name}: invalid reference-system labels")
            for row in frame.to_dict("records"):
                sys = row["HeQuyChieu"]
                for field in ("SoNha", "TenDuong", "PhuongXa", "TinhThanh"):
                    if not row[f"GT_{field}"]:
                        raise ValueError(f"{name}: GT_{field} must not be empty")
                if sys == "cu" and not row["GT_QuanHuyen"]:
                    raise ValueError(f"{name}: GT_QuanHuyen must not be empty for legacy row")
                if sys == "moi" and row["GT_QuanHuyen"]:
                    raise ValueError(f"{name}: GT_QuanHuyen must be empty for new system row")

        # Dataset 03 validation (Clean Complete Legacy addresses)
        if name == BENCHMARK_FILES[2]:
            if set(frame["HeQuyChieu"]) != {"cu"}:
                raise ValueError(f"{name}: invalid reference-system labels")
            for field in FIVE_FIELDS:
                if frame[field].str.strip().eq("").any():
                    empty_cnt = frame[field].str.strip().eq("").sum()
                    raise ValueError(f"{name}: {empty_cnt} rows have empty '{field}'; Data 03 must be 100% clean and complete")

        # Dataset 04 validation (Controlled Missing-field from clean source)
        if name == BENCHMARK_FILES[3]:
            if set(frame["HeQuyChieu"]) != {"cu", "moi"}:
                raise ValueError(f"{name}: invalid reference-system labels")
            counts = dict(frame["HeQuyChieu"].value_counts())
            if counts.get("cu") != 400 or counts.get("moi") != 400:
                raise ValueError(f"{name}: expected 400 'cu' and 400 'moi', found {counts}")

            dropped_spec = {
                "drop_ward": ("PhuongXa",),
                "drop_district": ("QuanHuyen",),
                "drop_housenumber": ("SoNha",),
                "drop_housenumber_ward": ("SoNha", "PhuongXa"),
            }

            for idx, row in enumerate(frame.to_dict("records")):
                sys = row["KieuThieu"]
                ref_sys = row["HeQuyChieu"]
                if sys not in dropped_spec:
                    raise ValueError(f"{name}: unknown KieuThieu '{sys}' at row {idx}")
                if ref_sys == "moi" and sys == "drop_district":
                    raise ValueError(f"{name}: drop_district is not allowed on new system at row {idx}")

                expected_dropped = set(dropped_spec[sys])
                if ref_sys == "moi":
                    expected_dropped.add("QuanHuyen")

                # Validate surface fields
                for field in FIVE_FIELDS:
                    val = row[field].strip()
                    if field in expected_dropped:
                        if val != "":
                            raise ValueError(f"{name}: field '{field}' should be dropped for {sys} at row {idx}")
                    else:
                        if val == "":
                            raise ValueError(f"{name}: field '{field}' unexpectedly empty for {sys} at row {idx}")

                # Validate GT_* preservation
                for field in ("SoNha", "TenDuong", "PhuongXa", "TinhThanh"):
                    if not row[f"GT_{field}"].strip():
                        raise ValueError(f"{name}: GT_{field} empty at row {idx}")
                if ref_sys == "cu" and not row["GT_QuanHuyen"].strip():
                    raise ValueError(f"{name}: GT_QuanHuyen empty for legacy row at row {idx}")
                if ref_sys == "moi" and row["GT_QuanHuyen"].strip():
                    raise ValueError(f"{name}: GT_QuanHuyen must be empty for new system row at row {idx}")

        # Dataset 06 validation
        if name == BENCHMARK_FILES[4]:
            if set(frame["HeQuyChieu"]) != {"Lai"}:
                raise ValueError(f"{name}: invalid hybrid label")
            for field in FIVE_FIELDS:
                if frame[field].str.strip().eq("").any():
                    empty_cnt = frame[field].str.strip().eq("").sum()
                    raise ValueError(f"{name}: {empty_cnt} rows have empty '{field}' in hybrid addresses")

        # Dataset 07 validation
        if name == BENCHMARK_FILES[5]:
            if frame["ID_Node"].duplicated().any() or not set(frame["QuanHe"]) <= {"N-1", "M-N", "1-N", "1-1"}:
                raise ValueError(f"{name}: duplicate node or invalid relation")
            for row in frame.to_dict("records"):
                old = [part.strip() for part in row["DiaChi_Cu"].split(",")]
                new = [part.strip() for part in row["DiaChi_Moi"].split(",")]
                if len(old) < 4 or len(new) < 3 or old[:-3] != new[:-2]:
                    raise ValueError(f"{name}: changed street/house prefix at {row['ID_Node']}")
                if (row["MaPhuongXaMoi"], new[-2], new[-1]) not in valid_targets:
                    raise ValueError(f"{name}: target code/name/province not found at {row['ID_Node']}")

        summary[name] = {"rows": len(frame), "sha256": compute_sha256(path), "columns": list(frame.columns)}
    return summary
