# Chất lượng dữ liệu và giới hạn — 06/10/2026 (cập nhật 15/10/2026: Nhóm 1 Sprint 4)

## Kết quả Sprint 3

Trạng thái là SPRINT3_PARTIAL_DP_BLOCKED. Bản hiện hành gồm [corpus_v1_release2](../data/processed/annotation/sprint03/corpus_v1_release2/manifest.json) và [test_gold_v1_release2](../data/processed/annotation/sprint03/test_gold_v1_release2/manifest.json): 240 train, 60 dev và 100 test. Test có 446 span T0; T1 có 64 mẫu eligible, 20 null và 16 excluded. Các ngoại lệ T1 giữ theo manifest, toàn bộ T0 được bảo toàn.

T0 test F1: HEUR-JW 0,9112; CRF-INDEP 0,9076; PhoBERT-CRF 0,9843; PROPOSED-DYN 0,9821; ablation không constraint 0,9843. DYN T1 accuracy 0,7188, macro-F1 0,5626, Lai F1 bằng 0 trên support 5. CRF/PhoBERT-CRF chưa triển khai T1. Hai cấu hình Deepparse chưa chạy do điều kiện sử dụng checkpoint chưa được xác minh. Agreement độc lập giữa người gán chưa đo.

Bộ kiểm tra nghiệm thu đạt 266 PASS / 8 SKIP / 0 FAIL. Audit cuối xác nhận 2.352 hash được bảo vệ và 4 kiểm tra size/mtime không đổi. Chi tiết nằm trong [kết quả](sprints/sprint_03/49_sprint3_final_results.md), [hướng dẫn tái lập](sprints/sprint_03/50_sprint3_reproduction_and_handoff.md) và [báo cáo tổng kết](sprints/sprint_03/53_sprint3_end_to_end_report_20261005.md).

## Kết quả Nhóm 1 Sprint 4 (15/10/2026)

Nhóm 1 lấp các khoảng trống khoa học theo Amendment A2 ([08](sprints/sprint_04/08_amendment_a2_group1_scope.md)): T2 baseline, T1/H5, khoảng tin cậy và đa seed, H2/H3/E1/H4, ablation ràng buộc. Không có dữ liệu mới và không sửa corpus, gold, split, gazetteer, checkpoint hay prediction của Sprint 3; mọi run mới nằm ở `data/processed/evaluation/sprint04/` (mỗi run một `run_manifest.json`). Bảng giả thuyết H1–H5/E1–E4, bảng T0/T1/T2 hợp nhất, giới hạn và phần còn thiếu nằm ở [báo cáo tổng hợp 14](sprints/sprint_04/14_group1_summary.md); báo cáo theo gói: [09](sprints/sprint_04/09_t2_baseline_results.md) (T2), [10](sprints/sprint_04/10_t1_h5_results.md) (T1, H5), [11](sprints/sprint_04/11_reliability_results.md) (CI, đa seed), [12](sprints/sprint_04/12_cpu_hypothesis_results.md) (H2, H3, E1, H4), [13](sprints/sprint_04/13_constraint_ablation_and_h1.md) (ràng buộc, H1).

Giới hạn dữ liệu mới của các run này, cần đọc cùng mọi số:
- Data 07 (T2) chỉ có B 244 và M 356 (A và C `NOT_EVALUABLE_NO_SUPPORT`), 23 mã phường mới, 49 đơn vị cũ chuẩn hóa, 441/600 ở Hà Nội; mỗi đơn vị cũ chỉ có một đích quan sát và Data 07 được xác minh bằng chính CSV nguồn của gazetteer, nên accuracy tra bảng không nói về độ phủ bảng ngoài Data 07.
- Dữ liệu T1 tổng hợp (train 105 dòng, `t1_synth_eval` 2.195, Data 06 held-out 580) cùng một generator và thuộc stress track; `Lai` của test chỉ có support 5; 870/987 dòng `cu` của `t1_synth_eval` mang khóa `UNRESOLVED`.
- Mọi số trên test Sprint 3 là hậu nghiệm (`POST_HOC_SECONDARY`): test đã bị quan sát. Checkpoint huấn luyện lại trên CPU cục bộ (ba seed) mang nhãn `LOCAL_CPU_RETRAINED` và không trộn với hàng Kaggle seed 42; ba seed là ước lượng thô.
- Track 5 trường là `DEVELOPMENT_TRACK`; nhãn Data 04 là silver từ generator; E4 chưa chạy (VQA HOLD); Tầng 2 neural của H3/E1 `NOT_RUN` (cần ≥ 20 GiB ổ D: trống); H1 `NOT_TESTABLE` vì chưa có adapter.

Bộ kiểm tra hiện tại: 453 test, 445 PASS / 8 SKIP / 0 FAIL (đo ngày 15/10/2026 trong `~/.venv_dacn`; 438 trước WP6 cộng 15 test của `tests/test_group1_summary.py`) (mốc Sprint 3: 266 PASS / 8 SKIP / 0 FAIL).

## Benchmark và nguồn dữ liệu

- Data 01–04 và 06–07 là các benchmark công khai/OSM hoặc dữ liệu tổng hợp có thể truy nguyên; Data 02 giữ ground truth trong các cột metadata và baseline chỉ nhận ChuoiDiaChi.
- Data 05 chưa phát hành vì thiếu nguồn mốc/hướng đã xác minh. Địa chỉ Viet-Receipt-VQA chỉ dùng cho hồ sơ nhiễu và đang HOLD; không thay thế benchmark có ground truth.
- Không dùng địa chỉ khách hàng thật. data/raw/ và third_party/ là nguồn gốc, không sửa trực tiếp.
- Bộ chuẩn hành chính là bảng nguồn chính cho cạnh cũ → mới. Cặp quan sát OSM cần giữ tag gốc, alias có audit và quan hệ Nguon.
- T2 baseline đã thực thi ở Nhóm 1 Sprint 4 (mốc 05/10 của Sprint 3 ghi "T2 chưa thực thi"; xem mục Kết quả Nhóm 1). Gazetteer s3_v4_nso_dual_snapshot_release2 có 14.149 entity, 10.597 cạnh xã nguyên tử, 187 alias audit và 5 chuyển đổi phi nguyên tử; mã cũ vẫn partial do còn unresolved và giới hạn điều khoản nguồn. Xem [manifest](../data/processed/gazetteer/s3_v4_nso_dual_snapshot_release2/manifest.json).

## Quy tắc phát hành

Giữ encoding UTF-8-sig cho CSV benchmark, seed cố định và manifest/hash cho từng phát hành. Không ghi đè split/gold đã phát hành; không nâng candidate thành verified khi thiếu nguồn chính xác. Kết quả track 5 trường là development/compatibility, không phải T0/T1 test.