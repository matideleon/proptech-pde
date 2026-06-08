"""Busca el teléfono/whatsapp real en los datos de InfoCasas."""
import asyncio
import json
import re

import aiohttp

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36"
LIST = "https://www.infocasas.com.uy/alquiler/casas-y-apartamentos/punta-del-este"


def find_phones(obj, path="", out=None):
    if out is None:
        out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if any(x in k.lower() for x in ["phone", "whatsapp", "telefono", "celular", "contact", "mobile"]):
                out.append((f"{path}.{k}", v if not isinstance(v, (dict, list)) else type(v).__name__))
            find_phones(v, f"{path}.{k}", out)
    elif isinstance(obj, list):
        for i, it in enumerate(obj[:2]):
            find_phones(it, f"{path}[{i}]", out)
    return out


async def main():
    conn = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=conn, headers={"User-Agent": UA}) as s:
        async with s.get(LIST, timeout=25) as r:
            html = await r.text()

    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    data = json.loads(m.group(1))
    items = data["props"]["pageProps"]["fetchResult"]["searchFast"]["data"]
    p = items[0]

    print("=== OWNER del primer item ===")
    print(json.dumps(p.get("owner", {}), indent=1, ensure_ascii=False)[:1500])
    print("\n=== Campos con phone/whatsapp en el item ===")
    for path, val in find_phones(p):
        print(f"  {path} = {val}")

    # Ahora la ficha de detalle
    link = p.get("link")
    detail_url = f"https://www.infocasas.com.uy{link}"
    print(f"\n=== Ficha de detalle: {detail_url} ===")
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False), headers={"User-Agent": UA}) as s:
        async with s.get(detail_url, timeout=25) as r:
            dhtml = await r.text()
    # wa.me / tel: en el HTML
    print("  wa.me:", re.findall(r'wa\.me/(\d+)', dhtml)[:3])
    print("  tel: :", re.findall(r'tel:\+?([\d\s]+)', dhtml)[:3])
    print("  whatsapp api:", re.findall(r'api\.whatsapp\.com/send\?phone=(\d+)', dhtml)[:3])
    dm = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', dhtml, re.DOTALL)
    if dm:
        ddata = json.loads(dm.group(1))
        prop = ddata["props"]["pageProps"].get("fetchResult", {}).get("property", {})
        if isinstance(prop, list):
            prop = prop[0] if prop else {}
        print("\n  === phones en ficha de detalle ===")
        for path, val in find_phones(prop):
            print(f"    {path} = {val}")


if __name__ == "__main__":
    asyncio.run(main())
