# Chương 1. Động lực nghiên cứu và phát biểu bài toán (v3)

- **Phiên bản tài liệu:** v3 draft (sinh tự động)
- **Run nguồn:** `baseline_v1`
- **Manifest SHA-256:** `0f63399b6c5344d6015277c07236267c71127a73bd1588efd4b326f100c223e1`
- **Dòng benchmark:** 5500; **lượt dự đoán:** 13000.
- **Trạng thái:** draft có truy vết artifact; không thay thế báo cáo baseline v1 frozen.

## 1.1. Bối cảnh

Việc sắp xếp đơn vị hành chính năm 2025 tạo ra hai hệ tham chiếu cho cùng một địa chỉ: hệ cũ có tỉnh/thành, quận/huyện, phường/xã; hệ mới trong benchmark dùng tỉnh/thành và phường/xã. Nghị quyết về sắp xếp cấp tỉnh năm 2025 được công bố theo Nghị quyết 202/2025/QH15 [R1]; khung sắp xếp đơn vị hành chính năm 2025 được nêu trong Nghị quyết 76/2025/UBTVQH15 [R2]. Bài toán kỹ thuật là bảo toàn nghĩa địa chỉ khi chuỗi có thể dùng hệ cũ, hệ mới hoặc trộn cả hai.

## 1.2. Vấn đề nghiên cứu

Đề tài tách bốn nhóm nhiệm vụ: T0 tách span theo schema 11 nhãn; T1 nhận diện hệ quy chiếu `cu/moi/Lai`; T2 ánh xạ đơn vị hành chính theo thời điểm; T3 đối sánh hai địa chỉ theo thời gian. Baseline hiện mới chấm năm trường chuẩn hóa và conversion old-to-new trên Data 07. Vì vậy, số baseline không được trình bày như kết quả hoàn tất T0, T1 hoặc T3.

## 1.3. Bằng chứng thực nghiệm hiện có

Run `baseline_v1` gồm 13000 lượt dự đoán từ 5500 dòng benchmark. Bảng sau chỉ ra các điều kiện đã thực thi; tên metric và mẫu số được giữ nguyên để tránh so sánh sai.

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
| Data 07\|old_to_new | vietnamadminunits | PhuongXa,TinhThanh | 600 | 586 | 0.976667 | 0.989158 | 0.989149 |

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

Chưa có Data 05 dựa trên mốc, nhãn T0 đủ 11 span, T1 tự động, task B/new-to-old hoặc T3. Độ phủ Data 07 tập trung N-1/M-N và có thiên lệch vùng, nên không suy rộng sang 1-1/1-N hoặc toàn quốc. Các case thực nghiệm nằm trong `baseline_ambiguity_evidence_v3.md` cùng run và được truy vết bằng ID/raw log.

## Tài liệu tham khảo

1. **[R1]** Quốc hội. *Nghị quyết số 202/2025/QH15 về sắp xếp đơn vị hành chính cấp tỉnh*. [Cổng Thông tin điện tử Chính phủ](https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-quyet-so-202-2025-qh15-ve-sap-xep-don-vi-hanh-chinh-cap-tinh-119250612174148722.htm).
2. **[R2]** Ủy ban Thường vụ Quốc hội. *Nghị quyết số 76/2025/UBTVQH15 về sắp xếp đơn vị hành chính năm 2025*. [Cổng Thông tin điện tử Chính phủ](https://xaydungchinhsach.chinhphu.vn/nghi-quyet-so-76-2025-ubtvqh15-sap-xep-don-vi-hanh-chinh-nam-2025-119250415130519882.htm).
3. **[R3]** Lafferty, J., McCallum, A., & Pereira, F. (2001). *Conditional Random Fields: Probabilistic Models for Segmenting and Labeling Sequence Data*. [PDF](https://www.cs.columbia.edu/~jebara/6772/papers/crf.pdf).
4. **[R4]** Nguyen, D. Q. & Nguyen, A. T. (2020). *PhoBERT: Pre-trained language models for Vietnamese*. Findings of EMNLP. [ACL Anthology](https://aclanthology.org/2020.findings-emnlp.92/).
5. **[R5]** OpenVenues. *libpostal: international street address NLP*. [Repository và tài liệu kỹ thuật](https://github.com/openvenues/libpostal).
6. **[R6]** OpenStreetMap Wiki. *Planet.osm/full and full-history data*. [Documentation](https://wiki.openstreetmap.org/wiki/Planet_History).
7. **[R7]** Dự án DACN. `data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv`, bảng ánh xạ hành chính được version/hash trong manifest của run.

