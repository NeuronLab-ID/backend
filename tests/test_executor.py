"""
Tests for the Docker-based code executor and container pool.
All Docker SDK calls are mocked — no Docker daemon required.
"""

import asyncio
import time

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.executor import ContainerPool, execute_code


# ==================== execute_code() tests ====================


@pytest.mark.asyncio
async def test_execute_code_pool_not_started():
    """execute_code() returns error dict when pool is not started."""
    pool = ContainerPool(pool_size=1)
    with patch("app.services.executor.container_pool", pool):
        result = await execute_code(
            code="print(42)",
            test_cases=[{"test": "print(42)", "expected_output": "42"}],
        )
    assert result["success"] is False
    assert result["results"] == []
    assert result["error"] == "Container pool not started"
    assert result["execution_time"] == 0


@pytest.mark.asyncio
async def test_execute_code_return_schema_fields():
    """execute_code() result contains all ExecuteResponse fields."""
    pool = ContainerPool(pool_size=1)
    with patch("app.services.executor.container_pool", pool):
        result = await execute_code(code="x = 1", test_cases=[])
    for key in ("success", "results", "error", "execution_time"):
        assert key in result, f"Missing key: {key}"
    assert isinstance(result["success"], bool)
    assert isinstance(result["results"], list)
    assert isinstance(result["execution_time"], (int, float))


@pytest.mark.asyncio
async def test_execute_code_valid_code_success():
    """execute_code() with passing tests returns success=True."""
    mock_run_result = {
        "status": "success",
        "results": [
            {
                "test_number": 1,
                "passed": True,
                "input": "solution()",
                "expected": "42",
                "actual": "42",
                "error": None,
            }
        ],
    }
    with patch("app.services.executor.container_pool") as mock_pool:
        mock_pool.is_started = True
        mock_pool.acquire = AsyncMock(return_value="test-container-1")
        mock_pool.release = AsyncMock()
        with patch(
            "app.services.executor._run_in_container",
            new_callable=AsyncMock,
            return_value=mock_run_result,
        ):
            result = await execute_code(
                code="def solution(): return 42",
                test_cases=[{"test": "solution()", "expected_output": "42"}],
            )
    assert result["success"] is True
    assert len(result["results"]) == 1
    assert result["results"][0]["passed"] is True
    assert result["error"] is None
    assert result["execution_time"] >= 0


@pytest.mark.asyncio
async def test_execute_code_syntax_error():
    """execute_code() with syntax error returns success=False."""
    mock_run_result = {
        "status": "error",
        "error": "SyntaxError: invalid syntax (line 1)",
    }
    with patch("app.services.executor.container_pool") as mock_pool:
        mock_pool.is_started = True
        mock_pool.acquire = AsyncMock(return_value="test-container-1")
        mock_pool.release = AsyncMock()
        with patch(
            "app.services.executor._run_in_container",
            new_callable=AsyncMock,
            return_value=mock_run_result,
        ):
            result = await execute_code(
                code="def solution( return 42",
                test_cases=[{"test": "solution()", "expected_output": "42"}],
            )
    assert result["success"] is False
    assert "SyntaxError" in result["error"]
    assert result["results"] == []


@pytest.mark.asyncio
async def test_execute_code_timeout():
    """execute_code() with infinite loop returns timeout error."""
    with patch("app.services.executor.container_pool") as mock_pool:
        mock_pool.is_started = True
        mock_pool.acquire = AsyncMock(return_value="test-container-1")
        mock_pool.release = AsyncMock()
        with patch(
            "app.services.executor._run_in_container",
            new_callable=AsyncMock,
            side_effect=asyncio.TimeoutError(),
        ):
            result = await execute_code(
                code="while True: pass",
                test_cases=[{"test": "solution()", "expected_output": "42"}],
                timeout=5,
            )
    assert result["success"] is False
    assert "timed out" in result["error"].lower()
    assert result["results"] == []
    assert result["execution_time"] == 5


@pytest.mark.asyncio
async def test_execute_code_empty_test_cases():
    """execute_code() with empty test cases returns success=True (vacuous truth)."""
    mock_run_result = {"status": "success", "results": []}
    with patch("app.services.executor.container_pool") as mock_pool:
        mock_pool.is_started = True
        mock_pool.acquire = AsyncMock(return_value="test-container-1")
        mock_pool.release = AsyncMock()
        with patch(
            "app.services.executor._run_in_container",
            new_callable=AsyncMock,
            return_value=mock_run_result,
        ):
            result = await execute_code(code="x = 1", test_cases=[])
    assert result["success"] is True
    assert result["results"] == []
    assert result["error"] is None


@pytest.mark.asyncio
async def test_execute_code_no_available_containers():
    """execute_code() returns error when pool has no available containers."""
    with patch("app.services.executor.container_pool") as mock_pool:
        mock_pool.is_started = True
        mock_pool.acquire = AsyncMock(return_value=None)
        result = await execute_code(
            code="x = 1",
            test_cases=[{"test": "x", "expected_output": "1"}],
        )
    assert result["success"] is False
    assert "No available containers" in result["error"]


# ==================== ContainerPool tests ====================


@pytest.mark.asyncio
async def test_container_pool_start_creates_containers():
    """ContainerPool.start() creates the expected number of containers."""
    pool = ContainerPool(pool_size=3)
    mock_container = MagicMock()
    with patch("app.services.executor.docker.DockerClient.from_env", return_value=MagicMock()):
        with patch.object(pool, "_cleanup_orphans", new_callable=AsyncMock):
            with patch.object(pool, "_create_container", new_callable=AsyncMock, return_value=mock_container):
                await pool.start()
    assert pool.is_started is True
    assert len(pool._containers) == 3
    assert pool._available.qsize() == 3


@pytest.mark.asyncio
async def test_container_pool_shutdown_removes_all():
    """ContainerPool.shutdown() removes all containers and resets state."""
    pool = ContainerPool(pool_size=2)
    mock_container = MagicMock()
    with patch("app.services.executor.docker.DockerClient.from_env", return_value=MagicMock()):
        with patch.object(pool, "_cleanup_orphans", new_callable=AsyncMock):
            with patch.object(pool, "_create_container", new_callable=AsyncMock, return_value=mock_container):
                await pool.start()
    assert pool.is_started is True
    with patch("app.services.executor._to_thread", new_callable=AsyncMock):
        await pool.shutdown()
    assert pool.is_started is False
    assert len(pool._containers) == 0
    assert pool._available.empty()
    assert pool._client is None


@pytest.mark.asyncio
async def test_container_pool_acquire_returns_name():
    """ContainerPool.acquire() returns a container name from the pool."""
    pool = ContainerPool(pool_size=1)
    mock_container = MagicMock()
    with patch("app.services.executor.docker.DockerClient.from_env", return_value=MagicMock()):
        with patch.object(pool, "_cleanup_orphans", new_callable=AsyncMock):
            with patch.object(pool, "_create_container", new_callable=AsyncMock, return_value=mock_container):
                await pool.start()
    name = await pool.acquire()
    assert name is not None
    assert isinstance(name, str)
    assert pool._available.qsize() == 0


@pytest.mark.asyncio
async def test_container_pool_release_returns_to_pool():
    """ContainerPool.release() returns container back to available pool."""
    pool = ContainerPool(pool_size=1)
    mock_container = MagicMock()
    mock_container.status = "running"
    with patch("app.services.executor.docker.DockerClient.from_env", return_value=MagicMock()):
        with patch.object(pool, "_cleanup_orphans", new_callable=AsyncMock):
            with patch.object(pool, "_create_container", new_callable=AsyncMock, return_value=mock_container):
                await pool.start()
    # Set tracking metadata that _create_container normally sets
    for cname in pool._containers:
        pool._exec_counts[cname] = 0
        pool._created_at[cname] = time.time()
    name = await pool.acquire()
    assert pool._available.qsize() == 0
    with patch("app.services.executor._to_thread", new_callable=AsyncMock):
        await pool.release(name)
    assert pool._available.qsize() == 1
