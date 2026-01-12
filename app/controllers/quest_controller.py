# Quest Controller
# Orchestration layer between routes and services

import json
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import asyncio

from app.config import LOCAL_DEV
from app.models.db import Quest, QuestProgress, QuestReasoning, Problem, ReasoningExport
from app.repositories import QuestRepository
from app.services.reasoning_service import (
    ReasoningService,
    fix_mermaid_code,
    generate_test_case_reasoning,
)
from app.services.export_service import ExportService
from app.services.executor import execute_code
from app.services.notebook_converter import NotebookConverter


class QuestController:
    """Controller for quest operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.repository = QuestRepository(db)
    
    async def get_quest(self, problem_id: int, generate: bool = False) -> dict:
        """Get quest for a problem, optionally generating on-demand."""
        from app.services.quest_service import get_or_generate_quest, generate_quest_on_demand
        
        result = await get_or_generate_quest(self.db, problem_id)
        
        if result:
            return result
        
        if generate:
            result = await generate_quest_on_demand(self.db, problem_id)
            if result:
                return result
            raise HTTPException(500, "Quest generation failed")
        
        raise HTTPException(404, "Quest not found for this problem. Use ?generate=true to generate on-demand.")
    
    async def execute_code(self, problem_id: int, step: int, code: str) -> dict:
        """Execute code for a quest exercise."""
        quest = self.repository.get_by_problem_id(problem_id)
        if not quest:
            raise HTTPException(404, "Quest not found")
        
        quest_data = json.loads(quest.data)
        sub_quests = quest_data.get("sub_quests", [])
        sub_quest = next((sq for sq in sub_quests if sq.get("step") == step), None)
        
        if not sub_quest:
            raise HTTPException(404, f"Step {step} not found in quest")
        
        exercise = sub_quest.get("exercise", {})
        test_cases = exercise.get("test_cases", [])
        
        if not test_cases:
            raise HTTPException(400, "No test cases found for this exercise")
        
        return await execute_code(code=code, test_cases=test_cases)
    
    async def save_progress(self, user_id: int, problem_id: int, step: int, code: str) -> dict:
        """Save progress for a quest step."""
        existing = self.repository.get_progress_by_step(user_id, problem_id, step)
        
        if existing:
            self.repository.update_progress(existing, code, completed=True)
        else:
            progress = QuestProgress(
                user_id=user_id,
                problem_id=problem_id,
                step=step,
                code=code,
                completed=True
            )
            self.repository.save_progress(progress)
        
        return {"message": "Progress saved", "step": step}
    
    def get_progress(self, user_id: int, problem_id: int) -> dict:
        """Get user's progress for all steps of a quest."""
        progress = self.repository.get_progress(user_id, problem_id)
        
        return {
            "progress": [
                {
                    "step": p.step,
                    "code": p.code,
                    "completed": p.completed,
                    "created_at": p.created_at.isoformat()
                }
                for p in progress
            ]
        }
    
    def get_cached_reasoning(self, problem_id: int) -> dict:
        """Get cached full reasoning for a problem."""
        reasoning = self.repository.get_reasoning(problem_id)
        
        if reasoning:
            return {
                "exists": True,
                "data": json.loads(reasoning.reasoning_data),
                "created_at": reasoning.created_at.isoformat()
            }
        return {"exists": False, "data": None}
    
    async def stream_full_reasoning(
        self,
        problem_id: int,
        user_id: int,
        force: bool = False,
        use_perplexity: bool = False,
        use_perplexity_reasoning: bool = False
    ) -> StreamingResponse:
        """Generate and stream full reasoning for all quest steps."""
        # Check for cached reasoning
        existing = self.repository.get_reasoning(problem_id)
        
        if force and existing:
            self.repository.delete_reasoning(problem_id)
            existing = None
        
        if existing:
            return self._stream_cached_reasoning(existing)
        
        # Get quest data
        quest = self.repository.get_by_problem_id(problem_id)
        if not quest:
            raise HTTPException(404, "Quest not found")
        
        quest_data = json.loads(quest.data)
        sub_quests = quest_data.get("sub_quests", [])
        
        if not sub_quests:
            raise HTTPException(400, "No quest steps found")
        
        return StreamingResponse(
            self._generate_reasoning_stream(
                problem_id, user_id, quest_data, sub_quests,
                use_perplexity, use_perplexity_reasoning
            ),
            media_type="text/event-stream"
        )
    
    def _stream_cached_reasoning(self, reasoning: QuestReasoning) -> StreamingResponse:
        """Stream cached reasoning data."""
        cached_data = json.loads(reasoning.reasoning_data)
        
        async def stream_cached():
            if cached_data.get("web_references"):
                yield f"data: {json.dumps({'type': 'search_result', 'data': {'content': cached_data['web_references']}})}\n\n"
                yield f"data: {json.dumps({'type': 'search_complete', 'data': {'chars': len(cached_data['web_references'])}})}\n\n"
            
            for step_data in cached_data.get("steps", []):
                yield f"data: {json.dumps({'type': 'step', 'data': step_data})}\n\n"
                await asyncio.sleep(0.1)
            
            if cached_data.get("summary"):
                yield f"data: {json.dumps({'type': 'summary', 'data': cached_data['summary']})}\n\n"
            
            yield f"data: {json.dumps({'type': 'done', 'cached': True})}\n\n"
        
        return StreamingResponse(stream_cached(), media_type="text/event-stream")
    
    async def _generate_reasoning_stream(
        self,
        problem_id: int,
        user_id: int,
        quest_data: dict,
        sub_quests: list,
        use_perplexity: bool,
        use_perplexity_reasoning: bool
    ):
        """Generate reasoning stream."""
        try:
            service = ReasoningService(
                use_perplexity=use_perplexity,
                use_perplexity_reasoning=use_perplexity_reasoning
            )
            
            complete_data = None
            
            async for event in service.stream_full_reasoning(quest_data, sub_quests):
                if event.get("type") == "complete":
                    complete_data = event["data"]
                    continue
                
                yield f"data: {json.dumps(event)}\n\n"
            
            # Save to database
            if complete_data:
                from app.database import SessionLocal
                db = SessionLocal()
                try:
                    new_reasoning = QuestReasoning(
                        problem_id=problem_id,
                        reasoning_data=json.dumps(complete_data),
                        created_by=user_id
                    )
                    db.add(new_reasoning)
                    db.commit()
                finally:
                    db.close()
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    async def export_markdown(
        self,
        problem_id: int,
        user_id: int,
        use_ai: bool = False,
        force: bool = False
    ) -> dict:
        """Export reasoning as formatted markdown."""
        # Check for cached export
        if use_ai and not force:
            cached_export = self.db.query(ReasoningExport).filter(
                ReasoningExport.problem_id == problem_id,
                ReasoningExport.export_type == 'markdown'
            ).first()
            
            if cached_export:
                return {"markdown": cached_export.content, "enhanced": True, "cached": True}
        
        # Get cached reasoning
        reasoning = self.repository.get_reasoning(problem_id)
        if not reasoning:
            raise HTTPException(404, "No reasoning found for this problem. Generate reasoning first.")
        
        reasoning_data = json.loads(reasoning.reasoning_data)
        steps = reasoning_data.get("steps", [])
        summary = reasoning_data.get("summary", "")
        web_references = reasoning_data.get("web_references", "")
        
        # Get problem title
        problem = self.db.query(Problem).filter(Problem.id == problem_id).first()
        problem_name = problem.title if problem else f"Problem {problem_id}"
        
        # Generate export
        service = ExportService()
        result = await service.export_to_markdown(
            problem_name=problem_name,
            steps=steps,
            summary=summary,
            web_references=web_references,
            use_ai=use_ai
        )
        
        # Save if AI-enhanced
        if use_ai and result.get("enhanced"):
            self._save_export(problem_id, user_id, 'markdown', result["markdown"], 'pplx_alpha')
        
        return result
    
    async def export_latex(
        self,
        problem_id: int,
        user_id: int,
        use_sonnet: bool = False,
        force: bool = False
    ) -> dict:
        """Export reasoning as valid LaTeX document."""
        export_type = 'latex_sonnet' if use_sonnet else 'latex'
        
        # Check for cached export
        if not force:
            cached_export = self.db.query(ReasoningExport).filter(
                ReasoningExport.problem_id == problem_id,
                ReasoningExport.export_type == export_type
            ).first()
            
            if cached_export:
                return {"latex": cached_export.content, "ai_generated": True, "model": cached_export.ai_model, "cached": True}
        
        # Get cached reasoning
        reasoning = self.repository.get_reasoning(problem_id)
        if not reasoning:
            raise HTTPException(404, "No reasoning found for this problem. Generate reasoning first.")
        
        reasoning_data = json.loads(reasoning.reasoning_data)
        steps = reasoning_data.get("steps", [])
        summary = reasoning_data.get("summary", "")
        
        # Get problem title
        problem = self.db.query(Problem).filter(Problem.id == problem_id).first()
        problem_name = problem.title if problem else f"Problem {problem_id}"
        
        # Generate export
        service = ExportService(use_sonnet=use_sonnet)
        result = await service.export_to_latex(
            problem_name=problem_name,
            steps=steps,
            summary=summary
        )
        
        # Save if AI-generated
        if result.get("ai_generated"):
            model = result.get("model", "pplx_alpha")
            self._save_export(problem_id, user_id, export_type, result["latex"], model)
        
        return result
    
    async def export_notebook(
        self,
        problem_id: int,
        user_id: int,
        use_sonnet: bool = False,
        force: bool = False
    ) -> dict:
        """Export reasoning as Jupyter notebook."""
        export_type = 'notebook_sonnet' if use_sonnet else 'notebook'
        
        # Check for cached export
        if not force:
            cached_export = self.db.query(ReasoningExport).filter(
                ReasoningExport.problem_id == problem_id,
                ReasoningExport.export_type == export_type
            ).first()
            
            if cached_export:
                return {
                    "notebook": cached_export.content,
                    "ai_model": cached_export.ai_model,
                    "cached": True
                }
        
        # Get cached reasoning
        reasoning = self.repository.get_reasoning(problem_id)
        if not reasoning:
            raise HTTPException(404, "No reasoning found for this problem. Generate reasoning first.")
        
        reasoning_data = json.loads(reasoning.reasoning_data)
        steps = reasoning_data.get("steps", [])
        summary = reasoning_data.get("summary", "")
        
        # Get problem title
        problem = self.db.query(Problem).filter(Problem.id == problem_id).first()
        problem_name = problem.title if problem else f"Problem {problem_id}"
        
        # Generate notebook
        try:
            converter = NotebookConverter(use_sonnet=use_sonnet)
            notebook_json = await converter.convert(problem_name, steps, summary)
            
            # Save to database
            model = 'sonnet' if use_sonnet else 'default'
            self._save_export(problem_id, user_id, export_type, notebook_json, model)
            
            return {
                "notebook": notebook_json,
                "ai_model": model,
                "cached": False
            }
            
        except Exception as e:
            print(f"Notebook generation failed: {e}")
            raise HTTPException(500, f"Failed to generate notebook: {str(e)}")
    
    def _save_export(self, problem_id: int, user_id: int, export_type: str, content: str, model: str) -> None:
        """Save export to database."""
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            existing = db.query(ReasoningExport).filter(
                ReasoningExport.problem_id == problem_id,
                ReasoningExport.export_type == export_type
            ).first()
            if existing:
                db.delete(existing)
            
            new_export = ReasoningExport(
                problem_id=problem_id,
                export_type=export_type,
                content=content,
                ai_model=model,
                created_by=user_id
            )
            db.add(new_export)
            db.commit()
        finally:
            db.close()


# Convenience functions for route handlers
async def create_quest(db: Session, problem_id: int, data: dict, user_id: int) -> dict:
    """Create a quest (LOCAL_DEV only)."""
    if not LOCAL_DEV:
        raise HTTPException(403, "Quest creation is only allowed in local development mode")
    
    repository = QuestRepository(db)
    existing = repository.get_by_problem_id(problem_id)
    if existing:
        raise HTTPException(400, "Quest already exists for this problem")
    
    quest = Quest(
        problem_id=problem_id,
        data=json.dumps(data),
        created_by=user_id
    )
    saved = repository.save(quest)
    
    return {"message": "Quest created", "id": saved.id}


def check_quest_exists(db: Session, problem_id: int) -> dict:
    """Check if a quest exists for a problem."""
    from app.services.quest_service import get_quest_status
    
    status = get_quest_status(db, problem_id)
    status["local_dev"] = LOCAL_DEV
    return status
