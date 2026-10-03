"""Build explicit train/dev + licensed-resource ZIPs and a non-executed notebook."""

import argparse
import json
from pathlib import Path
from src.modeling.colab_handoff import build_handoff


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build_handoff(args.output_dir.resolve()), ensure_ascii=False, indent=2))
