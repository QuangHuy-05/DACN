# Kế hoạch đóng Sprint 4 trước 19/10/2026

**Ngày lập:** 12/10/2026  
**Mốc đóng mục tiêu:** hết ngày 18/10/2026, múi giờ Asia/Saigon  
**Căn cứ:** `02_s4_protocol_v1.md`, trạng thái pilot package/review đang có trong `data/interim/annotation/sprint04/`.

## 1. Tình trạng và điều kiện khả thi

Sprint 4 hiện có protocol, candidate package 20 mẫu và công cụ review. Manifest package ghi 0 mẫu annotation-ready, pilot chưa chạy, thời gian chưa đo, chưa có gold và holdout `HOLDOUT_NOT_COMMITTED`. Bản review ngày 08/10 cũng ghi chưa có annotation export hoặc vòng gán lặp. Candidate package hiện có 12 site group; nó chưa đủ ngưỡng holdout đề xuất 20 site group và 50 mẫu. Các nguồn dùng trong package vẫn pending phạm vi/quyền dùng.

Protocol yêu cầu hai lần gán thủ công cách nhau ít nhất 168 giờ. Vì vậy, để có intra-annotator trước hết ngày 18/10, từng mẫu phải có log hoàn tất vòng 1 muộn nhất vào cùng thời điểm ngày 11/10. Cần kiểm tra xem có bằng chứng vòng 1 được tạo sau ngày 08/10 nhưng chưa nhập vào workspace hay không. Nếu không có, không thể nghiệm thu intra-annotator trước ngày 19/10 mà vẫn giữ đúng protocol.

**Quy tắc quyết định:**

- Nếu có vòng 1 đúng hạn, quyền nguồn được duyệt và các cổng dữ liệu/tài nguyên đạt: chạy kế hoạch đầy đủ trong lịch dưới đây, theo mức khả thi đo được.
- Nếu thiếu một trong các bằng chứng trên: chốt Sprint 4 ở trạng thái `PARTIAL` trước 19/10; ghi rõ hạng mục chưa đạt, giữ `NOT_MEASURED`/`NOT_COMMITTED`, và đưa phần còn lại sang lịch tiếp theo. Không rút washout, dùng dữ liệu chưa duyệt, hoặc đổi tên dev thành holdout.

Mục tiêu 200 mẫu và ngân sách 18 GPU-giờ vẫn là tham số tham khảo. Chốt lại số mẫu sau pilot và quota thực tế.

## 2. Kế hoạch theo ngày và cổng nghiệm thu

| Ngày | Nhiệm vụ | Đầu ra/cổng chuyển bước |
|---|---|---|
| **12/10** | **Bước 1 — chốt phạm vi, quyền nguồn và tính khả thi thời gian.** Kiểm tra vòng 1 đã thực sự diễn ra chưa; xác nhận quyền nghiên cứu, gán nhãn, upload cloud và phân phối riêng theo nguồn. Cập nhật decision log/protocol amendment theo hạn 18/10. | Quyết định `FULL_SCOPE` hoặc `SCOPED_PARTIAL`; bảng nguồn `APPROVED`/`BLOCKED`/`PENDING`; danh sách hash/thời điểm vòng 1; holdout `COMMITTED` hoặc `NOT_COMMITTED`. Không có quyền annotation thì dừng pilot trên nguồn đó. |
| **12–13/10** | Nếu nguồn được duyệt: chạy pilot thủ công 20 mẫu, so bản chép với tài liệu gốc, ghi thời gian rà nguồn/gán/QA và tỷ lệ hợp lệ; khóa quy tắc guideline cho ca khó. | Pilot review có số đo thực, quyết định loại/giữ từng mẫu, guideline version mới nếu cần. Không dùng gợi ý mô hình trong vòng đo lặp. |
| **13–15/10** | Chỉ với nguồn qua gate: lấy mẫu bổ sung theo thời gian thực đo; thiết lập document/site group, dedup exact/near, gán T0/T1 và QA toàn bộ. Ưu tiên năm nhãn hiếm và `Lai`, không ép quota bằng dữ liệu tổng hợp. | Corpus candidate có provenance, annotation mode, raw export/hash, coverage theo nhãn/provenance và không còn group/trùng chưa xử lý giữa split. Chốt quy mô theo thời gian, không mặc định 200. |
| **16/10** | Đóng split train/dev và đánh giá cổng holdout. Freeze corpus candidate, label QA, exception/decision log và manifest. | Release chỉ được tạo nếu chủ dự án duyệt. Holdout chỉ commit nếu đạt tối thiểu 50 mẫu hợp lệ, 20 site group có căn cứ, 2 document group, quyền dùng đầy đủ và 0 overlap chưa xử lý; nếu không, ghi lý do không commit. |
| **16–18/10** | Chuẩn bị/rà runner song song với dữ liệu. Sau release và clearance tài nguyên mới chạy smoke, rồi chạy roster/seed đã khóa, T1 và paired ablation. Khóa prediction trước scorer; chấm holdout chỉ sau model lock và chỉ khi holdout đã commit. | Run manifest/checkpoint/prediction/config/resource hash, thời gian chạy và metric theo seed. Nếu không kịp đủ seed, báo `PARTIAL_SEEDS`; thiếu nguồn/quota thì không upload hoặc train trên nguồn đó. |
| **17–18/10** | Chỉ nếu log vòng 1 chứng minh từng mẫu đã đủ 168 giờ: gán vòng 2 mù với thứ tự/ID mới, lưu raw export/hash, tính intra trước phân xử, rồi QA và adjudicate. | Intra exact-span và token Kappa theo protocol, hoặc `NOT_MEASURED`/`PARTIAL` kèm lý do. IAA người-người luôn `NOT_MEASURED` trong phạm vi một người. |
| **18/10** | Đóng báo cáo và bàn giao Sprint 4. | Bảng PASS/PARTIAL/BLOCKED, evaluation card, hướng dẫn tái lập, giới hạn support/provenance, trạng thái holdout/intra/seeds. Sprint 3 giữ nguyên. |

**Lưu ý thứ tự:** gán lặp có thể bắt đầu từ các mẫu vòng 1 đã đủ 168 giờ trong khi các công việc khác tiếp tục. Không phát hành gold, upload hoặc train trước các cổng tương ứng.

## 3. Checklist hoàn tất

- [ ] Source-use assessment có quyết định riêng cho local research, annotation, cloud upload và redistribution.
- [ ] Pilot đo thời gian và tỷ lệ mẫu hợp lệ; transcript/source locator đã được người gán kiểm tra.
- [ ] Corpus có split mới, group/duplicate audit, coverage theo nhãn và provenance.
- [ ] Holdout có quyết định rõ; không dùng test Sprint 3 làm holdout hoặc để tune.
- [ ] Intra-annotator có hai vòng đủ 168 giờ và metric trước phân xử; nếu không, ghi rõ chưa đo.
- [ ] Các run được phép có hash, seed, checkpoint, prediction, resource và metric đầy đủ.
- [ ] Báo cáo ghi PASS/PARTIAL/BLOCKED theo từng hạng mục; không gọi gán lặp là IAA.

## 4. Hướng dẫn thực hiện Bước 1

Tạo decision log mới dưới `data/interim/annotation/sprint04/` với ngày 12/10; không sửa candidate package đã hash. Hoàn thành ba phần sau:

### A. Ghi quyết định phạm vi

```text
target_close: 2026-10-18
scope: T0/T1 data quality + model stability only
out_of_scope: T2, T3, Data05, VQA, Deepparse
annotation_owner_count: 1
inter_annotator_agreement: NOT_MEASURED
```

### B. Ghi trạng thái cho nguồn thật sự có trong pilot package

Ưu tiên các source key đang được dùng: `hanoi_tb729`, `qhkt_current`, `qhkt_notice_2024`. Với từng nguồn, điền `APPROVED`, `BLOCKED` hoặc `PENDING` cho bốn phạm vi: local research, annotation, cloud upload, redistribution; đính kèm đường dẫn/hash bằng chứng điều khoản và ngày rà soát. Không suy rằng trang công khai hoặc Kaggle private tự động cho phép các phạm vi này. Nguồn nào annotation còn `PENDING` thì chưa được đưa vào pilot.

### C. Kiểm tra bằng chứng vòng 1 và chọn nhánh lịch

Tìm raw export/log có `sample_id`, thời điểm hoàn tất vòng 1 theo Asia/Saigon và SHA-256. Tính mốc vòng 2 riêng cho từng mẫu là `round1_completed_at + 168 hours`.

- Nếu không có mẫu nào hoàn tất vòng 1 muộn nhất ngày 11/10: đặt `intra_annotator: NOT_MEASURED_BY_2026-10-18`; không tuyên bố đầy đủ protocol trước hạn.
- Nếu có: chỉ đưa mẫu đủ 168 giờ vào vòng 2; giữ raw export của cả hai vòng trước adjudication.
- Giữ `holdout: HOLDOUT_NOT_COMMITTED` cho đến khi số lượng, site/document group, quyền nguồn và overlap thực tế đều qua gate.

**Bước 1 chỉ xong** khi decision log có bằng chứng đính kèm và chọn rõ một nhánh: `FULL_SCOPE` (chỉ khi tất cả cổng khả thi) hoặc `SCOPED_PARTIAL`. Dùng kết quả đó để bắt đầu pilot hoặc dừng nguồn đang pending.

## 5. Ngoài phạm vi Sprint 4

Không mở rộng sprint này sang T2/T3, phát hành Data 05, xử lý VQA, hoàn thiện toàn bộ Gazetteer hoặc chạy Deepparse khi chưa có căn cứ checkpoint. Các việc này tiếp tục là backlog riêng.
