# 19. G2-6 — Kiểm khả năng có dữ liệu cho phần thiếu của Nhóm 1

**Ngày:** 15/10/2026. **Trạng thái gói: PASS** (kết quả thực chất là âm: không việc nào chạy được ngay; GhiChu mới chỉ có quyền, chưa có support). Chỉ đọc dữ liệu có sẵn; không tạo gold, không thêm cặp vào corpus.
Đầu ra chính thức: `data/processed/evaluation/sprint04/data_feasibility_20261016_v3/`. `v1` và `v2` là bản trước sửa lời theo review (giữ nguyên, không ghi đè); `v2` giống `v1` từng byte (trừ thời điểm/đường dẫn trong manifest), nên tái lập đã chứng minh. `v3` giữ nguyên mọi số liệu; chỉ đổi lời kết luận E2 (`conclusions.csv`), tên trạng thái nhãn và thêm cột `Support` (`label_verdicts.csv`, `metrics.json`). Script (script `scripts/74_audit_data_feasibility.py`; manifest, hash, ngưỡng khai báo ở `run_manifest.json`).

```bash
cd /mnt/d/DACN && source ~/.venv_dacn/bin/activate
python -m scripts.74_audit_data_feasibility   # từ chối ghi đè (mã 3); dùng --out-dir ..._v4 để chạy lại
```

## 1. Tái lập số "đo 15/10" (`reproduction_check.csv`)

15/17 số khớp: 1.631 dòng/18 cột, Data 07 600 (M 356, B 244), 361 đơn vị cũ chuỗi thô (340/19/1/1 → 21 đơn vị ≥ 2 đích), gazetteer 10.035 khóa cũ/471 có ≥ 2 mã mới, 10.597 cạnh (A 3, B 9.432, C 132, M 1.030), 5 phi nguyên tử, 287/1.631 `HinhHocThayDoi`.
**LỆCH 2 số:** "5 trong 21 đơn vị (7 dòng) cũng ≥ 2 đích trong gazetteer" — khóa chuỗi thô chính xác cho **1 đơn vị / 2 dòng** (Phường Ngọc Hà, Ba Đình); khóa chuẩn hóa cũng 1; coi trường trống là ký tự thay thế cho 4 đơn vị/11 dòng. Không tái lập được cách đếm ra 5/7 (phiên review độc lập cũng ra 1/2); báo cáo này giữ số đo được (1 đơn vị / 2 dòng), không dùng 5/7.

## 2. E2 — NEEDS_NEW_SOURCE

- Khóa chuỗi thô có nhược điểm: 1.206/1.631 dòng có `PhuongXa_Moi` rỗng (phường mới nằm ở `QuanHuyen_Moi`), tỉnh viết nhiều kiểu. Chuẩn hóa bằng alias + mapping (cùng bộ lọc với bộ sinh Data 07):

| Trạng thái dòng OSM (1.631) | Số dòng |
|---|---|
| ELIGIBLE (bằng chứng hợp lệ) | 773 (600 thuộc Data 07; 173 ngoài) |
| NEW_TARGET_UNRESOLVED | 414 (phường mới trống 89; tỉnh mới không nhận ra 27; tên không thuộc đơn vị mới 298) |
| OLD_KEY_NOT_IN_SOURCE | 253 (khóa cũ thiếu trường 208; tên không có 45) |
| STREET_OR_HOUSENUMBER_CHANGED | 188 |
| OBSERVED_TARGET_NOT_AN_EDGE | 3 (2 đơn vị) |

- **E2 âm sau bộ lọc hiện hành:** 50 đơn vị cũ hợp lệ, **0 đơn vị có ≥ 2 đích hợp lệ khớp cạnh gazetteer** (0 dòng, 0 cụm). Trong 21 đơn vị thô: chỉ **5/21 được chứng minh là artefact khóa** (4 biến thể chính tả + 1 trường trống); **15/21 là `NO_ELIGIBLE_ROW`, chưa đánh giá được** (mọi dòng bị loại; chưa biết có phải nhiều đích thật; ví dụ Quận 3|Phường Võ Thị Sáu 114 dòng, 99 dòng bị loại vì `NEW_TARGET_UNRESOLVED`); 1/21 có thêm đích không phải cạnh gazetteer (Phường Tiền Ninh Vệ → Võ Cường, 2 dòng, bảng chỉ có → Kinh Bắc; ngoài ra Hàng Mã → Ba Đình 1 dòng: chưa kiểm nguyên nhân, không dùng làm gold).
- **Hướng kiểm trước khi xin nguồn mới:** 298 dòng có tên phường mới không nhận ra (`NEW_WARD_NOT_A_KNOWN_UNIT`); có thể chứa đơn vị nhiều đích bị loại. Kiểm này chưa làm và không được thêm alias ngoài `administrative_alias.py`.
- 10/50 đơn vị hợp lệ có fan-out gazetteer ≥ 2 (461 dòng) nhưng mỗi đơn vị chỉ quan sát **1** đích. Tổng thể gazetteer có 471 đơn vị cũ fan-out ≥ 2, nên dữ liệu OSM hiện có phủ 10/471 (2,1%).
- Ngưỡng khai báo trong manifest: ≥ 10 đơn vị và ≥ 30 dòng (tiền lệ k = 10 ở báo cáo 09 §6). **Ngưỡng chọn sau khi đã thấy sơ bộ 0 đơn vị**; kết luận không đổi với mọi ngưỡng dương.
- "Đích có phụ thuộc tên đường" (`StreetDependence`) không đánh giá được: không có đơn vị nào đủ hai đích.

## 3. T2 loại A và C

| | Cạnh | Đơn vị cũ | Dòng OSM hợp lệ quan sát | Ghi chú | Trạng thái |
|---|---|---|---|---|---|
| A | 3 | 3 (HCM, Bình Dương, Bình Định) | 0 | không có dòng OSM nào với khóa cũ đó; snapshot đầy đủ có 11 dòng nhưng dựng cặp từ snapshot cho A bị cấm (AGENTS §6) | NOT_FEASIBLE (quần thể 3 < 10) |
| C | 132 | 132 (124 không đổi tên) | 0 | dựng từ snapshot (tính trong bộ nhớ): 16 dòng, 8 đơn vị; vòng lặp (đích lấy từ chính bảng) | NEEDS_NEW_SOURCE (dùng như kiểm tra tỉnh táo) |
| C đổi tên | 8 | 8 | 0 | thông tin duy nhất của C với tra theo tên | NOT_FEASIBLE (8 < 10) |

Bằng chứng tối thiểu để dựng cặp quan sát: dòng OSM có số nhà và tên đường không đổi so với snapshot đầy đủ; khóa cũ đầy đủ (tỉnh+huyện+phường) khớp một cạnh nguồn; đích quan sát là cạnh của đúng đơn vị cũ đó. Quan hệ A/C xác định theo bậc đồ thị. 149/773 dòng hợp lệ có `HinhHocThayDoi=True`; hình học không phải điều kiện đủ để kết luận ranh giới. Bộ sinh cho 612 dòng quan sát (Data 07 lấy mẫu 600 từ đó; chênh 773→612 chưa giải thích bằng phép đo), 4.008 dòng dựng (B 3.992, C 16).

## 4. Nhãn mốc và `Lai` thật (`label_source_assessment.csv`, `label_verdicts.csv`)

Trạng thái nhãn dùng tên riêng `RIGHTS_OK_SUPPORT_UNMEASURED` (có nguồn đã duyệt annotation nhưng chưa có mẫu gán), **khác** `RUNNABLE_NOW` theo ngưỡng ở E2/T2. Nhãn lấy **từ mô tả trong source register v1, không từ mẫu**; quyền theo decision log v2 (04 §3); số mẫu thu = 0 cho mọi nguồn (chưa trích), nên **không có số mẫu ước lượng**.

| Nhãn | Nguồn nêu trong mô tả | Có nguồn annotation APPROVED | Trạng thái |
|---|---|---|---|
| GhiChu | TB729, QHKT hiện hành, QHKT 2024, UEH event | TB729 (cloud/phân phối APPROVED*), QHKT hiện hành (cloud/phân phối PENDING) | RIGHTS_OK_SUPPORT_UNMEASURED; Support = NOT_MEASURED |
| MocDinhVi, HuongDi | chỉ UEH campus | không (PENDING, loại) | NEEDS_NEW_SOURCE |
| ToaNha/CanHo | QHKT 2024 (BLOCKED), UEH event (PENDING) | không | NEEDS_NEW_SOURCE |
| `Lai` người viết | chỉ UEH campus ("old_new_parallel_mentions_require_review") | không | NEEDS_NEW_SOURCE |

TB243 Phụ lục II không có trong register v1 (ghi theo manifest nguồn): chỉ hệ mới, local/annotation APPROVED, cloud/phân phối PENDING, không có nhãn mốc hay `Lai`. Ngữ cảnh đo được (`sprint3_gold_support.csv`): gold Sprint 3 có MocDinhVi/GhiChu 6, HuongDi 6, ToaNha/CanHo 5 ở train+dev nhưng 0 ở test; nguồn gốc từng dòng không được ghi, không quy cho nguồn nào.

## 5. Bảng kết luận

| Việc | Trạng thái | Số liệu | Blocker | Người quyết |
|---|---|---|---|---|
| E2 | NEEDS_NEW_SOURCE | 0/50 đơn vị có ≥ 2 đích hợp lệ | chưa có nguồn quan sát nhiều đích | chủ dự án (G2-7) |
| T2 A | NOT_FEASIBLE | 3 cạnh, 0 quan sát | quần thể quá nhỏ | Nhóm 1 (chỉ ca định tính) |
| T2 C | NEEDS_NEW_SOURCE | 132 cạnh, 0 quan sát, 124 trivial | thiếu dòng quan sát | chủ dự án |
| GhiChu | RIGHTS_OK_SUPPORT_UNMEASURED | 2 nguồn APPROVED nêu nhãn; Support NOT_MEASURED | chủ dự án gán tay mới biết đủ support hay không | chủ dự án (G2-3/G2-4) |
| MocDinhVi/HuongDi/ToaNha-CanHo/`Lai` thật | NEEDS_NEW_SOURCE | 0 nguồn APPROVED nêu nhãn | cần nguồn mới | chủ dự án (G2-7) |

## 6. Suy luận thay vì đo; kiểm thử

Suy luận: nguyên nhân Tiền Ninh Vệ/Hàng Mã; trạng thái `RIGHTS_OK_SUPPORT_UNMEASURED` của GhiChu dựa trên mô tả register, không đo từ mẫu; chênh 773 → 612 dòng quan sát của bộ sinh: nguyên nhân chưa đo (`generator_observed_equals_eligible=false`; review đếm 163 dòng ELIGIBLE trùng khóa, gần nhưng chưa bằng 161).

Kiểm thử: `tests/test_group2_feasibility.py` 17 test PASS (logic thuần, mã thoát 2/3, số thật, tái lập đúng v3). Bộ đầy đủ trong `~/.venv_dacn`: 483 test, 475 PASS / 8 SKIP / 0 FAIL (466 mốc + 17 mới).
