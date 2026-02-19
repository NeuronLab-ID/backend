"""
Code execution routes.
"""

from fastapi import APIRouter, HTTPException, Depends
from starlette.requests import Request
import json

from app.routes.auth import get_current_user
from app.models.schemas import ExecuteRequest, ExecuteResponse
from app.services.executor import execute_code
from app.repositories.problem_repository import ProblemRepository
from app.dependencies import get_problem_repo
from app.rate_limit import limiter
from app.config import SANDBOX_RATE_LIMIT

router = APIRouter()


@router.post("/execute", response_model=ExecuteResponse)
@limiter.limit(SANDBOX_RATE_LIMIT)
async def run_code(
    request: Request,
    body: ExecuteRequest,
    user_id: int = Depends(get_current_user),
    repo: ProblemRepository = Depends(get_problem_repo),
):
    """Execute user code against test cases (requires auth)."""
    problem = repo.get_by_id(body.problem_id)

    if not problem:
        raise HTTPException(404, "Problem not found")

    # Get test cases
    test_cases = json.loads(problem.test_cases) if problem.test_cases else []

    # Execute code in sandbox
    result = await execute_code(code=body.code, test_cases=test_cases)

    return result
