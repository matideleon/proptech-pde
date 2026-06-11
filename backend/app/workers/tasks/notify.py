"""Tareas Celery de notificación: digest diario de nuevas propiedades."""
import asyncio
from collections import Counter
from datetime import datetime, timedelta, timezone

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import and_, select

logger = get_task_logger(__name__)


async def _collect_new(hours: int):
    """Devuelve (count, top_zones, price_min, price_max) de propiedades nuevas."""
    from app.db.database import get_db_context
    from app.models.property import Property

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    async with get_db_context() as db:
        result = await db.execute(
            select(
                Property.neighborhood,
                Property.city,
                Property.price_usd,
            ).where(
                and_(
                    Property.created_at >= cutoff,
                    Property.status == "active",
                )
            )
        )
        rows = result.all()

    zones = Counter()
    prices = []
    for neighborhood, city, price_usd in rows:
        zones[neighborhood or city or "—"] += 1
        if price_usd is not None:
            try:
                prices.append(float(price_usd))
            except (TypeError, ValueError):
                pass

    top_zones = zones.most_common(4)
    pmin = min(prices) if prices else None
    pmax = max(prices) if prices else None
    return len(rows), top_zones, pmin, pmax


def _build_message(count, top_zones, pmin, pmax, hours, link):
    if count == 0:
        return (
            "🌙 *PropTech PDE — Punta del Este*\n\n"
            f"No hubo propiedades nuevas en las últimas {hours} h.\n"
            f"Dashboard: {link}"
        )
    zonas = "\n".join(f"  • {z}: {n}" for z, n in top_zones) if top_zones else ""
    precios = ""
    if pmin is not None and pmax is not None:
        precios = f"💰 Rango: USD {pmin:,.0f} – USD {pmax:,.0f}\n".replace(",", ".")
    msg = (
        "🏠 *PropTech PDE — Nuevas propiedades*\n"
        f"📍 Punta del Este · últimas {hours} h\n\n"
        f"*{count} propiedades nuevas* detectadas hoy.\n"
        f"{precios}"
    )
    if zonas:
        msg += "🗺️ Zonas con más altas:\n" + zonas + "\n"
    msg += f"\n👉 Ver dashboard:\n{link}"
    return msg


@shared_task(
    name="app.workers.tasks.notify.daily_new_digest",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
)
def daily_new_digest(self) -> dict:
    """
    Digest diario (pensado para las 7:00 America/Montevideo): cuenta las
    propiedades nuevas de las últimas DIGEST_WINDOW_HOURS y envía un WhatsApp
    con el resumen y el link al dashboard público `/nuevas`.
    """
    from app.core.config import settings
    from app.notifications.whatsapp import WhatsAppNotifier

    hours = settings.DIGEST_WINDOW_HOURS
    link = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/nuevas"

    count, top_zones, pmin, pmax = asyncio.run(_collect_new(hours))
    message = _build_message(count, top_zones, pmin, pmax, hours, link)

    to = settings.WHATSAPP_ALERT_TO
    if not to:
        logger.warning(
            "WHATSAPP_ALERT_TO no configurado — no se envía. "
            "Mensaje que se habría enviado:\n%s", message
        )
        return {"sent": False, "reason": "no_recipient", "count": count}

    notifier = WhatsAppNotifier()
    ok = asyncio.run(notifier.send_text(to, message))
    logger.info("Digest diario WhatsApp enviado=%s (count=%s)", ok, count)
    return {"sent": ok, "count": count, "link": link}
