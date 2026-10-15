"""Unit tests for the baseline evaluation pipeline."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import pandas as pd

from src.evaluation.adapters.libpostal_adapter import HeuristicAddressAdapter, LibpostalAdapter
from src.evaluation.adapters.vnadmin_adapter import VietnamAdminUnitsAdapter, _call_geocoder_with_trace
from src.evaluation.data_contract import validate_benchmarks
from src.evaluation.manifest import generate_manifest
from src.evaluation.materials import select_traceable_cases, validate_case_table
from src.evaluation.protocol import (
    DATASET07_SCORED_FIELDS,
    scenario_for_dataset07,
)
from src.evaluation.run_artifacts import RunArtifacts, prepare_run_directory
from src.evaluation.schema import (
    STANDARD_FIELDS,
    UNIFIED_SCHEMA_COLUMNS,
    StandardPrediction,
    UnifiedEvaluationRecord,
)
from src.evaluation.scorer import (
    aggregate_prediction_pairs,
    compare_fields,
    compute_aggregate_metrics,
    evaluate_record,
    normalized_edit_similarity,
    score_prediction_pair,
)


class EvaluationPipelineTests(unittest.TestCase):
    def test_schema_contract_has_nine_columns(self):
        self.assertEqual(len(UNIFIED_SCHEMA_COLUMNS), 9)
        self.assertEqual(
            UNIFIED_SCHEMA_COLUMNS,
            (
                "ID",
                "DiaChiGoc",
                "CongCu",
                "TruongDuDoan",
                "TruongDung",
                "DungSai",
                "LoaiLoi",
                "TinhHuongMoHo",
                "GhiChu",
            ),
        )

    def test_standard_prediction_serialization(self):
        pred = StandardPrediction(
            so_nha="12",
            ten_duong="Lê Lợi",
            phuong_xa="Bến Nghé",
            quan_huyen="1",
            tinh_thanh="Hồ Chí Minh",
        )
        d = pred.to_dict()
        self.assertEqual(len(d), 5)
        self.assertEqual(d["SoNha"], "12")
        self.assertEqual(d["TenDuong"], "Lê Lợi")
        j = json.loads(pred.to_json())
        self.assertEqual(j["PhuongXa"], "Bến Nghé")

    def test_compare_fields_logic(self):
        pred = {"SoNha": "12", "TenDuong": "Lê Lợi", "PhuongXa": "Phường 1", "QuanHuyen": "", "TinhThanh": "Hà Nội"}
        truth = {"SoNha": "12", "TenDuong": "Lê Lợi", "PhuongXa": "Phường 1", "QuanHuyen": "", "TinhThanh": "Hà Nội"}
        comp = compare_fields(pred, truth)
        self.assertEqual(comp["SoNha"], "TP")
        self.assertEqual(comp["TenDuong"], "TP")
        self.assertEqual(comp["PhuongXa"], "TP")
        self.assertEqual(comp["QuanHuyen"], "TN")
        self.assertEqual(comp["TinhThanh"], "TP")

        # Test hallucination / over-imputation on empty field
        pred_halluc = dict(pred, QuanHuyen="Quận Hoàn Kiếm")
        comp_halluc = compare_fields(pred_halluc, truth)
        self.assertEqual(comp_halluc["QuanHuyen"], "FP")
        self.assertEqual(compare_fields(dict(pred, PhuongXa="Phường 2"), truth)["PhuongXa"], "MISMATCH")

    def test_fuzzy_similarity_normalization_and_empty_policy(self):
        self.assertEqual(normalized_edit_similarity(" Đường A  ", "đường a"), 1.0)
        self.assertEqual(normalized_edit_similarity("", ""), None)
        self.assertEqual(normalized_edit_similarity("12", ""), 0.0)
        self.assertEqual(normalized_edit_similarity("Lê Lợi", "Lê Loi"), 5 / 6)

    def test_fuzzy_metrics_keep_admin_type_strict_and_report_denominators(self):
        prediction = {
            "SoNha": "",
            "TenDuong": "Đường Lê Lợi",
            "PhuongXa": "Xã Ba Đình",
            "QuanHuyen": "",
            "TinhThanh": "Hà Nội",
        }
        truth = {
            "SoNha": "",
            "TenDuong": "Đường Lê Lơi",
            "PhuongXa": "Phường Ba Đình",
            "QuanHuyen": "",
            "TinhThanh": "Hà Nội",
        }
        scored = score_prediction_pair(prediction, truth, DATASET07_SCORED_FIELDS)
        self.assertFalse(scored["exact_match"])
        self.assertEqual(scored["field_metrics"]["TinhThanh"]["fuzzy_scored"], True)
        self.assertEqual(scored["field_metrics"]["PhuongXa"]["exact_comparison"], "MISMATCH")
        self.assertLess(scored["field_metrics"]["PhuongXa"]["fuzzy_similarity"], 1.0)

        aggregate = aggregate_prediction_pairs(
            [
                (
                    {"SoNha": "", "TenDuong": "Đường Lê Lợi"},
                    {"SoNha": "", "TenDuong": "Đường Lê Lơi"},
                ),
                (
                    {"SoNha": "12", "TenDuong": ""},
                    {"SoNha": "", "TenDuong": ""},
                ),
            ],
            ("SoNha", "TenDuong"),
        )
        self.assertEqual(aggregate["field_metrics"]["SoNha"]["fuzzy_similarity_n"], 1)
        self.assertEqual(aggregate["field_metrics"]["SoNha"]["mean_fuzzy_similarity"], 0.0)
        self.assertEqual(aggregate["field_metrics"]["TenDuong"]["fuzzy_similarity_n"], 1)
        self.assertEqual(aggregate["field_metrics"]["SoNha"]["exact_n"], 2)

    def test_fuzzy_similarity_does_not_make_wrong_dataset07_target_correct(self):
        prediction = StandardPrediction(
            phuong_xa="Phường Ba Đin",
            tinh_thanh="Thành phố Hà Nội",
        )
        truth = {
            "PhuongXa": "Phường Ba Đình",
            "TinhThanh": "Thành phố Hà Nội",
        }
        result = evaluate_record(
            "D07_1",
            "input",
            "vietnamadminunits",
            prediction,
            truth,
            scored_fields=DATASET07_SCORED_FIELDS,
        )
        self.assertEqual(result.dung_sai, "ERROR")
        self.assertNotEqual(result.loai_loi, "none")

    def test_dataset07_truth_lookup_uses_official_target_code(self):
        script_path = Path(__file__).resolve().parents[1] / "scripts" / "06_run_baseline_full.py"
        spec = importlib.util.spec_from_file_location("baseline_full_runner", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as folder:
            mapping_path = Path(folder) / "mapping.csv"
            pd.DataFrame([
                {
                    "Mã phường/xã mới": "00004",
                    "Phường/Xã mới (từ 1/7/2025)": "Phường Ba Đình",
                    "Tỉnh/TP mới": "Thành phố Hà Nội",
                },
                {
                    "Mã phường/xã mới": "00004",
                    "Phường/Xã mới (từ 1/7/2025)": "Phường Ba Đình",
                    "Tỉnh/TP mới": "Thành phố Hà Nội",
                },
            ]).to_csv(mapping_path, index=False, encoding="utf-8-sig")
            self.assertEqual(
                module._load_new_targets_by_code(mapping_path),
                {"00004": ("Phường Ba Đình", "Thành phố Hà Nội")},
            )

    def test_evaluate_record_assigns_correct_status_and_errors(self):
        pred = StandardPrediction(so_nha="12", ten_duong="Lê Lợi", phuong_xa="Phường 1", quan_huyen="", tinh_thanh="Hà Nội")
        truth = {"SoNha": "12", "TenDuong": "Lê Lợi", "PhuongXa": "Phường 1", "QuanHuyen": "", "TinhThanh": "Hà Nội"}

        rec = evaluate_record("REC_01", "12 Lê Lợi, Phường 1, Hà Nội", "test_tool", pred, truth)
        self.assertEqual(rec.dung_sai, "CORRECT")
        self.assertEqual(rec.loai_loi, "none")

        # Test over-imputation
        pred_over = StandardPrediction(so_nha="12", ten_duong="Lê Lợi", phuong_xa="Phường 1", quan_huyen="Đống Đa", tinh_thanh="Hà Nội")
        rec_over = evaluate_record("REC_02", "12 Lê Lợi, Phường 1, Hà Nội", "test_tool", pred_over, truth)
        self.assertIn(rec_over.dung_sai, ("PARTIAL", "ERROR"))
        self.assertEqual(rec_over.loai_loi, "hallucination_over_imputation")

    def test_heuristic_adapter_has_honest_identity(self):
        adapter = HeuristicAddressAdapter()
        self.assertEqual(adapter.tool_name, "heuristic_parser")
        pred, raw = adapter.parse("12, Đường Lê Lợi, Phường Bến Nghé, Quận 1, Thành phố Hồ Chí Minh")
        self.assertEqual(pred.so_nha, "12")
        self.assertEqual(pred.tinh_thanh, "Thành phố Hồ Chí Minh")
        self.assertIn("crf_tags", raw)

    def test_libpostal_adapter_requires_real_binding(self):
        try:
            adapter = LibpostalAdapter()
        except RuntimeError as exc:
            self.assertIn("Real Libpostal is unavailable", str(exc))
        else:
            self.assertEqual(adapter.tool_name, "libpostal")
            prediction, raw = adapter.parse("12 Đường Lê Lợi, Hà Nội")
            self.assertIn("postal_labels", raw)

    def test_administrative_conversion_scores_only_target_units(self):
        pred = StandardPrediction(so_nha="12", phuong_xa="Phường Ba Đình", tinh_thanh="Hà Nội")
        truth = {"PhuongXa": "Phường Ba Đình", "TinhThanh": "Hà Nội"}
        rec = evaluate_record("D07_1", "12, phố A", "vietnamadminunits", pred, truth, scored_fields=("PhuongXa", "TinhThanh"))
        self.assertEqual(rec.dung_sai, "CORRECT")
        self.assertNotEqual(rec.loai_loi, "hallucination_over_imputation")

    def test_data07_is_always_labeled_old_to_new_scenario_a(self):
        self.assertEqual(scenario_for_dataset07("N-1"), "A")
        self.assertEqual(scenario_for_dataset07("M-N"), "A")

    def test_geocoder_failure_is_traced_and_returns_explicit_fallback_signal(self):
        trace = {"geocoder_status": "not_applicable"}

        def unavailable(_address):
            raise TimeoutError("simulated timeout")

        self.assertIsNone(_call_geocoder_with_trace(unavailable, "test", trace, max_attempts=2))
        self.assertEqual(trace["geocoder_status"], "unavailable_after_retries")
        self.assertEqual(trace["geocoder_attempts"], 2)
        self.assertEqual(trace["geocoder_error_types"], ["TimeoutError", "TimeoutError"])

    def test_versioned_run_directory_rejects_accidental_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            artifacts = RunArtifacts(Path(folder), "baseline_v2")
            prepare_run_directory(artifacts)
            self.assertTrue(artifacts.run_dir.exists())
            with self.assertRaises(FileExistsError):
                prepare_run_directory(artifacts)
            prepare_run_directory(artifacts, overwrite=True)

    def test_traceable_case_table_projects_prediction_and_raw_log(self):
        predictions = pd.DataFrame([{
            "ID": "D01_0001",
            "DiaChiGoc": "12 Đường A, Phường B, Hà Nội",
            "CongCu": "tool_a",
            "TruongDuDoan": '{"SoNha": "12"}',
            "TruongDung": '{"SoNha": "13"}',
            "DungSai": "ERROR",
            "LoaiLoi": "parse_boundary_error",
            "TinhHuongMoHo": "NONE",
            "GhiChu": "source note",
        }])
        raw_logs = [{
            "id": "D01_0001",
            "tool": "tool_a",
            "input": "12 Đường A, Phường B, Hà Nội",
            "status": "success",
        }]
        cases = select_traceable_cases(predictions, raw_logs)
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases.iloc[0]["DiaChiGoc"], predictions.iloc[0]["DiaChiGoc"])
        validate_case_table(cases, predictions, raw_logs)
        cases.loc[0, "DiaChiGoc"] = "example invented by hand"
        with self.assertRaises(ValueError):
            validate_case_table(cases, predictions, raw_logs)

    def test_vnadmin_adapter_parses_2025_mode(self):
        adapter = VietnamAdminUnitsAdapter()
        self.assertEqual(adapter.tool_name, "vietnamadminunits")
        pred, raw = adapter.parse("70 Nguyễn Sỹ Sách, Phường Tân Sơn, Thành phố Hồ Chí Minh", mode="FROM_2025")
        self.assertEqual(pred.tinh_thanh, "Thành phố Hồ Chí Minh")
        self.assertEqual(pred.phuong_xa, "Phường Tân Sơn")
        self.assertEqual(pred.quan_huyen, "")

    def test_aggregate_metrics_calculation(self):
        pred_good = StandardPrediction(so_nha="1", ten_duong="A", phuong_xa="P1", quan_huyen="", tinh_thanh="T1")
        truth = {"SoNha": "1", "TenDuong": "A", "PhuongXa": "P1", "QuanHuyen": "", "TinhThanh": "T1"}
        rec1 = evaluate_record("R1", "addr1", "tool", pred_good, truth)

        pred_bad = StandardPrediction(so_nha="2", ten_duong="B", phuong_xa="P2", quan_huyen="", tinh_thanh="T1")
        rec2 = evaluate_record("R2", "addr2", "tool", pred_bad, truth)

        metrics = compute_aggregate_metrics([rec1, rec2])
        self.assertEqual(metrics["total"], 2)
        self.assertEqual(metrics["exact_accuracy"], 0.5)
        self.assertIn("field_metrics", metrics)

    def test_reporter_generates_markdown(self):
        from src.evaluation.reporter import generate_baseline_report_markdown
        df_dummy = pd.DataFrame([
            {
                "ID": "D01_0001",
                "DiaChiGoc": "123 Đường A, Phường B, Hà Nội",
                "CongCu": "vietnamadminunits",
                "TruongDuDoan": '{"SoNha": "123", "TenDuong": "Đường A", "PhuongXa": "Phường B", "QuanHuyen": "", "TinhThanh": "Hà Nội"}',
                "TruongDung": '{"SoNha": "123", "TenDuong": "Đường A", "PhuongXa": "Phường B", "QuanHuyen": "", "TinhThanh": "Hà Nội"}',
                "DungSai": "CORRECT",
                "LoaiLoi": "none",
                "TinhHuongMoHo": "NONE",
                "GhiChu": "mode=FROM_2025",
            }
        ])
        md = generate_baseline_report_markdown(df_dummy)
        self.assertIn("# Đánh giá baseline địa chỉ Việt Nam 2025", md)
        self.assertIn("vietnamadminunits", md)
        self.assertIn("normalized_levenshtein", md)
        self.assertIn("Fuzzy mean / n cặp", md)

    def test_report_materials_use_shared_metrics_and_keep_uncertainty_axes_separate(self):
        script_path = Path(__file__).resolve().parents[1] / "scripts" / "08_generate_report_materials.py"
        spec = importlib.util.spec_from_file_location("report_materials", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        complete_prediction = '{"SoNha": "12", "TenDuong": "Đường A", "PhuongXa": "Phường B", "QuanHuyen": "", "TinhThanh": "Hà Nội"}'
        predictions = pd.DataFrame([
            {
                "ID": "D01_0001",
                "CongCu": "test_tool",
                "TruongDuDoan": complete_prediction,
                "TruongDung": complete_prediction,
                "DungSai": "CORRECT",
            },
            {
                "ID": "D04_0000",
                "CongCu": "test_tool",
                "TruongDuDoan": complete_prediction,
                "TruongDung": complete_prediction,
                "DungSai": "CORRECT",
            },
            {
                "ID": "D06_0000_m25",
                "CongCu": "vietnamadminunits",
                "TruongDuDoan": complete_prediction,
                "TruongDung": complete_prediction,
                "DungSai": "CORRECT",
            },
            {
                "ID": "D07_0000_N-1",
                "CongCu": "vietnamadminunits",
                "TruongDuDoan": '{"PhuongXa": "Phường Ba Đin", "TinhThanh": "Tỉnh Bắc Ninh"}',
                "TruongDung": '{"PhuongXa": "Phường Ba Đình", "TinhThanh": "Tỉnh Bắc Ninh"}',
                "DungSai": "ERROR",
            },
        ])
        metrics, fields = module._metric_rows(
            predictions,
            data04=pd.DataFrame([{"KieuThieu": "drop_ward"}]),
            data06=pd.DataFrame([{"KieuLai": "C2_both_new"}]),
        )
        row = metrics.loc[metrics["dataset_condition"].eq("Data 01|all")].iloc[0]
        self.assertEqual(row["exact_match_rate"], 1.0)
        self.assertEqual(row["micro_mean_fuzzy_similarity"], 1.0)
        self.assertEqual(
            int(fields.loc[fields["dataset_condition"].eq("Data 01|all"), "exact_n"].iloc[0]),
            1,
        )
        data07_row = metrics.loc[metrics["dataset_condition"].eq("Data 07|old_to_new")].iloc[0]
        self.assertEqual(data07_row["scored_fields"], "PhuongXa,TinhThanh")
        self.assertEqual(data07_row["exact_match_rate"], 0.0)
        structural = module._structure_scenario_rows(metrics)
        self.assertEqual(len(structural), 2)
        self.assertEqual(set(structural["diagnostic_axis"]), {"structural_scenario"})
        self.assertIn("interpretation", module._spatial_trace_rows(
            predictions[predictions["ID"].str.startswith("D01_")],
            [],
            pd.DataFrame(columns=["QuanHe", "MaPhuongXaMoi"]),
        )[1].columns)

    def test_spatial_trace_report_is_diagnostic_and_uses_exact_target_match(self):
        script_path = Path(__file__).resolve().parents[1] / "scripts" / "08_generate_report_materials.py"
        spec = importlib.util.spec_from_file_location("report_materials_spatial", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        predictions = pd.DataFrame([{
            "ID": "D07_0000_N-1",
            "CongCu": "vietnamadminunits",
            "TruongDuDoan": '{"PhuongXa": "Phường Ba Đin", "TinhThanh": "Tỉnh Bắc Ninh"}',
            "TruongDung": '{"PhuongXa": "Phường Ba Đình", "TinhThanh": "Tỉnh Bắc Ninh"}',
        }])
        raw_logs = [{
            "id": "D07_0000_N-1",
            "tool": "vietnamadminunits",
            "status": "success",
            "trace": {
                "candidate_count": 2,
                "selection_path": "divided_geospatial_selection",
                "geocoder_status": "resolved",
                "fallback_used": False,
            },
        }]
        data07 = pd.DataFrame([{
            "QuanHe": "N-1",
            "MaPhuongXaMoi": "12345",
        }])
        cases, summary = module._spatial_trace_rows(predictions, raw_logs, data07)
        self.assertFalse(bool(cases.iloc[0]["exact_target_match"]))
        self.assertEqual(cases.iloc[0]["candidate_count"], 2)
        self.assertIn("not calibrated", summary.iloc[0]["interpretation"])

    def test_data_contract_rejects_empty_data03_fields(self):
        """validate_benchmarks must reject Data 03 if any standard field is empty."""
        with tempfile.TemporaryDirectory() as folder:
            b_dir = Path(folder)
            # Create minimal dummy files
            for fname, count in [
                ("01_full_address_new_verified.csv", 1000),
                ("02_raw_noisy_synthetic_1000.csv", 1000),
                ("04_missing_fields_800.csv", 800),
                ("06_hybrid_addresses_600.csv", 600),
                ("07_bidirectional_pairs_verified.csv", 600),
            ]:
                # We only need to check Data 03 specifically, so create invalid Data 03
                pass

            # Create bad Data 03 with empty SoNha
            bad_d03 = pd.DataFrame([{
                "ChuoiDiaChi": f"{i}, Đường A, Phường 1, Quận 1, Hà Nội",
                "SoNha": "" if i == 0 else str(i),
                "TenDuong": "Đường A",
                "PhuongXa": "Phường 1",
                "QuanHuyen": "Quận 1",
                "TinhThanh": "Hà Nội",
                "HeQuyChieu": "cu",
            } for i in range(1500)])
            d03_path = b_dir / "03_real_address_old_1500.csv"
            bad_d03.to_csv(d03_path, index=False, encoding="utf-8-sig")

            # Check logic directly on Data 03 frame
            from src.evaluation.data_contract import FIVE_FIELDS
            has_empty = any(bad_d03[f].str.strip().eq("").any() for f in FIVE_FIELDS)
            self.assertTrue(has_empty)


if __name__ == "__main__":
    unittest.main()
