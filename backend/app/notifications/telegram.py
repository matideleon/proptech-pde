"""Notificaciones via Telegram Bot API."""
from typing import Dict, Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("notifications.telegram")


class TelegramNotifier:
    """Cliente para Telegram Bot API."""

    BASE_URL = "https://api.telegram.org"

    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.default_chat_id = settings.TELEGRAM_CHAT_ID

    def _api_url(self, method: str) -> str:
        return f"{self.BASE_URL}/bot{self.token}/{method}"

    async def send_message(
        self,
        text: str,
        chat_id: Optional[str] = None,
        parse_mode: str = "HTML",
        disable_preview: bool = True,
    ) -> bool:
        """Enviar mensaje de texto a Telegram."""
        if not self.token:
            logger.warning("Telegram no configurado — simulando envío")
            logger.info(f"[TG SIMULADO]: {text[:100]}")
            return True

        chat_id = chat_id or self.default_chat_id
        if not chat_id:
            logger.error("No hay chat_id configurado para Telegram")
            return False

        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_preview,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self._api_url("sendMessage"),
                    json=payload,
                    timeout=10,
                )
                response.raise_for_status()
                logger.info(f"✅ Telegram enviado a {chat_id}")
                return True
            except httpx.HTTPError as e:
                logger.error("Error Telegram", error=str(e))
                return False

    async def send_new_property(
        self,
        property_data: Dict,
        chat_id: Optional[str] = None,
    ) -> bool:
        """Enviar alerta de nueva propiedad."""
        price = property_data.get("price_usd") or property_data.get("price", 0)
        title = property_data.get("title", "Propiedad")[:100]
        neighborhood = property_data.get("neighborhood", "N/A")
        bedrooms = property_data.get("bedrooms")
        area = property_data.get("area_total")
        url = property_data.get("url", "")
        source = property_data.get("source", "")
        ai_score = property_data.get("ai_score")
        is_premium = property_data.get("ai_premium", False)
        is_opportunity = property_data.get("ai_opportunity", False)

        # Badges
        badges = []
        if is_premium:
            badges.append("⭐ PREMIUM")
        if is_opportunity:
            badges.append("🔥 OPORTUNIDAD")
        badge_text = " | ".join(badges)

        features = []
        if bedrooms:
            features.append(f"🛏 {bedrooms} dorm")
        if area:
            features.append(f"📐 {area:.0f}m²")
        features_text = " · ".join(features)

        score_text = f"🤖 Score IA: {ai_score:.0f}/100" if ai_score else ""

        message = (
            f"🏠 <b>Nueva propiedad en {neighborhood}</b>\n"
            f"{badge_text}\n\n"
            f"<b>{title}</b>\n"
            f"💰 <b>USD {price:,.0f}</b>\n"
        )
        if features_text:
            message += f"{features_text}\n"
        if score_text:
            message += f"{score_text}\n"
        if source:
            message += f"📡 Fuente: {source}\n"
        if url:
            message += f'\n<a href="{url}">Ver propiedad →</a>'

        return await self.send_message(message, chat_id)

    async def send_price_drop(
        self,
        property_data: Dict,
        old_price: float,
        new_price: float,
        change_pct: float,
        chat_id: Optional[str] = None,
    ) -> bool:
        """Enviar alerta de baja de precio."""
        title = property_data.get("title", "Propiedad")[:100]
        neighborhood = property_data.get("neighborhood", "N/A")
        url = property_data.get("url", "")

        message = (
            f"📉 <b>¡Bajada de precio!</b>\n\n"
            f"<b>{title}</b>\n"
            f"📍 {neighborhood}\n\n"
            f"Precio anterior: USD {old_price:,.0f}\n"
            f"<b>Precio actual: USD {new_price:,.0f}</b>\n"
            f"💰 Ahorro: USD {old_price - new_price:,.0f} ({abs(change_pct):.1f}% menos)\n"
        )
        if url:
            message += f'\n<a href="{url}">Ver propiedad →</a>'

        return await self.send_message(message, chat_id)


# Singleton
telegram = TelegramNotifier()
