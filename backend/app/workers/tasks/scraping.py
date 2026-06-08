"""Tareas Celery para scraping."""
import asyncio
from typing import List, Optional

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    name="app.workers.tasks.scraping.scrape_source",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutos
    autoretry_for=(Exception,),
)
def scrape_source(self, source: str) -> dict:
    """
    Tarea Celery para scrapear una fuente específica.
    Se ejecuta según el schedule de beat.
    """
    logger.info(f"Iniciando scraping: {source}")

    from app.scrapers.runner import ScrapingRunner
    runner = ScrapingRunner()

    # Ejecutar en loop asyncio (Celery corre en context síncrono)
    result = asyncio.run(runner.run_all(sources=[source]))

    logger.info(f"Scraping completado: {source}", extra={"result": result})
    return result


@shared_task(name="app.workers.tasks.scraping.scrape_all")
def scrape_all(parallel: bool = False) -> dict:
    """Scrapear todas las fuentes."""
    from app.scrapers.runner import ScrapingRunner
    runner = ScrapingRunner()
    return asyncio.run(runner.run_all(parallel=parallel))


@shared_task(name="app.workers.tasks.scraping.detect_removed_properties")
def detect_removed_properties() -> dict:
    """
    Detectar propiedades que fueron eliminadas de los portales.
    Compara el estado actual con el último scraping.
    """
    logger.info("Detectando propiedades eliminadas...")

    async def _run():
        from sqlalchemy import select, and_, func
        from datetime import datetime, timedelta, timezone
        from app.db.database import get_db_context
        from app.models.property import Property, PropertyStatus

        now = datetime.now(timezone.utc)
        threshold = now - timedelta(days=3)  # Sin ver en 3 días = posible eliminada

        async with get_db_context() as db:
            # Propiedades activas que no se han visto en 3+ días
            result = await db.execute(
                select(Property).where(
                    and_(
                        Property.status == PropertyStatus.ACTIVE,
                        Property.last_seen_at < threshold,
                        Property.source != "manual",
                    )
                ).limit(1000)
            )
            stale = result.scalars().all()

            marked = 0
            for prop in stale:
                prop.status = PropertyStatus.INACTIVE
                marked += 1

            await db.commit()
            logger.info(f"Marcadas {marked} propiedades como inactivas")
            return {"marked_inactive": marked}

    return asyncio.run(_run())
