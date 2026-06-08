"""Prueba conectividad y estructura de MercadoLibre Inmuebles (web)."""
import asyncio
import json
import re

import aiohttp

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36"

# Páginas web públicas de listado (no la API)
URLS = [
    "https://listado.mercadolibre.com.uy/inmuebles/departamentos/alquiler/maldonado/",
    "https://inmuebles.mercadolibre.com.uy/apartamentos/alquiler/maldonado/",
    "https://listado.mercadolibre.com.uy/inmuebles/alquiler/maldonado/",
]


async def main() -> None:
    conn = aiohttp.TCPConnector(ssl=False)
    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-UY,es;q=0.9",
    }
    async with aiohttp.ClientSession(connector=conn, headers=headers) as s:
        for url in URLS:
            try:
                async with s.get(url, timeout=25, allow_redirects=True) as r:
                    html = await r.text()
                    status = r.status
            except Exception as e:
                print(f"ERR {url[:55]}: {type(e).__name__}")
                continue

            print(f"\n{status}  {url[:60]}  ({len(html)} bytes)")
            if status != 200:
                continue
            # ¿Cuántas fichas (ui-search-layout__item / poly-card)?
            items = re.findall(r'ui-search-layout__item', html)
            poly = re.findall(r'poly-card', html)
            prices = re.findall(r'andes-money-amount__fraction[^>]*>([\d.]+)', html)
            links = re.findall(r'https://(?:articulo|apartamento|casa|departamento)[^"]*?MLU-?\d+', html)
            print(f"  items: {len(items)} | poly-card: {len(poly)} | precios: {len(prices)}")
            print(f"  precios muestra: {prices[:5]}")
            print(f"  links muestra: {list(dict.fromkeys(links))[:3]}")
            # ¿Hay JSON embebido?
            print("  __PRELOADED_STATE__:", "__PRELOADED_STATE__" in html or "preloadedState" in html)
            break  # con el primero que dé 200 alcanza


if __name__ == "__main__":
    asyncio.run(main())
