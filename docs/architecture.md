# Arquitectura del Sistema — PropTech PDE

## Visión General

PropTech PDE es una plataforma de inteligencia inmobiliaria diseñada con arquitectura de microservicios modular, escalable y production-ready.

## Diagrama de Arquitectura

```
┌──────────────────────────────────────────────────────────────────────┐
│                           PROPTECH PDE                                │
│                  Inteligencia Inmobiliaria · PDE                      │
└──────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                         CAPA DE PRESENTACIÓN                         │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Next.js 14 (App Router)                    │   │
│  │                                                                │   │
│  │  Dashboard  │  Propiedades  │  CRM  │  Admin  │  Analytics    │   │
│  │                                                                │   │
│  │  TailwindCSS + shadcn/ui + Recharts + Mapbox GL               │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │ HTTP
┌─────────────────────────────────────────────────────────────────────┐
│                            NGINX (Proxy)                             │
│                   Rate Limiting · SSL · Load Balancing               │
└─────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────┐
│                          CAPA DE APLICACIÓN                          │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                  FastAPI (Python 3.11)                          │ │
│  │                                                                  │ │
│  │  /api/v1/                                                       │ │
│  │    ├── auth/          JWT Authentication                        │ │
│  │    ├── properties/    CRUD + búsqueda + filtros + stats         │ │
│  │    ├── scraping/      Control y monitoreo de scrapers           │ │
│  │    ├── zones/         Zonas y métricas de mercado               │ │
│  │    ├── leads/         CRM endpoints                             │ │
│  │    ├── alerts/        Sistema de alertas                        │ │
│  │    └── ai/            Motor de IA                               │ │
│  │                                                                  │ │
│  │  Middleware: CORS · Rate Limiting · JWT · Logging               │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                 Celery Workers                                   │ │
│  │                                                                  │ │
│  │  Queue: scraping     → Ejecutar scrapers por portal             │ │
│  │  Queue: ai           → Scoring y análisis de propiedades        │ │
│  │  Queue: notifications→ WhatsApp, Telegram, Email                │ │
│  │  Queue: default      → Tareas generales                         │ │
│  │                                                                  │ │
│  │  Celery Beat → Cron Jobs automáticos                            │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
            │                           │
┌───────────▼───────────┐   ┌──────────▼────────────┐
│    CAPA DE DATOS       │   │    CAPA DE IA          │
│                        │   │                        │
│  PostgreSQL 15         │   │  OpenAI GPT-4o         │
│  + PostGIS             │   │  Claude API            │
│  + TimescaleDB         │   │                        │
│                        │   │  Funciones:            │
│  Tablas principales:   │   │  - Scoring             │
│  - properties          │   │  - Clasificación       │
│  - price_history       │   │  - Descripciones       │
│  - zones               │   │  - Matching            │
│  - users               │   │  - Estimación valor    │
│  - leads               │   │  - Sentimiento         │
│  - alerts              │   │                        │
│  - scraping_runs       │   └────────────────────────┘
│                        │
│  Redis (Cache)         │   ┌────────────────────────┐
│  - Sessions            │   │   NOTIFICACIONES       │
│  - Task queue          │   │                        │
│  - Rate limiting       │   │  WhatsApp Business API │
│  - Cache API           │   │  Telegram Bot API      │
│                        │   │  SendGrid Email        │
└────────────────────────┘   └────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                          SCRAPING LAYER                              │
│                                                                       │
│  ┌──────────────┐ ┌───────────┐ ┌─────────┐ ┌───────────────────┐  │
│  │ MercadoLibre │ │InfoCasas  │ │ Gallito │ │ Inmobiliarias     │  │
│  │   (API +     │ │(HTTP +    │ │ (HTTP)  │ │ locales (HTTP)    │  │
│  │   Web)       │ │Playwright)│ │         │ │                   │  │
│  └──────────────┘ └───────────┘ └─────────┘ └───────────────────┘  │
│                                                                       │
│  Normalizer Pipeline: Precio · Barrio · Tipo · Dedup · Fingerprint   │
└─────────────────────────────────────────────────────────────────────┘
```

## Decisiones Técnicas

### ¿Por qué FastAPI?
- **Async nativo**: Perfecto para scraping asíncrono y múltiples conexiones DB
- **Tipado con Pydantic**: Validación automática y documentación Swagger auto-generada
- **Performance**: Comparable a Node.js, mejor que Django REST
- **Ecosistema Python**: Acceso a librerías de IA/ML (OpenAI, Anthropic)

### ¿Por qué PostgreSQL + PostGIS?
- **PostGIS**: Queries geográficas nativas (radio, polígonos, heatmaps)
- **JSONB**: Almacena raw_data del scraping sin schema rígido
- **GIN indexes**: Búsqueda de texto completo en español con `unaccent`
- **Escala**: Maneja millones de registros con índices correctos

### ¿Por qué Celery + Redis?
- **Scraping asíncrono**: No bloquea el API principal
- **Queues separadas**: Prioridades distintas por tipo de tarea
- **Celery Beat**: Cron jobs distribuidos sin crontab del sistema
- **Flower**: Dashboard de monitoreo incluido

### ¿Por qué Next.js 14 App Router?
- **RSC**: Mejor SEO y performance inicial
- **Turbopack**: Dev build ultra-rápido
- **Type safety**: TypeScript end-to-end con la API
- **Ecosystem**: Compatibilidad con shadcn/ui, Recharts, Mapbox

## Patrones de Código

### Backend
- **Repository Pattern**: Lógica de DB centralizada en services/
- **Dependency Injection**: FastAPI Depends() para DB, Auth
- **Schema separation**: Pydantic Input/Output separados
- **Async everything**: Toda la lógica es async/await

### Scrapers
- **BaseScraper**: Herencia con funcionalidades comunes
- **ScrapedProperty**: DTO de transferencia entre scraper y DB
- **Normalizer**: Pipeline de limpieza separado del scraper
- **Fingerprinting**: Deduplicación cross-source

### Frontend
- **TanStack Query**: Cache y sincronización de estado servidor
- **Zustand**: Estado global mínimo (auth, preferences)
- **Atomic design**: Componentes pequeños y reutilizables

## Escalabilidad

### Horizontal
- **API**: Multi-instancia detrás de NGINX con sticky sessions
- **Workers**: Múltiples Celery workers por tipo de queue
- **DB**: Read replicas para queries de lectura masiva (analytics)

### Vertical
- **Índices**: GIN, GIST (PostGIS), B-tree optimizados
- **Cache**: Redis para resultados de búsqueda y stats
- **Pagination**: Cursor-based para grandes datasets

### SaaS Multi-tenant (FASE 4)
- Agregar `tenant_id` a todos los modelos
- Row-Level Security en PostgreSQL
- Separar scrapers por tenant con configuración
- Billing con Stripe

## Estimaciones de Carga

| Métrica | Valor |
|---|---|
| Propiedades en DB (año 1) | ~100K |
| Requests/hora (pico) | ~5.000 |
| Scrapers simultáneos | 3-5 |
| Jobs de IA/día | ~1.000 |
| Latencia API p50 | <50ms |
| Latencia API p99 | <500ms |
