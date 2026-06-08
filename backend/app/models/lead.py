"""Modelo CRM — Leads y clientes."""
import uuid
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.db.pgtypes import JSONB, UUID
from app.models.base import TimestampMixin, UUIDMixin


class LeadStatus(str, PyEnum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    PROPOSAL_SENT = "proposal_sent"
    NEGOTIATING = "negotiating"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"
    ON_HOLD = "on_hold"


class LeadSource(str, PyEnum):
    WEBSITE = "website"
    WHATSAPP = "whatsapp"
    REFERRAL = "referral"
    PORTAL = "portal"
    SOCIAL = "social"
    MANUAL = "manual"


class Lead(UUIDMixin, TimestampMixin, Base):
    """Lead / cliente potencial del CRM."""
    __tablename__ = "leads"

    # ─── DATOS PERSONALES ────────────────────────────────────
    full_name: Mapped[str] = mapped_column(String(300), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(320), index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    phone_whatsapp: Mapped[Optional[str]] = mapped_column(String(50))
    nationality: Mapped[Optional[str]] = mapped_column(String(100))
    language: Mapped[str] = mapped_column(String(10), default="es")

    # ─── CRM ─────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        Enum(LeadStatus), nullable=False, default=LeadStatus.NEW, index=True
    )
    source: Mapped[str] = mapped_column(
        Enum(LeadSource), nullable=False, default=LeadSource.MANUAL
    )
    assigned_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    priority: Mapped[int] = mapped_column(Integer, default=0)  # 0-10
    score: Mapped[Optional[float]] = mapped_column()  # AI score del lead
    tags: Mapped[Optional[list]] = mapped_column(JSONB)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    next_action: Mapped[Optional[str]] = mapped_column(Text)
    next_action_at: Mapped[Optional[object]] = mapped_column(DateTime(timezone=True))

    # ─── PREFERENCIAS DE COMPRA ──────────────────────────────
    budget_min: Mapped[Optional[int]] = mapped_column(Integer)
    budget_max: Mapped[Optional[int]] = mapped_column(Integer)
    budget_currency: Mapped[str] = mapped_column(String(3), default="USD")
    preferred_operation: Mapped[Optional[str]] = mapped_column(String(30))
    preferred_zones: Mapped[Optional[list]] = mapped_column(JSONB)
    preferred_property_types: Mapped[Optional[list]] = mapped_column(JSONB)
    min_bedrooms: Mapped[Optional[int]] = mapped_column(Integer)
    min_area: Mapped[Optional[int]] = mapped_column(Integer)
    amenities_required: Mapped[Optional[list]] = mapped_column(JSONB)
    timeline: Mapped[Optional[str]] = mapped_column(String(100))  # "inmediato", "3 meses", etc.
    purpose: Mapped[Optional[str]] = mapped_column(String(100))   # "inversión", "residencia", etc.

    # ─── MÉTRICAS ────────────────────────────────────────────
    matched_properties_count: Mapped[int] = mapped_column(Integer, default=0)
    last_contacted_at: Mapped[Optional[object]] = mapped_column(DateTime(timezone=True))
    contact_attempts: Mapped[int] = mapped_column(Integer, default=0)
    deal_value: Mapped[Optional[int]] = mapped_column(Integer)  # Valor del deal si cierra

    # ─── RELACIONES ──────────────────────────────────────────
    assigned_to: Mapped[Optional["User"]] = relationship(
        "User", back_populates="leads", foreign_keys=[assigned_to_id]
    )
    conversations: Mapped[List["LeadConversation"]] = relationship(
        "LeadConversation", back_populates="lead", cascade="all, delete-orphan"
    )
    matched_properties: Mapped[List["LeadPropertyMatch"]] = relationship(
        "LeadPropertyMatch", back_populates="lead", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Lead {self.full_name} [{self.status}]>"


class LeadConversation(UUIDMixin, TimestampMixin, Base):
    """Historial de conversaciones con el lead."""
    __tablename__ = "lead_conversations"

    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(50), nullable=False)  # whatsapp, email, etc.
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # in, out
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # 'metadata' es reservado por Declarative → atributo extra_data, columna "metadata"
    extra_data: Mapped[Optional[dict]] = mapped_column("metadata", JSONB)
    sent_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    lead: Mapped["Lead"] = relationship("Lead", back_populates="conversations")


class LeadPropertyMatch(UUIDMixin, TimestampMixin, Base):
    """Matching entre leads y propiedades."""
    __tablename__ = "lead_property_matches"

    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    match_score: Mapped[float] = mapped_column(nullable=False)  # 0-100
    match_reasons: Mapped[Optional[list]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    sent_at: Mapped[Optional[object]] = mapped_column(DateTime(timezone=True))
    viewed_at: Mapped[Optional[object]] = mapped_column(DateTime(timezone=True))
    interested: Mapped[Optional[bool]] = mapped_column(Boolean)

    lead: Mapped["Lead"] = relationship("Lead", back_populates="matched_properties")
