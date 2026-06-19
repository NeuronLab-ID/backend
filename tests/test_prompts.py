"""Snapshot/structural tests for all prompt functions in app.prompts.

These tests verify the structural integrity of prompt outputs — return types,
non-emptiness, presence of negative constraints, structural markers, and
correct interpolation of input values. No LLM calls are made.
"""

import re

from app.prompts import (
    get_hint_prompt,
    get_hint_system_prompt,
    get_latex_export_prompt,
    get_latex_export_system_prompt,
    get_markdown_export_prompt,
    get_markdown_export_system_prompt,
    get_mermaid_fix_prompt,
    get_mermaid_fix_system_prompt,
    get_perplexity_hint_prompt,
    get_perplexity_hint_system_prompt,
    get_perplexity_reasoning_augmentation,
    get_solution_prompt,
    get_solution_system_prompt,
    get_step_reasoning_prompt,
    get_step_system_prompt,
    get_summary_prompt,
    get_summary_system_prompt,
    get_test_case_reasoning_prompt,
    get_test_case_reasoning_system_prompt,
)

# ---------------------------------------------------------------------------
# Shared test inputs
# ---------------------------------------------------------------------------

STEP_KWARGS = dict(
    step=1,
    total_steps=3,
    title="Calculate Dot Product",
    relation="Core linear algebra operation",
    definition="Sum of element-wise products",
    formulas_text="- Dot Product: $$\\mathbf{a} \\cdot \\mathbf{b}$$",
    function_signature="def dot_product(a, b):",
    example_input="[1,2,3], [4,5,6]",
    example_output="32",
)


def _has_negative_constraint(text: str) -> bool:
    """Return True if the text contains at least one negative constraint pattern."""
    return bool(re.search(r"Do NOT|NEVER", text))


# ===========================================================================
# TestStepReasoning
# ===========================================================================


class TestStepReasoning:
    """Tests for get_step_reasoning_prompt and get_step_system_prompt."""

    def test_step_reasoning_prompt_returns_str(self):
        result = get_step_reasoning_prompt(**STEP_KWARGS)
        assert isinstance(result, str)

    def test_step_reasoning_prompt_non_empty(self):
        result = get_step_reasoning_prompt(**STEP_KWARGS)
        assert len(result) > 0

    def test_step_reasoning_prompt_has_negative_constraint(self):
        result = get_step_reasoning_prompt(**STEP_KWARGS)
        assert _has_negative_constraint(result)

    def test_step_reasoning_prompt_contains_concept_overview(self):
        result = get_step_reasoning_prompt(**STEP_KWARGS)
        assert "Concept Overview" in result

    def test_step_reasoning_prompt_interpolates_title(self):
        result = get_step_reasoning_prompt(**STEP_KWARGS)
        assert "Calculate Dot Product" in result

    def test_step_reasoning_prompt_interpolates_step_number(self):
        result = get_step_reasoning_prompt(**STEP_KWARGS)
        assert "Step 1 of 3" in result

    def test_step_reasoning_prompt_with_previous_context(self):
        result = get_step_reasoning_prompt(
            **STEP_KWARGS,
            previous_context="Step 0: We defined vectors a and b",
        )
        assert "Step 0: We defined vectors a and b" in result
        assert "Previous Steps Summary" in result

    def test_step_reasoning_prompt_with_web_references(self):
        result = get_step_reasoning_prompt(
            **STEP_KWARGS,
            web_references="Khan Academy: Linear Algebra",
        )
        assert "Khan Academy: Linear Algebra" in result
        assert "Web References" in result

    def test_step_system_prompt_returns_str(self):
        result = get_step_system_prompt(step=1, total_steps=3)
        assert isinstance(result, str)

    def test_step_system_prompt_non_empty(self):
        result = get_step_system_prompt(step=1, total_steps=3)
        assert len(result) > 0

    def test_step_system_prompt_has_negative_constraint(self):
        result = get_step_system_prompt(step=1, total_steps=3)
        assert _has_negative_constraint(result)

    def test_step_system_prompt_mentions_mermaid(self):
        result = get_step_system_prompt(step=1, total_steps=3)
        assert "Mermaid" in result or "mermaid" in result


# ===========================================================================
# TestSummary
# ===========================================================================


class TestSummary:
    """Tests for get_summary_prompt and get_summary_system_prompt."""

    STEPS = (
        "Step 1: Entropy - Computed entropy values...\n"
        "Step 2: Gain - Calculated information gain..."
    )

    def test_summary_prompt_returns_str(self):
        result = get_summary_prompt(self.STEPS)
        assert isinstance(result, str)

    def test_summary_prompt_non_empty(self):
        result = get_summary_prompt(self.STEPS)
        assert len(result) > 0

    def test_summary_prompt_has_negative_constraint(self):
        result = get_summary_prompt(self.STEPS)
        assert _has_negative_constraint(result)

    def test_summary_prompt_contains_steps_text(self):
        result = get_summary_prompt(self.STEPS)
        assert "Entropy" in result
        assert "information gain" in result

    def test_summary_system_prompt_returns_str(self):
        result = get_summary_system_prompt()
        assert isinstance(result, str)

    def test_summary_system_prompt_non_empty(self):
        result = get_summary_system_prompt()
        assert len(result) > 0


# ===========================================================================
# TestMermaidFix
# ===========================================================================


class TestMermaidFix:
    """Tests for get_mermaid_fix_prompt and get_mermaid_fix_system_prompt."""

    CODE = "graph TD\n  A[Node ₁] --> B"
    ERROR = "Unicode not supported"

    def test_mermaid_fix_prompt_returns_str(self):
        result = get_mermaid_fix_prompt(self.CODE, self.ERROR)
        assert isinstance(result, str)

    def test_mermaid_fix_prompt_non_empty(self):
        result = get_mermaid_fix_prompt(self.CODE, self.ERROR)
        assert len(result) > 0

    def test_mermaid_fix_prompt_has_negative_constraint(self):
        result = get_mermaid_fix_prompt(self.CODE, self.ERROR)
        assert _has_negative_constraint(result)

    def test_mermaid_fix_prompt_contains_only_directive(self):
        result = get_mermaid_fix_prompt(self.CODE, self.ERROR)
        assert "ONLY" in result or "Nothing else" in result or "only" in result

    def test_mermaid_fix_prompt_interpolates_error(self):
        result = get_mermaid_fix_prompt(self.CODE, self.ERROR)
        assert "Unicode not supported" in result

    def test_mermaid_fix_prompt_interpolates_code(self):
        result = get_mermaid_fix_prompt(self.CODE, self.ERROR)
        assert "Node ₁" in result

    def test_mermaid_fix_system_prompt_returns_str(self):
        result = get_mermaid_fix_system_prompt()
        assert isinstance(result, str)

    def test_mermaid_fix_system_prompt_non_empty(self):
        result = get_mermaid_fix_system_prompt()
        assert len(result) > 0

    def test_mermaid_fix_system_prompt_has_negative_constraint(self):
        result = get_mermaid_fix_system_prompt()
        assert _has_negative_constraint(result)


# ===========================================================================
# TestTestCaseReasoning
# ===========================================================================


class TestTestCaseReasoning:
    """Tests for get_test_case_reasoning_prompt and get_test_case_reasoning_system_prompt."""

    SIG = "def dot_product(a, b):"
    INPUT = "[1,2,3], [4,5,6]"
    OUTPUT = "32"

    def test_test_case_reasoning_prompt_returns_str(self):
        result = get_test_case_reasoning_prompt(self.SIG, self.INPUT, self.OUTPUT)
        assert isinstance(result, str)

    def test_test_case_reasoning_prompt_non_empty(self):
        result = get_test_case_reasoning_prompt(self.SIG, self.INPUT, self.OUTPUT)
        assert len(result) > 0

    def test_test_case_reasoning_prompt_has_negative_constraint(self):
        result = get_test_case_reasoning_prompt(self.SIG, self.INPUT, self.OUTPUT)
        assert _has_negative_constraint(result)

    def test_test_case_reasoning_prompt_has_structural_markers(self):
        result = get_test_case_reasoning_prompt(self.SIG, self.INPUT, self.OUTPUT)
        assert "INPUT" in result
        assert "PROCESS" in result
        assert "OUTPUT" in result

    def test_test_case_reasoning_prompt_interpolates_signature(self):
        result = get_test_case_reasoning_prompt(self.SIG, self.INPUT, self.OUTPUT)
        assert "def dot_product(a, b):" in result

    def test_test_case_reasoning_system_prompt_returns_str(self):
        result = get_test_case_reasoning_system_prompt()
        assert isinstance(result, str)

    def test_test_case_reasoning_system_prompt_non_empty(self):
        result = get_test_case_reasoning_system_prompt()
        assert len(result) > 0

    def test_test_case_reasoning_system_prompt_has_negative_constraint(self):
        result = get_test_case_reasoning_system_prompt()
        assert _has_negative_constraint(result)


# ===========================================================================
# TestLatexExport
# ===========================================================================


class TestLatexExport:
    """Tests for get_latex_export_prompt and get_latex_export_system_prompt."""

    KWARGS = dict(
        problem_name="Dot Product",
        current_date="2026-01-01",
        raw_content="# Step 1\n$$a \\cdot b$$",
    )

    # -- prompt (use_sonnet=True) --

    def test_latex_prompt_sonnet_returns_str(self):
        result = get_latex_export_prompt(**self.KWARGS, use_sonnet=True)
        assert isinstance(result, str)

    def test_latex_prompt_sonnet_non_empty(self):
        result = get_latex_export_prompt(**self.KWARGS, use_sonnet=True)
        assert len(result) > 0

    def test_latex_prompt_sonnet_has_negative_constraint(self):
        result = get_latex_export_prompt(**self.KWARGS, use_sonnet=True)
        assert _has_negative_constraint(result)

    def test_latex_prompt_sonnet_mentions_search(self):
        result = get_latex_export_prompt(**self.KWARGS, use_sonnet=True)
        assert re.search(r"(?i)search|web", result)

    def test_latex_prompt_sonnet_interpolates_name(self):
        result = get_latex_export_prompt(**self.KWARGS, use_sonnet=True)
        assert "Dot Product" in result

    # -- prompt (use_sonnet=False / default) --

    def test_latex_prompt_default_returns_str(self):
        result = get_latex_export_prompt(**self.KWARGS, use_sonnet=False)
        assert isinstance(result, str)

    def test_latex_prompt_default_non_empty(self):
        result = get_latex_export_prompt(**self.KWARGS, use_sonnet=False)
        assert len(result) > 0

    def test_latex_prompt_default_has_negative_constraint(self):
        result = get_latex_export_prompt(**self.KWARGS, use_sonnet=False)
        assert _has_negative_constraint(result)

    def test_latex_prompt_default_no_search_the_web(self):
        result = get_latex_export_prompt(**self.KWARGS, use_sonnet=False)
        assert "search the web" not in result.lower()

    def test_latex_prompt_default_interpolates_date(self):
        result = get_latex_export_prompt(**self.KWARGS, use_sonnet=False)
        assert "2026-01-01" in result

    # -- system prompt --

    def test_latex_system_prompt_sonnet_returns_str(self):
        result = get_latex_export_system_prompt(use_sonnet=True)
        assert isinstance(result, str)

    def test_latex_system_prompt_sonnet_non_empty(self):
        result = get_latex_export_system_prompt(use_sonnet=True)
        assert len(result) > 0

    def test_latex_system_prompt_default_returns_str(self):
        result = get_latex_export_system_prompt(use_sonnet=False)
        assert isinstance(result, str)

    def test_latex_system_prompt_default_non_empty(self):
        result = get_latex_export_system_prompt(use_sonnet=False)
        assert len(result) > 0


# ===========================================================================
# TestMarkdownExport
# ===========================================================================


class TestMarkdownExport:
    """Tests for get_markdown_export_prompt and get_markdown_export_system_prompt."""

    STEPS = "## Step 1: Calculate\n$$a \\cdot b = 32$$"
    SUMMARY = "We calculated the dot product."

    def test_markdown_prompt_returns_str(self):
        result = get_markdown_export_prompt(self.STEPS, self.SUMMARY)
        assert isinstance(result, str)

    def test_markdown_prompt_non_empty(self):
        result = get_markdown_export_prompt(self.STEPS, self.SUMMARY)
        assert len(result) > 0

    def test_markdown_prompt_has_negative_constraint(self):
        result = get_markdown_export_prompt(self.STEPS, self.SUMMARY)
        assert _has_negative_constraint(result)

    def test_markdown_prompt_interpolates_steps(self):
        result = get_markdown_export_prompt(self.STEPS, self.SUMMARY)
        assert "Step 1: Calculate" in result

    def test_markdown_prompt_interpolates_summary(self):
        result = get_markdown_export_prompt(self.STEPS, self.SUMMARY)
        assert "We calculated the dot product." in result

    def test_markdown_system_prompt_returns_str(self):
        result = get_markdown_export_system_prompt()
        assert isinstance(result, str)

    def test_markdown_system_prompt_non_empty(self):
        result = get_markdown_export_system_prompt()
        assert len(result) > 0

    def test_markdown_system_prompt_has_negative_constraint(self):
        result = get_markdown_export_system_prompt()
        assert _has_negative_constraint(result)


# ===========================================================================
# TestHintPrompts
# ===========================================================================


class TestHintPrompts:
    """Tests for get_hint_system_prompt and get_hint_prompt."""

    TITLE = "Dot Product"
    DESC = "Calculate dot product of two vectors"
    CODE = "def dot(a,b): return sum(a)"
    ERROR = "IndexError: list index out of range"

    def test_hint_system_prompt_returns_str(self):
        result = get_hint_system_prompt()
        assert isinstance(result, str)

    def test_hint_system_prompt_non_empty(self):
        result = get_hint_system_prompt()
        assert len(result) > 0

    def test_hint_system_prompt_has_negative_constraint(self):
        result = get_hint_system_prompt()
        assert _has_negative_constraint(result)

    def test_hint_prompt_returns_str(self):
        result = get_hint_prompt(self.TITLE, self.DESC, self.CODE, self.ERROR)
        assert isinstance(result, str)

    def test_hint_prompt_non_empty(self):
        result = get_hint_prompt(self.TITLE, self.DESC, self.CODE, self.ERROR)
        assert len(result) > 0

    def test_hint_prompt_has_negative_constraint(self):
        result = get_hint_prompt(self.TITLE, self.DESC, self.CODE, self.ERROR)
        assert _has_negative_constraint(result)

    def test_hint_prompt_contains_title(self):
        result = get_hint_prompt(self.TITLE, self.DESC, self.CODE, self.ERROR)
        assert "Dot Product" in result

    def test_hint_prompt_contains_error(self):
        result = get_hint_prompt(self.TITLE, self.DESC, self.CODE, self.ERROR)
        assert "IndexError" in result

    def test_hint_prompt_contains_user_code(self):
        result = get_hint_prompt(self.TITLE, self.DESC, self.CODE, self.ERROR)
        assert "def dot(a,b): return sum(a)" in result


# ===========================================================================
# TestSolutionPrompts
# ===========================================================================


class TestSolutionPrompts:
    """Tests for get_solution_system_prompt and get_solution_prompt."""

    TITLE = "Dot Product"
    DESC = "Calculate dot product"
    STARTER = "def dot(a, b):"
    EXAMPLES = [{"input": "[1,2]", "output": "5"}]
    TEST_INFO = "2 test cases"

    def test_solution_system_prompt_returns_str(self):
        result = get_solution_system_prompt()
        assert isinstance(result, str)

    def test_solution_system_prompt_non_empty(self):
        result = get_solution_system_prompt()
        assert len(result) > 0

    def test_solution_system_prompt_has_negative_constraint(self):
        result = get_solution_system_prompt()
        assert _has_negative_constraint(result)

    def test_solution_prompt_returns_str(self):
        result = get_solution_prompt(
            self.TITLE, self.DESC, self.STARTER, self.EXAMPLES, self.TEST_INFO
        )
        assert isinstance(result, str)

    def test_solution_prompt_non_empty(self):
        result = get_solution_prompt(
            self.TITLE, self.DESC, self.STARTER, self.EXAMPLES, self.TEST_INFO
        )
        assert len(result) > 0

    def test_solution_prompt_has_negative_constraint(self):
        result = get_solution_prompt(
            self.TITLE, self.DESC, self.STARTER, self.EXAMPLES, self.TEST_INFO
        )
        assert _has_negative_constraint(result)

    def test_solution_prompt_contains_starter_code(self):
        result = get_solution_prompt(
            self.TITLE, self.DESC, self.STARTER, self.EXAMPLES, self.TEST_INFO
        )
        assert "def dot(a, b):" in result

    def test_solution_prompt_contains_title(self):
        result = get_solution_prompt(
            self.TITLE, self.DESC, self.STARTER, self.EXAMPLES, self.TEST_INFO
        )
        assert "Dot Product" in result

    def test_solution_prompt_contains_example(self):
        result = get_solution_prompt(
            self.TITLE, self.DESC, self.STARTER, self.EXAMPLES, self.TEST_INFO
        )
        assert "[1,2]" in result
        assert "5" in result


# ===========================================================================
# TestProviderPrompts
# ===========================================================================


class TestProviderPrompts:
    """Tests for Perplexity-specific prompt functions."""

    TITLE = "Dot Product"
    CODE = "def dot(a,b): return sum(a)"
    ERROR = "IndexError"

    # -- get_perplexity_reasoning_augmentation --

    def test_reasoning_augmentation_returns_str(self):
        result = get_perplexity_reasoning_augmentation()
        assert isinstance(result, str)

    def test_reasoning_augmentation_non_empty(self):
        result = get_perplexity_reasoning_augmentation()
        assert len(result) > 0

    def test_reasoning_augmentation_has_negative_constraint(self):
        result = get_perplexity_reasoning_augmentation()
        assert _has_negative_constraint(result)

    def test_reasoning_augmentation_mentions_latex(self):
        result = get_perplexity_reasoning_augmentation()
        assert "LaTeX" in result

    # -- get_perplexity_hint_system_prompt --

    def test_perplexity_hint_system_returns_str(self):
        result = get_perplexity_hint_system_prompt()
        assert isinstance(result, str)

    def test_perplexity_hint_system_non_empty(self):
        result = get_perplexity_hint_system_prompt()
        assert len(result) > 0

    def test_perplexity_hint_system_has_negative_constraint(self):
        result = get_perplexity_hint_system_prompt()
        assert _has_negative_constraint(result)

    # -- get_perplexity_hint_prompt --

    def test_perplexity_hint_prompt_returns_str(self):
        result = get_perplexity_hint_prompt(self.TITLE, self.CODE, self.ERROR)
        assert isinstance(result, str)

    def test_perplexity_hint_prompt_non_empty(self):
        result = get_perplexity_hint_prompt(self.TITLE, self.CODE, self.ERROR)
        assert len(result) > 0

    def test_perplexity_hint_prompt_has_negative_constraint(self):
        result = get_perplexity_hint_prompt(self.TITLE, self.CODE, self.ERROR)
        assert _has_negative_constraint(result)

    def test_perplexity_hint_prompt_contains_title(self):
        result = get_perplexity_hint_prompt(self.TITLE, self.CODE, self.ERROR)
        assert "Dot Product" in result

    def test_perplexity_hint_prompt_contains_error(self):
        result = get_perplexity_hint_prompt(self.TITLE, self.CODE, self.ERROR)
        assert "IndexError" in result

    def test_perplexity_hint_prompt_contains_code(self):
        result = get_perplexity_hint_prompt(self.TITLE, self.CODE, self.ERROR)
        assert "def dot(a,b): return sum(a)" in result
