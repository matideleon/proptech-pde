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
    external_links: List[str] = []
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
    posted_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class GroupPostList(BaseModel):
    items: List[GroupPostSchema]
    total: int
    page: int
    page_size: int
    pages: int


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
    total_count = total or 0
    return GroupPostList(
        items=[GroupPostSchema.model_validate(p) for p in items],
        total=total_count,
        page=page,
        page_size=page_size,
        pages=max(1, -(-total_count // page_size)),
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


@router.get("/debug")
async def debug_group_fetch(
    group_id: Optional[str] = None,
    login: bool = Query(False, description="Si True, intenta el login paso a paso y reporta dónde falla"),
    _admin: User = Depends(require_admin),
):
    """Diagnóstico: muestra qué responde Facebook al traer un grupo (admin)."""
    from app.scrapers.facebook_groups import FacebookGroupScraper

    scraper = FacebookGroupScraper()
    if login:
        return await scraper.diagnose_login()
    return await scraper.diagnose(group_id)


@router.post("/reset-session")
async def reset_fb_session(_admin: User = Depends(require_admin)):
    """Borra el perfil Playwright persistente (fuerza re-seed de FB_XS / re-login)."""
    from app.scrapers.facebook_groups import FacebookGroupScraper

    scraper = FacebookGroupScraper()
    return await scraper.reset_profile()


class SetCookieRequest(BaseModel):
    xs: str
    c_user: Optional[str] = None


@router.post("/set-cookie")
async def set_fb_cookie(payload: SetCookieRequest, _admin: User = Depends(require_admin)):
    """Renueva la cookie de Facebook SIN redeploy.

    El usuario pega el valor `xs` de su navegador logueado a FB y la sesión
    queda activa en el próximo scrape. No requiere editar el compose ni Implementar.
    """
    from app.scrapers.facebook_groups import FacebookGroupScraper

    scraper = FacebookGroupScraper()
    return await scraper.set_cookie(payload.xs, payload.c_user)


class CleanupResponse(BaseModel):
    deleted: int
    remaining: int


@router.post("/cleanup", response_model=CleanupResponse)
async def cleanup_junk_posts(
    all: bool = Query(False, description="Si True, borra TODOS los group-posts (no solo la basura)"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """
    Borra posts basura: los que NO son publicaciones reales sino el encabezado
    público del grupo o el muro de login que FB sirve con sesión vencida
    (texto que arranca con "Información sobre este grupo", gate de login, etc.).

    Con ?all=true borra TODOS los group-posts — útil para rehacer el dataset
    desde cero tras un cambio en la limpieza/clasificación. Admin.
    """
    from sqlalchemy import delete, or_

    if all:
        result = await db.execute(delete(GroupPost))
    else:
        junk_prefixes = [
            "Información sobre este grupo%",
            "%Hay más contenido para ver%",
            "%Iniciar sesión Crear cuenta nueva%",
            "%Mira más fotos, videos y novedades%",
        ]
        conds = [GroupPost.text.like(p) for p in junk_prefixes]
        result = await db.execute(delete(GroupPost).where(or_(*conds)))

    await db.commit()
    deleted = result.rowcount or 0

    remaining = await db.scalar(select(func.count()).select_from(GroupPost))
    return CleanupResponse(deleted=deleted, remaining=remaining or 0)


# ──────────────────────────────────────────────────────────────────────────────
# Push-batch: recibe group-posts ya scrapeados desde un runner externo
# (GitHub Actions), donde sí hay sesión de FB válida e IP no bloqueada.
# ──────────────────────────────────────────────────────────────────────────────

class RemoteGroupPost(BaseModel):
    group_id: str
    fb_post_id: str
    permalink: Optional[str] = None
    author_name: Optional[str] = None
    author_profile: Optional[str] = None
    external_links: List[str] = []
    text: str
    posted_at: Optional[datetime] = None
    kind: str = "otro"
    operation: Optional[str] = None
    property_type: Optional[str] = None
    period: Optional[str] = None
    neighborhood: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    bedrooms: Optional[int] = None
    contact_phone: Optional[str] = None
    confidence: float = 0.0
    classified_by: str = "keywords"


class PushGroupPostsRequest(BaseModel):
    posts: List[RemoteGroupPost]


class PushGroupPostsResponse(BaseModel):
    received: int
    new: int
    skipped: int


@router.post("/push-batch", response_model=PushGroupPostsResponse)
async def push_group_posts(
    request: PushGroupPostsRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """
    Recibe group-posts scrapeados externamente y los persiste (dedup por
    fb_post_id). Usado por GitHub Actions, que corre el scraper de grupos con
    sesión de FB válida desde una IP no bloqueada. Admin.
    """
    new = skipped = 0

    for rp in request.posts:
        existing = await db.scalar(
            select(GroupPost.id).where(GroupPost.fb_post_id == rp.fb_post_id)
        )
        if existing:
            skipped += 1
            continue
        try:
            kind = PostKind(rp.kind)
        except ValueError:
            kind = PostKind.OTRO
        db.add(GroupPost(
            source="facebook_group",
            group_id=rp.group_id,
            fb_post_id=rp.fb_post_id,
            permalink=rp.permalink,
            author_name=rp.author_name,
            author_profile=rp.author_profile,
            external_links=rp.external_links or [],
            text=rp.text,
            posted_at=rp.posted_at,
            kind=kind,
            operation=rp.operation,
            property_type=rp.property_type,
            period=rp.period,
            neighborhood=rp.neighborhood,
            price=rp.price,
            currency=rp.currency,
            bedrooms=rp.bedrooms,
            contact_phone=rp.contact_phone,
            confidence=rp.confidence,
            classified_by=rp.classified_by,
        ))
        new += 1

    await db.commit()
    return PushGroupPostsResponse(received=len(request.posts), new=new, skipped=skipped)
