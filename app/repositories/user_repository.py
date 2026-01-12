from sqlalchemy.orm import Session
from app.models.db import User, Submission


class UserRepository:
    """Repository for user queries."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_solved_count(self, user_id: int) -> int:
        return self.db.query(Submission.problem_id).filter(
            Submission.user_id == user_id,
            Submission.passed == True
        ).distinct().count()

    def get_submission_stats(self, user_id: int) -> dict:
        total = self.db.query(Submission).filter(Submission.user_id == user_id).count()
        passed = self.db.query(Submission).filter(
            Submission.user_id == user_id, Submission.passed == True
        ).count()
        return {"total": total, "passed": passed}

    def get_recent_submissions(self, user_id: int, limit: int = 10) -> list[Submission]:
        return self.db.query(Submission).filter(
            Submission.user_id == user_id
        ).order_by(Submission.created_at.desc()).limit(limit).all()

    def get_solved_problem_ids(self, user_id: int) -> list[int]:
        return [pid for (pid,) in self.db.query(Submission.problem_id).filter(
            Submission.user_id == user_id, Submission.passed == True
        ).distinct().all()]
