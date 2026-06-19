"""
Export Routes - Direct service calls (KISS principle, no controller layer)
Handles export endpoints that were previously in routes/quests.py
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.dependencies import get_quest_repo
from app.models.db import Problem, ReasoningExport
from app.repositories import QuestRepository
from app.routes.auth import get_current_user
from app.services.export_service import ExportService
from app.services.notebook_converter import NotebookConverter

router = APIRouter()


def _save_export(
    problem_id: int,
    user_id: int,
    export_type: str,
    content: str,
    model: str = "default",
) -> None:
    """
    Save or update an export in the database.

    NOTE: Intentional SessionLocal() - the request-scoped DB session may not be
    suitable for post-generation persistence. This separate session handles the
    DB write independently.
    """
    db = SessionLocal()
    try:
        existing = (
            db.query(ReasoningExport)
            .filter(
                ReasoningExport.problem_id == problem_id,
                ReasoningExport.export_type == export_type,
            )
            .first()
        )
        if existing:
            db.delete(existing)

        new_export = ReasoningExport(
            problem_id=problem_id,
            export_type=export_type,
            content=content,
            ai_model=model,
            created_by=user_id,
        )
        db.add(new_export)
        db.commit()
    finally:
        db.close()


@router.post("/quest/export-markdown/{problem_id}")
async def export_reasoning_markdown(
    problem_id: int,
    use_ai: bool = False,
    force: bool = False,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
    quest_repo: QuestRepository = Depends(get_quest_repo),
):
    """Export reasoning as formatted markdown."""
    # Check for cached export
    if use_ai and not force:
        cached_export = (
            db.query(ReasoningExport)
            .filter(
                ReasoningExport.problem_id == problem_id,
                ReasoningExport.export_type == "markdown",
            )
            .first()
        )
        if cached_export:
            return {"markdown": cached_export.content, "enhanced": True, "cached": True}

    # Get cached reasoning
    reasoning = quest_repo.get_reasoning(problem_id)
    if not reasoning:
        raise HTTPException(
            404, "No reasoning found for this problem. Generate reasoning first."
        )

    reasoning_data = json.loads(reasoning.reasoning_data)
    steps = reasoning_data.get("steps", [])
    summary = reasoning_data.get("summary", "")
    web_references = reasoning_data.get("web_references", "")

    # Get problem title
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    problem_name = problem.title if problem else f"Problem {problem_id}"

    # Generate export
    service = ExportService()
    result = await service.export_to_markdown(
        problem_name=problem_name,
        steps=steps,
        summary=summary,
        web_references=web_references,
        use_ai=use_ai,
    )

    # Save if AI-enhanced
    if use_ai and result.get("enhanced"):
        _save_export(problem_id, user_id, "markdown", result["markdown"], "pplx_alpha")

    return result


@router.post("/quest/export-latex/{problem_id}")
async def export_reasoning_latex(
    problem_id: int,
    useSonnet: bool = False,
    force: bool = False,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
    quest_repo: QuestRepository = Depends(get_quest_repo),
):
    """Export reasoning as valid LaTeX document."""
    export_type = "latex_sonnet" if useSonnet else "latex"

    # Check for cached export
    if not force:
        cached_export = (
            db.query(ReasoningExport)
            .filter(
                ReasoningExport.problem_id == problem_id,
                ReasoningExport.export_type == export_type,
            )
            .first()
        )
        if cached_export:
            return {
                "latex": cached_export.content,
                "ai_generated": True,
                "model": cached_export.ai_model,
                "cached": True,
            }

    # Get cached reasoning
    reasoning = quest_repo.get_reasoning(problem_id)
    if not reasoning:
        raise HTTPException(
            404, "No reasoning found for this problem. Generate reasoning first."
        )

    reasoning_data = json.loads(reasoning.reasoning_data)
    steps = reasoning_data.get("steps", [])
    summary = reasoning_data.get("summary", "")

    # Get problem title
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    problem_name = problem.title if problem else f"Problem {problem_id}"

    # Generate export
    service = ExportService(use_sonnet=useSonnet)
    result = await service.export_to_latex(
        problem_name=problem_name,
        steps=steps,
        summary=summary,
    )

    # Save if AI-generated
    if result.get("ai_generated"):
        model = result.get("model", "pplx_alpha")
        _save_export(problem_id, user_id, export_type, result["latex"], model)

    return result


@router.post("/quest/export-notebook/{problem_id}")
async def export_reasoning_notebook(
    problem_id: int,
    useSonnet: bool = False,
    force: bool = False,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
    quest_repo: QuestRepository = Depends(get_quest_repo),
):
    """Export reasoning as Jupyter notebook."""
    export_type = "notebook_sonnet" if useSonnet else "notebook"

    # Check for cached export
    if not force:
        cached_export = (
            db.query(ReasoningExport)
            .filter(
                ReasoningExport.problem_id == problem_id,
                ReasoningExport.export_type == export_type,
            )
            .first()
        )
        if cached_export:
            return {
                "notebook": cached_export.content,
                "ai_model": cached_export.ai_model,
                "cached": True,
            }

    # Get cached reasoning
    reasoning = quest_repo.get_reasoning(problem_id)
    if not reasoning:
        raise HTTPException(
            404, "No reasoning found for this problem. Generate reasoning first."
        )

    reasoning_data = json.loads(reasoning.reasoning_data)
    steps = reasoning_data.get("steps", [])
    summary = reasoning_data.get("summary", "")

    # Get problem title
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    problem_name = problem.title if problem else f"Problem {problem_id}"

    # Generate notebook
    try:
        converter = NotebookConverter(use_sonnet=useSonnet)
        notebook_json = await converter.convert(problem_name, steps, summary)

        # Save to database
        model = "sonnet" if useSonnet else "default"
        _save_export(problem_id, user_id, export_type, notebook_json, model)

        return {
            "notebook": notebook_json,
            "ai_model": model,
            "cached": False,
        }

    except Exception as e:
        print(f"Notebook generation failed: {e}")
        raise HTTPException(500, f"Failed to generate notebook: {str(e)}")
