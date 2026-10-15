# Chương 1. Động lực nghiên cứu và phát biểu bài toán (v4)

- **Phiên bản tài liệu:** v4 fuzzy/uncertainty draft (sinh tự động)
- **Run nguồn:** `baseline_v3_fuzzy`
- **Manifest SHA-256:** `14da842d270d2b0e2a31efd954c07d3a0f948cc7b3d7c8240687ae7a19a46fcb`
- **Dòng benchmark:** 5500; **lượt dự đoán:** 13000.
- **Trạng thái:** draft có truy vết artifact; không thay thế báo cáo baseline v1 frozen.

## 1.1. Bối cảnh

Việc sắp xếp đơn vị hành chính năm 2025 tạo ra hai hệ tham chiếu cho cùng một địa chỉ: hệ cũ có tỉnh/thành, quận/huyện, phường/xã; hệ mới trong benchmark dùng tỉnh/thành và phường/xã. Nghị quyết về sắp xếp cấp tỉnh năm 2025 được công bố theo Nghị quyết 202/2025/QH15 [R1]; khung sắp xếp đơn vị hành chính năm 2025 được nêu trong Nghị quyết 76/2025/UBTVQH15 [R2]. Bài toán kỹ thuật là bảo toàn nghĩa địa chỉ khi chuỗi có thể dùng hệ cũ, hệ mới hoặc trộn cả hai.

## 1.2. Vấn đề nghiên cứu

Đề tài tách bốn nhóm nhiệm vụ: T0 tách span theo schema 11 nhãn; T1 nhận diện hệ quy chiếu `cu/moi/Lai`; T2 ánh xạ đơn vị hành chính theo thời điểm; T3 đối sánh hai địa chỉ theo thời gian. Baseline hiện mới chấm năm trường chuẩn hóa và conversion old-to-new trên Data 07. Vì vậy, số baseline không được trình bày như kết quả hoàn tất T0, T1 hoặc T3.

## 1.3. Bằng chứng thực nghiệm hiện có

Run `baseline_v3_fuzzy` gồm 13000 lượt dự đoán từ 5500 dòng benchmark. Bảng sau chỉ ra các điều kiện đã thực thi; tên metric và mẫu số được giữ nguyên để tránh so sánh sai.

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

Data 02 cho phép so sánh cùng ground truth giữa chuỗi sạch và chuỗi nhiễu tổng hợp. Data 06 mô hình hóa địa chỉ lai theo ba hợp đồng dưới đây, thay vì giả định thiếu quận/huyện:

| KieuLai | n | PhuongXa_he | QuanHuyen_he | TinhThanh_he | all_surface_district_present |
| --- | --- | --- | --- | --- | --- |
| C1 | 420 | moi | cu | cu | True |
| C2 | 120 | moi | cu | moi | True |
| C3 | 60 | cu | cu | moi | True |

Data 07 chỉ có quan hệ N-1/M-N trong sample hiện tại:

| QuanHe | n | direction_evaluated | scored_fields |
| --- | --- | --- | --- |
| M-N | 356 | old_to_new | PhuongXa,TinhThanh |
| N-1 | 244 | old_to_new | PhuongXa,TinhThanh |

## 1.4. Câu hỏi nghiên cứu

1. Một mô hình trích xuất theo ngữ cảnh có cải thiện span địa chỉ tiếng Việt trước nhiễu và viết tắt không?
2. Có thể phân loại hệ quy chiếu trước khi parsing để tránh ép địa chỉ lai vào một mode cố định không?
3. Khi ánh xạ có nhiều đích, cơ chế nào nên trả kết quả, yêu cầu thêm bằng chứng hoặc từ chối dự đoán?
4. Độ phủ theo quan hệ, vùng và nguồn có làm thay đổi cách diễn giải kết quả không?

## 1.5. Phạm vi và tiêu chí không suy rộng

Chưa có Data 05 dựa trên mốc, nhãn T0 đủ 11 span, T1 tự động, task B/new-to-old hoặc T3. Độ phủ Data 07 tập trung N-1/M-N và có thiên lệch vùng, nên không suy rộng sang 1-1/1-N hoặc toàn quốc. Các case thực nghiệm nằm trong `baseline_diagnostics_v4.md` cùng run và được truy vết bằng ID/raw log.

## Tài liệu tham khảo

1. **[R1]** Quốc hội. *Nghị quyết số 202/2025/QH15 về sắp xếp đơn vị hành chính cấp tỉnh*. [Cổng Thông tin điện tử Chính phủ](https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-quyet-so-202-2025-qh15-ve-sap-xep-don-vi-hanh-chinh-cap-tinh-119250612174148722.htm).
2. **[R2]** Ủy ban Thường vụ Quốc hội. *Nghị quyết số 76/2025/UBTVQH15 về sắp xếp đơn vị hành chính năm 2025*. [Cổng Thông tin điện tử Chính phủ](https://xaydungchinhsach.chinhphu.vn/nghi-quyet-so-76-2025-ubtvqh15-sap-xep-don-vi-hanh-chinh-nam-2025-119250415130519882.htm).
3. **[R3]** Lafferty, J., McCallum, A., & Pereira, F. (2001). *Conditional Random Fields: Probabilistic Models for Segmenting and Labeling Sequence Data*. [PDF](https://www.cs.columbia.edu/~jebara/6772/papers/crf.pdf).
4. **[R4]** Nguyen, D. Q. & Nguyen, A. T. (2020). *PhoBERT: Pre-trained language models for Vietnamese*. Findings of EMNLP. [ACL Anthology](https://aclanthology.org/2020.findings-emnlp.92/).
5. **[R5]** OpenVenues. *libpostal: international street address NLP*. [Repository và tài liệu kỹ thuật](https://github.com/openvenues/libpostal).
6. **[R6]** OpenStreetMap Wiki. *Planet.osm/full and full-history data*. [Documentation](https://wiki.openstreetmap.org/wiki/Planet_History).
7. **[R7]** Dự án DACN. `data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv`, bảng ánh xạ hành chính được version/hash trong manifest của run.
