"""
Problem listing and details routes.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
import json
import base64

from app.config import PROBLEMS_DIR
from app.database import SessionLocal
from app.models.db import Problem
from app.models.schemas import ProblemListResponse, ProblemSummary
from app.routes.auth import get_current_user

router = APIRouter()


def decode_base64_if_needed(text: str) -> str:
    """Decode Base64 string if it appears to be encoded."""
    if not text:
        return text
    try:
        # Try to decode as Base64
        decoded = base64.b64decode(text).decode('utf-8')
        # If successful and looks like readable text, return decoded
        if decoded.isprintable() or '\n' in decoded:
            return decoded
    except:
        pass
    return text


@router.get("", response_model=ProblemListResponse)
async def list_problems(
    page: int = 1, 
    limit: int = 20,
    category: Optional[str] = Query(None, description="Filter by category")
):
    """Get list of problems with pagination (public)."""
    db = SessionLocal()
    try:
        query = db.query(Problem)
        
        # Apply category filter if provided
        if category:
            query = query.filter(Problem.category == category)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        problems = query.order_by(Problem.id).offset((page - 1) * limit).limit(limit).all()
        
        return ProblemListResponse(
            problems=[
                ProblemSummary(
                    id=p.id,
                    title=p.title,
                    category=p.category,
                    difficulty=p.difficulty
                )
                for p in problems
            ],
            total=total
        )
    finally:
        db.close()


@router.get("/{problem_id}")
async def get_problem(problem_id: int, user_id: int = Depends(get_current_user)):
    """Get problem details (requires auth)."""
    db = SessionLocal()
    try:
        problem = db.query(Problem).filter(Problem.id == problem_id).first()
        
        if not problem:
            raise HTTPException(404, "Problem not found")
        
        # Return as dict matching JSON structure
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
        
        # Add optional fields if present
        if problem.example:
            result["example"] = json.loads(problem.example)
        if problem.video:
            # Handle video (could be JSON array or string)
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
        
        # Playground fields
        if problem.playground_enabled:
            result["playground_enabled"] = problem.playground_enabled
            result["playground_code"] = problem.playground_code
        
        return result
    finally:
        db.close()


@router.get("/{problem_id}/solution")
async def get_solution(problem_id: int, user_id: int = Depends(get_current_user)):
    """Get AI-generated solution for a problem (requires auth, cached in database)."""
    from app.services.solution_generator import generate_solution
    from app.models.db import ProblemSolution
    
    db = SessionLocal()
    try:
        # Check if solution exists in database
        cached = db.query(ProblemSolution).filter(ProblemSolution.problem_id == problem_id).first()
        if cached:
            return {"solution": cached.solution, "cached": True}
        
        # Load problem from database
        problem = db.query(Problem).filter(Problem.id == problem_id).first()
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
    finally:
        db.close()
