"""
AI Providers Package - SOLID architecture for AI providers.

Available Providers:
- CopilotProvider: GitHub Copilot CLI
- OpenAIProvider: OpenAI API / GitHub Models
- PerplexityProvider: Perplexity AI (search + reasoning)

Usage:
    from app.services.ai_providers import get_provider, get_search_provider
    
    # Get default provider (based on AI_BACKEND env var)
    provider = get_provider()
    hint = await provider.generate_hint(problem, code, error)
    
    # Get specific provider
    perplexity = get_provider("perplexity")
    result = await perplexity.search("Naive Bayes")
    
    # Get reasoning provider with Perplexity preference
    provider = get_reasoning_provider(use_perplexity=True)
"""

from .ai_provider_base import AIProvider, SearchProvider
from .ai_provider_factory import get_provider, get_search_provider, get_reasoning_provider, clear_providers
from .copilot_provider import CopilotProvider
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
    "CopilotProvider",
    "OpenAIProvider",
    "PerplexityProvider",
]
