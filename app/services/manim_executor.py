import asyncio
import io
import json
import os
import tarfile
import time
from typing import Any, Callable, ParamSpec, TypeVar, cast

import docker
from docker.errors import APIError, DockerException, NotFound

from app.config import (
    MANIM_MAX_CONCURRENT_RENDERS,
    MANIM_OUTPUT_DIR,
    MANIM_RENDER_QUALITY,
    MANIM_SANDBOX_IMAGE,
    MANIM_TIMEOUT,
)
from app.logging_config import get_logger

logger: Any = get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


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


class ManimExecutor:
    def __init__(self) -> None:
        self._client: docker.DockerClient | None = None
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(MANIM_MAX_CONCURRENT_RENDERS)

    def _get_client(self) -> docker.DockerClient:
        if self._client is None:
            try:
                self._client = docker.from_env()
            except DockerException as exc:
                logger.error("Failed to initialize Docker client: {}", exc)
                raise
        return self._client

    async def render(
        self, manim_code: str, problem_id: int, step_number: int, video_type: str = "calculation"
    ) -> dict[str, object]:
        start_time = time.time()
        container = None
        async with self._semaphore:
            try:
                client = self._get_client()
                input_data = {
                    "code": manim_code,
                    "quality": MANIM_RENDER_QUALITY,
                    "scene_name": "MainScene",
                    "timeout": MANIM_TIMEOUT,
                }
                container = await _to_thread(
                    client.containers.create,
                    image=MANIM_SANDBOX_IMAGE,
                    command=["python", "manim_runner.py"],
                    stdin_open=True,
                    network_disabled=True,
                    mem_limit="1g",
                    pids_limit=100,
                )
                await _to_thread(container.start)

                raw_socket = await _to_thread(container.attach_socket, params={"stdin": True, "stream": True})
                # On Linux the socket wraps _sock; on Windows (NpipeSocket) methods are direct
                sock = getattr(raw_socket, "_sock", raw_socket)
                payload = json.dumps(input_data).encode("utf-8") + b"\n"
                await _to_thread(sock.sendall, payload)
                await _to_thread(sock.shutdown, 2)
                await _to_thread(raw_socket.close)

                wait_task = _to_thread(container.wait, timeout=MANIM_TIMEOUT + 10)
                _ = await asyncio.wait_for(wait_task, timeout=MANIM_TIMEOUT + 15)

                stdout_bytes = await _to_thread(container.logs, stdout=True, stderr=False)
                stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
                result = _parse_runner_output(stdout)
                elapsed_ms = int((time.time() - start_time) * 1000)

                if result.get("status") == "success":
                    video_path = result.get("video_path")
                    if not isinstance(video_path, str):
                        return {
                            "status": "error",
                            "error": "Missing video path from renderer",
                            "render_time_ms": elapsed_ms,
                        }

                    local_dir = os.path.join(str(MANIM_OUTPUT_DIR), str(problem_id))
                    os.makedirs(local_dir, exist_ok=True)
                    local_path = os.path.join(local_dir, f"step_{step_number}_{video_type}.mp4")

                    stream, _ = await _to_thread(container.get_archive, video_path)
                    tar_data = b"".join(stream)
                    tar_buffer = io.BytesIO(tar_data)
                    with tarfile.open(fileobj=tar_buffer) as tar:
                        members = tar.getmembers()
                        for member in members:
                            if member.name.endswith(".mp4"):
                                extracted = tar.extractfile(member)
                                if extracted is None:
                                    continue
                                mp4_data = extracted.read()
                                with open(local_path, "wb") as out:
                                    out.write(mp4_data)
                                break
                        else:
                            return {
                                "status": "error",
                                "error": "MP4 not found in archive",
                                "render_time_ms": elapsed_ms,
                            }

                    return {
                        "status": "success",
                        "video_path": str(local_path),
                        "render_time_ms": elapsed_ms,
                    }

                return {
                    "status": "error",
                    "error": result.get("error", "Unknown error"),
                    "render_time_ms": elapsed_ms,
                }
            except asyncio.TimeoutError:
                elapsed_ms = int((time.time() - start_time) * 1000)
                return {
                    "status": "error",
                    "error": f"Render timed out after {MANIM_TIMEOUT} seconds",
                    "render_time_ms": elapsed_ms,
                }
            except (DockerException, APIError) as exc:
                elapsed_ms = int((time.time() - start_time) * 1000)
                logger.error("Manim render failed: {}", exc)
                return {
                    "status": "error",
                    "error": str(exc),
                    "render_time_ms": elapsed_ms,
                }
            except Exception as exc:
                elapsed_ms = int((time.time() - start_time) * 1000)
                logger.error("Manim render failed: {}", exc)
                return {
                    "status": "error",
                    "error": str(exc),
                    "render_time_ms": elapsed_ms,
                }
            finally:
                if container is not None:
                    try:
                        await _to_thread(container.remove, force=True)
                    except NotFound:
                        pass
                    except Exception as exc:
                        logger.warning("Failed to remove manim container: {}", exc)

    async def check_docker_available(self) -> bool:
        try:
            _ = self._get_client()
            return True
        except DockerException:
            return False


manim_executor = ManimExecutor()
