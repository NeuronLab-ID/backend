"""
Test suite for prompt consolidation verification.

This module verifies that all prompts have been properly consolidated into the
app/prompts/ package and that no inline prompts remain in provider/service files.

Tests ensure:
1. All prompt functions are accessible from app.prompts
2. All expected functions are exported in __all__
3. No inline prompts remain in OpenAI provider
4. No inline prompts remain in solution generator
5. No inline hint prompts remain in Perplexity provider (search prompt is allowed)
6. Perplexity search prompt is still present (intentionally left inline)
7. New prompt modules exist and are importable
"""

import ast
import pytest


class TestPromptExports:
    """Test that all prompts are properly exported from app.prompts."""

    def test_all_prompt_functions_accessible(self):
        """Import every function listed in __all__ from app.prompts and verify each is callable."""
        import app.prompts

        # Get the __all__ list
        all_exports = app.prompts.__all__

        # Verify __all__ is not empty
        assert all_exports, "__all__ should not be empty"

        # Try to import and verify each export is callable or a constant
        for export_name in all_exports:
            # Get the attribute from the module
            attr = getattr(app.prompts, export_name, None)
            assert attr is not None, f"Export '{export_name}' not found in app.prompts"

            # Check if it's callable (function) or a constant (like DIFFICULTY_CONFIG)
            if export_name == "DIFFICULTY_CONFIG":
                # DIFFICULTY_CONFIG is a dict constant, not callable
                assert isinstance(attr, dict), f"{export_name} should be a dict"
            else:
                # All other exports should be callable functions
                assert callable(attr), f"{export_name} should be callable"

    def test_all_exports_in_dunder_all(self):
        """Verify that __all__ contains every expected function name."""
        import app.prompts

        expected_exports = {
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
        }

        actual_exports = set(app.prompts.__all__)

        # Check that all expected exports are present
        missing = expected_exports - actual_exports
        assert not missing, f"Missing exports in __all__: {missing}"

        # Check that there are no unexpected exports
        extra = actual_exports - expected_exports
        assert not extra, f"Unexpected exports in __all__: {extra}"


class TestNoInlinePrompts:
    """Test that inline prompts have been removed from provider/service files."""

    def _parse_file_ast(self, filepath: str) -> ast.Module:
        """Parse a Python file and return its AST."""
        with open(filepath, "r", encoding="utf-8") as f:
            return ast.parse(f.read())

    def _find_string_constants(self, tree: ast.Module) -> list[str]:
        """Find all string constants in an AST tree."""
        strings = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                strings.append(node.value)
        return strings

    def test_openai_provider_no_inline_prompts(self):
        """Verify no inline prompts remain in openai_provider.py.

        Checks for strings >100 chars containing words like 'tutor', 'expert',
        'programmer', 'guide', or 'socratic' (case-insensitive).
        """
        filepath = "app/services/ai_providers/openai_provider.py"
        tree = self._parse_file_ast(filepath)
        strings = self._find_string_constants(tree)

        # Keywords that indicate inline prompts
        prompt_keywords = ["tutor", "expert", "programmer", "guide", "socratic"]

        inline_prompts = []
        for s in strings:
            # Only check strings longer than 100 chars (likely prompts)
            if len(s) > 100:
                # Check if any prompt keyword is present (case-insensitive)
                if any(keyword in s.lower() for keyword in prompt_keywords):
                    inline_prompts.append(s[:100] + "...")

        assert not inline_prompts, f"Found inline prompts in {filepath}: {inline_prompts}"

    def test_solution_generator_no_inline_prompts(self):
        """Verify no inline prompts remain in solution_generator.py.

        Checks for strings >100 chars containing 'expert', 'programmer',
        'solution', or 'PEP 8' (case-insensitive).
        """
        filepath = "app/services/solution_generator.py"
        tree = self._parse_file_ast(filepath)
        strings = self._find_string_constants(tree)

        # Keywords that indicate inline prompts
        prompt_keywords = ["expert", "programmer", "solution", "pep 8"]

        inline_prompts = []
        for s in strings:
            # Only check strings longer than 100 chars (likely prompts)
            if len(s) > 100:
                # Check if any prompt keyword is present (case-insensitive)
                if any(keyword in s.lower() for keyword in prompt_keywords):
                    inline_prompts.append(s[:100] + "...")

        assert not inline_prompts, f"Found inline prompts in {filepath}: {inline_prompts}"

    def test_perplexity_provider_no_inline_hint_prompts(self):
        """Verify no inline hint prompts remain in perplexity_provider.py.

        The search() method's inline prompt is allowed and should NOT be flagged.
        Uses specific detection patterns to avoid false positives:
        - "Give a SHORT hint" or "has an error. Give"
        """
        filepath = "app/services/ai_providers/perplexity_provider.py"
        tree = self._parse_file_ast(filepath)
        strings = self._find_string_constants(tree)

        # Specific patterns that indicate hint prompts (not search prompts)
        hint_patterns = ["give a short hint", "has an error. give"]

        inline_hint_prompts = []
        for s in strings:
            # Only check strings longer than 100 chars (likely prompts)
            if len(s) > 100:
                # Check if any hint pattern is present (case-insensitive)
                if any(pattern in s.lower() for pattern in hint_patterns):
                    inline_hint_prompts.append(s[:100] + "...")

        assert not inline_hint_prompts, f"Found inline hint prompts in {filepath}: {inline_hint_prompts}"

    def test_perplexity_search_prompt_untouched(self):
        """Verify that the search() method's inline prompt is still present.

        The search() method's prompt was intentionally left inline and should
        contain the string "Search for educational resources".
        """
        filepath = "app/services/ai_providers/perplexity_provider.py"
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # The search prompt should still be present
        assert "Search for educational resources" in content, "search() method's inline prompt should still be present"


class TestPromptModules:
    """Test that new prompt modules exist and are importable."""

    def test_new_prompt_modules_exist(self):
        """Verify that hint_prompts.py, solution_prompts.py, and provider_prompts.py exist."""
        # Try to import each module
        try:
            import app.prompts.hint_prompts

            assert hasattr(app.prompts.hint_prompts, "get_hint_system_prompt"), (
                "hint_prompts should have get_hint_system_prompt"
            )
            assert hasattr(app.prompts.hint_prompts, "get_hint_prompt"), "hint_prompts should have get_hint_prompt"
        except ImportError as e:
            pytest.fail(f"Failed to import app.prompts.hint_prompts: {e}")

        try:
            import app.prompts.solution_prompts

            assert hasattr(app.prompts.solution_prompts, "get_solution_system_prompt"), (
                "solution_prompts should have get_solution_system_prompt"
            )
            assert hasattr(app.prompts.solution_prompts, "get_solution_prompt"), (
                "solution_prompts should have get_solution_prompt"
            )
        except ImportError as e:
            pytest.fail(f"Failed to import app.prompts.solution_prompts: {e}")

        try:
            import app.prompts.provider_prompts

            assert hasattr(app.prompts.provider_prompts, "get_perplexity_reasoning_augmentation"), (
                "provider_prompts should have get_perplexity_reasoning_augmentation"
            )
            assert hasattr(app.prompts.provider_prompts, "get_perplexity_hint_system_prompt"), (
                "provider_prompts should have get_perplexity_hint_system_prompt"
            )
            assert hasattr(app.prompts.provider_prompts, "get_perplexity_hint_prompt"), (
                "provider_prompts should have get_perplexity_hint_prompt"
            )
        except ImportError as e:
            pytest.fail(f"Failed to import app.prompts.provider_prompts: {e}")
