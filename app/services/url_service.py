"""
Lógica de negocio central del acortador.
Desacopla slugs de destinos para permitir edición total.
"""
from datetime import datetime, timezone  # ← agregado 'timezone'
from typing import Optional

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.url import Destination, Slug, Click, DestinationHistory, SlugHistory
from app.schemas.url import URLCreate, URLEditSlug, URLEditDestination
from app.core.security import generate_edit_token, generate_slug_code, hash_ip
from app.config import get_settings

settings = get_settings()


class URLService:
    """Servicio para gestionar URLs acortadas."""

    @staticmethod
    async def create_url(db: AsyncSession, data: URLCreate) -> dict:
        """
        Crea un nuevo acortado.
        Si custom_slug se proporciona, se usa; si no, se genera uno aleatorio.
        """
        target_url = str(data.target_url)

        # Verificar si ya existe el destino (deduplicación opcional)
        result = await db.execute(
            select(Destination).where(Destination.target_url == target_url)
        )
        destination = result.scalar_one_or_none()

        if not destination:
            destination = Destination(target_url=target_url)
            db.add(destination)
            await db.flush()  # Obtener ID sin commit

        # Generar o validar slug
        slug_code = data.custom_slug
        if slug_code:
            # Verificar que no exista
            existing = await db.execute(
                select(Slug).where(Slug.code == slug_code)
            )
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=409, detail="Slug ya existe. Prueba otro.")
        else:
            # Generar slug único
            while True:
                slug_code = generate_slug_code()
                existing = await db.execute(
                    select(Slug).where(Slug.code == slug_code)
                )
                if not existing.scalar_one_or_none():
                    break

        edit_token = generate_edit_token()

        slug = Slug(
            code=slug_code,
            destination_id=destination.id,
            edit_token=edit_token,
            redirect_type=data.redirect_type,
            expires_at=data.expires_at,
        )
        db.add(slug)
        await db.commit()
        await db.refresh(slug)

        return {
            "short_url": f"{settings.BASE_URL}/{slug_code}",
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
        """Obtiene un slug por su código."""
        result = await db.execute(
            select(Slug)
            .where(Slug.code == slug_code)
            .where(Slug.is_active == True)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def redirect(db: AsyncSession, slug_code: str, request_info: dict) -> str:
        """
        Procesa una redirección y registra analytics.
        Retorna la URL destino.
        """
        slug = await URLService.get_by_slug(db, slug_code)

        if not slug:
            raise HTTPException(status_code=404, detail="Slug no encontrado o inactivo.")

        # Verificar expiración ← CAMBIO AQUÍ
        if slug.expires_at and slug.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="Este link ha expirado.")

        # Registrar click
        click = Click(
            slug_id=slug.id,
            ip_hash=hash_ip(request_info.get("ip", "unknown")),
            user_agent=request_info.get("user_agent"),
            referrer=request_info.get("referrer"),
            country=request_info.get("country"),
        )
        db.add(click)
        await db.commit()

        return slug.destination.target_url

    @staticmethod
    async def edit_slug(db: AsyncSession, slug_code: str, data: URLEditSlug) -> dict:
        """
        Renombra un slug existente.
        Preserva analytics porque los clicks apuntan a slug_id (UUID), no al code.
        """
        result = await db.execute(select(Slug).where(Slug.code == slug_code))
        slug = result.scalar_one_or_none()

        if not slug:
            raise HTTPException(status_code=404, detail="Slug no encontrado.")

        if slug.edit_token != data.edit_token:
            raise HTTPException(status_code=403, detail="Token de edición inválido.")

        # Verificar que el nuevo slug no exista
        new_code = data.new_slug
        existing = await db.execute(select(Slug).where(Slug.code == new_code))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Nuevo slug ya está en uso.")

        # Guardar historial
        history = SlugHistory(
            slug_id=slug.id,
            old_code=slug.code,
            new_code=new_code,
        )
        db.add(history)

        # Actualizar slug
        old_code = slug.code
        slug.code = new_code
        await db.commit()
        await db.refresh(slug)

        return {
            "message": "Slug actualizado correctamente.",
            "old_slug": old_code,
            "new_slug": new_code,
            "short_url": f"{settings.BASE_URL}/{new_code}",
        }

    @staticmethod
    async def edit_destination(
        db: AsyncSession, slug_code: str, data: URLEditDestination
    ) -> dict:
        """
        Cambia la URL destino de un slug.
        El slug sigue funcionando, ahora apunta al nuevo destino.
        """
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

        # Guardar historial
        history = DestinationHistory(
            destination_id=slug.destination_id,
            old_target_url=old_target,
            new_target_url=new_target,
        )
        db.add(history)

        # Actualizar destino ← CAMBIO AQUÍ
        slug.destination.target_url = new_target
        slug.destination.updated_at = datetime.now(timezone.utc)
        await db.commit()

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

        # Total clicks
        total = await db.execute(
            select(func.count(Click.id)).where(Click.slug_id == slug.id)
        )
        total_clicks = total.scalar()

        # Clicks únicos (por ip_hash)
        unique = await db.execute(
            select(func.count(func.distinct(Click.ip_hash)))
            .where(Click.slug_id == slug.id)
        )
        unique_clicks = unique.scalar()

        # Último click
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

        return {"message": "Slug desactivado correctamente.", "slug": slug_code}

    @staticmethod
    async def list_all_urls(db: AsyncSession) -> dict:
        """
        Lista todos los slugs activos con sus stats básicas.
        """
        from sqlalchemy.orm import joinedload

        result = await db.execute(
            select(Slug)
            .options(joinedload(Slug.destination))
            .where(Slug.is_active == True)
            .order_by(desc(Slug.created_at))
        )
        slugs = result.unique().scalars().all()

        items = []
        for slug in slugs:
            # Contar clicks
            total = await db.execute(
                select(func.count(Click.id)).where(Click.slug_id == slug.id)
            )
            total_clicks = total.scalar() or 0

            items.append({
                "id": str(slug.id),
                "slug": slug.code,
                "short_url": f"{settings.BASE_URL}/{slug.code}",
                "target_url": slug.destination.target_url,
                "redirect_type": slug.redirect_type,
                "is_active": slug.is_active,
                "total_clicks": total_clicks,
                "created_at": slug.created_at,
                "expires_at": slug.expires_at,
            })

        return {
            "items": items,
            "total": len(items),
        }