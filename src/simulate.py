from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

SEVERITY_LEVELS = ("subtle", "moderate", "obvious")


@dataclass
class Injection:
    kind: str
    columns: list[str]
    details: str
    severity: str = "obvious"


def simulate_days(baseline: pd.DataFrame, seed: int = 42, severity: str = "obvious") -> list[tuple[str, pd.DataFrame, dict]]:
    """Create labeled synthetic snapshots with controllable corruption severity."""
    if severity not in SEVERITY_LEVELS:
        raise ValueError(f"Unknown severity '{severity}'. Must be one of {SEVERITY_LEVELS}")
    rng = np.random.default_rng(seed)
    schema_columns = ["hours_per_week"] if severity == "obvious" else ["fnlwgt"] if severity == "moderate" else ["columns"]
    cases = [
        ("day_01_null_spike", _null_spike(baseline, "occupation", rng, severity), Injection("null-spike", ["occupation"], f"null values injected ({severity})", severity)),
        ("day_02_numeric_shift", _numeric_shift(baseline, "hours_per_week", rng, severity), Injection("distribution-shift", ["hours_per_week"], f"mean shifted upward ({severity})", severity)),
        ("day_03_new_category", _new_category(baseline, "workclass", rng, severity), Injection("new-category", ["workclass"], f"new synthetic category ({severity})", severity)),
        ("day_04_missing_category", _missing_category(baseline, "workclass", severity), Injection("missing-category", ["workclass"], f"category removed ({severity})", severity)),
        ("day_05_schema_drift", _schema_drift(baseline, severity), Injection("schema-drift", schema_columns, f"schema change ({severity})", severity)),
        ("day_06_multi_change", _multi_change(baseline, rng, severity), Injection("multi-change", ["hours_per_week", "occupation", "workclass"], f"numeric, null, and category changes ({severity})", severity)),
    ]
    return [("day_00_clean", baseline.copy(), {"injections": []})] + [(name, frame, {"injections": [asdict(injection)]}) for name, frame, injection in cases]


def _null_spike(frame, column, rng, severity="obvious"):
    rates = {"subtle": 0.03, "moderate": 0.15, "obvious": 0.40}
    result = frame.copy()
    indexes = rng.choice(result.index, int(len(result) * rates[severity]), replace=False)
    result.loc[indexes, column] = np.nan
    return result


def _numeric_shift(frame, column, rng, severity="obvious"):
    result = frame.copy()
    if severity == "subtle":
        indexes = rng.choice(result.index, int(len(result) * 0.01), replace=False)
        result.loc[indexes, column] += 2
    elif severity == "moderate":
        indexes = rng.choice(result.index, int(len(result) * 0.08), replace=False)
        result.loc[indexes, column] += 4
    else:
        result[column] = result[column] * 1.35 + 8
    return result


def _new_category(frame, column, rng, severity="obvious"):
    rates = {"subtle": 0.001, "moderate": 0.02, "obvious": 0.10}
    result = frame.copy()
    indexes = rng.choice(result.index, max(1, int(len(result) * rates[severity])), replace=False)
    result.loc[indexes, column] = "Synthetic_New_Category"
    return result


def _missing_category(frame, column, severity="obvious"):
    result = frame.copy()
    if severity == "subtle":
        result.loc[result[column] == "Without-pay", column] = "Private"
    elif severity == "moderate":
        result.loc[result[column] == "Federal-gov", column] = "Private"
    else:
        result.loc[result[column] == result[column].mode().iat[0], column] = "Self-emp-not-inc"
    return result


def _schema_drift(frame, severity="obvious"):
    if severity == "subtle":
        return frame[list(frame.columns)[::-1]]
    if severity == "moderate":
        return frame.rename(columns={"fnlwgt": "sample_weight"})
    return frame.rename(columns={"hours_per_week": "weekly_hours"})


def _multi_change(frame, rng, severity="obvious"):
    result = _numeric_shift(frame, "hours_per_week", rng, severity)
    result = _null_spike(result, "occupation", rng, severity)
    if severity == "subtle":
        return _missing_category(result, "workclass", severity)
    return _new_category(result, "workclass", rng, severity)
