"""
SQLAlchemy database models.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Index
from datetime import datetime

from app.database import Base


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Submission(Base):
    """Submission model for tracking user progress."""
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    problem_id = Column(Integer, index=True, nullable=False)
    code = Column(Text, nullable=False)
    passed = Column(Boolean, default=False)
    error = Column(Text, nullable=True)
    execution_time = Column(Integer, default=0)  # milliseconds
    created_at = Column(DateTime, default=datetime.utcnow)


class Quest(Base):
    """Quest model for storing learning quests as JSON."""
    __tablename__ = "quests"

    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, unique=True, index=True, nullable=False)
    data = Column(Text, nullable=False)  # Full quest JSON as string
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, nullable=True)  # User ID who created it


class QuestProgress(Base):
    """Track user progress on quest steps."""
    __tablename__ = "quest_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    problem_id = Column(Integer, index=True, nullable=False)
    step = Column(Integer, nullable=False)
    code = Column(Text, nullable=False)  # Saved solution code
    completed = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Index for querying user's progress on a problem
    __table_args__ = (
        Index('ix_quest_progress_user_problem', 'user_id', 'problem_id'),
    )


class ProblemSolution(Base):
    """Cached AI-generated solutions for problems."""
    __tablename__ = "problem_solutions"

    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, unique=True, index=True, nullable=False)
    solution = Column(Text, nullable=False)  # AI-generated solution code
    created_at = Column(DateTime, default=datetime.utcnow)


class Problem(Base):
    """Problem model for coding challenges."""
    __tablename__ = "problems"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    difficulty = Column(String(20), nullable=False)  # easy, medium, hard
    description = Column(Text, nullable=False)
    starter_code = Column(Text, nullable=False)
    example = Column(Text, nullable=True)  # JSON string: {input, output, reasoning}
    test_cases = Column(Text, nullable=False)  # JSON array
    learn_section = Column(Text, nullable=True)
    video = Column(String(255), nullable=True)
    # Framework variants
    pytorch_starter_code = Column(Text, nullable=True)
    pytorch_test_cases = Column(Text, nullable=True)
    tinygrad_starter_code = Column(Text, nullable=True)
    tinygrad_test_cases = Column(Text, nullable=True)
    cuda_starter_code = Column(Text, nullable=True)
    cuda_test_cases = Column(Text, nullable=True)
    # Playground visualization
    playground_enabled = Column(Boolean, default=False)
    playground_code = Column(Text, nullable=True)  # React component code
    created_at = Column(DateTime, default=datetime.utcnow)


