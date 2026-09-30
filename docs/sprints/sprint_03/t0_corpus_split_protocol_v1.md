# Giao thức Phân tách Corpus T0/T1 (v1.0) — Sprint 3

**Phiên bản:** `v1.0`
**Ngày tạo bản ứng viên:** 29/09/2026. **Trạng thái:** chờ chủ dự án xác nhận trước khi mở project test.
**Seed cố định:** `42`
**Guideline áp dụng:** `s3-span-v1.1`
**Cấu hình Label Studio:** `configs/label_studio_span11.xml`

---

## 1. Mục tiêu và nguyên tắc kiểm soát rò rỉ

Giao thức này quy định việc xây dựng corpus T0 (11 nhãn span) và T1 (hệ quy chiếu `cu/moi/Lai`) phục vụ huấn luyện và đánh giá các mô hình trong Sprint 3:
1. **Phân tách ở cấp Nhóm Địa chỉ Gốc (Site Group):**
   - Khóa nhóm bảo thủ: `site_group(house, street)` = `SHA-256("site|" + norm(house) + "|" + norm(street))[:20]`.
   - Mọi biến thể sinh tổng hợp (nhiễu OCR, thiếu trường, địa chỉ lai) hoặc cặp lịch sử cùng vị trí **bắt buộc** phải thuộc cùng một split với mẫu cha (`parent_sample_id`).
   - Cùng `group_id` tuyệt đối không được xuất hiện ở cả `train`, `dev` và `test`.
2. **Loại trừ Toàn bộ Benchmark Khỏi Train/Dev:**
   - 4.017 nhóm theo khóa `site_group()` xuất hiện trong toàn bộ 6 tập benchmark (01, 02, 03, 04, 06, 07) bị chặn khỏi ứng viên train/dev. Khóa này là một lớp bảo vệ; cặp gần trùng vẫn phải rà thủ công.
   - Tập `test` chính thức của T0 là đúng **100 mẫu frozen** đã khóa tại `data/interim/annotation/sprint03/test_hold_manifest_v1.json` (20 mẫu từ mỗi tập 01, 02, 03, 04, 06).
   - 20 mẫu VQA `external_test_hold` tiếp tục ở trạng thái `HOLD`, không đưa vào corpus v1 lần này.
3. **Quy mô và Tỷ lệ Phân tầng:**
   - Mục tiêu khởi động: ~300 mẫu train/dev (gồm 68 pilot gold đã nghiệm thu + ~232 mẫu batch 02 mới).
   - Phân chia train/dev xấp xỉ 80/20 theo **cụm nhóm** (group-disjoint split), không xé lẻ các mẫu trong cùng nhóm để cố đạt tỷ lệ số dòng.
   - Bản preflight ngày 30/09 phân 240 train / 60 dev; 172 biến thể có parent là **bản ghi OSM nguồn chưa gán**, được đăng ký trong `source_parent_manifest.csv` với cùng group/split. `parent_sample_id=osm_row_<source_row>` là ID neo nguồn, không phải một gold annotation riêng.

---

## 2. Nguồn Dữ liệu Hợp lệ và Chặn trùng

| Vai trò | Nguồn được phép | Nguồn cấm / Chặn |
| :--- | :--- | :--- |
| **Train / Dev** | - 68 pilot gold (`pilot_gold_v1.jsonl`)<br/>- OSM Snapshot cũ/mới ngoài benchmark (`data/interim/osm/osm_old_snapshot_full.csv`, `osm_latest_clean.csv`)<br/>- Biến thể tổng hợp có parent thuộc train/dev | - Toàn bộ 4.017 nhóm thuộc Benchmark 01, 02, 03, 04, 06, 07<br/>- 100 mẫu benchmark test hold<br/>- Dữ liệu VQA và địa chỉ khách hàng thật |
| **Test T0 Chính** | - Đúng 100 mẫu frozen trong `test_hold_manifest_v1.json` | - Không lấy mẫu ngoài 100 ID đã chốt<br/>- Không thay thế ca khó |

---

## 3. Quy tắc Rà soát Chéo (Cross-Deduplication Protocol)

1. **Exact Text Hash:** SHA-256 của chuỗi văn bản nguyên bản UTF-8. Trùng exact hash giữa các split là vi phạm nghiêm trọng (`BLOCKED_SPLIT`).
2. **Normalized Text Hash:** Chuyển về chữ thường, bỏ dấu thanh, chuẩn hóa khoảng trắng.
3. **Near Duplicate Scanning:** Sử dụng `difflib.SequenceMatcher` với ngưỡng `0.85`.
   - Mọi cặp qua **train–dev, train–test, dev–test** có similarity $\ge 0.85$ được đưa vào danh sách kiểm toán (`near_duplicate_review_queue.csv`). Bản preflight hiện có 138 cặp.
   - Người kiểm duyệt quyết định ca trùng thực tế hay chỉ trùng tên đường phổ biến.
   - Quyết định được lưu riêng trong `near_duplicate_decisions.csv` với `decision`, `reason`, `reviewer`; cặp `same_site`/`uncertain` chặn phát hành cho đến khi sửa split/nguồn hoặc có bằng chứng mới.

---

## 4. Đặc tả Metadata Từng Mẫu (Manifest Contract)

Mỗi mẫu trong corpus v1 có đầy đủ các trường provenance:
- `sample_id`: Khóa định danh duy nhất (ví dụ: `s3_...`).
- `text_sha256`: Hash của chuỗi địa chỉ.
- `source_dataset`: Tên tập nguồn gốc.
- `source_ref`: Đường dẫn tương đối file nguồn.
- `source_file_sha256`: Hash của file nguồn.
- `source_row`: Dòng nguồn hoặc ID đối tượng.
- `source_group`: Mã nhóm chống rò rỉ (`group_id`).
- `parent_sample_id`: ID của mẫu cha nếu là biến thể sinh tổng hợp.
- `derivation`: Nguồn gốc (`observed_verified`, `synthetic_controlled`, `derived_mapping`).
- `observed_or_synthetic`: `observed` hoặc `synthetic`.
- `split`: `train`, `dev`, hoặc `test`.
- `stratum`: Nhóm phân tầng.
- `guideline_version`: Phiên bản hướng dẫn (`s3-span-v1.1`).
- `annotation_export_hash`: Hash bản export Label Studio tương ứng.
- `review_status`: Trạng thái nghiệm thu (`APPROVED_GOLD`, `PILOT_GOLD`, `PENDING_REVIEW`).

---

## 5. Quy trình Nghiệm thu và Cổng Bàn giao

1. **Cổng Label Studio:** Task import vào Label Studio **chỉ chứa** `data.sample_id` và `data.text`. Không lộ nhãn ground truth hoặc metadata.
2. **Cổng QA Cấu trúc:** 100% mẫu có `text[start:end]` khớp tuyệt đối, không chồng lấn, đủ 11 nhãn schema, thuộc tính hệ hợp lệ.
3. **Cổng Duyệt Người:** Biên bản nghiệm thu có chữ ký/email của người duyệt; không tự động phong cấp gold.
