"""
Tipos de columna portables (Postgres ↔ SQLite).

Permiten que los mismos modelos corran con PostgreSQL + PostGIS en producción
y con SQLite en desarrollo local, sin cambiar las definiciones de columnas.

Cada tipo usa `load_dialect_impl` para elegir la implementación nativa según
el dialecto en tiempo de creación de tablas / runtime.
"""
import json
import uuid
from typing import Any, Optional

from sqlalchemy import CHAR, JSON, Text, TypeDecorator
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.core.config import settings

# Flag global para ramas de DDL que no se pueden resolver por dialecto
# (p. ej. índices con funciones SQL específicas de Postgres).
IS_SQLITE: bool = "sqlite" in settings.DATABASE_URL


class UUID(TypeDecorator):
    """UUID nativo en Postgres; CHAR(36) en SQLite."""

    impl = CHAR
    cache_ok = True

    def __init__(self, as_uuid: bool = True, **kw: Any) -> None:
        self.as_uuid = as_uuid
        super().__init__(**kw)

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=self.as_uuid))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


class JSONB(TypeDecorator):
    """JSONB en Postgres; JSON en SQLite."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_JSONB())
        return dialect.type_descriptor(JSON())


class ARRAY(TypeDecorator):
    """ARRAY nativo en Postgres; lista serializada como JSON en SQLite."""

    impl = JSON
    cache_ok = True

    def __init__(self, item_type: Any = None, **kw: Any) -> None:
        self.item_type = item_type
        super().__init__()

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_ARRAY(self.item_type))
        return dialect.type_descriptor(JSON())


class Geography(TypeDecorator):
    """
    Geography(PostGIS) en Postgres; Text (WKT) en SQLite.

    Acepta la misma firma que geoalchemy2.Geography para no tocar los modelos.
    """

    impl = Text
    cache_ok = True

    def __init__(self, geometry_type: Optional[str] = None, srid: int = 4326, **kw: Any) -> None:
        self.geometry_type = geometry_type
        self.srid = srid
        super().__init__()

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from geoalchemy2 import Geography as PgGeography

            return dialect.type_descriptor(
                PgGeography(geometry_type=self.geometry_type, srid=self.srid)
            )
        return dialect.type_descriptor(Text())
