"""
AI-powered solution generator using OpenAI or GitHub Models.
"""
from typing import Optional
from app.services.hint_generator import create_client, AI_MODEL


async def generate_solution(problem: dict) -> Optional[str]:
    """
    Generate a reference solution for the problem.
    
    Returns Python code as a string.
    """
    try:
        client = create_client()
        
        # Build context
        problem_title = problem.get("title", "Unknown Problem")
        problem_desc = problem.get("description_decoded", problem.get("description", ""))
        starter_code = problem.get("starter_code", "")
        example = problem.get("example", {})
        test_cases = problem.get("test_cases", [])
        
        # Build test case info
        test_info = ""
        if test_cases:
            test_info = "\n".join([f"- Input: {tc.get('test', '')} => Expected: {tc.get('expected_output', '')}" for tc in test_cases[:3]])
        
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert Python programmer. Generate a clean, working solution for the given problem.

Rules:
- Write ONLY the Python code, no explanations
- Use the exact function signature provided
- Make sure the solution passes all test cases
- Keep the code clean and readable
- Add brief inline comments for key logic"""
                },
                {
                    "role": "user",
                    "content": f"""Problem: {problem_title}
Description: {problem_desc}

Starter Code:
```python
{starter_code}
```

Example:
- Input: {example.get('input', '')}
- Output: {example.get('output', '')}
- Reasoning: {example.get('reasoning', '')}

Test Cases:
{test_info}

Generate a complete, working solution:"""
                }
            ],
            max_tokens=500,
            temperature=0.3
        )
        
        solution = response.choices[0].message.content
        
        # Clean up the response (remove markdown code blocks if present)
        if solution:
            solution = solution.strip()
            if solution.startswith("```python"):
                solution = solution[9:]
            elif solution.startswith("```"):
                solution = solution[3:]
            if solution.endswith("```"):
                solution = solution[:-3]
            return solution.strip()
        
        return None
    
    except Exception as e:
        print(f"[Solution Generator] Error: {e}")
        return None
