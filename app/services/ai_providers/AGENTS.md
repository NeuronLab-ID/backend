# AGENTS.md — AI Providers

## Strategy Pattern

```
ai_provider_base.py    → ABC interfaces: AIProvider, SearchProvider
ai_provider_factory.py → Factory + singleton cache, provider selection logic
openai_provider.py     → OpenAI-compatible (works with any OpenAI-API-compatible endpoint)
perplexity_provider.py → Reverse-engineered unofficial Perplexity API (FRAGILE)
search_provider.py     → Perplexity web search via official API
```

## Factory (`ai_provider_factory.py`)

- `get_provider(name)` — returns cached singleton. Supports `"openai"`, `"perplexity"`.
- `get_reasoning_provider(use_perplexity, model)` — priority chain: explicit params → env vars (`REASONING_PROVIDER`, `REASONING_MODEL`) → default OpenAI.
- `get_search_provider()` — returns Perplexity search if `PERPLEXITY_API_KEY` set, else None.
- `clear_providers()` — resets cache. Used in tests only.

## Adding a New Provider

1. Create `app/services/ai_providers/new_provider.py`
2. Implement `AIProvider` (and optionally `SearchProvider`) ABC
3. Register in `ai_provider_factory.py`'s provider map
4. Add corresponding env vars to `app/config.py` and `.env.example`

## OpenAI Provider (`openai_provider.py`)

Standard OpenAI SDK integration. Works with any OpenAI-compatible API via `OPENAI_BASE_URL`. Raises `ValueError` if `OPENAI_API_KEY` not set. Supports streaming and non-streaming.

## Perplexity Provider (`perplexity_provider.py`) — HERE BE DRAGONS

**616 lines. Most fragile file in the entire codebase.**

- Uses `curl_cffi` with `impersonate="edge"` for TLS fingerprint impersonation
- Depends on browser session cookies (`PERPLEXITY_COOKIES` env var) — cookies expire regularly
- Reverse-engineered endpoints: SSE chat completion, thread fetching, undocumented API routes
- Retry logic: exponential backoff + jitter, max 3 attempts
- `_CookieExpiredError` is the most common failure mode — manifests as silent failures or 403s

**When modifying:**
- Cookie format: semicolon-separated `key=value` pairs from browser DevTools
- SSE parsing is hand-rolled (no library) — byte-level line splitting
- Thread management: creates/fetches conversation threads to maintain context
- Test with BOTH valid and expired cookies — the error paths matter more than happy paths
- Any Perplexity frontend change can break this. Check Perplexity's network tab if things stop working.

## Search Provider (`search_provider.py`)

Uses Perplexity's **official** API (not reverse-engineered). Requires `PERPLEXITY_API_KEY`. More stable than the chat provider. Returns structured search results with citations.
