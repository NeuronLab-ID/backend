"""
AI-powered hint generator using OpenAI or GitHub Models.
"""
import os
import subprocess
from openai import OpenAI
from typing import Optional

AI_BACKEND = os.getenv("AI_BACKEND", "github")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def create_client() -> OpenAI:
    """
    Create AI client based on .env configuration.
    
    AI_BACKEND options:
    - "github": Uses GitHub Models API (free, requires `gh auth login`)
    - "openai": Uses OpenAI API (requires OPENAI_API_KEY)
    """
    if AI_BACKEND == "openai":
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set in .env")
        return OpenAI(api_key=OPENAI_API_KEY)
    
    else:  # github
        try:
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                timeout=5
            )
            token = result.stdout.strip()
            
            if not token:
                raise ValueError("GitHub token not found. Run: gh auth login")
            
            return OpenAI(
                api_key=token,
                base_url="https://models.inference.ai.azure.com"
            )
        except FileNotFoundError:
            raise ValueError("GitHub CLI not installed. Install from: https://cli.github.com/")
        except subprocess.TimeoutExpired:
            raise ValueError("Timeout getting GitHub token")


async def generate_hint(problem: dict, user_code: str, error: str) -> Optional[str]:
    """
    Generate a helpful hint based on the error.
    
    Rules:
    - Short hint (1-2 sentences)
    - Guide without giving away the solution
    - Focus on the error type and common fixes
    """
    try:
        client = create_client()
        
        # Build context
        problem_title = problem.get("title", "Unknown Problem")
        problem_desc = problem.get("description_decoded", problem.get("description", ""))[:500]
        
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """You are a helpful programming tutor. When a student's code has an error:
1. Give a SHORT hint (1-2 sentences max)
2. Guide them toward the solution without giving it away
3. Focus on the specific error type
4. Be encouraging

DO NOT:
- Give the full solution
- Write more than 2 sentences
- Be condescending"""
                },
                {
                    "role": "user",
                    "content": f"""Problem: {problem_title}
Description: {problem_desc}

Student's Code:
```python
{user_code[:1000]}
```

Error:
{error[:500]}

Give a short, helpful hint:"""
                }
            ],
            max_tokens=100,
            temperature=0.7
        )
        
        hint = response.choices[0].message.content
        return hint.strip() if hint else None
    
    except Exception as e:
        # Log error but don't fail the request
        print(f"[Hint Generator] Error: {e}")
        return None
