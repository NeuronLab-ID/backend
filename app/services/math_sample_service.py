# Math Sample Service
# Handles AI-powered math sample generation

from loguru import logger

from app.prompts.math_prompts import (
    get_retry_prompt,
    get_retry_system_prompt,
    get_sample_prompt,
    get_system_prompt,
)
from app.services.ai_providers import get_provider
from app.utils.json_utils import clean_ai_response, try_parse_json


class MathSampleService:
    """Service for generating worked math examples using AI."""

    def __init__(self):
        self.provider = get_provider()

    async def generate_sample(
        self, formula_name: str, formula_latex: str, difficulty: str = "easy"
    ) -> dict:
        """Generate a worked math example.

        Args:
            formula_name: Name of the formula
            formula_latex: LaTeX representation
            difficulty: easy, medium, or hard

        Returns:
            Dict with success status, steps, and result
        """
        try:
            prompt = get_sample_prompt(formula_name, formula_latex, difficulty)

            content = await self.provider.generate_reasoning(
                prompt=prompt, system_prompt=get_system_prompt()
            )

            if content:
                content = clean_ai_response(content)
                data = try_parse_json(content)

                if data:
                    return {
                        "success": True,
                        "steps": data.get("steps", []),
                        "result": data.get("result", ""),
                    }

            # Retry with simpler prompt
            return await self._retry_generation(formula_name, formula_latex)

        except Exception as e:
            logger.error(f"[Math Sample] Error: {e}")
            return {"success": False, "error": str(e), "steps": [], "result": ""}

    async def _retry_generation(self, formula_name: str, formula_latex: str) -> dict:
        """Retry generation with a simpler prompt.

        Args:
            formula_name: Name of the formula
            formula_latex: LaTeX representation

        Returns:
            Dict with success status, steps, and result
        """
        logger.info("[Math Sample] Retrying with simpler prompt...")

        try:
            retry_prompt = get_retry_prompt(formula_name, formula_latex)

            content = await self.provider.generate_reasoning(
                prompt=retry_prompt, system_prompt=get_retry_system_prompt()
            )

            if content:
                content = clean_ai_response(content)
                data = try_parse_json(content)

                if data:
                    return {
                        "success": True,
                        "steps": data.get("steps", []),
                        "result": data.get("result", ""),
                    }

            logger.warning(
                f"[Math Sample] Failed after retry: {(content or '')[:200]}..."
            )
            return {
                "success": False,
                "error": "Failed to parse AI response. Please try again.",
                "steps": [],
                "result": "",
            }

        except Exception as e:
            logger.error(f"[Math Sample] Retry error: {e}")
            return {"success": False, "error": str(e), "steps": [], "result": ""}
