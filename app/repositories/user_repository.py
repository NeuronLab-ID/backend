from datetime import date, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.db import Problem, Submission, User


class UserRepository:
    """Repository for user queries."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_solved_count(self, user_id: int) -> int:
        return (
            self.db.query(Submission.problem_id)
            .filter(Submission.user_id == user_id, Submission.passed.is_(True))
            .distinct()
            .count()
        )

    def get_submission_stats(self, user_id: int) -> dict:
        total = self.db.query(Submission).filter(Submission.user_id == user_id).count()
        passed = self.db.query(Submission).filter(Submission.user_id == user_id, Submission.passed.is_(True)).count()
        return {"total": total, "passed": passed}

    def get_recent_submissions(self, user_id: int, limit: int = 10) -> list[Submission]:
        return (
            self.db.query(Submission)
            .filter(Submission.user_id == user_id)
            .order_by(Submission.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_solved_problem_ids(self, user_id: int) -> list[int]:
        return [
            pid
            for (pid,) in self.db.query(Submission.problem_id)
            .filter(Submission.user_id == user_id, Submission.passed.is_(True))
            .distinct()
            .all()
        ]

    def get_activity_calendar(self, user_id: int, year: Optional[str] = None) -> dict[str, int]:
        query = self.db.query(func.date(Submission.created_at).label("date"), func.count().label("count")).filter(
            Submission.user_id == user_id
        )

        if year:
            query = query.filter(func.strftime("%Y", Submission.created_at) == year)

        results = query.group_by(func.date(Submission.created_at)).all()
        return {row.date: row.count for row in results}

    def get_category_progress(self, user_id: int) -> list[dict]:
        totals = self.db.query(Problem.category, func.count(Problem.id)).group_by(Problem.category).all()

        solved_ids = self.get_solved_problem_ids(user_id)
        solved_counts = {}
        if solved_ids:
            solved_counts = dict(
                self.db.query(Problem.category, func.count(Problem.id))
                .filter(Problem.id.in_(solved_ids))
                .group_by(Problem.category)
                .all()
            )

        return [
            {"name": category, "solved": solved_counts.get(category, 0), "total": total} for category, total in totals
        ]

    def get_streak(self, user_id: int) -> int:
        rows = (
            self.db.query(func.date(Submission.created_at))
            .filter(Submission.user_id == user_id)
            .distinct()
            .order_by(func.date(Submission.created_at).desc())
            .all()
        )

        if not rows:
            return 0

        dates = []
        for (value,) in rows:
            if isinstance(value, date):
                dates.append(value)
            else:
                dates.append(date.fromisoformat(value))

        current = dates[0]
        streak = 0
        for value in dates:
            if value == current:
                streak += 1
                current -= timedelta(days=1)
            else:
                break

        return streak
