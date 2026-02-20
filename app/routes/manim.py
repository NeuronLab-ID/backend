"""
Manim animation routes for generating and serving reasoning step videos.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.routes.auth import get_current_user
from app.models.schemas import ManimGenerateRequest
from app.controllers.manim_controller import ManimController
from app.dependencies import get_manim_controller

router = APIRouter()


@router.post("/manim/generate")
async def generate_manim_animation(
    request: ManimGenerateRequest,
    user_id: int = Depends(get_current_user),
    controller: ManimController = Depends(get_manim_controller),
):
    """Generate manim animation for a problem's reasoning steps."""
    return await controller.generate_animation(request.problem_id, request.step_number, user_id)


@router.get("/manim/status/{problem_id}")
async def get_manim_status(
    problem_id: int,
    user_id: int = Depends(get_current_user),
    controller: ManimController = Depends(get_manim_controller),
):
    """Get manim animation status for a problem."""
    return controller.get_animation_status(problem_id)


@router.get("/manim/video/{problem_id}/{step_number}")
async def get_manim_video(
    problem_id: int,
    step_number: int,
    user_id: int = Depends(get_current_user),
    controller: ManimController = Depends(get_manim_controller),
):
    """Get rendered manim video file."""
    video_path = controller.get_video_path(problem_id, step_number)
    return FileResponse(video_path, media_type="video/mp4", filename=f"step_{step_number}.mp4")
