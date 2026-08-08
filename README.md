<div align="center">

# 🔗 LinkForge

**Acortador de URLs open source con slugs y destinos 100% editables**

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=flat&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[🚀 Demo](#demo) • [📖 Docs](#documentación) • [🛠️ Setup](#instalación) • [📡 API](#api-endpoints)

</div>

---

## ✨ ¿Por qué LinkForge?

La mayoría de acortadores **no te dejan editar** el slug ni la URL destino. Si una mensajería (WhatsApp, Telegram, SMS) bloquea tu link por ciertas palabras en el slug, estás atascado.

**LinkForge resuelve esto:**

- ✅ **Slug editable** — Renombra tu link cuando quieras sin perder analytics
- ✅ **Destino editable** — Cambia la URL de destino sin cambiar el slug
- ✅ **Analytics preservados** — Los clicks se guardan por ID interno, no por slug
- ✅ **Open Source** — Código limpio, bien documentado, listo para tu portafolio
- ✅ **Async** — FastAPI + SQLAlchemy 2.0 + asyncpg para máximo rendimiento
- ✅ **Dockerizado** — `docker-compose up` y listo

---

## 🏗️ Arquitectura

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Cliente       │────▶│  FastAPI     │────▶│  PostgreSQL     │
│  (Web/Mobile)   │     │   (async)    │     │   (Datos)       │
└─────────────────┘     └──────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │    Redis     │
                        │   (Cache)    │
                        └──────────────┘
```

**Modelo desacoplado:**
- `Destination` → URL real (editable)
- `Slug` → Nombre corto (editable)
- `Click` → Analytics (inmutable, apunta a Slug por UUID)
- `History` → Auditoría de cambios

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
  "is_active": true
}
```

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

---

## 🛠️ Instalación

### Docker (Recomendado)

```bash
# Clonar repo
git clone https://github.com/tuusuario/linkforge.git
cd linkforge

# Copiar variables de entorno
cp .env.example .env

# Levantar servicios
docker-compose up -d

# Crear migraciones (primera vez)
docker-compose exec app alembic revision --autogenerate -m "init"
docker-compose exec app alembic upgrade head

# Listo en http://localhost:8000
```

### Local (Desarrollo)

```bash
# Requisitos: Python 3.12, PostgreSQL 16, Redis

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

# Configurar .env
cp .env.example .env
# Editar DATABASE_URL, REDIS_URL, etc.

# Crear DB y migraciones
alembic upgrade head

# Correr
uvicorn app.main:app --reload
```

---

## 📡 API Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/v1/urls/shorten` | Crear acortado |
| `GET` | `/{slug}` | Redirigir al destino |
| `GET` | `/api/v1/urls/{slug}/info` | Info del acortado |
| `PATCH` | `/api/v1/urls/{slug}/slug` | **Renombrar slug** |
| `PATCH` | `/api/v1/urls/{slug}/destination` | **Cambiar destino** |
| `DELETE` | `/api/v1/urls/{slug}` | Desactivar (soft-delete) |
| `GET` | `/api/v1/analytics/{slug}` | Estadísticas |

📚 **Documentación interactiva:** `http://localhost:8000/docs` (Swagger UI)

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
url-shortener/
├── app/
│   ├── api/v1/          # Routers (endpoints)
│   ├── core/            # Seguridad, generadores
│   ├── db/              # Conexión SQLAlchemy
│   ├── models/          # Modelos desacoplados
│   ├── schemas/         # Pydantic (validación)
│   ├── services/        # Lógica de negocio
│   ├── utils/           # Validadores
│   ├── config.py        # Settings
│   ├── dependencies.py  # Inyección de dependencias
│   └── main.py          # Punto de entrada
├── tests/
│   ├── unit/            # Tests unitarios
│   └── integration/     # Tests de API
├── alembic/             # Migraciones
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
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

**Hecho con ❤️ usando FastAPI + PostgreSQL + Redis**

⭐ Si te sirve para tu portafolio, dale una estrella

</div>
