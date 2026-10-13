"""Separate private final inference package; training upload guards stay intact."""
import csv
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import zipfile

from src.evaluation.dev_runner import ROOT, file_hash, write_json, write_jsonl
from src.evaluation.benchmark_runner import BENCHMARKS, reserved_rows


def allowed_inference_member(name):
    path = PurePosixPath(name)
    if not name or '\\' in name or ':' in name or path.is_absolute() or '..' in path.parts:
        raise ValueError('UNSAFE_INFERENCE_MEMBER')
    forbidden = ('exports/', 'test_gold', 'test_benchmark_t0', 'kaggle.json', '.venv', '__pycache__',
                 'data/raw/', 'data/processed/benchmark/', 'data/interim/annotation/')
    if any(value in name for value in forbidden):
        raise ValueError('GOLD_RAW_OR_CREDENTIAL_IN_INFERENCE_PACKAGE:' + name)
    return True


def prepare_fivefield_inputs(output, hold_path):
    """Discard GT/strata before packaging; retain only row identities and literal text."""
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    excluded = reserved_rows(hold_path)
    hold = json.loads(Path(hold_path).read_text())
    hashes = {(s['source_dataset'], int(s['source_row']) - 2): s['text_sha256'] for s in hold['samples']}
    records, datasets = [], {}
    for dataset, filename in BENCHMARKS.items():
        path = ROOT / 'data/processed/benchmark' / filename
        count = 0
        with path.open(encoding='utf-8-sig', newline='') as stream:
            for index, row in enumerate(csv.DictReader(stream)):
                count += 1
                text = row['ChuoiDiaChi']
                if index in excluded[dataset]:
                    if hashlib.sha256(text.encode()).hexdigest() != hashes[(dataset, index)]:
                        raise ValueError('HOLD_IDENTITY_CHANGED')
                    continue
                records.append({'sample_id': f'D{dataset[:2]}_{index}', 'text': text,
                                'dataset': dataset, 'source_row': index})
        datasets[dataset] = {'file': filename, 'sha256': file_hash(path), 'source_rows': count,
            'evaluated_rows': count - len(excluded[dataset]), 'excluded_test_rows': sorted(excluded[dataset])}
    if len(records) != 4800:
        raise ValueError('UNEXPECTED_FIVEFIELD_COUNT')
    write_jsonl(output, records)
    manifest = {'sample_count': len(records), 'datasets': datasets,
        'hold_identity_sha256': file_hash(Path(hold_path)), 'input_sha256': file_hash(output),
        'fields': ['sample_id', 'text', 'dataset', 'source_row'],
        'adapter_input': 'text only; identities attached by runner', 'gold': 'NOT_INCLUDED'}
    write_json(output.with_suffix('.manifest.json'), manifest)
    return manifest


def build_final_package(workspace, output, username, run_id, fivefield_input, fivefield_manifest):
    workspace, output = Path(workspace), Path(output)
    if output.exists():
        raise FileExistsError(output)
    files = {}
    def add(relative, source=None):
        allowed_inference_member(relative)
        source = Path(source) if source else workspace / relative
        if not source.is_file():
            raise FileNotFoundError(source)
        files[relative] = source
    pairs = [('pcrf_model_config.json', 'pcrf_selection_lock.json'),
             ('dyn_model_config.json', 'dyn_selection_lock.json'),
             ('dyn_no_constraint_model_config_v2.json', 'dyn_no_constraint_selection_lock_v2.json')]
    for config_name, lock_name in pairs:
        base = 'final_neural_selection_v1/'
        add(base + config_name)
        add(base + lock_name)
        config = json.loads(files[base + config_name].read_text())
        lock = json.loads(files[base + lock_name].read_text())
        for name, entry in config['resources'].items():
            add(entry['path'])
        for name in (*lock['dev_evidence'], *lock['code_sha256']):
            add(name)
        resource_path = config['adapter_kwargs']['resource_lock_path']
        resource = json.loads((workspace / resource_path).read_text())
        for entry in resource['components'].values():
            for name in entry['files']:
                add(entry['path'] + '/' + name)
        java = resource['java']['path']
        for path in (workspace / java).rglob('*'):
            if path.is_file():
                add(path.relative_to(workspace).as_posix())
    # Include the exact submitted package layout, without overwriting its source.
    for directory in ('src', 'scripts', 'configs'):
        for path in (workspace / directory).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix in {'.py', '.json', '.txt'}:
                add(path.relative_to(workspace).as_posix())
    for name in ('final_input_only/test_input.jsonl', 'final_input_only/manifest.json'):
        add(name)
    add('final_input_only/fivefield_input.jsonl', fivefield_input)
    add('final_input_only/fivefield_input.manifest.json', fivefield_manifest)
    add('final_inference_entry.py', ROOT / 'notebooks/sprint03/final_inference_entry.py')
    output.mkdir(parents=True)
    dataset, kernel = output / 'dataset', output / 'kernel'
    dataset.mkdir(); kernel.mkdir()
    manifest = {'scope': 'FINAL_INFERENCE_ONLY_NO_GOLD100_NO_TRAINING',
                'files': {name: file_hash(path) for name, path in files.items()}}
    raw = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
    archive = dataset / 'dacn_final_inference.bundle'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as stream:
        for name, source in sorted(files.items()):
            stream.write(source, name)
        stream.writestr('final_input_bundle_manifest.json', raw)
    identity = {'bundle_sha256': file_hash(archive), 'bundle_manifest_sha256': hashlib.sha256(raw).hexdigest(),
                'test_input_sha256': manifest['files']['final_input_only/test_input.jsonl'],
                'fivefield_input_sha256': manifest['files']['final_input_only/fivefield_input.jsonl']}
    job = {'run_id': run_id, 'identity': identity, 'mode': 'final_inference',
           'archives': {archive.name: {'sha256': identity['bundle_sha256'],
                       'manifest': 'final_input_bundle_manifest.json', 'manifest_sha256': identity['bundle_manifest_sha256']}}}
    template = (ROOT / 'notebooks/sprint03/kaggle_entry.py').read_text()
    template = template.replace('__JOB_CONFIG_JSON__', repr(json.dumps(job)))
    template = template.replace('"test100": "NOT_INCLUDED_NOT_READ"', '"test100": "TEXT_ONLY_NO_GOLD"')
    start = template.index('    output = WORKSPACE / "data/interim/modeling/sprint03" / JOB["run_id"]')
    end = template.index('\n\ntry:\n    main()', start)
    template = template[:start] + '''    output = WORKSPACE / "data/interim/modeling/sprint03" / JOB["run_id"]
    run([python, "final_inference_entry.py", str(output)], SAVED / "remote_run.log")
    STATUS["backup_bytes"] = backup(final=True)
    report = json.loads((output / "final_inference_report.json").read_text())
    if report["status"] != "TEST_AND_FIVEFIELD_PREDICTIONS_FROZEN":
        raise ValueError("FINAL_INFERENCE_NOT_ACCEPTED")
    STATUS.update(status=report["status"], full_training_performed=False)
''' + template[end:]
    # Persist only fresh prediction outputs, never the mounted selected weights/dev evidence.
    template = template.replace('("data/interim/modeling/sprint03/" + JOB["run_id"], "data/processed/evaluation/sprint03")',
                                '("data/interim/modeling/sprint03/" + JOB["run_id"],)')
    (kernel / 'kaggle_final_entry.py').write_text(template, encoding='utf-8')
    dataset_id = f'{username}/{run_id}-input'
    write_json(dataset / 'dataset-metadata.json', {'title': (run_id + ' private final inference')[:50], 'id': dataset_id,
        'licenses': [{'name': 'other'}], 'description': 'Private authorized text-only evaluation. No test gold, GT, raw exports or credentials. Existing model/resource notices preserved.'})
    write_json(kernel / 'kernel-metadata.json', {'id': f'{username}/{run_id}', 'title': run_id,
        'code_file': 'kaggle_final_entry.py', 'language': 'python', 'kernel_type': 'script', 'is_private': True,
        'enable_gpu': True, 'enable_internet': True, 'machine_shape': 'NvidiaTeslaT4',
        'dataset_sources': [dataset_id], 'competition_sources': [], 'kernel_sources': []})
    result = {'run_id': run_id, 'identity': identity, 'mode': 'final_inference', 'kernel_id': f'{username}/{run_id}',
        'dataset_id': dataset_id, 'training': False, 'test100': 'TEXT_ONLY_NO_GOLD',
        'package_files': {p.relative_to(output).as_posix(): file_hash(p) for p in output.rglob('*') if p.is_file()},
        'upload_bytes': sum(p.stat().st_size for p in dataset.iterdir() if p.is_file())}
    write_json(output / 'handoff_manifest.json', result)
    validate_final_package(output)
    return result


def validate_final_package(directory):
    directory = Path(directory)
    result = json.loads((directory / 'handoff_manifest.json').read_text())
    if result.get('mode') != 'final_inference' or result.get('training') is not False or result.get('test100') != 'TEXT_ONLY_NO_GOLD':
        raise ValueError('FINAL_INFERENCE_SCOPE_MISMATCH')
    for name, digest in result['package_files'].items():
        path = (directory / name).resolve()
        if not path.is_relative_to(directory.resolve()) or file_hash(path) != digest:
            raise ValueError('FINAL_PACKAGE_CHANGED')
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()}
    if actual != set(result['package_files']) | {'handoff_manifest.json'}:
        raise ValueError('UNDECLARED_FINAL_PACKAGE_FILE')
    metadata = json.loads((directory / 'kernel/kernel-metadata.json').read_text())
    if metadata['is_private'] is not True or metadata['dataset_sources'] != [result['dataset_id']]:
        raise ValueError('PRIVATE_FINAL_SCOPE_REQUIRED')
    return result
