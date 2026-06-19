"""
Tests for rate limiting on sandbox execution endpoints.
Uses TestClient with mocked execute_code — no Docker daemon required.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.database import get_db

MOCK_EXECUTE_RESULT = {
    "success": True,
    "results": [],
    "error": None,
    "hint": None,
    "execution_time": 0.1,
}


@pytest.fixture
def client(db_session):
    """TestClient with Docker mocked out so lifespan doesn't need a running daemon."""
    from main import app

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with patch("docker.DockerClient.from_env") as mock_docker:
        mock_docker_client = MagicMock()
        mock_docker_client.containers.list.return_value = []
        mock_docker.return_value = mock_docker_client
        with TestClient(app) as test_client:
            yield test_client

    app.dependency_overrides.clear()


def test_rate_limit_normal_request_200(client, test_user, auth_headers, sample_problem):
    """Single request below rate limit returns 200."""
    with patch(
        "app.routes.execution.execute_code",
        new_callable=AsyncMock,
        return_value=MOCK_EXECUTE_RESULT,
    ):
        response = client.post(
            "/api/execute",
            json={"problem_id": 1, "code": "def solution(): return 42"},
            headers=auth_headers,
        )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_rate_limit_rapid_requests_429(client, test_user, auth_headers, sample_problem):
    """Rapid requests exceeding the 10/minute rate limit produce at least one 429."""
    status_codes = []
    with patch(
        "app.routes.execution.execute_code",
        new_callable=AsyncMock,
        return_value=MOCK_EXECUTE_RESULT,
    ):
        for _ in range(15):
            resp = client.post(
                "/api/execute",
                json={"problem_id": 1, "code": "x = 1"},
                headers=auth_headers,
            )
            status_codes.append(resp.status_code)
    assert 429 in status_codes, f"Expected 429 in {set(status_codes)}"
    assert status_codes[0] == 200


def test_rate_limit_both_endpoints(client, test_user, auth_headers, sample_problem):
    """Rate limit applies to /api/quest/execute as well (not just /api/execute)."""
    quest_statuses = []
    # Quest endpoint: controller raises 404 (no quest exists for problem),
    # but the rate limiter has already counted each request.
    for _ in range(15):
        resp = client.post(
            "/api/quest/execute",
            json={"problem_id": 1, "step": 1, "code": "x = 1"},
            headers=auth_headers,
        )
        quest_statuses.append(resp.status_code)
    assert 429 in quest_statuses, f"Quest endpoint: expected 429 in {set(quest_statuses)}"
