"""
Endpoints de autenticación: registro, inicio de sesión y perfil actual.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db_session
from app.models.user import User
from app.schemas.auth import TokenResponse, UserLogin, UserRegister, UserResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    data: UserRegister,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Registra una nueva cuenta de usuario y devuelve un token JWT listo para usar.
    """
    return await AuthService.register(db, data)


@router.post("/login", response_model=TokenResponse)
async def login_user(
    data: UserLogin,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Inicia sesión con email y contraseña y devuelve un token JWT Bearer.
    """
    return await AuthService.login(db, data)


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    """
    Retorna la información de la cuenta actualmente autenticada.
    """
    return current_user
