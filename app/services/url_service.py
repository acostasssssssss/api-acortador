"""
Lógica de negocio central del acortador.
Desacopla slugs de destinos para permitir edición total.
"""
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, Request

from app.models.url import Destination, Slug, Click, DestinationHistory, SlugHistory
from app.schemas.url import URLCreate, URLEditSlug, URLEditDestination, BatchInfoRequest
from app.core.security import generate_edit_token, generate_slug_code, hash_ip
from app.config import get_settings
from app.core.logger import logger

settings = get_settings()


def get_base_url(request: Optional[Request] = None) -> str:
    """
    Retorna la URL base del acortador dinámicamente:
    1. Si BASE_URL está fijada en variables de entorno (que no sea localhost), se prioriza.
    2. Si hay una petición HTTP, detecta automáticamente protocolo y host del cliente (Render, Vercel o dominio propio).
    3. Fallback a RENDER_EXTERNAL_URL o settings.BASE_URL.
    """
    env_base = os.getenv("BASE_URL")
    if env_base and "localhost" not in env_base and "127.0.0.1" not in env_base:
        return env_base.rstrip("/")

    if request:
        proto = request.headers.get("x-forwarded-proto") or request.url.scheme or "https"
        host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
        if host:
            return f"{proto}://{host}".rstrip("/")

    return (settings.BASE_URL or os.getenv("RENDER_EXTERNAL_URL") or "https://cort-link.onrender.com").rstrip("/")


class URLService:
    """Servicio para gestionar URLs acortadas."""

    @staticmethod
    async def create_url(db: AsyncSession, data: URLCreate, request: Optional[Request] = None) -> dict:
        """
        Crea un nuevo acortado.
        Si no se envía expires_at, se pone por defecto: ahora + 6 días.
        """
        target_url = str(data.target_url)

        # Verificar si ya existe el destino
        result = await db.execute(
            select(Destination).where(Destination.target_url == target_url)
        )
        destination = result.scalar_one_or_none()

        if not destination:
            destination = Destination(target_url=target_url)
            db.add(destination)
            await db.flush()

        # Generar o validar slug
        slug_code = data.custom_slug
        if slug_code:
            existing = await db.execute(
                select(Slug).where(Slug.code == slug_code)
            )
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=409, detail="Slug ya existe. Prueba otro.")
        else:
            while True:
                slug_code = generate_slug_code()
                existing = await db.execute(
                    select(Slug).where(Slug.code == slug_code)
                )
                if not existing.scalar_one_or_none():
                    break

        # Calcular expiración por defecto: 6 días
        expires_at = data.expires_at
        if expires_at is None:
            expires_at = datetime.now(timezone.utc) + timedelta(days=6)

        edit_token = generate_edit_token()

        slug = Slug(
            code=slug_code,
            destination_id=destination.id,
            edit_token=edit_token,
            redirect_type=data.redirect_type,
            expires_at=expires_at,
        )
        db.add(slug)
        await db.commit()
        await db.refresh(slug)

        short_url = f"{get_base_url(request)}/{slug_code}"
        logger.info("[Shorten] Nuevo enlace creado: '%s' -> %s", slug_code, target_url)

        return {
            "short_url": short_url,
            "slug": slug_code,
            "target_url": target_url,
            "edit_token": edit_token,
            "redirect_type": data.redirect_type,
            "created_at": slug.created_at,
            "expires_at": slug.expires_at,
            "is_active": slug.is_active,
        }

    @staticmethod
    async def get_by_slug(db: AsyncSession, slug_code: str) -> Optional[Slug]:
        """Obtiene un slug activo por su código."""
        result = await db.execute(
            select(Slug)
            .where(Slug.code == slug_code)
            .where(Slug.is_active == True)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def redirect(db: AsyncSession, slug_code: str, request_info: dict) -> str:
        """Procesa redirección y registra analytics."""
        slug = await URLService.get_by_slug(db, slug_code)

        if not slug:
            raise HTTPException(status_code=404, detail="Slug no encontrado o inactivo.")

        if slug.expires_at and slug.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="Este link ha expirado.")

        click = Click(
            slug_id=slug.id,
            ip_hash=hash_ip(request_info.get("ip", "unknown")),
            user_agent=request_info.get("user_agent"),
            referrer=request_info.get("referrer"),
            country=request_info.get("country"),
        )
        db.add(click)
        await db.commit()

        target = slug.destination.target_url
        logger.info("[Redirect] Redirigiendo '%s' -> %s", slug_code, target)
        return target

    @staticmethod
    async def edit_slug(db: AsyncSession, slug_code: str, data: URLEditSlug, request: Optional[Request] = None) -> dict:
        """Renombra un slug existente. Preserva analytics."""
        result = await db.execute(select(Slug).where(Slug.code == slug_code))
        slug = result.scalar_one_or_none()

        if not slug:
            raise HTTPException(status_code=404, detail="Slug no encontrado.")

        if slug.edit_token != data.edit_token:
            raise HTTPException(status_code=403, detail="Token de edición inválido.")

        new_code = data.new_slug
        existing = await db.execute(select(Slug).where(Slug.code == new_code))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Nuevo slug ya está en uso.")

        history = SlugHistory(
            slug_id=slug.id,
            old_code=slug.code,
            new_code=new_code,
        )
        db.add(history)

        old_code = slug.code
        slug.code = new_code
        await db.commit()
        await db.refresh(slug)

        logger.info("[Edit Slug] Renombrado con éxito: '%s' -> '%s'", old_code, new_code)

        return {
            "message": "Slug actualizado correctamente.",
            "old_slug": old_code,
            "new_slug": new_code,
            "short_url": f"{get_base_url(request)}/{new_code}",
        }

    @staticmethod
    async def edit_destination(
        db: AsyncSession, slug_code: str, data: URLEditDestination
    ) -> dict:
        """Cambia la URL destino de un slug."""
        result = await db.execute(
            select(Slug).where(Slug.code == slug_code)
        )
        slug = result.scalar_one_or_none()

        if not slug:
            raise HTTPException(status_code=404, detail="Slug no encontrado.")

        if slug.edit_token != data.edit_token:
            raise HTTPException(status_code=403, detail="Token de edición inválido.")

        new_target = str(data.new_target_url)
        old_target = slug.destination.target_url

        history = DestinationHistory(
            destination_id=slug.destination_id,
            old_target_url=old_target,
            new_target_url=new_target,
        )
        db.add(history)

        slug.destination.target_url = new_target
        slug.destination.updated_at = datetime.now(timezone.utc)
        await db.commit()

        logger.info("[Edit Dest] Destino cambiado para '%s': '%s' -> '%s'", slug_code, old_target, new_target)

        return {
            "message": "Destino actualizado correctamente.",
            "slug": slug_code,
            "old_target": old_target,
            "new_target": new_target,
        }

    @staticmethod
    async def get_stats(db: AsyncSession, slug_code: str) -> dict:
        """Obtiene estadísticas de un slug."""
        result = await db.execute(
            select(Slug).where(Slug.code == slug_code)
        )
        slug = result.scalar_one_or_none()

        if not slug:
            raise HTTPException(status_code=404, detail="Slug no encontrado.")

        total = await db.execute(
            select(func.count(Click.id)).where(Click.slug_id == slug.id)
        )
        total_clicks = total.scalar()

        unique = await db.execute(
            select(func.count(func.distinct(Click.ip_hash)))
            .where(Click.slug_id == slug.id)
        )
        unique_clicks = unique.scalar()

        last = await db.execute(
            select(Click.clicked_at)
            .where(Click.slug_id == slug.id)
            .order_by(desc(Click.clicked_at))
            .limit(1)
        )
        last_click = last.scalar_one_or_none()

        return {
            "slug": slug_code,
            "target_url": slug.destination.target_url,
            "total_clicks": total_clicks,
            "unique_clicks": unique_clicks,
            "created_at": slug.created_at,
            "last_clicked_at": last_click,
        }

    @staticmethod
    async def delete_slug(db: AsyncSession, slug_code: str, edit_token: str) -> dict:
        """Soft-delete de un slug."""
        result = await db.execute(select(Slug).where(Slug.code == slug_code))
        slug = result.scalar_one_or_none()

        if not slug:
            raise HTTPException(status_code=404, detail="Slug no encontrado.")

        if slug.edit_token != edit_token:
            raise HTTPException(status_code=403, detail="Token de edición inválido.")

        slug.is_active = False
        await db.commit()

        logger.info("[Delete] Enlace desactivado: '%s'", slug_code)

        return {"message": "Slug desactivado correctamente.", "slug": slug_code}

    @staticmethod
    async def list_all_urls(db: AsyncSession, request: Optional[Request] = None) -> dict:
        """Lista todos los slugs activos con stats básicas."""
        result = await db.execute(
            select(Slug)
            .options(joinedload(Slug.destination))
            .where(Slug.is_active == True)
            .order_by(desc(Slug.created_at))
        )
        slugs = result.unique().scalars().all()
        base_url = get_base_url(request)

        items = []
        for slug in slugs:
            total = await db.execute(
                select(func.count(Click.id)).where(Click.slug_id == slug.id)
            )
            total_clicks = total.scalar() or 0

            items.append({
                "id": str(slug.id),
                "slug": slug.code,
                "short_url": f"{base_url}/{slug.code}",
                "target_url": slug.destination.target_url,
                "redirect_type": slug.redirect_type,
                "is_active": slug.is_active,
                "total_clicks": total_clicks,
                "created_at": slug.created_at,
                "expires_at": slug.expires_at,
            })

        return {"items": items, "total": len(items)}

    @staticmethod
    async def batch_info(db: AsyncSession, data: BatchInfoRequest, request: Optional[Request] = None) -> dict:
        """
        Consulta info de múltiples slugs en una sola request.
        """
        result = await db.execute(
            select(Slug)
            .options(joinedload(Slug.destination))
            .where(Slug.code.in_(data.slugs))
            .where(Slug.is_active == True)
        )
        slugs = result.unique().scalars().all()
        base_url = get_base_url(request)

        items = []
        for slug in slugs:
            total = await db.execute(
                select(func.count(Click.id)).where(Click.slug_id == slug.id)
            )
            total_clicks = total.scalar() or 0

            items.append({
                "slug": slug.code,
                "short_url": f"{base_url}/{slug.code}",
                "target_url": slug.destination.target_url,
                "redirect_type": slug.redirect_type,
                "is_active": slug.is_active,
                "expires_at": slug.expires_at,
                "total_clicks": total_clicks,
            })

        return {"items": items}

    @staticmethod
    async def get_history(db: AsyncSession, slug_code: str) -> dict:
        """Obtiene historial de renombrados y cambios de destino."""
        result = await db.execute(
            select(Slug)
            .options(joinedload(Slug.destination))
            .where(Slug.code == slug_code)
        )
        slug = result.unique().scalar_one_or_none()

        if not slug:
            raise HTTPException(status_code=404, detail="Slug no encontrado.")

        slug_hist_result = await db.execute(
            select(SlugHistory)
            .where(SlugHistory.slug_id == slug.id)
            .order_by(desc(SlugHistory.changed_at))
        )
        slug_history = [
            {
                "old_code": h.old_code,
                "new_code": h.new_code,
                "changed_at": h.changed_at,
            }
            for h in slug_hist_result.scalars().all()
        ]

        dest_hist_result = await db.execute(
            select(DestinationHistory)
            .where(DestinationHistory.destination_id == slug.destination_id)
            .order_by(desc(DestinationHistory.changed_at))
        )
        destination_history = [
            {
                "old_target_url": h.old_target_url,
                "new_target_url": h.new_target_url,
                "changed_at": h.changed_at,
            }
            for h in dest_hist_result.scalars().all()
        ]

        return {
            "slug": slug_code,
            "slug_history": slug_history,
            "destination_history": destination_history,
        }