# Ma trận mô hình Sprint 3 — bản khóa cấu hình trước thực nghiệm

**Ngày chốt:** 25/09/2026. **Phạm vi:** năm cấu hình baseline mới và một mô hình đề xuất; đây là đặc tả thực nghiệm, chưa phải kết quả huấn luyện. Kết quả hiện hành `baseline_v3_fuzzy` được kiểm toán tại [baseline_run_audit.md](baseline_run_audit.md); nó chỉ là mốc **5 trường, oracle mode theo protocol**, không phải phép đo T0 11 span hay T1 tự động.

## 1. Hai track và hợp đồng so sánh

| Track | Gold | Input khi inference | Đầu ra/metric chính | Điều kiện so sánh |
| --- | --- | --- | --- | --- |
| 5 trường tương thích | `SoNha`, `TenDuong`, `PhuongXa`, `QuanHuyen`, `TinhThanh` trong benchmark 01/02/03/04/06 | Chỉ chuỗi địa chỉ; mode oracle nếu có phải là một cấu hình riêng | Exact cả bản ghi, micro/macro F1 theo trường, lỗi gán `QuanHuyen`, coverage/abstain, latency | Cùng dataset hash, cùng mode và cùng quyền truy cập metadata |
| T0 11 span | Offset ký tự `[start,end)` theo 11 nhãn, trên test span gold đã nghiệm thu | Chỉ chuỗi địa chỉ | Exact span P/R/F1 micro, macro và từng nhãn; supported-label coverage | Cùng split hash, cùng guideline và chính sách offset |
| T1 | `cu`, `moi`, `Lai`; `khong_ro` là trạng thái từ chối/không chắc chắn khi inference | Chỉ chuỗi địa chỉ | Accuracy/macro F1, confusion, abstain | Không đưa `HeQuyChieu` gold vào input |
| T2 | Cặp chuyển hệ và mã đích được xác minh | Địa chỉ cũ và tài nguyên ánh xạ được khai báo | Exact mã đích, coverage, lỗi chọn sai | Data 07 báo riêng; không đưa vào F1 T0 |

Benchmark hiện có sáu tập 01/02/03/04/06/07 với 5.500 dòng; Data 05 chưa có. Benchmark này **chưa có gold span 11 nhãn**. Không chuyển 5 trường thành 11 span bằng cách suy đoán vị trí rồi xem đó là gold. T0 test cần được gán nhãn riêng, khóa trước khi tune. Gán nhãn toàn bộ benchmark không phải điều kiện bắt buộc nếu test span đại diện và tách khỏi train được khóa rõ nguồn, số mẫu, hash và coverage từng nhãn.

Gold T0 gồm `SoNha`, `TenDuong`, `Ngo/Hem`, `ToaNha/CanHo`, `PhuongXa`, `QuanHuyen`, `TinhThanh`, `MocDinhVi`, `HuongDi`, `GhiChu`, `Khac`. Mỗi span lưu text nguyên bản, offset half-open `[start,end)`, nhãn, sample ID và nguồn. Theo [guideline T0](span_11_annotation_guideline.md), `Khac` là span thực, `O` là nền; BIO có 23 trạng thái. Span phẳng không chồng lấp, gồm từ chỉ loại đơn vị và bỏ dấu phân cách bên ngoài. Round-trip `text[start:end]` phải đúng sau chuyển từ Label Studio và sau tokenization.

Split theo nhóm nguồn: cùng địa chỉ sạch và biến thể nhiễu, cùng hóa đơn/OSM node, cùng cặp chuyển hệ và các biến thể hành chính liên quan không được rơi vào train và test khác nhau. Hash train/dev/test và danh sách nhóm bị loại do trùng phải lưu trong manifest. Chỉ dùng dev để chọn checkpoint, threshold, alias hoặc hyperparameter; test được mở một lần sau khi khóa cấu hình.

## 2. Ma trận sáu cấu hình

| Model ID | Kiến trúc và đầu vào | Train/tune | Nhãn đầu ra và chuyển đổi | Track chính | Artifact bắt buộc | Giới hạn |
| --- | --- | --- | --- | --- | --- | --- |
| `DP-ZS-FT` | Deepparse pretrained `AddressParser(model_type="fasttext")`; chuỗi địa chỉ | Không train; khóa package, pretrained weights và cache hash | Nhãn native Deepparse → subset có quy tắc an toàn; trường không hỗ trợ để rỗng | 5 trường subset; T0 supported subset nếu có offset đáng tin | model/version, mapping native→schema, parser raw output, predictions, coverage | Không claim đủ 11 nhãn; không dùng gold để chọn mapping theo từng hàng |
| `DP-FT-FT` | Deepparse FastText pretrained rồi `retrain(..., prediction_tags=...)`; chuỗi địa chỉ | Train/dev span gold đã nghiệm thu; checkpoint tốt nhất theo dev | Custom tags → span 11 nhãn nếu word/char alignment pass; từ span trích 5 trường | T0 và 5 trường tương thích | train/dev hash, label map, checkpoint hash, alignment log, config, predictions | Seq2seq tagger của Deepparse, **không** phải CRF |
| `CRF-INDEP` | CRF chuỗi độc lập; token/context, shape, dấu, viết tắt, tiền tố hành chính, gazetteer versioned | Train/dev span gold; feature template, regularization, seed khóa | BIO 11 nhãn → offset ký tự → 5 trường | T0 và 5 trường tương thích | feature template, tokenizer, gazetteer hash, CRF checkpoint, label map | Không dùng embeddings hoặc nhãn test; CRF riêng hoàn toàn |
| `PHOBERT-CRF` | PhoBERT encoder + linear emission + CRF BIO với chuyển nhãn hợp lệ | Train/dev span gold; khóa checkpoint, segmenter, tokenizer, seed | BIO 11 nhãn trên token hợp lệ → offset chuỗi gốc → 5 trường | T0 và 5 trường tương thích | PhoBERT/segmenter hash, alignment diagnostics, checkpoint, config | Phải word-segment trước; special/padding/subword phụ không gắn loss |
| `HEUR-JW` | Candidate lookup từ gazetteer có version/as-of date + Jaro-Winkler xếp hạng | Không train neural; tune threshold/reject trên dev | Chỉ các trường/span có rule xác minh được; báo abstain | 5 trường và T0 supported subset | gazetteer/alias hash, threshold, candidate trace, predictions | Jaro-Winkler là ranking; không phải metric fuzzy v3 |
| `PROPOSED-DYN` | PhoBERT encoder + đầu span + đầu T1 `cu/moi/Lai/khong_ro` + constrained decode 2/3 cấp | Train/dev T0+T1; cùng split và budget tune như baseline; ablation bỏ constraint | T0 11 nhãn, T1, 5 trường; T2 chỉ nếu có module và gold riêng | T0/T1/5 trường | checkpoint từng head, rules/threshold, ablation, trace, model hash | Chỉ cấm `QuanHuyen` khi hệ mới được xác nhận; với `Lai/khong_ro` giữ giả thuyết |

### `DP-ZS-FT` — adapter zero-shot

Lưu raw tag trước mọi ánh xạ. Bảng mapping phải ghi từng tag native, ví dụ `StreetNumber → SoNha` và `StreetName → TenDuong` là ứng viên cần xác nhận trên pilot tiếng Việt. `Municipality` và `Province` có thể biểu thị cấp hành chính khác nhau; chỉ gán `PhuongXa`, `QuanHuyen`, `TinhThanh` khi rule dùng **đầu ra và chuỗi input** đủ xác định. `Unit`, `Orientation`, `GeneralDelivery` không tự động thành nhãn của schema. Tách score trên trường hỗ trợ khỏi coverage; nếu báo exact 5 trường, các trường thiếu vẫn là rỗng và phải giải thích rõ. Deepparse công bố pretrained FastText/BPEmb và native tags trong [tài liệu parser](https://deepparse.org/parser.html).

### `DP-FT-FT` — chuẩn bị dữ liệu gán nhãn cho Deepparse

Chuyển gold char span sang đơn vị token Deepparse bằng alignment có log; từ chối mẫu có token cắt ngang span khi không có quy tắc nhất quán. Khóa dictionary `prediction_tags` (bao gồm EOS theo API), checkpoint và mọi tham số `retrain`. Dùng dev riêng, không để API tự chia ngẫu nhiên train chứa họ mẫu của dev. Báo lỗi alignment và coverage từng nhãn; test chỉ một lần sau khi checkpoint đã chọn. BPEmb có thể là ablation ID riêng `DP-ZS-BPE`/`DP-FT-BPE`; không trộn vào cấu hình FastText. Tài liệu Deepparse xác nhận custom `prediction_tags` và lưu checkpoint qua API retrain: [parser/retrain](https://deepparse.org/parser.html).

### `CRF-INDEP` và `PHOBERT-CRF` — cùng nhãn, khác encoder

CRF độc lập dùng feature thủ công từ chính chuỗi; mọi từ điển/alias phải có version, hiệu lực thời gian và không được học từ test. PhoBERT-CRF dùng cùng gold và split để so kiến trúc công bằng. Với cả hai, luật chuyển nhãn BIO, masking, cách xử lý `Khac/O`, span dài và truncation phải khóa trước huấn luyện. PhoBERT cần đầu vào đã phân đoạn từ; giữ bảng căn chỉnh từ token/subword về ký tự gốc và kiểm `text[start:end]` sau decode. [PhoBERT](https://huggingface.co/docs/transformers/en/model_doc/phobert), [hướng dẫn token classification](https://huggingface.co/docs/transformers/en/tasks/token_classification).

### `HEUR-JW` — đối sánh có từ chối

Pipeline: chuẩn hóa bảo toàn dấu và loại đơn vị → nhận diện ứng viên bằng alias đã kiểm → rank Jaro-Winkler → kiểm mã và tính hợp lệ theo as-of date → chọn hoặc abstain. Chỉ sử dụng cạnh hành chính có trong nguồn chuẩn; không suy diễn đích split/M-N khi thiếu bằng chứng. Báo threshold dev, phân bố score, coverage, precision trên accepted, tỷ lệ reject và lỗi chọn sai mã. Normalized Levenshtein của `baseline_v3_fuzzy` vẫn là **metric chẩn đoán đầu ra**; nó không thay Jaro-Winkler ranking hay exact identity.

### `PROPOSED-DYN` — nhận biết cấu trúc 2/3 cấp

T1 dự đoán từ chính chuỗi. Decoder áp ràng buộc `QuanHuyen` rỗng khi hệ mới đã được xác nhận; giữ phương án cũ/lai hoặc abstain khi T1 không chắc. Ablation dùng cùng encoder, dữ liệu và seed nhưng bỏ ràng buộc để đo lợi ích thực. Báo: false-positive rate của `QuanHuyen` trên gold `moi` không có quận với mẫu số cụ thể; recall trên `cu`/`Lai`; F1 T0 từng nhãn; T1 confusion và abstain. Không suy ra “0 ảo giác mọi trường hợp” từ rule cấu trúc. Con số 77,5% trong báo cáo cũ chỉ dùng khi đã xác minh run, tập và mẫu số.

## 3. Hợp đồng run và thứ tự triển khai về sau

1. **Data gate:** guideline 11 span, pilot nghiệm thu, adjudication, thống kê nhãn, split/hashes. T0 supervised chờ gate này; adapter zero-shot có thể viết trước nhưng không báo F1 toàn nhãn.
2. **Environment gate:** `requirements.txt` hiện thiếu Deepparse, PyTorch/Transformers và thư viện CRF. Lập bảng version, checkpoint, yêu cầu RAM/GPU, tương thích WSL/Python và dung lượng tải. `AGENTS.md` không cho cài mới nếu người dùng chưa cho phép; nhiệm vụ này không cài.
3. **Interface gate:** mỗi model nhận chuỗi địa chỉ, model ID và cấu hình đóng băng; xuất `sample_id`, raw output, span `(start,end,label,text)` nếu hỗ trợ, năm trường nếu hỗ trợ, `status`, `latency_ms`, `abstain`, `trace`. Oracle input/metadata chỉ có trong run ID riêng.
4. **Pilot rồi full:** `HEUR-JW`/`CRF-INDEP` → `DP-ZS-FT` → `DP-FT-FT` → `PHOBERT-CRF` → `PROPOSED-DYN` và ablation; có thể đổi thứ tự theo tài nguyên nhưng không đổi split/protocol sau khi xem test.
5. **Manifest mới:** mỗi run ID riêng; lưu benchmark/split/annotation/gazetteer hash, checkpoint/tokenizer/segmenter hash, package và code hash, seed, hyperparameter, hardware, input mode, output hash, lỗi runtime. Không ghi đè run v2/v3.
6. **Báo cáo:** bảng T0 11 nhãn, 5 trường, T1 và T2 tách riêng. So sánh chỉ khi cùng test hash, track và quyền truy cập input. Báo per-label support; tránh micro F1 toàn nhãn cho model chỉ hỗ trợ subset.

Nếu thử ViBERT, đặt ID riêng `VIBERT-CRF` hoặc `PROPOSED-VIBERT-DYN` với checkpoint/tokenizer hash riêng; không thay encoder dưới ID PhoBERT. Quy tắc `Khac/O` và overlap đã khóa trong guideline; checkpoint cụ thể vẫn phải ghi trong run manifest **trước** huấn luyện.
