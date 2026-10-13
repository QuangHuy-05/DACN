# Chất lượng dữ liệu và giới hạn — 06/10/2026

## Kết quả Sprint 3

Trạng thái là SPRINT3_PARTIAL_DP_BLOCKED. Bản hiện hành gồm [corpus_v1_release2](../data/processed/annotation/sprint03/corpus_v1_release2/manifest.json) và [test_gold_v1_release2](../data/processed/annotation/sprint03/test_gold_v1_release2/manifest.json): 240 train, 60 dev và 100 test. Test có 446 span T0; T1 có 64 mẫu eligible, 20 null và 16 excluded. Các ngoại lệ T1 giữ theo manifest, toàn bộ T0 được bảo toàn.

T0 test F1: HEUR-JW 0,9112; CRF-INDEP 0,9076; PhoBERT-CRF 0,9843; PROPOSED-DYN 0,9821; ablation không constraint 0,9843. DYN T1 accuracy 0,7188, macro-F1 0,5626, Lai F1 bằng 0 trên support 5. CRF/PhoBERT-CRF chưa triển khai T1. Hai cấu hình Deepparse chưa chạy do điều kiện sử dụng checkpoint chưa được xác minh. Agreement độc lập giữa người gán chưa đo.

Bộ kiểm tra nghiệm thu đạt 266 PASS / 8 SKIP / 0 FAIL. Audit cuối xác nhận 2.352 hash được bảo vệ và 4 kiểm tra size/mtime không đổi. Chi tiết nằm trong [kết quả](sprints/sprint_03/49_sprint3_final_results.md), [hướng dẫn tái lập](sprints/sprint_03/50_sprint3_reproduction_and_handoff.md) và [báo cáo tổng kết](sprints/sprint_03/53_sprint3_end_to_end_report_20261005.md).

## Benchmark và nguồn dữ liệu

- Data 01–04 và 06–07 là các benchmark công khai/OSM hoặc dữ liệu tổng hợp có thể truy nguyên; Data 02 giữ ground truth trong các cột metadata và baseline chỉ nhận ChuoiDiaChi.
- Data 05 chưa phát hành vì thiếu nguồn mốc/hướng đã xác minh. Địa chỉ Viet-Receipt-VQA chỉ dùng cho hồ sơ nhiễu và đang HOLD; không thay thế benchmark có ground truth.
- Không dùng địa chỉ khách hàng thật. data/raw/ và third_party/ là nguồn gốc, không sửa trực tiếp.
- Bộ chuẩn hành chính là bảng nguồn chính cho cạnh cũ → mới. Cặp quan sát OSM cần giữ tag gốc, alias có audit và quan hệ Nguon.
- T2 chưa thực thi. Gazetteer s3_v4_nso_dual_snapshot_release2 có 14.149 entity, 10.597 cạnh xã nguyên tử, 187 alias audit và 5 chuyển đổi phi nguyên tử; mã cũ vẫn partial do còn unresolved và giới hạn điều khoản nguồn. Xem [manifest](../data/processed/gazetteer/s3_v4_nso_dual_snapshot_release2/manifest.json).

## Quy tắc phát hành

Giữ encoding UTF-8-sig cho CSV benchmark, seed cố định và manifest/hash cho từng phát hành. Không ghi đè split/gold đã phát hành; không nâng candidate thành verified khi thiếu nguồn chính xác. Kết quả track 5 trường là development/compatibility, không phải T0/T1 test.