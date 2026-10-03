# PhoBERT offset-alignment remediation — 03/10/2026

## Trạng thái

**Đã hoàn tất lỗi căn chỉnh PhoBERT cho đủ 300 mẫu train/dev mà không sửa corpus hoặc gán nhãn.** Cả audit ký tự lẫn toàn đường PhoBERT tokenizer + VnCoreNLP đều đạt 240/240 train + 60/60 dev; raw-span round-trip 300/300; cả 29 ID từng bị từ chối đều được khôi phục. Không còn alignment reject. Đây là kiểm tra alignment, **không phải** model prediction, F1 hay kết quả test.

## Nguyên nhân và chính sách sửa

VnCoreNLP giữ chữ cái và dấu thanh nhưng có thể đổi vị trí dấu trong cùng một âm tiết, chẳng hạn `hòa → hoà`, `ủy → uỷ`, `ùy → uỳ`. So khớp từng code point đúng tuyệt đối vì vậy từ chối cả câu, dù có thể ánh xạ các grapheme của kết quả segmentation về chuỗi gốc.

Processor version mới `phobert_raw_unit_pool_v2_tone_relocation` áp dụng điều kiện hẹp:

- Chữ cái nền và các dấu chất lượng nguyên âm phải giữ nguyên ở từng vị trí.
- Dấu thanh được so sánh theo tập trong từng cụm nguyên âm liên tiếp; ranh giới là `_` của VnCoreNLP, phụ âm, khoảng trắng hoặc dấu phân cách.
- Chỉ chấp nhận thay đổi vị trí dấu nếu dấu thanh và cụm nguyên âm liên tiếp không đổi. Đổi dấu, đổi chữ/chất lượng nguyên âm hoặc chuyển dấu qua phụ âm/ranh giới âm tiết vẫn bị từ chối.
- Mỗi code point do segmenter trả về giữ mapping tới interval grapheme của **chuỗi gốc**. Text và offset gốc không bị chuẩn hóa hay ghi lại; không dùng fuzzy/edit-distance.
- Alignment trace ghi vị trí source/output nào có dấu khác nhau. Những mục trong trace là các vị trí ký tự nguồn/đích, không phải số âm tiết hay số lỗi.

Các config PHOBERT-CRF, PROPOSED-DYN và PROPOSED-NO-CONSTRAINT được gắn processor version mới. Ngân sách, split, model candidates và dữ liệu không đổi. `protocol_lock_v1.json` được amendment/hash lại; bản lock trước đó được giữ tại `protocol_lock_v1_pre_alignment_20261002.json`. Chưa chạy training.

## Bằng chứng chạy lại đủ 300 mẫu

Audit đọc manifest/corpus đã phát hành `corpus_train_dev_v2` với hash `9c91b77fa220e41b1b1067e5e99b216b7b4b2176181674b340f16dec134947bf`, chỉ lấy text train/dev làm đầu vào segmenter. Hash JAR và mọi asset word-segmenter khớp resource lock. Kết quả:

| Kiểm tra | Kết quả |
| --- | ---: |
| VnCoreNLP→raw-character map, train | 240/240 exact |
| VnCoreNLP→raw-character map, dev | 60/60 exact |
| Raw gold spans round-trip, cả hai split | 300/300 exact |
| ID từng bị reject đã được khôi phục | 29/29; train 23, dev 6 |
| So khớp segmentation với lần VnCoreNLP/ PhoBERT thực chạy trước | 300/300 giống hệt |
| Mẫu có thay đổi vị trí dấu được trace | 29; tổng 66 slot ký tự nguồn/đích |
| Mẫu còn unrepresentable | 0 |

**Xác nhận processor đầy đủ:** lúc đầu WSL trả `Wsl/EnumerateDistros … E_ACCESSDENIED`, nên script 38 dùng đúng VnCoreNLP JAR/model trên Windows Java Temurin 17.0.18.8 làm audit ký tự; segmentation khớp 300/300 với lần tích hợp cũ. Sau đó script 37 đã chạy thành công trong runtime neural D: Python 3.11.16, PhoBERT slow tokenizer thật và VnCoreNLP thật; kết quả 240/240 train + 60/60 dev `EXACT`, supervised alignment QA 300/300 `EXACT`, `alignment_reject_reasons={}`. Script chạy `--skip-forward`, nên không forward encoder, không train, không sinh prediction/metric. Không cài thêm package.

Không mở/đọc nhãn test100; không dùng Colab; không tạo prediction/metric; không thay đổi Label Studio, raw export, canonical gold, train/dev split hay exception T1 của task 543.

## Artifact và kiểm tra

- Mã policy: [alignment.py](../../../src/modeling/alignment.py)
- Audit tái lập: [38_audit_phobert_tone_alignment.py](../../../scripts/38_audit_phobert_tone_alignment.py)
- Regression tests: [test_modeling_pipeline.py](../../../tests/test_modeling_pipeline.py)
- Config version mới: `configs/modeling/sprint03/{phobert_crf_v1,proposed_dyn_v1,proposed_no_constraint_v1}.json`
- Protocol: [17_training_protocol_v1.md](17_training_protocol_v1.md)
- Evidence folder (interim, Git-ignore): `data/interim/modeling/sprint03/alignment_tone_policy_v2_20261003/full_300_audit_r5/`
  - `alignment_audit_manifest.json` SHA-256: `ebc88931ee743aea9f9d6dc3edefb3947517ce884424a85b93b65e8cb4349532`
  - `text_only_character_alignment.jsonl` SHA-256: `717da5bea90738a57b7c3327f2ed8718db117e1d1cc0025f51851dd68405fb13`
  - `supervised_raw_span_round_trip_qa.jsonl` SHA-256: `1b7b251ad0becc430c792209e07b92af1733851b30b99d3a425263599796f0d2`
- PhoBERT runtime integration (interim, Git-ignore): `data/interim/modeling/sprint03/neural_integration_tone_v2_replay_20261003_fullpath/`
  - `integration_manifest.json` SHA-256: `dc180674005e82e7750c934319079d4cb49478188e5afd534767fcfe7c8e0f36`
  - Actual tokenizer/segmenter offsets: `text_only_alignments.jsonl` SHA-256 `3eaf2732d2ebdeb6b3e4ccb4d739a00c445c405d5664705be8b568c015278b47`
  - Gold QA: `supervised_alignment_qa.jsonl` SHA-256 `1e52d92f47e25f25eecbfc08e1db06e379a39b75dfd64bb8afa190d964a905a7`
- Full WSL suite log: `data/interim/modeling/sprint03/alignment_tone_policy_v2_20261003/full_300_audit_r5/full_suite_wsl_py314_final.log`

Kiểm thử `test_modeling_pipeline.py`: **45 PASS / 7 SKIP / 0 FAIL** trong Python bundled 3.12.14; skip là integration Torch/Deepparse không có ở Python này. Full regression suite trong `.venv_dacn` WSL Python 3.14.4 đạt **153 PASS / 8 SKIP / 0 FAIL** trên 161 test. Lượt full discovery bundled Python trước đó có hai import error do thiếu `osmium` và `vietnamadminunits`; kết quả WSL đầy đủ là nghiệm thu cuối.

Lệnh đã dùng để chạy lại toàn bộ PhoBERT tokenizer integration trong WSL:

```bash
cd /mnt/d/DACN
source data/interim/modeling/sprint03/task_01_06_20261003_v1/runtime_env.sh
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
"$TASK_PYTHON" -m scripts.37_verify_local_neural_integration \
  --resource-lock data/interim/modeling/sprint03/task_01_06_20261003_v1/resource_lock_local_v1.json \
  --output-dir data/interim/modeling/sprint03/neural_integration_tone_v2_replay_20261003 \
  --skip-forward
```

Output folder là version mới nên lệnh sẽ từ chối ghi đè nếu thư mục đã tồn tại.
