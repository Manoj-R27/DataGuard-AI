from collections import defaultdict

import pandas as pd

from src.drift import detect_drift
from src.simulate import SEVERITY_LEVELS, simulate_days


def calculate_metrics(tp: int, fp: int, fn: int, tn: int) -> dict:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    return {"true_positive": tp, "false_positive": fp, "false_negative": fn, "true_negative": tn, "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4), "false_positive_rate": round(fpr, 4)}


def evaluate_detector(reference: pd.DataFrame, trials: int = 20, severities: tuple[str, ...] = SEVERITY_LEVELS) -> dict:
    clean_fp = clean_tn = 0
    corruption_counts = defaultdict(lambda: {"tp": 0, "fn": 0})
    severity_totals = defaultdict(lambda: {"tp": 0, "fn": 0})
    for seed in range(trials):
        clean_frame = simulate_days(reference, seed=seed, severity="obvious")[0][1]
        if detect_drift(reference, clean_frame).get("drifted", False):
            clean_fp += 1
        else:
            clean_tn += 1
        for severity in severities:
            for _, current, truth in simulate_days(reference, seed=seed, severity=severity)[1:]:
                kind = truth["injections"][0]["kind"]
                values = corruption_counts[(kind, severity)]
                if detect_drift(reference, current).get("drifted", False):
                    values["tp"] += 1
                    severity_totals[severity]["tp"] += 1
                else:
                    values["fn"] += 1
                    severity_totals[severity]["fn"] += 1

    clean_total = clean_fp + clean_tn
    clean_control = {"trials": clean_total, "true_negative": clean_tn, "false_positive": clean_fp, "false_positive_rate": round(clean_fp / clean_total if clean_total else 0.0, 4), "recall": round(clean_tn / clean_total if clean_total else 1.0, 4)}
    aggregate = defaultdict(lambda: {"tp": 0, "fn": 0})
    detailed_breakdown = {}
    nested_breakdown = defaultdict(dict)
    for (kind, severity), values in sorted(corruption_counts.items()):
        aggregate[kind]["tp"] += values["tp"]
        aggregate[kind]["fn"] += values["fn"]
        metrics = calculate_metrics(values["tp"], clean_fp, values["fn"], clean_tn)
        metrics.update({"corruption": kind, "severity": severity})
        detailed_breakdown[f"{kind} [{severity}]"] = metrics
        nested_breakdown[kind][severity] = metrics
    by_severity = {severity: {**calculate_metrics(values["tp"], clean_fp, values["fn"], clean_tn), "total_trials": values["tp"] + values["fn"]} for severity, values in sorted(severity_totals.items())}
    total_tp = sum(values["tp"] for values in aggregate.values())
    total_fn = sum(values["fn"] for values in aggregate.values())
    overall = {**calculate_metrics(total_tp, clean_fp, total_fn, clean_tn), "total_trials": clean_total + total_tp + total_fn}
    return {"trials_per_type": trials, "breakdown": detailed_breakdown, "severities": list(severities), "by_corruption_and_severity": dict(nested_breakdown), "by_severity": by_severity, "clean_control": clean_control, "overall": overall}
