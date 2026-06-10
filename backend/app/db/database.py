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
