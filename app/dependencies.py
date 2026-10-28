
"""
Inyección de dependencias globales.
"""
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.config import get_settings
from app.core.security import decode_access_token
from app.models.user import User
from app.services.auth_service import AuthService

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)


async def get_request_info(request: Request) -> dict:
    """Extrae información del request para analytics."""
    return {
        "ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent"),
        "referrer": request.headers.get("referer"),
        "country": request.headers.get("cf-ipcountry"),  # Cloudflare
    }


async def get_db_session() -> AsyncSession:
    """Dependency para sesiones de DB."""
    async for session in get_db():
        yield session


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> Optional[User]:
    """
    Retorna el usuario autenticado si se envía un Bearer token válido.
    Si no se envía header Authorization, retorna None.
    Si se envía un token inválido o expirado, lanza 401.
    """
    if credentials is None:
        return None

    payload = decode_access_token(credentials.credentials)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de sesión inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await AuthService.get_user_by_id(db, payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_user(
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> User:
    """Exige que el usuario haya iniciado sesión."""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Debes iniciar sesión para realizar esta acción.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user
