# Solution Prompts
# Prompt templates for AI-powered solution generation for programming problems.
# Centralizes solution prompt logic previously inline in solution_generator.py.


def get_solution_system_prompt() -> str:
    """Get the system prompt for solution generation.

    Returns:
        System prompt string that configures the LLM as an expert Python programmer.
    """
    return """You are an expert Python programmer and educator who writes clean, idiomatic, production-quality solutions.

Requirements:
1. Write ONLY the Python code — no explanations, no markdown fences
2. Use the exact function signature provided in the starter code
3. Ensure the solution passes all given test cases
4. Follow PEP 8, use meaningful variable names, include type hints where helpful
5. Keep code clean, readable, and efficient

Do NOT include unnecessary comments.
Do NOT over-engineer — use the simplest approach that works.
NEVER use global variables.
Do NOT import libraries unless absolutely necessary.

FEW-SHOT EXAMPLE (good output):
def add(a: int, b: int) -> int:
    return a + b

TOKEN BUDGET: Focus on clean, minimal code — no commentary.
Output ONLY the Python function. No explanation, no markdown."""


def get_solution_prompt(
    problem_title: str,
    problem_desc: str,
    starter_code: str,
    examples: list[dict[str, str]],
    test_info: str,
) -> str:
    """Generate the user prompt for solution generation.

    Constructs a structured prompt with the problem context, starter code,
    examples, and test case information for the LLM to produce a working solution.

    Args:
        problem_title: Title of the programming problem.
        problem_desc: Full description of the problem.
        starter_code: The function signature and starter code to build upon.
        examples: List of example dicts, each with 'input', 'output', and
            optionally 'reasoning' keys.
        test_info: Formatted string describing test cases the solution must pass.

    Returns:
        Formatted prompt string for solution generation.
    """
    examples_text = ""
    if examples:
        for i, ex in enumerate(examples, 1):
            examples_text += f"\nExample {i}:\n"
            examples_text += f"  Input: {ex.get('input', '')}\n"
            examples_text += f"  Output: {ex.get('output', '')}\n"
            if ex.get("reasoning"):
                examples_text += f"  Reasoning: {ex['reasoning']}\n"
    else:
        examples_text = "\n(No examples provided)\n"

    return f"""## Problem
Title: {problem_title}
Description: {problem_desc}

## Starter Code
```python
{starter_code}
```

## Examples
{examples_text}
## Test Cases
{test_info}

## Expected Output Format
Return ONLY the complete Python function. For example:
```
def solution(arg1, arg2):
    # implementation
    return result
```

Do NOT wrap the code in markdown code fences.
Do NOT include import statements unless the problem requires a specific library.
NEVER add a main block or test code.

TOKEN BUDGET: Output only the function body — no extra text.
REMEMBER: Output ONLY the Python function. No markdown, no explanation.
Generate a complete, working solution:"""
