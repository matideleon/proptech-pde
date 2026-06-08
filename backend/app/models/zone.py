"""Modelo de zonas/barrios de Punta del Este."""
import uuid
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Boolean, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.db.pgtypes import UUID, Geography
from app.models.base import TimestampMixin, UUIDMixin


class Zone(UUIDMixin, TimestampMixin, Base):
    """
    Zonas/barrios de Punta del Este y Maldonado.
    Incluye polígono geográfico para clasificar propiedades.
    """
    __tablename__ = "zones"

    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    name_aliases: Mapped[Optional[str]] = mapped_column(Text)  # Nombres alternativos separados por |
    description: Mapped[Optional[str]] = mapped_column(Text)

    # ─── GEOLOCALIZACIÓN ─────────────────────────────────────
    centroid: Mapped[Optional[object]] = mapped_column(
        Geography(geometry_type="POINT", srid=4326), nullable=True
    )
    polygon: Mapped[Optional[object]] = mapped_column(
        Geography(geometry_type="POLYGON", srid=4326), nullable=True
    )
    latitude: Mapped[Optional[float]] = mapped_column()
    longitude: Mapped[Optional[float]] = mapped_column()

    # ─── MÉTRICAS ────────────────────────────────────────────
    avg_price_sale_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    avg_price_rent_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    avg_price_m2_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    active_properties_count: Mapped[int] = mapped_column(Integer, default=0)
    premium_percentage: Mapped[Optional[float]] = mapped_column()  # % propiedades premium
    avg_roi: Mapped[Optional[float]] = mapped_column()  # ROI promedio estimado

    # ─── CLASIFICACIÓN ───────────────────────────────────────
    tier: Mapped[Optional[str]] = mapped_column(String(20))  # premium, standard, budget
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)  # Para ordenamiento

    # ─── RELACIONES ──────────────────────────────────────────
    properties: Mapped[List["Property"]] = relationship("Property", back_populates="zone")

    def __repr__(self) -> str:
        return f"<Zone {self.name}>"


# ─── ZONAS PREDEFINIDAS DE PUNTA DEL ESTE ─────────────────────
PUNTA_DEL_ESTE_ZONES = [
    {"name": "Punta del Este Centro", "slug": "pde-centro", "tier": "premium", "latitude": -34.9633, "longitude": -54.9367},
    {"name": "La Barra", "slug": "la-barra", "tier": "premium", "latitude": -34.9058, "longitude": -54.8692},
    {"name": "José Ignacio", "slug": "jose-ignacio", "tier": "premium", "latitude": -34.8458, "longitude": -54.6631},
    {"name": "Manantiales", "slug": "manantiales", "tier": "premium", "latitude": -34.8667, "longitude": -54.7833},
    {"name": "Punta Ballena", "slug": "punta-ballena", "tier": "premium", "latitude": -34.9833, "longitude": -55.0667},
    {"name": "Portezuelo", "slug": "portezuelo", "tier": "premium", "latitude": -34.9500, "longitude": -54.9833},
    {"name": "Cantegril", "slug": "cantegril", "tier": "standard", "latitude": -34.9700, "longitude": -54.9600},
    {"name": "Pinares", "slug": "pinares", "tier": "standard", "latitude": -34.9750, "longitude": -54.9450},
    {"name": "Beverly Hills", "slug": "beverly-hills", "tier": "standard", "latitude": -34.9650, "longitude": -54.9550},
    {"name": "Maldonado Centro", "slug": "maldonado-centro", "tier": "standard", "latitude": -34.9011, "longitude": -54.9617},
    {"name": "San Rafael", "slug": "san-rafael", "tier": "premium", "latitude": -34.9583, "longitude": -54.9917},
    {"name": "El Chorro", "slug": "el-chorro", "tier": "premium", "latitude": -34.8833, "longitude": -54.8167},
    {"name": "Montoya", "slug": "montoya", "tier": "premium", "latitude": -34.9000, "longitude": -54.8500},
    {"name": "Solanas", "slug": "solanas", "tier": "standard", "latitude": -34.9167, "longitude": -54.8833},
    {"name": "Aidy Grill", "slug": "aidy-grill", "tier": "standard", "latitude": -34.9500, "longitude": -54.9700},
    {"name": "Roosevelt", "slug": "roosevelt", "tier": "standard", "latitude": -34.9600, "longitude": -54.9500},
    {"name": "Laguna del Sauce", "slug": "laguna-del-sauce", "tier": "premium", "latitude": -34.9333, "longitude": -55.1167},
    {"name": "Sauce de Portezuelo", "slug": "sauce-de-portezuelo", "tier": "standard", "latitude": -34.9417, "longitude": -54.9750},
    {"name": "Punta Colorada", "slug": "punta-colorada", "tier": "standard", "latitude": -34.9500, "longitude": -55.0333},
    {"name": "El Placer", "slug": "el-placer", "tier": "standard", "latitude": -34.9333, "longitude": -55.0000},
]
