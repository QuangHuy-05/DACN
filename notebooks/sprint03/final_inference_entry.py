"""Run inside the restored source snapshot. Gold never exists in this job."""
from collections import Counter
import gc
import json
from pathlib import Path
import sys
import subprocess

from src.evaluation.dev_runner import (build_adapter, file_hash, load_predictions, read_jsonl,
    resource_manifest, write_json, write_jsonl)
from src.evaluation.test_runner import preflight_test, run_test_inference, run_text_inference


def fivefield_config(config):
    # Legacy dev adapter construction requires a development run ID. This
    # changes orchestration identity only, keeping the selected model intact.
    value = json.loads(json.dumps(config))
    value['run_id'] = config['run_id'] + '_dev_5field'
    return value


def main(output, worker_model=None, worker_track=None):
    output = Path(output)
    if worker_model is None:
        output.mkdir(parents=True, exist_ok=False)
    elif not output.is_dir():
        raise ValueError('WORKER_OUTPUT_PARENT_MISSING')
    input_path = Path('final_input_only/test_input.jsonl')
    manifest_path = Path('final_input_only/manifest.json')
    field_path = Path('final_input_only/fivefield_input.jsonl')
    field_manifest = json.loads(field_path.with_suffix('.manifest.json').read_text())
    if file_hash(field_path) != field_manifest['input_sha256']:
        raise ValueError('FIVEFIELD_INPUT_CHANGED')
    fields = read_jsonl(field_path)
    if len(fields) != 4800 or any(set(row) != {'sample_id', 'text', 'dataset', 'source_row'} for row in fields):
        raise ValueError('TEXT_ONLY_FIVEFIELD_CONTRACT')
    jobs = [('pcrf', 'pcrf_model_config.json', 'pcrf_selection_lock.json'),
            ('dyn', 'dyn_model_config.json', 'dyn_selection_lock.json'),
            ('dyn_off', 'dyn_no_constraint_model_config_v2.json', 'dyn_no_constraint_selection_lock_v2.json')]
    for _, config, lock in jobs:
        preflight_test(input_path, manifest_path, Path('final_neural_selection_v1') / config,
                       Path('final_neural_selection_v1') / lock)
    results = {}
    for name, config_name, lock_name in jobs:
        if worker_model is None:
            # py-vncorenlp sets JVM options during construction. A second
            # adapter in the same interpreter cannot reconfigure that JVM.
            for track in ('test', 'fivefield'):
                subprocess.run([sys.executable, __file__, str(output), name, track], check=True)
            results[name] = {track: json.loads((output / (name + suffix) / 'run_manifest.json').read_text())['status_counts']
                for track, suffix in [('test', '_test'), ('fivefield', '_5field')]}
            print(json.dumps({'completed': name, **results[name]}), flush=True)
            continue
        if name != worker_model:
            continue
        config_path = Path('final_neural_selection_v1') / config_name
        config = json.loads(config_path.read_text())
        if worker_track == 'test':
            run = run_test_inference(input_path, manifest_path, config_path,
                 Path('final_neural_selection_v1') / lock_name, output / (name + '_test'))
            if run['sample_count'] != 100:
                raise ValueError('TEST_ID_COUNT')
            return
        if worker_track != 'fivefield':
            raise ValueError('UNKNOWN_WORKER_TRACK')
        # Same selected adapter/projection; only text reaches the parser.
        field_config = fivefield_config(config)
        adapter = build_adapter(field_config)
        field_output = output / (name + '_5field_raw')
        raw_run = run_text_inference(adapter, [{'sample_id': r['sample_id'], 'text': r['text']} for r in fields],
            field_config, field_output, {'fivefield_input_sha256': file_hash(field_path)}, split='dev', track='T0_T1_DEV')
        predictions = load_predictions(field_output / 'predictions.jsonl')
        final_dir = output / (name + '_5field')
        final_dir.mkdir()
        write_json(final_dir / 'model_config.json', field_config)
        write_jsonl(final_dir / 'predictions.jsonl', [{**p.to_dict(), 'dataset': r['dataset'],
            'source_row': r['source_row'], 'fields': p.to_standard_5_fields().to_dict()} for p, r in zip(predictions, fields)])
        run5 = {**raw_run, 'track': 'FIVE_FIELDS_DEVELOPMENT', 'mode': 'TEXT_ONLY',
            'datasets': field_manifest['datasets'], 'hold_identity_sha256': field_manifest['hold_identity_sha256'],
            'projection_version': 'literal_span_to_five_fields_v1',
            'input_permission': 'Only text reaches adapter; input identity metadata attached afterwards',
            'output_sha256': {n: file_hash(final_dir / n) for n in ('predictions.jsonl', 'model_config.json')}}
        write_json(final_dir / 'run_manifest.json', run5)
        del adapter
        gc.collect()
        import torch
        torch.cuda.empty_cache()
        return
    receipt = {'status': 'TEST_AND_FIVEFIELD_PREDICTIONS_FROZEN', 'training_performed': False,
        'gold_access': 'NONE', 'models': results,
        'files': {p.relative_to(output).as_posix(): file_hash(p) for p in output.rglob('*') if p.is_file()}}
    write_json(output / 'final_inference_report.json', receipt)


if __name__ == '__main__':
    main(sys.argv[1], *(sys.argv[2:]))
