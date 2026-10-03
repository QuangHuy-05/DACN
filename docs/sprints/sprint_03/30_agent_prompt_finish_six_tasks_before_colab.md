# Prompt bàn giao: hoàn tất 6 việc trước thực nghiệm Colab và nghiệm thu test 100

Ngày soạn: **03/10/2026**. Đây là yêu cầu hiện thực dành cho agent tiếp theo. Việc tạo file prompt này không phải bằng chứng rằng sáu nhiệm vụ đã được thực hiện.

## Cách giao việc

Gửi agent đoạn sau và bảo đảm agent dùng workspace có đầy đủ mã, cấu hình và artifact hiện hành:

```text
Bạn là Senior AI/Data Engineer phụ trách hoàn tất sáu nhiệm vụ chuẩn bị của Sprint 3 trong repository DACN.
Đọc toàn bộ docs/sprints/sprint_03/30_agent_prompt_finish_six_tasks_before_colab.md.
Thực hiện đầy đủ phần PROMPT bên dưới, từ P0 đến U6: hiện thực mã, chạy baseline nhẹ trên dev, kiểm thử, kiểm tra artifact và bàn giao GitHub theo phạm vi đã quy định.
Chưa huấn luyện neural, chưa chạy Colab và chưa mở nội dung 100 test trong lượt này.
Cuối lượt, báo cáo trong chat kết quả từng U1–U6, nguồn đã lấy, package đã cài, GB/GiB thực đo, commit/nhánh/remote và thao tác chủ dự án còn cần làm.
```

Nếu chạy từ một clone mới, đọc mục U6: mã và dữ liệu chuẩn bị hiện có nhiều file chưa commit, còn artifact `data/interim/` bị Git ignore. Thiếu file phải được báo là thiếu đầu vào; không lấy báo cáo lịch sử để suy ra đã có tài nguyên.

---

# PROMPT

## A. Vai trò, mục tiêu và phạm vi

Bạn là Senior AI/Data Engineer trong repository DACN. Hoàn thành sáu nhiệm vụ:

1. **U1:** lấy nguồn chính thức theo ngày và xác minh mã hành chính cũ.
2. **U2:** phát hành Gazetteer mới có bằng chứng theo thời điểm và lookup đúng phạm vi.
3. **U3:** hoàn chỉnh provenance, giấy phép, resource lock và gói cấu hình chuẩn bị chạy model.
4. **U4:** cải thiện và thực nghiệm HEUR-JW/CRF-INDEP trên dev bằng run mới.
5. **U5:** nghiệm thu mã, dữ liệu, artifact, tính tái lập và bất biến.
6. **U6:** cập nhật tài liệu, chuẩn bị gói Label Studio/Colab và commit/push lên GitHub.

Chủ dự án yêu cầu thực hiện cả U4 trong lượt này. Nhiệm vụ U4 được giới hạn ở baseline nhẹ; không dùng việc cải thiện baseline để mở thêm huấn luyện neural hoặc tăng search không kiểm soát.

Kết quả cần giúp chủ dự án thực hiện hai luồng tiếp theo:

- Partner tiếp tục gán mù đúng 100 test bằng gói đã khóa.
- Chủ dự án mở Colab, kiểm tài nguyên và chạy thực nghiệm neural trong một lượt riêng.

**Trong lượt hiện tại:** được lấy danh mục hành chính công khai đã chỉ rõ, cài dependency cần thiết theo inventory, chạy kiểm thử/preflight và train CRF độc lập trên 240 train. Không mở phiên Colab, train PhoBERT/Deepparse/proposed, tải full FastText trên máy thiếu RAM, nhập prediction cho test hoặc chấm test cuối.

VQA giữ `HOLD`; dữ liệu thật có mốc/hướng giữ `DEFERRED_BY_USER`. Không mở lại các công việc thu địa chỉ mới, LLM/RAG, FastAPI, Docker, T3 hoặc thay đổi thiết kế nghiên cứu ngoài sáu nhiệm vụ.

## B. Đọc trước và xác định trạng thái hiện hành

Đọc nội dung thực tế của các file, kiểm hash và ưu tiên artifact đã phát hành cùng báo cáo mới nhất:

- `AGENTS.md`, `README.md`, `docs/data_quality.md`.
- `docs/sprints/sprint_03/README.md`.
- `docs/sprints/sprint_03/model_matrix.md`.
- `docs/sprints/sprint_03/span_11_annotation_guideline.md`.
- `docs/sprints/sprint_03/13_tasks_01_04_completion_20261002.md`.
- `docs/sprints/sprint_03/15_baseline_experiments_20261002.md`.
- `docs/sprints/sprint_03/17_training_protocol_v1.md` và `configs/modeling/sprint03/protocol_lock_v1.json`.
- Báo cáo `23_task_01_06_install_inventory_20261003.md`, `24_source_reconciliation_followup_20261003.md`, `25_frozen_baseline_error_analysis_20261003.md`, `26_local_neural_install_and_integration_20261003.md`, `27_tasks_01_06_completion_20261003.md`.
- **Hai báo cáo hiện hành:** `28_phobert_alignment_tone_relocation_20261003.md`, `29_nso_official_snapshot_gazetteer_release_20261003.md`.
- `data/processed/annotation/sprint03/corpus_train_dev_v2/{manifest.json,coverage.json}`.
- `data/processed/gazetteer/s3_v3_nso_2025_snapshot/manifest.json`.
- `configs/modeling/sprint03/gazetteer_source_register_v1.json` và các resource lock thực có trong interim.
- `src/data/{administrative_code_verifier,nso_gazetteer_release,source_reconciliation}.py`.
- `src/evaluation/`, `src/modeling/`, scripts `23`–`39` liên quan và tests tương ứng.
- Chỉ đọc tài liệu/schema/manifest của `docs/sprints/sprint_03/annotation_handoff/test100_v1/`; không phân tích text từng task test.

Trạng thái xuất phát cần kiểm lại, không diễn giải báo cáo cũ thành blocker mới:

| Thành phần | Trạng thái đã biết |
| --- | --- |
| Corpus | 240 train / 60 dev, 1.057 / 284 span; `TRAIN_DEV_APPROVED_TEST_PENDING` |
| Schema | `s3-span-v1.1`; BIO23 = `O` + B/I cho 11 nhãn |
| Ngoại lệ | Task 543, `s3_60931c369cbd85ef`: giữ T0, mask T1/consistency/chẩn đoán dùng T1 theo manifest |
| T1 đủ điều kiện | 206 train / 53 dev; phải tái kiểm từ policy trong manifest |
| PhoBERT alignment | Full tokenizer + VnCoreNLP đã đạt 300/300; 29 ca đổi vị trí dấu đã khôi phục |
| Runtime neural local | Python 3.11.16, Torch CPU 2.8.0, Transformers 4.57.1, Deepparse 0.11.0, Poutyne 1.17.4, py-vncorenlp 0.1.4; resources đã cài trên D |
| Neural experiments | Chưa train/chưa có prediction hoặc metric benchmark neural; forward thử không phải kết quả thực nghiệm |
| HEUR-JW / CRF | Có run dev frozen, F1 T0 lần lượt 88,01% / 89,82%; chỉ dùng làm mốc dev |
| Gazetteer v3 | 3.355 mã mới đã xác minh ở snapshot 01/07/2025; mã cũ còn unverified |
| Test100 | Partner gán mù; `TEST_PENDING`, chưa được dùng trong lượt này |
| Nhãn hiếm dev | 0 `MocDinhVi`, 0 `ToaNha/CanHo`, 1 `HuongDi` |

Hash corpus manifest đã báo: `9c91b77fa220e41b1b1067e5e99b216b7b4b2176181674b340f16dec134947bf`. Hash Gazetteer v3 manifest đã báo: `d838720b32c338dfc79ab37542519cf6a2f315f9a7602a6d5ba1753e7f7921fe`. Nếu hash thực tế khác, xác định nguyên nhân và phiên bản trước khi xử lý; không sửa bytes để ép khớp.

## C. Quyền và bất biến

### C1. Cài/tải tài nguyên

Chủ dự án đã cho phép cài/tải những thành phần cần thiết sau khi ghi inventory. Tại máy local, mọi package, venv mới, model, wheel cache, download cache, Java, temp và dữ liệu nguồn tải thêm phải nằm trên **ổ D**, ưu tiên dưới `D:/DACN/data/interim/modeling/sprint03/`.

- Kiểm kê package đã có, tái sử dụng runtime phù hợp; không cài lại một stack đã hoạt động.
- Inventory trước cài ghi tên/version/source URL/license/bytes ước tính/đích/mục đích; chỉ cài đúng danh sách đã ghi.
- Không cài vào C, home WSL, env hiện hữu hoặc cấu hình toàn máy. Dùng biến cache/temp cho process và `bash --noprofile --norc` khi gọi WSL.
- Không dùng Windows venv từ WSL; không chuyển sang Python khác để lách gate.
- Không tải full embedding khi RAM/đĩa không đủ. Metadata, tài liệu và manifest có thể được nghiên cứu trước; thiếu file thật phải giữ pending.
- Nếu WSL bị từ chối, tiếp tục code/read-only/static/focused checks trong runtime được phép; báo chính xác lệnh bị chặn. Không gọi kiểm tra Windows là tích hợp WSL đã qua.

### C2. Dữ liệu và run

- Giữ nguyên raw, third_party, export Label Studio, canonical gold, corpus, split, assignment, guideline đã khóa và 100 ID/text test.
- Giữ nguyên `s3_v1`, `s3_v2`, `s3_v3_nso_2025_snapshot`, baseline v2/v3 và mọi run hiện có khi bắt đầu lượt này.
- Mỗi release/run/evidence mới dùng đường dẫn mới; từ chối ghi đè. Có thể dùng suffix v2/v3 nếu tên đề xuất đã tồn tại.
- Input inference chỉ là `sample_id`/`text` và tài nguyên cấu hình. Không nhận `GT_*`, `HeQuyChieu`, `KieuThieu`, `Span_He_Detail`, nhãn T0/T1 hoặc source stratum gold.
- Lưu/freeze prediction trước khi scorer đọc gold. Gold chỉ dùng đúng vai trò train/scoring/phân tích dev; không đưa vào adapter.
- Offset là `[start,end)` trên text nguyên bản, phải khớp `text[start:end]`; không sửa text để hợp prediction.
- Metadata hold chỉ phục vụ anti-leakage trong runner hiện hữu: ID/source row/hash; không dùng các hàng bị loại làm ví dụ, feature, threshold, prompt hay debug. Nếu runner kiểm text hash để xác nhận hàng loại, giới hạn thao tác ở kiểm toàn vẹn nội bộ, không xuất text/nhãn của hàng hold.
- Không tự nâng `UNKNOWN` về giấy phép, `candidate` về mã chính thức hoặc `READY_FOR_HUMAN_REVIEW` về gold.

### C3. Thay đổi cấu hình

Giữ ngân sách, schema, split, seed, cách chọn checkpoint và ablation đã chốt. Hardware profile/đường dẫn portable phải được version hóa riêng nếu cần, giữ bản lock cũ và cập nhật đầy đủ reader/tests. Không tự giảm ngân sách đĩa/RAM, bật AMP, thay tokenizer, sửa loss hoặc đổi embedding để vượt gate.

## P0. Kiểm kê đầu vào và đóng băng trạng thái trước sửa

1. Ghi `git status`, branch/HEAD/remotes và danh sách dirty/untracked. Không reset, clean, stash hoặc xóa thay đổi có trước.
2. Lập ledger hash corpus, các Gazetteer frozen, run frozen, bảng mapping, configs/protocol và gói test-only. Có thể hash bytes file test để kiểm bất biến; không giải mã nội dung task.
3. Kiểm runtime chính/CRF/neural trên D, RAM available, đĩa trống, GPU nếu có. Số từ báo cáo cũ chỉ là lịch sử.
4. Kiểm resource files và prepared derivatives thực có. Nhận diện những file một clone GitHub mới sẽ thiếu.
5. Tạo evidence root mới, ví dụ `data/interim/modeling/sprint03/pre_colab_20261003_v1/`, ghi kế hoạch thao tác và inventory ban đầu ở đó.
6. Thứ tự phụ thuộc: **P0 → U1 → U2 → U4 → U5 → U6**; U3 được làm độc lập và phải hoàn tất trước U5/U6.

Đầu ra: `initial_state.json`, `frozen_before.json`, `input_availability.json`, inventory trước cài và danh sách blocker ban đầu.

## U1 — Lấy nguồn chính thức và xác minh mã cũ

### U1.1. Nguồn ưu tiên và kiểm tra thực tế

Nguồn chính thức đã được kiểm tra đọc thành công trước khi viết prompt:

- Service: `https://danhmuchanhchinh.nso.gov.vn/DMDVHC.asmx`.
- Operation docs: `?op=DanhMucTinh`, `?op=DanhMucQuanHuyen`, `?op=DanhMucPhuongXa`.
- Hướng dẫn cổng: `https://danhmuchanhchinh.nso.gov.vn/HDSD_DMHC_Web.htm`.
- Nguồn đối chiếu cộng đồng: tag `v2.4.1` của `https://github.com/thanglequoc/vietnamese-provinces-database`.
- Nguồn bên thứ ba đã có: `third_party/vietnamadminunits/` và hai CSV `data/raw/danhmuchanhchinh.gso.gov.vn_{ward,district}_2025-07-18.csv` bên trong clone đó; đọc-only.

SOAP namespace là `http://tempuri.org/`. Request dùng `Content-Type: text/xml; charset=utf-8`, `SOAPAction: "http://tempuri.org/<operation>"` và `POST /DMDVHC.asmx`.

Ví dụ body cho xã, không có thông tin cá nhân:

```xml
<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <DanhMucPhuongXa xmlns="http://tempuri.org/">
      <DenNgay>30/06/2025</DenNgay>
      <Tinh></Tinh><TenTinh></TenTinh>
      <QuanHuyen></QuanHuyen><TenQuanHuyen></TenQuanHuyen>
    </DanhMucPhuongXa>
  </soap:Body>
</soap:Envelope>
```

`DanhMucTinh` nhận `DenNgay`; `DanhMucQuanHuyen` nhận thêm `Tinh`, `TenTinh`. Kiểm operation docs trước khi gọi, dùng timeout/retry hữu hạn, kiểm HTTP/XML/Fault và giới hạn response size. Không thực hiện request cập nhật lên cổng.

Kết quả probe ngày 03/10/2026 để đối chiếu, **không phải chỉ tiêu buộc nguồn phải khớp**:

- API ngày 30/06/2025: **63 tỉnh / 686 huyện / 9.843 xã**, response toàn quốc.
- Tag GitHub v2.4.1: **63 tỉnh / 696 huyện / 10.035 xã**.
- Hà Nội qua API: ngày 30/06/2025 có **526 xã**, ngày 01/07/2025 có **126 xã**; danh mục và tên/mã thay đổi đúng theo ngày.

Agent phải truy xuất lại, lưu bằng chứng và kiểm phạm vi/các bộ lọc. Nếu số khác: kiểm response đầy đủ, phân trang, thời điểm, schema và sự điều chỉnh của nguồn. Không tự bổ sung 10 huyện/192 xã để ép counts, không coi chênh số lượng là đủ chứng minh đơn vị đã bị xóa.

### U1.2. Hiện thực thu nhận và canonical reference

1. Tạo client/CLI lấy ba danh mục ở `30/06/2025`; kiểm date control ở `01/07/2025` bằng danh mục hoặc mẫu ngoài corpus/test.
2. Lưu nguyên response XML và request parameters; manifest ghi source URL, operation, query, thời điểm truy xuất có timezone, HTTP status, bytes, SHA-256, scope, bộ lọc và trạng thái license.
3. Parse đúng các row `TABLE` trong diffgram/data, không parse các `xs:element` của schema thành dữ liệu. Bắt SOAP Fault, response rỗng, duplicate key/code và mã/cha thiếu.
4. Giữ mã dưới dạng chuỗi với zero đầu. Kiểm format tỉnh/huyện/xã và liên kết cha; không ép số rồi tự pad lại mã mất zero để gọi là bằng chứng gốc.
5. Tạo reference riêng có: `level`, `system`, tên nguyên văn, `official_code`, mã/tên cha đầy đủ, `as_of_date`, `source_id`, `source_hash`, locator tới row XML, extraction/validation status.
6. Query date chỉ chứng minh snapshot tại ngày đó. Không biến ngày truy vấn thành `valid_from` pháp lý; lịch sử hiệu lực chưa đủ phải thể hiện riêng.
7. Kiểm version/tag/commit, license và hash JSON cộng đồng nếu tải để đối chiếu. Phân biệt nguồn có thẩm quyền với bản cộng đồng dẫn nguồn nhà nước.

### U1.3. Reconciliation bảo thủ

Đối chiếu toàn bộ entity cũ, không chỉ 615 ca trong báo cáo 24. Tái dùng schema/verifier hiện có khi phù hợp.

- Province key: loại + tên tỉnh, hệ, ngày.
- District key: tỉnh + loại/tên huyện, hệ, ngày.
- Ward key: tỉnh + huyện + loại/tên xã, hệ, ngày.
- Exact full key + mã + cha + snapshot đủ bằng chứng mới được xác nhận. Nếu entity chưa có mã nhưng exact key duy nhất trong nguồn chính thức, có thể cấp mã cho **bản dẫn xuất mới** với trace đầy đủ.
- Mã candidate trùng hoặc tên giống chỉ tạo ứng viên để kiểm. Accent folding/Jaro-Winkler/cách đặt dấu chỉ phục vụ diagnostics; không tự promote identity hoặc sinh alias.
- Khác tên/cấp/cha cần bằng chứng hành chính riêng hoặc alias đã audit. Bảo lưu literal/canonical, lý do và nguồn; không sửa tên nguồn/corpus để tạo exact match.
- Không thấy đơn vị ở một snapshot: ghi `NO_REFERENCE_AS_OF` hoặc trạng thái tương đương; chỉ kết luận retirement/rename/reparent khi có bằng chứng xác định.
- Phân biệt rõ mã trùng ở hai thời kỳ nhưng chỉ tới hai thực thể khác nhau, ví dụ mã cũ/mới cùng số. Khóa định danh không được chỉ là mã.
- Các 5 huyện thiếu mã, 584 xã/26 huyện chưa exact ở audit trước phải có kết quả mới hoặc lý do vẫn unresolved.

**Đầu ra U1:** download manifest + XML, reference CSV/JSONL, reference manifest, reconciliation toàn bộ, diff NSO–GitHub, queue unresolved có reason/evidence, counts theo cấp/hệ/trạng thái, báo cáo nguồn.

**Nghiệm thu U1:** mỗi mã được xác minh truy tới source row + hash + ngày + cha; không có fuzzy promotion; mỗi ca unresolved có lý do. API lỗi hoặc nguồn không đủ thì phát hành báo cáo blocker, tiếp tục phần độc lập; không ghi số xác minh giả.

## U2 — Gazetteer dẫn xuất mới và lookup theo ngày

1. Dùng `s3_v3_nso_2025_snapshot` làm parent; dựng candidate trong interim trước. Nếu đủ bằng chứng cho một phần mã cũ, phát hành gói mới, ví dụ `data/processed/gazetteer/s3_v4_nso_dual_snapshot/`.
2. Giữ graph, entity ID, canonical names, alias đã audit và toàn bộ cạnh cũ/mới hiện có. Nếu cần thay graph do bằng chứng mới, tách đề xuất riêng; không tự sửa graph trong lượt xác minh mã này.
3. Nâng code status chỉ cho những entity đã vượt U1; giữ candidate/unverified/missing cho phần còn lại. Không đổi toàn package thành verified khi còn gap.
4. Gazetteer v3 chỉ có scope 01/07/2025. Thiết kế manifest/evidence để hỗ trợ **hai snapshot** 30/06/2025 và 01/07/2025; reader phải hiểu scope theo system/entity. Không đặt một ngày package chung rồi vô tình từ chối tất cả lookup cũ hoặc xác nhận mã cũ ở ngày mới.
5. Tách dữ liệu `verified_as_of` khỏi interval pháp lý. Hỗ trợ lookup tại ngày được chứng minh; ngày ngoài scope trả candidate/unknown/reject kèm lý do. Chỉ dùng interval rộng khi có nguồn lịch sử chứng minh interval đó.
6. Lookup đầu vào tối thiểu: name, level, system hoặc policy, reference date, cha khi có. Đầu ra: entity/candidates, code, code status, temporal scope, parent, source locator/hash, ambiguity/reject reason.
7. Thiếu huyện trong text không chứng minh hệ mới; `QuanHuyen` thuộc hệ cũ; tên cùng tồn tại ở hai hệ không được suy T1 từ tên đơn lẻ.
8. Giữ tất cả đích của A/1-N và M/M-N; 5 cạnh huyện→đặc khu là non-atomic. Không áp dụng default ward/nearest centroid của thư viện ngoài để tạo một đáp án chắc chắn.
9. Kiểm nhiều cấp/cha trùng tên, leading zero, hai snapshot, ngoài snapshot, mã tái dùng, huyện chưa mã, non-atomic và nhiều đích. Unit fixtures phải là dữ liệu tự soạn, không lấy test100.
10. Build mới phải từ chối ghi đè, có candidate QA rồi mới publish atomic; manifest hash input/code/output/reference/parent và báo diff so với v3.

**Đầu ra U2:** schema/reader/build CLI, package mới nếu qua gate, code evidence, source register, coverage/diff và lookup examples. Nếu không phát hành: candidate và gap report đủ để tái lập, giữ các gói frozen.

**Nghiệm thu U2:** package không mất đích/alias/entity; new verified có U1 evidence; lookup không vượt scope; chưa đủ evidence vẫn thể hiện partial. So sánh graph counts với parent và giải thích mọi khác biệt.

## U3 — Hồ sơ nguồn, resource lock và cấu hình Colab

### U3.1. Hồ sơ cần hoàn thiện

Lập registry riêng cho: hai CSV ward/district bên thứ ba, CSV ánh xạ `vietnam-sap-nhap-phuong-xa.csv`, reference NSO mới, Deepparse checkpoint, full FastText embedding, PhoBERT, tokenizer, VnCoreNLP, Java và runtime packages.

Mỗi mục ghi tên/role, URL cụ thể, cơ quan hoặc tác giả, revision/version/commit, ngày truy xuất, license URL/text và scope, input/output hash khi có file, bytes, target path, trạng thái local/remote, điều kiện dùng/phân phối, blocker.

- License code Deepparse không tự chứng minh license weights/embedding.
- MIT của repo ngoài không tự chứng minh quyền dùng mọi CSV gốc.
- HTTP 200/URL cổng chính thức không tự chứng minh thời kỳ hoặc quyền tái phân phối.
- Giữ `UNKNOWN`/`PUBLIC_PORTAL_TERMS_NOT_LOCATED` khi không tìm được điều khoản. Phân biệt code validity, quyền dùng nội bộ và quyền tái phân phối artifact.
- Xác định **đúng embedding/checkpoint native Deepparse FastText** từ package 0.11.0/source chính thức; không thay bằng FastText tiếng Việt, compressed embedding hoặc model khác mà vẫn dùng cùng model ID.

### U3.2. Khóa tài nguyên và preflight

1. Tái kiểm resources PhoBERT đã tải: revision `01daacda68afe13d83023d16ec647239e344a1e6`; VnCoreNLP commit `62bbc58fe5d113c898eae112656be97dcf50b3a0`. Không tải lại nếu hash/metadata đúng.
2. Resource lock local chỉ chứa files thật đã có và hash thực đo. Nếu chưa tải full FastText, tạo **download recipe/prospective lock** riêng; không đưa hash giả hoặc trạng thái `CLEARED_AND_AVAILABLE` vào lock hoạt động.
3. Phân biệt SHA-256 thực đo local với checksum dự kiến do upstream công bố, URL có revision và metadata chưa đủ immutable identity. Recipe phải kiểm local bytes/hash sau tải trước model load.
4. Theo preflight hiện hành, full FastText cần tối thiểu **10 GiB RAM hệ thống còn khả dụng**; PhoBERT training dự phòng **20 GiB đĩa/run**, Deepparse **3 GiB đĩa/run** sau khi đã có resources. Đo lại và báo cả phần tải/cache/checkpoint để không nhầm dự phòng với tổng cần dùng.
5. Trạng thái chuẩn bị được phép hoàn thành dù thiếu tài nguyên local. Preflight thiếu RAM/đĩa/weights phải exit có lỗi rõ, không instantiate parser tự download hoặc giảm gate.
6. Chuẩn bị requirements CPU local và profile Colab riêng. Runtime local hiện có Torch CPU; phải chuẩn bị cấu hình riêng khi dùng CUDA. Kiểm khả năng tương thích theo tài liệu chính thức và pin trước khi viết lệnh Colab; không mặc định GPU/CUDA/Python Colab có phiên bản cố định.
7. Python hiện khóa ở phiên bản 3.11; notebook phải kiểm runtime thực tế và tạo môi trường Python 3.11 riêng nếu cần. Không sửa target version âm thầm vì Colab default khác.
8. Nếu cần đổi `device`/runtime/path cho GPU, thiết kế profile cùng lock mới và reader có tests; giữ protocol/candidate budget/seed/processor/loss đã chốt. Ghi sự khác biệt có chủ đích, giữ profile CPU cũ.

### U3.3. Dung lượng và lệnh bàn giao

- Chốt registry + resource locks/recipes + exact CLI cho preflight/train/infer/score/audit/resume của DP-ZS-FT, DP-FT-FT, PHOBERT-CRF, PROPOSED-DYN và ablation.
- Lệnh future training phải được ghi là **chưa chạy**; tên/path checkpoint dự kiến không được trình bày thành artifact đã tồn tại.
- Resume PhoBERT gồm optimizer/scheduler/RNG và vào run mới; DP weights-only không được gọi optimizer resume.
- Giữ c01/c02, tối đa 20 epoch, patience 5, seed 42, effective batch 16; ablation constraint on/off từ **cùng checkpoint**; calibration T1 chỉ trên dev theo grid đã khóa.
- Đo package/cache/resources mới theo logical bytes không đếm trùng/symlink/hardlink; đo dung lượng trống ổ D trước/sau riêng. Báo GB (`bytes/10^9`) và GiB (`bytes/2^30`). Tách tổng mới của lượt này khỏi tổng cài cũ 2,453588804 GB; tổng cũ cần kiểm chứng bằng accounting, không cộng chồng thư mục.
- Liệt kê package thực sự cài/tải và package chỉ định sẵn cho Colab. Nếu không cài thêm, ghi dung lượng cài mới bằng 0; tách dung lượng response/evidence nguồn khỏi dung lượng cài package/model.

**Nghiệm thu U3:** biết rõ model nào có resource lock hợp lệ, model nào chờ download/tài nguyên/giấy phép; không có placeholder được đưa qua gate. Lệnh chuẩn bị khớp CLI thật, CPU/GPU profile được khai báo và mức readiness đúng bằng chứng.

## U4 — Cải thiện HEUR-JW và CRF trên dev

### U4.1. Chốt phạm vi trước chạy

1. Đọc error taxonomy từ báo cáo 25 và raw trace frozen; lấy nhóm lỗi ranh giới đường–ngõ, prefix hành chính, label/cấp và phép chiếu 5 trường làm backlog.
2. Viết kế hoạch candidate trước các run mới: rule/features, tokenizer/projection version, Gazetteer/policy, grid, selection metric, tie-break, seed và giới hạn. Tái dùng grid đang có ở scripts 26/27 khi phù hợp; tính cả phiên bản rule và các lượt quét trong ngân sách tune.
3. Chọn tối đa **hai phiên bản rule/feature mới cho mỗi baseline**; tính toàn bộ sweep/grid đã khai báo trong bảng trial. Dừng sau search đã chốt; báo kết quả kể cả không cải thiện.
4. Dùng các phiên bản code/model riêng có config rõ. Frozen metrics là mốc lịch sử; nếu cần so tác động cùng môi trường/mã, tạo control run mới, không chạy ghi đè hoặc sửa metric cũ.

### U4.2. HEUR-JW

- Rule phải tổng quát, không hardcode sample_id, nguyên chuỗi dev, GT hoặc tag riêng cho một mẫu.
- Chuẩn hóa để so sánh được tách khỏi raw offset. Cấp/cha/ngày/alias/code status đều hiện trong candidate trace.
- `heur_config()` và script 27 đang nạp **s3_v2 cố định**: nếu dùng package mới, hiện thực tham số `gazetteer_dir`/policy/date scope và đưa đúng file hashes vào config; kiểm adapter, không chỉ thay tên trong báo cáo.
- Chỉ dùng hai snapshot theo policy khai báo, không chọn ngày/hệ từ T1 gold từng mẫu. T0 có thể trả span/cấp rõ khi ID vẫn mơ hồ; T1/code lookup phải abstain khi chưa đủ bằng chứng.
- Mã unverified không được xuất như official verified. Candidate đồng điểm cần reject/ambiguity trace.
- Lưu sweep precision/recall/coverage/exact-span F1; chọn operating point theo rule đã khai báo trên dev, không chốt bằng câu chuyện vài ví dụ thuận lợi.

### U4.3. CRF-INDEP

- Linear-chain CRF, BIO23, feature từ text và tài nguyên khai báo; không PhoBERT/Deepparse embeddings hoặc T1 head.
- Train chỉ `train.jsonl`; chọn feature/regularization chỉ trên dev, giữ 240 train / 60 dev và áp dụng mask khi làm các chẩn đoán T1 liên quan.
- Phiên bản tokenizer/BIO/feature/repair policy/checkpoint phải lưu; round-trip giữ raw offsets. Nếu bổ sung Gazetteer feature, chỉ dùng raw text và Gazetteer, không hệ gold.
- Không sửa gold để khiến tokenize/projection thuận lợi. Feature/rule dựa trên schema có thể sửa; input/data hashes phải giữ.

### U4.4. Scoring và phân tích

1. T0 dev dùng `dev_input.jsonl`; freeze prediction rồi gọi scorer với `dev.jsonl`.
2. Chấm đầy đủ 11 nhãn, báo `supported_labels`, P/R/F1/micro/macro/support, abstain, runtime errors, latency và raw span QA.
3. T1 chỉ báo khi adapter có T1; CRF ghi `NOT_IMPLEMENTED`. Mask task 543 khỏi T1 và các thống kê dùng gold T1; vẫn giữ T0.
4. Projection sang 5 trường phải cố định toàn cục, giữ tên loại/dấu/normalization policy theo track; span lặp/nhiều giá trị cần quy tắc và trace, không lấy gold chọn span.
5. Track 5 trường dùng runner hiện hành loại 100 hold, cùng dataset hashes và text-only mode. Mốc cũ 4.800 hàng thuộc tập 01/02/03/04/06 phải được tái kiểm. Không tune trên track 5 trường sau khi xem metric; configuration chọn từ dev trước.
6. Báo sai `QuanHuyen` trên mẫu có gold T1 = `moi` đủ điều kiện, recall quận trên `cu`/`Lai` và coverage. Không tuyên bố triệt tiêu hoàn toàn lỗi quận hoặc suy F1 nhãn không support từ một dev nhỏ.
7. So sánh before/after theo cùng track/mode/input hash. Phân tích boundary/label/missing/extra/projection; provenance sidecar chỉ để báo cáo, không thành feature.

**Đầu ra mỗi run U4:** raw predictions, model config, run/scoring manifest, metrics, error analysis, candidate/alignment/projection trace, input/resource/code/output hash, latency; CRF có checkpoint/training log/metadata/grid. Có chosen config và bảng so sánh riêng cho T0 dev và track 5 trường.

**Nghiệm thu U4:** có run thật của hai baseline nếu runtime cho phép; cải thiện là mục tiêu, không là điều kiện để được ghi kết quả. Không có cải thiện phải báo giữ mốc phù hợp. Nếu bị runtime block, hiện thực/test phần độc lập và ghi `NOT_RUN` cho thực nghiệm bị chặn.

## U5 — Nghiệm thu kỹ thuật

1. Thêm/cập nhật tests cho logic sửa. Thay logic `src/`/pipeline dữ liệu phải có regression trong `tests/test_data_pipeline.py` và test chuyên biệt khi cần.
2. Chạy full suite `python -m unittest discover -s tests -v` trong runtime dự án có dependencies; chạy suite neural trong runtime neural trên D và CRF trong runtime CRF. Ghi interpreter/command/log/exit/PASS/SKIP/FAIL/import error riêng, không cộng suite chồng lặp.
3. Kiểm corpus 300 mẫu / 1.341 span / BIO23 / mask T1 / processor version hiện hành. Alignment đã đạt 300/300: audit lại khi sửa processor/loader; không gán lại dữ liệu. Nếu không sửa, xác minh evidence/hash và prepared artifact hiện hành.
4. Kiểm hash output U1/U2/U3/U4; schema/encoding/count/duplicate/full parent/time scopes/multiple targets; các JSON/CSV/CLI cần có đầu vào bắt buộc và từ chối output trùng.
5. Audit các run mới: prediction ID đủ 60 dev, offset exact, status rõ, metrics gắn frozen prediction hash, configuration/resource/checkpoint thật. Model subset vẫn báo FN trên toàn schema theo scorer.
6. So ledger trước/sau. Gói v3 phải được thêm vào phạm vi kiểm bất biến vì `frozen_snapshot()` cũ chỉ nêu v1/v2; không coi omission là PASS cho v3.
7. Phân biệt **frozen artifact bytes** với **mã hiện tại đã thay đổi**. Run lịch sử có code hash khác mã mới không tự là tamper output; audit against code snapshot lưu theo run khi có. Nếu thiếu snapshot ghi khả năng tái lập lịch sử chưa xác minh; không sửa run manifest để khớp mã mới.
8. Kiểm protocol lock/label map/resource lock/portable root khi chuyển workspace. Đường dẫn trong lock là tương đối repo; không hardcode user home/drive letter trong code.
9. Checkpoint tests có thể dùng tiny fixture đã khai báo. Không gọi tiny fixture/pretrained short forward là benchmark metric hoặc proof native fullFastText đã chạy.
10. Lập `readiness.json` riêng: U1–U6 status/evidence/blocker/owner/action, readiness cho annotation handoff, Colab bootstrap, model preflight và training. Không sửa corpus manifest để ghi test approved hoặc training ready.

**Nghiệm thu U5:** tests phù hợp chạy và không có failure chưa giải thích; frozen ledger giữ nguyên; run mới audit qua. Import error/skip/resource pending phải hiện trong readiness, không báo toàn suite PASS khi còn lỗi.

## U6 — Tài liệu, Label Studio, Colab và GitHub

### U6.1. Tài liệu hiện hành

Cập nhật README, docs/data_quality, Sprint 3 README và AGENTS phần trạng thái theo evidence mới; giữ báo cáo lịch sử, ghi rõ trạng thái đã được thay thế. Cập nhật source register/license/coverage theo artifact thực; không sửa guideline/annotation protocol dựa trên dev errors.

Tạo báo cáo mới cho U1–U5 và hướng dẫn bàn giao, ví dụ:

- `docs/sprints/sprint_03/31_pre_colab_source_verification.md`.
- `32_temporal_gazetteer_release.md`.
- `33_pre_colab_resource_inventory.md`.
- `34_light_baseline_followup.md`.
- `35_pre_colab_acceptance.md`.
- `36_label100_and_colab_handoff.md`.

Tên có thể đổi nếu trùng, nhưng kết luận cuối phải link đúng file thật.

### U6.2. Gói partner gán 100 test

1. Gói `annotation_handoff/test100_v1` hiện đã có `test100_import.json`, XML, guideline, manifest và submission template. Kiểm bytes/hash, không mở lại text task và không sinh 100 ID mới.
2. Giữ mode `blind_manual_no_predictions`. Không cross-AI sinh đáp án 100 task, không nạp model predictions; đổi phương thức annotation chỉ thuộc yêu cầu riêng của chủ dự án.
3. Viết checklist từ mở Label Studio → tạo project → dán XML → import đúng 100 task → gán span/hệ/flags → Submit → export raw JSON → gửi biên bản. Dùng hướng dẫn hiện có, không tạo bản test mới chỉ vì cần cập nhật README.
4. Ghi đường dẫn nhận export tương lai riêng, ví dụ `data/interim/annotation/sprint03/exports/test/test_blind_round1_<reviewer>.json`.
5. Ghi cách QA/phán quyết/package trong lượt test sau, dùng scripts 17/18 theo `--help` hiện hành. Không chạy các lệnh trên test lúc này và không coi README/QA cấu trúc là human approval.
6. Test export không đưa vào bundle Colab train/dev. Hai luồng có thể tiếp tục độc lập; partner không phải chờ mã cũ hoàn tất mới bắt đầu gán test.

### U6.3. Gói chạy Colab

Tạo bundle/version dưới interim và code notebook/bootstrap được track tại vị trí phù hợp, ví dụ `notebooks/sprint03/preflight_and_train_dev.ipynb`. **Chỉ chuẩn bị notebook; chưa chạy Colab hoặc huấn luyện neural.**

Bundle phải có code/config/protocol snapshot, `train.jsonl`, `dev.jsonl`, `dev_input.jsonl`, manifest/coverage, label map/mask T1, alignment policy/source hashes, resource locks/recipes/license notes và hướng dẫn. Không copy Windows/WSL venv, toàn bộ `data/raw/`, text/gold của test, raw export Label Studio, token hoặc toàn cache model. Resource lớn chỉ kèm khi quyền phân phối rõ và dung lượng cho phép; ưu tiên recipe tải đúng revision vào runtime sau preflight.

Notebook cần các cell theo thứ tự:

1. Đọc README, phạm vi train/dev, model IDs và phần human phải thao tác.
2. Nhận bundle hoặc clone **commit đã pin**; kiểm checksum file và git/code identity. Chưa có commit remote thì ghi local bundle fallback rõ.
3. Inventory Python/OS/CPU/RAM hệ thống còn khả dụng/disk/GPU/VRAM/CUDA; không mặc định Colab luôn có GPU hoặc đủ RAM.
4. Chọn bootstrap Python 3.11 + package profile đã khai báo; cài đúng thành phần cần, không nâng env toàn phiên bừa bãi. Resource/caches nằm workspace runtime Colab, dùng đường dẫn tương đối workspace.
5. Resource download có revision/license/checksum và capacity gate trước tải; FastText gate đo **RAM hệ thống**, kiểm riêng VRAM cho model dùng GPU. Thiếu điều kiện thì dừng model đó và in blocker.
6. Kiểm corpus hash/count/split/mask T1, tokenizer/segmenter/raw offsets; chuẩn bị BIO bằng pipeline có sẵn.
7. Preflight từng model. Flag `ENABLE_NEURAL_TRAINING` mặc định false; train cell chỉ hoạt động khi chủ dự án mở lượt training và mọi gate qua.
8. Các cell future DP-ZS-FT, DP-FT-FT, PHOBERT-CRF, PROPOSED-DYN gọi **CLI của repo**, giữ config và candidate budgets. Không reimplement model riêng trong notebook/Gemini.
9. Freeze prediction dev → scorer riêng → calibration T1 trên dev → ablation từ cùng checkpoint → audit. Không có cell chấm 100 test trong notebook này.
10. Lưu artifact theo run mới; giữ best/last/optimizer/RNG cho PhoBERT, lưu manifest/checksum; DP khai báo weights-only resume. Hướng dẫn sao lưu theo chu kỳ ra nơi chủ dự án chọn vì runtime Colab có thể kết thúc; dùng copy rồi kiểm hash, không move/xóa bản nguồn.
11. Xuất kết quả/báo cáo dev/package tải về; notebook không chứa token, đường dẫn Drive cá nhân, output gold hoặc kết quả giả.

Kiểm JSON của notebook, cú pháp các cell code và mọi CLI/đường dẫn được viết. Không thực thi cell train/download/mount để kiểm cú pháp. Báo **notebook prepared, Colab runtime not executed**; chưa chạy thật thì không ghi Colab integration PASS.

Tham khảo [FAQ chính thức Colab](https://research.google.com/colaboratory/faq.html): tài nguyên không được bảo đảm, VM có thể bị xóa và file/runtime không tự đi cùng notebook chia sẻ. Agent kiểm lại tài liệu trước bàn giao; không hứa model chạy được chỉ vì notebook mở được.

### U6.4. Git và quyền cập nhật

Chủ dự án đã yêu cầu cập nhật GitHub. Trong prompt này, agent được commit/push các thay đổi Sprint 3 liên quan đã qua review vào repository của chủ dự án: `https://github.com/QuangHuy-05/DACN.git`.

- Nhánh code/bàn giao chính ưu tiên **`sprint3_huy`** đã được chủ dự án đặt tên. Nhánh **`print3_label100test`** là bàn giao test-only hiện có; giữ gói của partner ổn định. Không ép push code neural/Gazetteer mới vào nhánh test-only chỉ vì workspace đang ở nhánh đó.
- Kiểm branch/remote/history/identity và status thực tế; remote refs cũ không là bằng chứng push mới.
- Workspace có nhiều file modified/untracked của những lượt Sprint 3 trước. Không `git add .`, không xóa/revert/stash/switch làm mất thay đổi. Lập danh sách prerequisite cần đưa vào bản bàn giao để clone mới chạy được, giữ thay đổi không liên quan.
- Nếu checkout đang có thay đổi chưa commit trên nhánh partner: ưu tiên checkout/worktree phù hợp theo công cụ và AGENTS, chuyển snapshot file cần thiết có ledger. Worktree mới không tự có uncommitted changes; phải kiểm nội dung trước commit. Không cherry-pick/switch branch với giả định untracked code sẽ tự đi theo.
- Stage code/config/tests/docs và các dữ liệu đã được cho phép chia sẻ. Source evidence có quyền chưa rõ phải được ghi giới hạn; không tự đưa raw export/model weights lớn/venv/cache/interim lên Git public. Không sửa `.gitignore` để đưa tất cả interim vào.
- Partner/Colab cần file trong interim thì tạo gói chia sẻ riêng có manifest/hash; code trên Git đủ để tải nguồn/tái dựng khi được phép. Kiểm không thiếu module untracked hoặc files do `.gitignore` chặn.
- Rà diff, secrets, artifact sizes và smoke ở snapshot bàn giao trước commit. Không force-push, không rewrite lịch sử, không merge vào main hoặc tạo PR nếu chủ dự án chưa yêu cầu thao tác đó.
- Push nhánh đã chọn; kiểm `git ls-remote` đối chiếu SHA sau push. Nếu thiếu auth/quyền ghi hoặc auto-review từ chối, giữ commit local/bundle, báo chính xác action/reason và lệnh chủ dự án cần chạy; chỉ ghi đã lên GitHub khi xác minh được SHA trên remote.

**Nghiệm thu U6:** tài liệu và bundle mở được, đủ prerequisites; gói test giữ hash; notebook được kiểm ở mức chuẩn bị; GitHub SHA thực nhận được ghi rõ hoặc có blocker cụ thể. Chủ dự án biết file nào gửi partner, file nào dùng Colab và thao tác nào còn cần mình thực hiện.

## D. Kiểm tra kết thúc và báo cáo trong chat

Trước khi kết thúc, kiểm toàn bộ checklist:

- [ ] Corpus/split/gold/Gazetteer frozen/run/gói test giữ bytes/hash.
- [ ] U1 có nguồn thật, ngày/query/hash response/parent và counts; chênh lệch không bị bù hoặc đoán.
- [ ] U2 chỉ promote mã có bằng chứng; dual snapshot và multiple targets qua tests; còn gap thì partial.
- [ ] U3 phân biệt giấy phép code/data/weights, lock đã xác minh/recipe còn pending, CPU/GPU và cổng kiểm tài nguyên.
- [ ] U4 có thực nghiệm nhẹ thật hoặc blocker; grid/version/runs/scoring riêng và không dùng test.
- [ ] U5 có logs, full/focused tests, skip/import error và audit frozen trung thực.
- [ ] U6 có gói partner ổn định, notebook Colab đã chuẩn bị, lệnh tái lập, bundle manifest/hash và trạng thái commit/push.
- [ ] Không huấn luyện neural, tạo prediction benchmark neural hoặc chấm test 100 trong lượt này.
- [ ] Ghi package đã cài, đích trên D, bytes/GB/GiB mới và cumulative nếu có accounting đủ; tách dữ liệu tải và biến động toàn ổ.

Báo cáo chat phải tự đủ nội dung, theo bảng **U1–U6** gồm: trạng thái, đã làm, evidence/tests, còn thiếu, đường dẫn đầu ra. Tiếp theo báo:

1. Nguồn lấy từ đâu, truy vấn gì; mã cũ/mới xác minh được bao nhiêu, bao nhiêu còn chưa xác minh và vì sao.
2. Kết quả HEUR-JW/CRF mới so mốc frozen: T0 dev, track 5 trường, T1 khi có; số mẫu/coverage và giới hạn nhãn hiếm. Kết quả là dev, không phải test cuối.
3. Package/download mới và dung lượng thực đo. Không có cài thêm thì ghi dung lượng cài mới bằng 0.
4. Commit/branch/SHA trên remote nhận được và files/bundle ngoài Git.
5. **Danh sách việc chủ dự án thực sự cần làm:** partner gán 100 test/export/biên bản; nguồn/quyền dùng chỉ khi agent không tự xác minh được; chủ dự án mở Colab/chọn runtime/cấp quyền Drive nếu dùng/bật training khi mọi gate qua. Không yêu cầu gán lại 300 mẫu hoặc tự điền hàng nghìn mã.
6. Readiness riêng cho annotation handoff, preflight Colab và training từng model. Chuẩn bị hoàn tất không đồng nghĩa thực nghiệm neural/test/Sprint 3 đã hoàn tất.

Nếu blocker xuất hiện, hoàn thành các nhiệm vụ độc lập và các phần code/evidence còn làm được. Không dừng ở một kế hoạch mới, không tạo prediction/metric giả và không giấu blocker để báo đủ sáu việc.
