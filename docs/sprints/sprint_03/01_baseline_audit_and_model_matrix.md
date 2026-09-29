# Sprint 3 — Giao việc 01: kiểm toán baseline và chốt ma trận mô hình

**Ngày lập:** 25/09/2026

**Người nhận:** AI agent thực hiện Sprint 3

**Phạm vi lần giao này:** kiểm toán run có sẵn, chốt hợp đồng so sánh và thiết kế các cấu hình mô hình. Chưa chạy huấn luyện hoặc công bố kết quả mới.

**Trạng thái thực thi 25/09/2026:** đã hoàn tất kiểm toán theo [báo cáo](baseline_run_audit.md) và khóa [ma trận mô hình](model_matrix.md). `baseline_v3_fuzzy` đạt `PASS` trong phạm vi 5 trường/protocol của run; `baseline_v2` tiếp tục frozen, việc tái lập toàn bộ mã nguồn lịch sử là `UNVERIFIABLE` vì thiếu hai snapshot khớp hash. Phần tiền kiểm ở Mục 2 ghi lại trạng thái trước khi chạy kiểm toán đầy đủ.

## 1. Kết quả cần bàn giao

1. Báo cáo kiểm toán có bằng chứng máy đọc được và bản giải thích tiếng Việt cho `baseline_v2` và `baseline_v3_fuzzy`. Tách rõ tính toàn vẹn của **run lõi** (manifest, input, prediction, raw log) với tính toàn vẹn của **báo cáo dẫn xuất**.
2. Kết luận có điều kiện cho v3: `PASS`, `PASS_CORE_ONLY`, `FAIL` hoặc `UNVERIFIABLE`, nêu từng cổng kiểm tra và bằng chứng. Chỉ `PASS` mới cho phép ghi v3 là mốc baseline theo protocol fuzzy hiện hành. `baseline_v2` luôn là mốc lịch sử frozen; không ghi đè, không chấm lại bằng scorer v3 rồi gọi đó là kết quả v2.
3. Ma trận cấu hình đã khóa ID, đầu vào, nguồn dữ liệu, nhãn đầu ra, phương pháp huấn luyện, track đánh giá và giới hạn so sánh. Ma trận phải phân biệt **5 cấu hình baseline mới** với **1 mô hình đề xuất**. “4 baseline còn lại” trong kế hoạch cũ là cách nhóm công việc, không phải số cấu hình cuối cùng sau khi tách CRF.
4. Danh sách cổng dữ liệu và môi trường cần đạt trước khi agent sau triển khai huấn luyện: gold span 11 nhãn, tập train/dev/test khóa, quyền cài dependency và tài nguyên chạy.

Đầu ra đề nghị: `docs/sprints/sprint_03/baseline_run_audit.md`, `docs/sprints/sprint_03/model_matrix.md` và `docs/sprints/sprint_03/baseline_run_audit.json`. Script kiểm toán chỉ đọc có thể đặt tại `scripts/09_audit_baseline_runs.py`. Tên tệp được đề nghị để agent triển khai thống nhất; không đưa artifact kiểm toán vào thư mục run frozen.

## 2. Hiện trạng được quan sát để định hướng kiểm toán

- Run lõi nằm tại `data/processed/evaluation/runs/{baseline_v2,baseline_v3_fuzzy}/`. Cả hai manifest ghi `run_kind=full`, sáu tập 01/02/03/04/06/07 với **5.500 dòng**, mỗi run ghi **13.000** prediction và **13.000** raw response. Data 05 chưa có trong manifest.
- v2 có `manifest_version=3.0`, chưa có `scoring` fuzzy; v3 fuzzy có `manifest_version=4.0`, `scoring.protocol_version=2.0`, `fuzzy_similarity_method=normalized_levenshtein`. Dữ liệu đầu vào và bảng ánh xạ ghi trong hai manifest hiện cùng hash. Không vì thế mà coi hai protocol tương đương.
- Tiền kiểm chỉ đọc ngày 25/09/2026: SHA-256 và kích thước của sáu CSV benchmark, hash bảng ánh xạ, hai output hash đều khớp manifest ở cả hai run; mỗi run có 13.000 khóa `(ID,CongCu)` duy nhất và khớp 1–1 với `(id,tool)` raw log, chuỗi đầu vào khớp. Riêng v3 có đúng phân bố lượt theo runner, 13.000 raw status `success`, JSON trường dự đoán/gold đọc được với đủ năm khóa. Mười ba file dẫn xuất `v4_fuzzy` khớp lineage và `parent_manifest_sha256` khớp hash manifest v3; các code hash v3 hiện khớp working tree. Đây **chưa phải** xác nhận gold, mode và điểm số ở từng hàng.
- Code làm nguồn đối chiếu: `src/evaluation/{manifest.py,data_contract.py,protocol.py,scorer.py,run_artifacts.py}`, `scripts/{06_run_baseline_full.py,07_generate_baseline_report.py,08_generate_report_materials.py}`, `docs/VERSIONING.md`, `docs/data_quality.md`. Đọc file `AGENTS.md` thực tế trước khi sửa code.

## 3. Thứ tự thực hiện kiểm toán

### A0 — Ghi lại trạng thái và khóa phạm vi (khoảng 0,5 ngày)

**Làm:** ghi `git status --short`, đường dẫn tuyệt đối repo, ngày giờ, SHA-256 của hai `run_manifest.json`, tên run, version, `run_kind`, seed, Python và phiên bản tool. Kiểm kê đủ tệp lõi và tất cả tệp dẫn xuất mà lineage khai báo. Lưu trạng thái này trong báo cáo kiểm toán. Dùng file manifest đang tồn tại làm nguồn chứng cứ; không gọi `06_run_baseline_full.py` và không dùng tùy chọn `--overwrite` của bất kỳ generator nào.

**Vì sao:** working tree có thay đổi chưa commit; hash code hiện tại có thể trùng hoặc lệch code của một run lịch sử. Việc khác hash mã **không đồng nghĩa** output bị sửa, nhưng làm thay đổi mức độ có thể tái lập; phải ghi thành mục riêng. Nếu thiếu snapshot code cũ, kết luận `UNVERIFIABLE` cho khả năng tái lập thay vì suy đoán.

**Xong khi:** inventory liệt kê từng file cùng trạng thái tồn tại, kích thước và hash; v2 và v3 không bị chạm byte nào.

### A1 — Kiểm tra manifest và nguồn đóng băng (khoảng 0,5 ngày)

Đọc JSON với schema theo **version riêng của từng run**. Xác nhận `run_id` khớp tên thư mục, `run_kind=full`, seed hiện diện, đủ sáu tên trong `datasets`, mỗi mục có `row_count`, danh sách `columns`, `size_bytes`, `sha256`; `mapping_source` và `output_hashes`, `output_row_counts` đầy đủ. V3 phải khai báo scoring version, công thức fuzzy, normalization, empty policy và quy tắc Data 07. V2 không bị đánh trượt vì thiếu các khóa chỉ xuất hiện ở manifest v4.

Với từng CSV: so SHA-256 byte-for-byte, kích thước, thứ tự cột, số dòng và UTF-8 BOM với manifest. Đối chiếu mapping source như vậy; sau đó gọi hoặc tái hiện logic `validate_benchmarks()` để phát hiện lỗi ngữ nghĩa dataset. Nếu CSV hiện tại khác hash đã đóng băng, **không** dùng nó để tự khẳng định run cũ sai; ghi thiếu input frozen và xếp `UNVERIFIABLE` cho bước phụ thuộc input, trừ khi tìm được bản snapshot đúng hash.

**Xong khi:** bảng 6 dòng input + 1 dòng mapping cho mỗi run, mỗi dòng có expected/actual hash, byte, rows, columns, verdict. Không có phép sửa CSV nguồn.

### A2 — Kiểm tra output, cặp prediction–raw và độ phủ (khoảng 1 ngày)

So hai output SHA-256 và số dòng với manifest. Prediction phải có đúng chín cột theo `UNIFIED_SCHEMA_COLUMNS`, BOM UTF-8; raw log phải là JSONL hợp lệ, một object mỗi dòng. Khóa `(ID,CongCu)` của prediction và `(id,tool)` của raw phải duy nhất, bằng nhau như tập hợp và có cùng `DiaChiGoc/input`, `DungSai/dung_sai`, `LoaiLoi/loai_loi`, `TinhHuongMoHo/scenario`. Parse `TruongDuDoan` và `TruongDung`: đều có đúng năm trường chuẩn, giá trị chuỗi; ghi số exception, trường rỗng, `duration_ms` âm hoặc thiếu. Exception nếu có phải được báo cáo theo tool/tập, không được biến mất khỏi mẫu số.

Đối chiếu số lượt **theo từng tập và tool**, không chỉ tổng:

| Tập | `libpostal` | `vietnamadminunits` | Quy tắc |
| --- | ---: | ---: | --- |
| 01 | 1.000 | 1.000 | 1 địa chỉ × 2 tool |
| 02 | 2.000 | 2.000 | noisy + clean × 2 tool |
| 03 | 1.500 | 1.500 | 1 địa chỉ × 2 tool |
| 04 | 800 | 800 | 1 địa chỉ × 2 tool |
| 06 | 600 | 1.200 | libpostal một lần, VietnamAdminUnits hai mode |
| 07 | 0 | 600 | chuyển cũ → mới, chỉ VietnamAdminUnits |

Kiểm ID chính xác theo index/source ID và suffix (`_noisy`, `_clean`, `_m25`, `_mleg`); kiểm không thiếu/nhân bản index, tool hoặc mode. Với Data 02, cả clean/noisy phải có gold giống nhau và input tương ứng hai cột nguồn. Với Data 04, gold extraction là năm trường **còn trên chuỗi**, không phải `GT_*` phục hồi. Với Data 07, gold chỉ `PhuongXa` và `TinhThanh` của đích xác minh bởi `MaPhuongXaMoi`; không chấm nó như bài T0 11 nhãn. Đối chiếu mode `FROM_2025`/`LEGACY` với protocol và raw trace; đây là oracle mode cho các tập có `HeQuyChieu`, không phải dự đoán T1 tự động.

**Xong khi:** báo cáo zero/missing/duplicate/mismatch theo từng điều kiện, kèm tối đa vài ID ví dụ lỗi; tổng kiểm tra khớp 13.000. Lưu số liệu machine-readable, không chỉ chụp màn hình.

### A3 — Kiểm tra scoring và báo cáo dẫn xuất (khoảng 0,5–1 ngày)

Khi A1–A2 đạt, dùng `evaluate_record()` và scorer **đúng phiên bản đã hash trong manifest** để tính lại `DungSai`, `LoaiLoi` và các metric từ dự đoán/gold đã lưu. Nếu mã hiện tại lệch hash, tìm bản mã đúng commit/snapshot trước; nếu không tìm được, đánh dấu phần tính lại là `UNVERIFIABLE`. V3 phải có strict exact và normalized Levenshtein theo policy trong manifest; fuzzy chỉ là thước đo khoảng cách chuỗi, **không** phải heuristic Jaro-Winkler và không thay thế đối chiếu mã hành chính.

Đối chiếu số liệu từ prediction với `docs/runs/baseline_v3_fuzzy/baseline_evaluation_report.md` và bảng `data/processed/evaluation/derived/baseline_v3_fuzzy/v4_fuzzy/comparative_analysis_tables/`. Kiểm `report_materials_lineage.json`: parent manifest hash, tất cả output hash và file thiếu. Nếu báo cáo dẫn xuất hỏng nhưng run lõi đúng, ghi `PASS_CORE_ONLY`, sửa bằng **một materials ID mới**, không ghi đè `v4_fuzzy`. Nếu báo cáo chính không có hash trong lineage, ghi phạm vi xác minh theo kiểm tra nội dung và công thức, không trình bày như đã chứng minh byte integrity.

**Xong khi:** mỗi metric có tên, tập, tool, mẫu số, giá trị tính lại và giá trị công bố; sai lệch vượt làm tròn theo cách report đang dùng phải được giải thích hoặc đánh trượt.

### A4 — Quyết định và công bố phạm vi sử dụng (khoảng 0,25 ngày)

| Kết luận | Điều kiện | Cách sử dụng |
| --- | --- | --- |
| `PASS` | A1–A3 đầy đủ, hash, độ phủ, gold, mode, scorer và report nhất quán | Dùng v3 làm mốc **5 trường / protocol fuzzy v2.0**; giữ v2 frozen |
| `PASS_CORE_ONLY` | Run lõi đúng, tài liệu dẫn xuất thiếu/lệch | Có thể dùng output lõi để phân tích nội bộ; chưa trích số report như kết quả được nghiệm thu |
| `FAIL` | Hash output sai, thiếu/nhân prediction, gold/mode/scorer sai hoặc không khớp protocol | Không lấy v3 làm mốc; tạo issue và một run ID mới sau khi sửa nguồn lỗi |
| `UNVERIFIABLE` | Thiếu manifest/input/source snapshot cần thiết để xác thực một cổng bắt buộc | Không công bố v3 là mốc; ghi rõ bằng chứng nào còn thiếu |

V2 vẫn được kiểm hash và giữ lịch sử. Không so sánh trực tiếp “v3 fuzzy tăng bao nhiêu so với v2” vì v2 không ghi metric fuzzy cùng protocol. Đánh giá lại v2, nếu cần, phải là một **derived analysis có ID mới** và mô tả rõ scorer mới; không thay thế v2 gốc.

### A5 — Hợp đồng script kiểm toán để có thể chạy lại

Đề nghị implement `python -m scripts.09_audit_baseline_runs --run-id baseline_v2 --run-id baseline_v3_fuzzy --output-dir docs/sprints/sprint_03`. Script chỉ mở input ở chế độ đọc, dùng `pathlib.Path`, `hashlib`, `csv`, `json` và code đánh giá đã có; không cần dependency mới. Chạy từ WSL tại `/mnt/d/DACN` bằng môi trường `~/.venv_dacn` nếu cần `pandas`. Cấm mọi tham số `overwrite-run` hoặc viết vào `data/processed/evaluation/runs/`.

JSON đầu ra nên có `audit_version`, `audited_at`, `repository_state`, `runs[run_id]`, `checks[]` và `decision`. Mỗi check ghi `id`, `scope`, `expected`, `actual`, `status` (`pass/fail/unverifiable`), `evidence_path`, `sample_ids`; dùng ID ổn định như `INPUT_SHA_01`, `OUTPUT_SHA_PRED`, `PAIR_KEY`, `D02_GOLD`, `D06_MODE`, `D07_TARGET`, `SCORER_REPLAY`, `DERIVED_PARENT_SHA`. Markdown phải được dựng từ cùng JSON để không mâu thuẫn. Exit code khác 0 nếu có `FAIL`; `UNVERIFIABLE` phải hiện rõ trong output và không được tự động đổi thành pass. Sau khi ghi báo cáo, kiểm lại hash hai manifest và bốn output lõi với inventory A0 để chứng minh quá trình audit không sửa run.

## 4. Ma trận mô hình phải khóa

### 4.1 Hai track dữ liệu và hợp đồng đầu ra

- **Track 5 trường tương thích:** các CSV benchmark 01/02/03/04/06; input inference chỉ là chuỗi địa chỉ. Kết quả gồm `SoNha, TenDuong, PhuongXa, QuanHuyen, TinhThanh`. Data 07 là **T2 chuyển hệ/đối chiếu mã**, báo riêng. Nếu một model cần oracle mode hoặc metadata, đặt thành cấu hình `oracle` có nhãn riêng và không so với cấu hình input-only.
- **Track T0 11 span:** corpus gán nhãn mới theo `SoNha, TenDuong, Ngo/Hem, ToaNha/CanHo, PhuongXa, QuanHuyen, TinhThanh, MocDinhVi, HuongDi, GhiChu, Khac`. Mỗi span lưu offset ký tự `[start,end)` trên chuỗi gốc, loại nhãn, text và ID nguồn. Quy ước `Khac` so với token `O`, span chồng nhau, tên đơn vị và dấu câu phải được chốt trong guideline trước khi train. Hiện benchmark 5 trường **không có gold span 11 nhãn**, nên không được tự tuyên bố điểm F1 T0 toàn nhãn trên đó.
- Nếu `Khac` là span thực sự và `O` là vùng không gán nhãn, BIO có `1 + 2 × 11 = 23` trạng thái; lưu danh sách label→ID cố định cùng split. Nếu guideline quyết định `Khac` chính là nền, phải sửa số trạng thái và ma trận **trước** mọi run, không trộn hai cách mã hóa trong một bảng kết quả.
- Khóa train/dev/test theo nhóm nguồn: cùng địa chỉ gốc và biến thể noisy/clean, cùng hóa đơn/OSM node, cùng cặp chuyển hệ không được rơi vào các split khác nhau. Không dùng test để chọn threshold, checkpoint, alias hoặc sửa nhãn. Train chỉ dùng dữ liệu được phép và nguồn truy xuất được; hóa đơn thật chỉ dùng khi nhãn được nghiệm thu và quy tắc riêng tư của dự án cho phép.
- Output tối thiểu của mọi parser: `sample_id`, `model_id`, `input`, danh sách span `(start,end,label,text)` nếu hỗ trợ T0, các trường chuẩn hóa nếu hỗ trợ 5 trường, `status`, `latency_ms`, và `trace` cần để truy vết. Parser có ít nhãn hơn 11 phải khai báo **supported-label subset**; báo điểm subset và coverage, không gán nhãn thiếu là kết quả âm tính giả để lấp khoảng trống.

### 4.2 Sáu cấu hình cụ thể

| ID | Cấu hình chính xác | Dữ liệu/huấn luyện | Đánh giá hợp lệ | Giới hạn bắt buộc ghi |
| --- | --- | --- | --- | --- |
| `DP-ZS-FT` | Deepparse pretrained `AddressParser(model_type="fasttext")`, zero-shot, không fine-tune | Không dùng train; khóa model weights, package, cache hash | 5 trường ở phần ánh xạ an toàn; T0 chỉ những nhãn native ánh xạ không mơ hồ | Native `Municipality` không tự suy ra `PhuongXa` hay `QuanHuyen`; không claim 11 nhãn |
| `DP-FT-FT` | Cùng kiến trúc Deepparse FastText, retrain với custom prediction tags trên train đã gán nhãn | T0 train + dev; checkpoint tốt nhất theo dev; test chỉ một lần | T0 11 nhãn nếu mapping/offset đầy đủ; 5 trường tách từ span | Không gọi đây là `Deepparse-CRF`; kiểm word-to-span alignment trước |
| `CRF-INDEP` | CRF chuỗi độc lập với feature thủ công: token/context, shape, tiền tố hành chính, dấu, từ điển phiên bản | T0 train + dev; seed, template feature, regularization khóa | T0 11 nhãn; 5 trường từ span | Không dùng embedding/nhãn test; không đồng nhất với Deepparse |
| `PHOBERT-CRF` | PhoBERT encoder + tuyến tính emission + CRF BIO có ràng buộc chuyển nhãn | T0 train + dev; checkpoint PhoBERT/version tokenizer/segmenter khóa | T0 11 nhãn; 5 trường từ span | PhoBERT cần word segmentation; offset phải quay về chuỗi gốc |
| `HEUR-JW` | Heuristic candidate lookup trên gazetteer versioned + Jaro-Winkler xếp hạng + ngưỡng chọn trên dev | Không train neural; chỉ tune threshold trên dev, khóa gazetteer/as-of date | 5 trường và subset T0 mà rule thực sự trích được | Jaro-Winkler là **thuật toán chọn candidate**, không phải metric fuzzy normalized Levenshtein của v3 |
| `PROPOSED-DYN` | PhoBERT span encoder + đầu T1 `cu/moi/Lai/khong_ro` + tầng giải mã chịu ràng buộc cấu trúc 2/3 cấp; so ablation cùng encoder không ràng buộc | T0+T1 train/dev đã gán nhãn; một split và ngân sách tune như baseline | T0 11 nhãn, T1, 5 trường tương thích; T2 chỉ khi bổ sung module và gold riêng | Cấm `QuanHuyen` chỉ khi đầu vào được xác nhận `moi`; với `Lai/khong_ro` phải giữ giả thuyết và báo bất định |

**Deepparse:** tài liệu chính thức mô tả hai pretrained model FastText/BPEmb và nhãn mặc định; `retrain(..., prediction_tags=...)` cho phép custom tags. BPEmb có thể là ablation `DP-ZS-BPE`/`DP-FT-BPE` sau khi khóa ma trận chính, không lẫn kết quả vào ID FastText. `fasttext-light` không dùng để retrain trực tiếp. Phiên bản đang được tài liệu mô tả là 0.10.0; khi triển khai phải khóa version thực cài và checkpoint thực tải. [Parser](https://deepparse.org/parser.html).

Với zero-shot, lập bảng mapping công khai cho từng nhãn native. `StreetNumber → SoNha`, `StreetName → TenDuong` là ứng viên trực tiếp cần kiểm bằng mẫu Việt; `Municipality` và `Province` có thể khác cấp hành chính theo địa chỉ nên chỉ ánh xạ nếu quy tắc từ **đầu ra và chuỗi đầu vào** xác định được cấp. `Unit`, `Orientation`, `GeneralDelivery` không tự biến thành nhãn 11 schema nếu guideline chưa xác nhận. Trường không hỗ trợ để trống và báo coverage; không dùng gold để chọn cách ánh xạ theo từng mẫu.

**PhoBERT/CRF:** lưu gold dưới dạng offset ký tự trước, rồi token hóa và BIO hóa có kiểm tra round-trip. Chỉ gắn loss/CRF mask lên token đại diện hợp lệ; special token, padding và mảnh subword phụ không mang nhãn. Nếu PhoBERT tokenizer/segmenter không cung cấp offset ổn định, tạo bảng ánh xạ ký tự có kiểm định và loại mẫu lỗi alignment khỏi train sau khi ghi lý do, không sửa gold theo output tokenizer. [PhoBERT](https://huggingface.co/docs/transformers/en/model_doc/phobert), [token classification](https://huggingface.co/docs/transformers/en/tasks/token_classification).

PhoBERT là encoder chính để ma trận có một cấu hình cố định. Nếu muốn thử ViBERT, thêm ID `VIBERT-CRF` hoặc `PROPOSED-VIBERT-DYN` với checkpoint/tokenizer/hash riêng và cùng split; không thay encoder âm thầm dưới ID PhoBERT.

**Heuristic:** ứng viên chỉ lấy từ gazetteer có mã định danh và hiệu lực theo ngày tham chiếu; dùng tổ hợp exact alias → Jaro-Winkler → ràng buộc tỉnh/phường đã có bằng chứng. Không tự sinh cạnh hành chính, không dùng bảng benchmark để thêm alias hoặc tune ngưỡng. Báo riêng coverage, reject/abstain, precision trên accepted và lỗi chọn sai thực thể dù chuỗi gần giống.

**Mô hình đề xuất:** cổng T1 dùng chính chuỗi đầu vào, không nhận `HeQuyChieu` gold lúc inference. Ràng buộc “không xuất `QuanHuyen` trên mẫu **được xác nhận** hệ mới” có thể loại lỗi cấu trúc trên slice đó, nhưng không bảo đảm toàn bộ tập đạt 0 lỗi khi T1 đoán sai. Đo `QuanHuyen` false-positive rate trên gold `moi` thiếu quận với mẫu số rõ ràng, đồng thời đo recall `QuanHuyen` trên `cu` và `Lai`, độ đúng T1 và tỉ lệ abstain. Con số 77,5% cũ phải dẫn tới đúng run, tập và mẫu số trước khi dùng làm điểm xuất phát.

### 4.3 Cách hiện thực ma trận ở các bước tiếp theo

1. **Data gate:** ban hành annotation guideline, nghiệm thu pilot 11 span, khóa split và hash. Có thể triển khai adapter zero-shot trước; các model supervised chờ train/dev gold. Không bắt buộc gán toàn bộ 5.500 dòng benchmark nếu tạo một T0 test đại diện, cố định và tách khỏi train. Mọi kết quả T0 phải ghi rõ kích thước, nguồn và coverage từng nhãn của test đó.
2. **Environment gate:** `requirements.txt` hiện không có Deepparse, PyTorch/Transformers hoặc CRF. `AGENTS.md` cấm cài dependency mới khi chưa có yêu cầu rõ. Agent trình bảng phiên bản, tương thích Python/WSL, RAM/GPU, dung lượng weights và quyền tải model; chỉ cài sau khi người dùng cho phép. Không tự dùng `.venv` Windows thay cho WSL runtime dự án.
3. **Adapter contract:** tách adapter inference, converter nhãn, scorer T0 và scorer 5 trường. Mỗi adapter nhận **chỉ** chuỗi địa chỉ và cấu hình đã khóa; metadata oracle là một run khác. Chuẩn hóa đầu ra không được thêm thông tin địa lý không có bằng chứng. Mỗi run có manifest input hash, split hash, model/checkpoint hash, code hash, package version, seed, output hash và lỗi runtime.
4. **Thứ tự xây dựng khi có gold:** `HEUR-JW` và `CRF-INDEP` để khóa scorer/annotation → `DP-ZS-FT` → `DP-FT-FT` → `PHOBERT-CRF` → `PROPOSED-DYN` và ablation. Thứ tự có thể đổi vì tài nguyên, nhưng tất cả cùng split và protocol. Chạy pilot để kiểm interface trước full run; mỗi run ghi ID mới, không ghi đè baseline cũ.
5. **Bảng kết quả:** cột `track, dataset/split hash, model_id, input mode, supported labels, exact span P/R/F1 micro và per-label, 5-field exact/micro-F1, QuanHuyen FP rate, latency, abstain, seed, run manifest`. Data 07/T2 là bảng riêng. So sánh chỉ trong cùng track, cùng tập và cùng quyền truy cập input.

## 5. Tiêu chí nghiệm thu giao việc 01

- [x] Có inventory và báo cáo bằng chứng kiểm toán v2/v3; không tệp frozen nào đổi hash.
- [x] Có bảng kết quả A1–A3 từng kiểm tra với expected/actual, mã lỗi và ID mẫu; không bỏ qua kiểm gold, mode hoặc báo cáo dẫn xuất.
- [x] Kết luận v3 theo đúng bốn trạng thái ở A4; nếu `PASS`, ghi rõ phạm vi **5 trường, oracle mode theo protocol, fuzzy normalized Levenshtein**, không gọi là kết quả T0 11 span hay T1 tự động.
- [x] Ma trận có đủ sáu ID; CRF độc lập; Deepparse FastText zero-shot/fine-tuned tách riêng; Jaro-Winkler và metric fuzzy v3 phân biệt.
- [x] Ghi rõ corpus T0 11 span chưa sẵn sàng, nguồn cho train/dev/test, quy tắc chống leakage, label coverage và điều kiện cài dependency.
- [x] Mọi tài liệu mới có liên kết nguồn code/manifest và nêu hạn chế; không ghi đè `baseline_v2`, `baseline_v3_fuzzy` hoặc tài liệu Sprint 2.

## 6. Prompt bàn giao ngắn cho AI agent khác

> Đọc `AGENTS.md`, `docs/VERSIONING.md` và tài liệu này. Thực hiện A0–A4 theo thứ tự với hợp đồng script A5, lưu báo cáo/JSON ở `docs/sprints/sprint_03/`. Không sửa run `baseline_v2` hay `baseline_v3_fuzzy`. Chỉ công nhận v3 khi cả hash, độ phủ, gold/mode/scorer và báo cáo đạt. Sau đó khóa ma trận ở Mục 4 thành `model_matrix.md`, xác nhận từng cấu hình và cổng dữ liệu/môi trường. Báo rõ kiểm tra nào đạt, không đạt hoặc chưa xác minh; chưa chạy huấn luyện hay cài thư viện mới.
