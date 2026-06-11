"""
Scraper autenticado de grupos PRIVADOS de Facebook (alquileres Punta del Este).

Usa la SESIÓN del usuario (cookies c_user + xs que el propio usuario extrae de
su navegador) contra mbasic.facebook.com — la versión HTML liviana sin JS, que
es la más estable para scraping con sesión. Cada post se clasifica con
`post_classifier` en oferta / demanda / otro.

⚠️  Esto usa contenido autenticado de grupos privados: viola los ToS de Facebook
y tiene riesgo de bloqueo de cuenta. El usuario lo activó conscientemente. Para
reducir el riesgo: rate limit alto, una sola pasada por corrida, sin acciones
de escritura (solo lectura del feed).

Configuración (en .env / EasyPanel env):
  FB_SESSION_COOKIE = "c_user=100xxxx; xs=xx%3Axxxx%3A..."
  FB_GROUP_IDS      = "1234567890,9876543210"   (IDs o slugs de los grupos)
"""
from __future__ import annotations

import asyncio
import random
import re
from dataclasses import asdict
from typing import AsyncGenerator, Dict, List, Optional

import aiohttp
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.logging import get_logger
from app.scrapers.post_classifier import ClassifiedPost, classify_post

logger = get_logger("scraper.fb_groups")

MBASIC = "https://mbasic.facebook.com"

# UA de navegador móvil real — mbasic responde mejor que con UA de bot.
_MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)


class FacebookGroupScraper:
    """Lee posts de grupos privados con la sesión del usuario."""

    SOURCE_NAME = "facebook_group"

    def __init__(
        self,
        session_cookie: Optional[str] = None,
        group_ids: Optional[List[str]] = None,
        max_posts_per_group: int = 40,
    ):
        self.session_cookie = (session_cookie or settings.fb_session_cookie or "").strip()
        raw_groups = group_ids if group_ids is not None else settings.fb_group_ids_list
        self.group_ids = [g.strip() for g in raw_groups if g.strip()]
        self.max_posts_per_group = max_posts_per_group
        self._session: Optional[aiohttp.ClientSession] = None

    # ─── HTTP ────────────────────────────────────────────────
    def _headers(self) -> Dict[str, str]:
        return {
            "User-Agent": _MOBILE_UA,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "es-UY,es;q=0.9",
            "Cookie": self.session_cookie,
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=settings.SCRAPING_TIMEOUT)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=aiohttp.TCPConnector(limit=4, ssl=False),
            )
        return self._session

    async def _fetch(self, url: str) -> Optional[str]:
        session = await self._get_session()
        try:
            await asyncio.sleep(random.uniform(settings.SCRAPING_DELAY_MIN, settings.SCRAPING_DELAY_MAX))
            async with session.get(url, headers=self._headers(), allow_redirects=True) as resp:
                html = await resp.text()
                if resp.status != 200:
                    logger.warning("HTTP no-200 en mbasic", url=url, status=resp.status)
                    return None
                # Si redirige al login, la sesión expiró
                if "login" in str(resp.url) or "Iniciá sesión" in html or "Log In" in html[:2000]:
                    logger.error("Sesión de Facebook inválida/expirada — refrescar FB_SESSION_COOKIE")
                    return None
                return html
        except Exception as e:  # noqa: BLE001
            logger.warning("Error al traer grupo", url=url, error=str(e))
            return None

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    # ─── NAVEGADOR (Playwright) ──────────────────────────────
    # m.facebook.com carga el feed por JS, así que para grupos usamos un
    # navegador headless que renderiza la página antes de parsear.
    def _browser_cookies(self) -> List[dict]:
        cookies = []
        for part in self.session_cookie.split(";"):
            if "=" in part:
                name, _, val = part.strip().partition("=")
                if name and val:
                    cookies.append({
                        "name": name.strip(), "value": val.strip(),
                        "domain": ".facebook.com", "path": "/",
                    })
        return cookies

    async def _fetch_browser(self, gid: str, scrolls: int = 4) -> Optional[str]:
        """Renderiza m.facebook.com/groups/{gid} con Chromium y devuelve el HTML."""
        try:
            from playwright.async_api import async_playwright
        except Exception as e:  # noqa: BLE001
            logger.error("Playwright no disponible", error=str(e))
            return None

        url = f"https://m.facebook.com/groups/{gid}"
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            try:
                ctx = await browser.new_context(
                    user_agent=_MOBILE_UA, locale="es-UY",
                    viewport={"width": 412, "height": 900},
                )
                await ctx.add_cookies(self._browser_cookies())
                page = await ctx.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                try:
                    await page.wait_for_selector('div[role="article"], article', timeout=15000)
                except Exception:  # noqa: BLE001
                    pass
                for _ in range(scrolls):
                    await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(1800)
                return await page.content()
            finally:
                await browser.close()

    async def diagnose(self, group_id: Optional[str] = None) -> dict:
        """Fetch de un grupo devolviendo qué respondió FB (para diagnóstico)."""
        gid = group_id or (self.group_ids[0] if self.group_ids else None)
        # Estado de configuración (sin exponer valores secretos)
        cfg = {
            "cookie_present": bool(self.session_cookie),
            "cookie_len": len(self.session_cookie),
            "has_c_user": "c_user=" in self.session_cookie,
            "has_xs": "xs=" in self.session_cookie,
            "source_combined": bool(settings.FB_SESSION_COOKIE and settings.FB_SESSION_COOKIE.strip()),
            "source_split": bool(settings.FB_C_USER and settings.FB_XS),
            "group_count": len(self.group_ids),
        }
        if not self.session_cookie:
            return {"error": "FB_SESSION_COOKIE vacía", "config": cfg}
        if not gid:
            return {"error": "FB_GROUP_IDS vacío", "config": cfg}

        # Render con navegador (m.facebook.com carga el feed por JS)
        try:
            html = await self._fetch_browser(gid)
        except Exception as e:  # noqa: BLE001
            return {"group": gid, "error": f"browser falló: {e}", "config": cfg}
        if not html:
            return {"group": gid, "error": "sin HTML (browser/sesión)", "config": cfg}
        status, final_url = 200, f"m.facebook.com/groups/{gid} (rendered)"

        low = html[:4000].lower()
        looks_login = ("login" in final_url.lower() or "iniciá sesión" in low
                       or "log in" in low or "iniciar sesión" in low)
        looks_checkpoint = "checkpoint" in final_url.lower() or "/checkpoint" in low
        soup = BeautifulSoup(html, "lxml")
        articles = (soup.find_all("article") or soup.select('div[role="article"]')
                    or soup.select("div[data-ft]"))
        # ¿Hay datos de posts embebidos en JSON dentro de la página?
        markers = {m: html.count(m) for m in
                   ['"message":', 'story_fbid', '"actors"', '"creation_time"',
                    'message_render', '"text":', 'feedback', '/groups/']}
        # Texto visible (lo que un parser DOM extraería)
        visible = soup.get_text(" ", strip=True)
        # Muestra de scripts con JSON (donde FB suele embeber el contenido)
        scripts = soup.find_all("script")
        big_scripts = sorted((len(s.get_text()) for s in scripts), reverse=True)[:3]
        return {
            "group": gid,
            "http_status": status,
            "final_url": final_url[:120],
            "html_len": len(html),
            "looks_like_login": looks_login,
            "looks_like_checkpoint": looks_checkpoint,
            "articles_found": len(articles),
            "title": (soup.title.get_text(strip=True)[:120] if soup.title else None),
            "visible_text_len": len(visible),
            "visible_sample": visible[200:700],
            "json_markers": markers,
            "script_count": len(scripts),
            "biggest_scripts": big_scripts,
            "parsed_posts": [
                {"kind": classify_post(p["text"]).kind, "text": p["text"][:120]}
                for p in self._parse_posts(html, gid)[:5]
            ],
            # Sonda de selectores para ubicar el contenedor de posts en m.facebook
            "selector_probe": {
                sel: len(soup.select(sel)) for sel in [
                    '[role="article"]', '[data-mcomponent]',
                    '[data-mcomponent="MContainer"]', '[data-tracking-duration-id]',
                    '[data-type="vscroller"]', '[data-type="vscroller"] > div',
                    '[aria-posinset]', 'div[data-actorid]', 'article',
                    'div[data-store]', '[data-gt]',
                ]
            },
        }

    # ─── PARSEO ──────────────────────────────────────────────
    @staticmethod
    def _extract_post_id(article, permalink: str) -> Optional[str]:
        # data-ft suele traer {"top_level_post_id": "..."} o {"mf_story_key": "..."}
        data_ft = article.get("data-ft", "") if hasattr(article, "get") else ""
        m = re.search(r'"(?:top_level_post_id|mf_story_key|story_fbid)"\s*:\s*"?(\d+)', data_ft)
        if m:
            return m.group(1)
        # Desde el permalink: /groups/x/permalink/{id}/  o  story_fbid={id}
        if permalink:
            m = re.search(r"/permalink/(\d+)", permalink) or re.search(r"story_fbid=(\d+)", permalink)
            if m:
                return m.group(1)
        return None

    def _parse_posts(self, html: str, group_id: str) -> List[dict]:
        """Extrae posts crudos del feed mbasic. Defensivo: varios fallbacks."""
        soup = BeautifulSoup(html, "lxml")
        posts: List[dict] = []

        # En mbasic cada historia es un <article> (o div[role=article] / div[data-ft]).
        articles = (
            soup.find_all("article")
            or soup.select('div[role="article"]')
            or soup.select("div[data-ft]")
        )

        for art in articles:
            text = art.get_text(" ", strip=True)
            if not text or len(text) < 15:
                continue

            # Permalink al post completo
            permalink = None
            for a in art.find_all("a", href=True):
                href = a["href"]
                if "/permalink/" in href or "story_fbid=" in href or "/groups/" in href and "/posts/" in href:
                    permalink = href if href.startswith("http") else f"{MBASIC}{href}"
                    break

            post_id = self._extract_post_id(art, permalink or "")
            if not post_id:
                # Fallback: hash del contenido (DOM renderizado sin permalink limpio).
                import hashlib
                post_id = "h" + hashlib.sha1(text[:200].encode("utf-8")).hexdigest()[:16]

            # Autor: primer link de perfil (no de grupo)
            author_name, author_profile = None, None
            for a in art.find_all("a", href=True):
                href, name = a["href"], a.get_text(strip=True)
                if name and ("profile.php" in href or re.match(r"^/[A-Za-z0-9.]+/?$", href)) and "/groups/" not in href:
                    author_name = name
                    author_profile = href if href.startswith("http") else f"https://facebook.com{href}"
                    break

            posts.append({
                "fb_post_id": f"{group_id}_{post_id}",
                "group_id": group_id,
                "permalink": permalink,
                "author_name": author_name,
                "author_profile": author_profile,
                "text": text,
            })

        return posts

    # ─── PIPELINE ────────────────────────────────────────────
    async def scrape(self) -> AsyncGenerator[dict, None]:
        """Recorre los grupos y yield-ea posts clasificados (oferta/demanda)."""
        if not self.session_cookie:
            logger.error("FB_SESSION_COOKIE no configurada — scraper de grupos deshabilitado")
            return
        if not self.group_ids:
            logger.error("FB_GROUP_IDS vacío — nada para scrapear")
            return

        for gid in self.group_ids:
            logger.info("🔍 Grupo FB", group=gid)
            html = await self._fetch_browser(gid)
            if not html:
                continue

            raw_posts = self._parse_posts(html, gid)[: self.max_posts_per_group]
            logger.info("Posts encontrados", group=gid, count=len(raw_posts))

            for raw in raw_posts:
                cls: ClassifiedPost = classify_post(raw["text"])
                if cls.kind == "otro":
                    continue  # descartar lo no relevante
                yield {
                    **raw,
                    "kind": cls.kind,
                    "operation": cls.operation,
                    "property_type": cls.property_type,
                    "period": cls.period,
                    "neighborhood": cls.neighborhood,
                    "price": cls.price,
                    "currency": cls.currency,
                    "bedrooms": cls.bedrooms,
                    "contact_phone": cls.contact_phone,
                    "confidence": cls.confidence,
                    "classified_by": "keywords",
                    "raw_data": {"matched": cls.matched},
                }


async def run_group_scraping(
    session_cookie: Optional[str] = None,
    group_ids: Optional[List[str]] = None,
) -> dict:
    """
    Ejecuta el scraping de grupos y persiste los posts nuevos (dedup por
    fb_post_id). Devuelve un resumen {found, new, by_kind}.
    """
    from sqlalchemy import select

    from app.db.database import get_db_context
    from app.models.group_post import GroupPost, PostKind

    scraper = FacebookGroupScraper(session_cookie=session_cookie, group_ids=group_ids)
    found = new = 0
    by_kind = {"oferta": 0, "demanda": 0}

    try:
        async with get_db_context() as db:
            async for post in scraper.scrape():
                found += 1
                existing = await db.execute(
                    select(GroupPost).where(GroupPost.fb_post_id == post["fb_post_id"])
                )
                if existing.scalar_one_or_none():
                    continue  # ya lo teníamos

                db.add(GroupPost(
                    source=scraper.SOURCE_NAME,
                    group_id=post["group_id"],
                    fb_post_id=post["fb_post_id"],
                    permalink=post.get("permalink"),
                    author_name=post.get("author_name"),
                    author_profile=post.get("author_profile"),
                    text=post["text"],
                    kind=PostKind(post["kind"]),
                    operation=post.get("operation"),
                    property_type=post.get("property_type"),
                    period=post.get("period"),
                    neighborhood=post.get("neighborhood"),
                    price=post.get("price"),
                    currency=post.get("currency"),
                    bedrooms=post.get("bedrooms"),
                    contact_phone=post.get("contact_phone"),
                    confidence=post.get("confidence", 0),
                    classified_by=post.get("classified_by", "keywords"),
                    raw_data=post.get("raw_data", {}),
                ))
                new += 1
                by_kind[post["kind"]] = by_kind.get(post["kind"], 0) + 1
            await db.commit()
    finally:
        await scraper.close()

    logger.info("✅ Scraping de grupos FB terminado", found=found, new=new, **by_kind)
    return {"found": found, "new": new, "by_kind": by_kind}
