# 11. Độ tin cậy T0/T1 trên prediction đã freeze — Phần a (WP3a)

**Ngày chạy:** 13/10/2026. **Phạm vi:** chỉ đọc prediction đã freeze và gold; không chạy mô hình, không huấn luyện. Phần b (đa seed, WP3b) nằm ở cuối tài liệu này.
**Căn cứ:** Amendment A2 điểm 2 (phân tích thống kê hậu nghiệm). Test Sprint 3 là tập **đã bị quan sát**: mọi số dưới đây là báo độ bất định, không dùng để chọn hay chỉnh bất cứ gì.
**Mã:** `src/evaluation/frozen_reliability.py`, `scripts/69_bootstrap_frozen_results.py`, `tests/test_group1_reliability.py`.
**Đầu ra:** `data/processed/evaluation/sprint04/reliability_20261014_v1/` (`metrics.json`, `run_manifest.json`, `tables/*.csv` utf-8-sig).
**Phương pháp:** bootstrap percentile 95%, B = 10.000, seed 20261014, lấy mẫu lại **theo mẫu**; thống kê tính lại từ tổng (tp, fp, fn) của từng resample (micro-F1), không lấy trung bình F1 từng mẫu. So sánh ghép cặp dùng cùng chỉ số mẫu cho hai hệ; p hoán vị xấp xỉ 10.000 hoán vị; McNemar chính xác; Holm trên họ **6 phép so sánh** (5 cặp T0 + 1 cặp T1; hàng "T1 macro-F1" là phụ, không nằm trong họ).

## 1. Bảng tái lập (làm trước khi tính CI)

Hash 5 file prediction khớp `all_test_predictions_frozen.json`; hash gold khớp manifest corpus. Mọi số khớp điểm công bố ở 4 chữ số; tổng (tp, fp, fn) theo mẫu bằng đúng tổng của scorer (tổng và từng nhãn, cả 5 hệ). Mask T1 = 64 eligible / 20 null / 16 excluded.

| Hệ | T0 P | T0 R | T0 F1 | Công bố | T1 acc | T1 macro-F1 | Khớp |
|---|---|---|---|---|---|---|---|
| HEUR-JW | 0,9512 | 0,8744 | 0,9112 | 0,9512/0,8744/0,9112 | 0,9219 | 0,9249 | PASS |
| CRF-INDEP | 0,9234 | 0,8924 | 0,9076 | 0,9234/0,8924/0,9076 | NOT_IMPLEMENTED | NOT_IMPLEMENTED | PASS |
| PHOBERT-CRF | 0,9843 | 0,9843 | 0,9843 | 0,9843 | NOT_IMPLEMENTED | NOT_IMPLEMENTED | PASS |
| PROPOSED-DYN | 0,9821 | 0,9821 | 0,9821 | 0,9821 | 0,7188 | 0,5626 | PASS |
| PROPOSED-NO-CONSTRAINT | 0,9843 | 0,9843 | 0,9843 | 0,9843 | 0,7188 | 0,5626 | PASS |

CRF-INDEP và PHOBERT-CRF không có đầu T1: scorer trả 0,0 vì mọi mẫu là `khong_ro` (đã kiểm: mọi `predicted_system` đều `khong_ro`); đó **không phải kết quả**. T1 của hai hệ này qua T1-PIPE nằm ở `10_t1_h5_results.md`.

Tổng (tp, fp, fn) test: PHOBERT-CRF 439/7/7; PROPOSED-DYN 438/8/8; NO-CONSTRAINT 439/7/7; CRF-INDEP 398/33/48; HEUR-JW 390/20/56 (gold 446 span).

## 2. CI 95% từng hệ — test (100 mẫu / 446 span)

**T0 micro** (CI theo mẫu):

| Hệ | P | R | F1 | Exact-match cả địa chỉ |
|---|---|---|---|---|
| HEUR-JW | 0,9512 [0,9212; 0,9779] | 0,8744 [0,8337; 0,9114] | 0,9112 [0,8773; 0,9415] | 0,63 (63/100) [0,54; 0,72] |
| CRF-INDEP | 0,9234 [0,8886; 0,9539] | 0,8924 [0,8450; 0,9348] | 0,9076 [0,8675; 0,9436] | 0,77 (77/100) [0,68; 0,85] |
| PHOBERT-CRF | 0,9843 [0,9720; 0,9936] | 0,9843 [0,9720; 0,9936] | 0,9843 [0,9720; 0,9936] | 0,93 (93/100) [0,88; 0,97] |
| PROPOSED-DYN | 0,9821 [0,9691; 0,9933] | 0,9821 [0,9691; 0,9933] | 0,9821 [0,9691; 0,9933] | 0,92 (92/100) [0,86; 0,97] |
| PROPOSED-NO-CONSTRAINT | 0,9843 [0,9724; 0,9935] | 0,9843 [0,9724; 0,9935] | 0,9843 [0,9724; 0,9935] | 0,93 (93/100) [0,88; 0,97] |

**T1** (64 eligible; Lai support = 5 → `LOW_SUPPORT`; resample thiếu một lớp gold: 0,53% số lần gọi, macro-F1 khi đó tính trên các lớp có mặt; resample không có Lai gold: 53/10.000, bị loại khỏi CI của Lai-F1):

| Hệ | Accuracy | Macro-F1 (3 lớp) | Lai-F1 | Coverage |
|---|---|---|---|---|
| HEUR-JW | 0,9219 [0,8438; 0,9844] | 0,9249 [0,7981; 0,9937] | 0,9091 [0,6667; 1,0000] | 0,9531 [0,8906; 1,0000] |
| PROPOSED-DYN | 0,7188 [0,6094; 0,8281] | 0,5626 [0,4872; 0,6202] | 0,0000 [0,0000; 0,0000] | 0,8125 [0,7188; 0,9062] |
| PROPOSED-NO-CONSTRAINT | 0,7188 [0,6094; 0,8281] | 0,5626 [0,4872; 0,6202] | 0,0000 [0,0000; 0,0000] | 0,8125 [0,7188; 0,9062] |
| CRF-INDEP, PHOBERT-CRF | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED |

CI `[0; 0]` của Lai-F1 DYN chỉ nói rằng trên mọi resample có Lai, DYN không đúng mẫu Lai nào; với support 5 không nên đọc như một ước lượng chặt.

**F1 theo nhãn:** xem `tables/test_t0_label_ci.csv` (đủ 11 nhãn × 5 hệ). `ToaNha/CanHo`, `MocDinhVi`, `HuongDi`, `GhiChu` = `NOT_EVALUABLE_NO_GOLD_SUPPORT` (support 0). `Khac` support 2 và `Ngo/Hem` support 13: `Khac` gắn `LOW_SUPPORT` và F1 = 0 ở cả 5 hệ. Nhãn có support ≥ 10: CI rộng nhất ở HEUR-JW/CRF-INDEP (ví dụ `Ngo/Hem` CRF-INDEP 0,8182 [0,5882; 0,9630]). **Lưu ý về `Khac`:** nhãn này chỉ nằm ở 2/100 mẫu, nên CI của nó được tính *có điều kiện* trên các resample có chứa `Khac`; 1.323/10.000 resample (13,2%) không có `Khac` và bị loại (cột `n_nonfinite_resamples` của `tables/test_t0_label_ci.csv`). CI `[0; 0]` của `Khac` vì vậy nghĩa là "với điều kiện resample có `Khac`", không phải CI trên toàn bộ resample.

## 3. So sánh ghép cặp — test (cùng 100 mẫu; T1 cùng 64 mẫu)

Δ = hệ A − hệ B. `P(Δ≤0)` = tỷ lệ resample có Δ ≤ 0. `b/c`: McNemar trên exact-match (T0) hoặc đúng/sai (T1; abstain tính sai); b = A đúng B sai, c = A sai B đúng. Holm: 6 phép.

| Cặp (A − B) | Δ | CI ghép cặp | Rộng CI | P(Δ≤0) | p hoán vị (Holm) | b/c | p McNemar (Holm) |
|---|---|---|---|---|---|---|---|
| T0 F1: PHOBERT-CRF − DYN | +0,0022 | [−0,0091; +0,0137] | 0,0228 | 0,431 | 1,000 (1,000) | 4/3 | 1,000 (1,000) |
| T0 F1: DYN − NO-CONSTRAINT | −0,0022 | [−0,0068; 0,0000] | 0,0068 | 1,000 | 1,000 (1,000) | 0/1 | 1,000 (1,000) |
| T0 F1: PHOBERT-CRF − CRF-INDEP | +0,0767 | [+0,0425; +0,1154] | 0,0729 | 0,000 | 0,0001 (0,0006) | 17/1 | 0,0001 (0,0007) |
| T0 F1: PHOBERT-CRF − HEUR-JW | +0,0731 | [+0,0429; +0,1066] | 0,0637 | 0,000 | 0,0001 (0,0006) | 31/1 | <0,0001 (<0,0001) |
| T0 F1: CRF-INDEP − HEUR-JW | −0,0036 | [−0,0294; +0,0206] | 0,0500 | 0,609 | 0,7724 (1,000) | 19/5 | 0,0066 (0,0198) |
| T1 acc: HEUR-JW − DYN (64 mẫu) | +0,2031 | [+0,0781; +0,3281] | 0,2500 | 0,001 | 0,0047 (0,0188) | 16/3 | 0,0044 (0,0177) |
| T1 macro-F1 (phụ): HEUR-JW − DYN | +0,3623 | [+0,2159; +0,4594] | 0,2435 | 0,000 | 0,0184 (không thuộc họ) | 16/3 | 0,0044 |

Không cặp nào ở trạng thái DEGENERATE trên test. Số mẫu có tổng (tp,fp,fn) khác nhau: PCRF–DYN 7 mẫu (chênh ròng chỉ 1 TP và 1 FP/FN, nhưng nằm ở 7 mẫu khác nhau; exact-match bất đồng ở 7 mẫu); DYN–NO-CONSTRAINT 1 mẫu.

### Kết luận theo CI

- **PHOBERT-CRF vs PROPOSED-DYN (chênh 1 span):** *không phân biệt được với dữ liệu này.* CI ghép cặp của Δ F1 là [−0,0091; +0,0137], chứa 0; hoán vị p = 1,0; McNemar 4/3. Độ rộng CI 0,023 cho thấy với 100 mẫu / 446 span, chênh nhỏ hơn khoảng ±0,011 F1 không phân biệt được. Không được viết "PHOBERT-CRF tốt hơn" hay "tương đương".
- **DYN bật vs tắt ràng buộc (đổi 1 mẫu, 2 span):** *không phân biệt được.* Δ = −0,0022 (tắt ràng buộc cao hơn), McNemar 0/1, p = 1,0. CI [−0,0068; 0,0000] chạm 0 ở biên và `P(Δ≤0) = 1,0` chỉ phản ánh việc chỉ có **một** mẫu bất đồng (mọi resample có mẫu đó đều Δ ≤ 0, resample không bốc mẫu đó cho Δ = 0); không phải bằng chứng ràng buộc làm hại. Kết luận hợp lệ: ràng buộc không cho lợi ích đo được trên test này.
- **PHOBERT-CRF hơn CRF-INDEP và hơn HEUR-JW (T0):** CI ghép cặp không chứa 0 (+0,043…+0,115 và +0,043…+0,107), p Holm ≤ 0,0007. Được ủng hộ trên tập này, với giới hạn ở mục 6.
- **CRF-INDEP vs HEUR-JW:** *không phân biệt được trên micro-F1* (Δ −0,0036, CI [−0,029; +0,021]), nhưng trên exact-match cả địa chỉ CRF-INDEP đúng nhiều hơn (19 so với 5 mẫu bất đồng, p Holm 0,0198). Hai thước đo trả lời hai câu hỏi khác nhau; không gộp.
- **T1 HEUR-JW vs DYN:** HEUR-JW cao hơn trên 64 mẫu (Δ accuracy +0,20, CI [+0,08; +0,33]; p Holm 0,019). Đây là kết quả hậu nghiệm trên test đã quan sát.

## 4. Độ nhạy: hiệu nhỏ nhất phân biệt được

Độ rộng CI ghép cặp ở mục 3 là ước lượng hiệu nhỏ nhất có thể phân biệt với 100 mẫu / 446 span: nửa độ rộng ≈ ±0,011 (PCRF–DYN), ±0,036 (PCRF–CRF), ±0,032 (PCRF–HEUR), ±0,025 (CRF–HEUR), ±0,125 accuracy T1 (HEUR–DYN, 64 mẫu). Đây là suy luận từ độ rộng CI quan sát (không phải tính công suất kiểm định). Cặp DYN on/off có độ rộng 0,0068 nhưng chỉ vì có đúng 1 mẫu bất đồng; không diễn giải như độ chính xác cao.

## 5. Theo source_dataset và độ nhạy theo cụm

**Mỗi mẫu test là một `source_group` riêng (100 nhóm khác nhau, đã kiểm)**, nên bootstrap theo `source_group` trùng với bootstrap theo mẫu (bảng `test_cluster_sensitivity.csv`: CI F1 của hai cách gần như bằng nhau, ví dụ HEUR-JW [0,8757; 0,9418] so với [0,8773; 0,9415]; chênh lệch nhỏ do khác chuỗi số ngẫu nhiên). Không coi là hai phân tích độc lập; bảng chính ở mục 2 dùng bootstrap theo mẫu.

Bảng độ nhạy theo cụm `source_dataset` (**5 cụm × 20 mẫu: quá ít để CI đáng tin**, CI percentile của 5 cụm thường quá hẹp ở đuôi và không ổn định):

| Hệ | F1 | CI theo mẫu | CI theo 5 cụm source_dataset |
|---|---|---|---|
| HEUR-JW | 0,9112 | [0,8773; 0,9415] | [0,8147; 0,9756] |
| CRF-INDEP | 0,9076 | [0,8675; 0,9436] | [0,7842; 0,9848] |
| PHOBERT-CRF | 0,9843 | [0,9720; 0,9936] | [0,9680; 0,9979] |
| PROPOSED-DYN | 0,9821 | [0,9691; 0,9933] | [0,9592; 0,9979] |
| NO-CONSTRAINT | 0,9843 | [0,9724; 0,9935] | [0,9664; 0,9979] |

**T0 micro-F1 theo lát source_dataset** (mỗi lát chỉ 20 mẫu; CI theo mẫu trong lát; đủ trong `tables/test_by_source_dataset.csv`):

| Lát (gold span) | HEUR-JW | CRF-INDEP | PHOBERT-CRF | DYN | NO-CONSTRAINT |
|---|---|---|---|---|---|
| 01_new (82) | 0,982 | 0,982 | 1,000 | 1,000 | 1,000 |
| 02_noisy (89) | 0,717 [0,59; 0,83] | 0,655 [0,51; 0,79] | 0,966 [0,93; 1,00] | 0,944 [0,90; 0,98] | 0,955 [0,91; 0,99] |
| 03_old (105) | 0,910 | 0,943 | 0,990 | 0,990 | 0,990 |
| 04_missing (68) | 0,962 | 0,933 | 0,956 | 0,971 | 0,971 |
| 06_hybrid (102) | 0,975 | 1,000 | 1,000 | 1,000 | 1,000 |

Chênh giữa các hệ tập trung ở lát `02_noisy` (nhiễu OCR/tổng hợp); trên các lát còn lại khoảng cách nhỏ và CI chồng nhau. CI `[1,0; 1,0]` ở nhiều ô là hệ quả của F1 = 1 trên cả 20 mẫu, không phải độ chính xác tuyệt đối.

## 6. Dev (Tầng 2) — nhãn `SELECTION_SET`

Dev (60 mẫu; T1 eligible 53) đã được dùng để chọn mô hình/ngưỡng, **không phải ước lượng không chệch**. Mask T1 của dev: manifest ghi 17 ID ở `evaluation_exclusions`, nhưng 16 ID trong đó là ID của test; chỉ **1 ID** thuộc dev (60 − 6 null − 1 = 53), nên chỉ ID đó được truyền cho scorer (scorer từ chối ID ngoài split).

**Ghi chú về nhãn:** các file `tables/dev_*.csv` **không có cột nhãn**; nhãn `SELECTION_SET` chỉ nằm trong `metrics.json` (`dev.label`) và trong báo cáo này. Không đọc riêng các CSV dev như ước lượng không chệch. (Không thêm cột vào CSV để tránh phải chạy lại sang thư mục `_v2`.)

Tìm prediction dev theo hash (không thay bằng file khác):

| Hệ | Trạng thái |
|---|---|
| HEUR-JW, CRF-INDEP | FOUND (đường dẫn trong lock còn tồn tại, hash khớp) |
| PHOBERT-CRF | FOUND (bản sao khớp hash dưới `release_and_kaggle_20261005_v1/pcrf_c02_selection_artifacts_v2/`) |
| PROPOSED-NO-CONSTRAINT | FOUND (bản sao khớp hash dưới `dyn_c02_selection_artifacts_v1/`) |
| PROPOSED-DYN | **NOT_FOUND** — bằng chứng chọn dev của DYN chỉ chứa run `…dev_proposed_no_constraint_v1`; không tồn tại dev prediction của bộ giải mã có ràng buộc. Không thay bằng run không ràng buộc dưới tên DYN. |

Do đó trên dev cặp DYN bật–tắt là `NOT_EVALUABLE_NO_CONSTRAINED_DEV_RUN`; PHOBERT-CRF được so với NO-CONSTRAINT, và T1 HEUR-JW so với NO-CONSTRAINT (giả định, ghi rõ: đầu T1 của hai biến thể dùng chung trọng số trên test cho kết quả T1 giống hệt, chưa kiểm trên dev).

| Hệ (dev) | T0 F1 [CI] | T1 acc [CI] | Lai-F1 [CI] (support 8) |
|---|---|---|---|
| HEUR-JW | 0,8801 [0,8352; 0,9200] | 0,7547 [0,6415; 0,8679] | 0,6667 [0,2857; 0,9091] |
| CRF-INDEP | 0,9056 [0,8542; 0,9519] | NOT_IMPLEMENTED | NOT_IMPLEMENTED |
| PHOBERT-CRF | 0,9389 [0,9024; 0,9725] | NOT_IMPLEMENTED | NOT_IMPLEMENTED |
| NO-CONSTRAINT | 0,9474 [0,9127; 0,9784] | 0,7736 [0,6604; 0,8868] | 0,0000 [0,0; 0,0] |

Ghép cặp dev (Δ = A − B; họ Holm 5 phép): PHOBERT-CRF − NO-CONSTRAINT −0,0085 [−0,029; +0,011], p = 0,53 → không phân biệt được; PHOBERT-CRF − CRF-INDEP +0,0333 [+0,004; +0,065], p hoán vị 0,040 (Holm 0,159), McNemar p = 0,29 → không vượt Holm; PHOBERT-CRF − HEUR-JW +0,0588 [+0,030; +0,090], Holm p < 0,001; CRF-INDEP − HEUR-JW +0,0254 [−0,013; +0,065] (p hoán vị 0,21; McNemar b/c = 17/2, p Holm 0,0029); T1 HEUR-JW − NO-CONSTRAINT −0,0189 [−0,170; +0,132] → không phân biệt được. Chi tiết: `tables/dev_*.csv`.

Quan sát đáng ghi: trên dev, HEUR-JW T1 accuracy 0,7547 thấp hơn nhiều so với test (0,9219) và Lai-F1 DYN vẫn bằng 0 — khoảng chênh dev/test của HEUR-JW (CI dev [0,64; 0,87] không chứa 0,92) cho thấy 64 mẫu test T1 là ước lượng lạc quan hoặc phân phối test dễ hơn; không thể tách hai khả năng từ dữ liệu này.

## 7. Track 5 trường (4.800 hàng)

`NOT_RUN` (nhãn `DEVELOPMENT_TRACK`). Tầng 1 và dev đã xong; track này không làm trong phiên này.

## 8. Giới hạn

1. Một bộ test 100 mẫu / 446 span **đã bị quan sát** ở Sprint 3; mọi CI ở đây là hậu nghiệm.
2. Gold do một người gán có AI hỗ trợ, IAA chưa đo: CI chỉ phản ánh lấy mẫu, không phản ánh nhiễu nhãn.
3. Một seed (đa seed là WP3b): CI chỉ gồm biến thiên lấy mẫu mẫu test, không gồm biến thiên huấn luyện.
4. 4 nhãn không có support (`ToaNha/CanHo`, `MocDinhVi`, `HuongDi`, `GhiChu`): không có F1 cho chúng, và nhãn `Khac` support 2.
5. Test lấy đều 20 mẫu từ mỗi nguồn (5 nguồn), không phải mẫu ngẫu nhiên của phân phối thật; các nguồn lại sinh từ cùng generator/nguồn OSM. CI không ngoại suy được sang địa chỉ do người thật viết.
6. Bootstrap percentile với F1 gần 1 và ít lỗi (7–8 FP/FN) cho CI không đối xứng và có thể hẹp đuôi dưới; mẫu bất đồng nhỏ (1–7 mẫu) làm các p hoán vị/McNemar bằng 1,0 không mang thông tin về "tương đương".
7. T1: Lai support 5 (test) và 8 (dev); mọi số Lai là `LOW_SUPPORT`.
8. Mask T1 test dùng 16 ID loại trừ đã khai báo; accuracy T1 chỉ trên 64 mẫu eligible, 20 mẫu null và 16 mẫu loại không tham gia.

## 9. Những điểm suy luận thay vì đo

- Việc ngưỡng "hiệu nhỏ nhất phân biệt được" lấy từ nửa độ rộng CI ghép cặp, không phải phép tính công suất.
- Giải thích CI `[−0,0068; 0,0000]` của DYN on/off là hệ quả của đúng một mẫu bất đồng (đã kiểm tổng (tp,fp,fn): 1 mẫu khác nhau), không có thêm phép thử nào.
- Nhận định dev HEUR-JW T1 thấp hơn test do "ước lượng lạc quan hoặc phân phối dễ hơn" là suy đoán; chưa kiểm.
- Giả định T1 của DYN bật = NO-CONSTRAINT trên dev (mục 6) chỉ dựa trên kết quả test giống hệt, chưa kiểm trên dev.
- Chọn họ Holm = 6 phép (5 cặp T0 + 1 cặp T1) và coi p thiếu (DEGENERATE) như 1 khi xếp hạng: quyết định hiện thực, ghi trong `run_manifest.json`.

## 10. Lệnh tái lập

```bash
cd /mnt/d/DACN && source ~/.venv_dacn/bin/activate
python -m scripts.69_bootstrap_frozen_results --repro-only   # chỉ bảng tái lập
python -m scripts.69_bootstrap_frozen_results                # ghi reliability_20261014_v1 (từ chối ghi đè)
python -m unittest tests.test_group1_reliability -v
```

Chạy lại từ đầu trên thư mục mới cho SHA-256 giống hệt của **13 file đầu ra** ngoài `run_manifest.json` (bản review độc lập đã kiểm lại 13/13; `run_manifest.json` có hash đầu ra và hash mã trùng khi chạy lại). `run_manifest.json` không ghi hash đầu vào của dev; các hash đó nằm ở `metrics.json`, `dev.locations[].expected_sha256`.

---

# Phần b — Đa seed trên CPU cục bộ (WP3b)

**Ngày chạy:** 13–14/10/2026. **Mã:** `scripts/70_run_multiseed_local.py`, `tests/test_group1_multiseed.py`. **Đầu ra:** `data/processed/evaluation/sprint04/multiseed_20261015_v1/` (`metrics.json`, `run_manifest.json`, `frozen_hashes.json`, `determinism_check.json`, `runs/`, `tables/per_seed.csv`); checkpoint/log/prediction ở `data/interim/modeling/sprint04/multiseed_20261015_v1/`.
**Trạng thái:** PASS — đủ 6 lượt (PHOBERT-CRF và PROPOSED-DYN × seed 42 / 1337 / 2025), không `PARTIAL_SEEDS`.

## b1. Cách chạy

- Cấu hình c02 đã khóa, seed gán trên bản sao trong bộ nhớ; không sửa `src/modeling/`, `configs/` hay adapter (hash 2 file config và `protocol_lock_v1.json` khớp manifest sau khi chạy). Gọi thẳng `train_model`; corpus `corpus_train_dev_v2` (train.jsonl và dev.jsonl giống hệt `corpus_v1_release2`, đã so SHA-256). CPU, 6 luồng (`OMP/MKL_NUM_THREADS=6`, `torch.set_num_threads(6)`), Java qua PATH/JAVA_HOME của tiến trình con. Chọn epoch theo quy tắc dev có sẵn trong `train_model`.
- Suy luận test chỉ nhận văn bản (`test_input.jsonl`, hash khớp manifest). **SHA-256 prediction được ghi vào `frozen_hashes.json` trước khi đọc gold**; bước chấm kiểm lại hash rồi mới mở gold, mask T1 64/20/16, mỗi seed chấm một lần.
- DYN dùng đúng policy đã khóa: ngưỡng 0,7 / margin 0,2 cho mọi seed, không hiệu chỉnh lại (dev chỉ có 8 Lai). PROPOSED-NO-CONSTRAINT dùng lại `best.pt` của DYN cùng seed với ràng buộc tắt.
- Thời gian: 20–29 phút huấn luyện mỗi lượt (đo từ lượt đầu; tổng ước tính dưới 6 giờ nên không phải dừng).
- **Sự cố môi trường đã xử lý (không phải lỗi mã khóa):** adapter khóa đòi ≥ 20 GiB đĩa trống trước khi suy luận; lượt DYN-1337 (16 epoch) làm đĩa xuống dưới ngưỡng và suy luận dừng với `DISK_BELOW_TRAINING_ARTIFACT_BUDGET`. Tôi dọn `epoch_*.pt`, `resume_*.pt`, `last.pt` của chính lượt đó (giữ `best.pt`, mọi file `.json`, `training_log.jsonl`; hash và kích thước từng file đã xóa nằm trong `multiseed_run_done.json` / `cleanup_after_training.json` / `early_cleanup_before_inference.json`) rồi chạy tiếp. Từ đó script dọn ngay sau huấn luyện. Hai file `BLOCKED_LOCAL_TRAINING.json` do hai lần dừng này sinh ra (22:36 và 23:58) đã bị **xóa sau khi xử lý**, và log suy luận được mở ở chế độ ghi đè, nên nguyên văn lỗi đĩa của DYN-1337 và của lượt rerun không còn; chỉ còn `run_all.log` và `determinism.log` trỏ tới các log đó.
- **Bốn phiên bản của `scripts/70_run_multiseed_local.py` đã được dùng** (SHA-256 theo `code_sha256` trong `training_manifest.json`, metadata checkpoint và `model_config.json` từng lượt; số liệu từ bản review độc lập, tôi không tự đo lại):

| Phiên bản | SHA-256 (rút gọn) | Dùng cho |
|---|---|---|
| A | `78d16d39…` | Huấn luyện PCRF-42, DYN-42, PCRF-1337, DYN-1337; suy luận và chấm ba lượt đầu |
| B | `87fd49e4…` (= `run_manifest.json`) | Suy luận và chấm DYN-1337; toàn bộ PCRF-2025 và DYN-2025 |
| C | `84c7e912…` | Huấn luyện `pcrf_seed42_rerun`; lần `determinism` đầu bị chặn ở suy luận (23:58) |
| D | `c09960f7…` (bản đã commit) | Suy luận rerun và phép so tất định (00:01) |

  Bản A, B, C **không còn trong git**, nên nội dung thay đổi chỉ suy được từ hệ quả (vị trí dọn dẹp checkpoint, thêm lệnh `determinism`); logic huấn luyện/suy luận/chấm không đổi. 155 file mã còn lại (gồm toàn bộ `src/modeling/` và `src/evaluation/`) có cùng hash ở cả bảy lượt. Hash mã trong `run_manifest.json` (bản B) vì vậy **không khớp** bản đã commit (bản D).

## b2. Bảng từng seed (test Sprint 3, 100 mẫu; T1 trên 64 eligible)

| Seed | Mô hình | Dev T0 F1 (epoch tốt nhất) | Test T0 P / R / F1 | Exact-match | T1 acc | T1 macro-F1 | Lai-F1 (support 5) | Coverage | Epoch tốt nhất / đã chạy | Thời gian |
|---|---|---|---|---|---|---|---|---|---|---|
| 42 | PHOBERT-CRF | 0,9439 | 0,9775 / 0,9753 / 0,9764 | 90 | NOT_IMPLEMENTED | — | — | — | 6 / 11 | 1.416 s |
| 42 | PROPOSED-DYN | 0,9404 | 0,9730 / 0,9686 / 0,9708 | 88 | 0,7031 | 0,5754 | 0,0000 | 0,7656 | 6 / 11 | 1.263 s |
| 42 | DYN tắt ràng buộc | (cùng checkpoint) | 0,9730 / 0,9686 / 0,9708 | 88 | 0,7031 | 0,5754 | 0,0000 | 0,7656 | — | — |
| 1337 | PHOBERT-CRF | 0,9455 | 0,9797 / 0,9753 / 0,9775 | 92 | NOT_IMPLEMENTED | — | — | — | 6 / 11 | 1.261 s |
| 1337 | PROPOSED-DYN | 0,9422 | 0,9910 / 0,9910 / 0,9910 | 96 | 0,8438 | 0,7204 | 0,3333 | 0,9688 | 11 / 16 | 1.753 s |
| 1337 | DYN tắt ràng buộc | (cùng checkpoint) | 0,9910 / 0,9910 / 0,9910 | 96 | 0,8438 | 0,7204 | 0,3333 | 0,9688 | — | — |
| 2025 | PHOBERT-CRF | 0,9350 | 0,9821 / 0,9821 / 0,9821 | 92 | NOT_IMPLEMENTED | — | — | — | 7 / 12 | 1.411 s |
| 2025 | PROPOSED-DYN | 0,9420 | 0,9752 / 0,9709 / 0,9730 | 89 | 0,6719 | 0,3891 | 0,0000 | 0,7500 | 6 / 11 | 1.213 s |
| 2025 | DYN tắt ràng buộc | (cùng checkpoint) | 0,9752 / 0,9709 / 0,9730 | 89 | 0,6719 | 0,3891 | 0,0000 | 0,7500 | — | — |

**Trung bình ± độ lệch chuẩn mẫu (ddof=1, n = 3 seed cục bộ):**

| Hệ | Test T0 F1 | Exact-match (/100) | T1 acc | T1 macro-F1 | Lai-F1 | Coverage |
|---|---|---|---|---|---|---|
| PHOBERT-CRF | 0,9787 ± 0,0030 | 91,3 ± 1,2 | NOT_IMPLEMENTED | — | — | — |
| PROPOSED-DYN | 0,9783 ± 0,0111 | 91,0 ± 4,4 | 0,7396 ± 0,0916 | 0,5616 ± 0,1661 | 0,1111 ± 0,1924 | 0,8281 ± 0,1221 |
| DYN tắt ràng buộc | 0,9783 ± 0,0111 | 91,0 ± 4,4 | giống DYN | giống DYN | giống DYN | giống DYN |

**Hàng riêng, không vào trung bình** — Sprint 3, GPU T4, seed 42 (Kaggle): PHOBERT-CRF test F1 0,9843; PROPOSED-DYN 0,9821, T1 0,7188 / 0,5626; NO-CONSTRAINT 0,9843. Hai lượt cùng seed danh nghĩa 42 nhưng khác nền tảng (CPU cục bộ so với GPU T4), nên "seed" không phải nguyên nhân của chênh lệch; chênh −0,0079 (PCRF: 439 → 435 TP, 4 TP) và −0,0113 (DYN: 438 → 432 TP, 6 TP) trên 446 span. Xem diễn giải ở b4 và b5.5.
**CRF-INDEP:** `DETERMINISTIC_SEED_INVARIANT` (L-BFGS), một dòng cố định: test F1 0,9076. **HEUR-JW:** một cấu hình cố định: test F1 0,9112, T1 acc 0,9219.

**Chẩn đoán T1 argmax thuần** (không ngưỡng/margin; chẩn đoán trên test đã quan sát, không phải cấu hình đề xuất): acc 0,8906 / 0,8594 / 0,8906 và Lai-F1 0,0 / 0,4615 / 0,0 cho seed 42 / 1337 / 2025.

## b3. Delta theo seed

| Seed | PCRF − DYN (T0 F1) | CI ghép cặp | p hoán vị | McNemar b/c | DYN bật − tắt |
|---|---|---|---|---|---|
| 42 | +0,0056 | [−0,0034; +0,0167] | 0,50 | 3/1 | 0,0000 |
| 1337 | −0,0135 | [−0,0276; −0,0011] | 0,09 | 1/5 | 0,0000 |
| 2025 | +0,0090 | [−0,0044; +0,0231] | 0,28 | 5/2 | 0,0000 |
| **Trung bình ± std** | **+0,0004 ± 0,0122** | | | | **0,0000 ± 0,0000** |

(CI ghép cặp theo mẫu, B = 10.000, seed 20261014; không hiệu chỉnh đa so sánh ở bảng này; p hoán vị trên micro-F1.)

## b4. Kiểm tất định (bước 5)

Huấn luyện lại PHOBERT-CRF seed 42 lần hai trong thư mục riêng: **0/100 mẫu khác span, chênh emissions tối đa = 0,0, cùng epoch tốt nhất (6)** → `DETERMINISTIC_ON_CPU` ở mức prediction. SHA-256 file `best.pt` khác nhau giữa hai lần (`best_checkpoint_sha256_equal = false`) dù emissions giống hệt. Nguyên nhân đã được bản review độc lập xác định (tôi không tự đo; nguồn: `reviews/review_wp3b_20261014.md`): so bằng `torch.load`, 206/206 tensor bằng nhau từng phần tử và 212 thành phần của file nén cùng CRC; hai file chỉ khác tên thư mục gốc trong file nén (lấy từ tên file tạm lúc lưu). Nghĩa là PCRF seed 42 tất định ở mức trọng số trên CPU; tính tất định này mới kiểm trên PHOBERT-CRF seed 42, áp dụng cho DYN là suy luận. Về chênh lệch với Kaggle: hai lượt cùng seed danh nghĩa 42 nhưng khác nền tảng (CPU cục bộ so với GPU T4), nên seed không phải nguyên nhân. Chênh của DYN (−0,0113) cùng cỡ std giữa seed (0,0111) và 0,9821 nằm trong khoảng cục bộ (0,9708–0,9910); chênh của PHOBERT-CRF (−0,0079) gấp khoảng 2,6 lần std của nó (0,0030) và 0,9843 cao hơn cả ba seed cục bộ, nhưng n = 3 không đủ để kết luận. Chưa tách được thành phần nào của nền tảng (chuỗi số ngẫu nhiên CPU so với CUDA, thứ tự phép toán, phiên bản thư viện).

## b5. Diễn giải (theo số, không vượt dữ liệu)

1. **PHOBERT-CRF vs PROPOSED-DYN (T0): không phân biệt được.** Δ trung bình +0,0004 với std giữa seed 0,0122; dấu đổi theo seed (+, −, +); CI ghép cặp của seed 1337 loại 0 nhưng p hoán vị = 0,09 và hai seed kia ngược chiều. Std giữa các seed của DYN (0,0111) **cùng cỡ** nửa-CI ghép cặp ở WP3a (0,0114); std của Δ (0,0122) lớn hơn nó một chút, và cả hai **lớn hơn nhiều** chênh lệch Kaggle seed 42 (0,0022). Chênh lệch 0,0022 của Sprint 3 nằm trong biến thiên seed; không dùng làm bằng chứng PCRF tốt hơn hay kém hơn.
2. **PCRF ổn định hơn DYN giữa các seed** (std 0,0030 so với 0,0111; exact-match std 1,2 so với 4,4), nhưng với n = 3 độ lệch chuẩn là ước lượng rất thô; không kiểm định được.
3. **Ràng buộc BIO không có tác dụng đo được ở cả ba seed:** DYN bật và tắt cho cùng điểm trên 100 mẫu ở mọi seed (Δ = 0; Kaggle seed 42 chênh 1 mẫu). Đếm từ `test_dyn` và `test_dyn_off` (khớp bản review độc lập): ràng buộc kích hoạt (`ban_district`) ở 28 / 31 / 3 mẫu (seed 42 / 1337 / 2025) nhưng không đổi đường giải mã nào: 0 mẫu khác span và 0 mẫu khác `predicted_system` ở cả ba seed. Xem WP5 về "dư địa".
4. **T1 của DYN — biến thiên nằm ở ngưỡng, không ở khả năng phân lớp; riêng lớp Lai tách được một phần ở 1/3 seed.** Số đếm từ `test_dyn/predictions.jsonl` (64 mẫu eligible: cu 47, moi 12, Lai 5; tôi tự đếm lại và khớp bản review):

   | Seed | Từ chối dưới ngưỡng (cu / moi / Lai) | Đúng có ngưỡng 0,7/0,2 | Đúng theo argmax | Lai đúng có ngưỡng / argmax | cu bị argmax thành Lai |
   |---|---|---|---|---|---|
   | 42 | 15 (12 / 0 / 3) | 45/64 | 57/64 | 0 / 0 | 0 |
   | 1337 | 2 (0 / 1 / 1) | 54/64 | 55/64 | 2 / 3 | 5 |
   | 2025 | 16 (6 / 9 / 1) | 43/64 | 57/64 | 0 / 0 | 0 |

   (a) Accuracy T1 theo argmax thuần ổn định giữa các seed, 55–57/64 (0,86–0,89). (b) Biến thiên 0,67–0,84 của accuracy có ngưỡng đến từ số mẫu bị từ chối dưới ngưỡng cố định 0,7/0,2 (15 / 2 / 16 mẫu): seed 42 từ chối 12 mẫu cu, seed 2025 từ chối 9/12 mẫu moi, tức độ tự tin của posterior thay đổi theo seed, không phải khả năng phân lớp. (c) Lớp Lai: 1/3 seed cục bộ (1337) tách được một phần (2/5 đúng khi có ngưỡng, 3/5 theo argmax) và phải trả bằng 5 mẫu cu bị gán Lai; seed 42 và 2025 cục bộ, cùng checkpoint Kaggle, không bao giờ xếp Lai lên đầu — tức 3 trên 4 lần huấn luyện cho Lai-F1 = 0. Lai chỉ có support 5 ở test (train 16, dev 8), nên mọi số Lai là `LOW_SUPPORT` và không đủ để kết luận về kiến trúc. Ở cả 3 seed accuracy T1 có ngưỡng của DYN thấp hơn HEUR-JW (0,9219) trên cùng 64 mẫu.
5. **Chênh với Kaggle seed 42 (−0,0079 PCRF, −0,0113 DYN):** hai lượt cùng seed danh nghĩa 42 nhưng khác nền tảng (CPU cục bộ so với GPU T4), nên "seed" không phải nguyên nhân. Chênh của DYN cùng cỡ std giữa seed (0,0111); chênh của PCRF gấp khoảng 2,6 lần std của nó (0,0030), nhưng n = 3 không đủ để kết luận. Chưa tách được thành phần nào của nền tảng; tính tất định mới kiểm trên PCRF seed 42, áp dụng cho DYN là suy luận (xem b4).

## b6. Giới hạn (bổ sung cho mục 8 của phần a)

- n = 3 seed; std ddof = 1 là ước lượng thô; không có kiểm định giữa các seed.
- Test Sprint 3 đã bị quan sát: mọi số ở đây là độ bền hậu nghiệm, không dùng chọn cấu hình, seed hay checkpoint. Không báo riêng seed tốt nhất.
- Cùng một bộ test 100 mẫu cho cả ba seed, nên ba seed không độc lập về mặt mẫu.
- Huấn luyện CPU cục bộ khác Kaggle T4 (phần cứng, thư viện, thứ tự phép toán); seed 42 Kaggle chỉ để so, không vào trung bình.
- Hash mã trong `run_manifest.json` (bản B) không khớp script đã commit (bản D); xem bảng bốn phiên bản ở b1.
- Mean ± std được tính từ điểm đã làm tròn 4 chữ số của scorer (từ giá trị không làm tròn, chữ số cuối của vài std khác 0,0001, ví dụ std macro-F1 0,1660 so với 0,1661). `run_manifest.json` của WP3b không ghi số dòng vào/ra; guard "hash trước gold" trong `_score_variant` chưa có unit test riêng (bản review đã thử tay: hoạt động).
- Policy T1 khóa 0,7/0,2 cho mọi seed, không hiệu chỉnh lại.

## b7. Lệnh tái lập

```bash
cd /mnt/d/DACN
PY=data/interim/modeling/sprint03/runtime_neural_d_v1/bin/python
$PY -m scripts.70_run_multiseed_local preflight
$PY -m scripts.70_run_multiseed_local run-all        # tuần tự, resume được, dừng khi đĩa < 15 GB
$PY -m scripts.70_run_multiseed_local aggregate
$PY -m scripts.70_run_multiseed_local determinism    # huấn luyện lại PCRF-42 và so prediction
```
