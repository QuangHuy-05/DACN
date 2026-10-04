# Kết quả local P0 và L1–L5 — 04/10/2026

## Phạm vi và kết luận

Evidence hiện hành: `data/interim/modeling/sprint03/local_finish_before_colab_20261004_v2/`, gọi là EVIDENCE dưới đây. Thư mục v1 đã tồn tại nên dùng v2. Chỉ thực hiện local; không submit Kaggle, chạy Colab, huấn luyện thực nghiệm neural hoặc inference/scoring trên test100 thật. Fixture nhỏ kiểm logic không phải thực nghiệm pretrained.

| Phần | Trạng thái | Kết quả thực |
| --- | --- | --- |
| P0 | SNAPSHOT_COMPLETE | Kiểm branch, base, runtime, storage, availability; ledger mở rộng 1.313 frozen hash và 4 raw size/mtime |
| L1 | TEST_REVIEW_BLOCKED | Round2 đủ 100 task / 103 annotation; 99 converted, 1 multiple tại 695, 0 missing; chờ phán quyết cuối |
| L2 | PUBLISHER_IMPLEMENTED_RELEASE_BLOCKED | Publisher/schema/CLI54 và 12 fixture PASS; chưa phát hành test_gold_v1 hoặc corpus_v1 |
| L3 | FINAL_TEST_PIPELINE_FIXTURE_VERIFIED_REAL_TEST_NOT_EXECUTED | Runner55/scorer56/selection protocol, 11 fixture PASS; đã tạo light dev locks |
| L4 | PREPARED_LOCAL_VERIFIED / DP_RESOURCE_BLOCKED | ZIP code/data và PhoBERT/resources v3; giải nén, hash, CPU preparation PASS; GPU/cloud/full training NOT_EXECUTED |
| L5 | TEST_AND_FROZEN_AUDIT_PASS | Full suite 239 PASS + 8 SKIP; Torch 73/73, CRF 50/50; frozen 1313+4 không đổi; Git có record riêng |

## 1. QA round2 và phần người duyệt còn chốt

Nguồn: `data/interim/annotation/sprint03/exports/test_assisted_v1/test100_assisted_round2.json`, **594.014 bytes**, SHA-256:

`d51b69c981e775e0e51ac3ed5a3ef4c91d845f5e7a900c2f3d4c79f98ca758a4`.

Raw và snapshot giữ nguyên. Mẫu thiếu của round1 `s3_7d9d2bd6ff632625` đã có; finding này được đóng. Không yêu cầu gán lại 300 train/dev. Map round1 không được áp mù: đã kiểm lại 602/653 trên round2, toàn bộ span/system/T1/flag/note tương đương; chọn annotation599/651 và lưu fingerprint/proof. Sau map có **99 converted / 1 multiple**, không lỗi offset/label/system/overlap trong các bản được chọn.

- **Task695**, ID `s3_e7cca64b0cdaf324`: annotation694 có `temporal_ambiguity`, annotation695 không cờ. T0/T1/note giống nhau nhưng toàn bộ nội dung không tương đương. Cần owner chọn 694 hoặc 695; không tự chọn bản mới nhất, không bắt sửa JSON.
- **14 ca T1** chưa có căn cứ thời kỳ trong hồ sơ hiện có: 602, 603, 609, 611, 613, 615, 617, 620, 621, 623, 629, 630, 633, 665. Không mặc định mọi T1 này sai; thiếu bằng chứng để agent phê duyệt.
- **Task663:** `Lê Đại Hành` tại Hà Nội gán moi; snapshot audited cũ xác nhận Hà Nội / 00256 / cha007 Hai Bà Trưng. Tên mới trùng có ở Hải Phòng / 10603. Finding gắn nguồn/ngày/hash; không dùng GT benchmark hoặc sửa Gazetteer.
- **Task664:** toàn câu Lai nhưng `Dịch Vọng Hậu` = cu, tỉnh/đường/số nhà không xác định; chưa có thành phần hệ mới rõ. T1 chưa qua cổng bằng chứng.
- **Task683:** có thể giữ privacy flag; cần disposition/lý do. Chuỗi có nguồn OSM công khai, không có tên cá nhân/số điện thoại rõ; điều đó không tự cấp privacy approval cho annotation.

Đề xuất giữ raw và khai báo **16 ngoại lệ T1/structure** (14 ca + 663 + 664), giữ tất cả T0. Đây là đề xuất, **chưa áp dụng**; không tự mask để báo QA xanh. Chủ dự án xác nhận hoàn thành review và yêu cầu giữ nguyên round2; lựa chọn695 và phạm vi ngoại lệ vẫn cần phán quyết cụ thể. Reviewer/account dùng hồ sơ đã xác minh trước, không đoán tên từ completed_by1.

Evidence: `test_qa_initial/`, `test_qa_equivalent_selection/`, `equivalent_annotation_evidence.json`, `equivalent_annotation_selection.json`, `manual_content_review.json`, `owner_adjudication_pending.json`. Review đã đọc toàn bộ 100 annotation, chỉ dùng nguồn hành chính đã audit. Không dùng findings test để thay baseline/threshold/mapping.

## 2. Publisher và corpus

Module `src/data/test_corpus_release.py`, CLI `scripts/54_publish_test_corpus.py` có prepare/publish. Validator kiểm export/QA/canonical/selection/approval và fingerprint finding: đúng 100 frozen ID/text/source_group, đúng annotation được chọn, schema/system/offset, decision identity/time/evidence và scope100. Unknown/stale decision, canonical tamper, thiếu approval/mask authorization hoặc output đã tồn tại đều bị từ chối.

Publisher kiểm lại bytes train240/dev60 và manifest nguồn; giữ mask T1 task543, giữ T0. Có test release riêng và corpus tổng liên kết hai nguồn; không sửa trạng thái manifest nguồn cũ. Coverage tính 11 nhãn, T1 eligible/null/excluded, source_group và observed/derived/synthetic từ provenance; không suy từ địa chỉ có vẻ thật.

`split_identity_audit.json`: **AUDIT_PASS_WITH_HUMAN_NEAR_DUP_REVIEW** cho 240/60/100 ID, group/text và 138 quyết định đúng cặp/text/split. Đây là audit identity, không phải phê duyệt 100 gold. Train/dev vẫn `TRAIN_DEV_APPROVED_TEST_PENDING`, 1057/284 span, T1 eligible206/53. **Chưa tạo approved release thật.** Test100 không vào training ZIP.

## 3. Final-test pipeline và selection

Module riêng `src/evaluation/test_runner.py`; giữ dev gate/API, primitive chung chỉ truyền raw text vào adapter. Lock liên kết dev run/config/prediction/resource/model/code hash. Neural cần hai candidate c01/c02, chọn bằng dev; proposed chọn checkpoint unconstrained rồi calibration dev và on/off cùng checkpoint. Fixture lock không mở real test. Prediction phải đóng băng trước khi scorer đọc gold.

Scorer tính đủ 11 nhãn, unsupported gold là FN; báo subset/coverage/abstain/status, source sidecar chỉ cho scorer, mask T1 theo manifest. Adapter không có T1 báo NOT_IMPLEMENTED, metric null. Hallucination QuanHuyen mẫu số0 thì null. Offset Unicode literal/raw; ID trùng/thiếu/sai phạm vi bị từ chối. Latency có hardware và phạm vi.

Locks hiện hành: `EVIDENCE/final_selection_v2/` cho HEUR-JW và CRF-INDEP, dựa trên dev frozen, không chạy baseline lại. HEUR threshold0.86; CRF context1, c1=0.1, c2=1.0. Hai baseline dùng rule lựa chọn lịch sử trong evidence run; không giả đã dùng quy tắc neural mới. Lock v1 giữ lịch sử nhưng code hash đã cũ, không dùng final test. Neural/DP selection pending; không có checkpoint giả. `final_result_template.json` giữ metric null / NOT_EXECUTED, không điền điểm dev vào cột test.

## 4. Gói Colab và resource audit

Builder nhận notebook/version mới, kiểm resource/source bytes, đủ trace300/generation_manifest/queue232. ZIP từ chối traversal, duplicate name, member không khai báo, hash sai và symlink archive. Legal symlink Java chỉ dereference vào file bên trong resource ROOT, đóng thành regular member đúng hash; giữ executable bits. Bản build v2 thất bại trước gate legal được giữ; **dùng handoff_v3**.

| Artifact v3 | Bytes ZIP | SHA-256 |
| --- | ---: | --- |
| `handoff_v3/dacn_train_dev_bundle_v3.zip` | 628105 | `2563ae13d4b577e4f42e575cc3fc4c186b6c95e1f9fcace34aab5e22568b168a` |
| `handoff_v3/dacn_phobert_resources_v3.zip` | 420749036 | `6b9953966494de8c8489618f98beaafe517f9c87fdc9c519b78824a623e707a8` |

Có 171 code/data member và 268 resource member; resource giải nén 715.711.529 bytes, gồm legal files được dereference. `closure_verification.json` xác nhận hash archive/member/sau giải nén, allowlist không test/raw export/cache/credentials và notebook AST. CPU preparation thật từ `extracted_workspace_v3/`: raw + DP surface EXACT240/240 + 60/60, T1 eligible206/53. Bằng chứng actual PhoBERT alignment300/300 đã khóa được đối chiếu hash; CPU closure không phải GPU smoke.

Notebook mới:

- `notebooks/sprint03/local_ready_train_dev_v3.ipynb`, SHA `14b0e4d64e48ed25994d390d3eced8aeef731bc0ed1aac7933275e220c665858`.
- `notebooks/sprint03/final_test_after_dev_lock_v1.ipynb`, riêng final test, mặc định tắt.

Script58 kiểm GPU/resource/alignment, pretrained smoke2 model/save-reload/optimizer-RNG; chuẩn bị full training c01/c02 + dev selection/calibration/ablation, backup best/last300s và checksum. Cần durable backup: `/content/drive` phải là mount thật; không tự mount hoặc dùng thư mục tạm. Script59 tạo final input bundle và scorer-only gold bundle **chỉ khi L2 approved**; hiện PENDING_TEST_GOLD. Chưa thực hiện full training/GPU smoke/cloud.

Tái dùng PhoBERT revision01daacda68afe13d83023d16ec647239e344a1e6 (MIT), VnCoreNLP62bbc58fe5d113c898eae112656be97dcf50b3a0 (GPL3-later), Temurin17.0.20.1+1 (GPL + Classpath). Nguồn/version/license có trong inventory44. **Deepparse full FastText bị chặn**: RAM host>=10GiB (local khoảng3.64GiB), embedding hash chưa active và license checkpoint weights chưa xác minh. FastText Common Crawl CC-BY-SA3.0 không tự clear checkpoint. Không tải/phát hành gói Deepparse hoặc gọi fixture là pretrained.

## 5. Kiểm thử, bất biến và dung lượng

| Suite | Runtime | Kết quả / log |
| --- | --- | --- |
| Full discovery | WSL main Python3.14.4 | 247 = 239 PASS + 8 SKIP, 0 FAIL; `full_suite_final.log` |
| Neural/checkpoint/processor logic | Python3.11.16/Torch CPU trên D | 73/73 PASS; `neural_suite_round2.log` |
| CRF/evaluation logic | Python3.11.16 CRF trên D | 50/50 PASS; `crf_suite_round1.log` |
| Publisher/final runner/Colab bundle | Python3.11.16 CRF trên D | 12+11+8 = 31/31 PASS; ba log `*_py311_final.log` |

Không cộng suite chồng lặp thành tổng test mới. 8 SKIP do optional runtime packages ở env main; suite chuyên biệt kiểm phần logic tương ứng nhưng không thay thực nghiệm full FastText/GPU. Scripts54–59 --help, notebook AST và actual ZIP closure đã kiểm PASS. `test_data_pipeline.py` có regression từ chối thiếu approval.

Kiểm thêm checkout bàn giao: full suite lần đầu báo 4 FAIL / 27 ERROR / 8 SKIP vì dữ liệu `interim`/corpus ngoài Git chưa có, notebook Kaggle phụ thuộc thiếu và XML/guideline bị đổi xuống dòng khi checkout. Đã bổ sung notebook và pin byte XML/guideline, giữ nguyên nội dung nguồn. **31/31 fixture publisher/final runner/Colab đã PASS ngay trong checkout riêng** (`git_*_fixture_round2.log`). Không báo full suite của clone code-only là PASS: các integration cần dữ liệu phải nhận artifact riêng. WSL có một lần lỗi service E_UNEXPECTED; lần thử sau chạy được, không thay cấu hình WSL.

`final_audit_v1.json`: **1313 hash + 4 raw size/mtime PASS**, 0 changed; handoff hash/allowlist/notebook PASS. Ledger mở rộng gồm Gazetteer v4/release2 và run pre_colab mới; không chỉ dùng ledger550 file cũ. VQA/Data05 giữ HOLD/DEFERRED_BY_USER; IAA NOT_MEASURED.

Không cài/tải package/model/cache mới. Tái dùng runtime hiện có, mọi output mới trên D. `final_audit_v1.json` đo artifact 1.199.971.903 bytes tại thời điểm kiểm: **1.199971903 GB / 1.117560922 GiB**, gồm ZIP, bản giải nén, evidence, log và Git checkout riêng. Đây là artifact, **không phải 1.2 GB cài đặt**. Đo sau Git lưu `storage_final.json`; không cộng chồng root.

Đo bổ sung `storage_final_windows.json` tại 15:52:33UTC: **1.200.533.346 bytes = 1.200533346 GB = 1.118083807 GiB**, 918 file artifact. Trước–sau cả bốn runtime/resource có số byte và số file bằng nhau, không tăng: neural1.342.973.969 bytes, resources714.579.809, Kaggle CLI49.788.314, CRF29.057.225. Kết quả này loại bản JSON kết quả đo và các file tạo sau thời điểm đo; audit/storage bản cuối trong evidence ghi thời điểm tương ứng.

| Loại | Bytes cài/tải mới | GB | GiB |
| --- | ---: | ---: | ---: |
| Env/packages | 0 | 0 | 0 |
| Cache/download/resources | 0 | 0 | 0 |

Đo logical file size, bỏ symlink, khử trùng inode/hardlink và path chồng lặp; không phải allocated disk blocks. Chênh lệch free space phụ thuộc app khác/compression, không tương đương tổng file. Bản copy resources vào ZIP/extraction tính artifact, không tính download mới.

## 6. Git và bước chủ dự án

Checkout chính giữ nhánh partner `print3_label100test`, HEAD `7e89f34d6b8ee3b00cbfdede145e70601979f292`. Bàn giao bằng checkout riêng `EVIDENCE/git_handoff/`, nhánh `sprint3_huy`, base `9c03785520a48e193ae8fb97e2828d2be06cb26f`. Chỉ stage code/config/test/doc/notebook L1–L5 và dependency tiên quyết QA/Kaggle pure helpers; không stage raw export/test gold/answer/interim/weights/source chưa rõ quyền phân phối. `.gitattributes` giữ bytes code/profile cho hash portability.

Commit/push và SHA remote thực lưu `git_handoff_record.json`; báo cáo chat ghi kết quả cuối. ZIP/evidence giữ local; cần nhận riêng, clone Git không tự có resources/dữ liệu.

**Git đã thực hiện:** code commit `fd48b4986a156c2e9258c3541ea7c824f5bbf0ce` trên `sprint3_huy`; archive từ Git kiểm 152/152 file code/config/XML/guideline khớp bytes workspace đã test. Push thử bị chặn xác thực HTTPS (`could not read Username`), không phải commit thất bại. SHA remote kiểm thực vẫn `9c03785520a48e193ae8fb97e2828d2be06cb26f`; remote partner vẫn `7e89f34d6b8ee3b00cbfdede145e70601979f292`. Không có gh CLI sẵn để hoàn tất đăng nhập tự động. Sau khi dùng terminal Git đã đăng nhập, chạy `git push origin sprint3_huy` từ thư mục dự án; không cần chuyển branch của checkout đang làm việc. Một commit tài liệu kế tiếp ghi trạng thái bàn giao này; SHA local cuối trong record/chat.

Diff có bốn file nguồn cũ chỉ khác cách lưu xuống dòng để khớp byte hash đã khóa; không thay logic OSM/VQA/normalize. Git diff-check báo ba khoảng trắng cuối dòng đã có trong script02; giữ nguyên source byte, không tự format rồi làm lệch selection/bundle hash.

Owner chỉ cần chọn annotation694 hoặc695 của task695 và chấp nhận ngoại lệ16T1 hoặc cung cấp căn cứ đủ; có thể giữ raw và flag. Agent sẽ tạo approval/decision gắn hash, QA100/100, phát hành hai release và tạo hai gói final evaluation sau khi nhận phán quyết. Không yêu cầu gán lại300 hoặc sửa24 task đã xong.

Sau release, chạy giai đoạn cuối theo [hướng dẫn45](45_local_release_and_colab_operations.md): upload hai ZIP → preflight/resources/alignment → pretrained GPU smoke hai model → durable backup → explicit full training → dev selection/calibration/on-off → selection locks → notebook test riêng → freeze prediction → scorer-only gold → tải artifact/tổng hợp. Chưa mở giai đoạn này trong lượt local.
