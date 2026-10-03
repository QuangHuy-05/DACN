# U3 — Tài nguyên, giấy phép và cấu hình future Colab

Evidence: `data/interim/modeling/sprint03/pre_colab_20261003_resume_v1/u3_v3/`. Không cài package/venv/model mới trong lượt này. Mọi response/evidence/gói mới nằm trên D.

## Tài nguyên thật và phần còn chặn

| Thành phần | Identity | Trạng thái |
| --- | --- | --- |
| PhoBERT encoder/tokenizer | `01daacda68afe13d83023d16ec647239e344a1e6` | File local, SHA-256 kiểm lại, MIT |
| VnCoreNLP | `62bbc58fe5d113c898eae112656be97dcf50b3a0` | File local, SHA-256 kiểm lại, GPL-3.0-or-later; giữ LICENSE/source URL |
| Temurin Java | JRE 17.0.20.1+1 | Local D, lock và legal files; GPL với Classpath exception theo upstream |
| Runtime local | Python 3.11.16, Torch 2.8.0 CPU, Transformers 4.57.1, Deepparse 0.11.0, Poutyne 1.17.4, py-vncorenlp 0.1.4 | Tái sử dụng, không cài lại |
| Full FastText native Deepparse | **`cc.fr.300.bin`**, [Common Crawl](https://fasttext.cc/docs/en/crawl-vectors.html) | Chưa tải; CC-BY-SA 3.0 với attribution/share-alike; host RAM ≥10 GiB |
| Deepparse checkpoint | [fasttext-base](https://huggingface.co/deepparse/fasttext-base), revision `908f403d0432a8e650da41e08d01bd33d77ac47f` | Model card không ghi license weights; không lấy MIT code làm license weights; chưa active lock |
| CSV hành chính/response NSO | Hash thật, dated source ở U1/U2 | Original export URL/điều khoản tái phân phối CSV còn chưa xác minh |

FastText tiếng Pháp ở đây là đúng embedding downloader native của Deepparse 0.11.0; không đổi thành FastText tiếng Việt hoặc compressed vector rồi giữ model ID. HTTP 403 khi lưu HTML FastText bằng urllib đã ghi `DOWNLOAD_BLOCKED`; điều khoản được kiểm qua tài liệu chính thức. Metadata HF/PyTorch/Colab lưu được. Không tải full weights/embedding.

Lock thật: `data/interim/modeling/sprint03/task_01_06_20261003_v1/resource_lock_local_v1.json`; giữ nguyên. Recipe DP: `u3_v3/deepparse_download_recipe_pending.json` là prospective, **không phải active lock**. Registry ghi packages/resource hashes và metadata sources. Tài nguyên Java đã có legal files trong lock cũ; gói private gửi chủ dự án giữ nguyên LICENSE và link mã nguồn upstream.

## Profile portable

`configs/colab/sprint03/cuda128_profile_v1.json` là overlay mới, không sửa CPU/protocol lock. CUDA `cuda:0`, Torch 2.8.0 wheel cu128, float32, AMP=false, VRAM tối thiểu 8 GiB. [Lệnh Torch chính thức](https://pytorch.org/get-started/previous-versions/). Requirements shared/transitive pin theo runtime local; notebook dùng env Python 3.11 riêng và [uv 0.8.22](https://pypi.org/project/uv/0.8.22/) (MIT/Apache-2.0), chỉ là bootstrap tương lai, chưa cài local.

Giữ c01/c02, seed42, tối đa20 epoch, patience5, effective batch16, processor/label map/loss/scheduler đã khóa. GPU preflight từ chối CUDA thiếu/VRAM thấp, không fallback CPU âm thầm. Disk PhoBERT ≥20 GiB/run; DP ≥3 GiB/run sau resources; embedding cần riêng phần download+uncompressed+cache. Local hiện không đáp ứng neural disk budget/DP host RAM. Các cổng phải đo lại ở Colab; GPU không thay RAM hệ thống.

## Lệnh future — chưa thực thi training

Sau bootstrap notebook, tại root workspace:

```bash
PY=.venv_colab311/bin/python
LOCK=data/interim/modeling/sprint03/task_01_06_20261003_v1/resource_lock_local_v1.json
GPU=configs/colab/sprint03/cuda128_profile_v1.json
$PY -m scripts.32_train_phobert_crf preflight --resources "$LOCK" --hardware-profile "$GPU" --candidate c01
$PY -m scripts.32_train_phobert_crf train --resources "$LOCK" --hardware-profile "$GPU" --candidate c01 --run-id phobert_run001_c01 --output-dir data/processed/evaluation/sprint03/phobert_run001_c01
$PY -m scripts.32_train_phobert_crf infer --resources "$LOCK" --hardware-profile "$GPU" --candidate c01 --checkpoint data/processed/evaluation/sprint03/phobert_run001_c01/checkpoints/best.pt --output-dir data/processed/evaluation/sprint03/phobert_run001_c01_dev --inference-only
$PY -m scripts.32_train_phobert_crf score --resources "$LOCK" --hardware-profile "$GPU" --candidate c01 --source-run data/processed/evaluation/sprint03/phobert_run001_c01_dev
$PY -m scripts.34_audit_modeling_artifacts run --run-dir data/processed/evaluation/sprint03/phobert_run001_c01_dev --output data/interim/modeling/sprint03/phobert_run001_c01_audit.json
```

Cho proposed thay module bằng `scripts.33_train_proposed_dynamic`. Calibration dùng `calibrate --source-run <dev run đã freeze> --output-dir <thư mục mới>`; infer lại với `--decoder-policy <calibration>/decoder_policy.json`. Ablation thêm `--config configs/modeling/sprint03/proposed_no_constraint_v1.json`, **cùng best.pt**, profile, resources và candidate; không train thêm checkpoint ablation. Chạy c02 vào run riêng, chọn bằng dev theo protocol.

Resume PhoBERT: thêm `--resume-from <run trước>/checkpoints/last.pt` vào lệnh train ở output mới, cùng resources/profile/candidate. Giữ optimizer/scheduler/RNG; chỉ `--weights-from` là restart optimizer.

DP sau license/hash/RAM/native loader gates: `scripts.31_train_deepparse_finetuned preflight/train/infer/score`, `--resources <active DP lock thật>`, cùng c01/c02 và output mới; native CPU profile đã pin, không dùng PhoBERT lock. `--weights-from <DP best.pt>` chỉ là weights restart; không có optimizer resume.

DP-ZS-FT sau gate dùng:

```bash
$PY -m scripts.47_prepare_dp_zero_shot_config --resources <active-DP-lock.json> --run-id dp_zs_run001 --output data/interim/modeling/sprint03/dp_zs_run001_config.json
$PY -m scripts.23_run_span_dev --input data/processed/annotation/sprint03/corpus_train_dev_v2/dev_input.jsonl --corpus-manifest data/processed/annotation/sprint03/corpus_train_dev_v2/manifest.json --model-config data/interim/modeling/sprint03/dp_zs_run001_config.json --output-dir data/processed/evaluation/sprint03/dp_zs_run001
$PY -m scripts.24_score_span_dev --predictions data/processed/evaluation/sprint03/dp_zs_run001/predictions.jsonl --gold data/processed/annotation/sprint03/corpus_train_dev_v2/dev.jsonl --corpus-manifest data/processed/annotation/sprint03/corpus_train_dev_v2/manifest.json --run-dir data/processed/evaluation/sprint03/dp_zs_run001
```

`<active-DP-lock.json>` chưa tồn tại: không chạy bằng template/recipe. Script47 không tạo active config khi thiếu gate; adapter47/locked loader chỉ chọn native pretrained checkpoint, không fine-tune. Tests dùng mock/fixture, không chứng minh full pretrained đã chạy.

Accounting: cài mới **0 bytes = 0 GB = 0 GiB**; tổng cài lịch sử 2.453.588.804 bytes = 2,453588804 GB = 2,285082642 GiB, không cộng trùng. Response nguồn/baseline/ZIP là artifact, thống kê riêng ở `storage_accounting.json` trong evidence root sau đóng gói.
