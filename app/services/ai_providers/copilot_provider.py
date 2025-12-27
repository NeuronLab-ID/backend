"""
Copilot CLI Provider - GitHub Copilot CLI integration.

Uses the `copilot` command-line tool for AI generation.
"""
import os
import subprocess
from typing import Optional
from loguru import logger

from .ai_provider_base import AIProvider


class CopilotProvider(AIProvider):
    """GitHub Copilot CLI provider for AI generation."""
    
    def __init__(self, model: str = None):
        self.model = model or os.getenv("COPILOT_MODEL", "gpt-4.1")
    
    @property
    def name(self) -> str:
        return "Copilot"
    
    def is_configured(self) -> bool:
        """Check if Copilot CLI is available."""
        try:
            result = subprocess.run(
                ["copilot", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    async def generate_hint(self, problem: dict, user_code: str, error: str) -> Optional[str]:
        """Generate hint using Copilot CLI."""
        problem_title = problem.get("title", "Unknown Problem")
        
        prompt = f"""This Python code for "{problem_title}" has an error. Give a SHORT hint (1-2 sentences) to help fix it without giving the solution:

Code:
{user_code[:800]}

Error:
{error[:300]}

Give only a short hint (1-2 sentences), nothing else:"""
        
        result = await self._run_copilot(prompt)
        
        if result:
            sentences = result.split('. ')
            return '. '.join(sentences[:2]) + ('.' if sentences and not sentences[0].endswith('.') else '')
        
        return None
    
    async def generate_reasoning(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """Generate reasoning using Copilot CLI."""
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        return await self._run_copilot(full_prompt)
    
    async def _run_copilot(self, prompt: str) -> Optional[str]:
        """Execute Copilot CLI command."""
        try:
            escaped_prompt = prompt.replace('"', '\\"').replace("'", "\\'")
            
            cmd = f'copilot -p "{escaped_prompt}" -s --allow-all-tools'
            if self.model:
                cmd += f' --model {self.model}'
            
            logger.debug(f"[Copilot] Generating with model: {self.model}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=240,
                shell=True
            )
            
            if result.returncode != 0:
                logger.error(f"[Copilot] Error: {result.stderr[:200]}")
                return None
            
            logger.success(f"[Copilot] Generated {len(result.stdout)} chars")
            return result.stdout.strip()
            
        except FileNotFoundError:
            logger.error("[Copilot] Copilot CLI not installed")
            return None
        except subprocess.TimeoutExpired:
            logger.warning("[Copilot] Timeout")
            return None
        except Exception as e:
            logger.error(f"[Copilot] Error: {e}")
            return None
