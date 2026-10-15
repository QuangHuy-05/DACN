# Bằng chứng baseline và chẩn đoán có truy vết (v4)

- **Phiên bản tài liệu:** v4 fuzzy/uncertainty draft (sinh tự động)
- **Run nguồn:** `baseline_v3_fuzzy`
- **Manifest SHA-256:** `14da842d270d2b0e2a31efd954c07d3a0f948cc7b3d7c8240687ae7a19a46fcb`
- **Dòng benchmark:** 5500; **lượt dự đoán:** 13000.
- **Trạng thái:** draft có truy vết artifact; không thay thế báo cáo baseline v1 frozen.

## 1. Phương pháp và giới hạn diễn giải

Tài liệu này đọc trực tiếp prediction CSV, raw JSONL và bảng CSV ở `comparative_analysis_tables/` của cùng run. Case study được chọn bằng quy tắc xác định: sắp xếp theo `(dataset, tool, LoaiLoi, ID)`, sau đó lấy một dòng đầu tiên cho mỗi nhóm `(dataset, tool, LoaiLoi)`. Mỗi case được kiểm tra lại với khóa `(ID, CongCu)` ở cả prediction và raw log trước khi xuất.

`exact_match_rate`, `micro_f1_scored_fields` và `macro_mean_field_f1` là ba chỉ số khác nhau. Định nghĩa: Tỷ lệ bản ghi có mọi trường được chấm đều khớp sau chuẩn hóa. F1 gộp mọi quyết định trên các trường được chấm; mismatch tính một FP và một FN. Trung bình không trọng số của F1 từng trường được chấm.

Metric fuzzy dùng `normalized_levenshtein` sau chuẩn hóa theo protocol: NFC Unicode, casefold, collapse whitespace, strip surrounding whitespace and trailing comma separators, retain Vietnamese diacritics and administrative unit-type prefixes, and compare only corresponding fields. Ignore pairs where both values are empty; score a one-sided empty pair as 0. Report the number of non-empty field pairs used as the denominator. Định nghĩa: Trung bình normalized Levenshtein similarity trên các cặp giá trị trường có ít nhất một vế không rỗng; rỗng-rỗng bị loại khỏi mẫu số. Trung bình không trọng số của micro_mean_fuzzy_similarity theo từng trường có ít nhất một cặp giá trị không rỗng. Fuzzy similarity đo độ gần chuỗi, không thay thế xác minh đúng thực thể hành chính.

Data 02 là nhiễu tổng hợp có kiểm soát, được hiệu chuẩn từ profile VQA; nó không thay thế đánh giá trên hóa đơn thật. Data 07 chỉ đo `old_to_new` bằng VietnamAdminUnits và chỉ chấm `PhuongXa, TinhThanh`; không có phép đo new-to-old hoặc Libpostal conversion.

## 2. Bảng định lượng nguồn

Nguồn: `comparative_analysis_tables/dataset_metrics.csv` của run `baseline_v3_fuzzy`. Bảng `dataset_field_metrics.csv` có 152 hàng theo điều kiện/trường, gồm exact numerator/denominator và fuzzy similarity sum/denominator.

| dataset_condition | tool | scored_fields | n | exact_correct | exact_match_rate | micro_mean_fuzzy_similarity | fuzzy_scored_field_values | macro_mean_field_fuzzy_similarity | micro_f1_scored_fields | macro_mean_field_f1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Data 01\|all | libpostal | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 1000 | 2 | 0.002 | 0.560473 | 4775 | 0.535252 | 0.573781 | 0.447774 |
| Data 01\|all | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 1000 | 973 | 0.973 | 0.992776 | 4000 | 0.992776 | 0.988109 | 0.790477 |
| Data 02\|clean | libpostal | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 1000 | 1 | 0.001 | 0.517121 | 4885 | 0.506481 | 0.501684 | 0.409995 |
| Data 02\|clean | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 1000 | 517 | 0.517 | 0.845009 | 4500 | 0.836402 | 0.731845 | 0.702981 |
| Data 02\|noisy | libpostal | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 1000 | 0 | 0.0 | 0.45329 | 4766 | 0.43614 | 0.372255 | 0.310184 |
| Data 02\|noisy | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 1000 | 123 | 0.123 | 0.681414 | 4500 | 0.68421 | 0.51169 | 0.508242 |
| Data 03\|all | libpostal | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 1500 | 1 | 0.000667 | 0.468431 | 7500 | 0.468431 | 0.425749 | 0.361786 |
| Data 03\|all | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 1500 | 87 | 0.058 | 0.724077 | 7500 | 0.724077 | 0.513598 | 0.519764 |
| Data 04\|surface_parse | libpostal | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 800 | 114 | 0.1425 | 0.521352 | 2961 | 0.472749 | 0.448648 | 0.384985 |
| Data 04\|surface_parse | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 800 | 39 | 0.04875 | 0.480963 | 2742 | 0.457276 | 0.32958 | 0.275428 |
| Data 06\|libpostal | libpostal | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 600 | 2 | 0.003333 | 0.584809 | 3000 | 0.584809 | 0.531125 | 0.485005 |
| Data 06\|vn_from_2025 | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 600 | 0 | 0.0 | 0.654718 | 3000 | 0.654718 | 0.604441 | 0.547298 |
| Data 06\|vn_legacy | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 600 | 157 | 0.261667 | 0.775672 | 3000 | 0.775672 | 0.751238 | 0.754926 |
| Data 07\|old_to_new | vietnamadminunits | PhuongXa,TinhThanh | 600 | 586 | 0.976667 | 0.99341 | 1200 | 0.99341 | 0.989158 | 0.989149 |
| Data 04\|KieuThieu=drop_district | libpostal | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 99 | 2 | 0.020202 | 0.557536 | 406 | 0.457292 | 0.472103 | 0.345036 |
| Data 04\|KieuThieu=drop_district | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 99 | 0 | 0.0 | 0.119888 | 405 | 0.098091 | 0.026316 | 0.020005 |
| Data 04\|KieuThieu=drop_housenumber | libpostal | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 348 | 0 | 0.0 | 0.362737 | 1358 | 0.287173 | 0.268744 | 0.178269 |
| Data 04\|KieuThieu=drop_housenumber | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 348 | 39 | 0.112069 | 0.760823 | 1191 | 0.604365 | 0.5 | 0.376274 |
| Data 04\|KieuThieu=drop_housenumber_ward | libpostal | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 112 | 31 | 0.276786 | 0.587585 | 315 | 0.338589 | 0.498155 | 0.261369 |
| Data 04\|KieuThieu=drop_housenumber_ward | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 112 | 0 | 0.0 | 0.370018 | 301 | 0.333324 | 0.220833 | 0.121429 |
| Data 04\|KieuThieu=drop_ward | libpostal | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 241 | 81 | 0.3361 | 0.72526 | 882 | 0.541547 | 0.649815 | 0.461916 |
| Data 04\|KieuThieu=drop_ward | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 241 | 0 | 0.0 | 0.299087 | 845 | 0.304035 | 0.212736 | 0.184769 |
| Data 06\|KieuLai=C1\|mode=single_parse | libpostal | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 420 | 0 | 0.0 | 0.559858 | 2100 | 0.559858 | 0.513595 | 0.470425 |
| Data 06\|KieuLai=C1\|mode=FROM_2025 | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 420 | 0 | 0.0 | 0.675778 | 2100 | 0.675778 | 0.592416 | 0.533999 |
| Data 06\|KieuLai=C1\|mode=LEGACY | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 420 | 5 | 0.011905 | 0.713103 | 2100 | 0.713103 | 0.668207 | 0.675201 |
| Data 06\|KieuLai=C2\|mode=single_parse | libpostal | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 120 | 0 | 0.0 | 0.647729 | 600 | 0.647729 | 0.574091 | 0.518554 |
| Data 06\|KieuLai=C2\|mode=FROM_2025 | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 120 | 0 | 0.0 | 0.738648 | 600 | 0.738648 | 0.760668 | 0.68493 |
| Data 06\|KieuLai=C2\|mode=LEGACY | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 120 | 96 | 0.8 | 0.893862 | 600 | 0.893862 | 0.917241 | 0.916364 |
| Data 06\|KieuLai=C3\|mode=single_parse | libpostal | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 60 | 2 | 0.033333 | 0.633624 | 300 | 0.633624 | 0.564007 | 0.522451 |
| Data 06\|KieuLai=C3\|mode=FROM_2025 | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 60 | 0 | 0.0 | 0.339436 | 300 | 0.339436 | 0.339785 | 0.292683 |
| Data 06\|KieuLai=C3\|mode=LEGACY | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 60 | 56 | 0.933333 | 0.977272 | 300 | 0.977272 | 0.9699 | 0.969888 |

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

## 4. Chẩn đoán uncertainty theo tình huống cấu trúc và trace chuyển đổi không gian

Data 04 (`KieuThieu`) và Data 06 (`KieuLai`/C1-C3) được dùng làm strata cấu trúc có sẵn. Đây là so sánh theo nhóm benchmark, không phải xác suất bất định đã hiệu chuẩn.

### Cấu trúc

Nguồn: `comparative_analysis_tables/structural_scenarios.csv`.

| diagnostic_axis | dataset_condition | tool | scored_fields | n | exact_correct | exact_match_rate | micro_mean_fuzzy_similarity | fuzzy_scored_field_values | macro_mean_field_fuzzy_similarity | micro_f1_scored_fields | macro_mean_field_f1 | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| structural_scenario | Data 04\|KieuThieu=drop_district | libpostal | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 99 | 2 | 0.020202 | 0.557536 | 406 | 0.457292 | 0.472103 | 0.345036 | Existing benchmark stratum; not a calibrated uncertainty estimate. |
| structural_scenario | Data 04\|KieuThieu=drop_district | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 99 | 0 | 0.0 | 0.119888 | 405 | 0.098091 | 0.026316 | 0.020005 | Existing benchmark stratum; not a calibrated uncertainty estimate. |
| structural_scenario | Data 04\|KieuThieu=drop_housenumber | libpostal | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 348 | 0 | 0.0 | 0.362737 | 1358 | 0.287173 | 0.268744 | 0.178269 | Existing benchmark stratum; not a calibrated uncertainty estimate. |
| structural_scenario | Data 04\|KieuThieu=drop_housenumber | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 348 | 39 | 0.112069 | 0.760823 | 1191 | 0.604365 | 0.5 | 0.376274 | Existing benchmark stratum; not a calibrated uncertainty estimate. |
| structural_scenario | Data 04\|KieuThieu=drop_housenumber_ward | libpostal | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 112 | 31 | 0.276786 | 0.587585 | 315 | 0.338589 | 0.498155 | 0.261369 | Existing benchmark stratum; not a calibrated uncertainty estimate. |
| structural_scenario | Data 04\|KieuThieu=drop_housenumber_ward | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 112 | 0 | 0.0 | 0.370018 | 301 | 0.333324 | 0.220833 | 0.121429 | Existing benchmark stratum; not a calibrated uncertainty estimate. |
| structural_scenario | Data 04\|KieuThieu=drop_ward | libpostal | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 241 | 81 | 0.3361 | 0.72526 | 882 | 0.541547 | 0.649815 | 0.461916 | Existing benchmark stratum; not a calibrated uncertainty estimate. |
| structural_scenario | Data 04\|KieuThieu=drop_ward | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 241 | 0 | 0.0 | 0.299087 | 845 | 0.304035 | 0.212736 | 0.184769 | Existing benchmark stratum; not a calibrated uncertainty estimate. |
| structural_scenario | Data 06\|KieuLai=C1\|mode=single_parse | libpostal | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 420 | 0 | 0.0 | 0.559858 | 2100 | 0.559858 | 0.513595 | 0.470425 | Existing benchmark stratum; not a calibrated uncertainty estimate. |
| structural_scenario | Data 06\|KieuLai=C1\|mode=FROM_2025 | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 420 | 0 | 0.0 | 0.675778 | 2100 | 0.675778 | 0.592416 | 0.533999 | Existing benchmark stratum; not a calibrated uncertainty estimate. |
| structural_scenario | Data 06\|KieuLai=C1\|mode=LEGACY | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 420 | 5 | 0.011905 | 0.713103 | 2100 | 0.713103 | 0.668207 | 0.675201 | Existing benchmark stratum; not a calibrated uncertainty estimate. |
| structural_scenario | Data 06\|KieuLai=C2\|mode=single_parse | libpostal | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 120 | 0 | 0.0 | 0.647729 | 600 | 0.647729 | 0.574091 | 0.518554 | Existing benchmark stratum; not a calibrated uncertainty estimate. |
| structural_scenario | Data 06\|KieuLai=C2\|mode=FROM_2025 | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 120 | 0 | 0.0 | 0.738648 | 600 | 0.738648 | 0.760668 | 0.68493 | Existing benchmark stratum; not a calibrated uncertainty estimate. |
| structural_scenario | Data 06\|KieuLai=C2\|mode=LEGACY | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 120 | 96 | 0.8 | 0.893862 | 600 | 0.893862 | 0.917241 | 0.916364 | Existing benchmark stratum; not a calibrated uncertainty estimate. |
| structural_scenario | Data 06\|KieuLai=C3\|mode=single_parse | libpostal | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 60 | 2 | 0.033333 | 0.633624 | 300 | 0.633624 | 0.564007 | 0.522451 | Existing benchmark stratum; not a calibrated uncertainty estimate. |
| structural_scenario | Data 06\|KieuLai=C3\|mode=FROM_2025 | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 60 | 0 | 0.0 | 0.339436 | 300 | 0.339436 | 0.339785 | 0.292683 | Existing benchmark stratum; not a calibrated uncertainty estimate. |
| structural_scenario | Data 06\|KieuLai=C3\|mode=LEGACY | vietnamadminunits | SoNha,TenDuong,PhuongXa,QuanHuyen,TinhThanh | 60 | 56 | 0.933333 | 0.977272 | 300 | 0.977272 | 0.9699 | 0.969888 | Existing benchmark stratum; not a calibrated uncertainty estimate. |

### Không gian / trace converter

Nguồn: `comparative_analysis_tables/spatial_trace_summary.csv`; từng dòng có trace nằm trong `spatial_trace_cases.csv`.

| diagnostic_axis | CongCu | QuanHe | candidate_count | selection_path | geocoder_status | fallback_used | n | exact_target_correct | exact_target_match_rate | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| spatial_converter_trace | vietnamadminunits | M-N | 2 | divided_geospatial_selection | resolved | False | 55 | 49 | 0.890909 | Observed converter trace stratum; not calibrated model uncertainty or geometric boundary ambiguity. |
| spatial_converter_trace | vietnamadminunits | M-N | 3 | divided_geospatial_selection | resolved | False | 2 | 1 | 0.5 | Observed converter trace stratum; not calibrated model uncertainty or geometric boundary ambiguity. |
| spatial_converter_trace | vietnamadminunits | M-N | 4 | divided_geospatial_selection | resolved | False | 299 | 294 | 0.983278 | Observed converter trace stratum; not calibrated model uncertainty or geometric boundary ambiguity. |
| spatial_converter_trace | vietnamadminunits | N-1 | 0 | unique_dictionary_or_unresolved | not_applicable | False | 244 | 242 | 0.991803 | Observed converter trace stratum; not calibrated model uncertainty or geometric boundary ambiguity. |

`candidate_count`, `selection_path`, `geocoder_status` và `fallback_used` là dấu vết converter. Chúng không phải confidence, khoảng cách tới ranh giới hay nhãn nhập nhằng được kiểm chứng thủ công. Adapter không xuất xác suất; run này không báo calibration/ECE.

## 5. Case study được sinh từ output

Nguồn: `comparative_analysis_tables/case_studies.csv`. Các dòng sau là projection của output, không phải ví dụ minh họa viết thủ công.

| ID | CongCu | Dataset | LoaiLoi | DungSai | DiaChiGoc | TruongDuDoan | TruongDung | RawStatus |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D01_0000 | libpostal | D01 | hallucination_over_imputation | PARTIAL | 394, Đường Lý Thường Kiệt, Phường Phù Khê, Tỉnh Bắc Ninh | {"SoNha": "394", "TenDuong": "đường lý thường kiệt", "PhuongXa": "", "QuanHuyen": "phường phù", "TinhThanh": "tỉnh bắc ninh"} | {"SoNha": "394", "TenDuong": "Đường Lý Thường Kiệt", "PhuongXa": "Phường Phù Khê", "QuanHuyen": "", "TinhThanh": "Tỉnh Bắc Ninh"} | success |
| D01_0002 | libpostal | D01 | missing_field | PARTIAL | 314, Nguyễn Văn Linh, Phường Tân Thuận, Thành phố Hồ Chí Minh | {"SoNha": "314", "TenDuong": "nguyễn văn linh phường tân thuận", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "thành phố hồ chí minh"} | {"SoNha": "314", "TenDuong": "Nguyễn Văn Linh", "PhuongXa": "Phường Tân Thuận", "QuanHuyen": "", "TinhThanh": "Thành phố Hồ Chí Minh"} | success |
| D01_0051 | vietnamadminunits | D01 | missing_field | PARTIAL | 32-A1, Phố Sơn Tây, Phường Ba Đình, Thành phố Hà Nội | {"SoNha": "32", "TenDuong": "- A1, Phố Sơn Tây", "PhuongXa": "Phường Ba Đình", "QuanHuyen": "", "TinhThanh": "Thành phố Hà Nội"} | {"SoNha": "32-A1", "TenDuong": "Phố Sơn Tây", "PhuongXa": "Phường Ba Đình", "QuanHuyen": "", "TinhThanh": "Thành phố Hà Nội"} | success |
| D02_N00006_noisy | libpostal | D02 | abbreviation_misunderstood | ERROR | Phố S0ng Tháp,P.Phu Khe,T.Bắc Ninh | {"SoNha": "", "TenDuong": "", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": ""} | {"SoNha": "8", "TenDuong": "Phố Song Tháp", "PhuongXa": "Phường Phù Khê", "QuanHuyen": "", "TinhThanh": "Tỉnh Bắc Ninh"} | success |
| D02_N00001_clean | libpostal | D02 | hallucination_over_imputation | PARTIAL | 213, Phố Lương Định Của, Phường Phương Liễu, Tỉnh Bắc Ninh | {"SoNha": "213", "TenDuong": "phố lương định của", "PhuongXa": "", "QuanHuyen": "phường phương", "TinhThanh": "tỉnh bắc ninh"} | {"SoNha": "213", "TenDuong": "Phố Lương Định Của", "PhuongXa": "Phường Phương Liễu", "QuanHuyen": "", "TinhThanh": "Tỉnh Bắc Ninh"} | success |
| D02_N00002_clean | libpostal | D02 | missing_field | PARTIAL | 37/11, Đường Đặng Thùy Trâm, Phường Bình Lợi Trung, Thành phố Hồ Chí Minh | {"SoNha": "37/11", "TenDuong": "đường đặng thùy trâm phường bình lợi trung", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "thành phố hồ chí minh"} | {"SoNha": "37/11", "TenDuong": "Đường Đặng Thùy Trâm", "PhuongXa": "Phường Bình Lợi Trung", "QuanHuyen": "", "TinhThanh": "Thành phố Hồ Chí Minh"} | success |
| D02_N00026_noisy | libpostal | D02 | parse_boundary_error | ERROR | 1 - Ngõ 40 Đặng Thùy Trâm - P Dich Vong Hau - Quận Cầu Giấy - HN | {"SoNha": "1 ngõ 40", "TenDuong": "đặng thùy trâm p dich vong hau", "PhuongXa": "", "QuanHuyen": "cầu giấy", "TinhThanh": "quận"} | {"SoNha": "1", "TenDuong": "Ngõ 40 Đặng Thùy Trâm", "PhuongXa": "Phường Dịch Vọng Hậu", "QuanHuyen": "Quận Cầu Giấy", "TinhThanh": "Hà Nội"} | success |
| D02_N00027_noisy | vietnamadminunits | D02 | abbreviation_misunderstood | ERROR | Pho Nguyen Xuan Chinh,P.Tiền Ninh Vệ,Thành phố Bắc Ninh,Bắc N1nh | {"SoNha": "", "TenDuong": "Pho Nguyen Xuan Chinh", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "Tỉnh Bắc Ninh"} | {"SoNha": "12", "TenDuong": "Phố Nguyễn Xuân Chính", "PhuongXa": "Phường Tiền Ninh Vệ", "QuanHuyen": "Thành phố Bắc Ninh", "TinhThanh": "Bắc Ninh"} | success |
| D02_N00001_noisy | vietnamadminunits | D02 | missing_field | PARTIAL | 213; Phố Lương Định Của; P.Phương Liễu; Tinh Bac Ninh | {"SoNha": "", "TenDuong": "213; Phố Lương Định Của; P", "PhuongXa": "Phường Phương Liễu", "QuanHuyen": "", "TinhThanh": "Tỉnh Bắc Ninh"} | {"SoNha": "213", "TenDuong": "Phố Lương Định Của", "PhuongXa": "Phường Phương Liễu", "QuanHuyen": "", "TinhThanh": "Tỉnh Bắc Ninh"} | success |
| D02_N00003_clean | vietnamadminunits | D02 | parse_boundary_error | ERROR | 18, Phố Ô Chợ Dừa, Chợ Dừa, Đống Đa, Hà Nội | {"SoNha": "", "TenDuong": "18", "PhuongXa": "Phường Ô Chợ Dừa", "QuanHuyen": "Quận Đống Đa", "TinhThanh": "Thành phố Hà Nội"} | {"SoNha": "18", "TenDuong": "Phố Ô Chợ Dừa", "PhuongXa": "Chợ Dừa", "QuanHuyen": "Đống Đa", "TinhThanh": "Hà Nội"} | success |
| D03_0000 | libpostal | D03 | missing_field | ERROR | NT02-29, Ngọc Trai 2, Đa Tốn, Gia Lâm, Hà Nội | {"SoNha": "2", "TenDuong": "nt02-29 ngọc trai đa tốn gia lâm", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "hà nội"} | {"SoNha": "NT02-29", "TenDuong": "Ngọc Trai 2", "PhuongXa": "Đa Tốn", "QuanHuyen": "Gia Lâm", "TinhThanh": "Hà Nội"} | success |
| D03_0111 | libpostal | D03 | parse_boundary_error | ERROR | A1-Fl.5, Km 10, Đường Trần Phú, Mộ Lao, Hà Đông, Hà Nội | {"SoNha": "", "TenDuong": "a1-fl.5 km 10 đường trần phú", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "mộ hà nội"} | {"SoNha": "A1-Fl.5, Km 10", "TenDuong": "Đường Trần Phú", "PhuongXa": "Mộ Lao", "QuanHuyen": "Hà Đông", "TinhThanh": "Hà Nội"} | success |
| D03_0165 | vietnamadminunits | D03 | abbreviation_misunderstood | ERROR | Lô VA, Đường số 24, phường Tân Thuận Đông, 7, TP. Hồ Chí Minh | {"SoNha": "", "TenDuong": "Lô Va", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "Thành phố Hồ Chí Minh"} | {"SoNha": "Lô VA", "TenDuong": "Đường số 24", "PhuongXa": "phường Tân Thuận Đông", "QuanHuyen": "7", "TinhThanh": "TP. Hồ Chí Minh"} | success |
| D03_0003 | vietnamadminunits | D03 | missing_field | PARTIAL | 73, Đường Lý Quốc Sư, Phường Võ Cường, Thành phố Bắc Ninh, Bắc Ninh | {"SoNha": "73", "TenDuong": "Đường Lý Quốc Sư", "PhuongXa": "Phường Võ Cường", "QuanHuyen": "Thành phố Bắc Ninh", "TinhThanh": "Tỉnh Bắc Ninh"} | {"SoNha": "73", "TenDuong": "Đường Lý Quốc Sư", "PhuongXa": "Phường Võ Cường", "QuanHuyen": "Thành phố Bắc Ninh", "TinhThanh": "Bắc Ninh"} | success |
| D03_0000 | vietnamadminunits | D03 | parse_boundary_error | ERROR | NT02-29, Ngọc Trai 2, Đa Tốn, Gia Lâm, Hà Nội | {"SoNha": "", "TenDuong": "Nt02 - 29, Ngọc Trai 2", "PhuongXa": "Xã Đa Tốn", "QuanHuyen": "Huyện Gia Lâm", "TinhThanh": "Thành phố Hà Nội"} | {"SoNha": "NT02-29", "TenDuong": "Ngọc Trai 2", "PhuongXa": "Đa Tốn", "QuanHuyen": "Gia Lâm", "TinhThanh": "Hà Nội"} | success |
| D04_0025 | libpostal | D04 | abbreviation_misunderstood | ERROR | Đường Hoàng Diệu, Phường Ba Đình, TP.HN | {"SoNha": "", "TenDuong": "đường hoàng diệu phường ba đình tp.hn", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": ""} | {"SoNha": "", "TenDuong": "Đường Hoàng Diệu", "PhuongXa": "Phường Ba Đình", "QuanHuyen": "", "TinhThanh": "TP.HN"} | success |
| D04_0005 | libpostal | D04 | hallucination_over_imputation | ERROR | Đường Hoàng Quốc Việt, Phường Cổ Nhuế 1, Q. Bắc Từ Liêm, Hà Nội | {"SoNha": "1 q.", "TenDuong": "đường hoàng quốc việt phường cổ nhuế bắc từ liêm", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "hà nội"} | {"SoNha": "", "TenDuong": "Đường Hoàng Quốc Việt", "PhuongXa": "Phường Cổ Nhuế 1", "QuanHuyen": "Q. Bắc Từ Liêm", "TinhThanh": "Hà Nội"} | success |
| D04_0000 | libpostal | D04 | missing_field | ERROR | 9, Ngách 1/88 Phạm Tuấn Tài, Phường Dịch Vọng Hậu, Hà Nội | {"SoNha": "9", "TenDuong": "ngách 1/88", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "phạm hà nội"} | {"SoNha": "9", "TenDuong": "Ngách 1/88 Phạm Tuấn Tài", "PhuongXa": "Phường Dịch Vọng Hậu", "QuanHuyen": "", "TinhThanh": "Hà Nội"} | success |
| D04_0023 | libpostal | D04 | parse_boundary_error | ERROR | Phố Yên Mẫn, Phường Kinh Bắc, T Bắc Ninh | {"SoNha": "", "TenDuong": "", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": ""} | {"SoNha": "", "TenDuong": "Phố Yên Mẫn", "PhuongXa": "Phường Kinh Bắc", "QuanHuyen": "", "TinhThanh": "T Bắc Ninh"} | success |
| D04_0003 | vietnamadminunits | D04 | abbreviation_misunderstood | ERROR | 89, Hoa Lan, P.2, TP. HCM | {"SoNha": "", "TenDuong": "89", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "Thành phố Hồ Chí Minh"} | {"SoNha": "89", "TenDuong": "Hoa Lan", "PhuongXa": "P.2", "QuanHuyen": "", "TinhThanh": "TP. HCM"} | success |
| D04_0007 | vietnamadminunits | D04 | hallucination_over_imputation | ERROR | Phố Ngọc Hà, Quận Ba Đình, Hà Nội | {"SoNha": "", "TenDuong": "Phố", "PhuongXa": "Phường Ngọc Hà", "QuanHuyen": "Quận Ba Đình", "TinhThanh": "Thành phố Hà Nội"} | {"SoNha": "", "TenDuong": "Phố Ngọc Hà", "PhuongXa": "", "QuanHuyen": "Quận Ba Đình", "TinhThanh": "Hà Nội"} | success |
| D04_0001 | vietnamadminunits | D04 | missing_field | PARTIAL | Đường Khả Lễ, Phường Võ Cường, T.Bắc Ninh | {"SoNha": "", "TenDuong": "Đường Khả Lễ", "PhuongXa": "Phường Võ Cường", "QuanHuyen": "", "TinhThanh": "Tỉnh Bắc Ninh"} | {"SoNha": "", "TenDuong": "Đường Khả Lễ", "PhuongXa": "Phường Võ Cường", "QuanHuyen": "", "TinhThanh": "T.Bắc Ninh"} | success |
| D04_0000 | vietnamadminunits | D04 | parse_boundary_error | ERROR | 9, Ngách 1/88 Phạm Tuấn Tài, Phường Dịch Vọng Hậu, Hà Nội | {"SoNha": "", "TenDuong": "9", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "Thành phố Hà Nội"} | {"SoNha": "9", "TenDuong": "Ngách 1/88 Phạm Tuấn Tài", "PhuongXa": "Phường Dịch Vọng Hậu", "QuanHuyen": "", "TinhThanh": "Hà Nội"} | success |
| D06_0001 | libpostal | D06 | missing_field | PARTIAL | 55, Đường Trần Hưng Đạo, Phường Quế Võ, Thị xã Quế Võ, Bắc Ninh | {"SoNha": "55", "TenDuong": "đường trần hưng đạo", "PhuongXa": "", "QuanHuyen": "quế võ thị xã quế võ bắc ninh", "TinhThanh": "phường"} | {"SoNha": "55", "TenDuong": "Đường Trần Hưng Đạo", "PhuongXa": "Phường Quế Võ", "QuanHuyen": "Thị xã Quế Võ", "TinhThanh": "Bắc Ninh"} | success |
| D06_0000 | libpostal | D06 | parse_boundary_error | ERROR | 6, Ngõ 42 Phố Trần Bình Trọng, Phường Phương Liễu, Thị xã Quế Võ, Bắc Ninh | {"SoNha": "6 ngõ 42", "TenDuong": "phố trần bình trọng", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "phường"} | {"SoNha": "6", "TenDuong": "Ngõ 42 Phố Trần Bình Trọng", "PhuongXa": "Phường Phương Liễu", "QuanHuyen": "Thị xã Quế Võ", "TinhThanh": "Bắc Ninh"} | success |
| D06_0000_m25 | vietnamadminunits | D06 | missing_field | ERROR | 6, Ngõ 42 Phố Trần Bình Trọng, Phường Phương Liễu, Thị xã Quế Võ, Bắc Ninh | {"SoNha": "6", "TenDuong": "Ngõ 42 Phố Trần Bình Trọng, Phường Phương Liễu", "PhuongXa": "Phường Quế Võ", "QuanHuyen": "", "TinhThanh": "Tỉnh Bắc Ninh"} | {"SoNha": "6", "TenDuong": "Ngõ 42 Phố Trần Bình Trọng", "PhuongXa": "Phường Phương Liễu", "QuanHuyen": "Thị xã Quế Võ", "TinhThanh": "Bắc Ninh"} | success |
| D07_0281_N-1 | vietnamadminunits | D07 | missing_field | ERROR | 14E, Đường Quốc Hương, Thảo Điền, 2, Ho Chi Minh CIty | {"SoNha": "", "TenDuong": "", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "Thành phố Hồ Chí Minh"} | {"SoNha": "", "TenDuong": "", "PhuongXa": "Phường An Khánh", "QuanHuyen": "", "TinhThanh": "Thành phố Hồ Chí Minh"} | success |
| D07_0018_M-N | vietnamadminunits | D07 | wrong_target | ERROR | 36, Phố Trần Phú, Phường Điện Biên, Quận Ba Đình, Hà Nội | {"SoNha": "36", "TenDuong": "Phố Trần Phú", "PhuongXa": "Phường Hoàn Kiếm", "QuanHuyen": "", "TinhThanh": "Thành phố Hà Nội"} | {"SoNha": "", "TenDuong": "", "PhuongXa": "Phường Ba Đình", "QuanHuyen": "", "TinhThanh": "Thành phố Hà Nội"} | success |

## 6. Diễn giải có điều kiện

Các output chỉ chứng minh hành vi quan sát được của adapter và tool ở run này. Khi raw log không có trace nhánh converter, không được kết luận một lỗi cụ thể do fallback/geocoder. Run mới ghi `conversion_trace` để phân biệt ánh xạ từ điển, geocoder và fallback. Bất kỳ kết luận nhân quả nào phải trỏ tới ID cùng trace hoặc được ghi là giả thuyết kỹ thuật.
