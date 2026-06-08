"""
Runner central de scrapers.
Coordina la ejecución de todos los scrapers y persiste datos en DB.
"""
import asyncio
import hashlib
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.database import get_db_context
from app.models.property import (
    Currency,
    OperationType,
    Property,
    PropertyAmenity,
    PropertyImage,
    PropertyStatus,
    PropertyType,
    PriceHistory,
    ScrapingSource,
)
from app.models.scraping import ScrapingRun, ScrapingStatus
from app.scrapers.base import BaseScraper, ScrapedProperty, ScraperStats
from app.scrapers.config import TARGET
from app.db.pgtypes import IS_SQLITE
from app.scrapers.gallito import GallitoScraper
from app.scrapers.infocasas import InfoCasasScraper
from app.scrapers.facebook import FacebookMarketplaceScraper
from app.scrapers.mercadolibre import MercadoLibreScraper, MercadoLibreWebScraper
from app.scrapers.normalizer import normalizer
from geoalchemy2.elements import WKTElement

logger = get_logger("scraper.runner")


# Registro de scrapers disponibles.
# MercadoLibre y Facebook usan Googlebot UA (sus APIs/web están cerradas a
# clientes anónimos, pero sirven datos al crawler de Google).
SCRAPERS: dict[str, Type[BaseScraper]] = {
    "mercadolibre": MercadoLibreWebScraper,
    "infocasas": InfoCasasScraper,
    "facebook": FacebookMarketplaceScraper,
    "gallito": GallitoScraper,
}


class ScrapingRunner:
    """
    Orquestador central del sistema de scraping.

    Responsable de:
    1. Ejecutar scrapers en orden/paralelo
    2. Normalizar datos
    3. Persistir en DB (upsert)
    4. Detectar cambios de precio
    5. Marcar propiedades eliminadas
    6. Registrar métricas de cada ejecución
    """

    def __init__(self):
        self.logger = get_logger("runner")

    async def run_scraper(
        self,
        scraper_class: Type[BaseScraper],
        db: AsyncSession,
        scraping_run: ScrapingRun,
    ) -> ScraperStats:
        """Ejecutar un scraper y persistir resultados."""
        scraper = scraper_class()
        source = scraper.SOURCE_NAME

        logger.info(f"▶ Ejecutando scraper: {source}")

        seen_external_ids = set()

        async for raw_prop in scraper.scrape():
            try:
                # Normalizar datos
                prop = normalizer.normalize(raw_prop)

                # Foco de negocio: priorizar alquileres en rango objetivo.
                # Los alquileres fuera de rango se descartan; las ventas se
                # conservan solo como contexto de mercado.
                if prop.operation == "alquiler":
                    price_for_filter = prop.price_usd or prop.price
                    cur = "USD" if prop.price_usd else prop.currency
                    if not TARGET.price_in_rent_range(price_for_filter, cur):
                        scraping_run.properties_skipped = (
                            getattr(scraping_run, "properties_skipped", 0) + 1
                        )
                        continue

                # Persistir/actualizar en DB
                await self._upsert_property(prop, db, scraping_run)

                seen_external_ids.add(prop.external_id or prop.url)
                scraping_run.properties_found += 1

                # Commit periódico
                if scraping_run.properties_found % 50 == 0:
                    await db.commit()
                    logger.info(
                        f"📊 Progreso {source}",
                        found=scraping_run.properties_found,
                        new=scraping_run.properties_new,
                        updated=scraping_run.properties_updated,
                    )

            except Exception as e:
                logger.error(
                    f"Error procesando propiedad",
                    source=source,
                    url=getattr(raw_prop, 'url', 'unknown'),
                    error=str(e),
                )
                scraping_run.errors_count += 1

        # Marcar propiedades no vistas como inactivas
        # (solo si scrapeamos todo el portal)
        await self._mark_removed_properties(source, seen_external_ids, db)

        await db.commit()
        await scraper.close()  # cerrar sesión HTTP del scraper
        return scraper.stats

    async def _upsert_property(
        self,
        prop: ScrapedProperty,
        db: AsyncSession,
        run: ScrapingRun,
    ) -> Optional[Property]:
        """
        Insertar o actualizar propiedad en DB.
        Detecta cambios de precio automáticamente.
        """
        # Buscar propiedad existente por source + external_id
        existing = None

        if prop.external_id:
            result = await db.execute(
                select(Property).where(
                    Property.source == prop.source,
                    Property.external_id == prop.external_id,
                )
            )
            existing = result.scalar_one_or_none()

        if not existing:
            # Buscar por URL hash
            url_hash = hashlib.sha256(prop.url.encode()).hexdigest()
            result = await db.execute(
                select(Property).where(Property.url_hash == url_hash)
            )
            existing = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)

        if existing:
            # ─── ACTUALIZAR EXISTENTE ──────────────────────
            run.properties_updated += 1

            # Detectar cambio de precio
            old_price = float(existing.price or 0)
            new_price = prop.price or 0

            if old_price > 0 and new_price > 0 and abs(new_price - old_price) > 0.01:
                change_type, change_pct = normalizer.detect_price_change(
                    new_price, old_price, prop.currency
                )
                if change_type != "stable":
                    # Registrar en historial
                    price_record = PriceHistory(
                        property_id=existing.id,
                        price=Decimal(str(new_price)),
                        price_usd=Decimal(str(prop.price_usd or new_price)),
                        currency=prop.currency,
                        change_pct=change_pct,
                        change_amount=Decimal(str(abs(new_price - old_price))),
                        change_type=change_type,
                        source=prop.source,
                    )
                    db.add(price_record)
                    run.price_changes += 1

                    logger.info(
                        f"💰 Cambio de precio detectado",
                        property_id=str(existing.id),
                        old=old_price,
                        new=new_price,
                        pct=change_pct,
                        type=change_type,
                    )

            # Actualizar campos
            existing.price = Decimal(str(new_price)) if new_price else existing.price
            existing.currency = prop.currency
            existing.last_seen_at = now
            existing.last_scraped_at = now
            existing.status = PropertyStatus.ACTIVE

            if prop.description and len(prop.description) > len(existing.description or ""):
                existing.description = prop.description
            if prop.neighborhood and not existing.neighborhood:
                existing.neighborhood = prop.neighborhood
            if prop.latitude and not existing.latitude:
                existing.latitude = prop.latitude
                existing.longitude = prop.longitude

            return existing

        else:
            # ─── INSERTAR NUEVA ───────────────────────────
            run.properties_new += 1

            # Calcular fingerprint para deduplicación
            fp = normalizer.compute_fingerprint(prop)
            url_hash = hashlib.sha256(prop.url.encode()).hexdigest()

            # Crear location point para PostGIS (solo en Postgres; en SQLite
            # la columna Geography es Text y no admite WKTElement).
            location = None
            if prop.latitude and prop.longitude and not IS_SQLITE:
                location = WKTElement(
                    f"POINT({prop.longitude} {prop.latitude})",
                    srid=4326,
                )

            db_prop = Property(
                source=prop.source,
                external_id=prop.external_id,
                url=prop.url,
                url_hash=url_hash,
                property_type=prop.property_type,
                operation=prop.operation,
                status=PropertyStatus.ACTIVE,
                title=prop.title,
                description=prop.description,
                price=Decimal(str(prop.price)) if prop.price else None,
                price_usd=Decimal(str(prop.price_usd)) if prop.price_usd else None,
                currency=prop.currency,
                price_per_m2=Decimal(str(prop.price_per_m2_usd)) if prop.price_per_m2_usd else None,
                price_per_m2_usd=Decimal(str(prop.price_per_m2_usd)) if prop.price_per_m2_usd else None,
                bedrooms=prop.bedrooms,
                bathrooms=prop.bathrooms,
                garages=prop.garages,
                area_total=Decimal(str(prop.area_total)) if prop.area_total else None,
                area_built=Decimal(str(prop.area_built)) if prop.area_built else None,
                floor=prop.floor,
                year_built=prop.year_built,
                country=prop.country,
                department=prop.department,
                city=prop.city,
                neighborhood=prop.neighborhood,
                address=prop.address,
                latitude=prop.latitude,
                longitude=prop.longitude,
                location=location,
                agency_name=prop.agency_name,
                agency_id=prop.agency_id,
                contact_name=prop.contact_name,
                contact_phone=prop.contact_phone,
                contact_phone_normalized=getattr(prop, 'contact_phone_normalized', None),
                contact_email=prop.contact_email,
                contact_whatsapp=prop.contact_whatsapp,
                amenities_raw=prop.amenities,
                first_seen_at=now,
                last_seen_at=now,
                last_scraped_at=now,
                published_at=prop.published_at,
                fingerprint=fp,
                raw_data=prop.raw_data,
            )

            db.add(db_prop)
            await db.flush()  # Para obtener el ID

            # Agregar imágenes
            for i, img_url in enumerate(prop.images[:20]):
                if img_url:
                    db.add(PropertyImage(
                        property_id=db_prop.id,
                        url=img_url,
                        order=i,
                        is_main=(i == 0),
                    ))

            # Agregar amenidades normalizadas
            for amenity in prop.amenities[:50]:
                db.add(PropertyAmenity(
                    property_id=db_prop.id,
                    amenity=amenity,
                    amenity_normalized=amenity.lower().replace(' ', '_'),
                ))

            # Registro inicial de precio en historial
            if prop.price:
                db.add(PriceHistory(
                    property_id=db_prop.id,
                    price=Decimal(str(prop.price)),
                    price_usd=Decimal(str(prop.price_usd or prop.price)),
                    currency=prop.currency,
                    change_type="initial",
                    source=prop.source,
                ))

            logger.debug(
                f"✅ Nueva propiedad",
                source=prop.source,
                title=prop.title[:50],
                price=prop.price,
                currency=prop.currency,
            )

            return db_prop

    async def _mark_removed_properties(
        self,
        source: str,
        seen_ids: set,
        db: AsyncSession,
    ) -> int:
        """
        Marcar propiedades que ya no aparecen en el portal como inactivas.
        Solo aplica si se scrapeó el portal completo.
        """
        if len(seen_ids) < 10:
            # Muy pocas propiedades vistas — probablemente scraping incompleto
            return 0

        # Buscar propiedades activas de esta fuente
        result = await db.execute(
            select(Property).where(
                Property.source == source,
                Property.status == PropertyStatus.ACTIVE,
                Property.external_id.is_not(None),
            )
        )
        all_active = result.scalars().all()

        marked = 0
        for prop in all_active:
            if prop.external_id not in seen_ids and prop.url not in seen_ids:
                prop.status = PropertyStatus.INACTIVE
                marked += 1

        if marked > 0:
            logger.info(f"🔴 {marked} propiedades marcadas como inactivas", source=source)

        return marked

    async def run_all(
        self,
        sources: Optional[List[str]] = None,
        parallel: bool = False,
    ) -> dict:
        """
        Ejecutar todos los scrapers configurados.

        Args:
            sources: Lista de fuentes a ejecutar. Si None, ejecuta todas.
            parallel: Si True, ejecuta en paralelo (más rápido pero más carga)
        """
        sources_to_run = sources or list(SCRAPERS.keys())
        results = {}

        async with get_db_context() as db:
            if parallel:
                # Ejecutar en paralelo
                tasks = []
                for source_name in sources_to_run:
                    if source_name in SCRAPERS:
                        run = ScrapingRun(
                            source=source_name,
                            status=ScrapingStatus.RUNNING,
                        )
                        db.add(run)
                        await db.flush()
                        tasks.append(
                            self.run_scraper(SCRAPERS[source_name], db, run)
                        )
                await asyncio.gather(*tasks, return_exceptions=True)
            else:
                # Ejecutar secuencialmente
                for source_name in sources_to_run:
                    if source_name not in SCRAPERS:
                        logger.warning(f"Scraper desconocido: {source_name}")
                        continue

                    run = ScrapingRun(
                        source=source_name,
                        status=ScrapingStatus.RUNNING,
                    )
                    db.add(run)
                    await db.flush()

                    try:
                        stats = await self.run_scraper(SCRAPERS[source_name], db, run)
                        run.status = ScrapingStatus.COMPLETED
                        run.finished_at = datetime.now(timezone.utc)
                        results[source_name] = {
                            "status": "completed",
                            "found": run.properties_found,
                            "new": run.properties_new,
                            "updated": run.properties_updated,
                            "price_changes": run.price_changes,
                        }
                    except Exception as e:
                        run.status = ScrapingStatus.FAILED
                        run.error_message = str(e)
                        run.finished_at = datetime.now(timezone.utc)
                        results[source_name] = {"status": "failed", "error": str(e)}
                        logger.error(f"Scraper {source_name} falló", error=str(e))

                    await db.commit()

        logger.info("🏁 Todos los scrapers completados", results=results)
        return results


# CLI entrypoint
if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="PropTech PDE Scraper Runner")
    parser.add_argument("--source", nargs="+", help="Fuentes a scrapear")
    parser.add_argument("--all", action="store_true", help="Scrapear todas las fuentes")
    parser.add_argument("--parallel", action="store_true", help="Ejecutar en paralelo")
    args = parser.parse_args()

    runner = ScrapingRunner()
    sources = args.source if not args.all else None

    asyncio.run(runner.run_all(sources=sources, parallel=args.parallel))
