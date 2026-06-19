"""
Code execution routes.
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request

from app.config import SANDBOX_RATE_LIMIT
from app.dependencies import get_problem_repo
from app.models.schemas import ExecuteRequest, ExecuteResponse
from app.rate_limit import limiter
from app.repositories.problem_repository import ProblemRepository
from app.routes.auth import get_current_user
from app.services.executor import execute_code

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

    # Get test cases based on framework
    framework = body.framework or "pytorch"

    # CUDA is not available in the current sandbox
    if framework == "cuda":
        raise HTTPException(400, "CUDA execution not available in current sandbox")

    # TinyGrad is not available in the current sandbox
    if framework == "tinygrad":
        raise HTTPException(400, "TinyGrad execution not available in current sandbox")

    if framework == "tinygrad" and problem.tinygrad_test_cases:
        test_cases = json.loads(problem.tinygrad_test_cases)
    elif framework == "cuda" and problem.cuda_test_cases:
        test_cases = json.loads(problem.cuda_test_cases)
    elif framework == "pytorch" and problem.pytorch_test_cases:
        test_cases = json.loads(problem.pytorch_test_cases)
    else:
        # Fallback to default test cases
        test_cases = json.loads(problem.test_cases) if problem.test_cases else []

    # Execute code in sandbox
    result = await execute_code(code=body.code, test_cases=test_cases)

    return result
