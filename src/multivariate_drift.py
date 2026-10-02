import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


_MODEL_CACHE = {}


def multivariate_anomaly_rate(reference: pd.DataFrame, current: pd.DataFrame) -> float:
    """Return the fraction of current records that differ from baseline patterns."""
    columns = [column for column in reference.columns if column in current.columns]
    if not columns or current.empty:
        return 0.0

    numeric = reference[columns].select_dtypes(include="number").columns.tolist()
    categorical = [column for column in columns if column not in numeric]
    cache_key = (id(reference), tuple(columns))
    cached = _MODEL_CACHE.get(cache_key)
    if cached is None:
        baseline_features, feature_columns = _encode(reference[columns], numeric, categorical)
        model = IsolationForest(n_estimators=50, contamination="auto", random_state=42, max_samples=min(256, len(baseline_features)))
        model.fit(baseline_features)
        cached = (model, feature_columns)
        _MODEL_CACHE[cache_key] = cached
    model, feature_columns = cached
    current_features, _ = _encode(current[columns], numeric, categorical, feature_columns)
    return float(np.mean(model.predict(current_features) == -1))


def _encode(frame, numeric, categorical, feature_columns=None):
    features = []
    if numeric:
        numeric_values = frame[numeric].apply(pd.to_numeric, errors="coerce")
        features.append(numeric_values.fillna(numeric_values.median()).fillna(0))
    if categorical:
        categorical_values = frame[categorical].fillna("<MISSING>").astype(str)
        features.append(pd.get_dummies(categorical_values, dtype=float))
    if not features:
        return np.empty((len(frame), 0)), []
    encoded = pd.concat(features, axis=1)
    if feature_columns is not None:
        encoded = encoded.reindex(columns=feature_columns, fill_value=0)
    return encoded.to_numpy(dtype=float), encoded.columns.tolist()