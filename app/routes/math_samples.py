"""
AI-powered math sample generator routes.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.routes.auth import get_current_user
from app.services.hint_generator import create_client

router = APIRouter()

AI_MODEL = "gpt-4o-mini"


class MathSampleRequest(BaseModel):
    formula_name: str
    formula_latex: str
    difficulty: str = "easy"  # easy, medium, hard


# Difficulty settings
DIFFICULTY_CONFIG = {
    "easy": {"steps": "2-3", "values": "single digits (1-9)", "elements": "2"},
    "medium": {"steps": "3-5", "values": "integers (-10 to 10)", "elements": "3"},
    "hard": {"steps": "5-7", "values": "any integers or decimals", "elements": "4-5"}
}


@router.post("/generate-sample")
async def generate_math_sample(request: MathSampleRequest, user_id: int = Depends(get_current_user)):
    """Generate a worked math example using AI."""
    try:
        client = create_client()
        
        # Get difficulty config
        config = DIFFICULTY_CONFIG.get(request.difficulty.lower(), DIFFICULTY_CONFIG["easy"])
        
        prompt = f"""Generate a worked example for this mathematical concept.

Formula Name: {request.formula_name}
Formula (LaTeX): {request.formula_latex}

Requirements (Difficulty: {request.difficulty.upper()}):
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

        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a math tutor. Generate simple, clear worked examples with random integer values. Always respond with valid JSON only, no markdown code blocks."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=500,
            temperature=0.9  # Higher for randomness
        )
        
        content = response.choices[0].message.content.strip()
        
        # Parse JSON response with multiple fallback strategies
        import json
        import re
        
        # Remove markdown code blocks if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        
        # Try to fix common JSON issues
        def try_parse_json(text):
            """Try multiple strategies to parse potentially malformed JSON."""
            # Strategy 1: Direct parse
            try:
                return json.loads(text)
            except:
                pass
            
            # Strategy 2: Fix unescaped backslashes in LaTeX
            try:
                fixed = text.replace("\\", "\\\\")
                # But keep valid escape sequences
                fixed = fixed.replace("\\\\n", "\\n").replace("\\\\t", "\\t")
                fixed = fixed.replace('\\\\"', '\\"')
                return json.loads(fixed)
            except:
                pass
            
            # Strategy 3: Extract JSON object using regex
            try:
                match = re.search(r'\{[^{}]*"steps"\s*:\s*\[[^\]]*\][^{}]*"result"\s*:[^}]*\}', text, re.DOTALL)
                if match:
                    return json.loads(match.group())
            except:
                pass
            
            # Strategy 4: Try to reconstruct from partial content
            try:
                # Find steps array
                steps_match = re.search(r'"steps"\s*:\s*\[(.*?)\]', text, re.DOTALL)
                result_match = re.search(r'"result"\s*:\s*"([^"]*)"', text)
                
                if steps_match:
                    steps_content = steps_match.group(1)
                    # Extract individual strings
                    steps = re.findall(r'"([^"]*(?:\\"[^"]*)*)"', steps_content)
                    result = result_match.group(1) if result_match else ""
                    return {"steps": steps, "result": result}
            except:
                pass
            
            return None
        
        data = try_parse_json(content)
        
        if data:
            return {
                "success": True,
                "steps": data.get("steps", []),
                "result": data.get("result", "")
            }
        
        # RETRY with simpler prompt - let AI decide steps
        print(f"[Math Sample] Retrying with simpler prompt...")
        retry_prompt = f"""Generate a simple worked math example for: {request.formula_name}

Formula: {request.formula_latex}

Use small numbers. Show whatever steps are needed. Use $...$ for math.

Return ONLY valid JSON:
{{"steps": ["step 1 text", "step 2 text"], "result": "final answer"}}"""

        retry_response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "Return only valid JSON. No markdown."},
                {"role": "user", "content": retry_prompt}
            ],
            max_tokens=800,
            temperature=0.7
        )
        
        retry_content = retry_response.choices[0].message.content.strip()
        if retry_content.startswith("```"):
            retry_content = retry_content.split("```")[1]
            if retry_content.startswith("json"):
                retry_content = retry_content[4:]
        retry_content = retry_content.strip()
        
        data = try_parse_json(retry_content)
        
        if data:
            return {
                "success": True,
                "steps": data.get("steps", []),
                "result": data.get("result", "")
            }
        
        print(f"[Math Sample] Failed after retry: {retry_content[:200]}...")
        return {
            "success": False,
            "error": "Failed to parse AI response. Please try again.",
            "steps": [],
            "result": ""
        }
    
    except Exception as e:
        print(f"[Math Sample] Error: {e}")
        return {
            "success": False,
            "error": str(e),
            "steps": [],
            "result": ""
        }
