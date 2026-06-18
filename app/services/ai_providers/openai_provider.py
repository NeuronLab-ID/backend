"""
OpenAI Provider - OpenAI API integration.
"""

import os
from typing import Optional

from loguru import logger
from openai import OpenAI

from app.prompts import get_hint_prompt, get_hint_system_prompt

from .ai_provider_base import AIProvider


class OpenAIProvider(AIProvider):
    """OpenAI-compatible provider for AI generation."""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.3,
        raise_errors: bool = False,
    ):
        """
        Initialize OpenAI-compatible provider.

        Args:
            model: Model name (default from env or gpt-4o-mini)
            api_key: Explicit API key. Falls back to OPENAI_API_KEY.
            base_url: Optional OpenAI-compatible endpoint base URL.
        """
        self.model = model or os.getenv("AI_MODEL", "gpt-4o-mini")
        self.api_key = api_key
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL") or None
        self.temperature = temperature
        self.raise_errors = raise_errors
        self._client: Optional[OpenAI] = None

    @property
    def name(self) -> str:
        return "OpenAI"

    def is_configured(self) -> bool:
        """Check if provider is properly configured."""
        return bool(self.api_key or os.getenv("OPENAI_API_KEY"))

    def get_client(self) -> OpenAI:
        """Get or create OpenAI client."""
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def _create_client(self) -> OpenAI:
        """Create OpenAI client."""
        api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in .env")
        if self.base_url:
            return OpenAI(api_key=api_key, base_url=self.base_url)
        return OpenAI(api_key=api_key)

    async def generate_hint(
        self, problem: dict[str, object], user_code: str, error: str
    ) -> Optional[str]:
        """Generate hint using OpenAI API."""
        try:
            import asyncio

            client = self.get_client()
            problem_title = str(problem.get("title", "Unknown Problem"))
            description_value = problem.get("description_decoded", problem.get("description", ""))
            problem_desc = str(description_value)[:500]

            logger.debug(f"[OpenAI] Generating hint for: {problem_title}")

            system_content = get_hint_system_prompt()
            user_content = get_hint_prompt(
                problem_title, problem_desc, user_code[:1000], error[:500]
            )

            def _blocking_call():
                return client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_content},
                        {"role": "user", "content": user_content},
                    ],
                    max_tokens=200,
                    temperature=0.7,
                )

            response = await asyncio.to_thread(_blocking_call)
            hint = response.choices[0].message.content
            logger.success("[OpenAI] Generated hint")
            return hint.strip() if hint else None

        except Exception as e:
            logger.error(f"[OpenAI] Error: {e}")
            if self.raise_errors:
                raise
            return None

    async def generate_reasoning(
        self, prompt: str, system_prompt: str = ""
    ) -> Optional[str]:
        """Generate reasoning using OpenAI API."""
        try:
            import asyncio

            client = self.get_client()

            logger.debug(f"[OpenAI] Generating reasoning with {self.model}")

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            def _blocking_call():
                return client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=4000,
                    temperature=self.temperature,
                )

            response = await asyncio.to_thread(_blocking_call)
            result = response.choices[0].message.content or ""
            logger.success(f"[OpenAI] Generated {len(result)} chars")
            return result

        except Exception as e:
            logger.error(f"[OpenAI] Error: {e}")
            if self.raise_errors:
                raise
            return None
