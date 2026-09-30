# Review S3-04/S3-03 và bàn giao các bước còn lại

**Ngày review:** 30/09/2026. **Trạng thái:** S3-04 mới có ứng viên và công cụ QA, chưa có corpus gold v1. S3-03 có gazetteer v2 phát hành một phần, chưa xác minh mã cũ hoặc quyền dùng của nguồn ánh xạ bên ngoài.

## 1. Kết quả review theo cổng kế hoạch

| Cổng | Kết luận | Bằng chứng / việc còn lại |
| --- | --- | --- |
| C2.1 Snapshot/test hold | Đạt về cấu trúc | 68 pilot, 100 test hold (20/tập 01, 02, 03, 04, 06), 20 VQA hold; preflight tính lại hash đầu vào và khóa text/group test. |
| C2.2 Split protocol | Có bản v1, cần chủ dự án xác nhận trước khi mở test | Seed 42, site group và ngưỡng gần trùng 0,85. Preflight tạo phân bổ 240 train / 60 dev / 100 test. |
| C2.3 Batch 02 | 232 ứng viên, chưa phải gold | 60 old, 60 new dẫn xuất, 40 noise, 40 missing, 32 hybrid. 172 mẫu dẫn xuất trỏ tới nguồn OSM cha; review đã tạo `source_parent_manifest.csv` với cùng group/split và hash văn bản nguồn. |
| C2.4 Batch 02 gold | Chưa đạt | Cần gán/kiểm 232 task, export JSON, QA và biên bản duyệt người. |
| C2.5 Test gold | Chưa đạt | Cần gán mù đúng 100 task trong project riêng; không đưa prediction vào test. |
| C2.6 Corpus v1 | Chưa đạt | 138 cặp gần giống qua split đang chờ quyết định. Chưa có `train.jsonl`, `dev.jsonl`, `test_benchmark_t0.jsonl` hoặc manifest gold. |
| G3.1–G3.5 Gazetteer v2 | Đạt ở mức partial | 14.149 entity, 10.597 cạnh xã, 187 alias, 5 chuyển đổi huyện đảo tra được. Mã xã cũ 0/10.035 verified; bảng ánh xạ mới thiếu URL nguồn gốc và giấy phép trong repo. |

## 2. Các lỗi/thiếu sót đã sửa trong review

1. `scripts/18_audit_corpus_split.py` trước đó chỉ in thông báo và không chạy audit từ CLI. Nay có `preflight` và `audit`; kiểm ID/group, text exact/normalized, gần trùng ở cả train–dev, train–test và dev–test. Đầu ra preflight ở `data/interim/annotation/sprint03/split_preflight_v1/` gồm phân bổ split, sổ 172 nguồn cha, báo cáo và 138 cặp cần rà. **138 là hàng đợi xem xét, chưa phải 138 lỗi rò rỉ.**
2. `scripts/17_convert_span_annotation_batch.py` nay kiểm `value.text` khớp `text[start:end]`, vùng `span_system` trùng đúng vùng nhãn, task chỉ chứa `sample_id`/`text`, hash guideline/XML đã khóa; với role test sẽ từ chối prediction. QA `READY_FOR_HUMAN_REVIEW` vẫn cần người duyệt nội dung.
3. `scripts/19_build_temporal_gazetteer_v2.py` nay tạo entity cho 5 huyện đảo, liên kết ID trong bảng chuyển đổi, trả kết quả qua lookup cấp huyện, sửa điều kiện lọc quận/huyện cho địa chỉ mới, loại alias tự trùng và thêm `lookup_examples.json`. Build kiểm hash v1, parent/edge và số mã xã mới. Sổ nguồn được đồng bộ; giá trị giấy phép chưa có chứng cứ được ghi `NOT_DOCUMENTED_IN_REPOSITORY`.
4. Số 705 huyện cũ trong báo cáo cũ là sai phép đếm: v1 có 691 huyện cũ có cạnh xã; v2 thêm 5 huyện đảo thành 696. Số alias v2 sau loại trùng là 187, không phải 302. Hash cũ trong hồ sơ phát hành đã được thay bằng manifest mới.
5. Đã tạo prediction **từ bề mặt `text`** cho 232 task train/dev bằng `scripts/20_prepare_batch02_predictions.py`: 970 span gợi ý, 75 task có cảnh báo cần xem kỹ. Prediction để `address_system` trống và hệ span không đủ bằng chứng là `khong_xac_dinh`; người gán quyết định T1/hệ sau khi đọc câu. Không có prediction cho test.

## 3. Việc chủ dự án/người gán cần làm, đúng thứ tự

### Bước A — Phân xử cặp gần giống trước khi mở test

Sao chép `data/interim/annotation/sprint03/split_preflight_v1/near_duplicate_review_queue.csv` thành `near_duplicate_decisions.csv` **trước khi sửa**; script sẽ tạo lại queue gốc. Mở bản sao trong Excel/LibreOffice. Mỗi dòng gồm hai `sample_id`, hai chuỗi, split và điểm giống. Điền `decision`, `reason`, `reviewer`:

- `distinct`: hai vị trí thật sự khác nhau; ghi bằng chứng cụ thể, ví dụ số nhà/ngõ/đường khác. Điểm giống cao do phần phường/tỉnh lặp lại chưa đủ để coi là cùng vị trí.
- `same_site`: cùng vị trí hoặc biến thể OCR/cũ–mới của cùng địa chỉ; **không** tự giữ ở hai split. Gửi danh sách ID này cho agent để gộp nhóm hoặc loại mẫu train/dev. Test ID frozen không đổi.
- `uncertain`: chưa đủ chứng cứ; agent phải giữ cổng split ở trạng thái chờ.

Lọc trước các dòng có `second_split=test` để bảo vệ test. Sau khi quyết định hết, chạy:

```bash
python -m scripts.18_audit_corpus_split preflight --decisions data/interim/annotation/sprint03/split_preflight_v1/near_duplicate_decisions.csv
```

Nếu có `same_site`/`uncertain`, trạng thái còn `BLOCKED_NEAR_DUP_DECISIONS`: gửi file cho agent sửa nhóm/split hoặc loại mẫu train/dev, rồi chạy lại với queue quyết định tương ứng. Chỉ `AUDIT_PASS_WITH_HUMAN_NEAR_DUP_REVIEW` mới đóng cổng gần trùng. Không tự sửa CSV import/test chỉ để giảm số cặp.

### Bước B — Gán batch 02 trên Label Studio với prediction gợi ý

1. Tạo project train/dev riêng, ví dụ `DACN_S3_T0_BATCH02_v1`; dùng nguyên `configs/label_studio_span11.xml`. Import **chỉ** `data/interim/annotation/sprint03/label_studio_batch02_import.json` (232 task). Nếu đã import đúng file, không import lại.
2. Trong WSL tại `/mnt/d/DACN`, kích hoạt môi trường Label Studio Python 3.11 đang dùng rồi tạo/kiểm candidate:

```bash
cd /mnt/d/DACN
source ~/.venv_labelstudio311/bin/activate
python -m scripts.20_prepare_batch02_predictions
```

3. Đặt token trong **terminal**, không chép token vào chat/file. Với PAT của Label Studio:

```bash
read -rsp 'Label Studio token: ' LABEL_STUDIO_API_TOKEN
export LABEL_STUDIO_API_TOKEN
echo
```

4. Đặt `BATCH02_PROJECT_ID` bằng số trên URL project (ví dụ URL `/projects/2/...` thì số là `2`), thay tên project trong lệnh nếu bạn dùng tên khác. Chạy dry run trước, thử một task rồi xem trong giao diện, sau đó nạp các task còn chưa gán:

```bash
BATCH02_PROJECT_ID=2
python -m scripts.15_import_pilot_predictions --project-id "$BATCH02_PROJECT_ID" --project-title DACN_S3_T0_BATCH02_v1 --expected-count 232 --candidates data/interim/annotation/sprint03/batch02_span11_candidate_predictions.json --model-version s3_span11_batch02_text_only_v1_not_gold --token-kind pat --sample-id s3_ad448edf801230dd
python -m scripts.15_import_pilot_predictions --project-id "$BATCH02_PROJECT_ID" --project-title DACN_S3_T0_BATCH02_v1 --expected-count 232 --candidates data/interim/annotation/sprint03/batch02_span11_candidate_predictions.json --model-version s3_span11_batch02_text_only_v1_not_gold --token-kind pat --sample-id s3_ad448edf801230dd --apply
python -m scripts.15_import_pilot_predictions --project-id "$BATCH02_PROJECT_ID" --project-title DACN_S3_T0_BATCH02_v1 --expected-count 232 --candidates data/interim/annotation/sprint03/batch02_span11_candidate_predictions.json --model-version s3_span11_batch02_text_only_v1_not_gold --token-kind pat --apply
```

5. Mở **từng task**, kiểm mọi span, sửa phân đoạn ngõ/hẻm và tên đường, nhãn phường/quận/tỉnh, hệ từng span, T1 toàn câu, OCR và ca lai. Prediction là gợi ý có thể sai, đặc biệt 75 task trong `batch02_prediction_generation_report.json`; không Submit hàng loạt chưa đọc. Nếu muốn đo Cohen's Kappa liên người, người thứ hai phải gán độc lập trên một tập chưa xem prediction.

### Bước C — Gán test mù trong project khác

Chỉ khi protocol và bước A được chốt, tạo project test riêng, dùng cùng XML, import `data/interim/annotation/sprint03/label_studio_test_benchmark_t0_import.json` đúng 100 task. **Không chạy script nạp prediction cho project test.** Gán mọi span và hệ theo guideline `s3-span-v1.1`, không mở cột benchmark `GT_*`/metadata nguồn khi gán. ID khó vẫn giữ; ghi cờ và note để duyệt.

### Bước D — Export, QA và duyệt nội dung

Xuất raw JSON của hai project, giữ từng vòng export riêng, ví dụ `exports/batch02/batch02_round1.json` và `exports/test/test_round1.json`. Chạy:

```bash
python -m scripts.17_convert_span_annotation_batch --export data/interim/annotation/sprint03/exports/batch02/batch02_round1.json --queue data/interim/annotation/sprint03/annotation_queue_batch02_train_dev.csv --role train_dev_batch02 --output-dir data/interim/annotation/sprint03/batch02_conversion/round1
python -m scripts.17_convert_span_annotation_batch --export data/interim/annotation/sprint03/exports/test/test_round1.json --queue data/interim/annotation/sprint03/annotation_queue_batch01.csv --role frozen_benchmark_test_hold --output-dir data/interim/annotation/sprint03/test_conversion/round1
```

Mỗi báo cáo phải có `status=READY_FOR_HUMAN_REVIEW`, đúng 232/232 hoặc 100/100, `issues=[]`. Mở `review_items.json` và các task có cờ/note; ghi quyết định, lý do, người/ngày duyệt. Nếu sửa trên Label Studio, export vòng mới và chạy QA lại. Người duyệt phải xác nhận đã xem **mọi task**, không chỉ ca bị cờ. `READY_FOR_HUMAN_REVIEW` không tự thành gold.

### Bước E — Giao cho agent đóng gói

Gửi đường dẫn hai raw export cuối, hai thư mục QA, CSV quyết định cặp gần giống, sổ adjudication, tên người/ngày duyệt và xác nhận nội dung đủ 232+100. Agent kiểm hash, ghép 68 pilot gold theo `train_dev_split_assignments.csv`, audit cuối và tạo `corpus_v1/` cùng manifest; chỉ công bố khi tất cả cổng đạt. `scripts/18_audit_corpus_split.py audit` **chỉ kiểm các file JSONL đã có**, không tự cấp gold hay tự viết corpus manifest.

## 4. Việc riêng cho gazetteer

Gazetteer v2 dùng được ở mức **partial** cho tra tên, alias, thời gian và cạnh đã có nguồn bảng ánh xạ. Nếu cần công bố mã cũ là chính thức, chủ dự án cung cấp/chốt danh mục mã cũ của cơ quan nhà nước trước 01/07/2025 có khóa tỉnh–huyện–xã, ngày hiệu lực, URL và quyền dùng; đồng thời chốt provenance/giấy phép của CSV ánh xạ mới. Agent sẽ đối chiếu từng khóa rồi phát hành phiên bản tiếp theo. Không cần Label Studio cho bước gazetteer.

## 5. Giới hạn môi trường và bàn giao file

Trong phiên review, WSL và `.venv` Windows bị môi trường agent từ chối; kiểm chứng chạy bằng Python bundle nội bộ. Các file `data/interim/` bị Git ignore nên **không tự xuất hiện trên GitHub**. Partner cần làm trên cùng workspace hoặc nhận bản sao an toàn của queue/import/prediction/export/split preflight. Không gửi PAT Label Studio cho partner qua Git hoặc chat.
