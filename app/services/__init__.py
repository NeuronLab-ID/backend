# Services package
"""
Backend Services - Core business logic.

AI Providers:
    from app.services.ai_providers import get_provider, PerplexityProvider
    
    # Or shorthand:
    from app.services import get_provider, get_search_provider
"""

# Re-export AI providers for convenience
from .ai_providers import (
    AIProvider,
    SearchProvider,
    get_provider,
    get_search_provider,
    get_reasoning_provider,
    CopilotProvider,
    OpenAIProvider,
    PerplexityProvider,
)

__all__ = [
    # AI Providers
    "AIProvider",
    "SearchProvider",
    "get_provider",
    "get_search_provider",
    "get_reasoning_provider",
    "CopilotProvider",
    "OpenAIProvider",
    "PerplexityProvider",
]
