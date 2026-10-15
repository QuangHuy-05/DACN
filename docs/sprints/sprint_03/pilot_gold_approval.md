# Biên bản rà soát và phát hành gold pilot T0

**Trạng thái:** `APPROVED_GOLD` — đã phát hành pilot gold v1 ngày 29/09/2026 lúc 16:27:18 (+07:00).

**Ngày rà soát:** 29/09/2026
**Người gán và duyệt nội dung:** `quanghuy050816@gmail.com` (tài khoản Label Studio)
**Phạm vi xác nhận của người duyệt:** đã xem đủ 68/68 task pilot. Đây là xác nhận của người dùng; bộ QA tự động chỉ kiểm cấu trúc annotation.

## Quyết định nội dung

- Bốn task 1–4 đã được sửa trên Label Studio theo guideline về thuộc tính hệ từng span và nhãn T1; task 1 và 4 nằm trong bảy ca có cờ.
- Bảy ca 1, 4, 35, 37, 42, 46, 48 có quyết định và lý do riêng trong [`pilot_decision_log.csv`](pilot_decision_log.csv). Các cờ thực sự phản ánh ca khó được giữ để lưu vết.
- Guideline `s3-span-v1.1` đã khóa trước khi mở test. Cấu hình Label Studio giữ nguyên.
- Cohen's Kappa mức token và exact-span F1 giữa hai người gán: `NOT_MEASURED` vì chỉ có một người gán độc lập.
- Thời gian gán thực đo chưa có nhật ký phiên đáng tin; không dùng lead time của lượt submit nhanh để suy ra năng suất gán.

## Bằng chứng và cổng phát hành

| Thành phần | Hash SHA-256 / tình trạng |
| --- | --- |
| Cấu hình `configs/label_studio_span11.xml` | `5b765ef778afdc8abac288d8bae3a51e9b1f491e944d0b09814e888842d57562` |
| Guideline `span_11_annotation_guideline.md` | `88dc2155d032f8052317e42c6f02f36c6cc9aee03579e9f3af76ebc12784673a` |
| Raw JSON export sau sửa | `b23ef52e19a5b60623f4abee048a7c237afa9b63b19d5f818b2cc384df74f171` |
| QA report sau sửa | `8a78d86d20c11cfe2993ef048f8a323f01993007b67a219969dafdbef2d53f80` |
| Sổ quyết định bảy ca | `2bf36127763bf7deeec40766bdd7773950a4ebb611280026478d6d72572dd703` |
| Gold `data/processed/annotation/sprint03/pilot_gold_v1.jsonl` | `48571230990ceec56a4f3e244775ad856e05931aeca7748f6407e8f06c96754d` |

Export mới đã qua bộ chuyển với `READY_FOR_HUMAN_REVIEW`: đúng 68 task, 68 annotation hợp lệ, 0 task thiếu và 0 lỗi cấu trúc. Đối chiếu canonical với export cũ cho thấy **chỉ bốn task 1–4 thay đổi**; tất cả thuộc tính hệ/T1 của bốn task khớp quyết định và guideline. Danh sách bảy ca có cờ khớp đúng bảy dòng trong sổ quyết định. Người duyệt đã xác nhận rà soát cả 68 task, nên bước duyệt nội dung chuyển trạng thái phát hành thành `APPROVED_GOLD`. `READY_FOR_HUMAN_REVIEW` trong QA report là trạng thái của bộ kiểm cấu trúc trước duyệt người, không phải trạng thái cuối của gold.

Gold được sao chép nguyên byte từ [`pilot_canonical_candidate.jsonl`](../../../data/interim/annotation/sprint03/pilot_conversion/approved_round2/pilot_canonical_candidate.jsonl) sau QA. [Manifest máy đọc được](../../../data/processed/annotation/sprint03/pilot_gold_v1_manifest.json) lưu đường dẫn, trạng thái, người duyệt, số lượng và toàn bộ hash. Pilot gold là tập gán nhãn để xây dựng/huấn luyện và kiểm quy tắc; **100 ứng viên benchmark test vẫn giữ riêng**, chưa gán nhãn và chưa dùng để báo F1 T0.
