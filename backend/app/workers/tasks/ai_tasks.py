"""Tareas Celery para análisis de IA."""
import asyncio
from celery.utils.log import get_task_logger
from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(name="app.workers.tasks.ai_tasks.score_new_properties")
def score_new_properties(limit: int = 50) -> dict:
    """Puntuar propiedades nuevas que no tienen score de IA."""

    async def _run():
        from sqlalchemy import select, and_
        from app.db.database import get_db_context
        from app.models.property import Property
        from app.ai.engine import ai_engine
        from datetime import datetime, timezone

        async with get_db_context() as db:
            # Propiedades sin score
            result = await db.execute(
                select(Property)
                .where(
                    and_(
                        Property.ai_score.is_(None),
                        Property.status == "active",
                    )
                )
                .limit(limit)
            )
            properties = result.scalars().all()

            if not properties:
                logger.info("No hay propiedades pendientes de scoring")
                return {"scored": 0}

            logger.info(f"Scoring {len(properties)} propiedades...")
            scored = 0

            for prop in properties:
                try:
                    prop_data = {
                        "id": str(prop.id),
                        "property_type": prop.property_type,
                        "operation": prop.operation,
                        "title": prop.title,
                        "description": prop.description,
                        "price": float(prop.price or 0),
                        "price_usd": float(prop.price_usd or 0),
                        "currency": prop.currency,
                        "area_total": float(prop.area_total or 0),
                        "bedrooms": prop.bedrooms,
                        "bathrooms": prop.bathrooms,
                        "neighborhood": prop.neighborhood,
                        "year_built": prop.year_built,
                        "agency_name": prop.agency_name,
                        "amenities": prop.amenities_raw or [],
                    }

                    score_data = await ai_engine.score_property(prop_data)

                    # Actualizar propiedad
                    prop.ai_score = score_data.get("quality_score")
                    prop.ai_premium = score_data.get("is_premium", False)
                    prop.ai_opportunity = score_data.get("is_opportunity", False)
                    prop.ai_undervalued = score_data.get("is_undervalued", False)
                    prop.ai_tags = score_data.get("tags", [])
                    prop.ai_summary = score_data.get("summary")

                    if score_data.get("estimated_market_value_usd"):
                        from decimal import Decimal
                        prop.ai_estimated_value = Decimal(str(score_data["estimated_market_value_usd"]))

                    if score_data.get("roi_estimate_pct"):
                        prop.ai_roi_estimate = score_data["roi_estimate_pct"]

                    prop.ai_last_analyzed = datetime.now(timezone.utc)
                    scored += 1

                except Exception as e:
                    logger.error(f"Error scoring propiedad {prop.id}: {e}")

            await db.commit()
            logger.info(f"✅ {scored} propiedades puntuadas")
            return {"scored": scored}

    return asyncio.run(_run())


@celery_app.task(name="app.workers.tasks.ai_tasks.update_zone_statistics")
def update_zone_statistics() -> dict:
    """Actualizar estadísticas de precios por zona."""

    async def _run():
        from sqlalchemy import select, func, and_
        from app.db.database import get_db_context
        from app.models.zone import Zone
        from app.models.property import Property
        from decimal import Decimal

        async with get_db_context() as db:
            # Obtener todas las zonas activas
            zones_result = await db.execute(select(Zone).where(Zone.is_active == True))
            zones = zones_result.scalars().all()

            updated = 0
            for zone in zones:
                # Calcular estadísticas de propiedades en esta zona
                stats = await db.execute(
                    select(
                        func.avg(Property.price_usd).label("avg_price_sale"),
                        func.avg(Property.price_per_m2_usd).label("avg_m2"),
                        func.count(Property.id).label("count"),
                    ).where(
                        and_(
                            Property.zone_id == zone.id,
                            Property.status == "active",
                            Property.operation == "venta",
                            Property.price_usd.is_not(None),
                        )
                    )
                )
                row = stats.one()

                if row.count > 0:
                    zone.avg_price_sale_usd = Decimal(str(row.avg_price_sale or 0))
                    zone.avg_price_m2_usd = Decimal(str(row.avg_m2 or 0))
                    zone.active_properties_count = row.count
                    updated += 1

            await db.commit()
            return {"zones_updated": updated}

    return asyncio.run(_run())


@celery_app.task(name="app.workers.tasks.ai_tasks.generate_descriptions")
def generate_ai_descriptions(property_ids: list) -> dict:
    """Generar descripciones IA para propiedades específicas."""

    async def _run():
        from sqlalchemy import select
        from app.db.database import get_db_context
        from app.models.property import Property
        from app.ai.engine import ai_engine
        import uuid

        async with get_db_context() as db:
            ids = [uuid.UUID(pid) if isinstance(pid, str) else pid for pid in property_ids]
            result = await db.execute(select(Property).where(Property.id.in_(ids)))
            properties = result.scalars().all()

            generated = 0
            for prop in properties:
                try:
                    prop_data = {
                        "property_type": prop.property_type,
                        "title": prop.title,
                        "price_usd": float(prop.price_usd or 0),
                        "area_total": float(prop.area_total or 0),
                        "bedrooms": prop.bedrooms,
                        "bathrooms": prop.bathrooms,
                        "neighborhood": prop.neighborhood,
                        "amenities": prop.amenities_raw or [],
                        "description": prop.description,
                        "year_built": prop.year_built,
                    }

                    description = await ai_engine.generate_commercial_description(
                        prop_data, tone="professional"
                    )
                    if description:
                        prop.description_ai = description
                        generated += 1

                except Exception as e:
                    logger.error(f"Error generando descripción: {e}")

            await db.commit()
            return {"generated": generated}

    return asyncio.run(_run())
