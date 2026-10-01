# Kế hoạch bàn giao agent: gán lại 68 pilot và 232 train/dev bằng ứng viên có truy vết nguồn

**Cập nhật quyết định vận hành 01/10/2026:** chủ dự án chọn prediction cho cả 68 và 232. Quy trình pilot độc lập được mô tả bên dưới là phương án nghiên cứu ban đầu; lần gán v2 hiện tại dùng rà soát có hỗ trợ và ghi agreement độc lập `NOT_MEASURED`. Thực hiện theo [hướng dẫn hiện hành](09_label_studio_400_step_by_step.md). Test 100 vẫn gán mù, không prediction.

## 1. Mục tiêu và quyết định phạm vi

Tạo **hai gói gán nhãn phiên bản mới** cho đúng 68 pilot và 232 mẫu batch 02 hiện có. Sinh ứng viên span từ cấu trúc và lịch sử biến đổi của dữ liệu nguồn, sau đó để người gán kiểm tra, sửa và Submit. Đợt 68 pilot được gán lại độc lập để kiểm tra độ tin cậy của pilot gold v1; 232 mẫu được gán có hỗ trợ prediction để giảm thao tác thủ công.

Trong lần này, “tạo lại” nghĩa là tạo **import, trace và prediction v2** cho cùng `sample_id`, `text`, `group_id`, `planned_split` của 300 mẫu đã chọn. Không lấy lại mẫu ngẫu nhiên hoặc sửa chuỗi địa chỉ. Như vậy 68 v1 vẫn so sánh được với bản gán lại, còn kế hoạch split và 100 ID test không bị thay đổi. Nếu phát hiện bắt buộc phải đổi `text` hoặc mẫu, báo thành yêu cầu phiên bản corpus khác và chạy lại toàn bộ preflight; không âm thầm đổi ngay trong công việc này.

Không sửa hoặc ghi đè `data/raw/`, `third_party/`, pilot gold v1, queue/import hiện hành, export cũ, benchmark test hay gazetteer. Không đưa 100 test, 20 VQA hold hoặc `GT_*` vào hai project mới. Các kết quả tự sinh chỉ là **candidate**, chưa phải gold.

### Bằng chứng và quy tắc đang khóa

- Đọc `docs/sprints/sprint_03/span_11_annotation_guideline.md` (`s3-span-v1.1`), `docs/sprints/sprint_03/t0_corpus_split_protocol_v1.md`, `docs/sprints/sprint_03/README.md` và `docs/data_quality.md` trước khi sửa code.
- `scripts/10_prepare_span_annotation.py`: 68 pilot = 24 địa chỉ OSM cũ, 24 địa chỉ mới/đã ánh xạ, 20 seed ca hiếm có kiểm soát.
- `scripts/16_prepare_t0_corpus_batch.py`: 232 batch 02 = 60 `osm_old_3tier`, 60 `osm_new_2tier`, 40 `synthetic_noise`, 40 `synthetic_missing`, 32 `synthetic_hybrid`.
- `scripts/14_prepare_pilot_answer_key.py` dùng vị trí mẫu và text để đoán; `scripts/20_prepare_batch02_predictions.py` chủ yếu suy từ text. Chúng chỉ là tài liệu đối chiếu, **không phải nguồn truth** cho ứng viên v2.
- `scripts/15_import_pilot_predictions.py` đã kiểm soát số task, ID, text và chặn test. Có thể tái sử dụng nếu ứng viên v2 tuân đúng schema script này.
- `scripts/11_convert_label_studio_pilot.py`, `scripts/17_convert_span_annotation_batch.py`, `scripts/18_audit_corpus_split.py` là các cổng QA/split hiện hành; không bỏ qua các cổng này.

## 2. Hợp đồng nhãn: tách hai loại “hệ”

Mỗi thành phần có hai thông tin khác nhau trong sidecar nội bộ:

1. `construction_system`: nguồn/thao tác sinh mẫu đã lấy đơn vị từ hệ `cu` hay `moi`, kèm ID, khóa hành chính, phiên bản, bằng chứng ánh xạ. Đây là **provenance**, có thể biết dù chuỗi chỉ ghi một tên dùng ở cả hai thời kỳ.
2. `span_system_candidate`: nhãn `cu`, `moi`, `khong_xac_dinh` đề xuất cho **span hiện trên văn bản**, phải đúng guideline. Không sao chép `construction_system` máy móc sang nhãn.

Áp dụng trước mắt:

| Thành phần trong text | Ứng viên `system` | Lý do / điều kiện |
| --- | --- | --- |
| `SoNha`, `TenDuong` | Luôn `khong_xac_dinh` | Quyết định của chủ dự án: số nhà và tên đường tự chúng không chỉ ra hệ hành chính. |
| `QuanHuyen` | `cu` | Theo guideline, cấp huyện thuộc hệ ba cấp cũ. Không tạo span này cho địa chỉ mới hai cấp nếu text không có. |
| `PhuongXa` | `cu`/`moi` nếu đủ chứng cứ phiên bản hoặc ngữ cảnh; nếu tên dùng được ở cả hai hệ và text không phân biệt thì `khong_xac_dinh` | Lưu hệ xây dựng riêng để người rà soát có thể tra cứu. Không suy hệ từ việc chỉ có/không có `QuanHuyen` trên toàn câu. |
| `TinhThanh` | `cu`/`moi` chỉ khi có chứng cứ phân biệt; tên còn dùng nguyên như `Hà Nội`, `Thành phố Hồ Chí Minh` thì `khong_xac_dinh` | Tên tỉnh/thành giống nhau qua hai mốc không mang thông tin thời kỳ trong span. |
| `Ngo/Hem`, `ToaNha/CanHo`, `MocDinhVi`, `HuongDi`, `GhiChu`, `Khac` | Mặc định `khong_xac_dinh`; chuyển thành hệ khác chỉ khi guideline cho phép và có bằng chứng rõ trong text | Không lấy hệ toàn câu làm hệ span. |

Ví dụ `12 Đường A, Phường Phú Hòa, Quận B, Thành phố Hồ Chí Minh` được sinh từ một bản ghi cũ: `12` và `Đường A` là `khong_xac_dinh`; `Quận B` là `cu`; `Phường Phú Hòa` chỉ là `cu` nếu tên/ID/phiên bản và chính sách gán nhãn cho phép khẳng định; khi cùng tên còn tồn tại ở hệ mới và text không phân biệt, `span_system_candidate=khong_xac_dinh` dù `construction_system=cu`. Tương tự, `Thành phố Hồ Chí Minh` có thể có `construction_system=cu` trong dữ liệu nguồn nhưng hệ span vẫn `khong_xac_dinh`.

Nếu nhóm nghiên cứu muốn dùng provenance để gán `cu`/`moi` cho **mọi** phường/tỉnh trùng tên, agent phải đề xuất thay đổi guideline thành phiên bản mới, ghi rõ đây là chính sách gán dựa trên metadata ẩn, cập nhật converter và đánh giá trước khi dùng. Không tự đổi chuẩn `s3-span-v1.1` trong công việc này.

`address_system` (T1 toàn câu) là một trường riêng. Chỉ đề xuất `cu`, `moi`, `Lai` khi có đủ bằng chứng theo guideline. `synthetic_missing` mất huyện không tự thành `moi`; `synthetic_hybrid` chỉ đề xuất `Lai` khi phường mới và huyện cũ đều được xác minh. Nếu text không cho thấy hệ, để trống ứng viên T1 và ghi lý do.

## 3. Thứ tự hiện thực cho agent

### Bước 0 — Chụp đầu vào và khóa hợp đồng

1. Đọc hai import hiện có: `data/interim/annotation/sprint03/label_studio_pilot_import.json` và `data/interim/annotation/sprint03/label_studio_batch02_import.json`; đọc các queue/manifest tương ứng. Xác nhận đúng 68 + 232 ID duy nhất và chuỗi `text` nguyên bản.
2. Ghi SHA-256 của hai import, hai queue, XML `configs/label_studio_span11.xml`, guideline, bảng ánh xạ và các file nguồn dùng dựng ứng viên. Lưu kết quả trong manifest v2. Không đưa hash của dữ liệu riêng tư vào task Label Studio nếu không cần.
3. Xác nhận 68 và 232 không trùng ID với test 100; so `group_id`, `planned_split` với preflight hiện hành. Nêu rõ nếu 138 cặp gần giống vẫn chờ quyết định: công việc gán nhãn không tự giải quyết rủi ro rò rỉ split.
4. Tạo thư mục output mới, ví dụ `data/interim/annotation/sprint03/reannotation_v2/`. Mọi script mới nhận `--output-dir` và từ chối ghi đè nếu chưa có cờ rõ ràng; tránh gọi lại script 10/16 để làm biến đổi các file cố định đã được dùng.

**Cổng:** danh sách 300 `(sample_id, text)` được khóa; mọi thay đổi dữ liệu gốc dừng quy trình và báo nguyên nhân.

### Bước 1 — Tạo trace của từng thành phần ngay tại lúc dựng địa chỉ

Thêm mô-đun dùng chung (ví dụ `src/data/span_trace.py`) để biểu diễn một thành phần trước khi nối thành chuỗi:

```text
sample_id, field, surface, source_value, source_ref, source_row,
source_key, entity_id_if_verified, construction_system,
transformation, start, end, match_status, evidence, abstain_reason
```

`field` ánh xạ rõ sang 11 nhãn; `surface` là **đúng chuỗi xuất hiện** sau biến đổi. `start/end` là offset Python trên `text` cuối cùng. Khi dựng chuỗi mới, dùng một hàm render nối các thành phần theo thứ tự và trả offset trong cùng lượt; đừng nối xong rồi lấy `str.find()` đầu tiên vì địa chỉ có thể lặp tên/số. Mỗi span phải thỏa `text[start:end] == surface`.

Với 300 text đã khóa, generator cần chạy chế độ **replay/trace**: dùng đúng hàng nguồn, seed và thao tác đã tạo từng chuỗi để xác minh text dựng lại khớp byte hoặc chuỗi Unicode sau đọc JSON. Nếu code cũ không ghi đủ thao tác để replay chính xác, đối sánh thành phần với text theo thứ tự và chỉ nhận match duy nhất, không chồng lấp. Trường hợp trùng lặp, thay đổi không xác định hoặc OCR phá hỏng ranh giới thì **abstain** thành phần đó, không tự bịa offset. Không đổi text chỉ để việc replay dễ hơn.

### Bước 2 — Gắn nguồn cho từng nhóm mẫu

| Nhóm | Cách lấy span ứng viên | Bắt buộc abstain/rà soát |
| --- | --- | --- |
| 24 pilot cũ + 60 batch cũ | Đối chiếu hàng OSM gốc (`SoNha`, `TenDuong`, `PhuongXa`, `QuanHuyen`, `TinhThanh`) với text khóa; dùng provenance OSM và khóa cũ đầy đủ tỉnh–huyện–xã. | Text OSM không khớp trường, trường xuất hiện hai lần, thiếu ID/phiên bản hành chính, tên dùng chung cũ/mới. |
| 24 pilot mới + 60 batch mới | Lấy thành phần đã dựng từ ánh xạ cũ→mới có **một đích đã xác minh** hoặc bản ghi mới quan sát trực tiếp; giữ ID đích, source hash và loại bằng chứng. | Một khóa cũ nhiều đích, không có bằng chứng đích, tên giống nhau qua hai hệ. Không thêm `QuanHuyen`. |
| 32 lai | Lấy phường mới và huyện cũ từ đúng cạnh ánh xạ một đích; ghi mỗi span cùng nhánh nguồn của nó. Số nhà/đường vẫn không xác định. | Cạnh A/M chưa có đích quan sát, không xác minh được một trong hai hệ. Không suy đích từ tên gần giống. |
| 40 nhiễu | Theo dõi từng phép viết tắt, đổi chữ hoa/thường, OCR ở **cấp thành phần** và lập ánh xạ ký tự cũ→mới; offset là trên text nhiễu cuối. | OCR làm thành phần không đọc được hoặc thay đổi không thể căn chỉnh chắc chắn: không đưa span đoán, đặt `unreadable_ocr` khi thích hợp. |
| 40 thiếu trường | Truy đúng biến đã bị bỏ; chỉ các thành phần còn hiện diện có span. | Không tạo span rỗng, không dùng `KieuThieu` để gán nội dung không có trong text; không suy T1 mới chỉ vì mất huyện. |
| 20 pilot ca hiếm | Dùng template thành phần có offset được khai báo/kiểm riêng theo seed gốc, hoặc abstain và đưa vào queue thủ công. | Không biến `candidate_rare` thành span nếu không xác định được ranh giới thực; không dựa vào pilot gold v1 để tạo đáp án. |

Một địa chỉ `Phường Phú Hòa` có cùng tên ở hai hệ cần lưu cả `source_key/ID/validity` và trạng thái tên trùng. Nếu không có bằng chứng cho nhãn hệ trên chính nội dung hiển thị theo guideline, ứng viên span là `khong_xac_dinh`, còn nguồn cũ/mới vẫn ở trace. Đây là trường hợp kiểm soát chất lượng, không phải lỗi thiếu dữ liệu.

### Bước 3 — Sinh hai gói task v2 và ứng viên v2

1. Sinh `pilot68_import.json` và `batch232_import.json` với **chỉ** `data.sample_id` và `data.text` (hoặc đúng cấu trúc import đang khóa). So khớp từng cặp ID/text với import v1, không thêm `GT_*`, `HeQuyChieu`, `KieuThieu`, `Span_He_Detail`, nhãn ứng viên, `group_id` hay `source_ref` vào phần hiển thị cho người gán.
2. Sinh `pilot68_candidates.json`, `batch232_candidates.json` theo schema `scripts/15_import_pilot_predictions.py`: mỗi bản ghi `status=candidate_not_gold`, `sample_id`, `text`, spans với `start/end/label/system`, `address_system` nếu có chứng cứ, review flags/note hợp lệ. Mỗi candidate phải có bản ghi private tương ứng trong `trace.jsonl` ghi bằng chứng và cách tính offset.
3. Xuất `coverage_report.json` theo nhóm 24/24/20 và 60/60/40/40/32: số span tự gán, số abstain, lý do abstain, số tên hành chính trùng thời kỳ, số T1 được đề xuất. **Không đặt mục tiêu 100% auto-label**; ưu tiên precision và khả năng truy vết.
4. Tạo `manual_review_queue.csv` ghi `sample_id`, khoảng text/field cần xét, lý do, nguồn tham chiếu nội bộ và mức ưu tiên; không chứa đáp án test.
5. Đặt tên model version mới, chẳng hạn `s3_span11_source_trace_v2_not_gold`, để không nhầm với prediction cũ hoặc gold.

### Bước 4 — QA tự động trước khi mở Label Studio

Agent thêm kiểm tra hồi quy vào `tests/test_data_pipeline.py` vì công việc sửa generator/logic dữ liệu, rồi chạy các kiểm tra sau trong WSL đúng môi trường dự án:

- 68 + 232 ID duy nhất; từng `sample_id` và `text` trùng import đã khóa; không có ID thuộc test 100 hoặc VQA hold.
- Từng candidate span không rỗng, offset hợp lệ, `text[start:end]` khớp đúng literal, không chồng lấp, nằm trong 11 nhãn, có `system` thuộc 3 giá trị. Kiểm offset với Unicode tiếng Việt và ký tự ngoài BMP nếu có.
- `SoNha`/`TenDuong` luôn `khong_xac_dinh`, `QuanHuyen` luôn `cu`; các phần bị drop không có span; địa chỉ mới hai cấp không tự có huyện.
- Mọi span tự gán có trace tới thành phần nguồn và phép biến đổi; mọi ánh xạ hành chính dùng đúng khóa cũ đầy đủ và duy nhất/quan sát trực tiếp. Không nhận mã cũ candidate bên thứ ba làm ID đã xác minh.
- Import JSON không chứa metadata đáp án. Manifest lưu hash input/output, seed, guideline/XML version, logic version và số lượng theo từng nhóm.
- Các ca replay/offset không chắc chắn xuất hiện trong queue abstain, không thành prediction khẳng định.

Chạy `python -m unittest discover -s tests -v` trong WSL có đủ dependency theo `AGENTS.md`. Nếu suite không chạy trọn vì môi trường, báo rõ phần đã/chưa chạy; không tuyên bố QA hoàn tất chỉ từ thống kê số lượng.

### Bước 5 — Gán lại trên Label Studio theo hai chế độ

**Pilot 68: vòng kiểm độc lập.** Tạo project mới từ `pilot68_import.json` và XML đã khóa. Sinh candidate file song song ở bước 3 nhưng **chưa import prediction vào project pilot**. Người gán thứ hai không xem pilot gold v1, candidate file hoặc trace trước khi Submit và export bản gán độc lập. Nếu cùng người gán lại 68 mẫu, gọi kết quả là kiểm tra nhất quán của một người, không gọi là Cohen’s Kappa giữa người gán. Sau export, so gold v1 với bản mới theo exact-span F1, nhãn hệ, T1; rà mọi bất đồng và lập biên bản quyết định. Có thể mở candidate v2 lúc phán quyết sau vòng độc lập.

**Batch 232: gán có hỗ trợ prediction.** Tạo project train/dev mới từ `batch232_import.json` và cùng XML. Dùng `scripts/15_import_pilot_predictions.py` ở chế độ dry-run với `--expected-count 232`, project title/ID mới, candidate file v2 và model version v2; chỉ `--apply` khi các kiểm tra project/count/ID/text đều đúng. Người gán phải mở từng task, kiểm tra và sửa mọi span, hệ span và T1 trước khi Submit. Prediction không tự biến thành annotation/gold.

Không mở hoặc nạp prediction vào project test 100 trong công việc này. Nếu cần ước lượng chất lượng nhãn 232, chọn một mẫu con để người thứ hai gán **mù**, rồi tính agreement riêng; việc duyệt prediction của một người không tạo agreement giữa người gán.

### Bước 6 — Export, QA, phán quyết và phát hành phiên bản mới

1. Export **raw JSON** của hai project ra đường dẫn khác nhau trong `data/interim/annotation/sprint03/exports/reannotation_v2/`, giữ từng vòng export và hash.
2. Chạy converter 68 bằng `scripts/11_convert_label_studio_pilot.py`; chạy converter 232 bằng `scripts/17_convert_span_annotation_batch.py --role train_dev_batch02` với queue v2 hoặc queue gốc đã kiểm exact ID/text. Không truyền nhầm queue test. Kiểm báo cáo đủ 68/68 và 232/232, `issues=[]`, sau đó xem `review_items` và mọi ca abstain/khác prediction.
3. Người phụ trách xác nhận đã xem **tất cả** task, ghi quyết định và lý do cho ca khó. Sai phải sửa trong Label Studio, export vòng mới, chạy converter lại. `READY_FOR_HUMAN_REVIEW` là trạng thái QA cấu trúc, chưa phải gold.
4. Đối chiếu 68 bản gán độc lập với pilot gold v1. Phân loại bất đồng `boundary`, `label`, `span_system`, `T1`, `missing/extra`, `guideline ambiguity`; giải quyết theo guideline có version. Lưu người duyệt, ngày, quyết định, lý do và hash của hai export. Nếu đổi guideline, khóa bản mới trước khi mở test.
5. Chỉ sau phán quyết mới phát hành pilot gold v2 và batch02 gold v1 với manifest/hash riêng trong `data/processed/annotation/sprint03/`; giữ v1 nguyên trạng. Tích hợp vào train/dev theo phân bổ group-disjoint hiện hành sau khi cổng 138 cặp gần giống được giải quyết. Không gọi `corpus_v1` hoàn tất khi chưa có 100 test blind đã gán và split audit đạt yêu cầu.

## 4. Đầu ra agent phải giao

| Đầu ra | Nội dung tối thiểu |
| --- | --- |
| Code trace/replay và lệnh CLI | Sinh v2 có output directory, không ghi đè bản cũ; tài liệu cách chạy trong WSL. |
| `pilot68_import.json`, `batch232_import.json` | Đúng 68/232 task, chỉ ID/text, trùng input đã khóa. |
| Hai candidate JSON | Schema import prediction hợp lệ, ghi `candidate_not_gold`; không chứa test. |
| `trace.jsonl`/`manual_review_queue.csv` | Offset, nguồn, thao tác biến đổi, evidence, abstain và lý do cho từng thành phần. |
| `generation_manifest.json`, `coverage_report.json` | Hash, version, seed, số lượng theo strata, coverage/abstain. |
| Kiểm thử và báo cáo QA | Kết quả suite, kiểm schema/offset/provenance, các hạn chế chưa xử lý. |
| Hướng dẫn cho người gán | Hai project, pilot độc lập, batch 232 có prediction, export đúng file và phán quyết. |
| Sau khi có người gán | Export raw, canonical candidate, review log, agreement pilot đúng loại, gold v2/manifest đã duyệt; thiếu người gán thì báo trạng thái chờ, không tự công bố gold. |

Các file trong `data/interim/` có thể bị Git ignore. Nếu agent/partner làm ở checkout khác, bàn giao bản import, candidate, trace/manifest và export qua kênh tệp riêng có kiểm hash; không mặc định `git push` sẽ mang theo chúng.

## 5. Tiêu chí dừng và trách nhiệm của người dùng

Agent có thể tự làm bước 0–4 và chuẩn bị hai project/lệnh import nếu Label Studio/API đang truy cập được. Người dùng hoặc annotator phải thực hiện vòng gán độc lập 68 (không xem prediction), duyệt 232 prediction từng task, phán quyết bất đồng và ký biên bản gold. Agent không được xác nhận thay rằng một người đã xem đủ task. Kết quả cuối của vòng code là **300 task và candidate sẵn sàng để gán**, chưa phải 300 gold. Khi export và quyết định đã có, agent tiếp tục converter, audit, đóng gói theo bước 6.

## 6. Prompt ngắn để giao agent thực hiện

> Trong repository `D:\DACN`, hiện thực đầy đủ kế hoạch tại `docs/sprints/sprint_03/07_source_derived_reannotation_plan.md`. Giữ nguyên 68 pilot, 232 batch02 theo cặp `sample_id,text` và 100 test frozen. Tạo import v2, trace từng thành phần ngay từ nguồn/phép biến đổi, candidate span/T1 v2 có truy vết, coverage và manual review queue. `SoNha`/`TenDuong` luôn `khong_xac_dinh`; `QuanHuyen` luôn `cu`; phân biệt hệ nguồn với hệ span, abstain khi cùng tên hoặc offset/ánh xạ chưa chắc. Không dùng pilot gold v1/answer key cũ để sinh candidate, không nạp prediction cho test. Viết kiểm thử pipeline và chạy QA trong WSL. Chuẩn bị pilot 68 để người khác gán độc lập không prediction; batch 232 được import prediction để người gán kiểm từng task. Đừng công bố gold khi chưa có export và phán quyết của người gán. Báo file đã tạo, lệnh chạy, số lượng từng strata, tỷ lệ abstain, hạn chế và những thao tác người dùng còn phải làm.
