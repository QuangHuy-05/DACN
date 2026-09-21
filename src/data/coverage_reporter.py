"""Generate multi-dimensional coverage report for benchmark datasets.

Covers: Source, Relationship, Region (Bac/Trung/Nam), Province, Geometry (node/way),
and Merger Form, with quality warnings for unobserved or skewed classes.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd

from src.utils.text_normalize import detect_macro_region

DIRECT_SOURCE = "OSM_Diff+vietnam-sap-nhap-phuong-xa.csv"
DERIVED_SOURCE = "OSM_Snapshot+vietnam-sap-nhap-phuong-xa.csv"
RELATIONSHIPS = ("1-1", "N-1", "1-N", "M-N")
REGIONS = ("Bac", "Trung", "Nam")
GEOMETRIES = ("node", "way")
MERGER_FORMS = ("Hợp nhất toàn bộ", "Tách — nhập chủ yếu", "Tách — một phần")


def _zero_coverage_stats() -> dict:
    """Return a renderable report state when no pair can be generated."""
    direct_relations = {relation: 0 for relation in RELATIONSHIPS}
    warnings = ["Dataset is empty"]
    warnings.extend(
        f"Quan hệ {relation} có 0 mẫu OSM diff trực tiếp (Thiếu bằng chứng). "
        "Không tạo thêm mẫu bằng suy đoán địa bàn."
        for relation in RELATIONSHIPS
    )
    return {
        "total": 0,
        "source_counts": {DIRECT_SOURCE: 0, DERIVED_SOURCE: 0},
        "relationship_counts": direct_relations.copy(),
        "geometry_counts": {geometry: 0 for geometry in GEOMETRIES},
        "region_counts": {region: 0 for region in REGIONS},
        "merger_counts": {form: 0 for form in MERGER_FORMS},
        "top_provinces": {},
        "direct_relation_counts": direct_relations,
        "warnings": warnings,
    }


def analyze_pairs_coverage(df_pairs: pd.DataFrame) -> dict:
    """Analyze Set 07 across multiple administrative, topological, and geometric axes."""
    total = len(df_pairs)
    if total == 0:
        return _zero_coverage_stats()

    # 1. Source distribution
    source_counts = df_pairs["Nguon"].value_counts().to_dict()
    source_counts.setdefault(DIRECT_SOURCE, 0)
    source_counts.setdefault(DERIVED_SOURCE, 0)

    # 2. Relationship distribution
    rel_counts = df_pairs["QuanHe"].value_counts().to_dict()
    for r in RELATIONSHIPS:
        rel_counts.setdefault(r, 0)

    # 3. Geometry (node vs way)
    def parse_geom(node_id: str) -> str:
        if isinstance(node_id, str) and ":" in node_id:
            return node_id.split(":")[0]
        return "unknown"

    geom_series = df_pairs["ID_Node"].apply(parse_geom)
    geom_counts = geom_series.value_counts().to_dict()
    for geometry in GEOMETRIES:
        geom_counts.setdefault(geometry, 0)

    # 4. Region (Bac / Trung / Nam)
    def parse_region(addr: str) -> str:
        return detect_macro_region("", addr)

    region_series = df_pairs["DiaChi_Moi"].apply(parse_region)
    region_counts = region_series.value_counts().to_dict()
    for region in REGIONS:
        region_counts.setdefault(region, 0)

    # 5. Merger Form
    merger_counts = df_pairs["HinhThucSapNhap"].value_counts().to_dict()
    for merger_form in MERGER_FORMS:
        merger_counts.setdefault(merger_form, 0)

    # 6. Province breakdown (extract last component of DiaChi_Moi)
    def parse_province(addr: str) -> str:
        parts = [p.strip() for p in str(addr).split(",") if p.strip()]
        return parts[-1] if parts else "Không rõ"

    prov_series = df_pairs["DiaChi_Moi"].apply(parse_province)
    prov_counts = prov_series.value_counts().head(10).to_dict()

    direct_mask = df_pairs["Nguon"].str.contains("OSM_Diff", na=False)
    direct_relation_counts = {
        relation: int((direct_mask & df_pairs["QuanHe"].eq(relation)).sum())
        for relation in RELATIONSHIPS
    }

    # Quality warnings
    warnings = []
    for relation in RELATIONSHIPS:
        if direct_relation_counts[relation] == 0:
            warnings.append(
                f"Quan hệ {relation} có 0 mẫu OSM diff trực tiếp (Thiếu bằng chứng). "
                "Không tạo thêm mẫu bằng suy đoán địa bàn."
            )
    direct_obs = int(direct_mask.sum())
    if direct_obs < total:
        warnings.append(
            f"Tập 07 có {total - direct_obs}/{total} mẫu được dẫn xuất từ snapshot 1 đích "
            f"({direct_obs}/{total} quan sát trực tiếp từ OSM diff)."
        )
    if region_counts.get("Trung", 0) < 0.1 * total:
        warnings.append(
            f"Độ phủ miền Trung chiếm tỷ lệ thấp ({region_counts.get('Trung', 0)}/{total}, "
            f"{region_counts.get('Trung', 0)/total*100:.1f}%) do mật độ đóng góp OSM tập trung tại Hà Nội và TP.HCM."
        )

    return {
        "total": total,
        "source_counts": source_counts,
        "relationship_counts": rel_counts,
        "geometry_counts": geom_counts,
        "region_counts": region_counts,
        "merger_counts": merger_counts,
        "top_provinces": prov_counts,
        "direct_relation_counts": direct_relation_counts,
        "warnings": warnings,
    }


def generate_coverage_markdown(stats: dict) -> str:
    """Render the multidimensional coverage statistics into Markdown format."""
    total = stats["total"]
    lines = [
        "# Báo Cáo Độ Phủ Đa Chiều Benchmark Địa Chỉ Hành Chính 2025",
        "",
        f"**Tổng số mẫu đánh giá (Tập 07):** {total} cặp ánh xạ hai chiều đã xác minh.",
        "",
        "---",
        "",
        "## 1. Phân Bố Theo Bằng Chứng Nguồn (Evidence Source)",
        "",
        "| Nguồn Dữ Liệu | Số lượng | Tỷ lệ (%) | Bản chất |",
        "| :--- | :---: | :---: | :--- |",
    ]

    denominator = total or 1
    for src in (DIRECT_SOURCE, DERIVED_SOURCE):
        cnt = stats["source_counts"].get(src, 0)
        pct = cnt / denominator * 100
        desc = "Quan sát trực tiếp từ lịch sử thay đổi OSM" if "Diff" in src else "Dẫn xuất an toàn từ snapshot cũ có đúng 1 đích"
        lines.append(f"| `{src}` | {cnt} | {pct:.1f}% | {desc} |")

    lines.extend([
        "",
        "## 2. Phân Bố Theo Quan Hệ Đồ Thị Sáp Nhập (Relationship Graph)",
        "",
        "| Quan Hệ | Tên gọi | Số lượng | Tỷ lệ (%) | Bằng chứng OSM diff | Ghi chú an toàn |",
        "| :---: | :--- | :---: | :---: | :---: | :--- |",
    ])

    rel_names = {
        "1-1": "Đổi tên / giữ nguyên cấp (C)",
        "N-1": "Hợp nhất nhiều xã vào một (B)",
        "1-N": "Tách một xã thành nhiều xã (A)",
        "M-N": "Tái cơ cấu phức hợp nhiều-nhiều (M)",
    }
    for rel in RELATIONSHIPS:
        cnt = stats["relationship_counts"].get(rel, 0)
        pct = cnt / denominator * 100
        diff_cnt = stats["direct_relation_counts"].get(rel, 0)
        note = "Quan sát đích thực tế" if diff_cnt > 0 else "Thiếu bằng chứng OSM diff"
        lines.append(f"| **{rel}** | {rel_names.get(rel, rel)} | {cnt} | {pct:.1f}% | {diff_cnt} | {note} |")

    lines.extend([
        "",
        "## 3. Phân Bố Vùng Miền (Geographic Regions)",
        "",
        "| Vùng Miền | Số lượng | Tỷ lệ (%) | Đặc điểm |",
        "| :--- | :---: | :---: | :--- |",
    ])

    for reg in REGIONS:
        cnt = stats["region_counts"].get(reg, 0)
        pct = cnt / denominator * 100
        lines.append(f"| **{reg}** | {cnt} | {pct:.1f}% | Đại diện các tỉnh/thành vùng {reg} |")

    lines.extend([
        "",
        "## 4. Phân Bố Hình Học OSM (OSM Geometry)",
        "",
        "| Đối tượng OSM | Số lượng | Tỷ lệ (%) | Vai trò |",
        "| :--- | :---: | :---: | :--- |",
    ])

    for geom in GEOMETRIES:
        cnt = stats["geometry_counts"].get(geom, 0)
        pct = cnt / denominator * 100
        desc = "Điểm địa chỉ độc lập" if geom == "node" else "Đối tượng OSM dạng way"
        lines.append(f"| `{geom}` | {cnt} | {pct:.1f}% | {desc} |")

    lines.extend([
        "",
        "## 5. Phân Bố Hình Thức Sáp Nhập (Merger Forms)",
        "",
        "| Hình thức sáp nhập | Số lượng | Tỷ lệ (%) |",
        "| :--- | :---: | :---: |",
    ])

    for form in MERGER_FORMS:
        cnt = stats["merger_counts"].get(form, 0)
        pct = cnt / denominator * 100
        lines.append(f"| {form if form else 'Không phân loại'} | {cnt} | {pct:.1f}% |")

    lines.extend([
        "",
        "## 6. Top Tỉnh / Thành Phố Đại Diện",
        "",
        "| Tỉnh / Thành Phố | Số lượng | Tỷ lệ (%) |",
        "| :--- | :---: | :---: |",
    ])

    for prov, cnt in stats["top_provinces"].items():
        pct = cnt / denominator * 100
        lines.append(f"| {prov} | {cnt} | {pct:.1f}% |")

    lines.extend([
        "",
        "---",
        "",
        "## 7. Cảnh Báo Chất Lượng & Ngưỡng Kiểm Soát (Quality Warnings)",
        "",
    ])

    if stats["warnings"]:
        for warn in stats["warnings"]:
            lines.append(f"> [!WARNING]\n> {warn}\n")
    else:
        lines.append("> [!NOTE]\n> Mọi tiêu chí kiểm tra chất lượng đều đạt ngưỡng cam kết.\n")

    return "\n".join(lines) + "\n"


def generate_and_save_coverage_report(df_pairs: pd.DataFrame, output_path: Path) -> dict:
    """Calculate coverage stats, format markdown, save to file and return stats dictionary."""
    stats = analyze_pairs_coverage(df_pairs)
    md_content = generate_coverage_markdown(stats)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md_content, encoding="utf-8")
    return stats
