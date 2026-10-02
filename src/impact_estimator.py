import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

TARGET = "income"


def _income_target(values):
    return values.astype(str).str.strip().eq(">50K").astype(int)

def fit_reference_model(baseline: pd.DataFrame):
    features = baseline.drop(columns=[TARGET])
    numeric = features.select_dtypes(include="number").columns
    categorical = features.select_dtypes(exclude="number").columns
    model = make_pipeline(ColumnTransformer([("num", StandardScaler(), numeric), ("cat", OneHotEncoder(handle_unknown="ignore"), categorical)]), LogisticRegression(max_iter=500))
    model.fit(features, _income_target(baseline[TARGET]))
    return model


def estimate_impact(model, baseline: pd.DataFrame, current: pd.DataFrame) -> dict:
    """V1 proxy: prediction and Brier shifts are estimates, not production impact."""
    baseline_y = _income_target(baseline[TARGET])
    current_y = _income_target(current[TARGET]) if TARGET in current else None
    baseline_prob = model.predict_proba(baseline.drop(columns=[TARGET]))[:, 1]
    current_prob = model.predict_proba(current.drop(columns=[TARGET], errors="ignore"))[:, 1]
    return {"mean_probability_shift": float(abs(current_prob.mean() - baseline_prob.mean())), "prediction_rate_shift": float(abs((current_prob >= .5).mean() - (baseline_prob >= .5).mean())), "baseline_brier": float(brier_score_loss(baseline_y, baseline_prob)), "current_brier": float(brier_score_loss(current_y, current_prob)) if current_y is not None else None}
