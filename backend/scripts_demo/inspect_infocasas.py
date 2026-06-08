"""Inspecciona la estructura de datos de InfoCasas para extracción real."""
import asyncio
import json
import re

import aiohttp

URL = "https://www.infocasas.com.uy/alquiler/casas-y-apartamentos/maldonado"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36"


async def main() -> None:
    conn = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=conn, headers={"User-Agent": UA}) as s:
        async with s.get(URL, timeout=25) as r:
            html = await r.text()

    print("bytes:", len(html))
    print("__NEXT_DATA__:", "__NEXT_DATA__" in html)
    print("__INITIAL_STATE__:", "__INITIAL_STATE__" in html)
    print("ld+json count:", html.count("application/ld+json"))

    # Extraer __NEXT_DATA__ si existe
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if m:
        data = json.loads(m.group(1))
        # Volcar las claves de nivel superior y buscar arrays de propiedades
        print("\n__NEXT_DATA__ keys:", list(data.keys()))
        pp = data.get("props", {}).get("pageProps", {})
        print("pageProps keys:", list(pp.keys())[:30])
        # Guardar para análisis
        with open("/tmp/infocasas_next.json", "w") as f:
            json.dump(data, f)
        print("→ guardado /tmp/infocasas_next.json")

    # ld+json
    for blk in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)[:3]:
        try:
            obj = json.loads(blk)
            t = obj.get("@type") if isinstance(obj, dict) else type(obj)
            print("ld+json @type:", t)
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
