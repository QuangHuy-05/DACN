import unittest

from src.evaluation.frozen_error_analysis import span_error_category, field_error_category


class FrozenErrorTaxonomyTests(unittest.TestCase):
    def test_wrong_label_and_boundary_are_distinguished(self):
        self.assertEqual(span_error_category([0, 5, 'TinhThanh'], [[0, 5, 'QuanHuyen']], 'FN'), 'WRONG_LABEL_EXACT_BOUNDARY')
        self.assertEqual(span_error_category([0, 5, 'TenDuong'], [[0, 3, 'TenDuong']], 'FN'), 'BOUNDARY_OR_SPLIT_MERGE')
        self.assertEqual(span_error_category([0, 5, 'TenDuong'], [[3, 6, 'Khac']], 'FN'), 'LABEL_AND_BOUNDARY_OVERLAP')
        self.assertEqual(span_error_category([0, 5, 'TenDuong'], [], 'FN'), 'MISSED_GOLD')
        self.assertEqual(span_error_category([0, 5, 'TenDuong'], [], 'FP'), 'EXTRA_PREDICTION')

    def test_field_taxonomy_does_not_assert_ocr_root_cause(self):
        row = {'gold': {'TenDuong': 'Đường A', 'TinhThanh': 'Hà Nội'},
               'prediction': {'TenDuong': 'Hà Nội', 'TinhThanh': 'Hà Nội'}}
        self.assertEqual(field_error_category(row, 'TenDuong', 'MISMATCH'), 'POSSIBLE_CROSS_FIELD_CONFUSION')
        row['prediction']['TenDuong'] = 'Đường'
        self.assertEqual(field_error_category(row, 'TenDuong', 'MISMATCH'), 'PARTIAL_FIELD_OR_BOUNDARY')
        row['prediction']['TenDuong'] = 'Duong AB'
        self.assertEqual(field_error_category(row, 'TenDuong', 'MISMATCH'), 'VALUE_MISMATCH_CAUSE_NOT_DETERMINED')
