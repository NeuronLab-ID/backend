import time
from typing import Any

try:
    from sqlalchemy.orm import Session
except Exception:  # pragma: no cover
    from typing import Any as Session

from app.logging_config import get_logger
from app.models.db import ManimAnimation
from app.prompts import (
    get_manim_code_prompt,
    get_manim_code_system_prompt,
)
from app.repositories.manim_repository import ManimRepository
from app.services import get_provider
from app.services.manim_executor import manim_executor

logger = get_logger(__name__)


class ManimService:
    def __init__(self, db: Session) -> None:
        self.repository: ManimRepository = ManimRepository(db)
        self.provider: Any = get_provider()

    async def generate_animation(
        self,
        problem_id: int,
        step_number: int,
        reasoning_data: dict[str, object],
    ) -> ManimAnimation:
        animation: ManimAnimation | None = None
        try:
            step_title = str(reasoning_data.get("step_title", ""))
            step_reasoning = str(reasoning_data.get("step_reasoning", ""))
            key_formulas = reasoning_data.get("key_formulas") or []
            if not isinstance(key_formulas, list):
                key_formulas = []
            problem_title = str(reasoning_data.get("problem_title", ""))
            problem_description = str(reasoning_data.get("problem_description", ""))

            system_prompt = get_manim_code_system_prompt()
            prompt = get_manim_code_prompt(
                step_number=step_number,
                step_title=step_title,
                step_reasoning=step_reasoning,
                key_formulas=key_formulas,
                problem_title=problem_title,
                problem_description=problem_description,
            )
            manim_code = await self.provider.generate_reasoning(prompt, system_prompt)

            animation = self.repository.create(problem_id, step_number, manim_code)
            self.repository.update_status(animation.id, "rendering")

            start_time = time.time()
            result = await manim_executor.render(manim_code, problem_id, step_number)
            render_time_ms = int((time.time() - start_time) * 1000)

            if result.get("status") == "success":
                video_path_value = result.get("video_path")
                video_path = video_path_value if isinstance(video_path_value, str) else ""
                self.repository.update_status(
                    animation.id,
                    "completed",
                    video_path=video_path,
                    render_time_ms=render_time_ms,
                )
            else:
                error_message_value = result.get("error", "Unknown error")
                error_message = (
                    error_message_value if isinstance(error_message_value, str) else str(error_message_value)
                )
                self.repository.update_status(
                    animation.id,
                    "error",
                    error_message=error_message,
                    render_time_ms=render_time_ms,
                )

            return self.repository.get_by_problem_and_step(problem_id, step_number) or animation
        except Exception as e:
            logger.error(f"Failed to generate animation for problem {problem_id} step {step_number}: {e}")
            if animation is not None:
                self.repository.update_status(animation.id, "error", error_message=str(e))
            raise

    async def generate_all_animations(
        self,
        problem_id: int,
        reasoning_data: dict[str, object],
    ) -> list[ManimAnimation]:
        steps = reasoning_data.get("steps") or reasoning_data.get("sub_quests") or []
        if not isinstance(steps, list):
            steps = []
        problem_title = str(reasoning_data.get("problem_title", reasoning_data.get("title", "")))
        problem_description = str(reasoning_data.get("problem_description", reasoning_data.get("description", "")))

        animations: list[ManimAnimation] = []
        for index, step in enumerate(steps, 1):
            if not isinstance(step, dict):
                step = {}
            step_payload = {
                "step_title": step.get("title", f"Step {index}"),
                "step_reasoning": step.get("reasoning", ""),
                "key_formulas": step.get("key_formulas", []),
                "problem_title": problem_title,
                "problem_description": problem_description,
            }
            animation = await self.generate_animation(problem_id, index, step_payload)
            animations.append(animation)

        return animations

    def get_animation_status(self, problem_id: int, total_steps: int) -> dict[str, Any]:
        return self.repository.get_status_summary(problem_id, total_steps)

    def get_animation(self, problem_id: int, step_number: int) -> ManimAnimation | None:
        return self.repository.get_by_problem_and_step(problem_id, step_number)
