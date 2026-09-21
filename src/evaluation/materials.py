"""Deterministic, traceable tables used by baseline report materials."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd


CASE_COLUMNS = (
    "ID",
    "CongCu",
    "Dataset",
    "LoaiLoi",
    "DungSai",
    "TinhHuongMoHo",
    "DiaChiGoc",
    "TruongDuDoan",
    "TruongDung",
    "GhiChu",
    "RawStatus",
)


def dataset_from_record_id(record_id: str) -> str:
    """Return the benchmark identifier from a unified evaluation record ID."""
    return str(record_id).split("_", maxsplit=1)[0]


def index_raw_logs(raw_logs: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    """Index raw records and reject duplicate (ID, tool) audit keys."""
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for item in raw_logs:
        key = (str(item["id"]), str(item["tool"]))
        if key in index:
            raise ValueError(f"Duplicate raw-log key: {key}")
        index[key] = item
    return index


def select_traceable_cases(predictions: pd.DataFrame, raw_logs: list[dict[str, Any]], per_group: int = 1) -> pd.DataFrame:
    """Select deterministic error examples from output, never hand-authored examples.

    Selection rule: sort by dataset, tool, error type and record ID; retain the
    first `per_group` rows for each (dataset, tool, error type) group.
    """
    missing = set(("ID", "CongCu", "DungSai", "LoaiLoi", "DiaChiGoc", "TruongDuDoan", "TruongDung", "TinhHuongMoHo", "GhiChu")) - set(predictions.columns)
    if missing:
        raise ValueError(f"Prediction data is missing columns: {sorted(missing)}")
    raw_index = index_raw_logs(raw_logs)
    rows: list[dict[str, str]] = []
    errors = predictions[predictions["DungSai"].ne("CORRECT")].copy()
    errors["Dataset"] = errors["ID"].map(dataset_from_record_id)
    for _, row in errors.sort_values(["Dataset", "CongCu", "LoaiLoi", "ID"], kind="stable").groupby(
        ["Dataset", "CongCu", "LoaiLoi"], sort=True
    ):
        for _, candidate in row.head(per_group).iterrows():
            key = (str(candidate["ID"]), str(candidate["CongCu"]))
            raw = raw_index.get(key)
            if raw is None:
                raise ValueError(f"Prediction has no raw log: {key}")
            if str(raw.get("input", "")) != str(candidate["DiaChiGoc"]):
                raise ValueError(f"Raw input mismatch for {key}")
            rows.append({
                "ID": str(candidate["ID"]),
                "CongCu": str(candidate["CongCu"]),
                "Dataset": str(candidate["Dataset"]),
                "LoaiLoi": str(candidate["LoaiLoi"]),
                "DungSai": str(candidate["DungSai"]),
                "TinhHuongMoHo": str(candidate["TinhHuongMoHo"]),
                "DiaChiGoc": str(candidate["DiaChiGoc"]),
                "TruongDuDoan": str(candidate["TruongDuDoan"]),
                "TruongDung": str(candidate["TruongDung"]),
                "GhiChu": str(candidate["GhiChu"]),
                "RawStatus": str(raw.get("status", "unknown")),
            })
    return pd.DataFrame(rows, columns=CASE_COLUMNS)


def validate_case_table(cases: pd.DataFrame, predictions: pd.DataFrame, raw_logs: list[dict[str, Any]]) -> None:
    """Prove every materialized case is an exact projection of prediction/raw output."""
    if set(CASE_COLUMNS) - set(cases.columns):
        raise ValueError("Case table does not satisfy its schema")
    pred_index = predictions.set_index(["ID", "CongCu"], verify_integrity=True)
    raw_index = index_raw_logs(raw_logs)
    for _, case in cases.iterrows():
        key = (str(case["ID"]), str(case["CongCu"]))
        if key not in pred_index.index or key not in raw_index:
            raise ValueError(f"Case key does not exist in source output: {key}")
        source = pred_index.loc[key]
        for field in ("DiaChiGoc", "TruongDuDoan", "TruongDung", "DungSai", "LoaiLoi", "TinhHuongMoHo", "GhiChu"):
            if str(case[field]) != str(source[field]):
                raise ValueError(f"Case field mismatch for {key}: {field}")
        if str(case["RawStatus"]) != str(raw_index[key].get("status", "unknown")):
            raise ValueError(f"Case raw status mismatch for {key}")


def parse_prediction_json(value: str) -> dict[str, str]:
    """Decode a stored prediction/ground-truth object for Markdown rendering."""
    parsed = json.loads(value)
    return {str(key): str(item or "") for key, item in parsed.items()}
