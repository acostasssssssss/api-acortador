<div align="center">

# 🔗 LinkForge Backend

**API REST asíncrona de alto rendimiento para acortar URLs con slugs y destinos 100% editables.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon_Cloud-336791?style=flat&logo=postgresql&logoColor=white)](https://neon.tech)
[![Render](https://img.shields.io/badge/Render-Deployed-46E3B7?style=flat&logo=render&logoColor=black)](https://cort-link.onrender.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[🌐 Demo en Render](https://cort-link.onrender.com) • [📚 Swagger Docs](https://cort-link.onrender.com/docs) • [🛠️ Instalación](#-instalación-local) • [📡 Endpoints](#-api-endpoints)

</div>

---

## ✨ Características Principales

- 🔄 **Slug y destino 100% editables** — Renombra el slug o cambia la landing page final en cualquier momento sin perder analíticas ni regenerar enlaces.
- 🌐 **Detección Dinámica de Dominios** — Genera URLs cortas basadas automáticamente en el host y protocolo de la petición entrante (Render, localhost o dominio propio).
- 💓 **Keep-Alive Inteligente para Render** — Auto-ping periódico en segundo plano cada 9 minutos para evitar la suspensión del servicio en la capa gratuita.
- 🔀 **Redirección desde la raíz** — Redirección instantánea visitando `https://cort-link.onrender.com/{slug}`.
- ⏱️ **Auto-expiración** — Enlaces con tiempo de vida configurable (6 días por defecto).
- 🔐 **Privacidad sin cuentas obligatorias** — Modificación y eliminación protegidas mediante `edit_token` único por enlace.
- 📊 **Auditoría e Historial Completo** — Registro cronológico de todos los cambios de slug (`SlugHistory`) y de destino (`DestinationHistory`).
- ⚡ **Stack Asíncrono Moderno** — FastAPI + SQLAlchemy 2.0 + asyncpg con pool resiliente (`pool_pre_ping=True`, `pool_recycle=300`).
- 📋 **Logging Profesional Estructurado** — Registro claro de eventos en consola con formato de fecha, severidad y tags legibles.

---

## 🏗️ Arquitectura del Backend

```
┌─────────────────┐       HTTP Requests        ┌───────────────────────┐
│ Frontend React  │ ─────────────────────────> │   FastAPI (async)     │
│   (Vercel)      │ <───────────────────────── │       (Render)        │
└─────────────────┘      JSON Responses        └───────────────────────┘
                                                           │
                                                           │ asyncpg + pooling
                                                           ▼
                                               ┌───────────────────────┐
                                               │   Neon PostgreSQL     │
                                               │ (Modelos desacoplados)│
                                               └───────────────────────┘
```

### Modelos de Datos Desacoplados:
- **`Destination`**: Almacena la URL destino original.
- **`Slug`**: Almacena el código corto y el `edit_token` (asociado a `Destination`).
- **`Click`**: Métricas de clicks inmutables vinculadas al UUID interno del `Slug`.
- **`SlugHistory`**: Auditoría de renombres (`old_code` ➔ `new_code`).
- **`DestinationHistory`**: Auditoría de destinos (`old_target` ➔ `new_target`).

---

## 📡 API Endpoints

### 🩺 Salud del Sistema y Redirecciones
| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/` | Health check general con metadata del servicio |
| `GET` | `/health` | Endpoint alternativo de verificación de salud |
| `GET` | `/api/v1/health` | Objetivo del keep-alive interno de Render |
| `GET` | `/{slug_code}` | **Redirección inmediata** al destino (registra click y analytics) |

### 🔗 Gestión de Enlaces (`/api/v1/urls`)
| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/v1/urls/shorten` | Crear un enlace acortado (retorna `short_url` y `edit_token`) |
| `GET` | `/api/v1/urls/` | Listar todos los enlaces activos |
| `POST` | `/api/v1/urls/batch-info` | Obtener info en lote para los enlaces guardados en localStorage |
| `GET` | `/api/v1/urls/{slug_code}/info` | Obtener información detallada sin redirigir |
| `PATCH` | `/api/v1/urls/{slug_code}/slug` | **Renombrar slug** (requiere `edit_token`) |
| `PATCH` | `/api/v1/urls/{slug_code}/destination` | **Cambiar URL destino** (requiere `edit_token`) |
| `DELETE` | `/api/v1/urls/{slug_code}` | Desactivar / soft-delete (requiere `edit_token`) |
| `GET` | `/api/v1/urls/{slug_code}/history` | Historial de auditoría de renombres y destinos |

### 📈 Analíticas (`/api/v1/analytics`)
| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/v1/analytics/{slug_code}` | Clicks totales, clicks únicos y fecha del último click |

📚 **Documentación Interactiva:** Accede a `/docs` (Swagger UI) o `/redoc` en tu navegador.

---

## 💻 Ejemplos de Uso con cURL

### 1. Crear un enlace acortado
```bash
curl -X POST "https://cort-link.onrender.com/api/v1/urls/shorten" \
  -H "Content-Type: application/json" \
  -d '{
    "target_url": "https://mi-tienda.com/producto-123",
    "custom_slug": "oferta-verano"
  }'
```

**Respuesta:**
```json
{
  "short_url": "https://cort-link.onrender.com/oferta-verano",
  "slug": "oferta-verano",
  "target_url": "https://mi-tienda.com/producto-123",
  "edit_token": "aB3xK9mP...",
  "redirect_type": "307",
  "created_at": "2026-10-17T18:00:00",
  "expires_at": "2026-10-23T18:00:00",
  "is_active": true
}
```
> ⚠️ **Guarda el `edit_token`**: Es la única clave para renombrar o cambiar el destino del enlace.

### 2. Renombrar un slug
```bash
curl -X PATCH "https://cort-link.onrender.com/api/v1/urls/oferta-verano/slug" \
  -H "Content-Type: application/json" \
  -d '{
    "new_slug": "oferta-navidad",
    "edit_token": "aB3xK9mP..."
  }'
```

### 3. Cambiar URL destino
```bash
curl -X PATCH "https://cort-link.onrender.com/api/v1/urls/oferta-navidad/destination" \
  -H "Content-Type: application/json" \
  -d '{
    "new_target_url": "https://mi-tienda.com/nueva-landing",
    "edit_token": "aB3xK9mP..."
  }'
```

---

## 🛠️ Instalación Local

### Requisitos Previos
- Python 3.12+
- Base de datos PostgreSQL (local o instancia gratuita de [Neon](https://neon.tech))

### Pasos:

1. **Clonar el repositorio y entrar a la carpeta backend:**
   ```bash
   cd BACKEND
   ```

2. **Crear y activar el entorno virtual:**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno:**
   ```bash
   cp .env.example .env
   ```
   Ajusta tu `DATABASE_URL` en el archivo `.env`:
   ```env
   DATABASE_URL=postgresql+asyncpg://usuario:password@host/neondb?ssl=require
   ```

5. **Iniciar el servidor en modo desarrollo:**
   ```bash
   uvicorn app.main:app --reload
   ```
   La API estará disponible en `http://localhost:8000` y la documentación en `http://localhost:8000/docs`.

---

## ⚙️ Variables de Entorno

| Variable | Tipo | Obligatoria | Descripción | Valor por Defecto |
|---|---|:---:|---|---|
| `DATABASE_URL` | String | **Sí** | Conexión PostgreSQL con driver `asyncpg` | - |
| `BASE_URL` | String | No | Dominio forzado para los links (ej: `https://midominio.com`). Si se omite, se detecta automáticamente por petición HTTP | `None` (Detección dinámica) |
| `KEEP_ALIVE_ENABLED` | Bool | No | Activa la tarea de self-ping cada 9 minutos | `true` en Render / `false` en local |
| `RENDER_EXTERNAL_URL` | String | No | Inyectada por Render automáticamente | `https://cort-link.onrender.com` |
| `DEBUG` | Bool | No | Modo depuración | `false` |
| `DB_ECHO` | Bool | No | Imprimir consultas SQL en consola | `false` |
| `REDIS_URL` | String | No | Conexión Redis opcional | `None` |
| `SECRET_KEY` | String | No | Llave secreta de la app | `change-me-in-production-please` |

---

## 🚀 Despliegue en Render

1. Crea un **Web Service** en Render conectado a tu repositorio de GitHub.
2. Configura los siguientes parámetros en Render:
   - **Root Directory:** `BACKEND`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Agrega en **Environment Variables**:
   - `DATABASE_URL` con tu cadena de conexión de Neon (asegúrate de que termine en `?ssl=require`).
4. ¡Listo! Render desplegará el backend y el keep-alive mantendrá despierto el servicio automáticamente.

---

## 📁 Estructura del Código

```text
BACKEND/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── analytics.py   # Endpoints de estadísticas y métricas
│   │       ├── router.py      # Agregador de rutas v1
│   │       └── urls.py       # Endpoints de creación, edición y redirección
│   ├── core/
│   │   ├── logger.py          # Logger estructurado centralizado
│   │   └── security.py        # Generación de tokens y slugs seguros
│   ├── db/
│   │   └── session.py         # Motor SQLAlchemy asyncpg con pooling
│   ├── models/
│   │   └── url.py             # Modelos desacoplados SQLAlchemy
│   ├── schemas/
│   │   └── url.py             # Esquemas de validación Pydantic
│   ├── services/
│   │   └── url_service.py     # Lógica de negocio y detección de dominios
│   ├── config.py              # Ajustes centralizados con pydantic-settings
│   ├── dependencies.py        # Inyección de dependencias (DB, headers)
│   └── main.py                # Punto de entrada FastAPI, lifespan y keep-alive
├── tests/                     # Pruebas unitarias e integración
├── requirements.txt           # Dependencias del proyecto
├── Dockerfile                 # Contenedor para despliegues Docker
└── README.md
```

---

## 📄 Licencia

Este proyecto está bajo la licencia [MIT](LICENSE) — Libre para uso personal, comercial y proyectos de portafolio.
