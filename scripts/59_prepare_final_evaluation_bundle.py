"""Build distinct final text-input and gold-scorer bundles from an approved release."""
import argparse
import json
from pathlib import Path
from src.modeling.colab_local_handoff import build_final_bundles, final_notebook
from src.evaluation.dev_runner import write_json

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--notebook", type=Path)
    args = parser.parse_args()
    result = {"status": "PENDING_TEST_GOLD", "test_inference_scoring": "NOT_EXECUTED"}
    if args.corpus_dir:
        if not args.output_dir:
            parser.error("--corpus-dir requires --output-dir")
        result = build_final_bundles(args.corpus_dir, args.output_dir)
    if args.notebook:
        if args.notebook.exists():
            raise FileExistsError(args.notebook)
        args.notebook.parent.mkdir(parents=True, exist_ok=True)
        write_json(args.notebook, final_notebook())
    print(json.dumps(result, ensure_ascii=False))
