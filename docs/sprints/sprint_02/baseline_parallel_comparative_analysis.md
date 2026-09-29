# Báo cáo Phân tích Song song và Đánh giá Toàn diện Baseline: Libpostal và VietnamAdminUnits

**Đơn vị thực hiện:** Senior AI Engineer độc lập (NLP Evaluation, Data Quality & Benchmark Reproducibility)  
**Dự án:** Vietnamese Address Benchmark (DACN)  
**Địa bàn repository:** `D:\DACN`  
**Phiên bản:** v1 (frozen)  
**Ngày thực hiện kiểm toán:** 19/09/2026  
**Dữ liệu đánh giá:** 13.000 lượt dự đoán thực nghiệm độc lập từ `baseline_predictions_unified.csv` và `baseline_raw_responses.jsonl` (đối chiếu `run_manifest.json` phiên bản 2.0).  

---

## 1. Tóm tắt điều hành (Executive Summary)

Báo cáo này cung cấp kết quả kiểm toán độc lập, phân tích song song và bóc tách cơ chế lỗi chuyên sâu giữa hai công cụ baseline: **Libpostal** (mô hình học máy chuỗi quốc tế CRF/Averaged Perceptron, binding C/Python) và **VietnamAdminUnits** (thư viện hệ luật kết hợp từ điển phân cấp hành chính Việt Nam). 

Đánh giá được thực hiện trên toàn bộ 6 tập benchmark (5.500 dòng địa chỉ gốc, tạo ra đúng **13.000 lượt dự đoán** hợp lệ, không có exception hoặc timeout nào). Toàn bộ dữ liệu định lượng trong báo cáo được tính toán trực tiếp từ `baseline_predictions_unified.csv`, `baseline_raw_responses.jsonl` và các file benchmark đông kết (freeze) tương ứng; **tuyệt đối không sử dụng số liệu từ báo cáo lỗi cũ**.

### Các phát hiện then chốt:

1. **Tính hợp thức của lần chạy baseline:**
   - Đạt 100% về tính toàn vẹn: 13.000 dòng dự đoán khớp chính xác 13.000 dòng log thô; 0 lỗi ngoại lệ (exception=0); 0 bản ghi trùng khóa `ID + CongCu`; mã băm SHA-256 của 6 tập benchmark và 2 file output khớp tuyệt đối với `run_manifest.json`.
2. **Bản chất nhiệm vụ và giới hạn so sánh:**
   - **VietnamAdminUnits không phải mô hình phân loại hệ quy chiếu tự động (T1):** Ở Data 01, 02, 03, 04, công cụ này được cung cấp trước hệ quy chiếu (Oracle mode: `FROM_2025` hoặc `LEGACY`). Ở Data 06 (địa chỉ lai), công cụ được chạy độc lập ở cả hai mode, không có cơ chế tự phát hiện xung đột thời kỳ. Ở Data 07, công cụ thực hiện tác vụ chuyển đổi hành chính cũ $\to$ mới (`CONVERT_2025`), không phải cùng tác vụ phân tích chuỗi (parsing) như Libpostal.
   - **Libpostal là mô hình gán nhãn chuỗi đa ngữ (CRF):** Libpostal xử lý độc lập mọi địa chỉ mà không nhận bất kỳ gợi ý nào về thời kỳ hay ranh giới hành chính Việt Nam.
3. **Bóc tách lỗi gán nhãn mô hình vs. Lỗi adapter ánh xạ:**
   - Điểm Exact Accuracy của Libpostal trên Data 01 cực thấp (2/1.000 = 0,2%) không phải do Libpostal hoàn toàn thất bại trong việc nhận diện thực thể, mà là do **lỗi khuếch đại của Adapter**: Khi Libpostal gán nhãn phường là `city` (513/1.000) hoặc `city_district` (263/1.000), logic ánh xạ trong `libpostal_adapter.py` đã ép `city` vào `QuanHuyen` khi có `state` (tỉnh). Vì hệ 2025 không có cấp huyện, adapter đã tạo ra **775/1.000 (77,5%) lỗi tự điền huyện (over-imputation)** và làm rỗng trường `PhuongXa` (F1 Phường/Xã chỉ đạt 0,004).
4. **Hiệu năng bóc tách số nhà và tên đường:**
   - Adapter của VietnamAdminUnits dùng biểu thức chính quy `^(\d+[\w\/\-]*)(?:[,\s]+)(.*)$`, giả định số nhà bắt đầu bằng chữ số. Khi gặp số nhà chứa chữ cái ở đầu (như `NT02-29`, `BT01-12`), công cụ thất bại hoàn toàn trong việc tách số nhà (gây ra **284/1.500 = 18,9% trường hợp số nhà bị bỏ trống** ở Data 03, đẩy toàn bộ số nhà vào tên đường). Ngược lại, Libpostal đạt F1 số nhà 0,924 (Data 01) và 0,718 (Data 03) nhờ mô hình học chuỗi token mềm dẻo.
5. **Độ bền trước nhiễu (Robustness on Data 02):**
   - VietnamAdminUnits bị suy giảm nghiêm trọng khi gặp nhiễu: độ chính xác toàn phần giảm từ **862/1.000 (86,2%)** trên tập sạch xuống **217/1.000 (21,7%)** trên tập nhiễu; có **645 mẫu** từ đúng thành sai. Các nhiễu phá vỡ từ điển hoặc dấu phân cách như thiếu từ khóa (`thieu_`: 0/148 = 0,0%), lỗi OCR (`loi_ocr_ky_tu`: 2/90 = 2,2%), đảo thứ tự (`dao_thu_tu_hanh_chinh`: 4/95 = 4,2%) làm tê liệt parser dựa trên luật của VietnamAdminUnits.
6. **Xử lý thiếu trường (Data 04):**
   - Về trích xuất bề mặt (Task A), cả hai công cụ đạt kết quả hạn chế: Libpostal đạt 120/800 (15,0%), VietnamAdminUnits đạt 208/800 (26,0%). Đáng chú ý, khi quận/huyện bị lược bỏ, VietnamAdminUnits bị giảm số dấu phẩy xuống dưới ngưỡng quy ước ($< 3$ phẩy ở mode LEGACY), dẫn đến hiện tượng "nuốt" tên đường và phường/xã.
   - Về phục hồi trường bị xóa (Task B), cả hai công cụ thể hiện tính bảo thủ an toàn cao: Libpostal không điền 826/912 (90,6%) trường bị xóa; VietnamAdminUnits không điền 858/912 (94,1%) trường bị xóa.
7. **Chuyển đổi hành chính cũ $\to$ mới (Data 07):**
   - Bộ chuyển đổi của VietnamAdminUnits đạt độ chính xác cặp đơn vị mới **586/600 (97,7%)**. Trên quan hệ $N-1$ (hợp nhất), công cụ đạt **242/244 (99,2%)** và 0 ca sai đích. Trên quan hệ phức hợp $M-N$, công cụ đạt **344/356 (96,6%)**, nhưng ghi nhận **12 ca sai đích có output (3,4%)** do cơ chế fallback chọn phường mặc định khi địa chỉ không thể định vị không gian qua geocoder.

---

## 2. Kiểm toán tính toàn vẹn lần chạy (Run Integrity Audit)

Bảng kiểm toán tính toàn vẹn độc lập của lần chạy baseline hiện hành:

| Kiểm tra | Kết quả ghi nhận | Đạt/Không đạt | Ảnh hưởng và Diễn giải |
|---|---:|:---:|---|
| **Số dòng prediction** | 13.000 dòng | **ĐẠT** | Đúng theo thiết kế: 1.000 (D01) + 4.000 (D02) + 3.000 (D03) + 1.600 (D04) + 1.800 (D06) + 600 (D07). |
| **Số dòng raw response** | 13.000 dòng | **ĐẠT** | Khớp 1:1 với số lượt dự đoán, bảo đảm tính truy vết vết thực thi. |
| **Tính duy nhất khóa `ID + CongCu`** | 0 bản ghi trùng (13.000 unique) | **ĐẠT** | Không có hiện tượng ghi đè hoặc xung đột định danh trong tập kết quả. |
| **Số exception / timeout** | 0 exception, 0 timeout (100% `success`) | **ĐẠT** | Toàn bộ 13.000 lượt gọi đều kết thúc bình thường ở tầng runtime. |
| **Số response rỗng hoàn toàn** | 0 response rỗng | **ĐẠT** | Mọi lời gọi đều trả về cấu trúc dữ liệu hợp lệ (dù có thể trường rỗng). |
| **Hash SHA-256 Benchmark** | 6/6 file khớp 100% manifest | **ĐẠT** | Dữ liệu đầu vào hoàn toàn đông kết, không bị biến đổi sau freeze. |
| **Hash SHA-256 Output** | `baseline_predictions_unified.csv`: `5cfef3...`<br>`baseline_raw_responses.jsonl`: `6ec6c3...` | **ĐẠT** | File kết quả phân tích là bản gốc được tạo từ lần chạy chính thức. |
| **Phiên bản Python & Runtime** | Python 3.14.4; pandas 2.3.3; pyarrow 23.0.1; osmium 4.3.1; tqdm 4.70.1 | **ĐẠT** | Môi trường ảo chuẩn hóa trên WSL (`~/.venv_dacn`). |
| **Phiên bản Libpostal** | Binding `postal` 1.1.11; C commit `25099c5...`; Model `openvenues default` | **ĐẠT** | Sử dụng thư viện C gốc Libpostal và mô hình toàn cầu chuẩn. |
| **Phiên bản VietnamAdminUnits** | Package `vietnamadminunits` 1.0.4 | **ĐẠT** | Thư viện xử lý hành chính Việt Nam phiên bản ổn định 1.0.4. |

### Phân bố số lượng dự đoán theo Dataset và Công cụ:

| Dataset | Mã | n (mẫu) | Lượt chạy Libpostal | Lượt chạy VNAdmin | Tổng lượt |
|---|:---:|---:|---:|---:|---:|
| Full Address New Verified | Data 01 | 1.000 | 1.000 | 1.000 (mode `FROM_2025`) | 2.000 |
| Raw Noisy Synthetic (Clean + Noisy) | Data 02 | 1.000 | 2.000 (1.000 clean + 1.000 noisy) | 2.000 (1.000 clean + 1.000 noisy) | 4.000 |
| Real Address Old (OSM Clean) | Data 03 | 1.500 | 1.500 | 1.500 (mode `LEGACY`) | 3.000 |
| Missing Fields (Task A surface) | Data 04 | 800 | 800 | 800 (Oracle mode) | 1.600 |
| Hybrid Addresses | Data 06 | 600 | 600 (single parse) | 1.200 (600 `FROM_2025` + 600 `LEGACY`) | 1.800 |
| Bidirectional Reform Pairs | Data 07 | 600 | 0 (n/a) | 600 (`convert_to_2025`) | 600 |
| **Tổng cộng** | | **5.500** | **5.900** | **7.100** | **13.000** |

> [!NOTE]
> Báo cáo xác nhận không có sai lệch giữa file dự đoán CSV và log thô JSONL. Mọi phép đối chiếu trong các phần tiếp theo đều xuất phát từ nguồn dữ liệu nhất quán này.

---

## 3. Chuẩn hóa Cách hiểu Protocol và Mapping của Từng Công cụ

### 3.1. Libpostal: Kiến trúc, Raw Labels và Logic Adapter

1. **Xác nhận bản chất công cụ:**
   - Đây là **Libpostal thật**, sử dụng C library (commit `25099c5`) thông qua Python C-binding chính thức `postal.parser` (phiên bản `1.1.11`). Công cụ không phải là mock hay adapter mô phỏng heuristic (lớp `HeuristicAddressAdapter` trong code chỉ là bộ quy tắc nội bộ và không được gọi trong lần chạy chính thức).
2. **Raw Labels thực tế phát sinh trong log:**
   - Trong `baseline_raw_responses.jsonl`, Libpostal trả về danh sách token gán nhãn theo ontology quốc tế: `house_number`, `road`, `suburb`, `neighbourhood`, `city_district`, `state_district`, `city`, `state`, `house`.
3. **Logic ánh xạ của Adapter (`src/evaluation/adapters/libpostal_adapter.py`):**
   ```python
   # Trích đoạn logic trong LibpostalAdapter.parse()
   province = tags.get("state", "") or tags.get("city", "")
   district = tags.get("state_district", "") or tags.get("city_district", "")
   if tags.get("state") and not district:
       district = tags.get("city", "")
   pred = StandardPrediction(
       so_nha=tags.get("house_number", ""),
       ten_duong=tags.get("road", ""),
       phuong_xa=tags.get("suburb", "") or tags.get("neighbourhood", ""),
       quan_huyen=district,
       tinh_thanh=province,
   )
   ```
4. **Bóc tách 4 tầng sai số của Libpostal:**
   - **Lỗi nhãn thô của mô hình (CRF Model Error):** Mô hình Libpostal được huấn luyện trên dữ liệu OpenStreetMap toàn cầu. Trong ngữ cảnh tiếng Việt, chuỗi `"Phường X"` hiếm khi được gán nhãn `suburb` (chỉ 22/1.000 trường hợp ở Data 01), mà thường bị gán nhãn thành `city` (1.059 lần) hoặc `city_district` (183 lần) do thiếu hiểu biết về hệ thống phân cấp hành chính nội địa.
   - **Lỗi logic của Adapter (Adapter Mapping Error):** Dòng code `if tags.get("state") and not district: district = tags.get("city", "")` là một giả định mang tính phá hủy đối với địa chỉ hệ mới 2025. Khi Libpostal gán `tỉnh bắc ninh` là `state` và `phường phù khê` là `city`, adapter đã tự động đưa `"phường phù khê"` vào `district` (`QuanHuyen`), trong khi `phuong_xa` hoàn toàn rỗng. Điều này biến một lỗi phân loại nhãn thô thành một **lỗi kép**: vừa bỏ sót phường (`PhuongXa` FN), vừa bịa ra huyện (`QuanHuyen` FP).
   - **Lỗi chuẩn hóa / Scorer:** Hàm `_norm` trong `scorer.py` loại bỏ các tiền tố `"phường", "xã", "thành phố"`. Tuy nhiên, khi một thực thể bị đẩy sai trường hoàn toàn, scorer chấm `MISMATCH` hoặc `FP/FN`.
   - **Bất đối xứng ngữ nghĩa với Ground Truth:** Libpostal là parser phi thời gian (atemporal). Ground truth của Data 01 không có `QuanHuyen` (cấu trúc 2 cấp 2025). Việc đánh giá Libpostal trên ground truth 2025 mà không có tầng điều chỉnh hệ quy chiếu khiến Libpostal chịu thiệt thòi về mặt kỹ thuật.
   - *Quy tắc diễn giải:* **Không được kết luận** Libpostal "không hiểu hành chính 2025" như một khiếm khuyết nội tại của mô hình, vì Libpostal vốn chỉ là mô hình bóc tách cấu trúc cú pháp địa chỉ chung, không được thiết kế cho việc suy luận thể chế hành chính cụ thể của một quốc gia.

### 3.2. VietnamAdminUnits: Cơ chế Phân tích, Oracle Mode và Converter

1. **Các hàm thực thi trong pipeline:**
   - `parse_address(address, mode=..., keep_street=True)` được dùng cho Data 01, 02, 03, 04, 06.
   - `convert_address(address, mode='CONVERT_2025')` được dùng riêng cho Data 07.
2. **Oracle Mode và sự phụ thuộc vào hệ quy chiếu cung cấp trước:**
   - Ở **Data 01**: Protocol truyền cứng `mode="FROM_2025"`.
   - Ở **Data 02**: Protocol kiểm tra nhãn `HeQuyChieu` trong ground truth; nếu là `"moi"` thì truyền `FROM_2025`, nếu là `"cu"` thì truyền `LEGACY`.
   - Ở **Data 03**: Protocol truyền cứng `mode="LEGACY"`.
   - Ở **Data 04**: Protocol truyền Oracle mode dựa trên `HeQuyChieu`.
   - *Ý nghĩa then chốt:* Kết quả cao của VietnamAdminUnits ở các tập này là kết quả **phân tích cú pháp khi đã biết trước thời kỳ**, hoàn toàn **chưa chứng minh được năng lực tự động phân loại hệ quy chiếu (T1)**.
3. **Data 06 (Địa chỉ lai):**
   - Chạy độc lập hai lần: một lần ép mode `FROM_2025`, một lần ép mode `LEGACY`. Tuyệt đối không có mode "tự động" và không được phép gộp kết quả sau khi nhìn đáp án.
4. **Data 07 (Chuyển đổi hành chính):**
   - Đây là tác vụ ánh xạ đơn vị hành chính cũ $\to$ mới, chấm trên hai trường `PhuongXa` và `TinhThanh`. Libpostal không có chức năng này nên không tham gia đánh giá trên Data 07.
5. **Cơ chế phụ thuộc mạng và Geocoder trong Converter:**
   - Khi kiểm tra mã nguồn `third_party/vietnamadminunits/vietnamadminunits/converter/converter_2025.py` (dòng 65–97) và `vietnamadminunits/parser/utils.py` (dòng 10: `geolocator = ArcGIS()`), phát hiện rằng: Đối với các xã/phường bị chia tách thành nhiều đơn vị mới (quan hệ $1-N$ hoặc $M-N$), nếu địa chỉ cũ có thông tin đường phố (`street`), converter sẽ thực hiện lời gọi mạng: `old_location = get_geo_location(old_unit.get_address())` thông qua dịch vụ **ArcGIS Geocoder**.
   - Nếu tìm thấy tọa độ, nó sẽ tính khoảng cách hình học tới các phường mới để chọn đích. Nếu không tìm thấy tọa độ hoặc mạng không khả dụng, nó rơi vào nhánh dự phòng: `next((ward['newWardKey'] for ward in new_wards if ward['isDefaultNewWard']), None)`.
   - *Hệ quả:* Tác vụ chuyển đổi $M-N$ có tính phụ thuộc dịch vụ bên ngoài và có thể tạo ra sai lệch im lặng khi mạng chậm hoặc ArcGIS trả về kết quả không khớp.
6. **Cách adapter tách số nhà và tên đường (`_split_street_house_number`):**
   - Đối tượng `AdminUnit` của VietnamAdminUnits chỉ trả về `street` gộp chung số nhà và tên đường.
   - Adapter tại `vnadmin_adapter.py` sử dụng regex:
     `match = re.match(r"^(\d+[\w\/\-]*)(?:[,\s]+)(.*)$", s)`
   - Nếu chuỗi `street` bắt đầu bằng chữ (ví dụ `"NT02-29, Ngọc Trai 2"`), regex thất bại, adapter trả về `SoNha = ""` và `TenDuong = s`.

---

## 4. Phân tích Song song theo Từng Dataset

### 4.1. Data 01 — Địa chỉ mới sạch (1.000 mẫu)

1. **Mục tiêu phép đo:** Đánh giá khả năng phân tích địa chỉ hệ mới 2 cấp (Số nhà, Tên đường, Phường/Xã, Tỉnh/Thành; không có Quận/Huyện).
2. **Số mẫu hợp lệ:** 1.000 mẫu.
3. **Protocol Libpostal:** Gọi mô hình C parser gốc, ánh xạ qua adapter cố định.
4. **Protocol VietnamAdminUnits:** Gọi `parse_address` với `mode="FROM_2025"`.
5. **Kết quả định lượng:**
   - **Libpostal:**
     - Exact match: **2/1.000 (0,2%)** [95% CI: 0,0% – 0,5%].
     - Partial match: **917/1.000 (91,7%)**.
     - Error: **81/1.000 (8,1%)**.
     - Field F1: Số nhà = **0,924**; Tên đường = **0,373**; Phường/Xã = **0,004**; Quận/Huyện = **0,000** (n/a); Tỉnh/Thành = **0,938**. Macro F1 = **0,448**.
     - Tỷ lệ tự điền huyện (Hallucination/Over-imputation): **775/1.000 (77,5%)**.
   - **VietnamAdminUnits:**
     - Exact match: **973/1.000 (97,3%)** [95% CI: 96,3% – 98,3%].
     - Partial match: **27/1.000 (2,7%)**.
     - Error: **0/1.000 (0,0%)**.
     - Field F1: Số nhà = **0,979**; Tên đường = **0,973**; Phường/Xã = **1,000**; Quận/Huyện = n/a; Tỉnh/Thành = **1,000**. Macro F1 = **0,790** (tính cả huyện 0,0) hoặc **0,988** (trên 4 trường hiện diện).
     - Tỷ lệ tự điền huyện: **0/1.000 (0,0%)**.
6. **So sánh Paired trên cùng ID:**
   - Cả hai cùng đúng: **2/1.000 (0,2%)** (`D01_0069`, `D01_0819`).
   - Chỉ Libpostal đúng: **0/1.000 (0,0%)**.
   - Chỉ VNAdmin đúng: **971/1.000 (97,1%)**.
   - Cả hai cùng sai: **27/1.000 (2,7%)**.
   - Kiểm định McNemar: $\chi^2 = 969,0$, $p = 9,8 \times 10^{-213}$ (chênh lệch có ý nghĩa thống kê cực đại).
7. **Bóc tách trường mạnh/yếu:**
   - *Số nhà:* Cả hai đều mạnh (LP 0,924 vs VN 0,979). Libpostal tách số nhà dạng xuyệt (`208/118`, `801/7`) rất tốt.
   - *Tên đường:* VNAdmin áp đảo (0,973 vs 0,373). Libpostal thường xuyên nuốt cụm phường xã vào tên đường (ví dụ `D01_0002`: `"nguyễn văn linh phường tân thuận"` được gán toàn bộ là `road`).
   - *Phường/Xã:* VNAdmin đạt tuyệt đối 1,000 nhờ từ điển 2025. Libpostal sụp đổ hoàn toàn (0,004) do nhãn raw bị lệch sang `city` (513 lần) và `city_district` (263 lần).
   - *Quận/Huyện:* VNAdmin tuân thủ cấu trúc 2 cấp (không điền huyện). Libpostal bị adapter ép điền huyện ở 775 mẫu.
8. **Ca lỗi đại diện:**
   - `D01_0000`: `"394, Đường Lý Thường Kiệt, Phường Phù Khê, Tỉnh Bắc Ninh"`.
     - *Libpostal:* Raw gán `"phường phù"` (`city_district`), `"khê"` (`city`). Adapter ghép thành `QuanHuyen = "phường phù"`, bỏ trống `PhuongXa`.
     - *VNAdmin:* Bóc tách chuẩn xác 100% (Số nhà: `394`, Tên đường: `Đường Lý Thường Kiệt`, Phường/Xã: `Phường Phù Khê`, Tỉnh/Thành: `Tỉnh Bắc Ninh`).
9. **Giới hạn kết luận:** Kết quả 97,3% của VNAdmin có được là nhờ được cung cấp trước mode `FROM_2025`. Nếu đưa vào một chuỗi địa chỉ chưa rõ thời kỳ, công cụ không tự quyết định được mode này.

---

### 4.2. Data 02 — Cặp sạch và nhiễu (1.000 cặp địa chỉ)

1. **Mục tiêu phép đo:** Đánh giá độ bền (robustness) và mức độ suy giảm hiệu năng của hai công cụ khi địa chỉ bị làm nhiễu mô phỏng (tổng hợp có kiểm soát từ tham số hóa đơn thật).
2. **Số mẫu hợp lệ:** 1.000 cặp địa chỉ ghép đôi theo ID cơ sở (`_clean` vs `_noisy`).
3. **Protocol Libpostal:** Chạy mô hình độc lập trên chuỗi sạch và chuỗi nhiễu.
4. **Protocol VietnamAdminUnits:** Chạy Oracle mode theo `HeQuyChieu` của từng dòng (`FROM_2025` nếu mới, `LEGACY` nếu cũ) trên cả hai chuỗi.
5. **So sánh trực tiếp theo mức độ nhiễu:**

| Mức nhiễu | n | LP clean Exact | LP noisy Exact | LP Clean $\to$ Noisy F1 | VN clean Exact | VN noisy Exact | VN Clean $\to$ Noisy F1 | VN Sạch đúng $\to$ Nhiễu sai | Công cụ suy giảm nhiều hơn |
|---|---:|---:|---:|:---:|---:|---:|:---:|---:|---|
| **Nhẹ** | 376 | 1/376 (0,3%) | 1/376 (0,3%) | 0,414 $\to$ 0,372 (-0,042) | 325/376 (86,4%) | 111/376 (29,5%) | 0,953 $\to$ 0,801 (-0,152) | **214/325 (65,8%)** | **VietnamAdminUnits** |
| **Vừa** | 413 | 0/413 (0,0%) | 0/413 (0,0%) | 0,419 $\to$ 0,322 (-0,097) | 356/413 (86,2%) | 94/413 (22,8%) | 0,946 $\to$ 0,771 (-0,175) | **262/356 (73,6%)** | **VietnamAdminUnits** |
| **Nặng** | 211 | 0/211 (0,0%) | 0/211 (0,0%) | 0,416 $\to$ 0,275 (-0,141) | 181/211 (85,8%) | 12/211 (5,7%) | 0,947 $\to$ 0,568 (-0,379) | **169/181 (93,4%)** | **VietnamAdminUnits** |
| **Toàn bộ** | **1.000** | **1/1.000 (0,1%)** | **1/1.000 (0,1%)** | **0,416 $\to$ 0,332 (-0,084)** | **862/1.000 (86,2%)** | **217/1.000 (21,7%)** | **0,949 $\to$ 0,748 (-0,201)** | **645/862 (74,8%)** | **VietnamAdminUnits** |

6. **Phân tích chi tiết mức độ suy giảm:**
   - **VietnamAdminUnits suy giảm nghiêm trọng:** Trên tập sạch, VNAdmin đạt độ chính xác 86,2% (862/1.000). Khi có nhiễu, độ chính xác sụp đổ xuống 21,7% (217/1.000), nghĩa là **74,8% số ca đúng trên tập sạch đã bị sai khi gặp nhiễu** (645 ca). Ở mức nhiễu nặng, độ chính xác chỉ còn 5,7% (12/211).
   - **Libpostal:** Do điểm exact match ở mức sàn (0,1%), việc đánh giá suy giảm phải nhìn vào **Field F1**. Macro F1 của Libpostal giảm từ 0,416 xuống 0,332 (-0,084, mức giảm tương đối 20,2%), trong khi VNAdmin giảm từ 0,949 xuống 0,748 (-0,201, mức giảm tương đối 21,2%). Tỷ lệ F1 tên đường của Libpostal giảm mạnh từ 0,305 xuống 0,189 do lỗi phân tách từ khi mất dấu hoặc dính từ.
   - **Hiện tượng Clean sai $\to$ Noisy đúng:**
     - Libpostal: ghi nhận đúng 1 ca (`D02_N00011`: sạch đúng $\to$ nhiễu đúng; `D02_N00732`: sạch sai $\to$ nhiễu đúng do nhiễu vô tình làm ngắt chuỗi giúp Libpostal nhận đúng `suburb`).
     - VietnamAdminUnits: **0 ca** (0/1.000). Không có trường hợp nào chuỗi sạch bị sai mà khi thêm nhiễu lại trở thành đúng.
7. **Kết quả theo từng nhóm phép biến đổi đồng xuất hiện:**

| Phép biến đổi | n | LP Clean F1 | LP Noisy F1 | VN Clean Exact | VN Noisy Exact | VN Clean F1 | VN Noisy F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `viet_tat` | 603 | 0,431 | 0,318 | 549/603 (91,0%) | 143/603 (23,7%) | 0,965 | 0,757 |
| `bo_dau` | 455 | 0,418 | 0,292 | 398/455 (87,5%) | 83/455 (18,2%) | 0,951 | 0,720 |
| `loi_ocr_ky_tu` | 90 | 0,400 | 0,250 | 75/90 (83,3%) | 2/90 (2,2%) | 0,944 | 0,477 |
| `thieu_` (thiếu từ khóa cấp) | 148 | 0,420 | 0,263 | 123/148 (83,1%) | **0/148 (0,0%)** | 0,939 | 0,468 |
| `dao_thu_tu_hanh_chinh` | 95 | 0,426 | 0,283 | 79/95 (83,2%) | 4/95 (4,2%) | 0,939 | 0,580 |
| `dinh_dang_phan_cach` | 1.000 | 0,416 | 0,332 | 862/1.000 (86,2%) | 217/1.000 (21,7%) | 0,949 | 0,748 |

8. **Cảnh báo phương pháp luận (Methodological Warning):**
   - Phép biến đổi `dinh_dang_phan_cach` xuất hiện ở **100% mẫu** (1.000/1.000 dòng).
   - Các phép biến đổi khác (viết tắt, bỏ dấu, lỗi OCR, thiếu tiền tố, đảo thứ tự) luôn đồng xuất hiện cùng thay đổi dấu phân cách. Do đó, **tuyệt đối không được quy kết một loại nhiễu cụ thể là nguyên nhân duy nhất** làm sụp đổ kết quả nếu chưa tiến hành ablation độc lập từng biến dạng.
   - Tuy nhiên, bằng chứng trực tiếp cho thấy: VietnamAdminUnits cực kỳ nhạy cảm với việc mất từ khóa nhận diện (`thieu_` khiến độ chính xác về 0%) và đảo trật tự phân cấp (`dao_thu_tu` chỉ còn 4,2%), bởi kiến trúc của nó dựa trên thứ tự xuất hiện chuẩn tắc và tra cứu từ điển tĩnh.

---

### 4.3. Data 03 — Mốc sạch hệ cũ (1.500 mẫu OSM chuẩn)

1. **Mục tiêu phép đo:** Đánh giá khả năng phân tách địa chỉ hệ cũ 3 cấp chuẩn (Số nhà, Tên đường, Phường/Xã, Quận/Huyện, Tỉnh/Thành) từ nguồn dữ liệu mở OpenStreetMap đã được chuẩn hóa sạch 100%.
2. **Xác nhận chất lượng dữ liệu đầu vào:**
   - Đã kiểm tra 100% dữ liệu: Cả 1.500 dòng đều có đầy đủ cả 5 trường trong ground truth, **không còn bất kỳ dòng nào bị thiếu tự nhiên**. Tập này hoàn toàn hợp thức để đo lường độ chính xác bóc tách trong điều kiện lý tưởng của hệ cũ.
3. **Kết quả định lượng:**
   - **Libpostal:**
     - Exact match: **1/1.500 (0,1%)** [95% CI: 0,0% – 0,2%].
     - Partial match: **936/1.500 (62,4%)**.
     - Error: **563/1.500 (37,5%)**.
     - Field F1: Số nhà = **0,718**; Tên đường = **0,259**; Phường/Xã = **0,006**; Quận/Huyện = **0,073**; Tỉnh/Thành = **0,826**. Macro F1 = **0,376**.
   - **VietnamAdminUnits:**
     - Exact match: **1.094/1.500 (72,9%)** [95% CI: 70,7% – 75,1%].
     - Partial match: **372/1.500 (24,8%)**.
     - Error: **34/1.500 (2,3%)**.
     - Field F1: Số nhà = **0,866**; Tên đường = **0,780**; Phường/Xã = **0,915**; Quận/Huyện = **0,977**; Tỉnh/Thành = **0,983**. Macro F1 = **0,904**.
4. **So sánh Paired trên cùng ID:**
   - Cả hai cùng đúng: **1/1.500 (0,1%)** (`D03_1281`).
   - Chỉ Libpostal đúng: **0/1.500 (0,0%)**.
   - Chỉ VNAdmin đúng: **1.093/1.500 (72,9%)**.
   - Cả hai cùng sai: **406/1.500 (27,1%)**.
   - McNemar test: $\chi^2 = 1.091,0$, $p = 3,0 \times 10^{-239}$.
5. **Bóc tách lỗi ranh giới (Boundary Errors) và số nhà dạng chữ của VNAdmin:**
   - Trong 406 ca sai của VNAdmin, phát hiện **284 trường hợp số nhà bị bỏ trống** (`SoNha` dự đoán là `""` dù ground truth có dữ liệu).
   - *Nguyên nhân trực tiếp:* Biểu thức regex của adapter `^(\d+[\w\/\-]*)` chỉ bóc tách được số nhà bắt đầu bằng ký tự số. Các địa chỉ thuộc dự án khu đô thị mới tại Việt Nam (như Vinhomes Ocean Park, Ecopark) có mã căn hộ dạng chữ-số như `"NT02-29, Ngọc Trai 2"` (`D03_0000`) hoặc `"NT02-35"` (`D03_0001`). Khi gặp chữ cái `"N"`, regex không khớp, dẫn đến `SoNha = ""` và đẩy toàn bộ `"Nt02 - 29, Ngọc Trai 2"` vào trường `TenDuong`.
   - Điều này giải thích tại sao VNAdmin có **330 ca sai lệch ranh giới tên đường** (`TenDuong` mismatch).
6. **Lỗi của Libpostal trên Data 03:**
   - Ở hệ cũ, ground truth có đầy đủ cả `PhuongXa` và `QuanHuyen`. Tuy nhiên, Libpostal vẫn liên tục gán nhãn cả cụm xã/huyện thành một thực thể duy nhất (`road` hoặc `city`), khiến trường `PhuongXa` chỉ đạt F1 là 0,006.
   - Ca duy nhất Libpostal đoán đúng hoàn toàn là `D03_1281`: `"68b/1, Đường Cách Mạng Tháng Tám, An Thạnh, Thuận An, Bình Dương"`. Trong ca này, raw labels của Libpostal tình cờ phân rã hoàn hảo: `"68b/1"` $\to$ `house_number`, `"đường cách mạng tháng tám"` $\to$ `road`, `"an thạnh"` $\to$ `suburb`, `"thuận an"` $\to$ `city`, `"bình dương"` $\to$ `state`.

---

### 4.4. Data 04 — Thiếu trường có kiểm soát (800 mẫu)

Data 04 được tạo ra từ nguồn địa chỉ sạch hoàn toàn, trong đó một số trường được chủ động lược bỏ theo 4 kịch bản kiểm soát (`drop_ward`, `drop_district`, `drop_housenumber`, `drop_housenumber_ward`). Đánh giá được tách bạch nghiêm ngặt thành hai nhiệm vụ:

#### Nhiệm vụ A — Trích xuất phần còn hiện diện trên bề mặt
Chỉ so khớp dự đoán với các trường thực sự còn xuất hiện trong chuỗi địa chỉ (trường bị lược bỏ có ground truth là rỗng).

| Chỉ số Task A | Libpostal | VietnamAdminUnits | So sánh & Kiểm định |
|---|---:|---:|---|
| **Exact Match** | **120/800 (15,0%)** [12,6% – 17,5%] | **208/800 (26,0%)** [23,0% – 29,1%] | VNAdmin cao hơn 11,0% |
| **Partial Match** | 213/800 (26,6%) | 246/800 (30,8%) | |
| **Error** | 467/800 (58,4%) | 346/800 (43,2%) | |
| SoNha F1 | **0,792** | 0,006 | Libpostal vượt trội |
| TenDuong F1 | 0,285 | **0,447** | VNAdmin tốt hơn |
| PhuongXa F1 | 0,012 | **0,697** | VNAdmin tốt hơn |
| QuanHuyen F1 | 0,162 | **0,936** | VNAdmin tốt hơn |
| TinhThanh F1 | 0,724 | **0,785** | Tương đương |
| **Macro F1** | 0,395 | **0,574** | VNAdmin cao hơn |
| **Paired McNemar** | Cả hai đúng: 0/800 (0,0%) | Chỉ LP đúng: 120; Chỉ VN đúng: 208 | $\chi^2 = 23,08; p = 1,56 \times 10^{-6}$ |

> [!IMPORTANT]
> Lưu ý đặc biệt ở Task A: **Không có ca nào cả hai công cụ cùng đoán đúng** (Both Correct = 0). Libpostal chiếm ưu thế tuyệt đối ở các ca giữ lại số nhà khi thiếu cấp hành chính, trong khi VietnamAdminUnits chiếm ưu thế ở các ca thiếu số nhà nhưng còn nguyên phân cấp hành chính.
> Sự sụp đổ của VNAdmin trên trường `SoNha` (F1 = 0,006) là do khi thiếu quận hoặc xã, số lượng dấu phẩy bị giảm xuống dưới 3, khiến parser của thư viện không bóc tách được `street` ra khỏi các thành phần còn lại.

#### Nhiệm vụ B — Đánh giá hành vi đối với trường bị lược bỏ (Imputation Behavior)
Sử dụng `GT_*` (giá trị nguyên bản trước khi xóa) để kiểm tra: công cụ tự điền đúng (phục hồi), điền sai (ảo giác/suy đoán sai), hay không điền (bảo thủ an toàn).

| Kiểu thiếu | Trường bị lược | n trường | Libpostal Phục hồi đúng | Libpostal Điền sai | Libpostal Không điền (Bảo thủ) | VNAdmin Phục hồi đúng | VNAdmin Điền sai | VNAdmin Không điền (Bảo thủ) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `drop_ward` | Phường/Xã | 241 | 0/241 (0,0%) | 7/241 (2,9%) | 234/241 (97,1%) | 5/241 (2,1%) | 19/241 (7,9%) | 217/241 (90,0%) |
| `drop_district` | Quận/Huyện | 99 | 0/99 (0,0%) | 10/99 (10,1%) | 89/99 (89,9%) | 2/99 (2,0%) | 7/99 (7,1%) | 90/99 (90,9%) |
| `drop_housenumber` | Số nhà | 348 | 2/348 (0,6%) | 48/348 (13,8%) | 298/348 (85,6%) | 1/348 (0,3%) | 0/348 (0,0%) | 347/348 (99,7%) |
| `drop_housenumber_ward` | Số nhà + Phường | 224 | 0/224 (0,0%) | 19/224 (8,5%) | 205/224 (91,5%) | 6/224 (2,7%) | 14/224 (6,2%) | 204/224 (91,1%) |
| **Tổng cộng** | **Tất cả trường bị lược** | **912** | **2/912 (0,2%)** | **84/912 (9,2%)** | **826/912 (90,6%)** | **14/912 (1,5%)** | **40/912 (4,4%)** | **858/912 (94,1%)** |

**So sánh định tính:**
- **Tính bảo thủ:** Cả hai công cụ đều có mức độ bảo thủ cao ($> 90\%$). VietnamAdminUnits bảo thủ hơn (94,1% không điền so với 90,6% của Libpostal).
- **Xu hướng tự điền sai (Over-imputation / Hallucination):** Libpostal có tỷ lệ điền sai cao hơn gấp đôi VNAdmin (9,2% vs 4,4%). Đặc biệt ở kịch bản `drop_housenumber`, Libpostal tự tiện lấy token đầu tiên của tên đường hoặc số ngõ để gán thành số nhà trong **48 trường hợp** (13,8%).
- VNAdmin khi bị thiếu xã (`drop_ward`) có 19 trường hợp (7,9%) tự suy đoán sai phường/xã dựa trên từ điển mặc định của quận.
---

### 4.5. Data 06 — Địa chỉ lai qua các thời kỳ (600 mẫu)

1. **Mục tiêu phép đo:** Kiểm tra khả năng xử lý các địa chỉ lai tạp giữa các thành phần cũ và mới:
   - **C1 (420 mẫu):** Phường mới + Quận cũ + Tỉnh cũ (dạng lai phổ biến nhất trong đời sống).
   - **C2 (120 mẫu):** Phường mới + Quận cũ + Tỉnh mới.
   - **C3 (60 mẫu):** Phường cũ + Quận cũ + Tỉnh mới.
2. **Protocol VietnamAdminUnits:** Báo cáo độc lập ở cả hai chế độ: `FROM_2025` và `LEGACY`. Tuyệt đối không chọn chế độ thắng sau khi nhìn kết quả.
3. **Protocol Libpostal:** Phân tích đơn lẻ (single parse) và kiểm tra raw tokens.
4. **Bảng so sánh chi tiết theo C1 / C2 / C3:**

| Kiểu lai | n | Libpostal Exact | VNAdmin mode FROM_2025 | VNAdmin mode LEGACY | Mode / Công cụ có kết quả bóc tách tốt nhất |
|---|---:|---:|---:|---:|---|
| **C1** | 420 | 0/420 (0,0%) | 0/420 (0,0%) | **262/420 (62,4%)** | **VNAdmin mode LEGACY** |
| **C2** | 120 | 0/120 (0,0%) | 0/120 (0,0%) | **97/120 (80,8%)** | **VNAdmin mode LEGACY** |
| **C3** | 60 | 2/60 (3,3%) | 0/60 (0,0%) | **56/60 (93,3%)** | **VNAdmin mode LEGACY** |
| **Toàn bộ** | **600** | **2/600 (0,3%)** | **0/600 (0,0%)** | **415/600 (69,2%)** | **VNAdmin mode LEGACY** |

5. **Bóc tách cơ chế phân tích trên địa chỉ lai:**
   - **Sự sụp đổ của VNAdmin mode `FROM_2025` (0,0%):**
     Hệ 2025 không có cấp quận/huyện. Khi ép mode `FROM_2025`, parser của VNAdmin gặp token quận cũ trong chuỗi địa chỉ lai. Hệ quả là nó xem token quận cũ là một phần của đường phố hoặc bị từ chối khớp, dẫn đến `PhuongXa` hoặc `TenDuong` bị sai hoàn toàn (92,7% partial, 7,3% error).
   - **Hiệu năng của VNAdmin mode `LEGACY` (69,2%):**
     Vì ground truth của Data 06 ghi nhận phân rã đầy đủ các thành phần thực tế trên chuỗi (gồm cả trường `QuanHuyen`), mode `LEGACY` nhận diện được cấu trúc 3 cấp.
     - Ở C3 (phường cũ + quận cũ), tỷ lệ đúng đạt tới **93,3%** vì cả phường và quận đều nằm trong từ điển cũ của thư viện.
     - Ở C1 (phường mới + quận cũ), tỷ lệ đúng giảm xuống **62,4%** vì phường mới không có trong từ điển của quận cũ tương ứng; thư viện thường nuốt phường mới vào tên đường hoặc ép vào một phường cũ gần giống.
   - **Libpostal:**
     Libpostal hoàn toàn không có nhận thức về xung đột thời kỳ. Nó chỉ bóc tách token theo xác suất ngữ cảnh. Trong một số ít trường hợp ở C3 (`D06_0556`, `D06_0588`), nó tách đúng các trường nhưng hoàn toàn không đưa ra bất kỳ cảnh báo nào về việc địa chỉ đang trộn lẫn các mốc thời gian.

---

### 4.6. Data 07 — Chuyển đổi hành chính cũ $\to$ mới (600 cặp)

1. **Bản chất tác vụ:** Đây là bài toán ánh xạ đơn vị hành chính (T2 mapping), kiểm tra khả năng suy ra đúng cặp `PhuongXa` và `TinhThanh` mới từ địa chỉ cũ trước ngày 01/07/2025.
2. **Đối tượng đánh giá:** Chỉ có hàm `convert_to_2025` của **VietnamAdminUnits** được đánh giá. **Không có điểm Libpostal** trên tập này vì Libpostal không cung cấp chức năng ánh xạ thể chế.
3. **Kết quả định lượng theo quan hệ sáp nhập:**

| Quan hệ đồ thị | Số mẫu (n) | Đúng cặp đơn vị mới | Sai đích có output | Trả rỗng (Empty) | Exception | Tỷ lệ thành công |
|---|---:|---:|---:|---:|---:|---:|
| **N-1 (Hợp nhất toàn phần)** | 244 | 242/244 | 0/244 (0,0%) | 2/244 (0,8%) | 0/244 (0,0%) | **99,2%** |
| **M-N (Tái cơ cấu phức hợp)**| 356 | 344/356 | 12/356 (3,4%) | 0/356 (0,0%) | 0/356 (0,0%) | **96,6%** |
| **Toàn bộ** | **600** | **586/600** | **12/600 (2,0%)** | **2/600 (0,3%)** | **0/600 (0,0%)** | **97,7%** |

4. **Đối chiếu thực tế và Cơ chế sai lệch im lặng (Silent Error):**
   - **Quan hệ N-1:** Đạt độ chính xác gần như tuyệt đối (99,2%). Trong quan hệ gộp nhiều xã cũ thành một xã mới, không có sự nhập nhằng về đích đến. 2 ca trả rỗng là do địa chỉ cũ bị thiếu thông tin nhận dạng trong từ điển chuyển đổi.
   - **Quan hệ M-N:** Toàn bộ **12 ca sai đích** đều tập trung ở nhóm này.
     - *Ví dụ điển hình:* `D07_0018_M-N` (`36, Phố Trần Phú, Phường Điện Biên, Quận Ba Đình, Hà Nội`).
       - Đáp án đúng theo nghị quyết và OSM diff: `PhuongXa = "Phường Ba Đình"`.
       - VNAdmin chuyển đổi thành: `PhuongXa = "Phường Hoàn Kiếm"`.
     - *Bằng chứng cơ chế:* Trong sáp nhập M-N, Phường Điện Biên cũ được chia tách một phần về Phường Ba Đình mới và một phần về Phường Hoàn Kiếm mới. Do tọa độ của số nhà 36 Trần Phú không được phân giải chuẩn xác qua ArcGIS hoặc cơ chế phân định không gian của converter bị lệch, công cụ đã gán sai đích sang Hoàn Kiếm nhưng vẫn trả về kết quả thành công mà không có cờ cảnh báo bất định.

---

## 5. So sánh Thống kê Hai Công cụ

### 5.1. Bảng So sánh Tổng thể theo Từng Dataset

| Dataset | Công cụ | n | Exact Match | Partial Match | Error | Macro Field F1 | Bỏ sót (Missing) | Ảo giác (Hallucination) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **Data 01 (Mới sạch)** | Libpostal | 1.000 | 2/1.000 (0,2%) | 917/1.000 (91,7%) | 81/1.000 (8,1%) | 0,448 | 223/1.000 (22,3%) | 775/1.000 (77,5%) |
| | VNAdmin (Oracle) | 1.000 | **973/1.000 (97,3%)** | 27/1.000 (2,7%) | 0/1.000 (0,0%) | **0,790** | 27/1.000 (2,7%) | 0/1.000 (0,0%) |
| **Data 02 Clean** | Libpostal | 1.000 | 1/1.000 (0,1%) | 760/1.000 (76,0%) | 239/1.000 (23,9%) | 0,416 | 639/1.000 (63,9%) | 358/1.000 (35,8%) |
| | VNAdmin (Oracle) | 1.000 | **862/1.000 (86,2%)** | 132/1.000 (13,2%) | 6/1.000 (0,6%) | **0,949** | 138/1.000 (13,8%) | 0/1.000 (0,0%) |
| **Data 02 Noisy** | Libpostal | 1.000 | 1/1.000 (0,1%) | 557/1.000 (55,7%) | 442/1.000 (44,2%) | 0,332 | 707/1.000 (70,7%) | 288/1.000 (28,8%) |
| | VNAdmin (Oracle) | 1.000 | **217/1.000 (21,7%)** | 764/1.000 (76,4%) | 19/1.000 (1,9%) | **0,748** | 780/1.000 (78,0%) | 0/1.000 (0,0%) |
| **Data 03 (Cũ sạch)** | Libpostal | 1.500 | 1/1.500 (0,1%) | 936/1.500 (62,4%) | 563/1.500 (37,5%) | 0,376 | 1.474/1.500 (98,3%) | 0/1.500 (0,0%) |
| | VNAdmin (mode LEGACY) | 1.500 | **1.094/1.500 (72,9%)** | 372/1.500 (24,8%) | 34/1.500 (2,3%) | **0,904** | 394/1.500 (26,3%) | 0/1.500 (0,0%) |
| **Data 04 (Thiếu Task A)**| Libpostal | 800 | 120/800 (15,0%) | 213/800 (26,6%) | 467/800 (58,4%) | 0,395 | 318/800 (39,8%) | 264/800 (33,0%) |
| | VNAdmin (Oracle) | 800 | **208/800 (26,0%)** | 246/800 (30,8%) | 346/800 (43,2%) | **0,574** | 483/800 (60,4%) | 54/800 (6,8%) |
| **Data 06 (Lai)** | Libpostal | 600 | 2/600 (0,3%) | 498/600 (83,0%) | 100/600 (16,7%) | 0,504 | 589/600 (98,2%) | 0/600 (0,0%) |
| | VNAdmin (FROM_2025) | 600 | 0/600 (0,0%) | 556/600 (92,7%) | 44/600 (7,3%) | **0,656** | 600/600 (100,0%) | 0/600 (0,0%) |
| | VNAdmin (LEGACY) | 600 | **415/600 (69,2%)** | 183/600 (30,5%) | 2/600 (0,3%) | **0,864** | 185/600 (30,8%) | 0/600 (0,0%) |

### 5.2. Bảng So sánh Paired và Kiểm định Thống kê trên Cùng ID

| Dataset | Số mẫu (n) | Cả hai cùng đúng | Chỉ Libpostal đúng | Chỉ VNAdmin đúng | Cả hai cùng sai | McNemar $\chi^2$ | $p$-value |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Data 01 (Mới sạch)** | 1.000 | 2/1.000 (0,2%) | 0/1.000 (0,0%) | **971/1.000 (97,1%)** | 27/1.000 (2,7%) | 969,0 | $9,8 \times 10^{-213}$ |
| **Data 03 (Cũ sạch)** | 1.500 | 1/1.500 (0,1%) | 0/1.500 (0,0%) | **1.093/1.500 (72,9%)** | 406/1.500 (27,1%) | 1.091,0 | $3,0 \times 10^{-239}$ |
| **Data 04 (Thiếu Task A)**| 800 | 0/800 (0,0%) | 120/800 (15,0%) | **208/800 (26,0%)** | 472/800 (59,0%) | 23,08 | $1,56 \times 10^{-6}$ |

> [!NOTE]
> Các giá trị $p$-value đều nhỏ hơn $10^{-5}$, khẳng định sự khác biệt giữa hai công cụ trên các benchmark này là có ý nghĩa thống kê thực sự, không phải do ngẫu nhiên lấy mẫu.

---

## 6. Phân tích Lỗi theo Cơ chế (Error Taxonomy & Mechanisms)

Bảng phân bố lỗi chuẩn hóa trên toàn bộ 13.000 lượt dự đoán:

| Loại lỗi (Taxonomy) | Libpostal (n=5.900) | Tỷ lệ LP | VNAdmin (n=7.100) | Tỷ lệ VN | Trường bị ảnh hưởng chính | Bản chất và Bằng chứng Raw |
|---|---:|---:|---:|---:|---|---|
| `none` (Dự đoán đúng) | 127 | 2,2% | 4.355 | 61,3% | Tất cả | Không có lỗi. |
| `missing_field` | **3.876** | **65,7%** | **2.592** | **36,5%** | `PhuongXa`, `TenDuong`, `SoNha` | **[Được quan sát trực tiếp]** LP bỏ sót phường do gán thành `city`; VN bỏ sót số nhà chữ hoặc mất đường khi thiếu phẩy. |
| `hallucination_over_imputation` | **1.690** | **28,6%** | 54 | 0,8% | `QuanHuyen`, `SoNha` | **[Được quan sát trực tiếp]** LP adapter tự điền huyện ở hệ mới; LP lấy số ngõ làm số nhà ở D04; VN tự điền xã ở D04. |
| `parse_boundary_error` | 133 | 2,3% | 63 | 0,9% | `SoNha`, `TenDuong` | **[Được quan sát trực tiếp]** Cắt sai ranh giới giữa số nhà và tên ngõ/đường. |
| `abbreviation_misunderstood` | 74 | 1,3% | 24 | 0,3% | `PhuongXa`, `QuanHuyen` | **[Được quan sát trực tiếp]** Từ viết tắt như `P.`, `Q.`, `TX.` không nhận dạng được trong chuỗi nhiễu. |
| `wrong_target` | 0 | 0,0% | 12 | 0,2% | `PhuongXa` (Data 07) | **[Được quan sát trực tiếp]** Chuyển đổi sai đích trong cụm sáp nhập M-N. |

---

## 7. Danh sách Ca Minh họa Trực tiếp từ Output Thực nghiệm

Mọi ca dưới đây đều trích xuất trực tiếp từ `baseline_predictions_unified.csv` và truy vết từ `baseline_raw_responses.jsonl`.

### 7.1. 5 ca Libpostal sai tiêu biểu

1. **`D01_0000`** (Data 01 - Tự điền huyện, mất phường)
   - *Chuỗi vào:* `394, Đường Lý Thường Kiệt, Phường Phù Khê, Tỉnh Bắc Ninh`
   - *Đáp án:* `{"SoNha": "394", "TenDuong": "Đường Lý Thường Kiệt", "PhuongXa": "Phường Phù Khê", "QuanHuyen": "", "TinhThanh": "Tỉnh Bắc Ninh"}`
   - *LP Dự đoán:* `{"SoNha": "394", "TenDuong": "đường lý thường kiệt", "PhuongXa": "", "QuanHuyen": "phường phù", "TinhThanh": "tỉnh bắc ninh"}`
   - *LP Raw Labels:* `[["394", "house_number"], ["đường lý thường kiệt", "road"], ["phường phù", "city_district"], ["khê", "city"], ["tỉnh bắc ninh", "state"]]`
   - *Cơ chế lỗi:* **[Được quan sát trực tiếp]** Libpostal gán nhãn `"khê"` là `city`, adapter ánh xạ vào `QuanHuyen`, làm rỗng `PhuongXa`.
2. **`D01_0006`** (Data 01 - Phường Hà Nội bị nhận thành thành phố)
   - *Chuỗi vào:* `65, Phố Hàng Điếu, Phường Hoàn Kiếm, Thành phố Hà Nội`
   - *Đáp án:* `{"SoNha": "65", "TenDuong": "Phố Hàng Điếu", "PhuongXa": "Phường Hoàn Kiếm", "QuanHuyen": "", "TinhThanh": "Thành phố Hà Nội"}`
   - *LP Dự đoán:* `{"SoNha": "65", "TenDuong": "phố hàng điếu", "PhuongXa": "", "QuanHuyen": "hoàn kiếm", "TinhThanh": "phường thành phố hà nội"}`
   - *LP Raw Labels:* `[["65", "house_number"], ["phố hàng điếu", "road"], ["phường", "city"], ["hoàn kiếm", "state_district"], ["thành phố hà nội", "city"]]`
   - *Cơ chế lỗi:* **[Được quan sát trực tiếp]** Lỗi phân mảnh thực thể hành chính của Libpostal model.
3. **`D01_0007`** (Data 01 - Nhầm số đường thành số nhà)
   - *Chuỗi vào:* `10, Đường Nội Khu 02, Phường Tân Phú, Thành phố Hồ Chí Minh`
   - *Đáp án:* `{"SoNha": "10", "TenDuong": "Đường Nội Khu 02", "PhuongXa": "Phường Tân Phú", "QuanHuyen": "", "TinhThanh": "Thành phố Hồ Chí Minh"}`
   - *LP Dự đoán:* `{"SoNha": "10 02", "TenDuong": "đường nội khu", "PhuongXa": "", "QuanHuyen": "phường tân phú", "TinhThanh": "thành phố hồ chí minh"}`
   - *LP Raw Labels:* `[["10", "house_number"], ["đường nội khu", "road"], ["02", "house_number"], ["phường tân phú", "city_district"], ["thành phố hồ chí minh", "city"]]`
   - *Cơ chế lỗi:* **[Được quan sát trực tiếp]** Số `"02"` trong tên đường bị Libpostal gán nhầm thành `house_number` thứ hai và gộp vào số nhà.
4. **`D02_N00000_noisy`** (Data 02 - Nhiễu làm nuốt toàn bộ đường vào số nhà)
   - *Chuỗi vào:* `16 Phan Boi Chau, P. Le Hong Phong, TP. Quy Nhon, Binh Dinh`
   - *Đáp án:* `{"SoNha": "16", "TenDuong": "Phan Bội Châu", "PhuongXa": "Lê Hồng Phong", "QuanHuyen": "Quy Nhơn", "TinhThanh": "Bình Định"}`
   - *LP Dự đoán:* `{"SoNha": "16", "TenDuong": "phan boi chau", "PhuongXa": "", "QuanHuyen": "tp. quy nhon", "TinhThanh": "p. le hong phong"}`
   - *LP Raw Labels:* `[["16", "house_number"], ["phan boi chau", "road"], ["p. le hong phong", "state"], ["tp. quy nhon", "city"], ["binh dinh", "state"]]`
   - *Cơ chế lỗi:* **[Được quan sát trực tiếp]** Bỏ dấu và viết tắt khiến CRF gán nhãn nhầm phường thành `state`.
5. **`D04_0025`** (Data 04 - Ảo giác số nhà từ số ngõ)
   - *Chuỗi vào:* `Ngõ 85 Hạ Đình, Thanh Xuân Trung, Thanh Xuân, Hà Nội` (bị drop số nhà)
   - *Đáp án:* `{"SoNha": "", "TenDuong": "Ngõ 85 Hạ Đình", "PhuongXa": "Thanh Xuân Trung", "QuanHuyen": "Thanh Xuân", "TinhThanh": "Hà Nội"}`
   - *LP Dự đoán:* `{"SoNha": "85", "TenDuong": "ngõ hạ đình", "PhuongXa": "", "QuanHuyen": "thanh xuân", "TinhThanh": "hà nội"}`
   - *LP Raw Labels:* `[["ngõ", "road"], ["85", "house_number"], ["hạ đình", "road"], ...]`
   - *Cơ chế lỗi:* **[Được quan sát trực tiếp]** Libpostal bóc số ngõ thành số nhà khi địa chỉ khuyết số nhà bề mặt.

---

### 7.2. 5 ca VietnamAdminUnits sai tiêu biểu

1. **`D03_0000`** (Data 03 - Regex số nhà thất bại trên mã căn hộ Vinhomes)
   - *Chuỗi vào:* `NT02-29, Ngọc Trai 2, Đa Tốn, Gia Lâm, Hà Nội`
   - *Đáp án:* `{"SoNha": "NT02-29", "TenDuong": "Ngọc Trai 2", "PhuongXa": "Đa Tốn", "QuanHuyen": "Gia Lâm", "TinhThanh": "Hà Nội"}`
   - *VN Dự đoán:* `{"SoNha": "", "TenDuong": "Nt02 - 29, Ngọc Trai 2", "PhuongXa": "Xã Đa Tốn", "QuanHuyen": "Huyện Gia Lâm", "TinhThanh": "Thành phố Hà Nội"}`
   - *VN Raw Output:* `{"street": "Nt02 - 29, Ngọc Trai 2", "ward": "Xã Đa Tốn", "district": "Huyện Gia Lâm", "province": "Thành phố Hà Nội"}`
   - *Cơ chế lỗi:* **[Được quan sát trực tiếp]** Regex `^(\d+[\w\/\-]*)` thất bại vì số nhà bắt đầu bằng chữ `"N"`.
2. **`D03_0001`** (Data 03 - Lỗi tương tự trên mã biệt thự)
   - *Chuỗi vào:* `NT02-35, Ngọc Trai 2, Đa Tốn, Gia Lâm, Hà Nội`
   - *Đáp án:* `{"SoNha": "NT02-35", "TenDuong": "Ngọc Trai 2", ...}`
   - *VN Dự đoán:* `{"SoNha": "", "TenDuong": "Nt02 - 35, Ngọc Trai 2", ...}`
   - *Cơ chế lỗi:* **[Được quan sát trực tiếp]** Adapter không hỗ trợ số nhà dạng chữ-số.
3. **`D04_0000`** (Data 04 - Mất quận làm sụp đổ cấu trúc phẩy)
   - *Chuỗi vào:* `9, Ngách 1/88 Phạm Tuấn Tài, Phường Dịch Vọng Hậu, Hà Nội` (bị drop quận Cầu Giấy)
   - *Đáp án:* `{"SoNha": "9", "TenDuong": "Ngách 1/88 Phạm Tuấn Tài", "PhuongXa": "Phường Dịch Vọng Hậu", "QuanHuyen": "", "TinhThanh": "Hà Nội"}`
   - *VN Dự đoán:* `{"SoNha": "", "TenDuong": "9", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "Thành phố Hà Nội"}`
   - *VN Raw Output:* `{"address": "9, Thành phố Hà Nội", "street": "9", "ward": null, "district": null}`
   - *Cơ chế lỗi:* **[Được quan sát trực tiếp]** Mode `LEGACY` yêu cầu 3+ dấu phẩy để giữ street và ward; khi thiếu quận, parser cắt cụt toàn bộ chuỗi đường và phường.
4. **`D04_0003`** (Data 04 - Mất quận và viết tắt gây rỗng kết quả)
   - *Chuỗi vào:* `89, Hoa Lan, P.2, TP. HCM` (bị drop quận Phú Nhuận)
   - *Đáp án:* `{"SoNha": "89", "TenDuong": "Hoa Lan", "PhuongXa": "P.2", "QuanHuyen": "", "TinhThanh": "TP. HCM"}`
   - *VN Dự đoán:* `{"SoNha": "", "TenDuong": "89", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "Thành phố Hồ Chí Minh"}`
   - *Cơ chế lỗi:* **[Được quan sát trực tiếp]** Giảm số dấu phẩy kết hợp viết tắt `P.2` làm tê liệt parser dựa trên luật.
5. **`D07_0018_M-N`** (Data 07 - Chuyển đổi sai đích trong quan hệ M-N)
   - *Chuỗi vào:* `36, Phố Trần Phú, Phường Điện Biên, Quận Ba Đình, Hà Nội`
   - *Đáp án mới (OSM diff):* `{"PhuongXa": "Phường Ba Đình", "TinhThanh": "Thành phố Hà Nội"}`
   - *VN Dự đoán:* `{"PhuongXa": "Phường Hoàn Kiếm", "TinhThanh": "Thành phố Hà Nội"}`
   - *VN Raw Output:* `{"ward": "Phường Hoàn Kiếm", "province": "Thành phố Hà Nội"}`
   - *Cơ chế lỗi:* **[Được quan sát trực tiếp]** Bộ giải quyết đa trị (geocoder fallback) gán sai phường trong cụm sáp nhập chia tách.

---

### 7.3. 5 ca Libpostal đúng nhưng VietnamAdminUnits sai

Toàn bộ các ca này xảy ra ở **Data 04** (khi địa chỉ bị khuyết trường, làm sụp đổ cấu trúc phẩy của VNAdmin):

1. **`D04_0002`**
   - *Chuỗi vào:* `17-19, Đường Trần Lựu, Tỉnh Bắc Ninh` (khuyết phường xã)
   - *Đáp án:* `SoNha: "17-19", TenDuong: "Đường Trần Lựu", PhuongXa: "", TinhThanh: "Tỉnh Bắc Ninh"`
   - *Libpostal (ĐÚNG):* `SoNha: "17-19", TenDuong: "đường trần lựu", PhuongXa: "", TinhThanh: "tỉnh bắc ninh"`
   - *VNAdmin (SAI):* `SoNha: "17", TenDuong: "- 19", PhuongXa: "", TinhThanh: "Tỉnh Bắc Ninh"` (Raw street: `"17 - 19"`, regex cắt sai số nhà thành `17` và tên đường thành `- 19`).
2. **`D04_0006`**
   - *Chuỗi vào:* `Đường Mỹ Phú 1B, TPHCM` (khuyết số nhà và phường)
   - *Đáp án:* `SoNha: "", TenDuong: "Đường Mỹ Phú 1B", PhuongXa: "", TinhThanh: "TPHCM"`
   - *Libpostal (ĐÚNG):* `SoNha: "", TenDuong: "đường mỹ phú 1b", PhuongXa: "", TinhThanh: "tphcm"`
   - *VNAdmin (SAI):* `SoNha: "", TenDuong: "", PhuongXa: "", TinhThanh: "Thành phố Hồ Chí Minh"` (Mất hoàn toàn tên đường vì chỉ có 1 dấu phẩy).
3. **`D04_0012`**
   - *Chuỗi vào:* `A58, Đường Nội Khu 1, Thành phố Hồ Chí Minh`
   - *Đáp án:* `SoNha: "A58", TenDuong: "Đường Nội Khu 1", PhuongXa: "", TinhThanh: "Thành phố Hồ Chí Minh"`
   - *Libpostal (ĐÚNG):* `SoNha: "a58", TenDuong: "đường nội khu 1", PhuongXa: "", TinhThanh: "thành phố hồ chí minh"`
   - *VNAdmin (SAI):* `SoNha: "", TenDuong: "A58", PhuongXa: "", TinhThanh: "Thành phố Hồ Chí Minh"` (Mất tên đường, `A58` bị coi là tên đường).
4. **`D04_0020`**
   - *Chuỗi vào:* `04, Đường Số 21, Thành phố Hồ Chí Minh`
   - *Đáp án:* `SoNha: "04", TenDuong: "Đường Số 21", PhuongXa: "", TinhThanh: "Thành phố Hồ Chí Minh"`
   - *Libpostal (ĐÚNG):* Bóc tách chính xác 100% từng trường.
   - *VNAdmin (SAI):* `SoNha: "", TenDuong: "04"` (Mất tên đường do thiếu dấu phẩy phân cách cấp xã).
5. **`D04_0021`**
   - *Chuỗi vào:* `53, Đường Hoàng Quốc Việt, Thành phố Hà Nội`
   - *Đáp án:* `SoNha: "53", TenDuong: "Đường Hoàng Quốc Việt", PhuongXa: "", TinhThanh: "Thành phố Hà Nội"`
   - *Libpostal (ĐÚNG):* Bóc tách chuẩn xác.
   - *VNAdmin (SAI):* `SoNha: "", TenDuong: "53", PhuongXa: "Xã Dương Hòa"` (Ảo giác tự điền Xã Dương Hòa dù chuỗi không hề có).

---

### 7.4. 5 ca VietnamAdminUnits đúng nhưng Libpostal sai

Xảy ra phổ biến ở **Data 01** (địa chỉ mới chuẩn tắc):

1. **`D01_0001`**
   - *Chuỗi vào:* `19, Đường Hai Bà Trưng, Phường Võ Cường, Tỉnh Bắc Ninh`
   - *VNAdmin (ĐÚNG):* Khớp 100% cả 4 trường (không điền huyện).
   - *Libpostal (SAI):* Gán `"võ cường"` là `state_district` $\to$ adapter điền vào `QuanHuyen`, bỏ trống `PhuongXa`.
2. **`D01_0002`**
   - *Chuỗi vào:* `314, Nguyễn Văn Linh, Phường Tân Thuận, Thành phố Hồ Chí Minh`
   - *VNAdmin (ĐÚNG):* Bóc tách chuẩn xác hoàn toàn.
   - *Libpostal (SAI):* Nuốt cả cụm `"nguyễn văn linh phường tân thuận"` vào `TenDuong`.
3. **`D01_0003`**
   - *Chuỗi vào:* `105, Phố Lê Hồng Phong, Phường Ba Đình, Thành phố Hà Nội`
   - *VNAdmin (ĐÚNG):* Bóc tách chuẩn xác hoàn toàn.
   - *Libpostal (SAI):* Nuốt cả cụm `"phố lê hồng phong phường ba đình"` vào `TenDuong`.
4. **`D01_0004`**
   - *Chuỗi vào:* `59, Bành Văn Trân, Phường Tân Sơn Nhất, Thành phố Hồ Chí Minh`
   - *VNAdmin (ĐÚNG):* Bóc tách chuẩn xác hoàn toàn.
   - *Libpostal (SAI):* Gán nhãn cụm `"bành văn trân phường tân sơn nhất"` là `house`, làm mất tên đường và phường.
5. **`D01_0005`**
   - *Chuỗi vào:* `266, Phố Lương Định Của, Phường Phương Liễu, Tỉnh Bắc Ninh`
   - *VNAdmin (ĐÚNG):* Bóc tách chuẩn xác hoàn toàn.
   - *Libpostal (SAI):* Tự điền `QuanHuyen = "phường phương"`, bỏ trống `PhuongXa`.

---

### 7.5. 3 ca cả hai cùng sai

1. **`D03_0000`**
   - *Chuỗi vào:* `NT02-29, Ngọc Trai 2, Đa Tốn, Gia Lâm, Hà Nội`
   - *Lý do:* VNAdmin thất bại do regex số nhà chữ; Libpostal gán `"nt02-29 ngọc trai"` là đường và `"2"` là số nhà (cắt sai hoàn toàn ranh giới số nhà).
2. **`D03_0001`**
   - *Chuỗi vào:* `NT02-35, Ngọc Trai 2, Đa Tốn, Gia Lâm, Hà Nội`
   - *Lý do:* Tương tự `D03_0000`. Cả hai mô hình đều thất bại trước cấu trúc số nhà khu đô thị mới.
3. **`D03_0002`**
   - *Chuỗi vào:* `59, Khương Trung, Khương Trung, Thanh Xuân, Hà Nội` (Tên đường trùng tên phường)
   - *Đáp án:* `SoNha: "59", TenDuong: "Khương Trung", PhuongXa: "Khương Trung", QuanHuyen: "Thanh Xuân", TinhThanh: "Hà Nội"`
   - *VNAdmin (SAI):* `SoNha: "", TenDuong: "59"` (Trùng lặp tên khiến parser luật loại trừ nhầm thành phần đường).
   - *Libpostal (SAI):* Nuốt cả cụm `"khương trung khương trung thanh xuân"` vào `TenDuong`.

---

### 7.6. 3 ca cả hai cùng đúng (Easy Cases)

1. **`D01_0069`**
   - *Chuỗi vào:* `208/118, Hẻm 208 đường số 5, Phường Bình Hưng Hòa, Thành phố Hồ Chí Minh`
   - *Đáp án:* `SoNha: "208/118", TenDuong: "Hẻm 208 đường số 5", PhuongXa: "Phường Bình Hưng Hòa", QuanHuyen: "", TinhThanh: "Thành phố Hồ Chí Minh"`
   - *Kết quả:* Cả hai công cụ đều dự đoán khớp 100%. Libpostal gán chuẩn xác `"208/118"` là `house_number`, `"hẻm 208 đường số 5"` là `road`, `"phường bình hưng hòa"` là `suburb`, `"thành phố hồ chí minh"` là `city`.
2. **`D01_0819`**
   - *Chuỗi vào:* `801/7, Hẻm 801 Xô viết Nghệ Tĩnh, Phường Bình Thạnh, Thành phố Hồ Chí Minh`
   - *Kết quả:* Cả hai công cụ đều dự đoán chuẩn xác 100%. Cấu trúc phân cách phẩy rõ ràng, số nhà thuần xuyệt số, tên phường có từ khóa `"Phường"` được Libpostal nhận diện đúng `suburb`.
3. **`D03_1281`**
   - *Chuỗi vào:* `68b/1, Đường Cách Mạng Tháng Tám, An Thạnh, Thuận An, Bình Dương`
   - *Kết quả:* Cả hai công cụ đều dự đoán chuẩn xác 100% trên địa chỉ cũ 3 cấp chuẩn.

---

## 8. Kết luận So sánh theo 13 Năng lực Cốt lõi

Đánh giá được cấu trúc thống nhất theo định dạng: **Kết luận**, **Bằng chứng**, **Công cụ có lợi thế**, **Giới hạn**, **Mức độ chắc chắn**.

```text
1. Parse địa chỉ sạch
Kết luận: VietnamAdminUnits vượt trội trên địa chỉ sạch chuẩn tắc có đủ phân cấp; Libpostal đạt điểm rất thấp do lỗi gán nhãn hành chính và mapping adapter.
Bằng chứng: Data 01 exact match: VNAdmin 97,3% (973/1.000) vs Libpostal 0,2% (2/1.000); Data 03 exact match: VNAdmin 72,9% (1.094/1.500) vs Libpostal 0,1% (1/1.500).
Công cụ có lợi thế: VietnamAdminUnits.
Giới hạn: Kết quả của VNAdmin phụ thuộc vào việc được cung cấp trước mode phù hợp (Oracle mode).
Mức độ chắc chắn: [Được chứng minh trực tiếp]

2. Tách số nhà và tên đường
Kết luận: Libpostal linh hoạt hơn với số nhà phức tạp (chứa chữ, ngõ ngách, xuyệt); VietnamAdminUnits bị trói buộc bởi regex số nhà thuần số.
Bằng chứng: F1 số nhà Data 04: Libpostal 0,792 vs VNAdmin 0,006. Data 03: VNAdmin bỏ trống số nhà ở 284 ca do tiền tố chữ (NT02-29).
Công cụ có lợi thế: Libpostal.
Giới hạn: Libpostal đôi khi nhầm số thứ tự đường (Đường Số 21) thành số nhà nếu không có dấu phẩy.
Mức độ chắc chắn: [Được chứng minh trực tiếp]

3. Nhận diện phường/xã
Kết luận: VietnamAdminUnits nhận diện phường/xã cực tốt nhờ từ điển chuẩn hóa; Libpostal gần như tê liệt trên trường này do gán nhãn thành city.
Bằng chứng: F1 Phường/Xã Data 01: VNAdmin 1,000 vs Libpostal 0,004; Data 03: VNAdmin 0,915 vs Libpostal 0,006. 513/1.000 phường ở Data 01 bị Libpostal gán nhãn là city.
Công cụ có lợi thế: VietnamAdminUnits.
Giới hạn: VNAdmin chỉ nhận diện tốt khi tên phường có trong từ điển của mode đang chạy.
Mức độ chắc chắn: [Được chứng minh trực tiếp]

4. Nhận diện quận/huyện cũ
Kết luận: VietnamAdminUnits nhận diện quận/huyện cũ đạt độ chính xác gần như tuyệt đối; Libpostal chỉ đạt F1 rất thấp.
Bằng chứng: F1 Quận/Huyện Data 03: VNAdmin 0,977 vs Libpostal 0,073.
Công cụ có lợi thế: VietnamAdminUnits.
Giới hạn: Chỉ áp dụng cho địa chỉ hệ cũ chạy ở mode LEGACY.
Mức độ chắc chắn: [Được chứng minh trực tiếp]

5. Nhận diện tỉnh/thành
Kết luận: Cả hai công cụ đều nhận diện tỉnh/thành rất tốt, đây là trường ổn định nhất của Libpostal.
Bằng chứng: F1 Tỉnh/Thành Data 01: VNAdmin 1,000, Libpostal 0,938; Data 03: VNAdmin 0,983, Libpostal 0,826.
Công cụ có lợi thế: VietnamAdminUnits nhỉnh hơn nhẹ, nhưng Libpostal hoàn toàn cạnh tranh được.
Giới hạn: Libpostal đôi khi gán nhãn nhầm tỉnh thành là city thay vì state.
Mức độ chắc chắn: [Được chứng minh trực tiếp]

6. Khả năng chịu nhiễu (Robustness)
Kết luận: VietnamAdminUnits cực kỳ nhạy cảm và sụp đổ nhanh khi gặp nhiễu; Libpostal suy giảm F1 ít hơn xét về tỷ lệ tương đối.
Bằng chứng: Data 02 exact match của VNAdmin giảm từ 86,2% xuống 21,7% (giảm 74,8% số ca đúng); 169/181 ca nhiễu nặng bị sai. Nhiễu thiếu từ khóa làm độ chính xác về 0,0%.
Công cụ có lợi thế: Libpostal bền bỉ hơn về mặt kiến trúc chuỗi, dù điểm cơ sở thấp.
Giới hạn: Data 02 là nhiễu tổng hợp, chưa phản ánh toàn diện hóa đơn thực tế.
Mức độ chắc chắn: [Được chứng minh trực tiếp]

7. Xử lý thiếu trường
Kết luận: Libpostal giữ được khả năng bóc tách các thành phần còn lại tốt hơn khi chuỗi khuyết trường; VNAdmin bị lỗi phụ thuộc cấu trúc phẩy.
Bằng chứng: Data 04 Task A: Libpostal đúng 120 ca mà VNAdmin sai hoàn toàn (nhất là khi giữ số nhà). VNAdmin F1 số nhà rớt xuống 0,006.
Công cụ có lợi thế: Libpostal (trích xuất bề mặt).
Giới hạn: Cả hai đều có điểm toàn phần thấp trên dữ liệu thiếu trường (15% vs 26%).
Mức độ chắc chắn: [Được chứng minh trực tiếp]

8. Xử lý địa chỉ lai
Kết luận: Không công cụ nào xử lý đúng bản chất địa chỉ lai; VNAdmin chỉ đạt điểm ở mode LEGACY do ăn khớp hình thức với ground truth bề mặt.
Bằng chứng: VNAdmin mode FROM_2025 đạt 0/600 (0,0%) trên Data 06; mode LEGACY đạt 415/600 (69,2%). Libpostal đạt 2/600 (0,3%).
Công cụ có lợi thế: Tạm thời là VNAdmin mode LEGACY nếu chỉ xét bóc tách thành phần, nhưng không có giá trị phân loại lai.
Giới hạn: Cả hai công cụ đều thiếu cơ chế phát hiện xung đột niên đại.
Mức độ chắc chắn: [Được chứng minh trực tiếp]

9. Nhận thức thời kỳ (Temporal Awareness)
Kết luận: Cả hai công cụ hoàn toàn không có năng lực nhận thức thời kỳ tự động.
Bằng chứng: VNAdmin cần người dùng cấp mode trước; Libpostal là mô hình tĩnh phi thời gian.
Công cụ có lợi thế: Không công cụ nào có lợi thế.
Giới hạn: Tác vụ T1 đòi hỏi mô hình phân loại chuyên biệt.
Mức độ chắc chắn: [Được chứng minh trực tiếp]

10. Ánh xạ hành chính (Administrative Mapping)
Kết luận: Chỉ VietnamAdminUnits có năng lực này thông qua bộ chuyển đổi tích hợp; Libpostal không có chức năng ánh xạ.
Bằng chứng: Data 07: VNAdmin đạt 586/600 (97,7%) chuyển đổi đúng (99,2% trên N-1; 96,6% trên M-N).
Công cụ có lợi thế: VietnamAdminUnits (độc quyền trong so sánh này).
Giới hạn: Ghi nhận 12 ca sai đích im lặng ở quan hệ M-N do phụ thuộc mạng/geocoder.
Mức độ chắc chắn: [Được chứng minh trực tiếp]

11. Khả năng trả về kết quả bảo thủ
Kết luận: Cả hai công cụ đều có tính bảo thủ cao khi gặp trường bị xóa, tránh suy đoán bừa bãi.
Bằng chứng: Data 04 Task B: VNAdmin không điền 858/912 (94,1%) trường bị lược; Libpostal không điền 826/912 (90,6%).
Công cụ có lợi thế: VietnamAdminUnits nhỉnh hơn.
Giới hạn: Libpostal có xu hướng lấy số ngõ đắp vào số nhà (48 ca).
Mức độ chắc chắn: [Được chứng minh trực tiếp]

12. Khả năng tránh lỗi im lặng (Silent Error Avoidance)
Kết luận: Cả hai công cụ đều tạo ra lỗi im lặng ở mức độ cao.
Bằng chứng: Libpostal tự điền huyện giả ở 77,5% địa chỉ mới; VNAdmin trả về xã mới sai đích ở 3,4% ca M-N mà không có cờ cảnh báo.
Công cụ có lợi thế: Cả hai đều kém ở năng lực này.
Giới hạn: Cần cơ chế tính độ bất định (uncertainty estimation) ở các phiên bản sau.
Mức độ chắc chắn: [Được chứng minh trực tiếp]

13. Khả năng mở rộng sang schema 11 nhãn
Kết luận: Libpostal có kiến trúc phù hợp hơn để mở rộng sang schema 11 nhãn; VNAdmin bị giới hạn bởi cấu trúc AdminUnit cố định.
Bằng chứng: Libpostal vốn phân tách token dạng chuỗi (hỗ trợ thêm nhãn mới vào CRF/Perceptron); VNAdmin được lập trình cứng theo 4-5 thuộc tính phân cấp.
Công cụ có lợi thế: Libpostal (về mặt tiềm năng kiến trúc).
Giới hạn: Hiện tại Libpostal chưa được huấn luyện trên nhãn tiếng Việt 11 lớp.
Mức độ chắc chắn: [Suy luận hợp lý]
```

---

## 9. Phân biệt các Loại Kết luận (Epistemological Classification)

Nhằm duy trì tính nghiêm mật trong đánh giá khoa học, toàn bộ kết luận của báo cáo được phân định thành 3 nhóm rõ rệt:

### Nhóm A: Được chứng minh trực tiếp từ bằng chứng thực nghiệm (Directly Proven)
- VNAdmin đạt 97,3% exact match ở Data 01 khi được cung cấp trước mode `FROM_2025`.
- Libpostal đạt exact match 0,2% ở Data 01, trong đó có 775/1.000 ca bị adapter tự điền `QuanHuyen` và bỏ rỗng `PhuongXa`.
- Raw labels của Libpostal chỉ có 22/1.000 token phường xã được gán là `suburb`; 513 lần bị gán là `city` và 263 lần là `city_district`.
- Độ chính xác của VNAdmin sụt giảm 74,8% (từ 86,2% xuống 21,7%) khi gặp nhiễu tổng hợp Data 02.
- VNAdmin mode `FROM_2025` đạt chính xác 0/600 (0,0%) trên tập địa chỉ lai Data 06.
- VNAdmin converter đạt 97,7% trên Data 07, với 12 ca sai đích tập trung 100% tại các quan hệ chia tách phức hợp $M-N$.
- Tỷ lệ ngoại lệ (exception) và timeout của cả hai công cụ trên 13.000 lượt chạy là 0/13.000 (0,0%).

### Nhóm B: Suy luận hợp lý nhưng chưa chứng minh hoàn toàn (Reasonable Inference)
- Adapter của Libpostal được thiết kế dựa trên giả định của hệ hành chính phương Tây (nơi `city` tương đương đô thị cấp trung và `state` là cấp bang), dẫn đến việc ánh xạ sai lệch nghiêm trọng đối với đơn vị hành chính Việt Nam.
- Sự sụp đổ của VNAdmin ở Data 04 khi thiếu quận/huyện xuất phát từ quy ước cứng trong hàm `parse_address` yêu cầu tối thiểu 3 dấu phẩy ở mode LEGACY.
- 12 ca sai đích ở Data 07 có thể liên quan đến việc ArcGIS Geocoder không phân giải được số nhà trong ngõ hẻm hoặc địa chỉ mới, kích hoạt nhánh fallback mặc định.

### Nhóm C: Tuyệt đối KHÔNG được phép kết luận (Forbidden Conclusions)
- **Không được kết luận:** "VietnamAdminUnits có khả năng nhận diện hệ quy chiếu 2025 tốt hơn Libpostal", vì VNAdmin được cấp trước mode thời kỳ trong protocol (Oracle mode), chưa trải qua bài kiểm tra phân loại tự động T1.
- **Không được kết luận:** "Viết tắt hay bỏ dấu là nguyên nhân đơn lẻ làm giảm 60% độ chính xác của VNAdmin", vì trong Data 02, biến đổi dấu phân cách và các loại nhiễu khác luôn đồng xuất hiện.
- **Không được kết luận:** "Kết quả Data 07 đại diện cho khả năng chuyển đổi hành chính toàn quốc", vì 98,7% mẫu của Data 07 tập trung tại miền Bắc (Hà Nội, Bắc Ninh), không có mẫu miền Trung và chỉ có 1,3% mẫu miền Nam.
- **Không được kết luận:** "Libpostal thất bại trên bài toán T0 11 nhãn", vì benchmark hiện tại chỉ đánh giá trên 5 trường chuẩn hóa, chưa có ground truth span 11 lớp.

---

## 10. Điểm mạnh và Điểm yếu Cốt lõi của Từng Công cụ

### 10.1. Libpostal
- **Điểm mạnh:**
  - Kiến trúc học máy chuỗi (CRF/Perceptron) độc lập ngữ cảnh, mềm dẻo với các biến thể số nhà phức tạp (xuyệt, ký tự chữ).
  - Không bị ràng buộc bởi số lượng dấu phân cách phẩy cố định; giữ được các trường còn lại tốt hơn khi địa chỉ bị khuyết trường.
  - Tốc độ thực thi C cực nhanh, ổn định (0 exception trên 5.900 lượt chạy), tiêu tốn ít bộ nhớ.
  - Khả năng nhận diện Tỉnh/Thành phố đạt độ chính xác cao ($F1 > 0,82 - 0,93$).
- **Điểm yếu:**
  - Mô hình toàn cầu không hiểu hệ thống phân cấp hành chính đặc thù của Việt Nam; gán nhãn sai lệch giữa phường, quận và thành phố.
  - Hoàn toàn không có năng lực nhận thức thời kỳ hay ánh xạ sáp nhập 2025.
  - Thiếu từ điển thực thể hành chính nội địa, dẫn đến việc thường xuyên nuốt tên phường xã vào tên đường.

### 10.2. VietnamAdminUnits
- **Điểm mạnh:**
  - Tích hợp sẵn cơ sở dữ liệu phân cấp hành chính Việt Nam đa thời kỳ (chuẩn hóa 63 tỉnh thành cũ và 34 tỉnh thành mới 2025).
  - Độ chính xác bóc tách cực cao ($> 97\%$) trên địa chỉ sạch khi được cung cấp đúng mode hoạt động.
  - Có sẵn module chuyển đổi hành chính cũ $\to$ mới (`convert_address`) đạt độ chính xác $97,7\%$.
  - Tính bảo thủ cao ($94,1\%$), ít khi tự điền bừa các trường bị thiếu.
- **Điểm yếu:**
  - Phụ thuộc hoàn toàn vào cấu trúc dấu phân cách chuẩn tắc (yêu cầu nghiêm ngặt 2+ hoặc 3+ dấu phẩy); sụp đổ khi dấu phẩy bị xáo trộn.
  - Cực kỳ kém bền bỉ trước nhiễu chính tả, viết tắt, mất dấu, lỗi OCR hoặc khuyết từ khóa.
  - Bộ tách số nhà dựa trên regex thô sơ, bỏ sót toàn bộ số nhà có chữ cái đứng đầu.
  - Module chuyển đổi $M-N$ phụ thuộc vào geocoder mạng bên ngoài (ArcGIS), tiềm ẩn rủi ro sai lệch im lặng và thiếu khả năng tái lập nếu không có mạng.

---

## 11. Các Vấn đề Kỹ thuật Phát hiện trong Pipeline (Pipeline Issue Audit)

Trong quá trình kiểm toán mã nguồn phục vụ phân tích, đã phát hiện 3 vấn đề kỹ thuật cần được ghi nhận cho các giai đoạn phát triển tiếp theo:

### Vấn đề 1: Logic ánh xạ nhãn thô của Libpostal Adapter ép sai cấp hành chính
- **File:** `src/evaluation/adapters/libpostal_adapter.py`
- **Hàm:** `LibpostalAdapter.parse` (dòng 120–130)
- **Đoạn logic:**
  ```python
  province = tags.get("state", "") or tags.get("city", "")
  district = tags.get("state_district", "") or tags.get("city_district", "")
  if tags.get("state") and not district:
      district = tags.get("city", "")
  ```
- **Bằng chứng:** Ở Data 01, Libpostal gán `"khê"` là `city`, `"tỉnh bắc ninh"` là `state`. Đoạn code trên lập tức gán `"khê"` vào `district` (`QuanHuyen`), trong khi hệ 2025 không có huyện.
- **Ảnh hưởng:** Tạo ra 775 lỗi tự điền huyện giả, kéo F1 của Phường/Xã xuống 0,004 và bóp méo đánh giá bản chất của mô hình Libpostal.
- **Cách kiểm chứng:** Chạy thử nghiệm với adapter giữ nguyên `city` làm ứng viên cho `PhuongXa` khi mode là 2 cấp; F1 Phường/Xã sẽ tăng từ 0,004 lên trên 0,51.

### Vấn đề 2: Regex tách số nhà của VNAdmin Adapter bỏ sót số nhà chứa chữ
- **File:** `src/evaluation/adapters/vnadmin_adapter.py`
- **Hàm:** `_split_street_house_number` (dòng 23–26)
- **Đoạn logic:**
  ```python
  match = re.match(r"^(\d+[\w\/\-]*)(?:[,\s]+)(.*)$", s)
  ```
- **Bằng chứng:** Các chuỗi số nhà khu đô thị như `"NT02-29"`, `"BT01-12"` có ký tự đầu là chữ, không khớp `^\d+`.
- **Ảnh hưởng:** 284 dòng ở Data 03 bị rỗng số nhà, làm giảm điểm F1 số nhà của VNAdmin xuống 0,866 và gây ra 330 lỗi ranh giới đường.
- **Cách kiểm chứng:** Thay bằng regex hỗ trợ tiền tố chữ cái: `r"^([A-Za-z0-9]+(?:[\w\/\-]*))(?:[,\s]+)(.*)$"`.

### Vấn đề 3: Phụ thuộc Geocoder mạng ngoài trong Converter
- **File:** `third_party/vietnamadminunits/vietnamadminunits/converter/converter_2025.py` và `vietnamadminunits/parser/utils.py`
- **Hàm:** `convert_address_2025` (dòng 65) và `get_geo_location` (dòng 10–14 trong `utils.py`)
- **Đoạn logic:** Gọi `geolocator = ArcGIS()` qua HTTP request mà không có timeout chặt chẽ hay bộ đệm offline.
- **Bằng chứng:** Code gọi trực tiếp dịch vụ bên ngoài khi xử lý chia tách xã.
- **Ảnh hưởng:** Khi chạy ngắt mạng, converter sẽ âm thầm rơi vào nhánh `isDefaultNewWard`, tạo ra sai số không đồng nhất giữa các lần chạy.
- **Cách kiểm chứng:** Ngắt kết nối internet và chạy lại 12 ca lỗi M-N; kiểm tra xem kết quả có bị thay đổi sang giá trị mặc định hay không.

---

## 12. Hạn chế của Benchmark Hiện tại (Benchmark Limitations)

1. **Chưa đánh giá được bài toán T0 11 nhãn span:**
   Benchmark hiện tại chỉ đánh giá trên 5 trường địa chỉ chuẩn hóa ở mức bản ghi. Chưa có ground truth dạng span offsets (vị trí ký tự bắt đầu/kết thúc) theo schema 11 nhãn đề cương (`SoNha, TenDuong, Ngo/Hem, ToaNha/CanHo, PhuongXa, QuanHuyen, TinhThanh, MocDinhVi, HuongDi, GhiChu, Khac`).
2. **Thiếu vắng bài toán phân loại hệ quy chiếu tự động (T1):**
   Chưa có pipeline đánh giá năng lực của một mô hình khi phải tự xác định chuỗi địa chỉ thuộc hệ `cu`, `moi` hay `Lai` trước khi tiến hành bóc tách.
3. **Độ phủ địa lý của tập chuyển đổi (Data 07) bị lệch:**
   Tập 07 có 98,7% mẫu ở miền Bắc (73,5% Hà Nội, 25,2% Bắc Ninh), miền Nam chỉ có 1,3% (TP.HCM) và miền Trung hoàn toàn trống (0,0%). Chưa phản ánh được sự đa dạng của các quyết định sáp nhập trên toàn quốc.
4. **Tập Data 02 là nhiễu mô phỏng đồng xuất hiện:**
   Tần suất nhiễu được ước lượng từ 146 hóa đơn Viet-Receipt-VQA, nhưng việc áp dụng đồng thời nhiều phép biến đổi khiến việc phân tích nguyên nhân nhân quả của từng loại nhiễu bị hạn chế.

---

## 13. Khuyến nghị Bước Nghiên cứu Tiếp theo (Recommendations)

1. **Xây dựng Mô hình Baseline Học sâu Nội địa (PhoBERT / XLM-RoBERTa + CRF):**
   Thay vì phụ thuộc vào luật tĩnh của VietnamAdminUnits hay mô hình toàn cầu của Libpostal, cần huấn luyện một mô hình Sequence Labeling chuyên biệt cho tiếng Việt, được học trực tiếp trên dữ liệu địa chỉ có nhãn phân cấp và nhãn thời kỳ.
2. **Thiết kế Pipeline Hai Giai đoạn (Two-Stage Pipeline):**
   - *Giai đoạn 1 (T1 Classifier):* Phân loại chuỗi địa chỉ thuộc hệ cũ, hệ mới hay lai.
   - *Giai đoạn 2 (T0 Parser & T2 Resolver):* Dựa trên nhãn T1, áp dụng parser tương ứng (2 cấp hoặc 3 cấp) và kích hoạt bộ giải quyết sáp nhập nếu phát hiện địa chỉ cũ/lai.
3. **Mở rộng Gazetteer Đa phiên bản Offline:**
   Đóng gói toàn bộ đồ thị sáp nhập hành chính 2025 thành một cơ sở dữ liệu đồ thị offline (kèm tọa độ bounding box hoặc polygon của từng xã mới), loại bỏ hoàn toàn việc gọi API mạng ngoài (ArcGIS) để bảo đảm 100% khả năng tái lập khoa học.
4. **Gán nhãn Span chuẩn 11 nhãn:**
   Ứng dụng Label Studio để gán nhãn span offsets trên tập con đại diện và đo hệ số tin cậy Cohen's Kappa giữa các annotators, phục vụ đánh giá bài toán T0 đầy đủ.

---
*Báo cáo được hoàn thành độc lập và kiểm tra tính toàn vẹn 13.000 lượt dự đoán. Mọi bảng trung gian phục vụ kiểm chứng đã được lưu trữ có hệ thống tại `D:\DACN\data\processed\evaluation\comparative_analysis_tables\`.*
