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

VGROUP / MOBJECT SAFETY:
- NEVER use VGroup(*self.mobjects) — self.mobjects contains non-VMobject items (cameras, updaters). Use explicit VGroup of created objects instead.
- NEVER use FadeOut(VGroup(*self.mobjects)) or similar cleanup patterns at end of scene — Manim handles cleanup automatically.
- NEVER reference self.mobjects directly — track your created objects in local variables.
- Do NOT use Mobject base class — always use VMobject subclasses (VGroup, VMobject, etc.) for grouping.
- NEVER add non-VMobject items to VGroup — VGroup only accepts VMobject subclasses.

LATEX / MATHTEX SAFETY:
- Do NOT use raw \\begin{bmatrix} or \\begin{pmatrix} inside MathTex — use Matrix() / IntegerMatrix() instead.
- NEVER put \\text{} inside MathTex — use Tex() for mixed text+math, MathTex is math-only.
- Do NOT use complex nested LaTeX environments — keep MathTex simple and atomic.

LAYOUT / FONT COLLISION PREVENTION:
- NEVER place two text/math objects at the same position — always use .next_to(), .shift(), or .arrange().
- Do NOT create text or formulas that exceed the frame width (14.2 units) — break into lines or reduce font_size. Frame is 14.2 × 8 units.
- NEVER use font_size larger than 48 for body text or 60 for titles — prevents overflow/clipping.
- Do NOT mix different font sizes in the same horizontal line — causes "font collapsing" artifacts.
- NEVER place labels/text adjacent without explicit spacing — always use buff ≥ 0.2.
- Do NOT animate text that will extend beyond the visible frame — calculate total width.
- NEVER let animated equations grow beyond their container — position each line below previous with .next_to(prev_line, DOWN, buff=0.3).

POSITIVE GUIDANCE:
- Use Matrix(), IntegerMatrix(), or DecimalMatrix() for matrix display.
- Track created objects in local variables: title = Text(...), formula = MathTex(...), then VGroup(title, formula).
- For cleanup/fadeout: self.play(FadeOut(title), FadeOut(formula)) — list specific objects.
- Use .scale_to_fit_width(config.frame_width - 1) if text/formula might be too wide.
- Use .arrange(DOWN, aligned_edge=LEFT, buff=0.3) for vertical lists.

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

LAYOUT RULES:
- Frame is 14.2 units wide × 8 units tall.
- Title at top (.to_edge(UP)), content stacked below with .next_to(DOWN).
- Max font_size: 48 for body text, 60 for titles.
- Use .scale_to_fit_width(config.frame_width - 1) for safety if text/formula might be too wide.

SAFE PATTERNS:
- Correct VGroup usage: title = Text(...), formula = MathTex(...), then VGroup(title, formula).
- Correct Matrix() usage instead of raw LaTeX: use Matrix(), IntegerMatrix(), or DecimalMatrix().
- Correct cleanup with named FadeOut: self.play(FadeOut(title), FadeOut(formula)) — list specific objects.
- Correct positioning: use .next_to(prev_obj, DOWN, buff=0.3) to avoid overlaps.

DANGEROUS PATTERNS — NEVER USE:
- VGroup(*self.mobjects) — will include non-VMobject items.
- FadeOut(VGroup(*self.mobjects)) — Manim handles cleanup automatically.
- Raw LaTeX matrix environments in MathTex — use Matrix() instead.
- Text commands inside MathTex — use Tex() for mixed text+math.
- Absolute coordinates that may overlap — always use .next_to() or .arrange().

FINAL REQUIREMENT: Return only the complete Python code file content."""


def get_manim_visualization_system_prompt() -> str:
    """Get the system prompt for ManimCE visualization animation generation."""
    return """You are a ManimCE expert who writes clean, runnable Python animations for visual/intuitive learning.
Generate valid Manim Community Edition code only.

NEGATIVE CONSTRAINTS:
- NEVER use ManimGL imports.
- Do NOT use OpenGL rendering.
- Do NOT include play() calls outside construct().
- NEVER use deprecated Scene.play() syntax.

VGROUP / MOBJECT SAFETY:
- NEVER use VGroup(*self.mobjects) — self.mobjects contains non-VMobject items (cameras, updaters). Use explicit VGroup of created objects instead.
- NEVER use FadeOut(VGroup(*self.mobjects)) or similar cleanup patterns at end of scene — Manim handles cleanup automatically.
- NEVER reference self.mobjects directly — track your created objects in local variables.
- Do NOT use Mobject base class — always use VMobject subclasses (VGroup, VMobject, etc.) for grouping.
- NEVER add non-VMobject items to VGroup — VGroup only accepts VMobject subclasses.

LATEX / MATHTEX SAFETY:
- Do NOT use raw \\begin{bmatrix} or \\begin{pmatrix} inside MathTex — use Matrix() / IntegerMatrix() instead.
- NEVER put \\text{} inside MathTex — use Tex() for mixed text+math, MathTex is math-only.
- Do NOT use complex nested LaTeX environments — keep MathTex simple and atomic.

LAYOUT / FONT COLLISION PREVENTION:
- NEVER place two text/math objects at the same position — always use .next_to(), .shift(), or .arrange().
- Do NOT create text or formulas that exceed the frame width (14.2 units) — break into lines or reduce font_size. Frame is 14.2 × 8 units.
- NEVER use font_size larger than 48 for body text or 60 for titles — prevents overflow/clipping.
- Do NOT mix different font sizes in the same horizontal line — causes "font collapsing" artifacts.
- NEVER place labels/text adjacent without explicit spacing — always use buff ≥ 0.2.
- Do NOT animate text that will extend beyond the visible frame — calculate total width.
- NEVER let animated equations grow beyond their container — position each line below previous with .next_to(prev_line, DOWN, buff=0.3).

VISUALIZATION-SPECIFIC CONSTRAINTS:
- NEVER use MathTex or Tex for displaying formulas or equations.
- Do NOT show calculations, derivations, or mathematical notation.
- NEVER include step-by-step mathematical working.
- Your ONLY purpose is to create visual/intuitive animations that build conceptual understanding.
- Use geometric shapes, spatial transformations, color-coded flows, animated diagrams, data visualizations.
- Choose the visual style that best matches the problem domain (geometric for linear algebra, neural network diagrams for deep learning, data flow for algorithms, etc.).

POSITIVE GUIDANCE:
- Use Matrix(), IntegerMatrix(), or DecimalMatrix() for matrix display.
- Track created objects in local variables: title = Text(...), formula = MathTex(...), then VGroup(title, formula).
- For cleanup/fadeout: self.play(FadeOut(title), FadeOut(formula)) — list specific objects.
- Use .scale_to_fit_width(config.frame_width - 1) if text/formula might be too wide.
- Use .arrange(DOWN, aligned_edge=LEFT, buff=0.3) for vertical lists.

OUTPUT REQUIREMENTS:
- The result must be valid Python code for ManimCE.
- Use standard ManimCE objects and animations.
- Keep the scene focused and deterministic."""


def get_manim_visualization_prompt(
    step_number: int,
    step_title: str,
    step_reasoning: str,
    key_formulas: list[dict[str, str]],
    problem_title: str,
    problem_description: str,
) -> str:
    """Get the user prompt for generating a ManimCE visualization scene for a single step."""
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

Key Formulas (for context only — do NOT display as text):
{formulas_text}

TASK: Generate a complete ManimCE scene that creates a VISUAL/INTUITIVE animation for this step.
Output format: a full Python file that starts with `from manim import *` and defines `class MainScene(Scene)`.

VISUALIZATION REQUIREMENTS:
- Create visual/intuitive animations that build conceptual understanding.
- Use geometric shapes, spatial transformations, color-coded flows, animated diagrams, data visualizations.
- Choose the visual style that best matches the problem domain (geometric for linear algebra, neural network diagrams for deep learning, data flow for algorithms, etc.).
- Do NOT show calculations, derivations, or mathematical notation.
- Do NOT display formulas or equations as text — show concepts visually instead.

SCENE REQUIREMENTS:
- Use ManimCE objects like Circle, Rectangle, Arrow, Dot, VGroup, Line, Polygon.
- Use animations like FadeIn, Write, Transform, Create, Rotate, Scale, Shift.
- Use self.play(), self.wait(), and self.add() inside construct().

NEGATIVE CONSTRAINTS:
- Do NOT generate audio/voiceover code.
- NEVER use external files or images.
- Do NOT exceed 30 seconds of animation.
- NEVER display formulas or equations as text — show concepts visually instead.

LAYOUT RULES:
- Frame is 14.2 units wide × 8 units tall.
- Title at top (.to_edge(UP)), content stacked below with .next_to(DOWN).
- Max font_size: 48 for body text, 60 for titles.
- Use .scale_to_fit_width(config.frame_width - 1) for safety if text/formula might be too wide.

SAFE PATTERNS:
- Correct VGroup usage: title = Text(...), shapes = VGroup(circle, rect), then VGroup(title, shapes).
- Correct cleanup with named FadeOut: self.play(FadeOut(title), FadeOut(shapes)) — list specific objects.
- Correct positioning: use .next_to(prev_obj, DOWN, buff=0.3) to avoid overlaps.

DANGEROUS PATTERNS — NEVER USE:
- VGroup(*self.mobjects) — will include non-VMobject items.
- FadeOut(VGroup(*self.mobjects)) — Manim handles cleanup automatically.
- Raw LaTeX matrix environments in MathTex — use Matrix() instead.
- Text commands inside MathTex — use Tex() for mixed text+math.
- Absolute coordinates that may overlap — always use .next_to() or .arrange().
- Displaying formulas or equations as text — visualize the concepts instead.

FINAL REQUIREMENT: Return only the complete Python code file content."""
