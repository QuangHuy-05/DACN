"""Generate a data-derived baseline report without fixed scores or examples."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.evaluation.scorer import _norm
from src.evaluation.schema import STANDARD_FIELDS


def _pct(numerator: int, denominator: int) -> str:
    return f"{100 * numerator / denominator:.1f}%" if denominator else "n/a"


def _table_counts(frame: pd.DataFrame, group_name: str) -> list[str]:
    lines = ["| Nhóm | Công cụ | n | Đúng | Một phần | Sai |", "| --- | --- | ---: | ---: | ---: | ---: |"]
    for tool, sub in frame.groupby("CongCu", sort=True):
        n = len(sub)
        counts = sub["DungSai"].value_counts()
        lines.append(f"| {group_name} | `{tool}` | {n} | {_pct(counts.get('CORRECT', 0), n)} | {_pct(counts.get('PARTIAL', 0), n)} | {_pct(counts.get('ERROR', 0), n)} |")
    return lines


def _pred(row: pd.Series) -> dict[str, str]:
    return json.loads(row["TruongDuDoan"])


def _field_f1(frame: pd.DataFrame, field: str | None = None) -> float | None:
    """Micro F1; a wrong nonempty value contributes both FP and FN."""
    tp = fp = fn = 0
    fields = (field,) if field else STANDARD_FIELDS
    for _, row in frame.iterrows():
        prediction, truth = _pred(row), json.loads(row["TruongDung"])
        for name in fields:
            p, t = _norm(prediction.get(name, "")), _norm(truth.get(name, ""))
            if p and p == t:
                tp += 1
            elif p and t:
                fp += 1
                fn += 1
            elif p:
                fp += 1
            elif t:
                fn += 1
    return 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None


def _field_f1_table(frame: pd.DataFrame) -> list[str]:
    lines = ["| Công cụ | SoNha F1 | TenDuong F1 | PhuongXa F1 | QuanHuyen F1 | TinhThanh F1 |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for tool, sub in frame.groupby("CongCu"):
        values = [_field_f1(sub, field) for field in STANDARD_FIELDS]
        lines.append("| `" + tool + "` | " + " | ".join("n/a" if value is None else f"{value:.3f}" for value in values) + " |")
    return lines


def generate_baseline_report_markdown(
    df_eval: pd.DataFrame,
    manifest_data: dict | None = None,
    benchmark_dir: Path | None = None,
    raw_log_path: Path | None = None,
) -> str:
    """Summarize observed outputs under the protocol recorded in the manifest."""
    root = Path(__file__).resolve().parents[2]
    benchmark_dir = benchmark_dir or root / "data/processed/benchmark"
    manifest_data = manifest_data or {}
    tools = sorted(df_eval["CongCu"].unique())
    lines = [
        "# Đánh giá baseline địa chỉ Việt Nam 2025",
        "",
        f"- Ngày tạo: {pd.Timestamp.now().strftime('%d/%m/%Y')}",
        f"- Dòng benchmark: {sum(item['row_count'] for item in manifest_data.get('datasets', {}).values())}; lượt dự đoán: {len(df_eval)}.",
        f"- Công cụ thực chạy: {', '.join(f'`{tool}`' for tool in tools)}.",
        "- VietnamAdminUnits nhận mode do protocol cung cấp ở Data 01/02/03/04, chạy hai mode ở Data 06 và convert cũ → mới ở Data 07. Đây không phải phép đo phân loại T1 tự động.",
        "- `libpostal` gọi Python binding của thư viện C và model data mặc định; raw nhãn Libpostal được lưu riêng trước khi ánh xạ sang 5 trường.",
        "- `exact_match_rate` yêu cầu mọi trường được chấm khớp sau chuẩn hóa. `micro_f1_scored_fields` gộp TP/FP/FN trên các trường được chấm; một MISMATCH đóng góp một FP và một FN.",
        "",
        "## 1. Dữ liệu và khả năng tái lập",
        "",
        "| File | Dòng | SHA-256 |",
        "| --- | ---: | --- |",
    ]
    for name, info in manifest_data.get("datasets", {}).items():
        lines.append(f"| `{name}` | {info['row_count']} | `{info['sha256']}` |")
    raw_path = raw_log_path or root / "data/processed/evaluation/baseline_raw_responses.jsonl"
    if raw_path.exists() and manifest_data.get("output_hashes"):
        raw_logs = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines()]
        if len(raw_logs) != len(df_eval):
            raise ValueError("Raw response count does not match prediction count")
        statuses = pd.DataFrame(raw_logs).groupby(["tool", "status"]).size()
        lines += ["", "Trạng thái lời gọi công cụ (raw log):", "", "| Công cụ | Trạng thái | n |", "| --- | --- | ---: |"]
        for (tool, status), count in statuses.items():
            lines.append(f"| `{tool}` | `{status}` | {count} |")
    lines += [
        "",
        f"- Phiên bản công cụ: `{json.dumps(manifest_data.get('baseline_tools', {}), ensure_ascii=False)}`.",
        f"- Python `{manifest_data.get('python_version', 'unknown')}`; thư viện chạy: `{json.dumps(manifest_data.get('runtime_packages', {}), ensure_ascii=False)}`.",
        f"- Hash mã khi chạy prediction: `{json.dumps(manifest_data.get('code_hashes', {}), ensure_ascii=False)}`.",
        f"- Hash mã tạo báo cáo: `{manifest_data.get('reporter_sha256', 'unknown')}`.",
        "- Data 07 chỉ có N-1/M-N và tập trung ở miền Bắc; không suy rộng sang 1-1/1-N hay các vùng chưa có mẫu.",
        "",
        "## 2. Parse địa chỉ theo các tập 01, 03, 04 và 06",
        "",
        "Tỷ lệ dưới đây là exact match 5 trường. Data 03 là benchmark hệ cũ sạch hoàn toàn có đủ 5 trường (không còn dòng thiếu tự nhiên). Riêng Data 04 chấm trích xuất các trường còn trên chuỗi bề mặt (phục hồi trường bị lược được phân tích riêng ở Mục 4); Data 06 báo hai mode VietnamAdminUnits riêng.",
        "",
    ]
    for prefix, title in (("D01_", "01 mới"), ("D03_", "03 cũ"), ("D04_", "04 thiếu trường")):
        sub = df_eval[df_eval["ID"].str.startswith(prefix)]
        lines += [f"### Data {title}", "", *_table_counts(sub, title), "", "Micro F1 từng trường:", "", *_field_f1_table(sub), ""]
    hybrid = df_eval[df_eval["ID"].str.startswith("D06_")].copy()
    if not hybrid.empty:
        hybrid["mode"] = hybrid["ID"].map(lambda x: "FROM_2025" if x.endswith("_m25") else ("LEGACY" if x.endswith("_mleg") else "single parse"))
        lines += ["### Data 06 lai", ""]
        for mode, sub in hybrid.groupby("mode"):
            lines += [f"**{mode}**", "", *_table_counts(sub, mode), ""]
        hybrid_source = pd.read_csv(benchmark_dir / "06_hybrid_addresses_600.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
        hybrid["kind"] = hybrid["ID"].map(lambda value: hybrid_source.iloc[int(value.split("_")[1])]["KieuLai"].split("_")[0])
        lines += ["Theo kiểu lai:", "", "| Công cụ | Mode | Kiểu | n | Đúng toàn phần |", "| --- | --- | --- | ---: | ---: |"]
        for (tool, mode, kind), sub in hybrid.groupby(["CongCu", "mode", "kind"], sort=True):
            lines.append(f"| `{tool}` | {mode} | {kind} | {len(sub)} | {_pct(int(sub['DungSai'].eq('CORRECT').sum()), len(sub))} |")

    lines += ["## 3. Data 02: độ bền trên cặp sạch và nhiễu", "", "Các nhóm nhiễu có thể đồng xuất hiện. `dinh_dang_phan_cach` có ở mọi dòng, nên bảng theo loại không diễn giải quan hệ nhân quả riêng của từng phép biến đổi. F1 trong mục này là `micro_f1_scored_fields`.", "", "| Công cụ | Mức | n | Sạch đúng | Nhiễu đúng | Micro F1 sạch | Micro F1 nhiễu | Sạch đúng → nhiễu sai |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    d02 = df_eval[df_eval["ID"].str.startswith("D02_")].copy()
    if not d02.empty:
        meta = pd.read_csv(benchmark_dir / "02_raw_noisy_synthetic_1000.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig").set_index("ID")
        d02["base_id"] = d02["ID"].str.extract(r"D02_([^_]+)")[0]
        for tool in sorted(d02["CongCu"].unique()):
            sub = d02[d02["CongCu"] == tool]
            clean = sub[sub["ID"].str.endswith("_clean")].set_index("base_id")
            noisy = sub[sub["ID"].str.endswith("_noisy")].set_index("base_id")
            if set(clean.index) != set(noisy.index):
                raise ValueError(f"Unpaired Data 02 predictions for {tool}")
            for level in ("nhe", "vua", "nang", "all"):
                ids = clean.index if level == "all" else clean.index[meta.loc[clean.index, "MucDoNhieu"].eq(level)]
                c, n = clean.loc[ids], noisy.loc[ids]
                c_ok, n_ok = c["DungSai"].eq("CORRECT"), n["DungSai"].eq("CORRECT")
                flips = int((c_ok & ~n_ok).sum())
                clean_f1, noisy_f1 = _field_f1(c), _field_f1(n)
                lines.append(f"| `{tool}` | {level} | {len(ids)} | {_pct(int(c_ok.sum()), len(ids))} | {_pct(int(n_ok.sum()), len(ids))} | {clean_f1:.3f} | {noisy_f1:.3f} | {flips} |")
        lines += ["", "### Nhóm phép biến đổi đồng xuất hiện", "", "Một dòng có thể thuộc nhiều nhóm, do đó không cộng các mẫu số và không xem chênh lệch là hiệu ứng nhân quả.", "", "| Công cụ | Phép biến đổi | n | Sạch đúng | Nhiễu đúng | F1 sạch | F1 nhiễu |", "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
        for tool in sorted(d02["CongCu"].unique()):
            sub = d02[d02["CongCu"] == tool]
            clean = sub[sub["ID"].str.endswith("_clean")].set_index("base_id")
            noisy = sub[sub["ID"].str.endswith("_noisy")].set_index("base_id")
            for operation in ("viet_tat", "bo_dau", "loi_ocr_ky_tu", "thieu_", "dao_thu_tu_hanh_chinh", "dinh_dang_phan_cach"):
                ids = clean.index[meta.loc[clean.index, "LoaiNhieu"].str.contains(operation, regex=False)]
                if not len(ids):
                    continue
                c, n = clean.loc[ids], noisy.loc[ids]
                lines.append(f"| `{tool}` | `{operation}` | {len(ids)} | {_pct(int(c['DungSai'].eq('CORRECT').sum()), len(ids))} | {_pct(int(n['DungSai'].eq('CORRECT').sum()), len(ids))} | {_field_f1(c):.3f} | {_field_f1(n):.3f} |")
    lines += ["", "## 4. Data 04: phục hồi trường đã lược", "", "Bảng này tách khỏi điểm parse trường còn hiện diện. Điền đúng một trường đã lược là phục hồi đúng; điền sai mới là suy đoán sai.", "", "| Công cụ | Trường bị lược | n | Phục hồi đúng | Điền sai | Không điền |", "| --- | --- | ---: | ---: | ---: | ---: |"]
    missing = pd.read_csv(benchmark_dir / "04_missing_fields_800.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    drop_fields = {"drop_ward": ("PhuongXa",), "drop_district": ("QuanHuyen",), "drop_housenumber": ("SoNha",), "drop_housenumber_ward": ("SoNha", "PhuongXa")}
    d04 = df_eval[df_eval["ID"].str.startswith("D04_")]
    for tool, sub in d04.groupby("CongCu"):
        by_kind = {kind: {"correct": 0, "wrong": 0, "empty": 0} for kind in drop_fields}
        for _, row in sub.iterrows():
            source = missing.iloc[int(row["ID"].split("_")[1])]
            counts = by_kind[source["KieuThieu"]]
            for field in drop_fields[source["KieuThieu"]]:
                value = _norm(_pred(row).get(field, ""))
                truth = _norm(source[f"GT_{field}"])
                counts["correct" if value and value == truth else ("wrong" if value else "empty")] += 1
        for kind, counts in (*by_kind.items(), ("tất cả", {key: sum(group[key] for group in by_kind.values()) for key in ("correct", "wrong", "empty")})):
            total = sum(counts.values())
            lines.append(f"| `{tool}` | {kind} | {total} | {counts['correct']} | {counts['wrong']} | {counts['empty']} |")
    lines += ["", "## 5. Data 07: chuyển đổi hành chính cũ → mới", "", "Chỉ VietnamAdminUnits có API converter và chỉ hai trường `PhuongXa`, `TinhThanh` được chấm. Không có thử nghiệm chiều mới → cũ; API hiện tại không cung cấp tác vụ đó.", "", "| Quan hệ | n | Đúng cặp đơn vị | Sai đích có output | Trả rỗng |", "| --- | ---: | ---: | ---: | ---: |"]
    d07 = df_eval[df_eval["ID"].str.startswith("D07_")]
    for relation in ("N-1", "M-N"):
        sub = d07[d07["ID"].str.endswith(relation)]
        if sub.empty:
            lines.append(f"| {relation} | 0 | n/a | n/a | n/a |")
            continue
        correct = int(sub["DungSai"].eq("CORRECT").sum())
        empty = int(sub.apply(lambda row: not _pred(row).get("PhuongXa", ""), axis=1).sum())
        lines.append(f"| {relation} | {len(sub)} | {correct} ({_pct(correct, len(sub))}) | {len(sub) - correct - empty} | {empty} |")
    lines += ["", "## 6. Mẫu lỗi truy vết", "", "Các dòng sau lấy trực tiếp từ CSV dự đoán; `ID` dùng để tra raw response cùng khóa ID/công cụ.", "", "| ID | Công cụ | Input | Dự đoán | Đáp án |", "| --- | --- | --- | --- | --- |"]
    for prefix in ("D01_", "D03_", "D04_", "D06_", "D07_"):
        subset = df_eval[df_eval["ID"].str.startswith(prefix) & df_eval["DungSai"].ne("CORRECT")]
        if not subset.empty:
            row = subset.iloc[0]
            if prefix == "D07_":
                fields = ("PhuongXa", "TinhThanh")
                prediction = {field: _pred(row).get(field, "") for field in fields}
                truth = {field: json.loads(row["TruongDung"]).get(field, "") for field in fields}
                cells = [row["ID"], row["CongCu"], row["DiaChiGoc"], json.dumps(prediction, ensure_ascii=False), json.dumps(truth, ensure_ascii=False)]
            else:
                cells = [row["ID"], row["CongCu"], row["DiaChiGoc"], row["TruongDuDoan"], row["TruongDung"]]
            lines.append("| " + " | ".join(str(cell).replace("|", "\\|").replace("\n", " ") for cell in cells) + " |")
    lines += ["", "## 7. Giới hạn", "", "- Điểm VietnamAdminUnits ở Data 01/02/03/04 có oracle mode, chưa đo T1. Data 06 không đo khả năng cảnh báo địa chỉ lai vì API không trả nhãn cảnh báo.", "- T0 theo 11 nhãn span chưa thể đo vì bộ hiện tại chỉ có ground truth 5 trường địa chỉ.", "- Data 02 là nhiễu tổng hợp; các loại nhiễu đồng xuất hiện và không chứng minh độ bền trên hóa đơn thật.", "- Các trường OSM là nhãn cộng đồng; Data 03 hiện đã được chuẩn hóa và lọc sạch hoàn toàn 100% đủ cả 5 trường (không còn dòng thiếu tự nhiên). Data 04 được sinh có kiểm soát từ các địa chỉ sạch, giữ nguyên ground truth trước khi xóa.", "- Data 07 dựa trên OSM diff quan sát được và bảng hành chính; cần đọc coverage trước khi ngoại suy. Converter có thể gọi ArcGIS geocoder qua mạng, nên lần chạy sau cần ghi nhận điều kiện dịch vụ khi so sánh kết quả.", ""]
    return "\n".join(lines)
