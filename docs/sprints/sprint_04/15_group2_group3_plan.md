# Kế hoạch Nhóm 2 (dữ liệu) và Nhóm 3 (đóng sản phẩm)

**Ngày lập:** 15/10/2026, tuần 8/15 của đề cương. **Đầu vào:** mục 2 của [05_project_review_and_remaining_tasks.md](05_project_review_and_remaining_tasks.md), kết quả Nhóm 1 trong [14_group1_summary.md](14_group1_summary.md), đề cương mục 6 (phân chia ĐACN / ĐATN).
**Prompt khởi động phiên điều phối mới:** [16_orchestrator_kickoff_group2_group3.md](16_orchestrator_kickoff_group2_group3.md).

## 0. Điểm xuất phát

- **Nhóm 1 xong sớm** (kế hoạch: tuần 8–11; thực tế: xong trong tuần 8). Toàn bộ WP0–WP6 đã review độc lập, commit và push trên nhánh `sprint4_group1`, pull request QuangHuy-05/DACN#1 (chưa merge). Bộ test: 453 test, 445 PASS / 8 SKIP / 0 FAIL.
- **Dữ liệu Sprint 4 dừng ở bước 1** (tài liệu 04): nhánh `SCOPED_PARTIAL`; pilot hiệu lực 19 mẫu (TB729 14, QH-KT 5), chưa gán mẫu nào; TB243 đã tải (thông báo + Phụ lục II, `data/interim/annotation/sprint04/source_tb243_20261013_v1/`), chưa trích; `HOLDOUT_NOT_COMMITTED`; intra-annotator `NOT_MEASURED`. Mốc 18–20/10 của protocol Sprint 4 không còn ràng buộc thực tế; cần Amendment A3 để dời lịch.
- **Ổ D chỉ còn khoảng 15 GB trống** (giảm từ 27 GB ngày 13/10, phần lớn không do dự án). Adapter neural đã khóa đòi 20 GiB trống, nên mọi suy luận neural mới đang bị chặn.

### Đề cương giao cho ĐACN những gì (mục 6) và trạng thái

| Hạng mục | ĐACN cần | Trạng thái |
|---|---|---|
| Dữ liệu | Bộ benchmark + gazetteer đa phiên bản | Có; gazetteer là hai bản chụp 30/06 và 01/07/2025, chưa phải khoảng hiệu lực pháp lý |
| T0 | Baseline đầy đủ | Có (Deepparse bị chặn license) |
| T1 | Đầu phân loại, đo trên tập lai | Có (Nhóm 1) |
| T2 | Baseline tra bảng hai chiều, đo tỷ lệ lỗi | Có (Nhóm 1) |
| **T3** | **Chỉ thiết kế và đặc tả** | **Chưa có — thiếu, đưa vào Nhóm 3** |
| Thực nghiệm | H2, H3, H5, E1, E3 | Có (Nhóm 1) |
| Hệ thống | Bản demo tối thiểu | Chưa có |
| Đầu ra | Đề cương + bộ dữ liệu + bảng baseline + phân tích lỗi | Có số liệu; chưa có chương báo cáo |

## 1. Nhóm 2 — Dữ liệu

Mục tiêu đã thu hẹp: không còn nhằm một holdout "đại diện". Nhóm 2 tạo một **track địa chỉ cơ quan, hệ mới** để kiểm chuyển miền, và thu những gì hợp pháp được cho `Lai` thật và nhãn hiếm. Phần thiếu do dữ liệu mà Nhóm 1 đã chuyển sang (A/C ở T2, E2, nhãn mốc, `Lai` thật, E4) được xử lý ở mức "kiểm tra khả năng có dữ liệu", không ép ra số.

| # | Gói | Mức | Ai làm | Nội dung | Xong khi |
|---|---|---|---|---|---|
| G2-0 | Amendment A3 — dời lịch Sprint 4 | Bắt buộc | Điều phối viết, **chủ dự án duyệt** | Lịch mới theo tuần 9–12; giữ nguyên mọi cổng (168 giờ gán lặp, cổng holdout); không sửa `s4-protocol-v1` | Tài liệu A3 có chữ "ĐÃ DUYỆT" |
| G2-1 | Tự kiểm quyền nguồn | Bắt buộc | **Chủ dự án** | Theo mục 4 của tài liệu 04; xác nhận hoặc yêu cầu decision log v3 | Câu trả lời rõ: giữ v2 hay mở v3 |
| G2-2 | Trích Phụ lục II TB243 | Nên | Agent (Sonnet high) | Trích địa chỉ từ PDF đã tải; đếm đủ 168 dòng (hiện đếm được khoảng 166); bỏ số điện thoại; đối chiếu bản ký số gốc nếu có; source manifest + hash | Danh sách ứng viên có số dòng, lý do loại từng dòng, không có số điện thoại |
| G2-3 | Pilot 19 mẫu thủ công | Nên | **Chủ dự án gán**; agent chuẩn bị và đo | Agent dựng gói gán (Label Studio đã có cấu hình) và bảng thời gian; chủ dự án gán không dùng gợi ý mô hình; agent tính phút/mẫu, tỷ lệ hợp lệ, liệt kê ca khó | Có số phút/mẫu thực đo và guideline ca khó được chốt |
| G2-4 | Track địa chỉ cơ quan, hệ mới | Nên | Agent (Sonnet high) + chủ dự án gán | Lấy mẫu từ TB729 + TB243 theo số phút/mẫu đo ở G2-3; nhóm theo site/document; gán T0/T1; QA; chạy 5 hệ hiện có (HEUR-JW, CRF-INDEP, và neural nếu đủ đĩa) | Track có tên đúng bản chất, kết quả 5 hệ có CI, không gọi là holdout đại diện |
| G2-5 | Gán lặp intra-annotator | Nên | **Chủ dự án** | Với lịch mới, vòng 2 cách vòng 1 ≥ 168 giờ là khả thi; tập 30 mẫu phân tầng | Exact-span và Kappa token theo protocol §6, hoặc `NOT_MEASURED` kèm lý do |
| G2-6 | Kiểm khả năng có dữ liệu cho phần thiếu của Nhóm 1 | Nên | Agent (Sonnet high), chỉ đọc dữ liệu có sẵn | (a) E2 và T2 loại A/C: trong `data/processed/osm/osm_real_bidirectional_pairs.csv` và OSM diff đã trích, có đơn vị cũ nào có ≥ 2 đích quan sát hay cạnh A/C nào không — nếu có, đủ để chạy lại E2 không; (b) nhãn mốc và `Lai` thật: nguồn nào trong source register có khả năng chứa, trạng thái quyền | Báo cáo khả thi: con số cụ thể, chạy được / không chạy được / cần nguồn mới |
| G2-7 | Nguồn mới cho `Lai` thật, nhãn hiếm | Cắt được | Agent tìm, **chủ dự án duyệt từng nguồn** | Chỉ nguồn công khai có căn cứ quyền dùng; không crawl khi chưa được phép (AGENTS.md) | Nguồn được duyệt hoặc ghi giới hạn |
| G2-8 | E4 và VQA | Cắt được | Chủ dự án quyết | VQA đang HOLD; E4 cần 130 chuỗi hóa đơn có nhãn. Quyết: mở HOLD và gán, hay ghi `NOT_RUN` vào giới hạn | Quyết định có ghi |

Các việc **chỉ chủ dự án làm được**: G2-0 (duyệt), G2-1, gán nhãn ở G2-3/G2-4/G2-5, duyệt nguồn ở G2-7, quyết định G2-8. Agent không thay người gán và không tự duyệt quyền nguồn.

## 2. Nhóm 3 — Đóng sản phẩm

| # | Gói | Mức | Ai làm | Nội dung | Xong khi |
|---|---|---|---|---|---|
| G3-1 | Chương kết quả và phân tích lỗi | Bắt buộc | Agent (Sonnet high) viết nháp, chủ dự án duyệt | Từ báo cáo 14 và các báo cáo 09–13: kết quả T0/T1/T2, H2–H5, E1–E3, phân tích lỗi định tính (ví dụ lỗi im lặng T2, lỗi `Lai`, lỗi khi xáo thứ tự), evaluation card, mục "Giới hạn và đe dọa tính hợp lệ" | Bản nháp đầy đủ; mọi số dẫn được về báo cáo 14 |
| G3-2 | Đặc tả T3 | Bắt buộc (đề cương mục 6) | Agent (Opus) | Định nghĩa bài toán đối sánh hai địa chỉ qua thời gian; đầu vào/đầu ra; cách dùng T0+T1+T2 làm thành phần; cách dựng dữ liệu đánh giá từ Data 07; metric; ca khó (N-1, M-N, lỗi im lặng); không hiện thực | Tài liệu đặc tả có ví dụ cụ thể và kế hoạch đánh giá cho ĐATN |
| G3-3 | Demo tối thiểu | Nên | Agent (Sonnet high) | CLI: nhập chuỗi → span T0 (HEUR-JW hoặc CRF-INDEP, chạy CPU không cần adapter neural) → T1 (T1-PIPE) → T2 (tra bảng hai chiều, trả danh sách ứng viên khi mơ hồ). Có ví dụ cho bốn tình huống A–D | Lệnh chạy được trên máy, có test, có README ngắn |
| G3-4 | Quyết định Deepparse | Nên | **Chủ dự án** quyết, agent ghi | Hỏi upstream về license weights, hoặc rút khỏi roster với `OUT_OF_SCOPE_LICENSE` | Trạng thái không còn treo |
| G3-5 | Slide bảo vệ cuối | Bắt buộc | Agent dựng, **chủ dự án trình bày** | Dùng lại khuôn LaTeX ở `docs/sprints/sprint_03/presentation_v1/`; nội dung theo chương kết quả | PDF slide và ghi chú người nói |
| G3-6 | Dọn và hợp nhất repo | Nên | Agent + **chủ dự án duyệt merge** | Quyết định merge PR #1 vào `main`; dọn tài liệu lỗi thời của Sprint 4 (01, 03); kiểm `.gitignore` | PR được merge hoặc có lý do giữ |
| G3-7 | Hướng phát triển (ĐATN) | Nên | Agent viết trong chương báo cáo | Gom phần hoãn: Data 05, VQA, T3 hiện thực, tầng 2 LLM/RAG, API/Docker, adapter cho H1, DYN-T1-AUG, gazetteer có khoảng hiệu lực | Mục có trong báo cáo |

## 3. Việc còn treo của Nhóm 1

- **Tầng 2 của WP4** (H3, E1 trên PhoBERT-CRF và mô hình đề xuất): cần ổ D có ≥ 20 GiB trống. Hiện còn khoảng 15 GB. Nếu chủ dự án giải phóng được chỗ, chạy như một gói ngắn trước G3-1 để kết luận H3 phủ cả mô hình chính.
- Pull request #1 chưa merge (G3-6).

## 4. Lịch đề xuất

| Tuần | Ngày | Nhóm 2 | Nhóm 3 |
|---|---|---|---|
| 9 | 20–26/10 | G2-0 (A3), G2-1, G2-2, G2-6; chuẩn bị gói pilot G2-3 | G3-2 (đặc tả T3), G3-4 (quyết định Deepparse) |
| 10 | 27/10–2/11 | G2-3 pilot (chủ dự án gán) và chốt guideline; vòng 1 gán lặp G2-5 | G3-1 bắt đầu (phần T2, T1) |
| 11 | 3–9/11 | G2-4 thu và gán track địa chỉ cơ quan | G3-1 tiếp (T0, H2–H4, E1); G3-3 demo |
| 12 | 10–16/11 | G2-4 QA và chạy 5 hệ; vòng 2 gán lặp (≥ 168 giờ sau vòng 1) | G3-1 thêm kết quả G2-4 |
| 13 | 17–23/11 | G2-7, G2-8 nếu còn thời gian | G3-1 bản đủ; G3-7 |
| 14 | 24–30/11 | — | G3-5 slide; G3-6 merge |
| 15 | 1–7/12 | — | Rà soát cuối, tập trình bày |

Nhóm 3 chạy song song với Nhóm 2 từ tuần 9, vì G3-1 và G3-2 dựa trên kết quả Nhóm 1 đã có. Kết quả G2-4 được thêm vào G3-1 khi xong; nếu G2-4 không đạt cổng, chương kết quả vẫn đủ với Nhóm 1.

## 5. Cách vận hành

Giữ vòng lặp đã dùng ở Nhóm 1: phiên điều phối rà prompt trên dữ liệu thật → phiên hiện thực → phiên review độc lập (Opus 5.5 mức medium) → sửa theo review → phiên điều phối commit và push khi chủ dự án đồng ý. Phiên hiện thực dùng Sonnet 5.5 mức high cho gói đã đặc tả kỹ; G3-2 (đặc tả T3) nên dùng Opus vì là việc thiết kế.

Với các gói có người gán (G2-3, G2-4, G2-5), phiên agent chỉ chuẩn bị, đo và QA; không tạo gold, không gợi ý nhãn trong vòng đo lặp, không tự phân xử.

## 6. Quyết định cần chủ dự án

1. Duyệt Amendment A3 (lịch mới) — trước mọi gói G2.
2. Tự kiểm quyền nguồn (G2-1).
3. Cam kết thời gian gán: pilot 19 mẫu, sau đó quy mô track theo phút/mẫu đo được.
4. Có giải phóng ổ D để chạy suy luận neural không (ảnh hưởng Tầng 2 WP4 và phần neural của G2-4).
5. Deepparse: hỏi upstream hay rút khỏi roster (G3-4).
6. VQA/E4: mở HOLD hay ghi `NOT_RUN` (G2-8).
7. Merge pull request #1 vào `main` khi nào (G3-6).
8. Xác nhận với GVHD rằng kết quả âm (H5, H1 không kiểm được, H4 không kết luận) được chấp nhận (đề cương, phụ lục mục 3).

## 7. Rủi ro

| Rủi ro | Xử lý |
|---|---|
| Thời gian gán của một người không đủ | Quy mô track theo phút/mẫu đo ở pilot; giảm cỡ mẫu, không sinh bù |
| Ổ D tiếp tục đầy | Chủ dự án kiểm phần dung lượng tăng ngoài dự án; agent không xóa gì để lấy chỗ |
| Nguồn không đủ quyền dùng | Giữ `PENDING`, không đưa vào corpus; ghi giới hạn |
| Track cơ quan bị đọc nhầm là holdout đại diện | Đặt tên đúng bản chất ngay từ G2-4; ghi trong chương kết quả |
| Chương kết quả nói mạnh hơn báo cáo gốc | Mỗi số dẫn về báo cáo 14; review độc lập cho G3-1 |
