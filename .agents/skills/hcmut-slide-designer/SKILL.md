---
name: hcmut-slide-designer
description: >-
  Standardize, style, structure, and verify academic LaTeX Beamer presentations
  following Ho Chi Minh City University of Technology (HCMUT) design guidelines.
  Enforces Open Sans 14.3pt unbolded titles, Montserrat 9pt content, Montserrat
  6pt unbolded footers, deep navy palettes, 6-part academic progression with
  active TOC highlights, XeLaTeX 2-pass compilation, and zero-overfull-vbox visual QA.
---

# HCMUT Slide Designer

## Overview
Skill chuyên biệt cho việc thiết kế, chuẩn hóa typography, tái cấu trúc nội dung và kiểm thử chất lượng trực quan cho các bài thuyết trình học thuật (Beamer XeLaTeX) theo đúng quy chuẩn Trường Đại học Bách Khoa ĐHQG-HCM (HCMUT).

Skill đảm bảo:
1. **Typography chuẩn xác:** Title banner `Open Sans Regular 14.3pt` (không in đậm), nội dung `Montserrat 9pt` (line spacing 11.5pt), footer `Montserrat Regular 6pt` (không in đậm).
2. **Bộ nhận diện thương hiệu:** Tông màu Deep Navy Bách Khoa (`#0B3B60`, `#072844`), logo khối lập phương 3D HCMUT ở góc dưới bên phải.
3. **Cấu trúc 6 phần học thuật:** Tự động điều hướng và chèn slide Table of Contents chuyển tiếp với hiệu ứng highlight phần hiện tại (`\color{bkblue}`) và làm mờ phần khác (`\color{gray}`).
4. **Quy tắc làm sạch giữa các Sprint:** Độc lập hóa nội dung, xóa bỏ slide cũ dư thừa và các câu tham chiếu chéo không cần thiết (như *"ở Slide 8"*).
5. **Zero-Overfull QA:** Biên dịch 2 lần với `xelatex` và tự động phân tích `.log` nhằm triệt tiêu hoàn toàn lỗi tràn khung dọc (`Overfull \vbox`).

---

## Dependencies
- **TeX Engine:** `xelatex` (hỗ trợ `fontspec` và nạp font TTF).
- **Fonts:** File font tĩnh đặt tại `docs/fonts/` (hoặc cài sẵn trong hệ thống):
  - `OpenSans-Regular.ttf`, `OpenSans-Bold.ttf`, `OpenSans-Italic.ttf`
  - `Montserrat-Regular.ttf`, `Montserrat-Bold.ttf`, `Montserrat-Italic.ttf`
- **Python libraries (QA):** `pymupdf` (`fitz`) để kết xuất ảnh slide PNG kiểm tra trực quan.

---

## Quick Start

Khi người dùng yêu cầu chuẩn hóa hoặc rà soát một bài thuyết trình Beamer (ví dụ: `docs/slides_hcmut.tex`), thực hiện theo quy trình tương tác 4 bước dưới đây.

---

## Workflow (Quy trình Thực thi)

### Bước 1: Rà soát & Đưa ra Checklist (Review & Checklist)
> [!IMPORTANT]
> **Quy tắc tương tác:** Luôn rà soát file `.tex` hiện tại, lập bảng checklist các điểm lệch chuẩn và trình bày cho người dùng xác nhận trước khi thực hiện chỉnh sửa mã nguồn.

Rà soát các tiêu chí cốt lõi:
- [ ] **Title Banner:** Đã tắt `\textbf` chưa? Cỡ chữ có đúng `\fontsize{14.3pt}{17pt}` font `Open Sans` không?
- [ ] **Content Body:** Font chính có phải `Montserrat` cỡ `9pt/11.5pt` không? Bullets có chuẩn tròn đen không?
- [ ] **Footer:** Đã tắt `\textbf` chưa? Cỡ chữ có đúng `\fontsize{6pt}{7.5pt}` font `Montserrat` không? Cấu trúc 3 cột có chừa khoảng trống `3.8em` cho logo BK ở góc phải không?
- [ ] **Cấu trúc 6 phần:** Đã đồng bộ Table of Contents với tiến trình:
  1. *Introduction* $\to$ 2. *Preliminaries and Problem Statement* $\to$ 3. *Related Works* $\to$ 4. *Proposed Method* $\to$ 5. *Experiments and Results* $\to$ 6. *Conclusion*.
- [ ] **Slide chuyển tiếp TOC:** Các phân đoạn lớn có slide TOC làm nổi bật phần đang nói (`\color{bkblue}`) và làm mờ các phần còn lại (`\color{gray}`) không?
- [ ] **Tham chiếu Sprint cũ:** Có còn các câu phụ thuộc như *"ở Slide 8"*, *"như Sprint 1"* không?

### Bước 2: Áp dụng Chuẩn hóa Preamble & Slide Code
Sau khi người dùng đồng ý:
1. Cập nhật preamble dựa theo mẫu tại:
   `references/beamer_preamble_template.tex`
2. Cập nhật slide Table of Contents và các slide chuyển tiếp theo hướng dẫn tại:
   `references/toc_structure_guidelines.md`
3. Định dạng bảng biểu:
   - Dùng `\rowcolor{tableheader}` cho hàng tiêu đề.
   - Bao bọc bảng bằng `\resizebox{0.95\textwidth}{!}{...}` để tránh tràn lề ngang (`Overfull \hbox`).
4. Tinh chỉnh khoảng cách:
   - Sử dụng `\vspace{...}` vừa phải (thường từ `0.05cm` đến `0.2cm`).
   - Đặt `\setlength{\itemsep}{1.5pt}` đến `3.5pt` cho các danh sách dài để tránh đè lên footer.

### Bước 3: Biên dịch 2 Lần với XeLaTeX
Chạy lệnh biên dịch 2 lần để cập nhật chính xác tổng số frame (`\inserttotalframenumber`) và siêu liên kết:
```bash
xelatex -interaction=nonstopmode slides_hcmut.tex
xelatex -interaction=nonstopmode slides_hcmut.tex
```

### Bước 4: Kiểm thử Tự động & QA Trực quan
Sử dụng script tiện ích có sẵn trong skill:
```bash
# 1. Quét file log kiểm tra cảnh báo tràn khung
python .agents/skills/hcmut-slide-designer/scripts/verify_slides.py check-log --log docs/slides_hcmut.log

# 2. Render các slide trọng điểm sang PNG để kiểm tra lề thị giác
python .agents/skills/hcmut-slide-designer/scripts/verify_slides.py render --pdf docs/slides_hcmut.pdf --out-dir /tmp/slide_previews --pages 2 3 14 18 20
```

Nếu phát hiện `Overfull \vbox`:
- Giảm cỡ chữ phụ (`\small` hoặc `\footnotesize`).
- Giảm `\itemsep` (ví dụ từ `3pt` xuống `1.5pt`).
- Rút gọn câu văn dài hoặc chuyển bớt nội dung sang slide tiếp theo.

---

## Utility Scripts

Script hỗ trợ: `.agents/skills/hcmut-slide-designer/scripts/verify_slides.py`

### Các lệnh hỗ trợ:
1. **`check-log`**: Quét cảnh báo tràn khung dọc (`Overfull \vbox`) và ngang (`Overfull \hbox`).
   ```bash
   python .agents/skills/hcmut-slide-designer/scripts/verify_slides.py check-log --log <path_to_log>
   ```
2. **`render`**: Chuyển đổi PDF sang hình ảnh PNG chất lượng cao phục vụ review trực quan.
   ```bash
   python .agents/skills/hcmut-slide-designer/scripts/verify_slides.py render --pdf <path_to_pdf> --out-dir <output_dir> [--pages 1 2 3]
   ```
3. **`compile`**: Biên dịch 2 pass và tự động audit log trong 1 lệnh duy nhất:
   ```bash
   python .agents/skills/hcmut-slide-designer/scripts/verify_slides.py compile --tex <path_to_tex>
   ```

---

## Common Mistakes (Các Lỗi Thường Gặp Cần Tránh)

1. **Vô tình in đậm Title và Footer:**
   - *Lỗi:* Để `\textbf{\insertframetitle}` hoặc `\bfseries` trong `footline`.
   - *Khắc phục:* Giữ nguyên trọng lượng `Regular` của Open Sans và Montserrat theo đúng thiết kế tối giản, thanh lịch của template Bách Khoa.
2. **Tràn khung dọc (`Overfull \vbox`):**
   - *Lỗi:* Nhồi nhét quá nhiều `\item` hoặc bảng quá cao khiến nội dung chèn lên thanh footer.
   - *Khắc phục:* Luôn chạy `check-log`. Khi có `Overfull \vbox`, giảm `\itemsep` hoặc tách slide.
3. **Quên biên dịch lần 2:**
   - *Lỗi:* Chỉ chạy `xelatex` 1 lần khiến bộ đếm trang hiển thị sai (ví dụ: `3 / ??` hoặc `3 / 29` thay vì `3 / 22`).
   - *Khắc phục:* Luôn chạy 2 lần hoặc dùng lệnh `verify_slides.py compile`.
4. **Giữ lại các slide tham chiếu cũ:**
   - *Lỗi:* Nhắc lại câu *"như đã cam kết ở Slide 8"* khi Slide 8 đã bị xóa hoặc thuộc Sprint trước.
   - *Khắc phục:* Viết các câu khẳng định độc lập: *"Mục tiêu đặt ra:"*, *"Kết quả thực hiện trong Sprint:"*.
