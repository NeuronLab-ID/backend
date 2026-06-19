import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from app.config import OPENCODE_CONFIG_PATH

_ENV_REF_RE = re.compile(r"\{?env:([A-Za-z_][A-Za-z0-9_]*)\}?|^\$([A-Za-z_][A-Za-z0-9_]*)$")


@dataclass(frozen=True)
class OpenCodeProviderConfig:
    provider: str
    model: str
    api_key: str
    base_url: str | None


_DEFAULT_MANIM_OPENAI_COMPATIBLE_MODEL = "cx/gpt-5.5-xhigh"


def _resolve_secret_ref(value: object) -> str:
    if not isinstance(value, str):
        return ""
    match = _ENV_REF_RE.search(value.strip())
    if match:
        env_name = match.group(1) or match.group(2)
        return os.getenv(env_name, "")
    return value


def _find_provider_config(data: object, provider_name: str) -> dict[str, object]:
    if isinstance(data, dict):
        mapping = cast("dict[object, object]", data)
        for key, value in mapping.items():
            if key == provider_name and isinstance(value, dict):
                return cast("dict[str, object]", value)
        for value in mapping.values():
            found = _find_provider_config(value, provider_name)
            if found:
                return found
    elif isinstance(data, list):
        items = cast("list[object]", data)
        for item in items:
            found = _find_provider_config(item, provider_name)
            if found:
                return found
    return {}


def _pick_first(mapping: dict[str, object], keys: tuple[str, ...]) -> str:
    stack = [mapping]
    while stack:
        current = stack.pop()
        for key in keys:
            if key in current:
                value = _resolve_secret_ref(current[key])
                if value:
                    return value
        for value in current.values():
            if isinstance(value, dict):
                stack.append(cast("dict[str, object]", value))
    return ""


def _env_with_legacy(canonical_name: str, legacy_name: str, default: str = "") -> str:
    if canonical_name in os.environ:
        return os.environ[canonical_name]
    return os.getenv(legacy_name, default)


def _read_opencode_provider_config(config_path: Path | None, provider_name: str) -> dict[str, object]:
    path = config_path or OPENCODE_CONFIG_PATH
    if not path.exists():
        return {}
    try:
        data = cast(object, json.loads(path.read_text()))
    except (OSError, json.JSONDecodeError):
        return {}
    return _find_provider_config(data, provider_name)


def load_manim_openai_compatible_config(config_path: Path | None = None) -> OpenCodeProviderConfig:
    model = _env_with_legacy(
        "MANIM_OPENAI_COMPATIBLE_MODEL",
        "MANIM_9ROUTER_MODEL",
    )
    api_key = _env_with_legacy("MANIM_OPENAI_COMPATIBLE_API_KEY", "MANIM_9ROUTER_API_KEY")
    base_url_value = _env_with_legacy("MANIM_OPENAI_COMPATIBLE_BASE_URL", "MANIM_9ROUTER_BASE_URL")
    base_url = base_url_value or None

    provider_config = _read_opencode_provider_config(config_path, "9router")
    if provider_config:
        api_key = api_key or _pick_first(provider_config, ("api_key", "apiKey", "key", "token"))
        base_url = base_url or _pick_first(provider_config, ("base_url", "baseUrl", "baseURL", "url", "api_url")) or None

    model = model or os.getenv("AI_MODEL", _DEFAULT_MANIM_OPENAI_COMPATIBLE_MODEL)
    api_key = api_key or os.getenv("OPENAI_API_KEY", "")
    base_url = base_url or os.getenv("OPENAI_BASE_URL") or None

    return OpenCodeProviderConfig(provider="openai-compatible", model=model, api_key=api_key, base_url=base_url)


def load_9router_opencode_config(config_path: Path | None = None) -> OpenCodeProviderConfig:
    cfg = load_manim_openai_compatible_config(config_path)
    return OpenCodeProviderConfig(provider="9router", model=cfg.model, api_key=cfg.api_key, base_url=cfg.base_url)
