# Hồ sơ Sprint 3

**05/10/2026 — Test đã duyệt và GPU đã xác minh:** [47 — corpus240/60/100 release2,446span test,mask16T1, GPU smoke thật hai model và các lượt full](47_test_gold_release_and_kaggle_20261005.md). Không cần gán lại100; train/dev/split/raw/old runs giữ nguyên. Release2 sửa báo cáo nguồn, không đổi annotation. Test inference/scoring chưa chạy; các dòng blocked trước bên dưới là lịch sử.

**Hiện hành local L1–L5, round2:** đủ100 task/103 annotation, 99 converted/1 multiple tại695, không còn mẫu thiếu. Giữ JSON nguyên trạng; release chờ lựa chọn annotation và phán quyết T1. Đã có publisher, final-test pipeline fixture, training/resource ZIP mới có đủ dependency và hai notebook tách train/dev khỏi final test. Fullsuite239PASS/8SKIP,1313frozenhash+4rawsize/mtime không đổi; 0 cài mới. Chưa train/chấm test/chạy Colab.

- [44 — Inventory tái dùng, nguồn/license và cổng Deepparse](44_local_finish_resource_inventory.md)
- [45 — Thao tác QA/release và Colab giai đoạn cuối](45_local_release_and_colab_operations.md)
- [46 — Kết quả từng L1–L5, kiểm thử, artifact, Git và phần owner còn chốt](46_local_completion_report_20261004.md)

Các kết luận round1/báo cáo41 dưới đây được giữ làm lịch sử; ưu tiên round2/báo cáo46.

**Prompt triển khai local trước Colab:** [43 — P0 và L1–L5, đầu ra, cổng nghiệm thu và bàn giao](43_agent_prompt_local_completion_before_colab.md). Agent triển khai QA/release/pipeline/gói chạy local; thực nghiệm Colab và chấm test thật là giai đoạn cuối.

**QA test export 04/10/2026:** [41 — thiếu một mẫu, chọn annotation và rà hệ](41_test100_export_qa_20261004.md); [42 — các việc local trước, thực nghiệm Colab sau](42_remaining_local_then_colab.md). Hiện 98 candidate/100 sau chọn hai bản trùng tương đương; test gold chưa phát hành. Kaggle/Colab không chạy trong lượt QA này.

**Kaggle 04/10/2026:** [38 — inventory cài CLI trên D](38_kaggle_install_inventory.md), [39 — pipeline private, preflight/smoke và gate full training](39_kaggle_pipeline_operations.md). Dùng train240/dev60, không có test100. Job đầu không có GPU; chưa có pretrained smoke PASS/full training. Báo cáo40 ghi kết quả cuối từng job và GB/GiB thực đo.

[40 — Kết quả hai lượt remote, 194PASS/8SKIP, dung lượng và bước mở quyềnGPU](40_kaggle_pipeline_completion_20261004.md).

**04/10/2026 — Test AI-assisted theo yêu cầu chủ dự án:** [37 — Gói 100 prediction, cấu hình, từng bước review/Submit/export và protocol bổ sung](37_test100_ai_assisted_annotation.md). Gói đáp án local trong interim; chưa có test gold hoặc test metric. Gói blind cũ được giữ nguyên làm hồ sơ trước đổi cách gán.

**Bàn giao hiện hành P0/U1–U6:** Gazetteer hai snapshot thêm8.607 mã cũ exact, giữ3.355 mã mới và2.187 mã cũ chưa xác minh; CRF T0 dev90,56%, HEUR88,01%. Có notebook/bundle train/dev đã chuẩn bị, chưa chạy neural/Colab/test100. Cài local mới0bytes; artifact ngoàiGit phải nhận riêng.

- [31 — Nguồn chính thức, kiểm cha/ngày và unresolved](31_pre_colab_source_verification.md)
- [32 — Gazetteer dual snapshot và bản hoàn chỉnh sổ nguồn](32_temporal_gazetteer_release.md)
- [33 — Resource lock, giấy phép và lệnh future Colab](33_pre_colab_resource_inventory.md)
- [34 — Run HEUR/CRF mới, sweep và so sánh development](34_light_baseline_followup.md)
- [35 — Kiểm thử, hash frozen và nghiệm thu artifact](35_pre_colab_acceptance.md)
- [36 — Từng bước partner Label Studio và chủ dự án Colab](36_label100_and_colab_handoff.md)

Các trạng thái ngày02/10 và đầu03/10 bên dưới là lịch sử; ưu tiên báo cáo31–36 cho lượt bàn giao mới.

**Hiện hành 03/10/2026:** đã xuất [gazetteer s3_v3 snapshot NSO](../../../data/processed/gazetteer/s3_v3_nso_2025_snapshot/manifest.json): 34 mã tỉnh mới + 3.321 mã xã/phường mới xác minh tại 01/07/2025; mã cũ tiếp tục unverified, toàn gói vẫn partial. PhoBERT full tokenizer + VnCoreNLP offset alignment đã qua 300/300 train/dev; 29/29 ca cũ khôi phục, gold QA 300/300, không còn reject. Full suite WSL đạt 153 PASS / 8 SKIP / 0 FAIL trước follow-up Gazetteer; 4 test snapshot mới PASS. Chưa train hoặc dùng test100/Colab. Xem [báo cáo xử lý alignment](28_phobert_alignment_tone_relocation_20261003.md), [báo cáo phát hành nguồn NSO](29_nso_official_snapshot_gazetteer_release_20261003.md), [nghiệm thu sáu việc và dung lượng](27_tasks_01_06_completion_20261003.md). Các trạng thái bên dưới là lịch sử.

- [Inventory trước cài của follow-up](23_task_01_06_install_inventory_20261003.md)
- [Nguồn mã, bảng 615 ca và gazetteer gap](24_source_reconciliation_followup_20261003.md)
- [Phân tích lỗi frozen: T0 và 5 trường](25_frozen_baseline_error_analysis_20261003.md)
- [Package/resources đã cài và tích hợp neural thật](26_local_neural_install_and_integration_20261003.md)
- [Nghiệm thu sáu việc, GB/GiB, tests, hash và blocker](27_tasks_01_06_completion_20261003.md)
- [Khôi phục 29 PhoBERT alignment rejects; audit đủ 300 train/dev](28_phobert_alignment_tone_relocation_20261003.md)
- [Đối chiếu snapshot NSO 01/07/2025 và phát hành s3_v3](29_nso_official_snapshot_gazetteer_release_20261003.md)
- [Prompt hoàn tất 6 việc trước thực nghiệm Colab và nghiệm thu 100 test](30_agent_prompt_finish_six_tasks_before_colab.md)

**Hiện hành U1–U7, 02/10/2026:** đã triển khai alignment/data loader, ba pipeline neural, protocol, checkpoint/prediction/audit và verifier gazetteer. Raw + DP surface giữ đủ 240/60 và 1.341 span; T1 mask 206/53. Kiểm thử toàn repo **143 PASS / 8 SKIP / 0 FAIL**, runtime3.11 **73 PASS / 7 SKIP / 0 FAIL**. Neural integration còn `INTEGRATION_PENDING_RESOURCE`, training `TRAINING_DEFERRED_BY_USER`; không có checkpoint/prediction/metric pretrained mới. Gazetteer **0 mã mới verified**, giữ partial. Colab/test100 tạm gác. Xem báo cáo19; báo cáo15 vẫn là nguồn kết quả baseline đã khóa.

**Thực nghiệm hiện hành 02/10/2026:** HEUR-JW và CRF độc lập đã có kết quả T0 dev60 và track5 trường4.800 hàng (đã loại100 hàng hold). DP-ZS-FT có adapter/mapping nhưng bị chặn RAM/license trước cài/tải; test gold vẫn chờ partner. Xem [kết quả thực nghiệm](15_baseline_experiments_20261002.md) và [inventory môi trường](14_experiment_01_04_environment.md). Các báo cáo13 trở về trước là lịch sử bước nghiệm thu dữ liệu.

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
- [Kế hoạch QA, train/dev và baseline trong lúc chờ 100 test](10_work_plan_while_waiting_test100.md)
- [Kết quả nhiệm vụ 1–4 ngày 02/10 và link 24 task cần sửa](11_tasks_01_04_review_20261002.md)
- [Lịch sử rà sau sửa 24 task và các ca từng chờ](12_tasks_01_04_followup_20261002.md)
- [Nghiệm thu nhiệm vụ 1–4: train/dev đã phát hành, ngoại lệ T1 và bàn giao](13_tasks_01_04_completion_20261002.md)
- [Inventory môi trường/package/model cho bốn nhiệm vụ thực nghiệm](14_experiment_01_04_environment.md)
- [Kết quả HEUR-JW, CRF-INDEP, blocker DP-ZS-FT và cách tái lập](15_baseline_experiments_20261002.md)
- [Prompt bàn giao 7 ưu tiên kỹ thuật; tạm gác Colab và test 100](16_agent_prompt_seven_priorities.md)
- [Protocol training/config/ablation đã khóa và lệnh vận hành](17_training_protocol_v1.md)
- [Inventory tài nguyên neural; chưa cài hoặc tải](18_modeling_resource_inventory.md)
- [Kết quả triển khai U1–U7, kiểm thử, artifact và blocker](19_seven_priorities_implementation_report.md)
- [Audit nguồn mã hành chính, coverage và reference verifier](20_gazetteer_source_audit.md)
- [Gói GitHub dành riêng cho partner gán 100 test](annotation_handoff/test100_v1/README.md)
- [Vận hành các gói S3-01 đến S3-03](03_s3_01_03_operations.md)
- [Lộ trình hoàn tất Sprint 3](02_completion_roadmap.md)

Kiểm toán ngày 25/09/2026: `baseline_v3_fuzzy` đạt `PASS` trong phạm vi benchmark 5 trường và protocol ghi trong manifest; `baseline_v2` được giữ frozen, còn thiếu hai snapshot mã lịch sử nên tính tái lập đầy đủ là `UNVERIFIABLE`. Xem báo cáo để biết từng cổng kiểm tra và giới hạn.

Batch 01 T0 gồm 68 pilot, 100 ứng viên benchmark test giữ riêng và 20 VQA chờ rà soát. [Pilot gold v1](../../../data/processed/annotation/sprint03/pilot_gold_v1.jsonl) đã được phát hành từ raw JSON export sau sửa ngày 29/09/2026: QA cấu trúc có 68/68 annotation hợp lệ và 0 lỗi; người gán `quanghuy050816@gmail.com` xác nhận đã rà soát cả 68 mẫu. Chỉ task 1–4 thay đổi so với export cũ; bảy ca có cờ được ghi trong [sổ quyết định](pilot_decision_log.csv). [Guideline](span_11_annotation_guideline.md) khóa ở `s3-span-v1.1`; [biên bản và hash](pilot_gold_approval.md) cùng [manifest gold](../../../data/processed/annotation/sprint03/pilot_gold_v1_manifest.json) ghi bằng chứng phát hành. Bộ QA vẫn dùng trạng thái trước duyệt `READY_FOR_HUMAN_REVIEW`; manifest sau duyệt ghi `APPROVED_GOLD`. Agreement giữa hai người gán là `NOT_MEASURED`. **100 ứng viên test chưa gán nhãn** nên chưa thể báo F1 T0 trên tập test. Cấu hình nằm tại `configs/label_studio_span11.xml`; script tái tạo danh sách là `python -m scripts.10_prepare_span_annotation`.

Review ngày 30/09/2026: batch 02 có 232 task train/dev và prediction gợi ý chỉ cho batch này; preflight phân bổ 240/60 train/dev khi ghép pilot và ghi 138 cặp gần giống cần quyết định. Gazetteer v2 có 14.149 entity, 10.597 cạnh cấp xã, 187 alias và 5 chuyển đổi cấp huyện→đặc khu tra được; mã cũ vẫn chưa xác minh. Xem [báo cáo review và thao tác bàn giao](06_s3_04_s3_03_review_and_handover.md). Các script `10_prepare_span_annotation.py` và `16_prepare_t0_corpus_batch.py` có output batch cố định; không chạy lại để ghi đè task đã dùng.

Gói [gán lại T0 v2](08_source_reannotation_v2_handover.md) giữ nguyên 68 pilot và 232 batch 02. Hai project dùng prediction nên agreement độc lập `NOT_MEASURED`. Partner nhận bộ test-only trên nhánh `print3_label100test`, theo protocol v1.0 sau [preflight PASS với 138 quyết định của Huy](test100_split_gate_20261001.json). Bản cuối ngày 02/10 hash `e4d4f60b...` đã được QA 68/68 + 232/232, 249 + 1.092 span và phát hành `corpus_train_dev_v2`: **240 train / 60 dev**, 1.057 / 284 span, `TRAIN_DEV_APPROVED_TEST_PENDING`. Chủ dự án giữ 537/543; ngoại lệ hệ task 543 được ghi và mask T1, T0 giữ nguyên. 87/87 test toàn repo và 18/18 span/CLI Python 3.11 PASS. [Báo cáo nghiệm thu hiện hành](13_tasks_01_04_completion_20261002.md) có hash, coverage và bước tiếp theo; các báo cáo 11/12 lưu lịch sử lượt rà trước. Partner tiếp tục 100 test mù.
