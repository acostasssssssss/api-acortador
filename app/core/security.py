"""
Utilidades de seguridad: generación de tokens, hashing de contraseñas, JWT y hashing de IPs.
"""
import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.config import get_settings

settings = get_settings()

PBKDF2_ITERATIONS = 390_000


def generate_edit_token(length: int = None) -> str:
    """Genera un token seguro para edición de slugs."""
    length = length or settings.EDIT_TOKEN_LENGTH
    return secrets.token_urlsafe(length)


def hash_ip(ip: str) -> str:
    """Hashea una IP para analytics anónimos."""
    return hashlib.sha256(f"{ip}{settings.SECRET_KEY}".encode()).hexdigest()[:16]


def generate_slug_code(length: int = None) -> str:
    """Genera un slug aleatorio usando nanoid-like approach."""
    length = length or settings.DEFAULT_SLUG_LENGTH
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def hash_password(password: str) -> str:
    """Hashea una contraseña usando PBKDF2-HMAC-SHA256 con salt aleatorio."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${dk.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña en texto plano contra su hash PBKDF2."""
    try:
        algorithm, iterations_str, salt, stored_hash = hashed_password.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_str)
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )
        return hmac.compare_digest(dk.hex(), stored_hash)
    except (ValueError, TypeError):
        return False


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(
    subject: str,
    extra_claims: Optional[dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Crea un token JWT firmado con HMAC-SHA256 (HS256)."""
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    header = {"alg": settings.JWT_ALGORITHM, "typ": "JWT"}
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    return f"{header_b64}.{payload_b64}.{_b64url_encode(signature)}"


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """Valida firma y expiración de un token JWT HS256. Retorna el payload o None."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, signature_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()
        actual_sig = _b64url_decode(signature_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        exp = payload.get("exp")
        if exp is None or int(exp) < int(datetime.now(timezone.utc).timestamp()):
            return None
        return payload
    except Exception:
        return None
