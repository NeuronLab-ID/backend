"""Route-level API contract tests.

These tests pin the current HTTP response shapes for the problem, quest, and
submission routes so the frontend and backend contracts stay aligned. They are
intentionally route-level: external work (AI, Docker, filesystem) is patched so
only the wiring and response envelopes are asserted.
"""

import json
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

from app.models.db import Problem, ProblemSolution, Quest, ReasoningExport, Submission, User
from app.routes.auth import get_current_user

AUTHENTICATED_USER_ID = 1


@contextmanager
def authenticated(client):
    from main import app

    app.dependency_overrides[get_current_user] = lambda: AUTHENTICATED_USER_ID
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_problem_list_contract(client, sample_problem):
    response = client.get("/api/problems")
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"problems", "total"}
    assert data["total"] == 1
    item = data["problems"][0]
    assert set(item.keys()) == {"id", "title", "category", "difficulty", "has_quest"}
    assert item["has_quest"] is False


def test_quest_check_contract_uses_available(client, sample_problem):
    with authenticated(client) as authed_client, patch("app.services.quest_service.Path.exists", return_value=False):
        response = authed_client.get(
            f"/api/quests/check/{sample_problem.id}",
        )
    assert response.status_code == 200
    data = response.json()
    assert "available" in data
    assert "exists" not in data
    assert data["available"] is False
    assert data["can_generate"] is True


def test_quest_fetch_contract_is_wrapped(client, db_session, sample_problem):
    quest_payload = {
        "problem_id": sample_problem.id,
        "title": sample_problem.title,
        "category": sample_problem.category,
        "difficulty": sample_problem.difficulty,
        "description": "Test quest description",
        "example": {"input": "x", "output": "y", "reasoning": "z"},
        "starter_code": "def solution():\n    pass",
        "sub_quests": [],
    }
    db_session.add(Quest(problem_id=sample_problem.id, data=json.dumps(quest_payload)))
    db_session.commit()
    with authenticated(client) as authed_client:
        response = authed_client.get(f"/api/quests/{sample_problem.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["quest"] == quest_payload
    assert data["source"] == "database"
    assert data["problem_id"] == sample_problem.id


def test_quest_create_contract_uses_create_route(client, sample_problem):
    from app.routes import quests as quest_routes

    with authenticated(client) as authed_client, patch.object(
        quest_routes,
        "create_quest",
        new=AsyncMock(return_value={"message": "Quest created", "id": 123}),
    ) as create_quest:
        response = authed_client.post(
            "/api/quests/create",
            json={"problem_id": sample_problem.id, "data": {"sub_quests": []}},
        )
    assert response.status_code == 200
    assert response.json() == {"message": "Quest created", "id": 123}
    create_quest.assert_awaited_once()


def test_legacy_quest_create_route_is_not_registered(client, sample_problem):
    with authenticated(client) as authed_client:
        response = authed_client.post(
            "/api/quests",
            json={"problem_id": sample_problem.id, "data": {}},
        )
    assert response.status_code in {404, 405}


def test_submissions_contract_is_wrapped(client, db_session, sample_problem):
    submission = Submission(
        user_id=AUTHENTICATED_USER_ID,
        problem_id=sample_problem.id,
        code="def solution():\n    return 42",
        passed=True,
        error=None,
        execution_time=0.12,
    )
    db_session.add(submission)
    db_session.commit()
    db_session.refresh(submission)
    with authenticated(client) as authed_client:
        response = authed_client.get(
            f"/api/submissions/{sample_problem.id}",
        )
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"submissions"}
    assert data["submissions"] == [
        {
            "id": submission.id,
            "code": submission.code,
            "passed": True,
            "error": None,
            "execution_time": 0.12,
            "created_at": submission.created_at.isoformat(),
        }
    ]


def test_problem_detail_omits_example_when_missing(client, sample_problem):
    with authenticated(client) as authed_client:
        response = authed_client.get(f"/api/problems/{sample_problem.id}")
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {
        "id",
        "title",
        "category",
        "difficulty",
        "description",
        "starter_code",
        "test_cases",
        "learn",
    }
    assert "example" not in data
    assert "video" not in data
    assert "pytorch_test_cases" not in data
    assert "tinygrad_test_cases" not in data
    assert "cuda_test_cases" not in data
    assert data["description"] == "A test problem description"
    assert data["learn"] == "Learn about testing"
    assert data["test_cases"] == [{"test": "solution()", "expected_output": "42"}]


def test_problem_detail_parses_framework_and_video_json(client, db_session):
    problem = Problem(
        id=1,
        title="Framework Problem",
        category="Linear Algebra",
        difficulty="medium",
        description="Rich problem detail description",
        starter_code="def solution():\n    pass",
        test_cases=json.dumps([{"test": "solution()", "expected_output": "1"}]),
        example=json.dumps({"input": "a", "output": "b", "reasoning": "c"}),
        video=json.dumps({"url": "https://youtu.be/abc123", "title": "Intro"}),
        pytorch_starter_code="import torch",
        pytorch_test_cases=json.dumps([{"test": "torch_solution()", "expected_output": "t1"}]),
        tinygrad_starter_code="from tinygrad import Tensor",
        tinygrad_test_cases=json.dumps([{"test": "tg_solution()", "expected_output": "t2"}]),
        cuda_starter_code="__global__ void k(){}",
        cuda_test_cases=json.dumps([{"test": "cuda_solution()", "expected_output": "t3"}]),
    )
    db_session.add(problem)
    db_session.commit()
    db_session.refresh(problem)
    with authenticated(client) as authed_client:
        response = authed_client.get(f"/api/problems/{problem.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["example"] == {"input": "a", "output": "b", "reasoning": "c"}
    assert data["video"] == {"url": "https://youtu.be/abc123", "title": "Intro"}
    assert data["pytorch_test_cases"] == [{"test": "torch_solution()", "expected_output": "t1"}]
    assert data["tinygrad_test_cases"] == [{"test": "tg_solution()", "expected_output": "t2"}]
    assert data["cuda_test_cases"] == [{"test": "cuda_solution()", "expected_output": "t3"}]


def test_problem_detail_video_falls_back_to_string(client, db_session):
    problem = Problem(
        id=1,
        title="Video String Problem",
        category="Linear Algebra",
        difficulty="easy",
        description="Video string fallback case",
        starter_code="def solution():\n    pass",
        test_cases=json.dumps([{"test": "solution()", "expected_output": "1"}]),
        video="https://youtu.be/plainstring",
    )
    db_session.add(problem)
    db_session.commit()
    db_session.refresh(problem)
    with authenticated(client) as authed_client:
        response = authed_client.get(f"/api/problems/{problem.id}")
    assert response.status_code == 200
    assert response.json()["video"] == "https://youtu.be/plainstring"


def test_problem_solution_returns_cached_contract(client, db_session, sample_problem):
    solution_code = "def solution():\n    return 42"
    solution = ProblemSolution(problem_id=sample_problem.id, solution=solution_code)
    db_session.add(solution)
    db_session.commit()
    db_session.refresh(solution)
    with authenticated(client) as authed_client:
        response = authed_client.get(f"/api/problems/{sample_problem.id}/solution")
    assert response.status_code == 200
    assert response.json() == {"solution": solution_code, "cached": True}


def test_export_markdown_returns_cached_contract(client, db_session, sample_problem):
    markdown = "# Reasoning\n\nCached markdown body."
    export = ReasoningExport(
        problem_id=sample_problem.id,
        export_type="markdown",
        content=markdown,
        ai_model="pplx_alpha",
        created_by=AUTHENTICATED_USER_ID,
    )
    db_session.add(export)
    db_session.commit()
    db_session.refresh(export)
    with authenticated(client) as authed_client:
        response = authed_client.post(
            f"/api/quest/export-markdown/{sample_problem.id}",
            params={"use_ai": "true"},
        )
    assert response.status_code == 200
    assert response.json() == {"markdown": markdown, "enhanced": True, "cached": True}


def test_export_latex_returns_cached_contract(client, db_session, sample_problem):
    latex = "\\documentclass{article}\\begin{document}Cached\\end{document}"
    export = ReasoningExport(
        problem_id=sample_problem.id,
        export_type="latex",
        content=latex,
        ai_model="pplx_alpha",
        created_by=AUTHENTICATED_USER_ID,
    )
    db_session.add(export)
    db_session.commit()
    db_session.refresh(export)
    with authenticated(client) as authed_client:
        response = authed_client.post(f"/api/quest/export-latex/{sample_problem.id}")
    assert response.status_code == 200
    assert response.json() == {
        "latex": latex,
        "ai_generated": True,
        "model": "pplx_alpha",
        "cached": True,
    }


def test_user_profile_envelope_contract(client, db_session):
    user = User(
        id=AUTHENTICATED_USER_ID,
        username="profileuser",
        email="profile@example.com",
        password_hash="hashed",
        display_name="Ada",
        bio="builder",
        avatar_url="https://img/avatar.png",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    with authenticated(client) as authed_client:
        response = authed_client.get("/api/user/profile")
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {
        "user",
        "stats",
        "difficulty_breakdown",
        "recent_activity",
        "calendar_data",
        "category_progress",
        "achievements",
    }
    assert set(data["user"].keys()) == {
        "id",
        "username",
        "email",
        "created_at",
        "display_name",
        "bio",
        "avatar_url",
    }
    assert data["user"]["id"] == AUTHENTICATED_USER_ID
    assert data["user"]["display_name"] == "Ada"
    assert set(data["stats"].keys()) == {
        "problems_solved",
        "total_submissions",
        "success_rate",
        "streak",
        "paths_completed",
        "rank",
    }
    assert data["difficulty_breakdown"] == {"easy": 0, "medium": 0, "hard": 0}
    assert data["recent_activity"] == []


def test_user_profile_update_accepts_supported_fields_only(client, db_session):
    user = User(
        id=AUTHENTICATED_USER_ID,
        username="profileuser",
        email="profile@example.com",
        password_hash="hashed",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    with authenticated(client) as authed_client:
        response = authed_client.put(
            "/api/user/profile",
            json={
                "display_name": "Grace",
                "bio": "compiler pioneer",
                "avatar_url": "https://img/grace.png",
                "username": "hacked",
                "email": "hacked@example.com",
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {
        "user",
        "stats",
        "difficulty_breakdown",
        "recent_activity",
        "calendar_data",
        "category_progress",
        "achievements",
    }
    assert data["user"]["display_name"] == "Grace"
    assert data["user"]["bio"] == "compiler pioneer"
    assert data["user"]["avatar_url"] == "https://img/grace.png"
    assert data["user"]["username"] == "profileuser"
    assert data["user"]["email"] == "profile@example.com"
