"""
Servicio de autenticación y gestión de usuarios.
"""
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import UserLogin, UserRegister


class AuthService:
    """Casos de uso de registro, login y consulta de usuario."""

    @staticmethod
    async def register(db: AsyncSession, data: UserRegister) -> dict:
        """Registra un nuevo usuario y retorna su token JWT de acceso."""
        existing = await db.execute(select(User).where(User.email == data.email))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El correo electrónico ya está registrado.",
            )

        user = User(
            email=data.email,
            username=data.username or data.email.split("@")[0],
            password_hash=hash_password(data.password),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        access_token = create_access_token(
            subject=str(user.id),
            extra_claims={"email": user.email},
        )
        logger.info("[Auth] Nuevo usuario registrado: %s", user.email)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user,
        }

    @staticmethod
    async def login(db: AsyncSession, data: UserLogin) -> dict:
        """Autentica un usuario con email y contraseña y emite un JWT."""
        result = await db.execute(select(User).where(User.email == data.email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas.",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La cuenta de usuario está desactivada.",
            )

        access_token = create_access_token(
            subject=str(user.id),
            extra_claims={"email": user.email},
        )
        logger.info("[Auth] Inicio de sesión exitoso: %s", user.email)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user,
        }

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: str | UUID) -> Optional[User]:
        """Obtiene un usuario activo por su ID."""
        try:
            parsed_id = UUID(str(user_id))
        except (ValueError, TypeError):
            return None

        result = await db.execute(
            select(User).where(User.id == parsed_id, User.is_active == True)
        )
        return result.scalar_one_or_none()
