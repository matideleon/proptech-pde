"""Configuración de la base de datos con SQLAlchemy async."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("db")


# ─── ENGINE ──────────────────────────────────────────────────
# SQLite (dev local) no soporta los parámetros de pool de Postgres.
_is_sqlite = "sqlite" in settings.DATABASE_URL
_engine_kwargs: dict = {"echo": settings.DEBUG}
if not _is_sqlite:
    _engine_kwargs.update(
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_pre_ping=True,
    )

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

# ─── SESSION FACTORY ─────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ─── BASE MODEL ──────────────────────────────────────────────
class Base(DeclarativeBase):
    """Base para todos los modelos SQLAlchemy."""
    pass


# ─── DEPENDENCY ──────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency para obtener sesión de DB."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error("DB session error", error=str(e))
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager para uso fuera de FastAPI."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error("DB context error", error=str(e))
            raise
        finally:
            await session.close()


# Columnas agregadas después del deploy inicial. `create_all` solo crea tablas
# faltantes, NO altera tablas existentes, así que las columnas nuevas en tablas
# ya creadas (p.ej. en prod) se aplican acá de forma idempotente.
# Formato: (tabla, columna, tipo_postgres, tipo_sqlite)
_ADDED_COLUMNS = [
    ("group_posts", "external_links", "JSONB DEFAULT '[]'::jsonb", "JSON DEFAULT '[]'"),
]


async def _ensure_columns(conn, is_postgres: bool) -> None:
    """Aplica columnas nuevas a tablas existentes (migración ligera idempotente)."""
    from sqlalchemy import text

    for table, column, pg_type, sqlite_type in _ADDED_COLUMNS:
        try:
            if is_postgres:
                await conn.execute(text(
                    f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {pg_type}'
                ))
            else:
                # SQLite: ADD COLUMN IF NOT EXISTS no existe en versiones viejas,
                # así que chequeamos PRAGMA primero.
                rows = await conn.exec_driver_sql(f"PRAGMA table_info({table})")
                existing = {r[1] for r in rows.fetchall()}
                if column not in existing:
                    await conn.exec_driver_sql(
                        f"ALTER TABLE {table} ADD COLUMN {column} {sqlite_type}"
                    )
        except Exception as e:  # noqa: BLE001 — tabla puede no existir aún; create_all la hará
            logger.warning(
                "No se pudo asegurar columna (ignorable si la tabla es nueva)",
                table=table, column=column, error=str(e),
            )


async def init_db() -> None:
    """Inicializar base de datos — crear extensiones (Postgres) y tablas."""
    from sqlalchemy import text

    # Importar modelos para que estén registrados en Base.metadata
    import app.models  # noqa: F401

    is_postgres = "postgresql" in settings.DATABASE_URL

    async with engine.begin() as conn:
        if is_postgres:
            # Extensiones solo aplican a PostgreSQL.
            # Usamos try/except individual para evitar errores de concurrencia
            # cuando múltiples workers arrancan en paralelo (ya existen en init.sql).
            for ext in ("postgis", "pg_trgm", "uuid-ossp"):
                try:
                    await conn.execute(text(f'CREATE EXTENSION IF NOT EXISTS "{ext}"'))
                except Exception as e:
                    logger.warning(
                        "Extension already exists or could not be created (ignorable)",
                        extension=ext,
                        error=str(e),
                    )
        await conn.run_sync(Base.metadata.create_all)
        # Migración ligera: columnas agregadas tras el deploy inicial.
        await _ensure_columns(conn, is_postgres)

    logger.info("✅ Base de datos inicializada", engine="postgres" if is_postgres else "sqlite")


async def check_db_health() -> bool:
    """Verificar conexión a DB."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(__import__("sqlalchemy").text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("DB health check failed", error=str(e))
        return False
