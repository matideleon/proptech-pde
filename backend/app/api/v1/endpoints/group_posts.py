"""Endpoints para posts de grupos de Facebook (alquileres ofrecidos/solicitados)."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, get_db, require_admin
from app.models.group_post import GroupPost, PostKind
from app.models.user import User

router = APIRouter(prefix="/group-posts", tags=["group-posts"])


class GroupPostSchema(BaseModel):
    id: UUID
    group_id: str
    group_name: Optional[str]
    permalink: Optional[str]
    author_name: Optional[str]
    text: str
    kind: PostKind
    operation: Optional[str]
    property_type: Optional[str]
    period: Optional[str]
    neighborhood: Optional[str]
    price: Optional[float]
    currency: Optional[str]
    bedrooms: Optional[int]
    contact_phone: Optional[str]
    confidence: float
    is_reviewed: bool
    created_at: datetime

    class Config:
        from_attributes = True


class GroupPostList(BaseModel):
    items: List[GroupPostSchema]
    total: int
    page: int
    page_size: int


@router.get("", response_model=GroupPostList)
async def list_group_posts(
    kind: Optional[PostKind] = Query(None, description="oferta | demanda"),
    neighborhood: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Lista los posts de grupos clasificados (oferta/demanda), más recientes primero."""
    base = select(GroupPost).where(GroupPost.is_archived == False)  # noqa: E712
    if kind:
        base = base.where(GroupPost.kind == kind)
    if neighborhood:
        base = base.where(GroupPost.neighborhood == neighborhood)

    total = await db.scalar(select(func.count()).select_from(base.subquery()))
    result = await db.execute(
        base.order_by(desc(GroupPost.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = result.scalars().all()
    return GroupPostList(
        items=[GroupPostSchema.model_validate(p) for p in items],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


class TriggerResponse(BaseModel):
    message: str


@router.post("/trigger", response_model=TriggerResponse)
async def trigger_group_scraping(
    background_tasks: BackgroundTasks,
    _admin: User = Depends(require_admin),
):
    """
    Dispara una revisión de los grupos de Facebook configurados.
    Requiere FB_SESSION_COOKIE y FB_GROUP_IDS en el entorno. Rol admin.
    """
    from app.scrapers.facebook_groups import run_group_scraping

    background_tasks.add_task(run_group_scraping)
    return TriggerResponse(message="Revisión de grupos de Facebook iniciada")
