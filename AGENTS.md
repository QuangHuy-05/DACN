# Vietnamese Address Benchmark (DACN) - Hướng dẫn cho AI Agent

## 1. Mục tiêu dự án

Đề tài xây dựng bộ benchmark và các thành phần nền cho bài toán **chuẩn hóa, phân tích và phân giải địa chỉ tiếng Việt qua thay đổi hành chính năm 2025**.

Địa chỉ đầu vào có thể thiếu trường, viết tắt, có nhiễu OCR, dùng hệ hành chính cũ, hệ mới hoặc trộn cả hai. Trọng tâm của repository hiện tại là tạo dữ liệu có nguồn truy xuất được cho các bài toán sau:

- T0 - Tách span địa chỉ theo schema 11 nhãn.
- T1 - Phân loại hệ quy chiếu: `cu`, `moi`, `Lai`.
- T2 - Ánh xạ đơn vị hành chính giữa hai hệ trước và sau 01/07/2025.
- T3 - Đối sánh hai địa chỉ theo thời gian là định hướng giai đoạn sau, chưa hiện thực.

Đề cương đầy đủ: `docs/proposal/de-cuong-dacn-dia-chi-tieng-viet.pdf`.

## 2. Tech stack và môi trường chạy

- Ngôn ngữ: Python.
- Runtime chính: Python trong môi trường ảo WSL.
- Thư viện hiện dùng: `pandas`, `osmium`, `pyarrow`, `tqdm`.
- Dữ liệu: CSV UTF-8-sig, Parquet và OSM full-history `.osh.pbf`.
- Hệ điều hành làm việc: Windows, chạy lệnh trong WSL.

Từ WSL, chạy tại thư mục dự án:

```bash
cd /mnt/d/DACN
source ~/.venv_dacn/bin/activate
pip install -r requirements.txt
```

Không dùng môi trường `.venv/` của Windows khi đang chạy trong WSL. Không cài thư viện mới nếu chưa có yêu cầu rõ ràng từ người dùng.

## 3. Các lệnh quan trọng

```bash
# Trích snapshot OSM cũ và OSM diff
python -m scripts.01_extract_osm

# Lọc hóa đơn Viet-Receipt-VQA, tạo thống kê nhiễu cho Data 2
python -m scripts.02_filter_vqa_receipts

# Sinh các tập benchmark từ dữ liệu trung gian
python -m scripts.03_generate_benchmarks

# Xuất bảng giải thích từng OSM diff được giữ/loại
python -m scripts.04_audit_osm_diff_filters

# Chạy kiểm thử hồi quy
python -m unittest discover -s tests -v
```

`01_extract_osm` đọc file full-history lớn và có thể tốn nhiều thời gian/bộ nhớ. Nếu chỉ cần tái tạo benchmark từ CSV sẵn có, chạy `03_generate_benchmarks` thay vì chạy lại `01`.

## 4. Luồng dữ liệu

```text
data/raw/
  ├─ OSM full-history (.osh.pbf)
  └─ Viet-Receipt-VQA (.parquet)
        │
        ├─ scripts/01_extract_osm.py
        │    └─ data/interim/osm/ và data/processed/osm/
        │
        ├─ scripts/02_filter_vqa_receipts.py
        │    └─ data/interim/vqa/ + configs/noise_params.json
        │
        └─ scripts/03_generate_benchmarks.py
             └─ data/processed/benchmark/
```

Quy tắc dữ liệu:

- `data/raw/` là nguồn gốc, tuyệt đối không sửa trực tiếp.
- Kết quả trung gian đặt trong `data/interim/`.
- Chỉ ghi tập đầu ra chính thức vào `data/processed/`.
- Không ghi đè dữ liệu trong `third_party/`; đây là mã và dữ liệu bên thứ ba.
- Không dùng địa chỉ khách hàng thật. Chỉ sử dụng dữ liệu công khai, OSM, hoặc dữ liệu sinh tổng hợp có nguồn/nhãn rõ ràng.

## 5. Cấu trúc repository

```text
configs/
  noise_params.json                         Phân bố nhiễu ước lượng từ hóa đơn

data/
  raw/osm/                                  OSM full-history
  raw/viet_receipt_vqa/                     Parquet Viet-Receipt-VQA
  reference/administrative_units/           vietnam-sap-nhap-phuong-xa.csv (nguồn chuẩn 2025)
  interim/osm/                              Snapshot cũ, dữ liệu hiện hành, lịch sử đã trích
  interim/vqa/                              Hóa đơn thật sau lọc: chỉ profile nhiễu/kiểm tra ngoài
  interim/annotation/sprint03/              Queue, import/export Label Studio và QA tạm
  processed/osm/                            OSM diff và địa chỉ sạch
  processed/benchmark/                      Tập benchmark 01-07
  processed/annotation/sprint03/            Pilot gold T0 và manifest đã duyệt
  processed/gazetteer/s3_v1/                Gazetteer thời gian một phần; mã cũ còn chưa xác minh
  processed/gazetteer/s3_v2/                Gazetteer thời gian v2; tách mã cũ candidate, 5 chuyển đổi phi nguyên tử

docs/
  proposal/                                 Đề cương đồ án
  sprints/sprint_02/                        Hồ sơ lưu trữ Sprint 2
  sprints/sprint_03/                        Baseline audit, guideline, pilot và kế hoạch Sprint 3
  data_quality.md                           Số lượng, nguồn và giới hạn dữ liệu hiện tại

scripts/
  01_extract_osm.py                         Tạo snapshot cũ và OSM diff
  02_filter_vqa_receipts.py                 Làm sạch/lọc địa chỉ hóa đơn
  03_generate_benchmarks.py                 Điều phối sinh benchmark
  04_audit_osm_diff_filters.py              Giải thích từng bước lọc OSM diff
  05_run_baseline_pilot.py                  Chạy pilot baseline
  06_run_baseline_full.py                   Chạy baseline đầy đủ
  07_generate_baseline_report.py            Báo cáo từ prediction CSV
  08_generate_report_materials.py           Bảng và tài liệu theo run
  09_audit_baseline_runs.py                 Audit manifest/hash và kết quả baseline
  10_prepare_span_annotation.py              Chuẩn bị batch span 01; có output cố định
  11_convert_label_studio_pilot.py           QA/chuyển export pilot
  12_prepare_vqa_review.py                  Tạo queue rà soát; không phải clearance
  13_build_temporal_gazetteer.py            Build/lookup s3_v1; build ghi output cố định
  14_prepare_pilot_answer_key.py             Tạo candidate đáp án pilot
  15_import_pilot_predictions.py             Import prediction pilot vào Label Studio
  16_prepare_t0_corpus_batch.py              Sinh batch 02 train/dev (232 mẫu) và import Label Studio
  17_convert_span_annotation_batch.py        QA/chuyển export Label Studio tổng quát theo batch/role
  18_audit_corpus_split.py                  Audit rò rỉ group, benchmark và gần trùng SequenceMatcher
  19_build_temporal_gazetteer_v2.py          Build/lookup gazetteer s3_v2 độc lập, tách mã cũ candidate
  20_prepare_batch02_predictions.py           Gợi ý span từ text cho batch 02 train/dev; không dùng test
  21_prepare_source_reannotation.py           Gói candidate 68/232 có trace; output version riêng
  22_review_and_package_train_dev.py          Review nội dung, audit frozen split, candidate có cách ly
  23_run_span_dev.py                          Runner dev chỉ nhận text-only và corpus đã qua gate
  24_score_span_dev.py                        Chấm T0/T1 dev riêng sau inference; kiểm hash/version
  25_publish_train_dev.py                     Phát hành train/dev đã duyệt, kiểm hash, giữ ngoại lệ và từ chối ghi đè
  30_prepare_model_training_data.py            Alignment/BIO dẫn xuất 240/60; không tải model hoặc train
  31_train_deepparse_finetuned.py              Pipeline DP-FT-FT có resource/API gate; native integration pending
  32_train_phobert_crf.py                      Pipeline encoder + CRF thật; Torch/processor integration pending
  33_train_proposed_dynamic.py                 T0/T1 mask + giải mã confidence + cùng-checkpoint ablation
  34_audit_modeling_artifacts.py               Audit read-only preparation/checkpoint/prediction và frozen hash
  35_verify_gazetteer_sources.py               Reference verifier exact theo cha/ngày; không sửa s3_v2
  65_prepare_group1_guards.py                  Nhóm 1/WP0: báo cáo loại trừ rò rỉ (leak_guard) cho các tập benchmark
  66_run_t2_baseline.py                        Nhóm 1/WP1: T2 baseline hai chiều, E2, E3 (run t2_baseline_*)
  67_build_t1_sets.py                          Nhóm 1/WP2: tập T1 tổng hợp tách nhóm và Data 06 held-out
  68_run_t1_evaluation.py                      Nhóm 1/WP2: đánh giá T1/H5 tầng 1 (68b, 68c: tầng 2 neural trên checkpoint cục bộ)
  69_bootstrap_frozen_results.py               Nhóm 1/WP3a: CI và kiểm định ghép cặp trên prediction đã freeze
  70_run_multiseed_local.py                    Nhóm 1/WP3b: huấn luyện lại và chấm ba seed trên CPU cục bộ
  71_run_cpu_hypothesis_experiments.py         Nhóm 1/WP4: H3, E1, H2, H4 bằng CRF-INDEP/HEUR-JW
  72_run_constraint_ablation.py                Nhóm 1/WP5: ablation ràng buộc BIO bằng giải mã lại emission đã lưu; H1 NOT_TESTABLE
  73_generate_group1_report.py                 Nhóm 1/WP6: kiểm hash run, đối chiếu số tiêu đề, sinh bảng báo cáo 14

src/
  data/administrative_mapping.py            Nạp/kiểm tra đồ thị ánh xạ hành chính nguyên tử
  data/administrative_alias.py              Alias OSM đã kiểm chứng; ghi vết từng thay đổi khi audit
  data/coverage_reporter.py                 Tổng hợp coverage theo nguồn, quan hệ, vùng, hình học, hình thức
  data/span_trace.py                        Render/align component với offset; abstain khi match mơ hồ
  data/osm_extractor.py                     Parse lịch sử OSM, làm sạch tag
  data/noise_profiler.py                    Đo nhiễu trên tập hóa đơn
  data/synthetic/raw_noisy.py               Sinh Data 2 nhiễu tổng hợp có ground truth
  data/synthetic/missing_fields.py          Sinh tập thiếu trường
  data/synthetic/hybrid_address.py          Sinh địa chỉ lai từ cạnh có một đích xác minh
  data/synthetic/bidirectional.py           Sinh cặp ánh xạ với bằng chứng OSM hoặc đích duy nhất
  evaluation/                               Adapter, scorer, protocol và run manifest
  evaluation/leak_guard.py                  Loại benchmark trùng train/dev/test; khóa nhóm hành chính (admin_group_key)
  evaluation/stats.py                       Bootstrap theo mẫu/cụm, ghép cặp, hoán vị xấp xỉ, McNemar chính xác
  evaluation/t2_lookup.py                   Tra bảng T2 hai chiều theo mức chuẩn hóa N0/N1/N2, STRICT/DEFAULT/SINGLE-VERSION/STREET
  evaluation/t2_scorer.py                   Chấm T2: accuracy theo chiều, lỗi im lặng, CI cụm, E3
  evaluation/t1_pipeline.py                 T1-PIPE (span của mô hình + luật gazetteer), T1-FEAT, T1-HEAD-PROBE
  evaluation/t1_situations.py               Thẻ tình huống A–D của T1 từ gazetteer
  evaluation/frozen_reliability.py          Biểu diễn theo mẫu của prediction đã freeze, CI T0/T1 và so sánh ghép cặp
  evaluation/perturbations.py               Dựng lại chuỗi (đảo/xáo thứ tự, bỏ phẩy, hạ chữ) có ánh xạ offset khả nghịch
  evaluation/constraint_ablation.py         Viterbi giải mã lại có/không cấm QuanHuyen; dư địa; ORACLE tách riêng
  utils/text_normalize.py                   Chuẩn hóa văn bản và vùng miền
  modeling/                                Alignment, BIO, trainer, CRF, T1, checkpoint, protocol và resource gate

tests/
  test_data_pipeline.py                     Kiểm thử hồi quy pipeline
  test_evaluation_pipeline.py                Kiểm thử protocol, manifest và báo cáo
  test_span_evaluation.py                    Kiểm thử scorer span T0
  test_group1_*.py, test_t1_*.py, test_t2_baseline.py  Kiểm thử các gói Nhóm 1 (WP0–WP6)

third_party/
  vietnamadminunits/                        Bảng đối chiếu đơn vị hành chính cũ/mới
```

## 6. Hợp đồng dữ liệu và logic hành chính

Schema span theo đề cương có 11 nhãn:

```text
SoNha, TenDuong, Ngo/Hem, ToaNha/CanHo, PhuongXa,
QuanHuyen, TinhThanh, MocDinhVi, HuongDi, GhiChu, Khac
```

`QuanHuyen` chỉ thuộc hệ cũ. Địa chỉ hệ mới dùng cấu trúc hai cấp: `SoNha, TenDuong, PhuongXa, TinhThanh`.

Data 2 chính thức là `02_raw_noisy_synthetic_1000.csv`. Baseline chỉ nhận cột `ChuoiDiaChi`; `ChuoiDiaChiGoc`, `GT_*`, `LoaiNhieu`, `MucDoNhieu` và `Seed` là metadata đánh giá. Hóa đơn thật trong `interim/vqa/` không được thay thế Data 2 vì không có ground truth đầy đủ.

Tập benchmark 07 dùng các cột:

```text
ID_Node, DiaChi_Cu, DiaChi_Moi, LoaiAnhXa, QuanHe,
HinhThucSapNhap, MaPhuongXaMoi, Nguon
```

Quy tắc hiện hành của tập 07:

- Nguồn chuẩn là `vietnam-sap-nhap-phuong-xa.csv`; mỗi dòng là một cạnh đầy đủ `tỉnh cũ + quận/huyện cũ + phường/xã cũ → tỉnh mới + phường/xã mới`, không phải một danh sách tên phường.
- Phân loại cạnh theo bậc trong đồ thị: `C/1-1`, `A/1-N`, `B/N-1`, `M/M-N`. Không ép M-N thành A hay B.
- Khóa cũ luôn gồm tỉnh, quận/huyện và phường/xã để tránh trùng tên. Tên đơn vị giữ dấu và loại đơn vị; nếu không khớp chính xác thì để trạng thái chưa xác minh.
- Cặp quan sát từ OSM diff chỉ hợp lệ khi số nhà và tên đường không đổi; có thể thuộc A, B, C hoặc M vì đích đã được quan sát.
- Tra ID của OSM diff bằng `interim/osm/osm_old_snapshot_full.csv`; snapshot cân bằng chỉ phục vụ lấy mẫu benchmark, không được dùng để loại ID quan sát trực tiếp.
- Alias chỉ được áp dụng từ `administrative_alias.py`. Audit phải giữ tag gốc, giá trị chuẩn hóa và `AliasDaApDung`; không tự sinh alias hoặc cạnh hành chính chưa có trong CSV nguồn.
- `HinhHocCoDuLieu=False` nghĩa là thiếu bằng chứng, không phải hình học không đổi. Với way, fingerprint chỉ phản ánh chuỗi node thành phần; không đủ để tự kết luận ranh giới hành chính.
- Cặp dựng từ snapshot chỉ được tạo khi khóa cũ có đúng một đích (`B` hoặc `C`). Tuyệt đối không dựng A/M khi thiếu hình học hoặc tọa độ phân định phần lãnh thổ.
- `HinhThucSapNhap` và `MaPhuongXaMoi` được xuất cùng cặp để truy nguyên về bảng nguồn. `Nguon` phân biệt quan sát trực tiếp và dựng an toàn.
- Không gán nhãn ngẫu nhiên để đạt chỉ tiêu số lượng.

## 7. Quy tắc lập trình

### Bắt buộc

- Giữ tên hàm, biến và hằng số mới bằng tiếng Anh; giữ nguyên tên cột dữ liệu tiếng Việt vì đây là hợp đồng CSV hiện hữu.
- Ghi chú ngắn cho logic hành chính, điều kiện lọc dữ liệu, hoặc quy tắc chống gán nhãn sai.
- Dùng `pathlib.Path` cho đường dẫn; không ghi đường dẫn máy cá nhân tuyệt đối vào code.
- Kiểm tra tồn tại file và cột bắt buộc trước khi xử lý CSV/Parquet.
- Đặt seed cố định cho mọi thao tác lấy mẫu để tái lập kết quả.
- Giữ encoding `utf-8-sig` khi xuất CSV benchmark.
- Thêm hoặc cập nhật test trong `tests/test_data_pipeline.py` khi thay đổi logic trong `src/` hoặc pipeline sinh dữ liệu.
- Cập nhật `docs/data_quality.md` và README khi thay đổi số lượng, nguồn hoặc giới hạn của benchmark.

### Không được làm

- Không sửa trực tiếp `data/raw/`, `third_party/`, `.venv/`, `.venv_wsl/` hoặc file `__pycache__/`.
- Không đổi schema hoặc tên cột đầu ra nếu chưa cập nhật toàn bộ nơi đọc file và tài liệu liên quan.
- Không coi thay đổi nhãn OSM là bằng chứng sáp nhập nếu không đối chiếu cạnh tương ứng trong bảng hành chính chuẩn.
- Không tự xóa quận/huyện để gắn nhãn `moi` khi ánh xạ phường/xã chưa được xác minh.
- Không trộn cặp quan sát trực tiếp với cặp dựng từ snapshot mà không ghi rõ `Nguon`.
- Không thêm dữ liệu cá nhân, crawl nguồn mới, hoặc cài dependency mới nếu chưa được người dùng cho phép.

## 8. Kiểm thử và kiểm tra trước khi hoàn thành

`tests/test_data_pipeline.py` kiểm tra làm sạch tag OSM, xử lý node bị xóa, quy đổi tỉnh, tính tái lập của Data 2 nhiễu tổng hợp và dữ liệu thiếu trường, thống kê nhiễu, phân loại 1-N/N-1/M-N, alias có vết audit, tra cứu OSM diff trên snapshot đầy đủ, và quy tắc không suy đoán đích split/M-N.

Trước khi báo hoàn thành thay đổi logic:

1. Chạy `python -m unittest discover -s tests -v`.
2. Nếu thay đổi generator, chạy script liên quan hoặc kiểm tra trực tiếp output bằng mẫu dữ liệu nhỏ.
3. Kiểm tra số dòng, cột, encoding và bản ghi trùng của CSV đầu ra.
4. Báo cáo rõ dữ liệu là quan sát trực tiếp hay được dẫn xuất từ ánh xạ.

Repository hiện chưa có cấu hình linter/formatter Python riêng. Không tự thêm công cụ mới chỉ để format; giữ phong cách mã đang dùng và định dạng phần thay đổi nhất quán.

## 9. Trạng thái thực hiện

**05/10/2026 — kết quả Sprint 3:** SPRINT3_PARTIAL_DP_BLOCKED. T0 test F1: HEUR-JW 0,9112; CRF-INDEP 0,9076; PhoBERT-CRF 0,9843; PROPOSED-DYN 0,9821; ablation không constraint 0,9843. DYN T1 accuracy 0,7188 / macro-F1 0,5626 / Lai F1=0; HEUR T1 accuracy 0,9219 / macro-F1 0,9249. Deepparse-ZS-FT và DP-FT-FT chưa chạy vì license checkpoint chưa được xác minh. Bộ test nghiệm thu 266 PASS / 8 SKIP / 0 FAIL; IAA chưa đo, VQA đang HOLD, Data05 deferred, T2 chưa thực thi, Gazetteer mã cũ còn partial.

Kết quả, giới hạn và receipt được lưu tại:
- docs/sprints/sprint_03/49_sprint3_final_results.md
- docs/sprints/sprint_03/50_sprint3_reproduction_and_handoff.md
- docs/sprints/sprint_03/53_sprint3_end_to_end_report_20261005.md
- data/interim/modeling/sprint03/final_completion_20261005_v1/

Không mở lại nhãn, thay split, tune trên test, hoặc xóa/sửa raw, gold, split và evidence có hash. Tiếp tục Sprint 4 từ các manifest phát hành; chỉ xử lý Deepparse khi có bằng chứng điều kiện sử dụng checkpoint.

**15/10/2026 — Nhóm 1 Sprint 4 (lấp khoảng trống khoa học, nhánh `sprint4_group1`):** WP0–WP5 đã hiện thực, review độc lập và commit; WP6 gom lại ở `docs/sprints/sprint_04/14_group1_summary.md` (bảng giả thuyết, bảng T0/T1/T2, giới hạn, phần còn thiếu). Amendment A2 (`docs/sprints/sprint_04/08_amendment_a2_group1_scope.md`) đã đưa T2 vào phạm vi của Nhóm 1, nên "T2 chưa thực thi" ở đoạn Sprint 3 phía trên là mốc 05/10; T2 baseline đã chạy. Trạng thái giả thuyết (theo báo cáo đã sửa theo review): SUPPORTED H3, E3; PARTLY_SUPPORTED H2, E1; NOT_SUPPORTED H5; INCONCLUSIVE H4, E2; NOT_TESTABLE H1 (không có adapter); NOT_RUN E4 (VQA HOLD). Kết quả chính: T2 cũ→mới 0,965 và mới→cũ 0,077 với luật mặc định, chênh là cấu trúc của cải cách (95,3% khóa cũ giải tất định so với 4,1% khóa mới); mô hình đề xuất không phân biệt được với PhoBERT-CRF ở T0 (ba seed cục bộ 0,9783 ± 0,0111 so với 0,9787 ± 0,0030) và kém HEUR-JW ở T1; ràng buộc giải mã không có dư địa trên dữ liệu sạch. Còn thiếu: Tầng 2 neural của WP4 (cần ≥ 20 GiB ổ D: trống), DYN-T1-AUG, H1, E4, loại A/C của T2. Bộ test sau WP6: 453 test, 445 PASS / 8 SKIP / 0 FAIL (đo ngày 15/10/2026 trong `~/.venv_dacn`; 438 trước WP6 cộng 15 test của `tests/test_group1_summary.py`).

Hai bẫy vận hành đã gặp: (1) `git status`/`git diff` của WSL báo khoảng 90 file "bị sửa" giả (gold, gazetteer, tài liệu Sprint 3) do khác ký tự xuống dòng vì WSL không có `core.autocrlf`; dùng git của Windows và kiểm file được bảo vệ bằng SHA-256 theo manifest. (2) Ba runtime tách biệt, không runtime nào đủ thư viện: chính `~/.venv_dacn` (không có `pycrfsuite`, `torch`, scipy, sklearn), CRF `data/interim/evaluation/sprint03/runtime_py311/bin/python` (không numpy/pandas), neural `data/interim/modeling/sprint03/runtime_neural_d_v1/bin/python` (không `pycrfsuite`); bước cần CRF hoặc neural chạy thành tiến trình riêng, đặt `OMP_NUM_THREADS=6` (cùng `MKL_NUM_THREADS=6`, `PYTHONDONTWRITEBYTECODE=1`) khi chạy neural trên CPU.
