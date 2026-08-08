
"""
Endpoints para crear, editar, redirigir y gestionar URLs acortadas.
"""
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.url import (
    URLCreate, URLResponse, URLEditSlug, URLEditDestination
)
from app.services.url_service import URLService
from app.dependencies import get_request_info, get_db_session

router = APIRouter()


@router.post("/shorten", response_model=URLResponse, status_code=201)
async def create_short_url(
    data: URLCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Crea un nuevo acortado.

    - **target_url**: URL de destino (requerido)
    - **custom_slug**: Slug personalizado (opcional, ej: "promo-verano")
    - **redirect_type**: 301 (permanente) o 307 (temporal, default)
    - **expires_at**: Fecha de expiración (opcional)

    Retorna el **edit_token** necesario para modificar el slug o destino.
    """
    result = await URLService.create_url(db, data)
    return result


@router.get("/{slug_code}")
async def redirect_to_url(
    slug_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Redirige al destino original y registra analytics.

    - Si el slug expiró: 410 Gone
    - Si no existe: 404 Not Found
    """
    request_info = await get_request_info(request)
    target_url = await URLService.redirect(db, slug_code, request_info)

    # Obtener redirect_type del slug
    slug = await URLService.get_by_slug(db, slug_code)
    status_code = int(slug.redirect_type) if slug else 307

    return RedirectResponse(url=target_url, status_code=status_code)


@router.patch("/{slug_code}/slug", response_model=dict)
async def edit_slug_name(
    slug_code: str,
    data: URLEditSlug,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Renombra el slug (el "nombre" del acortado).

    Ej: cambiar `tuapp.com/promo-verano` → `tuapp.com/oferta-2026`

    - Preserva analytics (los clicks usan ID interno, no el code)
    - El slug anterior queda reservado por 30 días
    """
    return await URLService.edit_slug(db, slug_code, data)


@router.patch("/{slug_code}/destination", response_model=dict)
async def edit_destination_url(
    slug_code: str,
    data: URLEditDestination,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Cambia la URL de destino sin afectar el slug.

    Ej: `mi-promo` seguirá siendo `mi-promo` pero ahora apunta a otra página.

    - Guarda historial de cambios
    - El slug sigue funcionando inmediatamente
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

    - Requiere edit_token
    - Los datos se preservan para analytics
    - El slug queda inactivo
    """
    return await URLService.delete_slug(db, slug_code, edit_token)


@router.get("/{slug_code}/info", response_model=URLResponse)
async def get_url_info(
    slug_code: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Obtiene información de un acortado sin redirigir.
    """
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
