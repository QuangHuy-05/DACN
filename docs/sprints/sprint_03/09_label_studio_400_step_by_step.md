# Gán nhãn 68 pilot, 232 train/dev và bàn giao 100 test

Ngày cập nhật: **01/10/2026**. Theo lựa chọn của chủ dự án, **68 và 232 đều dùng prediction để người gán kiểm tra, sửa và Submit**. Vòng pilot này là rà soát có hỗ trợ; inter-annotator agreement độc lập vẫn `NOT_MEASURED`. Partner gán 100 test thủ công, không prediction.

## 1. Chọn đúng tệp và project

| Người làm | Project mới | Tệp import | Số task |
| --- | --- | --- | --- |
| Chủ dự án | `DACN_S3_T0_PILOT_ASSISTED_v2` | `data/interim/annotation/sprint03/reannotation_v2_release1/pilot68_with_predictions.json` | 68 |
| Chủ dự án | `DACN_S3_T0_BATCH02_ASSISTED_v2` | `data/interim/annotation/sprint03/reannotation_v2_release1/batch232_with_predictions.json` | 232 |
| Partner | `DACN_S3_T0_TEST_BLIND_v1` | `docs/sprints/sprint_03/annotation_handoff/test100_v1/test100_import.json` | 100 |

Hai tệp `*_with_predictions.json` đã có cả `data` và `predictions`. Import **một tệp vào một project mới** là đủ; không import thêm bản `*_import.json` hoặc chạy script 15 vào cùng project vì sẽ tạo task trùng hoặc prediction lặp. Tệp `*_candidates.json` là định dạng nội bộ cho script, không phải tệp chọn ở màn hình Data Import. Bản mới dùng đúng ID/text hiện có, có 245 + 1.059 span ứng viên; bạn phải kiểm cả span đã gợi ý lẫn thực thể còn thiếu.

Các tệp của chủ dự án nằm trong `data/interim/`, được Git ignore. Gói 100 test nằm trong thư mục handoff đã được đưa lên nhánh `print3_label100test` để partner tải mà không cần dữ liệu OSM/raw hoặc chạy generator. Gói test chỉ có ID/text, XML, guideline và hash; không có nhãn benchmark, provenance gợi hệ hay prediction.

**Cổng test đã qua preflight ngày 01/10:** file quyết định có đủ 138 cặp `distinct`, lý do và người duyệt `Huy`; audit mới đạt `AUDIT_PASS_WITH_HUMAN_NEAR_DUP_REVIEW`, giữ phân bổ 240/60/100. [Bằng chứng bàn giao](test100_split_gate_20261001.json). Theo yêu cầu bàn giao test của chủ dự án ngày 01/10, lần gán này áp dụng protocol v1.0 và guideline đã khóa: đúng 100 ID frozen, gán mù, không prediction. Partner có thể bắt đầu; gold vẫn phải qua QA và duyệt sau export.

## 2. Mở Label Studio trên máy chủ dự án

Mở PowerShell/Windows Terminal rồi vào WSL:

```powershell
wsl
```

Trong cửa sổ WSL, chạy:

```bash
cd /mnt/d/DACN
source ~/.venv_labelstudio311/bin/activate
python --version
label-studio start --host http://localhost:8080 --port 8080 --no-browser
```

Python cần là 3.11.x. Khi thấy server đang nghe cổng 8080, giữ terminal đó chạy và mở **http://localhost:8080** trong trình duyệt Windows. Đăng nhập tài khoản cũ để dùng cùng database. `Ctrl+C` sẽ tắt server; mở terminal WSL thứ hai nếu cần chạy converter. `--no-browser` ngăn lỗi tự mở trình duyệt bằng `gio`; `--host` ở đây dùng URL có `http://`, không dùng giá trị trần `0.0.0.0`. [Tham khảo lệnh khởi động chính thức](https://labelstud.io/guide/start).

Nếu không vào được, chạy `curl -I http://localhost:8080` ở terminal WSL thứ hai. HTTP 200/302 cho thấy server có phản hồi. Nếu server đã dừng hoặc có `Connection refused`, khởi động lại và giữ terminal mở. Nếu cổng 8080 đã có Label Studio đang chạy, dùng instance đó thay vì khởi động lần hai. Lệnh rời virtualenv là `deactivate`.

## 3. Tạo và cấu hình hai project mới

Làm lần lượt cho project 68 rồi project 232; sau đó có thể mở hai tab trình duyệt và gán xen kẽ. Không dùng project pilot v1 cũ để thay vòng mới.

1. Ở trang Projects, chọn **Create**. Nhập đúng tên project trong bảng mục 1.
2. Chọn **Labeling Setup**, mở chế độ **Code**. Mở `D:\DACN\configs\label_studio_span11.xml` bằng VS Code/Notepad, sao chép toàn bộ XML và dán thay toàn bộ nội dung mặc định. Chọn Save; nếu dùng wizard, hoàn tất Create trước rồi mở Settings → Labeling Interface để dán XML.
3. Kiểm preview có 11 nút nhãn, chuỗi địa chỉ, mục hệ span khi chọn một region, hệ toàn câu, bốn flag và ô note. Giữ nguyên tên control/label trong XML.
4. Chọn **Import / Data Import → Upload Files** và chọn đúng một tệp `*_with_predictions.json` trong bảng. Xác nhận import, kiểm Data Manager có đúng 68 hoặc 232 task. Nếu thấy gấp đôi số task, chưa tiếp tục gán: project đã import trùng; tạo project mới đúng một lần sẽ giữ bản cũ để truy lại.
5. Vào **Settings → Machine Learning** (tên menu có thể khác theo phiên bản), bật lựa chọn **Show predictions to annotators in the Label Stream and Quick View**. Nếu giao diện cho chọn model version, chọn `s3_span11_source_trace_v2_not_gold`. Mở Label All/Label Stream để tạo annotation có thể chỉnh sửa từ prediction.
6. Mở task đầu, kiểm có các span màu. Nếu chỉ xem được prediction mà không sửa được, dùng chức năng copy prediction vào annotation/new annotation trong editor hoặc bật tùy chọn ở bước 5; sau đó sửa trên annotation của tài khoản bạn. Không bấm Submit trước khi đã kiểm từng span.

Label Studio hỗ trợ import task cùng prediction; để chỉnh sửa, prediction được sao chép thành annotation của người gán. [Hướng dẫn pre-annotation](https://labelstud.io/guide/predictions).

## 4. Ý nghĩa 11 nhãn span

Nhãn trả lời câu hỏi **“đoạn chữ này là thành phần địa chỉ nào?”**. Chọn đúng đoạn xuất hiện, gồm từ chỉ loại đơn vị, giữ cách viết/OCR gốc; dấu phân cách ngoài đoạn để trống. Bảng này tóm tắt [guideline khóa s3-span-v1.1](span_11_annotation_guideline.md).

| Nhãn | Thành phần và ví dụ |
| --- | --- |
| `SoNha` | Số nhà, kể cả chữ và gạch chéo: `Số 12/3A`, `50`. Không lấy dấu phẩy liền sau. |
| `TenDuong` | Tên đường/phố: `Đường Nguyễn Xí`, `Pasteur`, `Phố Trần Bình Trọng`; giữ từ `Đường`/`Phố` nếu có. |
| `Ngo/Hem` | Ngõ/hẻm/ngách: `Hẻm 12/3`, `Ngõ 42`; tên đường ngay sau được tách riêng nếu rõ. |
| `ToaNha/CanHo` | Tòa nhà, căn hộ: `Tòa A`, `Căn A305`; `tầng 3` thuộc `GhiChu`. |
| `PhuongXa` | Đơn vị cấp xã: `Phường 7`, `P.7`, `Xã Bình Hưng`; nhãn loại này giống nhau dù hệ cũ/mới. |
| `QuanHuyen` | Đơn vị cấp huyện cũ: `Quận 1`, `Huyện A`, thị xã/thành phố khi thực sự là cấp huyện. Không thêm huyện khi text không có. |
| `TinhThanh` | Tỉnh/thành phố cấp tỉnh: `Tỉnh Bắc Ninh`, `TP. Hồ Chí Minh`. Phải xem cấp đơn vị khi có từ “thành phố”. |
| `MocDinhVi` | Mốc và quan hệ vị trí: `gần cầu Sài Gòn`, `đối diện chợ Bà Chiểu`. |
| `HuongDi` | Hướng/chỉ dẫn di chuyển: `hướng Bình Thạnh`, `rẽ trái`, `đi thẳng`; tên đường sau lệnh rẽ có thể tách riêng. |
| `GhiChu` | Ghi chú tầng/tiếp cận: `tầng 3`, `cổng sau`, `lối giao hàng` theo ngữ cảnh. |
| `Khac` | Thành phần địa chỉ có nghĩa ngoài 10 loại trên, như `Khu phố 4`, `Ấp 2`. |

`O` không có nút trong giao diện: đó là phần để trống, như dấu phẩy/ngoặc ngoài span, “nay là”, nội dung ngoài địa chỉ hoặc OCR không đọc được. Không đưa mọi phần khó hiểu vào `Khac`. Không tạo span chồng lấp; mọi lần nhắc được nhận diện đều phải gán.

## 5. System of selected span: hệ của từng đoạn

Mục này chỉ hiện khi bạn **click một span/region** trên text hoặc danh sách Regions bên phải. Mỗi span đều cần đúng một lựa chọn; chọn hệ toàn câu không thay cho hệ span.

| Giá trị | Cách chọn |
| --- | --- |
| `cu` | Span thể hiện đơn vị thuộc hệ cũ khi có căn cứ. `QuanHuyen` luôn chọn `cu`, kể cả toàn câu là `Lai`. |
| `moi` | Span phường/xã hoặc tỉnh/thành thuộc hệ mới khi đủ căn cứ theo guideline. |
| `khong_xac_dinh` | Không đủ căn cứ phân biệt thời kỳ. `SoNha` và `TenDuong` dùng giá trị này; mốc/hướng/tòa/căn/ghi chú thường cũng vậy. |

Ví dụ span `TP. Hồ Chí Minh` hoặc `Hà Nội` tự nó có thể thuộc cả hai thời kỳ: chọn `khong_xac_dinh` khi text không có bằng chứng phân biệt. `Phường Phú Hòa` tồn tại ở cả hai hệ cũng xử lý như vậy. Có thể vẫn chọn `cu`/`moi`/`Lai` cho **toàn câu** nếu các thành phần khác đủ bằng chứng. Không ép tất cả span nhận hệ toàn câu hoặc nhận hệ nguồn của mẫu sinh.

## 6. Whole-address system và flags

Hệ toàn câu là trường tùy chọn: `cu` khi đủ bằng chứng hệ cũ; `moi` khi đủ bằng chứng hệ mới; `Lai` khi thấy thành phần của cả hai hệ. Chưa chắc thì để trống, ghi flag/note. Vắng huyện có thể do thiếu trường nên không đủ để chọn `moi`. Prediction có thể để trống trường này có chủ ý.

| Flag | Khi sử dụng | Note nên ghi |
| --- | --- | --- |
| `unreadable_ocr` | Ký tự OCR hỏng đến mức không nhận diện được thực thể. | `Đoạn ... không đọc được; để O, không khôi phục từ nguồn sạch.` |
| `ambiguous_label` | Chưa chắc loại nhãn hoặc ranh giới span. | `Đoạn ... có hai cách tách; cần phán quyết ranh giới.` |
| `temporal_ambiguity` | Không xác định được cũ/mới của span hoặc T1. | `Tên đơn vị dùng ở cả hai thời kỳ; span giữ khong_xac_dinh, T1 để trống nếu chưa đủ căn cứ.` |
| `privacy_review` | Text có thông tin cần kiểm riêng tư như tên/người nhận, điện thoại hoặc địa chỉ cá nhân không rõ quyền dùng. | `Cần kiểm nguồn và phạm vi sử dụng; chưa tự xác nhận clearance.` |

Flag là yêu cầu rà soát, không tự động làm annotation sai cấu trúc. Giữ flag phản ánh khó khăn thật và ghi lý do; không bỏ flag chỉ để báo cáo đẹp. Gợi ý `Check visible administrative period.` nghĩa là “kiểm bằng chứng thời kỳ của các đơn vị”. Có 473 mục trong queue mới, gồm nhiều mục trên cùng một task; đây không phải 473 task hoặc 473 lỗi.

## 7. Quy trình kiểm mỗi task rồi Submit

1. Đọc toàn bộ chuỗi và `sample_id`. So text với các vùng đang màu; kiểm cả phần chưa có màu để tìm thực thể bị bỏ sót.
2. Click từng region, kiểm loại nhãn và ranh giới; dấu phẩy/ngoặc ngoài span hoặc khoảng trắng ngoài cùng phải để trống. Khi cần đổi ranh giới, có thể xóa region sai bằng biểu tượng thùng rác và chọn lại đoạn đúng.
3. Nếu thiếu span, chọn nhãn trên thanh nhãn, kéo chuột chọn đúng đoạn chữ, rồi click region mới để chọn `span_system`.
4. Với mọi span, kiểm hệ theo mục 5. Hai span cùng chữ vẫn là hai region khác nhau và đều cần hệ.
5. Kiểm T1 toàn câu, flags và note. Với ô note có nút **Add**, nhấn Add sau khi viết để note thành kết quả đã lưu, rồi mới Submit.
6. Chọn **Submit**; nếu sửa annotation đã Submit, chọn **Update**. Mở lại ít nhất vài task đầu để kiểm kết quả đã lưu. Draft/prediction chưa Submit không được tính là gold.

Nếu thấy `Checkbox "span_system" is required`, click lần lượt từng region trong Regions và gán hệ còn thiếu. Kiểm thêm region trùng vô tình tạo ra: xóa region trùng thay vì gán lại hai lần. Trường T1/flags thường không bắt buộc, còn hệ mỗi span bắt buộc.

**Ca cần làm tay trong 232:** `sample_id=s3_c1f7b490f4d7c9bc` có nguồn số nhà `8 (660/8)`. Prediction mới đã bỏ riêng span số nhà để tránh ranh giới có ngoặc ngoài. Bạn cần xem chuỗi, quyết định các span số nhà; nếu coi hai số là hai lần nhắc, chọn riêng `8` và `660/8`, hệ đều `khong_xac_dinh`, dấu ngoặc để O. Giữ `ambiguous_label` và ghi lý do cho người phán quyết. Những span khác vẫn cần kiểm như mọi task.

68 và 232 có thể gán song song bằng hai tab/project; không gộp chúng vào cùng một project. Ghi ngày, người gán và thời gian gán thực nếu muốn tính tốc độ; không dùng thời gian server chạy làm thời gian annotator làm việc.

## 8. Export đúng JSON và lưu ba vòng riêng

Ở mỗi project: Data Manager → **Export → JSON → Export/Download**. Chọn **JSON raw**, không chọn JSON-MIN, CSV, CoNLL hoặc chỉ tải prediction. JSON raw giữ task, annotation, ID region và hệ span. [Tài liệu export chính thức](https://labelstud.io/guide/export).

Trong Windows tạo thư mục `D:\DACN\data\interim\annotation\sprint03\exports\reannotation_v2\`, rồi chép các file tải từ Downloads vào đúng tên:

- `pilot_assisted_round1.json` cho 68;
- `batch_assisted_round1.json` cho 232;
- `test_blind_round1.json` nhận từ partner cho 100.

Nếu Export chỉ gồm các task đã Submit thì converter sẽ báo thiếu phần còn lại; cần hoàn tất và export lại. Giữ export round1, round2... riêng; không chỉnh JSON để tự đổi prediction thành annotation.

## 9. Chạy QA ở máy chủ dự án

Mở terminal WSL thứ hai, không đóng terminal server:

```bash
cd /mnt/d/DACN
source ~/.venv_labelstudio311/bin/activate

python -m scripts.11_convert_label_studio_pilot \
  --export data/interim/annotation/sprint03/exports/reannotation_v2/pilot_assisted_round1.json \
  --queue data/interim/annotation/sprint03/annotation_queue_batch01.csv \
  --output-dir data/interim/annotation/sprint03/reannotation_v2_release1/pilot_conversion_round1

python -m scripts.17_convert_span_annotation_batch \
  --export data/interim/annotation/sprint03/exports/reannotation_v2/batch_assisted_round1.json \
  --queue data/interim/annotation/sprint03/annotation_queue_batch02_train_dev.csv \
  --role train_dev_batch02 \
  --output-dir data/interim/annotation/sprint03/reannotation_v2_release1/batch_conversion_round1

python -m scripts.17_convert_span_annotation_batch \
  --export data/interim/annotation/sprint03/exports/reannotation_v2/test_blind_round1.json \
  --queue data/interim/annotation/sprint03/annotation_queue_batch01.csv \
  --role frozen_benchmark_test_hold \
  --output-dir data/interim/annotation/sprint03/reannotation_v2_release1/test_conversion_round1
```

Chỉ chạy lệnh test khi đã nhận raw export của partner. Pilot xem `pilot_qa_report.json`, `pilot_review_items.json`; batch/test xem `qa_report.json`, `review_items.json`. Mục tiêu đủ 68/232/100, không thiếu task và `issues=[]`. Sửa ca lỗi trong Label Studio rồi export vòng mới. `READY_FOR_HUMAN_REVIEW` vẫn cần duyệt nội dung và phán quyết ca có flag/note trước khi phát hành gold.

## 10. Gửi partner 100 mẫu và nhận bàn giao

Gửi link thư mục `annotation_handoff/test100_v1` trên nhánh **print3_label100test**, hoặc nén riêng đúng thư mục đó để gửi. Partner đọc [README của gói test](annotation_handoff/test100_v1/README.md), dùng ba tệp task/XML/guideline trong gói, trả raw JSON và [biên bản bàn giao](annotation_handoff/test100_v1/submission_template.md) đã điền. GitHub cung cấp tệp; mỗi máy Label Studio local có project ID/account/database riêng, không cần dùng token của chủ dự án.

Partner không cần tái tạo benchmark, chạy script 10/16/21, đọc gold/prediction/GT hay source trace. Converter đầy đủ dùng queue nội bộ nên chủ dự án/agent chạy sau khi nhận export. Người gán vẫn giữ đủ 100 ID, đặt flag cho ca khó và bàn giao để phán quyết.

## 11. Bằng chứng kiểm tra trước bàn giao

Ngày 01/10/2026: mã xã mất zero đầu đã được sao lưu và khôi phục từ Git, gồm kiểu xuống dòng CRLF, khớp chính xác hash snapshot `22bd8278...`. Dùng thư mục `reannotation_v2_release1` có cổng ranh giới của converter. Candidate → prediction → converter trên 300 task đạt; các file input/output của generation manifest khớp hash. Toàn bộ **64/64 test** đã chạy đạt trong WSL. Gói test đúng 100 ID frozen, không prediction/annotation và không giao ID với 300 train/dev. Audit có quyết định người đã PASS. Trường `near_duplicate_pairs_pending` trong coverage của generator dùng snapshot preflight cũ; trạng thái hiện hành nằm trong `assisted_import_manifest.json` và `split_preflight_review_20261001/split_audit_report.json`, với 0 cặp chưa giải quyết. Đây là QA kỹ thuật, chưa xác nhận gold ngữ nghĩa.
