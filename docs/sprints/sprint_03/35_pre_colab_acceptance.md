# U5 — Nghiệm thu trước bàn giao

Evidence root: `data/interim/modeling/sprint03/pre_colab_20261003_resume_v1/`. P0 đã rà kết quả agent trước: P0/client đã có, chưa đủ release/run/bundle cho sáu việc. Agent tiếp tục giữ mọi dirty file, không reset/clean/stash. WSL cần quyền thực thi ngoài sandbox mặc định; dùng runtime có sẵn và cache/temp D, `bash --noprofile --norc`.

## Kiểm bất biến và artifact

- `u5/acceptance_v1/acceptance.json`: **ACCEPTANCE_PASS**,16run mới (6HEUR+8CRF+2track5field), prediction đủ60ID dev,raw text/offset/no-overlap PASS, checkpoint/resources/input/scoring manifest khớp.
- `u5/acceptance_v1/frozen_compare.json`: **550file hash +4raw size/mtime không thay đổi**; bao gồm corpus/split/gold, s3_v1/v2/v3, runs cũ, configs/protocol, raw exports và gói test-only. V3 được bao phủ rõ.
- Corpus vẫn240/60,1.341span,BIO23,T1eligible206/53,mask task543 giữ T0. Hash manifest `9c91b77fa220e41b1b1067e5e99b216b7b4b2176181674b340f16dec134947bf`.
- Actual processor evidence fullpath được kiểm output hashes: **240/240+60/60 EXACT**, gold alignment QA300/300,29ca đổi dấu đã khôi phục. Processor/alignment code không đổi; thay resource preflight thêm GPU gate không thay segmentation/BPE/offset policy.
- Source/reference/Gazetteer kiểm count/hash/parent/date/code status. Release2 chỉ hoàn chỉnh source metadata, không thay năm file entity/graph/alias/evidence của v4 đã chạy.

Code hash lịch sử có thể khác working tree hiện hành. Không sửa manifest của run frozen để khớp mã mới. Mã resource của run mới được lưu sidecar `u5/acceptance_v1/run_code_snapshot/`. Source metadata module lúc phát hành release2 cũng giữ snapshot riêng. Thiếu code snapshot của run lịch sử chỉ giới hạn replay, không chứng minh output bytes bị sửa.

## Kiểm thử

Kết quả cuối: full suite **185 = 177 PASS + 8 SKIP**, focused neural **73/73 PASS**, focused CRF **50/50 PASS**, không FAIL. Logs `full_suite_final.log`, `neural_suite_final.log`, `crf_suite_final.log`. Không cộng ba suite thành một tổng độc lập. `.gitattributes` giữ nguyên bytes config/profile/notebook có hash khi clone Windows.

Logs theo runtime, không cộng tổng các suite chồng lặp:

- Full suite: env dự án WSL hiện hữu; `full_suite_round2.log` và các log final tiếp theo nếu thêm regression. Các skip Torch/Deepparse và CRF là do env chính không cài stack đó; phải đọc focused suite riêng.
- Neural trên D: `neural_suite_round2.log` rồi log final; torch CRF/checkpoint/optimizer/RNG tests là **tiny fixture**, native Deepparse API/container test không tải fullembedding. Không gọi đây là thực nghiệm pretrained.
- CRF trên D: `crf_suite.log` rồi log final; checkpoint/feature/roundtrip tests chạy thật với pycrfsuite.
- Lần focused neural đầu gọi `tests.<module>` bị ba import error vì package `tests` bên thứ ba che namespace dự án. Đã đổi sang discovery bằng script46; giữ failed log, chạy lại PASS. Đây là lỗi gọi suite đã xử lý, không giấu bằng skip.
- Fixtures kiểm SOAPFault/schema row/duplicate/leading zero/parent invalid/date scope/alltargets/metadata; GPUoverlay/AMP/protocol pin; ZIPtraversal/hash/manifestcollision; notebook AST và trainingoff; DPzero gate chặn trước parser và chọn pretrained checkpoint.

Lệnh tái kiểm:

```bash
python -m unittest discover -s tests -v
python -m scripts.46_run_pre_colab_focused_tests --profile neural
python -m scripts.46_run_pre_colab_focused_tests --profile crf
python -m scripts.45_accept_pre_colab --output-dir data/interim/modeling/sprint03/pre_colab_reaudit001
```

`readiness.json`, final test summary, storage accounting và Git handoff report trong evidence root ghi số cuối có log/hash. Notebook/bundles chỉ **PREPARED_VERIFIED_NOT_EXECUTED**; GPU/bootstrap/train chưa thực thi Colab. DP full resources/license/native integration vẫn blocked, snapshot pháp lý/CSV redistribution vẫn chưa đủ nguồn. Test100 vẫn `TEST_PENDING`. Không phát hành corpus ba split/test gold trong lượt này.
