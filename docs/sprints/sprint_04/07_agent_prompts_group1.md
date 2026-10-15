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

Trước khi báo xong: chạy `python -m unittest discover -s tests -v` (toàn bộ; đo lại mốc khi bắt đầu gói — số test tăng sau mỗi gói
trong ~/.venv_dacn; không được có FAIL — không được có FAIL và không được làm giảm số PASS cũ),
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

## WP3a — Khoảng tin cậy và kiểm định ghép cặp trên prediction đã freeze

```text
NHIỆM VỤ: báo độ bất định của kết quả T0/T1 Sprint 3 bằng bootstrap và kiểm định ghép cặp, chỉ trên prediction đã
freeze. Không chạy mô hình, không huấn luyện. Chỉ cần runtime chính ~/.venv_dacn. Phụ thuộc: WP0 (src/evaluation/stats.py).

File bạn sở hữu: scripts/69_bootstrap_frozen_results.py, src/evaluation/frozen_reliability.py,
tests/test_group1_reliability.py, data/processed/evaluation/sprint04/reliability_20261014_v1/,
docs/sprints/sprint_04/11_reliability_results.md.

SỰ THẬT ĐÃ KIỂM NGÀY 13/10/2026 (bước đầu tiên là tái lập; lệch thì dừng và báo)
- Gold test: data/processed/annotation/sprint03/corpus_v1_release2/test_benchmark_t0.jsonl (100 mẫu, 446 span).
  Mask T1: manifest.json -> test_evaluation_exclusions (16 ID) => 64 eligible / 20 null / 16 excluded.
- Mỗi mẫu test là một source_group riêng (100 nhóm khác nhau): bootstrap theo source_group TRÙNG với bootstrap theo mẫu.
  Báo một lần, ghi rõ lý do; không trình bày như hai phân tích độc lập. Thay vào đó báo thêm CI theo cụm
  source_dataset (5 cụm × 20 mẫu: 01_new, 02_noisy, 03_old, 04_missing, 06_hybrid, lấy từ identity_registry.jsonl) như
  một bảng độ nhạy, ghi rõ 5 cụm là quá ít để CI đáng tin.
- Hash prediction: data/interim/modeling/sprint03/final_completion_20261005_v1/all_test_predictions_frozen.json
  (models -> predictions_sha256). Trường run_dir trong file đó của ba hệ neural trỏ tới một workspace đã bị dời;
  đường dẫn thật (đã kiểm hash khớp):
  · HEUR-JW:   .../final_completion_20261005_v1/light_test_runs_v2/heur-jw/predictions.jsonl
  · CRF-INDEP: .../final_completion_20261005_v1/light_test_runs_v2/crf-indep/predictions.jsonl
  · PHOBERT-CRF, PROPOSED-DYN, PROPOSED-NO-CONSTRAINT: .../final_completion_20261005_v1/kaggle_final_output_v4/
    dacn_artifacts/dacn-s3-final-infer-20261005-v4/workspace/data/interim/modeling/sprint03/
    dacn-s3-final-infer-20261005-v4/{pcrf_test,dyn_test,dyn_off_test}/predictions.jsonl
- Dùng src/evaluation/dev_runner.py::load_predictions và src/evaluation/span_scorer.py::compute_exact_span_metrics
  (tham số excluded_t1_sample_ids) phải ra đúng:
  T0 P/R/F1: HEUR-JW 0,9512/0,8744/0,9112; CRF-INDEP 0,9234/0,8924/0,9076; PHOBERT-CRF 0,9843 cả ba;
  PROPOSED-DYN 0,9821 cả ba; PROPOSED-NO-CONSTRAINT 0,9843 cả ba.
  T1 accuracy/macro-F1 (64 eligible): HEUR-JW 0,9219/0,9249; DYN và DYN tắt ràng buộc 0,7188/0,5626.
  CRF-INDEP và PHOBERT-CRF không có T1 (NOT_IMPLEMENTED): scorer trả 0,0 vì mọi mẫu là khong_ro — KHÔNG báo số 0 đó
  như kết quả; ghi NOT_IMPLEMENTED. T1 của hai hệ này qua T1-PIPE đã có ở WP2 (docs/sprints/sprint_04/10_t1_h5_results.md).
- Prediction dev: HEUR-JW ở data/processed/evaluation/sprint03/heur_jw_followup_20261003_v1/threshold_0.86/ và
  CRF-INDEP ở data/processed/evaluation/sprint03/crf_followup_20261003_v1/ctx1_c10.1_c21/dev_run/ (đã kiểm tồn tại).
  Dev của ba hệ neural: selection_lock.json trong từng thư mục *_test ghi selected_dev_run trỏ tới đường dẫn không còn
  tồn tại; tìm bản sao bằng hash trong dev_evidence của lock đó dưới data/interim/modeling/sprint03/
  release_and_kaggle_20261005_v1/. Không tìm được bản khớp hash thì ghi NOT_FOUND cho ô dev của hệ đó, không thay bằng
  file khác. Gold dev: corpus_v1_release2/dev.jsonl, mask evaluation_exclusions (17 ID).

TẦNG 1 — BẮT BUỘC (test Sprint 3)
1. Tái lập mọi số ở trên trước khi tính CI. Ghi bảng tái lập vào báo cáo.
2. Biểu diễn theo mẫu: với mỗi hệ, mỗi mẫu có (tp, fp, fn) toàn bộ và theo từng nhãn, cờ exact-match cả địa chỉ,
   và với T1: đúng/sai/abstain trên 64 mẫu eligible. Tổng theo mẫu phải bằng đúng tổng của scorer (kiểm trong test).
3. CI 95% percentile bootstrap theo mẫu, B = 10.000, seed 20261014, bằng src/evaluation/stats.py:
   T0 micro P, R, F1; F1 từng nhãn có support > 0 (nhãn support 0 ghi NOT_EVALUABLE_NO_GOLD_SUPPORT; support < 10 gắn
   LOW_SUPPORT); exact-match cả địa chỉ; T1 accuracy, macro-F1 ba lớp, F1 lớp Lai (support 5: LOW_SUPPORT), coverage.
   Macro-F1 trên một resample thiếu lớp: tính trên các lớp có mặt và đếm số resample như vậy; báo tỷ lệ.
4. So sánh ghép cặp trên cùng 100 mẫu: PCRF–DYN, DYN bật–tắt ràng buộc, PCRF–CRF, PCRF–HEUR, CRF–HEUR (T0);
   HEUR–DYN (T1, 64 mẫu). Mỗi cặp: delta, CI ghép cặp, tỷ lệ resample có delta <= 0, p hoán vị xấp xỉ (10.000 hoán vị),
   McNemar chính xác trên exact-match (T0) hoặc đúng/sai (T1). Thêm cột p Holm trên toàn bộ họ so sánh và ghi số phép
   so sánh. Cặp không có mẫu bất đồng: ghi trạng thái DEGENERATE từ stats.py, không bịa p.
5. Độ nhạy: với mỗi cặp, nêu độ rộng CI ghép cặp như ước lượng hiệu nhỏ nhất phân biệt được với 100 mẫu / 446 span.
6. T0 theo source_dataset (5 lát × 20 mẫu) cho từng hệ, kèm CI; ghi rõ mỗi lát chỉ 20 mẫu.

TẦNG 2 — NÊN
7. Lặp lại mục 3–4 trên dev (60 mẫu; 53 eligible T1) cho các hệ tìm được prediction dev khớp hash. Dev là tập đã dùng
   để chọn mô hình: ghi nhãn SELECTION_SET, không dùng làm ước lượng không chệch.
8. Track 5 trường (4.800 hàng): chỉ làm nếu tầng 1–2 đã xong. File prediction nặng 9–90 MB mỗi hệ; đọc theo dòng,
   không nạp cả file. Dùng metric đã lưu theo hàng nếu có; nếu phải chấm lại thì dùng src/evaluation/scorer.py.
   Ghi nhãn DEVELOPMENT_TRACK. Chưa làm thì ghi NOT_RUN.

BÁO CÁO 11 (phần a)
- Bảng tái lập; bảng CI từng hệ; bảng so sánh ghép cặp; bảng theo source_dataset; (nếu có) dev và 5 trường.
- Mỗi kết luận viết theo CI và dùng đúng từ: "không phân biệt được với dữ liệu này" khác "tương đương".
  Với PCRF–DYN (chênh 1 span) và DYN bật–tắt (đổi 1 mẫu, 2 span), nêu thẳng kết luận mà CI cho phép.
- Giới hạn: một bộ test 100 mẫu đã bị quan sát; gold một người gán có AI hỗ trợ, IAA chưa đo; một seed (đa seed là WP3b);
  4 nhãn không có support; mẫu test lấy đều 20 từ mỗi nguồn nên không phải mẫu ngẫu nhiên của phân phối thật.

TEST
- Tổng (tp, fp, fn) theo mẫu bằng tổng của scorer cho cả 5 hệ; tái lập đúng các điểm công bố (dùng dữ liệu thật, bỏ
  qua bằng skipTest nếu file interim vắng).
- CI tất định theo seed; mask T1 cho 64/20/16; hệ không có T1 được báo NOT_IMPLEMENTED chứ không phải 0.
- Hash prediction sai thì script dừng trước khi tính.

XONG KHI: tầng 1 đầy đủ và tái chạy cho cùng hash; tầng 2 có số hoặc trạng thái; bộ test đầy đủ không FAIL.
```

---

## WP3b — Đa seed trên CPU cục bộ

```text
NHIỆM VỤ: huấn luyện PHOBERT-CRF và PROPOSED-DYN (ứng viên c02 đã khóa) với ba seed 42 / 1337 / 2025 trên CPU cục bộ,
chấm dev và test, báo mean ± std. Phụ thuộc: WP3a (dùng lại frozen_reliability.py và stats.py).
Chạy sau khi chủ dự án đồng ý bắt đầu: tổng thời gian ước lượng 2–4 giờ máy, và cần đóng ứng dụng nặng trên Windows.

File bạn sở hữu: scripts/70_run_multiseed_local.py, tests/test_group1_multiseed.py,
data/interim/modeling/sprint04/multiseed_20261015_v1/ (checkpoint, log, prediction),
data/processed/evaluation/sprint04/multiseed_20261015_v1/ (metric, bảng, manifest),
và phần b của docs/sprints/sprint_04/11_reliability_results.md. KHÔNG sửa file nào trong src/modeling/, configs/ hay
src/evaluation/adapters/.

SỰ THẬT ĐÃ KIỂM NGÀY 13/10/2026
- Không cần sửa mã đã khóa để đổi seed: src/modeling/protocol.py::load_config chỉ kiểm hash của file config; sau khi
  nạp, lấy config = candidate_config(load_config(path), "c02"), gán config["seed"] trên bản sao trong bộ nhớ
  (validate_training_config cho phép 42/1337/2025), rồi gọi thẳng src/modeling/training.py::train_model(config,
  resource_path, corpus_dir, run_dir). Không dùng src/modeling/cli.py (nó ép thư mục đầu ra về sprint03 và không có --seed).
  Config gốc: configs/modeling/sprint03/phobert_crf_v1.json và proposed_dyn_v1.json; device gốc đã là "cpu".
- Corpus cho huấn luyện phải là data/processed/annotation/sprint03/corpus_train_dev_v2: manifest của nó có SHA-256
  9c91b77f… đúng bằng hằng số CORPUS_MANIFEST_SHA256 được ghim. corpus_v1_release2 bị từ chối (BLOCKED_INPUT_HASH).
  Kiểm rằng train.jsonl và dev.jsonl của hai thư mục giống hệt nhau (so SHA-256) và ghi kết quả.
- Preflight trên CPU với runtime neural (data/interim/modeling/sprint03/runtime_neural_d_v1/bin/python, torch 2.8.0+cpu)
  và resource lock cục bộ data/interim/modeling/sprint03/task_01_06_20261003_v1/resource_lock_local_v1.json:
  resource_lock_verified = true; KHÔNG có blocker CUDA. Hai blocker đã thấy và cách xử lý:
  · JAVA_MISSING_FOR_VNCORENLP: Java nằm ở data/interim/modeling/sprint03/resources_d_v1/java17/jdk-17.0.20.1+1-jre/bin;
    thêm thư mục đó vào PATH (và đặt JAVA_HOME) trong môi trường của tiến trình con. Không cài Java.
  · BLOCKED_INPUT_HASH: do truyền corpus_v1_release2; dùng corpus_train_dev_v2.
  Preflight đòi 21,5 GB đĩa trống; ổ D còn khoảng 22–32 GB.
- Mỗi epoch lưu một checkpoint (~540 MB) cộng một checkpoint resume: một lượt 20 epoch có thể chiếm hơn 10 GB.
  Ổ đĩa không đủ cho 6 lượt nếu giữ hết. Sau MỖI lượt: ghi SHA-256 và kích thước của mọi checkpoint vào manifest của
  lượt, giữ best.pt (+ best.pt.json) và training_log.jsonl, rồi xóa các epoch_*.pt và resume_*.pt CỦA CHÍNH LƯỢT ĐÓ.
  Chỉ xóa file trong data/interim/modeling/sprint04/multiseed_20261015_v1/. Kiểm đĩa trống trước mỗi lượt; dưới 15 GB thì dừng.
- Tốc độ đo trên máy này (mô hình cùng kích thước, micro-batch 4 × 48 token): 6 luồng 1,05 s/bước; 10 luồng 1,23 s;
  14 luồng 11,2 s. Bắt buộc OMP_NUM_THREADS=6, MKL_NUM_THREADS=6 và torch.set_num_threads(6). Ước lượng 15–30 phút/lượt;
  trên Kaggle T4 một lượt c02 mất khoảng 12 phút và dừng ở epoch 11.
- Checkpoint Sprint 3 (huấn luyện trên Kaggle với device cuda:0) không nạp được trên CPU cục bộ
  (CUDA_NOT_AVAILABLE / RESUME_CONFIG_MISMATCH, xem data/processed/evaluation/sprint04/t1_h5_20261015_v1/tier2/status.json).
  Vì vậy seed 42 phải được huấn luyện lại cục bộ; kết quả Kaggle seed 42 (T0 F1 PCRF 0,9843, DYN 0,9821; DYN T1
  0,7188/0,5626) báo thành hàng riêng "Sprint 3, GPU T4" và KHÔNG vào mean ± std.
- Train huấn luyện trên dev làm tập chọn epoch (selection_key: full11 dev micro F1 -> macro nhãn có support -> epoch sớm);
  quy tắc này nằm sẵn trong train_model, không tự chọn lại.
- Ngưỡng giải mã của DYN: dùng nguyên policy đã khóa threshold 0,7 / margin 0,2 cho mọi seed, không hiệu chỉnh lại theo
  seed (dev chỉ có 8 Lai, dưới mức 10 của protocol). Ghi rõ đây là lựa chọn và báo thêm T1 argmax thuần như số chẩn đoán.

CÁC BƯỚC
1. Smoke (bắt buộc, trước mọi lượt đầy đủ): chạy preflight cho cả hai mô hình; rồi một lượt PHOBERT-CRF seed 42 với
   max_epochs đầy đủ nhưng DỪNG TAY sau epoch 1 chỉ để đo thời gian một epoch và dung lượng checkpoint — làm trong thư
   mục smoke riêng và xóa sau khi ghi số đo. Nếu không thể dừng sạch sau một epoch mà không sửa mã khóa thì bỏ bước dừng
   tay: chạy thẳng lượt đầy đủ đầu tiên và đo epoch 1 từ log. Nếu preflight hay huấn luyện lỗi vì lý do không xử lý được
   bằng môi trường (PATH, biến môi trường, tham số gọi hàm): ghi BLOCKED_LOCAL_TRAINING kèm nguyên văn lỗi và DỪNG.
   Không sửa mã khóa, không đổi hash, không vòng qua kiểm tra.
2. Cập nhật ước lượng tổng thời gian và dung lượng từ số đo thật; nếu tổng vượt 6 giờ hoặc đĩa không đủ, dừng và báo
   để chủ dự án quyết định (cắt seed hay chuyển Kaggle).
3. Thứ tự chạy, tuần tự từng lượt một: PCRF-42, DYN-42, PCRF-1337, DYN-1337, PCRF-2025, DYN-2025. Mỗi lượt một tiến
   trình riêng, run_dir = .../multiseed_20261015_v1/<model>_seed<seed>/. Ghi thời gian, số epoch, epoch tốt nhất, dev key.
   PROPOSED-NO-CONSTRAINT không huấn luyện: dùng lại best.pt của DYN cùng seed với ràng buộc tắt.
4. Suy luận test (text-only, test_input.jsonl của corpus_v1_release2) bằng adapter của mã khóa
   (PhoBERTCRFAdapter / ProposedDynamicAdapter qua experiment_config.modeling_config + dev_runner.build_adapter, hoặc
   dựng adapter trực tiếp với model/processor đã nạp) với đúng config của seed đó. Khóa prediction (ghi SHA-256) TRƯỚC
   khi đọc gold; chấm đúng một lần mỗi seed bằng compute_exact_span_metrics với mask 64/20/16.
5. Kiểm tất định: chạy lại PCRF-42 lần hai nếu thời gian cho phép và so prediction; nếu khác, báo mức khác và ghi
   NONDETERMINISTIC_ON_CPU thay vì giả định tất định.
6. Bảng: từng seed × {dev T0 F1, test T0 P/R/F1, exact-match, test T1 accuracy / macro-F1 / Lai F1, coverage, epoch
   tốt nhất, thời gian}; mean ± std (ddof=1, n ghi rõ); delta PCRF−DYN và DYN bật−tắt theo từng seed và trung bình;
   hàng riêng cho Sprint 3 GPU T4. CRF-INDEP: một dòng DETERMINISTIC_SEED_INVARIANT; HEUR-JW: một cấu hình cố định.
   Thiếu seed thì ghi n thực và PARTIAL_SEEDS. Không báo riêng seed tốt nhất, không chọn gì bằng test.
7. Diễn giải: so độ lệch chuẩn giữa các seed với chênh lệch PCRF−DYN và với độ rộng CI của WP3a; nêu kết luận mà số
   cho phép. Ghi rõ khác biệt phần cứng (CPU cục bộ so với GPU T4) và rằng test đã bị quan sát.

TEST: seed ngoài {42, 1337, 2025} bị từ chối; file config gốc và protocol_lock_v1.json không đổi hash sau khi chạy;
hàm dọn checkpoint chỉ xóa trong thư mục của gói và không xóa best.pt; mean ± std tính đúng trên ví dụ tay; hàng
Sprint 3 GPU không vào trung bình.

XONG KHI: có đủ 6 lượt (hoặc PARTIAL_SEEDS / BLOCKED_LOCAL_TRAINING kèm lý do và số đo), prediction được khóa trước khi
chấm, bảng và phần b của báo cáo 11 đã viết, đĩa đã dọn, bộ test đầy đủ không FAIL.
```

---

## WP2b — Tầng 2 của WP2 trên checkpoint huấn luyện lại cục bộ

```text
NHIỆM VỤ: lấp các ô neural của bảng H5 (WP2) bằng ba checkpoint DYN và ba checkpoint PHOBERT-CRF mà WP3b đã huấn luyện
trên CPU cục bộ: suy luận DYN và PHOBERT-CRF trên các tập T1 tổng hợp, T1-PIPE trên span của chúng, và probe tuyến tính
trên vector CLS của encoder DYN đóng băng. Không huấn luyện mô hình neural. Phụ thuộc: WP2 (Tầng 1) và WP3b, đều đã
review và commit.

File bạn sở hữu: scripts/68c_run_t1_tier2_local.py, tests/test_t1_tier2_local.py,
data/interim/modeling/sprint04/t1_tier2_local_20261016_v1/ (vector CLS, file .npy),
data/processed/evaluation/sprint04/t1_h5_tier2_local_20261016_v1/ (prediction, metric, bảng, manifest),
và MỘT mục mới ở cuối docs/sprints/sprint_04/10_t1_h5_results.md có tiêu đề "Tầng 2 trên checkpoint huấn luyện lại
cục bộ (WP2b)". Không sửa phần còn lại của báo cáo 10 ngoài một câu dẫn tới mục mới ở mục Tầng 2 hiện có.
KHÔNG sửa: scripts/68_run_t1_evaluation.py, scripts/68b_run_t1_neural_local.py, scripts/70_run_multiseed_local.py,
src/evaluation/t1_pipeline.py, t1_situations.py, và mọi thứ trong src/modeling/, configs/, src/evaluation/adapters/.
Các file đó chỉ được import/đọc. KHÔNG ghi vào data/processed/evaluation/sprint04/t1_h5_20261015_v1/.

SỰ THẬT ĐÃ KIỂM (14/10/2026; bước đầu tiên là tái lập, lệch thì dừng và báo)
- Sáu checkpoint: data/interim/modeling/sprint04/multiseed_20261015_v1/{pcrf,dyn}_seed{42,1337,2025}/checkpoints/best.pt.
  SHA-256 rút gọn theo bản review độc lập (docs/sprints/sprint_04/reviews/review_wp3b_20261014.md): PCRF 5306980e… /
  54f1136b… / bb4ee1b5…; DYN 62105473… / b70d0f7d… / fc41f407… (seed 42 / 1337 / 2025). Hash đầy đủ nằm trong
  multiseed_train_summary.json và best.pt.json của từng lượt; kiểm khớp trước khi nạp.
- Các checkpoint này nạp được trên CPU bằng mã khóa: xem scripts/70_run_multiseed_local.py::inference_config (dùng
  src/evaluation/experiment_config.py::modeling_config với model_config.json của lượt, best.pt, và resource lock
  data/interim/modeling/sprint03/task_01_06_20261003_v1/resource_lock_local_v1.json; DYN dùng decoder policy đã khóa
  threshold 0,7 / margin 0,2, ràng buộc bật). Dựng adapter theo đúng cách đó (import hàm, không sao chép rồi sửa).
- scripts/68b_run_t1_neural_local.py gắn cứng với checkpoint Kaggle của Sprint 3 (không nạp được trên CPU) nên KHÔNG
  dùng lại nguyên script; tái dùng các phần độc lập với checkpoint của nó: ClsCapture (hook lấy đầu ra "cls" của
  model.forward), use_project_java, cách đọc và kiểm hash tier2_inputs.
- Đầu vào đã lưu, chỉ gồm {key, text}: data/processed/evaluation/sprint04/t1_h5_20261015_v1/tier2_inputs/ với
  tier2_inputs.json ghi SHA-256 từng file: t1_synth_train 105, t1_synth_dev 273, synth_eval 2.195, data06 580,
  s3_train 240, s3_dev 60, s3_test 100. Gold và thẻ chấm điểm của Tầng 1: tables/scoring_gold.csv cùng thư mục run
  và data/interim/modeling/sprint04/t1_sets_20261015_v1/.
- Prediction test của WP3b cho từng seed: data/interim/modeling/sprint04/multiseed_20261015_v1/<lượt>/test_dyn/,
  test_dyn_off/, test_pcrf/ (predictions.jsonl; hash trong data/processed/evaluation/sprint04/multiseed_20261015_v1/
  frozen_hashes.json). Dùng làm chuẩn cho bước smoke.
- Adapter khóa đòi ít nhất 20 GiB đĩa trống trước khi suy luận (DISK_BELOW_TRAINING_ARTIFACT_BUDGET); ổ D còn khoảng
  27 GB. Gói này ghi rất ít. Nếu đĩa dưới ngưỡng: DỪNG và báo; không xóa bất cứ thứ gì để lấy chỗ.
- Tốc độ CPU: bắt buộc OMP_NUM_THREADS=6, MKL_NUM_THREADS=6, torch.set_num_threads(6) (14 luồng chậm gấp 10 lần).
  Runtime neural: data/interim/modeling/sprint03/runtime_neural_d_v1/bin/python (có numpy, pandas; không có pycrfsuite).
  Java cho VnCoreNLP: thêm data/interim/modeling/sprint03/resources_d_v1/java17/jdk-17.0.20.1+1-jre/bin vào PATH.
- Kết quả WP3b cần biết khi diễn giải: accuracy T1 của DYN theo argmax ổn định giữa seed (55–57/64 trên test) nhưng
  số mẫu bị từ chối dưới ngưỡng cố định thay đổi mạnh (15 / 2 / 16); chỉ seed 1337 xếp được Lai lên đầu (3/5).

CÁC BƯỚC
1. Smoke cho từng checkpoint (6 lần): dựng adapter, suy luận 100 mẫu s3_test, so với prediction test của WP3b cùng
   seed: span giống hệt, predicted_system giống hệt, posterior chênh tối đa <= 1e-6. Không đạt ở checkpoint nào thì
   ghi SMOKE_FAIL kèm chi tiết cho checkpoint đó và bỏ nó khỏi các bước sau; không đạt ở cả sáu thì ghi
   BLOCKED_LOCAL_NEURAL và dừng. Đo thời gian 100 mẫu và ước lượng tổng (khoảng 3.550 chuỗi × 6 checkpoint); nếu ước
   lượng vượt 5 giờ thì dừng và báo để chủ dự án quyết định cắt phần nào.
2. Suy luận, mỗi checkpoint một tiến trình riêng trong runtime neural, ghi JSONL/NPY rồi thoát:
   - DYN × 3 seed: trên synth_eval, data06, s3_dev, s3_test: span, predicted_system (ngưỡng đã khóa), posterior ba lớp.
     Vector CLS cho cả bảy tập (t1_synth_train, t1_synth_dev, synth_eval, data06, s3_train, s3_dev, s3_test).
   - PHOBERT-CRF × 3 seed: span trên synth_eval, data06, s3_test.
   Ghi SHA-256 của từng file đầu ra TRƯỚC khi bước chấm đọc bất kỳ gold nào (file frozen_hashes.json riêng của gói).
   Mẫu bị processor từ chối (không gọi được mô hình): đếm, giữ trong mẫu số như dự đoán khong_ro.
3. Chấm (runtime chính ~/.venv_dacn), tái dùng hàm của src/evaluation/t1_pipeline.py (pipe_predict, load_locked_heur,
   t1_metrics, select_l2 và bộ softmax tuyến tính, to_units, các statistic_fn) và src/evaluation/stats.py:
   a. DYN (ngưỡng 0,7/0,2) và DYN argmax thuần (số chẩn đoán) trên synth_eval và data06.
   b. T1-PIPE-PCRF và T1-PIPE-DYN: span hành chính của mô hình + luật hệ quy chiếu của HEUR-JW, đúng như Tầng 1 đã làm
      cho T1-PIPE-CRF.
   c. T1-HEAD-PROBE: softmax tuyến tính bằng numpy trên vector CLS của DYN cùng seed; huấn luyện trên t1_synth_train
      (105 dòng) + các mẫu s3_train có nhãn T1; chọn L2 trong {0,01; 0,1; 1} bằng t1_synth_dev với cùng luật hòa như
      Tầng 1; báo trên synth_eval, data06, và test Sprint 3 (64 eligible, nhãn POST_HOC_SECONDARY). Báo thêm biến thể
      chỉ huấn luyện trên t1_synth_train để thấy đóng góp của s3_train. Chuẩn hóa đặc trưng (nếu có) chỉ ước lượng trên
      tập huấn luyện.
   d. Cùng mẫu số, cùng mask, cùng thẻ tình huống A–D, cùng lát cắt (KieuLai, tỉnh, nhóm ADM-only) như Tầng 1.
      t1_data06_heldout chỉ có lớp Lai: báo recall Lai, macro-F1 = NOT_EVALUABLE_SINGLE_CLASS.
4. Bảng: mỗi hệ × mỗi seed × {synth_eval, data06 (toàn bộ và phần nhóm chưa thấy trong train), test Sprint 3} với
   accuracy, macro-F1, Lai P/R/F1 kèm support, coverage, abstain; và mean ± std qua ba seed (ddof = 1, ghi n). CI
   cluster bootstrap theo admin_group_key cho từng seed (B = 10.000, seed 20261016). So sánh ghép cặp với HEUR-JW và
   với T1-FEAT của Tầng 1 trên cùng tập mẫu (lấy dự đoán của hai hệ này từ kết quả Tầng 1; nếu Tầng 1 không lưu dự
   đoán theo dòng thì chạy lại hai hệ CPU đó bằng hàm của t1_pipeline.py và kiểm rằng metric khớp bảng Tầng 1).
5. Mục mới trong báo cáo 10: bảng trên; trả lời ba câu hỏi bằng số — (i) DYN trên tập tổng hợp có tách được Lai
   không, theo từng seed; (ii) biểu diễn CLS có chứa đủ thông tin để một đầu tuyến tính tách Lai không khi có dữ liệu
   Lai (T1-HEAD-PROBE so với đầu T1 gốc của cùng checkpoint); (iii) T1-PIPE với span neural so với HEUR-JW và
   T1-PIPE-CRF. Cập nhật kết luận về hai vế của H5 nếu số liệu cho phép, hoặc ghi "không kết luận được" kèm lý do.

PHẢI GHI RÕ
- Mọi số của gói này mang nhãn LOCAL_CPU_RETRAINED: đây là checkpoint huấn luyện lại trên CPU cục bộ, không phải
  checkpoint đã khóa của Sprint 3 (7a4a3d01…). Các ô BLOCKED_LOCAL_NEURAL của "DYN gốc" trong bảng H5 của Tầng 1 GIỮ
  NGUYÊN; kết quả của bạn là các hàng mới trong bảng mới.
- Báo cả ba seed và mean ± std; không báo riêng seed tốt nhất, không chọn seed theo kết quả. Seed 1337 là seed duy nhất
  có Lai khác 0 trên test: nếu kết luận nào chỉ đứng trên seed này thì nói rõ.
- SHA-256 đầy đủ của sáu best.pt trong run_manifest.json.
- Lai của test, Data 06 và dữ liệu tổng hợp đến từ cùng một generator; probe huấn luyện trên 105 dòng tổng hợp;
  ba giá trị L2 có thể hòa nhau trên dev (như Tầng 1) — nếu hòa thì ghi rõ việc chọn bằng dev không mang thông tin.
- Probe là đầu tuyến tính trên đặc trưng đóng băng, không phải mô hình đề xuất được huấn luyện lại.

TEST (tests/test_t1_tier2_local.py)
- Hash của sáu best.pt và của các file tier2_inputs được kiểm trước khi dùng; sai hash thì dừng.
- Bước chấm từ chối chạy nếu hash prediction khác frozen_hashes.json của gói.
- Đường suy luận chỉ nhận {key, text}; probe không nhận cột gold của tập đánh giá.
- mean ± std đúng trên ví dụ tay; hàm chọn L2 dùng đúng luật hòa của Tầng 1.
- Script từ chối ghi vào thư mục đầu ra đã tồn tại và từ chối ghi vào t1_h5_20261015_v1.
- Test cần file trong data/interim/ thì skipTest khi file vắng.

XONG KHI: sáu checkpoint có kết quả smoke; các hệ có số hoặc trạng thái cho cả ba seed; chạy lại bước chấm cho cùng
hash; mục mới của báo cáo 10 đã viết; bộ test đầy đủ không FAIL (mốc hiện tại 396 test, 388 PASS / 8 SKIP).
```

---

## WP4 — Thí nghiệm CPU: H2, H3, E1, H4

```text
NHIỆM VỤ: bốn thí nghiệm chi phí thấp với CRF-INDEP (và HEUR-JW ở các phép nhiễu lúc test). Bốn bảng nhỏ, kể cả kết quả
âm. Phụ thuộc: WP0 (stats.py, leak_guard.py), WP3a (frozen_reliability.py). Các mô-đun đó chỉ được import, không sửa.

File bạn sở hữu: src/evaluation/perturbations.py, scripts/71_run_cpu_hypothesis_experiments.py,
tests/test_group1_cpu_experiments.py, data/interim/modeling/sprint04/cpu_hypotheses_20261016_v1/ (checkpoint CRF,
tập tăng cường, prediction), data/processed/evaluation/sprint04/cpu_hypotheses_20261016_v1/ (metric, bảng, manifest),
docs/sprints/sprint_04/12_cpu_hypothesis_results.md.

SỰ THẬT ĐÃ KIỂM NGÀY 14/10/2026 (bước đầu tiên là tái lập; lệch thì dừng và báo)
- CRF tái lập HOÀN TOÀN: huấn luyện lại bằng pycrfsuite trong runtime CRF
  (data/interim/evaluation/sprint03/runtime_py311/bin/python; có pycrfsuite, KHÔNG có numpy/pandas) với metadata
  data/processed/evaluation/sprint03/crf_followup_20261003_v1/ctx1_c10.1_c21/model_metadata.json (context 1,
  c1 0,1, c2 1,0, max_iterations 100, feature_version "surface_admin_segment_cue_v2"), train từ
  data/processed/annotation/sprint03/corpus_train_dev_v2/train.jsonl: mất 1,9 giây, file mô hình có SHA-256 TRÙNG checkpoint
  đã khóa (b4ff0d23…), và test T0 P/R/F1 = 0,9234 / 0,8924 / 0,9076. Dùng tokenize / encode_gold / token_features /
  decode_bio của src/evaluation/span_features.py và compute_exact_span_metrics trong src/evaluation/span_scorer.py (chạy
  được trong runtime CRF). Mọi huấn luyện/suy luận CRF là tiến trình riêng trong runtime CRF, ghi JSONL; thống kê chạy
  trong ~/.venv_dacn.
- Trên 400 mẫu train+dev+test: 0 mẫu có span chồng nhau; str.lower() không đổi độ dài ở mẫu nào; 28 mẫu không có dấu
  phẩy nào; 58 mẫu có văn bản không trùng với "các span nối bằng ', '" (có ký tự ngoài span hoặc dấu phân cách khác).
- H2, thiết kế ban đầu KHÔNG khả thi: nếu chỉ giữ dòng Data 04 có khóa nhóm tra được từ các cột bề mặt và loại mọi
  lãnh thổ có trong dev/test, chỉ còn 8/800 dòng. Hai nguyên nhân: dòng thiếu phường không tra được nhóm từ bề mặt, và
  Data 04 tập trung ở cùng các phường với test. Thiết kế sửa (dùng cho gói này):
  · Khóa nhóm lãnh thổ của Data 04 lấy từ các cột GT_TinhThanh / GT_QuanHuyen / GT_PhuongXa bằng admin_group_key. Các cột
    GT_* chỉ được dùng để chia nhóm và chống rò rỉ, KHÔNG bao giờ làm đặc trưng hay nhãn của mô hình; nhãn span đến từ
    các cột bề mặt (SoNha, TenDuong, PhuongXa, QuanHuyen, TinhThanh) căn vào ChuoiDiaChi.
  · Chống rò rỉ với Sprint 3 ở mức địa chỉ, cùng chuẩn với cách Sprint 3 chia train/test (theo source_group, không theo
    lãnh thổ: 16/26 nhóm lãnh thổ của dev+test cũng có trong train Sprint 3): loại dòng bị leak_guard loại (trùng chuỗi
    train/dev/test), và loại dòng có (số nhà, tên đường) GT trùng với một mẫu dev/test. KHÔNG đòi rời lãnh thổ với test;
    ghi rõ điều này là giới hạn trong báo cáo.
  · Đã đo: Data 04 → 779 sau leak_guard → 664 sau khi bỏ TenDuong bắt đầu bằng ngõ/hẻm/ngách/kiệt (bẫy nhãn: gold tách
    Ngo/Hem) → 653 sau khi bỏ trùng địa chỉ với dev/test. Khóa GT: 463 ADM / 190 UNRESOLVED; 142 nhóm; nhóm lớn nhất 16,7%.
    KieuThieu: drop_housenumber 293, drop_ward 198, drop_housenumber_ward 91, drop_district 71. HeQuyChieu: moi 351, cu 302.
  · Bể địa chỉ đầy đủ cho đối chứng AUG-FULL sau cùng các bộ lọc: Data 01 880 dòng, Data 03 1.199 dòng.
- Prediction test đã freeze và cách dựng biểu diễn theo mẫu đã có ở src/evaluation/frozen_reliability.py
  (test_prediction_paths, verify_frozen_hashes, build_units, bootstrap, paired_comparison) — dùng lại cho H4.
- Sáu checkpoint neural huấn luyện lại cục bộ của WP3b (data/interim/modeling/sprint04/multiseed_20261015_v1/
  {pcrf,dyn}_seed{42,1337,2025}/checkpoints/best.pt) nạp được trên CPU, mỗi lần nạp 2–7 phút do đọc từ /mnt/d; cách dựng
  adapter: scripts/68c_run_t1_tier2_local.py và scripts/70_run_multiseed_local.py::inference_config.

TẦNG 1 — BẮT BUỘC (CRF-INDEP và HEUR-JW, chỉ CPU)

0. Tái lập CRF ở điều kiện gốc (như trên) và dùng run tái lập làm mốc ghép cặp. Giữ NGUYÊN siêu tham số đó cho mọi điều
   kiện; không dò lưới lại theo điều kiện.

H3 — xáo thứ tự trường (perturbations.py: recompose_with_order)
- Từ gold span của 100 mẫu test, dựng lại chuỗi bằng cách nối văn bản các span bằng ", " theo: (i) thứ tự gốc [đối
  chứng]; (ii) đảo ngược; (iii) ba hoán vị ngẫu nhiên seed 42 / 1337 / 2025. Tính lại offset; kiểm text[start:end] ==
  nguyên văn span cho 100% span. Mọi so sánh lấy (i) làm mốc, không lấy chuỗi gốc; báo riêng 58 mẫu có văn bản ngoài span
  (đếm lại trên test) và mức thay đổi khi dựng lại.
- Chạy CRF-INDEP (mô hình gốc) và HEUR-JW (cấu hình đã khóa) trên năm điều kiện. Báo micro F1, độ sụt so với (i), F1 từng
  nhãn, CI ghép cặp so với (i). Đối chiếu Yassine et al. (mô hình tiếng Hàn rơi về khoảng 28% khi xáo thứ tự).

E1 — tiền xử lý 2×2: giữ/bỏ dấu phẩy × giữ/hạ chữ hoa
- Phép biến đổi có ánh xạ offset khả nghịch: bỏ dấu phẩy = thay mỗi dấu phẩy bằng khoảng trắng rồi gộp khoảng trắng liên
  tiếp, dựng bảng ánh xạ offset; hạ chữ = str.lower (đã đo: không đổi độ dài). Kiểm khả nghịch trên toàn bộ 400 mẫu.
- Chế độ (a): chỉ nhiễu lúc test, mô hình gốc — CRF-INDEP và HEUR-JW. Chế độ (b): huấn luyện và test cùng điều kiện —
  CRF-INDEP, 4 lần huấn luyện (mỗi lần vài giây). Báo bảng 2×2 cho từng chế độ, CI ghép cặp so với điều kiện gốc.
- Ghi chú bắt buộc: 28 mẫu không có dấu phẩy nên phép bỏ dấu phẩy không đổi gì ở các mẫu đó.

H2 — huấn luyện kèm địa chỉ thiếu trường (thiết kế đã sửa ở trên)
- Dựng tập Data 04 sau lọc (653 dòng); căn span bằng src/data/span_trace.py::align_unique với Component(field,
  surface, source_value, construction_system) từ các cột bề mặt; mẫu căn mơ hồ hoặc thất bại thì bỏ và đếm.
- Chia theo khóa nhóm GT (seed 20261016): heldout_missing ≈ 30% số nhóm ADM + toàn bộ dòng UNRESOLVED; aug_train = phần
  ADM còn lại. Hai phần rời nhóm. Báo số dòng, số nhóm, phân bố KieuThieu của mỗi phần.
- Ba mô hình × N ∈ {120, 240} (lấy mẫu từ aug_train theo seed, phân tầng theo KieuThieu; nếu aug_train không đủ 240 sau
  căn span thì dùng tối đa có được và ghi N thực): BASE (240 train Sprint 3); AUG-MISSING (BASE + N dòng Data 04);
  AUG-FULL (BASE + N địa chỉ đầy đủ từ bể Data 01/03 sau cùng bộ lọc, cân tỷ lệ cu/moi như phần Data 04 đã lấy). Chọn
  epoch không áp dụng (CRF L-BFGS); siêu tham số giữ nguyên.
- Đánh giá: (i) heldout_missing bằng scorer 5 trường (src/evaluation/scorer.py) với GT_* làm silver, tách theo KieuThieu —
  đây là thước đo chính của H2; (ii) 20 mẫu test có source_dataset = 04_missing và 80 mẫu còn lại, bằng scorer span —
  thước đo phụ, POST_HOC_SECONDARY, chỉ 20 mẫu; (iii) dev Sprint 3 để kiểm không suy giảm.
- Đối chiếu H2 của đề cương (tụt 20–40% trên địa chỉ thiếu trường, phục hồi khi thêm dữ liệu thiếu): báo BASE có tụt
  không (so heldout_missing với một tập địa chỉ đầy đủ cùng nguồn đã lọc), AUG-MISSING có phục hồi hơn AUG-FULL không.

H4 — theo nhóm loại địa điểm (không huấn luyện)
- Nhóm (định nghĩa vận hành của gói, vì đề cương không định nghĩa): hành chính = PhuongXa, QuanHuyen, TinhThanh; đường
  sá = SoNha, TenDuong, Ngo/Hem; mốc = MocDinhVi, HuongDi; khác = ToaNha/CanHo, GhiChu, Khac.
- Từ prediction test đã freeze của 5 hệ (frozen_reliability.py): micro P/R/F1 từng nhóm kèm CI, và delta ghép cặp hành
  chính − đường sá trong từng hệ. Nhóm mốc: support test = 0 → NOT_EVALUABLE_NO_GOLD_SUPPORT.
- Số tham khảo cho nhóm mốc: group k-fold (k = 5, nhóm theo source_group, seed 42) của CRF trên 240 mẫu train; ghi
  LOW_SUPPORT kèm support thực và không kết luận.

TẦNG 2 — NÊN (neural, chỉ suy luận, không huấn luyện)
- H3 và E1 chế độ (a) cho PHOBERT-CRF và PROPOSED-DYN với cả ba checkpoint WP3b (6 checkpoint × khoảng 9 điều kiện ×
  100 mẫu). Mỗi checkpoint một tiến trình trong runtime neural (data/interim/modeling/sprint03/runtime_neural_d_v1),
  OMP_NUM_THREADS=6, Java qua PATH như 68c. Smoke trước: 100 mẫu test gốc phải trùng prediction test của WP3b cùng seed.
  Báo từng seed và mean ± std; nhãn LOCAL_CPU_RETRAINED. Không chạy được thì ghi NOT_RUN kèm lý do.

BÁO CÁO 12
- Bốn bảng (H3, E1, H2, H4) và phần Tầng 2 nếu có; mỗi bảng có một dòng kết luận "ủng hộ / không ủng hộ / không kết
  luận được" theo CI. Không gộp thành một điểm tổng.
- Giới hạn bắt buộc: test Sprint 3 đã bị quan sát (mọi số trên test là phân tích độ bền hậu nghiệm); nhãn Data 04 là
  silver từ generator; tăng cường không rời lãnh thổ với test (cùng chuẩn với Sprint 3); chuỗi dựng lại ở H3 không còn
  nguyên văn; nhóm mốc không có support.

TEST
- Mọi phép biến đổi giữ đúng offset (kiểm trên toàn bộ 400 mẫu train+dev+test); hoán vị tất định theo seed.
- Dòng có TenDuong bắt đầu bằng ngõ/hẻm/ngách/kiệt bị loại; không chuỗi nào của train/dev/test Sprint 3 nằm trong tập
  tăng cường; không (số nhà, tên đường) nào của dev/test nằm trong tập tăng cường; aug_train và heldout_missing rời nhóm.
- Cột GT_* không đi vào đặc trưng: đường huấn luyện/suy luận chỉ nhận văn bản và span.
- Tái lập CRF gốc cho đúng hash và F1 0,9076 (skipTest nếu runtime CRF vắng).

XONG KHI: tầng 1 có bốn bảng với số hoặc trạng thái; tái chạy tầng 1 cho cùng hash; tầng 2 có số hoặc NOT_RUN; báo cáo 12
đã viết; bộ test đầy đủ không FAIL (mốc hiện tại 406 test, 398 PASS / 8 SKIP).
```

---

## WP5 — Ablation ràng buộc và tuyên bố H1

```text
NHIỆM VỤ: thay cho ablation adapter mà đề cương hứa (H1) bằng ablation trung thực của thứ đã được hiện thực: đầu T1 +
giải mã có ràng buộc (cấm nhãn QuanHuyen khi T1 tự tin dự đoán "moi"). Toàn bộ gói chạy trên CPU từ prediction đã lưu:
giải mã lại bằng Viterbi thuần Python với emission đã lưu và tham số CRF đọc từ checkpoint. KHÔNG suy luận lại mô hình
neural, KHÔNG dựng adapter khóa (adapter đòi 20 GiB đĩa trống, ổ D không đủ). Phụ thuộc: WP3a, WP3b, WP2, WP2b.

File bạn sở hữu: scripts/72_run_constraint_ablation.py, src/evaluation/constraint_ablation.py,
tests/test_group1_constraint_ablation.py, data/interim/modeling/sprint04/constraint_ablation_20261017_v1/ (tham số CRF đã
trích, kết quả giải mã lại theo dòng), data/processed/evaluation/sprint04/constraint_ablation_20261017_v1/ (metric, bảng,
manifest), docs/sprints/sprint_04/13_constraint_ablation_and_h1.md. Mô-đun của các gói trước chỉ được import.
KHÔNG sửa src/modeling/, configs/, src/evaluation/adapters/, src/modeling/structural_decoder.py.

SỰ THẬT ĐÃ KIỂM NGÀY 14/10/2026 (bước đầu tiên là tái lập; lệch thì dừng và báo)
- Mỗi dòng prediction của DYN có: raw_output.emissions (ma trận số token × 23 nhãn BIO), trace.path_before_constraint,
  trace.path_after_constraint, trace.spans_before_constraint, trace.alignment, trace.changed_unit_indices và
  trace.structure (posterior cu/moi/Lai, threshold 0,7, margin 0,2, predicted_system, ban_district, constraint_enabled).
  Đúng cho:
  · Test Sprint 3, checkpoint Kaggle DYN c02 (SHA-256 7a4a3d01…): .../final_completion_20261005_v1/kaggle_final_output_v4/
    dacn_artifacts/dacn-s3-final-infer-20261005-v4/workspace/data/interim/modeling/sprint03/dacn-s3-final-infer-20261005-v4/
    {dyn_test, dyn_off_test}/predictions.jsonl (hash trong all_test_predictions_frozen.json). Đã biết: bật ràng buộc đổi
    1 mẫu / 2 span (s3_224ae519b196f730, QuanHuyen → PhuongXa); lỗi QuanHuyen trên gold moi 0/12 ở cả hai chế độ.
  · Track 5 trường, cùng checkpoint: cùng thư mục, {dyn_5field, dyn_off_5field}/predictions.jsonl (khoảng 54 MB mỗi
    file; đọc theo dòng). Đã đếm: 4.800 dòng; ràng buộc kích hoạt (ban_district) ở 959 dòng; chỉ 5 dòng có
    changed_unit_indices khác rỗng. Có thêm thư mục *_5field_raw: xác định nó là gì trước khi dùng, ghi vào báo cáo.
    Đầu vào và gold của track: data/interim/modeling/sprint03/final_completion_20261005_v1/fivefield_input.jsonl
    (sample_id, text, dataset, source_row) và fivefield_input.manifest.json; gold lấy theo dataset + source_row từ
    data/processed/benchmark/ (HeQuyChieu, các cột trường và GT_*). Track này là DEVELOPMENT_TRACK.
  · Test Sprint 3, ba checkpoint DYN huấn luyện lại cục bộ của WP3b: data/interim/modeling/sprint04/multiseed_20261015_v1/
    dyn_seed{42,1337,2025}/{test_dyn, test_dyn_off}/predictions.jsonl. Đã biết (review WP3b): ràng buộc kích hoạt ở
    28 / 31 / 3 mẫu nhưng không đổi đường giải mã nào. Nhãn LOCAL_CPU_RETRAINED.
  · PHOBERT-CRF dùng cùng adapter nên prediction của nó (pcrf_test của Kaggle; test_pcrf của WP3b) cũng có emission —
    kiểm trước khi dùng cho bảng 2×2.
- Tham số CRF: src/modeling/crf.py::LinearChainCRF có start (23), end (23), transitions (23 × 23), cộng mặt nạ BIO từ
  src/modeling/labels.py::bio_constraints. src/modeling/structural_decoder.py::viterbi_reference(emissions,
  transitions, start_scores, end_scores, forbidden_tag_ids) là bản tham chiếu thuần Python đã dùng để kiểm decode của Torch.
  Trích start/end/transitions của từng checkpoint cần dùng (DYN Kaggle 7a4a3d01…, PCRF Kaggle 19894a1e…, sáu best.pt
  của WP3b) bằng torch.load(map_location="cpu") trong runtime neural (data/interim/modeling/sprint03/runtime_neural_d_v1/
  bin/python), ghi ra JSON nhỏ kèm SHA-256 checkpoint, rồi mọi bước sau chạy trong ~/.venv_dacn. Đây là đọc tensor,
  không dựng adapter và không suy luận. Tìm khóa trong state dict theo hậu tố "crf.start", "crf.end", "crf.transitions";
  không đoán định dạng — in danh sách khóa nếu không thấy.
- Dev: không có prediction dev của DYN có ràng buộc (chỉ có run không ràng buộc, xem review WP3a); nếu prediction dev
  không ràng buộc có emission và posterior thì áp ràng buộc bằng giải mã lại; không có thì ghi NOT_FOUND.

CỔNG KIỂM TRA BẮT BUỘC TRƯỚC MỌI PHÂN TÍCH
- Với mỗi tập và mỗi checkpoint: giải mã lại không cấm nhãn nào phải ra đúng trace.path_before_constraint ở 100% dòng;
  giải mã lại với đúng tập nhãn cấm mà DYN đã dùng (B-/I-QuanHuyen khi ban_district = true) phải ra đúng
  trace.path_after_constraint ở 100% dòng. Lệch ở bất kỳ dòng nào thì DỪNG, ghi số dòng lệch và ví dụ, gửi câu hỏi cho
  phiên điều phối. Không nới tiêu chí. Ghi cách xử lý hòa điểm (nếu có) và số dòng gặp hòa.

PHÂN TÍCH (Tầng 1, bắt buộc)
1. Ghép cặp bật/tắt cho mọi tập có sẵn (test Kaggle, track 5 trường, ba seed WP3b, dev nếu dựng được): số dòng kích
   hoạt ràng buộc, số dòng đổi đường giải mã, số span đổi; phân loại từng thay đổi (sửa đúng / làm sai / trung tính) theo
   gold; delta F1 kèm CI ghép cặp (src/evaluation/stats.py; test và seed: theo mẫu; track 5 trường: scorer 5 trường).
2. Dư địa: trên mỗi tập, đếm mẫu gold "moi" (không có QuanHuyen trong gold) mà đường giải mã KHÔNG ràng buộc vẫn dự
   đoán một span QuanHuyen — đó là số lỗi tối đa mà ràng buộc có thể sửa. Tách theo việc T1 của DYN có dự đoán đúng
   "moi" không. Nếu dư địa bằng 0 thì viết đúng như vậy.
3. Ablation nguồn T1 cho ràng buộc (giải mã lại trên emission của DYN, cùng quy tắc cấm QuanHuyen khi nguồn T1 nói "moi"):
   (a) T1 của DYN (tái lập chế độ bật); (b) T1 của HEUR-JW cho cùng chuỗi (lấy predicted_system từ prediction đã freeze
   của HEUR-JW: test ở light_test_runs_v2/heur-jw, track 5 trường ở data/processed/evaluation/sprint03/
   heur_jw_followup_fivefield_20261003_v1 hoặc heur_jw_5field_20261002_v1 — xác định file nào khớp cấu hình đã khóa
   threshold 0,86; đọc theo dòng, file 90 MB); (c) T1 gold làm ORACLE. (c) ghi nhãn ORACLE_UPPER_BOUND, không bao giờ đưa
   vào bảng so sánh mô hình.
4. Bảng 2×2 {có/không đầu T1 khi huấn luyện} × {có/không ràng buộc khi giải mã} trên test Sprint 3 (Kaggle):
   PHOBERT-CRF (không T1, không ràng buộc); PROPOSED-NO-CONSTRAINT (có T1, không ràng buộc); PROPOSED-DYN (có, có); ô
   (không T1, có ràng buộc) = giải mã lại emission của PHOBERT-CRF với nguồn T1 bên ngoài (HEUR-JW, và ORACLE ghi riêng).
   Ghi rõ PCRF và DYN là hai lần huấn luyện khác nhau; dùng std giữa seed của WP3b (T0 F1 DYN 0,0111, PCRF 0,0030) để
   diễn giải mọi chênh lệch giữa hàng.
5. Nếu thời gian cho phép, lặp mục 1–3 cho ba seed WP3b (nhãn LOCAL_CPU_RETRAINED); báo từng seed, không chọn seed.

BÁO CÁO 13 — mục trung thực bắt buộc
- H1 (type adapter / gazetteer adapter) = NOT_TESTABLE: không có adapter nào được hiện thực trong repo. Liệt kê cái đề
  cương hứa (mục 4.1: PhoBERT + gazetteer adapter đa phiên bản + type adapter + global pointer) so với cái đã có
  (PhoBERT + CRF + đầu T1 tuyến tính + ràng buộc giải mã theo confidence). Ablation ở đây không phải bằng chứng ủng hộ
  hay bác bỏ H1.
- Kết luận về ràng buộc theo đúng số: có lợi / có hại / không quan sát được tác dụng, kèm dư địa và kèm ORACLE (nếu ngay
  cả T1 hoàn hảo cũng không giúp thì nói rõ).
- Hướng ĐATN: điều kiện cần để H1 kiểm được (adapter nào, dữ liệu nào, support bao nhiêu).
- Giới hạn: test 100 mẫu đã bị quan sát; track 5 trường là development; checkpoint Kaggle so với cục bộ; T1-PIPE của WP2
  là một cách đưa gazetteer vào T1 nhưng KHÔNG phải adapter của H1.

TEST (tests/test_group1_constraint_ablation.py)
- Giải mã lại tái lập đúng path trước/sau ràng buộc trên các dòng mẫu thật (skipTest khi file interim vắng) và trên ví
  dụ dựng tay; Viterbi với tập cấm rỗng bằng không cấm.
- Phân loại thay đổi (sửa đúng / làm sai / trung tính) đúng trên ví dụ dựng tay.
- ORACLE không bao giờ xuất hiện trong bảng so sánh mô hình.
- Dư địa trên test Kaggle tái lập 0/12.
- Đường phân tích không nạp adapter và không gọi suy luận mô hình (kiểm import).

XONG KHI: cổng kiểm tra đạt cho mọi tập được dùng; mục 1–4 có số hoặc trạng thái (mục 5 có số hoặc NOT_RUN); báo cáo 13
đã viết; chạy lại cho cùng hash; bộ test đầy đủ không FAIL (mốc hiện tại: số test sau WP4, đo lại khi bắt đầu).
```

---

## WP6 — Tổng hợp và cập nhật tài liệu

```text
NHIỆM VỤ: gom kết quả Nhóm 1 (WP0–WP5) thành một báo cáo tổng hợp ngắn, có thể dùng làm khung cho chương kết quả của
đồ án, và cập nhật các tài liệu trạng thái đang lỗi thời. Không chạy thí nghiệm mới; mọi số phải truy được về một file
kết quả đã commit.

File bạn sở hữu: scripts/73_generate_group1_report.py, tests/test_group1_summary.py,
data/processed/evaluation/sprint04/group1_summary_20261015_v1/ (bảng tổng hợp, manifest),
docs/sprints/sprint_04/14_group1_summary.md, docs/sprints/sprint_04/README.md, docs/data_quality.md, README.md,
AGENTS.md (CHỈ mục 5 phần danh sách script/module mới và mục 9 trạng thái), và mục 7 của
docs/sprints/sprint_04/06_group1_science_gap_plan.md (chỉ cập nhật trạng thái, không viết lại kế hoạch).
KHÔNG sửa các báo cáo 09–13, các bản review, mã hay kết quả của WP0–WP5, tài liệu Sprint 3.

ĐẦU VÀO (đều đã review độc lập và commit trên nhánh sprint4_group1)
| Gói | Báo cáo | Run kết quả | Review |
|---|---|---|---|
| WP1 T2, E2, E3 | 09_t2_baseline_results.md | t2_baseline_20261014_v1 | (review trong phiên, không có file) |
| WP2 T1, H5 | 10_t1_h5_results.md mục 1–10 | t1_h5_20261015_v1 | reviews/review_wp2_20261013.md |
| WP2b Tầng 2 cục bộ | 10_t1_h5_results.md mục 11 | t1_h5_tier2_local_20261016_v1 | reviews/review_wp2b_20261014.md |
| WP3a CI | 11_reliability_results.md phần a | reliability_20261014_v1 | reviews/review_wp3a_20261013.md |
| WP3b đa seed | 11_reliability_results.md phần b | multiseed_20261015_v1 | reviews/review_wp3b_20261014.md |
| WP4 H2, H3, E1, H4 | 12_cpu_hypothesis_results.md | cpu_hypotheses_20261016_v1 và _v2 | reviews/review_wp4_20261014.md |
| WP5 ràng buộc, H1 | 13_constraint_ablation_and_h1.md | constraint_ablation_20261017_v1 | reviews/review_wp5_20261015.md |
Run nằm dưới data/processed/evaluation/sprint04/. File predictions*.jsonl không được commit (có trên đĩa nếu cần).
Đọc cả báo cáo VÀ bản review của từng gói: phán quyết cuối của một gói là báo cáo sau khi đã sửa theo review.

CÁC BƯỚC
1. Kiểm chéo (scripts/73, runtime ~/.venv_dacn): với mỗi run, hash đầu ra trong run_manifest.json khớp file hiện tại;
   chọn khoảng 5 con số tiêu đề mỗi báo cáo và đối chiếu với metrics.json hoặc bảng CSV của run. Lệch thì ghi vào mục
   "Sai lệch phát hiện" của báo cáo 14, KHÔNG sửa báo cáo gốc. Script sinh các bảng của báo cáo 14 từ file kết quả
   (không chép số bằng tay) và ghi manifest có hash đầu vào.
2. Báo cáo 14 (khoảng 2–3 trang), gồm:
   a. Bảng giả thuyết H1–H5, E1–E4 × trạng thái (SUPPORTED / PARTLY_SUPPORTED / NOT_SUPPORTED / INCONCLUSIVE /
      NOT_TESTABLE / NOT_RUN) × một câu bằng chứng có số × cỡ mẫu × đường dẫn. Lấy trạng thái từ báo cáo đã sửa theo
      review; nếu báo cáo dùng nhãn khác (ví dụ "ủng hộ một phần", NEGATIVE_RESULT) thì quy đổi và ghi nhãn gốc bên cạnh.
      Ghi chú theo đề cương mục 6: H2, H3, H5, E1, E3 thuộc ĐACN; H1, H4, E2 thuộc ĐATN; E4 NOT_RUN (VQA đang HOLD).
   b. Bảng T0 / T1 / T2 hợp nhất: điểm Sprint 3 kèm CI (WP3a), mean ± std ba seed cục bộ (WP3b, nhãn LOCAL_CPU_RETRAINED,
      hàng Kaggle seed 42 tách riêng), T1 của các hệ thay thế (WP2, WP2b), T2 theo chiều (WP1).
   c. Phát hiện xuyên gói, mỗi ý một đoạn ngắn có số và dẫn nguồn:
      - T2: bất đối xứng hai chiều là cấu trúc của cải cách (95,3% khóa cũ giải tất định so với 4,1% khóa mới); chuẩn
        hóa tên quan trọng hơn mọi luật chọn (0,008 / 0,860 / 0,965); 96,5% của luật mặc định là do cách lấy mẫu Data 07.
      - Mô hình đề xuất không hơn PhoBERT-CRF ở T0 (không phân biệt được qua ba seed) và kém HEUR-JW ở T1; T1 tốt nhất
        đến từ ghép span với gazetteer; biến thiên T1 của DYN giữa seed nằm ở tỷ lệ từ chối dưới ngưỡng cố định.
      - Lớp CRF của PhoBERT-CRF và DYN gần như không được dùng (tham số dưới 0,07 so với khoảng cách emission trung vị
        3,29): hành vi đến từ encoder (WP5, review WP5 Q2).
      - Ràng buộc giải mã không có tác dụng trên dữ liệu sạch vì dư địa bằng 0; chỉ dữ liệu nhiễu có dư địa.
      - H2: kết luận phụ thuộc thước đo (gt khoảng 32%, surface khoảng 6 điểm).
   d. Mục "Giới hạn và đe dọa tính hợp lệ" (gom từ các báo cáo): test 100 mẫu đã bị quan sát; gold một người gán có AI
      hỗ trợ, IAA chưa đo; Data 07 chỉ có B/M, tập trung Hà Nội, và có tính vòng lặp với bảng tra; dữ liệu lai cùng một
      generator; nhãn hiếm và nhãn mốc không có support; checkpoint Kaggle so với cục bộ; ba seed là ước lượng thô.
   e. Phần còn thiếu, xếp theo loại: (i) thiếu do dữ liệu, chuyển Nhóm 2 / ĐATN: loại A và C ở T2, E2, nhãn mốc, Lai
      do người thật viết, Accuracy@161km (cần tọa độ); (ii) thiếu do môi trường: Tầng 2 của WP4 (H3, E1 trên mô hình
      neural) NOT_RUN vì adapter khóa đòi 20 GiB đĩa trống; (iii) hoãn có chủ đích: DYN-T1-AUG (cần đổi protocol huấn
      luyện), H1 (không có adapter); (iv) tùy chọn: CI track 5 trường (WP3a), ô PhoBERT-CRF track 5 trường (WP5).
   f. Sai lệch phát hiện ở bước 1 (hoặc "không có").
3. Cập nhật tài liệu trạng thái, ngắn, dẫn tới báo cáo 14 thay vì chép bảng:
   - docs/data_quality.md: thêm mục kết quả Nhóm 1; sửa dòng "T2 chưa thực thi"; mốc test hiện tại.
   - README.md: thêm dòng kết quả Nhóm 1 và liên kết; thêm scripts 65–73 vào cây thư mục/danh sách script. Không sửa
     phần mô tả Sprint 3.
   - AGENTS.md mục 5: thêm scripts 65–73 và các module mới (src/evaluation/leak_guard.py, stats.py, t2_lookup.py,
     t2_scorer.py, t1_pipeline.py, t1_situations.py, frozen_reliability.py, perturbations.py, constraint_ablation.py)
     mỗi dòng một câu; mục 9: trạng thái Nhóm 1 (thêm đoạn mới có ngày, giữ đoạn Sprint 3). Thêm vào mục 9 hai bẫy vận
     hành đã gặp: git của WSL báo khoảng 90 file "bị sửa" giả do line ending (dùng git Windows); ba runtime tách biệt
     (chính / CRF / neural) và OMP_NUM_THREADS=6.
   - docs/sprints/sprint_04/README.md: thêm mục lục cho 05–14 và thư mục reviews; ghi rằng Amendment A2 (tài liệu 08) đã
     đưa T2 vào phạm vi, nên câu "Không mở rộng Sprint 4 sang T2" không còn đúng cho Nhóm 1.
   - Mục 7 của 06_group1_science_gap_plan.md: đánh dấu các bước đã xong kèm commit, thêm WP5 và WP6.
4. Chạy toàn bộ bộ test (python -m unittest discover -s tests trong ~/.venv_dacn), ghi số PASS/SKIP/FAIL vào báo cáo 14.

TEST (tests/test_group1_summary.py): script 73 dừng khi hash một run không khớp manifest; mọi ô số trong bảng sinh ra
có đường dẫn nguồn; script từ chối ghi đè thư mục đầu ra đã tồn tại.

PHẢI TRÁNH
- Không nâng trạng thái của giả thuyết so với báo cáo gốc đã sửa theo review; không làm mềm kết quả âm.
- Không trộn số Kaggle với số cục bộ trong cùng một trung bình.
- Không viết lại kết luận của gói khác; nếu thấy hai báo cáo mâu thuẫn, ghi vào "Sai lệch phát hiện" và nêu bên nào
  là bản sau review.

Không commit, không push. Kết thúc bằng báo cáo cuối theo định dạng trong Khối chung và danh sách file đã đổi.
```

---
