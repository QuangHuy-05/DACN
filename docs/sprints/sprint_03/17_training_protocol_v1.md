# Protocol huấn luyện Sprint 3 — v1

Ngày khóa: 02/10/2026; processor alignment được amendment ngày 03/10/2026. Trạng thái: **PROTOCOL_LOCKED_CODE_VERIFICATION_ONLY**. Ngân sách và split không đổi; huấn luyện nặng và test100 đang hoãn. Config tại `configs/modeling/sprint03/`; dấu vân tay cấu hình được cập nhật trong `protocol_lock_v1.json`.

## 1. Dữ liệu, nhiệm vụ và quyền truy cập

- Dùng duy nhất `corpus_train_dev_v2`: **240 train / 60 dev**, 1.057 / 284 span. Loader kiểm manifest SHA-256 `9c91b77f…` và toàn bộ output hash; không chia lại, gộp split hay tune neural bằng benchmark 5 trường.
- Inference chỉ đọc `dev_input.jsonl` gồm ID/text. Adapter chỉ nhận text. Gold được dùng trong training và scoring sau khi prediction đã lưu/hash.
- T0: 11 nhãn, BIO23; `O` là nền. DP thêm EOS nội bộ thành 24 tag, không thêm một nhãn span.
- T1: ba lớp `cu`, `moi`, `Lai`; gold null và danh sách `evaluation_exclusions.t1` bị mask. Hiện đủ điều kiện **206 train / 53 dev**. `khong_ro` là abstain của inference, không phải lớp huấn luyện.
- Task543 giữ tất cả T0, mask T1/loss hệ/chẩn đoán hệ. Không mở lại quyết định người duyệt hoặc sửa annotation.
- Data05 `DEFERRED_BY_USER`; VQA `HOLD`; independent agreement `NOT_MEASURED`; test100 không nằm trong lượt này.

## 2. Processor và kiến trúc

| Model | Processor / đơn vị dự đoán | Kiến trúc và T1 |
| --- | --- | --- |
| DP-FT-FT | `dp_surface_bio_v1`; raw surface tokens, dấu câu giữ thành token | Native FastText **full**, pretrained seq2seq; custom head24 tag; không CRF, không T1 |
| PHOBERT-CRF | `phobert_raw_unit_pool_v2_tone_relocation`; encoder subwords map về raw token, mean pooling | PhoBERT-base + dropout + emission + linear-chain CRF thật; không T1 |
| PROPOSED-DYN | cùng processor/encoder/T0 CRF | Thêm head T1 ba lớp; loss T0 + 0,5 loss T1 eligible; consistency weight = 0 |
| PROPOSED-NO-CONSTRAINT | cùng checkpoint của PROPOSED-DYN | Chỉ bỏ ràng buộc giải mã; không huấn luyện checkpoint khác |

PhoBERT cần word segmentation theo [hướng dẫn VinAI](https://github.com/VinAIResearch/PhoBERT). Chọn VnCoreNLP `wseg`; tokenizer slow, không giả định có `offset_mapping`. Giới hạn cấu hình **256**, tiếp tục đối chiếu giới hạn tokenizer/encoder thực khi nạp. NFC chỉ phục vụ so sánh mapping; text và offset gốc được giữ. Processor v2 chấp nhận riêng việc VnCoreNLP chuyển vị trí dấu thanh bên trong cùng cụm nguyên âm liên tiếp khi chữ cái nền, dấu chất lượng nguyên âm và tập dấu thanh vẫn trùng khớp. Mapping từng ký tự quay lại grapheme gốc; đổi dấu/chữ hoặc chuyển dấu qua phụ âm, âm tiết, khoảng trắng hay dấu phân cách vẫn bị từ chối. Trace lưu từng vị trí ký tự có dấu trước/sau khác nhau. Không sửa raw text/gold, không dùng fuzzy alignment, không truncation/windows.

DP fine-tune dùng container train và validation riêng; `seq2seq_params=None`. Dấu câu không bị default cleaner xóa. Parser dùng nhánh native logits T×B×C để lưu cả EOS/tag thừa, thay vì formatted output có thể zip mất token. API được guard theo signature thực tại runtime. Tài liệu web đang mang nhãn 0.10.0, profile package là 0.11.0: **integration chưa xác minh**, không gọi đây là API đã chạy thật. [Tài liệu API Deepparse](https://deepparse.org/_modules/deepparse/parser/address_parser.html).

Trước batch huấn luyện đầu, callback so shape/hash state trước/sau native head replacement, lưu `transfer_report.json` liệt kê tên layer được giữ, khởi tạo/thay và bỏ. Nếu không chứng minh được encoder pretrained giữ nguyên lúc khởi tạo thì dừng. Danh sách layer thực chỉ được công bố sau integration; chưa suy đoán tất cả decoder layer đều được chuyển nguyên vẹn.

CRF áp dụng cùng mask BIO ở start, partition, loss và Viterbi. Special/padding không nhận gold; pad target là O cùng mask liền mạch. Hai span liền kề cùng nhãn có B mới. Gold không được dùng để tách token.

## 3. Budget khóa trước thực nghiệm

| Hạng mục | DP-FT-FT | PHOBERT-CRF / PROPOSED-DYN |
| --- | --- | --- |
| Candidate theo thứ tự | c01: SGD lr0,01; c02: lr0,005 | c01: encoder lr2e-5; c02: lr5e-5; head lr1e-3 |
| Epoch / patience | tối đa20 / 5 | tối đa20 / 5 |
| Effective batch | 16, native API | 16 = micro4 × accumulation4 |
| Optimizer / scheduler | native SGD; native teacher forcing; không scheduler riêng | AdamW, decay0,01; warmup10% + linear decay; clip1,0 |
| Dropout / AMP | pretrained native architecture | dropout0,1; AMP **off** v1 |
| Ngân sách mẫu–epoch | tối đa9.600 cho hai candidate | tối đa9.600 mỗi mô hình cho hai candidate |
| Ước lượng đĩa khi đã có resource | dự phòng3GiB/run | dự phòng20GiB/run cho epoch weights, best/last và full resume state |

Tối đa **6 candidate training runs** ở seed phát triển42; không tự tăng search. Ablation chỉ thêm hai lần inference trên cùng checkpoint. Khác native optimizer/teacher forcing là khác biệt bắt buộc, không khẳng định ngân sách tính toán bằng nhau. Chưa có thời gian/GPU-hour thực đo. Stability seeds `[42,1337,2025]` là kế hoạch về sau, **chưa chạy**; thay seed phải ghi config/run mới.

## 4. Chọn checkpoint và cấu hình

Mỗi epoch: lưu checkpoint → inference tất cả60 ID từ text-only → khóa prediction/config/input/resource/code hash → scorer hiện hữu đọc dev gold.

Thứ tự chọn:

1. Exact-span **micro F1 toàn 11 nhãn** dev; tính từ TP/FP/FN nguyên để tránh tie do rounding.
2. Macro F1 chỉ các nhãn **có gold support**.
3. Epoch sớm hơn.
4. Candidate sớm hơn trong `[c01,c02]`.

Unsupported gold giữ FN. Error/alignment reject vẫn giữ ID trong mẫu số. Không chọn theo native accuracy hoặc loss. Proposed chọn checkpoint bằng **decoder không constraint**; sau đó so hai decoder cùng checkpoint. `best.pt` theo protocol; DP file native best-loss không phải kết quả chọn của dự án.

Training log lưu mỗi epoch, global step, loss và selection key. RNG Python/NumPy/Torch/CUDA được lưu nếu có; validation bảo toàn RNG của training dù runner đặt seed inference. Torch deterministic bật; không hứa bitwise giống giữa GPU/runtime khác nhau.

## 5. T1 confidence và ràng buộc

Operating policy trước calibration: threshold0,8; margin0,2. Grid **6 điểm** khóa: threshold `[0.7,0.8,0.9]` × margin `[0.1,0.2]`. Sau chọn checkpoint, script33 `calibrate` chỉ dùng posterior dev đã đóng băng và gold T1 eligible, giữ failure/abstain trong mẫu số. Chọn T1 macro F1 gold-supported, rồi accuracy toàn eligible, coverage, threshold cao hơn, margin cao hơn. Lưu toàn sweep và policy gắn hash checkpoint/prediction/corpus. **Calibration chưa chạy thật**.

Chỉ `moi` đủ confidence/margin mới ban B/I-QuanHuyen trong Viterbi. `cu`, `Lai`, `khong_ro` giữ đủ không gian nhãn. Không thêm trường thiếu, đổi text hay gán hệ mới cho tất cả span. T1-only abstain giữ T0; `SpanModelOutput.abstain` dành cho T0 không dùng được.

Hai decoder dùng cùng policy đã calibration, config, checkpoint và seed. Trace giữ posterior, policy, path/span trước/sau constraint, unit thay đổi và lý do. Chấm FP quận trên gold mới không có quận và recall quận cũ/lai bằng scorer, mask hệ theo manifest. T1 sai có thể làm mất recall quận; không hứa loại bỏ toàn bộ lỗi.

## 6. Checkpoint và artifact

- Mỗi run mới; từ chối output tồn tại hoặc ghi vào raw/annotation/gazetteer/frozen run.
- Epoch weights bất biến; best riêng; last có optimizer/scheduler/RNG để resume PhoBERT vào **run mới**. Full resume state cũ chỉ được xoay vòng trong run đang chạy; epoch weights gắn prediction vẫn giữ. Alias dùng hardlink khi được, fallback copy.
- Resume kiểm label map, processor, data/resource hash và training signature. Nạp weights khởi động optimizer mới khác với optimizer resume. DP optimizer resume **UNSUPPORTED**, dùng `--weights-from` ở run mới.
- Checkpoint ghi temp rồi atomic replace trước hash/metadata complete. Epoch model-only không được gọi là optimizer-resumable.
- Config, code thực trên đĩa, dirty Git, resource hash và corpus hash đều lưu. HEAD không thay thế hash mã chưa commit.
- Fixtures: `purpose=unit_or_integration_test`, `pretrained=false`; không đưa vào bảng thực nghiệm.
- Scoring không ghi đè. Audit đọc-only kiểm ID/status/raw span, hash và T1 exclusions; không rescore run cũ.

## 7. Lệnh vận hành

Hiện được chạy prepare/preflight/tests; các lệnh train/infer dưới đây chỉ dùng **sau khi được mở lại giai đoạn neural, dependency/resource integration đã xác minh**. Thay tên run nếu thư mục đã có.

```bash
cd /mnt/d/DACN
source ~/.venv_dacn/bin/activate
python -m scripts.30_prepare_model_training_data prepare \
  --output-dir data/interim/modeling/sprint03/prepare_new_v1
python -m scripts.31_train_deepparse_finetuned preflight
python -m scripts.32_train_phobert_crf preflight
python -m scripts.33_train_proposed_dynamic preflight
```

Preflight exit2 là blocker dự kiến khi thiếu package/resource; không phải đã train. Profile neural dùng Python3.11 WSL cô lập sau khi được cấp quyền cài/tải, không đổi env dự án3.14.

```bash
PY=data/interim/evaluation/sprint03/runtime_py311/bin/python
LOCK=data/interim/modeling/resources/phobert_lock.json
RUN=data/processed/evaluation/sprint03/phobert_crf_train_new_c01
"$PY" -m scripts.32_train_phobert_crf preflight --resources "$LOCK"
"$PY" -m scripts.32_train_phobert_crf train --candidate c01 \
  --resources "$LOCK" --output-dir "$RUN"
"$PY" -m scripts.32_train_phobert_crf infer --candidate c01 \
  --resources "$LOCK" --checkpoint "$RUN/checkpoints/best.pt" \
  --output-dir data/processed/evaluation/sprint03/phobert_crf_dev_new_v1 --inference-only
"$PY" -m scripts.32_train_phobert_crf score \
  --source-run data/processed/evaluation/sprint03/phobert_crf_dev_new_v1
"$PY" -m scripts.32_train_phobert_crf train --candidate c01 \
  --resources "$LOCK" --resume-from "$RUN/checkpoints/last.pt" \
  --output-dir data/processed/evaluation/sprint03/phobert_crf_train_resume_new
```

Resume bị từ chối nếu run đã dùng hết epoch/patience. DP dùng script31, lock FastText khác và `--weights-from` thay optimizer resume. Candidate c02 luôn có thư mục riêng. CLI `infer` mặc định chấm sau khi freeze; `--inference-only` dành cho hai lệnh tách riêng ở trên.

Proposed và ablation:

```bash
PRUN=data/processed/evaluation/sprint03/proposed_train_new_c01
"$PY" -m scripts.33_train_proposed_dynamic train --resources "$LOCK" --output-dir "$PRUN"
"$PY" -m scripts.33_train_proposed_dynamic infer --resources "$LOCK" \
  --checkpoint "$PRUN/checkpoints/best.pt" \
  --output-dir data/processed/evaluation/sprint03/proposed_dev_calibration_input
"$PY" -m scripts.33_train_proposed_dynamic calibrate \
  --source-run data/processed/evaluation/sprint03/proposed_dev_calibration_input \
  --output-dir data/interim/modeling/sprint03/proposed_calibration_new
POLICY=data/interim/modeling/sprint03/proposed_calibration_new/decoder_policy.json
"$PY" -m scripts.33_train_proposed_dynamic infer --resources "$LOCK" \
  --checkpoint "$PRUN/checkpoints/best.pt" --decoder-policy "$POLICY" \
  --output-dir data/processed/evaluation/sprint03/proposed_dyn_dev_new
"$PY" -m scripts.33_train_proposed_dynamic infer \
  --config configs/modeling/sprint03/proposed_no_constraint_v1.json \
  --resources "$LOCK" --checkpoint "$PRUN/checkpoints/best.pt" --decoder-policy "$POLICY" \
  --output-dir data/processed/evaluation/sprint03/proposed_no_constraint_dev_new
python -m scripts.34_audit_modeling_artifacts run \
  --run-dir data/processed/evaluation/sprint03/proposed_dyn_dev_new \
  --output data/interim/modeling/sprint03/proposed_dyn_audit_new.json
```

## 8. Giới hạn báo cáo

Dev: SoNha56, TenDuong60, Ngo/Hem13, PhuongXa61, QuanHuyen37, TinhThanh54, HuongDi1, GhiChu1, Khac1; **ToaNha/CanHo0, MocDinhVi0**. Không kết luận năng lực ở nhãn0/1 support. Provenance sidecar giữ observed/derived/synthetic; noise subtype `not_recorded` không suy từ text. T0, T1, 5 trường và chẩn đoán cấu trúc báo riêng. Chưa có checkpoint hoặc metric neural thật trong lượt này.
