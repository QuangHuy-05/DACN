# Inventory local L1–L5 — 04/10/2026

## Quyết định trước cài/tải

Tái dùng runtime hiện có; **không cài package, tải model hoặc đổi môi trường** trong lượt này. Cài mới/cache/weights mới dự kiến và thực tế: 0 bytes. ZIP, thư mục kiểm gói, logs và evidence là artifact riêng, không tính là cài đặt.

| Tài nguyên tái dùng trên D | Phiên bản/nguồn | Điều kiện sử dụng | Vai trò |
| --- | --- | --- | --- |
| `runtime_neural_d_v1` | Python3.11.16, Torch2.8.0+cpu, Transformers4.57.1, Deepparse0.11.0, Poutyne1.17.4, py-vncorenlp0.1.4; PyPI/PyTorch, inventory23/26/33 | Giấy phép package theo inventory đã lưu; không suy license weights từ package | Kiểm thử logic neural/CRF tiny fixture |
| `runtime_py311` | Python3.11.16, python-crfsuite0.9.12 | MIT python-crfsuite | Hồi quy CRF, không train baseline mới |
| PhoBERT | `vinai/phobert-base`, revision `01daacda68afe13d83023d16ec647239e344a1e6` | MIT; giữ LICENSE trong resource ZIP | Encoder/tokenizer cho giai đoạn Colab sau |
| VnCoreNLP | commit `62bbc58fe5d113c898eae112656be97dcf50b3a0` | GPL-3.0-or-later; giữ legal/source metadata | Word segmentation và alignment |
| Temurin JRE | 17.0.20.1+1 | GPL cùng Classpath Exception; giữ legal files | Java cho segmenter |

Các vị trí trên D: `data/interim/modeling/sprint03/{runtime_neural_d_v1,resources_d_v1,kaggle_runtime_d_v1}` và `data/interim/evaluation/sprint03/runtime_py311`. Resource lock thật: `task_01_06_20261003_v1/resource_lock_local_v1.json`; kiểm từng file trước đóng ZIP. Không sửa lock này.

## Rà upstream và cổng Deepparse

Ngày truy cập 04/10/2026. [FastText upstream](https://fasttext.cc/docs/en/crawl-vectors.html) ghi vectors Common Crawl có license CC-BY-SA3.0. Native Deepparse cần full `cc.fr.300.bin`, không thay bằng vector Việt/rút gọn. RAM host tối thiểu10GiB, local WSL khoảng3.64GiB chưa đạt. Hash embedding còn pending vì chưa tải; không cấp active lock.

Checkpoint dự kiến: `deepparse/fasttext-base`, revision `908f403d0432a8e650da41e08d01bd33d77ac47f`. [Model card tại revision](https://huggingface.co/deepparse/fasttext-base/blob/908f403d0432a8e650da41e08d01bd33d77ac47f/README.md) chưa truy xuất được qua web tool trong lượt này; không có bằng chứng mới giải quyết license weights. Giữ `DP_RESOURCE_BLOCKED`; MIT repo code không tự cấp quyền cho pretrained checkpoint. Không tải checkpoint/embedding nhiều GB khi cổng nguồn/terms và RAM chưa qua.

[PhoBERT upstream LICENSE](https://github.com/VinAIResearch/PhoBERT/blob/master/LICENSE) đã đối chiếu MIT; resource lock local giữ revision/hash đã tải. VnCoreNLP/JRE dùng evidence và legal files thực trong lock, không suy từ trang license chung.

## Ngân sách giai đoạn sau

Colab profile: Python3.11/Torch2.8 CUDA12.8, float32, AMP tắt, GPU>=8GiB VRAM, đĩa>=20GiB mỗi lượt. Giữ batch hiệu dụng16, seed42, hai candidate c01/c02, epochs<=20 và patience5. Package cài ở Colab chỉ khi người chạy mở notebook; lượt local này không bootstrap hoặc gọi cloud.

RAM/disk/hashes thực tại đầu lượt và dung lượng artifact cuối được lưu ở `data/interim/modeling/sprint03/local_finish_before_colab_20261004_v2/p0/` và báo cáo46. Các dữ liệu gazetteer/nguồn có điều kiện phân phối chưa rõ giữ local, không nằm trong resource/training ZIP hoặc Git commit mới.
