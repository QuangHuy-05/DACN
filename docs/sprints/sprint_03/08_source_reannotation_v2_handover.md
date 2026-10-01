# Bàn giao gói gán lại T0 v2

Ngày tạo: 30/09/2026; cập nhật 01/10/2026. Trạng thái: `candidate_not_gold`. **Hướng dẫn thao tác hiện hành:** [mở Label Studio, cấu hình, giải thích nhãn và export 68/232/100](09_label_studio_400_step_by_step.md). Chủ dự án đã chọn prediction cho cả 68 và 232; vòng pilot là rà soát có hỗ trợ, agreement độc lập `NOT_MEASURED`.

Gói dùng để gán hiện tại nằm tại `data/interim/annotation/sprint03/reannotation_v2_release1/`, với hai tệp `pilot68_with_predictions.json` và `batch232_with_predictions.json` để import trực tiếp qua UI một lần vào project mới. Không nạp thêm candidate qua API nếu đã dùng hai tệp này. Gói test cho partner được theo dõi trên Git tại [annotation_handoff/test100_v1](annotation_handoff/test100_v1/README.md), nhánh `print3_label100test`.

## Tái tạo và kiểm tra

Trong WSL, tại `/mnt/d/DACN` với `~/.venv_dacn` đã kích hoạt:

```bash
python -m scripts.21_prepare_source_reannotation --output-dir data/interim/annotation/sprint03/reannotation_v2_new_review
python -m unittest discover -s tests -p test_source_reannotation.py -v
python -m unittest discover -s tests -v
```

Script ghi vào `data/interim/annotation/sprint03/reannotation_v2/` và từ chối thư mục đích đã có tệp. Dùng `--output-dir` trỏ đến thư mục phiên bản mới khi cần tái tạo. Không chạy lại script 10/16 để thay queue/import đã khóa.

| Tệp v2 | Mục đích |
| --- | --- |
| `pilot68_import.json`, `batch232_import.json` | Task chỉ có `data.sample_id`, `data.text`; giữ nguyên từng cặp ID/text. |
| `pilot68_candidates.json`, `batch232_candidates.json` | Prediction theo schema script 15, trạng thái `candidate_not_gold`. |
| `trace.jsonl` | Nhóm/split, hàng nguồn, khóa hành chính, ánh xạ, phép biến đổi, offset và hệ nguồn/hệ span. |
| `manual_review_queue.csv` | Các span/câu cần người gán xem, đặc biệt tên hành chính không phân biệt được thời kỳ. UTF-8-sig. |
| `coverage_report.json`, `generation_manifest.json` | Coverage theo strata, lý do rà soát và SHA-256 đầu vào/đầu ra. |

Nguồn của 24 pilot cũ và 60 batch cũ là hàng OSM quan sát; 24 pilot mới gồm hàng mới quan sát hoặc địa chỉ dẫn xuất từ ánh xạ một đích; 60 batch mới và 32 hybrid dẫn xuất từ cạnh một đích; 40 noise, 40 missing và 20 seed hiếm là mẫu tổng hợp có kiểm soát. `trace.jsonl` ghi loại bằng chứng theo từng task. Script suy lại phép viết tắt/đổi hoa thường của 40 noise từ bản nguồn và text đã khóa, vì generator cũ không lưu từng quyết định RNG; các phép được nhận chỉ khi dựng ra đúng text. Đây không phải bằng chứng rằng đã khôi phục chuỗi số ngẫu nhiên ban đầu.

Gói có **68 pilot** (24 cũ, 24 mới, 20 seed) và **232 batch 02** (60 cũ, 60 mới, 40 noise, 40 missing, 32 hybrid). Bản QA ngày 01/10 có 245 span pilot và 1.059 span batch ứng viên. Một thành phần số nhà của `s3_c1f7b490f4d7c9bc` được bỏ khỏi prediction để người gán quyết định ranh giới `8 (660/8)`; các span khác còn nguyên. Có 473 mục rà soát: 472 mục thời kỳ/T1 và một mục ranh giới. `coverage_report.json` của thư mục mới ghi chi tiết; bản cũ được giữ để truy vết. 138 quyết định đã được Huy điền và áp dụng: audit ngày 01/10 đạt `AUDIT_PASS_WITH_HUMAN_NEAR_DUP_REVIEW`, xem [bằng chứng](test100_split_gate_20261001.json).

## Hai project Label Studio

1. Tạo project **mới** cho pilot, ví dụ `DACN_S3_T0_PILOT_ASSISTED_v2`; dùng nguyên `configs/label_studio_span11.xml`, import `pilot68_with_predictions.json` trong thư mục QA ngày 01/10. Người gán kiểm, sửa và Submit mọi task. Không dùng vòng có prediction này để báo agreement độc lập.
2. Tạo project **mới** cho batch, ví dụ `DACN_S3_T0_BATCH02_ASSISTED_v2`; dùng cùng XML, import `batch232_with_predictions.json` trong thư mục QA ngày 01/10. Có thể gán hai project song song. Đọc ID thật từ URL project `/projects/<ID>/...` nếu cần API.
3. **API là phương án bổ sung nếu project đã import bản text-only.** Nếu đã import `*_with_predictions.json`, bỏ qua phần API dưới đây. Với project text-only, đặt `LABEL_STUDIO_API_TOKEN` bằng biến môi trường; dùng ID/title thật và dry-run trước. Script 15 đối chiếu cấu hình XML, task, ID/text và trạng thái annotation. Chọn `--token-kind pat` hoặc `legacy` tương ứng loại token.

```bash
python -m scripts.15_import_pilot_predictions \
  --project-id "$BATCH02_PROJECT_ID" \
  --project-title DACN_S3_T0_BATCH02_ASSISTED_v2 \
  --expected-count 232 \
  --candidates data/interim/annotation/sprint03/reannotation_v2_release1/batch232_candidates.json \
  --model-version s3_span11_source_trace_v2_not_gold \
  --token-kind pat
```

Sau khi dry-run báo đúng project, 232 task và ID/text, có thể thử `--sample-id <ID đã chọn> --apply`, kiểm tra giao diện một task, rồi chạy lại lệnh trên với `--apply` cho các task còn lại. Mỗi task batch vẫn phải được người gán xem, sửa và Submit. Không dùng script prediction với project test 100.

## Export và cổng duyệt người

Xuất **raw JSON** của từng project vào hai đường dẫn riêng có số vòng, ví dụ `data/interim/annotation/sprint03/exports/reannotation_v2/pilot_round1.json` và `batch_round1.json`. Sau đó chạy:

```bash
python -m scripts.11_convert_label_studio_pilot \
  --export data/interim/annotation/sprint03/exports/reannotation_v2/pilot_round1.json \
  --queue data/interim/annotation/sprint03/annotation_queue_batch01.csv \
  --output-dir data/interim/annotation/sprint03/reannotation_v2/pilot_conversion_round1

python -m scripts.17_convert_span_annotation_batch \
  --export data/interim/annotation/sprint03/exports/reannotation_v2/batch_round1.json \
  --queue data/interim/annotation/sprint03/annotation_queue_batch02_train_dev.csv \
  --role train_dev_batch02 \
  --output-dir data/interim/annotation/sprint03/reannotation_v2/batch_conversion_round1
```

Kiểm tra đủ 68/68 và 232/232, `issues=[]`, rồi đọc toàn bộ `review_items` và queue v2. `READY_FOR_HUMAN_REVIEW` chỉ xác nhận QA cấu trúc. Người phụ trách phải xác nhận đã xem tất cả task, quyết định các ca khó và lưu biên bản trước khi phát hành gold. Có thể đối chiếu 68 bản rà có hỗ trợ với pilot gold v1 để lập danh sách thay đổi; agreement độc lập `NOT_MEASURED`. Giữ pilot gold v1 nguyên trạng. Corpus T0 chưa hoàn tất cho đến khi test 100 được gán mù/duyệt và audit split, gồm 138 cặp gần giống, đạt yêu cầu.

Các artifact trong `data/interim/` có thể bị Git ignore; khi bàn giao sang checkout khác, chuyển tệp cùng SHA-256 trong `generation_manifest.json` qua kênh tệp được phép.
