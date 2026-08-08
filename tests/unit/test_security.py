
"""
Tests unitarios para utilidades de seguridad.
"""
import pytest
from app.core.security import generate_edit_token, generate_slug_code, hash_ip


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
