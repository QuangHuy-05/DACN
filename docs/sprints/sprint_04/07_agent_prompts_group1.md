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
10. Git: KHÔNG chạy `git status`, `git add`, `git diff` từ WSL để kết luận về thay đổi. Git của WSL không có
   core.autocrlf nên báo khoảng 90 file "bị sửa" giả (gold, gazetteer, tài liệu Sprint 3) chỉ do khác ký tự xuống dòng.
   Kiểm thay đổi bằng git của Windows (Git Bash/PowerShell tại D:\DACN) và kiểm file được bảo vệ bằng SHA-256 theo manifest.
11. Kết quả WP0 đã nghiệm thu (13/10/2026), dùng lại, không viết lại: src/evaluation/stats.py (bootstrap_ci,
   cluster_bootstrap_ci, paired_bootstrap_delta có cluster_ids, approximate_randomization, mcnemar_exact,
   micro_f1_from_counts, exact_match_rate) và src/evaluation/leak_guard.py (normalize_for_overlap, build_exclusion_index,
   filter_benchmark, admin_group_key). Giới hạn đã đo của admin_group_key: tên không có tiền tố hành chính
   ("Đa Tốn" thay vì "Xã Đa Tốn") rơi vào khóa UNRESOLVED|..., khi đó dạng cũ và dạng mới của cùng lãnh thổ KHÔNG được
   gom chung — Data 03: 879/1500 dòng, Data 04: 223/800, Data 06: 1/600, Data 01: 0. Mọi phép chia nhóm rời nhau chỉ
   được dùng các dòng có khóa ADM|...; dòng UNRESOLVED chỉ dùng cho đánh giá, không đưa vào huấn luyện, và phải đếm.

Trước khi báo xong: chạy `python -m unittest discover -s tests -v` (toàn bộ; mốc đo ngày 13/10/2026 sau WP1
trong ~/.venv_dacn là 349 test: 341 PASS / 8 SKIP / 0 FAIL — không được có FAIL và không được làm giảm số PASS cũ),
chạy script của bạn từ đầu trên thư mục đầu ra mới để chứng minh tái lập, kiểm số dòng/cột/encoding/bản ghi trùng
của mọi CSV đầu ra.

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
- data/processed/benchmark/01_full_address_new_verified.csv và data/interim/osm/osm_latest_clean.csv — cho T2-STREET
  (data/processed/osm/osm_clean_addresses.csv chỉ có 1.500 dòng, không có OSM ID; không dùng làm nguồn chính).
- src/data/administrative_alias.py — alias đã kiểm chứng cho mức chuẩn hóa N2.

Sự thật đã kiểm trên repo ngày 13/10/2026, bạn phải xử lý đúng (xem F1–F3 của kế hoạch). Bước đầu tiên của bạn là
tái lập các số này; số nào lệch thì dừng và báo trước khi viết hệ thống:
- Data 07 chỉ có LoaiAnhXa M (356) và B (244). A và C trên Data 07 = NOT_EVALUABLE_NO_SUPPORT. Không gộp M vào A.
- Chỉ 23 mã phường mới và 69 đơn vị cũ; 441/600 ở Hà Nội. Bắt buộc bootstrap theo cụm.
  Cụm = khóa đơn vị nguồn của chiều đang xét (69 đơn vị cũ hoặc 23 phường mới), KHÔNG dùng admin_group_key: theo
  thành phần liên thông Data 07 chỉ có 21 nhóm và một nhóm chiếm 73,5% số cặp, CI sẽ vô nghĩa. Báo thêm một bảng độ
  nhạy với cụm = admin_group_key và ghi rõ số cụm ở mọi CI.
- Data 07 được xác minh bằng chính CSV nguồn của edges.csv (qua alias đã kiểm chứng). Vì vậy với chuẩn hóa đủ mạnh,
  candidate-recall tiến tới 100% do cấu trúc; phần còn lại của accuracy đo việc chọn đúng ứng viên, không đo độ phủ
  bảng. Viết rõ điều này trong báo cáo.
- Phía CŨ của Data 07 là chuỗi OSM thô, KHÔNG phải tên chuẩn (đo ngày 13/10/2026):
  · tỉnh cũ viết "Hà Nội" (435), "Bắc Ninh" (148), "Thành phố Hà Nội" (4), "Ho Chi Minh City" (3), "Bac Ninh" (2)...,
    trong khi edges.csv ghi "Thành phố Hà Nội", "Tỉnh Bắc Ninh";
  · so chuỗi thô (tỉnh, huyện, phường) với edges.csv chỉ khớp 5/600; qua chuẩn hóa của AdministrativeMapping
    (old_key/province_key/unit_key) khớp 535/600; 65 dòng còn lại (52 B, 13 M) cần alias đã kiểm chứng hoặc là NO_MATCH;
  · phía MỚI khớp chuỗi thô 600/600.
  Hệ quả: mức chuẩn hóa tên là một yếu tố thí nghiệm thật, phải báo riêng (xem "Mức chuẩn hóa").
- Fan-out cũ→mới đo qua AdministrativeMapping: M có 299 dòng với 4 đích, 44 dòng với 2 đích, 13 dòng không khớp;
  B có 192 dòng với 1 đích, 52 dòng không khớp. Tức 343/600 cặp có nhiều ứng viên ở chiều cũ→mới.
- Tách theo dấu phẩy: 598 dòng có 5 hoặc 4 phần (cũ) / 4 hoặc 3 phần (mới); 2 dòng có dấu phẩy thừa trong phần
  đầu (9 và 6 phần). Luôn lấy từ phải sang: cũ = [-1] tỉnh, [-2] huyện, [-3] phường; mới = [-1] tỉnh, [-2] phường.
- Có hai bảng cạnh: gazetteer edges.csv (10.597 cạnh phường nguyên tử) và CSV tham chiếu nạp qua
  load_administrative_mapping(default_mapping_path()) (10.602 = thêm 5 chuyển đổi phi nguyên tử; NewUnit có các trường
  province, ward, unit_type, code, merger_form; có sẵn old_to_new và new_to_old). Bảng tra chính thức của T2 là
  edges.csv; dùng hàm chuẩn hóa của administrative_mapping.py và đối chiếu chéo số cạnh với AdministrativeMapping
  (chênh lệch kỳ vọng đúng 5 dòng phi nguyên tử, lệch khác thì dừng và báo).
- merge_form theo quan hệ: B và C luôn "Hợp nhất toàn bộ"; M gồm "Tách — một phần" (562) và "Tách — nhập chủ yếu" (468);
  A có 3 cạnh "Tách — nhập chủ yếu".

Hệ thống (ghi vào run_manifest.json trước khi chấm, không thêm/bớt sau khi thấy kết quả):
- T2-LOOKUP-STRICT: tra khóa đầy đủ; trả lời khi đúng một ứng viên; còn lại abstain kèm danh sách ứng viên và mã lý do
  (AMBIGUOUS / NO_MATCH / NON_ATOMIC).
- T2-LOOKUP-DEFAULT-MAIN: luôn chọn một ứng viên: ưu tiên merge_form "Hợp nhất toàn bộ" > "Tách — nhập chủ yếu" >
  "Tách — một phần"; hòa thì source_row nhỏ nhất. Không trả cảnh báo.
- T2-LOOKUP-DEFAULT-FIRST: luôn chọn ứng viên có source_row nhỏ nhất, không nhìn merge_form. Không trả cảnh báo.
  Hai biến thể này cùng là "heuristic mặc định"; báo cả hai vì 335/356 cặp M của Data 07 có HinhThucSapNhap
  "Tách — nhập chủ yếu", nên DEFAULT-MAIN có thể được lợi từ cách Data 07 được lấy mẫu. Không chọn biến thể đẹp hơn.
- T2-VNADMIN: VietnamAdminUnitsAdapter.convert_to_2025 (src/evaluation/adapters/vnadmin_adapter.py), chỉ cũ→mới,
  nhận nguyên chuỗi DiaChi_Cu. Chặn mạng: TRƯỚC khi tạo/gọi adapter, gán
  `vietnamadminunits.converter.converter_2025.get_geo_location = lambda address: None` (adapter bọc đúng symbol này nên
  sẽ bọc hàm giả); test khẳng định không có socket nào được mở. Khi đó trace ghi geocoder_status = "empty" và
  selection_path = "divided_default_after_geocoder_unavailable" hoặc "divided_default_without_street" — đó chính là
  nhánh "heuristic mặc định" của thư viện; báo tỷ lệ từng selection_path. Thư viện không trả mã phường: so khớp bằng
  (tỉnh, phường) đã chuẩn hóa, và báo số dòng trả về rỗng/lỗi. Thư viện chỉ có trong ~/.venv_dacn.
  Chiều mới→cũ: NOT_SUPPORTED, vẫn có dòng trong bảng.
- T2-SINGLE-VERSION: khớp tên phường của địa chỉ nguồn trên gazetteer của HỆ ĐÍCH mà không biết phiên bản
  (mô phỏng hệ thống không có khái niệm thời gian). Trả lời "hợp lệ" nếu tên tồn tại trong tỉnh đích.
- T2-STREET (E2): khi có nhiều ứng viên, chọn ứng viên có tên đường của địa chỉ xuất hiện trong chỉ mục
  (tên đường chuẩn hóa -> tập phường mới); không có bằng chứng thì rơi về luật mặc định và đánh dấu.
  Nguồn chỉ mục: data/processed/benchmark/01_full_address_new_verified.csv (1.000 dòng) và
  data/interim/osm/osm_latest_clean.csv (cột SoNha, TenDuong, PhuongXa, QuanHuyen, TinhThanh, ChuoiDiaChi; lưu ý tên
  phường mới đôi khi nằm ở cột QuanHuyen — chỉ nhận dòng có đúng một giá trị khớp một phường mới trong edges.csv).
  KHÔNG nguồn nào có OSM ID, nên không thể loại theo ID. Chống rò rỉ bằng chuỗi, báo cả hai biến thể:
  (i) loại mọi dòng có ChuoiDiaChi chuẩn hóa (normalize_for_overlap) bằng một DiaChi_Moi của Data 07;
  (ii) nghiêm ngặt: loại thêm mọi dòng trùng cặp (số nhà, tên đường) với bất kỳ cặp nào của Data 07.
  Data 07 có 153 tên đường khác nhau. Ghi kích thước chỉ mục sau lọc, tỷ lệ mẫu có bằng chứng, và nêu giới hạn:
  hàng xóm cùng đường do cùng người đóng góp OSM vẫn có thể còn trong chỉ mục. Đây là mục [Nên]; nếu tỷ lệ có bằng
  chứng dưới 20% thì báo NOT_EVALUABLE_LOW_EVIDENCE kèm số, không diễn giải.

Mức chuẩn hóa tên (yếu tố thí nghiệm, áp cho các hệ T2-LOOKUP-*; khai báo trước trong run_manifest.json):
- N0: so chuỗi thô sau khi chỉ strip khoảng trắng.
- N1: khóa chuẩn hóa của administrative_mapping.py (old_key / new_key / resolve_new_province).
- N2: N1, nếu không khớp thì thử alias đã kiểm chứng của src/data/administrative_alias.py
  (resolve_province_alias / resolve_district_alias / resolve_ward_alias). Không tự sinh alias, không khớp mờ.
Bảng chính báo ở N2; N0 và N1 báo trong một bảng độ nhạy (coverage, accuracy, NO_MATCH). Dòng không khớp khóa là
NO_MATCH = thất bại CÓ cảnh báo, không tính là lỗi im lặng, và luôn nằm trong mẫu số.

Điều kiện đầu vào:
(a) oracle-segmentation: tách DiaChi_Cu/DiaChi_Moi theo dấu phẩy từ phải sang (cũ: ..., phường, huyện, tỉnh;
    mới: ..., phường, tỉnh). Báo số dòng không khớp khóa ở từng mức N0/N1/N2 và giữ chúng trong mẫu số.
(b) pipeline: lấy span PhuongXa/QuanHuyen/TinhThanh từ mô hình rồi mới tra ở mức N2. Không huấn luyện lại.
    · HEUR-JW: cấu hình đã khóa trong data/interim/modeling/sprint03/final_completion_20261005_v1/light_test_runs_v2/
      heur-jw/model_config.json — adapter_kwargs: gazetteer_dir data/processed/gazetteer/s3_v4_nso_dual_snapshot
      (bản KHÔNG phải release2; giữ nguyên như đã khóa), similarity_threshold 0.86, ambiguity_margin 0.02,
      temporal_policy dual_snapshot. Chạy trong ~/.venv_dacn.
    · CRF-INDEP: checkpoint data/processed/evaluation/sprint03/crf_followup_20261003_v1/ctx1_c10.1_c21/model.crfsuite
      và model_metadata.json cùng thư mục (kiểm SHA-256 theo model_config.json của crf-indep). Suy luận phải chạy
      thành tiến trình riêng trong runtime CRF (không có numpy/pandas), ghi spans ra JSONL, rồi bước tra bảng đọc lại.
    · Thiếu span cấp nào thì tra với phần còn lại theo đúng luật STRICT (thường thành AMBIGUOUS/NO_MATCH) và đếm.

Thứ tự ưu tiên (làm và báo theo tầng; tầng sau không được làm chậm tầng trước):
- Tầng 1 (bắt buộc): STRICT, DEFAULT-MAIN, DEFAULT-FIRST × oracle-segmentation × N2 × hai chiều; E3; phân tích đồ thị.
- Tầng 2 (bắt buộc): bảng độ nhạy N0/N1; T2-VNADMIN; T2-SINGLE-VERSION; tình huống C và D.
- Tầng 3 (nên): điều kiện pipeline (HEUR-JW, CRF-INDEP); T2-STREET (E2). Chưa làm thì ghi NOT_RUN, không bỏ trống.

Metric, tách theo chiều (cu_to_moi, moi_to_cu) × LoaiAnhXa × HinhThucSapNhap × hệ thống × điều kiện đầu vào:
- accuracy đơn vị đích trên khóa đầy đủ đã chuẩn hóa (mới: tỉnh+phường, đối chiếu thêm MaPhuongXaMoi;
  cũ: tỉnh+huyện+phường); abstain tính là không đúng trong accuracy toàn bộ, và báo riêng accepted accuracy.
- coverage, abstain rate, candidate recall, số ứng viên trung bình/trung vị.
- silent_error_rate = (trả lời sai và không có cảnh báo/abstain) / tổng số mẫu. Báo cả số tuyệt đối.
- CI 95% cluster bootstrap (cụm = đơn vị nguồn của chiều đang xét), B=10.000, seed 20261014.
- Ngoài accuracy theo cặp (micro), báo accuracy trung bình theo đơn vị nguồn (macro: mỗi đơn vị cũ/phường mới một
  phiếu) vì 299 cặp M đến từ số ít đơn vị có 4 đích; nêu số đơn vị và số cặp của đơn vị lớn nhất.
- E3: trên cùng 600 cặp, McNemar chính xác và paired bootstrap giữa hai chiều cho từng hệ thống.
- E2: T2-LOOKUP-DEFAULT-MAIN và T2-LOOKUP-DEFAULT-FIRST so với T2-STREET, ghép cặp, tách M (phía 1-nhiều) và B.

Phân tích đồ thị toàn bộ edges.csv (không cần Data 07): phân phối fan-out theo khóa cũ và fan-in theo khóa mới,
tỷ lệ khóa giải được tất định mỗi chiều, tách A/B/C/M, 5 chuyển đổi phi nguyên tử báo riêng. Ghi nhãn
"cận cấu trúc"; không gọi là accuracy quan sát.

Phần T2 của H5:
- Tình huống C: đưa 600 chuỗi Data 06 vào T2-LOOKUP-STRICT, T2-LOOKUP-DEFAULT-MAIN, T2-LOOKUP-DEFAULT-FIRST, T2-SINGLE-VERSION. Dùng các cột
  PhuongXa/QuanHuyen/TinhThanh có sẵn làm phân đoạn oracle. Hệ thống KHÔNG được đọc Span_He_Detail hay KieuLai.
  Gold chỉ định nghĩa cho đích hệ MỚI (tỉnh mới + phường mới): C1/C2 có phường đã là phường mới (540 dòng, đều tra
  được), C3 có phường cũ với đúng một đích (59 dòng; 1 dòng không có đích -> loại khỏi mẫu số và đếm riêng).
  Chiều về hệ cũ không có gold duy nhất (N-1) nên ghi NOT_EVALUABLE_NO_UNIQUE_GOLD.
  Chạy hai giả định hệ nguồn mà một hệ thống tra bảng buộc phải chọn: "coi là cũ" và "coi là mới". Đã đo: 421/600
  chuỗi lai vẫn KHỚP khi tra như một khóa cũ đầy đủ (tên phường mới trùng tên một phường cũ trong cùng huyện) — đây là
  đường dẫn tới lỗi im lặng; với mỗi giả định báo: NO_MATCH, khớp-và-đúng, khớp-và-sai (im lặng), tách theo KieuLai.
- Tình huống D: từ entities/edges, liệt kê tên phường xuất hiện ở cả hai hệ trong cùng tỉnh (sau quy đổi tỉnh)
  nhưng tập cạnh cho thấy phạm vi khác nhau; báo số lượng và tỷ lệ lỗi im lặng của T2-SINGLE-VERSION trên
  các cặp Data 07 thuộc nhóm này.

Đầu ra trong thư mục run: predictions.jsonl (mỗi dòng: ID_Node, chiều, hệ thống, điều kiện, đầu vào đã tách,
ứng viên, trả lời, cờ abstain, đúng/sai, mã lý do), metrics.json, tables/*.csv (utf-8-sig), graph_analysis.json,
run_manifest.json.

Test: phân loại quan hệ trên đồ thị nhỏ dựng tay (1-1, N-1, 1-N, M-N); luật mặc định tất định; STRICT abstain
đúng khi nhiều ứng viên; silent error được đếm đúng; chặn geocoder hoạt động; chỉ mục T2-STREET sau lọc không chứa chuỗi DiaChi_Moi nào của Data 07; ba mức N0/N1/N2
cho đúng số khớp đã đo (N0 = 5/600, N1 = 535/600 ở phía cũ).

Báo cáo 09: bảng T2 chính, bảng E3, bảng E2, bảng tình huống C/D, đoạn phân tích bất đối xứng (đối chiếu giả thuyết
đề cương "chiều mới→cũ khó hơn"), và mục giới hạn nêu F1–F3 cùng việc mã cũ của gazetteer còn partial.

XONG KHI: mọi ô của bảng có số hoặc trạng thái NOT_EVALUABLE/NOT_SUPPORTED; tái chạy cho cùng số; test PASS.
```

---

## WP2 — Đánh giá lại và sửa T1, bảng H5

```text
NHIỆM VỤ: đo T1 (cu / moi / Lai) có hệ thống, tìm nguyên nhân Lai F1 = 0 của PROPOSED-DYN bằng số liệu, thử các biến
thể rẻ, và lập bảng H5. Phụ thuộc: WP0 (stats.py, leak_guard.py) và WP1 (t2_lookup.py — chỉ đọc/tái dùng, không sửa).

File bạn sở hữu: src/evaluation/t1_pipeline.py, src/evaluation/t1_situations.py, scripts/67_build_t1_sets.py,
scripts/68_run_t1_evaluation.py, scripts/68b_run_t1_neural_local.py, tests/test_t1_group1.py,
data/interim/modeling/sprint04/t1_sets_20261015_v1/, data/processed/evaluation/sprint04/t1_h5_20261015_v1/,
docs/sprints/sprint_04/10_t1_h5_results.md. Không sửa bất kỳ file nào trong src/modeling/ hay configs/.

SỰ THẬT ĐÃ KIỂM TRÊN REPO NGÀY 13/10/2026 (bước đầu tiên của bạn là tái lập; số nào lệch thì dừng và báo)
- Mốc test Sprint 3: HEUR-JW T1 accuracy 0,9219 / macro-F1 0,9249; DYN 0,7188 / 0,5626, Lai F1 = 0, support Lai = 5;
  mask T1 trên test: 64 eligible / 20 null / 16 excluded (test_evaluation_exclusions trong manifest corpus_v1_release2;
  dev dùng evaluation_exclusions, 17 ID).
- T1 trong corpus (trước mask): train 119 cu / 71 moi / 16 Lai / 34 null; dev 31 / 15 / 8 / 6; test 49 / 25 / 6 / 20.
- Data 06: 600 dòng đều Lai, đều loại B; sau leak_guard còn 580 (C1 410 / C2 115 / C3 55), 48 nhóm admin_group_key.
  Test Sprint 3 chứa 20 dòng của Data 06 (và 20 dòng của mỗi Data 01/03/04).
- Generator generate_hybrid_addresses(df_old_snapshot, mapping_path, target_size, seed)
  (src/data/synthetic/hybrid_address.py) chỉ nhận đơn vị cũ có đúng một đích; hạn ngạch C1/C2/C3 = 70/20/10%.
  Với data/interim/osm/osm_old_snapshot_full.csv (26.961 dòng; 5.258 dòng có đúng một đích; 753 phường mới) và
  seed 20261015, target_size 3000: sinh đủ 3.000 dòng; 244 dòng TRÙNG NGUYÊN VĂN với Data 06; 20 dòng bị leak_guard
  loại; 527 nhóm, 74 dòng UNRESOLVED; nhóm lớn nhất 10,6%; 135 dòng có TenDuong bắt đầu bằng ngõ/hẻm/ngách/kiệt;
  tập trung ở TP.HCM và Bắc Ninh.
- Nhóm hành chính của dev/test Sprint 3 phần lớn không tra được (dev 23/40, test 34/48 nhóm là UNRESOLVED) vì gold
  ghi tên thiếu tiền tố. Chỉ loại theo admin_group_key là KHÔNG đủ: phải loại thêm theo cặp (tỉnh chuẩn hóa, tên
  phường bỏ tiền tố loại đơn vị) trùng với bất kỳ mẫu dev/test nào.
- Posterior T1 của DYN đã có sẵn trong prediction đã freeze: mỗi dòng predictions.jsonl của DYN có
  trace.structure = {posterior{cu,moi,Lai}, confidence, margin_observed, threshold, margin_required, predicted_system,
  t1_abstain, ban_district}. Phần chẩn đoán trên dev/test KHÔNG cần chạy mô hình.
- Checkpoint DYN c02: data/interim/modeling/sprint03/release_and_kaggle_20261005_v1/dyn_c02_selection_artifacts_v1/
  dacn_artifacts/dacn-s3-dyn-c02-20261005-v1/workspace/data/processed/evaluation/sprint03/
  dacn-s3-dyn-c02-20261005-v1_proposed_dyn_c02/checkpoints/best.pt, SHA-256
  7a4a3d01bff1222cd303cb5ff03872c5ee49b22cb67a0572833fa470f917a589 (đã kiểm). Chưa ai kiểm rằng checkpoint này nạp
  được trên CPU cục bộ: PhoBERTCRFAdapter gọi load_checkpoint với hash của resource lock, và checkpoint được huấn luyện
  trên Kaggle với resource lock của Kaggle.
- Pipeline huấn luyện đã khóa KHÔNG nhận dữ liệu bổ sung: src/modeling/datasets.py::load_corpus ghim hash manifest,
  src/modeling/protocol.py::load_config từ chối config có hash lạ. Vì vậy huấn luyện lại DYN với dữ liệu lai
  (DYN-T1-AUG) nằm NGOÀI gói này; ghi trạng thái DEFERRED_NEEDS_TRAINING_PROTOCOL_CHANGE trong bảng, không tìm cách vòng.
- Data 06 và generator để ngõ/hẻm bên trong TenDuong, gold Sprint 3 tách Ngo/Hem. Gói này chỉ dùng dữ liệu tổng hợp
  cho T1 (nhãn cấp chuỗi), KHÔNG dùng làm nhãn T0, nên không cần tách; nhưng không được suy ra hay báo T0 từ chúng.
- Prediction test đã freeze (đường dẫn và hash trong data/interim/modeling/sprint03/final_completion_20261005_v1/
  all_test_predictions_frozen.json): HEUR-JW và CRF-INDEP ở light_test_runs_v2/; PHOBERT-CRF, DYN, DYN tắt ràng buộc ở
  kaggle_final_output_v4/.../{pcrf_test,dyn_test,dyn_off_test}/. Prediction dev: lần theo selection_lock.json của từng run.

TẦNG 1 — BẮT BUỘC, CHỈ CPU (runtime chính ~/.venv_dacn; CRF qua runtime CRF thành tiến trình riêng)

1. scripts/67_build_t1_sets.py dựng trong data/interim/modeling/sprint04/t1_sets_20261015_v1/:
   a. Nguồn Lai mới: generate_hybrid_addresses trên osm_old_snapshot_full.csv, seed 20261015, target_size 3000.
      Loại: dòng trùng nguyên văn hoặc trùng sau chuẩn hóa với Data 06; dòng bị leak_guard loại (train/dev/test);
      dòng có khóa UNRESOLVED. Báo số dòng còn lại sau từng bước.
   b. Nguồn cu và moi: Data 03 (cu) và Data 01 (moi) qua leak_guard.
   c. Gộp (a)+(b) thành một bể, gán admin_group_key. Chia theo NHÓM (seed 20261015) thành t1_synth_train /
      t1_synth_dev / t1_synth_eval ≈ 60/20/20 số nhóm, phân tầng theo tỉnh mới. Chỉ dòng có khóa ADM| được vào
      train/dev; dòng UNRESOLVED chỉ vào eval và được đánh cờ.
   d. Loại khỏi train/dev mọi dòng có cặp (tỉnh chuẩn hóa, tên phường bỏ tiền tố) trùng một mẫu dev/test Sprint 3,
      và mọi dòng cùng nhóm ADM với một mẫu dev/test tra được. Báo số dòng loại.
   e. Cân bằng lớp trong t1_synth_train bằng cách lấy mẫu xuống theo seed (không nhân bản), báo tỷ lệ lớp cuối cùng
      của cả ba phần. Không lớp nào được phép suy ra chỉ từ "có cấp huyện": kiểm bằng một phân loại một-đặc-trưng
      (có/không có span cấp huyện) trên t1_synth_eval và báo accuracy của nó làm mốc tầm thường.
   f. t1_data06_heldout = 580 dòng Data 06 sau leak_guard, kèm cờ group_seen_in_synth_train. Đây là tập đánh giá,
      không bao giờ dùng để huấn luyện hay chọn tham số.
   g. Mọi file có cột: text, gold_system, source, KieuLai (nếu có), admin_group_key, province_new. Ghi run_manifest.json.

2. src/evaluation/t1_situations.py — thẻ tình huống theo mục 1.2 của đề cương, chỉ từ edges.csv, dùng ở phía chấm:
   A = mẫu cu có đơn vị nguồn với nhiều đích; B = mẫu moi có phường đích gộp từ nhiều nguồn; C = mẫu Lai;
   D = mẫu có tên phường tồn tại ở cả hai hệ trong cùng tỉnh mới (tái dùng SingleVersionIndex.homonyms của
   src/evaluation/t2_lookup.py). Một mẫu có thể mang nhiều thẻ; không gán được thì NONE. Ghi định nghĩa vận hành này
   vào báo cáo vì đề cương không cho định nghĩa máy đọc.

3. Chẩn đoán DYN từ prediction đã freeze (dev và test, không chạy mô hình):
   - Với mỗi mẫu T1 eligible: lớp gold, argmax của posterior, posterior của lớp gold, có vượt ngưỡng/margin không.
   - Tách riêng mẫu Lai: bao nhiêu mẫu có argmax = Lai nhưng bị ngưỡng/margin đẩy sang khong_ro, bao nhiêu mẫu có
     argmax là lớp khác (và lớp nào). Phân phối posterior(Lai) trên mẫu Lai so với mẫu cu/moi.
   - Accuracy và macro-F1 nếu KHÔNG áp ngưỡng (argmax thuần) — ghi rõ đây là phân tích chẩn đoán trên test đã quan sát,
     không phải cấu hình đề xuất. Mục đích: tách "đầu T1 không học được Lai" khỏi "ngưỡng quá chặt".
   - Ghi chú đã kiểm: config ghi structural_policy threshold 0,8 nhưng báo cáo Sprint 3 nói calibration 0,7 / 0,2;
     đọc threshold thực trong trace.structure và báo giá trị quan sát được.

4. Các hệ T1 chạy được trên CPU:
   - HEUR-JW (cấu hình đã khóa: light_test_runs_v2/heur-jw/model_config.json; gazetteer s3_v4_nso_dual_snapshot,
     threshold 0,86) trên t1_synth_eval và t1_data06_heldout.
   - T1-PIPE-<T0>: span hành chính từ một mô hình T0 + luật hệ quy chiếu của HEUR-JW (cu+moi -> Lai; một hệ -> hệ đó;
     không xác định -> khong_ro), tra hệ của từng span bằng đúng mã resolve của HeuristicJaroWinklerAdapter (tái dùng,
     không sao chép logic). Trên test Sprint 3: dùng prediction đã freeze của CRF-INDEP, PHOBERT-CRF, DYN (không suy
     luận lại) — việc này lấp ô T1 NOT_IMPLEMENTED của CRF-INDEP và PHOBERT-CRF. Trên t1_synth_eval và
     t1_data06_heldout: chỉ T1-PIPE-CRF (suy luận CRF-INDEP bằng runtime CRF, checkpoint
     data/processed/evaluation/sprint03/crf_followup_20261003_v1/ctx1_c10.1_c21/model.crfsuite, kiểm SHA-256).
   - T1-FEAT: phân loại softmax tuyến tính viết bằng numpy, huấn luyện trên t1_synth_train, chọn hệ số L2 trong
     {0,01; 0,1; 1} bằng t1_synth_dev, seed 42. Đặc trưng chỉ từ văn bản và gazetteer: có dấu hiệu cấp huyện, loại
     tiền tố đơn vị của từng đoạn, dạng viết của tỉnh, thành viên gazetteer của từng đoạn (chỉ cu / chỉ moi / cả hai /
     không có). Báo thêm một biến thể bỏ nhóm đặc trưng gazetteer để thấy đóng góp của tri thức gazetteer.
   - Mốc tầm thường: luôn đoán lớp đa số; và phân loại một-đặc-trưng ở mục 1e.

TẦNG 2 — NÊN, CẦN RUNTIME NEURAL CỤC BỘ (scripts/68b; chạy thành tiến trình riêng, OMP_NUM_THREADS=6)

5. Smoke trước: dùng data/interim/modeling/sprint03/runtime_neural_d_v1/bin/python, dựng ProposedDynamicAdapter qua
   src/evaluation/experiment_config.py::modeling_config + src/evaluation/dev_runner.py::build_adapter với checkpoint
   trên, resource lock cục bộ (ứng viên: data/interim/modeling/sprint03/task_01_06_20261003_v1/resource_lock_local_v1.json
   hoặc .../pre_colab_20261003_resume_v1/u3_v3/phobert_resource_lock_local.json) và decoder policy đã khóa (lấy đường
   dẫn từ model_config.json của run dyn_test). Chạy 5 mẫu của test_input.jsonl và so span + predicted_system + posterior
   với prediction đã freeze (sai khác posterior <= 1e-4 do khác phần cứng là chấp nhận; khác span thì KHÔNG).
   Nếu nạp checkpoint thất bại hoặc kết quả lệch: ghi BLOCKED_LOCAL_NEURAL kèm nguyên văn lỗi, lưu danh sách đầu vào
   của tầng 2 vào thư mục run, và DỪNG tầng 2. Không sửa mã đã khóa, không đổi hash, không vòng qua kiểm tra.
6. Nếu smoke đạt: suy luận DYN (ngưỡng đã khóa) trên t1_synth_eval và t1_data06_heldout; lưu posterior. Thêm
   T1-PIPE-DYN và T1-PIPE-PCRF trên hai tập này nếu PHOBERT-CRF cũng nạp được.
7. T1-HEAD-PROBE (thay cho DYN-T1-AUG trong gói này): trích vector CLS của encoder DYN đã đóng băng (đầu ra "cls" của
   model.forward) cho t1_synth_train / dev / eval, t1_data06_heldout, và dev/test Sprint 3; huấn luyện một đầu softmax
   tuyến tính bằng numpy trên t1_synth_train (+ 190 mẫu train Sprint 3 có nhãn T1), chọn L2 bằng t1_synth_dev.
   Câu hỏi nó trả lời: biểu diễn của encoder có chứa đủ thông tin để tách Lai không, khi có đủ dữ liệu Lai?
   Ghi rõ đây là probe trên đặc trưng đóng băng, không phải mô hình đề xuất được huấn luyện lại.

BẢNG H5 (báo cáo 10)
- Hàng: mốc đa số; mốc một-đặc-trưng; HEUR-JW; DYN gốc; T1-PIPE-CRF; T1-PIPE-PCRF; T1-PIPE-DYN; T1-FEAT;
  T1-FEAT không gazetteer; T1-HEAD-PROBE; DYN-T1-AUG (DEFERRED_NEEDS_TRAINING_PROTOCOL_CHANGE).
- Cột: test Sprint 3 (64 eligible; ghi nhãn POST_HOC_SECONDARY); t1_synth_eval; t1_data06_heldout (toàn bộ và riêng
  phần nhóm chưa thấy trong train). Mỗi ô: accuracy, macro-F1 ba lớp, Lai P/R/F1 kèm support, coverage, abstain;
  ô không chạy được ghi trạng thái (NOT_RUN / BLOCKED_LOCAL_NEURAL / NOT_APPLICABLE), không bỏ trống.
- t1_data06_heldout chỉ có lớp Lai: báo recall Lai và ghi macro-F1 = NOT_EVALUABLE_SINGLE_CLASS.
- CI cluster bootstrap theo admin_group_key (B=10.000, seed 20261015), ghi số cụm. Kiểm định ghép cặp với HEUR-JW bằng
  stats.py trên cùng tập mẫu.
- Bảng phụ: theo KieuLai C1/C2/C3; theo thẻ tình huống A–D; theo tỉnh mới (5 tỉnh nhiều mẫu nhất + còn lại).

PHẢI VIẾT RÕ TRONG BÁO CÁO
- Lai của test, của Data 06 và của dữ liệu tổng hợp đến từ cùng một generator, cùng nguồn OSM: kết quả tốt trên các
  tập này cho thấy học được mẫu sinh, không chứng minh tổng quát sang địa chỉ lai do người thật viết.
- Kết quả chẩn đoán mục 3: Lai F1 = 0 do đầu T1 không tách được lớp, do ngưỡng, hay cả hai — trả lời bằng số.
- Đối chiếu H5 của đề cương ("địa chỉ lai là lớp khó nhất và mô hình nhận biết phiên bản vượt trội rõ rệt ở lớp này"):
  kết luận ủng hộ / không ủng hộ / không kết luận được, theo CI. Kết quả âm báo đúng như kết quả âm.
- T1-FEAT và T1-HEAD-PROBE được chọn tham số bằng t1_synth_dev; số trên test Sprint 3 của chúng là POST_HOC_SECONDARY.
- Nêu rõ biến thể nào dùng gazetteer (HEUR-JW, T1-PIPE-*, T1-FEAT) và biến thể nào không (DYN, T1-HEAD-PROBE).

TEST (tests/test_t1_group1.py)
- Ba phần synth rời nhóm (giao tập admin_group_key rỗng); không dòng UNRESOLVED nào trong train/dev.
- Không chuỗi nào của train/dev/test Sprint 3 hay Data 06 nằm trong t1_synth_train/dev (so bằng normalize_for_overlap).
- Không cặp (tỉnh, tên phường bỏ tiền tố) nào của dev/test Sprint 3 xuất hiện trong t1_synth_train/dev.
- Luật T1-PIPE cho đúng trên ví dụ dựng tay cho cả bốn nhánh; thẻ A–D tất định; chia nhóm tất định theo seed.
- Chẩn đoán đọc đúng posterior từ một dòng prediction mẫu; mask T1 test cho đúng 64/20/16.
- Đường suy luận của mọi hệ không nhận các cột gold_system, KieuLai, source (test bằng cách truyền DataFrame chỉ có text).

XONG KHI: tầng 1 có đủ bảng với số hoặc trạng thái; tầng 2 có số hoặc BLOCKED_LOCAL_NEURAL kèm lỗi và đầu vào đã lưu;
tái chạy tầng 1 cho cùng hash; bộ test đầy đủ không FAIL.
```

---

## WP3 — Độ tin cậy T0/T1

```text
NHIỆM VỤ: (3a) khoảng tin cậy và kiểm định ghép cặp trên prediction Sprint 3 đã freeze; (3b) chuẩn bị và chấm
thí nghiệm đa seed 42/1337/2025 cho hai mô hình neural. Phụ thuộc: WP0.

File bạn sở hữu: scripts/69_bootstrap_frozen_results.py, scripts/70_prepare_multiseed_kaggle.py,
tests/test_group1_reliability.py, src/modeling/cli.py (chỉ thêm --seed, xem 3b.1),
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
1. Seed. KHÔNG tạo file config mới chỉ khác seed/run_id: src/modeling/protocol.py::load_config từ chối mọi config có
   canonical hash không nằm trong configs/modeling/sprint03/protocol_lock_v1.json (CONFIG_CHANGED_AFTER_PROTOCOL_LOCK),
   dù validate_training_config cho phép seed 1337 và 2025. Không sửa protocol_lock_v1.json (hash của nó được
   hardware profile ghim và nằm trong sổ hash bảo vệ). Hướng thực hiện: thêm tham số `--seed` (chỉ nhận 42/1337/2025)
   vào src/modeling/cli.py, áp seed SAU load_config lên bản sao config trong bộ nhớ, ghi seed thực và hash config gốc
   vào run_manifest.json; chỉ chạm cli.py/training.py ở mức tối thiểu và thêm test chứng minh (i) config gốc và lock
   không đổi, (ii) seed ngoài danh sách bị từ chối, (iii) không đổi seed thì kết quả/hash như cũ. Nếu cách này đòi
   sửa file ngoài danh sách sở hữu, dừng và hỏi chủ dự án. Dùng ứng viên c02 đã khóa.
   Nơi chạy (Kaggle hay máy cục bộ) do chủ dự án quyết định sau khi đo phần cứng; hardware profile hiện có yêu cầu
   cứng GPU >= 8 GiB, float32, torch 2.8.0 cu128 nên KHÔNG dùng được cho RTX 3050 4 GB. Chạy CPU dùng thẳng
   `device: cpu` có sẵn trong config gốc, không cần hardware profile.
2. Seed 42: dùng lại run đã khóa, không huấn luyện lại. CRF-INDEP: L-BFGS tất định -> DETERMINISTIC_SEED_INVARIANT,
   một dòng, không std. HEUR-JW: một cấu hình cố định.
3a. NẾU chủ dự án chọn chạy cục bộ trên CPU (máy i7-12700H, 6 nhân P + 8 nhân E, WSL 7,6 GB RAM; đo ngày 13/10/2026):
   - Bắt buộc đặt `OMP_NUM_THREADS=6 MKL_NUM_THREADS=6` và torch.set_num_threads(6) trước mọi lượt chạy. Đo thực tế:
     6 luồng 1,05 s/bước, 10 luồng 1,23 s, 14 luồng 11,2 s (chậm gấp 10 lần do tranh chấp nhân). Không dùng mặc định.
   - Chạy tuần tự từng lượt (mỗi tiến trình ~2,9 GB RSS); dùng runtime neural data/interim/modeling/sprint03/runtime_neural_d_v1
     với device cpu có sẵn trong config, không dùng hardware profile CUDA (đòi VRAM >= 8 GiB).
   - Chạy cả seed 42 cục bộ để ba seed cùng một môi trường; run Kaggle seed 42 của Sprint 3 báo thành hàng riêng
     "độ nhạy phần cứng", không trộn vào mean ± std.
   - Ước lượng thời gian: ~1 s mỗi micro-batch 4 mẫu, 60 micro-batch/epoch, tối đa 20 epoch (patience 5) => khoảng
     15–30 phút/lượt. Đo thời gian epoch đầu thật rồi cập nhật ước lượng trước khi chạy hết.
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
