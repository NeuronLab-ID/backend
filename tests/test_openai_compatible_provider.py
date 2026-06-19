import json
from pathlib import Path
from typing import Protocol
from unittest.mock import MagicMock, patch

from app.services.ai_providers.ai_provider_factory import clear_providers, get_provider
from app.services.ai_providers.openai_provider import OpenAIProvider
from app.services.ai_providers.opencode_config import load_9router_opencode_config, load_manim_openai_compatible_config


class MonkeyPatchFixture(Protocol):
    def delenv(self, name: str, raising: bool = True) -> None: ...

    def setenv(self, name: str, value: str, prepend: str | None = None) -> None: ...


def _clear_manim_openai_compatible_env(monkeypatch: MonkeyPatchFixture) -> None:
    for name in (
        "MANIM_OPENAI_COMPATIBLE_MODEL",
        "MANIM_OPENAI_COMPATIBLE_API_KEY",
        "MANIM_OPENAI_COMPATIBLE_BASE_URL",
        "MANIM_9ROUTER_MODEL",
        "MANIM_9ROUTER_API_KEY",
        "MANIM_9ROUTER_BASE_URL",
        "AI_MODEL",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)


def test_openai_provider_passes_custom_base_url_without_logging_secret(monkeypatch: MonkeyPatchFixture) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = OpenAIProvider(model="model-a", api_key="secret-key", base_url="https://example.test/v1")

    with patch("app.services.ai_providers.openai_provider.OpenAI") as openai_cls:
        provider.get_client()  # pyright: ignore[reportUnknownMemberType]

    openai_cls.assert_called_once_with(api_key="secret-key", base_url="https://example.test/v1")


def test_load_9router_config_uses_fake_file_and_env_secret(tmp_path: Path, monkeypatch: MonkeyPatchFixture) -> None:
    _clear_manim_openai_compatible_env(monkeypatch)
    monkeypatch.setenv("NINE_ROUTER_KEY", "resolved-secret")
    config_path = tmp_path / "opencode.json"
    _ = config_path.write_text(
        json.dumps(
            {
                "provider": {
                    "9router": {
                        "base_url": "https://nine-router.test/v1",
                        "api_key": "{env:NINE_ROUTER_KEY}",
                    }
                }
            }
        )
    )

    cfg = load_9router_opencode_config(config_path)

    assert cfg.provider == "9router"
    assert cfg.model == "cx/gpt-5.5-xhigh"
    assert cfg.base_url == "https://nine-router.test/v1"
    assert cfg.api_key == "resolved-secret"


def test_manim_openai_compatible_general_env_fallback_when_specific_and_opencode_absent(
    tmp_path: Path, monkeypatch: MonkeyPatchFixture
) -> None:
    _clear_manim_openai_compatible_env(monkeypatch)
    monkeypatch.setenv("AI_MODEL", "general-model")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://general.test/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "general-key")

    cfg = load_manim_openai_compatible_config(tmp_path / "missing-opencode.json")

    assert cfg.provider == "openai-compatible"
    assert cfg.model == "general-model"
    assert cfg.base_url == "https://general.test/v1"
    assert cfg.api_key == "general-key"


def test_manim_openai_compatible_canonical_env_overrides_legacy_env(monkeypatch: MonkeyPatchFixture) -> None:
    _clear_manim_openai_compatible_env(monkeypatch)
    monkeypatch.setenv("MANIM_OPENAI_COMPATIBLE_MODEL", "canonical-model")
    monkeypatch.setenv("MANIM_OPENAI_COMPATIBLE_BASE_URL", "https://canonical.test/v1")
    monkeypatch.setenv("MANIM_OPENAI_COMPATIBLE_API_KEY", "canonical-key")
    monkeypatch.setenv("MANIM_9ROUTER_MODEL", "legacy-model")
    monkeypatch.setenv("MANIM_9ROUTER_BASE_URL", "https://legacy.test/v1")
    monkeypatch.setenv("MANIM_9ROUTER_API_KEY", "legacy-key")
    monkeypatch.setenv("AI_MODEL", "general-model")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://general.test/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "general-key")

    cfg = load_manim_openai_compatible_config()

    assert cfg.provider == "openai-compatible"
    assert cfg.model == "canonical-model"
    assert cfg.base_url == "https://canonical.test/v1"
    assert cfg.api_key == "canonical-key"


def test_manim_openai_compatible_legacy_env_still_works(monkeypatch: MonkeyPatchFixture) -> None:
    _clear_manim_openai_compatible_env(monkeypatch)
    monkeypatch.setenv("MANIM_9ROUTER_MODEL", "legacy-model")
    monkeypatch.setenv("MANIM_9ROUTER_BASE_URL", "https://legacy.test/v1")
    monkeypatch.setenv("MANIM_9ROUTER_API_KEY", "legacy-key")
    monkeypatch.setenv("AI_MODEL", "general-model")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://general.test/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "general-key")

    cfg = load_manim_openai_compatible_config()

    assert cfg.model == "legacy-model"
    assert cfg.base_url == "https://legacy.test/v1"
    assert cfg.api_key == "legacy-key"


def test_manim_openai_compatible_opencode_9router_fallback_still_works(
    tmp_path: Path, monkeypatch: MonkeyPatchFixture
) -> None:
    _clear_manim_openai_compatible_env(monkeypatch)
    monkeypatch.setenv("NINE_ROUTER_KEY", "resolved-secret")
    monkeypatch.setenv("AI_MODEL", "general-model")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://general.test/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "general-key")
    config_path = tmp_path / "opencode.json"
    _ = config_path.write_text(
        json.dumps(
            {
                "provider": {
                    "9router": {
                        "base_url": "https://nine-router.test/v1",
                        "api_key": "$NINE_ROUTER_KEY",
                    }
                }
            }
        )
    )

    cfg = load_manim_openai_compatible_config(config_path)

    assert cfg.provider == "openai-compatible"
    assert cfg.model == "general-model"
    assert cfg.base_url == "https://nine-router.test/v1"
    assert cfg.api_key == "resolved-secret"


def test_factory_builds_9router_provider_from_safe_loader() -> None:
    clear_providers()
    fake_cfg = MagicMock(model="cx/gpt-5.5-xhigh", api_key="fake", base_url="https://router.test/v1")

    with patch("app.services.ai_providers.ai_provider_factory.load_manim_openai_compatible_config", return_value=fake_cfg):
        provider = get_provider("9router")

    assert isinstance(provider, OpenAIProvider)
    assert provider.model == "cx/gpt-5.5-xhigh"
    assert provider.base_url == "https://router.test/v1"
    assert provider.temperature == 0.1
    assert provider.raise_errors is True
    clear_providers()


def test_factory_builds_canonical_manim_openai_compatible_provider() -> None:
    clear_providers()
    fake_cfg = MagicMock(model="canonical-model", api_key="fake", base_url="https://router.test/v1")

    with patch("app.services.ai_providers.ai_provider_factory.load_manim_openai_compatible_config", return_value=fake_cfg):
        provider = get_provider("openai-compatible")

    assert isinstance(provider, OpenAIProvider)
    assert provider.model == "canonical-model"
    assert provider.base_url == "https://router.test/v1"
    assert provider.temperature == 0.1
    assert provider.raise_errors is True
    clear_providers()


def test_factory_9router_and_canonical_keys_share_cached_openai_provider() -> None:
    clear_providers()
    fake_cfg = MagicMock(model="canonical-model", api_key="fake", base_url="https://router.test/v1")

    with patch("app.services.ai_providers.ai_provider_factory.load_manim_openai_compatible_config", return_value=fake_cfg):
        legacy_provider = get_provider("9router")
        canonical_provider = get_provider("manim-openai-compatible")

    assert legacy_provider is canonical_provider
    assert isinstance(legacy_provider, OpenAIProvider)
    clear_providers()
