"""Schemas Pydantic para propiedades."""
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class PropertyImageSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    order: int
    is_main: bool


class PriceHistorySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    price: Decimal
    price_usd: Optional[Decimal]
    currency: str
    change_pct: Optional[float]
    change_type: Optional[str]
    recorded_at: datetime


class PropertyListItem(BaseModel):
    """Schema compacto para listados."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: str
    external_id: Optional[str]
    url: str

    property_type: str
    operation: str
    status: str

    title: str
    price: Optional[Decimal]
    price_usd: Optional[Decimal]
    currency: str
    price_per_m2_usd: Optional[Decimal]

    bedrooms: Optional[int]
    bathrooms: Optional[int]
    area_total: Optional[Decimal]

    neighborhood: Optional[str]
    city: str
    latitude: Optional[float]
    longitude: Optional[float]

    # IA
    ai_score: Optional[float]
    ai_premium: bool
    ai_opportunity: bool
    ai_undervalued: bool
    ai_tags: Optional[List[str]]

    # Main image
    main_image_url: Optional[str] = None

    # Timestamps
    created_at: datetime
    first_seen_at: Optional[datetime]
    published_at: Optional[datetime]

    @property
    def price_display(self) -> str:
        if self.price:
            symbol = "$" if self.currency == "USD" else "$U"
            return f"{symbol} {self.price:,.0f}"
        return "Consultar"


class PropertyDetail(PropertyListItem):
    """Schema completo para vista de detalle."""
    description: Optional[str]
    description_ai: Optional[str]
    ai_summary: Optional[str]

    garages: Optional[int]
    area_built: Optional[Decimal]
    floor: Optional[int]
    total_floors: Optional[int]
    year_built: Optional[int]

    address: Optional[str]
    department: str
    country: str

    agency_name: Optional[str]
    contact_phone: Optional[str]
    contact_email: Optional[str]
    contact_whatsapp: Optional[str]

    expenses: Optional[Decimal]
    expenses_currency: Optional[str]

    ai_estimated_value: Optional[Decimal]
    ai_roi_estimate: Optional[float]
    ai_sentiment_score: Optional[float]
    market_avg_price_zone: Optional[Decimal]
    price_vs_market_pct: Optional[float]
    days_on_market: Optional[int]

    images: List[PropertyImageSchema] = []
    price_history: List[PriceHistorySchema] = []
    amenities: List[str] = []

    raw_data: Optional[Dict[str, Any]] = None
    last_scraped_at: Optional[datetime]
    last_seen_at: Optional[datetime]


class PropertyFilter(BaseModel):
    """Filtros para búsqueda de propiedades."""
    # Texto libre
    q: Optional[str] = None

    # Tipo
    property_type: Optional[List[str]] = None
    operation: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = "active"

    # Precio
    price_min: Optional[int] = Field(None, ge=0)
    price_max: Optional[int] = Field(None, ge=0)
    currency: Optional[str] = "USD"

    # Características
    bedrooms_min: Optional[int] = Field(None, ge=0)
    bedrooms_max: Optional[int] = Field(None, ge=0)
    bathrooms_min: Optional[int] = Field(None, ge=0)
    area_min: Optional[int] = Field(None, ge=0)
    area_max: Optional[int] = Field(None, ge=0)

    # Localización
    neighborhood: Optional[List[str]] = None
    zone_id: Optional[UUID] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: Optional[float] = Field(None, ge=0.1, le=100)

    # IA
    ai_premium: Optional[bool] = None
    ai_opportunity: Optional[bool] = None
    ai_score_min: Optional[float] = Field(None, ge=0, le=100)

    # Ordenamiento
    sort_by: str = "created_at"
    sort_order: str = "desc"

    # Paginación
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PropertyStats(BaseModel):
    """Estadísticas del mercado."""
    total_properties: int
    active_properties: int
    new_today: int
    new_this_week: int
    price_drops_this_week: int

    avg_price_sale_usd: Optional[float]
    avg_price_rent_usd: Optional[float]
    avg_price_m2_usd: Optional[float]
    median_price_sale_usd: Optional[float]

    by_type: Dict[str, int] = {}
    by_zone: Dict[str, int] = {}
    by_source: Dict[str, int] = {}
    premium_count: int = 0
    opportunity_count: int = 0


class PaginatedResponse(BaseModel):
    """Respuesta paginada genérica."""
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def create(cls, items: List, total: int, page: int, page_size: int):
        pages = (total + page_size - 1) // page_size
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
