"""
OpenAI Provider - OpenAI API and GitHub Models integration.

Supports:
- OpenAI API (requires OPENAI_API_KEY)
- GitHub Models (requires `gh auth login`, uses Azure endpoint)
"""
import os
import subprocess
from typing import Optional
from loguru import logger

from openai import OpenAI

from .ai_provider_base import AIProvider


class OpenAIProvider(AIProvider):
    """OpenAI-compatible provider for AI generation."""
    
    def __init__(self, backend: str = "github", model: str = None):
        """
        Initialize OpenAI provider.
        
        Args:
            backend: "openai" or "github" (GitHub Models)
            model: Model name (default from env or gpt-4o-mini)
        """
        self.backend = backend
        self.model = model or os.getenv("AI_MODEL", "gpt-4o-mini")
        self._client: Optional[OpenAI] = None
    
    @property
    def name(self) -> str:
        return f"OpenAI ({self.backend})"
    
    def is_configured(self) -> bool:
        """Check if provider is properly configured."""
        if self.backend == "openai":
            return bool(os.getenv("OPENAI_API_KEY"))
        else:  # github
            try:
                result = subprocess.run(
                    ["gh", "auth", "token"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return bool(result.stdout.strip())
            except (FileNotFoundError, subprocess.TimeoutExpired):
                return False
    
    def get_client(self) -> OpenAI:
        """Get or create OpenAI client."""
        if self._client is None:
            self._client = self._create_client()
        return self._client
    
    def _create_client(self) -> OpenAI:
        """Create OpenAI client based on backend."""
        if self.backend == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set in .env")
            return OpenAI(api_key=api_key)
        
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
    
    async def generate_hint(self, problem: dict, user_code: str, error: str) -> Optional[str]:
        """Generate hint using OpenAI API."""
        try:
            import asyncio
            
            client = self.get_client()
            problem_title = problem.get("title", "Unknown Problem")
            problem_desc = problem.get("description_decoded", problem.get("description", ""))[:500]
            
            logger.debug(f"[OpenAI] Generating hint for: {problem_title}")
            
            def _blocking_call():
                return client.chat.completions.create(
                    model=self.model,
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
                    max_tokens=200,
                    temperature=0.7
                )
            
            response = await asyncio.to_thread(_blocking_call)
            hint = response.choices[0].message.content
            logger.success(f"[OpenAI] Generated hint")
            return hint.strip() if hint else None
            
        except Exception as e:
            logger.error(f"[OpenAI] Error: {e}")
            return None
    
    async def generate_reasoning(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """Generate reasoning using OpenAI API."""
        try:
            import asyncio
            
            client = self.get_client()
            
            logger.debug(f"[OpenAI] Generating reasoning with {self.model}")
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            def _blocking_call():
                return client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=3000,
                    temperature=0.3
                )
            
            response = await asyncio.to_thread(_blocking_call)
            result = response.choices[0].message.content or ""
            logger.success(f"[OpenAI] Generated {len(result)} chars")
            return result
            
        except Exception as e:
            logger.error(f"[OpenAI] Error: {e}")
            return None
