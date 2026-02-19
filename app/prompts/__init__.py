# Prompts package
from app.prompts.reasoning_prompts import (
    get_step_reasoning_prompt,
    get_step_system_prompt,
    get_summary_prompt,
    get_summary_system_prompt,
    get_mermaid_fix_prompt,
    get_mermaid_fix_system_prompt,
    get_test_case_reasoning_prompt,
    get_test_case_reasoning_system_prompt,
    get_latex_export_prompt,
    get_latex_export_system_prompt,
    get_markdown_export_prompt,
    get_markdown_export_system_prompt,
)
from app.prompts.math_prompts import (
    get_sample_prompt,
    get_retry_prompt,
    get_system_prompt as get_math_system_prompt,
    get_retry_system_prompt as get_math_retry_system_prompt,
    DIFFICULTY_CONFIG,
)
from app.prompts.hint_prompts import (
    get_hint_system_prompt,
    get_hint_prompt,
)
from app.prompts.solution_prompts import (
    get_solution_system_prompt,
    get_solution_prompt,
)
from app.prompts.provider_prompts import (
    get_perplexity_reasoning_augmentation,
    get_perplexity_hint_system_prompt,
    get_perplexity_hint_prompt,
)

__all__ = [
    # Reasoning prompts
    "get_step_reasoning_prompt",
    "get_step_system_prompt",
    "get_summary_prompt",
    "get_summary_system_prompt",
    "get_mermaid_fix_prompt",
    "get_mermaid_fix_system_prompt",
    "get_test_case_reasoning_prompt",
    "get_test_case_reasoning_system_prompt",
    "get_latex_export_prompt",
    "get_latex_export_system_prompt",
    "get_markdown_export_prompt",
    "get_markdown_export_system_prompt",
    # Math prompts
    "get_sample_prompt",
    "get_retry_prompt",
    "get_math_system_prompt",
    "get_math_retry_system_prompt",
    "DIFFICULTY_CONFIG",
    # Hint prompts
    "get_hint_system_prompt",
    "get_hint_prompt",
    # Solution prompts
    "get_solution_system_prompt",
    "get_solution_prompt",
    # Provider prompts
    "get_perplexity_reasoning_augmentation",
    "get_perplexity_hint_system_prompt",
    "get_perplexity_hint_prompt",
]
