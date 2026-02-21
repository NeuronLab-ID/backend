"""
Tests for ManimExecutor with fully mocked Docker client.
"""

import asyncio
import io
import tarfile

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from docker.errors import DockerException

from app.services.manim_executor import ManimExecutor


def _build_tar_bytes(filename: str, data: bytes) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        info = tarfile.TarInfo(name=filename)
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_render_success_writes_mp4(tmp_path):
    executor = ManimExecutor()
    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_socket = MagicMock()
    mock_socket._sock = MagicMock()

    mock_client.containers.create.return_value = mock_container
    mock_container.attach_socket.return_value = mock_socket
    mock_container.wait.return_value = {"StatusCode": 0}
    mock_container.logs.return_value = b'{"status":"success","video_path":"/tmp/render/output.mp4"}'
    tar_bytes = _build_tar_bytes("output.mp4", b"mp4-data")
    mock_container.get_archive.return_value = ([tar_bytes], {})

    with patch("app.services.manim_executor.docker.from_env", return_value=mock_client):
        with patch("app.services.manim_executor.MANIM_OUTPUT_DIR", tmp_path):
            result = await executor.render("print('hi')", problem_id=1, step_number=2)

    expected_path = tmp_path / "1" / "step_2_calculation.mp4"
    assert result["status"] == "success"
    assert result["video_path"] == str(expected_path)
    assert expected_path.read_bytes() == b"mp4-data"
    mock_container.remove.assert_called_once_with(force=True)


@pytest.mark.asyncio
async def test_render_error_status_returns_error(tmp_path):
    executor = ManimExecutor()
    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_socket = MagicMock()
    mock_socket._sock = MagicMock()

    mock_client.containers.create.return_value = mock_container
    mock_container.attach_socket.return_value = mock_socket
    mock_container.wait.return_value = {"StatusCode": 1}
    mock_container.logs.return_value = b'{"status":"error","error":"boom"}'

    with patch("app.services.manim_executor.docker.from_env", return_value=mock_client):
        with patch("app.services.manim_executor.MANIM_OUTPUT_DIR", tmp_path):
            result = await executor.render("bad", problem_id=3, step_number=1)

    assert result["status"] == "error"
    assert str(result["error"]) == "boom"
    mock_container.remove.assert_called_once_with(force=True)


@pytest.mark.asyncio
async def test_render_missing_video_path(tmp_path):
    executor = ManimExecutor()
    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_socket = MagicMock()
    mock_socket._sock = MagicMock()

    mock_client.containers.create.return_value = mock_container
    mock_container.attach_socket.return_value = mock_socket
    mock_container.wait.return_value = {"StatusCode": 0}
    mock_container.logs.return_value = b'{"status":"success"}'

    with patch("app.services.manim_executor.docker.from_env", return_value=mock_client):
        with patch("app.services.manim_executor.MANIM_OUTPUT_DIR", tmp_path):
            result = await executor.render("code", problem_id=9, step_number=4)

    assert result["status"] == "error"
    assert "video" in str(result["error"]).lower()
    mock_container.remove.assert_called_once_with(force=True)


@pytest.mark.asyncio
async def test_render_timeout_cleans_up_container(tmp_path):
    executor = ManimExecutor()
    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_socket = MagicMock()
    mock_socket._sock = MagicMock()

    mock_client.containers.create.return_value = mock_container
    mock_container.attach_socket.return_value = mock_socket

    async def _timeout_wait_for(coro, timeout):
        coro.close()
        raise asyncio.TimeoutError

    with patch("app.services.manim_executor.docker.from_env", return_value=mock_client):
        with patch("app.services.manim_executor.MANIM_OUTPUT_DIR", tmp_path):
            with patch("app.services.manim_executor.asyncio.wait_for", side_effect=_timeout_wait_for):
                result = await executor.render("loop", problem_id=7, step_number=1)

    assert result["status"] == "error"
    assert "timed out" in str(result["error"]).lower()
    mock_container.remove.assert_called_once_with(force=True)


@pytest.mark.asyncio
async def test_check_docker_available_false_on_exception():
    executor = ManimExecutor()
    with patch("app.services.manim_executor.docker.from_env", side_effect=DockerException("no docker")):
        available = await executor.check_docker_available()

    assert available is False
