"""Extrae la estructura JSON de listings de FB Marketplace (vía Googlebot)."""
import asyncio
import json
import re

import aiohttp

GB = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
URL = "https://www.facebook.com/marketplace/maldonado/propertyrentals"


async def main():
    conn = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=conn, headers={"User-Agent": GB, "Accept-Language": "es-UY"}) as s:
        async with s.get(URL, timeout=25) as r:
            html = await r.text()

    # FB embebe datos en bloques <script type="application/json">
    blocks = re.findall(r'<script type="application/json"[^>]*>(.*?)</script>', html, re.DOTALL)
    print(f"bloques JSON: {len(blocks)}")

    listings = []

    def walk(obj):
        """Buscar nodos que parezcan listings de marketplace."""
        if isinstance(obj, dict):
            # Un listing suele tener 'marketplace_listing_title' o 'listing' con id+price
            if "marketplace_listing_title" in obj:
                listings.append(obj)
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for it in obj:
                walk(it)

    for blk in blocks:
        try:
            data = json.loads(blk)
            walk(data)
        except Exception:
            continue

    print(f"listings encontrados: {len(listings)}")
    if listings:
        l = listings[0]
        print("\n=== KEYS de un listing ===")
        print(list(l.keys()))
        print("\n=== Ejemplo ===")
        print(json.dumps(l, indent=1, ensure_ascii=False)[:1200])

    # Guardar muestra para construir el parser
    with open("/tmp/fb_listings.json", "w") as f:
        json.dump(listings[:20], f, ensure_ascii=False)
    print(f"\n→ {len(listings[:20])} listings guardados en /tmp/fb_listings.json")


if __name__ == "__main__":
    asyncio.run(main())
