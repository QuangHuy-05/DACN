# U1 — Xác minh mã cũ bằng danh mục NSO theo ngày

Lượt tiếp tục 03/10/2026. Evidence: `data/interim/modeling/sprint03/pre_colab_20261003_resume_v1/u1_v4/`. Đây là kết quả truy xuất thật; không dùng test100 hoặc thay corpus.

## Nguồn và phạm vi

- Nguồn chính: [SOAP Cục Thống kê](https://danhmuchanhchinh.nso.gov.vn/DMDVHC.asmx), POST ba operation `DanhMucTinh`, `DanhMucQuanHuyen`, `DanhMucPhuongXa`, `DenNgay=30/06/2025`, bộ lọc trống, toàn quốc. Request/response XML, thời điểm UTC, HTTP status, bytes và SHA-256 nằm trong `download_manifest.json`.
- Kiểm ngày: Hà Nội 526 xã ở 30/06/2025, 126 xã ở 01/07/2025. Chỉ chứng minh catalogue thay đổi theo ngày; không tự suy hiệu lực pháp lý.
- Đối chiếu cộng đồng: [vietnamese-provinces-database tag v2.4.1](https://github.com/thanglequoc/vietnamese-provinces-database/tree/v2.4.1), JSON và LICENSE được lưu/hash. MIT của repository này không thay thế điều khoản của nguồn chính thức.
- Hai CSV trong `third_party/vietnamadminunits/` được đọc nguyên trạng. Mã trong đó là candidate cho đến khi có exact full key và nguồn chính thức phù hợp.

API trả **63 tỉnh, 686 huyện, 9.843 xã**. Bản cộng đồng có **63/696/10.035**. Không bù số thiếu và không coi chênh lệch counts là bằng chứng giải thể.

## Kết quả đối chiếu toàn bộ entity cũ

| Cấp | Xác minh exact | Chưa xác minh |
| --- | ---: | ---: |
| Tỉnh | 62 | 1 |
| Huyện | 561 | 135 |
| Xã | 7.984 | 2.051 |
| Tổng | **8.607** | **2.187** |

`reconcile()` kiểm loại/tên có dấu, toàn bộ tỉnh–huyện–xã, hệ, ngày, code và cha. Chỉ NFC/khoảng trắng/chữ hoa được chuẩn hóa; không fuzzy promote, không sinh alias/cạnh. Entity chưa có mã chỉ nhận mã nếu full key trong nguồn duy nhất. Mã được giữ dạng chuỗi với zero đầu.

Nguồn chính thức có **1.429 row không vượt kiểm cha**: ví dụ huyện mang mã tỉnh không khớp mã của tên tỉnh trong catalogue cùng ngày. Có tên thể hiện loại đơn vị khác bản cũ. Những row này bị loại khỏi authority index, vẫn giữ nguyên trong reference và trace. Không sửa source bằng suy đoán. Đơn vị không tìm thấy full key hợp lệ ghi `NO_REFERENCE_AS_OF`, không kết luận đã đổi tên/giải thể. Năm huyện thiếu mã và các ca audit 615 trước đây đều có decision trong lần rà toàn bộ này.

## Artifact và tái lập

`reference_old.jsonl`, `reference_old.csv`, `reference_manifest.json`, `code_decisions.jsonl`, `unresolved.jsonl`, `reconciliation_report.json`, `nso_community_diff.json`, `responses/`.

```bash
python -m scripts.41_nso_dual_snapshot fetch --help
python -m scripts.41_nso_dual_snapshot publish --help
```

Chọn thư mục output mới khi chạy lại. Build replay response XML và so canonical/hash trước promotion; không tin decision CSV đã sửa tay. Các thư mục `u1`, `u1_v2`, `u1_v3` là lịch sử các lần gate từ chối/khác schema; `u1_v4` là evidence thành công hiện hành.

Giấy phép tái phân phối danh mục/CSV nguồn vẫn `PUBLIC_PORTAL_TERMS_NOT_LOCATED`. Quyền truy cập công khai và tính chính thức không đồng nghĩa quyền phát hành nguyên export lên Git public. Raw XML/reference mới được giữ local, chưa stage GitHub. Người dùng không cần điền tay 2.187 mã còn thiếu; cần nguồn lịch sử đủ cha/ngày để agent xử lý tiếp.
