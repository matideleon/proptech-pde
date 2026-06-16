"""Tareas Celery de notificación: digest diario de nuevas propiedades."""
import asyncio
from collections import Counter
from datetime import datetime, timedelta, timezone

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import and_, or_, select

logger = get_task_logger(__name__)

# Precio mínimo (USD) que se le exige SOLO a los alquileres para entrar en el
# digest (filtra ruido / publicaciones sin precio real).
MIN_PRICE_USD = 500

# Piso de cordura (USD) para VENTAS: NO es un filtro de negocio, solo descarta
# precios basura (ej. USD 1,25 de publicaciones mal cargadas en Facebook).
# Las ventas SIN precio igual entran; ninguna venta real en PDE/Maldonado baja
# de este umbral.
MIN_SALE_PRICE_USD = 10_000


async def _collect_new(hours: int):
    """Devuelve (count, top_zones, price_min, price_max) de propiedades nuevas.

    Reglas de precio:
      • Venta    → sin filtro de negocio; solo se descarta precio-basura por
                   debajo de MIN_SALE_PRICE_USD. Las ventas sin precio entran.
      • Alquiler → solo si price_usd >= MIN_PRICE_USD.
    """
    from app.db.database import get_db_context
    from app.models.property import OperationType, Property

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
                    or_(
                        and_(
                            Property.operation == OperationType.VENTA,
                            or_(
                                Property.price_usd.is_(None),
                                Property.price_usd >= MIN_SALE_PRICE_USD,
                            ),
                        ),
                        and_(
                            Property.operation != OperationType.VENTA,
                            Property.price_usd >= MIN_PRICE_USD,
                        ),
                    ),
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
    """Mensaje en HTML (parse_mode de Telegram)."""
    if count == 0:
        return (
            "🌙 <b>PropTech PDE — Punta del Este</b>\n\n"
            f"No hubo propiedades nuevas en las últimas {hours} h.\n"
            f'<a href="{link}">Ver dashboard</a>'
        )
    zonas = "\n".join(f"  • {z}: {n}" for z, n in top_zones) if top_zones else ""
    precios = ""
    if pmin is not None and pmax is not None:
        precios = f"💰 Rango: USD {pmin:,.0f} – USD {pmax:,.0f}\n".replace(",", ".")
    msg = (
        "🏠 <b>PropTech PDE — Nuevas propiedades</b>\n"
        f"📍 Punta del Este · últimas {hours} h\n\n"
        f"<b>{count} propiedades nuevas</b> detectadas hoy.\n"
        f"{precios}"
    )
    if zonas:
        msg += "🗺️ Zonas con más altas:\n" + zonas + "\n"
    msg += f'\n👉 <a href="{link}">Ver dashboard</a>'
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
    propiedades nuevas de las últimas DIGEST_WINDOW_HOURS y envía un mensaje
    de Telegram con el resumen y el link al dashboard público `/nuevas`.
    """
    from app.core.config import settings
    from app.notifications.telegram import TelegramNotifier

    hours = settings.DIGEST_WINDOW_HOURS
    link = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/nuevas"

    count, top_zones, pmin, pmax = asyncio.run(_collect_new(hours))
    message = _build_message(count, top_zones, pmin, pmax, hours, link)

    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        logger.warning(
            "Telegram no configurado (TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID) — no se "
            "envía. Mensaje que se habría enviado:\n%s", message
        )
        return {"sent": False, "reason": "no_telegram_config", "count": count}

    notifier = TelegramNotifier()
    # disable_preview=False para que el link del dashboard muestre vista previa
    ok = asyncio.run(notifier.send_message(message, disable_preview=False))
    logger.info("Digest diario Telegram enviado=%s (count=%s)", ok, count)
    return {"sent": ok, "count": count, "link": link}
