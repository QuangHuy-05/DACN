from pathlib import Path
import pandas as pd
from src.data.osm_extractor import HistoryBiDirectionalMapper, balance_dataframe_by_region
from src.utils.text_normalize import detect_macro_region

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_FILE = PROJECT_ROOT / "data" / "raw" / "osm" / "vietnam-internal.osh.pbf"
OUT_OLD_FULL = PROJECT_ROOT / "data" / "interim" / "osm" / "osm_old_snapshot_full.csv"
OUT_OLD = PROJECT_ROOT / "data" / "interim" / "osm" / "osm_old_snapshot_20250630.csv"
OUT_PAIRS = PROJECT_ROOT / "data" / "processed" / "osm" / "osm_real_bidirectional_pairs.csv"

def main():
    if not RAW_FILE.exists():
        print(f"❌ Không tìm thấy file {RAW_FILE}")
        return

    handler = HistoryBiDirectionalMapper()
    try:
        handler.apply_file(str(RAW_FILE))
    finally:
        handler.pbar.close()

    real_pairs, old_snapshot = [], []

    for (elem_type, elem_id), states in handler.history_tracker.items():
        old_state, new_state = states['old'], states['new']
        if old_state:
            old_snapshot.append({
                'OSM_Type': elem_type, 'OSM_ID': elem_id,
                'SoNha': old_state['housenumber'], 'TenDuong': old_state['street'],
                'PhuongXa': old_state['ward'], 'QuanHuyen': old_state['district'],
                'TinhThanh': old_state['city'], 'ChuoiDiaChi': old_state['full_address'],
                'HinhHoc': old_state['geometry_signature'],
                'VungMien': detect_macro_region(old_state['city'], old_state['full_address'])
            })

        if old_state and new_state and states['has_post_cutoff_revision']:
            if (old_state['ward'] != new_state['ward']) or (old_state['district'] != new_state['district']) or (old_state['city'] != new_state['city']):
                real_pairs.append({
                    'OSM_Type': elem_type, 'OSM_ID': elem_id,
                    'SoNha': new_state['housenumber'] or old_state['housenumber'],
                    'TenDuong': new_state['street'] or old_state['street'],
                    'PhuongXa_Cu': old_state['ward'], 'QuanHuyen_Cu': old_state['district'], 'TinhThanh_Cu': old_state['city'],
                    'DiaChi_Cu': old_state['full_address'],
                    'PhuongXa_Moi': new_state['ward'], 'QuanHuyen_Moi': new_state['district'], 'TinhThanh_Moi': new_state['city'],
                    'DiaChi_Moi': new_state['full_address'],
                    'HinhHoc_Cu': old_state['geometry_signature'],
                    'HinhHoc_Moi': new_state['geometry_signature'],
                    # A false "changed" flag is ambiguous when one revision
                    # has no usable geometry.  Preserve availability explicitly
                    # so the downstream audit does not infer "unchanged".
                    'HinhHocCoDuLieu': str(
                        bool(old_state['geometry_signature'])
                        and bool(new_state['geometry_signature'])
                    ),
                    'HinhHocThayDoi': str(
                        bool(old_state['geometry_signature'])
                        and bool(new_state['geometry_signature'])
                        and old_state['geometry_signature'] != new_state['geometry_signature']
                    ),
                    'VungMien': detect_macro_region(new_state['city'] or old_state['city'], new_state['full_address']),
                    'Nguon': 'OSM Diff History (Real User Update)'
                })

    df_old_all = pd.DataFrame(old_snapshot)
    df_old = balance_dataframe_by_region(
        df_old_all[df_old_all['VungMien'].isin(('Bac', 'Trung', 'Nam'))],
        samples_per_region=10000,
    )
    df_pairs = pd.DataFrame(real_pairs)

    OUT_OLD_FULL.parent.mkdir(parents=True, exist_ok=True)
    OUT_OLD.parent.mkdir(parents=True, exist_ok=True)
    OUT_PAIRS.parent.mkdir(parents=True, exist_ok=True)

    df_old_all.to_csv(OUT_OLD_FULL, index=False, encoding="utf-8-sig")
    df_old.to_csv(OUT_OLD, index=False, encoding="utf-8-sig")
    df_pairs.to_csv(OUT_PAIRS, index=False, encoding="utf-8-sig")
    print(f"Đã lưu snapshot đầy đủ ({len(df_old_all)} mẫu) vào {OUT_OLD_FULL}")
    print(f"Đã lưu snapshot cân bằng ({len(df_old)} mẫu) vào {OUT_OLD}")
    print(f"Đã lưu {len(df_pairs)} cặp ánh xạ thực tế vào {OUT_PAIRS}")

if __name__ == "__main__":
    main()
