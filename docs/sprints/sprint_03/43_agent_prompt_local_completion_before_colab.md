# Prompt giao agent: hoàn thiện local trước khi chạy Colab

## Cách giao việc

Gửi agent lời dẫn ở cuối file và yêu cầu đọc **toàn bộ phần PROMPT**. Prompt này giao việc hiện thực L1–L5 trong [kế hoạch42](42_remaining_local_then_colab.md). Giai đoạn thực nghiệm trên Colab là lượt tiếp theo; lượt local này chưa chạy cloud hoặc chấm mô hình trên 100 test.

Nếu chưa có export sửa vòng mới, agent vẫn phải triển khai publisher, runner/scorer, kiểm thử fixture, resource audit và gói Colab độc lập. Phát hành gold thật chờ đủ bằng chứng duyệt; không gọi candidate thiếu mẫu là gold.

---

# PROMPT

Bạn là Senior AI/Data Engineer phụ trách hoàn thiện pipeline local Sprint 3 trong repository `D:\DACN`.

## A. Mục tiêu và phạm vi

Thực hiện **P0 và đầy đủ L1–L5**:

1. L1: QA export test100 mới và chuẩn bị/chốt phán quyết có bằng chứng.
2. L2: hiện thực công cụ phát hành test gold và corpus ba split; phát hành dữ liệu thật khi L1 qua cổng.
3. L3: hiện thực hạ tầng final-test inference/scoring và protocol, kiểm bằng fixture.
4. L4: hoàn chỉnh resource audit và gói Colab mới có đủ phụ thuộc.
5. L5: kiểm thử, audit artifact, cập nhật tài liệu và bàn giao Git.

**Phải hiện thực mã, chạy kiểm thử, kiểm artifact và tạo đầu ra**, không dừng ở kế hoạch hoặc giải thích.

Lượt này làm local. Chưa submit job Kaggle, chạy notebook Colab, huấn luyện thực nghiệm neural hoặc inference/chấm mô hình trên test100 thật. Các notebook/cell cho bước cuối phải được chuẩn bị đầy đủ nhưng mặc định tắt thực nghiệm.

Test100 được đọc để **QA annotation, phán quyết, kiểm split và phát hành gold**. Quyền này không cho phép dùng nhãn, địa chỉ hoặc kết quả rà test để chọn feature, threshold, mapping, checkpoint, candidate, prompt mô hình hoặc alias gazetteer.

## B. Đọc trước khi sửa

Đọc toàn bộ các tài liệu hiện hành:

- `AGENTS.md`, `README.md`, `docs/data_quality.md`.
- `docs/sprints/sprint_03/41_test100_export_qa_20261004.md`.
- `docs/sprints/sprint_03/42_remaining_local_then_colab.md`.
- `docs/sprints/sprint_03/37_test100_ai_assisted_annotation.md`.
- `docs/sprints/sprint_03/span_11_annotation_guideline.md`.
- `docs/sprints/sprint_03/model_matrix.md`.
- `docs/sprints/sprint_03/t0_corpus_split_protocol_v1.md`.
- `docs/sprints/sprint_03/17_training_protocol_v1.md`.
- `docs/sprints/sprint_03/28_phobert_alignment_tone_relocation_20261003.md`.
- `docs/sprints/sprint_03/33_pre_colab_resource_inventory.md`.
- `docs/sprints/sprint_03/35_pre_colab_acceptance.md`.
- `docs/sprints/sprint_03/36_label100_and_colab_handoff.md`: hồ sơ cũ; chính sách gán test hiện hành theo báo cáo37/41.

Đọc hợp đồng dữ liệu và nơi sử dụng:

- `data/processed/annotation/sprint03/corpus_train_dev_v2/manifest.json`, `coverage.json`.
- `data/interim/annotation/sprint03/test100_assisted_v1/manifest.json`.
- `data/interim/annotation/sprint03/test100_review_20261004_v3/`: acceptance, review summary, structure QA, manual findings và owner actions.
- `data/interim/annotation/sprint03/test100_review_20261004_v2/equivalent_annotation_selection*.json`.
- `data/interim/annotation/sprint03/test_hold_manifest_v1.json`.
- Queue, split assignment và quyết định gần trùng được manifest đã duyệt tham chiếu.
- `configs/modeling/sprint03/{protocol_lock_v1,tuning_protocol_v1}.json`.
- Model configs, native Deepparse mapping, hardware profile trong `configs/modeling/`, `configs/colab/`.
- Resource lock thực và resource template; phân biệt rõ hai loại.

Đọc code trước khi tái sử dụng/refactor:

- `scripts/17_convert_span_annotation_batch.py`, `18_audit_corpus_split.py`, `53_qa_test100_annotation.py`.
- `src/data/{annotation_release,test_assisted_annotation,test_annotation_qa}.py`.
- `src/evaluation/{schema,span_scorer,dev_runner,benchmark_runner}.py` và các adapter.
- `src/modeling/{datasets,alignment,labels,protocol,resources,cli,artifacts,colab_handoff}.py`.
- Scripts30–35, scripts42–48 và notebook Colab hiện có.
- Code Kaggle handoff/remote: chỉ tham khảo các hàm đóng gói, dependency và smoke đã có; không gọi API Kaggle trong lượt này.

Tái sử dụng thành phần đã đúng. Nếu thêm script mới, kiểm số/tên chưa được dùng. Các script54–57 dưới đây là gợi ý, không giả định chúng đã tồn tại.

## C. Trạng thái chuẩn để đối chiếu

### Train/dev đã phát hành

Thư mục: `data/processed/annotation/sprint03/corpus_train_dev_v2/`.

- 240 train / 60 dev, 1.057 / 284 span.
- Schema `s3-span-v1.1`.
- Manifest SHA-256:

  `9c91b77fa220e41b1b1067e5e99b216b7b4b2176181674b340f16dec134947bf`.

- T1 eligible: 206 train / 53 dev.
- Ngoại lệ `s3_60931c369cbd85ef` — task543: mask T1 theo manifest trong training, T1 scoring và chẩn đoán cấu trúc; giữ toàn bộ T0.
- Alignment PhoBERT thật đã có bằng chứng **300/300**; không quay về kết luận 217/240 + 54/60 của báo cáo cũ.
- Dev có 0 span `MocDinhVi`, 0 span `ToaNha/CanHo`, 1 span `HuongDi`; báo giới hạn support.

### QA test gần nhất là dữ liệu lịch sử của round1

File: `data/interim/annotation/sprint03/exports/test_assisted_v1/test100_assisted_round1.json`.

SHA-256: `ad11f44c5fb6d628e06bfcd82a9e307bb21b3851523a3349881f795ed338ca4c`.

- Raw có 99 task / 102 annotation.
- Sau chọn hai cặp trùng tương đương ở task602/653: 98 candidate hợp lệ cấu trúc, 1 missing, 1 multiple.
- Missing: `s3_7d9d2bd6ff632625`.
- Task695: annotation694 có `temporal_ambiguity`; annotation695 không có cờ. Chưa có lựa chọn cuối.
- Task663: `Lê Đại Hành` ở Hà Nội đang hệ mới; nguồn hai snapshot hỗ trợ hệ cũ.
- Task664: T1 `Lai` chưa có bằng chứng thành phần mới.
- 14 task cần căn cứ T1: 602, 603, 609, 611, 613, 615, 617, 620, 621, 623, 629, 630, 633, 665.
- Task683: `privacy_review` chưa có lý do cụ thể.
- Test theo **AI-assisted human review**, không còn là blind độc lập; IAA `NOT_MEASURED`.

Đây là trạng thái tại lúc viết prompt. **P0/L1 phải tìm và QA export thực tế mới nhất**, không áp kết luận cũ khi chủ dự án đã sửa. Không chọn file chỉ vì mtime lớn nhất; kiểm đúng project/phạm vi100, schema, hash và vòng xuất. Nếu người dùng cập nhật lại tên file cũ, snapshot hash mới vào thư mục mới và ghi nguồn; không sửa snapshot cũ.

### Baseline và tài nguyên

- HEUR-JW dev F1 88,01%; CRF-INDEP dev F1 90,56%, T1 `NOT_IMPLEMENTED`.
- Gazetteer hiện hành `s3_v4_nso_dual_snapshot_release2`: hai snapshot, không suy interval pháp lý; phần thiếu bằng chứng giữ unverified.
- Deepparse full native FastText/checkpoint vẫn có resource/source/license gate chưa hoàn tất. Có code không đồng nghĩa đã chạy pretrained.
- Lượt QA trước: 215 test = 207 PASS + 8 SKIP; 550 hash frozen + 4 raw size/mtime không đổi; 0 cài mới. Đây không phải kết quả kiểm thử của lượt bạn đang thực hiện.

## D. Quy tắc bắt buộc

1. Giữ nguyên `data/raw/`, `third_party/`, raw Label Studio export, canonical gold đã duyệt, split/assignment, gazetteer và run frozen.
2. Tạo output/run/release version mới; từ chối ghi đè. Không đổi 100 ID/text hoặc bỏ mẫu khó để đạt PASS.
3. Sửa annotation thật tại Label Studio rồi export mới. Không vá JSON/gold bằng code, không copy prediction thành annotation để bù mẫu thiếu.
4. Không đọc `GT_*`, chuỗi sạch, `HeQuyChieu`, `KieuThieu`, `Span_He_Detail` để quyết định test gold hoặc inference. Các prediction hỗ trợ chỉ được đọc trong QA provenance, không dùng để đánh giá chính mô hình gợi ý.
5. Adapter inference chỉ nhận raw text và tài nguyên khai báo. Source/group/system gold/trace sinh dữ liệu là sidecar, không phải feature inference.
6. Offset theo chuỗi nguyên bản `[start,end)`, khớp literal substring; không sửa OCR/Unicode của gold để vượt alignment gate. Dùng schema 11 nhãn, không overlap; mỗi span gold có hệ hợp lệ; `QuanHuyen` luôn `cu`.
7. T1 toàn câu `cu`/`moi`/`Lai` hoặc null. `khong_xac_dinh` là thuộc tính span; không tự tạo lớp T1 thứ tư. `khong_ro` ở output mô hình là abstain theo protocol.
8. Tên trùng hai thời kỳ không được ép chọn hệ; thiếu quận không đủ chứng minh mới. Metadata nguồn benchmark không phải bằng chứng gán mù/gán hỗ trợ từ text.
9. Unit/integration test tiny fixture được chạy để kiểm logic/checkpoint; không gọi chúng là thực nghiệm pretrained hoặc kết quả benchmark.
10. Giữ dev API/gate hiện có. Không dùng `enforce_release_pin=False`, sửa manifest cũ hoặc đổi literal `split=dev` thành test để lách gate.
11. Không tối ưu lại HEUR/CRF/native mapping bằng những ca test vừa đọc khi QA.
12. Data05 giữ `DEFERRED_BY_USER`, VQA giữ `HOLD`; không mở thu thập địa chỉ mới. T3, RAG/LLM, FastAPI/Docker ngoài phạm vi.
13. Tên hàm/biến mới tiếng Anh; giữ schema hiện hữu, dùng `Path`; không hardcode đường dẫn máy cá nhân vào code.
14. Đọc file theo `rg`, batch các việc độc lập; giữ edits/dependencies tuần tự. Gửi progress ngắn thường xuyên; không bỏ dở phần độc lập vì L1 bị chặn.

## P0 — Snapshot và kiểm kê đầu lượt

1. Kiểm branch/HEAD/remotes và dirty files. Không reset, clean, stash hoặc stage toàn repo. Không sửa nhánh partner `print3_label100test`.
2. Chọn evidence root mới, ví dụ:

   `data/interim/modeling/sprint03/local_finish_before_colab_20261004_v1/`.

   Nếu đã tồn tại, chọn suffix mới; ghi quyết định và đường dẫn.
3. Snapshot hash các corpus/gold/split/queue/decisions, các gazetteer hiện hành và run đã khóa; raw lớn dùng size/mtime theo policy. Có thể dùng script40 và bổ sung coverage cho release gazetteer/run mới chưa được ledger cũ bao phủ.
4. Kiểm WSL/Python3.11 và runtime có sẵn. Dùng WSL theo AGENTS.md; dùng `bash --noprofile --norc` khi phù hợp để tránh login-shell side effect. Không sửa env global.
5. Ghi dung lượng trước lượt của các thư mục cài/cache/resources/handoff sẽ dùng trên ổ D; phân biệt phần đã có với phần mới.
6. Lập bảng availability: export mới, bản duyệt, source references, corpus, checkpoint/resources, ZIP và notebook. Không coi thiếu approval là thiếu code.

**Đầu ra:** initial state, frozen ledger, availability, storage-before và task status. Bất biến bị thay từ trước phải báo rõ; không tự khôi phục dữ liệu của người khác.

## L1 — QA test và phán quyết gắn hash

### L1.1. Chọn đúng input

- Kiểm `exports/test_assisted_v1/`, dự kiến `test100_assisted_round2.json` hoặc vòng mới hơn.
- Nếu chưa có file mới, QA bản thực có để báo trạng thái, hỏi đúng file/corrections còn thiếu và tiếp tục L3/L4/phần fixture L2/L5.
- Snapshot byte nguyên trạng, lưu nguồn đường dẫn repo-relative, hash, project/account/annotation IDs. Không giả tên reviewer từ ID1.

### L1.2. Chạy QA bằng luồng hiện có

```bash
python -m scripts.53_qa_test100_annotation \
  --export data/interim/annotation/sprint03/exports/test_assisted_v1/test100_assisted_round2.json \
  --assisted-manifest data/interim/annotation/sprint03/test100_assisted_v1/manifest.json \
  --output-dir data/interim/annotation/sprint03/test100_review_round2_v1
```

Thay export/output bằng file/vòng thực. Nếu đã tồn tại output, dùng tên mới.

- Giữ assisted gate manifest/hash/version; blind mặc định vẫn từ chối prediction và không cho bỏ role để lách gate.
- Cần đúng 100 ID/text, annotations thật không cancelled; không unknown ID, duplicate task, hidden data field, lỗi offset/system/label hoặc overlap.
- Nếu nhiều annotation: chỉ tự chọn sau khi chứng minh **toàn bộ span/offset/label/system/T1/flag/note tương đương**; ghi rule, ID chọn, ID trùng và hash export. Khi nội dung khác, cần lựa chọn/phán quyết thật.
- Bản đồ602/653 của round1 phải được kiểm lại sau sửa; không áp mù vào round2. Task695 không tự chọn bản mới nhất.
- Nếu dùng adjudication map, chạy thư mục QA mới với `--adjudication-map`, lưu hash map và lý do lựa chọn.

### L1.3. Rà nội dung

Đọc mọi annotation được chọn trên 100 mẫu khi đủ export, không chỉ các dòng flag. Kiểm ranh giới tên đường/hẻm/số nhà, đơn vị cấp huyện/tỉnh, tên không có tiền tố, lần nhắc lặp, Khac/O, temporal span và T1.

Rà những ca trong báo cáo41 theo **hash mới**. Xác nhận chúng đã sửa thì đóng finding; không yêu cầu lặp sửa đã hoàn tất. Không tự kết luận 14 lựa chọn T1 sai nếu reviewer có bằng chứng đủ; cũng không dùng việc Submit làm bằng chứng thời kỳ.

Nguồn hành chính chỉ dùng những snapshot/alias đã audit, giữ khóa tỉnh–huyện–xã và mốc ngày. Nếu cần kiểm nguồn bổ sung, dùng nguồn chính thức/primary, lưu evidence; không lấy GT nguồn benchmark làm đáp án.

Flags có thể giữ khi phán quyết có lý do. Note `GỢI Ý AI CHƯA DUYỆT`, lead_time ngắn hoặc prediction không sửa không tự chứng minh người chưa review; không bắt sửa mọi note để làm xanh báo cáo.

### L1.4. Hồ sơ duyệt

Hiện thực schema/validator cho:

- Review decision: `sample_id`, finding code, task/annotation ID, decision, reason/evidence, reviewer/account ID, reviewed_at, export hash, annotation fingerprint.
- Attestation: reviewer, Label Studio account ID, `reviewed_sample_count=100`, phạm vi review, ngày, bằng chứng xác nhận trực tiếp của chủ dự án, export/guideline/XML/assisted-manifest hashes.
- Decision và attestation phải gắn **đúng bản export được QA**, không tái dùng xác nhận 300 train/dev hoặc 68 pilot cho 100 test.

Chỉ hỏi phần còn thiếu: reviewer, toàn bộ 100 đã xem, annotation ID cần chọn và quyết định không suy được. Không tự điền `approved`, tên người hay lời xác nhận của người dùng. Khi đã có bằng chứng đúng hash trong session/file hợp lệ, không hỏi lại.

**Nghiệm thu L1:** 100 converted, 0 vấn đề cấu trúc, mọi finding/cờ cần phán quyết đã có quyết định hợp lệ; attestation đủ; canonical khớp annotation raw được chọn. Nếu chưa đạt, ghi `TEST_REVIEW_BLOCKED` cùng danh sách ID/thao tác thực sự cần owner làm.

## L2 — Công cụ phát hành test gold/corpus ba split

### L2.1. Kiến trúc

Tái dùng các helper hash/schema/coverage/annotation fingerprint của `annotation_release.py`; pipeline cũ chỉ phát hành train/dev không được gọi là publisher test.

Hiện thực module publisher test riêng và CLI nếu chưa có, gợi ý:

- `src/data/test_corpus_release.py`.
- `scripts/54_publish_test_corpus.py`.

CLI nhận QA dir, approval/decisions, train/dev release, queue/assignment/near-duplicate decisions và output version mới. Ghi rõ lệnh tái lập thực tế trong docs.

Thiết kế hai bước:

1. `prepare/validate`: tạo candidate và audit, luôn chưa gold nếu thiếu approval.
2. `publish`: kiểm lại toàn bộ gate/hash tại thời điểm ghi rồi phát hành; fail closed nếu thiếu/bất nhất.

### L2.2. Validation

1. Kiểm đúng 100 frozen IDs/text bằng test-only import/hold manifest; `source_group` lấy từ queue đã khóa.
2. Re-convert hoặc kiểm fingerprint canonical với raw annotation được chọn. Không tin một JSONL có offset hợp lệ nhưng đã bị sửa label sau QA.
3. Kiểm attestation/decision hashes, reviewer và lựa chọn annotation; unknown/stale decision phải báo lỗi.
4. Kiểm train/dev bytes/hash/count, source group và split assignment; giữ manifest nguồn cũ.
5. Audit trùng ID, group, exact/normalized text và gần trùng. Dùng script18/helpers; 138 quyết định cũ chỉ tái dùng nếu đúng tập cặp/text/hash, không tự tạo `distinct` cho cặp mới.
6. Không tự loại lỗi khỏi gold bằng mask. Mask T1 mới chỉ khi có ngoại lệ đã được chủ dự án phán quyết và ghi manifest; giữ T0 theo phạm vi duyệt. Ngoại lệ543 cũ phải được kế thừa chính xác.

### L2.3. Đầu ra

Tạo test release version mới, ví dụ `data/processed/annotation/sprint03/test_gold_v1/`, và release tổng `.../corpus_v1/`; nếu tên đã tồn tại thì tăng version, không ghi đè.

Tối thiểu:

- `test_benchmark_t0.jsonl`: 100 gold canonical, schema giữ nguyên.
- `test_input.jsonl`: 100 dòng chỉ `{sample_id,text}`.
- `train.jsonl`, `dev.jsonl`, `dev_input.jsonl`: giữ **bytes** bản240/60 đã duyệt khi đưa vào corpus tổng.
- `manifest.json`: schema/status/count/hash của outputs, source manifests, split/audit/approval hashes, mode `AI_ASSISTED_HUMAN_REVIEW`, exclusion policy.
- `approval_record.json`, quyết định ca khó, `coverage.json`, `split_audit_report.json` và ID/source-group registry.
- README release với policy sử dụng train/dev/test và giới hạn gán hỗ trợ.

Manifest tổng liên kết nguồn train/dev và test release; không đổi trạng thái `TRAIN_DEV_APPROVED_TEST_PENDING` trong manifest train/dev bất biến. Training vẫn có thể dùng release 240/60 cũ được pin; luồng test dùng manifest mới riêng.

Coverage phải tính từ gold mới thật: support của cả 11 nhãn, T1 eligible/null/excluded, nhóm nguồn và observed/derived/synthetic theo provenance. Không suy dữ liệu observed từ nhãn có vẻ thật. Không báo F1 cho nhãn thiếu support ở giai đoạn packaging.

Nếu L1 chưa qua, vẫn hoàn thiện code/tests/template của L2; **không ghi release approved**, không dùng 98 candidate làm 100 test.

**Nghiệm thu:** publisher fixture PASS, từ chối raw/canonical/approval tampering và overwrite; khi phát hành thật đạt 240/60/100, bytes train/dev giữ nguyên, hash toàn bộ khớp, split sạch hoặc phán quyết hợp lệ.

## L3 — Hạ tầng final-test và protocol

### L3.1. API/CLI riêng

Hiện thực/tái sử dụng một tầng final-test, gợi ý:

- `src/evaluation/test_runner.py`.
- `scripts/55_run_span_test.py`: preflight/inference.
- `scripts/56_score_span_test.py`: scoring riêng.

Không sửa gate dev thành chấp nhận mọi status. Shared primitive có thể refactor khi giữ nguyên hành vi/API và regression của dev.

`preflight` kiểm manifest test approved, hash, 100 ID, selected-model lock/resources và khả năng tương thích adapter; không cần load gold từng dòng để inference.

Inference:

- Chỉ nhận `test_input` text-only; reject thêm GT/system/span/source_hint vào input record.
- Chỉ mở khi có lock thực được tạo sau chọn mô hình bằng dev. Model đã train cần checkpoint hash; HEUR cần gazetteer/alias/threshold lock; DP-ZS cần pretrained/resource/mapping lock.
- Mỗi ID có output/status rõ, raw native output nếu có, span/offset, confidence/abstain, alignment trace và runtime error.
- Ghi run ID mới, input/config/code/resources/checkpoint hashes, `supported_labels`, seed/runtime, latency/count/error; freeze prediction trước scoring.
- Không truyền gold/exclusion label làm feature hoặc skip prediction theo gold. Scorer xử lý eligible/mask sau.

Scoring:

- Đọc prediction đã freeze và gold đúng version; kiểm input ID/text hashes, đủ 100 output, config/resources/checkpoint lock.
- Reject duplicate/missing/unknown IDs hoặc manifest/hash khác; quy tắc xử lý runtime_error/abstain theo protocol không được bỏ mẫu âm thầm.
- Không để scoring stage ghi lại prediction, model config, checkpoint hoặc thực hiện calibration.
- Thực hiện phép chiếu span → 5 trường nếu protocol có, với mapping toàn cục/versioned; scorer 5 trường riêng, không sửa gold T0.

### L3.2. Ma trận và lock

Chuẩn bị protocol final version mới dẫn chiếu protocol cũ:

`HEUR-JW`, `DP-ZS-FT`, `DP-FT-FT`, `CRF-INDEP`, `PHOBERT-CRF`, `PROPOSED-DYN`.

Ablation `PROPOSED-NO-CONSTRAINT` dùng **cùng best checkpoint** và cùng calibration policy của proposed, không huấn luyện một mô hình khác rồi gọi ablation cùng checkpoint.

- Candidate c01/c02, seed/budget và selection đọc từ protocol lock/tuning protocol; không tự thêm grid hoặc seed chỉ để đạt tiêu chí.
- Giữ effective batch size/budget khi chọn hardware profile; không hạ gate RAM/VRAM/disk hoặc đổi embedding để chạy.
- Trạng thái lock trước training là `PENDING_DEV_SELECTION`, checkpoint hash để null khi chưa có; không viết hash giả/đổi future resource thành active.
- Lock sau dev phải có selected candidate/checkpoint, dev source-run hashes, mapping/resources/processor/decoder/calibration hashes và rule chọn. Test input/gold release được pin riêng.
- Các seed kiểm tra độ ổn định chưa chạy giữ `NOT_EXECUTED`; không báo mean/std ba seed từ một seed.

### L3.3. Metrics và report schema

1. **T0:** exact-span micro P/R/F1 toàn bộ 11 nhãn, theo từng nhãn và nguồn; lỗi ranh giới, sai nhãn, thiếu span và span thừa. Gold thuộc nhãn không hỗ trợ vẫn tính là FN; kết quả trên tập nhãn được hỗ trợ và coverage báo thêm, không thay điểm toàn schema.
2. **T1:** macro-F1, accuracy, confusion matrix, số mẫu đủ điều kiện, null/exclusion, coverage/abstain và quy tắc mẫu số. CRF/adapter chưa có T1 báo `NOT_IMPLEMENTED`.
3. **Hallucination Quận:** định nghĩa trước tử số/mẫu số trên những mẫu có gold T1=`moi` đủ điều kiện, áp mask. Tách địa chỉ có Quận/Huyện thừa với lỗi thiếu span và lỗi ranh giới. Khi mẫu số bằng 0, ghi không xác định/không có support, không ghi 0% như đã chứng minh tốt.
4. **5 trường:** báo cáo dataset/mode riêng theo `model_matrix`; oracle nếu có phải tách run. Không gộp điểm 5 trường thành T0.
5. **Support:** ghi số gold/predicted span của 11 nhãn, nhãn không hỗ trợ/không có gold, nhóm nhiễu/thiếu/lai nếu metadata scorer được phép sử dụng. Không suy kết luận vững từ vài span.
6. **Latency:** ghi hardware, CPU/GPU, memory, batch, phạm vi tính tokenization, warmup và mẫu số; không so số từ hardware khác mà thiếu chú thích.

Chuẩn bị schema/template tổng hợp, chưa có metric test thật. Trường chưa chạy để null và status `NOT_EXECUTED`, không để 0 rồi giải thích rằng đó là placeholder.

### L3.4. Kiểm local

Chạy fixture độc lập, dùng text hư cấu, adapter giả khai báo rõ là fixture và tiny checkpoint khi cần. Kiểm việc tách inference/scorer, Unicode/offset nguyên bản, FN cho nhãn không hỗ trợ, mask T1 nhưng giữ T0, abstain/lỗi runtime, sửa config trái phép, thiếu/trùng ID và cổng selection lock.

Không gọi runner bằng 100 text thật trong lượt này, kể cả chỉ HEUR/CRF. Không đánh giá test để debug mapping/decoder hoặc notebook.

**Nghiệm thu:** CLI/API/fixture và hợp đồng manifest chạy được; test thật `NOT_EXECUTED`, lock checkpoint cuối vẫn pending đúng thực tế.

## L4 — Resource audit và gói Colab mới

### L4.1. Inventory trước mọi cài/tải

Được dùng quyền cài/tải local đã có trong session **sau khi ghi inventory**, chỉ khi cần thiết. Mọi cài đặt/cache/temp/weights/managed Python mới nằm trên ổ D.

Inventory phải có:

- Package/version/source/purpose/license.
- Model/revision/checkpoint/embedding/source/hash có thật hoặc trạng thái pending.
- Dung lượng tải ước tính, dung lượng sau cài, host RAM/VRAM và đĩa trống.
- Vị trí cài/cache trên D, tài nguyên tái dùng từ local và những gì chưa được phép chia sẻ.

Ưu tiên runtime có sẵn; không nâng package không liên quan, sửa venv Windows/main WSL hay cài toàn máy. Khi cần env mới, tạo env version riêng dưới `data/interim/modeling/sprint03/` trên D. Không ghi token/cache/Java temp vào C. Không dùng HOME/CODEX_HOME làm biến riêng của nhiệm vụ.

FastText/checkpoint Deepparse cần xác minh từ upstream chính thức/primary; lưu URL, revision, trích dẫn điều kiện/license ngắn, ngày kiểm và evidence. Không coi license repo code là license weights. Template hoặc recipe chưa tải và kiểm hash không phải active lock.

Nếu nguồn/terms không rõ hoặc RAM/disk thiếu, ghi blocker riêng Deepparse; hoàn thành gói PhoBERT/proposed và hạ tầng độc lập. Không thay native embedding bằng embedding rút gọn hoặc hash embedding rồi gọi cùng baseline.

### L4.2. Dependency closure của bundle

Kiểm các đường dẫn file code thật đọc. Đã biết `prepare_data` cần:

- `data/interim/annotation/sprint03/reannotation_v2_release1/trace.jsonl`;
- `generation_manifest.json` cùng thư mục;
- `data/interim/annotation/sprint03/annotation_queue_batch02_train_dev.csv`;
- Corpus 240/60, toàn bộ file mà manifest của corpus pin, model/protocol/config/resources tương ứng.

Gói Colab cũ chưa bao gồm đầy đủ ba phụ thuộc này. Xác minh lại nguồn/hash và bổ sung tối thiểu vào bundle mới. Trace phải đúng 300 ID train/dev; queue chỉ 232 train/dev. **Không đưa queue batch01 chứa 100 test vào training ZIP** để giải quyết dependency.

Nếu cần sidecar thay thế, version hóa và giữ đủ provenance/hash; không sửa trace, queue hoặc manifest frozen để khớp ZIP.

### L4.3. Version mới và ba phạm vi artifact

Sửa builder để nhận notebook output path/version mới; notebook cũ đã tồn tại nên không gọi builder cũ rồi ghi đè/xóa notebook để vượt lỗi. Không sửa ZIP/manifest handoff đã khóa.

Tạo:

1. **Training code/data bundle:** 240 train / 60 dev, dev text-only, manifest/coverage/mask, source trace/queue tối thiểu, code/config/protocol. Không chứa 100 test, raw export, test candidate hoặc test gold.
2. **Resource bundle:** các file PhoBERT/VnCoreNLP/Java thật trong lock, LICENSE/legal/source metadata, giữ revision/hash và executable bits cần thiết. Gói Deepparse riêng chỉ khi license/hash đã qua cổng.
3. **Final evaluation bundle:** khi L2 qua cổng, đóng gói 100 input text-only + manifest tối thiểu và final runner/config; artifact gold dùng cho scorer quản lý riêng. Gói này không được mount/giải nén trong notebook training trước khi chốt dev.

Nếu L2 chưa qua, chỉ chuẩn bị builder/schema cho gói3 và ghi `PENDING_TEST_GOLD`, không dựng gói 100 từ 98 candidate.

### L4.4. Notebook và flow tương lai

Notebook mới phải có:

1. Kiểm ZIP/hash/path traversal, giải nén vào workspace mới; kiểm kê Python/CPU/RAM/GPU/disk thực tế.
2. Bootstrap Python cô lập và dependency profile đã pin; chỉ cài khi người chạy mở giai đoạn Colab, không tự thực thi khi build notebook local.
3. Kiểm resource/manifest/dependency, tokenizer/VnCoreNLP/Unicode/alignment; giữ offset theo raw text.
4. **Pretrained smoke ngắn** trước full training: loader/forward, backward trên tập con nhỏ của train240 nếu cần, checkpoint save/load và optimizer/RNG/resume. Ghi phạm vi mẫu và trạng thái `SMOKE`, không gọi là kết quả mô hình huấn luyện đầy đủ.
5. Cổng full training kiểm smoke/resources/hardware/backup; mặc định `ENABLE_NEURAL_TRAINING=False`.
6. Các lượt Deepparse/PhoBERT/proposed theo protocol, candidate/run ID mới; train240/chọn bằng dev60, calibration chỉ trên dev.
7. Constraint on/off cùng checkpoint; inference → freeze prediction → score dev riêng; audit và tạo selection lock.
8. Backup best/last/optimizer/scheduler/RNG; lưu checkpoint bằng cơ chế atomic khi phù hợp. Có backup định kỳ và checksum cuối. Không tự mount Drive hoặc lưu token cá nhân.
9. Notebook final test riêng: chỉ sau selection lock + test release approved, tải gói3, inference 100 input text-only, freeze prediction rồi scorer đọc gold riêng và tổng hợp.

Local chỉ kiểm AST/import notebook, hàm đóng gói, giải nén vào thư mục mới trên D và data preparation bằng CPU phù hợp; không thực thi notebook cloud/training thật. Có thể kiểm processor thật đã có khi RAM đủ và không đổi gate. Nếu dùng raw/fixture processor, ghi đúng phạm vi; kết quả đó không thay bằng chứng PhoBERT 300/300 thật.

### L4.5. Kiểm gói

- Kiểm nội dung bằng allowlist: không có test data trong training bundle; không có token/venv/cache/raw export hoặc nguồn chưa rõ điều kiện phân phối lại.
- Kiểm SHA từng member/archive, trùng tên trong manifest, symlink/path traversal và hash file sau giải nén.
- Kiểm đủ phụ thuộc bằng thực thi luồng chuẩn bị CPU an toàn trong workspace giải nén hoặc harness tương đương; không đổi ROOT của corpus để ghi vào artifact frozen và không bỏ pin hash.
- Thiếu GPU khiến GPU smoke giữ `NOT_EXECUTED/PENDING`, không dùng CPU fixture để ghi `SMOKE_PASS_GPU`.

**Nghiệm thu:** gói PhoBERT/proposed có thể chuẩn bị/tái lập local đúng hash; notebook có đầy đủ luồng thực nghiệm tương lai; GPU/Colab/training vẫn `NOT_EXECUTED`. Tài nguyên Deepparse chỉ ready khi có bằng chứng thật; blocker được ghi rõ.

## L5 — Kiểm thử, artifact, tài liệu và Git

### L5.1. Kiểm thử bắt buộc

Theo AGENTS.md:

```bash
python -m unittest discover -s tests -v
```

Nếu đổi logic data/src, thêm/cập nhật test phù hợp trong `tests/test_data_pipeline.py` và test module chuyên biệt. Không tự thêm formatter/linter/dependency chỉ để format.

Dùng runtime chuyên biệt có Torch/CRF khi thay đổi logic đó; ghi rõ phạm vi trùng nhau giữa các suite, không cộng tổng test chồng lặp. Skip trong env chính không chứng minh integration đã qua; phải chỉ ra evidence từ runtime chuyên biệt hoặc blocker.

Tối thiểu test:

- Assisted QA: hash/version, hidden metadata, cổng role blind.
- Chọn annotation tương đương so với annotation khác flag; cancelled/missing/hash đã cũ.
- Approval identity/scope/hash, canonical khác raw, publisher thiếu approval hoặc cố ghi đè.
- Split/group/exact/normalized/near duplicate; mask T1 task543 nhưng giữ T0.
- Inference input text-only, final selection lock, tách freeze/scorer, coverage/FN và mẫu số bằng 0.
- Colab bundle đủ phụ thuộc, hash trước/sau giải nén, path/security, không bootstrap local, training tắt mặc định và ablation cùng checkpoint.
- Resource hash giả/template chưa active; Deepparse bị chặn không ảnh hưởng gói PhoBERT.
- Regression dev API và pin corpus cũ.

### L5.2. Audit cuối

Gợi ý `57_audit_final_handoff.py` nếu cần. Audit chỉ đọc phải:

- So P0 ledger với trạng thái cuối; mọi corpus/split/gold/gazetteer/run/source frozen giữ nguyên bytes.
- Kiểm hash raw export nguồn/snapshot, approval, canonical và selection map đúng vòng.
- Kiểm counts 240/60/100 chỉ nếu test đã approved; không gọi là release đầy đủ khi L1 còn bị chặn.
- Kiểm T1 eligible/mask, T0 giữ nguyên, coverage và phạm vi observed/derived/synthetic.
- Kiểm ZIP/notebook/resource/manifest phụ thuộc và tất cả cổng mở giai đoạn tương lai.
- Chỉ ghi PASS khi đã kiểm thực; ghi SKIP/BLOCKED có lý do, không bỏ kiểm tra được yêu cầu để báo xanh.

### L5.3. Báo cáo dung lượng

Ghi packages/models thực đã cài/tải và vị trí trên D; phân biệt tài nguyên tái dùng với cài mới.

Đo bytes trước/sau các thư mục được quản lý. Báo:

| Loại | Bytes mới còn trên đĩa | GB | GiB |
| --- | --- | --- | --- |
| Env/packages mới | thực đo | bytes/10^9 | bytes/2^30 |
| Cache/download/resources mới | thực đo | tương ứng | tương ứng |
| Bundle/log/evidence artifact | thực đo riêng | tương ứng | tương ứng |
| Tổng phần mới theo phạm vi đo | thực đo, tránh cộng trùng path | tương ứng | tương ứng |

Nêu cách xử lý symlink/hardlink và sự khác biệt giữa tổng dung lượng file với chênh lệch đĩa trống. Không tính resources đã có như cài mới; không tính ZIP là package install. Nếu không cài/tải mới, báo 0 GB / 0 GiB nhưng vẫn nêu dung lượng artifact riêng.

### L5.4. Tài liệu và Git

- Cập nhật README, `docs/data_quality.md`, mục lục Sprint3, trạng thái AGENTS và báo cáo L1–L5 mới.
- Hướng dẫn phải dùng script/path/tham số đã kiểm thực, không để lệnh cho script chưa có.
- Ghi AI-assisted, IAA `NOT_MEASURED`, nhãn không hỗ trợ/ít support, resource/license gap và cloud `NOT_EXECUTED`.
- Bàn giao code Git dùng nhánh `sprint3_huy`, giữ nhánh partner `print3_label100test`. Xử lý checkout/worktree an toàn khi working tree có thay đổi của người khác; không reset/switch làm mất file.
- Chỉ stage code/config/tests/docs và data được phép chia sẻ. Raw export, answer key/test gold, interim, venv/cache, weights và nguồn chưa rõ quyền chia sẻ giữ local.
- Tôn trọng quyền commit/push đã có trong session; không xin lại quyền đã cấp. Nếu chưa có quyền cho hành động Git cụ thể, chuẩn bị diff/báo cáo xong rồi hỏi phần cuối cần thiết. Nếu thiếu auth, báo rõ và hoàn thành gói local; không ghi token ra output.
- Không gộp mù toàn bộ dirty files từ lượt trước. Kiểm git diff/danh sách stage theo đúng base, xác định các thay đổi tiên quyết cần bàn giao cùng.
- Khi push được phép/thực hiện, kiểm SHA remote thực tế; nếu chưa push ghi `LOCAL_ONLY/PUSH_BLOCKED`, không báo GitHub đã nhận chỉ vì commit local.

## E. Thứ tự và cách xử lý blocker

Thứ tự logic:

`P0 → L1 QA`.

Nếu L1 qua cổng: `L2 publish → L3 + L4 → L5`.

Nếu L1 chờ owner: hiện thực L2 publisher và fixture, L3, L4 và phần L5 độc lập; khi có file mới quay lại L1/L2. Không tạo release approved trong lúc chờ.

Mỗi blocker ghi: task/giai đoạn, triệu chứng, evidence, phần bị ảnh hưởng, phần độc lập đã hoàn thành và thao tác owner thực sự cần làm. Phân biệt:

- `TEST_REVIEW_BLOCKED`: cần raw export/annotation decision/attestation.
- `DP_RESOURCE_BLOCKED`: source/license/native embedding/checkpoint/RAM/disk.
- `WSL_RUNTIME_BLOCKED`: quyền/runtime/tooling cụ thể; không thay môi trường toàn máy để vượt.
- `GIT_PUSH_BLOCKED`: credential/quyền remote; không ảnh hưởng artifact local.

Nếu bị automatic approval review từ chối, báo rõ hành động và lý do từ chối; tiếp tục phần an toàn. Không suy đoán nguồn/metric/hash/human approval để vượt blocker.

## F. Trạng thái cuối hợp lệ

Không dùng một chữ DONE cho toàn bộ nếu còn cổng chặn. Báo status riêng:

- L1: `TEST_ANNOTATIONS_APPROVED` hoặc `TEST_REVIEW_BLOCKED`.
- L2: `CORPUS_240_60_100_RELEASED` hoặc `PUBLISHER_IMPLEMENTED_RELEASE_BLOCKED`.
- L3: `FINAL_TEST_PIPELINE_FIXTURE_VERIFIED_REAL_TEST_NOT_EXECUTED` hoặc blocker cụ thể.
- L4: PhoBERT/proposed `PREPARED_LOCAL_VERIFIED` hoặc blocker; Deepparse ready/block riêng; Colab/GPU smoke/full training đều `NOT_EXECUTED` trong lượt này.
- L5: test/audit PASS/SKIP/BLOCKED; Git SHA/trạng thái remote thật; GB/GiB đo thực.

Nghiệm thu local không có nghĩa Sprint3 đã hoàn thành thực nghiệm. Giai đoạn cuối sẽ là Colab preflight/smoke → train/dev selection → freeze locks → test inference/scoring → tổng hợp kết quả.

## G. Báo cáo bắt buộc ngay trong chat khi kết thúc

1. **Kết quả QA mới:** file/hash, đủ 100 hay còn thiếu, số converted/multiple, findings đã đóng/còn mở; task/sample ID và cách owner xử lý.
2. **Bảng L1–L5:** đã hiện thực gì, bằng chứng test/artifact, còn thiếu, status và đường dẫn click được.
3. **Corpus:** released hay blocked, counts, hash, approval mode, T1 mask/coverage; không gọi là 100 gold nếu còn thiếu.
4. **Final pipeline:** fixture đã kiểm gì; xác nhận chưa chấm test thật hoặc train neural.
5. **Resource/Colab:** gói nào ready, blocker Deepparse nào còn mở, cổng smoke/training tương lai; đường dẫn notebook/ZIP/manifest và checksum.
6. **Môi trường:** packages/models thực đã cài/tải, nguồn, version, license, vị trí trên D và bytes/GB/GiB mới; artifact báo riêng.
7. **Git:** branch, commit SHA, push remote SHA hoặc blocker thật; artifact ngoài Git cần nhận riêng.
8. **Owner checklist ngắn:** chỉ các thao tác agent không thể tự làm. Không yêu cầu owner tự kiểm hàng nghìn dòng hoặc gán lại 300 mẫu đã duyệt.
9. **Luồng bước cuối Colab:** lệnh/cell đã chuẩn bị, điều kiện mở giai đoạn và đầu ra cần nhận; chưa thực hiện trong lượt này.

---

## Lời dẫn ngắn để gửi agent

```text
Bạn là Senior AI/Data Engineer phụ trách repository D:\DACN.

Đọc toàn bộ file:
docs/sprints/sprint_03/43_agent_prompt_local_completion_before_colab.md

Thực hiện P0 và đầy đủ L1–L5 trong phần PROMPT: hiện thực mã,
chạy QA và kiểm thử, kiểm artifact, chuẩn bị release và gói Colab,
cập nhật tài liệu và bàn giao theo quyền Git đã có.
Không dừng ở việc lập kế hoạch.

Ưu tiên export test mới nếu đã có; các findings round1 là lịch sử,
không yêu cầu sửa lại những ca đã được giải quyết ở vòng mới.
Nếu thiếu export/phán quyết, hoàn thiện các phần độc lập và
báo chính xác phần owner cần làm; không tự duyệt/copy prediction
thành gold hoặc phát hành corpus thiếu mẫu.

Lượt này chỉ làm local: chưa chạy Kaggle/Colab, huấn luyện
thực nghiệm neural hoặc inference/chấm mô hình trên test100 thật.
Giữ nguyên corpus/split/gold/gazetteer/run đã khóa.

Nếu cần cài/tải, ghi inventory trước, mọi vị trí mới trên ổ D;
báo package/model và dung lượng thực đo bằng bytes/GB/GiB.
Kết thúc báo cáo QA và từng L1–L5 ngay trong chat, gồm evidence,
blocker, output, trạng thái Git và thao tác owner cần thực hiện.
```
