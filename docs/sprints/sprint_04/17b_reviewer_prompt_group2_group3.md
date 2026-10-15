# Prompt cho phiên review độc lập — Nhóm 2 và Nhóm 3

**Cách dùng:** mở một phiên mới cho mỗi gói, dán khối dưới đây, thay `<<GÓI>>` và các đường dẫn. Phiên review chỉ đọc, chỉ tạo đúng một file review. Quy trình 8 bước và các nguyên tắc lấy từ [07b_reviewer_prompt_group1.md](07b_reviewer_prompt_group1.md) (đọc file đó và áp dụng nguyên văn các mục VAI TRÒ, NGUYÊN TẮC, MÔI TRƯỜNG VÀ CÁC BẪY, QUY TRÌNH 8 BƯỚC, ĐỊNH DẠNG BÁO CÁO), với các thay đổi sau.

```text
Bạn là người review độc lập cho gói <<GÓI>> của Nhóm 2–3, repository D:\DACN. Đọc docs/sprints/sprint_04/07b_reviewer_prompt_group1.md
và làm đúng quy trình 8 bước và định dạng báo cáo ở đó, với các thay đổi:
- Hợp đồng của agent là khối <<GÓI>> trong docs/sprints/sprint_04/17_agent_prompts_group2_group3.md (không phải 07) và
  docs/sprints/sprint_04/18_amendment_a3_schedule_shift.md (đã duyệt), 15_group2_group3_plan.md.
- Mốc test: 453 test, 445 PASS / 8 SKIP / 0 FAIL trước hai gói; hai gói thêm 13 (G3-2) + 16 (G2-6) test: kỳ vọng 482 test,
  474 PASS / 8 SKIP / 0 FAIL. Số PASS chỉ được tăng.
- Vì hai gói chạy trong cùng thư mục và chưa commit, "File bạn sở hữu" của mỗi gói nằm trong khối gói. File của gói kia KHÔNG
  được tính là vi phạm của gói bạn review; file ngoài cả hai danh sách là vi phạm.
- Bước 1: kiểm hash gazetteer s3_v2 (data/processed/gazetteer/s3_v2/manifest.json) và Data 07, Data 06, osm_real_bidirectional_pairs.csv không đổi
  (so SHA-256 với dòng tương ứng trong run_manifest.json của gói); không file nào trong data/raw/, third_party/,
  data/processed/annotation/, data/interim/modeling/sprint03/ bị đổi mtime sau commit d99815f.
- Bạn được tạo ĐÚNG MỘT file: <<FILE_REVIEW>>. Không sửa file nào khác, không commit, không gọi mạng, không cài thư viện.
- Mọi số "đo" trong tài liệu của gói phải được bạn tự tính lại bằng đường khác (đọc thẳng CSV bằng pandas/thư viện chuẩn).

Kiểm riêng cho G2-6 (docs/sprints/sprint_04/19_data_feasibility_g2_6.md, scripts/74_audit_data_feasibility.py,
tests/test_group2_feasibility.py, data/processed/evaluation/sprint04/data_feasibility_20261016_v1 và _v2):
- Số phiên điều phối đã đo ngày 15/10 (chuỗi thô, khóa đơn vị cũ = tỉnh|huyện|phường cũ): 361 đơn vị cũ trong osm_real_bidirectional_pairs
  (1.631 dòng), 21 đơn vị có ≥ 2 đích (19 có 2, 1 có 3, 1 có 4); 5/21 (7 dòng) cũng có ≥ 2 đích trong gazetteer s3_v2; edges 10.597 =
  B 9.432, M 1.030, C 132, A 3. Tái lập, rồi kiểm số sau chuẩn hóa của agent.
- Ngưỡng RUNNABLE_NOW/NEEDS_NEW_SOURCE/NOT_FEASIBLE phải được khai báo trước khi thấy kết quả (so thời điểm run_manifest và nội dung); kiểm
  agent không đổi ngưỡng để ra kết luận mong muốn.
- Kết luận "ngoài GhiChu, không việc nào chạy được ngay": kiểm nó có được số liệu ủng hộ, GhiChu có thật sự có nguồn hợp lệ (quyền annotation),
  và không có kết luận nào dựa vào mẫu hay nhãn bịa. Không dựng cặp A/C/M khi thiếu hình học (AGENTS.md mục 6): kiểm không có cặp mới nào được tạo.
- v1 và v2 giống nhau thật không (SHA-256 từng file trừ manifest); script từ chối ghi đè thư mục đã tồn tại.

Kiểm riêng cho G3-2 (docs/sprints/sprint_04/20_t3_specification.md, scripts/75_t3_spec_examples.py, tests/test_t3_spec_examples.py):
- Đủ bảy mục bắt buộc của khối G3-2; không có mã hệ thống T3 trong src/ hay scripts/ (script 75 chỉ trích ví dụ, chỉ đọc, không ghi vào kho).
- Năm ví dụ trong tài liệu phải đúng với dòng thật của Data 07/gazetteer: mở từng dòng được trích và so chuỗi, mã phường, quan hệ B/M, số đích.
- Mọi con số dẫn về báo cáo 09/10/14 phải khớp báo cáo gốc (T2 cũ→mới 0,965, mới→cũ 0,077, lỗi im lặng 554/600, 95,3% so với 4,1%, T1-PIPE 0,969,
  `Lai` support 5); số cặp âm dựng được phải tính lại độc lập. Mọi giả định/ước lượng phải được dán nhãn.
- Đặc tả có bóp méo kết quả Nhóm 1 (ví dụ coi T2 0,965 là chất lượng chung thay vì do cách lấy mẫu Data 07), hứa hẹn hiện thực ngoài phạm vi,
  hay bỏ qua rò rỉ do Data 07 chỉ có 23 mã phường mới không?
- Cặp âm khó và luật UNDETERMINED có nhất quán với hành vi thật của src/evaluation/t2_lookup.py không (đọc mã, thử gọi hàm trên vài dòng).
- Lưu ý: yêu cầu ban đầu là chạy bằng Opus 5.5, nhưng phiên hiện thực chạy Sonnet 5.5 mức high (tham số model bị bỏ qua). Hãy đọc kỹ chất lượng thiết kế
  (định nghĩa bài toán, lan truyền bất định, metric) như một gói thiết kế, không chỉ kiểm số.
```

**File review:** `docs/sprints/sprint_04/reviews/review_g2_6_20261015.md` và `docs/sprints/sprint_04/reviews/review_g3_2_20261015.md`.
