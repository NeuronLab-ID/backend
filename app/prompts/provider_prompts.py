# Provider Prompts
# Prompt templates specific to individual AI providers (e.g., Perplexity).
# Centralizes provider-specific prompt logic previously inline in perplexity_provider.py.


def get_perplexity_reasoning_augmentation() -> str:
    """Get the reasoning augmentation suffix for Perplexity reasoning prompts.

    This text is appended to reasoning prompts when using Perplexity's
    reasoning model. It provides formatting guidance for mathematical
    and visual explanations.

    Returns:
        A text suffix string to append to reasoning prompts.
    """
    return """
Provide a detailed step-by-step mathematical explanation with:
1. Clear formulas using LaTeX ($...$ for inline, $$...$$ for display math)
2. A real-world example with actual data and concrete numbers
3. Step-by-step computation showing all intermediate values
4. Tables in markdown format when presenting structured data

Do NOT use images or external links in the explanation.
Do NOT skip intermediate computation steps — show every value.
NEVER mix LaTeX and plain text math in the same expression.

When using Mermaid diagrams, ensure valid syntax: use quoted labels for nodes containing special characters, and always terminate with a semicolon.

REMEMBER: Every formula must use LaTeX. Every step must show the numeric computation."""


def get_perplexity_hint_system_prompt() -> str:
    """Get the system prompt for Perplexity-based hint generation.

    Perplexity hints differ from OpenAI hints — they are generated via
    a search-augmented model and tend toward direct answers. This system
    prompt constrains the output to short, Socratic-style hints.

    Returns:
        System prompt string for Perplexity hint generation.
    """
    return """You are a concise programming tutor. When shown buggy code, give a brief Socratic hint that points the student in the right direction.

Rules:
1. Maximum 1-2 sentences
2. Focus on the specific error — do not explain general concepts
3. Guide the student to discover the fix, do not reveal it

Do NOT write corrected code or pseudocode.
Do NOT give away the solution or name the exact fix.
NEVER exceed 2 sentences.

REMEMBER: Be brief. One to two sentences only."""


def get_perplexity_hint_prompt(problem_title: str, user_code: str, error: str) -> str:
    """Generate the user prompt for Perplexity-based hint generation.

    Constructs a compact prompt for Perplexity's search-augmented model.
    Caller is responsible for truncating user_code and error to appropriate
    lengths (e.g., user_code[:500], error[:200]).

    Args:
        problem_title: Title of the programming problem.
        user_code: The student's submitted code (caller handles truncation).
        error: The error message or traceback (caller handles truncation).

    Returns:
        Formatted prompt string for Perplexity hint generation.
    """
    return f"""This Python code for "{problem_title}" has an error.

Code:
{user_code}

Error:
{error}

First, identify the root cause of the error. Then, give a hint that helps the student find it themselves.

Do NOT write the corrected code.
Do NOT name the exact function or method to use.

Give a SHORT hint (1-2 sentences) that guides the student toward the fix:"""
