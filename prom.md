
Bien, ahora ayúdame con lo siguiente. Guiándote de este código, me vas a ayudar a implementarlo en el main para evitar que el render se duerma, que es cada 15 minutos, entonces vas a hacer una petición al health de este código cada 9 minutos guiándote de esto para evitar que se duerma el servidor.

entonces como quedaria este es el url https://cort-link.onrender.com/

async def keep_alive_task():
    """Tarea en segundo plano para auto-ping periódico que evita la suspensión del servicio en Render."""
    ping_url = os.getenv(
        "RENDER_EXTERNAL_URL",
        "https://creditrack-backend-ntg8.onrender.com"
    ).rstrip("/") + "/api/v1/health"

    logger.info("[Keep-Alive] Tarea iniciada. Ping objetivo: %s cada 9 minutos.", ping_url)

    while True:
        try:
            await asyncio.sleep(540)  # 9 minutos
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(ping_url)
                if resp.status_code == 200:
                    print("[Keep-Alive] Ping enviado a Render.")
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
    """Arranque y apagado de la app."""
    logger.info("Iniciando %s...", settings.PROJECT_NAME)
    await init_db()  # Crea tablas automáticamente (Cambiar a Alembic luego)
    logger.info("Tablas verificadas. Servidor listo.")

    # ── Self-Ping para Render (Keep-Alive inteligente) ──
    keep_alive_task_handle = None
    is_keep_alive = os.getenv("KEEP_ALIVE_ENABLED", "false").lower() == "true"
    if is_keep_alive:
        keep_alive_task_handle = asyncio.create_task(keep_alive_task())
        print("[Keep-Alive] Activado")
        logger.info("[Keep-Alive] Activado")
    else:
        logger.info("[Keep-Alive] Desactivado (KEEP_ALIVE_ENABLED!=true)")

    yield

    if keep_alive_task_handle:
        keep_alive_task_handle.cancel()
        try:
            await keep_alive_task_handle
        except asyncio.CancelledError:
            pass

    await close_db()
    logger.info("Servidor detenido.")

