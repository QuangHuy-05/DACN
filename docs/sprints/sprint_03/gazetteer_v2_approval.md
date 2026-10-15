# Hồ sơ kiểm toán Gazetteer v2 (phát hành một phần)

**Phiên bản gói:** `s3-gazetteer-v2-partial`
**Ngày cập nhật:** 30/09/2026
**Thư mục lưu trữ:** `data/processed/gazetteer/s3_v2/`
**Trạng thái dữ liệu:** `PARTIAL_OLD_CODES_UNVERIFIED`. Mã xã mới khớp 100% với CSV ánh xạ trong repository; chưa có URL ấn phẩm gốc hoặc giấy phép tái sử dụng của CSV này trong sổ nguồn. Mã xã cũ chỉ là ứng viên từ bên thứ ba.

---

## 1. Sổ Đăng ký Nguồn (Source Register)

| Mã nguồn (`source_id`) | Tài liệu | Vai trò dữ liệu | Bằng chứng còn thiếu |
| :--- | :--- | :--- | :--- |
| `official_mapping_2025` | CSV ánh xạ `vietnam-sap-nhap-phuong-xa.csv` | Cạnh cũ→mới và mã xã mới theo bảng dự án | URL bản gốc, cơ quan phát hành, giấy phép và kỳ hiệu lực chưa được lưu trong repo. Tên ID nguồn là di sản; tự nó không chứng minh thẩm quyền pháp lý. |
| `legacy_candidate` | CSV VietnamAdminUnits | Mã cũ ứng viên | Nguồn nhà nước và quyền dùng chưa được xác minh. |
| `audited_aliases` | `src/data/administrative_alias.py` | Alias kiểm toán nội bộ | Không phải nguồn mã hành chính. |

---

## 2. Báo cáo Thống kê và Độ phủ (Coverage Report)

- **Tổng số thực thể:** **14.149**
  - Tỉnh/Thành phố cũ: 63
  - Quận/Huyện/Thị xã cũ: **696**, gồm 5 huyện đảo được bổ sung để tra lookup chuyển đổi phi nguyên tử
  - Phường/Xã cũ: 10.035
  - Tỉnh/Thành phố mới: 34
  - Phường/Xã mới: 3.321
- **Trạng thái Mã Hành chính (Code Status):**
  - **Mã phường/xã mới:** 3.321 / 3.321 có mã khớp CSV ánh xạ nội bộ (`verified_source` trong schema); trạng thái này chưa xác nhận nguồn pháp lý bên ngoài.
  - **Mã phường/xã cũ:** 0 / 10.035 verified (0%); 10.035 mang `candidate_third_party_unverified` (**100% ứng viên chưa có văn bản nguồn chuẩn**).
- **Cạnh Nguyên tử (Atomic Old $\to$ New Edges):** 10.597 cạnh
  - `B/N-1` (Gộp): 9.432 cạnh (89,0%)
  - `M/M-N` (Phức hợp): 1.030 cạnh (9,7%)
  - `C/1-1` (Bảo toàn/Đổi tên): 132 cạnh (1,2%)
  - `A/1-N` (Tách): 3 cạnh (0,03%)
- **Chuyển đổi phi nguyên tử:** 5 huyện đảo (Bạch Long Vĩ, Côn Đảo, Hoàng Sa, Lý Sơn, Cồn Cỏ) chuyển thành đặc khu. Bảng riêng có `old_entity_id`/`new_entity_id`; lookup cấp huyện trả chuyển đổi cùng nguồn, không tạo cạnh cấp xã giả.
- **Alias đã audit:** **187** cặp sau khi loại alias trùng tên chính và trùng chuẩn hóa, khớp v1.
- **Ví dụ lookup:** `lookup_examples.json` ghi ca trùng tên, quan hệ 1-N/M-N, mốc ngày và huyện đảo.

---

## 3. Danh mục Hồ sơ Nguồn Cần Chủ Dự án Phê duyệt / Cung cấp

> [!WARNING]
> Để nâng mức tin cậy, chủ dự án cần cung cấp/chốt (1) danh mục mã xã cũ từ cơ quan nhà nước có ngày hiệu lực, khóa tỉnh–huyện–xã và quyền sử dụng; (2) URL ấn phẩm gốc, cơ quan phát hành và điều kiện tái sử dụng của CSV ánh xạ mới. Sau đó đối chiếu từng khóa và tạo phiên bản mới; không sửa mã ứng viên thành mã chuẩn bằng khớp mờ.

---

## 4. Tính toàn vẹn

Hash từng tệp đầu ra nằm trong [`manifest.json`](../../../data/processed/gazetteer/s3_v2/manifest.json). SHA-256 của manifest sau đợt review: `fb350c06b3a3d1dca9ceb6de65695fa533ac20ea3bda3f1abd8465951f8646d9`. Không gọi hồ sơ này là phê duyệt mã cũ hoặc xác nhận quyền dùng nguồn ngoài.
