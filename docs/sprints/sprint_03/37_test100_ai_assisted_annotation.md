# Test100: gợi ý AI và duyệt thủ công — 04/10/2026

## 1. Protocol bổ sung `test100-assisted-v1`

Chủ dự án đã yêu cầu AI gán trước 100 mẫu test để chủ dự án kiểm tra lại. Lượt này là **AI-assisted human review**, không còn là gán mù độc lập. Chỉ thay cách gán nhãn; giữ guideline `s3-span-v1.1`, đúng 100 ID/text, split, corpus train/dev và các run đã khóa.

Gói blind `annotation_handoff/test100_v1/` và protocol v1.0 giữ nguyên làm hồ sơ cũ. Nếu partner đã gán một phần, giữ project/export đó riêng. Không gộp các lượt đã xem gợi ý rồi gọi là agreement độc lập. Quyền mới chỉ cho phép **annotation**; chưa mở train/tune/chấm test cuối.

## 2. File đã tạo

Thư mục `data/interim/annotation/sprint03/test100_assisted_v1/` có:

| File | Công dụng |
| --- | --- |
| `test100_import_with_predictions.json` | Import một lần vào project mới: 100 task kèm span/hệ/flag/note; không có annotation đã Submit. |
| `label_studio_span11.xml` | Copy toàn bộ vào Labeling Interface. |
| `span_11_annotation_guideline.md` | Bản sao nguyên byte guideline đã khóa. |
| `test100_candidate_spans.json` | Candidate có offset raw và trace nguồn hành chính. |
| `review_all_100.md` | Đáp án gợi ý theo từng sample_id, để mở cạnh giao diện. |
| `review_queue.json` | Cờ/note; không thay thế việc xem đủ 100 mẫu. |
| `prediction_structure_qa.json` | QA prediction; không phải QA human export hoặc duyệt gold. |
| `manifest.json` | Hash nguồn/công cụ/output, số đếm và trạng thái chưa duyệt. |
| `test100_text_only_import.json` | Bản đối chiếu ID/text; không import thêm cùng project. |

Đã tạo **100/100 task, 446 span**. Offset/substring/no-overlap, lựa chọn hệ bắt buộc và round-trip qua serializer/converter đạt. **15 mẫu ưu tiên rà nhãn/ranh giới, 51 mẫu ưu tiên rà hệ, 34 mẫu thường**. Gợi ý T1: 27 cu, 12 moi, 5 Lai, 56 để trống; đây là phân bố candidate, chưa phải gold.

Có 7 nhãn xuất hiện: SoNha 88, TenDuong 99, Ngo/Hem 13, PhuongXa 89, QuanHuyen 56, TinhThanh 99, Khac 2. Không sinh thêm mốc/hướng/tòa nhà/ghi chú để đủ support; người duyệt có thể sửa nếu văn bản có bằng chứng. Không suy năng lực 11 nhãn từ những nhãn không có support.

## 3. Cách tạo và nguồn tham khảo

AI đọc import chỉ có sample_id/text rồi soạn span; không đọc `GT_*`, địa chỉ sạch, nhãn nguồn sinh tổng hợp hoặc prediction của HEUR/CRF/neural. Giữ nguyên chữ viết tắt/OCR, dấu câu ngoài span là O; gán mọi lần xuất hiện. QuanHuyen luôn cu; số nhà/đường/khu địa điểm giữ khong_xac_dinh.

Hệ hành chính được tham khảo từ hai snapshot NSO đã có trong repository: `u1_v4/reference_old.jsonl` tại 30/06/2025 và `s3_v4_nso_dual_snapshot_release2/official_code_reference.csv` tại 01/07/2025. Nguồn: [Danh mục đơn vị hành chính NSO](https://danhmuchanhchinh.nso.gov.vn/). Hash và bằng chứng tra nằm trong manifest/candidate. Không tải nguồn hoặc cài package mới. Không suy khoảng hiệu lực pháp lý ngoài hai snapshot này.

Tên phường trùng hai hệ, tên thiếu căn cứ hoặc nguồn cũ có lỗi liên kết cha nhận **khong_xac_dinh**. Không suy moi vì thiếu quận, không sao chép cu từ quận lên phường. Span tỉnh/thành có tên trùng thời kỳ giữ chưa xác định. T1 được đề xuất riêng khi đơn vị có bằng chứng; còn phường mơ hồ thì T1 để trống. Đây là gợi ý cần người duyệt xác nhận.

Các mã lý do trong note:

| Mã | Cách hiểu khi duyệt |
| --- | --- |
| `EXACT_NEW_WARD_PROVINCE_SNAPSHOT` | Tên phường và tỉnh khớp bản mới; gợi ý moi theo hai snapshot đã tra. |
| `EXACT_OLD_WARD_PARENT_SNAPSHOT` | Khớp một đơn vị cũ và cha, không có cùng tên trong bản mới của tỉnh đã tra. |
| `NAME_PRESENT_IN_BOTH_SNAPSHOTS` | Tên tồn tại ở cả hai thời kỳ; giữ chưa xác định nếu chuỗi không cho bằng chứng thêm. |
| `OLD_REFERENCE_PARENT_LINK_GAP` | Nguồn danh mục cũ có lỗi liên kết cha; không đủ căn cứ để chọn hệ từ phép tra này. |
| `NO_EXACT_PROVINCE_CONTEXT` | Chuỗi thiếu tỉnh hoặc không đối chiếu được tên tỉnh nguyên văn. |
| `NO_UNIQUE_DATED_REFERENCE` | Không có đúng một kết quả tham khảo đủ căn cứ; cần người duyệt kiểm tra. |

## 4. Bật Label Studio

Trong WSL:

```bash
cd /mnt/d/DACN
source ~/.venv_labelstudio311/bin/activate
label-studio start --host http://localhost:8080 --port 8080 --no-browser
```

Giữ terminal chạy, mở **http://localhost:8080/** bằng trình duyệt Windows; không mở `0.0.0.0`.

## 5. Tạo project và import

1. **Create Project** → tên ** **. Dùng project mới để giữ lượt partner và những annotation trước riêng biệt.
2. **Settings → Labeling Interface → Code** → dán toàn bộ XML trong gói → **Save**.
3. **Import → Upload Files** → chọn:

   `D:\DACN\data\interim\annotation\sprint03\test100_assisted_v1\test100_import_with_predictions.json`

   Nhấn **Import**, xác nhận đúng **100 task**. Không nhập thêm file text-only; không chạy script 15 cho project test vì script đó vẫn bảo vệ train/dev.
4. **Settings → Annotation** → bật **Use predictions to prelabel tasks** và chọn version `s3_span11_test100_ai_assisted_v1_not_gold` nếu có danh sách. Nếu tùy chọn hiển thị nằm trong **Machine Learning**, bật **Show predictions to annotators in the Label Stream and Quick View**. Prediction là bản chỉ đọc; cần tạo annotation/copy prediction để sửa. Xem [pre-annotations](https://labelstud.io/guide/predictions) và [ML settings](https://labelstud.io/guide/ml) của Label Studio.
5. Mở task đầu, sample_id **s3_a66e21b407d25ee0**; phải thấy 5 span: `8`, `Ngõ 28`, `Ông Ích Khiêm`, `Phường Ba Đình`, `Thành phố Hà Nội`. Click region để thấy hệ đã điền. Nếu đang ở tab prediction, chọn tạo annotation từ prediction rồi mới sửa/Submit.

## 6. Kiểm tra rồi Submit

Mỗi task: đọc toàn câu → kiểm nhãn/ranh giới → click từng region kiểm System of selected span → kiểm Whole-address system riêng → sửa/bổ sung note cho ca khó → **Submit**. Làm đủ 100, không Submit hàng loạt. Số thứ tự trong review_all_100.md không phải task ID Label Studio; dùng **sample_id** đối chiếu.

Hệ span:

- **cu**: có bằng chứng thuộc hệ trước 01/07/2025; Quận/Huyện luôn cu.
- **moi**: có bằng chứng thuộc hệ hai cấp trong snapshot mới.
- **khong_xac_dinh**: không đủ căn cứ thời kỳ hoặc phần không phân biệt hệ như số nhà/đường; không phải vùng O.

Flag:

- **ambiguous_label**: cần xác nhận loại thực thể/ranh giới, ví dụ mã lô hay số nhà.
- **temporal_ambiguity**: chưa phân biệt được thời kỳ; có thể giữ sau duyệt với lý do.
- **unreadable_ocr**: thực sự không đọc/nhận diện được ký tự; bỏ dấu không tự động là OCR không đọc được.
- **privacy_review**: có thông tin riêng tư cần xử lý; không dùng chỉ vì có số nhà.

Note hiện là **gợi ý AI chưa duyệt**. Bạn bổ sung quyết định thực tế, không bỏ flag chỉ để báo cáo xanh. T1 để trống nếu chưa đủ bằng chứng, không tick bắt buộc.

Các ca cần đọc kỹ:

| Thứ tự | Sample ID | Cần kiểm |
| --- | --- | --- |
| 25 | s3_b489935e347b0113 | `16` đề xuất PhuongXa, nhưng không có chữ Phường. |
| 31 | s3_e192f19b0b238432 | `SH02-07` có thể là mã lô/căn; `San Ho 2` có thể không phải đường. |
| 45 | s3_878554ae9b7f8f0b | Số nhà khác span hẻm; cấp của Tân Phú cần rà. |
| 46 | s3_c3abeb01e2e73e91 | Gán hai lần Phường 11; không tự thêm tỉnh bị thiếu. |
| 49 | s3_3271d5524fc50164 | Công Trường Công Xã Paris tạm TenDuong, cần chốt loại địa điểm. |
| 51 | s3_39a5dfd0ab38f906 | `T2-4` và `Khu Công Nghệ Cao`: rà số nhà/mã lô và Khac. |
| 54 | s3_813d3b0d62e9319c | Hoàn Kiếm có thể là quận/phường; xem toàn cấu trúc. |
| 62 | s3_98d58db06330840b | Khu dân cư số 9 tạm Khac, không tự coi là đường. |

## 7. Export và QA sau duyệt

**Đã nhận export round1 ngày 04/10/2026.** Xem [QA hiện hành và danh sách xử lý](41_test100_export_qa_20261004.md): 98 candidate chuyển được sau lựa chọn tương đương, còn thiếu 1 mẫu và task 695 cần chốt annotation; có các ca nội dung/T1 cần xử lý. Bản này chưa được phát hành gold.

Đủ 100 task đã Submit → **Export → JSON**, giữ **raw JSON**, không JSON-MIN. Lưu file mới:

`data/interim/annotation/sprint03/exports/test_assisted_v1/test100_assisted_round1.json`

Tạo thư mục nếu chưa có; raw export bất biến, lần sửa sau dùng round2. Chạy QA khi file đã có:

```bash
python -m scripts.17_convert_span_annotation_batch \
  --export data/interim/annotation/sprint03/exports/test_assisted_v1/test100_assisted_round1.json \
  --queue data/interim/annotation/sprint03/annotation_queue_batch01.csv \
  --role frozen_benchmark_test_hold \
  --test-annotation-mode ai_assisted_human_review \
  --assisted-manifest data/interim/annotation/sprint03/test100_assisted_v1/manifest.json \
  --output-dir data/interim/annotation/sprint03/test_assisted_conversion/round1
```

Converter chỉ chọn human annotation; prediction không đủ làm gold. Cần 100/100 annotation hợp lệ, rà review items, ghi quyết định gắn hash và người duyệt, xác nhận đã duyệt toàn bộ 100. Sau đó mới đóng gói test gold/corpus ba split; manifest/báo cáo phải ghi **AI-assisted human-reviewed**. Agreement độc lập `NOT_MEASURED`. Chưa chấm test và chưa tạo test gold trong lượt này.

## 8. Tái lập và chia sẻ

Lệnh tạo: `python -m scripts.49_prepare_test100_assisted_annotation --acknowledge-assisted-test`. Proposal nằm tại `data/interim/annotation/sprint03/test100_assisted_inputs_v1/span_proposals.json`. Công cụ từ chối ghi đè; để sinh lượt khác dùng `--output-dir` mới trong annotation/sprint03. Kiểm input hash/ID/text, không metadata ẩn, không span sai offset/bỏ sót nội dung và kiểm hash nguồn tham khảo. Script 15 và runner/model vẫn giữ cổng chặn test.

Đáp án nằm trong interim bị Git ignore; giữ riêng cho người duyệt, không tự công khai lên nhánh partner đang gán mù. **0 GB / 0 GiB cài đặt mới**. Gói prediction là artifact gán nhãn, không phải dung lượng cài thư viện. Kết quả kiểm thử và audit được lưu riêng trong cùng thư mục.

Nghiệm thu kỹ thuật lượt này: **190 test: 182 PASS, 8 SKIP, 0 FAIL** trong runtime WSL theo AGENTS.md. **550 hash file frozen + 4 kiểm tra kích thước nguồn raw không đổi**; các hash nội dung gói khớp manifest. Evidence: `tests_full.log`, `frozen_comparison.json`, `acceptance_report.json`. Các SKIP là tích hợp neural/CRF thiếu dependency trong runtime kiểm thử, không phải bỏ qua QA 100 prediction. Dung lượng artifact trước khi thêm acceptance report là 849.898 byte (~0,85 MB), cài mới 0 byte. Kiểm thử không xác nhận mọi nhãn ngữ nghĩa đúng; người duyệt vẫn cần xem toàn bộ 100 task.
