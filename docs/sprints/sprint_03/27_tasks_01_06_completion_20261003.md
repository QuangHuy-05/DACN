# Nghiệm thu sáu việc tiếp theo — 03/10/2026

Đã hiện thực và chạy các phần trong phạm vi máy/tài nguyên. Không train hoặc chấm mới; không sử dụng Colab/test100. Không commit/push. Các phần thiếu bằng chứng được giữ đúng trạng thái, không thay bằng kết quả giả.

## 1. Kết quả từng việc

| Việc | Trạng thái | Kết quả và bằng chứng |
|---|---|---|
| 1. Source register | PARTIAL | Hai CSV đã có hash/schema/locator, official URLs và HTTP evidence; chưa xác minh thời kỳ export/quyền dùng CSV. Source register v3 + báo cáo24 |
| 2. Reconciliation | DONE audit; 0 verified mới | Tái tạo9.451/10.035 xã và665 huyện khớp; phân loại615ca, full key/zero đầu/evidence từng dòng, unresolved queue |
| 3. Gazetteer | DONE gap report; release BLOCKED | s3_v2 giữ partial; không tạo v3 hoặc điền mã thiếu; 5cạnh phi nguyên tử và mọi đích giữ nguyên |
| 4. Frozen error analysis | DONE | T0 và5field tách riêng; event taxonomy, source/stratum, examples/offset, backlog; không inference/scorer/tune |
| 5. Runtime + test | DONE với ngoại lệ log hệ thống có sẵn | Runtime CPU/resources/cache/temp mới nằmD;7test neural từngskip đã chạy thật; dung lượng ở bảng dưới |
| 6. Actual integration | PARTIAL | Deepparse API PASS nhưng full FastText BLOCKED; PhoBERT/VnCoreNLP271/300exact,29reject có trace; short pretrained forward PASS |

[Nguồn và615ca](24_source_reconciliation_followup_20261003.md) · [Phân tích baseline](25_frozen_baseline_error_analysis_20261003.md) · [Cài và tích hợp](26_local_neural_install_and_integration_20261003.md).

Evidence root: `data/interim/modeling/sprint03/task_01_06_20261003_v1/`. Thư mục interim bị Git ignore; partner cần nhận artifact riêng hoặc dùng workspace chung. Các báo cáo14–21 và run/corpus/gazetteer frozen không bị ghi đè.

## 2. Chi phí dung lượng thực đo

Mốc trước: `13,622,972,416` bytes trốngD. Mốc sau: `11,064,565,760` bytes (11.064565760 GB / 10.304680 GiB), đo `2026-10-02T19:31:04.301159+00:00`. Còn vượt reserve3GiB.

| Thành phần | Bytes | GB decimal | GiB |
|---|---:|---:|---:|
| Venv/packages | 1,342,973,969 | 1.342973969 | 1.250741974 |
| PhoBERT weights + tokenizer/license | 544,957,604 | 0.544957604 | 0.507531319 |
| VnCoreNLP wseg | 28,068,447 | 0.028068447 | 0.026140778 |
| Java local | 141,553,758 | 0.141553758 | 0.131832210 |
| Cache/archive giữ lại | 396,035,026 | 0.396035026 | 0.368836360 |
| Temp (đã nằm trong cache) | 0 | 0.000000000 | 0.000000000 |
| Evidence/report data (ngoài tổng cài) | 28,513,899 | 0.028513899 | 0.026555638 |
| **Tổng cài/tài nguyên/cache mới** | **2,453,588,804** | **2.453588804** | **2.285082642** |

D free giảm `2,558,406,656` bytes = 2.558406656 GB / 2.382701874 GiB. Đây là biến động toàn ổD, không đồng nhất với tổng logical bytes của file cài. NTFS allocation/directory metadata, evidence/code/docs và app ghi đồng thời tạo chênh lệch; không tự gán toàn phần chênh cho pip.

Phương pháp: mỗi regular file chỉ tính một lần theo inode trong các thư mục không giao nhau; không follow symlink; temp là tập con cache, không cộng thêm. Cache wheel/archive là bản sao vật lý riêng, đã tính một lần; không cộng lại số download trong inventory. 2distributions bootstrap và67package resolver thực cài có trong runtime_freeze/accounting. Không dọn cache có trước; temp do process tạo đã tự dọn, cuối cùng0byte.

Snapshot trước/sau, module.__file__, cache env, distribution versions và breakdown có ở `before_snapshot.json`, `install_accounting_final.json` (lịch sử) và `install_accounting_v2.json` (hiện hành). `df -B1` được lưu trong accounting; Windows Get-Volume bị từ chối quyền đọc, kiểm chéo read-only .NET DriveInfo trả cùng quy mô dung lượng, thời điểm đo khác nên có chênh vàiKB.

### Ngoại lệ cần ghi trung thực

Không đổi metadata của pip/HuggingFace/Torch/UV cache hiện có trong home. Mọi core module thực import nằm trong runtimeD. Tuy nhiên `.cache/ubuntu-pro/ubuntu-pro.log` **đã có từ15/09/2026** được chương trình update-motd của login shell cập nhật lúc18:53UTC; file15.548bytes. Đã chuyển lệnh còn lại sang `bash --noprofile --norc`, không xóa/sửa log hoặc cấu hình hệ thống. Vì vậy kết luận là **cài/package/model/cache mới chỉD**, có ngoại lệ log hệ điều hành có sẵn; không tuyên bố mọi process hệ thống hoàn toàn không ghi ngoàiD.

## 3. Kiểm thử thực chạy

| Runtime / command | PASS | SKIP | FAIL | Log trong evidence root |
|---|---:|---:|---:|---|
| Env dự án có sẵn: `python -m unittest discover -s tests -v` | 151 | 8 | 0 | `full_project_tests_final.log` |
| Runtime neuralD: `"$TASK_PYTHON" -m unittest discover -s tests -p test_modeling_pipeline.py -v` | 50 | 0 | 0 | `neural_tests_final.log` |
| Runtime CRF có sẵn: discover `test_sprint3_experiments.py` | 13 | 0 | 0 | `crf_runtime_tests.log` |
| Runtime neuralD: discover `test_neural_local_validation.py` | 2 | 0 | 0 | `local_validation_tests_final.log` |
| Runtime neuralD: discover `test_frozen_error_analysis.py` | 2 | 0 | 0 | `frozen_taxonomy_tests_final.log` |

8skip trong env dự án là6Torch +1Deepparse +1CRF, vì không cài vào env đó. Những test tương ứng đã chạy ở runtime chuyên biệt. Không cộng các suite chồng lặp thành số test độc lập hoặc gọi toàn suite dự án là khôngskip.

Các test modeling bao phủ verifier/leading zero/full parent/time interval/name ambiguity/multiple targets/non-atomic, raw/NFD/BIO, CRF brute-force/Viterbi/gradients, T1mask, actual Deepparse container/signatures và checkpoint round-trip. Regression trong test_data_pipeline kiểm chênh dấu chỉ là diagnostics, NFC→raw NFD offsets và basename checkpoint portable.

Lỗi đầu tiên và lệnh sai discovery được lưu trong logs round1/round2; không dùng chúng làm bằng chứng PASS. Đã sửa checkpoint temporary basename rồi chốt lại suite. `pip check` PASS. Pretrained PhoBERT forward trên câu tự soạn là bằng chứng riêng với tiny fixture, không phải benchmark.

## 4. Bất biến và phạm vi

Đã kiểm `251` file trong ledger trước/sau; `frozen_changed=[]`. Gồm corpus train/dev, baseline v2/v3/run frozen, s3_v1/s3_v2, raw code CSV và byte hash của test-hold manifest. Metadata ID/source line/hash của hold chỉ được existing regression test dùng để kiểm anti-leakage; không đọc địa chỉ/nhãn test100 hoặc đưa test vào model/debug/tune.

- Corpus manifest: `9c91b77fa220e41b1b1067e5e99b216b7b4b2176181674b340f16dec134947bf`.
- Gazetteer s3_v2 manifest: `fb350c06b3a3d1dca9ceb6de65695fa533ac20ea3bda3f1abd8465951f8646d9`.
- Raw CSV hashes và frozen run/input hashes ở báo cáo24/25 và ledger.
- Task543 giữ T0, mask T1 theo manifest; không sửa annotation/split/100ID test.
- Colab/training/prediction benchmark/neural metric đều NOT_RUN.

Mã mới: scripts36/37, source reconciliation, frozen taxonomy và tests. Sửa nhỏ checkpoints.py (portable tempfile) và alignment.py (NFC chỉ cho input segmenter, raw offsets giữ). Không có model checkpoint nghiên cứu được tạo; tiny checkpoint fixture ở temp đã xóa.

## 5. Phần còn lại và việc chủ dự án cần làm

| Cổng | Điều kiện để mở | Ai thực hiện tiếp |
|---|---|---|
| Mã hành chính/provenance | Official dated export/query hoặc catalogue + amendments, full key, locator, hash, điều kiện dùng nguồn, transcription approved | Chủ dự án cung cấp thông tin nguồn gốc nếu có; agent tiếp tục extraction/verifier; không yêu cầu tự đoán615mã |
|29case PhoBERT alignment | Policy/version ánh xạ vị trí dấu có bằng chứng, hoặc segmenter giữ literal; giữ gold/split và test đủ300 | Agent có thể thiết kế/hiện thực ở lượt tiếp; không cần bạn gán lại300mẫu |
| Native full FastText | >=10GiB RAM available, đủ disk reserve, license/revision/embedding/checkpoint lock rõ | Chủ dự án chọn máy đủ tài nguyên; agent kiểm/tải/chạy sau khi cổng qua |
| Training neural | Phê duyệt mở training, alignment/resource gates qua, disk budget20GiB theo protocol hiện hành | Chưa thuộc lượt này; không đổi protocol để qua gate |
| Test100 | Partner hoàn tất export/QA/phê duyệt khi mở riêng nhiệm vụ test | Không cần chờ để dùng các artifact audit/runtime của lượt này |

Hiện không cần bạn sửa nhãn, Submit hoặc export lại300mẫu. Các blocker kỹ thuật có thể giao agent xử lý tiếp; chưa đủ dữ kiện để gọi Sprint3 hoặc neural experiments hoàn tất.

## Follow-up ngày 03/10/2026 — căn chỉnh PhoBERT đã xử lý

Trạng thái “29 case alignment” ở bảng trên là snapshot lúc phát hành báo cáo27 và đã được giải quyết. Processor `phobert_raw_unit_pool_v2_tone_relocation` cùng audit runtime thật đạt 240/240 train + 60/60 dev exact, gold alignment QA 300/300 exact, không còn reject; không gán nhãn lại và không sửa corpus. Full regression suite trong WSL đạt 153 PASS / 8 SKIP / 0 FAIL. Chi tiết, policy, hashes và artifact nằm trong [báo cáo alignment 28](28_phobert_alignment_tone_relocation_20261003.md). Training, prediction neural và test100 vẫn chưa chạy trong lượt này.
