"""
Code execution routes.
"""
from fastapi import APIRouter, HTTPException, Depends
import json

from app.config import PROBLEMS_DIR
from app.routes.auth import get_current_user
from app.models.schemas import ExecuteRequest, ExecuteResponse
from app.services.executor import execute_code

router = APIRouter()


@router.post("/execute", response_model=ExecuteResponse)
async def run_code(request: ExecuteRequest, user_id: int = Depends(get_current_user)):
    """Execute user code against test cases (requires auth)."""
    problem_file = PROBLEMS_DIR / f"problem_{request.problem_id:04d}.json"
    
    if not problem_file.exists():
        raise HTTPException(404, "Problem not found")
    
    with open(problem_file, "r", encoding="utf-8") as f:
        problem = json.load(f)
    
    # Get test cases
    test_cases = problem.get("test_cases", [])
    
    # Execute code in sandbox
    result = await execute_code(
        code=request.code,
        test_cases=test_cases
    )
    
    return result
