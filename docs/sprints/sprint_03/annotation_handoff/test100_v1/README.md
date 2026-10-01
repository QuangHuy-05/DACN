# Partner: gán thủ công 100 test địa chỉ T0

Gói phiên bản `test100_v1_20261001`, guideline `s3-span-v1.1`, nhánh GitHub **print3_label100test**. Bộ task chỉ chứa `sample_id` và `text`. Công việc của bạn: đọc từng chuỗi, chọn span và hệ span, Submit đủ 100 task, export **raw JSON** và gửi lại chủ dự án để QA/phán quyết.

**Sẵn sàng để gán mù:** ngày 01/10/2026, 138 quyết định `distinct` có lý do/người duyệt `Huy` đã được áp dụng và preflight đạt `AUDIT_PASS_WITH_HUMAN_NEAR_DUP_REVIEW`. Chủ dự án yêu cầu bàn giao 100 test theo protocol v1.0 giữ 100 ID frozen; bạn có thể tạo project và bắt đầu gán. `manifest.json` ghi hash bằng chứng. Giữ nguyên 100 ID và ca khó; gold sẽ được duyệt sau khi có export và QA.

## 1. Nhận tệp từ GitHub

Link thư mục: https://github.com/QuangHuy-05/DACN/tree/print3_label100test/docs/sprints/sprint_03/annotation_handoff/test100_v1

Có thể chọn nhánh `print3_label100test` → Code → Download ZIP rồi giải nén và tìm đúng thư mục này. Nếu dùng Git, chạy trong thư mục làm việc của bạn:

```bash
git clone --branch print3_label100test --single-branch https://github.com/QuangHuy-05/DACN.git DACN_label100test
```

Nếu repository yêu cầu quyền truy cập, chủ dự án cần cấp quyền cho tài khoản GitHub của bạn. Chỉ cần thư mục gói này để gán; các folder benchmark/gold/candidate/trace của repository không phục vụ lượt test mù.

| Tệp | Cách dùng |
| --- | --- |
| `test100_import.json` | Import đúng một lần vào project test mới. |
| `label_studio_span11.xml` | Dán toàn bộ vào Labeling Setup → Code. |
| `span_11_annotation_guideline.md` | Quy tắc gán chuẩn; đọc trước khi gán. |
| `manifest.json` | Định danh phiên bản, 100 ID/text hash và hash ba tệp. |
| `submission_template.md` | Điền người gán, phạm vi đã xem và ca còn khó để bàn giao. |

## 2. Mở Label Studio

Nếu đã có môi trường Label Studio Python 3.11 trong WSL:

```bash
source ~/.venv_labelstudio311/bin/activate
python --version
label-studio start --host http://localhost:8080 --port 8080 --no-browser
```

Nếu máy đã có `python3.11` nhưng chưa có môi trường, tạo riêng rồi cài phiên bản tương ứng với dự án:

```bash
python3.11 -m venv ~/.venv_labelstudio311
source ~/.venv_labelstudio311/bin/activate
python -m pip install label-studio==1.23.1
label-studio start --host http://localhost:8080 --port 8080 --no-browser
```

Nếu `python3.11` chưa có, cần chuẩn bị Python 3.11 trước; không tiếp tục cài trong Python 3.14. Nếu dùng Python 3.11 có sẵn trên Windows thay vì WSL, mở PowerShell trong thư mục làm việc, dùng `py -3.11 -m venv .venv_labelstudio311`, rồi chạy trực tiếp `.venv_labelstudio311\Scripts\python.exe -m pip install label-studio==1.23.1` và `.venv_labelstudio311\Scripts\label-studio.exe start --host http://localhost:8080 --port 8080 --no-browser`.

Giữ terminal chạy. Mở **http://localhost:8080** trong trình duyệt; đăng ký/đăng nhập tài khoản riêng. Server trên máy bạn có database/account/project riêng; không cần token của chủ dự án. `--no-browser` tránh lệnh tự mở trình duyệt WSL. [Tài liệu khởi động](https://labelstud.io/guide/start).

## 3. Cấu hình project test

1. Projects → Create → tên **DACN_S3_T0_TEST_BLIND_v1**.
2. Labeling Setup → Code: mở `label_studio_span11.xml` của gói, sao chép toàn bộ XML và dán vào. Save/Create. Có thể dùng Settings → Labeling Interface sau khi tạo project nếu wizard khác phiên bản.
3. Import/Data Import → Upload Files → chọn **test100_import.json** → xác nhận. Kiểm Data Manager có đúng **100 task**. Không import lần hai; project mới đúng 100 task giúp giữ export sạch.
4. Mở Label All/task đầu. Text phải chưa có span gợi ý. Giữ project không ML backend/prediction, không đọc đáp án benchmark hoặc nhờ mô hình sinh đáp án từng task. “Gán mù” nghĩa là dùng chuỗi hiển thị và guideline để tạo đáp án của bạn.

## 4. Gán mỗi task

1. Đọc chuỗi nguyên bản và Sample ID. Giữ nguyên chữ viết tắt, OCR, dấu tiếng Việt; không sửa text để trở thành địa chỉ chuẩn.
2. Chọn nhãn trên thanh nhãn, dùng chuột bôi đúng đoạn. Gồm từ loại đơn vị (`Phường`, `Quận`, `Đường`, `TP.`) nếu có; dấu phẩy và khoảng trắng ngoài cùng để trống.
3. Click span vừa tạo hoặc region bên phải. Ở **System of selected span**, chọn đúng một giá trị: `cu`, `moi` hoặc `khong_xac_dinh`. Thực hiện cho mọi span.
4. Tạo tiếp tất cả thực thể còn lại, không chồng lấp. Có thể xóa region sai rồi bôi lại để sửa ranh giới.
5. Ở **Whole-address system, if clear**, chọn `cu`/`moi`/`Lai` chỉ khi đủ bằng chứng cho cả câu; nếu chưa chắc thì để trống. Trường này không thay hệ từng span.
6. Ghi flag/note khi cần. Nếu ô note có nút Add, nhấn Add sau khi viết. Submit để lưu; khi sửa bản đã Submit, dùng Update.

## 5. Tra nhanh nhãn và hệ

| Nhãn | Ví dụ minh họa |
| --- | --- |
| `SoNha` | `Số 12/3A`, `50` |
| `TenDuong` | `Đường Nguyễn Xí`, `Pasteur` |
| `Ngo/Hem` | `Ngõ 42`, `Hẻm 12/3` |
| `ToaNha/CanHo` | `Tòa A`, `Căn A305` |
| `PhuongXa` | `Phường 7`, `P.7`, `Xã Bình Hưng` |
| `QuanHuyen` | `Quận 1`, `Huyện A`, đơn vị cấp huyện cũ |
| `TinhThanh` | `TP. Hồ Chí Minh`, `Tỉnh Bắc Ninh`, đơn vị cấp tỉnh |
| `MocDinhVi` | `gần cầu Sài Gòn`, `đối diện chợ Bà Chiểu` |
| `HuongDi` | `hướng Bình Thạnh`, `rẽ trái`, `đi thẳng` |
| `GhiChu` | `tầng 3`, `cổng sau` |
| `Khac` | `Khu phố 4`, `Ấp 2`: thành phần địa chỉ có nghĩa ngoài các loại trên |

Các ví dụ chỉ minh họa guideline, không là đáp án của test. `O` là phần không bôi nhãn, như dấu phẩy/ngoặc ngoài span, “nay là”, chữ ngoài địa chỉ hoặc OCR không nhận ra; không có nút `O`. `Khac` không phải nơi chứa mọi đoạn khó hiểu. Xem quy tắc đúng/sai đầy đủ trong [guideline](span_11_annotation_guideline.md).

`SoNha`/`TenDuong` dùng hệ `khong_xac_dinh`; `QuanHuyen` luôn `cu`. `PhuongXa`/`TinhThanh` chỉ `cu`/`moi` khi có chứng cứ thời kỳ. `Hà Nội` hoặc `TP. Hồ Chí Minh` dùng được ở cả hai hệ nên span thường `khong_xac_dinh`. Không suy hệ mới chỉ vì thiếu huyện. Hệ toàn câu có thể khác hệ một span. Mốc/hướng/tòa/căn/ghi chú mặc định `khong_xac_dinh` theo guideline.

| Flag | Dùng khi |
| --- | --- |
| `unreadable_ocr` | OCR không nhận diện được; để đoạn đó không gán, ghi lý do. |
| `ambiguous_label` | Chưa chắc loại nhãn hoặc ranh giới đoạn. |
| `temporal_ambiguity` | Chưa xác định được hệ cũ/mới của span hoặc cả câu. |
| `privacy_review` | Có thông tin cần rà soát riêng tư/quyền sử dụng. |

Giữ ca khó, ghi note nêu đoạn và lý do. Nếu Submit báo `span_system is required`, click từng region để chọn hệ còn thiếu; kiểm có region trùng vô tình tạo ra hay không.

## 6. Export và trả kết quả

1. Kiểm **100/100 đã Submit**, chưa dùng draft/prediction để thay annotation. Mở lại vài task để kiểm lưu thành công.
2. Data Manager → Export → **JSON** → Export/Download. Chọn raw JSON để giữ `annotations[].result`, region ID, hệ span, flag/note; không chọn JSON-MIN, CSV hoặc CoNLL. [Hướng dẫn export](https://labelstud.io/guide/export).
3. Đổi tên bản tải xuống thành `test_blind_round1_<ten_nguoi_gan>.json`. Giữ bản gốc. Lần sửa dùng round2, round3... để giữ lịch sử.
4. Điền [submission_template.md](submission_template.md), gửi JSON + biên bản cho chủ dự án qua kênh tệp hai bạn đã thống nhất. Không cần commit export lên GitHub.
5. Chủ dự án/agent sẽ chạy QA và trả danh sách ID cần sửa; sửa trong Label Studio, Update, export vòng mới. QA đạt cấu trúc vẫn cần phán quyết ca khó để phát hành gold.

Không cần chạy generator/converter ở máy partner: converter đầy đủ cần queue nội bộ và hash khóa của máy chủ dự án. Hoàn tất 100 annotation không tự chứng nhận test gold; chủ dự án duyệt sau khi có QA và quyết định ca khó.
