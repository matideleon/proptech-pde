"""
Helper de Playwright para páginas que requieren JavaScript.
Usado para Facebook Marketplace y portales con protecciones anti-bot.
"""
import asyncio
import random
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("scraper.playwright")


class PlaywrightFetcher:
    """
    Fetcher basado en Playwright para páginas con JavaScript.

    Simula un browser real con:
    - Viewport humano
    - Movimientos de mouse aleatorios
    - Delays entre acciones
    - Fingerprinting mínimo
    """

    def __init__(self):
        self._browser = None
        self._playwright = None

    async def start(self):
        """Iniciar Playwright."""
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--no-first-run",
                "--no-zygote",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        logger.info("✅ Playwright iniciado")

    async def stop(self):
        """Detener Playwright."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Playwright detenido")

    async def get_page_html(
        self,
        url: str,
        wait_for: Optional[str] = None,
        scroll_to_bottom: bool = False,
        timeout: int = 30000,
    ) -> Optional[str]:
        """
        Obtener HTML de una página renderizada con JS.

        Args:
            url: URL a cargar
            wait_for: Selector CSS a esperar (opcional)
            scroll_to_bottom: Si debe hacer scroll para cargar lazy content
            timeout: Timeout en ms
        """
        if not self._browser:
            await self.start()

        context = None
        page = None

        try:
            context = await self._browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/121.0.0.0 Safari/537.36"
                ),
                locale="es-UY",
                timezone_id="America/Montevideo",
                extra_http_headers={
                    "Accept-Language": "es-UY,es;q=0.9",
                    "DNT": "1",
                },
            )

            # Anti-detección: ocultar webdriver
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                window.chrome = { runtime: {} };
            """)

            page = await context.new_page()

            # Bloquear recursos innecesarios para velocidad
            await page.route("**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2}", lambda route: route.abort())
            await page.route("**/google-analytics.com/**", lambda route: route.abort())
            await page.route("**/googletagmanager.com/**", lambda route: route.abort())
            await page.route("**/facebook.com/tr/**", lambda route: route.abort())

            # Navegar
            await page.goto(url, timeout=timeout, wait_until="domcontentloaded")

            # Simular comportamiento humano
            await asyncio.sleep(random.uniform(1, 3))

            # Mover mouse aleatoriamente
            await page.mouse.move(
                random.randint(100, 800),
                random.randint(100, 400),
            )

            # Esperar selector específico
            if wait_for:
                try:
                    await page.wait_for_selector(wait_for, timeout=10000)
                except Exception:
                    logger.warning(f"Selector no encontrado: {wait_for}")

            # Scroll para cargar lazy content
            if scroll_to_bottom:
                await self._smooth_scroll(page)

            # Obtener HTML final
            return await page.content()

        except Exception as e:
            logger.error("Error en Playwright fetch", url=url, error=str(e))
            return None
        finally:
            if page:
                await page.close()
            if context:
                await context.close()

    async def _smooth_scroll(self, page) -> None:
        """Scroll suave que simula comportamiento humano."""
        for _ in range(10):
            await page.evaluate("window.scrollBy(0, window.innerHeight * 0.7)")
            await asyncio.sleep(random.uniform(0.3, 0.8))

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.stop()


class FacebookMarketplaceScraper:
    """
    Scraper de Facebook Marketplace para inmuebles.

    NOTA: Facebook Marketplace requiere autenticación para ver detalles.
    Esta implementación usa Playwright con una cuenta de servicio.
    """

    SOURCE_NAME = "facebook"
    BASE_URL = "https://www.facebook.com/marketplace"

    # Búsquedas para Punta del Este
    SEARCH_QUERIES = [
        "apartamento punta del este",
        "casa punta del este venta",
        "inmueble maldonado uruguay",
        "propiedad la barra uruguay",
    ]

    def __init__(self, fb_cookies: Optional[str] = None):
        self.fb_cookies = fb_cookies
        self.fetcher = PlaywrightFetcher()
        self.logger = get_logger("scraper.facebook")

    async def scrape(self):
        """
        Scraping de Facebook Marketplace.

        IMPORTANTE: Para usar este scraper necesitas:
        1. Una cuenta de Facebook dedicada (no tu cuenta personal)
        2. Las cookies de sesión en fb_cookies
        3. VPN o proxies uruguayos (para resultados de Uruguay)
        """
        self.logger.warning(
            "Facebook Marketplace requiere autenticación. "
            "Configura fb_cookies para activar este scraper."
        )

        if not self.fb_cookies:
            return

        async with self.fetcher:
            for query in self.SEARCH_QUERIES:
                url = (
                    f"{self.BASE_URL}/search"
                    f"?query={query.replace(' ', '+')}"
                    f"&category_id=propertyrentals"
                )

                html = await self.fetcher.get_page_html(
                    url,
                    wait_for="[data-pagelet='MarketplaceTopbar']",
                    scroll_to_bottom=True,
                )

                if html:
                    # Parsear resultados (yield from no es válido en async)
                    for prop in self._parse_marketplace_results(html):
                        yield prop

    def _parse_marketplace_results(self, html: str):
        """Parsear resultados del Marketplace."""
        from bs4 import BeautifulSoup
        import re

        soup = BeautifulSoup(html, "lxml")

        # FB Marketplace usa data-testid y aria labels
        listings = soup.select("[data-testid='marketplace-item']") or \
                   soup.select("div[role='listitem']")

        for listing in listings:
            try:
                title_el = listing.select_one("span[dir='auto']")
                price_el = listing.select_one("[aria-label*='precio'], [class*='price']")
                link_el = listing.select_one("a[href*='/marketplace/item/']")

                if not link_el:
                    continue

                href = link_el.get("href", "")
                url = f"https://www.facebook.com{href}" if href.startswith("/") else href

                title = title_el.get_text(strip=True) if title_el else ""
                price_text = price_el.get_text(strip=True) if price_el else ""

                # Verificar que es inmueble de Uruguay
                if not any(kw in title.lower() for kw in ["punta", "maldonado", "uruguay", "barra", "uy"]):
                    continue

                from app.scrapers.base import ScrapedProperty
                yield ScrapedProperty(
                    source=self.SOURCE_NAME,
                    url=url,
                    title=title[:500],
                    price=float(re.sub(r'[^\d]', '', price_text)) if price_text else None,
                    currency="USD",
                )

            except Exception as e:
                self.logger.error("Error parseando Facebook listing", error=str(e))
