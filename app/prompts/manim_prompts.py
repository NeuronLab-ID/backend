# Manim prompt templates


def get_manim_code_system_prompt() -> str:
    """Get the system prompt for ManimCE code generation."""
    return """You are a ManimCE expert who writes clean, runnable Python animations.
Generate valid Manim Community Edition code only.

NEGATIVE CONSTRAINTS:
- NEVER use ManimGL imports.
- Do NOT use OpenGL rendering.
- Do NOT include play() calls outside construct().
- NEVER use deprecated Scene.play() syntax.

OUTPUT REQUIREMENTS:
- The result must be valid Python code for ManimCE.
- Use standard ManimCE objects and animations.
- Keep the scene focused and deterministic."""


def get_manim_code_prompt(
    step_number: int,
    step_title: str,
    step_reasoning: str,
    key_formulas: list[dict[str, str]],
    problem_title: str,
    problem_description: str,
) -> str:
    """Get the user prompt for generating a ManimCE scene for a single step."""
    formulas_text = ""
    if key_formulas:
        formulas_lines: list[str] = []
        for formula in key_formulas:
            name = formula.get("name", "")
            latex = formula.get("latex", "")
            description = formula.get("description", "")
            formulas_lines.append(f"- Name: {name}\n  LaTeX: {latex}\n  Description: {description}")
        formulas_text = "\n".join(formulas_lines)
    else:
        formulas_text = "- None"

    return f"""Problem: {problem_title}
Description: {problem_description}

Step {step_number}: {step_title}
Reasoning: {step_reasoning}

Key Formulas:
{formulas_text}

TASK: Generate a complete ManimCE scene for this single step.
Output format: a full Python file that starts with `from manim import *` and defines `class MainScene(Scene)`.

SCENE REQUIREMENTS:
- Use ManimCE objects like MathTex, Tex, NumberPlane, Arrow, Dot, VGroup.
- Use animations like FadeIn, Write, Transform, Create.
- Use self.play(), self.wait(), and self.add() inside construct().

NEGATIVE CONSTRAINTS:
- Do NOT generate audio/voiceover code.
- NEVER use external files or images.
- Do NOT exceed 30 seconds of animation.

FINAL REQUIREMENT: Return only the complete Python code file content."""
