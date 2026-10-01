# Hướng dẫn gán nhãn T0: 11 span địa chỉ

**Phiên bản:** `s3-span-v1.1` (29/09/2026). **Trạng thái:** khóa sau khi người gán xác nhận đã rà soát đủ 68 mẫu pilot; mọi thay đổi tiếp theo phải tăng phiên bản và ghi vào sổ quyết định. Tài liệu này áp dụng cho chuỗi đầu vào nguyên bản, không áp dụng trực tiếp cho năm cột ground truth của benchmark.

## 1. Hợp đồng gán nhãn

- Gán đúng 11 nhãn: `SoNha`, `TenDuong`, `Ngo/Hem`, `ToaNha/CanHo`, `PhuongXa`, `QuanHuyen`, `TinhThanh`, `MocDinhVi`, `HuongDi`, `GhiChu`, `Khac`.
- Mỗi thực thể là một span ký tự half-open `[start,end)`, với `text[start:end]` đúng bằng đoạn được chọn. Không sửa lỗi OCR, thêm dấu hay mở rộng chữ viết tắt trong văn bản gán nhãn. Bản chuẩn hóa, nếu có, là trường khác.
- Gán **mọi lần xuất hiện** của thực thể. Các span phẳng và không chồng lấp. Khoảng trắng, dấu phẩy, dấu chấm phẩy, dấu ngoặc ngoài span và từ nối thuần túy để trống (`O`). Dấu thuộc chính tên/viết tắt, như dấu chấm trong `P.7` hoặc dấu gạch chéo trong `12/3`, nằm trong span.
- Tên loại đơn vị là một phần của span: `Phường 7`, `P.7`, `Quận 1`, `TP. Hồ Chí Minh`, `Đường Lý Thường Kiệt`. Không mở rộng nhãn sang dấu phân cách liền sau.
- `Khac` là **thực thể địa chỉ có nghĩa** không thuộc mười nhãn còn lại. `O` là phần nền không phải thực thể địa chỉ hoặc không thể đọc/nhận diện. `O` không phải lựa chọn nhãn trong Label Studio; chỉ để vùng đó không gán nhãn. Không dùng `Khac` như nhãn chứa mọi phần khó hiểu.
- Mỗi span có thuộc tính hệ `cu`, `moi`, hoặc `khong_xac_dinh`. Với `QuanHuyen`, đặt `cu` kể cả khi cả chuỗi là `Lai`. `PhuongXa` và `TinhThanh` chỉ nhận `cu`/`moi` khi có bằng chứng từ tên/phiên bản hành chính; tên trùng hoặc không đủ bằng chứng nhận `khong_xac_dinh`. Số nhà, đường, mốc, hướng và ghi chú mặc định `khong_xac_dinh`, trừ khi chính văn bản nêu thời điểm rõ ràng. Nhãn T1 toàn chuỗi `cu`/`moi`/`Lai` là trường riêng, không được sao chép máy móc lên mọi span.
- Các mẫu không nhận ra thực thể do OCR quá hỏng: để đoạn không đọc được là `O` và ghi cờ `unreadable_ocr` trong biên bản rà soát. Không đoán nhãn từ cột GT hoặc chuỗi gốc sạch.

## 2. Bảng ví dụ đúng/sai theo nhãn

Trong bảng, dấu `⟦...⟧` biểu thị **chính xác vùng ký tự được chọn**. Các đoạn còn lại không mặc nhiên là `O`: chúng có thể nhận nhãn khác.

| Nhãn | Gán đúng | Gán sai và lý do |
| --- | --- | --- |
| `SoNha` | `⟦Số 12/3A⟧, Đường Huỳnh Văn Bánh` | `Số ⟦12/3A,⟧`: bỏ từ chỉ số nhà và kéo dấu phẩy ngoài span vào. |
| `TenDuong` | `12, ⟦Đường Lý Thường Kiệt⟧, Phường 7` | `12, Đường ⟦Lý Thường Kiệt,⟧`: thiếu loại đường, thừa dấu phẩy. |
| `Ngo/Hem` | `12, ⟦Ngõ 42⟧ ⟦Phố Trần Bình Trọng⟧` (span thứ hai là `TenDuong`) | `⟦Ngõ 42 Phố Trần Bình Trọng⟧` thành một `Ngo/Hem`: nuốt cả tên đường. |
| `ToaNha/CanHo` | `⟦Căn A305⟧, tầng 3, ⟦Tòa A⟧` | Gán `tầng 3` thành `ToaNha/CanHo`: tầng là ghi chú tầng. |
| `PhuongXa` | `⟦P.7⟧, Quận 3`; `⟦Xã Bình Hưng⟧` | Chỉ chọn `7` hoặc kéo dấu phẩy sau `P.7` vào span. |
| `QuanHuyen` | `⟦Quận Bình Thạnh⟧`; `⟦Thị xã Quế Võ⟧` khi thể hiện cấp huyện cũ | Gán `Quận Bình Thạnh` thành `TinhThanh` hoặc tự thêm `QuanHuyen` vào địa chỉ hệ mới không có chữ đó. |
| `TinhThanh` | `⟦TP. Hồ Chí Minh⟧`; `⟦Tỉnh Bắc Ninh⟧` | Chỉ chọn `Hồ Chí Minh` khi văn bản có `TP.`; gán `Quận 1` thành tỉnh. |
| `MocDinhVi` | `⟦gần cầu Sài Gòn⟧`; `⟦đối diện chợ Bà Chiểu⟧` | Gán `đối diện chợ Bà Chiểu` thành `HuongDi`: đó là quan hệ vị trí với mốc, không phải lệnh di chuyển/hướng đi. |
| `HuongDi` | `⟦hướng Bình Thạnh⟧`; `⟦rẽ trái vào⟧ ⟦đường Nguyễn Xí⟧` (span thứ hai là `TenDuong`) | Gán `gần cầu Sài Gòn` thành `HuongDi`, hoặc nuốt cả tên đường vào span `HuongDi` khi có thể tách rõ. |
| `GhiChu` | `Căn A305, ⟦tầng 3⟧`; `⟦cổng sau⟧` khi là ghi chú tiếp cận | Gán `tầng 3` thành `SoNha`, hoặc gán mọi chữ khó hiểu thành `GhiChu`. |
| `Khac` | `⟦Khu phố 4⟧, Phường 7`; `⟦Ấp 2⟧, Xã Bình Hưng` | Gán dấu phẩy, `nay là`, mã OCR vô nghĩa hoặc từ ngoài địa chỉ thành `Khac`; các phần đó là `O`. |

## 3. Quy tắc xử lý ca khó

1. **Quan hệ với mốc và hướng:** `gần`, `đối diện`, `cạnh`, `bên cạnh` đi cùng tên mốc tạo một `MocDinhVi`. `hướng`, `đi về`, `rẽ`, `quẹo`, `đi thẳng` tạo `HuongDi` khi thật sự là chỉ dẫn. Nếu tên đường là một thành phần nhận diện được sau lệnh rẽ, tách tên đường thành `TenDuong` liền kề. Nếu một cụm vừa chỉ mốc vừa chỉ lộ trình, tách ở ranh giới ngữ nghĩa và không chồng lấp; đưa ca không tách rõ vào sổ adjudication.
2. **Địa chỉ lai:** nhãn thực thể theo hình thức đang viết. `Quận 1` luôn là `QuanHuyen`, hệ `cu`; không gán sai thành tỉnh hay xóa đi để phù hợp địa chỉ mới. `Lai` là nhãn T1 của toàn câu nếu có bằng chứng trộn cũ/mới; không phải một giá trị hệ của span.
3. **Cụm “nay là”:** `⟦Phường A⟧ (nay là ⟦Phường B⟧)` gồm hai span `PhuongXa`; `nay là`, khoảng trắng và dấu ngoặc là `O`. Gán hệ `cu` cho A, `moi` cho B khi ngữ nghĩa chuyển hệ rõ; nếu không rõ mốc thời gian, ghi `khong_xac_dinh` và cờ rà soát. Giữ cả hai lần nhắc, không thay tên cũ bằng tên mới.
4. **Nhiễu/OCR:** `P. Bên Nghé` vẫn là span nguyên văn `PhuongXa` nếu loại đơn vị và ngữ cảnh đủ rõ; không viết lại thành `Phường Bến Nghé` trong gold span. Nếu chỉ còn các ký tự không thể nhận ra, để `O`, gắn cờ `unreadable_ocr`. Không tra `ChuoiDiaChiGoc`, `GT_*` hay `Span_He_Detail` trong lúc gán.
5. **Thiếu trường:** chỉ gán thứ xuất hiện trong chuỗi. Không tạo span rỗng cho trường bị thiếu, không dùng metadata `KieuThieu` để bù. `QuanHuyen` vắng mặt trong địa chỉ mới hai cấp là cấu trúc hợp lệ.
6. **Số nhà và ngõ/hẻm:** `Số 12/3` là `SoNha` nếu diễn đạt số nhà; `Hẻm 12/3` là `Ngo/Hem` nếu diễn đạt lối vào. Phần số bên trong span giữ nguyên dấu `/`, `-`, chữ cái và khoảng trắng nội bộ.
7. **Tên riêng không có từ loại:** dựa trên cấu trúc và ngữ cảnh ngay trong chuỗi; nếu còn mơ hồ giữa đường, mốc và địa danh hành chính, ghi cờ `ambiguous_label` để duyệt, không đoán từ bảng GT.
8. **Ki-ốt và đặc khu:** `Kios 8` là `Khac` vì chỉ một vị trí kinh doanh, không phải tòa nhà hoặc căn hộ theo schema này. `Đặc khu Cát Hải` là `PhuongXa` thuộc cấp xã hệ mới theo bảng đối chiếu hành chính của dự án; giữ nguyên chữ `Đặc khu` trong span. Không suy rộng quy tắc này sang một địa danh không có bằng chứng cấp hành chính.
9. **Số nhà cạnh tên công trình:** trong `Crescent Mall - 101, Tôn Dật Tiên`, gán `Crescent Mall` là `ToaNha/CanHo` và `101` là `SoNha` vì `101` đứng ngay trước tên đường. Nếu chuỗi khác không cho phép phân biệt số nhà với mã gian hàng, gắn `ambiguous_label` và ghi quyết định riêng.
10. **Cờ rà soát:** cờ `privacy_review`, `temporal_ambiguity` hoặc `ambiguous_label` có thể giữ trên annotation sau khi duyệt để lưu dấu ca khó. Mỗi cờ còn lại phải có quyết định và lý do trong sổ pilot; bản thân cờ không đồng nghĩa annotation bị từ chối.

## 4. Quy trình nghiệm thu pilot

1. Người gán chỉ thấy `text` và mã mẫu; các cột benchmark GT, nguồn sạch và nhãn gợi ý không hiện trong màn hình gán.
2. Xuất Label Studio với `start`, `end`, `text`, `labels` và thuộc tính hệ; kiểm tra vòng về `text[start:end]`, không trùng/đè span, đúng tập 11 nhãn. Với ký tự ngoài BMP, kiểm riêng quy đổi offset giữa giao diện và Python.
3. Ghi các ca `unreadable_ocr`, `ambiguous_label`, `privacy_review`, bất đồng về ranh giới vào sổ adjudication. Sửa guideline và chạy lại pilot trước khi khóa test; sau khi khóa test không thay quy tắc dựa trên kết quả mô hình.
4. Cohen's Kappa ở mức token chỉ có ý nghĩa khi **hai người gán độc lập cùng một mẫu**; exact-span F1 giữa người gán cũng vậy. Nếu hiện chỉ có một người, hai chỉ số này để `NOT_MEASURED`, không ghi bằng 0 hay tự gán lại rồi gọi là inter-annotator agreement. Có thể đo intra-annotator agreement riêng khi gán lặp sau thời gian cách ly.

**Nguồn:** [đề cương](../../proposal/de-cuong-dacn-dia-chi-tieng-viet.pdf), [ma trận mô hình](model_matrix.md), các quyết định của chủ dự án ngày 25/09/2026.
