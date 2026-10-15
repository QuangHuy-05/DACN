"""Prepare fixed train/dev raw alignment; optional verified PhoBERT resources."""

from src.modeling.cli import main

if __name__ == "__main__":
    raise SystemExit(main("phobert_crf_v1.json"))
