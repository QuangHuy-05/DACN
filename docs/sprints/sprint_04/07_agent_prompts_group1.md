# Prompt cho agent hiện thực Nhóm 1

**Cách dùng:** mỗi phiên agent nhận **Khối chung** + đúng **một** khối WP. Chạy WP0 trước; sau đó WP1, WP3a, WP4, WP2 có thể chạy song song (mỗi WP sở hữu tập file riêng); WP3b cần chủ dự án đồng ý upload Kaggle; WP5 chạy sau WP2 và WP3b; WP6 chạy cuối. Kế hoạch gốc: [06_group1_science_gap_plan.md](06_group1_science_gap_plan.md).

---

## Khối chung (dán vào đầu mọi prompt)

```text
Bạn làm việc trong repository D:\DACN (đồ án chuẩn hóa/phân giải địa chỉ tiếng Việt qua cải cách hành chính 2025).
Đọc trước, theo thứ tự: AGENTS.md; docs/sprints/sprint_04/06_group1_science_gap_plan.md (đặc biệt mục 1 "Hiện trạng đã kiểm"
và mục 5 "Quy tắc chung"); docs/sprints/sprint_03/49_sprint3_final_results.md.

Môi trường: chạy lệnh trong WSL tại /mnt/d/DACN. Không cài thư viện mới vào bất kỳ runtime nào.
Có ba runtime tách biệt (đo ngày 13/10/2026), không runtime nào có đủ mọi thư viện:
- Chính: `source ~/.venv_dacn/bin/activate` (Python 3.14) — numpy, pandas, pyarrow, osmium, tqdm, vietnamadminunits.
  KHÔNG có pycrfsuite, scipy, torch, transformers, sklearn. Dùng cho dữ liệu, tra bảng, chấm điểm, thống kê, bộ test.
- CRF: data/interim/evaluation/sprint03/runtime_py311/bin/python (Python 3.11) — có pycrfsuite; KHÔNG có numpy, pandas.
  Dùng riêng cho huấn luyện/suy luận CRF-INDEP; đặt PYTHONDONTWRITEBYTECODE=1.
- Neural: data/interim/modeling/sprint03/runtime_neural_d_v1/bin/python (Python 3.11) — numpy, torch 2.8.0 CPU,
  transformers; KHÔNG có pycrfsuite. Chỉ dùng cho suy luận neural trên CPU; nạp chậm vì nằm trên /mnt/d.
Hệ quả: bước cần CRF hoặc neural phải chạy thành tiến trình riêng trong runtime tương ứng và ghi predictions.jsonl;
bước chấm điểm/thống kê đọc file đó trong runtime chính. Không import pycrfsuite/torch ở mức module trong mã dùng
chung, và không import numpy/pandas trong đường chạy CRF. Thiếu thư viện thì hiện thực bằng numpy/thư viện chuẩn
hoặc dừng và báo, không tự cài.

Ràng buộc cứng:
1. Không sửa/xóa: data/raw/, third_party/, data/processed/annotation/, data/processed/gazetteer/, checkpoint,
   prediction và evidence trong data/interim/modeling/sprint03/, các tài liệu Sprint 3. Chỉ đọc.
2. Chỉ tạo/sửa các file được liệt kê ở mục "File bạn sở hữu" của gói việc. Cần sửa file khác thì dừng và hỏi.
3. Đầu ra thí nghiệm ghi vào thư mục có version được chỉ định; nếu thư mục đã tồn tại thì từ chối ghi đè, tạo _v2.
4. Suy luận chỉ nhận chuỗi văn bản. Mọi cột metadata/gold (GT_*, KieuLai, LoaiAnhXa, HeQuyChieu, spans,
   address_system...) chỉ được dùng ở phía chấm điểm.
5. Không chọn mô hình, seed, checkpoint, ngưỡng hay luật bằng test Sprint 3. Danh sách hệ thống, luật mặc định
   và seed phải được ghi vào run_manifest.json TRƯỚC khi chấm điểm.
6. Mỗi run có đúng một run_manifest.json: SHA-256 file đầu vào, SHA-256 mã nguồn liên quan, seed, phiên bản luật,
   thời điểm, số dòng vào/ra. Không tạo thêm lớp ledger/audit/receipt nào khác.
7. Mọi tỷ lệ phải đi kèm mẫu số và support. Support 0 ghi NOT_EVALUABLE_NO_SUPPORT. Kết quả âm là đầu ra hợp lệ:
   báo đúng số, không điều chỉnh thiết kế sau khi thấy kết quả để làm đẹp.
8. Quy ước mã: tên hàm/biến tiếng Anh, giữ tên cột tiếng Việt; pathlib.Path, không đường dẫn tuyệt đối máy cá nhân;
   kiểm tồn tại file và cột bắt buộc trước khi xử lý; seed cố định; CSV xuất utf-8-sig; ghi chú ngắn cho logic
   hành chính và điều kiện chống rò rỉ.
9. Không upload, submit Kaggle, gọi dịch vụ mạng, commit hay push nếu gói việc không nêu rõ và chủ dự án chưa
   đồng ý trong phiên.

Trước khi báo xong: chạy `python -m unittest discover -s tests -v` (toàn bộ; mốc đo ngày 13/10/2026 trong
~/.venv_dacn là 294 test: 286 PASS / 8 SKIP / 0 FAIL — không được có FAIL và không được làm giảm số PASS cũ), chạy script của bạn từ đầu trên thư mục đầu ra mới để chứng minh tái lập, kiểm số dòng/cột/
encoding/bản ghi trùng của mọi CSV đầu ra.

Báo cáo cuối (tiếng Việt, ngắn): trạng thái từng đầu ra (PASS / PARTIAL / NEGATIVE_RESULT / NOT_EVALUABLE / BLOCKED),
bảng số chính, giới hạn, lệnh tái lập, danh sách file đã tạo, và mọi điểm bạn suy luận thay vì đo được.
```

---

## WP0 — Nền dùng chung

```text
NHIỆM VỤ: dựng hai mô-đun dùng chung cho các thí nghiệm Nhóm 1 và ghi Amendment A2.

File bạn sở hữu: src/evaluation/leak_guard.py, src/evaluation/stats.py, tests/test_group1_shared.py,
scripts/65_prepare_group1_guards.py, docs/sprints/sprint_04/08_amendment_a2_group1_scope.md,
data/interim/modeling/sprint04/group1_guards_20261013_v1/.

1. Amendment A2: chép 5 điểm ở mục 2 của kế hoạch thành tài liệu 08, ghi trạng thái
   "ĐÃ DUYỆT — chủ dự án duyệt cả năm điểm ngày 13/10/2026"; không sửa 02_s4_protocol_v1.md.

2. leak_guard.py
   - Nạp train.jsonl, dev.jsonl, test_benchmark_t0.jsonl, identity_registry.jsonl của
     data/processed/annotation/sprint03/corpus_v1_release2 (kiểm hash theo manifest.json trước khi dùng).
   - normalize_for_overlap(text): NFC, casefold, bỏ dấu câu, gộp khoảng trắng.
   - build_exclusion_index(splits=("train","dev","test")) -> khóa chuỗi chuẩn hóa + source_group theo split.
   - filter_benchmark(frame, text_column, splits) -> (kept, dropped) với cột lý do và split gây trùng.
   - admin_group_key(province, district, ward): khóa nhóm đơn vị hành chính (dùng
     src/data/administrative_mapping.py để chuẩn hóa) cho việc chia nhóm rời nhau.
   - Script 65 chạy filter trên Data 01, 03, 04, 06 và ghi exclusion_report.json.
   - Kiểm chứng: số trùng chuỗi chính xác với toàn corpus phải tái lập 20 (Data 01), 21 (03), 21 (04), 20 (06).
     Nếu lệch, dừng và báo số đo được.

3. stats.py (chỉ numpy + thư viện chuẩn; mọi hàm nhận seed)
   - bootstrap_ci(statistic_fn, units, n_resamples=10000, alpha=0.05, seed) — percentile.
   - cluster_bootstrap_ci(statistic_fn, units, cluster_ids, ...) — lấy mẫu lại theo cụm.
   - paired_bootstrap_delta(statistic_fn, units_a, units_b, ...) — cùng chỉ số mẫu cho hai hệ, trả delta, CI,
     tỷ lệ resample có delta <= 0.
   - approximate_randomization(statistic_fn, units_a, units_b, n_permutations=10000, seed) — p hai phía.
   - mcnemar_exact(b, c) — nhị thức chính xác hai phía.
   - Trường hợp biên: n=0, mọi đơn vị giống nhau, một cụm duy nhất -> trả null kèm lý do, không ném lỗi im lặng.
   statistic_fn làm việc trên "đếm theo mẫu" (tp/fp/fn mỗi mẫu) để micro-F1 được tính lại đúng trên mỗi resample;
   không lấy trung bình F1 từng mẫu.

4. Test: tính tất định theo seed; CI bao giá trị thật trên dữ liệu tổng hợp nhỏ; McNemar khớp giá trị tính tay;
   filter_benchmark loại đúng dòng trùng do khác hoa/thường và dấu câu.

XONG KHI: test mới PASS, bộ test cũ không đổi, exclusion_report.json có đủ bốn tập và lý do từng dòng bị loại.
```

---

## WP1 — T2 baseline, E2, E3

```text
NHIỆM VỤ: hiện thực và chấm baseline ánh xạ đơn vị hành chính hai chiều (T2) trên Data 07, kèm phân tích
bất đối xứng (E3), so sánh heuristic mặc định với mô hình dùng tên đường (E2), và phần T2 của H5.
Phụ thuộc: WP0 (src/evaluation/stats.py, leak_guard.py) đã có.

File bạn sở hữu: src/evaluation/t2_lookup.py, src/evaluation/t2_scorer.py, scripts/66_run_t2_baseline.py,
tests/test_t2_baseline.py, data/processed/evaluation/sprint04/t2_baseline_20261014_v1/,
docs/sprints/sprint_04/09_t2_baseline_results.md.

Dữ liệu (chỉ đọc):
- data/processed/benchmark/07_bidirectional_pairs_verified.csv — 600 cặp; cột ID_Node, DiaChi_Cu, DiaChi_Moi,
  LoaiAnhXa, QuanHe, HinhThucSapNhap, MaPhuongXaMoi, Nguon.
- data/processed/gazetteer/s3_v4_nso_dual_snapshot_release2/ — edges.csv (10.597 cạnh; cột old_province,
  old_district, old_ward, new_province, new_ward, new_ward_code, relation, merge_form, source_row),
  entities.csv, aliases.csv, non_atomic_transitions.csv. Kiểm hash theo manifest.json. Có thể tái dùng
  DualSnapshotGazetteer (src/data/nso_dual_snapshot.py) và AdministrativeMapping (src/data/administrative_mapping.py).
- data/processed/benchmark/06_hybrid_addresses_600.csv — cho phần H5.
- data/processed/osm/osm_clean_addresses.csv — cho T2-STREET.

Sự thật đã kiểm, bạn phải xử lý đúng (xem F1–F3 của kế hoạch):
- Data 07 chỉ có LoaiAnhXa M (356) và B (244). A và C trên Data 07 = NOT_EVALUABLE_NO_SUPPORT. Không gộp M vào A.
- Chỉ 23 mã phường mới và 69 đơn vị cũ; 441/600 ở Hà Nội. Bắt buộc bootstrap theo cụm.
- Data 07 được xác minh bằng chính CSV nguồn của edges.csv, nên candidate-recall gần 100% do cấu trúc.
  Accuracy đo việc chọn đúng ứng viên, không đo độ phủ bảng. Viết rõ điều này trong báo cáo.

Hệ thống (ghi vào run_manifest.json trước khi chấm, không thêm/bớt sau khi thấy kết quả):
- T2-LOOKUP-STRICT: tra khóa đầy đủ; trả lời khi đúng một ứng viên; còn lại abstain kèm danh sách ứng viên và mã lý do
  (AMBIGUOUS / NO_MATCH / NON_ATOMIC).
- T2-LOOKUP-DEFAULT: luôn chọn một ứng viên: ưu tiên merge_form "Hợp nhất toàn bộ" > "Tách — nhập chủ yếu" >
  "Tách — một phần"; hòa thì source_row nhỏ nhất. Đây là "heuristic mặc định"; không trả cảnh báo.
- T2-VNADMIN: VietnamAdminUnitsAdapter.convert_to_2025 (src/evaluation/adapters/vnadmin_adapter.py), chỉ cũ→mới.
  Chặn mọi lời gọi geocoder mạng (thay get_geo_location bằng hàm trả None) và ghi nhánh fallback thực tế.
  Chiều mới→cũ: NOT_SUPPORTED, vẫn có dòng trong bảng.
- T2-SINGLE-VERSION: khớp tên phường của địa chỉ nguồn trên gazetteer của HỆ ĐÍCH mà không biết phiên bản
  (mô phỏng hệ thống không có khái niệm thời gian). Trả lời "hợp lệ" nếu tên tồn tại trong tỉnh đích.
- T2-STREET (E2): khi có nhiều ứng viên, chọn ứng viên có tên đường của địa chỉ xuất hiện trong chỉ mục
  (tên đường chuẩn hóa -> tập phường mới) dựng từ osm_clean_addresses.csv SAU KHI loại mọi OSM ID có trong Data 07;
  không có bằng chứng thì rơi về luật mặc định và đánh dấu. Ghi kích thước chỉ mục và tỷ lệ mẫu có bằng chứng.

Điều kiện đầu vào:
(a) oracle-segmentation: tách DiaChi_Cu/DiaChi_Moi theo dấu phẩy từ phải sang (cũ: ..., phường, huyện, tỉnh;
    mới: ..., phường, tỉnh). Kiểm từng dòng khớp khóa gazetteer; báo số dòng không khớp và giữ chúng trong mẫu số.
(b) pipeline: lấy span PhuongXa/QuanHuyen/TinhThanh từ HEUR-JW (cấu hình đã khóa trong
    data/interim/modeling/sprint03/final_completion_20261005_v1/light_test_runs_v2/heur-jw/model_config.json)
    và CRF-INDEP (model_config.json cùng thư mục crf-indep) rồi mới tra. Không huấn luyện lại.

Metric, tách theo chiều (cu_to_moi, moi_to_cu) × LoaiAnhXa × HinhThucSapNhap × hệ thống × điều kiện đầu vào:
- accuracy đơn vị đích trên khóa đầy đủ đã chuẩn hóa (mới: tỉnh+phường, đối chiếu thêm MaPhuongXaMoi;
  cũ: tỉnh+huyện+phường); abstain tính là không đúng trong accuracy toàn bộ, và báo riêng accepted accuracy.
- coverage, abstain rate, candidate recall, số ứng viên trung bình/trung vị.
- silent_error_rate = (trả lời sai và không có cảnh báo/abstain) / tổng số mẫu. Báo cả số tuyệt đối.
- CI 95% cluster bootstrap (cụm = đơn vị nguồn của chiều đang xét), B=10.000, seed 20261014.
- E3: trên cùng 600 cặp, McNemar chính xác và paired bootstrap giữa hai chiều cho từng hệ thống.
- E2: T2-LOOKUP-DEFAULT so với T2-STREET, ghép cặp, tách M (phía 1-nhiều) và B.

Phân tích đồ thị toàn bộ edges.csv (không cần Data 07): phân phối fan-out theo khóa cũ và fan-in theo khóa mới,
tỷ lệ khóa giải được tất định mỗi chiều, tách A/B/C/M, 5 chuyển đổi phi nguyên tử báo riêng. Ghi nhãn
"cận cấu trúc"; không gọi là accuracy quan sát.

Phần T2 của H5:
- Tình huống C: đưa 600 chuỗi Data 06 (qua oracle-segmentation) vào T2-LOOKUP-STRICT, T2-LOOKUP-DEFAULT,
  T2-SINGLE-VERSION theo cả hai giả định hệ nguồn; báo tỷ lệ NO_MATCH, trả lời sai im lặng, trả lời đúng.
  Gold đích suy từ Span_He_Detail + bảng cạnh; dòng nào không suy được duy nhất thì loại khỏi mẫu số và đếm riêng.
- Tình huống D: từ entities/edges, liệt kê tên phường xuất hiện ở cả hai hệ trong cùng tỉnh (sau quy đổi tỉnh)
  nhưng tập cạnh cho thấy phạm vi khác nhau; báo số lượng và tỷ lệ lỗi im lặng của T2-SINGLE-VERSION trên
  các cặp Data 07 thuộc nhóm này.

Đầu ra trong thư mục run: predictions.jsonl (mỗi dòng: ID_Node, chiều, hệ thống, điều kiện, đầu vào đã tách,
ứng viên, trả lời, cờ abstain, đúng/sai, mã lý do), metrics.json, tables/*.csv (utf-8-sig), graph_analysis.json,
run_manifest.json.

Test: phân loại quan hệ trên đồ thị nhỏ dựng tay (1-1, N-1, 1-N, M-N); luật mặc định tất định; STRICT abstain
đúng khi nhiều ứng viên; silent error được đếm đúng; chặn geocoder hoạt động; T2-STREET không đọc ID của Data 07.

Báo cáo 09: bảng T2 chính, bảng E3, bảng E2, bảng tình huống C/D, đoạn phân tích bất đối xứng (đối chiếu giả thuyết
đề cương "chiều mới→cũ khó hơn"), và mục giới hạn nêu F1–F3 cùng việc mã cũ của gazetteer còn partial.

XONG KHI: mọi ô của bảng có số hoặc trạng thái NOT_EVALUABLE/NOT_SUPPORTED; tái chạy cho cùng số; test PASS.
```

---

## WP2 — Đánh giá lại và sửa T1, bảng H5

```text
NHIỆM VỤ: đo T1 (cu / moi / Lai) có hệ thống, tìm nguyên nhân Lai F1 = 0 của PROPOSED-DYN, thử ba biến thể,
và lập bảng H5. Phụ thuộc: WP0.

File bạn sở hữu: src/evaluation/t1_pipeline.py, src/evaluation/t1_situations.py, scripts/67_build_t1_sets.py,
scripts/68_run_t1_evaluation.py, tests/test_t1_group1.py, configs/modeling/sprint04/proposed_dyn_t1aug_v1.json,
data/interim/modeling/sprint04/t1_sets_20261015_v1/, data/processed/evaluation/sprint04/t1_h5_20261015_v1/,
docs/sprints/sprint_04/10_t1_h5_results.md.

Bối cảnh đã kiểm (F4–F8 của kế hoạch):
- Mốc: HEUR-JW test T1 accuracy 92,19% / macro-F1 92,49%; DYN 71,88% / 56,26%, Lai F1 = 0 (support 5), dev Lai F1 = 0.
- Train có 16 Lai / 119 cu / 71 moi; dev 8 Lai. Đầu T1 của DYN là Linear trên CLS (src/modeling/proposed_dynamic.py),
  quyết định qua structure_decision ngưỡng 0,7 / margin 0,2 (src/modeling/structural_decoder.py).
- Data 06: 600 dòng đều Lai, đều loại B; KieuLai C1 420 / C2 120 / C3 60; khoảng 68% Bắc Ninh.
- Test Sprint 3 chứa 20 mẫu lấy từ Data 06 và 20 từ mỗi Data 01/03/04.
- Data 06 để ngõ/hẻm bên trong TenDuong; gold Sprint 3 tách Ngo/Hem. Không dùng thẳng làm nhãn T0.

BƯỚC A — đánh giá, không huấn luyện
1. scripts/67 dựng t1_stress_v1.csv: Data 06 (Lai) + Data 01 (moi) + Data 03 (cu), qua leak_guard loại trùng
   train/dev/test; giữ cột nguồn, KieuLai, tỉnh. Báo số dòng trước/sau lọc từng nguồn.
2. t1_situations.py gán thẻ tình huống theo đề cương mục 1.2, chỉ từ gazetteer edges, dùng ở phía chấm:
   A = mẫu cu có phường nguồn với nhiều đích; B = mẫu moi có phường đích gộp từ nhiều nguồn; C = mẫu Lai;
   D = mẫu có tên phường trùng danh pháp giữa hai hệ trong cùng tỉnh. Một mẫu có thể mang nhiều thẻ;
   mẫu không gán được ghi NONE. Ghi định nghĩa vận hành này vào báo cáo vì đề cương không cho định nghĩa máy đọc.
3. Chạy HEUR-JW (cấu hình đã khóa) trên t1_stress_v1. Chạy DYN checkpoint c02 đã khóa
   (data/interim/modeling/sprint03/release_and_kaggle_20261005_v1/dyn_c02_selection_artifacts_v1/.../checkpoints/best.pt,
   SHA-256 phải bằng 7a4a3d01bff1222cd303cb5ff03872c5ee49b22cb67a0572833fa470f917a589) bằng CPU cục bộ nếu runtime
   neural có sẵn; nếu không chạy được, ghi BLOCKED_LOCAL_RUNTIME và chuẩn bị danh sách đầu vào để gộp vào job Kaggle
   của WP3b. Lưu posterior ba lớp của DYN cho từng mẫu.
4. Báo: ma trận nhầm lẫn (kể cả khong_ro), P/R/F1 từng lớp, accuracy, macro-F1, coverage, abstain; tách theo KieuLai,
   theo thẻ A–D, theo tỉnh; CI cluster bootstrap theo admin_group_key. Thêm chẩn đoán DYN: phân phối posterior của
   lớp Lai trên mẫu Lai, số mẫu Lai có argmax = Lai nhưng bị ngưỡng/margin đẩy sang khong_ro.

BƯỚC B — ba biến thể, chọn chỉ bằng dev Sprint 3 và t1_synth_dev
1. T1-PIPE-<T0>: lấy span hành chính từ prediction T0 của CRF-INDEP / PHOBERT-CRF / DYN, tra hệ của từng span trên
   gazetteer theo đúng luật của HEUR-JW (cu+moi -> Lai; một hệ -> hệ đó; không xác định -> khong_ro). Tái dùng mã
   resolve của HeuristicJaroWinklerAdapter, không sao chép. Trên test dùng prediction đã freeze; không suy luận lại.
2. T1-FEAT: phân loại softmax tuyến tính viết bằng numpy trên đặc trưng: có dấu hiệu cấp huyện, loại tiền tố đơn vị,
   dạng tên tỉnh, thành viên gazetteer của từng đoạn (chỉ cu / chỉ moi / cả hai / không có). L2 cố định, seed 42.
3. DYN-T1-AUG: config proposed_dyn_t1aug_v1.json = proposed_dyn_v1.json c02 đã khóa, chỉ đổi dữ liệu huấn luyện
   (train + t1_synth_train). Không đổi siêu tham số khác. Chuẩn bị gói; KHÔNG submit Kaggle — bàn giao cho chủ dự án
   chạy cùng lượt WP3b. Khi có artifact, chấm theo cùng kịch bản.

Dữ liệu lai tổng hợp (scripts/67):
- Sinh bằng generate_hybrid_addresses (src/data/synthetic/hybrid_address.py) với seed mới 20261015; KHÔNG dùng lại
  600 dòng Data 06 làm dữ liệu huấn luyện.
- Chia t1_synth_train / t1_synth_dev / t1_synth_eval theo mã phường mới sao cho ba phần rời nhóm; loại mọi nhóm
  hành chính và mọi chuỗi xuất hiện trong dev/test Sprint 3; phân tầng theo KieuLai và tỉnh.
- Thêm mẫu cu và moi cùng nhóm địa lý (từ snapshot/địa chỉ sạch, qua leak_guard) để lớp không suy ra được chỉ từ
  "có cấp huyện". Báo tỷ lệ lớp cuối cùng.
- Nhãn T0 cho mẫu tổng hợp: loại dòng có tiền tố ngõ/hẻm/ngách/kiệt trong TenDuong, hoặc tách theo luật guideline
  s3-span-v1.1 rồi kiểm tay 30 dòng ngẫu nhiên (seed cố định) và ghi kết quả kiểm. Căn offset bằng src/data/span_trace.py;
  mẫu căn mơ hồ thì bỏ và đếm.
- Hiệu chỉnh ngưỡng: dev Sprint 3 có 8 Lai (<10) nên CALIBRATION_NOT_EVALUABLE theo protocol. Nếu hiệu chỉnh,
  chỉ dùng lưới 6 tổ hợp của protocol (threshold 0,7/0,8/0,9 × margin 0,1/0,2) trên t1_synth_dev, khai báo trước
  trong run_manifest.json, và báo song song kết quả với ngưỡng gốc 0,7/0,2.

Bảng H5 (báo cáo 10): hàng = HEUR-JW, DYN gốc, T1-PIPE-CRF, T1-PIPE-PCRF, T1-PIPE-DYN, T1-FEAT, DYN-T1-AUG;
cột = test Sprint 3 (64 eligible; nhãn POST_HOC_SECONDARY), t1_synth_eval, t1_stress_v1; mỗi ô có accuracy,
macro-F1, Lai P/R/F1 kèm support, coverage, abstain. Kiểm định ghép cặp so với HEUR-JW bằng stats.py.

Phải viết rõ trong báo cáo:
- Lai của test và dữ liệu tổng hợp cùng một generator: tăng Lai F1 trên test không chứng minh tổng quát sang địa chỉ
  lai do người thật viết.
- Đối chiếu với H5 của đề cương ("mô hình nhận biết phiên bản vượt trội ở lớp lai"): kết luận ủng hộ / không ủng hộ /
  không kết luận được, theo CI.
- Nếu Lai F1 vẫn bằng 0 ở biến thể nào: giải thích bằng số (posterior, ngưỡng, support), không suy đoán.

Test: chia nhóm rời nhau thật sự (không mã phường nào ở hai phần); không chuỗi nào của dev/test lọt vào tập tổng hợp;
luật T1-PIPE cho đúng trên ví dụ dựng tay; thẻ A–D tất định.

XONG KHI: Bước A có đủ bảng; Bước B có số cho các biến thể CPU; DYN-T1-AUG có số hoặc trạng thái PENDING_KAGGLE
kèm gói sẵn sàng; test PASS.
```

---

## WP3 — Độ tin cậy T0/T1

```text
NHIỆM VỤ: (3a) khoảng tin cậy và kiểm định ghép cặp trên prediction Sprint 3 đã freeze; (3b) chuẩn bị và chấm
thí nghiệm đa seed 42/1337/2025 cho hai mô hình neural. Phụ thuộc: WP0.

File bạn sở hữu: scripts/69_bootstrap_frozen_results.py, scripts/70_prepare_multiseed_kaggle.py,
tests/test_group1_reliability.py, configs/modeling/sprint04/phobert_crf_seed{1337,2025}.json,
configs/modeling/sprint04/proposed_dyn_seed{1337,2025}.json, configs/modeling/sprint04/proposed_no_constraint_seed*.json,
data/processed/evaluation/sprint04/reliability_20261014_v1/, data/interim/modeling/sprint04/multiseed_20261015_v1/,
docs/sprints/sprint_04/11_reliability_results.md.

3a — CPU, làm ngay
Đầu vào (chỉ đọc, kiểm SHA-256 với data/interim/modeling/sprint03/final_completion_20261005_v1/all_test_predictions_frozen.json
trước khi tính):
- HEUR-JW, CRF-INDEP: .../final_completion_20261005_v1/light_test_runs_v2/{heur-jw,crf-indep}/predictions.jsonl
- PHOBERT-CRF, PROPOSED-DYN, PROPOSED-NO-CONSTRAINT: .../kaggle_final_output_v4/dacn_artifacts/
  dacn-s3-final-infer-20261005-v4/workspace/data/interim/modeling/sprint03/dacn-s3-final-infer-20261005-v4/
  {pcrf_test,dyn_test,dyn_off_test}/predictions.jsonl
- Gold: data/processed/annotation/sprint03/test_gold_v1_release2/test_benchmark_t0.jsonl; mask T1 lấy từ
  test_evaluation_exclusions trong manifest của corpus_v1_release2 (kỳ vọng 64 eligible / 20 null / 16 excluded).
- Dev: prediction dev của các run đã chọn (đường dẫn trong selection_lock.json từng run) và dev.jsonl.
- Track 5 trường: prediction *_5field trong cùng thư mục output v4 và light runs; 4.800 hàng; ghi rõ là track development.

Bước bắt buộc đầu tiên: dùng compute_exact_span_metrics (src/evaluation/span_scorer.py) tái lập đúng các số đã công bố
(T0 F1: 0,9112 / 0,9076 / 0,9843 / 0,9821 / 0,9843; T1 HEUR 0,9219 / 0,9249; DYN 0,7188 / 0,5626). Lệch bất kỳ số nào
thì dừng và báo, không tính CI.

Tính bằng src/evaluation/stats.py, B=10.000, seed 20261014:
- Mỗi hệ: T0 micro P/R/F1, F1 từng nhãn có support > 0, exact-match cả địa chỉ, T1 accuracy và macro-F1, Lai F1;
  CI 95% bootstrap theo mẫu và theo source_group (báo số cụm; nếu mỗi mẫu là một cụm thì ghi rõ hai CI trùng nhau).
- Cặp: PCRF–DYN, DYN bật–tắt, PCRF–CRF, PCRF–HEUR, CRF–HEUR; với T1: HEUR–DYN. Mỗi cặp: delta, CI ghép cặp,
  p hoán vị xấp xỉ, McNemar chính xác trên exact-match (T0) hoặc đúng/sai (T1).
- Không hiệu chỉnh đa so sánh ngầm: liệt kê số phép so sánh và thêm cột p Holm.
- Ghi chú độ nhạy: với 100 mẫu / 446 span, hiệu nhỏ nhất phát hiện được ước lượng từ độ rộng CI ghép cặp.

3b — đa seed
1. Tạo config overlay theo seed từ configs/modeling/sprint03/{phobert_crf_v1,proposed_dyn_v1,proposed_no_constraint_v1}.json
   với ứng viên c02 đã khóa; chỉ đổi seed và run_id. src/modeling/cli.py không có --seed nên seed phải nằm trong config.
   Test khẳng định overlay chỉ khác bản gốc ở seed/run_id.
2. Seed 42: dùng lại run đã khóa, không huấn luyện lại. CRF-INDEP: L-BFGS tất định -> DETERMINISTIC_SEED_INVARIANT,
   một dòng, không std. HEUR-JW: một cấu hình cố định.
3. Dựng gói Kaggle bằng hạ tầng hiện có (scripts/50_kaggle_pipeline.py, 51_run_kaggle_remote.py, src/modeling/kaggle_*.py),
   mỗi model/seed một job tuần tự; DYN tắt ràng buộc dùng lại trọng số và calibration của DYN bật cùng seed.
   Ước lượng GPU-giờ từ log thời gian thực của các run c02 Sprint 3 và ghi vào kế hoạch chạy.
4. DỪNG tại đây và hỏi chủ dự án: quota GPU đọc trên giao diện Kaggle, đồng ý upload. Không tự upload/submit.
   Thứ tự ưu tiên nếu quota thiếu: PCRF-1337, DYN-1337, (DYN-T1-AUG của WP2), PCRF-2025, DYN-2025.
5. Sau khi có artifact: kiểm hash checkpoint/prediction, chọn epoch theo quy tắc dev đã khóa
   (full11 dev micro F1 -> gold-supported macro -> epoch sớm), suy luận test text-only, khóa prediction, rồi mới chấm
   đúng một lần mỗi seed.
6. Báo từng seed và mean ± std (ddof=1) cho T0 micro F1, T1 accuracy/macro-F1/Lai F1 trên dev và test; delta
   PCRF–DYN và bật–tắt theo từng seed; thiếu seed ghi n thực và PARTIAL_SEEDS. Không báo riêng seed tốt nhất.

Báo cáo 11: bảng CI, bảng kiểm định ghép cặp, bảng seed, và kết luận viết theo CI ("không phân biệt được" khác
"tương đương"). Nêu giới hạn: một bộ test 100 mẫu, đã bị quan sát, gold một người gán có AI hỗ trợ.

Test: tái lập điểm công bố trên fixture nhỏ; CI tất định theo seed; overlay config đúng; mask T1 64/20/16.

XONG KHI: 3a đầy đủ và tái lập; 3b có số hoặc trạng thái PENDING_KAGGLE / PARTIAL_SEEDS kèm gói và lệnh chạy.
```

---

## WP4 — Thí nghiệm CPU: H2, H3, E1, H4

```text
NHIỆM VỤ: bốn thí nghiệm chi phí thấp trên CPU với CRF-INDEP (và HEUR-JW ở các phép nhiễu lúc test). Bốn bảng nhỏ,
kể cả kết quả âm. Phụ thuộc: WP0.

File bạn sở hữu: src/evaluation/perturbations.py, scripts/71_run_cpu_hypothesis_experiments.py,
tests/test_group1_cpu_experiments.py, data/processed/evaluation/sprint04/cpu_hypotheses_20261015_v1/,
docs/sprints/sprint_04/12_cpu_hypothesis_results.md.

Nền chung:
- Corpus: data/processed/annotation/sprint03/corpus_v1_release2 (240/60/100). Chỉ đọc.
- CRF: tái dùng encode_gold/token_features/decode_bio (src/evaluation/span_features.py) và cách huấn luyện ở
  scripts/26_train_independent_crf.py. Giữ NGUYÊN siêu tham số đã chọn ở Sprint 3 (đọc context/c1/c2/feature_version từ
  .../final_completion_20261005_v1/light_test_runs_v2/crf-indep/model_config.json và metadata đi kèm) cho mọi điều kiện;
  không dò lưới lại theo điều kiện. Bước kiểm đầu tiên: huấn luyện lại ở điều kiện gốc phải tái lập test T0 F1 0,9076;
  nếu lệch, báo độ lệch và dùng run tái lập làm mốc ghép cặp.
- Mọi so sánh dùng paired bootstrap và CI từ src/evaluation/stats.py; chấm bằng compute_exact_span_metrics.
- Test Sprint 3 đã bị quan sát: mọi kết quả ở đây là phân tích độ bền hậu nghiệm, không dùng để chọn cấu hình.

H3 — xáo thứ tự trường (perturbations.py: recompose_with_order)
- Từ gold span của test, dựng lại chuỗi: nối văn bản các span bằng ", " theo (i) thứ tự gốc [đối chứng],
  (ii) đảo ngược (lớn -> nhỏ), (iii) ba hoán vị ngẫu nhiên seed 42/1337/2025. Tính lại offset; kiểm
  text[start:end] == nguyên văn span cho 100% span.
- Văn bản ngoài span bị bỏ khi dựng lại: báo số ký tự/mẫu bị ảnh hưởng. Vì vậy mọi so sánh lấy (i) làm mốc,
  không lấy chuỗi nguyên bản.
- Chạy CRF-INDEP và HEUR-JW (chỉ suy luận). Ghi danh sách chuỗi đầu vào để phiên khác chạy mô hình neural nếu có GPU;
  ô neural ghi NOT_RUN.
- Báo F1 từng điều kiện, độ sụt so với (i), F1 từng nhãn. Đối chiếu Yassine et al. (rơi về 28% trên tiếng Hàn).

E1 — tiền xử lý 2×2: giữ/bỏ dấu phẩy × giữ/hạ chữ hoa
- Biến đổi có ánh xạ offset khả nghịch (bỏ dấu phẩy: thay bằng khoảng trắng đơn rồi gộp; hạ chữ: str.lower giữ độ dài,
  kiểm độ dài không đổi với tiếng Việt, mẫu đổi độ dài thì loại và đếm).
- Hai chế độ: (a) chỉ nhiễu lúc test với mô hình gốc; (b) huấn luyện và test cùng điều kiện (4 lần huấn luyện CRF).
- HEUR-JW chỉ ở chế độ (a). Báo bảng 2×2 cho từng chế độ.

H2 — huấn luyện kèm địa chỉ thiếu trường
- Nguồn tăng cường: data/processed/benchmark/04_missing_fields_800.csv qua leak_guard (loại trùng dev/test theo chuỗi
  và admin_group_key). Căn span bằng src/data/span_trace.py từ các cột bề mặt SoNha/TenDuong/PhuongXa/QuanHuyen/TinhThanh;
  căn mơ hồ thì bỏ và đếm.
- BẪY NHÃN: Data 04 để ngõ/hẻm trong TenDuong, gold tách Ngo/Hem. Loại mọi dòng có TenDuong bắt đầu bằng
  ngõ/hẻm/ngách/kiệt khỏi tập tăng cường. Báo số dòng loại.
- Chia Data 04 còn lại theo admin_group_key: aug_train và heldout_missing (rời nhóm). N tăng cường = 120 và 240.
- Ba mô hình: BASE (240 train); AUG-MISSING (240 + N thiếu trường); AUG-FULL (240 + N địa chỉ đầy đủ cùng nguồn gốc,
  lấy từ Data 01/03 qua cùng quy trình) để tách tác dụng "thêm dữ liệu" khỏi "thêm mẫu thiếu trường".
- Đánh giá: (i) heldout_missing bằng scorer 5 trường (src/evaluation/scorer.py) với GT_* làm silver, tách theo KieuThieu;
  (ii) 20 mẫu test có source_dataset = 04_missing (lấy từ identity_registry) và 80 mẫu còn lại, bằng scorer span;
  (iii) dev để kiểm không suy giảm. Ghi rõ (i) là silver từ generator, (ii) chỉ có 20 mẫu.
- Đối chiếu H2 của đề cương (tụt 20–40%, phục hồi sau khi thêm dữ liệu thiếu): báo có tụt không, có phục hồi không.

H4 — theo nhóm loại địa điểm (không huấn luyện)
- Nhóm: hành chính = PhuongXa, QuanHuyen, TinhThanh; đường sá = SoNha, TenDuong, Ngo/Hem; mốc = MocDinhVi, HuongDi;
  khác = ToaNha/CanHo, GhiChu, Khac. Đề cương nói "bốn nhóm loại địa điểm" nhưng không định nghĩa: ghi rõ đây là
  định nghĩa vận hành của bạn.
- Từ prediction test đã freeze của 5 hệ (đường dẫn như WP3): micro P/R/F1 từng nhóm + CI, và delta ghép cặp
  hành chính − đường sá trong từng hệ.
- Nhóm mốc: support test = 0 -> NOT_EVALUABLE_NO_GOLD_SUPPORT. Bổ sung số tham khảo bằng group k-fold (k=5, nhóm theo
  source_group, seed 42) của CRF trên 240 train, ghi LOW_SUPPORT kèm support thực (5–6 span mỗi nhãn) và không kết luận.

Báo cáo 12: bốn bảng, mỗi bảng có một dòng kết luận dạng "ủng hộ / không ủng hộ / không kết luận được" theo CI,
và mục giới hạn. Không gộp thành một điểm tổng.

Test: mọi phép biến đổi giữ đúng offset (property test trên toàn bộ train+dev); hoán vị tất định theo seed; dòng có
ngõ/hẻm bị loại; aug_train và heldout_missing rời nhóm; không chuỗi dev/test nào trong tập tăng cường.

XONG KHI: bốn bảng có số hoặc trạng thái; tái chạy cho cùng số; test PASS.
```

---

## WP5 — Ablation ràng buộc và tuyên bố H1

```text
NHIỆM VỤ: thay cho ablation adapter mà đề cương hứa (H1) bằng ablation trung thực của thứ đã được hiện thực:
đầu T1 + giải mã có ràng buộc. Phụ thuộc: WP3 (CI, đa seed) và WP2 (T1 biến thể, t1_stress_v1).

File bạn sở hữu: scripts/72_run_constraint_ablation.py, tests/test_group1_constraint_ablation.py,
data/processed/evaluation/sprint04/constraint_ablation_20261017_v1/, docs/sprints/sprint_04/13_constraint_ablation_and_h1.md.

Bối cảnh đã kiểm: trên test, bật ràng buộc đổi 1 mẫu / 2 span (s3_224ae519b196f730: QuanHuyen -> PhuongXa), T0 F1
giảm 0,22 điểm; lỗi QuanHuyen trên mẫu moi là 0/12 ở cả hai chế độ. Ràng buộc chỉ kích hoạt khi T1 tự tin dự đoán
"moi" và khi đó cấm nhãn QuanHuyen (src/modeling/structural_decoder.py).

1. Ghép cặp bật/tắt (cùng checkpoint, cùng calibration, cùng đầu vào) trên: test, dev, track 5 trường (4.800 hàng),
   từng seed của WP3b nếu có, và phần moi của t1_stress_v1. Dùng prediction có sẵn; chỉ suy luận thêm khi chưa có
   và runtime cục bộ cho phép, nếu không ghi PENDING_INFERENCE kèm danh sách đầu vào.
   Mỗi tập: số mẫu thay đổi, số span thay đổi, phân loại từng thay đổi (sửa đúng / làm sai / trung tính), delta F1
   và CI ghép cặp (src/evaluation/stats.py), tỷ lệ kích hoạt ràng buộc.
2. Dư địa: trên mỗi tập, đếm mẫu gold moi (không có gold QuanHuyen) mà chế độ tắt dự đoán QuanHuyen. Đây là số lỗi
   tối đa ràng buộc có thể sửa. Nếu bằng 0, viết đúng như vậy: ràng buộc không có gì để sửa trên tập đó.
3. Ablation nguồn T1 cho ràng buộc, áp ở bước hậu xử lý trên prediction tắt-ràng-buộc khi có đủ thông tin, hoặc bằng
   giải mã lại nếu có emission: (a) T1 của DYN; (b) T1 của HEUR-JW; (c) T1 gold = ORACLE. Ghi nhãn (c) là cận trên,
   không phải kết quả mô hình, không đưa vào bảng so sánh mô hình. Nếu chỉ làm được hậu xử lý (xóa/đổi nhãn span
   QuanHuyen) thay vì Viterbi có ràng buộc, nêu rõ đây là xấp xỉ và khác gì.
4. So mask T1 với ràng buộc: bảng 2×2 {có/không đầu T1 trong huấn luyện} × {có/không ràng buộc khi giải mã} từ các run
   đã có: PHOBERT-CRF (không T1, không ràng buộc), PROPOSED-NO-CONSTRAINT (có T1, không ràng buộc), PROPOSED-DYN (có, có).
   Ô (không T1, có ràng buộc) chỉ điền được với T1 ngoài (HEUR hoặc oracle) từ mục 3; ghi rõ nguồn.
   Lưu ý: PCRF và DYN là hai lần huấn luyện khác nhau, nên chênh lệch giữa chúng gồm cả phương sai seed —
   dùng std của WP3b để diễn giải.

Mục trung thực bắt buộc trong báo cáo 13:
- H1 (type adapter / gazetteer adapter) = NOT_TESTABLE: không có adapter nào được hiện thực trong repo. Liệt kê cái
  đề cương hứa (mục 4.1: PhoBERT + gazetteer adapter đa phiên bản + type adapter + global pointer) so với cái đã có
  (PhoBERT + CRF + đầu T1 tuyến tính + ràng buộc giải mã theo confidence).
- Ablation ở đây không phải bằng chứng ủng hộ hay bác bỏ H1.
- Kết luận về ràng buộc theo đúng số: có lợi / có hại / không quan sát được tác dụng, kèm dư địa.
- Hướng ĐATN: điều kiện cần để H1 kiểm được.

Test: phân loại thay đổi đúng trên ví dụ dựng tay; oracle không bao giờ xuất hiện trong bảng mô hình; đếm dư địa
tái lập 0/12 trên test.

XONG KHI: bảng ghép cặp trên mọi tập có sẵn, bảng dư địa, bảng 2×2, mục H1; test PASS.
```

---

## WP6 — Tổng hợp và cập nhật tài liệu

```text
NHIỆM VỤ: gom kết quả Nhóm 1 thành một báo cáo ngắn và cập nhật tài liệu trạng thái. Chạy sau khi WP1–WP5 đã báo xong
(hoặc đã có trạng thái cuối cùng).

File bạn sở hữu: scripts/73_generate_group1_report.py, docs/sprints/sprint_04/14_group1_summary.md,
docs/sprints/sprint_04/README.md, docs/data_quality.md, README.md, AGENTS.md (chỉ mục 5 phần danh sách script/module
mới và mục 9 trạng thái).

1. Script 73 đọc metrics.json và run_manifest.json của các run trong data/processed/evaluation/sprint04/ và sinh các
   bảng của báo cáo 14. Không chép số bằng tay; mọi số trong báo cáo phải truy được về một file metrics.
2. Kiểm chéo trước khi viết: mỗi số trong các báo cáo 09–13 khớp với metrics.json tương ứng; mọi run có run_manifest
   với hash đầu vào còn khớp file hiện tại. Lệch thì ghi vào mục "Sai lệch phát hiện", không tự sửa báo cáo của WP khác.
3. Báo cáo 14 (tối đa khoảng 2 trang):
   - Bảng giả thuyết: H1–H5, E1–E4 × trạng thái (SUPPORTED / NOT_SUPPORTED / INCONCLUSIVE / NOT_TESTABLE / NOT_RUN) ×
     bằng chứng (đường dẫn) × cỡ mẫu. E4 = NOT_RUN (VQA đang HOLD).
   - Bảng T0/T1/T2 hợp nhất kèm CI và mean ± std.
   - Mục "Đe dọa tính hợp lệ": test 100 mẫu đã bị quan sát; gold một người gán có AI hỗ trợ, IAA chưa đo; Data 07 chỉ có
     B/M và tập trung Hà Nội; tính vòng lặp bảng–benchmark ở T2; dữ liệu lai cùng generator; nhãn hiếm không có support.
   - Việc còn lại cho Nhóm 2 và 3.
4. Cập nhật docs/data_quality.md (T2 không còn "chưa thực thi"; nêu giới hạn), README, mục 9 của AGENTS.md
   (trạng thái Sprint 4 Nhóm 1, đường dẫn kết quả). Không sửa nội dung Sprint 3.
5. Chạy toàn bộ bộ test và ghi số PASS/SKIP/FAIL vào báo cáo.

Không commit. Kết thúc bằng danh sách file đã đổi để chủ dự án rà và tự commit.
```
