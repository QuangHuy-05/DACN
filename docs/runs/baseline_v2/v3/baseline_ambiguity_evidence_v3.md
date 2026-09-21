# Bằng chứng baseline và ca nhập nhằng có truy vết (v3)

- **Phiên bản tài liệu:** v3 draft (sinh tự động)
- **Run nguồn:** `baseline_v2`
- **Manifest SHA-256:** `f870c0bc4d0317c45008a792a6be0f220e23818f2e0e738f972d1b25ffc9c7bf`
- **Dòng benchmark:** 5500; **lượt dự đoán:** 13000.
- **Trạng thái:** draft có truy vết artifact; không thay thế báo cáo baseline v1 frozen.

## 1. Phương pháp và giới hạn diễn giải

Tài liệu này đọc trực tiếp prediction CSV, raw JSONL và bảng CSV ở `comparative_analysis_tables/` của cùng run. Case study được chọn bằng quy tắc xác định: sắp xếp theo `(dataset, tool, LoaiLoi, ID)`, sau đó lấy một dòng đầu tiên cho mỗi nhóm `(dataset, tool, LoaiLoi)`. Mỗi case được kiểm tra lại với khóa `(ID, CongCu)` ở cả prediction và raw log trước khi xuất.

`exact_match_rate`, `micro_f1_scored_fields` và `macro_mean_field_f1` là ba chỉ số khác nhau. Định nghĩa: Tỷ lệ bản ghi có mọi trường được chấm đều khớp sau chuẩn hóa. F1 gộp mọi quyết định trên các trường được chấm; mismatch tính một FP và một FN. Trung bình không trọng số của F1 từng trường được chấm.

Data 02 là nhiễu tổng hợp có kiểm soát, được hiệu chuẩn từ profile VQA; nó không thay thế đánh giá trên hóa đơn thật. Data 07 chỉ đo `old_to_new` bằng VietnamAdminUnits và chỉ chấm `PhuongXa, TinhThanh`; không có phép đo new-to-old hoặc Libpostal conversion.

## 2. Bảng định lượng nguồn

Nguồn: `comparative_analysis_tables/dataset_exact_metrics.csv` của run `baseline_v2`.

| dataset_condition | tool | scored_fields | n | exact_correct | exact_match_rate | micro_f1_scored_fields | macro_mean_field_f1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Data 01\|all | libpostal | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 1000 | 2 | 0.002 | 0.573781 | 0.447774 |
| Data 01\|all | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 1000 | 973 | 0.973 | 0.988109 | 0.790477 |
| Data 02\|clean | libpostal | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 1000 | 1 | 0.001 | 0.509417 | 0.41643 |
| Data 02\|clean | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 1000 | 862 | 0.862 | 0.947452 | 0.949086 |
| Data 02\|noisy | libpostal | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 1000 | 1 | 0.001 | 0.39473 | 0.332415 |
| Data 02\|noisy | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 1000 | 217 | 0.217 | 0.731743 | 0.747826 |
| Data 03\|all | libpostal | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 1500 | 1 | 0.000667 | 0.442915 | 0.37625 |
| Data 03\|all | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 1500 | 1094 | 0.729333 | 0.904742 | 0.904169 |
| Data 04\|surface_parse | libpostal | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 800 | 120 | 0.15 | 0.456376 | 0.395081 |
| Data 04\|surface_parse | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 800 | 208 | 0.26 | 0.629273 | 0.574126 |
| Data 06\|libpostal | libpostal | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 600 | 2 | 0.003333 | 0.550543 | 0.504441 |
| Data 06\|vn_from_2025 | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 600 | 0 | 0.0 | 0.727136 | 0.655965 |
| Data 06\|vn_legacy | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 600 | 415 | 0.691667 | 0.867304 | 0.864372 |
| Data 07\|old_to_new | vietnamadminunits | PhuongXa,TinhThanh | 600 | 582 | 0.97 | 0.985774 | 0.985765 |

## 3. Hợp đồng Data 06 và phạm vi Data 07

Nguồn: `comparative_analysis_tables/data06_contract.csv` và `data07_scope.csv`.

### Data 06

| KieuLai | n | PhuongXa_he | QuanHuyen_he | TinhThanh_he | all_surface_district_present |
| --- | --- | --- | --- | --- | --- |
| C1 | 420 | moi | cu | cu | True |
| C2 | 120 | moi | cu | moi | True |
| C3 | 60 | cu | cu | moi | True |

Mọi kiểu Data 06 hiện có đều giữ `QuanHuyen` trên chuỗi bề mặt. C1 là phường/xã mới + quận/huyện cũ + tỉnh/thành cũ; C2 là phường/xã mới + quận/huyện cũ + tỉnh/thành mới; C3 là phường/xã cũ + quận/huyện cũ + tỉnh/thành mới.

### Data 07

| QuanHe | n | direction_evaluated | scored_fields |
| --- | --- | --- | --- |
| M-N | 356 | old_to_new | PhuongXa,TinhThanh |
| N-1 | 244 | old_to_new | PhuongXa,TinhThanh |

## 4. Case study được sinh từ output

Nguồn: `comparative_analysis_tables/case_studies.csv`. Các dòng sau là projection của output, không phải ví dụ minh họa viết thủ công.

| ID | CongCu | Dataset | LoaiLoi | DungSai | DiaChiGoc | TruongDuDoan | TruongDung | RawStatus |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D01_0000 | libpostal | D01 | hallucination_over_imputation | PARTIAL | 394, Đường Lý Thường Kiệt, Phường Phù Khê, Tỉnh Bắc Ninh | {"SoNha": "394", "TenDuong": "đường lý thường kiệt", "PhuongXa": "", "QuanHuyen": "phường phù", "TinhThanh": "tỉnh bắc ninh"} | {"SoNha": "394", "TenDuong": "Đường Lý Thường Kiệt", "PhuongXa": "Phường Phù Khê", "QuanHuyen": "", "TinhThanh": "Tỉnh Bắc Ninh"} | success |
| D01_0002 | libpostal | D01 | missing_field | PARTIAL | 314, Nguyễn Văn Linh, Phường Tân Thuận, Thành phố Hồ Chí Minh | {"SoNha": "314", "TenDuong": "nguyễn văn linh phường tân thuận", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "thành phố hồ chí minh"} | {"SoNha": "314", "TenDuong": "Nguyễn Văn Linh", "PhuongXa": "Phường Tân Thuận", "QuanHuyen": "", "TinhThanh": "Thành phố Hồ Chí Minh"} | success |
| D01_0051 | vietnamadminunits | D01 | missing_field | PARTIAL | 32-A1, Phố Sơn Tây, Phường Ba Đình, Thành phố Hà Nội | {"SoNha": "32", "TenDuong": "- A1, Phố Sơn Tây", "PhuongXa": "Phường Ba Đình", "QuanHuyen": "", "TinhThanh": "Thành phố Hà Nội"} | {"SoNha": "32-A1", "TenDuong": "Phố Sơn Tây", "PhuongXa": "Phường Ba Đình", "QuanHuyen": "", "TinhThanh": "Thành phố Hà Nội"} | success |
| D02_N00006_noisy | libpostal | D02 | abbreviation_misunderstood | ERROR | Phố S0ng Tháp,P.Phu Khe,T.Bắc Ninh | {"SoNha": "", "TenDuong": "", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": ""} | {"SoNha": "8", "TenDuong": "Phố Song Tháp", "PhuongXa": "Phường Phù Khê", "QuanHuyen": "", "TinhThanh": "Tỉnh Bắc Ninh"} | success |
| D02_N00001_clean | libpostal | D02 | hallucination_over_imputation | PARTIAL | 213, Phố Lương Định Của, Phường Phương Liễu, Tỉnh Bắc Ninh | {"SoNha": "213", "TenDuong": "phố lương định của", "PhuongXa": "", "QuanHuyen": "phường phương", "TinhThanh": "tỉnh bắc ninh"} | {"SoNha": "213", "TenDuong": "Phố Lương Định Của", "PhuongXa": "Phường Phương Liễu", "QuanHuyen": "", "TinhThanh": "Tỉnh Bắc Ninh"} | success |
| D02_N00002_clean | libpostal | D02 | missing_field | PARTIAL | 37/11, Đường Đặng Thùy Trâm, Phường Bình Lợi Trung, Thành phố Hồ Chí Minh | {"SoNha": "37/11", "TenDuong": "đường đặng thùy trâm phường bình lợi trung", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "thành phố hồ chí minh"} | {"SoNha": "37/11", "TenDuong": "Đường Đặng Thùy Trâm", "PhuongXa": "Phường Bình Lợi Trung", "QuanHuyen": "", "TinhThanh": "Thành phố Hồ Chí Minh"} | success |
| D02_N00030_noisy | libpostal | D02 | parse_boundary_error | ERROR | Ngõ 71 Lê Hồng Ph0ng; Phường Ba Đình; Thanh pho Ha Noi | {"SoNha": "", "TenDuong": "ngõ 71 lê hồng phường ba đình", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "thanh pho ha noi"} | {"SoNha": "10", "TenDuong": "Ngõ 71 Lê Hồng Phong", "PhuongXa": "Phường Ba Đình", "QuanHuyen": "", "TinhThanh": "Thành phố Hà Nội"} | success |
| D02_N00532_noisy | vietnamadminunits | D02 | abbreviation_misunderstood | ERROR | 594 - Đường Nguyễn Tất Thành - P.18 - TP Hồ Chí M1nh | {"SoNha": "", "TenDuong": "", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": ""} | {"SoNha": "594", "TenDuong": "Đường Nguyễn Tất Thành", "PhuongXa": "phường 18", "QuanHuyen": "quận 4", "TinhThanh": "TP Hồ Chí Minh"} | success |
| D02_N00001_noisy | vietnamadminunits | D02 | missing_field | PARTIAL | 213; Phố Lương Định Của; P.Phương Liễu; Tinh Bac Ninh | {"SoNha": "", "TenDuong": "213; Phố Lương Định Của; P", "PhuongXa": "Phường Phương Liễu", "QuanHuyen": "", "TinhThanh": "Tỉnh Bắc Ninh"} | {"SoNha": "213", "TenDuong": "Phố Lương Định Của", "PhuongXa": "Phường Phương Liễu", "QuanHuyen": "", "TinhThanh": "Tỉnh Bắc Ninh"} | success |
| D02_N00136_clean | vietnamadminunits | D02 | parse_boundary_error | ERROR | 188, Hậu Giang, Phường 6, Quận 6, Phường 6 | {"SoNha": "", "TenDuong": "188", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "Tỉnh Hậu Giang"} | {"SoNha": "188", "TenDuong": "Hậu Giang", "PhuongXa": "Phường 6", "QuanHuyen": "Quận 6", "TinhThanh": "Phường 6"} | success |
| D03_0000 | libpostal | D03 | missing_field | ERROR | NT02-29, Ngọc Trai 2, Đa Tốn, Gia Lâm, Hà Nội | {"SoNha": "2", "TenDuong": "nt02-29 ngọc trai đa tốn gia lâm", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "hà nội"} | {"SoNha": "NT02-29", "TenDuong": "Ngọc Trai 2", "PhuongXa": "Đa Tốn", "QuanHuyen": "Gia Lâm", "TinhThanh": "Hà Nội"} | success |
| D03_0111 | libpostal | D03 | parse_boundary_error | ERROR | A1-Fl.5, Km 10, Đường Trần Phú, Mộ Lao, Hà Đông, Hà Nội | {"SoNha": "", "TenDuong": "a1-fl.5 km 10 đường trần phú", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "mộ hà nội"} | {"SoNha": "A1-Fl.5, Km 10", "TenDuong": "Đường Trần Phú", "PhuongXa": "Mộ Lao", "QuanHuyen": "Hà Đông", "TinhThanh": "Hà Nội"} | success |
| D03_1430 | vietnamadminunits | D03 | abbreviation_misunderstood | ERROR | 289, Tô Hiến Thành, 13, Quan 10, TP.Hồ Chí Minh | {"SoNha": "", "TenDuong": "289", "PhuongXa": "", "QuanHuyen": "Quận 10", "TinhThanh": "Thành phố Hồ Chí Minh"} | {"SoNha": "289", "TenDuong": "Tô Hiến Thành", "PhuongXa": "13", "QuanHuyen": "Quan 10", "TinhThanh": "TP.Hồ Chí Minh"} | success |
| D03_0000 | vietnamadminunits | D03 | missing_field | PARTIAL | NT02-29, Ngọc Trai 2, Đa Tốn, Gia Lâm, Hà Nội | {"SoNha": "", "TenDuong": "Nt02 - 29, Ngọc Trai 2", "PhuongXa": "Xã Đa Tốn", "QuanHuyen": "Huyện Gia Lâm", "TinhThanh": "Thành phố Hà Nội"} | {"SoNha": "NT02-29", "TenDuong": "Ngọc Trai 2", "PhuongXa": "Đa Tốn", "QuanHuyen": "Gia Lâm", "TinhThanh": "Hà Nội"} | success |
| D03_0052 | vietnamadminunits | D03 | parse_boundary_error | ERROR | 21, Đồng Nai, 15, 10, Ho Chi Minh City | {"SoNha": "", "TenDuong": "21", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "Thành phố Hồ Chí Minh"} | {"SoNha": "21", "TenDuong": "Đồng Nai", "PhuongXa": "15", "QuanHuyen": "10", "TinhThanh": "Ho Chi Minh City"} | success |
| D04_0025 | libpostal | D04 | abbreviation_misunderstood | ERROR | Đường Hoàng Diệu, Phường Ba Đình, TP.HN | {"SoNha": "", "TenDuong": "đường hoàng diệu phường ba đình tp.hn", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": ""} | {"SoNha": "", "TenDuong": "Đường Hoàng Diệu", "PhuongXa": "Phường Ba Đình", "QuanHuyen": "", "TinhThanh": "TP.HN"} | success |
| D04_0005 | libpostal | D04 | hallucination_over_imputation | ERROR | Đường Hoàng Quốc Việt, Phường Cổ Nhuế 1, Q. Bắc Từ Liêm, Hà Nội | {"SoNha": "1 q.", "TenDuong": "đường hoàng quốc việt phường cổ nhuế bắc từ liêm", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "hà nội"} | {"SoNha": "", "TenDuong": "Đường Hoàng Quốc Việt", "PhuongXa": "Phường Cổ Nhuế 1", "QuanHuyen": "Q. Bắc Từ Liêm", "TinhThanh": "Hà Nội"} | success |
| D04_0000 | libpostal | D04 | missing_field | ERROR | 9, Ngách 1/88 Phạm Tuấn Tài, Phường Dịch Vọng Hậu, Hà Nội | {"SoNha": "9", "TenDuong": "ngách 1/88", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "phạm hà nội"} | {"SoNha": "9", "TenDuong": "Ngách 1/88 Phạm Tuấn Tài", "PhuongXa": "Phường Dịch Vọng Hậu", "QuanHuyen": "", "TinhThanh": "Hà Nội"} | success |
| D04_0023 | libpostal | D04 | parse_boundary_error | ERROR | Phố Yên Mẫn, Phường Kinh Bắc, T Bắc Ninh | {"SoNha": "", "TenDuong": "", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": ""} | {"SoNha": "", "TenDuong": "Phố Yên Mẫn", "PhuongXa": "Phường Kinh Bắc", "QuanHuyen": "", "TinhThanh": "T Bắc Ninh"} | success |
| D04_0003 | vietnamadminunits | D04 | abbreviation_misunderstood | ERROR | 89, Hoa Lan, P.2, TP. HCM | {"SoNha": "", "TenDuong": "89", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "Thành phố Hồ Chí Minh"} | {"SoNha": "89", "TenDuong": "Hoa Lan", "PhuongXa": "P.2", "QuanHuyen": "", "TinhThanh": "TP. HCM"} | success |
| D04_0007 | vietnamadminunits | D04 | hallucination_over_imputation | PARTIAL | Phố Ngọc Hà, Quận Ba Đình, Hà Nội | {"SoNha": "", "TenDuong": "Phố", "PhuongXa": "Phường Ngọc Hà", "QuanHuyen": "Quận Ba Đình", "TinhThanh": "Thành phố Hà Nội"} | {"SoNha": "", "TenDuong": "Phố Ngọc Hà", "PhuongXa": "", "QuanHuyen": "Quận Ba Đình", "TinhThanh": "Hà Nội"} | success |
| D04_0000 | vietnamadminunits | D04 | missing_field | ERROR | 9, Ngách 1/88 Phạm Tuấn Tài, Phường Dịch Vọng Hậu, Hà Nội | {"SoNha": "", "TenDuong": "9", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "Thành phố Hà Nội"} | {"SoNha": "9", "TenDuong": "Ngách 1/88 Phạm Tuấn Tài", "PhuongXa": "Phường Dịch Vọng Hậu", "QuanHuyen": "", "TinhThanh": "Hà Nội"} | success |
| D04_0006 | vietnamadminunits | D04 | parse_boundary_error | ERROR | Đường Mỹ Phú 1B, TPHCM | {"SoNha": "", "TenDuong": "", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "Thành phố Hồ Chí Minh"} | {"SoNha": "", "TenDuong": "Đường Mỹ Phú 1B", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "TPHCM"} | success |
| D06_0001 | libpostal | D06 | missing_field | PARTIAL | 55, Đường Trần Hưng Đạo, Phường Quế Võ, Thị xã Quế Võ, Bắc Ninh | {"SoNha": "55", "TenDuong": "đường trần hưng đạo", "PhuongXa": "", "QuanHuyen": "quế võ thị xã quế võ bắc ninh", "TinhThanh": "phường"} | {"SoNha": "55", "TenDuong": "Đường Trần Hưng Đạo", "PhuongXa": "Phường Quế Võ", "QuanHuyen": "Thị xã Quế Võ", "TinhThanh": "Bắc Ninh"} | success |
| D06_0000 | libpostal | D06 | parse_boundary_error | ERROR | 6, Ngõ 42 Phố Trần Bình Trọng, Phường Phương Liễu, Thị xã Quế Võ, Bắc Ninh | {"SoNha": "6 ngõ 42", "TenDuong": "phố trần bình trọng", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "phường"} | {"SoNha": "6", "TenDuong": "Ngõ 42 Phố Trần Bình Trọng", "PhuongXa": "Phường Phương Liễu", "QuanHuyen": "Thị xã Quế Võ", "TinhThanh": "Bắc Ninh"} | success |
| D06_0000_m25 | vietnamadminunits | D06 | missing_field | PARTIAL | 6, Ngõ 42 Phố Trần Bình Trọng, Phường Phương Liễu, Thị xã Quế Võ, Bắc Ninh | {"SoNha": "6", "TenDuong": "Ngõ 42 Phố Trần Bình Trọng, Phường Phương Liễu", "PhuongXa": "Phường Quế Võ", "QuanHuyen": "", "TinhThanh": "Tỉnh Bắc Ninh"} | {"SoNha": "6", "TenDuong": "Ngõ 42 Phố Trần Bình Trọng", "PhuongXa": "Phường Phương Liễu", "QuanHuyen": "Thị xã Quế Võ", "TinhThanh": "Bắc Ninh"} | success |
| D07_0281_N-1 | vietnamadminunits | D07 | missing_field | ERROR | 14E, Đường Quốc Hương, Thảo Điền, 2, Ho Chi Minh CIty | {"SoNha": "", "TenDuong": "", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "Thành phố Hồ Chí Minh"} | {"SoNha": "", "TenDuong": "", "PhuongXa": "Phường An Khánh", "QuanHuyen": "", "TinhThanh": "Thành phố Hồ Chí Minh"} | success |
| D07_0000_M-N | vietnamadminunits | D07 | parse_boundary_error | ERROR | 11, Phố Khúc Hạo, Phường Điện Biên, Quận Ba Đình, Hà Nội | {"SoNha": "", "TenDuong": "", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": ""} | {"SoNha": "", "TenDuong": "", "PhuongXa": "Phường Ba Đình", "QuanHuyen": "", "TinhThanh": "Thành phố Hà Nội"} | exception |
| D07_0018_M-N | vietnamadminunits | D07 | wrong_target | ERROR | 36, Phố Trần Phú, Phường Điện Biên, Quận Ba Đình, Hà Nội | {"SoNha": "36", "TenDuong": "Phố Trần Phú", "PhuongXa": "Phường Hoàn Kiếm", "QuanHuyen": "", "TinhThanh": "Thành phố Hà Nội"} | {"SoNha": "", "TenDuong": "", "PhuongXa": "Phường Ba Đình", "QuanHuyen": "", "TinhThanh": "Thành phố Hà Nội"} | success |

## 5. Diễn giải có điều kiện

Các output chỉ chứng minh hành vi quan sát được của adapter và tool ở run này. Khi raw log không có trace nhánh converter, không được kết luận một lỗi cụ thể do fallback/geocoder. Run mới ghi `conversion_trace` để phân biệt ánh xạ từ điển, geocoder và fallback. Bất kỳ kết luận nhân quả nào phải trỏ tới ID cùng trace hoặc được ghi là giả thuyết kỹ thuật.
