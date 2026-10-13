"""Final freeze gates, paired diagnostics and five-field overlap reporting."""
from collections import Counter, defaultdict
import csv
import hashlib
from importlib import import_module
import json
from pathlib import Path

from src.evaluation.dev_runner import ROOT, file_hash, load_predictions, read_jsonl, write_json, write_jsonl


def freeze_ready_predictions(roster, output, expected_input):
    """Gate every READY model before a scorer is allowed to read test gold."""
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    expected = {r['sample_id']: r['text'] for r in read_jsonl(Path(expected_input))}
    if len(expected) != 100:
        raise ValueError('FINAL_INPUT_NOT_100')
    artifacts = {}
    for model, entry in roster.items():
        if entry['status'] != 'READY':
            if not entry.get('blocker'):
                raise ValueError('BLOCKED_MODEL_MISSING_REASON')
            continue
        directory = Path(entry['run_dir'])
        if any((directory / name).exists() for name in ('metrics.json', 'scoring_manifest.json')):
            raise ValueError('SCORING_OCCURRED_BEFORE_ALL_MODELS_FROZEN')
        manifest = json.loads((directory / 'run_manifest.json').read_text())
        if manifest.get('model_id') != model or manifest.get('experiment_kind') != 'final_test':
            raise ValueError('WRONG_MODEL_OR_FIXTURE')
        for name, digest in manifest['output_sha256'].items():
            if file_hash(directory / name) != digest:
                raise ValueError('FROZEN_INFERENCE_CHANGED')
        predictions = load_predictions(directory / 'predictions.jsonl')
        if len(predictions) != 100 or {p.sample_id: p.raw_text for p in predictions} != expected:
            raise ValueError('MISSING_DUPLICATE_OR_CHANGED_TEST_INPUT')
        artifacts[model] = {'run_dir': str(directory), 'predictions_sha256': file_hash(directory / 'predictions.jsonl'),
            'run_manifest_sha256': file_hash(directory / 'run_manifest.json'), 'status_counts': dict(Counter(p.status for p in predictions)),
            'sample_count': len(predictions)}
    if not artifacts:
        raise ValueError('NO_READY_MODELS')
    receipt = {'status': 'ALL_READY_TEST_PREDICTIONS_FROZEN', 'gold_access_before_freeze': 'NONE',
        'models': artifacts, 'blocked_models': {m: e for m, e in roster.items() if e['status'] != 'READY'}}
    write_json(output, receipt)
    return receipt


def assert_freeze_receipt(receipt_path):
    receipt = json.loads(Path(receipt_path).read_text())
    if receipt.get('status') != 'ALL_READY_TEST_PREDICTIONS_FROZEN':
        raise ValueError('GLOBAL_FREEZE_REQUIRED')
    for entry in receipt['models'].values():
        directory = Path(entry['run_dir'])
        if file_hash(directory / 'predictions.jsonl') != entry['predictions_sha256']:
            raise ValueError('PREDICTION_CHANGED_AFTER_GLOBAL_FREEZE')
    return receipt


def paired_ablation(on_dir, off_dir):
    def checkpoint(directory):
        config = json.loads((Path(directory) / 'model_config.json').read_text())
        return config['resources']['checkpoint']['sha256']
    if checkpoint(on_dir) != checkpoint(off_dir):
        raise ValueError('ABLATION_CHECKPOINT_DIFFERS')
    on = {p.sample_id: p for p in load_predictions(Path(on_dir) / 'predictions.jsonl')}
    off = {p.sample_id: p for p in load_predictions(Path(off_dir) / 'predictions.jsonl')}
    if set(on) != set(off):
        raise ValueError('ABLATION_ID_SET_DIFFERS')
    changed = []
    for sid in sorted(on):
        if on[sid].raw_text != off[sid].raw_text:
            raise ValueError('ABLATION_INPUT_DIFFERS')
        keys = lambda p: {(s.start, s.end, s.label) for s in p.spans}
        a, b = keys(on[sid]), keys(off[sid])
        if a != b or on[sid].predicted_system != off[sid].predicted_system:
            changed.append({'sample_id': sid, 'spans_added_by_constraint': sorted(a - b),
                'spans_removed_by_constraint': sorted(b - a), 't1_changed': on[sid].predicted_system != off[sid].predicted_system})
    return {'checkpoint_sha256': checkpoint(on_dir), 'samples': len(on), 'changed_samples': len(changed),
            'span_changes': sum(len(r['spans_added_by_constraint']) + len(r['spans_removed_by_constraint']) for r in changed),
            'changes': changed, 'interpretation': 'No observed improvement from constraints' if not changed else 'Report paired metrics; no retraining or tuning'}


def score_overlap_subsets(run_dirs, output, corpus_dir):
    """Scorer-only source/group audit using the already registered site-key rule."""
    from src.evaluation.scorer import aggregate_prediction_pairs
    from src.evaluation.schema import STANDARD_FIELDS
    from src.evaluation.benchmark_runner import BENCHMARKS
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    corpus_dir = Path(corpus_dir)
    train, dev = read_jsonl(corpus_dir / 'train.jsonl'), read_jsonl(corpus_dir / 'dev.jsonl')
    normalizer = import_module('scripts.16_prepare_t0_corpus_batch')
    train_groups = {r['source_group'] for r in train}
    dev_groups = {r['source_group'] for r in dev}
    train_text = {normalizer.normalize_key(r['text']) for r in train}
    dev_text = {normalizer.normalize_key(r['text']) for r in dev}
    predictions = {name: read_jsonl(Path(path) / 'predictions.jsonl') for name, path in run_dirs.items()}
    identities = [{(r['dataset'], r['source_row']) for r in rows} for rows in predictions.values()]
    if not identities or any(ids != identities[0] for ids in identities):
        raise ValueError('FIVEFIELD_MODELS_DIFFERENT_INPUT_SUBSET')
    groups, gold_by_key, audit = defaultdict(set), {}, []
    for dataset, filename in BENCHMARKS.items():
        with (ROOT / 'data/processed/benchmark' / filename).open(encoding='utf-8-sig', newline='') as stream:
            for index, row in enumerate(csv.DictReader(stream)):
                key = (dataset, index)
                if key not in identities[0]:
                    continue
                group = normalizer.row_group(row)
                norm = normalizer.normalize_key(row['ChuoiDiaChi'])
                # Same registered rule is conservative; empty house/street use surface fallback.
                if group in train_groups or norm in train_text:
                    category = 'seen_train'
                elif group in dev_groups or norm in dev_text:
                    category = 'seen_dev'
                elif (row.get('GT_SoNha') or row.get('SoNha')) and (row.get('GT_TenDuong') or row.get('TenDuong')):
                    category = 'unseen_registered_site_key'
                else:
                    category = 'UNKNOWN_OVERLAP'
                groups[category].add(key)
                audit.append({'dataset': dataset, 'source_row': index, 'group_id': group, 'category': category,
                    'text_sha256': hashlib.sha256(row['ChuoiDiaChi'].encode()).hexdigest()})
                gold_by_key[key] = {f: row['GT_' + f if dataset == '02_noisy' else f] for f in STANDARD_FIELDS}
    if set(gold_by_key) != identities[0]:
        raise ValueError('INCOMPLETE_OVERLAP_AUDIT')
    write_jsonl(output / 'row_overlap.jsonl', audit)
    results = {}
    for name, rows in predictions.items():
        results[name] = {}
        for category, keys in groups.items():
            pairs = [(r['fields'], gold_by_key[(r['dataset'], r['source_row'])]) for r in rows if (r['dataset'], r['source_row']) in keys]
            results[name][category] = aggregate_prediction_pairs(pairs)
    result = {'sample_count': len(audit), 'counts': {k: len(v) for k, v in groups.items()},
        'method': 'Frozen row_group/site_group and normalized text; not geographic identity proof',
        'interpretation': 'Whole track is development/compatibility, not independent test. Unseen registered keys can still have unresolved source/geographic overlap.',
        'group_rule_sha256': file_hash(Path(normalizer.__file__)), 'row_audit_sha256': file_hash(output / 'row_overlap.jsonl'),
        'common_subset_sha256': {k: hashlib.sha256(json.dumps(sorted(v)).encode()).hexdigest() for k, v in groups.items()},
        'models': results}
    write_json(output / 'overlap_metrics.json', result)
    return result
