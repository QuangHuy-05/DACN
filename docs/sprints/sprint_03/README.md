# Hồ sơ Sprint 3

- [Kế hoạch kiểm toán baseline và chốt ma trận mô hình](01_baseline_audit_and_model_matrix.md)
- [Báo cáo kiểm toán baseline](baseline_run_audit.md) ([JSON bằng chứng](baseline_run_audit.json))
- [Ma trận mô hình đã chốt](model_matrix.md)
- [Guideline gán nhãn T0 11 span](span_11_annotation_guideline.md)
- [Biên bản rà soát và phát hành gold pilot](pilot_gold_approval.md)
- [Kiểm kê nguồn và batch 01 để gán nhãn](span_annotation_inventory.md)
- [Hướng dẫn Label Studio pilot 68 mẫu cho partner](04_label_studio_pilot_handover.md)
- [Kế hoạch bàn giao agent: ưu tiên 2 S3-04 (corpus/split) và ưu tiên 3 S3-03 (gazetteer)](05_s3_04_s3_03_agent_execution_plan.md)
- [Báo cáo review S3-04/S3-03 và hướng dẫn Label Studio batch 02/test](06_s3_04_s3_03_review_and_handover.md)
- [Kế hoạch gán lại 68 pilot và 232 train/dev bằng ứng viên có truy vết nguồn](07_source_derived_reannotation_plan.md)
- [Bàn giao gói gán lại T0 v2 và thao tác Label Studio](08_source_reannotation_v2_handover.md)
- [Hướng dẫn từng bước 68 + 232 có prediction và 100 test mù](09_label_studio_400_step_by_step.md)
- [Gói GitHub dành riêng cho partner gán 100 test](annotation_handoff/test100_v1/README.md)
- [Vận hành các gói S3-01 đến S3-03](03_s3_01_03_operations.md)
- [Lộ trình hoàn tất Sprint 3](02_completion_roadmap.md)

Kiểm toán ngày 25/09/2026: `baseline_v3_fuzzy` đạt `PASS` trong phạm vi benchmark 5 trường và protocol ghi trong manifest; `baseline_v2` được giữ frozen, còn thiếu hai snapshot mã lịch sử nên tính tái lập đầy đủ là `UNVERIFIABLE`. Xem báo cáo để biết từng cổng kiểm tra và giới hạn.

Batch 01 T0 gồm 68 pilot, 100 ứng viên benchmark test giữ riêng và 20 VQA chờ rà soát. [Pilot gold v1](../../../data/processed/annotation/sprint03/pilot_gold_v1.jsonl) đã được phát hành từ raw JSON export sau sửa ngày 29/09/2026: QA cấu trúc có 68/68 annotation hợp lệ và 0 lỗi; người gán `quanghuy050816@gmail.com` xác nhận đã rà soát cả 68 mẫu. Chỉ task 1–4 thay đổi so với export cũ; bảy ca có cờ được ghi trong [sổ quyết định](pilot_decision_log.csv). [Guideline](span_11_annotation_guideline.md) khóa ở `s3-span-v1.1`; [biên bản và hash](pilot_gold_approval.md) cùng [manifest gold](../../../data/processed/annotation/sprint03/pilot_gold_v1_manifest.json) ghi bằng chứng phát hành. Bộ QA vẫn dùng trạng thái trước duyệt `READY_FOR_HUMAN_REVIEW`; manifest sau duyệt ghi `APPROVED_GOLD`. Agreement giữa hai người gán là `NOT_MEASURED`. **100 ứng viên test chưa gán nhãn** nên chưa thể báo F1 T0 trên tập test. Cấu hình nằm tại `configs/label_studio_span11.xml`; script tái tạo danh sách là `python -m scripts.10_prepare_span_annotation`.

Review ngày 30/09/2026: batch 02 có 232 task train/dev và prediction gợi ý chỉ cho batch này; preflight phân bổ 240/60 train/dev khi ghép pilot và ghi 138 cặp gần giống cần quyết định. Gazetteer v2 có 14.149 entity, 10.597 cạnh cấp xã, 187 alias và 5 chuyển đổi cấp huyện→đặc khu tra được; mã cũ vẫn chưa xác minh. Xem [báo cáo review và thao tác bàn giao](06_s3_04_s3_03_review_and_handover.md). Các script `10_prepare_span_annotation.py` và `16_prepare_t0_corpus_batch.py` có output batch cố định; không chạy lại để ghi đè task đã dùng.

Gói [gán lại T0 v2](08_source_reannotation_v2_handover.md) giữ nguyên 68 pilot và 232 batch 02. Bản QA ngày 01/10 có 245 span pilot, 1.059 span batch và 473 mục rà soát, gồm một thành phần số nhà phải chọn ranh giới thủ công. Theo lựa chọn của chủ dự án, cả hai project dùng prediction để rà, sửa và Submit; agreement độc lập `NOT_MEASURED`. Tệp import kèm prediction nằm trong `data/interim/annotation/sprint03/reannotation_v2_release1/`. Partner nhận bộ test-only có version/hash trên nhánh `print3_label100test`, sẵn sàng gán mù theo protocol v1.0 sau [preflight PASS với 138 quyết định của Huy](test100_split_gate_20261001.json). Chưa có raw export hoặc biên bản duyệt vòng v2. Toàn bộ 64 kiểm thử đã chạy đạt trong WSL ngày 01/10/2026.
