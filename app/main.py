"""
Punto de entrada de FastAPI.
Configura la app, routers, middlewares y eventos de lifespan.
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router import router as api_router
from app.api.v1.urls import get_db_session, redirect_to_url
from app.config import get_settings
from app.core.logger import logger
from app.db.session import engine, init_db

settings = get_settings()


async def keep_alive_task():
    """Tarea en segundo plano para auto-ping periódico que evita la suspensión del servicio en Render."""
    ping_url = os.getenv(
        "RENDER_EXTERNAL_URL",
        "https://cort-link.onrender.com"
    ).rstrip("/") + "/api/v1/health"

    logger.info("[Keep-Alive] Tarea iniciada. Ping objetivo: %s cada 9 minutos.", ping_url)

    while True:
        try:
            await asyncio.sleep(540)  # 9 minutos
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(ping_url)
                if resp.status_code == 200:
                    logger.info("[Keep-Alive] Ping enviado a Render exitosamente (Status: %s).", resp.status_code)
                else:
                    logger.warning("[Keep-Alive] Ping a Render respondió con código %s.", resp.status_code)
        except asyncio.CancelledError:
            logger.info("[Keep-Alive] Tarea cancelada por apagado del servidor.")
            break
        except Exception as exc:
            logger.error("[Keep-Alive] Error en auto-ping a Render: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la app."""
    # Startup
    logger.info("==================================================")
    logger.info("[LinkForge] %s v%s iniciando...", settings.APP_NAME, settings.APP_VERSION)
    logger.info("[Docs] Documentacion interactiva en: /docs")
    logger.info("==================================================")
    try:
        await init_db()
        logger.info("[Database] Tablas verificadas/inicializadas correctamente.")
    except Exception as e:
        logger.warning("[Database] No se pudo conectar/inicializar DB en startup: %s", e)

    # ── Self-Ping para Render (Keep-Alive inteligente) ──
    keep_alive_task_handle = None
    # Se activa si KEEP_ALIVE_ENABLED=true o si está corriendo en Render (RENDER=true en entorno)
    is_keep_alive = os.getenv("KEEP_ALIVE_ENABLED", "true" if os.getenv("RENDER") else "false").lower() == "true"
    if is_keep_alive:
        keep_alive_task_handle = asyncio.create_task(keep_alive_task())
        logger.info("[Keep-Alive] Activado")
    else:
        logger.info("[Keep-Alive] Desactivado (KEEP_ALIVE_ENABLED!=true)")

    yield

    # Shutdown
    if keep_alive_task_handle:
        keep_alive_task_handle.cancel()
        try:
            await keep_alive_task_handle
        except asyncio.CancelledError:
            pass

    try:
        await engine.dispose()
    except Exception:
        pass
    logger.info("Servidor detenido.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="🔥 Acortador de URLs open source con slugs y destinos 100% editables.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
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


@app.get("/", tags=["Health"])
@app.get("/health", tags=["Health"])
@app.get("/api/v1/health", tags=["Health"])
async def root():
    """Health check."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "docs": "/docs",
    }


@app.get("/{slug_code}", tags=["Redirect"], include_in_schema=False)
async def root_redirect(
    slug_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Redirige al destino original desde la raíz del dominio."""
    return await redirect_to_url(slug_code, request, db)
