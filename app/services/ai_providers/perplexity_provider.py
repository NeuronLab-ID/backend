"""
Perplexity Provider - Perplexity AI integration.

Supports:
- pplx_alpha: Deep research model for web references
- claude45sonnetthinking: High-quality reasoning model

Uses curl_cffi for browser TLS fingerprint impersonation.
Requires browser cookies for authentication.
"""
import os
import asyncio
from typing import Optional
from loguru import logger

from .ai_provider_base import AIProvider, SearchProvider


# Constants
PERPLEXITY_URL = "https://www.perplexity.ai/rest/sse/perplexity_ask"

# Model options
PERPLEXITY_MODEL_SEARCH = "pplx_alpha"           # Deep research
PERPLEXITY_MODEL_REASONING = "claude45sonnetthinking"  # Deep reasoning

# Full supported block use cases from latest API
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


class PerplexityProvider(AIProvider, SearchProvider):
    """
    Perplexity AI provider with search and reasoning capabilities.
    
    Uses different models for different tasks:
    - pplx_alpha: Deep research with web references
    - claude45sonnetthinking: Deep reasoning with step-by-step math
    """
    
    def __init__(self):
        self.session_token = os.getenv("PERPLEXITY_SESSION_TOKEN", "")
        self.cf_clearance = os.getenv("PERPLEXITY_CF_CLEARANCE", "")
    
    @property
    def name(self) -> str:
        return "Perplexity"
    
    def is_configured(self) -> bool:
        """Check if browser cookies are configured."""
        return bool(self.session_token and self.cf_clearance)
    
    # ========================================
    # AIProvider Interface
    # ========================================
    
    async def generate_hint(self, problem: dict, user_code: str, error: str) -> Optional[str]:
        """Generate hint using Perplexity (uses pplx_alpha for speed)."""
        problem_title = problem.get("title", "Unknown Problem")
        
        prompt = f"""This Python code for "{problem_title}" has an error. Give a SHORT hint (1-2 sentences):

Code:
{user_code[:500]}

Error:
{error[:200]}

Hint:"""
        
        result = await self._request(
            prompt, 
            model=PERPLEXITY_MODEL_SEARCH,
            sources=["web"], 
            timeout=60, 
            log_prefix="Hint"
        )
        
        if result:
            sentences = result.split('. ')
            return '. '.join(sentences[:2])
        
        return None
    
    async def generate_reasoning(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """Generate reasoning using Claude 4.5 Sonnet Thinking."""
        full_prompt = f"""{system_prompt}

{prompt}

Provide a detailed step-by-step mathematical explanation with:
1. Clear formulas using LaTeX ($...$ inline, $$...$$ display)
2. Real-world example with actual data
3. Step-by-step computation showing all intermediate values
4. Tables in markdown format when presenting data"""

        logger.info(f"Generating reasoning with Claude 4.5 Sonnet Thinking")
        return await self._request(
            full_prompt, 
            model=PERPLEXITY_MODEL_REASONING,
            sources=["web", "scholar"], 
            timeout=900, 
            log_prefix="Reasoning"
        )
    
    # ========================================
    # SearchProvider Interface
    # ========================================
    
    async def search(self, topic: str, context: str = "") -> Optional[str]:
        """Search for information using Perplexity (uses pplx_alpha)."""
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

Include citations for your sources."""

        logger.info(f"Searching with pplx_alpha: {topic[:50]}...")
        return await self._request(
            search_prompt, 
            model=PERPLEXITY_MODEL_SEARCH,
            sources=["web", "scholar", "edgar"], 
            timeout=900, 
            log_prefix="Search"
        )
    
    # ========================================
    # Private Helpers
    # ========================================
    
    def _get_cookies(self, request_id: str) -> dict:
        """Build cookies for request."""
        import uuid
        return {
            "pplx.visitor-id": os.getenv("PERPLEXITY_VISITOR_ID", str(uuid.uuid4())),
            "__Secure-next-auth.session-token": self.session_token,
            "cf_clearance": self.cf_clearance,
            "__cf_bm": os.getenv("PERPLEXITY_CF_BM", ""),
            "pplx.session-id": os.getenv("PERPLEXITY_SESSION_ID", str(uuid.uuid4())),
        }
    
    def _get_headers(self, request_id: str) -> dict:
        """Build headers for request."""
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
    
    def _build_payload(self, query: str, model: str, sources: list) -> dict:
        """Build API payload with model selection."""
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
                "model_preference": model,
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
    
    def _parse_sse_response(self, response) -> Optional[str]:
        """Parse SSE streaming response and extract final markdown answer.
        
        Perplexity's SSE format uses:
        - blocks[].markdown_block.answer where intended_usage is 'ask_text' or 'ask_text_0_markdown'
        - The final message has text_completed: true and final_sse_message: true
        """
        import json
        
        full_text = ""
        event_count = 0
        
        for line in response.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith("data: "):
                    try:
                        data = json.loads(decoded[6:])
                        event_count += 1
                        
                        # Check if this is the final message with text_completed
                        text_completed = data.get("text_completed", False)
                        
                        # Look for answer in blocks[].markdown_block
                        blocks = data.get("blocks", [])
                        for block in blocks:
                            intended_usage = block.get("intended_usage", "")
                            
                            # Look for markdown blocks with the final answer
                            # The final SSE message contains the complete answer in markdown_block.answer
                            # We only use this and ignore diff_block patches to avoid duplicates
                            if "ask_text" in intended_usage or intended_usage == "ask_text_0_markdown":
                                markdown_block = block.get("markdown_block", {})
                                if isinstance(markdown_block, dict):
                                    answer = markdown_block.get("answer", "")
                                    # Only use if this is a longer/more complete version
                                    if answer and len(answer) > len(full_text):
                                        full_text = answer
                                        logger.debug(f"[Perplexity] Found answer in {intended_usage}, length: {len(answer)}")
                        
                        # Legacy fallback: check for direct text/answer fields
                        if not full_text:
                            if "text" in data and isinstance(data["text"], str):
                                full_text = data["text"]
                            elif "answer" in data and isinstance(data["answer"], str):
                                full_text = data["answer"]
                                
                    except json.JSONDecodeError:
                        continue
        
        # Enhanced logging with detailed stats
        if full_text:
            word_count = len(full_text.split())
            line_count = full_text.count('\n') + 1
            latex_blocks = full_text.count('\\[') + full_text.count('$$')
            inline_math = full_text.count('\\(') + full_text.count('$') - latex_blocks  
            headers = full_text.count('###') + full_text.count('##')
            # Estimate tokens: ~4 chars per token for English, ~1.3 tokens per word
            est_tokens = int(len(full_text) / 4)
            
            logger.info(
                f"[Perplexity] Response stats: "
                f"{event_count} SSE events | "
                f"~{est_tokens:,} tokens | "
                f"{len(full_text):,} chars | "
                f"{word_count:,} words | "
                f"{line_count} lines | "
                f"{latex_blocks} display math | "
                f"{max(0, inline_math)} inline math | "
                f"{headers} headers"
            )
        else:
            logger.warning(f"[Perplexity] No answer extracted from {event_count} SSE events")
        
        return full_text if full_text else None
    
    async def _request(self, query: str, model: str, sources: list, timeout: int, log_prefix: str) -> Optional[str]:
        """Make request to Perplexity API with specified model."""
        import uuid
        
        try:
            from curl_cffi import requests as cffi_requests
        except ImportError:
            logger.error(f"[{log_prefix}] curl_cffi not installed. Run: pip install curl_cffi")
            return None
        
        if not self.is_configured():
            logger.warning(f"[{log_prefix}] No browser cookies configured")
            return None
        
        request_id = str(uuid.uuid4())
        cookies = self._get_cookies(request_id)
        headers = self._get_headers(request_id)
        payload = self._build_payload(query, model, sources)
        
        logger.debug(f"[{log_prefix}] Using model: {model}")
        
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
                logger.error(f"[{log_prefix}] 403 Forbidden - cookies may have expired")
                return None
            
            if resp.status_code != 200:
                logger.error(f"[{log_prefix}] HTTP {resp.status_code}")
                return None
            
            return self._parse_sse_response(resp)
        
        try:
            result = await asyncio.to_thread(_blocking_request)
            if result:
                logger.success(f"[{log_prefix}] Complete, received {len(result)} chars")
            else:
                logger.warning(f"[{log_prefix}] No answer text found")
            return result
        except Exception as e:
            logger.error(f"[{log_prefix}] Error: {str(e)[:100]}")
            return None
