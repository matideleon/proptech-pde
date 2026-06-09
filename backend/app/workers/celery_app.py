"""
Configuración de Celery para tareas asíncronas.

Queues:
- scraping: Tareas de scraping (alta prioridad)
- ai: Análisis de IA (media prioridad)
- notifications: Envío de alertas (alta prioridad)
- default: Tareas generales
"""
from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

from app.core.config import settings

# ─── CONFIGURACIÓN ────────────────────────────────────────────
celery_app = Celery(
    "proptech_pde",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.tasks.scraping",
        "app.workers.tasks.ai_tasks",
        # "app.workers.tasks.notifications",  # TODO: crear este módulo
    ],
)

# ─── QUEUES ───────────────────────────────────────────────────
default_exchange = Exchange("default", type="direct")
scraping_exchange = Exchange("scraping", type="direct")
ai_exchange = Exchange("ai", type="direct")
notifications_exchange = Exchange("notifications", type="direct")

celery_app.conf.task_queues = (
    Queue("default", default_exchange, routing_key="default"),
    Queue("scraping", scraping_exchange, routing_key="scraping", priority=10),
    Queue("ai", ai_exchange, routing_key="ai", priority=5),
    Queue("notifications", notifications_exchange, routing_key="notifications", priority=8),
)

celery_app.conf.task_default_queue = "default"
celery_app.conf.task_default_exchange = "default"
celery_app.conf.task_default_routing_key = "default"

celery_app.conf.task_routes = {
    "app.workers.tasks.scraping.*": {"queue": "scraping"},
    "app.workers.tasks.ai_tasks.*": {"queue": "ai"},
    "app.workers.tasks.notifications.*": {"queue": "notifications"},
}

# ─── SETTINGS ─────────────────────────────────────────────────
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Montevideo",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    result_expires=3600,  # 1 hora
    worker_max_tasks_per_child=100,  # Reiniciar worker cada 100 tareas
)

# ─── SCHEDULE (CRON JOBS) ─────────────────────────────────────
celery_app.conf.beat_schedule = {
    # Scraping MercadoLibre — cada 4 horas
    "scrape-mercadolibre": {
        "task": "app.workers.tasks.scraping.scrape_source",
        "schedule": crontab(minute=0, hour="0,4,8,12,16,20"),
        "args": ("mercadolibre",),
        "options": {"queue": "scraping"},
    },
    # Scraping InfoCasas — cada 6 horas
    "scrape-infocasas": {
        "task": "app.workers.tasks.scraping.scrape_source",
        "schedule": crontab(minute=30, hour="0,6,12,18"),
        "args": ("infocasas",),
        "options": {"queue": "scraping"},
    },
    # Scraping Gallito — cada 8 horas
    "scrape-gallito": {
        "task": "app.workers.tasks.scraping.scrape_source",
        "schedule": crontab(minute=0, hour="2,10,18"),
        "args": ("gallito",),
        "options": {"queue": "scraping"},
    },
    # Scraping Facebook Marketplace — cada 8 horas
    "scrape-facebook": {
        "task": "app.workers.tasks.scraping.scrape_source",
        "schedule": crontab(minute=15, hour="3,11,19"),
        "args": ("facebook",),
        "options": {"queue": "scraping"},
    },
    # Análisis IA — cada hora (propiedades sin puntuar)
    "ai-score-new": {
        "task": "app.workers.tasks.ai_tasks.score_new_properties",
        "schedule": crontab(minute=0),
        "options": {"queue": "ai"},
    },
    # Actualizar métricas de zonas — cada hora
    "update-zone-stats": {
        "task": "app.workers.tasks.ai_tasks.update_zone_statistics",
        "schedule": crontab(minute=30),
        "options": {"queue": "default"},
    },
    # Reporte diario de mercado — 8am
    "daily-market-report": {
        "task": "app.workers.tasks.notifications.send_daily_market_report",
        "schedule": crontab(hour=8, minute=0),
        "options": {"queue": "notifications"},
    },
    # Detectar propiedades eliminadas — cada 24h
    "detect-removed": {
        "task": "app.workers.tasks.scraping.detect_removed_properties",
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": "scraping"},
    },
}
