# Manim Controller
# Orchestrates animation generation and retrieval for reasoning steps

import json
from pathlib import Path

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.repositories.quest_repository import QuestRepository
from app.services.manim_service import ManimService
from app.logging_config import get_logger

logger = get_logger(__name__)


class ManimController:
    """Controller for Manim animation generation and retrieval."""

    def __init__(self, db: Session):
        self.db = db
        self.quest_repository = QuestRepository(db)
        self.manim_service = ManimService(db)

    async def generate_animation(
        self, problem_id: int, step_number: int | None, user_id: int, video_type: str | None = None
    ) -> dict:
        """Generate animation(s) for a problem's reasoning steps."""
        reasoning = self.quest_repository.get_reasoning(problem_id)
        if not reasoning:
            raise HTTPException(404, "No reasoning available for this problem. Generate reasoning first.")

        reasoning_data = json.loads(reasoning.reasoning_data)
        steps = reasoning_data.get("steps", [])

        if step_number is None:
            animations = await self.manim_service.generate_all_animations(
                problem_id, reasoning_data, video_type=video_type
            )
            return {
                "problem_id": problem_id,
                "animations": [
                    {
                        "step_number": a.step_number,
                        "status": a.status,
                        "video_path": a.video_path,
                        "render_time_ms": a.render_time_ms,
                        "video_type": a.video_type,
                    }
                    for a in animations
                ],
            }

        if step_number < 1 or step_number > len(steps):
            raise HTTPException(
                400,
                f"Invalid step number {step_number}. Problem has {len(steps)} steps.",
            )

        step = steps[step_number - 1]
        step_data = {
            "step_title": step.get("title", ""),
            "step_reasoning": step.get("reasoning", ""),
            "key_formulas": step.get("key_formulas", []),
            "problem_title": reasoning_data.get("problem_title", ""),
            "problem_description": reasoning_data.get("problem_description", ""),
        }

        if video_type is None:
            # Generate both types for this step
            animations = []
            for vtype in ["visualization", "calculation"]:
                animation = await self.manim_service.generate_animation(
                    problem_id, step_number, step_data, video_type=vtype
                )
                animations.append(
                    {
                        "problem_id": problem_id,
                        "step_number": animation.step_number,
                        "status": animation.status,
                        "video_path": animation.video_path,
                        "render_time_ms": animation.render_time_ms,
                        "video_type": animation.video_type,
                    }
                )
            return {"animations": animations}
        else:
            # Generate only the specified type
            animation = await self.manim_service.generate_animation(
                problem_id, step_number, step_data, video_type=video_type
            )
            return {
                "problem_id": problem_id,
                "step_number": animation.step_number,
                "status": animation.status,
                "video_path": animation.video_path,
                "render_time_ms": animation.render_time_ms,
                "video_type": animation.video_type,
            }

    def get_animation_status(self, problem_id: int) -> dict:
        """Get animation status for all steps of a problem."""
        reasoning = self.quest_repository.get_reasoning(problem_id)
        if not reasoning:
            raise HTTPException(404, "No reasoning available for this problem.")

        reasoning_data = json.loads(reasoning.reasoning_data)
        steps = reasoning_data.get("steps", [])
        total_steps = len(steps)

        return self.manim_service.get_animation_status(problem_id, total_steps)

    def get_video_path(self, problem_id: int, step_number: int, video_type: str = "calculation") -> Path:
        """Get the video file path for a completed animation."""
        animation = self.manim_service.get_animation(problem_id, step_number, video_type=video_type)
        if not animation:
            raise HTTPException(404, "Animation not found")
        if animation.status != "completed":
            raise HTTPException(404, "Animation not ready")
        if not animation.video_path:
            raise HTTPException(404, "Video file path not set")

        path = Path(animation.video_path)
        if not path.exists():
            raise HTTPException(404, "Video file not found on disk")

        return path
