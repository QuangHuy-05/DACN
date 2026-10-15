# Kiểm toán run baseline — Sprint 3

- Thời điểm UTC: `2026-09-25T06:20:08.747782+00:00`.
- Runtime kiểm toán: `3.12.14 on win32`.
- Môi trường thực thi: WSL access denied in this Codex sandbox; used bundled Python 3.12.14 with no package installation; scorer source hashes verified against each manifest.
- Chạy chỉ đọc trên run frozen; JSON cùng thư mục là nguồn cho bảng này.
- `PASS` của v3 chỉ áp dụng cho track 5 trường với oracle mode theo protocol; Data 07 là phép chuyển cũ → mới, không phải T0/T1.

## Kết luận

| Run | Quyết định | Manifest SHA-256 | Pass | Fail | Unverifiable |
| --- | --- | --- | ---: | ---: | ---: |
| `baseline_v2` | **UNVERIFIABLE** | `f870c0bc4d0317c45008a792a6be0f220e23818f2e0e738f972d1b25ffc9c7bf` | 80 | 0 | 3 |
| `baseline_v3_fuzzy` | **PASS** | `14da842d270d2b0e2a31efd954c07d3a0f948cc7b3d7c8240687ae7a19a46fcb` | 115 | 0 | 0 |

**Các cổng chưa đạt hoặc chưa thể xác minh:**

- `baseline_v2`: `CODE_src_evaluation_adapters_vnadmin_adapter_py` (unverifiable), `CODE_scripts_build_baseline_dashboard_py` (unverifiable), `V2_DERIVED_SCOPE` (unverifiable).
  Scorer dùng để replay: `git:HEAD`.
- `baseline_v3_fuzzy`: không có.
  Scorer dùng để replay: `working_tree`.

`baseline_v2` là mốc lịch sử frozen. Không so điểm fuzzy v2 với v3 vì manifest v2 không dùng cùng protocol fuzzy. Tài liệu v2 thuộc phạm vi lưu lịch sử theo `docs/VERSIONING.md`.

## Kiểm tra chi tiết

### baseline_v2

| Check | Phạm vi | Kết quả | Expected | Actual | Bằng chứng | Mẫu lỗi |
| --- | --- | --- | --- | --- | --- | --- |
| `MANIFEST_VERSION` | core | pass | 3.0 | 3.0 | `data/processed/evaluation/runs/baseline_v2/run_manifest.json` | [] |
| `MANIFEST_RUN_ID` | core | pass | baseline_v2 | baseline_v2 | `data/processed/evaluation/runs/baseline_v2/run_manifest.json` | [] |
| `MANIFEST_RUN_KIND` | core | pass | full | full | `data/processed/evaluation/runs/baseline_v2/run_manifest.json` | [] |
| `MANIFEST_SEED` | core | pass | 42 | 42 | `data/processed/evaluation/runs/baseline_v2/run_manifest.json` | [] |
| `MANIFEST_FREEZE_TIMESTAMP` | core | pass | present | present | `data/processed/evaluation/runs/baseline_v2/run_manifest.json` | [] |
| `MANIFEST_PYTHON_VERSION` | core | pass | present | present | `data/processed/evaluation/runs/baseline_v2/run_manifest.json` | [] |
| `MANIFEST_RUNTIME_PACKAGES` | core | pass | present | present | `data/processed/evaluation/runs/baseline_v2/run_manifest.json` | [] |
| `MANIFEST_BASELINE_TOOLS` | core | pass | present | present | `data/processed/evaluation/runs/baseline_v2/run_manifest.json` | [] |
| `MANIFEST_PROTOCOL` | core | pass | present | present | `data/processed/evaluation/runs/baseline_v2/run_manifest.json` | [] |
| `MANIFEST_MAPPING_SOURCE` | core | pass | present | present | `data/processed/evaluation/runs/baseline_v2/run_manifest.json` | [] |
| `MANIFEST_CODE_HASHES` | core | pass | present | present | `data/processed/evaluation/runs/baseline_v2/run_manifest.json` | [] |
| `MANIFEST_OUTPUT_HASHES` | core | pass | present | present | `data/processed/evaluation/runs/baseline_v2/run_manifest.json` | [] |
| `MANIFEST_OUTPUT_ROW_COUNTS` | core | pass | present | present | `data/processed/evaluation/runs/baseline_v2/run_manifest.json` | [] |
| `MANIFEST_OUTPUT_baseline_predictions_unified_csv` | core | pass | hash and count present | hash and count present | `data/processed/evaluation/runs/baseline_v2/run_manifest.json` | [] |
| `MANIFEST_OUTPUT_baseline_raw_responses_jsonl` | core | pass | hash and count present | hash and count present | `data/processed/evaluation/runs/baseline_v2/run_manifest.json` | [] |
| `DATASET_LIST` | core | pass | ["01_full_address_new_verified.csv", "02_raw_noisy_synthetic_1000.csv", "03_real_address_old_1500... | ["01_full_address_new_verified.csv", "02_raw_noisy_synthetic_1000.csv", "03_real_address_old_1500... | `data/processed/evaluation/runs/baseline_v2/run_manifest.json` | [] |
| `INPUT_01` | core | pass | {"sha256": "7e2afd47828d04d108c67d29f45cb50b6a5321ae8feef595cf2b67229796a60d", "size_bytes": 1486... | {"sha256": "7e2afd47828d04d108c67d29f45cb50b6a5321ae8feef595cf2b67229796a60d", "size_bytes": 1486... | `data/processed/benchmark/01_full_address_new_verified.csv` | [] |
| `INPUT_02` | core | pass | {"sha256": "bd425883f624c98e206d6ab197240b9642eb63352b56efd06723d04401751def", "size_bytes": 3526... | {"sha256": "bd425883f624c98e206d6ab197240b9642eb63352b56efd06723d04401751def", "size_bytes": 3526... | `data/processed/benchmark/02_raw_noisy_synthetic_1000.csv` | [] |
| `INPUT_03` | core | pass | {"sha256": "d2748f4cedc498046100779a6f59fb1ef1e79c3049aeefe9d6d542afa79badda", "size_bytes": 3331... | {"sha256": "d2748f4cedc498046100779a6f59fb1ef1e79c3049aeefe9d6d542afa79badda", "size_bytes": 3331... | `data/processed/benchmark/03_real_address_old_1500.csv` | [] |
| `INPUT_04` | core | pass | {"sha256": "46305aac4821c2f2bc96913cfaf3a89f3087dd91216f5093dc7f89b8541fc021", "size_bytes": 1600... | {"sha256": "46305aac4821c2f2bc96913cfaf3a89f3087dd91216f5093dc7f89b8541fc021", "size_bytes": 1600... | `data/processed/benchmark/04_missing_fields_800.csv` | [] |
| `INPUT_05` | core | pass | {"sha256": "6249b06941d6e89a8a731fc47d0b844ee89ed8dce5a902bfcaac13d2785ced8d", "size_bytes": 2155... | {"sha256": "6249b06941d6e89a8a731fc47d0b844ee89ed8dce5a902bfcaac13d2785ced8d", "size_bytes": 2155... | `data/processed/benchmark/06_hybrid_addresses_600.csv` | [] |
| `INPUT_06` | core | pass | {"sha256": "3f11b0d02a05922662613c460014da34f89def7da1e7e1ba6ef496aa369245fc", "size_bytes": 1494... | {"sha256": "3f11b0d02a05922662613c460014da34f89def7da1e7e1ba6ef496aa369245fc", "size_bytes": 1494... | `data/processed/benchmark/07_bidirectional_pairs_verified.csv` | [] |
| `MAPPING_SOURCE` | core | pass | {"file_name": "vietnam-sap-nhap-phuong-xa.csv", "sha256": "22bd8278cf7b3f969f255e841271f33f63f6d9... | {"file_name": "vietnam-sap-nhap-phuong-xa.csv", "sha256": "22bd8278cf7b3f969f255e841271f33f63f6d9... | `data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv` | [] |
| `MAPPING_COLUMNS` | core | pass | ["Mã phường/xã mới", "Phường/Xã mới (từ 1/7/2025)", "Tỉnh/TP mới"] | ["Mã phường/xã mới", "Phường/Xã mới (từ 1/7/2025)", "Tỉnh/TP mới"] | `data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv` | [] |
| `MAPPING_TARGET_CONFLICTS` | core | pass | 0 | 0 | `data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv` | [] |
| `BENCHMARK_CONTRACT` | core | pass | valid | valid | `src/evaluation/data_contract.py` | [] |
| `CODE_src_evaluation_adapters_libpostal_adapter_py` | core | pass | 53817addaaf5bce4312b4823137e1a7e8d7c406a27a85eb7c6c88fbc9fa289a2 | 53817addaaf5bce4312b4823137e1a7e8d7c406a27a85eb7c6c88fbc9fa289a2 | `src/evaluation/adapters/libpostal_adapter.py` | [] |
| `CODE_src_evaluation_adapters_vnadmin_adapter_py` | core | unverifiable | 530bdf0d2a7c87edcb3327ed4f41dea18af5a6b57c0f41e65602168a3211b6fe | None | `src/evaluation/adapters/vnadmin_adapter.py` | [] |
| `CODE_src_evaluation_scorer_py` | core | pass | 15ea5f5fec0055d367b4374de3d99eba39aa26e3419f011ae59acaa786c8c5a1 | 15ea5f5fec0055d367b4374de3d99eba39aa26e3419f011ae59acaa786c8c5a1 | `src/evaluation/scorer.py` | [] |
| `CODE_src_evaluation_data_contract_py` | core | pass | 85f65d953394d9276604d8125538a7da03c3ab23e457ba9fb40cb2910f689d83 | 85f65d953394d9276604d8125538a7da03c3ab23e457ba9fb40cb2910f689d83 | `src/evaluation/data_contract.py` | [] |
| `CODE_src_evaluation_manifest_py` | core | pass | f3a2995a2a1431c1fc3e6ec7b1b7e78fd98ec3ece427bf875ea425190f4bbad9 | f3a2995a2a1431c1fc3e6ec7b1b7e78fd98ec3ece427bf875ea425190f4bbad9 | `src/evaluation/manifest.py` | [] |
| `CODE_src_evaluation_protocol_py` | core | pass | a5917c02e4829f08566dde3b6f8f1cace3aaca03d9c8921b51f8251df05e297a | a5917c02e4829f08566dde3b6f8f1cace3aaca03d9c8921b51f8251df05e297a | `src/evaluation/protocol.py` | [] |
| `CODE_src_evaluation_run_artifacts_py` | core | pass | a670f7a8ada43b3702323928300d368dee05b64b27efaef81e30880de43f758b | a670f7a8ada43b3702323928300d368dee05b64b27efaef81e30880de43f758b | `src/evaluation/run_artifacts.py` | [] |
| `CODE_scripts_05_run_baseline_pilot_py` | core | pass | 8037b7c3fcfeb0c19ee1beae4136967e41aaa70a043832cef72e57651f605a25 | 8037b7c3fcfeb0c19ee1beae4136967e41aaa70a043832cef72e57651f605a25 | `scripts/05_run_baseline_pilot.py` | [] |
| `CODE_scripts_06_run_baseline_full_py` | core | pass | f7a7ea0107118c5504f0dd584f23126f3e90a6c847083694ccc199c19b574b44 | f7a7ea0107118c5504f0dd584f23126f3e90a6c847083694ccc199c19b574b44 | `scripts/06_run_baseline_full.py` | [] |
| `CODE_scripts_07_generate_baseline_report_py` | core | pass | 4b671dba347bdd2e9b0a5c2389e3df17426e4a4ea0b4977ab81c747f94f9e62d | 4b671dba347bdd2e9b0a5c2389e3df17426e4a4ea0b4977ab81c747f94f9e62d | `scripts/07_generate_baseline_report.py` | [] |
| `CODE_scripts_08_generate_report_materials_py` | core | pass | 49ad65ca251ff2af08def9ac1dd1e5520457e303a3e271febea240f6afe97efa | 49ad65ca251ff2af08def9ac1dd1e5520457e303a3e271febea240f6afe97efa | `scripts/08_generate_report_materials.py` | [] |
| `CODE_scripts_build_baseline_dashboard_py` | core | unverifiable | 721c1fb99ad44bd303f38c691944f1aa55d3c25797a6b3cb10f1fd5615c74b2a | None | `scripts/build_baseline_dashboard.py` | [] |
| `CODE_src_evaluation_reporter_py` | core | pass | ae6333163a0610db185df615964fa253a96cabfe1c8dbe5a15485d1dc027b8b5 | ae6333163a0610db185df615964fa253a96cabfe1c8dbe5a15485d1dc027b8b5 | `src/evaluation/reporter.py` | [] |
| `OUTPUT_SHA_PRED` | core | pass | 49a670709a66e08c2c9f9097d1dc965cb427a8b37c714cf5afa7f6f976cc46ed | 49a670709a66e08c2c9f9097d1dc965cb427a8b37c714cf5afa7f6f976cc46ed | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `OUTPUT_SHA_RAW` | core | pass | 10b82803b6734053e4f4b1df2674adda465e4cb9291fcdef4978890c479be119 | 10b82803b6734053e4f4b1df2674adda465e4cb9291fcdef4978890c479be119 | `data/processed/evaluation/runs/baseline_v2/baseline_raw_responses.jsonl` | [] |
| `PRED_COLUMNS` | core | pass | ["ID", "DiaChiGoc", "CongCu", "TruongDuDoan", "TruongDung", "DungSai", "LoaiLoi", "TinhHuongMoHo"... | ["ID", "DiaChiGoc", "CongCu", "TruongDuDoan", "TruongDung", "DungSai", "LoaiLoi", "TinhHuongMoHo"... | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `PRED_BOM` | core | pass | True | True | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `PRED_ROWS` | core | pass | 13000 | 13000 | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `RAW_JSONL` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v2/baseline_raw_responses.jsonl` | [] |
| `RAW_ROWS` | core | pass | 13000 | 13000 | `data/processed/evaluation/runs/baseline_v2/baseline_raw_responses.jsonl` | [] |
| `EXPECTED_COUNT` | core | pass | 13000 | 13000 | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `PRED_KEY_UNIQUE` | core | pass | 13000 | 13000 | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `RAW_KEY_UNIQUE` | core | pass | 13000 | 13000 | `data/processed/evaluation/runs/baseline_v2/baseline_raw_responses.jsonl` | [] |
| `PRED_EXPECTED_KEYS` | core | pass | 13000 | 13000 | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `PRED_UNEXPECTED_KEYS` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `RAW_PAIR_KEYS` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v2/baseline_raw_responses.jsonl` | [] |
| `COVERAGE_D01_libpostal` | core | pass | 1000 | 1000 | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `COVERAGE_D01_vietnamadminunits` | core | pass | 1000 | 1000 | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `COVERAGE_D02_libpostal` | core | pass | 2000 | 2000 | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `COVERAGE_D02_vietnamadminunits` | core | pass | 2000 | 2000 | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `COVERAGE_D03_libpostal` | core | pass | 1500 | 1500 | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `COVERAGE_D03_vietnamadminunits` | core | pass | 1500 | 1500 | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `COVERAGE_D04_libpostal` | core | pass | 800 | 800 | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `COVERAGE_D04_vietnamadminunits` | core | pass | 800 | 800 | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `COVERAGE_D06_libpostal` | core | pass | 600 | 600 | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `COVERAGE_D06_vietnamadminunits` | core | pass | 1200 | 1200 | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `COVERAGE_D07_vietnamadminunits` | core | pass | 600 | 600 | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `COVERAGE_UNEXPECTED` | core | pass | [] | [] | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `INPUT_SOURCE` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `SCENARIO_SOURCE` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `PAIR_FIELDS` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v2/baseline_raw_responses.jsonl` | [] |
| `RAW_STATUS` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v2/baseline_raw_responses.jsonl` | [] |
| `RAW_STATUS_CONSISTENCY` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v2/baseline_raw_responses.jsonl` | [] |
| `RAW_EXCEPTION` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v2/baseline_raw_responses.jsonl` | [] |
| `RAW_DURATION` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v2/baseline_raw_responses.jsonl` | [] |
| `MODE_SOURCE` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v2/baseline_raw_responses.jsonl` | [] |
| `D07_DIRECTION` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v2/baseline_raw_responses.jsonl` | [] |
| `FIELD_JSON` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `D02_GOLD` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `D04_GOLD` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `D07_TARGET` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `OTHER_GOLD` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `D06_MODE_NOTE` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `D07_DIRECTION_NOTE` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `SCORER_REPLAY` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v2/baseline_predictions_unified.csv` | [] |
| `V2_DERIVED_SCOPE` | derived | unverifiable | historical report not certified | historical report not certified | `data/processed/evaluation/runs/baseline_v2/run_manifest.json` | [] |
| `FROZEN_UNCHANGED` | core | pass | True | True | `data/processed/evaluation/runs` | [] |

**Phân bố lượt theo tập và tool:**

- `D01|libpostal`: 1000
- `D01|vietnamadminunits`: 1000
- `D02|libpostal`: 2000
- `D02|vietnamadminunits`: 2000
- `D03|libpostal`: 1500
- `D03|vietnamadminunits`: 1500
- `D04|libpostal`: 800
- `D04|vietnamadminunits`: 800
- `D06|libpostal`: 600
- `D06|vietnamadminunits`: 1200
- `D07|vietnamadminunits`: 600

**Trạng thái raw log:**

- `libpostal|success`: 5900
- `vietnamadminunits|exception`: 4
- `vietnamadminunits|success`: 7096

### baseline_v3_fuzzy

| Check | Phạm vi | Kết quả | Expected | Actual | Bằng chứng | Mẫu lỗi |
| --- | --- | --- | --- | --- | --- | --- |
| `MANIFEST_VERSION` | core | pass | 4.0 | 4.0 | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `MANIFEST_RUN_ID` | core | pass | baseline_v3_fuzzy | baseline_v3_fuzzy | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `MANIFEST_RUN_KIND` | core | pass | full | full | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `MANIFEST_SEED` | core | pass | 42 | 42 | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `MANIFEST_FREEZE_TIMESTAMP` | core | pass | present | present | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `MANIFEST_PYTHON_VERSION` | core | pass | present | present | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `MANIFEST_RUNTIME_PACKAGES` | core | pass | present | present | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `MANIFEST_BASELINE_TOOLS` | core | pass | present | present | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `MANIFEST_PROTOCOL` | core | pass | present | present | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `MANIFEST_MAPPING_SOURCE` | core | pass | present | present | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `MANIFEST_CODE_HASHES` | core | pass | present | present | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `MANIFEST_OUTPUT_HASHES` | core | pass | present | present | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `MANIFEST_OUTPUT_ROW_COUNTS` | core | pass | present | present | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `MANIFEST_OUTPUT_baseline_predictions_unified_csv` | core | pass | hash and count present | hash and count present | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `MANIFEST_OUTPUT_baseline_raw_responses_jsonl` | core | pass | hash and count present | hash and count present | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `SCORING_PROTOCOL_VERSION` | core | pass | present | present | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `SCORING_FUZZY_SIMILARITY_METHOD` | core | pass | present | present | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `SCORING_FUZZY_SIMILARITY_NORMALIZATION` | core | pass | present | present | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `SCORING_FUZZY_EMPTY_POLICY` | core | pass | present | present | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `SCORING_ADMINISTRATIVE_TARGET_RULE` | core | pass | present | present | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `SCORING_PROTOCOL` | core | pass | 2.0 | 2.0 | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `SCORING_METHOD` | core | pass | normalized_levenshtein | normalized_levenshtein | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `DATASET_LIST` | core | pass | ["01_full_address_new_verified.csv", "02_raw_noisy_synthetic_1000.csv", "03_real_address_old_1500... | ["01_full_address_new_verified.csv", "02_raw_noisy_synthetic_1000.csv", "03_real_address_old_1500... | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `INPUT_01` | core | pass | {"sha256": "7e2afd47828d04d108c67d29f45cb50b6a5321ae8feef595cf2b67229796a60d", "size_bytes": 1486... | {"sha256": "7e2afd47828d04d108c67d29f45cb50b6a5321ae8feef595cf2b67229796a60d", "size_bytes": 1486... | `data/processed/benchmark/01_full_address_new_verified.csv` | [] |
| `INPUT_02` | core | pass | {"sha256": "bd425883f624c98e206d6ab197240b9642eb63352b56efd06723d04401751def", "size_bytes": 3526... | {"sha256": "bd425883f624c98e206d6ab197240b9642eb63352b56efd06723d04401751def", "size_bytes": 3526... | `data/processed/benchmark/02_raw_noisy_synthetic_1000.csv` | [] |
| `INPUT_03` | core | pass | {"sha256": "d2748f4cedc498046100779a6f59fb1ef1e79c3049aeefe9d6d542afa79badda", "size_bytes": 3331... | {"sha256": "d2748f4cedc498046100779a6f59fb1ef1e79c3049aeefe9d6d542afa79badda", "size_bytes": 3331... | `data/processed/benchmark/03_real_address_old_1500.csv` | [] |
| `INPUT_04` | core | pass | {"sha256": "46305aac4821c2f2bc96913cfaf3a89f3087dd91216f5093dc7f89b8541fc021", "size_bytes": 1600... | {"sha256": "46305aac4821c2f2bc96913cfaf3a89f3087dd91216f5093dc7f89b8541fc021", "size_bytes": 1600... | `data/processed/benchmark/04_missing_fields_800.csv` | [] |
| `INPUT_05` | core | pass | {"sha256": "6249b06941d6e89a8a731fc47d0b844ee89ed8dce5a902bfcaac13d2785ced8d", "size_bytes": 2155... | {"sha256": "6249b06941d6e89a8a731fc47d0b844ee89ed8dce5a902bfcaac13d2785ced8d", "size_bytes": 2155... | `data/processed/benchmark/06_hybrid_addresses_600.csv` | [] |
| `INPUT_06` | core | pass | {"sha256": "3f11b0d02a05922662613c460014da34f89def7da1e7e1ba6ef496aa369245fc", "size_bytes": 1494... | {"sha256": "3f11b0d02a05922662613c460014da34f89def7da1e7e1ba6ef496aa369245fc", "size_bytes": 1494... | `data/processed/benchmark/07_bidirectional_pairs_verified.csv` | [] |
| `MAPPING_SOURCE` | core | pass | {"file_name": "vietnam-sap-nhap-phuong-xa.csv", "sha256": "22bd8278cf7b3f969f255e841271f33f63f6d9... | {"file_name": "vietnam-sap-nhap-phuong-xa.csv", "sha256": "22bd8278cf7b3f969f255e841271f33f63f6d9... | `data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv` | [] |
| `MAPPING_COLUMNS` | core | pass | ["Mã phường/xã mới", "Phường/Xã mới (từ 1/7/2025)", "Tỉnh/TP mới"] | ["Mã phường/xã mới", "Phường/Xã mới (từ 1/7/2025)", "Tỉnh/TP mới"] | `data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv` | [] |
| `MAPPING_TARGET_CONFLICTS` | core | pass | 0 | 0 | `data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv` | [] |
| `BENCHMARK_CONTRACT` | core | pass | valid | valid | `src/evaluation/data_contract.py` | [] |
| `CODE_src_evaluation_adapters_libpostal_adapter_py` | core | pass | 53817addaaf5bce4312b4823137e1a7e8d7c406a27a85eb7c6c88fbc9fa289a2 | 53817addaaf5bce4312b4823137e1a7e8d7c406a27a85eb7c6c88fbc9fa289a2 | `src/evaluation/adapters/libpostal_adapter.py` | [] |
| `CODE_src_evaluation_adapters_vnadmin_adapter_py` | core | pass | 569bbbdc138224382c8d805191b7342d27311d49299c0cff2bb9d8045275fc1a | 569bbbdc138224382c8d805191b7342d27311d49299c0cff2bb9d8045275fc1a | `src/evaluation/adapters/vnadmin_adapter.py` | [] |
| `CODE_src_evaluation_scorer_py` | core | pass | ea439c543bc29212e1824a2620aa9895c883cdfdc73802df3dcbbe5d170b2cdb | ea439c543bc29212e1824a2620aa9895c883cdfdc73802df3dcbbe5d170b2cdb | `src/evaluation/scorer.py` | [] |
| `CODE_src_evaluation_data_contract_py` | core | pass | 85f65d953394d9276604d8125538a7da03c3ab23e457ba9fb40cb2910f689d83 | 85f65d953394d9276604d8125538a7da03c3ab23e457ba9fb40cb2910f689d83 | `src/evaluation/data_contract.py` | [] |
| `CODE_src_evaluation_manifest_py` | core | pass | 6e25c6d7a5ea72d346ff82e93006d75b68f255c10b3bd97d8a24d7379f3d12ce | 6e25c6d7a5ea72d346ff82e93006d75b68f255c10b3bd97d8a24d7379f3d12ce | `src/evaluation/manifest.py` | [] |
| `CODE_src_evaluation_protocol_py` | core | pass | 75ca13066d7b7289721e7b76d8345877d888c5e377e77513c273a0e653103c86 | 75ca13066d7b7289721e7b76d8345877d888c5e377e77513c273a0e653103c86 | `src/evaluation/protocol.py` | [] |
| `CODE_src_evaluation_run_artifacts_py` | core | pass | a670f7a8ada43b3702323928300d368dee05b64b27efaef81e30880de43f758b | a670f7a8ada43b3702323928300d368dee05b64b27efaef81e30880de43f758b | `src/evaluation/run_artifacts.py` | [] |
| `CODE_scripts_05_run_baseline_pilot_py` | core | pass | 8037b7c3fcfeb0c19ee1beae4136967e41aaa70a043832cef72e57651f605a25 | 8037b7c3fcfeb0c19ee1beae4136967e41aaa70a043832cef72e57651f605a25 | `scripts/05_run_baseline_pilot.py` | [] |
| `CODE_scripts_06_run_baseline_full_py` | core | pass | 5c89b65b61a1ed3eac42f83035042131767c5204da8fef8357763786391b016b | 5c89b65b61a1ed3eac42f83035042131767c5204da8fef8357763786391b016b | `scripts/06_run_baseline_full.py` | [] |
| `CODE_scripts_07_generate_baseline_report_py` | core | pass | 6eefb729ee4f859fd87dc713cc78ad2269b605fb1817ff4143da2115ab62d50f | 6eefb729ee4f859fd87dc713cc78ad2269b605fb1817ff4143da2115ab62d50f | `scripts/07_generate_baseline_report.py` | [] |
| `CODE_scripts_08_generate_report_materials_py` | core | pass | 1f23669c4cd816a33f8338647c1ae7bb064dc4c8dcb8f4a8cd939858655f27e0 | 1f23669c4cd816a33f8338647c1ae7bb064dc4c8dcb8f4a8cd939858655f27e0 | `scripts/08_generate_report_materials.py` | [] |
| `CODE_scripts_build_baseline_dashboard_py` | core | pass | 9352b15cc98d17c1bd43f00a3f985328824fb4b425d042c59215a1beec9f450a | 9352b15cc98d17c1bd43f00a3f985328824fb4b425d042c59215a1beec9f450a | `scripts/build_baseline_dashboard.py` | [] |
| `CODE_src_evaluation_reporter_py` | core | pass | cdb3e24959b4bf9b90e7d80630ddb6acdf8fae69dc78ec0e30baa7ea6f936f46 | cdb3e24959b4bf9b90e7d80630ddb6acdf8fae69dc78ec0e30baa7ea6f936f46 | `src/evaluation/reporter.py` | [] |
| `SCORING_NORMALIZATION_MATCH` | core | pass | NFC Unicode, casefold, collapse whitespace, strip surrounding whitespace and trailing comma separ... | NFC Unicode, casefold, collapse whitespace, strip surrounding whitespace and trailing comma separ... | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `SCORING_EMPTY_POLICY_MATCH` | core | pass | Ignore pairs where both values are empty; score a one-sided empty pair as 0. Report the number of... | Ignore pairs where both values are empty; score a one-sided empty pair as 0. Report the number of... | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `SCORING_DIRECTION_MATCH` | core | pass | old_to_new | old_to_new | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `SCORING_FIELDS_MATCH` | core | pass | ["PhuongXa", "TinhThanh"] | ["PhuongXa", "TinhThanh"] | `data/processed/evaluation/runs/baseline_v3_fuzzy/run_manifest.json` | [] |
| `OUTPUT_SHA_PRED` | core | pass | b1125fba3a319792ef37fce9f58728d2fa2e7b373a8855baba2b22e9d58930e0 | b1125fba3a319792ef37fce9f58728d2fa2e7b373a8855baba2b22e9d58930e0 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `OUTPUT_SHA_RAW` | core | pass | a124c05540efce4c0c92878f036414c31bfcac20f4a675e2e2b2b91415726040 | a124c05540efce4c0c92878f036414c31bfcac20f4a675e2e2b2b91415726040 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_raw_responses.jsonl` | [] |
| `PRED_COLUMNS` | core | pass | ["ID", "DiaChiGoc", "CongCu", "TruongDuDoan", "TruongDung", "DungSai", "LoaiLoi", "TinhHuongMoHo"... | ["ID", "DiaChiGoc", "CongCu", "TruongDuDoan", "TruongDung", "DungSai", "LoaiLoi", "TinhHuongMoHo"... | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `PRED_BOM` | core | pass | True | True | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `PRED_ROWS` | core | pass | 13000 | 13000 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `RAW_JSONL` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_raw_responses.jsonl` | [] |
| `RAW_ROWS` | core | pass | 13000 | 13000 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_raw_responses.jsonl` | [] |
| `EXPECTED_COUNT` | core | pass | 13000 | 13000 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `PRED_KEY_UNIQUE` | core | pass | 13000 | 13000 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `RAW_KEY_UNIQUE` | core | pass | 13000 | 13000 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_raw_responses.jsonl` | [] |
| `PRED_EXPECTED_KEYS` | core | pass | 13000 | 13000 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `PRED_UNEXPECTED_KEYS` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `RAW_PAIR_KEYS` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_raw_responses.jsonl` | [] |
| `COVERAGE_D01_libpostal` | core | pass | 1000 | 1000 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `COVERAGE_D01_vietnamadminunits` | core | pass | 1000 | 1000 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `COVERAGE_D02_libpostal` | core | pass | 2000 | 2000 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `COVERAGE_D02_vietnamadminunits` | core | pass | 2000 | 2000 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `COVERAGE_D03_libpostal` | core | pass | 1500 | 1500 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `COVERAGE_D03_vietnamadminunits` | core | pass | 1500 | 1500 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `COVERAGE_D04_libpostal` | core | pass | 800 | 800 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `COVERAGE_D04_vietnamadminunits` | core | pass | 800 | 800 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `COVERAGE_D06_libpostal` | core | pass | 600 | 600 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `COVERAGE_D06_vietnamadminunits` | core | pass | 1200 | 1200 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `COVERAGE_D07_vietnamadminunits` | core | pass | 600 | 600 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `COVERAGE_UNEXPECTED` | core | pass | [] | [] | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `INPUT_SOURCE` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `SCENARIO_SOURCE` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `PAIR_FIELDS` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_raw_responses.jsonl` | [] |
| `RAW_STATUS` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_raw_responses.jsonl` | [] |
| `RAW_STATUS_CONSISTENCY` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_raw_responses.jsonl` | [] |
| `RAW_EXCEPTION` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_raw_responses.jsonl` | [] |
| `RAW_DURATION` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_raw_responses.jsonl` | [] |
| `MODE_SOURCE` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_raw_responses.jsonl` | [] |
| `D07_DIRECTION` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_raw_responses.jsonl` | [] |
| `FIELD_JSON` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `D02_GOLD` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `D04_GOLD` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `D07_TARGET` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `OTHER_GOLD` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `D06_MODE_NOTE` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `D07_DIRECTION_NOTE` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `SCORER_REPLAY` | core | pass | 0 | 0 | `data/processed/evaluation/runs/baseline_v3_fuzzy/baseline_predictions_unified.csv` | [] |
| `DERIVED_PARENT_SHA` | derived | pass | 14da842d270d2b0e2a31efd954c07d3a0f948cc7b3d7c8240687ae7a19a46fcb | 14da842d270d2b0e2a31efd954c07d3a0f948cc7b3d7c8240687ae7a19a46fcb | `data/processed/evaluation/derived/baseline_v3_fuzzy/v4_fuzzy/comparative_analysis_tables/report_materials_lineage.json` | [] |
| `DERIVED_RUN_ID` | derived | pass | baseline_v3_fuzzy | baseline_v3_fuzzy | `data/processed/evaluation/derived/baseline_v3_fuzzy/v4_fuzzy/comparative_analysis_tables/report_materials_lineage.json` | [] |
| `DERIVED_SHA_dataset_metrics_csv` | derived | pass | 5cd1077d36db22c7b12f12300634919b3e3def05cd4b1b97aba9a3f0f8225146 | 5cd1077d36db22c7b12f12300634919b3e3def05cd4b1b97aba9a3f0f8225146 | `data/processed/evaluation/derived/baseline_v3_fuzzy/v4_fuzzy/comparative_analysis_tables/dataset_metrics.csv` | [] |
| `DERIVED_SHA_dataset_field_metrics_csv` | derived | pass | e58cdfa7923da1c028e2b081572b9a1fbef01e6032d967fff3682494873f2d3b | e58cdfa7923da1c028e2b081572b9a1fbef01e6032d967fff3682494873f2d3b | `data/processed/evaluation/derived/baseline_v3_fuzzy/v4_fuzzy/comparative_analysis_tables/dataset_field_metrics.csv` | [] |
| `DERIVED_SHA_structural_scenarios_csv` | derived | pass | 8bf1dba640d0b6f785dbb15c337fde4f0a627345b3fa0da9ceb7af5dd664b9d0 | 8bf1dba640d0b6f785dbb15c337fde4f0a627345b3fa0da9ceb7af5dd664b9d0 | `data/processed/evaluation/derived/baseline_v3_fuzzy/v4_fuzzy/comparative_analysis_tables/structural_scenarios.csv` | [] |
| `DERIVED_SHA_spatial_trace_cases_csv` | derived | pass | 42c4f5d4de0357d2d9f1f42083a3b8b0356c8d8bc38a1de6ecc93dfc0b8f64b1 | 42c4f5d4de0357d2d9f1f42083a3b8b0356c8d8bc38a1de6ecc93dfc0b8f64b1 | `data/processed/evaluation/derived/baseline_v3_fuzzy/v4_fuzzy/comparative_analysis_tables/spatial_trace_cases.csv` | [] |
| `DERIVED_SHA_spatial_trace_summary_csv` | derived | pass | a8cbdfe0b482ef53e9543f1d247acf44534c8caf39d3df86c2c58f41eabcfe49 | a8cbdfe0b482ef53e9543f1d247acf44534c8caf39d3df86c2c58f41eabcfe49 | `data/processed/evaluation/derived/baseline_v3_fuzzy/v4_fuzzy/comparative_analysis_tables/spatial_trace_summary.csv` | [] |
| `DERIVED_SHA_data06_contract_csv` | derived | pass | ce4b08ba0cbb39e0a922677142c496e85d714e352e965d8a21d73594e6e0e993 | ce4b08ba0cbb39e0a922677142c496e85d714e352e965d8a21d73594e6e0e993 | `data/processed/evaluation/derived/baseline_v3_fuzzy/v4_fuzzy/comparative_analysis_tables/data06_contract.csv` | [] |
| `DERIVED_SHA_data07_scope_csv` | derived | pass | 60b5f30e18aeee276a4ea63b4324baff7392353b6e7870d5f997f66db9b944c2 | 60b5f30e18aeee276a4ea63b4324baff7392353b6e7870d5f997f66db9b944c2 | `data/processed/evaluation/derived/baseline_v3_fuzzy/v4_fuzzy/comparative_analysis_tables/data07_scope.csv` | [] |
| `DERIVED_SHA_case_studies_csv` | derived | pass | 7efb5f36c81febc08d8c11e0537072dbb7eda013a2852f1219e58178f5498b5f | 7efb5f36c81febc08d8c11e0537072dbb7eda013a2852f1219e58178f5498b5f | `data/processed/evaluation/derived/baseline_v3_fuzzy/v4_fuzzy/comparative_analysis_tables/case_studies.csv` | [] |
| `DERIVED_SHA_baseline_diagnostics_v4_md` | derived | pass | ca85c26e9c341bbced4e1e33a18554bb246c0a3aef88f1077a84a08390ba5b75 | ca85c26e9c341bbced4e1e33a18554bb246c0a3aef88f1077a84a08390ba5b75 | `docs/runs/baseline_v3_fuzzy/v4_fuzzy/baseline_diagnostics_v4.md` | [] |
| `DERIVED_SHA_data_preparation_summary_v4_md` | derived | pass | 8e05bfd6189c361c6b013eda9b9c95fe0747641d193a5e05c8bb83862dc5d1da | 8e05bfd6189c361c6b013eda9b9c95fe0747641d193a5e05c8bb83862dc5d1da | `docs/runs/baseline_v3_fuzzy/v4_fuzzy/data_preparation_summary_v4.md` | [] |
| `DERIVED_SHA_chapter_01_research_motivation_v4_md` | derived | pass | 75789cb316b80740fa62c6b20c11865230286b58ae0ba84cabbe849704631645 | 75789cb316b80740fa62c6b20c11865230286b58ae0ba84cabbe849704631645 | `docs/runs/baseline_v3_fuzzy/v4_fuzzy/chapter_01_research_motivation_v4.md` | [] |
| `DERIVED_SHA_chapter_02_theoretical_foundation_v4_md` | derived | pass | 52eb0616194019127548a4d65677efb3ee1b8185f52a107b876191dfd7f30535 | 52eb0616194019127548a4d65677efb3ee1b8185f52a107b876191dfd7f30535 | `docs/runs/baseline_v3_fuzzy/v4_fuzzy/chapter_02_theoretical_foundation_v4.md` | [] |
| `DERIVED_SHA_report_materials_index_v4_md` | derived | pass | a217e3c7939d32af62bf106cac561ef5f303f681624e6ec3e5fd40b29faf9643 | a217e3c7939d32af62bf106cac561ef5f303f681624e6ec3e5fd40b29faf9643 | `docs/runs/baseline_v3_fuzzy/v4_fuzzy/report_materials_index_v4.md` | [] |
| `DERIVED_ARTIFACT_COUNT` | derived | pass | 13 | 13 | `data/processed/evaluation/derived/baseline_v3_fuzzy/v4_fuzzy/comparative_analysis_tables/report_materials_lineage.json` | [] |
| `SCORER_POLICY_SENTINELS` | derived | pass | True | True | `src/evaluation/scorer.py` | [] |
| `METRIC_REPLAY` | derived | pass | 0 | 0 | `data/processed/evaluation/derived/baseline_v3_fuzzy/v4_fuzzy/comparative_analysis_tables/dataset_metrics.csv` | [] |
| `METRIC_REPLAY_ROWS` | derived | pass | 31 | 31 | `data/processed/evaluation/derived/baseline_v3_fuzzy/v4_fuzzy/comparative_analysis_tables/dataset_metrics.csv` | [] |
| `FIELD_METRIC_REPLAY` | derived | pass | 0 | 0 | `data/processed/evaluation/derived/baseline_v3_fuzzy/v4_fuzzy/comparative_analysis_tables/dataset_field_metrics.csv` | [] |
| `FIELD_METRIC_REPLAY_ROWS` | derived | pass | 152 | 152 | `data/processed/evaluation/derived/baseline_v3_fuzzy/v4_fuzzy/comparative_analysis_tables/dataset_field_metrics.csv` | [] |
| `MAIN_REPORT_REPLAY` | derived | pass | 0 | 0 | `docs/runs/baseline_v3_fuzzy/baseline_evaluation_report.md` | [] |
| `FROZEN_UNCHANGED` | core | pass | True | True | `data/processed/evaluation/runs` | [] |

**Phân bố lượt theo tập và tool:**

- `D01|libpostal`: 1000
- `D01|vietnamadminunits`: 1000
- `D02|libpostal`: 2000
- `D02|vietnamadminunits`: 2000
- `D03|libpostal`: 1500
- `D03|vietnamadminunits`: 1500
- `D04|libpostal`: 800
- `D04|vietnamadminunits`: 800
- `D06|libpostal`: 600
- `D06|vietnamadminunits`: 1200
- `D07|vietnamadminunits`: 600

**Trạng thái raw log:**

- `libpostal|success`: 5900
- `vietnamadminunits|success`: 7100

**Metric tính lại từ prediction/gold (bảng dẫn xuất được so từng giá trị):**

| Tập/điều kiện | Tool | n | Exact đúng | Exact rate | Micro F1 | Fuzzy mean / số cặp |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Data 01|all | `libpostal` | 1000 | 2 | 0.002000 | 0.573781 | 0.560473 / 4775 |
| Data 01|all | `vietnamadminunits` | 1000 | 973 | 0.973000 | 0.988109 | 0.992776 / 4000 |
| Data 02|clean | `libpostal` | 1000 | 1 | 0.001000 | 0.501684 | 0.517121 / 4885 |
| Data 02|clean | `vietnamadminunits` | 1000 | 517 | 0.517000 | 0.731845 | 0.845009 / 4500 |
| Data 02|noisy | `libpostal` | 1000 | 0 | 0.000000 | 0.372255 | 0.453290 / 4766 |
| Data 02|noisy | `vietnamadminunits` | 1000 | 123 | 0.123000 | 0.511690 | 0.681414 / 4500 |
| Data 03|all | `libpostal` | 1500 | 1 | 0.000667 | 0.425749 | 0.468431 / 7500 |
| Data 03|all | `vietnamadminunits` | 1500 | 87 | 0.058000 | 0.513598 | 0.724077 / 7500 |
| Data 04|surface_parse | `libpostal` | 800 | 114 | 0.142500 | 0.448648 | 0.521352 / 2961 |
| Data 04|surface_parse | `vietnamadminunits` | 800 | 39 | 0.048750 | 0.329580 | 0.480963 / 2742 |
| Data 06|libpostal | `libpostal` | 600 | 2 | 0.003333 | 0.531125 | 0.584809 / 3000 |
| Data 06|vn_from_2025 | `vietnamadminunits` | 600 | 0 | 0.000000 | 0.604441 | 0.654718 / 3000 |
| Data 06|vn_legacy | `vietnamadminunits` | 600 | 157 | 0.261667 | 0.751238 | 0.775672 / 3000 |
| Data 07|old_to_new | `vietnamadminunits` | 600 | 586 | 0.976667 | 0.989158 | 0.993410 / 1200 |
| Data 04|KieuThieu=drop_district | `libpostal` | 99 | 2 | 0.020202 | 0.472103 | 0.557536 / 406 |
| Data 04|KieuThieu=drop_district | `vietnamadminunits` | 99 | 0 | 0.000000 | 0.026316 | 0.119888 / 405 |
| Data 04|KieuThieu=drop_housenumber | `libpostal` | 348 | 0 | 0.000000 | 0.268744 | 0.362737 / 1358 |
| Data 04|KieuThieu=drop_housenumber | `vietnamadminunits` | 348 | 39 | 0.112069 | 0.500000 | 0.760823 / 1191 |
| Data 04|KieuThieu=drop_housenumber_ward | `libpostal` | 112 | 31 | 0.276786 | 0.498155 | 0.587585 / 315 |
| Data 04|KieuThieu=drop_housenumber_ward | `vietnamadminunits` | 112 | 0 | 0.000000 | 0.220833 | 0.370018 / 301 |
| Data 04|KieuThieu=drop_ward | `libpostal` | 241 | 81 | 0.336100 | 0.649815 | 0.725260 / 882 |
| Data 04|KieuThieu=drop_ward | `vietnamadminunits` | 241 | 0 | 0.000000 | 0.212736 | 0.299087 / 845 |
| Data 06|KieuLai=C1|mode=single_parse | `libpostal` | 420 | 0 | 0.000000 | 0.513595 | 0.559858 / 2100 |
| Data 06|KieuLai=C1|mode=FROM_2025 | `vietnamadminunits` | 420 | 0 | 0.000000 | 0.592416 | 0.675778 / 2100 |
| Data 06|KieuLai=C1|mode=LEGACY | `vietnamadminunits` | 420 | 5 | 0.011905 | 0.668207 | 0.713103 / 2100 |
| Data 06|KieuLai=C2|mode=single_parse | `libpostal` | 120 | 0 | 0.000000 | 0.574091 | 0.647729 / 600 |
| Data 06|KieuLai=C2|mode=FROM_2025 | `vietnamadminunits` | 120 | 0 | 0.000000 | 0.760668 | 0.738648 / 600 |
| Data 06|KieuLai=C2|mode=LEGACY | `vietnamadminunits` | 120 | 96 | 0.800000 | 0.917241 | 0.893862 / 600 |
| Data 06|KieuLai=C3|mode=single_parse | `libpostal` | 60 | 2 | 0.033333 | 0.564007 | 0.633624 / 300 |
| Data 06|KieuLai=C3|mode=FROM_2025 | `vietnamadminunits` | 60 | 0 | 0.000000 | 0.339785 | 0.339436 / 300 |
| Data 06|KieuLai=C3|mode=LEGACY | `vietnamadminunits` | 60 | 56 | 0.933333 | 0.969900 | 0.977272 / 300 |

## Phạm vi xác minh

- Run v3 được tính lại bằng scorer có đúng SHA-256 trong manifest; báo cáo chính được tái tạo trong bộ nhớ và so nội dung trừ dòng ngày tạo. Báo cáo chính không có hash riêng trong lineage dẫn xuất.
- Runtime audit có thể khác runtime ghi trong manifest. Kiểm toán này không gọi lại Libpostal/VietnamAdminUnits, nên không xác minh tính tái lập của dịch vụ ngoài.
- Không có span gold 11 nhãn trong sáu tập này; kết luận không áp dụng cho T0 11 nhãn.
- Danh sách check đầy đủ và bằng chứng có cấu trúc nằm trong `baseline_run_audit.json`.
