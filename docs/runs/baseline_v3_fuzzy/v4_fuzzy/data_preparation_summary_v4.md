# Tóm tắt chuẩn bị dữ liệu và hợp đồng benchmark (v4)

- **Phiên bản tài liệu:** v4 fuzzy/uncertainty draft (sinh tự động)
- **Run nguồn:** `baseline_v3_fuzzy`
- **Manifest SHA-256:** `14da842d270d2b0e2a31efd954c07d3a0f948cc7b3d7c8240687ae7a19a46fcb`
- **Dòng benchmark:** 5500; **lượt dự đoán:** 13000.
- **Trạng thái:** draft có truy vết artifact; không thay thế báo cáo baseline v1 frozen.

## 1. Nguồn và snapshot OSM

Pipeline đọc `data/raw/osm/vietnam-internal.osh.pbf` bằng `pyosmium`, tách snapshot bằng mốc thời gian `2025-06-30T23:59:59Z`. Đây là lượt quét full-history trong code, không phải artifact từ lệnh CLI `osmium time-filter`. OSM full-history lưu nhiều revision của cùng đối tượng, phù hợp để kiểm tra thay đổi theo thời điểm [R6]. Snapshot hiện lưu 26.961 đối tượng: 15.749 node và 11.212 way; 6.008/15.749 node có đủ năm trường địa chỉ.

## 2. Mục đích từng tập

| Tập | Số dòng | Vai trò kiểm chứng | Hợp đồng chính |
| --- | ---: | --- | --- |
| Data 01 | 1.000 | Parse địa chỉ mới sạch | Cấu trúc hai cấp, `QuanHuyen` rỗng theo schema. |
| Data 02 | 1.000 | Độ bền trước phép biến đổi tổng hợp | Giữ `ChuoiDiaChiGoc`, `GT_*`, loại/mức nhiễu, seed. |
| Data 03 | 1.500 | Mốc parse hệ cũ sạch | Đủ cả năm trường bề mặt; không có thiếu tự nhiên. |
| Data 04 | 800 | Tách extraction và recovery khi thiếu trường | Sinh từ địa chỉ sạch; chỉ xóa theo `KieuThieu`; giữ `GT_*`. |
| Data 06 | 600 | Xung đột hệ quy chiếu trong cùng chuỗi | Chỉ dùng cạnh có một đích xác minh. |
| Data 07 | 600 | Conversion hành chính cũ → mới | Cặp OSM diff quan sát trực tiếp, chấm phường/xã và tỉnh/thành. |

## 3. Hợp đồng Data 03 và Data 04

Data 03 là mốc sạch đầy đủ trường của hệ cũ. Data 04 bắt đầu từ địa chỉ sạch cùng schema, sau đó xóa đúng trường quy định; `GT_*` giữ đáp án trước xóa. Điểm parse chính dùng trường còn hiện diện trên surface; phân tích recovery phải tách riêng, không dùng `GT_*` để tính extraction score.

## 4. Địa chỉ lai và conversion

| KieuLai | n | PhuongXa_he | QuanHuyen_he | TinhThanh_he | all_surface_district_present |
| --- | --- | --- | --- | --- | --- |
| C1 | 420 | moi | cu | cu | True |
| C2 | 120 | moi | cu | moi | True |
| C3 | 60 | cu | cu | moi | True |

| QuanHe | n | direction_evaluated | scored_fields |
| --- | --- | --- | --- |
| M-N | 356 | old_to_new | PhuongXa,TinhThanh |
| N-1 | 244 | old_to_new | PhuongXa,TinhThanh |

Các cạnh 1-N và M-N không được dựng từ snapshot khi thiếu bằng chứng hình học/toạ độ. Data 07 là quan sát trực tiếp nên có thể chứa M-N; phạm vi hiện tại không đại diện cho mọi vùng hoặc quan hệ hành chính.

## Tài liệu tham khảo

1. **[R1]** Quốc hội. *Nghị quyết số 202/2025/QH15 về sắp xếp đơn vị hành chính cấp tỉnh*. [Cổng Thông tin điện tử Chính phủ](https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-quyet-so-202-2025-qh15-ve-sap-xep-don-vi-hanh-chinh-cap-tinh-119250612174148722.htm).
2. **[R2]** Ủy ban Thường vụ Quốc hội. *Nghị quyết số 76/2025/UBTVQH15 về sắp xếp đơn vị hành chính năm 2025*. [Cổng Thông tin điện tử Chính phủ](https://xaydungchinhsach.chinhphu.vn/nghi-quyet-so-76-2025-ubtvqh15-sap-xep-don-vi-hanh-chinh-nam-2025-119250415130519882.htm).
3. **[R3]** Lafferty, J., McCallum, A., & Pereira, F. (2001). *Conditional Random Fields: Probabilistic Models for Segmenting and Labeling Sequence Data*. [PDF](https://www.cs.columbia.edu/~jebara/6772/papers/crf.pdf).
4. **[R4]** Nguyen, D. Q. & Nguyen, A. T. (2020). *PhoBERT: Pre-trained language models for Vietnamese*. Findings of EMNLP. [ACL Anthology](https://aclanthology.org/2020.findings-emnlp.92/).
5. **[R5]** OpenVenues. *libpostal: international street address NLP*. [Repository và tài liệu kỹ thuật](https://github.com/openvenues/libpostal).
6. **[R6]** OpenStreetMap Wiki. *Planet.osm/full and full-history data*. [Documentation](https://wiki.openstreetmap.org/wiki/Planet_History).
7. **[R7]** Dự án DACN. `data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv`, bảng ánh xạ hành chính được version/hash trong manifest của run.
