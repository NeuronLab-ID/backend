"""
Application configuration and settings.
"""

import os
import warnings
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent

# Data directories - can be overridden via environment variables
# Default: points to main deepml project for local development
_DEFAULT_DEEPML_PATH = Path("d:/PythonProject/deepml")
PROBLEMS_DIR = Path(os.getenv("PROBLEMS_DIR", str(_DEFAULT_DEEPML_PATH / "problems")))
QUESTS_DIR = Path(os.getenv("QUESTS_DIR", str(_DEFAULT_DEEPML_PATH / "quests")))
QUEST_GENERATOR_PATH = Path(os.getenv("QUEST_GENERATOR_PATH", str(_DEFAULT_DEEPML_PATH / "quest_generator.py")))

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./deepml.db")

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

# Sandbox Configuration
SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "deepml-sandbox:latest")
SANDBOX_TIMEOUT = int(os.getenv("SANDBOX_TIMEOUT", "30"))
SANDBOX_MEMORY = os.getenv("SANDBOX_MEMORY", "512m")

# Sandbox Security & Pool Configuration
SANDBOX_POOL_SIZE = int(os.getenv("CONTAINER_POOL_SIZE", "2"))
SANDBOX_SECURITY_LEVEL = os.getenv("SANDBOX_SECURITY_LEVEL", "full")  # "full" or "basic" (Windows)
SANDBOX_RATE_LIMIT = os.getenv("SANDBOX_RATE_LIMIT", "10/minute")  # slowapi format
SANDBOX_CONTAINER_TTL = int(os.getenv("SANDBOX_CONTAINER_TTL", "1800"))  # 30 min in seconds
SANDBOX_MAX_EXECUTIONS = int(os.getenv("SANDBOX_MAX_EXECUTIONS", "50"))  # per container
SANDBOX_PIDS_LIMIT = int(os.getenv("SANDBOX_PIDS_LIMIT", "50"))
SANDBOX_CODE_MAX_LENGTH = int(os.getenv("SANDBOX_CODE_MAX_LENGTH", "50000"))  # 50KB

# Feature flags
LOCAL_DEV = os.getenv("LOCAL_DEV", "false").lower() == "true"

# AI provider configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
REASONING_PROVIDER = os.getenv("REASONING_PROVIDER", "openai")
REASONING_MODEL = os.getenv("REASONING_MODEL", "")

# Security warnings for production
if JWT_SECRET == "dev-secret-change-in-production":
    warnings.warn(
        "JWT_SECRET is using the default value. Set JWT_SECRET environment variable for production.",
        stacklevel=1,
    )
