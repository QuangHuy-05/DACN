# Protocol Sprint 4 — dữ liệu mới và độ tin cậy T0/T1

**Version:** `s4-protocol-v1`. **Ngày lập:** 06/10/2026. **Hạn bàn giao:** 20/10/2026, múi giờ `Asia/Saigon`.

**Trạng thái:** nhiệm vụ 1 đã được đặc tả và khóa mốc Sprint 3; nguồn, số mẫu, release dữ liệu và tài nguyên chạy vẫn có cổng kiểm tra riêng. Chưa có corpus, annotation hoặc thực nghiệm Sprint 4 được nghiệm thu.

Protocol này thay thế các giả định hai người của [kế hoạch ban đầu](01_sprint4_two_person_plan.md). Các lựa chọn do chủ dự án xác nhận và các đề xuất vận hành được phân biệt bên dưới. Cấu hình tương ứng: [protocol_v1.json](../../../configs/annotation/sprint04/protocol_v1.json).

## 1. Quyết định và trách nhiệm

| Nội dung | Đã xác nhận / cách áp dụng |
|---|---|
| Người phụ trách | Chủ dự án phụ trách dữ liệu, gán nhãn, mô hình, rà soát và duyệt phát hành. Không giả định thêm thành viên hoặc chữ ký thứ hai. |
| Người gán | Một người. IAA giữa hai người giữ `NOT_MEASURED`; đây là giới hạn được khai báo trong phạm vi Sprint 4. |
| Nguồn | Ưu tiên nguồn mới. Chủ dự án cho phép tìm kiếm; từng nguồn vẫn phải có căn cứ về phạm vi sử dụng trước khi nhập corpus. |
| Holdout | Mục tiêu có holdout mới; chỉ cam kết sau kiểm kê và audit nguồn/nhóm/trùng. |
| Thời hạn | Hai tuần từ 06/10 đến 20/10/2026. |
| Compute | Kaggle; số mẫu, quota tài khoản và thời gian thực nghiệm chưa được đo. |

Các đề xuất vận hành của protocol: pilot 20 mẫu; mục tiêu tham khảo 200 mẫu mới; gán lặp sau ít nhất 7 ngày; ba seed và ngân sách dự kiến tối đa 18 GPU-giờ. Đây là tham số kế hoạch, không phải số mẫu đã thu, quota được cấp hoặc chi phí đã phát sinh.

## 2. Phạm vi, mốc khóa và hợp đồng nhãn

- T0 dùng nguyên schema 11 nhãn: `SoNha`, `TenDuong`, `Ngo/Hem`, `ToaNha/CanHo`, `PhuongXa`, `QuanHuyen`, `TinhThanh`, `MocDinhVi`, `HuongDi`, `GhiChu`, `Khac`.
- Offset Python half-open `[start,end)`, substring nguyên bản, span phẳng không chồng lấp. Không sửa OCR hoặc bổ sung thành phần vắng mặt vào gold.
- T1: `cu`, `moi`, `Lai`; gold chưa đủ căn cứ là null hoặc có quyết định loại riêng. Dự đoán abstain là `khong_ro`, không phải lớp gold thứ tư. Mask T1 giữ nguyên toàn bộ T0.
- Guideline kế thừa [s3-span-v1.1](../sprint_03/span_11_annotation_guideline.md). Nếu mở rộng quy tắc cho văn bản chỉ dẫn hoặc nhiều địa chỉ, tạo guideline Sprint 4 có version trước gán; không sửa guideline Sprint 3.
- Địa chỉ cơ quan, trường, bệnh viện hoặc địa điểm công khai được xem xét; địa chỉ nhà riêng/khách hàng và nội dung bệnh án/hỏi đáp cá nhân bị loại.
- T2, T3, API/RAG/Docker và mở lại Deepparse nằm ngoài phạm vi.

Mốc đọc: `corpus_v1_release2`, `test_gold_v1_release2`, config/lựa chọn cuối, scorer, guideline và báo cáo cuối Sprint 3. [Baseline snapshot](../../../data/interim/annotation/sprint04/protocol_v1/baseline_snapshot.json) ghi hash thực đo trước chỉnh sửa protocol và kiểm tra lại sau chỉnh sửa; bao gồm hai best checkpoint. Raw chỉ kiểm size/mtime. Snapshot này có phạm vi ghi rõ, không được gọi là đã tái kiểm toàn bộ ledger lịch sử 2.352 file.

Không dùng lại test Sprint 3 để phát triển, chọn mô hình hoặc bù holdout. Trong nhiệm vụ 1, chỉ đọc coverage/kết quả tổng hợp đã công bố và hash file test; không dùng nội dung gold test để thiết kế quy tắc theo từng mẫu.

## 3. Thiếu hụt hiện tại và mục tiêu support

Nguồn đếm: coverage release2. Support T0 là **số span**, không phải số mẫu hay số địa điểm độc lập.

| Nhãn | Train | Dev | Test lịch sử, chỉ tham chiếu tổng hợp |
|---|---:|---:|---:|
| SoNha | 215 | 56 | 88 |
| TenDuong | 221 | 60 | 99 |
| Ngo/Hem | 24 | 13 | 13 |
| ToaNha/CanHo | 5 | 0 | 0 |
| PhuongXa | 227 | 61 | 89 |
| QuanHuyen | 136 | 37 | 56 |
| TinhThanh | 210 | 54 | 99 |
| MocDinhVi | 6 | 0 | 0 |
| HuongDi | 5 | 1 | 0 |
| GhiChu | 5 | 1 | 0 |
| Khac | 3 | 1 | 2 |

Train có 71 mẫu quan sát / 69 dẫn xuất / 100 tổng hợp; dev có 16 / 12 / 32. Chưa có bảng chéo span hiếm theo provenance trong coverage, nên không tự coi tất cả support hiếm là dữ liệu quan sát.

T1 train: 119 `cu`, 71 `moi`, 16 `Lai`, 34 null; dev: 31/15/8/6 trước mask, 53 eligible sau mask. Test lịch sử có 64 eligible / 20 null / 16 excluded; support `Lai` dùng khi chấm là 5, khác số 6 trước mask trong coverage. Không trộn hai mẫu số.

Ưu tiên kiểm kê năm nhãn hiếm và T1 `Lai`. Mốc tham khảo sau gán/duyệt: mỗi nhãn hiếm có 20 span train, 5 dev, 10 holdout và 10 site group trong phần quan sát; mỗi lớp T1 có 10 mẫu eligible trong dev/holdout. Các mốc này là chính sách báo support, không chứng minh đủ công suất thống kê và không phải quota phải đạt bằng sinh mẫu. Đếm cả số mẫu/site group và tách provenance.

Support 0: `NOT_EVALUABLE_NO_GOLD_SUPPORT`; support dương dưới mốc: `LOW_SUPPORT`, vẫn báo điểm và cỡ mẫu, không kết luận tổng quát. Mẫu tổng hợp chỉ ở stress track riêng và không bù support quan sát. Hạ mục tiêu chỉ bằng decision log trước phát hành, không sửa nhãn để đạt số lượng.

## 4. Nguồn mới đã tìm và điều kiện nhập corpus

[Source register](../../../configs/annotation/sprint04/source_register_v1.csv) lưu URL, publisher/family, trạng thái tìm kiếm, loại nguồn, nhãn có thể có và các việc cần xác minh. Hiện đây là **danh sách nguồn ứng viên**, chưa phải dữ liệu thu được hoặc đã được phép phát hành.

| Ưu tiên | Nguồn đã tìm | Giá trị tiềm năng và giới hạn |
|---|---|---|
| 1 | [UEH — cơ sở trực thuộc](https://hotro.ueh.edu.vn/bai-viet/co-so-truc-thuoc-580) | Trang có địa chỉ cũ/mới và hướng dẫn di chuyển. Cần xem quyền dùng; các đoạn của cùng campus phải cùng nhóm. Không coi cách trình bày hai địa chỉ cũ/mới là gold `Lai` tự động. |
| 1 | [Hà Nội — Thông báo 729/TB-UBND](https://vanban.hanoi.gov.vn/chi-tiet-van-ban/ve-dia-diem-tru-so-lam-viec-cua-126-phuong-xa-sau-sap-xep-thuoc-pham-vi-quan-ly-cua-thanh-pho-ha-220624) | Kết quả tìm kiếm chính thức xác nhận văn bản 25/06/2025 và tài liệu đính kèm về 126 phường/xã. Lần mở trực tiếp lỗi; chưa trích PDF hoặc đếm địa chỉ hợp lệ. 126 đơn vị không đồng nghĩa 126 mẫu độc lập. |
| 2 | [Sở QH-KT TP.HCM — chức năng/nhiệm vụ](https://qhkt.hochiminhcity.gov.vn/chuc-nang-nhiem-vu.html) | Đã xem địa chỉ cơ quan có ghi tầng; tiềm năng `GhiChu`. Cần quyền sử dụng và rà nguyên văn. |
| 2 | [QH-KT — thông báo tuyển dụng 2024](https://qhkt.hochiminhcity.gov.vn/Media/Uploads/Tin%20t%E1%BB%A9c/N%C4%83m%202024/245-TB-TTNCKT.pdf) | PDF 6 trang có thông tin phòng/địa chỉ cơ quan theo kết quả tìm kiếm. Chưa trích nội dung; địa điểm trùng trang hiện hành phải gộp site group. Chỉ lấy khối địa điểm công khai. |
| 2 | [UEH — địa điểm hội thảo](https://ueh.edu.vn/college/cob/vi/hoi-thao-khoa-hoc-quoc-gia-%E2%80%9Ckinh-te-luat-va-chinh-sach-cong-nghe-so-dong-luc-phat-trien-quoc-gia-trong-ky-nguyen-vuon-minh%E2%80%9D-73821) | Kết quả tìm kiếm nêu mã phòng tại campus; cần mở trang/trích khối địa điểm và xác minh quyền dùng. Không tách campus này thành nguồn độc lập với trang cơ sở. |
| 3 | [Từ Dũ — cổng hướng dẫn](https://www.tudu.com.vn/) | Đã xác nhận mục bản đồ/đường đi; chưa xác nhận văn bản đủ nhãn hiếm. Chỉ xem hướng dẫn địa điểm; loại nội dung người bệnh. |
| Dự phòng | [OpenStreetMap — giấy phép](https://www.openstreetmap.org/copyright) | ODbL có điều kiện ghi nguồn/phân phối. Snapshot mới vẫn thuộc cùng family OSM đã dùng ở Sprint 3, không tự chứng minh độc lập nguồn. Không nhập vào corpus trước quyết định attribution/license/privacy/overlap riêng. |

Các trang cơ quan/đại học/bệnh viện công khai chưa được xác nhận quyền đưa văn bản vào corpus hoặc upload cloud: giữ `PENDING_TERMS`, 0 mẫu annotation-ready tại thời điểm nhiệm vụ 1. Giấy phép OSM đã xác nhận nhưng clearance cho dataset Sprint 4 vẫn chờ. Không suy rằng truy cập được, hay Kaggle private, đồng nghĩa được tái sử dụng/phân phối.

Trước nhập mẫu: xác minh quyền local research, annotation, cloud upload và redistribution riêng; lưu điều khoản/permission, ngày, hash bản nguồn khi thực sự thu và decision log. Không gửi yêu cầu xin phép tới người khác nếu chưa có ủy quyền gửi tin.

Khối nhập phải nguyên văn và liên tục trong nguồn; không ghép footer hiện hành với địa chỉ trong bài cũ rồi gọi đó là địa chỉ lai. OCR nguồn PDF được đánh dấu riêng; văn bản dựng từ nhiều ô/bảng là `derived` có trace. Một trang có nhiều địa chỉ hoặc nhắc cũ/mới nhận cờ `temporal_multimention`; T1 chưa rõ để null cho tới khi guideline mới quy định rõ. Ngày bài đăng không tự quyết định hệ hành chính của chuỗi.

## 5. Quy mô, phân tầng, split và cổng holdout

- Đề xuất pilot **20 mẫu mới** để đo phút/mẫu (gán + kiểm + phân xử) và tỷ lệ mẫu hợp lệ.
- Mục tiêu tham khảo **200 mẫu mới**: 120 train / 30 dev / 50 holdout; chưa cam kết. Phân nhóm có thể làm số lượng lệch mục tiêu. Quy mô được chốt theo nguồn hợp lệ và thời gian pilot; giảm cỡ mẫu khi cần, không tạo quota giả.
- Ước lượng công việc bằng thời gian thực đo: số mẫu × phút/mẫu + thời gian gán lặp + xử lý ca khó + 20% dự phòng. Mốc lập lịch ban đầu 60–90 phút gán/rà mỗi ngày; chưa được chủ dự án cam kết.
- Phân tầng theo provenance, publisher/family, địa lý có bằng chứng, cũ/mới/lai/không rõ, nhãn hiếm và chất lượng văn bản. `candidate_labels` chỉ dùng chọn mẫu, không phải gold.
- Track chính mặc định dùng train/dev/holdout Sprint 4 mới. Không tự gộp train hoặc dev Sprint 3. Nếu muốn augmentation bằng train cũ, ghi amendment và run riêng trước thí nghiệm.
- Đặt document group và site group trước split. Nối các mẫu chung tài liệu/địa điểm, bản sao, phiên bản cũ/mới, đoạn OCR hoặc biến thể vào cùng group component. Publisher/family khác nhau không tự bảo đảm độc lập địa lý; khác site key chưa xác minh cũng không đủ.
- Kiểm exact/normalized/near-duplicate với tập mới và registry Sprint 3; kiểm text/hash phía scorer giữ cách ly gold test. Seed chia nhóm `42`; cặp mơ hồ có quyết định, lý do và người duyệt. Không chia nhóm để đạt tỷ lệ đẹp.

**Cổng holdout, quyết định trước 09/10:** tối thiểu mục tiêu 50 mẫu hợp lệ, 20 site group có căn cứ, 2 document group; nguồn/privacy/use rights đủ và 0 group/trùng chưa xử lý với train/dev/Sprint 3. Đây là ngưỡng vận hành cho đánh giá thăm dò, không bảo đảm mọi nhãn đủ support. Kiểm kê chưa đạt thì trạng thái `HOLDOUT_NOT_COMMITTED`, tiếp tục dev/stability và báo PARTIAL theo hạng mục.

Default holdout là **group-disjoint trên nguồn mới**, không mặc nhiên source-family-disjoint hoặc đại diện toàn quốc. Nếu thật sự giữ lại publisher/family chưa xuất hiện ở train/dev, báo subset đó riêng. Bộ chỉ gồm một tài liệu danh sách không vượt điều kiện 2 document group; mọi bản mirror của danh sách đó vẫn một document group.

Holdout do chủ dự án gán thủ công với ID/text, không xem prediction của mô hình được đánh giá; gold được đóng riêng trước thí nghiệm. Cùng người gán và phát triển không tạo được đánh giá mù độc lập về con người, phải khai báo. Sau khóa không sửa nhãn do thấy lỗi mô hình; correction phát hành version mới và báo riêng.

## 6. Kiểm tra nhãn khi chỉ có một người gán

IAA người-người = `NOT_MEASURED`. AI không đóng vai người gán độc lập. Thay đổi phạm vi này đã được khai báo trước dữ liệu mới; nghiệm thu không đòi một chỉ số IAA giả hoặc ghi bằng 0.

1. Pilot 20 mẫu gán thủ công, chốt guideline/ca khó trước batch chính. Vòng chính train/dev có thể dùng AI-assisted candidate; chủ dự án rà toàn bộ. Lưu annotation mode và nguồn gợi ý; không coi việc Submit là đồng thuận độc lập.
2. Chọn **train/dev mới** để gán lặp: `min(N_train_dev, 60, max(30, ceil(0.15*N_train_dev)))`; nếu chưa đủ 30, gán lặp toàn bộ và nêu cỡ mẫu nhỏ. Phân tầng nhãn hiếm/ca mơ hồ, giữ xác suất và support, không chỉ chọn ca dễ.
3. Tập gán lặp có hai vòng thủ công; không có prediction hoặc nhãn vòng trước. Vòng 1 làm 09–10/10, vòng 2 từ 17/10, mỗi mẫu cách ít nhất 7×24 giờ; đổi thứ tự/ID hiển thị, giữ mapping và hai raw export/hash.
4. Tính **intra-annotator** exact-span P/R/F1: vòng 1 là reference, vòng 2 là prediction; cùng `[start,end,label]` mới là match. Cohen Kappa token-level dùng regex Unicode `\w+|[^\w\s]`, token nằm trọn span nhận nhãn đó, còn lại `O`. Token cắt qua ranh giới span làm Kappa `NOT_MEASURED_TOKEN_ALIGNMENT` kèm danh sách lỗi; vẫn đo exact-span, không sửa gold chỉ để ép token. Nếu expected agreement bằng 1 hoặc không có token, Kappa null và nêu lý do. T1 agreement chỉ trên mẫu cả hai vòng eligible, giữ riêng số null/mask/bất đồng. Báo confusion/support và khả năng nhớ mẫu; tập phân tầng có chủ đích không đại diện toàn corpus. Không lấy agreement sau phân xử. Có thể dùng công thức metric hiện có nhưng không giả ID người gán để vượt cổng hai người của script pilot Sprint 3.
5. Lưu kết quả hai vòng trước khi cùng chủ dự án tự phân xử; ghi lý do/thời điểm/phiên bản. Mỗi ca mơ hồ được rà 100%; QA offset, substring, overlap, ID, missing, system và privacy. AI chỉ hỗ trợ phát hiện vấn đề, chưa là người duyệt.
6. Không đặt ngưỡng agreement hậu nghiệm để chọn mẫu đẹp. Agreement thấp dẫn tới rà guideline/ca khó trước freeze; không loại bất đồng khỏi báo cáo. Nếu không thực hiện vòng 2 hoặc chưa đủ 7 ngày, intra = `NOT_MEASURED`, hạng mục kiểm tra lặp PARTIAL, không gọi toàn bộ hạng mục nhãn đã đạt.

## 7. Đánh giá và Kaggle

Roster: HEUR-JW, CRF-INDEP, PHOBERT-CRF, PROPOSED-DYN và ablation cùng checkpoint. CRF/PhoBERT T1 vẫn `NOT_IMPLEMENTED` nếu chưa có thay đổi được khóa riêng. Ba seed `42,1337,2025`; HEUR chạy một cấu hình cố định. DYN off dùng trọng số/calibration/input của DYN on, không tạo ba lượt train thêm.

T0 exact `[start,end,label]` full11 micro P/R/F1 và per-label support; nhãn không hỗ trợ vẫn tính FN. Báo macro all11 và gold-supported riêng. T1 báo accuracy, macro-F1, confusion, eligible/null/excluded, coverage, accepted accuracy và abstention; abstain vẫn nằm trong mẫu số eligible. Báo từng seed và mean/std mẫu (`ddof=1`, thiếu seed thì null hoặc ghi cỡ n); không chỉ đưa seed tốt nhất. Chênh on/off paired theo mẫu và bootstrap theo sample, không coi span độc lập. Với ít group, khai báo bootstrap/group uncertainty còn hạn chế.

Hyperparameter bắt đầu từ lựa chọn dev Sprint 3 đã khóa (c02 neural); một cấu hình/model, không sweep rộng. Epoch chọn bằng full11 dev micro F1 → gold-supported macro → epoch sớm. Decoder policy DYN được xác minh có threshold **0.7**, margin **0.2**, chọn trên dev Sprint 3. Tối đa 6 tổ hợp calibration trên **dev mới**: threshold `[0.7,0.8,0.9]` × margin `[0.1,0.2]`, chọn theo T1 macro-F1 toàn ba lớp → accuracy → accepted coverage → threshold/margin cao hơn, khóa trước holdout. Chỉ calibration khi mỗi lớp dev có ít nhất 10 mẫu eligible; chưa đủ thì giữ policy cũ và ghi `CALIBRATION_NOT_EVALUABLE`. Không chọn seed/model/checkpoint/threshold bằng holdout; báo mọi seed đã cam kết, khóa roster, cách tổng hợp và prediction trước scorer. Không tự bỏ lớp khó để tune.

Kaggle đề xuất:

- Private dataset/kernel; chỉ upload train/dev đã duyệt, mã và tài nguyên có quyền cloud. Holdout text-only đưa vào job inference riêng sau khóa; gold giữ local/scorer riêng. Private không vượt điều khoản nguồn; Gazetteer/raw nguồn quyền chưa rõ giữ local.
- Một GPU được cấp là đủ để lập kế hoạch; kiểm GPU/VRAM thực tế và smoke save/reload/alignment trước full run, không mặc định hai T4. Khởi đầu với profile Sprint 3 và precision đã kiểm chứng; đổi cấu hình phần cứng tạo run/profile mới.
- Quota tài khoản tại thời điểm chạy phải đọc từ giao diện Kaggle. [Docs](https://www.kaggle.com/docs/notebooks) và [thông báo floating quota](https://www.kaggle.com/discussions/product-feedback/173129) là tài liệu tham khảo, không phải bằng chứng tài khoản có 30 giờ/tuần hay 60 giờ trong hai tuần. Lần tra cứu này không đọc được nội dung trang JS hoặc quota tài khoản.
- **18 GPU-giờ là ngân sách kế hoạch do agent đề xuất**, chưa đo: 12 giờ train, 2 giờ smoke/inference, 4 giờ dự phòng. Sau smoke đo thời gian từng model/epoch và dự báo 3×PCRF + 3×DYN + inference/overhead; chỉ chạy nếu quota thực còn đủ. HEUR/CRF dùng CPU khi tài nguyên có quyền chạy ở đó; HEUR cần Gazetteer chưa được phép cloud thì chạy local hoặc ghi blocker.
- Job chạy tuần tự, run ID theo model/seed/corpus hash; checkpoint best/last, manifest, prediction và thời gian phải được nhận/hash sau từng job. Thiếu quota: ưu tiên đủ seed42 của hai neural rồi seed1337/2025 cho cả hai theo cặp; phần thiếu `PARTIAL_SEEDS`, không tuyên bố đa seed ổn định.
- Trong nhiệm vụ 1 chưa submit/upload/train/install hoặc đo GPU thực. Smoke/training trên dữ liệu thật phải qua cổng release/resource trước.

## 8. Lịch hai tuần và nghiệm thu

| Thời gian | Công việc | Điều kiện chuyển bước |
|---|---|---|
| 06–08/10 | Protocol, nguồn/điều khoản, kiểm kê, nhóm/trùng, chuẩn bị runner/resource | Nguồn đủ căn cứ trước lấy mẫu annotation; quyết định holdout có bằng chứng |
| 09–10/10 | Pilot 20, đo thời gian; vòng 1 tập gán lặp; chốt quy mô khả thi | Guideline được khóa, lưu raw vòng 1 |
| 11–16/10 | Gán/rà toàn bộ, quyết định ca khó; chuẩn bị candidate và QA | Không train trên candidate chưa duyệt |
| 17/10 | Vòng 2 sau đủ 7 ngày, tính intra trước phân xử, QA/freeze release | Gold/split/hash được duyệt trước thí nghiệm; IAA vẫn NOT_MEASURED |
| 18–19/10 | Kaggle smoke, train/dev nhiều seed, paired ablation | Hash/resources/quota và nhận artifact đủ; chọn bằng dev |
| 20/10 | Khóa lựa chọn/prediction, scorer holdout nếu đạt gate, kết quả/tái lập/nghiệm thu | Báo PASS/PARTIAL/BLOCKED từng đầu ra và giới hạn |

Nếu nguồn/quyền dùng chưa qua gate vào 09/10, giảm phạm vi hoặc báo thiếu holdout. Không rút ngắn thời gian gán lặp để bù trễ. Nếu release không khóa được 17/10, lịch training phải cập nhật theo ngân sách thực; không bỏ cổng để kịp hạn.

Checklist nhiệm vụ 1: [x] quyết định chủ dự án và phạm vi một người; [x] protocol/metric/split/label contract; [x] bảng thiếu hụt từ metadata; [x] snapshot mốc và hai checkpoint; [x] nguồn mới ứng viên với trạng thái quyền dùng; [x] kế hoạch intra/holdout/Kaggle và hạn hai tuần. Kết quả kiểm tra file/hash lưu trong snapshot. Các mốc dưới đây là công việc tiếp theo, chưa đạt ở nhiệm vụ 1.

Checklist phát hành/nghiệm thu Sprint 4:

- [ ] Nguồn/privacy/use scope/raw hash/group hợp lệ cho mọi mẫu; số lượng thực đo và decision log.
- [ ] Split và duplicate audit, không có trường hợp chưa xử lý xuyên tập; holdout có quyết định COMMITTED hoặc NOT_COMMITTED và lý do.
- [ ] Hai vòng intra đủ cách ly, raw/hash, metrics trước phân xử; IAA ghi NOT_MEASURED và giới hạn một người.
- [ ] QA toàn bộ, ngoại lệ có quyết định; release mới được chủ dự án duyệt; Sprint 3 không đổi.
- [ ] Runs theo seed, corpus/code/resource/prediction hash, metric/mẫu số/hardware rõ, on/off cùng checkpoint/calibration.
- [ ] Holdout sau khóa, evaluation card, phân tích lỗi, hướng dẫn tái lập; support thiếu và seed thiếu báo rõ.

Quyền nguồn/thu mẫu: chủ dự án phụ trách, ảnh hưởng cả annotation/cloud/release; giải pháp là căn cứ sử dụng hoặc thay nguồn. Holdout chưa đủ: kiểm kê nhóm/site/support, không bù bằng test cũ. Quota chưa biết: kiểm tra tài khoản và smoke thật. Các trạng thái pending này không được đổi thành PASS từ việc đã viết protocol.
