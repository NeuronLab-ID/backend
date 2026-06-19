from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import HTTPException


def _job(job_id="job123", status="queued"):
    return SimpleNamespace(
        job_id=job_id,
        problem_id=1,
        step_number=2,
        video_type="calculation",
        requested_backend="cpu",
        resolved_backend=None,
        status=status,
        progress=0,
        attempt=1,
        max_attempts=2,
        provider="openai-compatible",
        model="cx/gpt-5.5-xhigh",
        animation_id=None,
        error_code=None,
        error_message=None,
        logs_tail=None,
        created_at=None,
        queued_at=None,
        started_at=None,
        finished_at=None,
        cancel_requested_at=None,
    )


def test_backends_requires_auth(client):
    response = client.get("/api/manim/backends")
    assert response.status_code in {401, 403}


def test_job_routes_require_auth(client):
    assert client.post("/api/manim/jobs", json={"problem_id": 1}).status_code in {401, 403}
    assert client.get("/api/manim/jobs/job123").status_code in {401, 403}
    assert client.post("/api/manim/jobs/job123/cancel").status_code in {401, 403}
    assert client.post("/api/manim/jobs/job123/retry").status_code in {401, 403}


def test_backends_lists_cpu_and_egpu(client, auth_headers):
    from app.dependencies import get_manim_queue_service
    from main import app

    queue = MagicMock()
    queue.list_backends.return_value = {
        "default_backend": "cpu",
        "backends": [
            {"name": "cpu", "available": True, "default": True, "reason": None},
            {
                "name": "egpu",
                "available": False,
                "default": False,
                "reason": "eGPU backend is disabled by policy",
            },
        ],
    }
    app.dependency_overrides[get_manim_queue_service] = lambda: queue
    try:
        response = client.get("/api/manim/backends", headers=auth_headers)
    finally:
        del app.dependency_overrides[get_manim_queue_service]

    assert response.status_code == 200
    data = response.json()
    assert data["default_backend"] == "cpu"
    assert [backend["name"] for backend in data["backends"]] == ["cpu", "egpu"]
    egpu = data["backends"][1]
    assert egpu["available"] is False
    assert egpu["reason"] == "eGPU backend is disabled by policy"


def test_create_job_returns_accepted_contract(client, auth_headers):
    from app.dependencies import get_manim_queue_service
    from main import app

    queue = MagicMock()
    queue.create_job.return_value = _job()
    app.dependency_overrides[get_manim_queue_service] = lambda: queue
    try:
        response = client.post(
            "/api/manim/jobs",
            json={"problem_id": 1, "step_number": 2, "video_type": "calculation", "backend": "cpu"},
            headers=auth_headers,
        )
    finally:
        del app.dependency_overrides[get_manim_queue_service]

    assert response.status_code == 202
    assert response.headers["location"] == "/api/manim/jobs/job123"
    data = response.json()
    assert data == {
        "job_id": "job123",
        "status": "queued",
        "status_url": "/api/manim/jobs/job123",
        "events_url": "/api/manim/jobs/job123/events",
    }
    queue.create_job.assert_called_once()
    assert queue.create_job.call_args.kwargs["backend"] == "cpu"


def test_get_cancel_and_retry_job_contracts(client, auth_headers):
    from app.dependencies import get_manim_queue_service
    from main import app

    queue = MagicMock()
    queue.get_job.return_value = _job(status="rendering")
    queue.cancel_job.return_value = _job(status="cancelling")
    queue.retry_job.return_value = _job(job_id="retry123", status="queued")
    app.dependency_overrides[get_manim_queue_service] = lambda: queue
    try:
        status_response = client.get("/api/manim/jobs/job123", headers=auth_headers)
        cancel_response = client.post("/api/manim/jobs/job123/cancel", headers=auth_headers)
        retry_response = client.post("/api/manim/jobs/job123/retry", headers=auth_headers)
    finally:
        del app.dependency_overrides[get_manim_queue_service]

    assert status_response.status_code == 200
    assert status_response.json()["status"] == "rendering"
    assert status_response.json()["provider"] == "openai-compatible"
    assert cancel_response.status_code == 200
    assert cancel_response.json() == {"job_id": "job123", "status": "cancelling"}
    assert retry_response.status_code == 202
    assert retry_response.json()["job_id"] == "retry123"


def test_retry_job_route_returns_404_for_missing_job(client, auth_headers):
    from app.dependencies import get_manim_queue_service
    from main import app

    queue = MagicMock()
    queue.retry_job.side_effect = HTTPException(404, "Manim job not found")
    app.dependency_overrides[get_manim_queue_service] = lambda: queue
    try:
        response = client.post("/api/manim/jobs/missing/retry", headers=auth_headers)
    finally:
        del app.dependency_overrides[get_manim_queue_service]

    assert response.status_code == 404
    assert response.json()["detail"] == "Manim job not found"


def test_retry_job_route_returns_400_for_nonretryable_job(client, auth_headers):
    from app.dependencies import get_manim_queue_service
    from main import app

    queue = MagicMock()
    queue.retry_job.side_effect = HTTPException(400, "Manim job is not retryable")
    app.dependency_overrides[get_manim_queue_service] = lambda: queue
    try:
        response = client.post("/api/manim/jobs/exhausted/retry", headers=auth_headers)
    finally:
        del app.dependency_overrides[get_manim_queue_service]

    assert response.status_code == 400
    assert response.json()["detail"] == "Manim job is not retryable"
