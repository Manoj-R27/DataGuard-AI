from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

class DataBatch(Base):
    __tablename__ = "data_batches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    status: Mapped[str] = mapped_column(String, default="processed")
    drift_score: Mapped[float] = mapped_column(Float, default=0)
    severity: Mapped[str] = mapped_column(String, default="Low")
    report: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ColumnProfile(Base):
    __tablename__ = "column_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[str] = mapped_column(String, index=True)
    column_name: Mapped[str] = mapped_column(String)
    profile: Mapped[dict] = mapped_column(JSON)

class DriftEvent(Base):
    __tablename__ = "drift_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[str] = mapped_column(String, index=True)
    event: Mapped[dict] = mapped_column(JSON)

class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[str] = mapped_column(String, index=True)
    severity: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
