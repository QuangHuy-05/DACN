"""Versioned Colab notebooks and distinct final input/scoring bundles."""
import json
from pathlib import Path

from src.evaluation.dev_runner import ROOT, file_hash, read_jsonl, write_json
from src.data.test_corpus_release import APPROVED_STATUS
from src.modeling.colab_handoff import cell, notebook_content, write_archive


def training_notebook(code_archive, resource_archive):
    legacy = notebook_content(code_archive, resource_archive)
    cells = legacy["cells"][:5]
    cells[0] = cell("markdown", "# Sprint 3 — Colab train/dev v2\n"
        "Chỉ chứa train240/dev60. Chọn GPU, upload hai ZIP; kiểm hash trước khi cài. "
        "Notebook chưa thực thi; smoke và full training là hai cổng riêng. "
        "Không mount gói test vào workspace này trước khi chọn model bằng dev.\n")
    for item in cells:
        if item["cell_type"] == "code":
            source = "".join(item["source"])
            source = source.replace("dacn_train_dev_bundle_v1.zip", Path(code_archive["path"]).name)
            source = source.replace("dacn_phobert_resources_v1.zip", Path(resource_archive["path"]).name)
            if "archive.infolist()" in source:
                source = source.replace("    for entry in archive.infolist():", "    names = archive.namelist()\n"
                    "    if len(names) != len(set(names)):\n        raise RuntimeError('Duplicate ZIP member')\n"
                    "    manifest = json.loads(archive.read('code_bundle_manifest.json'))\n"
                    "    if set(names) != set(manifest['files']) | {'code_bundle_manifest.json'}:\n"
                    "        raise RuntimeError('Unexpected ZIP member')\n    for entry in archive.infolist():")
            item["source"] = source.splitlines(keepends=True)
    cells += [cell("code", '''# CPU data preparation checks the three source dependencies, without loading a model.
PREPARED = "data/interim/modeling/sprint03/colab_closure_run001"
subprocess.run([PY, "-m", "scripts.30_prepare_model_training_data", "prepare", "--output-dir", PREPARED], check=True)
# GPU preflight and 300-sample real tokenizer alignment. A new directory is required.
PREFLIGHT = "data/interim/modeling/sprint03/colab_preflight_run001"
subprocess.run([PY, "-m", "scripts.58_colab_runtime", "preflight", "--output-dir", PREFLIGHT], check=True)
'''), cell("code", '''# One optimizer step per pretrained model on train only; checkpoints are smoke-only.
ENABLE_PRETRAINED_GPU_SMOKE = False
SMOKE = "data/interim/modeling/sprint03/colab_smoke_run001"
if ENABLE_PRETRAINED_GPU_SMOKE:
    subprocess.run([PY, "-m", "scripts.58_colab_runtime", "smoke", "--output-dir", SMOKE], check=True)
else:
    print("GPU smoke NOT_EXECUTED; full training remains blocked")
'''), cell("code", '''# Full runs use c01 and c02 separately; smoke weights are never resumed as training.
if ENABLE_NEURAL_TRAINING:
    if BACKUP_DIRECTORY is None:
        raise RuntimeError("Configure a persistent backup outside ephemeral /content")
    from src.modeling.colab_runtime import validate_smoke_evidence
    validate_smoke_evidence(Path(SMOKE) / "smoke_report.json")
    for MODEL in ("PHOBERT-CRF", "PROPOSED-DYN"):
        for CANDIDATE in ("c01", "c02"):
            RUN_ID = "colab_run001_" + MODEL.lower().replace("-", "_") + "_" + CANDIDATE
            RUN = Path("data/processed/evaluation/sprint03") / RUN_ID
            CHECKPOINT = RUN / "checkpoints/best.pt"
            subprocess.run([PY, "-m", "scripts.58_colab_runtime", "train", "--model", MODEL,
                "--candidate", CANDIDATE, "--output-dir", str(RUN), "--smoke-evidence", SMOKE + "/smoke_report.json",
                "--backup-directory", str(BACKUP_DIRECTORY), "--enable-neural-training"], check=True)
else:
    print("Full training NOT_EXECUTED")
'''), cell("code", '''# Only completed dev artifacts can create a final selection lock.
if ENABLE_NEURAL_TRAINING:
    for MODEL in ("PHOBERT-CRF", "PROPOSED-DYN"):
        PREFIX = "colab_run001_" + MODEL.lower().replace("-", "_")
        DEV_RUNS = ["data/processed/evaluation/sprint03/" + PREFIX + "_" + c + "_dev" for c in ("c01", "c02")]
        SELECTION = "data/interim/modeling/sprint03/" + PREFIX + "_selection"
        subprocess.run([PY, "-m", "scripts.58_colab_runtime", "select", "--model", MODEL,
            "--dev-runs", *DEV_RUNS, "--output-dir", SELECTION], check=True)
        from src.modeling.colab_runtime import backup_run
        backup_run(Path(SELECTION), BACKUP_DIRECTORY)
'''), cell("markdown", "## Deepparse — gate riêng\n"
        "DP-ZS-FT/DP-FT-FT chưa có active checkpoint license/hash lock. Không tự tải hoặc thay FastText. "
        "Sau khi nguồn đủ bằng chứng: script47 tạo DP-ZS config, scripts23/24 infer/score dev; "
        "script31 preflight → prepare → train c01/c02 → infer riêng → score dev. "
        "Native DP resume hiện là weights restart, không phải optimizer/RNG resume.\n\n"
        "## Resume và bàn giao\nPhoBERT/proposed: script58 train có `--resume-from <last.pt>` vào run mới, "
        "giữ candidate/resources/profile. best/last lưu optimizer/scheduler/RNG; backup định kỳ 300s và checksum cuối. "
        "Người chạy cấp quyền Drive nếu sử dụng; notebook không tự mount. "
        "Chỉ sau dev locks mới mở notebook final test riêng. Stability seeds chưa chạy: NOT_EXECUTED.\n")]
    return {**legacy, "cells": cells}


def final_notebook():
    return {"nbformat": 4, "nbformat_minor": 5, "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}}, "cells": [
        cell("markdown", "# Sprint 3 — final test riêng\n"
             "Chỉ mở sau khi chọn model trên dev và khóa đủ resources/code/checkpoint. "
             "Dùng runtime đã chuẩn bị trong notebook train/dev; không train ở đây. "
             "Gold ZIP chỉ giải nén tại cell scorer sau khi predictions đã đóng băng.\n"),
        cell("code", '''from pathlib import Path
import json, subprocess, os, sys
ROOT = Path("/content/DACN")
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
from src.modeling.colab_handoff import safe_extract
from src.evaluation.dev_runner import file_hash
PY = str(ROOT / ".venv_colab311/bin/python")
ENABLE_FINAL_TEST = False
HANDOFF = Path("/content/final_evaluation_manifest.json")
CONFIG = Path("data/interim/modeling/sprint03/CHOSEN_selection/final_model_config.json")
SELECTION = CONFIG.with_name("selection_lock.json")
RUN = Path("data/processed/evaluation/sprint03/CHOSEN_final_test_run001")
BACKUP_DIRECTORY = None  # persistent directory configured before final execution
'''), cell("code", '''# Input-only bundle; no gold is opened in preflight or inference.
if ENABLE_FINAL_TEST:
    if BACKUP_DIRECTORY is None:
        raise RuntimeError("Configure a persistent backup before final execution")
    handoff = json.loads(HANDOFF.read_text())
    if handoff["status"] != "FINAL_EVALUATION_BUNDLES_READY":
        raise RuntimeError("Test gold release pending")
    INPUT_ZIP = Path("/content") / Path(handoff["input_archive"]["path"]).name
    safe_extract(INPUT_ZIP, ROOT, handoff["input_archive"]["sha256"], "test_input_bundle_manifest.json")
    CORPUS = Path(handoff["corpus_path"])
    COMMON = ["--input", str(CORPUS / "test_input.jsonl"), "--corpus-manifest", str(CORPUS / "manifest.json"),
              "--model-config", str(CONFIG), "--selection-lock", str(SELECTION)]
    subprocess.run([PY, "-m", "scripts.55_run_span_test", "preflight"] + COMMON, check=True)
    subprocess.run([PY, "-m", "scripts.55_run_span_test", "infer", "--output-dir", str(RUN),
                    "--execute-final-test"] + COMMON, check=True)
'''), cell("code", '''# Predictions and their manifest already exist; only now is scorer gold extracted.
if ENABLE_FINAL_TEST:
    if not (RUN / "run_manifest.json").is_file():
        raise RuntimeError("Freeze prediction before opening gold")
    GOLD_ZIP = Path("/content") / Path(handoff["gold_archive"]["path"]).name
    safe_extract(GOLD_ZIP, ROOT, handoff["gold_archive"]["sha256"], "test_gold_bundle_manifest.json")
    subprocess.run([PY, "-m", "scripts.56_score_span_test", "--run-dir", str(RUN),
        "--gold", str(CORPUS / "test_benchmark_t0.jsonl"), "--input", str(CORPUS / "test_input.jsonl"),
        "--corpus-manifest", str(CORPUS / "manifest.json"), "--execute-final-test"], check=True)
    from src.modeling.colab_runtime import backup_run
    backup_run(RUN, BACKUP_DIRECTORY)
'''), cell("markdown", "Mỗi model/run mới dùng lock đã chốt trên dev. "
             "Ablation dùng config/lock cùng checkpoint của proposed. Không đổi mapping/threshold sau xem test. "
             "5 trường báo track riêng; fixture và smoke không được đưa vào bảng kết quả pretrained.\n")]}


def build_final_bundles(corpus_dir, output_dir):
    corpus_dir, output_dir = Path(corpus_dir).resolve(), Path(output_dir).resolve()
    if output_dir.exists():
        raise FileExistsError(output_dir)
    manifest = json.loads((corpus_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("status") != APPROVED_STATUS or manifest["sample_counts"] != {"train": 240, "dev": 60, "test": 100}:
        raise ValueError("PENDING_TEST_GOLD")
    for name, digest in manifest["output_sha256"].items():
        if file_hash(corpus_dir / name) != digest:
            raise ValueError("TEST_RELEASE_ARTIFACT_CHANGED")
    inputs = read_jsonl(corpus_dir / "test_input.jsonl")
    if len(inputs) != 100 or any(set(row) != {"sample_id", "text"} for row in inputs):
        raise ValueError("FINAL_INPUT_NOT_TEXT_ONLY_100")
    relative = corpus_dir.relative_to(ROOT).as_posix()
    output_dir.mkdir(parents=True)
    input_archive = write_archive(output_dir / "dacn_final_test_input_v1.zip",
        {relative + "/" + name: corpus_dir / name for name in ("test_input.jsonl", "manifest.json")},
        {"scope": "100 input text-only and hash manifest; no gold"}, "test_input_bundle_manifest.json")
    gold_archive = write_archive(output_dir / "dacn_final_test_gold_scorer_only_v1.zip",
        {relative + "/" + name: corpus_dir / name for name in ("test_benchmark_t0.jsonl", "identity_registry.jsonl")},
        {"scope": "scorer only after prediction freeze; never mount during training"}, "test_gold_bundle_manifest.json")
    result = {"status": "FINAL_EVALUATION_BUNDLES_READY", "corpus_path": relative,
              "input_archive": input_archive, "gold_archive": gold_archive, "test_inference_scoring": "NOT_EXECUTED"}
    write_json(output_dir / "final_evaluation_manifest.json", result)
    return result
