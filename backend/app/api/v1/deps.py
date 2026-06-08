"""FastAPI dependencies — DB, Auth, Rate limiting."""
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import decode_token
from app.db.database import get_db as _get_db
from app.models.user import User, UserRole

logger = get_logger("api.deps")

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Auth scheme
security = HTTPBearer(auto_error=False)


async def get_db(db: AsyncSession = Depends(_get_db)) -> AsyncSession:
    """Dependency para sesión de DB."""
    return db


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Obtener usuario autenticado desde JWT token.
    Lanza 401 si no autenticado.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Token sin subject")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido: {e}",
        )

    result = await db.execute(
        select(User).where(User.id == UUID(user_id), User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
        )

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Usuario autenticado opcional (para rutas públicas/privadas mixtas)."""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


def require_role(*roles: UserRole):
    """Factory de dependency para requerir rol específico."""
    async def _require_role(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere rol: {', '.join(r.value for r in roles)}",
            )
        return current_user
    return _require_role


# Shorthands
require_admin = require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN)
require_analyst = require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.ANALYST)
