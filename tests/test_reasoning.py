"""
Tests for ReasoningService and ReasoningController.
All AI providers are mocked — no real API keys needed.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


def test_reasoning_service_instantiation():
    """ReasoningService can be instantiated with default config."""
    with patch("app.services.reasoning_service.get_reasoning_provider") as mock_get:
        mock_get.return_value = MagicMock()
        from app.services.reasoning_service import ReasoningService

        service = ReasoningService()
        assert service is not None
        assert service.use_perplexity is False
        assert service.search_provider is None


def test_reasoning_controller_cached_reasoning_empty(db_session):
    """get_cached_reasoning returns exists=False when no reasoning cached."""
    from app.controllers.reasoning_controller import ReasoningController

    controller = ReasoningController(db_session)
    result = controller.get_cached_reasoning(999)
    assert result["exists"] is False
    assert result["data"] is None


def test_fix_mermaid_code_mocked():
    """fix_mermaid_code returns fixed code via provider."""
    from app.services.reasoning_service import fix_mermaid_code

    with patch("app.services.reasoning_service.get_provider"):
        # fix_mermaid_code imports get_provider from ai_providers inside the function
        pass

    # The function uses a local import: from app.services.ai_providers import get_provider
    with patch("app.services.ai_providers.get_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.generate_reasoning = AsyncMock(return_value="graph TD\n    A-->B")
        mock_get.return_value = mock_provider
        result = asyncio.get_event_loop().run_until_complete(
            fix_mermaid_code("graph TD A-->B", "Parse error")
        )
        assert "A-->B" in result
