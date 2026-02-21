# AGENTS.md — Services Layer

## Role

Domain logic layer. Services are called by controllers/routes, never by other services (except AI providers via factory). Each service owns a single domain concern.

## Service Map

| Service | Lines | Domain |
|---------|-------|--------|
| `executor.py` | 430 | Docker-sandboxed code execution with container pool |
| `reasoning_service.py` | 287 | AI reasoning: step generation, summary, web search, SSE streaming |
| `solution_generator.py` | ~150 | AI-generated problem solutions |
| `math_sample_service.py` | ~120 | Mathematical sample data generation |
| `export_service.py` | 233 | Markdown + LaTeX export with AI formatting |
| `notebook_converter.py` | 236 | Jupyter notebook generation from reasoning |
| `quest_service.py` | ~150 | Quest generation and management |
| `auth_service.py` | ~80 | JWT + bcrypt (pure functions, no DB) |
| `user_stats_service.py` | ~60 | User statistics aggregation |

## Docker Executor (`executor.py`)

**ContainerPool** — pre-warmed sandbox containers with async semaphore.

- Pool auto-starts on first `acquire()`. Containers named `neuronlab-sandbox-pool-{uuid}`.
- TTL-based replacement: containers recycled after `SANDBOX_CONTAINER_TTL` seconds or `SANDBOX_MAX_EXECUTIONS` runs.
- `_cleanup_orphans()` removes leaked containers on startup.
- Race conditions are a real risk — the semaphore + lock pattern is intentional.
- Graceful degradation: if Docker unavailable, execution routes return error without crashing the app.
- Security: containers run as `nobody`, no network, memory/PID limits from config.

## Prompt Templates (`app/prompts/`)

All AI prompt strings live here. **NEVER** put prompts inline in services or routes.

| Module | Contents |
|--------|----------|
| `reasoning_prompts.py` (440 lines) | 12+ functions: step reasoning, summary, mermaid fix, test cases, LaTeX/MD export, hints |
| `solution_prompts.py` | Solution generation prompts |
| `hint_prompts.py` | Progressive hint system prompts |
| `math_prompts.py` | Mathematical sample generation prompts |
| `quest_prompts.py` | Quest/side-quest generation prompts |

**Rules enforced by tests:**
1. Every prompt function MUST return a string
2. Every prompt MUST include negative constraints ("NEVER", "Do NOT")
3. Interpolation variables MUST be used (no orphan `{var}`)
4. `test_prompt_consolidation.py` uses AST parsing to verify zero inline prompts exist outside `app/prompts/`

## AI Integration Pattern

Services call AI providers through the factory, never directly:
```python
from app.services.ai_providers.ai_provider_factory import get_provider, get_reasoning_provider
provider = get_provider("openai")        # cached singleton
provider = get_reasoning_provider(use_perplexity=True, model="sonar-pro")
```

## SSE Streaming (Reasoning)

`reasoning_service.py` yields `ReasoningStreamEvent` dicts via `StreamingResponse`:
- Event types: `step_start`, `step_content`, `step_complete`, `summary`, `search_results`, `error`, `complete`
- Frontend consumes via `fetchReasoningStream()` in `api.ts` (AsyncGenerator over EventSource)

## JSON Resilience

`app/utils/json_utils.py` — parses malformed AI JSON responses. Handles: markdown code fences, trailing commas, truncated output, single quotes. Used by all services processing AI output.
