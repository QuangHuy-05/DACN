# U2 — Gazetteer hai snapshot, còn partial

Gói hiện hành: `data/processed/gazetteer/s3_v4_nso_dual_snapshot_release2/`. Gói `s3_v4_nso_dual_snapshot/` đã dùng cho baseline mới và được giữ nguyên. Release2 hoàn chỉnh metadata/sổ nguồn, không đổi entity/code/graph/alias/evidence bytes của v4.

## Counts và scope

- 14.149 entity, 10.597 cạnh xã nguyên tử, 187 alias đã audit, 5 chuyển đổi huyện→đặc khu phi nguyên tử; cùng ID/tên/cha/graph với parent v3.
- **8.607 mã cũ** xác minh tại **30/06/2025**: 62 tỉnh + 561 huyện + 7.984 xã.
- **3.355 mã mới** giữ từ parent v3 tại **01/07/2025**: 34 tỉnh + 3.321 xã.
- Tổng 11.962 code evidence; **2.187 entity cũ vẫn chưa xác minh**. `PARTIAL_OLD_CODES_UNVERIFIED` tiếp tục có hiệu lực.
- `verified_as_of` là ngày snapshot được chứng minh. `legal_valid_from=UNKNOWN`; không lấy ngày query làm ngày thành lập đơn vị.

`source_register.csv` có 7 mục, gồm ba response SOAP cũ và nguồn snapshot mới. `metadata_completion.json` ghi hash năm file giữ nguyên, `coverage_report.json`/`verified_code_counts` ghi counts dual snapshot; summary new-only của parent được chuyển thành `parent_new_snapshot_summary` để tránh hiểu nhầm tổng cũ bằng 0.

## Lookup

Reader `DualSnapshotGazetteer` kiểm mọi output hash. Tra theo tên nguyên, cấp, ngày, hệ tùy chọn và tỉnh/huyện cha tùy chọn. Mã giống nhau ở hai hệ không là cùng entity. Ngoài hai snapshot trả `OUT_OF_SNAPSHOT_SCOPE`; thiếu cha có thể `AMBIGUOUS`; chưa verified chỉ trả candidate, không xuất code như official verified. Giữ mọi đích A/1-N/M/M-N và 5 cạnh phi nguyên tử.

```bash
python -m scripts.41_nso_dual_snapshot lookup --help
python -m scripts.44_complete_nso_source_register --help
```

Build/publish từ chối ghi đè. v1/v2/v3 và v4 đã dùng chạy baseline không bị thay. Source metadata code snapshot của release2 ở `pre_colab_20261003_resume_v1/u2_metadata_code_snapshot/`; code hiện hành tính counts trực tiếp từ entity verified cho các lần phát hành sau, giữ bytes của release2.

Kiểm thử fixtures: code có zero đầu, code tái dùng, hai ngày, ngoài scope, cha sai/trùng tên, chưa mã, nhiều đích, hash drift, sổ nguồn và từ chối overwrite. Evidence QA toàn gói ở báo cáo [35](35_pre_colab_acceptance.md).

Gói dữ liệu/reference mới giữ local vì điều khoản tái phân phối nguồn chưa được xác định. GitHub bàn giao builder/reader/tests/docs; artifact local được chỉ rõ trong manifest/bàn giao riêng.
