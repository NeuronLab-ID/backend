# Reasoning Prompts
# Centralized prompt templates for quest reasoning generation


def _get_latex_base_requirements(
    problem_name: str,
    current_date: str,
    raw_content: str,
    author: str,
    packages_text: str,
) -> str:
    """Shared LaTeX conversion requirements."""
    return f"""CRITICAL OUTPUT REQUIREMENTS:
1. Output ONLY valid LaTeX code - no markdown wrappers, no explanations
2. Start with \\documentclass{{article}}
3. Include packages: {packages_text}
4. Escape special characters: & -> \\&, % -> \\%, $ -> \\$,
   # -> \\#, _ -> \\_, {{ -> \\{{, }} -> \\}}, ~ -> \\textasciitilde{{}},
   ^ -> \\textasciicircum{{}}, \\ -> \\textbackslash{{}}
5. Use \\section{{}} for headers, \\subsection{{}} for subheaders,
   \\textbf{{}} for bold, \\textit{{}} for italic, \\texttt{{}} for inline code
6. Math: \\( \\) for inline, \\[ \\] for display equations
7. Code blocks: \\begin{{lstlisting}} ... \\end{{lstlisting}}
8. Tables: Use tabular with explicit column specs (use booktabs if available)
9. No undefined control sequences; every command must be valid
10. Must compile in pdfLaTeX without errors

TOKEN BUDGET: Keep the output focused and under 2000 tokens when possible.

DOCUMENT METADATA:
- Title: {problem_name} - Solution Reasoning
- Author: {author}
- Date: {current_date}

FEW-SHOT EXAMPLE (Markdown -> LaTeX):
Markdown:
## Step 1: Mean
We compute the mean as $\\bar{{x}} = (2 + 4)/2$.

LaTeX:
\\section{{Step 1: Mean}}
We compute the mean as \\({{\\bar{{x}} = (2 + 4)/2}}\\).

CONTENT TO CONVERT:
{raw_content}

FINAL REQUIREMENT: Output the complete, compilable .tex file only."""


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
    web_references: str = "",
) -> str:
    """Generate the user prompt for step reasoning."""
    context_section = ""
    if previous_context:
        context_section = f"""
### Previous Steps Summary (USE THESE RESULTS - CONTINUE THE CALCULATION):
{previous_context}

CRITICAL: You MUST use the computed values from previous steps. Continue the calculation chain.
"""

    web_section = ""
    if web_references:
        web_section = f"""
### Web References (USE ONLY IF RELEVANT):
{web_references}
"""

    return f"""Step {step} of {total_steps}: {title}
Let's think step by step and show every intermediate calculation clearly.

{context_section}{web_section}Relation to main problem: {relation}
Definition: {definition}
Key Formulas:
{formulas_text}

Function: {function_signature}
Example Test Case:
- Input: {example_input}
- Expected Output: {example_output}

TASK: Explain this step with VISUAL AIDS for visual learners. Use the exact 7-section format below.

1. Concept Overview: Identify the exact mathematical concept and why it applies.
2. Visual Data Table: Display the example data in a markdown table with real-world labels.
3. Formula Application: Show the formula in LaTeX and explain each variable.
4. Step-by-Step Computation: Show calculations in order, including intermediate results.
5. Visual Summary: Include ONE visual aid (flowchart, table, or tree) that matches the computation.
6. Key Result: State the computed value clearly in a highlighted box.
7. Connection to Next Step: Explain how this output is used next.

NEGATIVE CONSTRAINTS:
- Do NOT skip intermediate calculations.
- NEVER invent data that is not provided.
- Do NOT change the example inputs or outputs.

TOKEN BUDGET: Keep the response focused and under 900 tokens.

FULL FEW-SHOT EXAMPLE (different problem and data):
1. Concept Overview: We compute a mean because it summarizes the dataset for later variance calculation.

2. Visual Data Table:
| Sample | Value |
|--------|-------|
| A      | 2     |
| B      | 4     |

3. Formula Application:
$$\\bar{{x}} = \\frac{{1}}{{n}} \\sum_{{i=1}}^n x_i$$
Here, $n=2$ and $x_1=2, x_2=4$.

4. Step-by-Step Computation:
| Step | Calculation | Result |
|------|-------------|--------|
| 1    | $2 + 4$     | $6$    |
| 2    | $6/2$       | $3$    |

5. Visual Summary (Mermaid Flowchart):
```mermaid
graph LR
  A[Values: 2, 4] --> B[Sum = 6]
  B --> C[Divide by n=2]
  C --> D[Mean = 3]
```

6. Key Result:
> **Result:** $\\bar{{x}} = 3$

7. Connection to Next Step: This mean becomes the center used to compute squared deviations.

VISUAL REQUIREMENTS (RECENCY):
- Include at least ONE markdown table showing data.
- Include at least ONE mermaid diagram (flowchart, graph, or tree).
- Use LaTeX notation ($...$ for inline, $$...$$ for display math).
- Make it easy to follow visually.
FINAL REQUIREMENT: Your response MUST contain sections 1-7 in order with the exact headings."""


def get_step_system_prompt(step: int, total_steps: int) -> str:
    """Generate the system prompt for step reasoning."""
    return f"""You are an expert mathematics educator specializing in visual and interactive learning, with deep knowledge of LaTeX typesetting and Mermaid diagram syntax. You are performing Step {step} of {total_steps}.
Think step by step through each section, showing your reasoning process clearly.

OUTPUT STRUCTURE CONTRACT:
- You must include all 7 sections in order.
- Each section must be labeled and easy to scan.
- At least one markdown table and one Mermaid diagram are required.

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

```mermaid
graph TD
  Root[Dataset] --> A[Feature A]
  Root --> B[Feature B]
```

SEQUENTIAL COMPUTATION RULES:
- This is Step {step} of a {total_steps}-step sequential calculation.
- If web references provided a real-world dataset (e.g., Weather/Tennis), use that SAME dataset.
- If previous steps computed values, you MUST use those exact values.
- Your output feeds into the next step, so state your final result clearly.

NEGATIVE CONSTRAINTS:
- NEVER use Unicode special characters in Mermaid nodes.
- Do NOT output raw HTML.
- NEVER fabricate values not provided.

 TOKEN BUDGET: Keep each section concise — aim for under 900 tokens total.
 FINAL REQUIREMENT: End with a clear "Result for Step {step}:" and keep the format consistent and visual."""


def get_summary_prompt(steps_summary: str) -> str:
    """Generate the prompt for summarizing all steps."""
    return f"""Think about how each step's output feeds into the next, then summarize how these steps work together to solve the problem.
Note: You only see up to 100 characters per step summary, so do not assume missing details.

STEPS SUMMARY (TRUNCATED):
{steps_summary}

OUTPUT TEMPLATE:
Write a single coherent paragraph of 2-4 sentences that connects the key concepts and explains the overall flow.

FEW-SHOT EXAMPLE:
Input steps summary: "Step 1: compute mean. Step 2: compute squared deviations. Step 3: average deviations for variance."
Output: "The solution first computes the mean to establish a central reference point. It then measures squared deviations from that mean and averages them to obtain the variance, linking raw data to dispersion. This sequence turns individual values into a single, interpretable measure of spread."

NEGATIVE CONSTRAINTS:
- Do NOT simply list steps.
- Do NOT exceed 4 sentences.
- Do NOT introduce new concepts not implied by the summary.

TOKEN BUDGET: Keep the response under 120 tokens.
FINAL REQUIREMENT: Output exactly one paragraph of 2-4 sentences."""


def get_summary_system_prompt() -> str:
    """Get the system prompt for summary generation."""
    return """You are a concise mathematics communicator who excels at connecting concepts.
Output format: 2-4 sentences forming a coherent paragraph.
Constraints: Use LaTeX for formulas. Be precise. Avoid filler words.
Do NOT simply list steps — synthesize them into a narrative.

FEW-SHOT EXAMPLE:
Good: "The algorithm first partitions the data, then recursively sorts each half, achieving O(n log n) by dividing the work at each level."
Bad: "Step 1 partitions. Step 2 sorts left. Step 3 sorts right." (This just lists steps.)

TOKEN BUDGET: Keep response under 120 tokens.
NEVER exceed 4 sentences."""


def get_mermaid_fix_prompt(code: str, error: str) -> str:
    """Generate the prompt for fixing Mermaid code."""
    return f"""Fix this Mermaid diagram. First identify the syntax error, then apply the minimal fix.

Error: {error}

Original code:
{code}

FEW-SHOT EXAMPLE:
Broken:
graph TD
  A[Mean\\nValue] --> B[Variance₁]

Fixed:
graph TD
  A[Mean<br/>Value] --> B[Variance1]

NEGATIVE CONSTRAINTS:
- Do NOT change the diagram structure or node IDs unless required to fix syntax.
- NEVER wrap the output in markdown code blocks.
- Do NOT add explanations.

TOKEN BUDGET: Keep the response under 200 tokens.
OUTPUT ONLY the fixed Mermaid code. Nothing else."""


def get_mermaid_fix_system_prompt() -> str:
    """Get the system prompt for Mermaid fixing."""
    return """You are an expert Mermaid.js syntax debugger.

Common issues and fixes (examples):
1. Newlines inside node labels -> replace with <br/> or single line.
   Example: A[Line1\nLine2] -> A[Line1<br/>Line2]
2. Unicode subscripts -> replace with plain text.
   Example: Variance₁ -> Variance1
3. Unquoted special characters -> add quotes.
   Example: A[Mean (x)] -> A["Mean (x)"]
4. Missing quotes around labels with spaces -> add quotes.
   Example: A[Mean Value] -> A["Mean Value"]
5. Invalid node IDs -> use alphanumeric or underscores only.
6. Edge syntax errors -> ensure correct arrows and spacing.

NEGATIVE CONSTRAINTS:
 - NEVER output markdown code blocks.
 - NEVER add explanatory text.
 - ONLY return the fixed Mermaid code.

TOKEN BUDGET: Keep response under 200 tokens."""


def get_test_case_reasoning_prompt(function_signature: str, test_input: str, expected_output: str) -> str:
    """Generate prompt for test case reasoning."""
    return f"""Function: {function_signature}
Test Input: {test_input}
Expected Output: {expected_output}

Work through the computation step by step in natural language.

FORMAT (EXACT):
INPUT: ...
PROCESS: ...
OUTPUT: ...

FEW-SHOT EXAMPLE:
Function: def add_one(x: int) -> int
Test Input: x = 4
Expected Output: 5
INPUT: The input is the integer 4, representing the value to increment.
PROCESS: Add 1 to the input value. This gives 4 + 1 = 5.
OUTPUT: The result is 5, which matches the expected output.

NEGATIVE CONSTRAINTS:
 - Do NOT include code snippets.
 - Do NOT exceed 3 sentences per section.

 TOKEN BUDGET: Keep response under 250 tokens.
 FORMAT REMINDER: Your response MUST use exactly: INPUT: / PROCESS: / OUTPUT:"""


def get_test_case_reasoning_system_prompt() -> str:
    """Get system prompt for test case reasoning."""
    return """You are a precise programming tutor who explains test cases in plain language with math notation.

Exact format required:
INPUT: [2-4 sentences]
PROCESS: [2-4 sentences]
OUTPUT: [2-4 sentences]

FEW-SHOT EXAMPLE:
INPUT: The input is a list of three numbers: 1, 3, and 5.
PROCESS: Sum the numbers to get 9, then divide by 3 to compute the mean. The computed mean is 3.
OUTPUT: The function returns 3, which represents the average of the input list.

 NEGATIVE CONSTRAINTS:
 - Do NOT include code.
 - Do NOT use bullet points or additional headings.
 Keep each section to 2-4 sentences and use math notation where helpful.
 TOKEN BUDGET: Keep each section to 2-4 sentences."""


def get_latex_export_prompt(problem_name: str, current_date: str, raw_content: str, use_sonnet: bool = False) -> str:
    """Generate prompt for LaTeX export."""
    if use_sonnet:
        base_requirements = _get_latex_base_requirements(
            problem_name=problem_name,
            current_date=current_date,
            raw_content=raw_content,
            author="Generated by NeuronLab AI (Sonnet Enhanced)",
            packages_text="amsmath, amssymb, amsthm, hyperref, listings, graphicx, xcolor, geometry, booktabs",
        )
        return f"""You are a LaTeX expert. Convert this mathematical reasoning into a VALID pdfLaTeX document.

IMPORTANT: Search the web to verify LaTeX syntax for any complex mathematical notation.
- Search for correct LaTeX syntax for matrices, integrals, summations, fractions
- Search for proper package requirements for special symbols
- Validate that all environments (equation, align, lstlisting) are correctly used

NEGATIVE CONSTRAINTS:
- Do NOT use undefined commands.
- NEVER include text outside the LaTeX document.
- Do NOT output markdown or explanations.

{base_requirements}"""

    base_requirements = _get_latex_base_requirements(
        problem_name=problem_name,
        current_date=current_date,
        raw_content=raw_content,
        author="Generated by NeuronLab AI",
        packages_text="amsmath, amssymb, amsthm, hyperref, listings, graphicx, xcolor, geometry",
    )
    return f"""Convert the following mathematical reasoning content into a VALID pdfLaTeX document.

NEGATIVE CONSTRAINTS:
- Do NOT use undefined commands.
- NEVER include text outside the LaTeX document.
- Do NOT output markdown or explanations.

{base_requirements}"""


def get_latex_export_system_prompt(use_sonnet: bool = False) -> str:
    """Get system prompt for LaTeX export."""
    if use_sonnet:
        return """You are a LaTeX documentation expert. Produce ONLY valid, compilable pdfLaTeX code.
Common issues to avoid:
 - Missing package declarations for special symbols
 - Unescaped special characters (&, %, $, #, _, {, })
 - Mismatched braces or environments
 - Invalid math mode syntax
NEGATIVE CONSTRAINTS: Never output markdown, explanations, or partial documents.

FEW-SHOT: `## Title` → `\\section{Title}`, `$x$` → `\\(x\\)`.
TOKEN BUDGET: Focus on valid, compilable output."""
    return """You are a LaTeX documentation expert. Produce ONLY valid, compilable pdfLaTeX code.
Do NOT use undefined commands, unescaped characters, or mismatched environments.
NEVER output markdown, explanations, or partial documents.

FEW-SHOT: `## Title` → `\\section{Title}`, `**bold**` → `\\textbf{bold}`.
TOKEN BUDGET: Focus on valid, compilable output."""


def get_markdown_export_prompt(steps_text: str, summary: str) -> str:
    """Generate prompt for markdown export."""
    return f"""Reformat this mathematical solution reasoning for Google Docs compatibility.

REQUIREMENTS:
1. Use $...$ for inline math (e.g., $x = 5$)
2. Use $$...$$ for display math on separate lines (e.g., $$\\frac{{a}}{{b}}$$)
3. Fix LaTeX syntax errors and normalize delimiters
4. Keep all content but improve readability
5. Format tables properly using markdown syntax
6. Preserve the structure with headings in the form "## Step N: Title"

FEW-SHOT EXAMPLE:
Before:
Step 1: Mean
mean = (2+4)/2

After:
## Step 1: Mean
We compute the mean as $\\bar{{x}} = (2 + 4)/2$.

CONTENT TO REFORMAT:
{steps_text}

SUMMARY:
{summary}

NEGATIVE CONSTRAINTS:
- Do NOT add new steps or remove existing content.
- NEVER introduce HTML or code fences.
- Do NOT change mathematical meaning.

TOKEN BUDGET: Keep the response under 1800 tokens.
FINAL REQUIREMENT: Return only the reformatted markdown content."""


def get_markdown_export_system_prompt() -> str:
    """Get system prompt for markdown export."""
    return """You are a markdown formatting specialist for Google Docs math content.
Use $...$ for inline math and $$...$$ for display math. Keep headings as "## Step N: Title".
NEGATIVE CONSTRAINTS: Do NOT add code fences, HTML, or extra commentary. Do NOT change math meaning.

FEW-SHOT: `mean = (2+4)/2` → `$\bar{x} = (2+4)/2$`. Raw formulas become LaTeX.
TOKEN BUDGET: Keep response under 1800 tokens.
FINAL REQUIREMENT: Output only clean markdown content."""
