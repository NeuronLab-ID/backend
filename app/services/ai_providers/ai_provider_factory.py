"""
AI Provider Factory - Creates and manages AI providers.

Follows Factory Pattern for provider instantiation.
Supports dependency injection for testing.
"""

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

    Args:
        use_perplexity: If True, prefer Perplexity provider

    Returns:
        AIProvider instance for reasoning
    """
    if use_perplexity:
        perplexity = get_provider("perplexity")
        if perplexity.is_configured():
            return perplexity
        print("[Provider] Perplexity not configured, falling back to default")

    return get_provider()


def clear_providers():
    """Clear cached provider instances (useful for testing)."""
    global _providers
    _providers = {}
