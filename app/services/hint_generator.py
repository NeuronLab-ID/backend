"""
AI-powered hint generator using OpenAI, GitHub Models, or GitHub Copilot CLI.

NOTE: This module is maintained for backward compatibility.
New code should use the provider classes directly:
- from app.services.ai_providers import get_provider, get_search_provider
- from app.services.ai_providers import PerplexityProvider
- from app.services.ai_providers import OpenAIProvider
- from app.services.ai_providers import CopilotProvider
"""
import os
import subprocess
from openai import OpenAI
from typing import Optional, Union
from loguru import logger

AI_BACKEND = os.getenv("AI_BACKEND", "github")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
COPILOT_MODEL = os.getenv("COPILOT_MODEL", "gpt-4.1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")

# Log the active backend on module load
logger.info(f"AI Backend: {AI_BACKEND} | Model: {COPILOT_MODEL if AI_BACKEND == 'copilot' else AI_MODEL}")


def create_client() -> Optional[OpenAI]:
    """
    Create AI client based on .env configuration.
    
    AI_BACKEND options:
    - "github": Uses GitHub Models API (free, requires `gh auth login`)
    - "openai": Uses OpenAI API (requires OPENAI_API_KEY)
    - "copilot": Uses GitHub Copilot CLI (for hints only, requires Copilot CLI)
    """
    if AI_BACKEND == "copilot":
        # Copilot CLI doesn't use OpenAI client - return None for hint generation
        return None
    
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


def create_client_for_reasoning() -> Optional[OpenAI]:
    """
    Create AI client for reasoning generation.
    
    Returns None for copilot backend - reasoning should use generate_reasoning_copilot() instead.
    """
    if AI_BACKEND == "copilot":
        # Return None - the caller should use generate_reasoning_copilot() instead
        return None
    
    # For openai and github, use the normal client
    return create_client()


async def search_with_perplexity(topic: str, context: str = "") -> Optional[str]:
    """
    Search for web references using Perplexity AI with pplx_alpha (fast search).
    
    Args:
        topic: The topic to search for (e.g., "Binomial Distribution formula")
        context: Additional context for the search
    
    Returns:
        Search results with citations and real-world examples, or None on error
    """
    # Build enhanced search prompt
    search_prompt = f"""Search for educational resources and explanations about: {topic}

{f'Context: {context}' if context else ''}

Provide:
1. **Clear mathematical definition and formulas** with proper LaTeX notation
2. **Step-by-step explanation** of how the algorithm/formula works
3. **Real-world example with actual data** - Use a concrete, relatable scenario such as:
   - Weather classification (Sunny/Rainy → Play Tennis Yes/No)
   - Medical diagnosis (Symptoms → Disease prediction)
   - Spam detection (Email features → Spam/Not Spam)
   
   For the real-world example:
   - Show a small dataset (5-10 rows) with descriptive column names
   - Walk through the calculation step-by-step with actual numbers
   - Highlight how each formula parameter maps to real values

Include citations for your sources."""

    print(f"[Perplexity] Searching with pplx_alpha: {topic}")
    return await _perplexity_request(search_prompt, model=PERPLEXITY_MODEL_SEARCH, sources=["web", "scholar", "edgar"], timeout=90, log_prefix="Perplexity Search")


async def generate_reasoning_with_perplexity(prompt: str, system_context: str = "") -> Optional[str]:
    """
    Generate step reasoning using Perplexity AI with Claude 4.5 Sonnet Thinking.
    
    Args:
        prompt: The reasoning prompt (step context, formulas, examples)
        system_context: Additional system context for the reasoning
    
    Returns:
        Generated reasoning text or None on error
    """
    # Build the full prompt with system context
    full_prompt = f"""{system_context}

{prompt}

Provide a detailed step-by-step mathematical explanation with:
1. Clear formulas using LaTeX ($...$ inline, $$...$$ display)
2. Real-world example with actual data
3. Step-by-step computation showing all intermediate values
4. Tables in markdown format when presenting data"""

    print(f"[Perplexity Reasoning] Generating with Claude 4.5 Sonnet Thinking...")
    return await _perplexity_request(full_prompt, model=PERPLEXITY_MODEL_REASONING, sources=["web", "scholar"], timeout=120, log_prefix="Perplexity Reasoning")


# ========================================
# Perplexity Client Helpers - DRY Refactored
# ========================================

# Common constants
PERPLEXITY_URL = "https://www.perplexity.ai/rest/sse/perplexity_ask"
PERPLEXITY_MODEL_SEARCH = "pplx_alpha"  # Fast search
PERPLEXITY_MODEL_REASONING = "claude45sonnetthinking"  # Deep reasoning
PERPLEXITY_SUPPORTED_BLOCKS = [
    "answer_modes", "media_items", "knowledge_cards", "inline_entity_cards",
    "place_widgets", "finance_widgets", "prediction_market_widgets",
    "sports_widgets", "flight_status_widgets", "news_widgets",
    "shopping_widgets", "jobs_widgets", "search_result_widgets",
    "inline_images", "inline_assets", "placeholder_cards", "diff_blocks",
    "inline_knowledge_cards", "entity_group_v2", "refinement_filters",
    "canvas_mode", "maps_preview", "answer_tabs", "price_comparison_widgets",
    "preserve_latex", "in_context_suggestions"
]


def _get_perplexity_cookies(request_id: str) -> dict:
    """Build cookies for Perplexity request (DRY helper)."""
    import uuid
    return {
        "pplx.visitor-id": os.getenv("PERPLEXITY_VISITOR_ID", str(uuid.uuid4())),
        "__Secure-next-auth.session-token": os.getenv("PERPLEXITY_SESSION_TOKEN", ""),
        "cf_clearance": os.getenv("PERPLEXITY_CF_CLEARANCE", ""),
        "__cf_bm": os.getenv("PERPLEXITY_CF_BM", ""),
        "pplx.session-id": os.getenv("PERPLEXITY_SESSION_ID", str(uuid.uuid4())),
    }


def _get_perplexity_headers(request_id: str) -> dict:
    """Build headers for Perplexity request (DRY helper)."""
    return {
        "accept": "text/event-stream",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
        "origin": "https://www.perplexity.ai",
        "referer": "https://www.perplexity.ai/?",
        "sec-ch-ua": '"Microsoft Edge";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0",
        "x-perplexity-request-reason": "perplexity-query-state-provider",
        "x-request-id": request_id,
    }


def _build_perplexity_payload(query: str, model: str, sources: list) -> dict:
    """Build API payload for Perplexity request (DRY helper)."""
    import uuid
    frontend_uuid = str(uuid.uuid4())
    context_uuid = str(uuid.uuid4())
    
    return {
        "params": {
            "attachments": [],
            "language": "en-US",
            "timezone": "Asia/Bangkok",
            "search_focus": "internet",
            "sources": sources,
            "search_recency_filter": None,
            "frontend_uuid": frontend_uuid,
            "mode": "copilot",
            "model_preference": model,  # Dynamic model selection
            "is_related_query": False,
            "is_sponsored": False,
            "frontend_context_uuid": context_uuid,
            "prompt_source": "user",
            "query_source": "home",
            "is_incognito": False,
            "time_from_first_type": 1000,
            "local_search_enabled": False,
            "use_schematized_api": True,
            "send_back_text_in_streaming_api": False,
            "supported_block_use_cases": PERPLEXITY_SUPPORTED_BLOCKS,
            "client_coordinates": None,
            "mentions": [],
            "dsl_query": query,
            "skip_search_enabled": True,
            "is_nav_suggestions_disabled": False,
            "source": "default",
            "always_search_override": False,
            "override_no_search": False,
            "should_ask_for_mcp_tool_confirmation": True,
            "browser_agent_allow_once_from_toggle": False,
            "force_enable_browser_agent": False,
            "supported_features": ["browser_agent_permission_banner_v1.1"],
            "version": "2.18"
        },
        "query_str": query
    }


def _parse_perplexity_sse(response) -> Optional[str]:
    """Parse SSE response from Perplexity (DRY helper)."""
    import json as json_module
    
    full_text = ""
    for line in response.iter_lines():
        if line:
            decoded = line.decode('utf-8')
            if decoded.startswith("data: "):
                try:
                    data = json_module.loads(decoded[6:])
                    if "text" in data:
                        full_text = data["text"]
                    elif "answer" in data:
                        full_text = data["answer"]
                    elif "content" in data:
                        full_text = data["content"]
                except json_module.JSONDecodeError:
                    continue
    
    return full_text if full_text else None


async def _perplexity_request(query: str, model: str, sources: list, timeout: int, log_prefix: str) -> Optional[str]:
    """
    Make a request to Perplexity API (core implementation).
    
    Args:
        query: The query/prompt to send
        model: Model to use (pplx_alpha for search, claude45sonnetthinking for reasoning)
        sources: List of sources to search
        timeout: Request timeout in seconds
        log_prefix: Prefix for log messages
    """
    import uuid
    
    try:
        from curl_cffi import requests as cffi_requests
    except ImportError:
        print(f"[{log_prefix}] ⚠️ curl_cffi not installed. Run: pip install curl_cffi")
        return None
    
    # Check cookies
    session_token = os.getenv("PERPLEXITY_SESSION_TOKEN", "")
    cf_clearance = os.getenv("PERPLEXITY_CF_CLEARANCE", "")
    
    if not session_token or not cf_clearance:
        print(f"[{log_prefix}] ⚠️ No browser cookies configured")
        return None
    
    request_id = str(uuid.uuid4())
    cookies = _get_perplexity_cookies(request_id)
    headers = _get_perplexity_headers(request_id)
    payload = _build_perplexity_payload(query, model, sources)
    
    print(f"[{log_prefix}] Using model: {model}")
    import asyncio
    
    def _blocking_request():
        resp = cffi_requests.post(
            PERPLEXITY_URL,
            headers=headers,
            cookies=cookies,
            json=payload,
            impersonate="edge",
            timeout=timeout,
            stream=True
        )
        
        if resp.status_code == 403:
            print(f"[{log_prefix}] ⚠️ 403 Forbidden - cookies may have expired")
            return None
        
        if resp.status_code != 200:
            print(f"[{log_prefix}] ⚠️ HTTP {resp.status_code}")
            return None
        
        return _parse_perplexity_sse(resp)
    
    try:
        result = await asyncio.to_thread(_blocking_request)
        if result:
            print(f"[{log_prefix}] Complete, received {len(result)} chars")
        else:
            print(f"[{log_prefix}] ⚠️ No answer text found")
        return result
    except Exception as e:
        print(f"[{log_prefix}] ⚠️ Error: {str(e)[:100]}")
        return None


async def generate_reasoning_copilot(prompt: str, system_prompt: str = "") -> Optional[str]:
    """
    Generate reasoning using GitHub Copilot CLI (copilot -p).
    
    Args:
        prompt: The prompt to send to Copilot
        system_prompt: Optional system context (prepended to prompt)
    
    Returns:
        Generated reasoning text or None on error
    """
    try:
        # Combine system and user prompt
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        # Escape quotes in prompt for shell
        escaped_prompt = full_prompt.replace('"', '\\"').replace("'", "\\'")
        
        # Build command as string for shell execution
        cmd = f'copilot -p "{escaped_prompt}" -s --allow-all-tools'
        print(cmd)
        
        if COPILOT_MODEL:
            cmd += f' --model {COPILOT_MODEL}'
        
        print(f"[Copilot CLI] Generating reasoning with model: {COPILOT_MODEL}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=240,  # Longer timeout for reasoning
            shell=True  # Use shell to find copilot in PATH
        )
        
        if result.returncode != 0:
            print(f"[Copilot CLI] Error: {result.stderr}")
            return None
        
        print(result)
        
        return result.stdout.strip()
        
    except FileNotFoundError:
        print("[Copilot CLI] Error: Copilot CLI not installed")
        return None
    except subprocess.TimeoutExpired:
        print("[Copilot CLI] Timeout")
        return None
    except Exception as e:
        print(f"[Copilot CLI] Error: {e}")
        return None


async def generate_hint_copilot(problem: dict, user_code: str, error: str) -> Optional[str]:
    """
    Generate hint using GitHub Copilot CLI (copilot -p).
    
    Supports models: gpt-5.1, gpt-5, gpt-4.1, claude-sonnet-4, gemini-3-pro-preview, etc.
    Set AI_MODEL in .env to choose (default: gpt-4.1)
    """
    try:
        problem_title = problem.get("title", "Unknown Problem")
        
        # Build prompt for Copilot CLI
        prompt = f"""This Python code for "{problem_title}" has an error. Give a SHORT hint (1-2 sentences) to help fix it without giving the solution:

Code:
{user_code[:800]}

Error:
{error[:300]}

Give only a short hint (1-2 sentences), nothing else:"""
        
        # Escape quotes for shell
        escaped_prompt = prompt.replace('"', '\\"').replace("'", "\\'")
        
        # Build command as string for shell execution
        cmd = f'copilot -p "{escaped_prompt}" -s --allow-all-tools'
        
        # Add model (use global COPILOT_MODEL from .env)
        if COPILOT_MODEL:
            cmd += f' --model {COPILOT_MODEL}'
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            shell=True
        )
        
        if result.returncode != 0:
            print(f"[Copilot CLI] Error: {result.stderr}")
            return None
        
        hint = result.stdout.strip()
        # Extract just the first 1-2 sentences
        if hint:
            sentences = hint.split('. ')
            return '. '.join(sentences[:2]) + ('.' if len(sentences) > 0 and not sentences[0].endswith('.') else '')
        return None
        
    except FileNotFoundError:
        raise ValueError("GitHub Copilot CLI not installed. Install from: https://githubnext.com/projects/copilot-cli")
    except subprocess.TimeoutExpired:
        print("[Copilot CLI] Timeout")
        return None
    except Exception as e:
        print(f"[Copilot CLI] Error: {e}")
        return None


async def generate_hint(problem: dict, user_code: str, error: str) -> Optional[str]:
    """
    Generate a helpful hint based on the error.
    
    Rules:
    - Short hint (1-2 sentences)
    - Guide without giving away the solution
    - Focus on the error type and common fixes
    """
    # Use Copilot CLI if configured
    if AI_BACKEND == "copilot":
        return await generate_hint_copilot(problem, user_code, error)
    
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

