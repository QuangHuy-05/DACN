"""Taxonomy of frozen error events. Does not run inference or compute new F1."""

from collections import Counter, defaultdict
import json
from pathlib import Path

from src.evaluation.dev_runner import file_hash, write_json, write_jsonl
from src.modeling.datasets import load_corpus


def span_error_category(span, counterparts, error_side):
    start, end, label = span
    if any(start == item[0] and end == item[1] and label != item[2] for item in counterparts):
        return 'WRONG_LABEL_EXACT_BOUNDARY'
    overlaps = [item for item in counterparts if start < item[1] and end > item[0]]
    if any(label == item[2] for item in overlaps):
        return 'BOUNDARY_OR_SPLIT_MERGE'
    if overlaps:
        return 'LABEL_AND_BOUNDARY_OVERLAP'
    return 'MISSED_GOLD' if error_side == 'FN' else 'EXTRA_PREDICTION'


def field_error_category(row, field, comparison):
    if comparison in ('FP', 'FN'):
        return 'EXTRA_FIELD' if comparison == 'FP' else 'MISSING_FIELD'
    gold, predicted = row['gold'][field], row['prediction'][field]
    if predicted and any(predicted == value for name, value in row['gold'].items() if name != field and value):
        return 'POSSIBLE_CROSS_FIELD_CONFUSION'
    if predicted and gold and (predicted in gold or gold in predicted):
        return 'PARTIAL_FIELD_OR_BOUNDARY'
    return 'VALUE_MISMATCH_CAUSE_NOT_DETERMINED'


def jsonl(path):
    with path.open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def analyze_frozen(root, output):
    if output.exists():
        raise FileExistsError(output)
    base = root / 'data/processed/evaluation/sprint03'
    runs = {'HEUR-JW': {'T0': base / 'heur_jw_dev_20261002_v2/threshold_0.86',
                        '5field': base / 'heur_jw_5field_20261002_v1'},
            'CRF-INDEP': {'T0': base / 'crf_indep_dev_20261002_v1/ctx2_c10.05_c20.1/dev_run',
                          '5field': base / 'crf_indep_5field_20261002_v1'}}
    provenance_path = root / 'data/interim/modeling/sprint03/seven_priorities_20261002_v1/prepared_v3/provenance_sidecar.jsonl'
    provenance = {row['sample_id']: row for row in jsonl(provenance_path) if row['split'] == 'dev'}
    if len(provenance) != 60:
        raise ValueError('DEV_PROVENANCE_COUNT_MISMATCH')
    corpus_dir = root / 'data/processed/annotation/sprint03/corpus_train_dev_v2'
    corpus_manifest, corpus_splits = load_corpus(corpus_dir)
    gold = {row['sample_id']: row for row in corpus_splits['dev']}
    excluded = set(corpus_manifest['evaluation_exclusions']['t1'])
    events, summaries, input_hashes = [], {}, {}
    for model, tracks in runs.items():
        for track, run in tracks.items():
            error_path = run / 'error_analysis.jsonl'
            rows = jsonl(error_path)
            predictions = jsonl(run / 'predictions.jsonl')
            if len(predictions) != (60 if track == 'T0' else 4800) or len(rows) > len(predictions):
                raise ValueError('FROZEN_RUN_COUNT_MISMATCH:' + str(run))
            if not {row['sample_id'] for row in rows} <= {row['sample_id'] for row in predictions}:
                raise ValueError('ERROR_ID_NOT_IN_FROZEN_PREDICTIONS')
            for name in ('error_analysis.jsonl', 'predictions.jsonl', 'metrics.json', 'run_manifest.json', 'scoring_manifest.json'):
                input_hashes[(run / name).relative_to(root).as_posix()] = file_hash(run / name)
            metric = json.loads((run / 'metrics.json').read_text())
            row_counts, category_counts, by_source, by_dataset, t1 = Counter(), Counter(), defaultdict(Counter), defaultdict(Counter), Counter()
            by_stratum, trace_decisions, structural = defaultdict(Counter), Counter(), Counter()
            if track == 'T0':
                for sample_id, metadata in provenance.items():
                    by_source[metadata['source_kind']]['samples'] += 1
                    by_source[metadata['source_kind']]['gold_spans'] += len(gold[sample_id]['spans'])
                    by_stratum[metadata['stratum']]['samples'] += 1
                    by_stratum[metadata['stratum']]['gold_spans'] += len(gold[sample_id]['spans'])
                for prediction in predictions:
                    sample_id = prediction['sample_id']
                    for trace in prediction.get('trace', {}).get('admin_matches', []):
                        trace_decisions[trace['decision']] += 1
                    if sample_id not in excluded and gold[sample_id].get('address_system') == 'moi':
                        structural['gold_new_eligible_samples'] += 1
                        structural['district_on_gold_new_samples'] += int(any(s['label'] == 'QuanHuyen' for s in prediction['spans']))
            else:
                for prediction in predictions:
                    by_dataset[prediction['dataset']]['samples'] += 1
            for row in rows:
                sample_id = row['sample_id']
                if track == 'T0':
                    if sample_id not in gold or sample_id not in provenance:
                        raise ValueError('UNKNOWN_DEV_ID')
                    source = provenance[sample_id]['source_kind']
                    by_source[source]['error_records'] += 1
                    stats = row['t0']
                    for key in ('fp_count', 'fn_count'):
                        row_counts[key] += stats[key]
                        by_source[source][key] += stats[key]
                        by_stratum[provenance[sample_id]['stratum']][key] += stats[key]
                    for side, key, other in [('FN', 'fn_keys', 'fp_keys'), ('FP', 'fp_keys', 'fn_keys')]:
                        for span in stats[key]:
                            category = span_error_category(span, stats[other], side)
                            category_counts[category + ':' + side] += 1
                            events.append({'model': model, 'track': track, 'sample_id': sample_id, 'source_kind': source,
                                           'side': side, 'category': category, 'span': span, 'stratum': provenance[sample_id]['stratum'],
                                           'literal': gold[sample_id]['text'][span[0]:span[1]],
                                           'evidence': 'frozen error keys', 'causal_claim': False})
                    if model == 'HEUR-JW' and sample_id not in excluded and row.get('gold_t1') is not None:
                        t1['errors'] += bool(row.get('t1_error'))
                else:
                    dataset = row['dataset']
                    by_dataset[dataset]['error_records'] += 1
                    for field, comparison in row['comparisons'].items():
                        if comparison in ('TP', 'TN'):
                            continue
                        row_counts[comparison] += 1
                        by_dataset[dataset][comparison] += 1
                        category = field_error_category(row, field, comparison)
                        category_counts[category] += 1
                        events.append({'model': model, 'track': track, 'sample_id': sample_id, 'dataset': dataset,
                                       'source_kind': 'not_recorded_per_sample_in_frozen_output', 'field': field,
                                       'comparison': comparison, 'category': category,
                                       'gold': row['gold'][field], 'prediction': row['prediction'][field],
                                       'evidence': 'frozen field comparison', 'causal_claim': False})
            if track == 'T0':
                frozen_totals = metric['t0_exact_span']['micro']
                if row_counts['fp_count'] != frozen_totals['total_fp'] or row_counts['fn_count'] != frozen_totals['total_fn']:
                    raise ValueError('FROZEN_ERROR_COUNTS_MISMATCH')
            summaries[model + ':' + track] = {'samples': len(predictions), 'error_records': len(rows), 'frozen_run': run.relative_to(root).as_posix(),
                'frozen_metric_reference': (run / 'metrics.json').relative_to(root).as_posix(),
                'frozen_metric_payload': metric, 'error_key_counts': dict(row_counts), 'category_counts': dict(category_counts),
                'by_source': {key: dict(value) for key, value in by_source.items()},
                'by_dataset': {key: dict(value) for key, value in by_dataset.items()},
                'by_stratum': {key: dict(value) for key, value in by_stratum.items()},
                'heuristic_candidate_decisions': dict(trace_decisions),
                'structural_diagnostic_counts': dict(structural),
                't1': dict(t1) if model == 'HEUR-JW' and track == 'T0' else 'NOT_IMPLEMENTED_OR_NOT_ANALYZED',
                'scorer_called': False, 'inference_called': False}
    output.mkdir(parents=True)
    write_jsonl(output / 'error_taxonomy.jsonl', events)
    write_json(output / 'taxonomy_summary.json', {'status': 'FROZEN_ERROR_ANALYSIS_COMPLETE', 'runs': summaries,
        'new_metrics_computed': False, 'inputs_sha256': input_hashes,
        'provenance_sidecar_sha256': file_hash(provenance_path),
        'corpus_manifest_sha256': file_hash(corpus_dir / 'manifest.json'),
        'limits': ['taxonomy can overlap semantically; event counts are not new F1',
                   '5field MISMATCH contributes FP+FN in frozen scorer; taxonomy records one field event',
                   '5field per-record observed/derived/synthetic provenance unavailable in frozen output',
                   'error_analysis contains only error records; full denominators come from frozen predictions',
                   'dev rare labels support0/1 cannot support general conclusions; task543 masked for T1',
                   'OCR root causes are not inferred from strings']})
    return {key: {name: row[name] for name in ('samples', 'error_key_counts', 'category_counts', 'by_source')}
            for key, row in summaries.items()}
