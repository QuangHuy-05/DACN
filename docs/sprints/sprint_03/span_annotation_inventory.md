# Kiểm kê và chọn mẫu T0 11 span — batch 01

**Ngày:** 25/09/2026. **Seed:** `42`. **Trạng thái:** danh sách **ứng viên**, chưa phải gold. Chạy lại bằng `python -m scripts.10_prepare_span_annotation` trong WSL Python hoặc Python tương đương; script chỉ dùng thư viện chuẩn. Đầu ra nằm tại `data/interim/annotation/sprint03/`, không sửa benchmark frozen.

## 1. Nguồn đã kiểm kê

| Nguồn | Quy mô hiện có | ID/nhóm truy vết | Vai trò trong batch |
| --- | ---: | --- | --- |
| Benchmark 01, địa chỉ mới đã xác minh | 1.000 | Không có OSM ID trong CSV; dòng nguồn + hash + nhóm số nhà/đường | 20 ứng viên test T0 |
| Benchmark 02, nhiễu tổng hợp | 1.000 | `ID`, `ChuoiDiaChiGoc`, `GT_*`; nhóm từ cặp số nhà/đường gốc | 20 ứng viên test T0: 7 nhẹ, 7 vừa, 6 nặng |
| Benchmark 03, OSM cũ | 1.500 | `OSM_Type`, `OSM_ID`; nhóm số nhà/đường | 20 ứng viên test T0 |
| Benchmark 04, thiếu trường | 800 | `GT_*` và `KieuThieu`; nhóm theo giá trị gốc trước xóa | 20 ứng viên test T0: 5 cho mỗi kiểu thiếu |
| Benchmark 06, địa chỉ lai | 600 | `KieuLai`, `Span_He_Detail` (metadata, **không phải** gold T0); nhóm số nhà/đường | 20 ứng viên test T0: 10 C1, 5 C2, 5 C3 |
| Benchmark 07, cặp chuyển hệ | 600 cặp | `ID_Node` và hai bề mặt địa chỉ | Chỉ dùng để chặn trùng nhóm; chưa lấy vào T0 batch 01 |
| OSM snapshot cũ | 16.242 dòng | `OSM_Type:OSM_ID`; lọc trường đủ và khóa cũ có trong bảng hành chính | 24 pilot cũ, ngoài nhóm benchmark |
| OSM latest clean | 10.000 dòng | Dòng nguồn + hash; hệ mới chỉ nhận khi phường–tỉnh hiện hành đã xác minh hoặc khóa cũ có đúng **một** đích trong bảng hành chính | 24 pilot mới, ngoài nhóm benchmark |
| Viet-Receipt-VQA trung gian | 146 chuỗi duy nhất | Chỉ có `ChuoiDiaChi`; **không có ID hóa đơn/tài liệu** | 20 ứng viên external test, giữ chờ rà soát |
| Benchmark 05, địa chỉ mốc | 0 | Chưa có nguồn gold thật | Không có trong batch 01 |

VQA: kiểm tra từ khóa sơ bộ thấy 10 chuỗi có khả năng chứa mốc, 0 chuỗi có từ khóa `HuongDi` theo bộ lọc hiện tại; đây **không** phải số span gold. Bộ lọc đơn giản không thấy số điện thoại/email trong 146 chuỗi, nhưng không thay được kiểm tra quyền sử dụng và thông tin cá nhân bằng mắt. Bản CSV trung gian đã làm sạch và khử trùng lặp mờ; script sinh nó chỉ lưu `ChuoiDiaChi`, nên không thể khôi phục ID hóa đơn từ CSV này. Nếu cần truy lại ID, phải mở Parquet gốc ở môi trường có `pyarrow` và kiểm tra schema, không tự giả định các biến thể thuộc cùng hóa đơn.

## 2. Batch 01 đã chọn

| Vai trò | Thành phần | Số mẫu | Có thể import ngay? |
| --- | --- | ---: | --- |
| `pilot_train_pool` | 24 OSM cũ + 24 OSM mới xác minh + 20 ví dụ nhãn hiếm tổng hợp có kiểm soát | **68** | Có, chỉ là pilot để gán và sửa guideline |
| `frozen_benchmark_test_hold` | 20 mẫu từ mỗi tập 01/02/03/04/06 | **100** | Chưa; chỉ mở sau khi pilot và guideline được nghiệm thu |
| `external_test_hold` | 10 VQA có từ khóa ứng viên mốc + 10 VQA khác | **20** | Chưa; chờ kiểm tra riêng quyền sử dụng, dữ liệu cá nhân và nhóm tài liệu |
| **Tổng** | | **188** | |

Hai mươi ví dụ hiếm là các **cụm độc lập**, không ghép vào một địa chỉ OSM không liên quan. Gồm 6 ứng viên `MocDinhVi`, 6 `HuongDi`, 2 `ToaNha/CanHo`, 2 `GhiChu`, 2 `Khac`, 2 `Ngo/Hem`. Nguồn là [danh sách seed tổng hợp](../../../configs/span11_rare_seed_examples.json), dựa trên các ví dụ chủ dự án và các biến thể cú pháp có kiểm soát. Chúng chỉ phục vụ tập luyện quy tắc T0; **không** khẳng định một cặp địa chỉ–mốc cụ thể có vị trí địa lý đúng, không dùng làm chứng cứ T2 hoặc test thực địa. Bộ lọc nhãn hiếm chỉ dùng để chọn ứng viên; người gán phải tự xác nhận span.

## 3. Chống trùng và hợp đồng split

1. Tính `group_id` từ số nhà và tên đường đã chuẩn hóa cho mục đích **gom nhóm**, kể cả khi bề mặt bị nhiễu/thiếu trường. Ưu tiên `GT_SoNha`/`GT_TenDuong` khi có, vì chúng chỉ dùng tại bước chọn mẫu, không đưa cho người gán hoặc mô hình. Nhóm số nhà–đường không thêm tỉnh để tránh tách cùng điểm qua đổi tên tỉnh; cách này có thể gom dư một số địa chỉ giống tên ở hai nơi, nhưng an toàn hơn cho tách split.
2. Tập 07 được dùng làm danh sách chặn. Mọi nhóm của các benchmark 01/02/03/04/06/07 bị loại khỏi pilot/train pool. Không đưa cùng nhóm nguồn hoặc biến thể vào các split khác nhau. Các biến thể seed cùng mốc/hướng dùng chung `group_id` trong pilot.
3. Mỗi mẫu lưu `source_ref`, số dòng CSV gốc, SHA-256 file nguồn, `sample_id`, `group_id`, vai trò và dạng dẫn xuất. `sample_id` và `group_id` là hash; không chứa chuỗi địa chỉ thô. [Manifest JSON](annotation_batch01_manifest.json) ghi hash đầu vào/đầu ra và cảnh báo chưa giải quyết.
4. VQA chỉ có hash chuỗi làm khóa tạm. Toàn bộ được giữ trong external hold; không coi hash bề mặt là ID hóa đơn. Trước khi phát hành split chính thức, rà soát trùng gần và provenance ở cấp tài liệu.
5. Các mẫu benchmark test không được dùng để chọn quy tắc, sửa nhãn, tune model hay dựng từ điển. Chỉ mở sau khi guideline và cấu hình thực nghiệm đã khóa.

## 4. Tệp bàn giao

- [Guideline 11 nhãn](span_11_annotation_guideline.md): định nghĩa, ví dụ đúng/sai, `Khac/O`, hệ cũ/mới và quy tắc OCR.
- [`annotation_queue_batch01.csv`](../../../data/interim/annotation/sprint03/annotation_queue_batch01.csv): danh sách 188 ứng viên có provenance và vai trò; có nội dung VQA, không công bố ra ngoài trước rà soát.
- [`label_studio_pilot_import.json`](../../../data/interim/annotation/sprint03/label_studio_pilot_import.json): **chỉ 68 mẫu pilot**, không kèm GT, role, nguồn hay nhãn gợi ý trên giao diện.
- [`label_studio_span11.xml`](../../../configs/label_studio_span11.xml): cấu hình Label Studio cho 11 span, hệ từng span và hệ toàn câu. Sau khi có instance, tạo project với cấu hình này rồi import JSON pilot.
- [`annotation_batch01_manifest.json`](annotation_batch01_manifest.json): input/output hash, seed, số lượng và hạn chế; được lưu trong docs để xem lại dù `data/interim/` bị Git bỏ qua.

## 5. Cổng trước khi có gold và test hợp lệ

1. Gán 68 pilot; rà soát ca mơ hồ, sửa guideline nếu cần. Không chuyển 100 benchmark test sang gán trước khi quy tắc đã khóa.
2. Có người gán thứ hai trên tập giao nhau để đo Cohen's Kappa token-level và exact-span F1. Nếu chỉ có một người, ghi `NOT_MEASURED` cho inter-annotator agreement. Người gán lặp lại chỉ cho phép đo intra-annotator, phải gọi đúng tên.
3. Rà soát 20 VQA: loại mọi dữ liệu cá nhân, kiểm quyền sử dụng và đối chiếu ID tài liệu nếu có trong raw Parquet. VQA là external test riêng, không trộn vào train.
4. Thu thêm **mẫu `HuongDi` thật** từ nguồn công khai có provenance, giấy phép, ngày truy cập và khóa nguồn; hiện chưa có đủ để báo F1 nhãn này trên dữ liệu thật. Được phép thu thập nguồn mới theo quyết định của chủ dự án, nhưng mọi nguồn mới vẫn phải qua kiểm tra quyền sử dụng và loại thông tin cá nhân. OSM là nguồn mở ODbL, cần ghi công khi tái sử dụng dữ liệu; xem [trang giấy phép OSM](https://www.openstreetmap.org/copyright).
5. Sau khi nghiệm thu, xuất span gold và kiểm offset, nhãn, hệ, overlap, trùng nhóm, hash split. Chỉ sau đó huấn luyện các baseline T0 và mô hình đề xuất.

**Lưu ý:** batch 01 là bước chuẩn bị gán nhãn, chưa hoàn thành bộ corpus 11 span và chưa có phép đo F1 T0.
