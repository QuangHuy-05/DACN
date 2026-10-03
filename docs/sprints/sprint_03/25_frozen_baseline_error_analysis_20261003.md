# Phân tích lỗi baseline frozen — 03/10/2026

Chỉ đọc prediction, error_analysis, metrics và manifest của bốn run hiện hành. Không gọi inference/scorer, không tune và không tạo F1 mới. Điểm dưới đây được sao từ metric frozen; báo cáo15 vẫn là nguồn thực nghiệm.

Evidence root: `data/interim/modeling/sprint03/task_01_06_20261003_v1/`. Taxonomy hiện hành nằm ở `baseline_analysis_v2/`; phiên bản trước lưu lịch sử. `taxonomy_summary.json` gắn SHA-256 của predictions/metrics/run/scoring manifest và provenance sidecar.

## 1. T0 exact span — 60 dev / 284 gold spans

| Model | F1 frozen | TP | FP | FN | Mẫu có sự kiện FP/FN |
|---|---:|---:|---:|---:|---:|
| HEUR-JW | 88.01% | 235 | 15 | 49 | 29 / 60 |
| CRF-INDEP | 89.82% | 256 | 30 | 28 | 16 / 60 |

Error_analysis frozen có 33 dòng HEUR và 54 dòng CRF; đây không phải số mẫu lỗi T0. File còn ghi ca T1 sai/không có output trong khi T0 có thể exact. Báo cáo này đếm riêng ID có sự kiện FP/FN:29 và16. CRF không hiện thực T1; không coi T1 trống là kết quả classifier.

| Taxonomy sự kiện T0 | HEUR-JW | CRF-INDEP |
|---|---:|---:|
| BOUNDARY_OR_SPLIT_MERGE:FN | 6 | 3 |
| BOUNDARY_OR_SPLIT_MERGE:FP | 6 | 3 |
| LABEL_AND_BOUNDARY_OVERLAP:FN | 1 | 2 |
| LABEL_AND_BOUNDARY_OVERLAP:FP | 6 | 4 |
| MISSED_GOLD:FN | 39 | 0 |
| WRONG_LABEL_EXACT_BOUNDARY:FN | 3 | 23 |
| WRONG_LABEL_EXACT_BOUNDARY:FP | 3 | 23 |

FN và FP là hai sự kiện theo scorer exact; cùng một span sai nhãn có thể tạo một FN và một FP. Bảng này mô tả discrepancy với gold đã khóa, không tự khẳng định gold đúng trong mọi ca hành chính mơ hồ.

### Nguồn dữ liệu và nhiễu

| Nguồn dev | Mẫu / gold spans | HEUR FP / FN | CRF FP / FN |
|---|---:|---:|---:|
| observed | 16 / 83 | 5 / 19 | 17 / 16 |
| derived | 12 / 48 | 3 / 3 | 0 / 0 |
| synthetic | 32 / 153 | 7 / 27 | 13 / 12 |

Sidecar chỉ dùng để phân tầng báo cáo; không dùng làm feature. Nhóm `synthetic_noise` gồm11mẫu/58span: HEUR FP4/FN19, CRF FP8/FN8. Nhóm `synthetic_missing` gồm8mẫu/35span: HEUR FP1/FN6, CRF FP3/FN3. Đây là lỗi trên dữ liệu nhiễu tổng hợp; chưa đủ bằng chứng quy mọi sự kiện thành lỗi OCR thực. Noise subtype chưa được frozen output ghi rõ.

Dev có0 MocDinhVi,0 ToaNha/CanHo; HuongDi/GhiChu/Khac chỉ1span mỗi nhãn. Không kết luận năng lực các nhãn này từ điểm tổng hợp.

### T1 / cấu trúc

Theo frozen prediction, cả hai baseline không sinh QuanHuyen trên14mẫu dev có gold hệ mới đủ điều kiện (đã mask ngoại lệ543). Đây là một đếm chẩn đoán nhỏ, không chứng minh lỗi quận bằng0 trên dữ liệu tổng quát. T1 HEUR dùng metric frozen; CRF T1=`NOT_IMPLEMENTED`.

Candidate trace HEUR được tổng hợp riêng trong `heuristic_candidate_decisions`: tách accept span, accept cấp nhưng chưa biết identity, reject và tie. Thiếu mã/quyền nguồn vẫn không được xuất mã chính thức.

### Ví dụ T0 có ID/offset

| Model | sample_id | Offset / nhãn gold hoặc prediction | Phân loại |
|---|---|---|---|
| HEUR-JW | `s3_0f163c6fd93d4fa3` | [32,39) QuanHuyen (FN) | MISSED_GOLD |
| HEUR-JW | `s3_1f97da2b16c1b045` | [5,22) TenDuong (FN) | BOUNDARY_OR_SPLIT_MERGE |
| HEUR-JW | `s3_1f97da2b16c1b045` | [5,12) Ngo/Hem (FP) | LABEL_AND_BOUNDARY_OVERLAP |
| HEUR-JW | `s3_d32ff02acd38ce03` | [35,43) TinhThanh (FN) | WRONG_LABEL_EXACT_BOUNDARY |
| CRF-INDEP | `s3_0f163c6fd93d4fa3` | [23,30) PhuongXa (FN) | WRONG_LABEL_EXACT_BOUNDARY |
| CRF-INDEP | `s3_1f97da2b16c1b045` | [5,22) TenDuong (FN) | BOUNDARY_OR_SPLIT_MERGE |
| CRF-INDEP | `s3_1f97da2b16c1b045` | [5,12) Ngo/Hem (FP) | LABEL_AND_BOUNDARY_OVERLAP |

Ví dụ literal/nguồn đầy đủ có trong `baseline_error_examples.json`; chỉ đưa ID/offset vào báo cáo để không in toàn địa chỉ. Các ca ranh giới hoặc cấp hành chính có thể cần rà chuyên môn trong một revision gold tương lai; lượt này không thay annotation.

## 2. Track5 trường — 4.800 hàng / 24.000 vị trí trường

| Model | micro F1 frozen | Mẫu có field error |
|---|---:|---:|
| HEUR-JW | 82.04% | 3086 / 4.800 |
| CRF-INDEP | 85.41% | 1581 / 4.800 |

Cả hai dùng cùng protocol text-only hiện hành, loại100hold trước adapter. Mẫu số theo dataset:01=980,02=980,03=1.480,04=780,06=580. Không so như cùng protocol với run4.900hàng hoặc oracle mode.

| Taxonomy field error | HEUR-JW | CRF-INDEP |
|---|---:|---:|
| EXTRA_FIELD | 33 | 61 |
| MISSING_FIELD | 3452 | 1052 |
| PARTIAL_FIELD_OR_BOUNDARY | 1222 | 1599 |
| POSSIBLE_CROSS_FIELD_CONFUSION | 33 | 56 |
| VALUE_MISMATCH_CAUSE_NOT_DETERMINED | 512 | 816 |

Một MISMATCH được frozen scorer tính FP+FN, nhưng bảng taxonomy ghi một sự kiện field mismatch. Không cộng sự kiện bảng này như mẫu số F1 T0. `VALUE_MISMATCH_CAUSE_NOT_DETERMINED` chưa đủ để gán nguyên nhân normalization hay extraction; cần raw parser/trace của đúng run. Không suy nguyên nhân OCR chỉ từ chuỗi.

Provenance observed/derived/synthetic từng record không có trong frozen5field output. Báo theo dataset và missing-field pattern khi có; không đọc CSV đầy đủ chứa các hàng hold để lấp metadata còn thiếu.

## 3. Backlog đề xuất — không thực thi tune/training trong lượt này

| Ưu tiên | Việc tiếp theo | Bằng chứng / cổng nghiệm thu |
|---|---|---|
| P0 | Giải quyết29case processor thay vị trí dấu trước training neural | Trace alignment; policy/version mới, giữ raw offsets và toàn bộ gold |
| P1 | Rà boundary tên đường–ngõ và tên không có prefix | T0 FN39 missed HEUR; bảng event có ID; fixture + kiểm raw trace, không sửa threshold ở lượt này |
| P1 | Rà nhầm nhãn/cấp hành chính của CRF | 23FN+23FP wrong label exact boundary; review mẫu/coverage, chỉ thay model trong run mới |
| P2 | Audit phép chiếu span→5trường và missing/partial field | Hai track tách riêng; HEUR thiếu3.452field, CRF thiếu1.052field; không làm mịn gold cho khớp |
| P2 | Bổ sung raw trace cho normalization/OCR ở thực nghiệm sau | Giữ causal status chưa xác định; provenance chỉ sidecar |
| Deferred | Tăng support nhãn hiếm bằng nguồn đã duyệt | Hiện mốc/hướng thật do chủ dự án hoãn; không sinh mẫu để giả support observed |

Mỗi đề xuất gắn run/input hashes tại `taxonomy_summary.json`; không thay metric, prediction, gazetteer hoặc corpus hiện hành.

## 4. Tái lập báo cáo taxonomy

```bash
cd /mnt/d/DACN
source data/interim/modeling/sprint03/task_01_06_20261003_v1/runtime_env.sh
"$TASK_PYTHON" -m scripts.36_review_sources_and_frozen_baselines baseline \
  --output-dir data/interim/modeling/sprint03/frozen_error_analysis_next_version
```

Dùng output mới. Script kiểm corpus hash/count, ID prediction, FP/FN trong frozen log và metric; không gọi scorer/model. [Test và hash gate](27_tasks_01_06_completion_20261003.md).
