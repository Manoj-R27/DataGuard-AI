import pandas as pd


def profile_batch(frame: pd.DataFrame) -> dict:
    profiles = {}
    for column in frame.columns:
        series = frame[column]
        numeric = pd.api.types.is_numeric_dtype(series)
        profiles[column] = {"dtype": str(series.dtype), "null_rate": float(series.isna().mean()), "cardinality": int(series.nunique(dropna=True)), "mean": float(series.mean()) if numeric else None, "std": float(series.std()) if numeric else None, "min": float(series.min()) if numeric else None, "max": float(series.max()) if numeric else None, "top_values": series.value_counts(dropna=True).head(10).to_dict()}
    return profiles
