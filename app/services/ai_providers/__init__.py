"""
AI Providers Package - SOLID architecture for AI providers.

Available Providers:
- OpenAIProvider: OpenAI API
- PerplexityProvider: Perplexity AI (search + reasoning)

Usage:
    from app.services.ai_providers import get_provider, get_search_provider

    # Get default provider (defaults to OpenAI)
    provider = get_provider()
    hint = await provider.generate_hint(problem, code, error)

    # Get specific provider
    perplexity = get_provider("perplexity")
    result = await perplexity.search("Naive Bayes")

    # Get reasoning provider with Perplexity preference
    provider = get_reasoning_provider(use_perplexity=True)
"""

from .ai_provider_base import AIProvider, SearchProvider
from .ai_provider_factory import (
    get_provider,
    get_search_provider,
    get_reasoning_provider,
    clear_providers,
)
from .openai_provider import OpenAIProvider
from .perplexity_provider import PerplexityProvider

__all__ = [
    # Base classes
    "AIProvider",
    "SearchProvider",
    # Factory functions
    "get_provider",
    "get_search_provider",
    "get_reasoning_provider",
    "clear_providers",
    # Provider implementations
    "OpenAIProvider",
    "PerplexityProvider",
]
