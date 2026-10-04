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
  utils/text_normalize.py                   Chuẩn hóa văn bản và vùng miền
  modeling/                                Alignment, BIO, trainer, CRF, T1, checkpoint, protocol và resource gate

tests/
  test_data_pipeline.py                     Kiểm thử hồi quy pipeline
  test_evaluation_pipeline.py                Kiểm thử protocol, manifest và báo cáo
  test_span_evaluation.py                    Kiểm thử scorer span T0

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

**05/10/2026 — Test gold và GPU Kaggle:** owner giao tự chốt694(task695) và16T1exceptions; đã ghi decision/approval gắn raw round2 d51b69c9..., QA100/100. Currentrelease `corpus_v1_release2`240/60/100, `test_gold_v1_release2`100/446span,64T1eligible/20null/16excluded; tổng17mask với543dev, giữ toàn bộT0. Không sửa raw/gold/split cũ. Metadatafix không coi observed_or_existing_benchmark là observed100; registrytrain/dev từqueuepin, testprovenance giữunverified khicombined. Smokeprivate `huynq16/dacn-s3-smoke-gpu-20261005-v1/1` PASS thật2TeslaT4, actualalignment300/300,2model optimizer/save/reload; đủ checkpoint tải về/hash PASS. Fullc01/c02 mỗiPhoBERT-CRF/PROPOSED-DYN chỉtrain/dev; PCRF c01/c02 devF1 .9333/.9389, chọnc02 theo protocol; Dyn c01/c02 devF1 .9333/.9474, chọnc02; cả4fullruns/hash/recompute accepted. T1DynmacroF1 .5996/LaiF1=0; constrainton/off cùngT0, không chứng minh cải thiện. Neural locks/preflight3PASS tại workspace khôi phục submitted source; fixturebridge11PASS. Chi tiết đọc report47 và evidence `release_and_kaggle_20261005_v1`, không coi submit làcomplete. Chưa realtest inference/score. CLI2.2.4 eagerdownload MemoryError: modulekaggle_artifacts/script60/fetch50stream1MiB/version_labelv1/hashgate, selectionprofile giữ report+best/last; epochkhác remote-only, reuse hardlink phải khớp index tải mới; không sửa vendor/cài lại. WSL cóE_UNEXPECTED rồi hồi phục; runtimeWindows cósẵn chỉfallbackstdlib, mọioutputD,0cài local. Fullsuite262=254PASS+8SKIP,0FAIL, nghiệm thu TMPDIR trênD. Frozen1313hash+4rawsize/mtime PASS. Colab handoffv4 closure/ZIP/notebook PASS, lock nhẹ final_selection_v5 giữ dev choice/preflight100 text-only, chưa testinfer. GiữAI-assisted/IAA NOT_MEASURED,VQA HOLD,Data05DEFERRED,DPlicense/native blocked; gold/answer/raw/weights khôngstageGit. Các pending100 phía dưới làlịch sử.

**Local P0/L1–L5 04/10/2026, round2:** raw `test100_assisted_round2.json` SHA `d51b69c981e775e0e51ac3ed5a3ef4c91d845f5e7a900c2f3d4c79f98ca758a4` có100task/103annotation,0missing. Kiểm lại equivalent602/653 chọn599/651;695 còn694/695 khácflag nên99converted/1multiple,0structuralissue. Không sửa raw theo yêu cầu owner.16T1exception proposed chưa được duyệt:602/603/609/611/613/615/617/620/621/623/629/630/633/663/664/665; không tự mask hoặc duyệt gold. Source-identity/split240/60/100 audit138decisions PASS. Publisher54, finalrunner55/scorer56, audit57, Colabruntime58/finalbundle59 đã triển khai; fixture dùng scope riêng không mở realtest. Gói hiện hành evidence `local_finish_before_colab_20261004_v2/handoff_v3/`, notebook `local_ready_train_dev_v3.ipynb`; đủ trace/generation_manifest/queue232, không chứa100test/rawexport. Resource legal symlink được dereference bên trong root, archive members giữ hash/permissions. Giải nén+CPUpreparation240/240+60/60EXACT,T1eligible206/53; không thay bằng chứng actualPhoBERT300/300. Light selection locks `final_selection_v2/` chọn từ frozen dev; neural locks PENDING. Tests247=239PASS+8SKIP, chuyên biệtTorch73/73 vàCRF50/50 (không cộng các suite chồng lặp),1313frozenhash+4rawsize/mtime unchanged.0package/model cài/tải mới; artifactGB/GiB trong report46. L1/L2 BLOCKED_HUMAN_ADJUDICATION; không phát hành100gold hoặc chấm test thật, không cloud/neuraltraining. DPfullFastText vẫn RAM/hash/checkpointlicense blocked. Đọc reports44–46 trước triển khai tiếp; giữ543maskT1 và raw/split/gold/gazetteer/run. Trạng thái round1 dưới đây là lịch sử, không yêu cầu sửa lại mẫu thiếu đã bổ sung.

**QA test100 04/10/2026:** chủ dự án cho phép đọc raw export test để QA annotation. File `exports/test_assisted_v1/test100_assisted_round1.json`, SHA `ad11f44c...`, có 99 task/102 annotation; chọn hai bản tương đương cho 602/653 → 98 candidate, thiếu `s3_7d9d2bd6ff632625`, task 695 còn hai bản khác flag. Task 663/664 cần sửa/chốt hệ, 14 ca cần căn cứ T1 và 683 cần lý do privacy flag; xem report41 và evidence `test100_review_20261004_v3/`. Script17 có assisted gate explicit manifest/hash/version, blind mặc định vẫn chặn prediction; bỏ role không vượt được gate. Script53 snapshot/read-only QA, không tự duyệt gold. **215 test = 207 PASS + 8 SKIP**, 550 frozen hash + 4 raw size/mtime không đổi; 0 cài mới. Chưa phát hành test gold/chấm test hoặc chạy cloud trong lượt này. Không dùng test QA để tune/thay model. Plan42 local L1–L5 rồi Colab; gói Colab cũ phải kiểm phụ thuộc trace/generation_manifest/queue của prepare_data. Giữ mask T1 của 543, train/dev và frozen runs. Các trạng thái trước phía dưới là lịch sử theo từng lượt.

**Kaggle 04/10/2026:** scripts50/51/52, kaggle_handoff/kaggle_remote và profile GPU riêng đã triển khai. Local CLI kaggle2.2.4+32 dependency cài isolated trênD; inventory38 trước cài, docs39 cho thao tác. Private dataset train240/dev60/PhoBERT đã upload, không có test100/raw exports/credentials/Gazetteer. Script job version1 được API nhận nhưng nvidia-smi thiếu: không vượt GPU gate, không cài cloud neural hoặc tạo metric/checkpoint pretrained. Notebook retry v3 dùng lại immutable dataset v2; phải đọc report40/evidence cho kết quả, không gọi COMPLETE của Kaggle là SMOKE_PASS. Full training mặc định tắt; chỉ mở với evidence GPU smoke đủ2model/hash/300alignment và explicit flag. Không thay corpus/split/task543T1mask, frozen550hash+4rawsize unchanged. Không dùng trọng số smoke làm model selection. Không tự mở training hoặc đọc test100.

**04/10/2026 — Quyền mới cho annotation test100:** chủ dự án yêu cầu AI gán gợi ý 100 test để chủ dự án rà/Submit. Đã tạo `data/interim/annotation/sprint03/test100_assisted_v1/`: 100 task/446 span, đủ hệ span; 15 ca ưu tiên rà nhãn/ranh giới, 56 T1 để trống. Chỉ prediction candidate, chưa human annotation/gold/test metric; agreement độc lập NOT_MEASURED. Đọc protocol bổ sung `docs/sprints/sprint_03/37_test100_ai_assisted_annotation.md`; báo AI-assisted human-reviewed sau duyệt, không gán mù. Giữ blind package cũ/split/train-dev/run; quyền mới không mở train/tune/chấm test. Không dùng baseline được đánh giá/GT để tạo gợi ý. Script15 giữ chặn test; script49 là luồng riêng có acknowledgement/hash gate. Không công khai answer package trên nhánh partner mù; không cài/tải thêm.

**P0/U1–U6 trước Colab, lượt tiếp tục 03/10/2026:** evidence `data/interim/modeling/sprint03/pre_colab_20261003_resume_v1/`. SOAP NSO 30/06/2025:63/686/9843;1429 row parent-link gaps không promote. Exact verified8607 mã cũ (62 tỉnh/561 huyện/7984 xã),2187 unresolved. Gazetteer mới `s3_v4_nso_dual_snapshot` và metadata release `s3_v4_nso_dual_snapshot_release2`, giữ14149entity/10597edge/187alias/5non-atomic, tổng11962 code evidence cùng3355 mã mới từ v3; chỉ hai snapshot cu2025-06-30/moi2025-07-01, không suy legal interval. Nguồn/CSV redistributionterms chưa rõ nên rawsource và gói mới giữ local. HEURrulev4 sweep6candidate F1dev88.01% (không cải thiện); CRFfeaturev2 grid8candidate chosenctx1,c1=.1,c2=1 F1dev90.56%, T1NOT_IMPLEMENTED. Track5field4800rows excluded100hold F181.99%/85.59%. Mọi inference text-only; task543maskT1,giữT0.16newruns audited,550frozenhash+4rawsize unchanged;actualalignment300/300 evidencehash verified. Không cài package/model mới local (0bytes); chuẩn bị CUDA128profile riêng/Python3.11, notebook,bundles,code CLI DPzero gatedlicense/hash/10GiBhostRAM, không nativefullpretrained run. Colab/neuraltraining/test100 NOT_EXECUTED. Đọc reports31–36/readiness final để lấy tests/GitSHA/GB thực đo; không suy Sprint3 hoàn tất chỉ vì bàn giao code. Giữ nhánh partner `print3_label100test`, code lên `sprint3_huy`; không stage rawexport/venv/cache/weights/interim/source chưa rõ quyền dùng.

Đã có trong repository:

- Trích xuất snapshot OSM cũ và các thay đổi địa chỉ từ lịch sử OSM.
- Lọc địa chỉ Viet-Receipt-VQA, khử trùng lặp và đo phân bố nhiễu để sinh Data 2 tổng hợp có ground truth.
- Sinh benchmark hệ cũ/hệ mới, thiếu trường, địa chỉ lai và cặp ánh xạ có thể truy nguyên nguồn.
- `baseline_v3_fuzzy` đã qua audit trong track benchmark 5 trường; `baseline_v2` được giữ frozen. Đây chưa phải kết quả T0 11 span hoặc T1.
- Pilot gold T0 68 mẫu đã được duyệt ở `data/processed/annotation/sprint03/pilot_gold_v1.jsonl`, schema `s3-span-v1.1`; manifest lưu hash và người duyệt.
- Batch 02 có 232 ứng viên train/dev, test hold có 100 mẫu benchmark. Import Label Studio chỉ chứa `sample_id` và `text`. Preflight phân bổ 240 train / 60 dev / 100 test, đăng ký 172 nguồn cha và yêu cầu phân xử 138 cặp gần giống. Prediction chỉ tạo cho batch 02 train/dev.
- Gazetteer `data/processed/gazetteer/s3_v2/` gồm 14.149 entity, 10.597 cạnh cấp xã, 187 alias audit, và 5 chuyển đổi cấp huyện→đặc khu tra được qua lookup. 10.035 mã xã cũ vẫn là ứng viên bên thứ ba. Mã xã mới khớp bảng ánh xạ trong repo; xuất xứ và giấy phép bên ngoài của bảng còn cần xác minh. Trạng thái `PARTIAL_OLD_CODES_UNVERIFIED`.
- Các kiểm thử Sprint 3 liên quan đã qua; bộ kiểm thử toàn repo cần chạy trong WSL có `osmium` và `vietnamadminunits`.
- Ngày 01/10/2026, bộ kiểm thử toàn repo đạt 64/64 trong WSL. Gói `reannotation_v2_release1` giữ nguyên 68 + 232 ID/text, có 245 + 1.059 span và 473 mục review; một thành phần số nhà được abstain vì ranh giới. Chủ dự án chọn prediction cho cả 68 và 232, nên agreement độc lập `NOT_MEASURED`. Gói test-only có version/hash tại `docs/sprints/sprint_03/annotation_handoff/test100_v1/`, nhánh `print3_label100test`, sẵn sàng gán mù theo protocol v1.0 trong lần bàn giao do chủ dự án yêu cầu. 138 quyết định `distinct` có lý do/người duyệt Huy đã được áp dụng; preflight mới đạt `AUDIT_PASS_WITH_HUMAN_NEAR_DUP_REVIEW` trong `split_preflight_review_20261001/`.
- Ngày 02/10/2026, nhiệm vụ 1–4 đã phát hành `data/processed/annotation/sprint03/corpus_train_dev_v2/`: 240 train / 60 dev, 1.057 / 284 span, `TRAIN_DEV_APPROVED_TEST_PENDING`. Snapshot batch cuối `e4d4f60b...`; QA 68/68 + 232/232, audit 138 cặp PASS và canonical khớp raw. Chủ dự án chốt giữ 537/543; 543 giữ PhuongXa/cu cùng T1 moi nên ghi ngoại lệ `APPROVED_WITH_DECLARED_EXCEPTIONS`, chỉ mask T1 (ID `s3_60931c369cbd85ef`), giữ toàn bộ T0. Agent huấn luyện/chấm sau này phải đọc `evaluation_exclusions.t1`; không sửa nhãn raw hoặc mặc định coi ngoại lệ là gold T1 nhất quán. Script 22/25 ghi quyết định gắn hash và phát hành bất biến; 23/24 tách inference text-only khỏi gold và tự mask T1 khi chấm. 87/87 test toàn repo, 18/18 span/CLI Python 3.11 PASS. Xem `docs/sprints/sprint_03/13_tasks_01_04_completion_20261002.md`.

**Cập nhật U1–U7 ngày02/10/2026:** đã triển khai `src/modeling/`, ba adapter neural, scripts30–35, configs/protocol `s3-training-v1` khóa hash và verifier mã hành chính. Derivative hiện hành `data/interim/modeling/sprint03/seven_priorities_20261002_v1/prepared_v3/`: raw và DP surface **240/240 + 60/60 EXACT**, giữ1057+284 span,0 unrepresentable; T1eligible206/53 theo manifest, giữ T0 của543. PhoBERT raw-offset processor có fixture tests nhưng coverage tokenizer/segmenter thật vẫn pending. Không cài/tải dependency hoặc pretrained mới; Torch/Transformers/Deepparse/Poutyne/py-vncorenlp/Java thiếu, RAM fullFastText và đĩa lưu checkpoint chưa đủ. Tất cả neural integration `INTEGRATION_PENDING_RESOURCE`, training `TRAINING_DEFERRED_BY_USER`; chưa có prediction/metric neural thật. Bộ49 test mới **42 PASS/7 SKIP**; toàn repo **151=143 PASS+8 SKIP**, runtime3.11 **80=73 PASS+7 SKIP**,0FAIL. AST28file/import27module/help6/preflight3 PASS; preflight thiếu tài nguyên exit2. Audit246file frozen giữ nguyên hash. Gazetteer giữ partial,0 mã mới được nâng trạng thái; lookup/verifier giữ zero đầu, khóa cha, ngày và mọi đích. Xem `docs/sprints/sprint_03/19_seven_priorities_implementation_report.md`, protocol17, inventory18 và nguồn20. Colab và mọi công việc test100 tạm gác. Không gọi code/unit test là tích hợp pretrained đã xác minh; không mở training trước khi được phép và các cổng resource/integration đã qua.

Chưa hoàn thiện hoặc chưa có nguồn đủ mạnh:

**Follow-up sáu việc 03/10/2026 (thay trạng thái resource pending cũ):** đã audit615ca (584xã+26huyện+5huyện thiếu mã), tái tạo counts;0mã mới verified, nguồn export/quyền dùng còn gap, không phát hành gazetteer mới. Source/register/report24, frozen error analysis25 tách T0/5field, không chạy hoặc chấm lại baseline. Runtime `data/interim/modeling/sprint03/runtime_neural_d_v1/` Python3.11.16 + Torch2.8.0+cpu/Transformers4.57.1/Deepparse0.11.0/Poutyne1.17.4/py-vncorenlp0.1.4 cài riêng trênD, không thay env hiện có. Resources localD: PhoBERT revision01daacda68afe13d83023d16ec647239e344a1e6, VnCoreNLP commit62bbc58fe5d113c898eae112656be97dcf50b3a0, TemurinJRE17.0.20.1+1. Actual API PASS; PhoBERT segmentation/BPE alignment217/240train+54/60dev exact,29reject do thay vị trí dấu; không bỏ mẫu/sửa gold. Pretrained short CPU forward PASS, không train/predict benchmark/metric mới. Fix checkpoint tempfile và NFC chỉ cho segmenter input, giữ raw offsets. Test159=151PASS+8SKIP trong env chính;50/50neuralD và13/13CRF PASS,251frozenhash giữ nguyên. Tổng cài/cache/resources2.453.588.804bytes=2,453588804GB=2,285082642GiB; ngoại lệ một log Ubuntu Pro có sẵn bị login shell cập nhật, lệnh tiếp dùng `bash --noprofile --norc`. Xem reports26/27 và evidence `task_01_06_20261003_v1/`. Không mở train trước policy29ca/resource/disk gates và quyền train. FullFastText vẫn RAM/license blocked; Colab/test100 tạm gác. Các đoạn trạng thái ngày02/10 phía dưới là lịch sử.

**Cập nhật thực nghiệm 02/10/2026:** [inventory](docs/sprints/sprint_03/14_experiment_01_04_environment.md) ghi runtime WSL cô lập `data/interim/evaluation/sprint03/runtime_py311`, Python3.11.16, python-crfsuite0.9.12; không thay env hiện hữu. HEUR-JW dùng explicit s3_v2, dual_snapshot, threshold0.86, margin0.02 và reject/tie trace; T0 dev F1 **88.01%**. CRF-INDEP train240/dev60, BIO23, context2,c1=0.05,c2=0.1; T0 dev F1 **89.82%**, T1 `NOT_IMPLEMENTED`. Track5 trường text-only chấm4.800 hàng01/02/03/04/06 sau loại100 hold bằng source_line-2/text hash, micro F1 **82.04%/85.41%**. DP-ZS-FT có adapter/mapping/test nhưng **chưa chạy pretrained**: WSL RAM3.64GiB+swap1GiB thấp hơn full FastText8–10GB; license weights cần xác minh. Không cài Deepparse/Torch/Transformers hay thay cấu hình toàn máy. Scripts26/27/28 train/sweep/infer-score, script29 audit cuối; resource/model/input/output/code hashes trong mỗi run. **101 test toàn repo:100 pass+1 skip**, **31/31** trong runtime CRF. [Báo cáo thực nghiệm và tái lập](docs/sprints/sprint_03/15_baseline_experiments_20261002.md). Không gọi điểm dev là test cuối hoặc bỏ mask T1 của543.

- Chưa có corpus đủ ba split: train/dev v2 đã phát hành; test100 vẫn pending. Chưa phát hành `corpus_v1` ba split hoặc chấm test cuối. HEUR-JW/CRF đã có điểm dev frozen; các neural pipeline U1–U7 còn chờ tích hợp resource thật. Dev có0 MocDinhVi,0 ToaNha/CanHo,1 HuongDi; không dùng điểm nhãn ít/không support để kết luận vững. VQA/Data05 giữ hoãn/hold; không đọc hoặc thao tác test100 trong lượt U1–U7.
- Agreement giữa người gán `NOT_MEASURED` vì mới có một người gán độc lập.
- Rà soát PII/quyền sử dụng và ID tài liệu của VQA; không dùng VQA cho train/dev/test khi chưa qua clearance (trạng thái `HOLD`).
- Data 05 địa chỉ thật có mốc và hướng đang tạm hoãn (`DEFERRED_BY_USER`); ví dụ tổng hợp không được tính là dữ liệu quan sát.
- Danh mục mã hành chính cũ chính thức từ Nghị định/Quyết định Nhà nước (hiện chưa có nguồn chính thức trong repo; mã cũ đang ở trạng thái candidate).
- Các baseline Sprint 3 còn lại, T1 tự động, T2 phân giải ngữ cảnh và T3 đối sánh qua thời gian.
- PhoBERT/adapters đã có mã ở U1–U7, nhưng tích hợp tokenizer/segmenter/encoder thật và training chưa thực hiện. Tầng LLM + RAG, API FastAPI/Docker vẫn ngoài phạm vi Sprint3 hiện hành.

Đọc `docs/data_quality.md` trước khi lấy số lượng mẫu làm kết luận, vì các tập được sinh lại từ nguồn trung gian có thể thay đổi theo phiên bản dữ liệu.

## 10. Checklist xử lý một yêu cầu mới

1. Xác định yêu cầu đụng đến nguồn, dữ liệu trung gian, generator, hay tài liệu.
2. Đọc schema CSV và các nơi đang sử dụng file trước khi sửa.
3. Không suy diễn quan hệ hành chính khi thiếu bằng chứng từ bảng đối chiếu.
4. Thực hiện thay đổi nhỏ nhất đáp ứng yêu cầu.
5. Chạy kiểm thử phù hợp và kiểm tra đầu ra.
6. Cập nhật tài liệu khi thay đổi hợp đồng dữ liệu, cấu trúc hoặc trạng thái dự án.
