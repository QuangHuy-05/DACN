import ast
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
import pandas as pd
from src.data.noise_profiler import write_noise_profile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VQA_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "viet_receipt_vqa"
RAW_CSV_FALLBACK = PROJECT_ROOT / "data" / "interim" / "viet_receipt" / "viet_receipt_raw_addresses.csv"
OUT_FILE = PROJECT_ROOT / "data" / "interim" / "vqa" / "viet_receipt_raw_addresses.csv"
NOISE_CONFIG = PROJECT_ROOT / "configs" / "noise_params.json"

# =====================================================================
# 1. HÀM LÀM SẠCH NHIỄU BẨN (CLEANING)
# =====================================================================
def clean_vqa_address(text: str) -> str:
    """Làm sạch các loại nhiễu đặc thù từ OCR hóa đơn."""
    if not isinstance(text, str) or not text.strip():
        return ""

    # 1.1 Tách dòng, loại bỏ các dòng lặp lại nguyên văn do OCR quét trùng
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    unique_lines = []
    for line in lines:
        if line not in unique_lines:
            unique_lines.append(line)
    text = ", ".join(unique_lines)

    # 1.2 Xóa số điện thoại, hotline, số tổng đài (VD: 024.71066866-49301, 01224114004)
    text = re.sub(r'(\+?84|0\d{2,3})[.\s\/-]?\d{3,4}[.\s\/-]?\d{3,5}(-\s*\d+)?', '', text)

    # 1.3 Xóa mã POS / tiền tố định danh chuỗi bán lẻ đầu chuỗi (VM+, VMM+, VIM+, V/H+, CS1:...)
    text = re.sub(r'^(V[MIHT41W][A-Z0-9\+\s\/\-\.]*?(QNH|CNH|HNI|ONH|QHH|QBH|GNH|GLH|CHH)?\s+)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(VM\+|VMM\+|VMT\+|VIM\+|V\/H\+|V4\-|W4\+|VHH\+|V1A\+|V11\+|GNH|CS\d+:?)\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(Vinh\s*\+\s*[A-Z0-9\+]+|Vth\s*[\+\-]\s*[A-Z0-9\+]+|Võ\s+[A-Z0-9\+]+\s+)', '', text, flags=re.IGNORECASE)

    # 1.4 Xóa dấu ngoặc kép và các ký tự rác ở đầu/cuối chuỗi
    text = text.replace('"', '').replace("'", "")
    text = re.sub(r'^[,\-\+\.\s]+', '', text)
    text = re.sub(r'[,\-\+\.\s]+$', '', text)

    # 1.5 Chuẩn hóa khoảng trắng và dấu phẩy ngăn cách
    text = re.sub(r'\s*,\s*', ', ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def is_valid_vqa_address(addr: str) -> bool:
    """Lọc bỏ các chuỗi rác, bị cụt hoặc không chứa thông tin địa danh hợp lệ."""
    # Quá ngắn hoặc bị cắt cụt lửng lơ
    if len(addr) < 12 or addr.endswith('...') or addr.endswith('..') or addr.endswith(' -'):
        return False

    # Chứa danh sách nhiều cơ sở dạng liệt kê
    if 'CS1:' in addr or 'CS2:' in addr:
        return False

    # Phải chứa ít nhất 1 từ khóa định vị hoặc đơn vị hành chính
    lower = addr.lower()
    geo_keywords = [
        'đường', 'phố', 'ngõ', 'ngách', 'hẻm', 'số', 'phường', 'quận', 'huyện', 
        'thị xã', 'thành phố', 'tỉnh', 'p.', 'q.', 'tp.', 'tx.', 'h.', 't.', 
        'kdc', 'khu', 'tổ', 'chợ', 'toà', 'tầng', 'ấp', 'thôn', 'xã',
        'hà nội', 'quảng ninh', 'hồ chí minh', 'hải phòng', 'đà nẵng', 'gia lâm', 
        'cẩm phả', 'đống đa', 'cầu giấy', 'ba đình', 'hoàn kiếm', 'bình thạnh', 'gò vấp', 'tân phú'
    ]
    return any(k in lower for k in geo_keywords)

# =====================================================================
# 2. HÀM LỌC TRÙNG THÔNG MINH (FUZZY DEDUPLICATION)
# =====================================================================
def normalize_for_fuzzy(s: str) -> str:
    """Đưa chuỗi về dạng không dấu, bỏ ký tự đặc biệt để so sánh cốt lõi địa danh."""
    s = s.lower()
    s = re.sub(r'[^\w\s]', ' ', s)
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.replace('đ', 'd')
    return re.sub(r'\s+', ' ', s).strip()

def deduplicate_fuzzy(addresses: list, similarity_threshold: float = 0.82, max_variants_per_cluster: int = 2) -> list:
    """
    Gom các biến thể sai chính tả của cùng một địa chỉ cửa hàng.
    Giữ lại tối đa 2 biến thể bề mặt sạch và dài nhất cho mỗi cụm.
    """
    clusters = []
    for addr in dict.fromkeys(addresses):
        norm = normalize_for_fuzzy(addr)
        house = re.match(r'^\d+[a-z]?(?:[/-]\d+[a-z]?)*\b', norm)
        matched = False
        for cl in clusters:
            rep_norm = normalize_for_fuzzy(cl[0])
            rep_house = re.match(r'^\d+[a-z]?(?:[/-]\d+[a-z]?)*\b', rep_norm)
            if (house.group() if house else None) != (rep_house.group() if rep_house else None):
                continue
            if SequenceMatcher(None, norm, rep_norm).ratio() >= similarity_threshold:
                cl.append(addr)
                matched = True
                break
        if not matched:
            clusters.append([addr])

    final_list = []
    for cl in clusters:
        # Sắp xếp ưu tiên chuỗi dài hơn, đầy đủ trường hơn
        sorted_cl = sorted(list(set(cl)), key=lambda x: len(x), reverse=True)
        final_list.extend(sorted_cl[:max_variants_per_cluster])

    return sorted(final_list)

# =====================================================================
# 3. THỰC THI CHÍNH
# =====================================================================
def main():
    print("Đang nạp dữ liệu hóa đơn thô...")
    raw_list = []

    # Ưu tiên đọc từ file parquet gốc nếu có
    parquet_files = sorted(VQA_RAW_DIR.glob("*.parquet"))
    if parquet_files:
        for file_path in parquet_files:
            df = pd.read_parquet(file_path, columns=['extractions'])
            if 'extractions' in df.columns:
                for _, row in df.iterrows():
                    ext = row['extractions']
                    if isinstance(ext, dict) and ext.get('Địa chỉ'):
                        raw_list.append(str(ext['Địa chỉ']).strip())
                    elif isinstance(ext, str):
                        try:
                            d = ast.literal_eval(ext)
                            if isinstance(d, dict) and d.get('Địa chỉ'):
                                raw_list.append(str(d['Địa chỉ']).strip())
                        except Exception:
                            pass
    # Nếu không có parquet, đọc từ file CSV thô hiện có
    elif RAW_CSV_FALLBACK.exists():
        df_csv = pd.read_csv(RAW_CSV_FALLBACK)
        col = 'ChuoiDiaChi' if 'ChuoiDiaChi' in df_csv.columns else df_csv.columns[0]
        raw_list = df_csv[col].dropna().astype(str).tolist()
    else:
        print(f"Không tìm thấy dữ liệu tại {VQA_RAW_DIR} hoặc {RAW_CSV_FALLBACK}")
        return

    print(f"Tổng số bản ghi thô: {len(raw_list)}")

    # Bước 1: Làm sạch nhiễu bẩn
    cleaned_candidates = [clean_vqa_address(addr) for addr in raw_list]
    valid_candidates = [addr for addr in cleaned_candidates if is_valid_vqa_address(addr)]
    print(f"Sau khi làm sạch và loại bỏ rác: {len(valid_candidates)} bản ghi hợp lệ.")

    # Bước 2: Khử trùng lặp mờ và gom biến thể
    unique_final = deduplicate_fuzzy(valid_candidates, similarity_threshold=0.82, max_variants_per_cluster=2)
    print(f"Sau khi lọc trùng và gom biến thể: còn {len(unique_final)} địa chỉ duy nhất.")

    # Bước 3: Xuất file interim và hồ sơ nhiễu thực đo
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df_out = pd.DataFrame({'ChuoiDiaChi': unique_final})
    df_out.to_csv(OUT_FILE, index=False, encoding='utf-8-sig')
    print(f"Đã lưu danh sách vào: {OUT_FILE}")
    profile = write_noise_profile(OUT_FILE, NOISE_CONFIG)
    print(f"Đã lưu tham số nhiễu ({profile['sample_size']} mẫu) vào: {NOISE_CONFIG}")

    print("\n--- Một số mẫu địa chỉ sạch sau khi lọc ---")
    for sample in unique_final[:8]:
        print(f" • {sample}")

if __name__ == "__main__":
    main()
