from sqlalchemy.orm import Session
from app.repositories.user_repository import UserRepository
from app.repositories.problem_repository import ProblemRepository


class UserStatsService:
    """Service for aggregating user statistics."""

    def __init__(self, db: Session):
        self.user_repo = UserRepository(db)
        self.problem_repo = ProblemRepository(db)

    def get_difficulty_breakdown(self, user_id: int) -> dict:
        solved_ids = self.user_repo.get_solved_problem_ids(user_id)
        breakdown = {"easy": 0, "medium": 0, "hard": 0}

        for pid in solved_ids:
            problem = self.problem_repo.get_by_id(pid)
            if problem and problem.difficulty in breakdown:
                breakdown[problem.difficulty] += 1

        return breakdown

    def get_profile(self, user_id: int) -> dict:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return None

        stats = self.user_repo.get_submission_stats(user_id)
        solved = self.user_repo.get_solved_count(user_id)
        recent = self.user_repo.get_recent_submissions(user_id)
        breakdown = self.get_difficulty_breakdown(user_id)

        success_rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0

        return {
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "created_at": user.created_at.isoformat(),
                "avatar_url": None
            },
            "stats": {
                "problems_solved": solved,
                "total_submissions": stats["total"],
                "success_rate": round(success_rate, 1),
                "streak": 0,  # TODO: Calculate
                "paths_completed": 0,  # TODO: Calculate
                "rank": "Beginner"  # TODO: Calculate
            },
            "difficulty_breakdown": breakdown,
            "recent_activity": [
                {
                    "id": s.id,
                    "problem_id": s.problem_id,
                    "passed": s.passed,
                    "created_at": s.created_at.isoformat()
                }
                for s in recent
            ],
            "calendar_data": []  # TODO: Implement
        }

    def get_progress(self, user_id: int) -> dict:
        solved = self.user_repo.get_solved_count(user_id)
        recent = self.user_repo.get_recent_submissions(user_id)

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
