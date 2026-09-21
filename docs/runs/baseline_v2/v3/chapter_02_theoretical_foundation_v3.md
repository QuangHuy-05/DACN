# Chương 2. Cơ sở lý thuyết và phương pháp đánh giá (v3)

- **Phiên bản tài liệu:** v3 draft (sinh tự động)
- **Run nguồn:** `baseline_v2`
- **Manifest SHA-256:** `f870c0bc4d0317c45008a792a6be0f220e23818f2e0e738f972d1b25ffc9c7bf`
- **Dòng benchmark:** 5500; **lượt dự đoán:** 13000.
- **Trạng thái:** draft có truy vết artifact; không thay thế báo cáo baseline v1 frozen.

## 2.1. Trích xuất cấu trúc địa chỉ

T0 được phát biểu như gán nhãn chuỗi với 11 nhãn span: `SoNha`, `TenDuong`, `Ngo/Hem`, `ToaNha/CanHo`, `PhuongXa`, `QuanHuyen`, `TinhThanh`, `MocDinhVi`, `HuongDi`, `GhiChu`, `Khac`. Conditional Random Fields là khung phân biệt cho phân đoạn và gán nhãn chuỗi [R3]. Với tiếng Việt, PhoBERT là encoder đơn ngữ đã được đánh giá trên các tác vụ như POS, parsing và NER [R4]; đây là cơ sở để thử nghiệm encoder ngữ cảnh kết hợp đầu ra span, không phải bằng chứng rằng mô hình đã được huấn luyện trong repository này.

## 2.2. Đồ thị hành chính đa thời điểm

Biểu diễn mỗi đơn vị theo khóa `(tỉnh, quận/huyện, phường/xã, thời điểm)` và mỗi chuyển đổi là một cạnh đến đơn vị mới. Bậc vào/ra tạo các quan hệ 1-1, 1-N, N-1 và M-N. N-1 có một đích khi đi cũ → mới; 1-N và M-N cần bằng chứng không gian hoặc cơ chế abstention nếu địa chỉ không đủ định vị. Bảng nguồn [R7] là căn cứ duy nhất để tạo cạnh; tên đơn lẻ không đủ làm khóa ánh xạ.

## 2.3. Hai baseline trong phạm vi nghiên cứu

Libpostal là thư viện C dùng statistical NLP và dữ liệu địa lý mở để parse/normalize địa chỉ [R5]. VietnamAdminUnits là package được kiểm thử ở version đã ghi trong manifest. Phép so sánh trong repository là so sánh **adapter + phiên bản tool + protocol**, không suy rộng thành xếp hạng tuyệt đối của hai hệ thống ngoài điều kiện run.

## 2.4. Giao thức chấm điểm

Với mỗi trường được chấm, so sánh sau chuẩn hóa tạo TP, TN, FP, FN hoặc MISMATCH; MISMATCH đóng góp một FP và một FN. Exact match yêu cầu toàn bộ trường được chấm khớp. Hai chỉ số tổng hợp được ghi riêng:

$$F1_{micro} = \frac{2TP}{2TP + FP + FN}$$

$$F1_{macro} = \frac{1}{|F|} \sum_{f \in F} F1_f$$

Data 07 chỉ có `PhuongXa`, `TinhThanh` trong tập trường chấm và direction `old_to_new`. Tỷ lệ exact/micro/macro của từng điều kiện được ghi trong artifact sau, không thay bằng một nhãn F1 chung:

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

## 2.5. Thiết kế đề xuất

Giai đoạn 1 nhận chuỗi thô, chuẩn hóa có dấu vết và dự đoán span cùng hệ quy chiếu. Giai đoạn 2 tra đồ thị hành chính theo thời điểm. Nếu cạnh có một đích đã xác minh thì trả kết quả; nếu nhiều đích thì dùng toạ độ/bằng chứng biên giới hoặc trả trạng thái bất định. Cơ chế abstention giảm rủi ro gán một đích không có căn cứ, nhưng cần được đánh giá thực nghiệm bằng task riêng.

## 2.6. Tái lập và giới hạn

OSM full-history giữ nhiều revision của đối tượng [R6], nhưng tag OSM là nhãn cộng đồng. Data 02 là tổng hợp; Data 03/04 có hợp đồng rõ; Data 06/07 không bao phủ toàn bộ quan hệ. Run mới ghi trace converter để phân biệt fallback/geocoder từ quan sát trực tiếp. Các giới hạn này là một phần của phương pháp, không được che bằng điểm aggregate.

## Tài liệu tham khảo

1. **[R1]** Quốc hội. *Nghị quyết số 202/2025/QH15 về sắp xếp đơn vị hành chính cấp tỉnh*. [Cổng Thông tin điện tử Chính phủ](https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-quyet-so-202-2025-qh15-ve-sap-xep-don-vi-hanh-chinh-cap-tinh-119250612174148722.htm).
2. **[R2]** Ủy ban Thường vụ Quốc hội. *Nghị quyết số 76/2025/UBTVQH15 về sắp xếp đơn vị hành chính năm 2025*. [Cổng Thông tin điện tử Chính phủ](https://xaydungchinhsach.chinhphu.vn/nghi-quyet-so-76-2025-ubtvqh15-sap-xep-don-vi-hanh-chinh-nam-2025-119250415130519882.htm).
3. **[R3]** Lafferty, J., McCallum, A., & Pereira, F. (2001). *Conditional Random Fields: Probabilistic Models for Segmenting and Labeling Sequence Data*. [PDF](https://www.cs.columbia.edu/~jebara/6772/papers/crf.pdf).
4. **[R4]** Nguyen, D. Q. & Nguyen, A. T. (2020). *PhoBERT: Pre-trained language models for Vietnamese*. Findings of EMNLP. [ACL Anthology](https://aclanthology.org/2020.findings-emnlp.92/).
5. **[R5]** OpenVenues. *libpostal: international street address NLP*. [Repository và tài liệu kỹ thuật](https://github.com/openvenues/libpostal).
6. **[R6]** OpenStreetMap Wiki. *Planet.osm/full and full-history data*. [Documentation](https://wiki.openstreetmap.org/wiki/Planet_History).
7. **[R7]** Dự án DACN. `data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv`, bảng ánh xạ hành chính được version/hash trong manifest của run.

