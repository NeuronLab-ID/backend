"""
AI hint generation routes.
"""
from fastapi import APIRouter, HTTPException, Depends
import json

from app.config import PROBLEMS_DIR
from app.database import SessionLocal
from app.routes.auth import get_current_user
from app.models.db import Quest
from app.models.schemas import HintRequest, QuestHintRequest
from app.services.hint_generator import generate_hint

router = APIRouter()


@router.post("/hint")
async def get_hint_endpoint(request: HintRequest, user_id: int = Depends(get_current_user)):
    """Get AI hint for an error (requires auth)."""
    problem_file = PROBLEMS_DIR / f"problem_{request.problem_id:04d}.json"
    
    if not problem_file.exists():
        raise HTTPException(404, "Problem not found")
    
    with open(problem_file, "r", encoding="utf-8") as f:
        problem = json.load(f)
    
    hint = await generate_hint(
        problem=problem,
        user_code=request.code,
        error=request.error
    )
    
    return {"hint": hint}


@router.post("/quest/hint")
async def get_quest_hint(request: QuestHintRequest, user_id: int = Depends(get_current_user)):
    """Get AI hint for a quest exercise (requires auth)."""
    db = SessionLocal()
    try:
        quest = db.query(Quest).filter(Quest.problem_id == request.problem_id).first()
        if not quest:
            raise HTTPException(404, "Quest not found")
        quest_data = json.loads(quest.data)
    finally:
        db.close()
    
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
        "hint": sub_quest.get("hint", "")
    }
    
    hint = await generate_hint(
        problem=context,
        user_code=request.code,
        error=request.error
    )
    
    return {"hint": hint}
