"""
Docker-based code executor for sandboxed Python execution.
Uses Docker CLI via subprocess for reliable cross-platform support.
"""
import subprocess
import asyncio
import json
import os
import uuid
from typing import Dict, List, Any, Optional
import time
import tempfile
import logging

logger = logging.getLogger(__name__)

SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "deepml-sandbox:latest")
SANDBOX_TIMEOUT = int(os.getenv("SANDBOX_TIMEOUT", "30"))
SANDBOX_MEMORY = os.getenv("SANDBOX_MEMORY", "512m")
POOL_SIZE = int(os.getenv("CONTAINER_POOL_SIZE", "2"))


class ContainerPool:
    """
    Manages a pool of warm Docker containers for fast code execution.
    Containers are kept alive with 'sleep infinity' and code is executed
    via 'docker exec' to avoid container creation overhead.
    """

    def __init__(self, pool_size: int = POOL_SIZE):
        self.pool_size = pool_size
        self._containers: List[str] = []
        self._available: asyncio.Queue = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._started = False

    async def start(self) -> None:
        """Create and initialize all containers in the pool."""
        async with self._lock:
            if self._started:
                return

            logger.info(f"Starting container pool with {self.pool_size} containers...")

            for i in range(self.pool_size):
                container_name = f"deepml-sandbox-{uuid.uuid4().hex[:8]}"
                success = await self._create_container(container_name)
                if success:
                    self._containers.append(container_name)
                    await self._available.put(container_name)
                    logger.info(f"Created container: {container_name}")
                else:
                    logger.warning(f"Failed to create container {i+1}/{self.pool_size}")

            self._started = True
            logger.info(f"Container pool started with {len(self._containers)} containers")

    async def _create_container(self, container_name: str) -> bool:
        """Create a warm container with sleep infinity."""
        try:
            # Check if image exists
            check_image = subprocess.run(
                ["docker", "image", "inspect", SANDBOX_IMAGE],
                capture_output=True,
                timeout=5
            )
            if check_image.returncode != 0:
                logger.error(f"Sandbox image '{SANDBOX_IMAGE}' not found")
                return False

            # Create container with sleep infinity to keep it alive
            cmd = [
                "docker", "run", "-d",
                "--name", container_name,
                "--network", "none",
                "--memory", SANDBOX_MEMORY,
                "--cpus", "1",
                "--user", "nobody",
                "--tmpfs", "/tmp:size=64m",
                SANDBOX_IMAGE,
                "sleep", "infinity"
            ]

            proc = subprocess.run(cmd, capture_output=True, timeout=30)
            if proc.returncode == 0:
                # Wait a moment for container to be ready
                await asyncio.sleep(0.5)
                return True
            else:
                logger.error(f"Failed to create container: {proc.stderr.decode()}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Timeout creating container")
            return False
        except Exception as e:
            logger.error(f"Error creating container: {e}")
            return False

    async def acquire(self, timeout: float = 10.0) -> Optional[str]:
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
        if container_name in self._containers:
            await self._available.put(container_name)

    async def shutdown(self) -> None:
        """Remove all containers from the pool."""
        async with self._lock:
            if not self._started:
                return

            logger.info("Shutting down container pool...")

            for container_name in self._containers:
                try:
                    subprocess.run(
                        ["docker", "rm", "-f", container_name],
                        capture_output=True,
                        timeout=10
                    )
                    logger.info(f"Removed container: {container_name}")
                except Exception as e:
                    logger.warning(f"Failed to remove container {container_name}: {e}")

            self._containers.clear()
            # Clear the queue
            while not self._available.empty():
                try:
                    self._available.get_nowait()
                except asyncio.QueueEmpty:
                    break

            self._started = False
            logger.info("Container pool shut down")

    @property
    def is_started(self) -> bool:
        """Check if the pool has been started."""
        return self._started


# Module-level singleton pool instance
container_pool = ContainerPool()


async def execute_code(code: str, test_cases: List[Dict], timeout: int = 30) -> Dict[str, Any]:
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

    # Prepare the execution payload
    payload = {
        "code": code,
        "test_cases": test_cases
    }

    try:
        # Try to use container pool first (faster)
        if container_pool.is_started:
            result = await run_in_docker_exec(json.dumps(payload), timeout)
        else:
            # Fallback to docker run if pool not started
            logger.warning("Container pool not started, falling back to docker run")
            result = await run_in_docker_cli(json.dumps(payload), timeout)

        execution_time = time.time() - start_time

        if result["status"] == "success":
            return {
                "success": all(r["passed"] for r in result["results"]),
                "results": result["results"],
                "error": None,
                "execution_time": execution_time
            }
        else:
            return {
                "success": False,
                "results": [],
                "error": result.get("error", "Unknown error"),
                "execution_time": execution_time
            }

    except asyncio.TimeoutError:
        return {
            "success": False,
            "results": [],
            "error": f"Execution timed out after {timeout} seconds",
            "execution_time": timeout
        }
    except Exception as e:
        return {
            "success": False,
            "results": [],
            "error": str(e),
            "execution_time": time.time() - start_time
        }


async def run_in_docker_exec(payload: str, timeout: int) -> Dict[str, Any]:
    """
    Run code in a warm Docker container using docker exec.
    This avoids container creation overhead.
    """
    container = None
    try:
        # Acquire a container from the pool
        container = await container_pool.acquire()
        if container is None:
            # Fallback to docker run if no container available
            return await run_in_docker_cli(payload, timeout)

        # Execute code in the warm container using docker exec
        cmd = [
            "docker", "exec", "-i",
            container,
            "python", "runner.py"
        ]

        proc = subprocess.run(
            cmd,
            input=payload.encode(),
            capture_output=True,
            timeout=timeout
        )

        stdout = proc.stdout.decode("utf-8").strip()
        stderr = proc.stderr.decode("utf-8").strip()

        if proc.returncode == 0:
            # Try to extract JSON from output that may have extra text before it
            # (e.g., from os.system() or print statements in user code)
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                # Try to find JSON object in the output
                json_start = stdout.rfind('{"status":')
                if json_start == -1:
                    json_start = stdout.rfind('{')

                if json_start != -1:
                    try:
                        json_str = stdout[json_start:]
                        result = json.loads(json_str)
                        # Capture any extra output before JSON as a warning
                        extra_output = stdout[:json_start].strip()
                        if extra_output and "results" in result:
                            result["warning"] = f"Code produced extra output: {extra_output[:200]}"
                        return result
                    except json.JSONDecodeError:
                        pass

                return {"status": "error", "error": f"Invalid output from sandbox: {stdout[:500]}"}
        else:
            return {"status": "error", "error": stderr or stdout or f"Exit code: {proc.returncode}"}

    except subprocess.TimeoutExpired:
        # Kill any running python process in the container
        if container:
            subprocess.run(
                ["docker", "exec", container, "pkill", "-9", "python"],
                capture_output=True,
                timeout=5
            )
        raise asyncio.TimeoutError()
    except FileNotFoundError:
        return {"status": "error", "error": "Docker CLI not found. Please install Docker."}
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        # Always release the container back to the pool
        if container:
            await container_pool.release(container)


async def run_in_docker_cli(payload: str, timeout: int) -> Dict[str, Any]:
    """
    Run code in a Docker container using Docker CLI (subprocess).
    This is a fallback method when the container pool is not available.
    """
    try:
        # Check if Docker is available
        check = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5
        )
        if check.returncode != 0:
            return {"status": "error", "error": "Docker is not running"}

        # Check if image exists
        check_image = subprocess.run(
            ["docker", "image", "inspect", SANDBOX_IMAGE],
            capture_output=True,
            timeout=5
        )
        if check_image.returncode != 0:
            return {
                "status": "error",
                "error": f"Sandbox image '{SANDBOX_IMAGE}' not found. Run: docker build -t {SANDBOX_IMAGE} sandbox/"
            }

        # Run container with security restrictions
        # Using echo and pipe to send payload to stdin
        cmd = [
            "docker", "run",
            "--rm",                     # Remove after exit
            "-i",                       # Interactive (stdin)
            "--network", "none",        # No network access
            "--memory", SANDBOX_MEMORY, # Memory limit
            "--cpus", "1",              # CPU limit
            "--user", "nobody",         # Non-root user
            "--tmpfs", "/tmp:size=64m", # Writable tmpfs
            SANDBOX_IMAGE,
            "python", "runner.py"
        ]

        proc = subprocess.run(
            cmd,
            input=payload.encode(),
            capture_output=True,
            timeout=timeout
        )

        stdout = proc.stdout.decode("utf-8").strip()
        stderr = proc.stderr.decode("utf-8").strip()

        if proc.returncode == 0:
            # Try to extract JSON from output that may have extra text before it
            # (e.g., from os.system() or print statements in user code)
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                # Try to find JSON object in the output
                json_start = stdout.rfind('{"status":')
                if json_start == -1:
                    json_start = stdout.rfind('{')

                if json_start != -1:
                    try:
                        json_str = stdout[json_start:]
                        result = json.loads(json_str)
                        # Capture any extra output before JSON as a warning
                        extra_output = stdout[:json_start].strip()
                        if extra_output and "results" in result:
                            result["warning"] = f"Code produced extra output: {extra_output[:200]}"
                        return result
                    except json.JSONDecodeError:
                        pass

                return {"status": "error", "error": f"Invalid output from sandbox: {stdout[:500]}"}
        else:
            return {"status": "error", "error": stderr or stdout or f"Exit code: {proc.returncode}"}

    except subprocess.TimeoutExpired:
        # Kill the container if it's still running
        subprocess.run(["docker", "kill", "$(docker ps -q)"], shell=True, capture_output=True)
        raise asyncio.TimeoutError()
    except FileNotFoundError:
        return {"status": "error", "error": "Docker CLI not found. Please install Docker."}
    except Exception as e:
        return {"status": "error", "error": str(e)}
