# Data layout

- `raw/osm`: các snapshot và full-history PBF/OSH của OpenStreetMap.
- `raw/viet_receipt_vqa`: ba shard Parquet gốc của Viet-Receipt-VQA.
- `interim/osm`: dữ liệu OSM đã trích xuất hoặc cắt theo mốc thời gian.
- `interim/vqa`: địa chỉ hóa đơn sau lọc và khử trùng lặp mờ; `interim/viet_receipt` là bản trích cũ chỉ giữ để đối chiếu.
- `interim/annotation/sprint03`: queue/import/export Label Studio và báo cáo QA; đây là dữ liệu làm việc, có thể chứa chuỗi địa chỉ, không phát hành công khai.
- `processed/osm`: tập địa chỉ sạch và cặp ánh xạ hai chiều.
- `processed/benchmark`: các tập benchmark đã tạo lại bằng pipeline hiện tại. Tập 05 chưa có vì thiếu nguồn mốc.
- `processed/annotation/sprint03`: pilot gold T0 68 mẫu đã duyệt và manifest; 100 test T0 vẫn đang được giữ riêng, chưa có gold.
- `processed/gazetteer/s3_v1`: gói entity/edge/alias một phần với manifest/hash; mã cũ bên thứ ba là candidate chưa xác minh.
- `reference/administrative_units`: bảng sáp nhập và ánh xạ đơn vị hành chính.

Không chỉnh sửa trực tiếp dữ liệu trong `raw`; mọi kết quả dẫn xuất nên đi qua `interim` trước khi chuyển sang `processed`.

`vietnam-sap-nhap-phuong-xa.csv` là nguồn chuẩn của ánh xạ hành chính 2025. Mỗi dòng là một cạnh đầy đủ từ đơn vị cũ (tỉnh, quận/huyện, phường/xã) sang đơn vị mới; không được rút gọn thành từ điển tên phường. Đồ thị có thể chứa 1-1, 1-N, N-1 và M-N.

`interim/osm/osm_old_snapshot_full.csv` là snapshot đầy đủ trước 30/06/2025, dùng riêng để đối chiếu ID của OSM diff. `interim/osm/osm_old_snapshot_20250630.csv` là bản lấy mẫu cân bằng, chỉ dùng để sinh tập 03 và các dữ liệu dẫn xuất. Không thay thế file đầy đủ bằng file cân bằng khi audit hay sinh cặp quan sát trực tiếp.

Data 2 chính thức là `processed/benchmark/02_raw_noisy_synthetic_1000.csv`. File này được sinh từ địa chỉ OSM sạch đã xác minh, có chuỗi đầu vào nhiễu `ChuoiDiaChi`, chuỗi sạch `ChuoiDiaChiGoc`, nhãn gốc `GT_*`, mức/loại nhiễu, hệ quy chiếu và seed. Baseline chỉ được đọc `ChuoiDiaChi`; các cột `GT_*` chỉ dùng để chấm điểm. `interim/vqa/viet_receipt_raw_addresses.csv` giữ 146 hóa đơn thật làm nguồn ước lượng tần suất nhiễu và kiểm tra ngoài, không phải Data 2.

Tập 07 hiện có 600 cặp: 244 B/N-1 và 356 M/M-N, đều là quan sát OSM diff trực tiếp; không có mẫu C/1-1 hoặc A/1-N nên báo cáo coverage ghi rõ `0 mẫu (Thiếu bằng chứng)`. Cột `HinhThucSapNhap`, `MaPhuongXaMoi` và `Nguon` cho phép truy nguyên nguồn. Không dựng cặp A/1-N hoặc M/M-N chỉ từ snapshot vì không có hình học để biết địa chỉ nằm ở phần lãnh thổ nào. File `data/processed/evaluation/osm_diff_filter_audit.csv` ghi từng diff bị loại, giá trị alias đã dùng, trường chuẩn hóa và trạng thái bằng chứng hình học.
