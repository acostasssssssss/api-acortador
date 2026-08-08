
"""
Tests de integración para los endpoints de la API.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_create_short_url(client):
    response = await client.post("/api/v1/urls/shorten", json={
        "target_url": "https://example.com",
        "custom_slug": "test-slug-123"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "test-slug-123"
    assert "edit_token" in data
    assert data["target_url"] == "https://example.com"


@pytest.mark.asyncio
async def test_create_duplicate_slug(client):
    # Crear primero
    await client.post("/api/v1/urls/shorten", json={
        "target_url": "https://example.com",
        "custom_slug": "dup-test"
    })
    # Intentar duplicar
    response = await client.post("/api/v1/urls/shorten", json={
        "target_url": "https://otra.com",
        "custom_slug": "dup-test"
    })
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_edit_slug(client):
    # Crear
    create_resp = await client.post("/api/v1/urls/shorten", json={
        "target_url": "https://example.com",
        "custom_slug": "old-name"
    })
    edit_token = create_resp.json()["edit_token"]

    # Editar slug
    response = await client.patch("/api/v1/urls/old-name/slug", json={
        "new_slug": "new-name",
        "edit_token": edit_token
    })
    assert response.status_code == 200
    assert response.json()["new_slug"] == "new-name"


@pytest.mark.asyncio
async def test_edit_destination(client):
    # Crear
    create_resp = await client.post("/api/v1/urls/shorten", json={
        "target_url": "https://old-target.com",
        "custom_slug": "edit-dest-test"
    })
    edit_token = create_resp.json()["edit_token"]

    # Editar destino
    response = await client.patch("/api/v1/urls/edit-dest-test/destination", json={
        "new_target_url": "https://new-target.com",
        "edit_token": edit_token
    })
    assert response.status_code == 200
    assert response.json()["new_target"] == "https://new-target.com"
