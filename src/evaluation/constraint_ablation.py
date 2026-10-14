"""Offline re-decoding of saved PhoBERT-CRF emissions to ablate the QuanHuyen decoding constraint (WP5).

Nothing here runs a neural model or builds an adapter: CRF parameters are read from checkpoints as raw
tensors (``extract_crf_params``, torch imported lazily), then every analysis re-decodes the emissions stored
in the frozen prediction files with a pure-Python Viterbi.  Gold is touched only by the scoring helpers,
after the re-decoding gate has passed.

Constraint under study: ban the BIO tags B-/I-QuanHuyen when a T1 source says the address is "moi"
(new two-level system has no district).  The T1 source is the only thing that varies between ablations.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from src.evaluation.schema import CharacterSpan, SpanModelOutput
from src.evaluation.span_features import BIO_LABELS, Token, decode_bio
from src.modeling.labels import bio_constraints
from src.modeling.structural_decoder import viterbi_reference

ROOT = Path(__file__).resolve().parents[2]
RULE_VERSION = "constraint_ablation_v1"
SEED = 20261014          # same bootstrap seed/size as src/evaluation/frozen_reliability.py
N_RESAMPLES = 10_000
N_TAGS = len(BIO_LABELS)
QUAN_HUYEN_IDS = [i for i, tag in enumerate(BIO_LABELS) if tag.endswith("-QuanHuyen")]
MAX_MISMATCH_EXAMPLES = 5

KAGGLE_REL = ("data/interim/modeling/sprint03/final_completion_20261005_v1/kaggle_final_output_v4/dacn_artifacts/"
              "dacn-s3-final-infer-20261005-v4/workspace/data/interim/modeling/sprint03/dacn-s3-final-infer-20261005-v4")
SELECTION_REL = "data/interim/modeling/sprint03/release_and_kaggle_20261005_v1"
SEED_REL = "data/interim/modeling/sprint04/multiseed_20261015_v1"
HEUR_TEST_REL = "data/interim/modeling/sprint03/final_completion_20261005_v1/light_test_runs_v2/heur-jw"
# Both five-field HEUR-JW runs use threshold 0.86; only the followup run shares the locked test config
# (adapter heur_jw_followup, rule heur_jw_compact_prefix_dual_snapshot_v4, gazetteer s3_v4_nso_dual_snapshot).
HEUR_5FIELD_REL = "data/processed/evaluation/sprint03/heur_jw_followup_fivefield_20261003_v1"

CHECKPOINTS = {
    "kaggle_dyn": (SELECTION_REL + "/dyn_c02_selection_artifacts_v1/dacn_artifacts/dacn-s3-dyn-c02-20261005-v1/workspace/"
                   "data/processed/evaluation/sprint03/dacn-s3-dyn-c02-20261005-v1_proposed_dyn_c02/checkpoints/best.pt",
                   "7a4a3d01"),
    "kaggle_pcrf": (SELECTION_REL + "/pcrf_c02_selection_artifacts_v2/dacn_artifacts/dacn-s3-pcrf-c02-20261005-v1/workspace/"
                    "data/processed/evaluation/sprint03/dacn-s3-pcrf-c02-20261005-v1_phobert_crf_c02/checkpoints/best.pt",
                    "19894a1e"),
    **{f"seed{s}_{m}": (f"{SEED_REL}/{m}_seed{s}/checkpoints/best.pt", None)
       for s in (42, 1337, 2025) for m in ("dyn", "pcrf")},
}


# ------------------------------------------------------------------ io helpers
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl_lines(path: Path):
    """Stream one JSON object per line (the five-field files are 54-90 MB)."""
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


# ------------------------------------------------------------ CRF parameters
def extract_crf_params(checkpoint_path: Path) -> dict:
    """Read start/end/transitions tensors from a checkpoint; no model is built and nothing is inferred."""
    import torch  # lazy: this function is only called in the neural runtime

    path = Path(checkpoint_path)
    if not path.exists():
        raise FileNotFoundError(path)
    try:
        payload = torch.load(path, map_location="cpu", weights_only=True)
        load_mode = "weights_only=True"
    except Exception:  # older pickles with non-tensor objects
        payload = torch.load(path, map_location="cpu", weights_only=False)
        load_mode = "weights_only=False"
    state = payload.get("model", payload) if isinstance(payload, dict) else payload
    found = {}
    for suffix in ("crf.start", "crf.end", "crf.transitions"):
        keys = [k for k in state if k.endswith(suffix)]
        if len(keys) != 1:
            raise KeyError(f"expected exactly one key ending in {suffix}, got {keys}; keys: {sorted(state)[:40]}")
        found[suffix] = keys[0]
    start = state[found["crf.start"]].double().tolist()
    end = state[found["crf.end"]].double().tolist()
    transitions = state[found["crf.transitions"]].double().tolist()
    if len(start) != N_TAGS or len(end) != N_TAGS or len(transitions) != N_TAGS or any(len(r) != N_TAGS for r in transitions):
        raise ValueError("CRF parameter shape does not match the 23-tag BIO schema")
    starts_ok, trans_ok = bio_constraints()
    masks_match = None
    if "crf.start_allowed" in {k[k.rfind("crf."):] for k in state}:
        sa = [k for k in state if k.endswith("crf.start_allowed")][0]
        ta = [k for k in state if k.endswith("crf.transition_allowed")][0]
        masks_match = state[sa].tolist() == starts_ok and state[ta].tolist() == trans_ok
    return {"checkpoint_sha256": sha256_file(path), "state_dict_keys": found, "torch_load_mode": load_mode,
            "bio_masks_match_labels_py": masks_match, "start": start, "end": end, "transitions": transitions}


# ------------------------------------------------------------------- decoding
def _allowed_predecessors() -> list[list[int]]:
    _, allowed = bio_constraints()
    return [[p for p in range(N_TAGS) if allowed[p][t]] for t in range(N_TAGS)]


_PREDECESSORS = _allowed_predecessors()
_START_OK = bio_constraints()[0]


def viterbi_with_ties(emissions, params: dict, forbidden: list[int] | None = None) -> tuple[list[int], int]:
    """Same arithmetic and tie-break (lowest index wins) as ``viterbi_reference``, plus a tie counter.

    A tie is a step where a second finite option scores exactly the maximum; the tie-break is then decided by
    index order, so such rows are reported rather than hidden.
    """
    banned = set(forbidden or [])
    start, end, trans = params["start"], params["end"], params["transitions"]
    neg = -math.inf
    scores = [start[i] + emissions[0][i] if _START_OK[i] and i not in banned else neg for i in range(N_TAGS)]
    back, ties = [], 0
    for row in emissions[1:]:
        indices, following = [0] * N_TAGS, [neg] * N_TAGS
        for target in range(N_TAGS):
            if target in banned:
                continue
            best_value, best_index, tied = neg, 0, False
            for prior in _PREDECESSORS[target]:
                value = scores[prior] + trans[prior][target]
                if value > best_value:
                    best_value, best_index, tied = value, prior, False
                elif value == best_value and value != neg:
                    tied = True
            ties += tied
            indices[target] = best_index
            following[target] = best_value + row[target]
        back.append(indices)
        scores = following
    totals = [scores[i] + end[i] for i in range(N_TAGS)]
    last = max(range(N_TAGS), key=lambda i: totals[i])
    if not math.isfinite(totals[last]):
        raise ValueError("NO_VALID_BIO_PATH")
    ties += sum(1 for i in range(N_TAGS) if i != last and totals[i] == totals[last])
    path = [last]
    for indices in reversed(back):
        path.append(indices[path[-1]])
    return list(reversed(path)), ties


# ------------------------------------------------------------ prediction rows
def load_rows(path: Path, keep_stored_fields: bool = False) -> list[dict]:
    """Slim per-row records of a DYN/PCRF prediction file (emissions, paths, T1 posterior, stored spans)."""
    rows = []
    for rec in read_jsonl_lines(path):
        trace = rec.get("trace") or {}
        raw = rec.get("raw_output")
        emissions = raw.get("emissions") if isinstance(raw, dict) else None
        has = bool(emissions) and "path_before_constraint" in trace
        row = {"sample_id": rec["sample_id"], "raw_text": rec["raw_text"], "status": rec.get("status"),
               "abstain": rec.get("abstain", False), "predicted_system": rec.get("predicted_system", "khong_ro"),
               "stored_spans": rec.get("spans", []), "has_emissions": has,
               "dataset": rec.get("dataset"), "source_row": rec.get("source_row")}
        if keep_stored_fields:
            row["stored_fields"] = rec.get("fields")
        if has:
            alignment = trace["alignment"]
            row.update(units=alignment["units"], emissions=emissions, path_before=trace["path_before_constraint"],
                       path_after=trace["path_after_constraint"], structure=trace.get("structure"),
                       changed_unit_indices=trace.get("changed_unit_indices", []))
        rows.append(row)
    return rows


def ban_from_structure(row: dict) -> bool:
    """T1 source = the model's own head: ban iff its confident prediction is "moi" (ignores constraint_enabled)."""
    structure = row.get("structure")
    return bool(structure) and structure.get("predicted_system") == "moi"


def spans_from_path(row: dict, path: list[int]) -> list[CharacterSpan]:
    tokens = [Token(u["text"], u["start"], u["end"]) for u in row["units"]]
    spans, repairs = decode_bio(row["raw_text"], tokens, [BIO_LABELS[i] for i in path])
    if repairs:
        raise ValueError(f"{row['sample_id']}: decoded path needed BIO repairs")
    return spans


def redecode_rows(rows: list[dict], params: dict) -> None:
    """Attach ``free`` / ``banned`` re-decoded paths, tie counts and the pure-Python reference paths in place."""
    for row in rows:
        if not row["has_emissions"]:
            continue
        free, free_ties = viterbi_with_ties(row["emissions"], params)
        banned, ban_ties = viterbi_with_ties(row["emissions"], params, QUAN_HUYEN_IDS)
        ref_free, _ = viterbi_reference(row["emissions"], params["transitions"], params["start"], params["end"], [])
        ref_ban, _ = viterbi_reference(row["emissions"], params["transitions"], params["start"], params["end"], QUAN_HUYEN_IDS)
        row.update(free=free, banned=banned, free_ties=free_ties, ban_ties=ban_ties,
                   reference_agrees=(free == ref_free and banned == ref_ban))


def gate_rows(rows: list[dict], label: str, constrained_reference: bool) -> dict:
    """Mandatory gate. ``constrained_reference``: the file's path_after was produced with the ban rule enabled.

    * free re-decode == path_before_constraint on every decodable row;
    * if the file ran the constraint: banned re-decode == path_after on rows with ban_district, and
      path_after == path_before on the others; otherwise path_after == path_before everywhere;
    * decoded path_after reproduces the stored spans (checks alignment/offset reconstruction).
    """
    out = {"label": label, "n_rows": len(rows), "n_decodable": 0, "n_no_emissions": 0,
           "free_vs_before_mismatch": 0, "ban_rows": 0, "ban_vs_after_mismatch": 0,
           "after_eq_before_on_nonban_mismatch": 0, "stored_span_mismatch": 0, "reference_disagree": 0,
           "rows_with_tie_free": 0, "rows_with_tie_ban": 0, "examples": []}
    for row in rows:
        if not row["has_emissions"]:
            out["n_no_emissions"] += 1
            continue
        out["n_decodable"] += 1
        bad = []
        if row["free"] != row["path_before"]:
            out["free_vs_before_mismatch"] += 1
            bad.append("free!=before")
        structure = row.get("structure") or {}
        banned_run = constrained_reference and bool(structure.get("ban_district"))
        if banned_run:
            out["ban_rows"] += 1
            if row["banned"] != row["path_after"]:
                out["ban_vs_after_mismatch"] += 1
                bad.append("banned!=after")
        elif row["path_after"] != row["path_before"]:
            out["after_eq_before_on_nonban_mismatch"] += 1
            bad.append("after!=before_without_ban")
        stored = sorted((s["start"], s["end"], s["label"]) for s in row["stored_spans"])
        rebuilt = sorted((s.start, s.end, s.label) for s in spans_from_path(row, row["path_after"]))
        if stored != rebuilt:
            out["stored_span_mismatch"] += 1
            bad.append("stored_spans!=decoded_after")
        if not row["reference_agrees"]:
            out["reference_disagree"] += 1
            bad.append("tie_aware_viterbi!=viterbi_reference")
        out["rows_with_tie_free"] += row["free_ties"] > 0
        out["rows_with_tie_ban"] += row["ban_ties"] > 0
        if bad and len(out["examples"]) < MAX_MISMATCH_EXAMPLES:
            out["examples"].append({"sample_id": row["sample_id"], "problems": bad})
    failures = (out["free_vs_before_mismatch"] + out["ban_vs_after_mismatch"] + out["after_eq_before_on_nonban_mismatch"]
                + out["stored_span_mismatch"] + out["reference_disagree"])
    out["status"] = "PASS" if failures == 0 and out["n_decodable"] > 0 else "FAIL"
    out["tie_handling"] = ("lowest tag index wins at every tie (same rule as viterbi_reference and torch .max); "
                           "rows_with_tie_* count rows where any step had an exact tie among finite options")
    return out


# ------------------------------------------------------------------ outcomes
def classify_change(before: tuple[int, int, int], after: tuple[int, int, int]) -> str:
    """Per-row effect of the ban on exact span errors (fp + fn): correct_fix / harm / neutral."""
    delta = (after[1] + after[2]) - (before[1] + before[2])
    return "correct_fix" if delta < 0 else "harm" if delta > 0 else "neutral"


def path_for(row: dict, ban: bool) -> list[int] | None:
    if not row["has_emissions"]:
        return None
    return row["banned"] if ban else row["free"]


def spans_for(row: dict, ban: bool) -> list[CharacterSpan]:
    path = path_for(row, ban)
    if path is None:  # abstained / failed row: keep the stored (empty) spans
        return [CharacterSpan(**s) for s in row["stored_spans"]]
    return spans_from_path(row, path)


def span_key_set(spans) -> set[tuple[int, int, str]]:
    return {(s.start, s.end, s.label) for s in spans}


def row_changed(row: dict, ban: bool) -> bool:
    return bool(ban) and row["has_emissions"] and row["banned"] != row["free"]


def to_output(row: dict, spans, system: str) -> SpanModelOutput:
    return SpanModelOutput(row["sample_id"], row["raw_text"], list(spans), predicted_system=system,
                           abstain=row["abstain"], status=row["status"] or "ok")


def count_quan_huyen(spans) -> int:
    return sum(1 for s in spans if s.label == "QuanHuyen")


def micro_f1(counts) -> float:
    tp = sum(int(c[0]) for c in counts)
    fp = sum(int(c[1]) for c in counts)
    fn = sum(int(c[2]) for c in counts)
    return 0.0 if 2 * tp + fp + fn == 0 else 2 * tp / (2 * tp + fp + fn)


def pair_stats(counts_a, counts_b, seed: int = SEED, n_resamples: int = N_RESAMPLES) -> dict:
    """Delta F1 (A - B) with paired bootstrap CI over rows; units are (tp, fp, fn) rows."""
    import numpy as np
    from src.evaluation import stats

    a, b = np.asarray(counts_a, dtype=np.int64), np.asarray(counts_b, dtype=np.int64)
    delta = stats.paired_bootstrap_delta(stats.micro_f1_from_counts, a, b, n_resamples, seed=seed)
    return {"f1_a": float(stats.micro_f1_from_counts(a)), "f1_b": float(stats.micro_f1_from_counts(b)),
            "delta": delta["estimate"], "ci_low": delta["ci_low"], "ci_high": delta["ci_high"],
            "status": delta["status"], "prop_delta_le_0": delta.get("prop_delta_le_0")}


def single_ci(counts, seed: int = SEED, n_resamples: int = N_RESAMPLES) -> dict:
    import numpy as np
    from src.evaluation import stats

    res = stats.bootstrap_ci(stats.micro_f1_from_counts, np.asarray(counts, dtype=np.int64), n_resamples, seed=seed)
    return {"f1": res["estimate"], "ci_low": res["ci_low"], "ci_high": res["ci_high"], "status": res["status"]}


def tally(changes: list[str]) -> dict:
    c = Counter(changes)
    return {"correct_fix": c.get("correct_fix", 0), "harm": c.get("harm", 0), "neutral": c.get("neutral", 0)}


# ------------------------------------------------------- per-row score arrays
# Only two outputs exist per row: the unconstrained path and the QuanHuyen-banned path.  Every ablation
# (any T1 source, oracle included) just picks one of the two per row, so scoring is done once per row.
def _arrays(rows, free_counts, ban_counts, free_exact, ban_exact, free_spans, ban_spans, gold_moi, gold_has_qh):
    import numpy as np

    n = len(rows)
    changed = np.array([row_changed(r, True) for r in rows], dtype=bool)
    return {
        "sample_ids": [r["sample_id"] for r in rows],
        "cf": np.asarray(free_counts, dtype=np.int64).reshape(n, 3), "cb": np.asarray(ban_counts, dtype=np.int64).reshape(n, 3),
        "ef": np.asarray(free_exact, dtype=bool), "eb": np.asarray(ban_exact, dtype=bool),
        "qh_free": np.array([count_quan_huyen(s) > 0 for s in free_spans], dtype=bool),
        "qh_ban": np.array([count_quan_huyen(s) > 0 for s in ban_spans], dtype=bool),
        "changed": changed,
        "span_diff": np.array([len(span_key_set(a) ^ span_key_set(b)) for a, b in zip(free_spans, ban_spans)], dtype=np.int64),
        "dyn_system": [(r.get("structure") or {}).get("predicted_system") for r in rows],
        "gold_moi": np.asarray(gold_moi, dtype=bool), "gold_has_qh": np.asarray(gold_has_qh, dtype=bool),
        "datasets": [r.get("dataset") for r in rows],
    }


def order_rows_like(rows: list[dict], sample_ids: list[str]) -> list[dict]:
    by_id = {r["sample_id"]: r for r in rows}
    if len(by_id) != len(rows) or set(by_id) != set(sample_ids):
        raise ValueError("rows and gold must cover the same sample IDs exactly once")
    return [by_id[s] for s in sample_ids]


def span_arrays(rows: list[dict], golds: list[dict], excluded_t1: list[str]) -> dict:
    """Per-row (tp, fp, fn) of the free and banned decodes against span gold (T0 exact span scorer)."""
    import numpy as np
    from src.evaluation import frozen_reliability as fr
    from src.evaluation.schema import ADDRESS_SYSTEMS

    rows = order_rows_like(rows, [g["sample_id"] for g in golds])
    free = [spans_for(r, False) for r in rows]
    ban = [spans_for(r, True) for r in rows]
    uf = fr.build_units([to_output(r, s, r["predicted_system"]) for r, s in zip(rows, free)], golds, excluded_t1)
    ub = fr.build_units([to_output(r, s, r["predicted_system"]) for r, s in zip(rows, ban)], golds, excluded_t1)
    arrays = _arrays(rows, uf["totals"], ub["totals"], uf["exact"], ub["exact"], free, ban,
                     [g.get("address_system") == "moi" for g in golds],
                     [any(s["label"] == "QuanHuyen" for s in g["spans"]) for g in golds])
    arrays["gold_system"] = [g.get("address_system") for g in golds]
    # T1-eligible = the mask the T1 scorer uses (known gold system and not in the declared exclusion list)
    excluded_ids = set(excluded_t1)
    arrays["t1_eligible"] = np.array([g.get("address_system") in ADDRESS_SYSTEMS and g["sample_id"] not in excluded_ids
                                      for g in golds], dtype=bool)
    return arrays


def stored_span_counts(rows: list[dict], golds: list[dict], excluded_t1: list[str]):
    """(tp, fp, fn) per gold row of the spans stored in a frozen prediction file (no re-decoding)."""
    from src.evaluation import frozen_reliability as fr

    rows = order_rows_like(rows, [g["sample_id"] for g in golds])
    preds = [to_output(r, [CharacterSpan(**s) for s in r["stored_spans"]], r["predicted_system"]) for r in rows]
    return fr.build_units(preds, golds, excluded_t1)["totals"]


def fivefield_arrays(rows: list[dict], gold_by_key: dict) -> dict:
    """Same arrays against the five-field gold (strict field scorer of src/evaluation/scorer.py)."""
    from src.evaluation.scorer import score_prediction_pair

    keys = [(r["dataset"], r["source_row"]) for r in rows]
    if len(set(keys)) != len(keys) or set(keys) != set(gold_by_key):
        raise ValueError("five-field rows and gold keys differ")

    def fields_of(row, ban):
        return to_output(row, spans_for(row, ban), row["predicted_system"]).to_standard_5_fields().to_dict()

    free_c, ban_c, free_e, ban_e, free_s, ban_s = [], [], [], [], [], []
    for row, key in zip(rows, keys):
        if gold_by_key[key]["text"] != row["raw_text"]:  # gold row must be the one that was predicted
            raise ValueError(f"{row['sample_id']}: gold ChuoiDiaChi differs from the predicted raw_text")
        gold = gold_by_key[key]["fields"]
        for ban, counts, exact, spans in ((False, free_c, free_e, free_s), (True, ban_c, ban_e, ban_s)):
            score = score_prediction_pair(fields_of(row, ban), gold)
            counts.append((score["tp"], score["fp"], score["fn"]))
            exact.append(score["exact_match"])
            spans.append(spans_for(row, ban))
    arrays = _arrays(rows, free_c, ban_c, free_e, ban_e, free_s, ban_s,
                     [gold_by_key[k]["system"] == "moi" for k in keys],
                     [bool(gold_by_key[k]["fields"]["QuanHuyen"].strip()) for k in keys])
    arrays["gold_system"] = [gold_by_key[k]["system"] for k in keys]
    return arrays


def pick(arrays: dict, flags, key_free: str = "cf", key_ban: str = "cb"):
    import numpy as np

    f = np.asarray(flags, dtype=bool).reshape(-1, 1)
    return np.where(f, arrays[key_ban], arrays[key_free])


# ------------------------------------------------------------------- analyses
def analyze_source(arrays: dict, flags, source: str, with_ci: bool = True) -> dict:
    """Effect of banning QuanHuyen exactly on the rows where ``flags`` (a T1 source's "moi") is true."""
    import numpy as np

    flags = np.asarray(flags, dtype=bool)
    counts = pick(arrays, flags)
    exact = np.where(flags, arrays["eb"], arrays["ef"])
    effective = flags & arrays["changed"]
    idx = np.flatnonzero(effective)
    changes = [classify_change(tuple(arrays["cf"][i]), tuple(arrays["cb"][i])) for i in idx]
    result = {"source": source, "n_rows": int(len(flags)), "n_ban_rows": int(flags.sum()),
              "n_changed_rows": int(effective.sum()), "n_span_changes": int(arrays["span_diff"][idx].sum()),
              **tally(changes), "changed_sample_ids": [arrays["sample_ids"][i] for i in idx][:50],
              "changed_by_gold_system": dict(Counter(f"{arrays['gold_system'][i]}:{c}" for i, c in zip(idx, changes)))
              if "gold_system" in arrays else None,
              "f1_no_constraint": micro_f1(arrays["cf"]), "f1_with_ban": micro_f1(counts),
              "exact_no_constraint": int(arrays["ef"].sum()), "exact_with_ban": int(exact.sum()),
              "counts_no_constraint": [int(x) for x in arrays["cf"].sum(0)], "counts_with_ban": [int(x) for x in counts.sum(0)]}
    if with_ci:
        result["paired"] = pair_stats(counts, arrays["cf"])
        result["ci_with_ban"] = single_ci(counts)
    return result


def analyze_headroom(arrays: dict, dyn_flags=None, heur_systems: list | None = None) -> dict:
    """How many errors can the ban fix at all: gold-new rows (no QuanHuyen in gold) where the free decode still emits one."""
    import numpy as np

    gold_moi = arrays["gold_moi"]
    no_qh = gold_moi & ~arrays["gold_has_qh"]
    headroom = no_qh & arrays["qh_free"]
    eligible = arrays.get("t1_eligible", np.ones(len(gold_moi), dtype=bool))
    out = {"n_rows": int(len(gold_moi)), "n_gold_moi": int(gold_moi.sum()), "n_gold_moi_without_quan_huyen": int(no_qh.sum()),
           "n_gold_moi_t1_eligible": int((no_qh & eligible).sum()), "n_headroom_t1_eligible": int((headroom & eligible).sum()),
           "n_headroom": int(headroom.sum()), "n_headroom_removed_by_unconditional_ban": int((headroom & ~arrays["qh_ban"]).sum()),
           "headroom_sample_ids": [arrays["sample_ids"][i] for i in np.flatnonzero(headroom)][:50]}
    if dyn_flags is not None:
        dyn = arrays["dyn_system"]
        by_system = Counter(dyn[i] for i in np.flatnonzero(headroom))
        out["headroom_by_dyn_t1"] = {k: by_system.get(k, 0) for k in ("moi", "cu", "Lai", "khong_ro")}
        out["gold_moi_by_dyn_t1"] = {k: sum(1 for i in np.flatnonzero(no_qh) if dyn[i] == k) for k in ("moi", "cu", "Lai", "khong_ro")}
        dyn_flags = np.asarray(dyn_flags, dtype=bool)
        out["n_headroom_with_dyn_ban"] = int((headroom & dyn_flags).sum())
        out["n_headroom_fixed_by_dyn_ban"] = int((headroom & dyn_flags & ~arrays["qh_ban"]).sum())
        exposed = arrays["gold_has_qh"] & dyn_flags & arrays["qh_free"]
        out["n_harm_exposure_gold_quan_huyen_with_dyn_ban"] = int(exposed.sum())
        out["n_harm_exposure_qh_removed_by_ban"] = int((exposed & ~arrays["qh_ban"]).sum())
    if heur_systems is not None:
        by_heur = Counter(heur_systems[i] for i in np.flatnonzero(headroom))
        out["headroom_by_heur_t1"] = {k: by_heur.get(k, 0) for k in ("moi", "cu", "Lai", "khong_ro")}
    if any(d is not None for d in arrays["datasets"]):
        out["headroom_by_source_dataset"] = dict(Counter(arrays["datasets"][i] for i in np.flatnonzero(headroom)))
        out["gold_moi_by_source_dataset"] = dict(Counter(arrays["datasets"][i] for i in np.flatnonzero(no_qh)))
    out["status"] = "NOT_EVALUABLE_NO_SUPPORT" if out["n_gold_moi_without_quan_huyen"] == 0 else "OK"
    out["statement"] = (f"{out['n_headroom']}/{out['n_gold_moi_without_quan_huyen']} gold-new rows still get a QuanHuyen "
                        "span from the unconstrained decode (upper bound of errors the constraint can fix)")
    return out


def oracle_flags(arrays: dict):
    """ORACLE_UPPER_BOUND only: ban where the *gold* system is new. Never enters model comparison tables."""
    return arrays["gold_moi"].copy()


def dyn_flags_from_rows(rows: list[dict], sample_ids: list[str]):
    import numpy as np

    by_id = {r["sample_id"]: r for r in rows}
    return np.array([ban_from_structure(by_id[s]) for s in sample_ids], dtype=bool)


def heur_flags(heur_systems: dict, sample_ids: list[str]):
    """Ban where HEUR-JW's frozen T1 says "moi"; a missing prediction is an error, never a silent "no ban"."""
    import numpy as np

    missing = [s for s in sample_ids if s not in heur_systems]
    if missing:
        raise KeyError(f"HEUR-JW has no prediction for {len(missing)} rows, e.g. {missing[:3]}")
    return np.array([heur_systems[s] == "moi" for s in sample_ids], dtype=bool)


def load_system_map(path: Path) -> dict:
    """sample_id -> predicted_system from a frozen file, read line by line (abstain counts as khong_ro)."""
    out = {}
    for rec in read_jsonl_lines(path):
        key = rec["sample_id"]
        if key in out:
            raise ValueError(f"duplicate sample {key} in {path}")
        out[key] = "khong_ro" if rec.get("abstain") else rec.get("predicted_system", "khong_ro")
    return out


def model_comparison_row(cell: str, train_t1: bool, decode_constraint: bool, source: str, counts, exact) -> dict:
    """One model-comparison line. ORACLE is refused here so it can never reach a comparison table."""
    if "ORACLE" in source.upper() or "ORACLE" in cell.upper():
        raise ValueError("ORACLE results are an upper bound and must not enter model comparison tables")
    ci = single_ci(counts)
    return {"cell": cell, "train_with_t1_head": train_t1, "decode_with_constraint": decode_constraint, "t1_source": source,
            "n_rows": int(len(counts)), "f1": ci["f1"], "ci_low": ci["ci_low"], "ci_high": ci["ci_high"],
            "exact_rows": int(sum(exact)), "tp": int(sum(c[0] for c in counts)), "fp": int(sum(c[1] for c in counts)),
            "fn": int(sum(c[2] for c in counts))}


def sample_std(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    return math.sqrt(sum((v - mean) ** 2 for v in values) / (len(values) - 1))


# --------------------------------------------------------- five-field gold
BENCHMARK_FILES = {"01_new": "01_full_address_new_verified.csv", "02_noisy": "02_raw_noisy_synthetic_1000.csv",
                   "03_old": "03_real_address_old_1500.csv", "04_missing": "04_missing_fields_800.csv",
                   "06_hybrid": "06_hybrid_addresses_600.csv"}
FIVE_FIELDS = ("SoNha", "TenDuong", "PhuongXa", "QuanHuyen", "TinhThanh")


def load_fivefield_gold(keys: set, input_manifest: dict, benchmark_dir: Path | None = None) -> dict:
    """Gold fields + HeQuyChieu for (dataset, row_index) keys; each CSV is hash-checked against the track manifest."""
    import csv

    benchmark_dir = benchmark_dir or ROOT / "data/processed/benchmark"
    gold = {}
    for dataset, filename in BENCHMARK_FILES.items():
        path = benchmark_dir / filename
        expected = input_manifest["datasets"][dataset]["sha256"]
        if sha256_file(path) != expected:
            raise ValueError(f"{filename} does not match fivefield_input.manifest.json")
        prefix = "GT_" if dataset == "02_noisy" else ""
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            needed = {prefix + f for f in FIVE_FIELDS} | {"ChuoiDiaChi", "HeQuyChieu"}
            if not needed <= set(reader.fieldnames or []):
                raise ValueError(f"{filename}: missing columns {sorted(needed - set(reader.fieldnames or []))}")
            for index, row in enumerate(reader):
                if (dataset, index) in keys:
                    gold[(dataset, index)] = {"fields": {f: row[prefix + f] for f in FIVE_FIELDS},
                                              "system": row["HeQuyChieu"], "text": row["ChuoiDiaChi"]}
    if set(gold) != set(keys):
        raise ValueError("five-field gold does not cover every prediction key")
    return gold
