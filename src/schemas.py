from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict

class IngestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    batch_id: str
    status: str
    drifted: bool
    severity: str

class BatchSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    batch_id: str
    status: str
    drift_score: float
    severity: str
    created_at: datetime

class Report(BaseModel):
    batch: dict[str, Any]
    drift: dict[str, Any]
    root_causes: list[dict[str, Any]]
    impact: dict[str, Any]
    alert: dict[str, Any]

class AlertSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    batch_id: str
    severity: str
    payload: dict[str, Any]
    created_at: datetime

class PaginatedBatches(BaseModel):
    items: list[BatchSummary]
    total: int
    limit: int
    offset: int

class PaginatedAlerts(BaseModel):
    items: list[AlertSummary]
    total: int
    limit: int
    offset: int

