"""Sondea Gallito Luis: ¿qué UA/URL devuelve listings de alquiler?"""
import asyncio
import re

import aiohttp

GOOGLEBOT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
CHROME = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36"

# Distintas rutas de alquiler en Maldonado
URLS = [
    "https://www.gallito.com.uy/inmuebles/casas-y-apartamentos/alquiler/maldonado! td=2",
    "https://www.gallito.com.uy/inmuebles/alquileres/maldonado",
    "https://www.gallito.com.uy/inmuebles/apartamentos/alquiler/maldonado",
    "https://www.gallito.com.uy/inmuebles?currentpage=1&tipo=2&departamento=Maldonado",
]


def analyze(html: str) -> dict:
    return {
        "bytes": len(html),
        # contenedores típicos de Gallito
        "cards_aviso": html.count("aviso") ,
        "url_avisos": len(set(re.findall(r'/(?:inmuebles|apartamentos|casas)[^"\s]*?-(\d{6,})', html))),
        "precios": re.findall(r'(?:U\$S|\$U?)\s?[\d.]{3,}', html)[:5],
        "next_data": "__NEXT_DATA__" in html,
        "blocked": ("captcha" in html.lower() or "forbidden" in html.lower() or len(html) < 8000),
    }


async def main():
    for ua_name, ua in [("Googlebot", GOOGLEBOT), ("Chrome", CHROME)]:
        print(f"\n========= UA: {ua_name} =========")
        for url in URLS:
            try:
                conn = aiohttp.TCPConnector(ssl=False)
                async with aiohttp.ClientSession(connector=conn, headers={"User-Agent": ua, "Accept-Language": "es-UY,es"}) as s:
                    async with s.get(url, timeout=25, allow_redirects=True) as r:
                        html = await r.text()
                        info = analyze(html)
                        print(f"  HTTP {r.status} | {url[:58]}")
                        print(f"      {info}")
            except Exception as e:
                print(f"  ERR {url[:58]}: {type(e).__name__}")


if __name__ == "__main__":
    asyncio.run(main())
