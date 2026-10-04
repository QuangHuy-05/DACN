# Pipeline Kaggle riêng cho train/dev Sprint 3

Ngày triển khai: 04/10/2026. Mục tiêu: kiểm GPU/runtime, chạy smoke pretrained rồi mới cho phép các job training đầy đủ. Corpus vẫn **240 train / 60 dev**, không chứa test100. Kho mã local đã có pipeline; trạng thái thực nghiệm phải đọc báo cáo job, không suy từ việc push thành công.

**Cập nhật 05/10:** GPU smoke thật đã đạt và các job full train/dev đã được mở; xem [báo cáo47](47_test_gold_release_and_kaggle_20261005.md). Các trạng thái không có GPU ở mục2 là lịch sử. Fetch hiện dùng script60 tải từng chunk và pin SDK `version_label=v1`, không dùng đường tải buffer của CLI2.2.4.

## 1. Những thành phần đã hiện thực

- `scripts/50_kaggle_pipeline.py`: prepare, xác thực, kiểm quota, upload private, submit, status, inspect và fetch có kiểm hash. Secret chỉ vào môi trường subprocess, không vào bundle hoặc báo cáo. API rejection bị coi là lỗi cả khi Kaggle CLI trả exit 0.
- `notebooks/sprint03/kaggle_entry.py`: bootstrap độc lập, kiểm GPU/đĩa trước cài cloud, kiểm SHA-256 archive và từng file, từ chối đường ZIP nguy hiểm/symlink. Trường hợp Kaggle giải nén tự động phải khớp manifest đã pin.
- `configs/kaggle/sprint03/cuda128_profile_v1.json`: overlay riêng, Python3.11/Torch2.8 CUDA12.8, float32, AMP=false, VRAM>=8GiB. Giữ seed, optimizer, c01/c02 và split/protocol đã khóa.
- `scripts/51_run_kaggle_remote.py`, `src/modeling/kaggle_remote.py`: preflight từng model, kiểm alignment đủ 300 mẫu, optimizer step và checkpoint round-trip pretrained thật cho PhoBERT-CRF và PROPOSED-DYN. Full job chỉ chạy **một model/một candidate** để giữ ngân sách output.
- `scripts/52_measure_kaggle_install.py`: đo package/cache local; phân biệt hardlink tài nguyên cũ và byte mới.

Gói ban đầu tái dùng code/resource ZIP Colab frozen rồi bổ sung có kiểm hash. Không sửa notebook/ZIP Colab cũ. Bước alignment Kaggle dùng trực tiếp corpus approved; không gọi `prepare_data()` vốn còn phụ thuộc queue/trace gán nhãn trung gian không có trong gói.

## 2. Trạng thái đã đo

- Xác thực API tài khoản `huynq16`: PASS. Private dataset v2 được tạo và API báo `ready`.
- Job script `huynq16/dacn-s3-kaggle-smoke-20261004-v2`, version1: API nhận; status `COMPLETE`, nhưng artifact **`REMOTE_BLOCKED_OR_FAILED`** vì không có `nvidia-smi`. Chưa cài runtime neural cloud, chưa forward/backward, chưa sinh checkpoint hoặc metric.
- Metadata kéo từ server xác nhận `is_private=true`, `enable_gpu=true`, `enable_internet=true`, `machine_shape=NvidiaTeslaT4`; vẫn chưa chứng minh phần cứng được cấp.
- Quota tại lúc kiểm: GPU **0.00h used / 30.00h remaining**. Nguyên nhân không có GPU chưa xác định chỉ từ API; cần kiểm quyền GPU/xác minh tài khoản hoặc đường cấp image của Kaggle.
- Notebook v3/version1 cũng đã chạy đến cổng môi trường rồi dừng: không có `nvidia-smi` và `device_nodes=[]`, host RAM khoảng31GiB, Python kernel3.13.15. Chưa bước vào bootstrap Python3.11 hoặc cài neural. Artifact đã tải về và kiểm hash PASS. Xem [báo cáo nghiệm thu40](40_kaggle_pipeline_completion_20261004.md).
- Full training **DISABLED**, Deepparse chưa đưa vào do checkpoint/license active lock còn pending. Không gọi smoke là kết quả đủ epoch hay F1 benchmark.

Evidence local: `data/interim/modeling/sprint03/kaggle_setup_20261004_v1/`. Artifact version1 script: `data/interim/modeling/sprint03/kaggle_smoke_download_v2_version1/`, `download_verification.json` đã xác minh hash.

Artifact notebook version1: `data/interim/modeling/sprint03/kaggle_notebook_download_v3_version1/`. Không submit lặp các gói hiện hành để ghi đè run; sau khi quyền GPU sẵn sàng, tạo job mới với `relaunch --source-package .../kaggle_pipeline_20261004_v2 --package-dir .../NEW_PACKAGE --run-id NEW_RUN_ID`, rồi submit/status/fetch đúng version.

## 3. Mở job và kiểm quyền GPU

Mở [job script](https://www.kaggle.com/code/huynq16/dacn-s3-kaggle-smoke-20261004-v2) hoặc [job notebook thử tiếp](https://www.kaggle.com/code/huynq16/dacn-s3-kaggle-notebook-smoke-20261004-v3), đăng nhập đúng tài khoản. Trong Edit → Settings:

1. Kiểm tra Accelerator có chọn được **GPU T4 x2** hay không.
2. Nếu giao diện yêu cầu xác minh, hoàn tất trực tiếp tại [Kaggle Settings](https://www.kaggle.com/settings). Không gửi OTP/token cho agent.
3. Kiểm tra Internet có bật được không; bootstrap cần tải dependency công khai, weights đã ở input private.
4. Gửi trạng thái hoặc ảnh phần Accelerator. Không tự bật full training để thử vượt cổng.

Đây là kiểm tra tài khoản, không phải yêu cầu gán lại dữ liệu. Agent đã có phiên API hợp lệ, không cần cung cấp token mới nếu không có lỗi xác thực.

## 4. Lệnh thao tác WSL

Giữ cache/temp ở D bằng environment của dự án. Không dùng `.venv` Windows hoặc cài lại Torch trên local.

```bash
cd /mnt/d/DACN
source data/interim/modeling/sprint03/task_01_06_20261003_v1/runtime_env.sh
PY=data/interim/modeling/sprint03/kaggle_runtime_d_v1/bin/python
CREDS=/mnt/c/Users/quang/.kaggle/kaggle.json
PACKAGE=data/interim/modeling/sprint03/kaggle_notebook_smoke_20261004_v3

$PY -m scripts.50_kaggle_pipeline quota --credentials "$CREDS"
$PY -m scripts.50_kaggle_pipeline status --package-dir "$PACKAGE" \
  --kernel-ref huynq16/dacn-s3-kaggle-notebook-smoke-20261004-v3/1 --credentials "$CREDS"
```

Khi job kết thúc, tải đúng version vào thư mục **mới**:

```bash
$PY -m scripts.50_kaggle_pipeline fetch --package-dir "$PACKAGE" \
  --kernel-ref huynq16/dacn-s3-kaggle-notebook-smoke-20261004-v3/1 \
  --output-dir data/interim/modeling/sprint03/kaggle_notebook_download_v3_version1 \
  --credentials "$CREDS"
```

Lệnh fetch từ chối ghi đè. Nếu phiên bản này đã được agent tải, đọc thư mục đó; không chạy lặp. Fetch50/60 pin version qua SDK (`1` → `v1`), kiểm identity/hash. CLI2.2.4 có lỗi bỏ qua version ở đường status/output; status chỉ dùng chẩn đoán latest, không chứng minh version cũ. Các job mới dùng slug riêng và duy nhất version1. `inspect` cũng đọc metadata latest.

Với output đầy đủ nhiều checkpoint, có thể thêm `--artifact-profile selection`: tải mọi báo cáo/sidecar và trọng số `best.pt`/`last.pt`; checkpoint epoch khác giữ trên remote, danh sách/hash khai báo trong report. Trạng thái `SELECTED_ARTIFACTS_HASH_VERIFIED` chỉ xác minh phần đã tải, không tuyên bố toàn output được xác minh local. Mặc định `all` vẫn yêu cầu đủ từng file/hash. Chọn profile trước khi tải vào thư mục mới.

Nếu đã tải một phần vào thư mục khác, thêm `--reuse-dir THU_MUC_CU`: manifest luôn tải mới theo version; chỉ tái sử dụng file có SHA khớp index mới bằng hardlink trên D. Không đổi hoặc xóa bản cũ, không dùng `.download.part`. Report tách byte chuyển qua mạng, byte tái dùng và byte logical resident.

## 5. Điều kiện smoke đạt

Phải có đồng thời:

1. GPU thật được đo, Torch CUDA khả dụng, RAM/đĩa và resource/package preflight đạt.
2. Alignment **240/240 train + 60/60 dev EXACT**, giữ 1.341 span; T1 mask theo manifest, giữ T0 task543. Không bỏ mẫu lỗi để báo PASS.
3. Cả PhoBERT-CRF và PROPOSED-DYN có finite loss, backward và một optimizer step thay đổi trọng số.
4. Checkpoint lưu atomically cùng optimizer/scheduler/RNG, hash đúng, reload cho emissions khớp; report ghi `PRETRAINED_OPTIMIZER_CHECKPOINT_PASS`.
5. `smoke_report.json` = **`SMOKE_PASS`**, identity khớp corpus/lock/profile/protocol/code; output tải về kiểm hash PASS.

`COMPLETE` phía Kaggle chỉ nghĩa tiến trình đã kết thúc; report `REMOTE_BLOCKED_OR_FAILED` hoặc `BLOCKED_PREFLIGHT` không mở training. Fixture unit tests không thay thế các điều kiện trên.

## 6. Mở full training sau smoke — chưa chạy ở lượt này

Mỗi c01/c02 và mỗi model dùng job mới; chạy tuần tự, giữ ngân sách output. Chuẩn bị gói full chỉ khi đã có smoke đạt:

```bash
$PY -m scripts.50_kaggle_pipeline prepare --username huynq16 \
  --package-dir data/interim/modeling/sprint03/kaggle_full_phobert_c01_run001 \
  --run-id dacn-s3-kaggle-phobert-c01-run001 --mode full --model PHOBERT-CRF --candidate c01 \
  --allow-full-training --smoke-evidence PATH_TO_VERIFIED_SMOKE_REPORT
```

Sau đó upload/status dataset/submit với `--allow-full-training`. Nếu chưa có smoke đạt, prepare bị chặn. Full job khởi tạo lại pretrained base; **không dùng trọng số smoke để chọn mô hình**.

Full pipeline train đúng 240; chọn checkpoint/candidate bằng dev60 theo protocol. Infer nhận `sample_id/text`, lưu prediction trước score đọc gold. PROPOSED-DYN calibrate trên dev rồi chạy constraint on/off cùng checkpoint. Không đưa test100 vào job hoặc dùng nhãn test chọn config. Checkpoint/prediction/metrics/config/manifest và hash được backup định kỳ, tải về giữ nguyên path workspace để tái lập.

## 7. Ngân sách và cài đặt

Local: môi trường Kaggle2.2.4 + 32 dependency mới, tất cả ở D. Danh sách pin đầy đủ: `kaggle_setup_20261004_v1/installed_packages.txt`; inventory trước cài: [38](38_kaggle_install_inventory.md).

Đo lượt đầu: environment **49.788.314 bytes**, cache/evidence **6.976.617 bytes**, hai gói mới thêm **979.161 bytes**; resource420.749.036bytes dùng hardlink file cũ nên không tính thêm hai lần. Tổng **57.744.092 bytes = 0,057744092 GB = 0,053778376 GiB**. Đây là byte file mới thực đo, không phải block allocation hoặc dung lượng weights mới; bản đo cuối bổ sung sau chẩn đoán/đồng bộ báo cáo.

Cloud bootstrap/runtime ở scratch; chỉ report/checkpoint/artifact trong `/kaggle/working`, giới hạn riêng19GiB trong pipeline. Mọi file được kiểm hash khi copy. Cài cloud nếu diễn ra sẽ có `cloud_install_inventory.json`, `cloud_packages.txt`, `cloud_install_sizes.json`; không cộng nhầm cloud vào GB cài local.

Theo [Kaggle metadata chính thức](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels_metadata.md), GPU/private/input sources phải khai báo; theo [CLI kernels](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels.md), push/status/output là các thao tác tương ứng. Tài nguyên/license PhoBERT/VnCoreNLP/Java giữ từ [inventory33](33_pre_colab_resource_inventory.md). Trạng thái GPU thực tế luôn dựa artifact của job.
