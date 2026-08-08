"""
Punto de entrada de FastAPI.
Configura la app, routers, middlewares y eventos de lifespan.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as api_router
from app.config import get_settings
from app.db.session import init_db


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la app."""
    # Startup
    await init_db()
    yield
    # Shutdown
    pass


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="🔥 Acortador de URLs open source con slugs y destinos 100% editables.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Health check."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }
