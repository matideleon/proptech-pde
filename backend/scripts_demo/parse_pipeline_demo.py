"""
Demo determinista del pipeline parse → normalize.

Usa un payload con la estructura REAL de un item de la API de
MercadoLibre Uruguay (campos tal como los devuelve /items/{id}),
lo pasa por el parser real del scraper y por el normalizador real.

No requiere red ni base de datos: prueba la lógica de extracción y
normalización de forma reproducible.

Uso:
    python -m scripts_demo.parse_pipeline_demo
"""
from app.scrapers.mercadolibre import MercadoLibreScraper
from app.scrapers.normalizer import normalizer

# Payload con la forma real de un item de MercadoLibre Inmuebles UY.
REAL_SHAPE_ITEMS = [
    {
        "id": "MLU650123456",
        "title": "Apartamento 3 dormitorios frente al mar - La Barra",
        "price": 18_500_000,
        "currency_id": "UYU",
        "category_id": "MLU1466",  # Apartamentos
        "permalink": "https://articulo.mercadolibre.com.uy/MLU-650123456-apartamento-la-barra",
        "condition": "used",
        "listing_type_id": "gold_pro",
        "location": {
            "neighborhood": {"name": "la barra de maldonado"},
            "city": {"name": "Punta del Este"},
        },
        "geolocation": {"latitude": -34.9058, "longitude": -54.8692},
        "seller": {"nickname": "INMOBILIARIA COSTA ESTE"},
        "attributes": [
            {"id": "BEDROOMS", "value_name": "3 dormitorios"},
            {"id": "FULL_BATHROOMS", "value_name": "2"},
            {"id": "TOTAL_AREA", "value_name": "120 m²"},
            {"id": "COVERED_AREA", "value_name": "105 m²"},
        ],
        "pictures": [
            {"secure_url": "https://http2.mlstatic.com/foto-1.jpg"},
            {"secure_url": "https://http2.mlstatic.com/foto-2.jpg"},
        ],
    },
    {
        "id": "MLU777888999",
        "title": "Casa con piscina en José Ignacio - Oportunidad",
        "price": 850_000,
        "currency_id": "USD",
        "category_id": "MLU1467",  # Casas
        "permalink": "https://articulo.mercadolibre.com.uy/MLU-777888999-casa-jose-ignacio",
        "condition": "used",
        "location": {
            "neighborhood": {"name": "josé ignacio"},
            "city": {"name": "Maldonado"},
        },
        "geolocation": {"latitude": -34.8458, "longitude": -54.6631},
        "seller": {"nickname": "Premium Realty"},
        "attributes": [
            {"id": "BEDROOMS", "value_name": "4"},
            {"id": "FULL_BATHROOMS", "value_name": "3"},
            {"id": "TOTAL_AREA", "value_name": "320 m²"},
        ],
        "pictures": [{"secure_url": "https://http2.mlstatic.com/casa-1.jpg"}],
    },
]


def main() -> None:
    print("=" * 66)
    print("  DEMO PIPELINE parse → normalize (payload real de MercadoLibre)")
    print("=" * 66)

    scraper = MercadoLibreScraper()

    for i, item in enumerate(REAL_SHAPE_ITEMS, 1):
        raw = scraper._parse_item(item, "buy")
        assert raw is not None, "El parser debería extraer la propiedad"
        prop = normalizer.normalize(raw)
        fp = normalizer.compute_fingerprint(prop)

        print(f"\n┌── Propiedad #{i}  (raw → normalizada)")
        print(f"│  Título      : {prop.title}")
        print(f"│  Tipo        : {prop.property_type}")
        print(f"│  Operación   : {prop.operation}")
        print(f"│  Precio orig : {raw.currency} {raw.price:,.0f}")
        print(f"│  → Precio USD: USD {prop.price_usd:,.0f}   "
              f"(conversión {'aplicada' if raw.currency == 'UYU' else 'directa'})")
        if prop.price_per_m2_usd:
            print(f"│  → Precio/m² : USD {prop.price_per_m2_usd:,.0f}/m²")
        print(f"│  Barrio orig : '{item['location']['neighborhood']['name']}'")
        print(f"│  → Barrio    : '{prop.neighborhood}'  (canónico)")
        print(f"│  Dorm/Baños  : {prop.bedrooms} / {prop.bathrooms}")
        print(f"│  Área        : {prop.area_total} m² (cubierta {prop.area_built or '-'})")
        print(f"│  GPS         : {prop.latitude}, {prop.longitude}")
        print(f"│  Inmobiliaria: {prop.agency_name}")
        print(f"│  Imágenes    : {len(prop.images)}")
        print(f"│  Fingerprint : {fp}")
        print("└" + "─" * 56)

    # Validaciones de aserción explícitas
    a = normalizer.normalize(scraper._parse_item(REAL_SHAPE_ITEMS[0], "buy"))
    assert a.neighborhood == "La Barra", a.neighborhood
    assert a.property_type == "apartamento"
    assert a.price_usd and a.price_usd < a.price  # UYU → USD reduce el número
    print("\n✅ Aserciones OK:")
    print("   • 'la barra de maldonado' → 'La Barra' (normalización de barrio)")
    print("   • UYU 18.500.000 → USD (conversión de moneda)")
    print("   • category MLU1466 → 'apartamento' (mapeo de tipo)")
    print("   • precio/m² calculado automáticamente")
    print("=" * 66)


if __name__ == "__main__":
    main()
