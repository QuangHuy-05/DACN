"""Publish metadata completion separately; never overwrite a released package."""
import argparse
import json
from pathlib import Path
from src.data.nso_release_metadata import complete_source_register

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(complete_source_register(args.parent.resolve(), args.evidence.resolve(), args.output_dir.resolve())))
