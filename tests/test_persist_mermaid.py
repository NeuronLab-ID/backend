"""
Tests for persist_mermaid_fix controller method and route.
Verifies that AI-fixed mermaid diagrams are correctly persisted to reasoning data.
"""

import json

from app.models.db import QuestReasoning


def test_persist_mermaid_fix_replaces_code(db_session, client, test_user, auth_headers, sample_problem):
    """Happy path: reasoning exists, mermaid code is found and replaced."""
    # Setup: Create a QuestReasoning with mermaid code in step reasoning
    reasoning_data = json.dumps(
        {
            "steps": [
                {
                    "step": 1,
                    "title": "Step 1",
                    "reasoning": "Here is a diagram:\n```mermaid\ngraph TD\nA-->B\n```\nEnd of step.",
                }
            ],
            "summary": "A summary",
        }
    )
    reasoning = QuestReasoning(problem_id=sample_problem.id, reasoning_data=reasoning_data, created_by=test_user.id)
    db_session.add(reasoning)
    db_session.commit()

    # Action: POST to /api/persist-mermaid-fix
    response = client.post(
        "/api/persist-mermaid-fix",
        json={"problem_id": sample_problem.id, "original_code": "graph TD\nA-->B", "fixed_code": "graph TD;\nA-->B;"},
        headers=auth_headers,
    )

    # Assert: Response 200, success=True, updated=True
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["updated"] is True

    # Assert: Verify the JSON in DB has the fixed code
    updated_reasoning = db_session.query(QuestReasoning).filter_by(problem_id=sample_problem.id).first()
    assert updated_reasoning is not None
    updated_data = json.loads(updated_reasoning.reasoning_data)
    assert "graph TD;\nA-->B;" in updated_data["steps"][0]["reasoning"]
    assert "graph TD\nA-->B" not in updated_data["steps"][0]["reasoning"]


def test_persist_mermaid_fix_not_found(db_session, client, auth_headers):
    """Reasoning doesn't exist for given problem_id → returns 404."""
    # Setup: No QuestReasoning in DB for problem_id=999
    # Action: POST to /api/persist-mermaid-fix
    response = client.post(
        "/api/persist-mermaid-fix",
        json={"problem_id": 999, "original_code": "graph TD\nA-->B", "fixed_code": "graph TD;\nA-->B;"},
        headers=auth_headers,
    )

    # Assert: Response 404
    assert response.status_code == 404


def test_persist_mermaid_fix_code_not_in_reasoning(db_session, client, test_user, auth_headers, sample_problem):
    """Reasoning exists but original_code not found → returns success=True, updated=False."""
    # Setup: Create a QuestReasoning that does NOT contain the original_code
    reasoning_data = json.dumps(
        {
            "steps": [
                {
                    "step": 1,
                    "title": "Step 1",
                    "reasoning": "Here is a diagram:\n```mermaid\ngraph TD\nA-->B\n```\nEnd of step.",
                }
            ],
            "summary": "A summary",
        }
    )
    reasoning = QuestReasoning(problem_id=sample_problem.id, reasoning_data=reasoning_data, created_by=test_user.id)
    db_session.add(reasoning)
    db_session.commit()

    # Action: POST with original_code that doesn't exist in reasoning
    response = client.post(
        "/api/persist-mermaid-fix",
        json={"problem_id": sample_problem.id, "original_code": "nonexistent code", "fixed_code": "anything"},
        headers=auth_headers,
    )

    # Assert: Response 200, success=True, updated=False
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["updated"] is False


def test_persist_mermaid_fix_in_summary(db_session, client, test_user, auth_headers, sample_problem):
    """Mermaid code in summary field is also replaced."""
    # Setup: Create a QuestReasoning with mermaid code in summary
    reasoning_data = json.dumps(
        {
            "steps": [{"step": 1, "title": "Step 1", "reasoning": "Some reasoning"}],
            "summary": "Summary with diagram:\n```mermaid\ngraph LR\nX-->Y\n```\nEnd.",
        }
    )
    reasoning = QuestReasoning(problem_id=sample_problem.id, reasoning_data=reasoning_data, created_by=test_user.id)
    db_session.add(reasoning)
    db_session.commit()

    # Action: POST to /api/persist-mermaid-fix
    response = client.post(
        "/api/persist-mermaid-fix",
        json={"problem_id": sample_problem.id, "original_code": "graph LR\nX-->Y", "fixed_code": "graph LR;\nX-->Y;"},
        headers=auth_headers,
    )

    # Assert: Response 200, success=True, updated=True
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["updated"] is True

    # Assert: Verify the JSON in DB has the fixed code in summary
    updated_reasoning = db_session.query(QuestReasoning).filter_by(problem_id=sample_problem.id).first()
    updated_data = json.loads(updated_reasoning.reasoning_data)
    assert "graph LR;\nX-->Y;" in updated_data["summary"]
    assert "graph LR\nX-->Y" not in updated_data["summary"]


def test_persist_mermaid_fix_in_web_references(db_session, client, test_user, auth_headers, sample_problem):
    """Mermaid code in web_references field is also replaced."""
    # Setup: Create a QuestReasoning with mermaid code in web_references
    reasoning_data = json.dumps(
        {
            "steps": [{"step": 1, "title": "Step 1", "reasoning": "Some reasoning"}],
            "summary": "A summary",
            "web_references": "Reference with diagram:\n```mermaid\nsequenceDiagram\nA->>B: msg\n```\nEnd.",
        }
    )
    reasoning = QuestReasoning(problem_id=sample_problem.id, reasoning_data=reasoning_data, created_by=test_user.id)
    db_session.add(reasoning)
    db_session.commit()

    # Action: POST to /api/persist-mermaid-fix
    response = client.post(
        "/api/persist-mermaid-fix",
        json={
            "problem_id": sample_problem.id,
            "original_code": "sequenceDiagram\nA->>B: msg",
            "fixed_code": "sequenceDiagram\nA->>B: message",
        },
        headers=auth_headers,
    )

    # Assert: Response 200, success=True, updated=True
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["updated"] is True

    # Assert: Verify the JSON in DB has the fixed code in web_references
    updated_reasoning = db_session.query(QuestReasoning).filter_by(problem_id=sample_problem.id).first()
    updated_data = json.loads(updated_reasoning.reasoning_data)
    assert "sequenceDiagram\nA->>B: message" in updated_data["web_references"]
    assert "sequenceDiagram\nA->>B: msg" not in updated_data["web_references"]


def test_persist_mermaid_fix_multiple_steps(db_session, client, test_user, auth_headers, sample_problem):
    """Mermaid code in multiple steps is replaced in all occurrences."""
    # Setup: Create a QuestReasoning with mermaid code in multiple steps
    reasoning_data = json.dumps(
        {
            "steps": [
                {"step": 1, "title": "Step 1", "reasoning": "Diagram 1:\n```mermaid\ngraph TD\nA-->B\n```"},
                {"step": 2, "title": "Step 2", "reasoning": "Diagram 2:\n```mermaid\ngraph TD\nA-->B\n```"},
            ],
            "summary": "A summary",
        }
    )
    reasoning = QuestReasoning(problem_id=sample_problem.id, reasoning_data=reasoning_data, created_by=test_user.id)
    db_session.add(reasoning)
    db_session.commit()

    # Action: POST to /api/persist-mermaid-fix
    response = client.post(
        "/api/persist-mermaid-fix",
        json={"problem_id": sample_problem.id, "original_code": "graph TD\nA-->B", "fixed_code": "graph TD;\nA-->B;"},
        headers=auth_headers,
    )

    # Assert: Response 200, success=True, updated=True
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["updated"] is True

    # Assert: Verify both steps have the fixed code
    updated_reasoning = db_session.query(QuestReasoning).filter_by(problem_id=sample_problem.id).first()
    updated_data = json.loads(updated_reasoning.reasoning_data)
    for step in updated_data["steps"]:
        assert "graph TD;\nA-->B;" in step["reasoning"]
        assert "graph TD\nA-->B" not in step["reasoning"]


def test_persist_mermaid_fix_requires_auth(db_session, client, sample_problem):
    """Endpoint requires authentication."""
    # Action: POST without auth headers
    response = client.post(
        "/api/persist-mermaid-fix",
        json={"problem_id": sample_problem.id, "original_code": "graph TD\nA-->B", "fixed_code": "graph TD;\nA-->B;"},
    )

    # Assert: Response 401 (Unauthorized - no auth header provided)
    assert response.status_code == 401
