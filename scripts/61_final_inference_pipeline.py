"""Explicit inference-only packaging/API path; never accepts training or test gold."""
import argparse
import json
from pathlib import Path
from importlib import import_module

from src.modeling.final_inference_handoff import build_final_package, validate_final_package
from src.modeling.kaggle_artifacts import download_output
from src.evaluation.dev_runner import file_hash, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'upload', 'submit', 'status', 'dataset-status', 'fetch'))
    parser.add_argument('--package-dir', type=Path, required=True)
    parser.add_argument('--workspace', type=Path)
    parser.add_argument('--fivefield-input', type=Path)
    parser.add_argument('--username', default='huynq16')
    parser.add_argument('--run-id', default='dacn-s3-final-infer-20261005-v1')
    parser.add_argument('--credentials', type=Path)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--kernel-ref')
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare':
        if not args.workspace or not args.fivefield_input:
            parser.error('workspace/fivefield-input required')
        result = build_final_package(args.workspace, args.package_dir, args.username, args.run_id,
                     args.fivefield_input, args.fivefield_input.with_suffix('.manifest.json'))
        print(json.dumps({'status': 'FINAL_PACKAGE_VALID', 'upload_bytes': result['upload_bytes']}))
        return
    package = validate_final_package(args.package_dir)
    if args.action == 'upload' and package.get('reuses_uploaded_package'):
        raise ValueError('RELAUNCH_USES_EXISTING_IMMUTABLE_DATASET_NO_UPLOAD')
    api_tools = import_module('scripts.50_kaggle_pipeline')
    if args.action == 'fetch':
        if not args.kernel_ref or not args.output_dir or not args.report:
            parser.error('fetch needs exact kernel-ref, output-dir and report')
        if args.kernel_ref != package['kernel_id'] + '/1':
            raise ValueError('EXPECTED_EXACT_VERSION_1')
        env, _ = api_tools.credential_environment(args.credentials)
        import os
        os.environ.update(env)
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi(); api.authenticate()
        result = download_output(api, args.kernel_ref, args.output_dir)
        manifests = list(args.output_dir.rglob('artifact_manifest.json'))
        if len(manifests) != 1:
            raise ValueError('REMOTE_ARTIFACT_MANIFEST_MISSING')
        index = json.loads(manifests[0].read_text())
        if index['identity'] != package['identity'] or index['run_id'] != package['run_id']:
            raise ValueError('REMOTE_IDENTITY_MISMATCH')
        for name, digest in index['files'].items():
            path = (manifests[0].parent / name).resolve()
            if not path.is_relative_to(manifests[0].parent.resolve()) or file_hash(path) != digest:
                raise ValueError('REMOTE_CONTENT_HASH_CHANGED')
        result.update(status='DOWNLOADED_HASH_VERIFIED', remote_status=index['status'])
        if args.report.exists():
            raise FileExistsError(args.report)
        write_json(args.report, result)
        print(json.dumps({k: result[k] for k in ('status', 'remote_status', 'downloaded_bytes')}))
        return
    commands = {'upload': ['datasets', 'create', '-p', str(args.package_dir.resolve() / 'dataset'), '--keep-tabular', '--dir-mode', 'skip'],
        'submit': ['kernels', 'push', '-p', str(args.package_dir.resolve() / 'kernel'), '--timeout', '43200'],
        'status': ['kernels', 'status', package['kernel_id']], 'dataset-status': ['datasets', 'status', package['dataset_id']]}
    result = api_tools.kaggle_call(commands[args.action], credentials=args.credentials, report=args.report)
    raise SystemExit(result['returncode'])


if __name__ == '__main__':
    main()
