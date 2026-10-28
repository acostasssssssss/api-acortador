"""Modelos de base de datos."""
from app.models.user import User
from app.models.url import Destination, Slug, Click, DestinationHistory, SlugHistory

__all__ = ["User", "Destination", "Slug", "Click", "DestinationHistory", "SlugHistory"]
