# Chốt test gold và mở thực nghiệm Kaggle — 05/10/2026

## Phạm vi hiện hành

Evidence: `data/interim/modeling/sprint03/release_and_kaggle_20261005_v1/`.
Chủ dự án đã xác nhận hoàn thành review100 và giao agent chốt hai quyết định còn lại. Giữ nguyên raw round2, chọn annotation694 của task695, giữ `temporal_ambiguity`; khai báo16 ngoại lệ T1/structure, giữ mọi span T0. Biên bản nêu rõ Codex thực hiện phán quyết theo ủy quyền, không giả một lượt gán độc lập mới.

Hai release hiện hành:

- `data/processed/annotation/sprint03/corpus_v1_release2/`: **240 train / 60 dev / 100 test**, `CORPUS_240_60_100_APPROVED`.
- `data/processed/annotation/sprint03/test_gold_v1_release2/`: **100 mẫu / 446 span**, `TEST_GOLD_APPROVED`.

Các bản `corpus_v1/` và `test_gold_v1/` được giữ làm lịch sử. Release2 sửa metadata nguồn, không sửa text/span/offset/label/system/T1. Train/dev byte-identical với nguồn frozen. JSONL test của release2 có CRLF do runtime Windows dự phòng; so sánh JSON và đối chiếu sau đổi riêng xuống dòng xác nhận nội dung hoàn toàn giống v1. Không sửa bytes v1 hoặc raw.

## L1 — QA và phán quyết

Raw: `data/interim/annotation/sprint03/exports/test_assisted_v1/test100_assisted_round2.json`, 594.014 bytes, SHA-256:

`d51b69c981e775e0e51ac3ed5a3ef4c91d845f5e7a900c2f3d4c79f98ca758a4`.

QA cuối: **100 converted / 0 missing / 0 multiple / issues=[]**. Chọn599/651 cho hai cặp602/653 đã chứng minh tương đương; chọn694 cho695 theo ủy quyền cuối. `owner_authorization_v2.json`, `test_approval_final.json`, `test_review_decisions_final.json` và map cuối gắn hash export/canonical/XML/guideline/queue/hold/assisted manifest/fingerprint. Tài khoản người duyệt lấy từ hồ sơ đã được chủ dự án xác nhận; không đoán tên từ ID1. 100 quyết định có lý do, phạm vi và tác nhân thực hiện.

16 task mask riêng T1/chẩn đoán cấu trúc:

`602, 603, 609, 611, 613, 615, 617, 620, 621, 623, 629, 630, 633, 663, 664, 665`.

Giữ toàn bộ446 span T0. Test T1 có **64 eligible, 20 null, 16 excluded**. Manifest tổng kế thừa ngoại lệ543 của dev, tổng17 ID mask. Flags/note giữ như raw và có disposition; không xóa cờ chỉ để báo xanh. QA cấu trúc vẫn mang tên giai đoạn `READY_FOR_HUMAN_REVIEW`; trạng thái phát hành đã duyệt nằm trong manifest release.

Annotation là **AI-assisted human review**, IAA `NOT_MEASURED`. Không gọi đây là test gán mù độc lập hoặc gán đồng thuận hai người.

## L2 — Release và provenance

Audit đủ240/60/100 ID/group, không trùng group/exact/normalized text giữa split; **138 quyết định gần trùng** vẫn khớp cặp/text/split. Trạng thái `AUDIT_PASS_WITH_HUMAN_NEAR_DUP_REVIEW`.

Phát hiện metadata v1 đếm `observed_or_existing_benchmark` thành observed100. Publisher đã sửa: giá trị trộn này giữ `unverified_provenance`, không dùng nó để tuyên bố100 địa chỉ quan sát. Năm nguồn/stratum vẫn20 mẫu mỗi nhóm:01_new/02_noisy/03_old/04_missing/06_hybrid. Metadata không được dùng làm đáp án T1 hoặc feature inference. Registry train/dev đọc đúng các queue đã pin trong manifest nguồn, kiểm text/group/hash thay vì bỏ trống provenance của300 mẫu.

Không sửa queue, benchmark hoặc label để làm khớp báo cáo. Muốn chia chính xác observed/derived/synthetic của test cần provenance chi tiết từng benchmark child; chưa suy từ tên chuỗi. Train/dev coverage nguồn đã duyệt giữ nguyên.

| Artifact | SHA-256 |
| --- | --- |
| Corpus release2 manifest | `0abd9f01ae0b298d0ef44161e65426f9769302ebb89b8c9aa45097722b09aea8` |
| Test release2 manifest | `eb054ec5a0be324f7b16f3483b4337ca69c4dd7a1686e5ca856b496f13563222` |
| Manifest train/dev nguồn, không thay | `9c91b77fa220e41b1b1067e5e99b216b7b4b2176181674b340f16dec134947bf` |

Evidence: `metadata_release2_result.json`, `release_artifact_verification.json`, `final_audit_after_recovery.json`. T0 test không có support cho ToaNha/CanHo, MocDinhVi, HuongDi, GhiChu. Dev vẫn0 MocDinhVi/ToaNha,1 HuongDi. Không kết luận chất lượng trên các nhãn thiếu support.

## L3/L4 — Tách đánh giá cuối và training

`final_evaluation_bundle_v2/` có input-only ZIP và scorer-only gold ZIP riêng. Input chỉ chứa100 cặp sample_id/text và manifest; không có spans/gold. Gold chỉ được mở sau khi checkpoint/config đã chọn bằng dev và prediction test đã freeze. Chưa inference/chấm test thật.

Locks nhẹ được làm mới từ dev evidence frozen, không chạy hoặc tune lại baseline. Dùng phiên bản lock cuối ghi trong acceptance; các lock cũ giữ lịch sử vì code identity đã thay khi sửa publisher/downloader. Hai baseline giữ lựa chọn HEUR threshold0.86 và CRF context1/c1=.1/c2=1. Neural selection đã khóa c02 cho cả hai model sau nghiệm thu cả4 run; Deepparse còn source/license/native resource gate, chưa chạy.

Gói training dùng **nguồn train/dev cũ đã pin240/60**, giữ206/53 T1 eligible và mask543. Corpus ba split, export/raw/gold100, đáp án, credentials, Gazetteer/source chưa đủ quyền phân phối không nằm trong dataset Kaggle training.

## Kaggle smoke thật

Run: [dacn-s3-smoke-gpu-20261005-v1](https://www.kaggle.com/code/huynq16/dacn-s3-smoke-gpu-20261005-v1), version1, private. Dùng lại immutable dataset smokev2, không upload lại test hoặc tài nguyên mới. Chủ dự án xác nhận đã đăng nhập/chọn GPU trước khi submit.

- Hardware thật: **2 Tesla T4, mỗi GPU15.360MiB**, driver580.178.04; model dùng `cuda:0`.
- Alignment thực: **240/240 train + 60/60 dev EXACT**, T1eligible206/53.
- PhoBERT-CRF và PROPOSED-DYN: mỗi model1 optimizer step trên4 train sample, pretrained forward/backward/save/reload PASS.
- Trạng thái **SMOKE_PASS**, không tính benchmark metric hoặc dùng smoke weights để chọn model.
- Hash smoke report `2c279724f7cf94898fc3caaad6e3f4376826f35d7dae7654391e8af61691c711`; JSON evidence đã đối chiếu remote artifact index.

Evidence: `gpu_smoke_evidence_verified.json`, `kaggle_smoke_reports_v1/`, `kaggle_smoke_streamed_v2_verification.json`. Bản streaming đã tải đủ hai checkpoint cùng report: **3.231.659.007bytes**, mọi hash khớp remote index, `DOWNLOADED_HASH_VERIFIED/SMOKE_PASS`. Kaggle COMPLETE được kiểm lại bằng report/hash, không dùng làm bằng chứng PASS đơn lẻ.

### Trouble thực tế và cách xử lý

1. WSL có lượt launcher treo và `Wsl/Service/E_UNEXPECTED`. Dừng đúng6 PID agent tạo sau kiểm command line; không shutdown distro hoặc thay cấu hình toàn máy. Tái dùng Windows Python3.12.14 sẵn có để làm phần stdlib, không cài thêm. WSL hồi phục; đã chạy lại full suite và frozen audit ở runtime chính.
2. CLI Kaggle2.2.4 buffer toàn checkpoint1,6GB qua `Response.content`, tải toàn smoke bị MemoryError. Bản tải dở giữ evidence; tải JSON riêng qua gate trước, rồi thêm module `kaggle_artifacts.py` / script60 / route fetch50: **1MiB chunks**, atomic file, kiểm size/hash/path/pagination/disk, không overwrite. Upstream cũng ghi [lỗi buffer và sửa version trong changelog](https://github.com/Kaggle/kaggle-cli/blob/main/CHANGELOG.md).
3. API SDK nhận version label `v1`, không phải `1`; lượt thử số thuần trả404. Đã sửa mapping và test; theo [issue upstream1200](https://github.com/Kaggle/kaggle-cli/issues/1200). Không fallback sang latest khi fetch streaming. CLI status cũ còn đọc latest; các job của lượt này dùng slug riêng/version1 duy nhất.
4. CLI mutation Windows gặp cache-path upload không tương thích. Chuyển upload sang WSL có sẵn, giữ bản thất bại để đối chiếu; không vá vendor hoặc cài lại CLI.
5. Một lượt tải Dync01 bị lỗi mạng. Thêm retry tối đa3 lần, xin URL mới từ cùng page/version SDK, chỉ ghi loại lỗi/HTTP status, giữ URL ký riêng tư ngoài log. Retry/operator resume dùng thư mục mới và cache khớp index mới; không train lại model hoặc sửa artifact gốc. Regression retry có fixture riêng.
6. Recompute dev ban đầu khác **thứ tự** preview lỗi ranh giới do scorer dùng set; SHA scorer giống hệt, nội dung event và mọi số đếm/metric khớp sau chuẩn hóa thứ tự list debug. Không sửa scorer, metric cloud hoặc prediction để ép audit PASS.
7. Kiểm vị trí tạm cuối cho thấy các lượt unittest đầu dùng `/tmp` WSL mặc định cho fixture tự dọn. Đã nghiệm thu lại toàn suite với `TMPDIR` trên D. Package/cache/resource/model/artifact persistent của lượt này vẫn ở D; không gọi fixture tạm đã dọn là dung lượng cài mới.

## Full training và bước sau

Sau smoke thật, chuẩn bị hai candidate/model theo protocol, seed42, tối đa20epoch/patience5/effective batch16. Bốn dataset private đã upload; mỗi run có ID mới. **Cả4 full run đã `FULL_TRAINING_DEV_ONLY_COMPLETE`**. Báo cáo, dev prediction, best/last checkpoint của cả4 được tải/xác minh, nguồn code khớp ZIP thực gửi Kaggle, resource/corpus hash khớp, recompute dev khớp. Xem `neural_dev_acceptance.json`; không suy training thành công chỉ từ API COMPLETE.

| PhoBERT-CRF | Epoch được chọn | Epoch đã chạy | Exact-span micro F1 dev |
| --- | ---: | ---: | ---: |
| c01 | 12 | 17 | 93,33% |
| c02 | 8 | 13 | **93,89%** |

| PROPOSED-DYN | T0 F1 unconstrained dev | T0 F1 constraint on | T0 F1 constraint off |
| --- | ---: | ---: | ---: |
| c01 | 93,33% | 93,33% | 93,33% |
| c02 | **94,74%** | **94,74%** | **94,74%** |

Chọn **c02 cho cả2 model** theo full11 micro F1 → gold-supported macro F1 → earlier epoch/candidate; Dyn chọn bằng unconstrained dev, calibration không dùng test. Dync02 calibration threshold0.7/margin0.2; T1 trên53 eligible: macro-F1 **59,96%**, accuracy **77,36%**, accepted49/53; riêng Lai support8/F1=0. Constraint on/off cùng checkpoint cho cùng T0 F1 và cùng0/14 hallucination Quận trên gold-moi eligible. **Không chứng minh ràng buộc đã cải thiện kết quả hoặc triệt tiêu lỗi nói chung**, không so trực tiếp với77,5% từ track khác. Một seed42, không báo mean/std nhiều seed.

Đủ60 prediction mỗi candidate/variant, completion audit cloud `AUDIT_PASS`,0issues. Các bản selection tải đủ mọi report/sidecar + best/last; epoch khác ở remote với hash, không được gọi local-verified. Phần tải dở giữ lịch sử. Tái dùng hardlink chỉ sau hash khớp **index remote mới đúng version**. PCRFc01 có backup warning hash trong lúc alias cập nhật; Dync01 có warning rolling resume sidecar bị xóa khi backup định kỳ. Backup cuối thành công và selected checkpoint/hash acceptance PASS; không che các cảnh báo. `last` đã qua hash/metadata gate resume; chưa thực hiện resume full training từ last, smoke đã kiểm optimizer/scheduler/RNG round-trip thật.

Sau full run: xác minh artifact/checkpoint/hash → chấm dev đã freeze → chọn c01/c02 bằng dev → calibration/ablation on/off cùng checkpoint → lock → final inference input-only → freeze → scorer-only gold. Giai đoạn test chưa mở trong lượt này. Không tune từ16 case test hoặc kết quả QA test.

### L3 — Neural locks và workspace đánh giá cuối đã sẵn sàng

`neural_evaluation_workspace_v1/` khôi phục đúng code/resource ZIP đã gửi Kaggle. Không thay source model/processor/dev cũ đã pin trong checkpoint config bằng code mới rồi bỏ kiểm hash. Thêm các gate final-test và module tương thích riêng `final_inference_bridge.py`, giữ nguyên thân hàm inference text-only dùng chung; **11/11 fixture PASS**. Đây là kiểm hợp đồng, không phải chạy test100.

`neural_source_restoration_acceptance.json` xác nhận source được giữ nguyên và **3 preflight PASS**, mỗi variant đủ100 input-only: PhoBERT-CRF c02, PROPOSED-DYN c02, PROPOSED-NO-CONSTRAINT cùng checkpoint/calibration. Locks nằm trong `neural_evaluation_workspace_v1/final_neural_selection_v1/`; variant off dùng **`dyn_no_constraint_model_config_v2.json` / `dyn_no_constraint_selection_lock_v2.json`**. Bản off không khóa ở lần xây đầu được giữ lịch sử, không dùng để chạy. Workspace không chứa gold100.

Neural source này khác main hiện hành nên phải chạy các locks neural trong workspace đã khôi phục. Locks nhẹ `final_selection_v5/` chạy với main. Hai nơi đều mới **preflight**, chưa tạo prediction hoặc metric test thật. `neural_dev_acceptance.json` ghi trạng thái ở thời điểm trước khôi phục; receipt khôi phục phía trên là bằng chứng đóng phần neural lock còn chờ ở snapshot đó.

### L4 — Thao tác giai đoạn cuối

1. Giữ các checkpoint/config/threshold đã khóa; không chạy lại lựa chọn từ test.
2. Với neural, chuyển nguyên layout workspace đã khôi phục sang máy/cloud đủ tài nguyên. Giữ các đường dẫn resource, checkpoint và dev evidence mà lock đã pin. Với baseline nhẹ, dùng main và lock v5. Chưa upload hoặc chạy cloud test trong lượt này.
3. Chạy action `preflight` của script55 với input-only và lock đúng model. Khi mở giai đoạn cuối, action `infer` cần `--execute-final-test` và output directory mới. Đủ100 trạng thái output, offset phải khớp raw; lưu/freeze predictions trước chấm.
4. Đưa prediction đã freeze về scorer rồi mới mở ZIP gold riêng. Script56 chấm với manifest release2 và mask T1, không chỉnh prediction/threshold sau xem gold.
5. Báo T0/T1/structure và constraint on/off riêng; test100 này là AI-assisted human-reviewed. Deepparse vẫn phải qua cổng riêng trước khi thêm vào bảng thực nghiệm.

Deepparse full/native giữ blocker source/license/resource riêng, không dùng embedding rút gọn hoặc fixture để báo pretrained baseline hoàn tất. Data05 DEFERRED_BY_USER; VQA HOLD; T3/RAG/API ngoài phạm vi.

## Kiểm thử, dung lượng và Git

Full suite cuối với TMPDIR trên D: **262 test =254PASS +8SKIP,0FAIL**, bao gồm regression streaming/path/version/profile/hardlink/hash/retry. Publisher14/14, final pipeline11/11; Colab fixture Windows8test=7PASS/1SKIP(symlink), không thay bằng chứng WSL trước. Audit WSL: **1313 frozen hash +4 raw size/mtime PASS**,0changed. Ghi acceptance/artifact cuối sau các bước mới, không cộng suite trùng.

Gói Colab `handoff_v4/` có ZIP code/resource và notebook `notebooks/sprint03/colab_train_dev_release_v4.ipynb`. Kiểm hash toàn ZIP/member, AST notebook chưa execute và `prepare` trong workspace giải nén độc lập PASS240/60. Phiên bản khóa nhẹ cuối **`final_selection_v5/`** giữ nguyên lựa chọn frozen dev, preflight100 text-only PASS, chưa inference. v4 lock giữ lịch sử vì downloader retry đổi code identity. Gói Colab này chưa chạy; tích hợp/huấn luyện thật hiện ở các run Kaggle riêng phía trên.

Local **0 package/model/resource install**,0GB/0GiB. Tái dùng runtimes/resources trên D; Python dự phòng Windows đã có từ trước, chỉ đọc. Cloud smoke đo cài/cache trên scratch Kaggle **8.923.489.821bytes =8,923489821GB =8,310647515GiB**; không tính thành cài local. Artifact/log/ZIP/checkpoint tải về D đo riêng; resource bundles là hardlink tài nguyên có sẵn. Số đo426.456.453bytes ở audit trước tải checkpoint không phải số cuối hoặc allocated disk growth.

Receipt cuối `final_acceptance_receipt.json` xác nhận **1.313 hash +4 raw size/mtime không đổi**, hash lại **8 best/last checkpoint PASS**, release2 output hashes PASS, locks2light/3neural và handoffv4 PASS. Snapshot dung lượng evidence lượt này cùng4 release directory: **23.296.355.884bytes =23,296355884GB =21,696422141GiB**, đã bỏ trùng hardlink/inode; tổng logical trước bỏ trùng36.477.676.618bytes. Gồm các checkpoint tải thành công, phần tải dở giữ lịch sử, ZIP, log và workspace đã khôi phục. Có tài nguyên dùng lại trong phạm vi đo; đây là dung lượng file, **không phải dung lượng cài mới hoặc tăng allocated disk chính xác**. Receipt/log bổ sung sau snapshot có kích thước nhỏ ngoài số đo đó. Không xóa checkpoint/run frozen để làm đẹp số đo.

Git bàn giao qua checkout riêng nhánh `sprint3_huy`, giữ main/partner `print3_label100test`. Không stage gold/raw/answer/interim/venv/cache/weights hoặc nguồn chưa đủ quyền phân phối. Commit/push và SHA remote thực ghi ở acceptance cuối; thiếu auth không được báo GitHub đã nhận.

Commit bước đầu `e0b7c07` đã lưu14 file allowlist; commit kết thúc bổ sung retry regression và trạng thái nghiệm thu cuối. Git Credential Manager có sẵn đang chờ owner đăng nhập; Kaggle login/GPU đã hợp lệ nhưng không thay thế GitHub authentication. Nếu phiên không nhận credential, owner push từ **checkout bàn giao** `data/interim/modeling/sprint03/local_finish_before_colab_20261004_v2/git_handoff`, không dùng HEAD nhánh partner ở main để suy commit đã lên remote. `git_completion_receipt.json` ghi SHA cuối và trạng thái push thực.

**Chủ dự án không cần sửa/gán lại label hoặc bấm Submit.** Phần annotation/release đã chốt; bốn job Kaggle đã hoàn tất và được nghiệm thu. Cần owner can thiệp chỉ khi còn credential GitHub hoặc cổng tài nguyên Deepparse. Chấm test cuối là giai đoạn tiếp theo, không gọi dev metric là kết quả test cuối.
