# Rà soát toàn dự án, phản biện và việc còn lại (Sprint 1–4)

**Ngày:** 13/10/2026. Cách đọc: mục 1 là phản biện; mục 2 là việc còn lại theo ưu tiên; mục 3 là gợi ý cắt phạm vi để kịp đóng đồ án. Mọi con số lấy từ `docs/data_quality.md`, `49_sprint3_final_results.md` và đề cương; các điểm tôi suy luận được gắn nhãn "suy luận".

## 1. Phản biện: các điểm yếu của đồ án

### A. Kết quả chính ít sức thuyết phục

1. **Test chỉ 100 mẫu, 446 span, một seed.** PhoBERT-CRF 98,43% và PROPOSED-DYN 98,21% chênh nhau đúng 1 span. Không có khoảng tin cậy, không kiểm định ghép cặp, không đa seed, nên không kết luận được mô hình nào tốt hơn. Trần gần 98% cho thấy bộ test quá dễ để phân biệt mô hình.
2. **"Mô hình đề xuất" thua chính baseline của nó ở T1.** DYN T1 accuracy 71,88%, macro-F1 56,26%, `Lai` F1 = 0; baseline luật HEUR-JW đạt 92,19% / 92,49%. T1 là điểm khác biệt về thời gian của đề tài, nên đây là điểm yếu lớn nhất. Ngoài ra bật ràng buộc còn **giảm** T0 F1 0,22 điểm so với tắt.
3. **Mô hình đề xuất khác xa đề cương.** Đề cương hứa adapter đa phiên bản (H1: ablation gỡ từng adapter). Hiện chỉ có mask T0/T1 và giải mã theo confidence. H1 chưa thể kiểm chứng; đây là rủi ro bị hội đồng hỏi "đóng góp mô hình ở đâu".
4. **Nhãn hiếm không đánh giá được.** `ToaNha/CanHo`, `MocDinhVi`, `HuongDi`, `GhiChu` có support 0 trong test (`Khac` chỉ 2). Tuyên bố "schema 11 nhãn" thực chất mới được kiểm trên 6–7 nhãn.
5. **Giả thuyết còn bỏ ngỏ.** Trong 5 giả thuyết + 4 thí nghiệm phụ của đề cương: H2, H3, H4, H5, E1–E4 chưa có kết quả trong tài liệu hiện hành. (Suy luận: phần lớn có thể làm trên CPU với dữ liệu đã có.)

### B. Dữ liệu và nhãn

6. **Gold do một người gán, có AI hỗ trợ; IAA chưa đo.** Test là `AI_ASSISTED_HUMAN_REVIEW`. Rủi ro vòng lặp: gợi ý span sinh từ luật/heuristic (script 20) có thể thiên về các mẫu mà baseline luật bắt được. Chưa có bằng chứng ngược lại.
7. **Tính đại diện thấp.** Train có 71 mẫu quan sát / 69 dẫn xuất / 100 tổng hợp; test có "provenance kết hợp chưa xác minh", không phải 100 địa chỉ thật. E4 (khoảng cách tổng hợp–thật) cần 130 chuỗi hóa đơn nhưng VQA đang HOLD. Kết quả vì thế phản ánh "địa chỉ sạch, có cấu trúc", chưa phải địa chỉ nhiễu người dùng thật.
8. **Sprint 4 không giải quyết đúng chỗ yếu.** Nguồn đang thu (Thông báo 729 Hà Nội, 243 TP.HCM) là danh sách địa chỉ trụ sở theo mẫu cố định, chỉ hệ mới, không `QuanHuyen`, không `Lai`, không `HuongDi/MocDinhVi/GhiChu`. Holdout 50 mẫu từ hai tài liệu này sẽ **dễ** (cùng văn phong) và không bù được T1 `Lai` hay nhãn hiếm. Nếu không nói rõ, nó dễ bị đọc nhầm là "holdout đại diện".
9. **Data 05 hoãn, VQA hold, Gazetteer mã cũ partial** (2.187 mã cũ chưa giải quyết; hai snapshot 30/06 và 01/07/2025 không phải lịch sử hiệu lực pháp lý). Đề cương nói gazetteer đa phiên bản có khoảng hiệu lực; thực tế mới là hai ảnh chụp.

### C. Phạm vi thiếu phần cốt lõi

10. **T2 (ánh xạ cũ↔mới) chưa thực thi** dù đã có Data 07 (600 cặp) và gazetteer 10.597 cạnh. Đây là bài toán có giá trị thực tế nhất và là nền cho H5, E2, E3. Hiện nó là chỗ trống lớn nhất so với đề cương.
11. **Baseline bị cắt:** Deepparse (2 cấu hình) bị chặn vì license checkpoint; đề cương còn liệt kê Libpostal và vietnamadminunits (không thấy trong bảng Sprint 3, suy luận có thể nằm ở baseline Sprint 2 — cần xác nhận). Thiếu một baseline "thế hệ LSTM" nên claim "phủ ba thế hệ" chưa đủ.
12. **Sản phẩm bàn giao chưa đủ:** chưa có demo tối thiểu, chương kết quả/phân tích và slide cuối; slide hiện có là tổng kết Sprint 2 và Sprint 3.

### D. Quy trình và rủi ro vận hành

13. **Quản trị quá nặng so với khoa học.** 64 script, 2.352 hash bảo vệ, hơn 270 test, tài liệu tổng kết 65 KB. Tác dụng phụ đã gặp ngay hôm nay: không dọn được file trùng vì bị hash khóa. Công sức vào bằng chứng/hợp thức hóa lớn hơn công sức vào thực nghiệm.
14. **Lịch sử git trống cho cả Sprint 3 đến hôm nay** (đã commit lúc 13/10); hai file predictions 39 MB và 90 MB chưa được xử lý; trạng thái trong `AGENTS.md` vẫn dừng ở Sprint 3.
15. **Hạn Sprint 4 không khả thi theo protocol:** vòng 1 chưa có thì gán lặp (intra) không thể xong trước 18–20/10; quota Kaggle chưa đo; 18 GPU-giờ chỉ là đề xuất.
16. **Pháp lý chỉ là đánh giá dựa trên bằng chứng, không phải tư vấn.** Nguồn web (UEH, Từ Dũ) không có cho phép; OSM cần xử lý ODbL (attribution/share-alike) trước khi phát hành.

## 2. Việc còn lại, xếp theo giá trị

Ký hiệu: **[Bắt buộc]** nếu thiếu thì đồ án thiếu phần cốt lõi; **[Nên]**; **[Cắt được]**.

### Nhóm 1 — Lấp khoảng trống khoa học (làm trước)

| # | Việc | Dữ liệu/công cụ sẵn có | Đầu ra |
|---|---|---|---|
| 1 | **[Bắt buộc]** T2 baseline: tra bảng cũ→mới và mới→cũ trên Data 07 (600 cặp), báo accuracy theo chiều, theo A/B/C/M và tỷ lệ lỗi im lặng; làm E2, E3 | Gazetteer `s3_v4…release2`, Data 07 | Bảng T2 + phân tích bất đối xứng |
| 2 | **[Bắt buộc]** Sửa/đánh giá lại T1, nhất là `Lai`: báo theo tình huống A–D trên Data 06 (600 địa chỉ lai), thử đầu T1 huấn luyện bằng dữ liệu lai tổng hợp (tách khỏi test để không rò rỉ) | Data 06, HEUR-JW (92%) làm mốc | Bảng H5; `Lai` F1 > 0 hoặc giải thích âm |
| 3 | **[Bắt buộc]** Tăng độ tin cậy kết quả T0/T1: bootstrap CI, kiểm định ghép cặp, đa seed (42, 1337, 2025) | Checkpoint + Kaggle | Bảng mean ± std, CI |
| 4 | **[Nên]** Thí nghiệm rẻ trên CPU: H2 (huấn luyện kèm địa chỉ thiếu trường), H3 (xáo thứ tự trường), E1 (giữ/bỏ dấu phẩy và chữ hoa), H4 (nhóm mốc/đường) | Data 04, CRF-INDEP | 4 bảng nhỏ, kể cả kết quả âm |
| 5 | **[Nên]** Ablation đề xuất thay cho adapter: so mask T0/T1 với ràng buộc, nêu rõ H1 không kiểm được | DYN on/off | Mục trung thực trong báo cáo |

### Nhóm 2 — Dữ liệu (Sprint 4, thu hẹp lại)

| # | Việc | Ghi chú |
|---|---|---|
| 6 | **[Bắt buộc]** Chủ dự án tự kiểm các đánh giá quyền nguồn theo hướng dẫn (mục 4 của tài liệu 04) và xác nhận | Mở decision log v3 nếu có thay đổi |
| 7 | **[Nên]** Trích Phụ lục II (TB243), đếm đủ 168 dòng, loại số điện thoại; đối chiếu bản gốc | Ứng viên nhóm "out-of-domain, hệ mới" |
| 8 | **[Nên]** Pilot 19 mẫu thủ công, đo thời gian; chốt guideline ca khó | Quyết định quy mô thực dựa trên phút/mẫu |
| 9 | **[Nên]** Đổi tên đúng bản chất: bộ TB729/TB243 là **track địa chỉ cơ quan, hệ mới** (kiểm tra chuyển miền), không gọi là holdout đại diện; chỉ commit holdout khi đủ cổng | Tránh claim quá mức |
| 10 | **[Cắt được]** Gán lặp intra-annotator | Không đủ 168 giờ; ghi `NOT_MEASURED` |
| 11 | **[Cắt được]** Thu thêm nguồn cho `HuongDi/MocDinhVi/GhiChu` | Chỉ làm nếu có nguồn hợp pháp; nếu không, nêu rõ giới hạn |

### Nhóm 3 — Đóng sản phẩm

| # | Việc | Ghi chú |
|---|---|---|
| 12 | **[Bắt buộc]** Chương kết quả và phân tích lỗi; evaluation card; mục "Giới hạn và đe dọa tính hợp lệ" gom các điểm A–D ở trên | |
| 13 | **[Bắt buộc]** Slide bảo vệ cuối (slide hiện có chỉ là Sprint 2/3) | Dùng skill `hcmut-slide-designer` |
| 14 | **[Nên]** Demo tối thiểu (CLI hoặc notebook): nhập chuỗi → span + hệ quy chiếu + ánh xạ | Theo đề cương ĐACN |
| 15 | **[Nên]** Quyết định Deepparse: hoặc hỏi upstream về license weights, hoặc rút khỏi roster và ghi `OUT_OF_SCOPE_LICENSE` | Đừng để treo |
| 16 | **[Nên]** Xử lý hai file predictions lớn (ignore hoặc LFS); cập nhật `AGENTS.md`/README sang trạng thái Sprint 4 | |
| 17 | **[Cắt được]** Data 05, VQA, T3, RAG/API/Docker | Đã hoãn; chỉ liệt kê vào hướng phát triển/ĐATN |

## 3. Gợi ý cắt phạm vi để kịp đóng đồ án

- **Ưu tiên theo thứ tự:** 1 → 2 → 3 → 12 → 13 → 4 → 14. Làm xong 1–3 là đồ án có đủ T0, T1, T2 và kết quả đáng tin; phần còn lại là phân tích và đóng gói.
- **Chấp nhận kết quả âm.** DYN thua HEUR ở T1 và `Lai` F1 = 0 vẫn là kết quả trung thực; đề cương cũng nêu null result được chấp nhận (cần xác nhận với GVHD).
- **Đừng đầu tư tiếp vào nghi thức:** không mở thêm lớp hash/audit mới; gom tài liệu Sprint 3 thành một báo cáo ngắn khi viết chương.
- **Hạn 18–20/10:** chỉ khả thi với phạm vi "SCOPED_PARTIAL" (nhóm 1 + dữ liệu thu hẹp). Báo trước với GVHD nếu cần dời mốc T2/H-experiments sang tuần sau.
