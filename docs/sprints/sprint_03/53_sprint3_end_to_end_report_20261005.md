# Báo cáo tổng kết Sprint 3 — quy trình, kết quả và đề xuất Sprint 4

**Ngày chốt:** 05/10/2026  
**Trạng thái:** `SPRINT3_PARTIAL_DP_BLOCKED`  
**Phạm vi:** toàn bộ quy trình Sprint 3 từ kiểm toán baseline, xây dữ liệu T0, gazetteer và pipeline mô hình đến đánh giá cuối. Báo cáo này tổng hợp hồ sơ đã có; không mở lại nhãn, corpus, split, gazetteer hay các run đã khóa.

> **Cách đọc trạng thái:** Sprint 3 đã có corpus phát hành, các pipeline và đánh giá cuối cho HEUR-JW, CRF-INDEP, PhoBERT-CRF, PROPOSED-DYN và ablation. Hai cấu hình Deepparse `DP-ZS-FT` và `DP-FT-FT` chưa có thực nghiệm pretrained/native được nghiệm thu. Vì vậy Sprint 3 chưa được ghi là hoàn tất đầy đủ ma trận mô hình. Theo yêu cầu hiện tại, báo cáo ghi nhận điểm này và không tiếp tục xử lý điều kiện checkpoint.

## 1. Phân chia công việc Sprint 3 cho hai người

Bảng dưới đây **đề xuất phân chia toàn bộ các đầu việc đã triển khai trong Sprint 3 cho hai thành viên**, phục vụ quản lý, thuyết trình và bàn giao. Hồ sơ hiện có chưa đủ để quy toàn bộ code/thực nghiệm cho một người cụ thể; bảng không xác nhận đóng góp lịch sử. Việc kỹ thuật có hỗ trợ AI agent cũng phải được khai báo khi nhóm lập bảng đóng góp thực tế. Tạm dùng **A — dữ liệu và tài nguyên hành chính**, **B — mô hình và đánh giá**; tên và đóng góp thực tế cần nhóm xác nhận trước khi nộp.

| Người phụ trách | Phần việc Sprint 3 | Việc đã thực hiện và đầu ra cần bàn giao |
|---|---|---|
| **A — Dữ liệu và tài nguyên hành chính** | Guideline, Label Studio, truy nguyên nguồn, QA/adjudication, split/corpus release, gazetteer/verifier và coverage. | Raw export, quyết định duyệt, corpus/manifest, bảng xác minh mã và package gazetteer. Chủ dự án vẫn là người phê duyệt annotation/ngoại lệ. |
| **B — Mô hình và đánh giá** | Audit baseline, model matrix/protocol, alignment/BIO, HEUR-JW/CRF, tích hợp neural, Kaggle, freeze/scorer, phân tích lỗi và tái lập. | Config/selection lock, code/runner, checkpoint, prediction, metrics, audit và gói bàn giao. Chỉ những cấu hình có thực nghiệm thật được ghi là đã chạy. |

### 1.1 Danh mục giao việc chi tiết trong phạm vi Sprint 3

| Mã phần việc | A phụ trách | B phụ trách | Đầu ra và kết quả đã có | Điểm hai người cần kiểm tra chéo |
|---|---|---|---|---|
| S3-W01 — Mốc baseline và protocol | Đối chiếu nguồn benchmark, các trường chỉ dùng đánh giá, danh sách hold | Audit manifest/hash v2/v3; tách 5 trường/T0/T1; khóa model matrix | V3 fuzzy PASS ở phạm vi 5 trường; v2 giữ frozen; không biến metric lịch sử thành T0 | B xác minh quyền đọc metadata từng mode; A đối chiếu ID không được đưa vào train/tune |
| S3-W02 — Guideline và Label Studio | Soạn ví dụ ranh giới 11 nhãn, hệ span, `Khac/O`; quản lý lượt gán/duyệt | XML, converter, kiểm offset/overlap, xử lý nhiều annotation bằng lựa chọn explicit | 68 pilot, 232 batch, 100 test đã qua quy trình review/phát hành | A duyệt ý nghĩa nhãn; B chứng minh canonical xuất từ raw và quyết định, không vá JSON |
| S3-W03 — Prediction hỗ trợ 68/232 | Rà prediction, sửa và Submit, ghi ca mơ hồ | Luồng source-derived có trace thành phần/hệ; abstain khi offset không chắc | 300 mẫu phát triển, giữ ID/text; prediction chỉ là gợi ý | Hai người phân biệt metadata nguồn với bằng chứng trong text và với gold |
| S3-W04 — Split và corpus | Rà 138 cặp, ghi reason/reviewer; quyết định ngoại lệ | Group audit, kiểm normalized text/hash, publisher bất biến, coverage | Release2 240/60/100; mask dev543 và 16 test riêng T1 | Kiểm T0 vẫn đủ mẫu; T1 mẫu số đúng 206/53/64; không coi QA cấu trúc là human approval |
| S3-W05 — Gazetteer | Nguồn/cha/ngày/mã/alias, đối chiếu NSO, unresolved log | Build/lookup/verifier, schema/version/hash, giữ đa đích | 14.149 entity; 11.962 mã verified; 2.187 mã cũ unresolved | Không suy mã, interval pháp lý, alias/cạnh hoặc quyền tái phân phối |
| S3-W06 — Alignment/BIO | Đối chiếu literal span với guideline, kiểm corpus bất biến | Raw offset, BIO23, PhoBERT/VnCoreNLP mapping và tone relocation | Alignment thật 300/300 exact, giữ 1.341 span train/dev | Bằng chứng tokenizer thật tách khỏi fixture; không sửa gold để ép alignment |
| S3-W07 — Baseline nhẹ | Rà trace candidate/cấp hành chính và phạm vi hỗ trợ | HEUR sweep 6 ngưỡng; CRF grid 8 candidate; train/dev-only | Dev F1 88,01% / 90,56%; test 91,12% / 90,76% | Quy tắc inference text-only; tune chỉ dev; nhãn ngoài support vẫn FN |
| S3-W08 — Neural và cloud | Kiểm gói chỉ chứa dữ liệu được phép, cấu hình T1 mask | Preflight, smoke GPU, 4 full candidate run, save/reload, dev selection | PhoBERT-CRF và DYN chọn c02; DP chưa có run pretrained | COMPLETE của API không thay hash/checkpoint/report; không dùng smoke weights làm kết quả |
| S3-W09 — Đánh giá cuối và ablation | Kiểm release/gold/mask/support và danh sách exception | Global freeze, score riêng, recompute, paired on/off | 100 prediction/cấu hình; kết quả T0/T1/5 trường và ablation | Không chọn lại model từ test; on/off cùng checkpoint/calibration |
| S3-W10 — Nghiệm thu và báo cáo | Coverage/provenance/giới hạn nhãn, tổng hợp dữ liệu | Tests, protected hash, artifact/dung lượng, bàn giao code/config | 266 PASS + 8 SKIP; 2.352 hash được bảo toàn; receipt Git đã push | Không stage raw/gold/weights; báo cáo tiến độ không tự gọi đủ ma trận |

**Cách sử dụng phân công:** A cần trình bày được quy trình dữ liệu từ nguồn đến gold, B cần trình bày được từ gold đến model/prediction/metric. Hai người cùng hiểu mục 3 về kết quả và mục 5 về giới hạn; không chia báo cáo thành hai phần mà không kiểm tra giao diện giữa chúng. Đây không phải phân bổ thời gian theo tỷ lệ 50/50: chưa có time sheet để chứng minh số giờ của mỗi người.

**Ranh giới trách nhiệm:** A chuẩn bị hồ sơ nhãn/ngoại lệ để chủ dự án duyệt; B triển khai quy trình máy có thể tái lập và báo trạng thái theo evidence. Phân công này không tự chuyển quyền phê duyệt sang partner hay AI agent. Mô hình không tự biến prediction thành gold. Một nhiệm vụ chỉ được gọi hoàn tất khi có artifact, hash/manifest và cổng nghiệm thu tương ứng; “code đã có” hoặc “fixture test qua” không đồng nghĩa đã có thực nghiệm pretrained.

### 1.2 Đối chiếu với mục tiêu Sprint 3 ban đầu

| Mục tiêu ban đầu | Kết quả thực hiện | Mức hoàn thành/giới hạn |
|---|---|---|
| Bổ sung Deepparse zero-shot và fine-tuned FastText | Adapter/mapping/pipeline/resource gate và audit nguồn đã có | **Chưa có thực nghiệm pretrained/native**; không ghi hoàn tất hai baseline |
| PhoBERT-CRF và heuristic Jaro-Winkler | Huấn luyện/inference/đánh giá thật; có artifact | Đã có kết quả cuối trong protocol và coverage hiện tại |
| CRF độc lập được tách khỏi Deepparse | Linear-chain CRF, feature thủ công, train/dev search | Đã có kết quả T0; T1 không hiện thực |
| Fine-tune mô hình đề xuất và nhận biết cấu trúc 2/3 cấp | PhoBERT T0/T1 + giải mã động, paired ablation | Đã có thực nghiệm; **chưa chứng minh lợi ích constraint hoặc triệt tiêu lỗi Quận tổng quát**; ViBERT chưa thực nghiệm |
| Hoàn thiện dữ liệu bán thủ công | Corpus 400 mẫu đã phát hành; quyết định/QA có version/hash | Nhãn hiếm thiếu support; IAA chưa đo; test có hỗ trợ AI |
| Dữ liệu hóa đơn thật/mốc định vị | VQA phục vụ noise profile, luồng review/provenance có sẵn | VQA HOLD; Data 05 lấy mốc/hướng thật hoãn theo yêu cầu |
| Gazetteer đa phiên bản, mã chuẩn và thời gian | Lookup/verifier và hai snapshot chính thức đã tích hợp | Partial: mã cũ unresolved, interval pháp lý/redistribution chưa đủ; T2 chưa thực nghiệm |

Không có cơ sở đổi các mục thiếu thành hoàn tất chỉ vì đã chuyển sang viết báo cáo. Kết thúc Sprint 3 ở đây nghĩa là chốt **hồ sơ kết quả và tồn đọng**, với trạng thái `SPRINT3_PARTIAL_DP_BLOCKED`.

## 2. Mục tiêu và quy trình Sprint 3 từ đầu đến cuối

Sprint 3 đưa dự án từ baseline địa chỉ ở mức 5 trường sang quy trình có thể kiểm soát cho phân tích span T0 11 nhãn và phân loại hệ T1. Trình tự thực tế như sau.

### Nhật ký các mốc có bằng chứng

| Mốc hồ sơ | Nội dung và quyết định | Bằng chứng |
|---|---|---|
| 25/09/2026 | Audit v2/v3 và model matrix; xác định track 5 trường | Giao việc/audit ban đầu, [model matrix](model_matrix.md) |
| Giai đoạn chuẩn bị trước 01/10 | Guideline 11 nhãn, pilot 68, converter, batch 232 và hold 100; gazetteer v1/v2 | [Guideline](span_11_annotation_guideline.md), thao tác S3-01–03 |
| 01/10/2026 | Reannotation source-derived 68/232; prediction cho cả hai; 138 cặp được phân xử | Kế hoạch reannotation, hướng dẫn 68/232 |
| 02/10/2026 | QA/adjudication, phát hành train/dev 240/60 và exception543; baseline nhẹ; U1–U7 code | Train/dev completion, U1–U7 |
| 03/10/2026 | Tích hợp tokenizer thật; sửa 29 reject; xác minh NSO cũ/mới; baseline nhẹ v4/v2 | Alignment, gazetteer, baseline |
| 04/10/2026 | Theo yêu cầu, test chuyển assisted; Kaggle CLI/private pipeline; QA test round1/round2; gói local/Colab | [Test-assisted protocol](37_test100_ai_assisted_annotation.md), local completion |
| 05/10/2026 | Chủ dự án chốt annotation694/task695 và 16 mask; release2; GPU smoke/full runs; chọn c02 bằng dev | Release và GPU runs |
| 05/10/2026 — đánh giá cuối | Freeze rồi chấm; 5 model/variant có kết quả; 2 DP blocked; nghiệm thu và Git receipt | [Kết quả cuối](49_sprint3_final_results.md), [tái lập](50_sprint3_reproduction_and_handoff.md) |

Ngày ở bảng là ngày hồ sơ/mốc nghiệm thu; không phải suy đoán thời gian làm của từng thành viên. Những dòng “test pending/chưa training” trong báo cáo cũ phản ánh đúng thời điểm đó, không phải trạng thái hiện tại.

### 2.1 Kiểm toán điểm xuất phát và khóa cách so sánh

- Kiểm tra manifest/hash các lượt baseline cũ, giữ `baseline_v2` làm mốc frozen và xác nhận phạm vi của `baseline_v3_fuzzy`.
- Tách rõ track benchmark **5 trường** hiện có khỏi T0 **11 nhãn span** và T1 **hệ quy chiếu**. Metric 5 trường trước đây không được diễn giải thành kết quả T0/T1.
- Lập ma trận mô hình và protocol để mỗi lần chạy ghi rõ input, gold được phép đọc, split, adapter, ngưỡng, seed, hash resource/code và đầu ra.

### 2.2 Chốt schema và quy trình gán nhãn T0

- Chốt `s3-span-v1.1` với 11 nhãn: `SoNha`, `TenDuong`, `Ngo/Hem`, `ToaNha/CanHo`, `PhuongXa`, `QuanHuyen`, `TinhThanh`, `MocDinhVi`, `HuongDi`, `GhiChu`, `Khac`.
- Làm rõ ranh giới literal trên chuỗi gốc, dấu phân cách, cách tách span liền kề, `Khac` so với `O`, và thuộc tính hệ `cu/moi/khong_xac_dinh` ở từng span. Hệ của span và hệ toàn địa chỉ là hai trường quyết định khác nhau.
- Dựng giao diện Label Studio, thử pilot 68 mẫu, sửa quy trình import/export và converter để kiểm task thiếu/trùng, annotation được chọn, nhãn, thuộc tính, offset, substring và overlap. `READY_FOR_HUMAN_REVIEW` là trạng thái QA cấu trúc, không tự nó phê duyệt gold.
- Tạo batch 232 cho train/dev; chỉ dùng prediction như gợi ý khi người gán sửa và Submit. Prediction không phải đáp án chuẩn.

### 2.3 Kiểm soát nguồn, near-duplicate và phát hành train/dev

- Tạo group nguồn để ngăn địa chỉ cùng địa điểm/cùng nguồn rơi sang split khác nhau; lập hàng đợi rà 138 cặp gần giống và lưu quyết định, lý do, reviewer.
- Ghép 68 pilot đã duyệt và batch 232 theo phân bổ group-disjoint thành **240 train / 60 dev**; giữ manifest/hash và coverage.
- Ghi ngoại lệ task 543 (`s3_60931c369cbd85ef`): giữ annotation T0; loại riêng khỏi T1/diagnostic cấu trúc theo manifest do mâu thuẫn hệ. Không sửa raw export/gold để che ngoại lệ.
- Phát hành `corpus_train_dev_v2`, sau đó tích hợp vào `corpus_v1_release2` khi test được duyệt.

### 2.4 Gán và phát hành test100

- Ban đầu test được giữ riêng, không dùng để train/tune/chọn mapping/ngưỡng. Sau yêu cầu của chủ dự án, quy trình gán test chuyển thành AI-assisted rồi người dùng rà soát và duyệt; vì vậy cách gán được khai báo `AI_ASSISTED_HUMAN_REVIEW`, không phải blind annotation độc lập.
- QA vòng export, chọn annotation tương đương cho task trùng, làm rõ task có nhiều annotation và xử lý ngoại lệ T1. Giữ raw export bất biến; các quyết định được ghi riêng và gắn với release.
- Phát hành `corpus_v1_release2`: **240 train / 60 dev / 100 test**. Test có **446 span T0**; T1 có **64 eligible / 20 null / 16 excluded**. Mask chỉ tác động T1/diagnostic, không xóa T0.

### 2.5 Gazetteer và xác minh đơn vị hành chính

- Xây các gói gazetteer có phiên bản, alias audit, quan hệ cha-con, ngày snapshot và mã nguồn; bổ sung đối chiếu snapshot chính thức NSO cho hai mốc 30/06/2025 và 01/07/2025.
- Phát hành metadata `s3_v4_nso_dual_snapshot_release2`: **14.149 entity, 10.597 edge, 187 alias đã audit, 5 quan hệ phi nguyên tử**. Có **8.607 mã cũ và 3.355 mã mới verified**; **2.187 mã cũ còn unresolved**.
- Hai snapshot mô tả trạng thái ở hai ngày; không chứng minh toàn bộ khoảng hiệu lực pháp lý, không đủ căn cứ để suy hình học hay ép quan hệ 1-N/M-N thành một đích. Điều kiện tái phân phối một số CSV nguồn còn chưa được xác minh; không công bố package hạn chế ra ngoài.
- Hạng mục T2 ánh xạ hành chính chưa được chạy nghiệm thu như mô hình; gazetteer là tài nguyên/bằng chứng đầu vào, không phải kết quả T2.

### 2.6 Baseline, pipeline neural và đánh giá cuối

- Có alignment từ span ký tự sang tokenizer/BIO; kiểm tra alignment PhoBERT 300/300 mẫu train/dev trong giai đoạn chuẩn bị. Mẫu không căn chỉnh được không được âm thầm xóa hay dùng offset giả.
- Chạy HEUR-JW, CRF-INDEP trên dev; dựng pipeline PhoBERT-CRF và PROPOSED-DYN, chọn cấu hình bằng dev. Gói train/dev và notebook Kaggle tách riêng khỏi test.
- Xác nhận GPU Kaggle bằng smoke test, chạy full run trên train/dev, chọn checkpoint theo dev, tạo và khóa roster/prediction cho đánh giá cuối. Chỉ sau khi prediction của các cấu hình sẵn sàng đã được freeze mới đọc gold test.
- Thực hiện inference test cuối trên kernel Kaggle riêng, kiểm hash artifact, tái tính metric độc lập và audit các file corpus/run được bảo vệ. Không sử dụng test để điều chỉnh lại model sau khi thấy kết quả.

### 2.7 Luồng kỹ thuật được hiện thực như thế nào

```text
Benchmark/nguồn đã có + trace sinh dữ liệu
  → chọn 68 pilot + 232 train/dev + 100 hold, giữ ID/text
  → Label Studio: prediction candidate → người rà/sửa/Submit
  → raw export bất biến → QA cấu trúc → review nội dung → decision/approval
  → audit nhóm nguồn/gần trùng → corpus version/hash
  ├─ train 240 → raw offset/tokenization/BIO → train candidate
  ├─ dev 60 → inference text-only → freeze → scorer → chọn cấu hình/calibration
  └─ test input-only 100 + selection lock đã chốt
       → inference → global prediction freeze → scorer đọc gold riêng
       → T0/T1/structure/ablation + recompute + báo cáo
Gazetteer có version/hash → tài nguyên HEUR/constraint, không cấp gold cho inference
```

#### A. Dữ liệu có sẵn không đồng nghĩa đã có gold 11 span

Benchmark ban đầu có trường/metadata mô tả cách sinh, nhưng chưa bảo đảm biết offset literal của mọi thực thể trên chuỗi sau nhiễu, rút gọn hoặc pha hệ. Vì vậy sử dụng trace nguồn để tạo candidate cho 68/232, rồi con người kiểm chứng. Nếu trace không xác định được ranh giới duy nhất, pipeline abstain thay vì tìm một chuỗi gần giống và gọi đó là span đúng.

Ví dụ minh họa quy tắc, không phải bản ghi dùng làm kết quả: trong `12, đường A, phường B, quận C, Hà Nội`, số nhà và đường không có hệ hành chính tự thân nên thường là `khong_xac_dinh`; `quận C` thuộc hệ cũ. `Hà Nội` có cùng tên ở hai hệ không đủ chứng minh cũ/mới khi đứng riêng. Chuỗi có một quận không tự chứng minh tất cả span hành chính còn lại đều cũ; phải xét bằng chứng của từng thành phần.

Gold canonical lưu `sample_id`, `text`, `spans[{start,end,label,system}]`, `address_system`, `source_group`. Converter kiểm nhãn/thuộc tính, `[start,end)` nằm trong text, substring literal, overlap và task coverage. Human review kiểm ý nghĩa/cấp đơn vị/hệ; các cờ `unreadable_ocr`, `ambiguous_label`, `temporal_ambiguity`, `privacy_review` phục vụ rà soát, không phải nhãn thực thể thứ 12–15 và không mặc định làm annotation sai.

Các vòng sửa được thực hiện trên Label Studio rồi export mới. Phán quyết chọn annotation được lưu riêng; không sửa raw JSON rồi gọi bản đã vá là raw export của người gán. Mẫu có ngoại lệ không bị xóa khỏi T0 để cải thiện điểm.

#### B. Alignment dùng chung

Mô hình làm việc với token, gold định nghĩa bằng vị trí ký tự. Bộ alignment phải chuyển hai chiều mà không mất ranh giới: raw span → token/BIO → raw span. CRF dùng **23 trạng thái** (`O` + `B/I` cho 11 nhãn); preparation Deepparse có hợp đồng riêng gồm EOS, chưa phải training đã chạy. Dấu phân cách ngoài span giữ `O`; token cắt ngang span và câu vượt giới hạn phải có chính sách explicit, không silently truncate.

PhoBERT cần VnCoreNLP segmentation và BPE. Ban đầu chỉ **217/240 train + 54/60 dev** exact; 29 ca lỗi do dịch vị trí dấu như `hòa → hoà`, `ủy → uỷ`. Policy `phobert_raw_unit_pool_v2_tone_relocation` kiểm cùng chữ nền/chất lượng nguyên âm và cùng dấu thanh trong cụm nguyên âm, ghi mapping về interval grapheme gốc. Không dùng edit-distance để đoán. Kết quả tokenizer/segmenter thật sau sửa: **300/300 raw round-trip**, khôi phục **29/29** reject, giữ nguyên text/gold và mask543. Alignment PASS xác nhận biểu diễn được dữ liệu; không phải độ chính xác mô hình.

#### C. HEUR-JW và CRF độc lập

- **HEUR-JW:** tạo candidate từ gazetteer, chuẩn hóa bản dùng so sánh, xếp hạng Jaro-Winkler, kiểm cấp/cha/hệ/ngày/alias/tie. Raw span vẫn trên text gốc. Candidate thiếu chứng cứ hoặc đồng điểm trả reject/không xác định có trace. Phiên bản rule v4 dùng explicit dual snapshot; sweep ngưỡng **0,82/0,86/0,90/0,94/0,98/1,00**, margin **0,02**, chọn ngưỡng **0,86** bằng exact-span F1 dev (hòa chọn ngưỡng cao hơn).
- **CRF-INDEP:** linear-chain CRF với feature token/context/chữ-số/shape/prefix/segment cue từ text. Không dùng PhoBERT hoặc head T1. Grid **context1/2 × 4 cặp regularization**, tổng 8 candidate; chọn **context1, c1=0,1, c2=1**. Train chỉ 240 mẫu, chọn bằng 60 dev. Phiên bản feature `surface_admin_segment_cue_v2`; tokenizer/BIO/offset/projection giữ hợp đồng.
- **Phép chiếu 5 trường:** chuyển các span hỗ trợ sang số nhà/đường/phường/huyện/tỉnh theo policy cố định. Không thêm trường thiếu từ gold. 5 trường và T0 có đơn vị tính khác nhau nên không cộng hoặc so phần trăm như cùng metric.

So với mốc development trước đó, HEUR giữ F1 dev **88,01%**, 5 trường giảm **82,04 → 81,99%**; CRF tăng dev **89,82 → 90,56%** và 5 trường **85,41 → 85,59%**. Đây là thay đổi quan sát trên track phát triển, không phải bằng chứng thắng có ý nghĩa thống kê. Các run cũ vẫn frozen.

#### D. Huấn luyện neural thật và kiểm soát cloud

Pipeline PhoBERT-CRF dùng encoder pretrained và linear-chain CRF; DYN có T0/T1 và decoder theo confidence/constraint. Resource/code/corpus được pin; input inference chỉ text, T1 train/score đọc mask manifest. Kaggle private dataset không mặc định công khai gold/weights. Gói Colab đã chuẩn bị và kiểm cấu trúc; **training/inference thật trong đợt này chạy Kaggle**, không báo đã chạy Colab.

GPU smoke thật xác nhận **2 Tesla T4, mỗi GPU 15.360 MiB**, model dùng `cuda:0`. Mỗi mô hình chạy một optimizer step trên 4 train sample, pretrained forward/backward/save/reload PASS; không lấy smoke metric/weight làm kết quả. Sau gate smoke, chạy hai candidate mỗi model: **seed42, tối đa20 epoch, patience5, effective batch16**.

| Candidate | Dev T0 F1 | Quyết định trước test |
|---|---:|---|
| PhoBERT-CRF c01 | 93,33% | Không chọn; best epoch12/17 epoch đã chạy |
| PhoBERT-CRF c02 | 93,89% | Chọn; best epoch8/13 epoch đã chạy |
| DYN c01 | 93,33% | Không chọn |
| DYN c02 | 94,74% | Chọn bằng unconstrained dev; calibration threshold0,7/margin0,2 |

Cả **4 full run** có report/dev prediction/best-last checkpoint được tải về, hash khớp exact remote version, metric dev được tái tính. Epoch checkpoint khác chỉ còn remote không được gọi là đã xác minh local. `last` có gate metadata/hash để resume; chưa thực nghiệm resume full training, smoke đã kiểm round-trip optimizer/scheduler/RNG.

#### E. Khóa lựa chọn, inference và scorer

Roster v5/pre-test freeze v5/light lock v7 giữ lựa chọn dev; neural dùng đúng submitted source và best checkpoint. Neural workspace khôi phục source đã pin, bridge điều phối riêng giữ nguyên logic inference. Job cuối `huynq16/dacn-s3-final-infer-20261005-v4/1` sinh **100 trạng thái prediction cho từng model/variant**. Global freeze được kiểm trước khi scorer đọc test gold. Scorer áp dụng mask T1, chấm exact-span toàn schema, lưu support/coverage/abstain/error và hashes.

Mỗi run có prediction, native trace, model config, inference/scoring manifest, resource/input/output/code hash và latency. Tái tính metric của 5 cấu hình chạy được PASS; bộ kiểm fixture đảm bảo hợp đồng/gate không thay bằng chứng pretrained thật. Không train/tune bằng 100 test, không chọn lại checkpoint sau khi đọc điểm.

## 3. Kết quả cuối cùng

### 3.1 Corpus và quy trình dữ liệu

| Đầu ra | Trạng thái cuối | Ý nghĩa |
|---|---|---|
| Pilot T0 | 68 mẫu đã duyệt | Thử guideline, giao diện, converter và quy trình QA. Sau khi đã dùng trong pilot thì không dùng làm test cuối độc lập. |
| Train/dev T0 | 240 train / 60 dev | Dùng huấn luyện/chọn cấu hình. Có manifest, coverage và quyết định chống rò rỉ nhóm. |
| Test T0/T1 | 100 mẫu, 446 span; 64 eligible / 20 null / 16 T1-excluded | Đánh giá cuối theo release2. Gán AI-assisted và người dùng rà/duyệt; IAA không đo. T0 giữ đủ mẫu/span kể cả khi T1 bị mask. |
| Near-duplicate review | 138 cặp có quyết định `distinct` và lý do/reviewer | Là cổng kiểm soát split; không mặc định cặp gần giống là cùng địa chỉ. |
| Gazetteer | `s3_v4_nso_dual_snapshot_release2`, partial | Có mã được xác minh theo hai snapshot; 2.187 mã cũ và điều kiện sử dụng nguồn vẫn là giới hạn. |

### 3.2 Kết quả mô hình

T0 dùng exact match `[start,end,label]` trên chuỗi gốc. T1 là dự đoán hệ quy chiếu riêng. Track 5 trường là phép so sánh development/compatibility trên 4.800 hàng sau khi loại 100 hold; không gọi đó là test độc lập.

| Cấu hình | Dev T0 F1 | Test T0 P/R/F1 | Test T1 accuracy / macro-F1 | 5 trường micro-F1 | Kết luận |
|---|---:|---:|---:|---:|---|
| HEUR-JW | 88,01% | 95,12 / 87,44 / **91,12%** | 92,19 / 92,49% | 81,99% | Có thực nghiệm; heuristic hỗ trợ 6/11 nhãn. |
| CRF-INDEP | 90,56% | 92,34 / 89,24 / **90,76%** | Chưa hiện thực T1 | 85,59% | Có thực nghiệm T0; T1 không được suy ra. |
| PHOBERT-CRF | 93,89% | 98,43 / 98,43 / **98,43%** | Chưa hiện thực T1 | 89,94% | Đã fine-tune; checkpoint c02 được chọn trên dev. |
| PROPOSED-DYN | 94,74% | 98,21 / 98,21 / **98,21%** | 71,88 / 56,26% | 89,90% | Có T0/T1; macro-F1 T1 thấp hơn accuracy tổng thể. |
| PROPOSED-NO-CONSTRAINT | 94,74% | 98,43 / 98,43 / **98,43%** | 71,88 / 56,26% | 89,91% | Ablation cùng checkpoint/calibration; chỉ khác constraint flag. |
| DP-ZS-FT | — | Chưa chạy | — | — | `NOT_EXECUTED`; không tính là hoàn thành baseline. |
| DP-FT-FT | — | Chưa chạy | — | — | `NOT_EXECUTED`; không tính là hoàn thành baseline. |

Kết quả ablation là một cảnh báo thực nghiệm: bật dynamic constraint làm thay đổi 1 mẫu và 2 span tuple, giảm T0 F1 **0,22 điểm phần trăm**, nhưng không đổi T1 hoặc số lỗi Quận trên 12 trường hợp gold-mới (0/12). Chưa có bằng chứng rằng constraint cải thiện tổng thể hay triệt tiêu lỗi trong mọi trường hợp.

### 3.3 Những gì chưa thể kết luận

- Test gold có support bằng 0 cho `ToaNha/CanHo`, `MocDinhVi`, `HuongDi`, `GhiChu`; `Khac` chỉ có 2 span. F1 các nhãn 0 support là `NOT_EVALUABLE`, không phải bằng chứng mô hình đạt hay không đạt.
- Nhãn T1 `Lai` có support 5 và F1 bằng 0. DYN chấp nhận 52/64 dự đoán (coverage 81,25%), accuracy trong nhóm được chấp nhận 88,46%, abstain 12. Accuracy có điều kiện không thay thế độ chính xác trên toàn bộ 64 mẫu.
- Chỉ có seed 42; chưa có đánh giá độ dao động nhiều seed. Test được gán có hỗ trợ AI nên IAA `NOT_MEASURED`.
- Không được đối chiếu trực tiếp tỷ lệ lỗi Quận 77,5% với 0/12 cuối nếu mẫu số, split hoặc protocol khác nhau.
- Track 5 trường có một hàng `seen_train` và 4.799 hàng thuộc key đăng ký chưa thấy trong train; key khác không chứng minh độc lập địa lý hoặc nguồn.
- Deepparse zero-shot/fine-tuned chưa có inference/train pretrained được nghiệm thu; ma trận đầy đủ chưa hoàn tất. Phần xác minh checkpoint được để ngoài phạm vi xử lý tiếp theo theo yêu cầu hiện tại, nhưng điều đó không biến hai kết quả còn thiếu thành kết quả đã chạy.
- T2 chưa chạy; Data 05 đã hoãn, VQA đang HOLD; chưa đo đồng thuận giữa hai annotator; T3 chưa thuộc Sprint 3.

### 3.4 Support thực tế: dữ liệu đã đủ để đo cái gì?

Số dưới đây là **số span**, không phải số câu. Một câu có thể chứa nhiều thực thể cùng nhãn. Nguồn chuẩn là `corpus_v1_release2/coverage.json` và metric từng run.

| Nhãn | Train | Dev | Test | HEUR test F1 | CRF test F1 | PhoBERT-CRF test F1 | DYN test F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| SoNha | 215 | 56 | 88 | 100,00% | 97,14% | 100,00% | 100,00% |
| TenDuong | 221 | 60 | 99 | 87,13% | 87,00% | 99,50% | 99,00% |
| Ngo/Hem | 24 | 13 | 13 | 96,30% | 81,82% | 96,30% | 100,00% |
| ToaNha/CanHo | 5 | 0 | 0 | N/E | N/E | N/E | N/E |
| PhuongXa | 227 | 61 | 89 | 92,40% | 87,06% | 97,78% | 98,34% |
| QuanHuyen | 136 | 37 | 56 | 87,13% | 88,50% | **95,50%** | 95,58% |
| TinhThanh | 210 | 54 | 99 | 88,14% | 95,38% | 99,49% | 97,94% |
| MocDinhVi | 6 | 0 | 0 | N/E | N/E | N/E | N/E |
| HuongDi | 5 | 1 | 0 | N/E | N/E | N/E | N/E |
| GhiChu | 5 | 1 | 0 | N/E | N/E | N/E | N/E |
| Khac | 3 | 1 | 2 | 0,00% | 0,00% | 0,00% | 0,00% |
| **Tổng** | **1.057** | **284** | **446** | | | | |

**N/E = `NOT_EVALUABLE_NO_GOLD_SUPPORT`.** Scorer giữ zero-division=0 để tái lập, báo cáo không diễn giải số 0 ấy thành mô hình thất bại hoặc thành công ở nhãn chưa có test. `Khac` khác trường hợp này: có hai gold span và cả hai đều không nhận đúng, nên F1=0 có quan sát thật nhưng cỡ mẫu rất nhỏ.

Năm nhãn phổ biến (`SoNha`, `TenDuong`, `PhuongXa`, `QuanHuyen`, `TinhThanh`) chiếm **431/446 = 96,64%** span test. Do đó micro-F1 cao chủ yếu phản ánh các thành phần này; chưa chứng minh parser xử lý tốt mốc, hướng, tòa nhà và ghi chú. Tổng cộng 11 nhãn đã được định nghĩa và encode, nhưng chỉ 7 nhãn có support test. Đây là hạn chế về **khả năng kiểm chứng**, không phải lỗi của công thức F1.

Về nguồn train/dev, coverage khai báo **87 observed / 81 derived / 132 synthetic** trên 300 mẫu: train 71/69/100, dev 16/12/32. `derived` được dựng từ ánh xạ đã kiểm theo policy; `synthetic` là nhiễu/thiếu/lai hoặc ví dụ kiểm soát. Có source OSM không khiến mọi biến thể con trở thành observed. Metadata noise chi tiết train/dev còn `not_recorded`; không tự báo performance theo một loại OCR cụ thể khi thiếu metadata. Test giữ provenance hạn chế riêng, không suy từ phân bố train/dev.

### 3.5 T0: giải thích số đúng, sai và kết quả từng mô hình

TP là span đúng cả hai ranh giới và nhãn; FP là span dự đoán không khớp gold; FN là gold span chưa khớp prediction. Một span sai nhãn thường tạo **một FP và một FN**, không chỉ một lỗi trong mẫu số F1.

| Cấu hình | TP | FP | FN | Micro-F1 | Macro-F1 7 nhãn có gold | Macro-F1 toàn 11 nhãn* |
|---|---:|---:|---:|---:|---:|---:|
| HEUR-JW | 390 | 20 | 56 | 91,12% | 78,73% | 50,10% |
| CRF-INDEP | 398 | 33 | 48 | 90,76% | 76,70% | 48,81% |
| PHOBERT-CRF | 439 | 7 | 7 | 98,43% | 84,08% | 53,51% |
| PROPOSED-DYN | 438 | 8 | 8 | 98,21% | 84,41% | 53,71% |
| PROPOSED-NO-CONSTRAINT | 439 | 7 | 7 | 98,43% | 84,62% | 53,85% |

\* Toàn 11 nhãn dùng zero-division=0, gồm bốn nhãn không có support; chỉ giữ như chỉ số scorer, **không dùng để xếp chất lượng bốn nhãn không đo được**. Macro 7 nhãn cho mỗi nhãn trọng số bằng nhau nên bị ảnh hưởng rõ bởi `Khac` F1=0; micro ưu tiên nhãn nhiều span. Hai cách nhìn bổ sung nhau.

- **HEUR-JW:** precision 95,12% cao hơn recall 87,44%, phù hợp hành vi từ chối candidate khi chưa chắc. Nhận số nhà rất tốt nhưng bỏ sót nhiều tỉnh/huyện: `TinhThanh` TP78/FN21, `QuanHuyen` TP44/FN12. Hỗ trợ 6 nhãn có 444/446 gold span thuộc tập hỗ trợ; **444/446 là coverage theo khả năng biểu diễn, không phải 444 span đã dự đoán đúng**. Tổng đúng thực tế là390. Trên corpus hiện tại, heuristic có ích làm mốc nhanh và trace được lý do nhưng còn yếu về recall/ranh giới.
- **CRF-INDEP:** tăng TP lên398 nhưng FP33 khiến F1 test thấp hơn HEUR **0,36 điểm phần trăm**. Dev CRF cao hơn HEUR **2,55 điểm**, nên thứ hạng dev không bảo đảm thứ hạng test. Token cue học được tỉnh/huyện, nhưng `Ngo/Hem` chỉ TP9/13 và có nhiều ranh giới gộp. Đây là baseline nhẹ có train thật, không phải PhoBERT rút gọn.
- **PHOBERT-CRF:** có439/446 TP, cao hơn CRF **7,67 điểm phần trăm F1** trên test. Không thấy lỗi ranh giới trong diagnostics lượt này; vẫn có7 nhầm nhãn, đặc biệt cấp hành chính và `Khac`. F1 98,43% không phải tỷ lệ toàn bộ100 câu hoàn hảo và không chứng minh tổng quát hóa sang nguồn mới.
- **PROPOSED-DYN:** dev đứng cao hơn PhoBERT-CRF **0,85 điểm**, nhưng test thấp hơn **0,22 điểm**. `Ngo/Hem`/`PhuongXa` tốt hơn trong mẫu này; `TinhThanh` TP95/FN4 so với PhoBERT-CRF TP98/FN1. Kết quả tổng không chứng minh DYN ưu thế. Đây là kết quả cấu hình đã chốt, không đổi về variant tốt hơn sau xem test.
- **NO-CONSTRAINT:** cùng checkpoint DYN, không phải một model train độc lập thứ năm. F1 test bằng PhoBERT-CRF ở mức làm tròn nhưng tập lỗi khác; không được suy hai mô hình giống nhau.

Không kết luận khác biệt 0,22 hoặc 0,36 điểm là có ý nghĩa thống kê: chỉ100 câu và một seed, chưa có paired bootstrap/khoảng tin cậy.

### 3.6 T1: điểm tổng thể, từ chối và lớp `Lai`

Chấm **64 mẫu đủ điều kiện**: 47 `cu`, 12 `moi`, 5 `Lai`. 20 null và16 ngoại lệ không có đáp án T1 được nghiệm thu để chấm; không biến chúng thành `cu` hoặc `khong_xac_dinh` nhằm tăng số mẫu. Cả100 vẫn chấm T0.

| Chỉ số | HEUR-JW | PROPOSED-DYN và variant off |
|---|---:|---:|
| Đúng / tổng eligible | 59/64 | 46/64 |
| Overall accuracy | 92,19% | 71,88% |
| Macro-F1 ba lớp | 92,49% | 56,26% |
| Accepted / eligible | 61/64 | 52/64 |
| Coverage | 95,31% | 81,25% |
| Accepted accuracy | 96,72% | 88,46% |
| Abstain | 3 | 12 |
| F1 `cu` (support47) | 95,65% | 81,82% |
| F1 `moi` (support12) | 90,91% | 86,96% |
| F1 `Lai` (support5) | 90,91% | 0,00% |

**Confusion DYN**, hàng là gold, cột là prediction:

| Gold | Dự đoán cu | Dự đoán moi | Dự đoán Lai | Abstain |
|---|---:|---:|---:|---:|
| cu (47) | 36 | 1 | 0 | 10 |
| moi (12) | 1 | 10 | 0 | 1 |
| Lai (5) | 4 | 0 | 0 | 1 |

DYN không nhận đúng `Lai` nào:4/5 bị gọi cũ,1/5 từ chối. Dev cũng có Lai F1=0, nên vấn đề đã có trước test. T0 tốt không tự kéo T1 tốt: đầu T0 học ranh giới/loại thực thể, đầu T1 cần bằng chứng hệ và học phân biệt hỗn hợp. Hypothesis cần kiểm ở sprint sau gồm thiếu ví dụ Lai đủ đa dạng, mất cân bằng nhãn và calibration/constraint chưa phù hợp; **chưa có ablation để xác nhận nguyên nhân**.

Accepted accuracy 88,46% chỉ trả lời “khi DYN nhận trả lời thì đúng bao nhiêu”; người dùng vẫn nhận 12 trường hợp không có kết luận. Vì vậy mẫu số64 được giữ trong overall accuracy. CRF/PhoBERT-CRF T1 là `NOT_IMPLEMENTED`, không xếp chúng bằng 0% như một classifier đã chạy rồi sai.

### 3.7 Constraint và mục tiêu giảm ảo giác Quận

| Cấu hình | Dự đoán Quận sai trên gold-moi không có Quận | Recall exact Quận trên cu | Recall exact Quận trên Lai |
|---|---:|---:|---:|
| HEUR-JW | 1/12 | 36/45 =80,00% | 5/5 |
| CRF-INDEP | 0/12 | 40/45 =88,89% | 5/5 |
| PHOBERT-CRF | 0/12 | 42/45 =93,33% | 5/5 |
| DYN on | 0/12 | 43/45 =95,56% | 5/5 |
| DYN off | 0/12 | 44/45 =97,78% | 5/5 |

Mẫu số45/5 chỉ gồm nhóm T1 eligible tương ứng, khác support56 `QuanHuyen` toàn T0 vì T0 giữ cả mẫu T1-null/excluded. Đây là chẩn đoán extraction theo gold system, không phải một classifier T1 bổ sung cho CRF/PhoBERT-CRF.

On/off cùng trọng số thay nhãn một span `QuanHuyen → PhuongXa` ở một mẫu, khiến TP439→438, FP/FN7→8. “2 span tuple thay đổi” là bỏ tuple cũ và thêm tuple mới, **không phải hai mẫu thay đổi**. Quận gold-moi đã0/12 ngay khi off, nên quan sát này không chứng minh constraint là nguyên nhân loại ảo giác. Trên nhóm cũ, recall Quận lại giảm1/45. Mục tiêu ban đầu “triệt tiêu hoàn toàn lỗi77,5%” **chưa được chứng minh đạt**; tỷ lệ77,5% lịch sử không cùng protocol/mẫu số nên không thể tính mức giảm trực tiếp.

### 3.8 Track 5 trường và tốc độ

| Cấu hình | Micro-F1 | Macro trung bình5 trường | Đúng toàn bộ5 trường /4.800 |
|---|---:|---:|---:|
| HEUR-JW | 81,99% | 80,71% | 1.727 /35,98% |
| CRF-INDEP | 85,59% | 85,52% | 3.236 /67,42% |
| PHOBERT-CRF | 89,94% | 90,36% | 3.351 /69,81% |
| DYN on | 89,90% | 90,17% | 3.346 /69,71% |
| DYN off | 89,91% | 90,17% | 3.347 /69,73% |

Độ đúng cả câu thấp hơn F1 thành phần vì chỉ một trường sai đã làm câu không exact. HEUR có F1 thành phần81,99% nhưng chỉ35,98% đúng cả5 trường. PhoBERT-CRF cải thiện mức câu rõ so với HEUR trong track này, nhưng4.800 dòng gồm01/02/03/04/06 vẫn là **development/compatibility**, không phải thêm4.800 test độc lập. 100 hold bị loại; overlap audit còn1 `seen_train`,4.799 `unseen_registered_site_key`. Key chưa thấy trong registry không chứng minh nguồn/địa lý chưa thấy. Neural có4 alignment-abstain/4.800, không bỏ khỏi mẫu số.

| Cấu hình | Mean / p50 / p95 latency (ms) |
|---|---|
| HEUR-JW | 0,82 /0,13 /4,49 |
| CRF-INDEP | 0,25 /0,22 /0,36 |
| PHOBERT-CRF | 22,63 /17,82 /28,36 |
| DYN on | 23,70 /19,43 /29,49 |
| DYN off | 23,92 /19,57 /29,52 |

Latency batch1 tính preprocessing/parse, không tính load checkpoint, không loại warmup. Light chạy CPU WSL, neural chạy GPU T4: bảng phục vụ mô tả chi phí của các lượt đã đo, **không phải so sánh tốc độ trên cùng hardware**.

### 3.9 Các lỗi cụ thể cần giải thích trong báo cáo đồ án

Ví dụ dưới đây là các **cụm đơn vị/công trình** từ error trace, không tái công bố nguyên địa chỉ hoặc nhãn test để tune. Chúng mô tả findings sau đánh giá đóng băng.

| Model | Gold / prediction hoặc lỗi | Ý nghĩa |
|---|---|---|
| HEUR | Tên đường `Phố Bà Huyện Thanh Quan` bị dừng ở `Phố Bà` | Từ “Huyện” trong tên đường gây nhầm boundary cue hành chính |
| HEUR/CRF | Span nuốt dấu `-` ở cuối; CRF gộp prefix ngõ với tên đường | Chọn segment/token chưa đủ kiểm ranh giới literal |
| PhoBERT-CRF | `Q 7`, `Thị xã Quế Võ`: gold QuanHuyen, prediction PhuongXa | Nhận đúng đoạn chữ nhưng nhầm cấp đơn vị cũ; F1 exact-label vẫn phạt |
| PhoBERT-CRF/DYN | `Khu Công Nghệ Cao`, `Khu dân cư số 9`: gold Khac, prediction nhãn khác | Train chỉ3 Khac; cần ví dụ/định nghĩa phân biệt công trình, khu địa điểm và đơn vị |
| DYN | `T. Bắc Ninh`/`Tỉnh Bắc Ninh` bị gọi QuanHuyen | Còn nhầm prefix/cấp; constraint không sửa mọi loại lỗi |

Diagnostics đếm HEUR12 boundary/2label/4spurious/36missed; CRF23/8/0/0; PhoBERT0/7/0/0; DYN0/8/0/0; off0/7/0/0. Đây là **các nhóm lỗi của thuật toán phân tích**, không phải các thành phần có thể cộng trực tiếp để suy TP/FP/FN; dùng bảng3.5 cho số đếm metric chuẩn.

### 3.10 Gazetteer: giá trị sử dụng và khoảng trống

Nguồn snapshot NSO cũ30/06/2025 có63tỉnh/686huyện/9.843xã;1.429 bản ghi có lỗ hổng liên kết cha không được tự promote. Đối chiếu exact theo khóa cha/ngày xác minh **62tỉnh +561huyện +7.984xã =8.607 mã cũ**. Snapshot mới01/07/2025 xác minh **34tỉnh +3.321xã =3.355 mã mới**. Tổng11.962 verified không phải số mã mới được tạo ra; chúng là mã của các entity đã có được tăng mức bằng chứng.

Final package giữ14.149 entity/10.597edge/187alias/5 chuyển đổi phi nguyên tử; **471 khóa cũ nhiều đích** được giữ đầy đủ, không chọn đích đầu tiên.2.187 mã cũ unresolved vẫn có lý do; không tự chế mã để tăng coverage. Lookup có ý nghĩa tên+level+parent+date, trả candidate/evidence/reject. Gazetteer dùng cho HEUR và ràng buộc, nhưng chưa đủ coi là lịch sử đầy đủ mọi interval hiệu lực hoặc một hệ thống geocoding có geometry.

Đây là đóng góp dữ liệu/tài nguyên Sprint3 có thể kiểm chứng. T2 end-to-end còn `NOT_EXECUTED`; không quy số verified thành accuracy ánh xạ T2. Các nguồn CSV chưa rõ redistribution giữ local/private.

## 4. Khó khăn đã gặp và cách xử lý

1. **Môi trường Python/WSL và Label Studio:** WSL có lúc từ chối truy cập; cài Label Studio bằng Python 3.14 vướng build NumPy; URL `0.0.0.0` không mở trực tiếp trên trình duyệt; API token sai trả 401, project ID sai trả 404. Đổi sang Python 3.11 trong venv WSL, khởi động server bind phù hợp nhưng truy cập qua `localhost`, dùng PAT và đúng project ID. Lỗi `READY_FOR_HUMAN_REVIEW` ban đầu gây nhầm với duyệt gold; sau đó quy trình tách QA cấu trúc và human approval.
2. **Gán nhãn và quyết định nội dung:** giao diện yêu cầu chọn hệ cho từng span; hệ toàn câu khác hệ span. Nhiều ca tên địa danh trùng, địa chỉ lai, ranh giới thôn/xã/ngõ/tên đường và cấp đơn vị cần phán quyết người. Converter bắt được lỗi cấu trúc/offset nhưng không tự phát hiện mọi lỗi ngữ nghĩa; do đó cần review nội dung và decision log.
3. **Near-duplicate và split:** địa chỉ giống nhau có thể là vị trí khác nhau (ví dụ số nhà khác), còn khác chữ có thể vẫn cùng địa điểm do OCR/đổi tên/hệ hành chính. Phải xét theo bằng chứng và group nguồn; quyết định sai có thể gây leakage hoặc loại nhầm mẫu.
4. **Alignment tiếng Việt:** tokenizer có thể đổi dấu/cách biểu diễn Unicode làm offset raw lệch. Pipeline kiểm exact substring, giữ offset nguyên bản, xử lý alignment có kiểm chứng và ghi rõ các trường hợp reject; không sửa gold để làm vừa tokenizer.
5. **Tài nguyên và dịch vụ cloud:** máy local thiếu RAM cho một số resource; Kaggle ban đầu có job không GPU và các job lỗi ở import, dev gate hoặc khởi tạo JVM. Giữ log lỗi, tách worker/process, sửa phần orchestration, chạy smoke trước rồi mới full; job thành công cuối kiểm download/hash thực chứ không chỉ tin trạng thái API.
6. **Gazetteer/nguồn:** tìm thấy mã và bảng đối chiếu không đồng nghĩa đã chứng minh quan hệ pháp lý theo thời gian hoặc quyền tái phân phối. Chỉ promote các khóa khớp chính xác theo cha/ngày; để unresolved thay vì tự suy mã/alias/cạnh.

### 4.1 Trouble còn cần lưu trong lịch sử tái lập

| Vướng mắc | Ảnh hưởng | Đã xử lý ra sao | Giới hạn còn lại |
|---|---|---|---|
| WSL `E_ACCESSDENIED`/`E_UNEXPECTED`, có lượt launcher treo | Agent không truy cập runtime ngay được | Hoàn thiện phần độc lập; xác minh đúng PID agent tạo; runtime stdlib Windows có sẵn làm fallback; WSL hồi phục rồi nghiệm thu lại | Không suy fallback stdlib đã chạy training; không thay cấu hình toàn máy |
| NumPy source build khi cài Label Studio Python3.14 | Cài đặt lâu/không có wheel phù hợp | Dùng venv Python3.11 riêng | Không nâng tất cả env dự án chỉ để Label Studio chạy |
| Span chưa có `span_system`, 401 PAT, 404 project | Không Submit/import được | Chọn hệ từng region, xác định token kind và project ID thực | Đăng nhập UI không tự là API auth; prediction import không tự Submit |
| Export thiếu task hoặc nhiều annotation khác nhau | Candidate không đủ để release | Round2 đủ100task/103annotation; quyết định annotation694/task695 và chọn bản tương đương được ghi riêng | Raw round1/round2 giữ nguyên; không lấy bản đầu tiên tùy ý |
| Offset hợp lệ nhưng sai nhãn/cấp/hệ | QA cấu trúc PASS nhưng gold nội dung có vấn đề | Human review, sửa trên Label Studio/export lại, exception có approval/mask | Không khẳng định QA thay người duyệt; IAA vẫn chưa đo |
| Full FastText vượt RAM local | Chưa đủ native integration local | Có code/resource gate; kiểm cloud RAM đủ | Blocker cuối hai DP là điều kiện checkpoint còn thiếu, không dùng RAM local làm lý do mọi cloud không chạy |
| PyTorch từ chối tên temporary checkpoint | Lưu weights atomic lỗi | Đổi quy tắc tên file temporary và kiểm save/reload/tamper | Không ghi đè checkpoint cũ |
| CLI Kaggle tải toàn checkpoint qua buffer lớn | MemoryError với file khoảng1,6GB | Downloader streaming1MiB, atomic, size/hash/path/disk gates; retry bounded, pin exact version | Bản tải dở giữ lịch sử; không fallback sang latest |
| GPU ban đầu không được cấp dù API đã auth | Không qua smoke gate | Chủ dự án kiểm tài khoản/Accelerator; smoke thật xác minh2T4 | Trạng thái COMPLETE/quota không chứng minh đã train bằng GPU |
| Kernel cuối v1/v2/v3 lần lượt lỗi import/devgate/JVM | Chưa có inference được nghiệm thu | Bridge source pin, outer ID phù hợp, worker process riêng theo model/track; version4 PASS | Chỉ orchestration đổi; giữ model/weights/calibration; cả3 lỗi vẫn có registry |
| Debug preview dev khác thứ tự vì set | So sánh JSON tưởng metric lệch | Chuẩn hóa thứ tự list debug khi đối chiếu, mọi event/count khớp | Không sửa prediction/cloud metric/scorer frozen để ép PASS |
| Đường cache Windows/upload và temp fixture | Upload không tương thích; fixture từng dùng `/tmp` | Upload bằng WSL, nghiệm thu fullsuite với TMPDIR trênD | Chỉ persistent install/cache/artifact được tính dung lượng; không cộng fixture đã tự dọn |

### 4.2 Nghiệm thu cuối và quản lý dung lượng

| Kiểm tra tại mốc đánh giá cuối | Kết quả đã có | Phải hiểu như thế nào |
|---|---|---|
| Full regression suite | 274 =266 PASS +8 SKIP,0 FAIL | Các integration không đủ runtime trong suite chính được skip explicit |
| Runtime modeling chuyên biệt | 52/52 PASS | Báo riêng, có thể trùng fullsuite; không cộng thành326test |
| Runtime CRF chuyên biệt | 13/13 PASS | Kiểm trong env phù hợp; không cộng các suite chồng lặp |
| Integrity protected | 2.352 file hash +4 raw size/mtime PASS | Bằng chứng bảo toàn corpus/run/source thuộc audit; raw rất lớn có scope size/mtime riêng |
| Recompute metric | 5 cấu hình chạy được PASS | T0/T1 và 5 trường được đối chiếu; không có DP metric để recompute |
| GPU/remote artifact | Exact version/content/hash PASS | Job thật, checkpoint thật; không chỉ API status |
| Git receipt | `sprint3_huy`, remote SHA `ad2eaf04fea0e7145453242e143040cac7c90c57` | Bàn giao lịch sử đã được kiểm; không nghĩa các file báo cáo mới của lượt này đã push |

Các con số kiểm thử trên là **bằng chứng thực nghiệm đã có** ở mốc đóng 05/10, không phải tuyên bố chạy lại toàn suite khi biên tập báo cáo này. Lượt viết báo cáo chỉ kiểm tài liệu, nguồn số liệu và liên kết.

| Phạm vi đo | Bytes | GB (10^9) | GiB (2^30) | Giải thích |
|---|---:|---:|---:|---|
| Cài/resource local lượt tích hợp03/10 | 2.453.588.804 | 2,453589 | 2,285083 | Runtime/model/Java/cache trong phạm vi inventory26/27; không phải tổng cả ổD |
| Snapshot evidence/release lượt47 | 23.296.355.884 | 23,296356 | 21,696422 | Khử trùng hardlink/inode; chứa checkpoint, ZIP, tải dở và resource dùng lại; **không phải cài mới23GB** |
| Cài/package/model local lượt đánh giá cuối49 | 0 | 0 | 0 | Tái dùng runtime/resources đã có |
| Artifact mới lượt cuối, receipt v2 | 1.673.016.327 | 1,673016 | 1,558118 | Unique file bytes sau khử trùng; không gồm toàn history hoặc các tài liệu viết sau snapshot |
| Runtime/cache cloud job cuối | 8.923.520.962 | 8,923521 | 8,310677 | Scratch Kaggle, không chiếm ổD local |

Kaggle CLI 2.2.4 và 32 dependency cài riêng trên D ở lượt 04/10, report38/40 giữ phiên bản và số đo. Runtime neural local gồm Python 3.11.16, Torch 2.8.0+cpu, Transformers 4.57.1, Deepparse 0.11.0, Poutyne 1.17.4, py-vncorenlp 0.1.4; cloud có Torch CUDA 12.8/Python 3.11 theo lock. **Có package Deepparse không nghĩa có pretrained DP run.** PhoBERT revision `01daacda68afe13d83023d16ec647239e344a1e6`, VnCoreNLP commit `62bbc58fe5d113c898eae112656be97dcf50b3a0`; danh sách phụ thuộc/hash đầy đủ ở inventory/resource locks.

Không cộng các snapshot chồng nhau thành “tổng đã tốn” vì chúng chứa resource/hardlink dùng lại. Chênh lệch disk-free cũng không chứng minh allocated growth riêng của một lượt. Việc viết báo cáo này không cài package/model hoặc chạy cloud mới.

Chi tiết runtime, run ID, hash, package và artifact xem [báo cáo kết quả cuối](49_sprint3_final_results.md), [hướng dẫn tái lập](50_sprint3_reproduction_and_handoff.md), phát hành corpus và smoke/full runs, nghiệm thu nguồn và Gazetteer, cùng các báo cáo alignment và cài đặt liên quan trong mục lục Sprint 3.

## 5. Cần cải thiện gì

### 5.1 Những kết luận đã có cơ sở và chưa có cơ sở

| Phát biểu | Đánh giá bằng chứng |
|---|---|
| Có quy trình dữ liệu/offset/runner/scorer và kết quả tái lập | Có corpus/version/hash, alignment thật, run/prediction và recompute |
| PhoBERT-CRF/DYN vượt baseline nhẹ trên T0 của test hiện tại | Có số liệu chênh lệch; chưa đo độ chắc thống kê/multi-seed |
| Đã giải quyết đầy đủ T0 cả 11 nhãn trong thực tế | Chưa: 4 nhãn zero-support test, Khac chỉ 2 span và F1=0 |
| Mô hình đề xuất tốt hơn PhoBERT-CRF toàn diện | Chưa:microT0 thấp hơn, T1 còn Lai F1=0; không có T1 PhoBERT baseline để so head tương đương |
| Constraint đã loại bỏ hoàn toàn lỗi Quận 77,5% | Chưa: off đã 0/12 ở cùng tập con; on gây 1 nhầm; mẫu số không tương đương lịch sử |
| Đã hoàn thành hết ma trận Sprint 3 | Chưa: 2 cấu hình DP không thực nghiệm; nguồn/gazetteer và dữ liệu thật còn partial/hold/deferred |
| Kết quả hiện tại áp dụng chắc chắn cho hóa đơn/OCR thực | Chưa:VQA chưa được clearance thành corpus đánh giá, noise phần lớn là tổng hợp/kiểm soát |

### 5.2 Backlog cải thiện, tác động và cách nghiệm thu

| Ưu tiên | Hạn chế cần giải quyết | Cách làm tiếp | Bằng chứng đạt yêu cầu |
|---|---|---|---|
| P1 | Nhãn hiếm thiếu support; nguồn chưa đa dạng | Release mới, chọn mẫu có nguồn; báo observed/derived/synthetic, group-disjoint và support theo nhãn | Coverage đủ để đo hoặc NOT_EVALUABLE rõ; không đổi 100 test Sprint 3 |
| P1 | Chưa có IAA | Hai người gán tập con độc lập trước khi thấy prediction/nhãn nhau; exact-span F1 + token Kappa rồi adjudicate | Hai export độc lập, tokenizer/unit rõ, agreement trước phán quyết và decision log |
| P1 | Lai không nhận đúng; T1 abstain cao | Phân tích nguồn/T1 support, class weighting/sampling và calibration trên dev mới theo budget khóa | T1 perclass/confusion/coverage-risk; report null/excluded; ablation xác nhận giả thuyết |
| P2 | Constraint gây nhầm/không thấy lợi ích | Paired on/off cùng weights; kiểm confidence/điều kiện kích hoạt trên dev mới | Báo delta T0, Quận sai trên moi, recall Quận trên cu/Lai, số ca đổi; chấp nhận kết quả không cải thiện |
| P2 | Một seed và test100 nhỏ | Seed định trước, mean/std; paired bootstrap theo **sample**, không coi từng span độc lập | Từng run+hash, khoảng bất định theo protocol; không chọn seed bằngtest |
| P2 | Quyền/cha/ngày/mã chưa đủ cho gazetteer | Rà 2.187 unresolved và hồ sơ provenance riêng, snapshot/version mới nếu đủ chứng cứ | Không suy interval/cạnh; terms unknown giữ private; không nâng partial bằng số lượng |
| P3 — hoãn | Hai DP chưa thực nghiệm | Giữ bảng historical NOT_EXECUTED; chỉ lập run mới khi tài nguyên/bằng chứng đầy đủ và nhóm mở lại | Native smoke/train/inference/metric thật; không làm mặc định trong lượt hiện tại |

Những hàng trên là đề xuất nghiên cứu tiếp, không phải quyền tự thu dữ liệu/cài resource/train mới. Mốc/hướng thật vẫn hoãn ở Sprint3; nếu Sprint4 lấy lại đầu việc này cần chốt nguồn, người gán và ngân sách ở kickoff.

### Ưu tiên chất lượng nghiên cứu

- Bổ sung ví dụ thật và đủ support cho bốn nhãn chưa có test gold; tăng mẫu `Khac`/`Lai` và phân tầng theo nguồn, vùng, chất lượng OCR, hệ cũ/mới/lai. Không cân bằng bằng cách tổng hợp rồi báo như dữ liệu thật.
- Tổ chức gán nhãn độc lập trên một tập con mới, khóa guideline trước khi hai người gán, đo Cohen's Kappa token-level và exact-span F1. Không dùng lại vòng prediction-assisted làm IAA.
- Chạy nhiều seed và báo mean/std cho cấu hình được chọn; dùng dev để chọn, giữ test cho một lần đánh giá đóng băng sau khi bổ sung support.
- Thực hiện phân tích lỗi có kiểm soát theo nhãn, nguồn và kiểu địa chỉ; xử lý các trường hợp zero-support bằng bổ sung dữ liệu/định nghĩa nhãn, không bằng thay đổi test sau khi xem điểm.

### Ưu tiên kỹ thuật và dữ liệu

- Giữ trạng thái hai cấu hình Deepparse là `NOT_EXECUTED` trong ma trận lịch sử. Đây là khoảng trống Sprint 3 được công khai, nhưng không đưa việc xác minh checkpoint thành đầu việc mặc định của Sprint 4.
- Làm rõ provenance/quyền sử dụng nguồn CSV trước khi chia sẻ hoặc phát hành gazetteer; không nâng trạng thái partial và không suy mã/quan hệ khi thiếu chứng cứ.
- Tạo evaluation card gắn corpus hash, model/config hash, seed, split, support, coverage và hardware; tự động xác nhận prediction freeze trước scorer.
- Tách rõ T0 extraction, T1 classification, T2 mapping và track 5 trường trong mọi bảng; ghi rõ coverage, abstention và mẫu số.
- Đặt tiêu chí nghiệm thu theo nhãn và use case, không chỉ một micro-F1 tổng; xem xét rủi ro khi hệ thống abstain hoặc nhầm đơn vị theo thời gian.

## 6. Đề xuất kế hoạch Sprint 4

Sprint 4 được đề xuất tập trung vào hai câu hỏi còn quan trọng nhất sau Sprint 3: **nhãn T0/T1 có được gán đủ nhất quán và có đủ support để đo không; kết quả mô hình có ổn định qua nhiều seed không?** Kế hoạch chi tiết, phân công hai người, phụ thuộc, các cổng nghiệm thu và rủi ro nằm trong [kế hoạch Sprint 4](../sprint_04/01_sprint4_two_person_plan.md).

Phân công ở cấp vai trò:

- **Người A:** phân tích thiếu hụt dữ liệu, provenance, sampling/group split, guideline và gán nhãn độc lập, agreement/adjudication, phát hành corpus version mới.
- **Người B:** khóa runner/config từ dev, chạy T0/T1 nhiều seed trên dữ liệu đã qua gate, paired ablation, error analysis và evaluation card.
- **Cùng làm:** khóa protocol trước khi bắt đầu, kiểm chống leakage, duyệt release candidate và báo các mục chưa đạt.

Phạm vi Sprint 4 giữ nguyên release2 và các run Sprint 3. Không dùng test Sprint 3 để tune; không mở rộng sang T2, T3, API/RAG hoặc hạng mục Deepparse chưa có thực nghiệm trong kế hoạch hiện tại. Nếu nguồn hoặc annotator thứ hai không sẵn sàng, báo blocker và giảm tuyên bố; không tự thay bằng dữ liệu tổng hợp hoặc gán lặp của một người.

### Thứ tự triển khai và đầu ra bàn giao

| Checkpoint | A làm | B làm | Cổng cần đạt trước bước tiếp theo |
|---|---|---|---|
| C0 — Chốt phạm vi | Support/nguồn/guideline/IAA plan; đề xuất holdout mới | Protocol T0/T1/abstention/seed/ablation; resource budget | Hai người xác nhận protocol; giữ nguyên Sprint3 release2 |
| C1 — Nguồn và queue | Rà source register, privacy/quyền dùng, ID tài liệu/site group; chọn nhãn thiếu | Kiểm runner/config, dữ liệu synthetic stress tách riêng nếu dùng | Provenance và group/near-duplicate audit PASS; nguồn không rõ giữ HOLD |
| C2 — Annotation | Điều phối hai lượt độc lập và adjudication | Chạy converter/agreement sau khi cả hai lượt đã freeze | Offset/label/system QA PASS; IAA báo trước adjudication, không prediction-assisted trong tập đo |
| C3 — Release | Approval/decision log, coverage và manifest corpus mới | Audit hash/split, prepare alignment | Owner duyệt; không train bằng candidate chưa qua gate |
| C4 — Thí nghiệm | Kiểm chất lượng và phân tầng theo nguồn của lỗi | Train/dev các seed đã chốt; T1/Lai calibration; paired constraint | Không chọn bằng holdout; đầy đủ prediction/checkpoint/config/hash |
| C5 — Đánh giá và tổng kết | Rà support, giới hạn provenance/IAA | Freeze rồi score holdout mới nếu đủ điều kiện; recompute, mean/std/CI | Evaluation card và acceptance có PASS/PARTIAL/BLOCKED rõ |

**Có thể bắt đầu trước khi có data mới:** thống kê thiếu support, chốt protocol/sampling/IAA, đóng gói runner và kiểm integrity của mốc Sprint3. **Cần chờ data gate:** training thực nghiệm mới và đánh giá trên holdout mới. Nếu chưa có holdout đủ độc lập, chỉ báo development/stability, không đổi nhãn “dev” thành “test”.

Sprint4 chưa được chạy trong lượt báo cáo này. Danh sách nguồn, quota nhãn, số seed/ngân sách và người duyệt là quyết định kickoff; kế hoạch không mặc định có đủ annotator hay compute. Các tồn đọng Gazetteer/VQA/DP được giữ trong sổ backlog; mở lại theo ưu tiên nhóm, không kéo theo triển khai T2/T3 ngoài trọng tâm.

## 7. Artifact tham chiếu và trạng thái bảo toàn

- Báo cáo metric, giới hạn, run và dung lượng: [49 — Kết quả đánh giá cuối Sprint 3](49_sprint3_final_results.md).
- Tái lập inference/scoring và bàn giao: [50 — Hướng dẫn tái lập](50_sprint3_reproduction_and_handoff.md).
- Kế hoạch Sprint 4 chia vai trò, thứ tự, đầu ra và tiêu chí nghiệm thu: [Sprint 4 README](../sprint_04/README.md) và [kế hoạch hai người](../sprint_04/01_sprint4_two_person_plan.md).
- Phát hành test gold và Kaggle: 47 — Test gold release và GPU runs.
- Corpus chính thức: `data/processed/annotation/sprint03/corpus_v1_release2/` và `data/processed/annotation/sprint03/test_gold_v1_release2/`.
- Train/dev: `data/processed/annotation/sprint03/corpus_train_dev_v2/`.
- Evidence chi tiết/private: `data/interim/modeling/sprint03/final_completion_20261005_v1/`.
- Gazetteer: `data/processed/gazetteer/s3_v4_nso_dual_snapshot_release2/`.

Raw export, gold, checkpoint, cache và evidence private không mặc nhiên là artifact công khai trên GitHub. Không sửa split, raw/gold, Gazetteer hoặc run đã khóa trong quá trình viết báo cáo này. Báo cáo này chỉ tổng hợp và liên kết tới evidence sẵn có.

### 7.1 Tra cứu bằng chứng cho từng nội dung

| Nội dung | Tài liệu/code hướng dẫn | Artifact chuẩn cần đọc trong workspace |
|---|---|---|
| Guideline và Label Studio | [Guideline](span_11_annotation_guideline.md), hướng dẫn400 | Export/decision/approval dưới `data/interim/annotation/sprint03/`; corpus phát hành là đầu vào bất biến |
| Phát hành train/dev | Report13, scripts22/25 | `corpus_train_dev_v2/{train,dev,dev_input,manifest,coverage}` |
| Reannotation nguồn | Report08, script21 | Trace/generation manifest/queue của `reannotation_v2_release1`; không dùng candidate làm gold |
| Gazetteer | Report31, report32 | `s3_v4_nso_dual_snapshot_release2/`; nguồn/query/response/hash trong evidence riêng |
| Actual alignment | Report28, scripts37/38 | `neural_integration_tone_v2_replay_20261003_fullpath/`, `full_300_audit_r5/` |
| Baseline nhẹ | Report34, scripts26/27/28 | `data/processed/evaluation/sprint03/{heur_jw_followup_20261003_v1,crf_followup_20261003_v1}/` |
| Release/test và GPU full runs | Report47, scripts50/54/60 | `release_and_kaggle_20261005_v1/`: dev acceptance, checkpoint hash, submitted source, selection locks |
| Final metric | [Report49](49_sprint3_final_results.md), script62 | `final_completion_20261005_v1/scoring_v1/results_index.json`, từng `test_run/metrics.json` |
| Integrity/tests/Git/dung lượng | [Report50](50_sprint3_reproduction_and_handoff.md) | `sprint3_completion_manifest.json`, `protected_closure_audit.json`, `full_tests_closure.log`, `storage_receipt_v2.json`, `git_final_receipt.json` |

Đường dẫn rút gọn trong bảng là tên artifact, không phải lệnh để chạy lại vào folder frozen. Lệnh tái lập và runtime phù hợp ở report50; mọi replay cần output directory/run ID mới.

## 8. Kết luận và việc nhóm cần làm với báo cáo này

**Đóng góp đã đạt của Sprint 3:** thiết lập được corpus T0/T1 có QA/phán quyết/manifest; gazetteer theo hai snapshot với evidence mã; alignment raw-offset dùng được cho 300 mẫu; baseline nhẹ và hai mô hình neural có training/inference thật; prediction freeze/scorer/recompute và hồ sơ tái lập. PhoBERT-CRF đạt 439/446 span đúng, DYN 438/446 trên test release2.

**Các khoảng trống cần công khai:** hai DP chưa thực nghiệm, chưa chứng minh dynamic constraint cải thiện, T1 Lai yếu, bốn nhãn test không có support, IAA chưa đo, provenance/nguồn hành chính còn partial và VQA/Data05 chưa nghiệm thu. Vì vậy báo cáo không kết luận đã hoàn tất toàn bộ Sprint3 hoặc đã xử lý đầy đủ địa chỉ Việt Nam qua mọi thay đổi hành chính.

**Chủ dự án và partner cần làm:**

1. Xác nhận tên A/B và đóng góp thực tế nếu dùng phần1 làm bảng phân công/tác giả chính thức. Hồ sơ này mới phân vai theo đầu ra, không tự xác nhận ai viết/chạy toàn bộ phần đó.
2. Đọc mục3.4–3.9 khi trình bày kết quả; nêu cùng lúc micro-F1, support nhãn, T1 coverage/Lai và paired ablation.
3. Chốt kickoff Sprint4 theo kế hoạch liên kết: nguồn/annotator thứ hai/support/holdout/compute. Các quyết định đó cần con người; viết báo cáo không tự mở một đợt thu data hoặc training.

Không cần gán lại400 mẫu, export lại Label Studio hay chạy lại Kaggle/Colab để hoàn thành **báo cáo** này. Mốc Git đã push trong receipt là lịch sử; bản tổng kết53 và kế hoạch Sprint4 cần commit riêng nếu nhóm muốn cập nhật remote. Lượt biên tập chỉ tạo/cập nhật tài liệu và kiểm số liệu/liên kết, không sửa artifact thực nghiệm đã khóa.
