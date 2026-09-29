# Hướng dẫn Label Studio pilot T0 11 nhãn

Tài liệu này dành cho người phụ trách và partner cùng chạy pilot span địa chỉ trong Sprint 3. Có thể làm theo mà không cần đọc lịch sử trao đổi.

**Phiên bản guideline:** `s3-span-v1.0`
**Project dự kiến:** `DACN_S3_T0_PILOT_v1`
**Quy mô import:** 68 task pilot
**Trạng thái cập nhật 29/09/2026:** project có 68 task. Bản export `pilot_final.json` đã qua QA cấu trúc: 68 annotation hợp lệ, 0 lỗi, `READY_FOR_HUMAN_REVIEW`. Còn 7 task có cờ/note cần quyết định; chưa có gold pilot đã duyệt.

## Tiến độ hiện tại

- [x] Tạo project và lưu XML 11 nhãn.
- [x] Import đúng batch pilot 68 task.
- [x] Gán và export đủ 68 task; QA cấu trúc đạt.
- [ ] Duyệt 7 ca có cờ/note và ghi quyết định vào sổ.
- [ ] Xác nhận nội dung của 68 annotation, khóa guideline và ký duyệt canonical trước khi gọi dữ liệu là gold.

Có thể tiếp tục gán tay theo mục 6, hoặc nạp gợi ý rồi rà soát theo mục 6A. Giữ terminal Label Studio đang chạy; không import lại batch task.

## 1. Mục tiêu và phạm vi

Trong pilot này, người gán đánh dấu các span xuất hiện trong câu địa chỉ theo 11 nhãn, chọn hệ hành chính cho từng span, và chọn hệ của toàn câu khi đủ bằng chứng. Pilot dùng để phát hiện chỗ guideline khó áp dụng, kiểm tra giao diện và QA offset. Đây **chưa phải** benchmark test và **chưa phải** gold cho huấn luyện hoặc báo F1.

Chỉ import file này:

```text
D:\DACN\data\interim\annotation\sprint03\label_studio_pilot_import.json
```

File có đúng 68 task; giao diện chỉ cần cho người gán thấy `sample_id` và chuỗi `text`. Không import queue CSV đầy đủ, file benchmark, hay file chứa `GT_*`.

## 2. Vai trò

- **Người gán nhãn:** gán span đúng theo chuỗi nguyên bản, chọn hệ span, ghi cờ và note cho ca khó, rồi submit task.
- **Người duyệt/adjudicator:** xem các ca được gắn cờ, thống nhất cách xử lý, ghi quyết định vào sổ ca khó và chốt phiên bản guideline.
- **Người vận hành:** giữ bản XML/guideline đã dùng, xuất raw JSON từng vòng, chạy bộ QA và bàn giao report cùng các hash.

Một người có thể làm cả ba vai trò trong pilot. Khi chỉ một người gán, báo cáo đồng thuận giữa người gán phải để `NOT_MEASURED`.

## 3. Trước khi bấm gán

1. Giữ terminal đang chạy Label Studio mở. Nếu terminal báo `Starting development server at http://0.0.0.0:8080/`, mở trình duyệt Windows ở `http://localhost:8080`.
2. Tạo tài khoản local nếu Label Studio yêu cầu. Không cần bật chia sẻ Internet hoặc cấu hình cloud cho batch nhỏ này.
3. Mở trong repository các tài liệu sau để tra khi phân vân:
   - [Guideline 11 nhãn](span_11_annotation_guideline.md)
   - [XML giao diện](../../../configs/label_studio_span11.xml)
   - [Sổ quyết định ca khó](pilot_decision_log.csv)
4. Ghi lại phiên bản server. Trong một terminal WSL khác, chạy:

   ```bash
   source ~/.venv_labelstudio311/bin/activate
   label-studio --version
   ```

   Nếu venv của bạn dùng tên khác, thay đúng đường dẫn môi trường Label Studio đang chạy.

## 4. Tạo project và cấu hình giao diện

1. Trong Label Studio chọn **Create Project**.
2. Nhập tên `DACN_S3_T0_PILOT_v1`. Mô tả có thể ghi: `Pilot gán span địa chỉ T0, 11 nhãn, guideline s3-span-v1.0`.
3. Chọn tab **Labeling Setup** rồi chuyển sang **Code**.
4. Mở file [`configs/label_studio_span11.xml`](../../../configs/label_studio_span11.xml) trong VS Code/Notepad, sao chép toàn bộ nội dung và dán vào vùng XML trong Label Studio. Lưu cấu hình.
5. Kiểm tra phần xem trước:
   - Có dòng `Sample ID` và mã mẫu.
   - Có chuỗi địa chỉ nguyên văn.
   - Có đủ 11 nhãn span: `SoNha`, `TenDuong`, `Ngo/Hem`, `ToaNha/CanHo`, `PhuongXa`, `QuanHuyen`, `TinhThanh`, `MocDinhVi`, `HuongDi`, `GhiChu`, `Khac`.
   - Khi chọn một span, có lựa chọn hệ `cu`, `moi`, `khong_xac_dinh`.
   - Có lựa chọn hệ toàn câu `cu`, `moi`, `Lai` và phần cờ/note rà soát.
6. Lưu/tạo project. Label Studio đặt project ID trong URL hoặc trang project; ghi lại ID cùng phiên bản Label Studio vào nhật ký Sprint 3.

Nếu cấu hình báo XML không hợp lệ, hãy kiểm tra đã dán nguyên XML, không dán thêm dấu ``` hoặc tiêu đề Markdown. Chưa import dữ liệu cho đến khi preview hiện đủ các thành phần trên.

## 5. Import đúng batch 68 mẫu

1. Mở project vừa tạo và bấm **Import**.
2. Trong cửa sổ chọn file của Windows, đi tới `D:\DACN\data\interim\annotation\sprint03\` rồi chọn `label_studio_pilot_import.json`.
3. Chờ import xong. Data Manager phải có **68 tasks**.
4. Mở một task bất kỳ và xác nhận giao diện hiện `sample_id` cùng chuỗi gốc. Nếu không thấy `sample_id`, quay lại **Settings/Labeling Setup → Code**, kiểm tra XML đã có:

   ```xml
   <Header value="Sample ID" />
   <Text name="sample_id_display" value="$sample_id" />
   ```

5. Không import lại file lần thứ hai vào cùng project. Nếu lỡ import trùng và thấy 136 task, dừng gán; tạo project pilot mới, cấu hình XML và import đúng một lần để batch có danh sách sạch.

## 6. Cách gán một task

Với mỗi task, thực hiện theo thứ tự này:

1. Đọc câu từ đầu đến cuối. Không mở benchmark CSV, nhãn ground truth hay chuỗi gốc sạch để đoán phần bị thiếu.
2. Dùng chuột bôi đúng đoạn ký tự của một thực thể trên **chuỗi gốc**. Chọn một nhãn trong 11 nhãn.
3. Nhấp vào span vừa tạo. Ở phần **System of selected span**, chọn đúng một hệ:
   - `cu`: có bằng chứng span thuộc đơn vị/hệ hành chính cũ.
   - `moi`: có bằng chứng span thuộc đơn vị/hệ hành chính mới.
   - `khong_xac_dinh`: thành phần không đổi theo hệ, thiếu bằng chứng hoặc tên có thể thuộc nhiều hệ.
4. Lặp lại cho mọi span trong câu. Mỗi span phải có đúng một hệ.
5. Ở **Whole-address system, if clear**, chọn hệ toàn câu `cu`, `moi` hoặc `Lai` chỉ khi toàn câu cho đủ bằng chứng. Có thể để trống khi không xác định được.
6. Nếu gặp ca khó, chọn một hoặc nhiều `Review flags`, ghi diễn giải vào `Review note`, rồi submit. Cờ không thay thế nhãn span.
7. Bấm **Submit** để lưu task. Kiểm tra task chuyển khỏi trạng thái cần gán trước khi sang task tiếp theo.

Trong ảnh màn hình, khung bên phải hiện “Select a region to edit metadata” vì chưa có span nào được tạo/chọn. Đây là trạng thái bình thường. Sau khi tạo span, nhấp vào đoạn đã tô màu hoặc vùng tương ứng trong **Regions → Manual**; khi đó lựa chọn **System of selected span** mới hiện ra để gán `cu`/`moi`/`khong_xac_dinh`.

Nếu bấm **Submit** và nhận cảnh báo `Checkbox "span_system" is required`, nghĩa là có ít nhất một span chưa được gán hệ. Chọn từng vùng trong danh sách **Regions → Manual**, rồi tích đúng một giá trị trong **System of selected span**. Kể cả khi không biết hệ, vẫn phải chọn `khong_xac_dinh`. Làm lần lượt đến hết mọi vùng; cảnh báo này là kiểm tra bắt buộc của giao diện, không phải lỗi dữ liệu.

Trước khi submit, nhìn danh sách **Regions → Manual** để tìm span bị lặp. Nếu cùng một đoạn xuất hiện hai lần như `SoNha 50`, chọn đúng dòng thừa trong danh sách rồi bấm biểu tượng thùng rác màu đỏ ở phần thông tin vùng để xóa vùng đó. Giữ lại một vùng đúng, sau đó kiểm tra lại ranh giới và nhãn.

### Quy tắc cần nhớ

- Span phải giữ nguyên chính tả/OCR như văn bản. Không tự sửa dấu, không chuẩn hóa, không thêm từ bị lược.
- Ranh giới span là `[start, end)`: lấy ký tự đầu, không lấy ký tự tại `end`. Trên giao diện, chỉ cần bôi đúng phần chữ; script QA sẽ kiểm offset sau export.
- Không chồng lấp span. Khi hai nhãn kề nhau, tách thành hai span.
- Dấu phẩy, dấu chấm phẩy, ngoặc ngoài và khoảng trắng thường để nền (`O`). `O` không phải nút nhãn: để đoạn đó không được chọn.
- `Khac` dành cho thành phần địa chỉ có nghĩa nhưng không thuộc 10 nhãn khác. Không dùng `Khac` cho dấu câu, “nay là”, OCR vô nghĩa hoặc nội dung không phải địa chỉ.
- `QuanHuyen` luôn có hệ `cu`. Không tự tạo span `QuanHuyen` nếu địa chỉ mới không có huyện/quận.
- `MocDinhVi`: ví dụ `gần cầu Sài Gòn`, `đối diện chợ Bà Chiểu`.
- `HuongDi`: ví dụ `hướng Bình Thạnh`, `rẽ trái vào`. Nếu câu tiếp tục có tên đường nhận diện được, tách tên đường thành span `TenDuong`.
- `GhiChu`: ví dụ `tầng 3`, `cổng sau` khi đó là chỉ dẫn tiếp cận.
- Với “Phường A (nay là Phường B)”, gán riêng A và B thành hai span `PhuongXa`; để “nay là”, dấu ngoặc và khoảng trắng là `O`. Chọn hệ cũ/mới cho A/B khi ngữ nghĩa rõ.
- Nếu một đoạn không đọc được vì OCR, không đoán: để `O`, chọn `unreadable_ocr` và ghi note nếu cần.

### Ví dụ thao tác

Chuỗi: `50, Pasteur, Phường Bến Nghé, Quận 1, Thành phố Hồ Chí Minh`

- Chọn `50` → `SoNha` → hệ `khong_xac_dinh` nếu câu không nói rõ phiên bản.
- Chọn `Pasteur` → `TenDuong` → thường là `khong_xac_dinh` nếu văn bản không nêu thời điểm.
- Chọn cụm đơn vị phường nguyên văn → `PhuongXa`; chỉ gán `cu`/`moi` nếu có căn cứ từ ngữ cảnh hành chính, nếu không chọn `khong_xac_dinh`.
- Chọn `Quận 1` → `QuanHuyen` → hệ `cu`.
- Tỉnh/thành phố chọn `TinhThanh`; nếu không xác định được phiên bản từ chính văn bản thì dùng `khong_xac_dinh`.
- Không chọn các dấu phẩy hoặc khoảng trắng.

Đây là ví dụ minh họa thao tác, không phải đáp án gold cho một mẫu pilot cụ thể. Tra guideline trước khi quyết định hệ của tên hành chính trùng nhau giữa hai mốc.

### Ví dụ ngay trên task đang mở

Task đang hiện câu:

```text
01, Đường Mỹ Phú 1B, Phường Tân Phú, Quận 7, Thành phố Hồ Chí Minh
```

Tạo lần lượt 5 span sau, không chọn dấu phẩy:

| Bôi đúng đoạn | Nhãn | Hệ span đề xuất | Căn cứ |
| --- | --- | --- | --- |
| `01` | `SoNha` | `khong_xac_dinh` | Số nhà không tự cho biết hệ hành chính. |
| `Đường Mỹ Phú 1B` | `TenDuong` | `khong_xac_dinh` | Tên đường không tự cho biết hệ hành chính. Giữ cả từ `Đường`. |
| `Phường Tân Phú` | `PhuongXa` | `cu` | Đọc trong chuỗi cùng `Quận 7`, là cấp huyện của cấu trúc cũ. |
| `Quận 7` | `QuanHuyen` | `cu` | `QuanHuyen` chỉ thuộc hệ cũ. |
| `Thành phố Hồ Chí Minh` | `TinhThanh` | `khong_xac_dinh` | Bản thân tên thành phố không xác định được phiên bản; hệ toàn câu là `cu` vì có `Quận 7`. |

Sau khi gán span, ở **Whole-address system, if clear** chọn `cu`. Không chọn review flag và để note trống nếu bạn không phát hiện ca khó. Bấm **Submit** ở góc dưới bên phải để lưu task. Nếu bạn có căn cứ trong guideline khiến hệ của một span hành chính cụ thể chưa rõ, dùng `khong_xac_dinh` cho span đó và ghi `temporal_ambiguity`; không sao chép hệ toàn câu sang mọi span một cách máy móc.

## 6A. Nạp gợi ý 68 mẫu để chỉ cần rà soát

Bộ gợi ý ở `data/interim/annotation/sprint03/pilot_span11_candidate_answers.json` có 68 mẫu và 250 span. Đây là **candidate_not_gold**, cần người gán kiểm lại từng task. Script `scripts/15_import_pilot_predictions.py` biến các span, hệ từng span, hệ toàn câu và cờ/note thành **prediction** trên chính 68 task hiện có. Nó không tạo task mới, không tạo annotation đã submit và bỏ qua các task bạn đã submit. Mỗi prediction mang `model_version=s3_span11_manual_candidates_v1_not_gold` để truy nguồn. Những ca có review flag/note càng cần xem kỹ.

1. Trong Label Studio, bấm ảnh tài khoản góc phải → **Account & Settings** → **Legacy Token**. Sao chép token nhưng **không gửi token qua chat hoặc lưu vào repository**. Nếu chỉ có Personal Access Token, tạo PAT rồi dùng `--token-kind pat` ở các lệnh dưới.
2. Mở **terminal WSL thứ hai**; giữ terminal server Label Studio đang chạy. Đặt token vào biến môi trường chỉ trong terminal này:

   ```bash
   cd /mnt/d/DACN
   source ~/.venv_labelstudio311/bin/activate
   read -rsp 'Label Studio token: ' LABEL_STUDIO_API_TOKEN
   export LABEL_STUDIO_API_TOKEN
   echo
   ```

3. Chạy kiểm tra **không ghi dữ liệu**. Nếu bạn dùng PAT, thêm `--token-kind pat` vào từng lệnh. Script dừng nếu project không đúng tên, thiếu 68 task, lệch `sample_id`/text/XML hoặc thiếu thông tin annotation/prediction:

   ```bash
   python -m scripts.15_import_pilot_predictions --project-id 1
   ```

4. Nạp thử **một mẫu chưa submit** để kiểm giao diện. Ví dụ `s3_48761158958451ae` là mẫu số 4 trong bộ đề xuất; nếu đã submit, chọn một `sample_id` khác trong danh sách `pending_sample_ids` của bước 3:

   ```bash
   python -m scripts.15_import_pilot_predictions --project-id 1 \
     --sample-id s3_48761158958451ae --apply
   ```

5. Mở task vừa nạp trong Label Studio. Nếu prediction chưa hiện, vào **Settings → Machine Learning**, bật **Show predictions to annotators in the Label Stream and Quick View** hoặc tùy chọn **Use predictions to prelabel tasks** tương ứng phiên bản đang chạy. Prediction gốc là read-only; dùng nút **Copy prediction**/tạo annotation từ prediction nếu giao diện không tự chép vào annotation mới. Kiểm tra ví dụ có 5 span và mỗi span có `System of selected span`. Chỉ khi thao tác chỉnh span/hệ và Submit hoạt động đúng mới nạp phần còn lại:

   ```bash
   python -m scripts.15_import_pilot_predictions --project-id 1 --apply
   ```

6. Rà soát **từng task**, đặc biệt các mẫu có `review_flags` hoặc `review_note`; chỉnh các span/hệ sai rồi bấm **Submit**. Prediction chưa được Submit không phải annotation gold. Task đã có annotation trước khi nạp được script bỏ qua, hãy rà soát chúng riêng.
7. Sau khi xong, xóa biến token khỏi terminal và tiếp tục export/QA theo mục 8–10:

   ```bash
   unset LABEL_STUDIO_API_TOKEN
   ```

Không dùng lớp prediction này cho người gán thứ hai nếu muốn đo **đồng thuận độc lập** bằng Cohen's Kappa/exact-span F1; họ cần gán trên bản không thấy gợi ý. Xem [tài liệu prediction](https://labelstud.io/guide/predictions), [API import prediction vào task hiện có](https://api.labelstud.io/api-reference/api-reference/projects/import-predictions), [API token](https://labelstud.io/guide/access_tokens).

## 7. Chạy thử vài task rồi mới gán hết

Nên gán trước **5 task**, submit, rồi xuất một bản nháp để xác nhận giao diện tạo đúng dạng dữ liệu. Bản nháp 5 task sẽ thiếu 63 mẫu; báo cáo QA sẽ ghi `INCOMPLETE_OR_INVALID` và `missing_from_export=63`. Đó là trạng thái bình thường ở vòng chạy thử, chưa phải lỗi nhãn. Sửa giao diện hoặc cách gán nếu report chỉ ra lỗi offset/hệ, sau đó tiếp tục batch.

Không cần đánh dấu task là skipped chỉ vì khó. Gắn cờ và note, submit phần có thể gán; adjudicator sẽ quyết định ca đó. Nếu không có thực thể nào trong câu, không tạo span; vẫn submit task. Nếu hệ toàn câu không rõ, để trống.

## 8. Xuất JSON của từng vòng

1. Từ trang project chọn **Export**.
2. Chọn định dạng **JSON** (raw Label Studio JSON), rồi tải xuống. Không chọn CSV hay `JSON_MIN`, vì chúng có thể lược region ID/metadata mà converter cần.
3. Trong cửa sổ lưu file của Windows, tạo/chọn thư mục:

   ```text
   D:\DACN\data\interim\annotation\sprint03\exports\
   ```

   Nếu thư mục chưa có, tạo thư mục `exports` trước trong Explorer.
4. Đặt tên có vòng và ngày, ví dụ `pilot_2026-09-29_round01.json`, `pilot_2026-09-29_round02.json`. Không ghi đè export vòng trước.
5. Export giữa chừng có thể chỉ gồm task đã gán. Export cuối phải có đủ 68 task. Label Studio Community thường xuất các task đã có annotation; API có tùy chọn `download_all_tasks=true` để lấy cả task chưa gán. Xem [tài liệu export](https://labelstud.io/guide/export).

Mỗi vòng export là một bản chụp dữ liệu tại thời điểm đó. Khi sửa nhãn trên Label Studio, tạo tên export vòng mới, không thay nội dung bản cũ.

## 9. Chạy QA trên export

Giữ terminal đang chạy Label Studio mở. Mở terminal WSL thứ hai và chạy:

```bash
cd /mnt/d/DACN
source ~/.venv_labelstudio311/bin/activate
python -m scripts.11_convert_label_studio_pilot \
  --export data/interim/annotation/sprint03/exports/pilot_2026-09-29_round01.json \
  --output-dir data/interim/annotation/sprint03/pilot_conversion/round01
```

Thay `round01` bằng tên vòng export thực tế. Script chỉ dùng thư viện chuẩn; nếu Label Studio venv có Python 3.11 thì có thể dùng chính venv đó.

Đọc hai file tạo ra:

- `pilot_qa_report.json`: số task, trạng thái từng `sample_id`, lỗi cấu trúc, hash file và thời gian gán nếu export cung cấp.
- `pilot_review_items.json`: task có cờ/note để adjudicator xem xét.

Diễn giải kết quả:

| Report | Ý nghĩa | Hành động |
| --- | --- | --- |
| `INCOMPLETE_OR_INVALID`, `missing_from_export` lớn | Export vòng giữa hoặc còn task chưa submit | Tiếp tục gán; không công nhận là lỗi toàn batch |
| `invalid_annotation` / lỗi ở `issues` | Nhãn/hệ/offset/format chưa hợp lệ | Xem `issues`, sửa task tương ứng trong Label Studio, export vòng mới |
| `READY_FOR_HUMAN_REVIEW` | Đủ task và qua kiểm tra cấu trúc tự động | Người duyệt vẫn phải xem cờ/note và tính đúng ngữ nghĩa |
| `agreement.status=NOT_MEASURED` | Chỉ có một người gán độc lập | Giữ nguyên trạng thái, không ghi Kappa bằng 0 |

`READY_FOR_HUMAN_REVIEW` **không tự động có nghĩa là gold đã được duyệt**. Script kiểm tra cấu trúc, không hiểu địa chỉ đúng/sai về mặt ngữ nghĩa.

## 10. Chốt ca khó và bàn giao

1. Adjudicator xem từng mục trong `pilot_review_items.json`, mở task tương ứng bằng `sample_id` trong Label Studio.
2. Thống nhất nhãn, ranh giới, hệ và cách xử lý. Ghi mỗi quyết định vào [`pilot_decision_log.csv`](pilot_decision_log.csv): sample ID, đoạn liên quan, quyết định, lý do và có thay đổi guideline hay không.
3. Nếu guideline đổi, tăng version (ví dụ `s3-span-v1.1`), sửa ngày/trạng thái trong guideline, cập nhật project bằng XML hiện hành nếu XML cũng đổi; sau đó chạy lại các task bị ảnh hưởng và export vòng mới.
4. Khi đủ 68 task, `issues` rỗng và mọi ca review đã được xử lý, chạy converter trên export cuối vào thư mục riêng `pilot_conversion/final`.
5. Người duyệt đọc canonical candidate và xác nhận nội dung. Chỉ sau bước ký duyệt này mới sao chép candidate sang khu vực gold chính thức. Giữ raw export, QA report, review log, decision log, version/hash của XML và guideline cạnh bản gold.
6. Khóa guideline/config bằng commit hoặc bản lưu có hash trước khi mở 100 mẫu frozen benchmark. Không dùng 100 mẫu test để sửa guideline hoặc chọn mô hình.

## 11. Hash cần lưu khi bàn giao

Trong terminal WSL ở `D:\DACN` (hiện thành `/mnt/d/DACN`), chạy:

```bash
cd /mnt/d/DACN
sha256sum \
  configs/label_studio_span11.xml \
  docs/sprints/sprint_03/span_11_annotation_guideline.md \
  data/interim/annotation/sprint03/label_studio_pilot_import.json \
  data/interim/annotation/sprint03/exports/pilot_2026-09-29_round01.json
```

Ghi hash cùng Label Studio version, project ID, ngày export và người gán trong biên bản bàn giao. Đổi tên đường dẫn export trong lệnh cho đúng vòng cuối.

## 12. Checklist trước khi báo hoàn thành S3-01

- [ ] Project đúng tên, project ID và Label Studio version đã ghi.
- [ ] XML preview đủ 11 labels, `sample_id`, system span, system toàn câu, cờ và note.
- [ ] Đã import đúng 68 task, không import queue/test.
- [ ] 68/68 task có trạng thái đã submit hoặc lý do loại/giữ lại được ghi rõ.
- [ ] Export cuối là raw JSON và có hash.
- [ ] QA report không có `issues`, 68 task được xử lý, canonical candidate được tạo.
- [ ] Mọi cờ/note đã được adjudicate hoặc ghi rõ lý do còn pending.
- [ ] Nếu chỉ một người gán, inter-annotator agreement ghi `NOT_MEASURED`.
- [ ] Gold chỉ được tạo sau khi người duyệt ký duyệt candidate.
- [ ] Guideline/XML đã khóa version trước khi mở benchmark test.

## Tài liệu tham chiếu

- [Label Studio: tạo project](https://labelstud.io/guide/setup_project)
- [Label Studio: import task](https://labelstud.io/guide/tasks)
- [Label Studio: hướng dẫn gán nhãn](https://labelstud.io/guide/labeling)
- [Label Studio: export raw JSON](https://labelstud.io/guide/export)
- [Guideline T0 11 span của dự án](span_11_annotation_guideline.md)
