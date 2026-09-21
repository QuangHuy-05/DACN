import tempfile
import unittest
import importlib.util
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.data.administrative_mapping import load_administrative_mapping
from src.data.noise_profiler import profile_noise
from src.data.osm_extractor import HistoryBiDirectionalMapper, clean_tag
from src.data.synthetic.bidirectional import generate_bidirectional_pairs
from src.data.synthetic.hybrid_address import generate_hybrid_addresses, get_new_province, select_unique_hybrids
from src.data.synthetic.missing_fields import (
    DROP_FIELDS,
    generate_missing_fields,
    validate_clean_source,
    validate_missing_surface,
)
from src.data.synthetic.raw_noisy import generate_raw_noisy_addresses


class FakeElement:
    def __init__(self, element_id, timestamp, tags, visible=True):
        self.id = element_id
        self.timestamp = timestamp
        self.tags = tags
        self.visible = visible


class DataPipelineTests(unittest.TestCase):
    def test_non_latin_rejected_and_street_tail_cleaned(self):
        self.assertEqual(clean_tag("Đường Số 10, "), "Đường Số 10")
        self.assertEqual(clean_tag("شارع السلام"), "")
        self.assertEqual(clean_tag("улица"), "")

    def test_deleted_or_untagged_latest_revision_is_not_a_pair(self):
        handler = HistoryBiDirectionalMapper()
        old = datetime(2025, 6, 30, tzinfo=timezone.utc)
        new = datetime(2025, 7, 2, tzinfo=timezone.utc)
        tags = {"addr:street": "Lê Lợi", "addr:ward": "Phường 1", "addr:city": "Hà Nội"}
        handler.process_element(FakeElement(1, old, tags), "node")
        handler.process_element(FakeElement(1, new, {}), "node")
        self.assertIsNone(handler.history_tracker[("node", 1)]["new"])
        self.assertIsNotNone(handler.history_tracker[("node", 1)]["old"])
        handler.pbar.close()

    def test_geometry_is_read_only_for_valid_address_tags(self):
        class CountingHandler(HistoryBiDirectionalMapper):
            def __init__(self):
                super().__init__()
                self.geometry_calls = 0

            def geometry_signature(self, elem, elem_type):
                self.geometry_calls += 1
                return "node:0.0000000,0.0000000"

        handler = CountingHandler()
        old = datetime(2025, 6, 30, tzinfo=timezone.utc)
        handler.process_element(FakeElement(1, old, {"name": "not an address"}), "way")
        handler.process_element(
            FakeElement(2, old, {
                "addr:street": "Lê Lợi", "addr:ward": "Phường 1", "addr:city": "Hà Nội",
            }),
            "node",
        )
        self.assertEqual(handler.geometry_calls, 1)
        handler.pbar.close()

    def test_missing_fields_preserves_truth_and_is_repeatable(self):
        old = pd.DataFrame([{"SoNha": str(i), "TenDuong": f"Đường {i}",
                             "PhuongXa": "Phường 1", "QuanHuyen": "Quận 1",
                             "TinhThanh": "Thành phố Hồ Chí Minh"} for i in range(20)])
        new = old.assign(QuanHuyen="")
        one = generate_missing_fields(old, new, target_size=10)
        two = generate_missing_fields(old, new, target_size=10)
        self.assertEqual(one.to_csv(index=False), two.to_csv(index=False))
        self.assertEqual(one.HeQuyChieu.value_counts().to_dict(), {"cu": 5, "moi": 5})
        self.assertTrue((one[one.HeQuyChieu == "moi"].QuanHuyen == "").all())
        self.assertTrue((one.GT_PhuongXa == "Phường 1").all())

    def test_raw_noisy_data_keeps_ground_truth_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as folder:
            config_path = Path(folder) / "noise.json"
            config_path.write_text("""{
  "noise_probabilities": {
    "abbreviations": {"ward_P": 1.0, "district_Q": 1.0, "city_TP": 1.0},
    "missing_rates": {"drop_housenumber": 1.0, "drop_ward": 1.0, "drop_district": 1.0}
  }
}""", encoding="utf-8")
            old = pd.DataFrame([{
                "SoNha": str(index), "TenDuong": f"Đường Cũ {index}",
                "PhuongXa": "Phường 1", "QuanHuyen": "Quận 1", "TinhThanh": "Thành phố Hà Nội",
            } for index in range(1, 21)])
            new = pd.DataFrame([{
                "SoNha": str(index), "TenDuong": f"Đường Mới {index}",
                "PhuongXa": "Phường Mới", "QuanHuyen": "", "TinhThanh": "Thành phố Hồ Chí Minh",
            } for index in range(1, 21)])
            one = generate_raw_noisy_addresses(old, new, config_path, target_size=20, seed=9)
            two = generate_raw_noisy_addresses(old, new, config_path, target_size=20, seed=9)
            self.assertEqual(one.to_csv(index=False), two.to_csv(index=False))
            self.assertEqual(one.HeQuyChieu.value_counts().to_dict(), {"cu": 10, "moi": 10})
            self.assertTrue((one.ChuoiDiaChi != one.ChuoiDiaChiGoc).all())
            self.assertTrue((one[one.HeQuyChieu == "cu"].GT_QuanHuyen != "").all())
            self.assertTrue((one[one.HeQuyChieu == "moi"].GT_QuanHuyen == "").all())
            self.assertTrue(one.LoaiNhieu.str.contains("dinh_dang_phan_cach").all())

    def test_hybrid_never_fabricates_unknown_province(self):
        self.assertEqual(get_new_province("Tỉnh Kiên Giang"), "Tỉnh An Giang")
        self.assertEqual(get_new_province(""), "")
        self.assertEqual(get_new_province("Unknownland"), "")

    def test_hybrid_selection_rejects_conflicting_surface_labels(self):
        candidates = {
            "C2": [{"ChuoiDiaChi": "same", "KieuLai": "C2"}],
            "C3": [{"ChuoiDiaChi": "same", "KieuLai": "C3"}, {"ChuoiDiaChi": "other", "KieuLai": "C3"}],
        }
        selected = select_unique_hybrids(candidates, {"C2": 1, "C3": 1}, seed=42)
        self.assertEqual({row["ChuoiDiaChi"] for row in selected}, {"same", "other"})

    def test_noise_profile_has_auditable_denominator(self):
        profile = profile_noise(["12 Lê Lợi, P. 1, Q. 1, TP.HCM", "Đường A, Phường 2, Hà Nội"])
        self.assertEqual(profile["sample_size"], 2)
        self.assertEqual(profile["counts"]["abbreviations"]["ward_P"], 1)
        self.assertEqual(profile["counts"]["abbreviations"]["district_Q"], 1)

    def test_atomic_mapping_preserves_split_merge_and_many_to_many(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            mapping_path = root / "mapping.csv"
            rows = [
                # A: one old unit contributes to two otherwise distinct new units.
                ("Xã A", "Huyện H", "Tỉnh Cũ", "Tỉnh Mới", "Xã A1", "Tách — một phần"),
                ("Xã A", "Huyện H", "Tỉnh Cũ", "Tỉnh Mới", "Xã A2", "Tách — nhập chủ yếu"),
                # B: two old units join one new unit.
                ("Xã B1", "Huyện H", "Tỉnh Cũ", "Tỉnh Mới", "Xã B", "Hợp nhất toàn bộ"),
                ("Xã B2", "Huyện H", "Tỉnh Cũ", "Tỉnh Mới", "Xã B", "Hợp nhất toàn bộ"),
                # M: each old unit has several targets and targets have several origins.
                ("Xã M1", "Huyện H", "Tỉnh Cũ", "Tỉnh Mới", "Xã M-A", "Tách — một phần"),
                ("Xã M1", "Huyện H", "Tỉnh Cũ", "Tỉnh Mới", "Xã M-B", "Tách — nhập chủ yếu"),
                ("Xã M2", "Huyện H", "Tỉnh Cũ", "Tỉnh Mới", "Xã M-A", "Tách — nhập chủ yếu"),
                ("Xã M2", "Huyện H", "Tỉnh Cũ", "Tỉnh Mới", "Xã M-B", "Tách — một phần"),
            ]
            pd.DataFrame([{
                "Phường/Xã cũ": old_ward,
                "Quận/Huyện cũ": district,
                "Tỉnh/TP cũ (trước sáp nhập)": old_province,
                "Tỉnh/TP mới": new_province,
                "Phường/Xã mới (từ 1/7/2025)": new_ward,
                "Loại đơn vị mới": "Xã",
                "Mã phường/xã mới": f"{index:05d}",
                "Hình thức sáp nhập": merger_form,
                "Diện tích mới (km²)": "1",
            } for index, (old_ward, district, old_province, new_province, new_ward, merger_form) in enumerate(rows)]).to_csv(mapping_path, index=False)
            mapping = load_administrative_mapping(mapping_path)
            self.assertEqual(mapping.relation_for("Tỉnh Cũ", "Huyện H", "Xã A", mapping.targets_for_old("Tỉnh Cũ", "Huyện H", "Xã A")[0]), ("A", "1-N"))
            self.assertEqual(mapping.relation_for("Tỉnh Cũ", "Huyện H", "Xã B1", mapping.targets_for_old("Tỉnh Cũ", "Huyện H", "Xã B1")[0]), ("B", "N-1"))
            self.assertEqual(mapping.relation_for("Tỉnh Cũ", "Huyện H", "Xã M1", mapping.targets_for_old("Tỉnh Cũ", "Huyện H", "Xã M1")[0]), ("M", "M-N"))

    def test_bidirectional_pairs_do_not_guess_split_or_many_to_many_targets(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            mapping = root / "mapping.csv"
            pairs = root / "pairs.csv"
            snapshot = root / "old.csv"
            edges = [
                ("Xã A", "Xã A1"), ("Xã A", "Xã A2"),
                ("Xã B1", "Xã B"), ("Xã B2", "Xã B"),
                ("Xã M1", "Xã M-A"), ("Xã M1", "Xã M-B"),
                ("Xã M2", "Xã M-A"), ("Xã M2", "Xã M-B"),
            ]
            pd.DataFrame([{
                "Phường/Xã cũ": old_ward, "Quận/Huyện cũ": "Huyện H",
                "Tỉnh/TP cũ (trước sáp nhập)": "Tỉnh Cũ", "Tỉnh/TP mới": "Tỉnh Mới",
                "Phường/Xã mới (từ 1/7/2025)": new_ward, "Loại đơn vị mới": "Xã",
                "Mã phường/xã mới": f"{index:05d}",
                "Hình thức sáp nhập": "Tách — một phần" if old_ward in {"Xã A", "Xã M1", "Xã M2"} else "Hợp nhất toàn bộ",
                "Diện tích mới (km²)": "1",
            } for index, (old_ward, new_ward) in enumerate(edges)]).to_csv(mapping, index=False)
            pd.DataFrame([
                {"OSM_ID": 1, "OSM_Type": "node", "TinhThanh_Cu": "Tỉnh Cũ", "QuanHuyen_Cu": "Huyện H", "PhuongXa_Cu": "Xã A", "PhuongXa_Moi": "Xã A1", "QuanHuyen_Moi": "", "TinhThanh_Moi": "Tỉnh Mới", "SoNha": "1", "TenDuong": "Đường A", "DiaChi_Cu": "1, Đường A, Xã A, Huyện H, Tỉnh Cũ"},
                {"OSM_ID": 2, "OSM_Type": "node", "TinhThanh_Cu": "Tỉnh Cũ", "QuanHuyen_Cu": "Huyện H", "PhuongXa_Cu": "Xã B1", "PhuongXa_Moi": "Xã B", "QuanHuyen_Moi": "", "TinhThanh_Moi": "Tỉnh Mới", "SoNha": "2", "TenDuong": "Đường B", "DiaChi_Cu": "2, Đường B, Xã B1, Huyện H, Tỉnh Cũ"},
                {"OSM_ID": 3, "OSM_Type": "node", "TinhThanh_Cu": "Tỉnh Cũ", "QuanHuyen_Cu": "Huyện H", "PhuongXa_Cu": "Xã M1", "PhuongXa_Moi": "Xã M-A", "QuanHuyen_Moi": "", "TinhThanh_Moi": "Tỉnh Mới", "SoNha": "3", "TenDuong": "Đường M", "DiaChi_Cu": "3, Đường M, Xã M1, Huyện H, Tỉnh Cũ"},
            ]).to_csv(pairs, index=False)
            pd.DataFrame([
                {"OSM_ID": 1, "OSM_Type": "node", "SoNha": "1", "TenDuong": "Đường A", "PhuongXa": "Xã A", "QuanHuyen": "Huyện H", "TinhThanh": "Tỉnh Cũ"},
                {"OSM_ID": 2, "OSM_Type": "node", "SoNha": "2", "TenDuong": "Đường B", "PhuongXa": "Xã B1", "QuanHuyen": "Huyện H", "TinhThanh": "Tỉnh Cũ"},
                {"OSM_ID": 3, "OSM_Type": "node", "SoNha": "3", "TenDuong": "Đường M", "PhuongXa": "Xã M1", "QuanHuyen": "Huyện H", "TinhThanh": "Tỉnh Cũ"},
                {"OSM_ID": 4, "OSM_Type": "node", "SoNha": "4", "TenDuong": "Đường D", "PhuongXa": "Xã B2", "QuanHuyen": "Huyện H", "TinhThanh": "Tỉnh Cũ"},
                {"OSM_ID": 5, "OSM_Type": "node", "SoNha": "5", "TenDuong": "Đường S", "PhuongXa": "Xã A", "QuanHuyen": "Huyện H", "TinhThanh": "Tỉnh Cũ"},
                {"OSM_ID": 6, "OSM_Type": "node", "SoNha": "6", "TenDuong": "Đường X", "PhuongXa": "Xã M2", "QuanHuyen": "Huyện H", "TinhThanh": "Tỉnh Cũ"},
            ]).to_csv(snapshot, index=False)
            result = generate_bidirectional_pairs(pairs, mapping, snapshot, target_size=10)
            self.assertEqual(set(result[result.Nguon.str.startswith("OSM_Diff")].QuanHe), {"1-N", "N-1", "M-N"})
            derived = result[result.Nguon.str.startswith("OSM_Snapshot")]
            self.assertEqual(set(derived.QuanHe), {"N-1"})
            self.assertIn("Đường D", " ".join(derived.DiaChi_Cu))
            self.assertNotIn("Đường S", " ".join(derived.DiaChi_Cu))
            self.assertNotIn("Đường X", " ".join(derived.DiaChi_Cu))

    def test_administrative_alias_normalizes_known_variants_and_typos(self):
        from src.data.administrative_alias import (
            resolve_province_alias,
            resolve_district_alias,
            resolve_ward_alias,
            normalize_diff_record,
            normalize_diff_record_with_trace,
        )
        self.assertEqual(resolve_province_alias("Ho Chi Minh City"), "Thành phố Hồ Chí Minh")
        self.assertEqual(resolve_province_alias("Hanoi"), "Thành phố Hà Nội")
        self.assertEqual(resolve_district_alias("Thành phố Bác Ninh"), "Thành phố Bắc Ninh")
        self.assertEqual(resolve_district_alias("Q.Ba Đình"), "Quận Ba Đình")
        self.assertEqual(resolve_ward_alias("Hàng Buồm"), "Phường Hàng Buồm")

        rec = {
            "TinhThanh_Cu": "Hanoi",
            "QuanHuyen_Cu": "Hoan Kiem",
            "PhuongXa_Cu": "Hang Buom",
            "TinhThanh_Moi": "Hà Nội",
            "QuanHuyen_Moi": "",
            "PhuongXa_Moi": "Phường Hoàn Kiếm",
        }
        normed = normalize_diff_record(rec)
        self.assertEqual(normed["TinhThanh_Cu"], "Thành phố Hà Nội")
        self.assertEqual(normed["QuanHuyen_Cu"], "Quận Hoàn Kiếm")
        self.assertEqual(normed["PhuongXa_Cu"], "Phường Hàng Buồm")
        traced, changes = normalize_diff_record_with_trace(rec)
        self.assertEqual(traced, normed)
        self.assertEqual(len(changes), 4)
        self.assertTrue(any("PhuongXa_Cu: Hang Buom → Phường Hàng Buồm" in c for c in changes))

    def test_direct_pairs_use_full_snapshot_and_audited_aliases(self):
        """A direct OSM observation must not be lost because Set 03 is sampled."""
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            mapping_path = root / "mapping.csv"
            pairs_path = root / "pairs.csv"
            balanced_snapshot = root / "old.csv"
            full_snapshot = root / "osm_old_snapshot_full.csv"

            # Two old wards sharing one new ward create an N-1 official edge.
            pd.DataFrame([
                {
                    "Phường/Xã cũ": "Phường Hàng Buồm", "Quận/Huyện cũ": "Quận Hoàn Kiếm",
                    "Tỉnh/TP cũ (trước sáp nhập)": "Thành phố Hà Nội", "Tỉnh/TP mới": "Thành phố Hà Nội",
                    "Phường/Xã mới (từ 1/7/2025)": "Phường Hoàn Kiếm", "Loại đơn vị mới": "Phường",
                    "Mã phường/xã mới": "00001", "Hình thức sáp nhập": "Hợp nhất toàn bộ",
                    "Diện tích mới (km²)": "1",
                },
                {
                    "Phường/Xã cũ": "Phường Hàng Bồ", "Quận/Huyện cũ": "Quận Hoàn Kiếm",
                    "Tỉnh/TP cũ (trước sáp nhập)": "Thành phố Hà Nội", "Tỉnh/TP mới": "Thành phố Hà Nội",
                    "Phường/Xã mới (từ 1/7/2025)": "Phường Hoàn Kiếm", "Loại đơn vị mới": "Phường",
                    "Mã phường/xã mới": "00001", "Hình thức sáp nhập": "Hợp nhất toàn bộ",
                    "Diện tích mới (km²)": "1",
                },
            ]).to_csv(mapping_path, index=False)
            pd.DataFrame([{
                "OSM_Type": "node", "OSM_ID": "101", "SoNha": "1", "TenDuong": "Đường Hàng Ngang",
                "PhuongXa_Cu": "Hang Buom", "QuanHuyen_Cu": "Hoan Kiem", "TinhThanh_Cu": "Hanoi",
                "PhuongXa_Moi": "Phường Hoàn Kiếm", "QuanHuyen_Moi": "", "TinhThanh_Moi": "Hà Nội",
                "DiaChi_Cu": "1, Đường Hàng Ngang, Phường Hàng Buồm, Quận Hoàn Kiếm, Thành phố Hà Nội",
            }]).to_csv(pairs_path, index=False)
            # The balanced snapshot intentionally does not contain direct ID 101.
            pd.DataFrame([{
                "OSM_Type": "node", "OSM_ID": "202", "SoNha": "2", "TenDuong": "Đường Hàng Bồ",
                "PhuongXa": "Phường Hàng Bồ", "QuanHuyen": "Quận Hoàn Kiếm", "TinhThanh": "Thành phố Hà Nội",
            }]).to_csv(balanced_snapshot, index=False)
            pd.DataFrame([{
                "OSM_Type": "node", "OSM_ID": "101", "SoNha": "1", "TenDuong": "Đường Hàng Ngang",
                "PhuongXa": "Phường Hàng Buồm", "QuanHuyen": "Quận Hoàn Kiếm", "TinhThanh": "Thành phố Hà Nội",
            }]).to_csv(full_snapshot, index=False)

            result = generate_bidirectional_pairs(
                pairs_path, mapping_path, balanced_snapshot, target_size=10,
                full_snapshot_path=full_snapshot,
            )
            direct = result[result["Nguon"].str.startswith("OSM_Diff")]
            self.assertEqual(direct["ID_Node"].tolist(), ["node:101"])
            self.assertEqual(direct["QuanHe"].tolist(), ["N-1"])

    def test_audit_does_not_treat_missing_geometry_as_unchanged(self):
        script_path = Path(__file__).resolve().parents[1] / "scripts" / "04_audit_osm_diff_filters.py"
        spec = importlib.util.spec_from_file_location("osm_diff_audit", script_path)
        audit_module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(audit_module)

        self.assertEqual(audit_module.geometry_status({}), "not_captured")
        self.assertEqual(
            audit_module.geometry_status({"HinhHocCoDuLieu": "False", "HinhHocThayDoi": "False"}),
            "not_captured",
        )
        self.assertEqual(
            audit_module.geometry_status({"HinhHocCoDuLieu": "True", "HinhHocThayDoi": "False"}),
            "unchanged",
        )
        self.assertEqual(
            audit_module.geometry_status({"HinhHocCoDuLieu": "True", "HinhHocThayDoi": "True"}),
            "changed",
        )

    def test_new_address_builder_uses_the_same_alias_layer_as_pair_audit(self):
        script_path = Path(__file__).resolve().parents[1] / "scripts" / "03_generate_benchmarks.py"
        spec = importlib.util.spec_from_file_location("benchmark_generator", script_path)
        benchmark_module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(benchmark_module)

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            mapping_path = root / "mapping.csv"
            pd.DataFrame([{
                "Phường/Xã cũ": "Phường Hàng Buồm", "Quận/Huyện cũ": "Quận Hoàn Kiếm",
                "Tỉnh/TP cũ (trước sáp nhập)": "Thành phố Hà Nội", "Tỉnh/TP mới": "Thành phố Hà Nội",
                "Phường/Xã mới (từ 1/7/2025)": "Phường Hoàn Kiếm", "Loại đơn vị mới": "Phường",
                "Mã phường/xã mới": "00001", "Hình thức sáp nhập": "Hợp nhất toàn bộ",
                "Diện tích mới (km²)": "1",
            }]).to_csv(mapping_path, index=False)
            latest = pd.DataFrame(columns=["SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh"])
            pairs = pd.DataFrame([{
                "SoNha": "1", "TenDuong": "Đường Hàng Ngang", "PhuongXa_Moi": "Phường Hoàn Kiếm",
                "QuanHuyen_Moi": "", "TinhThanh_Moi": "Hà Nội",
            }])
            result = benchmark_module.build_new_addresses(latest, pairs, mapping_path)
            self.assertEqual(result["TinhThanh"].tolist(), ["Thành phố Hà Nội"])
            self.assertEqual(result["QuanHuyen"].tolist(), [""])

    def test_coverage_reporter_computes_multidimensional_metrics(self):
        from src.data.coverage_reporter import analyze_pairs_coverage, generate_coverage_markdown
        df = pd.DataFrame([
            {
                "ID_Node": "node:101",
                "DiaChi_Cu": "1, Đường A, Xã B, Huyện C, Hà Nội",
                "DiaChi_Moi": "1, Đường A, Phường D, Thành phố Hà Nội",
                "QuanHe": "N-1",
                "HinhThucSapNhap": "Hợp nhất toàn bộ",
                "Nguon": "OSM_Diff+vietnam-sap-nhap-phuong-xa.csv",
            },
            {
                "ID_Node": "way:202",
                "DiaChi_Cu": "2, Đường B, Xã M, Huyện N, Thành phố Hồ Chí Minh",
                "DiaChi_Moi": "2, Đường B, Phường P, Thành phố Hồ Chí Minh",
                "QuanHe": "M-N",
                "HinhThucSapNhap": "Tách — nhập chủ yếu",
                "Nguon": "OSM_Snapshot+vietnam-sap-nhap-phuong-xa.csv",
            },
        ])
        stats = analyze_pairs_coverage(df)
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["geometry_counts"], {"node": 1, "way": 1})
        self.assertEqual(stats["relationship_counts"]["N-1"], 1)
        self.assertEqual(stats["relationship_counts"]["M-N"], 1)
        self.assertEqual(stats["relationship_counts"]["1-N"], 0)
        self.assertEqual(stats["region_counts"]["Bac"], 1)
        self.assertEqual(stats["region_counts"]["Trung"], 0)
        self.assertEqual(stats["region_counts"]["Nam"], 1)
        self.assertTrue(any("1-N" in w for w in stats["warnings"]))
        self.assertTrue(any("M-N" in w for w in stats["warnings"]))

        empty = analyze_pairs_coverage(pd.DataFrame())
        self.assertEqual(empty["total"], 0)
        self.assertEqual(empty["direct_relation_counts"]["1-N"], 0)
        self.assertIn("0.0%", generate_coverage_markdown(empty))

    def test_data03_contains_only_complete_legacy_addresses(self):
        """Data 03 must contain complete 5-field legacy addresses and reject incomplete quota."""
        rows = [
            {"SoNha": "1", "TenDuong": "Đường A", "PhuongXa": "Phường 1", "QuanHuyen": "Quận 1", "TinhThanh": "Hà Nội"},
            {"SoNha": "", "TenDuong": "Đường B", "PhuongXa": "Phường 2", "QuanHuyen": "Quận 2", "TinhThanh": "Hà Nội"},
            {"SoNha": "3", "TenDuong": "Đường C", "PhuongXa": "", "QuanHuyen": "Quận 3", "TinhThanh": "Hà Nội"},
        ]
        df = pd.DataFrame(rows)
        fields = ["SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh"]
        complete = df[df[fields].apply(lambda col: col.str.strip().ne("")).all(axis=1)]
        self.assertEqual(len(complete), 1)
        self.assertEqual(complete.iloc[0]["SoNha"], "1")
        # Quota check
        with self.assertRaises(ValueError) as ctx:
            if len(complete) < 1500:
                raise ValueError(f"Not enough complete legacy addresses for Data 03: {len(complete)}/1500")
        self.assertIn("Not enough complete legacy addresses for Data 03: 1/1500", str(ctx.exception))

    def test_missing_fields_removes_only_declared_fields(self):
        """Every missing-field row must drop only the fields specified by KieuThieu."""
        old = pd.DataFrame([{"SoNha": str(i), "TenDuong": f"Đường {i}",
                             "PhuongXa": f"Phường {i}", "QuanHuyen": f"Quận {i}",
                             "TinhThanh": "Thành phố Hồ Chí Minh"} for i in range(1, 31)])
        new = pd.DataFrame([{"SoNha": str(i), "TenDuong": f"Đường Mới {i}",
                             "PhuongXa": f"Phường Mới {i}", "QuanHuyen": "",
                             "TinhThanh": "Thành phố Hà Nội"} for i in range(1, 31)])
        out = generate_missing_fields(old, new, target_size=20, seed=42)
        self.assertEqual(len(out), 20)
        fields = ("SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh")
        for _, row in out.iterrows():
            kt = row["KieuThieu"]
            sys = row["HeQuyChieu"]
            expected_dropped = set(DROP_FIELDS[kt])
            if sys == "moi":
                expected_dropped.add("QuanHuyen")
            for f in fields:
                if f in expected_dropped:
                    self.assertEqual(row[f], "", f"Field {f} should be dropped for {kt}")
                else:
                    self.assertNotEqual(row[f], "", f"Field {f} should not be dropped for {kt}")

    def test_missing_fields_preserves_gt_values(self):
        """Ground truth fields GT_* must be preserved exactly before deletion."""
        old = pd.DataFrame([{"SoNha": str(i), "TenDuong": f"Đường Cũ {i}",
                             "PhuongXa": f"Phường Cũ {i}", "QuanHuyen": f"Quận Cũ {i}",
                             "TinhThanh": "Thành phố Hồ Chí Minh"} for i in range(1, 21)])
        new = pd.DataFrame([{"SoNha": str(i), "TenDuong": f"Đường Mới {i}",
                             "PhuongXa": f"Phường Mới {i}", "QuanHuyen": "",
                             "TinhThanh": "Thành phố Hà Nội"} for i in range(1, 21)])
        out = generate_missing_fields(old, new, target_size=10, seed=42)
        for _, row in out.iterrows():
            sys = row["HeQuyChieu"]
            self.assertTrue(row["GT_SoNha"].strip().isdigit())
            self.assertTrue(row["GT_TenDuong"].startswith("Đường"))
            self.assertTrue(row["GT_PhuongXa"].startswith("Phường"))
            self.assertTrue(row["GT_TinhThanh"].startswith("Thành phố"))
            if sys == "cu":
                self.assertTrue(row["GT_QuanHuyen"].startswith("Quận Cũ"))
            else:
                self.assertEqual(row["GT_QuanHuyen"], "")

    def test_new_system_allows_empty_district(self):
        """Empty QuanHuyen is structural for 2-tier new system, not an error."""
        new = pd.DataFrame([{"SoNha": "10", "TenDuong": "Đường A",
                             "PhuongXa": "Phường B", "QuanHuyen": "",
                             "TinhThanh": "Thành phố Hà Nội"}])
        # Should validate without error
        validate_clean_source(new, "moi")
        # Validation row check
        row_dict = {
            "SoNha": "", "TenDuong": "Đường A", "PhuongXa": "Phường B",
            "QuanHuyen": "", "TinhThanh": "Thành phố Hà Nội",
            "GT_SoNha": "10", "GT_TenDuong": "Đường A", "GT_PhuongXa": "Phường B",
            "GT_QuanHuyen": "", "GT_TinhThanh": "Thành phố Hà Nội",
        }
        validate_missing_surface(row_dict, "moi", "drop_housenumber", source_index=0)

    def test_missing_generator_rejects_incomplete_source(self):
        """Source with missing fields must be rejected immediately."""
        bad_old = pd.DataFrame([{"SoNha": "", "TenDuong": "Đường A", "PhuongXa": "P1", "QuanHuyen": "Q1", "TinhThanh": "HN"}])
        good_new = pd.DataFrame([{"SoNha": "1", "TenDuong": "Đường B", "PhuongXa": "P2", "QuanHuyen": "", "TinhThanh": "HCM"}])
        with self.assertRaises(ValueError) as ctx:
            validate_clean_source(bad_old, "cu")
        self.assertIn("Incomplete clean source for system 'cu'", str(ctx.exception))
        with self.assertRaises(ValueError):
            generate_missing_fields(bad_old, good_new, target_size=2)

        bad_new = pd.DataFrame([{"SoNha": "1", "TenDuong": "Đường B", "PhuongXa": "", "QuanHuyen": "", "TinhThanh": "HCM"}])
        good_old = pd.DataFrame([{"SoNha": "1", "TenDuong": "Đường A", "PhuongXa": "P1", "QuanHuyen": "Q1", "TinhThanh": "HN"}])
        with self.assertRaises(ValueError) as ctx:
            validate_clean_source(bad_new, "moi")
        self.assertIn("Incomplete clean source for system 'moi'", str(ctx.exception))
        with self.assertRaises(ValueError):
            generate_missing_fields(good_old, bad_new, target_size=2)

    def test_data02_uses_complete_sources_only(self):
        """Data 02 requires complete source addresses and produces full GT_*."""
        with tempfile.TemporaryDirectory() as folder:
            noise_cfg = Path(folder) / "noise.json"
            noise_cfg.write_text('{"noise_probabilities": {}}', encoding="utf-8")
            old = pd.DataFrame([{"SoNha": "1", "TenDuong": "Đường A", "PhuongXa": "Phường 1", "QuanHuyen": "Quận 1", "TinhThanh": "Hà Nội"}])
            new = pd.DataFrame([{"SoNha": "2", "TenDuong": "Đường B", "PhuongXa": "Phường 2", "QuanHuyen": "", "TinhThanh": "Hồ Chí Minh"}])
            out = generate_raw_noisy_addresses(old, new, noise_cfg, target_size=2, seed=42)
            self.assertEqual(len(out), 2)
            for _, r in out.iterrows():
                self.assertNotEqual(r["GT_SoNha"], "")
                self.assertNotEqual(r["GT_TenDuong"], "")
                self.assertNotEqual(r["GT_PhuongXa"], "")
                self.assertNotEqual(r["GT_TinhThanh"], "")
                if r["HeQuyChieu"] == "cu":
                    self.assertNotEqual(r["GT_QuanHuyen"], "")
                else:
                    self.assertEqual(r["GT_QuanHuyen"], "")

    def test_data06_uses_complete_legacy_source(self):
        """Data 06 hybrid addresses from complete source must have all 5 surface fields."""
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            mapping_path = root / "mapping.csv"
            pd.DataFrame([{
                "Phường/Xã cũ": "Xã Cũ", "Quận/Huyện cũ": "Huyện Cũ",
                "Tỉnh/TP cũ (trước sáp nhập)": "Tỉnh Cũ", "Tỉnh/TP mới": "Tỉnh Mới",
                "Phường/Xã mới (từ 1/7/2025)": "Phường Mới", "Loại đơn vị mới": "Phường",
                "Mã phường/xã mới": "99999", "Hình thức sáp nhập": "Hợp nhất toàn bộ",
                "Diện tích mới (km²)": "1",
            }]).to_csv(mapping_path, index=False)
            complete_old = pd.DataFrame([{
                "SoNha": "123", "TenDuong": "Đường Cũ", "PhuongXa": "Xã Cũ",
                "QuanHuyen": "Huyện Cũ", "TinhThanh": "Tỉnh Cũ",
            }])
            hybrids = generate_hybrid_addresses(complete_old, mapping_path, target_size=1, seed=42)
            self.assertEqual(len(hybrids), 1)
            row = hybrids.iloc[0]
            self.assertEqual(row["SoNha"], "123")
            self.assertEqual(row["TenDuong"], "Đường Cũ")
            self.assertEqual(row["PhuongXa"], "Phường Mới")
            self.assertEqual(row["QuanHuyen"], "Huyện Cũ")
            self.assertIn(row["TinhThanh"], ("Tỉnh Cũ", "Tỉnh Mới"))

    def test_generators_are_reproducible_with_same_seed(self):
        """Generators must produce identical CSVs with the same seed."""
        old = pd.DataFrame([{"SoNha": str(i), "TenDuong": f"Đường {i}",
                             "PhuongXa": f"Phường {i}", "QuanHuyen": f"Quận {i}",
                             "TinhThanh": "Thành phố Hồ Chí Minh"} for i in range(1, 21)])
        new = pd.DataFrame([{"SoNha": str(i), "TenDuong": f"Đường Mới {i}",
                             "PhuongXa": f"Phường Mới {i}", "QuanHuyen": "",
                             "TinhThanh": "Thành phố Hà Nội"} for i in range(1, 21)])
        run1 = generate_missing_fields(old, new, target_size=10, seed=123)
        run2 = generate_missing_fields(old, new, target_size=10, seed=123)
        self.assertEqual(run1.to_csv(index=False), run2.to_csv(index=False))


if __name__ == "__main__":
    unittest.main()
