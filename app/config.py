"""
Configuración centralizada usando pydantic-settings.
Soporta variables de entorno y valores por defecto.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Configuración de la aplicación."""

    # App
    APP_NAME: str = "LinkForge"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Base URL del acortador
    BASE_URL: str = "http://localhost:8000"

    # Database LOCAL (tu DB: cortlink_db)
    # Si tienes password, agrégalo: postgresql+asyncpg://postgres:TU_PASSWORD@localhost:5432/cortlink_db
    DATABASE_URL: str = "postgresql+asyncpg://postgres@localhost:5432/cortlink_db"
    DB_ECHO: bool = False

    # Redis LOCAL
    REDIS_URL: str = "redis://localhost:6379/0"

    # Seguridad
    SECRET_KEY: str = "change-me-in-production-please"
    EDIT_TOKEN_LENGTH: int = 32

    # Slug generation
    DEFAULT_SLUG_LENGTH: int = 6
    MAX_SLUG_LENGTH: int = 64
    MIN_SLUG_LENGTH: int = 3

    # Rate limiting
    RATE_LIMIT_SHORTEN: str = "10/minute"
    RATE_LIMIT_REDIRECT: str = "100/minute"

    # Features
    ALLOW_CUSTOM_SLUGS: bool = True
    TRACK_ANALYTICS: bool = True
    SLUG_RESERVATION_DAYS: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Retorna instancia cacheada de Settings."""
    return Settings()