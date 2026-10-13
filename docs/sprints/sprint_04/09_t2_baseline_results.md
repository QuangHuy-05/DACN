# Kết quả baseline T2 — ánh xạ đơn vị hành chính hai chiều (WP1)

**Ngày chạy:** 13/10/2026 (nhãn `20261014` trong tên thư mục là mã phiên bản theo kế hoạch, không phải ngày chạy). **Run:** `data/processed/evaluation/sprint04/t2_baseline_20261014_v1/` (manifest `run_manifest.json`). **Mã:** `src/evaluation/t2_lookup.py`, `src/evaluation/t2_scorer.py`, `scripts/66_run_t2_baseline.py`, `tests/test_t2_baseline.py`.
**Bảng tra:** gazetteer `s3_v4_nso_dual_snapshot_release2` (10.597 cạnh nguyên tử, kiểm hash theo `manifest.json`). Mã cũ của gazetteer còn *partial* (8.607 mã cũ verified, 2.187 chưa xác minh); T2 ở đây tra bằng **tên**, không dùng mã cũ.

## 0. Trạng thái các đầu ra

| Đầu ra | Trạng thái | Ghi chú |
|---|---|---|
| Tầng 1: STRICT / DEFAULT-MAIN / DEFAULT-FIRST × oracle × N2 × hai chiều | **PASS** | CI cụm, B = 10.000, seed 20261014 |
| E3 (bất đối xứng) | **PASS** | McNemar chính xác + bootstrap ghép cặp theo 3 kiểu cụm |
| Phân tích đồ thị toàn bộ cạnh | **PASS** (nhãn "cận cấu trúc") | `graph_analysis.json` |
| Tầng 2: độ nhạy N0/N1, T2-VNADMIN, T2-SINGLE-VERSION, tình huống C và D | **PASS** | |
| Tầng 3: điều kiện pipeline (HEUR-JW, CRF-INDEP) | **PASS** (đã chạy) | CRF chạy tiến trình riêng trong runtime CRF |
| Tầng 3: T2-STREET (E2) | **PASS** về mặt chạy; **diễn giải có điều kiện** | tỷ lệ bằng chứng 89,0% (L1) / 42,1% (L2) ≥ 20%, nên không rơi vào `NOT_EVALUABLE_LOW_EVIDENCE`; xem mục 6 về rò rỉ hàng xóm |
| A và C trên Data 07 | `NOT_EVALUABLE_NO_SUPPORT` | Data 07 chỉ có B (244) và M (356) |
| Chiều mới→cũ của VNADMIN và STREET | `NOT_SUPPORTED` | vẫn có dòng trong bảng |
| Chiều về hệ cũ trên Data 06 | `NOT_EVALUABLE_NO_UNIQUE_GOLD` | quan hệ N-1 |

Bộ test toàn repo: **349 test, 0 FAIL, 8 SKIP** (mốc cũ 319 + 30 test mới).

## 1. Tái lập các số F1–F3 (bước đầu tiên)

Mọi số bên dưới được `preflight` của script kiểm tự động; lệch là dừng trước khi ghi bất kỳ hệ thống nào. **Không số nào lệch.**

| Số cần tái lập | Kỳ vọng | Đo được |
|---|---|---|
| Data 07: B / M | 244 / 356 | 244 / 356 |
| Mã phường mới; chuỗi cũ thô; dòng ở Hà Nội | 23; 69; 441 | 23; 69; 441 |
| Số phần khi tách dấu phẩy (cũ) | 5:532, 4:66, 9:1, 6:1 | giống hệt |
| Khớp khóa cũ N0 / N1 | 5 / 535 | 5 / 535 |
| Khớp khóa mới N0 | 600 | 600 |
| Fan-out N1: M (4/2/0 đích), B (1/0 đích) | 299/44/13; 192/52 | giống hệt; 343/600 cặp nhiều ứng viên |
| 335/356 cặp M có "Tách — nhập chủ yếu" | 335 | 335 |
| edges.csv: B / C / M / A | 9.432 / 132 / 1.030 / 3 | giống hệt; nhãn tính từ bậc đồ thị trùng cột `relation` 10.597/10.597 |
| Đối chiếu với `AdministrativeMapping` | chênh đúng 5 | 5 cạnh chỉ có ở bảng tham chiếu (chính là 5 chuyển đổi phi nguyên tử); 0 cạnh chỉ có ở edges.csv |
| Data 06: C1 / C2 / C3; khớp như khóa cũ đầy đủ (N1) | 420/120/60; 421 | 420/120/60; 421 |

Số mới đo thêm: **N2 (alias đã kiểm chứng) khớp 600/600 phía cũ**, cả 600 cặp có cạnh `(đơn vị cũ → đơn vị mới)` tồn tại trong edges.csv và mã `MaPhuongXaMoi` trùng 600/600. Sau chuẩn hóa N2, 69 chuỗi cũ thô gộp thành **49 đơn vị cũ chuẩn hóa**; đây là số cụm của CI chiều cũ→mới (không phải 69).

## 2. Thiết kế (khai báo trong manifest trước khi chấm)

- **Gold:** cũ→mới = đơn vị mới (tỉnh+phường) của `DiaChi_Moi`, đối chiếu thêm `MaPhuongXaMoi`; mới→cũ = đơn vị cũ (tỉnh+huyện+phường) của `DiaChi_Cu` giải ở N2. Mức chuẩn hóa chỉ ảnh hưởng *cách khớp đầu vào*, không ảnh hưởng cách xác định gold.
- **Chấm:** abstain tính là không đúng; `silent_error_rate` = (trả lời sai **và** không cảnh báo) / 600; `NO_MATCH` là thất bại *có* cảnh báo, luôn nằm trong mẫu số. Bộ chọn mặc định (MAIN/FIRST) không trả cảnh báo.
- **CI:** bootstrap percentile theo cụm = đơn vị nguồn của chiều đang xét (49 đơn vị cũ chuẩn hóa cho cũ→mới; 23 phường mới cho mới→cũ), B = 10.000, seed 20261014; số cụm ghi ở mọi CI. Khi mọi dòng cho cùng kết quả (ví dụ 244/244 đúng) CI là `DEGENERATE` (không đổi), không bịa khoảng.
- **Cụm cho E3:** chọn trước là phường mới (23), vì ít cụm hơn nên thận trọng hơn; báo thêm đơn vị cũ (49) và `admin_group_key` (21).
- Hệ thống và định nghĩa đầy đủ: `run_manifest.json → systems / rules`.

## 3. Bảng T2 chính (oracle-segmentation, N2)

Accuracy theo cặp (micro) với CI 95% cụm. `k` = số cụm. Silent = số lỗi im lặng trên 600 (hoặc trên số dòng của lát cắt).

### 3.1 Toàn bộ 600 cặp

| Hệ thống | Chiều | Accuracy [CI] (k) | Coverage | Accuracy khi trả lời | Lỗi im lặng (tỷ lệ) | Macro theo đơn vị |
|---|---|---|---|---|---|---|
| STRICT | cũ→mới | 0,407 [0,158; 0,927] (49) | 0,407 | 1,000 (244/244) | 0 (0%) | 0,796 |
| STRICT | mới→cũ | 0,000 (DEGENERATE) (23) | 0,000 | NOT_EVALUABLE | 0 (0%) | 0,000 |
| DEFAULT-MAIN | cũ→mới | 0,965 [0,831; 1,000] (49) | 1,000 | 0,965 | **21 (3,5%)** | 0,959 |
| DEFAULT-MAIN | mới→cũ | 0,077 [0,040; 0,224] (23) | 1,000 | 0,077 | **554 (92,3%)** | 0,323 |
| DEFAULT-FIRST | cũ→mới | 0,955 [0,812; 0,997] (49) | 1,000 | 0,955 | **27 (4,5%)** | 0,898 |
| DEFAULT-FIRST | mới→cũ | 0,037 [0,013; 0,196] (23) | 1,000 | 0,037 | **578 (96,3%)** | 0,358 |
| T2-VNADMIN (geocoder tắt) | cũ→mới | 0,962 [0,823; 1,000] (49) | 0,997 (2 dòng trả rỗng) | 0,965 | 21 (3,5%) | 0,946 |
| T2-VNADMIN | mới→cũ | NOT_SUPPORTED | — | — | — | — |
| T2-SINGLE-VERSION | cũ→mới | 0,087 [0,016; 0,297] (49) | 0,100 | 0,867 | 8 (1,3%) | 0,163 |
| T2-SINGLE-VERSION | mới→cũ | 0,087 [0,017; 0,419] (23) | 0,235 | 0,369 | **89 (14,8%)** | 0,206 |

Candidate-recall = 1,000 cho mọi hệ thống tra bảng ở N2 (xem mục 8, tính vòng lặp). Số ứng viên trung bình trên dòng có khớp: cũ→mới 2,59 (trung vị 3); mới→cũ 9,07 (trung vị 10; tối đa 14).

### 3.2 Tách theo `LoaiAnhXa` (A và C: `NOT_EVALUABLE_NO_SUPPORT`, n = 0)

| Hệ thống | Chiều | B (n = 244) | M (n = 356) |
|---|---|---|---|
| STRICT | cũ→mới | 1,000 (DEGENERATE, 39 đơn vị), im lặng 0 | 0,000: 356/356 abstain `AMBIGUOUS` |
| DEFAULT-MAIN | cũ→mới | 1,000 (DEGENERATE) | 0,941 [0,296; 1,000] (10), im lặng 21; macro 0,800 |
| DEFAULT-FIRST | cũ→mới | 1,000 (DEGENERATE) | 0,924 [0,143; 0,993] (10), im lặng 27; macro 0,500 |
| T2-VNADMIN | cũ→mới | 0,992 (2 dòng rỗng), im lặng 0 | 0,941, im lặng 21 |
| DEFAULT-MAIN | mới→cũ | 0,189 [0,075; 0,365] (20), im lặng 198 | 0,000 (5 cụm), im lặng 356 |
| DEFAULT-FIRST | mới→cũ | 0,078 [0,026; 0,227] (20), im lặng 225 | 0,008 [0,000; 0,400] (5), im lặng 353 |

### 3.3 Tách theo `HinhThucSapNhap` (cũ→mới) — chỗ DEFAULT-MAIN "được lợi"

| Hệ thống | Hợp nhất toàn bộ (244) | Tách — nhập chủ yếu (335) | Tách — một phần (21) |
|---|---|---|---|
| DEFAULT-MAIN | 1,000 | **1,000** | **0,000** (21 sai im lặng) |
| DEFAULT-FIRST | 1,000 | 0,919 [0,015; 0,992] (27 sai im lặng) | 1,000 |
| T2-VNADMIN | 0,992 | 1,000 | 0,000 |

Độ chính xác 96,5% của DEFAULT-MAIN **hoàn toàn do cách lấy mẫu**: nó đúng 335/335 cặp "nhập chủ yếu" và sai 21/21 cặp "một phần". Heuristic mặc định của thư viện (T2-VNADMIN, nhánh `divided_default_after_geocoder_unavailable` cho cả 356 cặp M) cho đúng cùng kiểu kết quả. DEFAULT-FIRST tốt hơn trên "một phần" và kém hơn trên "nhập chủ yếu". Không chọn biến thể nào là "đẹp hơn".

### 3.4 Độ nhạy theo mức chuẩn hóa tên (chiều cũ→mới; phía mới khớp 600/600 ở cả N0, N1, N2 nên chiều mới→cũ không đổi giữa các mức)

| Hệ thống | Mức | Khớp khóa | Coverage | Accuracy | NO_MATCH | Lỗi im lặng |
|---|---|---|---|---|---|---|
| STRICT | N0 / N1 / N2 | 5 / 535 / 600 | 0,005 / 0,320 / 0,407 | 0,005 / 0,320 / 0,407 | 595 / 65 / 0 | 0 / 0 / 0 |
| DEFAULT-MAIN | N0 / N1 / N2 | 5 / 535 / 600 | 0,008 / 0,892 / 1,000 | 0,008 / 0,860 / 0,965 | 595 / 65 / 0 | 0 / 19 / 21 |
| DEFAULT-FIRST | N0 / N1 / N2 | 5 / 535 / 600 | 0,008 / 0,892 / 1,000 | 0,007 / 0,860 / 0,955 | 595 / 65 / 0 | 1 / 19 / 27 |

Chuỗi OSM thô gần như không khớp được bảng (5/600); chuẩn hóa của `administrative_mapping` đưa lên 535/600; 65 dòng còn lại (52 B, 13 M) cần alias đã kiểm chứng. Chuẩn hóa tên là một yếu tố thí nghiệm thật, lớn hơn mọi khác biệt giữa các heuristic mặc định.

## 4. Điều kiện pipeline (span từ mô hình rồi mới tra, N2; không huấn luyện lại)

Cấu hình HEUR-JW và checkpoint CRF-INDEP được kiểm SHA-256 theo `model_config.json` đã khóa trước khi chạy (không lệch). Quy tắc span (khai báo trước): lấy span PhuongXa/QuanHuyen/TinhThanh phải nhất; thiếu cấp nào thì để trống làm ký tự thay thế (thiếu phường = NO_MATCH). Số chuỗi thiếu cấp: HEUR-JW thiếu tỉnh 149/1.200 và thiếu huyện 42/600 chuỗi cũ; CRF-INDEP thiếu phường 16/1.200.

| Mô hình | Hệ thống | Chiều | Accuracy [CI] | Coverage | NO_MATCH | AMBIGUOUS | Im lặng |
|---|---|---|---|---|---|---|---|
| (oracle, để so) | DEFAULT-MAIN | cũ→mới | 0,965 | 1,000 | 0 | 0 | 21 |
| HEUR-JW | STRICT | cũ→mới | 0,392 [0,150; 0,899] | 0,392 | 7 | 358 | 0 |
| HEUR-JW | DEFAULT-MAIN | cũ→mới | 0,950 [0,791; 0,997] | 0,988 | 7 | 0 | 23 |
| HEUR-JW | DEFAULT-FIRST | cũ→mới | 0,940 [0,771; 0,990] | 0,988 | 7 | 0 | 29 |
| CRF-INDEP | STRICT | cũ→mới | 0,377 [0,144; 0,871] | 0,377 | 18 | 356 | 0 |
| CRF-INDEP | DEFAULT-MAIN | cũ→mới | 0,935 [0,759; 0,990] | 0,970 | 18 | 0 | 21 |
| CRF-INDEP | DEFAULT-FIRST | cũ→mới | 0,925 [0,739; 0,983] | 0,970 | 18 | 0 | 27 |
| cả hai | mọi hệ thống | mới→cũ | y hệt oracle (0,000 / 0,077 / 0,037) | — | 0 | — | — |

Lỗi tách span làm giảm độ phủ 1–3 điểm phần trăm ở chiều cũ→mới; phần còn lại của accuracy do cùng lựa chọn ứng viên như điều kiện oracle. Chiều mới→cũ không đổi vì phía mới (chuỗi hai cấp) luôn tách đúng.

## 5. E3 — bất đối xứng hai chiều (oracle, N2, cùng 600 cặp)

Hiệu = accuracy(cũ→mới) − accuracy(mới→cũ). `b` = cũ→mới đúng & mới→cũ sai; `c` = ngược lại. McNemar chính xác hai phía.

| Hệ thống | cũ→mới | mới→cũ | Δ | b / c | McNemar p | CI Δ, cụm phường mới (k=23) | CI Δ, cụm đơn vị cũ (k=49) | CI Δ, cụm `admin_group_key` (k=21) |
|---|---|---|---|---|---|---|---|---|
| STRICT | 0,407 | 0,000 | 0,407 | 244 / 0 | < 1e-70 | [0,159; 0,991] | [0,158; 0,927] | [0,248; 1,000] |
| DEFAULT-MAIN | 0,965 | 0,077 | 0,888 | 533 / 0 | < 1e-100 | [0,776; 0,930] | [0,634; 0,971] | [0,733; 0,947] |
| DEFAULT-FIRST | 0,955 | 0,037 | 0,918 | 551 / 0 | < 1e-100 | [0,706; 0,979] | [0,719; 0,977] | [0,708; 0,943] |
| SINGLE-VERSION | 0,087 | 0,087 | 0,000 | 0 / 0 | không xác định (không có cặp bất đồng) | [0,000; 0,000] | [0,000; 0,000] | [0,000; 0,000] |

Theo lát cắt: B (cụm phường mới k=20) DEFAULT-MAIN Δ = 0,811 [0,635; 0,925]; M (k=5) DEFAULT-MAIN Δ = 0,941 [0,936; 1,000]. Với k = 5 cụm, CI của lát cắt M rất kém tin cậy dù hẹp. Bảng đầy đủ (kể cả điều kiện pipeline) ở `tables/t2_e3_asymmetry.csv`. Không có cặp nào mà mới→cũ đúng còn cũ→mới sai ở điều kiện oracle (c = 0 cho cả ba hệ thống tra bảng).

McNemar giả định các cặp độc lập; ở đây 600 cặp đến từ 23–49 đơn vị, nên p-value chỉ mang tính tham khảo. Kết luận nên dựa vào CI cụm.

## 6. E2 — heuristic mặc định so với T2-STREET

Chỉ mục `tên đường → tập phường mới` dựng từ Data 01 (1.000 dòng) và `osm_latest_clean.csv` (10.000 dòng); chỉ nhận dòng có đúng một giá trị là phường mới đã biết. Không nguồn nào có OSM ID nên chống rò rỉ bằng chuỗi: **L1** loại dòng có `ChuoiDiaChi` chuẩn hóa trùng một `DiaChi_Moi` (184 dòng); **L2** nghiêm ngặt loại thêm dòng trùng cặp (số nhà, tên đường chuẩn hóa) với bất kỳ địa chỉ nào của Data 07 (thêm 290 dòng). Kiểm bằng test trên dữ liệu thật: không dòng nào của chỉ mục có chuỗi trùng Data 07 hoặc cặp (số nhà, tên đường) bị cấm.

| Biến thể | Dòng giữ trong chỉ mục (/ 11.000) | Số tên đường | Dòng nhiều ứng viên | Bằng chứng quyết định | Tỷ lệ | Tên đường có trong chỉ mục (/600) |
|---|---|---|---|---|---|---|
| L1 | 3.406 | 591 | 356 | 317 | 89,0% | 531 |
| L2 | 3.116 | 574 | 356 | 150 | 42,1% | 438 |

Ghép cặp T2-STREET với mặc định *cùng luật dự phòng* (khi không có bằng chứng, STREET rơi về chính luật đó; chênh lệch chỉ đến từ bằng chứng):

| Cặp (cũ→mới) | Accuracy STREET | Accuracy mặc định | Δ | STREET đúng & mặc định sai / ngược lại | McNemar p | CI Δ (cụm đơn vị cũ, k=49) | Lỗi im lặng STREET / mặc định |
|---|---|---|---|---|---|---|---|
| L1, MAIN, toàn bộ | 1,000 | 0,965 | +0,035 | 21 / 0 | 1e-6 | [0,000; 0,169] | 0 / 21 |
| L1, FIRST, toàn bộ | 0,998 | 0,955 | +0,043 | 26 / 0 | < 1e-6 | [0,002; 0,184] | 1 / 27 |
| **L2, MAIN, toàn bộ** | **0,993** | 0,965 | **+0,028** | 17 / 0 | 1,5e-5 | [0,000; 0,135] | 4 / 21 |
| **L2, FIRST, toàn bộ** | **0,992** | 0,955 | **+0,037** | 22 / 0 | < 1e-6 | [0,002; 0,159] | 5 / 27 |
| L2, MAIN, riêng M (n=356, k=10) | 0,989 | 0,941 | +0,048 | 17 / 0 | 1,5e-5 | [0,000; 0,567] | 4 / 21 |
| L2, MAIN, riêng B (n=244) | 1,000 | 1,000 | 0 | 0 / 0 | — | DEGENERATE | 0 / 0 |
| L2, MAIN, chỉ dòng có bằng chứng quyết định (n=150) | 1,000 | 0,887 | +0,113 | 17 / 0 | 1,5e-5 | [0,000; 0,727] | 0 / 17 |

Trên B không có gì để chọn (một ứng viên), nên mọi lợi ích nằm ở phía một-nhiều (M). Hướng của hiệu ứng nhất quán (không cặp nào STREET sai mà mặc định đúng), nhưng cận dưới của CI cụm bằng hoặc gần 0 (0,000–0,002) vì chỉ có 10 đơn vị cũ thuộc M, nên chưa đủ căn cứ khẳng định mức cải thiện. **Giới hạn bắt buộc:** hàng xóm cùng đường do cùng người đóng góp OSM vẫn nằm trong chỉ mục (L2 chỉ loại cặp số nhà trùng, không loại số nhà khác trên cùng đường), nên accuracy 0,992–0,993 của L2 nhiều khả năng cao hơn hiệu quả thật trên địa chỉ chưa từng thấy; đọc L2 là một *cận trên* của lợi ích của tên đường, không phải ước lượng độc lập. Đây là suy luận về cơ chế; mức rò rỉ còn lại không đo được.

## 7. H5, phần T2

### 7.1 Tình huống C — chuỗi lai (Data 06, phân đoạn oracle, kết quả trên 599 dòng có gold)

Gold chỉ định nghĩa cho đích hệ mới. C1/C2: 540 dòng, đều tra được. C3: 59 dòng có đúng một đích theo **khóa cũ đầy đủ** (tỉnh + huyện + phường); **1 dòng bị loại khỏi mẫu số** (`d06:112`, "Phường 3, Thành phố Bạc Liêu, Tỉnh Cà Mau": khóa đầy đủ không có trong bảng vì tỉnh cũ là Bạc Liêu; nếu bỏ qua tỉnh thì đích là Phường Bạc Liêu, Cà Mau, nhưng không dùng định nghĩa đó). Hệ thống không đọc `KieuLai` hay `Span_He_Detail`.

| Giả định hệ nguồn | Hệ thống | NO_MATCH (cảnh báo) | AMBIGUOUS (abstain) | Khớp và đúng | **Khớp và sai (im lặng)** |
|---|---|---|---|---|---|
| coi là cũ | STRICT | 178 | 22 | 399 | **0** |
| coi là cũ | DEFAULT-MAIN | 178 | 0 | 415 | **6** (tất cả C1) |
| coi là cũ | DEFAULT-FIRST | 178 | 0 | 415 | **6** (tất cả C1) |
| coi là cũ | SINGLE-VERSION | 59 (cả 59 là C3) | 0 | 540 | 0 |
| coi là mới | STRICT / MAIN / FIRST / SINGLE | 59 (cả 59 là C3) | 0 | 540 | 0 |

Theo `KieuLai` ("coi là cũ", DEFAULT-MAIN): C1 420 → 157 NO_MATCH, 257 đúng, **6 sai im lặng**; C2 120 → 21 NO_MATCH, 99 đúng, 0 sai; C3 59 → 0 NO_MATCH, 59 đúng. Giả định "coi là mới" luôn đúng ở C1/C2 và thất bại có cảnh báo ở C3; giả định "coi là cũ" cứu được C3 nhưng để lọt 6 lỗi im lặng và 157 NO_MATCH ở C1. 421/599 chuỗi lai vẫn khớp khi tra như khóa cũ đầy đủ, đúng như đã đo trước (399 + 22 và 415 + 6). SINGLE-VERSION cho cùng kết quả ở hai giả định *theo cấu tạo* (hệ không biết phiên bản nên không có khái niệm "giả định"). Lỗi im lặng của tra bảng trên chuỗi lai là có thật nhưng nhỏ (6/599 = 1,0%); đa số chuỗi lai được xử lý đúng hoặc thất bại có cảnh báo vì tên phường mới thường trùng một phường cũ cùng huyện và đi về cùng một đích.

### 7.2 Tình huống D — tên phường tồn tại ở cả hai hệ trong cùng tỉnh

**Toàn gazetteer (cận cấu trúc, không phải lỗi quan sát):** trong 10.035 phường cũ, 1.989 có một phường mới *cùng tên* trong cùng tỉnh mới (1.989 cặp). Trong 1.989 cặp: 124 cùng phạm vi (6,2%), 1.708 có cạnh nhưng phạm vi khác (một bên còn láng giềng khác), 157 không có cạnh (cùng tên, lãnh thổ khác). **Nhóm D = 1.865/1.989 (93,8%)**.

**Trên Data 07, T2-SINGLE-VERSION** (nhóm D = có phường trùng tên ở hệ đích và cặp quan sát không thuộc "cùng phạm vi"):

| Chiều | Nhóm D | Đúng | Im lặng | Tỷ lệ lỗi im lặng trong nhóm | Ngoài nhóm D |
|---|---|---|---|---|---|
| cũ→mới | 60 (10,0% của 600) | 52 | **8** | 13,3% (1,3% của 600) | 540 dòng không có phường trùng tên: NO_MATCH có cảnh báo |
| mới→cũ | 141 (23,5% của 600) | 52 | **89** | **63,1%** (14,8% của 600) | 459 dòng NO_MATCH có cảnh báo |

Phần lớn lỗi im lặng thuộc loại "phường trùng tên là một đơn vị khác nhưng vẫn có cạnh với đơn vị nguồn" (8 ở cũ→mới; 88 ở mới→cũ), cộng 1 trường hợp lãnh thổ rời hẳn (mới→cũ). Không có cặp nào thuộc `SAME_SCOPE` (mọi cặp Data 07 đều qua sáp nhập).

## 8. Phân tích đồ thị toàn bộ edges.csv (cận cấu trúc, không phải accuracy quan sát)

| Chỉ số | Giá trị |
|---|---|
| Cạnh nguyên tử; đơn vị cũ; đơn vị mới | 10.597; 10.035; 3.316 |
| Quan hệ (cạnh): B / M / C / A | 9.432 / 1.030 / 132 / 3 |
| Chuyển đổi phi nguyên tử (báo riêng, `NON_ATOMIC`) | 5 huyện đảo → đặc khu |
| Fan-out cũ→mới theo khóa cũ (1/2/3/4/5 đích) | 9.564 / 397 / 58 / 15 / 1 |
| Fan-in mới→cũ theo khóa mới (1/2/3/4/5 / … / 15 nguồn) | 135 / 756 / 1.499 / 566 / 181 / … / 1; trung bình 3,20, trung vị 3, tối đa 15 |
| Khóa giải được tất định: cũ→mới | 9.564/10.035 = **95,3%** |
| Khóa giải được tất định: mới→cũ | 135/3.316 = **4,1%** |
| Trần accuracy của luật chọn một đích cố định mỗi khóa (trên cạnh lấy đều) | cũ→mới 94,7%; mới→cũ **31,3%** |
| Fan-out theo quan hệ | A: 3 cạnh, fan-out 2; B: toàn bộ fan-out 1; C: 1; M: fan-out 2/3/4/5 = 791 / 174 / 60 / 5 |

Một-nhiều thật sự gần như hoàn toàn nằm ở M (1.030 cạnh), không phải A (3 cạnh): đúng như F2, không ép M thành A.

## 9. Phân tích bất đối xứng — giả thuyết đề cương "chiều mới→cũ khó hơn"

Giả thuyết **được ủng hộ mạnh** và nhất quán ở cả ba nguồn bằng chứng: (i) Data 07, mọi hệ thống tra bảng giảm 0,41–0,92 điểm accuracy (E3, CI cụm khoảng [0,6; 0,98] cho hai heuristic mặc định, không chứa 0); (ii) lỗi im lặng của heuristic mặc định tăng từ 3,5–4,5% lên 92–96%; (iii) đồ thị: chỉ 4,1% khóa mới giải được tất định so với 95,3% khóa cũ, trần của luật chọn cố định là 31,3% so với 94,7%.

Cách hiểu đúng: đây là **tính bất định cấu trúc, không phải độ khó của mô hình hay của chuẩn hóa tên**. Phía mới khớp 600/600 ở mọi mức chuẩn hóa, STRICT luôn abstain đúng (600/600 AMBIGUOUS, 0 lỗi im lặng), và ngay cả luật tốt nhất mỗi đơn vị trên Data 07 cũng chỉ đạt 0,742 (B 0,635; M 0,899) ở chiều mới→cũ so với 1,000 chiều cũ→mới. Một phường mới nhận đất từ trung bình 3,2 (tối đa 15) phường cũ; từ tên phường mới không thể suy ra phường cũ nếu thiếu bằng chứng thêm (số nhà, tên đường, tọa độ). Vì vậy kết quả "lỗi im lặng 92–96%" của heuristic mặc định chiều ngược phản ánh việc *ép chọn một* trong nhiều ứng viên chứ không phải lỗi tra cứu, và thiết kế đúng ở chiều này là trả danh sách ứng viên hoặc abstain. Kết luận về nguyên nhân ("do cấu trúc N-1") là suy luận từ số đo ở (i)–(iii); mức đóng góp riêng của từng yếu tố không được tách bằng thí nghiệm riêng.

Hai chiều chỉ đối xứng ở T2-SINGLE-VERSION (0,087 cả hai chiều, 0 cặp bất đồng) vì hệ này đúng khi và chỉ khi tên phường không đổi; chiều mới→cũ lại có lỗi im lặng cao hơn nhiều (14,8% so với 1,3%).

## 10. Giới hạn

- **F1 — support:** Data 07 chỉ có B (244) và M (356); A và C `NOT_EVALUABLE_NO_SUPPORT`. Chỉ 23 mã phường mới và 49 đơn vị cũ chuẩn hóa (69 chuỗi thô), 441/600 ở Hà Nội; một đơn vị cũ chiếm 299 cặp (49,8% tổng; 84% số cặp M), một phường mới chiếm 350 cặp (58%) và 328/356 cặp M. CI cụm vì vậy rộng, và lát cắt M chỉ có 10 cụm (cũ→mới) hoặc 5 cụm (mới→cũ). Mỗi đơn vị cũ trong Data 07 chỉ có đúng một đích quan sát (trần luật hằng-số-theo-đơn-vị = 1,000), nên Data 07 không đo được việc *cùng một đơn vị cũ đi về các đích khác nhau tùy địa chỉ*; đó là lý do mọi heuristic mặc định trông tốt hơn thực tế.
- **F2 — A thuần gần như không tồn tại (3 cạnh):** "một cũ → nhiều mới" thực tế là M; không gộp M vào A.
- **F3 — tính vòng lặp:** Data 07 được xác minh bằng chính CSV nguồn của edges.csv. Với N2, candidate-recall = 100% *do cấu trúc*; phần còn lại của accuracy đo việc chọn đúng ứng viên, không đo độ phủ của bảng. Hệ quả: accuracy cũ→mới 0,95–0,97 của các heuristic không nói rằng bảng "đúng 96%" trên địa chỉ ngoài Data 07.
- **Gazetteer:** mã cũ còn *partial* (2.187 mã cũ chưa xác minh); hai bản chụp 30/06 và 01/07/2025 không là lịch sử khoảng pháp lý; terms tái phân phối CSV nguồn chưa rõ nên gazetteer giữ local. T2-LOOKUP tra bằng tên nên không phụ thuộc mã cũ.
- **Chuẩn hóa:** N2 chỉ dùng alias đã kiểm chứng; 26 chuỗi OSM cũ khác nhau cần alias. Alias có thể che khuất lỗi gắn nhầm tỉnh/huyện (gold luôn có cạnh khớp 600/600, nên không phát hiện alias sai thông qua gold).
- **T2-VNADMIN** chạy với geocoder bị tắt (stub trả `None`, không socket nào được mở, có test): nó đo nhánh *mặc định* của thư viện, không phải khả năng định vị không gian đầy đủ của thư viện.
- **T2-SINGLE-VERSION** khớp tên phường *có kèm loại đơn vị* (Phường/Xã/Thị trấn) trong tỉnh đích; nếu bỏ loại đơn vị để khớp, số lỗi im lặng sẽ khác (không chạy).
- **T2-STREET:** xem mục 6 (rò rỉ hàng xóm, 162/600 = 27% chuỗi có tên đường chưa xuất hiện trong chỉ mục L2).
- **Pipeline:** chỉ HEUR-JW và CRF-INDEP; neural không chạy trong gói này.

## 11. Điểm suy luận thay vì đo, và thay đổi sau lần chạy thử

Suy luận (không đo trực tiếp): kết luận về nguyên nhân cấu trúc của bất đối xứng (mục 9); mức rò rỉ hàng xóm còn lại của T2-STREET; việc alias không che lỗi.

Hai quyết định thiết kế được chọn sau một lần chạy thử (dev, B = 200, ghi ở thư mục tạm, không dùng làm kết quả), cả hai nhằm tuân thủ quy tắc đã khai báo chứ không làm đẹp số:
1. **Lọc L2 của T2-STREET:** ban đầu so cặp (số nhà, tên đường) bằng chuỗi thô, trong khi chỉ mục dùng `street_key` (bỏ "Đường/Phố"), nên "Phố X" lọt qua "X". Sửa để L2 dùng cùng `street_key`. Hệ quả: tỷ lệ bằng chứng quyết định của L2 giảm từ 62% xuống 42% và accuracy STREET-L2 giảm (1,000 → 0,993/0,992), tức sửa làm kết quả *kém thuận lợi hơn* cho STREET. L1 không đổi.
2. **Gold C3:** chuyển sang định nghĩa "khóa cũ đầy đủ có đúng một đích" để khớp 59 + 1 loại như kế hoạch (bản đầu dùng tỉnh làm ký tự thay thế và không loại dòng nào).

## 12. Tái lập

```bash
cd /mnt/d/DACN && source ~/.venv_dacn/bin/activate
python -m scripts.66_run_t2_baseline --out-dir data/processed/evaluation/sprint04/t2_baseline_20261014_v1   # thư mục phải chưa tồn tại; nếu có thì dùng _v2
python -m unittest tests.test_t2_baseline -v
python -m unittest discover -s tests
```

Script chạy ~42 giây. Đã chạy lại từ đầu vào một thư mục khác: 23 file kết quả (`predictions.jsonl`, `metrics.json`, `graph_analysis.json`, 17 bảng CSV, span của mô hình) **trùng SHA-256 từng byte**; chỉ `run_manifest.json` khác ở thời điểm. `--skip-pipeline` / `--skip-street` ghi tầng 3 là `NOT_RUN`.

Đầu ra: `predictions.jsonl` (27.000 dòng, khóa duy nhất), `metrics.json`, `graph_analysis.json`, `run_manifest.json`, `tables/*.csv` (17 bảng, utf-8-sig, không dòng trùng), `pipeline/` (đầu vào chỉ gồm khóa mờ và văn bản, span HEUR-JW và CRF-INDEP).
