# pyright: reportAttributeAccessIssue=false, reportGeneralTypeIssues=false, reportReturnType=false
# Manim Animation Repository
# Handles database operations for ManimAnimation artifacts and ManimRenderJob lifecycle.

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import get_manim_code_provider_metadata
from app.models.db import ManimAnimation, ManimRenderJob

ACTIVE_JOB_STATUSES = {"queued", "generating_code", "rendering", "cancelling"}
RETRYABLE_JOB_STATUSES = {"failed_retryable", "failed_terminal", "cancelled", "orphaned"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def build_manim_request_hash(problem_id: int, step_number: int | None, video_type: str | None, backend: str) -> str:
    raw = f"{problem_id}:{step_number or ''}:{video_type or ''}:{backend}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ManimRepository:
    """Repository for manim animation and render job database operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_problem_id(self, problem_id: int) -> list[ManimAnimation]:
        """Get all animations for a problem."""
        return self.db.query(ManimAnimation).filter(ManimAnimation.problem_id == problem_id).all()

    def get_by_problem_and_step(
        self, problem_id: int, step_number: int, video_type: str | None = None
    ) -> ManimAnimation | None:
        """Get animation by problem ID and step number. Optionally filter by video_type."""
        query = self.db.query(ManimAnimation).filter(
            ManimAnimation.problem_id == problem_id, ManimAnimation.step_number == step_number
        )
        if video_type is not None:
            query = query.filter(ManimAnimation.video_type == video_type)
        return query.first()

    def get_by_problem_step_and_type(self, problem_id: int, step_number: int, video_type: str) -> ManimAnimation | None:
        """Get animation by problem ID, step number, and video type."""
        return (
            self.db.query(ManimAnimation)
            .filter(
                ManimAnimation.problem_id == problem_id,
                ManimAnimation.step_number == step_number,
                ManimAnimation.video_type == video_type,
            )
            .first()
        )

    def create(
        self, problem_id: int, step_number: int, manim_code: str, video_type: str = "calculation"
    ) -> ManimAnimation:
        """Create or reset a manim animation with status='pending'.

        The (problem_id, step_number, video_type) tuple is unique. To keep
        re-renders and retries safe, an existing row is reset to a fresh
        pending state instead of inserting a duplicate that would violate
        uq_manim_problem_step_type.
        """
        existing = self.get_by_problem_step_and_type(problem_id, step_number, video_type)
        if existing is not None:
            existing.manim_code = manim_code
            existing.status = "pending"
            existing.video_path = None
            existing.error_message = None
            existing.render_time_ms = None
            existing.updated_at = _now()
            self.db.commit()
            self.db.refresh(existing)
            return existing

        animation = ManimAnimation(
            problem_id=problem_id,
            step_number=step_number,
            manim_code=manim_code,
            status="pending",
            video_type=video_type,
        )
        self.db.add(animation)
        self.db.commit()
        self.db.refresh(animation)
        return animation

    def update_status(
        self,
        animation_id: int,
        status: str,
        video_path: str | None = None,
        error_message: str | None = None,
        render_time_ms: int | None = None,
    ) -> ManimAnimation:
        """Update animation status and optional fields."""
        animation = self.db.query(ManimAnimation).filter(ManimAnimation.id == animation_id).first()

        if animation:
            animation.status = status
            animation.updated_at = _now()
            if video_path is not None:
                animation.video_path = video_path
            if error_message is not None:
                animation.error_message = error_message
            if render_time_ms is not None:
                animation.render_time_ms = render_time_ms
            self.db.commit()
            self.db.refresh(animation)

        return animation

    def get_status_summary(self, problem_id: int, total_steps: int) -> dict[str, object]:
        """Get status summary for all animations of a problem."""
        animations = self.get_by_problem_id(problem_id)

        completed_count = sum(1 for a in animations if a.status == "completed")
        rendering_count = sum(1 for a in animations if a.status == "rendering")
        error_count = sum(1 for a in animations if a.status == "error")
        pending_count = sum(1 for a in animations if a.status == "pending")

        animations_sorted = sorted(animations, key=lambda a: (a.step_number, a.video_type))
        animations_list = [
            {
                "id": a.id,
                "problem_id": a.problem_id,
                "step_number": a.step_number,
                "status": a.status,
                "video_url": a.video_path,
                "error_message": a.error_message,
                "render_time_ms": a.render_time_ms,
                "video_type": a.video_type,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in animations_sorted
        ]

        return {
            "problem_id": problem_id,
            "total_steps": total_steps,
            "completed_count": completed_count,
            "rendering_count": rendering_count,
            "error_count": error_count,
            "pending_count": pending_count,
            "animations": animations_list,
        }

    def exists_for_step_and_type(self, problem_id: int, step_number: int, video_type: str) -> bool:
        """Check if animation exists for problem, step, and video type."""
        return (
            self.db.query(ManimAnimation)
            .filter(
                ManimAnimation.problem_id == problem_id,
                ManimAnimation.step_number == step_number,
                ManimAnimation.video_type == video_type,
            )
            .first()
            is not None
        )

    def create_job(
        self,
        *,
        user_id: int,
        problem_id: int,
        step_number: int | None,
        video_type: str | None,
        requested_backend: str,
        idempotency_key: str | None = None,
        max_attempts: int = 2,
    ) -> ManimRenderJob:
        request_hash = build_manim_request_hash(problem_id, step_number, video_type, requested_backend)
        if idempotency_key:
            existing = (
                self.db.query(ManimRenderJob)
                .filter(
                    ManimRenderJob.user_id == user_id,
                    ManimRenderJob.idempotency_key == idempotency_key,
                    ManimRenderJob.request_hash == request_hash,
                    ManimRenderJob.status.in_(tuple(ACTIVE_JOB_STATUSES | {"succeeded"})),
                )
                .order_by(ManimRenderJob.created_at.desc())
                .first()
            )
            if existing:
                return existing

        provider, model = get_manim_code_provider_metadata()
        job = ManimRenderJob(
            job_id=uuid.uuid4().hex,
            user_id=user_id,
            problem_id=problem_id,
            step_number=step_number,
            video_type=video_type,
            requested_backend=requested_backend,
            status="queued",
            progress=0,
            attempt=1,
            max_attempts=max_attempts,
            provider=provider,
            model=model,
            request_hash=request_hash,
            idempotency_key=idempotency_key,
            queued_at=_now(),
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_job(self, job_id: str, user_id: int | None = None) -> ManimRenderJob | None:
        query = self.db.query(ManimRenderJob).filter(ManimRenderJob.job_id == job_id)
        if user_id is not None:
            query = query.filter(ManimRenderJob.user_id == user_id)
        return query.first()

    def claim_next_job(self) -> ManimRenderJob | None:
        job = (
            self.db.query(ManimRenderJob)
            .filter(ManimRenderJob.status == "queued")
            .order_by(ManimRenderJob.queued_at.asc(), ManimRenderJob.created_at.asc())
            .first()
        )
        if not job:
            return None
        job.status = "generating_code"
        job.progress = 10
        job.started_at = _now()
        job.updated_at = job.started_at
        self.db.commit()
        self.db.refresh(job)
        return job

    def update_job(
        self,
        job_id: str,
        *,
        status: str | None = None,
        progress: int | None = None,
        resolved_backend: str | None = None,
        container_id: str | None = None,
        animation_id: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        logs_tail: str | None = None,
        finished: bool = False,
    ) -> ManimRenderJob | None:
        job = self.get_job(job_id)
        if not job:
            return None
        if status is not None:
            job.status = status
        if progress is not None:
            job.progress = max(0, min(100, progress))
        if resolved_backend is not None:
            job.resolved_backend = resolved_backend
        if container_id is not None:
            job.container_id = container_id
        if animation_id is not None:
            job.animation_id = animation_id
        if error_code is not None:
            job.error_code = error_code
        if error_message is not None:
            job.error_message = error_message[:2000]
        if logs_tail is not None:
            job.logs_tail = logs_tail[-4000:]
        if finished:
            job.finished_at = _now()
        job.updated_at = _now()
        self.db.commit()
        self.db.refresh(job)
        return job

    def request_cancel_job(self, job_id: str, user_id: int) -> ManimRenderJob | None:
        job = self.get_job(job_id, user_id=user_id)
        if not job:
            return None
        if job.status in {"succeeded", "failed_retryable", "failed_terminal", "cancelled", "orphaned"}:
            return job
        if job.status == "queued":
            now = _now()
            job.status = "cancelled"
            job.progress = 100
            job.cancel_requested_at = now
            job.finished_at = now
            job.updated_at = now
            self.db.commit()
            self.db.refresh(job)
            return job
        job.status = "cancelling"
        job.cancel_requested_at = _now()
        job.updated_at = job.cancel_requested_at
        self.db.commit()
        self.db.refresh(job)
        return job

    def retry_job(self, job_id: str, user_id: int) -> ManimRenderJob | None:
        original = self.get_job(job_id, user_id=user_id)
        if (
            not original
            or original.status not in RETRYABLE_JOB_STATUSES
            or original.attempt >= original.max_attempts
        ):
            return None
        job = ManimRenderJob(
            job_id=uuid.uuid4().hex,
            user_id=original.user_id,
            problem_id=original.problem_id,
            step_number=original.step_number,
            video_type=original.video_type,
            requested_backend=original.requested_backend,
            status="queued",
            progress=0,
            attempt=original.attempt + 1,
            max_attempts=original.max_attempts,
            provider=original.provider,
            model=original.model,
            request_hash=original.request_hash,
            idempotency_key=None,
            queued_at=_now(),
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def mark_stale_jobs_orphaned(self, cutoff: datetime) -> int:
        jobs = (
            self.db.query(ManimRenderJob)
            .filter(
                ManimRenderJob.status.in_(("generating_code", "rendering", "cancelling")),
                or_(ManimRenderJob.updated_at.is_(None), ManimRenderJob.updated_at < cutoff),
            )
            .all()
        )
        for job in jobs:
            job.status = "orphaned"
            job.finished_at = _now()
            job.updated_at = job.finished_at
            job.error_code = job.error_code or "worker_orphaned"
            job.error_message = job.error_message or "Job was orphaned by worker reconciliation"
        if jobs:
            self.db.commit()
        return len(jobs)

    def should_cancel(self, job_id: str) -> bool:
        job = (
            self.db.query(ManimRenderJob)
            .populate_existing()
            .filter(ManimRenderJob.job_id == job_id)
            .first()
        )
        return bool(job and job.status == "cancelling")
