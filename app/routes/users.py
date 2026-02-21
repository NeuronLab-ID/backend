"""
User profile and progress routes.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db import User
from app.models.schemas import UserUpdate
from app.routes.auth import get_current_user
from app.services.user_stats_service import UserStatsService
from app.dependencies import get_user_stats_service

router = APIRouter()


@router.get("/progress")
async def get_user_progress(
    user_id: int = Depends(get_current_user),
    service: UserStatsService = Depends(get_user_stats_service),
):
    """Get user's progress (requires auth)."""
    return service.get_progress(user_id)


@router.get("/profile")
async def get_user_profile(
    user_id: int = Depends(get_current_user),
    service: UserStatsService = Depends(get_user_stats_service),
):
    """Get complete user profile with stats and activity."""
    profile = service.get_profile(user_id)
    if not profile:
        raise HTTPException(404, "User not found")
    return profile


@router.put("/profile")
async def update_user_profile(
    updates: UserUpdate,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: UserStatsService = Depends(get_user_stats_service),
):
    """Update user profile fields (requires auth)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    # Apply only non-None fields (partial update)
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    # Return full profile
    return service.get_profile(user_id)
