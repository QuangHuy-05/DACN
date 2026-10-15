"""Unit tests for the T0 11-span and T1 address system evaluation pipeline."""

import unittest

from src.evaluation.adapters.heur_jw_adapter import (
    HeuristicJaroWinklerAdapter,
    jaro_similarity,
    jaro_winkler_similarity,
)
from src.evaluation.schema import (
    SPAN11_LABELS,
    CharacterSpan,
    SpanModelOutput,
    StandardPrediction,
)
from src.evaluation.span_scorer import (
    compute_exact_span_metrics,
    evaluate_single_sample_spans,
    validate_span_integrity,
)


class SpanEvaluationTests(unittest.TestCase):
    def test_schema_span11_labels_count_and_content(self):
        self.assertEqual(len(SPAN11_LABELS), 11)
        expected = {
            "SoNha",
            "TenDuong",
            "Ngo/Hem",
            "ToaNha/CanHo",
            "PhuongXa",
            "QuanHuyen",
            "TinhThanh",
            "MocDinhVi",
            "HuongDi",
            "GhiChu",
            "Khac",
        }
        self.assertEqual(set(SPAN11_LABELS), expected)

    def test_character_span_serialization(self):
        span = CharacterSpan(
            start=0,
            end=5,
            label="SoNha",
            text="12/34",
            system="cu",
        )
        d = span.to_dict()
        self.assertEqual(d["start"], 0)
        self.assertEqual(d["end"], 5)
        self.assertEqual(d["label"], "SoNha")
        self.assertEqual(d["text"], "12/34")
        self.assertEqual(d["system"], "cu")

    def test_span_model_output_to_standard_5_fields(self):
        text = "12 Đường Lê Lợi, Phường Bến Nghé, Quận 1, TP Hồ Chí Minh"
        output = SpanModelOutput(
            sample_id="test-01",
            raw_text=text,
            spans=[
                CharacterSpan(start=0, end=2, label="SoNha", text="12"),
                CharacterSpan(start=3, end=15, label="TenDuong", text="Đường Lê Lợi"),
                CharacterSpan(start=17, end=32, label="PhuongXa", text="Phường Bến Nghé"),
                CharacterSpan(start=34, end=40, label="QuanHuyen", text="Quận 1"),
                CharacterSpan(start=42, end=57, label="TinhThanh", text="TP Hồ Chí Minh"),
            ],
            predicted_system="cu",
        )
        pred5 = output.to_standard_5_fields()
        self.assertIsInstance(pred5, StandardPrediction)
        self.assertEqual(pred5.so_nha, "12")
        self.assertEqual(pred5.ten_duong, "Đường Lê Lợi")
        self.assertEqual(pred5.phuong_xa, "Phường Bến Nghé")
        self.assertEqual(pred5.quan_huyen, "Quận 1")
        self.assertEqual(pred5.tinh_thanh, "TP Hồ Chí Minh")

    def test_validate_span_integrity_detects_issues(self):
        text = "123 Đường ABC"
        # 1. Valid span
        valid = [CharacterSpan(start=0, end=3, label="SoNha", text="123")]
        self.assertEqual(validate_span_integrity(valid, text), [])

        # 2. Text mismatch
        mismatch = [CharacterSpan(start=0, end=3, label="SoNha", text="999")]
        issues = validate_span_integrity(mismatch, text)
        self.assertTrue(any("text mismatch" in i for i in issues))

        # 3. Overlapping spans
        overlap = [
            CharacterSpan(start=0, end=4, label="SoNha", text="123 "),
            CharacterSpan(start=3, end=13, label="TenDuong", text=" Đường ABC"),
        ]
        issues = validate_span_integrity(overlap, text)
        self.assertTrue(any("Overlapping spans" in i for i in issues))

        # 4. Out of bounds
        oob = [CharacterSpan(start=0, end=50, label="Khac", text="xxx")]
        issues = validate_span_integrity(oob, text)
        self.assertTrue(any("extends beyond text length" in i for i in issues))

    def test_evaluate_single_sample_exact_and_diagnostics(self):
        gold = [
            CharacterSpan(start=0, end=2, label="SoNha", text="12"),
            CharacterSpan(start=3, end=15, label="TenDuong", text="Đường Lê Lợi"),
            CharacterSpan(start=17, end=32, label="PhuongXa", text="Phường Bến Nghé"),
        ]
        # Pred has:
        # - Exact match for SoNha
        # - Boundary error for TenDuong (starts at 0 instead of 3)
        # - Label error for PhuongXa (same offsets [17, 32), label QuanHuyen)
        # - Spurious span for TinhThanh
        pred = [
            CharacterSpan(start=0, end=2, label="SoNha", text="12"),
            CharacterSpan(start=0, end=15, label="TenDuong", text="12 Đường Lê Lợi"),
            CharacterSpan(start=17, end=32, label="QuanHuyen", text="Phường Bến Nghé"),
            CharacterSpan(start=35, end=45, label="TinhThanh", text="Hồ Chí Minh"),
        ]

        res = evaluate_single_sample_spans(pred, gold)
        self.assertEqual(res["tp_count"], 1)  # Only SoNha
        self.assertEqual(len(res["boundary_errors"]), 1)
        self.assertEqual(res["boundary_errors"][0]["label"], "TenDuong")
        self.assertEqual(len(res["label_errors"]), 1)
        self.assertEqual(res["label_errors"][0]["pred_label"], "QuanHuyen")
        self.assertEqual(res["label_errors"][0]["gold_label"], "PhuongXa")
        self.assertEqual(len(res["spurious_preds"]), 1)

    def test_compute_exact_span_metrics_aggregation(self):
        predictions = [
            SpanModelOutput(
                sample_id="s1",
                raw_text="12 Đường Lê Lợi",
                spans=[
                    CharacterSpan(start=0, end=2, label="SoNha", text="12"),
                    CharacterSpan(start=3, end=15, label="TenDuong", text="Đường Lê Lợi"),
                ],
                predicted_system="cu",
            ),
            SpanModelOutput(
                sample_id="s2",
                raw_text="Xã An Phú",
                spans=[
                    CharacterSpan(start=0, end=9, label="PhuongXa", text="Xã An Phú"),
                    CharacterSpan(start=0, end=2, label="QuanHuyen", text="Xã"),  # Hallucinated QuanHuyen on moi
                ],
                predicted_system="moi",
            ),
        ]
        golds = [
            {
                "sample_id": "s1",
                "text": "12 Đường Lê Lợi",
                "spans": [
                    {"start": 0, "end": 2, "label": "SoNha", "text": "12"},
                    {"start": 3, "end": 15, "label": "TenDuong", "text": "Đường Lê Lợi"},
                ],
                "address_system": "cu",
            },
            {
                "sample_id": "s2",
                "text": "Xã An Phú",
                "spans": [
                    {"start": 0, "end": 9, "label": "PhuongXa", "text": "Xã An Phú"},
                ],
                "address_system": "moi",
            },
        ]

        metrics = compute_exact_span_metrics(predictions, golds)
        t0 = metrics["t0_exact_span"]
        self.assertEqual(t0["micro"]["total_tp"], 3)  # SoNha, TenDuong, PhuongXa
        self.assertEqual(t0["micro"]["total_fp"], 1)  # Extra QuanHuyen
        self.assertEqual(t0["micro"]["total_fn"], 0)
        self.assertEqual(t0["micro"]["recall"], 1.0)
        self.assertAlmostEqual(t0["micro"]["precision"], 3 / 4, places=4)

        t1 = metrics["t1_address_system"]
        self.assertEqual(t1["total_evaluated"], 2)
        self.assertEqual(t1["overall_accuracy"], 1.0)
        self.assertEqual(t1["abstain_count"], 0)

        # Structural consistency check
        struct = metrics["structural_consistency"]
        self.assertEqual(struct["new_system_sample_count"], 1)
        self.assertEqual(struct["quan_huyen_hallucinations_on_new"], 1)
        self.assertEqual(struct["quan_huyen_false_positive_rate_on_new"], 1.0)

    def test_jaro_and_jaro_winkler_metric(self):
        # Exact match
        self.assertEqual(jaro_similarity("abc", "abc"), 1.0)
        self.assertEqual(jaro_winkler_similarity("abc", "abc"), 1.0)

        # Disjoint
        self.assertEqual(jaro_similarity("abc", "xyz"), 0.0)

        # Prefix bonus: "hồ chí minh" vs "hồ chí minh city"
        sim_j = jaro_similarity("hồ chí minh", "hồ chí minh city")
        sim_jw = jaro_winkler_similarity("hồ chí minh", "hồ chí minh city")
        self.assertGreater(sim_jw, sim_j)

    def test_heuristic_jaro_winkler_adapter_parse(self):
        adapter = HeuristicJaroWinklerAdapter()
        addr = "12 Đường Lê Lợi, Phường Bến Nghé, Quận 1, Thành phố Hồ Chí Minh"
        output = adapter.parse_spans(addr, sample_id="test-sample")

        self.assertIsInstance(output, SpanModelOutput)
        self.assertEqual(output.sample_id, "test-sample")
        self.assertFalse(output.abstain)
        self.assertEqual(output.predicted_system, "cu")

        # Check character spans match exact slice of raw string
        for span in output.spans:
            self.assertEqual(addr[span.start : span.end], span.text)

        labels = {s.label for s in output.spans}
        self.assertIn("SoNha", labels)
        self.assertIn("TinhThanh", labels)
        self.assertIn("QuanHuyen", labels)

        # Test 5-field conversion
        pred5, trace = adapter.parse(addr)
        self.assertIsInstance(pred5, StandardPrediction)
        self.assertEqual(pred5.so_nha, "12")
        self.assertIn("Hồ Chí Minh", pred5.tinh_thanh)


if __name__ == "__main__":
    unittest.main()
