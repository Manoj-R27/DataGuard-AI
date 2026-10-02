import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, ks_2samp
from src.multivariate_drift import multivariate_anomaly_rate


def detect_drift(reference: pd.DataFrame, current: pd.DataFrame, alpha: float = .01) -> dict:
    events = []
    for column in sorted(set(reference.columns) | set(current.columns)):
        if column not in reference or column not in current:
            events.append(_event(column, "schema-drift", 1.0, True, "column missing from one batch")); continue
        left, right = reference[column], current[column]
        null_delta = abs(left.isna().mean() - right.isna().mean())
        if null_delta >= .10:
            events.append(_event(column, "null-spike", null_delta, True, "null-rate delta"))
        if pd.api.types.is_numeric_dtype(left) and pd.api.types.is_numeric_dtype(right):
            stat, p = ks_2samp(left.dropna(), right.dropna())
            events.append(_event(column, "distribution-shift", float(stat), bool(p < alpha), f"KS p={p:.5g}"))
        else:
            categories = sorted(set(left.dropna().astype(str)) | set(right.dropna().astype(str)))
            table = pd.DataFrame({"reference": left.astype(str).value_counts(), "current": right.astype(str).value_counts()}).fillna(0)
            _, p, _, _ = chi2_contingency(table + 0.5)
            new = set(right.dropna().astype(str)) - set(left.dropna().astype(str))
            events.append(_event(column, "categorical-shift", float(1 - p), bool(p < alpha or new), f"chi-square p={p:.5g}; new={len(new)}"))
    flagged = [event for event in events if event["flagged"]]
    return {"overall_score": float(np.mean([event["score"] for event in flagged])) if flagged else 0.0, "drifted": bool(flagged), "columns": events, "multivariate_anomaly_rate": multivariate_anomaly_rate(reference, current)}


def _event(column, kind, score, flagged, detail):
    return {"column": column, "kind": kind, "score": float(score), "flagged": bool(flagged), "detail": detail}
