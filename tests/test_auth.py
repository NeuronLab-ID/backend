"""
Tests for authentication routes: register, login, /me.
"""

from unittest.mock import patch, MagicMock
from datetime import datetime


def test_register_success(client, test_user):
    """Register new user returns 200 with user data."""
    # Mock repo.create to avoid commit+refresh issue with in-memory SQLite threading
    mock_user = MagicMock()
    mock_user.id = 99
    mock_user.username = "newuser"
    mock_user.email = "new@example.com"
    mock_user.created_at = datetime.utcnow()

    with patch(
        "app.repositories.auth_repository.AuthRepository.create",
        return_value=mock_user,
    ):
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "pass123",
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "new@example.com"
    assert "id" in data
    assert "created_at" in data


def test_register_duplicate_email(client, test_user):
    """Register with existing email returns 400."""
    response = client.post(
        "/api/auth/register",
        json={
            "username": "other",
            "email": "test@example.com",
            "password": "pass123",
        },
    )
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


def test_login_success(client, test_user):
    """Login with valid credentials returns token."""
    response = client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpass123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_password(client, test_user):
    """Login with wrong password returns 401."""
    response = client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "wrongpass"},
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_get_me(client, auth_headers):
    """GET /auth/me with valid token returns user info."""
    response = client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
