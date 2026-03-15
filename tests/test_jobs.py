"""Tests for job endpoints."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_create_job(client):
    """Test creating a generation job."""
    with patch("lofty.worker.celery_app.celery_app") as mock_celery:
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_celery.send_task.return_value = mock_task

        # Also patch the rate_limit dependency to bypass Redis
        from lofty.dependencies import rate_limit
        from lofty.auth.clerk import get_current_user
        from lofty.main import app

        app.dependency_overrides[rate_limit] = app.dependency_overrides[get_current_user]

        response = await client.post(
            "/api/v1/jobs",
            json={
                "prompt": "upbeat electronic dance music",
                "duration_seconds": 10.0,
                "model_name": "musicgen-small",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["prompt"] == "upbeat electronic dance music"
        assert data["status"] in ("pending", "queued")
        assert "id" in data


@pytest.mark.asyncio
async def test_create_job_validation_error(client):
    """Test that short prompts are rejected."""
    from lofty.dependencies import rate_limit
    from lofty.auth.clerk import get_current_user
    from lofty.main import app

    app.dependency_overrides[rate_limit] = app.dependency_overrides[get_current_user]

    response = await client.post(
        "/api/v1/jobs",
        json={"prompt": "ab", "duration_seconds": 10.0},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_jobs(client):
    """Test listing jobs."""
    response = await client.get("/api/v1/jobs")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data


@pytest.mark.asyncio
async def test_get_nonexistent_job(client):
    """Test getting a job that doesn't exist."""
    response = await client.get("/api/v1/jobs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
