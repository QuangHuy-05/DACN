"""Inventory Sprint 3 sources and prepare a leakage-aware T0 annotation batch.

This is a candidate queue, not span gold. It uses only the Python standard
library and never changes raw data or the frozen benchmark CSVs.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import re
import unicodedata
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = ROOT / "data/processed/benchmark"
OSM_DIR = ROOT / "data/interim/osm"
VQA_PATH = ROOT / "data/interim/vqa/viet_receipt_raw_addresses.csv"
MAPPING_PATH = ROOT / "data/reference/administrative_units/vietnam-sap-nhap-phuong-xa.csv"
RARE_SEEDS_PATH = ROOT / "configs/span11_rare_seed_examples.json"
OUT_DIR = ROOT / "data/interim/annotation/sprint03"
SEED = 42
GUIDELINE_VERSION = "s3-span-v1.0"
BENCHMARK_QUOTA = 20
PILOT_QUOTA = 24
VQA_QUOTA = 20
RARE_QUOTA = 20

BENCHMARK_FILES = {
    "01_new": "01_full_address_new_verified.csv",
    "02_noisy": "02_raw_noisy_synthetic_1000.csv",
    "03_old": "03_real_address_old_1500.csv",
    "04_missing": "04_missing_fields_800.csv",
    "06_hybrid": "06_hybrid_addresses_600.csv",
}
FIELD_NAMES = (
    "sample_id", "text", "source_dataset", "source_row", "source_ref",
    "source_file_sha256", "group_id", "planned_role", "stratum",
    "candidate_rare", "review_flag", "derivation", "parent_sample_id",
)
LANDMARK_CUES = re.compile(r"\b(?:gần|đối diện|cạnh|bên cạnh|chợ|cầu|bệnh viện|ngã tư)\b", re.I)
SENSITIVE_CUES = re.compile(r"(?:\b0\d{9,10}\b|\S+@\S+|\b(?:khách hàng|người nhận|điện thoại)\b)", re.I)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@lru_cache(maxsize=None)
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
    # Administrative matching keeps accents and unit types. Never infer a
    # mapping from an accent-insensitive or abbreviated name alone.
    return " ".join(unicodedata.normalize("NFC", (value or "").strip()).split())


def site_group(house: str, street: str, fallback: str) -> str:
    # Group by house + street across all provinces. This may over-group common
    # addresses, but prevents old/new and synthetic variants crossing splits.
    house_key, street_key = normalize_key(house), normalize_key(street)
    key = f"site|{house_key}|{street_key}" if house_key and street_key else f"surface|{normalize_key(fallback)}"
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


def make_candidate(
    text: str, dataset: str, row_number: int, source_path: Path,
    group_id: str, planned_role: str, stratum: str, *,
    review_flag: str = "", derivation: str = "observed_or_existing_benchmark",
    parent_sample_id: str = "", candidate_rare: str = "",
) -> dict[str, str]:
    source_digest = file_sha256(source_path)
    stable_key = f"{dataset}|{row_number}|{sha256_bytes(text.encode('utf-8'))}"
    return {
        "sample_id": "s3_" + sha256_bytes(stable_key.encode("utf-8"))[:16],
        "text": text,
        "source_dataset": dataset,
        "source_row": str(row_number),
        "source_ref": source_path.relative_to(ROOT).as_posix(),
        "source_file_sha256": source_digest,
        "group_id": group_id,
        "planned_role": planned_role,
        "stratum": stratum,
        "candidate_rare": candidate_rare,
        "review_flag": review_flag,
        "derivation": derivation,
        "parent_sample_id": parent_sample_id,
    }


def ordered_rows(rows: list[dict[str, str]], namespace: str) -> list[tuple[int, dict[str, str]]]:
    rng = random.Random(f"{SEED}:{namespace}")
    indexed = [(int(row["_source_line"]), row) for row in rows]
    rng.shuffle(indexed)
    return indexed


def select_rows(
    rows: list[dict[str, str]], dataset: str, source_path: Path,
    quota: int, role: str, stratum: str, used_groups: set[str],
    subgroup_quotas: tuple[str, dict[str, int]] | None = None,
) -> list[dict[str, str]]:
    selected = []
    buckets = [(None, quota)] if subgroup_quotas is None else list(subgroup_quotas[1].items())
    if sum(count for _, count in buckets) != quota:
        raise ValueError(f"{dataset}: subgroup quotas do not sum to {quota}")
    for subgroup, target_count in buckets:
        selected_count = 0
        for line_number, row in ordered_rows(rows, f"{dataset}:{subgroup}"):
            if subgroup is not None and row.get(subgroup_quotas[0]) != subgroup:
                continue
            text = row.get("ChuoiDiaChi", "").strip()
            group_id = row_group(row)
            if not text or group_id in used_groups:
                continue
            selected.append(make_candidate(text, dataset, line_number, source_path, group_id, role, stratum))
            used_groups.add(group_id)
            selected_count += 1
            if selected_count == target_count:
                break
        if selected_count != target_count:
            raise ValueError(f"{dataset}/{subgroup}: selected only {selected_count}/{target_count} groups")
    if len(selected) != quota:
        raise ValueError(f"{dataset}: selected only {len(selected)}/{quota} distinct groups")
    return selected


def load_mapping() -> tuple[set[tuple[str, str]], dict[tuple[str, str, str], set[tuple[str, str]]]]:
    rows = read_csv(MAPPING_PATH, (
        "Phường/Xã cũ", "Quận/Huyện cũ", "Tỉnh/TP cũ (trước sáp nhập)",
        "Tỉnh/TP mới", "Phường/Xã mới (từ 1/7/2025)",
    ))
    current_units = set()
    old_to_new: dict[tuple[str, str, str], set[tuple[str, str]]] = defaultdict(set)
    for row in rows:
        target = (row["Tỉnh/TP mới"], row["Phường/Xã mới (từ 1/7/2025)"])
        current_units.add((admin_key(target[0]), admin_key(target[1])))
        old_key = tuple(admin_key(row[key]) for key in (
            "Tỉnh/TP cũ (trước sáp nhập)", "Quận/Huyện cũ", "Phường/Xã cũ",
        ))
        old_to_new[old_key].add(target)
    return current_units, old_to_new


def new_pilot_pool(
    rows: list[dict[str, str]], current_units: set[tuple[str, str]],
    old_to_new: dict[tuple[str, str, str], set[tuple[str, str]]],
) -> list[dict[str, str]]:
    pool = []
    for row in rows:
        if not all(row.get(key, "").strip() for key in ("SoNha", "TenDuong", "PhuongXa", "TinhThanh")):
            continue
        if not row.get("QuanHuyen", "").strip() and (
            admin_key(row["TinhThanh"]), admin_key(row["PhuongXa"])
        ) in current_units:
            new_row = dict(row)
            new_row["_derivation"] = "observed_verified_current_unit"
        else:
            old_key = tuple(admin_key(row.get(key, "")) for key in (
                "TinhThanh", "QuanHuyen", "PhuongXa",
            ))
            targets = old_to_new.get(old_key, set())
            if len(targets) != 1:
                continue  # Never force a split/M-N old unit to one destination.
            province, ward = next(iter(targets))
            new_row = dict(row)
            new_row["PhuongXa"] = ward
            new_row["QuanHuyen"] = ""
            new_row["TinhThanh"] = province
            new_row["_derivation"] = "derived_verified_unique_admin_mapping"
        new_row["ChuoiDiaChi"] = ", ".join(
            new_row[key] for key in ("SoNha", "TenDuong", "PhuongXa", "TinhThanh")
        )
        pool.append(new_row)
    return pool


def reserve_benchmark_groups(benchmarks: dict[str, list[dict[str, str]]]) -> set[str]:
    groups = {row_group(row) for rows in benchmarks.values() for row in rows}
    pair_path = BENCHMARK_DIR / "07_bidirectional_pairs_verified.csv"
    for row in read_csv(pair_path, ("ID_Node", "DiaChi_Cu", "DiaChi_Moi")):
        for key in ("DiaChi_Cu", "DiaChi_Moi"):
            parts = [part.strip() for part in row[key].split(",")]
            if len(parts) >= 2:
                groups.add(site_group(parts[0], parts[1], row[key]))
    return groups


def select_pilot(
    dataset: str, path: Path, pool: list[dict[str, str]],
    frozen_groups: set[str], used_groups: set[str], quota: int,
) -> list[dict[str, str]]:
    selected = []
    for line_number, row in ordered_rows(pool, dataset):
        group_id = row_group(row)
        if group_id in frozen_groups or group_id in used_groups:
            continue
        text = row.get("ChuoiDiaChi", "").strip()
        if not text:
            continue
        selected.append(make_candidate(
            text, dataset, line_number, path, group_id, "pilot_train_pool",
            dataset, derivation=row.get("_derivation", "observed_osm"),
        ))
        used_groups.add(group_id)
        if len(selected) == quota:
            break
    if len(selected) != quota:
        raise ValueError(f"{dataset}: selected only {len(selected)}/{quota} non-benchmark groups")
    return selected


def add_rare_pilot() -> list[dict[str, str]]:
    if not RARE_SEEDS_PATH.is_file():
        raise FileNotFoundError(RARE_SEEDS_PATH)
    seeds = json.loads(RARE_SEEDS_PATH.read_text(encoding="utf-8"))
    if len(seeds) != RARE_QUOTA:
        raise ValueError(f"Rare seed count {len(seeds)} != {RARE_QUOTA}")
    selected = []
    for index, seed in enumerate(seeds, start=1):
        if not all(seed.get(key) for key in ("text", "candidate_rare", "family")):
            raise ValueError(f"Rare seed {index} missing text, candidate_rare, or family")
        group_id = "seed_" + sha256_bytes(seed["family"].encode("utf-8"))[:20]
        selected.append(make_candidate(
            seed["text"], "controlled_rare_seed", index, RARE_SEEDS_PATH,
            group_id, "pilot_train_pool", "pilot_rare_candidate",
            review_flag="synthetic_example_review_required",
            derivation="controlled_synthetic_example_no_geographic_pair_claim",
            candidate_rare=seed["candidate_rare"],
        ))
    return selected


def select_vqa(used_text: set[str]) -> tuple[list[dict[str, str]], dict[str, int]]:
    rows = read_csv(VQA_PATH, ("ChuoiDiaChi",))
    eligible = [(line, row) for line, row in ordered_rows(rows, "vqa")
                if not SENSITIVE_CUES.search(row["ChuoiDiaChi"])
                and normalize_key(row["ChuoiDiaChi"]) not in used_text]
    landmark = [(line, row) for line, row in eligible if LANDMARK_CUES.search(row["ChuoiDiaChi"])]
    others = [(line, row) for line, row in eligible if not LANDMARK_CUES.search(row["ChuoiDiaChi"])]
    picked = landmark[: min(10, len(landmark))] + others[: VQA_QUOTA - min(10, len(landmark))]
    if len(picked) != VQA_QUOTA:
        raise ValueError(f"VQA: selected only {len(picked)}/{VQA_QUOTA}")
    selected = []
    for line_number, row in picked:
        text = row["ChuoiDiaChi"]
        # The interim CSV has no receipt/document ID. Keep every VQA item in
        # external hold; surface hash is provisional, not an identity claim.
        group_id = "vqa_" + sha256_bytes(normalize_key(text).encode("utf-8"))[:20]
        selected.append(make_candidate(
            text, "viet_receipt_vqa", line_number, VQA_PATH, group_id,
            "external_test_hold", "vqa_landmark_candidate" if LANDMARK_CUES.search(text) else "vqa_other",
            review_flag="privacy_and_document_group_review_required",
            derivation="filtered_real_receipt_address",
            candidate_rare="MocDinhVi" if LANDMARK_CUES.search(text) else "",
        ))
    return selected, {"total": len(rows), "sensitive_cue_count": sum(bool(SENSITIVE_CUES.search(r["ChuoiDiaChi"])) for r in rows),
                      "landmark_cue_count": sum(bool(LANDMARK_CUES.search(r["ChuoiDiaChi"])) for r in rows),
                      "document_id_available": 0}


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELD_NAMES)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    benchmark_rows = {}
    inputs = {}
    for dataset, filename in BENCHMARK_FILES.items():
        path = BENCHMARK_DIR / filename
        benchmark_rows[dataset] = read_csv(path, ("ChuoiDiaChi", "SoNha", "TenDuong"))
        inputs[path.relative_to(ROOT).as_posix()] = {"rows": len(benchmark_rows[dataset]), "sha256": file_sha256(path)}
    frozen_groups = reserve_benchmark_groups(benchmark_rows)
    pair_path = BENCHMARK_DIR / "07_bidirectional_pairs_verified.csv"
    pair_rows = read_csv(pair_path, ("ID_Node", "DiaChi_Cu", "DiaChi_Moi"))
    inputs[pair_path.relative_to(ROOT).as_posix()] = {"rows": len(pair_rows), "sha256": file_sha256(pair_path)}

    benchmark_selected = []
    selected_groups: set[str] = set()
    subgroup_plan = {
        "02_noisy": ("MucDoNhieu", {"nhe": 7, "vua": 7, "nang": 6}),
        "04_missing": ("KieuThieu", {
            "drop_district": 5, "drop_housenumber": 5,
            "drop_ward": 5, "drop_housenumber_ward": 5,
        }),
        "06_hybrid": ("KieuLai", {
            "C1_PhuongMoi_QuanCu_TinhCu": 10,
            "C2_PhuongMoi_QuanCu_TinhMoi": 5,
            "C3_PhuongCu_QuanCu_TinhMoi": 5,
        }),
    }
    for dataset, filename in BENCHMARK_FILES.items():
        benchmark_selected.extend(select_rows(
            benchmark_rows[dataset], dataset, BENCHMARK_DIR / filename,
            BENCHMARK_QUOTA, "frozen_benchmark_test_hold", dataset,
            selected_groups, subgroup_plan.get(dataset),
        ))

    old_path = OSM_DIR / "osm_old_snapshot_20250630.csv"
    latest_path = OSM_DIR / "osm_latest_clean.csv"
    old_rows = read_csv(old_path, ("OSM_Type", "OSM_ID", "SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh", "ChuoiDiaChi"))
    latest_rows = read_csv(latest_path, ("SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh", "ChuoiDiaChi"))
    current_units, old_to_new = load_mapping()
    old_pool = [row for row in old_rows if all(row.get(key, "").strip() for key in (
        "SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh"))
        and tuple(admin_key(row[key]) for key in ("TinhThanh", "QuanHuyen", "PhuongXa")) in old_to_new]
    new_pool = new_pilot_pool(latest_rows, current_units, old_to_new)
    for path, count in ((old_path, len(old_rows)), (latest_path, len(latest_rows)),
                        (MAPPING_PATH, len(read_csv(MAPPING_PATH, ("Phường/Xã cũ",))))):
        inputs[path.relative_to(ROOT).as_posix()] = {"rows": count, "sha256": file_sha256(path)}

    pilot_groups = set(selected_groups)
    old_pilot = select_pilot("osm_old_pilot", old_path, old_pool, frozen_groups, pilot_groups, PILOT_QUOTA)
    new_pilot = select_pilot("osm_new_pilot", latest_path, new_pool, frozen_groups, pilot_groups, PILOT_QUOTA)
    rare_pilot = add_rare_pilot()
    inputs[RARE_SEEDS_PATH.relative_to(ROOT).as_posix()] = {
        "rows": RARE_QUOTA, "sha256": file_sha256(RARE_SEEDS_PATH),
    }

    used_text = {normalize_key(row["text"]) for row in benchmark_selected + old_pilot + new_pilot + rare_pilot}
    vqa_selected, vqa_stats = select_vqa(used_text)
    inputs[VQA_PATH.relative_to(ROOT).as_posix()] = {"rows": vqa_stats["total"], "sha256": file_sha256(VQA_PATH)}

    queue = old_pilot + new_pilot + rare_pilot + benchmark_selected + vqa_selected
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    queue_path = OUT_DIR / "annotation_queue_batch01.csv"
    import_path = OUT_DIR / "label_studio_pilot_import.json"
    manifest_path = ROOT / "docs/sprints/sprint_03/annotation_batch01_manifest.json"
    write_csv(queue_path, queue)
    pilot = [row for row in queue if row["planned_role"] == "pilot_train_pool"]
    # Only pilot tasks can be imported now. Benchmark test and VQA stay held.
    tasks = [{"data": {"text": row["text"], "sample_id": row["sample_id"]}} for row in pilot]
    import_path.write_text(json.dumps(tasks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "batch_id": "s3_span_batch01", "guideline_version": GUIDELINE_VERSION,
        "seed": SEED, "status": "candidate_only_no_gold",
        "roles": dict(Counter(row["planned_role"] for row in queue)),
        "strata": dict(Counter(row["stratum"] for row in queue)),
        "test_subgroup_quotas": {key: {"field": field, "quotas": quotas}
                                 for key, (field, quotas) in subgroup_plan.items()},
        "rare_candidates": dict(Counter(row["candidate_rare"] for row in queue if row["candidate_rare"])),
        "input_files": inputs,
        "frozen_benchmark_group_count": len(frozen_groups),
        "selected_unique_groups": len({row["group_id"] for row in queue}),
        "vqa": vqa_stats,
        "limitations": [
            "No span gold; candidate rare labels require human review.",
            "VQA interim has only ChuoiDiaChi, no receipt/document ID; external hold pending privacy and source-group review.",
            "Controlled rare examples are synthetic T0 pilot items, not verified address-geography pairs.",
            "Site grouping by normalized house and street is conservative but cannot prove all cross-source identities.",
            "Real HuongDi examples are absent from the present VQA candidate screen; collect a verified public source before final test.",
        ],
        "outputs": {
            queue_path.relative_to(ROOT).as_posix(): file_sha256(queue_path),
            import_path.relative_to(ROOT).as_posix(): file_sha256(import_path),
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"queue_rows": len(queue), "roles": manifest["roles"],
                      "strata": manifest["strata"], "vqa": vqa_stats,
                      "output": OUT_DIR.as_posix()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
