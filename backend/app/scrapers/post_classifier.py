"""
Clasificador de posts de grupos de Facebook (alquileres Punta del Este).

Detecta si un post es:
  - "oferta"  → alguien OFRECE un alquiler (se alquila / alquilo / disponible)
  - "demanda" → alguien BUSCA un alquiler (busco / necesito / familia busca)
  - "otro"    → no es sobre alquileres (consultas, ventas, spam, etc.)

y extrae datos estructurados (operación, zona, precio, dormitorios, período,
teléfono) con heurística por palabras clave. Funciona SIN OpenAI; si hay una
API key configurada, `classify_post_ai` refina la extracción.

Diseñado para español rioplatense / jerga inmobiliaria de Punta del Este.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional

from app.models.zone import PUNTA_DEL_ESTE_ZONES

# ─── Léxicos ────────────────────────────────────────────────────────────────

# Señales de que alguien BUSCA (demanda). Las más específicas pesan más.
_DEMANDA_KEYWORDS = {
    "busco": 3, "buscamos": 3, "busca": 2, "buscando": 3,
    "necesito": 3, "necesitamos": 3, "preciso": 3, "precisamos": 3,
    "ando buscando": 4, "estoy buscando": 4, "estamos buscando": 4,
    "alguien alquila": 4, "alguien que alquile": 4, "alguien tiene": 3,
    "se busca": 4, "familia busca": 4, "pareja busca": 4,
    "quien alquile": 3, "quien tenga": 3, "me recomiendan": 2,
    "alguien para alquilar": 4, "necesito alquilar": 4, "busco alquilar": 4,
}

# Señales de que alguien OFRECE (oferta).
_OFERTA_KEYWORDS = {
    "alquilo": 3, "se alquila": 4, "alquila": 2, "rento": 3, "se renta": 3,
    "ofrezco": 3, "disponible para alquilar": 4, "disponible alquiler": 3,
    "alquiler disponible": 4, "para alquilar": 2, "en alquiler": 3,
    "tengo disponible": 3, "ultimo disponible": 2, "se ofrece": 3,
    "consultar disponibilidad": 2, "reservas": 1, "agenda tu": 2,
}

# Tipos de operación
_VENTA_KEYWORDS = ("venta", "vendo", "se vende", "en venta", "permuta")
_ALQUILER_KEYWORDS = ("alquil", "renta", "arriendo", "arrendar")

# Períodos de alquiler típicos de la zona
_PERIODOS = {
    "anual": ("anual", "todo el año", "por año", "contrato anual"),
    "invernal": ("invernal", "invierno", "fuera de temporada", "marzo a diciembre"),
    "temporada": ("temporada", "enero", "febrero", "verano", "fin de año", "quincena"),
    "diario": ("por dia", "por noche", "diario", "fin de semana", "finde", "turistic"),
}

# Tipos de propiedad
_TIPOS = {
    "casa": ("casa", "chalet", "ph ", "duplex"),
    "apartamento": ("apartamento", "apto", "depto", "departamento", "monoambiente", "mono ambiente"),
    "terreno": ("terreno", "lote", "chacra"),
    "local_comercial": ("local", "oficina", "comercial"),
}


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def _norm(text: str) -> str:
    """Minúsculas + sin acentos + espacios colapsados (para matching robusto)."""
    return re.sub(r"\s+", " ", _strip_accents(text or "").lower()).strip()


@dataclass
class ClassifiedPost:
    """Resultado de clasificar un post."""
    kind: str = "otro"                       # oferta | demanda | otro
    operation: Optional[str] = None          # alquiler | venta
    property_type: Optional[str] = None
    period: Optional[str] = None             # anual | invernal | temporada | diario
    neighborhood: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None           # USD | UYU
    bedrooms: Optional[int] = None
    contact_phone: Optional[str] = None
    confidence: float = 0.0                  # 0..1
    matched: List[str] = field(default_factory=list)


def _score_keywords(text: str, lexicon: dict) -> tuple[int, List[str]]:
    score, hits = 0, []
    for kw, weight in lexicon.items():
        if kw in text:
            score += weight
            hits.append(kw)
    return score, hits


def _extract_zone(text: str) -> Optional[str]:
    # Match por nombre de zona normalizado (el más largo primero, evita parciales).
    for zone in sorted(PUNTA_DEL_ESTE_ZONES, key=lambda z: -len(z["name"])):
        if _norm(zone["name"]) in text:
            return zone["name"]
    # Alias frecuentes en los grupos
    aliases = {
        "playa mansa": "Punta del Este Centro", "mansa": "Punta del Este Centro",
        "playa brava": "Punta del Este Centro", "brava": "Punta del Este Centro",
        "peninsula": "Punta del Este Centro", "centro": "Punta del Este Centro",
        "maldonado": "Maldonado Centro",
    }
    for alias, zone in aliases.items():
        if re.search(rf"\b{re.escape(alias)}\b", text):
            return zone
    return None


def _extract_price(text: str) -> tuple[Optional[float], Optional[str]]:
    # USD: u$s 800, usd 800, 800 dolares, $800 (ambiguo → USD si dice dolar/u$s)
    # UYU: $ 30000, 30.000 pesos
    currency = None
    if re.search(r"u\$s|usd|dolar|dólar", text):
        currency = "USD"
    elif re.search(r"\$u|pesos|uyu", text):
        currency = "UYU"

    # Buscar el primer número con magnitud razonable de precio.
    # Acepta "30.000", "30000", y números cortos con multiplicador ("25 mil", "5k").
    for m in re.finditer(r"(\d{1,3}(?:[.,]\d{3})+|\d+)\s*(mil|k)?\b", text):
        raw = m.group(1).replace(".", "").replace(",", "")
        try:
            val = float(raw)
        except ValueError:
            continue
        if m.group(2):  # "30 mil" / "30k"
            val *= 1000
        elif len(raw) < 3:  # número corto sin multiplicador → no es un precio
            continue
        # Filtrar números que no parecen precios (años, teléfonos cortos)
        if 100 <= val <= 5_000_000 and not (1900 <= val <= 2100):
            # Heurística: precios > 50.000 sin moneda → UYU; menores → USD
            if currency is None:
                currency = "UYU" if val >= 50_000 else "USD"
            return val, currency
    return None, currency


def _extract_bedrooms(text: str) -> Optional[int]:
    m = re.search(r"(\d+)\s*(?:dorm|dormitorio|amb|ambiente|hab|cuarto)", text)
    if m:
        return int(m.group(1))
    if "monoambiente" in text or "mono ambiente" in text:
        return 1
    return None


def _extract_phone(text: str) -> Optional[str]:
    # Teléfonos uruguayos: 09x xxx xxx, +598 9x..., con o sin separadores
    m = re.search(r"(?:\+?598\s?)?0?9\d[\s.\-]?\d{3}[\s.\-]?\d{3}", text)
    if m:
        digits = re.sub(r"\D", "", m.group(0))
        return digits or None
    return None


def _detect(text: str, mapping: dict) -> Optional[str]:
    for label, needles in mapping.items():
        if any(n in text for n in needles):
            return label
    return None


def classify_post(raw_text: str) -> ClassifiedPost:
    """Clasifica un post con heurística (sin IA). Robusto y barato."""
    result = ClassifiedPost()
    if not raw_text or len(raw_text.strip()) < 5:
        return result

    text = _norm(raw_text)

    # ¿Es de venta? Entonces no es alquiler.
    is_venta = any(k in text for k in _VENTA_KEYWORDS)
    is_alquiler = any(k in text for k in _ALQUILER_KEYWORDS)

    demanda_score, demanda_hits = _score_keywords(text, _DEMANDA_KEYWORDS)
    oferta_score, oferta_hits = _score_keywords(text, _OFERTA_KEYWORDS)

    result.matched = demanda_hits + oferta_hits

    # Decidir kind. Demanda gana empates (sus keywords son más específicas).
    if max(demanda_score, oferta_score) == 0:
        # Sin señal de oferta/demanda explícita pero menciona alquiler → oferta débil
        if is_alquiler and not is_venta:
            result.kind = "oferta"
            result.confidence = 0.35
        else:
            result.kind = "otro"
            return result
    elif demanda_score >= oferta_score:
        result.kind = "demanda"
        result.confidence = min(1.0, 0.4 + demanda_score * 0.12)
    else:
        result.kind = "oferta"
        result.confidence = min(1.0, 0.4 + oferta_score * 0.12)

    # Operación
    if is_venta and not is_alquiler:
        result.operation = "venta"
        # Una venta no es ni oferta ni demanda de alquiler
        result.kind = "otro"
        return result
    result.operation = "alquiler"

    # Extracción de datos
    result.property_type = _detect(text, _TIPOS)
    result.period = _detect(text, _PERIODOS)
    result.neighborhood = _extract_zone(text)
    result.price, result.currency = _extract_price(text)
    result.bedrooms = _extract_bedrooms(text)
    result.contact_phone = _extract_phone(text)

    return result
