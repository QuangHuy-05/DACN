"""Train T0 CRF on frozen 240 train samples; select by exact span F1 on 60 dev."""

from collections import Counter
import argparse
from contextlib import redirect_stdout
import json
from pathlib import Path
import random
from time import perf_counter

from src.evaluation.adapters.crf_adapter import IndependentCRFAdapter
from src.evaluation.dev_runner import (ROOT, check_release_file, file_hash, load_dev_input, read_jsonl,
    run_dev_inference, runtime_manifest, score_dev_predictions, write_json)
from src.evaluation.experiment_config import crf_config
from src.evaluation.span_features import BIO_LABELS, FEATURE_VERSION, FOLLOWUP_FEATURE_VERSION, TOKENIZER_VERSION, encode_gold, token_features


def train_crf(corpus_dir: Path, output_dir: Path, experiment_id: str, seed: int = 42, feature_version: str = FEATURE_VERSION) -> dict:
    import pycrfsuite
    if output_dir.exists():
        raise FileExistsError(output_dir)
    manifest_path = corpus_dir / "manifest.json"
    corpus = check_release_file(corpus_dir / "train.jsonl", manifest_path, "train.jsonl")
    check_release_file(corpus_dir / "dev.jsonl", manifest_path, "dev.jsonl")
    samples = load_dev_input(corpus_dir / "dev_input.jsonl", manifest_path)
    train = read_jsonl(corpus_dir / "train.jsonl")
    if len(train) != corpus["sample_counts"]["train"]:
        raise ValueError("Frozen train count mismatch")
    aligned = [encode_gold(row["text"], row["spans"]) for row in train]
    seen_tags = Counter(tag for _, tags in aligned for tag in tags)
    random.seed(seed)
    output_dir.mkdir(parents=True)
    records = []
    # Predeclared small grid, no random re-split and no benchmark tuning.
    for context in (1, 2):
        for c1, c2 in ((0.05, 0.1), (0.1, 0.1), (0.1, 1.0), (0.5, 1.0)):
            key = f"ctx{context}_c1{c1:g}_c2{c2:g}"
            candidate = output_dir / key
            candidate.mkdir()
            checkpoint = candidate / "model.crfsuite"
            metadata_path = candidate / "model_metadata.json"
            trainer = pycrfsuite.Trainer(verbose=True)
            trainer.select("lbfgs", "crf1d")
            for row, (tokens, tags) in zip(train, aligned):
                trainer.append(token_features(row["text"], tokens, context, feature_version), tags)
            parameters = {"c1": c1, "c2": c2, "max_iterations": 100, "num_memories": 6,
                          "epsilon": 1e-5, "feature.possible_states": True, "feature.possible_transitions": True}
            trainer.set_params(parameters)
            started = perf_counter()
            with (candidate / "training_log.txt").open("w", encoding="utf-8") as log, redirect_stdout(log):
                trainer.train(str(checkpoint))
            metadata = {"model_id": "CRF-INDEP", "algorithm": "CRFsuite crf1d/L-BFGS", "context": context,
                "parameters": parameters, "seed": seed, "seed_scope": "deterministic L-BFGS; Python RNG fixed; no stochastic sampling",
                "feature_version": feature_version, "tokenizer_version": TOKENIZER_VERSION, "bio_schema": list(BIO_LABELS),
                "observed_training_tags": dict(seen_tags), "unseen_training_tags": sorted(set(BIO_LABELS)-set(seen_tags)),
                "train_samples": len(train), "token_count": sum(len(tokens) for tokens, _ in aligned),
                "truncation": "none; all tokens and all 240 samples retained",
                "gold_alignment": "all train spans exactly reversible through BIO",
                "illegal_bio_policy": "I without matching preceding B/I becomes B, each repair logged",
                "t1": "NOT_IMPLEMENTED; no system labels used as features or targets",
                "t1_excluded_ids_from_manifest": corpus.get("evaluation_exclusions", {}).get("t1", []),
                "train_sha256": file_hash(corpus_dir / "train.jsonl"), "dev_sha256": file_hash(corpus_dir / "dev.jsonl"),
                "corpus_manifest_sha256": file_hash(manifest_path), "checkpoint_sha256": file_hash(checkpoint),
                "training_seconds": perf_counter()-started}
            write_json(metadata_path, metadata)
            config = crf_config(experiment_id+"_dev_"+key, checkpoint, metadata_path, seed)
            run_dir = candidate / "dev_run"
            run_dev_inference(IndependentCRFAdapter(str(checkpoint), str(metadata_path)), samples, config, run_dir,
                {"dev_input_sha256": file_hash(corpus_dir / "dev_input.jsonl"), "corpus_manifest_sha256": file_hash(manifest_path)})
            metrics = score_dev_predictions(run_dir / "predictions.jsonl", corpus_dir / "dev.jsonl", run_dir, manifest_path)
            micro = metrics["t0_exact_span"]["micro"]
            records.append({"context": context, "c1": c1, "c2": c2, "micro": micro,
                "config_path": (run_dir/"model_config.json").resolve().relative_to(ROOT).as_posix(),
                "run_dir": run_dir.resolve().relative_to(ROOT).as_posix(), "checkpoint_sha256": file_hash(checkpoint)})
            print(json.dumps({"candidate": key, "micro": micro}), flush=True)
    chosen = sorted(records, key=lambda r: (-r["micro"]["f1"], r["context"], -r["c2"], -r["c1"]))[0]
    config = json.loads((ROOT / chosen["config_path"]).read_text(encoding="utf-8"))
    write_json(output_dir / "chosen_model_config.json", config)
    report = {"experiment_id": experiment_id, "model_id": "CRF-INDEP", "status": "TRAINED_DEV_SELECTED_TEST_PENDING",
        "selection_rule": "max dev exact-span micro F1; ties: smaller context, higher c2, higher c1",
        "candidates": records, "chosen": chosen, "runtime": runtime_manifest(),
        "code_sha256": {str(path.relative_to(ROOT)): file_hash(path) for path in (
            ROOT/"scripts/26_train_independent_crf.py", ROOT/"src/evaluation/span_features.py", ROOT/"src/evaluation/adapters/crf_adapter.py")},
        "corpus_manifest_sha256": file_hash(manifest_path), "test": "NOT_READ_NOT_USED",
        "interpretation": "Tuned dev result; not an unbiased test estimate"}
    write_json(output_dir / "training_manifest.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", type=Path, default=Path("data/processed/annotation/sprint03/corpus_train_dev_v2"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--feature-version", choices=(FEATURE_VERSION, FOLLOWUP_FEATURE_VERSION), default=FEATURE_VERSION)
    args = parser.parse_args()
    report = train_crf(args.corpus_dir, args.output_dir, args.experiment_id, args.seed, args.feature_version)
    print(json.dumps({"status": report["status"], "chosen": report["chosen"]}))


if __name__ == "__main__":
    main()
