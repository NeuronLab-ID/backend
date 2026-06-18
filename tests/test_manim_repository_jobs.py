# pyright: reportGeneralTypeIssues=false, reportArgumentType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false
from datetime import datetime, timedelta, timezone

from app.models.db import ManimAnimation, ManimRenderJob
from app.repositories.manim_repository import ManimRepository


def test_create_job_persists_separate_lifecycle(db_session):
    repo = ManimRepository(db_session)

    job = repo.create_job(
        user_id=7,
        problem_id=1,
        step_number=2,
        video_type="visualization",
        requested_backend="cpu",
    )

    assert job.job_id
    assert job.status == "queued"
    assert job.provider == "9router"
    assert job.model == "cx/gpt-5.5-xhigh"
    assert job.requested_backend == "cpu"
    assert job.animation_id is None
    assert db_session.query(ManimRenderJob).filter_by(job_id=job.job_id).one()


def test_claim_update_cancel_and_retry_job(db_session):
    repo = ManimRepository(db_session)
    job = repo.create_job(user_id=1, problem_id=2, step_number=1, video_type="calculation", requested_backend="cpu")

    claimed = repo.claim_next_job()
    assert claimed.job_id == job.job_id
    assert claimed.status == "generating_code"
    assert claimed.started_at is not None

    updated = repo.update_job(job.job_id, status="rendering", progress=55, resolved_backend="cpu")
    assert updated.status == "rendering"
    assert updated.progress == 55
    assert updated.resolved_backend == "cpu"

    cancelling = repo.request_cancel_job(job.job_id, user_id=1)
    assert cancelling.status == "cancelling"
    assert cancelling.cancel_requested_at is not None

    repo.update_job(job.job_id, status="cancelled", progress=100, finished=True)
    retry = repo.retry_job(job.job_id, user_id=1)
    assert retry is not None
    assert retry.job_id != job.job_id
    assert retry.status == "queued"
    assert retry.attempt == 2


def test_idempotency_returns_existing_active_job(db_session):
    repo = ManimRepository(db_session)

    first = repo.create_job(
        user_id=1,
        problem_id=3,
        step_number=None,
        video_type=None,
        requested_backend="cpu",
        idempotency_key="same-request",
    )
    second = repo.create_job(
        user_id=1,
        problem_id=3,
        step_number=None,
        video_type=None,
        requested_backend="cpu",
        idempotency_key="same-request",
    )

    assert second.job_id == first.job_id


def test_mark_stale_jobs_orphaned(db_session):
    repo = ManimRepository(db_session)
    job = repo.create_job(user_id=1, problem_id=4, step_number=1, video_type=None, requested_backend="cpu")
    repo.claim_next_job()
    persisted = repo.get_job(job.job_id)
    persisted.updated_at = datetime.now(timezone.utc) - timedelta(hours=2)
    db_session.commit()

    count = repo.mark_stale_jobs_orphaned(datetime.now(timezone.utc) - timedelta(hours=1))

    assert count == 1
    assert repo.get_job(job.job_id).status == "orphaned"


def test_create_reuses_existing_animation_row_on_rerender(db_session):
    repo = ManimRepository(db_session)

    first = repo.create(problem_id=10, step_number=2, manim_code="code_v1", video_type="calculation")
    repo.update_status(
        first.id,
        "completed",
        video_path="/videos/old.mp4",
        error_message="prior error",
        render_time_ms=1234,
    )

    second = repo.create(problem_id=10, step_number=2, manim_code="code_v2", video_type="calculation")

    assert second.id == first.id
    assert db_session.query(ManimAnimation).count() == 1

    assert second.manim_code == "code_v2"
    assert second.status == "pending"
    assert second.video_path is None
    assert second.error_message is None
    assert second.render_time_ms is None
    assert second.updated_at is not None


def test_create_distinct_video_types_are_separate_rows(db_session):
    repo = ManimRepository(db_session)

    calc = repo.create(problem_id=11, step_number=1, manim_code="calc", video_type="calculation")
    viz = repo.create(problem_id=11, step_number=1, manim_code="viz", video_type="visualization")

    assert calc.id != viz.id
    assert db_session.query(ManimAnimation).count() == 2
