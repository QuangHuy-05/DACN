"""Build text-only annotation suggestions for the Sprint 3 pilot.

This is an annotator aid, not adjudicated gold. It reads only the Label Studio
import (sample_id and text), never benchmark GT columns.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPORT_PATH = ROOT / "data/interim/annotation/sprint03/label_studio_pilot_import.json"
OUTPUT_DIR = ROOT / "data/interim/annotation/sprint03"
JSON_PATH = OUTPUT_DIR / "pilot_span11_candidate_answers.json"
MD_PATH = OUTPUT_DIR / "pilot_span11_candidate_answers.md"

LABELS = {
    "SoNha", "TenDuong", "Ngo/Hem", "ToaNha/CanHo", "PhuongXa",
    "QuanHuyen", "TinhThanh", "MocDinhVi", "HuongDi", "GhiChu", "Khac",
}
SYSTEMS = {"cu", "moi", "khong_xac_dinh"}

# Only names with enough evidence from the address and the public 2025 unit
# list are assigned a period. Reused names stay khong_xac_dinh.
OLD_WARD_SAMPLES = {
    1, 2, 3, 6, 7, 8, 9, 10, 11, 12, 13, 14, 17, 18, 19, 20, 21, 22, 23, 24,
}
NEW_WARD_SAMPLES = {
    25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 36, 38, 39, 40, 41,
    43, 44, 45, 46, 47, 48,
}
UNCLEAR_WHOLE_SYSTEM = {35, 37, 42}
REVIEW = {
    4: (["temporal_ambiguity"], "Cầu Ông Lãnh là tên phường ở cả hai giai đoạn; Quận 1 cho biết cấu trúc toàn câu là cũ."),
    35: (["temporal_ambiguity"], "Không có quận; tên Phường Cầu Ông Lãnh xuất hiện ở cả hai giai đoạn."),
    37: (["temporal_ambiguity"], "Không có quận; tên Phường Tân Bình có thể trùng giữa các khu vực và giai đoạn."),
    42: (["temporal_ambiguity", "ambiguous_label"], "Phường Tân Phú trùng tên cũ/mới ở các khu vực khác nhau; kiểm tra 101 là số nhà hay mã vị trí trong Crescent Mall."),
    46: (["ambiguous_label"], "Kios 8 được gợi ý là Khac; duyệt lại nếu quy ước mở rộng ToaNha/CanHo cho ki-ốt."),
    48: (["ambiguous_label"], "Đặc khu Cát Hải là đơn vị cấp xã mới; cần chốt PhuongXa có bao gồm đặc khu hay chuyển sang Khac."),
}


def span_system(sample_number: int, label: str) -> str:
    if label == "QuanHuyen":
        return "cu"
    if label == "PhuongXa":
        if sample_number in OLD_WARD_SAMPLES:
            return "cu"
        if sample_number in NEW_WARD_SAMPLES:
            return "moi"
    return "khong_xac_dinh"


def whole_system(sample_number: int) -> str | None:
    if sample_number <= 24:
        return "cu"  # Explicit old district tier is present.
    if sample_number <= 48 and sample_number not in UNCLEAR_WHOLE_SYSTEM:
        return "moi"  # New unit name or special zone, with no district tier.
    return None


def build_spans(sample_number: int, text: str) -> list[dict[str, object]]:
    spans: list[dict[str, object]] = []

    def add(value: str, label: str, start: int) -> None:
        assert label in LABELS
        assert text[start:start + len(value)] == value
        spans.append({
            "start": start,
            "end": start + len(value),
            "text": value,
            "label": label,
            "system": span_system(sample_number, label),
        })

    if sample_number <= 48:
        cursor = 0
        for part_index, part in enumerate(text.split(", ")):
            start = text.index(part, cursor)
            cursor = start + len(part)

            if sample_number == 42 and part_index == 0:
                add(part, "GhiChu", start)
            elif sample_number == 42 and part_index == 1:
                add("Crescent Mall", "ToaNha/CanHo", start)
                add("101", "SoNha", start + part.index("101"))
            elif sample_number == 46 and part_index == 0:
                add(part, "Khac", start)
            elif part_index == 0:
                add(part, "SoNha", start)
            elif part.startswith("Hẻm "):
                match = re.fullmatch(r"(Hẻm \S+) (.+)", part)
                if match is None:
                    raise ValueError(f"Cannot split alley in sample {sample_number}: {part}")
                add(match.group(1), "Ngo/Hem", start)
                add(match.group(2), "TenDuong", start + len(match.group(1)) + 1)
            elif part.startswith(("Phường ", "Xã ", "Đặc khu ")):
                add(part, "PhuongXa", start)
            elif part.startswith(("Quận ", "Thị xã ")) or part in {
                "Thành phố Thủ Đức", "Thành phố Từ Sơn",
            }:
                add(part, "QuanHuyen", start)
            elif part.startswith(("Thành phố ", "Tỉnh ")):
                add(part, "TinhThanh", start)
            else:
                add(part, "TenDuong", start)
    elif sample_number <= 54:
        add(text, "MocDinhVi", 0)
    elif sample_number <= 60:
        add(text, "HuongDi", 0)
    elif sample_number in {61, 62}:
        cursor = 0
        for part in text.split(", "):
            start = text.index(part, cursor)
            cursor = start + len(part)
            add(part, "GhiChu" if part.lower().startswith("tầng ") else "ToaNha/CanHo", start)
    elif sample_number in {63, 64}:
        cursor = 0
        for part in text.split(", "):
            start = text.index(part, cursor)
            cursor = start + len(part)
            add(part, "GhiChu", start)
    elif sample_number in {65, 66}:
        first, second = text.split(", ")
        add(first, "Khac", 0)
        add(second, "PhuongXa", len(first) + 2)
    else:
        match = re.fullmatch(r"((?:Ngõ|Hẻm) \S+) (.+)", text)
        if match is None:
            raise ValueError(f"Cannot split alley in sample {sample_number}: {text}")
        add(match.group(1), "Ngo/Hem", 0)
        add(match.group(2), "TenDuong", len(match.group(1)) + 1)

    spans.sort(key=lambda span: int(span["start"]))
    previous_end = 0
    for span in spans:
        assert int(span["start"]) >= previous_end
        assert span["system"] in SYSTEMS
        previous_end = int(span["end"])
    return spans


def render_markdown(rows: list[dict[str, object]]) -> str:
    lines = [
        "# Đáp án gợi ý để gán pilot T0 trong Label Studio",
        "",
        "**Trạng thái:** candidate, chưa phải gold đã duyệt. Chỉ đọc `sample_id` và `text` trong file import 68 task; không đọc `GT_*` hoặc nguồn gốc sạch.",
        "",
        "**Cách đọc:** `⟦chuỗi⟧ Nhãn/hệ`. Hệ `?` nghĩa là chọn `khong_xac_dinh` cho span. T1 `—` nghĩa là để trống phần *Whole-address system, if clear*. Mỗi span phải chọn đúng một hệ trước Submit. Dấu phẩy, khoảng trắng và dấu nối ngoài span để `O` (không quét).",
        "",
        "**Lưu ý độc lập:** Nếu đo đồng thuận giữa hai người gán, người thứ hai không được xem bảng này trước khi gán độc lập.",
        "",
        "**Nguồn kiểm tra tên hành chính:** [Nghị quyết 1685 về các đơn vị cấp xã TP.HCM](https://xaydungchinhsach.chinhphu.vn/sap-xep-dvhc-danh-sach-168-xa-phuong-dac-khu-cua-thanh-pho-ho-chi-minh-119250623085031865.htm), [đặc khu Cát Hải](https://xaydungchinhsach.chinhphu.vn/sap-xep-dvhc-danh-sach-114-xa-phuong-dac-khu-cua-thanh-pho-hai-phong-119250622201739743.htm). Tên trùng qua hai hệ vẫn để `?` nếu chính chuỗi không xác định được phiên bản.",
        "",
    ]
    for title, start, end in (
        ("01–24: Có cấp quận/huyện cũ", 1, 24),
        ("25–48: Cấu trúc hai cấp và ca cần duyệt", 25, 48),
        ("49–68: Mốc, hướng, tòa nhà, thành phần khác", 49, 68),
    ):
        lines.extend([f"## {title}", "", "| # / sample_id | Span cần quét và chọn nhãn/hệ | T1 | Cờ cần rà soát |", "| --- | --- | --- | --- |"])
        for row in rows[start - 1:end]:
            rendered_spans = "<br>".join(
                f"⟦{span['text']}⟧ **{span['label']}**/{'?' if span['system'] == 'khong_xac_dinh' else span['system']}"
                for span in row["spans"]
            )
            flags = ", ".join(row["review_flags"]) or "—"
            if row["review_note"]:
                flags += f"<br>{row['review_note']}"
            lines.append(
                f"| {row['number']:02d} / `{row['sample_id']}` | {rendered_spans} | {row['address_system'] or '—'} | {flags} |"
            )
        lines.append("")
    lines.extend([
        "## Quy tắc kiểm nhanh trước Submit",
        "",
        "1. Số vùng trong Regions đúng bằng số span ghi ở hàng đó, không gán trùng.",
        "2. Chọn `span_system` riêng cho **từng** vùng, kể cả số nhà/đường/mốc có hệ `?`.",
        "3. Chỉ tick cờ nêu trong bảng khi đúng tình huống; ghi quyết định cuối vào sổ adjudication.",
        "4. Với ca `ambiguous_label` hoặc `temporal_ambiguity`, xem đây là gợi ý để rà soát, chưa tự khóa thành gold.",
        "",
        "Các offset ký tự `[start,end)` và nguyên văn từng span nằm trong `pilot_span11_candidate_answers.json` cùng thư mục.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    if not IMPORT_PATH.exists():
        raise FileNotFoundError(IMPORT_PATH)
    imported = json.loads(IMPORT_PATH.read_text(encoding="utf-8"))
    if len(imported) != 68:
        raise ValueError(f"Expected 68 pilot tasks, found {len(imported)}")

    rows: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for number, task in enumerate(imported, start=1):
        data = task.get("data", {})
        sample_id = data.get("sample_id")
        text = data.get("text")
        if not isinstance(sample_id, str) or not isinstance(text, str):
            raise ValueError(f"Missing sample_id/text in task {number}")
        if sample_id in seen_ids:
            raise ValueError(f"Repeated sample_id: {sample_id}")
        seen_ids.add(sample_id)
        flags, note = REVIEW.get(number, ([], ""))
        rows.append({
            "number": number,
            "sample_id": sample_id,
            "text": text,
            "spans": build_spans(number, text),
            "address_system": whole_system(number),
            "review_flags": flags,
            "review_note": note,
            "status": "candidate_not_gold",
        })

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MD_PATH.write_text(render_markdown(rows), encoding="utf-8")
    print(f"Wrote {len(rows)} candidate answers to {MD_PATH}")


if __name__ == "__main__":
    main()
