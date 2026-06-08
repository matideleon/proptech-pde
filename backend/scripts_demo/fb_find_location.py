"""Encuentra la ubicación correcta de Maldonado/PDE en FB Marketplace."""
import asyncio
import json
import re

import aiohttp

GB = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"

# Estrategias de URL para forzar ubicación Uruguay
CANDIDATES = [
    # lat/long de Maldonado/Punta del Este
    "https://www.facebook.com/marketplace/category/propertyrentals?latitude=-34.91&longitude=-54.96&radius=40",
    # slugs posibles
    "https://www.facebook.com/marketplace/punta-del-este/propertyrentals",
    "https://www.facebook.com/marketplace/montevideo/propertyrentals",
    # IDs de ciudad conocidos de FB (Maldonado UY)
    "https://www.facebook.com/marketplace/108125522545767/propertyrentals",  # Maldonado, Uruguay (a verificar)
]


def cities_in(html: str):
    blocks = re.findall(r'<script type="application/json"[^>]*>(.*?)</script>', html, re.DOTALL)
    cities = []
    prices = []

    def walk(o):
        if isinstance(o, dict):
            if "marketplace_listing_title" in o:
                loc = ((o.get("location") or {}).get("reverse_geocode") or {})
                cities.append(f"{loc.get('city')}, {loc.get('state')}")
                p = o.get("listing_price") or {}
                prices.append(p.get("formatted_amount"))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for it in o:
                walk(it)

    for b in blocks:
        try:
            walk(json.loads(b))
        except Exception:
            pass
    return cities, prices


async def main():
    for url in CANDIDATES:
        try:
            conn = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=conn, headers={"User-Agent": GB, "Accept-Language": "es-UY,es"}) as s:
                async with s.get(url, timeout=25, allow_redirects=True) as r:
                    html = await r.text()
            cities, prices = cities_in(html)
            uy = [c for c in cities if any(x in (c or "") for x in ["Maldonado", "Punta", "Uruguay", "Montevideo", "Rocha", "Canelones"])]
            print(f"\n{url[:70]}")
            print(f"  HTTP {r.status} | listings: {len(cities)} | UY: {len(uy)}")
            print(f"  ciudades muestra: {cities[:6]}")
            print(f"  precios muestra : {prices[:6]}")
        except Exception as e:
            print(f"\n{url[:70]}\n  ERR {type(e).__name__}: {str(e)[:50]}")


if __name__ == "__main__":
    asyncio.run(main())
