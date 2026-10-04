import random
import re
import pandas as pd

REGION_MAP = {
    'Bac': [
        'hà nội', 'hải phòng', 'quảng ninh', 'bắc ninh', 'hải dương', 'hưng yên',
        'hà nam', 'nam định', 'thái bình', 'ninh bình', 'vĩnh phúc', 'phú thọ',
        'thái nguyên', 'bắc giang', 'lạng sơn', 'tuyên quang', 'hà giang', 'cao bằng',
        'bắc kạn', 'lào cai', 'yên bái', 'điện biên', 'lai châu', 'sơn la', 'hòa bình'
    ],
    'Trung': [
        'thanh hóa', 'nghệ an', 'hà tĩnh', 'quảng bình', 'quảng trị', 'thừa thiên huế',
        'đà nẵng', 'quảng nam', 'quảng ngãi', 'bình định', 'phú yên', 'khánh hòa',
        'ninh thuận', 'bình thuận', 'kon tum', 'gia lai', 'đắk lắk', 'đắk nông', 'lâm đồng'
    ],
    'Nam': [
        'hồ chí minh', 'bình dương', 'đồng nai', 'bà rịa - vũng tàu', 'tây ninh',
        'bình phước', 'long an', 'tiền giang', 'bến tre', 'trà vinh', 'vĩnh long',
        'đồng tháp', 'an giang', 'kiên giang', 'cần thơ', 'hậu giang', 'sóc trăng',
        'bạc liêu', 'cà mau', 'tp.hcm', 'tphcm', 'sài gòn'
    ]
}

def detect_macro_region(province_str, address_str=""):
    target = f"{province_str} {address_str}".lower()
    for reg, keywords in REGION_MAP.items():
        if any(kw in target for kw in keywords):
            return reg
    return 'Khac'

def apply_prefix_abbreviations(text, prefix_type, abbrev_probs=None, rng=None):
    if not text or pd.isna(text):
        return ""
    text = str(text).strip()
    if abbrev_probs is None:
        abbrev_probs = {}
    rng = rng or random

    p_district = abbrev_probs.get('district_Q', 0.75)
    p_city = abbrev_probs.get('city_TP', 0.80)
    p_ward_p = abbrev_probs.get('ward_P', 0.60)
    p_ward_f = abbrev_probs.get('ward_F', 0.10)

    if prefix_type == 'ward':
        roll = rng.random()
        if re.match(r'^Phường\b', text, flags=re.IGNORECASE):
            if roll < p_ward_p:
                rep = rng.choice(['P. ', 'P.', 'P '])
                return re.sub(r'^Phường\s+', rep, text, flags=re.IGNORECASE)
            elif roll < p_ward_p + p_ward_f:
                rep = rng.choice(['F. ', 'F.', 'F '])
                return re.sub(r'^Phường\s+', rep, text, flags=re.IGNORECASE)
            elif roll < p_ward_p + p_ward_f + 0.15:
                return re.sub(r'^Phường\s+', '', text, flags=re.IGNORECASE)
        elif re.match(r'^Xã\b', text, flags=re.IGNORECASE):
            if roll < p_ward_p:
                rep = rng.choice(['X. ', 'X.', 'X '])
                return re.sub(r'^Xã\s+', rep, text, flags=re.IGNORECASE)
        elif re.match(r'^Thị trấn\b', text, flags=re.IGNORECASE):
            if roll < p_ward_p:
                rep = rng.choice(['TT. ', 'TT.', 'TT '])
                return re.sub(r'^Thị trấn\s+', rep, text, flags=re.IGNORECASE)

    elif prefix_type == 'district':
        if rng.random() < p_district:
            if re.match(r'^Quận\b', text, flags=re.IGNORECASE):
                rep = rng.choice(['Q. ', 'Q.', 'Q '])
                return re.sub(r'^Quận\s+', rep, text, flags=re.IGNORECASE)
            elif re.match(r'^Huyện\b', text, flags=re.IGNORECASE):
                rep = rng.choice(['H. ', 'H.', 'H '])
                return re.sub(r'^Huyện\s+', rep, text, flags=re.IGNORECASE)
            elif re.match(r'^Thị xã\b', text, flags=re.IGNORECASE):
                rep = rng.choice(['TX. ', 'TX.', 'TX '])
                return re.sub(r'^Thị xã\s+', rep, text, flags=re.IGNORECASE)
            elif re.match(r'^Thành phố\b', text, flags=re.IGNORECASE):
                rep = rng.choice(['TP. ', 'TP.', 'TP '])
                return re.sub(r'^Thành phố\s+', rep, text, flags=re.IGNORECASE)

    elif prefix_type == 'city':
        if rng.random() < p_city:
            if re.search(r'Hồ Chí Minh', text, flags=re.IGNORECASE):
                return rng.choice(['TP.HCM', 'TPHCM', 'TP. HCM', 'HCM'])
            if re.search(r'Hà Nội', text, flags=re.IGNORECASE):
                return rng.choice(['TP. Hà Nội', 'TP.HN', 'Hà Nội', 'HN'])
            if re.match(r'^Thành phố\b', text, flags=re.IGNORECASE):
                rep = rng.choice(['TP. ', 'TP.', 'TP '])
                return re.sub(r'^Thành phố\s+', rep, text, flags=re.IGNORECASE)
            elif re.match(r'^Tỉnh\b', text, flags=re.IGNORECASE):
                if rng.random() < 0.6:
                    return re.sub(r'^Tỉnh\s+', '', text, flags=re.IGNORECASE)
                else:
                    rep = rng.choice(['T. ', 'T.', 'T '])
                    return re.sub(r'^Tỉnh\s+', rep, text, flags=re.IGNORECASE)

    return text
