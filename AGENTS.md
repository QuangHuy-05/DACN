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

Chưa hoàn thiện hoặc chưa có nguồn đủ mạnh:

- Corpus T0 train/dev/test hoàn chỉnh: lượt rà 68 pilot, Batch 02 (232 mẫu) và test benchmark (100 mẫu) đang chờ export/người duyệt trước khi ghép thành `corpus_v1/`; cổng 138 cặp gần giống đã qua preflight với quyết định người ngày 01/10, cần audit lại theo gold cuối khi đóng gói.
- Agreement giữa người gán `NOT_MEASURED` vì mới có một người gán độc lập.
- Rà soát PII/quyền sử dụng và ID tài liệu của VQA; không dùng VQA cho train/dev/test khi chưa qua clearance (trạng thái `HOLD`).
- Data 05 địa chỉ thật có mốc và hướng đang tạm hoãn (`DEFERRED_BY_USER`); ví dụ tổng hợp không được tính là dữ liệu quan sát.
- Danh mục mã hành chính cũ chính thức từ Nghị định/Quyết định Nhà nước (hiện chưa có nguồn chính thức trong repo; mã cũ đang ở trạng thái candidate).
- Các baseline Sprint 3 còn lại, T1 tự động, T2 phân giải ngữ cảnh và T3 đối sánh qua thời gian.
- Mô hình PhoBERT/adapters, tầng LLM + RAG và API FastAPI/Docker là phạm vi các giai đoạn tiếp theo.

Đọc `docs/data_quality.md` trước khi lấy số lượng mẫu làm kết luận, vì các tập được sinh lại từ nguồn trung gian có thể thay đổi theo phiên bản dữ liệu.

## 10. Checklist xử lý một yêu cầu mới

1. Xác định yêu cầu đụng đến nguồn, dữ liệu trung gian, generator, hay tài liệu.
2. Đọc schema CSV và các nơi đang sử dụng file trước khi sửa.
3. Không suy diễn quan hệ hành chính khi thiếu bằng chứng từ bảng đối chiếu.
4. Thực hiện thay đổi nhỏ nhất đáp ứng yêu cầu.
5. Chạy kiểm thử phù hợp và kiểm tra đầu ra.
6. Cập nhật tài liệu khi thay đổi hợp đồng dữ liệu, cấu trúc hoặc trạng thái dự án.
