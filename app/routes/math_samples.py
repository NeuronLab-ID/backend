"""
AI-powered math sample generator routes.

Refactored from 196 lines to ~25 lines.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.routes.auth import get_current_user
from app.services.math_sample_service import MathSampleService

router = APIRouter()


class MathSampleRequest(BaseModel):
    formula_name: str
    formula_latex: str
    difficulty: str = "easy"  # easy, medium, hard


@router.post("/generate-sample")
async def generate_math_sample(request: MathSampleRequest, user_id: int = Depends(get_current_user)):
    """Generate a worked math example using AI."""
    service = MathSampleService()
    return await service.generate_sample(
        request.formula_name,
        request.formula_latex,
        request.difficulty
    )
