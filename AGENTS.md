# AGENTS.md — Backend (Python/FastAPI)

## Layer Architecture

```
routes/        → Thin HTTP. Parse request, call controller/service, return response.
controllers/   → Business logic orchestration (quest_controller, reasoning_controller).
services/      → Domain logic, AI calls, Docker execution, exports.
repositories/  → SQLAlchemy queries. One repo per model.
models/        → db.py (ORM) + schemas.py (Pydantic). Both must stay in sync.
prompts/       → All LLM prompt templates. NEVER inline prompts elsewhere.
utils/         → json_utils (resilient AI parse), encoding (base64 decode).
```

## Python Conventions

- **Python 3.12**, Ruff linter (E/F/I rules, E501 ignored), 120-char line limit
- **Loguru** logging everywhere — `from app.logging_config import get_logger; logger = get_logger(__name__)`
- **No custom exceptions** — all errors raised as `HTTPException(status_code, detail)` 
- **DI hub**: `app/dependencies.py` — all `Depends()` providers (repos, services, controllers)
- **Config**: `app/config.py` — all env vars via `os.getenv()` with defaults. Never read env vars elsewhere.

## Database

- **SQLite** (default `sqlite:///./deepml.db`), **SQLAlchemy** ORM
- 6 models: `User`, `Problem`, `Submission`, `Quest`, `QuestProgress`, `ProblemSolution`
- Alembic migrations in `alembic/`. Base schema created by `create_all()`, Alembic tracks incremental changes.
- `setup_models.py` — DB seeder script (459 lines). Seeds problems from JSON in `frontend/public/data/`.

## Auth Flow (Backend Side)

1. `routes/auth.py`: `get_current_user()` dependency extracts Bearer token → `decode_token()` → user_id or 401
2. `services/auth_service.py`: `create_access_token()` / `decode_token()` (python-jose), `hash_password()` / `verify_password()` (bcrypt)
3. `repositories/auth_repository.py`: `get_by_email()`, `get_by_username()`, `get_by_id()`
4. JWT payload: `{"sub": user_id, "exp": expiry}`. HS256 algorithm. Default 24h expiry.

## Error Handling

- Routes: `HTTPException(4xx)` for validation/not-found
- Controllers: `HTTPException(5xx)` for business logic failures
- Services: `ValueError` for config errors (missing API key, unknown provider)
- Executor: Returns error dicts `{"status": "error", "error": "..."}` — no exceptions
- Global handlers in `main.py`: catch `StarletteHTTPException` + unhandled `Exception` → structured JSON

## Rate Limiting

`slowapi` in `app/rate_limit.py`. IP-based key extraction. Applied on `/api/execute` and `/api/quest/execute`. Default: `10/minute` (configurable via `SANDBOX_RATE_LIMIT`).

## Testing

- `pytest` + in-memory SQLite. All external calls mocked.
- `conftest.py`: function-scoped DB, TestClient, mock AI provider, test user fixture, auth token fixture
- `test_prompts.py` (57+ tests): structural validation — return types, interpolation, negative constraints
- `test_prompt_consolidation.py` (7 tests): AST parsing ensures no inline prompts in services/routes
- Run: `pytest --cov=app` for coverage

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point. `load_dotenv()` FIRST, then CORS, exception handlers, lifespan, router mount |
| `app/config.py` | All env vars. Security warning if JWT_SECRET is default |
| `app/dependencies.py` | Central DI provider for all repos/services/controllers |
| `app/database.py` | Engine + `get_db()` session dependency |
| `app/rate_limit.py` | slowapi limiter instance + key function |
| `docker-compose.yml` | Backend + sandbox-builder services |
| `sandbox/Dockerfile` | Python 3.11-slim + numpy/scipy/pandas/sklearn/torch/matplotlib |
