# Prompt cho agent hiện thực Nhóm 2 và Nhóm 3

**Cách dùng:** mỗi phiên agent nhận **Khối chung** của [07_agent_prompts_group1.md](07_agent_prompts_group1.md) (dán nguyên, nhưng thay dòng đọc trước bằng dòng ở "Đọc trước bổ sung" bên dưới và dùng mốc test ở "Mốc test") + đúng **một** khối gói của file này. Phiên review dùng [07b_reviewer_prompt_group1.md](07b_reviewer_prompt_group1.md) (quy trình 8 bước), chỉ ghi đúng một file trong `docs/sprints/sprint_04/reviews/`. Kế hoạch gốc: [15_group2_group3_plan.md](15_group2_group3_plan.md).

**Đọc trước bổ sung (thay mục "Đọc trước" của Khối chung):** AGENTS.md; `docs/sprints/sprint_04/15_group2_group3_plan.md`; `docs/sprints/sprint_04/14_group1_summary.md`; tài liệu nêu ở khối gói.

**Mốc test:** 453 test, 445 PASS / 8 SKIP / 0 FAIL (đo 15/10/2026, `~/.venv_dacn`). Đo lại khi bắt đầu gói; không được có FAIL, không được làm giảm số PASS.

**Điều chỉnh Khối chung cho Nhóm 2–3:** ràng buộc 1 thêm `data/interim/annotation/` và `docs/sprints/sprint_04/` (trừ file được liệt kê ở "File bạn sở hữu") chỉ đọc; ràng buộc 5 áp dụng cho mọi số đo; thêm: gán nhãn là việc của chủ dự án, agent không tạo gold, không gợi ý nhãn trong vòng đo lặp, không tự phân xử; không crawl nguồn mới, không gửi tin cho người ngoài, không upload khi chưa được chủ dự án cho phép trong phiên.

Mọi số ghi "(đo 15/10)" dưới đây do phiên điều phối đo trên repo ngày 15/10/2026; agent **phải tái lập trước khi làm**, số nào lệch thì dừng và báo.

---

## G2-6 — Kiểm khả năng có dữ liệu cho phần thiếu của Nhóm 1

```text
NHIỆM VỤ: báo cáo khả thi (chỉ đọc dữ liệu có sẵn, không thu thêm, không chạy mô hình) cho bốn việc Nhóm 1 để lại do thiếu dữ liệu:
(a) E2: có đơn vị cũ nào với ≥ 2 đích quan sát khác nhau, đủ để tách "tên đường quyết định đích" khỏi "nhớ đích theo đơn vị" không;
(b) T2 loại A và C: có thể dựng bộ đánh giá T2 cho cạnh A/1-N và C/1-1 từ dữ liệu có sẵn không, và với bằng chứng gì;
(c) nhãn mốc (MocDinhVi, HuongDi, GhiChu, ToaNha/CanHo) và `Lai` do người thật viết: nguồn nào trong source register có thể chứa, trạng thái quyền;
(d) kết luận: mỗi việc ở trạng thái RUNNABLE_NOW / NEEDS_NEW_SOURCE / NOT_FEASIBLE, kèm con số.

File bạn sở hữu: scripts/74_audit_data_feasibility.py, tests/test_group2_feasibility.py,
data/processed/evaluation/sprint04/data_feasibility_20261016_v1/, docs/sprints/sprint_04/19_data_feasibility_g2_6.md.
Không tạo gold, không sửa dữ liệu nguồn, không đưa gì vào corpus.

Dữ liệu (chỉ đọc):
- data/processed/osm/osm_real_bidirectional_pairs.csv (1.631 dòng, 18 cột, Nguon = OSM Diff History; cột TinhThanh/QuanHuyen/PhuongXa_Cu/_Moi, DiaChi_Cu/_Moi, HinhHocThayDoi)
- data/processed/benchmark/07_bidirectional_pairs_verified.csv (600 dòng, M 356, B 244)
- data/processed/gazetteer/s3_v2/edges.csv (10.597 cạnh; cột old_province, old_district, old_ward, new_province, new_ward, new_ward_code, relation, merge_form), non_atomic_transitions.csv (5 dòng)
- configs/annotation/sprint04/source_register_v1.csv, docs/sprints/sprint_04/04_step1_decision_and_protocol_amendment.md §3 (quyền nguồn)
- src/evaluation/t2_lookup.py (T2Table, classify_relations; dùng lại, không viết lại), src/evaluation/leak_guard.py (admin_group_key)
- docs/sprints/sprint_04/09_t2_baseline_results.md §6, §8, §10; 14_group1_summary.md mục e

SỰ THẬT ĐÃ KIỂM (đo 15/10 bởi phiên điều phối, khóa đơn vị cũ = tỉnh|huyện|phường cũ theo chuỗi thô của osm_real_bidirectional_pairs; khóa đích = tỉnh|phường mới):
- 361 đơn vị cũ; 340 có 1 đích, 19 có 2, 1 có 3, 1 có 4 → 21 đơn vị có ≥ 2 đích quan sát (chuỗi thô, chưa chuẩn hóa).
- Gazetteer: 10.035 khóa cũ, 471 có ≥ 2 mã phường mới; chỉ 5 trong 21 đơn vị OSM ở trên (7 dòng) cũng có ≥ 2 đích trong gazetteer. Nghĩa là 16/21 đơn vị có ≥ 2 đích OSM nhưng gazetteer chỉ cho một đích: nghi do khóa thô trùng tên khác huyện/tỉnh, alias, hoặc nhãn OSM sai; CHƯA kiểm. Đây là điều bạn phải làm rõ trước khi kết luận.
- Quan hệ gazetteer: B/N-1 9.432, M/M-N 1.030, C/1-1 132, A/1-N 3 cạnh. Data 07 chỉ có B và M.
- Mọi dòng OSM pairs có HinhHocCoDuLieu = True; 287/1.631 HinhHocThayDoi = True. AGENTS.md mục 6: không suy đích split/M-N khi thiếu hình học; cặp quan sát từ OSM chỉ hợp lệ khi số nhà và tên đường không đổi.

Việc cần làm:
1. Tái lập các số trên. Chuẩn hóa khóa bằng AdministrativeMapping/alias đã kiểm chứng (src/data/administrative_mapping.py, administrative_alias.py), rồi đếm lại số đơn vị cũ có ≥ 2 đích.
2. E2: với mỗi đơn vị cũ có ≥ 2 đích sau chuẩn hóa, kiểm đích có khớp một cạnh gazetteer (đích hợp lệ) không; đếm dòng, số đơn vị, số cụm (admin_group_key); ghi mỗi đơn vị có dòng nào cho phép đích phụ thuộc tên đường hay không. Kết luận E2 RUNNABLE_NOW chỉ khi có đủ đơn vị và dòng để CI cụm không vô nghĩa; ghi ngưỡng bạn dùng và lý do (không chọn ngưỡng sau khi thấy kết quả).
3. T2 loại A và C: đếm cạnh A/C trong gazetteer và số có dòng OSM quan sát tương ứng (đã có đích quan sát hợp lệ); nêu bằng chứng tối thiểu để dựng cặp (AGENTS.md mục 6: không dựng A/M khi thiếu hình học/tọa độ). Không dựng cặp mới.
4. Nhãn mốc và `Lai` thật: đọc source register v1, báo mỗi nguồn: nhãn có thể có (từ mô tả, không phải từ mẫu), quyền local/annotation/cloud/redistribution theo decision log v2; số mẫu ước lượng chỉ nêu khi có số đo, ghi rõ "ước lượng" nếu không.
5. Kết luận từng việc bằng bảng (trạng thái, số liệu, blocker, người quyết). Ghi mọi điều suy luận thay vì đo được.

XONG KHI: báo cáo 19 có bảng kết luận và số tái lập được, script tạo lại được từ đầu vào thư mục mới, test mới PASS, bộ test cũ không đổi.
```

---

## G3-2 — Đặc tả T3 (Opus 5.5, gói thiết kế; không hiện thực)

```text
NHIỆM VỤ: viết đặc tả T3 (đối sánh hai địa chỉ theo thời gian) đủ để ĐATN hiện thực, theo mục 6 của đề cương: "chỉ thiết kế và đặc tả" cho ĐACN. KHÔNG viết mã hệ thống T3, không huấn luyện, không dựng tập dữ liệu mới.

File bạn sở hữu: docs/sprints/sprint_04/20_t3_specification.md (và nếu cần ví dụ tái lập: scripts/75_t3_spec_examples.py cùng tests/test_t3_spec_examples.py, chỉ đọc dữ liệu có sẵn để trích ví dụ; không bắt buộc).

Đọc: đề cương docs/proposal/de-cuong-dacn-dia-chi-tieng-viet.pdf (T3, giả thuyết, metric, mục 6); 14_group1_summary.md; 09_t2_baseline_results.md; 10_t1_h5_results.md; AGENTS.md mục 6.
Công cụ có sẵn để mô tả, không sửa: src/evaluation/t2_lookup.py (T2Table, Resolution, STRICT/DEFAULT/STREET), src/evaluation/t1_pipeline.py (T1-PIPE), src/evaluation/t1_situations.py (thẻ tình huống A–D), src/data/administrative_mapping.py.

SỰ THẬT ĐÃ KIỂM (đo 15/10 bởi phiên điều phối; agent tái lập các số liên quan khi dùng làm ví dụ):
- Data 07: 600 cặp (DiaChi_Cu, DiaChi_Moi), M 356, B 244, 49 đơn vị cũ chuẩn hóa, 23 mã phường mới; mỗi cặp là cùng một phần tử OSM trước/sau, số nhà và tên đường không đổi. Không có cặp ÂM (hai địa chỉ khác nhau cố ý) trong Data 07: đặc tả phải định nghĩa cách dựng cặp âm từ dữ liệu có sẵn và nêu giới hạn.
- T2 (WP1, 14 mục b3): cũ→mới 0,965, mới→cũ 0,077 (luật mặc định, N2); 554/600 lỗi im lặng ở chiều mới→cũ; khóa giải tất định 95,3% (cũ) so với 4,1% (mới).
- Gazetteer s3_v2: 10.597 cạnh nguyên tử (B/N-1 9.432, M/M-N 1.030, C/1-1 132, A/1-N 3), 5 chuyển đổi phi nguyên tử (huyện → đặc khu), mã phường cũ chưa xác minh (2.187/…, release PARTIAL_OLD_CODES_UNVERIFIED), hai bản chụp 30/06 và 01/07/2025, chưa có khoảng hiệu lực pháp lý.
- T1: T1-PIPE (span + luật gazetteer) 0,969 trên test 64 eligible; `Lai` support 5, mọi số `Lai` là LOW_SUPPORT.

Nội dung bắt buộc trong đặc tả:
1. Định nghĩa bài toán: đầu vào (hai chuỗi địa chỉ, mỗi chuỗi kèm hoặc không kèm mốc thời gian), đầu ra (SAME_PLACE / DIFFERENT_PLACE / UNDETERMINED hoặc điểm, kèm lý do có thể truy vết), và thế nào là "cùng một địa điểm qua cải cách". Phân biệt rõ T3 với T2 (T3 so hai chuỗi, T2 ánh xạ một đơn vị).
2. Cách dùng T0, T1, T2 làm thành phần: sơ đồ luồng, hợp đồng giao diện giữa các bước, và cách lan truyền bất định (T1 `Lai`/`khong_ro`, T2 nhiều ứng viên, lỗi im lặng).
3. Dựng dữ liệu đánh giá từ Data 07 (cặp dương) và quy tắc dựng cặp âm từ gazetteer/OSM, kể cả cặp âm khó (cùng phường mới, khác số nhà/đường; cùng tên phường ở hai tỉnh); ước tính cỡ có thể dựng từ dữ liệu hiện có (có số đo) và rủi ro rò rỉ (dùng leak_guard.admin_group_key khi chia nhóm; Data 07 chỉ 23 mã phường mới nên cụm ít).
4. Metric: tách accuracy chung khỏi tỷ lệ lỗi im lặng (khớp nhầm khi đáng lẽ UNDETERMINED); báo coverage/abstention; CI theo cụm; ca N-1, M-N phân tầng riêng; nêu rõ cái gì Data 07 không đo được (A, C, đích phụ thuộc tên đường).
5. Ba đến năm ví dụ cụ thể, chạy tay hoặc bằng script tái lập, lấy từ dữ liệu thật: một ca N-1 (khớp), một ca M-N (mơ hồ → UNDETERMINED), một ca lỗi im lặng T2 mới→cũ, một cặp âm khó. Ghi rõ ví dụ lấy từ dòng nào.
6. Kế hoạch đánh giá cho ĐATN: baseline đề xuất, giả thuyết có thể kiểm, điều kiện dừng, và cái cần thêm (gazetteer có khoảng hiệu lực, dữ liệu `Lai` thật, mốc thời gian).
7. Phạm vi và rủi ro: những gì đặc tả KHÔNG hứa; mọi con số hoặc giả định không đo được phải dán nhãn "ước lượng" hoặc "giả định".

XONG KHI: tài liệu 20 đủ bảy mục, mọi số dẫn được về báo cáo 09/10/14 hoặc phép đo có lệnh tái lập, không có mã hệ thống T3. Nếu viết script ví dụ: test mới PASS, bộ test cũ không đổi.
```
