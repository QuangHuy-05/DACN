"""T1 (cu / moi / Lai) evaluation, DYN diagnostics and the H5 table (WP2).

Usage (repository root, main venv):
    python -m scripts.68_run_t1_evaluation                 # tier 1 (CPU)
    python -m scripts.68_run_t1_evaluation --stage tier2   # score outputs of scripts/68b

Tier 1 creates the versioned run directory (never overwritten), declares the
systems in ``run_manifest.json`` *before* any scoring, runs every CPU system
on text only and writes predictions, metrics and tables.  Tier 2 only adds
files under ``tier2/`` and ``tables/*tier2*``; tier-1 files are left untouched.

CRF-INDEP needs ``pycrfsuite``, which only the CRF runtime has; this file
therefore doubles as a stdlib-only worker (``--crf-worker``).
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]
SCRIPT_VERSION = "t1-h5-run-v1"
CI_SEED = 20261015
DEFAULT_RESAMPLES = 10_000
DEFAULT_SETS = Path("data/interim/modeling/sprint04/t1_sets_20261015_v1")
DEFAULT_OUT = Path("data/processed/evaluation/sprint04/t1_h5_20261015_v1")
CORPUS_DIR = Path("data/processed/annotation/sprint03/corpus_v1_release2")
GAZETTEER_DIR = Path("data/processed/gazetteer/s3_v4_nso_dual_snapshot_release2")
CRF_RUNTIME = Path("data/interim/evaluation/sprint03/runtime_py311/bin/python")
FINAL_DIR = Path("data/interim/modeling/sprint03/final_completion_20261005_v1")
FROZEN_INDEX = FINAL_DIR / "all_test_predictions_frozen.json"
LIGHT_RUNS = FINAL_DIR / "light_test_runs_v2"
NEURAL_RUNS = (FINAL_DIR / "kaggle_final_output_v4/dacn_artifacts/dacn-s3-final-infer-20261005-v4/workspace"
               / "data/interim/modeling/sprint03/dacn-s3-final-infer-20261005-v4")
FROZEN_TEST_RUNS = {
    "HEUR-JW": LIGHT_RUNS / "heur-jw", "CRF-INDEP": LIGHT_RUNS / "crf-indep",
    "PHOBERT-CRF": NEURAL_RUNS / "pcrf_test", "PROPOSED-DYN": NEURAL_RUNS / "dyn_test",
}
DYN_WORKSPACE = Path("data/interim/modeling/sprint03/release_and_kaggle_20261005_v1/dyn_c02_selection_artifacts_v1/"
                     "dacn_artifacts/dacn-s3-dyn-c02-20261005-v1/workspace")
DYN_CHECKPOINT = DYN_WORKSPACE / ("data/processed/evaluation/sprint03/"
                                  "dacn-s3-dyn-c02-20261005-v1_proposed_dyn_c02/checkpoints/best.pt")
DYN_CHECKPOINT_SHA256 = "7a4a3d01bff1222cd303cb5ff03872c5ee49b22cb67a0572833fa470f917a589"

# System identifiers (rows of the H5 table, fixed before scoring).
MAJORITY, ONE_FEATURE, HEUR, DYN = "BASELINE-MAJORITY", "BASELINE-ONE-FEATURE", "HEUR-JW", "PROPOSED-DYN"
PIPE_CRF, PIPE_PCRF, PIPE_DYN = "T1-PIPE-CRF", "T1-PIPE-PCRF", "T1-PIPE-DYN"
FEAT, FEAT_NOGAZ, PROBE, DYN_AUG = "T1-FEAT", "T1-FEAT-NOGAZ", "T1-HEAD-PROBE", "DYN-T1-AUG"
SYSTEM_ORDER = (MAJORITY, ONE_FEATURE, HEUR, DYN, PIPE_CRF, PIPE_PCRF, PIPE_DYN, FEAT, FEAT_NOGAZ, PROBE, DYN_AUG)
SYSTEM_DEFINITIONS = {
    MAJORITY: {"uses_gazetteer": False, "definition": "always the majority T1 class of the Sprint 3 train split"},
    ONE_FEATURE: {"uses_gazetteer": True, "definition": "class from one binary text feature (district sign: district "
                  "prefix or a non-final segment equal to an old district name); value -> majority class of t1_synth_train"},
    HEUR: {"uses_gazetteer": True, "definition": "locked HEUR-JW (light_test_runs_v2/heur-jw/model_config.json)"},
    DYN: {"uses_gazetteer": False, "definition": "PROPOSED-DYN c02 T1 head with the locked threshold/margin"},
    PIPE_CRF: {"uses_gazetteer": True, "definition": "CRF-INDEP administrative spans + HEUR-JW _resolve + system rule"},
    PIPE_PCRF: {"uses_gazetteer": True, "definition": "PHOBERT-CRF administrative spans + HEUR-JW _resolve + system rule"},
    PIPE_DYN: {"uses_gazetteer": True, "definition": "PROPOSED-DYN administrative spans + HEUR-JW _resolve + system rule"},
    FEAT: {"uses_gazetteer": True, "definition": "numpy linear softmax on surface + gazetteer-membership features; "
           "trained on t1_synth_train, L2 chosen on t1_synth_dev"},
    FEAT_NOGAZ: {"uses_gazetteer": False, "definition": "T1-FEAT without the gazetteer feature group"},
    PROBE: {"uses_gazetteer": False, "definition": "numpy linear softmax probe on the frozen DYN encoder CLS vector; "
            "trained on t1_synth_train + Sprint 3 train T1 labels, L2 chosen on t1_synth_dev; not a retrained model"},
    DYN_AUG: {"uses_gazetteer": False, "definition": "DYN retrained with hybrid data (outside this work package)"},
}
DATASETS = ("s3_test", "synth_eval", "data06")
COLUMNS = {  # H5 columns -> (dataset, subset flag or None)
    "s3_test_eligible": ("s3_test", None),
    "t1_synth_eval": ("synth_eval", None),
    "t1_data06_heldout": ("data06", None),
    "t1_data06_heldout_unseen_groups": ("data06", "unseen_group"),
}
EXTRA_COLUMNS = {"t1_synth_eval_adm_only": ("synth_eval", "resolved_group")}
COLUMN_LABELS = {"s3_test_eligible": "POST_HOC_SECONDARY", "t1_synth_eval": "STRESS_TRACK",
                 "t1_data06_heldout": "STRESS_TRACK", "t1_data06_heldout_unseen_groups": "STRESS_TRACK",
                 "t1_synth_eval_adm_only": "STRESS_TRACK"}
NEURAL_ONLY_OFF_TEST = (DYN, PIPE_PCRF, PIPE_DYN)
STATUS_NOT_RUN = "NOT_RUN"
STATUS_DEFERRED = "DEFERRED_NEEDS_TRAINING_PROTOCOL_CHANGE"
STATUS_BLOCKED = "BLOCKED_LOCAL_NEURAL"
SOURCE_FILES = (
    "scripts/68_run_t1_evaluation.py", "scripts/68b_run_t1_neural_local.py", "scripts/67_build_t1_sets.py",
    "src/evaluation/t1_pipeline.py", "src/evaluation/t1_situations.py", "src/evaluation/t2_lookup.py",
    "src/evaluation/stats.py", "src/evaluation/leak_guard.py", "src/evaluation/adapters/heur_jw_adapter.py",
    "src/evaluation/adapters/heur_jw_followup.py", "src/evaluation/adapters/crf_adapter.py",
    "src/evaluation/span_features.py",
)
DECLARED_RULES = {
    "t1_pipe": "administrative spans (PhuongXa/QuanHuyen/TinhThanh by T0 label) visited right to left; each is "
               "resolved with HeuristicJaroWinklerFollowup._resolve (locked arguments); cu+moi -> Lai, one system "
               "-> that system, none -> khong_ro",
    "abstention": "khong_ro counts as wrong in accuracy and as a missed gold class in per-class recall",
    "macro_f1": "mean F1 over cu/moi/Lai (Sprint 3 scorer convention); single-class sets -> NOT_EVALUABLE_SINGLE_CLASS",
    "ci": "percentile cluster bootstrap over admin_group_key, B resamples, seed 20261015; per-cluster count "
          "matrices are resampled so every statistic is recomputed from summed counts",
    "paired": "each system vs HEUR-JW on the same samples: cluster paired bootstrap of the accuracy difference, "
              "exact McNemar on correct/wrong, approximate randomization on accuracy",
    "l2_selection": "grid {0.01, 0.1, 1}; dev macro-F1, then dev accuracy, then the larger L2; seed 42",
    "majority_class": "majority T1 label of the Sprint 3 train split (ties: cu, moi, Lai)",
    "situations": "t1-situations-v1 (see src/evaluation/t1_situations.py)",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# CRF worker (stdlib + pycrfsuite only; never imports numpy/pandas)
# ---------------------------------------------------------------------------

def crf_worker(repo: Path, input_path: Path, output_path: Path) -> None:
    sys.path.insert(0, str(repo))
    from src.evaluation.adapters.crf_adapter import IndependentCRFAdapter

    config = json.loads((repo / LIGHT_RUNS / "crf-indep" / "model_config.json").read_text(encoding="utf-8"))
    for name in ("checkpoint", "metadata"):  # locked hashes are checked before the model is opened
        resource = config["resources"][name]
        if sha256_file(repo / resource["path"]) != resource["sha256"]:
            raise SystemExit(f"HASH_MISMATCH {resource['path']}")
    adapter = IndependentCRFAdapter(**{k: str(repo / v) for k, v in config["adapter_kwargs"].items()})
    with input_path.open(encoding="utf-8") as src, output_path.open("w", encoding="utf-8", newline="\n") as dst:
        for line in src:
            item = json.loads(line)  # only {"key", "text"}: no metadata reaches the model
            out = adapter.parse_spans(item["text"], sample_id=item["key"])
            spans = [{"start": s.start, "end": s.end, "label": s.label} for s in out.spans]
            dst.write(json.dumps({"key": item["key"], "spans": spans, "python": platform.python_version()},
                                 ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Small IO helpers
# ---------------------------------------------------------------------------

def dump_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _fmt(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        # Tiny non-zero values (p-values) keep their magnitude instead of printing 0.000000.
        return f"{value:.3e}" if 0 < abs(value) < 1e-4 else f"{value:.6f}"
    return value


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> dict:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _fmt(row.get(column)) for column in columns})
    keys = [tuple(_fmt(row.get(column)) for column in columns) for row in rows]
    return {"rows": len(rows), "columns": len(columns), "duplicate_rows": len(keys) - len(set(keys))}


def write_text_inputs(path: Path, keys, texts) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for key, text in zip(keys, texts):  # opaque key + text only
            stream.write(json.dumps({"key": key, "text": text}, ensure_ascii=False) + "\n")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

class Run:
    def __init__(self, sets_dir: Path, out_dir: Path, resamples: int) -> None:
        import pandas as pd

        from src.evaluation import leak_guard, stats, t1_pipeline, t1_situations
        self.pd, self.P, self.S, self.G, self.stats = pd, t1_pipeline, t1_situations, leak_guard, stats
        self.sets_dir, self.out, self.resamples = sets_dir, out_dir, resamples
        self.inputs: dict[str, str] = {}
        self.predictions: dict[tuple[str, str], dict[str, str]] = {}  # (system, dataset) -> key -> label
        self.gold: dict[str, "pd.DataFrame"] = {}
        self.texts: dict[str, "pd.DataFrame"] = {}  # dataset -> frame with only key/text
        self.notes: dict = {}

    # -- loading -----------------------------------------------------------------

    def _hash(self, relative: Path) -> str:
        digest = sha256_file(REPO / relative)
        self.inputs[str(relative).replace("\\", "/")] = digest
        return digest

    def load_sets(self) -> None:
        pd = self.pd
        manifest = json.loads((self.sets_dir / "run_manifest.json").read_text(encoding="utf-8"))
        self.sets = {}
        for name in ("t1_synth_train", "t1_synth_dev", "t1_synth_eval", "t1_data06_heldout"):
            path = self.sets_dir / f"{name}.csv"
            digest = sha256_file(path)
            if digest != manifest["outputs"][f"{name}.csv"]["sha256"]:
                raise ValueError(f"HASH_MISMATCH {path}")
            self.inputs[f"t1_sets/{name}.csv"] = digest
            frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
            missing = [c for c in ("key", "text", "gold_system", "admin_group_key", "province_new") if c not in frame]
            if missing:
                raise ValueError(f"{path}: missing columns {missing}")
            self.sets[name] = frame
        self.inputs["t1_sets/run_manifest.json"] = sha256_file(self.sets_dir / "run_manifest.json")
        self.notes["t1_sets_summary"] = manifest["summary"]
        self.notes["t1_sets_steps"] = manifest["steps"]
        self.notes["sprint3_dev_test_filter"] = manifest["sprint3_dev_test_filter"]

    def load_corpus(self) -> None:
        records, hashes = self.G.load_corpus_records(REPO / CORPUS_DIR)  # verifies manifest hashes
        self.records = records
        self.inputs.update({f"{CORPUS_DIR.as_posix()}/{name}": digest for name, digest in hashes.items()})
        manifest_path = CORPUS_DIR / "manifest.json"
        self._hash(manifest_path)
        manifest = json.loads((REPO / manifest_path).read_text(encoding="utf-8"))
        self.exclusions = {"dev": manifest["evaluation_exclusions"]["t1"],
                           "test": manifest["test_evaluation_exclusions"]["t1"]}
        inputs = self.P.read_jsonl(REPO / CORPUS_DIR / "test_input.jsonl")
        self._hash(CORPUS_DIR / "test_input.jsonl")
        if [r["sample_id"] for r in inputs] != [r["sample_id"] for r in records["test"]]:
            raise ValueError("test_input.jsonl and test gold differ in sample order")
        self.test_inputs = inputs

    def load_frozen(self) -> None:
        index = json.loads((REPO / FROZEN_INDEX).read_text(encoding="utf-8"))
        self._hash(FROZEN_INDEX)
        self.frozen = {}
        for model, run_dir in FROZEN_TEST_RUNS.items():
            path = run_dir / "predictions.jsonl"
            if self._hash(path) != index["models"][model]["predictions_sha256"]:
                raise ValueError(f"HASH_MISMATCH frozen predictions of {model}")
            rows = self.P.read_jsonl(REPO / path)
            self.frozen[model] = {row["sample_id"]: row for row in rows}
            if set(self.frozen[model]) != {r["sample_id"] for r in self.test_inputs}:
                raise ValueError(f"{model}: frozen predictions do not cover the test split")
        # Dev predictions of DYN: the run named by the selection lock of dyn_test.
        lock = json.loads((REPO / FROZEN_TEST_RUNS["PROPOSED-DYN"] / "selection_lock.json").read_text(encoding="utf-8"))
        dev_rel = Path(lock["selected_dev_run"]) / "predictions.jsonl"
        dev_path = DYN_WORKSPACE / dev_rel
        if self._hash(dev_path) != lock["dev_evidence"][dev_rel.as_posix()]:
            raise ValueError("HASH_MISMATCH DYN dev predictions vs selection_lock.json")
        self.dyn_dev = self.P.read_jsonl(REPO / dev_path)
        self.notes["dyn_dev_run"] = lock["selected_dev_run"]
        if self._hash(DYN_CHECKPOINT) != DYN_CHECKPOINT_SHA256:
            raise ValueError("HASH_MISMATCH DYN c02 checkpoint")
        self._hash(LIGHT_RUNS / "heur-jw" / "model_config.json")
        self._hash(LIGHT_RUNS / "crf-indep" / "model_config.json")


# -- gold tables (scoring side only) --------------------------------------------------

def build_gold(self) -> None:
    pd, S = self.pd, self.S
    from src.data.administrative_alias import resolve_province_alias
    from src.data.administrative_mapping import default_mapping_path, load_administrative_mapping

    tagger = S.SituationTagger.load(REPO / GAZETTEER_DIR)
    self.inputs.update({f"{GAZETTEER_DIR.as_posix()}/{name}": digest
                        for name, digest in tagger.table.source_hashes.items()})
    mapping = load_administrative_mapping(default_mapping_path())

    def synthetic(frame, dataset):
        gold = pd.DataFrame({
            "key": frame["key"], "gold_system": frame["gold_system"], "cluster": frame["admin_group_key"],
            "KieuLai": frame["KieuLai"].str[:2], "province_new": frame["province_new"],
            "resolved_group": frame["admin_group_key"].str.startswith("ADM|"),
        })
        gold["unseen_group"] = (frame["group_seen_in_synth_train"] == "False") if "group_seen_in_synth_train" in frame \
            else False
        gold["tags"] = [S.format_tags(tagger.tags(r["gold_system"], r["gold_province"], r["gold_district"], r["gold_ward"]))
                        for r in frame.to_dict("records")]
        self.gold[dataset] = gold.reset_index(drop=True)
        self.texts[dataset] = frame[["key", "text"]].reset_index(drop=True)

    synthetic(self.sets["t1_synth_eval"], "synth_eval")
    synthetic(self.sets["t1_data06_heldout"], "data06")

    mask = self.P.t1_mask(self.records["test"], self.exclusions["test"])
    self.notes["s3_test_mask"] = {name: len(ids) for name, ids in mask.items()}
    eligible = set(mask["eligible"])
    rows = []
    for record in self.records["test"]:
        if record["sample_id"] not in eligible:
            continue
        fields = S.fields_from_gold_spans(record["text"], record["spans"])
        province_new = mapping.resolve_new_province(fields["province"]) or mapping.resolve_new_province(
            resolve_province_alias(fields["province"]))
        cluster = self.G.admin_group_key(fields["province"], fields["district"], fields["ward"], mapping)
        rows.append({
            "key": record["sample_id"], "gold_system": record["address_system"], "cluster": cluster,
            "KieuLai": "", "province_new": province_new, "resolved_group": cluster.startswith("ADM|"),
            "unseen_group": False,
            "tags": S.format_tags(tagger.tags(record["address_system"], fields["province"], fields["district"],
                                              fields["ward"])),
        })
    self.gold["s3_test"] = pd.DataFrame(rows)
    # Inference input of the test split is the published text-only file.
    self.texts["s3_test"] = pd.DataFrame(
        [{"key": r["sample_id"], "text": r["text"]} for r in self.test_inputs])


Run.build_gold = build_gold


def declare(self, stage_note: str) -> None:
    """Write the manifest with systems, rules and seeds before anything is scored."""
    self.manifest = {
        "script_version": SCRIPT_VERSION,
        "status": "DECLARED_BEFORE_SCORING",
        "declared_at": now_iso(),
        "stage": stage_note,
        "seeds": {"ci_bootstrap": CI_SEED, "classifier": self.P.CLASSIFIER_SEED, "t1_sets": 20261015},
        "n_resamples": self.resamples,
        "systems": {name: SYSTEM_DEFINITIONS[name] for name in SYSTEM_ORDER},
        "system_order": list(SYSTEM_ORDER),
        "h5_columns": {**COLUMNS, **EXTRA_COLUMNS},
        "column_labels": COLUMN_LABELS,
        "rules": DECLARED_RULES,
        "rule_versions": {"t1_pipeline": self.P.RULE_VERSION, "t1_situations": self.S.RULE_VERSION,
                          "leak_guard": self.G.RULE_VERSION},
        "l2_grid": list(self.P.L2_GRID),
        "inference_contract": "every system receives a frame with only key/text; gold_system, KieuLai, source, "
                              "admin_group_key and spans stay on the scoring side",
        "test_usage": "Sprint 3 test is POST_HOC_SECONDARY: no system, rule, seed or threshold was chosen on it",
        "inputs_sha256": dict(sorted(self.inputs.items())),
        "code_sha256": {name: sha256_file(REPO / name) for name in SOURCE_FILES if (REPO / name).exists()},
        "python": platform.python_version(),
    }
    dump_json(self.out / "run_manifest.json", self.manifest)


Run.declare = declare


# -- inference (text only) ------------------------------------------------------------

def set_predictions(self, system: str, dataset: str, keys, labels) -> None:
    self.predictions[(system, dataset)] = dict(zip(keys, labels))


Run.set_predictions = set_predictions


def run_crf_spans(self, workdir: Path) -> dict[str, list[dict]]:
    """CRF-INDEP spans for the synthetic sets, computed in the CRF runtime as a separate process."""
    texts = workdir / "crf_inputs.jsonl"
    keys, values = [], []
    for dataset in ("synth_eval", "data06"):
        frame = self.texts[dataset]
        keys += [f"{dataset}|{k}" for k in frame["key"]]
        values += self.P.inference_texts(frame)
    write_text_inputs(texts, keys, values)
    out = workdir / "crf_indep_spans.jsonl"
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    cmd = [str(REPO / CRF_RUNTIME), str(REPO / "scripts" / "68_run_t1_evaluation.py"), "--crf-worker",
           "--worker-in", str(texts), "--worker-out", str(out), "--repo", str(REPO)]
    subprocess.run(cmd, check=True, env=env, cwd=str(REPO))
    spans = {}
    for row in self.P.read_jsonl(out):
        spans[row["key"]] = row["spans"]
        self.notes["crf_python"] = row["python"]
    self.notes["crf_span_file_sha256"] = sha256_file(out)
    return spans


Run.run_crf_spans = run_crf_spans


def run_tier1_systems(self) -> None:
    P, np = self.P, __import__("numpy")
    heur = P.load_locked_heur(REPO)
    extractor = P.FeatureExtractor(heur)
    test_keys = self.texts["s3_test"]["key"].tolist()
    test_text = dict(zip(test_keys, P.inference_texts(self.texts["s3_test"])))

    # Majority baseline: constant class fixed from the Sprint 3 train labels.
    train_counts = Counter(r["address_system"] for r in self.records["train"] if r.get("address_system") in P.CLASSES)
    majority = sorted(P.CLASSES, key=lambda c: (-train_counts[c], P.CLASSES.index(c)))[0]
    self.notes["majority_class"] = {"class": majority, "sprint3_train_counts": dict(train_counts)}

    # One-feature baseline: rule learnt on t1_synth_train (labels used for fitting only).
    train, dev = self.sets["t1_synth_train"], self.sets["t1_synth_dev"]
    train_text = P.inference_texts(train[["key", "text"]])
    dev_text = P.inference_texts(dev[["key", "text"]])
    rule = {}
    flags = [extractor.has_district_sign(t) for t in train_text]
    for flag in (True, False):
        counts = Counter(g for g, f in zip(train["gold_system"], flags) if f == flag)
        rule[flag] = sorted(P.CLASSES, key=lambda c: (-counts[c], P.CLASSES.index(c)))[0]
    self.notes["one_feature_rule"] = {"district_sign": rule[True], "no_district_sign": rule[False]}

    # T1-FEAT and the variant without the gazetteer feature group.
    feat_models = {}
    y_train = [P.CLASSES.index(g) for g in train["gold_system"]]
    y_dev = [P.CLASSES.index(g) for g in dev["gold_system"]]
    for system, use_gazetteer in ((FEAT, True), (FEAT_NOGAZ, False)):
        train_features = [extractor.features(t, use_gazetteer) for t in train_text]
        vectorizer = P.Vectorizer(train_features)
        model, l2, trials = P.select_l2(
            vectorizer.transform(train_features), y_train,
            vectorizer.transform([extractor.features(t, use_gazetteer) for t in dev_text]), y_dev,
            seed=P.CLASSIFIER_SEED)
        feat_models[system] = (vectorizer, model, use_gazetteer)
        weights = {name: [round(float(w), 4) for w in model.weights[i]] for i, name in enumerate(vectorizer.names)}
        self.notes[f"{system}_selection"] = {
            "selected_l2": l2, "trials": trials, "n_features": len(vectorizer.names),
            "train_rows": len(train), "dev_rows": len(dev), "weights_cu_moi_lai": weights}

    crf_spans = self.run_crf_spans(self.out / "work")

    for dataset in DATASETS:
        frame = self.texts[dataset]
        keys, texts = frame["key"].tolist(), P.inference_texts(frame)
        self.set_predictions(MAJORITY, dataset, keys, [majority] * len(keys))
        self.set_predictions(ONE_FEATURE, dataset, keys, [rule[extractor.has_district_sign(t)] for t in texts])
        for system, (vectorizer, model, use_gazetteer) in feat_models.items():
            matrix = vectorizer.transform([extractor.features(t, use_gazetteer) for t in texts])
            self.set_predictions(system, dataset, keys, [P.CLASSES[i] for i in model.predict(matrix)])
        if dataset == "s3_test":
            continue
        self.set_predictions(HEUR, dataset, keys, [P.heur_predict(heur, t) for t in texts])
        self.set_predictions(PIPE_CRF, dataset, keys,
                             [P.pipe_predict(heur, t, crf_spans[f"{dataset}|{k}"])[0] for k, t in zip(keys, texts)])

    # Sprint 3 test: frozen predictions only (no model is run again).
    def frozen_system(model):
        return [P.ABSTAIN if self.frozen[model][k]["abstain"] else self.frozen[model][k]["predicted_system"]
                for k in test_keys]

    self.set_predictions(HEUR, "s3_test", test_keys, frozen_system("HEUR-JW"))
    self.set_predictions(DYN, "s3_test", test_keys, frozen_system("PROPOSED-DYN"))
    for system, model in ((PIPE_CRF, "CRF-INDEP"), (PIPE_PCRF, "PHOBERT-CRF"), (PIPE_DYN, "PROPOSED-DYN")):
        # Span offsets come from the frozen prediction, surfaces from the text-only input.
        self.set_predictions(system, "s3_test", test_keys,
                             [P.pipe_predict(heur, test_text[k], self.frozen[model][k]["spans"])[0] for k in test_keys])
    # Consistency check of the reused rule: HEUR-JW's own spans must give HEUR-JW's own T1.
    own = [P.pipe_predict(heur, test_text[k], self.frozen["HEUR-JW"][k]["spans"])[0] for k in test_keys]
    self.notes["pipe_rule_check_on_heur_spans"] = {
        "agree": sum(a == b for a, b in zip(own, frozen_system("HEUR-JW"))), "n": len(test_keys)}
    self.notes["heur_gazetteer_version"] = heur.gazetteer_version


Run.run_tier1_systems = run_tier1_systems


# -- scoring -----------------------------------------------------------------------------

def column_frame(self, column: str):
    dataset, flag = {**COLUMNS, **EXTRA_COLUMNS}[column]
    gold = self.gold[dataset]
    return dataset, (gold[gold[flag]] if flag else gold)


Run.column_frame = column_frame


def _ci_fields(result: dict, prefix: str) -> dict:
    return {f"{prefix}_ci_low": result.get("ci_low"), f"{prefix}_ci_high": result.get("ci_high"),
            f"{prefix}_ci_status": result.get("status")}


def score_cell(self, system: str, column: str, with_ci: bool = True) -> dict:
    P, stats, np = self.P, self.stats, __import__("numpy")
    dataset, gold = self.column_frame(column)
    base = {"system": system, "column": column, "dataset": dataset, "column_label": COLUMN_LABELS[column],
            "uses_gazetteer": SYSTEM_DEFINITIONS[system]["uses_gazetteer"]}
    predictions = self.predictions.get((system, dataset))
    if predictions is None:
        status = STATUS_DEFERRED if system == DYN_AUG else self.cell_status.get((system, dataset), STATUS_NOT_RUN)
        return {**base, "status": status}
    labels = [predictions[k] for k in gold["key"]]
    golds = gold["gold_system"].tolist()
    metrics = P.t1_metrics(golds, labels)
    lai = metrics["per_class"]["Lai"]
    row = {**base, "status": "OK", "n": metrics["n"], "n_clusters": int(gold["cluster"].nunique()),
           "correct": metrics["correct"], "accuracy": metrics["accuracy"], "macro_f1": metrics["macro_f1"],
           "lai_support": lai["support"], "lai_predicted": lai["predicted"], "lai_tp": lai["tp"],
           "lai_precision": lai["precision"] if lai["predicted"] else "NOT_EVALUABLE_NO_PREDICTION",
           "lai_recall": lai["recall"] if lai["support"] else P.NOT_EVALUABLE_NO_SUPPORT,
           "lai_f1": lai["f1"] if lai["support"] else P.NOT_EVALUABLE_NO_SUPPORT,
           "coverage": metrics["coverage"], "abstain_count": metrics["abstain_count"],
           "abstain_rate": metrics["abstain_rate"]}
    detail = {"metrics": metrics}
    if not with_ci:
        return {**row, "_detail": detail}
    units = P.to_units(golds, labels)
    clusters = gold["cluster"].tolist()
    grouped = P.aggregate_by_cluster(units, clusters)
    ids = np.arange(len(grouped))
    kwargs = {"n_resamples": self.resamples, "seed": CI_SEED}
    ci = {"accuracy": stats.cluster_bootstrap_ci(P.accuracy_stat, grouped, ids, **kwargs)}
    if metrics["classes_with_support"] > 1:
        ci["macro_f1"] = stats.cluster_bootstrap_ci(P.macro_f1_stat, grouped, ids, **kwargs)
        ci["lai_f1"] = stats.cluster_bootstrap_ci(P.class_f1_stat("Lai"), grouped, ids, **kwargs)
    else:
        ci["lai_recall"] = stats.cluster_bootstrap_ci(P.class_recall_stat("Lai"), grouped, ids, **kwargs)
    for name, result in ci.items():
        row.update(_ci_fields(result, name))
    detail["ci"] = ci
    reference = self.predictions.get((HEUR, dataset))
    if system != HEUR and reference is not None:
        ref_labels = [reference[k] for k in gold["key"]]
        ref_units = P.to_units(golds, ref_labels)
        ref_grouped = P.aggregate_by_cluster(ref_units, clusters)
        delta = stats.paired_bootstrap_delta(P.accuracy_stat, grouped, ref_grouped, cluster_ids=ids, **kwargs)
        b = sum(p == g and r != g for p, r, g in zip(labels, ref_labels, golds))
        c = sum(p != g and r == g for p, r, g in zip(labels, ref_labels, golds))
        mcnemar = stats.mcnemar_exact(b, c)
        randomization = stats.approximate_randomization(P.accuracy_stat, units, ref_units,
                                                        n_permutations=self.resamples, seed=CI_SEED)
        row.update({"delta_acc_vs_heur": metrics["accuracy"] - P.t1_metrics(golds, ref_labels)["accuracy"],
                    **_ci_fields(delta, "delta_acc"), "delta_prop_le_0": delta.get("prop_delta_le_0"),
                    "mcnemar_b_sys_only_correct": b, "mcnemar_c_heur_only_correct": c,
                    "mcnemar_p": mcnemar.get("p_value"), "mcnemar_status": mcnemar.get("status"),
                    "randomization_p": randomization.get("p_value"),
                    "randomization_status": randomization.get("status")})
        detail["paired_vs_heur"] = {"bootstrap": delta, "mcnemar": mcnemar, "randomization": randomization}
    return {**row, "_detail": detail}


Run.score_cell = score_cell

H5_COLUMNS = [
    "system", "column", "column_label", "status", "uses_gazetteer", "n", "n_clusters", "correct", "accuracy",
    "accuracy_ci_low", "accuracy_ci_high", "accuracy_ci_status", "macro_f1", "macro_f1_ci_low", "macro_f1_ci_high",
    "lai_support", "lai_predicted", "lai_tp", "lai_precision", "lai_recall", "lai_recall_ci_low", "lai_recall_ci_high",
    "lai_f1", "lai_f1_ci_low", "lai_f1_ci_high", "coverage", "abstain_count", "abstain_rate", "delta_acc_vs_heur",
    "delta_acc_ci_low", "delta_acc_ci_high", "delta_acc_ci_status", "delta_prop_le_0", "mcnemar_b_sys_only_correct",
    "mcnemar_c_heur_only_correct", "mcnemar_p", "mcnemar_status", "randomization_p", "randomization_status",
]
BREAKDOWN_COLUMNS = ["system", "dataset", "breakdown", "value", "status", "n", "correct", "accuracy", "lai_support",
                     "lai_tp", "lai_recall", "abstain_count"]


def breakdown_rows(self, systems, kind: str) -> list[dict]:
    """Accuracy with denominators by KieuLai, situation tag or new province (no CI: small strata)."""
    P = self.P
    rows = []
    for dataset in DATASETS:
        gold = self.gold[dataset]
        if kind == "kieu_lai":
            groups = {v: gold["KieuLai"] == v for v in sorted(set(gold["KieuLai"]) - {""})}
        elif kind == "situation":
            groups = {tag: gold["tags"].map(lambda t, tag=tag: tag in t.split("|"))
                      for tag in (*self.S.TAGS, self.S.NONE_TAG)}
            # Complement of D: the ward name does not exist in both systems of the province.
            groups["NOT_D"] = ~groups["D"]
            groups["C_AND_D"] = groups["C"] & groups["D"]
            groups["C_NOT_D"] = groups["C"] & ~groups["D"]
        else:
            top = [name for name, _ in sorted(Counter(gold["province_new"]).items(), key=lambda kv: (-kv[1], kv[0]))[:5]]
            groups = {(name or "KHONG_XAC_DINH"): gold["province_new"] == name for name in top}
            groups["CON_LAI"] = ~gold["province_new"].isin(top)
        for value, selector in groups.items():
            part = gold[selector]
            for system in systems:
                base = {"system": system, "dataset": dataset, "breakdown": kind, "value": value, "n": len(part)}
                predictions = self.predictions.get((system, dataset))
                if predictions is None:
                    status = STATUS_DEFERRED if system == DYN_AUG else self.cell_status.get((system, dataset), STATUS_NOT_RUN)
                    rows.append({**base, "status": status})
                    continue
                if len(part) == 0:
                    rows.append({**base, "status": P.NOT_EVALUABLE_NO_SUPPORT})
                    continue
                metrics = P.t1_metrics(part["gold_system"].tolist(), [predictions[k] for k in part["key"]])
                lai = metrics["per_class"]["Lai"]
                rows.append({**base, "status": "OK", "correct": metrics["correct"], "accuracy": metrics["accuracy"],
                             "lai_support": lai["support"], "lai_tp": lai["tp"],
                             "lai_recall": lai["recall"] if lai["support"] else P.NOT_EVALUABLE_NO_SUPPORT,
                             "abstain_count": metrics["abstain_count"]})
    return rows


Run.breakdown_rows = breakdown_rows


def diagnostics(self) -> dict:
    P = self.P
    out = {}
    tables = []
    sources = {"dev": (self.records["dev"], self.dyn_dev, self.exclusions["dev"]),
               "test": (self.records["test"], list(self.frozen["PROPOSED-DYN"].values()), self.exclusions["test"])}
    for split, (gold, predictions, excluded) in sources.items():
        gold_ids = {r["sample_id"] for r in gold}
        result = P.diagnose_dyn(gold, predictions, [i for i in excluded if i in gold_ids])
        for row in result.pop("rows"):
            tables.append({"split": split, "sample_id": row["sample_id"], "gold": row["gold"], "argmax": row["argmax"],
                           "posterior_cu": row["posterior"]["cu"], "posterior_moi": row["posterior"]["moi"],
                           "posterior_lai": row["posterior"]["Lai"], "posterior_gold": row["posterior_gold"],
                           "confidence": row["confidence"], "margin_observed": row["margin_observed"],
                           "threshold": row["threshold"], "margin_required": row["margin_required"],
                           "passes_threshold": row["passes_threshold"], "passes_margin": row["passes_margin"],
                           "predicted_system": row["predicted_system"]})
        out[split] = result
    out["note"] = ("argmax_only is a diagnostic on data that was already observed (dev was used for selection, "
                   "test in Sprint 3); it is not a proposed configuration")
    return out, tables


Run.diagnostics = diagnostics


def save_predictions(self, path: Path, systems) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for system in systems:
            for dataset in DATASETS:
                predictions = self.predictions.get((system, dataset))
                if predictions is None:
                    continue
                for key in self.texts[dataset]["key"]:
                    stream.write(json.dumps({"dataset": dataset, "key": key, "system": system,
                                             "predicted_system": predictions[key]}, ensure_ascii=False) + "\n")
                    count += 1
    return count


Run.save_predictions = save_predictions


def score_all(self, systems, columns) -> tuple[list[dict], dict]:
    rows, detail = [], {}
    for system in systems:
        for column in columns:
            row = self.score_cell(system, column)
            detail[f"{system}|{column}"] = row.pop("_detail", {"status": row["status"]})
            rows.append(row)
    return rows, detail


Run.score_all = score_all


def tier1(args) -> int:
    out = args.output if args.output.is_absolute() else REPO / args.output
    sets_dir = args.sets if args.sets.is_absolute() else REPO / args.sets
    if out.exists():
        raise SystemExit(f"{out} already exists; refusing to overwrite. Use a _v2 directory.")
    run = Run(sets_dir, out, args.resamples)
    run.cell_status = {}
    run.load_sets()
    run.load_corpus()
    run.load_frozen()
    run.build_gold()
    (out / "tables").mkdir(parents=True)
    (out / "work").mkdir()
    run.declare("tier1")  # systems, rules and seeds are on disk before any scoring

    run.run_tier1_systems()

    # Inputs of tier 2 (text only) are saved even if the neural runtime never runs.
    tier2_inputs = out / "tier2_inputs"
    tier2_inputs.mkdir()
    listing = {}
    P = run.P
    for name, keys, texts in (
        ("t1_synth_train", run.sets["t1_synth_train"]["key"], run.sets["t1_synth_train"]["text"]),
        ("t1_synth_dev", run.sets["t1_synth_dev"]["key"], run.sets["t1_synth_dev"]["text"]),
        ("synth_eval", run.texts["synth_eval"]["key"], run.texts["synth_eval"]["text"]),
        ("data06", run.texts["data06"]["key"], run.texts["data06"]["text"]),
        ("s3_train", [r["sample_id"] for r in run.records["train"]], [r["text"] for r in run.records["train"]]),
        ("s3_dev", [r["sample_id"] for r in run.records["dev"]], [r["text"] for r in run.records["dev"]]),
        ("s3_test", run.texts["s3_test"]["key"], run.texts["s3_test"]["text"]),
    ):
        path = tier2_inputs / f"{name}.jsonl"
        write_text_inputs(path, list(keys), list(texts))
        listing[name] = {"rows": len(list(keys)), "sha256": sha256_file(path)}
    dump_json(tier2_inputs / "tier2_inputs.json", {
        "purpose": "text-only inputs of tier 2 (DYN inference, T1-PIPE-DYN/PCRF, T1-HEAD-PROBE CLS features)",
        "files": listing, "checkpoint": DYN_CHECKPOINT.as_posix(), "checkpoint_sha256": DYN_CHECKPOINT_SHA256})

    columns = list(COLUMNS) + list(EXTRA_COLUMNS)
    rows, detail = run.score_all(SYSTEM_ORDER, columns)
    diag, diag_rows = run.diagnostics()
    outputs = {}
    outputs["tables/h5_main.csv"] = write_csv(out / "tables" / "h5_main.csv",
                                              [r for r in rows if r["column"] in COLUMNS], H5_COLUMNS)
    outputs["tables/h5_synth_eval_adm_only.csv"] = write_csv(
        out / "tables" / "h5_synth_eval_adm_only.csv", [r for r in rows if r["column"] in EXTRA_COLUMNS], H5_COLUMNS)
    for kind in ("kieu_lai", "situation", "province"):
        name = f"tables/h5_by_{kind}.csv"
        outputs[name] = write_csv(out / name, run.breakdown_rows(SYSTEM_ORDER, kind), BREAKDOWN_COLUMNS)
    outputs["tables/dyn_diagnosis_samples.csv"] = write_csv(
        out / "tables" / "dyn_diagnosis_samples.csv", diag_rows, list(diag_rows[0]))
    gold_rows = [{"dataset": d, **r} for d in DATASETS for r in run.gold[d].to_dict("records")]
    outputs["tables/scoring_gold.csv"] = write_csv(
        out / "tables" / "scoring_gold.csv", gold_rows,
        ["dataset", "key", "gold_system", "cluster", "KieuLai", "province_new", "resolved_group", "unseen_group", "tags"])
    outputs["predictions.jsonl"] = {"rows": run.save_predictions(out / "predictions.jsonl", SYSTEM_ORDER)}
    dump_json(out / "dyn_diagnostics.json", diag)
    dump_json(out / "metrics.json", {
        "cells": detail, "notes": run.notes,
        "situation_counts": {d: dict(Counter(t for tags in run.gold[d]["tags"] for t in tags.split("|")))
                             for d in DATASETS},
        "class_counts": {d: dict(Counter(run.gold[d]["gold_system"])) for d in DATASETS},
    })
    for name in ("predictions.jsonl", "metrics.json", "dyn_diagnostics.json", *[n for n in outputs if n.startswith("tables/")]):
        outputs.setdefault(name, {})["sha256"] = sha256_file(out / name)
    run.manifest.update({
        "status": "TIER1_COMPLETE", "finished_at": now_iso(),
        "rows_in": {d: len(run.texts[d]) for d in DATASETS},
        "rows_scored": {c: len(run.column_frame(c)[1]) for c in columns},
        "outputs": outputs,
        "tier2": {"status": STATUS_NOT_RUN, "inputs": "tier2_inputs/tier2_inputs.json"},
    })
    dump_json(out / "run_manifest.json", run.manifest)
    print(json.dumps({"h5": [{k: r.get(k) for k in ("system", "column", "status", "n", "accuracy", "macro_f1",
                                                    "lai_recall", "lai_f1")} for r in rows if r["column"] in COLUMNS],
                      "notes": {k: v for k, v in run.notes.items() if k in (
                          "majority_class", "one_feature_rule", "pipe_rule_check_on_heur_spans", "s3_test_mask")}},
                     ensure_ascii=False, indent=1, default=str))
    return 0


def tier2(args) -> int:
    """Score the neural outputs written by scripts/68b into ``<run>/tier2/``."""
    import numpy as np

    out = args.output if args.output.is_absolute() else REPO / args.output
    sets_dir = args.sets if args.sets.is_absolute() else REPO / args.sets
    tier2_dir = out / "tier2"
    status_path = tier2_dir / "status.json"
    if not status_path.exists():
        raise SystemExit(f"{status_path} is missing; run scripts/68b_run_t1_neural_local.py first")
    done = out / "tables" / "h5_main_tier2.csv"
    if done.exists():
        raise SystemExit(f"{done} already exists; refusing to overwrite tier-2 results")
    status = json.loads(status_path.read_text(encoding="utf-8"))
    manifest = json.loads((out / "run_manifest.json").read_text(encoding="utf-8"))

    run = Run(sets_dir, out, int(manifest["n_resamples"]))
    run.cell_status = {}
    run.load_sets()
    run.load_corpus()
    run.load_frozen()
    run.build_gold()
    P = run.P
    # Tier-1 predictions are read back unchanged (HEUR-JW is the paired reference).
    for row in P.read_jsonl(out / "predictions.jsonl"):
        run.predictions.setdefault((row["system"], row["dataset"]), {})[row["key"]] = row["predicted_system"]

    neural_systems = (DYN, PIPE_PCRF, PIPE_DYN, PROBE)
    tier2_notes = {"smoke": status.get("smoke"), "status": status["status"]}
    if status["status"] != "SMOKE_PASS":
        for system in neural_systems:
            for dataset in DATASETS:
                if (system, dataset) not in run.predictions:
                    run.cell_status[(system, dataset)] = STATUS_BLOCKED
    else:
        heur = P.load_locked_heur(REPO)
        for model, system_t1, system_pipe in (("dyn", DYN, PIPE_DYN), ("pcrf", None, PIPE_PCRF)):
            path = tier2_dir / f"{model}_predictions.jsonl"
            if not path.exists():
                tier2_notes[f"{model}_predictions"] = STATUS_NOT_RUN
                continue
            tier2_notes[f"{model}_predictions_sha256"] = sha256_file(path)
            by_dataset: dict[str, dict[str, dict]] = {}
            for row in P.read_jsonl(path):
                by_dataset.setdefault(row["dataset"], {})[row["key"]] = row
            for dataset in ("synth_eval", "data06"):
                rows = by_dataset.get(dataset)
                if rows is None:
                    continue
                frame = run.texts[dataset]
                keys, texts = frame["key"].tolist(), P.inference_texts(frame)
                if system_t1:
                    run.set_predictions(system_t1, dataset, keys, [rows[k]["predicted_system"] for k in keys])
                run.set_predictions(system_pipe, dataset, keys,
                                    [P.pipe_predict(heur, t, rows[k]["spans"])[0] for k, t in zip(keys, texts)])
        # T1-HEAD-PROBE: linear probe on frozen CLS vectors.
        def cls(name):
            meta = json.loads((tier2_dir / f"cls_{name}.keys.json").read_text(encoding="utf-8"))
            return meta["keys"], np.load(tier2_dir / f"cls_{name}.npy"), np.asarray(meta["valid"], dtype=bool)

        if (tier2_dir / "cls_t1_synth_train.npy").exists():
            train, dev = run.sets["t1_synth_train"], run.sets["t1_synth_dev"]
            k_train, x_train, v_train = cls("t1_synth_train")
            k_dev, x_dev, v_dev = cls("t1_synth_dev")
            k_s3, x_s3, v_s3 = cls("s3_train")
            if k_train != train["key"].tolist() or k_dev != dev["key"].tolist():
                raise ValueError("CLS feature keys do not match the synthetic sets")
            s3_label = {r["sample_id"]: r.get("address_system") for r in run.records["train"]}
            s3_rows = [i for i, k in enumerate(k_s3) if s3_label[k] in P.CLASSES and v_s3[i]]
            train_rows = [i for i in range(len(k_train)) if v_train[i]]
            dev_rows = [i for i in range(len(k_dev)) if v_dev[i]]
            x_fit = np.vstack([x_train[train_rows], x_s3[s3_rows]])
            y_fit = ([P.CLASSES.index(train["gold_system"].iloc[i]) for i in train_rows]
                     + [P.CLASSES.index(s3_label[k_s3[i]]) for i in s3_rows])
            y_dev = [P.CLASSES.index(dev["gold_system"].iloc[i]) for i in dev_rows]
            model, l2, trials = P.select_l2(x_fit, y_fit, x_dev[dev_rows], y_dev, seed=P.CLASSIFIER_SEED,
                                            standardize=True)
            tier2_notes["probe_selection"] = {
                "selected_l2": l2, "trials": trials, "feature_dim": int(x_fit.shape[1]),
                "train_rows_synth": len(train_rows), "train_rows_sprint3": len(s3_rows), "dev_rows": len(dev_rows),
                "rows_without_cls": {"train": int((~v_train).sum()), "dev": int((~v_dev).sum()),
                                     "s3_train": int((~v_s3).sum())},
                "train_class_counts": dict(Counter(P.CLASSES[i] for i in y_fit))}
            for dataset in DATASETS:
                keys, matrix, valid = cls(dataset)
                if keys != run.texts[dataset]["key"].tolist():
                    raise ValueError(f"CLS feature keys do not match {dataset}")
                # A text rejected by the processor has no CLS vector: the probe abstains.
                labels = [P.CLASSES[i] if ok else P.ABSTAIN for i, ok in zip(model.predict(matrix), valid)]
                run.set_predictions(PROBE, dataset, keys, labels)
                tier2_notes.setdefault("probe_rows_without_cls", {})[dataset] = int((~valid).sum())
        else:
            tier2_notes["probe"] = STATUS_NOT_RUN

    columns = list(COLUMNS) + list(EXTRA_COLUMNS)
    rows, detail = run.score_all(neural_systems, columns)
    tables = out / "tables"
    outputs = {"tables/h5_main_tier2.csv": write_csv(done, [r for r in rows if r["column"] in COLUMNS], H5_COLUMNS)}
    # Combined table: tier-1 rows, with the neural rows replaced by their tier-2 values.
    with (tables / "h5_main.csv").open(encoding="utf-8-sig", newline="") as stream:
        tier1_rows = list(csv.DictReader(stream))
    replaced = {(r["system"], r["column"]): r for r in rows if r["column"] in COLUMNS}
    combined = []
    for row in tier1_rows:
        new = replaced.get((row["system"], row["column"]))
        combined.append(new if new is not None and row["status"] != "OK" else row)
    outputs["tables/h5_main_combined.csv"] = write_csv(tables / "h5_main_combined.csv", combined, H5_COLUMNS)
    outputs["tables/h5_synth_eval_adm_only_tier2.csv"] = write_csv(
        tables / "h5_synth_eval_adm_only_tier2.csv", [r for r in rows if r["column"] in EXTRA_COLUMNS], H5_COLUMNS)
    for kind in ("kieu_lai", "situation", "province"):
        name = f"tables/h5_by_{kind}_tier2.csv"
        outputs[name] = write_csv(out / name, run.breakdown_rows(neural_systems, kind), BREAKDOWN_COLUMNS)
    count = 0
    with (tier2_dir / "predictions_tier2.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
        for system in neural_systems:
            for dataset in DATASETS:
                if dataset == "s3_test" and system != PROBE:
                    continue  # already in the tier-1 predictions file
                for key, label in (run.predictions.get((system, dataset)) or {}).items():
                    stream.write(json.dumps({"dataset": dataset, "key": key, "system": system,
                                             "predicted_system": label}, ensure_ascii=False) + "\n")
                    count += 1
    outputs["tier2/predictions_tier2.jsonl"] = {"rows": count}
    dump_json(tier2_dir / "metrics_tier2.json", {"cells": detail, "notes": tier2_notes})
    for name in list(outputs) + ["tier2/metrics_tier2.json"]:
        outputs.setdefault(name, {})["sha256"] = sha256_file(out / name)
    manifest["tier2"] = {"status": status["status"], "scored_at": now_iso(), "outputs": outputs,
                         "status_file_sha256": sha256_file(status_path),
                         "code_sha256": {name: sha256_file(REPO / name) for name in SOURCE_FILES if (REPO / name).exists()}}
    manifest["status"] = "TIER1_AND_TIER2_COMPLETE" if status["status"] == "SMOKE_PASS" else "TIER1_COMPLETE_TIER2_BLOCKED"
    dump_json(out / "run_manifest.json", manifest)
    print(json.dumps([{k: r.get(k) for k in ("system", "column", "status", "n", "accuracy", "macro_f1", "lai_recall",
                                             "lai_f1")} for r in rows if r["column"] in COLUMNS],
                     ensure_ascii=False, indent=1, default=str))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("tier1", "tier2"), default="tier1")
    parser.add_argument("--sets", type=Path, default=DEFAULT_SETS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--resamples", type=int, default=DEFAULT_RESAMPLES)
    parser.add_argument("--crf-worker", action="store_true")
    parser.add_argument("--worker-in", type=Path)
    parser.add_argument("--worker-out", type=Path)
    parser.add_argument("--repo", type=Path, default=REPO)
    args = parser.parse_args(argv)
    if args.crf_worker:
        crf_worker(args.repo, args.worker_in, args.worker_out)
        return 0
    return tier1(args) if args.stage == "tier1" else tier2(args)


if __name__ == "__main__":
    sys.exit(main())
