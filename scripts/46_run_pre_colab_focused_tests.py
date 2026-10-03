"""Focused suites via discovery, avoiding installed packages named 'tests'."""

import argparse
import unittest
from src.evaluation.dev_runner import ROOT

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("neural", "crf"), required=True)
    args = parser.parse_args()
    patterns = ["test_pre_colab_followup.py"]
    patterns += (["test_modeling_pipeline.py", "test_neural_local_validation.py"] if args.profile == "neural"
                 else ["test_sprint3_experiments.py", "test_span_dev_runner.py", "test_span_evaluation.py"])
    suite = unittest.TestSuite()
    for pattern in patterns:
        suite.addTests(unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern=pattern))
    raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
