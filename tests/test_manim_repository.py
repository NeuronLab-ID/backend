"""
Tests for ManimRepository CRUD operations.
"""

from datetime import datetime, timezone

import pytest

from app.models.db import ManimAnimation
from app.repositories.manim_repository import ManimRepository


@pytest.fixture
def manim_repo(db_session):
    """Create a ManimRepository instance for testing."""
    return ManimRepository(db_session)


class TestManimRepositoryCreate:
    """Test create operations."""

    def test_create_animation(self, manim_repo, db_session):
        """Test creating a new manim animation."""
        animation = manim_repo.create(problem_id=1, step_number=1, manim_code="class MyScene(Scene):\n    pass")

        assert animation.id is not None
        assert animation.problem_id == 1
        assert animation.step_number == 1
        assert animation.manim_code == "class MyScene(Scene):\n    pass"
        assert animation.status == "pending"
        assert animation.video_path is None
        assert animation.error_message is None
        assert animation.render_time_ms is None
        assert animation.created_at is not None

        # Verify persisted in DB
        persisted = db_session.query(ManimAnimation).filter(ManimAnimation.id == animation.id).first()
        assert persisted is not None
        assert persisted.status == "pending"

    def test_create_multiple_animations_same_problem(self, manim_repo):
        """Test creating multiple animations for the same problem."""
        anim1 = manim_repo.create(1, 1, "code1")
        anim2 = manim_repo.create(1, 2, "code2")
        anim3 = manim_repo.create(1, 3, "code3")

        assert anim1.step_number == 1
        assert anim2.step_number == 2
        assert anim3.step_number == 3
        assert anim1.problem_id == anim2.problem_id == anim3.problem_id == 1

    def test_create_animation_with_video_type(self, manim_repo):
        """Test creating an animation with explicit video_type."""
        animation = manim_repo.create(1, 1, "code", video_type="visualization")

        assert animation.video_type == "visualization"

    def test_create_animation_default_video_type(self, manim_repo):
        """Test that default video_type is 'calculation'."""
        animation = manim_repo.create(1, 1, "code")

        assert animation.video_type == "calculation"


class TestManimRepositoryGetByProblemId:
    """Test get_by_problem_id operations."""

    def test_get_by_problem_id_returns_all_animations(self, manim_repo):
        """Test retrieving all animations for a problem."""
        manim_repo.create(1, 1, "code1")
        manim_repo.create(1, 2, "code2")
        manim_repo.create(1, 3, "code3")
        manim_repo.create(2, 1, "code_other")

        animations = manim_repo.get_by_problem_id(1)

        assert len(animations) == 3
        assert all(a.problem_id == 1 for a in animations)
        assert [a.step_number for a in animations] == [1, 2, 3]

    def test_get_by_problem_id_empty(self, manim_repo):
        """Test retrieving animations for non-existent problem."""
        animations = manim_repo.get_by_problem_id(999)

        assert animations == []

    def test_get_by_problem_id_different_problems(self, manim_repo):
        """Test that animations are correctly filtered by problem."""
        manim_repo.create(1, 1, "code1")
        manim_repo.create(2, 1, "code2")
        manim_repo.create(3, 1, "code3")

        problem1 = manim_repo.get_by_problem_id(1)
        problem2 = manim_repo.get_by_problem_id(2)
        problem3 = manim_repo.get_by_problem_id(3)

        assert len(problem1) == 1
        assert len(problem2) == 1
        assert len(problem3) == 1
        assert problem1[0].problem_id == 1
        assert problem2[0].problem_id == 2
        assert problem3[0].problem_id == 3


class TestManimRepositoryGetByProblemAndStep:
    """Test get_by_problem_and_step operations."""

    def test_get_by_problem_and_step_found(self, manim_repo):
        """Test retrieving animation by problem and step."""
        manim_repo.create(1, 1, "code1")
        manim_repo.create(1, 2, "code2")

        animation = manim_repo.get_by_problem_and_step(1, 2)

        assert animation is not None
        assert animation.problem_id == 1
        assert animation.step_number == 2
        assert animation.manim_code == "code2"

    def test_get_by_problem_and_step_not_found(self, manim_repo):
        """Test retrieving non-existent animation."""
        manim_repo.create(1, 1, "code1")

        animation = manim_repo.get_by_problem_and_step(1, 999)

        assert animation is None

    def test_get_by_problem_and_step_wrong_problem(self, manim_repo):
        """Test that step is correctly filtered by problem."""
        manim_repo.create(1, 1, "code1")
        manim_repo.create(2, 1, "code2")

        animation = manim_repo.get_by_problem_and_step(2, 1)

        assert animation is not None
        assert animation.problem_id == 2
        assert animation.step_number == 1

    def test_get_by_problem_and_step_with_video_type(self, manim_repo):
        """Test filtering by video_type returns the correct animation."""
        manim_repo.create(1, 1, "calc_code", video_type="calculation")
        manim_repo.create(1, 1, "viz_code", video_type="visualization")

        animation = manim_repo.get_by_problem_and_step(1, 1, video_type="visualization")

        assert animation is not None
        assert animation.video_type == "visualization"
        assert animation.manim_code == "viz_code"

    def test_get_by_problem_and_step_without_video_type_returns_first(self, manim_repo):
        """Test that querying without video_type returns something (not None)."""
        manim_repo.create(1, 1, "calc_code", video_type="calculation")

        animation = manim_repo.get_by_problem_and_step(1, 1)

        assert animation is not None


class TestManimRepositoryGetByProblemStepAndType:
    """Test get_by_problem_step_and_type operations."""

    def test_get_by_problem_step_and_type(self, manim_repo):
        """Test retrieving animation by problem, step, and video type."""
        manim_repo.create(1, 1, "viz_code", video_type="visualization")
        manim_repo.create(1, 1, "calc_code", video_type="calculation")

        viz = manim_repo.get_by_problem_step_and_type(1, 1, "visualization")
        calc = manim_repo.get_by_problem_step_and_type(1, 1, "calculation")

        assert viz is not None
        assert viz.video_type == "visualization"
        assert viz.manim_code == "viz_code"

        assert calc is not None
        assert calc.video_type == "calculation"
        assert calc.manim_code == "calc_code"

    def test_get_by_problem_step_and_type_not_found(self, manim_repo):
        """Test that querying for a nonexistent type returns None."""
        manim_repo.create(1, 1, "calc_code", video_type="calculation")

        result = manim_repo.get_by_problem_step_and_type(1, 1, "visualization")

        assert result is None


class TestManimRepositoryExistsForStepAndType:
    """Test exists_for_step_and_type operations."""

    def test_exists_for_step_and_type_true(self, manim_repo):
        """Test that exists returns True when animation exists."""
        manim_repo.create(1, 2, "code", video_type="visualization")

        result = manim_repo.exists_for_step_and_type(1, 2, "visualization")

        assert result is True

    def test_exists_for_step_and_type_false(self, manim_repo):
        """Test that exists returns False when animation does not exist."""
        result = manim_repo.exists_for_step_and_type(1, 99, "calculation")

        assert result is False


class TestManimRepositoryUpdateStatus:
    """Test update_status operations."""

    def test_update_status_to_rendering(self, manim_repo, db_session):
        """Test updating status to rendering."""
        animation = manim_repo.create(1, 1, "code")
        original_created_at = animation.created_at

        updated = manim_repo.update_status(animation.id, "rendering")

        assert updated.status == "rendering"
        assert updated.created_at == original_created_at
        assert updated.updated_at is not None

        # Verify persisted
        persisted = db_session.query(ManimAnimation).filter(ManimAnimation.id == animation.id).first()
        assert persisted.status == "rendering"

    def test_update_status_to_completed_with_video_path(self, manim_repo):
        """Test updating status to completed with video path."""
        animation = manim_repo.create(1, 1, "code")

        updated = manim_repo.update_status(
            animation.id, "completed", video_path="/videos/anim_1_1.mp4", render_time_ms=5000
        )

        assert updated.status == "completed"
        assert updated.video_path == "/videos/anim_1_1.mp4"
        assert updated.render_time_ms == 5000
        assert updated.error_message is None
        assert updated.updated_at is not None

    def test_update_status_to_error_with_message(self, manim_repo):
        """Test updating status to error with error message."""
        animation = manim_repo.create(1, 1, "code")

        updated = manim_repo.update_status(animation.id, "error", error_message="Syntax error in manim code")

        assert updated.status == "error"
        assert updated.error_message == "Syntax error in manim code"
        assert updated.video_path is None
        assert updated.render_time_ms is None
        assert updated.updated_at is not None

    def test_update_status_sets_updated_at_to_utc_now(self, manim_repo):
        """Test that updated_at is set to current UTC time."""
        animation = manim_repo.create(1, 1, "code")
        before_update = datetime.now(timezone.utc)

        updated = manim_repo.update_status(animation.id, "rendering")

        after_update = datetime.now(timezone.utc)
        # Handle both naive and aware datetimes
        updated_at = updated.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        assert before_update <= updated_at <= after_update

    def test_update_status_partial_fields(self, manim_repo):
        """Test updating only some fields."""
        animation = manim_repo.create(1, 1, "code")

        # Update with only status and video_path
        updated = manim_repo.update_status(animation.id, "completed", video_path="/videos/test.mp4")

        assert updated.status == "completed"
        assert updated.video_path == "/videos/test.mp4"
        assert updated.error_message is None
        assert updated.render_time_ms is None


class TestManimRepositoryGetStatusSummary:
    """Test get_status_summary operations."""

    def test_get_status_summary_all_pending(self, manim_repo):
        """Test summary when all animations are pending."""
        manim_repo.create(1, 1, "code1")
        manim_repo.create(1, 2, "code2")
        manim_repo.create(1, 3, "code3")

        summary = manim_repo.get_status_summary(1, 3)

        assert summary["problem_id"] == 1
        assert summary["total_steps"] == 3
        assert summary["completed_count"] == 0
        assert summary["rendering_count"] == 0
        assert summary["error_count"] == 0
        assert summary["pending_count"] == 3
        assert "animations" in summary
        assert len(summary["animations"]) == 3
        assert all(a["status"] == "pending" for a in summary["animations"])

    def test_get_status_summary_mixed_statuses(self, manim_repo):
        """Test summary with mixed statuses."""
        anim1 = manim_repo.create(1, 1, "code1")
        anim2 = manim_repo.create(1, 2, "code2")
        anim3 = manim_repo.create(1, 3, "code3")
        manim_repo.create(1, 4, "code4")

        # Update statuses
        manim_repo.update_status(anim1.id, "completed", video_path="/v1.mp4")
        manim_repo.update_status(anim2.id, "rendering")
        manim_repo.update_status(anim3.id, "error", error_message="Failed")
        # anim4 stays pending

        summary = manim_repo.get_status_summary(1, 4)

        assert summary["problem_id"] == 1
        assert summary["total_steps"] == 4
        assert summary["completed_count"] == 1
        assert summary["rendering_count"] == 1
        assert summary["error_count"] == 1
        assert summary["pending_count"] == 1
        assert "animations" in summary
        assert len(summary["animations"]) == 4
        # Verify animations are sorted by step_number
        assert [a["step_number"] for a in summary["animations"]] == [1, 2, 3, 4]

    def test_get_status_summary_no_animations(self, manim_repo):
        """Test summary when no animations exist."""
        summary = manim_repo.get_status_summary(999, 5)

        assert summary["problem_id"] == 999
        assert summary["total_steps"] == 5
        assert summary["completed_count"] == 0
        assert summary["rendering_count"] == 0
        assert summary["error_count"] == 0
        assert summary["pending_count"] == 0
        assert "animations" in summary
        assert summary["animations"] == []

    def test_get_status_summary_all_completed(self, manim_repo):
        """Test summary when all animations are completed."""
        anim1 = manim_repo.create(1, 1, "code1")
        anim2 = manim_repo.create(1, 2, "code2")

        manim_repo.update_status(anim1.id, "completed", video_path="/v1.mp4")
        manim_repo.update_status(anim2.id, "completed", video_path="/v2.mp4")

        summary = manim_repo.get_status_summary(1, 2)

        assert summary["completed_count"] == 2
        assert summary["rendering_count"] == 0
        assert summary["error_count"] == 0
        assert summary["pending_count"] == 0
        assert "animations" in summary
        assert len(summary["animations"]) == 2
        assert all(a["status"] == "completed" for a in summary["animations"])

    def test_get_status_summary_ignores_other_problems(self, manim_repo):
        """Test that summary only counts animations for the specified problem."""
        anim1 = manim_repo.create(1, 1, "code1")
        anim2 = manim_repo.create(2, 1, "code2")

        manim_repo.update_status(anim1.id, "completed", video_path="/v1.mp4")
        manim_repo.update_status(anim2.id, "rendering")

        summary = manim_repo.get_status_summary(1, 1)

        assert summary["problem_id"] == 1
        assert summary["completed_count"] == 1
        assert summary["rendering_count"] == 0
        assert summary["pending_count"] == 0
        assert "animations" in summary
        assert len(summary["animations"]) == 1
        assert summary["animations"][0]["problem_id"] == 1

    def test_get_status_summary_animation_structure(self, manim_repo):
        """Test that animation dicts have correct structure and field mapping."""
        anim = manim_repo.create(1, 1, "code1")
        manim_repo.update_status(anim.id, "completed", video_path="/videos/test.mp4", render_time_ms=5000)

        summary = manim_repo.get_status_summary(1, 1)

        assert len(summary["animations"]) == 1
        animation_dict = summary["animations"][0]

        # Verify all required fields exist
        assert "id" in animation_dict
        assert "problem_id" in animation_dict
        assert "step_number" in animation_dict
        assert "status" in animation_dict
        assert "video_url" in animation_dict
        assert "error_message" in animation_dict
        assert "render_time_ms" in animation_dict
        assert "created_at" in animation_dict

        # Verify field values and mapping
        assert animation_dict["id"] == anim.id
        assert animation_dict["problem_id"] == 1
        assert animation_dict["step_number"] == 1
        assert animation_dict["status"] == "completed"
        assert animation_dict["video_url"] == "/videos/test.mp4"  # Mapped from video_path
        assert animation_dict["error_message"] is None
        assert animation_dict["render_time_ms"] == 5000
        assert animation_dict["created_at"] is not None
        # Verify created_at is ISO 8601 string
        assert isinstance(animation_dict["created_at"], str)
        assert "T" in animation_dict["created_at"]

    def test_get_status_summary_includes_video_type(self, manim_repo):
        """Test that animation dicts in summary include the video_type field."""
        manim_repo.create(1, 1, "viz_code", video_type="visualization")

        summary = manim_repo.get_status_summary(1, 1)

        assert len(summary["animations"]) == 1
        animation_dict = summary["animations"][0]
        assert "video_type" in animation_dict
        assert animation_dict["video_type"] == "visualization"
