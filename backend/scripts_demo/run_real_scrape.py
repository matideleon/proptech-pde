"""
Ejecuta el scraper REAL de InfoCasas y persiste en la base local.

Trae propiedades reales (con fotos y contacto) del portal y las guarda
pasando por el pipeline de normalización + post-filtro de alquiler.
"""
import asyncio

from app.db.database import get_db_context, init_db
from app.models.scraping import ScrapingRun, ScrapingStatus
from app.scrapers.infocasas import InfoCasasScraper
from app.scrapers.runner import ScrapingRunner


async def main() -> None:
    await init_db()
    runner = ScrapingRunner()

    async with get_db_context() as db:
        run = ScrapingRun(
            source="infocasas",
            status=ScrapingStatus.RUNNING,
        )
        db.add(run)
        await db.flush()

        stats = await runner.run_scraper(InfoCasasScraper, db, run)

        run.status = ScrapingStatus.COMPLETED
        await db.commit()

        print("\n" + "=" * 56)
        print("  SCRAPING REAL INFOCASAS — COMPLETADO")
        print("=" * 56)
        print(f"  Encontradas : {run.properties_found}")
        print(f"  Nuevas      : {run.properties_new}")
        print(f"  Actualizadas: {run.properties_updated}")
        print(f"  Descartadas (fuera de rango): {getattr(run, 'properties_skipped', 0)}")
        print(f"  Errores     : {run.errors_count}")
        print("=" * 56)


if __name__ == "__main__":
    asyncio.run(main())
