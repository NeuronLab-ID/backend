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

# Manim Animation Configuration
MANIM_SANDBOX_IMAGE = os.getenv("MANIM_SANDBOX_IMAGE", "deepml-sandbox-manim:latest")
MANIM_RENDER_QUALITY = os.getenv("MANIM_RENDER_QUALITY", "l")  # l/m/h/k (low/medium/high/4K)
MANIM_GPU_ENABLED = os.getenv("MANIM_GPU_ENABLED", "false").lower() == "true"
MANIM_DEFAULT_BACKEND = os.getenv("MANIM_DEFAULT_BACKEND", "cpu").lower()
MANIM_EGPU_ENABLED = os.getenv("MANIM_EGPU_ENABLED", "false").lower() == "true" or MANIM_GPU_ENABLED
MANIM_EGPU_DEVICE_PATHS = tuple(
    path.strip() for path in os.getenv("MANIM_EGPU_DEVICE_PATHS", "/dev/dri").split(",") if path.strip()
)
MANIM_TIMEOUT = int(os.getenv("MANIM_TIMEOUT", "120"))  # seconds per render
MANIM_OUTPUT_DIR = Path(os.getenv("MANIM_OUTPUT_DIR", str(BASE_DIR / "media" / "manim")))
MANIM_MAX_CONCURRENT_RENDERS = int(os.getenv("MANIM_MAX_CONCURRENT_RENDERS", "3"))
MANIM_WORKER_POLL_INTERVAL = float(os.getenv("MANIM_WORKER_POLL_INTERVAL", "1.0"))
MANIM_STALE_JOB_SECONDS = int(os.getenv("MANIM_STALE_JOB_SECONDS", "1800"))

# Manim code-generation provider configuration
_DEFAULT_MANIM_OPENAI_COMPATIBLE_MODEL = "cx/gpt-5.5-xhigh"
MANIM_CODE_PROVIDER = os.getenv("MANIM_CODE_PROVIDER", "openai-compatible")
MANIM_OPENAI_COMPATIBLE_MODEL = os.getenv(
    "MANIM_OPENAI_COMPATIBLE_MODEL",
    os.getenv("MANIM_9ROUTER_MODEL", _DEFAULT_MANIM_OPENAI_COMPATIBLE_MODEL),
)
MANIM_OPENAI_COMPATIBLE_BASE_URL = os.getenv(
    "MANIM_OPENAI_COMPATIBLE_BASE_URL",
    os.getenv("MANIM_9ROUTER_BASE_URL", ""),
)
MANIM_OPENAI_COMPATIBLE_API_KEY = os.getenv(
    "MANIM_OPENAI_COMPATIBLE_API_KEY",
    os.getenv("MANIM_9ROUTER_API_KEY", ""),
)
MANIM_9ROUTER_MODEL = MANIM_OPENAI_COMPATIBLE_MODEL
MANIM_9ROUTER_BASE_URL = MANIM_OPENAI_COMPATIBLE_BASE_URL
MANIM_9ROUTER_API_KEY = MANIM_OPENAI_COMPATIBLE_API_KEY
OPENCODE_CONFIG_PATH = Path(os.getenv("OPENCODE_CONFIG_PATH", str(Path.home() / ".config" / "opencode" / "opencode.json")))

# Feature flags
LOCAL_DEV = os.getenv("LOCAL_DEV", "false").lower() == "true"

# AI provider configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
REASONING_PROVIDER = os.getenv("REASONING_PROVIDER", "openai")
REASONING_MODEL = os.getenv("REASONING_MODEL", "")

# Security warnings for production
if JWT_SECRET == "dev-secret-change-in-production":
    warnings.warn(
        "JWT_SECRET is using the default value. Set JWT_SECRET environment variable for production.",
        stacklevel=1,
    )
