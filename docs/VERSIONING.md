# Quy ước quản lý phiên bản tài liệu và kết quả baseline

## Phiên bản đang dùng

- Báo cáo chính thức hiện hành: `baseline_parallel_comparative_analysis.md` — **v1, frozen**.
- Artifact v1 đã được sao lưu có hash tại `data/processed/evaluation/runs/baseline_v1/`; `freeze_record.json` liệt kê SHA-256 của prediction, raw log, manifest và bảng v1.
- Tài liệu v2 được giữ để truy cứu lịch sử nhưng không được phát hành vì review đã phát hiện case không truy vết được và mô tả Data 06 sai. Bản sửa sinh tự động dùng hậu tố v3 trong `docs/runs/<run_id>/`.

## Quy tắc khi có thay đổi

1. Không ghi đè báo cáo hoặc core output đã đóng băng.
2. Mọi run mới dùng ID duy nhất, chỉ gồm chữ thường, số và `_`, ví dụ `baseline_v2` hoặc `baseline_v2_pilot`.
3. Output của một run luôn nằm tại `data/processed/evaluation/runs/<run_id>/`: `run_manifest.json`, prediction CSV, raw JSONL và `comparative_analysis_tables/`.
4. Báo cáo/dashboard của run nằm tại `docs/runs/<run_id>/`. Script từ chối ghi đè run, bảng, tài liệu hoặc dashboard trừ khi có cờ explicit tương ứng.
5. Manifest run đóng băng benchmark, mapping, package và hash code trước khi gọi tool; output hash được ghi sau khi run hoàn tất. Báo cáo/dashboard giữ lineage riêng trỏ đến SHA-256 của manifest, không sửa manifest sau khi freeze.
6. Khi thay đổi benchmark, adapter, scorer hoặc protocol, tạo run ID mới; không dùng lại output cũ làm kết quả của run mới. Báo cáo so sánh phải ghi rõ run ID nguồn, manifest hash, số dòng benchmark và lượt dự đoán.
7. Khi chỉnh tài liệu, tạo phiên bản kế tiếp (`v3`, `v4`, …) thay vì ghi đè. Tài liệu do script sinh có trạng thái `draft` cho đến khi review pass.

## Dọn output cũ ngày 20/09/2026

Đã loại bỏ các artifact của baseline cũ không còn được code hiện hành tham chiếu:

- `docs/baseline_error_analysis.md`
- `data/processed/evaluation/baseline_cases.csv`
- `data/processed/evaluation/baseline_error_table.csv`
- `data/processed/evaluation/baseline_raw_outputs.jsonl`

Không xóa dữ liệu nguồn, dữ liệu trung gian được pipeline dùng làm fallback, benchmark hiện hành, `third_party/`, archive `baseline_v1` hoặc manifest của bất kỳ run nào.
