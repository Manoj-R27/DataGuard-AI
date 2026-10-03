
To ingest a snapshot, send it as the `file` multipart upload field with `batch_id` as a query parameter. Reports are available at `GET /batches/{batch_id}/report`; alerts at `GET /alerts?severity=High`.

For local configuration, copy `.env.example` to `.env` and fill in the values. Docker Compose passes the shared API key to the API and dashboard. The scheduler is a one-shot Python job rather than a Compose service; run it with `python -m scheduler.jobs` after setting `DATAGUARD_API_URL` and `DATAGUARD_API_KEY`.

## API Reference

| Method | Endpoint                     | Notes                                                               |
| ------ | ----------------------------- | --------------------------------------------------------------------- |
| GET    | `/health`                    | Public health check                                                   |
| POST   | `/ingest?batch_id=...`       | Multipart `file` CSV upload; requires `X-API-Key`                     |
| GET    | `/batches?limit=50&offset=0` | Public paginated batch history                                        |
| GET    | `/batches/{batch_id}/report` | Public batch report, including multivariate anomaly rate              |
| GET    | `/alerts?limit=50&offset=0`  | Public paginated alerts                                               |
| GET    | `/evaluation`                 | Controlled precision/recall/F1/FPR evaluation; requires `X-API-Key`   |
| GET    | `/validation`                 | Latest cached precision/recall/F1 evaluation                          |
| POST   | `/validation/run`             | Runs seeded trials per corruption type (see src/validation.py for the exact count); requires `X-API-Key` |
| GET    | `/metrics`                    | Public Prometheus operational metrics                                 |

Copy `.env.example` to `.env` and fill in values rather than relying on shell-specific environment setup. `DATAGUARD_API_KEY` configures mutation endpoint authentication and `LOG_LEVEL` controls application logging; `DATAGUARD_LOG_LEVEL` is retained for scheduler compatibility.

## Design Decisions and Limitations

This project deliberately separates real detection from demonstration data. The Adult dataset is real, but the "daily" failures and treatment-like changes are synthetic and labeled. Root cause is v1 heuristic pattern matching, not causal analysis. Impact is a reference-model proxy, not a claim that every production model will degrade by the same amount. A v2 would use lineage-aware dependency graphs, feature-level historical baselines, real production model/version inputs, robust calibration monitoring, and causal/root-cause analysis tied to upstream systems.

## Skills Demonstrated

Python, FastAPI, Pydantic, SQLAlchemy, SQLite/Postgres, statistical testing, rigorous statistical evaluation methodology, multivariate anomaly detection, data quality, ML monitoring, API authentication, structured logging, operational metrics, scikit-learn, pytest, CI, Docker Compose, scheduled jobs, and Streamlit.

## Known Limitations

- Root-cause ranking is pattern matching, not causal inference.
- Impact estimation uses a reference-model proxy, not real production model telemetry.
- The multivariate detector is IsolationForest on a static baseline, not an online or streaming method.
