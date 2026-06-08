"""Inspecciona la estructura HTML de Gallito (vía cloudscraper)."""
import re

import cloudscraper
from bs4 import BeautifulSoup

URL = "https://www.gallito.com.uy/inmuebles/alquileres/maldonado"


def main():
    s = cloudscraper.create_scraper(browser={"browser": "chrome", "platform": "darwin", "mobile": False})
    r = s.get(URL, timeout=40)
    html = r.text
    print(f"HTTP {r.status_code} | {len(html)} bytes")

    soup = BeautifulSoup(html, "lxml")

    # Probar selectores típicos de Gallito
    for sel in [
        "div.itemAviso", ".aviso", "[class*='Aviso']", ".cardAviso",
        "div.box-aviso", "a[href*='inmuebles']", ".js-item-aviso",
    ]:
        els = soup.select(sel)
        if els:
            print(f"  selector '{sel}': {len(els)} elementos")

    # Links a avisos
    links = list(dict.fromkeys(re.findall(r'href="(/[^"]*?-\d{6,}[^"]*?)"', html)))[:5]
    print("\nlinks aviso muestra:", links)

    # Buscar un contenedor con precio
    # Gallito suele usar clases como .precio, .us, span con U$S
    for sel in [".precio", "[class*='precio']", "[class*='Precio']", "span.us", ".dolar"]:
        els = soup.select(sel)
        if els:
            print(f"\nprecio selector '{sel}': {len(els)} | muestra: {[e.get_text(strip=True)[:15] for e in els[:4]]}")

    # Texto con U$S o $
    money = re.findall(r'(U\$S|\$U?)\s*([\d.]{3,})', html)[:6]
    print("\nmoney regex:", money)

    # Guardar primer card completo para análisis manual
    card = soup.select_one("div.itemAviso, .aviso, [class*='Aviso']")
    if card:
        print("\n=== primer card (clases) ===", card.get("class"))
        print(card.get_text(" | ", strip=True)[:200])


if __name__ == "__main__":
    main()
