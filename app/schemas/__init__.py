"""Esquemas Pydantic para request/response."""
from app.schemas.url import (
    URLCreate,
    URLResponse,
    URLEditSlug,
    URLEditDestination,
    URLStats,
    URLList,
)

__all__ = [
    "URLCreate",
    "URLResponse",
    "URLEditSlug",
    "URLEditDestination",
    "URLStats",
    "URLList",
]
