"""Sistema de logging estructurado con structlog."""
import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger

from app.core.config import settings


def add_app_context(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Agrega contexto de la app a cada log."""
    event_dict["app"] = settings.APP_NAME
    event_dict["env"] = settings.APP_ENV
    event_dict["version"] = settings.APP_VERSION
    return event_dict


def setup_logging() -> None:
    """Configura el sistema de logging."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Configurar logging estándar
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Silenciar loggers ruidosos
    for noisy_logger in ["httpx", "httpcore", "playwright"]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    # Processors comunes — nativos de structlog (compatibles con PrintLogger)
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        add_app_context,
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.is_development:
        processors = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        processors = [
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """Obtener logger configurado."""
    return structlog.get_logger(name)


# Logger principal
logger = get_logger("proptech")
