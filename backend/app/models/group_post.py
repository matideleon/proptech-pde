"""Modelo de posts de grupos de Facebook (alquileres ofrecidos / solicitados)."""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.pgtypes import JSONB, UUID
from app.models.base import TimestampMixin, UUIDMixin


class PostKind(str, PyEnum):
    OFERTA = "oferta"      # alguien ofrece un alquiler
    DEMANDA = "demanda"    # alguien busca un alquiler
    OTRO = "otro"          # no relevante


class GroupPost(UUIDMixin, TimestampMixin, Base):
    """
    Post de un grupo de Facebook, clasificado como oferta o demanda de alquiler.

    Es deliberadamente independiente de `Property`: los posts de grupos son más
    ruidosos y de menor calidad que los listados de portales, y la demanda
    (gente buscando) no tiene equivalente en el catálogo de propiedades.
    """
    __tablename__ = "group_posts"

    # ─── ORIGEN ──────────────────────────────────────────────
    source: Mapped[str] = mapped_column(String(50), default="facebook_group", index=True)
    group_id: Mapped[str] = mapped_column(String(100), index=True)
    group_name: Mapped[Optional[str]] = mapped_column(String(300))
    # ID estable del post para deduplicar entre corridas
    fb_post_id: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    permalink: Mapped[Optional[str]] = mapped_column(String(600))

    # ─── AUTOR ───────────────────────────────────────────────
    author_name: Mapped[Optional[str]] = mapped_column(String(300))
    author_profile: Mapped[Optional[str]] = mapped_column(String(600))

    # Links a portales inmobiliarios (Marketplace, InfoCasas, ML, Gallito…)
    # que el autor pegó dentro del post. Lista de URLs.
    external_links: Mapped[Optional[list]] = mapped_column(JSONB, default=list)

    # ─── CONTENIDO ───────────────────────────────────────────
    text: Mapped[str] = mapped_column(Text)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)

    # ─── CLASIFICACIÓN ───────────────────────────────────────
    kind: Mapped[PostKind] = mapped_column(
        Enum(PostKind), default=PostKind.OTRO, nullable=False, index=True
    )
    operation: Mapped[Optional[str]] = mapped_column(String(20))   # alquiler | venta
    property_type: Mapped[Optional[str]] = mapped_column(String(50))
    period: Mapped[Optional[str]] = mapped_column(String(20))      # anual | invernal | temporada | diario
    neighborhood: Mapped[Optional[str]] = mapped_column(String(200), index=True)
    price: Mapped[Optional[float]] = mapped_column(Numeric(14, 2))
    currency: Mapped[Optional[str]] = mapped_column(String(10))
    bedrooms: Mapped[Optional[int]] = mapped_column(Integer)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50))
    confidence: Mapped[float] = mapped_column(Numeric(4, 2), default=0)
    classified_by: Mapped[str] = mapped_column(String(20), default="keywords")  # keywords | ai

    # ─── GESTIÓN ─────────────────────────────────────────────
    is_reviewed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Datos crudos del scrape (por si se quiere reprocesar)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
