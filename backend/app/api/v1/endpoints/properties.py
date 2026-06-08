"""
Endpoints de propiedades inmobiliarias.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.deps import get_current_user, get_db, limiter
from app.core.logging import get_logger
from app.models.property import (
    Property,
    PropertyAmenity,
    PropertyImage,
    PropertyStatus,
)
from app.models.user import User
from app.schemas.property import (
    PaginatedResponse,
    PropertyDetail,
    PropertyFilter,
    PropertyListItem,
    PropertyStats,
)

router = APIRouter(prefix="/properties", tags=["properties"])
logger = get_logger("api.properties")


@router.get("/", response_model=PaginatedResponse)
async def list_properties(
    q: Optional[str] = Query(None, description="Búsqueda de texto"),
    property_type: Optional[List[str]] = Query(None),
    operation: Optional[str] = Query(None, pattern="^(venta|alquiler|alquiler_temporal)$"),
    status: Optional[str] = Query("active"),
    price_min: Optional[int] = Query(None, ge=0),
    price_max: Optional[int] = Query(None, ge=0),
    bedrooms_min: Optional[int] = Query(None, ge=0),
    bedrooms_max: Optional[int] = Query(None, ge=0),
    bathrooms_min: Optional[int] = Query(None, ge=0),
    bathrooms_max: Optional[int] = Query(None, ge=0),
    area_min: Optional[int] = Query(None, ge=0),
    area_max: Optional[int] = Query(None, ge=0),
    neighborhood: Optional[List[str]] = Query(None),
    ai_premium: Optional[bool] = Query(None),
    ai_opportunity: Optional[bool] = Query(None),
    sort_by: str = Query("created_at", pattern="^(created_at|price|ai_score|area_total|price_per_m2_usd)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Listar propiedades con filtros avanzados y paginación.

    - **q**: Búsqueda de texto en título y descripción
    - **property_type**: apartamento, casa, terreno, etc.
    - **operation**: venta, alquiler, alquiler_temporal
    - **price_min/price_max**: Rango de precio en USD
    - **ai_premium**: Solo propiedades premium detectadas por IA
    - **ai_opportunity**: Solo oportunidades detectadas por IA
    """
    filters = []

    if status:
        filters.append(Property.status == status)

    if operation:
        filters.append(Property.operation == operation)

    if property_type:
        filters.append(Property.property_type.in_(property_type))

    if price_min is not None:
        filters.append(Property.price_usd >= price_min)

    if price_max is not None:
        filters.append(Property.price_usd <= price_max)

    if bedrooms_min is not None:
        filters.append(Property.bedrooms >= bedrooms_min)

    if bedrooms_max is not None:
        filters.append(Property.bedrooms <= bedrooms_max)

    if bathrooms_min is not None:
        filters.append(Property.bathrooms >= bathrooms_min)

    if bathrooms_max is not None:
        filters.append(Property.bathrooms <= bathrooms_max)

    if area_min is not None:
        filters.append(Property.area_total >= area_min)

    if area_max is not None:
        filters.append(Property.area_total <= area_max)

    if neighborhood:
        filters.append(Property.neighborhood.in_(neighborhood))

    if ai_premium is not None:
        filters.append(Property.ai_premium == ai_premium)

    if ai_opportunity is not None:
        filters.append(Property.ai_opportunity == ai_opportunity)

    # Búsqueda de texto: full-text (tsvector) en Postgres, LIKE en SQLite
    if q:
        from app.db.pgtypes import IS_SQLITE

        if IS_SQLITE:
            like = f"%{q}%"
            filters.append(
                or_(
                    Property.title.ilike(like),
                    Property.description.ilike(like),
                    Property.neighborhood.ilike(like),
                )
            )
        else:
            search_query = func.plainto_tsquery("spanish", q)
            filters.append(
                func.to_tsvector(
                    "spanish",
                    func.coalesce(Property.title, "") + " " + func.coalesce(Property.description, ""),
                ).op("@@")(search_query)
            )

    # Ordenamiento
    sort_col = getattr(Property, sort_by, Property.created_at)
    order_func = desc if sort_order == "desc" else lambda x: x

    # Count total
    count_query = select(func.count(Property.id)).where(and_(*filters))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Fetch propiedades
    offset = (page - 1) * page_size
    query = (
        select(Property)
        .where(and_(*filters))
        .order_by(order_func(sort_col).nullslast() if sort_order == "desc" else sort_col.nullslast())
        .offset(offset)
        .limit(page_size)
        .options(
            selectinload(Property.images),
        )
    )

    result = await db.execute(query)
    properties = result.scalars().all()

    # Convertir a schema
    items = []
    for prop in properties:
        item = PropertyListItem.model_validate(prop)
        # Imagen principal
        main_img = next((img for img in prop.images if img.is_main), None)
        if not main_img and prop.images:
            main_img = prop.images[0]
        item.main_image_url = main_img.url if main_img else None
        items.append(item)

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=PropertyStats)
async def get_stats(
    zone_id: Optional[UUID] = Query(None),
    operation: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Estadísticas del mercado inmobiliario.
    """
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    today = now.replace(hour=0, minute=0, second=0)

    base_filters = [Property.status == "active"]
    if zone_id:
        base_filters.append(Property.zone_id == zone_id)
    if operation:
        base_filters.append(Property.operation == operation)

    # Total propiedades
    total_q = await db.execute(select(func.count(Property.id)))
    total = total_q.scalar() or 0

    active_q = await db.execute(
        select(func.count(Property.id)).where(and_(*base_filters))
    )
    active = active_q.scalar() or 0

    # Nuevas hoy / esta semana
    new_today_q = await db.execute(
        select(func.count(Property.id)).where(
            and_(*base_filters, Property.created_at >= today)
        )
    )
    new_today = new_today_q.scalar() or 0

    new_week_q = await db.execute(
        select(func.count(Property.id)).where(
            and_(*base_filters, Property.created_at >= week_ago)
        )
    )
    new_week = new_week_q.scalar() or 0

    # Precios promedio
    sale_filters = base_filters + [
        Property.operation == "venta",
        Property.price_usd.is_not(None),
    ]
    avg_sale_q = await db.execute(
        select(func.avg(Property.price_usd)).where(and_(*sale_filters))
    )
    avg_sale = avg_sale_q.scalar()

    rent_filters = base_filters + [
        Property.operation == "alquiler",
        Property.price_usd.is_not(None),
    ]
    avg_rent_q = await db.execute(
        select(func.avg(Property.price_usd)).where(and_(*rent_filters))
    )
    avg_rent = avg_rent_q.scalar()

    avg_m2_q = await db.execute(
        select(func.avg(Property.price_per_m2_usd)).where(
            and_(*base_filters, Property.price_per_m2_usd.is_not(None))
        )
    )
    avg_m2 = avg_m2_q.scalar()

    # Por tipo
    type_q = await db.execute(
        select(Property.property_type, func.count(Property.id))
        .where(and_(*base_filters))
        .group_by(Property.property_type)
    )
    by_type = {row[0]: row[1] for row in type_q.all()}

    # Por zona/barrio (top 10)
    zone_q = await db.execute(
        select(Property.neighborhood, func.count(Property.id))
        .where(and_(*base_filters, Property.neighborhood.is_not(None)))
        .group_by(Property.neighborhood)
        .order_by(desc(func.count(Property.id)))
        .limit(10)
    )
    by_zone = {row[0]: row[1] for row in zone_q.all()}

    # Por fuente
    source_q = await db.execute(
        select(Property.source, func.count(Property.id))
        .where(and_(*base_filters))
        .group_by(Property.source)
    )
    by_source = {row[0]: row[1] for row in source_q.all()}

    # Premium y oportunidades
    premium_q = await db.execute(
        select(func.count(Property.id)).where(
            and_(*base_filters, Property.ai_premium == True)
        )
    )
    opportunity_q = await db.execute(
        select(func.count(Property.id)).where(
            and_(*base_filters, Property.ai_opportunity == True)
        )
    )

    return PropertyStats(
        total_properties=total,
        active_properties=active,
        new_today=new_today,
        new_this_week=new_week,
        price_drops_this_week=0,  # TODO: desde price_history
        avg_price_sale_usd=float(avg_sale) if avg_sale else None,
        avg_price_rent_usd=float(avg_rent) if avg_rent else None,
        avg_price_m2_usd=float(avg_m2) if avg_m2 else None,
        median_price_sale_usd=None,  # TODO
        by_type=by_type,
        by_zone=by_zone,
        by_source=by_source,
        premium_count=premium_q.scalar() or 0,
        opportunity_count=opportunity_q.scalar() or 0,
    )


@router.get("/opportunities", response_model=List[PropertyListItem])
async def get_opportunities(
    operation: Optional[str] = Query(None),
    neighborhood: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Propiedades detectadas como oportunidades por IA."""
    filters = [
        Property.status == "active",
        Property.ai_opportunity == True,
    ]
    if operation:
        filters.append(Property.operation == operation)
    if neighborhood:
        filters.append(Property.neighborhood == neighborhood)

    result = await db.execute(
        select(Property)
        .where(and_(*filters))
        .order_by(desc(Property.ai_score))
        .limit(limit)
        .options(selectinload(Property.images))
    )
    properties = result.scalars().all()

    items = []
    for prop in properties:
        item = PropertyListItem.model_validate(prop)
        main_img = next((img for img in prop.images if img.is_main), None)
        item.main_image_url = main_img.url if main_img else None
        items.append(item)

    return items


@router.get("/{property_id}", response_model=PropertyDetail)
async def get_property(
    property_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Obtener detalles completos de una propiedad."""
    result = await db.execute(
        select(Property)
        .where(Property.id == property_id)
        .options(
            selectinload(Property.images),
            selectinload(Property.price_history),
            selectinload(Property.amenities),
        )
    )
    prop = result.scalar_one_or_none()

    if not prop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Propiedad no encontrada",
        )

    detail = PropertyDetail.model_validate(prop)
    detail.amenities = [a.amenity for a in prop.amenities]

    return detail


@router.get("/{property_id}/similar", response_model=List[PropertyListItem])
async def get_similar_properties(
    property_id: UUID,
    limit: int = Query(6, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Propiedades similares a una dada."""
    # Obtener la propiedad base
    result = await db.execute(select(Property).where(Property.id == property_id))
    prop = result.scalar_one_or_none()

    if not prop:
        raise HTTPException(status_code=404, detail="Propiedad no encontrada")

    # Buscar similares por: mismo tipo, operación, barrio y rango de precio
    price_usd = float(prop.price_usd or 0)
    price_min = price_usd * 0.7
    price_max = price_usd * 1.3

    similar_result = await db.execute(
        select(Property)
        .where(
            and_(
                Property.id != property_id,
                Property.status == "active",
                Property.operation == prop.operation,
                Property.property_type == prop.property_type,
                Property.neighborhood == prop.neighborhood,
                Property.price_usd >= price_min,
                Property.price_usd <= price_max,
            )
        )
        .order_by(desc(Property.ai_score))
        .limit(limit)
        .options(selectinload(Property.images))
    )
    similar = similar_result.scalars().all()

    # Si no hay suficientes similares, ampliar búsqueda
    if len(similar) < limit:
        extra_result = await db.execute(
            select(Property)
            .where(
                and_(
                    Property.id != property_id,
                    Property.id.not_in([s.id for s in similar]),
                    Property.status == "active",
                    Property.operation == prop.operation,
                    Property.property_type == prop.property_type,
                    Property.price_usd >= price_min,
                    Property.price_usd <= price_max,
                )
            )
            .order_by(desc(Property.ai_score))
            .limit(limit - len(similar))
            .options(selectinload(Property.images))
        )
        similar = list(similar) + list(extra_result.scalars().all())

    items = []
    for p in similar:
        item = PropertyListItem.model_validate(p)
        main_img = next((img for img in p.images if img.is_main), None)
        item.main_image_url = main_img.url if main_img else None
        items.append(item)

    return items


@router.get("/{property_id}/price-history", response_model=List[dict])
async def get_price_history(
    property_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Historial de precios de una propiedad."""
    from app.models.property import PriceHistory

    result = await db.execute(
        select(PriceHistory)
        .where(PriceHistory.property_id == property_id)
        .order_by(PriceHistory.recorded_at)
    )
    history = result.scalars().all()

    return [
        {
            "price": float(h.price),
            "price_usd": float(h.price_usd) if h.price_usd else None,
            "currency": h.currency,
            "change_pct": h.change_pct,
            "change_type": h.change_type,
            "recorded_at": h.recorded_at.isoformat(),
        }
        for h in history
    ]
