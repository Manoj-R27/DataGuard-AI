import json
import logging
import os
import time
from io import BytesIO
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, Response, UploadFile
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.orm import Session
from src.alerts import build_alert
from src.data_loader import COLUMNS, load_baseline
from src.drift import detect_drift
from src.impact_estimator import estimate_impact, fit_reference_model
from src.profiling import profile_batch
from src.root_cause import rank_root_causes
from src.simulate import simulate_days
from src.validation import evaluate_detector
from src.evaluation import evaluate_detector as run_evaluation

load_dotenv()

from .database import SessionLocal, init_db
from .models import Alert, ColumnProfile, DataBatch, DriftEvent


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "batch_id"):
            log_entry["batch_id"] = record.batch_id
        if hasattr(record, "severity"):
            log_entry["severity"] = record.severity
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


log_level_name = os.getenv("LOG_LEVEL", os.getenv("DATAGUARD_LOG_LEVEL", "INFO")).upper()
log_level = getattr(logging, log_level_name, logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(StructuredFormatter())
_root = logging.getLogger()
_root.setLevel(log_level)
_root.handlers = [_handler]
logger = logging.getLogger("dataguard.api")

app = FastAPI(title="DataGuard AI", version="1.0.0")
BASELINE = None
REFERENCE_MODEL = None
LATEST_VALIDATION = None
LATEST_EVALUATION = None
BATCHES_INGESTED = Counter("dataguard_batches_ingested_total", "Total batches ingested")
ALERTS_BY_SEVERITY = Counter("dataguard_alerts_total", "Total alerts by severity", ["severity"])
LATEST_DRIFT_SCORE = Gauge("dataguard_drift_score", "Drift score of the most recent batch")
DRIFT_LATENCY = Histogram("dataguard_drift_detection_seconds", "Drift detection latency in seconds")
Instrumentator().instrument(app).expose(app, endpoint="/metrics")
init_db()

@app.on_event("startup")
def startup():
    global BASELINE, REFERENCE_MODEL
    init_db()
    try:
        BASELINE = load_baseline()
        REFERENCE_MODEL = fit_reference_model(BASELINE)
    except Exception:
        BASELINE = None
        REFERENCE_MODEL = None
        logger.exception("Reference model initialization failed; retry startup after fixing baseline data or network access")

def db():
    session = SessionLocal()
    try: yield session
    finally: session.close()

def require_api_key(x_api_key: str | None = Header(default=None)):
    expected = os.getenv("DATAGUARD_API_KEY")
    if not expected or x_api_key != expected:
        raise HTTPException(401, "missing or invalid X-API-Key")

@app.get("/health")
def health(): return {"status": "ok", "service": "dataguard-ai"}

@app.get("/validation")
def validation():
    if LATEST_VALIDATION is None:
        raise HTTPException(404, "validation has not been run; POST /validation/run first")
    return LATEST_VALIDATION

@app.post("/validation/run", dependencies=[Depends(require_api_key)])
def run_validation():
    global LATEST_VALIDATION
    if BASELINE is None:
        raise HTTPException(503, "reference data is not initialized")
    LATEST_VALIDATION = evaluate_detector(BASELINE)
    logger.info("Detector validation completed", extra={"batch_id": "validation", "severity": "info"})
    return LATEST_VALIDATION

@app.get("/evaluation", dependencies=[Depends(require_api_key)])
def evaluation(trials: int = Query(20, ge=1, le=100), refresh: bool = False):
    global LATEST_EVALUATION
    if BASELINE is None:
        raise HTTPException(503, "reference data is not initialized")
    if LATEST_EVALUATION is None or refresh or LATEST_EVALUATION.get("trials_per_type") != trials:
        LATEST_EVALUATION = run_evaluation(BASELINE, trials=trials)
    return LATEST_EVALUATION

@app.post("/ingest")
def ingest(batch_id: str = Query(...), file: UploadFile = File(...), session: Session = Depends(db), _: None = Depends(require_api_key)):
    if BASELINE is None or REFERENCE_MODEL is None:
        raise HTTPException(503, "reference model is not initialized")
    try:
        current = pd.read_csv(BytesIO(file.file.read()))
    except Exception as exc:
        raise HTTPException(422, f"uploaded file is not a parseable CSV: {exc}") from exc
    missing = [column for column in COLUMNS if column not in current.columns]
    unexpected = [column for column in current.columns if column not in COLUMNS]
    if missing or unexpected:
        details = []
        if missing:
            details.append(f"missing columns: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected columns: {', '.join(unexpected)}")
        raise HTTPException(422, "uploaded CSV has invalid columns; " + "; ".join(details))
    started = time.perf_counter()
    drift = detect_drift(BASELINE, current)
    DRIFT_LATENCY.observe(time.perf_counter() - started)
    causes = rank_root_causes(drift)
    impact = estimate_impact(REFERENCE_MODEL, BASELINE, current)
    alert = build_alert(drift, causes, impact)
    record = DataBatch(batch_id=batch_id, status="processed", drift_score=drift["overall_score"], severity=alert["severity"], report={"batch_id": batch_id, "drift": drift, "root_causes": causes, "impact": impact, "alert": alert})
    session.add(record)
    for column, value in profile_batch(current).items(): session.add(ColumnProfile(batch_id=batch_id, column_name=column, profile=value))
    for event in drift["columns"]: session.add(DriftEvent(batch_id=batch_id, event=event))
    if alert["severity"] != "Low": session.add(Alert(batch_id=batch_id, severity=alert["severity"], payload=alert))
    session.commit(); session.refresh(record)
    LATEST_DRIFT_SCORE.set(drift["overall_score"])
    BATCHES_INGESTED.inc()
    ALERTS_BY_SEVERITY.labels(severity=alert["severity"]).inc()
    logger.info("Batch ingested", extra={"batch_id": batch_id, "severity": alert["severity"]})
    return {"id": record.id, "batch_id": batch_id, "status": record.status, "drifted": drift["drifted"], "severity": alert["severity"]}

@app.get("/batches")
def batches(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), session: Session = Depends(db)):
    total = session.query(DataBatch).count()
    items = session.query(DataBatch).order_by(DataBatch.created_at.desc()).offset(offset).limit(limit).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}

@app.get("/batches/{batch_id}/report")
def report(batch_id: str, session: Session = Depends(db)):
    record = session.query(DataBatch).filter_by(batch_id=batch_id).first()
    if not record: raise HTTPException(404, "batch not found")
    return record.report

@app.get("/alerts")
def alerts(severity: str | None = None, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), session: Session = Depends(db)):
    query = session.query(Alert)
    if severity: query = query.filter_by(severity=severity)
    total = query.count()
    items = query.order_by(Alert.created_at.desc()).offset(offset).limit(limit).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}

