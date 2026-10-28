"""
Configuración de base de datos async con SQLAlchemy 2.0.
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.config import get_settings

settings = get_settings()

# Engine async configurado para reconexión bajo demanda (ideal para serverless y local)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Base declarativa
Base = declarative_base()


async def get_db() -> AsyncSession: # type: ignore
    """Dependency para inyección de sesiones de DB."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Crea las tablas si no existen (solo para desarrollo)."""
    import app.models  # noqa: F401 - registra todos los modelos en Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                "ALTER TABLE slugs "
                "ADD COLUMN IF NOT EXISTS user_id UUID "
                "REFERENCES users(id) ON DELETE CASCADE"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_slugs_user_active "
                "ON slugs (user_id, is_active)"
            )
        )
