"""
Quest routes for CRUD and execution.

This is the refactored slim version that delegates to controllers and services.
Original: 1162 lines -> Refactored: ~130 lines
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.routes.auth import get_current_user
from app.models.schemas import (
    QuestExecuteRequest,
    QuestCreateRequest,
    QuestProgressSaveRequest,
    QuestReasoningRequest,
    FixMermaidRequest,
)
from app.controllers import QuestController, create_quest, check_quest_exists
from app.controllers.reasoning_controller import ReasoningController
from app.dependencies import get_quest_controller, get_reasoning_controller
from app.services.reasoning_service import (
    fix_mermaid_code,
    generate_test_case_reasoning,
)


router = APIRouter()


@router.get("/quests/{problem_id}")
async def get_quest(
    problem_id: int,
    generate: bool = False,
    user_id: int = Depends(get_current_user),
    controller: QuestController = Depends(get_quest_controller),
):
    """Get quest for a problem (requires auth)."""
    return await controller.get_quest(problem_id, generate)


@router.post("/quest/execute")
async def execute_quest_code(
    request: QuestExecuteRequest,
    user_id: int = Depends(get_current_user),
    controller: QuestController = Depends(get_quest_controller),
):
    """Execute code for a quest exercise (requires auth)."""
    return await controller.execute_code(request.problem_id, request.step, request.code)


@router.post("/quests/create")
async def create_quest_route(
    request: QuestCreateRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a quest (LOCAL_DEV only)."""
    user_id = user["user_id"] if isinstance(user, dict) else user
    return await create_quest(db, request.problem_id, request.data, user_id)


@router.get("/quests/check/{problem_id}")
async def check_quest_exists_route(
    problem_id: int,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check if a quest exists for a problem (requires auth)."""
    return check_quest_exists(db, problem_id)


@router.post("/quest/progress")
async def save_quest_progress(
    request: QuestProgressSaveRequest,
    user_id: int = Depends(get_current_user),
    controller: QuestController = Depends(get_quest_controller),
):
    """Save progress for a quest step."""
    return await controller.save_progress(
        user_id, request.problem_id, request.step, request.code
    )


@router.get("/quest/progress/{problem_id}")
async def get_quest_progress(
    problem_id: int,
    user_id: int = Depends(get_current_user),
    controller: QuestController = Depends(get_quest_controller),
):
    """Get user's progress for all steps of a quest."""
    return controller.get_progress(user_id, problem_id)


@router.post("/quest/reasoning")
async def generate_test_case_reasoning_route(
    request: QuestReasoningRequest, user_id: int = Depends(get_current_user)
):
    """Generate step-by-step reasoning for a test case."""
    return await generate_test_case_reasoning(
        request.function_signature, request.test_input, request.expected_output
    )


@router.get("/quest/full-reasoning/{problem_id}")
async def get_full_reasoning(
    problem_id: int,
    user_id: int = Depends(get_current_user),
    reasoning: ReasoningController = Depends(get_reasoning_controller),
):
    """Get cached full reasoning for a problem if it exists."""
    return reasoning.get_cached_reasoning(problem_id)


@router.get("/quest/full-reasoning/{problem_id}/stream")
async def stream_full_reasoning(
    problem_id: int,
    force: bool = False,
    usePerplexity: bool = False,
    usePerplexityReasoning: bool = False,
    user_id: int = Depends(get_current_user),
    reasoning: ReasoningController = Depends(get_reasoning_controller),
):
    """Generate and stream full reasoning for all quest steps using SSE."""
    return await reasoning.stream_full_reasoning(
        problem_id, user_id, force, usePerplexity, usePerplexityReasoning
    )


@router.post("/fix-mermaid")
async def fix_mermaid_code_route(
    request: FixMermaidRequest, user_id: int = Depends(get_current_user)
):
    """Use AI to fix invalid Mermaid diagram code."""
    fixed_code = await fix_mermaid_code(request.code, request.error)
    return {"fixed_code": fixed_code}
