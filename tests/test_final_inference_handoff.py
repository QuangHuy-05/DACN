"""Privacy, literal-input and immutable-package regression for final inference."""
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import runpy
import types
import os
from unittest.mock import patch

from src.modeling.final_inference_handoff import (allowed_inference_member,
    prepare_fivefield_inputs, validate_final_package)
from src.evaluation.dev_runner import file_hash
from src.evaluation.benchmark_runner import BENCHMARKS


class FinalInferenceHandoffTests(unittest.TestCase):
    def test_parent_dispatches_six_workers_without_constructing_a_jvm(self):
        path = Path(__file__).resolve().parents[1] / 'notebooks/sprint03/final_inference_entry.py'
        namespace = runpy.run_path(str(path), run_name='fixture_import')
        scope = namespace['main'].__globals__
        rows = [{'sample_id': str(i), 'text': 'fixture', 'dataset': '01_new', 'source_row': i} for i in range(4800)]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'final_input_only').mkdir()
            (root / 'final_input_only/fivefield_input.manifest.json').write_text(json.dumps({'input_sha256': 'fixture'}))
            output = root / 'output'
            commands = []
            def dispatch(command, check):
                commands.append(command)
                name, track = command[-2:]
                folder = output / (name + ('_test' if track == 'test' else '_5field'))
                folder.mkdir()
                (folder / 'run_manifest.json').write_text(json.dumps({'status_counts': {'ok': 100 if track == 'test' else 4800}}))
            previous = Path.cwd()
            os.chdir(root)
            try:
                with patch.dict(scope, {'file_hash': lambda p: 'fixture', 'read_jsonl': lambda p: rows}), patch(
                    'subprocess.run', side_effect=dispatch), patch.dict(scope, {'preflight_test': lambda *args: None,
                    'build_adapter': lambda *args: self.fail('Parent must not initialize a model/JVM')}):
                    namespace['main'](output)
            finally:
                os.chdir(previous)
            self.assertEqual(6, len(commands))
            self.assertEqual({(m, t) for m in ('pcrf', 'dyn', 'dyn_off') for t in ('test', 'fivefield')},
                             {(c[-2], c[-1]) for c in commands})
            self.assertEqual('NONE', json.loads((output / 'final_inference_report.json').read_text())['gold_access'])

    def test_entry_uses_test_bridge_when_legacy_dev_has_no_shared_primitive(self):
        dev = types.ModuleType('src.evaluation.dev_runner')
        for name in ('build_adapter', 'file_hash', 'load_predictions', 'read_jsonl', 'resource_manifest', 'write_json', 'write_jsonl'):
            setattr(dev, name, lambda *args: None)
        bridge = types.ModuleType('src.evaluation.test_runner')
        primitive = lambda *args: None
        for name in ('preflight_test', 'run_test_inference', 'run_text_inference'):
            setattr(bridge, name, primitive)
        path = Path(__file__).resolve().parents[1] / 'notebooks/sprint03/final_inference_entry.py'
        with patch.dict('sys.modules', {'src.evaluation.dev_runner': dev, 'src.evaluation.test_runner': bridge}):
            namespace = runpy.run_path(str(path), run_name='fixture_import')
        self.assertIs(primitive, namespace['run_text_inference'])
        original = {'run_id': 'fixture_test', 'adapter_kwargs': {'config': {'run_id': 'inner_test'}}}
        compatible = namespace['fivefield_config'](original)
        self.assertIn('dev', compatible['run_id'])
        self.assertEqual('fixture_test', original['run_id'])
        self.assertEqual(original['adapter_kwargs'], compatible['adapter_kwargs'])

    def test_reject_gold_raw_credentials_and_traversal(self):
        for name in ('../x', '/absolute', 'C:/x', 'data/raw/x', 'x/test_gold_v1/y',
                     'test_benchmark_t0.jsonl', 'x/exports/raw.json', 'kaggle.json', 'data/processed/benchmark/01.csv'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                allowed_inference_member(name)
        self.assertTrue(allowed_inference_member('final_input_only/test_input.jsonl'))

    def test_strip_gold_and_exclude_all_100_before_upload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / 'data/processed/benchmark'; folder.mkdir(parents=True)
            samples = []
            for dataset, filename in BENCHMARKS.items():
                with (folder / filename).open('w', encoding='utf-8-sig', newline='') as stream:
                    writer = csv.DictWriter(stream, fieldnames=['ChuoiDiaChi', 'GT_QuanHuyen', 'HeQuyChieu'])
                    writer.writeheader()
                    for index in range(980):
                        text = f'{dataset} {index} đ'
                        writer.writerow({'ChuoiDiaChi': text, 'GT_QuanHuyen': 'secret', 'HeQuyChieu': 'secret'})
                        if index < 20:
                            samples.append({'source_dataset': dataset, 'source_row': index + 2,
                                'text_sha256': hashlib.sha256(text.encode()).hexdigest()})
            hold = root / 'hold.json'; hold.write_text(json.dumps({'samples': samples}))
            excluded = {key: set(range(20)) for key in BENCHMARKS}
            output = root / 'input.jsonl'
            with patch('src.modeling.final_inference_handoff.ROOT', root), patch(
                    'src.modeling.final_inference_handoff.reserved_rows', return_value=excluded):
                manifest = prepare_fivefield_inputs(output, hold)
            rows = [json.loads(line) for line in output.read_text().splitlines()]
            self.assertEqual(4800, len(rows))
            self.assertTrue(all(set(row) == {'sample_id', 'text', 'dataset', 'source_row'} for row in rows))
            self.assertTrue(all(row['source_row'] >= 20 for row in rows))
            self.assertNotIn('secret', output.read_text())
            self.assertEqual(file_hash(output), manifest['input_sha256'])
            self.assertRaises(FileExistsError, prepare_fivefield_inputs, output, hold)

    def test_modified_or_extra_package_file_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / 'kernel').mkdir()
            metadata = root / 'kernel/kernel-metadata.json'
            metadata.write_text(json.dumps({'is_private': True, 'dataset_sources': ['owner/data']}))
            manifest = {'mode': 'final_inference', 'training': False, 'test100': 'TEXT_ONLY_NO_GOLD',
                'dataset_id': 'owner/data', 'package_files': {'kernel/kernel-metadata.json': file_hash(metadata)}}
            (root / 'handoff_manifest.json').write_text(json.dumps(manifest))
            validate_final_package(root)
            (root / 'extra').write_text('unregistered')
            self.assertRaises(ValueError, validate_final_package, root)
            (root / 'extra').unlink()
            metadata.write_text('{}')
            self.assertRaises(ValueError, validate_final_package, root)

    def test_training_and_public_scope_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'handoff_manifest.json').write_text(json.dumps({'mode': 'full', 'training': True}))
            self.assertRaises(ValueError, validate_final_package, root)


if __name__ == '__main__':
    unittest.main()
