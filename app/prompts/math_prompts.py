# Math Prompts
# Prompt templates for math sample generation

DIFFICULTY_CONFIG = {
    "easy": {"steps": "2-3", "values": "single digits (1-9)", "elements": "2"},
    "medium": {"steps": "3-5", "values": "integers (-10 to 10)", "elements": "3"},
    "hard": {"steps": "5-7", "values": "any integers or decimals", "elements": "4-5"}
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

Formula Name: {formula_name}
Formula (LaTeX): {formula_latex}

Requirements (Difficulty: {difficulty.upper()}):
1. Use {config['values']} for numbers
2. Show {config['steps']} clear steps with detailed explanations
3. Use LaTeX formatting for math expressions (wrap in $...$)
4. Use vectors/matrices with {config['elements']} elements

Respond in this exact JSON format:
{{
    "steps": [
        "Given: $\\\\mathbf{{u}} = [1, 2]$ and $\\\\mathbf{{v}} = [3, 4]$",
        "Step 1: Multiply element-wise: $(1 \\\\times 3) + (2 \\\\times 4)$",
        "Step 2: Calculate: $3 + 8 = 11$"
    ],
    "result": "$\\\\mathbf{{u}} \\\\cdot \\\\mathbf{{v}} = 11$"
}}

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
{{"steps": ["step 1 text", "step 2 text"], "result": "final answer"}}"""


def get_system_prompt() -> str:
    """Get the system prompt for math sample generation."""
    return "You are a math tutor. Generate simple, clear worked examples with random integer values. Always respond with valid JSON only, no markdown code blocks."


def get_retry_system_prompt() -> str:
    """Get the system prompt for retry generation."""
    return "Return only valid JSON. No markdown."
