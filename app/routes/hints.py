"""
AI hint generation routes.
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_problem_repo
from app.models.db import Quest
from app.models.schemas import HintRequest, QuestHintRequest
from app.repositories.problem_repository import ProblemRepository
from app.routes.auth import get_current_user
from app.services.ai_providers import get_provider

router = APIRouter()


@router.post("/hint")
async def get_hint_endpoint(
    request: HintRequest,
    user_id: int = Depends(get_current_user),
    repo: ProblemRepository = Depends(get_problem_repo),
):
    """Get AI hint for an error (requires auth)."""
    problem = repo.get_by_id(request.problem_id)

    if not problem:
        raise HTTPException(404, "Problem not found")

    # Convert ORM object to dict for AI provider
    problem_data = {
        "title": problem.title,
        "description": problem.description,
        "starter_code": problem.starter_code,
        "test_cases": json.loads(problem.test_cases) if problem.test_cases else [],
    }

    provider = get_provider()
    hint = await provider.generate_hint(
        problem=problem_data, user_code=request.code, error=request.error
    )

    return {"hint": hint}


@router.post("/quest/hint")
async def get_quest_hint(
    request: QuestHintRequest,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get AI hint for a quest exercise (requires auth)."""
    quest = db.query(Quest).filter(Quest.problem_id == request.problem_id).first()
    if not quest:
        raise HTTPException(404, "Quest not found")
    quest_data = json.loads(quest.data)

    # Find the sub_quest for this step
    sub_quests = quest_data.get("sub_quests", [])
    sub_quest = next((sq for sq in sub_quests if sq.get("step") == request.step), None)

    if not sub_quest:
        raise HTTPException(404, f"Step {request.step} not found in quest")

    # Build context for AI
    exercise = sub_quest.get("exercise", {})
    context = {
        "title": sub_quest.get("title", f"Step {request.step}"),
        "description": exercise.get("description", ""),
        "function_signature": exercise.get("function_signature", ""),
        "hint": sub_quest.get("hint", ""),
    }

    provider = get_provider()
    hint = await provider.generate_hint(
        problem=context, user_code=request.code, error=request.error
    )

    return {"hint": hint}
