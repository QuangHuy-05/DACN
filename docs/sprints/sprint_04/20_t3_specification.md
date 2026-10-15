# 20. Đặc tả T3 — đối sánh hai địa chỉ qua ranh giới thời gian hành chính

**Ngày:** 15/10/2026 (bản sửa theo review `reviews/review_g3_2_20261015.md`). **Phạm vi:** theo đề cương mục 6, ĐACN chỉ thiết kế và đặc tả T3; hiện thực dành cho ĐATN. Tài liệu này **không** hiện thực hệ thống T3, không huấn luyện, không dựng tập dữ liệu mới. "Qua thời gian" ở đây nghĩa là **qua đúng một ranh giới, 01/07/2025** (hai thời điểm: trước và sau); không mô hình hóa nhiều thời điểm hay khoảng hiệu lực. Số đo tái lập bằng `python -m scripts.75_t3_spec_examples` (chỉ đọc; đầu ra JSON; kiểm bằng `tests/test_t3_spec_examples.py`). Số lấy từ báo cáo 09, 10, 14 ghi nguồn; số mới do script đo. Mọi điều không đo được ghi **"giả định"** hoặc **"ước lượng"**.

## 1. Định nghĩa bài toán

**Đầu vào:** hai chuỗi địa chỉ `a`, `b` (mỗi chuỗi có thể kèm mốc thời gian `t_a`, `t_b`, tùy chọn), viết theo hệ cũ, mới hoặc lai.

**Đầu ra (bốn giá trị, một định nghĩa duy nhất dùng xuyên suốt tài liệu):**

| Nhãn | Nghĩa |
|---|---|
| `SAME_PLACE` | cùng phần tử vật lý, và bằng chứng lãnh thổ *kéo theo* điều đó (mọi cặp giả thuyết lãnh thổ chồng lấn độc quyền) |
| `SAME_CONDITIONAL` | cùng phần tử là kết luận *nhất quán* nhưng còn phụ thuộc điều kiện: lãnh thổ chỉ chồng lấn chung (M-N) nên cần giả định A-UNIQ; kèm danh sách điều kiện |
| `DIFFERENT_PLACE` | chứng minh được khác nhau (phần tử khác, hoặc lãnh thổ rời nhau) |
| `UNDETERMINED` | không đủ thông tin để kết luận ba nhãn trên |

Mỗi đầu ra kèm `reason_codes` truy vết được (span T0, hệ T1, tập ứng viên T2, quy tắc đã dùng). Có thể thêm điểm tin cậy; quyết định bốn nhãn vẫn là đầu ra chính (có thể gộp `SAME_CONDITIONAL` vào `SAME` khi báo, kèm cờ).

**"Cùng một địa điểm qua cải cách":** hai chuỗi chỉ cùng một phần tử vật lý (một số nhà trên một đường, hoặc công trình có tên) mà lãnh thổ hành chính chứa phần tử ở hai hệ chồng lấn nhau. Địa chỉ chỉ tới đơn vị hành chính (không có số nhà/đường hoặc công trình) là **vùng**, không phải điểm: hai vùng chỉ chứng minh được là khác nhau khi rời nhau; không bao giờ `SAME_PLACE`.

**Khác T2:** T2 ánh xạ *một đơn vị* sang hệ kia (đầu ra là tập ứng viên). T3 so *hai chuỗi* và phải xét thêm số nhà/đường; T3 có thể kết luận `SAME_CONDITIONAL` khi T2 còn nhiều ứng viên, vì chỉ cần kiểm chồng lấn, không cần chọn một đích.

**Giả định nền (đều không đo được):** (A-TRUTH) mỗi chuỗi mô tả trung thực một phần tử; (A-DISTINCT) hai cặp (số nhà, tên đường) đã chuẩn hóa khác nhau là hai phần tử khác nhau; (A-UNIQ) một cặp (số nhà, tên đường) xác định tối đa một phần tử trong các vùng chồng lấn. A-DISTINCT sai khi một đường có nhiều cách viết (alias); A-UNIQ sai với số nhà trùng ở đường dài.

## 2. T0, T1, T2 làm thành phần

```
a, b ──T0──► spans (SoNha, TenDuong, PhuongXa, QuanHuyen, TinhThanh, ToaNha…)
      ──T1──► hệ ∈ {cu, moi, Lai, khong_ro}
      ──T2──► tập đơn vị giả thuyết U(a), U(b) + quan hệ chồng lấn O(u,v)
      ──so sánh──► (i) phần tử: cặp (số nhà, đường) bằng / khác / thiếu
                   (ii) lãnh thổ: DISJOINT / EXCLUSIVE / SHARED cho từng cặp (u,v)
      ──luật──► nhãn + reason_codes
```

**Giao diện:** T0 trả span có offset; T1 trả hệ (không dùng gold); T2 (`T2Table`) trả đơn vị và danh sách ứng viên, lý do `NO_MATCH`/`AMBIGUOUS`/`NON_ATOMIC`. `U(x)` là tập đơn vị trong *hệ của chính địa chỉ x* (thường một phần tử; nhiều hơn khi T1 là `Lai`/`khong_ro`, tên phường trùng ở cả hai hệ — tình huống D — hoặc thiếu cấp). **Chồng lấn** `O(u,v)`: cùng hệ → cùng đơn vị là `EXCLUSIVE`, khác đơn vị là `DISJOINT`; khác hệ → không có cạnh trong `edges.csv` là `DISJOINT`; có cạnh và đơn vị cũ chỉ có một đích (quan hệ B hoặc C) là `EXCLUSIVE` (toàn bộ đơn vị cũ nằm trong đơn vị mới); có cạnh và đơn vị cũ có ≥ 2 đích (M, A) là `SHARED` (phần tử có thể nằm ở đích khác). Phần tử so bằng `street_key` và số nhà chuẩn hóa. Một địa chỉ là **điểm** khi có số nhà + tên đường (hoặc tên công trình + đường); chỉ có đường thì không phải điểm.

**Luật quyết định (khai báo, thứ tự ưu tiên):**
1. Cả hai là điểm và phần tử khác nhau theo quy tắc an toàn (khác đường, hoặc cùng đường và hai số nhà có mặt, khác nhau) → `DIFFERENT_PLACE`.
2. Mọi cặp `(u,v) ∈ U(a)×U(b)` là `DISJOINT` → `DIFFERENT_PLACE`.
3. Cả hai là điểm, phần tử bằng nhau, không cặp nào `DISJOINT`: mọi cặp `EXCLUSIVE` → `SAME_PLACE`; có cặp `SHARED` → `SAME_CONDITIONAL` (điều kiện: A-UNIQ trên phần chồng lấn; đích T2 không được chọn).
4. Còn lại → `UNDETERMINED` (mã lý do: `NOT_POINT_LEVEL`, `WARD_MISSING`, `FRAME_AMBIGUOUS` khi một số nhưng không phải mọi cặp `DISJOINT`, `PARTIAL_OVERLAP`, `NO_MATCH`).

**Lan truyền bất định:**

| Nguồn | Xử lý |
|---|---|
| T1 `Lai`/`khong_ro`, tên phường có ở cả hai hệ (tình huống D) | giữ giả thuyết của cả hai hệ trong `U(x)`; luật 2–4 chỉ kết luận khi mọi cặp cùng hướng, nếu không `FRAME_AMBIGUOUS` |
| T2 nhiều ứng viên (M-N, N-1 theo chiều mới→cũ) | không chọn đích mặc định; nhiều ứng viên chỉ làm cặp thành `SHARED` |
| Lỗi im lặng của T2 (luật mặc định chọn sai) | cấm dùng luật mặc định làm bước quyết định; chỉ dùng như baseline đối chứng |
| T0 thiếu/sai span hành chính | thiếu cấp → `U(x)` rộng hơn → thường `UNDETERMINED`; span sai không phát hiện được → lỗi im lặng, đo ở mục 4 |
| Mốc thời gian | chỉ là tiên nghiệm để phá hòa giữa hai hệ ở tình huống D, không ghi đè bằng chứng span (giả định: ngày ghi không đảm bảo hệ viết); dữ liệu Data 07 có mốc "trước/sau" theo cấu tạo, nên mốc phải có cờ ablation để không rò rỉ nhãn hệ |

## 3. Dữ liệu đánh giá

**Cặp dương (Data 07, đo bằng script):** 600 cặp (M 356, B 244); 49 đơn vị cũ chuẩn hóa, 23 mã phường mới, 21 nhóm `admin_group_key`; cả 600 cặp có số nhà và tên đường **không đổi** (head giống nhau 600/600) và có cạnh tương ứng trong gazetteer (600/600, nên "tồn tại cạnh" luôn đúng — tính vòng lặp, báo cáo 09 F3). Hàng B là đúng các hàng có đơn vị cũ một đích. **Data 07 không có cặp âm, không có A và C.**

**Hai lớp nhãn:** `gold_decision` (điều một hệ lý tưởng được phép kết luận từ đúng thông tin trong hai chuỗi) dùng để chấm; `latent_truth` (từ nguồn gốc cặp) chỉ để chẩn đoán "đoán may".

**Hàm `gold_decision` (bảng quyết định, chỉ dùng đặc trưng văn bản + gazetteer, oracle span; hiện thực hàm là việc của ĐATN):**

| Đặc trưng của cặp (a, b) | `gold_decision` |
|---|---|
| cả hai điểm, phần tử khác nhau (A-DISTINCT) | `DIFFERENT_PLACE` (bất kể lãnh thổ) |
| mọi cặp đơn vị còn lại sau khi suy giảm đều `DISJOINT` (cần tối thiểu tỉnh phân giải được ở cả hai phía) | `DIFFERENT_PLACE`, kể cả khi đã bỏ phường, bỏ số nhà hoặc bỏ phần đầu |
| cả hai điểm, phần tử bằng, mọi cặp `EXCLUSIVE` | `SAME_PLACE` |
| cả hai điểm, phần tử bằng, có cặp `SHARED`, không cặp `DISJOINT` | `SAME_CONDITIONAL` |
| một phía không phải điểm (chỉ đường hoặc vùng) và còn cặp chồng lấn | `UNDETERMINED` |
| thiếu phường ở một phía, đơn vị còn lại không rời hẳn | `UNDETERMINED` |
| `Lai`/`khong_ro` mà các giả thuyết hệ cho kết luận khác nhau | `UNDETERMINED` |

**Phân bố cặp dương theo `gold_decision` (script, theo đặc trưng số nhà và số đích; không chạy luật trên văn bản):** `SAME_PLACE` 182 (B có số nhà), `SAME_CONDITIONAL` 349 (M có số nhà), `UNDETERMINED` 69 (chỉ có đường: 62 B, 7 M), tổng 600. Nhãn tiềm ẩn của 69 dòng này vẫn là cùng phần tử, nhưng theo luật không kết luận được. Vì vậy ba tầng (B / M / chỉ-đường) luôn báo riêng, không gộp.

**Quy tắc dựng cặp âm (từ dữ liệu có sẵn; số do script đo):**

| Loại | Dựng | Cơ sở nhãn | Sức chứa đo được | Rủi ro |
|---|---|---|---|---|
| N-A cùng phường mới, khác phần tử | `a` = địa chỉ cũ dòng i, `b` = địa chỉ mới dòng j, cùng `MaPhuongXaMoi`, phần tử khác theo quy tắc an toàn | A-DISTINCT | 134.732 cặp có thứ tự (đường khác 125.372; cùng đường khác số 9.360; cùng đơn vị cũ 93.834); 204 cặp cùng đường thiếu số bị loại; ≤ 2 mỗi neo: 1.176 | 96,5% cặp nằm trong một nhóm (Hà Nội–Ba Đình); chỉ 11/21 nhóm có cặp; nhãn trùng với phép so sánh của luật nên luật chính xác đạt 100% theo cấu tạo |
| N-B hoán lãnh thổ | giữ phần tử dòng i, thay phường đích bằng đơn vị mới không có cạnh từ đơn vị cũ của i | rời nhau là điều chứng minh được | 3.312–3.315 ứng viên mỗi neo (3.316 đơn vị mới); ≤ 2 mỗi neo: 1.200 | văn bản tổng hợp (đường có thể không tồn tại ở nơi đó): nhãn đúng về logic lãnh thổ, không là địa chỉ thật |
| N-B2 trùng tên phường khác tỉnh | thay đơn vị cũ bằng đơn vị cùng tên phường ở tỉnh cũ khác | rời nhau theo tỉnh | 351 neo, 12 đơn vị cũ, 415 hoán; phía mới chỉ 1 dòng (Diên Hồng, TP.HCM / Gia Lai) | cụm ít; một neo mới duy nhất |
| N-C trùng tên cùng tỉnh, khác lãnh thổ (mức vùng) | cặp (đơn vị cũ, đơn vị mới cùng tên) không có cạnh | rời nhau | 1.989 cặp trùng tên; 1.832 có cạnh; **157 không cạnh**; neo Data 07: 0 | chỉ mức vùng, không có phần tử thật |
| **KHÔNG dựng**: đích hợp lệ khác của cùng đơn vị cũ | đổi phường đích sang đích khác trong fan-out (956 hoán trên 356 dòng M) | — | — | văn bản giống hệt một cặp dương hợp lệ khác; nhãn `DIFFERENT` không suy ra được từ văn bản, cần hình học/tọa độ ranh giới (chưa có) |

**Cặp UNDETERMINED hoặc DIFFERENT từ "bản sinh đôi suy giảm":** từ cặp dương hoặc âm bỏ số nhà (531 dòng đủ điều kiện), bỏ phường một phía, hoặc bỏ phần đầu (600 dòng); nhãn gold tính bằng bảng quyết định ở trên (không mặc định `UNDETERMINED`: nếu lãnh thổ còn lại vẫn rời nhau thì là `DIFFERENT_PLACE`); giữ `latent_truth` của cặp gốc để đo "đoán may". Tỷ lệ trộn các nhãn là **giả định** (đề xuất cân bằng theo từng tầng, báo theo tầng, không báo một accuracy gộp).

**Chia nhóm và rò rỉ:** dùng `leak_guard.admin_group_key`; cặp âm được dựng *sau* khi chia, cả hai địa chỉ thuộc cùng phân vùng. Data 07 có 21 nhóm, nhóm lớn nhất 441/600 (73,5%), ba nhóm đầu 87,5%: không chia 60/20/20 được; đề xuất leave-one-group-out hoặc giữ nhóm Hà Nội–Ba Đình làm một phần riêng. Cụm ít, CI rộng (báo cáo 14 mục d.3). Mở rộng nguồn thuộc phạm vi báo cáo khả thi G2-6 và ĐATN, không thuộc tài liệu này.

## 4. Metric

Không báo một accuracy gộp. Báo theo từng tầng gold (`SAME_PLACE`, `SAME_CONDITIONAL`, `DIFFERENT_PLACE`, `UNDETERMINED`), mỗi tỷ lệ kèm mẫu số:
- **Khớp nhầm**: dự đoán `SAME_*` khi gold `DIFFERENT_PLACE`. **Tách nhầm**: dự đoán `DIFFERENT_PLACE` khi gold `SAME_PLACE` hoặc `SAME_CONDITIONAL` (báo hai tầng riêng; tầng M tách khỏi tầng B). **Cam kết quá mức**: cam kết (`SAME_*`/`DIFFERENT_PLACE`) khi gold `UNDETERMINED`, và dự đoán `SAME_PLACE` khi gold `SAME_CONDITIONAL` (khẳng định mạnh hơn bằng chứng cho phép). **Hạ mức** (không tính là lỗi im lặng): dự đoán `SAME_CONDITIONAL` khi gold `SAME_PLACE`.
- **Lỗi im lặng** = cam kết sai / N; **coverage** = cam kết / N; **abstain thừa** = `UNDETERMINED` khi gold quyết định được.
- CI bootstrap theo cụm `admin_group_key` (`src/evaluation/stats.py`); tầng có < 20 cụm gắn `FEW_CLUSTERS` (ngưỡng 20 là **giả định**, chọn trước); báo thêm kết quả bỏ nhóm lớn nhất.
- Phân tầng riêng: N-1 (B) và M-N (M) (`LoaiAnhXa`), `HinhThucSapNhap`, hướng cũ→mới / mới→cũ, tình huống D.
- **Không đo được bằng Data 07:** A và C (`NOT_EVALUABLE_NO_SUPPORT`), đích phụ thuộc tên đường (mỗi đơn vị cũ một đích, E2 INCONCLUSIVE), `Lai` do người viết, mốc/công trình (support 0), nhãn M-N khi cần hình học.

## 5. Ví dụ (số từ script; verdict áp dụng tay theo mục 2)

**V1 — N-1, khớp** (CSV dòng 3, `node:11675985421`, B): `12C, Phố Hàng Cót, Phường Hàng Mã, Quận Hoàn Kiếm, Hà Nội` / `12C, Phố Hàng Cót, Phường Hoàn Kiếm, Thành phố Hà Nội`. Phần tử bằng (12c, hàng cót); cạnh Hàng Mã→Hoàn Kiếm có, đơn vị cũ một đích → `EXCLUSIVE` → **SAME_PLACE** (luật 3).

**V2 — M-N** (dòng 58, `way:1301699235`, M, "Tách — một phần"): `11, Phố Ngọc Hà, Phường Đội Cấn, Quận Ba Đình` / `11, Phố Ngọc Hà, Phường Ba Đình`. `U(a) = {Đội Cấn}`, `U(b) = {Ba Đình}`; có cạnh, nhưng Đội Cấn có hai đích {Ba Đình, Ngọc Hà} → `SHARED`; phần tử bằng → **SAME_CONDITIONAL** (luật 3; điều kiện A-UNIQ). Luật mặc định T2 chọn Ngọc Hà → baseline chiếu-rồi-so báo `DIFFERENT_PLACE` sai (một trong 21 lỗi im lặng cũ→mới): đây là loại lỗi tầng M. Phiên bản vùng (bỏ số nhà/đường: `Phường Đội Cấn, Quận Ba Đình` / `Phường Ba Đình`) → không phải điểm, còn chồng lấn → **UNDETERMINED** (`NOT_POINT_LEVEL`, `PARTIAL_OVERLAP`); đây là cặp suy giảm, không phải dòng Data 07.

**V3 — lỗi im lặng T2 mới→cũ** (dòng 7, `way:1370501880`, B): `33, Đường Nguyễn Đăng Đạo, Phường Suối Hoa, Thành phố Bắc Ninh` / `…Phường Kinh Bắc, Tỉnh Bắc Ninh`. Chiếu mới→cũ có 6 ứng viên, mặc định chọn Phường Hòa Long, gold là Suối Hoa → baseline chiếu-rồi-so báo `DIFFERENT_PLACE` sai, không cảnh báo; luật T3 cho **SAME_PLACE** (đơn vị cũ một đích). Dòng 3 (V1) cũng sai ở chiều này (14 ứng viên, chọn Hàng Buồm).

**V4 — cặp âm khó N-A** (`way:565803559` dòng 5 và `node:11290270603` dòng 6, cùng phường 00004): `a` = `8, Phố Khúc Hạo, Phường Điện Biên, Quận Ba Đình` (cũ, từ `DiaChi_Cu` dòng 5), `b` = `10, Phố Khúc Hạo, Phường Ba Đình, Thành phố Hà Nội` (mới, từ `DiaChi_Moi` dòng 6). Lãnh thổ chồng lấn, cùng đường, số nhà 8 ≠ 10 → **DIFFERENT_PLACE** (luật 1). Baseline chỉ so lãnh thổ sẽ báo `SAME`.

**V5 — trùng tên phường hai tỉnh** (dòng 95, `way:849287352`): `a` = `DiaChi_Moi` dòng 95 = `451, Tô Hiến Thành, Phường Diên Hồng, Thành phố Hồ Chí Minh` (dòng gốc là cặp cũ–mới; ở đây chỉ dùng phía mới); `b` = cùng chuỗi nhưng `Phường Diên Hồng, Tỉnh Gia Lai` (dựng, loại N-B2, cặp mới–mới). Tên phường giống hệt, tỉnh khác, đơn vị Gia Lai không là đích của đơn vị cũ → rời nhau → **DIFFERENT_PLACE** (luật 2). Độ tương tự chuỗi cao nhưng khác địa điểm.

**Hành vi baseline trên 600 cặp dương (dẫn xuất từ báo cáo 09, đã tái lập; 95,3% khóa cũ so với 4,1% khóa mới giải tất định, báo cáo 14 mục c.1):** chiếu cũ→mới bằng DEFAULT-MAIN rồi so: khớp 579, tách nhầm 21 (3,5%); chiếu mới→cũ: khớp 46, tách nhầm 554 (92,3%); STRICT cũ→mới: khớp 244, abstain 356; STRICT mới→cũ: abstain 600; chỉ kiểm cạnh: 600 khớp (rỗng về thông tin vì 600/600 cạnh tồn tại theo cấu tạo). Cặp dương đơn thuần không phân biệt được các hệ; sức phân biệt đến từ cặp âm và các tầng `UNDETERMINED`. Với span từ mô hình, T1-PIPE đạt 0,969 trên test 64 eligible (`Lai` support 5, mọi số `Lai` là `LOW_SUPPORT`, báo cáo 14 mục b2).

## 6. Kế hoạch đánh giá cho ĐATN

**Baseline:** B0 so chuỗi chuẩn hóa; B1 luật mục 2 với span oracle; B2 như B1 với span dự đoán (HEUR-JW, CRF-INDEP, PhoBERT-CRF); B3 chiếu rồi so, hai chiều, STRICT và DEFAULT-MAIN; B4 `vietnamadminunits` chuyển cũ→mới rồi so chuỗi; B5 tương tự chuỗi (Jaro–Winkler) làm cận dưới.

**Giả thuyết kiểm được (đặt trước):** (T3-1) B3 DEFAULT-MAIN có tỷ lệ tách nhầm bất đối xứng theo hướng, khớp 21/600 và 554/600 ở trên (kiểm nhất quán, không phải bằng chứng mới). (T3-2) luật chỉ-lãnh-thổ có tỷ lệ khớp nhầm 100% trên N-A, luật có phần tử thì 0 với span oracle (theo cấu tạo), nên điểm chính là độ nhạy với span T0 dự đoán (**giả định**: lỗi SoNha/TenDuong làm tăng lỗi im lặng); sau khi tách tầng, giả thuyết được kiểm riêng ở tầng B (182, kết luận không điều kiện) và tầng M (349, `SAME_CONDITIONAL`), vì tầng M chỉ nhận kết luận có điều kiện nên "đúng" ở tầng M không cùng nghĩa với tầng B. (T3-3) giữ giả thuyết của cả hai hệ (thay vì chọn một hệ theo T1) giảm lỗi im lặng ở tình huống D, đổi lấy coverage; kiểm được ở cả hai tầng nhưng phép đếm `FRAME_AMBIGUOUS` phải báo riêng cho B và M. (T3-4) chính sách `UNDETERMINED` giảm cam kết quá mức. Kết quả âm là hợp lệ.

**Điều kiện dừng (giả định, chọn trước):** dừng báo kết luận cho một tầng khi < 20 cụm hoặc support < 30; kiểm tay 100 cặp dựng ngẫu nhiên (do chủ dự án, không phải agent), dừng nếu đồng thuận nhãn < 95%; không tinh chỉnh luật sau khi thấy test.

**Cần thêm:** gazetteer có khoảng hiệu lực pháp lý (hiện chỉ hai bản chụp 30/06 và 01/07/2025, mã cũ 2.187 chưa xác minh); dữ liệu `Lai` do người viết (T1 `Lai` support 5, tập lai cùng một generator); mốc thời gian thực; hình học/ranh giới để phân định M-N; thêm cặp ngoài ba thành phố của Data 07; cạnh A và C (gazetteer chỉ 3 và 132 cạnh).

## 7. Phạm vi và rủi ro

Đặc tả **không hứa**: kết quả định lượng nào của T3; xử lý đúng khi A-DISTINCT/A-UNIQ sai; quyết định M-N không điều kiện khi thiếu hình học (chỉ `SAME_CONDITIONAL`); xử lý địa chỉ chỉ có đường (đường như một địa điểm); tổng quát sang địa chỉ lai thật; hiệu quả của tầng 2 LLM/RAG; nhiều thời điểm ngoài ranh giới 01/07/2025. Rủi ro chính: (1) tính vòng lặp của Data 07 và nhãn N-A trùng luật so sánh, nên 100% theo cấu tạo là giả; (2) cụm ít, một nhóm chiếm 73,5% dòng dương và 96,5% cặp N-A; (3) cặp N-B tổng hợp có thể lạ so với địa chỉ thật; (4) nhãn `UNDETERMINED`/`SAME_CONDITIONAL` định nghĩa theo bảng quyết định của đặc tả, không phải chân lý khách quan; (5) tỷ lệ trộn nhãn là giả định. Nguồn số: báo cáo 09 (§3, §7.2, §8–10), 10 (§6), 14 (§b2, §b3, §c, §d); số mới: `scripts/75_t3_spec_examples.py`.

## Tái lập

Đầu vào đo: gazetteer `data/processed/gazetteer/s3_v4_nso_dual_snapshot_release2` (`manifest.json` SHA-256 `35e42cff0d220121d0e6c8c815451ff6081369a74ca8dbca5cbb84ef61159d5e`), Data 07 `data/processed/benchmark/07_bidirectional_pairs_verified.csv` (SHA-256 `3f11b0d02a05922662613c460014da34f89def7da1e7e1ba6ef496aa369245fc`). Script ghi các hash này vào mục `inputs` của đầu ra.

```bash
cd /mnt/d/DACN && source ~/.venv_dacn/bin/activate
python -m scripts.75_t3_spec_examples                       # JSON ra stdout
python -m scripts.75_t3_spec_examples --out <file_moi.json>  # từ chối ghi đè
python -m unittest tests.test_t3_spec_examples -v
```
