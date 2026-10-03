# Prompt bàn giao agent — 7 ưu tiên kỹ thuật còn lại của Sprint 3

**Ngày soạn:** 02/10/2026. **Phạm vi lần làm:** hoàn thiện mã, dữ liệu dẫn xuất phục vụ mô hình, protocol, kiểm thử và hồ sơ nguồn trong repository. Việc vận hành Colab, huấn luyện nặng và công việc với test 100 đang được chủ dự án tạm gác.

Sao chép toàn bộ nội dung từ mục **PROMPT** dưới đây để giao agent, hoặc yêu cầu agent đọc trực tiếp file này. Đây là yêu cầu triển khai; các đường dẫn đầu ra đề xuất bên dưới chưa phải artifact đã được tạo.

---

## PROMPT

Bạn là Senior AI Engineer phụ trách hoàn thiện 7 ưu tiên kỹ thuật còn lại của Sprint 3 trong repository DACN. Hãy thực hiện mã và tài liệu, kiểm tra đầu ra và báo cáo bằng chứng; không dừng ở việc viết một kế hoạch khác.

### A. Mục tiêu và phạm vi

Hoàn thiện đủ 7 hạng mục:

1. Alignment và bộ đọc/chuyển dữ liệu cho các mô hình.
2. Pipeline Deepparse fine-tuned FastText (`DP-FT-FT`).
3. Pipeline PhoBERT-CRF (`PHOBERT-CRF`).
4. Pipeline mô hình đề xuất và giải mã cấu trúc động (`PROPOSED-DYN`).
5. Protocol huấn luyện, chọn cấu hình và ablation.
6. Quản lý checkpoint, prediction và artifact cho các mô hình mới.
7. Kiểm toán nguồn, mã hành chính và coverage gazetteer đa phiên bản.

**Giới hạn lần làm này:**

- Chủ dự án đang tạm gác việc chạy mô hình trên Google Colab. Không tạo notebook Colab, mount Drive, đăng nhập dịch vụ cloud, thuê GPU hay chạy huấn luyện nặng trong lượt này.
- Hoàn thiện training code và kiểm thử bằng tài nguyên hiện có. Kiểm thử mô hình nhỏ, khởi tạo ngẫu nhiên được phép khi dependency tương ứng đã có và không đòi tải model. Phải ghi rõ đó là fixture kiểm thử, không phải checkpoint thực nghiệm.
- Không import, đọc nội dung/nhãn, gán nhãn, QA, đóng gói, inference, chấm điểm hay tune trên test 100. Không xem file test-only để tìm ví dụ debug. Chính sách loại trừ hold đã tồn tại được giữ nguyên.
- Không tự cài dependency, tải pretrained checkpoint, embedding hoặc segmenter mới nếu chưa có quyền tương ứng. Việc kiểm kê không tự tạo ra quyền cài/tải. Không mở rộng quyền cài python-crfsuite của lượt trước thành quyền cài Torch/Transformers/Deepparse.
- Được tra cứu tài liệu kỹ thuật và nguồn hành chính công khai để lập hồ sơ bằng chứng; chỉ dựa vào nguồn chính thức cho kết luận thẩm quyền, mã và hiệu lực. Không crawl địa chỉ mới hoặc tự mở lại việc thu Data 05/VQA đang hoãn.
- Không tạo tầng LLM/RAG, API, FastAPI, Docker, T2 resolver đầy đủ hoặc T3 trong yêu cầu này.

Phân biệt rõ **mã đã hiện thực**, **unit test đã chạy**, **tích hợp với tài nguyên thật đã xác minh**, và **mô hình đã huấn luyện/đánh giá**. Hoàn thiện mã không cho phép báo đã có kết quả neural thật.

### B. Trạng thái đầu vào phải kế thừa

Corpus được phép dùng:

```text
data/processed/annotation/sprint03/corpus_train_dev_v2/
  train.jsonl          240 mẫu, 1.057 span
  dev.jsonl             60 mẫu,   284 span
  dev_input.jsonl       chỉ sample_id/text
  manifest.json
  coverage.json
```

- Schema `s3-span-v1.1`.
- Trạng thái `TRAIN_DEV_APPROVED_TEST_PENDING`.
- Chất lượng `APPROVED_WITH_DECLARED_EXCEPTIONS`.
- Không đổi split, ID, text, nguồn, annotation hoặc assignment.
- Người gán đã xác nhận rà toàn bộ 300 mẫu; không tự yêu cầu gán lại 68/232 hoặc mở lại quyết định đã chốt của task 537/543.
- Ngoại lệ task 543: `s3_60931c369cbd85ef`. Giữ toàn bộ T0; mask T1 trong training, evaluation và mọi loss/chẩn đoán về nhất quán hệ. Đọc danh sách từ `evaluation_exclusions.t1` trong manifest; không hardcode chỉ một ID vào logic.
- T1 có 206 train và 53 dev đủ điều kiện hiện tại. Gold null không phải lớp thứ tư và không phải đáp án `khong_ro`.
- Dev có 0 `MocDinhVi`, 0 `ToaNha/CanHo`, 1 `HuongDi`, 1 `GhiChu`, 1 `Khac`. Không bổ sung synthetic vào split đã khóa để làm đủ support.
- Phân loại nguồn phải giữ `observed`, `derived`, `synthetic` theo metadata đã công bố. Không gọi biến thể synthetic là địa chỉ quan sát.
- Independent agreement vẫn `NOT_MEASURED`; không dùng một lượt rà có prediction để tính đồng thuận giữa hai người.

Hash tham chiếu của bản phát hành hiện hành:

| File | SHA-256 |
| --- | --- |
| `train.jsonl` | `283b494713bc68fa55961c809631df3db28fef39564187845215e507a201802c` |
| `dev.jsonl` | `c16e1f6ec81df2203cb9236a558785277beb424aba8f94f6aa00e0d9426eee5b` |
| `dev_input.jsonl` | `218b5246d3b59ae2aa18afd583b908759dc8a5ee590ca4418b5c0b5cbfb6e2e2` |
| `manifest.json` | `9c91b77fa220e41b1b1067e5e99b216b7b4b2176181674b340f16dec134947bf` |

Kiểm cả manifest và các output hash bên trong. Nếu khác, báo rõ file/hash lệch và tiếp tục các hạng mục không phụ thuộc; không tự bỏ kiểm hash hoặc phát hành lại corpus.

Phần đã có, cần tái sử dụng:

- HEUR-JW: adapter s3_v2, threshold 0.86, margin 0.02, dual_snapshot; dev F1 88,01%.
- CRF-INDEP: 240 train/60 dev, BIO23; dev F1 89,82%; T1 `NOT_IMPLEMENTED`.
- Prediction, metric, run manifest và audit của hai cấu hình đã lưu. Không chạy lại hoặc ghi đè chỉ để thay tên/thư mục.
- Deepparse zero-shot: có adapter, mapping và kiểm thử alignment; chưa chạy pretrained thật. WSL hiện ghi nhận RAM 3,64 GiB + swap 1 GiB; full FastText cần nhiều RAM hơn. License của weights/embedding còn cần xác minh.
- Gazetteer s3_v2: 14.149 entity, 10.597 cạnh xã, 187 alias audit, 5 chuyển đổi huyện→đặc khu; 10.035 mã xã cũ chưa xác minh. Trạng thái `PARTIAL_OLD_CODES_UNVERIFIED`.
- Mã mới khớp bảng ánh xạ trong repo; điều này chưa chứng minh thẩm quyền/giấy phép của nguồn bên ngoài.

### C. Tài liệu và mã phải đọc trước

Đọc các file sau, ưu tiên báo cáo hiện hành hơn đoạn lịch sử trong tài liệu:

```text
AGENTS.md
README.md
docs/data_quality.md
docs/sprints/sprint_03/model_matrix.md
docs/sprints/sprint_03/span_11_annotation_guideline.md
docs/sprints/sprint_03/13_tasks_01_04_completion_20261002.md
docs/sprints/sprint_03/14_experiment_01_04_environment.md
docs/sprints/sprint_03/15_baseline_experiments_20261002.md
docs/sprints/sprint_03/gazetteer_v2_approval.md
data/processed/annotation/sprint03/corpus_train_dev_v2/manifest.json
data/processed/annotation/sprint03/corpus_train_dev_v2/coverage.json
src/evaluation/schema.py
src/evaluation/adapters/base.py
src/evaluation/span_features.py
src/evaluation/adapters/deepparse_adapter.py
src/evaluation/adapters/crf_adapter.py
src/evaluation/experiment_config.py
src/evaluation/dev_runner.py
src/evaluation/span_scorer.py
src/evaluation/benchmark_runner.py
src/evaluation/run_artifacts.py
src/data/span_trace.py
src/data/administrative_mapping.py
src/data/administrative_alias.py
scripts/19_build_temporal_gazetteer_v2.py
scripts/23_run_span_dev.py
scripts/24_score_span_dev.py
scripts/26_train_independent_crf.py
scripts/29_audit_sprint3_experiments.py
tests/test_data_pipeline.py
tests/test_span_evaluation.py
tests/test_span_dev_runner.py
tests/test_sprint3_experiments.py
```

Kiểm `git status` và file hiện có trước khi sửa. Workspace có nhiều thay đổi chưa commit từ các lượt trước; giữ nguyên các thay đổi đó. Không reset/clean, xóa file hàng loạt, tự đổi nhánh, force push hoặc commit toàn bộ workspace. Push GitHub không thuộc lượt này.

### D. Hợp đồng chung bắt buộc

1. T0 dùng đúng 11 nhãn từ `SPAN11_LABELS`; `O` là nền, không phải span `Khac`.
2. BIO gồm 23 trạng thái: `O` và B/I cho mỗi nhãn. Dictionary phải có phiên bản và được kiểm khi nạp checkpoint.
3. Offset `[start,end)` tính theo Python Unicode string của text gốc; không dùng byte offset hoặc UTF-16 index như thể là Python index.
4. Span phẳng, không overlap, nằm trong chuỗi; `span.text == text[start:end]`.
5. Giữ nguyên text gốc. Chuẩn hóa, lowercase, bỏ dấu câu hoặc thay tone chỉ được áp dụng ở nhánh encoder/feature có bảng mapping và khả năng khôi phục rõ ràng.
6. Tokenization/alignment khi inference chỉ dựa trên text và tài nguyên khai báo. Không dùng gold boundary để tách token ở train rồi dùng tokenizer khác khi inference.
7. Adapter inference nhận text, không nhận gold, `GT_*`, `HeQuyChieu`, `KieuThieu`, `Span_He_Detail`, label candidate, source stratum hoặc hệ hành chính nguồn của từng mẫu.
8. Gold chỉ dùng ở nhánh supervised training/validation và scorer. Inference dev nhận `dev_input.jsonl`; prediction được lưu và khóa hash trước scoring.
9. Output tương thích `SpanModelOutput`/`CharacterSpan`; `parse()` chiếu span sang 5 trường bằng quy tắc chung đã có. Không điền đơn vị không xuất hiện trong text hoặc sửa OCR để tạo span giả.
10. `system` của span và `predicted_system` toàn câu là hai trường khác nhau. Không biến T1 `moi` thành nhãn hệ của mọi span. Các baseline T0-only khai báo T1 `NOT_IMPLEMENTED`; không thêm một đầu T1 ẩn.
11. Không âm thầm loại mẫu dev. ID thất bại vẫn có record/status và đi vào mẫu số metric theo scorer hiện hành. Unsupported gold giữ FN trong điểm toàn schema.
12. Không ép tokenizer hoặc kiến trúc của mọi mô hình giống nhau. Dùng chung hợp đồng raw offset, validation, BIO, manifest và phép chiếu; tokenizer/processor có version riêng theo model.

### E. Luồng triển khai và cổng kiểm tra

Thứ tự công việc:

```text
Kiểm kê + hash đầu vào
  → U1: core alignment + data loader
  → U5: khóa protocol/config trước khi chọn bằng dev
  → U2: Deepparse pipeline
  → U3: PhoBERT-CRF pipeline
  → U4: proposed + ablation
  → U6: tích hợp artifact/audit
  → nghiệm thu mã và bàn giao

U7: audit nguồn gazetteer có thể thực hiện độc lập sau kiểm kê.
```

Đây là thứ tự phụ thuộc kỹ thuật, dù bảng bàn giao vẫn ghi đủ U1–U7. Mỗi cổng có artifact và trạng thái. Khi một tài nguyên thiếu, hoàn thiện core, wrapper, config và test độc lập; ghi blocker cho integration tương ứng. Không dùng mock để khai báo integration với pretrained đã PASS.

Trong báo cáo dùng tối thiểu các mức riêng:

- `IMPLEMENTED`: mã chạy được ở phạm vi khai báo, không còn TODO ở luồng chính.
- `UNIT_TESTED`: test đã chạy, có log.
- `INTEGRATION_VERIFIED`: xác minh bằng package/tokenizer/segmenter/model thật ở phiên bản đã pin.
- `INTEGRATION_PENDING_RESOURCE`: có mã và test phần độc lập, chưa xác minh với tài nguyên thật.
- `BLOCKED_INPUT_HASH`, `BLOCKED_SOURCE` hoặc blocker cụ thể khác.
- `TRAINING_DEFERRED_BY_USER`: chưa chạy huấn luyện thực nghiệm nặng trong lượt này.

Không gọi pipeline sẵn sàng huấn luyện thật nếu phần integration bắt buộc chưa xác minh. Không gọi toàn bộ Sprint 3 hoàn thành từ việc hoàn thành 7 hạng mục mã này.

### U1 — Alignment và bộ đọc/chuyển dữ liệu

**Mục tiêu:** gold char span được chuyển sang đơn vị dự đoán rồi khôi phục đúng trên chuỗi gốc; model không học hoặc chấm nhãn bị lệch vì tiền xử lý.

#### U1.1. Core và adapter alignment

- Tái sử dụng tokenizer/BIO hiện có trong `span_features.py` nếu phù hợp; giữ version/hành vi của CRF frozen. Đặt core dùng chung trong module riêng hoặc wrapper để hạn chế thay đổi phần đã chạy.
- Thiết kế record alignment chứa ít nhất: `sample_id`, text hash, processor/version, raw token `(text,start,end)`, model token/subword ID, mapping model unit→raw interval/unit, special mask, prediction-unit mask, trạng thái và diagnostics.
- Tách rõ `align_text(text)` khỏi `encode_gold(alignment, spans)`. `align_text` chạy được mà không có gold và cho cùng token/mapping ở train/dev/inference.
- Chuyển span→BIO và BIO→span; kiểm equality tập `(start,end,label)` sau round-trip, không chỉ substring trùng.
- Tách hai span liền kề cùng nhãn bằng B mới; không gộp chỉ vì cùng loại hoặc cùng text.
- Có policy rõ khi token/model unit cắt qua ranh giới thực thể. Không lấy nhãn đa số, tự mở rộng gold, tự cắt text hoặc bỏ lỗi không ghi log.
- Khi preprocessing nhiều-một/một-nhiều, mapping phải biểu diễn được hoặc trả trạng thái không khôi phục được. Không dùng `str.find` rồi chọn lần xuất hiện đầu tiên.

#### U1.2. Dữ liệu dẫn xuất

- Đọc train/dev qua gate manifest hiện có; xác minh số lượng/hash trước chuyển đổi.
- Cache/data derivative đặt trong thư mục mới có version tại `data/interim/modeling/sprint03/`; không ghi vào corpus đã duyệt.
- Lưu ID, split, text hash, processor hash, label-map hash và provenance trong sidecar; metadata không trở thành feature inference.
- T1 mask dựa trên manifest + gold null. T0 vẫn giữ các span của mẫu có T1 mask.
- Báo 240/240 train và 60/60 dev theo từng processor: số EXACT, unrepresentable, rejected, số span giữ/không biểu diễn được theo nhãn và lý do.
- Core raw-token hiện có phải round-trip toàn bộ 300 mẫu. PhoBERT/Deepparse processor chỉ được xác nhận coverage thật khi dùng đúng tài nguyên thực; nếu thiếu resource, ghi pending cho processor đó.
- Không lặng lẽ dùng tập nhỏ hơn rồi ghi vẫn là cùng 240/60. Nếu processor không biểu diễn được toàn bộ, sửa processor bằng rule áp dụng chung không dùng gold input; phần chưa giải quyết là blocker của cấu hình đó.

#### U1.3. Ca kiểm thử tối thiểu

- Dấu tiếng Việt, NFC/NFD và ký tự có nhiều code point.
- Khoảng trắng liên tiếp, tab/newline, dấu phẩy/chấm/ngoặc; slash/hyphen trong số nhà/hẻm.
- Tên lặp lại trong câu; hai span liền kề cùng nhãn; `Khac` đối với nền `O`.
- Underscore do word segmentation và underscore vốn có trong input.
- Span chồng lấp, offset lệch, token cắt ngang span, unknown token và preprocessing không khôi phục được.
- Special token, padding, empty prediction-unit sequence và chuỗi vượt giới hạn encoder.
- Test khẳng định thay gold không làm thay kết quả `align_text`.

**Nghiệm thu:** có core, processor interface, data loader, label map, báo cáo alignment và các test trên. Không còn offset giả hoặc gold-dependent tokenization. Trạng thái tài nguyên thật của từng processor được công bố riêng.

### U2 — Pipeline Deepparse fine-tuned FastText

**Mục tiêu:** fine-tune pretrained FastText seq2seq của Deepparse bằng custom tags cho T0, giữ nguyên split. Cấu hình này không phải CRF.

#### U2.1. Kiểm kê và API

- Kiểm package/cache hiện có và nguồn chính thức. Ghi package/version, Python tương thích, API signature, checkpoint/revision/hash, embedding nguồn, RAM/VRAM/đĩa và license theo từng tài nguyên vào inventory mới.
- Kiểm API của phiên bản sẽ pin; tài liệu web có thể thuộc phiên bản khác. Không giả định tên tham số nạp checkpoint hoặc format dataset từ trí nhớ.
- Ghi rõ transfer pretrained encoder/decoder nào và prediction head nào được khởi tạo lại. Không chỉnh `seq2seq_params` khiến API train từ đầu rồi gọi đó là fine-tune pretrained.
- Giữ `DP-ZS-FT` mapping hiện hành riêng; không dùng mapping native subset của zero-shot để làm mất custom labels của `DP-FT-FT`.
- Không thay full FastText bằng BPEmb/FastText Light dưới cùng model ID để vượt blocker RAM.

#### U2.2. Converter và trainer

- Dùng preprocessing/tokenization đã kiểm, có map về raw. Kiểm riêng dấu câu hoặc ranh giới bị loại bởi preprocessor; không tạo span đi xuyên qua vùng `O` bị xóa.
- Thiết kế dictionary custom tags giữ được ranh giới 11 nhãn: ưu tiên BIO23 cộng EOS nội bộ (24 tag) nếu API phiên bản pin hỗ trợ. Nếu cần encode tên tag khác, có map hai chiều có version và test; nhãn gold/output schema giữ nguyên.
- EOS/PAD là điều khiển nội bộ, không xuất thành span; chẩn đoán EOS sớm, số tag thiếu/thừa và unknown tag.
- Cung cấp train container và validation container riêng. Dùng `val_dataset_container` nếu API pin có tham số này; không để API tự chia lại train bằng `train_ratio`.
- Lưu native/custom token-tag output trước decode. Sai alignment trả status/abstain có lý do; không tìm offset theo từng chuỗi field đã gộp.
- Có training CLI đọc config/manifest, kiểm tài nguyên và dừng sớm với blocker rõ khi dependency/resource thiếu.
- Callback/chọn checkpoint phải dựa trên exact-span F1 dev từ scorer chung sau decode. Native token accuracy hoặc validation loss có thể log thêm, không tự thay metric chính.
- Nếu API mặc định chọn best theo loss, lưu checkpoint từng epoch cần thiết và chọn best theo protocol riêng, không tuyên bố mặc định tương đương exact-span F1.
- Có checkpoint metadata, load/reload, seed, log, resume nếu API thực hỗ trợ; phần resume không hỗ trợ phải báo rõ và cho lệnh khởi động run mới, không fake resume.

#### U2.3. Adapter và kiểm thử

- Tạo adapter `DP-FT-FT` nhận raw text; trả `SpanModelOutput`, T1 `NOT_IMPLEMENTED`, phép chiếu 5 trường hiện hành.
- Test container labels/count, dictionary/EOS, train/dev không re-split, decode raw offset, native-output mismatch và checkpoint metadata mismatch.
- Có test tích hợp thư viện thật khi tài nguyên có sẵn; không tự tải full model để chạy test.

**Đầu ra:** converter, trainer, custom-tag map, adapter, config, inventory/API evidence, test/log và hướng dẫn. Nếu tài nguyên vẫn thiếu, phần code phải hoàn thiện, trạng thái pretrained integration/training vẫn pending/deferred; không tạo metric giả.

### U3 — Pipeline PhoBERT-CRF

**Mục tiêu:** encoder PhoBERT → emission → linear-chain CRF trên BIO23 → raw char spans, dùng cùng gold/split.

#### U3.1. Encoder và alignment

- Ứng viên mặc định `vinai/phobert-base`; ghi revision/tokenizer file hash và license cụ thể trước chạy thật. Không tự đổi sang PhoBERT-base-v2, PhoBERT-large, ViBERT hoặc encoder khác dưới ID này.
- Dùng word segmentation đúng yêu cầu PhoBERT, ưu tiên quy trình được VinAI khuyến nghị. Ghi segmenter/version/model và tiền xử lý tone nếu có; không giả định segmenter giữ text byte-for-byte.
- Không giả định tokenizer có `offset_mapping` hoặc `word_ids` dùng được. Kiểm khả năng API thật của phiên bản pin; nếu không có, hiện thực mapping có test.
- Tách encoder subwords khỏi prediction units. Chốt đơn vị CRF và pooling trước train; có thể dùng raw surface units đã round-trip được rồi lấy embedding qua map từ subword. Nếu dùng segmented words, chứng minh mọi gold boundary biểu diễn được.
- Không dùng gold để tách segmented word. Không bỏ qua trường hợp một segmented word hoặc subword phủ nhiều raw units/span.
- Padding/special token không nhận gold BIO; chỉ đưa chuỗi prediction units thật vào CRF. Mask CRF phải phù hợp API, tránh mask có lỗ giữa chuỗi hoặc sentinel nhãn âm lọt vào CRF.
- Chốt policy chuỗi dài bằng giới hạn tokenizer/model thật. Không hardcode 512. Nếu dùng windows, phải không phụ thuộc gold lúc inference, có owner rule cho vùng overlap và test ghép về một tập span không trùng/overlap. Nếu chưa hỗ trợ, trả lỗi rõ thay vì silently truncate.

#### U3.2. Model và trainer

- Encoder pretrained + dropout + linear emission + CRF BIO23.
- Có luật chuyển BIO hợp lệ cho start/end và các transition. Mask transition phải áp dụng nhất quán ở loss/partition và Viterbi, không chỉ sửa output sau decode.
- Trainer train-only 240; validation 60 để chọn checkpoint theo exact-span micro F1. Không dùng T1/span system/source stratum làm feature hoặc target bổ sung cho baseline này.
- Optimizer, learning rate encoder/head, weight decay, gradient clipping, scheduler, effective batch size và mixed precision có config; CPU smoke không bắt buộc AMP.
- Checkpoint lưu encoder/head/CRF, tokenizer/segmenter identifiers, label map, processor version, optimizer/scheduler và metadata để reload đúng.
- Dependency là optional với core: module dữ liệu/scorer/CLI help vẫn import được khi Torch/Transformers không có. Lỗi phải chỉ ra package/resource thiếu và lệnh đã được kiểm, không tự cài lúc import.

#### U3.3. Kiểm thử

- Khi Torch đã có: tiny encoder không cần tải weights, forward/backward, gradient emission/CRF, finite loss, Viterbi hợp lệ, batch padding và save/load output tương đương trong eval.
- Test brute-force CRF trên chuỗi nhỏ để kiểm partition/Viterbi/constraint nếu tự hiện thực CRF; không chấp nhận một class mang tên CRF nhưng chỉ dùng token cross-entropy/argmax.
- Adapter/inference test nhận text-only và exact offset sau decode.
- Khi dependency chưa có, test thuần Python alignment/config/data gate vẫn chạy; neural tests skip có lý do, không thay bằng mô hình giả để báo PASS neural integration.

**Đầu ra:** alignment processor, model, trainer, adapter, config, test/log và hướng dẫn. Ghi riêng runtime/segmenter/pretrained integration còn thiếu.

### U4 — Mô hình đề xuất và giải mã cấu trúc động

**Mục tiêu:** T0 + T1 từ chuỗi input, với ràng buộc hành chính có thể kiểm chứng và ablation công bằng.

#### U4.1. Kiến trúc và loss

- Tái sử dụng PhoBERT alignment/encoder từ U3; chốt kiến trúc đầu T0 trong protocol. Không cần tự thêm span-system head khi chưa có yêu cầu/chỉ tiêu riêng.
- T1 gold có ba lớp `cu/moi/Lai`; `khong_ro` là trạng thái từ chối khi inference. Mặc định dùng head ba lớp + confidence/margin để abstain; không coi gold null là lớp `khong_ro` thứ tư.
- Loss T0 dùng tất cả span đã duyệt. Loss T1 chỉ dùng gold hợp lệ không thuộc `evaluation_exclusions.t1`.
- Nếu có consistency loss, mask cùng những mẫu gold null/ngoại lệ T1; kiểm trường hợp batch không có T1 eligible: loss hữu hạn, không chia cho 0.
- Loss weight, abstain threshold, margin và quy tắc confidence ghi trong config; không đặt ngưỡng theo gold của từng mẫu inference.

#### U4.2. Constrained decoding

- Dự đoán T1 từ encoder/text. Không đưa hệ nguồn/`HeQuyChieu` gold hoặc ngày tham chiếu gold của mẫu vào decoder.
- Chỉ khi T1 `moi` vượt policy confidence đã khóa mới áp ràng buộc không xuất `QuanHuyen`.
- Với `cu`, `Lai` hoặc `khong_ro`: không tự xóa quận/huyện và không ép địa chỉ thiếu quận thành mới. Cho phép thành phần thiếu đúng theo chuỗi quan sát.
- Dùng constrained decode hợp lệ ở không gian nhãn/path, lưu output trước/sau constraint và nguyên nhân. Không dùng gold để xóa span sai sau scoring.
- Không tạo trường còn thiếu, đổi text hoặc relabel mọi span theo T1 toàn câu.
- Trace gồm posterior T1, confidence/threshold, quyết định cấu trúc, path/span bị ảnh hưởng, trạng thái abstain và rule version.
- Không hứa triệt tiêu toàn bộ lỗi quận: đo FP trên gold mới không có quận và recall trên gold cũ/lai; có thể giảm FP nhưng làm mất recall khi T1 sai.

#### U4.3. Ablation và kiểm thử

- `PROPOSED-DYN` và cấu hình bỏ constraint giữ cùng encoder, head, training config, data, seed và checkpoint; ưu tiên so hai decoder trên cùng checkpoint để cô lập tác dụng constraint.
- Nếu thêm ablation bỏ T1/loss thì dùng ID/config riêng và ghi thay đổi chính xác, không trộn với ablation chỉ bỏ decode constraint.
- Test `moi` chắc/không chắc, `cu`, `Lai`, `khong_ro`, input thiếu trường, T1 đoán sai và không có T1 gold.
- Test mask ngoại lệ đọc từ manifest: T0 vẫn có loss/metric; T1 và consistency/diagnostics không tính mẫu bị mask. Không đổi annotation task 543.
- Test path BIO hợp lệ sau constraint, không overlap, không thêm đơn vị hành chính và không truy cập gold trong decoder.

**Đầu ra:** model/trainer/adapter đề xuất, decoder, ablation configs, trace schema và test. Chưa train thật thì chỉ báo mã/kiểm thử, không có điểm đề xuất hay kết luận ablation thực nghiệm.

### U5 — Protocol huấn luyện, chọn cấu hình và ablation

**Mục tiêu:** khóa quy trình trước khi chạy/tune, tránh chọn theo những đáp án đã xem và so mô hình lệch ngân sách.

- Tạo `docs/sprints/sprint_03/17_training_protocol_v1.md` và config JSON tương ứng; nội dung phải khớp trainer.
- Ghi model ID, encoder/checkpoint/revision, processor, label map, supported labels, heads/tasks và quyền dùng resource.
- Giữ 240 train/60 dev; không gộp, chia lại hoặc dùng 5-field benchmark để tune neural trong lượt này.
- Metric chọn checkpoint: exact-span micro F1 toàn 11 nhãn trên dev, unsupported gold vẫn là FN. Tie: macro F1 trên nhãn có gold support, sau đó epoch sớm hơn; tie giữa configs theo thứ tự cấu hình đã khai báo.
- T1/report cấu trúc phải mask theo manifest. Head T1 chọn threshold trên dev eligible, không trên gold-null hoặc ngoại lệ.
- Khai báo số candidate/hyperparameter ranges, tối đa epochs, patience, effective batch size và chi phí mỗi cấu hình. Không tự tăng số lần thử khi kết quả dev chưa đẹp.
- Đặt seed phát triển 42; cấu hình kiểm độ ổn định dự kiến [42, 1337, 2025]. Ghi rõ đây là kế hoạch chạy về sau, chưa phải ba run đã thực hiện.
- Các mô hình/ablation dùng budget công bố trước. Khác biệt bắt buộc vì API phải được ghi, không gọi mọi điều kiện bằng nhau nếu không bằng nhau.
- Log RNG Python/NumPy/Torch/CUDA khi có; cờ deterministic và giới hạn tái lập theo runtime. Không hứa bitwise-identical giữa mọi GPU/version.
- Chốt chính sách truncation/windows, số mẫu không align, illegal BIO repair/reject, hỗ trợ nhãn và đánh giá toàn schema.
- Bảng metric tách T0, T1, 5 trường và chẩn đoán cấu trúc; T0-only không bị mô tả là classifier T1 có accuracy 0.
- Luôn báo support từng nhãn, nguồn observed/derived/synthetic theo metadata và hạn chế 0/1 support. Không suy noise subtype từ text vì metadata hiện `not_recorded`.
- Bộ test 100 vẫn nằm ngoài lượt này; báo cáo dùng trạng thái dev/development.

**Nghiệm thu:** protocol và configs có version/hash, CLI từ chối cấu hình không tương thích; có test label/processor mismatch, lựa chọn checkpoint/tie, dev-only selection và seed/config manifest.

### U6 — Quản lý checkpoint, prediction và artifact

**Mục tiêu:** thêm các mô hình mới vào hạ tầng hiện hữu, đủ bằng chứng chạy lại và phát hiện sửa artifact sau inference.

#### U6.1. Tích hợp và checkpoint

- Mở rộng `experiment_config.py`/factory và runner hiện có theo interface; không xây scorer khác để lấy điểm thuận lợi hơn.
- Training CLI có lệnh prepare/preflight/train; chỉ lệnh train được yêu cầu mới thực thi training. Help/preflight không tự tải model hay train.
- Mỗi run có ID/thư mục mới. Output đã tồn tại phải bị từ chối; không ghi đè baseline, corpus, gazetteer hoặc run frozen.
- Lưu best và last checkpoint riêng. Metadata tối thiểu: model/task, label map, processor/tokenizer/segmenter, base revision/resources, config, train/dev/corpus hash, epoch/global_step, optimizer/scheduler/scaler/RNG nếu resume được hỗ trợ.
- Resume vào run mới, tham chiếu checkpoint nguồn và hash; kiểm data/config compatibility. Resume optimizer khác với nạp weights để bắt đầu run mới; log chính xác loại thao tác.
- Checkpoint tạm ghi rồi hoàn tất atomically trước hash; không để manifest coi file đang ghi là checkpoint hoàn chỉnh.
- Nếu dependency/API không hỗ trợ một khả năng, fail rõ hoặc khai báo unsupported; không tạo placeholder để nghiệm thu.

#### U6.2. Prediction và scoring

- Inference dev lấy input text-only; một record cho mỗi ID, bao gồm runtime error, alignment reject và abstain.
- Lưu `raw_output`, token/native tags hoặc emission/path khi phù hợp, T1 posterior, alignment/constraint trace, latency. Không đưa gold vào raw prediction/trace inference.
- Lưu prediction/model config/run manifest và output hashes trước scoring. Scorer kiểm hash/version; test tampering phải bị từ chối.
- Chấm từ prediction đã đóng băng bằng `span_scorer.py` và pipeline hiện có. Tách error analysis chứa gold khỏi output inference.
- Lưu config/resources/code hashes bao phủ tất cả module thực sự dùng, không chỉ hash runner. Ghi git revision và trạng thái dirty nhưng không lấy git HEAD như bằng chứng cho code chưa commit.
- Tài nguyên thực tế được pin/hash lại lúc chạy; cấu hình placeholder chưa tải không được ghi thành verified hash.
- Fixture/tiny random model output nằm trong thư mục verification riêng, có `purpose=unit_or_integration_test`, `pretrained=false`; không gộp vào bảng kết quả baseline.
- Bổ sung audit read-only kiểm corpus/split, config/checkpoint/resource, prediction count/status/offset, T1 mask và sự phân biệt fixture/thực nghiệm.
- Giữ các audit và run đã có, không rescore ghi đè sau khi đổi code.

**Cấu trúc một run thực nghiệm dự kiến:**

```text
<new_run_id>/
  model_config.json
  training_manifest.json
  training_log.jsonl
  checkpoints/
  run_manifest.json
  predictions.jsonl
  raw_outputs.jsonl             hoặc raw_output bên trong prediction
  alignment_log.jsonl           hoặc trace có cùng thông tin
  metrics.json
  scoring_manifest.json
  error_analysis.jsonl
  completion_audit.json
```

Chỉ tạo metric khi có prediction thực tế tương ứng. File manifest có thể ghi `not_run` và blocker, không điền số 0 thay kết quả chưa chạy.

**Nghiệm thu:** CLI/config/factory hoạt động; test thiếu tài nguyên, hash thay đổi, resume mismatch, label mismatch, input bị lẫn metadata và giữ đủ ID; các artifact có nguồn rõ.

### U7 — Nguồn, mã hành chính và coverage gazetteer

**Mục tiêu:** bổ sung bằng chứng cho gazetteer theo thời gian mà không biến mã candidate hoặc tên giống nhau thành quan hệ pháp lý.

#### U7.1. Kiểm toán nguồn

- Đọc source register, schema, builder/lookup và manifest s3_v2 trước sửa.
- Tra cứu nguồn sơ cấp từ cơ quan nhà nước/văn bản chính thức cho mã đơn vị cũ trước 01/07/2025; cho mã/bảng ánh xạ mới tìm ấn phẩm gốc, cơ quan phát hành, thời kỳ và quyền tái sử dụng.
- Mỗi bằng chứng lưu source ID, URL tài liệu cụ thể, document/version ID, cơ quan, ngày ban hành, thời điểm truy cập, effective interval, điều khoản sử dụng tìm được, vị trí trang/dòng và hash nếu có file thực tế được phép lưu.
- Không mặc định văn bản công khai đồng nghĩa mọi bảng dẫn xuất bên thứ ba có cùng giấy phép. Trạng thái quyền dùng chưa xác định phải lưu đúng như vậy.
- Không gọi ID di sản `official_mapping_2025` là chứng minh nguồn chính thức. Phân biệt khớp file trong repo với xác minh bằng nguồn pháp lý bên ngoài.
- Không tạo dữ liệu địa chỉ mới, không crawl hàng loạt. Khi nguồn/reference file cần tải chưa được phép hoặc chưa thể xác minh, lưu URL/gap/blocker và tiếp tục toolkit/coverage; không bịa source hash, ngày hoặc license.

#### U7.2. Verification toolkit

- Tạo công cụ đối chiếu bảng reference được cung cấp theo khóa đầy đủ tỉnh–huyện–xã cũ, cấp/hệ và thời kỳ.
- Đọc mã dưới dạng string để giữ zero đầu; padding chỉ theo schema nguồn chính thức, không tự đoán độ dài.
- Chỉ nâng trạng thái từng mã khi match chắc chắn cùng cấp/hệ, khóa cha và thời kỳ. Fuzzy match chỉ tạo queue review, không tự xác nhận mã.
- Canonical tên giữ loại đơn vị và dấu; normalization/alias chỉ từ lớp đã audit, có trace. Không tự thêm alias/cạnh bằng LLM hoặc suy từ tên.
- Giữ internal `entity_id` ổn định hoặc có migration map rõ. Internal ID không được mô tả là mã nhà nước.
- Bảo toàn đồ thị 1-1/1-N/N-1/M-N và 5 chuyển đổi phi nguyên tử huyện→đặc khu. Không ép nhiều đích thành một đích khi thiếu bằng chứng lãnh thổ.
- Validity là interval có policy rõ, ưu tiên `[valid_from,valid_to)`; không suy thời kỳ từ tên bề mặt. Ngày không biết giữ unknown có lý do, không bịa để qua lookup.
- Lookup `(name,level,reference_date,parent_context)` trả ID/candidate, code status, nguồn/bằng chứng và reject reason. Đồng tên hai hệ giữ candidate/ambiguity, không chọn dòng đầu.

#### U7.3. Phiên bản và nghiệm thu

- Không sửa package s3_v1/s3_v2 frozen hoặc CSV reference hiện hành. Dẫn xuất mới nằm tại interim version riêng; chỉ phát hành package mới khi có bằng chứng đủ cho phần nâng cấp.
- Khi phát hành version mới: có schema/version, nguồn/hash, coverage verified/candidate/unverified theo cấp/hệ, diff từ v2 và test lookup ngày/trùng tên/multiple targets/missing code.
- Nếu chưa tìm được nguồn đủ mạnh: hoàn thiện toolkit, source audit, gap report; giữ dữ liệu ở `PARTIAL_OLD_CODES_UNVERIFIED` hoặc trạng thái partial tương ứng. Không tạo v3 chỉ để đổi tên và báo gazetteer hoàn tất.
- Cấu hình HEUR-JW/run đã chốt vẫn tham chiếu s3_v2; version mới chỉ dùng trong run mới theo config riêng về sau.

**Đầu ra:** source audit/register, reference verifier, coverage/gap report, test và package mới chỉ nếu đủ điều kiện. Báo chính xác số mã đã verified; số 0 verified là kết quả audit hợp lệ nhưng không phải xác minh đầy đủ 10.035 mã.

### F. Tổ chức mã và đầu ra đề xuất

Kiểm tra tên chưa bị sử dụng trước khi tạo; có thể điều chỉnh cấu trúc để hợp với repo, nhưng phải ghi mapping trong báo cáo:

```text
src/modeling/
  alignment.py
  datasets.py
  labels.py
  training.py
  checkpoints.py
  phobert_crf.py
  proposed_dynamic.py
  structural_decoder.py
src/evaluation/adapters/
  deepparse_finetuned_adapter.py
  phobert_crf_adapter.py
  proposed_dynamic_adapter.py
src/data/
  administrative_code_verifier.py
configs/modeling/sprint03/
  dp_ft_ft_v1.json
  phobert_crf_v1.json
  proposed_dyn_v1.json
  proposed_no_constraint_v1.json
  tuning_protocol_v1.json
scripts/
  30_prepare_model_training_data.py
  31_train_deepparse_finetuned.py
  32_train_phobert_crf.py
  33_train_proposed_dynamic.py
  34_audit_modeling_artifacts.py
  35_verify_gazetteer_sources.py
docs/sprints/sprint_03/
  17_training_protocol_v1.md
  18_modeling_resource_inventory.md
  19_seven_priorities_implementation_report.md
  20_gazetteer_source_audit.md
data/interim/modeling/sprint03/<new_version>/
  input_manifest.json
  alignment_report.json
  alignment_diagnostics.jsonl
  converted_data/
  verification/
```

Tránh lớp trừu tượng hoặc framework tổng quát vượt quá ba mô hình đang cần. Không nhồi model training vào scorer; giữ adapter inference, training và gold scoring ở các module riêng.

### G. Kiểm thử và kiểm tra cuối

Tuân thủ AGENTS.md. Không cài dependency để làm một test hết skip khi chưa có quyền.

1. Chạy kiểm thử hiện hữu làm mốc nếu runtime cho phép; ghi command/runtime và kết quả thực tế.
2. Thêm test chuyên biệt cho alignment, model pipeline, CRF, T1 mask, structural decoder, artifact và code verifier. Thêm regression trong `tests/test_data_pipeline.py` khi đổi logic `src/` theo yêu cầu repo.
3. Chạy toàn repo trong WSL môi trường dự án:

   ```bash
   cd /mnt/d/DACN
   source ~/.venv_dacn/bin/activate
   python -m unittest discover -s tests -v
   ```

4. Nếu runtime neural khác, chạy thêm các test tương ứng ở runtime đó với package versions ghi rõ. Test không có dependency phải skip cụ thể; báo PASS/SKIP/FAIL riêng, không báo tổng số test như thể tất cả đều chạy.
5. Chạy data preparation/preflight trên train/dev để kiểm số ID/span, round-trip, label/system mask, encoding và duplicate. Nếu resource processor thật thiếu, chạy phần core đã có và ghi processor pending.
6. Kiểm save/load, một forward/backward và resume trên tiny model khi Torch sẵn có; test thật không yêu cầu pretrained download. Giá trị loss fixture không phải metric mô hình nghiên cứu.
7. Kiểm input/output/resource/code hash và tính bất biến corpus, split, baseline/gazetteer frozen. Không sửa raw/export/canonical để chữa test.
8. Chạy `git diff --check`; kiểm các import/CLI help không khởi động training/tải model. Không tự thêm linter/formatter mới.
9. Cập nhật README, Sprint 3 README, AGENTS.md và `docs/data_quality.md` khi trạng thái/giới hạn/hợp đồng thực sự thay đổi. Giữ lịch sử; không ghi đã train hoặc verified trước khi có bằng chứng.

### H. Báo cáo bắt buộc trong chat và file

Viết `19_seven_priorities_implementation_report.md`; final trong chat phải tự đầy đủ, gồm:

1. **Bảng U1–U7:** nội dung đã hiện thực, test đã chạy, integration thật/pending, artifact, phần chưa hoàn thành và lý do.
2. File đã thêm/sửa và vì sao; giữ nguyên dữ liệu/model/run frozen được chứng minh bằng hash.
3. Coverage alignment train/dev theo processor; phần không biểu diễn được, cách xử lý và nhãn bị ảnh hưởng.
4. Neural code verification đã chạy tới mức nào. Mô hình nào chưa có checkpoint pretrained hoặc chưa train thật; không điền prediction/metric giả.
5. Protocol và config đã khóa, selection rule, masks và ablation.
6. Gazetteer: nguồn mới xác minh được, số mã nâng trạng thái, gaps và khả năng lookup; không gộp code license với model/data license.
7. Test counts/log paths, runtime và các skip/failure thực tế.
8. **Việc chủ dự án cần làm**, chỉ ghi các dependency cụ thể còn thiếu: cấp quyền cài/tải tài nguyên đã kiểm kê, cung cấp nguồn/reference nếu không truy được, hoặc mở lại giai đoạn chạy GPU về sau. Không giao lại những phần agent đã có quyền và có thể hoàn thiện.
9. Lệnh prepare/preflight/infer/score/train/resume đúng với CLI đã hiện thực. Các lệnh chạy nặng chỉ là hướng dẫn cho giai đoạn được mở lại, không phải đã chạy.

Không kết thúc với một danh sách TODO có thể hiện thực trong quyền hiện tại. Nếu một mục bị chặn, hoàn thiện tất cả phần độc lập và nêu rõ điều kiện để mở cổng tiếp theo. Mục tiêu bàn giao là mã thực, kiểm thử thực, protocol rõ và hồ sơ nguồn trung thực; chưa phải kết quả test cuối Sprint 3.

### I. Nguồn kỹ thuật để kiểm chứng khi hiện thực

Các trang này là điểm bắt đầu; kiểm API/version thật của runtime sẽ dùng:

- [Deepparse parser/retrain](https://deepparse.org/parser.html): validation container riêng, custom tags/EOS và cấu hình retrain. Chú ý `seq2seq_params` có thể đổi sang train từ đầu.
- [Deepparse custom tags](https://deepparse.org/examples/retrain_with_new_prediction_tags.html): ví dụ tag dictionary; không sao chép cách tự chia train nếu trái split dự án.
- [Deepparse FastText/runtime](https://deepparse.org/get_started/get_started.html): yêu cầu tài nguyên và tương thích loader.
- [PhoBERT chính thức](https://github.com/VinAIResearch/PhoBERT): word segmentation, checkpoint, giới hạn encoder và license theo từng phiên bản.
- [PhoBERT tokenizer trong Transformers](https://huggingface.co/docs/transformers/model_doc/phobert): kiểm khả năng tokenizer trước dùng offset API.

## Hết PROMPT
