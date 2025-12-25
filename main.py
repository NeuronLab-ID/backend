"""
NeuronLab Backend - FastAPI Application
Based on Deep-ML (https://deep-ml.com)
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import create_tables
from app.routes import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    create_tables()
    yield


app = FastAPI(
    title="NeuronLab API",
    description="Backend API for NeuronLab ML practice platform (based on Deep-ML)",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all API routes
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "name": "NeuronLab API", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
