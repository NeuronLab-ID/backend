# Manim Animation Repository
# Handles all database operations for ManimAnimation model

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.db import ManimAnimation


class ManimRepository:
    """Repository for manim animation database operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_problem_id(self, problem_id: int) -> list[ManimAnimation]:
        """Get all animations for a problem."""
        return self.db.query(ManimAnimation).filter(ManimAnimation.problem_id == problem_id).all()

    def get_by_problem_and_step(self, problem_id: int, step_number: int) -> ManimAnimation | None:
        """Get animation by problem ID and step number."""
        return (
            self.db.query(ManimAnimation)
            .filter(ManimAnimation.problem_id == problem_id, ManimAnimation.step_number == step_number)
            .first()
        )

    def create(self, problem_id: int, step_number: int, manim_code: str) -> ManimAnimation:
        """Create a new manim animation with status='pending'."""
        animation = ManimAnimation(
            problem_id=problem_id, step_number=step_number, manim_code=manim_code, status="pending"
        )
        self.db.add(animation)
        self.db.commit()
        self.db.refresh(animation)
        return animation

    def update_status(
        self,
        animation_id: int,
        status: str,
        video_path: str | None = None,
        error_message: str | None = None,
        render_time_ms: int | None = None,
    ) -> ManimAnimation:
        """Update animation status and optional fields."""
        animation = self.db.query(ManimAnimation).filter(ManimAnimation.id == animation_id).first()

        if animation:
            animation.status = status
            animation.updated_at = datetime.now(timezone.utc)
            if video_path is not None:
                animation.video_path = video_path
            if error_message is not None:
                animation.error_message = error_message
            if render_time_ms is not None:
                animation.render_time_ms = render_time_ms
            self.db.commit()
            self.db.refresh(animation)

        return animation

    def get_status_summary(self, problem_id: int, total_steps: int) -> dict[str, object]:
        """Get status summary for all animations of a problem."""
        animations = self.get_by_problem_id(problem_id)

        completed_count = sum(1 for a in animations if a.status == "completed")
        rendering_count = sum(1 for a in animations if a.status == "rendering")
        error_count = sum(1 for a in animations if a.status == "error")
        pending_count = sum(1 for a in animations if a.status == "pending")

        # Serialize animations sorted by step_number
        animations_sorted = sorted(animations, key=lambda a: a.step_number)
        animations_list = [
            {
                "id": a.id,
                "problem_id": a.problem_id,
                "step_number": a.step_number,
                "status": a.status,
                "video_url": a.video_path,
                "error_message": a.error_message,
                "render_time_ms": a.render_time_ms,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in animations_sorted
        ]

        return {
            "problem_id": problem_id,
            "total_steps": total_steps,
            "completed_count": completed_count,
            "rendering_count": rendering_count,
            "error_count": error_count,
            "pending_count": pending_count,
            "animations": animations_list,
        }
