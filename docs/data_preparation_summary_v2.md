# Báo cáo Kiểm toán và Phương pháp Chuẩn bị Dữ liệu (v2)
## Vietnamese Address Benchmark (DACN) — Cải cách Hành chính 2025

- **Ngày lập:** 20/09/2026
- **Tác giả:** Senior AI Engineer (Kiểm toán Dữ liệu & Đánh giá Độc lập)
- **Phiên bản:** v2.0 (Đóng băng theo `docs/VERSIONING.md`)
- **Khóa run manifest:** `data/processed/evaluation/run_manifest.json` (Phiên bản 2.0, Freeze: `2026-09-19T14:48:18.462853+00:00`)
- **Môi trường:** Python 3.14.4, pandas 2.3.3, pyarrow 23.0.1, osmium 4.3.1, tqdm 4.70.1 (WSL Ubuntu)

---

## 1. Tổng quan và Mục đích Báo cáo

Báo cáo này tài liệu hóa chi tiết quá trình kiểm toán thực nghiệm, phương pháp trích xuất dữ liệu lịch sử OpenStreetMap (OSM) và kiểm định chất lượng 3 tập dữ liệu chuyên đề (Data 04, Data 06, Data 07) phục vụ xây dựng bộ benchmark địa chỉ tiếng Việt cho đề tài DACN.

Mục tiêu kiểm toán bao gồm:
1. Xác minh tính toàn vẹn và nguồn gốc của tệp full-history OSM `vietnam-internal.osh.pbf`.
2. Kiểm chứng quy trình lọc thời gian (time-filter) tại mốc cắt quyết định $t_0 =$ **30/06/2025 23:59:59 UTC**, đánh giá độ phủ tag `addr:*`, đo lường tỷ lệ dữ liệu sạch/thiếu trường.
3. Kiểm tra hợp đồng dữ liệu (data contract) của 3 tập dữ liệu chuyên đề: Data 04 (800 mẫu thiếu trường), Data 06 (600 mẫu địa chỉ lai) và Data 07 (600 cặp ánh xạ hành chính hai chiều).
4. Khẳng định cơ sở khoa học để giữ nguyên trạng thái đóng băng của dữ liệu mà không cần tái sinh ngẫu nhiên.

---

## 2. Phần A: Kiểm toán Nguồn OSM Full-History và Quy trình Lọc Thời gian

### 2.1. Xác minh nguồn dữ liệu gốc `data/raw/osm/`

Tệp dữ liệu thô lịch sử OSM được lưu trữ tại `data/raw/osm/vietnam-internal.osh.pbf`. Theo nguyên tắc tại `AGENTS.md`, thư mục `data/raw/` là bất biến và không được can thiệp trực tiếp.

Kết quả kiểm tra băm mật mã và siêu dữ liệu tệp:
- **Tên tệp:** `vietnam-internal.osh.pbf`
- **Kích thước byte:** $756.709.921$ bytes ($\approx 721{,}65$ MB)
- **Mã băm SHA-256:** `3371669670769e224b3ab0c37992e4d0500bdc0bbab4c03d7833238fbcb300da`
- **Định dạng:** OSM Full-History Protocolbuffer Binary Format (`.osh.pbf`), chứa đầy đủ các phiên bản (versions), mốc thời gian (timestamps), changeset và cờ trạng thái tồn tại (visible/deleted) của mọi thực thể bản đồ tại Việt Nam từ khởi nguyên đến sau thời điểm sáp nhập 2025.

### 2.2. Cơ chế time-filter và Trích xuất Snapshot Lịch sử

Để tái hiện chính xác hiện trạng địa chỉ hệ cũ trước khi Nghị quyết sắp xếp đơn vị hành chính cấp huyện, cấp xã giai đoạn 2023–2025 có hiệu lực vào ngày 01/07/2025, module `src/data/osm_extractor.py` sử dụng thư viện `pyosmium` để duyệt qua từng thực thể với điều kiện lọc thời gian:

$$\text{Timestamp}(v_i) \le \text{2025-06-30T23:59:59Z} \quad \wedge \quad \text{visible} = \text{True}$$

Nếu một thực thể có nhiều phiên bản trước mốc cắt, phiên bản mới nhất thỏa mãn điều kiện thời gian được chọn làm trạng thái của thực thể tại thời điểm chốt sổ.

Kết quả trích xuất được lưu vào `data/interim/osm/osm_old_snapshot_full.csv`:
- **Tổng số bản ghi trích xuất:** $26.961$ thực thể.
  + Số lượng Node: $15.749$ ($15.749 / 26.961 = 58{,}41\%$).
  + Số lượng Way (Đường / Đa giác tòa nhà): $11.212$ ($11.212 / 26.961 = 41{,}59\%$).

### 2.3. Thống kê Phân bố Tag `addr:*` trên tập Node ($N = 15.749$)

Phân tích chất lượng các tag địa chỉ cấu thành trên $15.749$ node hệ cũ thu được kết quả như sau:

| Tag OSM tương ứng | Trường địa chỉ chuẩn hóa | Số lượng có dữ liệu | Tỷ lệ hiện diện |
| :--- | :--- | :---: | :---: |
| `addr:street` | `TenDuong` | $15.749$ | $15.749 / 15.749 = 100{,}00\%$ |
| `addr:city` / `addr:province` | `TinhThanh` | $14.359$ | $14.359 / 15.749 = 91{,}18\%$ |
| `addr:district` / `is_in:district` | `QuanHuyen` | $13.580$ | $13.580 / 15.749 = 86{,}23\%$ |
| `addr:subdistrict` / `addr:ward` | `PhuongXa` | $12.401$ | $12.401 / 15.749 = 78{,}74\%$ |
| `addr:housenumber` | `SoNha` | $9.119$ | $9.119 / 15.749 = 57{,}90\%$ |

Đánh giá mức độ hoàn thiện thông tin cấu trúc (5 trường cơ bản):
- **Số node sạch hoàn chỉnh (đủ cả 5 trường `SoNha`, `TenDuong`, `PhuongXa`, `QuanHuyen`, `TinhThanh`):**
  $$N_{\text{clean}} = 6.008 \quad (6.008 / 15.749 = 38{,}15\%)$$
- **Số node thiếu tự nhiên ($\ge 1$ trường bị khuyết trong OSM thô):**
  $$N_{\text{incomplete}} = 9.741 \quad (9.741 / 15.749 = 61{,}85\%)$$
  *(Trong đó thiếu số nhà chiếm tỷ trọng lớn nhất với $6.630 / 15.749 = 42{,}10\%$).*

### 2.4. Snapshot Cân bằng Vùng miền và Tuyển chọn Benchmark Sạch

Nhằm tránh hiện tượng thiên lệch mật độ tập trung dữ liệu vào các đô thị lớn ở miền Bắc, pipeline thiết lập tệp snapshot cân bằng `data/interim/osm/osm_old_snapshot_20250630.csv` gồm $16.242$ bản ghi:
- **Miền Bắc:** $10.000 / 16.242 = 61{,}57\%$
- **Miền Nam:** $4.925 / 16.242 = 30{,}32\%$
- **Miền Trung:** $1.317 / 16.242 = 8{,}11\%$

Từ snapshot cân bằng này, tập con các địa chỉ hoàn toàn sạch (đủ 5 trường) gồm $8.848$ ứng viên được lọc ra. Tập **Data 03 (`03_real_address_old_1500.csv`)** gồm đúng $1.500$ mẫu được lấy mẫu phân tầng ngẫu nhiên (seed cố định) từ $8.848$ ứng viên này, bảo đảm $1.500 / 1.500 = 100{,}00\%$ mẫu hệ cũ sạch hoàn hảo không chứa lỗi thiếu trường tự nhiên.

### 2.5. Kiểm toán Quy trình Lọc OSM Diff Lịch sử ($N_{\text{diff}} = 1.631$)

Module `scripts/04_audit_osm_diff_filters.py` đã giải trình và kiểm toán từng bản ghi biến đổi địa chỉ giữa hai phiên bản trước và sau sáp nhập trên toàn bộ $1.631$ cặp diff quan sát được:

| Mã trạng thái kiểm toán | Số lượng | Tỷ lệ | Diễn giải lý do giữ / loại bỏ |
| :--- | :---: | :---: | :--- |
| `accepted_observed` | $612$ | $612 / 1.631 = 37{,}52\%$ | Số nhà, tên đường không đổi; đơn vị hành chính cũ và mới khớp hoàn toàn với bảng sáp nhập chuẩn; giữ lại để làm tập ứng viên Data 07. |
| `new_unit_not_found` | $325$ | $325 / 1.631 = 19{,}93\%$ | Đơn vị mới trong OSM không tồn tại trong bảng sáp nhập chuẩn 2025. |
| `missing_old_ward` | $188$ | $188 / 1.631 = 11{,}53\%$ | Bản ghi cũ bị thiếu tag phường/xã, không đủ cơ sở xác định điểm xuất phát. |
| `house_or_street_changed` | $188$ | $188 / 1.631 = 11{,}53\%$ | Số nhà hoặc tên đường bị thay đổi đồng thời (nghi ngờ dời địa điểm vật lý thay vì sáp nhập). |
| `missing_new_ward` | $89$ | $89 / 1.631 = 5{,}46\%$ | Bản ghi mới bị thiếu tag phường/xã. |
| `missing_old_district` | $19$ | $19 / 1.631 = 1{,}16\%$ | Bản ghi cũ thiếu quận/huyện, gây rủi ro nhập nhằng đồng âm. |
| `duplicate_record` | $161$ | $161 / 1.631 = 9{,}87\%$ | Các cặp diff trùng lặp bề mặt chuỗi. |
| `possible_geometry_move` | $14$ | $14 / 1.631 = 0{,}86\%$ | Cạnh chưa xác minh, tọa độ thay đổi đáng kể ($>50$m), loại bỏ. |
| `stationary_unverified_edge` | $35$ | $35 / 1.631 = 2{,}15\%$ | Cạnh chưa xác minh dù tọa độ không đổi, loại bỏ để tránh đoán mò. |
| **Tổng cộng** | **$1.631$** | **$100{,}00\%$** | Toàn bộ quyết định kiểm toán được lưu tại `data/processed/evaluation/osm_diff_filter_audit.csv`. |

Từ $612$ cặp `accepted_observed`, pipeline lấy mẫu phân tầng $600$ cặp cho tập **Data 07**, đạt $600 / 600 = 100{,}00\%$ nguồn gốc quan sát thực tế từ biến đổi lịch sử OSM, $0 / 600 = 0{,}00\%$ suy diễn tĩnh từ snapshot.

---

## 3. Phần B: Kiểm định Chất lượng và Hợp đồng Dữ liệu 3 Tập Chuyên đề

Kiểm tra toàn diện 3 tập benchmark chuyên đề được sinh tự động/lọc trích xuất:

```
Data 04: data/processed/benchmark/04_missing_fields_800.csv
Data 06: data/processed/benchmark/06_hybrid_addresses_600.csv
Data 07: data/processed/benchmark/07_bidirectional_pairs_verified.csv
```

### 3.1. Bảng Tổng hợp Kiểm toán Hợp đồng Dữ liệu (Contract Verification Table)

| Tiêu chí kiểm định | Data 04 (`04_missing_fields_800.csv`) | Data 06 (`06_hybrid_addresses_600.csv`) | Data 07 (`07_bidirectional_pairs_verified.csv`) |
| :--- | :--- | :--- | :--- |
| **Kích thước dòng ($N$)** | Đúng $800$ dòng ($800 / 800 = 100\%$) | Đúng $600$ dòng ($600 / 600 = 100\%$) | Đúng $600$ cặp ($600 / 600 = 100\%$) |
| **Mã băm SHA-256** | `46305aac4821c2f2bc96913cfaf3a89f3087dd91216f5093dc7f89b8541fc021` | `6249b06941d6e89a8a731fc47d0b844ee89ed8dce5a902bfcaac13d2785ced8d` | `3f11b0d02a05922662613c460014da34f89def7da1e7e1ba6ef496aa369245fc` |
| **Encoding chuẩn** | `UTF-8-sig` (khớp hợp đồng) | `UTF-8-sig` (khớp hợp đồng) | `UTF-8-sig` (khớp hợp đồng) |
| **Số chuỗi trùng lặp** | $0 / 800 = 0{,}00\%$ (Duy nhất 100%) | $0 / 600 = 0{,}00\%$ (Duy nhất 100%) | $0 / 600 = 0{,}00\%$ (Duy nhất 100%) |
| **Cột bắt buộc** | `ChuoiDiaChi`, `SoNha`, `TenDuong`, `PhuongXa`, `QuanHuyen`, `TinhThanh`, `GT_*`, `KieuThieu`, `HeQuyChieu` | `ChuoiDiaChi`, `SoNha`, `TenDuong`, `PhuongXa`, `QuanHuyen`, `TinhThanh`, `KieuLai`, `HeQuyChieu`, `Span_He_Detail`, `LoaiAnhXa`, `QuanHe`, `HinhThucSapNhap`, `Nguon` | `ID_Node`, `DiaChi_Cu`, `DiaChi_Moi`, `LoaiAnhXa`, `QuanHe`, `HinhThucSapNhap`, `MaPhuongXaMoi`, `Nguon` |
| **Ground Truth (`GT_*`)** | Đầy đủ $100\%$ ($0$ giá trị null trong các trường gốc cần bảo toàn) | Đầy đủ thông tin nhãn span cho từng cấp | Đối chiếu 2 chuỗi hoàn chỉnh xuôi - ngược |
| **Nguồn gốc dữ liệu** | Sinh có kiểm soát từ Data 01 (hệ mới) và Data 03 (hệ cũ sạch) | Sinh từ đồ thị sáp nhập nguyên tử có xác minh đích | $100\%$ quan sát từ OSM diff thực tế |

---

### 3.2. Phân tích Chi tiết Từng Tập Benchmark Chuyên đề

#### A. Data 04 — Benchmark Địa chỉ Thiếu trường Có kiểm soát ($N = 800$)
- **Mục tiêu:** Đánh giá khả năng bóc tách thực thể khi chuỗi văn bản bị khuyết các thành phần trọng yếu (Task A: Sequence Parsing) và kiểm tra khả năng suy luận phục hồi thông tin hành chính từ ngữ cảnh còn lại (Task B: Contextual Resolution).
- **Phân bố hệ quy chiếu:**
  + Hệ cũ (`cu`): $400 / 800 = 50{,}00\%$
  + Hệ mới (`moi`): $400 / 800 = 50{,}00\%$
- **Phân bố kiểu thiếu (`KieuThieu`):**
  + `drop_housenumber` (Khuyết số nhà): $348 / 800 = 43{,}50\%$ ($146$ mẫu cũ, $202$ mẫu mới).
  + `drop_ward` (Khuyết phường/xã): $241 / 800 = 30{,}12\%$ ($98$ mẫu cũ, $143$ mẫu mới).
  + `drop_housenumber_ward` (Khuyết đồng thời số nhà và phường/xã): $112 / 800 = 14{,}00\%$ ($57$ mẫu cũ, $55$ mẫu mới).
  + `drop_district` (Khuyết quận/huyện): $99 / 800 = 12{,}38\%$ ($99$ mẫu cũ, $0$ mẫu mới vì hệ mới vốn không có cấp quận/huyện).
- **Bảo toàn Ground Truth:** Toàn bộ $800$ dòng đều giữ nguyên vẹn các trường `GT_SoNha`, `GT_TenDuong`, `GT_PhuongXa`, `GT_QuanHuyen`, `GT_TinhThanh` của địa chỉ gốc trước khi áp dụng phép khuyết. Không có hiện tượng khuyết trường ngẫu nhiên ngoài danh mục quy định. Trường `QuanHuyen` rỗng ở $400$ mẫu hệ mới phản ánh chính xác cấu trúc phân cấp hành chính 2 cấp (Tỉnh $\to$ Phường).

#### B. Data 06 — Benchmark Địa chỉ Lai ($N = 600$)
- **Mục tiêu:** Đánh giá khả năng xử lý hiện tượng "chuyển dịch tham chiếu cục bộ" khi người dùng vô tình hoặc cố ý kết hợp các thành phần hành chính cũ và mới trong cùng một chuỗi địa chỉ giao dịch.
- **Phân loại kiểu lai (`KieuLai`):**
  + **Kiểu C1 (Phường cũ + Tỉnh mới, không có quận):** $420 / 600 = 70{,}00\%$. Phản ánh thói quen người dân ghi tên phường cũ quen thuộc nhưng cập nhật tên tỉnh theo địa giới mới, bỏ qua cấp quận bị bãi bỏ.
  + **Kiểu C2 (Phường mới + Quận cũ + Tỉnh mới):** $120 / 600 = 20{,}00\%$. Phản ánh tình huống người dùng cập nhật phường mới nhưng vẫn chèn tên quận cũ theo thói quen định vị không gian.
  + **Kiểu C3 (Phường mới + Tỉnh cũ, không có quận):** $60 / 600 = 10{,}00\%$. Phản ánh việc cập nhật phường mới nhưng giữ nguyên tỉnh cũ.
- **Độ đặc thù:** Toàn bộ $600$ chuỗi địa chỉ là duy nhất tuyệt đối ($0$ bản ghi trùng). Tất cả các cặp thực thể lai đều được kiểm tra đảm bảo có cạnh hợp lệ trên đồ thị hành chính xác minh (`vietnam-sap-nhap-phuong-xa.csv`).

#### C. Data 07 — Benchmark Cặp Ánh xạ Hành chính Hai chiều ($N = 600$)
- **Mục tiêu:** Đánh giá năng lực của các bộ chuyển đổi đơn vị hành chính qua thời điểm cải cách 01/07/2025.
- **Đặc trưng nguồn:** $600 / 600 = 100{,}00\%$ cặp địa chỉ được trích xuất trực tiếp từ biến đổi lịch sử OSM diff (`OSM_Diff+vietnam-sap-nhap-phuong-xa.csv`), trong đó số nhà và tên đường giữ nguyên vẹn qua hai thời kỳ:
  $$\text{SoNha}_{\text{cu}} = \text{SoNha}_{\text{moi}} \quad \wedge \quad \text{TenDuong}_{\text{cu}} = \text{TenDuong}_{\text{moi}}$$
- **Phân bố quan hệ không gian (`QuanHe`):**
  + **Quan hệ $M-N$ (Nhiều xã cũ chia tách và sáp nhập thành nhiều xã mới):** $356 / 600 = 59{,}33\%$. Đây là nhóm quan hệ có độ phức tạp cao nhất, đòi hỏi phân giải ranh giới tọa độ địa lý chi tiết.
  + **Quan hệ $N-1$ (Nhiều xã cũ sáp nhập trọn vẹn vào một xã mới):** $244 / 600 = 40{,}67\%$. Quan hệ xác định đơn ánh xuôi (deterministic forward mapping).
- **Mã định danh:** $600$ node có ID duy nhất ($600 / 600 = 100\%$), có đầy đủ mã phường/xã mới (`MaPhuongXaMoi`) và hình thức sáp nhập (`HinhThucSapNhap`) liên kết trực tiếp tới văn bản pháp quy.

---

## 4. Kết luận Kiểm toán

1. **Tính hợp thức của nguồn:** Nguồn OSM full-history `vietnam-internal.osh.pbf` có nguồn gốc rõ ràng, mã băm khớp tuyệt đối, quy trình time-filter tại mốc 30/06/2025 bảo đảm tính chân thực lịch sử.
2. **Tính nghiêm ngặt của tập dữ liệu:** Ba tập dữ liệu Data 04, Data 06, Data 07 tuân thủ nghiêm ngặt hợp đồng dữ liệu, không có bản ghi trùng lặp, không bị nhiễu tự nhiên ngoài kiểm soát, bảo toàn trọn vẹn ground truth.
3. **Quyết định đóng băng:** Giữ nguyên trạng thái đóng băng dữ liệu hiện hành theo `docs/VERSIONING.md`. Không thực hiện tái sinh hay can thiệp ngẫu nhiên nhằm duy trì tính tái lập (reproducibility) hoàn hảo cho các nghiên cứu tiếp theo.
