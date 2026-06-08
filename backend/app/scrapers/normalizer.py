"""
Pipeline de normalización de datos de propiedades.

Responsable de:
- Normalizar monedas (USD/UYU)
- Normalizar barrios/zonas
- Normalizar tipos de propiedades
- Detectar duplicados
- Limpiar textos
- Calcular fingerprints para deduplicación
"""
import hashlib
import re
import unicodedata
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import phonenumbers
from price_parser import Price
from slugify import slugify

from app.core.logging import get_logger
from app.scrapers.base import ScrapedProperty

logger = get_logger("normalizer")

# ─── TIPO DE CAMBIO UYU/USD ────────────────────────────────────
# En producción esto debería obtenerse de una API de tipo de cambio
UYU_TO_USD_RATE = 40.0  # 1 USD = 40 UYU (configurado para mercado local)


# ─── MAPEO DE BARRIOS PUNTA DEL ESTE ──────────────────────────
# Normaliza variaciones de nombres a un nombre canónico
NEIGHBORHOOD_ALIASES: Dict[str, str] = {
    # Punta del Este
    "punta del este": "Punta del Este Centro",
    "pde": "Punta del Este Centro",
    "peninsula": "Punta del Este Centro",
    "la peninsula": "Punta del Este Centro",

    # La Barra
    "la barra": "La Barra",
    "barra de maldonado": "La Barra",
    "la barra de maldonado": "La Barra",

    # José Ignacio
    "jose ignacio": "José Ignacio",
    "josé ignacio": "José Ignacio",
    "j. ignacio": "José Ignacio",

    # Manantiales
    "manantiales": "Manantiales",
    "manantial": "Manantiales",

    # Punta Ballena
    "punta ballena": "Punta Ballena",
    "ballena": "Punta Ballena",

    # Portezuelo
    "portezuelo": "Portezuelo",
    "el portezuelo": "Portezuelo",

    # Cantegril
    "cantegril": "Cantegril",
    "country cantegril": "Cantegril",
    "cantegril cc": "Cantegril",

    # Pinares
    "pinares": "Pinares",
    "el pinar": "Pinares",
    "pinares de maldonado": "Pinares",

    # Beverly Hills
    "beverly hills": "Beverly Hills",
    "bh": "Beverly Hills",

    # San Rafael
    "san rafael": "San Rafael",
    "barrio san rafael": "San Rafael",

    # Maldonado
    "maldonado": "Maldonado Centro",
    "centro maldonado": "Maldonado Centro",

    # Solanas
    "solanas": "Solanas",
    "solanas verde": "Solanas",

    # El Chorro
    "el chorro": "El Chorro",
    "chorro": "El Chorro",

    # Montoya
    "montoya": "Montoya",
    "playa montoya": "Montoya",

    # Aidy Grill
    "aidy grill": "Aidy Grill",
    "aidy": "Aidy Grill",
    "aidy grill cc": "Aidy Grill",

    # Roosevelt
    "roosevelt": "Roosevelt",
    "barrio roosevelt": "Roosevelt",
    "cc roosevelt": "Roosevelt",
}


# ─── TIPOS DE PROPIEDAD NORMALIZADOS ──────────────────────────
PROPERTY_TYPE_ALIASES: Dict[str, str] = {
    "apto": "apartamento",
    "apt": "apartamento",
    "apartment": "apartamento",
    "depto": "apartamento",
    "departamento": "apartamento",
    "ph": "penthouse",
    "pent-house": "penthouse",
    "pent house": "penthouse",
    "casa quinta": "casa",
    "quinta": "chacra",
    "estancia": "campo",
    "rancho": "casa",
    "bungalow": "casa",
    "chalet": "casa",
    "villa": "casa",
    "loft": "apartamento",
    "monoambiente": "apartamento",
    "estudio": "apartamento",
    "local comercial": "local_comercial",
    "local": "local_comercial",
    "galpon": "local_comercial",
    "galpón": "local_comercial",
    "bodega": "local_comercial",
    "negocio": "local_comercial",
    "parking": "garage",
    "cochera": "garage",
    "box": "garage",
    "solar": "terreno",
    "lote": "terreno",
    "parcela": "terreno",
    "fracion": "terreno",
    "fracción": "terreno",
}

# ─── AMENIDADES NORMALIZADAS ───────────────────────────────────
AMENITY_NORMALIZATIONS: Dict[str, str] = {
    "piscina": "pileta",
    "pool": "pileta",
    "swimming pool": "pileta",
    "parrilla": "barbacoa",
    "bbq": "barbacoa",
    "barbecue": "barbacoa",
    "ascensor": "elevador",
    "lift": "elevador",
    "elevator": "elevador",
    "ac": "aire_acondicionado",
    "a/c": "aire_acondicionado",
    "aire acondicionado": "aire_acondicionado",
    "air conditioning": "aire_acondicionado",
    "wifi": "internet",
    "internet": "internet",
    "seguridad 24": "seguridad_24h",
    "vigilancia": "seguridad_24h",
    "gym": "gimnasio",
    "gimnasio": "gimnasio",
    "fitness": "gimnasio",
    "spa": "spa",
    "sauna": "sauna",
    "terraza": "terraza",
    "balcon": "balcon",
    "balcón": "balcon",
    "jardin": "jardin",
    "jardín": "jardin",
    "garden": "jardin",
    "amueblado": "amueblado",
    "furnished": "amueblado",
    "vista al mar": "vista_mar",
    "vista mar": "vista_mar",
    "ocean view": "vista_mar",
    "frente al mar": "frente_mar",
    "beachfront": "frente_mar",
    "playa": "acceso_playa",
    "acceso playa": "acceso_playa",
    "beach access": "acceso_playa",
}


class PropertyNormalizer:
    """
    Pipeline de normalización de propiedades.
    Convierte ScrapedProperty crudo a datos normalizados y listos para DB.
    """

    def normalize(self, prop: ScrapedProperty) -> ScrapedProperty:
        """
        Aplicar todo el pipeline de normalización.

        Returns:
            ScrapedProperty normalizado
        """
        prop = self._normalize_price(prop)
        prop = self._normalize_neighborhood(prop)
        prop = self._normalize_property_type(prop)
        prop = self._normalize_operation(prop)
        prop = self._normalize_phone(prop)
        prop = self._normalize_amenities(prop)
        prop = self._clean_text(prop)
        return prop

    def _normalize_price(self, prop: ScrapedProperty) -> ScrapedProperty:
        """
        Normalizar precios y convertir a USD.

        Maneja formatos: "U$S 250,000", "$U 500.000", "250000", etc.
        """
        if prop.price is None:
            return prop

        # Asegurar que el precio sea positivo y razonable
        if prop.price <= 0 or prop.price > 50_000_000:  # Max 50M USD
            prop.price = None
            return prop

        # Calcular precio en USD
        if prop.currency == "UYU":
            prop_dict = prop.__dict__.copy()
            prop.price_usd = round(prop.price / UYU_TO_USD_RATE, 2)
        else:
            prop.price_usd = prop.price

        # Calcular precio por m²
        if prop.price_usd and prop.area_total and prop.area_total > 0:
            prop.price_per_m2_usd = round(prop.price_usd / prop.area_total, 2)

        return prop

    def _normalize_neighborhood(self, prop: ScrapedProperty) -> ScrapedProperty:
        """
        Normalizar nombre de barrio/zona.
        """
        if not prop.neighborhood:
            # Intentar extraer del título o dirección
            for alias, canonical in NEIGHBORHOOD_ALIASES.items():
                if prop.title and alias in prop.title.lower():
                    prop.neighborhood = canonical
                    break
            return prop

        # Normalizar a minúsculas sin acentos para comparación
        normalized = self._strip_accents(prop.neighborhood.lower().strip())

        # Buscar en aliases
        for alias, canonical in NEIGHBORHOOD_ALIASES.items():
            alias_norm = self._strip_accents(alias.lower())
            if alias_norm in normalized or normalized in alias_norm:
                prop.neighborhood = canonical
                return prop

        # Si no hay alias, capitalizar correctamente
        prop.neighborhood = prop.neighborhood.title()
        return prop

    def _normalize_property_type(self, prop: ScrapedProperty) -> ScrapedProperty:
        """Normalizar tipo de propiedad."""
        if not prop.property_type:
            prop.property_type = "otro"
            return prop

        ptype = prop.property_type.lower().strip()

        # Buscar en aliases
        for alias, canonical in PROPERTY_TYPE_ALIASES.items():
            if alias == ptype or alias in ptype:
                prop.property_type = canonical
                return prop

        # Tipos válidos directos
        valid_types = {
            "apartamento", "casa", "chacra", "terreno",
            "local_comercial", "oficina", "garage", "penthouse",
            "duplex", "campo", "hotel", "otro",
        }
        if ptype not in valid_types:
            prop.property_type = "otro"

        return prop

    def _normalize_operation(self, prop: ScrapedProperty) -> ScrapedProperty:
        """Normalizar tipo de operación."""
        op = (prop.operation or "").lower().strip()

        if op in ("venta", "sale", "buy", "compra", "comprar"):
            prop.operation = "venta"
        elif op in ("alquiler", "rent", "renta", "arrendamiento"):
            prop.operation = "alquiler"
        elif op in ("alquiler_temporal", "temporal", "temporada", "vacation", "holiday"):
            prop.operation = "alquiler_temporal"
        else:
            prop.operation = "venta"  # Default

        return prop

    def _normalize_phone(self, prop: ScrapedProperty) -> ScrapedProperty:
        """Normalizar número de teléfono con librería phonenumbers."""
        if not prop.contact_phone:
            return prop

        try:
            # Intentar parsear como número uruguayo
            parsed = phonenumbers.parse(prop.contact_phone, "UY")
            if phonenumbers.is_valid_number(parsed):
                prop.contact_phone_normalized = phonenumbers.format_number(
                    parsed, phonenumbers.PhoneNumberFormat.E164
                )
                # Número de WhatsApp (sin el +)
                prop.contact_whatsapp = prop.contact_phone_normalized.replace("+", "")
        except Exception:
            # Si falla, dejar el número tal cual
            # Limpiar caracteres extraños
            phone_clean = re.sub(r'[^\d\+\-\s\(\)]', '', prop.contact_phone)
            if len(phone_clean) >= 7:
                prop.contact_phone = phone_clean

        return prop

    def _normalize_amenities(self, prop: ScrapedProperty) -> ScrapedProperty:
        """Normalizar lista de amenidades."""
        if not prop.amenities:
            return prop

        normalized = []
        seen = set()

        for amenity in prop.amenities:
            amenity_clean = amenity.lower().strip()
            amenity_clean = self._strip_accents(amenity_clean)

            # Buscar en normalizations
            found = False
            for alias, canonical in AMENITY_NORMALIZATIONS.items():
                alias_norm = self._strip_accents(alias.lower())
                if alias_norm in amenity_clean or amenity_clean in alias_norm:
                    if canonical not in seen:
                        normalized.append(canonical)
                        seen.add(canonical)
                    found = True
                    break

            if not found:
                # Limpiar y capitalizar
                clean = re.sub(r'\s+', ' ', amenity).strip()
                clean_norm = clean.lower()
                if clean_norm not in seen and len(clean) > 2:
                    normalized.append(clean)
                    seen.add(clean_norm)

        prop.amenities = normalized[:50]  # Max 50 amenidades
        return prop

    def _clean_text(self, prop: ScrapedProperty) -> ScrapedProperty:
        """Limpiar textos de caracteres extraños."""
        if prop.title:
            prop.title = self._clean_string(prop.title)[:500]

        if prop.description:
            prop.description = self._clean_string(prop.description)[:10000]

        if prop.agency_name:
            prop.agency_name = self._clean_string(prop.agency_name)[:300]

        if prop.neighborhood:
            prop.neighborhood = self._clean_string(prop.neighborhood)[:200]

        return prop

    def _clean_string(self, text: str) -> str:
        """Limpiar string: remove HTML, normalizar espacios."""
        if not text:
            return ""

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Remove HTML entities
        text = re.sub(r'&\w+;', ' ', text)
        # Normalizar espacios
        text = re.sub(r'\s+', ' ', text)
        # Remove caracteres de control
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        return text.strip()

    def _strip_accents(self, text: str) -> str:
        """Remover acentos del texto."""
        return ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )

    def compute_fingerprint(self, prop: ScrapedProperty) -> str:
        """
        Calcular fingerprint para deduplicación cross-source.

        El fingerprint combina características únicas de la propiedad
        para detectar la misma propiedad en múltiples portales.
        """
        # Normalizar valores para el fingerprint
        price_str = str(int(prop.price or 0))
        neighborhood = self._strip_accents((prop.neighborhood or "").lower().strip())
        ptype = (prop.property_type or "").lower()
        operation = (prop.operation or "").lower()
        bedrooms = str(prop.bedrooms or 0)
        area = str(int(prop.area_total or 0))

        key = f"{ptype}|{operation}|{price_str}|{neighborhood}|{bedrooms}|{area}"
        return hashlib.md5(key.encode()).hexdigest()

    def is_duplicate(
        self,
        prop: ScrapedProperty,
        existing_fingerprints: List[str],
    ) -> bool:
        """
        Verificar si una propiedad es duplicado de otra ya existente.
        """
        fp = self.compute_fingerprint(prop)
        return fp in existing_fingerprints

    def detect_price_change(
        self,
        new_price: float,
        old_price: float,
        currency: str,
    ) -> Tuple[str, float]:
        """
        Detectar cambio de precio.

        Returns:
            (change_type, change_pct) donde change_type es:
            'increase', 'decrease', 'stable'
        """
        if old_price == 0:
            return "stable", 0.0

        change_pct = ((new_price - old_price) / old_price) * 100
        threshold = 0.5  # 0.5% de umbral para considerar cambio

        if change_pct > threshold:
            return "increase", round(change_pct, 2)
        elif change_pct < -threshold:
            return "decrease", round(change_pct, 2)
        else:
            return "stable", 0.0


# Instancia singleton del normalizador
normalizer = PropertyNormalizer()
