# Sprint 3

**Trạng thái:** SPRINT3_PARTIAL_DP_BLOCKED. Kết quả T0/T1 đã được freeze và chấm; hai cấu hình Deepparse vẫn blocked do chưa xác minh điều kiện sử dụng checkpoint.

## Hồ sơ hiện hành

- [49 — Kết quả cuối, metrics, support và giới hạn](49_sprint3_final_results.md)
- [50 — Tái lập inference/scoring và bàn giao](50_sprint3_reproduction_and_handoff.md)
- [53 — Tổng kết quy trình Sprint 3 và kế hoạch Sprint 4](53_sprint3_end_to_end_report_20261005.md)
- [48 — Prompt đánh giá cuối Sprint 3](48_agent_prompt_finish_sprint3_final_evaluation.md)

Bằng chứng máy và receipt nằm trong data/interim/modeling/sprint03/final_completion_20261005_v1/ và data/interim/modeling/sprint03/release_and_kaggle_20261005_v1/. Giữ nguyên các manifest/hash này khi chia sẻ kết quả.

## Tài liệu vận hành còn dùng

- [Hướng dẫn nhãn T0 11 span](span_11_annotation_guideline.md)
- [Protocol chia corpus T0](t0_corpus_split_protocol_v1.md)
- [Protocol training và lựa chọn](17_training_protocol_v1.md)
- [Protocol QA test AI-assisted](37_test100_ai_assisted_annotation.md)
- [Bản phát hành corpus train/dev/test](../../../data/processed/annotation/sprint03/corpus_v1_release2/manifest.json)
- [Gazetteer thời gian](../../../data/processed/gazetteer/s3_v4_nso_dual_snapshot_release2/manifest.json)
- [Kế hoạch Sprint 4](../sprint_04/README.md)

**Giới hạn cần giữ trong mọi báo cáo:** T1 của CRF/PhoBERT-CRF chưa hiện thực; DYN Lai có F1 bằng 0 trên support 5; 4 nhãn test không có gold support; IAA chưa đo; track 5 trường không phải kết quả test; Gazetteer mã cũ còn phần chưa xác minh.
