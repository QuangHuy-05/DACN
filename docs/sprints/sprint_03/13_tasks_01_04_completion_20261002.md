# Nghiệm thu nhiệm vụ 1–4 — 02/10/2026

## 1. Kết quả hiện hành

Đã phát hành **`data/processed/annotation/sprint03/corpus_train_dev_v2/`** từ 68 pilot và 232 batch được chủ dự án rà soát. Gói có **240 train / 60 dev**, **1.057 / 284 span**, giữ nguyên assignment, ID/text và annotation đã Submit. Trạng thái manifest là **`TRAIN_DEV_APPROVED_TEST_PENDING`**; chất lượng ghi **`APPROVED_WITH_DECLARED_EXCEPTIONS`** vì chủ dự án giữ nguyên task 543 dù có mâu thuẫn hệ. 100 test còn chờ partner.

| Nhiệm vụ | Đầu ra thực đạt | Nghiệm thu |
| --- | --- | --- |
| 1. QA export mới | 68/68 pilot, 232/232 batch; 0 lỗi cấu trúc, thiếu ID, text drift hoặc overlap | COMPLETE |
| 2. Phán quyết và biên bản | 300 quyết định: 299 `keep`, 1 `keep_as_exception`; xác nhận đã xem đủ 300, quyết định trực tiếp giữ 537/543 có trích dẫn và hash | COMPLETE_WITH_DECLARED_EXCEPTION |
| 3. Train/dev | 240 train / 60 dev; 0 quarantine; manifest, coverage và audit 138 cặp PASS; phát hành processed bằng script 25 | COMPLETE_WITH_DECLARED_EXCEPTION |
| 4. Runner/scorer dev | CLI 23 chỉ nhận ID/text, CLI 24 chấm riêng sau inference; scorer `s3-span-score-v3`, đọc mask T1 từ manifest | COMPLETE về hạ tầng; thực nghiệm baseline là nhiệm vụ tiếp theo |

Người duyệt: **`quanghuy050816@gmail.com`**, `completed_by=1`. Bằng chứng là xác nhận trực tiếp trong cuộc hội thoại rằng đã xem đủ 300 và đã sửa/export lại. Agent ghi lại xác nhận và kết quả kiểm tra, không tạo chữ ký thay người duyệt. Agreement độc lập **`NOT_MEASURED`** vì lượt 68/232 có prediction hỗ trợ.

## 2. Export được dùng và kiểm tra sửa đổi

Tên file batch round3 được cập nhật trong cùng đường dẫn. Snapshot theo hash là đầu vào nghiệm thu; báo cáo hash cũ được giữ làm lịch sử.

| Tệp | SHA-256 |
| --- | --- |
| Pilot `exports/reannotation_v2/pilot_assisted_round1.json` | `2fd36521009b0fe8e902a73c71d99c9fbb6c6d05ca19ec1371a1144c237615e1` |
| Batch `exports/reannotation_v2/batch_assisted_round3.json` | `e4d4f60b6c3586652bcbd22d20e38792f0f80ee02befa81b830a23f8406780d8` |
| Assignment 240/60 đã khóa | `a4052315b55ea16bc060b92fd0baf3afb63b0e17165aa6a8aa1fcbe8e7fba8d1` |
| 138 quyết định gần trùng | `118afc7cd5d1bdb166482a8c0d77a2c26d8db0b8ae1ba20e9f0b5bcbcd892165` |
| Guideline `s3-span-v1.1` | `88dc2155d032f8052317e42c6f02f36c6cc9aee03579e9f3af76ebc12784673a` |
| XML Label Studio | `5b765ef778afdc8abac288d8bae3a51e9b1f491e944d0b09814e888842d57562` |

Snapshot bằng chứng: [`review_latest_20261002_e4d4f60b/`](../../../data/interim/annotation/sprint03/review_latest_20261002_e4d4f60b/). So với snapshot `ffb10418`, 6 task thay đổi annotation: 422, 427, 433, 495, 534, 537. Task 543 giữ nguyên theo quyết định người duyệt.

| Task project 6 | Kết quả đối chiếu export cuối |
| --- | --- |
| 381 | Tên đường `Hoàng Quốc Việt` và `Ngách 238/29` đã tách đúng từ vòng trước |
| 422 | `Grand World Phú Quốc` → `Khac/khong_xac_dinh`; `Thành phố Phú Quốc` → `QuanHuyen/cu` |
| 427 | `trung tâm hành chính` → `ToaNha/CanHo/khong_xac_dinh`; huyện giữ `QuanHuyen/cu` |
| 433 | `Phường Hòa Hưng/moi` và T1 toàn câu `moi` đã thống nhất |
| 495 | Số nhà/hẻm/thôn/xã/huyện/tỉnh đã tách; `thôn Dương Đình` → `Khac/khong_xac_dinh` |
| 534 | `Phường 2` → hệ `khong_xac_dinh`, T1 bỏ trống; giữ cờ thời kỳ |
| 537 | Người duyệt giữ `Đống Đa = PhuongXa/moi`, T1 `moi`; ghi quyết định riêng, không suy đáp án từ GT nguồn |
| 543 | Người duyệt giữ `Đống Đa = PhuongXa/cu`, T1 `moi`; ghi ngoại lệ và mask T1 như mục 3 |

Raw JSON, canonical span và T1 trong gói được đối chiếu lại với annotation được chọn. Các cờ/note được giữ để truy vết; guideline/XML vẫn phiên bản đã khóa. Agent không vá annotation.

## 3. Ngoại lệ task 543 và cách sử dụng

Chủ dự án trực tiếp xác nhận: “537 và 543 đã đúng theo ý tôi rồi k cần sửa thêm nữa bạn hãy hoàn thiện nốt các bước cuối cùng đu”. Sổ phán quyết ghi rõ đây là quyết định giữ annotation, không xem đó là bằng chứng độc lập xác minh cấp/thời kỳ hành chính.

**Task 543 (`s3_60931c369cbd85ef`, thuộc dev)** vẫn có hệ span `cu` và T1 toàn câu `moi`. Nhãn T0 `PhuongXa` giữ theo quyết định người duyệt. Cách xử lý đã hiện thực:

1. Giữ nguyên giá trị span và T1 trong raw export lẫn `dev.jsonl`.
2. Lưu finding gốc, lý do giữ và trích dẫn quyết định vào `adjudicated_content_exceptions.json`; dòng decision log là `keep_as_exception`.
3. Manifest khai báo `evaluation_exclusions.t1 = ["s3_60931c369cbd85ef"]`.
4. CLI scorer 24 tự loại riêng ca đó khỏi T1 và các mẫu số chẩn đoán theo hệ. **T0 vẫn chấm đủ 60 mẫu**.
5. Khi hiện thực huấn luyện sau này, mask ID này khỏi loss T1 và ràng buộc hệ; giữ T0 theo phạm vi duyệt. Không dùng cột T1 đơn độc mà bỏ qua manifest.

Task 537 giữ quyết định người duyệt, không có mâu thuẫn hệ nội bộ trong export cuối. Có thể rà lại các cách diễn giải trong phiên bản dữ liệu sau nếu có bằng chứng mới; gói đã phát hành giữ nguyên để tái lập.

Biên bản có trạng thái **`HUMAN_REVIEW_ATTESTED_WITH_EXCEPTIONS`**. `content_review_items.json` rỗng nghĩa là không còn finding **chưa được xử lý**; ngoại lệ task 543 vẫn được công bố trong tệp riêng.

## 4. Gói đầu ra và độ phủ

Thư mục chính thức: [`corpus_train_dev_v2/`](../../../data/processed/annotation/sprint03/corpus_train_dev_v2/).

| Tệp | Mục đích |
| --- | --- |
| `train.jsonl` | 240 mẫu phát triển/huấn luyện, có span và T1 gốc |
| `dev.jsonl` | 60 mẫu chọn cấu hình/phân tích lỗi; đọc mask T1 cùng manifest |
| `dev_input.jsonl` | Input inference duy nhất: `sample_id`, `text`; không có nhãn/metadata nguồn |
| `manifest.json` | Version, hash input/output/code, schema, test pending và chính sách ngoại lệ |
| `decision_log_v2.csv` | Quyết định, lý do, người/ngày duyệt, annotation ID, flag/note và hash đủ 300 mẫu |
| `approval_record.json` | Xác nhận phạm vi rà 300 và hai quyết định trực tiếp 537/543 |
| `adjudicated_content_exceptions.json` | Ngoại lệ 543 và yêu cầu loại khỏi T1 |
| `coverage.json` | Support 11 nhãn, nguồn, hệ span, T1 gốc và số mẫu T1 được sử dụng |
| `split_audit.json` | ID/group/text và 138 quyết định; test chỉ dùng identity/text frozen |
| `quarantine.jsonl`, `content_review_items.json`, `label_studio_correction_queue.csv` | Không còn mẫu/finding chờ sửa; CSV giữ header |

| Thống kê | Train | Dev |
| --- | ---: | ---: |
| Mẫu | 240 | 60 |
| Span | 1.057 | 284 |
| Nguồn observed | 71 | 16 |
| Nguồn derived | 69 | 12 |
| Nguồn synthetic | 100 | 32 |
| T1 gốc cu/moi/Lai/null | 119 / 71 / 16 / 34 | 31 / 15 / 8 / 6 |
| T1 được dùng sau mask/null | 206 | 53 |

| Nhãn | Span train | Span dev |
| --- | ---: | ---: |
| SoNha | 215 | 56 |
| TenDuong | 221 | 60 |
| Ngo/Hem | 24 | 13 |
| ToaNha/CanHo | 5 | 0 |
| PhuongXa | 227 | 61 |
| QuanHuyen | 136 | 37 |
| TinhThanh | 210 | 54 |
| MocDinhVi | 6 | 0 |
| HuongDi | 5 | 1 |
| GhiChu | 5 | 1 |
| Khac | 3 | 1 |

Mốc/hướng thật vẫn `DEFERRED_BY_USER`. Dev không có gold `MocDinhVi` hoặc `ToaNha/CanHo`, chỉ có 1 span `HuongDi`; chưa đủ cơ sở đánh giá các nhãn này trên dữ liệu thật. Nguồn synthetic có provenance riêng và không được tính là observed. Queue chưa ghi subtype nhiễu nên `noise_type=not_recorded`; vẫn có tầng `synthetic_noise`, không suy subtype để điền báo cáo.

Audit: không giao ID/group giữa split, không trùng exact/normalized text trái split, không có benchmark leakage group. 138 cặp được người duyệt chốt `distinct` có lý do, hash và người duyệt. Báo cáo có `test:100` là **100 identity/text đã khóa để kiểm rò rỉ**, không phải đã có 100 gold test.

| Tệp | SHA-256 |
| --- | --- |
| `train.jsonl` | `283b494713bc68fa55961c809631df3db28fef39564187845215e507a201802c` |
| `dev.jsonl` | `c16e1f6ec81df2203cb9236a558785277beb424aba8f94f6aa00e0d9426eee5b` |
| `dev_input.jsonl` | `218b5246d3b59ae2aa18afd583b908759dc8a5ee590ca4418b5c0b5cbfb6e2e2` |
| `manifest.json` | `9c91b77fa220e41b1b1067e5e99b216b7b4b2176181674b340f16dec134947bf` |

## 5. Hiện thực và kiểm thử

- Script 22 kiểm QA/source snapshot, canonical ↔ raw, split/group/138 quyết định và biên bản người duyệt; hỗ trợ `--adjudications` gắn hash. Quyết định chỉ áp cho finding chỉ rõ; lỗi cấu trúc không được bỏ qua. Ngoại lệ mâu thuẫn thời kỳ bắt buộc mask T1.
- Script 25 chỉ phát hành vào version mới dưới processed khi đủ 240/60, không còn quarantine, input/output/code hash khớp và biên bản/audit đầy đủ. Sao chép nguyên byte artifact; từ chối ghi đè.
- Script 23 nhận corpus đã duyệt, kiểm hash input, adapter chỉ nhận chuỗi nguyên bản. Prediction có một hàng mỗi ID, kể cả lỗi runtime/abstain; giữ trace/latency.
- Script 24 chấm sau inference đã freeze, kiểm prediction/corpus/scorer hash và T1 mask. Scorer `s3-span-score-v3` báo exact T0 micro/per-label/macro, T1 coverage/null/ngoại lệ/abstain, mẫu số lỗi Quận và recall Quận trên cũ/lai.
- **87/87 test toàn repo** PASS, Python WSL 3.14.4 có dependency dự án; **18/18 test span/runner/scorer/CLI** PASS, Python 3.11.16. Test bổ sung kiểm phát hành, hash drift, raw không đổi, quyền phán quyết và mask T1 giữ nguyên T0.
- `release_verification.json`: mọi hash input/output/code khớp, annotation giống raw được chọn, 240/60/60 input text-only, đủ 300 quyết định. Không có file gold test hoặc corpus ba split.

Bằng chứng trong snapshot review: `full_repo_tests_final.log`, `python311_span_tests_final.log`, `round3_content_comparison.json`, `release_verification.json`. Không cài dependency/tải checkpoint mới trong lượt này. Không chạy baseline dev thật, huấn luyện hoặc chấm 100 test; CLI được kiểm bằng fixture cục bộ.

## 6. Lệnh bàn giao cho agent tiếp theo

Gói processed đã có sẵn; đọc manifest/coverage rồi bắt đầu **nhiệm vụ 5: HEUR-JW trên dev** theo [kế hoạch](10_work_plan_while_waiting_test100.md). Giữ nguyên version đã nghiệm thu và 300 ID; không chạy lại generator/import để thay dữ liệu.

Khi thật sự cần tái tạo candidate từ snapshot, dùng **tên output mới**:

```bash
cd /mnt/d/DACN
source ~/.venv_labelstudio311/bin/activate

python -m scripts.22_review_and_package_train_dev \
  --review-dir data/interim/annotation/sprint03/review_latest_20261002_e4d4f60b \
  --attestation data/interim/annotation/sprint03/review_latest_20261002_e4d4f60b/human_review_attestation.json \
  --manual-review data/interim/annotation/sprint03/review_latest_20261002_e4d4f60b/manual_content_review.json \
  --adjudications data/interim/annotation/sprint03/review_latest_20261002_e4d4f60b/human_adjudications.json \
  --output-dir data/interim/annotation/sprint03/corpus_train_dev_v2_candidate/rebuild_new_version

python -m scripts.25_publish_train_dev \
  --candidate-dir data/interim/annotation/sprint03/corpus_train_dev_v2_candidate/rebuild_new_version \
  --output-dir data/processed/annotation/sprint03/corpus_train_dev_v2_rebuild
```

Hash export, guideline, cấu hình và biên bản cần tiếp tục khớp; thay đổi nhãn cần snapshot/phán quyết/version mới. Không dùng biên bản cũ để duyệt JSON đã đổi.

Sau khi hiện thực/khóa config HEUR-JW dùng gazetteer `s3_v2`, chạy theo mẫu; placeholder là tệp/config/thư mục run mới do nhiệm vụ 5 tạo:

```bash
python -m scripts.23_run_span_dev \
  --input data/processed/annotation/sprint03/corpus_train_dev_v2/dev_input.jsonl \
  --corpus-manifest data/processed/annotation/sprint03/corpus_train_dev_v2/manifest.json \
  --model-config <MODEL_CONFIG_JSON> \
  --output-dir <NEW_DEV_RUN_DIR>

python -m scripts.24_score_span_dev \
  --predictions <NEW_DEV_RUN_DIR>/predictions.jsonl \
  --gold data/processed/annotation/sprint03/corpus_train_dev_v2/dev.jsonl \
  --corpus-manifest data/processed/annotation/sprint03/corpus_train_dev_v2/manifest.json \
  --run-dir <NEW_DEV_RUN_DIR>
```

Hiện CLI chưa kèm model config HEUR-JW được chọn trên dev. Adapter hiện hữu cần rà temporal lookup/version/ties trước bước 5; không xem test fixture là kết quả thực nghiệm. Adapter chỉ nhận text/tài nguyên công bố; gold chỉ được nạp ở scorer.

## 7. Phần cần chủ dự án và partner làm

**Chủ dự án:** nhiệm vụ 1–4 không còn thao tác Label Studio cần làm tại thời điểm phát hành này. Có thể giao agent nhiệm vụ 5 trước khi partner xong test. Quyết định giữ 537/543 đã được ghi; khi dùng T1 phải tuân thủ mask trên manifest.

**Partner:** tiếp tục gán mù đủ 100 ID trong [gói test](annotation_handoff/test100_v1/README.md), dùng guideline/XML đã khóa, Submit và export raw JSON cùng thông tin người gán/xác nhận đã rà từng mẫu. Không nạp prediction/đổi ID test. Khi bàn giao, chạy converter 17 theo role test, duyệt ca khó và audit đủ ba split trước khi phát hành corpus chứa test hoặc chấm test.

Sprint 3 còn thực nghiệm baseline, mô hình đề xuất/giải mã động và nghiệm thu test. Fine-tune giữ cho giai đoạn cuối theo ưu tiên chủ dự án; VQA `HOLD`, Data 05 thật `DEFERRED_BY_USER`, mã hành chính cũ gazetteer còn candidate. Báo cáo này nghiệm thu riêng nhiệm vụ 1–4.
