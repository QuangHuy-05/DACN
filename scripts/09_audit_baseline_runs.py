"""Read-only audit of frozen baseline runs and their derived reports."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import types
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evaluation.schema import STANDARD_FIELDS, StandardPrediction, UNIFIED_SCHEMA_COLUMNS


BENCHMARK_NAMES = (
    "01_full_address_new_verified.csv",
    "02_raw_noisy_synthetic_1000.csv",
    "03_real_address_old_1500.csv",
    "04_missing_fields_800.csv",
    "06_hybrid_addresses_600.csv",
    "07_bidirectional_pairs_verified.csv",
)
PREDICTIONS_NAME = "baseline_predictions_unified.csv"
RAW_NAME = "baseline_raw_responses.jsonl"
MAPPING_NAME = "vietnam-sap-nhap-phuong-xa.csv"
DATA07_FIELDS = ("PhuongXa", "TinhThanh")
EXPECTED_TOOL_COUNTS = {
    "D01|libpostal": 1000,
    "D01|vietnamadminunits": 1000,
    "D02|libpostal": 2000,
    "D02|vietnamadminunits": 2000,
    "D03|libpostal": 1500,
    "D03|vietnamadminunits": 1500,
    "D04|libpostal": 800,
    "D04|vietnamadminunits": 800,
    "D06|libpostal": 600,
    "D06|vietnamadminunits": 1200,
    "D07|vietnamadminunits": 600,
}
METRIC_COLUMNS = (
    "n", "exact_correct", "exact_match_rate", "micro_mean_fuzzy_similarity",
    "fuzzy_scored_field_values", "macro_mean_field_fuzzy_similarity",
    "micro_f1_scored_fields", "macro_mean_field_f1",
)
FIELD_METRIC_COLUMNS = (
    "exact_correct", "exact_n", "exact_match_rate", "fuzzy_similarity_sum",
    "fuzzy_similarity_n", "mean_fuzzy_similarity",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evidence(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]], bool]:
    with path.open("rb") as stream:
        bom = stream.read(3) == b"\xef\xbb\xbf"
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = list(reader.fieldnames or [])
        rows = list(reader)
    return columns, rows, bom


def git_output(*args: str) -> bytes | None:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, check=False
    )
    return result.stdout if result.returncode == 0 else None


def source_snapshot(relative_path: str, expected_hash: str) -> tuple[bytes | None, str]:
    current_path = ROOT / relative_path
    if current_path.is_file():
        current = current_path.read_bytes()
        if hashlib.sha256(current).hexdigest() == expected_hash:
            return current, "working_tree"
    head = git_output("show", f"HEAD:{relative_path}")
    if head is not None and hashlib.sha256(head).hexdigest() == expected_hash:
        return head, "git:HEAD"
    revisions = git_output("rev-list", "--all", "--", relative_path)
    if revisions:
        for revision in revisions.decode("ascii").splitlines():
            blob = git_output("show", f"{revision}:{relative_path}")
            if blob is not None and hashlib.sha256(blob).hexdigest() == expected_hash:
                return blob, f"git:{revision}"
    return None, "snapshot_not_found"


def load_scorer(source: bytes, run_id: str) -> types.ModuleType:
    module = types.ModuleType(f"frozen_scorer_{run_id}")
    module.__file__ = f"<frozen:{run_id}:src/evaluation/scorer.py>"
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module


class RunAudit:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.run_dir = ROOT / "data" / "processed" / "evaluation" / "runs" / run_id
        self.checks: list[dict[str, Any]] = []
        self.metrics: list[dict[str, Any]] = []
        self.context: dict[str, Any] = {}

    def check(
        self,
        check_id: str,
        scope: str,
        expected: Any,
        actual: Any,
        path: Path,
        *,
        status: str | None = None,
        sample_ids: list[str] | None = None,
    ) -> None:
        self.checks.append({
            "id": check_id,
            "scope": scope,
            "expected": expected,
            "actual": actual,
            "status": status or ("pass" if actual == expected else "fail"),
            "evidence_path": evidence(path),
            "sample_ids": (sample_ids or [])[:5],
        })

    def finish(self) -> dict[str, Any]:
        core = [item for item in self.checks if item["scope"] == "core"]
        derived = [item for item in self.checks if item["scope"] == "derived"]
        if any(item["status"] == "fail" for item in core):
            decision = "FAIL"
        elif any(item["status"] == "unverifiable" for item in core):
            decision = "UNVERIFIABLE"
        elif any(item["status"] != "pass" for item in derived):
            decision = "PASS_CORE_ONLY"
        else:
            decision = "PASS"
        return {
            "run_id": self.run_id,
            "decision": decision,
            "checks": self.checks,
            "metrics": self.metrics,
            "context": self.context,
            "check_counts": dict(Counter(item["status"] for item in self.checks)),
        }


def expected_records(
    datasets: dict[str, list[dict[str, str]]],
    targets: dict[str, tuple[str, str]],
) -> dict[tuple[str, str], dict[str, Any]]:
    records: dict[tuple[str, str], dict[str, Any]] = {}

    def add(record_id: str, tool: str, address: str, truth: dict[str, str],
            scenario: str, mode: str | None, conditions: list[str],
            source_id: str) -> None:
        key = (record_id, tool)
        if key in records:
            raise ValueError(f"Duplicate expected key: {key}")
        records[key] = {
            "input": address,
            "truth": {name: truth.get(name, "") for name in STANDARD_FIELDS},
            "scenario": scenario,
            "mode": mode,
            "conditions": conditions,
            "source_id": source_id,
        }

    for index, row in enumerate(datasets[BENCHMARK_NAMES[0]]):
        record_id = f"D01_{index:04d}"
        truth = {name: row[name] for name in STANDARD_FIELDS}
        for tool in ("vietnamadminunits", "libpostal"):
            add(record_id, tool, row["ChuoiDiaChi"], truth, "NONE",
                "FROM_2025" if tool == "vietnamadminunits" else None,
                ["Data 01|all"], record_id)

    for index, row in enumerate(datasets[BENCHMARK_NAMES[1]]):
        base = f"D02_{row['ID']}"
        # Both surface variants are scored against the frozen GT_* fields.
        truth = {name: row[f"GT_{name}"] for name in STANDARD_FIELDS}
        mode = "FROM_2025" if row["HeQuyChieu"] == "moi" else "LEGACY"
        for suffix, column in (("noisy", "ChuoiDiaChi"), ("clean", "ChuoiDiaChiGoc")):
            for tool in ("vietnamadminunits", "libpostal"):
                add(f"{base}_{suffix}", tool, row[column], truth, "NONE",
                    mode if tool == "vietnamadminunits" else None,
                    [f"Data 02|{suffix}"], base)

    for index, row in enumerate(datasets[BENCHMARK_NAMES[2]]):
        record_id = f"D03_{index:04d}"
        truth = {name: row[name] for name in STANDARD_FIELDS}
        for tool in ("vietnamadminunits", "libpostal"):
            add(record_id, tool, row["ChuoiDiaChi"], truth, "NONE",
                "LEGACY" if tool == "vietnamadminunits" else None,
                ["Data 03|all"], record_id)

    for index, row in enumerate(datasets[BENCHMARK_NAMES[3]]):
        record_id = f"D04_{index:04d}"
        # Extraction uses fields still visible on the surface, not recovery GT_*.
        truth = {name: row[name] for name in STANDARD_FIELDS}
        mode = "FROM_2025" if row["HeQuyChieu"] == "moi" else "LEGACY"
        conditions = ["Data 04|surface_parse", f"Data 04|KieuThieu={row['KieuThieu']}"]
        for tool in ("vietnamadminunits", "libpostal"):
            add(record_id, tool, row["ChuoiDiaChi"], truth, "NONE",
                mode if tool == "vietnamadminunits" else None,
                conditions, record_id)

    for index, row in enumerate(datasets[BENCHMARK_NAMES[4]]):
        base = f"D06_{index:04d}"
        truth = {name: row[name] for name in STANDARD_FIELDS}
        kind_match = re.match(r"^(C[1-3])", row["KieuLai"])
        if not kind_match:
            raise ValueError(f"Unknown Data 06 KieuLai: {row['KieuLai']!r}")
        kind = kind_match.group(1)
        for suffix, tool, mode, condition in (
            ("_m25", "vietnamadminunits", "FROM_2025", "vn_from_2025"),
            ("_mleg", "vietnamadminunits", "LEGACY", "vn_legacy"),
            ("", "libpostal", None, "libpostal"),
        ):
            mode_name = mode or "single_parse"
            add(base + suffix, tool, row["ChuoiDiaChi"], truth, "C", mode,
                [f"Data 06|{condition}",
                 f"Data 06|KieuLai={kind}|mode={mode_name}"], base)

    for index, row in enumerate(datasets[BENCHMARK_NAMES[5]]):
        relation = row["QuanHe"]
        record_id = f"D07_{index:04d}_{relation}"
        # Resolve target identity by official code; never infer it from string splitting.
        code = row["MaPhuongXaMoi"].strip()
        if code not in targets:
            raise ValueError(f"Unknown Data 07 target code {code!r} at {record_id}")
        ward, province = targets[code]
        add(record_id, "vietnamadminunits", row["DiaChi_Cu"],
            {"PhuongXa": ward, "TinhThanh": province}, "A", "old_to_new",
            ["Data 07|old_to_new"], record_id)
    return records


def audit_inputs(audit: RunAudit, manifest: dict[str, Any]) -> tuple[dict, dict]:
    benchmark_dir = ROOT / "data" / "processed" / "benchmark"
    datasets: dict[str, list[dict[str, str]]] = {}
    mapping_path = ROOT / "data" / "reference" / "administrative_units" / MAPPING_NAME
    frozen_datasets = manifest.get("datasets", {})
    audit.check("DATASET_LIST", "core", list(BENCHMARK_NAMES),
                list(frozen_datasets), audit.run_dir / "run_manifest.json")
    for index, name in enumerate(BENCHMARK_NAMES, 1):
        path = benchmark_dir / name
        frozen = frozen_datasets.get(name, {})
        if not path.is_file():
            audit.check(f"INPUT_{index:02d}", "core", frozen, None, path,
                        status="unverifiable")
            continue
        try:
            columns, rows, bom = read_csv(path)
            datasets[name] = rows
            actual = {
                "sha256": sha256(path), "size_bytes": path.stat().st_size,
                "row_count": len(rows), "columns": columns, "utf8_bom": bom,
            }
            expected = {key: frozen.get(key) for key in ("sha256", "size_bytes", "row_count", "columns")}
            expected["utf8_bom"] = True
            audit.check(f"INPUT_{index:02d}", "core", expected, actual, path)
        except (OSError, UnicodeError, csv.Error) as exc:
            audit.check(f"INPUT_{index:02d}", "core", frozen, str(exc), path,
                        status="unverifiable")

    frozen_mapping = manifest.get("mapping_source", {})
    targets: dict[str, tuple[str, str]] = {}
    if mapping_path.is_file():
        columns, mapping_rows, bom = read_csv(mapping_path)
        actual = {
            "file_name": mapping_path.name,
            "sha256": sha256(mapping_path),
            "size_bytes": mapping_path.stat().st_size,
            "utf8_bom": bom,
        }
        expected = {key: frozen_mapping.get(key) for key in ("file_name", "sha256", "size_bytes")}
        expected["utf8_bom"] = True
        audit.check("MAPPING_SOURCE", "core", expected, actual, mapping_path)
        required = {"Mã phường/xã mới", "Phường/Xã mới (từ 1/7/2025)", "Tỉnh/TP mới"}
        audit.check("MAPPING_COLUMNS", "core", sorted(required),
                    sorted(required.intersection(columns)), mapping_path)
        conflicts = []
        if required.issubset(columns):
            for row in mapping_rows:
                code = row["Mã phường/xã mới"].strip()
                target = (row["Phường/Xã mới (từ 1/7/2025)"].strip(),
                          row["Tỉnh/TP mới"].strip())
                if not code or not all(target):
                    continue
                if code in targets and targets[code] != target:
                    conflicts.append(code)
                targets[code] = target
        audit.check("MAPPING_TARGET_CONFLICTS", "core", 0, len(conflicts),
                    mapping_path, sample_ids=conflicts)
    else:
        audit.check("MAPPING_SOURCE", "core", frozen_mapping, None, mapping_path,
                    status="unverifiable")

    if len(datasets) == len(BENCHMARK_NAMES) and targets:
        contract_path = ROOT / "src" / "evaluation" / "data_contract.py"
        expected_hash = manifest.get("code_hashes", {}).get("src/evaluation/data_contract.py")
        if sha256(contract_path) == expected_hash:
            try:
                from src.evaluation.data_contract import validate_benchmarks
                validate_benchmarks(benchmark_dir, manifest)
            except Exception as exc:
                audit.check("BENCHMARK_CONTRACT", "core", "valid", str(exc),
                            contract_path)
            else:
                audit.check("BENCHMARK_CONTRACT", "core", "valid", "valid",
                            contract_path)
        else:
            audit.check("BENCHMARK_CONTRACT", "core", "frozen data contract",
                        "current contract hash differs", contract_path,
                        status="unverifiable")
    return datasets, targets


def audit_code(audit: RunAudit, manifest: dict[str, Any]) -> dict[str, tuple[bytes | None, str]]:
    resolved: dict[str, tuple[bytes | None, str]] = {}
    hashes = manifest.get("code_hashes", {})
    for relative_path, expected_hash in hashes.items():
        source, origin = source_snapshot(relative_path, expected_hash)
        resolved[relative_path] = source, origin
        audit.check("CODE_" + relative_path.replace("/", "_").replace(".", "_"),
                    "core", expected_hash,
                    hashlib.sha256(source).hexdigest() if source else None,
                    ROOT / relative_path,
                    status="pass" if source else "unverifiable")
    audit.context["source_origins"] = {key: origin for key, (_, origin) in resolved.items()}
    return resolved


def audit_outputs(audit: RunAudit, manifest: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    output_hashes = manifest.get("output_hashes", {})
    output_counts = manifest.get("output_row_counts", {})
    predictions_path = audit.run_dir / PREDICTIONS_NAME
    raw_path = audit.run_dir / RAW_NAME
    predictions: list[dict[str, str]] = []
    raw_logs: list[dict[str, Any]] = []
    for name, path in ((PREDICTIONS_NAME, predictions_path), (RAW_NAME, raw_path)):
        audit.check("OUTPUT_SHA_" + ("PRED" if name == PREDICTIONS_NAME else "RAW"),
                    "core", output_hashes.get(name),
                    sha256(path) if path.is_file() else None, path)
    if predictions_path.is_file():
        try:
            columns, predictions, bom = read_csv(predictions_path)
            audit.check("PRED_COLUMNS", "core", list(UNIFIED_SCHEMA_COLUMNS),
                        columns, predictions_path)
            audit.check("PRED_BOM", "core", True, bom, predictions_path)
            audit.check("PRED_ROWS", "core", output_counts.get(PREDICTIONS_NAME),
                        len(predictions), predictions_path)
        except (OSError, UnicodeError, csv.Error) as exc:
            audit.check("PRED_PARSE", "core", "parseable", str(exc), predictions_path)
    if raw_path.is_file():
        errors = []
        with raw_path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                try:
                    item = json.loads(line)
                    if not isinstance(item, dict):
                        raise ValueError("JSONL item is not an object")
                    raw_logs.append(item)
                except (json.JSONDecodeError, ValueError) as exc:
                    errors.append(f"line {line_number}: {exc}")
        audit.check("RAW_JSONL", "core", 0, len(errors), raw_path,
                    sample_ids=errors)
        audit.check("RAW_ROWS", "core", output_counts.get(RAW_NAME),
                    len(raw_logs) + len(errors), raw_path)
    return predictions, raw_logs


def audit_records(
    audit: RunAudit,
    manifest: dict[str, Any],
    datasets: dict[str, list[dict[str, str]]],
    targets: dict[str, tuple[str, str]],
    predictions: list[dict[str, str]],
    raw_logs: list[dict[str, Any]],
    scorer_source: bytes | None,
) -> dict[tuple[str, str], list[tuple[dict, dict]]]:
    path = audit.run_dir / PREDICTIONS_NAME
    raw_path = audit.run_dir / RAW_NAME
    if len(datasets) != len(BENCHMARK_NAMES) or not targets:
        audit.check("GOLD_SOURCE", "core", "frozen input available", None, path,
                    status="unverifiable")
        return {}
    try:
        expected = expected_records(datasets, targets)
    except (KeyError, ValueError) as exc:
        audit.check("GOLD_SOURCE", "core", "valid source rows", str(exc), path)
        return {}
    audit.check("EXPECTED_COUNT", "core", 13000, len(expected), path)
    expected_keys = set(expected)
    pred_keys = [(row.get("ID", ""), row.get("CongCu", "")) for row in predictions]
    raw_keys = [(str(row.get("id", "")), str(row.get("tool", ""))) for row in raw_logs]
    audit.check("PRED_KEY_UNIQUE", "core", len(pred_keys), len(set(pred_keys)),
                path, sample_ids=[str(k) for k, n in Counter(pred_keys).items() if n > 1])
    audit.check("RAW_KEY_UNIQUE", "core", len(raw_keys), len(set(raw_keys)),
                raw_path, sample_ids=[str(k) for k, n in Counter(raw_keys).items() if n > 1])
    audit.check("PRED_EXPECTED_KEYS", "core", len(expected_keys),
                len(expected_keys.intersection(pred_keys)), path,
                sample_ids=[str(k) for k in list(expected_keys - set(pred_keys))[:5]])
    audit.check("PRED_UNEXPECTED_KEYS", "core", 0,
                len(set(pred_keys) - expected_keys), path,
                sample_ids=[str(k) for k in list(set(pred_keys) - expected_keys)[:5]])
    audit.check("RAW_PAIR_KEYS", "core", 0,
                len(set(pred_keys).symmetric_difference(raw_keys)), raw_path,
                sample_ids=[str(k) for k in list(set(pred_keys).symmetric_difference(raw_keys))[:5]])

    counts = Counter(f"{key[0][:3]}|{key[1]}" for key in pred_keys)
    audit.context["tool_counts"] = dict(sorted(counts.items()))
    for label, expected_count in EXPECTED_TOOL_COUNTS.items():
        audit.check("COVERAGE_" + label.replace("|", "_"), "core",
                    expected_count, counts.get(label, 0), path)
    audit.check("COVERAGE_UNEXPECTED", "core", [],
                sorted(set(counts) - set(EXPECTED_TOOL_COUNTS)), path)

    raw_by_key = {key: row for key, row in zip(raw_keys, raw_logs)}
    errors: dict[str, list[str]] = defaultdict(list)
    status_counts = Counter()
    metric_groups: dict[tuple[str, str], list[tuple[dict, dict]]] = defaultdict(list)
    scorer = load_scorer(scorer_source, audit.run_id) if scorer_source else None
    for row, key in zip(predictions, pred_keys):
        source = expected.get(key)
        raw = raw_by_key.get(key)
        record_id = key[0]
        if source:
            if row.get("DiaChiGoc") != source["input"]:
                errors["INPUT_SOURCE"].append(record_id)
            if row.get("TinhHuongMoHo") != source["scenario"]:
                errors["SCENARIO_SOURCE"].append(record_id)
        if raw:
            for pred_key, raw_key in (
                ("DiaChiGoc", "input"), ("DungSai", "dung_sai"),
                ("LoaiLoi", "loai_loi"), ("TinhHuongMoHo", "scenario"),
            ):
                if row.get(pred_key) != raw.get(raw_key):
                    errors["PAIR_FIELDS"].append(record_id)
            status = raw.get("status")
            status_counts[f"{key[1]}|{status}"] += 1
            if status not in {"success", "exception"}:
                errors["RAW_STATUS"].append(record_id)
            raw_data = raw.get("raw_data")
            expected_status = (
                "exception" if isinstance(raw_data, dict) and "error" in raw_data
                else "success"
            )
            if status != expected_status:
                errors["RAW_STATUS_CONSISTENCY"].append(record_id)
            if status == "exception" and not isinstance(raw.get("raw_data"), dict):
                errors["RAW_EXCEPTION"].append(record_id)
            try:
                duration = float(raw.get("duration_ms"))
                if not math.isfinite(duration) or duration < 0:
                    errors["RAW_DURATION"].append(record_id)
            except (TypeError, ValueError):
                errors["RAW_DURATION"].append(record_id)
            if source:
                raw_data = raw_data or {}
                if source["mode"] in {"LEGACY", "FROM_2025"}:
                    if not isinstance(raw_data, dict) or raw_data.get("mode") != source["mode"]:
                        errors["MODE_SOURCE"].append(record_id)
                elif source["mode"] == "old_to_new":
                    trace = raw.get("trace") or {}
                    if not isinstance(trace, dict) or trace.get("direction") != "old_to_new":
                        errors["D07_DIRECTION"].append(record_id)
                    if not isinstance(raw_data, dict) or (raw_data.get("conversion_trace") or {}).get("direction") != "old_to_new":
                        errors["D07_DIRECTION"].append(record_id)
        try:
            prediction = json.loads(row["TruongDuDoan"])
            truth = json.loads(row["TruongDung"])
            if (not isinstance(prediction, dict) or not isinstance(truth, dict)
                    or set(prediction) != set(STANDARD_FIELDS)
                    or set(truth) != set(STANDARD_FIELDS)
                    or any(not isinstance(value, str) for value in (*prediction.values(), *truth.values()))):
                raise ValueError("prediction/gold must have five string fields")
        except (KeyError, json.JSONDecodeError, ValueError) as exc:
            errors["FIELD_JSON"].append(f"{record_id}: {exc}")
            continue
        if source:
            if truth != source["truth"]:
                category = "D02_GOLD" if record_id.startswith("D02_") else (
                    "D04_GOLD" if record_id.startswith("D04_") else (
                    "D07_TARGET" if record_id.startswith("D07_") else "OTHER_GOLD"))
                errors[category].append(record_id)
            if record_id.startswith("D06_") and key[1] == "vietnamadminunits":
                expected_mode_note = f"mode={source['mode']}"
                if expected_mode_note not in row.get("GhiChu", ""):
                    errors["D06_MODE_NOTE"].append(record_id)
            if record_id.startswith("D07_") and "direction=old_to_new" not in row.get("GhiChu", ""):
                errors["D07_DIRECTION_NOTE"].append(record_id)
            for condition in source["conditions"]:
                metric_groups[(condition, key[1])].append((prediction, truth))
            if scorer is not None:
                fields = DATA07_FIELDS if record_id.startswith("D07_") else STANDARD_FIELDS
                standard = StandardPrediction(
                    so_nha=prediction["SoNha"], ten_duong=prediction["TenDuong"],
                    phuong_xa=prediction["PhuongXa"], quan_huyen=prediction["QuanHuyen"],
                    tinh_thanh=prediction["TinhThanh"],
                )
                replay = scorer.evaluate_record(
                    record_id, source["input"], key[1], standard,
                    source["truth"], scenario=source["scenario"], scored_fields=fields,
                )
                if replay.dung_sai != row.get("DungSai") or replay.loai_loi != row.get("LoaiLoi"):
                    errors["SCORER_REPLAY"].append(record_id)
    audit.context["raw_status_counts"] = dict(sorted(status_counts.items()))
    for check_id in (
        "INPUT_SOURCE", "SCENARIO_SOURCE", "PAIR_FIELDS", "RAW_STATUS",
        "RAW_STATUS_CONSISTENCY", "RAW_EXCEPTION", "RAW_DURATION",
        "MODE_SOURCE", "D07_DIRECTION",
        "FIELD_JSON", "D02_GOLD", "D04_GOLD", "D07_TARGET", "OTHER_GOLD",
        "D06_MODE_NOTE", "D07_DIRECTION_NOTE",
    ):
        check_path = raw_path if check_id.startswith("RAW_") or check_id in {"MODE_SOURCE", "D07_DIRECTION", "PAIR_FIELDS"} else path
        audit.check(check_id, "core", 0, len(errors[check_id]), check_path,
                    sample_ids=errors[check_id])
    if scorer is None:
        audit.check("SCORER_REPLAY", "core", 0, None, path,
                    status="unverifiable")
    else:
        audit.check("SCORER_REPLAY", "core", 0,
                    len(errors["SCORER_REPLAY"]), path,
                    sample_ids=errors["SCORER_REPLAY"])
    return metric_groups


def numbers_match(expected: str, actual: Any) -> bool:
    if actual is None:
        return expected == ""
    try:
        return math.isclose(float(expected), float(actual), rel_tol=1e-10, abs_tol=1e-10)
    except (TypeError, ValueError):
        return str(expected) == str(actual)


def audit_metrics(
    audit: RunAudit,
    manifest: dict[str, Any],
    groups: dict[tuple[str, str], list[tuple[dict, dict]]],
    scorer_source: bytes | None,
) -> None:
    if audit.run_id != "baseline_v3_fuzzy":
        audit.check("V2_DERIVED_SCOPE", "derived", "historical report not certified",
                    "historical report not certified", audit.run_dir / "run_manifest.json",
                    status="unverifiable")
        return
    docs_dir = ROOT / "docs" / "runs" / audit.run_id
    derived_root = ROOT / "data" / "processed" / "evaluation" / "derived" / audit.run_id / "v4_fuzzy"
    tables_dir = derived_root / "comparative_analysis_tables"
    lineage_path = tables_dir / "report_materials_lineage.json"
    if not lineage_path.is_file():
        audit.check("DERIVED_LINEAGE", "derived", "exists", "missing", lineage_path)
        return
    lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
    audit.check("DERIVED_PARENT_SHA", "derived", sha256(audit.run_dir / "run_manifest.json"),
                lineage.get("parent_manifest_sha256"), lineage_path)
    audit.check("DERIVED_RUN_ID", "derived", audit.run_id,
                lineage.get("run_id"), lineage_path)
    for name, expected_hash in lineage.get("output_hashes", {}).items():
        path = docs_dir / "v4_fuzzy" / name if name.endswith(".md") else tables_dir / name
        audit.check("DERIVED_SHA_" + name.replace(".", "_"), "derived",
                    expected_hash, sha256(path) if path.is_file() else None, path)
    audit.check("DERIVED_ARTIFACT_COUNT", "derived", 13,
                len(lineage.get("output_hashes", {})), lineage_path)

    scorer_hash = manifest.get("code_hashes", {}).get("src/evaluation/scorer.py")
    if scorer_source is None or hashlib.sha256(scorer_source).hexdigest() != scorer_hash:
        audit.check("METRIC_REPLAY", "derived", "matching scorer", None,
                    tables_dir / "dataset_metrics.csv", status="unverifiable")
        return
    scorer = load_scorer(scorer_source, audit.run_id)
    sentinel_results = {
        "casefold": scorer.normalized_edit_similarity("Phường A", "phường a"),
        "both_empty": scorer.normalized_edit_similarity("", ""),
        "one_empty": scorer.normalized_edit_similarity("", "Phường A"),
        "keep_unit_type": scorer.normalized_edit_similarity("Phường A", "Xã A"),
        "keep_diacritics": scorer.normalized_edit_similarity("Hòa", "Hoa"),
    }
    sentinel_ok = (
        sentinel_results["casefold"] == 1.0
        and sentinel_results["both_empty"] is None
        and sentinel_results["one_empty"] == 0.0
        and sentinel_results["keep_unit_type"] < 1.0
        and sentinel_results["keep_diacritics"] < 1.0
    )
    audit.check("SCORER_POLICY_SENTINELS", "derived", True, sentinel_ok,
                ROOT / "src" / "evaluation" / "scorer.py")
    expected_rows: dict[tuple[str, str], dict[str, Any]] = {}
    expected_field_rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    for (condition, tool), pairs in groups.items():
        fields = DATA07_FIELDS if condition.startswith("Data 07|") else STANDARD_FIELDS
        metrics = scorer.aggregate_prediction_pairs(pairs, fields)
        expected_rows[(condition, tool)] = {
            "n": metrics["record_count"],
            "exact_correct": metrics["exact_record_correct"],
            "exact_match_rate": metrics["exact_record_match_rate"],
            "micro_mean_fuzzy_similarity": metrics["micro_mean_fuzzy_similarity"],
            "fuzzy_scored_field_values": metrics["fuzzy_scored_field_values"],
            "macro_mean_field_fuzzy_similarity": metrics["macro_mean_field_fuzzy_similarity"],
            "micro_f1_scored_fields": metrics["micro_f1_scored_fields"],
            "macro_mean_field_f1": metrics["macro_mean_field_f1"],
        }
        for field, field_metric in metrics["field_metrics"].items():
            expected_field_rows[(condition, tool, field)] = {
                name: field_metric[name] for name in FIELD_METRIC_COLUMNS
            }
    for file_name, expected_map, key_columns, columns, check_id in (
        ("dataset_metrics.csv", expected_rows, ("dataset_condition", "tool"),
         METRIC_COLUMNS, "METRIC_REPLAY"),
        ("dataset_field_metrics.csv", expected_field_rows,
         ("dataset_condition", "tool", "field"), FIELD_METRIC_COLUMNS,
         "FIELD_METRIC_REPLAY"),
    ):
        path = tables_dir / file_name
        if not path.is_file():
            audit.check(check_id, "derived", "present", "missing", path)
            continue
        _, rows, _ = read_csv(path)
        actual_keys = {tuple(row.get(name, "") for name in key_columns) for row in rows}
        errors = []
        for row in rows:
            key = tuple(row.get(name, "") for name in key_columns)
            expected_values = expected_map.get(key)
            if expected_values is None:
                errors.append(f"unexpected:{key}")
                continue
            for name in columns:
                if not numbers_match(row.get(name, ""), expected_values[name]):
                    errors.append(f"{key}:{name}")
            if file_name == "dataset_metrics.csv":
                audit.metrics.append({
                    "dataset_condition": key[0], "tool": key[1],
                    "n": expected_values["n"],
                    "exact_correct": expected_values["exact_correct"],
                    "exact_match_rate": expected_values["exact_match_rate"],
                    "micro_f1_scored_fields": expected_values["micro_f1_scored_fields"],
                    "micro_mean_fuzzy_similarity": expected_values["micro_mean_fuzzy_similarity"],
                    "fuzzy_scored_field_values": expected_values["fuzzy_scored_field_values"],
                })
        errors.extend(f"missing:{key}" for key in expected_map.keys() - actual_keys)
        audit.check(check_id, "derived", 0, len(errors), path, sample_ids=errors)
        audit.check(check_id + "_ROWS", "derived", len(expected_map), len(rows), path)

    report_path = docs_dir / "baseline_evaluation_report.md"
    reporter_path = ROOT / "src" / "evaluation" / "reporter.py"
    expected_reporter_hash = manifest.get("code_hashes", {}).get("src/evaluation/reporter.py")
    if not report_path.is_file():
        audit.check("MAIN_REPORT", "derived", "present", "missing", report_path)
    elif sha256(reporter_path) != expected_reporter_hash:
        audit.check("MAIN_REPORT", "derived", "matching reporter code", None,
                    reporter_path, status="unverifiable")
    else:
        try:
            import pandas as pd
            from src.evaluation.reporter import generate_baseline_report_markdown
            report_manifest = dict(manifest)
            report_manifest["reporter_sha256"] = sha256(reporter_path)
            predictions = pd.read_csv(audit.run_dir / PREDICTIONS_NAME,
                                      dtype=str, keep_default_na=False, encoding="utf-8-sig")
            generated = generate_baseline_report_markdown(
                predictions, manifest_data=report_manifest,
                benchmark_dir=ROOT / "data" / "processed" / "benchmark",
                raw_log_path=audit.run_dir / RAW_NAME,
            )
            published = report_path.read_text(encoding="utf-8")
            def without_date(value: str) -> list[str]:
                return [line for line in value.splitlines() if not line.startswith("- Ngày tạo:")]
            generated_lines = without_date(generated)
            published_lines = without_date(published)
            differences = [str(index + 1) for index, (left, right) in enumerate(
                zip(generated_lines, published_lines)
            ) if left != right]
            if len(generated_lines) != len(published_lines):
                differences.append("line_count")
            audit.check("MAIN_REPORT_REPLAY", "derived", 0, len(differences),
                        report_path, sample_ids=differences)
            audit.context["main_report_scope"] = "Content replay excluding date; main report is not in derived lineage."
        except Exception as exc:
            audit.check("MAIN_REPORT_REPLAY", "derived", "successful replay", str(exc),
                        report_path, status="unverifiable")


def audit_one(run_id: str) -> dict[str, Any]:
    audit = RunAudit(run_id)
    manifest_path = audit.run_dir / "run_manifest.json"
    if not manifest_path.is_file():
        audit.check("MANIFEST_FILE", "core", "present", "missing", manifest_path)
        return audit.finish()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        audit.check("MANIFEST_PARSE", "core", "parseable JSON", str(exc), manifest_path)
        return audit.finish()
    audit.context["manifest_sha256"] = sha256(manifest_path)
    version = manifest.get("manifest_version")
    audit.check("MANIFEST_VERSION", "core",
                "3.0" if run_id == "baseline_v2" else "4.0", version, manifest_path)
    audit.check("MANIFEST_RUN_ID", "core", run_id, manifest.get("run_id"), manifest_path)
    audit.check("MANIFEST_RUN_KIND", "core", "full", manifest.get("run_kind"), manifest_path)
    audit.check("MANIFEST_SEED", "core", 42, manifest.get("seed"), manifest_path)
    for name in ("freeze_timestamp", "python_version", "runtime_packages",
                 "baseline_tools", "protocol", "mapping_source", "code_hashes",
                 "output_hashes", "output_row_counts"):
        audit.check("MANIFEST_" + name.upper(), "core", "present",
                    "present" if manifest.get(name) else "missing", manifest_path)
    for name in (PREDICTIONS_NAME, RAW_NAME):
        audit.check("MANIFEST_OUTPUT_" + name.replace(".", "_"), "core",
                    "hash and count present",
                    "hash and count present" if manifest.get("output_hashes", {}).get(name)
                    and isinstance(manifest.get("output_row_counts", {}).get(name), int)
                    else "missing", manifest_path)
    if version == "4.0":
        scoring = manifest.get("scoring", {})
        for name in ("protocol_version", "fuzzy_similarity_method",
                     "fuzzy_similarity_normalization", "fuzzy_empty_policy",
                     "administrative_target_rule"):
            audit.check("SCORING_" + name.upper(), "core", "present",
                        "present" if scoring.get(name) else "missing", manifest_path)
        audit.check("SCORING_PROTOCOL", "core", "2.0",
                    scoring.get("protocol_version"), manifest_path)
        audit.check("SCORING_METHOD", "core", "normalized_levenshtein",
                    scoring.get("fuzzy_similarity_method"), manifest_path)
    audit.context["manifest_version"] = version
    audit.context["protocol"] = manifest.get("protocol")
    audit.context["scoring"] = manifest.get("scoring")
    datasets, targets = audit_inputs(audit, manifest)
    sources = audit_code(audit, manifest)
    if version == "4.0":
        protocol_source = sources.get("src/evaluation/protocol.py", (None, "missing"))[0]
        if protocol_source:
            protocol_module = types.ModuleType(f"frozen_protocol_{run_id}")
            exec(compile(protocol_source, "<frozen_protocol>", "exec"),
                 protocol_module.__dict__)
            scoring = manifest["scoring"]
            for check_id, manifest_key, constant in (
                ("SCORING_NORMALIZATION_MATCH", "fuzzy_similarity_normalization", "FUZZY_NORMALIZATION"),
                ("SCORING_EMPTY_POLICY_MATCH", "fuzzy_empty_policy", "FUZZY_EMPTY_POLICY"),
            ):
                audit.check(check_id, "core", getattr(protocol_module, constant),
                            scoring.get(manifest_key), manifest_path)
            audit.check("SCORING_DIRECTION_MATCH", "core", "old_to_new",
                        protocol_module.DATASET07_DIRECTION, manifest_path)
            audit.check("SCORING_FIELDS_MATCH", "core", DATA07_FIELDS,
                        tuple(protocol_module.DATASET07_SCORED_FIELDS), manifest_path)
        else:
            audit.check("SCORING_POLICY_SOURCE", "core", "available", None,
                        ROOT / "src" / "evaluation" / "protocol.py",
                        status="unverifiable")
    predictions, raw_logs = audit_outputs(audit, manifest)
    scorer_source = sources.get("src/evaluation/scorer.py", (None, "missing"))[0]
    groups = audit_records(audit, manifest, datasets, targets, predictions, raw_logs,
                           scorer_source)
    audit_metrics(audit, manifest, groups, scorer_source)
    return audit.finish()


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Kiểm toán run baseline — Sprint 3", "",
        f"- Thời điểm UTC: `{result['audited_at']}`.",
        f"- Runtime kiểm toán: `{result['runtime']}`.",
        f"- Môi trường thực thi: {result.get('execution_environment_note', 'Không có ghi chú bổ sung')}.",
        "- Chạy chỉ đọc trên run frozen; JSON cùng thư mục là nguồn cho bảng này.",
        "- `PASS` của v3 chỉ áp dụng cho track 5 trường với oracle mode theo protocol; "
        "Data 07 là phép chuyển cũ → mới, không phải T0/T1.",
        "", "## Kết luận", "",
        "| Run | Quyết định | Manifest SHA-256 | Pass | Fail | Unverifiable |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for run_id, run in result["runs"].items():
        counts = run["check_counts"]
        lines.append(
            f"| `{run_id}` | **{run['decision']}** | "
            f"`{run['context'].get('manifest_sha256', 'missing')}` | "
            f"{counts.get('pass', 0)} | {counts.get('fail', 0)} | "
            f"{counts.get('unverifiable', 0)} |"
        )
    lines += ["", "**Các cổng chưa đạt hoặc chưa thể xác minh:**", ""]
    for run_id, run in result["runs"].items():
        unresolved = [f"`{item['id']}` ({item['status']})"
                      for item in run["checks"] if item["status"] != "pass"]
        lines.append(f"- `{run_id}`: {', '.join(unresolved) if unresolved else 'không có'}.")
        scorer_origin = run["context"].get("source_origins", {}).get(
            "src/evaluation/scorer.py", "unknown")
        lines.append(f"  Scorer dùng để replay: `{scorer_origin}`.")
    lines += [
        "", "`baseline_v2` là mốc lịch sử frozen. Không so điểm fuzzy v2 với v3 vì "
        "manifest v2 không dùng cùng protocol fuzzy. Tài liệu v2 thuộc phạm vi lưu lịch sử "
        "theo `docs/VERSIONING.md`.",
        "", "## Kiểm tra chi tiết", "",
    ]
    for run_id, run in result["runs"].items():
        lines += [f"### {run_id}", "", "| Check | Phạm vi | Kết quả | Expected | Actual | Bằng chứng | Mẫu lỗi |",
                  "| --- | --- | --- | --- | --- | --- | --- |"]
        for item in run["checks"]:
            def cell(value: Any) -> str:
                if isinstance(value, tuple):
                    value = list(value)
                value_text = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
                if len(value_text) > 100:
                    value_text = value_text[:97] + "..."
                return value_text.replace("|", "\\|").replace("\n", " ")
            lines.append(
                f"| `{item['id']}` | {item['scope']} | {item['status']} | "
                f"{cell(item['expected'])} | {cell(item['actual'])} | "
                f"`{item['evidence_path']}` | {cell(item['sample_ids'])} |"
            )
        lines += ["", "**Phân bố lượt theo tập và tool:**", ""]
        for label, count in run["context"].get("tool_counts", {}).items():
            lines.append(f"- `{label}`: {count}")
        lines += ["", "**Trạng thái raw log:**", ""]
        for label, count in run["context"].get("raw_status_counts", {}).items():
            lines.append(f"- `{label}`: {count}")
        if run["metrics"]:
            lines += ["", "**Metric tính lại từ prediction/gold (bảng dẫn xuất được so từng giá trị):**", "",
                      "| Tập/điều kiện | Tool | n | Exact đúng | Exact rate | Micro F1 | Fuzzy mean / số cặp |",
                      "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
            for row in run["metrics"]:
                fuzzy = row["micro_mean_fuzzy_similarity"]
                fuzzy_text = "n/a" if fuzzy is None else f"{fuzzy:.6f} / {row['fuzzy_scored_field_values']}"
                lines.append(
                    f"| {row['dataset_condition']} | `{row['tool']}` | {row['n']} | "
                    f"{row['exact_correct']} | {row['exact_match_rate']:.6f} | "
                    f"{row['micro_f1_scored_fields']:.6f} | {fuzzy_text} |"
                )
        lines.append("")
    lines += [
        "## Phạm vi xác minh", "",
        "- Run v3 được tính lại bằng scorer có đúng SHA-256 trong manifest; báo cáo chính "
        "được tái tạo trong bộ nhớ và so nội dung trừ dòng ngày tạo. Báo cáo chính "
        "không có hash riêng trong lineage dẫn xuất.",
        "- Runtime audit có thể khác runtime ghi trong manifest. Kiểm toán này không gọi "
        "lại Libpostal/VietnamAdminUnits, nên không xác minh tính tái lập của dịch vụ ngoài.",
        "- Không có span gold 11 nhãn trong sáu tập này; kết luận không áp dụng cho T0 11 nhãn.",
        "- Danh sách check đầy đủ và bằng chứng có cấu trúc nằm trong `baseline_run_audit.json`.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", action="append", required=True,
                        help="Frozen run to audit; repeat for multiple runs")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--environment-note", default="",
                        help="Record a runtime limitation without changing audit rules")
    args = parser.parse_args()
    run_ids = list(dict.fromkeys(args.run_id))
    for run_id in run_ids:
        if not re.fullmatch(r"[a-z0-9_]+", run_id):
            parser.error(f"Invalid run ID: {run_id}")
    output_dir = args.output_dir.resolve()
    frozen_dir = (ROOT / "data" / "processed" / "evaluation" / "runs").resolve()
    if output_dir == frozen_dir or frozen_dir in output_dir.parents:
        parser.error("Audit output directory cannot be inside frozen runs")

    frozen_paths = [
        ROOT / "data" / "processed" / "evaluation" / "runs" / run_id / name
        for run_id in run_ids
        for name in ("run_manifest.json", PREDICTIONS_NAME, RAW_NAME)
    ]
    before = {evidence(path): sha256(path) if path.is_file() else None
              for path in frozen_paths}
    status = git_output("status", "--short")
    result: dict[str, Any] = {
        "audit_version": "1.0",
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "runtime": sys.version.split()[0] + " on " + sys.platform,
        "execution_environment_note": args.environment_note,
        "repository_state": status.decode("utf-8", errors="replace") if status else "",
        "frozen_hashes_before": before,
        "runs": {run_id: audit_one(run_id) for run_id in run_ids},
    }
    after = {evidence(path): sha256(path) if path.is_file() else None
             for path in frozen_paths}
    result["frozen_hashes_after"] = after
    result["frozen_unchanged"] = before == after
    for run in result["runs"].values():
        run["checks"].append({
            "id": "FROZEN_UNCHANGED", "scope": "core", "expected": True,
            "actual": result["frozen_unchanged"],
            "status": "pass" if result["frozen_unchanged"] else "fail",
            "evidence_path": "data/processed/evaluation/runs",
            "sample_ids": [],
        })
        run["check_counts"] = dict(Counter(item["status"] for item in run["checks"]))
        if not result["frozen_unchanged"]:
            run["decision"] = "FAIL"

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "baseline_run_audit.json"
    markdown_path = output_dir / "baseline_run_audit.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    markdown_path.write_text(render_markdown(result), encoding="utf-8")
    post_report = {evidence(path): sha256(path) if path.is_file() else None
                   for path in frozen_paths}
    result["frozen_hashes_after_report"] = post_report
    result["frozen_unchanged"] = before == post_report
    if not result["frozen_unchanged"]:
        for run in result["runs"].values():
            for check in run["checks"]:
                if check["id"] == "FROZEN_UNCHANGED":
                    check["actual"] = False
                    check["status"] = "fail"
            run["check_counts"] = dict(Counter(item["status"] for item in run["checks"]))
            run["decision"] = "FAIL"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    markdown_path.write_text(render_markdown(result), encoding="utf-8")
    for run_id, run in result["runs"].items():
        print(f"{run_id}: {run['decision']} {run['check_counts']}")
    print(f"Frozen files unchanged: {result['frozen_unchanged']}")
    print(json_path)
    print(markdown_path)
    if any(run["decision"] == "FAIL" for run in result["runs"].values()):
        return 1
    if any(run["decision"] == "UNVERIFIABLE" for run in result["runs"].values()):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
