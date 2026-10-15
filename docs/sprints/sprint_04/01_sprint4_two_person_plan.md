# Kế hoạch Sprint 4 — nâng độ tin cậy T0/T1 và đánh giá độ ổn định

> **Khung đề xuất lịch sử:** từ 06/10/2026, áp dụng [protocol v1](02_s4_protocol_v1.md). Chủ dự án xác nhận phụ trách toàn bộ và không có người gán thứ hai. Các vai A/B dưới đây trở thành nhóm trách nhiệm của cùng chủ dự án; IAA giữ NOT_MEASURED, kiểm tra gán lặp intra-annotator và cổng nghiệm thu theo protocol hiện hành. Hạn mới là 20/10/2026; nguồn/số mẫu/holdout/compute còn cổng kiểm tra. Không coi các giả định hai người trong tài liệu này là yêu cầu phải đạt hiện tại.

**Phiên bản:** 1.0  
**Cơ sở:** kết quả Sprint 3 chốt ngày 05/10/2026.  
**Trạng thái:** kế hoạch đề xuất, chưa phải công việc đã thực hiện.  
**Phân công:** theo vai trò Người A / Người B; thay bằng tên thành viên khi nhóm xác nhận.

## 1. Mục tiêu Sprint 4

Sprint 3 đã tạo được corpus span 11 nhãn, quy trình phát hành, các baseline và kết quả cuối cho một số mô hình. Tuy nhiên, kết quả chưa đủ mạnh ở các nhãn hiếm, T1 `Lai`, độ đồng thuận người gán và độ ổn định qua seed. Sprint 4 tập trung giải quyết các giới hạn này, không mở rộng sang bài toán ánh xạ hành chính T2 hay đối sánh T3.

**Mục tiêu:** tạo một gói bằng chứng mới, có thể tái lập, về chất lượng nhãn và độ ổn định T0/T1 trên dữ liệu được chia theo nhóm nguồn, đồng thời giữ nguyên các kết quả Sprint 3 làm mốc lịch sử.

Sprint 4 không đặt mục tiêu “làm F1 cao hơn bằng mọi giá”. Kết quả đạt yêu cầu nếu đo lường trung thực được mức bất định, support và giới hạn; nếu mẫu hiếm vẫn chưa đủ, phải báo `NOT_EVALUABLE` thay vì suy diễn.

## 2. Điểm xuất phát đã được xác nhận

- Corpus release2: 240 train / 60 dev / 100 test; test có 446 span.
- Test T1 có 64 mẫu đủ căn cứ, 20 mẫu null, 16 mẫu mask khỏi T1; mask không xóa span T0.
- Gán test là `AI_ASSISTED_HUMAN_REVIEW`; đồng thuận giữa hai người `NOT_MEASURED`.
- T0 test F1: HEUR-JW 91,12%; CRF-INDEP 90,76%; PhoBERT-CRF 98,43%; PROPOSED-DYN 98,21%; PROPOSED-NO-CONSTRAINT 98,43%.
- T1 PROPOSED-DYN: accuracy 71,88%, macro-F1 56,26%; nhãn `Lai` support 5, F1 0%; 52/64 được chấp nhận, 12 abstain.
- Constraint động làm đổi 1 mẫu/2 span tuple, giảm T0 F1 0,22 điểm phần trăm trên test; không đổi T1 hoặc 0/12 lỗi Quận trong tập con đã định nghĩa. Đây chưa phải bằng chứng tổng quát rằng constraint loại bỏ lỗi.
- `ToaNha/CanHo`, `MocDinhVi`, `HuongDi`, `GhiChu` có 0 support trên test; `Khac` có 2. Vì thế không thể kết luận chất lượng mô hình trên các nhãn này.
- Chỉ có một seed. Kết quả 5 trường là track phát triển/tương thích, không phải test độc lập; không gộp với T0/T1.
- Gazetteer hiện ở trạng thái partial; T2 chưa được nghiệm thu. Các hạng mục này được giữ ngoài phạm vi Sprint 4 theo kế hoạch hiện tại.

Nguồn chi tiết: [báo cáo kết quả cuối Sprint 3](../sprint_03/49_sprint3_final_results.md), [báo cáo quy trình và tổng kết](../sprint_03/53_sprint3_end_to_end_report_20261005.md).

## 3. Phạm vi và giới hạn

### Trong Sprint 4

1. Lập kế hoạch support cho nhãn hiếm và phân tầng mẫu theo nguồn/hệ/chất lượng văn bản.
2. Thu thập hoặc chọn thêm dữ liệu chỉ từ nguồn được phép, có provenance và không chứa địa chỉ khách hàng cá nhân.
3. Gán nhãn dữ liệu mới theo guideline có version; đo đồng thuận trên tập con được gán độc lập bởi hai người.
4. Tạo release dữ liệu Sprint 4 mới sau adjudication, group-disjoint split và audit rò rỉ.
5. Đo độ ổn định các cấu hình T0/T1 đã chọn qua nhiều seed trên train/dev; làm paired ablation cho constraint và báo coverage/abstention.
6. Cập nhật evaluation card, phân tích lỗi, hướng dẫn tái lập và biên bản nghiệm thu.

### Ngoài Sprint 4

- Không mở lại hoặc sửa corpus/gold/test/split/run đã khóa của Sprint 3.
- Không chọn threshold, mapping, checkpoint, seed hay model bằng kết quả test Sprint 3.
- Không coi lại 100 test Sprint 3 là test mới hoặc dùng nhãn đó để phát triển mô hình.
- Không triển khai T2 ánh xạ mã hành chính, T3 đối sánh địa chỉ, RAG/API/Docker.
- Không mở lại vấn đề điều kiện sử dụng Deepparse trong kế hoạch này; hai cấu hình DP của Sprint 3 tiếp tục được ghi là chưa có thực nghiệm pretrained được nghiệm thu.
- Không dùng dữ liệu tổng hợp để tuyên bố đã bổ sung support thực tế; nếu dùng tổng hợp cho stress test thì tách thành track riêng.

## 4. Phân công cho hai người

| Vai trò | Phạm vi chịu trách nhiệm | Không tự quyết định |
|---|---|---|
| **Người A — dữ liệu, guideline và nghiệm thu nhãn** | Phân tích support; lập sampling/provenance register; chọn/thu mẫu hợp lệ; quản lý project gán nhãn; điều phối gán độc lập; tổng hợp agreement; adjudication; phát hành corpus Sprint 4 candidate và coverage. | Không sửa nhãn Sprint 3 đã khóa; không đổi guideline giữa vòng mà không version bump; không đưa prediction cho annotator thứ hai trong tập đo IAA; không tự gán là agreement nếu chỉ một người. |
| **Người B — mô hình, thí nghiệm và tái lập** | Khóa config từ dev; chuẩn bị train/dev mới sau data gate; chạy các seed cố định; tính T0/T1, support, coverage, abstention; paired constraint ablation; phân tích lỗi; đóng gói run manifest, environment lock, prediction và evaluation card. | Không mở test Sprint 3 để tune; không chọn model theo test; không thay gold/split; không gọi pipeline/fixture pass là pretrained result. |
| **Cả hai — cổng chung** | Chốt tiêu chí support/IAA, rà rủi ro leakage, duyệt release candidate, xác nhận thay đổi guideline và ký nghiệm thu. | Không phát hành nếu thiếu provenance, annotation decision, hash hoặc audit split. |

Phân vai này cân bằng theo đầu ra cần tạo; nó không khẳng định ai đã thực hiện phần nào của Sprint 3. Lịch sử vai trò Sprint 3 được mô tả riêng trong báo cáo tổng kết.

## 5. Lộ trình công việc theo thứ tự phụ thuộc

### S4-P0 — Kickoff và khóa protocol

**Chủ trì:** A + B.  
**Mục đích:** ngăn việc thu mẫu, gán nhãn hoặc chạy seed trước khi thống nhất đơn vị đánh giá.

**Thực hiện:**

1. Khóa hash của release2, model config, guideline `s3-span-v1.1`, scorer và kết quả Sprint 3 làm mốc; chỉ đọc.
2. Chốt phiên bản dữ liệu Sprint 4 là release mới; định nghĩa `source_group`/`site_group`, loại nguồn hợp lệ, metadata và chính sách loại trùng.
3. Chốt danh sách nhãn ưu tiên dựa vào coverage hiện có: trước hết `MocDinhVi`, `HuongDi`, `ToaNha/CanHo`, `GhiChu`, `Khac`; tăng mẫu T1 `Lai` theo bằng chứng.
4. Chốt mục tiêu support theo tập (train/dev/test) sau khi xem khối lượng nguồn thực tế. Không tự ấn định số lượng mẫu để đạt chỉ tiêu nếu nguồn không đủ.
5. Chốt tập IAA: lấy mẫu phân tầng độc lập, có mặt nhãn hiếm/ca khó; khuyến nghị ít nhất 20% dữ liệu mới hoặc 60 mẫu (lấy mức lớn hơn nếu nguồn cho phép). Nếu tổng dữ liệu mới dưới 60, gán đôi toàn bộ phần mới và ghi rõ độ bất định do cỡ mẫu nhỏ.
6. Viết protocol đánh giá: exact-span T0, T1 eligible/null/excluded, threshold/abstention, split group-disjoint, số seed, metric và quy tắc NOT_EVALUABLE.

**Đầu ra:** `s4_protocol_v1.md`, hash snapshot của các mốc Sprint 3, sampling/IAA plan và acceptance checklist.  
**Gate:** cả A và B ký protocol trước khi mở thu/gán dữ liệu.

### S4-A1 — Phân tích thiếu hụt và đăng ký nguồn

**Chủ trì:** Người A. **Phụ thuộc:** S4-P0.

1. Tạo bảng support hiện tại từ manifest/coverage và kết quả 49; ghi rõ nguồn, split, nhãn, T1 class và số lượng.
2. Với mỗi nhãn hiếm, ghi định nghĩa vận hành, ví dụ bao gồm/loại trừ, nguồn dự kiến và rủi ro nhầm với nhãn lân cận.
3. Lập source register gồm URL/ID, thời điểm lấy, giấy phép/phạm vi dùng, loại dữ liệu, định danh tài liệu/địa điểm cha và hash nguồn.
4. Loại địa chỉ cá nhân/PII; không suy ra dữ liệu quan sát từ tên benchmark hoặc chuỗi địa chỉ.
5. Đánh dấu rõ `observed`, `derived`, `synthetic`, `unknown`; không trộn các lớp trong báo cáo kết quả.

**Đầu ra:** support gap report, source register, selection queue có group ID và audit log lấy/loại mẫu.  
**Gate:** không nhập mẫu vào annotation trước khi nguồn và quyền sử dụng được ghi nhận.

### S4-A2 — Chọn mẫu, chống trùng và phân chia candidate

**Chủ trì:** Người A; Người B review split script. **Phụ thuộc:** A1.

1. Chọn mẫu theo phân tầng: nguồn/địa lý có thể xác minh, cũ/mới/lai, OCR/nhiễu, thiếu trường, nhãn hiếm và ambiguity.
2. Giữ các biến metadata chỉ trong sidecar; annotation UI chỉ hiển thị text và ID cần thiết, không hiển thị gold/benchmark metadata.
3. Gán `group_id` theo tài liệu/địa điểm/nguồn cha trước khi split; chạy exact/normalized/near-duplicate audit.
4. Chia group-disjoint thành train/dev và một holdout Sprint 4 hoàn toàn mới. Nếu support không đủ cho holdout thì ghi giới hạn; không lấy mẫu test Sprint 3 để bù.
5. Lập file queue/import có chỉ ID và text; prediction-assisted có thể dùng cho vòng gán chính nếu được protocol cho phép, nhưng tập IAA phải mù và độc lập.

**Đầu ra:** input queues versioned, group assignment, near-duplicate report, split manifest.  
**Gate:** 0 group trùng split; mọi duplicate/uncertain có quyết định và lý do.

### S4-A3 — Gán nhãn, IAA và adjudication

**Chủ trì:** Người A; Người B chạy thống kê IAA sau khi hai lượt độc lập được freeze. **Phụ thuộc:** A2.

1. Khóa guideline; nếu cần sửa định nghĩa, tạo `s3-span-v1.2` hoặc phiên bản mới, ghi ví dụ và decision log trước annotation.
2. Dùng Label Studio/import mới, gán toàn bộ spans literal, label, span-system và whole-address T1 theo guideline.
3. Trong tập IAA, hai annotator gán độc lập cùng task; không xem prediction/gold/người kia trước khi freeze cả hai vòng.
4. Đo Cohen's Kappa token-level với quy tắc tokenization đã ghi, exact-span precision/recall/F1 giữa hai annotator và confusion theo nhãn; báo support/CI hoặc giới hạn cỡ mẫu. Kappa và exact-span F1 bổ sung nhau, không thay thế nhau.
5. Adjudicate sau khi lưu kết quả agreement nguyên bản; ghi quyết định, lý do, annotator/adjudicator và thời điểm. Không tính nhãn sau adjudication vào IAA như thể hai người đồng thuận ban đầu.
6. Chạy converter/QA offsets, substring, labels, system fields, overlap, duplicate IDs, missing tasks và review flags.

**Đầu ra:** raw exports bất biến, agreement report, adjudication log, canonical candidate và QA report.  
**Gate:** toàn bộ task có trạng thái; lỗi QA bằng 0 hoặc được giải quyết bằng quyết định có thể truy nguyên.

### S4-A4 — Phát hành dữ liệu Sprint 4

**Chủ trì:** Người A; Người B review manifest. **Phụ thuộc:** A3.

- Tạo corpus version mới, không sửa `corpus_v1_release2` hay `corpus_train_dev_v2`.
- Gắn hash cho raw export, guideline, config, queues, split và converter.
- Công bố số mẫu/span theo split/nhãn/nguồn/hệ, IAA, nguồn unknown, các mask và giới hạn.
- Kiểm tra leakage theo group/site, exact text, normalized text và near duplicates.

**Đầu ra:** `corpus_s4_v1/` candidate (train/dev/new holdout), manifest, coverage, split audit, release note.  
**Gate:** release status chỉ `APPROVED` sau khi owner duyệt nội dung và artifact; nếu chưa duyệt để `CANDIDATE`.

### S4-B1 — Khóa gói thí nghiệm và baseline

**Chủ trì:** Người B. **Phụ thuộc:** P0; dùng A4 khi đã sẵn sàng. Trong lúc chờ A, chỉ có thể chuẩn bị runner/config trên snapshot đã khóa.

1. Khóa danh sách các mô hình có thực nghiệm được nghiệm thu ở Sprint 3: HEUR-JW, CRF-INDEP, PhoBERT-CRF, PROPOSED-DYN và ablation. Không đưa DP vào bảng “đã chạy” khi chưa có experiment.
2. Ghi rõ phiên bản model/checkpoint/resource, code hash, corpus hash, supported labels, preprocessing/alignment và hardware.
3. Giữ hyperparameter đã chọn ở Sprint 3 làm điểm xuất phát; không sweep rộng. Tách thay đổi cấu hình thành run mới.
4. Chốt seed kế hoạch `[42, 1337, 2025]`; với HEUR không có training seed, chỉ chạy một cấu hình cố định. Nếu training compute không đủ, chạy phần độc lập và báo thiếu seed.
5. Thiết lập prediction-first: lưu và hash prediction dev trước scorer; không trộn gold input vào inference.

**Đầu ra:** model roster, resource/code lock, execution plan, empty run registry.  
**Gate:** run không bắt đầu nếu corpus/config/resource hash không khớp protocol.

### S4-B2 — Đo độ ổn định T0/T1 và constraint

**Chủ trì:** Người B. **Phụ thuộc:** A4 và B1.

1. Huấn luyện các cấu hình neural/CRF trên train Sprint 4; mỗi seed có `run_id` và output directory mới. Không gộp train/dev, không chọn theo holdout.
2. Chọn checkpoint/operating point chỉ trên dev theo metric đã khóa; lưu toàn bộ score theo seed.
3. Chấm dev T0 exact span toàn 11 nhãn, từng nhãn/support/coverage; T1 accuracy, macro-F1, confusion, accepted coverage và abstention.
4. Báo mean, standard deviation và từng seed; không chỉ đưa seed tốt nhất.
5. Với DYN, dùng cùng checkpoint/calibration/input để chạy constraint on/off; báo paired sample/span change, delta T0/T1, FP Quận trên tập con định nghĩa và recall theo hệ. Không tuyên bố “triệt tiêu hoàn toàn” từ tỷ lệ nhỏ.
6. Tách kết quả `observed`, `derived` và `synthetic`; nếu có stress test synthetic, đặt bảng riêng.

**Đầu ra:** predictions đóng băng từng seed, metrics, paired ablation, error analysis, run manifests.  
**Gate:** đủ seed đã cam kết hoặc có blocker cụ thể; không có artifact bị overwrite; scorer khớp gold hash.

### S4-B3 — Báo cáo và tái lập

**Chủ trì:** Người B; Người A xác nhận dữ liệu. **Phụ thuộc:** B2.

- Viết evaluation card gồm mục đích, tập áp dụng, support, macro/micro, seed mean/std, abstention, giới hạn và các nhãn `NOT_EVALUABLE`.
- Thêm bảng paired comparison mới với Sprint 3 chỉ khi track/schema/source/split semantics so sánh được; nếu khác thì trình bày song song, không trừ trực tiếp điểm.
- Chạy regression tests và audit hash corpus/run cũ trước/sau.
- Ghi lệnh tái lập, môi trường, package/checkpoint, thời gian/chi phí compute thực đo và nơi lưu artifact.

**Đầu ra:** evaluation card, Sprint 4 results report, reproduction guide, final integrity audit.  
**Gate:** báo cáo có đầy đủ numerator/denominator, version/hash, seed, hardware và không có tuyên bố ngoài dữ liệu.

## 6. Timeline theo checkpoint

Không giả định sprint dài bao nhiêu ngày; nhóm có thể gắn ngày sau khi chốt lịch.

| Checkpoint | Công việc song song | Điều kiện chuyển bước |
|---|---|---|
| **C0 — Protocol** | A+B chốt scope, support target, IAA, split và metric. | Protocol và mốc Sprint 3 được hash/khóa. |
| **C1 — Data readiness** | A lập nguồn/queue; B chuẩn hóa runner và resource lock trên dev frozen. | Nguồn hợp lệ, queue có provenance, group split audit pass. |
| **C2 — Annotation** | A điều phối gán; B không xem task IAA cho tới khi cả hai annotation freeze. | Đủ trạng thái task, IAA được tính trước adjudication, lỗi QA được giải quyết. |
| **C3 — Corpus release** | A phát hành candidate; B tái kiểm hash/split. | Owner duyệt release; candidate thành input bất biến. |
| **C4 — Experiments** | B chạy seed/ablation; A review phân tầng và nguồn của lỗi. | Predictions/dev metrics/hash đầy đủ, không có leakage. |
| **C5 — Sprint review** | A+B trình bày kết quả, giới hạn và quyết định tiếp theo. | Acceptance checklist đóng hoặc ghi rõ mục chưa đạt. |

## 7. Tiêu chí nghiệm thu Sprint 4

### Dữ liệu và gán nhãn

- Mọi mẫu có ID, source group, provenance class, quyền sử dụng và split; nguồn chưa rõ được gắn `unknown`, không suy đoán.
- Không có group hoặc duplicate chưa xử lý chạy xuyên train/dev/holdout.
- 100% task có trạng thái QA; annotation candidate khớp substring và offset nguyên bản; mọi ngoại lệ được ghi sổ.
- IAA được đo trên hai lượt độc lập trước adjudication; nếu thiếu annotator thì ghi `NOT_MEASURED` và không gọi release là đã xác nhận độ đồng thuận.
- Corpus mới có version/hash riêng; Sprint 3 release2 không đổi.

### Mô hình và đánh giá

- Mỗi run có seed, corpus/model/code/resource hash, hardware, prediction hash và run ID riêng.
- T0/T1/5-field không bị trộn; unsupported/zero-support được báo đúng.
- Mean/std qua các seed và từng seed đều được báo; abstention có denominator rõ.
- Ablation constraint paired trên cùng checkpoint và calibration; không suy rộng ngoài support.
- Test Sprint 3 không được mở lại để tune; nếu có holdout mới thì chỉ chấm sau khi roster/prediction đã freeze.

### Bàn giao

- Có dữ liệu candidate/release, coverage, IAA, split audit, evaluation card, run manifests, report, reproduction guide và integrity audit.
- Mọi blocker có owner, tác động, đường khắc phục và trạng thái.

## 8. Rủi ro và cách giảm thiểu

| Rủi ro | Tác động | Kiểm soát |
|---|---|---|
| Nguồn không đủ cho nhãn hiếm | Không thể đo chất lượng từng nhãn | Không đặt quota giả; báo NOT_EVALUABLE và giữ nhãn ở research backlog. |
| Annotator thứ hai không sẵn sàng | Không đo được IAA | Thu nhỏ phạm vi IAA có chủ đích nếu có thể; nếu không, ghi NOT_MEASURED. Không dùng self-rerun làm agreement. |
| Cặp cùng địa điểm qua split | Điểm dev/holdout lạc quan | Group trước split, exact/normalized/near-duplicate audit và quyết định người có lý do. |
| Thay guideline trong khi gán | Nhãn không nhất quán | Version bump, pause batch, ghi quyết định và re-QA phần bị ảnh hưởng. |
| Một seed tốt che độ bất ổn | Kết luận quá lạc quan | Báo tất cả seed, mean/std và per-label support. |
| DYN có T1 Lai yếu/abstain nhiều | Khả năng dùng thực tế thấp | Đánh giá coverage-risk/accepted accuracy song song; không chỉ nhìn accuracy. |
| Data mới khác phân phối benchmark | So sánh không công bằng | Báo theo nguồn/stratum, không gộp thành một điểm duy nhất nếu semantic khác. |

## 9. Các quyết định cần chốt tại kickoff

Đây là các quyết định quản trị Sprint 4; không cần trả lời để đọc hoặc sử dụng kế hoạch, nhưng phải chốt trước khi bắt đầu các bước phụ thuộc:

1. Ai là Người A và Người B, ai có quyền duyệt gold cuối.
2. Có annotator thứ hai độc lập hay không; nếu không, IAA không phải deliverable đạt được trong sprint.
3. Các nguồn được phép dùng và tiêu chí support mục tiêu theo nhãn.
4. Holdout mới có đủ dữ liệu/nguồn độc lập hay Sprint 4 chỉ báo dev/stability.
5. Ngân sách compute và số seed bắt buộc nếu vượt khả năng hiện có.

## 10. Danh sách đầu ra cuối Sprint 4

1. Protocol v1, data gap/source register và guideline version được dùng.
2. Queue/import/export bất biến, decision/adjudication log và IAA report.
3. Corpus release mới (nếu đạt gate), coverage và split/duplicate audit.
4. Runner/config/resource lock, predictions/metrics theo seed và paired ablation.
5. Error analysis, evaluation card, reproduction guide và integrity audit.
6. Báo cáo cuối nêu PASS/PARTIAL/BLOCKED theo từng deliverable; không gọi toàn Sprint hoàn tất nếu gate phát hành hoặc IAA bị bỏ ngỏ mà kế hoạch coi là bắt buộc.
