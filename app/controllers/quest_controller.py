# Quest Controller
# Orchestration layer for quest CRUD and progress operations

import json
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.config import LOCAL_DEV
from app.models.db import Quest, QuestProgress
from app.repositories import QuestRepository
from app.services.executor import execute_code


class QuestController:
    """Controller for quest CRUD and progress operations."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = QuestRepository(db)

    async def get_quest(self, problem_id: int, generate: bool = False) -> dict:
        """Get quest for a problem, optionally generating on-demand."""
        from app.services.quest_service import (
            get_or_generate_quest,
            generate_quest_on_demand,
        )

        result = await get_or_generate_quest(self.db, problem_id)

        if result:
            return result

        if generate:
            result = await generate_quest_on_demand(self.db, problem_id)
            if result:
                return result
            raise HTTPException(500, "Quest generation failed")

        raise HTTPException(
            404,
            "Quest not found for this problem. Use ?generate=true to generate on-demand.",
        )

    async def execute_code(self, problem_id: int, step: int, code: str) -> dict:
        """Execute code for a quest exercise."""
        quest = self.repository.get_by_problem_id(problem_id)
        if not quest:
            raise HTTPException(404, "Quest not found")

        quest_data = json.loads(quest.data)
        sub_quests = quest_data.get("sub_quests", [])
        sub_quest = next((sq for sq in sub_quests if sq.get("step") == step), None)

        if not sub_quest:
            raise HTTPException(404, f"Step {step} not found in quest")

        exercise = sub_quest.get("exercise", {})
        test_cases = exercise.get("test_cases", [])

        if not test_cases:
            raise HTTPException(400, "No test cases found for this exercise")

        return await execute_code(code=code, test_cases=test_cases)

    async def save_progress(
        self, user_id: int, problem_id: int, step: int, code: str
    ) -> dict:
        """Save progress for a quest step."""
        existing = self.repository.get_progress_by_step(user_id, problem_id, step)

        if existing:
            self.repository.update_progress(existing, code, completed=True)
        else:
            progress = QuestProgress(
                user_id=user_id,
                problem_id=problem_id,
                step=step,
                code=code,
                completed=True,
            )
            self.repository.save_progress(progress)

        return {"message": "Progress saved", "step": step}

    def get_progress(self, user_id: int, problem_id: int) -> dict:
        """Get user's progress for all steps of a quest."""
        progress = self.repository.get_progress(user_id, problem_id)

        return {
            "progress": [
                {
                    "step": p.step,
                    "code": p.code,
                    "completed": p.completed,
                    "created_at": p.created_at.isoformat(),
                }
                for p in progress
            ]
        }


# Convenience functions for route handlers
async def create_quest(db: Session, problem_id: int, data: dict, user_id: int) -> dict:
    """Create a quest (LOCAL_DEV only)."""
    if not LOCAL_DEV:
        raise HTTPException(
            403, "Quest creation is only allowed in local development mode"
        )

    repository = QuestRepository(db)
    existing = repository.get_by_problem_id(problem_id)
    if existing:
        raise HTTPException(400, "Quest already exists for this problem")

    quest = Quest(problem_id=problem_id, data=json.dumps(data), created_by=user_id)
    saved = repository.save(quest)

    return {"message": "Quest created", "id": saved.id}


def check_quest_exists(db: Session, problem_id: int) -> dict:
    """Check if a quest exists for a problem."""
    from app.services.quest_service import get_quest_status

    status = get_quest_status(db, problem_id)
    status["local_dev"] = LOCAL_DEV
    return status
