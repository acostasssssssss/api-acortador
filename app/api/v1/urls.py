"""
Endpoints para crear, editar, redirigir y gestionar URLs acortadas.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.url import (
    URLCreate,
    URLResponse,
    URLEditSlug,
    URLEditDestination,
    URLListResponse,
    URLHistoryResponse,
    BatchInfoRequest,
    BatchInfoResponse,
)
from app.services.url_service import URLService
from app.dependencies import get_request_info, get_db_session

router = APIRouter()


# ============================================================
# RUTAS ESTÁTICAS (específicas) - VAN PRIMERO
# ============================================================

@router.get("/", response_model=URLListResponse)
async def list_all_short_urls(
    db: AsyncSession = Depends(get_db_session),
):
    """
    Lista todos los links acortados activos con sus estadísticas básicas.
    """
    return await URLService.list_all_urls(db)


@router.post("/shorten", response_model=URLResponse, status_code=201)
async def create_short_url(
    data: URLCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Crea un nuevo acortado.

    - **target_url**: URL de destino (requerido)
    - **custom_slug**: Slug personalizado (opcional)
    - **redirect_type**: 301 o 307 (default)
    - **expires_at**: Fecha de expiración (default: 6 días)

    Retorna el **edit_token** necesario para modificar.
    """
    result = await URLService.create_url(db, data)
    return result


@router.post("/batch-info", response_model=BatchInfoResponse)
async def get_batch_info(
    data: BatchInfoRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Consulta info de múltiples slugs en una sola request.
    Útil para que el frontend cargue "mis links" desde localStorage.
    """
    return await URLService.batch_info(db, data)


# ============================================================
# RUTAS DINÁMICAS (con {slug_code}) - VAN DESPUÉS
# ============================================================

@router.get("/{slug_code}/history", response_model=URLHistoryResponse)
async def get_url_history(
    slug_code: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Obtiene el historial completo de un acortado:
    - **slug_history**: renombrados
    - **destination_history**: cambios de URL destino
    """
    return await URLService.get_history(db, slug_code)


@router.get("/{slug_code}/info", response_model=URLResponse)
async def get_url_info(
    slug_code: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Obtiene información de un acortado sin redirigir."""
    slug = await URLService.get_by_slug(db, slug_code)
    if not slug:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Slug no encontrado.")

    from app.config import get_settings
    settings = get_settings()

    return {
        "short_url": f"{settings.BASE_URL}/{slug.code}",
        "slug": slug.code,
        "target_url": slug.destination.target_url,
        "edit_token": slug.edit_token,
        "redirect_type": slug.redirect_type,
        "created_at": slug.created_at,
        "expires_at": slug.expires_at,
        "is_active": slug.is_active,
    }


@router.patch("/{slug_code}/slug", response_model=dict)
async def edit_slug_name(
    slug_code: str,
    data: URLEditSlug,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Renombra el slug. Preserva analytics.
    """
    return await URLService.edit_slug(db, slug_code, data)


@router.patch("/{slug_code}/destination", response_model=dict)
async def edit_destination_url(
    slug_code: str,
    data: URLEditDestination,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Cambia la URL destino sin afectar el slug.
    """
    return await URLService.edit_destination(db, slug_code, data)


@router.delete("/{slug_code}", response_model=dict)
async def delete_short_url(
    slug_code: str,
    edit_token: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Desactiva (soft-delete) un acortado.
    """
    return await URLService.delete_slug(db, slug_code, edit_token)


@router.get("/{slug_code}")
async def redirect_to_url(
    slug_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Redirige al destino original y registra analytics.
    - Expirado: 410 Gone
    - No existe: 404
    """
    request_info = await get_request_info(request)
    target_url = await URLService.redirect(db, slug_code, request_info)

    slug = await URLService.get_by_slug(db, slug_code)
    status_code = int(slug.redirect_type) if slug else 307

    return RedirectResponse(url=target_url, status_code=status_code)