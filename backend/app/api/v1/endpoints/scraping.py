"""Endpoints para control del sistema de scraping."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_db, require_admin
from app.models.scraping import ScrapingRun, ScrapingStatus
from app.models.user import User

router = APIRouter(prefix="/scraping", tags=["scraping"])


class ScrapingRunSchema(BaseModel):
    id: UUID
    source: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime]
    duration_seconds: Optional[int]
    properties_found: int
    properties_new: int
    properties_updated: int
    price_changes: int
    errors_count: int
    error_message: Optional[str]


class TriggerScrapeRequest(BaseModel):
    sources: Optional[List[str]] = None  # None = todas las fuentes
    parallel: bool = False


class TriggerScrapeResponse(BaseModel):
    message: str
    task_id: Optional[str] = None
    sources: List[str]


@router.post("/trigger", response_model=TriggerScrapeResponse)
async def trigger_scrape(
    request: TriggerScrapeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """
    Disparar scraping manualmente.
    Requiere rol admin.
    """
    from app.scrapers.runner import SCRAPERS, ScrapingRunner

    # Validar fuentes
    available_sources = list(SCRAPERS.keys())
    sources = request.sources or available_sources

    invalid_sources = [s for s in sources if s not in available_sources]
    if invalid_sources:
        raise HTTPException(
            status_code=400,
            detail=f"Fuentes inválidas: {invalid_sources}. Disponibles: {available_sources}",
        )

    # Ejecutar en background
    runner = ScrapingRunner()

    async def run_scraping():
        await runner.run_all(sources=sources, parallel=request.parallel)

    background_tasks.add_task(run_scraping)

    return TriggerScrapeResponse(
        message=f"Scraping iniciado para {len(sources)} fuentes",
        sources=sources,
    )


@router.get("/runs", response_model=List[ScrapingRunSchema])
async def list_scraping_runs(
    source: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Listar runs de scraping con sus estadísticas."""
    filters = []
    if source:
        filters.append(ScrapingRun.source == source)
    if status:
        filters.append(ScrapingRun.status == status)

    from sqlalchemy import and_
    query = (
        select(ScrapingRun)
        .where(and_(*filters) if filters else True)
        .order_by(desc(ScrapingRun.started_at))
        .limit(limit)
    )
    result = await db.execute(query)
    runs = result.scalars().all()

    return [ScrapingRunSchema.model_validate(run) for run in runs]


@router.get("/runs/{run_id}", response_model=ScrapingRunSchema)
async def get_scraping_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Obtener detalles de un run de scraping."""
    result = await db.execute(
        select(ScrapingRun).where(ScrapingRun.id == run_id)
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Run no encontrado")

    return ScrapingRunSchema.model_validate(run)


@router.get("/status")
async def get_scraping_status(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Estado actual del sistema de scraping."""
    from sqlalchemy import func

    # Último run por fuente
    from app.scrapers.runner import SCRAPERS
    sources_status = {}

    for source in SCRAPERS.keys():
        last_run = await db.execute(
            select(ScrapingRun)
            .where(ScrapingRun.source == source)
            .order_by(desc(ScrapingRun.started_at))
            .limit(1)
        )
        run = last_run.scalar_one_or_none()
        if run:
            sources_status[source] = {
                "last_run": run.started_at.isoformat(),
                "status": run.status,
                "properties_found": run.properties_found,
                "new": run.properties_new,
            }
        else:
            sources_status[source] = {"status": "never_run"}

    return {
        "sources": sources_status,
        "available_scrapers": list(SCRAPERS.keys()),
    }
