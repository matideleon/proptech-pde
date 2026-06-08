"""Router principal de la API v1."""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, properties, scraping

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(properties.router)
api_router.include_router(scraping.router)

# TODO: Agregar en FASE 2-3
# api_router.include_router(zones.router)
# api_router.include_router(leads.router)
# api_router.include_router(alerts.router)
# api_router.include_router(analytics.router)
# api_router.include_router(ai_router)
