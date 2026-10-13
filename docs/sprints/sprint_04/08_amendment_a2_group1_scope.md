# Amendment A2 — Phạm vi Nhóm 1 (lấp khoảng trống khoa học)

**Ngày:** 13/10/2026. **Trạng thái: ĐÃ DUYỆT — chủ dự án duyệt cả năm điểm ngày 13/10/2026.**
**Bản chất:** bổ sung cho `s4-protocol-v1`, không sửa [02_s4_protocol_v1.md](02_s4_protocol_v1.md). Amendment A1 (bước 1) giữ nguyên hiệu lực.
**Nguồn nội dung:** mục 2 của [06_group1_science_gap_plan.md](06_group1_science_gap_plan.md).

## Lý do

Protocol `s4-protocol-v1` ghi T2 ngoài phạm vi và không dùng lại test Sprint 3 để phát triển. Kế hoạch Nhóm 1 cần (i) một baseline T2, (ii) báo cáo độ bất định trên prediction đã freeze, (iii) chạy lại đa seed và (iv) vài biến thể mô hình mới. Các việc này cần quy tắc rõ ràng về việc test Sprint 3 được dùng thế nào.

## Năm điểm được duyệt

1. Đưa **T2 baseline** vào phạm vi: tra bảng hai chiều trên Data 07 và phân tích đồ thị cạnh. Chỉ đọc gazetteer; không sửa, không phát hành lại gazetteer.
2. Cho phép **phân tích thống kê hậu nghiệm** (bootstrap, kiểm định ghép cặp) trên prediction test Sprint 3 đã freeze. Đây là báo cáo độ bất định, không phải phát triển mô hình.
3. Cho phép **huấn luyện lại đa seed** (1337, 2025) với cấu hình c02 đã khóa và chấm test Sprint 3 đúng một lần mỗi seed. Báo mọi seed; không chọn seed, checkpoint, ngưỡng bằng test.
4. Biến thể mô hình mới (đầu T1 có dữ liệu lai tổng hợp, CRF huấn luyện kèm thiếu trường) được chọn **chỉ bằng dev / dev tổng hợp tách nhóm**; kết quả trên test Sprint 3 ghi nhãn `POST_HOC_SECONDARY` vì test đã bị quan sát ở Sprint 3.
5. Mọi tập sinh tổng hợp dùng để huấn luyện/đánh giá thuộc **stress track**, báo riêng, không bù support quan sát.

## Việc chủ dự án tự làm (không thuộc phạm vi agent)

- Đọc quota GPU trên giao diện Kaggle trước khi chạy huấn luyện đa seed (WP3b).
- Xác nhận cho phép upload gói train/dev tổng hợp lên dataset Kaggle **private** (Data 06/04 dẫn xuất từ OSM và CSV hành chính, cùng họ nguồn đã upload ở Sprint 3). Upload/submit Kaggle chỉ làm sau khi có xác nhận này trong phiên.

## Điều không thay đổi

Không mở lại nhãn, không đổi split, không tune trên test, không sửa/xóa raw, gold, split, gazetteer, checkpoint, prediction và evidence có hash. Suy luận chỉ nhận văn bản; metadata và `GT_*` chỉ dùng ở phía chấm điểm. Mỗi run có đúng một `run_manifest.json`; kết quả âm và `NOT_EVALUABLE` là đầu ra hợp lệ.

## Công cụ dùng chung ràng buộc bởi Amendment này

- `src/evaluation/leak_guard.py`: loại benchmark trùng train/dev/test theo chuỗi chuẩn hóa; khóa nhóm hành chính để chia nhóm rời nhau. Báo cáo tại `data/interim/modeling/sprint04/group1_guards_20261013_v1/exclusion_report.json`.
- `src/evaluation/stats.py`: bootstrap theo mẫu/cụm, bootstrap ghép cặp, hoán vị ngẫu nhiên xấp xỉ, McNemar chính xác.
