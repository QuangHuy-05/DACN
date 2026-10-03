"""PhoBERT-CRF prepare/preflight/train/infer CLI."""

from src.modeling.cli import main

if __name__ == "__main__":
    raise SystemExit(main("phobert_crf_v1.json"))
