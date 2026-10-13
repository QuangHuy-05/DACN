# Rà soát toàn dự án, phản biện và việc còn lại (Sprint 1–4)

**Ngày:** 13/10/2026 — **tuần 8/15** của đề cương. **Phiên bản:** v2 (thay v1 cùng ngày).
Nguồn số liệu: `docs/data_quality.md`, `49_sprint3_final_results.md`, `model_matrix.md`, đề cương và protocol Sprint 4. Điểm nào là suy luận của tôi, không phải số liệu đã đo, được gắn nhãn *(suy luận)*; điểm chưa kiểm chứng gắn *(chưa kiểm)*.

## 0. Bối cảnh lịch

- Đề cương 15 tuần; hiện mới tuần 8, còn khoảng 7 tuần. Hạn 18–20/10 trong protocol Sprint 4 chỉ là hạn riêng của Sprint 4, **không phải hạn đồ án**; cần amendment dời lịch (chưa làm).
- Thứ tự thực hiện chủ dự án chọn: **Nhóm 1 (khoa học) → Nhóm 2 (dữ liệu) → Nhóm 3 (đóng sản phẩm)**. Đề cương đặt H2, H3, H5, E1, E3 ở tuần 11–14 nên thứ tự này khớp.

## 1. Phản biện: các điểm yếu của đồ án

Mỗi điểm ghi mức nghiêm trọng đối với việc bảo vệ: **Cao** (hội đồng dễ hỏi và khó đáp), **Vừa**, **Thấp**.

### A. Kết quả chính

| # | Điểm yếu | Bằng chứng | Mức |
|---|---|---|---|
| 1 | Test chỉ 100 mẫu (446 span), một seed, không có khoảng tin cậy; không phân biệt được các mô hình hàng đầu | PhoBERT-CRF 98,43% so với DYN 98,21%, chênh đúng 1 span; trần gần 98% | Cao |
| 2 | Mô hình đề xuất thua baseline luật ở T1 | DYN T1 71,88% / macro-F1 56,26%, `Lai` F1 = 0 (support 5); HEUR-JW 92,19% / 92,49% | Cao |
| 3 | Ràng buộc của mô hình đề xuất không giúp | Bật ràng buộc làm T0 F1 giảm 0,22 điểm, không đổi lỗi Quận (0/12) hoặc T1 | Vừa |
| 4 | Mô hình đề xuất lệch đề cương: đề cương hứa adapter đa phiên bản (H1: ablation gỡ từng adapter), thực tế chỉ có mask T0/T1 và giải mã theo confidence | `model_matrix.md` (PROPOSED-DYN) | Cao |
| 5 | Nhãn hiếm không đánh giá được: `ToaNha/CanHo`, `MocDinhVi`, `HuongDi`, `GhiChu` support 0; `Khac` chỉ 2 | Bảng support test | Vừa |
| 6 | H2, H3, H4, H5, E1–E4 chưa có kết quả trong tài liệu hiện hành | Kết quả Sprint 3 chỉ báo T0/T1/5 trường | Cao |

### B. Dữ liệu và nhãn

| # | Điểm yếu | Bằng chứng / suy luận | Mức |
|---|---|---|---|
| 7 | Gold do một người gán có AI hỗ trợ, IAA chưa đo; rủi ro vòng lặp nếu gợi ý sinh từ heuristic | Test `AI_ASSISTED_HUMAN_REVIEW`; script 20 gợi ý span từ text *(suy luận về thiên lệch)* | Cao |
| 8 | Tính đại diện thấp: train 71 quan sát / 69 dẫn xuất / 100 tổng hợp; test có provenance kết hợp chưa xác minh | `data_quality.md`, protocol §3 | Cao |
| 9 | E4 (khoảng cách tổng hợp–thật) bị kẹt vì VQA đang HOLD | `data_quality.md` | Vừa |
| 10 | Dữ liệu Sprint 4 không giải quyết đúng chỗ yếu: TB729/TB243 là danh sách địa chỉ trụ sở theo mẫu cố định, chỉ hệ mới, không có `QuanHuyen`, `Lai` hay nhãn hiếm | Đã mở và đọc Phụ lục II; holdout từ hai tài liệu này sẽ dễ và không đại diện | Cao |
| 11 | Gazetteer mã cũ còn partial (2.187 mã chưa giải quyết); hai snapshot 30/06 và 01/07/2025 chưa phải lịch sử hiệu lực pháp lý | `49_sprint3_final_results.md` §5 | Vừa |
| 12 | Data 05 hoãn, VQA hold | `data_quality.md` | Thấp |

### C. Phạm vi và sản phẩm

| # | Điểm yếu | Bằng chứng | Mức |
|---|---|---|---|
| 13 | T2 chưa thực thi dù đã có Data 07 (600 cặp) và gazetteer 10.597 cạnh; đây là bài toán thực tế nhất và là nền của H5, E2, E3 | `T2: NOT_EXECUTED` | Cao |
| 14 | Baseline thế hệ LSTM bị chặn: Deepparse không có điều kiện sử dụng checkpoint rõ ràng | `DP-*: BLOCKED` | Vừa |
| 15 | Libpostal và vietnamadminunits **có** adapter (`libpostal_adapter.py`, `vnadmin_adapter.py`) và nằm trong baseline Sprint 2 trên track 5 trường; **không** có trong track T0 11 span của Sprint 3. Cần ghi rõ để so sánh hợp lệ | Thư mục `src/evaluation/adapters/` | Thấp |
| 16 | Chưa có demo tối thiểu, chương kết quả/phân tích, slide bảo vệ cuối (slide hiện có chỉ tổng kết Sprint 2 và 3) | Cây thư mục `docs/` | Cao |

### D. Quy trình và rủi ro vận hành

| # | Điểm yếu | Bằng chứng | Mức |
|---|---|---|---|
| 17 | Quản trị nặng hơn khoa học: 64 script, 2.352 hash bảo vệ, hơn 270 test; hash khóa chặn cả việc dọn file trùng | Phiên làm việc hôm nay | Vừa |
| 18 | Lịch sử git trống cho Sprint 3 đến 13/10 (đã commit hôm nay); hai file predictions 39 MB và 90 MB chưa xử lý; `AGENTS.md` còn dừng ở Sprint 3 | `git log`, kích thước file | Vừa |
| 19 | Lịch Sprint 4 không khả thi nếu giữ 18–20/10: vòng 1 chưa có nên gán lặp không đủ 168 giờ; quota Kaggle và 18 GPU-giờ chưa đo | Decision log v2 | Vừa (hết nếu dời lịch) |
| 20 | Đánh giá quyền nguồn là suy luận dựa trên bằng chứng, không phải tư vấn pháp lý; OSM cần xử lý ODbL trước khi phát hành | Decision log v2 | Vừa |

## 2. Việc còn lại, theo thứ tự thực hiện

Ký hiệu: **[BB]** bắt buộc (thiếu là thiếu phần cốt lõi), **[N]** nên làm, **[C]** có thể cắt.

### Nhóm 1 — Lấp khoảng trống khoa học (tuần 8–11)

| # | Việc | Dữ liệu / công cụ sẵn có | Đầu ra | Tuần |
|---|---|---|---|---|
| 1.1 | **[BB]** T2 baseline: tra bảng cũ→mới và mới→cũ trên Data 07 (600 cặp); accuracy theo chiều và theo loại A/B/C/M; tỷ lệ lỗi im lặng; E2 và E3 | Gazetteer `s3_v4…release2`, Data 07 | Bảng T2 + phân tích bất đối xứng | 8 |
| 1.2 | **[BB]** T1 và H5: báo T1 theo tình huống A–D trên Data 06 (600 địa chỉ lai tổng hợp); thử đầu T1 huấn luyện để `Lai` F1 > 0, tách dữ liệu huấn luyện khỏi test | Data 06, HEUR-JW làm mốc | Bảng H5; `Lai` F1 > 0 hoặc giải thích kết quả âm | 9 |
| 1.3 | **[BB]** Độ tin cậy: bootstrap CI, kiểm định ghép cặp, 3 seed (42, 1337, 2025) | Checkpoint hiện có, Kaggle | Bảng mean ± std, CI | 10 |
| 1.4 | **[N]** H2 (huấn luyện kèm địa chỉ thiếu trường), H3 (xáo thứ tự trường), E1 (giữ/bỏ dấu phẩy và chữ hoa), H4 (nhóm mốc/đường) | Data 04, CRF-INDEP (CPU) | 4 bảng nhỏ, kể cả kết quả âm | 11 |
| 1.5 | **[N]** Ghi rõ H1 (adapter) không kiểm được; thay bằng ablation mask T0/T1 với ràng buộc | DYN on/off | Mục trung thực trong báo cáo | 11 |

**Phụ thuộc cần lưu ý:** `Lai` trong test chỉ có support 5, nên 1.2 chỉ chứng minh được trên Data 06 (tổng hợp). Kết luận về `Lai` thật phải chờ dữ liệu ở Nhóm 2.

### Nhóm 2 — Dữ liệu (Sprint 4, tuần 12)

| # | Việc | Ghi chú |
|---|---|---|
| 2.1 | **[BB]** Chủ dự án tự kiểm các đánh giá quyền nguồn theo hướng dẫn §4 của tài liệu 04; xác nhận hoặc yêu cầu decision log v3 | Có thể làm song song ngay từ bây giờ, không tốn công |
| 2.2 | **[N]** Trích Phụ lục II (TB243), kiểm đếm đủ 168 dòng, loại số điện thoại, đối chiếu bản gốc | Mới đếm được ~166 dòng *(chưa kiểm)* |
| 2.3 | **[N]** Pilot 19 mẫu thủ công, đo phút/mẫu; chốt guideline ca khó | Dùng để quyết định quy mô thật |
| 2.4 | **[N]** Gọi bộ TB729/TB243 là **track địa chỉ cơ quan, hệ mới** (kiểm tra chuyển miền); chỉ commit holdout khi đủ cổng 50 mẫu / 20 site group / 2 document group | Tránh claim quá mức |
| 2.5 | **[N]** Thu mẫu `Lai` thật và nhãn hiếm từ nguồn hợp pháp nếu tìm được | Nếu không, nêu rõ giới hạn thay vì sinh bù |
| 2.6 | **[C]** Gán lặp intra-annotator | Chỉ còn khả thi nếu dời lịch; nếu không, ghi `NOT_MEASURED` |
| 2.7 | **[N]** Amendment A3 dời lịch Sprint 4 sang khung tuần 8–15 (A2 đã dùng cho phạm vi Nhóm 1, tài liệu 08) | Tài liệu riêng, không sửa protocol đã hash |

### Nhóm 3 — Đóng sản phẩm (viết dần từ tuần 9, hoàn tất tuần 13–15)

| # | Việc | Ghi chú |
|---|---|---|
| 3.1 | **[BB]** Chương kết quả và phân tích lỗi; evaluation card; mục "Giới hạn và đe dọa tính hợp lệ" gom điểm A–D | Viết ngay sau mỗi việc ở Nhóm 1 |
| 3.2 | **[BB]** Slide bảo vệ cuối | Dùng skill `hcmut-slide-designer` |
| 3.3 | **[N]** Demo tối thiểu (CLI hoặc notebook): nhập chuỗi → span + hệ quy chiếu + ánh xạ | Theo đề cương ĐACN |
| 3.4 | **[N]** Quyết định Deepparse: hỏi upstream về license weights, hoặc rút khỏi roster và ghi `OUT_OF_SCOPE_LICENSE` | Đừng để treo |
| 3.5 | **[N]** Xử lý hai file predictions lớn (ignore hoặc LFS); cập nhật `AGENTS.md` và README sang trạng thái hiện hành | |
| 3.6 | **[C]** Data 05, VQA, T3, RAG/API/Docker | Đưa vào hướng phát triển/ĐATN |

## 3. Lịch gợi ý (tuần 8–15)

| Tuần | Trọng tâm | Kết quả cuối tuần |
|---|---|---|
| 8 | 1.1 (T2) + 2.1 (tự kiểm quyền nguồn) | Bảng T2; xác nhận quyền nguồn |
| 9 | 1.2 (T1, H5) + viết mục T2 | Bảng H5; mục T2 trong chương kết quả |
| 10 | 1.3 (CI, 3 seed) + viết mục T1 | Kết quả có CI |
| 11 | 1.4, 1.5 (H2, H3, E1, H4) | **Mốc kiểm tra giữa kỳ**: T0/T1/T2 đều có bảng; nếu không, báo GVHD thu hẹp phạm vi |
| 12 | Nhóm 2 (2.2–2.5, 2.7) | Track địa chỉ cơ quan; số liệu thu mẫu thật |
| 13–14 | Nhóm 3 (3.1, 3.3, 3.4, 3.5) | Bản nháp báo cáo đầy đủ, demo |
| 15 | 3.2 (slide) + rà soát cuối | Báo cáo cuối, slide |

**Nguyên tắc điều chỉnh:**
- Chấp nhận kết quả âm (DYN thua HEUR ở T1, `Lai` F1 = 0 vẫn hợp lệ); cần xác nhận với GVHD rằng đề cương cho phép null result.
- Không mở thêm lớp hash/audit mới; khi viết chương, gom tài liệu Sprint 3 thành một báo cáo ngắn.
- Mỗi thí nghiệm mới dùng run ID mới và không tune trên test Sprint 3.
- Nếu hết tuần 10 mà T1 hoặc T2 chưa ra bảng, ưu tiên T2 và giữ T1 ở mức đã có.
