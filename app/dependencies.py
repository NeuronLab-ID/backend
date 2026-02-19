"""
FastAPI dependency injection providers.
Centralized DI for repositories, services, and controllers.
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.auth_repository import AuthRepository
from app.repositories.problem_repository import ProblemRepository
from app.repositories.submission_repository import SubmissionRepository
from app.repositories.quest_repository import QuestRepository
from app.repositories.user_repository import UserRepository
from app.services.user_stats_service import UserStatsService
from app.controllers import QuestController
from app.controllers.reasoning_controller import ReasoningController


# Repository providers
def get_auth_repo(db: Session = Depends(get_db)) -> AuthRepository:
    return AuthRepository(db)


def get_problem_repo(db: Session = Depends(get_db)) -> ProblemRepository:
    return ProblemRepository(db)


def get_submission_repo(db: Session = Depends(get_db)) -> SubmissionRepository:
    return SubmissionRepository(db)


def get_quest_repo(db: Session = Depends(get_db)) -> QuestRepository:
    return QuestRepository(db)


def get_user_repo(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


# Service providers
def get_user_stats_service(db: Session = Depends(get_db)) -> UserStatsService:
    return UserStatsService(db)


# Controller providers
def get_quest_controller(db: Session = Depends(get_db)) -> QuestController:
    return QuestController(db)


def get_reasoning_controller(db: Session = Depends(get_db)) -> ReasoningController:
    return ReasoningController(db)
