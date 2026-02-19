"""
Tests for QuestController: quest retrieval and progress management.
"""

import pytest
import asyncio
from fastapi import HTTPException

from app.controllers.quest_controller import QuestController


def test_get_quest_not_found(db_session):
    """get_quest raises 404 when quest doesn't exist."""
    controller = QuestController(db_session)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.get_event_loop().run_until_complete(controller.get_quest(999))
    assert exc_info.value.status_code == 404


def test_save_progress(db_session, test_user):
    """save_progress creates new progress record."""
    controller = QuestController(db_session)
    result = asyncio.get_event_loop().run_until_complete(
        controller.save_progress(test_user.id, 1, 1, "def solution(): pass")
    )
    assert result["message"] == "Progress saved"
    assert result["step"] == 1


def test_get_progress_empty(db_session, test_user):
    """get_progress returns empty list when no progress exists."""
    controller = QuestController(db_session)
    result = controller.get_progress(test_user.id, 1)
    assert result["progress"] == []
