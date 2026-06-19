from sqlalchemy.orm import Session

from app.models.db import Submission


class SubmissionRepository:
    """Repository for submission queries."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_problem(self, user_id: int, problem_id: int, limit: int = 20) -> list[Submission]:
        return self.db.query(Submission).filter(
            Submission.user_id == user_id,
            Submission.problem_id == problem_id
        ).order_by(Submission.created_at.desc()).limit(limit).all()

    def create(self, submission: Submission) -> Submission:
        self.db.add(submission)
        self.db.commit()
        self.db.refresh(submission)
        return submission

    def delete(self, user_id: int, submission_id: int) -> bool:
        submission = self.db.query(Submission).filter(
            Submission.id == submission_id,
            Submission.user_id == user_id
        ).first()
        if not submission:
            return False
        self.db.delete(submission)
        self.db.commit()
        return True
