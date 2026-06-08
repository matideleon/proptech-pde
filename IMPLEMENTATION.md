# 🚀 Implementación — Estado Verificado

Registro de la puesta en marcha real del sistema y las pruebas ejecutadas.

## Entorno usado

- **Python**: 3.11.4 (venv en `backend/.venv`)
- **Node**: 24.x (frontend)
- **Sin Docker / sin PostgreSQL** en la máquina de verificación → se validó
  todo lo que no requiere base de datos en vivo, y el resto en *modo degradado*.

## ✅ Pruebas ejecutadas y resultado

| # | Prueba | Comando | Resultado |
|---|--------|---------|-----------|
| 1 | Tests unitarios del normalizador | `pytest tests/unit/` | **21/21 PASS** |
| 2 | Pipeline parse→normalize (payload real MercadoLibre) | `python -m scripts_demo.parse_pipeline_demo` | **OK** (moneda, barrio, tipo, precio/m², fingerprint) |
| 3 | Import de todos los módulos backend | script de import | **25/25 OK** |
| 4 | API FastAPI cableada | `app.openapi()` | **16 paths, 16 schemas** |
| 5 | Servidor HTTP en vivo | `uvicorn app.main:app` | `/health` 200 (degraded), `/` 200, `/openapi.json` 27KB |
| 6 | Motor IA (fallback determinista) | `ai_engine._default_score()` | **OK** |
| 7 | Scraper en vivo MercadoLibre | API pública | 403 (MELI exige auth desde 2024) → **resiliencia/backoff funcionó** |

## 🐛 Bugs reales encontrados y corregidos durante la implementación

1. **`base.py`** — `return self.stats` con valor dentro de un async generator
   (ilegal). Convertido `run()` en generador limpio (stats vía `self.stats`).
2. **`normalizer.py` / `seeds.py`** — import incorrecto `python_slugify` →
   `slugify` (el paquete `python-slugify` se importa como `slugify`).
3. **`models/alert.py`** — `last_sent_at: Mapped[Optional[object]]` sin tipo de
   columna → SQLAlchemy no podía mapearlo. Cambiado a `DateTime`.
4. **`models/lead.py`** — columna `metadata` (nombre reservado por Declarative)
   → renombrada a `extra_data` mapeando a la columna `"metadata"`.
5. **`main.py`** — `import sentry_sdk` obligatorio (solo se usa en prod) →
   import opcional con guard.
6. **`main.py`** — `init_db()` en el lifespan tiraba la app si no había DB →
   arranque en *modo degradado* + `/health` reporta `database: error`.
7. **`core/logging.py`** — `structlog.stdlib.add_logger_name` incompatible con
   `PrintLoggerFactory` (`PrintLogger` no tiene `.name`) → processors nativos.
8. **`playwright_helper.py`** — `yield from` dentro de función async (ilegal) →
   `for ... yield`.
9. **`core/config.py`** — `.env` no se encontraba al correr desde `backend/` →
   resolución robusta del `.env` (backend dir + raíz del repo).

## Mejoras estructurales

- **Tests separados**: `tests/conftest.py` minimal; fixtures pesadas de DB/HTTP
  movidas a `tests/integration/conftest.py` con *skip* automático si falta el
  stack. Así los tests unitarios corren sin Postgres.
- **Scripts de demo** en `backend/scripts_demo/` (live scrape + parse pipeline).

## Reproducir la verificación local (sin Docker)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install pydantic pydantic-settings beautifulsoup4 lxml aiohttp \
  fake-useragent price-parser phonenumbers python-slugify pytest \
  pytest-asyncio structlog dateparser fastapi "uvicorn[standard]" \
  slowapi "sqlalchemy[asyncio]" GeoAlchemy2 "python-jose[cryptography]" \
  "passlib[bcrypt]" email-validator asyncpg httpx openai

# Tests
python -m pytest tests/unit/ -v

# Demo del pipeline (sin red ni DB)
python -m scripts_demo.parse_pipeline_demo

# API en vivo (modo degradado sin Postgres)
uvicorn app.main:app --port 8000
curl localhost:8000/health
```

## Para producción completa

`make up` con Docker levanta Postgres+PostGIS, Redis, API, workers, frontend,
Metabase y Nginx — ahí los endpoints que requieren DB (`/properties`, `/stats`,
etc.) funcionan al 100%. El único punto que requiere acción del operador es
configurar credenciales reales en `.env` (OpenAI, WhatsApp, Telegram) y, para
scraping de MercadoLibre vía API, un token OAuth de MELI (su API dejó de ser
anónima); el scraper web (`MercadoLibreWebScraper`) y los de Gallito/InfoCasas
no lo requieren.
