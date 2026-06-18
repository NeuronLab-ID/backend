from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from fastapi import HTTPException

from app.config import MANIM_DEFAULT_BACKEND, MANIM_EGPU_DEVICE_PATHS, MANIM_EGPU_ENABLED

ManimBackendName = Literal["cpu", "egpu"]
_ALLOWED_EGPU_DEVICE_PATHS = {"/dev/dri"}


@dataclass(frozen=True)
class ManimBackendPolicy:
    name: ManimBackendName
    available: bool
    default: bool
    reason: str | None = None
    docker_devices: tuple[str, ...] = ()

    def docker_kwargs(self) -> dict[str, object]:
        if not self.docker_devices:
            return {}
        return {"devices": list(self.docker_devices)}


def _validated_egpu_devices() -> tuple[str, ...]:
    devices: list[str] = []
    for raw_path in MANIM_EGPU_DEVICE_PATHS:
        if raw_path not in _ALLOWED_EGPU_DEVICE_PATHS:
            continue
        if Path(raw_path).exists():
            devices.append(f"{raw_path}:{raw_path}:rwm")
    return tuple(devices)


def list_manim_backend_policies() -> list[ManimBackendPolicy]:
    default_backend = MANIM_DEFAULT_BACKEND if MANIM_DEFAULT_BACKEND in {"cpu", "egpu"} else "cpu"
    egpu_devices = _validated_egpu_devices() if MANIM_EGPU_ENABLED else ()
    egpu_available = bool(egpu_devices)
    egpu_reason = None
    if not MANIM_EGPU_ENABLED:
        egpu_reason = "eGPU backend is disabled by policy"
    elif not egpu_devices:
        egpu_reason = "No allowlisted eGPU device is available"

    if default_backend == "egpu" and not egpu_available:
        default_backend = "cpu"

    return [
        ManimBackendPolicy(name="cpu", available=True, default=default_backend == "cpu"),
        ManimBackendPolicy(
            name="egpu",
            available=egpu_available,
            default=default_backend == "egpu",
            reason=egpu_reason,
            docker_devices=egpu_devices,
        ),
    ]


def get_manim_backend_policy(name: str | None) -> ManimBackendPolicy:
    requested = (name or "cpu").lower()
    if requested not in {"cpu", "egpu"}:
        raise HTTPException(400, "Manim backend must be 'cpu' or 'egpu'")

    for policy in list_manim_backend_policies():
        if policy.name == requested:
            if not policy.available:
                raise HTTPException(400, policy.reason or f"Manim backend {requested} is unavailable")
            return policy

    raise HTTPException(400, "Manim backend is unavailable")


def default_manim_backend() -> ManimBackendName:
    for policy in list_manim_backend_policies():
        if policy.default and policy.available:
            return policy.name
    return "cpu"
