# Sprint 4

**Hiện hành — 06/10/2026:** đã hiện thực nhiệm vụ 1 với một chủ dự án phụ trách toàn bộ, nguồn mới ưu tiên, holdout có điều kiện, Kaggle và hạn 20/10/2026. Dữ liệu mới/gán nhãn/thực nghiệm chưa thực hiện.

Đọc [Protocol Sprint 4 v1](02_s4_protocol_v1.md) trước triển khai. IAA giữa hai người là `NOT_MEASURED`; kế hoạch kiểm tra thay thế là gán lặp thủ công của cùng người sau ít nhất 7 ngày, báo **intra-annotator** riêng.

## Mục tiêu

Tăng độ tin cậy của benchmark T0/T1 và xác định mức ổn định của các mô hình đã có kết quả trong Sprint 3. Sprint 4 giữ nguyên các release và kết quả Sprint 3 đã khóa; dữ liệu mới (nếu được thu thập và duyệt) phải phát hành thành phiên bản mới.

## Tài liệu chính

- [Protocol Sprint 4 v1](02_s4_protocol_v1.md) — quyết định hiện hành, support, source register, gán lặp, split/holdout, Kaggle, lịch và nghiệm thu.
- [Cấu hình protocol](../../../configs/annotation/sprint04/protocol_v1.json) và [nguồn ứng viên](../../../configs/annotation/sprint04/source_register_v1.csv).
- [Snapshot Sprint 3 trước/sau nhiệm vụ 1](../../../data/interim/annotation/sprint04/protocol_v1/baseline_snapshot.json) — phạm vi hash được ghi rõ; raw kiểm size/mtime.
- [Kế hoạch Sprint 4 ban đầu](01_sprint4_two_person_plan.md) — khung tham khảo; giả định hai người/IAA bắt buộc đã được protocol v1 thay thế.
- [Tổng kết toàn bộ Sprint 3](../sprint_03/53_sprint3_end_to_end_report_20261005.md) — quy trình, kết quả, khó khăn, giới hạn và khuyến nghị.

## Nguyên tắc

- Không sửa corpus, gold, split, Gazetteer, checkpoint, prediction hoặc run đã khóa của Sprint 3.
- Chỉ dùng dev để phát triển/chọn cấu hình; test Sprint 3 là kết quả đã công bố, không dùng lại để tune.
- Mọi dữ liệu Sprint 4 có provenance, nhóm nguồn và split mới; gán nhãn dự đoán hỗ trợ không được tính là gán độc lập.
- Nguồn trong register chưa có mẫu annotation-ready; nguồn công khai vẫn phải xác minh phạm vi sử dụng, đặc biệt cloud/redistribution.
- Mục tiêu 200 mẫu/3 seed/18 GPU-giờ là đề xuất kế hoạch, chưa phải số lượng hoặc quota đã xác minh.
- Không mở rộng Sprint 4 sang T2, T3, API/RAG hoặc các tác vụ ngoài kế hoạch đã duyệt.
