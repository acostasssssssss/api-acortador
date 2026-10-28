
"""
Endpoints de analytics para URLs acortadas.
"""
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.url_service import URLService
from app.schemas.url import URLStats
from app.dependencies import get_db_session, get_optional_current_user

router = APIRouter()


@router.get("/{slug_code}", response_model=URLStats)
async def get_url_stats(
    slug_code: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Obtiene estadísticas de un acortado:
    - Total de clicks
    - Clicks únicos (por IP hasheado)
    - Último click
    - Fecha de creación
    """
    return await URLService.get_stats(db, slug_code, current_user=current_user)
