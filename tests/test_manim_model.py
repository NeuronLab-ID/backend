"""
Tests for ManimAnimation model.
"""

from datetime import datetime, timezone

from app.models.db import ManimAnimation


def test_manim_animation_creation(db_session):
    """Test creating a ManimAnimation instance."""
    anim = ManimAnimation(
        problem_id=1,
        step_number=1,
        status="pending",
        manim_code="from manim import *",
        video_path=None,
        error_message=None,
        render_time_ms=None,
    )
    db_session.add(anim)
    db_session.commit()
    db_session.refresh(anim)

    assert anim.id is not None
    assert anim.problem_id == 1
    assert anim.step_number == 1
    assert anim.status == "pending"
    assert anim.manim_code == "from manim import *"
    assert anim.video_path is None
    assert anim.error_message is None
    assert anim.render_time_ms is None
    assert anim.created_at is not None
    assert isinstance(anim.created_at, datetime)


def test_manim_animation_default_status(db_session):
    """Test that default status is 'pending'."""
    anim = ManimAnimation(
        problem_id=1,
        step_number=1,
    )
    db_session.add(anim)
    db_session.commit()
    db_session.refresh(anim)

    assert anim.status == "pending"


def test_manim_animation_created_at_defaults_to_utc_now(db_session):
    """Test that created_at defaults to UTC now."""
    before = datetime.now(timezone.utc)
    anim = ManimAnimation(
        problem_id=1,
        step_number=1,
    )
    db_session.add(anim)
    db_session.commit()
    db_session.refresh(anim)
    after = datetime.now(timezone.utc)

    assert anim.created_at is not None
    # Handle both naive and aware datetimes
    created_at = anim.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    assert before <= created_at <= after


def test_manim_animation_all_fields(db_session):
    """Test creating ManimAnimation with all fields populated."""
    anim = ManimAnimation(
        problem_id=42,
        step_number=3,
        status="completed",
        manim_code="class MyScene(Scene):\n    def construct(self):\n        pass",
        video_path="/tmp/output.mp4",
        error_message=None,
        render_time_ms=5000,
    )
    db_session.add(anim)
    db_session.commit()
    db_session.refresh(anim)

    assert anim.problem_id == 42
    assert anim.step_number == 3
    assert anim.status == "completed"
    assert anim.manim_code == "class MyScene(Scene):\n    def construct(self):\n        pass"
    assert anim.video_path == "/tmp/output.mp4"
    assert anim.error_message is None
    assert anim.render_time_ms == 5000


def test_manim_animation_error_status(db_session):
    """Test ManimAnimation with error status."""
    anim = ManimAnimation(
        problem_id=1,
        step_number=1,
        status="error",
        error_message="Syntax error in manim code",
    )
    db_session.add(anim)
    db_session.commit()
    db_session.refresh(anim)

    assert anim.status == "error"
    assert anim.error_message == "Syntax error in manim code"


def test_manim_animation_composite_index(db_session):
    """Test that composite index on (problem_id, step_number) exists."""
    # Create multiple animations for same problem, different steps
    anim1 = ManimAnimation(problem_id=1, step_number=1)
    anim2 = ManimAnimation(problem_id=1, step_number=2)
    anim3 = ManimAnimation(problem_id=2, step_number=1)

    db_session.add_all([anim1, anim2, anim3])
    db_session.commit()

    # Verify we can query by problem_id and step_number
    result = (
        db_session.query(ManimAnimation)
        .filter(
            ManimAnimation.problem_id == 1,
            ManimAnimation.step_number == 2,
        )
        .first()
    )

    assert result is not None
    assert result.problem_id == 1
    assert result.step_number == 2


def test_manim_animation_updated_at_nullable(db_session):
    """Test that updated_at is nullable."""
    anim = ManimAnimation(
        problem_id=1,
        step_number=1,
    )
    db_session.add(anim)
    db_session.commit()
    db_session.refresh(anim)

    assert anim.updated_at is None
