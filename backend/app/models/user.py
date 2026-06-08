"""Modelo de usuarios del sistema."""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.db.pgtypes import UUID
from app.models.base import TimestampMixin, UUIDMixin


class UserRole(str, PyEnum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    ANALYST = "analyst"
    AGENT = "agent"  # Corredor inmobiliario
    CLIENT = "client"
    VIEWER = "viewer"


class User(UUIDMixin, TimestampMixin, Base):
    """Usuario del sistema PropTech."""
    __tablename__ = "users"

    # ─── DATOS PERSONALES ────────────────────────────────────
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(300), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    phone_whatsapp: Mapped[Optional[str]] = mapped_column(String(50))
    telegram_id: Mapped[Optional[str]] = mapped_column(String(100))
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)

    # ─── AUTH ────────────────────────────────────────────────
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum(UserRole), nullable=False, default=UserRole.VIEWER
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # ─── PREFERENCIAS / ALERTAS ──────────────────────────────
    alert_email: Mapped[bool] = mapped_column(Boolean, default=True)
    alert_whatsapp: Mapped[bool] = mapped_column(Boolean, default=False)
    alert_telegram: Mapped[bool] = mapped_column(Boolean, default=False)

    # ─── RELACIONES ──────────────────────────────────────────
    alerts: Mapped[List["Alert"]] = relationship("Alert", back_populates="user")
    leads: Mapped[List["Lead"]] = relationship(
        "Lead", back_populates="assigned_to", foreign_keys="Lead.assigned_to_id"
    )

    def __repr__(self) -> str:
        return f"<User {self.email} [{self.role}]>"

    @property
    def is_admin(self) -> bool:
        return self.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN)
