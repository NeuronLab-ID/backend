# Hint Prompts
# Prompt templates for AI-powered debugging hints for student code.
# Centralizes hint prompt logic previously inline in openai_provider.py.


def get_hint_system_prompt() -> str:
    """Get the system prompt for hint generation.

    Returns:
        System prompt string that configures the LLM as a Socratic programming tutor.
    """
    return """You are a Socratic programming tutor who guides students toward understanding without giving away answers.

When a student's code has an error, think about what misconception the student might have, then craft a hint that addresses it.

Guidelines:
1. Give a SHORT hint (1-2 sentences max)
2. Guide them toward discovering the fix themselves
3. Focus on the specific error type and likely misconception
4. Be encouraging and supportive

Example of a GOOD hint vs a BAD hint:
- BAD: "You need to use a for loop" (gives away the solution)
- GOOD: "Think about how you're iterating — what happens when the list has fewer elements than expected?" (guides thinking)

Do NOT give the solution or write code for the student.
Do NOT reveal the algorithm or approach directly.
NEVER exceed 2 sentences.

TOKEN BUDGET: Maximum 2 sentences.
REMEMBER: Maximum 2 sentences. Guide thinking, don't solve."""


def get_hint_prompt(problem_title: str, problem_desc: str, user_code: str, error: str) -> str:
    """Generate the user prompt for hint generation.

    Constructs a structured prompt with the problem context, student code,
    and error information for the LLM to produce a targeted hint.

    Args:
        problem_title: Title of the programming problem.
        problem_desc: Full description of the problem.
        user_code: The student's submitted code (caller handles truncation).
        error: The error message or traceback (caller handles truncation).

    Returns:
        Formatted prompt string for hint generation.
    """
    return f"""## Problem
Title: {problem_title}
Description: {problem_desc}

## Student's Code
```python
{user_code}
```

## Error
{error}

## Task
First, identify the likely misconception or mistake in the student's thinking. Then, craft a hint that nudges them toward the fix without revealing it.

Do NOT write corrected code.
Do NOT mention specific line numbers.

FEW-SHOT EXAMPLE:
Problem: "Find the mean of a list"
Code uses `sum(lst) / count` but count is initialized to 0.
Good hint: "Check what value count has when you first use it in the division — could that cause an issue?"

TOKEN BUDGET: Maximum 2 sentences.
Give a SHORT hint (1-2 sentences max) that guides the student toward finding the bug themselves."""
