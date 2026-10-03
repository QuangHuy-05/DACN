# Đối chiếu nguồn NSO và phát hành Gazetteer snapshot 2025 — 03/10/2026

## Kết quả

Đã lấy và xác minh một export có ngày tham chiếu rõ ràng từ [Cổng đối chiếu đơn vị hành chính của Cục Thống kê](https://danhmuchanhchinh.nso.gov.vn/Doi_Chieu_Moi.aspx). Export so sánh **30/06/2025 với 01/07/2025**, lọc cấp xã. Cổng có [hướng dẫn tra cứu và xuất Excel](https://danhmuchanhchinh.nso.gov.vn/HDSD_DMHC_Web.htm). [Quyết định 19/2025/QĐ-TTg bản ký](https://datafiles.chinhphu.vn/cpp/files/vbpq/2025/7/19ttg.signed.pdf) là văn bản pháp lý liên quan; bảng trong lượt này được lấy từ export NSO, không chép lại thủ công từ PDF.

Đã phát hành bản dẫn xuất mới `s3-gazetteer-v3-nso-2025-snapshot-partial` tại `data/processed/gazetteer/s3_v3_nso_2025_snapshot/`. `s3_v1`, `s3_v2`, benchmark, corpus, các run baseline và nhãn không bị sửa.

| Kiểm tra | Kết quả |
| --- | ---: |
| Dòng cấp xã phía đối chiếu, hiệu lực 01/07/2025 | 3.321 |
| Mã xã/phường duy nhất, khớp từng mã với bảng ánh xạ repo | 3.321/3.321 |
| Mã cấp tỉnh duy nhất trong export | 34/34 |
| Ghép đúng tỉnh cha theo export | 3.321/3.321 |
| Mã mới được chứng minh trong gói s3_v3 | 3.355 (34 tỉnh + 3.321 xã/phường) |
| Mã xã/phường cũ được xác minh bởi export này | 0 |
| Sai khác cách ghi tên xã giữa export và CSV repo | 17; giữ hai dạng theo mã, không tự sửa tên/alias |

File hiện tại của cổng còn có 22 dòng đổi sau mốc 2025 ở phía danh mục live. **Chỉ cột phía so sánh có ngày hiệu lực 01/07/2025 được nhập**; phía live 2026 bị loại. Package đặt `snapshot_only=true`; lookup chỉ chấp nhận ngày `2025-07-01`, ngày khác trả `OUT_OF_SNAPSHOT_SCOPE`. Đây là snapshot, không phải lịch sử thay đổi liên tục.

## Nguồn và dấu vết

- Trang xuất: `https://danhmuchanhchinh.nso.gov.vn/Doi_Chieu_Moi.aspx` — cơ quan thống kê nhà nước, export Excel lấy ngày 03/10/2026.
- Truy vấn: cấp `Xã`, ngày mới `2025-07-01`, ngày cũ `2025-06-30`; thao tác xuất Excel của cổng.
- File tải: `data/interim/modeling/sprint03/nso_official_crosswalk_2025_20261003_v1/nso_administrative_comparison_2025-06-30_to_2025-07-01.xls`.
- SHA-256 file `.xls`: `976f0aa4f40c97189dec7adc1bde0d6fa0058496b8912df9dba1ab94c9417f61`.
- Manifest tải, ngày truy xuất, query, bytes và hash: `data/interim/modeling/sprint03/nso_official_crosswalk_2025_20261003_v1/download_manifest.json`.
- PDF Quyết định 19/2025/QĐ-TTg lưu cùng thư mục evidence; SHA-256 `2fd391335947affbfb86fa2b9438f0fdca90694e80887e205266542c3236aea1`. PDF được giữ làm provenance pháp lý, không dùng OCR/trích tay để tạo các dòng tham chiếu.
- Điều khoản tái sử dụng riêng cho export chưa tìm thấy; ghi `PUBLIC_PORTAL_TERMS_NOT_LOCATED`, không tự gán giấy phép.

## Artifact và tái lập

- Package: `data/processed/gazetteer/s3_v3_nso_2025_snapshot/` (14.149 entity; 10.597 cạnh nguyên tử; 5 cạnh phi nguyên tử; 187 alias). `manifest.json` ghi hash của mọi file package, parent manifest, export, bảng ánh xạ và code build/verifier.
- SHA-256 manifest gói phát hành: `d838720b32c338dfc79ab37542519cf6a2f315f9a7602a6d5ba1753e7f7921fe`.
- Bảng tham chiếu có cột tên nguyên văn chính thức và tên canonical dự án: `official_code_reference.csv` trong package và `data/interim/modeling/sprint03/nso_official_crosswalk_2025_20261003_v1/release_v1/`.
- Trace mã theo entity, locator Excel và sai khác tên: `code_evidence.csv` trong package.
- Reconciliation tên/mã với bảng ánh xạ: `release_v1/mapping_reconciliation.json`; hồ sơ đầy đủ ở `release_v1/`.
- `release_v1/frozen_s3_v2_audit/` là audit chỉ đọc trên bản v2 trước khi dựng v3. Nó xác minh 3.321 mã xã mới, còn 34 mã tỉnh chưa có trường trong v2; trạng thái `new_package_released=false` của báo cáo audit nghĩa là chính audit không ghi package. `release_v1/release_report.json` ghi kết quả phát hành v3 hoàn tất.
- Chạy lại source audit chuẩn trên package phát hành đã đạt: `release_v1/final_s3_v3_reference_audit/coverage_gap_report.json` — **3.355/3.355 mã mới verified**, **0 mã cũ**; graph counts giữ nguyên.
- Lệnh dựng lại sau khi có các input trên:

```bash
python -m scripts.39_release_nso_gazetteer_snapshot
```

Script từ chối ghi đè output hiện có. Muốn tái tạo phải chọn thư mục evidence và tên package phiên bản mới bằng `--release-dir` và `--output-package`.

Tra một mã mới trong đúng snapshot:

```bash
python -m scripts.35_verify_gazetteer_sources lookup \
  --gazetteer-dir data/processed/gazetteer/s3_v3_nso_2025_snapshot \
  --name 'Phường Ba Đình' --level ward --date 2025-07-01 \
  --province 'Thành phố Hà Nội'
```

## Giới hạn và cách dùng

- `s3_v3` chỉ nâng mã cấp tỉnh và xã/phường **mới** tại đúng ngày 01/07/2025. 10.035 mã xã cũ, 691 huyện cũ, 63 tỉnh cũ và 5 huyện thiếu mã vẫn giữ nguyên trạng thái candidate/unverified hoặc missing. Gói vẫn là `PARTIAL_OLD_CODES_UNVERIFIED`.
- 17 sai khác tên là khác cách đặt dấu/chính tả giữa export và CSV nội bộ. Ghép mã + tỉnh cha đều duy nhất; cả hai dạng tên được lưu cùng evidence. Không sửa canonical name và không tự thêm 17 alias.
- Kết quả xác minh mã của s3_v2 trước khi phát hành: 3.321 mã xã mới khớp nguồn NSO, 34 tỉnh mới chưa có trường mã trong s3_v2, 0 mã cũ được xác minh. s3_v3 điền 34 mã tỉnh từ cùng export.
- Export công khai không thay thế việc làm rõ điều khoản tái sử dụng. Người dùng nên dùng đúng snapshot date khi tra cứu, không suy rộng trạng thái mã sang 2026.
- Không chạy lại HEUR-JW hoặc baseline. Các run đã khóa giữ nguyên; nếu sau này muốn đo tác động của s3_v3, tạo run mới có cấu hình/hash riêng.

Kiểm tra hồi quy mới: **4/4 test mới PASS**; nhóm modeling/verifier **49 PASS / 7 SKIP** (skip vì Deepparse/Torch không cài trong Python test host này). Lệnh `scripts.35_verify_gazetteer_sources audit` trên s3_v3 xác nhận **3.355 mã mới verified, 0 mã cũ**, hash package đúng. Smoke lookup trả `VERIFIED`, giữ mã `00004` và `official_primary_source_snapshot` cho Phường Ba Đình vào 01/07/2025; trả `OUT_OF_SNAPSHOT_SCOPE` cho 02/07/2025. Toàn bộ unit suite được gọi: **92 test chạy qua, 8 skip, 2 module import error** vì host Windows thiếu `osmium` và `vietnamadminunits`; không có lỗi assertion trong các test đã chạy. WSL vẫn bị môi trường từ chối truy cập.
