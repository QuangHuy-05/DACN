# Tái lập và bàn giao đánh giá cuối Sprint 3

## 1. Chuẩn bị

Đọc báo cáo 49 và prompt 48. Giữ HEUR threshold .86, CRF context 1/c1 .1/c2 1, PhoBERT-CRF c02, DYN c02 + calibration .7/.2, seed 42. Không train/tune/chọn mapping trên test. Hai cấu hình Deepparse bị chặn bởi nguồn điều kiện sử dụng checkpoint; chưa có metric pretrained thật.

Clone Git chỉ có code/config/docs/tests. Nhận **private artifact** từ owner: corpus release2, train/dev v2, source workspace submitted, hai best checkpoint, resource/legal locks và selection evidence. Đầu vào inference và gold scorer phải tách riêng. Kiểm SHA theo manifest; không upload gold100/raw export/GT/credentials. Gazetteer chưa rõ terms chỉ dùng local/private.

Runtime theo AGENTS: WSL; cache/TMPDIR trên D và PYTHONDONTWRITEBYTECODE=1. Tái dùng runtime CRF, neural và Kaggle CLI có sẵn trên D. Không đổi Python/WSL toàn máy. Inventory trước mọi cài mới. Credential đọc từ file riêng/phiên đăng nhập, không dán token vào Git hoặc chat.

## 2. Tạo một lượt inference mới

Chạy public script61 từ main, truyền workspace submitted đã khôi phục. Không chép main đè source model/processor cũ. Tạo text-only 5 trường bằng `prepare_fivefield_inputs` trong `src/modeling/final_inference_handoff.py`; đủ 4.800 hàng, loại 100 hold theo source row và text hash. Metadata ID/dataset chỉ ghép sau inference, không là feature.

```bash
python -m scripts.61_final_inference_pipeline prepare \
  --workspace "$NEURAL_WORKSPACE" --package-dir "$NEW_PACKAGE" \
  --fivefield-input "$FIVEFIELD_INPUT" --run-id "$NEW_RUN_ID"
python -m scripts.61_final_inference_pipeline upload \
  --package-dir "$NEW_PACKAGE" --credentials "$KAGGLE_CREDENTIAL_FILE" \
  --report "$NEW_UPLOAD_REPORT"
python -m scripts.61_final_inference_pipeline dataset-status \
  --package-dir "$NEW_PACKAGE" --credentials "$KAGGLE_CREDENTIAL_FILE" \
  --report "$NEW_DATASET_STATUS"
python -m scripts.61_final_inference_pipeline submit \
  --package-dir "$NEW_PACKAGE" --credentials "$KAGGLE_CREDENTIAL_FILE" \
  --report "$NEW_SUBMIT_REPORT"
```

Pipeline inference riêng giữ guard training của script50. Entry `notebooks/sprint03/final_inference_entry.py` dùng bridge trong `test_runner`, outer run ID `dev` cho phép chiếu 5 trường, **một worker/process cho mỗi model/track** để không cấu hình JVM hai lần. Không thay semantic config hoặc checkpoint. Lượt đã nghiệm thu: package v5, kernel `huynq16/dacn-s3-final-infer-20261005-v4/1`, dataset private tái dùng. Chưa cần chạy lại.

```bash
python -m scripts.61_final_inference_pipeline fetch \
  --package-dir "$PACKAGE" --credentials "$KAGGLE_CREDENTIAL_FILE" \
  --kernel-ref "$EXACT_OWNER_SLUG_VERSION" \
  --output-dir "$NEW_DOWNLOAD_DIR" --report "$NEW_TRANSFER_REPORT"
```

Kiểm job report, final inference report, artifact manifest, 100 ID/offset/status. Downloader stream 1 MiB, exact version và hash; không dùng eager buffer cho file lớn hoặc download latest. Giữ failed runs và tải phiên bản mới vào thư mục mới.

## 3. Freeze toàn roster rồi mới chấm

`freeze_ready_predictions` kiểm tất cả READY model và ablation, 100 ID/text/hash, chưa tồn tại metric/scoring manifest. Roster và pre-test manifest phải hash-pin trước inference; DP blocker ghi trước scorer. Chỉ `ALL_READY_TEST_PREDICTIONS_FROZEN` mới mở quyền đọc gold.

```bash
python -m scripts.62_score_final_evaluation \
  --freeze-receipt "$ALL_READY_FREEZE" --roster "$FROZEN_ROSTER" \
  --pre-test-freeze "$PRE_TEST_FREEZE" \
  --neural-workspace "$NEURAL_WORKSPACE" --output-dir "$NEW_SCORING_DIR"
```

Script62 gọi neural scorer trong đúng source workspace pin; light scorer từ main. Kiểm mask T1 64/20/16, giữ tất cả T0; track 5 trường và overlap dùng cùng subset cho các model. Output/run mới, không overwrite. Không sửa mapping, threshold hoặc weights theo test score.

## 4. Artifact bàn giao

- `scoring_v1/results_index.json`: T0/T1/structure/5 trường và đường dẫn/hash từng model.
- `paired_ablation.json`, `paired_metric_delta.json`: checkpoint giống nhau, span thay đổi và delta on/off.
- `overlap/overlap_metrics.json`: seen train/dev, unseen registered key và UNKNOWN_OVERLAP. Toàn track vẫn là development.
- `metric_recomputation.json`, `fivefield_metric_recomputation.json`, `protected_final_audit.json`: metric T0/T1/5 trường tái tính; raw/gold/split/source/Gazetteer/run/checkpoint giữ nguyên.
- `artifact_index.json`, `artifact_index_v2.json`, `storage_receipt.json`, `storage_receipt_v2.json`, `sprint3_completion_manifest.json`, `git_final_receipt.json`: bytes/hash/phạm vi chia sẻ/Git thật. Snapshot v2 đóng các file bàn giao viết sau snapshot audit đầu.
- `execution_registry.json`: ID thực thi duy nhất theo kernel/version/output. Nhãn run_id trong config đã khóa không dùng riêng để phân biệt retries; không đổi tên manifest frozen.

Các file trong evidence private cần nhận riêng, không có trong clone Git. Nhãn 0 support là NOT_EVALUABLE; T1 NOT_IMPLEMENTED có metric null; accepted accuracy không phải accuracy trên toàn 64 mẫu.

## 5. Kiểm thử và Git

```bash
python -m unittest discover -s tests -v
```

274 test: 266 PASS, 8 SKIP, 0 FAIL ở env chính. Modeling 52/52 và CRF 13/13 chạy ở runtime chuyên biệt, không cộng trùng vào tổng. Fixture không thay pretrained experiment. Audit SHA trước/sau và metric recomputation là cổng nghiệm thu.

Dùng checkout bàn giao riêng nhánh `sprint3_huy`; giữ main/partner `print3_label100test`. Native Windows Git xử lý worktree path Windows. Stage allowlist code/tests/docs, review diff, commit, push không force, verify remote SHA. Không stage gold/raw/answer/weights/cache/nguồn chưa cleared.

## 6. Owner còn cần làm gì

Không cần gán/Submit/export lại bất kỳ mẫu nào. Bốn mô hình và ablation đã đánh giá cuối. Để đủ cả sáu cấu hình cần bằng chứng upstream rõ về license/terms của Deepparse checkpoint pin; khi có bằng chứng, agent tiếp tục native smoke và hai candidate DP chỉ bằng train/dev. Data05 hoãn, VQA HOLD, IAA NOT_MEASURED. Colab là phương án thay thế; không cần train lại checkpoint chỉ để đổi nền tảng.
