import json
from typing import Optional

from sqlalchemy.orm import Session

from app.models.db import Quest, QuestProgress
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

    def get_profile(self, user_id: int) -> Optional[dict]:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return None

        stats = self.user_repo.get_submission_stats(user_id)
        solved = self.user_repo.get_solved_count(user_id)
        recent = self.user_repo.get_recent_submissions(user_id)
        breakdown = self.get_difficulty_breakdown(user_id)
        streak = self.user_repo.get_streak(user_id)

        if solved == 0:
            rank = "Beginner"
        elif 1 <= solved <= 5:
            rank = "Novice"
        elif 6 <= solved <= 15:
            rank = "Intermediate"
        elif 16 <= solved <= 30:
            rank = "Advanced"
        else:
            rank = "Expert"

        success_rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        calendar_data = self.user_repo.get_activity_calendar(user_id)
        category_progress = self.user_repo.get_category_progress(user_id)

        progress_rows = (
            self.user_repo.db.query(QuestProgress.problem_id, QuestProgress.step)
            .filter(QuestProgress.user_id == user_id, QuestProgress.completed == True)
            .all()
        )

        progress_steps = {}
        for problem_id, step in progress_rows:
            progress_steps.setdefault(problem_id, set()).add(step)

        paths_completed = 0
        for quest in self.user_repo.db.query(Quest).all():
            if not quest.data:
                continue
            try:
                quest_data = json.loads(quest.data)
            except json.JSONDecodeError:
                continue

            steps = quest_data.get("sub_quests") or quest_data.get("steps") or []
            total_steps = len(steps)
            if total_steps == 0:
                continue

            if len(progress_steps.get(quest.problem_id, set())) >= total_steps:
                paths_completed += 1

        achievements = [
            {
                "name": "First Blood",
                "description": "Solve your first problem",
                "unlocked": solved >= 1,
                "unlocked_at": None,
            },
            {
                "name": "Getting Started",
                "description": "Solve 5 problems",
                "unlocked": solved >= 5,
                "unlocked_at": None,
            },
            {
                "name": "Problem Solver",
                "description": "Solve 10 problems",
                "unlocked": solved >= 10,
                "unlocked_at": None,
            },
            {
                "name": "Streak Master",
                "description": "7-day solve streak",
                "unlocked": streak >= 7,
                "unlocked_at": None,
            },
            {
                "name": "Centurion",
                "description": "100 total submissions",
                "unlocked": stats["total"] >= 100,
                "unlocked_at": None,
            },
            {
                "name": "Perfectionist",
                "description": "100% success rate on a submission",
                "unlocked": stats["passed"] > 0,
                "unlocked_at": None,
            },
        ]

        return {
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "created_at": user.created_at.isoformat(),
                "display_name": user.display_name,
                "bio": user.bio,
                "avatar_url": user.avatar_url,
            },
            "stats": {
                "problems_solved": solved,
                "total_submissions": stats["total"],
                "success_rate": round(success_rate, 1),
                "streak": streak,
                "paths_completed": paths_completed,
                "rank": rank,
            },
            "difficulty_breakdown": breakdown,
            "recent_activity": [
                {"id": s.id, "problem_id": s.problem_id, "passed": s.passed, "created_at": s.created_at.isoformat()}
                for s in recent
            ],
            "calendar_data": calendar_data,
            "category_progress": category_progress,
            "achievements": achievements,
        }

    def get_progress(self, user_id: int) -> dict:
        solved = self.user_repo.get_solved_count(user_id)
        recent = self.user_repo.get_recent_submissions(user_id)

        return {
            "solved": solved,
            "streak": self.user_repo.get_streak(user_id),
            "submissions": [
                {"id": s.id, "problem_id": s.problem_id, "passed": s.passed, "created_at": s.created_at.isoformat()}
                for s in recent
            ],
        }
