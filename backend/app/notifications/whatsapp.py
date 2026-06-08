"""
Sistema de notificaciones WhatsApp Business API.
Usa la API oficial de Meta para enviar mensajes.
"""
import json
from typing import Dict, Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("notifications.whatsapp")


class WhatsAppNotifier:
    """
    Cliente para WhatsApp Business API (Meta Cloud API).

    Documentación: https://developers.facebook.com/docs/whatsapp/cloud-api
    """

    API_VERSION = "v18.0"

    def __init__(self):
        self.phone_id = settings.WHATSAPP_PHONE_ID
        self.token = settings.WHATSAPP_TOKEN
        self.base_url = f"{settings.WHATSAPP_API_URL}/{self.phone_id}"

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def send_text(
        self,
        to: str,
        message: str,
    ) -> bool:
        """Enviar mensaje de texto simple."""
        if not self.phone_id or not self.token:
            logger.warning("WhatsApp no configurado — simulando envío")
            logger.info(f"[WA SIMULADO] Para: {to}\n{message}")
            return True

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": message},
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=self._get_headers(),
                    json=payload,
                    timeout=15,
                )
                response.raise_for_status()
                logger.info(f"✅ WhatsApp enviado a {to}")
                return True
            except httpx.HTTPError as e:
                logger.error(f"Error enviando WhatsApp a {to}", error=str(e))
                return False

    async def send_property_alert(
        self,
        to: str,
        alert_type: str,
        property_data: Dict,
    ) -> bool:
        """
        Enviar alerta de propiedad formateada.

        alert_type: 'new_property', 'price_drop', 'opportunity'
        """
        price = property_data.get("price_usd") or property_data.get("price", 0)
        neighborhood = property_data.get("neighborhood", "")
        title = property_data.get("title", "Propiedad")
        url = property_data.get("url", "")
        bedrooms = property_data.get("bedrooms", "")
        area = property_data.get("area_total", "")
        change_pct = property_data.get("change_pct", 0)

        if alert_type == "new_property":
            emoji = "🏠"
            header = "¡Nueva propiedad!"
        elif alert_type == "price_drop":
            emoji = "📉"
            header = f"¡Bajada de precio! -{abs(change_pct or 0):.0f}%"
        elif alert_type == "opportunity":
            emoji = "⭐"
            header = "¡Oportunidad detectada!"
        else:
            emoji = "🔔"
            header = "Alerta inmobiliaria"

        rooms_text = f"🛏 {bedrooms} dorm" if bedrooms else ""
        area_text = f"📐 {area}m²" if area else ""
        features = " | ".join(filter(None, [rooms_text, area_text]))

        message = (
            f"{emoji} *{header}*\n\n"
            f"*{title}*\n"
            f"📍 {neighborhood}\n"
            f"💰 USD {price:,.0f}\n"
        )
        if features:
            message += f"{features}\n"
        if url:
            message += f"\n🔗 {url}"

        return await self.send_text(to, message)

    async def send_market_summary(
        self,
        to: str,
        zone: str,
        stats: Dict,
    ) -> bool:
        """Enviar resumen de mercado diario."""
        message = (
            f"📊 *Resumen de mercado — {zone}*\n\n"
            f"📅 {stats.get('date', '')}\n\n"
            f"🏠 Propiedades activas: {stats.get('active_count', 0):,}\n"
            f"🆕 Nuevas hoy: {stats.get('new_today', 0)}\n"
            f"📉 Bajas de precio: {stats.get('price_drops', 0)}\n"
            f"⭐ Oportunidades: {stats.get('opportunities', 0)}\n\n"
            f"💵 Precio promedio venta: USD {stats.get('avg_sale_usd', 0):,.0f}\n"
            f"📐 Precio/m²: USD {stats.get('avg_m2_usd', 0):,.0f}\n\n"
            f"_PropTech PDE — Punta del Este Intelligence_"
        )
        return await self.send_text(to, message)


# Singleton
whatsapp = WhatsAppNotifier()
