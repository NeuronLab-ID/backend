import asyncio
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from app.services.manim_service import ManimService, _strip_code_fences


def test_generate_animation_success() -> None:
    manim_code = "from manim import *\nclass MainScene(Scene):\n    pass"
    mock_provider = MagicMock()
    mock_provider.generate_reasoning = AsyncMock(return_value=manim_code)

    mock_repo = MagicMock()
    animation = MagicMock()
    animation.id = 123
    mock_repo.create.return_value = animation
    mock_repo.get_by_problem_and_step.return_value = animation

    with (
        patch("app.services.manim_service.ManimRepository", return_value=mock_repo),
        patch("app.services.manim_service.get_reasoning_provider", return_value=mock_provider),
        patch("app.services.manim_service.manim_executor") as mock_executor,
    ):
        mock_executor.render = AsyncMock(return_value={"status": "success", "video_path": "video.mp4"})
        service = ManimService(MagicMock())
        reasoning_data = {
            "step_title": "Intro",
            "step_reasoning": "Explain the concept",
            "key_formulas": [{"name": "x", "latex": "x"}],
            "problem_title": "Sample",
            "problem_description": "Desc",
        }
        result = asyncio.get_event_loop().run_until_complete(service.generate_animation(1, 2, reasoning_data))

    assert result == animation
    mock_repo.create.assert_called_once_with(1, 2, manim_code)
    assert mock_repo.update_status.call_args_list[0].args[:2] == (animation.id, "rendering")
    assert mock_repo.update_status.call_args_list[1].args[:2] == (animation.id, "completed")
    assert mock_repo.update_status.call_args_list[1].kwargs == {
        "video_path": "video.mp4",
        "render_time_ms": ANY,
    }


def test_generate_animation_render_failure() -> None:
    manim_code = "from manim import *\nclass MainScene(Scene):\n    pass"
    mock_provider = MagicMock()
    mock_provider.generate_reasoning = AsyncMock(return_value=manim_code)

    mock_repo = MagicMock()
    animation = MagicMock()
    animation.id = 456
    mock_repo.create.return_value = animation
    mock_repo.get_by_problem_and_step.return_value = animation

    with (
        patch("app.services.manim_service.ManimRepository", return_value=mock_repo),
        patch("app.services.manim_service.get_reasoning_provider", return_value=mock_provider),
        patch("app.services.manim_service.manim_executor") as mock_executor,
    ):
        mock_executor.render = AsyncMock(return_value={"status": "error", "error": "boom"})
        service = ManimService(MagicMock())
        reasoning_data = {
            "step_title": "Intro",
            "step_reasoning": "Explain",
            "key_formulas": [],
            "problem_title": "Sample",
            "problem_description": "Desc",
        }
        result = asyncio.get_event_loop().run_until_complete(service.generate_animation(2, 1, reasoning_data))

    assert result == animation
    assert mock_repo.update_status.call_args_list[0].args[:2] == (animation.id, "rendering")
    assert mock_repo.update_status.call_args_list[1].args[:2] == (animation.id, "error")
    assert mock_repo.update_status.call_args_list[1].kwargs == {
        "error_message": "boom",
        "render_time_ms": ANY,
    }


def test_generate_all_animations() -> None:
    mock_provider = MagicMock()
    mock_provider.generate_reasoning = AsyncMock(return_value="code")
    mock_repo = MagicMock()

    with (
        patch("app.services.manim_service.ManimRepository", return_value=mock_repo),
        patch("app.services.manim_service.get_reasoning_provider", return_value=mock_provider),
    ):
        service = ManimService(MagicMock())
        service.generate_animation = AsyncMock(side_effect=["anim1", "anim2"])
        reasoning_data = {
            "problem_title": "Sample",
            "problem_description": "Desc",
            "steps": [
                {"title": "Step A", "reasoning": "A"},
                {"title": "Step B", "reasoning": "B"},
            ],
        }
        result = asyncio.get_event_loop().run_until_complete(service.generate_all_animations(5, reasoning_data))

    assert result == ["anim1", "anim2"]
    assert service.generate_animation.call_args_list[0].args[0:2] == (5, 1)
    assert service.generate_animation.call_args_list[1].args[0:2] == (5, 2)


def test_get_animation_status_delegates() -> None:
    mock_repo = MagicMock()
    mock_repo.get_status_summary.return_value = {"completed": 1}

    with (
        patch("app.services.manim_service.ManimRepository", return_value=mock_repo),
        patch("app.services.manim_service.get_reasoning_provider", return_value=MagicMock()),
    ):
        service = ManimService(MagicMock())
        result = service.get_animation_status(3, 2)

    assert result == {"completed": 1}
    mock_repo.get_status_summary.assert_called_once_with(3, 2)


def test_get_animation_delegates() -> None:
    mock_repo = MagicMock()
    animation = MagicMock()
    mock_repo.get_by_problem_and_step.return_value = animation

    with (
        patch("app.services.manim_service.ManimRepository", return_value=mock_repo),
        patch("app.services.manim_service.get_reasoning_provider", return_value=MagicMock()),
    ):
        service = ManimService(MagicMock())
        result = service.get_animation(9, 4)

    assert result == animation
    mock_repo.get_by_problem_and_step.assert_called_once_with(9, 4)


def test_generate_animation_ai_failure() -> None:
    mock_provider = MagicMock()
    mock_provider.generate_reasoning = AsyncMock(side_effect=Exception("boom"))
    mock_repo = MagicMock()

    with (
        patch("app.services.manim_service.ManimRepository", return_value=mock_repo),
        patch("app.services.manim_service.get_reasoning_provider", return_value=mock_provider),
    ):
        service = ManimService(MagicMock())
        reasoning_data = {
            "step_title": "Intro",
            "step_reasoning": "Explain",
            "key_formulas": [],
            "problem_title": "Sample",
            "problem_description": "Desc",
        }
        with pytest.raises(Exception, match="boom"):
            asyncio.get_event_loop().run_until_complete(service.generate_animation(1, 1, reasoning_data))

    mock_repo.create.assert_not_called()


def test_strip_code_fences_with_python_fence() -> None:
    """Test stripping ```python wrapped code."""
    code_with_fence = """```python
from manim import *
class MainScene(Scene):
    def construct(self):
        pass
```"""
    expected = """from manim import *
class MainScene(Scene):
    def construct(self):
        pass"""
    assert _strip_code_fences(code_with_fence) == expected


def test_strip_code_fences_with_generic_fence() -> None:
    """Test stripping ``` (no language) wrapped code."""
    code_with_fence = """```
from manim import *
class MainScene(Scene):
    pass
```"""
    expected = """from manim import *
class MainScene(Scene):
    pass"""
    assert _strip_code_fences(code_with_fence) == expected


def test_strip_code_fences_with_clean_code() -> None:
    """Test that clean code (no fences) is returned unchanged."""
    clean_code = """from manim import *
class MainScene(Scene):
    def construct(self):
        pass"""
    assert _strip_code_fences(clean_code) == clean_code


def test_strip_code_fences_with_empty_string() -> None:
    """Test that empty string returns empty string."""
    assert _strip_code_fences("") == ""
    assert _strip_code_fences(None or "") == ""
