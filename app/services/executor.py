"""
Docker-based code executor for sandboxed Python execution.
Uses Docker SDK for container pooling and exec-based runs.
"""

# pyright: reportDeprecated=false
# pyright: reportMissingModuleSource=false
# pyright: reportMissingTypeArgument=false
# pyright: reportUnknownParameterType=false

import asyncio
import base64
import json
import logging
import time
import uuid
from typing import Callable, Dict, List, ParamSpec, TypeVar, cast

import docker
from docker.errors import APIError, DockerException, NotFound
from docker.models.containers import Container

from app.config import (
    SANDBOX_CONTAINER_TTL,
    SANDBOX_IMAGE,
    SANDBOX_MAX_EXECUTIONS,
    SANDBOX_MEMORY,
    SANDBOX_PIDS_LIMIT,
    SANDBOX_POOL_SIZE,
    SANDBOX_SECURITY_LEVEL,
    SANDBOX_TIMEOUT,
)

logger = logging.getLogger(__name__)


P = ParamSpec("P")
T = TypeVar("T")
Any = object


async def _to_thread(func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    return await asyncio.to_thread(func, *args, **kwargs)


def _parse_runner_output(stdout: str) -> dict[str, object]:
    try:
        return cast(dict[str, object], json.loads(stdout))
    except json.JSONDecodeError:
        json_start = stdout.rfind('{"status":')
        if json_start == -1:
            json_start = stdout.rfind("{")

        if json_start != -1:
            try:
                json_str = stdout[json_start:]
                result = cast(dict[str, object], json.loads(json_str))
                extra_output = stdout[:json_start].strip()
                if extra_output and "results" in result:
                    result["warning"] = f"Code produced extra output: {extra_output[:200]}"
                return result
            except json.JSONDecodeError:
                pass

        return {
            "status": "error",
            "error": f"Invalid output from sandbox: {stdout[:500]}",
        }


class ContainerPool:
    """
    Manages a pool of warm Docker containers for fast code execution.
    Containers are kept alive with 'sleep infinity' and code is executed
    via exec_run to avoid container creation overhead.
    """

    def __init__(self, pool_size: int = SANDBOX_POOL_SIZE):
        self.pool_size: int = pool_size
        self._client: docker.DockerClient | None = None
        self._containers: dict[str, Container] = {}
        self._available: asyncio.Queue[str] = asyncio.Queue()
        self._lock: asyncio.Lock = asyncio.Lock()
        self._started: bool = False
        self._replacement_failures: list[float] = []
        self._exec_counts: dict[str, int] = {}
        self._created_at: dict[str, float] = {}

    async def start(self) -> None:
        """Create and initialize all containers in the pool."""
        async with self._lock:
            if self._started:
                return

            self._client = docker.DockerClient.from_env()

            logger.info("Starting container pool with %s containers...", self.pool_size)

            await self._cleanup_orphans()

            for _ in range(self.pool_size):
                container_name = f"deepml-sandbox-{uuid.uuid4().hex[:8]}"
                container = await self._create_container(container_name)
                if container is not None:
                    self._containers[container_name] = container
                    await self._available.put(container_name)
                    logger.info("Created container: %s", container_name)
                else:
                    logger.warning("Failed to create container in pool")

            self._started = True
            logger.info("Container pool started with %s containers", len(self._containers))

    async def _cleanup_orphans(self) -> None:
        if self._client is None:
            return
        try:
            containers = await _to_thread(
                self._client.containers.list,
                all=True,
                filters={"name": "deepml-sandbox-"},
            )
            for container in containers:
                try:
                    await _to_thread(container.remove, force=True)
                except Exception as exc:
                    logger.warning("Failed to remove orphan container %s: %s", container.name, exc)
        except Exception as exc:
            logger.warning("Failed to cleanup orphan containers: %s", exc)

    async def _create_container(self, container_name: str) -> Container | None:
        if self._client is None:
            return None
        try:
            if SANDBOX_SECURITY_LEVEL == "full":
                container = await _to_thread(
                    self._client.containers.run,
                    image=SANDBOX_IMAGE,
                    command="sleep infinity",
                    name=container_name,
                    detach=True,
                    network_mode="none",
                    mem_limit=SANDBOX_MEMORY,
                    cpu_period=100000,
                    cpu_quota=100000,
                    user="nobody",
                    tmpfs={"/tmp": "size=64m,mode=1777"},
                    cap_drop=["ALL"],
                    read_only=True,
                    security_opt=["no-new-privileges"],
                    pids_limit=SANDBOX_PIDS_LIMIT,
                )
                self._created_at[container_name] = time.time()
                self._exec_counts[container_name] = 0
                return container

            container = await _to_thread(
                self._client.containers.run,
                image=SANDBOX_IMAGE,
                command="sleep infinity",
                name=container_name,
                detach=True,
                network_mode="none",
                mem_limit=SANDBOX_MEMORY,
                cpu_period=100000,
                cpu_quota=100000,
                user="nobody",
                tmpfs={"/tmp": "size=64m,mode=1777"},
            )
            self._created_at[container_name] = time.time()
            self._exec_counts[container_name] = 0
            return container
        except APIError as exc:
            if SANDBOX_SECURITY_LEVEL == "full":
                logger.warning("Security flags failed, retrying without them: %s", exc)
                try:
                    container = await _to_thread(
                        self._client.containers.run,
                        image=SANDBOX_IMAGE,
                        command="sleep infinity",
                        name=container_name,
                        detach=True,
                        network_mode="none",
                        mem_limit=SANDBOX_MEMORY,
                        cpu_period=100000,
                        cpu_quota=100000,
                        user="nobody",
                        tmpfs={"/tmp": "size=64m,mode=1777"},
                    )
                    self._created_at[container_name] = time.time()
                    self._exec_counts[container_name] = 0
                    return container
                except Exception as inner_exc:
                    logger.error("Failed to create container without security flags: %s", inner_exc)
                    return None
            logger.error("Failed to create container: %s", exc)
            return None
        except DockerException as exc:
            logger.error("Docker error creating container: %s", exc)
            return None

    async def acquire(self, timeout: float = 10.0) -> str | None:
        """Get an available container from the pool."""
        if not self._started:
            logger.warning("Container pool not started, returning None")
            return None

        try:
            return await asyncio.wait_for(self._available.get(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for available container")
            return None

    async def release(self, container_name: str) -> None:
        """Return a container to the pool."""
        container = self._containers.get(container_name)
        if container is None:
            return

        try:
            await _to_thread(container.reload)
            if container.status != "running":
                logger.warning("Container %s unhealthy, replacing", container_name)
                await self._replace_container(container_name)
                return
        except Exception as exc:
            logger.warning("Failed to reload container %s: %s", container_name, exc)
            await self._replace_container(container_name)
            return

        exec_count = self._exec_counts.get(container_name, 0) + 1
        self._exec_counts[container_name] = exec_count
        age = time.time() - self._created_at.get(container_name, 0)
        if exec_count >= SANDBOX_MAX_EXECUTIONS or age >= SANDBOX_CONTAINER_TTL:
            logger.info(
                "Recycling container %s: execs=%s, age=%ss",
                container_name,
                exec_count,
                f"{age:.0f}",
            )
            await self._replace_container(container_name)
            return

        await self._available.put(container_name)

    async def _replace_container(self, old_name: str) -> None:
        now = time.time()
        self._replacement_failures = [t for t in self._replacement_failures if now - t <= 60]
        if len(self._replacement_failures) >= 3:
            logger.critical("Container replacement circuit breaker tripped")
            _ = self._containers.pop(old_name, None)
            _ = self._exec_counts.pop(old_name, None)
            _ = self._created_at.pop(old_name, None)
            return

        container = self._containers.pop(old_name, None)
        _ = self._exec_counts.pop(old_name, None)
        _ = self._created_at.pop(old_name, None)
        if container is not None:
            try:
                await _to_thread(container.remove, force=True)
            except NotFound:
                pass
            except Exception as exc:
                logger.warning("Failed to remove container %s: %s", old_name, exc)

        new_container = await self._create_container(old_name)
        if new_container is None:
            self._replacement_failures.append(now)
            logger.error("Failed to replace container %s", old_name)
            return

        self._containers[old_name] = new_container
        await self._available.put(old_name)

    async def shutdown(self) -> None:
        """Remove all containers from the pool."""
        async with self._lock:
            if not self._started:
                return

            logger.info("Shutting down container pool...")
            for container in list(self._containers.values()):
                try:
                    await _to_thread(container.remove, force=True)
                except Exception as exc:
                    logger.warning("Failed to remove container %s: %s", container.name, exc)

            self._containers.clear()
            self._exec_counts.clear()
            self._created_at.clear()
            while not self._available.empty():
                try:
                    _ = self._available.get_nowait()
                except asyncio.QueueEmpty:
                    break

            self._started = False
            if self._client is not None:
                try:
                    await _to_thread(self._client.close)
                except Exception as exc:
                    logger.warning("Failed to close Docker client: %s", exc)
                self._client = None
            logger.info("Container pool shut down")

    @property
    def is_started(self) -> bool:
        """Check if the pool has been started."""
        return self._started

    def get_container(self, container_name: str) -> Container | None:
        return self._containers.get(container_name)


container_pool = ContainerPool()


async def _run_in_container(payload_json: str, container_name: str, timeout: int) -> dict[str, object]:
    container = container_pool.get_container(container_name)
    if container is None:
        return {"status": "error", "error": "Container not found"}

    b64_payload = base64.b64encode(payload_json.encode("utf-8")).decode("ascii")
    command = ["sh", "-c", f"echo '{b64_payload}' | base64 -d | python runner.py"]

    try:
        exec_coro = _to_thread(container.exec_run, command, demux=True)
        exec_result = cast(
            tuple[int, tuple[bytes | None, bytes | None]], await asyncio.wait_for(exec_coro, timeout=timeout)
        )
        exit_code, output = exec_result
        stdout_bytes = (output[0] if output else None) or b""
        stderr_bytes = (output[1] if output else None) or b""
        stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
        stderr = stderr_bytes.decode("utf-8", errors="replace").strip()

        if exit_code == 0:
            return _parse_runner_output(stdout)

        return {
            "status": "error",
            "error": stderr or stdout or f"Exit code: {exit_code}",
        }
    except asyncio.TimeoutError:
        try:
            _ = await _to_thread(container.exec_run, ["pkill", "-9", "python"])
        except Exception as exc:
            logger.warning("Failed to kill python process in container %s: %s", container_name, exc)
        raise
    except Exception as exc:
        logger.error("Error executing code in container %s: %s", container_name, exc)
        return {"status": "error", "error": str(exc)}


async def execute_code(code: str, test_cases: List[Dict], timeout: int = 30) -> Dict[str, Any]:  # type: ignore[reportExplicitAny]
    """
    Execute user code in a Docker sandbox using the container pool.

    Args:
        code: User's Python code
        test_cases: List of test cases with 'test' and 'expected_output' keys
        timeout: Maximum execution time in seconds

    Returns:
        Dict with success, results, error, and execution_time
    """
    start_time = time.time()
    payload = cast(dict[str, object], {"code": code, "test_cases": test_cases})
    effective_timeout = timeout or SANDBOX_TIMEOUT

    if not container_pool.is_started:
        return {
            "success": False,
            "results": [],
            "error": "Container pool not started",
            "execution_time": 0,
        }

    container_name = await container_pool.acquire(timeout=10.0)
    if container_name is None:
        return {
            "success": False,
            "results": [],
            "error": "No available containers",
            "execution_time": time.time() - start_time,
        }

    try:
        result = await _run_in_container(json.dumps(payload), container_name, effective_timeout)
        execution_time = time.time() - start_time

        if result.get("status") == "success":
            results = result.get("results")
            if isinstance(results, list):
                normalized_results = cast(list[dict[str, object]], results)
                passed = all(r.get("passed") for r in normalized_results)
            else:
                passed = False
                normalized_results = []
            return {
                "success": passed,
                "results": normalized_results,
                "error": None,
                "execution_time": execution_time,
            }

        return {
            "success": False,
            "results": [],
            "error": result.get("error", "Unknown error"),
            "execution_time": execution_time,
        }
    except asyncio.TimeoutError:
        return {
            "success": False,
            "results": [],
            "error": f"Execution timed out after {effective_timeout} seconds",
            "execution_time": effective_timeout,
        }
    except Exception as exc:
        logger.error("Execution failed: %s", exc)
        return {
            "success": False,
            "results": [],
            "error": str(exc),
            "execution_time": time.time() - start_time,
        }
    finally:
        await container_pool.release(container_name)
