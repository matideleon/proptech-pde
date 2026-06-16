"""Scheduler propio — independiente de Celery beat.

Corre como un ÚNICO proceso (servicio compose `scheduler`) y dispara los
scrapes en-proceso, usando exactamente la misma ruta que los endpoints
`/scraping/trigger` y `/group-posts/trigger`, que está probada y es confiable.

Motivación: el `celery beat` dejó de disparar las tareas programadas en prod
(los runs nunca coincidían con el cron), por lo que no entraban propiedades ni
posts de grupos de forma automática. Este loop asíncrono no depende de beat ni
del worker: llama directamente al `ScrapingRunner` y a `run_group_scraping`.

Al ser un solo contenedor/proceso no hay riesgo de ejecuciones duplicadas
(a diferencia de correrlo dentro de gunicorn, que tiene varios workers).
"""
import asyncio
import logging
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [scheduler] %(levelname)s %(message)s",
)
logger = logging.getLogger("scheduler")

# Portales de propiedades a scrapear.
PROPERTY_SOURCES = ["mercadolibre", "infocasas", "gallito", "facebook"]

# Intervalos en segundos.
PROPERTY_INTERVAL = 4 * 3600   # propiedades: cada 4 h
GROUP_INTERVAL = 2 * 3600      # grupos FB: cada 2 h
AI_SCORE_INTERVAL = 1 * 3600   # scoring IA de propiedades nuevas: cada 1 h
DIGEST_HOUR_UTC = 10           # digest diario Telegram: 10:00 UTC = 07:00 America/Montevideo


async def _scrape_properties() -> None:
    from app.scrapers.runner import ScrapingRunner

    logger.info("▶ scrape propiedades: %s", PROPERTY_SOURCES)
    try:
        res = await ScrapingRunner().run_all(sources=PROPERTY_SOURCES, parallel=False)
        logger.info("✔ scrape propiedades ok: %s", res)
    except Exception:
        logger.exception("✗ scrape propiedades falló")


async def _scrape_groups() -> None:
    from app.scrapers.facebook_groups import run_group_scraping

    logger.info("▶ scrape grupos de Facebook")
    try:
        await run_group_scraping()
        logger.info("✔ scrape grupos de Facebook ok")
    except Exception:
        logger.exception("✗ scrape grupos de Facebook falló")


async def _score_new() -> None:
    # score_new_properties es una tarea Celery síncrona que usa asyncio.run()
    # internamente; la corremos en un thread aparte para no chocar con este loop.
    from app.workers.tasks.ai_tasks import score_new_properties

    logger.info("▶ scoring IA de propiedades nuevas")
    try:
        res = await asyncio.to_thread(score_new_properties)
        logger.info("✔ scoring IA ok: %s", res)
    except Exception:
        logger.exception("✗ scoring IA falló")


async def _daily_digest() -> None:
    # daily_new_digest es una tarea Celery síncrona (usa asyncio.run internamente);
    # la corremos en un thread aparte. Envía a Telegram el resumen de propiedades
    # nuevas de las últimas 24h con link al dashboard.
    from app.workers.tasks.notify import daily_new_digest

    logger.info("▶ digest diario Telegram")
    try:
        res = await asyncio.to_thread(daily_new_digest)
        logger.info("✔ digest diario ok: %s", res)
    except Exception:
        logger.exception("✗ digest diario falló")


async def _daily_at(hour_utc: int, job, *, minute: int = 0) -> None:
    """Ejecuta `job` una vez por día a la hora UTC indicada."""
    from datetime import timedelta

    while True:
        now = datetime.now(timezone.utc)
        nxt = now.replace(hour=hour_utc, minute=minute, second=0, microsecond=0)
        if nxt <= now:
            nxt += timedelta(days=1)
        await asyncio.sleep((nxt - now).total_seconds())
        await job()


async def _every(interval: int, job, *, initial_delay: float = 0.0) -> None:
    """Ejecuta `job` una vez tras `initial_delay` y luego cada `interval` seg.

    El intervalo se mide entre finales de ejecución (drift-safe): descuenta lo
    que tardó el job para no acumular retraso ni solaparse.
    """
    if initial_delay:
        await asyncio.sleep(initial_delay)
    while True:
        start = datetime.now(timezone.utc)
        await job()
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        await asyncio.sleep(max(1.0, interval - elapsed))


async def main() -> None:
    logger.info(
        "Scheduler iniciado · propiedades=%dh grupos=%dh scoring=%dh",
        PROPERTY_INTERVAL // 3600,
        GROUP_INTERVAL // 3600,
        AI_SCORE_INTERVAL // 3600,
    )
    # initial_delay escalonado para no arrancar todo a la vez al boot.
    await asyncio.gather(
        _every(PROPERTY_INTERVAL, _scrape_properties, initial_delay=30),
        _every(GROUP_INTERVAL, _scrape_groups, initial_delay=120),
        _every(AI_SCORE_INTERVAL, _score_new, initial_delay=600),
        _daily_at(DIGEST_HOUR_UTC, _daily_digest),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Scheduler detenido")
