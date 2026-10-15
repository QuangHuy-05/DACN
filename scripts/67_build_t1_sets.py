"""Build the group-disjoint synthetic T1 sets and the Data 06 held-out set (WP2).

Usage (repository root, main venv):
    python -m scripts.67_build_t1_sets [--output DIR]

Outputs (CSV utf-8-sig) in a versioned directory that is never overwritten:
    t1_synth_train.csv, t1_synth_dev.csv, t1_synth_eval.csv, t1_data06_heldout.csv,
    t1_synth_excluded.csv (rows removed from train/dev, with the reason), run_manifest.json

All three classes come from benchmark generators over OSM data: Lai from
``generate_hybrid_addresses`` (new seed), cu from Data 03, moi from Data 01.
These sets carry string-level T1 labels only and must not be used as T0 labels
(lanes stay inside TenDuong, unlike the Sprint 3 gold).
Exit code 2: a number measured on 13/10/2026 did not reproduce.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd

from src.data.administrative_alias import resolve_province_alias
from src.data.administrative_mapping import (
    AdministrativeMapping,
    default_mapping_path,
    load_administrative_mapping,
    normalise_text,
    province_key,
)
from src.data.synthetic.hybrid_address import generate_hybrid_addresses
from src.evaluation.leak_guard import (
    DEFAULT_CORPUS_DIR,
    admin_group_key,
    build_exclusion_index,
    filter_benchmark,
    load_corpus_records,
    normalize_for_overlap,
    sha256_file,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = Path("data/interim/modeling/sprint04/t1_sets_20261015_v1")
SCRIPT_VERSION = "t1-sets-v1"
SEED = 20261015
TARGET_SIZE = 3000
SPLIT_FRACTIONS = (0.6, 0.2, 0.2)  # share of groups: train / dev / eval
CLASSES = ("cu", "moi", "Lai")

OLD_SNAPSHOT = Path("data/interim/osm/osm_old_snapshot_full.csv")
DATA01 = Path("data/processed/benchmark/01_full_address_new_verified.csv")
DATA03 = Path("data/processed/benchmark/03_real_address_old_1500.csv")
DATA06 = Path("data/processed/benchmark/06_hybrid_addresses_600.csv")
ADMIN_COLUMNS = ("TinhThanh", "QuanHuyen", "PhuongXa")
TEXT_COLUMN = "ChuoiDiaChi"
SOURCE_FILES = (
    "scripts/67_build_t1_sets.py", "src/evaluation/leak_guard.py", "src/data/synthetic/hybrid_address.py",
    "src/data/administrative_mapping.py", "src/data/administrative_alias.py",
)
OUTPUT_COLUMNS = [
    "key", "text", "gold_system", "source", "KieuLai", "admin_group_key", "province_new",
    "unresolved_group", "gold_province", "gold_district", "gold_ward",
]

# Measured on 13/10/2026 on the full 3,000 generated rows (not sequentially).
EXPECTED = {
    "old_snapshot_rows": 26961, "generated_rows": 3000, "generated_exact_dup_data06": 244,
    "generated_leak_guard_dropped": 20, "generated_groups": 527, "generated_unresolved_rows": 74,
    "generated_lane_street_rows": 135, "data06_rows": 600, "data06_kept": 580, "data06_kept_groups": 48,
}

REASON_PAIR = "TRUNG_CAP_TINH_PHUONG_DEV_TEST_S3"
REASON_GROUP = "CUNG_NHOM_ADM_DEV_TEST_S3"
REASON_BALANCE = "LAY_MAU_XUONG_CAN_BANG_LOP"

WARD_PREFIX = re.compile(r"^(?:phường|xã|thị\s+trấn|đặc\s+khu|p\.|x\.|tt\.)\s*")


def load_csv(path: Path, required: tuple[str, ...]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{path}: missing required columns {missing}")
    return frame


def bare_ward(value: object) -> str:
    """Ward name without its unit-type prefix ("Phường Ba Đình" -> "ba đình")."""
    return WARD_PREFIX.sub("", normalise_text(value)).strip()


def new_province_name(mapping: AdministrativeMapping, value: object) -> str:
    """Official post-reform province for an old or new spelling ('' when unknown)."""
    return mapping.resolve_new_province(value) or mapping.resolve_new_province(resolve_province_alias(value))


def province_pair_key(mapping: AdministrativeMapping, value: object) -> str:
    return province_key(new_province_name(mapping, value) or value)


def sprint3_holdout(records: dict[str, list[dict]], mapping: AdministrativeMapping) -> dict:
    """Keys of Sprint 3 dev/test samples that train/dev synthetic rows must avoid.

    The administrative group alone is not enough: most dev/test gold names lack
    a unit prefix and fall into UNRESOLVED keys, so the (new province, bare ward
    name) pair is excluded as well.
    """
    pairs: set[tuple[str, str]] = set()
    groups: set[str] = set()
    stats = {}
    for split in ("dev", "test"):
        all_keys, without_pair = set(), 0
        for row in records[split]:
            by_label: dict[str, list[str]] = {}
            for span in sorted(row["spans"], key=lambda s: (s["start"], s["end"])):
                by_label.setdefault(span["label"], []).append(row["text"][span["start"]:span["end"]])
            wards, provinces = by_label.get("PhuongXa", []), by_label.get("TinhThanh", [])
            if not wards or not provinces:
                without_pair += 1  # nothing to exclude by pair: a limit of this filter
            pairs.update((province_pair_key(mapping, p), bare_ward(w)) for p in provinces for w in wards)
            key = admin_group_key(
                (provinces or [""])[0], (by_label.get("QuanHuyen") or [""])[0], (wards or [""])[0], mapping
            )
            all_keys.add(key)
            if key.startswith("ADM|"):
                groups.add(key)
        stats[split] = {
            "samples": len(records[split]),
            "distinct_group_keys": len(all_keys),
            "unresolved_group_keys": sum(k.startswith("UNRESOLVED|") for k in all_keys),
            "samples_without_ward_or_province_span": without_pair,
        }
    return {"pairs": pairs, "groups": groups, "stats": stats}


def to_pool(frame: pd.DataFrame, source: str, system: str, mapping: AdministrativeMapping) -> pd.DataFrame:
    rows = []
    for position, row in enumerate(frame.to_dict("records")):
        province, district, ward = (row[c] for c in ADMIN_COLUMNS)
        rows.append({
            "key": f"{source}:{position:05d}",
            "text": row[TEXT_COLUMN],
            "gold_system": system,
            "source": source,
            "KieuLai": row.get("KieuLai", ""),
            "admin_group_key": admin_group_key(province, district, ward, mapping),
            "province_new": new_province_name(mapping, province),
            "gold_province": province, "gold_district": district, "gold_ward": ward,
        })
    pool = pd.DataFrame(rows, columns=[c for c in OUTPUT_COLUMNS if c != "unresolved_group"])
    pool["unresolved_group"] = pool["admin_group_key"].str.startswith("UNRESOLVED|")
    return pool[OUTPUT_COLUMNS]


def assign_groups(pool: pd.DataFrame, seed: int) -> dict[str, str]:
    """Group -> part, about 60/20/20 of the groups inside every new province.

    A random phase per province keeps small provinces from always landing in
    train.  Only resolved (ADM) groups are split.
    """
    resolved = pool[~pool["unresolved_group"]]
    province_of = {}
    for group, part in resolved.groupby("admin_group_key", sort=True):
        counts = Counter(part["province_new"])
        province_of[group] = sorted(counts, key=lambda name: (-counts[name], name))[0]
    by_province: dict[str, list[str]] = {}
    for group, province in sorted(province_of.items()):
        by_province.setdefault(province, []).append(group)
    rng = np.random.default_rng(seed)
    train_cut, dev_cut = SPLIT_FRACTIONS[0], SPLIT_FRACTIONS[0] + SPLIT_FRACTIONS[1]
    assignment = {}
    for province in sorted(by_province):
        groups = by_province[province]
        order = rng.permutation(len(groups))
        phase = rng.random()
        for rank, index in enumerate(order):
            share = (rank + phase) / len(groups)
            assignment[groups[index]] = "train" if share < train_cut else "dev" if share < dev_cut else "eval"
    return assignment


def district_majority_baseline(train: pd.DataFrame, evaluation: pd.DataFrame) -> dict:
    """Class predicted from "district column filled" alone (oracle column, data-level check)."""
    rule = {}
    for flag in (True, False):
        counts = Counter(train.loc[(train["gold_district"] != "") == flag, "gold_system"])
        rule[flag] = sorted(CLASSES, key=lambda c: (-counts[c], CLASSES.index(c)))[0]
    predicted = [(rule[d != ""]) for d in evaluation["gold_district"]]
    correct = sum(p == g for p, g in zip(predicted, evaluation["gold_system"]))
    return {"rule": {"district_present": rule[True], "district_absent": rule[False]},
            "eval_correct": correct, "eval_rows": len(evaluation),
            "eval_accuracy": correct / len(evaluation) if len(evaluation) else None}


def class_table(frame: pd.DataFrame) -> dict:
    counts = Counter(frame["gold_system"])
    total = len(frame)
    return {label: {"rows": counts[label], "share": round(counts[label] / total, 4) if total else None}
            for label in CLASSES} | {"total": total}


def build(repo: Path) -> dict:
    mapping_path = default_mapping_path()
    mapping = load_administrative_mapping(mapping_path)
    corpus_dir = repo / DEFAULT_CORPUS_DIR
    index = build_exclusion_index(("train", "dev", "test"), corpus_dir)
    records, _ = load_corpus_records(corpus_dir)
    steps: dict = {}
    measured: dict = {}

    data06 = load_csv(repo / DATA06, (TEXT_COLUMN, "KieuLai", "HeQuyChieu", *ADMIN_COLUMNS))
    data06_texts = set(data06[TEXT_COLUMN])
    data06_normalized = {normalize_for_overlap(t) for t in data06_texts}

    # (a) new hybrid source ----------------------------------------------------
    snapshot = load_csv(repo / OLD_SNAPSHOT, ("SoNha", "TenDuong", *ADMIN_COLUMNS))
    generated = generate_hybrid_addresses(snapshot, mapping_path, target_size=TARGET_SIZE, seed=SEED)
    generated_keys = [admin_group_key(r["TinhThanh"], r["QuanHuyen"], r["PhuongXa"], mapping)
                      for r in generated.to_dict("records")]
    measured.update({
        "old_snapshot_rows": len(snapshot),
        "generated_rows": len(generated),
        "generated_exact_dup_data06": int(generated[TEXT_COLUMN].isin(data06_texts).sum()),
        "generated_leak_guard_dropped": len(filter_benchmark(generated, TEXT_COLUMN, index=index)[1]),
        "generated_groups": len(set(generated_keys)),
        "generated_unresolved_rows": sum(k.startswith("UNRESOLVED|") for k in generated_keys),
        "generated_lane_street_rows": int(generated["TenDuong"].str.match(r"(?i)^(?:ngõ|hẻm|ngách|kiệt)\b").sum()),
        "generated_largest_group_share": round(max(Counter(generated_keys).values()) / len(generated), 4),
    })
    lai = generated[~generated[TEXT_COLUMN].map(normalize_for_overlap).isin(data06_normalized)]
    steps["lai_after_data06_dedup"] = len(lai)
    lai, _ = filter_benchmark(lai, TEXT_COLUMN, index=index)
    steps["lai_after_leak_guard"] = len(lai)
    lai_pool = to_pool(lai.reset_index(drop=True), "synth_lai", "Lai", mapping)
    lai_pool = lai_pool[~lai_pool["unresolved_group"]]
    steps["lai_after_unresolved_drop"] = len(lai_pool)

    # (b) cu and moi sources ----------------------------------------------------
    pools = [lai_pool]
    for name, path, system in (("data03", DATA03, "cu"), ("data01", DATA01, "moi")):
        frame = load_csv(repo / path, (TEXT_COLUMN, "HeQuyChieu", *ADMIN_COLUMNS))
        if set(frame["HeQuyChieu"]) != {system}:
            raise ValueError(f"{path}: expected only HeQuyChieu={system}")
        kept, dropped = filter_benchmark(frame, TEXT_COLUMN, index=index)
        steps[f"{name}_rows"] = len(frame)
        steps[f"{name}_after_leak_guard"] = len(kept)
        pools.append(to_pool(kept.reset_index(drop=True), name, system, mapping))

    # (c) one pool; a surface string keeps a single label ------------------------
    pool = pd.concat(pools, ignore_index=True)
    pool["_norm"] = pool["text"].map(normalize_for_overlap)
    labels_per_text = pool.groupby("_norm")["gold_system"].nunique()
    conflicting = set(labels_per_text[labels_per_text > 1].index)
    steps["pool_rows_before_dedup"] = len(pool)
    # A Data 06 string must not reappear under another label (old ward and new ward can share a
    # name, so one surface may be "cu" in Data 03 and "Lai" in Data 06).
    equals_data06 = pool["_norm"].isin(data06_normalized)
    steps["pool_rows_equal_data06_text_dropped"] = int(equals_data06.sum())
    steps["pool_rows_equal_data06_text_by_class"] = dict(Counter(pool.loc[equals_data06, "gold_system"]))
    pool = pool[~equals_data06]
    steps["pool_rows_conflicting_label_dropped"] = int(pool["_norm"].isin(conflicting).sum())
    pool = pool[~pool["_norm"].isin(conflicting)]
    steps["pool_duplicate_text_dropped"] = int(pool.duplicated("_norm").sum())
    pool = pool[~pool.duplicated("_norm")].drop(columns="_norm").reset_index(drop=True)
    steps["pool_rows"] = len(pool)
    steps["pool_unresolved_rows"] = int(pool["unresolved_group"].sum())
    steps["pool_resolved_groups"] = int(pool.loc[~pool["unresolved_group"], "admin_group_key"].nunique())

    assignment = assign_groups(pool, SEED)
    # UNRESOLVED rows cannot be proven disjoint from train: evaluation only, flagged.
    pool["part"] = [("eval" if unresolved else assignment[group])
                    for group, unresolved in zip(pool["admin_group_key"], pool["unresolved_group"])]

    # (d) keep Sprint 3 dev/test territory out of train/dev ------------------------
    holdout = sprint3_holdout(records, mapping)
    pair_hit = [(province_pair_key(mapping, p), bare_ward(w)) in holdout["pairs"]
                for p, w in zip(pool["gold_province"], pool["gold_ward"])]
    group_hit = pool["admin_group_key"].isin(holdout["groups"])
    reason = pd.Series("", index=pool.index)
    reason[pd.Series(pair_hit, index=pool.index)] = REASON_PAIR
    reason[group_hit & (reason == "")] = REASON_GROUP
    in_fit = pool["part"].isin(("train", "dev"))
    pool["exclusion_reason"] = reason.where(in_fit, "")
    steps["train_dev_rows_before_s3_exclusion"] = int(in_fit.sum())
    steps["train_dev_rows_excluded_pair"] = int((pool["exclusion_reason"] == REASON_PAIR).sum())
    steps["train_dev_rows_excluded_group_only"] = int((pool["exclusion_reason"] == REASON_GROUP).sum())
    steps["train_dev_rows_pair_and_group"] = int((pd.Series(pair_hit, index=pool.index) & group_hit & in_fit).sum())

    usable = pool[pool["exclusion_reason"] == ""]
    parts = {name: usable[usable["part"] == name].copy() for name in ("train", "dev", "eval")}
    steps["train_rows_before_balance"] = len(parts["train"])
    class_before = class_table(parts["train"])

    # (e) balance train by down-sampling (never by duplication) --------------------
    floor = min(Counter(parts["train"]["gold_system"]).get(label, 0) for label in CLASSES)
    if floor == 0:
        raise ValueError("a class is empty in t1_synth_train")
    chosen = pd.concat([
        parts["train"][parts["train"]["gold_system"] == label].sample(n=floor, random_state=SEED)
        for label in CLASSES
    ])
    balanced_keys = set(chosen["key"])
    downsampled = parts["train"][~parts["train"]["key"].isin(balanced_keys)].copy()
    downsampled["exclusion_reason"] = REASON_BALANCE
    parts["train"] = parts["train"][parts["train"]["key"].isin(balanced_keys)]
    steps["train_rows_downsampled"] = len(downsampled)

    excluded = pd.concat([pool[pool["exclusion_reason"] != ""], downsampled], ignore_index=True)

    # (f) Data 06 held-out: evaluation only ----------------------------------------
    kept06, _ = filter_benchmark(data06, TEXT_COLUMN, index=index)
    heldout = to_pool(kept06.reset_index(drop=True), "data06", "Lai", mapping)
    train_groups = set(parts["train"]["admin_group_key"])
    heldout["group_seen_in_synth_train"] = heldout["admin_group_key"].isin(train_groups)
    # Scoring-side flag: the same surface is a verified *old* address in Data 03.
    data03_normalized = set(load_csv(repo / DATA03, (TEXT_COLUMN,))[TEXT_COLUMN].map(normalize_for_overlap))
    heldout["same_text_labelled_cu_in_data03"] = heldout["text"].map(normalize_for_overlap).isin(data03_normalized)
    measured.update({"data06_rows": len(data06), "data06_kept": len(heldout),
                     "data06_kept_groups": int(heldout["admin_group_key"].nunique())})

    return {
        "parts": parts, "heldout": heldout, "excluded": excluded, "steps": steps, "measured": measured,
        "holdout_stats": holdout["stats"], "holdout_pairs": len(holdout["pairs"]),
        "holdout_groups": len(holdout["groups"]), "class_before_balance": class_before,
        "mapping_path": mapping_path, "corpus_sha256": index.corpus_sha256,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    if output.exists():
        raise SystemExit(f"{output} already exists; refusing to overwrite. Use a _v2 directory.")

    result = build(ROOT)
    parts, heldout = result["parts"], result["heldout"]
    mismatches = {name: {"expected": value, "measured": result["measured"].get(name)}
                  for name, value in EXPECTED.items() if result["measured"].get(name) != value}

    output.mkdir(parents=True)
    files = {}
    for name, frame, columns in (
        ("t1_synth_train.csv", parts["train"], OUTPUT_COLUMNS),
        ("t1_synth_dev.csv", parts["dev"], OUTPUT_COLUMNS),
        ("t1_synth_eval.csv", parts["eval"], OUTPUT_COLUMNS),
        ("t1_data06_heldout.csv", heldout, OUTPUT_COLUMNS + ["group_seen_in_synth_train", "same_text_labelled_cu_in_data03"]),
        ("t1_synth_excluded.csv", result["excluded"], OUTPUT_COLUMNS + ["part", "exclusion_reason"]),
    ):
        ordered = frame.sort_values("key")[columns]
        ordered.to_csv(output / name, index=False, encoding="utf-8-sig", lineterminator="\n")
        files[name] = {"rows": len(ordered), "columns": columns, "sha256": sha256_file(output / name),
                       "duplicate_text_rows": int(ordered["text"].duplicated().sum())}

    group_sets = {name: set(frame.loc[~frame["unresolved_group"], "admin_group_key"]) for name, frame in parts.items()}
    summary = {
        "classes": {name: class_table(frame) for name, frame in parts.items()},
        "train_classes_before_balance": result["class_before_balance"],
        "resolved_groups": {name: len(groups) for name, groups in group_sets.items()},
        "group_overlap": {"train_dev": len(group_sets["train"] & group_sets["dev"]),
                          "train_eval": len(group_sets["train"] & group_sets["eval"]),
                          "dev_eval": len(group_sets["dev"] & group_sets["eval"])},
        "unresolved_rows": {name: int(frame["unresolved_group"].sum()) for name, frame in parts.items()},
        "eval_rows_by_source": dict(Counter(parts["eval"]["source"])),
        "eval_unresolved_by_class": dict(Counter(parts["eval"].loc[parts["eval"]["unresolved_group"], "gold_system"])),
        "data06_heldout": {
            "rows": len(heldout),
            "kieu_lai": dict(Counter(heldout["KieuLai"].str[:2])),
            "groups": int(heldout["admin_group_key"].nunique()),
            "rows_group_seen_in_synth_train": int(heldout["group_seen_in_synth_train"].sum()),
            "rows_group_unseen": int((~heldout["group_seen_in_synth_train"]).sum()),
            "groups_unseen": int(heldout.loc[~heldout["group_seen_in_synth_train"], "admin_group_key"].nunique()),
            "rows_same_text_labelled_cu_in_data03": int(heldout["same_text_labelled_cu_in_data03"].sum()),
        },
        # Data-level check that no class follows from "has a district" alone.
        "district_only_baseline_oracle_column": district_majority_baseline(parts["train"], parts["eval"]),
    }
    manifest = {
        "script_version": SCRIPT_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": SEED,
        "generator": {"function": "src.data.synthetic.hybrid_address.generate_hybrid_addresses",
                      "target_size": TARGET_SIZE, "seed": SEED},
        "split_fractions_of_groups": dict(zip(("train", "dev", "eval"), SPLIT_FRACTIONS)),
        "label_scope": "T1 string-level labels only; not valid as T0 span labels",
        "inputs_sha256": {
            str(OLD_SNAPSHOT): sha256_file(ROOT / OLD_SNAPSHOT), str(DATA01): sha256_file(ROOT / DATA01),
            str(DATA03): sha256_file(ROOT / DATA03), str(DATA06): sha256_file(ROOT / DATA06),
            "reference/vietnam-sap-nhap-phuong-xa.csv": sha256_file(result["mapping_path"]),
            **{f"corpus/{name}": digest for name, digest in result["corpus_sha256"].items()},
            "corpus/manifest.json": sha256_file(ROOT / DEFAULT_CORPUS_DIR / "manifest.json"),
        },
        "code_sha256": {name: sha256_file(ROOT / name) for name in SOURCE_FILES},
        "reproduction": {"expected": EXPECTED, "measured": result["measured"], "mismatches": mismatches},
        "sprint3_dev_test_filter": {
            "group_key_definition": "admin_group_key(first TinhThanh, first QuanHuyen or '', first PhuongXa) "
                                    "over all samples of the split",
            "stats": result["holdout_stats"], "distinct_pairs": result["holdout_pairs"],
            "resolved_groups": result["holdout_groups"],
            "note": "the WP2 prompt quotes 23/40 (dev) and 34/48 (test) for the subset of samples "
                    "having both a PhuongXa and a TinhThanh span",
        },
        "steps": result["steps"],
        "summary": summary,
        "outputs": files,
    }
    (output / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"steps": result["steps"], "summary": summary, "mismatches": mismatches},
                     ensure_ascii=False, indent=1))
    return 2 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
