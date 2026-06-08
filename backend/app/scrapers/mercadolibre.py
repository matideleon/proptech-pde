"""
Scraper de MercadoLibre Inmuebles — Uruguay.

Scraping de propiedades en venta y alquiler de Punta del Este
y toda la región de Maldonado.

Documentación de la API pública de MercadoLibre:
https://developers.mercadolibre.com.ar/es_ar/items-y-busquedas
"""
import asyncio
import json
import re
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, List, Optional
from urllib.parse import urlencode

import aiohttp

from app.core.config import settings
from app.core.logging import get_logger
from app.scrapers.base import BaseScraper, ScrapedProperty
from app.scrapers.config import TARGET

logger = get_logger("scraper.mercadolibre")

# URLs de la API pública de MercadoLibre
ML_API_BASE = "https://api.mercadolibre.com"
ML_SITE_ID = "MLU"  # Uruguay
ML_CATEGORY_INMUEBLES = "MLU1459"  # Inmuebles Uruguay

# Mapeo de tipos de propiedad ML → sistema interno
PROPERTY_TYPE_MAP = {
    "MLU1466": "apartamento",    # Apartamentos
    "MLU1467": "casa",           # Casas
    "MLU1468": "casa",           # Quintas y Chacras
    "MLU1469": "oficina",        # Oficinas y Locales
    "MLU1470": "terreno",        # Terrenos
    "MLU1471": "garage",         # Cocheras y Garages
    "MLU1472": "campo",          # Campos y Estancias
    "MLU1473": "otro",           # Otros inmuebles
}

OPERATION_MAP = {
    "buy": "venta",
    "rent": "alquiler",
}


class MercadoLibreScraper(BaseScraper):
    """
    Scraper para MercadoLibre Inmuebles Uruguay.

    Usa la API pública de ML que no requiere autenticación para búsquedas.
    Para detalles, usa la API de items.
    """

    SOURCE_NAME = "mercadolibre"
    BASE_URL = "https://www.mercadolibre.com.uy"
    API_URL = ML_API_BASE

    # Configuración de búsqueda — el foco es ALQUILER en el rango objetivo.
    # El orden importa: alquiler primero (operación primaria).
    SEARCH_CONFIGS = [
        {
            "state_id": "TUxVUE1BTDc4OTU",  # Maldonado
            "operation": "rent",
            "label": "Alquiler Maldonado",
            # Filtro de precio en origen (USD): rango objetivo con tolerancia
            "price_min_usd": TARGET.rent_min_usd,
            "price_max_usd": TARGET.rent_max_usd,
        },
        {
            "state_id": "TUxVUE1BTDc4OTU",  # Maldonado
            "operation": "buy",
            "label": "Venta Maldonado (contexto de mercado)",
        },
    ]

    ITEMS_PER_PAGE = 50  # Max de la API de ML

    async def _search_page(
        self,
        state_id: str,
        operation: str,
        offset: int = 0,
        price_min_usd: Optional[int] = None,
        price_max_usd: Optional[int] = None,
    ) -> Optional[Dict]:
        """Buscar propiedades en la API de ML."""
        params = {
            "category": ML_CATEGORY_INMUEBLES,
            "state": state_id,
            "OPERATION": operation,
            "offset": offset,
            "limit": self.ITEMS_PER_PAGE,
            "sort": "date_desc",
        }
        # Filtro de precio en origen (la API de ML acepta price=MIN-MAX en USD)
        if price_min_usd is not None and price_max_usd is not None:
            params["price"] = f"{price_min_usd}-{price_max_usd}"

        # OAuth: la API de ML exige token desde 2024. Si está configurado,
        # se envía como query param access_token (también admite Bearer header).
        if settings.MERCADOLIBRE_ACCESS_TOKEN:
            params["access_token"] = settings.MERCADOLIBRE_ACCESS_TOKEN

        url = f"{self.API_URL}/sites/{ML_SITE_ID}/search"

        html = await self._fetch(url, params=params)
        if not html:
            return None

        try:
            return json.loads(html)
        except json.JSONDecodeError as e:
            self.logger.error("Error parseando JSON de ML", error=str(e))
            return None

    def _auth_params(self) -> Optional[Dict]:
        """Params de autenticación OAuth si hay token configurado."""
        if settings.MERCADOLIBRE_ACCESS_TOKEN:
            return {"access_token": settings.MERCADOLIBRE_ACCESS_TOKEN}
        return None

    async def _get_item_details(self, item_id: str) -> Optional[Dict]:
        """Obtener detalles completos de un item."""
        url = f"{self.API_URL}/items/{item_id}"
        html = await self._fetch(url, params=self._auth_params())
        if not html:
            return None
        try:
            return json.loads(html)
        except json.JSONDecodeError:
            return None

    async def _get_item_description(self, item_id: str) -> Optional[str]:
        """Obtener descripción de un item."""
        url = f"{self.API_URL}/items/{item_id}/description"
        html = await self._fetch(url, params=self._auth_params())
        if not html:
            return None
        try:
            data = json.loads(html)
            return data.get("plain_text") or data.get("text", "")
        except json.JSONDecodeError:
            return None

    def _extract_attribute(self, attributes: List[Dict], attr_id: str) -> Optional[str]:
        """Extraer valor de un atributo por ID."""
        for attr in attributes:
            if attr.get("id") == attr_id:
                return attr.get("value_name") or attr.get("values", [{}])[0].get("name")
        return None

    def _safe_int(self, value: Optional[str]) -> Optional[int]:
        """Convertir string a int de forma segura."""
        if not value:
            return None
        try:
            # Limpiar: "3 dormitorios" → 3
            numbers = re.findall(r'\d+', str(value))
            return int(numbers[0]) if numbers else None
        except (ValueError, IndexError):
            return None

    def _safe_float(self, value: Optional[str]) -> Optional[float]:
        """Convertir string a float de forma segura."""
        if not value:
            return None
        try:
            cleaned = re.sub(r'[^\d.,]', '', str(value)).replace(',', '.')
            return float(cleaned) if cleaned else None
        except ValueError:
            return None

    def _parse_item(self, item: Dict, operation: str) -> Optional[ScrapedProperty]:
        """
        Parsear un item de la API de ML a ScrapedProperty.
        """
        try:
            item_id = item.get("id", "")
            attributes = item.get("attributes", [])

            # Precio
            price = item.get("price")
            currency = item.get("currency_id", "USD")
            if currency == "UYU":
                currency = "UYU"
            else:
                currency = "USD"

            # Tipo de propiedad desde categoría
            category_id = item.get("category_id", "")
            property_type = PROPERTY_TYPE_MAP.get(category_id, "otro")

            # Atributos
            bedrooms = self._safe_int(
                self._extract_attribute(attributes, "BEDROOMS")
            )
            bathrooms = self._safe_int(
                self._extract_attribute(attributes, "FULL_BATHROOMS")
                or self._extract_attribute(attributes, "BATHROOMS")
            )
            area_total = self._safe_float(
                self._extract_attribute(attributes, "TOTAL_AREA")
            )
            area_built = self._safe_float(
                self._extract_attribute(attributes, "COVERED_AREA")
            )

            # Localización
            location = item.get("location", {})
            neighborhood = None
            city = "Punta del Este"

            if location:
                neighborhood = (
                    location.get("neighborhood", {}).get("name")
                    or location.get("city", {}).get("name")
                )
                city = location.get("city", {}).get("name", city)

            # Coordenadas
            geo = item.get("geolocation", {})
            latitude = geo.get("latitude")
            longitude = geo.get("longitude")

            # Seller info
            seller = item.get("seller", {})
            agency_name = seller.get("nickname", "") if seller else None

            # Imágenes
            pictures = item.get("pictures", [])
            images = [
                pic.get("secure_url") or pic.get("url", "")
                for pic in pictures
                if pic.get("secure_url") or pic.get("url")
            ]

            # URL del listing
            url = item.get("permalink", "")

            prop = ScrapedProperty(
                source=self.SOURCE_NAME,
                external_id=item_id,
                url=url,
                property_type=property_type,
                operation=OPERATION_MAP.get(operation, "venta"),
                title=item.get("title", "")[:500],
                price=price,
                currency=currency,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                area_total=area_total,
                area_built=area_built,
                neighborhood=neighborhood,
                city=city,
                latitude=float(latitude) if latitude else None,
                longitude=float(longitude) if longitude else None,
                agency_name=agency_name,
                images=images[:20],  # Max 20 imágenes
                raw_data={
                    "ml_id": item_id,
                    "category_id": category_id,
                    "listing_type": item.get("listing_type_id"),
                    "condition": item.get("condition"),
                    "attributes": attributes[:50],  # Guardar atributos raw
                },
            )

            return prop

        except Exception as e:
            self.logger.error("Error parseando item ML", item_id=item.get("id"), error=str(e))
            return None

    async def scrape(self) -> AsyncGenerator[ScrapedProperty, None]:
        """
        Scraping principal de MercadoLibre.

        Itera sobre todas las configuraciones de búsqueda y páginas.
        """
        for config in self.SEARCH_CONFIGS:
            state_id = config["state_id"]
            operation = config["operation"]
            label = config["label"]
            price_min = config.get("price_min_usd")
            price_max = config.get("price_max_usd")

            self.logger.info(f"🔍 Buscando: {label}")
            offset = 0
            total_found = 0

            while True:
                self.logger.debug(f"Página offset={offset}", source=label)

                data = await self._search_page(
                    state_id, operation, offset,
                    price_min_usd=price_min, price_max_usd=price_max,
                )
                if not data:
                    break

                results = data.get("results", [])
                paging = data.get("paging", {})
                total = paging.get("total", 0)

                if not results:
                    self.logger.info(f"Sin más resultados", source=label, offset=offset)
                    break

                self.logger.info(
                    f"📄 Página procesada",
                    source=label,
                    items=len(results),
                    offset=offset,
                    total=total,
                )
                self.stats.pages_scraped += 1

                # Procesar items de esta página
                # Obtener detalles en paralelo (batches de 5)
                batch_size = 5
                for i in range(0, len(results), batch_size):
                    batch = results[i : i + batch_size]
                    tasks = [self._get_item_details(item["id"]) for item in batch]
                    details_list = await asyncio.gather(*tasks, return_exceptions=True)

                    for item_data, details in zip(batch, details_list):
                        if isinstance(details, Exception) or details is None:
                            # Usar datos del search si no hay detalles
                            details = item_data

                        prop = self._parse_item(details, operation)
                        if prop and prop.url:
                            # Post-filtro: para alquiler, descartar fuera de rango.
                            if (
                                prop.operation == "alquiler"
                                and not TARGET.price_in_rent_range(prop.price, prop.currency)
                            ):
                                continue

                            # Obtener descripción
                            desc_task = self._get_item_description(details.get("id", ""))
                            description = await desc_task
                            if description:
                                prop.description = description[:5000]

                            total_found += 1
                            yield prop

                offset += len(results)

                # ¿Hay más páginas?
                if offset >= total or offset >= 1000:  # ML limita a 1000 resultados
                    self.logger.info(f"✅ Búsqueda completada", source=label, total=total_found)
                    break

                # Pausa entre páginas
                await asyncio.sleep(2)

            self.logger.info(f"✅ {label}: {total_found} propiedades")


class MercadoLibreWebScraper(BaseScraper):
    """
    Scraper web de MercadoLibre.

    La API pública de búsqueda fue cerrada por ML (403 incluso con OAuth),
    y el sitio web bloquea a clientes anónimos con un muro de
    'account-verification'. Solución: identificarse como Googlebot, a quien
    ML sí le sirve el HTML completo (para indexación en buscadores).

    Foco en ALQUILER en el rango objetivo (USD 400–2.000).
    """

    SOURCE_NAME = "mercadolibre"
    BASE_URL = "https://listado.mercadolibre.com.uy"

    # UA de Googlebot: ML sirve el contenido para indexación.
    GOOGLEBOT_UA = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"

    # Solo alquiler, zonas de Maldonado / Punta del Este.
    SEARCH_URLS = [
        ("https://listado.mercadolibre.com.uy/inmuebles/alquiler/maldonado/", "alquiler"),
        ("https://listado.mercadolibre.com.uy/inmuebles/departamentos/alquiler/punta-del-este/", "alquiler"),
    ]

    ITEMS_PER_PAGE = 48
    MAX_PAGES = 8

    def _get_headers(self) -> dict:
        """Headers de Googlebot para sortear el muro anti-bot de ML."""
        return {
            "User-Agent": self.GOOGLEBOT_UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-UY,es;q=0.9,en;q=0.8",
            "From": "googlebot(at)googlebot.com",
        }

    async def scrape(self) -> AsyncGenerator[ScrapedProperty, None]:
        """Scraping del sitio web de MercadoLibre vía Googlebot UA."""
        for base_url, operation in self.SEARCH_URLS:
            self.logger.info(f"🔍 ML web: {operation} {base_url[:50]}")
            seen = set()

            for page in range(1, self.MAX_PAGES + 1):
                # Paginación de ML: _Desde_49, _Desde_97, ...
                if page > 1:
                    offset = (page - 1) * self.ITEMS_PER_PAGE + 1
                    url = f"{base_url}_Desde_{offset}"
                else:
                    url = base_url

                html = await self._fetch(url)
                if not html:
                    break

                if "account-verification" in html[:5000] and "ui-search-layout__item" not in html:
                    self.logger.warning("ML bloqueó la petición (account-verification)")
                    break

                soup = self._parse_html(html)
                cards = soup.select("li.ui-search-layout__item")
                if not cards:
                    self.logger.info(f"Sin más resultados en página {page}")
                    break

                self.stats.pages_scraped += 1
                new_in_page = 0

                for card in cards:
                    prop = self._parse_card(card, operation)
                    if prop and prop.external_id and prop.external_id not in seen:
                        seen.add(prop.external_id)
                        new_in_page += 1
                        yield prop

                self.logger.info(f"📄 ML web página {page}", items=new_in_page)
                if new_in_page == 0:
                    break

            self.logger.info(f"✅ ML web {operation}: {len(seen)} propiedades")

    def _parse_card(self, card, operation: str) -> Optional[ScrapedProperty]:
        """Parsear card de listing del sitio web."""
        try:
            # URL + ID
            link = card.select_one("a.poly-component__title, a.ui-search-link, a[href*='MLU']")
            if not link:
                return None
            url = (link.get("href") or "").split("#")[0]
            if not url:
                return None
            id_match = re.search(r'MLU-?(\d+)', url)
            external_id = f"MLU{id_match.group(1)}" if id_match else None

            # Título
            title_el = card.select_one(".poly-component__title, .ui-search-item__title, h2")
            title = title_el.get_text(strip=True) if title_el else ""

            # Precio + moneda (estructura andes-money-amount)
            price = None
            currency = "USD"
            cur_el = card.select_one(".andes-money-amount__currency-symbol")
            frac_el = card.select_one(".andes-money-amount__fraction")
            if cur_el:
                cur_txt = cur_el.get_text(strip=True)
                currency = "UYU" if ("$U" in cur_txt or cur_txt == "$") else "USD"
                # ML usa "US$" para dólar y "$" para pesos uruguayos
                if "US$" in cur_txt or "U$S" in cur_txt:
                    currency = "USD"
            if frac_el:
                numbers = re.sub(r'[^\d]', '', frac_el.get_text(strip=True))
                price = float(numbers) if numbers else None

            # Atributos: dormitorios, baños, m²
            bedrooms = bathrooms = None
            area_total = None
            attrs = card.select(
                ".poly-attributes_list__item, .poly-attributes-list__item, "
                ".ui-search-card-attributes__attribute"
            )
            for attr in attrs:
                text = attr.get_text(strip=True).lower()
                nums = re.findall(r'[\d.,]+', text)
                if not nums:
                    continue
                if "dormitorio" in text or "ambiente" in text or "habitac" in text:
                    bedrooms = int(re.sub(r'[^\d]', '', nums[0]) or 0) or None
                elif "baño" in text or "bano" in text:
                    bathrooms = int(re.sub(r'[^\d]', '', nums[0]) or 0) or None
                elif "m²" in text or "m2" in text or "metro" in text:
                    area_total = float(nums[0].replace('.', '').replace(',', '.'))

            # Localización
            loc_el = card.select_one(".poly-component__location, .ui-search-item__location")
            neighborhood = loc_el.get_text(strip=True) if loc_el else None

            # Imagen (puede venir en data-src por lazy-load)
            img_el = card.select_one("img.poly-component__picture, img.ui-search-result-image__element, img")
            images = []
            if img_el:
                img_url = img_el.get("data-src") or img_el.get("src") or ""
                if img_url and not img_url.startswith("data:"):
                    images = [img_url]

            return ScrapedProperty(
                source=self.SOURCE_NAME,
                external_id=external_id,
                url=url,
                operation=operation,
                title=title,
                price=price,
                currency=currency,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                area_total=area_total,
                neighborhood=neighborhood,
                department="Maldonado",
                images=images,
                raw_data={"ml_id": external_id},
            )

        except Exception as e:
            self.logger.error("Error parseando card ML web", error=str(e))
            return None
