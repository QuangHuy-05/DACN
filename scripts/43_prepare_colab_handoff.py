"""Build explicit train/dev + licensed-resource ZIPs and a non-executed notebook."""

import argparse
import json
from pathlib import Path
from src.modeling.colab_handoff import build_handoff


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--notebook", type=Path)
    parser.add_argument("--version", default="v1")
    args = parser.parse_args()
    print(json.dumps(build_handoff(args.output_dir.resolve(), args.notebook, args.version), ensure_ascii=False, indent=2))
