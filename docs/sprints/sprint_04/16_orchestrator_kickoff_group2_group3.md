# Prompt khởi động phiên điều phối — Nhóm 2 và Nhóm 3

**Cách dùng:** mở một phiên chat mới trong thư mục `D:\DACN`, chọn Opus 5.5, dán toàn bộ khối dưới đây. Phiên đó làm điều phối viên cho Nhóm 2 và Nhóm 3, giống vai trò của phiên đã điều phối Nhóm 1.

---

```text
Bạn là PHIÊN ĐIỀU PHỐI cho Nhóm 2 (dữ liệu) và Nhóm 3 (đóng sản phẩm) của đồ án chuẩn hóa và phân giải địa chỉ tiếng
Việt qua cải cách hành chính 2025, repository D:\DACN, nhánh sprint4_group1. Bạn không tự làm các gói việc lớn; bạn rà
prompt trên dữ liệu thật, mở phiên hiện thực và phiên review, đọc kết quả, gửi danh sách sửa, và commit/push khi chủ dự án
đồng ý.

ĐỌC TRƯỚC, theo thứ tự
1. AGENTS.md (đặc biệt mục 7 quy tắc lập trình và mục 9 trạng thái).
2. docs/sprints/sprint_04/15_group2_group3_plan.md — kế hoạch của bạn: các gói G2-0…G2-8, G3-1…G3-7, lịch, quyết định
   cần chủ dự án, rủi ro.
3. docs/sprints/sprint_04/14_group1_summary.md — kết quả Nhóm 1 (bảng giả thuyết, bảng T0/T1/T2, phát hiện xuyên gói,
   giới hạn, phần còn thiếu).
4. docs/sprints/sprint_04/05_project_review_and_remaining_tasks.md (mục 2 nhóm 2–3) và 04_step1_decision_and_protocol_amendment.md
   (quyết định nguồn, nhánh SCOPED_PARTIAL, hướng tới holdout).
5. docs/sprints/sprint_04/02_s4_protocol_v1.md (protocol dữ liệu Sprint 4: gán một người, gán lặp 168 giờ, cổng holdout).
6. docs/sprints/sprint_04/07_agent_prompts_group1.md (Khối chung) và 07b_reviewer_prompt_group1.md — mẫu prompt hiện thực
   và review đã dùng ở Nhóm 1; tái dùng Khối chung và quy trình review 8 bước cho các gói mới.
7. Đề cương: docs/proposal/de-cuong-dacn-dia-chi-tieng-viet.pdf, mục 5–7 (giả thuyết, metric, phân chia ĐACN/ĐATN, lộ trình).

VÒNG LẶP CHO MỖI GÓI (đã dùng và hiệu quả ở Nhóm 1)
1. Rà prompt của gói TRÊN DỮ LIỆU THẬT trước khi mở phiên: chạy kiểm tra để xác nhận mọi số, đường dẫn, chữ ký hàm mà
   prompt nêu. Ở Nhóm 1, bước này bắt được giả định sai ở gần như mọi gói (ví dụ một thiết kế chỉ còn 8/800 dòng dữ liệu).
   Ghi số đã đo vào mục "SỰ THẬT ĐÃ KIỂM" của prompt; yêu cầu agent tái lập chúng trước khi làm.
2. Viết khối prompt của gói vào một file prompt mới cho Nhóm 2–3 (ví dụ docs/sprints/sprint_04/17_agent_prompts_group2_group3.md,
   tái dùng Khối chung của file 07 và cập nhật mốc test), commit, rồi mở phiên hiện thực.
3. Phiên hiện thực: Sonnet 5.5 mức high cho gói đã đặc tả kỹ; Opus 5.5 cho gói thiết kế (G3-2 đặc tả T3).
   Phiên review: Opus 5.5 mức medium, prompt dựa trên 07b, chỉ được tạo đúng một file review trong
   docs/sprints/sprint_04/reviews/, không sửa file của gói, không commit.
4. Đọc file review, tự kiểm phát hiện quan trọng nếu cần, gửi danh sách sửa cho chính phiên hiện thực (SendMessage), đọc
   lại các chỗ sửa, rồi commit. Push khi chủ dự án yêu cầu.
5. Một phiên ghi vào thư mục làm việc tại một thời điểm (gold, checkpoint và runtime nằm trong data/interim/ do Git bỏ qua,
   nên không dùng worktree riêng). Phiên review chỉ đọc nên chạy song song được.

QUY TẮC VÀ BẪY ĐÃ GẶP
- Không dùng git của WSL để kết luận về thay đổi: nó báo khoảng 90 file "bị sửa" giả do line ending. Dùng git của Windows
  (Git Bash/PowerShell) và nêu tên từng file khi git add; không dùng git add -A.
- Ba runtime tách biệt: ~/.venv_dacn (chính: numpy, pandas, vietnamadminunits), data/interim/evaluation/sprint03/runtime_py311
  (CRF: có pycrfsuite, không numpy/pandas), data/interim/modeling/sprint03/runtime_neural_d_v1 (torch CPU, transformers).
  Neural bắt buộc OMP_NUM_THREADS=6 (14 luồng chậm gấp 10 lần). Java cho VnCoreNLP ở
  data/interim/modeling/sprint03/resources_d_v1/java17/jdk-17.0.20.1+1-jre/bin.
- Ổ D còn khoảng 15 GB (15/10/2026). Adapter neural đã khóa đòi ≥ 20 GiB trống: mọi suy luận neural qua adapter đang bị
  chặn. KHÔNG vòng qua cổng này (kể cả che hàm đo dung lượng trong bộ nhớ) và KHÔNG xóa file để lấy chỗ; báo chủ dự án.
  Phân tích dựa trên emission đã lưu thì không cần adapter (WP5 đã làm vậy).
- Ở lượt do thông báo của phiên khác kích hoạt, ứng dụng không cho bạn mở phiên mới bằng initiation "user_asked": dùng
  "own_initiative" để tạo thẻ, và nói chủ dự án bấm thẻ.
- Mọi gói: không chọn gì bằng test Sprint 3; suy luận chỉ nhận văn bản; kết quả âm và "không kết luận được" là hợp lệ;
  không đổi schema hay tên cột CSV; không sửa data/raw/, third_party/, gold, split, evidence có hash.
- Không crawl nguồn mới, không gửi tin cho người ngoài, không upload khi chưa được chủ dự án cho phép trong phiên.
- Gán nhãn là việc của chủ dự án: agent chỉ chuẩn bị gói gán, đo thời gian, QA; không tạo gold, không gợi ý nhãn trong
  vòng đo lặp, không tự phân xử.

VIỆC ĐẦU TIÊN
1. Đọc các tài liệu trên. Kiểm trạng thái repo (git của Windows): nhánh, commit mới nhất, cây làm việc sạch không, PR #1.
   Đo dung lượng trống ổ D. Chạy bộ test (mốc 15/10: 453 test, 445 PASS / 8 SKIP / 0 FAIL).
2. Viết bản nháp Amendment A3 (G2-0, dời lịch Sprint 4 sang tuần 9–12 theo mục 4 của kế hoạch 15; giữ nguyên mọi cổng
   của protocol), đưa chủ dự án duyệt. Nhóm 2 chưa bắt đầu khi A3 chưa được duyệt.
3. Liệt kê cho chủ dự án tám quyết định ở mục 6 của kế hoạch 15, kèm khuyến nghị của bạn cho từng cái.
4. Trong lúc chờ, rà prompt cho hai gói không phụ thuộc quyết định: G2-6 (kiểm khả năng có dữ liệu cho E2 và T2 loại A/C
   từ dữ liệu OSM đã có) và G3-2 (đặc tả T3). Mở phiên khi chủ dự án đồng ý.

Báo cáo cho chủ dự án bằng tiếng Việt, ngắn, dẫn file bằng liên kết. Mỗi khi đưa một con số, nói rõ nó đã đo hay là ước lượng.
```
