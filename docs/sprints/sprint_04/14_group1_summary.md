# 14. Tổng hợp kết quả Nhóm 1 (WP0–WP5)

**Ngày:** 15/10/2026. **Phạm vi:** tổng hợp WP0–WP5 của Nhóm 1 (kế hoạch `06_group1_science_gap_plan.md`, Amendment A2 `08_amendment_a2_group1_scope.md`). Không chạy thí nghiệm mới: mọi số đọc từ file kết quả đã commit bằng `scripts/73_generate_group1_report.py` (bảng sinh tự động; manifest, bảng kiểm chéo và nguồn từng ô ở `data/processed/evaluation/sprint04/group1_summary_20261015_v2/`; bản v1 là bản trước review WP6, giữ nguyên). Nguồn: báo cáo `09`–`13` đã sửa theo review và các bản review trong `reviews/` (WP1: `review_wp1_20261013.md`, review trong phiên điều phối 13/10 được ghi lại thành file ngày 15/10, không phải review mới).

**Cách đọc.** Test Sprint 3 (100 mẫu / 446 span) đã bị quan sát, nên mọi số trên test là hậu nghiệm; tập tổng hợp thuộc stress track; hàng `LOCAL_CPU_RETRAINED` là checkpoint huấn luyện lại trên CPU, không trộn với hàng Kaggle seed 42; kết quả âm giữ nguyên.

**Tóm tắt.**
- T0: PHOBERT-CRF 0,9843 và PROPOSED-DYN 0,9821 (Kaggle) không phân biệt được; ba seed cục bộ 0,9787 ± 0,0030 và 0,9783 ± 0,0111. PHOBERT-CRF hơn CRF-INDEP (0,9076) và HEUR-JW (0,9112) với CI ghép cặp loại 0 (WP3a).
- T1: mô hình đề xuất kém baseline luật (accuracy 0,719 so với 0,922); T1 tốt nhất đến từ ghép span với gazetteer (0,969).
- T2 (lần đầu có số): cũ→mới 0,965, mới→cũ 0,077 với luật mặc định; chênh là cấu trúc của cải cách.
- Giả thuyết: SUPPORTED H3, E3; PARTLY_SUPPORTED H2, E1; NOT_SUPPORTED H5; INCONCLUSIVE H4, E2; NOT_TESTABLE H1; NOT_RUN E4.

## a. Giả thuyết H1–H5 và thí nghiệm E1–E4

Trạng thái lấy từ **báo cáo đã sửa theo review** (nhãn gốc ghi cạnh bên); không nâng hạng, không làm mềm kết quả âm. Nhãn "quy đổi" của H2 và E1 là của WP6 (báo cáo 12 chỉ có nhãn từng ý). Phân công ĐACN/ĐATN theo đề cương mục 6.

| Mã | Phân công | Trạng thái | Nhãn gốc | Bằng chứng | Cỡ mẫu | Đường dẫn |
|---|---|---|---|---|---|---|
| H1 | ĐATN | **NOT_TESTABLE** | NOT_TESTABLE (13 §9.1) | Không có type/gazetteer adapter nào được hiện thực; thứ đã kiểm là mask T1 + giải mã ràng buộc, dư địa 0/25 mẫu gold-new trên test, ORACLE ΔF1 0,0000. Không ủng hộ cũng không bác bỏ H1. | test 100 mẫu (25 gold-new); 5 trường 4.800 dòng | 13_constraint_ablation_and_h1.md §9 |
| H2 | ĐACN | **PARTLY_SUPPORTED** | phần tụt: ủng hộ; phần phục hồi đặc thù: không ủng hộ (12 §3) | Tụt: BASE F1 `gt` 0,641 so với 0,948 khi đủ trường (giảm 32,4%; `surface`: 6,8%). Phục hồi: AUG-MISSING − AUG-FULL = −0,001 [−0,013; 0,011] (N = 240), thêm dữ liệu nói chung giúp +0,013 so với BASE: không đặc thù cho địa chỉ thiếu trường. | held-out 399 dòng, 300 dòng đầy đủ; 3 seed lấy mẫu; test 04_missing 20 mẫu | 12_cpu_hypothesis_results.md §3 |
| H3 | ĐACN | **SUPPORTED** | ủng hộ (12 §1) | CRF-INDEP F1 0,933 (thứ tự gốc dựng lại) → 0,217 khi đảo (Δ −0,716 [−0,742; −0,689]); HEUR-JW Δ −0,159. Chỉ kiểm trên CRF-INDEP và HEUR-JW; Tầng 2 neural NOT_RUN (12 §5). Chuỗi dựng lại không còn nguyên văn. | test 100 mẫu / 446 span | 12_cpu_hypothesis_results.md §1 |
| H4 | ĐATN | **INCONCLUSIVE** | không kết luận được ở mức tổng quát (12 §4) | ΔF1 hành chính − đường sá: HEUR-JW −0,038 [−0,068; −0,008], PHOBERT-CRF −0,015 [−0,035; 0,002], PROPOSED-DYN −0,020; 2/5 hệ có CI loại 0; nhóm mốc support 0 (`NOT_EVALUABLE_NO_GOLD_SUPPORT`). | test 100 mẫu (244 span hành chính, 200 đường sá, 0 mốc) | 12_cpu_hypothesis_results.md §4 |
| H5 | ĐACN | **NOT_SUPPORTED** | mô hình đề xuất: NEGATIVE_RESULT; "Lai khó nhất": không kết luận được (10 §8, §11.4) | Test Sprint 3: T1 PROPOSED-DYN 0,719 so với HEUR-JW 0,922 (Δ −0,203 [−0,389; −0,058]); ba seed cục bộ: accuracy 0,740 ± 0,092, `Lai` recall data06 0,048. T2: tra bảng không thất bại hoàn toàn trên chuỗi lai (lỗi im lặng 6/599); tình huống D, mới→cũ: 89 lỗi im lặng (63,1% trong nhóm D). | test 64 eligible (`Lai` 5); synth_eval 2.195; data06 580; Data 06 599 cho T2 | 10_t1_h5_results.md §6, §11; 09_t2_baseline_results.md §7 |
| E1 | ĐACN | **PARTLY_SUPPORTED** | ba ý: ủng hộ / ủng hộ một phần / không ủng hộ-không kết luận được; báo cáo không có phán quyết chung (12 §2) | Bỏ phẩy lúc test: CRF Δ −0,317, HEUR-JW Δ −0,134; huấn luyện cùng điều kiện còn Δ −0,058; hạ chữ CRF Δ −0,019 (chế độ a), −0,004 (chế độ b). Tầng 2 (neural) NOT_RUN. | test 100 mẫu | 12_cpu_hypothesis_results.md §2 |
| E2 | ĐATN | **INCONCLUSIVE** | INCONCLUSIVE (09 §6) | T2-STREET L2 0,993 so với mặc định 0,965 (Δ 0,028 [0,000; 0,135], 49 cụm), nhưng mỗi đơn vị cũ của Data 07 chỉ có một đích (trần luật hằng-theo-đơn-vị 1,000), nên không tách được tên đường khỏi việc nhớ đích. | Data 07: 600 cặp, 49 cụm đơn vị cũ | 09_t2_baseline_results.md §6 |
| E3 | ĐACN | **SUPPORTED** | được ủng hộ mạnh (09 §9) | DEFAULT-MAIN cũ→mới 0,965 so với mới→cũ 0,077 (Δ 0,888 [0,776; 0,930], 23 cụm); khóa giải tất định 95,3% (cũ) so với 4,1% (mới). Nguyên nhân cấu trúc, chỉ có B và M. | Data 07: 600 cặp (B 244, M 356); đồ thị 10.597 cạnh | 09_t2_baseline_results.md §5, §8, §9 |
| E4 | mục 6 không phân công | **NOT_RUN** | VQA đang HOLD (docs/data_quality.md) | Không chạy: Viet-Receipt-VQA đang HOLD, không có ground truth đầy đủ cho 130 chuỗi hóa đơn. | — | docs/data_quality.md |

## b. Bảng T0 / T1 / T2 hợp nhất

Mọi số trong bảng đọc từ file kết quả; nguồn từng ô ở `tables/unified_cells.csv`. Hàng `LOCAL_CPU_RETRAINED` là checkpoint huấn luyện lại trên CPU, **không trộn** với hàng Kaggle seed 42 của Sprint 3. Test Sprint 3 đã bị quan sát: mọi số trên test là hậu nghiệm.

### b1. T0 (test Sprint 3, 100 mẫu / 446 span)

*Sprint 3 (Kaggle T4, seed 42) với CI bootstrap theo mẫu — WP3a*

| Hệ | F1 [CI 95%] | exact-match toàn địa chỉ [CI] (tỷ lệ) |
|---|---|---|
| HEUR-JW | 0,9112 [0,8773; 0,9415] | 0,63 [0,54; 0,72] |
| CRF-INDEP | 0,9076 [0,8675; 0,9436] | 0,77 [0,68; 0,85] |
| PHOBERT-CRF | 0,9843 [0,9720; 0,9936] | 0,93 [0,88; 0,97] |
| PROPOSED-DYN | 0,9821 [0,9691; 0,9933] | 0,92 [0,86; 0,97] |
| PROPOSED-NO-CONSTRAINT | 0,9843 [0,9724; 0,9935] | 0,93 [0,88; 0,97] |

*`LOCAL_CPU_RETRAINED`, ba seed 42 / 1337 / 2025 trên CPU cục bộ — WP3b (không trộn với hàng Kaggle ở trên)*

| Hệ | F1 mean ± std (n = 3) | F1 theo seed | exact-match mean ± std |
|---|---|---|---|
| PHOBERT-CRF | 0,9787 ± 0,0030 | 0,9764 / 0,9775 / 0,9821 | 91,3 ± 1,2 |
| PROPOSED-DYN | 0,9783 ± 0,0111 | 0,9708 / 0,9910 / 0,9730 | 91,0 ± 4,4 |

*Hiệu PHOBERT-CRF − PROPOSED-DYN*

| Hệ | ΔF1 |
|---|---|
| Sprint 3, Kaggle seed 42 (WP3a) | +0,0022 [CI ghép cặp −0,0091; +0,0137] |
| ba seed cục bộ (WP3b) | +0,0004 ± 0,0122 (mean ± std của hiệu) |

### b2. T1 (test 64 eligible, `Lai` support 5; synth_eval 2.195; data06 580 — stress track)

*Test Sprint 3, 64 mẫu eligible, `Lai` support 5 (`POST_HOC_SECONDARY`) — checkpoint Sprint 3 và pipeline T1-PIPE (WP2)*

| Hệ | accuracy [CI cụm] | macro-F1 | `Lai` recall |
|---|---|---|---|
| HEUR-JW | 0,922 [0,837; 0,979] | 0,925 | 1,000 |
| DYN gốc (Kaggle seed 42) | 0,719 [0,542; 0,846] | 0,563 | 0,000 |
| T1-PIPE-CRF | 0,938 [0,841; 0,988] | 0,985 | 1,000 |
| T1-PIPE-PCRF | 0,969 [0,906; 1,000] | 0,982 | 1,000 |
| T1-PIPE-DYN | 0,969 [0,906; 1,000] | 0,982 | 1,000 |
| T1-FEAT | 0,703 [0,477; 0,846] | 0,664 | 1,000 |

*Tập stress (tổng hợp, cùng generator) — WP2*

| Hệ | synth_eval (2.195): accuracy | data06 (580, chỉ `Lai`): `Lai` recall |
|---|---|---|
| HEUR-JW | 0,498 | 0,295 |
| T1-FEAT | 0,892 | 0,548 |

*`LOCAL_CPU_RETRAINED`, ba seed — WP2b (checkpoint huấn luyện lại, không phải checkpoint Sprint 3)*

| Hệ | test: accuracy mean ± std | test: macro-F1 mean | synth_eval: accuracy mean | data06: `Lai` recall mean |
|---|---|---|---|---|
| DYN ngưỡng 0,7 / 0,2 | 0,740 ± 0,092 | 0,562 | 0,541 | 0,048 |
| DYN argmax (chẩn đoán) | 0,880 ± 0,018 | 0,663 | 0,609 | 0,074 |
| T1-PIPE-PCRF | 0,969 ± 0,000 | 0,982 | 0,494 | 0,295 |
| T1-PIPE-DYN | 0,969 ± 0,000 | 0,982 | 0,491 | 0,295 |
| T1-HEAD-PROBE | 0,849 ± 0,018 | 0,747 | 0,752 | 0,242 |

*Để so: DYN Sprint 3 trên Kaggle*

| Hệ | test: accuracy / macro-F1 |
|---|---|
| DYN (Kaggle seed 42, WP3b) | 0,719 / 0,563 |

### b3. T2 (Data 07, 600 cặp: B 244, M 356; A/C `NOT_EVALUABLE_NO_SUPPORT`; oracle-segmentation, N2)

*Oracle-segmentation, N2, 600 cặp — WP1*

| Hệ | cũ→mới: accuracy [CI cụm] | cũ→mới: lỗi im lặng (/600) | mới→cũ: accuracy [CI cụm] | mới→cũ: lỗi im lặng (/600) |
|---|---|---|---|---|
| STRICT | 0,407 [0,158; 0,927] | 0 | 0,000 (DEGENERATE: luôn abstain) | 0 |
| DEFAULT-MAIN | 0,965 [0,831; 1,000] | 21 | 0,077 [0,040; 0,224] | 554 |
| DEFAULT-FIRST | 0,955 [0,812; 0,997] | 27 | 0,037 [0,013; 0,196] | 578 |
| SINGLE-VERSION | 0,087 [0,016; 0,297] | 8 | 0,087 [0,017; 0,419] | 89 |
| T2-VNADMIN (geocoder tắt) | 0,962 [0,823; 1,000] | 21 |  |  |

*Điều kiện pipeline (span từ mô hình rồi DEFAULT-MAIN; cũ→mới; N2) — WP1*

| Hệ | accuracy | coverage |
|---|---|---|
| HEUR-JW → DEFAULT-MAIN | 0,950 | 0,988 |
| CRF-INDEP → DEFAULT-MAIN | 0,935 | 0,970 |

## c. Phát hiện xuyên gói

**1. T2: bất đối xứng do cấu trúc.** Bất đối xứng hai chiều là cấu trúc của cải cách, không phải độ khó của mô hình: 95,3% khóa cũ giải tất định so với 4,1% khóa mới (trung bình 3,20 phường cũ/phường mới); DEFAULT-MAIN đạt 0,965 cũ→mới và 0,077 mới→cũ với 554/600 lỗi im lặng (CI Δ cụm phường mới [0,776; 0,930]). Chuẩn hóa tên quan trọng hơn mọi luật chọn: accuracy cũ→mới 0,008 (N0) / 0,860 (N1) / 0,965 (N2). Mức 96,5% của luật mặc định là do cách lấy mẫu Data 07: đúng 1,000 trên cặp "nhập chủ yếu" (335) và 0,000 trên cặp "một phần" (21). Nguồn: `09_t2_baseline_results.md` §3, §8, §9.

**2. Mô hình đề xuất không hơn PhoBERT-CRF (T0) và kém baseline luật (T1).** Mô hình đề xuất không hơn PhoBERT-CRF ở T0: ba seed cục bộ cho PHOBERT-CRF 0,9787 ± 0,0030 và PROPOSED-DYN 0,9783 ± 0,0111; hiệu +0,0004 ± 0,0122 đổi dấu theo seed, hiệu Kaggle seed 42 (+0,0022, CI ghép cặp [−0,0091; +0,0137]) nằm trong biến thiên seed: không phân biệt được (không phải "tương đương"). Ở T1 mô hình kém baseline luật: accuracy 0,719 so với 0,922 của HEUR-JW (Δ −0,203 [−0,389; −0,058]), ba seed cục bộ 0,740 ± 0,092. T1 tốt nhất đến từ ghép span với gazetteer: T1-PIPE-PCRF/-DYN 0,969 ở cả ba seed, `Lai` recall 1,000 trên test nhưng chỉ 0,295 trên data06 (trùng danh pháp). Biến thiên T1 của DYN giữa seed nằm ở tỷ lệ từ chối dưới ngưỡng cố định: accuracy argmax 0,891 / 0,859 / 0,891 (ổn định), accuracy có ngưỡng 0,703 / 0,844 / 0,672. Nguồn: `11_reliability_results.md` phần a, b5; `10_t1_h5_results.md` §11.

**3. Lớp CRF gần như không được dùng.** **Suy luận, không có thí nghiệm cô lập** (13 §9.2, §11): đường giải mã không ràng buộc của PhoBERT-CRF và DYN gần như là argmax của emission (encoder + lớp tuyến tính) dưới mặt nạ BIO, nên lớp CRF gần như không được dùng. Cơ sở đo: độ lớn tham số transitions tối đa chỉ 0,092 ở cả 8 checkpoint (DYN Kaggle [−0,068; +0,045], PHOBERT-CRF Kaggle [−0,077; +0,050], DYN seed 1337 [−0,092; +0,055]; đo lại từ `crf_params/*.json`, `tables/cross_check.csv`), trong khi khoảng cách emission top-1/top-2 của **DYN Kaggle trên test** có trung vị 3,29 (số đo của review WP5, Q2, báo cáo 13 §2 trích lại; không đo lại ở gói này và không đo cho PhoBERT-CRF). Hệ quả đã đo: dư địa của ràng buộc bằng 0 trên dữ liệu sạch (ý 4).

**4. Ràng buộc không có dư địa trên dữ liệu sạch.** Ràng buộc giải mã không có tác dụng trên dữ liệu sạch vì dư địa bằng 0: đường giải mã không ràng buộc không sinh `QuanHuyen` cho địa chỉ mới (0/25 mẫu gold-new trên test; một mẫu ngoại lệ ở seed 1337). Ràng buộc kích hoạt 20 mẫu nhưng chỉ đổi 1 mẫu và làm hại (ΔF1 −0,0022, CI chạm 0); ba seed cục bộ đổi 0 mẫu. Dư địa chỉ có trên track 5 trường (`DEVELOPMENT_TRACK`, nhiễu/thiếu trường): 168/1861 mẫu, DYN chỉ khai thác 4; cận trên ORACLE ΔF1 +0,0019 [+0,0013; +0,0025] (đánh giá thấp vì scorer 5 trường so bề mặt chưa chuẩn hóa; không so với std giữa seed). Nguồn: `13_constraint_ablation_and_h1.md` §2, §6, §7.

**5. H2 phụ thuộc thước đo.** H2 phụ thuộc thước đo: BASE tụt 32,4% theo `gt` (F1 0,641 so với 0,948; 399 dòng thiếu trường so với 300 dòng đầy đủ) nhưng chỉ 6,8% theo `surface` (Δ −0,064); chênh chủ yếu do 25,3% trường GT vắng khỏi chuỗi (báo cáo 12 §3). Thêm dữ liệu thiếu trường không hơn thêm dữ liệu đầy đủ (Δ −0,001 [−0,013; 0,011]). Nguồn: `12_cpu_hypothesis_results.md` §3.

## d. Giới hạn và đe dọa tính hợp lệ

1. **Test 100 mẫu / 446 span đã bị quan sát ở Sprint 3**; CI chỉ phản ánh lấy mẫu; hiệu nhỏ hơn khoảng ±0,011 F1 không phân biệt được (11a §4, §8).
2. **Gold do một người gán có AI hỗ trợ; IAA chưa đo** (`NOT_MEASURED`): CI không phản ánh nhiễu nhãn (11a §8).
3. **Data 07** chỉ có B (244) và M (356); A và C `NOT_EVALUABLE_NO_SUPPORT`; 23 mã phường mới, 49 đơn vị cũ chuẩn hóa, 441/600 dòng ở Hà Nội, một đơn vị cũ chiếm 299 cặp; được xác minh bằng chính CSV nguồn của gazetteer nên candidate-recall 100% là do cấu trúc (tính vòng lặp) và mỗi đơn vị cũ chỉ có một đích quan sát, nên không đo được việc chọn đích khác nhau trong cùng một đơn vị (09 §10).
4. **Dữ liệu lai cùng một generator**: `Lai` của test, Data 06 và tập tổng hợp đều sinh bằng `generate_hybrid_addresses` từ cùng nguồn OSM; kết quả tốt trên chúng không chứng minh tổng quát sang địa chỉ lai do người thật viết; tập huấn luyện T1 tổng hợp chỉ 105 dòng (10 §3, §8, §9).
5. **Nhãn hiếm và nhãn mốc không có support**: `ToaNha/CanHo`, `MocDinhVi`, `HuongDi`, `GhiChu` support 0 (`NOT_EVALUABLE_NO_GOLD_SUPPORT`); `Khac` support 2; `Lai` support 5 (test) và 8 (dev) — mọi số `Lai` là `LOW_SUPPORT` (11a §2, §8).
6. **Checkpoint Kaggle (GPU T4) so với cục bộ (CPU)**: hai nhóm riêng, seed danh nghĩa 42 không cùng lần huấn luyện; **ba seed là ước lượng thô** (n = 3, ddof = 1, cùng một test nên không độc lập về mẫu); tính tất định mới kiểm trên PHOBERT-CRF seed 42 (11b b4, b6).
7. **Silver và track phát triển**: nhãn Data 04 là silver từ generator; thước đo `gt` của H2 bị chặn trên vì 25,3% trường GT vắng khỏi chuỗi (12 §3); track 5 trường là `DEVELOPMENT_TRACK`, hàng không độc lập nên CI theo dòng quá hẹp (13 §10).
8. **Gazetteer** mã cũ còn partial (2.187 mã chưa xác minh), hai snapshot 30/06 và 01/07/2025 không phải lịch sử hiệu lực pháp lý; T2 tra bằng tên (09 §10).
9. **Dev** đã dùng để chọn (`SELECTION_SET`), chỉ 8 mẫu `cu` và 8 `Lai` nên hiệu chỉnh ngưỡng T1 là `CALIBRATION_NOT_EVALUABLE` (11a §6; protocol mục 7).
10. **Ngoài phạm vi đo**: VQA đang HOLD (E4), Data 05 hoãn, Deepparse chưa chạy vì chưa xác minh điều kiện sử dụng checkpoint (AGENTS.md mục 9).

## e. Phần còn thiếu, theo nguyên nhân

**(i) Thiếu do dữ liệu — chuyển Nhóm 2 / ĐATN.** Loại A và C ở T2 (Data 07 chỉ có B/M; gazetteer chỉ có 3 cạnh A và 132 cạnh C, 09 §8); E2 (cần dữ liệu mà một đơn vị cũ đi về ít nhất hai đích quan sát); nhãn mốc/hướng (support 0) và H4 theo nhóm mốc; `Lai` do người thật viết; Accuracy@161km (cần tọa độ); E4 (`NOT_RUN`, VQA đang HOLD: thiếu 130 chuỗi hóa đơn có ground truth đầy đủ).

**(ii) Thiếu do môi trường.** Tầng 2 của WP4 (H3 và E1 trên PHOBERT-CRF/PROPOSED-DYN) là `NOT_RUN`: adapter khóa đòi ≥ 20 GiB ổ D: trống, đo được khoảng 18 GiB lúc chạy (12 §5). WP2b chạy được cùng loại adapter khi ổ còn trống khoảng 28 GB (`free_bytes_at_prepare` trong manifest WP2b); suy luận (chưa chạy lại): giải phóng đĩa là đủ, lệnh nằm ở 12 §5. Ngoài ra "DYN gốc" (checkpoint Kaggle `7a4a3d01…`) trên hai tập stress vẫn `BLOCKED_LOCAL_NEURAL` vì checkpoint này không nạp được trên CPU (10 §7).

**(iii) Hoãn có chủ đích.** `DYN-T1-AUG` (`DEFERRED_NEEDS_TRAINING_PROTOCOL_CHANGE`: `load_corpus`/`load_config` ghim hash, cần protocol huấn luyện mới); H1 (không có adapter; điều kiện cần ở 13 §9.3); ablation ràng buộc trên `t1_stress_v1` (cần suy luận neural, 13 §1).

**(iv) Tùy chọn.** CI cho track 5 trường (WP3a §7, `NOT_RUN`); ô PHOBERT-CRF trên track 5 trường của WP5 (`NOT_RUN`); pipeline T2 với span neural (chỉ HEUR-JW và CRF-INDEP đã chạy, 09 §10); gán lặp intra-annotator; dev của DYN có ràng buộc `NOT_FOUND` (11a §6; WP5 đã dựng lại bằng giải mã lại).

## f. Sai lệch phát hiện ở bước kiểm chéo

Kiểm chéo bằng `scripts/73`: **191 hash đầu ra** khai báo trong `run_manifest.json` của tám run đều khớp file hiện tại (không MISMATCH, không thiếu file bắt buộc; trong đó 103 file prediction không commit nhưng có trên đĩa và khớp); **54 số tiêu đề** của báo cáo 09–13 được đối chiếu với `metrics.json`/CSV: 54 khớp, 0 lệch; **16 đại lượng** do hai gói cùng báo: 16 khớp, 0 lệch; **12 liên kết hash** giữa các run: 12 khớp, 0 khác. Chi tiết ở `tables/hash_verification.csv`, `cross_check.csv`, `cross_report_consistency.csv`, `cross_run_links.csv`. Báo cáo gốc không bị sửa.



- **Số liệu: không có số nào lệch** ở ba phép kiểm trên.
- **Quản trị WP3b (đã biết, 11b b1):** `run_manifest.json` của WP3b không khai báo hash đầu ra, nên `metrics.json` và `tables/per_seed.csv` không có hash để đối chiếu; chỉ kiểm được hash prediction đóng băng (`frozen_hashes.json`, khớp, và khớp với hash WP5 ghi lại). Hash mã trong manifest (bản B `87fd49e4…`) không khớp script đã commit (bản D); logic không đổi. Số WP3b vẫn khớp WP5 và WP2b (bảng nhất quán).
- **Review WP1 do phiên điều phối thực hiện** (`reviews/review_wp1_20261013.md`, review trong phiên 13/10 được ghi lại thành file ngày 15/10): không phải review của một phiên độc lập riêng như WP2–WP5.
- **Hai định nghĩa "tình huống D":** 09 §7.2 (tên phường trùng giữa hai hệ trong cùng tỉnh, phân nhóm theo cạnh gazetteer, trên Data 07) và 10 §4 (thẻ D của `SingleVersionIndex.homonyms` trên mẫu T1, nhạy với tiền tố loại đơn vị). Số hai báo cáo không so được; bảng a chỉ trích số D của báo cáo 09 cho T2.
- **Phán quyết chung của H2 và E1 là quy đổi của WP6:** báo cáo 12 cho nhãn từng ý (H2: tụt ủng hộ / phục hồi đặc thù không ủng hộ; E1: ba ý) và không có nhãn chung cho E1 (review WP4 N2). Hai ô này không phải "nhãn gốc" của báo cáo.
- **Cận "< 0,07" của báo cáo 13 §2 chỉ đúng với 4/8 checkpoint** (đo lại từ `crf_params/*.json`: PHOBERT-CRF Kaggle [−0,077; +0,050], DYN seed 1337 [−0,092; +0,055], PHOBERT-CRF seed 1337 và 2025 cũng vượt 0,07); độ lớn tối đa là 0,092. Báo cáo 13 là bản sau review và không bị sửa ở gói này; ý c3 dùng cận 0,092 (review WP6 Q1).
- **Làm tròn:** ba CI ở báo cáo 14 khác chữ số cuối so với báo cáo gốc; giá trị trong file là nguồn. H5 Δ T1 DYN − HEUR-JW [−0,389; −0,058] so với 10 §6.1 [−0,388; −0,057] (file −0,388889 / −0,057687; báo cáo 10 cắt bớt); H2 AUG-MISSING − AUG-FULL [−0,013; 0,011] so với 12 [−0,014; +0,011] (file −0,0135); H4 PHOBERT-CRF −0,015 so với 12 −0,016 (file −0,0155).
- **Con số tham số CRF < 0,07 và khoảng cách emission trung vị 3,29** (13 §2) là số đo của review WP5 (Q2) từ `crf_params/` (interim, không commit): không có trong file kết quả đã commit. Khoảng của transitions được đo lại từ file interim và khớp; trung vị 3,29 không đo lại.
- **Tên thư mục là mã phiên bản kế hoạch, không phải ngày chạy** (09 đầu báo cáo; 13 đầu báo cáo): ví dụ `t2_baseline_20261014_v1` chạy 13/10, `constraint_ablation_20261017_v1` chạy 14–15/10.
- Mốc số test trong các báo cáo (349 → 374 → 396 → 406 → 422 → 438) là lịch sử tăng dần theo gói, không phải lệch; mốc hiện tại ở mục dưới.

## Kiểm thử và tái lập

Bộ test đầy đủ (`python -m unittest discover -s tests -v`, `~/.venv_dacn`): 453 test, 445 PASS / 8 SKIP / 0 FAIL (438 trước WP6, cộng 15 test mới của tests/test_group1_summary.py).

```bash
cd /mnt/d/DACN && source ~/.venv_dacn/bin/activate
python -m scripts.73_generate_group1_report            # từ chối ghi đè; dùng --out-dir group1_summary_20261015_v3 để chạy lại
python -m unittest tests.test_group1_summary -v
python -m unittest discover -s tests
```

Mã thoát: 2 (không ghi gì) nếu một hash trong `run_manifest.json` của tám run không khớp, hoặc thiếu manifest/file bắt buộc; 3 nếu thư mục đầu ra đã tồn tại (không ghi đè); 0 nếu xong. Bản nháp báo cáo do script sinh nằm ở `report_draft.md` trong thư mục đầu ra; báo cáo này chỉ khác bản nháp ở dòng kết quả bộ test (chạy sau khi sinh).
