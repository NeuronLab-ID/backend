"""
AI-powered solution generator using the AI Provider pattern.
"""

from typing import Optional

from loguru import logger

from app.prompts import get_solution_prompt, get_solution_system_prompt
from app.services.ai_providers import get_provider


async def generate_solution(problem: dict) -> Optional[str]:
    """
    Generate a reference solution for the problem.

    Returns Python code as a string.
    """
    try:
        provider = get_provider()

        # Build context
        problem_title = problem.get("title", "Unknown Problem")
        problem_desc = problem.get(
            "description_decoded", problem.get("description", "")
        )
        starter_code = problem.get("starter_code", "")
        example = problem.get("example", {})
        test_cases = problem.get("test_cases", [])

        # Build test case info
        test_info = ""
        if test_cases:
            test_info = "\n".join(
                [
                    f"- Input: {tc.get('test', '')} => Expected: {tc.get('expected_output', '')}"
                    for tc in test_cases[:3]
                ]
            )

        system_prompt = get_solution_system_prompt()

        examples = [example] if example else []
        prompt = get_solution_prompt(
            problem_title, problem_desc, starter_code, examples, test_info
        )

        solution = await provider.generate_reasoning(
            prompt=prompt, system_prompt=system_prompt
        )

        # Clean up the response (remove markdown code blocks if present)
        if solution:
            solution = solution.strip()
            if solution.startswith("```python"):
                solution = solution[9:]
            elif solution.startswith("```"):
                solution = solution[3:]
            if solution.endswith("```"):
                solution = solution[:-3]
            return solution.strip()

        return None

    except Exception as e:
        logger.error(f"[Solution Generator] Error: {e}")
        return None
