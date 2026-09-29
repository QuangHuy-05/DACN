# Chương 2. Cơ sở lý thuyết và phương pháp đánh giá (v4)

- **Phiên bản tài liệu:** v4 fuzzy/uncertainty draft (sinh tự động)
- **Run nguồn:** `baseline_v3_fuzzy`
- **Manifest SHA-256:** `14da842d270d2b0e2a31efd954c07d3a0f948cc7b3d7c8240687ae7a19a46fcb`
- **Dòng benchmark:** 5500; **lượt dự đoán:** 13000.
- **Trạng thái:** draft có truy vết artifact; không thay thế báo cáo baseline v1 frozen.

## 2.1. Trích xuất cấu trúc địa chỉ

T0 được phát biểu như gán nhãn chuỗi với 11 nhãn span: `SoNha`, `TenDuong`, `Ngo/Hem`, `ToaNha/CanHo`, `PhuongXa`, `QuanHuyen`, `TinhThanh`, `MocDinhVi`, `HuongDi`, `GhiChu`, `Khac`. Conditional Random Fields là khung phân biệt cho phân đoạn và gán nhãn chuỗi [R3]. Với tiếng Việt, PhoBERT là encoder đơn ngữ đã được đánh giá trên các tác vụ như POS, parsing và NER [R4]; đây là cơ sở để thử nghiệm encoder ngữ cảnh kết hợp đầu ra span, không phải bằng chứng rằng mô hình đã được huấn luyện trong repository này.

## 2.2. Đồ thị hành chính đa thời điểm

Biểu diễn mỗi đơn vị theo khóa `(tỉnh, quận/huyện, phường/xã, thời điểm)` và mỗi chuyển đổi là một cạnh đến đơn vị mới. Bậc vào/ra tạo các quan hệ 1-1, 1-N, N-1 và M-N. N-1 có một đích khi đi cũ → mới; 1-N và M-N cần bằng chứng không gian hoặc cơ chế abstention nếu địa chỉ không đủ định vị. Bảng nguồn [R7] là căn cứ duy nhất để tạo cạnh; tên đơn lẻ không đủ làm khóa ánh xạ.

## 2.3. Hai baseline trong phạm vi nghiên cứu

Libpostal là thư viện C dùng statistical NLP và dữ liệu địa lý mở để parse/normalize địa chỉ [R5]. VietnamAdminUnits là package được kiểm thử ở version đã ghi trong manifest. Phép so sánh trong repository là so sánh **adapter + phiên bản tool + protocol**, không suy rộng thành xếp hạng tuyệt đối của hai hệ thống ngoài điều kiện run.

## 2.4. Giao thức chấm điểm

Với mỗi trường được chấm, so sánh strict sau chuẩn hóa tạo TP, TN, FP, FN hoặc MISMATCH; MISMATCH đóng góp một FP và một FN. Exact match yêu cầu toàn bộ trường được chấm khớp. Báo cáo fuzzy dùng normalized Levenshtein similarity, bằng 1 trừ khoảng cách Levenshtein chia cho độ dài lớn hơn của hai chuỗi chuẩn hóa. Chuẩn hóa dùng NFC, casefold và gộp khoảng trắng; giữ dấu tiếng Việt và tiền tố loại đơn vị hành chính. So sánh chỉ trong cùng trường. Cặp rỗng-rỗng bị loại khỏi fuzzy denominator; một vế rỗng có điểm 0. Mọi bảng trường ghi numerator và denominator.

Điểm fuzzy là mức gần bề mặt chuỗi. Với đích hành chính, một tên gần giống không được tính là đúng đơn vị; exact target match vẫn là tiêu chí nhận diện thực thể.

$$F1_{micro} = \frac{2TP}{2TP + FP + FN}$$

$$F1_{macro} = \frac{1}{|F|} \sum_{f \in F} F1_f$$

Data 07 chỉ có `PhuongXa`, `TinhThanh` trong tập trường chấm và direction `old_to_new`. Truth phường/xã và tỉnh/thành được tra từ `MaPhuongXaMoi` qua bảng mapping. Tỷ lệ exact, fuzzy và F1 của từng điều kiện được ghi riêng:

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

## 2.5. Thiết kế đề xuất

Giai đoạn 1 nhận chuỗi thô, chuẩn hóa có dấu vết và dự đoán span cùng hệ quy chiếu. Giai đoạn 2 tra đồ thị hành chính theo thời điểm. Nếu cạnh có một đích đã xác minh thì trả kết quả; nếu nhiều đích thì dùng toạ độ/bằng chứng biên giới hoặc trả trạng thái bất định. Cơ chế abstention giảm rủi ro gán một đích không có căn cứ, nhưng cần được đánh giá thực nghiệm bằng task riêng.

Phân tích hiện tại tách tình huống cấu trúc (nhóm `KieuThieu`, `KieuLai`) khỏi trace converter phục vụ lựa chọn đích. Đây là strata/chỉ báo chẩn đoán, không phải xác suất uncertainty. Chưa có nhãn bất định thủ công, xác suất dự đoán hoặc hình học biên giới đủ để tính calibration hay độ gần ranh giới.

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
