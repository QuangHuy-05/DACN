# 12. Thí nghiệm CPU H3, E1, H2, H4 (WP4)

**Ngày chạy:** 14/10/2026. **Mô hình:** CRF-INDEP huấn luyện lại ở cấu hình đã khóa (context 1, c1 0,1, c2 1,0, 100 vòng, `surface_admin_segment_cue_v2`), và HEUR-JW cấu hình đã khóa ở các phép nhiễu lúc test. Siêu tham số giữ nguyên ở mọi điều kiện, không dò lưới.
**Căn cứ:** Amendment A2. Test Sprint 3 là tập **đã bị quan sát**: mọi số trên test là phân tích độ bền hậu nghiệm, không dùng để chọn gì; các số trên test của H2 mang nhãn `POST_HOC_SECONDARY`.
**Mã:** `src/evaluation/perturbations.py`, `scripts/71_run_cpu_hypothesis_experiments.py`, `tests/test_group1_cpu_experiments.py` (16 test).
**Đầu ra:** `data/processed/evaluation/sprint04/cpu_hypotheses_20261016_v1/` (10 CSV utf-8-sig và 1 JSONL (`h2_training_data_ids.jsonl`), `metrics.json`, `run_manifest.json`; thư mục con `tier2_local_neural/`), checkpoint và prediction trong `data/interim/modeling/sprint04/cpu_hypotheses_20261016_v1/` (Git bỏ qua).
**Phương pháp thống kê:** bootstrap percentile 95%, B = 10.000, seed 20261016, thống kê tính lại từ tổng (tp, fp, fn) của mỗi resample. So sánh ghép cặp dùng cùng chỉ số mẫu. H2 resample theo **nhóm lãnh thổ** (cluster bootstrap). Cột "đọc" chỉ xét khoảng tin cậy của delta có loại 0 hay không.

## 0. Bước 0 — tái lập (làm trước mọi thí nghiệm)

| Mục | Kết quả | Trạng thái |
|---|---|---|
| Hash CRF huấn luyện lại (1,9 s) | `b4ff0d23…2004f8` = checkpoint đã khóa | PASS |
| CRF test P/R/F1 | 0,9234 / 0,8924 / 0,9076; span trùng từng mẫu với prediction đã freeze | PASS |
| HEUR-JW test P/R/F1 | 0,9512 / 0,8744 / 0,9112; span trùng prediction đã freeze (hash tài nguyên khóa đã kiểm) | PASS |
| 400 mẫu train+dev+test | 0 span chồng; `str.lower()` không đổi độ dài; 28 mẫu không dấu phẩy (test: 14); bỏ phẩy và hạ chữ khả nghịch, bề mặt span đúng 400/400 cho cả ba phép | PASS |
| Data 04: 800 → 779 → 664 → 653 | khớp từng bước (leak_guard, bỏ ngõ/hẻm/ngách/kiệt, bỏ trùng (số nhà, tên đường) GT với dev/test); 142 nhóm, 463 ADM / 190 UNRESOLVED, nhóm lớn nhất 16,7%, KieuThieu 293/198/91/71, cu 302 / mới 351 | PASS |
| Pool đầy đủ | Data 01: 880, Data 03: 1.199 (khớp) | PASS |
| Căn span 653 dòng Data 04 và 2.079 dòng pool | 100% căn được duy nhất và vòng BIO đúng (0 dòng bị bỏ) | PASS |

**Một số lệch, đã làm rõ với phiên điều phối:** số mẫu có văn bản ngoài span. Prompt ghi 58; với định nghĩa chính xác `text != ", ".join(văn bản span theo thứ tự start)` tôi đo **66/400** (train 25, dev 11, **test 30**). 43 mẫu chỉ khác ở dấu cách giữa `Ngo/Hem` và `TenDuong` (không có dấu phẩy); các mẫu còn lại có phân cách `;`, ` - `, `,` hoặc ký tự ngoài span. Số 58 trong prompt do phiên điều phối đo bằng định nghĩa so **độ dài** (len(nối văn bản span) + 2 × (số span − 1) khác len(text)), vốn bỏ sót các mẫu dùng dấu phân cách cùng độ dài với ", " (ví dụ "; "); phiên điều phối xác nhận định nghĩa so chuỗi ở trên chặt hơn và đúng mục đích của H3, nên báo cáo dùng 66. Số này chỉ dùng để mô tả và để tách mẫu ở H3 (30 mẫu test).

## 1. H3 — xáo thứ tự trường (test, 100 mẫu, 446 span)

Dựng lại chuỗi từ gold span nối bằng ", ". 100% span giữ nguyên văn (kiểm text[start:end] ở mọi điều kiện). Mốc ghép cặp là điều kiện (i) dựng lại theo thứ tự gốc, không phải chuỗi gốc. Dựng lại theo thứ tự gốc làm đổi chữ ở **30/100** mẫu (đúng bằng số mẫu có văn bản ngoài span); mỗi seed hoán vị có 4 mẫu rơi vào hoán vị đồng nhất.

| Hệ | Điều kiện | F1 [CI 95%] | Δ so (i) [CI ghép cặp] | Đọc |
|---|---|---|---|---|
| CRF-INDEP | chuỗi gốc (tham chiếu) | 0,9076 [0,867; 0,943] | −0,025 [−0,064; +0,009] | không tách được |
| CRF-INDEP | (i) thứ tự gốc, dựng lại | 0,9329 [0,906; 0,958] | mốc | — |
| CRF-INDEP | (ii) đảo ngược | 0,2171 [0,195; 0,239] | **−0,716** [−0,742; −0,689] | giảm |
| CRF-INDEP | hoán vị seed 42 | 0,4550 [0,410; 0,500] | **−0,478** [−0,526; −0,429] | giảm |
| CRF-INDEP | hoán vị seed 1337 | 0,4270 [0,380; 0,476] | **−0,506** [−0,557; −0,453] | giảm |
| CRF-INDEP | hoán vị seed 2025 | 0,4651 [0,420; 0,511] | **−0,468** [−0,519; −0,415] | giảm |
| HEUR-JW | chuỗi gốc | 0,9112 [0,876; 0,941] | −0,020 [−0,048; +0,003] | không tách được |
| HEUR-JW | (i) thứ tự gốc, dựng lại | 0,9308 [0,910; 0,950] | mốc | — |
| HEUR-JW | (ii) đảo ngược | 0,7722 [0,746; 0,797] | **−0,159** [−0,176; −0,142] | giảm |
| HEUR-JW | hoán vị seed 42 / 1337 / 2025 | 0,809 / 0,820 / 0,825 | −0,122 / −0,111 / −0,106 (CI đều loại 0) | giảm |

Tách theo mẫu có văn bản ngoài span (30 mẫu) và không có (70 mẫu): chiều giảm giống nhau ở cả hai nhóm (CRF đảo ngược −0,659 và −0,743; CRF hoán vị −0,42…−0,54), nên sụt giảm không do việc dựng lại bỏ chữ ngoài span. Theo nhãn (CRF, đảo ngược): SoNha 0,994 → 0,0; TinhThanh 0,995 → 0,0; PhuongXa 0,915 → 0,593; HEUR-JW mất chủ yếu ở SoNha (1,0 → 0,0 khi đảo; 0,34 khi hoán vị); TenDuong, Ngo/Hem, TinhThanh gần như giữ, PhuongXa giảm nhẹ (0,95 → 0,84 khi đảo).

**Kết luận H3 (ủng hộ).** CRF-INDEP phụ thuộc rất mạnh vào thứ tự trường (F1 còn 22–47%, mọi CI loại 0); HEUR-JW phụ thuộc vừa phải và tập trung ở số nhà. Đối chiếu Yassine et al. (mô hình tiếng Hàn còn khoảng 28% khi xáo thứ tự): cùng bậc độ lớn với CRF của chúng ta khi đảo ngược (0,22), nhưng khác ngôn ngữ, mô hình và dữ liệu, chỉ so định tính. Suy luận (chưa đo): CRF có đặc trưng `position_bucket` và ngữ cảnh ±1 nên phụ thuộc thứ tự là kết quả có thể dự đoán từ thiết kế, không riêng của "học thuộc".

## 2. E1 — tiền xử lý 2×2: dấu phẩy × chữ hoa

28/400 mẫu không có dấu phẩy (test: 14), phép bỏ phẩy không đổi gì ở các mẫu đó. Mốc: điều kiện gốc.

**Chế độ (a): chỉ nhiễu lúc test, mô hình gốc**

| Điều kiện | CRF-INDEP F1 [CI] | Δ [CI ghép cặp] | HEUR-JW F1 [CI] | Δ [CI ghép cặp] |
|---|---|---|---|---|
| giữ phẩy, giữ hoa (gốc) | 0,9076 [0,867; 0,943] | mốc | 0,9112 [0,876; 0,941] | mốc |
| bỏ phẩy, giữ hoa | 0,5907 [0,539; 0,645] | **−0,317** [−0,368; −0,264] | 0,7772 [0,726; 0,825] | **−0,134** [−0,172; −0,098] |
| giữ phẩy, hạ chữ | 0,8884 [0,847; 0,926] | −0,019 [−0,038; −0,001] | 0,9112 | 0,000 (hai chuỗi dự đoán trùng ở 100/100 mẫu, ghi DEGENERATE) |
| bỏ phẩy, hạ chữ | 0,6570 [0,602; 0,712] | **−0,251** [−0,305; −0,198] | 0,7772 | −0,134 [−0,172; −0,098] |

**Chế độ (b): huấn luyện và test cùng điều kiện (4 lần huấn luyện CRF)**

| Điều kiện | CRF-INDEP F1 [CI] | Δ [CI ghép cặp] | Đọc |
|---|---|---|---|
| giữ phẩy, giữ hoa (tái lập hash b4ff0d23) | 0,9076 | mốc | — |
| bỏ phẩy, giữ hoa | 0,8498 [0,800; 0,895] | −0,058 [−0,088; −0,030] | giảm |
| giữ phẩy, hạ chữ | 0,9041 [0,863; 0,940] | −0,004 [−0,013; +0,005] | không tách được |
| bỏ phẩy, hạ chữ | 0,8492 [0,798; 0,896] | −0,058 [−0,090; −0,029] | giảm |

**Kết luận E1.** Dấu phẩy là tín hiệu chính, chữ hoa gần như không quan trọng. Bỏ phẩy lúc test làm CRF mất 0,32 F1 và HEUR-JW mất 0,13; huấn luyện cùng điều kiện lấy lại phần lớn (còn −0,058, CI vẫn loại 0). Hạ chữ: CRF mất 0,019 ở chế độ (a) (CI sát 0: −0,038…−0,001) và không tách được ở chế độ (b); HEUR-JW không đổi vì luật không phân biệt hoa/thường. Hướng cụ thể: tiền xử lý chuẩn hóa chữ hoa là an toàn; **không** nên bỏ dấu phẩy ở đầu vào, và nếu dữ liệu thực thiếu phẩy thì phải huấn luyện kèm nhiễu này.

Nhãn theo hợp đồng cho từng ý: (1) "bỏ dấu phẩy gây suy giảm lúc test": **ủng hộ** (CRF −0,317, HEUR-JW −0,134, CI loại 0); (2) "huấn luyện cùng điều kiện lấy lại phần lớn": **ủng hộ một phần** (còn −0,058, CI vẫn loại 0); (3) "hạ chữ gây suy giảm": **không ủng hộ / không kết luận được** (CRF chế độ (a) −0,019 với CI sát 0, chế độ (b) −0,004 không tách được; HEUR-JW không đổi).

## 3. H2 — huấn luyện kèm địa chỉ thiếu trường

### Thiết kế đã dùng (đã sửa so với bản đầu; khớp số đã kiểm)

- Nguồn: Data 04 sau `leak_guard` (779) → bỏ TenDuong bắt đầu bằng ngõ/hẻm/ngách/kiệt (664) → bỏ trùng (số nhà, tên đường) GT với dev/test (653). Cả 653 dòng căn được span từ cột bề mặt vào `ChuoiDiaChi` bằng `align_unique` (0 dòng bỏ).
- Cột GT_* chỉ dùng để dựng khóa nhóm lãnh thổ (`admin_group_key`) và để lọc rò rỉ; không phải đặc trưng hay nhãn của mô hình (có test kiểm: tệp huấn luyện/suy luận chỉ có `sample_id`, `text`, `spans`).
- Chia theo khóa nhóm (seed 20261016): `heldout_missing` = 15/49 nhóm ADM (30%) + toàn bộ dòng UNRESOLVED; `aug_train` = 34 nhóm ADM còn lại. Hai phần rời nhóm (có test).

| Phần | Dòng | Nhóm | KieuThieu (district / housenumber / hn+ward / ward) | cu / mới |
|---|---|---|---|---|
| heldout_missing | 399 (gồm 190 UNRESOLVED) | 108 | 48 / 178 / 62 / 111 | 226 / 173 |
| aug_train | 254 | 34 | 23 / 115 / 29 / 87 | 76 / 178 |

- N ∈ {120, 240} đạt đủ (aug_train có 254 dòng) nên N thực = N. Mỗi N lấy phân tầng theo KieuThieu, ba seed lấy mẫu {20261016 (chính), 1337, 2025}; AUG-FULL lấy từ pool Data 01/03 (1.779 dòng sau khi để riêng 300 dòng đánh giá "đầy đủ") với đúng số cu/mới của phần AUG-MISSING cùng seed. Không nhóm nào của AUG-MISSING nằm trong heldout.
- Thước đo chính: scorer 5 trường trên heldout_missing với GT_* làm silver (`gt`). GT còn chứa trường đã bị bỏ khỏi chuỗi (số nhà/phường) nên **không mô hình nào phục hồi được** — trần F1 thấp (~0,64 ở BASE). Vì vậy tôi báo thêm `surface` (đáp án = chỉ các trường thực sự có trong chuỗi), để phân biệt "mô hình chiết xuất sai" với "trường vắng mặt". Kết luận về các so sánh AUG (AUG-MISSING, AUG-FULL, BASE) giống nhau ở hai cách chấm; **câu hỏi "có tụt hay không" thì phụ thuộc cách chấm** (xem dưới).

### Kết quả (seed lấy mẫu chính 20261016; CI theo nhóm lãnh thổ)

| Mô hình | N | F1 `gt` [CI] | F1 `surface` [CI] | Trung bình ± độ lệch trên 3 seed lấy mẫu (`gt`) |
|---|---|---|---|---|
| BASE (240) | — | 0,6407 [0,609; 0,661] | 0,8837 [0,829; 0,916] | (một mô hình) |
| AUG-MISSING | 120 | 0,6513 | 0,8968 | 0,6500 ± 0,0032 |
| AUG-FULL | 120 | 0,6504 | 0,8957 | 0,6489 ± 0,0017 |
| AUG-MISSING | 240 | 0,6538 [0,628; 0,674] | 0,8998 [0,853; 0,928] | 0,6594 ± 0,0049 |
| AUG-FULL | 240 | 0,6545 [0,628; 0,675] | 0,9009 [0,856; 0,926] | 0,6551 ± 0,0013 |

**Delta ghép cặp (`gt`, N = 240, seed 20261016; CI theo nhóm):** AUG-MISSING − BASE = +0,013 [+0,005; +0,027] (tăng); AUG-FULL − BASE = +0,014 [+0,003; +0,031] (tăng); **AUG-MISSING − AUG-FULL = −0,001 [−0,014; +0,011] (không tách được)**. Hai seed còn lại cho AUG-MISSING − AUG-FULL = +0,005 [−0,009; +0,022] và +0,008 [−0,006; +0,024]: mọi CI đều chứa 0 ở cả 3 seed × 2 N × 2 cách chấm. Theo KieuThieu (N = 240): lợi ích tập trung ở `drop_housenumber` (+0,028 [+0,012; +0,057]) và `drop_housenumber_ward` (+0,017 [+0,003; +0,040]); `drop_ward` và `drop_district` không đổi; AUG-FULL tăng tương đương ở `drop_housenumber` (+0,027).

**BASE có tụt trên địa chỉ thiếu trường không? Phụ thuộc thước đo.** So heldout_missing (399 dòng) với 300 địa chỉ đầy đủ Data 01/03 đã lọc (F1 0,948; chấm lại từ prediction đã lưu vào `cpu_hypotheses_20261016_v2/h2_drop_vs_full_gt.csv`, không huấn luyện lại; CI theo nhóm ở phía thiếu trường):

| Cách chấm | BASE trên heldout_missing | Δ so với đầy đủ [CI] | Giảm tương đối |
|---|---|---|---|
| `gt` (thước đo chính của hợp đồng) | 0,6407 | −0,307 [−0,343; −0,279] | 32,4% (trong khoảng 20–40% của đề cương) |
| `surface` | 0,8837 | −0,064 [−0,123; −0,028] | 6,8% |

Mức −0,307 của `gt` chủ yếu do cấu trúc dữ liệu: 461/1.822 trường GT (25,3%) vắng khỏi chuỗi nên recall tối đa dưới `gt` là 0,747 và không mô hình nào phục hồi được. Với `surface`, phần tụt thật nằm ở mẫu thiếu số nhà: BASE `drop_housenumber` 0,853, `drop_housenumber_ward` 0,720, trong khi `drop_district` 0,950 và `drop_ward` 0,963 ngang mức đầy đủ (0,948). Sụt giảm còn nguyên sau khi tăng cường (`surface`: AUG-MISSING 240 −0,047 [−0,097; −0,013], AUG-FULL 240 −0,055; `gt`: −0,293 và −0,302). Cả hai cách chấm cùng chiều: heldout_missing thấp hơn địa chỉ đầy đủ với CI loại 0; chỉ khác độ lớn và nguyên nhân.

**Thước đo phụ (POST_HOC_SECONDARY, test, N = 240):** 20 mẫu `04_missing`: BASE 0,933; AUG-MISSING 0,940 (Δ +0,007 [−0,056; +0,063]); AUG-FULL 0,933 (Δ 0). 80 mẫu còn lại: AUG-MISSING −0,003 [−0,016; +0,011]. Không có thay đổi tách được; 20 mẫu quá ít để kết luận. **Dev (kiểm không suy giảm):** BASE 0,906; AUG-MISSING 240: 0,888 (Δ −0,018 [−0,039; +0,001]); AUG-FULL 240: 0,891 (Δ −0,015 [−0,050; +0,023]). CI chứa 0 nhưng điểm ước lượng nghiêng về phía giảm ở cả hai, nên **không loại được suy giảm nhẹ** trên dev.

**Kết luận H2: phần "tụt khi thiếu trường" — ủng hộ, nhưng độ lớn và nguyên nhân phụ thuộc thước đo** (`gt`: giảm ~32%, trong khoảng của đề cương, chủ yếu do 25,3% trường GT vắng khỏi chuỗi; `surface`: ~6 điểm, 6,8%, tập trung ở mẫu thiếu số nhà). **Phần "phục hồi đặc thù khi thêm dữ liệu thiếu trường" — không ủng hộ.** Thêm dữ liệu giúp CRF khoảng +0,013 F1 trên heldout_missing, nhưng thêm địa chỉ đầy đủ giúp ngang hệt (AUG-MISSING − AUG-FULL không tách khỏi 0, kể cả sau khi bỏ các dòng heldout chồng với AUG-FULL, xem giới hạn 3). Dữ liệu thiếu trường không tốt hơn chỉ-thêm-dữ-liệu ở quy mô này.

## 4. H4 — hiệu năng theo nhóm nhãn (prediction test đã freeze, 5 hệ)

Nhóm (định nghĩa vận hành của gói): hành chính = PhuongXa, QuanHuyen, TinhThanh (244 span gold); đường sá = SoNha, TenDuong, Ngo/Hem (200); mốc = MocDinhVi, HuongDi (0); khác = ToaNha/CanHo, GhiChu, Khac (2).

| Hệ | F1 hành chính [CI] | F1 đường sá [CI] | Δ hành chính − đường sá [CI ghép cặp] | Đọc |
|---|---|---|---|---|
| HEUR-JW | 0,8953 [0,858; 0,928] | 0,9333 [0,894; 0,968] | −0,038 [−0,068; −0,008] | hành chính thấp hơn |
| CRF-INDEP | 0,9079 [0,862; 0,948] | 0,9118 [0,862; 0,955] | −0,004 [−0,048; +0,042] | không tách được |
| PHOBERT-CRF | 0,9795 [0,961; 0,996] | 0,9950 [0,987; 1,000] | −0,016 [−0,035; +0,002] | không tách được |
| PROPOSED-DYN | 0,9754 [0,954; 0,992] | 0,9950 [0,987; 1,000] | −0,020 [−0,042; −0,0004] | hành chính thấp hơn (sát 0) |
| PROPOSED-NO-CONSTRAINT | 0,9795 [0,959; 0,996] | 0,9950 [0,987; 1,000] | −0,016 [−0,036; +0,002] | không tách được |

- **Mốc: `NOT_EVALUABLE_NO_GOLD_SUPPORT`** (support test = 0 cho cả 5 hệ). Nhóm khác: support 2, `LOW_SUPPORT`, F1 0,0, không kết luận.
- **Số tham khảo (group 5-fold theo `source_group`, seed 42, CRF, 240 mẫu train; 235 nhóm, fold 47/47/47/49/50):** F1 tổng 0,9177; hành chính 0,9391 (573 span), đường sá 0,9158 (460), **mốc support 11, F1 0,0, `LOW_SUPPORT`**, khác support 13, F1 0,143, `LOW_SUPPORT`. Chỉ là tham khảo, không kết luận về mốc.
- **Kết luận H4: không kết luận được ở mức tổng quát.** Hành chính thấp hơn đường sá ở 2/5 hệ (HEUR-JW, PROPOSED-DYN) với CI loại 0 (DYN sát biên), ba hệ còn lại không tách được; chiều của CRF khác chiều trong k-fold (hành chính cao hơn). Nhóm mốc chưa kiểm được bằng dữ liệu hiện có.

## 5. Tầng 2 — neural chỉ suy luận (PHOBERT-CRF, PROPOSED-DYN × 3 checkpoint WP3b): `NOT_RUN`

**NOT_RUN — adapter khóa từ chối nạp checkpoint.** Lúc 14/10/2026 22:55 (UTC+7), nạp PHOBERT-CRF seed 42 báo nguyên văn: `RuntimeError: ['DISK_BELOW_TRAINING_ARTIFACT_BUDGET:need 21474836480 bytes free per new run']` (cần 20 GiB trống; đo được khoảng 18 GiB trên ổ D:). Cổng nằm trong `src/modeling/resources.py` (mã khóa, không sửa) và cũng bảo vệ chính ổ D:. Theo quy tắc của gói, tôi **không** vòng qua kiểm tra này và không xóa gì; việc giải phóng chỗ thuộc chủ dự án. Đầu vào đã chuẩn bị: chín điều kiện văn bản ở `data/interim/modeling/sprint04/cpu_hypotheses_20261016_v1/tier2/inputs/`, manifest khai báo trước chấm ở `.../tier2_local_neural/run_manifest.json`, và bước smoke bắt buộc (prediction văn bản gốc phải trùng prediction test WP3b cùng seed). Tầng 2 sẽ chạy như một bước tiếp nối riêng, không chặn review Tầng 1. Để chạy tiếp sau khi giải phóng ≥ 2 GiB:

```bash
python -m scripts.71_run_cpu_hypothesis_experiments tier2-run --only original_text --only-model pcrf --only-seed 42   # smoke
python -m scripts.71_run_cpu_hypothesis_experiments tier2-run                                                      # đủ 6 checkpoint, tuần tự
python -m scripts.71_run_cpu_hypothesis_experiments tier2-score
```
Mỗi checkpoint mất vài phút để nạp. Mọi số Tầng 2 phải mang nhãn `LOCAL_CPU_RETRAINED`.

## 6. Giới hạn

1. Test Sprint 3 đã bị quan sát: mọi số trên test (H3, E1, H4, phần phụ của H2) là phân tích độ bền hậu nghiệm, không dùng để chọn.
2. Nhãn Data 04 là silver từ generator; GT_* chứa trường không có trong chuỗi nên thước đo `gt` bị chặn trên; đã báo thêm thước đo `surface`.
3. Tăng cường **không rời lãnh thổ với test** (cùng chuẩn với Sprint 3, theo địa chỉ). Còn 22 dòng Data 04 giữ lại có cặp (số nhà, tên đường) bề mặt trùng một mẫu dev/test (lọc trên GT theo đặc tả, nên số nhà bề mặt có thể trống). **Chồng giữa AUG-FULL và heldout_missing ở mức địa chỉ (đo được):** Data 04 được sinh từ cùng bể với Data 01/03 (`scripts/03_generate_benchmarks.py`), nên bể AUG-FULL chứa bản đầy đủ của chính một số địa chỉ heldout. Số dòng heldout có địa chỉ (số nhà, tên đường, phường, tỉnh) nằm trong tập AUG-FULL: N120 có 8 / 8 / 9 và N240 có 11 / 15 / 11 theo ba seed lấy mẫu; AUG-MISSING có 0–2; `eval_full` có 16 dòng trùng heldout (`h2_aug_full_overlap_check.csv`). Chiều thiên lệch **có lợi cho AUG-FULL**, tức đẩy AUG-MISSING − AUG-FULL về phía "không hơn". Bỏ các dòng chồng rồi tính lại: delta đổi tối đa 0,0014 (ví dụ N240 seed 1337 `gt`: +0,0054 → +0,0067) và cả 12 CI (3 seed × 2 N × 2 cách chấm) vẫn chứa 0, nên kết luận H2 đứng.
4. Chuỗi dựng lại ở H3 không còn nguyên văn (30/100 đổi ngay cả ở thứ tự gốc); chỉ kiểm tính bền với thứ tự.
5. Heldout_missing và tập đầy đủ dùng chung bể nguồn; khác biệt chính giữa chúng là trường bị bỏ. Tiền tố viết tắt không ảnh hưởng đáng kể (BASE `surface`: 0,882 trên dòng có viết tắt so với 0,885 không viết tắt, số đo của review độc lập, chưa tự tái tính).
6. 20 mẫu `04_missing` của test là quá ít; chỉ có 4 nhóm tình huống thiếu trường, nhóm `drop_district` chỉ 48 dòng.
7. Hạt giống: CRF tất định (L-BFGS), nên phương sai ở H2 chỉ đến từ việc lấy mẫu tập tăng cường (ba seed), không phải từ khởi tạo.
8. Nhóm mốc không có support ở test và chỉ 11 span ở train.

## 7. Tái lập

```bash
cd /mnt/d/DACN && source ~/.venv_dacn/bin/activate
python -m scripts.71_run_cpu_hypothesis_experiments run \
    --interim-dir <dir mới> --processed-dir <dir mới>      # ~3,5 phút; từ chối ghi đè thư mục đã có
python -m unittest tests.test_group1_cpu_experiments -v      # 16 test
python -m unittest discover -s tests                         # 422 test: 414 PASS / 8 SKIP / 0 FAIL
```
Đã chạy lại từ đầu vào thư mục khác: cả 13 tệp đầu ra, 90 tệp prediction và 23 checkpoint CRF có SHA-256 trùng bản v1 (chỉ `run_manifest.json` khác ở các trường thời gian).

Lưu ý: tên thư mục/tệp ở interim chứa ký tự `|` (ví dụ `e1b/commas_drop|case_keep/`), trên Windows hiện thành U+F07C và khó mở bằng công cụ Windows; không đổi tên tệp, không ảnh hưởng kết quả. Chấm lại `gt` và kiểm chồng AUG-FULL (không huấn luyện lại): `python data/processed/evaluation/sprint04/cpu_hypotheses_20261016_v2/rescore_drop_gt.py`.

## 8. Điểm suy luận thay vì đo

- Giải thích vì sao CRF nhạy với thứ tự (đặc trưng `position_bucket`, ngữ cảnh ±1) và vì sao HEUR-JW chỉ mất ở số nhà: suy từ mã, không có thí nghiệm bóc tách đặc trưng.
- Nguyên nhân của mức tụt `gt` (25,3% trường vắng) là số đo; việc "tụt thật nằm ở mẫu thiếu số nhà" là số đo trên `surface`; còn lý do vì sao thiếu số nhà khó hơn (không có mỏ neo số ở đầu chuỗi) là suy luận, chưa có thí nghiệm.
- Câu "dữ liệu thiếu trường không tốt hơn chỉ-thêm-dữ-liệu" là kết luận ở quy mô N ≤ 240 và 653 dòng gốc; quy mô lớn hơn chưa kiểm.
