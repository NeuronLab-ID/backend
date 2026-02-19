# Math Prompts
# Prompt templates for math sample generation

DIFFICULTY_CONFIG = {
    "easy": {"steps": "2-3", "values": "single digits (1-9)", "elements": "2"},
    "medium": {"steps": "3-5", "values": "integers (-10 to 10)", "elements": "3"},
    "hard": {"steps": "5-7", "values": "any integers or decimals", "elements": "4-5"},
}


def get_sample_prompt(formula_name: str, formula_latex: str, difficulty: str) -> str:
    """Generate the prompt for creating a worked math example.

    Args:
        formula_name: Name of the mathematical formula
        formula_latex: LaTeX representation of the formula
        difficulty: Difficulty level (easy, medium, hard)

    Returns:
        Formatted prompt string
    """
    config = DIFFICULTY_CONFIG.get(difficulty.lower(), DIFFICULTY_CONFIG["easy"])

    return f"""Generate a worked example for this mathematical concept.
Think through each step of the calculation before generating the example.

Formula Name: {formula_name}
Formula (LaTeX): {formula_latex}

Requirements (Difficulty: {difficulty.upper()}):
1. Use {config["values"]} for numbers
2. Show {config["steps"]} clear steps with detailed explanations
3. Use LaTeX formatting for math expressions (wrap in $...$)
4. Use vectors/matrices with {config["elements"]} elements

FULL FEW-SHOT EXAMPLE (JSON ONLY):
{{
    "steps": [
        "Given: $\\mathbf{{a}} = [2, -1, 3]$ and $\\mathbf{{b}} = [4, 0, -2]$",
        "Step 1: Multiply corresponding elements: $(2 \\times 4) + (-1 \\times 0) + (3 \\times -2)$",
        "Step 2: Calculate each product: $8 + 0 - 6$",
        "Step 3: Sum the results: $8 - 6 = 2$"
    ],
    "result": "$\\mathbf{{a}} \\cdot \\mathbf{{b}} = 2$"
}}

NEGATIVE CONSTRAINTS:
- Do NOT use the same numbers as the example above.
- NEVER include explanation text outside the JSON.
- Do NOT skip intermediate calculation steps.

REMEMBER: Return ONLY valid JSON. No markdown code blocks. No text before or after the JSON.

Generate a new random example now:"""


def get_retry_prompt(formula_name: str, formula_latex: str) -> str:
    """Generate a simplified retry prompt when initial generation fails.

    Args:
        formula_name: Name of the mathematical formula
        formula_latex: LaTeX representation of the formula

    Returns:
        Simplified prompt string
    """
    return f"""Generate a simple worked math example for: {formula_name}

Formula: {formula_latex}

Use small numbers. Show whatever steps are needed. Use $...$ for math.

Return ONLY valid JSON:
{{"steps": ["Given: $x = 3$", "Step 1: Compute $x^2 = 3^2 = 9$"], "result": "$x^2 = 9$"}}

NEGATIVE CONSTRAINTS:
- Do NOT include markdown code fences.
- NEVER add explanation text.

OUTPUT: Only the JSON object. Nothing else."""


def get_system_prompt() -> str:
    """Get the system prompt for math sample generation."""
    return """You are an expert mathematics tutor who creates clear, step-by-step worked examples.
Output format: JSON only with keys steps and result.
Do NOT wrap JSON in markdown code blocks.
NEVER include conversational text."""


def get_retry_system_prompt() -> str:
    """Get the system prompt for retry generation."""
    return """You are a math example generator. Return ONLY valid JSON.
Do NOT add any text outside the JSON structure."""
