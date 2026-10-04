# Inventory trước khi chuẩn bị Kaggle — 04/10/2026

Chủ dự án đã yêu cầu chuyển gói train/dev sang pipeline Kaggle và chạy preflight + smoke trước training đầy đủ. Cho phép cài dependency cần thiết từ yêu cầu trước, chỉ trên D cho môi trường local. Không thay môi trường đang dùng, corpus, split hoặc run đã khóa; không upload/use test100 trong training.

## Local CLI

- Runtime mới riêng: `data/interim/modeling/sprint03/kaggle_runtime_d_v1/`, Python 3.11.16 đã có; không tải Python mới local.
- Package chính **kaggle==2.2.4**, nguồn [PyPI Kaggle](https://pypi.org/project/kaggle/2.2.4/), requires Python >=3.11, wheel chính 126.165 bytes. License **Apache-2.0** theo [upstream](https://github.com/Kaggle/kaggle-cli/blob/main/LICENSE.txt).
- Dependency được khai báo upstream: bleach, jupytext, kagglesdk>=0.1.35,<1, packaging, protobuf, python-dateutil, python-dotenv, python-slugify, requests, tqdm, urllib3; dependency bắc cầu chỉ từ resolution report PyPI. Chốt phiên bản/dung lượng toàn bộ trước khi cài, lưu `install_plan.json` và `install_inventory_resolved.json` trong evidence của lượt này. Không cài thành phần ngoài bản resolution đó.
- Ước tính tải/cache <=200 MB, environment <=1 GB; kiểm lượng thực sau cài. D còn khoảng 14,9 GB theo kiểm kê trước cài.
- Pip/temp/cache mới: `data/interim/modeling/sprint03/kaggle_setup_20261004_v1/cache/`. Không dùng Windows .venv hoặc cài toàn máy.
- Credential đã có được đọc cho subprocess xác thực, không in key/token, không đưa vào bundle/Git. Chỉ ghi kết quả xác thực và username.

## Kaggle runtime

- Giữ Python 3.11, Torch 2.8.0 CUDA 12.8 và package versions đã khóa; uv==0.8.22 để tạo môi trường cloud riêng. Nguồn uv/PyPI, Torch từ https://download.pytorch.org/whl/cu128, requirements và profile từ bundle đã khóa; package licenses giữ từ inventory 33. Cài cloud trong scratch/runtime Kaggle, không thuộc dung lượng cài local trên D.
- Tài nguyên có sẵn: PhoBERT/VnCoreNLP/Java và file legal/source/hash từ resource lock; tái dùng ZIP cũ 420.749.036 byte, không tải model mới local. Không bao gồm full FastText/Deepparse checkpoint chưa đủ quyền dùng.
- Upload **private**, gồm đúng train240/dev60, code/config đã kê và resource đã cleared; không có test, Label Studio export, dữ liệu nguồn/gazetteer chưa rõ quyền tái phân phối, cache hoặc credential.
- GPU, host RAM, disk và driver được đo lại trong notebook; nếu không đạt profile/gate, ghi blocker, không fallback CPU hoặc giảm gate. Smoke là một optimizer step/model + checkpoint round-trip, không phải kết quả thực nghiệm đủ epoch/F1.

Kết quả cài, package thực đo và trạng thái cloud sẽ được bổ sung sau khi chạy. Chưa giả định tài khoản có GPU hoặc quota khi chưa có evidence.

## Kết quả thực hiện

Đã cài thành công **kaggle2.2.4 và32 dependency** vào environment riêng trênD, pin theo report resolution và `--require-hashes`. `installed_packages.txt` giữ33 version thực tế, `install.log` giữ kết quả cài. Environment49.788.314bytes; cache/evidence đo lượt đầu6.976.617bytes. Tổng local gồm gói/code/evidence khoảng **0,058GB / 0,054GiB**; [báo cáo40](40_kaggle_pipeline_completion_20261004.md) ghi bản đo cuối. Resource420.749.036bytes đã có được dùng hardlink; không tải model mới local.

API auth/upload private PASS. Hai job script/notebook đã chạy preflight phần cứng nhưng đều chưa cóGPU, nên cloud neural cài mới0bytes, pretrained smoke/training chưa thực hiện. Quota đọc được30hGPU còn trống; không suy tài khoản đã được mở quyềnGPU chỉ từ quota. [Thao tác kiểmGPU và chạy lại](39_kaggle_pipeline_operations.md).
