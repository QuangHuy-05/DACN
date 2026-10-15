"""Run text-only span inference on an approved frozen dev input."""

import argparse
import json
from pathlib import Path

from src.evaluation.dev_runner import build_adapter, file_hash, load_dev_input, run_dev_inference


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Text-only dev_input.jsonl")
    parser.add_argument("--corpus-manifest", type=Path, required=True)
    parser.add_argument("--model-config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    samples = load_dev_input(args.input, args.corpus_manifest)
    config = json.loads(args.model_config.read_text(encoding="utf-8"))
    adapter = build_adapter(config)
    report = run_dev_inference(adapter, samples, config, args.output_dir, {
        "dev_input_sha256": file_hash(args.input), "corpus_manifest_sha256": file_hash(args.corpus_manifest),
        "model_config_sha256": file_hash(args.model_config),
    })
    print(json.dumps({key: report[key] for key in ("run_id", "sample_count", "status_counts")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
