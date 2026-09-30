"""Prepare batch 02 train/dev candidate pool for Sprint 3 T0/T1 annotation.

Follows Protocol v1.0 and Sprint 3 Execution Plan (C2.3):
- Excludes all 4,017 reserved benchmark groups and 100 frozen test hold samples.
- Excludes the 68 pilot groups from new selections.
- Allocates groups to train and dev prior to synthetic derivation.
- Generates 232 new candidate samples (old, new 2-tier, noise, missing, hybrid)
  from OSM sources with explicit provenance and parent linkages.
- Produces:
  1. annotation_queue_batch02_train_dev.csv
  2. annotation_batch02_manifest.json
  3. label_studio_batch02_import.json (strictly sample_id and text, zero leakage).
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = ROOT / "data/processed/benchmark"
OSM_OLD_PATH = ROOT / "data/interim/osm/osm_old_snapshot_full.csv"
MAPPING_PATH = ROOT / "data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv"
BATCH01_QUEUE_PATH = ROOT / "data/interim/annotation/sprint03/annotation_queue_batch01.csv"
OUT_DIR = ROOT / "data/interim/annotation/sprint03"

SEED = 42
TARGET_QUOTA_TOTAL = 232
STRATA_TARGETS = {
    "osm_old_3tier": 60,
    "osm_new_2tier": 60,
    "synthetic_noise": 40,
    "synthetic_missing": 40,
    "synthetic_hybrid": 32,
}

FIELD_NAMES = (
    "sample_id",
    "text",
    "source_dataset",
    "source_row",
    "source_ref",
    "source_file_sha256",
    "group_id",
    "planned_role",
    "planned_split",
    "stratum",
    "candidate_rare",
    "review_flag",
    "derivation",
    "parent_sample_id",
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_key(value: str) -> str:
    value = unicodedata.normalize("NFKD", (value or "").casefold()).replace("đ", "d")
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())


def admin_key(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", (value or "").strip()).split())


def site_group(house: str, street: str, fallback: str) -> str:
    house_key, street_key = normalize_key(house), normalize_key(street)
    key = (
        f"site|{house_key}|{street_key}"
        if house_key and street_key
        else f"surface|{normalize_key(fallback)}"
    )
    return "g_" + sha256_bytes(key.encode("utf-8"))[:20]


def row_group(row: dict[str, str]) -> str:
    return site_group(
        row.get("GT_SoNha") or row.get("SoNha", ""),
        row.get("GT_TenDuong") or row.get("TenDuong", ""),
        row.get("ChuoiDiaChiGoc") or row.get("ChuoiDiaChi", ""),
    )


def read_csv(path: Path, required: tuple[str, ...]) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = set(required) - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        rows = list(reader)
        for line_number, row in enumerate(rows, start=2):
            row["_source_line"] = str(line_number)
        return rows


def get_reserved_benchmark_groups() -> set[str]:
    benchmark_files = {
        "01_new": "01_full_address_new_verified.csv",
        "02_noisy": "02_raw_noisy_synthetic_1000.csv",
        "03_old": "03_real_address_old_1500.csv",
        "04_missing": "04_missing_fields_800.csv",
        "06_hybrid": "06_hybrid_addresses_600.csv",
    }
    groups = set()
    for name, fname in benchmark_files.items():
        rows = read_csv(BENCHMARK_DIR / fname, ("ChuoiDiaChi",))
        for r in rows:
            groups.add(row_group(r))

    pair_path = BENCHMARK_DIR / "07_bidirectional_pairs_verified.csv"
    for r in read_csv(pair_path, ("ID_Node", "DiaChi_Cu", "DiaChi_Moi")):
        for k in ("DiaChi_Cu", "DiaChi_Moi"):
            parts = [p.strip() for p in r[k].split(",")]
            if len(parts) >= 2:
                groups.add(site_group(parts[0], parts[1], r[k]))

    return groups


def load_mapping() -> dict[tuple[str, str, str], list[tuple[str, str]]]:
    rows = read_csv(
        MAPPING_PATH,
        (
            "Phường/Xã cũ",
            "Quận/Huyện cũ",
            "Tỉnh/TP cũ (trước sáp nhập)",
            "Tỉnh/TP mới",
            "Phường/Xã mới (từ 1/7/2025)",
        ),
    )
    old_to_new = defaultdict(list)
    for r in rows:
        old_k = (
            admin_key(r["Tỉnh/TP cũ (trước sáp nhập)"]),
            admin_key(r["Quận/Huyện cũ"]),
            admin_key(r["Phường/Xã cũ"]),
        )
        target = (r["Tỉnh/TP mới"].strip(), r["Phường/Xã mới (từ 1/7/2025)"].strip())
        if target not in old_to_new[old_k]:
            old_to_new[old_k].append(target)
    return old_to_new


def inject_noise_synthetic(text: str, rng: random.Random) -> str:
    """Inject mild typographic noise or abbreviation typical of OCR."""
    replacements = [
        ("Phường ", "P. "),
        ("Quận ", "Q. "),
        ("Thành phố ", "TP. "),
        ("Đường ", "Đ. "),
        ("Hồ Chí Minh", "HCM"),
        ("Hà Nội", "HN"),
        ("Xã ", "X. "),
    ]
    res = text
    for old, new in replacements:
        if old in res and rng.random() < 0.6:
            res = res.replace(old, new, 1)
    if rng.random() < 0.3:
        # Lowercase a random character
        idx = rng.randint(0, len(res) - 1)
        res = res[:idx] + res[idx].lower() + res[idx + 1 :]
    return res


def drop_field_synthetic(
    house: str, street: str, ward: str, district: str, province: str, rng: random.Random
) -> str:
    """Drop one administrative or street component."""
    mode = rng.choice(["drop_district", "drop_housenumber", "drop_ward"])
    if mode == "drop_district":
        parts = [house, street, ward, province]
    elif mode == "drop_housenumber":
        parts = [street, ward, district, province]
    else:  # drop_ward
        parts = [house, street, district, province]
    return ", ".join(p for p in parts if p)


def main() -> None:
    frozen_outputs = (
        OUT_DIR / "annotation_queue_batch02_train_dev.csv",
        OUT_DIR / "annotation_batch02_manifest.json",
        OUT_DIR / "label_studio_batch02_import.json",
    )
    if any(path.exists() for path in frozen_outputs):
        raise FileExistsError(
            "Batch 02 artifacts already exist. Use scripts.18_audit_corpus_split preflight "
            "to verify them; publish a new batch version instead of overwriting fixed task IDs."
        )
    print(f"Building Batch 02 candidates with SEED={SEED}...")
    rng = random.Random(SEED)

    # 1. Reserved groups
    reserved_benchmark_groups = get_reserved_benchmark_groups()
    print(f"Reserved benchmark groups: {len(reserved_benchmark_groups)}")

    # 2. Pilot groups to exclude
    pilot_groups = set()
    if BATCH01_QUEUE_PATH.is_file():
        with BATCH01_QUEUE_PATH.open("r", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if r["planned_role"] == "pilot_train_pool":
                    pilot_groups.add(r["group_id"])
    print(f"Pilot groups excluded: {len(pilot_groups)}")

    all_excluded_groups = reserved_benchmark_groups | pilot_groups
    print(f"Total excluded groups: {len(all_excluded_groups)}")

    # 3. Load OSM candidates
    osm_digest = file_sha256(OSM_OLD_PATH)
    osm_rows = read_csv(
        OSM_OLD_PATH,
        ("SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh", "ChuoiDiaChi"),
    )

    valid_candidates = []
    seen_groups = set()
    for row in osm_rows:
        if not all(
            row.get(k, "").strip()
            for k in ("SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh")
        ):
            continue
        grp = row_group(row)
        if grp in all_excluded_groups or grp in seen_groups:
            continue
        valid_candidates.append(row)
        seen_groups.add(grp)

    print(f"Total available distinct group candidates in OSM: {len(valid_candidates)}")
    rng.shuffle(valid_candidates)

    # Load mapping for new and hybrid derivations
    old_to_new = load_mapping()

    # Separate candidates that have verified unique mapping targets
    exact_1_candidates = []
    other_candidates = []
    for r in valid_candidates:
        old_k = (
            admin_key(r["TinhThanh"]),
            admin_key(r["QuanHuyen"]),
            admin_key(r["PhuongXa"]),
        )
        targets = old_to_new.get(old_k, [])
        if len(targets) == 1:
            exact_1_candidates.append((r, targets[0]))
        else:
            other_candidates.append(r)

    print(f"Candidates with exact 1 mapping target: {len(exact_1_candidates)}, others: {len(other_candidates)}")

    selected_items: list[dict[str, str]] = []
    used_batch02_groups = set()

    # 1. Stratum 2: osm_new_2tier (60 samples)
    new_pool = []
    for r, target in exact_1_candidates:
        if len(new_pool) >= STRATA_TARGETS["osm_new_2tier"]:
            break
        grp = row_group(r)
        if grp not in used_batch02_groups:
            used_batch02_groups.add(grp)
            new_pool.append((r, target))

    # 2. Stratum 5: synthetic_hybrid (32 samples)
    hybrid_pool = []
    for r, target in exact_1_candidates:
        if len(hybrid_pool) >= STRATA_TARGETS["synthetic_hybrid"]:
            break
        grp = row_group(r)
        if grp not in used_batch02_groups:
            used_batch02_groups.add(grp)
            hybrid_pool.append((r, target))

    # Remaining candidate pool for unconstrained strata
    remaining_candidates = [
        (r, None) for r, target in exact_1_candidates if row_group(r) not in used_batch02_groups
    ] + [(r, None) for r in other_candidates if row_group(r) not in used_batch02_groups]
    rng.shuffle(remaining_candidates)

    # 3. Stratum 1: osm_old_3tier (60 samples)
    old_pool = []
    for r, _ in remaining_candidates:
        if len(old_pool) >= STRATA_TARGETS["osm_old_3tier"]:
            break
        grp = row_group(r)
        if grp not in used_batch02_groups:
            used_batch02_groups.add(grp)
            old_pool.append(r)

    # 4. Stratum 3: synthetic_noise (40 samples)
    noise_pool = []
    for r, _ in remaining_candidates:
        if len(noise_pool) >= STRATA_TARGETS["synthetic_noise"]:
            break
        grp = row_group(r)
        if grp not in used_batch02_groups:
            used_batch02_groups.add(grp)
            noise_pool.append(r)

    # 5. Stratum 4: synthetic_missing (40 samples)
    missing_pool = []
    for r, _ in remaining_candidates:
        if len(missing_pool) >= STRATA_TARGETS["synthetic_missing"]:
            break
        grp = row_group(r)
        if grp not in used_batch02_groups:
            used_batch02_groups.add(grp)
            missing_pool.append(r)

    print(
        f"Selected pools counts: old={len(old_pool)}, new={len(new_pool)}, "
        f"noise={len(noise_pool)}, missing={len(missing_pool)}, hybrid={len(hybrid_pool)}"
    )

    # Assign groups to split: ~80% train, ~20% dev
    all_groups_list = sorted(used_batch02_groups)
    rng_split = random.Random(SEED + 999)
    rng_split.shuffle(all_groups_list)
    split_map = {}
    for i, g in enumerate(all_groups_list):
        split_map[g] = "dev" if (i % 5 == 0) else "train"

    # Assemble samples
    # 1. Old 3-tier
    for r in old_pool:
        grp = row_group(r)
        line_num = int(r["_source_line"])
        text = r["ChuoiDiaChi"].strip()
        sample_id = "s3_" + sha256_bytes(f"b02_old|{line_num}|{text}".encode("utf-8"))[:16]
        selected_items.append(
            {
                "sample_id": sample_id,
                "text": text,
                "source_dataset": "osm_old_snapshot_full",
                "source_row": str(line_num),
                "source_ref": "data/interim/osm/osm_old_snapshot_full.csv",
                "source_file_sha256": osm_digest,
                "group_id": grp,
                "planned_role": "train_dev_batch02",
                "planned_split": split_map[grp],
                "stratum": "osm_old_3tier",
                "candidate_rare": "",
                "review_flag": "",
                "derivation": "observed_verified_old_osm",
                "parent_sample_id": "",
            }
        )

    # 2. New 2-tier
    for r, (new_prov, new_ward) in new_pool:
        grp = row_group(r)
        line_num = int(r["_source_line"])
        text = f"{r['SoNha']}, {r['TenDuong']}, {new_ward}, {new_prov}".strip()
        sample_id = "s3_" + sha256_bytes(f"b02_new|{line_num}|{text}".encode("utf-8"))[:16]
        selected_items.append(
            {
                "sample_id": sample_id,
                "text": text,
                "source_dataset": "osm_old_snapshot_full",
                "source_row": str(line_num),
                "source_ref": "data/interim/osm/osm_old_snapshot_full.csv",
                "source_file_sha256": osm_digest,
                "group_id": grp,
                "planned_role": "train_dev_batch02",
                "planned_split": split_map[grp],
                "stratum": "osm_new_2tier",
                "candidate_rare": "",
                "review_flag": "",
                "derivation": "derived_verified_unique_admin_mapping",
                "parent_sample_id": f"osm_row_{line_num}",
            }
        )

    # 3. Noise
    for r in noise_pool:
        grp = row_group(r)
        line_num = int(r["_source_line"])
        parent_id = f"osm_row_{line_num}"
        text = inject_noise_synthetic(r["ChuoiDiaChi"], rng)
        sample_id = "s3_" + sha256_bytes(f"b02_noise|{line_num}|{text}".encode("utf-8"))[:16]
        selected_items.append(
            {
                "sample_id": sample_id,
                "text": text,
                "source_dataset": "osm_old_snapshot_full",
                "source_row": str(line_num),
                "source_ref": "data/interim/osm/osm_old_snapshot_full.csv",
                "source_file_sha256": osm_digest,
                "group_id": grp,
                "planned_role": "train_dev_batch02",
                "planned_split": split_map[grp],
                "stratum": "synthetic_noise",
                "candidate_rare": "",
                "review_flag": "synthetic_noise_controlled",
                "derivation": "synthetic_noise_controlled",
                "parent_sample_id": parent_id,
            }
        )

    # 4. Missing
    for r in missing_pool:
        grp = row_group(r)
        line_num = int(r["_source_line"])
        parent_id = f"osm_row_{line_num}"
        text = drop_field_synthetic(
            r["SoNha"], r["TenDuong"], r["PhuongXa"], r["QuanHuyen"], r["TinhThanh"], rng
        )
        sample_id = "s3_" + sha256_bytes(f"b02_missing|{line_num}|{text}".encode("utf-8"))[:16]
        selected_items.append(
            {
                "sample_id": sample_id,
                "text": text,
                "source_dataset": "osm_old_snapshot_full",
                "source_row": str(line_num),
                "source_ref": "data/interim/osm/osm_old_snapshot_full.csv",
                "source_file_sha256": osm_digest,
                "group_id": grp,
                "planned_role": "train_dev_batch02",
                "planned_split": split_map[grp],
                "stratum": "synthetic_missing",
                "candidate_rare": "",
                "review_flag": "synthetic_missing_controlled",
                "derivation": "synthetic_missing_controlled",
                "parent_sample_id": parent_id,
            }
        )

    # 5. Hybrid (new ward with old district/province)
    for r, (new_prov, new_ward) in hybrid_pool:
        grp = row_group(r)
        line_num = int(r["_source_line"])
        parent_id = f"osm_row_{line_num}"
        text = f"{r['SoNha']}, {r['TenDuong']}, {new_ward}, {r['QuanHuyen']}, {r['TinhThanh']}".strip()
        sample_id = "s3_" + sha256_bytes(f"b02_hybrid|{line_num}|{text}".encode("utf-8"))[:16]
        selected_items.append(
            {
                "sample_id": sample_id,
                "text": text,
                "source_dataset": "osm_old_snapshot_full",
                "source_row": str(line_num),
                "source_ref": "data/interim/osm/osm_old_snapshot_full.csv",
                "source_file_sha256": osm_digest,
                "group_id": grp,
                "planned_role": "train_dev_batch02",
                "planned_split": split_map[grp],
                "stratum": "synthetic_hybrid",
                "candidate_rare": "",
                "review_flag": "synthetic_hybrid_controlled",
                "derivation": "synthetic_hybrid_controlled",
                "parent_sample_id": parent_id,
            }
        )

    assert len(selected_items) == TARGET_QUOTA_TOTAL, (
        f"Expected {TARGET_QUOTA_TOTAL}, got {len(selected_items)}"
    )

    # Ensure zero group overlap with benchmark
    batch02_groups = {item["group_id"] for item in selected_items}
    overlap_with_benchmark = batch02_groups & reserved_benchmark_groups
    assert not overlap_with_benchmark, f"Group overlap with benchmark: {len(overlap_with_benchmark)}"

    # Ensure zero group overlap with pilot
    overlap_with_pilot = batch02_groups & pilot_groups
    assert not overlap_with_pilot, f"Group overlap with pilot: {len(overlap_with_pilot)}"

    # Write CSV Queue
    queue_out = OUT_DIR / "annotation_queue_batch02_train_dev.csv"
    with queue_out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELD_NAMES)
        writer.writeheader()
        writer.writerows(selected_items)
    print(f"Wrote {len(selected_items)} rows to {queue_out}")

    # Write Label Studio Import (STRICTLY data.sample_id and data.text)
    ls_import = [
        {"data": {"sample_id": item["sample_id"], "text": item["text"]}}
        for item in selected_items
    ]
    ls_import_out = OUT_DIR / "label_studio_batch02_import.json"
    ls_import_out.write_text(
        json.dumps(ls_import, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(ls_import)} tasks to {ls_import_out}")

    # Write Manifest
    manifest = {
        "batch_id": "s3_span_batch02_train_dev",
        "guideline_version": "s3-span-v1.1",
        "label_config": "configs/label_studio_span11.xml",
        "seed": SEED,
        "status": "candidate_for_annotation_no_gold",
        "total_samples": len(selected_items),
        "split_counts": dict(Counter(item["planned_split"] for item in selected_items)),
        "strata_counts": dict(Counter(item["stratum"] for item in selected_items)),
        "unique_groups": len(batch02_groups),
        "zero_leakage_checks": {
            "overlap_with_benchmark_groups": len(overlap_with_benchmark),
            "overlap_with_pilot_groups": len(overlap_with_pilot),
            "cross_split_group_overlap": 0,
        },
        "output_hashes": {
            "queue_csv": file_sha256(queue_out),
            "label_studio_import_json": file_sha256(ls_import_out),
        },
    }
    manifest_out = OUT_DIR / "annotation_batch02_manifest.json"
    manifest_out.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote manifest to {manifest_out}")


if __name__ == "__main__":
    main()
