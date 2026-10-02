from collections import defaultdict

from src.drift import detect_drift
from src.simulate import simulate_days


TRIALS = 30


def _metrics(true_positive, false_positive, false_negative, true_negative):
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    false_positive_rate = false_positive / (false_positive + true_negative) if false_positive + true_negative else 0.0
    return {
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "true_negative": true_negative,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive_rate": false_positive_rate,
    }


def evaluate_detector(reference, trials: int = TRIALS) -> dict:
    counts = defaultdict(lambda: [0, 0, 0, 0])
    for seed in range(trials):
        for _, current, truth in simulate_days(reference, seed=seed):
            kind = "clean" if not truth["injections"] else truth["injections"][0]["kind"]
            expected = bool(truth["injections"])
            detected = detect_drift(reference, current)["drifted"]
            index = 0 if expected and detected else 1 if not expected and detected else 2 if expected else 3
            counts[kind][index] += 1

    breakdown = {}
    totals = [0, 0, 0, 0]
    for kind, values in sorted(counts.items()):
        breakdown[kind] = _metrics(*values)
        totals = [left + right for left, right in zip(totals, values)]
    return {"trials_per_type": trials, "breakdown": breakdown, "overall": _metrics(*totals)}