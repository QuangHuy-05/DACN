import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import csv
from importlib import import_module

from src.evaluation.dev_runner import file_hash, write_json, write_jsonl
from src.evaluation.schema import SpanModelOutput
from src.evaluation.final_results import freeze_ready_predictions, assert_freeze_receipt, paired_ablation, score_overlap_subsets


class FinalResultsTests(unittest.TestCase):
    def test_paired_delta_keeps_negative_result_and_does_not_change_metrics(self):
        derive = import_module('scripts.62_score_final_evaluation').paired_metric_deltas
        def metric(f1, district, accuracy, abstain):
            return {'test_t0_micro': {'f1': f1},
                    'test_structural': {'quan_huyen_hallucinations_on_new': district},
                    'test_t1': {'overall_accuracy': accuracy, 'abstain_count': abstain}}
        on, off = metric(.7, 2, .5, 3), metric(.8, 1, .5, 3)
        before = json.dumps([on, off], sort_keys=True)
        delta = derive(on, off)
        self.assertEqual(-.1, delta['test_t0_micro_f1_on_minus_off'])
        self.assertEqual(1, delta['test_district_fp_on_minus_off'])
        self.assertEqual(0, delta['test_t1_accuracy_on_minus_off'])
        self.assertEqual(0, delta['test_t1_abstain_on_minus_off'])
        self.assertEqual(before, json.dumps([on, off], sort_keys=True))

    def test_scorer_requires_original_roster_and_same_frozen_run_paths(self):
        checker = import_module('scripts.62_score_final_evaluation').validate_evaluation_bindings
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            roster_path, freeze_path = root / 'roster.json', root / 'freeze.json'
            write_json(roster_path, {'CRF-INDEP': {'status': 'READY', 'run_dir': str(root / 'run')}})
            write_json(freeze_path, {'roster_sha256': file_hash(roster_path)})
            receipt = {'models': {'CRF-INDEP': {'run_dir': str(root / 'run')}}}
            checker(roster_path, freeze_path, receipt)
            self.assertRaises(ValueError, checker, roster_path, freeze_path, {'models': {}})
            receipt['models']['CRF-INDEP']['run_dir'] = str(root / 'different')
            self.assertRaises(ValueError, checker, roster_path, freeze_path, receipt)
            roster_path.write_text('{}')
            self.assertRaises(ValueError, checker, roster_path, freeze_path, receipt)

    def test_global_freeze_requires_all_predictions_and_no_early_score(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            rows = [{'sample_id': str(i), 'text': 'Địa chỉ'} for i in range(100)]
            write_jsonl(root / 'input.jsonl', rows)
            run = root / 'run'; run.mkdir()
            write_jsonl(run / 'predictions.jsonl', [SpanModelOutput(r['sample_id'], r['text']).to_dict() for r in rows])
            write_json(run / 'run_manifest.json', {'model_id': 'CRF-INDEP', 'experiment_kind': 'final_test',
                'output_sha256': {'predictions.jsonl': file_hash(run / 'predictions.jsonl')}})
            roster = {'CRF-INDEP': {'status': 'READY', 'run_dir': str(run)},
                'DP-ZS-FT': {'status': 'BLOCKED', 'blocker': 'Missing license'}}
            write_json(run / 'metrics.json', {})
            self.assertRaises(ValueError, freeze_ready_predictions, roster, root / 'freeze.json', root / 'input.jsonl')
            (run / 'metrics.json').unlink()
            receipt = freeze_ready_predictions(roster, root / 'freeze.json', root / 'input.jsonl')
            self.assertEqual(100, receipt['models']['CRF-INDEP']['sample_count'])
            assert_freeze_receipt(root / 'freeze.json')
            (run / 'predictions.jsonl').write_text('changed')
            self.assertRaises(ValueError, assert_freeze_receipt, root / 'freeze.json')

    def test_paired_check_rejects_different_weights_and_compares_decisions(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, system in [('on', 'cu'), ('off', 'moi')]:
                directory = root / name; directory.mkdir()
                write_json(directory / 'model_config.json', {'resources': {'checkpoint': {'sha256': 'same'}}})
                write_jsonl(directory / 'predictions.jsonl', [SpanModelOutput('id', 'text', predicted_system=system).to_dict()])
            result = paired_ablation(root / 'on', root / 'off')
            self.assertEqual(1, result['changed_samples'])
            self.assertEqual(0, result['span_changes'])
            write_json(root / 'off/model_config.json', {'resources': {'checkpoint': {'sha256': 'other'}}})
            self.assertRaises(ValueError, paired_ablation, root / 'on', root / 'off')

    def test_overlap_audit_distinguishes_seen_and_unknown_and_common_subsets(self):
        from src.evaluation.benchmark_runner import BENCHMARKS
        from src.evaluation.schema import STANDARD_FIELDS
        normalizer = import_module('scripts.16_prepare_t0_corpus_batch')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); corpus = root / 'corpus'; corpus.mkdir()
            benchmark = root / 'data/processed/benchmark'; benchmark.mkdir(parents=True)
            source = []
            for i in range(4):
                source.append({**{f: '' for f in STANDARD_FIELDS}, 'SoNha': str(i) if i < 3 else '',
                    'TenDuong': 'A' if i < 3 else '', 'ChuoiDiaChi': f'address{i}'})
            for dataset, filename in BENCHMARKS.items():
                with (benchmark / filename).open('w', encoding='utf-8-sig', newline='') as stream:
                    writer = csv.DictWriter(stream, fieldnames=[*STANDARD_FIELDS, 'ChuoiDiaChi'])
                    writer.writeheader()
                    if dataset == '01_new':
                        writer.writerows(source)
            for split, index in [('train', 0), ('dev', 1)]:
                write_jsonl(corpus / (split + '.jsonl'), [{'sample_id': split, 'text': source[index]['ChuoiDiaChi'],
                    'source_group': normalizer.row_group(source[index])}])
            runs = {}
            for model in ('one', 'two'):
                run = root / model; run.mkdir(); runs[model] = run
                write_jsonl(run / 'predictions.jsonl', [{'dataset': '01_new', 'source_row': i,
                    'fields': {f: r[f] for f in STANDARD_FIELDS}} for i, r in enumerate(source)])
            with patch('src.evaluation.final_results.ROOT', root):
                result = score_overlap_subsets(runs, root / 'audit', corpus)
                self.assertEqual({'seen_train': 1, 'seen_dev': 1, 'unseen_registered_site_key': 1, 'UNKNOWN_OVERLAP': 1}, result['counts'])
                write_jsonl(root / 'two/predictions.jsonl', [])
                self.assertRaises(ValueError, score_overlap_subsets, runs, root / 'audit2', corpus)


if __name__ == '__main__':
    unittest.main()
