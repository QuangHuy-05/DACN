# Bước 1 Sprint 4 — Quyết định phạm vi, quyền nguồn và Amendment A1

**Ngày:** 13/10/2026 (Asia/Saigon). **Nhánh đã chọn: `SCOPED_PARTIAL`.** **Phiên bản: v2** (thay v1 cùng ngày).
Dữ liệu máy đọc được: `data/interim/annotation/sprint04/decision_log_20261013_v2/` (`decision_log.json`, `source_use_decisions.csv`, `build_decision_log.py`, `evidence/`). Bản v1 được giữ nguyên để truy vết. Gói candidate `pilot_review_20261008_v2` không bị sửa; script xác minh lại toàn bộ hash đầu ra và hash bằng chứng nguồn trước khi ghi.

## 1. Phạm vi

```text
target_close: 2026-10-18        (hạn cứng theo protocol: 2026-10-20)
scope: T0/T1 data quality + model stability only
out_of_scope: T2, T3, Data05, VQA, Deepparse
annotation_owner_count: 1
inter_annotator_agreement: NOT_MEASURED
intra_annotator: NOT_MEASURED_BY_2026-10-18
holdout: HOLDOUT_NOT_COMMITTED
```

## 2. Vì sao `SCOPED_PARTIAL`, không phải `FULL_SCOPE`

1. **Vòng 1 chưa tồn tại.** Chủ dự án xác nhận chưa gán mẫu nào. Repo: `annotation_import.json` chỉ 3 byte, `timing_log.csv` không có dòng dữ liệu, không có export/log nào mới hơn 08/10. Vòng 2 phải ≥ vòng 1 + 168 giờ; vòng 1 xong 13/10 thì vòng 2 sớm nhất 20/10.
2. **Holdout chưa đạt cổng:** pilot hiệu lực có 12 site group (cần ≥ 20), 2 document group, 0 mẫu annotation-ready.
3. **Cloud/phân phối lại** chỉ được duyệt cho `hanoi_tb729`.

## 3. Quyền sử dụng theo nguồn (v2)

| Nguồn | Local research | Annotation | Cloud upload | Redistribution | Trong pilot |
|---|---|---|---|---|---|
| `hanoi_tb729` (14 mẫu) | APPROVED | APPROVED | APPROVED* | APPROVED* | Có |
| `qhkt_current` (5 mẫu) | APPROVED | APPROVED | PENDING | PENDING | Có |
| `qhkt_notice_2024` (1 mẫu, `s4_pilot_qh06`) | PENDING | **BLOCKED** | PENDING | PENDING | **Loại** |
| `ueh_campus`, `ueh_event`, `tudu_home`, `osm_copyright` | PENDING | PENDING | PENDING | PENDING | Không |

\* Có điều kiện: ghi nguồn "Cổng Thông tin điện tử thành phố Hà Nội", chỉ giữ khối địa chỉ, chỉ upload dataset Kaggle **private**.

**Pilot hiệu lực: 19 mẫu, 12 site group, 2 document group.**

**Thay đổi so với v1**
- `qhkt_notice_2024` bị loại theo quyết định của chủ dự án: đây là thông báo tuyển dụng, không thuộc chủ đề, là PDF ảnh nên không kiểm được nội dung. Nó chỉ được tải vì source register liệt kê làm ví dụ `ToaNha/CanHo` ("Phòng 5.3, 168 Pasteur"). Site 168 Pasteur vẫn còn qua `qh01`, nên số site group không đổi.
- Đã kiểm Luật 131/2025/QH15 (hiệu lực 01/04/2026): **không sửa Điều 15 khoản 2**, chỉ thêm khoản 4 (ý tưởng, khẩu hiệu, tên tác phẩm). Căn cứ "văn bản hành chính không được bảo hộ" vẫn đúng. Luật cũng thêm **Điều 7 khoản 5**: được dùng văn bản/dữ liệu đã công bố hợp pháp cho nghiên cứu khoa học, thử nghiệm, huấn luyện AI nếu không ảnh hưởng bất hợp lý quyền chủ sở hữu; với tác phẩm đang được bảo hộ còn phải theo quy định của Chính phủ (nghị định chưa kiểm). Vì vậy `hanoi_tb729` (không được bảo hộ) được duyệt cả cloud và phân phối lại, còn `qhkt_current` (trang web có thể được bảo hộ) giữ `PENDING` cho hai phạm vi đó.

## 4. Hướng dẫn tự kiểm tra các đánh giá

Làm theo thứ tự; mỗi bước nêu cách kiểm và kết quả đúng.

1. **Văn bản hành chính không được bảo hộ.** Mở PDF `data/interim/annotation/sprint04/readiness_20261007_v1/sources/ip_law_2025.pdf` (Luật SHTT hợp nhất 155/VBHN-VPQH), tìm "Điều 15". Khoản 2 phải nêu văn bản quy phạm pháp luật, văn bản hành chính, văn bản tư pháp và bản dịch chính thức không thuộc phạm vi bảo hộ.
2. **Luật sửa đổi 2026.** Mở nguồn chính thức: [WIPO Lex 23828](https://www.wipo.int/wipolex/en/legislation/details/23828) hoặc [thuvienphapluat — Luật 131/2025/QH15](https://thuvienphapluat.vn/van-ban/So-huu-tri-tue/Law-131-2025-QH15-amendments-to-the-Law-on-Intellectual-Property-700208.aspx). Kiểm ba điểm: hiệu lực 01/04/2026; Điều 15 chỉ **thêm** khoản 4; Điều 7 có khoản 5 mới về nghiên cứu/AI. Bản tôi đọc là bản sao của legalzone.vn (`evidence/luat_131_2025_qh15_legalzone_copy.docx`), nên cần đối chiếu nguồn chính thức.
3. **Đúng là văn bản hành chính?** Mở `.../sources/hanoi_tb729.pdf`: trang đầu phải là Thông báo số 729/TB-UBND của UBND thành phố Hà Nội, ngày 25/06/2025. Thông báo của cơ quan nhà nước có số hiệu là văn bản hành chính.
4. **Điều khoản trang web.** Mở dòng cuối `hanoi_notice_page.txt` ("Ghi rõ nguồn …") và `qhkt_current.txt` (dòng "© Ghi rõ nguồn …"); hoặc mở lại trang gốc ở chân trang. Cả hai chỉ yêu cầu ghi nguồn khi phát hành lại, không cấm dùng nghiên cứu.
5. **Hash chưa đổi.** Chạy lại `py -I data/interim/annotation/sprint04/decision_log_20261013_v2/build_decision_log.py`. Nếu không báo `AssertionError` thì gói candidate và bằng chứng vẫn khớp hash.
6. **Điểm rủi ro cần bạn tự cân nhắc.** (a) Tôi không phải luật sư; nếu cần chắc chắn cho khâu phát hành công khai, hỏi giảng viên hướng dẫn hoặc đơn vị pháp chế của trường. (b) Điều 7 khoản 5 phụ thuộc nghị định của Chính phủ với tác phẩm còn được bảo hộ; chưa tìm thấy nghị định, nên `qhkt_current` chưa được phép lên cloud. (c) Dùng cho đồ án học thuật phi thương mại; nếu sau này thương mại hóa phải rà lại.

## 5. Đường tới holdout (không ép số lượng)

Cổng: ≥ 50 mẫu hợp lệ, ≥ 20 site group, ≥ 2 document group, quyền nguồn đầy đủ, 0 overlap chưa xử lý.

- TB729 có 126 đơn vị nên đủ site group, nhưng mới dùng 7 site; cần trích thêm (OCR trang scan có sẵn trong `readiness_20261007_v1/extracted/`). Các biến thể cũ/mới của một địa điểm phải cùng site group.
- Holdout phải có **document group thứ hai**. **Đã tải ngày 13/10 (chủ dự án đồng ý):** Thông báo 243/TB-UBND ngày 25/06/2025 của UBND TP.HCM và Phụ lục II (địa chỉ Trung tâm Phục vụ Hành chính công của 168 phường/xã/đặc khu), lưu tại `data/interim/annotation/sprint04/source_tb243_20261013_v1/` kèm `source_manifest.json` (URL, SHA-256). Đây là văn bản hành chính có số hiệu nên cùng căn cứ Điều 15(2). Phụ lục II có khoảng 166 dòng địa chỉ (đếm theo số điện thoại, chưa kiểm đủ 168). Chỉ tải thông báo chính và Phụ lục II, không tải Phụ lục I và III.
  - Trạng thái: local research và annotation `APPROVED`; cloud/redistribution `PENDING` vì chưa kiểm điều khoản cổng. Bản Phụ lục II lấy từ website một sở khác, cần đối chiếu với bản ký số gốc. Địa chỉ chỉ thuộc hệ mới (không có `QuanHuyen`); không đưa số điện thoại hotline vào corpus.
  - Cùng với TB729 (Hà Nội), đủ **2 document group** và dư site group cho cổng holdout, nhưng chưa có mẫu nào được trích/gán, nên holdout vẫn `HOLDOUT_NOT_COMMITTED`.
- Giới hạn trung thực: các nguồn này không chứa `HuongDi`, `MocDinhVi`, `GhiChu` hay T1 `Lai`, nên holdout không đánh giá được các nhãn đó.

## 6. Amendment A1 (bổ sung, không sửa `s4-protocol-v1`)

1. Mốc đóng mục tiêu là 18/10/2026; hạn cứng giữ 20/10/2026.
2. Không có bằng chứng vòng 1 đúng hạn thì `intra_annotator = NOT_MEASURED_BY_2026-10-18`, hạng mục gán lặp `PARTIAL`. Không rút ngắn 168 giờ.
3. Nguồn có `annotation != APPROVED` bị loại khỏi pilot và corpus.
4. `cloud_upload`/`redistribution` chỉ rời `PENDING` bằng quyết định riêng có bằng chứng; nguồn chưa APPROVED không được upload Kaggle.
5. Holdout giữ `HOLDOUT_NOT_COMMITTED` đến khi đủ cổng.

## 7. Bước tiếp theo

1. Tự kiểm theo mục 4; nếu thấy sai phạm vi nào, báo để tạo decision log v3.
2. Chạy pilot 19 mẫu thủ công, không dùng gợi ý mô hình; điền `timing_log.csv` của gói candidate phiên bản mới (không sửa bản đã hash).
3. Cho phép (hoặc từ chối) tải Thông báo 243/TB-UBND để dựng document group thứ hai.
