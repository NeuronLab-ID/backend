"""
Debug script to capture and analyze Perplexity SSE response.
Run: python debug_perplexity_sse.py

Matches the exact implementation in perplexity_provider.py
"""
import os
import json
import uuid
from dotenv import load_dotenv

load_dotenv()

# Constants - EXACT MATCH with perplexity_provider.py
PERPLEXITY_URL = "https://www.perplexity.ai/rest/sse/perplexity_ask"
PERPLEXITY_MODEL_REASONING = "claude45sonnetthinking"
PERPLEXITY_MODEL_SEARCH = "pplx_alpha"

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

def get_cookies():
    """Get cookies from environment - matches perplexity_provider.py"""
    session_token = os.getenv("PERPLEXITY_SESSION_TOKEN", "")
    cf_clearance = os.getenv("PERPLEXITY_CF_CLEARANCE", "")
    return {
        "__Secure-next-auth.session-token": session_token,
        "cf_clearance": cf_clearance,
    }

def get_headers(request_id: str):
    """Build headers - matches perplexity_provider.py"""
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

def build_payload(query: str, model: str, sources: list):
    """Build payload - EXACT MATCH with perplexity_provider.py"""
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

def debug_sse_response():
    """Make a request and capture the full SSE response."""
    try:
        from curl_cffi import requests as cffi_requests
    except ImportError:
        print("ERROR: curl_cffi not installed. Run: pip install curl_cffi")
        return
    
    # Check cookies
    session_token = os.getenv("PERPLEXITY_SESSION_TOKEN", "")
    cf_clearance = os.getenv("PERPLEXITY_CF_CLEARANCE", "")
    
    print("=" * 60)
    print("COOKIE CHECK")
    print("=" * 60)
    print(f"  PERPLEXITY_SESSION_TOKEN: {'✓ SET' if session_token else '✗ MISSING'}")
    print(f"    Preview: ...{session_token[-20:]}" if session_token else "")
    print(f"  PERPLEXITY_CF_CLEARANCE: {'✓ SET' if cf_clearance else '✗ MISSING'}")
    print(f"    Preview: ...{cf_clearance[-20:]}" if cf_clearance else "")
    
    if not session_token or not cf_clearance:
        print("\n❌ Missing required cookies! Update your .env file.")
        return
    
    # Build request
    request_id = str(uuid.uuid4())
    cookies = get_cookies()
    headers = get_headers(request_id)
    
    # Test query
    query = "What is 2 + 2? Answer in one sentence."
    model = PERPLEXITY_MODEL_REASONING
    sources = ["web"]
    
    payload = build_payload(query, model, sources)
    
    print("\n" + "=" * 60)
    print("REQUEST DETAILS")
    print("=" * 60)
    print(f"URL: {PERPLEXITY_URL}")
    print(f"Model: {model}")
    print(f"Query: {query}")
    print(f"Request ID: {request_id}")
    
    print("\n" + "=" * 60)
    print("MAKING REQUEST...")
    print("=" * 60)
    
    try:
        resp = cffi_requests.post(
            PERPLEXITY_URL,
            headers=headers,
            cookies=cookies,
            json=payload,
            impersonate="edge",
            timeout=120,
            stream=True
        )
        
        print(f"Status Code: {resp.status_code}")
        
        if resp.status_code == 403:
            print("\n❌ 403 Forbidden - Cookies have expired!")
            print("Please update your cookies in .env file.")
            return
        
        if resp.status_code == 401:
            print("\n❌ 401 Unauthorized - Session token invalid!")
            return
        
        if resp.status_code != 200:
            print(f"\n❌ HTTP Error: {resp.status_code}")
            print(f"Response: {resp.text[:1000]}")
            return
        
        print("\n" + "=" * 60)
        print("SSE RESPONSE ANALYSIS")
        print("=" * 60)
        
        all_lines = []
        all_data = []
        line_count = 0
        
        for line in resp.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                all_lines.append(decoded)
                line_count += 1
                
                # Show first 5 lines and key events
                if line_count <= 5:
                    print(f"\n[LINE {line_count}]: {decoded[:150]}...")
                
                if decoded.startswith("data: "):
                    try:
                        data = json.loads(decoded[6:])
                        all_data.append(data)
                        
                        step_type = data.get("step_type", "N/A")
                        
                        # Show FINAL steps in detail
                        if step_type == "FINAL":
                            print(f"\n[LINE {line_count}] *** FINAL STEP FOUND ***")
                            content = data.get("content", {})
                            if isinstance(content, dict):
                                print(f"  content keys: {list(content.keys())}")
                                if "answer" in content:
                                    answer_str = content["answer"]
                                    print(f"  answer type: {type(answer_str).__name__}")
                                    print(f"  answer length: {len(answer_str) if answer_str else 0}")
                                    if answer_str:
                                        print(f"  answer preview: {str(answer_str)[:200]}...")
                                        
                    except json.JSONDecodeError as e:
                        if line_count <= 5:
                            print(f"  [JSON Error]: {e}")
        
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total lines received: {len(all_lines)}")
        print(f"Parsed data objects: {len(all_data)}")
        
        if all_data:
            step_types = [d.get("step_type", "unknown") for d in all_data]
            unique_types = list(set(step_types))
            print(f"Step types found: {unique_types}")
            
            # Count each type
            for st in unique_types:
                count = step_types.count(st)
                print(f"  - {st}: {count}")
            
            # Analyze FINAL steps
            final_steps = [d for d in all_data if d.get("step_type") == "FINAL"]
            if final_steps:
                print(f"\n✓ Found {len(final_steps)} FINAL step(s)")
                for i, f in enumerate(final_steps):
                    content = f.get("content", {})
                    print(f"\n  FINAL {i+1}:")
                    print(f"    content type: {type(content).__name__}")
                    
                    if isinstance(content, dict):
                        print(f"    content keys: {list(content.keys())}")
                        answer_raw = content.get("answer", "")
                        if answer_raw:
                            print(f"    answer type: {type(answer_raw).__name__}")
                            print(f"    answer length: {len(str(answer_raw))}")
                            
                            # Try to extract the actual text
                            if isinstance(answer_raw, str):
                                try:
                                    answer_obj = json.loads(answer_raw)
                                    if isinstance(answer_obj, dict):
                                        print(f"    Parsed as JSON dict with keys: {list(answer_obj.keys())}")
                                        if "answer" in answer_obj:
                                            final_answer = answer_obj["answer"]
                                            print(f"    NESTED ANSWER length: {len(final_answer)}")
                                            print(f"    First 300 chars:\n{final_answer[:300]}")
                                except json.JSONDecodeError:
                                    print(f"    Not JSON, first 300 chars:\n{answer_raw[:300]}")
            else:
                print("\n❌ No FINAL step found!")
                print("This explains why 'No answer text found'")
                
                # Check if there's any text content
                for d in all_data:
                    if "text" in d:
                        print(f"\nFound 'text' field: {str(d['text'])[:200]}...")
                        break
        else:
            print("\n❌ No data objects parsed from SSE stream!")
        
        # Save full response
        output_file = "debug_sse_response.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "raw_lines_count": len(all_lines),
                "first_10_lines": all_lines[:10],
                "parsed_data": all_data
            }, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Full response saved to: {output_file}")
        
    except Exception as e:
        print(f"\n❌ Exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_sse_response()
