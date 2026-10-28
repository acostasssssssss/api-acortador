
"""
Tests unitarios para utilidades de seguridad, JWT, esquemas y autorización multi-tenant.
"""
import uuid
from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_edit_token,
    generate_slug_code,
    hash_ip,
    hash_password,
    verify_password,
)
from app.models.url import Slug
from app.models.user import User
from app.schemas.auth import UserRegister
from app.schemas.url import URLCreate
from app.services.url_service import URLService


def test_generate_edit_token_length():
    token = generate_edit_token(32)
    assert len(token) > 30  # base64urlsafe genera más chars


def test_generate_edit_token_uniqueness():
    t1 = generate_edit_token()
    t2 = generate_edit_token()
    assert t1 != t2


def test_generate_slug_code_length():
    slug = generate_slug_code(6)
    assert len(slug) == 6


def test_generate_slug_code_format():
    slug = generate_slug_code(8)
    assert slug.isalnum()


def test_hash_ip_consistency():
    h1 = hash_ip("192.168.1.1")
    h2 = hash_ip("192.168.1.1")
    assert h1 == h2


def test_hash_ip_anonymity():
    h = hash_ip("192.168.1.1")
    assert "192.168" not in h


def test_password_hash_and_verify():
    hashed = hash_password("MiClaveSegura123")
    assert hashed != "MiClaveSegura123"
    assert verify_password("MiClaveSegura123", hashed) is True
    assert verify_password("ClaveIncorrecta", hashed) is False


def test_jwt_create_and_decode():
    user_id = str(uuid.uuid4())
    token = create_access_token(subject=user_id, extra_claims={"email": "dev@example.com"})
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["email"] == "dev@example.com"


def test_jwt_expired_or_tampered():
    expired_token = create_access_token(
        subject="user-1",
        expires_delta=timedelta(seconds=-10),
    )
    assert decode_access_token(expired_token) is None

    valid_token = create_access_token(subject="user-1")
    tampered = valid_token[:-4] + "xxxx"
    assert decode_access_token(tampered) is None


def test_url_create_normalizes_custom_slug():
    schema = URLCreate(target_url="https://example.com", custom_slug="Mi-Slug_2026")
    assert schema.custom_slug == "mi-slug_2026"


def test_user_register_normalizes_email():
    reg = UserRegister(email="  Usuario@Example.COM ", password="password123", username=" carlos ")
    assert reg.email == "usuario@example.com"
    assert reg.username == "carlos"


def test_multi_tenant_authorization():
    owner = User(id=uuid.uuid4(), email="owner@example.com", password_hash="x")
    intruder = User(id=uuid.uuid4(), email="intruder@example.com", password_hash="x")
    slug = Slug(
        id=uuid.uuid4(),
        code="mi-link",
        destination_id=uuid.uuid4(),
        user_id=owner.id,
        edit_token="secret-edit-token",
    )

    # El propietario autenticado puede modificar sin enviar edit_token
    URLService._authorize_slug_mutation(slug, current_user=owner, edit_token=None)

    # Otra cuenta autenticada recibe 403 incluso si intenta usar el endpoint
    with pytest.raises(HTTPException) as exc:
        URLService._authorize_slug_mutation(slug, current_user=intruder, edit_token="secret-edit-token")
    assert exc.value.status_code == 403
