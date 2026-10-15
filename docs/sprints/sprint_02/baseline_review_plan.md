# Rà soát kế hoạch đánh giá baseline (17/09/2026)

## Kết luận

Chưa thể duyệt kết quả hiện tại như phép đo **Libpostal và VietnamAdminUnits** có giá trị báo cáo chính thức. Sáu CSV đầu vào đều đọc được, đúng cột/số dòng, UTF-8 BOM và SHA-256 trong `run_manifest.json`; các lỗi chính nằm ở định nghĩa phép đo, scorer và phần diễn giải báo cáo. Giữ các file kết quả hiện tại làm bản chạy thử, không dùng các tỷ lệ của chúng để kết luận năng lực Libpostal.

## Kết quả kiểm tra dữ liệu đầu vào

| Tập | Dòng | Kiểm tra định dạng | Vấn đề cần xử lý trước khi chấm |
| --- | ---: | --- | --- |
| 01 | 1.000 | Đúng cột, BOM, hash; không trùng chuỗi | Xác nhận phạm vi là địa chỉ mới đã xác minh, không suy rộng sang toàn quốc. |
| 02 | 1.000 | Đúng cột, BOM, hash; ID duy nhất; chuỗi nhiễu khác chuỗi gốc | `dinh_dang_phan_cach` có trong 1.000/1.000 dòng và thường đi cùng nhiễu khác; các nhóm nhiễu trong báo cáo không phải tác động riêng lẻ. |
| 03 | 1.500 | Đúng cột, BOM, hash; không trùng chuỗi | Có 544 dòng thiếu `SoNha`, 127 thiếu `PhuongXa`, 87 thiếu `QuanHuyen`, 11 thiếu `TinhThanh`. Không mô tả cả tập là địa chỉ cũ đầy đủ. |
| 04 | 800 | Đúng cột, BOM, hash; các trường được chỉ định đều đã bị bỏ khỏi chuỗi | Có 107 `drop_district`, 302 `drop_housenumber`, 94 `drop_housenumber_ward`, 297 `drop_ward`. Phải chấm trích xuất theo trường còn trong chuỗi và chấm phục hồi theo `GT_*` riêng. |
| 06 | 600 | Đúng cột, BOM, hash | Có 2 chuỗi lặp giữa C2 và C3 với nhãn thời kỳ khác nhau. Cần loại hoặc xác minh lại các ca có bề mặt trùng mà nhãn khác. |
| 07 | 600 | Đúng cột, BOM, hash; 600 `ID_Node` duy nhất; 244 N-1 và 356 M-N | Chuỗi đầu số nhà/đường giữ nguyên giữa hai vế theo phép kiểm tra tiền tố; tuy nhiên scorer hiện bỏ `SoNha` trong đáp án được tạo từ `DiaChi_Moi`. |

Kiểm tra bằng PowerShell đọc CSV và tính hash, không chạy lại generator. Bộ dữ liệu 07 tập trung ở miền Bắc (592/600), không có 1-1/1-N; xem `docs/benchmark_coverage_report.md`.

## Các lỗi phương pháp và triển khai cần sửa

1. `src/evaluation/adapters/libpostal_adapter.py` là thuật toán regex do dự án viết, không gọi Python binding `postal` hay thư viện Libpostal C. Việc đặt tên `libpostal`, `CRF Parser` và suy luận về trọng số CRF trong báo cáo là không có căn cứ. Chỉ báo cáo Libpostal khi đã chạy thư viện thật; nếu giữ bộ hiện tại thì đổi tên thành **heuristic mô phỏng** và tách khỏi so sánh chính.
2. `scripts/06_run_baseline_full.py` chọn `mode` từ `HeQuyChieu` ở Data 02/04, và từ tên tập ở Data 01/03. Đây là phép đánh giá parser **đã được cung cấp hệ quy chiếu**, không phải nhận diện T1 tự động hay phép chạy hoàn toàn chỉ nhận chuỗi. Cần nêu rõ protocol và không gọi là `zero-leakage` theo nghĩa chỉ có chuỗi đầu vào.
3. Data 04 đang dùng toàn bộ `GT_*` để chấm trích xuất, nên trường cố ý bị xóa luôn thành false negative. Dùng cột bề mặt `SoNha`…`TinhThanh` cho tác vụ trích xuất; dùng `GT_*` cho tác vụ suy phục riêng. Điền giá trị cho trường bị xóa không mặc nhiên là bịa; phân biệt đúng, sai và không điền.
4. `scripts/06_run_baseline_full.py` tạo truth Data 07 bằng `DiaChi_Moi.split(',')` và không điền `SoNha`. Có 523/600 dự đoán VietnamAdminUnits có số nhà bị gắn `hallucination_over_imputation` chỉ vì truth trống. Tạo truth có cấu trúc từ cột nguồn/snapshot đã xác minh hoặc chấm duy nhất cặp `PhuongXa` + `TinhThanh` cho T2. Không dùng `DungSai` năm trường hiện tại để đánh giá chuyển đổi.
5. `src/evaluation/scorer.py` gộp dự đoán sai giá trị thành một FP, không tính FN tương ứng; F1 và phân loại lỗi vì vậy thiếu nhất quán. `LoaiLoi` chỉ giữ một loại dù một dòng có thể vừa bỏ sót vừa điền sai. Cần định nghĩa rõ exact match, micro/macro F1 theo trường, coverage, abstention và lỗi nhiều nhãn; giữ bảng 9 cột nếu cần, thêm JSON chi tiết hoặc bảng phụ.
6. `docs/baseline_evaluation_report.md` khẳng định chiều Mới → Cũ `UNSUPPORTED` nhưng `baseline_predictions_unified.csv` có **0** dòng `UNSUPPORTED`; runner không hề gọi chiều này. Nếu API không có chiều ngược, ghi `not evaluated / capability absent` dựa trên API, không đưa vào tỷ lệ thực nghiệm.
7. `src/evaluation/reporter.py` nhúng số liệu, nguyên nhân và bảng ví dụ A–D tĩnh trong mã. Một số số liệu được tính động, nhưng diễn giải không tự cập nhật và bảng ví dụ không truy vết bằng ID. Cần sinh mọi con số/ca từ kết quả có ID, phân biệt quan sát với giả thuyết nguyên nhân.
8. Manifest ghi cứng phiên bản công cụ, chưa lưu phiên bản package thực, commit/hash mã adapter, tham số chạy, trạng thái lỗi và hash output. `convert_address` của bản `third_party` có thể gọi ArcGIS geocoder qua mạng ở ca phân tách, nên kết quả có thể đổi theo dịch vụ. Ghi nhận hoặc cố định phụ thuộc này, và tách lỗi mạng/timeout khỏi sai ánh xạ.

## Kế hoạch chạy lại theo thứ tự

### Cổng 1 — Khóa hợp đồng dữ liệu và thí nghiệm

- Kiểm tra tự động sự tồn tại, cột, UTF-8 BOM, hash, ID/chuỗi trùng, giá trị nhãn, các trường bắt buộc theo **từng tập**, tính nhất quán `GT_*` và cặp Data 07.
- Giải quyết 2 chuỗi C2/C3 trùng của Data 06; Data 03 chia `đủ 5 trường` và `thiếu tự nhiên`, hoặc đổi mô tả tập và báo cáo theo tầng.
- Chốt nhiệm vụ riêng: T0 parsing 5 trường quan sát được; T1 phân loại `cu/moi/Lai` chỉ khi có bộ phân loại; T2 chuyển đổi cũ → mới. Schema 11 span của đề cương chưa có ground truth span nên không được báo cáo F1 T0 theo 11 nhãn.

### Cổng 2 — Chạy công cụ thật và lưu bằng chứng

- Dùng Libpostal thật qua `postal.parser.parse_address` trên WSL sau khi có môi trường phù hợp; ghi rõ model/data version và phép ánh xạ label Libpostal → 5 trường. Nếu chưa khả thi, loại khỏi báo cáo Libpostal và giữ mô phỏng như baseline heuristic riêng.
- VietnamAdminUnits chạy ở chế độ có `oracle mode` cho 01/02/03/04; 06 chạy cả hai mode và báo cáo riêng; 07 chỉ dùng `convert_address` cho cũ → mới. Không đối chiếu parser Libpostal với converter VietnamAdminUnits như cùng một năng lực chuyển đổi.
- Lưu raw output, status `success/none/exception/timeout`, mode, thời gian, bản cài thực, và ID nguồn ổn định. Nếu chuyển đổi gọi geocoder ngoài, lưu trạng thái mạng và kết quả vị trí/nguồn theo khả năng API cung cấp.

### Cổng 3 — Sửa scorer và pilot phân tầng

- Data 02: cặp sạch/nhiễu cùng ID, so sánh exact match và F1; báo cáo nhóm nhiễu **đồng xuất hiện**, và nếu muốn hiệu ứng riêng phải sinh tập ablation từng phép biến đổi.
- Data 04: hai ma trận độc lập cho trích xuất trường hiện diện và phục hồi trường bị bỏ; báo cáo điền đúng/sai/không điền. Data 06: đối chiếu 5 trường bề mặt và nhãn thời kỳ từng span, không suy ra khả năng cảnh báo mâu thuẫn nếu API không trả cảnh báo.
- Data 07: chấm `(PhuongXa, TinhThanh)` và đích theo `MaPhuongXaMoi` nếu công cụ xuất mã; phân loại trả rỗng, sai đích có output, lỗi parser, lỗi dịch vụ. Không gọi mọi mismatch là `silent_error` nếu chưa kiểm tra trạng thái cảnh báo.
- Pilot tối thiểu theo từng hệ, mức nhiễu, kiểu thiếu, C1/C2/C3 và N-1/M-N; soát thủ công mẫu lỗi và so sánh raw output với unified output trước full run.

### Cổng 4 — Full run và phát hành báo cáo

- Xác nhận manifest đầu vào trước chạy; 5.500 **dòng benchmark** tạo 13.600 **lượt dự đoán** theo protocol hiện tại, nhưng số lượt có thể đổi khi bỏ các phép so sánh khác nhiệm vụ.
- Chạy tests về schema, mapping adapter, scorer thay thế FP+FN, Data 04, Data 07 có/không số nhà, exception/timeout, bất biến hash; sau đó chạy full một lần và kiểm tra số dòng, unique key, raw log, JSON hợp lệ và hash output.
- Báo cáo số liệu động kèm mẫu số, ID dòng minh họa, giới hạn độ phủ vùng và bộ dữ liệu; xóa các khẳng định CRF, `UNSUPPORTED` thực nghiệm và nguyên nhân không kiểm chứng. Giữ bản chạy cũ với nhãn **pilot không dùng để kết luận**.

## Điều kiện duyệt cuối

Chỉ duyệt khi (1) công cụ được gọi đúng danh tính và có phiên bản thực, (2) mỗi phép đo có input/truth tương ứng với nhiệm vụ, (3) pilot đã soát lỗi, (4) raw log và số liệu báo cáo tái tạo được từ output, và (5) báo cáo không suy rộng ngoài độ phủ benchmark.

WSL trong phiên rà soát này trả `E_ACCESSDENIED`; chưa chạy lại unittest hoặc baseline. Các kết luận trên dựa vào kiểm tra mã và dữ liệu hiện hữu, cộng với kiểm tra CSV/hash bằng PowerShell.

## Trạng thái triển khai sau rà soát

Theo yêu cầu tiếp theo của người dùng, các cổng đã được thực hiện trong WSL:

- Cổng dữ liệu: Data 06 được tái sinh còn 600 chuỗi duy nhất; cả sáu CSV qua kiểm tra cột, số dòng, BOM, hash, nhãn và Data 07 khớp mã/tên/tỉnh trong bảng hành chính chuẩn.
- Cổng công cụ: Libpostal C chính thức commit `25099c506612b34b23b1bfe286ca6321fcf06f35`, model mặc định và Python binding `postal==1.1.11` đã cài; VietnamAdminUnits `1.0.4`. Raw nhãn Libpostal được lưu trước khi ánh xạ sang 5 trường.
- Cổng pilot: 20 dòng phân tầng mỗi tập, 280 lượt dự đoán và raw response, không có exception.
- Cổng full: 5.500 dòng benchmark, 13.000 lượt dự đoán, 13.000 raw response, 0 exception; hash output khớp manifest. Data 07 chỉ chấm converter VietnamAdminUnits theo phường/xã và tỉnh/thành.
- Cổng hồi quy và báo cáo: 25/25 tests qua; `docs/baseline_evaluation_report.md` được sinh từ output, script từ chối output đổi hash.

Giới hạn còn lại là độ phủ Data 07 chưa có 1-1/1-N và lệch miền Bắc, Data 05 chưa có nguồn, T0 11 span/T1 tự động/chuyển đổi ngược chưa được đánh giá, và converter có thể phụ thuộc ArcGIS geocoder qua mạng. Đây là giới hạn của phép đo, không phải lỗi định dạng CSV.

### Chuẩn hóa luồng dữ liệu Data 03 và Data 04

Đã hoàn thành sửa đổi và khóa chặt hợp đồng dữ liệu:
- **Data 03**: Chuyển thành benchmark sạch hoàn toàn của hệ cũ: 1.500 dòng lấy mẫu từ 8.848 dòng sạch trong snapshot; 100% có đủ 5 trường (`SoNha`, `TenDuong`, `PhuongXa`, `QuanHuyen`, `TinhThanh`), 0 dòng thiếu tự nhiên.
- **Data 04**: Chuyển thành benchmark thiếu trường có kiểm soát: 800 dòng (400 cũ, 400 mới) sinh từ các frame sạch `old_complete` và `new_complete`. Chỉ các trường chỉ định bởi `KieuThieu` mới bị xóa; `GT_*` được bảo toàn nguyên vẹn giá trị ban đầu. `QuanHuyen` rỗng ở hệ mới là cấu trúc hai cấp, không tính là lỗi.
- **Data contract & Tests**: Bổ sung hàm `validate_clean_source`, `validate_missing_surface`, nâng cấp `validate_benchmarks` và thêm 8 unit tests kiểm định tính sạch, bảo toàn GT, cấu trúc 2 cấp và từ chối nguồn lỗi. Toàn bộ 34 tests kiểm thử hồi quy đều đạt.
