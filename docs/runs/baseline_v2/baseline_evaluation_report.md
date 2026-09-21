# Đánh giá baseline địa chỉ Việt Nam 2025

- Ngày tạo: 20/09/2026
- Dòng benchmark: 5500; lượt dự đoán: 13000.
- Công cụ thực chạy: `libpostal`, `vietnamadminunits`.
- VietnamAdminUnits nhận mode do protocol cung cấp ở Data 01/02/03/04, chạy hai mode ở Data 06 và convert cũ → mới ở Data 07. Đây không phải phép đo phân loại T1 tự động.
- `libpostal` gọi Python binding của thư viện C và model data mặc định; raw nhãn Libpostal được lưu riêng trước khi ánh xạ sang 5 trường.
- `exact_match_rate` yêu cầu mọi trường được chấm khớp sau chuẩn hóa. `micro_f1_scored_fields` gộp TP/FP/FN trên các trường được chấm; một MISMATCH đóng góp một FP và một FN.

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
| `vietnamadminunits` | `exception` | 4 |
| `vietnamadminunits` | `success` | 7096 |

- Phiên bản công cụ: `{"vietnamadminunits": "1.0.4", "libpostal": "1.1.11", "libpostal_model": "openvenues default", "libpostal_c_commit": "25099c506612b34b23b1bfe286ca6321fcf06f35"}`.
- Python `3.14.4`; thư viện chạy: `{"pandas": "2.3.3", "pyarrow": "23.0.1", "osmium": "4.3.1", "tqdm": "4.70.1"}`.
- Hash mã khi chạy prediction: `{"src/evaluation/adapters/libpostal_adapter.py": "53817addaaf5bce4312b4823137e1a7e8d7c406a27a85eb7c6c88fbc9fa289a2", "src/evaluation/adapters/vnadmin_adapter.py": "530bdf0d2a7c87edcb3327ed4f41dea18af5a6b57c0f41e65602168a3211b6fe", "src/evaluation/scorer.py": "15ea5f5fec0055d367b4374de3d99eba39aa26e3419f011ae59acaa786c8c5a1", "src/evaluation/data_contract.py": "85f65d953394d9276604d8125538a7da03c3ab23e457ba9fb40cb2910f689d83", "src/evaluation/manifest.py": "f3a2995a2a1431c1fc3e6ec7b1b7e78fd98ec3ece427bf875ea425190f4bbad9", "src/evaluation/protocol.py": "a5917c02e4829f08566dde3b6f8f1cace3aaca03d9c8921b51f8251df05e297a", "src/evaluation/run_artifacts.py": "a670f7a8ada43b3702323928300d368dee05b64b27efaef81e30880de43f758b", "scripts/05_run_baseline_pilot.py": "8037b7c3fcfeb0c19ee1beae4136967e41aaa70a043832cef72e57651f605a25", "scripts/06_run_baseline_full.py": "f7a7ea0107118c5504f0dd584f23126f3e90a6c847083694ccc199c19b574b44", "scripts/07_generate_baseline_report.py": "4b671dba347bdd2e9b0a5c2389e3df17426e4a4ea0b4977ab81c747f94f9e62d", "scripts/08_generate_report_materials.py": "49ad65ca251ff2af08def9ac1dd1e5520457e303a3e271febea240f6afe97efa", "scripts/build_baseline_dashboard.py": "721c1fb99ad44bd303f38c691944f1aa55d3c25797a6b3cb10f1fd5615c74b2a", "src/evaluation/reporter.py": "ae6333163a0610db185df615964fa253a96cabfe1c8dbe5a15485d1dc027b8b5"}`.
- Hash mã tạo báo cáo: `ae6333163a0610db185df615964fa253a96cabfe1c8dbe5a15485d1dc027b8b5`.
- Data 07 chỉ có N-1/M-N và tập trung ở miền Bắc; không suy rộng sang 1-1/1-N hay các vùng chưa có mẫu.

## 2. Parse địa chỉ theo các tập 01, 03, 04 và 06

Tỷ lệ dưới đây là exact match 5 trường. Data 03 là benchmark hệ cũ sạch hoàn toàn có đủ 5 trường (không còn dòng thiếu tự nhiên). Riêng Data 04 chấm trích xuất các trường còn trên chuỗi bề mặt (phục hồi trường bị lược được phân tích riêng ở Mục 4); Data 06 báo hai mode VietnamAdminUnits riêng.

### Data 01 mới

| Nhóm | Công cụ | n | Đúng | Một phần | Sai |
| --- | --- | ---: | ---: | ---: | ---: |
| 01 mới | `libpostal` | 1000 | 0.2% | 91.7% | 8.1% |
| 01 mới | `vietnamadminunits` | 1000 | 97.3% | 2.7% | 0.0% |

Micro F1 từng trường:

| Công cụ | SoNha F1 | TenDuong F1 | PhuongXa F1 | QuanHuyen F1 | TinhThanh F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `libpostal` | 0.924 | 0.373 | 0.004 | 0.000 | 0.938 |
| `vietnamadminunits` | 0.979 | 0.973 | 1.000 | n/a | 1.000 |

### Data 03 cũ

| Nhóm | Công cụ | n | Đúng | Một phần | Sai |
| --- | --- | ---: | ---: | ---: | ---: |
| 03 cũ | `libpostal` | 1500 | 0.1% | 62.4% | 37.5% |
| 03 cũ | `vietnamadminunits` | 1500 | 72.9% | 24.8% | 2.3% |

Micro F1 từng trường:

| Công cụ | SoNha F1 | TenDuong F1 | PhuongXa F1 | QuanHuyen F1 | TinhThanh F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `libpostal` | 0.718 | 0.259 | 0.006 | 0.073 | 0.826 |
| `vietnamadminunits` | 0.866 | 0.780 | 0.915 | 0.977 | 0.983 |

### Data 04 thiếu trường

| Nhóm | Công cụ | n | Đúng | Một phần | Sai |
| --- | --- | ---: | ---: | ---: | ---: |
| 04 thiếu trường | `libpostal` | 800 | 15.0% | 26.6% | 58.4% |
| 04 thiếu trường | `vietnamadminunits` | 800 | 26.0% | 30.8% | 43.2% |

Micro F1 từng trường:

| Công cụ | SoNha F1 | TenDuong F1 | PhuongXa F1 | QuanHuyen F1 | TinhThanh F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `libpostal` | 0.792 | 0.285 | 0.012 | 0.162 | 0.724 |
| `vietnamadminunits` | 0.006 | 0.447 | 0.697 | 0.936 | 0.785 |

### Data 06 lai

**FROM_2025**

| Nhóm | Công cụ | n | Đúng | Một phần | Sai |
| --- | --- | ---: | ---: | ---: | ---: |
| FROM_2025 | `vietnamadminunits` | 600 | 0.0% | 92.7% | 7.3% |

**LEGACY**

| Nhóm | Công cụ | n | Đúng | Một phần | Sai |
| --- | --- | ---: | ---: | ---: | ---: |
| LEGACY | `vietnamadminunits` | 600 | 69.2% | 30.5% | 0.3% |

**single parse**

| Nhóm | Công cụ | n | Đúng | Một phần | Sai |
| --- | --- | ---: | ---: | ---: | ---: |
| single parse | `libpostal` | 600 | 0.3% | 83.0% | 16.7% |

Theo kiểu lai:

| Công cụ | Mode | Kiểu | n | Đúng toàn phần |
| --- | --- | --- | ---: | ---: |
| `libpostal` | single parse | C1 | 420 | 0.0% |
| `libpostal` | single parse | C2 | 120 | 0.0% |
| `libpostal` | single parse | C3 | 60 | 3.3% |
| `vietnamadminunits` | FROM_2025 | C1 | 420 | 0.0% |
| `vietnamadminunits` | FROM_2025 | C2 | 120 | 0.0% |
| `vietnamadminunits` | FROM_2025 | C3 | 60 | 0.0% |
| `vietnamadminunits` | LEGACY | C1 | 420 | 62.4% |
| `vietnamadminunits` | LEGACY | C2 | 120 | 80.8% |
| `vietnamadminunits` | LEGACY | C3 | 60 | 93.3% |
## 3. Data 02: độ bền trên cặp sạch và nhiễu

Các nhóm nhiễu có thể đồng xuất hiện. `dinh_dang_phan_cach` có ở mọi dòng, nên bảng theo loại không diễn giải quan hệ nhân quả riêng của từng phép biến đổi. F1 trong mục này là `micro_f1_scored_fields`.

| Công cụ | Mức | n | Sạch đúng | Nhiễu đúng | Micro F1 sạch | Micro F1 nhiễu | Sạch đúng → nhiễu sai |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `libpostal` | nhe | 376 | 0.3% | 0.3% | 0.504 | 0.443 | 1 |
| `libpostal` | vua | 413 | 0.0% | 0.0% | 0.514 | 0.388 | 0 |
| `libpostal` | nang | 211 | 0.0% | 0.0% | 0.511 | 0.315 | 0 |
| `libpostal` | all | 1000 | 0.1% | 0.1% | 0.509 | 0.395 | 1 |
| `vietnamadminunits` | nhe | 376 | 86.4% | 29.5% | 0.951 | 0.783 | 214 |
| `vietnamadminunits` | vua | 413 | 86.2% | 22.8% | 0.946 | 0.752 | 262 |
| `vietnamadminunits` | nang | 211 | 85.8% | 5.7% | 0.944 | 0.574 | 169 |
| `vietnamadminunits` | all | 1000 | 86.2% | 21.7% | 0.947 | 0.732 | 645 |

### Nhóm phép biến đổi đồng xuất hiện

Một dòng có thể thuộc nhiều nhóm, do đó không cộng các mẫu số và không xem chênh lệch là hiệu ứng nhân quả.

| Công cụ | Phép biến đổi | n | Sạch đúng | Nhiễu đúng | F1 sạch | F1 nhiễu |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `libpostal` | `viet_tat` | 603 | 0.2% | 0.2% | 0.531 | 0.372 |
| `libpostal` | `bo_dau` | 455 | 0.0% | 0.0% | 0.514 | 0.353 |
| `libpostal` | `loi_ocr_ky_tu` | 90 | 0.0% | 0.0% | 0.487 | 0.281 |
| `libpostal` | `thieu_` | 148 | 0.0% | 0.0% | 0.513 | 0.295 |
| `libpostal` | `dao_thu_tu_hanh_chinh` | 95 | 0.0% | 0.0% | 0.517 | 0.308 |
| `libpostal` | `dinh_dang_phan_cach` | 1000 | 0.1% | 0.1% | 0.509 | 0.395 |
| `vietnamadminunits` | `viet_tat` | 603 | 91.0% | 23.7% | 0.964 | 0.737 |
| `vietnamadminunits` | `bo_dau` | 455 | 87.5% | 18.2% | 0.949 | 0.704 |
| `vietnamadminunits` | `loi_ocr_ky_tu` | 90 | 83.3% | 2.2% | 0.939 | 0.488 |
| `vietnamadminunits` | `thieu_` | 148 | 83.1% | 0.0% | 0.935 | 0.496 |
| `vietnamadminunits` | `dao_thu_tu_hanh_chinh` | 95 | 83.2% | 4.2% | 0.934 | 0.590 |
| `vietnamadminunits` | `dinh_dang_phan_cach` | 1000 | 86.2% | 21.7% | 0.947 | 0.732 |

## 4. Data 04: phục hồi trường đã lược

Bảng này tách khỏi điểm parse trường còn hiện diện. Điền đúng một trường đã lược là phục hồi đúng; điền sai mới là suy đoán sai.

| Công cụ | Trường bị lược | n | Phục hồi đúng | Điền sai | Không điền |
| --- | --- | ---: | ---: | ---: | ---: |
| `libpostal` | drop_ward | 241 | 0 | 7 | 234 |
| `libpostal` | drop_district | 99 | 0 | 10 | 89 |
| `libpostal` | drop_housenumber | 348 | 2 | 48 | 298 |
| `libpostal` | drop_housenumber_ward | 224 | 0 | 19 | 205 |
| `libpostal` | tất cả | 912 | 2 | 84 | 826 |
| `vietnamadminunits` | drop_ward | 241 | 5 | 19 | 217 |
| `vietnamadminunits` | drop_district | 99 | 2 | 7 | 90 |
| `vietnamadminunits` | drop_housenumber | 348 | 1 | 0 | 347 |
| `vietnamadminunits` | drop_housenumber_ward | 224 | 6 | 14 | 204 |
| `vietnamadminunits` | tất cả | 912 | 14 | 40 | 858 |

## 5. Data 07: chuyển đổi hành chính cũ → mới

Chỉ VietnamAdminUnits có API converter và chỉ hai trường `PhuongXa`, `TinhThanh` được chấm. Không có thử nghiệm chiều mới → cũ; API hiện tại không cung cấp tác vụ đó.

| Quan hệ | n | Đúng cặp đơn vị | Sai đích có output | Trả rỗng |
| --- | ---: | ---: | ---: | ---: |
| N-1 | 244 | 242 (99.2%) | 0 | 2 |
| M-N | 356 | 340 (95.5%) | 12 | 4 |

## 6. Mẫu lỗi truy vết

Các dòng sau lấy trực tiếp từ CSV dự đoán; `ID` dùng để tra raw response cùng khóa ID/công cụ.

| ID | Công cụ | Input | Dự đoán | Đáp án |
| --- | --- | --- | --- | --- |
| D01_0000 | libpostal | 394, Đường Lý Thường Kiệt, Phường Phù Khê, Tỉnh Bắc Ninh | {"SoNha": "394", "TenDuong": "đường lý thường kiệt", "PhuongXa": "", "QuanHuyen": "phường phù", "TinhThanh": "tỉnh bắc ninh"} | {"SoNha": "394", "TenDuong": "Đường Lý Thường Kiệt", "PhuongXa": "Phường Phù Khê", "QuanHuyen": "", "TinhThanh": "Tỉnh Bắc Ninh"} |
| D03_0000 | vietnamadminunits | NT02-29, Ngọc Trai 2, Đa Tốn, Gia Lâm, Hà Nội | {"SoNha": "", "TenDuong": "Nt02 - 29, Ngọc Trai 2", "PhuongXa": "Xã Đa Tốn", "QuanHuyen": "Huyện Gia Lâm", "TinhThanh": "Thành phố Hà Nội"} | {"SoNha": "NT02-29", "TenDuong": "Ngọc Trai 2", "PhuongXa": "Đa Tốn", "QuanHuyen": "Gia Lâm", "TinhThanh": "Hà Nội"} |
| D04_0000 | vietnamadminunits | 9, Ngách 1/88 Phạm Tuấn Tài, Phường Dịch Vọng Hậu, Hà Nội | {"SoNha": "", "TenDuong": "9", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "Thành phố Hà Nội"} | {"SoNha": "9", "TenDuong": "Ngách 1/88 Phạm Tuấn Tài", "PhuongXa": "Phường Dịch Vọng Hậu", "QuanHuyen": "", "TinhThanh": "Hà Nội"} |
| D06_0000_m25 | vietnamadminunits | 6, Ngõ 42 Phố Trần Bình Trọng, Phường Phương Liễu, Thị xã Quế Võ, Bắc Ninh | {"SoNha": "6", "TenDuong": "Ngõ 42 Phố Trần Bình Trọng, Phường Phương Liễu", "PhuongXa": "Phường Quế Võ", "QuanHuyen": "", "TinhThanh": "Tỉnh Bắc Ninh"} | {"SoNha": "6", "TenDuong": "Ngõ 42 Phố Trần Bình Trọng", "PhuongXa": "Phường Phương Liễu", "QuanHuyen": "Thị xã Quế Võ", "TinhThanh": "Bắc Ninh"} |
| D07_0000_M-N | vietnamadminunits | 11, Phố Khúc Hạo, Phường Điện Biên, Quận Ba Đình, Hà Nội | {"PhuongXa": "", "TinhThanh": ""} | {"PhuongXa": "Phường Ba Đình", "TinhThanh": "Thành phố Hà Nội"} |

## 7. Giới hạn

- Điểm VietnamAdminUnits ở Data 01/02/03/04 có oracle mode, chưa đo T1. Data 06 không đo khả năng cảnh báo địa chỉ lai vì API không trả nhãn cảnh báo.
- T0 theo 11 nhãn span chưa thể đo vì bộ hiện tại chỉ có ground truth 5 trường địa chỉ.
- Data 02 là nhiễu tổng hợp; các loại nhiễu đồng xuất hiện và không chứng minh độ bền trên hóa đơn thật.
- Các trường OSM là nhãn cộng đồng; Data 03 hiện đã được chuẩn hóa và lọc sạch hoàn toàn 100% đủ cả 5 trường (không còn dòng thiếu tự nhiên). Data 04 được sinh có kiểm soát từ các địa chỉ sạch, giữ nguyên ground truth trước khi xóa.
- Data 07 dựa trên OSM diff quan sát được và bảng hành chính; cần đọc coverage trước khi ngoại suy. Converter có thể gọi ArcGIS geocoder qua mạng, nên lần chạy sau cần ghi nhận điều kiện dịch vụ khi so sánh kết quả.
