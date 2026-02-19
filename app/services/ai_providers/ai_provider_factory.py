"""
AI Provider Factory - Creates and manages AI providers.

Follows Factory Pattern for provider instantiation.
Supports dependency injection for testing.
"""

import os
from typing import Optional

from .ai_provider_base import AIProvider, SearchProvider
from .openai_provider import OpenAIProvider
from .perplexity_provider import PerplexityProvider


# Singleton instances
_providers: dict[str, AIProvider] = {}


def get_provider(provider_type: Optional[str] = None) -> AIProvider:
    """
    Get an AI provider instance.

    Args:
        provider_type: "openai" or "perplexity". If None, defaults to "openai"

    Returns:
        AIProvider instance
    """
    if provider_type is None:
        provider_type = "openai"

    # Return cached instance if available
    if provider_type in _providers:
        return _providers[provider_type]

    # Create new provider
    if provider_type == "openai":
        provider = OpenAIProvider()
    elif provider_type == "perplexity":
        provider = PerplexityProvider()
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")

    _providers[provider_type] = provider
    return provider


def get_search_provider() -> Optional[SearchProvider]:
    """
    Get a search provider instance.

    Currently only Perplexity supports search.

    Returns:
        SearchProvider instance or None if not available
    """
    provider = get_provider("perplexity")
    if isinstance(provider, SearchProvider) and provider.is_configured():
        return provider
    return None


def get_reasoning_provider(use_perplexity: bool = False) -> AIProvider:
    """
    Get the appropriate provider for reasoning generation.

    Priority: REASONING_PROVIDER env var > use_perplexity param > default (openai)

    Env vars:
        REASONING_PROVIDER: "openai" or "perplexity" (overrides use_perplexity param)
        REASONING_MODEL: Model name for reasoning (only used when provider is openai)
    """
    # Env var takes priority over function parameter
    env_provider = os.getenv("REASONING_PROVIDER", "").lower()

    if env_provider == "perplexity" or (not env_provider and use_perplexity):
        perplexity = get_provider("perplexity")
        if perplexity.is_configured():
            return perplexity
        print("[Provider] Perplexity not configured, falling back to OpenAI")

    # Check for custom reasoning model
    reasoning_model = os.getenv("REASONING_MODEL")
    if reasoning_model:
        # Create/cache a separate OpenAI instance with the reasoning model
        cache_key = f"openai-reasoning-{reasoning_model}"
        if cache_key not in _providers:
            _providers[cache_key] = OpenAIProvider(model=reasoning_model)
        return _providers[cache_key]

    return get_provider()


def clear_providers():
    """Clear cached provider instances (useful for testing)."""
    global _providers
    _providers = {}
