"""
Submission CRUD routes.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.routes.auth import get_current_user
from app.models.db import Submission
from app.models.schemas import SaveSubmissionRequest
from app.repositories.submission_repository import SubmissionRepository
from app.dependencies import get_submission_repo

router = APIRouter()


@router.get("/{problem_id}")
async def get_submissions(
    problem_id: int,
    user_id: int = Depends(get_current_user),
    repo: SubmissionRepository = Depends(get_submission_repo),
):
    """Get user's submission history for a problem (requires auth)."""
    submissions = repo.get_by_problem(user_id, problem_id)

    return {
        "submissions": [
            {
                "id": s.id,
                "code": s.code,
                "passed": s.passed,
                "error": s.error,
                "execution_time": s.execution_time,
                "created_at": s.created_at.isoformat(),
            }
            for s in submissions
        ]
    }


@router.post("")
async def save_submission(
    request: SaveSubmissionRequest,
    user_id: int = Depends(get_current_user),
    repo: SubmissionRepository = Depends(get_submission_repo),
):
    """Save a submission (when user clicks Save)."""
    submission = Submission(
        user_id=user_id,
        problem_id=request.problem_id,
        code=request.code,
        passed=request.passed,
        execution_time=0,
    )
    submission = repo.create(submission)

    return {
        "id": submission.id,
        "message": "Submission saved",
        "created_at": submission.created_at.isoformat(),
    }


@router.delete("/{submission_id}")
async def delete_submission(
    submission_id: int,
    user_id: int = Depends(get_current_user),
    repo: SubmissionRepository = Depends(get_submission_repo),
):
    """Delete a submission (requires auth, user can only delete their own)."""
    if not repo.delete(user_id, submission_id):
        raise HTTPException(404, "Submission not found")
    return {"message": "Submission deleted"}
