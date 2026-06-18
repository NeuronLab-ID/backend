"""
Manim animation routes for generating and serving reasoning step videos.
"""

import json

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import FileResponse, StreamingResponse

from app.controllers.manim_controller import ManimController
from app.dependencies import get_manim_controller, get_manim_queue_service
from app.models.schemas import ManimGenerateRequest, ManimJobCreateRequest
from app.routes.auth import get_current_user
from app.services.manim_queue import ManimQueueService, serialize_manim_job

router = APIRouter()


@router.get("/manim/backends")
async def get_manim_backends(
    user_id: int = Depends(get_current_user),
    queue: ManimQueueService = Depends(get_manim_queue_service),
):
    """Discover available Manim render backends."""
    return queue.list_backends()


@router.post("/manim/jobs", status_code=202)
async def create_manim_job(
    request: ManimJobCreateRequest,
    response: Response,
    user_id: int = Depends(get_current_user),
    queue: ManimQueueService = Depends(get_manim_queue_service),
):
    """Create a persisted async Manim render job."""
    job = queue.create_job(
        user_id=user_id,
        problem_id=request.problem_id,
        step_number=request.step_number,
        video_type=request.video_type,
        backend=request.backend,
        idempotency_key=request.idempotency_key,
    )
    status_url = f"/api/manim/jobs/{job.job_id}"
    response.headers["Location"] = status_url
    return {
        "job_id": job.job_id,
        "status": job.status,
        "status_url": status_url,
        "events_url": f"{status_url}/events",
    }


@router.get("/manim/jobs/{job_id}")
async def get_manim_job(
    job_id: str,
    user_id: int = Depends(get_current_user),
    queue: ManimQueueService = Depends(get_manim_queue_service),
):
    """Get persisted Manim render job status."""
    return serialize_manim_job(queue.get_job(job_id, user_id))


@router.post("/manim/jobs/{job_id}/cancel")
async def cancel_manim_job(
    job_id: str,
    user_id: int = Depends(get_current_user),
    queue: ManimQueueService = Depends(get_manim_queue_service),
):
    """Request cancellation for a queued or running Manim job."""
    job = queue.cancel_job(job_id, user_id)
    return {"job_id": job.job_id, "status": job.status}


@router.post("/manim/jobs/{job_id}/retry", status_code=202)
async def retry_manim_job(
    job_id: str,
    response: Response,
    user_id: int = Depends(get_current_user),
    queue: ManimQueueService = Depends(get_manim_queue_service),
):
    """Retry a failed, cancelled, or orphaned Manim job as a new queued job."""
    job = queue.retry_job(job_id, user_id)
    status_url = f"/api/manim/jobs/{job.job_id}"
    response.headers["Location"] = status_url
    return {
        "job_id": job.job_id,
        "status": job.status,
        "status_url": status_url,
        "events_url": f"{status_url}/events",
    }


@router.get("/manim/jobs/{job_id}/events")
async def stream_manim_job_events(
    job_id: str,
    user_id: int = Depends(get_current_user),
    queue: ManimQueueService = Depends(get_manim_queue_service),
):
    """Stream the current job snapshot once; polling remains authoritative."""
    job = queue.get_job(job_id, user_id)

    async def event_stream():
        yield f"event: status\ndata: {json.dumps(serialize_manim_job(job), default=str)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/manim/generate")
async def generate_manim_animation(
    request: ManimGenerateRequest,
    user_id: int = Depends(get_current_user),
    controller: ManimController = Depends(get_manim_controller),
):
    """Generate manim animation for a problem's reasoning steps."""
    return await controller.generate_animation(request.problem_id, request.step_number, user_id, request.video_type)


@router.get("/manim/status/{problem_id}")
async def get_manim_status(
    problem_id: int,
    user_id: int = Depends(get_current_user),
    controller: ManimController = Depends(get_manim_controller),
):
    """Get manim animation status for a problem."""
    return controller.get_animation_status(problem_id)


@router.get("/manim/video/{problem_id}/{step_number}")
async def get_manim_video(
    problem_id: int,
    step_number: int,
    type: str = Query("calculation", alias="type"),
    user_id: int = Depends(get_current_user),
    controller: ManimController = Depends(get_manim_controller),
):
    """Get rendered manim video file."""
    video_path = controller.get_video_path(problem_id, step_number, type)
    return FileResponse(video_path, media_type="video/mp4", filename=f"step_{step_number}_{type}.mp4")
