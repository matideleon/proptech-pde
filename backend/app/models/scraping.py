"""Modelos para control de scraping."""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.pgtypes import JSONB, UUID
from app.models.base import TimestampMixin, UUIDMixin


class ScrapingSource(str, PyEnum):
    MERCADOLIBRE = "mercadolibre"
    INFOCASAS = "infocasas"
    GALLITO = "gallito"
    FACEBOOK = "facebook"
    INMOBILIARIA_LOCAL = "inmobiliaria_local"


class ScrapingStatus(str, PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ScrapingRun(UUIDMixin, Base):
    """
    Registro de cada ejecución de scraping.
    Permite monitoreo y debugging del sistema.
    """
    __tablename__ = "scraping_runs"

    source: Mapped[str] = mapped_column(
        Enum(ScrapingSource), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        Enum(ScrapingStatus), nullable=False, default=ScrapingStatus.PENDING, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)

    # ─── MÉTRICAS ────────────────────────────────────────────
    pages_scraped: Mapped[int] = mapped_column(Integer, default=0)
    properties_found: Mapped[int] = mapped_column(Integer, default=0)
    properties_new: Mapped[int] = mapped_column(Integer, default=0)
    properties_updated: Mapped[int] = mapped_column(Integer, default=0)
    properties_removed: Mapped[int] = mapped_column(Integer, default=0)
    price_changes: Mapped[int] = mapped_column(Integer, default=0)
    errors_count: Mapped[int] = mapped_column(Integer, default=0)

    # ─── LOGS ────────────────────────────────────────────────
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    log_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    config_used: Mapped[Optional[dict]] = mapped_column(JSONB)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(200))

    def __repr__(self) -> str:
        return f"<ScrapingRun {self.source} [{self.status}] {self.started_at}>"

    @property
    def success_rate(self) -> float:
        total = self.properties_found
        if total == 0:
            return 0
        return (total - self.errors_count) / total * 100
