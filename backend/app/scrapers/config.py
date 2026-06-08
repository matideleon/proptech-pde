"""
Configuración objetivo del scraping.

Define el foco de captación del sistema. Por decisión de negocio, el sistema
prioriza ALQUILERES de bajo/medio ticket en Maldonado / Punta del Este:

    Rango objetivo: USD 400 – 2.000 / mes
    Equivalente UYU (1 USD = 40 UYU): UYU 16.000 – 80.000 / mes

Los scrapers usan estos valores para filtrar resultados en origen (cuando el
portal lo permite) y como post-filtro local en el pipeline de normalización.
"""
from dataclasses import dataclass, field
from typing import List

# Tasa de cambio de referencia (1 USD = UYU)
USD_UYU_RATE = 40.0

# ─── RANGO OBJETIVO DE ALQUILER ──────────────────────────────
# Rango estricto solicitado: USD 400 – 2.000 (sin tolerancia).
RENT_MIN_USD = 400
RENT_MAX_USD = 2_000
RENT_MIN_UYU = RENT_MIN_USD * int(USD_UYU_RATE)      # 16000
RENT_MAX_UYU = RENT_MAX_USD * int(USD_UYU_RATE)      # 80000

# Límites efectivos del filtro (estrictos, sin holgura)
RENT_MIN_USD_SOFT = RENT_MIN_USD                      # 400
RENT_MAX_USD_SOFT = RENT_MAX_USD                      # 2000
RENT_MIN_UYU_SOFT = RENT_MIN_UYU                      # 16000
RENT_MAX_UYU_SOFT = RENT_MAX_UYU                      # 80000


@dataclass
class ScrapingTarget:
    """Foco de captación del scraping."""

    # Operación: el sistema se enfoca en alquileres. Se mantiene 'venta'
    # con baja prioridad para contexto de mercado, pero el grueso es alquiler.
    operations: List[str] = field(default_factory=lambda: ["rent", "buy"])
    primary_operation: str = "rent"

    # Distribución objetivo de captación (peso relativo por operación)
    operation_weights: dict = field(
        default_factory=lambda: {"rent": 0.85, "buy": 0.15}
    )

    # Rango de precio para alquiler (post-filtro)
    rent_min_usd: int = RENT_MIN_USD_SOFT
    rent_max_usd: int = RENT_MAX_USD_SOFT
    rent_min_uyu: int = RENT_MIN_UYU_SOFT
    rent_max_uyu: int = RENT_MAX_UYU_SOFT

    def price_in_rent_range(self, price: float, currency: str) -> bool:
        """¿El precio cae en el rango objetivo de alquiler?"""
        if price is None:
            return False
        if currency == "UYU":
            return self.rent_min_uyu <= price <= self.rent_max_uyu
        return self.rent_min_usd <= price <= self.rent_max_usd


# Instancia global
TARGET = ScrapingTarget()
