# Math Sample Service
# Handles AI-powered math sample generation

from app.services.hint_generator import create_client, AI_MODEL
from app.prompts.math_prompts import (
    get_sample_prompt,
    get_retry_prompt,
    get_system_prompt,
    get_retry_system_prompt,
)
from app.utils.json_utils import try_parse_json, clean_ai_response


class MathSampleService:
    """Service for generating worked math examples using AI."""
    
    def __init__(self):
        self.client = create_client()
    
    async def generate_sample(
        self,
        formula_name: str,
        formula_latex: str,
        difficulty: str = "easy"
    ) -> dict:
        """Generate a worked math example.
        
        Args:
            formula_name: Name of the formula
            formula_latex: LaTeX representation
            difficulty: easy, medium, or hard
            
        Returns:
            Dict with success status, steps, and result
        """
        try:
            prompt = get_sample_prompt(formula_name, formula_latex, difficulty)
            
            response = self.client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {"role": "system", "content": get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.9  # Higher for randomness
            )
            
            content = clean_ai_response(response.choices[0].message.content)
            data = try_parse_json(content)
            
            if data:
                return {
                    "success": True,
                    "steps": data.get("steps", []),
                    "result": data.get("result", "")
                }
            
            # Retry with simpler prompt
            return await self._retry_generation(formula_name, formula_latex)
            
        except Exception as e:
            print(f"[Math Sample] Error: {e}")
            return {
                "success": False,
                "error": str(e),
                "steps": [],
                "result": ""
            }
    
    async def _retry_generation(self, formula_name: str, formula_latex: str) -> dict:
        """Retry generation with a simpler prompt.
        
        Args:
            formula_name: Name of the formula
            formula_latex: LaTeX representation
            
        Returns:
            Dict with success status, steps, and result
        """
        print("[Math Sample] Retrying with simpler prompt...")
        
        try:
            retry_prompt = get_retry_prompt(formula_name, formula_latex)
            
            response = self.client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {"role": "system", "content": get_retry_system_prompt()},
                    {"role": "user", "content": retry_prompt}
                ],
                max_tokens=800,
                temperature=0.7
            )
            
            content = clean_ai_response(response.choices[0].message.content)
            data = try_parse_json(content)
            
            if data:
                return {
                    "success": True,
                    "steps": data.get("steps", []),
                    "result": data.get("result", "")
                }
            
            print(f"[Math Sample] Failed after retry: {content[:200]}...")
            return {
                "success": False,
                "error": "Failed to parse AI response. Please try again.",
                "steps": [],
                "result": ""
            }
            
        except Exception as e:
            print(f"[Math Sample] Retry error: {e}")
            return {
                "success": False,
                "error": str(e),
                "steps": [],
                "result": ""
            }
