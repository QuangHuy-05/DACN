# Inventory trước cài — sáu việc tiếp theo, 03/10/2026

Quyền cài/tải đã được chủ dự án cấp trong prompt thực hiện. Tất cả file cài/tải/cache/temp mới phải nằm trên D. Không train, không sử dụng test100, không thay môi trường hiện hữu.

## Mốc trước thay đổi

- WSL kernel 6.6.87.2, x86_64. Python 3.11.16 hiện có được dùng làm interpreter nền; không cài lại hoặc thay nó.
- Runtime CRF hiện hữu chỉ có pip24.0/python-crfsuite0.9.12; không thay runtime này.
- WSL RAM total3.906.109.440 bytes, available3.386.060.800 bytes; swap1.073.741.824 bytes tại lần đo ban đầu.
- D free13.622.988.800 bytes tại lần đo WSL ban đầu; đo chính xác lại ngay trước mỗi tải lớn. Giữ ít nhất3GiB trống sau dự báo.
- Java chưa có. Full FastText không được tải: RAM thấp hơn gate10GiB và license embedding/weights còn pending.

## Thành phần cho phép resolve/cài

| Thành phần | Pin / nguồn chính thức | License code | Ước lượng tải / dung lượng lưu | Mục đích |
|---|---|---|---|---|
| Venv trên D | Python3.11.16 hiện có, venv copies | Python/PSF | <100MiB | Runtime mới `data/interim/modeling/sprint03/runtime_neural_d_v1` |
| torch CPU |2.8.0, https://download.pytorch.org/whl/cpu |BSD3, https://github.com/pytorch/pytorch/blob/v2.8.0/LICENSE |CPU stack0,5–1,5GB sau cài; resolver đo wheel thực |CRF tensor/tiny forward-backward/checkpoint |
| transformers |4.57.1, PyPI version page |Apache2 |stack0,2–0,5GB |PhoBERT tokenizer/encoder local |
| deepparse |0.11.0, PyPI version page |LGPLv3 |wheel233,8KB; transitive dự phòng1GB |Actual parser/container signature; không pretrained FastText full |
| Poutyne |1.17.4, PyPI version page |LGPLv3 |riêng package<50MB |Native API/callback imports; không train |
| py-vncorenlp |0.1.4, PyPI version page |MIT wrapper |sdist3,9KB; pyjnius/numpy resolve riêng |VnCoreNLP wseg interface |
| Java local |Temurin/OpenJDK17 LTS exact build sau metadata inspection |GPL2+Classpath exception |JRE dự phòng100MB compressed/250MB extracted |Local segmentation; không apt/system install |
| PhoBERT-base |vinai/phobert-base, exact revision/file list sau inspection |MIT theo VinAI; lưu model card/LICENSE |weights~0,54GB, tokenizer nhỏ; dự phòng0,7GB |Tokenizer alignment và một CPU forward |
| VnCoreNLP wseg |vncorenlp/VnCoreNLP, pinned commit/jar1.2 |GPL3-or-later; assets đối chiếu repository |dự phòng0,3GB |Actual segmentation 240/60 |

Không tải mô hình/hình thức khác để thay baseline. Không cài CUDA, torchvision, torchaudio hoặc dependency không cần. Transitive dependency sẽ được ghi version/license/source/size từ resolver report **trước actual install**; nếu conflict pins, dừng phần đó và giữ các phần độc lập.

Destinations: venv, `install_cache_d_v1` (wheel/cache/tmp) và `resources_d_v1` (Java/model/segmenter), tất cả dưới `data/interim/modeling/sprint03/`. Process env điều hướng pip/HF/Torch/XDG/UV/temp vào D; không sửa HOME/dotfiles/.wslconfig.

Evidence bổ sung và kết quả cuối ghi trong `data/interim/modeling/sprint03/task_01_06_20261003_v1/` và báo cáo follow-up mới. Bản inventory này giữ lịch sử cài ban đầu; license weights/embedding được kiểm riêng với license package.
