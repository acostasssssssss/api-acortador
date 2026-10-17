"""
Configuración centralizada de logging para LinkForge.
Genera logs limpios, estructurados y fáciles de identificar en terminal y en Render.
"""
import logging
import sys

# Configurar stdout para soportar UTF-8 de manera segura tanto en Windows como en Linux/Render
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logger = logging.getLogger("linkforge")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
