"""Evaluation engine and scorer for T0 11-span and T1 address system tasks.

Provides exact character-offset span evaluation, boundary/label mismatch
diagnostics, T1 confusion matrix and abstain tracking, as well as structural
consistency checks (e.g. QuanHuyen hallucination on 2-tier new system).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Sequence

from src.evaluation.schema import (
    ADDRESS_SYSTEMS,
    SPAN11_LABELS,
    CharacterSpan,
    SpanModelOutput,
)


def validate_span_integrity(
    spans: Sequence[CharacterSpan], raw_text: str = ""
) -> list[str]:
    """Check offsets, ordering, boundaries, text slices, and overlaps.

    Returns a list of issue descriptions (empty list if valid).
    """
    issues: list[str] = []
    text_len = len(raw_text) if raw_text else None

    # Check bounds and text slice
    sorted_spans = sorted(spans, key=lambda s: (s.start, s.end))
    for i, s in enumerate(sorted_spans):
        if s.start < 0:
            issues.append(f"Negative start offset: {s.start} in span {s.label}")
        if s.start >= s.end:
            issues.append(f"Non-positive span length [{s.start}, {s.end}) for {s.label}")
        if text_len is not None and s.end > text_len:
            issues.append(
                f"Span [{s.start}, {s.end}) extends beyond text length {text_len} for {s.label}"
            )
        if raw_text and s.text:
            actual_slice = raw_text[s.start : s.end]
            if actual_slice != s.text:
                issues.append(
                    f"Span text mismatch for {s.label}: slice '{actual_slice}' != declared '{s.text}'"
                )

        # Check overlap with next span
        if i + 1 < len(sorted_spans):
            next_s = sorted_spans[i + 1]
            if s.end > next_s.start:
                issues.append(
                    f"Overlapping spans: {s.label}[{s.start}:{s.end}] overlaps with {next_s.label}[{next_s.start}:{next_s.end}]"
                )

    return issues


def _span_key(span: CharacterSpan) -> tuple[int, int, str]:
    return (span.start, span.end, span.label)


def evaluate_single_sample_spans(
    pred_spans: Sequence[CharacterSpan],
    gold_spans: Sequence[CharacterSpan],
    raw_text: str = "",
) -> dict[str, Any]:
    """Evaluate exact character span matches for a single sample.

    Calculates:
    - true_positives, false_positives, false_negatives
    - boundary_errors (same label, overlapping offsets)
    - label_errors (identical [start, end), different label)
    - spurious_spans (pred does not overlap any gold)
    - missed_spans (gold has no overlapping pred)
    """
    gold_keys = {_span_key(g): g for g in gold_spans}
    pred_keys = {_span_key(p): p for p in pred_spans}

    matched_keys = set(gold_keys.keys()) & set(pred_keys.keys())

    unmatched_pred = [p for k, p in pred_keys.items() if k not in matched_keys]
    unmatched_gold = [g for k, g in gold_keys.items() if k not in matched_keys]

    # Diagnostics
    boundary_errors = []
    label_errors = []
    spurious_preds = []

    remaining_golds = list(unmatched_gold)

    for p in unmatched_pred:
        # Check label error: exact boundary, different label
        label_match = [
            g for g in remaining_golds if g.start == p.start and g.end == p.end
        ]
        if label_match:
            g = label_match[0]
            label_errors.append(
                {
                    "start": p.start,
                    "end": p.end,
                    "pred_label": p.label,
                    "gold_label": g.label,
                    "text": p.text or (raw_text[p.start : p.end] if raw_text else ""),
                }
            )
            continue

        # Check boundary error: overlapping range, same label
        overlap_same_label = [
            g
            for g in remaining_golds
            if g.label == p.label and max(p.start, g.start) < min(p.end, g.end)
        ]
        if overlap_same_label:
            g = overlap_same_label[0]
            boundary_errors.append(
                {
                    "label": p.label,
                    "pred_range": (p.start, p.end),
                    "gold_range": (g.start, g.end),
                    "pred_text": p.text
                    or (raw_text[p.start : p.end] if raw_text else ""),
                    "gold_text": g.text
                    or (raw_text[g.start : g.end] if raw_text else ""),
                }
            )
            continue

        # Check if overlaps with any gold at all
        overlaps_any = [
            g for g in remaining_golds if max(p.start, g.start) < min(p.end, g.end)
        ]
        if not overlaps_any:
            spurious_preds.append(p)

    # Missed golds that do not overlap any pred
    missed_golds = []
    for g in unmatched_gold:
        overlaps_any_pred = [
            p for p in pred_spans if max(p.start, g.start) < min(p.end, g.end)
        ]
        if not overlaps_any_pred:
            missed_golds.append(g)

    return {
        "tp_count": len(matched_keys),
        "fp_count": len(unmatched_pred),
        "fn_count": len(unmatched_gold),
        "tp_keys": list(matched_keys),
        "fp_keys": [_span_key(p) for p in unmatched_pred],
        "fn_keys": [_span_key(g) for g in unmatched_gold],
        "boundary_errors": boundary_errors,
        "label_errors": label_errors,
        "spurious_preds": [_span_key(p) for p in spurious_preds],
        "missed_golds": [_span_key(g) for g in missed_golds],
    }


def compute_exact_span_metrics(
    predictions: Sequence[SpanModelOutput],
    golds: Sequence[dict[str, Any]],
    labels: Sequence[str] = SPAN11_LABELS,
) -> dict[str, Any]:
    """Compute aggregate exact span metrics (Precision, Recall, F1) across samples.

    Supports micro-average, macro-average (across all labels and across active labels),
    and per-label detailed breakdown.
    """
    gold_by_id = {g["sample_id"]: g for g in golds}

    per_label_tp: Counter[str] = Counter()
    per_label_fp: Counter[str] = Counter()
    per_label_fn: Counter[str] = Counter()

    total_boundary_errors: list[dict[str, Any]] = []
    total_label_errors: list[dict[str, Any]] = []
    total_spurious_spans: list[dict[str, Any]] = []
    total_missed_spans: list[dict[str, Any]] = []

    # T1 evaluation counters
    t1_gold_counts: Counter[str] = Counter()
    t1_pred_counts: Counter[str] = Counter()
    t1_correct_counts: Counter[str] = Counter()
    t1_confusion: defaultdict[str, Counter[str]] = defaultdict(Counter)
    t1_abstain_count = 0
    t1_total_samples = 0

    # Structural constraint check: QuanHuyen predicted on gold 'moi'
    quan_huyen_hallucinations_on_new = 0
    new_system_sample_count = 0

    for pred in predictions:
        sample_id = pred.sample_id
        if sample_id not in gold_by_id:
            continue

        gold_dict = gold_by_id[sample_id]
        raw_text = pred.raw_text or gold_dict.get("text", "")

        # Convert gold dict spans to CharacterSpan objects
        gold_spans = [
            CharacterSpan(
                start=s["start"],
                end=s["end"],
                label=s["label"],
                text=s.get("text", raw_text[s["start"] : s["end"]] if raw_text else ""),
                system=s.get("system", "khong_xac_dinh"),
            )
            for s in gold_dict.get("spans", [])
        ]

        sample_eval = evaluate_single_sample_spans(
            pred.spans, gold_spans, raw_text=raw_text
        )

        for _, _, label in sample_eval["tp_keys"]:
            per_label_tp[label] += 1
        for _, _, label in sample_eval["fp_keys"]:
            per_label_fp[label] += 1
        for _, _, label in sample_eval["fn_keys"]:
            per_label_fn[label] += 1

        for err in sample_eval["boundary_errors"]:
            total_boundary_errors.append({"sample_id": sample_id, **err})
        for err in sample_eval["label_errors"]:
            total_label_errors.append({"sample_id": sample_id, **err})
        for item in sample_eval["spurious_preds"]:
            total_spurious_spans.append({"sample_id": sample_id, "span": item})
        for item in sample_eval["missed_golds"]:
            total_missed_spans.append({"sample_id": sample_id, "span": item})

        # Evaluate T1 system if available in gold
        gold_sys = gold_dict.get("address_system")
        if gold_sys in ADDRESS_SYSTEMS:
            t1_total_samples += 1
            t1_gold_counts[gold_sys] += 1
            pred_sys = pred.predicted_system

            if pred.abstain or pred_sys == "khong_ro":
                t1_abstain_count += 1
                t1_confusion[gold_sys]["khong_ro"] += 1
            else:
                t1_pred_counts[pred_sys] += 1
                t1_confusion[gold_sys][pred_sys] += 1
                if pred_sys == gold_sys:
                    t1_correct_counts[gold_sys] += 1

            if gold_sys == "moi":
                new_system_sample_count += 1
                # Check if model predicted QuanHuyen on 2-tier new system
                has_quan_huyen = any(s.label == "QuanHuyen" for s in pred.spans)
                if has_quan_huyen:
                    quan_huyen_hallucinations_on_new += 1

    # Per-label metrics
    per_label_metrics: dict[str, dict[str, Any]] = {}
    active_precisions: list[float] = []
    active_recalls: list[float] = []
    active_f1s: list[float] = []

    for label in labels:
        tp = per_label_tp[label]
        fp = per_label_fp[label]
        fn = per_label_fn[label]
        support = tp + fn

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        per_label_metrics[label] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "support": support,
        }

        if support > 0 or (tp + fp) > 0:
            active_precisions.append(prec)
            active_recalls.append(rec)
            active_f1s.append(f1)

    # Micro average
    total_tp = sum(per_label_tp.values())
    total_fp = sum(per_label_fp.values())
    total_fn = sum(per_label_fn.values())

    micro_prec = (
        total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    )
    micro_rec = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    micro_f1 = (
        (2 * micro_prec * micro_rec) / (micro_prec + micro_rec)
        if (micro_prec + micro_rec) > 0
        else 0.0
    )

    # Macro average across labels with support > 0
    macro_prec = (
        sum(active_precisions) / len(active_precisions) if active_precisions else 0.0
    )
    macro_rec = sum(active_recalls) / len(active_recalls) if active_recalls else 0.0
    macro_f1 = sum(active_f1s) / len(active_f1s) if active_f1s else 0.0

    # T1 system metrics
    accepted_t1_samples = t1_total_samples - t1_abstain_count
    t1_correct_total = sum(t1_correct_counts.values())
    t1_overall_accuracy = (
        t1_correct_total / t1_total_samples if t1_total_samples > 0 else 0.0
    )
    t1_accepted_accuracy = (
        t1_correct_total / accepted_t1_samples if accepted_t1_samples > 0 else 0.0
    )

    t1_per_class: dict[str, dict[str, float]] = {}
    for sys_label in ADDRESS_SYSTEMS:
        tp_s = t1_correct_counts[sys_label]
        fp_s = sum(
            t1_confusion[other][sys_label]
            for other in ADDRESS_SYSTEMS
            if other != sys_label
        )
        fn_s = sum(
            t1_confusion[sys_label][pred_col]
            for pred_col in ("cu", "moi", "Lai", "khong_ro")
            if pred_col != sys_label
        )
        p_s = tp_s / (tp_s + fp_s) if (tp_s + fp_s) > 0 else 0.0
        r_s = tp_s / (tp_s + fn_s) if (tp_s + fn_s) > 0 else 0.0
        f1_s = (2 * p_s * r_s) / (p_s + r_s) if (p_s + r_s) > 0 else 0.0
        t1_per_class[sys_label] = {
            "precision": round(p_s, 4),
            "recall": round(r_s, 4),
            "f1": round(f1_s, 4),
            "support": t1_gold_counts[sys_label],
        }

    return {
        "t0_exact_span": {
            "micro": {
                "precision": round(micro_prec, 4),
                "recall": round(micro_rec, 4),
                "f1": round(micro_f1, 4),
                "total_tp": total_tp,
                "total_fp": total_fp,
                "total_fn": total_fn,
            },
            "macro": {
                "precision": round(macro_prec, 4),
                "recall": round(macro_rec, 4),
                "f1": round(macro_f1, 4),
                "evaluated_labels_count": len(active_f1s),
            },
            "per_label": per_label_metrics,
            "diagnostics": {
                "boundary_error_count": len(total_boundary_errors),
                "label_error_count": len(total_label_errors),
                "spurious_span_count": len(total_spurious_spans),
                "missed_span_count": len(total_missed_spans),
                "boundary_errors_sample": total_boundary_errors[:10],
                "label_errors_sample": total_label_errors[:10],
            },
        },
        "t1_address_system": {
            "total_evaluated": t1_total_samples,
            "abstain_count": t1_abstain_count,
            "abstain_rate": round(
                t1_abstain_count / t1_total_samples if t1_total_samples > 0 else 0.0,
                4,
            ),
            "overall_accuracy": round(t1_overall_accuracy, 4),
            "accepted_accuracy": round(t1_accepted_accuracy, 4),
            "per_class": t1_per_class,
            "confusion_matrix": {k: dict(v) for k, v in t1_confusion.items()},
        },
        "structural_consistency": {
            "new_system_sample_count": new_system_sample_count,
            "quan_huyen_hallucinations_on_new": quan_huyen_hallucinations_on_new,
            "quan_huyen_false_positive_rate_on_new": round(
                quan_huyen_hallucinations_on_new / new_system_sample_count
                if new_system_sample_count > 0
                else 0.0,
                4,
            ),
        },
    }
