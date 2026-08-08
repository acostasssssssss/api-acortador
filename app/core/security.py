"""
Utilidades de seguridad: generación de tokens, hashing de IPs, rate limiting.
"""
import hashlib
import secrets

from app.config import get_settings

settings = get_settings()


def generate_edit_token(length: int = None) -> str:
    """Genera un token seguro para edición de slugs."""
    length = length or settings.EDIT_TOKEN_LENGTH
    return secrets.token_urlsafe(length)


def hash_ip(ip: str) -> str:
    """Hashea una IP para analytics anónimos."""
    return hashlib.sha256(f"{ip}{settings.SECRET_KEY}".encode()).hexdigest()[:16]


def generate_slug_code(length: int = None) -> str:
    """Genera un slug aleatorio usando nanoid-like approach."""
    length = length or settings.DEFAULT_SLUG_LENGTH
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))
