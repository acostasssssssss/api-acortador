
"""
Validadores adicionales.
"""
import re

from fastapi import HTTPException

from app.config import get_settings

settings = get_settings()


SLUG_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def validate_slug_format(slug: str) -> None:
    """Valida formato de slug."""
    if not SLUG_PATTERN.match(slug):
        raise HTTPException(
            status_code=400,
            detail="Slug inválido. Solo letras, números, guiones y guiones bajos."
        )
    if len(slug) < settings.MIN_SLUG_LENGTH or len(slug) > settings.MAX_SLUG_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Slug debe tener entre {settings.MIN_SLUG_LENGTH} y {settings.MAX_SLUG_LENGTH} caracteres."
        )


def validate_url_scheme(url: str) -> str:
    """Asegura que la URL tenga scheme."""
    if not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400,
            detail="La URL debe comenzar con http:// o https://"
        )
    return url
