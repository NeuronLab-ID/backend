"""
Submission CRUD routes.
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.routes.auth import get_current_user
from app.models.db import Submission
from app.models.schemas import SaveSubmissionRequest, SubmissionResponse

router = APIRouter()


@router.get("/{problem_id}")
async def get_submissions(problem_id: int, user_id: int = Depends(get_current_user)):
    """Get user's submission history for a problem (requires auth)."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        submissions = db.query(Submission).filter(
            Submission.user_id == user_id,
            Submission.problem_id == problem_id
        ).order_by(Submission.created_at.desc()).limit(20).all()
        
        return {
            "submissions": [
                {
                    "id": s.id,
                    "code": s.code,
                    "passed": s.passed,
                    "error": s.error,
                    "execution_time": s.execution_time,
                    "created_at": s.created_at.isoformat()
                }
                for s in submissions
            ]
        }
    finally:
        db.close()


@router.post("")
async def save_submission(request: SaveSubmissionRequest, user_id: int = Depends(get_current_user)):
    """Save a submission (when user clicks Save)."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        submission = Submission(
            user_id=user_id,
            problem_id=request.problem_id,
            code=request.code,
            passed=request.passed,
            execution_time=0
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)
        
        return {
            "id": submission.id,
            "message": "Submission saved",
            "created_at": submission.created_at.isoformat()
        }
    finally:
        db.close()


@router.delete("/{submission_id}")
async def delete_submission(submission_id: int, user_id: int = Depends(get_current_user)):
    """Delete a submission (requires auth, user can only delete their own)."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        submission = db.query(Submission).filter(
            Submission.id == submission_id,
            Submission.user_id == user_id
        ).first()
        
        if not submission:
            raise HTTPException(404, "Submission not found")
        
        db.delete(submission)
        db.commit()
        
        return {"message": "Submission deleted"}
    finally:
        db.close()
