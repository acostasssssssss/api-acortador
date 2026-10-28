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
from app.models.user import User
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
    def _authorize_slug_mutation(
        slug: Slug,
        current_user: Optional[User] = None,
        edit_token: Optional[str] = None,
    ) -> None:
        """
        Verifica que quien modifica o elimina un enlace tenga permiso:
        - Si el enlace pertenece a una cuenta (user_id != None):
          * El propietario autenticado tiene acceso directo.
          * Otra cuenta autenticada recibe 403 (aislamiento multi-tenant).
          * Sin sesión, se permite solo si presenta el edit_token válido del enlace.
        - Si el enlace es anónimo (user_id == None):
          * Requiere edit_token válido.
        """
        if slug.user_id is not None:
            if current_user is not None:
                if slug.user_id != current_user.id:
                    raise HTTPException(
                        status_code=403,
                        detail="No tienes permiso para modificar un enlace de otra cuenta.",
                    )
                return
            if edit_token and slug.edit_token == edit_token:
                return
            raise HTTPException(
                status_code=403,
                detail="Debes iniciar sesión con la cuenta propietaria o proporcionar un token de edición válido.",
            )

        if not edit_token or slug.edit_token != edit_token:
            raise HTTPException(status_code=403, detail="Token de edición inválido.")

    @staticmethod
    def _authorize_slug_tenant_access(
        slug: Slug,
        current_user: Optional[User] = None,
    ) -> None:
        """Evita que una cuenta autenticada consulte detalles privados de otra cuenta."""
        if (
            slug.user_id is not None
            and current_user is not None
            and slug.user_id != current_user.id
        ):
            raise HTTPException(
                status_code=403,
                detail="No tienes permiso para acceder a un enlace de otra cuenta.",
            )

    @staticmethod
    async def create_url(
        db: AsyncSession,
        data: URLCreate,
        request: Optional[Request] = None,
        current_user: Optional[User] = None,
    ) -> dict:
        """
        Crea un nuevo acortado.
        - Con sesión iniciada: el enlace pertenece al usuario y es permanente (sin expiración automática)
          salvo que el usuario envíe expires_at explícitamente.
        - Sin sesión (anónimo): expira por defecto en 6 días.
        """
        target_url = str(data.target_url)

        # Crear un Destination dedicado para este enlace para que futuras ediciones
        # no modifiquen los enlaces de otros usuarios.
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

        # Expiración: permanente para usuarios autenticados; 6 días para enlaces anónimos
        expires_at = data.expires_at
        if expires_at is None and current_user is None:
            expires_at = datetime.now(timezone.utc) + timedelta(
                days=settings.ANONYMOUS_LINK_EXPIRE_DAYS
            )

        edit_token = generate_edit_token()

        slug = Slug(
            code=slug_code,
            destination_id=destination.id,
            user_id=current_user.id if current_user else None,
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
            "user_id": slug.user_id,
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
    async def edit_slug(
        db: AsyncSession,
        slug_code: str,
        data: URLEditSlug,
        request: Optional[Request] = None,
        current_user: Optional[User] = None,
    ) -> dict:
        """Renombra un slug existente. Preserva analytics."""
        result = await db.execute(select(Slug).where(Slug.code == slug_code))
        slug = result.scalar_one_or_none()

        if not slug:
            raise HTTPException(status_code=404, detail="Slug no encontrado.")

        URLService._authorize_slug_mutation(slug, current_user=current_user, edit_token=data.edit_token)

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
        db: AsyncSession,
        slug_code: str,
        data: URLEditDestination,
        current_user: Optional[User] = None,
    ) -> dict:
        """Cambia la URL destino de un slug."""
        result = await db.execute(
            select(Slug).where(Slug.code == slug_code)
        )
        slug = result.scalar_one_or_none()

        if not slug:
            raise HTTPException(status_code=404, detail="Slug no encontrado.")

        URLService._authorize_slug_mutation(slug, current_user=current_user, edit_token=data.edit_token)

        new_target = str(data.new_target_url)
        old_target = slug.destination.target_url

        shared_count_result = await db.execute(
            select(func.count(Slug.id)).where(Slug.destination_id == slug.destination_id)
        )
        shared_count = shared_count_result.scalar() or 1

        if shared_count > 1:
            new_destination = Destination(target_url=new_target)
            db.add(new_destination)
            await db.flush()
            slug.destination_id = new_destination.id
            target_dest_id = new_destination.id
        else:
            slug.destination.target_url = new_target
            slug.destination.updated_at = datetime.now(timezone.utc)
            target_dest_id = slug.destination_id

        history = DestinationHistory(
            destination_id=target_dest_id,
            old_target_url=old_target,
            new_target_url=new_target,
        )
        db.add(history)
        await db.commit()

        logger.info("[Edit Dest] Destino cambiado para '%s': '%s' -> '%s'", slug_code, old_target, new_target)

        return {
            "message": "Destino actualizado correctamente.",
            "slug": slug_code,
            "old_target": old_target,
            "new_target": new_target,
        }

    @staticmethod
    async def get_stats(
        db: AsyncSession,
        slug_code: str,
        current_user: Optional[User] = None,
    ) -> dict:
        """Obtiene estadísticas de un slug."""
        result = await db.execute(
            select(Slug).where(Slug.code == slug_code)
        )
        slug = result.scalar_one_or_none()

        if not slug:
            raise HTTPException(status_code=404, detail="Slug no encontrado.")

        URLService._authorize_slug_tenant_access(slug, current_user=current_user)

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
    async def delete_slug(
        db: AsyncSession,
        slug_code: str,
        edit_token: Optional[str] = None,
        current_user: Optional[User] = None,
    ) -> dict:
        """Soft-delete de un slug."""
        result = await db.execute(select(Slug).where(Slug.code == slug_code))
        slug = result.scalar_one_or_none()

        if not slug:
            raise HTTPException(status_code=404, detail="Slug no encontrado.")

        URLService._authorize_slug_mutation(slug, current_user=current_user, edit_token=edit_token)

        slug.is_active = False
        await db.commit()

        logger.info("[Delete] Enlace desactivado: '%s'", slug_code)

        return {"message": "Slug desactivado correctamente.", "slug": slug_code}

    @staticmethod
    async def list_all_urls(
        db: AsyncSession,
        request: Optional[Request] = None,
        current_user: Optional[User] = None,
    ) -> dict:
        """
        Lista los enlaces activos de la cuenta autenticada (aislamiento multi-tenant).
        Si no hay sesión iniciada, retorna lista vacía para no exponer enlaces de otros usuarios.
        """
        if current_user is None:
            return {"items": [], "total": 0}

        result = await db.execute(
            select(Slug)
            .options(joinedload(Slug.destination))
            .where(Slug.is_active == True)
            .where(Slug.user_id == current_user.id)
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
    async def get_history(
        db: AsyncSession,
        slug_code: str,
        current_user: Optional[User] = None,
    ) -> dict:
        """Obtiene historial de renombrados y cambios de destino."""
        result = await db.execute(
            select(Slug)
            .options(joinedload(Slug.destination))
            .where(Slug.code == slug_code)
        )
        slug = result.unique().scalar_one_or_none()

        if not slug:
            raise HTTPException(status_code=404, detail="Slug no encontrado.")

        URLService._authorize_slug_tenant_access(slug, current_user=current_user)

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