# Nguồn mã và reconciliation — 03/10/2026

## Kết luận

Đã hoàn thành kiểm kê, tái tạo số lượng và phân loại **615 ca** cần đối chiếu. **0 mã được xác minh mới**. Chưa đủ bằng chứng về thời kỳ của hai CSV để phát hành gazetteer mới; s3_v1/s3_v2 giữ nguyên. Đây là kết quả audit, không phải cổng xác nhận mã đã qua.

Evidence root: `data/interim/modeling/sprint03/task_01_06_20261003_v1/`.

## 1. Provenance hai CSV

| CSV bên thứ ba | Hàng | Bytes | SHA-256 |
|---|---:|---:|---|
| ward_2025-07-18.csv | 10.035 | 780.242 | `494074f7b7a6f3ee01f4c198e8182cf31856b9a1274be00e0e286b44754b2a26` |
| district_2025-07-18.csv | 696 | 40.177 | `4fa4e90fe869fab149da656e728ab455ea39a69c653d18b38824ff9c3697abd7` |

Cả hai dùng UTF-8-sig. Mã đọc như chuỗi, không bỏ zero đầu. Ghi chú tải nguồn chỉ dẫn về cổng GSO, không lưu câu truy vấn/export gốc, ngày tham chiếu, ngày hiệu lực hoặc document ID. **18/07/2025 trong tên file không chứng minh ngày snapshot**. License MIT của thư viện không tự xác định quyền dùng CSV dẫn xuất.

[Source register v3](../../../data/interim/modeling/sprint03/task_01_06_20261003_v1/source_register_v3.json) ghi schema/column, hash, cơ quan được dẫn, URL, locator, license scope và từng trường chưa xác minh. Đường dẫn local của register tính từ root repository.

Nguồn chính thức đã tìm:

- [Cổng đối chiếu của Cục Thống kê](https://danhmuchanhchinh.nso.gov.vn/Doi_Chieu_Moi.aspx): HTTP200; HTML hiện tại lưu tại `source_evidence/nso_current_portal.html`, SHA `e3215ca2d000322d8d83f08d2fd20766f06c45ce1747c57b441aba35af9fffbf`. Đây là bằng chứng truy cập hiện tại, không xác thực hai export cũ. Host GSO gốc gặp lỗi DNS; log tại `source_evidence/access_log.json`.
- [Quyết định 124/2004/QĐ-TTg](https://vbpl.vn/bonoivu/Pages/vbpq-toanvan.aspx?ItemID=17617): nguồn lịch sử; thiếu chuỗi sửa đổi và transcription đã duyệt để coi là bảng tại 30/06/2025.
- [Quyết định 19/2025/QĐ-TTg bản ký](https://datafiles.chinhphu.vn/cpp/files/vbpq/2025/7/19ttg.signed.pdf) và [phụ lục trên NSO](https://www.nso.gov.vn/wp-content/uploads/2025/07/19_2025_qd-ttg_30062025-signed-6-143-da-nen.pdf): nguồn hệ mới; không dùng để xác nhận mã xã/huyện cũ.

Các ấn phẩm này chưa được chép thành bảng tham chiếu có phê duyệt từng dòng. Register phân biệt URL nguồn chính thức với một CSV tham chiếu đã đủ điều kiện.

## 2. Đối chiếu full key và 615 ca

| Cấp cũ | Exact key + mã khớp nội bộ | Không exact match | Key khớp nhưng gazetteer thiếu mã |
|---|---:|---:|---:|
| Xã/phường | 9.451 / 10.035 | 584 | 0 |
| Quận/huyện | 665 / 696 | 26 | 5 |

Khóa giữ đầy đủ tỉnh–huyện–xã cho cấp xã và tỉnh–huyện cho cấp huyện. Không tái dựng mã từ số, không chọn theo tên đơn lẻ. Exact match nội bộ **không bằng xác minh nguồn có thẩm quyền và thời kỳ**.

| Nhóm 615 ca | Số ca | Xử lý |
|---|---:|---|
| Khác dấu/cách đặt dấu sau kiểm từng thành phần | 517 | Candidate đối chiếu; chưa trở thành alias mới |
| Khác tên hoặc khóa cha cần bằng chứng theo ngày | 93 | Giữ unresolved; lưu chênh lệch từng cấp |
| Key tìm được trong raw nhưng gazetteer chưa có mã | 5 | Lưu raw code candidate; chưa tự điền |

Đầu ra tại `source_reconciliation/`:

- `full_reconciliation.jsonl`: toàn bộ 10.731 entity xã/huyện cũ.
- `reconciliation_615.jsonl` và CSV UTF-8-sig: mỗi ca có entity/key/mã lưu, raw candidates, cấp, dòng CSV, source hash, component differences, rule, status, reason và evidence cần thêm.
- `unresolved_review_queue.jsonl`: 615 ca chưa đủ bằng chứng.
- `summary.json`: số lượng tái tạo đúng, output hashes và `newly_verified_official_codes=0`.

Candidate có thể được tìm bằng mã ứng viên đang lưu hoặc tên lá exact để chẩn đoán. Accent folding chỉ phân loại chênh lệch, **không dùng để promote identity/code**. Không sửa lớp alias, raw hoặc mã trong package frozen.

## 3. Gazetteer outcome

[Gap report](../../../data/interim/modeling/sprint03/task_01_06_20261003_v1/gazetteer_gap_audit/coverage_gap_report.json) giữ:

- 14.149 entity, 10.597 cạnh nguyên tử, 5 chuyển đổi phi nguyên tử, 187 alias audit.
- Quan hệ: B/N-1=9.432, C/1-1=132, M/M-N=1.030, A/1-N=3; mọi đích được giữ.
- Mã cũ vẫn candidate/unverified; mã xã mới vẫn theo bảng ánh xạ đã có, không nâng quyền nguồn.
- `new_package_released=false`; không tạo s3_v3.
- Manifest s3_v2: `fb350c06b3a3d1dca9ceb6de65695fa533ac20ea3bda3f1abd8465951f8646d9`.

Verifier phát hành decision derivative ở interim. Lookup dùng interval nửa mở qua adapter; không sửa cách ghi ngày trong bytes v2.

## 4. Tái lập và điều kiện mở tiếp

```bash
cd /mnt/d/DACN
source data/interim/modeling/sprint03/task_01_06_20261003_v1/runtime_env.sh
# Dùng output mới; không ghi đè thư mục đã có.
"$TASK_PYTHON" -m scripts.36_review_sources_and_frozen_baselines source \
  --output-dir data/interim/modeling/sprint03/reconciliation_next_version
```

Để mở xác minh mã: cần export chính thức lưu truy vấn/ngày tham chiếu và full parent keys, hoặc catalogue + sửa đổi có hiệu lực đến 30/06/2025; cần URL/document ID/hash/locator từng dòng, điều kiện dùng nguồn và transcription được duyệt. Không yêu cầu chủ dự án rà lại 615 dòng để tự suy đoán mã. Agent có thể tiếp tục extraction/verifier khi nguồn đủ.

Các test lookup/verifier kiểm ngày biên, zero đầu, khóa cha, tên trùng, nhiều đích, 5 cạnh phi nguyên tử và source manifest; bằng chứng ở [báo cáo nghiệm thu](27_tasks_01_06_completion_20261003.md).
