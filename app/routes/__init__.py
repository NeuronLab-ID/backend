# Routes package
from fastapi import APIRouter

from app.routes.auth import router as auth_router
from app.routes.problems import router as problems_router
from app.routes.execution import router as execution_router
from app.routes.submissions import router as submissions_router
from app.routes.quests import router as quests_router
from app.routes.hints import router as hints_router
from app.routes.users import router as users_router
from app.routes.math_samples import router as math_samples_router

# Aggregate all routers
api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(problems_router, prefix="/problems", tags=["problems"])
api_router.include_router(execution_router, tags=["execution"])
api_router.include_router(submissions_router, prefix="/submissions", tags=["submissions"])
api_router.include_router(quests_router, tags=["quests"])
api_router.include_router(hints_router, tags=["hints"])
api_router.include_router(users_router, prefix="/user", tags=["users"])
api_router.include_router(math_samples_router, tags=["math"])

