# U7 bổ sung — các bảng mã đã có trong repository

Ngày rà: 02/10/2026. Đây là bổ sung cho báo cáo19/20; không sửa corpus, source file, gazetteer s3_v2 hoặc run đã khóa.

## File đã tìm thấy

| File | Số dòng | Nội dung |
| --- | ---: | --- |
| `data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv` |10.602|Khóa tỉnh–huyện–xã cũ → tỉnh–xã mới, mã xã mới, loại/quan hệ; không có cột mã xã cũ|
| `data/reference/administrative_units/data_satnhap.csv` |3.321|Tỉnh mới, xã mới và danh sách tên xã cũ; không có mã hành chính hoặc đủ khóa cha cũ|
| `third_party/vietnamadminunits/data/raw/danhmuchanhchinh.gso.gov.vn_ward_2025-07-18.csv` |10.035|Mã/tên/cấp xã, mã/tên huyện và tỉnh; mã được đọc string, giữ zero đầu|
| `third_party/vietnamadminunits/data/raw/danhmuchanhchinh.gso.gov.vn_district_2025-07-18.csv` |696|Mã/tên/cấp huyện và mã/tên tỉnh|

Ghi chú thu thập `third_party/vietnamadminunits/scripts/collecting_data/s1_downloading_danhmuchanhchinh.gso.gov.vn.txt` ghi URL `https://danhmuchanhchinh.gso.gov.vn` và thao tác Download ward/district. Đây là dấu vết nguồn trong repo, cần được rà cùng bản raw. Báo cáo20 và source register của lượt U1–U7 chưa đưa hai raw CSV này vào danh mục nguồn; yêu cầu chủ dự án cung cấp bảng mới trước khi kiểm tra chúng là chưa đầy đủ.

## Đối chiếu thực tế với s3_v2

Đã đối chiếu exact theo tên đầy đủ tỉnh–huyện–xã, chỉ NFC/gộp whitespace, không fuzzy/alias mới và không thay mã:

- Xã cũ: **9.451/10.035** khớp cả khóa và mã ứng viên; **584** chưa tìm được khóa exact.
- Huyện cũ: **665** khớp khóa/mã; **5** tìm được khóa trong raw nhưng mã đang thiếu ở gazetteer; **26** chưa tìm được khóa exact.
- Chưa nâng mã nào thành official verified. Các ca không khớp cần kiểm tên/cấp/cha và alias đã audit; **không mặc định là mã sai**.

Kết quả, hashes từng file, schema và danh sách chưa khớp: `data/interim/modeling/sprint03/existing_code_sources_review_20261002_v1/existing_sources_review.json`. Script đi kèm chỉ đọc và ghi báo cáo interim, không sửa `third_party/` hoặc package frozen.

## Phần còn cần xác minh

Ngày `2025-07-18` trong tên file không tự chứng minh thời kỳ dữ liệu đã chọn khi xuất. Ghi chú tải hiện chỉ có URL trang chủ, chưa ghi query/kỳ tham chiếu, trang xuất hoặc metadata snapshot cụ thể. Vì vậy cần kiểm provenance và thời kỳ của **bảng đã có**, rồi giải quyết các khóa chưa match trước khi nâng mức xác minh. Quyền dùng bảng và quyền dùng code thư viện được ghi riêng.

**Bước tiếp theo là tái sử dụng và audit hai bảng raw hiện có.** Không cần chủ dự án tự tạo bảng mã mới hoặc tự kiểm10.035 dòng. Chỉ cần bổ sung tài liệu nguồn nếu kiểm tra các file hiện có vẫn không đủ bằng chứng. Trạng thái s3_v2 tiếp tục `PARTIAL_OLD_CODES_UNVERIFIED` trong thời gian đó; không yêu cầu gán lại68/232 hoặc đọc test100.
