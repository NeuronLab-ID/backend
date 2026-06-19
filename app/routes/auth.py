"""
Authentication routes.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.dependencies import get_auth_repo
from app.models.db import User
from app.models.schemas import Token, UserCreate, UserLogin, UserResponse
from app.repositories.auth_repository import AuthRepository
from app.services.auth_service import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter()
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    """Verify JWT token and return user_id."""
    user_id = decode_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(401, "Invalid or expired token")
    return user_id


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate, repo: AuthRepository = Depends(get_auth_repo)
):
    """Register a new user."""
    if repo.get_by_email(user_data.email):
        raise HTTPException(400, "Email already registered")
    if repo.get_by_username(user_data.username):
        raise HTTPException(400, "Username already taken")

    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
    )
    user = repo.create(user)

    return UserResponse(
        id=user.id, username=user.username, email=user.email, created_at=user.created_at
    )


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, repo: AuthRepository = Depends(get_auth_repo)):
    """Login and get JWT token."""
    user = repo.get_by_email(credentials.email)

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")

    token = create_access_token(user.id)
    return Token(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    user_id: int = Depends(get_current_user),
    repo: AuthRepository = Depends(get_auth_repo),
):
    """Get current user info."""
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")

    return UserResponse(
        id=user.id, username=user.username, email=user.email, created_at=user.created_at
    )
