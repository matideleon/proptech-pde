# 🏠 PropTech PDE — Plataforma de Inteligencia Inmobiliaria

> Sistema completo de scraping, análisis y automatización para el mercado inmobiliario de **Punta del Este, Uruguay**.

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+PostGIS-blue?logo=postgresql)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)](https://docker.com)

---

## 🎯 Objetivos

- **Scraping automático** de +5 portales inmobiliarios de Uruguay
- **Detección inteligente** de nuevas propiedades, bajas de precio y eliminaciones
- **IA** para scoring, clasificación y automatización comercial
- **Dashboard PropTech** con mapas, heatmaps y analytics avanzados
- **CRM integrado** con matching cliente-propiedad
- **Alertas** por WhatsApp, Telegram y Email
- **API pública** para futuro SaaS

---

## 🗂️ Estructura del Proyecto

```
proptech-pde/
├── backend/                    # FastAPI + Python
│   ├── app/
│   │   ├── api/v1/endpoints/   # REST API endpoints
│   │   ├── core/               # Config, seguridad, logging
│   │   ├── db/                 # Database, sessions, migrations
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── services/           # Business logic
│   │   ├── scrapers/           # Scrapers por portal
│   │   ├── ai/                 # Motor de IA
│   │   ├── crm/                # Sistema CRM
│   │   ├── notifications/      # WhatsApp, Telegram, Email
│   │   └── admin/              # Panel administrativo
│   ├── migrations/             # Alembic migrations
│   ├── workers/                # Celery workers
│   └── tests/                  # Tests unitarios e integración
├── frontend/                   # Next.js 14
│   ├── app/                    # App Router
│   ├── components/             # Componentes UI
│   └── lib/                    # Utilidades
├── docker/                     # Configuraciones Docker
├── scripts/                    # Scripts de instalación
└── docs/                       # Documentación
```

---

## 🚀 Instalación Rápida

### Prerequisitos
- Docker & Docker Compose v2+
- Make

### Setup en 3 pasos

```bash
# 1. Clonar y configurar
git clone https://github.com/tu-org/proptech-pde.git
cd proptech-pde
cp .env.example .env  # Editar con tus claves

# 2. Levantar todo
make up

# 3. Inicializar DB y seeds
make migrate && make seed
```

### Accesos
| Servicio | URL | Credenciales |
|---|---|---|
| Frontend Dashboard | http://localhost:3000 | admin@proptech.uy / admin123 |
| API Docs (Swagger) | http://localhost:8000/docs | JWT Token |
| Admin Panel | http://localhost:8000/admin | — |
| Metabase | http://localhost:3001 | admin@proptech.uy |
| PGAdmin | http://localhost:5050 | admin@proptech.uy / admin123 |

---

## 🔧 Comandos Make

```bash
make up          # Levantar todos los servicios
make down        # Bajar servicios
make logs        # Ver logs
make migrate     # Correr migrations
make seed        # Poblar DB con datos iniciales
make scrape      # Correr scrapers manualmente
make test        # Ejecutar tests
make lint        # Linting y formateo
make backup      # Backup de base de datos
```

---

## 📊 Fuentes de Datos

| Portal | Estado | Frecuencia |
|---|---|---|
| MercadoLibre Inmuebles | ✅ Activo | Cada 4h |
| InfoCasas | ✅ Activo | Cada 6h |
| Gallito Luis | ✅ Activo | Cada 8h |
| Facebook Marketplace | 🔧 Playwright | Cada 12h |
| Inmobiliarias locales | ✅ Activo | Cada 24h |

---

## 💰 Costos Estimados (Producción)

| Componente | Costo/mes |
|---|---|
| VPS 4vCPU / 8GB RAM | ~$40 USD |
| OpenAI API (GPT-4o) | ~$30-80 USD |
| WhatsApp Business API | ~$20 USD |
| Supabase Pro | $25 USD |
| **Total** | **~$115-165 USD/mes** |

---

## 📈 Rendimiento Esperado

- **Propiedades scrapeadas/día**: 500-2.000
- **Latencia API p95**: < 200ms
- **Throughput scraping**: 10-50 req/seg con proxies
- **Precisión deduplicación**: > 95%
- **Uptime objetivo**: 99.5%

---

## 🔐 Variables de Entorno

Ver `.env.example` para la lista completa de variables requeridas.

---

## 📚 Documentación

- [Arquitectura del Sistema](docs/architecture.md)
- [Guía de Scrapers](docs/scrapers.md)
- [API Reference](docs/api.md)
- [Guía de Deploy](docs/deploy.md)
- [Motor de IA](docs/ai.md)

---

## 🗺️ Roadmap

- [x] **FASE 1**: Arquitectura + DB + Scrapers
- [ ] **FASE 2**: API REST + Dashboard
- [ ] **FASE 3**: IA + Automatizaciones
- [ ] **FASE 4**: CRM + SaaS multi-tenant

---

*Construido con ❤️ para el mercado inmobiliario de Punta del Este, Uruguay.*
