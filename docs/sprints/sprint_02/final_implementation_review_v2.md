# Kiểm toán triển khai cuối cùng và điều kiện phát hành v2

- **Ngày kiểm toán:** 20/09/2026
- **Vai trò:** Senior AI Engineer độc lập — NLP evaluation, data quality và reproducibility
- **Phạm vi:** mã nguồn, sáu tập benchmark, manifest/output baseline, bảng định lượng, dashboard và bộ tài liệu v2.
- **Nguyên tắc:** đọc và đối chiếu tĩnh; không sửa dữ liệu, không ghi đè kết quả baseline v1 đã đóng băng.

## 1. Kết luận điều hành

**Dữ liệu benchmark và output baseline v1 có tính toàn vẹn đủ để giữ làm mốc nội bộ. Bộ tài liệu v2 chưa đạt điều kiện dùng trong báo cáo chính thức hoặc bảo vệ.**

Hai lỗi P0 trong tài liệu v2 làm đứt chuỗi truy vết giữa kết quả, dữ liệu và diễn giải: (1) định nghĩa C1/C2/C3 của Data 06 bị đảo sai so với generator và CSV; (2) phần lớn case study trong `baseline_ambiguity_evidence_v2.md` không khớp chuỗi input thực tế của ID được nêu. Vì vậy, không được trích các bảng case, kết luận định lượng hay chương 1/2 v2 hiện tại làm bằng chứng khoa học trước khi tái lập chúng từ output đã đóng băng.

Không có bằng chứng cho thấy cần tái sinh Data 03 hoặc Data 04: Data 03 đang là mốc hệ cũ sạch đủ trường; Data 04 có ground truth `GT_*` đầy đủ và các trường bị xóa được kiểm soát. Việc sửa trước mắt là sửa **tài liệu và cơ chế tái lập**, không phải sửa dữ liệu nguồn. Một lần chạy baseline v2 chỉ cần thực hiện sau khi sửa các lỗi code ảnh hưởng protocol và chuyển output sang thư mục/ID phiên bản mới.

| Hạng mục | Trạng thái | Quyết định |
| --- | --- | --- |
| Sáu CSV benchmark và manifest v1 | Đạt kiểm tra tĩnh | Giữ đóng băng |
| Output 13.000 lượt dự đoán và raw log | Hash khớp manifest | Giữ đóng băng |
| Hợp đồng Data 03 và Data 04 | Đạt | Không tái sinh |
| Data 06, Data 07 trong CSV | Đạt cấu trúc; diễn giải v2 sai | Sửa tài liệu, thêm test ngữ nghĩa |
| Mã runner/versioning | Chưa đạt | Sửa trước lần chạy v2 |
| Tài liệu nghiên cứu v2 | Không đạt | Tái tạo có truy vết từ output |
| Regression test động | Đạt: 34/34 test pass trong WSL | Giữ làm gate bắt buộc trước mỗi run mới |

## 2. Những gì đã kiểm chứng

### 2.1. Toàn vẹn dữ liệu và output

Đã đối chiếu trực tiếp sáu CSV trong `data/processed/benchmark/` với `data/processed/evaluation/run_manifest.json`.

| Tập | Số dòng | UTF-8 BOM | SHA-256 khớp manifest |
| --- | ---: | :---: | :---: |
| Data 01 | 1.000 | Có | Có |
| Data 02 | 1.000 | Có | Có |
| Data 03 | 1.500 | Có | Có |
| Data 04 | 800 | Có | Có |
| Data 06 | 600 | Có | Có |
| Data 07 | 600 | Có | Có |

`baseline_predictions_unified.csv` có 13.000 dòng và SHA-256 `5cfef31abc8085522606869699b1f893c4afa83804ae3d7668802072c44d793f`, đúng bằng manifest. `baseline_raw_responses.jsonl` có 13.000 dòng và SHA-256 `6ec6c372c4bc1624af058234d85d6b128b536035eacd34fd08dee6288791563b`, cũng đúng bằng manifest. Phân bố lời gọi là 5.900 Libpostal và 7.100 VietnamAdminUnits; raw log không ghi exception.

### 2.2. Hợp đồng dữ liệu quan trọng

| Tập | Kết quả kiểm chứng tĩnh |
| --- | --- |
| Data 01 | 1.000 địa chỉ hệ mới; `QuanHuyen` rỗng; các trường bề mặt yêu cầu đầy đủ. |
| Data 02 | 1.000 địa chỉ nhiễu **tổng hợp có kiểm soát**, 500 `cu` và 500 `moi`; ground truth `GT_*` đầy đủ. Không phải tập hóa đơn thật. |
| Data 03 | 1.500 địa chỉ hệ cũ, không trùng `ChuoiDiaChi`, đủ năm trường `SoNha`, `TenDuong`, `PhuongXa`, `QuanHuyen`, `TinhThanh`. |
| Data 04 | 800 dòng, 400 `cu` và 400 `moi`; chỉ xóa theo `KieuThieu`; mọi `GT_*` có mặt. Đây là đúng hợp đồng “bắt đầu từ địa chỉ sạch, rồi xóa có kiểm soát”. |
| Data 06 | 600 chuỗi `Lai`, không trùng; phân bố C1/C2/C3 là 420/120/60. Định nghĩa đúng nêu ở Mục 4.1. |
| Data 07 | 600 cặp quan sát trực tiếp từ OSM diff và bảng chuẩn; chỉ có 356 `M-N` và 244 `N-1`. Baseline chỉ chạy chuyển đổi cũ → mới, chấm `PhuongXa` và `TinhThanh`. |

Với snapshot OSM cũ đầy đủ, `osm_old_snapshot_full.csv` có 26.961 bản ghi gồm 15.749 node và 11.212 way. Có 6.008/15.749 node đủ năm trường. Script hiện dùng `pyosmium` quét full-history và chia tại `CUTOFF_TIME=2025-06-30T23:59:59Z`; tài liệu không nên gọi đây là lệnh CLI `osmium time-filter` nếu lệnh đó không thực sự được chạy/lưu artifact.

### 2.3. Kiểm chứng động trong WSL

Đã chạy đúng lệnh quy định trong môi trường WSL:

```bash
cd /mnt/d/DACN
source ~/.venv_dacn/bin/activate
python -m unittest discover -s tests -v
```

Kết quả: **34/34 test pass trong 1,064 giây**. Bộ test bao phủ hợp đồng Data 02/03/04/06, tính tái lập generator, alias/audit OSM, quy tắc không suy diễn split/M-N, scoring, schema 9 cột, Libpostal binding thật, VietnamAdminUnits mode 2025 và sinh Markdown report. Kết quả này xác nhận các kiểm tra regression hiện hữu; các test mới đề xuất ở Mục 5 vẫn cần được bổ sung khi sửa versioning, scenario Data 07 và generator case study.

## 3. Phát hiện bắt buộc sửa

### P0 — Chặn phát hành tài liệu v2

#### P0-01. Định nghĩa Data 06 bị sai ở ba tài liệu

`src/data/synthetic/hybrid_address.py` là nguồn thực thi của hợp đồng Data 06. Tại các dòng 80–91, generator tạo:

| Kiểu | Định nghĩa đúng theo generator và CSV | Số dòng |
| --- | --- | ---: |
| C1 | `PhuongXa=moi`, `QuanHuyen=cu`, `TinhThanh=cu` | 420 |
| C2 | `PhuongXa=moi`, `QuanHuyen=cu`, `TinhThanh=moi` | 120 |
| C3 | `PhuongXa=cu`, `QuanHuyen=cu`, `TinhThanh=moi` | 60 |

Ngược lại, `baseline_ambiguity_evidence_v2.md` (dòng 149–151), `data_preparation_summary_v2.md` (139–141) và `chapter_01_research_motivation_v2.md` (74–76) mô tả C1 là “phường cũ + tỉnh mới, không quận” và C3 là “phường mới + tỉnh cũ, không quận”. Cả hai đều sai và trái với chuỗi đầu vào thực tế, vốn luôn chứa `QuanHuyen` ở ba kiểu hiện tại. Lỗi này làm các diễn giải về “khuyết quận”, nguyên nhân thất bại và động lực nghiên cứu không còn hợp lệ.

**Cách sửa:** cập nhật ba tài liệu từ CSV hoặc từ hằng số dùng chung; thêm test đọc `KieuLai` và kiểm tra `Span_He_Detail`/trường bề mặt của từng kiểu. Không tự viết lại diễn giải bằng tay.

#### P0-02. Case study v2 không truy vết được về output đã đóng băng

Đối chiếu 26 dòng case trong `docs/baseline_ambiguity_evidence_v2.md` với `baseline_predictions_unified.csv` theo ID và `DiaChiGoc` cho kết quả:

- 23/26 ID có mặt trong output, nhưng chỉ **9/26** dòng có input trùng chính xác.
- 17/26 dòng có ID nhưng input/tình huống/prediction đã được thay bằng chuỗi khác.
- 3/26 ID Data 02 không tồn tại vì quy ước output là `D02_N00005_clean` hoặc `D02_N00005_noisy`, trong khi bảng case dùng tên/hoa thường khác.

Ví dụ đủ để tái lập sai lệch:

| ID trong tài liệu | Input ghi trong tài liệu | Input thực trong output đã đóng băng |
| --- | --- | --- |
| `D01_0001` | `48, Phố Nguyễn Huệ, ... Bình Phước` | `19, Đường Hai Bà Trưng, Phường Võ Cường, Tỉnh Bắc Ninh` |
| `D03_0000` | `NT02-29, Đường Ven Hồ, ... Tây Hồ` | `NT02-29, Ngọc Trai 2, Đa Tốn, Gia Lâm, Hà Nội` |
| `D04_0055` | `15, Đường Giải Phóng, ...` | `213, Phố Trần Quốc Hoàn, Quận Cầu Giấy, Hà Nội` |
| `D06_0000` | `12, Đường Nguyễn Huệ, Phường Bến Nghé, ...` | `6, Ngõ 42 Phố Trần Bình Trọng, Phường Phương Liễu, Thị xã Quế Võ, Bắc Ninh` |

**Cách sửa:** viết script sinh case table chỉ từ `baseline_predictions_unified.csv` và raw log, nối bằng khóa `(ID, CongCu)`, rồi render Markdown. Mỗi hàng phải lưu ít nhất `ID`, tool, input, JSON prediction, JSON ground truth, `DungSai`, `LoaiLoi`, scenario và liên kết tới raw log. Cấm dùng ví dụ minh họa tự viết trong bảng mang nhãn “ca thực tế”.

### P1 — Sửa trước lần chạy baseline v2

#### P1-01. Runner có thể ghi đè kết quả đã đóng băng

`scripts/06_run_baseline_full.py` dùng cố định `run_manifest.json`, `baseline_predictions_unified.csv` và `baseline_raw_responses.jsonl` (dòng 32–34), tạo manifest mới ở dòng 40 và ghi đè manifest ở dòng 278. `scripts/05_run_baseline_pilot.py` gọi cùng runner, nên pilot cũng thay manifest chính dù output pilot có tên khác. `scripts/07_generate_baseline_report.py` lại luôn ghi `docs/baseline_evaluation_report.md`.

**Cách sửa:** thêm `run_id` bắt buộc, ví dụ `baseline_v2_20260920`, và đặt toàn bộ manifest/predictions/raw/report vào `data/processed/evaluation/runs/<run_id>/` và `docs/runs/<run_id>/`. Chỉ cho phép ghi một run đã tồn tại khi truyền cờ explicit `--overwrite-run`; mặc định phải lỗi. `VERSIONING.md` cần bao phủ cả report sinh tự động và dashboard, không chỉ báo cáo so sánh.

#### P1-02. Scenario Data 07 gán sai cho quan hệ N-1

Data 07 thực hiện một chiều cũ → mới ở `scripts/06_run_baseline_full.py` dòng 255–260. Tuy nhiên dòng 253 gán `N-1` thành scenario `B`, vốn được định nghĩa là chiều mới → cũ. Đây là lỗi taxonomy: 244 mẫu `N-1` hiện bị nhãn scenario sai dù không làm thay đổi số exact match.

**Cách sửa:** đặt scenario `A` cho toàn bộ Data 07 của run hiện tại; giữ `QuanHe` là biến phân tầng riêng. Khi có benchmark chiều mới → cũ thực sự, hãy tạo output/task riêng mới được gán scenario `B`.

#### P1-03. Metric aggregate có tên chưa phân biệt micro và macro

`src/evaluation/reporter.py` dòng 31–48 tính micro F1 trên các trường được chấm. Bảng `cross_dataset_summary.csv` lại dùng cột `avg_f1`, là trung bình F1 theo trường. Hai chỉ số đều hợp lệ nhưng không cùng nghĩa. Nếu báo cáo chỉ ghi “F1” hoặc “F1 trung bình”, người đọc có thể so sánh sai.

**Cách sửa:** ghi rõ `micro_f1_scored_fields` và `macro_mean_field_f1`; định nghĩa mẫu số, tập trường được chấm và cách đếm mismatch thành FP+FN tại ngay bảng. Chương 2 chỉ dùng công thức phù hợp với từng con số trích dẫn.

#### P1-04. Kết luận nguyên nhân vượt quá bằng chứng log

Raw log có raw response, thời gian và status, nhưng không ghi trạng thái geocoder/fallback hoặc trace nhánh xử lý. Do đó câu “12 lỗi này trực tiếp do `isDefaultNewWard`” trong tài liệu v2 chưa là bằng chứng theo từng record. Nó chỉ là giả thuyết phù hợp với code path và kết quả quan sát.

**Cách sửa:** hoặc đổi thành “phù hợp với giả thuyết fallback; cần trace để xác nhận”, hoặc bổ sung trường audit như `geocoder_attempted`, `geocoder_status`, `fallback_used`, `selected_candidate` trước run v2. Không dùng các khẳng định tuyệt đối như “ngăn chặn hoàn toàn” hay “triệt tiêu hoàn toàn”.

#### P1-05. Diễn giải task/dữ liệu sai hoặc quá rộng

- Data 02 phải được gọi là **nhiễu tổng hợp hiệu chuẩn từ profile VQA**, không phải “nhiễu thực tế” hay bằng chứng trực tiếp về hóa đơn thật.
- Data 07 là **cặp cũ/mới có quan sát trực tiếp và benchmark conversion cũ → mới**, không phải benchmark hai chiều. Không có 1-1, 1-N hay phép đo mới → cũ trong output hiện tại.
- Mốc 13.000 là **lượt dự đoán**, trên 5.500 dòng benchmark, không phải 13.000 “mẫu độc lập”.
- `docs/report_materials_index_v2.md` không được tuyên bố “hoàn tất 100% mục tiêu”: Data 05, T0 đủ 11 nhãn, T1 tự động, new→old và T3 vẫn chưa hiện thực, đúng như `docs/data_quality.md` và báo cáo v1 đã nêu.

#### P1-06. Chương khoa học không có trích dẫn kiểm chứng được

`chapter_01_research_motivation_v2.md` và `chapter_02_theoretical_foundation_v2.md` không có danh mục tham khảo, DOI, URL nguồn chính thức hoặc khóa trích dẫn. Các khẳng định pháp lý, kiến trúc Libpostal, số lượng đơn vị hành chính, công bố học thuật và research gap phải có nguồn sơ cấp/học thuật. Chỉ sau đó mới dùng số baseline đã truy vết để lập luận động lực nghiên cứu.

### P2 — Nâng chất lượng và kiểm soát lâu dài

1. `LoaiLoi` trong scorer chỉ giữ một nguyên nhân ưu tiên; case phức hợp cần thêm `error_tags` nhiều nhãn nếu muốn phân tích căn nguyên.
2. Dashboard tạo record Libpostal `UNSUPPORTED` cho Data 07. Giao diện phải hiển thị đây là placeholder trình bày, không phải output gọi tool.
3. Dashboard đang chứa số liệu tóm tắt hard-code; đưa số liệu vào build step đọc manifest/tables để tránh dashboard cũ sau run v2.
4. Adapter Libpostal có heuristic gán `city` vào `QuanHuyen` khi thiếu `state_district`; regex số nhà của VietnamAdminUnits bỏ mã bắt đầu bằng chữ. Hai sửa đổi này là thay đổi adapter, phải chạy một baseline mới và không được thay thế v1.
5. Thêm test tái lập case table và test runner không ghi đè run đã đóng băng.

## 4. Ngôn ngữ đã hiệu chỉnh để dùng trong tài liệu mới

### 4.1. Mô tả Data 06

> Data 06 gồm 600 địa chỉ lai được sinh có seed cố định từ địa chỉ hệ cũ có đúng một đích hành chính đã xác minh. C1 gồm phường/xã mới, quận/huyện cũ và tỉnh/thành cũ (420 mẫu); C2 gồm phường/xã mới, quận/huyện cũ và tỉnh/thành mới (120 mẫu); C3 gồm phường/xã cũ, quận/huyện cũ và tỉnh/thành mới (60 mẫu). Các quan hệ 1-N và M-N không được suy diễn từ snapshot khi thiếu bằng chứng địa lý.

### 4.2. Mô tả Data 07

> Data 07 gồm 600 cặp địa chỉ cũ/mới quan sát được từ OSM history và đối chiếu với bảng hành chính chuẩn. Baseline hiện chỉ đánh giá VietnamAdminUnits ở chiều cũ → mới, chấm hai trường phường/xã và tỉnh/thành. Tập có 244 quan hệ N-1 và 356 quan hệ M-N; không có phép đo chiều mới → cũ và không bao phủ quan hệ 1-1 hoặc 1-N.

### 4.3. Mô tả Data 02 và cỡ mẫu

> Data 02 là tập nhiễu tổng hợp có ground truth, hiệu chuẩn bằng profile nhiễu rút ra từ hóa đơn VQA đã lọc. Kết quả phản ánh độ bền trên phép biến đổi tổng hợp, không đại diện trực tiếp cho hiệu năng trên hóa đơn thật. Lần chạy hiện có 5.500 dòng benchmark và 13.000 lượt dự đoán do protocol chạy nhiều công cụ/chế độ trên một số tập.

## 5. Kế hoạch sửa theo thứ tự

### Bước 1 — Bảo toàn run v1 và tạo nhánh artifact cho v2

1. Không chạy `05_run_baseline_pilot.py` hoặc `06_run_baseline_full.py` bản hiện tại.
2. Lưu run v1 vào thư mục immutable/hoặc ghi rõ run ID trong manifest hiện hữu trước khi đổi code.
3. Thiết kế CLI có `--run-id` và output path theo run; pilot phải có manifest độc lập.
4. Bổ sung kiểm tra từ chối ghi đè và test cho hành vi này.

**Điều kiện đạt:** chạy pilot v2 không sửa một byte nào trong hash của v1.

### Bước 2 — Sửa protocol và observability

1. Gán scenario `A` cho Data 07 cũ → mới, giữ `QuanHe` để báo cáo N-1/M-N.
2. Đổi tên metric trong schema/table/report, ghi tập trường được chấm cho từng data.
3. Bổ sung trace converter/geocoder/fallback vào raw log hoặc hạ mức kết luận nguyên nhân.
4. Gắn version/hash của adapter, mapping và dashboard build vào manifest run.

**Điều kiện đạt:** mỗi assertion nguyên nhân trong báo cáo có ID/raw trace hoặc được ghi rõ là giả thuyết kỹ thuật.

### Bước 3 — Tạo lại toàn bộ tài liệu v2 từ nguồn máy đọc được

1. Viết generator cho bảng case, dùng selection rule công khai (ví dụ: top error theo dataset/error tag, seed cố định) và join chính xác `(ID, CongCu)`.
2. Sinh lại bảng Data 06 từ CSV để không thể đảo C1/C2/C3.
3. Dùng các bảng dưới `comparative_analysis_tables/` làm nguồn định lượng; ghi tên file, run ID, metric và tử số/mẫu số cạnh mỗi bảng.
4. Sửa thuật ngữ Data 02, Data 07, 13.000 lượt dự đoán và mức độ suy luận causal.
5. Thay trạng thái “đóng băng/hoàn tất” của tài liệu v2 thành “draft được tái tạo từ run v1” cho tới khi review pass.

**Điều kiện đạt:** 100% dòng case có ID tồn tại, tool khớp, input khớp, prediction/truth khớp nguồn; script test tự động kiểm tra điều này.

### Bước 4 — Hoàn thiện Chương 1 và Chương 2 theo chuẩn báo cáo khoa học

1. Tách rõ bằng chứng thực nghiệm nội bộ, thông tin pháp lý và tổng quan học thuật.
2. Thêm citation key trong thân bài, bibliography cuối chương và liên kết tới nguồn sơ cấp/học thuật.
3. Mỗi số liệu baseline trỏ về run ID/table; mỗi claim về tool trỏ về mã nguồn/phiên bản hoặc tài liệu chính thức.
4. Nêu đúng phạm vi chưa đo: T0 11 nhãn, T1 tự động, Data 05, B/new→old, T3 và độ phủ vùng/quan hệ.

**Điều kiện đạt:** người phản biện có thể lần theo mọi claim định lượng, pháp lý và kỹ thuật mà không dựa vào suy đoán.

### Bước 5 — Regression và run v2 có kiểm soát

Trong WSL:

```bash
cd /mnt/d/DACN
source ~/.venv_dacn/bin/activate
python -m unittest discover -s tests -v
python -m scripts.05_run_baseline_pilot --run-id baseline_v2_pilot
python -m scripts.06_run_baseline_full --run-id baseline_v2
python -m scripts.07_generate_baseline_report --run-id baseline_v2
```

Sau đó kiểm tra: hash benchmark không đổi; manifest/output cùng run ID; số dòng/raw log đúng protocol; không có duplicate key; Data 03/04 contract còn đúng; dashboard/table/case đều đọc cùng run ID. Chỉ khi đó mới so sánh v1 và v2. Nếu adapter thay đổi, gọi đây là **baseline v2**, không thay thế số v1.

## 6. Tiêu chí ký duyệt cuối cùng

Có thể ký duyệt bộ báo cáo khi tất cả điều kiện sau cùng đúng:

- Mỗi output có run ID, manifest bất biến và SHA-256 đã xác minh.
- Data 03 sạch đủ năm trường; Data 04 xóa có kiểm soát, `GT_*` nguyên vẹn.
- Định nghĩa C1/C2/C3 được lấy từ generator/CSV và có test.
- Mọi case “thực tế” được sinh từ output, không có ví dụ thủ công trộn vào bằng chứng.
- Data 07 được mô tả là old→new và giới hạn N-1/M-N; scenario không đảo chiều.
- Chỉ số micro/macro, mẫu số và scored fields được gọi đúng tên.
- Chương 1/2 có nguồn trích dẫn kiểm chứng được và nêu giới hạn còn lại.
- Regression test, pilot và full run v2 đều pass trong WSL.

## 7. Phán quyết

**Giữ baseline v1 làm mốc tái lập được về dữ liệu/output; không phát hành hoặc nộp tài liệu v2 hiện tại.** Ưu tiên là tái tạo tài liệu từ run v1 và sửa cơ chế versioning/protocol. Sau khi các gate ở Mục 6 đạt, chạy baseline v2 trong artifact riêng để có một báo cáo khoa học có thể truy vết từ claim đến từng dòng output.
