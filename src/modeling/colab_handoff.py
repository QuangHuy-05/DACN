"""Build/check explicit train/dev bundles; no test tasks, neural load or training."""

import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import zipfile

from src.evaluation.dev_runner import ROOT, file_hash, write_json
from src.modeling.datasets import load_corpus
from src.modeling.resources import validate_resource_lock

TRAIN_DEPENDENCIES = (
    "data/interim/annotation/sprint03/reannotation_v2_release1/trace.jsonl",
    "data/interim/annotation/sprint03/reannotation_v2_release1/generation_manifest.json",
    "data/interim/annotation/sprint03/annotation_queue_batch02_train_dev.csv",
)


def _safe_name(name):
    path = PurePosixPath(name)
    return bool(name) and "\\" not in name and ":" not in name and not path.is_absolute() and ".." not in path.parts


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_MANIFEST_KEY")
        result[key] = value
    return result


def _stream_hash(stream):
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def check_bundle(directory, manifest_name="code_bundle_manifest.json"):
    manifest = json.loads((directory / manifest_name).read_text())
    for name, digest in manifest["files"].items():
        path = (directory / name).resolve()
        if not path.is_relative_to(directory.resolve()) or not path.is_file() or file_hash(path) != digest:
            raise ValueError("BUNDLE_HASH_MISMATCH:" + name)
    return {"status": "BUNDLE_HASH_PASS", "files": len(manifest["files"]), "scope": manifest["scope"]}


def safe_extract(archive, destination, expected_sha256, manifest_name="code_bundle_manifest.json"):
    if file_hash(archive) != expected_sha256:
        raise ValueError("ARCHIVE_HASH_MISMATCH")
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as stream:
        names = [entry.filename for entry in stream.infolist()]
        if len(set(names)) != len(names):
            raise ValueError("DUPLICATE_ZIP_MEMBER")
        for entry in stream.infolist():
            target = (destination / entry.filename).resolve()
            if not _safe_name(entry.filename) or not target.is_relative_to(destination.resolve()):
                raise ValueError("UNSAFE_ARCHIVE_PATH")
            if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("ARCHIVE_SYMLINK_FORBIDDEN")
            if target.exists():
                if target.is_dir() and entry.is_dir():
                    continue
                if target.is_file():
                    with stream.open(entry) as member:
                        if file_hash(target) == _stream_hash(member):
                            continue
                raise FileExistsError(target)
        if not _safe_name(manifest_name) or manifest_name not in names:
            raise ValueError("ARCHIVE_MANIFEST_MISSING_OR_UNSAFE")
        manifest = json.loads(stream.read(manifest_name), object_pairs_hook=_unique_object)
        members = {entry.filename for entry in stream.infolist() if not entry.is_dir()}
        if members != set(manifest["files"]) | {manifest_name} or manifest_name in manifest["files"]:
            raise ValueError("ARCHIVE_ALLOWLIST_MISMATCH")
        for name, digest in manifest["files"].items():
            with stream.open(name) as member:
                if _stream_hash(member) != digest:
                    raise ValueError("ARCHIVE_MEMBER_HASH_MISMATCH")
        stream.extractall(destination)
        for entry in stream.infolist():
            if not entry.is_dir():
                mode = (entry.external_attr >> 16) & 0o777
                if mode:
                    (destination / entry.filename).chmod(mode)
    return check_bundle(destination, manifest_name)


def write_archive(path, files, extra, manifest_name="code_bundle_manifest.json", *, allow_source_symlinks=False):
    if path.exists():
        raise FileExistsError(path)
    if not _safe_name(manifest_name) or manifest_name in files or any(not _safe_name(name) for name in files):
        raise ValueError("UNSAFE_OR_COLLIDING_ARCHIVE_MEMBER")
    if any(not source.is_file() or (source.is_symlink() and (
            not allow_source_symlinks or not source.resolve().is_relative_to(ROOT.resolve()))) for source in files.values()):
        raise ValueError("ARCHIVE_SOURCE_MISSING_OR_SYMLINK")
    manifest = {"version": "s3-colab-bundle-v1", **extra,
                "files": {relative: file_hash(source) for relative, source in files.items()}}
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as stream:
        for relative, source in files.items():
            stream.write(source, relative)
        stream.writestr(manifest_name, json.dumps(manifest, ensure_ascii=False, indent=2))
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": file_hash(path), "bytes": path.stat().st_size,
            "uncompressed_bytes": sum(source.stat().st_size for source in files.values()), "files": len(files)}


def cell(kind, source):
    result = {"cell_type": kind, "metadata": {}, "source": source.splitlines(keepends=True)}
    if kind == "code":
        ast.parse(source)
        result.update(execution_count=None, outputs=[])
    return result


def notebook_content(code_archive, resource_archive):
    cells = [cell("markdown", "# DACN Sprint 3: train/dev only\nNotebook đã chuẩn bị; chưa thực thi Colab. Không có 100 test hoặc đáp án test.\nUpload hai ZIP được chủ dự án bàn giao. Chọn GPU rồi chạy các cell chuẩn bị. Huấn luyện mặc định tắt.\n"),
        cell("code", f'''from pathlib import Path
import hashlib, json, os, subprocess, sys, zipfile
ROOT = Path("/content/DACN")
CODE_ZIP = Path("/content/dacn_train_dev_bundle_v1.zip")
RESOURCE_ZIP = Path("/content/dacn_phobert_resources_v1.zip")
CODE_SHA256 = {code_archive['sha256']!r}
RESOURCE_SHA256 = {resource_archive['sha256']!r}
ENABLE_NEURAL_TRAINING = False
ENABLE_DP_ZERO_SHOT = False
DP_RESOURCE_LOCK = None  # cleared real full FastText + checkpoint lock, not a template
MODEL = "PHOBERT-CRF"  # or PROPOSED-DYN; DP waits for a cleared active lock
CANDIDATE = "c01"
RUN_ID = "phobert_crf_colab_run001_c01"  # change for every run
BACKUP_DIRECTORY = None  # choose a persistent directory; grant Drive access yourself if used
'''),
        cell("code", '''# Verify and extract the code bundle before importing its helper.
if hashlib.sha256(CODE_ZIP.read_bytes()).hexdigest() != CODE_SHA256:
    raise RuntimeError("Code ZIP checksum mismatch")
ROOT.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(CODE_ZIP) as archive:
    for entry in archive.infolist():
        target = (ROOT / entry.filename).resolve()
        if "\\\\" in entry.filename or not target.is_relative_to(ROOT.resolve()):
            raise RuntimeError("Unsafe ZIP path")
        if (entry.external_attr >> 16) & 0o170000 == 0o120000:
            raise RuntimeError("ZIP symlink forbidden")
        if target.exists() and target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() != hashlib.sha256(archive.read(entry)).hexdigest():
            raise RuntimeError("Existing file differs; use a new workspace")
    archive.extractall(ROOT)
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
from src.modeling.colab_handoff import check_bundle, safe_extract
from src.evaluation.dev_runner import file_hash
print(check_bundle(ROOT))
safe_extract(RESOURCE_ZIP, ROOT, RESOURCE_SHA256, "resource_bundle_manifest.json")
print("Two verified bundles extracted; test not included")
'''),
        cell("code", '''import platform, shutil
print({"python": platform.python_version(), "disk_free_bytes": shutil.disk_usage(ROOT).free})
print({"os": platform.platform(), "cpu_count": os.cpu_count()})
print(Path("/proc/meminfo").read_text().splitlines()[:5])
subprocess.run(["nvidia-smi"], check=False)
if shutil.disk_usage(ROOT).free < 20 * 1024**3:
    raise RuntimeError("Need at least 20 GiB free before bootstrap/training; choose another runtime")
CACHE = ROOT / "data/interim/modeling/sprint03/colab_cache_v1"
CACHE.mkdir(parents=True, exist_ok=True)
for name in ("TMPDIR", "TEMP", "TMP", "PIP_CACHE_DIR", "UV_CACHE_DIR", "XDG_CACHE_HOME", "HF_HOME", "TORCH_HOME"):
    directory = CACHE / name.lower()
    directory.mkdir(exist_ok=True)
    os.environ[name] = str(directory)
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["PYTHONNOUSERSITE"] = "1"
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
# The pinned profile requires an isolated Python 3.11, independent of kernel version.
UV = ROOT / ".bootstrap_uv/bin/uv"
if not UV.exists():
    subprocess.run([sys.executable, "-m", "pip", "install", "--target", str(ROOT / ".bootstrap_uv"), "uv==0.8.22"], check=True)
os.environ["UV_PYTHON_INSTALL_DIR"] = str(ROOT / ".managed_python")
ENV = ROOT / ".venv_colab311"
if not (ENV / "bin/python").exists():
    subprocess.run([str(UV), "venv", "--python", "3.11", str(ENV), "--seed"], check=True)
PY = str(ENV / "bin/python")
subprocess.run([PY, "--version"], check=True)
subprocess.run([PY, "-m", "pip", "install", "torch==2.8.0", "--index-url", "https://download.pytorch.org/whl/cu128"], check=True)
subprocess.run([PY, "-m", "pip", "install", "-r", "configs/colab/sprint03/requirements_transitive_v1.txt"], check=True)
LOCK = ROOT / "data/interim/modeling/sprint03/task_01_06_20261003_v1/resource_lock_local_v1.json"
lock = json.loads(LOCK.read_text())
JAVA_HOME = ROOT / lock["java"]["path"]
(JAVA_HOME / "bin/java").chmod(0o755)
os.environ["JAVA_HOME"] = str(JAVA_HOME)
os.environ["PATH"] = str(JAVA_HOME / "bin") + os.pathsep + os.environ["PATH"]
os.environ["JAVA_TOOL_OPTIONS"] = "-Djava.io.tmpdir=" + str(CACHE / "tmpdir") + " -XX:-UsePerfData"
'''),
        cell("markdown", "## Resource gates\nPhoBERT resources đã có trong ZIP với revision/hash/license. DP chưa có active lock: checkpoint license và full FastText còn pending. Không tự tải DP hoặc thay bằng embedding khác. RAM hệ thống cần ít nhất 10 GiB cho full FastText; GPU VRAM không thay được RAM này. Training PhoBERT cần 20 GiB đĩa trống/run và profile GPU ít nhất 8 GiB VRAM.\n"),
        cell("code", '''MODULES = {"PHOBERT-CRF": "scripts.32_train_phobert_crf", "PROPOSED-DYN": "scripts.33_train_proposed_dynamic", "DP-FT-FT": "scripts.31_train_deepparse_finetuned"}
PROFILE = "configs/colab/sprint03/cuda128_profile_v1.json"
if MODEL == "DP-FT-FT":
    if DP_RESOURCE_LOCK is None:
        raise RuntimeError("DP resource/license/native-integration gates pending; supply a separately cleared active lock")
    LOCK = ROOT / DP_RESOURCE_LOCK
if MODEL not in MODULES:
    raise RuntimeError("Unknown model")
COMMAND = [PY, "-m", MODULES[MODEL]]
COMMON = ["--resources", str(LOCK), "--hardware-profile", PROFILE, "--candidate", CANDIDATE]
if MODEL == "DP-FT-FT":
    COMMON = ["--resources", str(LOCK), "--candidate", CANDIDATE]  # native pinned CPU profile
subprocess.run(COMMAND + ["preflight"] + COMMON, check=True)
PREPARED = "data/interim/modeling/sprint03/colab_prepared_run001"
subprocess.run(COMMAND + ["prepare", "--output-dir", PREPARED] + COMMON, check=True)
subprocess.run([PY, "-m", "scripts.34_audit_modeling_artifacts", "prepared", "--run-dir", PREPARED, "--output", "data/interim/modeling/sprint03/colab_prepared_audit_run001.json"], check=True)
'''),
        cell("code", '''RUN = Path("data/processed/evaluation/sprint03") / RUN_ID
def backup_run():
    if BACKUP_DIRECTORY is None:
        raise RuntimeError("Choose a persistent backup directory before training")
    destination = Path(BACKUP_DIRECTORY) / RUN_ID
    destination.mkdir(parents=True, exist_ok=True)
    for source in RUN.rglob("*"):
        if not source.is_file() or source.name.endswith(".tmp"):
            continue
        target = destination / source.relative_to(RUN)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if file_hash(source) != file_hash(target):
            raise RuntimeError("Backup checksum mismatch")
if ENABLE_NEURAL_TRAINING:
    import threading, time
    if BACKUP_DIRECTORY is None:
        raise RuntimeError("Configure backup before training")
    stop = threading.Event()
    def periodic_backup():
        while not stop.wait(300):
            try: backup_run()
            except Exception as error: print("Backup attention:", error)
    worker = threading.Thread(target=periodic_backup, daemon=True)
    worker.start()
    try:
        subprocess.run(COMMAND + ["train", "--output-dir", str(RUN), "--run-id", RUN_ID] + COMMON, check=True)
    finally:
        stop.set()
        worker.join(timeout=10)
        if RUN.exists(): backup_run()
else:
    print("Training disabled; prepared notebook is not a completed experiment")
'''),
        cell("code", '''# Separate prediction and scoring; no test100 cells.
if ENABLE_NEURAL_TRAINING:
    CHECKPOINT = RUN / "checkpoints/best.pt"
    DEV_RUN = Path("data/processed/evaluation/sprint03") / (RUN_ID + "_dev")
    subprocess.run(COMMAND + ["infer", "--checkpoint", str(CHECKPOINT), "--output-dir", str(DEV_RUN), "--inference-only"] + COMMON, check=True)
    subprocess.run(COMMAND + ["score", "--source-run", str(DEV_RUN)] + COMMON, check=True)
    subprocess.run([PY, "-m", "scripts.34_audit_modeling_artifacts", "run", "--run-dir", str(DEV_RUN), "--output", "data/interim/modeling/sprint03/" + RUN_ID + "_audit.json"], check=True)
    if MODEL == "PROPOSED-DYN":
        CAL = "data/interim/modeling/sprint03/" + RUN_ID + "_calibration"
        subprocess.run(COMMAND + ["calibrate", "--source-run", str(DEV_RUN), "--output-dir", CAL] + COMMON, check=True)
        # The same checkpoint is reused for both constraint-on and constraint-off.
        for variant in ("proposed_dyn_v1.json", "proposed_no_constraint_v1.json"):
            target = str(DEV_RUN) + "_" + variant.removesuffix(".json")
            subprocess.run(COMMAND + ["infer", "--config", "configs/modeling/sprint03/" + variant, "--checkpoint", str(CHECKPOINT), "--decoder-policy", CAL + "/decoder_policy.json", "--output-dir", target, "--inference-only"] + COMMON, check=True)
            subprocess.run(COMMAND + ["score", "--config", "configs/modeling/sprint03/" + variant, "--source-run", target] + COMMON, check=True)
    backup_run()
'''),
        cell("code", '''# Future native zero-shot only; disabled until a real cleared DP lock exists.
if ENABLE_DP_ZERO_SHOT:
    if DP_RESOURCE_LOCK is None:
        raise RuntimeError("Full native embedding/checkpoint license/hash/RAM gates pending")
    DP_ID = "dp_zs_ft_colab_run001"  # choose a new ID each time
    DP_CONFIG = "data/interim/modeling/sprint03/" + DP_ID + "_config.json"
    DP_RUN = "data/processed/evaluation/sprint03/" + DP_ID
    subprocess.run([PY, "-m", "scripts.47_prepare_dp_zero_shot_config", "--resources", DP_RESOURCE_LOCK, "--run-id", DP_ID, "--output", DP_CONFIG], check=True)
    CORPUS = "data/processed/annotation/sprint03/corpus_train_dev_v2/"
    subprocess.run([PY, "-m", "scripts.23_run_span_dev", "--input", CORPUS + "dev_input.jsonl", "--corpus-manifest", CORPUS + "manifest.json", "--model-config", DP_CONFIG, "--output-dir", DP_RUN], check=True)
    subprocess.run([PY, "-m", "scripts.24_score_span_dev", "--predictions", DP_RUN + "/predictions.jsonl", "--gold", CORPUS + "dev.jsonl", "--corpus-manifest", CORPUS + "manifest.json", "--run-dir", DP_RUN], check=True)
else:
    print("DP-ZS-FT not executed; no active DP resources are included")
'''),
        cell("markdown", "## Bàn giao/resume\nMỗi c01/c02 dùng run mới; chỉ chọn bằng dev theo protocol. PhoBERT resume dùng `--resume-from <run trước/checkpoints/last.pt>` trong một run mới và cùng profile/resources; giữ optimizer/scheduler/RNG. DP chỉ có weights restart `--weights-from`; chưa chạy native full FastText nên đang chặn. DP-ZS-FT sẽ dùng scripts 23/24 với mapping cố định sau resource/API gates; chưa tạo config active vì thiếu lock thực.\nTải artifact về máy và kiểm checksum. Runtime có thể kết thúc; dữ liệu lưu trong /content không tự tồn tại ở phiên sau.\n")]
    return {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}}, "nbformat": 4, "nbformat_minor": 5}


def build_handoff(output_dir, notebook_path=None, version="v1"):
    output_dir = Path(output_dir)
    notebook = Path(notebook_path) if notebook_path else ROOT / "notebooks/sprint03/preflight_and_train_dev.ipynb"
    if not notebook.is_absolute():
        notebook = ROOT / notebook
    if not notebook.resolve().is_relative_to((ROOT / "notebooks/sprint03").resolve()):
        raise ValueError("NOTEBOOK_MUST_BE_IN_SPRINT03")
    if not version.replace("_", "").isalnum():
        raise ValueError("INVALID_BUNDLE_VERSION")
    if notebook.exists():
        raise FileExistsError(notebook)
    if output_dir.exists():
        raise FileExistsError(output_dir)
    output_dir.mkdir(parents=True)
    load_corpus(ROOT / "data/processed/annotation/sprint03/corpus_train_dev_v2")
    files = {}
    for folder in ("src", "scripts", "configs/modeling", "configs/colab", "configs/evaluation"):
        for path in (ROOT / folder).rglob("*"):
            if path.is_file() and path.suffix in (".py", ".json", ".txt"):
                files[path.relative_to(ROOT).as_posix()] = path
    for name in ("deepparse_native_mapping_v1.json", "requirements_sprint3_crf.txt"):
        path = ROOT / "configs" / name
        files[path.relative_to(ROOT).as_posix()] = path
    for path in (ROOT / "data/processed/annotation/sprint03/corpus_train_dev_v2").iterdir():
        if path.is_file():
            files[path.relative_to(ROOT).as_posix()] = path
    for relative in TRAIN_DEPENDENCIES:
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        files[relative] = path
    from src.modeling.datasets import prepare_data
    # This exact call verifies both dependency closure and their pinned hashes.
    prepare_data(ROOT / "data/processed/annotation/sprint03/corpus_train_dev_v2", output_dir / "source_preparation")
    lock_path = ROOT / "data/interim/modeling/sprint03/task_01_06_20261003_v1/resource_lock_local_v1.json"
    lock = validate_resource_lock(lock_path, "PHOBERT-CRF")
    files[lock_path.relative_to(ROOT).as_posix()] = lock_path
    for name in ("17_training_protocol_v1.md", "28_phobert_alignment_tone_relocation_20261003.md", "33_pre_colab_resource_inventory.md", "36_label100_and_colab_handoff.md"):
        path = ROOT / "docs/sprints/sprint_03" / name
        if not path.is_file():
            raise FileNotFoundError(path)
        files[path.relative_to(ROOT).as_posix()] = path
    code = write_archive(output_dir / ("dacn_train_dev_bundle_" + version + ".zip"), files, {"scope": "train240/dev60/code/config only; no test100/raw export/venv", "git_identity": "working tree file hashes; upload bundle rather than assuming HEAD includes dirty source"})
    resources = {}
    for entry in list(lock["components"].values()) + [lock["java"]]:
        for name, digest in entry["files"].items():
            path = ROOT / entry["path"] / name
            if file_hash(path) != digest:
                raise ValueError("RESOURCE_BUNDLE_HASH_MISMATCH")
            resources[path.relative_to(ROOT).as_posix()] = path
    resource = write_archive(output_dir / ("dacn_phobert_resources_" + version + ".zip"), resources,
                             {"scope": "declared PhoBERT MIT, VnCoreNLP GPL and JRE legal files; no FastText/DP weights or cache", "upstream_sources": lock},
                             "resource_bundle_manifest.json", allow_source_symlinks=True)
    notebook.parent.mkdir(parents=True, exist_ok=True)
    if version == "v1":
        content = notebook_content(code, resource)
    else:
        from src.modeling.colab_local_handoff import training_notebook
        content = training_notebook(code, resource)
    write_json(notebook, content)
    write_json(output_dir / "handoff_manifest.json", {"code_archive": code, "resource_archive": resource,
               "notebook": notebook.relative_to(ROOT).as_posix(), "notebook_sha256": file_hash(notebook),
               "colab_execution": "NOT_EXECUTED", "training": "NOT_EXECUTED", "test100": "NOT_INCLUDED_NOT_READ"})
    return {"code": code, "resources": resource, "notebook": notebook.relative_to(ROOT).as_posix()}
