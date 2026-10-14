# WP2 — Đánh giá lại T1 (cu / moi / Lai) và bảng H5

**Ngày chạy:** 13/10/2026. **Run:** `data/processed/evaluation/sprint04/t1_h5_20261015_v1/`. **Tập dữ liệu:** `data/interim/modeling/sprint04/t1_sets_20261015_v1/`.
**Phạm vi:** Amendment A2 ([08_amendment_a2_group1_scope.md](08_amendment_a2_group1_scope.md)). Mọi số trên test Sprint 3 mang nhãn `POST_HOC_SECONDARY`; mọi tập tổng hợp thuộc stress track.

## 1. Trạng thái đầu ra

| Đầu ra | Trạng thái |
|---|---|
| Tập T1 tổng hợp tách nhóm + Data 06 held-out (`scripts/67`) | PASS (tái lập cùng hash) — train rất nhỏ, xem mục 3 |
| Thẻ tình huống A–D (`t1_situations.py`) | PASS |
| Chẩn đoán DYN từ prediction đã freeze (dev, test) | PASS |
| Tầng 1: HEUR-JW, T1-PIPE-CRF, T1-FEAT, T1-FEAT-NOGAZ, hai mốc tầm thường | PASS |
| T1-PIPE-PCRF, T1-PIPE-DYN, DYN gốc trên test Sprint 3 (prediction đã freeze) | PASS |
| Tầng 2: DYN gốc, T1-PIPE-PCRF, T1-PIPE-DYN trên hai tập stress; T1-HEAD-PROBE | **BLOCKED_LOCAL_NEURAL** (mục 7) |
| DYN-T1-AUG | DEFERRED_NEEDS_TRAINING_PROTOCOL_CHANGE |
| Giả thuyết H5 | **NEGATIVE_RESULT** cho mô hình đề xuất trên test Sprint 3; **không kết luận được** trên tập stress (mục 8) (với checkpoint Sprint 3 gốc; với checkpoint huấn luyện lại cục bộ: NEGATIVE_RESULT, xem 11.4) |

## 2. Tái lập các số đã kiểm trước khi viết hệ thống

Tái lập đúng: T1 test HEUR-JW 0,9219 / 0,9249; DYN 0,7188 / 0,5626, `Lai` F1 = 0 (support 5); mask 64 eligible / 20 null / 16 excluded; T1 trong corpus train 119/71/16/34, dev 31/15/8/6, test 49/25/6/20; Data 06 sau `leak_guard` 580 (C1 410 / C2 115 / C3 55), 48 nhóm; generator seed 20261015: 26.961 dòng snapshot, 5.258 dòng một đích, 753 phường mới, 3.000 dòng sinh, 244 trùng nguyên văn Data 06, 20 bị `leak_guard` loại, 527 nhóm, 74 dòng `UNRESOLVED`, nhóm lớn nhất 10,63%, 135 dòng `TenDuong` bắt đầu bằng ngõ/hẻm/ngách/kiệt; SHA-256 checkpoint DYN c02 khớp; SHA-256 prediction đã freeze của HEUR-JW, CRF-INDEP, PHOBERT-CRF, PROPOSED-DYN khớp `all_test_predictions_frozen.json`.

**Một số lệch, đã báo phiên điều phối và được quyết định:** số nhóm `UNRESOLVED` của dev/test. Định nghĩa dùng trong báo cáo này: `admin_group_key(TinhThanh, QuanHuyen hoặc rỗng, PhuongXa)` trên span gold đầu tiên của mỗi nhãn, tính trên **toàn bộ** mẫu: dev 28/45 khóa là `UNRESOLVED` (60 mẫu), test 43/57 (100 mẫu). Prompt ghi 23/40 và 34/48 theo tập con "mẫu có cả span `PhuongXa` và `TinhThanh`". Đây là số mô tả, không vào mẫu số của metric nào.

## 3. Tập dữ liệu T1 (`scripts/67_build_t1_sets.py`)

| Bước | Số dòng |
|---|---|
| Lai sinh mới (seed 20261015, target 3.000) | 3.000 |
| − trùng Data 06 (nguyên văn hoặc sau chuẩn hóa) | 2.756 |
| − `leak_guard` (train/dev/test Sprint 3) | 2.741 |
| − khóa `UNRESOLVED` | 2.667 |
| cu: Data 03 sau `leak_guard` | 1.477 (870 dòng `UNRESOLVED`) |
| moi: Data 01 sau `leak_guard` | 980 |
| Bể gộp trước khử trùng | 5.124 |
| − dòng cu có chuỗi trùng một chuỗi `Lai` của Data 06 | 22 |
| − chuỗi mang hai nhãn khác nhau trong bể | 40 |
| − chuỗi lặp | 2 |
| Bể cuối | 5.060 (473 nhóm `ADM`, 870 dòng `UNRESOLVED`) |

Chia theo nhóm `admin_group_key` (seed 20261015, phân tầng theo tỉnh mới, ≈ 60/20/20 số nhóm). Dòng `UNRESOLVED` chỉ vào eval và được đánh cờ.

Lọc lãnh thổ dev/test Sprint 3 khỏi train/dev (mục 1d): 79 cặp (tỉnh chuẩn hóa, tên phường bỏ tiền tố) và 26 nhóm `ADM`. Trong 2.865 dòng train/dev: **1.456 dòng bị loại theo cặp, 282 dòng bị loại chỉ theo nhóm**. Giới hạn của bộ lọc: 6 mẫu dev và 13 mẫu test không có đủ span `PhuongXa` và `TinhThanh` nên không sinh được cặp để loại.

| Phần | cu | moi | Lai | Tổng | Nhóm `ADM` | Dòng `UNRESOLVED` |
|---|---|---|---|---|---|---|
| `t1_synth_train` trước cân bằng | 42 | 35 | 777 | 854 | 48 | 0 |
| `t1_synth_train` (lấy mẫu xuống, không nhân bản) | 35 | 35 | 35 | **105** | 48 | 0 |
| `t1_synth_dev` | 8 | 29 | 236 | 273 | 94 | 0 |
| `t1_synth_eval` | 987 | 329 | 879 | 2.195 | 88 | 870 (đều là cu) |
| `t1_data06_heldout` | 0 | 0 | 580 | 580 | 48 nhóm | 0 |

Giao nhóm giữa ba phần = 0. `t1_data06_heldout`: 553 dòng (34 nhóm) thuộc nhóm chưa thấy trong train, 27 dòng thuộc nhóm đã thấy.

Kế toán phần train theo lớp (từ `t1_synth_excluded.csv`):

| Lớp | Dòng được chia vào train | − trùng cặp (tỉnh, phường) dev/test | − chỉ cùng nhóm `ADM` | Còn lại | − lấy mẫu xuống | Train cuối |
|---|---|---|---|---|---|---|
| cu | 434 | 299 | 93 | 42 | 7 | 35 |
| moi | 603 | 530 | 38 | 35 | 0 | 35 |
| Lai | 1.494 | 579 | 138 | 777 | 742 | 35 |

Phần dev mất 61 dòng theo cùng bộ lọc (cu 6, moi 19, Lai 36). Lớp moi là lớp giới hạn: chỉ 35 dòng moi của train nằm ngoài lãnh thổ dev/test Sprint 3.

**Giới hạn lớn nhất của tập huấn luyện.** Train chỉ còn 105 dòng vì ba lãnh thổ chứa phần lớn dữ liệu cu/moi (Ba Đình 704 dòng, Kinh Bắc 486, Võ Cường 260) cũng là lãnh thổ của dev/test Sprint 3 và bị loại đúng theo thiết kế; thêm vào đó 870/1.477 dòng cu của Data 03 mang khóa `UNRESOLVED` nên không được vào train. Dev chỉ có 8 mẫu cu. Thiết kế được giữ nguyên, không điều chỉnh sau khi thấy số.

**Mốc "chỉ dựa vào cấp huyện" (mục 1e).** Dùng cột huyện có/không (metadata, chỉ để kiểm dữ liệu): luật học được là có huyện → cu, không có huyện → moi; accuracy trên `t1_synth_eval` = 1.316/2.195 = 0,5995. Lớp `Lai` không suy ra được từ đặc trưng này (recall 0), lớp moi thì suy ra được hoàn toàn.

**Nhãn `Lai` mơ hồ do trùng danh pháp.** 22 chuỗi của `t1_data06_heldout` trùng nguyên một chuỗi được Data 03 ghi là địa chỉ cu thật. Tổng quát hơn, 355/580 dòng Data 06 held-out và 520/879 dòng `Lai` của eval mang thẻ D (tên phường tồn tại ở cả hai hệ trong cùng tỉnh mới): với các chuỗi này, văn bản một mình không phân biệt được "phường mới + huyện cũ" với "địa chỉ cũ hoàn chỉnh".

## 4. Định nghĩa vận hành của tình huống A–D

Đề cương (mục 1.2) không cho định nghĩa máy đọc. Định nghĩa dùng ở phía chấm điểm, chỉ từ `edges.csv` của `s3_v4_nso_dual_snapshot_release2`, mức chuẩn hóa N2:

- **A** — mẫu cu có đơn vị nguồn với nhiều hơn một đích mới.
- **B** — mẫu moi có phường đích gộp từ nhiều hơn một đơn vị cũ.
- **C** — mẫu `Lai`.
- **D** — tên phường của mẫu tồn tại ở cả hai hệ trong cùng tỉnh mới (`SingleVersionIndex.homonyms` theo cả hai chiều). Khóa so khớp giữ tiền tố loại đơn vị, nên tên không có tiền tố (đa số Data 03) không bao giờ nhận thẻ D.

Một mẫu có thể mang nhiều thẻ; không có thẻ nào thì `NONE`. Số mẫu: test Sprint 3 (64): A 8, B 11, C 5, D 11, NONE 29; `t1_synth_eval`: A 15, B 329, C 879, D 894, NONE 920; `t1_data06_heldout`: C 580, D 355.

## 5. Chẩn đoán DYN từ prediction đã freeze (không chạy mô hình)

Ngưỡng quan sát trong `trace.structure`: **threshold 0,7 / margin 0,2 trên cả 100 dòng test và 60 dòng dev** của run được `selection_lock.json` chỉ định. Lưu ý: run dev được chỉ định là biến thể `dev_proposed_no_constraint_v1` (`constraint_enabled: False`, không cấm huyện), còn run test là DYN có ràng buộc; cột dev vì vậy không so sánh trực tiếp được với cột test. Giá trị 0,8 trong `structural_policy` của config là giá trị trước hiệu chỉnh; `decoder_policy.json` của c02 ghi 0,7 / 0,2.

| | dev (53 eligible) | test (64 eligible) |
|---|---|---|
| Accuracy / macro-F1 có ngưỡng | 0,7736 / 0,5996 | 0,7188 / 0,5626 |
| Accuracy / macro-F1 argmax thuần (chẩn đoán) | 0,8302 / 0,6735 | 0,8594 / 0,5845 |
| Support `Lai` | 8 | 5 |
| `Lai` có argmax = `Lai` | 1 | 0 |
| …trong đó bị ngưỡng/margin đẩy sang `khong_ro` | 1 | 0 |
| `Lai` có argmax = cu | 7 | 5 |
| `Lai` bị ngưỡng/margin từ chối (bất kể argmax) | 1 | 1 |
| Posterior(`Lai`) trên mẫu `Lai`: trung vị [min – max] | 0,143 [0,070 – 0,402] | 0,147 [0,108 – 0,340] |
| Posterior(`Lai`) trên mẫu cu: trung vị [min – max] | 0,084 [0,057 – 0,358] | 0,110 [0,064 – 0,377] |
| Posterior(`Lai`) trên mẫu moi: trung vị [min – max] | 0,019 [0,016 – 0,090] | 0,034 [0,017 – 0,198] |

Ma trận nhầm lẫn test, có ngưỡng: cu→cu 36, cu→moi 1, cu→`khong_ro` 10; moi→moi 10, moi→cu 1, moi→`khong_ro` 1; `Lai`→cu 4, `Lai`→`khong_ro` 1. Argmax thuần: cu→cu 44, cu→moi 3; moi→moi 11, moi→cu 1; `Lai`→cu 5.

**Trả lời bằng số, *với checkpoint Kaggle seed 42 của Sprint 3*: `Lai` F1 = 0 là do đầu T1 không tách được lớp, không phải do ngưỡng.** (Phạm vi: chỉ checkpoint này. WP3b — `11_reliability_results.md`, phần b — cho thấy seed 42 và 2025 huấn luyện lại cục bộ lặp lại hiện tượng, argmax `Lai` 0/5; seed 1337 tách được một phần, argmax 3/5 kèm 5 mẫu cu bị gán `Lai`.) Trên test, không mẫu `Lai` nào có `Lai` là lớp xác suất cao nhất (0/5); bỏ ngưỡng thì `Lai` F1 vẫn bằng 0. Phân phối posterior(`Lai`) của mẫu `Lai` chồng lên phân phối của mẫu cu. Ngưỡng chỉ gây thêm một loại lỗi khác: 10 mẫu cu bị đẩy sang `khong_ro`; bỏ ngưỡng thì accuracy tăng từ 0,7188 lên 0,8594. Dòng argmax là phân tích chẩn đoán trên dữ liệu đã quan sát, không phải cấu hình đề xuất.

## 6. Bảng H5

Mỗi ô: accuracy [CI 95%] · macro-F1 ba lớp [CI] · `Lai` P / R / F1 (đúng/support) · số abstain. CI: cluster bootstrap theo `admin_group_key`, B = 10.000, seed 20261015. "GZ" = hệ dùng gazetteer.

### 6.1 Test Sprint 3 — 64 eligible, 33 cụm, `POST_HOC_SECONDARY`

| Hệ | GZ | Accuracy [CI] | Macro-F1 [CI] | `Lai` P / R / F1 (5) | Coverage | Abstain | Δ accuracy so với HEUR-JW [CI] | McNemar b/c, p |
|---|---|---|---|---|---|---|---|---|
| Mốc đa số (cu) | – | 0,7344 [0,590; 0,921] | 0,2823 [0,247; 0,320] | – / 0 / 0 | 1,000 | 0 | −0,188 [−0,339; 0,020] | 3/15, 0,0075 |
| Mốc một-đặc-trưng | có | 0,8438 [0,732; 0,920] | 0,5738 [0,439; 0,628] | – / 0 / 0 | 1,000 | 0 | −0,078 [−0,166; 0,000] | 2/7, 0,180 |
| HEUR-JW | có | 0,9219 [0,837; 0,979] | 0,9249 [0,836; 0,993] | 0,833 / 1,000 / 0,909 | 0,953 | 3 | — | — |
| DYN gốc | – | 0,7188 [0,542; 0,846] | 0,5626 [0,376; 0,621] | – / 0 / 0 | 0,813 | 12 | −0,203 [−0,388; −0,057] | 3/16, 0,0044 |
| T1-PIPE-CRF | có | 0,9375 [0,841; 0,988] | 0,9852 [0,956; 0,997] | 1 / 1 / 1 | 0,938 | 4 | +0,016 [−0,044; 0,061] | 2/1, 1,0 |
| T1-PIPE-PCRF | có | 0,9688 [0,906; 1,000] | 0,9819 [0,872; 1,000] | 1 / 1 / 1 | 0,969 | 2 | +0,047 [0,000; 0,103] | 3/0, 0,25 |
| T1-PIPE-DYN | có | 0,9688 [0,906; 1,000] | 0,9819 [0,872; 1,000] | 1 / 1 / 1 | 0,969 | 2 | +0,047 [0,000; 0,103] | 3/0, 0,25 |
| T1-FEAT | có | 0,7031 [0,477; 0,846] | 0,6637 [0,410; 0,814] | 0,263 / 1,000 / 0,417 | 1,000 | 0 | −0,219 [−0,434; −0,074] | 2/16, 0,0013 |
| T1-FEAT không gazetteer | – | 0,6563 [0,463; 0,796] | 0,5454 [0,360; 0,667] | 0,077 / 0,200 / 0,111 | 1,000 | 0 | −0,266 [−0,481; −0,095] | 5/22, 0,0015 |
| T1-HEAD-PROBE | – | BLOCKED_LOCAL_NEURAL | | | | | | |
| DYN-T1-AUG | – | DEFERRED_NEEDS_TRAINING_PROTOCOL_CHANGE | | | | | | |

Kiểm tra luật tái dùng: áp T1-PIPE lên chính span của HEUR-JW cho đúng T1 của HEUR-JW ở 100/100 mẫu test.

### 6.2 `t1_synth_eval` — 2.195 mẫu (cu 987 / moi 329 / Lai 879), 365 cụm

| Hệ | GZ | Accuracy [CI] | Macro-F1 [CI] | `Lai` P / R / F1 (879) [CI F1] | Abstain | Δ accuracy so với HEUR-JW [CI] | McNemar b/c |
|---|---|---|---|---|---|---|---|
| Mốc đa số (cu) | – | 0,4497 [0,303; 0,676] | 0,2068 [0,155; 0,269] | – / 0 / 0 | 0 | −0,048 [−0,146; 0,038] | 163/269 |
| Mốc một-đặc-trưng | có | 0,5891 [0,499; 0,723] | 0,5491 [0,503; 0,582] | – / 0 / 0 | 0 | +0,091 [−0,079; 0,214] | 473/273 |
| HEUR-JW | có | 0,4980 [0,332; 0,723] | 0,3971 [0,269; 0,569] | 0,963 / 0,295 / 0,451 [0,213; 0,728] | 471 | — | — |
| T1-PIPE-CRF | có | 0,4984 [0,332; 0,722] | 0,3962 [0,269; 0,565] | 0,981 / 0,291 / 0,449 [0,210; 0,727] | 480 | +0,000 [−0,006; 0,010] | 13/12 |
| T1-FEAT | có | 0,8925 [0,813; 0,970] | 0,9106 [0,838; 0,967] | 0,898 / 0,843 / 0,870 [0,755; 0,969] | 0 | +0,395 [0,210; 0,534] | 953/87 |
| T1-FEAT không gazetteer | – | 0,8683 [0,817; 0,950] | 0,8878 [0,840; 0,937] | 0,993 / 0,694 / 0,817 [0,753; 0,931] | 0 | +0,370 [0,194; 0,503] | 901/88 |
| DYN gốc, T1-PIPE-PCRF, T1-PIPE-DYN, T1-HEAD-PROBE | | BLOCKED_LOCAL_NEURAL | | | | | |
| DYN-T1-AUG | | DEFERRED_NEEDS_TRAINING_PROTOCOL_CHANGE | | | | | |

Mốc một-đặc-trưng ở bảng này (1.293/2.195 = 0,5891) khác mốc 0,5995 (1.316/2.195) ở mục 3 vì **khác đặc trưng, cùng tập, cùng luật, không có abstain**: mục 3 dùng cột huyện có/không của metadata (chỉ để kiểm dữ liệu), còn bảng H5 dùng đặc trưng suy từ văn bản (tiền tố cấp huyện, hoặc một đoạn không phải đoạn cuối khớp chính xác tên một huyện cũ trong gazetteer). Chênh lệch đúng bằng 23 mẫu cu có cột huyện nhưng đặc trưng văn bản không nhận ra dấu hiệu cấp huyện, nên bị gán moi (cu→cu 964, cu→moi 23, moi→moi 329, `Lai`→cu 879).

Ma trận HEUR-JW: cu→cu 824, cu→`khong_ro` 151, cu→`Lai` 10, cu→moi 2; moi→moi 10, **moi→`khong_ro` 319**; **`Lai`→cu 593**, `Lai`→`Lai` 259, `Lai`→moi 26, `Lai`→`khong_ro` 1.
Chỉ phần có khóa `ADM` (1.325 mẫu, 88 cụm, bảng `h5_synth_eval_adm_only.csv`): HEUR-JW 0,290 [0,149; 0,571]; T1-FEAT 0,859 [0,753; 0,983]; T1-FEAT không gazetteer 0,796 [0,745; 0,907].

### 6.3 `t1_data06_heldout` — chỉ có lớp `Lai`; macro-F1 = `NOT_EVALUABLE_SINGLE_CLASS`

| Hệ | GZ | Recall `Lai`, toàn bộ (580; 48 cụm) [CI] | Recall `Lai`, nhóm chưa thấy trong train (553; 34 cụm) [CI] | Abstain | Δ so với HEUR-JW, toàn bộ [CI] |
|---|---|---|---|---|---|
| Mốc đa số, mốc một-đặc-trưng | | 0/580 = 0 | 0/553 = 0 | 0 | −0,295 [−0,600; −0,133] |
| HEUR-JW | có | 171/580 = 0,2948 [0,133; 0,600] | 150/553 = 0,2712 [0,111; 0,587] | 0 | — |
| T1-PIPE-CRF | có | 171/580 = 0,2948 [0,133; 0,600] | 150/553 = 0,2712 [0,111; 0,587] | 1 | 0 (0 cặp bất đồng) |
| T1-FEAT | có | 318/580 = 0,5483 [0,382; 0,818] | 294/553 = 0,5316 [0,359; 0,817] | 0 | +0,253 [0,098; 0,448]; b/c 147/0 |
| T1-FEAT không gazetteer | – | 151/580 = 0,2603 [0,155; 0,325] | 147/553 = 0,2658 [0,157; 0,332] | 0 | −0,034 [−0,433; 0,181]; b/c 134/154, p 0,26 |
| DYN gốc, T1-PIPE-PCRF, T1-PIPE-DYN, T1-HEAD-PROBE | | BLOCKED_LOCAL_NEURAL | | | |
| DYN-T1-AUG | | DEFERRED_NEEDS_TRAINING_PROTOCOL_CHANGE | | | |

Mọi dự đoán `Lai` trên tập này đều đúng theo cấu trúc (precision 1 vì không có lớp khác), nên chỉ recall có nghĩa.

### 6.4 Bảng phụ (số đúng / số mẫu; không tính CI vì tầng nhỏ)

**Theo `KieuLai` — recall `Lai`:**

| Tập | Kiểu | n | HEUR-JW | T1-PIPE-CRF | T1-FEAT | T1-FEAT không GZ |
|---|---|---|---|---|---|---|
| `t1_synth_eval` | C1 | 621 | 245 (0,395) | 243 (0,391) | 519 (0,836) | 360 (0,580) |
| | C2 | 184 | 14 (0,076) | 13 (0,071) | 184 (1,000) | 177 (0,962) |
| | C3 | 74 | 0 (0) | 0 (0) | 38 (0,514) | 73 (0,986) |
| `t1_data06_heldout` | C1 | 410 | 151 (0,368) | 151 (0,368) | 203 (0,495) | 6 (0,015) |
| | C2 | 115 | 20 (0,174) | 20 (0,174) | 115 (1,000) | 101 (0,878) |
| | C3 | 55 | 0 (0) | 0 (0) | 0 (0) | 44 (0,800) |

**Theo thẻ tình huống — accuracy:**

| Tập | Thẻ | n | HEUR-JW | DYN gốc | T1-PIPE-CRF | T1-PIPE-PCRF / -DYN | T1-FEAT | T1-FEAT không GZ |
|---|---|---|---|---|---|---|---|---|
| Test Sprint 3 | A | 8 | 8 | 8 | 8 | 8 / 8 | 8 | 8 |
| | B | 11 | 10 | 10 | 11 | 11 / 11 | 11 | 11 |
| | C | 5 | 5 | 0 | 5 | 5 / 5 | 5 | 1 |
| | D | 11 | 11 | 7 | 11 | 11 / 11 | 5 | 6 |
| | NONE | 29 | 25 | 21 | 25 | 27 / 27 | 16 | 16 |
| `t1_synth_eval` | A | 15 | 15 | BLOCKED | 15 | BLOCKED | 14 | 15 |
| | B | 329 | 10 (0,030) | BLOCKED | 9 | BLOCKED | 329 | 329 |
| | C và D | 520 | 10 (0,019) | BLOCKED | 7 | BLOCKED | 418 (0,804) | 319 (0,613) |
| | C không D | 359 | 249 (0,694) | BLOCKED | 249 | BLOCKED | 323 (0,900) | 291 (0,811) |
| | NONE | 920 | 759 (0,825) | BLOCKED | 764 | BLOCKED | 871 (0,947) | 900 (0,978) |
| `t1_data06_heldout` | C và D | 355 | 3 (0,008) | BLOCKED | 3 | BLOCKED | 148 (0,417) | 88 (0,248) |
| | C không D | 225 | 168 (0,747) | BLOCKED | 168 | BLOCKED | 170 (0,756) | 63 (0,280) |

5 mẫu `Lai` của test Sprint 3 đều thuộc nhóm "C không D".

**Theo tỉnh mới** (5 tỉnh nhiều mẫu nhất + còn lại): `tables/h5_by_province.csv`. Trên `t1_synth_eval`: Bắc Ninh 709 mẫu — HEUR-JW 52 (0,073), T1-FEAT 561 (0,791); TP.HCM 597 — 400 (0,670) và 528 (0,884); Hà Nội 581 — 522 (0,898) và 576 (0,991); Cần Thơ 54 — 21 và 53; Đà Nẵng 36 — 25 và 36; còn lại 218 — 73 và 205. Trên `t1_data06_heldout`: Bắc Ninh 390 — HEUR-JW 32 (0,082), T1-FEAT 164 (0,421); TP.HCM 111 — 97 và 105; Hà Nội 50 — 27 và 29.

### 6.5 Chọn tham số

T1-FEAT và T1-FEAT không gazetteer được huấn luyện trên 105 dòng `t1_synth_train`, chọn L2 bằng `t1_synth_dev` (273 dòng, chỉ 8 cu); số trên test Sprint 3 của chúng là `POST_HOC_SECONDARY`.

| Hệ | Số đặc trưng | L2 = 0,01 | L2 = 0,1 | L2 = 1 | Chọn |
|---|---|---|---|---|---|
| T1-FEAT | 44 | macro-F1 0,8735 / acc 0,9670 | 0,8735 / 0,9670 | 0,8735 / 0,9670 | 1 (hòa → L2 lớn hơn, luật khai báo trước) |
| T1-FEAT không gazetteer | 17 | 0,7821 / 0,9121 | 0,7821 / 0,9121 | 0,7781 / 0,9084 | 0,1 |

Với T1-FEAT, ba giá trị L2 cho cùng một kết quả trên `t1_synth_dev` (273 dòng, chỉ 8 cu), nên việc "chọn bằng dev" **không mang thông tin phân biệt**: L2 = 1 được lấy chỉ theo luật hòa khai báo trước (hòa → L2 lớn hơn), không phải vì dev ủng hộ nó. Với biến thể không gazetteer, hai giá trị 0,01 và 0,1 cũng hòa nhau và 0,1 được lấy theo cùng luật hòa; dev chỉ loại được L2 = 1.

## 7. Tầng 2 — BLOCKED_LOCAL_NEURAL

Bước smoke dừng ở việc dựng adapter; không có suy luận neural cục bộ nào được chạy. Môi trường: Python 3.11.16, torch 2.8.0+cpu, `torch.cuda.is_available() = False`, 6 luồng, JRE của dự án tại `data/interim/modeling/sprint03/resources_d_v1/java17/`.

Hai lần thử, đều qua `modeling_config` + `build_adapter`, checkpoint DYN c02 (SHA-256 khớp), resource lock `task_01_06_20261003_v1/resource_lock_local_v1.json`, decoder policy `c02_calibration/decoder_policy.json`:

1. Config huấn luyện đã freeze, không đổi gì (`device: cuda:0`):
   `RuntimeError: ['CUDA_NOT_AVAILABLE:no automatic CPU fallback']` — từ `src/modeling/resources.py::preflight`, gọi trong `PhoBERTCRFAdapter.__init__`.
2. Bản sao config chỉ đổi `device` thành `cpu`:
   `ValueError: RESUME_CONFIG_MISMATCH` — từ `src/modeling/checkpoints.py::validate_checkpoint_metadata`: `training_signature` của checkpoint được tính trên config Kaggle (gồm `device` và `hardware_profile`).

Cả hai là kiểm tra có chủ đích của mã đã khóa nên không tìm cách vòng. Resource lock không phải nguyên nhân: hash lock cục bộ trùng `resource_lock_sha256` trong metadata checkpoint (`621cb1db…`). Nguyên văn traceback: `tier2/status.json`. Đầu vào của tầng 2 (chỉ `key`, `text`) đã lưu tại `tier2_inputs/` (7 file: 105 / 273 / 2.195 / 580 / 240 / 60 / 100 dòng).

Hệ quả: DYN gốc, T1-PIPE-PCRF, T1-PIPE-DYN trên hai tập stress và T1-HEAD-PROBE trên cả ba cột đều `BLOCKED_LOCAL_NEURAL`. Cập nhật sau WP3b: WP3b đã huấn luyện cục bộ trên CPU và các checkpoint đó nạp được trên CPU, nên Tầng 2 có thể chạy trên checkpoint huấn luyện lại cục bộ (một gói riêng, chưa chạy). Trạng thái `BLOCKED_LOCAL_NEURAL` vẫn đúng với "DYN gốc" (checkpoint Kaggle `7a4a3d01…`), vì checkpoint này vẫn không nạp được trên CPU. Kết quả Tầng 2 trên checkpoint huấn luyện lại cục bộ: xem mục 11 (WP2b).

## 8. Diễn giải

**Giới hạn chung của mọi kết quả về `Lai`.** `Lai` của test Sprint 3, của Data 06 và của dữ liệu tổng hợp đến từ cùng một generator (`generate_hybrid_addresses`) trên cùng nguồn OSM. Kết quả tốt trên các tập này cho thấy hệ nhận được mẫu sinh, **không chứng minh tổng quát sang địa chỉ lai do người thật viết**.

**Vì sao HEUR-JW thắng DYN trên test.** Thay span của HEUR-JW bằng span của CRF-INDEP, PHOBERT-CRF hay DYN mà giữ nguyên bước tra gazetteer thì `Lai` vẫn đúng 5/5 và accuracy bằng hoặc cao hơn HEUR-JW (0,9375 – 0,9688 so với 0,9219; khác biệt không phân biệt được: McNemar p ≥ 0,25, CI của Δ chạm 0). Vậy lợi thế T1 của HEUR-JW trên test đến từ tri thức gazetteer, không từ chất lượng tách span. Điều này lấp ô T1 `NOT_IMPLEMENTED` của CRF-INDEP và PHOBERT-CRF bằng một pipeline, không phải bằng một đầu T1 học được.

**HEUR-JW không giữ được kết quả đó ngoài test.** Recall `Lai` giảm từ 5/5 trên test xuống 0,295 trên cả `t1_synth_eval` (259/879) và `t1_data06_heldout` (171/580). Lỗi tập trung ở trùng danh pháp (thẻ D): "C và D" đúng 3/355 (Data 06) và 10/520 (eval), trong khi "C không D" đúng 168/225 và 249/359. Khi phường mới trùng tên một phường cũ trong cùng huyện, luật tra theo ngữ cảnh chọn thực thể cũ và trả về cu. Cùng nguyên nhân làm 319/329 mẫu moi của eval rơi vào `khong_ro`. 5 mẫu `Lai` của test đều là "C không D", nên test Sprint 3 không đo được điểm yếu này.

**T1-FEAT.** Với 105 dòng huấn luyện, T1-FEAT đạt accuracy 0,8925 và `Lai` F1 0,870 trên `t1_synth_eval`, recall `Lai` 0,548 trên Data 06 (cao hơn HEUR-JW 0,253, CI [0,098; 0,448]). Nhưng trên test Sprint 3 nó thấp hơn HEUR-JW 0,219 (CI [−0,434; −0,074]) với 14 mẫu cu bị gán `Lai`. Biến thể bỏ gazetteer vẫn đạt 0,8683 trên eval: ba lớp tổng hợp đến từ ba nguồn có cách viết khác nhau (Data 03 không có tiền tố, Data 01 có tiền tố, generator ghép phường có tiền tố với huyện/tỉnh OSM thô), nên có thể bộ phân loại học **dấu vết nguồn dữ liệu** (suy luận từ việc biến thể không gazetteer vẫn đạt 0,8683 trên eval mà không chuyển sang test Sprint 3; chưa có thí nghiệm cô lập nguồn để xác nhận). Đóng góp của gazetteer thấy rõ ở Data 06 (0,548 so với 0,260) và ở 5 mẫu `Lai` của test (5/5 so với 1/5), nhưng không đồng nhất: ở C3 biến thể không gazetteer lại tốt hơn (44/55 so với 0/55). Không coi T1-FEAT là một hệ T1 dùng được; nó là mốc học máy rẻ cho thấy tập tổng hợp dễ bị học theo bề mặt.

**Đối chiếu H5 của đề cương** ("địa chỉ lai là lớp khó nhất và mô hình nhận biết phiên bản vượt trội rõ rệt ở lớp này"):

- *Vế "mô hình đề xuất vượt trội ở lớp `Lai`"* — **không được ủng hộ** trên test Sprint 3: PROPOSED-DYN có `Lai` 0/5, accuracy thấp hơn HEUR-JW 0,203 (CI [−0,388; −0,057], McNemar p = 0,0044), và chẩn đoán cho thấy đầu T1 của checkpoint Kaggle seed 42 không xếp `Lai` lên đầu ở mẫu nào (phạm vi chỉ checkpoint này; xem `11_reliability_results.md` phần b cho ba seed huấn luyện lại cục bộ). Trên hai tập stress: **không kết luận được** (`BLOCKED_LOCAL_NEURAL`). Support test chỉ 5 mẫu và là `POST_HOC_SECONDARY`.
- *Vế "`Lai` là lớp khó nhất"* — **không kết luận được ở dạng tổng quát**. Với DYN trên test, `Lai` là lớp duy nhất có recall 0. Với HEUR-JW trên `t1_synth_eval`, recall moi (10/329) còn thấp hơn recall `Lai` (259/879); cái khó đo được là trùng danh pháp giữa hai hệ (tình huống D), tác động lên cả moi và `Lai`.
- Hệ có tri thức phiên bản qua gazetteer (HEUR-JW, T1-PIPE-*) hơn DYN ở lớp `Lai` trên test (5/5 so với 0/5), nhưng đó là baseline luật, không phải mô hình đề xuất, và ưu thế này mất ở các mẫu trùng danh pháp.

**Hệ nào dùng gazetteer.** Có: HEUR-JW, T1-PIPE-CRF, T1-PIPE-PCRF, T1-PIPE-DYN, T1-FEAT, và mốc một-đặc-trưng (dùng tên huyện cũ của gazetteer để nhận dấu hiệu cấp huyện). Không: PROPOSED-DYN, T1-FEAT không gazetteer, T1-HEAD-PROBE, mốc đa số. HEUR-JW và T1-PIPE dùng gazetteer đã khóa `s3_v4_nso_dual_snapshot` (ngưỡng 0,86); thẻ tình huống dùng `s3_v4_nso_dual_snapshot_release2`.

## 9. Giới hạn

1. Tập huấn luyện tổng hợp chỉ 105 dòng (35 mỗi lớp) và dev chỉ 8 mẫu cu; CI trên eval rộng vì dữ liệu dồn vào ít nhóm (Bắc Ninh, TP.HCM, Hà Nội).
2. Cả ba lớp tổng hợp tách được phần lớn bằng cách viết của nguồn; kết quả T1-FEAT trên eval không chuyển sang test Sprint 3.
3. 870/987 mẫu cu của eval mang khóa `UNRESOLVED`: không chứng minh được chúng rời lãnh thổ với train. Số riêng phần `ADM` nằm ở `h5_synth_eval_adm_only.csv`.
4. Nhãn `Lai` của các chuỗi trùng danh pháp là nhãn theo cách sinh; 22 chuỗi Data 06 held-out trùng nguyên một địa chỉ cu của Data 03.
5. Bộ lọc lãnh thổ dev/test không có cặp để loại cho 6 mẫu dev và 13 mẫu test thiếu span `PhuongXa` hoặc `TinhThanh`.
6. Thẻ D chỉ khớp tên có tiền tố loại đơn vị; mẫu viết tên trần không được gắn D dù có thể trùng danh pháp.
7. Dữ liệu tổng hợp để ngõ/hẻm trong `TenDuong`; không có số T0 nào được suy ra từ các tập này.
8. Macro-F1 theo quy ước scorer Sprint 3 (lớp không có support trong một resample tính F1 = 0), nên CI macro-F1 trên test 64 mẫu bị kéo xuống ở các resample không có `Lai`.
9. Gazetteer mã cũ vẫn partial (phiên bản `s3-gazetteer-v4-nso-dual-snapshot-partial`).

## 10. Tái lập

```bash
cd /mnt/d/DACN && source ~/.venv_dacn/bin/activate
python -m scripts.67_build_t1_sets                      # từ chối ghi đè; thêm --output <dir mới> để chạy lại
python -m scripts.68_run_t1_evaluation                  # tầng 1; CRF-INDEP chạy thành tiến trình riêng trong runtime CRF
OMP_NUM_THREADS=6 MKL_NUM_THREADS=6 PYTHONDONTWRITEBYTECODE=1 \
  data/interim/modeling/sprint03/runtime_neural_d_v1/bin/python scripts/68b_run_t1_neural_local.py
python -m scripts.68_run_t1_evaluation --stage tier2    # ghi trạng thái/số của tầng 2
python -m unittest discover -s tests -v
```

Chạy lại `scripts/67` và tầng 1 của `scripts/68` vào thư mục mới cho cùng SHA-256 ở mọi CSV của tập dữ liệu và ở `predictions.jsonl`, `metrics.json`, `dyn_diagnostics.json`, các bảng `tables/*.csv`, span CRF và đầu vào tầng 2 (chỉ `run_manifest.json` khác vì có thời điểm).

Đầu ra của run: `run_manifest.json` (hệ thống, luật, seed khai báo trước khi chấm; SHA-256 đầu vào và mã), `predictions.jsonl`, `metrics.json`, `dyn_diagnostics.json`, `tables/` (`h5_main.csv`, `h5_main_tier2.csv`, `h5_main_combined.csv`, `h5_synth_eval_adm_only.csv`, `h5_by_kieu_lai.csv`, `h5_by_situation.csv`, `h5_by_province.csv`, `dyn_diagnosis_samples.csv`, `scoring_gold.csv`), `tier2_inputs/`, `tier2/status.json`.

## 11. Tầng 2 trên checkpoint huấn luyện lại cục bộ (WP2b)

**Nhãn bắt buộc cho mọi số của mục này: `LOCAL_CPU_RETRAINED`.** Đây là sáu checkpoint WP3b huấn luyện lại trên CPU cục bộ (c02, seed 42 / 1337 / 2025), **không phải** checkpoint đã khóa của Sprint 3 (`7a4a3d01…`). Các ô `BLOCKED_LOCAL_NEURAL` của "DYN gốc" ở mục 6 giữ nguyên; mục này thêm các hàng mới. Run: `data/processed/evaluation/sprint04/t1_h5_tier2_local_20261016_v1/` (bảng trong `tables/`); đầu ra suy luận và vector CLS: `data/interim/modeling/sprint04/t1_tier2_local_20261016_v1/`. Mọi tập tổng hợp là stress track; test Sprint 3 là `POST_HOC_SECONDARY`; không chọn seed, checkpoint hay ngưỡng bằng test.

### 11.1 Trạng thái và smoke

| Đầu ra | Trạng thái |
|---|---|
| Smoke sáu checkpoint (100 mẫu `s3_test` so với prediction test của WP3b) | **PASS 6/6**: span, `predicted_system`, `abstain` giống hệt 100/100; posterior DYN lệch tối đa 0,0 (ngưỡng 1e-6); vector CLS hợp lệ 100/100 (768 chiều) |
| Suy luận DYN × 3 (bảy tập, kèm CLS) và PHOBERT-CRF × 3 (ba tập) | PASS; mỗi checkpoint một tiến trình riêng; ≈ 123 s (DYN) và ≈ 99 s (PCRF) suy luận, chưa kể 140–390 s nạp |
| Hash prediction/CLS khóa trước khi chấm (`frozen_hashes.json`, 54 file) | PASS |
| Chấm: DYN, DYN argmax (chẩn đoán), T1-PIPE-PCRF, T1-PIPE-DYN, T1-HEAD-PROBE và biến thể chỉ-train-tổng-hợp × 3 seed × 5 cột | PASS (90 ô) |
| Chấm lại cùng hash đóng băng vào thư mục mới | PASS: mọi bảng, `predictions_tier2_local.jsonl`, `metrics.json` trùng SHA-256 |
| Ô tier-1 dùng làm tham chiếu (HEUR-JW, T1-PIPE-CRF, T1-FEAT) tính lại | PASS: 12/12 accuracy trùng bảng tầng 1 (`tier1_reference_check.csv`) |

Thời gian smoke (nạp / 100 mẫu): DYN 386 s / 36,7 s (seed 42), 141 s / 20,6 s (1337), 142 s / 19,5 s (2025); PCRF 262 s / 21,0 s, 142 s / 19,9 s, 137 s / 18,3 s. Ước lượng tổng ≈ 1,6 giờ (dưới ngưỡng 5 giờ); suy luận thực tế nhanh hơn ước lượng. 2/2.195 mẫu `synth_eval` bị processor từ chối ở cả sáu checkpoint (cùng hai mẫu); giữ trong mẫu số như `khong_ro`. Không có mẫu bị từ chối ở `data06` và `s3_test`.

SHA-256 đầy đủ sáu `best.pt` (epoch tốt nhất): DYN 42 `6210547365cad2b93674dcd007ed388a707bbc453e6b9b6824b96150953a14e4` (6); DYN 1337 `b70d0f7dd5091ddc9e7fd09b631f092f6c7b07b54b79c36d7a01639dcb41f034` (11); DYN 2025 `fc41f40702951dd13ddb906fb5b499eb78b185cd69a0e8eb4c481d50201f4695` (6); PCRF 42 `5306980e10328c82241492da8503ed97feaf5ae472a9118958653b6688084abd` (6); PCRF 1337 `54f1136b5e843626a0cbc58069fbb72d47d251e88a4c159706d0bc6acdb8c350` (6); PCRF 2025 `bb4ee1b587a6adb36c1bc0f7612ecee3b9438b88406227c4a75bfda993032d54` (7). Cũng có trong `run_manifest.json`.

### 11.2 Bảng chính — theo seed (42 / 1337 / 2025) và mean ± std (n = 3, ddof = 1)

CI cluster bootstrap từng seed (B = 10.000, seed 20261016) nằm trong `tables/h5_tier2_local_per_seed.csv`; mean ± std trong `h5_tier2_local_mean_std.csv`. "DYN thr." = ngưỡng đã khóa 0,7 / margin 0,2; "DYN argmax" = số chẩn đoán, không phải cấu hình. Tham chiếu tầng 1, ba số theo thứ tự accuracy test / accuracy `synth_eval` / `Lai` recall `data06`: HEUR-JW 0,9219 / 0,4980 / 0,2948; T1-PIPE-CRF 0,9375 / 0,4984 / 0,2948; T1-FEAT 0,7031 / 0,8925 / 0,5483.

**Test Sprint 3 — 64 eligible, `Lai` support 5, `POST_HOC_SECONDARY`**

| Hệ (`LOCAL_CPU_RETRAINED`) | Accuracy theo seed | Accuracy mean ± std | Macro-F1 mean ± std | `Lai` recall theo seed | Coverage mean |
|---|---|---|---|---|---|
| DYN thr. | 0,703 / 0,844 / 0,672 | 0,740 ± 0,092 | 0,562 ± 0,166 | 0 / 0,4 / 0 (chỉ seed 1337 dự đoán `Lai`: P 2/7) | 0,828 |
| DYN argmax | 0,891 / 0,859 / 0,891 | 0,880 ± 0,018 | 0,663 ± 0,084 | 0 / 0,6 / 0 | 1,000 |
| T1-PIPE-PCRF | 0,969 / 0,969 / 0,969 | 0,969 ± 0 | 0,982 ± 0 | 1 / 1 / 1 | 0,969 |
| T1-PIPE-DYN | 0,969 / 0,969 / 0,969 | 0,969 ± 0 | 0,982 ± 0 | 1 / 1 / 1 | 0,969 |
| T1-HEAD-PROBE (train tổng hợp + Sprint 3) | 0,859 / 0,828 / 0,859 | 0,849 ± 0,018 | 0,747 ± 0,015 | 0,6 / 0,8 / 0,4 (P 0,43 / 0,31 / 0,29) | 1,000 |
| T1-HEAD-PROBE, chỉ train tổng hợp | 0,766 / 0,719 / 0,656 | 0,714 ± 0,055 | 0,643 ± 0,065 | 0,4 / 1,0 / 0,2 (P 0,17 / 0,23 / 0,06) | 1,000 |

**`t1_synth_eval` — 2.195 mẫu (cu 987 / moi 329 / `Lai` 879), 365 cụm**

| Hệ | Accuracy theo seed | Accuracy mean ± std | Macro-F1 mean ± std | `Lai` recall theo seed | `Lai` F1 mean ± std |
|---|---|---|---|---|---|
| DYN thr. | 0,555 / 0,623 / 0,445 | 0,541 ± 0,090 | 0,507 ± 0,157 | 0 / 0,080 / 0 | 0,049 ± 0,085 |
| DYN argmax | 0,606 / 0,629 / 0,592 | 0,609 ± 0,019 | 0,583 ± 0,031 | 0,025 / 0,093 / 0 | 0,073 ± 0,088 |
| T1-PIPE-PCRF | 0,489 / 0,493 / 0,499 | 0,494 ± 0,005 | 0,395 ± 0,003 | 0,290 / 0,296 / 0,299 | 0,454 ± 0,005 |
| T1-PIPE-DYN | 0,488 / 0,495 / 0,489 | 0,491 ± 0,004 | 0,393 ± 0,002 | 0,290 / 0,296 / 0,294 | 0,451 ± 0,003 |
| T1-HEAD-PROBE | 0,756 / 0,750 / 0,749 | 0,752 ± 0,004 | 0,778 ± 0,006 | 0,416 / 0,410 / 0,407 | 0,576 ± 0,003 |
| T1-HEAD-PROBE, chỉ train tổng hợp | 0,818 / 0,881 / 0,810 | 0,836 ± 0,039 | 0,858 ± 0,038 | 0,634 / 0,845 / 0,636 | 0,776 ± 0,074 |

**`t1_data06_heldout` — chỉ có `Lai` (580; 553 dòng thuộc nhóm chưa thấy trong train); macro-F1 = `NOT_EVALUABLE_SINGLE_CLASS`; số = recall `Lai`**

| Hệ | Toàn bộ theo seed | Toàn bộ mean ± std | Nhóm chưa thấy mean ± std | Abstain theo seed (toàn bộ) |
|---|---|---|---|---|
| DYN thr. | 0 / 0,145 / 0 | 0,048 ± 0,084 | 0,047 ± 0,081 | 228 / 88 / 189 |
| DYN argmax | 0,002 / 0,219 / 0 | 0,074 ± 0,126 | 0,072 ± 0,124 | 0 / 0 / 0 |
| T1-PIPE-PCRF | 0,295 / 0,295 / 0,295 | 0,295 ± 0 | 0,271 ± 0 | 1 / 1 / 1 |
| T1-PIPE-DYN | 0,295 / 0,295 / 0,295 | 0,295 ± 0 | 0,271 ± 0 | 1 / 1 / 1 |
| T1-HEAD-PROBE | 0,152 / 0,405 / 0,169 | 0,242 ± 0,142 | 0,227 ± 0,143 | 0 / 0 / 0 |
| T1-HEAD-PROBE, chỉ train tổng hợp | 0,255 / 0,779 / 0,247 | 0,427 ± 0,305 | 0,426 ± 0,310 | 0 / 0 / 0 |

CI từng seed rộng ở các ô này (ví dụ DYN seed 1337 trên `data06`: 0,145 [0,031; 0,280]; probe chỉ-tổng-hợp seed 1337: 0,779 [0,618; 0,938] so với seed 42: 0,255 [0,153; 0,437]). Phần `t1_synth_eval_adm_only` nằm trong `h5_tier2_local_per_seed.csv`; bảng theo `KieuLai`, thẻ A–D và tỉnh: `tables/h5_tier2_local_by_*.csv`; ghép cặp với HEUR-JW và T1-FEAT: `tables/paired_vs_heur_and_feat.csv`.

**Ghép cặp (Δ accuracy [CI cụm 95%]; trích)**

| So sánh | seed 42 | seed 1337 | seed 2025 |
|---|---|---|---|
| DYN thr. − HEUR-JW, test | −0,218 [−0,411; −0,071], p 0,0025 | −0,078 [−0,253; 0,073], p 0,27 | −0,250 [−0,363; −0,081], p 0,0015 |
| DYN thr. − HEUR-JW, `synth_eval` | +0,057 [−0,135; 0,194] | +0,125 [−0,032; 0,234] | −0,053 [−0,168; 0,046] |
| DYN thr. − T1-FEAT, `synth_eval` | −0,337 [−0,450; −0,221] | −0,269 [−0,363; −0,169] | −0,447 [−0,571; −0,271] |
| DYN thr. − HEUR-JW, `data06` | −0,294 [−0,597; −0,134] | −0,150 [−0,473; 0,063] | −0,294 [−0,597; −0,134] |
| T1-PIPE-DYN − HEUR-JW, test | +0,047 [0,000; 0,103], p 0,25 | như seed 42 | như seed 42 |
| T1-PIPE-DYN − HEUR-JW, `synth_eval` | −0,010 [−0,029; 0,000], p 0,0001 | −0,003 [−0,020; 0,010] | −0,008 [−0,030; 0,004] |
| T1-HEAD-PROBE − HEUR-JW, `synth_eval` | +0,258 [0,138; 0,348] | +0,252 [0,141; 0,340] | +0,251 [0,120; 0,347] |
| T1-HEAD-PROBE − T1-FEAT, `synth_eval` | −0,136 [−0,213; −0,039] | −0,142 [−0,239; −0,033] | −0,143 [−0,233; −0,049] |

### 11.3 Ba câu hỏi

**(i) DYN trên tập tổng hợp có tách được `Lai` không? Không ở seed 42 và 2025; seed 1337 tách được một phần nhỏ.** Với ngưỡng đã khóa, `Lai` recall trên `t1_synth_eval` là 0 / 0,080 / 0 (seed 42 / 1337 / 2025) và trên `data06` là 0 / 0,145 / 0; bỏ ngưỡng thì 0,025 / 0,093 / 0 và 0,002 / 0,219 / 0. Seed 1337 là seed duy nhất cho `Lai` khác 0 một cách đáng kể, đúng như WP3b trên test, nhưng recall vẫn thấp hơn HEUR-JW (0,295) trên `data06`, và Δ accuracy so với T1-FEAT là −0,27 đến −0,45 trên `synth_eval` ở mọi seed. Phần thua của DYN có ngưỡng so với argmax nằm ở abstain: 522 / 38 / 525 mẫu `synth_eval` và 228 / 88 / 189 mẫu `data06` bị đẩy sang `khong_ro`; mức này đổi mạnh theo seed (như WP3b báo trên test: 15 / 2 / 16). Trên `data06`, DYN không đạt mức HEUR-JW (0,295) ở cả ba seed; chỉ seed 1337 tách được một phần (`Lai` recall có ngưỡng 0,145, CI [0,031; 0,280]; CI ghép cặp với HEUR-JW [−0,473; 0,063] chứa 0). Kết luận "tách được một phần" chỉ đứng trên seed 1337.

**(ii) Biểu diễn CLS có đủ thông tin để một đầu tuyến tính tách `Lai` khi có dữ liệu `Lai` không? Có một phần, phụ thuộc mạnh vào seed của encoder; không kết luận chắc được.** Trả lời bằng biến thể khai báo chính trong `run_manifest.json` (hàng "T1-HEAD-PROBE": train tổng hợp + `s3_train`): trên `synth_eval` kết quả ổn định giữa seed, `Lai` recall 0,416 / 0,410 / 0,407 (0,411 ± 0,005) và accuracy 0,752 ± 0,004, cao hơn nhiều so với argmax của đầu T1 gốc cùng checkpoint (0,025 / 0,093 / 0). Sự phụ thuộc vào seed nằm ở `data06`: recall `Lai` 0,152 / 0,405 / 0,169, thấp hơn HEUR-JW (0,295) ở seed 42 và 2025. Probe chính vẫn dưới T1-FEAT trên `synth_eval` (Δ accuracy −0,14, CI không chạm 0 ở cả ba seed; đây là số của biến thể chính). Phân tích bổ sung, biến thể chỉ-train-tổng-hợp (105 dòng, 35 `Lai`): `Lai` recall trên `synth_eval` 0,634 / 0,845 / 0,636, accuracy 0,836 ± 0,039; trên `data06` 0,255 / 0,779 / 0,247 (tách tốt ở seed 1337, hai seed còn lại không hơn HEUR-JW). Với biến thể này, seed 1337 có Δ accuracy so với T1-FEAT −0,012 [−0,062; 0,029], CI chứa 0. Biến thể chính (có nhãn T1 của `s3_train`) **kém hơn** biến thể chỉ-tổng-hợp trên `synth_eval` (0,752 so với 0,836) và `data06` (recall 0,242 so với 0,427), nhưng cao hơn trên test Sprint 3 (0,849 so với 0,714). Dev chọn L2 không hòa ở probe nào (`probe_selection.csv`) nên việc chọn có mang thông tin, nhưng dev chỉ có 8 mẫu cu. Giới hạn: CLS của `s3_train` lấy từ encoder đã được huấn luyện trên chính 240 mẫu đó, nên phần Sprint 3 của tập huấn luyện probe không "mới" với encoder; probe huấn luyện trên 105 dòng tổng hợp cùng generator với `synth_eval` và `data06`, nên số tốt ở seed 1337 chưa chứng minh tổng quát sang địa chỉ lai do người thật viết; std theo seed (0,305 trên `data06`) lớn hơn chênh lệch giữa hai biến thể.

**(iii) T1-PIPE với span neural so với HEUR-JW và T1-PIPE-CRF.** Test Sprint 3: T1-PIPE-PCRF và T1-PIPE-DYN đều 0,9688 ở cả ba seed (std 0), `Lai` 5/5, bằng giá trị tầng 1 tính từ checkpoint Kaggle; so với HEUR-JW +0,047 [0,000; 0,103], McNemar p = 0,25 (không phân biệt được); so với T1-PIPE-CRF (0,9375) hơn 2 mẫu (62/64 so với 60/64). `data06`: 0,2948 ở mọi seed, giống hệt HEUR-JW và T1-PIPE-CRF (0 cặp lệch với HEUR-JW, b = c = 0). `synth_eval`: 0,494 ± 0,005 (PCRF) và 0,491 ± 0,004 (DYN) so với HEUR-JW 0,4980 và T1-PIPE-CRF 0,4984; chênh lệch so với HEUR-JW từ −0,010 đến +0,001. Thay span bằng span của mô hình neural huấn luyện lại, ở cả ba seed, **không đổi kết luận của tầng 1**: kết quả T1 của pipeline do bước tra gazetteer quyết định, không do mô hình tách span.

### 11.4 Cập nhật kết luận H5

- *Vế "mô hình đề xuất vượt trội ở lớp `Lai`"* — **không được ủng hộ** với các checkpoint huấn luyện lại cục bộ: trên test, accuracy DYN thấp hơn HEUR-JW ở cả ba seed (−0,218 / −0,078 / −0,250; hai trong ba CI không chạm 0) và `Lai` recall 0 / 0,4 / 0; trên `synth_eval` và `data06`, `Lai` recall của DYN ≤ 0,22 ở mọi seed, thấp hơn HEUR-JW (0,295) và T1-FEAT (0,548) trên `data06`. Phạm vi: các checkpoint huấn luyện lại cục bộ, không phải checkpoint Sprint 3; support `Lai` test chỉ 5; tập tổng hợp và `data06` cùng một generator (stress track). Trạng thái trên tập stress đổi từ "không kết luận được" sang `NEGATIVE_RESULT` cho các checkpoint huấn luyện lại cục bộ; với "DYN gốc" vẫn không kết luận được.
- *Vế "`Lai` là lớp khó nhất"* — **vẫn không kết luận được ở dạng tổng quát**: với DYN, `Lai` là lớp có recall thấp nhất (≈ 0); với HEUR-JW và T1-PIPE trên `synth_eval`, recall moi (tầng 1: 10/329) thấp hơn recall `Lai`; với probe, bảng chính không tách recall từng lớp (xem `h5_tier2_local_per_seed.csv` cho macro-F1).

### 11.5 Giới hạn và điểm suy luận

1. Mọi số mang nhãn `LOCAL_CPU_RETRAINED`; DYN seed 42 cục bộ trên test (accuracy 0,7031) khớp T1 do WP3b báo, khác checkpoint Kaggle (0,7188).
2. n = 3 seed: mean ± std là mô tả, không phải suy luận thống kê; CI từng seed là bootstrap theo cụm, không gộp seed.
3. `Lai` của test (5 mẫu), `data06` và dữ liệu tổng hợp cùng generator; không chứng minh tổng quát sang địa chỉ lai do người thật viết.
4. Probe là đầu tuyến tính trên đặc trưng đóng băng, không phải mô hình đề xuất được huấn luyện lại; `DYN-T1-AUG` vẫn `DEFERRED_NEEDS_TRAINING_PROTOCOL_CHANGE`.
5. **Suy luận, không đo:** (a) probe có `s3_train` kém hơn probe chỉ-tổng-hợp trên `synth_eval` có thể do lệch phân phối nhãn/cách viết giữa dữ liệu Sprint 3 và dữ liệu tổng hợp (không có thí nghiệm cô lập); (b) seed 1337 là seed duy nhất tách được `Lai` ở cả đầu gốc lẫn probe, gợi ý encoder seed đó mã hóa phiên bản tốt hơn, nhưng với n = 3 không phân biệt được với biến thiên ngẫu nhiên.
6. Script `68c` được thêm tùy chọn `--out` (chấm lại vào thư mục mới) sau lần chấm chính; hash mã trong `run_manifest.json` của run chính là hash trước thay đổi đó. Logic chấm không đổi (kiểm bằng việc mọi bảng trùng SHA-256 khi chấm lại).

### 11.6 Tái lập

```bash
cd /mnt/d/DACN && source ~/.venv_dacn/bin/activate
python -m scripts.68c_run_t1_tier2_local prepare              # từ chối ghi đè; kiểm hash 6 best.pt và 7 file đầu vào
NEURAL=data/interim/modeling/sprint03/runtime_neural_d_v1/bin/python
export OMP_NUM_THREADS=6 MKL_NUM_THREADS=6 PYTHONDONTWRITEBYTECODE=1
$NEURAL -m scripts.68c_run_t1_tier2_local smoke-all           # smoke 6 checkpoint
$NEURAL -m scripts.68c_run_t1_tier2_local infer-all           # suy luận, mỗi checkpoint một tiến trình
python -m scripts.68c_run_t1_tier2_local freeze               # khóa hash trước khi chấm
python -m scripts.68c_run_t1_tier2_local score                # chấm
python -m scripts.68c_run_t1_tier2_local score --out <thư mục mới>   # chấm lại để kiểm tái lập
```
