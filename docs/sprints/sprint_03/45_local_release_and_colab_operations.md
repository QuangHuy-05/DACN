# Thao tác local và Colab giai đoạn cuối

## 1. Trạng thái bàn giao

Evidence hiện hành: `data/interim/modeling/sprint03/local_finish_before_colab_20261004_v2/` (viết tắt `EVIDENCE` trong tài liệu). Artifact trong interim giữ local và phải nhận riêng; clone Git không có ZIP/resources/raw export/test gold.

Round2 có100 task/103 annotation, không thiếu mẫu. Hai cặp602/653 tương đương được chọn bằng fingerprint; task695 còn hai bản khác cờ. QA hiện tại chuyển99 task, không có lỗi offset/label/system/overlap; chưa duyệt gold. Chủ dự án yêu cầu giữ raw nguyên trạng; không cần gán lại300 train/dev.

Chỉ còn phán quyết người cần chốt trước release:

- Task695 chọn annotation694 (giữ temporal_ambiguity) hoặc695 (không cờ).
- Với16 ca T1 được liệt kê trong `owner_adjudication_pending.json`, chọn giữ raw và khai báo ngoại lệ/mask T1, hoặc cung cấp căn cứ thời kỳ. Agent chưa áp mask mới khi chưa nhận xác nhận. Task663 có xung đột với snapshot hành chính theo tên+cha; task664 thiếu thành phần hệ mới;14 ca còn lại chưa có căn cứ T1 trong annotation.

Các flag có thể giữ; quyết định phải ghi lý do, reviewer và đúng annotation fingerprint. Không dùng Submit/lead_time hoặc note gợi ý chưa sửa làm chứng cứ người chưa review. Reviewer dùng tài khoản đã được xác nhận trong hồ sơ trước; account ID đơn lẻ không tạo ra tên người.

## 2. Tái lập QA hiện tại

WSL dùng runtime đang có; không cài lại. Tại `/mnt/d/DACN`:

```bash
PYTHONDONTWRITEBYTECODE=1 ~/.venv_dacn/bin/python -m scripts.53_qa_test100_annotation \
  --export data/interim/annotation/sprint03/exports/test_assisted_v1/test100_assisted_round2.json \
  --assisted-manifest data/interim/annotation/sprint03/test100_assisted_v1/manifest.json \
  --adjudication-map data/interim/modeling/sprint03/local_finish_before_colab_20261004_v2/equivalent_annotation_selection.json \
  --output-dir data/interim/modeling/sprint03/local_finish_before_colab_20261004_v2/test_qa_replay_NEW
```

`NEW` là thư mục chưa tồn tại. Với map hiện tại, exit1 là đúng: task695 chưa chọn; không phải lỗi dữ liệu bị mất. Bản đã chạy: `test_qa_equivalent_selection/`, hash export `d51b69c981e775e0e51ac3ed5a3ef4c91d845f5e7a900c2f3d4c79f98ca758a4`.

Sau khi owner chốt, agent tạo map cuối, QA vòng mới100/100, decision/attestation gắn các hash export/canonical/queue/hold/XML/guideline/assisted/map/manual findings. Không tái dùng biên bản300 mẫu để duyệt100 test.

## 3. Publisher

Script54 có `prepare` tạo candidate và `publish` phát hành bất biến. Thiếu approval, có canonical khác raw, hash cũ, ID/text/group thay đổi hoặc near-duplicate chưa xử lý đều chặn. Tái dùng138 quyết định chỉ khi text/split/cặp không đổi. Audit source identity hiện tại đạt PASS cho240/60/100ID, chưa phải approval nhãn.

Ví dụ dưới đây **chỉ dùng sau khi agent đã tạo các hồ sơ cuối có thật**:

```bash
python -m scripts.54_publish_test_corpus publish \
  --qa-dir data/interim/modeling/sprint03/local_finish_before_colab_20261004_v2/test_qa_final \
  --selection data/interim/modeling/sprint03/local_finish_before_colab_20261004_v2/annotation_selection_final.json \
  --manual-findings data/interim/modeling/sprint03/local_finish_before_colab_20261004_v2/manual_content_review.json \
  --approval data/interim/modeling/sprint03/local_finish_before_colab_20261004_v2/test_approval_final.json \
  --review-decisions data/interim/modeling/sprint03/local_finish_before_colab_20261004_v2/test_review_decisions_final.json \
  --test-output-dir data/processed/annotation/sprint03/test_gold_v1 \
  --output-dir data/processed/annotation/sprint03/corpus_v1
```

Các path `*_final`/release trên chưa tồn tại nếu còn pending; không tự tạo JSON `approved`. Nếu tên release đã tồn tại, dùng version mới. Manifest tổng liên kết test release riêng và manifest train/dev nguồn; giữ bytes train/dev và giữ T0 của543. Mask T1 mới chỉ theo quyết định đã duyệt; không sửa nhãn raw. Mode test là AI-assisted human review, IAA NOT_MEASURED.

## 4. Bộ chạy test cuối

- Script55 `lock`: chỉ đọc các dev run hoàn tất; verify output/resources/code và chọn theo protocol. Neural bắt buộc đủ c01/c02; proposed chọn từ dev unconstrained.
- Script55 `preflight`: chỉ đọc manifest/input text-only/config/lock, không mở gold hoặc nạp adapter.
- Script55 `infer`: yêu cầu `--execute-final-test`, thư mục mới và lock thực.
- Script56: scorer riêng, cũng cần `--execute-final-test`; chỉ mở gold sau prediction freeze. Không gọi trong lượt local này.

Hai light-model locks cuối tại `EVIDENCE/final_selection_v2/`, dùng dev đã frozen, không chạy lại baseline. Các lock đầu tại `final_selection/` là lịch sử trước khi hoàn tất code; không dùng cho test. Neural/DP locks vẫn PENDING_DEV_SELECTION, checkpoint hash=null. Stability seeds NOT_EXECUTED.

T0 tính đủ11 nhãn; unsupported gold vẫn FN; subset và coverage báo thêm. T1 mask theo manifest/null, `khong_ro` là abstain. Adapter không có T1 báo NOT_IMPLEMENTED. Hallucination Quận: mẫu số là gold T1moi đủ điều kiện và không có QuanHuyen; mẫu số0 ghi null. Latency có phạm vi/hardware, không so CPU/GPU như cùng điều kiện. Bảng5 trường giữ track riêng theo model_matrix, không gộp thành T0.

## 5. Gói Colab hiện hành và lần chạy cuối

Gói đã kiểm local: `EVIDENCE/handoff_v3/`. Dùng `handoff_manifest.json` để đối chiếu SHA của:

1. `dacn_train_dev_bundle_v3.zip`: train240/dev60, code/config, trace300 và queue232; không có test/raw export/cache.
2. `dacn_phobert_resources_v3.zip`: PhoBERT/VnCoreNLP/Java và legal files thật. Symlink legal được dereference; ZIP không chứa symlink.
3. Notebook `notebooks/sprint03/local_ready_train_dev_v3.ipynb`.

Gói v2 là build thất bại trước khi xử lý legal symlink, không dùng. Gói cũ và notebook cũ giữ nguyên.

Thao tác Colab cho lượt kế tiếp:

1. Chọn runtime GPU; upload hai ZIP với đúng tên. Mở notebook train/dev v3.
2. Giữ `ENABLE_NEURAL_TRAINING=False`. Chạy cell verify ZIP/hash/extract, kiểm GPU/RAM/disk, rồi bootstrap Python3.11/profile đã pin trong Colab. Local chưa thực thi các cell này.
3. Chạy CPU preparation và GPU preflight/alignment. Gói đã kiểm CPU closure local; bằng chứng PhoBERT thật300/300 trước đó vẫn còn. Không coi raw processor là smoke pretrained.
4. Bật `ENABLE_PRETRAINED_GPU_SMOKE=True`; chạy một optimizer step cho PhoBERT-CRF và proposed trên train subset. Cần SMOKE_PASS cả2model, CUDA, alignment300, checkpoint/optimizer/RNG reload. Smoke weights không dùng chọn model hoặc resume full training.
5. Cấp quyền/mount Drive bằng thao tác của người chạy nếu dùng. Điền `BACKUP_DIRECTORY` là thư mục bền vững; `/content/drive` phải là mount thực, hoặc dùng nơi lưu ngoài `/content`. Không dùng thư mục tạm để gọi là backup.
6. Chỉ khi smoke/resources/hardware/backup qua cổng mới bật full training. Notebook chạy riêng c01/c02 cho2model, giữ seed42/batch16/budget. Best/last có optimizer/scheduler/RNG, backup300s và checksum cuối. Resume dùng script58 `train --resume-from <last.pt>` vào run mới, cùng candidate/profile/resources.
7. Chọn best bằng dev60. Proposed calibration dùng grid đã khóa trên checkpoint được chọn; on/off cùng checkpoint. Script58 `select` tạo final_model_config/selection_lock và ablation config/lock, không đọc test.
8. DP-ZS/DP-FT giữ BLOCKED đến khi license weights/full native FastText/hash/RAM qua cổng. Không thay embedding để có kết quả.
9. Khi test gold đã approved, script59 tạo **input bundle riêng và gold bundle scorer-only**. Mở `notebooks/sprint03/final_test_after_dev_lock_v1.ipynb` sau dev locks; trước execution điền config/lock/run/backup, bật `ENABLE_FINAL_TEST=True`. Input-only được giải nén trước inference; gold chỉ ở cell scorer. Mỗi model/run riêng, không tune sau khi xem điểm test.
10. Tải toàn bộ run manifests/configs/predictions/metrics/error analysis/selection/calibration/checkpoint hashes về; báo riêng5 trường/T0/T1, unsupported labels, few-support labels, AI-assisted và seeds chưa chạy.

## 6. Kiểm thử và Git

Báo cáo46 ghi suite/hashes/GB/GiB và SHA remote thực. Không cộng các suite chồng lặp thành một số test khác. Code bàn giao nhánh `sprint3_huy`; nhánh partner `print3_label100test` giữ nguyên. Raw export/test gold/resources và interim không stage; nhận ZIP/evidence riêng từ chủ dự án.
