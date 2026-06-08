"""Modelos para el sistema de alertas."""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.db.pgtypes import JSONB, UUID
from app.models.base import TimestampMixin, UUIDMixin


class AlertType(str, PyEnum):
    NEW_PROPERTY = "new_property"
    PRICE_DROP = "price_drop"
    PRICE_INCREASE = "price_increase"
    PROPERTY_REMOVED = "property_removed"
    OPPORTUNITY_DETECTED = "opportunity_detected"
    PREMIUM_PROPERTY = "premium_property"
    MARKET_REPORT = "market_report"


class AlertChannel(str, PyEnum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    PUSH = "push"
    WEBHOOK = "webhook"


class AlertFrequency(str, PyEnum):
    INSTANT = "instant"
    DAILY = "daily"
    WEEKLY = "weekly"


class Alert(UUIDMixin, TimestampMixin, Base):
    """
    Configuración de alertas por usuario.

    Permite configurar criterios de filtro para recibir notificaciones
    cuando aparezcan propiedades que cumplan las condiciones.
    """
    __tablename__ = "alerts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    frequency: Mapped[str] = mapped_column(
        Enum(AlertFrequency), default=AlertFrequency.INSTANT
    )

    # ─── CRITERIOS DE FILTRO ─────────────────────────────────
    alert_types: Mapped[Optional[list]] = mapped_column(JSONB)  # Lista de AlertType
    operation: Mapped[Optional[str]] = mapped_column(String(30))
    property_types: Mapped[Optional[list]] = mapped_column(JSONB)
    zone_ids: Mapped[Optional[list]] = mapped_column(JSONB)
    neighborhoods: Mapped[Optional[list]] = mapped_column(JSONB)
    price_min: Mapped[Optional[int]] = mapped_column(Integer)
    price_max: Mapped[Optional[int]] = mapped_column(Integer)
    currency: Mapped[Optional[str]] = mapped_column(String(3))
    bedrooms_min: Mapped[Optional[int]] = mapped_column(Integer)
    bedrooms_max: Mapped[Optional[int]] = mapped_column(Integer)
    area_min: Mapped[Optional[int]] = mapped_column(Integer)
    area_max: Mapped[Optional[int]] = mapped_column(Integer)
    price_drop_min_pct: Mapped[Optional[float]] = mapped_column()  # Mínimo % de baja
    ai_score_min: Mapped[Optional[float]] = mapped_column()  # Score mínimo de IA
    only_opportunities: Mapped[bool] = mapped_column(Boolean, default=False)
    only_premium: Mapped[bool] = mapped_column(Boolean, default=False)

    # ─── CANALES ─────────────────────────────────────────────
    channels: Mapped[Optional[list]] = mapped_column(JSONB)  # Lista de AlertChannel
    webhook_url: Mapped[Optional[str]] = mapped_column(Text)
    phone_override: Mapped[Optional[str]] = mapped_column(String(50))

    # ─── MÉTRICAS ────────────────────────────────────────────
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    last_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # ─── RELACIONES ──────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="alerts")

    def __repr__(self) -> str:
        return f"<Alert '{self.name}' [{self.user_id}]>"
