"""
Esquemas Pydantic para validación y serialización.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

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
    expires_at: Optional[datetime] = Field(
        None,
        description="Fecha de expiración opcional (permanente si el usuario inició sesión; 6 días si es anónimo)",
    )

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
    edit_token: Optional[str] = Field(None, description="Token secreto para editar")
    redirect_type: str = Field(..., description="301 o 307")
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool
    user_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class URLEditSlug(BaseModel):
    """Request para renombrar el slug."""
    new_slug: str = Field(
        ...,
        min_length=settings.MIN_SLUG_LENGTH,
        max_length=settings.MAX_SLUG_LENGTH,
        description="Nuevo slug"
    )
    edit_token: Optional[str] = Field(
        None,
        description="Token de edición (opcional si eres el usuario propietario autenticado)",
    )

    @field_validator("new_slug")
    @classmethod
    def validate_new_slug(cls, v: str) -> str:
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("El slug solo puede contener letras, números, guiones y guiones bajos")
        return v.lower()


class URLEditDestination(BaseModel):
    """Request para cambiar la URL destino."""
    new_target_url: HttpUrl = Field(..., description="Nueva URL de destino")
    edit_token: Optional[str] = Field(
        None,
        description="Token de edición (opcional si eres el usuario propietario autenticado)",
    )


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

    model_config = ConfigDict(from_attributes=True)


class URLList(BaseModel):
    """Lista paginada de URLs."""
    items: list[URLResponse]
    total: int
    page: int
    page_size: int

class URLListItem(BaseModel):
    """Item de la lista de URLs acortadas."""
    id: str
    slug: str
    short_url: str
    target_url: str
    redirect_type: str
    is_active: bool
    total_clicks: int
    created_at: datetime
    expires_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class URLListResponse(BaseModel):
    """Respuesta paginada de lista de URLs."""
    items: list[URLListItem]
    total: int

class SlugHistoryItem(BaseModel):
    """Item del historial de renombrados de slug."""
    old_code: str
    new_code: str
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DestinationHistoryItem(BaseModel):
    """Item del historial de cambios de destino."""
    old_target_url: str
    new_target_url: str
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class URLHistoryResponse(BaseModel):
    """Respuesta con historial completo de un slug."""
    slug: str
    slug_history: list[SlugHistoryItem]
    destination_history: list[DestinationHistoryItem]

class BatchInfoRequest(BaseModel):
    """Request para consultar info de múltiples slugs."""
    slugs: list[str] = Field(..., min_length=1, max_length=50)


class BatchInfoItem(BaseModel):
    """Info de un slug en batch."""
    slug: str
    short_url: str
    target_url: str
    redirect_type: str
    is_active: bool
    expires_at: Optional[datetime] = None
    total_clicks: int


class BatchInfoResponse(BaseModel):
    """Respuesta batch."""
    items: list[BatchInfoItem]