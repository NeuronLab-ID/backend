"""
Per-user rate limiting for sandbox execution endpoints.

Uses slowapi (flask-limiter syntax) with in-memory storage.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import SANDBOX_RATE_LIMIT  # noqa: F401 (re-exported for convenience)


def get_rate_limit_key(request):
    """Extract client IP for rate limiting. Falls back to remote address."""
    return get_remote_address(request)


limiter = Limiter(key_func=get_rate_limit_key)
