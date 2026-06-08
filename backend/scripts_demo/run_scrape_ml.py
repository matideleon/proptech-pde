"""Ejecuta el scraper web REAL de MercadoLibre y persiste en la base."""
import asyncio

from app.db.database import get_db_context, init_db
from app.models.scraping import ScrapingRun, ScrapingStatus
from app.scrapers.mercadolibre import MercadoLibreWebScraper
from app.scrapers.runner import ScrapingRunner


async def main() -> None:
    await init_db()
    runner = ScrapingRunner()
    async with get_db_context() as db:
        run = ScrapingRun(source="mercadolibre", status=ScrapingStatus.RUNNING)
        db.add(run)
        await db.flush()
        await runner.run_scraper(MercadoLibreWebScraper, db, run)
        run.status = ScrapingStatus.COMPLETED
        await db.commit()
        print("\n" + "=" * 56)
        print("  SCRAPING REAL MERCADOLIBRE — COMPLETADO")
        print("=" * 56)
        print(f"  Encontradas : {run.properties_found}")
        print(f"  Nuevas      : {run.properties_new}")
        print(f"  Actualizadas: {run.properties_updated}")
        print(f"  Descartadas (fuera de rango): {getattr(run, 'properties_skipped', 0)}")
        print(f"  Errores     : {run.errors_count}")
        print("=" * 56)


if __name__ == "__main__":
    asyncio.run(main())
