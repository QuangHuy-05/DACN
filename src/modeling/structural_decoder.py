"""Text-model posterior policy and constrained BIO paths; no gold arguments."""

import math

from src.evaluation.schema import ADDRESS_SYSTEMS
from src.evaluation.span_features import BIO_LABELS
from src.modeling.labels import bio_constraints

RULE_VERSION = "confidence_bio_constraint_v1"


def structure_decision(posterior: list[float], threshold: float = 0.8,
                       margin: float = 0.2, enabled: bool = True) -> dict:
    if len(posterior) != 3 or any(not math.isfinite(p) or not 0 <= p <= 1 for p in posterior) or abs(sum(posterior) - 1) > 1e-5:
        raise ValueError("INVALID_T1_POSTERIOR")
    order = sorted(range(3), key=lambda i: (-posterior[i], i))
    confident = posterior[order[0]] >= threshold and posterior[order[0]] - posterior[order[1]] >= margin
    system = ADDRESS_SYSTEMS[order[0]] if confident else "khong_ro"
    constrain = enabled and system == "moi"
    return {"rule_version": RULE_VERSION, "posterior": dict(zip(ADDRESS_SYSTEMS, posterior)),
            "confidence": posterior[order[0]], "margin_observed": posterior[order[0]] - posterior[order[1]],
            "threshold": threshold, "margin_required": margin, "predicted_system": system,
            "t1_abstain": not confident, "constraint_enabled": enabled, "ban_district": constrain,
            "reason": "confident_new_two_level" if constrain else "keep_full_label_space",
            "forbidden_tag_ids": [i for i, tag in enumerate(BIO_LABELS) if tag.endswith("-QuanHuyen")] if constrain else []}


def viterbi_reference(emissions: list[list[float]], transitions: list[list[float]],
                      start_scores: list[float], end_scores: list[float],
                      forbidden_tag_ids: list[int] | None = None) -> tuple[list[int], float]:
    """Pure-Python reference also used to independently verify Torch decoding."""
    if not emissions or any(len(row) != len(BIO_LABELS) for row in emissions):
        raise ValueError("EMPTY_OR_INVALID_EMISSIONS")
    starts, allowed = bio_constraints()
    banned = set(forbidden_tag_ids or [])
    n = len(BIO_LABELS)
    scores = [start_scores[i] + emissions[0][i] if starts[i] and i not in banned else -math.inf for i in range(n)]
    back = []
    for row in emissions[1:]:
        indices, following = [], []
        for target in range(n):
            options = [scores[prior] + transitions[prior][target] if allowed[prior][target] and target not in banned else -math.inf for prior in range(n)]
            best = max(range(n), key=lambda i: options[i])
            indices.append(best)
            following.append(options[best] + row[target])
        back.append(indices)
        scores = following
    last = max(range(n), key=lambda i: scores[i] + end_scores[i])
    score, path = scores[last] + end_scores[last], [last]
    if not math.isfinite(score):
        raise ValueError("NO_VALID_BIO_PATH")
    for indices in reversed(back):
        path.append(indices[path[-1]])
    return list(reversed(path)), score
