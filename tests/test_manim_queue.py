import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.models.db import QuestReasoning
from app.repositories.manim_repository import ManimRepository
from app.services.manim_queue import ManimQueueService, ManimWorker


def test_queue_retry_missing_job_returns_404(db_session):
    service = ManimQueueService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        service.retry_job("missing", user_id=1)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Manim job not found"


def test_queue_retry_exhausted_job_returns_400(db_session):
    repo = ManimRepository(db_session)
    job = repo.create_job(
        user_id=1,
        problem_id=30,
        step_number=1,
        video_type="calculation",
        requested_backend="cpu",
        max_attempts=1,
    )
    job_id = getattr(job, "job_id")
    repo.update_job(job_id, status="failed_retryable", progress=100, finished=True)
    service = ManimQueueService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        service.retry_job(job_id, user_id=1)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Manim job is not retryable"


@pytest.mark.asyncio
async def test_worker_exception_path_with_cancelling_job_marks_cancelled(db_session):
    repo = ManimRepository(db_session)
    job = repo.create_job(user_id=1, problem_id=31, step_number=1, video_type="calculation", requested_backend="cpu")
    job_id = getattr(job, "job_id")
    repo.claim_next_job()
    db_session.add(
        QuestReasoning(
            problem_id=31,
            reasoning_data=json.dumps(
                {
                    "problem_title": "Sample",
                    "problem_description": "Desc",
                    "steps": [{"title": "Step A", "reasoning": "A"}],
                }
            ),
        )
    )
    db_session.commit()

    async def fail_generation(*args, **kwargs):
        repo.request_cancel_job(job_id, user_id=1)
        raise RuntimeError("boom")

    worker = ManimWorker()
    with (
        patch("app.services.manim_queue.SessionLocal", return_value=db_session),
        patch("app.services.manim_queue.get_manim_backend_policy", return_value=SimpleNamespace(name="cpu")),
        patch.object(worker, "_run_generation", AsyncMock(side_effect=fail_generation)),
    ):
        await worker._process_job(job_id)

    persisted = repo.get_job(job_id)
    assert persisted is not None
    assert getattr(persisted, "status") == "cancelled"
