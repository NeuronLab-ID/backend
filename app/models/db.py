"""
SQLAlchemy database models.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text, UniqueConstraint

from app.database import Base


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Profile fields
    display_name = Column(String(100), nullable=True)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)


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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Quest(Base):
    """Quest model for storing learning quests as JSON."""

    __tablename__ = "quests"

    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, unique=True, index=True, nullable=False)
    data = Column(Text, nullable=False)  # Full quest JSON as string
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Index for querying user's progress on a problem
    __table_args__ = (Index("ix_quest_progress_user_problem", "user_id", "problem_id"),)


class ProblemSolution(Base):
    """Cached AI-generated solutions for problems."""

    __tablename__ = "problem_solutions"

    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, unique=True, index=True, nullable=False)
    solution = Column(Text, nullable=False)  # AI-generated solution code
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class QuestReasoning(Base):
    """Cached AI-generated reasoning for quest problems."""

    __tablename__ = "quest_reasonings"

    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, unique=True, index=True, nullable=False)
    reasoning_data = Column(Text, nullable=False)  # JSON: {steps: [{step, title, reasoning}], summary}
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = Column(Integer, nullable=True)  # User ID who first generated it


class ReasoningExport(Base):
    """Cached AI-generated exports (markdown/LaTeX) for reasoning."""

    __tablename__ = "reasoning_exports"

    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, index=True, nullable=False)
    export_type = Column(String(20), nullable=False)  # 'markdown', 'latex', 'latex_sonnet'
    content = Column(Text, nullable=False)  # The generated markdown or LaTeX content
    ai_model = Column(String(50), nullable=True)  # e.g. 'pplx_alpha', 'sonnet'
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = Column(Integer, nullable=True)  # User ID who first generated it

    # Index for querying exports by problem and type
    __table_args__ = (Index("ix_reasoning_export_problem_type", "problem_id", "export_type"),)


class ManimAnimation(Base):
    """Cached manim animation renders for reasoning steps."""

    __tablename__ = "manim_animations"

    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, index=True, nullable=False)
    step_number = Column(Integer, nullable=False)
    video_type = Column(String(20), nullable=False, server_default="calculation")  # visualization, calculation
    status = Column(String(20), nullable=False, default="pending")  # pending, rendering, completed, error
    manim_code = Column(Text, nullable=True)
    video_path = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)
    render_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint("problem_id", "step_number", "video_type", name="uq_manim_problem_step_type"),)


class ManimRenderJob(Base):
    """Persisted async Manim render job lifecycle."""

    __tablename__ = "manim_render_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(64), unique=True, index=True, nullable=False)
    user_id = Column(Integer, index=True, nullable=False)
    problem_id = Column(Integer, index=True, nullable=False)
    step_number = Column(Integer, nullable=True)
    video_type = Column(String(20), nullable=True)
    requested_backend = Column(String(20), nullable=False, default="cpu")
    resolved_backend = Column(String(20), nullable=True)
    status = Column(String(32), nullable=False, default="queued", index=True)
    progress = Column(Integer, nullable=False, default=0)
    attempt = Column(Integer, nullable=False, default=1)
    max_attempts = Column(Integer, nullable=False, default=2)
    provider = Column(String(50), nullable=False, default="openai-compatible")
    model = Column(String(100), nullable=False, default="cx/gpt-5.5-xhigh")
    container_id = Column(String(128), nullable=True)
    animation_id = Column(Integer, nullable=True)
    request_hash = Column(String(64), nullable=True, index=True)
    idempotency_key = Column(String(128), nullable=True, index=True)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    logs_tail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    queued_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    cancel_requested_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    __table_args__ = (Index("ix_manim_render_jobs_status_created", "status", "created_at"),)
