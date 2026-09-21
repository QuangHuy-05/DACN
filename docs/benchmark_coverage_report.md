# Báo Cáo Độ Phủ Đa Chiều Benchmark Địa Chỉ Hành Chính 2025

**Tổng số mẫu đánh giá (Tập 07):** 600 cặp ánh xạ hai chiều đã xác minh.

---

## 1. Phân Bố Theo Bằng Chứng Nguồn (Evidence Source)

| Nguồn Dữ Liệu | Số lượng | Tỷ lệ (%) | Bản chất |
| :--- | :---: | :---: | :--- |
| `OSM_Diff+vietnam-sap-nhap-phuong-xa.csv` | 600 | 100.0% | Quan sát trực tiếp từ lịch sử thay đổi OSM |
| `OSM_Snapshot+vietnam-sap-nhap-phuong-xa.csv` | 0 | 0.0% | Dẫn xuất an toàn từ snapshot cũ có đúng 1 đích |

## 2. Phân Bố Theo Quan Hệ Đồ Thị Sáp Nhập (Relationship Graph)

| Quan Hệ | Tên gọi | Số lượng | Tỷ lệ (%) | Bằng chứng OSM diff | Ghi chú an toàn |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **1-1** | Đổi tên / giữ nguyên cấp (C) | 0 | 0.0% | 0 | Thiếu bằng chứng OSM diff |
| **N-1** | Hợp nhất nhiều xã vào một (B) | 244 | 40.7% | 244 | Quan sát đích thực tế |
| **1-N** | Tách một xã thành nhiều xã (A) | 0 | 0.0% | 0 | Thiếu bằng chứng OSM diff |
| **M-N** | Tái cơ cấu phức hợp nhiều-nhiều (M) | 356 | 59.3% | 356 | Quan sát đích thực tế |

## 3. Phân Bố Vùng Miền (Geographic Regions)

| Vùng Miền | Số lượng | Tỷ lệ (%) | Đặc điểm |
| :--- | :---: | :---: | :--- |
| **Bac** | 592 | 98.7% | Đại diện các tỉnh/thành vùng Bac |
| **Trung** | 0 | 0.0% | Đại diện các tỉnh/thành vùng Trung |
| **Nam** | 8 | 1.3% | Đại diện các tỉnh/thành vùng Nam |

## 4. Phân Bố Hình Học OSM (OSM Geometry)

| Đối tượng OSM | Số lượng | Tỷ lệ (%) | Vai trò |
| :--- | :---: | :---: | :--- |
| `node` | 202 | 33.7% | Điểm địa chỉ độc lập |
| `way` | 398 | 66.3% | Đối tượng OSM dạng way |

## 5. Phân Bố Hình Thức Sáp Nhập (Merger Forms)

| Hình thức sáp nhập | Số lượng | Tỷ lệ (%) |
| :--- | :---: | :---: |
| Hợp nhất toàn bộ | 244 | 40.7% |
| Tách — nhập chủ yếu | 335 | 55.8% |
| Tách — một phần | 21 | 3.5% |

## 6. Top Tỉnh / Thành Phố Đại Diện

| Tỉnh / Thành Phố | Số lượng | Tỷ lệ (%) |
| :--- | :---: | :---: |
| Thành phố Hà Nội | 441 | 73.5% |
| Tỉnh Bắc Ninh | 151 | 25.2% |
| Thành phố Hồ Chí Minh | 8 | 1.3% |

---

## 7. Cảnh Báo Chất Lượng & Ngưỡng Kiểm Soát (Quality Warnings)

> [!WARNING]
> Quan hệ 1-1 có 0 mẫu OSM diff trực tiếp (Thiếu bằng chứng). Không tạo thêm mẫu bằng suy đoán địa bàn.

> [!WARNING]
> Quan hệ 1-N có 0 mẫu OSM diff trực tiếp (Thiếu bằng chứng). Không tạo thêm mẫu bằng suy đoán địa bàn.

> [!WARNING]
> Độ phủ miền Trung chiếm tỷ lệ thấp (0/600, 0.0%) do mật độ đóng góp OSM tập trung tại Hà Nội và TP.HCM.

