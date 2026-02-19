"""
NeuronLab Backend - FastAPI Application
Based on Deep-ML (https://deep-ml.com)
"""

# Load .env FIRST before any other imports
from dotenv import load_dotenv

load_dotenv()

# Initialize logging
from app.logging_config import setup_logger

setup_logger()

import os
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.database import create_tables
from app.routes import api_router
from app.logging_config import get_logger
from app.rate_limit import limiter

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and container pool on startup."""
    create_tables()
    # Start container pool
    from app.services.executor import container_pool

    await container_pool.start()
    yield
    # Shutdown container pool
    await container_pool.shutdown()


app = FastAPI(
    title="NeuronLab API",
    description="Backend API for NeuronLab ML practice platform (based on Deep-ML)",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware - environment-driven configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# Global Exception Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with structured JSON response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error": exc.detail, "status_code": exc.status_code},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions with structured JSON response."""
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
    logger.debug(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "status_code": 500},
    )


# Include all API routes
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "name": "NeuronLab API", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    import os

    # For development: single worker with reload
    # For production: multiple workers (set WORKERS env var)
    workers = int(os.getenv("WORKERS", "1"))
    reload_mode = os.getenv("RELOAD", "true").lower() == "true"

    if reload_mode:
        # Development mode: single worker with hot reload
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    else:
        # Production mode: multiple workers for concurrent requests
        uvicorn.run("main:app", host="0.0.0.0", port=8000, workers=workers)
