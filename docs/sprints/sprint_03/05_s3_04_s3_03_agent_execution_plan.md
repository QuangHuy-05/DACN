# Kế hoạch giao agent — ưu tiên 2: corpus T0/T1; ưu tiên 3: gazetteer đa phiên bản

**Ngày lập:** 29/09/2026. **Loại tài liệu:** kế hoạch triển khai, chưa phải kết quả thực hiện.
**Ưu tiên 2:** S3-04, xây corpus gold và khóa train/dev/test.
**Ưu tiên 3:** S3-03, nâng gói gazetteer đa phiên bản từ `s3_v1` hiện có.
**Ngoài phạm vi lần này:** rà soát/đưa VQA vào corpus, thu thập địa chỉ thật có `MocDinhVi`/`HuongDi`, Data 05 quan sát, huấn luyện/chạy baseline. VQA tiếp tục `HOLD`; Data 05 quan sát ghi `DEFERRED_BY_USER`.

## 0. Nguồn chuẩn và những điều không được làm sai

1. Pilot gold 68 mẫu đã được người gán duyệt tại `data/processed/annotation/sprint03/pilot_gold_v1.jsonl`, có `pilot_gold_v1_manifest.json`. Trong đó có 24 mẫu OSM cũ, 24 mẫu OSM mới, 20 ví dụ nhãn hiếm tổng hợp có kiểm soát. Đây là dữ liệu **train/dev candidate**, không phải test và không phải 20 địa chỉ mốc/hướng quan sát thật. Giữ nguyên byte và hash pilot v1.
2. Guideline `docs/sprints/sprint_03/span_11_annotation_guideline.md` đã khóa ở `s3-span-v1.1`; Label Studio dùng `configs/label_studio_span11.xml`. Manifest pilot lưu hash guideline/config. Nếu hash hiện tại khác manifest, dừng nhập batch mới để tìm nguyên nhân; không sửa ngầm guideline theo nhãn test.
3. Queue batch 01 `data/interim/annotation/sprint03/annotation_queue_batch01.csv` gồm 68 `pilot_train_pool`, 100 `frozen_benchmark_test_hold`, 20 `external_test_hold` VQA. Chính **100 sample ID đã frozen** là test T0 chính; 20 VQA không tham gia hai ưu tiên này. Tập benchmark 07 là nguồn chặn trùng/T2, không phải test T0.
4. Gazetteer `data/processed/gazetteer/s3_v1/` đã có 14.144 entity, 10.597 cạnh nguyên tử, 187 alias và manifest/hash. Đây là `s3-gazetteer-v1-partial`, không được ghi đè hoặc gọi là đã xác minh toàn bộ mã cũ. Manifest ghi 10.035 ward cũ có `candidate_code` từ `third_party` nhưng **0 mã ward cũ đã được xác minh từ nguồn chuẩn**; 3.321 ward mới có mã từ bảng ánh xạ. Có 5 dòng nguồn chuyển đổi cấp huyện không có khóa ward cũ, đang được giữ ở `skipped_mapping_rows` chứ không dựng cạnh ward giả.
5. `data/raw/`, `third_party/`, benchmark 5 trường frozen, pilot gold, batch 01, gazetteer v1 và raw export đã duyệt là bất biến. `scripts/10_prepare_span_annotation.py` ghi đè queue/import batch 01; `scripts/13_build_temporal_gazetteer.py build` ghi đè `s3_v1`. **Không chạy lại hai lệnh này trên đầu ra hiện hành.** Tạo script/đường dẫn version mới cho batch 02 và gazetteer v2.
6. Không đưa `GT_*`, `ChuoiDiaChiGoc`, `HeQuyChieu`, `KieuThieu`, `Span_He_Detail`, `candidate_rare`, nguồn/nhóm, prediction model hoặc đáp án benchmark vào giao diện Label Studio. Task gán nhãn chỉ có `data.sample_id` và `data.text`. Các cột GT chỉ có thể dùng phía điều phối để kiểm nhóm/chấm đúng track, không là input mô hình.
7. Không sử dụng địa chỉ khách hàng thật. Không dùng VQA trong train/dev/test của corpus v1 ở kế hoạch này. Không cài dependency mới hoặc crawl nguồn mới nếu chưa có chỉ đạo phù hợp `AGENTS.md`. Nếu cần danh mục mã cũ chính thức từ ngoài repo, trước tiên lập hồ sơ nguồn cụ thể để chủ dự án cung cấp/chốt quyền dùng.
8. Mọi số lượng mới trong tài liệu là **mục tiêu thiết kế**, không phải số đã gán hoặc được duyệt. Không phát hành trạng thái `APPROVED_GOLD`, `CORE_CORPUS_READY` hay `GAZETTEER_VERIFIED` chỉ vì script chạy xong.

## 1. Trình tự tổng thể và cổng bàn giao

| Thứ tự | Gói việc | Đầu ra trung gian | Cổng phải qua |
| --- | --- | --- | --- |
| 1 | Chụp trạng thái và hash đầu vào | Snapshot + danh sách ID cố định | Không có input drift |
| 2 | S3-04: khóa protocol split | Protocol version, seed, nhóm/chặn trùng, test IDs | Chủ dự án xác nhận trước khi mở test |
| 3 | S3-04: tạo/gán batch 02 train/dev | Queue/import mới, raw export, QA, gold đã duyệt | Người gán duyệt nội dung |
| 4 | S3-04: gán 100 test riêng | Raw export, QA, gold test đã duyệt | Đúng 100/100; không thấy GT |
| 5 | S3-04: audit và phát hành corpus | Train/dev/test JSONL, manifest/hash, distribution | Không rò rỉ nhóm; người duyệt ký |
| 6 | S3-03: audit v1 và nguồn mã | Gap report, source register, hồ sơ mã cũ | Không nâng mã ứng viên thành mã chuẩn |
| 7 | S3-03: build và audit v2 | Entities/edges/aliases/lookup/manifest/coverage | Đúng thời gian, cạnh, ID, trạng thái mã |

Việc audit gazetteer có thể chạy cùng lúc với chọn/gán batch 02. Corpus lõi không chờ mã cũ chính thức; phần sinh địa chỉ lai chỉ dùng cạnh bảng ánh xạ đã xác minh. Gazetteer v2 là điều kiện cho `HEUR-JW` và các ràng buộc giải mã về sau, không phải lý do để dùng test khi chưa khóa split.

## 2. Ưu tiên 2 — S3-04: xây corpus gold và khóa split

### C2.1 — Chụp input và danh sách test cố định

1. Đọc `AGENTS.md`, `docs/data_quality.md`, `span_annotation_inventory.md`, guideline v1.1, manifest pilot, `scripts/10_prepare_span_annotation.py` và `scripts/11_convert_label_studio_pilot.py`. Tính lại SHA-256 của pilot gold, queue batch 01, guideline, XML, nguồn OSM, các benchmark 01/02/03/04/06/07. Đối chiếu hash đã ghi; bất đồng phải ghi `BLOCKED_INPUT_DRIFT` trước khi chọn mẫu.
2. Tạo **snapshot mới** `docs/sprints/sprint_03/s3_04_input_snapshot_v1.json`: đường dẫn, hash, số dòng, schema, version, ngày chụp. Không chứa toàn bộ địa chỉ VQA. Chụp đúng tập 100 `sample_id`, `text_sha256`, `source_dataset`, `group_id` (tên cột trong queue) vào `data/interim/annotation/sprint03/test_hold_manifest_v1.json`; không thay lại ID do ca khó. Khi chuyển sang canonical, `group_id` trở thành `source_group`.
3. Đếm lại 68 pilot/100 test/20 VQA bằng `planned_role`. Bảo đảm 100 test gồm 20 từ mỗi benchmark 01, 02, 03, 04, 06. Chụp group chặn từ **toàn bộ** benchmark, kể cả 07, không chỉ 100 test.

**Đạt khi:** mọi input khớp hash/row count hiện hành, danh sách 100 ID được khóa bằng hash, pilot gold v1 không bị thay đổi.

### C2.2 — Viết protocol split trước khi gán test

1. Tạo `docs/sprints/sprint_03/t0_corpus_split_protocol_v1.md` và bản máy đọc `data/interim/annotation/sprint03/split_protocol_v1.json`. Chốt seed `42`, phiên bản code chọn nhóm, nguồn được phép, nguồn chặn, chỉ tiêu phân tầng, tỷ lệ train/dev, quy tắc QA/duyệt, cách xử lý mẫu không thể gán, ngày và người khóa.
2. Nguồn train/dev là OSM cũ/mới từ **nguồn ngoài file benchmark**, cộng 68 pilot gold và biến thể tổng hợp có parent thuộc train/dev. Không đưa cả 100 test lẫn các dòng benchmark còn lại vào train/dev. 20 VQA `external_test_hold` vẫn `HOLD`; không tạo `external_vqa.jsonl` trong lần này.
3. Chia ở cấp **nhóm địa chỉ gốc** trước khi tạo biến thể. Cùng `OSM_Type:OSM_ID`, cùng site số nhà–đường, cùng `parent_sample_id`, family ví dụ tổng hợp, cặp cũ/mới của cùng điểm, hoặc địa chỉ gần trùng đã xác nhận phải nằm cùng một split. Dùng hàm `site_group()` hiện có làm khóa bảo thủ; gộp nhóm bằng cạnh có bằng chứng. Ghi quyết định gộp/loại vào sổ, không đổi `group_id` chỉ để làm đẹp số overlap.
4. Rà chéo bằng hash text chính xác, text chuẩn hóa, ID OSM/parent, site key và hàng đợi gần trùng. Ngưỡng `SequenceMatcher >= 0.85` chỉ **đề xuất ca cần người xét**; không tự kết luận cùng địa chỉ từ tên đường phổ biến. Khóa ngưỡng trước khi mở nhãn test, không điều chỉnh theo kết quả mô hình.
5. Mục tiêu khởi động: khoảng **300 mẫu train/dev đã duyệt**, trong đó 68 pilot đã có và khoảng 232 mẫu mới; chia xấp xỉ 80/20 theo nhóm, không làm vỡ nhóm để đạt tỷ lệ chính xác. Đây là quota lập kế hoạch để ước lượng khối lượng gán; nếu pool không đủ, báo con số thật và lý do. 100 test đã fixed, không nằm trong 300.
6. Định nghĩa manifest từng mẫu: `sample_id`, `text_sha256`, `source_dataset`, `source_ref`, `source_file_sha256`, `source_row` hoặc source object ID, `source_group`, `parent_sample_id`, `derivation`, `observed_or_synthetic`, `split`, `stratum`, `guideline_version`, `annotation_export_hash`, `review_status`. Metadata lưu ngoài task gán và ngoài input mô hình.

**Đạt khi:** protocol đã version/hash và chủ dự án chốt, test ID fixed, không dùng nhãn test/GT để chọn quota, alias hoặc ngưỡng.

### C2.3 — Chọn batch 02 train/dev

1. Viết builder mới, ví dụ `scripts/16_prepare_t0_corpus_batch.py`, nhận queue batch 01, pilot gold, OSM nguồn, benchmark group exclusion và protocol. **Không sửa output batch 01.** Builder phải xác minh cột bắt buộc, nguồn, hash, sample ID duy nhất và seed cố định.
2. Đưa 68 pilot gold vào pool theo `source_group`. Đánh dấu riêng 20 dòng `controlled_rare_seed` là `synthetic_controlled`; chúng có giá trị dạy quy tắc/huấn luyện nhưng không là support *observed* cho mốc/hướng. Không gán toàn bộ 68 vào train mặc định: trước tiên phân chia các group giữa train/dev.
3. Chọn thêm khoảng 232 địa chỉ nguồn cũ/mới ngoài mọi nhóm benchmark. Cân đối ca cấu trúc hai cấp, ba cấp, nhiễu OCR, thiếu trường và lai **khi có bằng chứng**. Nếu dùng generator noise/missing/hybrid, phân nhóm parent trước rồi sinh biến thể trong cùng split; ghi parent, generator version, seed, nguồn cạnh hành chính. Không suy đoán đích A/M khi thiếu hình học/ngữ cảnh.
4. Tạo `annotation_queue_batch02_train_dev.csv`, `annotation_batch02_manifest.json` và `label_studio_batch02_import.json`; JSON import chỉ có `data.sample_id`, `data.text`. Nếu cần hỗ trợ gán nhanh bằng prediction, chỉ sử dụng cho train/dev và phải được người gán kiểm từng span; test không có preannotation. Không lộ GT hoặc gợi ý nguồn.
5. Trước import: 0 ID trùng; 0 group giao với tập benchmark/test; mỗi biến thể có parent trong cùng split; file nguồn/hash có thể truy nguyên. Nếu 232 không đạt, xuất backlog/shortfall với lý do và không tự bù bằng benchmark/VQA.

**Đạt khi:** batch 02 có manifest/hash và provenance từng mẫu; không lẫn nguồn cấm; quota thực đạt được báo trung thực.

### C2.4 — Gán, chuyển đổi và duyệt gold train/dev

1. Dùng project Label Studio mới cho batch 02 với **đúng XML đã khóa**. Người gán thấy `sample_id` và `text`, gán nguyên văn 11 span, `span_system` cho từng span, `address_system` T1 chỉ khi có chứng cứ; tuân thủ quy tắc `Khac`/`O`, `QuanHuyen=cu`, dấu câu, cụm “nay là”. Ghi cờ và note cho ca OCR/ranh giới/hệ mơ hồ.
2. Lưu raw export từng vòng ở `data/interim/annotation/sprint03/exports/batch02/`, không ghi đè. Tạo converter tổng quát mới hoặc mở rộng `scripts/11_convert_label_studio_pilot.py` với `--queue`, `--role`, `--export`, `--output-dir`, giữ hành vi mặc định của pilot. Không dùng bộ chuyển cũ nguyên trạng vì nó lọc cứng `pilot_train_pool`.
3. QA từng task: đúng sample ID/text queue; một annotation được chọn hoặc có map ID adjudication; `0 <= start < end <= len(text)` và `text[start:end]` khớp; không overlap; nhãn thuộc 11 loại; hệ span thuộc `cu/moi/khong_xac_dinh`; `QuanHuyen` phải `cu`; T1 chỉ `cu/moi/Lai` hoặc null; không mất ký tự khi Unicode/OCR. Check toàn bộ task có trạng thái rõ.
4. Người gán/duyệt sửa ca sai trên Label Studio, ghi sổ quyết định ca có flag, rồi xác nhận nội dung đủ mẫu. `READY_FOR_HUMAN_REVIEW` chỉ là QA cấu trúc; agent không tự phát hành gold. Lưu gold batch 02 và manifest hash mới sau duyệt. Nếu có hai người gán **độc lập** cùng tập, đo Cohen’s Kappa token và exact-span F1; nếu một người, ghi `NOT_MEASURED`.

**Đạt khi:** toàn bộ mẫu được giữ trong batch 02 có annotation hợp lệ và người duyệt xác nhận; mẫu loại có ID/lý do; 0 lỗi offset, nhãn, hệ, overlap. Pilot gold 68 không phải gán lại.

### C2.5 — Gán riêng đúng 100 benchmark test

1. Chỉ sau C2.2, mở project Label Studio **test riêng** từ đúng 100 dòng `frozen_benchmark_test_hold`. Import chỉ `sample_id`/`text`, không GT, metadata, prediction hay chuỗi sạch. Không tái lấy mẫu do nhãn khó. Người gán theo cùng guideline/XML đã khóa.
2. Export raw JSON version riêng; converter chung kiểm đúng 100/100 fixed IDs, đúng 20 mỗi tập nguồn, không thừa/thiếu, text hash trùng test manifest, 0 lỗi cấu trúc. Người duyệt xem và quyết định ca khó, ghi biên bản rồi mới chuyển canonical candidate thành test gold.
3. Giữ test gold trong vị trí held-out nội bộ. Runner huấn luyện/tuning chỉ nhận train/dev manifest; chỉ scorer của lượt đánh giá cuối dùng test sau khi checkpoint, threshold, alias, gazetteer hash và cấu hình đã khóa. Nếu phát hiện lỗi gold test sau này, phát hành erratum v2 và đánh giá lại **mọi** mô hình trên cùng bản, không sửa riêng ca model sai.

**Đạt khi:** 100/100 test có gold duyệt người, 0 lỗi cấu trúc và bằng chứng task gán không chứa GT/prediction.

### C2.6 — Audit split và phát hành corpus

1. Tạo `data/processed/annotation/sprint03/corpus_v1/train.jsonl`, `dev.jsonl`, `test_benchmark_t0.jsonl` chỉ khi các cổng trước đạt; canonical mỗi dòng `(sample_id, text, spans[{start,end,label,system}], address_system, source_group)`. Không tạo file external VQA trong phạm vi này.
2. Kiểm giao `sample_id`, text hash, `source_group`, OSM object, parent và cặp gần trùng giữa train/dev/test. Mọi va chạm chưa phân xử là `BLOCKED_SPLIT`. Lưu báo cáo nhóm bị gộp, mẫu bị loại và quyết định thủ công; bảo toàn bằng chứng nguồn.
3. Báo số mẫu/số group theo split, nguồn, observed/synthetic, hệ `cu/moi/Lai/null`, độ nhiễu, thiếu trường, số span/support từng nhãn. T1 null không được điền từ metadata. `MocDinhVi`/`HuongDi` trong synthetic được thống kê riêng; không gọi F1 test thật Data 05 nếu chưa có test observed phù hợp.
4. Tạo `corpus_v1_manifest.json` với hash input/queue/guideline/XML/export/gold/split/code, seed, protocol, người duyệt/ngày duyệt, counts, QA, leakage audit, agreement status. Cập nhật `docs/data_quality.md`, `README.md` và Sprint 3 README bằng **số thật**. Mọi thay đổi sau phát hành tạo v2, không viết đè v1.

**Đạt khi:** 0 group chồng chéo giữa split, 0 near duplicate nghi rò rỉ chưa xử lý, 0 lỗi annotation, test 100/100 và hash kiểm lại khớp. Trạng thái `CORE_CORPUS_READY` chỉ áp dụng phạm vi nhãn có support; `DATA05_OBSERVED=DEFERRED_BY_USER`, `VQA_EXTERNAL=HOLD`.

## 3. Ưu tiên 3 — S3-03: hoàn thiện gói gazetteer đa phiên bản

### G3.1 — Audit v1 và khóa hợp đồng dữ liệu v2

1. Đọc `scripts/13_build_temporal_gazetteer.py`, `s3_v1/manifest.json`, `entities.csv`, `edges.csv`, `aliases.csv`, `src/data/administrative_mapping.py`, `src/data/administrative_alias.py`, bảng mapping `data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv`. Tính lại hash và đối chiếu manifest trước khi dùng. Không chạy `build` v1 vì nó ghi đè gói hiện tại.
2. Lập `docs/sprints/sprint_03/gazetteer_v1_gap_audit.md`: số entity theo `system/level/code_status`, số cạnh C/A/B/M, alias, mã cũ candidate vs verified, mã mới, 5 dòng phi nguyên tử, ID/parent thiếu, duplicate name/code, và giới hạn tọa độ/hình học. Dùng số thực; manifest v1 là mốc đối chiếu, không suy ra số verified từ việc `candidate_code` có giá trị.
3. Chốt schema v2: giữ `entity_id`, `level`, `system`, `canonical_name`, `parent_id`, `official_code`, `candidate_code`, `code_status`, `valid_from`, `valid_to`, `source_id`, `source_hash`, `status`; cạnh nguyên tử giữ đầy đủ khóa cũ tỉnh–huyện–xã, đích tỉnh–xã+mã, `relation`, `merge_form`, `source_row`. Alias có entity ID và bằng chứng. Thêm bảng `non_atomic_transitions.csv` cho 5 trường hợp cấp huyện nếu source đủ rõ; không chuyển chúng thành cạnh ward giả. Nếu đổi schema so với v1, version thành `s3_v2` và cập nhật mọi consumer liên quan.

**Đạt khi:** v1 vẫn nguyên vẹn; gap report và hợp đồng v2 có hash/version, chỉ rõ phần nào có thể xây từ nguồn hiện có và phần nào thiếu bằng chứng.

### G3.2 — Sổ nguồn và xác minh mã hành chính cũ

1. Lập `gazetteer_source_register_v2.csv`: `source_id`, tên cơ quan/tài liệu, URL hoặc đường dẫn, cấp hành chính, hệ cũ/mới, khoảng hiệu lực, ngày truy cập, giấy phép/phạm vi dùng, file SHA-256 và vai trò (`edge_authority`, `official_code_authority`, `candidate_only`, `audited_alias`). Bảng mapping hiện hành là nguồn cho cạnh cũ→mới và mã xã mới; file `third_party/vietnamadminunits/...legacy...csv` chỉ là nguồn **ứng viên mã cũ**.
2. Kiểm trong repo có danh mục mã cũ chính thức với tên đơn vị, loại đơn vị và mốc thời gian không. Nếu chưa có, lập hồ sơ nguồn cụ thể cho chủ dự án cung cấp/chốt quyền dùng trước khi tải/crawl. Không tự quảng bá file bên thứ ba thành nguồn chuẩn; không tự tạo mã để tăng coverage.
3. Khi có nguồn chuẩn, đối chiếu bằng khóa đầy đủ **tỉnh cũ–quận/huyện cũ–phường/xã cũ** và loại đơn vị, giữ dấu. Chỉ `verified_source` nếu khóa và mã khớp duy nhất, có source row/hash và kỳ hiệu lực phù hợp. Trường hợp thiếu, trùng, mâu thuẫn hoặc đổi tên chưa rõ phải `unverified_missing`/`unverified_conflict`/`candidate_third_party_unverified`; ghi riêng bảng mismatch để người duyệt xem. Không dùng khớp tên không dấu/khớp mờ để cấp mã chuẩn.
4. Không coi ID nội bộ SHA của v1 là mã hành chính chính thức. Không gắn tọa độ/hình học nếu nguồn chưa có bằng chứng. Không lấy ngày `valid_from` của hệ cũ từ suy đoán; giữ unknown. Hệ cũ kết thúc 30/06/2025 và hệ mới bắt đầu 01/07/2025 theo gói hiện tại, ghi nguồn chứng minh mốc trong manifest.

**Đạt khi:** mọi `official_code` có nguồn/row/hash và kỳ hiệu lực; mã chưa xác minh vẫn hiện rõ status. Nếu không có nguồn mã cũ đạt chuẩn, gói v2 được phát hành **partial có ghi coverage**, không gắn nhãn “mã cũ đã hoàn thiện”.

### G3.3 — Build v2 không ghi đè v1

1. Tạo builder mới, ví dụ `scripts/19_build_temporal_gazetteer_v2.py`, output `data/processed/gazetteer/s3_v2/`. Đầu vào versioned: mapping chuẩn, alias đã audit, file candidate mã cũ và nguồn mã chính thức **nếu có**. Check file/cột/hash trước khi xử lý. Dùng `pathlib`, tên biến/hàm tiếng Anh, CSV UTF-8-sig, thứ tự sort cố định và source IDs cụ thể.
2. Sinh entity cũ/mới với `parent_id` đúng: cũ province→district→ward; mới province→ward. `entity_id` phải ổn định theo system, level, đầy đủ khóa cha và canonical name; kiểm collision và duplicate code. Giữ loại đơn vị và dấu trong tên. Alias chỉ từ `administrative_alias.py` hoặc nguồn alias được duyệt; alias không tự tạo cạnh hành chính.
3. Sinh cạnh nguyên tử **chỉ** từ các dòng có đủ khóa cũ tỉnh–huyện–xã và đích, mã mới trong bảng mapping. Tính C/1-1, A/1-N, B/N-1, M/M-N theo bậc đồ thị; không ép M-N thành A/B, không chọn một đích ở split khi thiếu bằng chứng tọa độ/hình học. Ghi `source_row`, hash, `HinhThucSapNhap`, mã mới trên cạnh.
4. Giữ 5 trường hợp thiếu ward cũ thành `non_atomic_transitions.csv` với khóa cấp huyện, đích, loại quan hệ nguồn và trạng thái `NOT_WARD_EDGE`; đối chiếu từng dòng với nguồn. Không tự suy ra mọi ward cũ trong huyện đã đi vào một đích. Các dòng nguồn thiếu trường khác phải ở bảng rejected cùng lý do.
5. Xuất `entities.csv`, `edges.csv`, `aliases.csv`, `non_atomic_transitions.csv`, `source_register.csv`, `coverage_report.json`, `manifest.json`. Manifest ghi version, boundary date, hash script/nguồn/output, counts theo hệ/cấp/code status, quan hệ đồ thị, số bản ghi bị giữ/loại và limitation. Nếu nguồn mã cũ chưa có, giữ `candidate_code` riêng và `official_code` rỗng cho cũ.

**Đạt khi:** build lặp lại với cùng input tạo cùng nội dung/hash; v1 không thay đổi; mọi dòng nguồn được phân loại thành cạnh nguyên tử, chuyển đổi phi nguyên tử hoặc rejected có lý do.

### G3.4 — Lookup và hợp đồng dùng cho mô hình

1. Mở rộng lookup theo `name + level + as_of + system + province + district` (các ngữ cảnh cha tùy chọn), trả **danh sách ứng viên** với entity ID, parent path, code/status, valid dates, alias/source evidence và mọi transition candidate liên quan. Phân biệt `NO_MATCH`, `UNIQUE_ENTITY`, `AMBIGUOUS_ENTITY`; riêng chuyển hệ phân biệt `UNIQUE_TARGET`, `MULTIPLE_TARGETS`, `NO_VERIFIED_TARGET`. Một entity duy nhất không có nghĩa mã cũ đã chuẩn hoặc đích chuyển hệ duy nhất.
2. Lọc theo hiệu lực ngày: 30/06/2025 nhận hệ cũ; 01/07/2025 nhận hệ mới. Hệ cũ thiếu `valid_from` phải được giải thích là “chưa biết ngày bắt đầu”, không suy là tồn tại vô hạn được xác minh. Tra cùng tên ở nhiều tỉnh/cấp phải trả nhiều candidate hoặc yêu cầu thêm context, không chọn tên đầu tiên.
3. Trả bằng chứng nguồn cho từng kết luận. Quan hệ A/M hoặc nhiều đích trả tất cả ứng viên; HEUR-JW và decoder chỉ được rank/từ chối trên dev sau này, không dùng test để chốt một đích. Candidate code cũ không được xuất như official code ở API adapter.
4. Cung cấp ví dụ lookup document và file JSON cho các ca: tên duy nhất, trùng tên nhiều tỉnh, mã cũ chỉ candidate, 1-N, M-N, năm dòng phi nguyên tử, ngày sát 01/07/2025 và không khớp. Ví dụ là minh họa hành vi từ dữ liệu thực, không được ngầm tạo quan hệ mới.

**Đạt khi:** lookup có thể tái lập theo version/hash, không chọn sai đích khi nguồn nhiều nhánh, người dùng thấy rõ trạng thái xác minh và bằng chứng.

### G3.5 — QA, phát hành và giới hạn được công bố

1. Kiểm thống kê đầu ra so với v1 và từng dòng mapping: số entity/cạnh/alias, mã trùng, orphan parent, cạnh tới entity thiếu, ngày hiệu lực vô lý, alias trùng, source row không khớp, quan hệ bậc đồ thị, mọi mã verified có bằng chứng. Kiểm lookup với ca biên và ca mơ hồ. Nếu sửa logic trong `src/`/pipeline, agent phải cập nhật kiểm thử hồi quy theo `AGENTS.md`; báo kết quả kiểm chứng riêng khi triển khai, không coi tài liệu kế hoạch này là đã chạy test.
2. Tạo `gazetteer_v2_approval.md` nêu source register, hash, coverage theo mã cũ/mới, số mã `verified/candidate/missing/conflict`, 5 chuyển đổi cấp huyện, giới hạn tọa độ/hình học và quyết định release. Cập nhật `docs/data_quality.md`, `README.md`, Sprint 3 README theo số thực. Không đổi v1; mọi sửa sau phát hành tạo v3 hoặc erratum versioned.
3. Trạng thái release phải trung thực: `READY_VERIFIED` chỉ khi cổng nguồn/mã cần thiết đạt; nếu mã cũ vẫn chưa có nguồn chính thức, `PARTIAL_OLD_CODES_UNVERIFIED`. Gói partial vẫn có thể cấp tên/alias/candidate/transition cho HEUR-JW nhưng baseline phải báo coverage và abstain, không gọi mã candidate là mã chuẩn.

**Đạt khi:** manifest/hash và báo cáo coverage đầy đủ, không có lỗi cấu trúc, trạng thái xác minh khớp bằng chứng; các lỗ hổng còn lại được liệt kê.

## 4. Đầu ra cuối cùng và phần cần người tham gia

| Ưu tiên | Agent có thể giao | Chủ dự án/người gán cần làm |
| --- | --- | --- |
| **2 — Corpus** | Protocol và snapshot; batch 02 import; export/QA/canonical; train/dev/test JSONL; split/leakage report; manifest/hashes; tài liệu số liệu thật | Chốt protocol trước test; gán hoặc giao người gán và rà lại mẫu batch 02 cùng 100 test; quyết định ca khó; xác nhận phát hành gold. 68 pilot **không cần gán lại**. Nếu một người gán, agreement liên người là `NOT_MEASURED`. |
| **3 — Gazetteer** | Audit v1; source register; gói v2 entity/edge/alias/non-atomic/lookup; coverage report, manifest và trạng thái mã | Khi thiếu nguồn mã cũ chính thức: cung cấp/chốt nguồn và quyền dùng cụ thể. Duyệt các ca mã/khóa mâu thuẫn nếu cần. Không phải gán span trong Label Studio cho gazetteer. |

Không cần can thiệp vào việc viết script, tính hash, chọn mẫu theo protocol hay build CSV nếu agent có quyền làm trong repo. Cần con người xác nhận **nội dung gold** và **bằng chứng mã hành chính**; agent không tự phán quyết thay. Nếu chủ dự án chưa có nguồn mã cũ, agent vẫn phải hoàn thiện audit/lookup/coverage và công bố v2 ở trạng thái partial, không dừng corpus.

## 5. Mẫu báo cáo tiến độ và prompt giao việc

Mỗi lần báo tiến độ, agent phải ghi: `C2.1–C2.6` và `G3.1–G3.5` đạt/chưa đạt/bị chặn; counts thực tế; số ca cần duyệt; đường dẫn output; SHA-256; lý do hold; bước tiếp theo. Khi gặp thiếu nguồn/WSL/Label Studio, tiếp tục việc độc lập và báo chính xác đầu vào cần chủ dự án cung cấp.

**Prompt có thể đưa nguyên văn cho agent khác:**

> Hãy triển khai theo `docs/sprints/sprint_03/05_s3_04_s3_03_agent_execution_plan.md`, chỉ gồm ưu tiên 2 S3-04 (corpus gold và split) và ưu tiên 3 S3-03 (gazetteer đa phiên bản). Đọc `AGENTS.md`, manifest pilot gold, guideline v1.1, batch 01, gazetteer v1, các script 10/11/13 và `docs/data_quality.md` trước khi sửa. Chủ dự án tạm hoãn dữ liệu thật cho `MocDinhVi`/`HuongDi`; không làm Data 05 quan sát và không đưa VQA vào corpus. Bảo toàn pilot gold 68, test hold 100, benchmark và gazetteer v1. Tạo batch/gold/split mới có provenance, kiểm rò rỉ, QA và duyệt người; test task chỉ gồm sample_id/text. Tạo gazetteer v2 từ nguồn chứng minh được, tách mã cũ candidate khỏi official, giữ quan hệ nhiều đích và 5 chuyển đổi phi nguyên tử. Nếu cần danh mục mã cũ chính thức ngoài repo, chuẩn bị hồ sơ nguồn cụ thể để chủ dự án chốt; không tự suy mã. Không tự ký `APPROVED_GOLD` hoặc gọi gói partial là verified. Giao file, manifest/hash, counts, giới hạn và danh sách việc cần người duyệt theo cổng C2.1–C2.6/G3.1–G3.5. Không cài dependency mới, không sửa data/raw, third_party hoặc các artifact đã khóa. Khi thay logic, thực hiện các kiểm chứng được AGENTS.md yêu cầu và báo kết quả thật.
