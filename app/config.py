"""
Application configuration and settings.
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent

# Data directories - can be overridden via environment variables
# Default: points to main deepml project for local development
_DEFAULT_DEEPML_PATH = Path("d:/PythonProject/deepml")
PROBLEMS_DIR = Path(os.getenv("PROBLEMS_DIR", str(_DEFAULT_DEEPML_PATH / "problems")))
QUESTS_DIR = Path(os.getenv("QUESTS_DIR", str(_DEFAULT_DEEPML_PATH / "quests")))

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

# Feature flags
LOCAL_DEV = os.getenv("LOCAL_DEV", "false").lower() == "true"
AI_BACKEND = os.getenv("AI_BACKEND", "")
