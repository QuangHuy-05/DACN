# Inventory thực nghiệm HEUR-JW, DP-ZS-FT và CRF-INDEP — 02/10/2026

Inventory này được ghi **trước cài đặt/tải model**. Chủ dự án cho phép các thành phần đã được kiểm kê trong yêu cầu thực hiện nhiệm vụ 1–4. Đây là lượt phát triển; 100 test vẫn `TEST_PENDING`.

## Môi trường ban đầu

- Windows host, WSL2 Ubuntu 26.04.1 LTS, kernel `6.6.87.2-microsoft-standard-WSL2`, x86_64, glibc 2.43.
- CPU Intel Core i7-12700H; WSL nhìn thấy 20 logical CPU.
- WSL RAM 3.64 GiB; khoảng 2.80 GiB available khi kiểm kê; swap 1 GiB.
- GPU NVIDIA GeForce RTX 3050 Laptop, 4 GiB VRAM; driver Windows 566.07, CUDA driver capability 12.7. Các run được phép chạy trong lượt này dùng CPU.
- Đĩa dự án còn khoảng 79.24 GiB; filesystem WSL còn khoảng 948 GiB theo `disk_usage` (giá trị filesystem ảo, không bảo đảm dung lượng vật lý Windows tương ứng).
- Runtime dự án hiện hữu: Python 3.14.4, pandas 2.3.3, numpy 2.5.3, osmium 4.3.1, pyarrow 23.0.1, tqdm 4.70.1, vietnamadminunits 1.0.4. Không có torch, transformers, deepparse, pycrfsuite.
- Runtime Python 3.11.16 hiện hữu dùng cho Label Studio; chưa có torch, transformers, deepparse, pycrfsuite. Không cài các gói thử nghiệm vào runtime này.
- Không thấy cache Deepparse/FastText/Hugging Face trong thư mục cache đã kiểm kê. Chưa tải weights/embedding.
- Sandbox thường từ chối `wsl.exe` với `E_ACCESSDENIED`; lệnh đọc WSL qua quyền thực thi đã được cấp chạy được.

## Inventory được phép cài trong lượt này

| Thành phần | Phiên bản / nguồn | Dung lượng | Mục đích | Giấy phép / quyết định |
| --- | --- | --- | --- | --- |
| Python virtual environment mới | Python 3.11.16 đã có; `python -m venv`, pip bootstrap đi kèm interpreter | dự phòng <50 MiB | Runtime WSL cô lập tại `data/interim/evaluation/sprint03/runtime_py311/`; không đổi Python toàn máy | Dùng interpreter hiện hữu; [Python license](https://docs.python.org/3/license.html). Không nâng pip hoặc package của env khác |
| python-crfsuite | **0.9.12**, [PyPI chính thức](https://pypi.org/project/python-crfsuite/0.9.12/), wheel CP311 manylinux x86_64 | tải 1,261,888 bytes; dự phòng 10 MiB sau cài | CRF-INDEP, linear-chain CRF/L-BFGS | MIT; không có dependency runtime trong metadata. SHA-256 wheel `5cd2b153bed935e4d6bd37d35f8cba9fcb73c01b539bbb63153589a10ac9fc6f`. Được cài với `--no-deps` |
| HEUR-JW | Python stdlib và gazetteer **s3_v2** đã có | không tải; dự phòng <200 MiB trace/run | Lookup/Jaro-Winkler/dev sweep/5 trường | Gazetteer giữ `PARTIAL_OLD_CODES_UNVERIFIED`; quyền dùng CSV nguồn bên ngoài chưa xác minh, không phát hành mã cũ như mã chuẩn |

Chỉ cài mục Python virtual environment và python-crfsuite nêu trên. HEUR-JW dùng stdlib. Bộ kiểm thử toàn repo chạy bằng runtime dự án hiện hữu có osmium/vietnamadminunits.

## Inventory ứng viên DP-ZS-FT — **chặn, không cài/tải**

- Package Deepparse **0.11.0**: metadata PyPI `Requires-Python >=3.10`, LGPLv3; wheel khoảng 234 KiB. [Metadata chính thức](https://pypi.org/project/deepparse/0.11.0/), [tài liệu](https://deepparse.org/parser.html).
- Các dependency chính được khai báo: numpy, torch, bpemb, scipy, gensim>=4.3.3, requests, pymagnitude-light, poutyne, pandas, urllib3, cloudpathlib[azure,gs,s3], transformers, huggingface_hub. Chưa resolve phiên bản chính xác vì cấu hình đã bị chặn trước cài. Các dependency này **không được cài trong lượt này**.
- `fasttext-wheel` là extra FastText; tài liệu chính thức cho biết native fastText chưa hỗ trợ Python 3.13+, Gensim fallback dùng nhiều RAM hơn. Python 3.11 là ứng viên phù hợp cho native FastText, nhưng vẫn không vượt qua cổng RAM.
- Checkpoint chính thức [deepparse/fasttext-base](https://huggingface.co/deepparse/fasttext-base): revision `908f403d0432a8e650da41e08d01bd33d77ac47f`, `model.safetensors` 38,589,364 bytes, SHA-256 `9cce032b1252c789ffaf7958f4d80d09c354f874095262259b397b5618c7691b`. Model card không khai báo trường license riêng ở revision kiểm kê; không suy LGPL của code thành license mọi pretrained resource.
- [Hướng dẫn chính thức Deepparse](https://deepparse.org/get_started/get_started.html) và [parser](https://deepparse.org/parser.html) ước tính FastText native khoảng **8 GB RAM**, Gensim khoảng **10 GB**. Embedding lớn và phần giải nén cần thêm dung lượng; chưa tải để đo.
- **Blocker `BLOCKED_INSUFFICIENT_RAM`**: 3.64 GiB RAM + 1 GiB swap của WSL thấp hơn yêu cầu nạp full FastText. VRAM 4 GiB không thay RAM host dùng cho embedding. Không đổi `.wslconfig`, tăng swap hoặc tải multi-GB để thử vượt cổng.
- **Blocker provenance/license**: model card chưa có license riêng cho weights/embedding; cần làm rõ khi mở lại bước tải. FastText Light/BPEmb không thay thế model ID `DP-ZS-FT` của lượt này.
- Adapter, mapping toàn cục và unit test alignment có thể hoàn thiện mà không cần cài/tải Deepparse. Các điểm số và latency mô hình thật phải ghi `NOT_RUN`, không dùng fixture làm kết quả thực nghiệm.

## Kết quả sau cài / chạy

Đã tạo runtime WSL cô lập Python **3.11.16**, pip **24.0**, setuptools **79.0.1** (bootstrap đi kèm interpreter). Đã cài đúng **python-crfsuite 0.9.12**, `--no-deps`; import thành công. Không cài/nâng package ở hai môi trường hiện hữu. File tái lập pin/hash: `configs/requirements_sprint3_crf.txt`.

HEUR-JW đã quét 6 ngưỡng dev và chạy 4.800 hàng benchmark được phép. CRF đã train 8 cấu hình bằng 240 mẫu, chọn bằng 60 dev, rồi chạy cùng 4.800 hàng. Cả hai dùng CPU, không tải embedding/checkpoint bên ngoài. Các run mới nằm trong `data/processed/evaluation/sprint03/`; runtime tạm nằm trong `data/interim/evaluation/sprint03/`.

DP-ZS-FT giữ `BLOCKED_INSUFFICIENT_RAM`, chưa cài Deepparse/Torch/Transformers hoặc tải weights. Model card thiếu license riêng vẫn là mục phải xác minh trước tải. Adapter/mapping có test fixture, chưa nghiệm thu integration với pretrained thực.

Lệnh CIM đọc RAM Windows host bị sandbox từ chối; không suy lượng RAM host từ giới hạn WSL. Để tiếp tục DP-ZS-FT, cần runtime có đủ RAM thực (dự phòng khoảng 10–12 GiB available cho full FastText) và xác minh quyền dùng pretrained resource. Không tăng bộ nhớ WSL tự động trong lượt này. [Báo cáo thực nghiệm](15_baseline_experiments_20261002.md) ghi metric, run/hash, kiểm thử và cách chạy lại.
