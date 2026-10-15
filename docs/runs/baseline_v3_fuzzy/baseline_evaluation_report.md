# Đánh giá baseline địa chỉ Việt Nam 2025

- Ngày tạo: 24/09/2026
- Dòng benchmark: 5500; lượt dự đoán: 13000.
- Công cụ thực chạy: `libpostal`, `vietnamadminunits`.
- VietnamAdminUnits nhận mode do protocol cung cấp ở Data 01/02/03/04, chạy hai mode ở Data 06 và convert cũ → mới ở Data 07. Đây không phải phép đo phân loại T1 tự động.
- `libpostal` gọi Python binding của thư viện C và model data mặc định; raw nhãn Libpostal được lưu riêng trước khi ánh xạ sang 5 trường.
- `exact_match_rate` yêu cầu mọi trường được chấm khớp sau chuẩn hóa. `micro_f1_scored_fields` gộp TP/FP/FN trên các trường được chấm; một MISMATCH đóng góp một FP và một FN.
- Fuzzy: `normalized_levenshtein`; NFC Unicode, casefold, collapse whitespace, strip surrounding whitespace and trailing comma separators, retain Vietnamese diacritics and administrative unit-type prefixes, and compare only corresponding fields. Ignore pairs where both values are empty; score a one-sided empty pair as 0. Report the number of non-empty field pairs used as the denominator. Fuzzy similarity đo độ gần chuỗi, không xác nhận đúng thực thể hành chính.

## 1. Dữ liệu và khả năng tái lập

| File | Dòng | SHA-256 |
| --- | ---: | --- |
| `01_full_address_new_verified.csv` | 1000 | `7e2afd47828d04d108c67d29f45cb50b6a5321ae8feef595cf2b67229796a60d` |
| `02_raw_noisy_synthetic_1000.csv` | 1000 | `bd425883f624c98e206d6ab197240b9642eb63352b56efd06723d04401751def` |
| `03_real_address_old_1500.csv` | 1500 | `d2748f4cedc498046100779a6f59fb1ef1e79c3049aeefe9d6d542afa79badda` |
| `04_missing_fields_800.csv` | 800 | `46305aac4821c2f2bc96913cfaf3a89f3087dd91216f5093dc7f89b8541fc021` |
| `06_hybrid_addresses_600.csv` | 600 | `6249b06941d6e89a8a731fc47d0b844ee89ed8dce5a902bfcaac13d2785ced8d` |
| `07_bidirectional_pairs_verified.csv` | 600 | `3f11b0d02a05922662613c460014da34f89def7da1e7e1ba6ef496aa369245fc` |

Trạng thái lời gọi công cụ (raw log):

| Công cụ | Trạng thái | n |
| --- | --- | ---: |
| `libpostal` | `success` | 5900 |
| `vietnamadminunits` | `success` | 7100 |

- Phiên bản công cụ: `{"vietnamadminunits": "1.0.4", "libpostal": "1.1.11", "libpostal_model": "openvenues default", "libpostal_c_commit": "25099c506612b34b23b1bfe286ca6321fcf06f35"}`.
- Python `3.14.4`; thư viện chạy: `{"pandas": "2.3.3", "pyarrow": "23.0.1", "osmium": "4.3.1", "tqdm": "4.70.1"}`.
- Hash mã khi chạy prediction: `{"src/evaluation/adapters/libpostal_adapter.py": "53817addaaf5bce4312b4823137e1a7e8d7c406a27a85eb7c6c88fbc9fa289a2", "src/evaluation/adapters/vnadmin_adapter.py": "569bbbdc138224382c8d805191b7342d27311d49299c0cff2bb9d8045275fc1a", "src/evaluation/scorer.py": "ea439c543bc29212e1824a2620aa9895c883cdfdc73802df3dcbbe5d170b2cdb", "src/evaluation/data_contract.py": "85f65d953394d9276604d8125538a7da03c3ab23e457ba9fb40cb2910f689d83", "src/evaluation/manifest.py": "6e25c6d7a5ea72d346ff82e93006d75b68f255c10b3bd97d8a24d7379f3d12ce", "src/evaluation/protocol.py": "75ca13066d7b7289721e7b76d8345877d888c5e377e77513c273a0e653103c86", "src/evaluation/run_artifacts.py": "a670f7a8ada43b3702323928300d368dee05b64b27efaef81e30880de43f758b", "scripts/05_run_baseline_pilot.py": "8037b7c3fcfeb0c19ee1beae4136967e41aaa70a043832cef72e57651f605a25", "scripts/06_run_baseline_full.py": "5c89b65b61a1ed3eac42f83035042131767c5204da8fef8357763786391b016b", "scripts/07_generate_baseline_report.py": "6eefb729ee4f859fd87dc713cc78ad2269b605fb1817ff4143da2115ab62d50f", "scripts/08_generate_report_materials.py": "1f23669c4cd816a33f8338647c1ae7bb064dc4c8dcb8f4a8cd939858655f27e0", "scripts/build_baseline_dashboard.py": "9352b15cc98d17c1bd43f00a3f985328824fb4b425d042c59215a1beec9f450a", "src/evaluation/reporter.py": "cdb3e24959b4bf9b90e7d80630ddb6acdf8fae69dc78ec0e30baa7ea6f936f46"}`.
- Hash mã tạo báo cáo: `cdb3e24959b4bf9b90e7d80630ddb6acdf8fae69dc78ec0e30baa7ea6f936f46`.
- Data 04/06 được phân tầng theo KieuThieu/KieuLai; tỷ lệ theo nhóm là diagnostic strata, không phải xác suất uncertainty.
- Trace converter Data 07 là tín hiệu chẩn đoán; candidate count không phải confidence hay khoảng cách tới ranh giới. Chưa có nhãn uncertainty hoặc hình học biên giới để tính calibration/ECE.
- Data 07 chỉ có N-1/M-N và tập trung ở miền Bắc; không suy rộng sang 1-1/1-N hay các vùng chưa có mẫu.

## 2. Parse địa chỉ theo các tập 01, 03, 04 và 06

Các bảng báo exact cùng fuzzy theo trường. Data 03 là benchmark hệ cũ sạch hoàn toàn có đủ 5 trường (không còn dòng thiếu tự nhiên). Riêng Data 04 chấm trích xuất các trường còn trên chuỗi bề mặt (phục hồi trường bị lược được phân tích riêng ở Mục 4); Data 06 báo hai mode VietnamAdminUnits riêng.

### Data 01 mới

| Nhóm | Công cụ | n | Đúng | Một phần | Sai |
| --- | --- | ---: | ---: | ---: | ---: |
| 01 mới | `libpostal` | 1000 | 0.2% | 91.7% | 8.1% |
| 01 mới | `vietnamadminunits` | 1000 | 97.3% | 2.7% | 0.0% |

Metric strict và fuzzy từng trường (fuzzy mean kèm số cặp):

| Công cụ | Trường | Exact đúng / n | Exact rate | Fuzzy mean / n cặp | F1 strict |
| --- | --- | ---: | ---: | ---: | ---: |
| libpostal | SoNha | 920 / 1000 | 0.920 | 0.947 / 1000 | 0.924 |
| libpostal | TenDuong | 370 / 1000 | 0.370 | 0.735 / 1000 | 0.373 |
| libpostal | PhuongXa | 2 / 1000 | 0.002 | 0.015 / 1000 | 0.004 |
| libpostal | QuanHuyen | 225 / 1000 | 0.225 | 0.000 / 775 | 0.000 |
| libpostal | TinhThanh | 938 / 1000 | 0.938 | 0.981 / 1000 | 0.938 |
| vietnamadminunits | SoNha | 974 / 1000 | 0.974 | 0.980 / 1000 | 0.979 |
| vietnamadminunits | TenDuong | 973 / 1000 | 0.973 | 0.992 / 1000 | 0.973 |
| vietnamadminunits | PhuongXa | 1000 / 1000 | 1.000 | 1.000 / 1000 | 1.000 |
| vietnamadminunits | QuanHuyen | 1000 / 1000 | 1.000 | n/a | 0.000 |
| vietnamadminunits | TinhThanh | 1000 / 1000 | 1.000 | 1.000 / 1000 | 1.000 |

### Data 03 cũ

| Nhóm | Công cụ | n | Đúng | Một phần | Sai |
| --- | --- | ---: | ---: | ---: | ---: |
| 03 cũ | `libpostal` | 1500 | 0.1% | 62.4% | 37.5% |
| 03 cũ | `vietnamadminunits` | 1500 | 5.8% | 74.1% | 20.1% |

Metric strict và fuzzy từng trường (fuzzy mean kèm số cặp):

| Công cụ | Trường | Exact đúng / n | Exact rate | Fuzzy mean / n cặp | F1 strict |
| --- | --- | ---: | ---: | ---: | ---: |
| libpostal | SoNha | 1062 / 1500 | 0.708 | 0.794 / 1500 | 0.718 |
| libpostal | TenDuong | 378 / 1500 | 0.252 | 0.563 / 1500 | 0.259 |
| libpostal | PhuongXa | 5 / 1500 | 0.003 | 0.057 / 1500 | 0.006 |
| libpostal | QuanHuyen | 61 / 1500 | 0.041 | 0.079 / 1500 | 0.070 |
| libpostal | TinhThanh | 1123 / 1500 | 0.749 | 0.851 / 1500 | 0.756 |
| vietnamadminunits | SoNha | 1176 / 1500 | 0.784 | 0.794 / 1500 | 0.866 |
| vietnamadminunits | TenDuong | 1170 / 1500 | 0.780 | 0.855 / 1500 | 0.780 |
| vietnamadminunits | PhuongXa | 614 / 1500 | 0.409 | 0.715 / 1500 | 0.417 |
| vietnamadminunits | QuanHuyen | 639 / 1500 | 0.426 | 0.765 / 1500 | 0.430 |
| vietnamadminunits | TinhThanh | 159 / 1500 | 0.106 | 0.491 / 1500 | 0.106 |

### Data 04 thiếu trường

| Nhóm | Công cụ | n | Đúng | Một phần | Sai |
| --- | --- | ---: | ---: | ---: | ---: |
| 04 thiếu trường | `libpostal` | 800 | 14.2% | 26.9% | 58.9% |
| 04 thiếu trường | `vietnamadminunits` | 800 | 4.9% | 20.2% | 74.9% |

Metric strict và fuzzy từng trường (fuzzy mean kèm số cặp):

| Công cụ | Trường | Exact đúng / n | Exact rate | Fuzzy mean / n cặp | F1 strict |
| --- | --- | ---: | ---: | ---: | ---: |
| libpostal | SoNha | 693 / 800 | 0.866 | 0.767 / 398 | 0.792 |
| libpostal | TenDuong | 224 / 800 | 0.280 | 0.685 / 800 | 0.285 |
| libpostal | PhuongXa | 338 / 800 | 0.422 | 0.021 / 465 | 0.012 |
| libpostal | QuanHuyen | 337 / 800 | 0.421 | 0.105 / 498 | 0.121 |
| libpostal | TinhThanh | 550 / 800 | 0.688 | 0.785 / 800 | 0.715 |
| vietnamadminunits | SoNha | 460 / 800 | 0.575 | 0.012 / 341 | 0.006 |
| vietnamadminunits | TenDuong | 335 / 800 | 0.419 | 0.439 / 800 | 0.447 |
| vietnamadminunits | PhuongXa | 413 / 800 | 0.516 | 0.497 / 491 | 0.250 |
| vietnamadminunits | QuanHuyen | 596 / 800 | 0.745 | 0.717 / 310 | 0.350 |
| vietnamadminunits | TinhThanh | 259 / 800 | 0.324 | 0.622 / 800 | 0.324 |

### Data 06 lai

**FROM_2025**

| Nhóm | Công cụ | n | Đúng | Một phần | Sai |
| --- | --- | ---: | ---: | ---: | ---: |
| FROM_2025 | `vietnamadminunits` | 600 | 0.0% | 78.5% | 21.5% |

**LEGACY**

| Nhóm | Công cụ | n | Đúng | Một phần | Sai |
| --- | --- | ---: | ---: | ---: | ---: |
| LEGACY | `vietnamadminunits` | 600 | 26.2% | 62.2% | 11.7% |

**single parse**

| Nhóm | Công cụ | n | Đúng | Một phần | Sai |
| --- | --- | ---: | ---: | ---: | ---: |
| single parse | `libpostal` | 600 | 0.3% | 82.3% | 17.3% |

Theo kiểu lai:

| Công cụ | Mode | Kiểu | n | Đúng toàn phần | Fuzzy mean | Cặp fuzzy |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| libpostal | single parse | C1 | 420 | 0.0% | 0.560 | 2100 |
| libpostal | single parse | C2 | 120 | 0.0% | 0.648 | 600 |
| libpostal | single parse | C3 | 60 | 3.3% | 0.634 | 300 |
| vietnamadminunits | FROM_2025 | C1 | 420 | 0.0% | 0.676 | 2100 |
| vietnamadminunits | FROM_2025 | C2 | 120 | 0.0% | 0.739 | 600 |
| vietnamadminunits | FROM_2025 | C3 | 60 | 0.0% | 0.339 | 300 |
| vietnamadminunits | LEGACY | C1 | 420 | 1.2% | 0.713 | 2100 |
| vietnamadminunits | LEGACY | C2 | 120 | 80.0% | 0.894 | 600 |
| vietnamadminunits | LEGACY | C3 | 60 | 93.3% | 0.977 | 300 |
## 3. Data 02: độ bền trên cặp sạch và nhiễu

Các nhóm nhiễu có thể đồng xuất hiện. `dinh_dang_phan_cach` có ở mọi dòng, nên bảng theo loại không diễn giải quan hệ nhân quả riêng của từng phép biến đổi. Exact hiển thị số bản ghi đúng/mẫu số; fuzzy hiển thị trung bình/số cặp trường được chấm; F1 là `micro_f1_scored_fields`.

| Công cụ | Mức | n | Exact sạch đúng/n | Exact nhiễu đúng/n | Fuzzy sạch mean/n cặp | Fuzzy nhiễu mean/n cặp | Micro F1 sạch | Micro F1 nhiễu | Sạch đúng → nhiễu sai |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `libpostal` | nhe | 376 | 1 / 376 | 0 / 376 | 0.514 / 1836 | 0.480 / 1811 | 0.500 | 0.418 | 1 |
| `libpostal` | vua | 413 | 0 / 413 | 0 / 413 | 0.520 / 2015 | 0.459 / 1971 | 0.503 | 0.368 | 0 |
| `libpostal` | nang | 211 | 0 / 211 | 0 / 211 | 0.517 / 1034 | 0.393 / 984 | 0.502 | 0.294 | 0 |
| `libpostal` | all | 1000 | 1 / 1000 | 0 / 1000 | 0.517 / 4885 | 0.453 / 4766 | 0.502 | 0.372 | 1 |
| `vietnamadminunits` | nhe | 376 | 181 / 376 | 64 / 376 | 0.834 / 1703 | 0.737 / 1703 | 0.706 | 0.531 | 117 |
| `vietnamadminunits` | vua | 413 | 217 / 413 | 53 / 413 | 0.847 / 1856 | 0.731 / 1856 | 0.736 | 0.534 | 164 |
| `vietnamadminunits` | nang | 211 | 119 / 211 | 6 / 211 | 0.861 / 941 | 0.483 / 941 | 0.770 | 0.419 | 113 |
| `vietnamadminunits` | all | 1000 | 517 / 1000 | 123 / 1000 | 0.845 / 4500 | 0.681 / 4500 | 0.732 | 0.512 | 394 |

### Nhóm phép biến đổi đồng xuất hiện

Một dòng có thể thuộc nhiều nhóm, do đó không cộng các mẫu số và không xem chênh lệch là hiệu ứng nhân quả.

| Công cụ | Phép biến đổi | n | Exact sạch đúng/n | Exact nhiễu đúng/n | Fuzzy sạch mean/n cặp | Fuzzy nhiễu mean/n cặp | F1 sạch | F1 nhiễu |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `libpostal` | `viet_tat` | 603 | 1 / 603 | 0 / 603 | 0.531 / 2927 | 0.441 / 2821 | 0.520 | 0.336 |
| `libpostal` | `bo_dau` | 455 | 0 / 455 | 0 / 455 | 0.520 / 2222 | 0.433 / 2154 | 0.505 | 0.334 |
| `libpostal` | `loi_ocr_ky_tu` | 90 | 0 / 90 | 0 / 90 | 0.505 / 444 | 0.355 / 416 | 0.481 | 0.268 |
| `libpostal` | `thieu_` | 148 | 0 / 148 | 0 / 148 | 0.525 / 723 | 0.372 / 686 | 0.507 | 0.274 |
| `libpostal` | `dao_thu_tu_hanh_chinh` | 95 | 0 / 95 | 0 / 95 | 0.523 / 464 | 0.393 / 442 | 0.512 | 0.293 |
| `libpostal` | `dinh_dang_phan_cach` | 1000 | 1 / 1000 | 0 / 1000 | 0.517 / 4885 | 0.453 / 4766 | 0.502 | 0.372 |
| `vietnamadminunits` | `viet_tat` | 603 | 389 / 603 | 95 / 603 | 0.906 / 2636 | 0.724 / 2636 | 0.847 | 0.616 |
| `vietnamadminunits` | `bo_dau` | 455 | 255 / 455 | 50 / 455 | 0.861 / 2027 | 0.656 / 2027 | 0.761 | 0.514 |
| `vietnamadminunits` | `loi_ocr_ky_tu` | 90 | 48 / 90 | 1 / 90 | 0.850 / 405 | 0.382 / 405 | 0.738 | 0.336 |
| `vietnamadminunits` | `thieu_` | 148 | 85 / 148 | 0 / 148 | 0.855 / 660 | 0.397 / 660 | 0.765 | 0.353 |
| `vietnamadminunits` | `dao_thu_tu_hanh_chinh` | 95 | 52 / 95 | 2 / 95 | 0.851 / 425 | 0.504 / 425 | 0.752 | 0.420 |
| `vietnamadminunits` | `dinh_dang_phan_cach` | 1000 | 517 / 1000 | 123 / 1000 | 0.845 / 4500 | 0.681 / 4500 | 0.732 | 0.512 |

## 4. Data 04: phục hồi trường đã lược

Bảng này tách khỏi điểm parse trường còn hiện diện. Điền đúng một trường đã lược là phục hồi đúng; điền sai mới là suy đoán sai.

| Công cụ | Trường bị lược | n | Phục hồi đúng | Điền sai | Không điền |
| --- | --- | ---: | ---: | ---: | ---: |
| `libpostal` | drop_ward | 241 | 0 | 7 | 234 |
| `libpostal` | drop_district | 99 | 0 | 10 | 89 |
| `libpostal` | drop_housenumber | 348 | 2 | 48 | 298 |
| `libpostal` | drop_housenumber_ward | 224 | 0 | 19 | 205 |
| `libpostal` | tất cả | 912 | 2 | 84 | 826 |
| `vietnamadminunits` | drop_ward | 241 | 2 | 22 | 217 |
| `vietnamadminunits` | drop_district | 99 | 1 | 8 | 90 |
| `vietnamadminunits` | drop_housenumber | 348 | 1 | 0 | 347 |
| `vietnamadminunits` | drop_housenumber_ward | 224 | 0 | 20 | 204 |
| `vietnamadminunits` | tất cả | 912 | 4 | 50 | 858 |

## 5. Data 07: chuyển đổi hành chính cũ → mới

Chỉ VietnamAdminUnits có API converter và chỉ hai trường `PhuongXa`, `TinhThanh` được chấm. Không có thử nghiệm chiều mới → cũ; API hiện tại không cung cấp tác vụ đó. Fuzzy là chẩn đoán gần chuỗi; đúng cặp đơn vị vẫn dùng exact match.

| Quan hệ | n | Đúng cặp đơn vị | Fuzzy mean / cặp | Sai đích có output | Trả rỗng |
| --- | ---: | ---: | ---: | ---: | ---: |
| N-1 | 244 | 242 (99.2%) | 0.996 / 488 | 0 | 2 |
| M-N | 356 | 344 (96.6%) | 0.992 / 712 | 12 | 0 |

## 6. Mẫu lỗi truy vết

Các dòng sau lấy trực tiếp từ CSV dự đoán; `ID` dùng để tra raw response cùng khóa ID/công cụ.

| ID | Công cụ | Input | Dự đoán | Đáp án |
| --- | --- | --- | --- | --- |
| D01_0000 | libpostal | 394, Đường Lý Thường Kiệt, Phường Phù Khê, Tỉnh Bắc Ninh | {"SoNha": "394", "TenDuong": "đường lý thường kiệt", "PhuongXa": "", "QuanHuyen": "phường phù", "TinhThanh": "tỉnh bắc ninh"} | {"SoNha": "394", "TenDuong": "Đường Lý Thường Kiệt", "PhuongXa": "Phường Phù Khê", "QuanHuyen": "", "TinhThanh": "Tỉnh Bắc Ninh"} |
| D03_0000 | vietnamadminunits | NT02-29, Ngọc Trai 2, Đa Tốn, Gia Lâm, Hà Nội | {"SoNha": "", "TenDuong": "Nt02 - 29, Ngọc Trai 2", "PhuongXa": "Xã Đa Tốn", "QuanHuyen": "Huyện Gia Lâm", "TinhThanh": "Thành phố Hà Nội"} | {"SoNha": "NT02-29", "TenDuong": "Ngọc Trai 2", "PhuongXa": "Đa Tốn", "QuanHuyen": "Gia Lâm", "TinhThanh": "Hà Nội"} |
| D04_0000 | vietnamadminunits | 9, Ngách 1/88 Phạm Tuấn Tài, Phường Dịch Vọng Hậu, Hà Nội | {"SoNha": "", "TenDuong": "9", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "Thành phố Hà Nội"} | {"SoNha": "9", "TenDuong": "Ngách 1/88 Phạm Tuấn Tài", "PhuongXa": "Phường Dịch Vọng Hậu", "QuanHuyen": "", "TinhThanh": "Hà Nội"} |
| D06_0000_m25 | vietnamadminunits | 6, Ngõ 42 Phố Trần Bình Trọng, Phường Phương Liễu, Thị xã Quế Võ, Bắc Ninh | {"SoNha": "6", "TenDuong": "Ngõ 42 Phố Trần Bình Trọng, Phường Phương Liễu", "PhuongXa": "Phường Quế Võ", "QuanHuyen": "", "TinhThanh": "Tỉnh Bắc Ninh"} | {"SoNha": "6", "TenDuong": "Ngõ 42 Phố Trần Bình Trọng", "PhuongXa": "Phường Phương Liễu", "QuanHuyen": "Thị xã Quế Võ", "TinhThanh": "Bắc Ninh"} |
| D07_0018_M-N | vietnamadminunits | 36, Phố Trần Phú, Phường Điện Biên, Quận Ba Đình, Hà Nội | {"PhuongXa": "Phường Hoàn Kiếm", "TinhThanh": "Thành phố Hà Nội"} | {"PhuongXa": "Phường Ba Đình", "TinhThanh": "Thành phố Hà Nội"} |

## 7. Giới hạn

- Điểm VietnamAdminUnits ở Data 01/02/03/04 có oracle mode, chưa đo T1. Data 06 không đo khả năng cảnh báo địa chỉ lai vì API không trả nhãn cảnh báo.
- T0 theo 11 nhãn span chưa thể đo vì bộ hiện tại chỉ có ground truth 5 trường địa chỉ.
- Data 02 là nhiễu tổng hợp; các loại nhiễu đồng xuất hiện và không chứng minh độ bền trên hóa đơn thật.
- Các trường OSM là nhãn cộng đồng; Data 03 hiện đã được chuẩn hóa và lọc sạch hoàn toàn 100% đủ cả 5 trường (không còn dòng thiếu tự nhiên). Data 04 được sinh có kiểm soát từ các địa chỉ sạch, giữ nguyên ground truth trước khi xóa.
- Data 07 dựa trên OSM diff quan sát được và bảng hành chính; cần đọc coverage trước khi ngoại suy. Converter có thể gọi ArcGIS geocoder qua mạng, nên lần chạy sau cần ghi nhận điều kiện dịch vụ khi so sánh kết quả.
