# Quest Repository
# Handles all database operations for Quest, QuestProgress, and QuestReasoning

from sqlalchemy.orm import Session

from app.models.db import Quest, QuestProgress, QuestReasoning


class QuestRepository:
    """Repository for quest-related database operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_problem_id(self, problem_id: int) -> Quest | None:
        """Get quest by problem ID."""
        return self.db.query(Quest).filter(Quest.problem_id == problem_id).first()

    def save(self, quest: Quest) -> Quest:
        """Save a new quest."""
        self.db.add(quest)
        self.db.commit()
        self.db.refresh(quest)
        return quest

    def get_progress(self, user_id: int, problem_id: int) -> list[QuestProgress]:
        """Get all progress for a user's quest."""
        return (
            self.db.query(QuestProgress)
            .filter(QuestProgress.user_id == user_id, QuestProgress.problem_id == problem_id)
            .all()
        )

    def get_progress_by_step(self, user_id: int, problem_id: int, step: int) -> QuestProgress | None:
        """Get progress for a specific step."""
        return (
            self.db.query(QuestProgress)
            .filter(
                QuestProgress.user_id == user_id, QuestProgress.problem_id == problem_id, QuestProgress.step == step
            )
            .first()
        )

    def save_progress(self, progress: QuestProgress) -> QuestProgress:
        """Save quest progress."""
        self.db.add(progress)
        self.db.commit()
        return progress

    def update_progress(self, progress: QuestProgress, code: str, completed: bool = True) -> None:
        """Update existing progress."""
        progress.code = code
        progress.completed = completed
        self.db.commit()

    def get_reasoning(self, problem_id: int) -> QuestReasoning | None:
        """Get reasoning for a problem."""
        return self.db.query(QuestReasoning).filter(QuestReasoning.problem_id == problem_id).first()

    def save_reasoning(self, reasoning: QuestReasoning) -> QuestReasoning:
        """Save quest reasoning."""
        self.db.add(reasoning)
        self.db.commit()
        return reasoning

    def update_reasoning_data(self, problem_id: int, new_reasoning_data: str) -> bool:
        """Update reasoning data for a problem. Returns True if updated, False if not found."""
        reasoning = self.db.query(QuestReasoning).filter(QuestReasoning.problem_id == problem_id).first()
        if not reasoning:
            return False
        reasoning.reasoning_data = new_reasoning_data
        self.db.commit()
        return True

    def delete_reasoning(self, problem_id: int) -> None:
        """Delete reasoning for a problem."""
        self.db.query(QuestReasoning).filter(QuestReasoning.problem_id == problem_id).delete()
        self.db.commit()
