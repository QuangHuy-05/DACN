# U4 — Thực nghiệm baseline nhẹ, chỉ development

Kế hoạch trước chạy: `configs/experiments/sprint03/pre_colab_followup_v1.json`. Một phiên bản rule HEUR mới và một phiên bản feature CRF mới; không mở thêm search sau xem metric 5 trường.

## Changes và ngân sách

- HEUR v4 hỗ trợ prefix viết gọn, Gazetteer v4 dual snapshot explicit, candidate code evidence/cha/ngày/tie/abstain trace. Giữ raw offsets. Sáu threshold 0,82/0,86/0,90/0,94/0,98/1,00; margin0,02. Chọn all-schema exact-span dev F1, hòa ưu tiên threshold cao hơn. Chosen0,86. HEUR chỉ support sáu nhãn, không là parser đủ11.
- CRF `surface_admin_segment_cue_v2` thêm cue hành chính trong segment và dạng token, hoàn toàn từ text. BIO23/tokenizer/offset/projection giữ nguyên. Tám candidate: context1/2 × `(c1,c2)=(0,05;0,1),(0,1;0,1),(0,1;1),(0,5;1)`, seed42. Chosen context1,c1=0,1,c2=1. Train chỉ240, chọn bằng60 dev.
- Feature/rule cũ giữ behavior mặc định, run cũ không sửa. CRF checkpoint thật hash `b4ff0d23427934cf10fbfe72764eb83d931bec05a8fb8b4a3056df8c682004f8`.

## Kết quả

| Track | HEUR frozen → mới | CRF frozen → mới |
| --- | --- | --- |
| T0 dev60 exact-span micro F1 | 88,01% → **88,01%** | 89,82% → **90,56%** |
| 5 trường TEXT_ONLY4.800 hàng micro F1 | 82,04% → **81,99%** | 85,41% → **85,59%** |

HEUR mới TP235/FP15/FN49, P94,00/R82,75; 59ok/1abstain. CRF TP259/FP29/FN25, P89,93/R91,20,60ok. Mean dev latency HEUR1,90ms, CRF0,24ms trên máy local; không là so sánh hardware chuẩn giữa lần cũ/mới. Trace/sweep/support từng nhãn nằm trong run.

5 trường chạy inference trước, scoring sau trên runtime dự án có pandas sẵn; runtime CRF không có pandas, không cài thêm để chấm. HEUR4.794ok/6abstain, CRF4.800ok. Exact record HEUR1.727/4.800, CRF3.236/4.800. Input hashes và100 hold được loại theo runner hiện hành; không tune bằng những metric này.

Không có cải thiện HEUR trên T0 và giảm nhẹ 5 trường: giữ run frozen làm mốc hiệu năng; v4 là candidate có provenance/temporal scope rõ hơn. CRF mới là chosen development candidate. Không gọi điểm dev đã tune là kết quả test cuối.

HEUR T1 đánh giá53 mẫu đủ điều kiện, accepted46/53, accepted accuracy86,96%, accuracy toàn eligible75,47%, macroF1 ba lớp78,68%. CRF T1 **NOT_IMPLEMENTED**. Task543 mask khỏi mọi chẩn đoán dùng T1, giữ T0.

Chẩn đoán quận dev: cả hai0/14 mẫu gold `moi` đủ điều kiện có predicted `QuanHuyen`. Recall exact quận HEUR15/29 (`cu`),5/6 (`Lai`); CRF27/29 và6/6. Điều này chỉ đúng dev nhỏ; không tuyên bố triệt tiêu hoàn toàn ảo giác quận. Track5 trường CRF vẫn17 FP quận/1.861 mẫu gold mới không quận. Không dùng dev0 `MocDinhVi`,0 `ToaNha/CanHo`,1 `HuongDi` để kết luận chất lượng nhãn hiếm.

## Artifact

```text
data/processed/evaluation/sprint03/
  heur_jw_followup_20261003_v1/       6 threshold runs, precision_coverage.csv, chosen config
  crf_followup_20261003_v1/          8 training/checkpoint/dev runs, chosen config
  heur_jw_followup_fivefield_20261003_v1/
  crf_followup_fivefield_20261003_v1/
```

Mỗi run có prediction, native output/trace, metrics/support/errors, resource/input/output/code hashes, model config và inference/scoring manifest. Read-only audit16run ở `pre_colab_20261003_resume_v1/u5/acceptance_v1/`.

Tái chạy dùng output/run ID **mới**, không dùng tên đã phát hành:

```bash
python -m scripts.27_sweep_heur_jw_dev --experiment-id heur_replay001 --output-dir data/processed/evaluation/sprint03/heur_replay001 --gazetteer-dir data/processed/gazetteer/s3_v4_nso_dual_snapshot --rule-version v4
python -m scripts.26_train_independent_crf --experiment-id crf_replay001 --output-dir data/processed/evaluation/sprint03/crf_replay001 --feature-version surface_admin_segment_cue_v2
python -m scripts.28_run_fivefield_experiment infer --config <chosen_model_config.json> --output-dir <new-fivefield-run>
python -m scripts.28_run_fivefield_experiment score --run-dir <new-fivefield-run>
```

Chạy CRF trong runtime_py311 có python-crfsuite0.9.12, scoring5field trong env dự án hiện hữu có pandas. Các đường dẫn placeholder chỉ dùng sau lựa chọn config dev; chưa tạo run mới chỉ để minh họa.
