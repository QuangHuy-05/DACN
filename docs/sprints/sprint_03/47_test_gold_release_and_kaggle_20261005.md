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

Locks nhẹ được làm mới từ dev evidence frozen, không chạy hoặc tune lại baseline. Dùng phiên bản lock cuối ghi trong acceptance; các lock cũ giữ lịch sử vì code identity đã thay khi sửa publisher/downloader. Hai baseline giữ lựa chọn HEUR threshold0.86 và CRF context1/c1=.1/c2=1. Neural selection chờ đủ c01/c02; Deepparse còn source/license/native resource gate, chưa chạy.

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

## Full training và bước sau

Sau smoke thật, chuẩn bị hai candidate/model theo protocol, seed42, tối đa20epoch/patience5/effective batch16. Bốn dataset private đã upload; mỗi run có ID mới. PhoBERT-CRF c01/c02 đã huấn luyện/dev score thành công; hai candidate PROPOSED-DYN đã submit trên hai slot vừa trống. Trạng thái thực sau mỗi bước nằm ở report API và acceptance cuối; không coi prepared/submitted là training complete.

| PhoBERT-CRF | Epoch được chọn | Epoch đã chạy | Exact-span micro F1 dev |
| --- | ---: | ---: | ---: |
| c01 | 12 | 17 | 93,33% |
| c02 | 8 | 13 | **93,89%** |

Đủ60 prediction mỗi candidate, completion audit cloud `AUDIT_PASS`,0issues. Báo cáo/sidecar JSON được đối chiếu hash index; checkpoint best/last đang tải và kiểm riêng. c02 thắng theo protocol dev, chưa dùng test. Bản tải toàn lịch sử được thay bằng profile `selection`: giữ toàn report/sidecar + best/last, các epoch khác nằm trên Kaggle với danh sách/hash. Các phần tải dở giữ nguyên; không gọi chúng là bản hash-verified đầy đủ. Tái dùng file đã tải bằng hardlink chỉ sau khi hash khớp **index remote được tải mới của đúng version**. Lượt backup định kỳ c01 có cảnh báo hash trong lúc alias checkpoint đang cập nhật; backup cuối và hash nghiệm thu phải đạt riêng, không bỏ qua cảnh báo.

Sau full run: xác minh artifact/checkpoint/hash → chấm dev đã freeze → chọn c01/c02 bằng dev → calibration/ablation on/off cùng checkpoint → lock → final inference input-only → freeze → scorer-only gold. Giai đoạn test chưa mở trong lượt này. Không tune từ16 case test hoặc kết quả QA test.

Deepparse full/native giữ blocker source/license/resource riêng, không dùng embedding rút gọn hoặc fixture để báo pretrained baseline hoàn tất. Data05 DEFERRED_BY_USER; VQA HOLD; T3/RAG/API ngoài phạm vi.

## Kiểm thử, dung lượng và Git

Full suite cuối: **260 test =252PASS +8SKIP,0FAIL**, bao gồm regression streaming/path/version/profile/hardlink/hash. Publisher14/14, final pipeline11/11; Colab fixture Windows8test=7PASS/1SKIP(symlink), không thay bằng chứng WSL trước. Audit WSL: **1313 frozen hash +4 raw size/mtime PASS**,0changed. Ghi acceptance/artifact cuối sau các bước mới, không cộng suite trùng.

Gói Colab `handoff_v4/` có ZIP code/resource và notebook `notebooks/sprint03/colab_train_dev_release_v4.ipynb`. Kiểm hash toàn ZIP/member, AST notebook chưa execute và `prepare` trong workspace giải nén độc lập PASS240/60. Phiên bản khóa nhẹ cuối `final_selection_v4/` giữ nguyên lựa chọn frozen dev, preflight100 text-only PASS, chưa inference. Gói Colab này chưa chạy; tích hợp/huấn luyện thật hiện ở các run Kaggle riêng phía trên.

Local **0 package/model/resource install**,0GB/0GiB. Tái dùng runtimes/resources trên D; Python dự phòng Windows đã có từ trước, chỉ đọc. Cloud smoke đo cài/cache trên scratch Kaggle **8.923.489.821bytes =8,923489821GB =8,310647515GiB**; không tính thành cài local. Artifact/log/ZIP/checkpoint tải về D đo riêng; resource bundles là hardlink tài nguyên có sẵn. Số đo426.456.453bytes ở audit trước tải checkpoint không phải số cuối hoặc allocated disk growth.

Git bàn giao qua checkout riêng nhánh `sprint3_huy`, giữ main/partner `print3_label100test`. Không stage gold/raw/answer/interim/venv/cache/weights hoặc nguồn chưa đủ quyền phân phối. Commit/push và SHA remote thực ghi ở acceptance cuối; thiếu auth không được báo GitHub đã nhận.

**Chủ dự án không cần sửa/gán lại label hoặc bấm Submit.** Phần annotation/release đã chốt. Cần owner can thiệp chỉ khi còn credential GitHub hoặc cổng tài nguyên Deepparse; trạng thái cloud đang chạy được agent tiếp tục xử lý trong lượt này.
