# Các bước còn lại: hoàn thiện local trước, chạy Colab sau

**Giao agent hiện thực:** dùng [prompt43 — P0 và đầy đủ L1–L5](43_agent_prompt_local_completion_before_colab.md). File có logic, hợp đồng input/output, kiểm thử, điều kiện phát hành và mẫu báo cáo; giai đoạn local không chạy thực nghiệm Colab hoặc chấm test thật.

## 1. Nền đã có và cổng hiện đang chặn

- Train/dev đã duyệt **240/60**, alignment PhoBERT thật **300/300**, giữ mask T1 của `s3_60931c369cbd85ef` và mọi T0 của mẫu.
- HEUR-JW và CRF độc lập đã có run dev; kết quả hiện hành **88,01% / 90,56%** exact-span F1. Các run cũ giữ bất biến.
- Code huấn luyện, checkpoint, processor, calibration, ablation và resource gate đã triển khai. Đây chưa phải kết quả neural đã huấn luyện.
- **Test export mới còn thiếu 1 task, 1 task cần chọn annotation và các ca hệ cần chốt.** Xem [QA chi tiết](41_test100_export_qa_20261004.md).
- Lượt test này là **AI-assisted human review**, không gọi gán mù độc lập; agreement giữa người gán `NOT_MEASURED`.

## 2. Các việc local theo thứ tự

| Ưu tiên | Việc | Agent làm | Chủ dự án cần làm | Đầu ra/nghiệm thu |
| --- | --- | --- | --- | --- |
| **L1** | Chốt QA và phán quyết test100 | QA export mới, đối chiếu ID/text, offset và mọi annotation; gắn quyết định với hash | Sửa/chốt các mục trong báo cáo41, export toàn bộ 100; xác nhận người duyệt và đủ 100 đã xem | 100/100 candidate hợp lệ, ca khó có quyết định, biên bản duyệt |
| **L2** | Phát hành gold test và corpus ba split | Kiểm split/group/gần trùng; dùng lại 138 quyết định đã kiểm hash nếu tập cặp không đổi; tạo release mới bất biến | Xác nhận phán quyết còn mở ở L1 | `test_gold_v1`/release mới và `corpus_v1`: 240 train / 60 dev / 100 test; manifest/hash, coverage, nguồn và policy gán hỗ trợ |
| **L3** | Chuẩn bị runner/scorer final test và protocol | Làm entry point test riêng, kiểm gate/hash bằng fixture; khóa input chỉ text; mẫu report 6 cấu hình | Chốt protocol nếu có thay đổi thực sự về scope/budget | Runner/test config/metric schema; fixture PASS, **chưa inference/chấm thật test** |
| **L4** | Hoàn chỉnh resource lock và gói Colab mới | Audit native FastText/Deepparse nguồn/license/hash/RAM; kiểm phụ thuộc gói; dựng ZIP/notebook version mới, kiểm tĩnh và hàm độc lập local | Chỉ bổ sung bằng chứng nguồn/quyền dùng nếu upstream chưa rõ; chọn nơi lưu artifact khi chạy Colab | Gói train/dev tái lập được, resource inventory và blocker riêng DP; không có test gold trong training ZIP |
| **L5** | Nghiệm thu local và bàn giao | Full regression, hash corpus/gazetteer/run frozen, offset/T1 mask, QA release/bundle; cập nhật tài liệu và commit/push khi được giao | Cung cấp phiên GitHub nếu thiếu đăng nhập; nhận artifact ngoài Git | Báo cáo PASS/SKIP/blocker, manifest ZIP, hướng dẫn vận hành và trạng thái Git thực |

### L1 — Phán quyết trước phát hành

Sửa tại Label Studio rồi export vòng mới; không vá JSON raw hay nhãn đã phát hành. Ca không phân biệt được hệ có thể giữ span `khong_xac_dinh` và T1 null. Không tự bỏ task khó hoặc thay 100 ID.

Lệnh QA vòng mới từ môi trường WSL của dự án, dùng output directory mới:

```bash
python -m scripts.53_qa_test100_annotation \
  --export data/interim/annotation/sprint03/exports/test_assisted_v1/test100_assisted_round2.json \
  --assisted-manifest data/interim/annotation/sprint03/test100_assisted_v1/manifest.json \
  --output-dir data/interim/annotation/sprint03/test100_review_round2_v1
```

Nếu có nhiều annotation, agent lập bản đồ ID sau kiểm tương đương hoặc quyết định của người duyệt rồi chạy **thư mục QA mới** với `--adjudication-map <file.json>`. Cần 100 converted, không lỗi cấu trúc và quyết định nội dung đã duyệt trước L2; cảnh báo T1 không tự ghi đè nhãn.

Các quyết định khó ghi `sample_id`, task/annotation ID, quyết định, lý do/bằng chứng, người và ngày; hash export, guideline, XML được khóa cùng biên bản. Giữ cờ thật có lý do. Kiểm cấu trúc và duyệt nội dung là hai bước khác nhau.

### L2 — Release ba split

1. Kiểm hash bản train/dev hiện có và số lượng/split assignment.
2. Đối chiếu tất cả 100 ID/text test với input frozen; nhóm nguồn theo queue, không suy từ tên địa chỉ.
3. Audit trùng ID, exact text, normalized text, source group và gần trùng. Quyết định cũ chỉ dùng lại khi đúng tập cặp, text và hash.
4. Phát hành **thư mục phiên bản mới**, giữ nguyên bytes train/dev đã duyệt và manifest nguồn cũ. Manifest tổng liên kết hai release, không sửa trạng thái trong manifest train/dev đã khóa.
5. Tạo `test_input.jsonl` chỉ `{sample_id,text}` riêng với gold. Lưu approval/provenance/coverage, nguồn gán AI hỗ trợ và mask T1 đúng phạm vi. Không tự mask lỗi nội dung chưa phán quyết để làm cho gold qua QA.

Phát hành gold chỉ sau đủ 100 và các quyết định. Canonical 98 mẫu hiện hành không được gọi là test100 hoặc corpus đủ ba split.

### L3 — Protocol và hạ tầng final test

- Ma trận: **HEUR-JW, DP-ZS-FT, DP-FT-FT, CRF-INDEP, PHOBERT-CRF, PROPOSED-DYN**; ablation bỏ ràng buộc dùng cùng checkpoint proposed.
- Khóa trước phạm vi dữ liệu, candidate grid, seed/budget và tiêu chí chọn trên dev; mapping native tag và luật offset có version. Hash checkpoint/mapping/decoder thực được khóa **sau training và chọn bằng dev**, trước inference test.
- T0: exact-span P/R/F1 toàn schema 11 nhãn, theo nhãn và nguồn; nhãn không hỗ trợ vẫn gây FN. Báo thêm supported subset/coverage/abstain, không gộp với điểm 5 trường.
- T1: macro-F1/accuracy/coverage/abstain với null/exclusion đúng manifest. HEUR/CRF không có T1 phải báo `NOT_IMPLEMENTED`, không suy từ GT để tạo điểm.
- Lỗi Quận: ghi mẫu nào thực sự có gold T1 mới, tử số và mẫu số; tách hallucination/omission. Một rule cấm Quận khi confidence cao không chứng minh mọi lỗi địa chỉ đã triệt tiêu.
- Tránh ghi kết luận tốt cho nhãn test/dev không có hoặc rất ít support. Test hiện chưa phát hành; sau release phải tính lại coverage từ gold thật.
- Runner final không dùng những gate dành riêng cho `dev_input.jsonl` bằng cách bỏ kiểm tra. Tạo luồng test được cho phép riêng, vẫn tách inference text-only → freeze prediction → scorer đọc gold.
- Bước này được kiểm bằng fixture và artifact giả lập khai báo rõ; không tạo prediction/metric test hoặc thay feature/threshold theo các ví dụ đã đọc khi QA annotation.

### L4 — Gói Colab cần rà lại trước bàn giao

Gói cũ đã chuẩn bị nhưng chưa thực thi. Kiểm dependency closure bằng các đường dẫn code thật, không chỉ cú pháp notebook.

Một điểm đã xác định: `src/modeling/datasets.py::prepare_data` đọc `reannotation_v2_release1/trace.jsonl`, `generation_manifest.json` và queue liên quan. Luồng Kaggle đã có xử lý phụ thuộc này; **gói Colab cũ cần kiểm và bổ sung chúng nếu thiếu**, giữ hash/provenance train/dev. Không chuyển file test vào gói chỉ để sửa thiếu dependency.

Gói mới cần:

- Code/config/protocol, corpus train/dev/manifest/coverage/mask và mọi trace/queue cần cho prepare.
- Processor/resource lock PhoBERT/VnCoreNLP/Java đúng revision/hash/license; Python và dependency profile đã pin.
- Lượt **preflight + pretrained smoke ngắn + checkpoint roundtrip** đứng trước full training; mặc định full training tắt, có báo cáo GPU/RAM/disk thực tế.
- Run ID/thư mục mới; best/last checkpoint, optimizer/RNG, resume, backup và checksum.
- Deepparse zero-shot/fine-tuned có lock native FastText + checkpoint riêng đã cleared. Recipe/template không phải active lock. **DP còn blocker license/checkpoint/full embedding**; không thay embedding hoặc bỏ gate để báo đã hoàn thành baseline.
- Không đưa venv/cache Windows/WSL, token, raw annotation hay tài liệu nguồn chưa rõ quyền chia sẻ vào ZIP.

Chỉ ghi `PREPARED_LOCAL_VERIFIED` khi chưa chạy Colab; GPU/pretrained training chưa chạy vẫn pending. Nếu cần cài/tải local mới: inventory trước, mọi vị trí mới trên D, báo package/version/source và GB/GiB thực đo.

### L5 — Kiểm thử và bàn giao

Full suite theo AGENTS.md; focused runtime khi thay đổi neural/CRF; kiểm snapshot corpus/split/gazetteer/run, toàn bộ hash ZIP và khả năng bootstrap đường dẫn. Chỉ báo PASS cho kiểm đã thực chạy; ghi SKIP/blocker và phạm vi fixture.

Code/config/tests/docs có thể đưa nhánh code `sprint3_huy` khi được giao push; file interim/raw export/weights không stage. Bàn giao riêng ZIP và manifest có hash. Tài liệu phải ghi ai gán, AI hỗ trợ, IAA chưa đo, nhãn thiếu support và các nguồn unresolved.

## 3. Có thể làm song song ngay

**L3 và L4** có thể thực hiện khi chủ dự án sửa L1. Phần fixture/docs của L5 cũng làm ngay. **L2 và nghiệm thu release cuối L5** chờ L1 qua cổng. Không cần gán lại train/dev 68+232 để chuẩn bị các việc này.

Data05 mốc/hướng giữ `DEFERRED_BY_USER`, VQA giữ `HOLD`, mã hành chính chưa đủ bằng chứng giữ `unverified`. Đây là các giới hạn công bố; không tự mở thu thập/gán mới để làm đẹp support. T3, LLM/RAG, FastAPI/Docker ngoài scope Sprint3 đang thực hiện.

## 4. Các bước cuối trên Colab

1. **Preflight và smoke**: upload gói train/dev/resource đã khóa; kiểm GPU/RAM/disk, import, tokenizer/segmentation/offset, forward/backward ngắn và checkpoint. Chưa qua thì sửa integration rồi chạy lượt mới.
2. **Thực nghiệm neural**: DP-ZS-FT sau resource gate; DP-FT-FT, PHOBERT-CRF, PROPOSED-DYN train chỉ 240, chọn candidate/checkpoint trên 60 dev theo protocol. Không đưa test vào optimizer, calibration hoặc lựa chọn mapping.
3. **Chốt dev**: lưu raw output, prediction, latency, metrics, error analysis; proposed calibration chỉ dev; chạy constraint on/off cùng best checkpoint. Khóa checkpoint/config/mapping/decoder và resource hash.
4. **Mở final test**: inference từ 100 chuỗi text-only bằng cấu hình đã khóa cho cả 6 cấu hình đã chạy được; freeze prediction; scorer mới đọc gold. HEUR/CRF nhẹ có thể chạy local tại giai đoạn final này, dùng cấu hình đã chọn trên dev.
5. **Tổng kết**: bảng T0/T1/5 trường tách riêng, coverage/support/abstain, hallucination Quận có mẫu số, ablation, artifact/checksum và báo cáo Sprint3. Cấu hình chưa chạy ghi đúng blocker, không tạo hoặc ước lượng metric thay thế.

Nếu DP resource gate chưa qua, có thể hoàn thành PhoBERT/proposed trước nhưng **chưa thể nói đủ mọi baseline Sprint3**. Kết quả dev, QA label và fixture PASS không thay cho kết quả test cuối.
