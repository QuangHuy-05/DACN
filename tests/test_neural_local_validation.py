"""Pure QA tests; actual pretrained evidence is emitted by script37 separately."""
from importlib import import_module
import unittest

from src.modeling.alignment import align_text

audit_gold_alignment = import_module("scripts.37_verify_local_neural_integration").audit_gold_alignment


class LocalNeuralGoldQATests(unittest.TestCase):
    def test_gold_attached_after_alignment_keeps_t0_with_t1_mask(self):
        alignment = align_text("12 Hà Nội")
        before = alignment.to_dict()
        row = {"sample_id": "fixture_excluded", "text": "12 Hà Nội", "address_system": "moi",
               "spans": [{"start": 0, "end": 2, "label": "SoNha"}, {"start": 3, "end": 9, "label": "TinhThanh"}]}
        result = audit_gold_alignment(alignment, row, {"evaluation_exclusions": {"t1": ["fixture_excluded"]}})
        self.assertEqual(result["gold_span_count"], 2)
        self.assertFalse(result["t1_mask"])
        self.assertEqual(before, alignment.to_dict())

    def test_cross_token_boundary_is_rejected_without_gold_repair(self):
        alignment = align_text("Hà Nội")
        row = {"sample_id": "fixture", "text": "Hà Nội", "address_system": None,
               "spans": [{"start": 1, "end": 2, "label": "TinhThanh"}]}
        with self.assertRaisesRegex(ValueError, "UNREPRESENTABLE_GOLD_BOUNDARY"):
            audit_gold_alignment(alignment, row, {"evaluation_exclusions": {"t1": []}})
        self.assertEqual(row["spans"][0]["start"], 1)
