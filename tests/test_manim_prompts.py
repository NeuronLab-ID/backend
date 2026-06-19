"""Tests for Manim prompt templates."""

import re

from app.prompts import (
    get_manim_code_prompt,
    get_manim_code_system_prompt,
    get_manim_visualization_prompt,
    get_manim_visualization_system_prompt,
)


def _has_negative_constraint(text: str) -> bool:
    return bool(re.search(r"Do NOT|Do not|NEVER|MUST NOT", text))


def test_get_manim_code_system_prompt_returns_string():
    result = get_manim_code_system_prompt()
    assert isinstance(result, str)


def test_get_manim_code_system_prompt_contains_negative_constraints():
    result = get_manim_code_system_prompt()
    assert _has_negative_constraint(result)


def test_get_manim_code_system_prompt_interpolation():
    result = get_manim_code_system_prompt()
    assert "ManimCE" in result


def test_get_manim_code_prompt_returns_string():
    result = get_manim_code_prompt(
        step_number=2,
        step_title="Normalize the vector",
        step_reasoning="We compute the magnitude and divide each component.",
        key_formulas=[
            {
                "name": "Magnitude",
                "latex": "\\|\\vec{v}\\| = \\sqrt{v_x^2 + v_y^2}",
                "description": "Euclidean norm for 2D vectors.",
            }
        ],
        problem_title="Vector Normalization",
        problem_description="Normalize a 2D vector to unit length.",
    )
    assert isinstance(result, str)


def test_get_manim_code_prompt_contains_negative_constraints():
    result = get_manim_code_prompt(
        step_number=1,
        step_title="Show the vector",
        step_reasoning="Introduce the vector on a number plane.",
        key_formulas=[],
        problem_title="Vector Setup",
        problem_description="Display the vector components.",
    )
    assert _has_negative_constraint(result)


def test_get_manim_code_prompt_interpolation():
    result = get_manim_code_prompt(
        step_number=3,
        step_title="Scale to unit length",
        step_reasoning="Divide the vector by its magnitude.",
        key_formulas=[
            {
                "name": "Unit Vector",
                "latex": "\\hat{v} = \\vec{v} / \\|\\vec{v}\\|",
                "description": "Normalize by magnitude.",
            }
        ],
        problem_title="Unit Vector",
        problem_description="Create a unit vector from v.",
    )
    assert "Scale to unit length" in result
    assert "Unit Vector" in result
    assert "Normalize by magnitude." in result


def test_get_manim_visualization_system_prompt_returns_string():
    result = get_manim_visualization_system_prompt()
    assert isinstance(result, str)


def test_get_manim_visualization_system_prompt_contains_negative_constraints():
    result = get_manim_visualization_system_prompt()
    assert _has_negative_constraint(result)


def test_get_manim_visualization_prompt_returns_string():
    result = get_manim_visualization_prompt(
        step_number=2,
        step_title="Normalize the vector",
        step_reasoning="We compute the magnitude and divide each component.",
        key_formulas=[
            {
                "name": "Magnitude",
                "latex": "\\|\\vec{v}\\| = \\sqrt{v_x^2 + v_y^2}",
                "description": "Euclidean norm for 2D vectors.",
            }
        ],
        problem_title="Vector Normalization",
        problem_description="Normalize a 2D vector to unit length.",
    )
    assert isinstance(result, str)


def test_get_manim_visualization_prompt_contains_negative_constraints():
    result = get_manim_visualization_prompt(
        step_number=1,
        step_title="Show the vector",
        step_reasoning="Introduce the vector on a number plane.",
        key_formulas=[],
        problem_title="Vector Setup",
        problem_description="Display the vector components.",
    )
    assert _has_negative_constraint(result)


def test_get_manim_visualization_prompt_interpolation():
    result = get_manim_visualization_prompt(
        step_number=4,
        step_title="Visualize the transformation",
        step_reasoning="Show how the matrix transforms the space.",
        key_formulas=[],
        problem_title="Matrix Transformation",
        problem_description="Apply a 2D linear transformation.",
    )
    assert "Visualize the transformation" in result
    assert "Matrix Transformation" in result


def test_visualization_and_calculation_prompts_differ():
    calc_system = get_manim_code_system_prompt()
    viz_system = get_manim_visualization_system_prompt()
    assert calc_system != viz_system

    shared_args = (
        1,
        "Compute dot product",
        "Multiply element-wise and sum.",
        [],
        "Dot Product",
        "Compute the dot product of two vectors.",
    )
    calc_prompt = get_manim_code_prompt(*shared_args)
    viz_prompt = get_manim_visualization_prompt(*shared_args)
    assert calc_prompt != viz_prompt
