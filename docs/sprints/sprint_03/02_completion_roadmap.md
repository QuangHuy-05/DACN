# Lộ trình hoàn tất Sprint 3: từ guideline đến kết quả mô hình

**Lập ngày:** 25/09/2026. **Trạng thái đầu vào:** kiểm toán `baseline_v3_fuzzy` đã `PASS` trong phạm vi 5 trường; `baseline_v2` frozen; ma trận gồm **5 baseline mới + 1 mô hình đề xuất** đã chốt. [Guideline T0](span_11_annotation_guideline.md) và [batch ứng viên 01](span_annotation_inventory.md) đã có, gồm 68 pilot, 100 benchmark test giữ riêng và 20 VQA external hold. **Chưa có span gold 11 nhãn, Label Studio instance, gazetteer đa phiên bản hoàn chỉnh hoặc run mô hình mới.**

## 1. Đích Sprint 3 và thứ tự phụ thuộc

Sprint 3 được coi là hoàn tất khi có: corpus gold T0/T1 có provenance và split không rò rỉ; tập mốc thật và VQA được nghiệm thu theo phạm vi công bố; gazetteer có mã và hiệu lực thời gian từ nguồn xác minh; năm baseline mới chạy theo [ma trận mô hình](model_matrix.md); mô hình đề xuất và ablation; báo cáo đối đầu trên cùng test, cùng quyền truy cập đầu vào, kèm manifest/hashes. Không gọi cấu hình chỉ hỗ trợ một phần nhãn là baseline 11 nhãn đầy đủ.

```text
Label Studio → pilot 68 → sửa/khóa guideline ─┐
Nguồn mốc thật + rà soát VQA ────────────────┼→ corpus gold + split khóa → CRF/Deepparse FT/PhoBERT-CRF → Proposed → đánh giá cuối
Gazetteer có mã và thời gian ─────────────────┼→ HEUR-JW và ràng buộc hành chính ────────────┘
Môi trường + giao diện run/scorer ────────────┘
```

`DP-ZS-FT` và khung adapter/scorer có thể viết trước gold; kết quả T0 cuối cùng vẫn chờ test gold. `DP-FT-FT`, `CRF-INDEP`, `PHOBERT-CRF` và `PROPOSED-DYN` không được train bằng 100 mẫu benchmark test.

## 2. Các gói công việc theo thứ tự

### S3-01 — Dựng Label Studio và nghiệm thu pilot

**Làm:** tạo project với [`configs/label_studio_span11.xml`](../../../configs/label_studio_span11.xml); import **chỉ** [`label_studio_pilot_import.json`](../../../data/interim/annotation/sprint03/label_studio_pilot_import.json). Người gán thấy chuỗi nguyên bản và `sample_id`, không thấy `GT_*`, `HeQuyChieu`, `KieuThieu`, `Span_He_Detail` hay nhãn ứng viên. Gán cả nhãn span, hệ từng span; T1 toàn câu chỉ khi đủ bằng chứng. Xuất JSON của từng vòng pilot, lưu phiên bản cấu hình và danh sách ca cần quyết định. Xây bộ chuyển export thành gold canonical `(sample_id, text, spans[{start,end,label,system}], address_system, source_group)` và QA offset/nhãn/overlap.

**Nghiệm thu:** 68/68 mẫu pilot có trạng thái rõ; mọi span thỏa `text[start:end]`, không chồng lấp, nằm trong 11 nhãn và có thuộc tính hệ. Ca `O` vì OCR hỏng, `Khac`, mốc/hướng và “nay là” được rà soát; guideline được version hóa rồi **khóa trước khi mở test**. Ghi tốc độ gán thực đo để ước lượng phần corpus còn lại. Nếu có người thứ hai gán độc lập trên cùng một tập, đo Cohen's Kappa mức token và exact-span F1; nếu chỉ một người, ghi `NOT_MEASURED` cho inter-annotator agreement, không gọi lần gán lặp của một người là Kappa giữa người gán.

**Đầu ra:** project/config version, pilot export, gold pilot đã duyệt, sổ quyết định ca khó, báo cáo QA và đồng thuận (hoặc `NOT_MEASURED`).

### S3-02 — Bổ sung mẫu thật, xử lý VQA và Data 05

**Làm:** lập sổ nguồn mới với URL/ID, thời điểm truy cập, giấy phép, phạm vi sử dụng, loại địa chỉ, ID tài liệu/đối tượng gốc. Ưu tiên nguồn công khai có thể kiểm chứng, không lấy địa chỉ khách hàng cá nhân. Thu các câu chứa mốc và hướng đi **thật**; tách văn bản nguồn khỏi biến thể tổng hợp, không gán synthetic thành observed. Đề cương đặt mục tiêu khoảng 500 địa chỉ mốc; báo số ứng viên, số được duyệt và lý do loại, không bù mẫu bằng suy đoán. Với VQA, kiểm từng chuỗi về PII/quyền dùng; tìm ID hóa đơn trong raw Parquet nếu schema cho phép, vì CSV trung gian chỉ có `ChuoiDiaChi`. Nếu không truy được ID tài liệu đáng tin, giữ VQA làm external hold và báo hạn chế đó.

**Nghiệm thu:** có đủ mẫu thật đã kiểm nguồn để nhãn `MocDinhVi` và `HuongDi` xuất hiện trong train/dev/test; support mỗi nhãn được công bố. Không báo F1 của nhãn hiếm như một kết luận vững khi test chỉ có vài span. Data 05 chỉ được gọi là hoàn thành với số lượng thực đạt và provenance từng mẫu; VQA không đi vào train khi chưa qua cổng riêng tư và nhóm nguồn.

**Đầu ra:** source register, tập ứng viên Data 05, nhật ký duyệt/loại, VQA clearance log và bản chọn mẫu mới có `group_id`.

### S3-03 — Đóng gói gazetteer đa phiên bản

**Làm:** kiểm nguồn mã đơn vị cũ/mới; bảng hiện tại có `Mã phường/xã mới` nhưng không mặc định có mã chuẩn cho mọi đơn vị cũ. Thiết kế bản ghi tối thiểu `entity_id`, `level`, `system`, `canonical_name`, `aliases`, `parent_id`, `valid_from`, `valid_to`, `source_id`, `source_hash`, `status`; cạnh chuyển hệ giữ khóa cũ đầy đủ tỉnh–huyện–xã, mã đích và loại quan hệ 1-1/1-N/N-1/M-N. Mốc hiệu lực 01/07/2025 được thể hiện rõ trong phiên bản, không suy từ tên bề mặt. Alias chỉ lấy từ lớp đã audit; không tự tạo cạnh hành chính. Tọa độ/hình học chỉ ghi khi có bằng chứng nguồn.

**Nghiệm thu:** một lookup theo tên + cấp + ngày tham chiếu trả ID/ứng viên và bằng chứng; quan hệ nhiều đích không bị ép thành một đích; mã thiếu được đánh dấu `unverified`, không tự chế. Gazetteer có version/hash, báo cáo số đơn vị, alias, cạnh và các lỗ hổng ID. Đủ dùng cho `HEUR-JW` và ràng buộc giải mã; phần không có mã được từ chối có ghi lý do.

**Đầu ra:** schema, gói dữ liệu phiên bản, script build/lookup, source manifest và báo cáo coverage.

### S3-04 — Xây corpus gold và khóa split

**Làm:** từ các nguồn ngoài benchmark, lấy train/dev theo nhóm địa chỉ gốc; sinh biến thể nhiễu/thiếu/lai **chỉ từ nhóm thuộc train/dev tương ứng**, không lấy 100 test làm seed. Gán và nghiệm thu span trên chuỗi nguyên bản; T1 toàn chuỗi và thuộc tính hệ từng span dùng cùng guideline. Sau khi guideline khóa, gán 100 mẫu benchmark đã giữ; 20 VQA là external test riêng sau clearance; bổ sung test mốc/hướng thật từ nguồn độc lập. Khóa nhóm bằng source ID khi có, và bằng khóa site bảo thủ khi không có; rà soát thủ công va chạm mờ giữa nguồn.

**Nghiệm thu:** train/dev/test không giao `group_id` và không có chuỗi gần trùng vượt ngưỡng duyệt thủ công; mọi sample có nguồn và annotation version; mọi split có SHA-256 và thống kê số mẫu/span theo nhãn, nguồn, hệ cũ/mới/lai, nhiễu, thiếu trường. Test không được dùng chọn threshold, checkpoint, alias hay sửa guideline sau khi đã mở kết quả mô hình.

**Đầu ra:** gold canonical, split manifest, báo cáo phân bố/QA, danh sách nhóm bị loại hoặc gộp; 100 test benchmark frozen được đánh giá đúng phạm vi T0.

### S3-05 — Môi trường và hạ tầng thực nghiệm chung

**Làm:** xử lý khả năng chạy WSL/GPU trước huấn luyện; ghi Python, package, checkpoint, bộ tách từ, tài nguyên RAM/VRAM, dung lượng tải. Không dùng `.venv` Windows như runtime WSL; không cài dependency mới trước khi quyền cài được chốt theo `AGENTS.md`. Tạo adapter nhận **chỉ chuỗi địa chỉ**, xuất `sample_id`, spans, 5 trường khi hỗ trợ, T1 khi hỗ trợ, status/abstain, latency và trace. Tạo scorer T0 exact span, 5 trường, T1 và báo cáo subset coverage; tách Data 07/T2. Mỗi run lưu input/split/gazetteer/checkpoint/code hash, seed và package versions.

**Nghiệm thu:** cùng một gold và split được nạp bởi mọi cấu hình; offset sau tokenizer/decoder quay về đúng chuỗi gốc; mọi run dùng ID mới, không ghi đè v2/v3. Nếu WSL bị từ chối, ghi nguyên nhân và môi trường thay thế được kiểm soát trước khi công bố run, không lặng lẽ đổi runtime.

**Đầu ra:** environment lock, runner/adapter/scorer contract, run manifest template, báo cáo alignment và tài nguyên.

### S3-06 — Năm baseline mới

| Thứ tự | Cấu hình | Việc chính | Điều kiện công bố |
| ---: | --- | --- | --- |
| 1 | `DP-ZS-FT` | Khóa model pretrained; lưu raw tags; ánh xạ native→schema trên pilot theo rule cố định | Chỉ báo 5 trường hoặc T0 supported subset, cùng coverage; không gọi đủ 11 nhãn |
| 2 | `HEUR-JW` | Candidate từ gazetteer theo ngày; Jaro-Winkler rank; threshold/reject trên dev | Báo coverage, precision khi accepted, lỗi chọn sai mã và latency |
| 3 | `CRF-INDEP` | BIO 23 trạng thái, token/feature thủ công, seed/regularization khóa | Gold alignment đạt, T0 per-label và 5 trường từ span |
| 4 | `DP-FT-FT` | Fine-tune Deepparse FastText custom tags; kiểm word↔char alignment và log mẫu bị loại | Chỉ báo T0 toàn nhãn nếu offset và mapping đầy đủ, cùng split đã khóa |
| 5 | `PHOBERT-CRF` | Word segmentation, subword alignment, PhoBERT encoder + CRF | Không tính loss trên special/padding; round-trip offset đạt |

Có thể song song hóa `DP-ZS-FT` và `HEUR-JW` với công việc dữ liệu; ba baseline supervised chỉ chạy sau S3-04. `baseline_v3_fuzzy` là mốc lịch sử **5 trường**, không thay `HEUR-JW`; `baseline_v2` giữ frozen. Mỗi cấu hình cần run pilot interface, sau đó full run trên cùng split; mọi ngoại lệ và từ chối vẫn ở mẫu số báo cáo.

### S3-07 — Mô hình đề xuất nhận biết cấu trúc động

**Làm:** train `PROPOSED-DYN` với PhoBERT encoder, đầu T0 span và đầu T1 `cu/moi/Lai`; `khong_ro` là trạng thái từ chối khi inference. Decoder chỉ cấm `QuanHuyen` nếu hệ mới được xác nhận với ngưỡng đã chọn trên dev; khi `Lai`/không chắc, giữ giả thuyết hoặc abstain. Tạo ablation cùng encoder, seed, split và ngân sách tune nhưng **không** có ràng buộc cấu trúc. Không cấp `HeQuyChieu` gold cho inference.

**Nghiệm thu:** báo T0 từng nhãn, T1 confusion/macro F1/abstain, false-positive rate `QuanHuyen` trên gold `moi` có mẫu số, recall `QuanHuyen` trên `cu`/`Lai`, exact 5 trường và latency. Đối chiếu với ablation để quy lợi ích cho module động. Không tuyên bố “0 ảo giác tuyệt đối” nếu chỉ một slice đạt 0; con số 77,5% lịch sử phải dẫn đúng run và mẫu số trước khi so.

**Đầu ra:** checkpoint/head/decoder hash, config, ablation run, trace ca lỗi cấu trúc và báo cáo hiệu quả.

### S3-08 — Đánh giá đối đầu và bàn giao

**Làm:** chấm tất cả cấu hình trên cùng test hash và input mode; trình bày riêng track 5 trường, T0, T1 và Data 07/T2 nếu có. Báo micro/macro/per-label P/R/F1 với support, precision/coverage khi abstain, latency, độ bền theo nhiễu, thiếu trường, cũ/mới/lai, mốc/hướng; phân tích lỗi không nhận diện span, sai cấp, sai thời gian, ảo giác Quận. Lưu prediction thô, manifest, metric JSON và báo cáo tiếng Việt; không gộp unsupported label vào “đúng” hay so model trên test khác nhau.

**Nghiệm thu:** bảng đối đầu có 5 baseline + proposed + ablation và mốc v3 ở track tương thích; mọi con số truy về run, dữ liệu, code, model và gazetteer hash. Những phần chưa đạt do thiếu nguồn hoặc môi trường được ghi `BLOCKED/NOT_MEASURED` với bằng chứng, không đổi tên thành kết quả hoàn tất.

## 3. Ưu tiên thực hiện và các cổng quyết định

| Cổng | Việc phải đạt trước khi đi tiếp | Rủi ro nếu bỏ qua |
| --- | --- | --- |
| **G1: pilot** | 68 mẫu, QA offset, guideline khóa, tình trạng người gán thứ hai rõ | Gold thiếu nhất quán; Kappa/F1 agreement không có cơ sở |
| **G2: nguồn** | Mốc/hướng thật và VQA clearance, provenance/ID nhóm | F1 nhãn hiếm không đại diện, rò rỉ nguồn hoặc quyền dùng chưa rõ |
| **G3: corpus** | Train/dev/test gold, group disjoint, split/hash khóa | Kết quả mô hình bị rò rỉ hoặc không tái lập |
| **G4: môi trường/gazetteer** | Runtime chạy được; version/checkpoint/gazetteer hash và mã hiệu lực rõ | Baseline không công bằng hoặc heuristic dùng sai phiên bản hành chính |
| **G5: báo cáo** | Cùng test, đúng track, đầy đủ run manifest và mẫu số | Không thể kết luận mô hình đề xuất hơn baseline |

**Đường găng:** S3-01 → S3-04 → S3-06 supervised → S3-07 → S3-08. S3-02, S3-03 và phần chuẩn bị S3-05 chạy song song ngay từ đầu. Sau pilot mới ước lượng lịch theo tốc độ gán nhãn thực tế; hiện không nên hứa ngày hoàn tất chỉ từ số mẫu ứng viên.

## 4. Việc bắt đầu ngay

1. Dựng Label Studio và import **68 pilot**, chưa import 100 test hoặc 20 VQA.
2. Phân công người gán chính và người gán thứ hai cho một tập giao nhau; nếu không có người thứ hai, ghi trước rằng inter-annotator agreement sẽ `NOT_MEASURED`.
3. Mở đồng thời sổ nguồn thật cho `MocDinhVi`/`HuongDi`, rà soát VQA và kiểm mã gazetteer cũ/mới.
4. Chỉ sau cổng G1–G3 mới khởi chạy train supervised; adapter zero-shot, schema gazetteer và hạ tầng run có thể chuẩn bị sớm.
