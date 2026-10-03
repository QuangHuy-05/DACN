# U6 — Bàn giao partner và Colab

Hai luồng tiếp tục độc lập. **Không cần gán lại300mẫu** train/dev đã duyệt. Test100 không có trong bundle Colab.

## A. Partner hoàn thành100test

Gửi thư mục đã khóa [test100_v1](annotation_handoff/test100_v1/README.md) từ nhánh GitHub **print3_label100test**. Gồm `test100_import.json`, XML, guideline, manifest, submission template và README. Gói này được kiểm bytes/hash, không mở nội dung task trong lượt chuẩn bị. Không dùng cross-AI/model prediction cho test ở protocol hiện tại.

1. Mở terminal có Label Studio Python3.11 sẵn, bật `label-studio start --host http://localhost:8080 --port 8080 --no-browser`. Giữ terminal chạy, truy cập **http://localhost:8080**, không truy cập0.0.0.0.
2. Tạo project mới `DACN_S3_T0_TEST_BLIND_v1`; Settings→Labeling Interface→Code: dán XML **của gói test** rồi Save.
3. Import duy nhất `test100_import.json`; kiểm đúng100task và chưa có prediction/MLbackend. Nếu đã import đúng thì không import lần hai.
4. Đọc guideline trước khi bắt đầu. Bôi mọi span theo chuỗi nguyên; gồm tiền tố loại đơn vị, không dấu phân cách ngoài. Không chồng lấp. Chọn hệ từng region; số nhà/đường không xác định, quận/huyện cũ; tên dùng ở cả hai thời kỳ cần bằng chứng để chọn hệ.
5. Hệ toàn câu chỉ khi đủ bằng chứng. Ca khó giữ task, thêm flag/note. Chọn `O` bằng cách không bôi phần ngoài địa chỉ/không đọc được, không dùng `Khac` chứa mọi ca khó. Submit hoặc Update mỗi task; không submit hàng loạt.
6. Khi đủ100/100, Export→**JSON raw**, không JSON-MIN/CSV/CoNLL. Gửi `test_blind_round1_<reviewer>.json` và submission template đã điền, gồm người gán/phạm vi đã xem/ca khó. Lưu tại máy chủ dự án: `data/interim/annotation/sprint03/exports/test/`.
7. Sau đó agent chạy QA trong **lượt test riêng**; partner sửa trên Label Studio rồi export vòng mới, chủ dự án phán quyết để phát hành gold. Submit/QA cấu trúc không tự là gold approval.

Lệnh dự kiến sau khi được mở lượt test, **chưa chạy trong lượt này**:

```bash
python -m scripts.17_convert_span_annotation_batch --export data/interim/annotation/sprint03/exports/test/test_blind_round1_<reviewer>.json --queue data/interim/annotation/sprint03/annotation_queue_batch01.csv --role frozen_benchmark_test_hold --output-dir data/interim/annotation/sprint03/test_conversion/blind_round1_<reviewer>
python -m scripts.18_audit_corpus_split audit --train data/processed/annotation/sprint03/corpus_train_dev_v2/train.jsonl --dev data/processed/annotation/sprint03/corpus_train_dev_v2/dev.jsonl --test <approved-canonical-test.jsonl> --decisions <approved-near-duplicate-decisions.csv> --output-dir <new-split-audit-dir>
```

Không lấy canonical candidate chưa duyệt thay approved test; giữ đúng100ID. Queue nội bộ/converter ở máy chủ dự án, partner chỉ cần gán/export/biên bản.

## B. Chủ dự án chuẩn bị Colab

Notebook: `notebooks/sprint03/preflight_and_train_dev.ipynb`. Local bundle: `data/interim/modeling/sprint03/pre_colab_20261003_resume_v1/handoff_v1/`.

- `dacn_train_dev_bundle_v1.zip`: snapshot code/config/protocol, train240/dev60/text-onlydev, corpus manifest/coverage/mask, lock và hướng dẫn. Không chứa test/raw export/venv.
- `dacn_phobert_resources_v1.zip`: chỉ files trong lock thực PhoBERT/VnCoreNLP/Java, dedup encoder/tokenizer, giữ LICENSE/legal/source URLs. Không fullFastText/DPweights.
- `handoff_manifest.json`: SHA-256/bytes của ZIP và notebook; các ZIP có manifest riêng tránh collision khi giải nén. File interim bị Gitignore: gửi/tải riêng, GitHub code không tự cung cấp resources/corpus local.

1. Mở notebook trên [Google Colab](https://colab.research.google.com/). Runtime→Change runtime type→GPU. GPU/RAM/disk không được bảo đảm theo [FAQ chính thức](https://research.google.com/colaboratory/faq.html); preflight phải kiểm thực tế.
2. Upload **haiZIP** vào `/content/` với đúng tên. Notebook đã pin checksum, dùng bundle snapshot thay giả định dirtycode đã có trong HEAD. Không copy WSL/Windowsvenv sang Colab.
3. Chạy lần lượt cell kiểm ZIP/hash, inventory, env Python3.11 riêng, package profile, Java, corpus/offset preparation và preflight. Packages cài chỉ trong env riêng/runtimeworkspace. Đọc output blocker; không giảm gate/AMP/budget để chạy.
4. PhoBERT/proposed: cần≥8GiBVRAM,≥20GiBdisk/run. Chọn candidate/runID **mới**. `ENABLE_NEURAL_TRAINING=False` mặc định; bật chỉ khi chủ dự án mở lượt training và preflight qua. Chạy cảc01/c02 theo protocol; chọn bằng dev.
5. Chọn `BACKUP_DIRECTORY` ở nơi persistent bạn quản lý. Nếu dùng Drive, bạn tự mount/cấp quyền và đặt path; không có token/Drive cá nhân trong notebook. Cell backup mỗi300giây và cuối lượt; copy/streaminghash, không move/xóa nguồn. Giữ best/last/optimizer/RNG và metadata.
6. Freeze devprediction trước→score riêng→proposed calibration dev→ablation constrainton/off cùngbestcheckpoint→audit. File checkpoint ở `checkpoints/best.pt`; resumePhoBERT từ `checkpoints/last.pt` vào run mới. DP chỉ weights restart.
7. DP-ZS/DP-FT cells đã có CLI/gate, mặc định không chạy: cần source/license weights được xác nhận, fullnativeFastText, active hashlock và≥10GiBhostRAM. Recipe pending không đủ để bật. Không đổi embedding để vượt gate.
8. Tải artifacts/manifest/báo cáo về và kiểm hash. Notebook chỉ chuẩn bị/cú pháp kiểm qua; **Colab bootstrap/GPU/training chưa được thực thi** ở lượt này. Không có cell100test.

## C. GitHub và dữ liệu riêng

Code/config/tests/docs/notebook bàn giao trên **sprint3_huy**; nhánh partner **print3_label100test** không bị cập nhật. Không push rawXML/CSV nguồn mới có redistributionterms chưa rõ, rawannotations, venv/cache/modelZIP hoặc run output lớn. Git snapshot giữ các prerequisitemodules từ những lượt Sprint3 trước.

Commit/push SHA thực nhận và diff/stagingmanifest nằm trong `pre_colab_20261003_resume_v1/git_handoff.json` sau push. Nếu GitHub chặn authentication/quyền ghi, report sẽ ghi blocker và commitlocal; không báo remote thành công khi chưa kiểm `git ls-remote`.

Việc chủ dự án cần làm: partner gán/export/biên bản100test; nhận haiZIP và mở Colab/preflight/chọnbackup/bậttraining ở lượt tiếp theo. Không cần sửa nhãn300mẫu, tự gán mã hành chính hàng nghìn dòng hoặc cài lại runtime local. Với DP/CSVsource, chỉ cần bổ sung quyền/bằng chứng khi upstream hiện chưa công bố đủ; agent xử lý tự động phần còn lại khi có nguồn.
