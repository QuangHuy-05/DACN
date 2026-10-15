# BỘ SLIDE BÁO CÁO HỌC THUẬT SPRINT 3 & KẾ HOẠCH SPRINT 4 (HCMUT BEAMER)

Gói tài liệu trình chiếu LaTeX Beamer chuẩn học thuật cho Đồ án Chuyên ngành (DACN) — Đề tài: **Chuẩn hóa và phân giải địa chỉ tiếng Việt qua thay đổi địa giới hành chính năm 2025**.

---

## 1. DANH MỤC TÀI NGUYÊN BÀN GIAO (DELIVERABLES)

Thư mục: `docs/sprints/sprint_03/presentation_v1/`

| Tệp tin / Thư mục | Định dạng | Mô tả nội dung |
|:---|:---:|:---|
| **`sprint3_review_sprint4_plan.pdf`** | PDF (24 trang) | **Tập tin trình chiếu chính thức** (tỷ lệ 16:9, đúng 24 trang, zero-overfull-vbox). |
| **`sprint3_review_sprint4_plan.tex`** | LaTeX Source | Mã nguồn Beamer đầy đủ 24 frames, thiết lập fontspec và bảng màu HCMUT. |
| **`speaker_notes.md`** | Markdown | Kịch bản thuyết trình chi tiết từng slide (80–140 từ/slide nội dung). |
| **`slide_source_map.md`** | Markdown | Bản đồ ánh xạ chi tiết từng số liệu, bảng biểu trên slide về các báo cáo gốc trong repo. |
| **`slides_qa_report.md`** | Markdown | Báo cáo kiểm định chất lượng kỹ thuật (log audit, pixel inspection, numerical check). |
| **`assets/`** | Thư mục | Chứa logo trường (`bk_logo.png`), background bìa (`bg_title.jpg`) và background nội dung (`bg_template.jpg`). |
| **`fonts/`** | Thư mục | Chứa bộ font TrueType cục bộ: `OpenSans-*.ttf` và `Montserrat-*.ttf`. |
| **`previews/`** | Thư mục | 24 ảnh xem trước chất lượng cao (`slide_01.png` đến `slide_24.png`) ở độ phân giải 150 DPI. |

---

## 2. CẤU TRÚC BỘ TRÌNH CHIẾU (24 TRANG HỌC THUẬT)

Bộ slide được tái cấu trúc hoàn chỉnh theo yêu cầu:
- **Slide 01:** Slide Tiêu đề bài toán (Cover Title Slide) chuẩn nhận diện HCMUT.
- **Slide 02:** Slide Phân công nhiệm vụ Sprint 3 của hai thành viên (Nguyễn Quang Tùng & Nguyễn Quang Huy).
- **Slide 03–14:** Nội dung thuyết trình học thuật cốt lõi Sprint 3 (không có slide mục lục tĩnh, chắt lọc cô đọng).
- **Slide 15–23:** Toàn bộ các chuyên đề hồ sơ tham chiếu kỹ thuật chi tiết đã được chuyển lên trước phần Sprint 4, xóa hoàn toàn chữ "Phụ lục" trong tiêu đề.
- **Slide 24:** Kế hoạch và Phân công nhiệm vụ hai thành viên trong Sprint 4 (trang kết thúc toàn bộ bài báo cáo).

```text
Slide 01: [BẮT BUỘC] Slide Tiêu đề Đề tài (HCMUT Cover Title Slide)
Slide 02: [BẮT BUỘC] Sprint 3 — Phân công nhiệm vụ hai thành viên (Bảng 2 cột)
Slide 03: Tổng quan kết quả Sprint 3: Ba trụ cột cốt lõi (Corpus 400 mẫu/11.962 mã NSO, T0 cao nhất 98.43%, Giới hạn IAA/T2/Lai/DP)
Slide 04: Bài toán nghiên cứu, Schema và Corpus phát hành (T0/T1, 400 mẫu, 240/60/100, Train/Dev 87/81/132, Test unverified, VQA HOLD, group-disjoint)
Slide 05: Chuẩn hóa dữ liệu: Gán nhãn, Rò rỉ và Ngoại lệ T1 (Quy trình Gold, SequenceMatcher 138 cặp distinct, 64 mẫu T1 eligible)
Slide 06: Gazetteer thời gian: Dual-snapshot và xác minh NSO (11.962 mã đơn vị hành chính, tra cứu 2 mốc, terms gap, T2 NOT_EXECUTED)
Slide 07: Ma trận mô hình: Thực nghiệm và Giới hạn bản quyền (4 mô hình hoàn thành; Deepparse NOT_EXECUTED do bản quyền trọng số)
Slide 08: Phương pháp: Chuẩn hóa Tone Relocation & Kiến trúc Đa nhiệm (Tone Relocation v2, PhoBERT encoder dùng chung)
Slide 09: Kỷ luật thực nghiệm: Lựa chọn bằng Dev & Đóng băng Dự đoán (Kaggle 2x T4, chọn c02 trên Dev, freeze trước gold)
Slide 10: Kết quả T0 toàn schema và Cảnh báo Support nhãn (Micro-F1 4 mô hình, PhoBERT-CRF 98.43% cao nhất, cảnh báo 4 zero-support)
Slide 11: Đánh giá phân loại hệ T1: Thách thức nhận diện lớp Lai (HEUR 92.49%, DYN 56.26%, Lai F1=0.00%, 12 mẫu abstain)
Slide 12: Paired Ablation: Đánh giá vai trò của Dynamic Constraint (-0.22% F1, chỉ đổi 1 mẫu, kết luận phủ định khoa học)
Slide 13: Phân tích lỗi thực tế: Hai hiện tượng tiêu biểu (Lệch ranh giới từ vựng & Thiếu dữ liệu nhãn hiếm)
Slide 14: Kết luận tổng kết kỹ thuật Sprint 3 (3 kết quả kỹ thuật hoàn thành, bảo toàn toàn vẹn 2.352 hashes SHA-256 trên 1 seed)
Slide 15: Danh mục tài liệu tham chiếu kỹ thuật (Danh mục 8 hồ sơ kỹ thuật chuyên sâu 1--8)
Slide 16: Chi tiết Schema 11 nhãn địa chỉ tiếng Việt (Bảng 11 nhãn định nghĩa & quy tắc)
Slide 17: Bảng F1 và Support chi tiết từng nhãn T0 (Bảng phân rã support và F1 từng nhãn, cảnh báo zero-support)
Slide 18: Ma trận nhầm lẫn chi tiết T1 (PROPOSED-DYN) (Ma trận nhầm lẫn và bảng chỉ số từng lớp)
Slide 19: Chi tiết tham số cấu hình Baseline (HEUR & CRF) (Quét lưới 6 ngưỡng HEUR & 8 cấu hình CRF)
Slide 20: Bằng chứng tái lập & Kiểm toán mã băm SHA-256 (2.352 hashes bất biến, 274 tests)
Slide 21: Đánh giá Track 5 trường truyền thống (4.800 mẫu) (Track phát triển/tương thích ngược; overlap 1 seen train + 4.799 unseen site key)
Slide 22: Bảng tổng hợp các trường hợp lỗi phân tích (5 ca lỗi phân loại rõ theo Split và Model, kèm mẫu chẩn đoán từ Train*)
Slide 23: Khó khăn kỹ thuật hạ tầng và giải pháp xử lý (NumPy ABI, Tone Relocation, Kaggle, Bản quyền)
Slide 24: [BẮT BUỘC] Sprint 4 — Định hướng trọng tâm và Phân công nhiệm vụ (SLIDE KẾT THÚC)
```

---

## 3. HƯỚNG DẪN TÁI LẬP VÀ BIÊN DỊCH (REPRODUCTION GUIDE)

Môi trường yêu cầu: Máy tính cài đặt MiKTeX hoặc TeX Live hỗ trợ trình biên dịch **XeLaTeX** (đã cấu hình sẵn trong repository).

### Bước 1: Biên dịch Beamer (2 passes)
Từ thư mục `docs/sprints/sprint_03/presentation_v1`:
```powershell
cd D:\DACN\docs\sprints\sprint_03\presentation_v1
& "C:\Users\quang\AppData\Local\Programs\MiKTeX\miktex\bin\x64\xelatex.exe" -interaction=nonstopmode sprint3_review_sprint4_plan.tex
& "C:\Users\quang\AppData\Local\Programs\MiKTeX\miktex\bin\x64\xelatex.exe" -interaction=nonstopmode sprint3_review_sprint4_plan.tex
```

### Bước 2: Kiểm tra cảnh báo Overfull Log
Chạy công cụ kiểm tra log của skill `hcmut-slide-designer`:
```powershell
cd D:\DACN
& "C:\Users\quang\AppData\Local\Programs\Python\Python311\python.exe" d:\DACN\.agents\skills\hcmut-slide-designer\scripts\verify_slides.py check-log --log docs/sprints/sprint_03/presentation_v1/sprint3_review_sprint4_plan.log
```
*Kết quả kiểm định: 0 lỗi, 0 Overfull \vbox, 0 Overfull \hbox.*

### Bước 3: Xuất ảnh xem trước phục vụ QA thị giác
```powershell
& "C:\Users\quang\AppData\Local\Programs\Python\Python311\python.exe" d:\DACN\.agents\skills\hcmut-slide-designer\scripts\verify_slides.py render --pdf docs/sprints/sprint_03/presentation_v1/sprint3_review_sprint4_plan.pdf --out-dir docs/sprints/sprint_03/presentation_v1/previews
```

---

## 4. LƯU Ý DÀNH CHO NHÓM TÁC GIẢ (HUMAN ACTION ITEMS)

1. **Thông tin tác giả:**
   - Đã cập nhật chính thức tên hai thành viên: **Nguyễn Quang Tùng (MSSV: 2313817)** và **Nguyễn Quang Huy (MSSV: 2311202)** trên bìa, footline và các slide phân công nhiệm vụ.
2. **Thời lượng trình bày khuyến nghị:**
   - Tổng thời lượng: **15 đến 20 phút** (bình quân 35–45 giây/slide).
   - Slide 02 mở đầu bài thuyết trình, Slide 24 khép lại toàn bộ bài thuyết trình bằng cam kết phân công nhiệm vụ Sprint 4.
