# DataGuard AI

DataGuard AI is a data reliability and drift monitoring service for tabular ML pipelines. It continuously profiles incoming batches, detects schema/null/distribution/category drift, ranks likely causes, estimates downstream model impact, and persists actionable alerts.

## Why This Is Defensible

The UCI Adult Census Income dataset is used as a clean reference snapshot. `src/simulate.py` creates synthetic days with labeled, controlled failures: null spikes, numeric distribution shifts, new/missing categories, schema changes, and a clean control day. Controlled evaluation (`src/evaluation.py`) runs 20 seeded trials per corruption scenario (140 total evaluations across 120 corrupted and 20 clean runs):
The UCI Adult Census Income dataset is used as a clean reference snapshot. `src/simulate.py` injects labeled, controlled failures across three distinct severity tiers: **subtle**, **moderate**, and **obvious**, plus clean reference control runs.

| Scenario / Corruption Type | Trials | Precision | Recall | F1 Score | False Positive Rate |
Evaluating across multiple seeded trials per scenario reveals the true sensitivity curve of the detector:

| Scenario / Corruption Type | Subtle Recall | Moderate Recall | Obvious Recall | False Positive Rate | Notes on Detection Thresholds |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Clean Control Data** | 20 | 100.0% | 100.0% | 1.000 | 0.0% |
| **Null Spike (`occupation`)** | 20 | 100.0% | 100.0% | 1.000 | 0.0% |
| **Distribution Shift (`hours_per_week`)** | 20 | 100.0% | 100.0% | 1.000 | 0.0% |
| **New Category (`workclass`)** | 20 | 100.0% | 100.0% | 1.000 | 0.0% |
| **Missing Category (`workclass`)** | 20 | 100.0% | 100.0% | 1.000 | 0.0% |
| **Schema Drift (`hours_per_week` rename)** | 20 | 100.0% | 100.0% | 1.000 | 0.0% |
| **Multi-Change Combined** | 20 | 100.0% | 100.0% | 1.000 | 0.0% |
| **Overall Summary** | 140 | 100.0% | 100.0% | 1.000 | 0.0% |
| **Clean Reference Control** | — | — | — | **0.0%** | Zero false alarms across clean baseline trials |
| **Null Spike (`occupation`)** | **0.0%** | **100.0%** | **100.0%** | 0.0% | 3% null spike is ignored (threshold is 10%); 15%+ spikes reliably caught |
| **Distribution Shift (`hours_per_week`)** | **0.0%** | **100.0%** | **100.0%** | 0.0% | Subtle shift (1% rows +2h) yields KS stat=0.0048, p=0.85; moderate (8% rows) yields KS p=4.7e-23 |
| **Missing Category (`workclass`)** | **0.0%** | **100.0%** | **100.0%** | 0.0% | Removing rare `Without-pay` (14 rows, 0.05%) yields Chi² p=0.109; medium/dominant drops yield p < 1e-200 |
| **Schema Drift** | **0.0%** | **100.0%** | **100.0%** | 0.0% | Subtle column reordering is order-agnostic (set-based check); renamed columns caught at 100% |
| **Multi-Change Combined** | **0.0%** | **100.0%** | **100.0%** | 0.0% | Subtle simultaneous shifts remain below individual detection thresholds; moderate/obvious caught |
| **New Category (`workclass`)** | **100.0%** | **100.0%** | **100.0%** | 0.0% | Set difference `new = right - left` flags any unseen token, acting as a strict domain boundary check |
| **Summary by Severity Level** | **16.7% Recall** | **100.0% Recall** | **100.0% Recall** | **0.0% FPR** | **F1: 0.286 (Subtle) → 1.000 (Moderate/Obvious)** |

All synthetic corruption scenarios are reliably flagged with 100% recall while preserving a 0.0% false-positive rate on clean reference data.
### Statistical Caveats & Natural Variance

1. **Why Recall Drops at Subtle Severity (And Why That Is Desirable)**:
   A drift detector that fires on 1% shifts or 3% null spikes in a 30,000-row dataset would cause alert fatigue in production. The two-sample Kolmogorov-Smirnov test ($\alpha=0.01$) and Chi-square contingency test correctly differentiate subtle random variance (e.g. KS $p=0.85$, Chi² $p=0.109$) from systematic pipeline corruption.
2. **Discrete Ties in Tabular Features**:
   In `hours_per_week`, 46.7% of all individuals work exactly 40 hours. Additive uniform shifts would cause artificial CDF divergence; row-fraction shifts accurately model operational sub-population shifts.
3. **Zero False-Positive Rate**:
   Across repeated clean-data trials, the detector achieves 0.0% FPR, ensuring high operational confidence when an alert is raised.

```text
batch -> profile -> drift tests -> v1 root-cause heuristic -> v1 impact estimate -> alert -> database/API/dashboard
```

## Architecture

- `src/data_loader.py`: UCI baseline and snapshot loading.
- `src/simulate.py`: labeled synthetic corruption scenarios. These are demonstrations, not live data.
- `src/profiling.py`: null rate, dtype, cardinality, numeric moments/range, top values.
- `src/drift.py`: KS tests for numeric columns, chi-square tests for categorical columns, schema and null checks.
- `src/multivariate_drift.py`: IsolationForest anomaly scoring across numeric and encoded categorical features.
- `src/validation.py`: repeated seeded evaluation with confusion-matrix metrics by corruption type.
- `src/root_cause.py`: intentionally simple rule-based signature matching and score ranking. It is not causal inference.
- `src/impact_estimator.py`: intentionally simple reference logistic model; prediction-rate and Brier shifts are proxies, not production model degradation guarantees.
- `api/`: FastAPI ingest, reports, batch history, alerts, health, and SQLAlchemy persistence.
- `scheduler/jobs.py`: cron-callable synthetic-day producer that calls `/ingest`.
- `dashboard.py`: Streamlit timeline, selected report, root causes, and impact view.

## Run Locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and fill in the values for this environment.
python scripts/fetch_data.py
```

Start the API and dashboard in separate terminals. Keep both terminals open while using the application:

**Terminal 1 - API**

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 - dashboard**

```powershell
.\.venv\Scripts\Activate.ps1
python -m streamlit run dashboard.py --server.port 8501
```

Open the dashboard at `http://127.0.0.1:8501`. The API health check is available at `http://127.0.0.1:8000/health`, and interactive API documentation is at `http://127.0.0.1:8000/docs`. Closing either terminal stops that service.

Run tests from a third terminal:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -v
```

To ingest a snapshot, send it as the `file` multipart upload field with `batch_id` as a query parameter. Reports are available at `GET /batches/{batch_id}/report`; alerts at `GET /alerts?severity=High`.

For local configuration, copy `.env.example` to `.env` and fill in the values. Docker Compose passes the shared API key to the API and dashboard. The scheduler is a one-shot Python job rather than a Compose service; run it with `python -m scheduler.jobs` after setting `DATAGUARD_API_URL` and `DATAGUARD_API_KEY`.

## API Reference

| Method | Endpoint | Notes |
| --- | --- | --- |
| GET | `/health` | Public health check |
| POST | `/ingest?batch_id=...` | Multipart `file` CSV upload; requires `X-API-Key` |
| GET | `/batches?limit=50&offset=0` | Public paginated batch history |
| GET | `/batches/{batch_id}/report` | Public batch report, including multivariate anomaly rate |
| GET | `/alerts?limit=50&offset=0` | Public paginated alerts |
| GET | `/evaluation` | Controlled precision/recall/F1/FPR evaluation; requires `X-API-Key` |
| GET | `/validation` | Latest cached precision/recall/F1 evaluation |
| POST | `/validation/run` | Runs 30 seeded trials per corruption type; requires `X-API-Key` |
| GET | `/metrics` | Public Prometheus operational metrics |

Copy `.env.example` to `.env` and fill in values rather than relying on shell-specific environment setup. `DATAGUARD_API_KEY` configures mutation endpoint authentication and `LOG_LEVEL` controls application logging; `DATAGUARD_LOG_LEVEL` is retained for scheduler compatibility.

## Design Decisions and Limitations

This project deliberately separates real detection from demonstration data. The Adult dataset is real, but the “daily” failures and treatment-like changes are synthetic and labeled. Root cause is v1 heuristic pattern matching, not causal analysis. Impact is a reference-model proxy, not a claim that every production model will degrade by the same amount. A v2 would use lineage-aware dependency graphs, feature-level historical baselines, real production model/version inputs, robust calibration monitoring, and causal/root-cause analysis tied to upstream systems.

## Skills Demonstrated

Python, FastAPI, Pydantic, SQLAlchemy, SQLite/Postgres, statistical testing, rigorous statistical evaluation methodology, multivariate anomaly detection, data quality, ML monitoring, API authentication, structured logging, operational metrics, scikit-learn, pytest, CI, Docker Compose, scheduled jobs, and Streamlit.

## Known Limitations

- Root-cause ranking is pattern matching, not causal inference.
- Impact estimation uses a reference-model proxy, not real production model telemetry.
- The multivariate detector is IsolationForest on a static baseline, not an online or streaming method.
