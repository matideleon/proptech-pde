"""
Scraper de Gallito Luis — gallito.com.uy

Gallito está protegido por Cloudflare ("Just a moment..." challenge), que
bloquea peticiones HTTP normales (403). Se usa `cloudscraper`, que resuelve
el challenge JS de Cloudflare sin necesidad de navegador.

Las publicaciones se extraen de los <article> del listado; el ID y la URL
se toman del enlace de la ficha (presente en el botón de WhatsApp).
"""
import asyncio
import re
from typing import AsyncGenerator, List, Optional

from bs4 import BeautifulSoup

from app.core.logging import get_logger
from app.scrapers.base import BaseScraper, ScrapedProperty

logger = get_logger("scraper.gallito")

try:
    import cloudscraper

    _CLOUDSCRAPER = True
except ImportError:  # pragma: no cover
    _CLOUDSCRAPER = False


class GallitoScraper(BaseScraper):
    """Scraper de Gallito Luis vía cloudscraper (bypass Cloudflare)."""

    SOURCE_NAME = "gallito"
    BASE_URL = "https://www.gallito.com.uy"

    # Rutas de alquiler. Gallito pagina con ?pag=N
    SEARCH_CONFIGS = [
        {"path": "/inmuebles/alquileres/maldonado", "label": "Alquiler Maldonado"},
    ]
    MAX_PAGES = 6

    def __init__(self):
        super().__init__()
        self._scraper = None

    def _get_cloudscraper(self):
        if self._scraper is None:
            if not _CLOUDSCRAPER:
                raise RuntimeError("cloudscraper no está instalado")
            self._scraper = cloudscraper.create_scraper(
                browser={"browser": "chrome", "platform": "darwin", "mobile": False},
                delay=10,
            )
            self._warmed = False
        return self._scraper

    async def _warmup(self) -> None:
        """Calentar cookies de Cloudflare visitando la home primero."""
        if getattr(self, "_warmed", False):
            return
        loop = asyncio.get_event_loop()

        def _do():
            import time

            sc = self._get_cloudscraper()
            for _ in range(3):
                try:
                    r = sc.get(self.BASE_URL + "/", timeout=45)
                    if r.status_code == 200 and "Just a moment" not in r.text:
                        return True
                except Exception:  # noqa: BLE001
                    pass
                time.sleep(3)
            return False

        ok = await loop.run_in_executor(None, _do)
        self._warmed = ok
        self.logger.info("Gallito warm-up", ok=ok)

    async def _fetch_cf(self, url: str, retries: int = 3) -> Optional[str]:
        """Fetch a través de cloudscraper (síncrono, corre en thread)."""
        await self._warmup()
        loop = asyncio.get_event_loop()

        def _do():
            import time

            sc = self._get_cloudscraper()
            for attempt in range(retries):
                try:
                    r = sc.get(url, timeout=45)
                    if r.status_code == 200 and "Just a moment" not in r.text:
                        return r.text
                    self.logger.warning(
                        "Gallito bloqueado", url=url, status=r.status_code, intento=attempt + 1
                    )
                except Exception as e:  # noqa: BLE001
                    self.logger.error("Error fetch Gallito", url=url, error=str(e))
                time.sleep(5)
            return None

        return await loop.run_in_executor(None, _do)

    # ─────────────────────────────────────────────────────────
    def _parse_article(self, art) -> Optional[ScrapedProperty]:
        """Parsear un <article> del listado de Gallito."""
        try:
            html_str = str(art)
            txt = art.get_text(" ", strip=True)

            # URL + ID (del enlace de la ficha, presente en el botón WhatsApp)
            m = re.search(
                r'(https?://www\.gallito\.com\.uy/[a-z0-9-]+-inmuebles-(\d+))', html_str
            )
            if not m:
                return None
            url, ext_id = m.group(1), m.group(2)

            # Título desde el slug de la URL
            slug = url.rstrip("/").split("/")[-1].replace(f"-inmuebles-{ext_id}", "")
            title = slug.replace("-", " ").strip().capitalize()

            # Precio + moneda
            price = None
            currency = "USD"
            pm = re.search(r'(U\$S|US\$|\$U)\s?([\d.]+)', txt)
            if pm:
                currency = "USD" if ("U$S" in pm.group(1) or "US$" in pm.group(1)) else "UYU"
                num = pm.group(2).replace(".", "")
                price = float(num) if num.isdigit() else None

            # Dormitorios / baños
            bedrooms = bathrooms = None
            dm = re.search(r'(\d+)\s*Dormitorio', txt)
            if dm:
                bedrooms = int(dm.group(1))
            bm = re.search(r'(\d+)\s*Baño', txt)
            if bm:
                bathrooms = int(bm.group(1))

            # m²
            area = None
            am = re.search(r'([\d.]+)\s*m²', txt)
            if am:
                area = float(am.group(1).replace(".", "").replace(",", "."))

            # Tipo de propiedad (heurístico desde el título)
            low = title.lower()
            if "casa" in low:
                ptype = "casa"
            elif "local" in low:
                ptype = "local_comercial"
            elif "penthouse" in low:
                ptype = "penthouse"
            elif "terreno" in low or "lote" in low:
                ptype = "terreno"
            else:
                ptype = "apartamento"

            # Imagen
            img_el = art.select_one("img")
            images: List[str] = []
            if img_el:
                src = img_el.get("data-src") or img_el.get("src") or ""
                if src.startswith("http") and "no-disponible" not in src:
                    images = [src]

            return ScrapedProperty(
                source=self.SOURCE_NAME,
                external_id=ext_id,
                url=url,
                property_type=ptype,
                operation="alquiler",
                title=title or "Aviso Gallito",
                price=price,
                currency=currency,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                area_total=area,
                department="Maldonado",
                images=images,
                raw_data={"gallito_id": ext_id},
            )
        except Exception as e:  # noqa: BLE001
            self.logger.warning("No se pudo parsear article Gallito", error=str(e))
            return None

    async def scrape(self) -> AsyncGenerator[ScrapedProperty, None]:
        """Scraping de Gallito vía cloudscraper."""
        if not _CLOUDSCRAPER:
            self.logger.error("cloudscraper no instalado — Gallito deshabilitado")
            return

        for config in self.SEARCH_CONFIGS:
            label = config["label"]
            self.logger.info(f"🔍 Gallito: {label}")
            seen = set()

            for page in range(1, self.MAX_PAGES + 1):
                url = f"{self.BASE_URL}{config['path']}"
                if page > 1:
                    url = f"{url}?pag={page}"

                html = await self._fetch_cf(url)
                if not html:
                    break

                soup = BeautifulSoup(html, "lxml")
                articles = [a for a in soup.select("article") if a.get_text(strip=True)]
                if not articles:
                    self.logger.info(f"Sin más resultados en página {page}")
                    break

                self.stats.pages_scraped += 1
                new_in_page = 0

                for art in articles:
                    prop = self._parse_article(art)
                    if not prop or not prop.external_id:
                        continue
                    if prop.external_id in seen:
                        continue
                    seen.add(prop.external_id)
                    new_in_page += 1
                    yield prop

                self.logger.info(f"📄 Gallito página {page}", items=new_in_page)
                if new_in_page == 0:
                    break

                await asyncio.sleep(2)  # cortesía entre páginas

            self.logger.info(f"✅ Gallito {label}: {len(seen)} propiedades")
