import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import MANIM_9ROUTER_API_KEY, MANIM_9ROUTER_BASE_URL, MANIM_9ROUTER_MODEL, OPENCODE_CONFIG_PATH

_ENV_REF_RE = re.compile(r"\{?env:([A-Za-z_][A-Za-z0-9_]*)\}?|^\$([A-Za-z_][A-Za-z0-9_]*)$")


@dataclass(frozen=True)
class OpenCodeProviderConfig:
    provider: str
    model: str
    api_key: str
    base_url: str | None


def _resolve_secret_ref(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    match = _ENV_REF_RE.search(value.strip())
    if match:
        env_name = match.group(1) or match.group(2)
        return os.getenv(env_name, "")
    return value


def _find_provider_config(data: Any, provider_name: str) -> dict[str, Any]:
    if isinstance(data, dict):
        for key, value in data.items():
            if key == provider_name and isinstance(value, dict):
                return value
        for value in data.values():
            found = _find_provider_config(value, provider_name)
            if found:
                return found
    elif isinstance(data, list):
        for item in data:
            found = _find_provider_config(item, provider_name)
            if found:
                return found
    return {}


def _pick_first(mapping: dict[str, Any], keys: tuple[str, ...]) -> str:
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
                stack.append(value)
    return ""


def load_9router_opencode_config(config_path: Path | None = None) -> OpenCodeProviderConfig:
    model = MANIM_9ROUTER_MODEL or "cx/gpt-5.5-xhigh"
    api_key = MANIM_9ROUTER_API_KEY
    base_url = MANIM_9ROUTER_BASE_URL or None
    path = config_path or OPENCODE_CONFIG_PATH

    if path.exists():
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            data = {}
        provider_config = _find_provider_config(data, "9router")
        if provider_config:
            api_key = api_key or _pick_first(provider_config, ("api_key", "apiKey", "key", "token"))
            base_url = base_url or _pick_first(provider_config, ("base_url", "baseUrl", "baseURL", "url", "api_url")) or None

    return OpenCodeProviderConfig(provider="9router", model=model, api_key=api_key, base_url=base_url)
