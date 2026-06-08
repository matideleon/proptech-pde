"""
Scraper base con funcionalidades comunes:
- Rotación de user agents
- Rate limiting
- Reintentos automáticos
- Manejo de proxies
- Logging estructurado
"""
import asyncio
import hashlib
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("scraper")

# Pool de user agents
_ua = UserAgent()

# User agents extra para mayor variedad
EXTRA_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


@dataclass
class ScrapedProperty:
    """Datos crudos de una propiedad scrapeada."""
    # Identificación
    source: str
    external_id: Optional[str] = None
    url: str = ""

    # Clasificación
    property_type: str = "apartamento"
    operation: str = "venta"

    # Descripción
    title: str = ""
    description: str = ""

    # Precio
    price: Optional[float] = None
    currency: str = "USD"
    price_usd: Optional[float] = None          # calculado por el normalizer
    price_per_m2_usd: Optional[float] = None   # calculado por el normalizer
    expenses: Optional[float] = None
    expenses_currency: Optional[str] = None

    # Características
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    garages: Optional[int] = None
    area_total: Optional[float] = None
    area_built: Optional[float] = None
    floor: Optional[int] = None
    year_built: Optional[int] = None

    # Localización
    country: str = "Uruguay"
    department: str = "Maldonado"
    city: str = "Punta del Este"
    neighborhood: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Contacto
    agency_name: Optional[str] = None
    agency_id: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    contact_whatsapp: Optional[str] = None

    # Media
    images: List[str] = field(default_factory=list)
    amenities: List[str] = field(default_factory=list)

    # Fechas
    published_at: Optional[datetime] = None
    scraped_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Raw
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScraperStats:
    """Estadísticas de una ejecución de scraping."""
    source: str
    pages_scraped: int = 0
    properties_found: int = 0
    properties_new: int = 0
    properties_updated: int = 0
    errors: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None

    @property
    def duration_seconds(self) -> float:
        if self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return 0


class BaseScraper(ABC):
    """
    Clase base para todos los scrapers del sistema.

    Implementa:
    - Session HTTP reutilizable con headers correctos
    - Rotación automática de user agents
    - Rate limiting configurable
    - Reintentos con backoff exponencial
    - Manejo de proxies
    """

    SOURCE_NAME: str = "base"
    BASE_URL: str = ""
    DEFAULT_DELAY: float = 2.0

    def __init__(self):
        self.stats = ScraperStats(source=self.SOURCE_NAME)
        self._session: Optional[aiohttp.ClientSession] = None
        self.logger = get_logger(f"scraper.{self.SOURCE_NAME}")
        self._proxy_list = settings.proxy_list
        self._proxy_index = 0

    def _get_user_agent(self) -> str:
        """Rotación de user agent."""
        try:
            return _ua.random
        except Exception:
            return random.choice(EXTRA_USER_AGENTS)

    def _get_proxy(self) -> Optional[str]:
        """Obtener siguiente proxy en rotación."""
        if not settings.USE_PROXY or not self._proxy_list:
            return None
        proxy = self._proxy_list[self._proxy_index % len(self._proxy_list)]
        self._proxy_index += 1
        return proxy

    def _get_headers(self) -> Dict[str, str]:
        """Headers HTTP que simulan un browser real."""
        return {
            "User-Agent": self._get_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "es-UY,es;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtener o crear sesión HTTP."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=settings.SCRAPING_TIMEOUT)
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=3,
                ssl=False,
            )
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers=self._get_headers(),
            )
        return self._session

    async def _fetch(
        self,
        url: str,
        params: Optional[Dict] = None,
        max_retries: int = None,
    ) -> Optional[str]:
        """
        Fetch de URL con reintentos y backoff exponencial.

        Returns:
            HTML content o None si falla
        """
        max_retries = max_retries or settings.SCRAPING_MAX_RETRIES
        session = await self._get_session()

        for attempt in range(max_retries):
            try:
                # Rate limiting
                delay = random.uniform(settings.SCRAPING_DELAY_MIN, settings.SCRAPING_DELAY_MAX)
                if attempt > 0:
                    delay = delay * (2 ** attempt)  # backoff exponencial
                    self.logger.info(f"Reintento {attempt + 1}/{max_retries}", url=url, delay=delay)

                await asyncio.sleep(delay)

                # Rotar headers en cada intento
                session.headers.update(self._get_headers())

                proxy = self._get_proxy()

                async with session.get(url, params=params, proxy=proxy) as response:
                    if response.status == 200:
                        return await response.text()
                    elif response.status == 429:
                        # Rate limited — esperar más
                        wait = int(response.headers.get("Retry-After", 60))
                        self.logger.warning(f"Rate limited, esperando {wait}s", url=url)
                        await asyncio.sleep(wait)
                    elif response.status in (403, 401):
                        self.logger.warning(f"Bloqueado {response.status}", url=url)
                        # Rotar user agent agresivamente
                        session.headers.update({"User-Agent": self._get_user_agent()})
                        await asyncio.sleep(10)
                    elif response.status == 404:
                        self.logger.debug(f"No encontrado 404", url=url)
                        return None
                    else:
                        self.logger.warning(f"HTTP {response.status}", url=url)

            except aiohttp.ClientError as e:
                self.logger.warning(f"Error de red (intento {attempt+1})", url=url, error=str(e))
            except asyncio.TimeoutError:
                self.logger.warning(f"Timeout (intento {attempt+1})", url=url)
            except Exception as e:
                self.logger.error(f"Error inesperado", url=url, error=str(e))
                self.stats.errors += 1

        self.logger.error(f"Fallaron todos los reintentos", url=url)
        self.stats.errors += 1
        return None

    def _parse_html(self, html: str) -> BeautifulSoup:
        """Parsear HTML con BeautifulSoup."""
        return BeautifulSoup(html, "lxml")

    def _url_hash(self, url: str) -> str:
        """SHA256 hash de una URL para deduplicación."""
        return hashlib.sha256(url.encode()).hexdigest()

    def _property_fingerprint(self, prop: ScrapedProperty) -> str:
        """
        Fingerprint de una propiedad para deduplicación cross-source.
        Combina: tipo, operación, precio, barrio, dormitorios, área.
        """
        key_parts = [
            prop.property_type or "",
            prop.operation or "",
            str(int(prop.price or 0)),
            (prop.neighborhood or "").lower().strip(),
            str(prop.bedrooms or 0),
            str(int(prop.area_total or 0)),
        ]
        return hashlib.md5("|".join(key_parts).encode()).hexdigest()

    async def close(self) -> None:
        """Cerrar sesión HTTP."""
        if self._session and not self._session.closed:
            await self._session.close()

    @abstractmethod
    async def scrape(self) -> AsyncGenerator[ScrapedProperty, None]:
        """Scraper principal — debe ser implementado por cada portal."""
        raise NotImplementedError

    async def run(self) -> AsyncGenerator[ScrapedProperty, None]:
        """
        Correr el scraper como async generator.

        Actualiza `self.stats` durante la ejecución; las estadísticas
        finales quedan disponibles en `self.stats` tras agotar el generador
        (no se pueden retornar valores desde un async generator).
        """
        self.logger.info("🚀 Iniciando scraper", source=self.SOURCE_NAME)
        self.stats.started_at = datetime.now(timezone.utc)

        try:
            async for prop in self.scrape():
                self.stats.properties_found += 1
                yield prop
        except Exception as e:
            self.logger.error("Error en scraper", source=self.SOURCE_NAME, error=str(e))
            raise
        finally:
            self.stats.finished_at = datetime.now(timezone.utc)
            await self.close()
            self.logger.info(
                "✅ Scraping completado",
                source=self.SOURCE_NAME,
                found=self.stats.properties_found,
                pages=self.stats.pages_scraped,
                duration=f"{self.stats.duration_seconds:.1f}s",
                errors=self.stats.errors,
            )
