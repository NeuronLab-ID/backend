"""
Tests for manim animation routes: generate, status, video.
"""

from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException


def test_generate_requires_auth(client):
    """POST /api/manim/generate returns 403 without auth (HTTPBearer)."""
    response = client.post("/api/manim/generate", json={"problem_id": 1})
    assert response.status_code in {401, 403}


def test_status_requires_auth(client):
    """GET /api/manim/status/1 returns 403 without auth (HTTPBearer)."""
    response = client.get("/api/manim/status/1")
    assert response.status_code in {401, 403}


def test_video_requires_auth(client):
    """GET /api/manim/video/1/1 returns 403 without auth (HTTPBearer)."""
    response = client.get("/api/manim/video/1/1")
    assert response.status_code in {401, 403}


def test_generate_success(client, auth_headers):
    """POST /api/manim/generate returns animation data."""
    from app.dependencies import get_manim_controller
    from main import app

    mock_controller = MagicMock()
    mock_controller.generate_animation = AsyncMock(
        return_value={
            "id": 1,
            "problem_id": 1,
            "step_number": 1,
            "status": "completed",
        }
    )

    app.dependency_overrides[get_manim_controller] = lambda: mock_controller
    try:
        response = client.post(
            "/api/manim/generate",
            json={"problem_id": 1, "step_number": 1},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["problem_id"] == 1
        mock_controller.generate_animation.assert_awaited_once_with(
            1, 1, mock_controller.generate_animation.await_args[0][2], None
        )
    finally:
        del app.dependency_overrides[get_manim_controller]


def test_generate_no_step_number(client, auth_headers):
    """POST /api/manim/generate with no step_number generates all steps."""
    from app.dependencies import get_manim_controller
    from main import app

    mock_controller = MagicMock()
    mock_controller.generate_animation = AsyncMock(
        return_value={
            "problem_id": 1,
            "animations": [
                {"step_number": 1, "status": "completed"},
                {"step_number": 2, "status": "completed"},
            ],
        }
    )

    app.dependency_overrides[get_manim_controller] = lambda: mock_controller
    try:
        response = client.post(
            "/api/manim/generate",
            json={"problem_id": 1},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["problem_id"] == 1
        assert len(data["animations"]) == 2
    finally:
        del app.dependency_overrides[get_manim_controller]


def test_status_success(client, auth_headers):
    """GET /api/manim/status/{id} returns status data."""
    from app.dependencies import get_manim_controller
    from main import app

    mock_controller = MagicMock()
    mock_controller.get_animation_status.return_value = {
        "problem_id": 1,
        "total_steps": 3,
        "completed_count": 1,
        "rendering_count": 1,
        "error_count": 0,
        "pending_count": 1,
    }

    app.dependency_overrides[get_manim_controller] = lambda: mock_controller
    try:
        response = client.get("/api/manim/status/1", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_steps"] == 3
        assert data["completed_count"] == 1
        assert data["pending_count"] == 1
        mock_controller.get_animation_status.assert_called_once_with(1)
    finally:
        del app.dependency_overrides[get_manim_controller]


def test_video_success(client, auth_headers, tmp_path):
    """GET /api/manim/video/{problem_id}/{step} returns video file."""
    from app.dependencies import get_manim_controller
    from main import app

    # Create a temp file to serve
    video_file = tmp_path / "step_1.mp4"
    video_file.write_bytes(b"\x00\x00\x00\x1cftypisom")  # Minimal MP4 header bytes

    mock_controller = MagicMock()
    mock_controller.get_video_path.return_value = video_file

    app.dependency_overrides[get_manim_controller] = lambda: mock_controller
    try:
        response = client.get("/api/manim/video/1/1", headers=auth_headers)
        assert response.status_code == 200
        assert response.headers["content-type"] == "video/mp4"
        mock_controller.get_video_path.assert_called_once_with(1, 1, "calculation")
    finally:
        del app.dependency_overrides[get_manim_controller]


def test_video_not_found(client, auth_headers):
    """GET /api/manim/video/1/1 returns 404 when animation not found."""
    from app.dependencies import get_manim_controller
    from main import app

    mock_controller = MagicMock()
    mock_controller.get_video_path.side_effect = HTTPException(404, "Animation not found")

    app.dependency_overrides[get_manim_controller] = lambda: mock_controller
    try:
        response = client.get("/api/manim/video/1/1", headers=auth_headers)
        assert response.status_code == 404
    finally:
        del app.dependency_overrides[get_manim_controller]


def test_generate_reasoning_not_found(client, auth_headers):
    """POST /api/manim/generate returns 404 when no reasoning exists."""
    from app.dependencies import get_manim_controller
    from main import app

    mock_controller = MagicMock()
    mock_controller.generate_animation = AsyncMock(
        side_effect=HTTPException(404, "No reasoning available for this problem. Generate reasoning first.")
    )

    app.dependency_overrides[get_manim_controller] = lambda: mock_controller
    try:
        response = client.post(
            "/api/manim/generate",
            json={"problem_id": 999, "step_number": 1},
            headers=auth_headers,
        )
        assert response.status_code == 404
    finally:
        del app.dependency_overrides[get_manim_controller]


def test_generate_with_video_type(client, auth_headers):
    """POST /api/manim/generate with video_type passes it to the controller."""
    from app.dependencies import get_manim_controller
    from main import app

    mock_controller = MagicMock()
    mock_controller.generate_animation = AsyncMock(
        return_value={
            "problem_id": 1,
            "step_number": 1,
            "status": "completed",
            "video_type": "visualization",
        }
    )

    app.dependency_overrides[get_manim_controller] = lambda: mock_controller
    try:
        response = client.post(
            "/api/manim/generate",
            json={"problem_id": 1, "step_number": 1, "video_type": "visualization"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["video_type"] == "visualization"
        # The controller should receive video_type as the 4th argument
        call_args = mock_controller.generate_animation.await_args
        assert call_args[0][0] == 1  # problem_id
        assert call_args[0][1] == 1  # step_number
        assert call_args[0][3] == "visualization"  # video_type
    finally:
        del app.dependency_overrides[get_manim_controller]


def test_video_with_type_query_param(client, auth_headers, tmp_path):
    """GET /api/manim/video/1/1?type=visualization passes video_type to controller."""
    from app.dependencies import get_manim_controller
    from main import app

    video_file = tmp_path / "step_1_visualization.mp4"
    video_file.write_bytes(b"\x00\x00\x00\x1cftypisom")

    mock_controller = MagicMock()
    mock_controller.get_video_path.return_value = video_file

    app.dependency_overrides[get_manim_controller] = lambda: mock_controller
    try:
        response = client.get("/api/manim/video/1/1?type=visualization", headers=auth_headers)
        assert response.status_code == 200
        mock_controller.get_video_path.assert_called_once_with(1, 1, "visualization")
    finally:
        del app.dependency_overrides[get_manim_controller]
