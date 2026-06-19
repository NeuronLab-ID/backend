"""
Tests for Manim animation configuration variables.
"""

from pathlib import Path

from app import config


class TestManim:
    """Test Manim configuration variables."""

    def test_manim_sandbox_image_default(self):
        """Test MANIM_SANDBOX_IMAGE has correct default value."""
        assert config.MANIM_SANDBOX_IMAGE == "deepml-sandbox-manim:latest"
        assert isinstance(config.MANIM_SANDBOX_IMAGE, str)

    def test_manim_render_quality_default(self):
        """Test MANIM_RENDER_QUALITY has correct default value."""
        assert config.MANIM_RENDER_QUALITY == "l"
        assert isinstance(config.MANIM_RENDER_QUALITY, str)

    def test_manim_gpu_enabled_default(self):
        """Test MANIM_GPU_ENABLED has correct default value (False)."""
        assert config.MANIM_GPU_ENABLED is False
        assert isinstance(config.MANIM_GPU_ENABLED, bool)

    def test_manim_timeout_default(self):
        """Test MANIM_TIMEOUT has correct default value."""
        assert config.MANIM_TIMEOUT == 120
        assert isinstance(config.MANIM_TIMEOUT, int)

    def test_manim_output_dir_default(self):
        """Test MANIM_OUTPUT_DIR has correct default value and is a Path."""
        assert isinstance(config.MANIM_OUTPUT_DIR, Path)
        expected_path = config.BASE_DIR / "media" / "manim"
        assert config.MANIM_OUTPUT_DIR == expected_path

    def test_manim_max_concurrent_renders_default(self):
        """Test MANIM_MAX_CONCURRENT_RENDERS has correct default value."""
        assert config.MANIM_MAX_CONCURRENT_RENDERS == 3
        assert isinstance(config.MANIM_MAX_CONCURRENT_RENDERS, int)
