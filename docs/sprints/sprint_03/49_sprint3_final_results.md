# Kết quả đánh giá cuối Sprint 3 — 05/10/2026

## Trạng thái hiện hành

**SPRINT3_PARTIAL_DP_BLOCKED.** Đã chấm test cuối cho bốn mô hình và ablation cùng trọng số. Hai cấu hình Deepparse chưa có thực nghiệm pretrained/native/fine-tune vì chưa đủ bằng chứng về điều kiện sử dụng checkpoint. Giữ lựa chọn dev; không huấn luyện, tune, đổi mapping hoặc threshold sau khi xem test.

Corpus `corpus_v1_release2`: **240 train / 60 dev / 100 test**. Test có **446 span**; T1 **64 eligible / 20 null / 16 excluded**. Giữ toàn bộ T0, kể cả các mẫu bị mask T1. Task 543 chỉ mask T1/structure ở dev. Test được gán theo **AI_ASSISTED_HUMAN_REVIEW**, IAA **NOT_MEASURED**.

## 1. Kết quả theo mô hình

| Mô hình | Dev T0 F1 | Test T0 P / R / F1 | Test T1 accuracy / macro-F1 | 5 trường micro-F1 |
|---|---:|---|---|---:|
| HEUR-JW | 88.01% | 95.12% / 87.44% / 91.12% | 92.19% / 92.49% | 81.99% |
| DP-ZS-FT | — | BLOCKED: chưa rõ điều kiện sử dụng checkpoint | NOT_EXECUTED | — |
| DP-FT-FT | — | BLOCKED: chưa rõ điều kiện sử dụng checkpoint | NOT_EXECUTED | — |
| CRF-INDEP | 90.56% | 92.34% / 89.24% / 90.76% | NOT_IMPLEMENTED | 85.59% |
| PHOBERT-CRF | 93.89% | 98.43% / 98.43% / 98.43% | NOT_IMPLEMENTED | 89.94% |
| PROPOSED-DYN | 94.74% | 98.21% / 98.21% / 98.21% | 71.88% / 56.26% | 89.90% |
| PROPOSED-NO-CONSTRAINT | 94.74% | 98.43% / 98.43% / 98.43% | 71.88% / 56.26% | 89.91% |

T0 đo exact `[start,end,label]` trên chuỗi nguyên bản, toàn schema 11 nhãn; nhãn không được hỗ trợ vẫn tính FN. T1 từ chối vẫn nằm trong mẫu số 64. Track 5 trường có **4.800 hàng** sau khi loại 100 hold, là so sánh phát triển/tương thích; không gọi toàn track là test độc lập. Baseline v3 fuzzy oracle có quyền đọc metadata khác, giữ ở bảng lịch sử riêng.

| Mô hình | Trạng thái train | Nhãn hỗ trợ | Coverage gold span | Latency mean / p50 / p95 (ms) |
|---|---|---|---:|---|
| HEUR-JW | Không train | Ngo/Hem, PhuongXa, QuanHuyen, SoNha, TenDuong, TinhThanh | 444/446 | 0.82 / 0.13 / 4.49 |
| CRF-INDEP | CRF train 240, chọn trên dev | GhiChu, HuongDi, Khac, MocDinhVi, Ngo/Hem, PhuongXa, QuanHuyen, SoNha, TenDuong, TinhThanh, ToaNha/CanHo | 446/446 | 0.25 / 0.22 / 0.36 |
| PHOBERT-CRF | Checkpoint pretrained đã fine-tune; selected c02 | GhiChu, HuongDi, Khac, MocDinhVi, Ngo/Hem, PhuongXa, QuanHuyen, SoNha, TenDuong, TinhThanh, ToaNha/CanHo | 446/446 | 22.63 / 17.82 / 28.36 |
| PROPOSED-DYN | Checkpoint pretrained đã fine-tune; selected c02 | GhiChu, HuongDi, Khac, MocDinhVi, Ngo/Hem, PhuongXa, QuanHuyen, SoNha, TenDuong, TinhThanh, ToaNha/CanHo | 446/446 | 23.70 / 19.43 / 29.49 |
| PROPOSED-NO-CONSTRAINT | Checkpoint pretrained đã fine-tune; selected c02 | GhiChu, HuongDi, Khac, MocDinhVi, Ngo/Hem, PhuongXa, QuanHuyen, SoNha, TenDuong, TinhThanh, ToaNha/CanHo | 446/446 | 23.92 / 19.57 / 29.52 |
| DP-ZS-FT | Chưa có thực nghiệm pretrained/native | Chưa nghiệm thu | — | — |
| DP-FT-FT | Chưa có thực nghiệm pretrained/native | Chưa nghiệm thu | — | — |

Hai model neural dùng source submitted đã pin và hai best checkpoint: PhoBERT-CRF `19894a1e899a94c69c68bd33d091c348a7b049582090f41dc6d6a9f85b8a351e`, DYN `7a4a3d01bff1222cd303cb5ff03872c5ee49b22cb67a0572833fa470f917a589`. On/off cùng checkpoint/calibration/tokenizer/source; chỉ constraint flag khác. Config, selection lock và resource/code hash nằm trong run manifest. Mọi inference là text-only.

### Track 5 trường — so sánh development riêng

| Mô hình | Micro-F1 | Macro mean field F1 | Exact cả 5 trường |
|---|---:|---:|---:|
| HEUR-JW | 81.99% | 80.71% | 35.98% |
| CRF-INDEP | 85.59% | 85.52% | 67.42% |
| PHOBERT-CRF | 89.94% | 90.36% | 69.81% |
| PROPOSED-DYN | 89.90% | 90.17% | 69.71% |
| PROPOSED-NO-CONSTRAINT | 89.91% | 90.17% | 69.73% |

Neural có 4/4.800 mẫu abstain do alignment; giữ trong mẫu số. Per-field metric, prediction, native trace và latency được giữ trong từng run. Không dùng canonical repair hoặc impute đáp án gold.

### T1 và cấu trúc

DYN accepted **52/64**, coverage **81.25%**, accepted accuracy **88.46%**, abstain **12**. Lai có support **5**, F1 **0.00%**. Dev Lai F1=0. Các số này không chứng minh T1 ổn định trên nguồn mới.

Lỗi Quận trên gold `moi` eligible không có gold QuanHuyen: **0/12**. Không so trực tiếp với 77,5% ở run/track cũ có mẫu số khác. Recall Quận trên cũ/lai: `{"cu": {"tp": 43, "support": 45, "recall": 0.9556}, "Lai": {"tp": 5, "support": 5, "recall": 1.0}}`.

Ablation cùng checkpoint: **1 mẫu thay đổi**, **2 thay đổi span**. Delta on − off: `{"test_t0_micro_f1_on_minus_off": -0.0022, "test_district_fp_on_minus_off": 0, "test_t1_accuracy_on_minus_off": 0.0, "test_t1_abstain_on_minus_off": 0}`. Nếu delta và số mẫu thay đổi đều bằng 0, không quan sát cải thiện do constraint; không tuyên bố triệt tiêu lỗi trong mọi trường hợp.

Trong lượt test này, bật constraint **giảm 0,22 điểm phần trăm T0 F1** và không đổi lỗi Quận 0/12 hoặc T1. Một span QuanHuyen bị đổi thành PhuongXa tại mẫu `s3_224ae519b196f730`. Đây là kết quả quan sát, không là lý do đổi cấu hình đã chốt hoặc chọn lại model bằng test.

## 2. Support và phân tích lỗi

| Nhãn | Gold support | HEUR F1 | CRF F1 | PhoBERT-CRF F1 | DYN F1 |
|---|---:|---:|---:|---:|---:|
| SoNha | 88 | 100.00% | 97.14% | 100.00% | 100.00% |
| TenDuong | 99 | 87.13% | 87.00% | 99.50% | 99.00% |
| Ngo/Hem | 13 | 96.30% | 81.82% | 96.30% | 100.00% |
| ToaNha/CanHo | 0 | NOT_EVALUABLE | NOT_EVALUABLE | NOT_EVALUABLE | NOT_EVALUABLE |
| PhuongXa | 89 | 92.40% | 87.06% | 97.78% | 98.34% |
| QuanHuyen | 56 | 87.13% | 88.50% | 95.50% | 95.58% |
| TinhThanh | 99 | 88.14% | 95.38% | 99.49% | 97.94% |
| MocDinhVi | 0 | NOT_EVALUABLE | NOT_EVALUABLE | NOT_EVALUABLE | NOT_EVALUABLE |
| HuongDi | 0 | NOT_EVALUABLE | NOT_EVALUABLE | NOT_EVALUABLE | NOT_EVALUABLE |
| GhiChu | 0 | NOT_EVALUABLE | NOT_EVALUABLE | NOT_EVALUABLE | NOT_EVALUABLE |
| Khac | 2 | 0.00% | 0.00% | 0.00% | 0.00% |

Nhãn không có gold support là **NOT_EVALUABLE_NO_GOLD_SUPPORT**; giữ số scorer để tái lập nhưng không dùng làm kết luận chất lượng. Dev có 0 MocDinhVi, 0 ToaNha/CanHo và 1 HuongDi. HEUR hỗ trợ 6 nhãn; CRF/neural hỗ trợ đầu ra 11 nhãn, không có nghĩa mọi nhãn đã được học đầy đủ. Chỉ một seed **42**; không báo mean/std nhiều seed.

| Mô hình | Sai ranh giới | Sai nhãn cùng ranh giới | Span thừa | Span thiếu | Trạng thái |
|---|---:|---:|---:|---:|---|
| HEUR-JW | 12 | 2 | 4 | 36 | {"ok": 100} |
| CRF-INDEP | 23 | 8 | 0 | 0 | {"ok": 100} |
| PHOBERT-CRF | 0 | 7 | 0 | 0 | {"ok": 100} |
| PROPOSED-DYN | 0 | 8 | 0 | 0 | {"ok": 100} |
| PROPOSED-NO-CONSTRAINT | 0 | 7 | 0 | 0 | {"ok": 100} |

Sai nhãn và ranh giới được phân tích từ prediction đã freeze. Metric theo nguồn, danh sách lỗi từng mẫu và trace nằm trong mỗi run; không dùng các lỗi test để cải thiện model trong cùng release. T1 confusion/per-class support, macro gold-supported/all-11, latency mean/p50/p95 và coverage nằm trong `metrics.json`.

Overlap 5 trường: **{"unseen_registered_site_key": 4799, "seen_train": 1}**. Cùng ID/subset/hash cho mọi mô hình. Audit theo `row_group/site_group` đã đăng ký và normalized text; `unseen_registered_site_key` không chứng minh độc lập địa lý/nguồn, `UNKNOWN_OVERLAP` không được tự coi là độc lập. Metric nhóm nằm trong `scoring_v1/overlap/overlap_metrics.json`.

Latency đo batch 1, gồm `parse_spans` và tiền xử lý, không tính nạp checkpoint, không loại warmup. Light chạy CPU WSL, neural chạy GPU T4; không so tốc độ như cùng phần cứng.

## 3. Nghiệm thu P0/F1–F6

| Giai đoạn | Trạng thái | Bằng chứng trong evidence root |
|---|---|---|
| P0 | PASS | inventory, execution_policy, protected_before, git_initial |
| F1 | BLOCKED | deepparse_blocker, nguồn chính thức HTTP 200, native API review; chưa pretrained smoke/train |
| F2 | PASS | roster v5, pre-test freeze v5, light lock v7, ba neural locks, package v5 |
| F3 | PASS | kernel `huynq16/dacn-s3-final-infer-20261005-v4/1`, content/hash acceptance, 100 ID/model, global freeze trước gold |
| F4 | PASS | T0/T1/structure, 5 trường, mask 64/20/16, overlap, paired delta, recomputation |
| F5 | PASS trong phạm vi khai báo | báo cáo này, hướng dẫn 50, Gazetteer read-only acceptance |
| F6 | kiểm thử/artifact PASS; Git theo receipt cuối | 2352 protected hash + 4 raw size/mtime giữ nguyên; 274 test = 266 PASS + 8 SKIP, 0 FAIL |

Runtime modeling **52/52 PASS**, runtime CRF **13/13 PASS** được báo riêng vì có phần chồng lặp. Fixture kiểm gate/orchestration không thay thực nghiệm pretrained GPU.

## 4. Deepparse và nguồn

Model card/API chính thức [deepparse/fasttext-base](https://huggingface.co/deepparse/fasttext-base), revision `908f403d0432a8e650da41e08d01bd33d77ac47f`, chưa khai báo license weights. Package 0.11.0 dùng [LGPLv3](https://github.com/GRAAL-Research/deepparse/blob/0.11.0/LICENSE); không suy license weights từ package. [FastText vectors](https://fasttext.cc/docs/en/crawl-vectors.html) có CC-BY-SA 3.0; archive `cc.fr.300.bin.gz` HEAD **4.496.886.212 bytes**, chưa tải. Cloud có 32 GiB RAM nên blocker hiện hành là điều kiện weights, không dùng RAM local thấp làm lý do cloud không chạy.

Cần explicit upstream evidence cho checkpoint pin. Sau clearance: pretrained native smoke, DP-ZS dev/mapping/alignment, DP-FT c01/c02 theo budget cố định, chọn bằng dev rồi khóa và đánh giá. Không thay embedding bằng bản rút gọn/Vi/BPEmb dưới ID FastText. Không cần chủ dự án gán/sửa label lại.

## 5. Gazetteer và phạm vi hoãn

Read-only `s3_v4_nso_dual_snapshot_release2`: **14.149 entity / 10.597 edge / 187 alias / 5 non-atomic**, 471 khóa cũ nhiều đích, không thiếu khóa cha. **8.607 mã cũ + 3.355 mã mới verified**, **2.187 mã cũ unresolved**. Hai snapshot 30/06 và 01/07/2025 không là lịch sử interval pháp lý; không suy geometry hoặc ép đích 1-N/M-N. Terms tái phân phối CSV còn gap, package giữ local/private. Lookup không thay thực nghiệm T2: **NOT_EXECUTED**.

Data05 **DEFERRED_BY_USER**, VQA **HOLD**, IAA **NOT_MEASURED**. T3, RAG, API/Docker, ViBERT ngoài phạm vi hiện hành. Test provenance kết hợp vẫn chưa xác minh, không gọi 100 địa chỉ benchmark là 100 quan sát thật.

## 6. Trouble, dung lượng và GitHub

Kaggle từ chối title quá 50 ký tự; sửa metadata trong package mới. Ba job trước giữ nguyên: v1 lỗi import shared primitive trong source cũ; v2 bị gate `dev` ở track 5 trường; v3 lỗi tạo JVM lần hai. Chứng minh bằng fixture rồi sửa **orchestration**: dùng bridge đã pin, đổi outer run ID trung tính, mỗi model/track chạy trong process riêng. Không thay model source/checkpoint/calibration và chưa đọc gold lúc sửa. Job v4 đã kiểm artifact/hash thật, không chỉ dựa vào API COMPLETE.

Local cài mới **0 package/model = 0 bytes / 0 GB / 0 GiB**. Artifact mới tại snapshot audit sau khử trùng hardlink/inode: **1,672,806,161 bytes = 1.672806 GB = 1.557922 GiB**; receipt ghi rõ chưa tính các file tài liệu/Git viết sau snapshot. Snapshot đóng bàn giao bổ sung tại `storage_receipt_v2.json`. Cloud runtime/cache của job đã nghiệm thu đo riêng: **8.923.520.962 bytes = 8,923521 GB = 8,310677 GiB**, không nằm trên D và không phải số dung lượng đĩa local tăng. Ba job lỗi có snapshot riêng, không cộng thành dung lượng đang giữ trên máy local. 23,296 GB lịch sử không tính vào lượt cài mới; disk-free delta không được coi là allocated growth riêng của lượt này.

Cloud cài CPython 3.11 qua uv 0.8.22, Torch 2.8.0 CUDA 12.8 từ index chính thức và dependencies pin trong `configs/colab/sprint03/requirements_transitive_v1.txt`, gồm Transformers 4.57.1, py-vncorenlp 0.1.4, Deepparse 0.11.0/Poutyne 1.17.4. Package Deepparse có mặt trong runtime chung nhưng không có pretrained DP experiment. Tái dùng PhoBERT revision `01daacda68afe13d83023d16ec647239e344a1e6`, VnCoreNLP commit `62bbc58fe5d113c898eae112656be97dcf50b3a0`, Temurin Java 17.0.20.1+1 và checkpoint đã tải ở lượt trước. Nguồn, hash, terms và full package list trong resource inventory/legal notices và `cloud_packages.txt`; không tải model mới ở lượt này.

Tái tính độc lập T0/T1 và toàn bộ 5-field overall/per-dataset đều PASS. `execution_registry.json` gán ID duy nhất theo kernel/version/output cho mọi lượt, kể cả job lỗi; trường `run_id` trong model config cũ là nhãn cấu hình đã khóa và có thể được tái dùng, không dùng riêng trường đó để xác định một lần thực thi. Không sửa lại manifest frozen để đổi tên.

Evidence private: `data/interim/modeling/sprint03/final_completion_20261005_v1/`, gồm freeze, results index, recomputation, artifact index, storage và Git receipt. Git không chứa gold/raw/answer/weights/cache hoặc Gazetteer chưa cleared. Branch **sprint3_huy**, commit/push SHA thực theo `git_final_receipt.json`. [Hướng dẫn tái lập và bàn giao](50_sprint3_reproduction_and_handoff.md).
