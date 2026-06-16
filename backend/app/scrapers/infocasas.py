"""
Scraper de InfoCasas Uruguay — infocasas.com.uy

Portal inmobiliario líder de Uruguay. Requiere Playwright para
algunas páginas con lazy loading y protecciones anti-bot.
"""
import asyncio
import re
from typing import AsyncGenerator, Optional
from urllib.parse import urljoin, urlencode

from bs4 import BeautifulSoup

from app.core.logging import get_logger
from app.scrapers.base import BaseScraper, ScrapedProperty
from app.scrapers.playwright_helper import PlaywrightFetcher

logger = get_logger("scraper.infocasas")


class InfoCasasScraper(BaseScraper):
    """
    Scraper para InfoCasas Uruguay.

    InfoCasas tiene protecciones anti-bot moderadas.
    Usamos una combinación de requests HTTP para páginas de listado
    y Playwright para páginas de detalle cuando es necesario.
    """

    SOURCE_NAME = "infocasas"
    BASE_URL = "https://www.infocasas.com.uy"

    # Configuraciones de búsqueda — alquiler + venta (datos vía __NEXT_DATA__).
    # Estos paths devuelven HTML con el JSON embebido de Next.js.
    SEARCH_CONFIGS = [
        {
            "path": "/alquiler/casas-y-apartamentos/maldonado",
            "operation": "alquiler",
            "label": "Alquiler Maldonado",
        },
        {
            "path": "/alquiler/casas-y-apartamentos/punta-del-este",
            "operation": "alquiler",
            "label": "Alquiler Punta del Este",
        },
        {
            "path": "/alquiler/casas-y-apartamentos/maldonado/maldonado",
            "operation": "alquiler",
            "label": "Alquiler Maldonado ciudad",
        },
        {
            "path": "/venta/casas-y-apartamentos/maldonado",
            "operation": "venta",
            "label": "Venta Maldonado",
        },
        {
            "path": "/venta/casas-y-apartamentos/punta-del-este",
            "operation": "venta",
            "label": "Venta Punta del Este",
        },
        {
            "path": "/venta/casas-y-apartamentos/maldonado/maldonado",
            "operation": "venta",
            "label": "Venta Maldonado ciudad",
        },
    ]

    MAX_PAGES = 8  # páginas por config

    # Tipos de propiedad InfoCasas
    PROPERTY_TYPE_MAP = {
        "apartamento": "apartamento",
        "casa": "casa",
        "terreno": "terreno",
        "local": "local_comercial",
        "oficina": "oficina",
        "campo": "campo",
        "chacra": "chacra",
        "garage": "garage",
        "penthouse": "penthouse",
        "duplex": "duplex",
    }

    def _parse_price(self, price_text: str) -> tuple[Optional[float], str]:
        """
        Parsear precio de InfoCasas.
        Formatos: "U$S 250,000", "$U 500.000", "Consultar"
        """
        if not price_text or "consultar" in price_text.lower():
            return None, "USD"

        currency = "USD"
        if "U$S" in price_text or "USD" in price_text or "US$" in price_text:
            currency = "USD"
        elif "$U" in price_text or "UYU" in price_text or "UR$" in price_text:
            currency = "UYU"

        # Extraer número
        cleaned = re.sub(r'[^\d]', '', price_text)
        if cleaned:
            return float(cleaned), currency
        return None, currency

    def _parse_area(self, area_text: str) -> Optional[float]:
        """Parsear área en m²."""
        if not area_text:
            return None
        match = re.search(r'([\d.,]+)\s*m²?', area_text, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(',', '.'))
        return None

    def _extract_int(self, text: str) -> Optional[int]:
        """Extraer primer número entero del texto."""
        if not text:
            return None
        match = re.search(r'\d+', text)
        return int(match.group()) if match else None

    async def _scrape_listing_page(
        self,
        url: str,
        operation: str,
    ) -> tuple[list[ScrapedProperty], Optional[str]]:
        """
        Scrape una página de listado.
        Retorna (propiedades, url_siguiente_pagina)
        """
        html = await self._fetch(url)
        if not html:
            return [], None

        soup = self._parse_html(html)
        properties = []

        # Buscar cards de propiedades
        # InfoCasas usa varios selectores según el tipo de vista
        cards = (
            soup.select("div.list-card-container")
            or soup.select("article.property-card")
            or soup.select(".result-item")
            or soup.select("[data-qa='posting PROPERTY']")
        )

        self.logger.debug(f"Cards encontradas: {len(cards)}", url=url)

        for card in cards:
            prop = self._parse_card(card, operation)
            if prop:
                properties.append(prop)

        # URL de siguiente página
        next_url = None
        next_link = (
            soup.select_one("a[rel='next']")
            or soup.select_one(".pagination-next a")
            or soup.select_one("a.next")
        )
        if next_link:
            href = next_link.get("href", "")
            if href:
                next_url = urljoin(self.BASE_URL, href)

        return properties, next_url

    def _parse_card(self, card, operation: str) -> Optional[ScrapedProperty]:
        """Parsear una card de propiedad de InfoCasas."""
        try:
            # URL y external_id
            link = card.select_one("a[href]")
            if not link:
                return None

            href = link.get("href", "")
            url = urljoin(self.BASE_URL, href)

            # ID desde URL o atributo data
            external_id = (
                card.get("data-id")
                or card.get("data-posting-id")
                or re.search(r'/(\d+)(?:/|$)', href, re.IGNORECASE) and
                   re.search(r'/(\d+)(?:/|$)', href).group(1)
            )

            # Título
            title_el = (
                card.select_one("h2.card-title")
                or card.select_one(".property-title")
                or card.select_one("h2, h3")
            )
            title = title_el.get_text(strip=True) if title_el else "Propiedad"

            # Tipo de propiedad (del título o clase)
            property_type = "apartamento"
            title_lower = title.lower()
            for key, val in self.PROPERTY_TYPE_MAP.items():
                if key in title_lower:
                    property_type = val
                    break

            # Precio
            price_el = (
                card.select_one(".price strong")
                or card.select_one(".property-price")
                or card.select_one("[class*='price']")
            )
            price_text = price_el.get_text(strip=True) if price_el else ""
            price, currency = self._parse_price(price_text)

            # Características en chips/badges
            bedrooms = bathrooms = None
            area_total = None

            feature_items = card.select(".features li, .specs li, .card-features span, [class*='feature']")
            for item in feature_items:
                text = item.get_text(strip=True).lower()
                icon = item.select_one("i, svg, use")
                icon_class = icon.get("class", []) if icon else []

                if any(x in text for x in ["dorm", "hab", "pieza"]) or "bedroom" in str(icon_class):
                    bedrooms = self._extract_int(text)
                elif "baño" in text or "bano" in text or "bathroom" in str(icon_class):
                    bathrooms = self._extract_int(text)
                elif "m²" in text or "m2" in text or "area" in str(icon_class):
                    area_total = self._parse_area(text)

            # Localización
            location_el = (
                card.select_one(".card-location")
                or card.select_one(".property-location")
                or card.select_one("[class*='location']")
            )
            neighborhood = None
            if location_el:
                neighborhood = location_el.get_text(strip=True)
                # Limpiar "Maldonado >" etc.
                neighborhood = re.sub(r'\s*>\s*', ', ', neighborhood)
                # Tomar la parte más específica
                parts = [p.strip() for p in neighborhood.split(',') if p.strip()]
                if parts:
                    neighborhood = parts[-1]  # La más específica

            # Imagen principal
            images = []
            img_el = card.select_one("img[src], img[data-src]")
            if img_el:
                img_url = img_el.get("src") or img_el.get("data-src", "")
                if img_url and not img_url.startswith("data:") and "placeholder" not in img_url:
                    images = [img_url]

            # Inmobiliaria
            agency_el = card.select_one(".agency-name, .publisher-name, [class*='agency']")
            agency_name = agency_el.get_text(strip=True) if agency_el else None

            return ScrapedProperty(
                source=self.SOURCE_NAME,
                external_id=str(external_id) if external_id else None,
                url=url,
                property_type=property_type,
                operation=operation,
                title=title[:500],
                price=price,
                currency=currency,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                area_total=area_total,
                neighborhood=neighborhood,
                images=images,
                agency_name=agency_name,
            )

        except Exception as e:
            self.logger.error("Error parseando card InfoCasas", error=str(e))
            return None

    async def _scrape_detail(self, prop: ScrapedProperty) -> ScrapedProperty:
        """
        Enriquecer propiedad con datos de la página de detalle.
        """
        html = await self._fetch(prop.url)
        if not html:
            return prop

        soup = self._parse_html(html)

        # Descripción completa
        desc_el = (
            soup.select_one(".property-description")
            or soup.select_one(".description-body")
            or soup.select_one("[class*='description']")
        )
        if desc_el:
            prop.description = desc_el.get_text(separator="\n", strip=True)[:5000]

        # Amenidades
        amenity_items = soup.select(".amenities li, .features-list li, [class*='amenity']")
        prop.amenities = [item.get_text(strip=True) for item in amenity_items if item.get_text(strip=True)]

        # Más características
        detail_rows = soup.select("table.property-details tr, .spec-row")
        for row in detail_rows:
            cells = row.select("td, span")
            if len(cells) >= 2:
                key = cells[0].get_text(strip=True).lower()
                val = cells[1].get_text(strip=True)
                if "año" in key or "construccion" in key:
                    year = self._extract_int(val)
                    if year and 1900 < year < 2030:
                        prop.year_built = year
                elif "piso" in key or "planta" in key:
                    prop.floor = self._extract_int(val)
                elif "garage" in key or "cochera" in key:
                    prop.garages = self._extract_int(val)
                elif "expensa" in key or "gasto" in key:
                    expense_price, expense_currency = self._parse_price(val)
                    prop.expenses = expense_price
                    prop.expenses_currency = expense_currency

        # Teléfonos de contacto
        phones = []
        phone_els = soup.select("a[href^='tel:'], .phone-number, [class*='phone']")
        for el in phone_els:
            phone = el.get("href", "").replace("tel:", "").strip() or el.get_text(strip=True)
            if phone and re.match(r'[\d\s\+\-\(\)]{7,}', phone):
                phones.append(phone)
        if phones:
            prop.contact_phone = phones[0]

        # Email de contacto
        email_els = soup.select("a[href^='mailto:']")
        if email_els:
            prop.contact_email = email_els[0].get("href", "").replace("mailto:", "").strip()

        # Coordenadas GPS (desde script JSON-LD o mapa)
        scripts = soup.select("script[type='application/ld+json']")
        for script in scripts:
            try:
                import json
                data = json.loads(script.string or "")
                geo = data.get("geo", {})
                if geo:
                    prop.latitude = float(geo.get("latitude", 0)) or None
                    prop.longitude = float(geo.get("longitude", 0)) or None
                    break
            except Exception:
                pass

        # Buscar coordenadas en scripts JS
        if not prop.latitude:
            for script in soup.find_all("script"):
                script_text = script.string or ""
                lat_match = re.search(r'"latitude":\s*([-\d.]+)', script_text)
                lng_match = re.search(r'"longitude":\s*([-\d.]+)', script_text)
                if lat_match and lng_match:
                    prop.latitude = float(lat_match.group(1))
                    prop.longitude = float(lng_match.group(1))
                    break

        # Imágenes adicionales
        if len(prop.images) <= 1:
            all_imgs = []
            for img in soup.select("img[src]"):
                src = img.get("src", "")
                if src and "photo" in src or "image" in src or any(
                    ext in src.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]
                ):
                    if not src.startswith("data:"):
                        all_imgs.append(src)
            if all_imgs:
                prop.images = list(dict.fromkeys(all_imgs))[:20]

        # Nombre del agente / inmobiliaria
        agent_el = soup.select_one(".agent-name, .publisher-name, [class*='agent']")
        if agent_el and not prop.agency_name:
            prop.agency_name = agent_el.get_text(strip=True)

        return prop

    # ─────────────────────────────────────────────────────────
    #  EXTRACCIÓN VÍA __NEXT_DATA__  (robusta, sin selectores HTML)
    # ─────────────────────────────────────────────────────────
    def _extract_next_data(self, html: str) -> Optional[dict]:
        """Extraer el JSON de Next.js embebido en la página."""
        import json

        m = re.search(
            r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL
        )
        if not m:
            return None
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            return None

    def _parse_next_item(self, item: dict, operation: str) -> Optional[ScrapedProperty]:
        """Mapear un item de searchFast.data a ScrapedProperty."""
        try:
            ext_id = str(item.get("id"))
            link = item.get("link") or ""
            url = urljoin(self.BASE_URL, link) if link else f"{self.BASE_URL}/{ext_id}"

            # Precio + moneda
            price_obj = item.get("price") or {}
            amount = price_obj.get("amount")
            cur_name = ((price_obj.get("currency") or {}).get("name") or "").strip()
            currency = "UYU" if cur_name in ("$", "$U") else "USD"

            # Ubicación
            locs = item.get("locations") or {}
            neigh = locs.get("neighbourhood") or []
            neighborhood = neigh[0]["name"] if neigh else None
            state = locs.get("state") or []
            department = state[0]["name"] if state else "Maldonado"

            # Características
            area = item.get("m2Built") or item.get("m2apto")

            # Imágenes (URLs reales del CDN de InfoCasas)
            images = [
                img["image"]
                for img in (item.get("images") or [])
                if img.get("image")
            ]

            # Contacto / inmobiliaria — usar whatsapp_phone real (no el masked_phone)
            owner = item.get("owner") or {}
            agency_name = owner.get("name")
            whatsapp = owner.get("whatsapp_phone")  # teléfono real completo
            address = owner.get("address")
            subs = owner.get("subsidiaries") or []
            if not address and subs:
                address = subs[0].get("address")
            # Si no hay whatsapp, usar el masked como último recurso
            phone = whatsapp or (subs[0].get("masked_phone") if subs else None)

            # Tipo de propiedad (typeID: 1=casa, 2=apartamento aprox.)
            type_map = {1: "casa", 2: "apartamento", 3: "terreno", 4: "local_comercial"}
            property_type = type_map.get(item.get("typeID"), "apartamento")

            return ScrapedProperty(
                source=self.SOURCE_NAME,
                external_id=ext_id,
                url=url,
                property_type=property_type,
                operation=operation,
                title=item.get("title", "").strip() or "Propiedad InfoCasas",
                price=float(amount) if amount else None,
                currency=currency,
                bedrooms=item.get("bedrooms"),
                bathrooms=item.get("bathrooms"),
                area_total=float(area) if area else None,
                area_built=float(item.get("m2Built")) if item.get("m2Built") else None,
                neighborhood=neighborhood,
                department=department,
                latitude=item.get("latitude"),
                longitude=item.get("longitude"),
                agency_name=agency_name,
                contact_phone=phone,
                contact_whatsapp=whatsapp or phone,
                address=address,
                images=images,
                raw_data={"infocasas_id": ext_id, "code": item.get("code")},
            )
        except Exception as e:  # noqa: BLE001
            self.logger.warning("No se pudo parsear item InfoCasas", error=str(e))
            return None

    async def scrape(self) -> AsyncGenerator[ScrapedProperty, None]:
        """Scraping principal de InfoCasas vía __NEXT_DATA__."""
        for config in self.SEARCH_CONFIGS:
            operation = config["operation"]
            label = config["label"]
            seen = set()

            self.logger.info(f"🔍 InfoCasas: {label}")

            for page in range(1, self.MAX_PAGES + 1):
                path = config["path"]
                url = urljoin(self.BASE_URL, path)
                if page > 1:
                    url = f"{url}?pagina={page}"

                html = await self._fetch(url)
                if not html:
                    break

                data = self._extract_next_data(html)
                if not data:
                    self.logger.warning("Sin __NEXT_DATA__", url=url)
                    break

                try:
                    items = (
                        data["props"]["pageProps"]["fetchResult"]["searchFast"]["data"]
                    )
                except (KeyError, TypeError):
                    items = []

                if not items:
                    self.logger.info(f"Sin más resultados en página {page}")
                    break

                self.stats.pages_scraped += 1
                new_in_page = 0

                for item in items:
                    prop = self._parse_next_item(item, operation)
                    if not prop or not prop.external_id:
                        continue
                    if prop.external_id in seen:
                        continue
                    seen.add(prop.external_id)
                    new_in_page += 1
                    yield prop

                self.logger.info(
                    f"📄 Página {page}", source=label, items=new_in_page
                )

                if new_in_page == 0:
                    break

            self.logger.info(f"✅ InfoCasas {label}: {len(seen)} propiedades")
