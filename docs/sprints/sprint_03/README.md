# Hồ sơ Sprint 3

- [Kế hoạch kiểm toán baseline và chốt ma trận mô hình](01_baseline_audit_and_model_matrix.md)
- [Báo cáo kiểm toán baseline](baseline_run_audit.md) ([JSON bằng chứng](baseline_run_audit.json))
- [Ma trận mô hình đã chốt](model_matrix.md)
- [Guideline gán nhãn T0 11 span](span_11_annotation_guideline.md)
- [Biên bản rà soát và phát hành gold pilot](pilot_gold_approval.md)
- [Kiểm kê nguồn và batch 01 để gán nhãn](span_annotation_inventory.md)
- [Hướng dẫn Label Studio pilot 68 mẫu cho partner](04_label_studio_pilot_handover.md)
- [Kế hoạch bàn giao agent: ưu tiên 2 S3-04 (corpus/split) và ưu tiên 3 S3-03 (gazetteer)](05_s3_04_s3_03_agent_execution_plan.md)
- [Vận hành các gói S3-01 đến S3-03](03_s3_01_03_operations.md)
- [Lộ trình hoàn tất Sprint 3](02_completion_roadmap.md)

Kiểm toán ngày 25/09/2026: `baseline_v3_fuzzy` đạt `PASS` trong phạm vi benchmark 5 trường và protocol ghi trong manifest; `baseline_v2` được giữ frozen, còn thiếu hai snapshot mã lịch sử nên tính tái lập đầy đủ là `UNVERIFIABLE`. Xem báo cáo để biết từng cổng kiểm tra và giới hạn.

Batch 01 T0 gồm 68 pilot, 100 ứng viên benchmark test giữ riêng và 20 VQA chờ rà soát. [Pilot gold v1](../../../data/processed/annotation/sprint03/pilot_gold_v1.jsonl) đã được phát hành từ raw JSON export sau sửa ngày 29/09/2026: QA cấu trúc có 68/68 annotation hợp lệ và 0 lỗi; người gán `quanghuy050816@gmail.com` xác nhận đã rà soát cả 68 mẫu. Chỉ task 1–4 thay đổi so với export cũ; bảy ca có cờ được ghi trong [sổ quyết định](pilot_decision_log.csv). [Guideline](span_11_annotation_guideline.md) khóa ở `s3-span-v1.1`; [biên bản và hash](pilot_gold_approval.md) cùng [manifest gold](../../../data/processed/annotation/sprint03/pilot_gold_v1_manifest.json) ghi bằng chứng phát hành. Bộ QA vẫn dùng trạng thái trước duyệt `READY_FOR_HUMAN_REVIEW`; manifest sau duyệt ghi `APPROVED_GOLD`. Agreement giữa hai người gán là `NOT_MEASURED`. **100 ứng viên test chưa gán nhãn** nên chưa thể báo F1 T0 trên tập test. Cấu hình nằm tại `configs/label_studio_span11.xml`; script tái tạo danh sách là `python -m scripts.10_prepare_span_annotation`.
