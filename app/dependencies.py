
"""
Inyección de dependencias globales.
"""
from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.config import get_settings

settings = get_settings()


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
