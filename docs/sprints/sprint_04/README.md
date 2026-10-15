# Sprint 4

**Hiện hành — 06/10/2026:** đã hiện thực nhiệm vụ 1 với một chủ dự án phụ trách toàn bộ, nguồn mới ưu tiên, holdout có điều kiện, Kaggle và hạn 20/10/2026. Dữ liệu mới và gán nhãn chưa thực hiện; các thực nghiệm Nhóm 1 (lấp khoảng trống khoa học) đã chạy, xem mục "Nhóm 1" bên dưới.

Đọc [Protocol Sprint 4 v1](02_s4_protocol_v1.md) trước triển khai. IAA giữa hai người là `NOT_MEASURED`; kế hoạch kiểm tra thay thế là gán lặp thủ công của cùng người sau ít nhất 7 ngày, báo **intra-annotator** riêng.

## Mục tiêu

Tăng độ tin cậy của benchmark T0/T1 và xác định mức ổn định của các mô hình đã có kết quả trong Sprint 3. Sprint 4 giữ nguyên các release và kết quả Sprint 3 đã khóa; dữ liệu mới (nếu được thu thập và duyệt) phải phát hành thành phiên bản mới.

## Tài liệu chính

- [Protocol Sprint 4 v1](02_s4_protocol_v1.md) — quyết định hiện hành, support, source register, gán lặp, split/holdout, Kaggle, lịch và nghiệm thu.
- [Bước 1 — quyết định phạm vi, quyền nguồn và Amendment A1](04_step1_decision_and_protocol_amendment.md) — 13/10/2026, nhánh `SCOPED_PARTIAL`; [kế hoạch đóng sprint](03_execution_plan_before_20261019.md).
- [Cấu hình protocol](../../../configs/annotation/sprint04/protocol_v1.json) và [nguồn ứng viên](../../../configs/annotation/sprint04/source_register_v1.csv).
- [Snapshot Sprint 3 trước/sau nhiệm vụ 1](../../../data/interim/annotation/sprint04/protocol_v1/baseline_snapshot.json) — phạm vi hash được ghi rõ; raw kiểm size/mtime.
- [Kế hoạch Sprint 4 ban đầu](01_sprint4_two_person_plan.md) — khung tham khảo; giả định hai người/IAA bắt buộc đã được protocol v1 thay thế.
- [Tổng kết toàn bộ Sprint 3](../sprint_03/53_sprint3_end_to_end_report_20261005.md) — quy trình, kết quả, khó khăn, giới hạn và khuyến nghị.

## Nhóm 1 — lấp khoảng trống khoa học (13–15/10/2026)

Chạy theo vòng lặp điều phối → hiện thực → review độc lập trên nhánh `sprint4_group1`. Bắt đầu từ [báo cáo tổng hợp 14](14_group1_summary.md); mỗi báo cáo gói có bản review tương ứng trong [reviews/](reviews/) (review WP1 do phiên điều phối làm ngày 13/10, ghi lại thành file 15/10).

| Tài liệu | Nội dung |
|---|---|
| [05](05_project_review_and_remaining_tasks.md) | Rà soát toàn dự án, phản biện và việc còn lại |
| [06](06_group1_science_gap_plan.md) | Kế hoạch chi tiết Nhóm 1; mục 7 là lịch điều phối và trạng thái |
| [07](07_agent_prompts_group1.md), [07b](07b_reviewer_prompt_group1.md) | Prompt cho agent hiện thực và agent review |
| [08](08_amendment_a2_group1_scope.md) | Amendment A2: đưa T2 baseline, thống kê hậu nghiệm và đa seed vào phạm vi Nhóm 1 |
| [09](09_t2_baseline_results.md) | WP1: T2 baseline hai chiều, E2, E3 |
| [10](10_t1_h5_results.md) | WP2 và WP2b: T1, bảng H5 (mục 11: checkpoint huấn luyện lại cục bộ) |
| [11](11_reliability_results.md) | WP3a: CI và kiểm định ghép cặp; WP3b: ba seed cục bộ |
| [12](12_cpu_hypothesis_results.md) | WP4: H3, E1, H2, H4 |
| [13](13_constraint_ablation_and_h1.md) | WP5: ablation ràng buộc giải mã và tuyên bố về H1 |
| [14](14_group1_summary.md) | WP6: bảng giả thuyết, bảng T0/T1/T2, giới hạn, phần còn thiếu |

Amendment A2 đã đưa T2 baseline vào phạm vi: câu cũ "không mở rộng Sprint 4 sang T2, T3, API/RAG" ở mục Nguyên tắc dưới đây **đã được sửa** (T2 baseline vào phạm vi Nhóm 1 theo Amendment A2, tài liệu 08); T3, API/RAG và các tác vụ ngoài kế hoạch vẫn ngoài phạm vi. Run của Nhóm 1 nằm ở `data/processed/evaluation/sprint04/` (mỗi run một `run_manifest.json`).

## Nguyên tắc

- Không sửa corpus, gold, split, Gazetteer, checkpoint, prediction hoặc run đã khóa của Sprint 3.
- Chỉ dùng dev để phát triển/chọn cấu hình; test Sprint 3 là kết quả đã công bố, không dùng lại để tune.
- Mọi dữ liệu Sprint 4 có provenance, nhóm nguồn và split mới; gán nhãn dự đoán hỗ trợ không được tính là gán độc lập.
- Nguồn trong register chưa có mẫu annotation-ready; nguồn công khai vẫn phải xác minh phạm vi sử dụng, đặc biệt cloud/redistribution.
- Mục tiêu 200 mẫu/3 seed/18 GPU-giờ là đề xuất kế hoạch, chưa phải số lượng hoặc quota đã xác minh.
- Không mở rộng Sprint 4 sang T3, API/RAG hoặc các tác vụ ngoài kế hoạch đã duyệt. T2 baseline được đưa vào phạm vi cho Nhóm 1 bởi Amendment A2 ([08](08_amendment_a2_group1_scope.md)).
