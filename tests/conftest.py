"""
Test configuration and fixtures.
Provides in-memory SQLite database, FastAPI TestClient, mock AI providers, and test user.
"""

import asyncio
from collections.abc import Callable, Iterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.models.db import Problem, User
from app.services.auth_service import create_access_token, hash_password

# In-memory SQLite for tests
TEST_DATABASE_URL = "sqlite://"
test_engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def pytest_asyncio_loop_factories() -> dict[str, Callable[[], asyncio.AbstractEventLoop]]:
    return {"default": asyncio.new_event_loop}


LEGACY_SYNC_EVENT_LOOP_MODULES = {
    Path("tests/test_manim_service.py"),
    Path("tests/test_quest_controller.py"),
    Path("tests/test_reasoning.py"),
    Path("tests/test_services.py"),
}


@pytest.fixture(autouse=True)
def legacy_sync_event_loop(request: pytest.FixtureRequest) -> Iterator[None]:
    if Path(str(request.node.path)).relative_to(Path.cwd()) not in LEGACY_SYNC_EVENT_LOOP_MODULES:
        yield
        return

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield
    finally:
        asyncio.set_event_loop(None)
        loop.close()


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with test database."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    # Import app here to avoid circular imports
    from main import app

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """Create a test user and return user object."""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=hash_password("testpass123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user):
    """Create a JWT token for the test user."""
    return create_access_token(test_user.id)


@pytest.fixture
def auth_headers(auth_token):
    """Authorization headers with Bearer token."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def sample_problem(db_session):
    """Create a sample problem in the database."""
    import json

    problem = Problem(
        id=1,
        title="Test Problem",
        category="Linear Algebra",
        difficulty="easy",
        description="A test problem description",
        starter_code="def solution():\n    pass",
        test_cases=json.dumps([{"test": "solution()", "expected_output": "42"}]),
        learn_section="Learn about testing",
    )
    db_session.add(problem)
    db_session.commit()
    db_session.refresh(problem)
    return problem


@pytest.fixture
def mock_ai_provider():
    """Mock AI provider that returns canned responses."""
    provider = MagicMock()
    provider.name = "mock"
    provider.is_configured.return_value = True
    provider.generate_hint = AsyncMock(return_value="Try checking your variable types.")
    provider.generate_reasoning = AsyncMock(return_value="Step 1: Analyze the input...")
    return provider
