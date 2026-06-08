"""
Seeds de base de datos — datos iniciales para desarrollo y testing.
"""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from app.core.logging import get_logger
from app.core.security import hash_password
from app.db.database import get_db_context
from app.models.user import User, UserRole
from app.models.zone import Zone, PUNTA_DEL_ESTE_ZONES

logger = get_logger("seeds")


async def seed_users():
    """Crear usuarios iniciales."""
    async with get_db_context() as db:
        from sqlalchemy import select

        # Admin
        existing = await db.execute(
            select(User).where(User.email == "admin@proptech.uy")
        )
        if not existing.scalar_one_or_none():
            admin = User(
                email="admin@proptech.uy",
                full_name="Admin PropTech",
                hashed_password=hash_password("admin123"),
                role=UserRole.SUPER_ADMIN,
                is_active=True,
                is_verified=True,
                alert_email=True,
                alert_whatsapp=True,
                alert_telegram=True,
            )
            db.add(admin)

            # Analyst
            analyst = User(
                email="analista@proptech.uy",
                full_name="Analista de Mercado",
                hashed_password=hash_password("analyst123"),
                role=UserRole.ANALYST,
                is_active=True,
                is_verified=True,
            )
            db.add(analyst)

            # Agent
            agent = User(
                email="agente@proptech.uy",
                full_name="Corredor Inmobiliario",
                hashed_password=hash_password("agent123"),
                role=UserRole.AGENT,
                is_active=True,
                is_verified=True,
                phone="+59898123456",
            )
            db.add(agent)

            await db.commit()
            logger.info("✅ Usuarios creados")
        else:
            logger.info("Usuarios ya existen, saltando...")


async def seed_zones():
    """Crear zonas/barrios de Punta del Este."""
    async with get_db_context() as db:
        from sqlalchemy import select
        from slugify import slugify  # noqa: F401

        existing = await db.execute(select(Zone).limit(1))
        if existing.scalar_one_or_none():
            logger.info("Zonas ya existen, saltando...")
            return

        for zone_data in PUNTA_DEL_ESTE_ZONES:
            zone = Zone(
                name=zone_data["name"],
                slug=zone_data["slug"],
                latitude=zone_data.get("latitude"),
                longitude=zone_data.get("longitude"),
                tier=zone_data.get("tier", "standard"),
                is_active=True,
                priority=10 if zone_data.get("tier") == "premium" else 5,
            )
            db.add(zone)

        await db.commit()
        logger.info(f"✅ {len(PUNTA_DEL_ESTE_ZONES)} zonas creadas")


async def seed_sample_properties():
    """Crear propiedades de ejemplo para testing."""
    async with get_db_context() as db:
        from sqlalchemy import select
        from app.models.property import (
            Property, PropertyImage, PriceHistory,
            PropertyStatus, ScrapingSource
        )
        import uuid

        existing = await db.execute(select(Property).limit(1))
        if existing.scalar_one_or_none():
            logger.info("Propiedades ya existen, saltando...")
            return

        # Foco de negocio: alquileres UYU 20.000–40.000 (1 USD = 40 UYU → USD 500–1.000).
        # Precios en UYU; price_usd se calcula con la tasa 40.
        def _usd(uyu: int) -> Decimal:
            return Decimal(round(uyu / 40))

        sample_properties = [
            {
                "source": "mercadolibre",
                "external_id": "MLU-RENT-001",
                "url": "https://www.mercadolibre.com.uy/alquiler-maldonado-centro-1",
                "property_type": "apartamento",
                "operation": "alquiler",
                "title": "Apartamento 1 dormitorio - Maldonado Centro",
                "description": "Cómodo apartamento de 1 dormitorio a pasos de la peatonal. Ideal para estudiante o pareja. Disponible todo el año.",
                "price": Decimal("22000"),
                "price_usd": _usd(22000),       # USD 550
                "currency": "UYU",
                "price_per_m2_usd": _usd(22000) / Decimal("45"),
                "bedrooms": 1,
                "bathrooms": 1,
                "area_total": Decimal("45"),
                "neighborhood": "Maldonado Centro",
                "city": "Maldonado",
                "latitude": -34.9011,
                "longitude": -54.9617,
                "ai_score": 72.0,
                "ai_premium": False,
                "ai_opportunity": True,
                "ai_tags": ["anual", "centrico", "economico", "buena_relacion"],
                "ai_summary": "Alquiler anual económico y bien ubicado en Maldonado Centro.",
                "amenities_raw": ["cocina_equipada", "calefon", "balcon"],
            },
            {
                "source": "infocasas",
                "external_id": "IC-RENT-002",
                "url": "https://www.infocasas.com.uy/alquiler-pde-centro-2",
                "property_type": "apartamento",
                "operation": "alquiler",
                "title": "Monoambiente amoblado - Punta del Este Centro",
                "description": "Monoambiente totalmente amoblado en la península. A 3 cuadras de Gorlero y de la playa Mansa. Alquiler anual.",
                "price": Decimal("28000"),
                "price_usd": _usd(28000),       # USD 700
                "currency": "UYU",
                "price_per_m2_usd": _usd(28000) / Decimal("38"),
                "bedrooms": 0,
                "bathrooms": 1,
                "area_total": Decimal("38"),
                "neighborhood": "Punta del Este Centro",
                "city": "Punta del Este",
                "latitude": -34.9633,
                "longitude": -54.9367,
                "ai_score": 78.0,
                "ai_premium": False,
                "ai_opportunity": True,
                "ai_tags": ["amoblado", "peninsula", "anual", "cerca_playa"],
                "ai_summary": "Monoambiente amoblado en la península, excelente para alquiler anual.",
                "amenities_raw": ["amoblado", "wifi", "cocina_equipada"],
            },
            {
                "source": "gallito",
                "external_id": "G-RENT-003",
                "url": "https://www.gallito.com.uy/alquiler-maldonado-3",
                "property_type": "apartamento",
                "operation": "alquiler",
                "title": "Apartamento 2 dormitorios - Maldonado",
                "description": "Apartamento de 2 dormitorios con patio, zona tranquila de Maldonado. Apto para familia, alquiler anual.",
                "price": Decimal("35000"),
                "price_usd": _usd(35000),       # USD 875
                "currency": "UYU",
                "price_per_m2_usd": _usd(35000) / Decimal("65"),
                "bedrooms": 2,
                "bathrooms": 1,
                "area_total": Decimal("65"),
                "neighborhood": "Maldonado Centro",
                "city": "Maldonado",
                "latitude": -34.9011,
                "longitude": -54.9617,
                "ai_score": 75.0,
                "ai_premium": False,
                "ai_opportunity": False,
                "ai_tags": ["familiar", "patio", "anual"],
                "ai_summary": "Alquiler familiar de 2 dormitorios en zona tranquila.",
                "amenities_raw": ["patio", "cocina_equipada", "lavadero"],
            },
            {
                "source": "mercadolibre",
                "external_id": "MLU-RENT-004",
                "url": "https://www.mercadolibre.com.uy/alquiler-pinares-4",
                "property_type": "apartamento",
                "operation": "alquiler",
                "title": "Apartamento 2 dormitorios - Pinares",
                "description": "Luminoso apartamento en Pinares, a metros de la playa Brava. Edificio con seguridad. Alquiler anual.",
                "price": Decimal("38000"),
                "price_usd": _usd(38000),       # USD 950
                "currency": "UYU",
                "price_per_m2_usd": _usd(38000) / Decimal("70"),
                "bedrooms": 2,
                "bathrooms": 2,
                "garages": 1,
                "area_total": Decimal("70"),
                "neighborhood": "Pinares",
                "city": "Punta del Este",
                "latitude": -34.9750,
                "longitude": -54.9450,
                "ai_score": 80.0,
                "ai_premium": False,
                "ai_opportunity": True,
                "ai_tags": ["cerca_playa", "seguridad", "garaje", "anual"],
                "ai_summary": "Buen alquiler anual en Pinares cerca de la playa Brava.",
                "amenities_raw": ["seguridad_24h", "garaje", "ascensor"],
            },
            {
                "source": "infocasas",
                "external_id": "IC-RENT-005",
                "url": "https://www.infocasas.com.uy/alquiler-san-rafael-5",
                "property_type": "apartamento",
                "operation": "alquiler",
                "title": "Apartamento 1 dormitorio - San Rafael",
                "description": "Apartamento de 1 dormitorio en San Rafael, zona residencial y arbolada. Alquiler anual.",
                "price": Decimal("25000"),
                "price_usd": _usd(25000),       # USD 625
                "currency": "UYU",
                "price_per_m2_usd": _usd(25000) / Decimal("48"),
                "bedrooms": 1,
                "bathrooms": 1,
                "area_total": Decimal("48"),
                "neighborhood": "San Rafael",
                "city": "Punta del Este",
                "latitude": -34.9583,
                "longitude": -54.9917,
                "ai_score": 70.0,
                "ai_premium": False,
                "ai_opportunity": False,
                "ai_tags": ["residencial", "anual", "tranquilo"],
                "ai_summary": "Alquiler anual de 1 dormitorio en zona residencial de San Rafael.",
                "amenities_raw": ["cocina_equipada", "placards"],
            },
            {
                "source": "gallito",
                "external_id": "G-RENT-006",
                "url": "https://www.gallito.com.uy/alquiler-cantegril-6",
                "property_type": "apartamento",
                "operation": "alquiler",
                "title": "Apartamento 2 dormitorios - Cantegril",
                "description": "Apartamento en Cantegril Country, con acceso a amenidades. Alquiler anual.",
                "price": Decimal("40000"),
                "price_usd": _usd(40000),       # USD 1.000
                "currency": "UYU",
                "price_per_m2_usd": _usd(40000) / Decimal("75"),
                "bedrooms": 2,
                "bathrooms": 1,
                "area_total": Decimal("75"),
                "neighborhood": "Cantegril",
                "city": "Punta del Este",
                "latitude": -34.9700,
                "longitude": -54.9600,
                "ai_score": 73.0,
                "ai_premium": False,
                "ai_opportunity": False,
                "ai_tags": ["country_club", "amenidades", "anual"],
                "ai_summary": "Alquiler anual con amenidades en Cantegril Country.",
                "amenities_raw": ["piscina", "cancha_tenis", "seguridad_24h"],
            },
            {
                "source": "infocasas",
                "external_id": "IC-RENT-007",
                "url": "https://www.infocasas.com.uy/alquiler-maldonado-7",
                "property_type": "apartamento",
                "operation": "alquiler",
                "title": "Monoambiente económico - Maldonado",
                "description": "Monoambiente económico en Maldonado, ideal para una persona. Alquiler anual, el más accesible de la zona.",
                "price": Decimal("15000"),
                "price_usd": _usd(15000),       # USD 375
                "currency": "UYU",
                "price_per_m2_usd": _usd(15000) / Decimal("30"),
                "bedrooms": 0,
                "bathrooms": 1,
                "area_total": Decimal("30"),
                "neighborhood": "Maldonado Centro",
                "city": "Maldonado",
                "latitude": -34.9011,
                "longitude": -54.9617,
                "ai_score": 68.0,
                "ai_premium": False,
                "ai_opportunity": True,
                "ai_tags": ["economico", "anual", "una_persona", "accesible"],
                "ai_summary": "El alquiler más accesible del rango, ideal para una persona.",
                "amenities_raw": ["cocina_equipada"],
            },
            {
                "source": "gallito",
                "external_id": "G-RENT-008",
                "url": "https://www.gallito.com.uy/alquiler-la-barra-8",
                "property_type": "casa",
                "operation": "alquiler",
                "title": "Casa 3 dormitorios - La Barra",
                "description": "Casa amplia de 3 dormitorios con parrillero y jardín en La Barra. Alquiler anual, tope del rango.",
                "price": Decimal("80000"),
                "price_usd": _usd(80000),       # USD 2.000
                "currency": "UYU",
                "price_per_m2_usd": _usd(80000) / Decimal("140"),
                "bedrooms": 3,
                "bathrooms": 2,
                "garages": 1,
                "area_total": Decimal("140"),
                "neighborhood": "La Barra",
                "city": "Punta del Este",
                "latitude": -34.9058,
                "longitude": -54.8692,
                "ai_score": 82.0,
                "ai_premium": True,
                "ai_opportunity": False,
                "ai_tags": ["casa", "jardin", "parrillero", "familiar", "anual"],
                "ai_summary": "Casa familiar amplia en La Barra, tope del rango de alquiler.",
                "amenities_raw": ["jardin", "parrillero", "garaje"],
            },
            # — Venta de referencia (contexto de mercado, no es el foco) —
            {
                "source": "mercadolibre",
                "external_id": "MLU-SALE-CTX",
                "url": "https://www.mercadolibre.com.uy/venta-pde-centro-ctx",
                "property_type": "apartamento",
                "operation": "venta",
                "title": "Apartamento frente al mar - Punta del Este Centro (referencia)",
                "description": "Apartamento de 3 dormitorios con vista al mar. Incluido como referencia de mercado de venta.",
                "price": Decimal("450000"),
                "price_usd": Decimal("450000"),
                "currency": "USD",
                "price_per_m2_usd": Decimal("3750"),
                "bedrooms": 3,
                "bathrooms": 2,
                "area_total": Decimal("120"),
                "neighborhood": "Punta del Este Centro",
                "city": "Punta del Este",
                "latitude": -34.9633,
                "longitude": -54.9367,
                "ai_score": 88.5,
                "ai_premium": True,
                "ai_opportunity": False,
                "ai_tags": ["frente_al_mar", "premium", "referencia_venta"],
                "ai_summary": "Referencia de mercado de venta premium en la península.",
            },
        ]

        now = datetime.now(timezone.utc)
        for prop_data in sample_properties:
            amenities = prop_data.pop("amenities_raw", None)

            import hashlib

            # Datos de contacto (demo) según la inmobiliaria / fuente.
            # En producción estos campos los completa el scraper desde el portal.
            _agencies = {
                "mercadolibre": {
                    "agency_name": "Costa Este Propiedades",
                    "contact_name": "Lucía Fernández",
                    "contact_phone": "+598 4224 5566",
                    "contact_whatsapp": "+598 99 612 345",
                    "contact_email": "ventas@costaeste.com.uy",
                },
                "infocasas": {
                    "agency_name": "Maldonado Realty",
                    "contact_name": "Martín Rodríguez",
                    "contact_phone": "+598 4225 7788",
                    "contact_whatsapp": "+598 99 745 678",
                    "contact_email": "info@maldonadorealty.uy",
                },
                "gallito": {
                    "agency_name": "Península Inmobiliaria",
                    "contact_name": "Carolina Méndez",
                    "contact_phone": "+598 4244 1122",
                    "contact_whatsapp": "+598 99 823 901",
                    "contact_email": "contacto@peninsula.com.uy",
                },
            }
            _contact = _agencies.get(prop_data["source"], {})

            prop = Property(
                **prop_data,
                **_contact,
                contact_phone_normalized=_contact.get("contact_whatsapp", "").replace(" ", ""),
                url_hash=hashlib.sha256(prop_data["url"].encode()).hexdigest(),
                status=PropertyStatus.ACTIVE,
                first_seen_at=now,
                last_seen_at=now,
                last_scraped_at=now,
            )
            db.add(prop)
            await db.flush()

            # Imagen placeholder — SVG inline (data URI) que carga sin red.
            # En producción aquí van las imágenes reales scrapeadas.
            import base64

            _palette = ["#0ea5e9", "#0284c7", "#38bdf8", "#075985", "#0369a1"]
            _color = _palette[hash(prop.external_id) % len(_palette)]
            _label = (prop.neighborhood or prop.city or "PDE")
            _svg = (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600">'
                f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
                f'<stop offset="0%" stop-color="{_color}"/>'
                f'<stop offset="100%" stop-color="#082f49"/></linearGradient></defs>'
                f'<rect width="800" height="600" fill="url(#g)"/>'
                f'<text x="50%" y="48%" font-family="Inter,Arial" font-size="42" '
                f'fill="white" text-anchor="middle" font-weight="700">{_label}</text>'
                f'<text x="50%" y="58%" font-family="Inter,Arial" font-size="24" '
                f'fill="rgba(255,255,255,.8)" text-anchor="middle">PropTech PDE</text></svg>'
            )
            _data_uri = "data:image/svg+xml;base64," + base64.b64encode(_svg.encode()).decode()
            db.add(PropertyImage(
                property_id=prop.id,
                url=_data_uri,
                order=0,
                is_main=True,
            ))

            # Precio inicial en historial
            db.add(PriceHistory(
                property_id=prop.id,
                price=prop.price,
                price_usd=prop.price_usd,
                currency=prop.currency,
                change_type="initial",
                source=prop.source,
            ))

        await db.commit()
        logger.info(f"✅ {len(sample_properties)} propiedades de ejemplo creadas")


async def run_all_seeds():
    """Ejecutar todos los seeds en orden."""
    logger.info("🌱 Iniciando seeds...")
    await seed_users()
    await seed_zones()
    await seed_sample_properties()
    logger.info("✅ Seeds completados")


if __name__ == "__main__":
    asyncio.run(run_all_seeds())
