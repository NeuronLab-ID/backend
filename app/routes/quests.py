"""
Quest routes for CRUD and execution.
"""
from fastapi import APIRouter, HTTPException, Depends
import json

from app.config import LOCAL_DEV
from app.database import SessionLocal
from app.routes.auth import get_current_user
from app.models.db import Quest, QuestProgress
from app.models.schemas import QuestExecuteRequest, QuestCreateRequest, QuestProgressSaveRequest
from app.services.executor import execute_code

router = APIRouter()


@router.get("/quests/{problem_id}")
async def get_quest(problem_id: int, generate: bool = False, user_id: int = Depends(get_current_user)):
    """
    Get quest for a problem (requires auth).
    
    Args:
        problem_id: Problem ID
        generate: If True and quest not found, generate on-demand (slow, ~60s)
    """
    from app.services.quest_service import get_or_generate_quest, generate_quest_on_demand
    
    db = SessionLocal()
    try:
        # Try to get from database or file
        result = await get_or_generate_quest(db, problem_id)
        
        if result:
            return result
        
        # Quest not available
        if generate:
            # Try on-demand generation (blocking, slow)
            result = await generate_quest_on_demand(db, problem_id)
            if result:
                return result
            raise HTTPException(500, "Quest generation failed")
        
        raise HTTPException(404, "Quest not found for this problem. Use ?generate=true to generate on-demand.")
    finally:
        db.close()


@router.post("/quest/execute")
async def execute_quest_code(request: QuestExecuteRequest, user_id: int = Depends(get_current_user)):
    """Execute code for a quest exercise (requires auth)."""
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
    
    # Get exercise test cases
    exercise = sub_quest.get("exercise", {})
    test_cases = exercise.get("test_cases", [])
    
    if not test_cases:
        raise HTTPException(400, "No test cases found for this exercise")
    
    # Execute code
    result = await execute_code(
        code=request.code,
        test_cases=test_cases
    )
    
    return result


@router.post("/quests/create")
async def create_quest(request: QuestCreateRequest, user=Depends(get_current_user)):
    """Create a quest (LOCAL_DEV only)."""
    if not LOCAL_DEV:
        raise HTTPException(403, "Quest creation is only allowed in local development mode")
    
    db = SessionLocal()
    try:
        # Check if quest already exists
        existing = db.query(Quest).filter(Quest.problem_id == request.problem_id).first()
        if existing:
            raise HTTPException(400, "Quest already exists for this problem")
        
        quest = Quest(
            problem_id=request.problem_id,
            data=json.dumps(request.data),
            created_by=user["user_id"] if isinstance(user, dict) else user
        )
        db.add(quest)
        db.commit()
        db.refresh(quest)
        
        return {"message": "Quest created", "id": quest.id}
    finally:
        db.close()


@router.get("/quests/check/{problem_id}")
async def check_quest_exists(problem_id: int, user_id: int = Depends(get_current_user)):
    """Check if a quest exists for a problem and whether it can be generated (requires auth)."""
    from app.services.quest_service import get_quest_status
    
    db = SessionLocal()
    try:
        status = get_quest_status(db, problem_id)
        status["local_dev"] = LOCAL_DEV
        return status
    finally:
        db.close()


@router.post("/quest/progress")
async def save_quest_progress(request: QuestProgressSaveRequest, user_id: int = Depends(get_current_user)):
    """Save progress for a quest step (mark as completed with code)."""
    db = SessionLocal()
    try:
        # Check if progress already exists
        existing = db.query(QuestProgress).filter(
            QuestProgress.user_id == user_id,
            QuestProgress.problem_id == request.problem_id,
            QuestProgress.step == request.step
        ).first()
        
        if existing:
            # Update existing progress
            existing.code = request.code
            existing.completed = True
        else:
            # Create new progress
            progress = QuestProgress(
                user_id=user_id,
                problem_id=request.problem_id,
                step=request.step,
                code=request.code,
                completed=True
            )
            db.add(progress)
        
        db.commit()
        return {"message": "Progress saved", "step": request.step}
    finally:
        db.close()


@router.get("/quest/progress/{problem_id}")
async def get_quest_progress(problem_id: int, user_id: int = Depends(get_current_user)):
    """Get user's progress for all steps of a quest."""
    db = SessionLocal()
    try:
        progress = db.query(QuestProgress).filter(
            QuestProgress.user_id == user_id,
            QuestProgress.problem_id == problem_id
        ).all()
        
        return {
            "progress": [
                {
                    "step": p.step,
                    "code": p.code,
                    "completed": p.completed,
                    "created_at": p.created_at.isoformat()
                }
                for p in progress
            ]
        }
    finally:
        db.close()
