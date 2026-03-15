"""Tests for track endpoints."""

import pytest


@pytest.mark.asyncio
async def test_list_tracks(client):
    """Test listing tracks."""
    response = await client.get("/api/v1/tracks")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_get_nonexistent_track(client):
    """Test getting a track that doesn't exist."""
    response = await client.get("/api/v1/tracks/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
