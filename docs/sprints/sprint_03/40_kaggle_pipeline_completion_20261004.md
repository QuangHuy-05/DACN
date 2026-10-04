# Nghiệm thu triển khai Kaggle — 04/10/2026

## Kết luận

**PIPELINE_IMPLEMENTED_REMOTE_GPU_BLOCKED**. Đã hiện thực mã, cài CLI, upload private và gửi hai lượt kiểm tra môi trường thật. Cả hai dừng trước cài neural vì runtime không có GPU. **Chưa có pretrained smoke PASS, checkpoint smoke, neural prediction/metric hoặc training đầy đủ.** Không gọi kết quả fixture là thực nghiệm pretrained.

## Kết quả từng phần

| Phần | Kết quả và bằng chứng |
| --- | --- |
| CLI local | Kaggle2.2.4+32dependency cài isolated trênD; `install_plan.json`, `install_inventory_resolved.json`, `requirements_kaggle_cli_locked.txt`, `install.log`, `installed_packages.txt` |
| Đăng nhập | API auth PASS, tài khoản huynq16; không ghi token/key vào bundle/report |
| Gói training | Tái dùng hai ZIP frozen, code overlay có manifest/hash, train240/dev60, resource PhoBERT/VnCoreNLP/Java cleared; không test100, raw exports, Gazetteer hoặc credential |
| Private dataset | Upload v1 và v2 PASS; v2 API `ready`. V1 là bản trước chốt guard, không submit; v2 là input đang dùng |
| Job script | `huynq16/dacn-s3-kaggle-smoke-20261004-v2/1`: API nhận, COMPLETE; report failed vì thiếu nvidia-smi, không vào neural bootstrap |
| Metadata server | Private/GPU/Internet=true, machine_shape=NvidiaTeslaT4; đây là cấu hình lưu, không chứng minh GPU thực cấp |
| Job notebook | `huynq16/dacn-s3-kaggle-notebook-smoke-20261004-v3/1`: API nhận, COMPLETE; `KAGGLE_GPU_NOT_AVAILABLE`, GPU=null, returncode127, `/dev/nvidia*` rỗng |
| Máy cloud đo được | Linux x86_64, kernelPython3.13.15,4CPU, MemTotal32.869.448kB, MemAvailable31.720.468kB, scratchfree1.148.819.505.152bytes; Python3.11 riêng chưa bootstrap do GPU gate |
| Quota API | GPU0used/30hremaining, TPU0used/20hremaining; refresh2026-10-10UTC. Không suy nguyên nhân thiếuGPU chỉ từ quota |
| Artifact download | Hai version1 tải về hai folder riêng, hash/runidentity PASS; report trạng thái thật failed, không biến COMPLETE thành SMOKE_PASS |
| Full training | Tắt mặc định, yêu cầu explicit flag và smoke thật đủ2model,300alignment,hash đồng nhất; mộtmodel/candidate/job, infer text-only rồi score dev riêng |
| Deepparse | Chưa đưa vào training GPU này; activecheckpoint/license/resource gate còn pending theo inventory33 |

## Kiểm thử và bảo toàn

- Bộ riêng Kaggle: **12/12 PASS**, `kaggle_unit_release.log`. Guard private, input whitelist train/dev, path escape, profile giữ optimizer/budget, full mặc định off, fixture không mở full, đổiidentity bị chặn, T1mask không xóaT0, downloadhash, APIexit0 khi pushrejected, notebookAST và reuseno reupload.
- Toànrepo WSL: **202tests =194PASS +8SKIP,0FAIL**, `full_regression_release.log`. SKIP do tài nguyên/integration trong runtime chính; không suy GPU integration PASS.
- Ledger: **550hash +4rawsize/mtime unchanged**,0changed/removed/sizechanged.138file mới đã có từ lượt prior; không phải sửa nội dung locked. `frozen_comparison.json`.
- Corpusmanifest: `9c91b77fa220e41b1b1067e5e99b216b7b4b2176181674b340f16dec134947bf`; resource lock: `621cb1dbf3d09a37327bc5c6ad79584104a36eb2adb3c2e421532133a4b94322`; Kaggleprofile: `4c085c1599cff80e972775369afc397a9818c7fa017fcb1c47ef64eda70d9b53`.
- Test100 không được đọc nội dung hoặc đưa vào training job; comparison ledger chỉ kiểm bytehash đã có theo policy, không mở nhãn. Task543 giữ toàn bộT0, T1eligible206/53 dùng maskmanifest. Raw/Gold/split/run/Gazetteer không sửa.

## Dung lượng cài trên D

Môi trường mới49.788.314bytes (**0,049788314GB /0,046368981GiB**). Lượt đo đầu tổng env+cache/evidence+hai gói thêm57.744.092bytes (**0,057744092GB /0,053778376GiB**). Tài nguyên420.749.036bytes dùng hardlink archive cũ nên phần ấy0byte bổ sung; không tải model local mới.

Bản đo cuối `kaggle_setup_20261004_v1/disk_install_report_final.json`: **57.826.066bytes =0,057826066GB /0,053854721GiB** cho env/cache/evidence/gói, làm tròn **0,058GB /0,054GiB**. Phương pháp: sizefile thực, bỏ symlinktarget, dedupinode/hardlink có từ trước; không phải blockallocation hoặc tổng dung lượng repository. Các report nhỏ có thể tăng sau khi chốt. Artifact download chỉ có báo cáo/log, chưa có weights; cloudpackage/model mới0byte vì gateGPU dừng trước install.

## Đường dẫn bàn giao

- Mã: `src/modeling/kaggle_handoff.py`, `src/modeling/kaggle_remote.py`, `scripts/50_kaggle_pipeline.py`, `scripts/51_run_kaggle_remote.py`, `scripts/52_measure_kaggle_install.py`.
- Bootstrap/profile: `notebooks/sprint03/kaggle_entry.py`, `configs/kaggle/sprint03/cuda128_profile_v1.json`.
- Gói input: `data/interim/modeling/sprint03/kaggle_pipeline_20261004_v2/`; notebookjob: `kaggle_notebook_smoke_20261004_v3/`.
- Evidence: `data/interim/modeling/sprint03/kaggle_setup_20261004_v1/`.
- Downloadscript: `data/interim/modeling/sprint03/kaggle_smoke_download_v2_version1/`.
- Downloadnotebook: `data/interim/modeling/sprint03/kaggle_notebook_download_v3_version1/`.
- Hướng dẫn từng thao tác/lệnh/gate: [39](39_kaggle_pipeline_operations.md); inventory trước cài [38](38_kaggle_install_inventory.md).

## Thao tác còn cần chủ dự án

1. Kiểm [Kaggle Settings](https://www.kaggle.com/settings) đã hoàn tất Phone verification hay chưa; chỉ thực hiện nếu UI yêu cầu. Không gửi OTP/token.
2. Mở [notebookjob](https://www.kaggle.com/code/huynq16/dacn-s3-kaggle-notebook-smoke-20261004-v3) → Edit → Settings → Accelerator, kiểm chọn được GPU T4x2 và Internet hay không; gửi trạng thái hoặc ảnh phần này.
3. Sau khi GPU thật sẵn sàng, agent tạo run mới qua `relaunch`, submit và fetch đúngversion. Chỉ khi smoke2model PASS và checkpoint/alignmenthash đạt mới mở jobfull c01/c02. Không cần gán lại300mẫu hoặc cung cấp tokenmới trong lúc API vẫn xác thực tốt.

Không khẳng định tài khoản chưa xác minh, hếtquota hoặc lỗiimage đã được chứng minh: hiện mới có evidence thiếuhardware; cần UI/account để phân biệt. Không tiếp tục gửi lặp job cùng điều kiện khi hai đường script/notebook đều thiếuGPU.

Đã kiểm thêm trình duyệt in-app: trang Settings chuyển sang đăng nhập, chưa có phiên web Kaggle. API legacycredential vẫn PASS; phiên web và phiênAPI khác nhau. Đã mở tab đăng nhập trả vềSettings để chủ dự án đăng nhập đúnghuynq16 và kiểmGPU. Agent không thể tự xác nhận Phoneverification từ phiên web chưa đăng nhập, không yêu cầu gửi mật khẩu/OTP/token quachat.

Lượt này đã cập nhật code/config/README/AGENTS/data_quality/docs local và upload Kaggle private; **chưa tạo commit/push GitHub mới** cho phần Kaggle. Artifactinterim/cache/resource không stage lênGit. Nhánh partner vẫn giữ nguyên.
