"""
Esquemas Pydantic para validación y serialización.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.config import get_settings

settings = get_settings()


class URLCreate(BaseModel):
    """Request para crear un acortado."""
    target_url: HttpUrl = Field(..., description="URL de destino")
    custom_slug: Optional[str] = Field(
        None,
        min_length=settings.MIN_SLUG_LENGTH,
        max_length=settings.MAX_SLUG_LENGTH,
        description="Slug personalizado (opcional)"
    )
    redirect_type: str = Field(
        default="307",
        pattern="^(301|307)$",
        description="Tipo de redirección: 301 (permanente) o 307 (temporal)"
    )
    expires_at: Optional[datetime] = Field(None, description="Fecha de expiración")

    @field_validator("custom_slug")
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        # Solo letras, números, guiones y guiones bajos
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("El slug solo puede contener letras, números, guiones y guiones bajos")
        return v.lower()


class URLResponse(BaseModel):
    """Response al crear/acceder a un acortado."""
    short_url: str = Field(..., description="URL completa del acortado")
    slug: str = Field(..., description="Código del slug")
    target_url: str = Field(..., description="URL de destino actual")
    edit_token: str = Field(..., description="Token secreto para editar")
    redirect_type: str = Field(..., description="301 o 307")
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool

    class Config:
        from_attributes = True


class URLEditSlug(BaseModel):
    """Request para renombrar el slug."""
    new_slug: str = Field(
        ...,
        min_length=settings.MIN_SLUG_LENGTH,
        max_length=settings.MAX_SLUG_LENGTH,
        description="Nuevo slug"
    )
    edit_token: str = Field(..., description="Token de edición")

    @field_validator("new_slug")
    @classmethod
    def validate_new_slug(cls, v: str) -> str:
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("El slug solo puede contener letras, números, guiones y guiones bajos")
        return v.lower()


class URLEditDestination(BaseModel):
    """Request para cambiar la URL destino."""
    new_target_url: HttpUrl = Field(..., description="Nueva URL de destino")
    edit_token: str = Field(..., description="Token de edición")


class URLStats(BaseModel):
    """Estadísticas de un acortado."""
    slug: str
    target_url: str
    total_clicks: int
    unique_clicks: int
    created_at: datetime
    last_clicked_at: Optional[datetime] = None
    top_referrers: list[dict] = []
    clicks_by_day: list[dict] = []

    class Config:
        from_attributes = True


class URLList(BaseModel):
    """Lista paginada de URLs."""
    items: list[URLResponse]
    total: int
    page: int
    page_size: int
