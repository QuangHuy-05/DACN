# Chỉ mục artifact báo cáo và trạng thái kiểm toán (v3)

- **Phiên bản tài liệu:** v3 draft (sinh tự động)
- **Run nguồn:** `baseline_v1`
- **Manifest SHA-256:** `0f63399b6c5344d6015277c07236267c71127a73bd1588efd4b326f100c223e1`
- **Dòng benchmark:** 5500; **lượt dự đoán:** 13000.
- **Trạng thái:** draft có truy vết artifact; không thay thế báo cáo baseline v1 frozen.

## Artifact nguồn

| Thành phần | Đường dẫn | Vai trò |
| --- | --- | --- |
| Manifest | `data/processed/evaluation/runs/baseline_v1/run_manifest.json` | Hash benchmark, mapping, package và code của run. |
| Prediction | `data/processed/evaluation/runs/baseline_v1/baseline_predictions_unified.csv` | Output 9 cột đã chấm. |
| Raw log | `data/processed/evaluation/runs/baseline_v1/baseline_raw_responses.jsonl` | Response/trace theo `(ID, tool)`. |
| Bảng định lượng | `data/processed/evaluation/derived/baseline_v1/v3/comparative_analysis_tables` | Metric, scope, contract và case CSV. |

## Tài liệu sinh tự động

| Tệp | Nguồn máy đọc được | Trạng thái |
| --- | --- | --- |
| `baseline_ambiguity_evidence_v3.md` | prediction + raw + case table | Draft có truy vết |
| `data_preparation_summary_v3.md` | benchmark + OSM snapshot + manifest | Draft có truy vết |
| `chapter_01_research_motivation_v3.md` | bảng metric + nguồn [R1], [R2] | Draft có truy vết |
| `chapter_02_theoretical_foundation_v3.md` | protocol + nguồn [R3]–[R7] | Draft có truy vết |

Không tài liệu nào trong nhóm này thay thế baseline v1 frozen. Mọi thay đổi protocol, adapter, benchmark hoặc mapping phải tạo run ID mới và sinh lại toàn bộ bảng/tài liệu từ run đó.

## Tài liệu tham khảo

1. **[R1]** Quốc hội. *Nghị quyết số 202/2025/QH15 về sắp xếp đơn vị hành chính cấp tỉnh*. [Cổng Thông tin điện tử Chính phủ](https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-quyet-so-202-2025-qh15-ve-sap-xep-don-vi-hanh-chinh-cap-tinh-119250612174148722.htm).
2. **[R2]** Ủy ban Thường vụ Quốc hội. *Nghị quyết số 76/2025/UBTVQH15 về sắp xếp đơn vị hành chính năm 2025*. [Cổng Thông tin điện tử Chính phủ](https://xaydungchinhsach.chinhphu.vn/nghi-quyet-so-76-2025-ubtvqh15-sap-xep-don-vi-hanh-chinh-nam-2025-119250415130519882.htm).
3. **[R3]** Lafferty, J., McCallum, A., & Pereira, F. (2001). *Conditional Random Fields: Probabilistic Models for Segmenting and Labeling Sequence Data*. [PDF](https://www.cs.columbia.edu/~jebara/6772/papers/crf.pdf).
4. **[R4]** Nguyen, D. Q. & Nguyen, A. T. (2020). *PhoBERT: Pre-trained language models for Vietnamese*. Findings of EMNLP. [ACL Anthology](https://aclanthology.org/2020.findings-emnlp.92/).
5. **[R5]** OpenVenues. *libpostal: international street address NLP*. [Repository và tài liệu kỹ thuật](https://github.com/openvenues/libpostal).
6. **[R6]** OpenStreetMap Wiki. *Planet.osm/full and full-history data*. [Documentation](https://wiki.openstreetmap.org/wiki/Planet_History).
7. **[R7]** Dự án DACN. `data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv`, bảng ánh xạ hành chính được version/hash trong manifest của run.

