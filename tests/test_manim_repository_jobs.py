# pyright: reportGeneralTypeIssues=false, reportArgumentType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false
import importlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

import sqlalchemy as sa
from alembic.config import Config
from sqlalchemy.orm import sessionmaker

import app.config as app_config
import app.repositories.manim_repository as manim_repository_module
from alembic import command
from app.models.db import ManimAnimation, ManimRenderJob
from app.repositories.manim_repository import ManimRepository


class MonkeyPatchFixture(Protocol):
    def delenv(self, name: str, raising: bool = True) -> None: ...

    def setenv(self, name: str, value: str, prepend: str | None = None) -> None: ...


def _clear_manim_metadata_env(monkeypatch: MonkeyPatchFixture) -> None:
    for name in ("MANIM_CODE_PROVIDER", "MANIM_OPENAI_COMPATIBLE_MODEL", "MANIM_9ROUTER_MODEL"):
        monkeypatch.delenv(name, raising=False)


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
    assert job.provider == "openai-compatible"
    assert job.model == "cx/gpt-5.5-xhigh"
    assert job.requested_backend == "cpu"
    assert job.animation_id is None
    assert db_session.query(ManimRenderJob).filter_by(job_id=job.job_id).one()


def test_create_job_uses_default_openai_compatible_provider(db_session, monkeypatch):
    _clear_manim_metadata_env(monkeypatch)
    repo = ManimRepository(db_session)

    job = repo.create_job(
        user_id=7,
        problem_id=11,
        step_number=3,
        video_type="calculation",
        requested_backend="cpu",
    )

    assert job.provider == "openai-compatible"
    assert job.model == "cx/gpt-5.5-xhigh"


def test_create_job_uses_canonical_openai_compatible_model_override(db_session, monkeypatch):
    _clear_manim_metadata_env(monkeypatch)
    monkeypatch.setenv("MANIM_OPENAI_COMPATIBLE_MODEL", "canonical-model")
    monkeypatch.setenv("MANIM_9ROUTER_MODEL", "legacy-model")
    _ = importlib.reload(app_config)
    reloaded_repository_module = importlib.reload(manim_repository_module)
    try:
        repo = reloaded_repository_module.ManimRepository(db_session)

        job = repo.create_job(
            user_id=7,
            problem_id=12,
            step_number=3,
            video_type="calculation",
            requested_backend="cpu",
        )

        assert job.provider == "openai-compatible"
        assert job.model == "canonical-model"
    finally:
        _ = importlib.reload(app_config)
        _ = importlib.reload(manim_repository_module)


def test_create_job_uses_legacy_provider_env_override(db_session, monkeypatch):
    _clear_manim_metadata_env(monkeypatch)
    monkeypatch.setenv("MANIM_CODE_PROVIDER", "9router")
    monkeypatch.setenv("MANIM_9ROUTER_MODEL", "legacy-model")
    repo = ManimRepository(db_session)

    job = repo.create_job(
        user_id=7,
        problem_id=13,
        step_number=3,
        video_type="calculation",
        requested_backend="cpu",
    )

    assert job.provider == "9router"
    assert job.model == "legacy-model"


def test_manim_render_jobs_migration_creates_columns_and_indexes(tmp_path):
    db_path = tmp_path / "migration.sqlite"
    alembic_cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

    command.stamp(alembic_cfg, "98bff2535119")
    command.upgrade(alembic_cfg, "head")

    engine = sa.create_engine(f"sqlite:///{db_path}")
    inspector = sa.inspect(engine)
    try:
        assert "manim_render_jobs" in inspector.get_table_names()
        column_names = {column["name"] for column in inspector.get_columns("manim_render_jobs")}
        assert {
            "id",
            "job_id",
            "user_id",
            "problem_id",
            "step_number",
            "video_type",
            "requested_backend",
            "resolved_backend",
            "status",
            "progress",
            "attempt",
            "max_attempts",
            "provider",
            "model",
            "container_id",
            "animation_id",
            "request_hash",
            "idempotency_key",
            "error_code",
            "error_message",
            "logs_tail",
            "created_at",
            "queued_at",
            "started_at",
            "finished_at",
            "cancel_requested_at",
            "updated_at",
        } <= column_names
        indexes = {index["name"]: index for index in inspector.get_indexes("manim_render_jobs")}
        assert set(indexes) >= {
            "ix_manim_render_jobs_id",
            "ix_manim_render_jobs_job_id",
            "ix_manim_render_jobs_user_id",
            "ix_manim_render_jobs_problem_id",
            "ix_manim_render_jobs_status",
            "ix_manim_render_jobs_request_hash",
            "ix_manim_render_jobs_idempotency_key",
            "ix_manim_render_jobs_status_created",
        }
        assert bool(indexes["ix_manim_render_jobs_job_id"]["unique"]) is True
        assert indexes["ix_manim_render_jobs_status_created"]["column_names"] == ["status", "created_at"]
    finally:
        engine.dispose()

    command.downgrade(alembic_cfg, "98bff2535119")
    engine = sa.create_engine(f"sqlite:///{db_path}")
    try:
        assert "manim_render_jobs" not in sa.inspect(engine).get_table_names()
    finally:
        engine.dispose()


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


def test_retry_job_returns_none_at_max_attempts(db_session):
    repo = ManimRepository(db_session)
    job = repo.create_job(
        user_id=1,
        problem_id=20,
        step_number=1,
        video_type="calculation",
        requested_backend="cpu",
        max_attempts=2,
    )
    repo.update_job(job.job_id, status="failed_retryable", progress=100, finished=True)
    persisted = repo.get_job(job.job_id)
    persisted.attempt = 2
    db_session.commit()

    retry = repo.retry_job(job.job_id, user_id=1)

    assert retry is None
    assert db_session.query(ManimRenderJob).count() == 1


def test_retry_job_creates_attempt_two_when_bounded(db_session):
    repo = ManimRepository(db_session)
    job = repo.create_job(
        user_id=1,
        problem_id=21,
        step_number=1,
        video_type="visualization",
        requested_backend="cpu",
        max_attempts=2,
    )
    repo.update_job(job.job_id, status="failed_retryable", progress=100, finished=True)

    retry = repo.retry_job(job.job_id, user_id=1)

    assert retry is not None
    assert retry.job_id != job.job_id
    assert retry.status == "queued"
    assert retry.attempt == 2
    assert retry.max_attempts == 2
    assert retry.provider == job.provider
    assert retry.model == job.model
    assert retry.request_hash == job.request_hash


def test_retry_job_reuses_existing_next_attempt_for_same_source(db_session):
    repo = ManimRepository(db_session)
    job = repo.create_job(
        user_id=1,
        problem_id=25,
        step_number=1,
        video_type="visualization",
        requested_backend="cpu",
        max_attempts=3,
    )
    repo.update_job(job.job_id, status="failed_retryable", progress=100, finished=True)

    first_retry = repo.retry_job(job.job_id, user_id=1)
    second_retry = repo.retry_job(job.job_id, user_id=1)

    assert first_retry is not None
    assert second_retry is not None
    assert second_retry.job_id == first_retry.job_id
    assert db_session.query(ManimRenderJob).count() == 2


def test_queued_cancel_becomes_terminal_and_is_not_claimed(db_session):
    repo = ManimRepository(db_session)
    job = repo.create_job(user_id=1, problem_id=22, step_number=1, video_type="calculation", requested_backend="cpu")

    cancelled = repo.request_cancel_job(job.job_id, user_id=1)
    claimed = repo.claim_next_job()

    assert cancelled.status == "cancelled"
    assert cancelled.progress == 100
    assert cancelled.cancel_requested_at is not None
    assert cancelled.finished_at is not None
    assert claimed is None


def test_running_cancel_remains_cancelling(db_session):
    repo = ManimRepository(db_session)
    job = repo.create_job(user_id=1, problem_id=23, step_number=1, video_type="calculation", requested_backend="cpu")
    repo.claim_next_job()

    cancelling = repo.request_cancel_job(job.job_id, user_id=1)

    assert cancelling.status == "cancelling"
    assert cancelling.finished_at is None


def test_should_cancel_sees_cross_session_cancel_without_worker_commit(db_session):
    worker_repo = ManimRepository(db_session)
    job = worker_repo.create_job(
        user_id=1,
        problem_id=24,
        step_number=1,
        video_type="calculation",
        requested_backend="cpu",
    )
    job_id = job.job_id
    worker_repo.claim_next_job()
    worker_repo.update_job(job_id, status="rendering", progress=50)

    assert worker_repo.should_cancel(job_id) is False

    request_session_factory = sessionmaker(bind=db_session.get_bind(), autocommit=False, autoflush=False)
    request_session = request_session_factory()
    try:
        request_repo = ManimRepository(request_session)
        request_repo.request_cancel_job(job_id, user_id=1)
    finally:
        request_session.close()

    assert worker_repo.should_cancel(job_id) is True


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
