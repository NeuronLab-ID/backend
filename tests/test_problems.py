"""
Tests for problem listing, detail, and solution routes.
"""

from unittest.mock import patch, AsyncMock


def test_list_problems(client, sample_problem):
    """GET /problems returns paginated list."""
    response = client.get("/api/problems")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["problems"]) >= 1
    assert data["problems"][0]["title"] == "Test Problem"


def test_get_problem(client, auth_headers, sample_problem):
    """GET /problems/{id} returns problem details."""
    response = client.get("/api/problems/1", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Problem"
    assert data["category"] == "Linear Algebra"
    assert data["difficulty"] == "easy"
    assert "description" in data
    assert "starter_code" in data


def test_get_problem_not_found(client, auth_headers):
    """GET /problems/999 returns 404."""
    response = client.get("/api/problems/999", headers=auth_headers)
    assert response.status_code == 404


def test_get_solution_mocked(client, auth_headers, sample_problem):
    """GET /problems/{id}/solution with mocked AI returns solution."""
    with (
        patch(
            "app.routes.problems.generate_solution",
            new_callable=AsyncMock,
            return_value="def solution(): return 42",
        ),
        patch(
            "app.repositories.problem_repository.ProblemRepository.get_solution_by_problem_id",
            return_value=None,
        ),
        patch(
            "app.repositories.problem_repository.ProblemRepository.save_solution",
        ),
    ):
        response = client.get("/api/problems/1/solution", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "solution" in data
        assert "def solution" in data["solution"]
