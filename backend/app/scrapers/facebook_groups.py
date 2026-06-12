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
            "looks_like_logged_out": self._looks_logged_out(html),
            "looks_like_checkpoint": looks_checkpoint,
            "articles_found": len(articles),
            "title": (soup.title.get_text(strip=True)[:120] if soup.title else None),
            "visible_text_len": len(visible),
            "visible_sample": visible[200:700],
            "json_markers": markers,
            "script_count": len(scripts),
            "biggest_scripts": big_scripts,
            "parsed_posts": [
                {"kind": classify_post(p["text"]).kind, "text": p["text"][:120],
                 "permalink": p.get("permalink")}
                for p in self._parse_posts(html, gid)[:5]
            ],
            # Muestra de hrefs dentro de los primeros contenedores de post
            "post_hrefs": [
                [a.get("href") for a in art.find_all("a", href=True)][:8]
                for art in soup.select('[data-type="vscroller"] > div')[4:7]
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
    # Substrings de portales inmobiliarios que pueden aparecer en posts de grupos.
    # Se chequean como substring, por lo que cualquier subdominio (articulo., www.)
    # también matchea (p.ej. articulo.mercadolibre.com.uy contiene mercadolibre.com.uy).
    _PROPERTY_DOMAINS = (
        "facebook.com/marketplace/item/",
        "infocasas.com.uy/",
        "mercadolibre.com.uy/",
        "gallito.com.uy/",
        "properati.com",
        "zonaprop.com.uy/",
    )

    # Regex genérico para cualquier URL http(s) en texto plano.
    _URL_IN_TEXT = re.compile(r"https?://[^\s\"'<>)\]]+")

    @staticmethod
    def _unwrap_fb_redirect(href: str) -> str:
        """FB envuelve links externos en l.facebook.com/l.php?u=<url-encoded>."""
        if "l.facebook.com" in href or "/l.php" in href:
            m = re.search(r"[?&]u=([^&]+)", href)
            if m:
                import urllib.parse
                return urllib.parse.unquote(m.group(1))
        return href

    def _extract_external_links(self, article, raw_html_text: str) -> List[str]:
        """
        Extrae URLs de portales inmobiliarios que aparecen en un post.
        Busca tanto en atributos href como en texto plano.
        """
        seen: set = set()
        links: List[str] = []

        def _add(url: str) -> None:
            url = self._unwrap_fb_redirect(url)
            # Limpiar parámetros de tracking y trailing slashes
            url = re.sub(r"[?#].*$", "", url).rstrip("/")
            if (url.startswith("http")
                    and any(d in url for d in self._PROPERTY_DOMAINS)
                    and url not in seen):
                seen.add(url)
                links.append(url)

        # 1. Atributos href de todos los <a> en el artículo
        for a in article.find_all("a", href=True):
            _add(a["href"])

        # 2. URLs en texto plano del post (links pegados sin hipervínculo)
        for m in self._URL_IN_TEXT.finditer(raw_html_text):
            _add(m.group(0))

        return links

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

    @staticmethod
    def _canonical_permalink(group_id: str, post_id: Optional[str], raw: Optional[str]) -> Optional[str]:
        """
        URL canónica al post de Facebook, que abre bien en desktop y móvil.

        - Con un post_id numérico real → /groups/{gid}/posts/{id}/ (formato estándar).
        - Si no, normaliza el host del permalink crudo (mbasic/m/web → www).
        - Sin nada utilizable → link al grupo (mejor que nada).
        """
        if post_id and post_id.isdigit():
            return f"https://www.facebook.com/groups/{group_id}/posts/{post_id}/"
        if raw:
            return re.sub(
                r"https?://(?:mbasic|m|web|free)\.facebook\.com",
                "https://www.facebook.com",
                raw,
            )
        return f"https://www.facebook.com/groups/{group_id}"

    # Markers de UI que indican que un item NO es un post real.
    _UI_NOISE = (
        "Escribe algo", "Crear publicación", "ORDENAR", "Grupo público",
        "Grupo privado", "Invitar", "Actividad reciente", "Videos Comunicados",
        "miembros", "Unirte al grupo", "Sugerencias",
        # Vista pública/deslogueada de FB (no son posts, son el encabezado del grupo
        # y el muro de login que aparece cuando la cookie de sesión está vencida).
        "Información sobre este grupo", "Hay más contenido para ver",
        "Iniciar sesión", "Inicia sesión", "Crear cuenta nueva",
    )

    # Señales de que FB sirvió la vista DESLOGUEADA (cookie vencida/inválida):
    # solo se ve la descripción del grupo + un gate de login, sin el feed real.
    _LOGGED_OUT_MARKERS = (
        "Hay más contenido para ver",
        "Mira más fotos, videos y novedades",
        "Iniciar sesión Crear cuenta nueva",
        "Inicia sesión o crea una cuenta",
    )

    def _looks_logged_out(self, html: str) -> bool:
        """¿FB devolvió la vista pública/deslogueada (sin feed) por cookie inválida?"""
        # Si no hay ningún marcador de contenido de post Y aparece el gate de login.
        has_post_data = any(m in html for m in ('story_fbid', '"creation_time"', 'feedback'))
        has_login_gate = any(m in html for m in self._LOGGED_OUT_MARKERS)
        return has_login_gate and not has_post_data

    @staticmethod
    def _clean_post_text(text: str) -> str:
        """Limpia el texto de un post: glifos de iconos, footer y timestamps."""
        # Quitar glifos de la Private Use Area (iconos de la fuente de FB)
        text = "".join(
            c for c in text
            if not ("" <= c <= "" or "\U000f0000" <= c <= "\U0010ffff")
        )
        # Cortar el footer de interacción
        for marker in ("Ver publicación", "Me gusta Comentar", "Comentar Compartir",
                       "Ver más comentarios", "Todas las reacciones", "Comentar como"):
            i = text.find(marker)
            if i > 0:
                text = text[:i]
        # Quitar tokens de UI y timestamps sueltos
        text = re.sub(
            r"(Seguir|Colaborador (?:en ascenso|destacado)|Hace un momento|"
            r"Me gusta|Comentar|Compartir|Reacciona|Ver traducción)", " ", text)
        text = re.sub(r"\b\d+\s*(?:min|h|d|sem|año|años)\b", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _parse_posts(self, html: str, group_id: str) -> List[dict]:
        """Extrae posts del feed renderizado de m.facebook.com (MComponent)."""
        soup = BeautifulSoup(html, "lxml")
        posts: List[dict] = []

        # m.facebook.com renderiza el feed como hijos directos de un "vscroller".
        articles = (
            soup.select('[data-type="vscroller"] > div')
            or soup.find_all("article")
            or soup.select('div[role="article"]')
            or soup.select("div[data-ft]")
        )

        seen_text = set()
        for art in articles:
            raw = art.get_text(" ", strip=True)
            if not raw or any(ui in raw[:80] for ui in self._UI_NOISE):
                continue
            text = self._clean_post_text(raw)
            if len(text) < 25:
                continue
            # Dedup dentro de la misma página
            key = text[:80]
            if key in seen_text:
                continue
            seen_text.add(key)

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

            # Permalink canónico (www.facebook.com) — abre el post en cualquier device.
            permalink = self._canonical_permalink(group_id, post_id, permalink)

            # Autor: primer link de perfil (no de grupo)
            author_name, author_profile = None, None
            for a in art.find_all("a", href=True):
                href, name = a["href"], a.get_text(strip=True)
                if name and ("profile.php" in href or re.match(r"^/[A-Za-z0-9.]+/?$", href)) and "/groups/" not in href:
                    author_name = name
                    author_profile = href if href.startswith("http") else f"https://facebook.com{href}"
                    break

            # Links externos (Marketplace, portales) presentes en el post
            external_links = self._extract_external_links(art, str(art))

            posts.append({
                "fb_post_id": f"{group_id}_{post_id}",
                "group_id": group_id,
                "permalink": permalink,
                "author_name": author_name,
                "author_profile": author_profile,
                "text": text,
                "external_links": external_links,
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

        try:
            from playwright.async_api import async_playwright
        except Exception as e:  # noqa: BLE001
            logger.error("Playwright no disponible", error=str(e))
            return

        # Un solo navegador reutilizado para todos los grupos (eficiente).
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

                for gid in self.group_ids:
                    logger.info("🔍 Grupo FB", group=gid)
                    try:
                        await page.goto(f"https://m.facebook.com/groups/{gid}",
                                        wait_until="domcontentloaded", timeout=45000)
                        try:
                            await page.wait_for_selector('[data-type="vscroller"]', timeout=12000)
                        except Exception:  # noqa: BLE001
                            pass
                        for _ in range(4):
                            await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                            await page.wait_for_timeout(1800)
                        html = await page.content()
                    except Exception as e:  # noqa: BLE001
                        logger.warning("Grupo falló", group=gid, error=str(e))
                        continue

                    # Si FB sirvió la vista deslogueada (cookie vencida), NO hay feed:
                    # solo la descripción del grupo + gate de login. No guardar basura.
                    if self._looks_logged_out(html):
                        logger.error(
                            "⚠️  Facebook devolvió la vista DESLOGUEADA — FB_SESSION_COOKIE "
                            "vencida o inválida. Refrescá c_user+xs desde el navegador. "
                            "Sin sesión válida no se ven las publicaciones del grupo.",
                            group=gid,
                        )
                        continue

                    raw_posts = self._parse_posts(html, gid)[: self.max_posts_per_group]
                    logger.info("Posts encontrados", group=gid, count=len(raw_posts))

                    for raw in raw_posts:
                        cls: ClassifiedPost = classify_post(raw["text"])
                        if cls.kind == "otro":
                            continue
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
            finally:
                await browser.close()


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
                    external_links=post.get("external_links") or [],
                    raw_data=post.get("raw_data", {}),
                ))
                new += 1
                by_kind[post["kind"]] = by_kind.get(post["kind"], 0) + 1
            await db.commit()
    finally:
        await scraper.close()

    logger.info("✅ Scraping de grupos FB terminado", found=found, new=new, **by_kind)
    return {"found": found, "new": new, "by_kind": by_kind}
