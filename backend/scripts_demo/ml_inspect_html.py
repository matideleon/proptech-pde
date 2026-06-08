"""Inspecciona la estructura HTML de ML (vía Googlebot UA) para el parser."""
import asyncio
import re

import aiohttp
from bs4 import BeautifulSoup

GOOGLEBOT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
URL = "https://listado.mercadolibre.com.uy/inmuebles/alquiler/maldonado/"


async def main():
    conn = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=conn, headers={"User-Agent": GOOGLEBOT, "Accept": "text/html"}) as s:
        async with s.get(URL, timeout=30) as r:
            html = await r.text()

    soup = BeautifulSoup(html, "lxml")

    # Buscar contenedores de resultados
    cards = soup.select("li.ui-search-layout__item")
    print(f"cards (li.ui-search-layout__item): {len(cards)}")
    if not cards:
        cards = soup.select(".ui-search-result__wrapper, .poly-card")
        print(f"cards (poly-card): {len(cards)}")

    if cards:
        c = cards[0]
        print("\n=== Primer card: análisis de selectores ===")
        title = c.select_one(".poly-component__title, .ui-search-item__title, h2, a.poly-component__title")
        price = c.select_one(".andes-money-amount__fraction")
        cur = c.select_one(".andes-money-amount__currency-symbol")
        link = c.select_one("a.poly-component__title, a.ui-search-link, a[href*='MLU']")
        img = c.select_one("img")
        attrs = c.select(".poly-attributes_list__item, .ui-search-card-attributes__attribute, li.poly-attributes-list__item")
        loc = c.select_one(".poly-component__location, .ui-search-item__location")

        print(f"  title: {title.get_text(strip=True)[:55] if title else 'NO'}")
        print(f"  price: {price.get_text(strip=True) if price else 'NO'}  cur: {cur.get_text(strip=True) if cur else '?'}")
        print(f"  link : {(link.get('href') or '')[:60] if link else 'NO'}")
        print(f"  img  : {(img.get('data-src') or img.get('src') or '')[:55] if img else 'NO'}")
        print(f"  loc  : {loc.get_text(strip=True)[:45] if loc else 'NO'}")
        print(f"  attrs: {[a.get_text(strip=True) for a in attrs[:5]]}")

        # Mostrar clases reales del card para depurar
        print(f"\n  clases del card: {c.get('class')}")
        # primeros enlaces con MLU
        links = re.findall(r'href=\"(https://[^\"]*?MLU-?\d+[^\"]*?)\"', str(c))
        print(f"  links MLU en card: {links[:2]}")


if __name__ == "__main__":
    asyncio.run(main())
