# Lộ trình và prompt hoàn tất Sprint 3 — giữ cấu hình hiện tại

Ngày: 05/10/2026. Quyết định mới của chủ dự án: **giữ cấu hình hiện tại, đánh giá cuối và báo rõ hạn chế**. File này bàn giao công việc cho agent tiếp theo; các bước thực nghiệm còn thiếu chưa được chạy trong lượt tạo prompt.

## 1. Phạm vi và lộ trình

Hoàn thành hai cấu hình Deepparse còn thiếu, khóa mô hình trước khi mở scorer test, đánh giá test100, hoàn thiện track 5 trường, tổng hợp báo cáo và bàn giao GitHub.

Giữ lựa chọn HEUR-JW, CRF-INDEP, PhoBERT-CRF c02 và PROPOSED-DYN c02 đã chốt. Không mở thêm vòng cải thiện T1/Lai, đổi threshold, thêm seed hoặc huấn luyện lại hai mô hình neural này. Hai candidate Deepparse fine-tuned thuộc ngân sách đã định nghĩa nhưng chưa chạy, vẫn cần hoàn tất bằng train/dev.

Data05 địa chỉ thật có mốc/hướng vẫn `DEFERRED_BY_USER`; VQA vẫn `HOLD`; T3, RAG, FastAPI/Docker và encoder ViBERT bổ sung ngoài phạm vi lượt này. Gazetteer được bàn giao với coverage và giới hạn thực tế; không gọi toàn bộ mã cũ đã verified hoặc mọi quan hệ nhiều đích đã được phân giải.

| Giai đoạn | Công việc | Cổng chuyển bước và đầu ra |
| --- | --- | --- |
| P0 | Kiểm kê trạng thái, nguồn và tài nguyên | Protected ledger, inventory, execution policy, task tracker |
| F1 | DP-ZS-FT và DP-FT-FT thật | Resource lock, native smoke, dev evidence, checkpoint hoặc blocker cụ thể |
| F2 | Khóa nguồn mã và lựa chọn trước test | Model roster, selection locks, input-only package, preflight |
| F3 | Inference test100 và freeze trước chấm | 100 trạng thái/model, predictions, raw output, trace, latency, hash |
| F4 | Chấm T0/T1/structure và track 5 trường | Metrics, support, error analysis, overlap audit, paired ablation |
| F5 | Tổng hợp kết quả và Gazetteer | Báo cáo Sprint 3, giới hạn, trạng thái việc hoãn và hướng dẫn tái lập |
| F6 | Kiểm thử, artifact, dung lượng và GitHub | Acceptance report, storage receipt, commit/push SHA và artifact index |

Luồng chính: **P0 → F1 → F2 → F3 → F4 → F5 → F6**. Khi F1 chạy, có thể hoàn thiện bộ gom báo cáo và pipeline inference cloud bằng fixture. Chưa chấm test thật khi các lựa chọn còn mở.

Nếu Deepparse bị chặn bởi nguồn, điều kiện sử dụng hoặc tài nguyên: ghi blocker và kế hoạch cấu hình trước khi mở scorer test; khóa roster phần chạy được và hoàn thành việc độc lập. Không ghi Sprint 3 hoàn thành đầy đủ khi các cấu hình này còn thiếu thực nghiệm.

## 2. PROMPT — giao nguyên phần này cho agent

Bạn là Senior AI/Data Engineer phụ trách repository `D:\DACN`.

Thực hiện **P0 và F1–F6**: hiện thực mã còn thiếu, chạy thực nghiệm thật, kiểm tra artifact, đánh giá cuối, cập nhật tài liệu và bàn giao GitHub. Không dừng ở lập kế hoạch hoặc chỉ kiểm thử fixture.

### A. Quyết định và quyền hiện hành

1. Chủ dự án chọn **giữ cấu hình hiện tại, đánh giá cuối và báo rõ hạn chế**. Không cải thiện thêm PhoBERT-CRF/PROPOSED-DYN, T1/Lai hoặc baseline nhẹ trước test.
2. Prompt này mở **giai đoạn inference/chấm test cuối** sau các cổng F2/F3. Những câu “chưa thực thi test” trong báo cáo trước là trạng thái lịch sử. Quyền này không cho phép train, tune hoặc chọn mapping bằng nhãn test.
3. Test đã duyệt đủ100. Task695 chọn annotation694, giữ flag;16 ngoại lệ T1/structure đã được duyệt. Không yêu cầu chủ dự án gán lại hoặc mở lại quyết định này.
4. Tái dùng Kaggle account `huynq16`, runtime/API và private datasets đã có. GPU và full training thật đã được xác minh. Ưu tiên Kaggle API cho phần tài nguyên nặng; Colab là phương án chạy thay thế khi cần. Không bắt buộc huấn luyện lại checkpoint đã nghiệm thu chỉ để đổi nền tảng.
5. Chủ dự án đã cho phép cài/tải tài nguyên cần thiết sau inventory. **Mọi cài đặt, model/cache, temp và output local mới phải ở D**. Tái dùng runtime có sẵn; không thay cấu hình Python/WSL toàn máy.
6. Cài cloud trong scratch Kaggle/Colab được đo riêng. Chỉ upload tài nguyên được phép vào private dataset; ghi nguồn/revision/license/hash. Không công khai raw export/gold/answer package hoặc nguồn Gazetteer chưa đủ quyền phân phối.
7. Chủ dự án đã yêu cầu cập nhật `sprint3_huy`; tiếp tục commit/push phần được phép. Nếu GitHub chưa đăng nhập, hoàn thành commit và việc độc lập, rồi báo đúng thao tác đăng nhập cần người dùng. Không xin lại quyền push đã có.

### B. Đọc trước khi thực hiện

Đọc `AGENTS.md` hiện hành và các file sau. Đối chiếu manifest/receipt thực tế khi gặp trạng thái lịch sử khác nhau:

- `docs/data_quality.md`.
- `docs/sprints/sprint_03/model_matrix.md`.
- `docs/sprints/sprint_03/span_11_annotation_guideline.md`.
- `docs/sprints/sprint_03/17_training_protocol_v1.md`.
- `docs/sprints/sprint_03/39_kaggle_pipeline_operations.md`.
- `docs/sprints/sprint_03/43_agent_prompt_local_completion_before_colab.md` — hợp đồng còn hiệu lực.
- `docs/sprints/sprint_03/44_local_finish_resource_inventory.md`.
- `docs/sprints/sprint_03/45_local_release_and_colab_operations.md`.
- `docs/sprints/sprint_03/47_test_gold_release_and_kaggle_20261005.md`.
- `configs/evaluation/sprint03/final_test_protocol_v1.json`.
- `configs/modeling/sprint03/{tuning_protocol_v1.json,protocol_lock_v1.json,dp_ft_ft_v1.json,deepparse_resource_lock_template.json}`.
- `scripts/{23_run_span_dev,24_score_span_dev,28_run_fivefield_experiment,31_train_deepparse_finetuned,47_prepare_dp_zero_shot_config,50_kaggle_pipeline,55_run_span_test,56_score_span_test,60_download_kaggle_artifacts}.py`.
- `src/modeling/{deepparse_training,resources,cli,kaggle_handoff,kaggle_remote,kaggle_artifacts}.py`.
- `src/evaluation/{test_runner,benchmark_runner,dev_runner,span_scorer,schema}.py` và các adapter liên quan.

Evidence root hiện hành:

`data/interim/modeling/sprint03/release_and_kaggle_20261005_v1/`

Đọc `final_acceptance_receipt.json`, `release_artifact_verification.json`, `neural_dev_acceptance.json`, `neural_source_restoration_acceptance.json`, `git_completion_receipt.json`, `final_selection_v5/preflight_report.json` và `neural_evaluation_workspace_v1/final_neural_selection_v1/preflight_report.json` trong root này.

### C. Tài nguyên và lựa chọn đã khóa

**Corpus và nhãn**

- Train/dev gốc: `data/processed/annotation/sprint03/corpus_train_dev_v2/` —240/60 mẫu,1057/284 span, T1 eligible206/53.
- Manifest nguồn SHA-256: `9c91b77fa220e41b1b1067e5e99b216b7b4b2176181674b340f16dec134947bf`.
- Corpus ba split: `data/processed/annotation/sprint03/corpus_v1_release2/` —240/60/100.
- Manifest corpus SHA-256: `0abd9f01ae0b298d0ef44161e65426f9769302ebb89b8c9aa45097722b09aea8`.
- Test gold: `data/processed/annotation/sprint03/test_gold_v1_release2/` —100 mẫu/446 span.
- Manifest test SHA-256: `eb054ec5a0be324f7b16f3483b4337ca69c4dd7a1686e5ca856b496f13563222`.
- Raw round2 SHA-256: `d51b69c981e775e0e51ac3ed5a3ef4c91d845f5e7a900c2f3d4c79f98ca758a4`; không vá raw JSON.
- Test T1:64 eligible,20 null,16 excluded. Manifest tổng có17 mask kể cả543 ở dev.
- Task543: `s3_60931c369cbd85ef`; mask T1/structure, giữ toàn bộ T0.
- Test100 là `AI_ASSISTED_HUMAN_REVIEW`, agreement `NOT_MEASURED`.
- Test0 support cho `ToaNha/CanHo`, `MocDinhVi`, `HuongDi`, `GhiChu`; dev0 `MocDinhVi`/`ToaNha/CanHo`,1 `HuongDi`.

Chỉ đọc nhãn gold test tại F4 sau khi mọi prediction trong roster đã freeze. P0/F2 kiểm hash/manifest/identity/support đã công bố; không đọc lại từng annotation hoặc raw export.

**Hai baseline nhẹ**

- Locks: `data/interim/modeling/sprint03/release_and_kaggle_20261005_v1/final_selection_v5/`.
- HEUR-JW giữ threshold0.86 cùng rule/reject/gazetteer đúng config đã chọn; không sweep lại.
- CRF-INDEP giữ context1/c1=0.1/c2=1 và checkpoint đã chọn; không train lại.
- Lấy đường dẫn resource/alias/checkpoint từ config/lock; không thay Gazetteer mặc định.

**Hai mô hình neural**

- Workspace: `data/interim/modeling/sprint03/release_and_kaggle_20261005_v1/neural_evaluation_workspace_v1/`.
- Locks/config: `final_neural_selection_v1/` trong workspace đó.
- PhoBERT-CRF c02: dev T0 F1=93,89%; best SHA `19894a1e899a94c69c68bd33d091c348a7b049582090f41dc6d6a9f85b8a351e`.
- PROPOSED-DYN c02: dev T0 F1=94,74%; best SHA `7a4a3d01bff1222cd303cb5ff03872c5ee49b22cb67a0572833fa470f917a589`.
- Dyn calibration threshold0.7/margin0.2; kiểm đúng calibration/hash đã chọn.
- Ablation off dùng **`dyn_no_constraint_model_config_v2.json` và `dyn_no_constraint_selection_lock_v2.json`**; không dùng bản off không khóa từ lần dựng đầu.
- Giữ submitted source model/processor/dev và `final_inference_bridge.py` trong workspace. Không chép main mới đè lên rồi vô hiệu kiểm hash.

**Giới hạn đã chấp nhận**

- Dyn T1 dev macro-F1=59,96%,accuracy77,36%,accepted49/53; Lai support8/F1=0.
- Constraint on/off cùng checkpoint cho cùng devT0 và cùng0/14 lỗi Quận trên gold-moi eligible. Chưa chứng minh constraint gây cải thiện.
- Chỉ seed42 đã chạy. Seed1337/2025 là kế hoạch; không thêm trong lượt này hoặc báo mean/std giả.
- Gazetteer hai snapshot: báo cáo trước có8607 mã cũ exact verified,3355 mã mới,2187 mã cũ unresolved. Đối chiếu manifest thực; không suy lịch sử hiệu lực pháp lý từ hai snapshot30/06 và01/07/2025.

### D. Quy tắc dữ liệu và run

1. Giữ split, text, gold, guideline, raw exports, Gazetteer, baseline v2/v3 và run/lock đã khóa.
2. Output mới dùng run_id/thư mục mới, từ chối overwrite; seed42 cho bước có ngẫu nhiên.
3. Adapter chỉ nhận chuỗi và tài nguyên khai báo. Không dùng `GT_*`, `HeQuyChieu`, `KieuThieu`, `Span_He_Detail`, source stratum hoặc gold T1 làm feature.
4. Mỗi ID có trạng thái rõ. Runtime error/abstain không bị loại khỏi mẫu số; dùng empty scored output và status theo protocol, không tạo prediction giả.
5. T0 lưu `[start,end)` trên chuỗi nguyên bản; mọi `text[start:end]` khớp chính xác. Không lưu offset trên chuỗi đã sửa OCR/chuẩn hóa.
6. Mask T1/structure từ `evaluation_exclusions.t1` và gold null; không bỏ T0 các ID đó.
7. Không ép T1 thành `moi` vì thiếu Quận hoặc lấy hệ từ tên dataset.
8. Không đổi model/mapping/calibration/threshold sau xem score test để tăng điểm.
9. Lỗi kỹ thuật phải được chứng minh bằng fixture không dùng gold test; giữ run lỗi, ghi tác động và chạy run mới. Sửa làm thay đổi mô hình sau xem test phải được ghi như lần đánh giá sau phát hiện lỗi, không gọi lại là test độc lập ban đầu.
10. Cập nhật tài liệu trạng thái; không sửa manifest/metrics/receipt/run frozen.

### P0 — Kiểm kê và chốt execution policy

1. Kiểm git status, nhánh/remote và checkout bàn giao; không reset/clean/stash hàng loạt hoặc switch main đang có thay đổi của người khác.
2. Kiểm hash corpus, checkpoint/calibration/locks, resource paths và file bắt buộc. Lập bảng `PASS/BLOCKED/MISSING`.
3. Kiểm WSL/Python, RAM host, GPU/VRAM cloud và đĩa D/cloud. Dùng `bash --noprofile --norc`; đặt `TMPDIR`, pip/HF/XDG/cache local mới trên D và tắt bytecode khi đọc source frozen.
4. Tạo evidence root duy nhất, ví dụ `data/interim/modeling/sprint03/final_completion_<date>_v1/`, ngày theo Asia/Saigon.
5. Ghi inventory **trước cài/tải/upload**: package/version/source; model/revision/license; bytes dự kiến, RAM/đĩa, vai trò, vị trí local/cloud. Terms chưa rõ có status riêng.
6. Protected ledger kế thừa `frozen_before.json`1313hash+4rawsize/mtime và bổ sung release2/selected artifacts/locks/source workspace hiện hành; audit trước/sau.
7. Ghi `execution_policy.json`: quyết định giữ mô hình, budget DP còn lại, phương pháp chọn, resource/code identities, gold access stage, phạm vi hoãn.
8. Task tracker P0/F1–F6 có outputs, dependency, status, blocker và evidence path.

Đầu ra: state ledger, inventory, execution policy, tracker và audit đầu lượt.

### F1 — Hoàn tất thực nghiệm Deepparse thật

**F1.1. Nguồn và tài nguyên**

1. Kiểm tài liệu/API/code/model card chính thức của pinned Deepparse: nguồn embedding/checkpoint, revision, URL, license/attribution/redistribution terms, file cần nạp và dung lượng.
2. Tài liệu trước nêu full `cc.fr.300.bin` và checkpoint ứng viên `deepparse/fasttext-base` revision `908f403d0432a8e650da41e08d01bd33d77ac47f`. Xác minh upstream; đây chưa phải tài nguyên mặc định đã cleared.
3. Không suy license weights từ MIT repo. Không đổi sang embedding Việt/rút gọn hoặc BPEmb dưới ID FastText. Nếu cần phương án khác, trình bày ID/điều kiện và phần ma trận bị thiếu.
4. Đo host dự định chạy; không coi RAM local3.64GiB là giới hạn cloud. Gate trước yêu cầu >=10GiB host RAM; thêm ngân sách peak thực/đĩa giải nén/checkpoint. GPU không thay RAM host khi nạp full FastText.
5. Đủ nguồn/terms/tài nguyên thì ghi inventory, tải đúng nơi khai báo, lưu legal/source evidence/hash và tạo resource lock mới.
6. Không đủ thì ghi bước lỗi, URL/ngày/revision/HTTP hoặc RAM/space thực, phạm vi ảnh hưởng và thao tác cụ thể cần owner. Không fake license/kích hoạt config blocked.

**F1.2. Native integration và smoke**

1. Kiểm constructor/retrain/ListDatasetContainer, preprocessing, EOS/tag dictionary, tensor dimensions, validation split và offline loading trên package pin.
2. Tái dùng `src/modeling/deepparse_training.py`, sửa phần chưa đúng API bằng meaningful tests. Không thay bằng CRF khác rồi gọi Deepparse fine-tuned.
3. Custom dictionary: BIO23 +EOS, native24tags. Kiểm số class, EOS, output length, unknown tags, raw alignment.
4. Train/dev đúng240/60; native API không tự chia train thay dev đã khóa. Derivative mới phải bảo toàn text/span corpus.
5. Chạy pretrained smoke thật trên một phần train: forward/backward, save/reload, prediction alignment; tiny/fixture không thay full dev metric hoặc dùng chọn candidate.
6. Phân biệt `SMOKE_PASS`, `NATIVE_INTEGRATION_PASS`, `TRAINING_COMPLETE` và metric accepted; có code không đủ chứng minh.

**F1.3. DP-ZS-FT**

1. Dùng pretrained FastText, không fine-tune. Khóa mapping native→schema toàn cục; không theo từng mẫu/gold test.
2. Lưu native tags/segments trước mapping. Tag rộng như Municipality/Unit cần rule đủ bằng chứng từ output/input.
3. Kiểm token→raw char alignment, Unicode/dấu/punctuation/repeated substring; abstain khi match mơ hồ.
4. Có span đáng tin thì infer dev60, freeze rồi chấm subset/full11. Không có thì T0 `UNSUPPORTED`, vẫn chạy track 5 trường theo native field contract nếu hợp lệ; không tạo span giả để qua runner.
5. Nếu runner5fields chỉ nhận span, thêm đường native-field rõ ràng với regression, giữ text-only; không cho T0unsupported chặn một kết quả5fields hợp lệ.
6. Khóa resource/mapping/code trước test. T1 `NOT_IMPLEMENTED` nếu không có head.

**F1.4. DP-FT-FT**

1. Dùng `configs/modeling/sprint03/dp_ft_ft_v1.json`: c01 lr0.01,c02 lr0.005,seed42,max20epoch,patience5,effective batch16; đối chiếu file pin trước chạy.
2. Train thật từng candidate từ pretrained base trên240train, chọn bằng60dev; giữ seq2seq dimensions và chỉ đổi projection customtags đúng integration.
3. Chọn full11 exact-span microF1 → gold-supported macroF1 → earlier epoch → earlier candidate. Hoàn thiện callback patience/selection metric dự án trước full run.
4. Khóa budget/device profile trước train; không thêm candidate sau score test.
5. Lưu native/raw output, config, train/dev/resource/code/hash, alignment diagnostics, best checkpoint, logs, dev predictions/scoring, latency.
6. Native optimizer resume chưa hỗ trợ thì ghi `UNSUPPORTED`; weight file không chứng minh resume đầy đủ. Weights restart là run mới có provenance.
7. Download cloud bằng script60/streaming, version cụ thể, chunks/size/hash/path/disk/retry gate. Không dùng eager buffer nhiềuGB hoặc gọi file remote-only là local verified.

Đầu ra F1: resource inventory/lock, nguồn/legal evidence, native smoke, DP-ZS dev, DP-FT c01/c02 và selected checkpoint; hoặc blocker từng model có scope thiếu.

### F2 — Khóa roster và gói đánh giá cuối

1. Roster6 ID: `HEUR-JW`, `DP-ZS-FT`, `DP-FT-FT`, `CRF-INDEP`, `PHOBERT-CRF`, `PROPOSED-DYN`; thêm `PROPOSED-NO-CONSTRAINT` cùng checkpoint.
2. Mỗi ID: `READY`, `T0_UNSUPPORTED_5FIELD_READY` hoặc `BLOCKED`, kèm evidence. Ghi phần thiếu trước scorer. Bốn neural full runs là hai model×hai candidate.
3. Hoàn thiện DP/runner/report code trước snapshot cuối. Nếu global code identity đổi, tạo lock nhẹ mới từ **cùng dev evidence/cùng lựa chọn**, ghi diff và assert resource/threshold/checkpoint không đổi. Không rewrite v5/chọn lại bằng test.
4. Neural giữ workspace submitted source; orchestration mới nằm ngoài source model/processor đã pin. Cloud giữ path tương đối/resource hash và preflight lại.
5. Locks DP dùng evidence train/dev thật; zero-shot resource/mapping không dựa test. Helper chưa hỗ trợ zero-shot/T0unsupported thì thêm contract rõ/test; không giả dev score.
6. Khóa span/native→5fields, decoder/calibration, supported_labels, EOS/BIO/reject policies và runtime/code trước cả hai track; không sửa projection sau xem GT5fields.
7. Training DP package chỉ240/60; không100test/raw/gold100.
8. **Final-inference package riêng** chứa100sample_id/text, selected checkpoint/config/resource và selection evidence cần preflight. Không gold100/rawexports/GT benchmark/credentials. Dev selection evidence chỉ được gate đọc, không vào adapter.
9. Không sửa guard scripts50/51 để nhét100test vào training. Tái dùng tầng API/credential/download và tạo entry point inference riêng nếu chưa có.
10. Preflight đủ100input/modelT0 và offset contract. Neutral smoke dùng train/example công khai, không gold test.
11. Freeze `pre_test_model_roster.json` và `pre_test_freeze_manifest.json` với locks/checkpoint/resource/code SHA, policies/support/blockers trước F3.

Đầu ra F2: roster/locks, input-only package/manifest, entry point cloud nếu cần, preflight; gold scorer ZIP riêng.

### F3 — Inference test100 và freeze trước chấm

1. Baseline nhẹ dùng runtime/main snapshot đúng lock; neural dùng workspace đã khôi phục. Không vô hiệu hash vì chạy sai source tree.
2. Tái dùng script55 `infer --execute-final-test`, output directory mới trong scope cho phép. Remote entry point phải gọi cùng primitive/guard và giữ manifest contract.
3. Feed100sample_id/text; model tự dự đoán span/T1. Metadata hệ/stratum/exclusions không vào adapter.
4. Model/variant hỗ trợT0 cần đúng100ID, không duplicate/extra/missing. Kiểm raw text hash, offset/label/overlap, status, supported_labels, latency, native/candidate trace.
5. ModelT0unsupported không tạo fake100span output; ghi status track rõ. Model hỗ trợT0 có lỗi vẫn đủ100status, empty spans+abstain theo protocol.
6. DYN on/off cùng checkpoint/calibration/tokenizer/source, chỉ constraint flag khác. Ghi hash chứng minh cùng trọng số.
7. Lưu prediction/raw output/inference manifest/config/lock/input/resource/code hashes; chỉ ghi `TEST_PREDICTIONS_FROZEN` sau kiểm count/schema/hash.
8. Thu và kiểm tất cả prediction trong roster chạy được, gồm ablation. **Không chấm một model rồi điều chỉnh model khác đang chưa freeze.**
9. API `COMPLETE` cần artifact nội dung/hash gate; kernel/CLI/download lỗi có evidence. Resume transfer bằng output mới/cached files khớp fresh version index, không tải latest vô tình.

Ví dụ script55 cho PhoBERT-CRF, chạy từ ROOT của **neural workspace đã khôi phục**. Thay runtime/output ID theo thực tế; dùng đúng config/lock:

```bash
python -m scripts.55_run_span_test preflight \
  --model-config final_neural_selection_v1/pcrf_model_config.json \
  --input final_input_only/test_input.jsonl \
  --corpus-manifest final_input_only/manifest.json \
  --selection-lock final_neural_selection_v1/pcrf_selection_lock.json

python -m scripts.55_run_span_test infer \
  --model-config final_neural_selection_v1/pcrf_model_config.json \
  --input final_input_only/test_input.jsonl \
  --corpus-manifest final_input_only/manifest.json \
  --selection-lock final_neural_selection_v1/pcrf_selection_lock.json \
  --output-dir data/processed/evaluation/sprint03/pcrf_final_test_run001 \
  --execute-final-test
```

Đây là ví dụ flags đã có. Kiểm `--help`, actual paths, source identity và output chưa tồn tại trước chạy. Tạo lệnh riêng cho từng model/variant; không dùng đường PhoBERT cho DP/baseline nhẹ.

Đầu ra F3: prediction đủID, manifests/hash và frozen receipt của toàn bộ roster chạy được, chưa đọc gold test để chấm.

### F4 — Chấm cuối và track 5 trường

**F4.1. Test T0/T1/structure**

1. Sau F3 freeze đủ roster, mở scorer-only gold. Tái dùng script56/scorer dự án; không thay định nghĩa metric theo kết quả.
2. T0 đủ100mẫu: exact-span P/R/F1 micro, macro theo policy, per-label TP/FP/FN/support và supported-label coverage. Unsupported gold ở model subset vẫnFN trong full-schema score.
3. Nhãn0support: giữ raw scorer metric/policy để tái lập, annotate `NOT_EVALUABLE_NO_GOLD_SUPPORT`; không diễn giải F1=0 hoặc không có lỗi như một phép đo chất lượng thật.
4. T1 chỉ64testeligible theo manifest/null mask; kiểm counts64/20/16. Model không có headT1 ghi `NOT_IMPLEMENTED`, metric null; không loại reject khỏi score chính.
5. Báo T1accuracy/macroF1/per-class confusion/support, abstain, acceptedcoverage/acceptedaccuracy với denominator rõ. Giữ kết quả `Lai` yếu trong báo cáo.
6. Structure mask cùngT1: lỗi Quận trên eligible gold `moi` không có goldQuanHuyen, numerator/denominator cụ thể; recallQuanHuyen trên `cu`/`Lai` nếu đủ support. Mẫu số0 thìnull, không giả0%.
7. Ablation on/off cùng checkpoint: paired deltaF1/districtFP, số mẫu/span thay đổi vàT1/abstain. Nếu giống nhau, báo không quan sát cải thiện. Không so77,5% từ run/track khác khi chưa chứng minh cùng điều kiện/mẫu số.
8. Phân tích lỗi boundary/label/adminlevel/T1/abstain/runtime/OCR/source để giải thích; không quay lại train/tune trong cùng release từ lỗi test.
9. Lưu metrics, scoring manifest/scorer version/hash, error analysis và recomputation evidence. Preview debug khác thứ tự do set thì kiểm event content/numeric counts; không sửa prediction/cloudmetric để ép khớp.

Ví dụ script56 sau freeze; `GOLD_PATH` phải là file gold release2 tại nơi scorer đọc được, không có mặt trong job inference. Scorer chạy trong đúng source layout có run manifest/resource paths:

```bash
python -m scripts.56_score_span_test \
  --run-dir data/processed/evaluation/sprint03/pcrf_final_test_run001 \
  --gold "$GOLD_PATH" \
  --input final_input_only/test_input.jsonl \
  --corpus-manifest final_input_only/manifest.json \
  --execute-final-test
```

Không copy gold vào workspace inference trước F3 chỉ để script này có đường dẫn. Chuẩn bị scorer workspace hoặc đưa prediction/layout về máy scorer sau freeze và kiểm lại hash.

**F4.2. Track 5 trường**

1. Tái dùng script28/benchmark_runner.py với benchmark01/02/03/04/06 và identity hold manifest. Data07 thuộc T2, không đưa vào F1 span/5 trường.
2. Giữ việc loại100hold bằng source_row-2 và text hash; không đưa chúng trở lại benchmark sau khi có gold. Số4800 là evidence trước, phải kiểm actual count/hash.
3. Chạy phần neural/DP còn thiếu, cùng ablation nếu protocol yêu cầu. Tái dùng light runs frozen khi cùng input/mode/projection; run mới không overwrite hoặc tune lại.
4. Input chỉ ChuoiDiaChi; mapping/projection đã khóa. Freeze prediction trước chấm GT. Oracle baselinev3 nằm ở bảng riêng vì quyền truy cập input khác.
5. **Audit overlap train/dev với benchmark5fields** bằng source/group/normalized-text identities đã đăng ký. Corpus lấy từ benchmark nên các hàng có thể chứa mẫu hoặc họ mẫu đã được huấn luyện.
6. Báo toàn track là development/compatibility comparison, cùng counts/metrics seen_train, seen_dev, unseen_group khi nguồn đủ. Không gọi toàn bộ là independent test.
7. Nhóm unseen_group phải có cùng input subset cho mọi model, hash/ID list và report dẫn xuất mới. Không sửa CSV benchmark/split corpus. Thiếu group provenance thì UNKNOWN_OVERLAP, không tự chứng nhận độc lập.
8. Báo exact whole-record, micro/macro/per-field F1, coverage/abstain, lỗi QuanHuyen và latency. Projection lấy literal; không canonical repair hoặc impute gold.
9. T0/T1test100 và 5-field development có bảng riêng; không trộn metric, sample count hoặc support.

Đầu ra F4: test metrics từng model/variant, paired ablation, error analysis, 5-field metrics/runs, overlap report và scoring hashes.

### F5 — Tổng hợp Sprint 3 trong phạm vi đã chốt

1. Tạo bảng6model: pretrained/train status, checkpoint/source, modes, supported labels, devT0, testT0, testT1, trạng thái5fields, coverage, latency và blocker/evidence.
2. Báo cáo giải thích mục tiêu, corpus240/60/100, annotation mode, quy trình freeze, điều kiện so sánh, kết quả chính, ablation, dạng lỗi và giới hạn thực tế.
3. Ghi T1/Lai yếu, một seed, nhãn ít/0support, test AI-assisted/IAA NOT_MEASURED, provenance kết hợp chưa xác minh, train overlap trong5fields và Gazetteer/redistribution terms còn thiếu.
4. Không tuyên bố0ảo giác mọi trường hợp từ0/N hoặc constraint rule. Fixture/native code không thay pretrained experiment.
5. Nghiệm thu hồ sơ Gazetteer hiện hành read-only: số entity/edge/alias/non-atomic, coverage verified/unverified, đầy đủ khóa cha cũ, multiple-target lookup, dated snapshots, source/legal manifest và thiếu geometry. Không promote2187mã cũ hoặc ép1-N/M-N bằng suy đoán.
6. T2module/metric nếu đã có thì báo riêng vớiData07; chưa chạy thì NOT_EXECUTED/OUT_OF_CURRENT_MODELING_SCOPE. Gazetteer lookup không thay thực nghiệm T2.
7. Ghi Data05 DEFERRED_BY_USER, VQA HOLD, IAA NOT_MEASURED. Không tạo dữ liệu quan sát hoặc quyền sử dụng giả để đánh dấu hoàn thành.
8. Cập nhật README, docs/data_quality, Sprint3index và AGENTS current status. Giữ báo cáo cũ có ngày làm lịch sử; chỉ rõ current release/run receipt.
9. Báo cáo gợi ý: docs/sprints/sprint_03/49_sprint3_final_results.md và 50_sprint3_reproduction_and_handoff.md. Nếu tên đã có, dùng suffix/version mới; không overwrite báo cáo frozen.
10. Artifact index có path/bytes/hash/license/sharing scope và commands/runtime. Weights/gold/interim ngoàiGit phải bàn giao private riêng; cloneGit không được coi là đủ để inference.

Đầu ra F5: results index có thể đọc bằng chương trình, reportMarkdown, bảng/figure từ metrics đã kiểm, hướng dẫn tái lập, Gazetteer acceptance/limits và danh sách việc hoãn.

### F6 — Kiểm thử, artifact, dung lượng và Git

**Kiểm thử và artifact**

1. Thêm meaningful tests cho logic mới/đã sửa: nativeAPI/alignment/EOS, resource gate, final package không gold100, locks/source paths, maskT1 giữT0,100ID đầy đủ, mẫu số runtime error,5-field overlap và result aggregation.
2. Không thêm test mirror implementation cho chỉnhMD đơn giản. Fixture không thay GPU/pretrained smoke/full-run acceptance.
3. Chạy suite theoAGENTS trongWSL/runtime phù hợp, TMPDIR/cache ghiD. Báo đúng tổng PASS/SKIP/FAIL cuối, không cộng suite chồng lặp.
4. Audit protected ledger, raw/gold/split/Gazetteer/run cũ và selected artifacts; không sửa frozen file vì newline/serialization.
5. Audit prediction/scoring/config/lock/checkpoint/source/resource/code hashes, ID completeness, latency schema, overlap report, metric recompute và cùng-checkpoint ablation.
6. Script57 main() cũ có hardcoded stage fields về training/download. Tái dùng hàm read-only hoặc thêm version-aware auditor/test để báo đúng thực tế.

**Dung lượng**

1. Ghi baseline bytes của roots lượt mới trước ghi; đo environment/cache/resource/download/log/ZIP/checkpoint mới theo từng nhóm sau ghi.
2. Báo bytes, GB=bytes/1e9, GiB=bytes/2**30, disk-free before/after và phương pháp đo. Khử trùng hardlink/inode, không tính resource cũ thành install mới.
3. Tách local install, local downloaded artifact, cloud install/cache, logical artifact và allocated disk nếu có đo. Số23.296.355.884bytes ởreport47 là snapshot lượt trước.
4. Không xóa frozen checkpoint/gold/run hoặc phần tải dở lịch sử để tăng chỗ trống. Nếu thiếu đĩa, ghi ảnh hưởng/bytes cần và phương án cloud/private outputs; không đổ cacheC.

**Git**

1. Kiểm checkout bàn giao data/interim/modeling/sprint03/local_finish_before_colab_20261004_v2/git_handoff, nhánh sprint3_huy. HEAD được ghi cuối là f0dce57, remote khi đó9c03785; kiểm thực tế thay vì suy từ receipt cũ.
2. Giữ main/partner print3_label100test. Không stage toàn workspace đang dirty; dùng explicit allowlist code/config/tests/docs và review diff. Không gold/raw/answers/interim/venv/cache/weights/nguồn chưa cleared.
3. Commit/push origin sprint3_huy bằng credential hiện có, kiểm remoteSHA thật. Không force-push hoặc báo GitHub đã nhận vì có local commit.
4. GitHub chưa auth: báo Credential Manager cần người dùng đăng nhập, đưa đúng command từ checkout bàn giao; không yêu cầu token qua chat. Hoàn thành việc độc lập trong lúc chờ.
5. Không tạoPR hoặc nhắn partner khi chưa có yêu cầu; bàn giao qua chat/file.

Đầu ra F6: acceptance report, test evidence, frozen audit, storage receipt, artifact index, Git receipt và commit/push thực.

### E. Nghiệm thu và báo cáo kết thúc

Tạo sprint3_completion_manifest.json trong evidence lượt mới, gồm:

- P0/F1–F6 status và evidence path.
- Roster6ID+ablation, status/track/support và selection hash.
- T0/T1/5-field result paths,100counts/masks, score/prediction hash và policy không test tuning.
- Gazetteer coverage/limits và trạng thái Data05/VQA/IAA/T2/T3.
- Test/audit thực, model/package inventory, storage bytes/GB/GiB.
- Git branch/localSHA/remoteSHA/push status.
- Blockers và thao tác thật sự cần owner.

Trạng thái kết thúc:

1. SPRINT3_COMPLETE_WITH_DECLARED_LIMITS: cả6configuration có experiment đúng track; T0unsupported có bằng chứng và5fields thật có metric; test/predictions/report/audit/handoff đầy đủ. Giữ phạm vi Data05/VQA đã hoãn và giới hạn Gazetteer/T1/support trong báo cáo.
2. SPRINT3_PARTIAL_DP_BLOCKED: DP còn thiếu experiment native/pretrained/training. Hoàn thành phần chạy được, ghi đúng remaining tasks; không gọi complete vì fixturePASS.
3. Model/evaluation đủ nhưng push bị auth: ghi kỹ thuật đã nghiệm thu cùng GIT_PUSH_BLOCKED_AUTH; không gọi GitHub handoff hoàn thành.

Kết thúc phải báo ngay trong chat, đủ hiểu mà không cần đọc log:

1. Đã hoàn thành gì, còn thiếu gì và current status thật.
2. Bảng P0/F1–F6: việc đã làm, evidence, test/artifact, blocker và path clickable.
3. Bảng6model: dev/testT0,T1,5fields,support/status. Bốn full run neural cũ là hai model×hai candidate.
4. Giới hạn T1/Lai, ablation, zero-support, một seed, AI-assisted, provenance, overlap và Gazetteer.
5. Package/model đã cài/tải, source/revision/license và bytes/GB/GiB; nếu0 ghi0.
6. Trouble và cách xử lý; không dump credentials/signedURLs hoặc gán lỗi runtime là điểm mô hình.
7. Commit/pushSHA thật và thao tác owner. Không cần owner gán/sửa label thì ghi rõ.

Kiên trì hoàn thành phần đã được phép/có tài nguyên. Gặp blocker cụ thể thì giữ evidence và tiếp tục việc độc lập; không tạo prediction/metric/nguồn/license giả.

## 3. Lời dẫn để gửi agent

```text
Bạn là Senior AI/Data Engineer phụ trách repository D:\DACN.

Đọc toàn bộ file:
docs/sprints/sprint_03/48_agent_prompt_finish_sprint3_final_evaluation.md

Thực hiện P0 và đầy đủ F1–F6 trong phần PROMPT.
Chủ dự án đã chốt giữ cấu hình hiện tại, đánh giá cuối và báo rõ hạn chế.
Hoàn tất Deepparse còn thiếu, khóa mô hình, chạy inference/chấm test theo gate,
hoàn thiện track 5 trường, báo cáo Sprint3, kiểm thử/artifact/dung lượng và GitHub.
Không dừng ở lập kế hoạch hoặc fixture; giữ corpus, split, gold và run frozen.
Mọi cài đặt/cache/output local mới ở D sau inventory; báo bytes/GB/GiB.
Kết thúc báo P0/F1–F6 và kết quả từng model ngay trong chat.
```
