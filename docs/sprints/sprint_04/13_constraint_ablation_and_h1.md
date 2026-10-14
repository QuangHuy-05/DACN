# 13. Ablation ràng buộc giải mã và tuyên bố về H1 (WP5)

**Ngày chạy:** 14–15/10/2026 (thư mục đặt tên theo kế hoạch: `constraint_ablation_20261017_v1`). **Phạm vi:** giải mã lại trên CPU từ emission đã lưu trong prediction đã freeze; **không** suy luận lại mô hình neural, **không** dựng adapter khóa. Tham số CRF đọc từ checkpoint bằng `torch.load` (chỉ đọc tensor).
**Mã:** `src/evaluation/constraint_ablation.py`, `scripts/72_run_constraint_ablation.py`, `tests/test_group1_constraint_ablation.py`.
**Đầu ra:** `data/processed/evaluation/sprint04/constraint_ablation_20261017_v1/` (`metrics.json`, `run_manifest.json`, `tables/*.csv` utf-8-sig); tham số CRF và đường giải mã lại theo dòng ở `data/interim/modeling/sprint04/constraint_ablation_20261017_v1/` (`crf_params/`, `redecode/`).
**Ràng buộc được kiểm:** cấm hai nhãn BIO `B-QuanHuyen` / `I-QuanHuyen` (id 11, 12) trong Viterbi khi một nguồn T1 dự đoán "moi". Nguồn T1 là thứ duy nhất thay đổi giữa các ablation.

## 1. Trạng thái đầu ra

| Đầu ra | Trạng thái |
|---|---|
| Trích tham số CRF (8 checkpoint: DYN và PCRF của Kaggle; 3 seed × 2 của WP3b) | PASS — SHA-256 Kaggle khớp (`7a4a3d01…`, `19894a1e…`); mask BIO trong checkpoint khớp `labels.py` ở cả 8 |
| **Cổng kiểm tra** (17 file prediction, mọi tập) | **PASS** — mục 3 |
| 1. Ghép cặp bật/tắt (test Kaggle, 3 seed, track 5 trường, dev) | PASS |
| 2. Dư địa | PASS (test: 0 / 25 gold-new, 0 / 12 trong tập T1-eligible) |
| 3. Ablation nguồn T1 (DYN, HEUR-JW) + ORACLE tách riêng | PASS (test, seed, 5 trường, dev); ORACLE ghi `ORACLE_UPPER_BOUND` |
| 4. Bảng 2×2 trên test Kaggle | PASS (thêm ba seed và dev làm đối chiếu) |
| 5. Lặp mục 1–3 cho ba seed WP3b | PASS (nhãn `LOCAL_CPU_RETRAINED`, báo từng seed) |
| Tập stress T1 (`t1_stress_v1`) của kế hoạch 06 | NOT_RUN — không có prediction DYN kèm emission trên tập này; sinh chúng cần suy luận neural |
| 5 trường × PHOBERT-CRF (ô "không T1 + ràng buộc" trên 5 trường) | NOT_RUN — prompt chỉ yêu cầu 2×2 trên test; `pcrf_5field` có emission nhưng không nằm trong phạm vi |
| H1 (type / gazetteer adapter) | **NOT_TESTABLE** (mục 9) |

## 2. Kết luận ngắn

1. **Trên test Sprint 3 (và ba seed cục bộ, và dev) ràng buộc không có tác dụng quan sát được.** Dư địa bằng 0: không có mẫu gold-new nào mà đường giải mã *không* ràng buộc vẫn dự đoán `QuanHuyen` (0/25; 0/12 T1-eligible; ngoại lệ duy nhất là seed 1337 với 1 mẫu, T1 của DYN dự đoán "cu" cho mẫu đó). Ràng buộc kích hoạt ở 20 mẫu (Kaggle) / 28 / 31 / 3 (ba seed) và 13 (dev) nhưng đổi đúng 1 / 0 / 0 / 0 / 0 mẫu; cái đổi duy nhất (`s3_224ae519b196f730`) là **làm hại**: T1 của DYN đoán "moi" cho một mẫu gold "cu" và ràng buộc xóa một `QuanHuyen` đúng.
2. **ORACLE (T1 gold) cũng không giúp trên test:** Δ F1 = 0 ở Kaggle, seed 42, seed 2025, dev-DYN; +0,0022 (1 mẫu sửa đúng) ở seed 1337. Ngay cả T1 hoàn hảo cũng chỉ có 1 mẫu để sửa trên 100 mẫu test × 4 checkpoint. **Điểm nghẽn không phải là ràng buộc mà là dư địa: đường giải mã không ràng buộc không sinh `QuanHuyen` cho địa chỉ mới. Đó là đặc tính của emission (encoder + lớp tuyến tính), không phải của transitions CRF: tham số CRF đã trích có độ lớn dưới 0,07 (transitions trong [−0,068; +0,045]) so với khoảng cách top-1/top-2 của emission trung vị 3,29, nên giải mã gần như argmax emission dưới mặt nạ BIO.**
3. **Track 5 trường (development) là nơi duy nhất có dư địa:** 168/1.861 mẫu gold-new (9,0%) vẫn bị dự đoán `QuanHuyen` (134 ở `02_noisy`, 34 ở `04_missing`). ORACLE sửa 50, làm hại 4, "trung tính" 114 (nghĩa là số lỗi fp+fn không đổi, xem mục 7b về lý do): Δ F1 = +0,0019 [+0,0013; +0,0025]; theo metric 5 trường nghiêm ngặt này cận trên đánh giá thấp tác dụng gán nhãn. Nhưng T1 của DYN chỉ nói "moi" ở **4/168** mẫu đó (147 mẫu bị đoán "cu", 17 từ chối), nên ràng buộc thật của DYN đổi 5 mẫu, 0 sửa đúng, 1 làm hại: Δ F1 = −0,00007 [−0,00022; 0]. T1 của HEUR-JW còn tệ hơn trên track này (12 mẫu đổi: 1 sửa, 5 hại, 6 trung tính; Δ F1 = −0,00027 [−0,00061; −0,000005], CI chạm 0 ở biên).
4. **Bảng 2×2:** trên test Kaggle, có/không đầu T1 và có/không ràng buộc cho cùng F1 0,9843 ở ba ô và 0,9821 ở ô DYN; mọi chênh nằm trong CI và trong std giữa seed (0,0030 / 0,0111). Không có ô nào phân biệt được với ô khác.
5. **H1 là `NOT_TESTABLE`.** Ablation này kiểm "đầu T1 + giải mã có ràng buộc", không phải adapter; không là bằng chứng ủng hộ hay bác bỏ H1.

## 3. Cổng kiểm tra (làm trước mọi phân tích)

Với mỗi file prediction: (a) giải mã lại **không cấm nhãn nào** phải ra đúng `trace.path_before_constraint` ở 100% dòng; (b) giải mã lại với tập cấm `{B-QuanHuyen, I-QuanHuyen}` phải ra đúng `trace.path_after_constraint` ở 100% dòng có `ban_district = true`; (c) ở dòng không kích hoạt (và mọi dòng của file tắt ràng buộc) `path_after == path_before`; (d) đường `path_after` giải mã ngược về span phải bằng span đã lưu; (e) Viterbi tự viết (có đếm hòa) phải bằng `viterbi_reference` của repo ở cả hai chế độ. Mỗi mục sai ở bất kỳ dòng nào thì dừng (mã thoát 2 trước khi đọc gold); không nới tiêu chí.

| Tập / file | Dòng | Giải mã được | Không emission | Dòng `ban_district` | (a) lệch | (b) lệch | (c) lệch | (d) lệch | (e) lệch | Hòa | Kết quả |
|---|---|---|---|---|---|---|---|---|---|---|---|
| test Kaggle: DYN bật / DYN tắt / PCRF | 100 ×3 | 100 | 0 | 20 / 0 / 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| seed 42: DYN bật / tắt / PCRF | 100 ×3 | 100 | 0 | 28 / 0 / 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| seed 1337: DYN bật / tắt / PCRF | 100 ×3 | 100 | 0 | 31 / 0 / 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| seed 2025: DYN bật / tắt / PCRF | 100 ×3 | 100 | 0 | 3 / 0 / 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| track 5 trường: DYN bật / tắt | 4.800 | 4.796 | 4 (abstain) | 959 / 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| dev Kaggle: DYN không ràng buộc / PCRF | 60 | 60 | 0 | 0 / 0 | 0 | — | 0 | 0 | 0 | 0 | PASS (không có kiểm (b) trên file đã khóa) |
| dev Kaggle: DYN có ràng buộc `…_dev_proposed_dyn_v1` (**chỉ để kiểm (b)**) | 60 | 60 | 0 | 13 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |

**Xử lý hòa điểm:** nhãn có chỉ số nhỏ nhất thắng ở mọi bước (cùng quy tắc `viterbi_reference` và `max` của Torch). Cột "Hòa" đếm số dòng có ít nhất một bước hòa chính xác giữa hai lựa chọn hữu hạn: **0 dòng** ở mọi tập và cả hai chế độ, nên quy tắc hòa không ảnh hưởng đến kết quả nào ở đây. 4 dòng không emission của track 5 trường là các `abstain` (không có đường giải mã); chúng giống hệt ở hai chế độ và giữ nguyên span rỗng đã lưu.

Giới hạn của cổng: cổng **không nhạy với tham số CRF**. Giải mã lại `dyn_test` của Kaggle bằng tham số PCRF Kaggle hay bằng tham số toàn 0 cũng cho 0/100 dòng lệch `path_before` và 0/20 dòng lệch `path_after` (đã tự tính lại); vì vậy cổng chứng minh cài đặt Viterbi và việc dùng đúng emission, còn tham số đúng checkpoint được xác nhận bằng SHA-256 checkpoint (và 8/8 tensor khớp JSON).

Ghi chú về dev: bằng chứng chọn mô hình của DYN trên dev chỉ chứa run **không** ràng buộc, nên phân tích dev dùng file đó (khớp hash theo khóa chọn) và áp ràng buộc bằng giải mã lại với T1 posterior đã lưu. File dev **có** ràng buộc nằm cạnh (`…_dev_proposed_dyn_v1`) không thuộc bằng chứng chọn; mình chỉ dùng nó làm tham chiếu kiểm (b), không báo số từ nó.

Kiểm chéo thêm trên các tập có cả file bật và tắt (test Kaggle, 3 seed): tổng (tp, fp, fn) tính lại bằng giải mã lại với nguồn T1 của DYN **bằng đúng** tổng tính từ span đã lưu của file bật, và đường không ràng buộc bằng đúng file tắt; điểm tái lập T0 F1 khớp điểm công bố ở 4 chữ số (PHOBERT-CRF 0,9843; NO-CONSTRAINT 0,9843; DYN 0,9821). Std giữa seed tính lại: PCRF 0,0030, DYN 0,0111 — khớp số WP3b.

## 4. Cách làm và nhãn

- **Nguồn T1 (cùng quy tắc cấm `QuanHuyen` khi nguồn nói "moi"):** (a) **DYN** — `predicted_system` từ posterior đã lưu, ngưỡng 0,7 / margin 0,2 như đã khóa (bằng `ban_district` đã lưu: đã kiểm trùng 100% dòng); (b) **HEUR-JW** — `predicted_system` trong prediction đã freeze (test: `light_test_runs_v2/heur-jw`; track 5 trường: `heur_jw_followup_fivefield_20261003_v1`, vì chỉ run này có cấu hình trùng cấu hình test đã khóa — cùng adapter `heur_jw_followup`, quy tắc `…dual_snapshot_v4`, gazetteer `s3_v4_nso_dual_snapshot`, ngưỡng 0,86; run `heur_jw_5field_20261002_v1` dùng quy tắc v3 và gazetteer s3_v2; dev: run threshold 0,86 đã khớp hash theo khóa chọn); `khong_ro`/abstain = không cấm; (c) **ORACLE_UPPER_BOUND** — `address_system` của gold (test, dev) hoặc `HeQuyChieu` (5 trường) bằng "moi".
- Mỗi dòng chỉ có hai kết quả có thể: đường không ràng buộc hoặc đường cấm `QuanHuyen`. Mọi nguồn T1 chỉ chọn một trong hai trên từng dòng, nên chấm điểm một lần mỗi dòng rồi chọn.
- **Phân loại thay đổi theo dòng** (chỉ trên dòng nguồn nói "moi" **và** đường giải mã đổi): so (fp + fn) trước/sau theo gold — `sửa đúng` nếu giảm, `làm hại` nếu tăng, `trung tính` nếu bằng (không có nghĩa là "vẫn sai chỗ khác": xem 7b). Số span đổi = |đối xứng hiệu| hai tập span (start, end, nhãn).
- **Chấm điểm:** test, dev, seed: T0 micro-F1 theo span chính xác (scorer Sprint 3 qua `frozen_reliability.build_units`; CI bootstrap theo mẫu, B = 10.000, seed 20261014). Track 5 trường: scorer 5 trường nghiêm ngặt (`score_prediction_pair`, micro-F1 trên 5 trường) trên 4.800 dòng; CI bootstrap theo dòng (xem giới hạn).
- **Nhãn tập:** test Kaggle = `SPRINT3_TEST_OBSERVED_POSTHOC` (test 100 mẫu đã bị quan sát); seed = `LOCAL_CPU_RETRAINED` (cùng test, hậu nghiệm); track 5 trường = `DEVELOPMENT_TRACK`; dev = `SELECTION_SET` (đã dùng chọn mô hình, không phải ước lượng không chệch). Không dùng test để chọn, tinh chỉnh hay đổi bất cứ gì.
- `run_manifest.json` được ghi (giai đoạn `PRE_SCORING`: hệ thống, luật, seed, hash đầu vào, hash mã) **trước khi** mở gold; sau chấm điểm cùng file được ghi lại thành `COMPLETE` kèm hash đầu ra và `pre_scoring_manifest_sha256`.

- Thư mục `*_5field_raw` (`dyn_5field_raw`, `dyn_off_5field_raw`, `pcrf_5field_raw`) là cùng prediction của track 5 trường nhưng ghi theo track `T0_T1_DEV`: `dyn_5field_raw` có cùng 4.800 dòng, `spans` và `path_after` giống hệt `dyn_5field`, chỉ thiếu các khóa `dataset`, `source_row`, `fields`. Phân tích dùng bản `*_5field` (có khóa để nối gold).

## 5. Bảng 1 — Ghép cặp bật/tắt (nguồn T1 = đầu T1 của DYN)

| Tập | Nhãn | Dòng | Kích hoạt | Dòng đổi | Span đổi | Sửa đúng / Hại / Trung tính | F1 tắt | F1 bật | Δ F1 [CI ghép cặp 95%] |
|---|---|---|---|---|---|---|---|---|---|
| test Kaggle (T4, seed 42) | `SPRINT3_TEST_OBSERVED_POSTHOC` | 100 | 20 | 1 | 2 | 0 / 1 / 0 | 0,9843 | 0,9821 | −0,0022 [−0,0068; 0,0000] |
| seed 42 | `LOCAL_CPU_RETRAINED` | 100 | 28 | 0 | 0 | 0 / 0 / 0 | 0,9708 | 0,9708 | 0,0000 [0,0000; 0,0000] |
| seed 1337 | `LOCAL_CPU_RETRAINED` | 100 | 31 | 0 | 0 | 0 / 0 / 0 | 0,9910 | 0,9910 | 0,0000 [0,0000; 0,0000] |
| seed 2025 | `LOCAL_CPU_RETRAINED` | 100 | 3 | 0 | 0 | 0 / 0 / 0 | 0,9730 | 0,9730 | 0,0000 [0,0000; 0,0000] |
| track 5 trường (F1 5 trường) | `DEVELOPMENT_TRACK` | 4.800 | 959 | 5 | 10 | 0 / 1 / 4 | 0,8991 | 0,8990 | −0,00007 [−0,00022; 0,0000] |
| dev | `SELECTION_SET` | 60 | 13 | 0 | 0 | 0 / 0 / 0 | 0,9474 | 0,9474 | 0,0000 [0,0000; 0,0000] |

Cặp "tắt = bật không đổi" cho CI `[0; 0]`: đó là hệ quả của không có dòng nào khác nhau, không phải độ chính xác cao. Với test Kaggle, CI chạm 0 ở biên vì chỉ có **một** mẫu bất đồng (cùng giải thích như báo cáo 11 mục 3); kết luận hợp lệ là "không có lợi ích đo được", không phải "ràng buộc gây hại có ý nghĩa thống kê". Mẫu đổi duy nhất của test Kaggle: `s3_224ae519b196f730`, gold "cu", `QuanHuyen` → `PhuongXa` — lỗi T1 truyền thành lỗi T0. Ở track 5 trường, 5 dòng đổi: 4 dòng gold-moi (trung tính; cả 4 là `PhuongXa: FN→MISMATCH`, cùng kiểu chuẩn hóa bề mặt như mục 7b) và 1 dòng gold-cu (hại).

## 6. Bảng 2 — Dư địa (số lỗi tối đa mà ràng buộc có thể sửa)

Dư địa = số mẫu gold-new (không có `QuanHuyen` trong gold) mà đường giải mã **không ràng buộc** vẫn dự đoán một span `QuanHuyen`. Cột "T1-eligible" áp mask T1 của scorer (loại 16 ID khai báo): test có 25 mẫu gold-new, trong đó 12 là T1-eligible (số "0/12" đã biết).

| Tập (checkpoint) | Gold-new | T1-eligible | **Dư địa** | Dư địa (T1-eligible) | T1 DYN trên dư địa: moi / cu / Lai / khong_ro | T1 HEUR-JW trên dư địa: moi / cu / Lai / khong_ro | Cấm vô điều kiện loại được | `QuanHuyen` bị xóa bởi ràng buộc DYN (trong dư địa) |
|---|---|---|---|---|---|---|---|---|
| test Kaggle — DYN | 25 | 12 | **0** | 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 | 0 |
| test Kaggle — PHOBERT-CRF | 25 | 12 | **0** | 0 | — | 0 / 0 / 0 / 0 | 0 | — |
| seed 42 — DYN / PCRF | 25 | 12 | **0 / 0** | 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 | 0 |
| seed 1337 — DYN | 25 | 12 | **1** | 0 | 0 / **1** / 0 / 0 | 0 / 0 / 0 / 1 | 1 | **0** |
| seed 1337 — PCRF | 25 | 12 | **0** | 0 | — | 0 | 0 | — |
| seed 2025 — DYN / PCRF | 25 | 12 | **0 / 0** | 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 | 0 |
| dev — DYN (không ràng buộc) | 15 | 14 | **0** | 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 | 0 |
| dev — PHOBERT-CRF | 15 | 14 | **1** (không T1-eligible) | 0 | — | 0 / 0 / 0 / 1 | 1 | — |
| track 5 trường — DYN | 1.861 | 1.861 | **168** | 168 | **4** / 147 / 0 / 17 | 7 / 3 / 1 / 157 | 168 | **4** |

Phân bố dư địa 5 trường: `02_noisy` 134 (trên 490 mẫu gold-new), `04_missing` 34 (trên 391), `01_new` 0 (trên 980). Rủi ro "ngược": 1 mẫu gold có `QuanHuyen` mà DYN T1 đoán "moi" và ràng buộc xóa `QuanHuyen` đúng đó (test Kaggle: 1; 5 trường: 1; seed và dev: 0).

**Đọc kết quả:** test, seed (trừ một mẫu của seed 1337 không phải T1-eligible) và dev có dư địa 0 → ràng buộc không có gì để sửa; nói đúng như vậy. Dư địa chỉ tồn tại trên track 5 trường (nhiễu OCR và thiếu trường), và ở đó T1 của DYN bỏ lỡ 164/168 mẫu.

## 7. Bảng 3 — Ablation nguồn T1 (giải mã lại trên emission của DYN; ORACLE ở bảng riêng 7b)

| Tập | Nguồn T1 | Kích hoạt | Dòng đổi | Span đổi | Sửa đúng / Hại / Trung tính | F1 tắt → có ràng buộc | Δ F1 [CI] |
|---|---|---|---|---|---|---|---|
| test Kaggle | (a) DYN | 20 | 1 | 2 | 0 / 1 / 0 | 0,9843 → 0,9821 | −0,0022 [−0,0068; 0,0000] |
| test Kaggle | (b) HEUR-JW | 10 | 0 | 0 | 0 / 0 / 0 | 0,9843 → 0,9843 | 0,0000 [0,0000; 0,0000] |
| seed 42 | DYN / HEUR-JW | 28 / 10 | 0 / 0 | 0 / 0 | — | 0,9708 → 0,9708 | 0,0000 |
| seed 1337 | DYN / HEUR-JW | 31 / 10 | 0 / 0 | 0 / 0 | — | 0,9910 → 0,9910 | 0,0000 |
| seed 2025 | DYN / HEUR-JW | 3 / 10 | 0 / 0 | 0 / 0 | — | 0,9730 → 0,9730 | 0,0000 |
| track 5 trường | (a) DYN | 959 | 5 | 10 | 0 / 1 / 4 | 0,8991 → 0,8990 | −0,00007 [−0,00022; 0,0000] |
| track 5 trường | (b) HEUR-JW | 428 | 12 | 24 | 1 / 5 / 6 | 0,8991 → 0,8988 | −0,00027 [−0,00061; −0,000005] (CI chạm 0 ở biên: cận trên đổi giữa −0,000005 và 0,0 theo thứ tự dòng/seed bootstrap) |
| dev | DYN / HEUR-JW | 13 / 11 | 0 / 0 | 0 / 0 | — | 0,9474 → 0,9474 | 0,0000 |

HEUR-JW tốt hơn DYN ở T1 trên test (0,9219 so với 0,7188) nhưng hơn không dịch thành lợi ích T0, vì dư địa là 0 ở đó. Ở track 5 trường thay T1 tốt hơn trên test bằng T1 của HEUR-JW không giúp: HEUR-JW ban 428 mẫu, chỉ 7/168 mẫu dư địa được nói "moi" (157 là `khong_ro`), còn 5 mẫu hại (3 gold-cu, 2 gold-Lai). Trên track 5 trường, ban theo HEUR-JW trên mẫu gold-cu/Lai lặp lại đúng loại lỗi của DYN (xóa `QuanHuyen` đúng).

### 7b. ORACLE_UPPER_BOUND (T1 gold) — **cận trên, không phải kết quả mô hình, không vào bảng so sánh**

| Tập | Checkpoint | Dòng ban | Dòng đổi | Sửa đúng / Hại / Trung tính | F1 tắt → ORACLE | Δ F1 [CI] |
|---|---|---|---|---|---|---|
| test Kaggle | DYN / PCRF | 25 | 0 / 0 | 0 | 0,9843 → 0,9843 | 0,0000 |
| seed 42 | DYN / PCRF | 25 | 0 / 0 | 0 | 0,9708 / 0,9764 (không đổi) | 0,0000 |
| seed 1337 | DYN | 25 | 1 | 1 / 0 / 0 | 0,9910 → 0,9933 | +0,0022 [0,0000; +0,0069] |
| seed 1337 | PCRF | 25 | 0 | 0 | 0,9775 (không đổi) | 0,0000 |
| seed 2025 | DYN / PCRF | 25 | 0 / 0 | 0 | không đổi | 0,0000 |
| dev | DYN / PCRF | 15 | 0 / 1 | 0 / 1 sửa | 0,9474 / 0,9389 → 0,9424 (PCRF) | 0,0000 / +0,0035 [0,0000; +0,0109] |
| track 5 trường | DYN | 1.861 | **168** | 50 / 4 / 114 | 0,8991 → 0,9009 | **+0,0019 [+0,0013; +0,0025]** |

**Ngay cả T1 hoàn hảo cũng không giúp trên test Sprint 3**: 0 mẫu để sửa ở Kaggle, 1 mẫu ở một trong ba seed. Chỉ trên track 5 trường (development, có nhiễu OCR) cận trên có số đo: +0,0019 F1 với 168 mẫu đổi (50 sửa, 4 hại, 114 "trung tính").

**Về 114 dòng "trung tính" (và 4 dòng của DYN, 6 của HEUR-JW):** không phải "vẫn sai ở chỗ khác". Đã đếm lại trạng thái từng trường (TP/TN/FP/FN/MISMATCH) giữa đường tự do và đường cấm: 84 dòng có `QuanHuyen: FP→TN` kèm `TinhThanh: FN→MISMATCH`; 29 dòng có `QuanHuyen: FP→TN` kèm `PhuongXa: FN→MISMATCH`; 1 dòng có `QuanHuyen: FP→TN` kèm `PhuongXa: TN→FP`. Ví dụ `D02_0` "213; Phố Lương Định Của; P.Phương Liễu; Tinh Bac Ninh": đường tự do gán "Tinh Bac Ninh" vào `QuanHuyen`, đường cấm gán đúng vào `TinhThanh`, nhưng scorer 5 trường nghiêm ngặt so văn bản bề mặt chưa chuẩn hóa với `GT_*` đã chuẩn hóa của `02_noisy` ("Tỉnh Bắc Ninh"), nên lỗi chuyển từ FP sang MISMATCH và tổng fp+fn không đổi. Do đó **cận trên ORACLE +0,0019 theo metric này đánh giá thấp tác dụng gán nhãn của ràng buộc**; nếu chấm theo nhãn/biên span, phần lớn 114 dòng này sẽ là sửa đúng. Vì metric 5 trường và test span là hai thước đo khác nhau trên hai tập khác nhau, báo cáo này **không** so cận trên +0,0019 với std giữa seed (0,0111, T0 span F1 trên test) hay hiệu mô hình (+0,07, test).

## 8. Bảng 4 — 2×2 {có/không đầu T1 khi huấn luyện} × {có/không ràng buộc khi giải mã} (test Sprint 3)

PCRF và DYN là **hai lần huấn luyện khác nhau** (không cùng checkpoint); chỉ ô DYN và NO-CONSTRAINT dùng chung một checkpoint. Giải thích mọi chênh giữa hàng bằng std giữa seed của WP3b (T0 F1: PCRF 0,0030, DYN 0,0111; đã tính lại và khớp).

| Có đầu T1 khi huấn luyện | Ràng buộc khi giải mã | Hệ | Test Kaggle (T4) F1 [CI] | Δ so với PCRF [CI ghép cặp] | Seed 42 | Seed 1337 | Seed 2025 |
|---|---|---|---|---|---|---|---|
| không | không | PHOBERT-CRF | 0,9843 [0,9720; 0,9936] | — | 0,9764 | 0,9775 | 0,9821 |
| có | không | PROPOSED-NO-CONSTRAINT | 0,9843 [0,9724; 0,9935] | 0,0000 [−0,0112; +0,0113] | 0,9708 | 0,9910 | 0,9730 |
| có | có (T1 của DYN) | PROPOSED-DYN | 0,9821 [0,9691; 0,9933] | −0,0022 [−0,0137; +0,0091] | 0,9708 | 0,9910 | 0,9730 |
| không | có (T1 ngoài: HEUR-JW) | emission PCRF + T1 HEUR-JW | 0,9843 [0,9720; 0,9936] | 0,0000 [0,0000; 0,0000] | 0,9764 | 0,9775 | 0,9821 |

Ô "không T1 + ràng buộc" (T1 ngoài từ HEUR-JW) không đổi gì so với PCRF thuần ở cả bốn bộ checkpoint (0 dòng đổi). Ô tương ứng với T1 gold nằm ở bảng 7b (ORACLE), không ở đây. Dev (nhãn `SELECTION_SET`): PCRF 0,9389; NO-CONSTRAINT 0,9474; DYN 0,9474; PCRF + HEUR-JW 0,9389 (chi tiết `tables/model_comparison_2x2.csv`).

Trung bình ± std ba seed cục bộ (n = 3, ddof = 1): PCRF 0,9787 ± 0,0030; DYN (bật = tắt) 0,9783 ± 0,0111; PCRF + HEUR-JW 0,9787 ± 0,0030; Δ DYN bật − tắt = 0,0000 ± 0,0000; Δ HEUR-JW-ban = 0,0000 ± 0,0000. Ô "emission PCRF + T1 ngoài" giống hệt PCRF thuần vì không có dòng nào đổi.

**Lưu ý seed 1337:** PROPOSED-NO-CONSTRAINT so PHOBERT-CRF là +0,0135 [+0,0011; +0,0276] (CI ghép cặp loại 0). Kết luận "không kết luận được" vẫn đứng vì ba seed đổi dấu (−0,0056, +0,0135, −0,0090) và đây là hai lần huấn luyện khác nhau.

**Diễn giải:** hàng "có T1" so hàng "không T1" lệch từ −0,0090 đến +0,0135 tùy seed (dấu đổi), cùng cỡ std giữa seed của DYN; không kết luận được đầu T1 giúp hay hại T0. Hàng "ràng buộc" so hàng "không ràng buộc" lệch đúng 0 ở mọi seed và −0,0022 ở Kaggle (1 mẫu). Hai hiệu ứng này không tách khỏi nhau với dữ liệu này (cùng một checkpoint DYN đóng góp cả hai chiều).

## 9. Mục trung thực — H1 và tuyên bố của mô hình đề xuất

### 9.1 H1 = `NOT_TESTABLE`

H1 của đề cương: gỡ từng adapter (type adapter / gazetteer adapter) làm giảm kết quả. **Không adapter nào được hiện thực trong repo**, nên không có thứ để gỡ. Những gì ablation này đo (đầu T1 tuyến tính + ràng buộc giải mã theo confidence) là thứ **khác** với những gì H1 nêu; kết quả ở trên không ủng hộ cũng không bác bỏ H1.

| Đề cương (mục 4.1) hứa | Đã hiện thực (checkpoint `PROPOSED-DYN` c02) |
|---|---|
| PhoBERT làm encoder | Có: PhoBERT + pooling theo đơn vị |
| Gazetteer adapter đa phiên bản (trước/sau 01/07/2025) | **Không**; gazetteer chỉ được dùng ở HEUR-JW, ở tra cứu T2 và ở `T1-PIPE` (WP2) — bên ngoài mạng |
| Type adapter theo loại đơn vị hành chính | **Không** |
| Global pointer cho span | **Không**: đầu ra là CRF tuyến tính BIO 23 nhãn |
| Decoder B: đầu phân loại 3 lớp (T1: cũ / mới / lai) | **Có**: đầu T1 tuyến tính ba lớp (loss T0 + 0,5 × loss T1 trên mẫu eligible, trọng số nhất quán = 0) |
| (đề cương không nêu) | Có: ràng buộc giải mã cấm `QuanHuyen` khi T1 đoán "moi" với ngưỡng 0,7 / margin 0,2 (chỉ thành phần này là ngoài đề cương) |

`T1-PIPE` của WP2 là một cách đưa gazetteer vào T1 (ghép span hành chính của một mô hình T0 với bước `_resolve` của HEUR-JW, xem `src/evaluation/t1_pipeline.py` và báo cáo 10), **không phải adapter của H1**: nó chạy ngoài mạng, sau khi đã có span T0, và không điều chỉnh biểu diễn của PhoBERT.

### 9.2 Kết luận về ràng buộc (theo đúng số)

**Không quan sát được tác dụng** trên test Sprint 3, trên ba seed huấn luyện lại, và trên dev: dư địa 0 (một ngoại lệ 1 mẫu ở seed 1337 mà T1 của DYN đoán sai), ban kích hoạt 3–31 mẫu nhưng đổi 0 đường giải mã (Kaggle: 1 đường, làm hại). **Có hại rất nhỏ** trên test Kaggle (−0,0022, 1 mẫu, CI chạm 0) và trên track 5 trường (DYN −0,00007, CI chạm 0; HEUR-JW −0,00027, CI theo dòng chạm 0 ở biên và quá hẹp vì hàng không độc lập, mục 10.2): độ lớn nhỏ hơn nhiều std giữa seed. **Có dư địa thật nhưng chỉ ở dữ liệu nhiễu/thiếu trường** (track 5 trường: 168 mẫu), ở đó cận trên ORACLE là +0,0019 F1; DYN chỉ khai thác được 4/168 vì T1 đoán sai hoặc từ chối ở 164 mẫu.

Tách phần **đã đo** khỏi phần **suy luận**. *Đã đo:* (i) dư địa 0 trên test Kaggle, ba seed (trừ 1 mẫu), dev và `01_new` của track 5 trường — đường giải mã không ràng buộc không sinh `QuanHuyen` cho địa chỉ mới ở đó; (ii) T1 của DYN yếu (accuracy 0,72, `Lai` F1 = 0), nên khi ràng buộc kích hoạt nó từng kích hoạt trên mẫu cu (hại, 1 mẫu test) và bỏ lỡ 164/168 mẫu moi trong dư địa 5 trường; (iii) ORACLE không đổi gì trên test Kaggle. *Suy luận (không có thí nghiệm cô lập):* cơ chế của (i) là đặc tính của emission (encoder + lớp tuyến tính) chứ không phải của transitions CRF, vì tham số CRF nhỏ (< 0,07) so với khoảng cách top-1/top-2 của emission (trung vị 3,29); từ đó ràng buộc là thừa trên dữ liệu sạch. Dư địa chỉ xuất hiện ở `02_noisy`/`04_missing`.

### 9.3 Hướng ĐATN — điều kiện cần để H1 kiểm được

Cần *(đề xuất, chưa kiểm)*: (1) hiện thực ít nhất một adapter thật trong mạng — gazetteer adapter (tra cứu thực thể hành chính theo phiên bản trước/sau 01/07/2025, đưa vào tầng ẩn) và type adapter theo loại đơn vị; mỗi adapter bật/tắt độc lập bằng cờ cấu hình cùng một lần huấn luyện cơ sở; (2) ablation ít nhất 4 ô (không adapter / chỉ gazetteer / chỉ type / cả hai) × ≥ 3 seed, cùng split; (3) dữ liệu đủ **support** ở nơi adapter được kỳ vọng giúp: nhãn `Lai` (test hiện chỉ 5 mẫu, train 16, dev 8 — không đủ cho kết luận về T1) và các mẫu có thay đổi hành chính hai phiên bản; cỡ mẫu cần thiết nên tính từ độ rộng CI ghép cặp mục tiêu (báo cáo 11: nửa CI ≈ ±0,011 F1 với 100 mẫu / 446 span), chưa tính trong gói này; (4) một tập đánh giá mới ngoài test Sprint 3 đã bị quan sát; (5) huấn luyện trên GPU (Kaggle) hoặc đủ thời gian CPU — adapter thêm tham số và cần nạp lại PhoBERT, không làm được bằng giải mã lại như gói này.

## 10. Giới hạn

1. **Test 100 mẫu đã bị quan sát** ở Sprint 3; mọi số test/seed là hậu nghiệm, không dùng chọn gì. Test có đúng 25 mẫu gold-new (12 T1-eligible); dư địa 0 trên 25 mẫu chưa chứng minh dư địa 0 trên dữ liệu thực.
2. **Track 5 trường là `DEVELOPMENT_TRACK`**, không phải test độc lập; hàng không độc lập (cùng generator/nguồn OSM; các mẫu `02_noisy` sinh từ `01_new`), nên CI bootstrap theo dòng **quá hẹp** — chỉ nên đọc dấu và độ lớn, không đọc như khoảng tin cậy chặt. Phần lớn dòng giống hệt nhau giữa hai chế độ (≤ 168 dòng đổi trên 4.800).
3. **Checkpoint Kaggle (T4) so với cục bộ (CPU):** hai nhóm không cùng nền tảng; "seed 42" của hai nhóm không cùng lần huấn luyện. Ba seed cục bộ cùng một test nên không độc lập về mẫu.
4. **PCRF và DYN là hai lần huấn luyện khác nhau**; hiệu giữa hai hàng của 2×2 lẫn cả hiệu ứng "có T1" và hiệu ứng "khác lần huấn luyện".
5. Tập stress T1 và PHOBERT-CRF trên track 5 trường chưa chạy (NOT_RUN, mục 1). Dev DYN không có file có ràng buộc trong bằng chứng chọn; nên dev dùng giải mã lại (đã kiểm với file ngoài khóa).
6. ORACLE là cận trên về T1, không phải khả năng của mô hình; dư địa đếm theo gold `QuanHuyen` rỗng ở gold-new, tức không tính trường hợp gold-new có `QuanHuyen` (không có trong dữ liệu này).
7. Gold do một người gán có AI hỗ trợ, IAA chưa đo; CI chỉ phản ánh lấy mẫu.
8. Mean ± std ba seed tính từ giá trị không làm tròn; n = 3 là ước lượng rất thô.

## 11. Điểm suy luận thay vì đo

- Cơ chế "đường giải mã không ràng buộc không sinh `QuanHuyen` là đặc tính của emission, không phải của transitions CRF" suy từ độ lớn tham số CRF (< 0,07) so với khoảng cách top-1/top-2 emission (trung vị 3,29) và từ dư địa 0; không có thí nghiệm cô lập nguyên nhân riêng cho nhãn `QuanHuyen`.
- Cận trên ORACLE (+0,0019) là Δ micro-F1 5 trường trên track development (4.800 dòng), nên không so được với std giữa seed hay hiệu mô hình (T0 span F1 trên test 100 mẫu); báo cáo không đưa phép so đó.
- Điều kiện cho H1 ở mục 9.3 là đề xuất thiết kế, không phải kết quả đo.
- Giải thích mẫu `s3_224ae519b196f730` ("lỗi T1 truyền thành lỗi T0") dựa vào gold hệ "cu" của mẫu và `predicted_system = moi` của DYN; không đọc thêm văn bản địa chỉ.
- Tính quyết định (tất định) của giải mã: đã kiểm bằng chạy lại cho cùng hash (mục 12), không có kiểm riêng về độ nhạy với làm tròn float32 ngoài việc cổng khớp 100% đường.

## 12. Tái lập

```bash
cd /mnt/d/DACN
# 1) tham số CRF (runtime neural; chỉ đọc tensor, không suy luận)
data/interim/modeling/sprint03/runtime_neural_d_v1/bin/python -m scripts.72_run_constraint_ablation extract-crf
# 2) cổng + phân tích (runtime chính; dừng với mã 2 nếu cổng không đạt, trước khi mở gold)
source ~/.venv_dacn/bin/activate
python -m scripts.72_run_constraint_ablation run
python -m unittest tests.test_group1_constraint_ablation -v
```

Cả hai bước từ chối ghi đè thư mục đã có; dùng `--run-name <tên>_v2` để chạy lại. Chạy lại từ đầu (cả `extract-crf` và `run`) vào thư mục mới `constraint_ablation_20261017_repro` cho SHA-256 **giống hệt** ở **35/35** file: 9 file `crf_params/`, 18 file `redecode/` (gồm `gate_report.json`), `metrics.json` và 7 CSV trong `tables/` (thư mục thử đã xóa sau khi so). `run_manifest.json` khác nhau theo thiết kế (tên run, thời điểm). Sau review độc lập, `constraint_ablation.py` được thêm một assert (gold `ChuoiDiaChi` phải bằng `raw_text` dự đoán); chạy lại extract + run vào thư mục tạm cho 35/35 file giống hệt (đã xóa thư mục tạm), nên `code_sha256` của `constraint_ablation.py` trong `run_manifest.json` của run chính là của bản trước assert. Mốc test: **422 test** (OK, 8 skipped) trước khi bắt đầu; sau gói **438** (OK, 8 skipped, 0 FAIL).

SHA-256 (rút gọn) của đầu ra: `metrics.json` `9f7ac5c2…`; `tables/model_comparison_2x2.csv` `c43b5809…`; `tables/headroom.csv` `a68eee96…`; `tables/t1_source_ablation.csv` `0c6b3208…`; `tables/oracle_upper_bound.csv` `1fec7c6d…`; `tables/onoff_dyn_source.csv` `f9c39356…`; `tables/seed_summary.csv` `9a2358b5…`; `tables/gate.csv` `e9860b4b…`.
