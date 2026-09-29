# Sprint 3: vận hành S3-01, S3-02 và S3-03

**Ngày cập nhật:** 29/09/2026. **Trạng thái:** S3-01 đã phát hành [pilot gold v1](../../../data/processed/annotation/sprint03/pilot_gold_v1.jsonl): 68/68 task được người gán xác nhận rà soát, task 1–4 đã sửa trong Label Studio, bảy ca có cờ đã ghi sổ, guideline `s3-span-v1.1` đã khóa và export sau sửa qua QA 0 lỗi. Xem [biên bản duyệt gold](pilot_gold_approval.md). Giữ riêng 100 mẫu benchmark test; pilot gold chưa đủ để báo F1 T0 trên test.

## Thứ tự thực hiện và cổng phụ thuộc

1. **S3-01: mở pilot 68 mẫu.** Gán, xuất từng vòng, rà soát lỗi offset/nhãn/hệ, quyết định ca khó và khóa guideline. Mục tiêu là tạo quy tắc gán có thể áp dụng nhất quán trước khi mở test.
2. **S3-02: kiểm nguồn song song với pilot.** Duyệt quyền, PII và nhóm nguồn VQA; thu Data 05 có bằng chứng thật. Mục tiêu là có nhãn `MocDinhVi`/`HuongDi` trên dữ liệu quan sát, không dùng cụm tổng hợp để thay thế.
3. **S3-03: dùng gói gazetteer có trạng thái xác minh.** Tra tên + cấp + ngày + ngữ cảnh; xác minh mã cũ bằng nguồn chính thức trước khi gọi mã đó là chuẩn. Mục tiêu là cung cấp ứng viên cho heuristic và ràng buộc giải mã mà không tự chọn đích ở quan hệ nhiều nhánh.

## S3-01: dựng project và nghiệm thu pilot

### Đã có trong repository

- Cấu hình giao diện: [`configs/label_studio_span11.xml`](../../../configs/label_studio_span11.xml), phiên bản cấu hình ban đầu `s3-span-v1.0`. Người gán thấy `$text`, `sample_id` và lựa chọn 11 nhãn, hệ từng span, hệ toàn câu cùng cờ/note rà soát. Trường `GT_*`, `HeQuyChieu`, `KieuThieu`, `Span_He_Detail` không nằm trong JSON import.
- File import duy nhất: [`data/interim/annotation/sprint03/label_studio_pilot_import.json`](../../../data/interim/annotation/sprint03/label_studio_pilot_import.json), **68 task**. File này ở `data/interim/`, bị Git bỏ qua và không được công bố khi chưa kiểm nguồn.
- Bộ chuyển/QA: [`scripts/11_convert_label_studio_pilot.py`](../../../scripts/11_convert_label_studio_pilot.py). Nó từ chối sample lạ, text khác queue, nhãn ngoài 11 lớp, offset sai, overlap, span thiếu hệ, `QuanHuyen` không mang `cu`. Đầu ra canonical **ứng viên**, cần người duyệt trước khi gọi gold.
- Sổ quyết định mẫu: [`pilot_decision_log.csv`](pilot_decision_log.csv). Phiên bản hướng dẫn: [`span_11_annotation_guideline.md`](span_11_annotation_guideline.md).

### Quy trình Label Studio để tái lập pilot

Project Label Studio hiện tại đã được tạo, import và nghiệm thu đủ 68 task. Các bước dưới đây ghi lại quy trình để partner tái lập ở một project riêng; **không import lại** vào project đã duyệt. Bản export, QA và gold được chốt nằm trong [biên bản](pilot_gold_approval.md).

1. Tạo project tên `DACN_S3_T0_PILOT_v1`. Ở **Labeling Setup → Code**, dán toàn bộ XML trong file cấu hình rồi lưu. Label Studio hỗ trợ cấu hình named entity và lựa chọn trên từng vùng; xem [project setup](https://labelstud.io/guide/setup_project) và [NER template](https://labelstud.io/templates/named_entity).
2. Trong **Import**, chỉ chọn `data/interim/annotation/sprint03/label_studio_pilot_import.json`. Xác nhận đúng **68 task**; xem [hướng dẫn import task](https://labelstud.io/guide/tasks). Mở một task, kiểm tra giao diện chỉ có chuỗi gốc và `sample_id`, không có đáp án benchmark hay nhãn gợi ý.
3. Với mỗi task, gán mọi thực thể xuất hiện; giữ offset theo chuỗi gốc. Chọn hệ cho **từng span**: `cu`, `moi`, hoặc `khong_xac_dinh`. Chỉ chọn hệ toàn câu khi văn bản đủ bằng chứng. Với phần OCR không đọc được, để `O` và đánh `unreadable_ocr`. Với ca `Khac`, mốc/hướng, `nay là`, ghi chú vào cờ/note và sổ quyết định.
4. Sau mỗi vòng, xuất **raw JSON** của project, giữ thành `pilot_round01.json`, `pilot_round02.json`... trong `data/interim/annotation/sprint03/exports/`. Không chỉ tải CSV rút gọn vì cần region ID, offset, người gán và lead time; xem [hướng dẫn export](https://labelstud.io/guide/export). Export JSON qua giao diện Community Edition có thể chỉ gồm task đã được gán; vì vậy báo cáo các vòng giữa chừng có `missing_from_export` là bình thường. Bản export cuối phải có đủ 68 task. Nếu cần xem cả task chưa gán trong export, dùng API với `download_all_tasks=true` theo tài liệu chính thức.
5. Nếu có hai người gán độc lập, yêu cầu họ gán cùng một tập task trước khi xem bài của nhau. Chọn annotation đã duyệt qua file JSON `{"sample_id": annotation_id}` và truyền `--adjudication-map`. Nếu chỉ một người, báo cáo đồng thuận liên người là `NOT_MEASURED`; lần gán lặp của chính người đó không tính là inter-annotator Kappa.

Chạy chuyển đổi sau khi xuất JSON (trong WSL chính của dự án):

```bash
cd /mnt/d/DACN
source ~/.venv_dacn/bin/activate
python -m scripts.11_convert_label_studio_pilot \
  --export data/interim/annotation/sprint03/exports/pilot_round01.json \
  --output-dir data/interim/annotation/sprint03/pilot_conversion/round01
```

Khi có hai annotation trên một task, thêm `--adjudication-map data/interim/annotation/sprint03/exports/adjudication_map.json`. Đọc `pilot_qa_report.json`: phải thấy `expected_pilot_tasks=68`, 68 trạng thái trong `task_statuses`, không có `issues`, và `status=READY_FOR_HUMAN_REVIEW`. `pilot_review_items.json` là danh sách ca cần quyết định. Chỉ khi đó mới có `pilot_canonical_candidate.jsonl`, với mỗi dòng đúng dạng `sample_id`, `text`, `spans[{start,end,label,system}]`, `address_system`, `source_group`.

**Nghiệm thu bằng người:** mở lại từng ca được gắn cờ, sửa trên Label Studio nếu cần, điền `pilot_decision_log.csv`, xuất vòng cuối, rồi duyệt canonical candidate thành gold. Ghi hash XML, guideline và export từ QA report; tăng version guideline khi có thay đổi và ghi ngày khóa. **Không mở 100 test trước khi khóa.** Nếu Label Studio không ghi lead time đáng tin, đo thời gian bằng nhật ký bắt đầu/kết thúc từng phiên và nêu phương pháp; không suy từ thời gian mở trình duyệt.

## S3-02: dữ liệu thật, VQA và Data 05

### VQA hiện có và cổng kiểm duyệt

`scripts/12_prepare_vqa_review.py` đã lập `data/interim/annotation/sprint03/vqa_review_queue.csv` cho **146 chuỗi**. [Báo cáo kiểm kê](vqa_review_inventory.json) ghi 10 chuỗi có cue mốc, 0 cue hướng theo regex; cue **không phải** nhãn gold. Tất cả hàng mang `PENDING_MANUAL_REVIEW` và quyền `UNVERIFIED`.

1. Mở queue trong môi trường riêng tư. Với từng dòng, kiểm bằng mắt tên người, số điện thoại, địa chỉ cá nhân, bối cảnh hóa đơn, và quyền dùng. Ghi reviewer, thời điểm, kết luận và lý do. Không đưa VQA vào train/test công bố khi cổng này chưa qua.
2. CSV trung gian chỉ có `ChuoiDiaChi`, không có ID hóa đơn. Muốn tìm ID tài liệu, chạy ở WSL có `pyarrow` đã cài theo môi trường dự án, đọc schema raw Parquet **chỉ để kiểm kê**. Ví dụ:

```bash
cd /mnt/d/DACN
source ~/.venv_dacn/bin/activate
python - <<'PY'
from pathlib import Path
import pyarrow.parquet as pq
for path in Path('data/raw/viet_receipt_vqa').rglob('*.parquet'):
    print(path, pq.read_schema(path))
PY
```

Sau khi biết cột ID thực, bổ sung bước liên kết ở pipeline VQA với bằng chứng `raw_file + row/group ID + text`, rồi kiểm bằng mắt các khớp mơ hồ. **Không ghép bằng chuỗi địa chỉ đơn thuần** vì một chuỗi có thể xuất hiện ở nhiều hóa đơn. Nếu raw không có ID tin cậy, giữ VQA là external hold và ghi hạn chế.

### Thu Data 05 thật

Điền [`data05_source_register.csv`](data05_source_register.csv) cho từng nguồn: URL, tác giả/nhà xuất bản, ngày truy cập, giấy phép, phạm vi tái sử dụng, ID tài liệu/đối tượng gốc. Điền [`data05_candidate_register.csv`](data05_candidate_register.csv) cho từng câu **nguyên văn**, hash, `source_group_id`, dấu hiệu mốc/hướng, quyết định PII/quyền, nhận hay loại và lý do. Chỉ nguồn công khai có quyền sử dụng rõ mới chuyển sang hàng chờ gán nhãn. Với OpenStreetMap phải ghi attribution và kiểm điều kiện [ODbL](https://www.openstreetmap.org/copyright); với website khác kiểm điều khoản riêng. Không lấy địa chỉ khách hàng cá nhân.

Thu riêng các câu thực có mốc (`gần`, `đối diện`, tên chợ/cầu...) và hướng (`hướng`, `rẽ`, `đi về`...), nhưng chỉ chấp nhận khi chính **câu nguồn** chứa quan hệ đó. Nếu tạo biến thể tổng hợp từ câu thật, đánh `synthetic`, giữ ID câu cha, không tính là `observed`. Ưu tiên nhiều nguồn/tài liệu và gom biến thể cùng tài liệu vào một `source_group_id`; khóa nhóm trước khi chia train/dev/test. Báo **số ứng viên, số được duyệt, số loại và lý do**. Mục tiêu khoảng 500 địa chỉ mốc là đích thu thập, không phải quota để tự sinh dữ liệu.

**Tình trạng hiện tại:** 0 câu Data 05 thật đã qua kiểm nguồn; `MocDinhVi` và `HuongDi` trong 20 ví dụ pilot hiếm là seed tổng hợp để thử guideline. Chưa thể công bố support hoặc F1 trên Data 05 quan sát.

## S3-03: gazetteer đa phiên bản một phần

Chạy lại bản build bằng thư viện chuẩn:

```bash
cd /mnt/d/DACN
source ~/.venv_dacn/bin/activate
python -m scripts.13_build_temporal_gazetteer build
python -m scripts.13_build_temporal_gazetteer lookup \
  --name 'Phường Bến Nghé' --level ward --as-of 2025-06-30 \
  --system cu --province 'Thành phố Hồ Chí Minh'
```

Gói ở [`data/processed/gazetteer/s3_v1/`](../../../data/processed/gazetteer/s3_v1/) gồm `entities.csv`, `edges.csv`, `aliases.csv`, `manifest.json`. `entity_id` là ID nội bộ ổn định, **không phải mã hành chính chính thức**. Bản mới có `official_code` cấp xã từ bảng ánh xạ; mã cũ từ `third_party/vietnamadminunits` chỉ ghi vào `candidate_code`, trạng thái `candidate_third_party_unverified`, kèm `candidate_code_source_id` và `candidate_code_source_hash` riêng. Bản cũ kết thúc 30/06/2025, bản mới bắt đầu 01/07/2025; `valid_from` cũ để trống vì chưa có mốc gốc chắc chắn. Không có tọa độ/hình học.

Manifest hiện ghi **10.602 dòng nguồn**, **10.597 cạnh đủ khóa cũ**, **5 dòng chuyển từ cấp huyện sang đặc khu không có phường/xã cũ**, **10.035 xã/phường cũ**, **3.321 xã/phường mới**, **187 alias**, cùng hash từng nguồn và đầu ra. Năm dòng thiếu phường/xã cũ chỉ tạo entity mới, không tạo cạnh cũ giả. Lookup trả danh sách ứng viên và bằng chứng; khi nhiều tên hoặc nhiều đích, phía HEUR-JW/decoder phải giữ nhiều ứng viên cho đến khi có ngữ cảnh chứng minh đích duy nhất. Không xem `candidate_code` là mã chuẩn.

Để hoàn thiện cổng mã cũ, đối chiếu `candidate_code` theo khóa đầy đủ tỉnh–huyện–xã với danh mục mã chính thức có thời gian hiệu lực và giấy phép. Lưu source ID, hash, kết quả khớp/không khớp; chỉ nâng `code_status` sang `verified_source` khi đối chiếu được. Nguồn chính phủ công bố danh mục mới [34 tỉnh và 3.321 đơn vị cấp xã](https://xaydungchinhsach.chinhphu.vn/bang-danh-muc-va-ma-so-cua-34-tinh-thanh-moi-cac-don-vi-hanh-chinh-cap-xa-moi-11925070418263625.htm); cần kiểm văn bản nguồn cụ thể cho **mã cũ** trước khi coi chúng là chính thức.

## Điều kiện để gọi ba gói việc hoàn thành

| Gói | Đã làm | Còn thiếu để nghiệm thu |
| --- | --- | --- |
| S3-01 | Config, project, 68/68 task đã được người gán rà soát, bảy quyết định đã ghi sổ, guideline đã khóa; export sau sửa qua QA và pilot gold v1 có manifest/hash | Thời gian gán thực đo chưa có nguồn tin cậy; đồng thuận liên người `NOT_MEASURED` vì chỉ một người gán |
| S3-02 | Queue VQA 146 chuỗi, sổ nguồn/candidate, quy tắc hold | Kiểm quyền/PII và ID hóa đơn; câu Data 05 thật được duyệt; support mỗi nhãn/split |
| S3-03 | Gói version/hash, entity/alias/cạnh và lookup theo ngày | Xác minh mã đơn vị cũ từ nguồn chính thức; quyết định xử lý 5 chuyển đổi cấp huyện; coverage sâu hơn |
