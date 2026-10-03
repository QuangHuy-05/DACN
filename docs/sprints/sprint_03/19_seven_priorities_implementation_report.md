# Nghiệm thu triển khai U1–U7 — 02/10/2026

## 1. Kết luận và phạm vi

Đã hiện thực mã, dữ liệu dẫn xuất, config/protocol, CLI, kiểm thử và hồ sơ nguồn cho cả U1–U7. **Chưa xác minh tích hợp neural với resource thật và chưa huấn luyện thực nghiệm neural.** Các phần thiếu Torch/Deepparse/tokenizer/segmenter giữ `INTEGRATION_PENDING_RESOURCE`; training giữ `TRAINING_DEFERRED_BY_USER`. Không có prediction/metric pretrained mới và không lấy fixture làm kết quả mô hình.

Đầu vào giữ nguyên `corpus_train_dev_v2`, 240 train / 60 dev, 1.057 / 284 span. Không đổi 537/543 hoặc nhãn đã duyệt; T1 đọc mask từ manifest. Colab, toàn bộ công việc test100, VQA/Data05, LLM/RAG/API nằm ngoài lượt này. Không cài/tải package/model, đổi nhánh, commit hoặc push GitHub.

## 2. Bảng nghiệm thu từng ưu tiên

| U | Đã hiện thực | Bằng chứng chạy thật trong lượt này | Trạng thái còn lại / đầu ra |
| --- | --- | --- | --- |
| U1 | Alignment raw-offset, BIO23 round-trip, loader gate hash, processor DP/PhoBERT, provenance sidecar, T1 mask | Raw và DP surface đều 240/240 train + 60/60 dev EXACT; 1.341 span giữ nguyên; alignment audit PASS; test Unicode/NFC/NFD, underscore, tên lặp, B liền kề, overlap/boundary/special/UNK/long-input | `IMPLEMENTED`, core `UNIT_TESTED`; PhoBERT processor thật pending, DP native pending. Gói hiện hành `prepared_v3/` |
| U2 | Native Deepparse FastText full, custom BIO23 + EOS24, train240/val60 riêng, API guard, callback project exact-span F1, transfer gate encoder/decoder, adapter raw-logits | Converter/punctuation/EOS/illegal-BIO/API-guard fixtures PASS; preflight chặn đúng tài nguyên thiếu; test package API thật SKIP | Code độc lập `IMPLEMENTED/UNIT_TESTED`; `INTEGRATION_PENDING_RESOURCE`, `TRAINING_DEFERRED_BY_USER`. Script31, DP config và inventory18; không có checkpoint thật |
| U3 | PhoBERT encoder, raw-unit pooling, emission + constrained linear-chain CRF; optimizer/scheduler/accumulation, adapter text-only | Alignment/API fixtures và protocol/artifact gates PASS; CRF tensor/bruteforce/forward-backward/save-load tests đã viết nhưng SKIP do không Torch | `IMPLEMENTED`; integration encoder/tokenizer/VnCoreNLP/CRF tensor pending. Script32, `phobert_crf_v1.json`; không có coverage processor thật hoặc metric |
| U4 | Cùng T0 CRF + head T1 ba lớp; mask null/ngoại lệ; confidence/margin, Viterbi ban quận chỉ cho moi chắc; paired decoder cùng checkpoint; dev calibration6 điểm | Pure reference Viterbi, posterior validation, các hệ cu/moi/Lai/abstain, trường hợp T1 sai gây mất recall và calibration mask fixtures PASS; tensor model/paired adapter test SKIP | Code `IMPLEMENTED/UNIT_TESTED` ở phần độc lập; chưa có kết quả calibration/ablation neural thật. Script33 và hai proposed configs |
| U5 | Protocol v1/config hash khóa, budget, seed, full-schema selection/tie, resource/truncation/loss/ablation policies | Bốn config PASS; thay processor/label/split/budget/config bị từ chối; mất protocol lock bị từ chối; selection/mask tests PASS | `IMPLEMENTED/UNIT_TESTED`; chưa chạy search hoặc stability seeds. Protocol17, `protocol_lock_v1.json`, `tuning_protocol_v1.json` |
| U6 | Factory vào runner/scorer hiện có, atomic checkpoint, best/last, resume/new-weights phân biệt, text-only freeze → score, code/resource hashes và audit | CLI/import/AST PASS; fixture orchestration dùng runner/scorer thật PASS; tampering/metadata/overwrite/mismatch tests PASS; 246 frozen file hash PASS | `IMPLEMENTED/UNIT_TESTED` phần độc lập; Torch save/load/optimizer resume và model inference integration còn SKIP. Scripts30–34, checkpoint/artifact modules |
| U7 | Audit nguồn, exact dated full-parent verifier, code string/zero đầu, half-open interval adapter, lookup ambiguity/multiple targets, coverage/gap | Audit package thật 14.149 entity, 10.597 cạnh nguyên tử, 187 alias, 5 cạnh phi nguyên tử; verifier/lookup/date/zero-leading/hash fixtures PASS | Toolkit `IMPLEMENTED/UNIT_TESTED`; **0 mã mới verified**, `BLOCKED_SOURCE`, package vẫn `PARTIAL_OLD_CODES_UNVERIFIED`; không phát hành v3. Script35, báo cáo20, `gazetteer_audit_v2/` |

`UNIT_TESTED` của U2/U3/U4/U6 chỉ áp dụng phần thực sự chạy. Không đồng nghĩa forward/backward, native parser hoặc pretrained integration đã PASS.

## 3. Artifact hiện hành và cách đọc

Thư mục gốc: `data/interim/modeling/sprint03/seven_priorities_20261002_v1/`.

| Đầu ra | Nội dung / trạng thái |
| --- | --- |
| `prepared_v3/input_manifest.json` | Pin corpus, input/output/code/label-map/processor/provenance hashes; preparation, không prediction |
| `prepared_v3/raw_train.jsonl`, `raw_dev.jsonl` | Alignment text-only + nhãn BIO gắn ở nhánh supervised;240/60 |
| `prepared_v3/deepparse_surface_train.jsonl`, `deepparse_surface_dev.jsonl` | DP surface lowercase có mapping về raw;240/60, chưa qua native library |
| `prepared_v3/alignment_report.json`, `alignment_diagnostics.jsonl` | EXACT và số gold/represented/unrepresentable từng nhãn; trạng thái processor thật |
| `prepared_v3/label_map.json`, `provenance_sidecar.jsonl` | BIO23/DP24/T1 classes; nguồn/nhóm/hash ở sidecar, không feature inference |
| `gazetteer_audit_v2/source_register.json` | Nguồn nội bộ/web, thẩm quyền, thời kỳ, quyền dùng và hash khi có file local |
| `gazetteer_audit_v2/code_verification_decisions.jsonl` |14.149 quyết định derivative, không thay entity frozen |
| `gazetteer_audit_v2/coverage_gap_report.json`, `audit_manifest.json` |0 newly verified, gaps/cấp/hệ/quan hệ và hashes |
| `verification/*_preflight/preflight.json` | Ba model đều pending; corpus hash/count PASS; không tải hoặc train |
| `verification/alignment_audit_final.json` | `ALIGNMENT_AUDIT_PASS`, không issue |
| `verification/tests_acceptance_v2.json` và hai log cùng hậu tố | Kết quả kiểm thử cuối, command/runtime/skip reasons |
| `verification/cli_import_smoke_acceptance_v2.json` | AST28file, import27module,6 help +3 preflight; preflight exit2 khi thiếu resource |
| `verification/frozen_integrity_acceptance_v2.json` |246 file đã khóa không thay đổi |
| `handoff_manifest.json` | Index cuối, SHA của mã/config/docs/derivatives/evidence; không phải run thực nghiệm |

`prepared/`, `prepared_v2/`, `gazetteer_audit/` và log round1–3 là lịch sử phát triển, đã được thay bằng các phiên bản trong bảng. Không dùng những phiên bản đó làm đầu vào hiện hành. Snapshot này là artifact cục bộ; `data/interim/` bị Git ignore.

## 4. Coverage, mask và tính bất biến

| Processor | Train EXACT | Dev EXACT | Span train/dev giữ | Unrepresentable |
| --- | ---: | ---: | --- | ---: |
| raw `word_punct_raw_v1` |240/240|60/60|1.057/284|0 trên mọi nhãn|
| DP surface `dp_surface_bio_v1` |240/240|60/60|1.057/284|0 trên mọi nhãn|
| PhoBERT `phobert_raw_unit_pool_v1` thật |PENDING|PENDING|Chưa công bố coverage tokenizer/segmenter thật|Không điền 0 giả|

Tên processor raw trong record lấy từ artifact; không ép kiến trúc/tokenizer ba mô hình giống nhau. Gold chỉ gắn sau `align_text(text)`. Span cắt ngang unit bị reject có lý do; không majority vote, nới gold, đổi text hoặc chọn lần `find` đầu. PhoBERT >256 reject, không truncate. DP native EOS/lệch count và illegal BIO có reject/repair trace đã version hóa.

T1 eligible **206 train / 53 dev**; gold null không thành lớp thứ tư. Task543 đọc từ `evaluation_exclusions.t1`, vẫn giữ đủ T0. Provenance train71 observed/69 derived/100 synthetic; dev16/12/32. Dev có0 `MocDinhVi`,0 `ToaNha/CanHo`,1 `HuongDi`,1 `GhiChu`,1 `Khac`; không kết luận năng lực ở support0/1. Noise subtype `not_recorded`, agreement độc lập `NOT_MEASURED`, VQA `HOLD`, Data05 `DEFERRED_BY_USER`.

Corpus manifest giữ `9c91b77fa220e41b1b1067e5e99b216b7b4b2176181674b340f16dec134947bf`. Audit so snapshot trước lượt triển khai với sau kiểm thử: **246 file**,0 thay đổi, gồm corpus train/dev, s3_v1/s3_v2, baseline v2/v3 và6 thư mục kết quả Sprint3 hiện có. Không chạy lại/rescore HEUR-JW/CRF hoặc đổi giá trị88,01%/89,82% đã khóa.

## 5. Protocol và neural verification

[Protocol17](17_training_protocol_v1.md) và `configs/modeling/sprint03/protocol_lock_v1.json` khóa trước thực nghiệm; loader từ chối lock mất/version sai hoặc config thay canonical hash. Tối đa2 candidates/mô hình,20epoch,patience5,effectivebatch16,seed phát triển42. `[42,1337,2025]` là stability plan chưa chạy. Proposed và PhoBERT chung encoder/processor; ablation sử dụng **cùng checkpoint** và chỉ bỏ constraint.

Chọn best: dev exact-span micro F1 toàn11nhãn từ TP/FP/FN, rồi macro trên gold-supported labels, epoch sớm, candidate sớm. Unsupported gold vẫn FN. Proposed chọn checkpoint bằng decoder không constraint, rồi calibration6 điểm chỉ trên eligible dev posterior đã frozen. `moi` đủ threshold/margin mới ban B/I-QuanHuyen; các hệ còn lại không bị ban. T1 sai có thể làm giảm recall quận; chưa có bằng chứng triệt tiêu mọi lỗi.

DP dùng native retrain train/val containers riêng; không CRF, không `seq2seq_params` train từ đầu. Callback kiểm state encoder và decoder backbone trước/sau thay head, lưu transfer report khi chạy thật. Native best-loss không được coi là best theo project F1. Native optimizer resume unsupported; weights restart có metadata vào run mới. PhoBERT resume có optimizer/scheduler/RNG và compatibility gate, nhưng test thực bằng Torch còn skip.

Mức verification thực tế: **core/contract/CLI/orchestration fixtures đã chạy**; **package/tokenizer/segmenter/encoder native neural chưa chạy**. Phiên bản package/source profile nằm ở [inventory18](18_modeling_resource_inventory.md). Không có local weights/resource lock đã CLEARED; template revision/null hoặc files rỗng bị từ chối. Help/preflight không tự tải hoặc train.

## 6. Kiểm thử và vấn đề đã sửa

| Suite | Runtime | Tổng | PASS | SKIP | FAIL |
| --- | --- | ---: | ---: | ---: | ---: |
| Toàn repo, nghiệm thu cuối | WSL main Python3.14.4 |151|143|8|0|
| Modeling/span/dev-runner/experiments | Runtime CRF Python3.11.16 |80|73|7|0|
| `tests.test_modeling_pipeline` trong hai suite trên | Cùng runtime tương ứng |49|42|7|0|

Các suite chồng lấp; không cộng151+80 để gọi231 test độc lập. Main skip6Torch +1Deepparse package +1python-crfsuite; runtime3.11 đã chạy test CRF thật nên còn7 skip neural. Torch tests đã viết cho partition/Viterbi/bruteforce/gradient, padding/BIO, tiny forward/backward, T1 all-mask, save/reload/resume và paired text-only adapter; **chưa được chạy**. Không cài dependency chỉ để xóa skip.

Lệnh đã thực thi:

```bash
cd /mnt/d/DACN
source ~/.venv_dacn/bin/activate
python -m unittest discover -s tests -v
data/interim/evaluation/sprint03/runtime_py311/bin/python -m unittest \
  tests.test_modeling_pipeline tests.test_span_evaluation \
  tests.test_span_dev_runner tests.test_sprint3_experiments -v
```

Log cuối: [main](../../../data/interim/modeling/sprint03/seven_priorities_20261002_v1/verification/full_repo_tests_acceptance_v2.log), [Python3.11](../../../data/interim/modeling/sprint03/seven_priorities_20261002_v1/verification/runtime_py311_tests_acceptance_v2.log), [summary](../../../data/interim/modeling/sprint03/seven_priorities_20261002_v1/verification/tests_acceptance_v2.json).

Trong triển khai đã sửa: API guard quá chặt với fixture retrain, gọi scorer thiếu tham số manifest, phân biệt underscore literal/inserted trong cùng segmentation word, giữ dev T0 khi T1 abstain, shape/hash gate native transfer, resume state tách epoch weights frozen, và config lock thiếu không được fallback permissive. Log vòng đầu giữ lịch sử; kết quả nghiệm thu cuối không còn failure. `git diff --check` bằng Git Windows đạt, có cảnh báo LF→CRLF. Git WSL mặc định báo CR cuối dòng là whitespace; nghiệm thu thêm `git -c core.autocrlf=true diff --check` khớp cấu hình Windows đã đọc, không đổi cấu hình toàn máy hoặc line-ending frozen data. Log WSL chưa cấu hình được giữ để truy nguyên.

## 7. Nguồn gazetteer và blocker

[Audit20](20_gazetteer_source_audit.md) ghi nguồn sơ cấp tìm được: 124/2004/QĐ-TTg,19/2025/QĐ-TTg và URL danh mục NSO. Bảng2004 không tự chứng minh snapshot30/06/2025; cần chuỗi cấp/thay mã được duyệt. PDF danh mục mới không tự chứng minh mọi cạnh sáp nhập. Nội dung chỉ truy cập web không có hash file local.

**0 mã mới được nâng trạng thái**, old ward verified0/10.035. Mã mới3.321 khớp CSV repo, thẩm quyền/giấy phép bên ngoài vẫn chưa đủ. Có34 mã tỉnh mới thiếu,5 mã huyện cũ thiếu,63 mã tỉnh cũ +691 mã huyện cũ candidate. Toolkit đối chiếu exact đầy đủ cha/cấp/hệ/ngày, giữ mã dạng string và zero đầu; không fuzzy promotion. A/B/C/M và5 cạnh phi nguyên tử giữ nguyên. Không phát hành gazetteer v3.

## 8. File thêm/sửa

- Thêm `src/modeling/`: alignment/datasets/labels/protocol/resources; CRF/PhoBERT/proposed/structural decoder; native Deepparse converter/trainer; training/checkpoints/calibration/artifacts/CLI. Tách supervised training khỏi text-only inference và gold scoring.
- Thêm3adapter tại `src/evaluation/adapters/`; mở rộng factory trong `src/evaluation/experiment_config.py`. Giữ runner/scorer, schema11, tokenizer CRF frozen và các adapter/run baseline hiện hành.
- Thêm `src/data/administrative_code_verifier.py`, scripts30–35 và9JSON trong `configs/modeling/sprint03/` (bốn model configs, tuning protocol/lock, hai pending resource templates, source register).
- Thêm `tests/test_modeling_pipeline.py`; thêm regression span liền kề cùng nhãn ở `tests/test_data_pipeline.py`.
- Thêm docs17–20; cập nhật README, Sprint3README, AGENTS và data_quality với trạng thái/giới hạn thực. Workspace đã dirty từ lượt trước; không commit/push hoặc gom các thay đổi cũ vào một commit.

## 9. Lệnh kiểm tra an toàn và thao tác còn cần chủ dự án

Không cần gán lại68/232, sửa raw/canonical hoặc chờ test100 để dùng core/protocol. Có thể tái tạo preparation vào **thư mục mới** và audit đọc-only:

```bash
python -m scripts.30_prepare_model_training_data prepare \
  --output-dir data/interim/modeling/sprint03/prepare_next_version
python -m scripts.34_audit_modeling_artifacts prepared \
  --run-dir data/interim/modeling/sprint03/seven_priorities_20261002_v1/prepared_v3 \
  --output data/interim/modeling/sprint03/alignment_readonly_audit_new.json
python -m scripts.31_train_deepparse_finetuned preflight
python -m scripts.32_train_phobert_crf preflight
python -m scripts.33_train_proposed_dynamic preflight
```

Preflight thiếu resource exit2 là dự kiến; không phải đã train. Lệnh train/resume/infer/calibrate/score đúng CLI đã ghi đầy đủ tại [protocol17, mục7](17_training_protocol_v1.md). **Chỉ dùng ở giai đoạn được mở lại sau integration**, không chạy huấn luyện nặng ngay.

Ba điều kiện còn cần quyết định/cung cấp từ chủ dự án:

1. **Khi muốn mở neural integration:** cấp quyền riêng cho package/model/segmenter/Java được liệt kê ở inventory18. Resolve transitive inventory trước cài; pin actual revisions/files/license trước nạp. Hiện không Torch/Transformers/Deepparse/Poutyne/py-vncorenlp/Java, nên chưa thể xác minh actual API hoặc forward/backward/resume.
2. **Khi mở training:** cung cấp runtime đủ RAM cho FastText full (gate10GiB available), đủ đĩa cho PhoBERT checkpoint retention (dự phòng20GiB/run), và mở lại giai đoạn GPU/training. Hiện WSL RAM3,64GiB+swap1GiB, đĩa trống khoảng12,7GiB; không thay toàn máy hoặc chuyển sang Colab trong lượt này.
3. **Khi nâng gazetteer:** cung cấp hoặc cho phép tải bảng reference chính thức đúng ngày kèm full-parent keys, page/row evidence, transcription review, change history khi cần và quyền sử dụng của CSV ánh xạ. Format/manifest và lệnh verifier nằm ở audit20. Chưa có nguồn đủ thì giữ partial.

Không có phần code độc lập được giao lại cho chủ dự án. Các cổng còn lại là tài nguyên/tích hợp thực và bằng chứng nguồn; hoàn thiện U1–U7 trong phạm vi này chưa đồng nghĩa toàn bộ Sprint3 hoặc test cuối đã hoàn thành.
