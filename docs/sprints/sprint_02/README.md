# Hồ sơ Sprint 2

Thư mục này tập hợp tài liệu rà soát, dữ liệu, baseline, chương nghiên cứu và slide đã được tạo hoặc dùng trong Sprint 2. Nội dung tài liệu lịch sử được giữ nguyên theo quy ước phiên bản; một số đường dẫn bên trong chúng phản ánh cấu trúc thư mục tại thời điểm lập. README này là chỉ mục cho vị trí hiện tại.

## Tài liệu

| Nhóm | Tệp |
| --- | --- |
| Kế hoạch và rà soát | [baseline_review_plan.md](baseline_review_plan.md), [final_implementation_review_v2.md](final_implementation_review_v2.md) |
| Dữ liệu và phạm vi benchmark | [data_preparation_summary_v2.md](data_preparation_summary_v2.md) |
| Đánh giá baseline | [baseline_evaluation_report.md](baseline_evaluation_report.md), [baseline_parallel_comparative_analysis.md](baseline_parallel_comparative_analysis.md), [baseline_ambiguity_evidence_v2.md](baseline_ambiguity_evidence_v2.md), [baseline_dashboard.html](baseline_dashboard.html), [report_materials_index_v2.md](report_materials_index_v2.md) |
| Chương nghiên cứu | [chapter_01_research_motivation_v2.md](chapter_01_research_motivation_v2.md), [chapter_02_theoretical_foundation_v2.md](chapter_02_theoretical_foundation_v2.md) |
| Slide | [slides_hcmut.tex](slides_hcmut.tex), [slides_hcmut.pdf](slides_hcmut.pdf) |

## Output theo run

Output sinh theo run vẫn nằm trong thư mục versioned để khớp quy ước pipeline:

- [Báo cáo baseline_v2](../../runs/baseline_v2/baseline_evaluation_report.md)
- [Dashboard baseline_v2](../../runs/baseline_v2/baseline_dashboard.html)
- [Lineage dashboard baseline_v2](../../runs/baseline_v2/baseline_dashboard.lineage.json)

`data_quality.md`, `VERSIONING.md` và báo cáo coverage là tài liệu dùng chung toàn dự án, nên vẫn nằm trực tiếp trong `docs/`.

## Lưu ý sử dụng

`final_implementation_review_v2.md` ghi nhận các vấn đề truy vết trong một số tài liệu nghiên cứu v2. Vì vậy, hồ sơ Sprint 2 này là bản lưu lịch sử; khi trích số liệu cho Sprint 3, hãy đối chiếu với manifest/run tương ứng và [data_quality.md](../../data_quality.md), không xem mọi nhận định trong tài liệu v2 là kết quả đã được xác nhận.

## Biên dịch slide

Từ thư mục `docs/`, chạy:

```bash
xelatex -output-directory=sprints/sprint_02 -interaction=nonstopmode sprints/sprint_02/slides_hcmut.tex
```

Slide dùng chung font và hình ảnh tại `docs/fonts/` và `docs/assets/`.
