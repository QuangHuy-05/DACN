# Báo cáo Kiểm toán và Khoảng cách Dữ liệu Gazetteer v1 (S3-v1 Gap Audit)

**Ngày lập:** 29/09/2026
**Đối tượng kiểm toán:** Gói `data/processed/gazetteer/s3_v1/`
**Mục tiêu:** Xác định hiện trạng, kiểm tra tính toàn vẹn và khóa hợp đồng dữ liệu cho gói `s3_v2`.

---

## 1. Hiện trạng Thực tế của Gói `s3_v1`

| Chỉ số | Giá trị trong Manifest v1 | Trạng thái Thực tế |
| :--- | :--- | :--- |
| **Tổng số Entity** | 14.144 | - Cũ: 63 tỉnh, **691** quận/huyện có cạnh cấp xã, 10.035 phường/xã<br/>- Mới: 34 tỉnh/thành mới, 3.321 phường/xã mới. Năm huyện đảo không có xã cũ chưa được tạo entity ở v1. |
| **Cạnh nguyên tử (Atomic Edges)** | 10.597 | Cũ $\to$ Mới có đủ khóa 3 cấp `(tỉnh, huyện, xã)` |
| **Chuyển đổi Phi nguyên tử** | 5 | 5 huyện đảo chuyển thành Đặc khu (không có cấp xã cũ) |
| **Alias đã kiểm chứng** | 187 | Từ `src/data/administrative_alias.py` |
| **Phân bố quan hệ cạnh** | 10.597 cạnh | - `B/N-1` (Gộp): 9.432 cạnh (89,0%)<br/>- `M/M-N` (Phức hợp): 1.030 cạnh (9,7%)<br/>- `C/1-1` (Bảo toàn/Đổi tên): 132 cạnh (1,2%)<br/>- `A/1-N` (Tách): 3 cạnh (0,03%) |

---

## 2. Các Khoảng cách Dữ liệu Cốt lõi (Critical Gaps)

1. **Trạng thái Xác minh Mã Cấp Xã Cũ (Old Ward Codes):**
   - **Thực tế:** 10.035 phường/xã cũ đều có giá trị trong cột `candidate_code` lấy từ `third_party/vietnamadminunits`.
   - **Khoảng cách:** **0 / 10.035** mã cũ có nguồn xác minh chính thức từ cơ quan nhà nước được lưu vết trong repository. Toàn bộ mang trạng thái `candidate_third_party_unverified`.
   - **Quy tắc:** Tuyệt đối không tự động nâng cấp `candidate_code` thành `official_code`.
2. **5 Dòng Chuyển đổi Cấp Huyện:**
   - Các huyện đảo: Bạch Long Vĩ, Côn Đảo, Hoàng Sa, Lý Sơn, Cồn Cỏ không chia cấp xã ở hệ cũ, chuyển trực tiếp thành "Đặc khu".
   - Trong `s3_v1`, 5 dòng này bị bỏ qua (`skipped_mapping_rows`).
   - Trong `s3_v2`, cần xuất riêng thành bảng `non_atomic_transitions.csv` với trạng thái `NOT_WARD_EDGE`.
3. **Mốc Thời gian Hiệu lực (Temporal Validity):**
   - Mốc ranh giới: `2025-07-01`.
   - Hệ mới: `valid_from = 2025-07-01`, `valid_to = null`.
   - Hệ cũ: `valid_to = 2025-06-30`. Cột `valid_from` để trống (`null`) vì chưa có văn bản xác minh mốc thành lập của từng đơn vị cũ trong lịch sử.
4. **Giới hạn Tọa độ & Hình học:**
   - Gói gazetteer hiện tại hoàn toàn là dữ liệu quan hệ danh mục (relational/topological), **không có tọa độ (lat/lon) hoặc ranh giới hình học (polygon)**.
   - Khi gặp quan hệ `A/1-N` hoặc `M/M-N`, không được suy diễn đích duy nhất nếu thiếu bằng chứng ngữ cảnh hoặc địa chỉ cụ thể.

---

## 3. Hợp đồng Dữ liệu Gói `s3_v2`

| Tệp đầu ra | Cấu trúc Cột | Mục đích |
| :--- | :--- | :--- |
| `entities.csv` | `entity_id, level, system, canonical_name, parent_id, official_code, candidate_code, candidate_code_source_id, candidate_code_source_hash, code_status, valid_from, valid_to, source_id, source_hash, status` | Lưu toàn bộ thực thể hành chính đa phiên bản |
| `edges.csv` | `old_entity_id, new_entity_id, old_province, old_district, old_ward, new_province, new_ward, new_ward_code, relation, merge_form, source_row, source_id, source_hash` | Lưu các cạnh nguyên tử có đủ khóa 3 cấp cũ |
| `aliases.csv` | `entity_id, alias, system, level, source_id, source_hash` | Lưu tên gọi khác/viết tắt đã kiểm chứng |
| `non_atomic_transitions.csv` | `source_row, old_entity_id, new_entity_id, old_province, old_district, new_province, new_ward, new_ward_code, new_unit_type, merge_form, relation, status, source_id, source_hash` | Lưu 5 ca chuyển đổi đặc thù cấp huyện $\to$ đặc khu, tra được qua lookup |
| `source_register.csv` | `source_id, name, path_or_url, level_scope, system, valid_range, license, sha256, role` | Sổ đăng ký nguồn kiểm toán |
| `coverage_report.json` | Thống kê số lượng, tỷ lệ xác minh, phân bố quan hệ | Đo lường độ phủ thực tế |
| `manifest.json` | Hash SHA-256 của script, nguồn và tệp đầu ra | Bảo chứng tính toàn vẹn dữ liệu |
