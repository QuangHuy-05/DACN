# Kết quả bốn nhiệm vụ thực nghiệm đầu — 02/10/2026

Phạm vi: kiểm kê môi trường, HEUR-JW, Deepparse zero-shot FastText và CRF độc lập. Corpus dùng đúng `corpus_train_dev_v2`, 240 train / 60 dev, schema `s3-span-v1.1`. **100 test vẫn `TEST_PENDING`**. Thu mốc/hướng thật vẫn hoãn, VQA vẫn `HOLD`.

## Trạng thái nghiệm thu

| Nhiệm vụ | Trạng thái | Bằng chứng |
| --- | --- | --- |
| 1. Môi trường | Hoàn thành inventory và runtime CRF | [Inventory trước cài và kết quả](14_experiment_01_04_environment.md); chỉ cài python-crfsuite 0.9.12 trong env cô lập |
| 2. HEUR-JW | Đã hiện thực, quét ngưỡng và chạy hai track | `heur_jw_dev_20261002_v2`, `heur_jw_5field_20261002_v1` |
| 3. DP-ZS-FT | Adapter/mapping/alignment đã viết; **thực nghiệm thật bị chặn** | WSL 3.64 GiB RAM + 1 GiB swap thấp hơn full FastText 8–10 GB; model card chưa khai báo license riêng |
| 4. CRF-INDEP | Đã train, chọn cấu hình và chạy hai track | `crf_indep_dev_20261002_v1`, `crf_indep_5field_20261002_v1` |

**Chưa hoàn thành toàn bộ bốn nhiệm vụ ở mức thực nghiệm:** DP-ZS-FT chưa có prediction/metric pretrained thật. Test fixture của adapter không được tính thành kết quả mô hình. Chưa hoàn thành toàn bộ Sprint 3.

## Hợp đồng dữ liệu và chống rò rỉ

- T0 inference dùng duy nhất `dev_input.jsonl` (60 `sample_id/text`). Adapter chỉ nhận text; runner gắn ID sau inference. Gold được đọc ở scorer sau khi prediction đã lưu và hash khóa.
- CRF chỉ train 240 mẫu; 60 dev dùng chọn hyperparameter. Không gộp hoặc chia lại split.
- Task 543 `s3_60931c369cbd85ef` giữ mọi span T0; scorer đọc `evaluation_exclusions.t1`, loại đúng một ID khỏi T1 và chẩn đoán cấu trúc theo hệ. T1 dev có 53 mẫu đủ điều kiện sau 6 null + 1 ngoại lệ.
- Track 5 trường nhận `ChuoiDiaChi` ở mode **TEXT_ONLY**. Không có oracle run. Benchmark 01/02/03/04/06 ban đầu có 4.900 hàng; loại 100 hàng đã reserve cho test, còn **4.800** hàng. Manifest định danh test chỉ có ID/hash/nguồn, không có gold; dùng duy nhất để loại hàng, không đưa vào adapter.
- `source_row` trong manifest là dòng CSV vật lý (header=1, bản ghi đầu=2); runner chuyển thành chỉ số bản ghi bằng **source_row - 2**, kiểm text hash của hàng bị loại. Đã có regression test cho quy tắc này.
- Chấm Data 02 bằng `GT_*` sạch sau inference; Data 04 chấm 5 trường còn trên bề mặt, không chấm khả năng khôi phục trường đã lược như thể đó là extraction. Data 07 là T2, không nằm trong lượt này.
- Phép chiếu sang 5 trường thống nhất: lấy nguyên văn span, nối các lần nhắc cùng trường bằng `, `. Không sửa tên OCR thành tên chuẩn hoặc bổ sung đơn vị vắng trong chuỗi. Vì vậy T0 đúng trên văn bản nhiễu vẫn có thể sai strict field so với GT sạch Data 02.
- Baseline v2/v3, benchmark, corpus, assignment, guideline và raw export không bị sửa. Audit cuối đối chiếu hash ledger và các artifact corpus. [Audit máy đọc được](../../../data/processed/evaluation/sprint03/experiment_01_04_review_20261002_v1/completion_audit.json).

## HEUR-JW

Adapter nạp rõ **gazetteer s3_v2**, kiểm hash entities/alias/edges/5 chuyển đổi phi nguyên tử; alias chỉ từ lớp audit. Gazetteer vẫn `PARTIAL_OLD_CODES_UNVERIFIED`, không trả mã candidate cũ như mã chính thức.

Chính sách thời gian `dual_snapshot`: so ứng viên cũ tại 30/06/2025 và mới tại 01/07/2025, dùng giống nhau cho mọi input. Không lấy ngày/hệ gold từng hàng. Ngày bắt đầu hiệu lực cũ còn unknown được giữ như giới hạn nguồn. API cũng hỗ trợ `fixed_as_of` khi ngày được khai báo toàn cục.

Candidate giữ cấp, loại đơn vị, ancestor context, hiệu lực, nguồn và trạng thái code. Chuẩn hóa chỉ dùng để so tên; offset luôn lấy từ text gốc. Blocking cố định: cùng ký tự đầu Unicode, tỷ lệ độ dài core >=0.60 và JW>=0.80; có thể bỏ sót OCR thay đổi ký tự đầu/bỏ dấu. Prefix loại đơn vị không được xóa rồi ghép nhầm `Phường` với `Xã` để quyết định hệ/ID.

Nếu nhiều cấp còn cạnh tranh, từ chối span. Nếu cấp đã xác định nhưng nhiều ID/thời kỳ còn phù hợp, giữ span T0, ghi `entity_id=null`, `identity_abstain=true`; hệ span là `khong_xac_dinh` khi cả cũ/mới còn khả dĩ. Không chọn bản ghi đầu tiên. Trace ghi cả số ứng viên và tối đa 10 ứng viên đứng đầu; quyết định được tính trên toàn bộ contenders.

Đã quét 0.82/0.86/0.90/0.94/0.98/1.00. Chọn **0.86** theo exact-span micro F1 toàn schema; nếu hòa chọn ngưỡng cao hơn. Margin cố định 0.02. [Bảng precision–coverage đầy đủ](../../../data/processed/evaluation/sprint03/heur_jw_dev_20261002_v2/precision_coverage.csv).

| Threshold | Precision | Recall | F1 |
| ---: | ---: | ---: | ---: |
| 0.82 | 92.80% | 81.69% | 86.89% |
| **0.86** | **94.00%** | **82.75%** | **88.01%** |
| 0.90 | 93.98% | 82.39% | 87.80% |
| 0.94 | 93.98% | 82.39% | 87.80% |
| 0.98 | 93.95% | 82.04% | 87.59% |
| 1.00 | 93.95% | 82.04% | 87.59% |

Ở ngưỡng chọn: 59/60 câu có >=1 span; 68.98% các đoạn tra hành chính được xác định cấp, **35.83%** được xác định ID nội bộ duy nhất; 58 đoạn bị reject. Coverage có span không có nghĩa mọi trường hoặc ID đều đúng. Candidate trace nằm trong `predictions.jsonl`, ở `trace.admin_matches` và `raw_output.candidate_trace`.

HEUR chỉ hỗ trợ **6 nhãn**: SoNha, TenDuong, Ngo/Hem, PhuongXa, QuanHuyen, TinhThanh. Nhãn hỗ trợ phủ 281/284 gold span =98.94%, nhưng metric toàn schema vẫn tính 3 span nhãn ngoài phạm vi thành FN. Không gọi đây là recognizer đủ 11 nhãn. Run dev v1 được giữ làm lịch sử; v2 là bản dùng cuối sau kiểm loại đơn vị.

## CRF-INDEP

- python-crfsuite 0.9.12, `crf1d`, L-BFGS, CPU; không có PhoBERT/Deepparse/embedding.
- Tokenizer `word_punct_raw_v1`: word/number/compound `-` hoặc `/`, punctuation tách riêng; không chuẩn hóa text trước offset. Toàn bộ 240 train + 60 dev span khớp ranh giới token. Train có **3.636 token**; BIO23 có đủ 23 trạng thái quan sát trong train.
- Feature `surface_context_v1`: lowercase NFC dùng trong feature, shape/chữ/số/dấu, prefix/suffix, tiền tố đường/hẻm/hành chính, vị trí và context ±1/±2. Không dùng hệ gold hoặc từ điển học từ benchmark/test. Không dùng gazetteer trong cấu hình CRF này.
- BIO gold round-trip phải khớp nguyên span. Token cắt ngang span gây lỗi chặn, không tự sửa label/boundary. Không truncation hoặc bỏ mẫu.
- Decoder đổi I không có B/I cùng nhãn trước đó thành B, ghi từng repair; cấu hình chọn có **0 repair trên dev**.
- Grid khai báo trước: context 1/2 × (c1,c2)=(0.05,0.1),(0.1,0.1),(0.1,1),(0.5,1). 100 iteration tối đa, epsilon1e-5; seed42, L-BFGS deterministic. Chọn max dev micro F1; hòa ưu tiên context nhỏ, c2 lớn, c1 lớn.
- Chọn **context2, c1=0.05, c2=0.1**. Lượt train này mất khoảng 1.86s; xem từng training log/metadata cho hội tụ và tham số. **T1 `NOT_IMPLEMENTED`**; không huấn luyện head hệ ẩn. Các giá trị T1=0 trong JSON là toàn bộ abstain, không đưa vào bảng so sánh classifier T1.

[Training manifest/grid/checkpoint](../../../data/processed/evaluation/sprint03/crf_indep_dev_20261002_v1/training_manifest.json). Hash checkpoint chọn: `4f23ed9e5127b2720a70546f9672f31af45a0ad6b74708f8f6f09f81cf83e333`.

## Kết quả T0 dev — 60 mẫu, 284 span

| Model | Precision | Recall | Exact-span micro F1 | TP / FP / FN | Macro F1 nhãn có gold support |
| --- | ---: | ---: | ---: | --- | ---: |
| HEUR-JW | 94.00% | 82.75% | **88.01%** | 235 / 15 / 49 | 57.77% |
| CRF-INDEP | 89.51% | 90.14% | **89.82%** | 256 / 30 / 28 | 70.66% |
| DP-ZS-FT | NOT_RUN | NOT_RUN | NOT_RUN | RAM/license blocker | NOT_RUN |

Macro nhãn có gold support tính 9 nhãn, kể cả HuongDi/GhiChu/Khac mỗi nhãn chỉ 1 span. Macro all11 gán zero cho nhãn support0 theo scorer lần lượt 47.27%/57.81%; đây là quy ước metric, không là bằng chứng khả năng xử lý hai nhãn chưa có mẫu.

| Nhãn | Gold support | HEUR-JW F1 | CRF-INDEP F1 |
| --- | ---: | ---: | ---: |
| SoNha | 56 | 92.73% | 95.41% |
| TenDuong | 60 | 82.88% | 88.33% |
| Ngo/Hem | 13 | 82.76% | 84.62% |
| ToaNha/CanHo | 0 | chưa đánh giá được | chưa đánh giá được |
| PhuongXa | 61 | 94.12% | 83.87% |
| QuanHuyen | 37 | 73.33% | 84.62% |
| TinhThanh | 54 | 94.12% | 99.08% |
| MocDinhVi | 0 | chưa đánh giá được | chưa đánh giá được |
| HuongDi | 1 | 0% (ngoài phạm vi) | 100% **chỉ 1 span** |
| GhiChu | 1 | 0% (ngoài phạm vi) | 0% |
| Khac | 1 | 0% (ngoài phạm vi) | 0% |

Không suy rộng từ 1 span HuongDi. Cả hai hiện có 0/14 câu gold mới xuất hiện QuanHuyen dư ở dev; recall QuanHuyen trên gold cũ là HEUR51.72%, CRF86.21%, trên Lai là 83.33%/100% (support lần lượt 29/6). Kết quả này chưa chứng minh đã loại hoàn toàn lỗi quận.

HEUR T1 phụ: 40/53 đúng=75.47% accuracy; accepted46/53, đúng40/46=86.96%; abstain7/53; macro F1 ba lớp78.68%. Task543 không tham gia mẫu số. T1 CRF/DP chưa thực hiện.

Error analysis có trong từng run: HEUR thường bỏ sót tên huyện không có prefix, chia tên đường chứa từ như `Huyện` hoặc không khôi phục được ranh giới số nhà phức tạp; CRF có nhiều nhầm cấp hành chính/tên đường khi thiếu cue, sai ranh giới cụm hẻm và số nhà. Scorer giữ nguyên các ranh giới gold đã duyệt, kể cả những cụm gộp khác cách model tách; không sửa gold để tăng điểm.

## Track 5 trường — 4.800 hàng, TEXT_ONLY

| Dataset | n được chấm | HEUR micro F1 | CRF micro F1 | HEUR exact cả bản ghi | CRF exact cả bản ghi |
| --- | ---: | ---: | ---: | ---: | ---: |
| 01 mới | 980 | 96.23% | 97.59% | 86.53% | 90.82% |
| 02 nhiễu | 980 | 56.04% | 45.86% | 3.88% | 5.61% |
| 03 cũ | 1.480 | 84.59% | 93.47% | 18.45% | 77.16% |
| 04 thiếu trường | 780 | 80.26% | 91.61% | 34.87% | 77.31% |
| 06 lai | 580 | 92.48% | 97.91% | 48.79% | 91.21% |
| **Gộp** | **4.800** | **82.04%** | **85.41%** | **35.71%** | **67.06%** |

Một mismatch đóng góp FP+FN; cả bản ghi đúng yêu cầu mọi trường khớp sau chuẩn hóa giữ dấu/loại đơn vị. Macro mean field F1 lần lượt80.75%/85.53%. Data02 cho thấy extraction nguyên văn chưa giải quyết tốt chuẩn hóa/khôi phục OCR: đây là giới hạn rõ của hai cấu hình. CRF có micro F1 tổng cao hơn nhưng thấp hơn HEUR ở Data02.

QuanHuyen dư trên gold mới không có quận: HEUR **5/1.861=0.27%**, CRF **19/1.861=1.02%**. Đây là chẩn đoán 5 trường, tách khỏi 0/14 ở T0 dev. Không đối đầu trực tiếp các số trên với v3 oracle hoặc run chứa đủ 4.900 hàng.

## Deepparse: phần hoàn thành và phần còn chờ

Code `src/evaluation/adapters/deepparse_adapter.py`; mapping [dp_native_literal_v1](../../../configs/deepparse_native_mapping_v1.json). Pretrained `model_type="fasttext"`, offline/cache khai báo, không retrain. Raw token/native tag/native field được giữ trước mapping.

StreetNumber/StreetName ánh xạ SoNha/TenDuong. Municipality/Province chỉ dùng prefix cấp rõ trong nhóm native; tên city/tp/bare names không được ép cấp. Unit/Orientation/GeneralDelivery/PostalCode/EOS không được suy thành nhãn khác. Nhóm native chứa nhiều loại đơn vị hành chính bị reject.

Alignment yêu cầu toàn bộ token output theo đúng thứ tự khớp dòng token của text gốc sau comma/lowercase; không tìm occurrence về sau khi mismatch, không gộp qua dấu phẩy, không chấp nhận lowercase thay độ dài Unicode. Các token lặp, city cấp huyện, native group quá rộng, Unicode và mismatch đã có test. **Chưa chạy pretrained thật**, nên chưa xác nhận coverage/alignment integration và không tuyên bố T0 thực tế `SUPPORTED` hay gán điểm0.

Để mở lại: cần máy/runtime có đủ RAM thực (dự phòng10–12 GiB available), xác minh license weights/embedding với nguồn chính thức, resolve toàn bộ dependency version/dung lượng vào inventory bổ sung, rồi mới cài/tải đúng danh sách. [Deepparse chính thức](https://deepparse.org/get_started/get_started.html) ghi nhu cầu RAM và hạn chế native FastText trên Python3.13+. Không đổi cấu hình toàn máy hoặc dùng FastText Light dưới cùng model ID trong lượt này. Sau khi có tài nguyên, chạy smoke test trên chuỗi tự soạn, khóa checkpoint/cache/mapping hash, dùng script23/24 cho dev và script28 cho 5 trường.

## Artifact, kiểm thử và tái lập

Artifact gốc tại `data/processed/evaluation/sprint03/`. Mỗi run có `predictions.jsonl`, `model_config.json`, `run_manifest.json`, `metrics.json`, `error_analysis.jsonl`, `scoring_manifest.json`. CRF còn có model.crfsuite, metadata/training log/grid; HEUR có sweep/precision–coverage. Mọi thư mục run từ chối ghi đè.

Latency mean/p95, milliseconds, CPU; **không gồm khởi tạo/load model**, HEUR cache có ảnh hưởng:

| Track | HEUR mean/p95 | CRF mean/p95 |
| --- | ---: | ---: |
| Dev | 2.16 / 10.88 | 0.30 / 0.51 |
| 5 trường | 0.79 / 4.39 | 0.29 / 0.46 |

Hash corpus giữ nguyên:

- train `283b494713bc68fa55961c809631df3db28fef39564187845215e507a201802c`.
- dev `c16e1f6ec81df2203cb9236a558785277beb424aba8f94f6aa00e0d9426eee5b`.
- dev input `218b5246d3b59ae2aa18afd583b908759dc8a5ee590ca4418b5c0b5cbfb6e2e2`.
- corpus manifest `9c91b77fa220e41b1b1067e5e99b216b7b4b2176181674b340f16dec134947bf`.

Kiểm thử cuối: **101 test toàn repo, 100 pass + 1 skip** (runtime chính chưa có pycrfsuite); **31/31** test span/runner/adapter trong runtime CRF, bao gồm test train CRF thực được skip ở lượt toàn repo. Log tại `data/interim/evaluation/sprint03/verification_20261002_v1/full_repo_tests.txt` và `crf_runtime_tests.txt`. Các test kiểm offset/BIO, ties/hệ trùng, parent/type/date, hash drift, mẫu hold không đến adapter và mask T1. Audit cuối kiểm hash artifact/corpus/baseline và đủ60/4.800 prediction.

Chạy lại bằng thư mục **mới**; ví dụ sau khi tạo env WSL mới từ Python3.11 đã có:

```bash
cd /mnt/d/DACN
source ~/.venv_labelstudio311/bin/activate
python -m venv data/interim/evaluation/sprint03/runtime_py311_new
data/interim/evaluation/sprint03/runtime_py311_new/bin/python -m pip install \
  --no-deps --require-hashes -r configs/requirements_sprint3_crf.txt

data/interim/evaluation/sprint03/runtime_py311/bin/python -m scripts.27_sweep_heur_jw_dev \
  --output-dir data/processed/evaluation/sprint03/heur_jw_dev_REPLAY_NEW \
  --experiment-id heur_jw_REPLAY_NEW

data/interim/evaluation/sprint03/runtime_py311/bin/python -m scripts.26_train_independent_crf \
  --output-dir data/processed/evaluation/sprint03/crf_indep_dev_REPLAY_NEW \
  --experiment-id crf_indep_REPLAY_NEW

data/interim/evaluation/sprint03/runtime_py311/bin/python -m scripts.28_run_fivefield_experiment infer \
  --config data/processed/evaluation/sprint03/crf_indep_dev_REPLAY_NEW/chosen_model_config.json \
  --output-dir data/processed/evaluation/sprint03/crf_indep_5field_REPLAY_NEW

# Scoring chạy trong env dự án hiện hữu có pandas, không nạp adapter/checkpoint:
source ~/.venv_dacn/bin/activate
python -m scripts.28_run_fivefield_experiment score \
  --run-dir data/processed/evaluation/sprint03/crf_indep_5field_REPLAY_NEW
python -m scripts.29_audit_sprint3_experiments \
  --output-dir data/processed/evaluation/sprint03/experiment_01_04_review_REPLAY_NEW \
  --runs heur_jw_dev_REPLAY_NEW/threshold_0.86 \
  crf_indep_dev_REPLAY_NEW/CONFIG_CHOSEN/dev_run \
  heur_jw_5field_REPLAY_NEW crf_indep_5field_REPLAY_NEW
```

Nếu dùng env mới, thay `runtime_py311` trong các lệnh tương ứng bằng tên mới. Chạy HEUR 5 trường tương tự CRF, dùng chosen config của HEUR; thay `CONFIG_CHOSEN` bằng thư mục thực được chọn trong training manifest và threshold bằng kết quả sweep thực. Script29 nhận `--runs` cho replay, mặc định audit bốn run gốc nêu trong báo cáo. Script23/24 vẫn dùng để infer/chấm riêng từng config dev đã chọn. File interim/runtime không đi cùng Git; partner có thể tạo runtime mới theo inventory/pin.

Việc cần chủ dự án: cung cấp runtime đủ RAM và xác minh quyền dùng pretrained nếu muốn hoàn tất DP-ZS-FT. Việc cần partner: hoàn tất gán mù100 test, bàn giao export để QA/duyệt; khi đó mới đóng gói đủ split và chấm test với cấu hình khóa. Fine-tune Deepparse/PhoBERT và Proposed-DYN vẫn là công việc Sprint3 tiếp theo.
