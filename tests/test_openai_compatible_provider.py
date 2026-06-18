import json
from unittest.mock import MagicMock, patch

from app.services.ai_providers.ai_provider_factory import clear_providers, get_provider
from app.services.ai_providers.openai_provider import OpenAIProvider
from app.services.ai_providers.opencode_config import load_9router_opencode_config


def test_openai_provider_passes_custom_base_url_without_logging_secret(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = OpenAIProvider(model="model-a", api_key="secret-key", base_url="https://example.test/v1")

    with patch("app.services.ai_providers.openai_provider.OpenAI") as openai_cls:
        provider.get_client()

    openai_cls.assert_called_once_with(api_key="secret-key", base_url="https://example.test/v1")


def test_load_9router_config_uses_fake_file_and_env_secret(tmp_path, monkeypatch):
    monkeypatch.setenv("NINE_ROUTER_KEY", "resolved-secret")
    monkeypatch.delenv("MANIM_9ROUTER_API_KEY", raising=False)
    config_path = tmp_path / "opencode.json"
    config_path.write_text(
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


def test_factory_builds_9router_provider_from_safe_loader():
    clear_providers()
    fake_cfg = MagicMock(model="cx/gpt-5.5-xhigh", api_key="fake", base_url="https://router.test/v1")

    with patch("app.services.ai_providers.ai_provider_factory.load_9router_opencode_config", return_value=fake_cfg):
        provider = get_provider("9router")

    assert isinstance(provider, OpenAIProvider)
    assert provider.model == "cx/gpt-5.5-xhigh"
    assert provider.base_url == "https://router.test/v1"
    assert provider.temperature == 0.1
    assert provider.raise_errors is True
    clear_providers()
