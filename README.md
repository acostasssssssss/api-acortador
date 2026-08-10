<div align="center">

# 🔗 LinkForge

**Acortador de URLs open source con slugs y destinos 100% editables**

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=flat&logo=postgresql&logoColor=white)](https://postgresql.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[🚀 Demo](#demo) • [📖 Docs](#documentación) • [🛠️ Setup](#instalación) • [📡 API](#api-endpoints)

</div>

---

## ✨ ¿Por qué LinkForge?

La mayoría de acortadores **no te dejan editar** el slug ni la URL destino. Si WhatsApp, Telegram o SMS bloquea tu link por ciertas palabras en el slug, estás atascado.

**LinkForge resuelve esto:**

- ✅ **Slug editable** — Renombra tu link cuando quieras sin perder analytics
- ✅ **Destino editable** — Cambia la URL de destino sin cambiar el slug
- ✅ **Auto-expiración** — Los links expiran en 6 días por defecto (limpieza automática)
- ✅ **Sin login** — Cada usuario ve solo sus links mediante `localStorage` (privacidad total)
- ✅ **Historial de cambios** — Auditoría completa de renombrados y cambios de destino
- ✅ **Analytics preservados** — Los clicks se guardan por ID interno, no por slug
- ✅ **Open Source** — Código limpio, bien documentado, listo para tu portafolio
- ✅ **Async** — FastAPI + SQLAlchemy 2.0 + asyncpg para máximo rendimiento

---

## 🏗️ Arquitectura Desacoplada

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   FastAPI    │────▶│   PostgreSQL    │
│  React + Vite   │     │   (async)    │     │   (Datos)       │
└─────────────────┘     └──────────────┘     └─────────────────┘
      localStorage              │
      (mis links)               ▼
                         ┌──────────────┐
                         │    Redis     │
                         │   (Cache)    │
                         └──────────────┘
```

**Modelo desacoplado:**
- `Destination` → URL real (editable independientemente)
- `Slug` → Nombre corto editable (el code cambia, el ID preserva analytics)
- `Click` → Analytics (inmutable, apunta a Slug por UUID)
- `SlugHistory` → Auditoría de renombrados
- `DestinationHistory` → Auditoría de cambios de destino

---

## 🚀 Demo

### Crear un acortado
```bash
curl -X POST "http://localhost:8000/api/v1/urls/shorten" \
  -H "Content-Type: application/json" \
  -d '{
    "target_url": "https://mi-tienda.com/producto-123",
    "custom_slug": "promo-verano"
  }'
```

**Response:**
```json
{
  "short_url": "http://localhost:8000/promo-verano",
  "slug": "promo-verano",
  "target_url": "https://mi-tienda.com/producto-123",
  "edit_token": "aB3xK9mP...",
  "redirect_type": "307",
  "created_at": "2026-08-07T19:00:00",
  "expires_at": "2026-08-13T19:00:00",
  "is_active": true
}
```

> **Importante:** Guarda el `edit_token`. Es la única forma de editar o eliminar el link después.

### Editar el slug (renombrar)
```bash
curl -X PATCH "http://localhost:8000/api/v1/urls/promo-verano/slug" \
  -H "Content-Type: application/json" \
  -d '{
    "new_slug": "oferta-2026",
    "edit_token": "aB3xK9mP..."
  }'
```

### Editar la URL destino
```bash
curl -X PATCH "http://localhost:8000/api/v1/urls/oferta-2026/destination" \
  -H "Content-Type: application/json" \
  -d '{
    "new_target_url": "https://mi-tienda.com/oferta-nueva",
    "edit_token": "aB3xK9mP..."
  }'
```

### Ver historial de cambios
```bash
curl http://localhost:8000/api/v1/urls/oferta-2026/history
```

### Consultar mis links (batch)
```bash
curl -X POST "http://localhost:8000/api/v1/urls/batch-info" \
  -H "Content-Type: application/json" \
  -d '{
    "slugs": ["oferta-2026", "otro-link"]
  }'
```

---

## 🛠️ Instalación

### Backend (FastAPI + PostgreSQL)

```bash
# 1. Clonar y entrar al backend
cd url-shortener

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar DB local
cp .env.example .env
# Editar DATABASE_URL apuntando a tu PostgreSQL local

# 5. Crear tablas (usando el schema SQL)
psql -U postgres -d cortlink_db -f linkforge_schema.sql

# 6. Correr
uvicorn app.main:app --reload
```

### Frontend (React + Vite + Tailwind)

```bash
cd linkforge-frontend
npm install
npm run dev
```

---

## 📡 API Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/v1/urls/shorten` | Crear acortado (expira en 6 días por defecto) |
| `GET` | `/api/v1/urls/` | Listar todos los acortados activos |
| `POST` | `/api/v1/urls/batch-info` | Info de múltiples slugs (para localStorage) |
| `GET` | `/{slug}` | Redirigir al destino (registra analytics) |
| `GET` | `/api/v1/urls/{slug}/info` | Info del acortado |
| `GET` | `/api/v1/urls/{slug}/history` | **Historial** de renombrados y cambios de destino |
| `PATCH` | `/api/v1/urls/{slug}/slug` | **Renombrar slug** |
| `PATCH` | `/api/v1/urls/{slug}/destination` | **Cambiar destino** |
| `DELETE` | `/api/v1/urls/{slug}` | Desactivar (soft-delete) |
| `GET` | `/api/v1/analytics/{slug}` | Estadísticas de clicks |

📚 **Documentación interactiva:** `http://localhost:8000/docs` (Swagger UI)

---

## 🔐 Privacidad sin Login

LinkForge **no requiere autenticación**. Cada usuario ve solo sus links gracias a:

- **`localStorage`**: El frontend guarda `slug + edit_token` en el navegador
- **Batch info**: El frontend consulta solo sus slugs al backend
- **Auto-expiración**: Links muertos se limpian automáticamente después de 6 días

> ⚠️ **Guarda tu `edit_token`**. Sin él no podrás editar ni eliminar el link.

---

## 🧪 Testing

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Coverage
pytest --cov=app --cov-report=html
```

---

## 📁 Estructura del Proyecto

```
linkforge/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Routers (endpoints)
│   │   ├── core/            # Seguridad, generadores
│   │   ├── db/              # Conexión SQLAlchemy
│   │   ├── models/          # Modelos desacoplados
│   │   ├── schemas/         # Pydantic (validación)
│   │   ├── services/        # Lógica de negocio
│   │   ├── utils/           # Validadores
│   │   ├── config.py        # Settings
│   │   ├── dependencies.py  # Inyección de dependencias
│   │   └── main.py          # Punto de entrada
│   ├── tests/
│   ├── linkforge_schema.sql # Schema PostgreSQL
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── api/             # Cliente Axios + endpoints
│   │   ├── components/      # UI components
│   │   ├── pages/           # Vistas
│   │   ├── hooks/           # Lógica React
│   │   ├── types/           # TypeScript interfaces
│   │   └── utils/           # Helpers
│   ├── package.json
│   └── vite.config.ts
│
└── README.md
```

---

## 🎯 Casos de Uso

1. **Marketing:** Cambia el slug si una plataforma bloquea ciertas palabras
2. **Campañas:** Actualiza la landing page sin regenerar el QR/link
3. **A/B Testing:** Múltiples slugs apuntando al mismo destino
4. **Portafolio:** Muestra arquitectura limpia, async, Docker, testing

---

## 🤝 Contribuir

1. Fork el repo
2. Crea una rama: `git checkout -b feature/nueva-funcion`
3. Commitea: `git commit -m 'Agrega nueva función'`
4. Push: `git push origin feature/nueva-funcion`
5. Abre un Pull Request

---

## 📄 Licencia

MIT License — Libre para usar, modificar y distribuir.

---

<div align="center">

**Hecho con ❤️ usando FastAPI + PostgreSQL + React**

⭐ Si te sirve para tu portafolio, dale una estrella

</div>
