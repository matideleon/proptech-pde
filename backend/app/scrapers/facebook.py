"""
Scraper de Facebook Marketplace — Maldonado / Punta del Este.

Facebook Marketplace exige sesión iniciada para usuarios normales y bloquea
el scraping anónimo. Sin embargo, sirve los listings embebidos en JSON al
crawler de Google (Googlebot UA) para indexación. Combinado con coordenadas
lat/long, permite obtener publicaciones reales de la zona sin login ni
navegador.

Técnica:
  - User-Agent de Googlebot
  - URL de categoría con ?latitude/longitude/radius (geolocaliza a Maldonado)
  - Parseo de los bloques <script type="application/json"> embebidos
"""
import json
import re
from typing import AsyncGenerator, List, Optional

from app.core.logging import get_logger
from app.scrapers.base import BaseScraper, ScrapedProperty

logger = get_logger("scraper.facebook")


class FacebookMarketplaceScraper(BaseScraper):
    """Scraper de Facebook Marketplace vía Googlebot UA + geolocalización."""

    SOURCE_NAME = "facebook"
    BASE_URL = "https://www.facebook.com"

    GOOGLEBOT_UA = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"

    # Coordenadas y radios de búsqueda (Maldonado / Punta del Este).
    SEARCH_CONFIGS = [
        {"lat": -34.91, "lng": -54.96, "radius": 40, "label": "Maldonado / PDE"},
        {"lat": -34.85, "lng": -54.66, "radius": 20, "label": "José Ignacio / La Barra"},
    ]

    # Categorías de FB Marketplace: alquiler + venta.
    CATEGORIES = [
        {"slug": "propertyrentals", "operation": "alquiler"},
        {"slug": "propertyforsale", "operation": "venta"},
    ]

    def _get_headers(self) -> dict:
        """Headers de Googlebot para que FB sirva los listings embebidos."""
        return {
            "User-Agent": self.GOOGLEBOT_UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-UY,es;q=0.9,en;q=0.8",
            "From": "googlebot(at)googlebot.com",
        }

    # ─────────────────────────────────────────────────────────
    def _extract_listings(self, html: str) -> List[dict]:
        """Extraer listings de los bloques JSON embebidos en el HTML."""
        blocks = re.findall(
            r'<script type="application/json"[^>]*>(.*?)</script>', html, re.DOTALL
        )
        listings: List[dict] = []
        seen_ids = set()

        def walk(obj):
            if isinstance(obj, dict):
                if "marketplace_listing_title" in obj and obj.get("id"):
                    lid = obj.get("id")
                    if lid not in seen_ids:
                        seen_ids.add(lid)
                        listings.append(obj)
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                for it in obj:
                    walk(it)

        for blk in blocks:
            try:
                walk(json.loads(blk))
            except (json.JSONDecodeError, RecursionError):
                continue
        return listings

    def _is_target_location(self, listing: dict) -> bool:
        """¿El listing es de la zona objetivo (Maldonado / PDE)?"""
        loc = (listing.get("location") or {}).get("reverse_geocode") or {}
        city = (loc.get("city") or "")
        targets = (
            "Maldonado", "Punta del Este", "San Carlos", "Piriápolis",
            "La Barra", "José Ignacio", "Pan de Azúcar", "Punta Ballena",
        )
        return any(t in city for t in targets)

    def _parse_listing(self, item: dict, operation: str = "alquiler") -> Optional[ScrapedProperty]:
        """Mapear un listing de FB a ScrapedProperty."""
        try:
            ext_id = str(item.get("id"))
            title = (item.get("marketplace_listing_title") or "").replace("+", " ").strip()
            custom = (item.get("custom_title") or "").replace("+", " ")

            # Precio + moneda
            price_obj = item.get("listing_price") or {}
            amount = price_obj.get("amount")
            formatted = price_obj.get("formatted_amount") or ""
            currency = "UYU" if ("$U" in formatted or "UYU" in formatted) else "USD"
            price = float(amount) if amount else None

            # Dormitorios / baños desde título o custom_title
            bedrooms = bathrooms = None
            text = f"{title} {custom}".lower()
            mb = re.search(r"(\d+)\s*(?:habitaci|dormitor|cuarto|bed|hab\b)", text)
            if mb:
                bedrooms = int(mb.group(1))
            ba = re.search(r"(\d+)\s*(?:baño|bano|bath)", text)
            if ba:
                bathrooms = int(ba.group(1))

            # Ubicación
            loc = (item.get("location") or {}).get("reverse_geocode") or {}
            city = loc.get("city")

            # Imagen real (CDN de FB)
            img = ((item.get("primary_listing_photo") or {}).get("image") or {})
            images = [img["uri"]] if img.get("uri") else []

            url = f"{self.BASE_URL}/marketplace/item/{ext_id}"

            # Tipo de propiedad heurístico
            ptype = "casa" if any(w in text for w in ["casa", "house", "ph", "duplex"]) else "apartamento"

            return ScrapedProperty(
                source=self.SOURCE_NAME,
                external_id=ext_id,
                url=url,
                property_type=ptype,
                operation=operation,
                title=title or "Publicación Facebook Marketplace",
                price=price,
                currency=currency,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                neighborhood=city,
                city=city or "Maldonado",
                department="Maldonado",
                agency_name="Facebook Marketplace (particular)",
                images=images,
                raw_data={"fb_id": ext_id, "formatted_price": formatted},
            )
        except Exception as e:  # noqa: BLE001
            self.logger.warning("No se pudo parsear listing FB", error=str(e))
            return None

    async def scrape(self) -> AsyncGenerator[ScrapedProperty, None]:
        """Scraping de Facebook Marketplace por zona."""
        global_seen = set()

        for category in self.CATEGORIES:
            slug = category["slug"]
            operation = category["operation"]

            for config in self.SEARCH_CONFIGS:
                label = config["label"]
                url = (
                    f"{self.BASE_URL}/marketplace/category/{slug}"
                    f"?latitude={config['lat']}&longitude={config['lng']}&radius={config['radius']}"
                )
                self.logger.info(f"🔍 FB Marketplace [{operation}]: {label}")

                html = await self._fetch(url)
                if not html:
                    self.logger.warning("FB no devolvió HTML", zona=label, operation=operation)
                    continue

                listings = self._extract_listings(html)
                self.stats.pages_scraped += 1
                count = 0

                for item in listings:
                    if not self._is_target_location(item):
                        continue
                    prop = self._parse_listing(item, operation)
                    if not prop or not prop.external_id:
                        continue
                    if prop.external_id in global_seen:
                        continue
                    global_seen.add(prop.external_id)
                    count += 1
                    yield prop

                self.logger.info(f"✅ FB [{operation}] {label}: {count} listings de la zona")
