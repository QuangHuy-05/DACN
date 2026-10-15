"""Score only after the all-model final freeze; never trains or chooses a model."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from src.evaluation.dev_runner import ROOT, file_hash, write_json
from src.evaluation.final_results import assert_freeze_receipt, paired_ablation, score_overlap_subsets
from src.evaluation.test_runner import score_test_predictions
from src.evaluation.benchmark_runner import score_fivefield_run


def validate_evaluation_bindings(roster_path, pre_test_freeze_path, receipt):
    frozen = json.loads(Path(pre_test_freeze_path).read_text())
    if frozen.get('roster_sha256') != file_hash(Path(roster_path)):
        raise ValueError('PRE_TEST_ROSTER_CHANGED')
    roster = json.loads(Path(roster_path).read_text())
    ready = {m for m, entry in roster.items() if entry['status'] == 'READY'}
    if ready != set(receipt['models']):
        raise ValueError('SCORING_ROSTER_DIFFERENT_FROM_GLOBAL_FREEZE')
    if any(Path(roster[m]['run_dir']).resolve() != Path(entry['run_dir']).resolve()
           for m, entry in receipt['models'].items()):
        raise ValueError('SCORING_RUN_PATH_CHANGED')
    return roster


def paired_metric_deltas(on, off):
    """Report on minus off without changing selections or scored artifacts."""
    return {
        'test_t0_micro_f1_on_minus_off': round(on['test_t0_micro']['f1'] - off['test_t0_micro']['f1'], 8),
        'test_district_fp_on_minus_off': on['test_structural']['quan_huyen_hallucinations_on_new'] - off['test_structural']['quan_huyen_hallucinations_on_new'],
        'test_t1_accuracy_on_minus_off': round(on['test_t1']['overall_accuracy'] - off['test_t1']['overall_accuracy'], 8),
        'test_t1_abstain_on_minus_off': on['test_t1']['abstain_count'] - off['test_t1']['abstain_count'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze-receipt', type=Path, required=True)
    parser.add_argument('--roster', type=Path, required=True)
    parser.add_argument('--pre-test-freeze', type=Path, required=True)
    parser.add_argument('--neural-workspace', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    receipt = assert_freeze_receipt(args.freeze_receipt)
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    corpus = ROOT / 'data/processed/annotation/sprint03/corpus_v1_release2'
    gold = corpus / 'test_benchmark_t0.jsonl'
    roster = validate_evaluation_bindings(args.roster, args.pre_test_freeze, receipt)
    results = {}
    for model, entry in receipt['models'].items():
        directory = Path(entry['run_dir'])
        if model in {'PHOBERT-CRF', 'PROPOSED-DYN', 'PROPOSED-NO-CONSTRAINT'}:
            command = [sys.executable, '-m', 'scripts.56_score_span_test', '--run-dir', str(directory),
                '--gold', str(gold), '--input', str(corpus / 'test_input.jsonl'),
                '--corpus-manifest', str(corpus / 'manifest.json'), '--execute-final-test']
            completed = subprocess.run(command, cwd=args.neural_workspace, capture_output=True, text=True)
            (args.output_dir / (model.lower() + '_score.log')).write_text(completed.stdout + completed.stderr)
            if completed.returncode:
                raise RuntimeError('NEURAL_SCORING_FAILED:' + model)
            metric = json.loads((directory / 'metrics.json').read_text())
        else:
            metric = score_test_predictions(directory, gold, corpus / 'manifest.json', corpus / 'test_input.jsonl')
        t1 = metric['t1_address_system']
        if (t1['total_evaluated'], t1['gold_null_excluded'], t1['declared_exception_excluded']) != (64, 20, 16):
            raise ValueError('FINAL_MASK_COUNTS_CHANGED')
        results[model] = {'test_run': str(directory.relative_to(ROOT)), 'test_metrics_sha256': file_hash(directory / 'metrics.json'),
            'test_t0_micro': metric['t0_exact_span']['micro'], 'test_t1': t1,
            'test_structural': metric['structural_consistency'], 'latency_ms': metric['latency_ms']}
        print(json.dumps({'model': model, 'test_t0': results[model]['test_t0_micro'], 't1_accuracy': t1['overall_accuracy']}), flush=True)
    field_runs = {'HEUR-JW': ROOT / 'data/processed/evaluation/sprint03/heur_jw_followup_fivefield_20261003_v1',
                  'CRF-INDEP': ROOT / 'data/processed/evaluation/sprint03/crf_followup_fivefield_20261003_v1'}
    remote_root = Path(roster['PHOBERT-CRF']['run_dir']).parent
    field_runs.update({model: remote_root / (slug + '_5field') for model, slug in (
        ('PHOBERT-CRF', 'pcrf'), ('PROPOSED-DYN', 'dyn'), ('PROPOSED-NO-CONSTRAINT', 'dyn_off'))})
    for model, directory in field_runs.items():
        manifest = json.loads((directory / 'run_manifest.json').read_text())
        if manifest['sample_count'] != 4800:
            raise ValueError('FIVEFIELD_COUNT_CHANGED')
        for name, digest in manifest['output_sha256'].items():
            if file_hash(directory / name) != digest:
                raise ValueError('FIVEFIELD_FROZEN_CHANGED')
        if (directory / 'metrics.json').exists():
            metric = json.loads((directory / 'metrics.json').read_text())
        else:
            metric = score_fivefield_run(directory)
        results[model].update(fivefield_run=str(directory.relative_to(ROOT)), fivefield=metric['overall'])
    overlap = score_overlap_subsets(field_runs, args.output_dir / 'overlap', ROOT / 'data/processed/annotation/sprint03/corpus_train_dev_v2')
    ablation = paired_ablation(Path(roster['PROPOSED-DYN']['run_dir']), Path(roster['PROPOSED-NO-CONSTRAINT']['run_dir']))
    write_json(args.output_dir / 'paired_ablation.json', ablation)
    write_json(args.output_dir / 'paired_metric_delta.json', {**ablation, 'metric_deltas': paired_metric_deltas(
        results['PROPOSED-DYN'], results['PROPOSED-NO-CONSTRAINT'])})
    for model in ('DP-ZS-FT', 'DP-FT-FT'):
        results[model] = {'status': 'BLOCKED_CHECKPOINT_LICENSE_UNDECLARED', 'test': None, 'fivefield': None}
    write_json(args.output_dir / 'results_index.json', {'status': 'FINAL_READY_MODELS_SCORED_DP_BLOCKED',
        'global_freeze_sha256': file_hash(args.freeze_receipt), 'no_test_tuning': True,
        'models': results, 'overlap_counts': overlap['counts'], 'ablation': ablation,
        'gold_manifest_sha256': file_hash(corpus / 'manifest.json')})


if __name__ == '__main__':
    main()
