# Cấu trúc Slide Học thuật 6 Phần & Quy tắc Chuyển tiếp (HCMUT Standard)

Tài liệu hướng dẫn quy chuẩn cấu trúc nội dung bài thuyết trình đồ án / nghiên cứu khoa học chuẩn Trường Đại học Bách Khoa ĐHQG-HCM.

---

## 1. Cấu trúc 6 Phần Chuẩn (Standard Academic Progression)

Toàn bộ slide thuyết trình đồ án/nghiên cứu nên tuân thủ khung 6 phần logic chặt chẽ:

```latex
\begin{enumerate}[\bfseries 1]
  \item \textbf{Introduction}
  \item \textbf{Preliminaries and Problem Statement}
  \item \textbf{Related Works}
  \item \textbf{Proposed Method}
  \item \textbf{Experiments and Results}
  \item \textbf{Conclusion}
\end{enumerate}
```

### Chi tiết mục tiêu từng phần:
1. **Introduction:**
   - Đặt vấn đề, bối cảnh không gian - thời gian, động lực nghiên cứu.
   - Với các bài báo cáo Sprint định kỳ: Slide tổng kết *"Mục tiêu vs Kết quả đạt được"* đóng vai trò tóm tắt điều hành (Executive Summary).
2. **Preliminaries and Problem Statement:**
   - Các định nghĩa toán học / kỹ thuật, các tình huống mô hình hóa cốt lõi ($A, B, C, D$).
   - Các khoảng trống nghiên cứu học thuật sâu sắc ($G1, G6, G7, G8$).
3. **Related Works:**
   - Khảo sát các hướng tiếp cận liên quan (Rule-based, Heuristic, CRF, Pretrained Language Models).
   - Chỉ rõ điểm mù cấu trúc (ví dụ: mô hình bị đóng băng trên cấu trúc 3 cấp cũ, nhạy cảm với lỗi chính tả).
4. **Proposed Method:**
   - Sơ đồ kiến trúc tổng thể (Architecture Flowchart qua TikZ).
   - Chi tiết từng mô-đun/hợp phần (Component 1, 2, 3) với công thức lọc, thuật toán hoặc quy trình dữ liệu.
5. **Experiments and Results:**
   - Đặc tả các tập dữ liệu benchmark (bảng số mẫu, mã băm SHA-256).
   - Hệ thống chỉ số đánh giá độc lập ($EM$, Token $F1$, Missing Rate, Hallucination Rate).
   - Bảng kết quả định lượng đối đầu giữa các hệ baseline.
   - Phân tích ca lỗi thực tế (Case Studies) có đối chiếu giữa dự đoán và Ground Truth.
6. **Conclusion:**
   - Nhận diện các điểm nghẽn kỹ thuật và giải pháp tháo gỡ (Blockers).
   - Kế hoạch hành động Sprint tiếp theo (Next Steps / Roadmap).
   - Slide kết thúc (-THE END-) kèm lời cảm ơn Thầy Cô hướng dẫn & Hội đồng, thông tin liên hệ.

---

## 2. Quy tắc Chèn Slide Chuyển tiếp Table of Contents (TOC Transitions)

Thay vì chèn slide chuyển tiếp màu mè, sử dụng chính slide Table of Contents làm mốc định vị không gian bài nói:
- **Nguyên tắc:** Phần chuẩn bị nói được in đậm và đổi sang màu xanh thương hiệu (`\color{bkblue}`), các phần còn lại chuyển sang màu xám nhạt (`\color{gray}`).
- **Vị trí chèn:** Trước các phần lớn (thường là trước Phần 4 - Proposed Method, Phần 5 - Experiments and Results, và Phần 6 - Conclusion).

### Đoạn mã mẫu chuyển tiếp (Ví dụ trước Phần 4):
```latex
\begin{frame}{Table of Contents}
  \vspace{0.4cm}
  \begin{enumerate}[\bfseries 1]
    \setlength{\itemsep}{0.35cm}
    \item \color{gray} Introduction
    \item \color{gray} Preliminaries and Problem Statement
    \item \color{gray} Related Works
    \item \textbf{\color{bkblue} Proposed Method}
    \item \color{gray} Experiments and Results
    \item \color{gray} Conclusion
  \end{enumerate}
\end{frame}
```

---

## 3. Quy tắc Độc lập hóa Nội dung giữa các Sprint (Sprint Transition Rules)

Khi chuyển từ Sprint $N$ sang Sprint $N+1$:
1. **Không giữ lại slide Sprint cũ làm phân đoạn:** Loại bỏ các slide lý thuyết sơ khai hoặc kế hoạch cũ của Sprint trước; tích hợp những gì đã cải tiến trực tiếp vào khung cấu trúc 6 phần của bài báo cáo mới.
2. **Triệt tiêu các tham chiếu chéo phụ thuộc thời gian:**
   - *Sai:* `"Đối chiếu với cam kết ở Slide 8"`, `"Như đã trình bày ở Sprint 1"`.
   - *Đúng:* `"Tổng kết Hạng mục Công việc & Kết quả Thực hiện trong Sprint 2"`, `"Mục tiêu đặt ra: ..."`, `"Kết quả đạt được: ..."`.
3. **Số trang tối ưu:** Một bài báo cáo Sprint định kỳ nên gói gọn trong khoảng **20 – 24 slide** để đảm bảo thời lượng trình bày 15 – 20 phút.
