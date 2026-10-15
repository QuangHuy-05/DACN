# Amendment A3 — Dời lịch Sprint 4 sang tuần 9–12 (G2-0)

**Ngày soạn:** 15/10/2026. **Trạng thái: ĐÃ DUYỆT — chủ dự án duyệt ngày 15/10/2026 (xác nhận trong phiên điều phối).**
**Bản chất:** bổ sung cho `s4-protocol-v1`, không sửa [02_s4_protocol_v1.md](02_s4_protocol_v1.md). Amendment A1 ([04](04_step1_decision_and_protocol_amendment.md) §6) và A2 ([08](08_amendment_a2_group1_scope.md)) giữ hiệu lực, trừ hai điểm ngày tháng của A1 được thay ở mục 2.
**Nguồn nội dung:** [15_group2_group3_plan.md](15_group2_group3_plan.md) mục 1 và 4.

## 1. Lý do

Lịch của protocol (06–20/10/2026, hạn cứng 20/10) giả định bắt đầu gán từ 09/10. Đến 15/10 chưa gán mẫu nào (pilot hiệu lực 19 mẫu, không có `annotation_import.json` hay `timing_log.csv` có dữ liệu). Thời gian này được dùng cho Nhóm 1 (khoa học), hoàn tất 15/10. Mốc 18–20/10 không còn ràng buộc thực tế; A1 điểm 2 khi đó sẽ buộc `intra_annotator = NOT_MEASURED_BY_2026-10-18` mà không có lý do khoa học. Dời lịch cho phép đo intra-annotator đúng theo protocol (≥ 168 giờ giữa hai vòng) thay vì bỏ.

## 2. Điều thay đổi (chỉ ngày tháng và thứ tự)

| Mục | Protocol / A1 | A3 |
|---|---|---|
| Hạn đóng dữ liệu Sprint 4 | 18/10 mục tiêu, 20/10 hạn cứng (A1 §6 điểm 1) | **16/11/2026** mục tiêu đóng dữ liệu Nhóm 2; 23/11 hạn cứng cho phần cắt được (G2-7, G2-8) |
| Intra-annotator | `NOT_MEASURED_BY_2026-10-18` nếu thiếu vòng 1 đúng hạn (A1 §6 điểm 2) | Đo theo protocol §6; `NOT_MEASURED` chỉ khi vòng 2 chưa đủ 168 giờ hoặc không thực hiện, kèm lý do |
| Quyết định cổng holdout | trước 09/10 (protocol §5) | **16/11/2026**, sau QA track; **không** cam kết trước khi gán |
| Pilot | 09–10/10 | **27/10–2/11** (G2-3, chủ dự án gán) |
| Tập gán lặp vòng 1 | 09–10/10 | **từ 3/11, sau khi guideline S4 khóa** (xem điểm 3 mục 3) |
| Tập gán lặp vòng 2 | từ 17/10 | **từ 10/11**, mỗi mẫu ≥ 7×24 giờ sau dấu thời gian vòng 1 của chính nó |
| Thu và gán track địa chỉ cơ quan (G2-4) | 11–16/10 | thu mẫu 3–9/11; QA và chạy hệ 10–16/11 |

Lịch tuần: tuần 9 (20–26/10) A3, tự kiểm nguồn (G2-1), trích TB243 (G2-2), kiểm khả năng dữ liệu (G2-6), chuẩn bị gói pilot; tuần 10 (27/10–2/11) pilot và chốt guideline; tuần 11 (3–9/11) vòng 1 gán lặp và thu mẫu track; tuần 12 (10–16/11) QA, chạy 5 hệ, vòng 2 gán lặp; tuần 13 phần cắt được. Nhóm 3 chạy song song từ tuần 9 và không phụ thuộc A3.

## 3. Ba điểm làm rõ (đều siết chặt, không nới cổng)

1. **Giữ nguyên mọi cổng của protocol:** 168 giờ giữa hai vòng; holdout cần ≥ 50 mẫu hợp lệ, ≥ 20 site group, ≥ 2 document group, quyền nguồn đủ, 0 overlap chưa xử lý; một người gán, IAA `NOT_MEASURED`; không chọn bằng test Sprint 3; mẫu tổng hợp không bù support quan sát.
2. **Track địa chỉ cơ quan hệ mới không phải holdout đại diện.** Nguồn (TB729 Hà Nội, TB243 TP.HCM) chỉ có địa chỉ hệ mới, nên mọi mẫu T1 là `moi`: T1 trên track là `NOT_EVALUABLE_SINGLE_CLASS`, không báo macro-F1; không có `QuanHuyen`, `HuongDi`, `MocDinhVi`, `GhiChu`. Track dùng để kiểm chuyển miền của T0 trên địa chỉ hành chính hệ mới. Chỉ gọi là holdout khi qua cổng ở điểm 1, và tên vẫn ghi "địa chỉ cơ quan".
3. **Vòng 1 gán lặp chỉ bắt đầu sau khi guideline S4 khóa** (kết thúc pilot). Nếu gán vòng 1 trước khi chốt ca khó rồi sửa guideline, bất đồng giữa hai vòng đo thay đổi guideline chứ không đo độ ổn định của người gán. Mẫu pilot (gán khi guideline còn mở) không đưa vào tập gán lặp. Tập gán lặp là 30 mẫu phân tầng lấy từ danh sách ứng viên G2-2/TB729 (công thức protocol §6: `min(N, 60, max(30, ceil(0,15 N)))` cho N ≤ 200 là 30); chọn và đóng băng danh sách bằng seed 42 trước khi gán.

## 4. Điều không thay đổi

Không sửa `s4-protocol-v1`, gold, split, raw, gazetteer, checkpoint, evidence có hash của Sprint 3. Quyền nguồn theo decision log v2 (04 §3): `hanoi_tb729` APPROVED; `qhkt_current` annotation APPROVED, cloud/redistribution PENDING; TB243 local/annotation APPROVED, cloud/redistribution PENDING; nguồn chưa APPROVED cho annotation bị loại (A1 điểm 3). Agent không tạo gold, không gợi ý nhãn trong vòng đo lặp, không tự phân xử, không tự duyệt quyền nguồn.

## 5. Hệ quả cần biết

- TB243 chưa được phép upload cloud, nên suy luận neural trên mẫu TB243 chỉ làm được local; local đang bị chặn bởi cổng ≥ 20 GiB trống của ổ D (còn khoảng 14,3 GiB đo ngày 15/10).
- Nếu mốc 16/11 không đạt: track báo `NOT_COMMITTED`, phần còn lại (pilot, gán lặp, số phút/mẫu) vẫn là đầu ra hợp lệ.

---

**Phê duyệt:** ĐÃ DUYỆT, 15/10/2026.
