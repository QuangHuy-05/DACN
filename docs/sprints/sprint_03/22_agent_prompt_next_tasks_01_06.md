# Lộ trình và prompt agent — 6 việc tiếp theo của Sprint 3

**Phạm vi:** hoàn thiện các việc có thể làm trên train/dev và nguồn sẵn có, chưa dùng Google Colab và chưa đụng tới 100 test. Prompt này không yêu cầu huấn luyện hoặc công bố metric mới cho mô hình neural.

## Trạng thái cần giữ làm mốc

- Corpus đã duyệt: `data/processed/annotation/sprint03/corpus_train_dev_v2/` — 240 train / 60 dev, schema `s3-span-v1.1`, manifest là nguồn chuẩn về hash và ngoại lệ. Task 543 bị loại khỏi T1 theo manifest nhưng vẫn giữ đầy đủ cho T0.
- Test 100 đang chờ partner; không import, đọc nhãn, dùng làm input, tune, debug theo gold hoặc chấm test.
- Baseline frozen: HEUR-JW đã có dev T0 F1 88,01%; CRF-INDEP 89,82%; track 5 trường đã có kết quả. Không chạy đè, sửa hoặc chấm lại các run đó. DP-ZS-FT chưa có thực nghiệm pretrained thật.
- Gazetteer `s3_v2` còn `PARTIAL_OLD_CODES_UNVERIFIED`; không sửa trực tiếp.
- Hai bảng mã đã có trong repository: `third_party/vietnamadminunits/data/raw/danhmuchanhchinh.gso.gov.vn_ward_2025-07-18.csv` (10.035 dòng) và `..._district_2025-07-18.csv` (696 dòng). So sánh exact trước đây: 9.451/10.035 xã cũ khớp khóa đầy đủ và mã ứng viên; 584 xã chưa khớp. Huyện: 665 khớp; 5 khóa khớp nhưng thiếu mã trong gazetteer; 26 chưa khớp. Chưa có mã nào được nâng thành official verified.
- Runtime neural chưa được cài. Inventory ngày 02/10/2026 ghi Python 3.11.16 hiện có, RAM WSL khả dụng khoảng 3,64 GiB + swap 1 GiB, đĩa D còn khoảng 13,65 GB tại thời điểm đo. Đây chỉ là số cũ; phải đo lại trước khi tải/cài.

## Lộ trình theo thứ tự

| Thứ tự | Việc | Vì sao / mục tiêu | Đầu ra và điều kiện hoàn tất | Phụ thuộc |
|---|---|---|---|---|
| 1 | Hoàn chỉnh hồ sơ nguồn cho bảng GSO đã có | Biết chính xác ai phát hành, bảng phản ánh thời điểm nào, có thể dùng dữ liệu đến đâu; tên file và URL trang chủ chưa đủ chứng minh snapshot hoặc license. | Source register có URL tài liệu cụ thể, cơ quan, ID/phiên bản, ngày ban hành/truy cập, thời kỳ hiệu lực/tham chiếu, điều khoản sử dụng, hash file local nếu có, vị trí trang/dòng. Mục chưa chứng minh phải để `UNKNOWN`/`UNVERIFIED`. | Không phụ thuộc; bắt đầu trước việc 2. |
| 2 | Phân loại các khóa xã/huyện chưa khớp | Phân biệt khác chính tả/tên lịch sử, thiếu alias, thiếu cha, sai cấp, thiếu mã hay thực sự không có bản ghi; không dùng fuzzy để tự xác nhận. | 2.1. Báo cáo cho 584 xã, 26 huyện, 5 huyện thiếu mã; mỗi hàng có khóa gốc, khóa tra, trạng thái, bằng chứng và lý do. 2.2. Queue riêng cho trường hợp cần người duyệt. Chỉ exact match theo khóa cha/cấp/hệ/thời điểm hoặc alias có bằng chứng mới được đánh dấu xác minh. | Việc 1 cung cấp bằng chứng và thời kỳ. Có thể bắt đầu đối chiếu kỹ thuật song song, nhưng chưa nâng trạng thái. |
| 3 | Cập nhật dữ liệu gazetteer nếu bằng chứng cho phép | Chuyển kết quả audit thành bản dẫn xuất có thể tái lập, nhưng không làm hỏng gói đang dùng baseline. | Bản ứng viên luôn nằm trong `data/interim/modeling/sprint03/<version>/gazetteer_candidate/`. Chỉ khi bằng chứng đủ mới phát hành `data/processed/gazetteer/s3_v3/`, kèm manifest/hash, diff so với v2, coverage theo cấp/hệ/trạng thái và lookup tests. Nếu chưa đủ: chỉ cập nhật gap report; giữ v2 và trạng thái partial, không tạo v3 “cho đủ”. | Sau 1–2. |
| 4 | Phân tích lỗi baseline đã frozen | Tìm lỗi có giá trị nghiên cứu để quyết định bước sau, không phát sinh run khác hoặc dùng test. | Báo cáo lỗi HEUR-JW/CRF theo T0 và 5 trường tách riêng; nhóm theo span boundary, nhầm nhãn/cấp, thiếu span, FP cấu trúc, lỗi nhiễu/thiếu trường, nguồn observed/derived/synthetic và support. Đính kèm ID/offset/error category; kết luận thận trọng với nhãn support 0/1. | Độc lập; làm song song với 1–3. |
| 5 | Tạo runtime neural cô lập chỉ trên ổ D và chạy kiểm thử đang bị skip | Xác nhận code U1–U7 có thể giao tiếp với framework thật, không cài vào env chính. | Venv/package/cache/temp/model assets mới chỉ nằm dưới D; Torch CPU tiny forward/backward/save-load và neural unit suite thực sự chạy. Ghi package/version/source/license/hash, đường dẫn, byte trước/sau và test PASS/SKIP/FAIL. | Kiểm kê ổ đĩa/RAM trước; task 6 dùng runtime này. |
| 6 | Kiểm tra tích hợp thật của Deepparse và PhoBERT processor/model | Xác minh API, tokenization, segmentation, offset Unicode và trạng thái tài nguyên thật thay vì dựa vào fixture. | Deepparse: API/native tag và alignment chỉ được xác nhận tới mức package/resource thật đã chạy; FastText full vẫn pending nếu thiếu RAM/đĩa/license. PhoBERT: tokenizer/VnCoreNLP local, alignment audit 240/60, tiny CPU forward nếu RAM cho phép. Lưu revision/license/hash và kết quả. Không tạo prediction/metric benchmark, không train. | Sau task 5; resource license/hash phải rõ. |

### Các ràng buộc tài nguyên

- Chỉ cài hoặc tải mới vào `D:\DACN\...` (WSL tương ứng `/mnt/d/DACN/...`). Không ghi package, wheel cache, HF cache, temp, Java hoặc model weights vào C:, Windows profile, `/home`, `/root`, `/tmp` hoặc env có sẵn.
- Runtime đề xuất: `data/interim/modeling/sprint03/runtime_neural_d_v1/`; cache/temp: `data/interim/modeling/sprint03/install_cache_d_v1/`; model/segmenter assets: `data/interim/modeling/sprint03/resources_d_v1/`. Tạo tên version mới nếu đã tồn tại; không xóa hay tái sử dụng thư mục ngoài task.
- Dùng Python 3.11 đã có làm interpreter nền nếu còn hoạt động; tạo venv mới nằm trên D (dùng chế độ copy nếu symlink trên NTFS gây lỗi). Không cài Python/package vào env toàn máy hoặc các venv hiện hành. Nếu Python nền cần được cài mới thì chỉ được cài vào thư mục D sau khi ghi nguồn, version, license và dung lượng vào inventory.
- Đặt `PIP_CACHE_DIR`, `UV_CACHE_DIR`, `TMPDIR`, `XDG_CACHE_HOME`, `HF_HOME`, `HF_HUB_CACHE`, `TRANSFORMERS_CACHE`, `TORCH_HOME` và `PYTHONUSERBASE` vào thư mục task trên D; tắt pip user install; kiểm tra `sys.prefix`, `module.__file__`, cache env và file mới trước/sau. Không sửa cấu hình shell/WSL toàn máy.
- Chỉ dùng CPU build của PyTorch; version dự án đang khóa là 2.8.0. Tài liệu PyTorch phát lệnh CPU riêng qua index `https://download.pytorch.org/whl/cpu`. Không cài CUDA stack vào WSL khi mục tiêu là smoke test CPU.
- Inventory hiện pin tham khảo: `torch==2.8.0`, `transformers==4.57.1`, `deepparse==0.11.0`, `poutyne==1.17.4`, `py-vncorenlp==0.1.4`, Temurin/OpenJDK 17 local nếu VnCoreNLP cần. Đây không phải lệnh cài mù: xác minh package identity, tương thích, resolver và license từ nguồn chính thức trước. Cài đúng những gì test cần; không cập nhật package không liên quan.
- PhoBERT base khoảng 0,54 GB weights theo inventory cũ; Deepparse FastText full embedding khoảng 6,8 GB, đòi hỏi khoảng 8–10 GB RAM, license embedding riêng còn pending. Không tải FastText full trong runtime hiện ghi RAM khả dụng 3,64 GiB. Chỉ mở tải sau khi đo mới thấy RAM đạt gate ít nhất 10 GiB, đĩa D đủ chỗ sau khi giữ lại tối thiểu 3 GiB trống, và license/revision/hash đã được xác minh. Thiếu một điều kiện thì báo `BLOCKED`, không thay bằng FastText light dưới cùng model ID.
- Trước mỗi lần tải, ghi package/model/resource, version/revision, URL nguồn chính thức, license và đường dẫn license, dung lượng tải ước tính, dung lượng giải nén ước tính, mục đích, dung lượng D hiện trống và phần trống sẽ còn lại. Chỉ tiếp tục khi nằm trong D và còn đủ dự phòng. Không tải dữ liệu địa chỉ mới.
- Cuối task 5–6 báo cáo dung lượng theo **byte, GB thập phân (10⁹) và GiB (2³⁰)**: tổng venv, model/checkpoint/segmenter/Java, cache còn lưu, temp còn sót, tổng bytes mới tạo trong các thư mục task và thay đổi dung lượng trống D. Ghi rõ số thư mục là logical size; dùng mức giảm dung lượng trống D làm kiểm tra chéo vì ổ có thể có nén/hoạt động khác. Không cộng trùng wheel trong cache và bản cài. Chỉ xóa temp do chính lượt này tạo trong thư mục task; giữ runtime/resource và không xóa cache hoặc file có trước.

## PROMPT GIAO AGENT

```text
Bạn là Senior AI/Data Engineer phụ trách hoàn thiện sáu việc tiếp theo của Sprint 3 trong repository D:\DACN. Hãy thực hiện công việc và bàn giao artifact/report; không chỉ lập kế hoạch.

ĐỌC TRƯỚC:
1. AGENTS.md
2. docs/sprints/sprint_03/19_seven_priorities_implementation_report.md
3. docs/sprints/sprint_03/20_gazetteer_source_audit.md
4. docs/sprints/sprint_03/21_existing_administrative_code_sources_review.md
5. docs/sprints/sprint_03/14_experiment_01_04_environment.md
6. docs/sprints/sprint_03/15_baseline_experiments_20261002.md
7. docs/sprints/sprint_03/17_training_protocol_v1.md
8. configs/modeling/sprint03/protocol_lock_v1.json và resource lock/config liên quan
9. manifest.json của data/processed/annotation/sprint03/corpus_train_dev_v2/

MỤC TIÊU — làm theo đúng thứ tự và tiếp tục mọi phần độc lập nếu một phần bị chặn:
1) Hoàn chỉnh provenance/source register của hai bảng GSO đã có.
2) Audit 584 xã cũ, 26 huyện cũ chưa match và 5 huyện match khóa nhưng thiếu mã trong gazetteer.
3) Tạo bản dẫn xuất gazetteer mới chỉ khi bằng chứng đủ; nếu chưa đủ, phát hành gap report thay vì tự xác nhận dữ liệu.
4) Phân tích lỗi từ các prediction/run đã frozen của HEUR-JW và CRF-INDEP, tách track T0 với 5 trường.
5) Sau inventory, cài runtime neural cô lập và mọi cache/temp/resource phát sinh chỉ trên ổ D; chạy các kiểm thử neural trước đó bị skip.
6) Xác minh tích hợp thật của API Deepparse và PhoBERT tokenizer/segmenter/model tới mức tài nguyên và máy cho phép; kiểm alignment train/dev. Không huấn luyện mô hình, không sinh prediction benchmark hoặc metric mới trong nhiệm vụ này.

PHẠM VI CẤM:
- Không dùng Google Colab.
- Không đọc/import/đưa vào adapter/train/tune/debug/chấm benchmark 100 test. Test 100 vẫn do partner phụ trách; không tìm các nhãn của test.
- Không train Deepparse fine-tuned, PhoBERT-CRF hay proposed model; không tune dev, không chấm lại baseline. Neural smoke/integration tests không phải thực nghiệm mô hình.
- Không sửa `data/raw/`, `third_party/`, file export/canonical/Label Studio, corpus đã duyệt, split, manifest, hash, gazetteer s3_v1/s3_v2 hoặc bất kỳ run/baseline frozen nào. Không sửa label của sample 543; T1 mask của nó phải được giữ theo corpus manifest.
- Không tạo prediction/metric giả; fixture/tiny random model không được gọi là pretrained experiment.
- Không tải/crawl địa chỉ mới, không dùng dữ liệu hóa đơn cá nhân, không tạo alias/cạnh hành chính theo suy đoán.
- Không thay đổi env Python/WSL toàn máy, không cài vào C:, `/home`, `/root`, `/tmp`, Windows profile, user site, env hiện có hoặc system packages. Không dùng apt/sudo. Không commit/push trừ khi chủ dự án yêu cầu riêng.

QUY TẮC BẤT BIẾN VÀ ANTI-LEAKAGE:
- Train/dev chuẩn là 240/60 trong `corpus_train_dev_v2`, schema `s3-span-v1.1`; manifest mới nhất là nguồn chuẩn cho hash/exclusion. T0 giữ đủ task 543; T1 phải loại nó theo `evaluation_exclusions.t1`.
- Mọi inference adapter chỉ được nhận text-only. Chấm gold tách biệt, chỉ sau khi prediction thực đã được serialize/freeze. Không dùng `GT_*`, `HeQuyChieu`, metadata gán nhãn, provenance hay gold span như feature.
- Không đọc/đưa test100 qua bất cứ lệnh audit có thể lộ gold. Nếu một script tự glob cả corpus/evaluation, kiểm code trước và giới hạn đường dẫn rõ ràng.
- Với mọi run/artifact mới dùng ID và thư mục version mới; không ghi đè. Nếu một input đã có hash trong ledger, kiểm tra trước/sau.
- Mỗi kết quả phân biệt `PASS`, `PARTIAL`, `BLOCKED`, `NOT_RUN`; ghi bằng chứng và lệnh thật. Không biến skip thành pass.

VIỆC 1 — SOURCE REGISTER:
- Audit hai CSV đã có:
  `third_party/vietnamadminunits/data/raw/danhmuchanhchinh.gso.gov.vn_ward_2025-07-18.csv`
  `third_party/vietnamadminunits/data/raw/danhmuchanhchinh.gso.gov.vn_district_2025-07-18.csv`
- Ghi SHA-256, bytes, row count, columns, encoding, date string trong filename; đọc ghi chú tải nguồn trong `third_party/vietnamadminunits/scripts/collecting_data/s1_downloading_danhmuchanhchinh.gso.gov.vn.txt`.
- Tìm bằng chứng nguồn chính thức cho đúng ấn phẩm/bảng/snapshot, cơ quan, ngày ban hành/tải, reference/effective date, license/điều khoản tái sử dụng. Dùng URL cụ thể (không chỉ trang chủ), document ID, trang/dòng hoặc file local + hash. Phân biệt license thư viện bên thứ ba với quyền dùng CSV và văn bản nguồn.
- Không suy rằng ngày trong tên file là thời điểm snapshot, hoặc “cơ quan nhà nước công khai” tự động cấp cùng license cho CSV dẫn xuất. Không tìm được thì ghi UNKNOWN/UNVERIFIED và evidence gap.
- Cập nhật source register trong thư mục version mới dưới `data/interim/modeling/sprint03/` và docs follow-up mới (không ghi đè báo cáo20/21 đã phát hành).

VIỆC 2 — RECONCILIATION:
- Dùng script/verifier đã có. Lưu mã như string, giữ zero đầu. Exact key gồm đầy đủ tỉnh+huyện+xã cũ, đúng level/system/time. Trước tiên tái tạo baseline counts 9.451/10.035, 584 xã unmatched; 665 huyện matched, 5 thiếu code và 26 huyện unmatched. Nếu counts lệch, dừng sửa và điều tra version/hash/schema.
- Phân loại từng unmatched: normalized-only variation; alias đã có audit và có evidence; cấp/parent mismatch; có trong nguồn khác nhưng thời kỳ không tương đương; không có evidence; code absent. Mỗi hàng lưu raw key/code, lookup key/code, status, evidence source ID/page/row/hash, rule áp dụng, confidence/status và reason.
- Fuzzy/string similarity chỉ tạo review candidate queue; không tự promote. Alias mới chỉ vào candidate/audit queue, chưa sửa lớp alias frozen. Không tự điền mã thiếu và không chọn một candidate khi tên trùng.
- Đầu ra machine-readable: exact reconciliation table đầy đủ cho 615 trường hợp cần audit (584+26+5), summary coverage và unresolved queue. Báo chính xác số verified mới; 0 cũng hợp lệ nếu nguồn không chứng minh được.

VIỆC 3 — GAZETTEER:
- Giữ nguyên s3_v1 và s3_v2. Bản thử mới nằm ở đường dẫn versioned trong interim; không thay package hiện hành.
- Chỉ phát hành package/version mới nếu từng thay đổi có source evidence và kiểm thử. Cần entity schema, valid interval `[valid_from, valid_to)`, parent/system/level/code status, aliases có audit, source IDs/hash, edge type đầy đủ (1-1/1-N/N-1/M-N), diff với v2, coverage report và lookup results.
- Mã thiếu hoặc candidate không chứng minh được giữ nguyên trạng thái. Tên giống nhau không đủ để xác lập mã/quan hệ. Không ép nhiều target thành một đích, không thay 5 cạnh phi nguyên tử.
- Nếu evidence không đủ: không tạo s3_v3. Tạo report giải thích lỗ hổng, yêu cầu bằng chứng cụ thể, xác nhận s3_v2/hash không đổi.
- Chạy test verifier, duplicate keys, leading-zero, date interval, ambiguous lookup, multiple targets và non-atomic relations; log test thực tế.

VIỆC 4 — BASELINE ERROR ANALYSIS:
- Đọc report/run manifests/predictions đã frozen của HEUR-JW và CRF-INDEP; không gọi scripts run/score/audit nếu chúng có thể ghi đè hoặc sinh kết quả mới. Ưu tiên phân tích trực tiếp prediction + error_analysis + frozen metrics.
- Tạo báo cáo riêng cho (a) T0 exact span 11 nhãn và (b) track benchmark 5 trường. Không trộn số liệu/đơn vị. Không so với run chứa 4.900 hàng như thể cùng protocol với 4.800.
- Phân nhóm: missed span/FN; extra span/FP; boundary/partial; wrong label/administrative level; address-system/structural error nếu có nhãn hợp lệ; normalization-vs-extraction; OCR/noise; missing field; source type observed/derived/synthetic. Dùng provenance chỉ để phân tầng báo cáo, không đưa vào model.
- Báo count, denominator, ví dụ với sample_id/offset và mô tả ngắn; không in địa chỉ nhạy cảm. Với nhãn support0/1 ghi “không đủ bằng chứng kết luận”. Giữ F1 đã công bố 88.01%/89.82% cho T0 và điểm track5 trường như report15; không tính lại/chọn lỗi cho khớp số.
- Đầu ra: error taxonomy CSV/JSONL, summary Markdown, recommendation backlog ưu tiên có liên kết tới đúng run/input hash. Không sửa gold/prediction.

VIỆC 5 — D-ONLY RUNTIME INSTALL + TEST:
- Trước khi tạo file/cài: ghi snapshot dung lượng trống D (`df` và Windows `Get-Volume`/`fsutil` nếu có), RAM/swap, Python version/realpath, package hiện có, GPU nếu đọc được; tính dung lượng từng thư mục task đã có. Ghi giờ đo và byte chính xác.
- Tạo venv và mọi nội dung cài mới trong các thư mục mới dưới:
  `/mnt/d/DACN/data/interim/modeling/sprint03/runtime_neural_d_v1/`
  `/mnt/d/DACN/data/interim/modeling/sprint03/install_cache_d_v1/`
  `/mnt/d/DACN/data/interim/modeling/sprint03/resources_d_v1/`
  Nếu một path đã tồn tại, dùng suffix version mới và không xóa nó.
- Python nền ưu tiên Python3.11 đã có. Dùng `venv --copies` khi cần. Không cài Python nếu interpreter hiện có hoạt động; nếu buộc phải cài thì chỉ bản local vào D, ghi nguồn/version/license/hash/size trước.
- Trước cài từng package: cập nhật inventory với package/version, official index/source URL, license + URL license, wheel/source size, resolved dependencies + license, destination path, purpose, estimated installed size. Dùng các version khóa trong inventory14: Torch2.8.0 CPU, Transformers4.57.1, Deepparse0.11.0, Poutyne1.17.4, py-vncorenlp0.1.4; verify rằng đúng package/version tồn tại và tương thích. Chỉ cài package cần cho acceptance/tests. Không tự upgrade hoặc đổi protocol pin.
- PyTorch chỉ CPU build theo hướng dẫn chính thức. Kiểm dependency resolution có kéo CUDA packages không; nếu có thì hủy resolver/dừng trước khi cài, sửa index/constraint theo official CPU instructions rồi inventory lại.
- Chuyển tất cả cache/temp sang thư mục D bằng env vars có scope cho terminal/task: `PIP_CACHE_DIR`, `UV_CACHE_DIR`, `TMPDIR`, `XDG_CACHE_HOME`, `HF_HOME`, `HF_HUB_CACHE`, `TRANSFORMERS_CACHE`, `TORCH_HOME`, `PYTHONUSERBASE`. Disable user-site/user-install. Xác minh `sys.prefix` và `module.__file__` của package mới nằm dưới `/mnt/d/DACN`; xác minh không có cache/download mới trong home/C. Không sửa dotfiles hoặc shell config global.
- Không apt/sudo, không thay Java toàn máy. Nếu VnCoreNLP cần Java, chỉ tải distribution đã xác minh và giải nén local dưới `resources_d_v1`; nếu license/revision/hash chưa rõ thì bỏ bước download và ghi blocker.
- Trước khi cài/tải, giữ ít nhất 3 GiB trống trên D sau ước lượng. Inventory cũ chỉ có 12.71 GiB trống, phải đo hiện tại. Không tải FastText full 6.8 GB với WSL RAM khả dụng thấp hơn gate 10 GiB; license embedding cũng chưa xác minh. Không thay FastText full bằng light hoặc BPEmb dưới cùng model ID. Có thể kiểm package/API không tải full resource và ghi prediction integration blocked.
- Tải PhoBERT/VnCoreNLP weights/assets chỉ khi cần cho việc 6, license/version đã xác minh, dung lượng D đủ sau reserve và đường dẫn local explicit. Không để HuggingFace tự tải về `~/.cache`.
- Chạy đúng bộ test đã bị skip do Torch/Deepparse/VnCoreNLP tại runtime D, thêm `python -m unittest discover -s tests -v` ở runtime dự án hiện có nếu không sửa package/env đó. Ghi command, version, PASS/SKIP/FAIL, reason, log path. Tiny random fixture chỉ được ghi `unit/integration test`, không phải experiment.
- Sau install: tính bytes theo thư mục venv/model/Java/cache/temp; đo D free lại; đối chiếu với snapshot. Báo bytes, GB decimal và GiB, không cộng trùng wheel-cache và installed copy. Chỉ dọn temp do lượt này tạo dưới install_cache task; không xóa runtime, weights, cache có trước hay bất cứ data nào.

VIỆC 6 — TÍCH HỢP MODEL/PROCESSOR THẬT:
Deepparse:
- Xác minh constructor, pretrained path, parser output/tag, EOS, alignment API đúng với Deepparse pin đã cài. Không dùng model fixture để tuyên bố native pretrained đã chạy.
- Thử model chỉ khi đúng artifact/resource/revision/license được inventory và dung lượng/RAM gate đạt. Đối với FastText full, gate RAM tối thiểu 10 GiB available và D còn >=3 GiB sau dự báo cài; hiện inventory cũ không đạt. Nếu không đạt, chốt package API/alignment test tới mức có thể và để `PRETRAINED_INTEGRATION_BLOCKED_RESOURCE`.
- Nếu được chạy tài nguyên thật, dùng chỉ địa chỉ tự soạn cho smoke, không benchmark metric; log raw native output, tag mapping version, token-to-char offsets, unicode/dấu tiếng Việt, punctuation, repeated token, abstain/reject. Không load gold vào parser.

PhoBERT:
- Pin exact model repo/revision, file list + SHA-256, model card/license; chỉ cache local trên D và bật offline/local-files-only sau download.
- Pin VnCoreNLP jar/version, word-segmenter assets, Java distribution/version/license + file hashes. Test trên chuỗi tự soạn trước.
- Chạy segmentation/tokenizer alignment trên đủ 240 train + 60 dev text-only; sau đó kiểm khả năng biểu diễn spans với gold chỉ trong bước supervised alignment/QA riêng, ghi unsupported/cross-token cases thay vì sửa gold. Kiểm Unicode NFC/NFD, tên lặp, punctuation, underscore/space, B/I edges, long input. Không dùng GT/system/source labels làm input inference.
- Nếu RAM cho phép, chạy 1 CPU forward với PhoBERT local, batch1/sequence ngắn, `eval()` và không gradient; nếu task5 cần test forward/backward, dùng tiny random architecture riêng. Ghi rõ pretrained forward và tiny fixture là hai bằng chứng khác nhau.
- Chưa train. Không tạo checkpoint nghiên cứu, prediction dev hay metric model.

TEST/FINAL GATE:
- Theo AGENTS.md: chạy test toàn repo phù hợp; test file nào sửa trong `src/` phải có regression. Nếu toàn repo có skip, giải thích skip; không gọi toàn suite “đã pass” khi còn skip.
- Kiểm `git diff --check`, mọi hash trước/sau cho corpus, test hold, baseline v2/v3, s3_v1/s3_v2 và raw CSV; chúng phải giữ nguyên.
- Kiểm không có file mới ngoài D do cài đặt. Lệnh/snapshot phải cho phép truy vết mọi package/model file mới.
- Đầu ra tài liệu: tạo follow-up version mới dưới `docs/sprints/sprint_03/` gồm (1) source/code reconciliation + gazetteer outcome; (2) frozen baseline error analysis; (3) D-only install inventory + dung lượng; (4) neural/API integration outcomes; (5) test report; (6) remaining blockers and exact conditions to reopen them. Không ghi đè docs14–21 đã phát hành.

BÁO CÁO CUỐI TRONG CHAT:
1. Kết quả 1–6 từng mục: DONE/PARTIAL/BLOCKED và bằng chứng.
2. Danh sách package/model/Java thật đã cài/tải: version/revision, nguồn, license, hash và đường dẫn trên D. Nếu không cài được gì thì nói rõ.
3. Dung lượng trước/sau, tổng mới chiếm, breakdown venv / model / segmenter-Java / cache / temp theo bytes + GB + GiB; nói rõ cách tính và khả năng sai số.
4. Test PASS/SKIP/FAIL cùng command/runtime/log path.
5. Hash bất biến corpus/baseline/gazetteer và kết luận test100/Colab không bị đụng tới.
6. Việc duy nhất còn cần chủ dự án làm, có lý do cụ thể. Không yêu cầu họ xử lý phần agent có thể làm trong quyền đã được cấp.

Không dừng sau khi phát hiện một blocker. Hoàn tất các mục độc lập, ghi trạng thái thật, không tuyên bố neural pretrained experiment/metric nếu chỉ mới cài package hoặc chạy fixture.
```

## Bằng chứng phiên bản package tham khảo

Các version trên là pins hiện có trong inventory của repository, không phải đề xuất cập nhật. Tài liệu PyTorch chính thức ghi riêng lệnh CPU cho 2.8.0; Deepparse 0.11.0 yêu cầu Python từ 3.10 và khai báo LGPLv3; Transformers 4.57.1 yêu cầu Python từ 3.9; Poutyne 1.17.4 yêu cầu Python từ 3.10 và khai báo LGPLv3. Agent phải kiểm lại nguồn/license đúng artifact trước cài.

- [PyTorch previous versions / CPU install](https://docs.pytorch.org/get-started/previous-versions/)
- [PyPI Deepparse 0.11.0](https://pypi.org/project/deepparse/0.11.0/)
- [PyPI Transformers 4.57.1](https://pypi.org/project/transformers/4.57.1/)
- [PyPI Poutyne](https://pypi.org/project/poutyne/)
- [PyPI python-vncorenlp](https://pypi.org/project/python-vncorenlp/)
- [VnCoreNLP repository/license](https://github.com/vncorenlp/VnCoreNLP)
- [PhoBERT by VinAI](https://github.com/VinAIResearch/PhoBERT)
- [Deepparse FastText resource requirements](https://deepparse.org/get_started/get_started.html)
