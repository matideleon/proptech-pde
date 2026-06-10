"""
Modelo central de propiedades inmobiliarias.
Incluye PostGIS para geolocalización e historial de precios.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    text,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.db.pgtypes import ARRAY, IS_SQLITE, JSONB, UUID, Geography
from app.models.base import TimestampMixin, UUIDMixin


# ─── ENUMS ────────────────────────────────────────────────────
class OperationType(str, PyEnum):
    VENTA = "venta"
    ALQUILER = "alquiler"
    ALQUILER_TEMPORAL = "alquiler_temporal"


class PropertyType(str, PyEnum):
    APARTAMENTO = "apartamento"
    CASA = "casa"
    CHACRA = "chacra"
    TERRENO = "terreno"
    LOCAL_COMERCIAL = "local_comercial"
    OFICINA = "oficina"
    GARAGE = "garage"
    PENTHOUSE = "penthouse"
    DUPLEX = "duplex"
    CAMPO = "campo"
    HOTEL = "hotel"
    OTRO = "otro"


class Currency(str, PyEnum):
    USD = "USD"
    UYU = "UYU"


class PropertyStatus(str, PyEnum):
    ACTIVE = "active"       # Activa en el portal
    INACTIVE = "inactive"   # Dada de baja
    SOLD = "sold"           # Vendida/alquilada
    DUPLICATE = "duplicate" # Duplicado detectado


class ScrapingSource(str, PyEnum):
    MERCADOLIBRE = "mercadolibre"
    INFOCASAS = "infocasas"
    GALLITO = "gallito"
    FACEBOOK = "facebook"
    INMOBILIARIA_LOCAL = "inmobiliaria_local"
    MANUAL = "manual"


# ─── PROPERTY MODEL ───────────────────────────────────────────
class Property(UUIDMixin, TimestampMixin, Base):
    """
    Modelo principal de propiedades.

    Representa una propiedad inmobiliaria scrapeada o ingresada
    manualmente. Incluye geolocalización con PostGIS.
    """
    __tablename__ = "properties"

    # Índices portables (corren en cualquier dialecto)
    _base_indexes = (
        UniqueConstraint("source", "external_id", name="uq_property_source_external"),
        Index("ix_property_type_operation", "property_type", "operation"),
        Index("ix_property_price_currency", "price", "currency"),
        Index("ix_property_zone_id", "zone_id"),
        Index("ix_property_status", "status"),
        Index("ix_property_created_at", "created_at"),
    )
    # Índices específicos de Postgres (GIST geográfico + GIN full-text en español)
    _pg_indexes = (
        Index("ix_property_location", "location", postgresql_using="gist"),
        Index("ix_property_fts", text("to_tsvector('spanish', coalesce(title, '') || ' ' || coalesce(description, ''))"), postgresql_using="gin"),
    )
    __table_args__ = _base_indexes if IS_SQLITE else (_base_indexes + _pg_indexes)

    # ─── IDENTIFICACIÓN ──────────────────────────────────────
    source: Mapped[str] = mapped_column(
        Enum(ScrapingSource), nullable=False, index=True
    )
    external_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), index=True)  # SHA256 de URL

    # ─── CLASIFICACIÓN ───────────────────────────────────────
    property_type: Mapped[str] = mapped_column(
        Enum(PropertyType), nullable=False, default=PropertyType.APARTAMENTO
    )
    operation: Mapped[str] = mapped_column(
        Enum(OperationType), nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum(PropertyStatus), nullable=False, default=PropertyStatus.ACTIVE
    )

    # ─── DESCRIPCIÓN ─────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    description_ai: Mapped[Optional[str]] = mapped_column(Text)  # Generado por IA

    # ─── PRECIO ──────────────────────────────────────────────
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), index=True)
    price_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), index=True)
    currency: Mapped[str] = mapped_column(
        Enum(Currency), nullable=False, default=Currency.USD
    )
    price_per_m2: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    price_per_m2_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    expenses: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    expenses_currency: Mapped[Optional[str]] = mapped_column(String(3))

    # ─── CARACTERÍSTICAS ─────────────────────────────────────
    bedrooms: Mapped[Optional[int]] = mapped_column(Integer)
    bathrooms: Mapped[Optional[int]] = mapped_column(Integer)
    garages: Mapped[Optional[int]] = mapped_column(Integer)
    area_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))  # m²
    area_built: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))  # m² construidos
    floor: Mapped[Optional[int]] = mapped_column(Integer)
    total_floors: Mapped[Optional[int]] = mapped_column(Integer)
    year_built: Mapped[Optional[int]] = mapped_column(Integer)

    # ─── LOCALIZACIÓN ────────────────────────────────────────
    country: Mapped[str] = mapped_column(String(50), default="Uruguay")
    department: Mapped[str] = mapped_column(String(100), default="Maldonado")
    city: Mapped[str] = mapped_column(String(100), default="Punta del Este")
    neighborhood: Mapped[Optional[str]] = mapped_column(String(200), index=True)
    address: Mapped[Optional[str]] = mapped_column(String(500))
    address_normalized: Mapped[Optional[str]] = mapped_column(String(500))
    latitude: Mapped[Optional[float]] = mapped_column()
    longitude: Mapped[Optional[float]] = mapped_column()
    location: Mapped[Optional[object]] = mapped_column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=True,
    )
    zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("zones.id"), nullable=True
    )

    # ─── CONTACTO / INMOBILIARIA ─────────────────────────────
    agency_name: Mapped[Optional[str]] = mapped_column(String(300))
    agency_id: Mapped[Optional[str]] = mapped_column(String(100))
    contact_name: Mapped[Optional[str]] = mapped_column(String(200))
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50))
    contact_phone_normalized: Mapped[Optional[str]] = mapped_column(String(50))
    contact_email: Mapped[Optional[str]] = mapped_column(String(200))
    contact_whatsapp: Mapped[Optional[str]] = mapped_column(String(50))

    # ─── IA SCORING ──────────────────────────────────────────
    ai_score: Mapped[Optional[float]] = mapped_column()           # 0-100 calidad
    ai_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_opportunity: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_undervalued: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_estimated_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    ai_roi_estimate: Mapped[Optional[float]] = mapped_column()    # % anual estimado
    ai_sentiment_score: Mapped[Optional[float]] = mapped_column() # -1 a 1
    ai_tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))
    ai_summary: Mapped[Optional[str]] = mapped_column(Text)
    ai_last_analyzed: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # ─── MÉTRICAS DE MERCADO ─────────────────────────────────
    market_avg_price_zone: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    price_vs_market_pct: Mapped[Optional[float]] = mapped_column()  # % vs promedio zona
    days_on_market: Mapped[Optional[int]] = mapped_column(Integer)

    # ─── SCRAPING METADATA ───────────────────────────────────
    first_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    views_count: Mapped[int] = mapped_column(Integer, default=0)
    favorites_count: Mapped[Optional[int]] = mapped_column(Integer)

    # ─── EXTRA DATA ──────────────────────────────────────────
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    amenities_raw: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))
    features: Mapped[Optional[dict]] = mapped_column(JSONB)

    # ─── DEDUP ───────────────────────────────────────────────
    fingerprint: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    duplicate_of_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id"), nullable=True
    )

    # ─── RELACIONES ──────────────────────────────────────────
    images: Mapped[List["PropertyImage"]] = relationship(
        "PropertyImage", back_populates="property", cascade="all, delete-orphan"
    )
    price_history: Mapped[List["PriceHistory"]] = relationship(
        "PriceHistory", back_populates="property", cascade="all, delete-orphan"
    )
    amenities: Mapped[List["PropertyAmenity"]] = relationship(
        "PropertyAmenity", back_populates="property", cascade="all, delete-orphan"
    )
    zone: Mapped[Optional["Zone"]] = relationship("Zone", back_populates="properties")

    def __repr__(self) -> str:
        return f"<Property {self.id} | {self.title[:50]} | {self.price} {self.currency}>"

    @property
    def price_display(self) -> str:
        """Precio formateado para mostrar."""
        if self.price:
            return f"{'$' if self.currency == 'USD' else '$U'} {self.price:,.0f}"
        return "Consultar"

    @property
    def is_opportunity(self) -> bool:
        """¿Es una oportunidad según IA?"""
        return bool(self.ai_opportunity or self.ai_undervalued)


# ─── PROPERTY IMAGE ───────────────────────────────────────────
class PropertyImage(UUIDMixin, TimestampMixin, Base):
    """Imágenes de propiedades."""
    __tablename__ = "property_images"

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    url_local: Mapped[Optional[str]] = mapped_column(Text)  # Cached localmente
    order: Mapped[int] = mapped_column(Integer, default=0)
    is_main: Mapped[bool] = mapped_column(Boolean, default=False)
    width: Mapped[Optional[int]] = mapped_column(Integer)
    height: Mapped[Optional[int]] = mapped_column(Integer)
    alt_text: Mapped[Optional[str]] = mapped_column(String(500))

    property: Mapped["Property"] = relationship("Property", back_populates="images")


# ─── PRICE HISTORY ────────────────────────────────────────────
class PriceHistory(UUIDMixin, Base):
    """
    Historial de precios — un registro por cada cambio detectado.
    Permite análisis de tendencias y detección de oportunidades.
    """
    __tablename__ = "price_history"
    __table_args__ = (
        Index("ix_price_history_property", "property_id"),
        Index("ix_price_history_recorded_at", "recorded_at"),
    )

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    price_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    change_pct: Mapped[Optional[float]] = mapped_column()  # % de cambio vs anterior
    change_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    change_type: Mapped[Optional[str]] = mapped_column(String(20))  # increase, decrease, stable
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    source: Mapped[Optional[str]] = mapped_column(String(50))

    property: Mapped["Property"] = relationship("Property", back_populates="price_history")


# ─── PROPERTY AMENITY ─────────────────────────────────────────
class PropertyAmenity(UUIDMixin, Base):
    """Amenidades normalizadas de propiedades."""
    __tablename__ = "property_amenities"

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    amenity: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    amenity_normalized: Mapped[str] = mapped_column(String(200), index=True)
    category: Mapped[Optional[str]] = mapped_column(String(100))

    property: Mapped["Property"] = relationship("Property", back_populates="amenities")
