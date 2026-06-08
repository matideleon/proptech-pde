"""
Intenta scrapear MercadoLibre vía HTTP con cookies "calentadas".

Estrategia: visitar primero la home (obtener cookies de sesión), luego
pedir el listado con esas cookies + headers realistas, para intentar
sortear el muro account-verification.
"""
import asyncio
import re

import aiohttp

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

LISTINGS = [
    "https://listado.mercadolibre.com.uy/inmuebles/alquiler/maldonado/",
    "https://inmuebles.mercadolibre.com.uy/apartamentos/alquiler/maldonado/_DisplayType_LF",
]


async def attempt(label, headers, warm=False):
    jar = aiohttp.CookieJar(unsafe=True)
    conn = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=conn, headers=headers, cookie_jar=jar) as s:
        if warm:
            try:
                async with s.get("https://www.mercadolibre.com.uy/", timeout=25) as r:
                    await r.text()
                    print(f"  [{label}] home: HTTP {r.status}, cookies: {len(jar)}")
            except Exception as e:
                print(f"  [{label}] home ERR: {e}")

        for url in LISTINGS:
            try:
                async with s.get(url, timeout=25, allow_redirects=True) as r:
                    html = await r.text()
                    blocked = "account-verification" in str(r.url)
                    items = html.count("ui-search-layout__item") + html.count("poly-card__content")
                    print(f"  [{label}] {url[:48]} → HTTP {r.status} | bloqueado={blocked} | fichas={items} | {len(html)}b")
                    if not blocked and items > 0:
                        prices = re.findall(r'andes-money-amount__fraction[^>]*>([\d.]+)', html)
                        print(f"       ✅ DESBLOQUEADO — precios muestra: {prices[:5]}")
                        return True
            except Exception as e:
                print(f"  [{label}] {url[:48]} ERR: {type(e).__name__}")
    return False


async def main():
    print("=== Intento 1: UA Chrome + cookie warming ===")
    h1 = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-UY,es;q=0.9",
        "Referer": "https://www.mercadolibre.com.uy/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-site",
        "Upgrade-Insecure-Requests": "1",
    }
    if await attempt("warm", h1, warm=True):
        return

    print("\n=== Intento 2: Googlebot UA ===")
    h2 = {
        "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Accept": "text/html",
        "From": "googlebot(at)googlebot.com",
    }
    if await attempt("googlebot", h2):
        return

    print("\n❌ No se pudo sortear el muro por HTTP.")


if __name__ == "__main__":
    asyncio.run(main())
