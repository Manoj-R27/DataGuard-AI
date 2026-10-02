from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests

ADULT_URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = PROJECT_ROOT / "data" / "adult_baseline.csv"
COLUMNS = ["age", "workclass", "fnlwgt", "education", "education_num", "marital_status", "occupation", "relationship", "race", "sex", "capital_gain", "capital_loss", "hours_per_week", "native_country", "income"]

@dataclass
class Batch:
    batch_id: str
    frame: pd.DataFrame
    ground_truth: dict


def load_baseline(source: str = ADULT_URL) -> pd.DataFrame:
    path = Path(source)
    if source == ADULT_URL and CACHE_PATH.exists():
        path = CACHE_PATH

    if path.exists():
        frame = pd.read_csv(path, names=COLUMNS, header=None, na_values=" ?", skipinitialspace=True)
    else:
        try:
            response = requests.get(source, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
            response.raise_for_status()
        except (requests.RequestException, OSError) as exc:
            raise RuntimeError(
                f"Unable to fetch baseline data from {source}. "
                "Run scripts/fetch_data.py after checking network access."
            ) from exc
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_bytes(response.content)
        frame = pd.read_csv(BytesIO(response.content), names=COLUMNS, header=None, na_values=" ?", skipinitialspace=True)
    return frame.dropna().reset_index(drop=True)


def load_snapshot(path: str) -> pd.DataFrame:
    return pd.read_csv(path)
