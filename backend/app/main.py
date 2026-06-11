"""
PropTech PDE — FastAPI Application
Plataforma de Inteligencia Inmobiliaria para Punta del Este, Uruguay
"""
import time
from contextlib import asynccontextmanager

try:
    import sentry_sdk
except ImportError:  # Sentry es opcional (solo producción)
    sentry_sdk = None

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.deps import limiter
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.db.database import check_db_health, init_db

# Setup logging
setup_logging()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle de la aplicación."""
    logger.info(f"🚀 Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")

    # Inicializar DB — en modo degradado si no está disponible
    try:
        await init_db()
        logger.info("✅ Base de datos inicializada")
        # Seed mínimo idempotente: usuario admin + zonas. NO propiedades de
        # ejemplo (queremos solo datos reales del scraper en prod). Se ejecuta
        # acá porque el CMD del contenedor (gunicorn) siempre corre el lifespan,
        # sin depender de que el orquestador respete `command` del compose.
        try:
            from app.db.seeds import seed_users, seed_zones
            await seed_users()
            await seed_zones()
            logger.info("✅ Seed mínimo (admin + zonas) OK")
        except Exception as e:  # noqa: BLE001 — race entre workers es benigna (idempotente)
            logger.warning("Seed mínimo no aplicado (posible race entre workers)", error=str(e))
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "⚠️  Base de datos no disponible — arrancando en modo degradado",
            error=str(e),
        )

    # Setup Sentry en producción
    if sentry_sdk and settings.SENTRY_DSN and settings.is_production:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=0.1,
            environment=settings.APP_ENV,
        )
        logger.info("✅ Sentry configurado")

    yield

    logger.info("🔴 Cerrando aplicación...")


# ─── CREAR APP ─────────────────────────────────────────────────
app = FastAPI(
    title="PropTech PDE API",
    description="""
    ## 🏠 Plataforma de Inteligencia Inmobiliaria — Punta del Este

    Sistema completo de scraping, análisis con IA y CRM para el mercado
    inmobiliario de Punta del Este y Maldonado, Uruguay.

    ### Funcionalidades
    - 🔍 **Búsqueda avanzada** de propiedades con filtros
    - 🤖 **IA**: scoring, oportunidades, descripciones automáticas
    - 📊 **Analytics**: estadísticas de mercado en tiempo real
    - 🔔 **Alertas**: WhatsApp, Telegram y Email
    - 🏢 **CRM**: gestión de leads y matching inteligente
    - 🗺️ **Mapas**: geolocalización con PostGIS

    ### Autenticación
    Usar JWT Bearer token obtenido en `/api/v1/auth/login`
    """,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    openapi_url="/openapi.json" if settings.is_development else None,
    lifespan=lifespan,
)

# ─── MIDDLEWARES ───────────────────────────────────────────────

# Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS — permite localhost y dominios de túnel público (loca.lt, trycloudflare, ngrok)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://.*\.(loca\.lt|trycloudflare\.com|ngrok-free\.app|ngrok\.io)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

# GZip
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Trusted Host (producción)
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts_list,
    )


# ─── MIDDLEWARE DE LOGGING ─────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.monotonic()

    try:
        response = await call_next(request)
        duration_ms = (time.monotonic() - start_time) * 1000

        logger.info(
            "HTTP Request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=f"{duration_ms:.1f}",
            client=request.client.host if request.client else "unknown",
        )

        response.headers["X-Process-Time"] = f"{duration_ms:.1f}ms"
        return response

    except Exception as e:
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.error(
            "HTTP Error",
            method=request.method,
            path=request.url.path,
            error=str(e),
            duration_ms=f"{duration_ms:.1f}",
        )
        raise


# ─── RUTAS ────────────────────────────────────────────────────
app.include_router(api_router)


# ─── HEALTH CHECK ─────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health_check():
    """Estado del sistema."""
    db_ok = await check_db_health()
    return {
        "status": "healthy" if db_ok else "degraded",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "env": settings.APP_ENV,
        "database": "ok" if db_ok else "error",
    }


@app.get("/", tags=["system"])
async def root():
    return {
        "message": f"🏠 {settings.APP_NAME} API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


# ─── EXCEPTION HANDLERS ───────────────────────────────────────
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Recurso no encontrado", "path": request.url.path},
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error("Error interno", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"},
    )
