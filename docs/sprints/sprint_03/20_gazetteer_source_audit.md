# Audit nguồn gazetteer — U7, 02/10/2026

Kết quả: **PARTIAL_OLD_CODES_UNVERIFIED**. Toolkit đã hiện thực; **0 mã được nâng trạng thái từ bằng chứng mới**. Giữ s3_v1/s3_v2 và HEUR-JW frozen; không tạo package v3 chỉ để đổi tên.

## 1. Nguồn sơ cấp đã tìm

| Nguồn | Bằng chứng đã đọc | Phần chưa đủ |
| --- | --- | --- |
| [124/2004/QĐ-TTg, CSDL Bộ Nội vụ](https://vbpl.vn/bonoivu/Pages/vbpq-toanvan.aspx?ItemID=17617) | Ban hành08/07/2004; metadata hiệu lực27/08/2004–01/07/2025; Điều1 nêu bảng đến30/06/2004 | Không phải snapshot30/06/2025; phải có chuỗi thay đổi/cấp mã tiếp theo để xác nhận từng khóa |
| [19/2025/QĐ-TTg, PDF ký số](https://datafiles.chinhphu.vn/cpp/files/vbpq/2025/7/19ttg.signed.pdf) và [Công báo metadata](https://congbao.chinhphu.vn/van-ban-dang-cong-bao/thu-tuong-chinh-phu-c2/trang-37.htm) | Văn bản danh mục mã mới; ban hành30/06/2025, hiệu lực01/07/2025; PDF143 trang đã truy cập qua web | Chưa trích bảng, duyệt transcription và đối chiếu từng mã; bảng mã không tự chứng minh từng cạnh sáp nhập |
| [Danh mục hành chính NSO](https://danhmuchanhchinh.nso.gov.vn/DiaBan.aspx) | Xác định được URL cơ quan thống kê | Web tool chưa truy cập được nội dung; query/snapshot thời kỳ chưa xác minh |
| CSV ánh xạ trong repo | SHA-256 `22bd8278…`; mã mới khớp file nội bộ | Thiếu URL ấn phẩm gốc, provenance/cơ quan và điều khoản tái sử dụng của CSV dẫn xuất |

Access date02/10/2026. Không có file nguồn mới được tải vào project; PDF/HTML đọc qua web **không được ghi thành SHA file local**. Source register ghi hash=null cho nguồn chỉ truy cập web, quyền dùng UNKNOWN. Mã source di sản `official_mapping_2025` chỉ là ID nội bộ. Giấy phép code/package/model và giấy phép bảng dữ liệu tách riêng.

## 2. Coverage package frozen

| Hệ / cấp | Code status trong s3_v2 | Số lượng |
| --- | --- | ---: |
| cũ / tỉnh | candidate_third_party_unverified | 63 |
| cũ / huyện | candidate_third_party_unverified | 691 |
| cũ / huyện | unverified_missing | 5 |
| cũ / xã | candidate_third_party_unverified | **10.035** |
| mới / tỉnh | unverified_missing | 34 |
| mới / xã | verified_source (khớp CSV repo) | 3.321 |

Tổng14.149 entity;10.597 cạnh nguyên tử;187 alias audit;5 chuyển đổi huyện→đặc khu. Các quan hệ giữ B/N-1:9.432, C/1-1:132, M/M-N:1.030, A/1-N:3. `verified_source` của mã mới chưa đồng nghĩa verified bằng văn bản pháp lý bên ngoài. Internal entity_id không phải mã nhà nước.

## 3. Công cụ đã hiện thực

`src/data/administrative_code_verifier.py` + script35:

- Gate hash mọi output s3_v2; không sửa package/reference/third_party.
- Khóa exact `(system, level, province, district, ward)` có cha đầy đủ, giữ loại đơn vị/dấu; chỉ NFC và gộp whitespace. Không fuzzy promotion, không alias/cạnh tự sinh.
- Đọc code dưới dạng string, giữ zero đầu; không tự padding. Conflict/missing/reference ngoài thời kỳ giữ unverified.
- Lookup `(name,level,date,parent_context)` trả toàn bộ candidate, code status, nguồn/hash và lý do từ chối. Đồng tên không chọn dòng đầu.
- Adapter interval `[from,to)`; s3_v2 `valid_to` là ngày cuối inclusive được cộng1 ngày **trong bộ nhớ**. Old start unknown vẫn báo START_UNKNOWN; không bịa ngày khởi đầu.
- Lookup targets giữ mọi đích và cả5 cạnh phi nguyên tử; không ép A/M thành một đích.
- Verifier reference yêu cầu manifest nguồn sơ cấp, URL chính thức, transcription APPROVED, snapshot phù hợp hoặc change history đã xác minh đến ngày tra. Không dùng bảng2004 như bảng2025.
- Output hiện là audit/decision derivative, **không phát hành package mới**. Nâng package cần bằng chứng từng mã, quyền dùng và release review đủ.

## 4. Reference phải cung cấp khi mở cổng nguồn

CSV UTF-8-sig với mã string:

```text
province,district,ward,level,system,code,valid_from,valid_to,source_id,source_locator
```

`valid_to` exclusive; ward cũ bắt buộc tỉnh–huyện–xã, ward mới tỉnh–xã; cấp tỉnh/huyện không nhét tên xã vào khóa. `source_locator` trang/dòng cụ thể. Không đổi tên/cấp theo fuzzy để làm match.

Manifest JSON gồm: `schema_version=s3-official-code-reference-v1`, source_id, URL tài liệu cụ thể, issuer, document_id, accessed_at, reference_sha256 của CSV thực, authority_status=OFFICIAL_PRIMARY_SOURCE, extraction_review_status=APPROVED, license_status (CLEARED/UNKNOWN), effective_from/to, table_as_of, change_history_verified_through. Chỉ ghi ngày/hash có bằng chứng. Một bảng thiếu nguồn/đối chiếu không được đặt APPROVED chỉ để vượt gate.

```bash
python -m scripts.35_verify_gazetteer_sources audit \
  --output-dir data/interim/modeling/sprint03/gazetteer_audit_new
python -m scripts.35_verify_gazetteer_sources lookup \
  --name 'Phường Bến Nghé' --level ward --date 2025-06-30 \
  --province 'Thành phố Hồ Chí Minh' --district 'Quận 1'
python -m scripts.35_verify_gazetteer_sources audit \
  --reference data/reference/new_reviewed_reference.csv \
  --reference-manifest data/reference/new_reviewed_reference_manifest.json \
  --date 2025-06-30 --output-dir data/interim/modeling/sprint03/gazetteer_reference_audit_new
```

Dòng cuối là hướng dẫn khi reference mới đã có quyền và được duyệt; hiện chưa chạy. Bảng nguồn mới chỉ đọc, không ghi đè CSV hiện hành.
