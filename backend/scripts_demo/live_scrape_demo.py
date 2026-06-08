"""
Demo en vivo del pipeline de scraping + normalización.

Hace una consulta real a la API pública de MercadoLibre Uruguay,
normaliza los resultados con el pipeline real del sistema y los muestra.
No requiere base de datos.

Uso:
    python -m scripts_demo.live_scrape_demo
"""
import asyncio
import json

from app.scrapers.base import ScrapedProperty
from app.scrapers.mercadolibre import (
    ML_API_BASE,
    ML_CATEGORY_INMUEBLES,
    ML_SITE_ID,
    MercadoLibreScraper,
)
from app.scrapers.normalizer import normalizer


async def main() -> None:
    print("=" * 64)
    print("  DEMO EN VIVO — PropTech PDE")
    print("  Scraping real: MercadoLibre Inmuebles Uruguay (Maldonado)")
    print("=" * 64)

    scraper = MercadoLibreScraper()

    # Una sola página de búsqueda real (venta en Maldonado)
    data = await scraper._search_page(
        state_id="TUxVUE1BTDc4OTU",  # Maldonado
        operation="buy",
        offset=0,
    )

    if not data:
        print("\n⚠️  La API no devolvió datos (rate-limit o red). Reintentá luego.")
        await scraper.close()
        return

    results = data.get("results", [])
    paging = data.get("paging", {})
    print(f"\n✅ Conexión OK — total disponibles en Maldonado: {paging.get('total', 0):,}")
    print(f"   Propiedades en esta página: {len(results)}\n")

    shown = 0
    for item in results[:5]:
        raw: ScrapedProperty = scraper._parse_item(item, "buy")
        if not raw:
            continue
        # Pipeline real de normalización
        prop = normalizer.normalize(raw)
        fp = normalizer.compute_fingerprint(prop)
        shown += 1

        print(f"┌── Propiedad #{shown}")
        print(f"│  Título     : {prop.title[:60]}")
        print(f"│  Tipo/Oper. : {prop.property_type} / {prop.operation}")
        print(f"│  Precio     : {prop.currency} {prop.price:,.0f}" if prop.price else "│  Precio     : Consultar")
        if prop.price_usd:
            print(f"│  Precio USD : USD {prop.price_usd:,.0f}")
        if prop.price_per_m2_usd:
            print(f"│  Precio/m²  : USD {prop.price_per_m2_usd:,.0f}/m²")
        print(f"│  Dorm/Baños : {prop.bedrooms or '-'} / {prop.bathrooms or '-'}")
        print(f"│  Área       : {prop.area_total or '-'} m²")
        print(f"│  Barrio     : {prop.neighborhood or '-'}")
        if prop.latitude:
            print(f"│  GPS        : {prop.latitude:.4f}, {prop.longitude:.4f}")
        print(f"│  Imágenes   : {len(prop.images)}")
        print(f"│  Fingerprint: {fp[:16]}...")
        print(f"│  URL        : {prop.url[:60]}")
        print("└" + "─" * 50 + "\n")

    await scraper.close()

    print("=" * 64)
    print(f"  ✅ {shown} propiedades reales scrapeadas y normalizadas")
    print("     (precio→USD, barrio canónico, fingerprint anti-duplicados)")
    print("=" * 64)


if __name__ == "__main__":
    asyncio.run(main())
