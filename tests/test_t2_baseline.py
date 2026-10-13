"""Regression tests for the T2 lookup baseline (hand-built graphs plus Data 07 facts)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import socket
import tempfile
import unittest
from unittest import mock

from src.evaluation import t2_lookup as L
from src.evaluation import t2_scorer as S

ROOT = Path(__file__).resolve().parents[1]
GAZETTEER = ROOT / "data/processed/gazetteer/s3_v4_nso_dual_snapshot_release2"
DATA07 = ROOT / "data/processed/benchmark/07_bidirectional_pairs_verified.csv"
DATA01 = ROOT / "data/processed/benchmark/01_full_address_new_verified.csv"
OSM_LATEST = ROOT / "data/interim/osm/osm_latest_clean.csv"
SCRIPT = ROOT / "scripts/66_run_t2_baseline.py"
HAS_REAL_DATA = GAZETTEER.exists() and DATA07.exists()


def edge(old_id, new_id, old_ward, new_ward, row, merge="Hợp nhất toàn bộ", old_district="Quận X",
         old_province="Tỉnh Cũ", new_province="Tỉnh Mới", code=None):
    return L.make_edge(old_id, new_id, old_province, old_district, old_ward, new_province, new_ward,
                       code or new_id, "?", merge, row)


def small_graph() -> list[L.Edge]:
    """C (o1->n1), B (o2,o3->n2), A (o4->n3,n4), M (o5,o6 x n5,n6: complete 2x2)."""
    return [
        edge("o1", "n1", "Phường 1", "Phường N1", 1),
        edge("o2", "n2", "Phường 2", "Phường N2", 2),
        edge("o3", "n2", "Phường 3", "Phường N2", 3),
        edge("o4", "n3", "Phường 4", "Phường N3", 4, merge="Tách — nhập chủ yếu"),
        edge("o4", "n4", "Phường 4", "Phường N4", 5, merge="Tách — nhập chủ yếu"),
        edge("o5", "n5", "Phường 5", "Phường N5", 6, merge="Tách — một phần"),
        edge("o5", "n6", "Phường 5", "Phường N6", 7, merge="Tách — nhập chủ yếu"),
        edge("o6", "n5", "Phường 6", "Phường N5", 8, merge="Tách — một phần"),
        edge("o6", "n6", "Phường 6", "Phường N6", 9, merge="Tách — một phần"),
    ]


def small_table() -> L.T2Table:
    return L.T2Table(small_graph())


class GraphClassificationTests(unittest.TestCase):
    def test_relations_from_degrees(self):
        labels = L.classify_relations(small_graph())
        self.assertEqual(labels[1], "C")          # 1-1
        self.assertEqual(labels[2], "B")          # N-1
        self.assertEqual(labels[3], "B")
        self.assertEqual(labels[4], "A")          # 1-N
        self.assertEqual(labels[5], "A")
        self.assertEqual({labels[r] for r in (6, 7, 8, 9)}, {"M"})  # M-N never folded into A or B

    def test_graph_analysis_counts_and_ceilings(self):
        info = L.graph_analysis(small_table())
        self.assertEqual(info["relation_counts"], {"A": 2, "B": 2, "C": 1, "M": 4})
        self.assertEqual(info["old_units"], 6)
        self.assertEqual(info["new_units"], 6)
        self.assertEqual(info["by_relation"]["A"]["status"], "OK")
        # one fixed pick per old key is right on at most 6 of 9 edges
        self.assertAlmostEqual(info["ceiling_deterministic_pick_old_to_new"], 6 / 9)
        self.assertAlmostEqual(info["ceiling_deterministic_pick_new_to_old"], 6 / 9)

    def test_empty_relation_is_not_evaluable(self):
        info = L.graph_analysis(L.T2Table([edge("o1", "n1", "Phường 1", "Phường N1", 1)]))
        self.assertEqual(info["by_relation"]["A"]["status"], "NOT_EVALUABLE_NO_SUPPORT")


class SelectionRuleTests(unittest.TestCase):
    fields = {"province": "Tỉnh Cũ", "district": "Quận X", "ward": "Phường 5"}

    def test_strict_abstains_on_several_candidates_and_answers_on_one(self):
        table = small_table()
        many = L.resolve_lookup(table, L.STRICT, L.OLD_TO_NEW, "N1", self.fields)
        self.assertEqual((many.status, many.reason, many.warning), ("ABSTAIN", "AMBIGUOUS", True))
        self.assertEqual(len(many.candidates), 2)
        one = L.resolve_lookup(table, L.STRICT, L.OLD_TO_NEW, "N1", dict(self.fields, ward="Phường 2"))
        self.assertEqual((one.status, one.answer.cid), ("ANSWER", "n2"))
        none = L.resolve_lookup(table, L.STRICT, L.OLD_TO_NEW, "N1", dict(self.fields, ward="Phường 99"))
        self.assertEqual((none.status, none.reason, none.warning), ("ABSTAIN", "NO_MATCH", True))

    def test_default_main_prefers_main_part_then_smallest_row(self):
        table = small_table()
        main = L.resolve_lookup(table, L.DEFAULT_MAIN, L.OLD_TO_NEW, "N1", self.fields)
        self.assertEqual(main.answer.cid, "n6")  # 'nhập chủ yếu' beats 'một phần' although n5 has the smaller row
        first = L.resolve_lookup(table, L.DEFAULT_FIRST, L.OLD_TO_NEW, "N1", self.fields)
        self.assertEqual(first.answer.cid, "n5")  # smallest source_row, merge_form ignored
        self.assertFalse(main.warning or first.warning)  # a default pick carries no warning

    def test_default_rules_are_deterministic_under_edge_order(self):
        graph = small_graph()
        reference = {}
        for order in (graph, list(reversed(graph)), graph[3:] + graph[:3]):
            table = L.T2Table(order)
            for system in (L.DEFAULT_MAIN, L.DEFAULT_FIRST):
                answer = L.resolve_lookup(table, system, L.OLD_TO_NEW, "N1", self.fields).answer.cid
                self.assertEqual(reference.setdefault(system, answer), answer)

    def test_merge_form_tie_goes_to_smallest_source_row(self):
        table = L.T2Table([
            edge("o1", "n2", "Phường 1", "Phường N2", 20, merge="Tách — nhập chủ yếu"),
            edge("o1", "n1", "Phường 1", "Phường N1", 10, merge="Tách — nhập chủ yếu"),
        ])
        res = L.resolve_lookup(table, L.DEFAULT_MAIN, L.OLD_TO_NEW, "N1",
                               {"province": "Tỉnh Cũ", "district": "Quận X", "ward": "Phường 1"})
        self.assertEqual(res.answer.cid, "n1")

    def test_new_to_old_fan_in_is_ambiguous_for_strict(self):
        res = L.resolve_lookup(small_table(), L.STRICT, L.NEW_TO_OLD, "N1",
                               {"province": "Tỉnh Mới", "ward": "Phường N2"})
        self.assertEqual((res.reason, len(res.candidates)), ("AMBIGUOUS", 2))

    def test_non_atomic_transition_is_reported_not_guessed(self):
        special = {"source_row": "1", "old_entity_id": "d1", "new_entity_id": "z1", "old_province": "Tỉnh Cũ",
                   "old_district": "Huyện Đảo", "new_province": "Tỉnh Mới", "new_ward": "Đặc khu Đảo",
                   "new_ward_code": "9"}
        table = L.T2Table(small_graph(), [special])
        old = L.resolve_lookup(table, L.STRICT, L.OLD_TO_NEW, "N1",
                               {"province": "Tỉnh Cũ", "district": "Huyện Đảo", "ward": ""})
        self.assertEqual((old.status, old.reason), ("ABSTAIN", "NON_ATOMIC"))
        new = L.resolve_lookup(table, L.DEFAULT_MAIN, L.NEW_TO_OLD, "N1",
                               {"province": "Tỉnh Mới", "ward": "Đặc khu Đảo"})
        self.assertEqual((new.status, new.reason), ("ABSTAIN", "NON_ATOMIC"))

    def test_missing_district_becomes_wildcard_and_is_ambiguous_across_districts(self):
        table = L.T2Table([
            edge("o1", "n1", "Phường 1", "Phường N1", 1, old_district="Quận A"),
            edge("o2", "n2", "Phường 1", "Phường N2", 2, old_district="Quận B"),
        ])
        res = L.resolve_lookup(table, L.STRICT, L.OLD_TO_NEW, "N1", {"province": "Tỉnh Cũ", "district": "", "ward": "Phường 1"})
        self.assertEqual(res.reason, "AMBIGUOUS")
        no_ward = L.resolve_lookup(table, L.STRICT, L.OLD_TO_NEW, "N1", {"province": "Tỉnh Cũ", "district": "Quận A", "ward": ""})
        self.assertEqual(no_ward.reason, "NO_MATCH")


class ScoringTests(unittest.TestCase):
    def _res(self, answer_key, warning=False, status="ANSWER", reason="OK"):
        cand = L.Candidate("new", "x", answer_key, "P", "", "W", "1") if answer_key else None
        return L.Resolution("S", status, reason, [cand] if cand else [], cand, warning)

    def test_silent_error_counts_only_unwarned_wrong_answers(self):
        wrong = S.score_resolution(self._res(("p", "a")), ("p", "b"))
        self.assertTrue(wrong["silent"] and not wrong["correct"])
        right = S.score_resolution(self._res(("p", "b")), ("p", "b"))
        self.assertTrue(right["correct"] and not right["silent"])
        abstain = S.score_resolution(self._res(None, True, "ABSTAIN", "NO_MATCH"), ("p", "b"))
        self.assertFalse(abstain["silent"] or abstain["correct"])
        self.assertTrue(abstain["no_match"])
        warned_wrong = S.score_resolution(self._res(("p", "a"), warning=True), ("p", "b"))
        self.assertFalse(warned_wrong["silent"])
        missing_gold = S.score_resolution(self._res(("p", "a")), None)
        self.assertTrue(missing_gold["silent"] and not missing_gold["gold_in_candidates"])

    def test_cell_metrics_use_all_rows_as_denominator(self):
        def rec(correct, answered, silent, cluster, n_candidates=1, no_match=False):
            return {"correct": correct, "answered": answered, "abstain": not answered, "silent": silent,
                    "reason": "NO_MATCH" if no_match else "", "no_match": no_match, "n_candidates": n_candidates,
                    "gold_in_candidates": correct, "cluster": cluster}
        records = [rec(True, True, False, "u1"), rec(False, True, True, "u1"), rec(False, False, False, "u2", 0, True),
                   rec(True, True, False, "u2")]
        out = S.summarize_cell(records, with_ci=False)
        self.assertEqual((out["n"], out["answered"], out["correct"], out["silent_errors"], out["no_match"]), (4, 3, 2, 1, 1))
        self.assertAlmostEqual(out["accuracy"], 0.5)
        self.assertAlmostEqual(out["accepted_accuracy"], 2 / 3)
        self.assertAlmostEqual(out["silent_error_rate"], 0.25)
        self.assertAlmostEqual(out["macro_accuracy"], 0.5)  # u1: 1/2, u2: 1/2
        self.assertEqual(S.summarize_cell([], with_ci=False)["status"], S.NO_SUPPORT)

    def test_cluster_ci_reports_cluster_count(self):
        records = [{"correct": i % 3 == 0, "answered": True, "abstain": False, "silent": i % 3 != 0, "reason": "",
                    "no_match": False, "n_candidates": 2, "gold_in_candidates": True, "cluster": f"u{i % 5}"}
                   for i in range(50)]
        out = S.summarize_cell(records, with_ci=True, n_resamples=200)
        self.assertEqual(out["n_clusters"], 5)
        self.assertLessEqual(out["accuracy_ci_low"], out["accuracy"] + 1e-9)

    def test_unit_constant_ceiling(self):
        records = [{"cluster": "u1"}, {"cluster": "u1"}, {"cluster": "u1"}, {"cluster": "u2"}]
        keys = [("a",), ("a",), ("b",), ("c",)]
        self.assertAlmostEqual(S.unit_constant_ceiling(records, keys), 3 / 4)

    def test_slices_expose_unsupported_relations_with_zero_support(self):
        records = [{"loai": "B", "hinhthuc": "Hợp nhất toàn bộ"}]
        sizes = {(t, v): len(r) for t, v, r in S.slice_defs(records)}
        self.assertEqual(sizes[("LoaiAnhXa", "A")], 0)
        self.assertEqual(sizes[("LoaiAnhXa", "C")], 0)
        self.assertEqual(sizes[("LoaiAnhXa", "B")], 1)

    def test_address_splitting_is_right_aligned(self):
        old = S.split_address("11, Phố Khúc Hạo, Phường Điện Biên, Quận Ba Đình, Hà Nội", "old")
        self.assertEqual((old["ward"], old["district"], old["province"]), ("Phường Điện Biên", "Quận Ba Đình", "Hà Nội"))
        weird = S.split_address("1, 2, 3, 4, 5, Phường Y, Quận Z, Hà Nội", "old")
        self.assertEqual((weird["ward"], weird["district"], weird["province"]), ("Phường Y", "Quận Z", "Hà Nội"))
        new = S.split_address("12C, Phố Hàng Cót, Phường Hoàn Kiếm, Thành phố Hà Nội", "new")
        self.assertEqual((new["ward"], new["province"], new["district"]), ("Phường Hoàn Kiếm", "Thành phố Hà Nội", ""))
        self.assertEqual(S.house_and_street(old["head"]), ("11", "Phố Khúc Hạo"))
        self.assertEqual(S.house_and_street(["Ngõ 5", "Đường X"]), ("", "Ngõ 5, Đường X"))


class SingleVersionTests(unittest.TestCase):
    def test_name_collision_is_a_silent_error(self):
        # Old "Phường A" (Tỉnh Cũ) feeds new "Phường B"; a different new "Phường A" exists in the same province.
        table = L.T2Table([
            edge("o1", "nB", "Phường A", "Phường B", 1),
            edge("o2", "nA", "Phường C", "Phường A", 2),
        ])
        entities = [
            {"entity_id": "P_old", "level": "province", "system": "cu", "canonical_name": "Tỉnh Cũ", "parent_id": ""},
            {"entity_id": "D_old", "level": "district", "system": "cu", "canonical_name": "Quận X", "parent_id": "P_old"},
            {"entity_id": "o1", "level": "ward", "system": "cu", "canonical_name": "Phường A", "parent_id": "D_old"},
            {"entity_id": "o2", "level": "ward", "system": "cu", "canonical_name": "Phường C", "parent_id": "D_old"},
            {"entity_id": "P_new", "level": "province", "system": "moi", "canonical_name": "Tỉnh Mới", "parent_id": ""},
            {"entity_id": "nB", "level": "ward", "system": "moi", "canonical_name": "Phường B", "parent_id": "P_new"},
            {"entity_id": "nA", "level": "ward", "system": "moi", "canonical_name": "Phường A", "parent_id": "P_new"},
        ]
        index = L.SingleVersionIndex(entities, table)
        res = index.resolve(L.OLD_TO_NEW, "N1", {"province": "Tỉnh Cũ", "district": "Quận X", "ward": "Phường A"})
        self.assertEqual((res.status, res.answer.cid, res.warning), ("ANSWER", "nA", False))
        gold_key = ("mới", "phường b")  # the true target is Phường B
        self.assertTrue(S.score_resolution(res, gold_key)["silent"])
        missing = index.resolve(L.OLD_TO_NEW, "N1", {"province": "Tỉnh Cũ", "district": "Quận X", "ward": "Phường Z"})
        self.assertEqual((missing.status, missing.reason), ("ABSTAIN", "NO_MATCH"))


@unittest.skipUnless(HAS_REAL_DATA, "Data 07 or gazetteer missing")
class Data07FactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = L.T2Table.load(GAZETTEER)
        cls.rows = L.read_csv_rows(DATA07, ("ID_Node", "DiaChi_Cu", "DiaChi_Moi", "LoaiAnhXa"))
        cls.old = [S.split_address(r["DiaChi_Cu"], "old") for r in cls.rows]
        cls.new = [S.split_address(r["DiaChi_Moi"], "new") for r in cls.rows]

    def _matched(self, side, level):
        if side == "old":
            return sum(1 for f in self.old if self.table.old_to_new_candidates(level, f["province"], f["district"], f["ward"])[0])
        return sum(1 for f in self.new if self.table.new_to_old_candidates(level, f["province"], f["ward"])[0])

    def test_normalisation_levels_reproduce_measured_matches(self):
        self.assertEqual(self._matched("old", "N0"), 5)
        self.assertEqual(self._matched("old", "N1"), 535)
        self.assertEqual(self._matched("old", "N2"), 600)  # verified aliases close the remaining 65 rows
        self.assertEqual(self._matched("new", "N0"), 600)

    def test_table_has_expected_graph_shape_and_hash_check(self):
        self.assertEqual(len(self.table.edges), 10597)
        info = L.graph_analysis(self.table)
        self.assertEqual(info["relation_counts"], {"A": 3, "B": 9432, "C": 132, "M": 1030})
        self.assertEqual(info["relation_label_mismatch_vs_file"], 0)
        self.assertEqual(len(self.table.non_atomic), 5)

    def test_data07_has_only_b_and_m(self):
        self.assertEqual({r["LoaiAnhXa"] for r in self.rows}, {"B", "M"})

    def test_candidate_recall_is_structural_at_n2(self):
        for row, old, new in list(zip(self.rows, self.old, self.new))[:60]:
            gold = S.build_pair_gold(self.table, row)
            self.assertTrue(gold.edge_exists)
            res = L.resolve_lookup(self.table, L.DEFAULT_MAIN, L.OLD_TO_NEW, "N2", S.lookup_fields(old))
            self.assertIn(gold.new.key, {c.key for c in res.candidates})


class GeocoderBlockTests(unittest.TestCase):
    def test_no_socket_is_opened_and_symbol_is_restored(self):
        try:
            from vietnamadminunits.converter import converter_2025 as module
        except ImportError:
            self.skipTest("vietnamadminunits not installed in this runtime")
        original = module.get_geo_location

        def forbidden(*args, **kwargs):
            raise AssertionError("a socket was opened")

        with mock.patch.object(socket, "socket", side_effect=forbidden), \
                mock.patch.object(socket, "create_connection", side_effect=forbidden), \
                mock.patch.object(socket, "getaddrinfo", side_effect=forbidden):
            out = L.run_vnadmin(["11, Phố Khúc Hạo, Phường Điện Biên, Quận Ba Đình, Hà Nội"])
        self.assertIs(module.get_geo_location, original)
        self.assertEqual(out[0]["geocoder_status"], "empty")
        self.assertEqual(out[0]["selection_path"], "divided_default_after_geocoder_unavailable")
        self.assertTrue(out[0]["ward"])

    def test_geocoder_stub_is_active_inside_the_context(self):
        try:
            with L.geocoder_disabled() as module:
                self.assertIsNone(module.get_geo_location("any address"))
        except ImportError:
            self.skipTest("vietnamadminunits not installed in this runtime")


class StreetIndexTests(unittest.TestCase):
    def _rows(self):
        return [
            {"SoNha": "1", "TenDuong": "Đường Lê Lợi", "PhuongXa": "Phường N1", "QuanHuyen": "", "TinhThanh": "Tỉnh Mới",
             "ChuoiDiaChi": "1, Đường Lê Lợi, Phường N1, Tỉnh Mới"},
            {"SoNha": "2", "TenDuong": "Phố Lê Lợi", "PhuongXa": "Phường N1", "QuanHuyen": "", "TinhThanh": "Tỉnh Mới",
             "ChuoiDiaChi": "2, Phố Lê Lợi, Phường N1, Tỉnh Mới"},
            {"SoNha": "3", "TenDuong": "Trần Hưng Đạo", "PhuongXa": "", "QuanHuyen": "Phường N2", "TinhThanh": "Tỉnh Mới",
             "ChuoiDiaChi": "3, Trần Hưng Đạo, Phường N2, Tỉnh Mới"},
            {"SoNha": "4", "TenDuong": "Quang Trung", "PhuongXa": "Phường N1", "QuanHuyen": "Phường N2",
             "TinhThanh": "Tỉnh Mới", "ChuoiDiaChi": "4, Quang Trung, Phường N1, Phường N2, Tỉnh Mới"},
        ]

    def test_street_key_ignores_generic_type_prefix(self):
        self.assertEqual(L.street_key("Đường Lê Lợi"), L.street_key("phố  lê lợi"))
        self.assertNotEqual(L.street_key("Ngõ 5 Lê Lợi"), L.street_key("Lê Lợi"))

    def test_ward_must_be_exactly_one_known_new_ward(self):
        index = L.build_street_index(small_table(), [], self._rows(), set(), None)
        self.assertEqual(index.report["no_unique_new_ward"], 1)  # row 4 has two ward-like values
        self.assertIn(("mới", "phường n2"), index.wards_for("Trần Hưng Đạo"))

    def test_text_and_pair_filters(self):
        table = small_table()
        banned_text = {L.normalize_for_overlap("1, Đường Lê Lợi, Phường N1, Tỉnh Mới")}
        index = L.build_street_index(table, [], self._rows(), banned_text, None)
        self.assertNotIn(banned_text.copy().pop(), index.kept_texts)
        self.assertEqual(index.report["dropped_text_overlap"], 1)
        # strict pair filter: "Phố Lê Lợi" must collide with "Đường Lê Lợi" (same street_key) and house number
        pairs = {(L.normalize_for_overlap("2"), L.street_key("Lê Lợi"))}
        strict = L.build_street_index(table, [], self._rows(), set(), pairs)
        self.assertEqual(strict.report["dropped_pair_overlap"], 1)
        self.assertEqual(strict.report["kept"], 2)

    def test_street_evidence_is_decisive_only_when_it_narrows_to_one(self):
        table = small_table()
        index = L.StreetIndex(by_street={"lê lợi": {("mới", "phường n6")}})
        fields = {"province": "Tỉnh Cũ", "district": "Quận X", "ward": "Phường 5"}
        res = L.resolve_street(table, index, "first", "N1", fields, "Đường Lê Lợi")
        self.assertEqual((res.answer.cid, res.flags["evidence"], res.flags["fallback_used"]), ("n6", "decisive", False))
        none = L.resolve_street(table, L.StreetIndex(), "first", "N1", fields, "Đường Lạ")
        self.assertEqual((none.answer.cid, none.flags["fallback_used"]), ("n5", True))  # falls back to DEFAULT-FIRST
        unique = L.resolve_street(table, index, "first", "N1", dict(fields, ward="Phường 2"), "x")
        self.assertEqual(unique.flags["evidence"], "not_needed")

    @unittest.skipUnless(HAS_REAL_DATA and DATA01.exists() and OSM_LATEST.exists(), "real inputs missing")
    def test_real_index_contains_no_data07_address_string(self):
        table = L.T2Table.load(GAZETTEER)
        rows = L.read_csv_rows(DATA07, ("DiaChi_Cu", "DiaChi_Moi"))
        banned = {L.normalize_for_overlap(r["DiaChi_Moi"]) for r in rows}
        pairs = set()
        for r in rows:
            for kind, column in (("old", "DiaChi_Cu"), ("new", "DiaChi_Moi")):
                house, street = S.house_and_street(S.split_address(r[column], kind)["head"])
                pairs.add((L.normalize_for_overlap(house), L.street_key(street)))
        columns = ("SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh", "ChuoiDiaChi")
        data01, osm = L.read_csv_rows(DATA01, columns), L.read_csv_rows(OSM_LATEST, columns)
        loose = L.build_street_index(table, data01, osm, banned, None)
        strict = L.build_street_index(table, data01, osm, banned, pairs)
        self.assertFalse(loose.kept_texts & banned)
        self.assertFalse(strict.kept_texts & banned)
        self.assertLessEqual(strict.report["kept"], loose.report["kept"])
        self.assertGreater(strict.report["dropped_pair_overlap"], 0)
        kept_pairs = set()
        for source in (data01, osm):
            for r in source:
                if L.normalize_for_overlap(r["ChuoiDiaChi"]) in strict.kept_texts:
                    kept_pairs.add((L.normalize_for_overlap(r["SoNha"]), L.street_key(r["TenDuong"])))
        self.assertFalse(kept_pairs & pairs)


class RunnerTests(unittest.TestCase):
    def test_refuses_to_overwrite_an_existing_output_directory(self):
        spec = importlib.util.spec_from_file_location("t2_runner", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            args = module.argparse.Namespace(out_dir=Path(tmp), resamples=10, skip_pipeline=True, skip_street=True)
            self.assertEqual(module.T2Run(args).execute(), 3)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_script_module_level_imports_are_stdlib_only(self):
        header = SCRIPT.read_text(encoding="utf-8").split("class T2Run", 1)[0]
        for forbidden in ("import numpy", "import pandas", "import pycrfsuite", "import torch"):
            self.assertNotIn(forbidden, header)


if __name__ == "__main__":
    unittest.main()
