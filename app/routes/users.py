"""
User profile and progress routes.
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.routes.auth import get_current_user
from app.models.db import User, Submission

router = APIRouter()


@router.get("/progress")
async def get_user_progress(user_id: int = Depends(get_current_user)):
    """Get user's progress (requires auth)."""
    db = SessionLocal()
    try:
        # Get distinct solved problems
        solved = db.query(Submission.problem_id).filter(
            Submission.user_id == user_id,
            Submission.passed == True
        ).distinct().count()
        
        # Get recent submissions
        recent = db.query(Submission).filter(
            Submission.user_id == user_id
        ).order_by(Submission.created_at.desc()).limit(10).all()
        
        return {
            "solved": solved,
            "streak": 0,  # TODO: Calculate actual streak
            "submissions": [
                {
                    "id": s.id,
                    "problem_id": s.problem_id,
                    "passed": s.passed,
                    "created_at": s.created_at.isoformat()
                }
                for s in recent
            ]
        }
    finally:
        db.close()


@router.get("/profile")
async def get_user_profile(user_id: int = Depends(get_current_user)):
    """Get complete user profile with stats and activity."""
    db = SessionLocal()
    try:
        # Get user info
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(404, "User not found")
        
        # Get submission stats
        total_submissions = db.query(Submission).filter(
            Submission.user_id == user_id
        ).count()
        
        passed_submissions = db.query(Submission).filter(
            Submission.user_id == user_id,
            Submission.passed == True
        ).count()
        
        # Get unique solved problems
        solved_problems = db.query(Submission.problem_id).filter(
            Submission.user_id == user_id,
            Submission.passed == True
        ).distinct().count()
        
        # Get difficulty breakdown
        from app.config import PROBLEMS_DIR
        import json
        
        difficulty_breakdown = {"easy": 0, "medium": 0, "hard": 0}
        solved_ids = db.query(Submission.problem_id).filter(
            Submission.user_id == user_id,
            Submission.passed == True
        ).distinct().all()
        
        for (pid,) in solved_ids:
            problem_file = PROBLEMS_DIR / f"problem_{pid:04d}.json"
            if problem_file.exists():
                with open(problem_file, "r") as f:
                    problem = json.load(f)
                    diff = problem.get("difficulty", "medium").lower()
                    if diff in difficulty_breakdown:
                        difficulty_breakdown[diff] += 1
        
        # Calculate success rate
        success_rate = (passed_submissions / total_submissions * 100) if total_submissions > 0 else 0
        
        # Get recent activity
        recent_activity = db.query(Submission).filter(
            Submission.user_id == user_id
        ).order_by(Submission.created_at.desc()).limit(10).all()
        
        return {
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "created_at": user.created_at.isoformat(),
                "avatar_url": None
            },
            "stats": {
                "problems_solved": solved_problems,
                "total_submissions": total_submissions,
                "success_rate": round(success_rate, 1),
                "streak": 0,  # TODO: Calculate
                "paths_completed": 0,  # TODO: Calculate
                "rank": "Beginner"  # TODO: Calculate
            },
            "difficulty_breakdown": difficulty_breakdown,
            "recent_activity": [
                {
                    "id": s.id,
                    "problem_id": s.problem_id,
                    "passed": s.passed,
                    "created_at": s.created_at.isoformat()
                }
                for s in recent_activity
            ],
            "calendar_data": []  # TODO: Implement
        }
    finally:
        db.close()
