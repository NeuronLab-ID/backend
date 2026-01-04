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
    
    def _parse_sse_response(self, response) -> tuple[Optional[str], Optional[str]]:
        """Parse SSE streaming response and extract text + thread slug.
        
        Returns:
            tuple: (answer_text, thread_url_slug)
        """
        import json
        
        full_text = ""
        thread_slug = None
        event_count = 0
        
        for line in response.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith("data: "):
                    try:
                        data = json.loads(decoded[6:])
                        event_count += 1
                        
                        # Extract thread_url_slug for later REST fetch
                        if "thread_url_slug" in data and data["thread_url_slug"]:
                            thread_slug = data["thread_url_slug"]
                        
                        # Collect answer text from markdown blocks
                        blocks = data.get("blocks", [])
                        for block in blocks:
                            intended_usage = block.get("intended_usage", "")
                            
                            # Look for any markdown blocks with answers
                            if "ask_text" in intended_usage:
                                markdown_block = block.get("markdown_block", {})
                                if isinstance(markdown_block, dict):
                                    answer = markdown_block.get("answer", "")
                                    if answer and len(answer) > len(full_text):
                                        full_text = answer
                                        
                    except json.JSONDecodeError:
                        continue
        
        logger.info(f"[Perplexity] SSE: {event_count} events, {len(full_text)} chars, slug: {bool(thread_slug)}")
        return (full_text if full_text else None, thread_slug)
    
    def _fetch_thread_content(self, thread_slug: str, cookies: dict, headers: dict, timeout: int) -> Optional[dict]:
        """Fetch complete thread data from REST API after SSE completes.
        
        Args:
            thread_slug: The thread URL slug from SSE response
            cookies: Request cookies
            headers: Request headers
            timeout: Request timeout
            
        Returns:
            dict: Complete thread JSON response or None
        """
        import json
        try:
            from curl_cffi import requests as cffi_requests
        except ImportError:
            logger.error("[Perplexity] curl_cffi not installed")
            return None
        
        # Build REST API URL with all supported block use cases
        base_url = f"https://www.perplexity.ai/rest/thread/{thread_slug}"
        params = {
            "with_parent_info": "true",
            "with_schematized_response": "true",
            "version": "2.18",
            "source": "default",
            "limit": "10",
            "offset": "0",
            "from_first": "true",
        }
        # Add all supported block use cases
        block_params = "&".join([f"supported_block_use_cases={b}" for b in PERPLEXITY_SUPPORTED_BLOCKS])
        url = f"{base_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}&{block_params}"
        
        # Modify headers for JSON response
        rest_headers = headers.copy()
        rest_headers["accept"] = "application/json"
        
        try:
            resp = cffi_requests.get(
                url,
                headers=rest_headers,
                cookies=cookies,
                impersonate="edge",
                timeout=timeout
            )
            
            if resp.status_code != 200:
                logger.warning(f"[Perplexity] Thread fetch failed: HTTP {resp.status_code}")
                return None
            
            data = resp.json()
            logger.info(f"[Perplexity] Thread fetch success: {len(str(data))} bytes")
            return data
            
        except Exception as e:
            logger.warning(f"[Perplexity] Thread fetch error: {str(e)[:100]}")
            return None
    
    def _parse_thread_response(self, thread_data: dict) -> Optional[str]:
        """Parse complete thread response with inline images.
        
        The thread response has entries[].blocks[] with:
        - intended_usage: 'ask_text_N_markdown' for text sections
        - intended_usage: 'ask_text_N_images' for images linked to section N
        
        Images are inserted inline after their corresponding markdown sections.
        """
        import re
        
        if not thread_data:
            return None
        
        entries = thread_data.get("entries", [])
        if not entries:
            return None
        
        # Use the first/latest entry
        entry = entries[0]
        blocks = entry.get("blocks", [])
        
        # Track markdown sections and their images by section number
        markdown_sections = {}  # {section_num: text}
        section_images = {}     # {section_num: [(url, name), ...]}
        standalone_images = []  # Images from CODE blocks without section
        
        for block in blocks:
            intended_usage = block.get("intended_usage", "")
            
            # Parse intended_usage to extract section number
            section_match = re.match(r'ask_text_(\d+)_(markdown|images)', intended_usage)
            
            if section_match:
                section_num = int(section_match.group(1))
                block_type = section_match.group(2)
                
                if block_type == "markdown":
                    markdown_block = block.get("markdown_block", {})
                    if isinstance(markdown_block, dict):
                        answer = markdown_block.get("answer", "")
                        if answer:
                            if section_num not in markdown_sections or len(answer) > len(markdown_sections[section_num]):
                                markdown_sections[section_num] = answer
                        
                        # Check for media_items in markdown_block
                        media_items = markdown_block.get("media_items", [])
                        if media_items:
                            logger.debug(f"[Perplexity] Section {section_num} markdown_block has {len(media_items)} media_items")
                        for item in media_items:
                            if item.get("medium") == "image":
                                img_url = item.get("image") or item.get("url")
                                img_name = item.get("name", "Generated Visualization")
                                logger.info(f"[Perplexity] 📷 Section {section_num} markdown image: {img_name[:40]}... URL: {img_url[:80] if img_url else 'None'}...")
                                if img_url:
                                    if section_num not in section_images:
                                        section_images[section_num] = []
                                    if img_url not in [u for u, n in section_images[section_num]]:
                                        section_images[section_num].append((img_url, img_name))
                
                elif block_type == "images":
                    # Extract images from inline_entity_block
                    inline_entity = block.get("inline_entity_block", {})
                    media_block = inline_entity.get("media_block", {})
                    media_items = media_block.get("media_items", [])
                    
                    if media_items:
                        logger.debug(f"[Perplexity] Section {section_num} inline_entity_block has {len(media_items)} media_items")
                    for item in media_items:
                        if item.get("medium") == "image":
                            img_url = item.get("image") or item.get("url")
                            img_name = item.get("name", "Code Interpreter Output")
                            logger.info(f"[Perplexity] 📷 Section {section_num} inline image: {img_name[:40]}... URL: {img_url[:80] if img_url else 'None'}...")
                            if img_url:
                                if section_num not in section_images:
                                    section_images[section_num] = []
                                if img_url not in [u for u, n in section_images[section_num]]:
                                    section_images[section_num].append((img_url, img_name))
            
            # Handle pro_search_steps for CODE block charts  
            if intended_usage == "pro_search_steps":
                plan_block = block.get("plan_block", {})
                steps = plan_block.get("steps", [])
                for step in steps:
                    if step.get("step_type") == "CODE":
                        assets = step.get("assets", [])
                        if assets:
                            logger.debug(f"[Perplexity] CODE step has {len(assets)} assets")
                        for asset in assets:
                            if asset.get("asset_type") == "CHART":
                                chart = asset.get("chart", {})
                                chart_url = chart.get("url") or chart.get("svg_url")
                                logger.info(f"[Perplexity] 📷 CODE chart: URL: {chart_url[:80] if chart_url else 'None'}...")
                                if chart_url and chart_url not in [u for u, n in standalone_images]:
                                    standalone_images.append((chart_url, "Generated Chart"))
        
        # Build final output with inline images
        full_text = ""
        
        if markdown_sections:
            sorted_sections = sorted(markdown_sections.keys())
            
            for section_num in sorted_sections:
                section_text = markdown_sections[section_num]
                full_text += section_text
                
                # Insert images for this section inline
                if section_num in section_images:
                    full_text += "\n\n"
                    for img_url, img_name in section_images[section_num]:
                        full_text += f"![{img_name}]({img_url})\n\n"
                    logger.debug(f"[Perplexity] Inserted {len(section_images[section_num])} image(s) after section {section_num}")
                
                full_text += "\n\n"
        
        # Handle orphan images: sections with images but no corresponding markdown text
        orphan_images = []
        for section_num, images in section_images.items():
            if section_num not in markdown_sections:
                orphan_images.extend(images)
                logger.debug(f"[Perplexity] Section {section_num} has {len(images)} orphan image(s) (no text)")
        
        # Combine standalone and orphan images
        all_standalone = standalone_images + orphan_images
        
        # Append standalone images at the end
        if all_standalone:
            full_text += "\n\n---\n\n### Generated Visualizations\n\n"
            for url, name in all_standalone:
                full_text += f"![{name}]({url})\n\n"
            logger.info(f"[Perplexity] Appended {len(all_standalone)} visualization(s) ({len(standalone_images)} standalone, {len(orphan_images)} orphan)")
        
        # Log stats
        if full_text:
            total_images = sum(len(imgs) for imgs in section_images.values()) + len(standalone_images)
            word_count = len(full_text.split())
            line_count = full_text.count('\n') + 1
            latex_blocks = full_text.count('\\[') + full_text.count('$$')
            inline_math = full_text.count('\\(') + full_text.count('$') - latex_blocks
            headers = full_text.count('###') + full_text.count('##')
            est_tokens = int(len(full_text) / 4)
            
            logger.info(
                f"[Perplexity] Thread stats: "
                f"~{est_tokens:,} tokens | "
                f"{len(full_text):,} chars | "
                f"{word_count:,} words | "
                f"{total_images} images"
            )
        
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
            # Step 1: SSE request to get answer and thread slug
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
            
            sse_text, thread_slug = self._parse_sse_response(resp)
            
            # Step 2: If we got a thread slug, fetch complete thread for inline images
            if thread_slug:
                logger.info(f"[{log_prefix}] Fetching thread: {thread_slug}")
                thread_data = self._fetch_thread_content(thread_slug, cookies, headers, timeout)
                
                if thread_data:
                    thread_result = self._parse_thread_response(thread_data)
                    if thread_result:
                        return thread_result
                    else:
                        logger.warning(f"[{log_prefix}] Thread parse failed, using SSE text")
                else:
                    logger.warning(f"[{log_prefix}] Thread fetch failed, using SSE text")
            
            # Fallback to SSE text if thread fetch/parse failed
            return sse_text
        
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
