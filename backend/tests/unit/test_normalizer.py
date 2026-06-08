"""Tests unitarios del normalizador de propiedades."""
import pytest
from app.scrapers.normalizer import PropertyNormalizer, UYU_TO_USD_RATE
from app.scrapers.base import ScrapedProperty


@pytest.fixture
def normalizer():
    return PropertyNormalizer()


@pytest.fixture
def sample_property():
    return ScrapedProperty(
        source="mercadolibre",
        url="https://www.mercadolibre.com.uy/test-123",
        property_type="apartamento",
        operation="venta",
        title="Apartamento 3 dorm en Punta del Este",
        price=450000,
        currency="USD",
        bedrooms=3,
        bathrooms=2,
        area_total=120,
        neighborhood="punta del este",
        amenities=["piscina", "pool", "parrilla", "bbq"],
    )


class TestPriceNormalization:
    def test_usd_price_passthrough(self, normalizer, sample_property):
        result = normalizer._normalize_price(sample_property)
        assert result.price_usd == 450000

    def test_uyu_price_conversion(self, normalizer, sample_property):
        sample_property.price = 19_000_000  # UYU
        sample_property.currency = "UYU"
        result = normalizer._normalize_price(sample_property)
        expected_usd = round(19_000_000 / UYU_TO_USD_RATE, 2)
        assert result.price_usd == expected_usd

    def test_invalid_price_removed(self, normalizer, sample_property):
        sample_property.price = -1000
        result = normalizer._normalize_price(sample_property)
        assert result.price is None

    def test_price_per_m2_calculation(self, normalizer, sample_property):
        result = normalizer._normalize_price(sample_property)
        expected_m2 = round(450000 / 120, 2)
        assert result.price_per_m2_usd == expected_m2


class TestNeighborhoodNormalization:
    def test_pde_centro_alias(self, normalizer, sample_property):
        sample_property.neighborhood = "punta del este"
        result = normalizer._normalize_neighborhood(sample_property)
        assert result.neighborhood == "Punta del Este Centro"

    def test_la_barra_alias(self, normalizer, sample_property):
        sample_property.neighborhood = "la barra de maldonado"
        result = normalizer._normalize_neighborhood(sample_property)
        assert result.neighborhood == "La Barra"

    def test_jose_ignacio_with_accent(self, normalizer, sample_property):
        sample_property.neighborhood = "José Ignacio"
        result = normalizer._normalize_neighborhood(sample_property)
        assert result.neighborhood == "José Ignacio"

    def test_unknown_neighborhood_title_cased(self, normalizer, sample_property):
        sample_property.neighborhood = "nuevo barrio xyz"
        result = normalizer._normalize_neighborhood(sample_property)
        assert result.neighborhood == "Nuevo Barrio Xyz"


class TestPropertyTypeNormalization:
    @pytest.mark.parametrize("input_type,expected", [
        ("apto", "apartamento"),
        ("apt", "apartamento"),
        ("ph", "penthouse"),
        ("lote", "terreno"),
        ("cochera", "garage"),
        ("galpón", "local_comercial"),
        ("desconocido", "otro"),
    ])
    def test_property_type_mapping(self, normalizer, sample_property, input_type, expected):
        sample_property.property_type = input_type
        result = normalizer._normalize_property_type(sample_property)
        assert result.property_type == expected


class TestAmenityNormalization:
    def test_dedup_amenities(self, normalizer, sample_property):
        # "piscina" y "pool" deben normalizarse a lo mismo y deduplicarse
        sample_property.amenities = ["piscina", "pool", "swimming pool"]
        result = normalizer._normalize_amenities(sample_property)
        # Deben quedar solo una instancia
        pileta_count = result.amenities.count("pileta")
        assert pileta_count == 1

    def test_parrilla_normalization(self, normalizer, sample_property):
        sample_property.amenities = ["parrilla", "bbq"]
        result = normalizer._normalize_amenities(sample_property)
        assert "barbacoa" in result.amenities


class TestFingerprint:
    def test_same_property_same_fingerprint(self, normalizer):
        prop1 = ScrapedProperty(
            source="mercadolibre",
            url="https://ml.com/1",
            property_type="apartamento",
            operation="venta",
            title="Test",
            price=450000,
            currency="USD",
            neighborhood="La Barra",
            bedrooms=3,
            area_total=120,
        )
        prop2 = ScrapedProperty(
            source="infocasas",  # Diferente fuente
            url="https://ic.com/2",
            property_type="apartamento",
            operation="venta",
            title="Diferente título",  # Título diferente
            price=450000,
            currency="USD",
            neighborhood="la barra",  # Misma zona (case insensitive)
            bedrooms=3,
            area_total=120,
        )
        # Misma propiedad en diferentes portales debería tener fingerprint similar
        fp1 = normalizer.compute_fingerprint(prop1)
        fp2 = normalizer.compute_fingerprint(prop2)
        # (después de normalizar el barrio)
        prop1.neighborhood = "La Barra"
        prop2.neighborhood = "La Barra"
        fp1 = normalizer.compute_fingerprint(prop1)
        fp2 = normalizer.compute_fingerprint(prop2)
        assert fp1 == fp2


class TestPriceChange:
    @pytest.mark.parametrize("old,new,expected_type", [
        (100000, 90000, "decrease"),
        (100000, 115000, "increase"),
        (100000, 100500, "stable"),
    ])
    def test_price_change_detection(self, normalizer, old, new, expected_type):
        change_type, change_pct = normalizer.detect_price_change(new, old, "USD")
        assert change_type == expected_type
