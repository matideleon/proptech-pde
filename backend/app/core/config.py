"""Configuración central del sistema."""
from functools import lru_cache
from pathlib import Path
from typing import Any, List, Optional

from pydantic import AnyHttpUrl, Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolver .env tanto si se ejecuta desde backend/ como desde la raíz del repo.
# (En Docker las variables llegan por environment; esto es para dev local.)
_BACKEND_DIR = Path(__file__).resolve().parents[2]   # .../backend
_REPO_ROOT = _BACKEND_DIR.parent                       # .../proptech-pde
_ENV_FILES = (
    str(_BACKEND_DIR / ".env"),
    str(_REPO_ROOT / ".env"),
    ".env",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── APP ──────────────────────────────────────────────────
    APP_NAME: str = "PropTech PDE"
    APP_ENV: str = "development"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = Field(min_length=32)
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"

    @property
    def allowed_hosts_list(self) -> List[str]:
        return [h.strip() for h in self.ALLOWED_HOSTS.split(",")]

    # ─── DATABASE ────────────────────────────────────────────
    DATABASE_URL: str
    DATABASE_SYNC_URL: str
    POSTGRES_USER: str = "proptech"
    POSTGRES_PASSWORD: str = "proptech123"
    POSTGRES_DB: str = "proptech_pde"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # ─── REDIS ───────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_URL: str = "redis://localhost:6379/1"

    # ─── JWT ─────────────────────────────────────────────────
    JWT_SECRET_KEY: str = Field(default="change-me-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ─── AI ──────────────────────────────────────────────────
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_MODEL_PREMIUM: str = "gpt-4o"
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"

    # ─── SCRAPING ────────────────────────────────────────────
    SCRAPING_DELAY_MIN: float = 2.0
    SCRAPING_DELAY_MAX: float = 5.0
    SCRAPING_MAX_RETRIES: int = 3
    SCRAPING_TIMEOUT: int = 30
    USE_PROXY: bool = False
    PROXY_LIST: str = ""
    BROWSERLESS_URL: Optional[str] = None

    # ─── CREDENCIALES DE PORTALES ────────────────────────────
    # MercadoLibre: su API exige OAuth desde 2024. Token gratuito para
    # developers en https://developers.mercadolibre.com.uy
    MERCADOLIBRE_ACCESS_TOKEN: Optional[str] = None
    # Facebook Marketplace: requiere sesión iniciada. Cookies exportadas
    # de una cuenta (formato JSON de Playwright storage_state).
    FACEBOOK_SESSION_FILE: Optional[str] = None

    # ─── GRUPOS DE FACEBOOK (alquileres ofrecidos/solicitados) ──
    # Sesión del usuario para leer grupos privados. Formato de header Cookie:
    #   "c_user=100xxxx; xs=xx%3A...; ..."  (extraída del navegador logueado).
    FB_SESSION_COOKIE: Optional[str] = None
    # IDs o slugs de los grupos a monitorear, separados por coma.
    FB_GROUP_IDS: str = ""

    @property
    def fb_group_ids_list(self) -> List[str]:
        if not self.FB_GROUP_IDS:
            return []
        return [g.strip() for g in self.FB_GROUP_IDS.split(",") if g.strip()]

    @property
    def proxy_list(self) -> List[str]:
        if not self.PROXY_LIST:
            return []
        return [p.strip() for p in self.PROXY_LIST.split(",") if p.strip()]

    # ─── WHATSAPP ────────────────────────────────────────────
    WHATSAPP_API_URL: str = "https://graph.facebook.com/v18.0"
    WHATSAPP_PHONE_ID: Optional[str] = None
    WHATSAPP_TOKEN: Optional[str] = None
    WHATSAPP_VERIFY_TOKEN: Optional[str] = None
    # Destinatario del digest diario (formato internacional sin +, ej. 59899123456)
    WHATSAPP_ALERT_TO: Optional[str] = None

    # ─── DIGEST DIARIO ───────────────────────────────────────
    # URL pública base para construir el link del dashboard en las alertas.
    PUBLIC_BASE_URL: str = "https://dynamiclabsai.com"
    # Ventana (horas) para considerar una propiedad "nueva" en el digest.
    DIGEST_WINDOW_HOURS: int = 24

    # ─── TELEGRAM ────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None

    # ─── EMAIL ───────────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SENDGRID_API_KEY: Optional[str] = None
    FROM_EMAIL: str = "noreply@proptech.uy"
    FROM_NAME: str = "PropTech PDE"

    # ─── EXTERNAL ────────────────────────────────────────────
    GOOGLE_MAPS_API_KEY: Optional[str] = None
    GEOCODIO_API_KEY: Optional[str] = None

    # ─── CELERY ──────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/2"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/3"
    CELERY_TASK_ALWAYS_EAGER: bool = False

    # ─── SUPABASE ────────────────────────────────────────────
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_KEY: Optional[str] = None

    # ─── SENTRY ──────────────────────────────────────────────
    SENTRY_DSN: Optional[str] = None

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def cors_origins(self) -> List[str]:
        if self.is_development:
            return [
                "http://localhost:3000",
                "http://localhost:3001",
                "http://localhost:3002",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:3001",
                "http://localhost:8000",
                "http://127.0.0.1:8000",
            ]
        return self.allowed_hosts_list


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
