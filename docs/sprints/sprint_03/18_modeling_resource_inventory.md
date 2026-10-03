# Inventory U1–U7 — 02/10/2026

**Không cài package, tải model/embedding/segmenter hoặc thay WSL/Python toàn máy trong lượt này.** Các thành phần dưới đây là profile dự kiến cần được cho phép riêng. Quyền cài python-crfsuite của lượt trước không mở rộng sang neural.

## Môi trường quan sát thực

Log JSON: `data/interim/modeling/sprint03/seven_priorities_20261002_v1/verification/runtime_main.json` và `runtime_py311.json`.

- WSL Ubuntu26.04.1, kernel6.6.87.2, glibc2.43; CPU20 logical. Main env Python**3.14.4**, numpy2.5.3, pandas2.3.3, osmium4.3.1, pyarrow23.0.1, vietnamadminunits1.0.4.
- Runtime CRF cô lập hiện có: Python**3.11.16**, python-crfsuite0.9.12; không Torch/Transformers/Deepparse/Poutyne/VnCoreNLP/NumPy. Main env cũng thiếu các package neural.
- WSL RAM khoảng**3,64GiB**, swap1GiB; Java không tìm thấy. GPU từ inventory trước: RTX3050 Laptop4GiB; lượt này không xác minh neural/CUDA bằng Torch.
- Đĩa D còn khoảng**13,65GB ≈12,71GiB**, thay đổi theo thời điểm. Profile PhoBERT dự phòng20GiB/run sau khi có resource; preflight hiện báo thiếu đĩa. Full FastText cần RAM lớn hơn hiện có.
- Python3.14 vẫn chạy được core/tests hiện hữu. Profile neural khóa Python**3.11**; không cài package tương thích khác vào main env để vượt cổng.

## Package dự kiến, không phải đã cài

| Package / nguồn | Pin | License được khai báo | Ước lượng đĩa / mục đích |
| --- | --- | --- | --- |
| [PyTorch](https://pypi.org/project/torch/2.8.0/) | 2.8.0; CPU/CUDA build ghi đúng khi cài | BSD3, theo metadata dự án | CPU stack khoảng0,5–1,5GB; CUDA stack có thể4–8GB gồm dependency; cả ba neural pipeline |
| [Transformers](https://pypi.org/project/transformers/4.57.1/) | 4.57.1 | Apache2 | khoảng0,2–0,5GB cùng tokenizer/HF deps; PhoBERT |
| [Deepparse](https://pypi.org/project/deepparse/0.11.0/) | 0.11.0 | LGPLv3 code | package nhỏ, transitive khác cần inventory thực khi resolver có quyền; DP-FT-FT |
| [Poutyne](https://pypi.org/project/Poutyne/1.17.4/) | 1.17.4 | LGPLv3 | <50MB riêng package; native retrain callback |
| [py-vncorenlp](https://pypi.org/project/py-vncorenlp/0.1.4/) | 0.1.4 | wrapper theo nguồn package; assets kiểm riêng | wrapper/pyjnius cần kiểm resolution; PhoBERT segmentation |
| Java local runtime | Temurin/OpenJDK17 LTS, exact build còn pending | GPL2 + Classpath exception theo distribution | khoảng0,2–0,4GB; [Temurin releases](https://adoptium.net/temurin/releases/); không thay Java toàn máy |

Ước lượng không thay package-lock/resolution thực. Transitive packages/chính xác wheel hash chưa được resolve/download; chưa có quyền tự cài. Khi được mở cổng, phải lập inventory bổ sung trước cài những thành phần chưa liệt kê, ưu tiên runtime3.11 cô lập. Không tự nâng dependency env hiện hữu.

## Model/embedding/segmenter

| Tài nguyên | Nguồn / revision | Dung lượng ước tính / license / trạng thái |
| --- | --- | --- |
| Deepparse fasttext-base | [HF chính thức](https://huggingface.co/deepparse/fasttext-base), revision tham chiếu `908f403d0432a8e650da41e08d01bd33d77ac47f` | model.safetensors38.589.364bytes, SHA tham chiếu `9cce032b1252c789ffaf7958f4d80d09c354f874095262259b397b5618c7691b`; **chưa có file local để xác minh**, loader/cache format integration pending; weights license chưa được xác minh riêng |
| FastText **full** | [Deepparse resource guide](https://deepparse.org/get_started/get_started.html) | embedding khoảng6,8GB; native loader RAM~8GB, fallback gensim~10GB; preflight bảo thủ yêu cầu10GiB available. Nguồn embedding/revision/hash/điều kiện dùng riêng **PENDING**, không kế thừa LGPL code |
| PhoBERT-base | [VinAI repo](https://github.com/VinAIResearch/PhoBERT), [HF model](https://huggingface.co/vinai/phobert-base) | khoảng135M tham số, encoder weights~0,54GB FP32; MIT theo nguồn VinAI/model card. Exact full revision/file hashes **PENDING**; chưa tải, không ghi placeholder thành verified hash |
| VnCoreNLP wseg | [Repo chính thức](https://github.com/vncorenlp/VnCoreNLP), chọn jar1.2 + wordsegmenter assets sau khi kiểm | khoảng0,1–0,3GB, exact revision/hash pending. [LICENSE](https://github.com/vncorenlp/VnCoreNLP/blob/master/LICENSE.md) GPL3-or-later; quyền/model assets cần lưu theo bản thực tải, khác PhoBERT MIT |

Không đổi FastText full thành light/BPEmb dưới ID DP-FT-FT. Không tải model để làm test hết skip. Torch chưa có nên forward/backward, CRF tensor, optimizer resume và tokenizer/segmenter thật vẫn **INTEGRATION_PENDING_RESOURCE**.

## Resource lock và API gate

Hai template JSON tại `configs/modeling/sprint03/*resource_lock_template.json` có `revision=null`, `license_status=PENDING`, `files={}`: preflight phải từ chối chúng. Lock thực ghi family, từng component/path tương đối project, full revision, license CLEARED và SHA-256 **mọi file local**; từ chối file thiếu, thay hash, file không khai báo hoặc dùng annotation/address data làm model resource.

DP base checkpoint và full embedding dùng cùng offline cache đã khai báo. Constructor/retrain/container signature được kiểm trước chạy; constructor đúng là `path_to_retrained_model` trong source đọc được. Native loader bị khóa network nếu cache thiếu. PhoBERT dùng `local_files_only=True`; segmenter chỉ dùng local assets, khôi phục cwd của caller.

Preflight không import neural model, tải tài nguyên hoặc train; ghi package phiên bản thực, Python, disk/RAM và blocker. Chỉ profile đúng, tài nguyên được pin/hash/license rõ và integration thật đã qua mới được mở giai đoạn training. Thời gian huấn luyện/GPU-hour chưa đo, không có số thực nghiệm neural mới.
