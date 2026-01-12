# Reasoning Prompts
# Centralized prompt templates for quest reasoning generation

def get_step_reasoning_prompt(
    step: int,
    total_steps: int,
    title: str,
    relation: str,
    definition: str,
    formulas_text: str,
    function_signature: str,
    example_input: str,
    example_output: str,
    previous_context: str = "",
    web_references: str = ""
) -> str:
    """Generate the user prompt for step reasoning."""
    context_section = ""
    if previous_context:
        context_section = f"""
### Previous Steps Summary (USE THESE RESULTS - CONTINUE THE CALCULATION):
{previous_context}

**CRITICAL**: You MUST use the computed values from previous steps. Continue the calculation chain.
"""
    
    return f"""Step {step} of {total_steps}: {title}
{context_section}
{web_references}
Relation to main problem: {relation}
Definition: {definition}
Key Formulas:
{formulas_text}

Function: {function_signature}
Example Test Case:
- Input: {example_input}
- Expected Output: {example_output}

Now, explain this step with VISUAL AIDS for visual learners:

1. **Concept Overview**: What mathematical concept is being used (include a Mermaid flowchart if helpful)

2. **Visual Data Table**: Display the example data in a MARKDOWN TABLE:
   | Feature | Value 1 | Value 2 | ... |
   |---------|---------|---------|-----|
   Use REAL-WORLD descriptive values (e.g., Weather=Sunny, Play=Yes)

3. **Formula Application**: Show the formula with a visual breakdown:
   - Display the formula in LaTeX ($$...$$)
   - Create a Mermaid diagram showing data flow if applicable:
     ```mermaid
     graph LR
       A[Input] --> B[Process] --> C[Output]
     ```

4. **Step-by-Step Computation**: Show calculations in an organized way:
   - Use TABLES for intermediate results when appropriate
   - Show each calculation step clearly
   - Use $$...$$ for important formulas

5. **Visual Summary**: Include ONE of these visual aids:
   - **Mermaid Flowchart**: For algorithm steps
   - **Markdown Table**: For data transformations
   - **Tree Diagram** (using mermaid): For hierarchical data

6. **Key Result**: State the computed value clearly in a highlighted box
7. **Connection to Next Step**: How this result feeds into the next step

VISUAL REQUIREMENTS:
- Include at least ONE markdown table showing data
- Include at least ONE mermaid diagram (flowchart, graph, or tree)
- Use LaTeX notation ($...$ for inline, $$...$$ for display math)
- Make it easy to follow visually"""


def get_step_system_prompt(step: int, total_steps: int) -> str:
    """Generate the system prompt for step reasoning."""
    return f"""You are a VISUAL LEARNING specialist performing Step {step} of {total_steps}.

YOU MUST INCLUDE VISUAL AIDS:
1. **Markdown Tables**: Show data in tabular format
2. **Mermaid Diagrams**: Include flowcharts, graphs, or trees
3. **LaTeX Formulas**: Use $$...$$ for display math

MERMAID EXAMPLES YOU CAN USE:
```mermaid
graph TD
    A[Start] --> B{{Decision}}
    B -->|Yes| C[Action 1]
    B -->|No| D[Action 2]
```

```mermaid
graph LR
    Input --> Process --> Output
```

SEQUENTIAL COMPUTATION RULES:
- This is Step {step} of a {total_steps}-step sequential calculation
- If web references provided a real-world dataset (e.g., Weather/Tennis), use that SAME dataset
- If previous steps computed values, you MUST use those exact values
- Your output feeds into the next step, so state your final result clearly

VISUAL OUTPUT REQUIREMENTS:
1. Start with a brief concept overview
2. Show data in a MARKDOWN TABLE (required)
3. Include a MERMAID DIAGRAM showing the algorithm/data flow (required)
4. Use LaTeX for all formulas ($...$ inline, $$...$$ display)
5. Show step-by-step calculations with intermediate tables
6. End with a clear visual summary and "**Result for Step {step}:**"

IMPORTANT: Make the explanation VISUAL and easy to scan. Use diagrams and tables extensively."""


def get_summary_prompt(steps_summary: str) -> str:
    """Generate the prompt for summarizing all steps."""
    return f"""Summarize how these steps work together to solve the problem:
{steps_summary}

Provide a 2-3 sentence summary connecting all concepts."""


def get_summary_system_prompt() -> str:
    """Get the system prompt for summary generation."""
    return "You are a math tutor providing a concise summary of how all steps connect to solve the problem. Use LaTeX for formulas."


def get_mermaid_fix_prompt(code: str, error: str) -> str:
    """Generate the prompt for fixing Mermaid code."""
    return f"""Fix this Mermaid diagram. Error: {error}

Original code:
{code}

Return only the fixed Mermaid code:"""


def get_mermaid_fix_system_prompt() -> str:
    """Get the system prompt for Mermaid fixing."""
    return """You are a Mermaid diagram syntax expert. Fix the provided Mermaid diagram code.

Common issues to fix:
1. Newlines inside node labels - use <br/> instead or put on single line
2. Unicode subscripts (like ₁, ₂) - replace with regular text
3. Unquoted special characters in labels - add quotes around labels with special chars
4. Missing quotes around labels with spaces/special characters
5. Invalid node IDs - ensure IDs are alphanumeric with underscores only
6. Syntax errors in edges or subgraphs

Return ONLY the fixed Mermaid code, nothing else. No explanation, no markdown code blocks."""


def get_test_case_reasoning_prompt(function_signature: str, test_input: str, expected_output: str) -> str:
    """Generate prompt for test case reasoning."""
    return f"""Function: {function_signature}
Test Input: {test_input}
Expected Output: {expected_output}

Explain the reasoning step by step:"""


def get_test_case_reasoning_system_prompt() -> str:
    """Get system prompt for test case reasoning."""
    return """You are a programming tutor explaining how to solve a test case step by step.
Given a function signature, test input, and expected output, explain:
1. INPUT: What the input represents and its values
2. PROCESS: The step-by-step calculation/algorithm to transform input to output
3. OUTPUT: What the final result is and why

Keep each section concise (2-4 sentences max). Use mathematical notation when helpful.
Format your response EXACTLY as:
INPUT: [your explanation]
PROCESS: [your explanation]
OUTPUT: [your explanation]"""


def get_latex_export_prompt(problem_name: str, current_date: str, raw_content: str, use_sonnet: bool = False) -> str:
    """Generate prompt for LaTeX export."""
    if use_sonnet:
        return f"""You are a LaTeX expert. Convert this mathematical reasoning into a VALID pdfLaTeX document.

IMPORTANT: Search the web to verify LaTeX syntax for any complex mathematical notation.
- Search for correct LaTeX syntax for matrices, integrals, summations, fractions
- Search for proper package requirements for special symbols
- Validate that all environments (equation, align, lstlisting) are correctly used

CRITICAL OUTPUT REQUIREMENTS:
1. Output ONLY valid LaTeX code - no markdown wrappers, no explanations
2. Start with \\documentclass{{article}}
3. Include packages: amsmath, amssymb, amsthm, hyperref, listings, graphicx, xcolor, geometry, booktabs
4. ESCAPE all special characters: & → \\&, % → \\%, # → \\#, _ → \\_
5. Use \\section{{}} for headers, \\textbf{{}} for bold, \\textit{{}} for italic
6. Math: \\( \\) for inline, \\[ \\] or $$ for display equations
7. Code blocks: \\begin{{lstlisting}} ... \\end{{lstlisting}}
8. Tables: Use tabular with proper column specs
9. NO undefined control sequences - verify each LaTeX command exists
10. Must compile in pdfLaTeX without errors

DOCUMENT METADATA:
- Title: {problem_name} - Solution Reasoning  
- Author: Generated by NeuronLab AI (Sonnet Enhanced)
- Date: {current_date}

CONTENT TO CONVERT:
{raw_content}

Output the complete, compilable .tex file:"""
    
    return f"""Convert the following mathematical reasoning content into a VALID pdfLaTeX document.

CRITICAL REQUIREMENTS:
1. Output ONLY the LaTeX code, no markdown, no explanation
2. Start with \\documentclass{{article}}
3. Include all necessary packages: amsmath, amssymb, amsthm, hyperref, listings, graphicx, xcolor, geometry
4. Properly escape all special LaTeX characters: &, %, $, #, _, {{}}, ~, ^, \\
5. Convert markdown headers to \\section{{}} and \\subsection{{}}
6. Convert **bold** to \\textbf{{}} and *italic* to \\textit{{}}
7. Convert `code` to \\texttt{{}}
8. Ensure all math expressions use proper LaTeX: \\( \\) for inline, \\[ \\] for display
9. Convert markdown code blocks to lstlisting environment
10. Make sure the document compiles without errors in pdfLaTeX

TITLE: {problem_name} - Solution Reasoning
DATE: {current_date}
AUTHOR: Generated by NeuronLab AI

CONTENT TO CONVERT:
{raw_content}

Output the complete .tex file that will compile without errors:"""


def get_latex_export_system_prompt(use_sonnet: bool = False) -> str:
    """Get system prompt for LaTeX export."""
    if use_sonnet:
        return """You are a LaTeX documentation expert. Your task is to produce ONLY valid, compilable pdfLaTeX code.
Search the web to verify any LaTeX syntax you are unsure about. Common issues to avoid:
- Missing package declarations for special symbols
- Unescaped special characters (&, %, #, _, {, })
- Mismatched braces or environments
- Invalid math mode syntax"""
    return "Generate valid pdfLaTeX document"


def get_markdown_export_prompt(steps_text: str, summary: str) -> str:
    """Generate prompt for markdown export."""
    return f"""Reformat this mathematical solution reasoning for Google Docs compatibility.

REQUIREMENTS:
1. Use $...$ for inline math (e.g., $x = 5$)
2. Use $$...$$ for display math on separate lines (e.g., $$\\frac{{a}}{{b}}$$)
3. Clean up any LaTeX syntax errors
4. Ensure all mathematical expressions are properly formatted
5. Keep all content but improve readability
6. Format tables properly using markdown syntax

CONTENT TO REFORMAT:
{steps_text}

SUMMARY:
{summary}

Return the reformatted content maintaining the same structure (## Step N: Title format)."""
