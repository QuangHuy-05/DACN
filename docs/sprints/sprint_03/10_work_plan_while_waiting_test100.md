**Kế hoạch làm việc trong lúc chờ 100 test — Sprint 3**

**Nghiệm thu hiện hành 02/10/2026:** [nhiệm vụ 1–4 đã được xử lý và phát hành train/dev](13_tasks_01_04_completion_20261002.md): `corpus_train_dev_v2`, 240/60 mẫu, 1.057/284 span, audit PASS. Chủ dự án giữ 537/543; 543 ghi ngoại lệ hệ và mask riêng T1, giữ T0. Trạng thái `TRAIN_DEV_APPROVED_TEST_PENDING`, chất lượng `APPROVED_WITH_DECLARED_EXCEPTIONS`. Runner/scorer/phát hành đã kiểm, 87/87 + 18/18 test PASS. Các cập nhật bên dưới là lịch sử trước khi chốt; bước làm tiếp là **nhiệm vụ 5 HEUR-JW dev**, 100 test chờ partner.

Ngày lập: **02/10/2026**. Phạm vi: nghiệm thu lượt gán lại 68 pilot + 232 batch, chuẩn bị train/dev và thực nghiệm baseline trên dev. Chủ dự án đã chọn ưu tiên baseline, để các bước fine-tune neural về cuối; thu dữ liệu thật cho mốc/hướng vẫn `DEFERRED_BY_USER`, VQA vẫn `HOLD`.

**Cập nhật thực thi:** [báo cáo nhiệm vụ 1–4](11_tasks_01_04_review_20261002.md) ghi QA mới 68/68 + 232/232, audit 138 cặp PASS, 24 task batch cần sửa/phán quyết, candidate 223/53 ở `BLOCKED_CONTENT_REVIEW`, runner/scorer đã qua kiểm thử. Bảng/hash dưới đây giữ như lịch sử thời điểm lập kế hoạch; batch được chủ dự án cập nhật trong cùng tên file và có hash mới `044e2b805227dda2dce748afc9bc6e7d0dae216fbcda6c2466eabdc5c388bf2d`. Dùng snapshot/báo cáo QA mới để làm việc tiếp, không dùng QA cũ cho export đã đổi.

**Cập nhật tiếp theo sau sửa 24 task:** [báo cáo hiện hành](12_tasks_01_04_followup_20261002.md) dùng export `ffb10418...`, QA 300 mẫu hợp lệ cấu trúc; còn 7 task cần chốt nội dung, candidate 235/58 và 7 cách ly. 80/80 test toàn repo, 16/16 span/CLI trên Python 3.11 pass. Chưa phát hành gold train/dev và chưa chạy baseline dev thật; không dùng số liệu lịch sử phía dưới như trạng thái mới nhất.

**Đầu vào hiện có và mức xác minh**

| Export | Số task / ID duy nhất | Có annotation không bị hủy | ID thiếu / text lệch |
| --- | ---: | ---: | --- |
| `data/interim/annotation/sprint03/exports/reannotation_v2/pilot_assisted_round1.json` | 68 / 68 | 68 | 0 / 0 |
| `data/interim/annotation/sprint03/exports/reannotation_v2/batch_assisted_round1.json` | 232 / 232 | 232 | 0 / 0 |

Pilot đã được chủ dự án cập nhật sau khi bản export đầu thiếu hai task. Kết quả trong bảng là **kiểm kê export**, chưa chạy converter QA cho lượt mới và chưa duyệt nội dung thành gold. Project ID trong export lần lượt là 5 và 6; khi xử lý phải dùng `sample_id` để liên kết dữ liệu, không giả định task ID của các project cũ giống nhau.

Hash export tại thời điểm lập kế hoạch:

- Pilot: `2fd36521009b0fe8e902a73c71d99c9fbb6c6d05ca19ec1371a1144c237615e1`.
- Batch: `1e77d36538e5c7b284e89a32f7bf83b407ae18e6486f5a35da69283daa8ee661`.

Cổng 138 cặp đã `AUDIT_PASS_WITH_HUMAN_NEAR_DUP_REVIEW`; bằng chứng tại [test100_split_gate_20261001.json](test100_split_gate_20261001.json). Danh sách ID/text, phân nhóm và phân bổ 240 train / 60 dev / 100 test vẫn giữ bản đã khóa. Partner đang gán 100 test mù. Agreement độc lập `NOT_MEASURED`: vòng 68/232 có prediction và partner gán một tập khác, không phải hai lượt độc lập trên cùng mẫu.

**1. Chạy QA hai export — thực hiện trước mọi thực nghiệm dùng gold mới**

Agent dùng converter hiện có, ghi output vào thư mục review mới. Giữ export nguồn và các gói candidate đã phát hành để truy nguyên phiên bản; sửa lỗi trong Label Studio rồi export vòng kế tiếp.

Mở terminal WSL riêng với terminal đang chạy Label Studio:

```bash
cd /mnt/d/DACN
source ~/.venv_labelstudio311/bin/activate

python -m scripts.11_convert_label_studio_pilot \
  --export data/interim/annotation/sprint03/exports/reannotation_v2/pilot_assisted_round1.json \
  --queue data/interim/annotation/sprint03/annotation_queue_batch01.csv \
  --output-dir data/interim/annotation/sprint03/reannotation_v2_review_20261002/pilot_round1

python -m scripts.17_convert_span_annotation_batch \
  --export data/interim/annotation/sprint03/exports/reannotation_v2/batch_assisted_round1.json \
  --queue data/interim/annotation/sprint03/annotation_queue_batch02_train_dev.csv \
  --role train_dev_batch02 \
  --output-dir data/interim/annotation/sprint03/reannotation_v2_review_20261002/batch_round1
```

Kiểm số lượng, text, substring/offset `[start,end)`, nhãn, hệ của region, overlap, annotation bị hủy và nhiều annotation trên một task. Khi có nhiều annotation, người duyệt chọn annotation ID qua adjudication map; không tự chọn theo điểm prediction hoặc thứ tự kết quả.

**Đầu ra:** báo cáo QA pilot/batch, canonical candidate và danh sách cần review. **Cổng đi tiếp:** đủ 68 và 232 annotation được chọn, không thiếu task, không lỗi cấu trúc. `READY_FOR_HUMAN_REVIEW` là trạng thái chờ bước 2.

**2. Phán quyết nội dung và duyệt lượt gán mới**

Agent tổng hợp các flag/note từ hai bộ cùng cảnh báo semantic bổ sung; chủ dự án quyết định ca còn mơ hồ. Ưu tiên:

- Hệ `SoNha`/`TenDuong` là `khong_xac_dinh`; `QuanHuyen` là `cu`.
- Tên tỉnh/phường có cùng bề mặt ở hai thời kỳ không được ép thành `cu`/`moi` chỉ theo nhãn nguồn sinh.
- Không suy `moi` chỉ vì vắng huyện; chỉ có T1 khi chuỗi đủ bằng chứng. T1 bỏ trống giữ là null, không điền từ `HeQuyChieu` nguồn.
- Ranh giới gồm từ loại đơn vị có trong chuỗi; dấu phân cách ngoài span để O; không nhầm `Khac` với chữ ngoài địa chỉ/OCR hỏng.
- Mốc/hướng, ghi chú và cụm “nay là”; ca `s3_c1f7b490f4d7c9bc` có số nhà `8 (660/8)` cần phán quyết ranh giới.
- Prediction bỏ sót hoặc tạo dư span: kiểm nội dung ngoài các vùng màu, không chỉ đếm các vùng đã có.

Ghi log mới cho vòng v2 gồm tối thiểu `sample_id`, annotation ID được chọn, quyết định giữ/sửa, lý do, người/ngày duyệt, export hash và guideline version. Những cờ phản ánh sự mơ hồ thật có thể được giữ sau phán quyết. Người duyệt xác nhận phạm vi đã rà và các quyết định; agent không tự ký thay người duyệt.

Guideline vẫn là `s3-span-v1.1`. Nếu một quyết định đòi đổi quy tắc đang khóa, ghi tác động và phối hợp với partner đang gán test trước khi áp phiên bản mới. Không đổi guideline âm thầm giữa hai lượt gán.

**Đầu ra:** decision log v2, canonical đã được duyệt và biên bản gắn hash export/XML/guideline. Pilot gold v1 giữ để truy nguyên; lượt mới được phát hành bằng version mới sau duyệt. **Cổng đi tiếp:** toàn bộ 300 mẫu có trạng thái rõ; các ca chặn phát hành đã được giải quyết.

**3. Đóng gói train/dev để dùng ngay**

Agent ghép canonical pilot mới được duyệt và batch mới được duyệt bằng `sample_id`, sử dụng:

`data/interim/annotation/sprint03/split_preflight_review_20261001/train_dev_split_assignments.csv`.

Giữ assignment đã khóa; không chia ngẫu nhiên lại 300 mẫu và không coi toàn bộ 68 là train hoặc toàn bộ 232 là dev. Mục tiêu hiện tại là **240 train / 60 dev** khi cả 300 mẫu đã được duyệt. Nếu phải quarantine mẫu, báo số thực đạt và ID/lý do; không tự bù bằng test hoặc biến thể test.

Kiểm tra không giao ID/group, không trùng exact/normalized text trái split, tham chiếu nguồn cha hợp lệ và không rơi vào nhóm benchmark đã reserve. Dùng metadata nhóm trong frozen test manifest để chặn giao train/dev–test; không cần nhãn của 100 test cho bước này. Liên kết lại bằng chứng 138 quyết định và hash assignment.

Thống kê riêng train và dev: số mẫu/span mỗi nhãn, hệ từng span, T1 `cu/moi/Lai/null`, nguồn observed/synthetic/derived, dạng nhiễu/thiếu/lai. Giữ đủ 11 nhãn trong bảng kể cả support bằng 0. Metadata nguồn phục vụ audit/stratification; input inference chỉ có chuỗi địa chỉ. T1 null không tham gia loss/chấm điểm như một nhãn cũ/mới.

**Đầu ra ứng viên:** `data/interim/annotation/sprint03/corpus_train_dev_v2_candidate/` gồm `train.jsonl`, `dev.jsonl`, manifest, coverage và audit. Sau duyệt, có thể phát hành gói `data/processed/annotation/sprint03/corpus_train_dev_v2/` với trạng thái `TRAIN_DEV_APPROVED_TEST_PENDING`. Manifest phải ghi version pilot v2/batch v2 thực dùng, thay vì gọi nhãn mới là pilot v1.

Chưa phát hành `corpus_v1` đủ ba split khi test chưa được duyệt. Subcommand `scripts.18_audit_corpus_split audit` hiện yêu cầu cả ba file; audit cuối chờ test, không cấp một test rỗng để báo PASS.

**4. Hoàn thiện runner và scorer cho thực nghiệm dev**

Repository đã có `src/evaluation/schema.py`, `span_scorer.py` và giao diện adapter. Agent phải kiểm chúng với hợp đồng [model_matrix.md](model_matrix.md), rồi bổ sung runner dev cần thiết; script 06 hiện chạy track benchmark 5 trường, không tự đại diện cho runner T0 đầy đủ.

Runner nhận split đã khóa và model config; xuất đúng một kết quả cho mỗi `sample_id`, kể cả runtime error/abstain. Adapter chỉ nhận text và cấu hình tài nguyên công bố, không nhận gold/source-system để chọn đáp án. Prediction lưu span trên text nguyên bản, raw output, status, latency và trace. Scorer đọc gold riêng sau inference.

Kiểm meaningful cases: Unicode/offset round-trip, dấu phân cách, span sai nhãn/sai biên, nhãn không hỗ trợ, mẫu abstain/runtime error, T1 null và mẫu số lỗi Quận. Lỗi chuẩn hóa/tokenization phải được báo, không silently drop sample. Khi sửa logic, thêm test phù hợp và chạy kiểm thử theo AGENTS.md.

**Đầu ra mỗi run dev:** prediction JSONL, metric JSON, run manifest, phân tích lỗi. Manifest lưu code/input/split/annotation/gazetteer/model hash, package, seed, cấu hình, phần cứng và quyền truy cập input. Tên run mới ghi rõ `dev`; không ghi đè baseline v2/v3.

T0 dùng exact-span P/R/F1 micro và từng nhãn; định nghĩa macro phải công bố với nhãn support 0. T1 chỉ chấm mẫu có gold T1 và báo coverage; `khong_ro` là từ chối của mô hình, không thay gold null. Đo lỗi `QuanHuyen` trên các mẫu gold `moi` thực sự có nhãn T1 với mẫu số cụ thể, đồng thời báo recall Quận trên `cu`/`Lai`.

**5. Chạy HEUR-JW trước**

Đây là baseline có adapter sẵn và không cần fine-tune neural. Agent rà adapter hiện tại, nạp **explicit** gazetteer `s3_v2`, khóa version/hash và ngày tham chiếu hoặc chính sách ngày từ input. Adapter hiện mặc định `s3_v1`; chưa đủ cơ sở gọi là hoàn tất yêu cầu lookup theo thời gian/chống mơ hồ trong ma trận.

Rà các điểm: tên trùng/cùng cấp, parent context, hiệu lực thời gian, alias audit, ties/độ chắc chắn, code status, trường hợp thiếu nguồn. Không chọn hệ chỉ theo ứng viên đầu tiên có tên trùng. Chuỗi mới hai cấp không được thêm huyện từ bảng tra. T0 có thể nhận diện tên đơn vị đã có bằng chứng dù mã cũ còn candidate; nếu báo mã chuẩn/T2 phải từ chối mã chưa xác minh.

Chọn ngưỡng và rule trên dev, lưu bảng thử ngưỡng, coverage, precision khi accepted và error analysis. Công bố supported labels; không gọi heuristic là mô hình nhận diện đủ 11 loại chỉ vì scorer dùng schema 11 nhãn. Phần nhận diện nhãn ngoài phạm vi vẫn là rỗng/abstain và phải hiện trong báo cáo.

**Đầu ra:** run HEUR-JW dev, config đã chọn, trace candidate và danh sách giới hạn Gazetteer. **Cổng đi tiếp:** output offset hợp lệ, không oracle metadata, cấu hình và tài nguyên truy xuất được bằng hash.

**6. Chạy Deepparse zero-shot và chuẩn bị supervised**

Agent lập inventory môi trường WSL/Python/RAM/GPU và bảng dependency/checkpoint/dung lượng cần tải. `requirements.txt` hiện chưa khai báo Deepparse, PyTorch/Transformers hoặc CRF; kiểm env thực tế trước. Tuân thủ AGENTS.md: cài dependency/tải tài nguyên trong phạm vi được chủ dự án cho phép, tránh dùng môi trường Label Studio để thử các gói có thể xung đột.

Với `DP-ZS-FT`, giữ pretrained FastText, lưu raw tag rồi áp mapping native→schema thống nhất. Xác minh offset theo text nguyên bản; không suy span gold từ 5 trường để chấm và không chọn mapping theo đáp án từng mẫu. Chạy dev, báo nhãn hỗ trợ/abstain/runtime/latency; cùng nguyên tắc manifest như HEUR-JW.

Sau train/dev được duyệt, có thể chuẩn bị tokenizer, BIO 23 trạng thái, feature template CRF, word/subword alignment, masking, truncation và config cho `CRF-INDEP`, `DP-FT-FT`, `PHOBERT-CRF`. Các supervised model có thể train/tune bằng train/dev khi gate dữ liệu đạt, không phải chờ nhãn test. Theo ưu tiên hiện tại, **thực nghiệm CRF độc lập có thể đi trước; fine-tune Deepparse/PhoBERT và mô hình đề xuất giữ cho lượt cuối**. PhoBERT-CRF và Deepparse fine-tuned cần huấn luyện để có kết quả; không thể hoàn tất các baseline đó chỉ bằng zero-shot.

**Đầu ra trong giai đoạn chờ:** DP-ZS-FT dev và bộ input/config/alignment dùng chung cho supervised; nếu triển khai CRF, bổ sung checkpoint và run dev. ViBERT là cấu hình khác nếu quyết định thử, không thay encoder dưới ID PhoBERT.

**7. Báo cáo dev và chuẩn bị phiên đánh giá test**

Agent tổng hợp bảng dev theo nhãn, nguồn, cũ/mới/lai có nhãn, nhiễu/thiếu, coverage và latency. Sử dụng 5 trường hiện có cho track tương thích phải giữ báo cáo/mode riêng; `baseline_v3_fuzzy` là mốc lịch sử oracle 5 trường, không phải HEUR-JW hoặc T0 test result.

Khóa threshold, rule, mapping, tokenizer/gazetteer và checkpoint của mỗi cấu hình trước lần chấm test của cấu hình đó. Một baseline chưa sẵn sàng có thể chờ; không dùng kết quả test của baseline trước để tune baseline sau. Vắng hoặc ít support mốc/hướng trên dev/test phải được nêu là giới hạn; không khôi phục nhiệm vụ lấy dữ liệu thật đang tạm hoãn chỉ để đạt đủ số nhãn.

**Đầu ra:** báo cáo thực nghiệm dev, danh sách cấu hình đã khóa và checklist chạy test. Đây là kết quả phát triển, chưa là bảng đối đầu cuối Sprint 3.

**8. Khi partner gửi 100 test**

Nhận raw JSON và biên bản người gán; đối chiếu đúng 100 ID/text frozen, kiểm gán mù không prediction. Chạy script 17 với queue batch01 và role `frozen_benchmark_test_hold` vào output mới; QA đủ 100, phán quyết flag/note, sửa trên Label Studio nếu cần, rồi duyệt gold.

Ghép train/dev đã duyệt với test đã duyệt thành `corpus_v1`, chạy audit script 18 trên ba canonical split, áp quyết định gần trùng còn phù hợp và kiểm hash/text/group giữ nguyên. Nếu input drift làm quyết định cũ không còn đúng, dừng phát hành để xử lý; không thay test ID.

Chạy test với cấu hình đã khóa, lưu prediction/metrics/manifests và làm bảng đối đầu cuối khi các mô hình cần báo đã sẵn sàng. Neural fine-tune/proposed vẫn cần thực hiện theo phạm vi Sprint 3, nhưng chúng chỉ dùng train/dev; test dùng cho đánh giá cuối.

**Phân công và cổng hoàn thành trong thời gian chờ**

| Công việc | Agent | Chủ dự án | Partner |
| --- | --- | --- | --- |
| QA 68/232 | Chạy converter, báo ID/lỗi | Sửa trên Label Studio khi cần | Không phụ thuộc |
| Duyệt 300 mẫu | Tổng hợp log/checklist/hash | Quyết định ca khó, xác nhận phạm vi duyệt | Không phụ thuộc |
| Train/dev và runner | Build, audit, báo coverage | Chốt ngoại lệ thực sự cần quyết định | Không phụ thuộc |
| HEUR-JW / DP-ZS-FT dev | Hiện thực và chạy theo phạm vi đã giao | Cung cấp tài nguyên/quyền cài mới khi cần | Không phụ thuộc |
| Chuẩn bị CRF / fine-tune | Dataset, alignment, config; CRF dev khi triển khai | Chốt tài nguyên/budget khi bắt đầu | Không phụ thuộc |
| Test gold / corpus ba split / điểm test | QA, đóng gói và chấm sau khi có export | Phán quyết, duyệt phát hành | Hoàn tất 100 và bàn giao raw JSON |

Thứ tự đề xuất: **QA → duyệt nội dung → train/dev → runner/scorer → HEUR-JW → DP-ZS-FT → CRF hoặc chuẩn bị supervised → chấm test khi partner hoàn tất**. Có thể chuẩn bị runner và kiểm môi trường trong lúc chủ dự án xử lý ca QA. Không ước lượng ngày hoàn tất huấn luyện trước khi biết tài nguyên và chi phí chạy thực đo.

Tiêu chí đã tận dụng tốt thời gian chờ: có train/dev được duyệt cùng hash/coverage, runner dev tái lập được, HEUR-JW và DP-ZS-FT có kết quả dev hoặc blocker môi trường cụ thể, cấu hình supervised chuẩn bị xong. Các cổng còn chờ partner được ghi `TEST_PENDING`; không coi corpus hoặc Sprint 3 đã hoàn thành toàn bộ.
