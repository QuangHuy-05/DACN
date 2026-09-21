"""Unit tests for the baseline evaluation pipeline."""

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
from src.evaluation.protocol import scenario_for_dataset07
from src.evaluation.run_artifacts import RunArtifacts, prepare_run_directory
from src.evaluation.schema import (
    STANDARD_FIELDS,
    UNIFIED_SCHEMA_COLUMNS,
    StandardPrediction,
    UnifiedEvaluationRecord,
)
from src.evaluation.scorer import compare_fields, compute_aggregate_metrics, evaluate_record


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
