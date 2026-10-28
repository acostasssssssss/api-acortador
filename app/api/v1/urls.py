"""
Endpoints para crear, editar, redirigir y gestionar URLs acortadas.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
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
from app.services.url_service import URLService, get_base_url
from app.dependencies import (
    get_current_user,
    get_db_session,
    get_optional_current_user,
    get_request_info,
)

router = APIRouter()


# ============================================================
# RUTAS ESTÁTICAS (específicas) - VAN PRIMERO
# ============================================================

@router.get("/", response_model=URLListResponse)
async def list_all_short_urls(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Lista todos los links acortados activos pertenecientes a la cuenta autenticada.
    """
    return await URLService.list_all_urls(db, request=request, current_user=current_user)


@router.post("/shorten", response_model=URLResponse, status_code=201)
async def create_short_url(
    data: URLCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Crea un nuevo acortado.

    - **target_url**: URL de destino (requerido)
    - **custom_slug**: Slug personalizado (opcional)
    - **redirect_type**: 301 o 307 (default)
    - **expires_at**: Fecha de expiración (permanente si iniciaste sesión; 6 días si es anónimo)

    Retorna el **edit_token** necesario para modificar.
    """
    result = await URLService.create_url(
        db, data, request=request, current_user=current_user
    )
    return result


@router.post("/batch-info", response_model=BatchInfoResponse)
async def get_batch_info(
    data: BatchInfoRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Consulta info de múltiples slugs en una sola request.
    Útil para que el frontend cargue "mis links" desde localStorage.
    """
    return await URLService.batch_info(db, data, request=request)


# ============================================================
# RUTAS DINÁMICAS (con {slug_code}) - VAN DESPUÉS
# ============================================================

@router.get("/{slug_code}/history", response_model=URLHistoryResponse)
async def get_url_history(
    slug_code: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Obtiene el historial completo de un acortado:
    - **slug_history**: renombrados
    - **destination_history**: cambios de URL destino
    """
    return await URLService.get_history(db, slug_code, current_user=current_user)


@router.get("/{slug_code}/info", response_model=URLResponse)
async def get_url_info(
    slug_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Obtiene información de un acortado sin redirigir."""
    slug = await URLService.get_by_slug(db, slug_code)
    if not slug:
        raise HTTPException(status_code=404, detail="Slug no encontrado.")

    base_url = get_base_url(request)
    is_owner = (
        current_user is not None
        and slug.user_id is not None
        and slug.user_id == current_user.id
    )

    return {
        "short_url": f"{base_url}/{slug.code}",
        "slug": slug.code,
        "target_url": slug.destination.target_url,
        "edit_token": slug.edit_token if is_owner else None,
        "redirect_type": slug.redirect_type,
        "created_at": slug.created_at,
        "expires_at": slug.expires_at,
        "is_active": slug.is_active,
        "user_id": slug.user_id,
    }


@router.patch("/{slug_code}/slug", response_model=dict)
async def edit_slug_name(
    slug_code: str,
    data: URLEditSlug,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Renombra el slug. Preserva analytics.
    """
    return await URLService.edit_slug(
        db, slug_code, data, request=request, current_user=current_user
    )


@router.patch("/{slug_code}/destination", response_model=dict)
async def edit_destination_url(
    slug_code: str,
    data: URLEditDestination,
    db: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Cambia la URL destino sin afectar el slug.
    """
    return await URLService.edit_destination(
        db, slug_code, data, current_user=current_user
    )


@router.delete("/{slug_code}", response_model=dict)
async def delete_short_url(
    slug_code: str,
    edit_token: Optional[str] = Query(
        None,
        description="Token de edición (opcional si eres el usuario propietario autenticado)",
    ),
    db: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Desactiva (soft-delete) un acortado.
    """
    return await URLService.delete_slug(
        db, slug_code, edit_token=edit_token, current_user=current_user
    )


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