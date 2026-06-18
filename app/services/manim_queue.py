# pyright: reportArgumentType=false, reportGeneralTypeIssues=false, reportMissingTypeArgument=false, reportInvalidCast=false
from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from fastapi import HTTPException

from app.config import MANIM_STALE_JOB_SECONDS, MANIM_WORKER_POLL_INTERVAL
from app.database import SessionLocal
from app.logging_config import get_logger
from app.models.db import ManimRenderJob
from app.repositories.manim_repository import ManimRepository
from app.repositories.quest_repository import QuestRepository
from app.services.manim_backends import get_manim_backend_policy, list_manim_backend_policies
from app.services.manim_service import ManimService

logger = get_logger(__name__)

def serialize_manim_job(job: ManimRenderJob) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "problem_id": job.problem_id,
        "step_number": job.step_number,
        "video_type": job.video_type,
        "requested_backend": job.requested_backend,
        "resolved_backend": job.resolved_backend,
        "status": job.status,
        "progress": job.progress,
        "attempt": job.attempt,
        "max_attempts": job.max_attempts,
        "provider": job.provider,
        "model": job.model,
        "animation_id": job.animation_id,
        "error_code": job.error_code,
        "error_message": job.error_message,
        "logs_tail": job.logs_tail,
        "created_at": job.created_at,
        "queued_at": job.queued_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "cancel_requested_at": job.cancel_requested_at,
    }


def classify_failure(exc: Exception | None = None, message: str | None = None, attempt: int = 1, max_attempts: int = 2) -> tuple[str, str]:
    text = f"{type(exc).__name__ if exc else ''} {exc or ''} {message or ''}".lower()
    retryable_markers = ("timeout", "rate", "429", "temporar", "connection", "docker", "unavailable")
    if any(marker in text for marker in retryable_markers) and attempt < max_attempts:
        return "failed_retryable", "transient_failure"
    return "failed_terminal", "terminal_failure"


class ManimQueueService:
    def __init__(self, db):
        self.repository = ManimRepository(db)

    def list_backends(self) -> dict[str, Any]:
        policies = list_manim_backend_policies()
        default_backend = next((policy.name for policy in policies if policy.default), "cpu")
        return {
            "default_backend": default_backend,
            "backends": [
                {
                    "name": policy.name,
                    "available": policy.available,
                    "default": policy.default,
                    "reason": policy.reason,
                }
                for policy in policies
            ],
        }

    def create_job(
        self,
        *,
        user_id: int,
        problem_id: int,
        step_number: int | None,
        video_type: str | None,
        backend: str,
        idempotency_key: str | None = None,
    ) -> ManimRenderJob:
        get_manim_backend_policy(backend)
        return self.repository.create_job(
            user_id=user_id,
            problem_id=problem_id,
            step_number=step_number,
            video_type=video_type,
            requested_backend=backend,
            idempotency_key=idempotency_key,
        )

    def get_job(self, job_id: str, user_id: int) -> ManimRenderJob:
        job = self.repository.get_job(job_id, user_id=user_id)
        if not job:
            raise HTTPException(404, "Manim job not found")
        return job

    def cancel_job(self, job_id: str, user_id: int) -> ManimRenderJob:
        job = self.repository.request_cancel_job(job_id, user_id)
        if not job:
            raise HTTPException(404, "Manim job not found")
        return job

    def retry_job(self, job_id: str, user_id: int) -> ManimRenderJob:
        job = self.repository.retry_job(job_id, user_id)
        if not job:
            raise HTTPException(400, "Manim job is not retryable")
        return job


class ManimWorker:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._stopping = asyncio.Event()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stopping.clear()
        self._reconcile_orphaned_jobs()
        self._task = asyncio.create_task(self._run(), name="manim-worker")

    async def stop(self) -> None:
        self._stopping.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self) -> None:
        while not self._stopping.is_set():
            try:
                processed = await self.process_next_job()
                if not processed:
                    await asyncio.sleep(MANIM_WORKER_POLL_INTERVAL)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("Manim worker loop error: %s", exc)
                await asyncio.sleep(MANIM_WORKER_POLL_INTERVAL)

    async def process_next_job(self) -> bool:
        db = SessionLocal()
        try:
            repo = ManimRepository(db)
            job = repo.claim_next_job()
            if not job:
                return False
            job_id = job.job_id
        finally:
            db.close()

        await self._process_job(job_id)
        return True

    def _reconcile_orphaned_jobs(self) -> None:
        db = SessionLocal()
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(seconds=MANIM_STALE_JOB_SECONDS)
            count = ManimRepository(db).mark_stale_jobs_orphaned(cutoff)
            if count:
                logger.warning("Marked %s stale Manim jobs as orphaned", count)
        finally:
            db.close()

    async def _process_job(self, job_id: str) -> None:
        db = SessionLocal()
        try:
            repo = ManimRepository(db)
            job = repo.get_job(job_id)
            if not job:
                return
            if job.status == "cancelling":
                repo.update_job(job_id, status="cancelled", progress=100, finished=True)
                return

            policy = get_manim_backend_policy(job.requested_backend)
            repo.update_job(job_id, resolved_backend=policy.name, status="generating_code", progress=20)

            quest_repo = QuestRepository(db)
            reasoning = quest_repo.get_reasoning(job.problem_id)
            if not reasoning:
                repo.update_job(
                    job_id,
                    status="failed_terminal",
                    progress=100,
                    error_code="reasoning_not_found",
                    error_message="No reasoning available for this problem",
                    finished=True,
                )
                return

            reasoning_data = json.loads(reasoning.reasoning_data)
            if repo.should_cancel(job_id):
                repo.update_job(job_id, status="cancelled", progress=100, finished=True)
                return

            service = ManimService(db)
            repo.update_job(job_id, status="rendering", progress=50)
            started = time.time()
            animation = await self._run_generation(
                service, job_id, reasoning_data, job.problem_id, job.step_number, job.video_type, policy.name
            )
            animation_id = cast(int, animation.id)
            if repo.should_cancel(job_id):
                repo.update_job(job_id, status="cancelled", progress=100, animation_id=animation_id, finished=True)
                return
            animation_status = cast(str, animation.status)
            if animation_status == "completed":
                repo.update_job(job_id, status="succeeded", progress=100, animation_id=animation_id, finished=True)
            else:
                message = cast(str | None, animation.error_message) or "Manim render failed"
                status, code = classify_failure(
                    message=message, attempt=cast(int, job.attempt), max_attempts=cast(int, job.max_attempts)
                )
                repo.update_job(
                    job_id,
                    status=status,
                    progress=100,
                    animation_id=animation_id,
                    error_code=code,
                    error_message=message,
                    finished=True,
                )
            if animation.render_time_ms is None:
                repo.update_status(animation_id, animation_status, render_time_ms=int((time.time() - started) * 1000))
        except HTTPException as exc:
            db.rollback()
            repo = ManimRepository(db)
            repo.update_job(
                job_id,
                status="failed_terminal",
                progress=100,
                error_code="backend_unavailable",
                error_message=str(exc.detail),
                finished=True,
            )
        except Exception as exc:
            db.rollback()
            repo = ManimRepository(db)
            job = repo.get_job(job_id)
            attempt = job.attempt if job else 1
            max_attempts = job.max_attempts if job else 1
            status, code = classify_failure(exc=exc, attempt=attempt, max_attempts=max_attempts)
            repo.update_job(
                job_id,
                status=status,
                progress=100,
                error_code=code,
                error_message=str(exc),
                finished=True,
            )
        finally:
            db.close()

    async def _run_generation(
        self,
        service: ManimService,
        job_id: str,
        reasoning_data: dict[str, Any],
        problem_id: int,
        step_number: int | None,
        video_type: str | None,
        backend: str,
    ):
        if step_number is not None:
            steps = reasoning_data.get("steps") or reasoning_data.get("sub_quests") or []
            if not isinstance(steps, list) or step_number < 1 or step_number > len(steps):
                raise ValueError(f"Invalid step number {step_number}")
            step = steps[step_number - 1] if isinstance(steps[step_number - 1], dict) else {}
            step_payload = {
                "step_title": step.get("title", f"Step {step_number}"),
                "step_reasoning": step.get("reasoning", ""),
                "key_formulas": step.get("key_formulas", []),
                "problem_title": reasoning_data.get("problem_title", reasoning_data.get("title", "")),
                "problem_description": reasoning_data.get("problem_description", reasoning_data.get("description", "")),
            }
            return await service.generate_animation(
                problem_id,
                step_number,
                step_payload,
                video_type=video_type or "calculation",
                backend=backend,
                on_container_started=lambda container_id: service.repository.update_job(job_id, container_id=container_id),
                should_cancel=lambda: service.repository.should_cancel(job_id),
            )

        animations = await service.generate_all_animations(
            problem_id,
            reasoning_data,
            video_type=video_type,
            backend=backend,
            should_cancel=lambda: service.repository.should_cancel(job_id),
        )
        if not animations:
            raise ValueError("No Manim animations were generated")
        return animations[-1]


manim_worker = ManimWorker()
