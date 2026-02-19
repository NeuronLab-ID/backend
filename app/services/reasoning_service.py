# Reasoning Service
# Handles AI-powered reasoning generation for quests

import json
import asyncio
from typing import AsyncIterator

from app.services import get_provider, get_search_provider, get_reasoning_provider
from app.prompts import (
    get_step_reasoning_prompt,
    get_step_system_prompt,
    get_summary_prompt,
    get_summary_system_prompt,
    get_mermaid_fix_prompt,
    get_mermaid_fix_system_prompt,
    get_test_case_reasoning_prompt,
    get_test_case_reasoning_system_prompt,
)


class ReasoningService:
    """Service for generating AI reasoning for quest steps."""

    def __init__(
        self, use_perplexity: bool = False, use_perplexity_reasoning: bool = False
    ):
        """
        Initialize the reasoning service.

        Args:
            use_perplexity: Use Perplexity for web search references
            use_perplexity_reasoning: Use Perplexity with Claude 4.5 Sonnet for reasoning
        """
        self.use_perplexity = use_perplexity
        self.use_perplexity_reasoning = use_perplexity_reasoning
        self.reasoning_provider = get_reasoning_provider(
            use_perplexity=use_perplexity_reasoning
        )
        self.search_provider = get_search_provider() if use_perplexity else None

    async def generate_step_reasoning(
        self,
        step: int,
        total_steps: int,
        title: str,
        relation: str,
        definition: str,
        key_formulas: list,
        function_signature: str,
        example_input: str,
        example_output: str,
        previous_context: str = "",
        web_references: str = "",
    ) -> str:
        """Generate reasoning for a single step."""
        formulas_text = "\n".join(
            [
                f"- {f.get('name', '')}: {f.get('latex', '')} ({f.get('description', '')})"
                for f in key_formulas
            ]
        )

        prompt = get_step_reasoning_prompt(
            step=step,
            total_steps=total_steps,
            title=title,
            relation=relation,
            definition=definition,
            formulas_text=formulas_text,
            function_signature=function_signature,
            example_input=example_input,
            example_output=example_output,
            previous_context=previous_context,
            web_references=web_references,
        )

        system_prompt = get_step_system_prompt(step, total_steps)

        reasoning = await self.reasoning_provider.generate_reasoning(
            prompt, system_prompt
        )
        return (
            reasoning if reasoning else f"[Error generating reasoning for step {step}]"
        )

    async def generate_summary(self, all_steps: list) -> str:
        """Generate a summary connecting all steps."""
        steps_summary = "\n".join(
            [
                f"Step {s['step']}: {s['title']} - {s['reasoning'][:100]}..."
                for s in all_steps
            ]
        )

        prompt = get_summary_prompt(steps_summary)
        system_prompt = get_summary_system_prompt()

        summary = await self.reasoning_provider.generate_reasoning(
            prompt, system_prompt
        )
        return summary if summary else "[Error generating summary]"

    async def search_web_references(
        self, quest_data: dict, sub_quests: list
    ) -> tuple[str, str]:
        """
        Perform a single web search covering all steps.

        Returns:
            Tuple of (raw_search_result, formatted_web_references)
        """
        if not self.search_provider:
            return "", ""

        all_titles = [sq.get("title", f"Step {sq.get('step', 0)}") for sq in sub_quests]
        all_relations = [
            sq.get("relation_to_problem", "")
            for sq in sub_quests
            if sq.get("relation_to_problem")
        ]
        main_topic = (
            quest_data.get("title", "")
            or quest_data.get("problem_title", "")
            or all_titles[0]
        )

        search_topic = f"{main_topic}: {', '.join(all_titles[:3])}"
        search_context = f"""This is a multi-step problem covering:
{chr(10).join([f"- Step {i + 1}: {t}" for i, t in enumerate(all_titles)])}

Main concepts: {", ".join(list(set(all_relations))[:3]) if all_relations else main_topic}"""

        search_result = await self.search_provider.search(search_topic, search_context)

        if search_result:
            web_references = f"""
### 📚 Web References (from Perplexity) - USE THIS DATA FOR ALL STEPS:
{search_result}

**IMPORTANT**: Use the SAME real-world example dataset above for ALL steps below.
Each step should build on the previous step's results using this consistent dataset.
"""
            return search_result, web_references

        return "", ""

    async def stream_full_reasoning(
        self, quest_data: dict, sub_quests: list
    ) -> AsyncIterator[dict]:
        """
        Stream reasoning generation for all quest steps.

        Yields SSE-formatted events with types: search, search_result, search_complete, step, summary, done, error
        """
        all_steps = []
        previous_context = ""

        # Step 0: Web search
        web_references = ""
        if self.search_provider:
            all_titles = [
                sq.get("title", f"Step {sq.get('step', 0)}") for sq in sub_quests
            ]
            main_topic = (
                quest_data.get("title", "")
                or quest_data.get("problem_title", "")
                or all_titles[0]
            )
            search_topic = f"{main_topic}: {', '.join(all_titles[:3])}"

            yield {
                "type": "search",
                "data": {"step": 0, "topic": f"Searching: {search_topic[:50]}..."},
            }

            search_result, web_references = await self.search_web_references(
                quest_data, sub_quests
            )

            if search_result:
                yield {"type": "search_result", "data": {"content": search_result}}
                yield {"type": "search_complete", "data": {"chars": len(search_result)}}

        # Steps 1-N: Generate reasoning
        for sq in sub_quests:
            step = sq.get("step", 0)
            title = sq.get("title", f"Step {step}")
            relation = sq.get("relation_to_problem", "")
            math_content = sq.get("math_content", {})
            key_formulas = sq.get("key_formulas", [])
            exercise = sq.get("exercise", {})
            test_cases = exercise.get("test_cases", [])
            function_signature = exercise.get("function_signature", "")

            example_input = test_cases[0].get("input", "") if test_cases else ""
            example_output = test_cases[0].get("expected", "") if test_cases else ""

            reasoning = await self.generate_step_reasoning(
                step=step,
                total_steps=len(sub_quests),
                title=title,
                relation=relation,
                definition=math_content.get("definition", ""),
                key_formulas=key_formulas,
                function_signature=function_signature,
                example_input=example_input,
                example_output=example_output,
                previous_context=previous_context,
                web_references=web_references,
            )

            step_data = {"step": step, "title": title, "reasoning": reasoning}
            all_steps.append(step_data)

            # Build context for next step
            previous_context += f"""
**Step {step} - {title}**:
- Function: `{function_signature}`
- Input: `{example_input}`
- Output: `{example_output}`
- Key concept: {relation[:100] if relation else title}
"""

            yield {"type": "step", "data": step_data}

        # Generate final summary
        summary = await self.generate_summary(all_steps)
        yield {"type": "summary", "data": summary}

        # Return complete data for storage
        yield {
            "type": "complete",
            "data": {
                "steps": all_steps,
                "summary": summary,
                "web_references": web_references,
            },
        }

        yield {"type": "done", "cached": False}


async def fix_mermaid_code(code: str, error: str) -> str:
    """Use AI to fix invalid Mermaid diagram code."""
    from app.services.ai_providers import get_provider

    try:
        provider = get_provider()

        fixed_code = await provider.generate_reasoning(
            prompt=get_mermaid_fix_prompt(code, error),
            system_prompt=get_mermaid_fix_system_prompt(),
        )

        if not fixed_code:
            return code

        # Clean up markdown wrappers
        fixed_code = fixed_code.strip()
        if fixed_code.startswith("```"):
            lines = fixed_code.split("\n")
            fixed_code = "\n".join(
                lines[1:-1] if lines[-1].startswith("```") else lines[1:]
            )

        return fixed_code

    except Exception:
        return code


async def generate_test_case_reasoning(
    function_signature: str, test_input: str, expected_output: str
) -> dict:
    """Generate step-by-step reasoning for a test case."""
    from app.services.ai_providers import get_provider

    try:
        provider = get_provider()

        content = await provider.generate_reasoning(
            prompt=get_test_case_reasoning_prompt(
                function_signature, test_input, expected_output
            ),
            system_prompt=get_test_case_reasoning_system_prompt(),
        )

        content = content or ""

        # Parse response into sections
        input_section = ""
        process_section = ""
        output_section = ""

        lines = content.strip().split("\n")
        current_section = None

        for line in lines:
            line_upper = line.upper()
            if line_upper.startswith("INPUT:"):
                current_section = "input"
                input_section = line[6:].strip()
            elif line_upper.startswith("PROCESS:"):
                current_section = "process"
                process_section = line[8:].strip()
            elif line_upper.startswith("OUTPUT:"):
                current_section = "output"
                output_section = line[7:].strip()
            elif current_section:
                if current_section == "input":
                    input_section += " " + line.strip()
                elif current_section == "process":
                    process_section += " " + line.strip()
                elif current_section == "output":
                    output_section += " " + line.strip()

        return {
            "input": input_section.strip() or f"Input: {test_input}",
            "process": process_section.strip()
            or "Processing the input to compute the result.",
            "output": output_section.strip() or f"Expected output: {expected_output}",
        }

    except Exception as e:
        return {
            "input": f"Input: {test_input}",
            "process": f"Error generating reasoning: {str(e)}",
            "output": f"Expected output: {expected_output}",
        }
