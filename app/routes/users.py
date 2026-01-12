"""
User profile and progress routes.
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.routes.auth import get_current_user
from app.services.user_stats_service import UserStatsService

router = APIRouter()


@router.get("/progress")
async def get_user_progress(
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's progress (requires auth)."""
    service = UserStatsService(db)
    return service.get_progress(user_id)


@router.get("/profile")
async def get_user_profile(
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get complete user profile with stats and activity."""
    service = UserStatsService(db)
    profile = service.get_profile(user_id)
    if not profile:
        raise HTTPException(404, "User not found")
    return profile
