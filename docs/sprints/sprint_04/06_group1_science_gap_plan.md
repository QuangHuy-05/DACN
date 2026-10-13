# Kế hoạch chi tiết Nhóm 1 — Lấp khoảng trống khoa học

**Ngày lập:** 13/10/2026. **Mốc đóng mục tiêu:** 18/10/2026 (hạn cứng 20/10).
**Nguồn yêu cầu:** mục 2, Nhóm 1 của [05_project_review_and_remaining_tasks.md](05_project_review_and_remaining_tasks.md).
**Prompt cho agent:** [07_agent_prompts_group1.md](07_agent_prompts_group1.md).

Mọi con số ở mục 1 được đo trực tiếp trên repo ngày 13/10 (lệnh đọc CSV/JSONL, không chạy mô hình). Các điểm là suy luận hoặc đề xuất được ghi rõ.

## 1. Hiện trạng đã kiểm, ảnh hưởng trực tiếp tới thiết kế

| # | Quan sát (đo trên repo) | Hệ quả cho kế hoạch |
|---|---|---|
| F1 | Data 07 có 600 cặp nhưng **chỉ có `M` (356) và `B` (244)**; không có `A`, không có `C`. Chỉ 23 mã phường mới, 69 đơn vị cũ; 441/600 ở Hà Nội, 151 Bắc Ninh, 8 TP.HCM. | Bảng "theo A/B/C/M" trên Data 07 chỉ điền được B và M; A và C phải ghi `NOT_EVALUABLE_NO_SUPPORT`. Bù bằng phân tích toàn bộ đồ thị cạnh (F2). CI phải bootstrap theo cụm đơn vị, không coi 600 cặp là độc lập. |
| F2 | Gazetteer `s3_v4_nso_dual_snapshot_release2/edges.csv`: 10.597 cạnh = B 9.432, M 1.030, C 132, **A chỉ 3**. | Tình huống A thuần (1-N) gần như không tồn tại trong cải cách 2025; "một cũ → nhiều mới" thực tế nằm ở M. Phải nói rõ trong báo cáo, không ép M thành A. |
| F3 | Data 07 được xác minh bằng chính CSV nguồn đã dựng nên `edges.csv`. | Tra bảng có candidate-recall ≈ 100% **do cấu trúc**. Accuracy T2 trên Data 07 đo khả năng **chọn đúng trong các ứng viên**, không đo độ phủ của bảng. Phải khai báo tính vòng lặp này. |
| F4 | Data 06: 600 dòng, **100% `Lai`, 100% loại `B`**, ba kiểu `C1` 420 / `C2` 120 / `C3` 60; khoảng 68% ở Bắc Ninh, 78 phường. Không có cột "tình huống A–D". | Chỉ đo được recall của `Lai`. Muốn có precision/F1 phải thêm tập đối chứng `moi` (Data 01) và `cu` (Data 03). "Tình huống A–D" phải được gán bằng quy tắc từ gazetteer (mục 3, WP2). |
| F5 | Test Sprint 3 lấy đúng 20 mẫu từ mỗi tập Data 01/02/03/04/06 (khớp chuỗi chính xác: 20/21/20/21/20). 5 mẫu `Lai` của test đến từ Data 06. | Mọi huấn luyện dùng Data 04/06 phải loại mẫu trùng test/dev theo chuỗi chuẩn hóa **và** theo nhóm đơn vị hành chính. Tăng `Lai` F1 trên test bằng dữ liệu cùng generator chỉ chứng minh học được mẫu sinh, không chứng minh tổng quát. |
| F6 | Train có 16 `Lai` / 119 `cu` / 71 `moi`; dev 8 `Lai`. DYN: đầu T1 tuyến tính trên CLS, `t1_loss_weight=0.5`, ngưỡng 0,7 / margin 0,2. HEUR-JW suy T1 từ hệ của span hành chính khớp gazetteer. | Giả thuyết làm việc (suy luận): DYN thua vì thiếu dữ liệu `Lai` và không có tri thức gazetteer, không phải vì kiến trúc đầu phân loại. WP2 thiết kế để tách hai nguyên nhân này. |
| F7 | Dev có 8 `Lai` (< 10). | Theo protocol mục 7, hiệu chỉnh ngưỡng trên dev là `CALIBRATION_NOT_EVALUABLE`; muốn hiệu chỉnh phải dùng T1-dev tổng hợp tách nhóm và khai báo trước. |
| F8 | Data 04 và Data 06 để ngõ/hẻm **bên trong** `TenDuong` (ví dụ "Ngách 1/88 Phạm Tuấn Tài"); gold Sprint 3 tách `Ngo/Hem` riêng. | Không được đưa thẳng các tập này vào huấn luyện T0: sẽ dạy sai quy ước nhãn. Phải lọc dòng có tiền tố ngõ/hẻm/ngách/kiệt hoặc tách theo quy tắc guideline rồi kiểm mẫu. |
| F9 | Test có support 0 cho `MocDinhVi`, `HuongDi`, `GhiChu`, `ToaNha/CanHo`; dev có 1 `HuongDi`; train 5–6 mỗi nhãn. | H4 chỉ kiểm được "đường sá" so với "hành chính". Nhóm "mốc" ghi `NOT_EVALUABLE_NO_GOLD_SUPPORT`. |
| F10 | `src/modeling/cli.py` không có tham số `--seed`; seed nằm trong config. CRF-INDEP dùng L-BFGS tất định. | Đa seed neural cần config overlay theo seed. CRF đổi seed không đổi kết quả: ghi `DETERMINISTIC_SEED_INVARIANT`, không báo std giả. |
| F11 | Prediction test đã freeze của 5 hệ nằm trong `data/interim/modeling/sprint03/final_completion_20261005_v1/` (`light_test_runs_v2/`, `kaggle_final_output_v4/.../pcrf_test`, `dyn_test`, `dyn_off_test`). Checkpoint `best.pt` của PCRF c02 và DYN c02 có sẵn cục bộ. | Bootstrap CI và kiểm định ghép cặp làm được ngay trên CPU, không cần GPU, không đọc lại mô hình. |
| F12 | Protocol `s4-protocol-v1` ghi T2 ngoài phạm vi và "không dùng lại test Sprint 3 để phát triển". | Cần **Amendment A2** trước khi chạy (mục 2). |

## 2. Quyết định cần chủ dự án xác nhận trước khi chạy

**Amendment A2 (bổ sung, không sửa `s4-protocol-v1`). Trạng thái: chủ dự án đã duyệt cả năm điểm ngày 13/10/2026.**

1. Đưa **T2 baseline** vào phạm vi: tra bảng hai chiều trên Data 07 và phân tích đồ thị cạnh. Chỉ đọc gazetteer; không sửa, không phát hành lại gazetteer.
2. Cho phép **phân tích thống kê hậu nghiệm** (bootstrap, kiểm định ghép cặp) trên prediction test Sprint 3 đã freeze. Đây là báo cáo độ bất định, không phải phát triển mô hình.
3. Cho phép **huấn luyện lại đa seed** (1337, 2025) với cấu hình c02 đã khóa và chấm test Sprint 3 đúng một lần mỗi seed. Báo mọi seed; không chọn seed, checkpoint, ngưỡng bằng test.
4. Biến thể mô hình mới (đầu T1 có dữ liệu lai tổng hợp, CRF huấn luyện kèm thiếu trường) được chọn **chỉ bằng dev / dev tổng hợp tách nhóm**; kết quả trên test Sprint 3 ghi nhãn `POST_HOC_SECONDARY` vì test đã bị quan sát ở Sprint 3.
5. Mọi tập sinh tổng hợp dùng để huấn luyện/đánh giá thuộc **stress track**, báo riêng, không bù support quan sát.

**Việc cần chủ dự án tự làm:** đọc quota GPU trên giao diện Kaggle trước WP3b; xác nhận cho phép upload gói train/dev tổng hợp lên dataset Kaggle private (Data 06/04 dẫn xuất từ OSM và CSV hành chính, cùng họ nguồn đã upload ở Sprint 3).

## 3. Các gói việc

Ký hiệu trạng thái đầu ra: `PASS`, `PARTIAL`, `NEGATIVE_RESULT` (thí nghiệm chạy đúng, giả thuyết không được ủng hộ), `NOT_EVALUABLE`, `BLOCKED`.

### WP0 — Nền dùng chung (làm trước, khoảng nửa ngày, CPU)

- Ghi Amendment A2 thành `docs/sprints/sprint_04/08_amendment_a2_group1_scope.md` sau khi chủ dự án xác nhận.
- `src/evaluation/leak_guard.py`: từ `identity_registry.jsonl` và `train/dev/test` của `corpus_v1_release2`, dựng tập khóa loại trừ gồm chuỗi chuẩn hóa (NFC, hạ chữ, gộp khoảng trắng, bỏ dấu câu) và `source_group`. Hàm lọc một DataFrame benchmark, trả về phần giữ lại và lý do loại từng dòng.
- `src/evaluation/stats.py`: bootstrap theo mẫu và theo cụm (percentile, B = 10.000, seed cố định), bootstrap ghép cặp cho hiệu F1, hoán vị ngẫu nhiên xấp xỉ (approximate randomization), McNemar chính xác. Chỉ dùng `numpy` và thư viện chuẩn.
- Kiểm thử: `tests/test_group1_shared.py`.
- **Xong khi:** test mới PASS; `leak_guard` tái lập đúng các số trùng ở F5; bộ test hiện có không đổi kết quả.

### WP1 — T2 baseline, E2, E3 [Bắt buộc]

**Câu hỏi:** tra bảng đúng bao nhiêu theo từng chiều; chiều nào khó hơn; bao nhiêu lỗi là lỗi im lặng.

**Hệ thống so sánh (cố định trước khi chạy):**

| ID | Mô tả | Chiều |
|---|---|---|
| `T2-LOOKUP-STRICT` | Tra khóa đầy đủ trên `edges.csv`; chỉ trả lời khi đúng một ứng viên, còn lại abstain kèm danh sách ứng viên | cả hai |
| `T2-LOOKUP-DEFAULT` | Như trên nhưng luôn chọn một ứng viên theo luật mặc định khai báo trước: ưu tiên `merge_form` "Hợp nhất toàn bộ" → "Tách — nhập chủ yếu" → "Tách — một phần", hòa thì lấy `source_row` nhỏ nhất | cả hai |
| `T2-VNADMIN` | `vietnamadminunits.convert` qua adapter hiện có, **tắt geocoder mạng**, ghi nhánh fallback | cũ→mới; mới→cũ ghi `NOT_SUPPORTED` |
| `T2-SINGLE-VERSION` | Khớp tên trên gazetteer chỉ một hệ (không biết phiên bản) | cả hai; dùng đo tình huống D |
| `T2-STREET` (E2, [Nên]) | Chọn ứng viên bằng chỉ mục `tên đường → phường mới` dựng từ `osm_clean_addresses.csv`, loại mọi `ID_Node` của Data 07 | cũ→mới |

**Điều kiện đầu vào:** (a) *oracle-segmentation*: tách theo dấu phẩy từ phải sang, kiểm 100% khớp khóa gazetteer, báo số dòng không tách được; (b) *pipeline*: span từ HEUR-JW và CRF-INDEP rồi mới tra.

**Metric (tách theo chiều, theo `LoaiAnhXa`, theo `HinhThucSapNhap`):** accuracy đơn vị đích (khóa đầy đủ: mới = tỉnh + phường; cũ = tỉnh + huyện + phường); coverage và tỷ lệ abstain; **tỷ lệ lỗi im lặng** = số câu trả lời sai mà không có cảnh báo / tổng số mẫu; candidate-recall; số ứng viên trung bình. CI bootstrap theo cụm (cụm = đơn vị nguồn của chiều đang xét). E3: McNemar ghép cặp cũ→mới so với mới→cũ trên cùng 600 cặp.

**Phân tích đồ thị toàn bộ 10.597 cạnh:** phân phối fan-out (cũ→mới) và fan-in (mới→cũ), tỷ lệ khóa giải được tất định theo từng chiều, tách A/B/C/M. Ghi nhãn "cận cấu trúc", không gọi là accuracy quan sát.

**Phần T2 của H5:** đưa 600 chuỗi lai (Data 06) vào tra bảng → tỷ lệ thất bại/lỗi im lặng (tình huống C); đếm và đo tình huống D (tên phường tồn tại ở cả hai hệ trong cùng tỉnh nhưng tập cạnh khác nhau).

**Đầu ra:** `scripts/66_run_t2_baseline.py`, `src/evaluation/t2_lookup.py`, `src/evaluation/t2_scorer.py`, `tests/test_t2_baseline.py`; kết quả tại `data/processed/evaluation/sprint04/t2_baseline_20261014_v1/`; báo cáo `09_t2_baseline_results.md`.

**Xong khi:** có bảng T2 theo chiều × loại × hệ thống kèm CI; có số lỗi im lặng; có đoạn phân tích bất đối xứng; các giới hạn F1–F3 được nêu trong báo cáo; A/C trên Data 07 ghi `NOT_EVALUABLE_NO_SUPPORT`.

### WP2 — Đánh giá lại và sửa T1, bảng H5 [Bắt buộc]

**Bước A — đánh giá, không huấn luyện.** Dựng `t1_stress_v1` = Data 06 (`Lai`) + Data 01 (`moi`) + Data 03 (`cu`), sau khi `leak_guard` loại mẫu trùng train/dev/test. Gán thẻ tình huống cho từng mẫu bằng quy tắc từ gazetteer: A = `cu` có phường nguồn nhiều đích; B = `moi` có phường đích gộp từ nhiều nguồn; C = `Lai`; D = có tên phường trùng danh pháp giữa hai hệ. Chạy HEUR-JW và DYN (checkpoint c02 đã khóa, suy luận CPU cục bộ nếu runtime có sẵn; nếu không, gộp vào job Kaggle của WP3b). Báo ma trận nhầm lẫn, P/R/F1 từng lớp, tách theo `KieuLai` C1/C2/C3, theo tình huống A–D, theo tỉnh.

**Bước B — ba biến thể T1, chọn bằng dev.**

| ID | Ý tưởng | Chi phí | Trả lời câu hỏi |
|---|---|---|---|
| `T1-PIPE-<T0>` | Span của CRF-INDEP / PHOBERT-CRF / DYN + luật hệ quy chiếu của HEUR-JW trên gazetteer | CPU | Thiếu tri thức gazetteer có phải nguyên nhân chính? Đồng thời lấp ô `NOT_IMPLEMENTED` của CRF và PhoBERT-CRF |
| `T1-FEAT` | Phân loại tuyến tính nhỏ trên đặc trưng bề mặt + thành viên gazetteer (viết bằng `numpy`) | CPU | Mốc học máy rẻ |
| `DYN-T1-AUG` | Huấn luyện lại DYN c02 với train + dữ liệu lai tổng hợp tách nhóm | Kaggle GPU | Thiếu dữ liệu `Lai` có phải nguyên nhân? |

**Dữ liệu lai tổng hợp:** sinh bằng `generate_hybrid_addresses` với seed mới; chia `t1_synth_train / t1_synth_dev / t1_synth_eval` theo **mã phường mới** (nhóm rời nhau); loại mọi nhóm xuất hiện trong test/dev Sprint 3; xử lý quy ước `Ngo/Hem` theo F8; cân bằng thêm mẫu `cu`/`moi` để không dạy mô hình "có huyện thì là lai".

**Báo cáo:** Bảng H5 = hệ thống × {test Sprint 3 (64 eligible, `POST_HOC_SECONDARY`), `t1_synth_eval`, `t1_stress_v1`} × {accuracy, macro-F1, `Lai` P/R/F1, coverage, abstain}. Nếu `Lai` F1 vẫn bằng 0: viết giải thích âm có số liệu (phân phối posterior, ngưỡng, support).

**Đầu ra:** `scripts/67_build_t1_sets.py`, `scripts/68_run_t1_evaluation.py`, `src/evaluation/t1_pipeline.py`, `tests/test_t1_group1.py`; `data/processed/evaluation/sprint04/t1_h5_20261015_v1/`; báo cáo `10_t1_h5_results.md`.

### WP3 — Độ tin cậy T0/T1 [Bắt buộc]

**3a — CI và kiểm định trên prediction đã freeze (CPU, làm ngay).** Cho 5 hệ: T0 micro P/R/F1, F1 từng nhãn, T1 accuracy và macro-F1, mỗi số kèm CI 95% bootstrap theo mẫu và theo `source_group`. Cặp so sánh: PCRF–DYN, DYN bật–tắt, PCRF–CRF, PCRF–HEUR, CRF–HEUR, mỗi cặp có ΔF1, CI ghép cặp, p-value hoán vị và McNemar trên exact-match cả địa chỉ. Lặp lại cho dev và cho track 5 trường (4.800 hàng; ghi rõ đây là track development). Xác minh hash prediction trước khi tính; tái lập đúng điểm số đã công bố ở `49_sprint3_final_results.md` trước khi báo CI.

**3b — Đa seed (Kaggle).** PHOBERT-CRF c02 và PROPOSED-DYN c02 với seed 1337 và 2025 (seed 42 dùng lại run đã khóa): 4 lượt huấn luyện + suy luận; DYN tắt ràng buộc dùng lại trọng số DYN bật. Thứ tự ưu tiên khi thiếu quota: seed 1337 cho cả hai mô hình trước, rồi 2025; thiếu thì ghi `PARTIAL_SEEDS`. Chọn epoch theo quy tắc dev đã khóa. Báo từng seed và mean ± std (`ddof=1`, n = 3).

**Đầu ra:** `scripts/69_bootstrap_frozen_results.py`, `scripts/70_prepare_multiseed_kaggle.py`, config overlay tại `configs/modeling/sprint04/`, `tests/test_group1_reliability.py`; `data/processed/evaluation/sprint04/reliability_20261014_v1/`; báo cáo `11_reliability_results.md`.

**Kỳ vọng trung thực (suy luận):** với 100 mẫu và chênh 1 span, CI của PCRF và DYN gần như chắc chắn chồng nhau. Kết luận hợp lệ là "không phân biệt được", không phải "tương đương".

### WP4 — Thí nghiệm rẻ trên CPU: H2, H3, E1, H4 [Nên]

Mô hình chính: CRF-INDEP (huấn luyện lại vài giây); HEUR-JW chạy thêm ở các phép nhiễu lúc test. Siêu tham số CRF giữ nguyên cấu hình đã chọn ở Sprint 3 cho mọi điều kiện.

| TN | Thiết kế | Đối chứng bắt buộc | Giới hạn phải ghi |
|---|---|---|---|
| H3 | Dựng lại chuỗi test từ gold span theo thứ tự đảo (lớn→nhỏ) và 3 hoán vị ngẫu nhiên có seed; tính lại offset | Chuỗi dựng lại theo **thứ tự gốc** để tách ảnh hưởng của việc đổi dấu phân cách | Chuỗi dựng lại không còn nguyên văn; chỉ kiểm tính bền với thứ tự |
| E1 | 2×2: giữ/bỏ dấu phẩy × giữ/hạ chữ hoa; hai chế độ: nhiễu chỉ lúc test, và huấn luyện + test cùng điều kiện | Điều kiện gốc | Offset phải được ánh xạ lại và kiểm khả nghịch |
| H2 | CRF huấn luyện trên train, so với train + N địa chỉ thiếu trường (Data 04 qua `leak_guard`, xử lý F8); đánh giá bằng **scorer 5 trường** trên phần Data 04 giữ lại và trên 20 mẫu `04_missing` của test | Cùng kích thước tăng cường nhưng bằng địa chỉ đầy đủ (tách tác dụng của "thêm dữ liệu") | Nhãn Data 04 là silver từ generator; 20 mẫu test quá ít |
| H4 | F1 theo nhóm nhãn: hành chính / đường sá / mốc / khác, từ prediction đã freeze, kèm CI | — | Nhóm mốc `NOT_EVALUABLE_NO_GOLD_SUPPORT` |

**Đầu ra:** `scripts/71_run_cpu_hypothesis_experiments.py`, `src/evaluation/perturbations.py`, `tests/test_group1_cpu_experiments.py`; `data/processed/evaluation/sprint04/cpu_hypotheses_20261015_v1/`; báo cáo `12_cpu_hypothesis_results.md` với bốn bảng, kể cả kết quả âm.

### WP5 — Ablation thay cho adapter và tuyên bố về H1 [Nên]

- Ghép cặp DYN bật/tắt ràng buộc trên: test, dev, track 5 trường, từng seed của WP3b, và `t1_stress_v1` (phần `moi`, nơi ràng buộc cấm `QuanHuyen` mới có cơ hội tác dụng).
- Ablation nguồn T1 cho ràng buộc: (a) đầu T1 của DYN, (b) T1 của HEUR-JW, (c) T1 gold làm **oracle**, ghi nhãn rõ là cận trên và không phải kết quả mô hình. Mục đích: ràng buộc có thể giúp tới đâu nếu T1 hoàn hảo.
- Đếm "dư địa": số mẫu `moi` mà mô hình không ràng buộc dự đoán `QuanHuyen`. Nếu dư địa bằng 0 thì ràng buộc không có gì để sửa; nêu đúng như vậy.
- Mục trung thực: **H1 `NOT_TESTABLE`** vì không có gazetteer adapter hay type adapter nào được hiện thực; thứ đã kiểm là "mask T1 + giải mã có ràng buộc". Không diễn giải ablation này như bằng chứng về adapter.

**Đầu ra:** `scripts/72_run_constraint_ablation.py`; `data/processed/evaluation/sprint04/constraint_ablation_20261017_v1/`; báo cáo `13_constraint_ablation_and_h1.md`. Phụ thuộc WP3b và WP2.

### WP6 — Tổng hợp

`14_group1_summary.md`: một bảng giả thuyết (H1–H5, E1–E4) × trạng thái × bằng chứng; cập nhật `docs/data_quality.md`, README và mục 9 của `AGENTS.md`; chạy toàn bộ bộ test.

## 4. Thứ tự, phụ thuộc và lịch

```text
WP0 ─┬─ WP1 (T2)  ───────────────┐
     ├─ WP3a (CI) ───────────────┤
     ├─ WP4 (CPU) ───────────────┼─ WP6
     ├─ WP2-A ─ WP2-B ─┐         │
     └─ WP3b (Kaggle) ─┴─ WP5 ───┘
```

| Ngày | Việc | Cổng |
|---|---|---|
| 13/10 | Xác nhận Amendment A2; WP0 | Test dùng chung PASS |
| 14/10 | WP1; WP3a; bắt đầu WP4 | Tái lập đúng điểm Sprint 3 trước khi báo CI |
| 15/10 | WP2-A; dựng dữ liệu WP2-B; đóng gói Kaggle cho WP3b và `DYN-T1-AUG`; xong WP4 | Chủ dự án đọc quota và đồng ý upload |
| 16/10 | Chạy Kaggle; nhận artifact, kiểm hash; WP2-B | Chọn bằng dev xong trước khi chấm test |
| 17/10 | WP5; WP6 | Bộ test đầy đủ PASS |
| 18/10 | Dự phòng | — |

Các agent ghi vào tập file riêng (bảng mục 3), không hai agent nào cùng sửa một file. Chỉ WP6 sửa `data_quality.md`, README và `AGENTS.md`.

## 5. Quy tắc chung cho mọi gói việc

1. Tuân thủ `AGENTS.md`: WSL, không cài thư viện mới. `~/.venv_dacn` không có `pycrfsuite` hay `torch`; CRF chạy bằng `data/interim/evaluation/sprint03/runtime_py311`, neural CPU bằng `data/interim/modeling/sprint03/runtime_neural_d_v1`, mỗi loại một tiến trình riêng (chi tiết trong Khối chung của prompt). Ngoài ra: `pathlib`, seed cố định, CSV `utf-8-sig`, tên hàm/biến tiếng Anh, giữ tên cột tiếng Việt.
2. Không sửa `data/raw/`, `third_party/`, gold, split, gazetteer, checkpoint, prediction hay evidence đã có hash. Đầu ra mới vào thư mục có version; từ chối ghi đè.
3. Suy luận chỉ nhận văn bản. Metadata, `GT_*`, `KieuLai`, `LoaiAnhXa` chỉ dùng ở phía chấm điểm.
4. Không chọn mô hình, seed, ngưỡng, luật bằng test Sprint 3. Luật mặc định và danh sách hệ thống phải được ghi vào `run_manifest.json` trước khi chấm.
5. Quản trị nhẹ: mỗi run một `run_manifest.json` (hash đầu vào, hash mã, seed, phiên bản luật, thời gian). Không tạo thêm lớp ledger/audit mới.
6. Kết quả âm và `NOT_EVALUABLE` là đầu ra hợp lệ; ghi mẫu số và support cạnh mọi tỷ lệ.
7. Hành động ra ngoài (upload/submit Kaggle) chỉ làm sau khi chủ dự án đồng ý trong phiên.

## 6. Rủi ro

| Rủi ro | Xử lý |
|---|---|
| Quota Kaggle không đủ 4 lượt huấn luyện + `DYN-T1-AUG` | Ưu tiên: seed 1337 của hai mô hình → `DYN-T1-AUG` seed 42 → seed 2025. Phần thiếu ghi `PARTIAL_SEEDS` |
| T2 trên Data 07 quá dễ do F3 | Báo thêm điều kiện pipeline, chiều mới→cũ và phân tích đồ thị; nêu rõ tính vòng lặp |
| `Lai` F1 tăng nhờ học mẫu sinh (F5) | Báo riêng `t1_synth_eval` tách nhóm; test Sprint 3 chỉ là số phụ |
| CI rộng làm mất "người thắng" | Chấp nhận; viết kết luận theo CI |
| `vietnamadminunits` gọi geocoder mạng | Tắt geocoder, ghi nhánh fallback; không gọi dịch vụ ngoài |
