# Runtime local và tích hợp neural thật — 03/10/2026

## 1. Phạm vi và môi trường

Đã cài runtime CPU mới, kiểm API thật và processor/pretrained forward. **Không train, không tạo prediction benchmark hoặc metric neural**, không sử dụng Colab/test100. Runtime Python3.11.16 nền có sẵn được đọc để tạo venv mới; không cài lại Python, không thay env dự án/CRF/Label Studio, apt, sudo hoặc cấu hình WSL.

Runtime: `data/interim/modeling/sprint03/runtime_neural_d_v1/`.
Cache/temp: `data/interim/modeling/sprint03/install_cache_d_v1/`.
Model/Java/segmenter: `data/interim/modeling/sprint03/resources_d_v1/`.
Evidence: `data/interim/modeling/sprint03/task_01_06_20261003_v1/`.

Kiểm kê trước cài nằm ở [inventory23](23_task_01_06_install_inventory_20261003.md). Các resolver inventories v2 ghi exact dependency, official URL, artifact hash/bytes, license metadata + license trong distribution **trước actual install**. Pin không bị thay đổi. Có 67 package được cài theo hai resolver (9+58), runtime có 69 distributions kể cả pip/setuptools bootstrap. Không cài CUDA/nvidia/triton/torchvision/torchaudio.

## 2. Những gì thực sự đã cài/tải

| Thành phần | Phiên bản/revision | Nguồn và license | Đích |
|---|---|---|---|
| Torch | 2.8.0+cpu | [PyTorch CPU index](https://download.pytorch.org/whl/cpu), BSD3 | runtime D |
| Transformers | 4.57.1 | [PyPI chính thức](https://pypi.org/project/transformers/4.57.1/), Apache2 | runtime D |
| Deepparse | 0.11.0 | [PyPI chính thức](https://pypi.org/project/deepparse/0.11.0/), LGPL3 | runtime D |
| Poutyne | 1.17.4 | [PyPI chính thức](https://pypi.org/project/Poutyne/1.17.4/), LGPL3 | runtime D |
| py-vncorenlp wrapper | 0.1.4 | [PyPI chính thức](https://pypi.org/project/py-vncorenlp/0.1.4/), MIT | runtime D |
| PhoBERT-base | `01daacda68afe13d83023d16ec647239e344a1e6` | [VinAI model](https://huggingface.co/vinai/phobert-base/tree/01daacda68afe13d83023d16ec647239e344a1e6), model card và VinAI LICENSE MIT | `resources_d_v1/phobert_base/` |
| VnCoreNLP jar1.2 + wordsegmenter | `62bbc58fe5d113c898eae112656be97dcf50b3a0` | [Repository chính thức](https://github.com/vncorenlp/VnCoreNLP/tree/62bbc58fe5d113c898eae112656be97dcf50b3a0), GPL3-or-later theo LICENSE của repo | `resources_d_v1/vncorenlp_wseg/` |
| Temurin JRE17 x64 Linux | 17.0.20.1+1 | [Release Adoptium](https://github.com/adoptium/temurin17-binaries/releases/tag/jdk-17.0.20.1%2B1), [GPL2 + Classpath exception](https://adoptium.net/docs/faq) | `resources_d_v1/java17/` |

License của wrapper py-vncorenlp không thay license jar/assets. Không tải FastText full, BPEmb weights hoặc checkpoint Deepparse pretrained. BPEmb Python package xuất hiện vì dependency bắt buộc của Deepparse; không dùng nó để thay cấu hình FastText.

Các SHA-256 chính:

- Torch CPU wheel: `cb06175284673a581dd91fb1965662ae4ecaba6e5c357aa0ea7bb8b84b6b7eeb`.
- PhoBERT `pytorch_model.bin`: `a0b0f0912c710147fbaac015b0a4011216a0061a56c03b840b639e40d3bb49cc`, 542.923.308 bytes.
- VnCoreNLP jar: `9e2811cdbc2ddfc71d04be5dc36e185c88dcd1ad4d5d69e4ff2e1369dccf7793`.
- Java archive: `0b2b640e3046b64c8ec504de0ab9d91bb5610182bda21fad454681ce54d45a62`.
- Resource lock: `621cb1dbf3d09a37327bc5c6ad79584104a36eb2adb3c2e421532133a4b94322`.

File lists/revisions/license URLs/hash từng asset đều ở `resource_metadata/download_plan_v2.json`, `resource_download_manifest.json`, `resource_lock_local_v1.json`. Encoder/tokenizer dùng cùng thư mục để không nhân đôi weights. Wordsegmenter chỉ tải jar, RDR và `vi-vocab`; không tự tải POS/NER/dependency models.

`runtime_freeze.txt`, hai requirements có `--hash`, `pip_check.log` và inventories cho phép tái lập. `pip check` không có dependency conflict. Inventory resolver đầu tiên chưa hoàn chỉnh được giữ làm lịch sử; chỉ inventories `_v2.json` là hồ sơ trước cài hiện hành.

## 3. Deepparse — API thật đã qua, pretrained vẫn bị chặn

`neural_integration_v2/deepparse_api.json` xác minh signatures constructor, retrain, ListDatasetContainer và DataProcessor.process_for_inference từ package đã cài. Dataset container BIO24 tiny fixture thực sự tạo được; không load parser/checkpoint/embedding.

Default native tags được đọc từ package: StreetNumber, StreetName, Unit, Municipality, Province, PostalCode, Orientation, GeneralDelivery và EOS(index8). Tag mapping toàn cục đã có được gắn hash; không thay mapping theo mẫu. Kiểm EOS/early-EOS/token order/Unicode bằng test fixture; đó không phải output pretrained.

Trạng thái: `PACKAGE_API_PASS` và `PRETRAINED_INTEGRATION_BLOCKED_RESOURCE`. Máy WSL chỉ khoảng3,64GiB RAM total, available thấp hơn gate10GiB. License/resource evidence cho full embedding và weights chưa đủ. Không instantiate native parser để nó tự download, không tạo prediction giả.

## 4. PhoBERT — tokenizer/segmenter thật và supervised alignment QA

Quy trình:

1. Kiểm exact resource lock/hash; tất cả loaders dùng local-files-only/offline.
2. Serialize train/dev text-only trong thư mục integration mới. Processor chỉ nhận chuỗi, không nhận nhãn/hệ/nguồn.
3. Segmentation → BPE → mapping về raw character offsets → raw token pooling.
4. Lưu và hash `text_only_alignments.jsonl` trước khi gắn gold.
5. QA supervised riêng: encode BIO23/decode exact round-trip; không sửa raw, gold hoặc output alignment sau QA; giữ mask T1 manifest.

| Split | Tổng mẫu | Alignment exact | Từ chối | Gold span biểu diễn / tổng |
|---|---:|---:|---:|---:|
| Train | 240 | 217 | 23 | 952 / 1.057 |
| Dev | 60 | 54 | 6 | 257 / 284 |

**271/300 exact, 29 ca chưa biểu diễn được**. 132 span nằm trong những câu bị từ chối; đây là coverage của processor, không phải F1 hoặc FN của mô hình. Không loại29mẫu khỏi split đã khóa.

Nguyên nhân được trace: VnCoreNLP đổi vị trí dấu như `òa→oà`, `óa→oá`, `ùy→uỳ`. Raw stream và segmented stream không còn exact theo policy hiện hành; processor từ chối thay vì tạo offset bằng đoán. `alignment_coverage_and_review.json` có ID/split, chênh lệch và coverage từng nhãn. Không dùng accent folding/fuzzy để vá gold.

Đã sửa một lỗi NFD độc lập: normalize **input segmenter** thành NFC, giữ raw text và map qua original combining-cluster offsets. Smoke NFC, NFD, punctuation, tên lặp và underscore đều qua; câu dài bị reject `ENCODER_TOO_LONG`, không truncate. Có regression cho NFD nguyên bản và dấu không khôi phục được.

Trước training, cần một policy processor mới cho biến đổi vị trí dấu có ánh xạ ký tự được chứng minh và tests, hoặc cấu hình segmenter giữ literal. Phải ghi revision/code hash và kiểm lại300mẫu; không âm thầm bỏ mẫu hoặc đổi corpus để vượt cổng này.

## 5. Pretrained encoder forward và lỗi checkpoint được sửa

Một forward PhoBERT thật trên **câu tự soạn**, batch1, sequence7, CPU, `eval()` + `no_grad()` đã qua: tensor hữu hạn `[1,7,768]`. Evidence `neural_integration_v2/encoder_smoke.json`. Không backprop pretrained, không train, không sinh span prediction/dev metric.

Tiny random architecture tests riêng kiểm CRF partition/Viterbi/gradient, pooling, T1 mask và save/reload/resume. Torch thật phát hiện tên tạm `.checkpoint-*` bị zip writer từ chối. `save_checkpoint` nay dùng `checkpoint-*.pt.tmp`, vẫn ghi atomic và từ chối ghi đè; test lưu/nạp/resume/tamper và regression mock đã qua. Không sửa checkpoint/run frozen.

## 6. Cách chạy lại integration

```bash
cd /mnt/d/DACN
source data/interim/modeling/sprint03/task_01_06_20261003_v1/runtime_env.sh
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
"$TASK_PYTHON" -m scripts.37_verify_local_neural_integration \
  --resource-lock data/interim/modeling/sprint03/task_01_06_20261003_v1/resource_lock_local_v1.json \
  --output-dir data/interim/modeling/sprint03/local_neural_integration_next_version
```

Đầu ra phải là thư mục mới. Từ PowerShell, nếu gọi WSL cho lượt tiếp: dùng `wsl.exe --exec bash --noprofile --norc -c '…'` để tránh chương trình update-motd của login shell. Source env chỉ áp dụng cho process/task; không sửa dotfiles.

## 7. Dung lượng và cổng còn lại

Bảng byte/GB/GiB cuối, disk delta, kiểm module/cache và ngoại lệ log hệ thống nằm ở [nghiệm thu27](27_tasks_01_06_completion_20261003.md), evidence `install_accounting_v2.json`.

Các cổng chưa mở: 29case alignment; native FastText RAM/license/resource lock; disk budget training neural hiện hành20GiB; quyền train đang `TRAINING_DEFERRED_BY_USER`. Một forward CPU qua không có nghĩa mọi cổng training đã qua. Test100 vẫn do partner phụ trách, không được sử dụng trong các bước này.
