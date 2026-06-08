"""Sondeo de Facebook Marketplace: ¿hay alguna vía de acceso sin login?"""
import asyncio
import re

import aiohttp

GOOGLEBOT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
CHROME = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36"

# Maldonado/Punta del Este location id en FB ~ buscamos por categoría property rentals
TARGETS = [
    ("Marketplace cat (Googlebot)", "https://www.facebook.com/marketplace/category/propertyrentals", GOOGLEBOT),
    ("Marketplace cat (Chrome)", "https://www.facebook.com/marketplace/category/propertyrentals", CHROME),
    ("mbasic", "https://mbasic.facebook.com/marketplace/", CHROME),
    ("m.facebook", "https://m.facebook.com/marketplace/category/propertyrentals", CHROME),
    ("Marketplace Maldonado", "https://www.facebook.com/marketplace/maldonado/propertyrentals", GOOGLEBOT),
]


def analyze(html: str) -> dict:
    low = html.lower()
    return {
        "bytes": len(html),
        "login_wall": any(x in low for x in ["iniciar sesión", "log in to facebook", "you must log in", "inicia sesión", "iniciá sesión"]),
        "has_listings": ("marketplace_search" in low or "/marketplace/item/" in low),
        "items": len(re.findall(r'/marketplace/item/\d+', html)),
        "prices": re.findall(r'(?:US?\$|UYU|\$U?)\s?[\d.,]+', html)[:4],
    }


async def main():
    for label, url, ua in TARGETS:
        try:
            conn = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=conn, headers={"User-Agent": ua, "Accept-Language": "es-UY,es;q=0.9"}) as s:
                async with s.get(url, timeout=25, allow_redirects=True) as r:
                    html = await r.text()
                    info = analyze(html)
                    print(f"[{label}] HTTP {r.status} | final={str(r.url)[:45]}")
                    print(f"    {info}")
                    # Buscar datos embebidos tipo listing
                    if "marketplace_listing_title" in html or "listing_price" in html:
                        print("    ⚠️  hay claves de listing embebidas en el HTML")
        except Exception as e:
            print(f"[{label}] ERR {type(e).__name__}: {str(e)[:50]}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
