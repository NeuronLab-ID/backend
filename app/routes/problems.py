"""
Problem listing and details routes.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from typing import Optional
import json

from app.database import get_db
from app.models.db import Problem, ProblemSolution
from app.models.schemas import ProblemListResponse, ProblemSummary
from app.routes.auth import get_current_user
from app.repositories.problem_repository import ProblemRepository
from app.utils.encoding import decode_base64_if_needed
from app.services.solution_generator import generate_solution

router = APIRouter()


def _format_problem_detail(problem: Problem) -> dict:
    """Format problem object for API response."""
    result = {
        "id": problem.id,
        "title": problem.title,
        "category": problem.category,
        "difficulty": problem.difficulty,
        "description": decode_base64_if_needed(problem.description),
        "starter_code": problem.starter_code,
        "test_cases": json.loads(problem.test_cases) if problem.test_cases else [],
        "learn": decode_base64_if_needed(problem.learn_section),
    }

    if problem.example:
        result["example"] = json.loads(problem.example)
    if problem.video:
        try:
            result["video"] = json.loads(problem.video)
        except (json.JSONDecodeError, TypeError):
            result["video"] = problem.video
    if problem.pytorch_starter_code:
        result["pytorch_starter_code"] = problem.pytorch_starter_code
    if problem.pytorch_test_cases:
        result["pytorch_test_cases"] = json.loads(problem.pytorch_test_cases)
    if problem.tinygrad_starter_code:
        result["tinygrad_starter_code"] = problem.tinygrad_starter_code
    if problem.tinygrad_test_cases:
        result["tinygrad_test_cases"] = json.loads(problem.tinygrad_test_cases)
    if problem.cuda_starter_code:
        result["cuda_starter_code"] = problem.cuda_starter_code
    if problem.cuda_test_cases:
        result["cuda_test_cases"] = json.loads(problem.cuda_test_cases)
    if hasattr(problem, 'playground_enabled') and problem.playground_enabled:
        result["playground_enabled"] = problem.playground_enabled
        result["playground_code"] = problem.playground_code

    return result


@router.get("", response_model=ProblemListResponse)
async def list_problems(
    page: int = 1,
    limit: int = 20,
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by title"),
    db: Session = Depends(get_db)
):
    """Get list of problems with pagination (public)."""
    repo = ProblemRepository(db)
    problems, total = repo.list_problems(page, limit, category, search)
    quest_ids = repo.get_problem_ids_with_quests([p.id for p in problems])

    return ProblemListResponse(
        problems=[
            ProblemSummary(
                id=p.id,
                title=p.title,
                category=p.category,
                difficulty=p.difficulty,
                has_quest=p.id in quest_ids
            )
            for p in problems
        ],
        total=total
    )


@router.get("/{problem_id}")
async def get_problem(
    problem_id: int,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get problem details (requires auth)."""
    repo = ProblemRepository(db)
    problem = repo.get_by_id(problem_id)

    if not problem:
        raise HTTPException(404, "Problem not found")

    return _format_problem_detail(problem)


@router.get("/{problem_id}/solution")
async def get_solution(
    problem_id: int,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI-generated solution for a problem (requires auth, cached in database)."""
    # Check if solution exists in database
    cached = db.query(ProblemSolution).filter(
        ProblemSolution.problem_id == problem_id
    ).first()
    if cached:
        return {"solution": cached.solution, "cached": True}

    # Load problem from database
    repo = ProblemRepository(db)
    problem = repo.get_by_id(problem_id)
    if not problem:
        raise HTTPException(404, "Problem not found")

    # Convert to dict for solution generator
    problem_data = {
        "id": problem.id,
        "title": problem.title,
        "description": problem.description,
        "starter_code": problem.starter_code,
        "test_cases": json.loads(problem.test_cases) if problem.test_cases else []
    }

    # Generate solution using AI
    solution = await generate_solution(problem_data)

    if not solution:
        raise HTTPException(500, "Failed to generate solution")

    # Cache in database
    new_solution = ProblemSolution(problem_id=problem_id, solution=solution)
    db.add(new_solution)
    db.commit()

    return {"solution": solution, "cached": False}
