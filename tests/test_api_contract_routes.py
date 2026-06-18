"""Route-level API contract tests.

These tests pin the current HTTP response shapes for the problem, quest, and
submission routes so the frontend and backend contracts stay aligned. They are
intentionally route-level: external work (AI, Docker, filesystem) is patched so
only the wiring and response envelopes are asserted.
"""

import json
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

from app.models.db import Quest, Submission
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
