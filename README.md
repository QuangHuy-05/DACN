# Vietnamese Address Benchmark (DACN)

Dự án tạo dữ liệu địa chỉ tiếng Việt trước/sau thay đổi hành chính 2025.

**Đánh giá cuối 05/10/2026 — `SPRINT3_PARTIAL_DP_BLOCKED`:** đã freeze toàn bộ prediction trước khi chấm 100 test. F1 T0: HEUR-JW **91,12%**, CRF **90,76%**, PhoBERT-CRF **98,43%**, PROPOSED-DYN **98,21%**; ablation không constraint **98,43%**. DYN T1 accuracy **71,88%**, macro-F1 **56,26%**, Lai F1 **0** trên 64 mẫu eligible. Constraint làm giảm 0,22 điểm phần trăm T0; cả on/off có 0/12 lỗi Quận ở nhóm hệ mới eligible. Hai cấu hình Deepparse chưa có thực nghiệm vì checkpoint chưa rõ điều kiện sử dụng. **274 test: 266 PASS / 8 SKIP / 0 FAIL**, 2.352 protected hash + 4 raw size/mtime giữ nguyên. [Kết quả và giới hạn](docs/sprints/sprint_03/49_sprint3_final_results.md), [tái lập và bàn giao](docs/sprints/sprint_03/50_sprint3_reproduction_and_handoff.md). Track 5 trường là development/compatibility, test AI-assisted, IAA NOT_MEASURED; không gọi Sprint 3 hoàn thành đủ sáu cấu hình. Các trạng thái chưa chấm test bên dưới là lịch sử.

**Đánh giá cuối 05/10/2026 — `SPRINT3_PARTIAL_DP_BLOCKED`:** đã freeze toàn bộ prediction trước khi chấm 100 test. F1 T0: HEUR-JW **91,12%**, CRF **90,76%**, PhoBERT-CRF **98,43%**, PROPOSED-DYN **98,21%**; ablation không constraint **98,43%**. DYN T1 accuracy **71,88%**, macro-F1 **56,26%**, Lai F1 **0** trên 64 mẫu eligible. Constraint làm giảm 0,22 điểm phần trăm T0; cả on/off có 0/12 lỗi Quận ở nhóm hệ mới eligible. Hai cấu hình Deepparse chưa có thực nghiệm vì checkpoint chưa rõ điều kiện sử dụng. **274 test: 266 PASS / 8 SKIP / 0 FAIL**, 2.352 protected hash + 4 raw size/mtime giữ nguyên. [Kết quả và giới hạn](docs/sprints/sprint_03/49_sprint3_final_results.md), [tái lập và bàn giao](docs/sprints/sprint_03/50_sprint3_reproduction_and_handoff.md). Track 5 trường là development/compatibility, test AI-assisted, IAA NOT_MEASURED; không gọi Sprint 3 hoàn thành đủ sáu cấu hình. Các trạng thái chưa chấm test bên dưới là lịch sử.

**Hiện hành05/10/2026:** test100 đã duyệt theo ủy quyền cuối; dùng [corpus240/60/100 release2](data/processed/annotation/sprint03/corpus_v1_release2/manifest.json). Test có446 span T0,64 T1eligible/20null/16mask; giữ T0 của mọi mẫu và kế thừa mask543 ở dev. QA100/100 và audit138 cặp đạt; source metadata không còn đếm100 benchmark child thành observed. **GPU smoke PASS và4 full run Kaggle đã nghiệm thu**; chọn c02: PhoBERT-CRF **93,89% F1 dev**, PROPOSED-DYN **94,74% F1 dev**. Alignment300/300, checkpoint/hash và locks đã kiểm; chi tiết trong [báo cáo47](docs/sprints/sprint_03/47_test_gold_release_and_kaggle_20261005.md). Chưa inference/chấm test cuối. Các trạng thái pending bên dưới là lịch sử trước phán quyết này.

**Lịch sử local L1–L5, 04/10/2026:** round2 đã đủ **100 task / 103 annotation**, không thiếu mẫu; hai cặp tương đương được kiểm lại, hiện **99 converted / 1 multiple** tại task695, không lỗi cấu trúc trong 99 bản được chọn. Cần chọn annotation của task695 và phán quyết T1 trước phát hành; JSON được giữ nguyên. Publisher, final-test runner/scorer và gói Colab mới đã kiểm bằng fixture/CPU; **239 PASS / 8 SKIP / 0 FAIL**, 1.313 frozen hash + 4 raw size/mtime không đổi. **Chưa phát hành test gold, chạy cloud, train neural hoặc chấm test thật.** [Kết quả L1–L5](docs/sprints/sprint_03/46_local_completion_report_20261004.md), [thao tác release và Colab](docs/sprints/sprint_03/45_local_release_and_colab_operations.md), [inventory tái dùng, 0 cài mới](docs/sprints/sprint_03/44_local_finish_resource_inventory.md). Các kết luận round1 dưới đây chỉ là lịch sử.

**Pipeline Kaggle 04/10/2026:** đã có upload private, GPU preflight, smoke pretrained/checkpoint và gate full training riêng cho train240/dev60. Job đã được gửi bằng API nhưng runtime đầu không có GPU; chưa có `SMOKE_PASS` hoặc training neural đầy đủ. [Hướng dẫn, artifact và thao tác kiểm GPU](docs/sprints/sprint_03/39_kaggle_pipeline_operations.md). Kaggle CLI cài riêng trên D, không đưa test100 vào gói; trạng thái thực tế xem báo cáo40.

**Gán test có hỗ trợ, 04/10/2026:** theo yêu cầu chủ dự án, đã tạo gợi ý 100 task/446 span trong `data/interim/annotation/sprint03/test100_assisted_v1/`, chờ kiểm tra và Submit. [Hướng dẫn import và export](docs/sprints/sprint_03/37_test100_ai_assisted_annotation.md). Lượt này là AI-assisted, không còn là gán mù độc lập; gói blind cũ/corpus/run giữ nguyên. Chưa phát hành gold hoặc chấm test; đáp án giữ local.

**Cập nhật bàn giao trước Colab:** đã xác minh **8.607 mã cũ** theo NSO 30/06/2025, giữ **3.355 mã mới** ở 01/07/2025; Gazetteer hai snapshot còn **2.187 entity cũ chưa xác minh**. CRF mới đạt **90,56% F1 T0 dev**, HEUR giữ **88,01%**; đây là kết quả phát triển. Xem [nguồn](docs/sprints/sprint_03/31_pre_colab_source_verification.md), [Gazetteer](docs/sprints/sprint_03/32_temporal_gazetteer_release.md), [baseline](docs/sprints/sprint_03/34_light_baseline_followup.md), [nghiệm thu](docs/sprints/sprint_03/35_pre_colab_acceptance.md) và [bàn giao Label Studio/Colab](docs/sprints/sprint_03/36_label100_and_colab_handoff.md). Không cài thêm local; notebook đã chuẩn bị, chưa chạy Colab/neural/test100. Gói dữ liệu/resources trong interim phải nhận riêng; clone GitHub không tự có các artifact đó. Các đoạn trạng thái trước bên dưới là lịch sử.

**Hiện hành 03/10/2026:** đã đối chiếu export chính thức NSO và phát hành [gazetteer s3_v3 snapshot 01/07/2025](data/processed/gazetteer/s3_v3_nso_2025_snapshot/manifest.json): xác minh 34 mã tỉnh mới + 3.321 mã xã/phường mới; các mã cũ vẫn chưa đủ nguồn. [Báo cáo và hash nguồn](docs/sprints/sprint_03/29_nso_official_snapshot_gazetteer_release_20261003.md). Sáu việc follow-up neural đã được [kiểm tra và bàn giao](docs/sprints/sprint_03/27_tasks_01_06_completion_20261003.md): PhoBERT/VnCoreNLP/Java đã cài trên D:, API Deepparse PASS, alignment đủ 300/300 train/dev sau xử lý 29 ca dấu, short pretrained PhoBERT forward PASS. Chưa train/chấm neural, không sử dụng Colab/test100.

**Bàn giao gán nhãn Sprint 3 (01/10/2026):** chủ dự án theo [hướng dẫn 68/232 có prediction](docs/sprints/sprint_03/09_label_studio_400_step_by_step.md); partner nhận [gói 100 test mù có task/XML/guideline](docs/sprints/sprint_03/annotation_handoff/test100_v1/README.md) trên nhánh `print3_label100test`. GitHub cung cấp tệp; Label Studio chạy trên máy người gán. Gói test đã qua preflight với 138 quyết định người, sẵn sàng gán theo protocol v1.0; annotation vẫn cần QA và duyệt gold sau export.

**Nghiệm thu nhiệm vụ 1–4 ngày 02/10/2026:** đã phát hành [corpus_train_dev_v2](data/processed/annotation/sprint03/corpus_train_dev_v2/manifest.json), **240 train / 60 dev**, **1.057 + 284 span**, `TRAIN_DEV_APPROVED_TEST_PENDING`. Export batch cuối có hash `e4d4f60b...`; QA 68/68 + 232/232 và audit 138 cặp PASS. Chủ dự án giữ 537/543; task 543 có ngoại lệ mâu thuẫn hệ, giữ T0 và mask T1 theo manifest (`APPROVED_WITH_DECLARED_EXCEPTIONS`). Runner/scorer và script phát hành đã kiểm; 87/87 test toàn repo, 18/18 span/CLI Python 3.11 PASS. Xem [báo cáo nghiệm thu và bàn giao](docs/sprints/sprint_03/13_tasks_01_04_completion_20261002.md). Có thể bắt đầu HEUR-JW dev; 100 test còn chờ partner.

**Triển khai U1–U7 ngày 02/10/2026:** đã thêm core alignment/BIO, bộ đọc train/dev, training code DP-FT-FT/PhoBERT-CRF/proposed, protocol khóa, checkpoint/adapter/audit và verifier mã hành chính. Raw và Deepparse surface round-trip đủ **240/240 train + 60/60 dev**, giữ **1.341 span**, T1 eligible **206/53**. Kiểm thử toàn repo: **143 PASS / 8 SKIP / 0 FAIL**; runtime3.11: **73 PASS / 7 SKIP / 0 FAIL**. Torch/Deepparse/tokenizer/segmenter thật chưa có nên neural integration **PENDING_RESOURCE**, chưa train hoặc tạo metric neural. Gazetteer giữ partial, **0 mã mới được xác minh**. Xem [báo cáo U1–U7 và artifact](docs/sprints/sprint_03/19_seven_priorities_implementation_report.md), [protocol và lệnh](docs/sprints/sprint_03/17_training_protocol_v1.md), [inventory](docs/sprints/sprint_03/18_modeling_resource_inventory.md), [audit nguồn](docs/sprints/sprint_03/20_gazetteer_source_audit.md). Colab/test100 tạm gác; 246 file corpus/baseline/gazetteer/run đã khóa giữ nguyên hash.

## Cấu trúc dự án

**Thực nghiệm baseline ngày 02/10/2026:** HEUR-JW dev exact-span F1 **88.01%**, CRF-INDEP **89.82%** trên60 mẫu; track5 trường text-only **82.04% / 85.41%** micro F1 trên4.800 hàng sau loại100 hold. DP-ZS-FT chưa chạy vì giới hạn RAM và provenance/license pretrained cần xác minh. Đây là kết quả phát triển, **test gold đang chờ partner**. [Kết quả, artifact và cách chạy lại](docs/sprints/sprint_03/15_baseline_experiments_20261002.md), [inventory trước cài](docs/sprints/sprint_03/14_experiment_01_04_environment.md). Kiểm thử mới:101 test toàn repo,100 pass +1 skip;31/31 trong runtime CRF.

```text
DACN/
├── configs/
│   ├── noise_params.json                      Tham số và thống kê nhiễu hóa đơn
│   ├── label_studio_span11.xml                Cấu hình gán nhãn T0 11 span
│   └── span11_rare_seed_examples.json          Ví dụ tổng hợp có kiểm soát cho pilot
├── data/
│   ├── raw/                                  Dữ liệu nguồn OSM/Viet-Receipt-VQA; không chỉnh sửa
│   ├── reference/administrative_units/       Bảng sáp nhập hành chính 2025
│   ├── interim/osm/                          Snapshot cũ đầy đủ/cân bằng, dữ liệu hiện hành và lịch sử OSM
│   ├── interim/vqa/                          Hóa đơn thật sau lọc, chỉ dùng đo phân bố nhiễu/kiểm tra ngoài
│   ├── interim/annotation/sprint03/          Batch ứng viên T0, manifest và import pilot Label Studio
│   ├── interim/modeling/sprint03/            Alignment dẫn xuất, preflight và bằng chứng kiểm thử U1–U7
│   └── processed/
│       ├── osm/                              Địa chỉ sạch và OSM diff
│       ├── benchmark/                        Các tập benchmark đầu ra (01–07; 05 chưa có nguồn)
│       ├── annotation/sprint03/              Pilot gold T0 đã duyệt và manifest
│       ├── gazetteer/s3_v1/                  Gazetteer đa phiên bản một phần
│       ├── gazetteer/s3_v2/                  Gazetteer thời gian v2 (source register, phi nguyên tử)
│       ├── gazetteer/s3_v3_nso_2025_snapshot/ Mã mới được đối chiếu export NSO có ngày
│       └── evaluation/                       Run và bảng đánh giá baseline
├── docs/
│   ├── sprints/sprint_02/                   Tài liệu tổng kết Sprint 2
│   ├── sprints/sprint_03/                   Hồ sơ, kế hoạch và hướng dẫn Sprint 3
│   ├── proposal/                             Đề cương đồ án và tài liệu yêu cầu
│   ├── data_quality.md                       Số lượng và giới hạn chất lượng dữ liệu
│   ├── runs/<run_id>/                        Báo cáo, dashboard và tài liệu sinh từ một run
│   └── VERSIONING.md                         Quy ước phiên bản và dọn output cũ
├── notebooks/exploration/                    Notebook kiểm tra dữ liệu
├── scripts/
│   ├── 01_extract_osm.py                     Trích xuất snapshot và OSM diff
│   ├── 02_filter_vqa_receipts.py             Lọc địa chỉ từ Viet-Receipt-VQA
│   ├── 03_generate_benchmarks.py             Sinh các tập benchmark
│   ├── 04_audit_osm_diff_filters.py          Audit lý do giữ/loại từng OSM diff
│   ├── 05_run_baseline_pilot.py              Pilot phân tầng
│   ├── 06_run_baseline_full.py               Chạy toàn bộ baseline
│   ├── 07_generate_baseline_report.py        Sinh báo cáo từ prediction CSV
│   ├── 08_generate_report_materials.py       Sinh bảng phân tích theo run
│   ├── 09_audit_baseline_runs.py             Kiểm kê và xác minh run baseline
│   ├── 10_prepare_span_annotation.py         Chọn batch 01 T0 (ghi output cố định)
│   ├── 11_convert_label_studio_pilot.py      QA/chuyển export pilot thành canonical
│   ├── 12_prepare_vqa_review.py              Tạo queue rà soát VQA
│   ├── 13_build_temporal_gazetteer.py        Dựng/tra cứu gazetteer s3_v1
│   ├── 14_prepare_pilot_answer_key.py        Tạo đáp án ứng viên cho pilot
│   ├── 15_import_pilot_predictions.py        Import prediction pilot vào Label Studio
│   ├── 16_prepare_t0_corpus_batch.py         Sinh batch 02 train/dev (232 mẫu) và task Label Studio
│   ├── 17_convert_span_annotation_batch.py   QA/chuyển export Label Studio theo batch/role
│   ├── 18_audit_corpus_split.py              Audit rò rỉ group, benchmark và gần trùng SequenceMatcher
│   ├── 19_build_temporal_gazetteer_v2.py     Dựng/tra cứu gazetteer s3_v2 độc lập, tách mã cũ candidate
│   ├── 20_prepare_batch02_predictions.py     Gợi ý span từ text cho batch 02 train/dev
│   ├── 21_prepare_source_reannotation.py      Candidate 68/232 có trace nguồn và kiểm ranh giới
│   ├── 22_review_and_package_train_dev.py     Log nội dung, audit split và candidate train/dev có cách ly
│   ├── 23_run_span_dev.py                    Inference dev nhận text-only; từ chối corpus chưa duyệt
│   ├── 24_score_span_dev.py                  Chấm T0/T1 dev riêng sau khi freeze prediction
│   ├── 25_publish_train_dev.py               Phát hành version processed từ candidate đã duyệt, giữ hash và mask T1
│   └── build_baseline_dashboard.py            Sinh dashboard theo run
├── src/
│   ├── data/administrative_mapping.py       Đồ thị ánh xạ đơn vị hành chính 2025
│   ├── data/administrative_alias.py          Alias OSM đã xác minh, có vết audit
│   ├── data/coverage_reporter.py             Báo cáo độ phủ benchmark đa chiều
│   ├── data/osm_extractor.py                 Đọc lịch sử OSM và làm sạch tag
│   ├── data/noise_profiler.py                Thống kê dạng nhiễu địa chỉ
│   ├── data/synthetic/                       Sinh dữ liệu thiếu, lai và cặp ánh xạ
│   ├── evaluation/                            Adapter, contract, scorer và manifest run
│   └── utils/text_normalize.py                Chuẩn hóa văn bản và vùng miền
├── tests/                                     Kiểm thử pipeline, evaluation và span
├── third_party/                              Mã và bảng đơn vị hành chính bên thứ ba
├── requirements.txt                          Phụ thuộc Python
└── README.md                                 Hướng dẫn dự án
```

Các thư mục `.venv/`, `.venv_wsl/`, `__pycache__/` và dữ liệu nguồn lớn phục vụ chạy cục bộ, không phải mã nguồn cần chỉnh sửa.

## Hướng dẫn Cài đặt và Chạy từ Đầu (Step-by-Step Guide)

### 1. Yêu cầu hệ thống (Prerequisites)
- **Hệ điều hành:** Linux, macOS, hoặc Windows (khuyến nghị sử dụng **WSL2 Ubuntu** để tối ưu hóa việc cài đặt thư viện NLP và Libpostal).
- **Python:** Phiên bản `>= 3.10` (khuyến nghị Python 3.10 hoặc 3.11).
- **Git:** Để quản lý mã nguồn và kéo dự án về máy.
- **(Tùy chọn) XeLaTeX / MiKTeX / TeX Live:** Nếu muốn chỉnh sửa và biên dịch slide báo cáo thuyết trình `docs/sprints/sprint_02/slides_hcmut.tex`.

---

### 2. Tải mã nguồn về máy (Clone Repository)
Mở Terminal trên máy tính của bạn và chạy lệnh:
```bash
git clone https://github.com/<username>/<repo-name>.git
cd <repo-name>
```

---

### 3. Khởi tạo môi trường ảo Python và Cài đặt Thư viện

#### Cách A: Trên WSL2 / Linux (Môi trường khuyến nghị)
```bash
# Tạo môi trường ảo
python3 -m venv .venv

# Kích hoạt môi trường
source .venv/bin/activate

# Nâng cấp pip và cài đặt toàn bộ dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

#### Cách B: Trên Windows (PowerShell)
```powershell
# Tạo môi trường ảo
python -m venv .venv

# Kích hoạt môi trường (nếu gặp lỗi policy, chạy: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned)
.venv\Scripts\Activate.ps1

# Nâng cấp pip và cài đặt dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

### 4. Kiểm thử Xác thực Môi trường (Verify Setup)
Trước khi chạy bất kỳ pipeline nào, hãy chạy bộ kiểm thử hồi quy tự động để đảm bảo môi trường và các hàm xử lý hoạt động chuẩn xác:
```bash
python -m unittest discover -s tests -v
```
Kết quả cần là toàn bộ test hiện có vượt qua (`OK`); số lượng test có thể thay đổi theo phiên bản repository.

---

### 5. Hướng dẫn Chạy Thử nghiệm & Baseline (Dành cho Thành viên Mới / Partner)

Dự án đã tích hợp sẵn **Bộ 6 tập dữ liệu Benchmark v2.0** ($5.500$ mẫu chuẩn) tại thư mục `data/processed/benchmark/`. Bạn **không cần tải các file thô nặng Gigabyte** mà có thể bắt đầu chạy đánh giá ngay lập tức:

#### Bước 5.1: Chạy thử nghiệm mẫu nhỏ (Pilot Run - 20 mẫu/tập)
Dùng để kiểm tra nhanh luồng chạy của các bộ phân tích địa chỉ mà không tốn nhiều thời gian:
```bash
python -m scripts.05_run_baseline_pilot --run-id baseline_v2_pilot
```

#### Bước 5.2: Chạy đánh giá toàn diện ($13.000$ lượt dự đoán)
Chạy toàn bộ dữ liệu trên các baseline đã tích hợp:
```bash
python -m scripts.06_run_baseline_full --run-id baseline_v2
```

#### Bước 5.3: Xuất báo cáo, bảng chỉ số và Dashboard trực quan
Sau khi chạy xong dự đoán, sinh toàn bộ bảng phân tích thống kê và giao diện dashboard HTML:
```bash
# Sinh báo cáo Markdown chi tiết
python -m scripts.07_generate_baseline_report --run-id baseline_v2

# Tổng hợp bảng so sánh, ma trận đối đầu và nghiên cứu ca lỗi
python -m scripts.08_generate_report_materials --run-id baseline_v2

# Xây dựng Dashboard HTML trực quan
python -m scripts.build_baseline_dashboard --run-id baseline_v2
```
*Kết quả:* Mở file `docs/runs/baseline_v2/baseline_dashboard.html` bằng trình duyệt web để xem biểu đồ và các ca lỗi.

---

### 6. (Tùy chọn) Tái tạo Toàn bộ Pipeline Dữ liệu Thô từ Đầu (Full Raw Data Reproduction)

Chỉ thực hiện phần này nếu bạn muốn tự trích xuất lại dữ liệu từ tệp lịch sử OpenStreetMap và Parquet hóa đơn gốc:

1. **Chuẩn bị file nguồn:**
   - Tải file OSM full-history `vietnam-internal.osh.pbf` (khoảng 756 MB) đặt vào thư mục `data/raw/osm/`.
   - Tải các file Parquet Viet-Receipt-VQA đặt vào thư mục `data/raw/viet_receipt_vqa/`.
2. **Chạy tuần tự các script trích xuất:**
   ```bash
   # Bước 1: Quét lịch sử OSM, trích snapshot cũ mốc 30/06/2025 và OSM diff
   python -m scripts.01_extract_osm

   # Bước 2: Lọc địa chỉ hóa đơn Viet-Receipt-VQA và đo phân bố nhiễu
   python -m scripts.02_filter_vqa_receipts

   # Bước 3: Sinh 6 tập benchmark chính thức (Data 01-07)
   python -m scripts.03_generate_benchmarks

   # Bước 4: Xuất báo cáo audit chi tiết lý do giữ/loại từng OSM diff
   python -m scripts.04_audit_osm_diff_filters
   ```

---

### 7. (Tùy chọn) Cài đặt Thư viện C Libpostal trên WSL/Ubuntu

Để chạy baseline CRF của **Libpostal** thật sự, bạn cần biên dịch thư viện C theo tài liệu OpenVenues trên WSL:
```bash
# Cài đặt công cụ biên dịch
sudo apt-get update
sudo apt-get install -y build-essential libsnappy-dev autoconf automake libtool pkg-config git curl

# Clone và build Libpostal C library (cần ~2GB RAM & dung lượng ổ cứng để tải model dữ liệu)
git clone https://github.com/openvenues/libpostal
cd libpostal
./bootstrap.sh
./configure --datadir=$HOME/.local/share
make -j4
make install
sudo ldconfig

# Nạp đường dẫn thư viện động trước khi chạy code Python
export LD_LIBRARY_PATH="$HOME/.local/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
```

---

### 8. Biên dịch Slide Báo cáo Thuyết trình (Beamer HCMUT)

Slide báo cáo tiến độ đồ án được thiết kế chuyên nghiệp bằng LaTeX Beamer theo template chuẩn Trường Đại học Bách Khoa - ĐHQG-HCM:
- **File mã nguồn:** `docs/sprints/sprint_02/slides_hcmut.tex`
- **File ảnh nền & logo:** `docs/assets/`

Để biên dịch slide ra file PDF:
```bash
cd docs
xelatex -output-directory=sprints/sprint_02 -interaction=nonstopmode sprints/sprint_02/slides_hcmut.tex
```
*Kết quả xuất ra tại:* `docs/sprints/sprint_02/slides_hcmut.pdf`.

## Kiểm thử

`tests/test_data_pipeline.py` là bộ kiểm thử hồi quy cho pipeline. File này không sinh benchmark; nó tạo dữ liệu nhỏ tạm thời để kiểm tra các quy tắc quan trọng trước khi chạy trên dữ liệu lớn:

- Làm sạch tag OSM, giữ tiếng Việt và loại chữ ngoài Latin.
- Không tạo cặp khi phiên bản mới bị xóa hoặc không còn tag địa chỉ.
- Sinh dữ liệu thiếu trường đúng tỷ lệ, giữ `GT_*` và cho kết quả lặp lại với cùng seed.
- Sinh Data 2 nhiễu tổng hợp có ground truth, cân bằng hai hệ quy chiếu và không giữ nguyên chuỗi sạch.
- Tra cứu tỉnh mới và từ chối tỉnh không xác định.
- Kiểm tra thống kê nhiễu có mẫu số rõ ràng.
- Kiểm tra đồ thị ánh xạ giữ đúng quan hệ 1-N, N-1 và M-N; chỉ dữ liệu có bằng chứng trực tiếp mới dùng đích của ca mơ hồ.
- Giữ cặp OSM diff có ID chỉ nằm trong snapshot đầy đủ, không làm mất chúng vì snapshot cân bằng của tập 03.
- Ghi vết alias hành chính và không nhầm "chưa có hình học" với "hình học không đổi" trong audit.

Chạy kiểm thử từ thư mục gốc:

```powershell
python -m unittest discover -s tests -v
```

## Nguyên tắc chất lượng

- Không làm giả dữ liệu quan sát. Riêng Data 2 là nhiễu tổng hợp có kiểm soát: phải giữ chuỗi gốc, `GT_*`, seed và loại nhiễu để phục vụ đo độ bền baseline.
- `configs/noise_params.json` là ước lượng regex trên chuỗi hóa đơn, không phải nhãn xác nhận thủ công.
- Data 03 là benchmark sạch hoàn toàn của hệ cũ: 1.500 dòng đủ cả 5 trường (`SoNha`, `TenDuong`, `PhuongXa`, `QuanHuyen`, `TinhThanh`), không có dòng thiếu tự nhiên.
- Data 04 là benchmark thiếu trường có kiểm soát: 800 dòng (400 cũ, 400 mới) sinh từ nguồn sạch rồi mới xóa trường theo `KieuThieu`, bảo toàn nguyên vẹn `GT_*` trước khi xóa; `QuanHuyen` rỗng ở hệ mới phản ánh cấu trúc hai cấp (không tính là lỗi).
- `vietnam-sap-nhap-phuong-xa.csv` là nguồn chuẩn duy nhất cho ánh xạ 2025. Mỗi dòng là một cạnh: tỉnh cũ + quận/huyện cũ + phường/xã cũ → tỉnh mới + phường/xã mới.
- Không thu gọn đồ thị thành từ điển tên phường. Quan hệ được tính bằng bậc hai đầu mút: `C/1-1`, `A/1-N`, `B/N-1`, `M/M-N`.
- Cặp từ OSM diff có thể thuộc mọi quan hệ, vì đối tượng OSM đã ghi nhận đích thực tế. Cặp dựng từ snapshot cũ chỉ dùng khi đơn vị cũ có đúng một đích xác minh (`B` hoặc `C`); `A` và `M` không được suy đoán khi không có hình học/toạ độ.
- CSV xuất UTF-8-sig; generator dùng seed cố định để tái lập.

## Trạng thái nguồn hiện tại

- Snapshot hệ cũ đầy đủ: 26.961 đối tượng hợp lệ trước 30/06/2025, dùng để đối chiếu ID OSM diff.
- Snapshot hệ cũ cân bằng: 16.242 đối tượng (10.000 Bắc, 1.317 Trung, 4.925 Nam), trong đó có 8.848 đối tượng sạch đủ cả 5 trường dùng để lấy mẫu cho tập 03 và các tập con dựng an toàn.
- Hệ mới hai cấp: 1.000 địa chỉ đã xác minh và lấy mẫu có seed cố định.
- Data 2: 1.000 chuỗi nhiễu tổng hợp (500 hệ cũ/500 hệ mới), sinh tái lập bằng seed `42` từ nguồn sạch; baseline chỉ đọc `ChuoiDiaChi`, còn `GT_*` là đáp án chấm điểm.
- Hóa đơn thật: 146 chuỗi sau lọc từ 1.659 bản ghi thô, dùng để ước lượng phân bố nhiễu và làm kiểm tra ngoài, không còn là Data 2 chính thức.
- Bảng chuẩn có 10.602 cạnh, 10.040 đơn vị cũ và 3.321 đơn vị mới: 137 cạnh 1-1, 3 cạnh 1-N, 9.432 cạnh N-1 và 1.030 cạnh M-N.
- Audit OSM diff hiện có 1.631 dòng: 612 cặp quan sát được xác minh; không còn nhóm `not_in_old_snapshot` vì audit tra ID trên snapshot đầy đủ. Alias được ghi trong `AliasDaApDung`; các cạnh không xác minh được không bị ép ghép.
- Tập 07 hiện có 600 cặp OSM diff trực tiếp đã lấy mẫu phân tầng: 244 `B/N-1`, 356 `M/M-N`, 0 `C/1-1`, 0 `A/1-N`. Tập không nhân bản mẫu để đạt quota; xem [báo cáo coverage](docs/benchmark_coverage_report.md) để biết các khoảng trống bằng chứng và độ lệch vùng miền.
- Tập 05 địa chỉ dựa trên mốc chưa có nguồn đã xác minh nên chưa xuất.
- Tập 06 sau kiểm tra nhãn không còn chuỗi đầu vào trùng giữa C2/C3.

## Đánh giá baseline

Baseline dùng `vietnamadminunits==1.0.4` và Libpostal thật qua `postal==1.1.11`. Python binding cần thư viện C và model data Libpostal được cài trước theo [hướng dẫn chính thức của OpenVenues](https://github.com/openvenues/libpostal#installation-maclinux) và [Python binding](https://github.com/openvenues/pypostal#installation). Trong WSL hiện tại, thư viện C và model mặc định nằm dưới `~/.local`; nạp thư viện động trước khi chạy:

Bản C dùng cho lần đánh giá này lấy từ commit `25099c506612b34b23b1bfe286ca6321fcf06f35` của OpenVenues; model mặc định (không dùng bản Senzing). Hệ thống cần vài GB dung lượng trống và Python development headers để build binding.

```bash
cd /mnt/d/DACN
source ~/.venv_dacn/bin/activate
export LD_LIBRARY_PATH="$HOME/.local/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m scripts.05_run_baseline_pilot --run-id baseline_v2_pilot
python -m scripts.06_run_baseline_full --run-id baseline_v2
python -m scripts.07_generate_baseline_report --run-id baseline_v2
python -m scripts.08_generate_report_materials --run-id baseline_v2
python -m scripts.build_baseline_dashboard --run-id baseline_v2
```

`05` và `06` kiểm tra schema, BOM, hash, nhãn và tính duy nhất của 6 CSV trước khi gọi công cụ. Pilot chọn phân tầng 20 dòng/tập; full run lưu prediction 9 cột, raw response và manifest riêng tại `data/processed/evaluation/runs/<run_id>/`. Cùng run ID, `07`, `08` và dashboard sinh report/tables/case có truy vết tại `docs/runs/<run_id>/`. Data 01/02/03/04 cung cấp trước mode hệ quy chiếu cho VietnamAdminUnits; Data 06 thử cả hai mode; Data 07 chỉ chấm chuyển đổi cũ → mới trên phường/xã và tỉnh/thành. Không có phép đo tự động T1 hoặc chiều chuyển đổi ngược. Runner từ chối ghi đè run trừ khi truyền `--overwrite-run` rõ ràng.

#### Đánh giá theo protocol fuzzy mới

Run `baseline_v2` là kết quả frozen theo protocol cũ. Để tạo kết quả mới, dùng run ID riêng; script báo cáo sẽ từ chối áp dụng protocol mới lên manifest cũ. Protocol mới giữ exact match và thêm normalized Levenshtein similarity liên tục, báo rõ mẫu số, chuẩn hóa NFC/casefold/khoảng trắng và giữ dấu cùng tiền tố loại đơn vị. Data 07 vẫn xác định đúng đích hành chính bằng đối chiếu exact sau chuẩn hóa an toàn; độ giống chuỗi chỉ là chẩn đoán.

Kiểm toán Sprint 3 đã xác nhận `baseline_v3_fuzzy` là mốc baseline 5 trường theo protocol này; `baseline_v2` vẫn frozen và chưa xác minh được toàn bộ snapshot mã lịch sử. Xem [báo cáo kiểm toán](docs/sprints/sprint_03/baseline_run_audit.md) và [ma trận mô hình Sprint 3](docs/sprints/sprint_03/model_matrix.md) trước khi so các cấu hình tiếp theo.

Đối với T0, [hướng dẫn vận hành S3-01 đến S3-03](docs/sprints/sprint_03/03_s3_01_03_operations.md) mô tả pilot 68 mẫu trên Label Studio, cổng kiểm duyệt VQA/Data 05 và gói gazetteer đa phiên bản một phần. [Pilot gold T0 68 mẫu](data/processed/annotation/sprint03/pilot_gold_v1.jsonl) đã được duyệt ngày 29/09/2026 với [biên bản và hash](docs/sprints/sprint_03/pilot_gold_approval.md). 100 ứng viên test T0 vẫn giữ riêng và chưa gán nhãn; chưa thể báo F1 T0 trên test. Các script `11_convert_label_studio_pilot.py`, `12_prepare_vqa_review.py`, `13_build_temporal_gazetteer.py` lần lượt kiểm export, chuẩn bị queue VQA và dựng gazetteer. Data 05 quan sát vẫn chưa được duyệt.

```bash
python -m unittest discover -s tests -v
python -m scripts.05_run_baseline_pilot --run-id baseline_v3_fuzzy_pilot
python -m scripts.06_run_baseline_full --run-id baseline_v3_fuzzy
python -m scripts.07_generate_baseline_report --run-id baseline_v3_fuzzy
python -m scripts.08_generate_report_materials --run-id baseline_v3_fuzzy --materials-id v4_fuzzy
```

Materials v4 xuất metric theo điều kiện/trường và hai bảng chẩn đoán tách biệt: strata cấu trúc `KieuThieu`/`KieuLai` và trace converter không gian Data 07. Đây không phải xác suất uncertainty, calibration/ECE hay bằng chứng gần ranh giới. Report v4 chỉ chạy với manifest mang scoring protocol mới; không ghi đè hoặc tái diễn giải run v2.

## Bắt đầu theo dõi Sprint 3

Đọc [mục lục Sprint 3](docs/sprints/sprint_03/README.md) trước khi chạy script. Train/dev hiện hành là `corpus_train_dev_v2` (240/60); 68 + 232 đã được duyệt và 138 cặp gần giống đã qua phân xử. HEUR-JW/CRF-INDEP có kết quả dev; gazetteer `s3_v2` vẫn partial. U1–U7 đã có mã/protocol và bằng chứng kiểm thử độc lập, còn chờ tài nguyên để tích hợp neural thật. [Báo cáo U1–U7](docs/sprints/sprint_03/19_seven_priorities_implementation_report.md) ghi phạm vi hoàn thành và blocker; Colab và mọi công việc test100 tạm gác trong lượt này. Các báo cáo gán nhãn trước là lịch sử, không yêu cầu gán lại 300 mẫu.

Lưu ý vận hành: `scripts/10_prepare_span_annotation.py` và lệnh `build` của `scripts/13_build_temporal_gazetteer.py` ghi vào các đường dẫn cố định. Không chạy lại trên artifact hiện hành; kế hoạch Sprint 3 quy định tạo batch/gazetteer phiên bản mới. Việc thu thập địa chỉ mốc/hướng thật hiện được tạm hoãn.

Đề cương: [docs/proposal/de-cuong-dacn-dia-chi-tieng-viet.pdf](docs/proposal/de-cuong-dacn-dia-chi-tieng-viet.pdf).
