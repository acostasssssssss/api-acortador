
"""
Agregador de routers de la API v1.
"""
from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.urls import router as urls_router
from app.api.v1.analytics import router as analytics_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["Auth"])
router.include_router(urls_router, prefix="/urls", tags=["URLs"])
router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
