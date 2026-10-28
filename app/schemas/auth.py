"""
Esquemas Pydantic para autenticación (registro, login y sesión).
"""
import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserRegister(BaseModel):
    """Datos para registrar una cuenta nueva."""
    email: str = Field(..., max_length=255, description="Correo electrónico único")
    password: str = Field(
        ...,
        min_length=6,
        max_length=128,
        description="Contraseña (mínimo 6 caracteres)",
    )
    username: Optional[str] = Field(
        None,
        min_length=2,
        max_length=64,
        description="Nombre de usuario opcional",
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if not EMAIL_REGEX.match(cleaned):
            raise ValueError("Formato de correo electrónico inválido")
        return cleaned

    @field_validator("username")
    @classmethod
    def clean_username(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = v.strip()
        return cleaned or None


class UserLogin(BaseModel):
    """Credenciales para iniciar sesión."""
    email: str = Field(..., description="Correo electrónico")
    password: str = Field(..., description="Contraseña")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class UserResponse(BaseModel):
    """Datos públicos de la cuenta de usuario."""
    id: UUID
    email: str
    username: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Respuesta de autenticación con JWT y perfil del usuario."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
